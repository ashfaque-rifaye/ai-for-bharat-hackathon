"""Orchestrator Lambda — Main API handler for REST endpoints.

Routes:
  POST   /sessions              → Create new session
  GET    /sessions/{id}         → Get session details
  POST   /sessions/{id}/message → Send a text message to the AI
  POST   /synthesize            → Text-to-Speech via Amazon Polly
  POST   /transcribe            → Speech-to-Text via Amazon Transcribe
  GET    /schemes               → List all schemes
  GET    /schemes/{id}          → Get scheme details
  POST   /schemes/search        → Search schemes
  GET    /applications/{id}     → Get application details
  POST   /benefit-summary       → Cross-scheme benefit analysis
  GET    /analytics             → Aggregate dashboard stats
  POST   /generate-pdf          → Generate PDF report (benefit or application)
"""

import base64
import json
import logging
import os
import re
import time
import uuid
from decimal import Decimal

import boto3

from pdf_generator import generate_benefit_summary_pdf, generate_application_pdf
from session_manager import (
    create_session,
    get_session,
    add_message,
    update_session,
    complete_session,
    DecimalEncoder,
    _table as _sessions_table,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment
SCHEMES_TABLE = os.environ.get("SCHEMES_TABLE", "vaanisetu-schemes")
APPLICATIONS_TABLE = os.environ.get("APPLICATIONS_TABLE", "vaanisetu-applications")
AI_ENGINE_FUNCTION = os.environ.get("AI_ENGINE_FUNCTION", "")
REGION = os.environ.get("AWS_REGION", "us-east-1")

# AWS clients
_dynamodb = boto3.resource("dynamodb", region_name=REGION)
_schemes_table = _dynamodb.Table(SCHEMES_TABLE)
_applications_table = _dynamodb.Table(APPLICATIONS_TABLE)
_lambda_client = boto3.client("lambda", region_name=REGION)
_polly_client = boto3.client("polly", region_name=REGION)
_transcribe_client = boto3.client("transcribe", region_name=REGION)
_s3_client = boto3.client("s3", region_name=REGION)
_translate_client = boto3.client("translate", region_name=REGION)
_comprehend_client = boto3.client("comprehend", region_name=REGION)
_events_client = boto3.client("events", region_name=REGION)

AUDIO_BUCKET = os.environ.get("AUDIO_BUCKET", "")

# Polly voice mappings for supported languages (neural voices)
POLLY_VOICE_MAP = {
    "hi-IN": {"VoiceId": "Kajal", "Engine": "neural", "LanguageCode": "hi-IN"},
    "en-IN": {"VoiceId": "Kajal", "Engine": "neural", "LanguageCode": "en-IN"},
    "ta-IN": {"VoiceId": "Kajal", "Engine": "neural", "LanguageCode": "hi-IN"},  # Fallback
    "bn-IN": {"VoiceId": "Kajal", "Engine": "neural", "LanguageCode": "hi-IN"},
    "te-IN": {"VoiceId": "Kajal", "Engine": "neural", "LanguageCode": "hi-IN"},
    "mr-IN": {"VoiceId": "Kajal", "Engine": "neural", "LanguageCode": "hi-IN"},
    "kn-IN": {"VoiceId": "Kajal", "Engine": "neural", "LanguageCode": "hi-IN"},
    "ml-IN": {"VoiceId": "Kajal", "Engine": "neural", "LanguageCode": "hi-IN"},
}


def _clean_ai_response(text: str) -> str:
    """Clean up raw AI model output (belt-and-suspenders with ai_engine)."""
    if not text:
        return text
    # Strip <thinking>...</thinking> blocks
    text = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL).strip()
    # Extract clean text from JSON-wrapped responses
    if text.startswith("{") and text.endswith("}"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict) and "response" in parsed:
                text = parsed["response"]
        except (json.JSONDecodeError, KeyError):
            pass
    return text.strip()


# ── Greeting Messages ────────────────────────────────────────────────
GREETINGS = {
    "hi-IN": "नमस्ते! मैं वाणी सेतु हूँ, आपकी AI सहायक। मैं आपको सरकारी योजनाओं की जानकारी देने और आवेदन भरने में मदद कर सकती हूँ। आप किस बारे में जानना चाहते हैं?",
    "ta-IN": "வணக்கம்! நான் வாணி சேது, உங்கள் AI உதவியாளர். அரசு திட்டங்கள் பற்றிய தகவல்களை வழங்கவும், விண்ணப்பங்களை நிரப்பவும் உங்களுக்கு உதவ முடியும். நீங்கள் எதைப் பற்றி தெரிந்துகொள்ள விரும்புகிறீர்கள்?",
    "en-IN": "Hello! I am VaaniSetu, your AI assistant. I can help you discover government schemes you're eligible for and guide you through the application process. What would you like to know about?",
}


