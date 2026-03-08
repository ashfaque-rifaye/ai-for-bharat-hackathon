"""Notification Lambda — SMS and notification dispatch.

Handles:
  - Application submission SMS confirmations
  - Status update notifications
  - Scheme match alerts
  - Document reminder notifications
"""

import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal

import boto3

from templates import get_template, DEFAULT_HELPLINE

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ.get("AWS_REGION", "us-east-1")
SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE", "vaanisetu-sessions")
APPLICATIONS_TABLE = os.environ.get("APPLICATIONS_TABLE", "vaanisetu-applications")

_sns = boto3.client("sns", region_name=REGION)
_dynamodb = boto3.resource("dynamodb", region_name=REGION)
_applications_table = _dynamodb.Table(APPLICATIONS_TABLE)


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


def handler(event, context):
    """
    Main handler — processes notification events.

    Supports direct invocation and SNS trigger:
      {
        "type": "application_submitted" | "status_update" | "scheme_match" | "documents_needed",
        "phone": "+91...",
        "language": "hi-IN",
        "data": { ... template variables ... }
      }
    """
    logger.info(f"Notification event: {json.dumps(event, cls=DecimalEncoder)[:500]}")

    try:
        # Handle SNS trigger
        if "Records" in event:
            for record in event["Records"]:
                message = json.loads(record["Sns"]["Message"])
                _process_notification(message)
            return {"statusCode": 200, "body": "OK"}

        # Handle direct invocation
        if isinstance(event, dict) and "type" in event:
            result = _process_notification(event)
            return {
                "statusCode": 200,
                "body": json.dumps(result, cls=DecimalEncoder),
            }

        # Handle batch notifications
        if isinstance(event, dict) and "notifications" in event:
            results = []
            for notification in event["notifications"]:
                results.append(_process_notification(notification))
            return {
                "statusCode": 200,
                "body": json.dumps({"results": results}, cls=DecimalEncoder),
            }

        return {"statusCode": 400, "body": "Invalid event format"}

    except Exception as e:
        logger.exception(f"Notification handler error: {e}")
        return {"statusCode": 500, "body": str(e)}


def _process_notification(notification: dict) -> dict:
    """Process a single notification."""
    notif_type = notification.get("type", "")
    phone = notification.get("phone", "")
    language = notification.get("language", "hi-IN")
    data = notification.get("data", {})

    if not phone:
        logger.error("Missing phone number in notification")
        return {"success": False, "error": "Missing phone number"}

    # Ensure phone has country code
    phone = _normalize_phone(phone)

    # Build SMS message from template
    message = get_template(notif_type, language, **data)

    if not message:
        logger.error(f"Unknown notification type: {notif_type}")
        return {"success": False, "error": f"Unknown type: {notif_type}"}

    # Send SMS
    result = _send_sms(phone, message)

    # Log notification to application record if applicable
    if data.get("application_id"):
        _log_notification(data["application_id"], notif_type, phone, result)

    return result


def _send_sms(phone: str, message: str) -> dict:
    """Send SMS via Amazon SNS."""
    try:
        response = _sns.publish(
            PhoneNumber=phone,
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

        message_id = response.get("MessageId", "")
        logger.info(f"SMS sent: {message_id} to {phone[:6]}***")

        return {
            "success": True,
            "messageId": message_id,
            "phone": f"{phone[:6]}***",
        }

    except _sns.exceptions.InvalidParameterException as e:
        logger.error(f"Invalid phone number {phone[:6]}***: {e}")
        return {"success": False, "error": "Invalid phone number"}
    except Exception as e:
        logger.exception(f"SMS send error: {e}")
        return {"success": False, "error": str(e)}


def _log_notification(application_id: str, notif_type: str, phone: str, result: dict):
    """Log notification event to application record."""
    try:
        _applications_table.update_item(
            Key={"applicationId": application_id},
            UpdateExpression=(
                "SET notifications = list_append(if_not_exists(notifications, :empty), :notif),"
                "    updatedAt = :now"
            ),
            ExpressionAttributeValues={
                ":notif": [{
                    "type": notif_type,
                    "phone": f"{phone[:6]}***",
                    "success": result.get("success", False),
                    "messageId": result.get("messageId", ""),
                    "sentAt": datetime.now(timezone.utc).isoformat(),
                }],
                ":empty": [],
                ":now": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception as e:
        logger.error(f"Failed to log notification: {e}")


def _normalize_phone(phone: str) -> str:
    """Ensure phone number has +91 country code."""
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone.startswith("+"):
        return phone
    if phone.startswith("91") and len(phone) == 12:
        return f"+{phone}"
    if len(phone) == 10:
        return f"+91{phone}"
    return f"+91{phone}"


# ── Convenience functions for direct invocation ───────────────────────

def send_application_confirmation(
    phone: str, application_id: str, scheme_name: str, language: str = "hi-IN"
) -> dict:
    """Send application submission confirmation SMS."""
    return _process_notification({
        "type": "application_submitted",
        "phone": phone,
        "language": language,
        "data": {
            "application_id": application_id,
            "scheme_name": scheme_name,
            "date": datetime.now(timezone.utc).strftime("%d/%m/%Y"),
        },
    })


def send_status_update(
    phone: str, application_id: str, scheme_name: str, status: str, language: str = "hi-IN"
) -> dict:
    """Send application status update SMS."""
    return _process_notification({
        "type": "status_update",
        "phone": phone,
        "language": language,
        "data": {
            "application_id": application_id,
            "scheme_name": scheme_name,
            "status": status,
        },
    })
