"""Voice Processor Lambda — WebSocket handler for voice streaming.

Handles WebSocket events:
  $connect     → Create connection record
  $disconnect  → Clean up connection
  startSession → Initialize a voice session
  audioChunk   → Process audio via Transcribe → AI → Polly
  message      → Process text message (web demo fallback)
  endSession   → End the session gracefully
"""

import base64
import json
import logging
import os
import time

import boto3

from transcribe import transcribe_audio
from polly import synthesize_speech, detect_language

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment
REGION = os.environ.get("AWS_REGION", "us-east-1")
CONNECTIONS_TABLE = os.environ.get("CONNECTIONS_TABLE", "vaanisetu-connections")
SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE", "vaanisetu-sessions")
WEBSOCKET_API_ENDPOINT = os.environ.get("WEBSOCKET_API_ENDPOINT", "")
AI_ENGINE_FUNCTION = os.environ.get("AI_ENGINE_FUNCTION", "")
CONNECTION_TTL = 2 * 60 * 60  # 2 hours

# AWS clients
_dynamodb = boto3.resource("dynamodb", region_name=REGION)
_connections_table = _dynamodb.Table(CONNECTIONS_TABLE)
_sessions_table = _dynamodb.Table(SESSIONS_TABLE)
_lambda_client = boto3.client("lambda", region_name=REGION)


def handler(event, context):
    """Main WebSocket handler — routes based on event type."""
    logger.info(f"WS Event: {json.dumps({k: v for k, v in event.items() if k != 'body'}, default=str)}")

    route_key = event.get("requestContext", {}).get("routeKey", "")
    connection_id = event.get("requestContext", {}).get("connectionId", "")

    try:
        if route_key == "$connect":
            return _handle_connect(connection_id, event)
        elif route_key == "$disconnect":
            return _handle_disconnect(connection_id)
        elif route_key == "$default":
            body = _parse_body(event)
            action = body.get("action", "")

            if action == "startSession":
                return _handle_start_session(connection_id, body)
            elif action == "audioChunk":
                return _handle_audio_chunk(connection_id, body)
            elif action == "message":
                return _handle_text_message(connection_id, body)
            elif action == "switchLanguage":
                return _handle_switch_language(connection_id, body)
            elif action == "endSession":
                return _handle_end_session(connection_id, body)
            else:
                _send_to_client(connection_id, {
                    "type": "error",
                    "message": f"Unknown action: {action}"
                })
                return {"statusCode": 400}

        return {"statusCode": 200}

    except Exception as e:
        logger.exception(f"WebSocket handler error: {e}")
        try:
            _send_to_client(connection_id, {
                "type": "error",
                "message": "An error occurred. Please try again."
            })
        except Exception:
            pass
        return {"statusCode": 500}


# ── WebSocket Event Handlers ─────────────────────────────────────────

def _handle_connect(connection_id: str, event: dict) -> dict:
    """Handle new WebSocket connection."""
    _connections_table.put_item(Item={
        "connectionId": connection_id,
        "connectedAt": _now_iso(),
        "ttl": int(time.time()) + CONNECTION_TTL,
    })
    logger.info(f"Connected: {connection_id}")
    return {"statusCode": 200}


def _handle_disconnect(connection_id: str) -> dict:
    """Handle WebSocket disconnection — cleanup."""
    try:
        # Get connection to find session
        conn = _connections_table.get_item(Key={"connectionId": connection_id})
        item = conn.get("Item", {})
        session_id = item.get("sessionId")

        # Mark session as abandoned if active
        if session_id:
            _sessions_table.update_item(
                Key={"sessionId": session_id},
                UpdateExpression="SET #s = :s, updatedAt = :now",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={
                    ":s": "abandoned",
                    ":now": _now_iso(),
                },
            )

        # Remove connection record
        _connections_table.delete_item(Key={"connectionId": connection_id})

    except Exception as e:
        logger.error(f"Disconnect cleanup error: {e}")

    logger.info(f"Disconnected: {connection_id}")
    return {"statusCode": 200}


def _handle_start_session(connection_id: str, body: dict) -> dict:
    """Initialize a new voice conversation session."""
    import uuid

    language = body.get("language", "auto")
    session_id = str(uuid.uuid4())

    # Create session in DynamoDB
    now = _now_iso()
    session = {
        "sessionId": session_id,
        "connectionId": connection_id,
        "language": language if language != "auto" else "hi-IN",
        "status": "active",
        "conversationState": "GREETING",
        "conversationHistory": [],
        "userProfile": {},
        "matchedSchemes": [],
        "formData": {},
        "createdAt": now,
        "updatedAt": now,
        "ttl": int(time.time()) + (90 * 24 * 60 * 60),
    }
    _sessions_table.put_item(Item=session)

    # Link connection to session
    _connections_table.update_item(
        Key={"connectionId": connection_id},
        UpdateExpression="SET sessionId = :sid",
        ExpressionAttributeValues={":sid": session_id},
    )

    # Send greeting
    greetings = {
        "hi-IN": "नमस्ते! मैं वाणी सेतु हूँ।",
        "ta-IN": "வணக்கம்! நான் வாணி சேது.",
        "en-IN": "Hello! I am VaaniSetu.",
    }
    greeting = greetings.get(session["language"], greetings["hi-IN"])

    # Generate speech for greeting
    audio_data = synthesize_speech(greeting, session["language"])

    _send_to_client(connection_id, {
        "type": "sessionStarted",
        "sessionId": session_id,
        "language": session["language"],
    })

    _send_to_client(connection_id, {
        "type": "aiResponse",
        "text": greeting,
        "audio": audio_data.get("audio", ""),
        "contentType": audio_data.get("contentType", ""),
        "sessionId": session_id,
    })

    return {"statusCode": 200}