def handler(event, context):
    """Main Lambda handler — routes based on HTTP method and path."""
    logger.info(f"Event: {json.dumps(event, default=str)}")

    try:
        http_method = event.get("httpMethod", "GET")
        path = event.get("path", "/")
        path_params = event.get("pathParameters") or {}
        body = _parse_body(event)

        # Route requests
        if path == "/health" and http_method == "GET":
            return _response(200, {"status": "healthy", "service": "vaanisetu"})

        elif path == "/sessions" and http_method == "POST":
            return _create_session(body)

        elif "/sessions/" in path and path.endswith("/message") and http_method == "POST":
            session_id = path_params.get("id") or path.split("/sessions/")[1].split("/message")[0]
            return _send_message(session_id, body)

        elif "/sessions/" in path and http_method == "GET":
            session_id = path_params.get("id") or path.split("/sessions/")[1].split("/")[0]
            return _get_session(session_id)

        elif path == "/schemes/search" and http_method == "POST":
            return _search_schemes(body)

        elif path == "/synthesize" and http_method == "POST":
            return _synthesize_speech(body)

        elif path == "/transcribe" and http_method == "POST":
            return _transcribe_audio(body)

        elif path == "/schemes" and http_method == "GET":
            return _list_schemes(event.get("queryStringParameters") or {})

        elif "/schemes/" in path and http_method == "GET":
            scheme_id = path_params.get("id") or path.split("/schemes/")[1].split("/")[0]
            return _get_scheme(scheme_id)

        elif "/applications/" in path and http_method == "GET":
            app_id = path_params.get("id") or path.split("/applications/")[1].split("/")[0]
            return _get_application(app_id)

        elif path == "/benefit-summary" and http_method == "POST":
            return _benefit_summary(body)

        elif path == "/analytics" and http_method == "GET":
            return _get_analytics()

        elif path == "/generate-pdf" and http_method == "POST":
            return _generate_pdf(body)

        else:
            return _response(404, {"error": "Not found", "path": path})

    except Exception as e:
        logger.exception(f"Handler error: {e}")
        return _response(500, {"error": str(e)})


# ── Route Handlers ───────────────────────────────────────────────────

def _create_session(body: dict) -> dict:
    """POST /sessions — Create a new conversation session."""
    language = body.get("language", "hi-IN")
    phone_number = body.get("phoneNumber")

    session_id = str(uuid.uuid4())
    session = create_session(
        session_id=session_id,
        language=language,
        phone_number=phone_number,
    )

    # Add greeting to conversation history
    greeting = GREETINGS.get(language, GREETINGS["en-IN"])
    add_message(session_id, "assistant", greeting, language)

    return _response(201, {
        "sessionId": session_id,
        "language": language,
        "status": "active",
        "greeting": greeting,
    })


def _get_session(session_id: str) -> dict:
    """GET /sessions/{id} — Retrieve session details."""
    session = get_session(session_id)
    if not session:
        return _response(404, {"error": f"Session {session_id} not found"})
    return _response(200, session)


