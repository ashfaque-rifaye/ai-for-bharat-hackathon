"""Session Manager — CRUD operations for VaaniSetu conversation sessions."""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger(__name__)

# Environment
SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE", "vaanisetu-sessions")
REGION = os.environ.get("AWS_REGION", "us-east-1")

# DynamoDB resource (reused across invocations)
_dynamodb = boto3.resource("dynamodb", region_name=REGION)
_table = _dynamodb.Table(SESSIONS_TABLE)

# Session TTL: 90 days
SESSION_TTL_SECONDS = 90 * 24 * 60 * 60


class DecimalEncoder(json.JSONEncoder):
    """Handle DynamoDB Decimal types in JSON serialization."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_ttl() -> int:
    import time
    return int(time.time()) + SESSION_TTL_SECONDS


def create_session(
    session_id: str,
    language: str = "hi-IN",
    phone_number: Optional[str] = None,
    connection_id: Optional[str] = None,
) -> dict:
    """Create a new conversation session."""
    now = _now_iso()
    session = {
        "sessionId": session_id,
        "language": language,
        "status": "active",
        "conversationState": "GREETING",
        "conversationHistory": [],
        "detectedIntent": None,
        "matchedSchemes": [],
        "selectedScheme": None,
        "userProfile": {},
        "formData": {},
        "formFieldsCompleted": 0,
        "formFieldsTotal": 0,
        "applicationId": None,
        "createdAt": now,
        "updatedAt": now,
        "ttl": _get_ttl(),
    }

    if phone_number:
        session["phoneNumber"] = phone_number
    if connection_id:
        session["connectionId"] = connection_id

    _table.put_item(Item=session)
    logger.info(f"Created session {session_id}, language={language}")
    return session


def get_session(session_id: str) -> Optional[dict]:
    """Retrieve a session by ID."""
    response = _table.get_item(Key={"sessionId": session_id})
    item = response.get("Item")
    if item:
        logger.debug(f"Retrieved session {session_id}")
    else:
        logger.warning(f"Session {session_id} not found")
    return item


def update_session(session_id: str, updates: dict[str, Any]) -> dict:
    """Update specific fields of a session."""
    updates["updatedAt"] = _now_iso()

    # Build update expression dynamically
    update_parts = []
    expr_names = {}
    expr_values = {}

    for i, (key, value) in enumerate(updates.items()):
        attr_name = f"#k{i}"
        attr_value = f":v{i}"
        update_parts.append(f"{attr_name} = {attr_value}")
        expr_names[attr_name] = key
        expr_values[attr_value] = value

    update_expression = "SET " + ", ".join(update_parts)

    response = _table.update_item(
        Key={"sessionId": session_id},
        UpdateExpression=update_expression,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
        ReturnValues="ALL_NEW",
    )

    logger.info(f"Updated session {session_id}: {list(updates.keys())}")
    return response.get("Attributes", {})


def add_message(session_id: str, role: str, content: str, language: Optional[str] = None) -> dict:
    """Append a message to the conversation history."""
    message = {
        "role": role,
        "content": content,
        "timestamp": _now_iso(),
    }
    if language:
        message["language"] = language

    response = _table.update_item(
        Key={"sessionId": session_id},
        UpdateExpression="SET conversationHistory = list_append(if_not_exists(conversationHistory, :empty), :msg), updatedAt = :now",
        ExpressionAttributeValues={
            ":msg": [message],
            ":empty": [],
            ":now": _now_iso(),
        },
        ReturnValues="ALL_NEW",
    )

    logger.debug(f"Added {role} message to session {session_id}")
    return response.get("Attributes", {})


def update_conversation_state(session_id: str, state: str) -> dict:
    """Update the conversation state machine state."""
    return update_session(session_id, {"conversationState": state})


def update_matched_schemes(session_id: str, scheme_ids: list[str]) -> dict:
    """Update the list of matched schemes."""
    return update_session(session_id, {"matchedSchemes": scheme_ids})


def update_form_progress(session_id: str, form_data: dict, completed: int, total: int) -> dict:
    """Update form filling progress."""
    return update_session(session_id, {
        "formData": form_data,
        "formFieldsCompleted": completed,
        "formFieldsTotal": total,
    })


def complete_session(session_id: str, application_id: Optional[str] = None) -> dict:
    """Mark session as completed."""
    updates = {"status": "completed", "conversationState": "COMPLETE"}
    if application_id:
        updates["applicationId"] = application_id
    return update_session(session_id, updates)


def get_sessions_by_phone(phone_number: str, limit: int = 10) -> list[dict]:
    """Get recent sessions for a phone number."""
    response = _table.query(
        IndexName="phone-index",
        KeyConditionExpression=Key("phoneNumber").eq(phone_number),
        ScanIndexForward=False,  # newest first
        Limit=limit,
    )
    return response.get("Items", [])


def delete_session(session_id: str) -> None:
    """Delete a session (for testing/admin)."""
    _table.delete_item(Key={"sessionId": session_id})
    logger.info(f"Deleted session {session_id}")
