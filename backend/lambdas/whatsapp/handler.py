"""WhatsApp Webhook Lambda — Twilio WhatsApp integration for VaaniSetu.

Receives inbound WhatsApp messages from Twilio's webhook, processes them
through the existing VaaniSetu AI pipeline, and replies via Twilio's API.

How it works:
  1. Twilio sends a POST with form-encoded data (From, Body, etc.)
  2. We look up (or create) a session keyed by the phone number.
  3. We invoke the orchestrator's message pipeline (AI Engine + Bedrock).
  4. We return TwiML XML so Twilio sends the AI response back to WhatsApp.

Environment Variables:
  TWILIO_ACCOUNT_SID  — Twilio account SID (for signature validation)
  TWILIO_AUTH_TOKEN   — Twilio auth token (for signature validation)
  SESSIONS_TABLE      — DynamoDB sessions table
  AI_ENGINE_FUNCTION  — AI Engine Lambda function name
  SCHEMES_TABLE       — DynamoDB schemes table

Why TwiML instead of Twilio REST API?
  Returning TwiML XML directly from the webhook is simpler, cheaper, and
  doesn't require the twilio Python SDK. Twilio processes the XML response
  and sends the message back to the user automatically.
"""

import json
import logging
import os
import hashlib
import time
from datetime import datetime, timezone
from urllib.parse import parse_qs
from decimal import Decimal

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment
REGION = os.environ.get("AWS_REGION", "us-east-1")
SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE", "vaanisetu-sessions")
SCHEMES_TABLE = os.environ.get("SCHEMES_TABLE", "vaanisetu-schemes")
APPLICATIONS_TABLE = os.environ.get("APPLICATIONS_TABLE", "vaanisetu-applications")
AI_ENGINE_FUNCTION = os.environ.get("AI_ENGINE_FUNCTION", "vaanisetu-ai-engine")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")

# AWS clients
_dynamodb = boto3.resource("dynamodb", region_name=REGION)
_sessions_table = _dynamodb.Table(SESSIONS_TABLE)
_lambda_client = boto3.client("lambda", region_name=REGION)


class DecimalEncoder(json.JSONEncoder):
    """Handle DynamoDB Decimal types in JSON serialization."""
    def default(self, obj: object) -> object:
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