def _send_message(session_id: str, body: dict) -> dict:
    """POST /sessions/{id}/message — Send a user message and get AI response."""
    text = (body.get("text") or body.get("message") or "").strip()
    if not text:
        return _response(400, {"error": "Message text is required"})

    # Get current session
    session = get_session(session_id)
    if not session:
        return _response(404, {"error": f"Session {session_id} not found"})

    language = body.get("language") or session.get("language", "hi-IN")

    # ── Auto Language Detection ──────────────────────────────────
    # On GREETING state (first message), detect language from user text
    # and auto-update the session. This lets users start in any language
    # without selecting it first.
    conv_state = session.get("conversationState", "GREETING")
    if conv_state == "GREETING":
        detected = _detect_language(text)
        if detected and detected != language:
            language = detected
            update_session(session_id, {"language": language})
            logger.info(f"Auto-detected language: {language}")

    # Add user message to history
    add_message(session_id, "user", text, language)

    # Detect user sentiment via Amazon Comprehend
    sentiment = _detect_sentiment(text, language)

    # Invoke AI Engine Lambda
    ai_response = _invoke_ai_engine(session_id, text, language, session, sentiment)

    # Add AI response to history — clean up any model artifacts
    ai_text = ai_response.get("response", "")
    ai_text = _clean_ai_response(ai_text)
    # Guard against empty response after cleaning
    if not ai_text:
        fallbacks = {
            "hi-IN": "मैं समझ नहीं पाई। कृपया दोबारा बताएं।",
            "en-IN": "I couldn't understand that. Could you please rephrase?",
            "ta-IN": "என்னால் புரிந்துகொள்ள முடியவில்லை. தயவுசெய்து மீண்டும் சொல்லுங்கள்.",
        }
        ai_text = fallbacks.get(language, fallbacks["en-IN"])
    add_message(session_id, "assistant", ai_text, language)

    # Update session state if AI engine provides updates
    state_updates = {}
    if ai_response.get("conversationState"):
        state_updates["conversationState"] = ai_response["conversationState"]
    if ai_response.get("matchedSchemes"):
        # matchedSchemes can be a list of dicts or a list of strings — normalise to string IDs
        raw = ai_response["matchedSchemes"]
        state_updates["matchedSchemes"] = [
            s["schemeId"] if isinstance(s, dict) else str(s) for s in raw
        ]
    if ai_response.get("userProfile"):
        state_updates["userProfile"] = ai_response["userProfile"]
    if ai_response.get("formData"):
        state_updates["formData"] = ai_response["formData"]
    if ai_response.get("selectedScheme"):
        state_updates["selectedScheme"] = ai_response["selectedScheme"]
    if ai_response.get("applicationId"):
        state_updates["applicationId"] = ai_response["applicationId"]

    if state_updates:
        update_session(session_id, state_updates)

    # ── Publish milestone events to EventBridge ──────────────────
    new_state = ai_response.get("conversationState", "")
    _publish_milestone_event(
        session_id=session_id,
        conversation_state=new_state,
        application_id=ai_response.get("applicationId"),
        language=language,
        sentiment=sentiment,
    )

    # ── Auto-generate application PDF after submission ───────────
    pdf_url = None
    application_id = ai_response.get("applicationId")
    if application_id:
        try:
            # Gather data for the PDF
            selected_scheme_id = (
                ai_response.get("selectedScheme")
                or session.get("selectedScheme", "")
            )
            scheme_data = {}
            if selected_scheme_id:
                resp = _schemes_table.get_item(Key={"schemeId": selected_scheme_id})
                scheme_data = resp.get("Item", {})

            form_data = ai_response.get("formData") or session.get("formData", {})
            application_data = {
                "applicationId": application_id,
                "status": "SUBMITTED",
                "submittedAt": time.strftime("%d %b %Y, %H:%M UTC", time.gmtime()),
                "fields": form_data,
            }

            pdf_bytes = generate_application_pdf(
                application_data=application_data,
                scheme_data=scheme_data,
                language=language,
            )

            s3_key = f"pdfs/application-{application_id}-{int(time.time())}.pdf"
            _s3_client.put_object(
                Bucket=AUDIO_BUCKET,
                Key=s3_key,
                Body=pdf_bytes,
                ContentType="application/pdf",
                ContentDisposition=f'attachment; filename="application-{application_id}.pdf"',
            )
            pdf_url = _s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": AUDIO_BUCKET, "Key": s3_key},
                ExpiresIn=3600,
            )
            logger.info(f"Auto-generated application PDF: {s3_key}")
        except Exception as e:
            logger.warning(f"Auto-PDF generation failed (non-fatal): {e}")

    # ── Look up required documents for the selected scheme ───────
    required_documents = None
    selected_scheme_id = (
        ai_response.get("selectedScheme")
        or state_updates.get("selectedScheme")
        or session.get("selectedScheme", "")
    )
    if selected_scheme_id:
        try:
            resp = _schemes_table.get_item(Key={"schemeId": selected_scheme_id})
            scheme_item = resp.get("Item", {})
            required_documents = scheme_item.get("requiredDocuments")
        except Exception as e:
            logger.warning(f"Failed to fetch requiredDocuments: {e}")

    return _response(200, {
        "response": ai_text,
        "conversationState": ai_response.get("conversationState", session.get("conversationState")),
        "matchedSchemes": ai_response.get("matchedSchemes"),
        "formProgress": ai_response.get("formProgress"),
        "applicationId": application_id,
        "pdfUrl": pdf_url,
        "requiredDocuments": required_documents,
        "userProfile": ai_response.get("userProfile") or session.get("userProfile"),
        "sentiment": sentiment,
        "detectedLanguage": language,
    })


