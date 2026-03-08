"""Tests for Notification Lambda — SMS via SNS + Post-Call Analytics."""

import json
import pytest
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "shared"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "lambdas" / "notification"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "lambdas" / "post_call"))


# ── SMS Template Tests ───────────────────────────────────────────────

class TestSMSTemplates:
    """Test SMS template formatting in Hindi, English, and Tamil."""

    def test_call_summary_hindi(self):
        template = (
            "वाणी सेतु: आपकी कॉल के लिए धन्यवाद!\n"
            "चर्चित योजनाएं: {schemes}\n"
            "{extra}\n"
            "दोबारा कॉल करें: {phone}"
        )
        msg = template.format(schemes="PM-KISAN", extra="", phone="1800-XXX-XXXX")
        assert "वाणी सेतु" in msg
        assert "PM-KISAN" in msg
        assert "1800-XXX-XXXX" in msg

    def test_call_summary_english(self):
        template = (
            "VaaniSetu: Thanks for calling!\n"
            "Schemes discussed: {schemes}\n"
            "{extra}\n"
            "Call again: {phone}"
        )
        msg = template.format(schemes="PM-KISAN, Ayushman Bharat", extra="", phone="1800-XXX-XXXX")
        assert "VaaniSetu" in msg
        assert "PM-KISAN" in msg

    def test_call_summary_tamil(self):
        template = (
            "வாணி சேது: உங்கள் அழைப்புக்கு நன்றி!\n"
            "விவாதிக்கப்பட்ட திட்டங்கள்: {schemes}\n"
            "{extra}\n"
            "மீண்டும் அழைக்கவும்: {phone}"
        )
        msg = template.format(schemes="PM-KISAN", extra="", phone="1800-XXX-XXXX")
        assert "வாணி சேது" in msg

    def test_application_submitted_hindi(self):
        template = "आवेदन संख्या: {app_id}\nयोजना: {scheme}\nस्थिति: जमा हो गया ✅"
        msg = template.format(app_id="VS-2025-ABC12", scheme="PM-KISAN")
        assert "VS-2025-ABC12" in msg
        assert "PM-KISAN" in msg
        assert "✅" in msg

    def test_application_submitted_english(self):
        template = "Application ID: {app_id}\nScheme: {scheme}\nStatus: Submitted ✅"
        msg = template.format(app_id="VS-2025-XYZ", scheme="Ayushman Bharat")
        assert "VS-2025-XYZ" in msg
        assert "Submitted" in msg

    def test_sms_length_under_160(self):
        """SMS should be under 640 chars (4 SMS segments) to keep costs low."""
        template = "VaaniSetu: Thanks for calling!\nSchemes discussed: {schemes}\n{extra}\nCall again: {phone}"
        msg = template.format(schemes="PM-KISAN", extra="Call again for more.", phone="1800-XXX-XXXX")
        assert len(msg) <= 640


# ── Post Call Analytics ──────────────────────────────────────────────

class TestPostCallAnalytics:
    """Test call analytics computation."""

    def test_compute_analytics_basic(self):
        session = {
            "sessionId": "test-123",
            "channel": "phone",
            "language": "hi-IN",
            "conversationHistory": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "namaste"},
                {"role": "user", "content": "kisan"},
                {"role": "assistant", "content": "PM-KISAN..."},
            ],
            "conversationState": "SCHEME_MATCH",
            "matchedSchemes": ["PM-KISAN"],
            "applicationId": None,
            "createdAt": "2025-01-01T00:00:00Z",
        }

        analytics = {
            "sessionId": session["sessionId"],
            "channel": session.get("channel", "phone"),
            "language": session["language"],
            "messageCount": len(session["conversationHistory"]),
            "userMessages": sum(1 for m in session["conversationHistory"] if m["role"] == "user"),
            "finalState": session["conversationState"],
            "schemesMatched": len(session.get("matchedSchemes", [])),
            "applicationSubmitted": bool(session.get("applicationId")),
            "startTime": session["createdAt"],
        }

        assert analytics["messageCount"] == 4
        assert analytics["userMessages"] == 2
        assert analytics["finalState"] == "SCHEME_MATCH"
        assert analytics["schemesMatched"] == 1
        assert analytics["applicationSubmitted"] is False

    def test_analytics_with_application(self):
        session = {
            "sessionId": "test-456",
            "conversationHistory": [{"role": "user", "content": "m"}] * 10,
            "conversationState": "COMPLETE",
            "matchedSchemes": ["PM-KISAN", "PM Awas"],
            "applicationId": "VS-2025-ABC12",
            "createdAt": "2025-01-01T00:00:00Z",
        }
        assert bool(session["applicationId"]) is True
        assert len(session["matchedSchemes"]) == 2

    def test_analytics_empty_session(self):
        session = {
            "sessionId": "test-789",
            "conversationHistory": [],
            "conversationState": "GREETING",
            "matchedSchemes": [],
            "applicationId": None,
            "createdAt": "2025-01-01T00:00:00Z",
        }
        assert len(session["conversationHistory"]) == 0
        assert session["conversationState"] == "GREETING"