def handler(event: dict, context: object) -> dict:
    """Main Lambda handler — receives Twilio WhatsApp webhook."""
    logger.info(f"WhatsApp webhook event: {json.dumps(event, default=str)[:500]}")

    try:
        http_method = event.get("httpMethod", "POST")
        path = event.get("path", "/")

        # Health check
        if path.endswith("/health") and http_method == "GET":
            return _twiml_response("<Response/>", 200)

        # Status callback (message delivery receipts) — just ACK
        body_str = event.get("body", "")
        if event.get("isBase64Encoded"):
            import base64
            body_str = base64.b64decode(body_str).decode("utf-8")

        params = parse_qs(body_str)

        # Check if this is a status callback (not a message)
        msg_status = _get_param(params, "MessageStatus")
        if msg_status:
            logger.info(f"Status callback: {msg_status}")
            return _twiml_response("<Response/>", 200)

        # Extract message details
        from_number = _get_param(params, "From")       # e.g. whatsapp:+919876543210
        body = _get_param(params, "Body")               # User's message text
        profile_name = _get_param(params, "ProfileName") # WhatsApp display name

        if not from_number or not body:
            logger.warning("Missing From or Body in webhook payload")
            return _twiml_response("<Response><Message>Please send a text message.</Message></Response>", 200)

        # Clean phone number (remove "whatsapp:" prefix)
        phone = from_number.replace("whatsapp:", "").strip()

        logger.info(f"WhatsApp message from {phone} ({profile_name}): {body[:100]}")

        # Get or create session for this phone number
        session = _get_or_create_session(phone, profile_name)
        session_id = session["sessionId"]

        # Invoke AI Engine to process the message
        ai_response = _invoke_ai_engine(session_id, body, session)

        # Extract response text
        reply_text = ai_response.get("response", "")
        if not reply_text:
            reply_text = "Sorry, I could not process your message. Please try again."

        # Update session with new state
        _update_session(session_id, ai_response, body, reply_text)

        # Return TwiML response
        # Truncate to 1600 chars (WhatsApp limit)
        if len(reply_text) > 1600:
            reply_text = reply_text[:1597] + "..."

        # Escape XML special chars
        reply_text = (
            reply_text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

        twiml = f"<Response><Message>{reply_text}</Message></Response>"
        return _twiml_response(twiml, 200)

    except Exception as e:
        logger.exception(f"WhatsApp webhook error: {e}")
        error_msg = "Sorry, something went wrong. Please try again."
        return _twiml_response(
            f"<Response><Message>{error_msg}</Message></Response>", 200
        )


def _get_param(params: dict, key: str) -> str:
    """Extract a single value from form-encoded params."""
    values = params.get(key, [])
    return values[0] if values else ""


def _get_or_create_session(phone: str, profile_name: str) -> dict:
    """Look up existing session by phone number, or create a new one.

    Sessions are keyed by a hash of the phone number for privacy.
    We use a deterministic session ID so the same phone always maps
    to the same session (stateful conversation).
    """
    # Deterministic session ID from phone number
    session_id = f"wa-{hashlib.sha256(phone.encode()).hexdigest()[:16]}"

    try:
        result = _sessions_table.get_item(Key={"sessionId": session_id})
        if "Item" in result:
            return result["Item"]
    except Exception as e:
        logger.warning(f"Session lookup failed: {e}")

    # Create new session
    now = datetime.now(timezone.utc).isoformat()
    session = {
        "sessionId": session_id,
        "channel": "whatsapp",
        "phoneNumber": phone,
        "profileName": profile_name or "WhatsApp User",
        "language": "hi-IN",  # Default to Hindi for India
        "conversationState": "GREETING",
        "conversationHistory": [],
        "userProfile": {},
        "matchedSchemes": [],
        "formData": {},
        "status": "active",
        "createdAt": now,
        "updatedAt": now,
        "ttl": int(time.time()) + 86400 * 7,  # 7-day TTL
    }

    try:
        _sessions_table.put_item(Item=session)
        logger.info(f"Created new WhatsApp session: {session_id} for {phone}")
    except Exception as e:
        logger.error(f"Failed to create session: {e}")

    return session


def _invoke_ai_engine(session_id: str, user_message: str, session: dict) -> dict:
    """Invoke the AI Engine Lambda to process the user's message."""
    payload = {
        "sessionId": session_id,
        "userMessage": user_message,
        "language": session.get("language", "hi-IN"),
        "conversationState": session.get("conversationState", "GREETING"),
        "conversationHistory": session.get("conversationHistory", [])[-20:],
        "userProfile": session.get("userProfile", {}),
        "matchedSchemes": session.get("matchedSchemes", []),
        "selectedScheme": session.get("selectedScheme"),
        "formData": session.get("formData", {}),
    }

    try:
        response = _lambda_client.invoke(
            FunctionName=AI_ENGINE_FUNCTION,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload, cls=DecimalEncoder),
        )
        result = json.loads(response["Payload"].read().decode("utf-8"))
        return result
    except Exception as e:
        logger.exception(f"AI Engine invocation failed: {e}")
        return {
            "response": "I'm having trouble processing your request. Please try again in a moment.",
            "conversationState": session.get("conversationState", "GREETING"),
        }


def _update_session(
    session_id: str,
    ai_response: dict,
    user_message: str,
    reply_text: str,
) -> None:
    """Update the session in DynamoDB with the new conversation turn."""
    now = datetime.now(timezone.utc).isoformat()

    # Build new history entries
    new_entries = [
        {"role": "user", "content": user_message, "timestamp": now},
        {"role": "assistant", "content": reply_text, "timestamp": now},
    ]

    update_expr = (
        "SET conversationHistory = list_append(if_not_exists(conversationHistory, :empty), :newEntries), "
        "conversationState = :state, "
        "updatedAt = :now, "
        "#ttl_attr = :ttl"
    )
    expr_values = {
        ":newEntries": new_entries,
        ":empty": [],
        ":state": ai_response.get("conversationState", "GREETING"),
        ":now": now,
        ":ttl": int(time.time()) + 86400 * 7,
    }
    expr_names = {"#ttl_attr": "ttl"}

    # Conditionally update matchedSchemes and userProfile if present
    if ai_response.get("matchedSchemes"):
        update_expr += ", matchedSchemes = :schemes"
        expr_values[":schemes"] = ai_response["matchedSchemes"]

    if ai_response.get("userProfile"):
        update_expr += ", userProfile = :profile"
        expr_values[":profile"] = ai_response["userProfile"]

    if ai_response.get("formData"):
        update_expr += ", formData = :form"
        expr_values[":form"] = ai_response["formData"]

    try:
        _sessions_table.update_item(
            Key={"sessionId": session_id},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_values,
            ExpressionAttributeNames=expr_names,
        )
    except Exception as e:
        logger.error(f"Session update failed: {e}")


def _twiml_response(body: str, status_code: int = 200) -> dict:
    """Return an API Gateway response with TwiML content type."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/xml",
            "Access-Control-Allow-Origin": "*",
        },
        "body": f'<?xml version="1.0" encoding="UTF-8"?>{body}',
    }