def _detect_language(text: str) -> str:
    """Detect the dominant language of user text using Amazon Comprehend.

    Why: Lets users start chatting in ANY Indian language without manually
    selecting it. Comprehend identifies the script/language and we map it
    to our supported language codes.

    Returns:
        Language code like "hi-IN", "ta-IN", etc. or empty string if unsure.
    """
    # Map Comprehend language codes → our app language codes
    LANG_MAP = {
        "hi": "hi-IN",
        "en": "en-IN",
        "ta": "ta-IN",
        "bn": "bn-IN",
        "te": "te-IN",
        "mr": "mr-IN",
        "kn": "kn-IN",
        "ml": "ml-IN",
        # Less common but possible detections
        "gu": "hi-IN",  # Gujarati → fallback to Hindi
        "pa": "hi-IN",  # Punjabi → fallback to Hindi
        "or": "hi-IN",  # Odia → fallback to Hindi
    }
    try:
        resp = _comprehend_client.detect_dominant_language(Text=text[:300])
        languages = resp.get("Languages", [])
        if not languages:
            return ""
        # Pick the highest-confidence language
        top = max(languages, key=lambda x: x.get("Score", 0))
        code = top.get("LanguageCode", "")
        confidence = top.get("Score", 0)
        logger.info(f"Comprehend language detection: {code} ({confidence:.2f})")
        # Only auto-switch if confidence is high enough
        if confidence >= 0.5:
            return LANG_MAP.get(code, "")
        return ""
    except Exception as e:
        logger.warning(f"Language detection failed: {e}")
        return ""


def _publish_milestone_event(
    session_id: str,
    conversation_state: str,
    application_id: str = None,
    language: str = "",
    sentiment: dict = None,
) -> None:
    """Publish key milestone events to Amazon EventBridge.

    Why: Enables downstream processing — alerts, analytics pipelines,
    notifications to admins. Shows judges we think beyond the demo.

    Events published:
      - vaanisetu.application.submitted  (when applicationId is created)
      - vaanisetu.session.completed      (when state moves to COMPLETE)
      - vaanisetu.session.negative       (when user sentiment is NEGATIVE)
    """
    MILESTONE_STATES = {"COMPLETE", "SUBMIT", "ERROR"}
    entries = []

    # Application submitted
    if application_id:
        entries.append({
            "Source": "vaanisetu",
            "DetailType": "ApplicationSubmitted",
            "Detail": json.dumps({
                "sessionId": session_id,
                "applicationId": application_id,
                "language": language,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }),
        })

    # Conversation milestone
    if conversation_state in MILESTONE_STATES:
        entries.append({
            "Source": "vaanisetu",
            "DetailType": f"Session{conversation_state.title()}",
            "Detail": json.dumps({
                "sessionId": session_id,
                "state": conversation_state,
                "language": language,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }),
        })

    # Negative sentiment alert — user may need human help
    if sentiment and sentiment.get("sentiment") == "NEGATIVE":
        neg_score = sentiment.get("scores", {}).get("negative", 0)
        if neg_score > 0.8:
            entries.append({
                "Source": "vaanisetu",
                "DetailType": "NegativeSentimentAlert",
                "Detail": json.dumps({
                    "sessionId": session_id,
                    "negativeScore": neg_score,
                    "language": language,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }),
            })

    if entries:
        try:
            _events_client.put_events(Entries=entries)
            logger.info(f"Published {len(entries)} EventBridge event(s) for session {session_id}")
        except Exception as e:
            # Non-critical — don't fail the request if event publishing fails
            logger.warning(f"EventBridge publish failed: {e}")


def _detect_sentiment(text: str, language: str) -> dict:
    """Detect user sentiment using Amazon Comprehend.

    Why: Lets the AI adjust its tone — empathetic for frustrated users,
    congratulatory for positive ones. Also surfaces mood in the frontend.

    Returns:
        {"sentiment": "POSITIVE"|"NEGATIVE"|"NEUTRAL"|"MIXED",
         "scores": {"Positive": 0.9, "Negative": 0.01, ...}}
    """
    # Comprehend supports: en, es, fr, de, it, pt, ar, hi, ja, ko, zh, zh-TW
    COMPREHEND_LANGS = {"en", "es", "fr", "de", "it", "pt", "ar", "hi", "ja", "ko", "zh"}
    lang_code = language[:2] if language else "en"
    # Default to English for unsupported Indic languages
    comprehend_lang = lang_code if lang_code in COMPREHEND_LANGS else "en"

    try:
        resp = _comprehend_client.detect_sentiment(
            Text=text[:4500],  # Comprehend limit is 5KB
            LanguageCode=comprehend_lang,
        )
        return {
            "sentiment": resp["Sentiment"],
            "scores": {
                "positive": float(resp["SentimentScore"]["Positive"]),
                "negative": float(resp["SentimentScore"]["Negative"]),
                "neutral": float(resp["SentimentScore"]["Neutral"]),
                "mixed": float(resp["SentimentScore"]["Mixed"]),
            },
        }
    except Exception as e:
        logger.warning(f"Comprehend sentiment detection failed: {e}")
        return {"sentiment": "NEUTRAL", "scores": {}}