def _handle_audio_chunk(connection_id: str, body: dict) -> dict:
    """Process an audio chunk — STT → AI → TTS."""
    audio_data = body.get("data", "")
    session_id = body.get("sessionId", "")

    if not audio_data:
        return {"statusCode": 400}

    # Get session
    session = _get_session_for_connection(connection_id, session_id)
    if not session:
        _send_to_client(connection_id, {"type": "error", "message": "No active session"})
        return {"statusCode": 400}

    # Decode audio
    audio_bytes = base64.b64decode(audio_data)

    # Speech-to-Text
    language = session.get("language", "hi-IN")
    transcript = transcribe_audio(audio_bytes, language)

    text = transcript.get("text", "").strip()
    if not text:
        _send_to_client(connection_id, {"type": "transcription", "text": "", "isFinal": False})
        return {"statusCode": 200}

    # Send transcription to client
    _send_to_client(connection_id, {
        "type": "transcription",
        "text": text,
        "isFinal": True,
        "language": transcript.get("language", language),
    })

    # Detect language if auto
    if session.get("language") == "auto" or not session.get("language"):
        detected = detect_language(text)
        language = detected
        _sessions_table.update_item(
            Key={"sessionId": session["sessionId"]},
            UpdateExpression="SET #lang = :lang",
            ExpressionAttributeNames={"#lang": "language"},
            ExpressionAttributeValues={":lang": language},
        )
        _send_to_client(connection_id, {"type": "languageDetected", "language": language})

    # Process through AI Engine
    _process_and_respond(connection_id, session, text, language)

    return {"statusCode": 200}


def _handle_text_message(connection_id: str, body: dict) -> dict:
    """Process a text message (web demo) — AI → TTS."""
    text = body.get("data", body.get("text", "")).strip()
    session_id = body.get("sessionId", "")

    if not text:
        return {"statusCode": 400}

    session = _get_session_for_connection(connection_id, session_id)
    if not session:
        _send_to_client(connection_id, {"type": "error", "message": "No active session"})
        return {"statusCode": 400}

    language = body.get("language") or session.get("language", "hi-IN")

    _process_and_respond(connection_id, session, text, language)
    return {"statusCode": 200}


def _handle_switch_language(connection_id: str, body: dict) -> dict:
    """Switch conversation language."""
    new_language = body.get("language", "hi-IN")
    session_id = body.get("sessionId", "")

    session = _get_session_for_connection(connection_id, session_id)
    if session:
        _sessions_table.update_item(
            Key={"sessionId": session["sessionId"]},
            UpdateExpression="SET #lang = :lang, updatedAt = :now",
            ExpressionAttributeNames={"#lang": "language"},
            ExpressionAttributeValues={":lang": new_language, ":now": _now_iso()},
        )

    _send_to_client(connection_id, {"type": "languageSwitched", "language": new_language})
    return {"statusCode": 200}


def _handle_end_session(connection_id: str, body: dict) -> dict:
    """End the current session."""
    session_id = body.get("sessionId", "")
    session = _get_session_for_connection(connection_id, session_id)

    if session:
        _sessions_table.update_item(
            Key={"sessionId": session["sessionId"]},
            UpdateExpression="SET #s = :s, updatedAt = :now",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "completed", ":now": _now_iso()},
        )

    _send_to_client(connection_id, {"type": "sessionEnded", "sessionId": session_id})
    return {"statusCode": 200}


# ── Helper Functions ─────────────────────────────────────────────────

