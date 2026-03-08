"""VaaniSetu Post-Call Handler — Analytics, follow-up SMS, and session cleanup.

Triggered after a Connect call ends to:
- Update session status to completed
- Send follow-up SMS with scheme info / application status
- Log call analytics (duration, state reached, schemes discussed)
- Schedule follow-up calls if needed
"""

import json
import os
import time
import traceback

import boto3

REGION = os.environ.get("AWS_REGION_NAME", "us-east-1")
dynamodb = boto3.resource("dynamodb", region_name=REGION)
sns = boto3.client("sns", region_name=REGION)

SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE", "vaanisetu-sessions")
APPLICATIONS_TABLE = os.environ.get("APPLICATIONS_TABLE", "vaanisetu-applications")

sessions_table = dynamodb.Table(SESSIONS_TABLE)
applications_table = dynamodb.Table(APPLICATIONS_TABLE)


# ── SMS Templates ────────────────────────────────────────────────────
SMS_TEMPLATES = {
    "call_summary_hi": (
        "वाणी सेतु: आपकी कॉल के लिए धन्यवाद!\n"
        "चर्चित योजनाएं: {schemes}\n"
        "{extra}\n"
        "दोबारा कॉल करें: {phone}"
    ),
    "call_summary_en": (
        "VaaniSetu: Thanks for calling!\n"
        "Schemes discussed: {schemes}\n"
        "{extra}\n"
        "Call again: {phone}"
    ),
    "call_summary_ta": (
        "வாணி சேது: உங்கள் அழைப்புக்கு நன்றி!\n"
        "விவாதிக்கப்பட்ட திட்டங்கள்: {schemes}\n"
        "{extra}\n"
        "மீண்டும் அழைக்கவும்: {phone}"
    ),
    "application_submitted_hi": "आवेदन संख्या: {app_id}\nयोजना: {scheme}\nस्थिति: जमा हो गया ✅",
    "application_submitted_en": "Application ID: {app_id}\nScheme: {scheme}\nStatus: Submitted ✅",
    "application_submitted_ta": "விண்ணப்ப எண்: {app_id}\nதிட்டம்: {scheme}\nநிலை: சமர்ப்பிக்கப்பட்டது ✅",
}

HELPLINE_NUMBER = "1800-XXX-XXXX"


def handler(event, context):
    """Post-call handler triggered by Connect or EventBridge."""
    print(f"Post-call event: {json.dumps(event)}")

    try:
        # Handle different event sources
        if "Details" in event:
            # Direct Connect trigger
            return _handle_connect_event(event)
        elif "source" in event and event["source"] == "aws.connect":
            # EventBridge Connect event
            return _handle_eventbridge_event(event)
        elif "Records" in event:
            # SNS/SQS trigger
            for record in event["Records"]:
                body = json.loads(record.get("body", record.get("Sns", {}).get("Message", "{}")))
                _process_post_call(body)
            return {"statusCode": 200}
        else:
            # Direct invocation
            return _process_post_call(event)

    except Exception as e:
        print(f"Post-call error: {traceback.format_exc()}")
        return {"statusCode": 500, "error": str(e)}


def _handle_connect_event(event: dict) -> dict:
    """Process Connect contact flow event."""
    contact_data = event.get("Details", {}).get("ContactData", {})
    contact_id = contact_data.get("ContactId", "")
    attributes = contact_data.get("Attributes", {})

    return _process_post_call({
        "sessionId": contact_id,
        "language": attributes.get("language", "hi-IN"),
    })


def _handle_eventbridge_event(event: dict) -> dict:
    """Process EventBridge Connect event (CONTACT_ENDED)."""
    detail = event.get("detail", {})
    contact_id = detail.get("contactId", "")

    return _process_post_call({
        "sessionId": contact_id,
        "eventType": detail.get("eventType", ""),
    })