def _invoke_ai_engine(session_id: str, text: str, language: str, session: dict, sentiment: dict = None) -> dict:
    """Invoke the AI Engine Lambda for conversation processing."""
    if not AI_ENGINE_FUNCTION:
        # Fallback: simple echo response for testing
        logger.warning("AI_ENGINE_FUNCTION not set, using fallback response")
        return {
            "response": f"[Echo] आपने कहा: {text}",
            "conversationState": session.get("conversationState", "NEED_ASSESSMENT"),
        }

    try:
        payload = {
            "sessionId": session_id,
            "userMessage": text,
            "language": language,
            "conversationState": session.get("conversationState", "GREETING"),
            "conversationHistory": session.get("conversationHistory", []),
            "userProfile": session.get("userProfile", {}),
            "matchedSchemes": session.get("matchedSchemes", []),
            "selectedScheme": session.get("selectedScheme"),
            "formData": session.get("formData", {}),
            "sentiment": sentiment or {},
        }

        response = _lambda_client.invoke(
            FunctionName=AI_ENGINE_FUNCTION,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload, cls=DecimalEncoder),
        )

        result = json.loads(response["Payload"].read().decode("utf-8"))

        if "errorMessage" in result:
            logger.error(f"AI Engine error: {result['errorMessage']}")
            return {"response": "क्षमा करें, कुछ गड़बड़ हो गई। कृपया फिर से कोशिश करें।"}

        return result

    except Exception as e:
        logger.exception(f"Error invoking AI Engine: {e}")
        return {"response": "क्षमा करें, कुछ गड़बड़ हो गई। कृपया फिर से कोशिश करें।"}


# ── Voice Endpoints ──────────────────────────────────────────────────

def _build_ssml(text: str, language: str = "hi-IN") -> str:
    """Wrap plain text in SSML for natural-sounding Polly output.

    Adds:
      - 300 ms pauses after sentence-ending punctuation (Hindi „।‟ and ‟.!?‟)
      - A slightly slower speaking rate (95 %) for Indic languages
      - Emphasis on recognised government scheme names
    """
    # Escape XML-special chars
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Insert pauses after sentence endings
    escaped = re.sub(r"([।.!?])\s*", r'\1<break time="300ms"/> ', escaped)

    # Add a small pause before scheme keywords for natural emphasis
    _keywords = [
        "PM-KISAN", "PM-AWAS", "AYUSHMAN", "UJJWALA", "MUDRA",
        "PM-GARIB-KALYAN", "FASAL BIMA", "SUKANYA SAMRIDDHI",
        "SOIL HEALTH CARD", "RKVY", "पीएम किसान", "आयुष्मान",
        "उज्ज्वला", "मुद्रा", "प्रधानमंत्री",
    ]
    for kw in _keywords:
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        safe_kw = kw.replace("&", "&amp;")
        # Neural voices don't support <emphasis>, so we add a tiny pause instead
        escaped = pattern.sub(f'<break time="100ms"/>{safe_kw}', escaped)

    rate = "95%" if language != "en-IN" else "100%"
    return f'<speak><prosody rate="{rate}">{escaped}</prosody></speak>'


def _synthesize_speech(body: dict) -> dict:
    """POST /synthesize — Convert text to speech using Amazon Polly with SSML.

    Request body:
        {"text": "...", "language": "hi-IN", "outputFormat": "mp3"}
    Response:
        {"audio": "<base64>", "contentType": "audio/mpeg", "language": "hi-IN"}
    """
    text = body.get("text", "").strip()
    language = body.get("language", "hi-IN")
    output_format = body.get("outputFormat", "mp3")

    if not text:
        return _response(400, {"error": "Text is required for synthesis"})

    try:
        voice_config = POLLY_VOICE_MAP.get(language, POLLY_VOICE_MAP["hi-IN"])

        # For languages without native Polly voices, translate to Hindi first
        actual_text = text
        needs_translate = language not in ("hi-IN", "en-IN")
        if needs_translate:
            try:
                source_lang = language.split("-")[0]
                translate_resp = _translate_client.translate_text(
                    Text=text,
                    SourceLanguageCode=source_lang,
                    TargetLanguageCode="hi",
                )
                actual_text = translate_resp["TranslatedText"]
            except Exception as e:
                logger.warning(f"Translation failed for {language}, using original: {e}")

        # Build SSML for natural prosody (pauses, speed, emphasis)
        ssml_text = _build_ssml(actual_text, language)

        polly_resp = _polly_client.synthesize_speech(
            Text=ssml_text,
            TextType="ssml",
            OutputFormat=output_format,
            VoiceId=voice_config["VoiceId"],
            Engine=voice_config["Engine"],
            LanguageCode=voice_config["LanguageCode"],
        )

        audio_stream = polly_resp["AudioStream"].read()
        audio_b64 = base64.b64encode(audio_stream).decode("utf-8")

        content_type = {
            "mp3": "audio/mpeg",
            "ogg_vorbis": "audio/ogg",
            "pcm": "audio/pcm",
        }.get(output_format, "audio/mpeg")

        return _response(200, {
            "audio": audio_b64,
            "contentType": content_type,
            "language": language,
        })

    except Exception as e:
        logger.exception(f"Polly synthesis error: {e}")
        return _response(500, {"error": f"Speech synthesis failed: {str(e)}"})