def _process_and_respond(connection_id: str, session: dict, text: str, language: str):
    """Process message through AI and send response with audio."""
    from decimal import Decimal

    class DecimalEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, Decimal):
                return int(obj) if obj % 1 == 0 else float(obj)
            return super().default(obj)

    # Add user message to history
    _sessions_table.update_item(
        Key={"sessionId": session["sessionId"]},
        UpdateExpression="SET conversationHistory = list_append(if_not_exists(conversationHistory, :empty), :msg), updatedAt = :now",
        ExpressionAttributeValues={
            ":msg": [{"role": "user", "content": text, "timestamp": _now_iso(), "language": language}],
            ":empty": [],
            ":now": _now_iso(),
        },
    )

    # Invoke AI Engine
    ai_payload = {
        "sessionId": session["sessionId"],
        "userMessage": text,
        "language": language,
        "conversationState": session.get("conversationState", "GREETING"),
        "conversationHistory": session.get("conversationHistory", []),
        "userProfile": session.get("userProfile", {}),
        "matchedSchemes": session.get("matchedSchemes", []),
        "selectedScheme": session.get("selectedScheme"),
        "formData": session.get("formData", {}),
    }

    ai_response = _invoke_ai_engine(ai_payload)
    response_text = ai_response.get("response", "")

    # Generate speech
    audio_data = synthesize_speech(response_text, language)

    # Update session with AI response
    updates = {"updatedAt": _now_iso()}
    if ai_response.get("conversationState"):
        updates["conversationState"] = ai_response["conversationState"]
    if ai_response.get("userProfile"):
        updates["userProfile"] = ai_response["userProfile"]
    if ai_response.get("matchedSchemes"):
        updates["matchedSchemes"] = [s.get("schemeId", s) if isinstance(s, dict) else s for s in ai_response["matchedSchemes"]]
    if ai_response.get("selectedScheme"):
        updates["selectedScheme"] = ai_response["selectedScheme"]
    if ai_response.get("formData"):
        updates["formData"] = ai_response["formData"]

    if len(updates) > 1:
        update_parts = []
        expr_names = {}
        expr_values = {}
        for i, (k, v) in enumerate(updates.items()):
            update_parts.append(f"#k{i} = :v{i}")
            expr_names[f"#k{i}"] = k
            expr_values[f":v{i}"] = v
        _sessions_table.update_item(
            Key={"sessionId": session["sessionId"]},
            UpdateExpression="SET " + ", ".join(update_parts),
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
        )

    # Send AI response to client
    ws_message = {
        "type": "aiResponse",
        "text": response_text,
        "audio": audio_data.get("audio", ""),
        "contentType": audio_data.get("contentType", ""),
        "sessionId": session["sessionId"],
    }

    if ai_response.get("conversationState"):
        ws_message["conversationState"] = ai_response["conversationState"]
    if ai_response.get("matchedSchemes"):
        ws_message["matchedSchemes"] = ai_response["matchedSchemes"]
    if ai_response.get("formProgress"):
        ws_message["formProgress"] = ai_response["formProgress"]
    if ai_response.get("applicationId"):
        ws_message["applicationId"] = ai_response["applicationId"]

    _send_to_client(connection_id, ws_message)

    # Add assistant message to history
    _sessions_table.update_item(
        Key={"sessionId": session["sessionId"]},
        UpdateExpression="SET conversationHistory = list_append(if_not_exists(conversationHistory, :empty), :msg)",
        ExpressionAttributeValues={
            ":msg": [{"role": "assistant", "content": response_text, "timestamp": _now_iso()}],
            ":empty": [],
        },
    )


def _invoke_ai_engine(payload: dict) -> dict:
    """Invoke AI Engine Lambda."""
    from decimal import Decimal

    class DecimalEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, Decimal):
                return int(obj) if obj % 1 == 0 else float(obj)
            return super().default(obj)

    if not AI_ENGINE_FUNCTION:
        return {"response": f"[Dev] Received: {payload.get('userMessage', '')}"}

    try:
        response = _lambda_client.invoke(
            FunctionName=AI_ENGINE_FUNCTION,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload, cls=DecimalEncoder),
        )
        return json.loads(response["Payload"].read().decode("utf-8"))
    except Exception as e:
        logger.error(f"AI Engine invocation error: {e}")
        return {"response": "क्षमा करें, कुछ गड़बड़ हो गई।"}


def _get_session_for_connection(connection_id: str, session_id: str = "") -> dict:
    """Get session linked to a connection."""
    if session_id:
        response = _sessions_table.get_item(Key={"sessionId": session_id})
        return response.get("Item")

    # Look up session from connection
    conn = _connections_table.get_item(Key={"connectionId": connection_id})
    conn_item = conn.get("Item", {})
    sid = conn_item.get("sessionId")
    if sid:
        response = _sessions_table.get_item(Key={"sessionId": sid})
        return response.get("Item")

    return None


def _send_to_client(connection_id: str, data: dict):
    """Send message to WebSocket client."""
    from decimal import Decimal

    class DecimalEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, Decimal):
                return int(obj) if obj % 1 == 0 else float(obj)
            return super().default(obj)

    if not WEBSOCKET_API_ENDPOINT:
        logger.warning(f"No WS endpoint, would send: {json.dumps(data, cls=DecimalEncoder)[:200]}")
        return

    try:
        apigw = boto3.client(
            "apigatewaymanagementapi",
            endpoint_url=WEBSOCKET_API_ENDPOINT,
            region_name=REGION,
        )
        apigw.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(data, ensure_ascii=False, cls=DecimalEncoder).encode("utf-8"),
        )
    except Exception as e:
        logger.error(f"Error sending to client {connection_id}: {e}")


def _parse_body(event: dict) -> dict:
    body = event.get("body", "{}")
    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {}
    return body


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
