"""Shared fixtures for VaaniSetu tests."""

import os
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── Fix Python path so Lambda code can be imported ───────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend" / "shared"))
sys.path.insert(0, str(ROOT / "backend" / "lambdas" / "ai_engine"))
sys.path.insert(0, str(ROOT / "backend" / "lambdas" / "orchestrator"))
sys.path.insert(0, str(ROOT / "backend" / "lambdas" / "voice_processor"))
sys.path.insert(0, str(ROOT / "backend" / "lambdas" / "notification"))
sys.path.insert(0, str(ROOT / "backend" / "lambdas" / "connect_handler"))
sys.path.insert(0, str(ROOT / "backend" / "lambdas" / "post_call"))


# ── Environment Variables ────────────────────────────────────────────
@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Set test environment variables."""
    monkeypatch.setenv("AWS_REGION", "ap-south-1")
    monkeypatch.setenv("SESSIONS_TABLE", "test-sessions")
    monkeypatch.setenv("SCHEMES_TABLE", "test-schemes")
    monkeypatch.setenv("APPLICATIONS_TABLE", "test-applications")
    monkeypatch.setenv("CONNECTIONS_TABLE", "test-connections")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
    monkeypatch.setenv("AUDIO_BUCKET", "test-audio-bucket")
    monkeypatch.setenv("SNS_TOPIC_ARN", "arn:aws:sns:ap-south-1:123456789012:test-topic")
    monkeypatch.setenv("AI_ENGINE_ARN", "arn:aws:lambda:ap-south-1:123456789012:function:test-ai")
    monkeypatch.setenv("VOICE_PROCESSOR_ARN", "arn:aws:lambda:ap-south-1:123456789012:function:test-voice")


# ── Sample Data ──────────────────────────────────────────────────────
@pytest.fixture
def sample_session():
    return {
        "sessionId": "test-session-123",
        "language": "hi-IN",
        "conversationState": "GREETING",
        "conversationHistory": [],
        "matchedSchemes": [],
        "userProfile": {},
        "formData": {},
        "formFieldsCompleted": 0,
        "formFieldsTotal": 0,
        "status": "active",
        "createdAt": "2025-01-01T00:00:00+00:00",
        "updatedAt": "2025-01-01T00:00:00+00:00",
        "ttl": 9999999999,
    }


@pytest.fixture
def sample_scheme():
    return {
        "schemeId": "pm_kisan",
        "name": {"en": "PM-KISAN", "hi": "पीएम-किसान", "ta": "பிஎம் கிசான்"},
        "description": {
            "en": "Income support to farmer families",
            "hi": "किसान परिवारों को आय सहायता",
        },
        "shortDescription": {
            "en": "₹6000/year for farmers",
            "hi": "किसानों के लिए ₹6000/वर्ष",
        },
        "category": "agriculture",
        "ministry": "Ministry of Agriculture",
        "isActive": True,
        "eligibility": {
            "min_age": 18,
            "max_income": 200000,
            "occupation": "farmer",
        },
        "eligibilityRules": [
            {"field": "age", "operator": "gte", "value": 18},
            {"field": "occupation", "operator": "eq", "value": "farmer"},
            {"field": "annual_income", "operator": "lte", "value": 200000},
        ],
        "benefits": {
            "amount": 6000,
            "description": {"en": "₹6000 per year", "hi": "₹6000 प्रति वर्ष"},
            "frequency": "annual",
        },
        "formFields": [
            {"id": "full_name", "type": "name", "question": {"en": "Full Name", "hi": "पूरा नाम"}, "required": True},
            {"id": "aadhaar", "type": "aadhaar", "question": {"en": "Aadhaar Number", "hi": "आधार संख्या"}, "required": True},
            {"id": "phone", "type": "phone", "question": {"en": "Phone Number", "hi": "फोन नंबर"}, "required": True},
            {"id": "land_size", "type": "land_size", "question": {"en": "Land Size (acres)", "hi": "भूमि (एकड़)"}, "required": True},
            {"id": "state", "type": "state", "question": {"en": "State", "hi": "राज्य"}, "required": True},
        ],
        "requiredDocuments": [
            {"id": "aadhaar_card", "name": {"en": "Aadhaar Card", "hi": "आधार कार्ड"}, "mandatory": True},
        ],
    }


@pytest.fixture
def sample_user_profile():
    return {
        "age": 35,
        "occupation": "farmer",
        "annual_income": 120000,
        "state": "Uttar Pradesh",
        "land_size": 2.5,
    }


@pytest.fixture
def api_gw_event():
    """Factory for API Gateway events."""
    def _event(method="POST", path="/sessions", body=None, path_params=None, query_params=None):
        return {
            "httpMethod": method,
            "path": path,
            "body": json.dumps(body) if body else None,
            "pathParameters": path_params,
            "queryStringParameters": query_params,
            "headers": {"Content-Type": "application/json"},
            "requestContext": {"requestId": "test-request-id"},
        }
    return _event


@pytest.fixture
def connect_event():
    """Factory for Amazon Connect Lambda events."""
    def _event(input_text="मुझे योजना चाहिए", language="hi-IN", session_id="test-session-123"):
        return {
            "Details": {
                "ContactData": {
                    "ContactId": "contact-123",
                    "Channel": "VOICE",
                    "CustomerEndpoint": {"Address": "+919876543210"},
                    "Attributes": {
                        "language": language,
                        "sessionId": session_id,
                    },
                },
                "Parameters": {
                    "InputText": input_text,
                },
            },
            "Name": "InvokeLambda",
        }
    return _event


@pytest.fixture
def mock_dynamodb():
    """Provide a mock DynamoDB table."""
    table = MagicMock()
    table.get_item.return_value = {"Item": None}
    table.put_item.return_value = {}
    table.update_item.return_value = {}
    table.scan.return_value = {"Items": [], "Count": 0}
    return table