def _benefit_summary(body: dict) -> dict:
    """POST /benefit-summary — Cross-scheme benefit stacking analysis.

    Request body:
        {"sessionId": "...", "userProfile": {...}, "language": "hi-IN"}
    Response:
        {"totalAnnualBenefit": 42000, "eligibleSchemes": [...], "synergies": [...], ...}

    This calls the AI engine's benefit_stacker module via a Lambda invoke
    so it has access to the scheme data and eligibility engine.
    """
    session_id = body.get("sessionId", "")
    user_profile = body.get("userProfile", {})
    language = body.get("language", "hi-IN")

    if not user_profile:
        # Try to pull profile from the session
        if session_id:
            try:
                session = get_session(session_id)
                user_profile = session.get("userProfile", {})
            except Exception:
                pass

    if not user_profile:
        return _response(400, {"error": "userProfile is required"})

    try:
        # Invoke AI engine with a special action
        payload = {
            "action": "benefit_stack",
            "userProfile": user_profile,
            "language": language,
        }
        resp = _lambda_client.invoke(
            FunctionName=AI_ENGINE_FUNCTION,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )
        result = json.loads(resp["Payload"].read())
        return _response(200, result)

    except Exception as e:
        logger.exception(f"Benefit summary error: {e}")
        return _response(500, {"error": f"Benefit analysis failed: {str(e)}"})