def _process_post_call(data: dict) -> dict:
    """Main post-call processing logic."""
    session_id = data.get("sessionId", "")
    if not session_id:
        return {"statusCode": 400, "error": "No sessionId"}

    # Get session
    try:
        result = sessions_table.get_item(Key={"sessionId": session_id})
        session = result.get("Item")
    except Exception:
        session = None

    if not session:
        print(f"Session not found: {session_id}")
        return {"statusCode": 404, "error": "Session not found"}

    language = session.get("language", "hi-IN")
    phone_number = session.get("phoneNumber", "")
    matched_schemes = session.get("matchedSchemes", [])
    conversation_state = session.get("conversationState", "")
    application_id = session.get("applicationId")

    # 1. Update session status
    _complete_session(session_id)

    # 2. Log analytics
    analytics = _compute_analytics(session)
    print(f"Call analytics: {json.dumps(analytics)}")

    # 3. Send follow-up SMS
    if phone_number and phone_number != "unknown":
        _send_followup_sms(
            phone_number=phone_number,
            language=language,
            matched_schemes=matched_schemes,
            application_id=application_id,
            conversation_state=conversation_state,
        )

    return {
        "statusCode": 200,
        "analytics": analytics,
    }


def _complete_session(session_id: str):
    """Mark session as completed."""
    try:
        sessions_table.update_item(
            Key={"sessionId": session_id},
            UpdateExpression="SET #s = :s, updatedAt = :u, completedAt = :c",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":s": "completed",
                ":u": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                ":c": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        )
    except Exception as e:
        print(f"Error completing session: {e}")


def _compute_analytics(session: dict) -> dict:
    """Compute call analytics from session data."""
    history = session.get("conversationHistory", [])
    created = session.get("createdAt", "")

    return {
        "sessionId": session.get("sessionId"),
        "channel": session.get("channel", "phone"),
        "language": session.get("language"),
        "messageCount": len(history),
        "userMessages": sum(1 for m in history if m.get("role") == "user"),
        "finalState": session.get("conversationState"),
        "schemesMatched": len(session.get("matchedSchemes", [])),
        "applicationSubmitted": bool(session.get("applicationId")),
        "startTime": created,
    }


def _send_followup_sms(
    phone_number: str,
    language: str,
    matched_schemes: list,
    application_id: str | None,
    conversation_state: str,
):
    """Send follow-up SMS to the caller."""
    lang_suffix = {"hi-IN": "hi", "en-IN": "en", "ta-IN": "ta"}.get(language, "hi")

    # Build schemes list
    scheme_names = ", ".join(matched_schemes[:3]) if matched_schemes else "N/A"

    # Determine extra info based on state
    extra = ""
    if application_id:
        app_template_key = f"application_submitted_{lang_suffix}"
        if app_template_key in SMS_TEMPLATES:
            extra = SMS_TEMPLATES[app_template_key].format(
                app_id=application_id,
                scheme=matched_schemes[0] if matched_schemes else "N/A",
            )
    elif conversation_state in ("NEED_ASSESSMENT", "SCHEME_MATCH"):
        extra_msgs = {
            "hi": "अधिक जानकारी के लिए दोबारा कॉल करें।",
            "en": "Call again to continue your scheme search.",
            "ta": "மேலும் தகவலுக்கு மீண்டும் அழைக்கவும்.",
        }
        extra = extra_msgs.get(lang_suffix, extra_msgs["hi"])

    # Build SMS
    template_key = f"call_summary_{lang_suffix}"
    message = SMS_TEMPLATES.get(template_key, SMS_TEMPLATES["call_summary_hi"]).format(
        schemes=scheme_names,
        extra=extra,
        phone=HELPLINE_NUMBER,
    )

    # Send via SNS
    try:
        sns.publish(
            PhoneNumber=phone_number,
            Message=message,
            MessageAttributes={
                "AWS.SNS.SMS.SenderID": {
                    "DataType": "String",
                    "StringValue": "VaaniSetu",
                },
                "AWS.SNS.SMS.SMSType": {
                    "DataType": "String",
                    "StringValue": "Transactional",
                },
            },
        )
        print(f"SMS sent to {phone_number[:5]}***")
    except Exception as e:
        print(f"SMS send error: {e}")