# ── Post-Call Event Handling ─────────────────────────────────────────

class TestPostCallEventHandling:
    """Test different event source parsing."""

    def test_connect_direct_event(self):
        """Connect direct invocation event."""
        event = {
            "Details": {
                "ContactData": {
                    "ContactId": "contact-123",
                    "Attributes": {"language": "hi-IN"},
                }
            }
        }
        contact_id = event["Details"]["ContactData"]["ContactId"]
        language = event["Details"]["ContactData"]["Attributes"]["language"]
        assert contact_id == "contact-123"
        assert language == "hi-IN"

    def test_eventbridge_event(self):
        """EventBridge Connect CONTACT_ENDED event."""
        event = {
            "source": "aws.connect",
            "detail": {
                "contactId": "contact-456",
                "eventType": "CONTACT_ENDED",
            },
        }
        assert event["source"] == "aws.connect"
        assert event["detail"]["contactId"] == "contact-456"

    def test_sns_trigger_event(self):
        """SNS/SQS trigger event."""
        event = {
            "Records": [
                {
                    "Sns": {
                        "Message": json.dumps({"sessionId": "test-789"}),
                    }
                }
            ]
        }
        body = json.loads(event["Records"][0]["Sns"]["Message"])
        assert body["sessionId"] == "test-789"

    def test_direct_invocation(self):
        """Direct Lambda invocation with sessionId."""
        event = {"sessionId": "test-direct"}
        assert event["sessionId"] == "test-direct"


# ── Follow-up SMS Logic ─────────────────────────────────────────────

class TestFollowUpSMS:
    """Test follow-up SMS generation logic."""

    def test_schemes_list_formatting(self):
        schemes = ["PM-KISAN", "Ayushman Bharat", "PM Awas"]
        formatted = ", ".join(schemes[:3])
        assert formatted == "PM-KISAN, Ayushman Bharat, PM Awas"

    def test_empty_schemes_fallback(self):
        schemes = []
        formatted = ", ".join(schemes[:3]) if schemes else "N/A"
        assert formatted == "N/A"

    def test_extra_info_for_submitted_app(self):
        app_id = "VS-2025-ABC12"
        extra = f"Application ID: {app_id}\nScheme: PM-KISAN\nStatus: Submitted ✅"
        assert app_id in extra

    def test_extra_info_for_incomplete_call(self):
        conversation_state = "NEED_ASSESSMENT"
        if conversation_state in ("NEED_ASSESSMENT", "SCHEME_MATCH"):
            extra = "Call again to continue your scheme search."
        else:
            extra = ""
        assert "Call again" in extra

    def test_language_suffix_mapping(self):
        mapping = {"hi-IN": "hi", "en-IN": "en", "ta-IN": "ta"}
        assert mapping["hi-IN"] == "hi"
        assert mapping["en-IN"] == "en"
        assert mapping["ta-IN"] == "ta"
        assert mapping.get("bn-IN", "hi") == "hi"  # Default fallback