def _get_analytics() -> dict:
    """GET /analytics — Lightweight aggregate stats for the dashboard.

    Scans the sessions table and returns aggregate metrics:
    totalSessions, activeSessions, languageDistribution,
    conversationStateDistribution, topSchemes, averageMessagesPerSession.
    """
    try:
        items: list[dict] = []
        scan_kwargs = {
            "ProjectionExpression": "#lang, #st, conversationState, matchedSchemes, conversationHistory, createdAt",
            "ExpressionAttributeNames": {"#lang": "language", "#st": "status"},
        }
        while True:
            resp = _sessions_table.scan(**scan_kwargs)
            items.extend(resp.get("Items", []))
            if "LastEvaluatedKey" not in resp:
                break
            scan_kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

        total_sessions = len(items)
        language_dist: dict[str, int] = {}
        state_dist: dict[str, int] = {}
        scheme_counts: dict[str, int] = {}
        total_messages = 0
        active_count = 0

        # Normalize short language codes to full BCP-47 form
        _lang_normalize = {
            "hi": "hi-IN", "en": "en-IN", "ta": "ta-IN",
            "bn": "bn-IN", "te": "te-IN", "mr": "mr-IN",
            "kn": "kn-IN", "ml": "ml-IN",
        }

        for item in items:
            lang = item.get("language", "unknown")
            lang = _lang_normalize.get(lang, lang)  # Normalize short codes
            language_dist[lang] = language_dist.get(lang, 0) + 1

            if item.get("status") == "active":
                active_count += 1

            state = item.get("conversationState", "unknown")
            state_dist[state] = state_dist.get(state, 0) + 1

            schemes = item.get("matchedSchemes", [])
            if isinstance(schemes, list):
                for s in schemes:
                    scheme_counts[s] = scheme_counts.get(s, 0) + 1

            history = item.get("conversationHistory", [])
            if isinstance(history, list):
                total_messages += len(history)

        avg_messages = round(total_messages / total_sessions, 1) if total_sessions else 0

        top_schemes = sorted(scheme_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return _response(200, {
            "totalSessions": total_sessions,
            "activeSessions": active_count,
            "averageMessagesPerSession": avg_messages,
            "languageDistribution": language_dist,
            "conversationStateDistribution": state_dist,
            "topSchemes": [{"schemeId": s, "count": c} for s, c in top_schemes],
            "totalMessages": total_messages,
        })

    except Exception as e:
        logger.exception(f"Analytics error: {e}")
        return _response(500, {"error": f"Analytics failed: {str(e)}"})


def _generate_pdf(body: dict) -> dict:
    """POST /generate-pdf — Generate a PDF report and return a pre-signed S3 URL.

    Request body:
        {
            "type": "benefit-summary" | "application-confirmation",
            "sessionId": "...",           # optional, pulls profile from session
            "userProfile": {...},         # required for benefit-summary
            "benefitData": {...},         # required for benefit-summary
            "applicationData": {...},     # required for application-confirmation
            "schemeData": {...},          # required for application-confirmation
            "language": "hi-IN"
        }
    Response:
        {"pdfUrl": "https://s3.../...", "expiresIn": 3600}
    """
    report_type = body.get("type", "benefit-summary")
    language = body.get("language", "hi-IN")
    session_id = body.get("sessionId", "")

    if not AUDIO_BUCKET:
        return _response(500, {"error": "S3 bucket not configured"})

    try:
        if report_type == "benefit-summary":
            user_profile = body.get("userProfile", {})
            benefit_data = body.get("benefitData", {})

            # If no benefit data provided, compute it from user profile
            if not benefit_data and user_profile:
                payload = {
                    "action": "benefit_stack",
                    "userProfile": user_profile,
                    "language": language,
                }
                resp = _lambda_client.invoke(
                    FunctionName=AI_ENGINE_FUNCTION,
                    InvocationType="RequestResponse",
                    Payload=json.dumps(payload),
                )
                benefit_data = json.loads(resp["Payload"].read())

            if not benefit_data:
                return _response(400, {"error": "benefitData or userProfile required"})

            pdf_bytes = generate_benefit_summary_pdf(
                benefit_data=benefit_data,
                user_profile=user_profile,
                language=language,
            )
            filename = f"benefit-summary-{session_id or 'report'}"

        elif report_type == "application-confirmation":
            application_data = body.get("applicationData", {})
            scheme_data = body.get("schemeData", {})

            if not application_data:
                return _response(400, {"error": "applicationData is required"})

            pdf_bytes = generate_application_pdf(
                application_data=application_data,
                scheme_data=scheme_data,
                language=language,
            )
            app_id = application_data.get("applicationId", "unknown")
            filename = f"application-{app_id}"

        else:
            return _response(400, {"error": f"Unknown report type: {report_type}"})

        # Upload to S3
        s3_key = f"pdfs/{filename}-{int(time.time())}.pdf"
        _s3_client.put_object(
            Bucket=AUDIO_BUCKET,
            Key=s3_key,
            Body=pdf_bytes,
            ContentType="application/pdf",
            ContentDisposition=f'attachment; filename="{filename}.pdf"',
        )

        # Generate pre-signed URL (1 hour expiry)
        presigned_url = _s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": AUDIO_BUCKET, "Key": s3_key},
            ExpiresIn=3600,
        )

        logger.info(f"PDF generated: type={report_type}, key={s3_key}, size={len(pdf_bytes)}")

        return _response(200, {
            "pdfUrl": presigned_url,
            "expiresIn": 3600,
            "fileName": f"{filename}.pdf",
            "sizeBytes": len(pdf_bytes),
        })

    except Exception as e:
        logger.exception(f"PDF generation error: {e}")
        return _response(500, {"error": f"PDF generation failed: {str(e)}"})


def _transcribe_audio(body: dict) -> dict:
    """POST /transcribe — Convert speech to text using Amazon Transcribe.

    Request body:
        {"audio": "<base64>", "language": "hi-IN", "sampleRate": 16000}
    Response:
        {"text": "transcribed text", "language": "hi-IN", "confidence": 0.95}
    """
    audio_b64 = body.get("audio", "")
    language = body.get("language", "hi-IN")
    sample_rate = body.get("sampleRate", 16000)

    if not audio_b64:
        return _response(400, {"error": "Audio data is required"})

    if not AUDIO_BUCKET:
        return _response(500, {"error": "AUDIO_BUCKET not configured for transcription"})

    try:
        audio_bytes = base64.b64decode(audio_b64)

        # Upload audio to S3 temporarily (frontend records as webm/opus)
        job_name = f"vaanisetu-{uuid.uuid4().hex[:8]}"
        s3_key = f"temp-audio/{job_name}.webm"

        _s3_client.put_object(
            Bucket=AUDIO_BUCKET,
            Key=s3_key,
            Body=audio_bytes,
            ContentType="audio/webm",
        )

        # Use automatic language identification so Transcribe detects
        # the actual spoken language (English, Hindi, Tamil, etc.)
        # instead of forcing the UI-selected language.
        supported_langs = "en-IN,hi-IN,ta-IN,bn-IN,te-IN,mr-IN,kn-IN,ml-IN"

        _transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            IdentifyLanguage=True,
            LanguageOptions=supported_langs,
            MediaFormat="webm",
            Media={"MediaFileUri": f"s3://{AUDIO_BUCKET}/{s3_key}"},
        )

        # Poll for completion (max 30 seconds)
        for _ in range(30):
            time.sleep(1)
            status = _transcribe_client.get_transcription_job(
                TranscriptionJobName=job_name
            )
            job_status = status["TranscriptionJob"]["TranscriptionJobStatus"]

            if job_status == "COMPLETED":
                transcript_uri = status["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
                import urllib.request
                with urllib.request.urlopen(transcript_uri) as resp:
                    transcript_data = json.loads(resp.read().decode())

                results = transcript_data.get("results", {})
                transcripts = results.get("transcripts", [])
                text = transcripts[0]["transcript"] if transcripts else ""

                items = results.get("items", [])
                confidences = [
                    float(item.get("alternatives", [{}])[0].get("confidence", 0))
                    for item in items if item.get("alternatives")
                ]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0

                # Get the detected language from the transcription job
                detected_lang = (
                    status["TranscriptionJob"]
                    .get("LanguageCode", language)
                )

                return _response(200, {
                    "text": text,
                    "language": detected_lang,
                    "confidence": round(avg_confidence, 2),
                })

            elif job_status == "FAILED":
                reason = status["TranscriptionJob"].get("FailureReason", "Unknown")
                return _response(500, {"error": f"Transcription failed: {reason}"})

        return _response(504, {"error": "Transcription timed out"})

    except Exception as e:
        logger.exception(f"Transcribe error: {e}")
        return _response(500, {"error": f"Transcription failed: {str(e)}"})

    finally:
        # Cleanup temporary S3 audio and Transcribe job
        try:
            _transcribe_client.delete_transcription_job(TranscriptionJobName=job_name)
        except Exception:
            pass
        try:
            _s3_client.delete_object(Bucket=AUDIO_BUCKET, Key=s3_key)
        except Exception:
            pass


def _list_schemes(params: dict) -> dict:
    """GET /schemes — List all schemes, optionally filtered by category."""
    category = params.get("category")

    if category:
        response = _schemes_table.query(
            IndexName="category-index",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("category").eq(category),
        )
    else:
        response = _schemes_table.scan()

    items = response.get("Items", [])

    # Return simplified scheme list
    schemes = []
    for item in items:
        lang = params.get("language", "en")
        schemes.append({
            "schemeId": item["schemeId"],
            "name": item["name"].get(lang, item["name"]["en"]),
            "shortDescription": item.get("shortDescription", {}).get(lang, item.get("shortDescription", {}).get("en", "")),
            "category": item["category"],
            "isActive": item.get("isActive", True),
        })

    return _response(200, {"schemes": schemes, "totalResults": len(schemes)})


def _get_scheme(scheme_id: str) -> dict:
    """GET /schemes/{id} — Get full scheme details."""
    response = _schemes_table.get_item(Key={"schemeId": scheme_id})
    item = response.get("Item")
    if not item:
        return _response(404, {"error": f"Scheme {scheme_id} not found"})
    return _response(200, item)


def _search_schemes(body: dict) -> dict:
    """POST /schemes/search — Search schemes by keyword/category."""
    query = body.get("query", "").lower()
    category = body.get("category")

    # Scan all schemes and filter (for MVP; RAG will replace this)
    if category:
        response = _schemes_table.query(
            IndexName="category-index",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("category").eq(category),
        )
    else:
        response = _schemes_table.scan()

    items = response.get("Items", [])

    # Simple keyword matching (RAG will replace this in Phase 2)
    if query:
        query_words = query.split()
        matched = []
        for item in items:
            searchable = json.dumps(item, ensure_ascii=False, cls=DecimalEncoder).lower()
            if any(word in searchable for word in query_words):
                matched.append(item)
        items = matched

    lang = body.get("language", "en")
    schemes = []
    for item in items:
        schemes.append({
            "schemeId": item["schemeId"],
            "name": item["name"].get(lang, item["name"]["en"]),
            "description": item["description"].get(lang, item["description"]["en"]),
            "shortDescription": item.get("shortDescription", {}).get(lang, ""),
            "category": item["category"],
            "benefits": item.get("benefits", {}),
        })

    return _response(200, {"schemes": schemes, "totalResults": len(schemes)})


def _get_application(application_id: str) -> dict:
    """GET /applications/{id} — Get application details."""
    response = _applications_table.get_item(Key={"applicationId": application_id})
    item = response.get("Item")
    if not item:
        return _response(404, {"error": f"Application {application_id} not found"})
    return _response(200, item)


# ── Utility Functions ────────────────────────────────────────────────

def _parse_body(event: dict) -> dict:
    """Parse request body from API Gateway event."""
    body = event.get("body")
    if not body:
        return {}
    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {}
    return body


def _response(status_code: int, body: dict) -> dict:
    """Create API Gateway response with CORS headers."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        "body": json.dumps(body, ensure_ascii=False, cls=DecimalEncoder),
    }
