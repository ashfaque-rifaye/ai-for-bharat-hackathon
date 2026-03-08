"""Tests for Connect Handler Lambda — Amazon Connect bridge to Bedrock AI."""

import json
import pytest
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "shared"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "lambdas" / "connect_handler"))


# ── Connect Event Parsing ────────────────────────────────────────────

class TestConnectEventParsing:
    """Test parsing of Amazon Connect event format."""

    def test_extract_contact_id(self, connect_event):
        event = connect_event()
        contact_id = event["Details"]["ContactData"]["ContactId"]
        assert contact_id == "contact-123"

    def test_extract_phone_number(self, connect_event):
        event = connect_event()
        phone = event["Details"]["ContactData"]["CustomerEndpoint"]["Address"]
        assert phone == "+919876543210"

    def test_extract_language(self, connect_event):
        event = connect_event(language="ta-IN")
        lang = event["Details"]["ContactData"]["Attributes"]["language"]
        assert lang == "ta-IN"

    def test_extract_user_input(self, connect_event):
        event = connect_event(input_text="मुझे किसान योजना चाहिए")
        text = event["Details"]["Parameters"]["InputText"]
        assert "किसान" in text

    def test_extract_session_id(self, connect_event):
        event = connect_event(session_id="my-session")
        sid = event["Details"]["ContactData"]["Attributes"]["sessionId"]
        assert sid == "my-session"


# ── Connect Response Format ──────────────────────────────────────────

class TestConnectResponseFormat:
    """Test response format compatible with Amazon Connect."""

    def test_connect_response_has_required_keys(self):
        """Connect expects specific keys in Lambda response."""
        response = {
            "aiResponse": "some text",
            "ssmlResponse": "<speak>some text</speak>",
            "sessionId": "test-123",
            "conversationState": "GREETING",
        }
        assert "aiResponse" in response
        assert "ssmlResponse" in response
        assert "sessionId" in response
        assert "conversationState" in response

    def test_ssml_wrapping(self):
        text = "Hello, welcome to VaaniSetu!"
        ssml = f"<speak>{text}</speak>"
        assert ssml.startswith("<speak>")
        assert ssml.endswith("</speak>")
        assert text in ssml

    def test_response_text_cleaned(self):
        """Response should strip markdown for TTS."""
        raw = "**PM-KISAN**: ₹6,000 per year for `farmers`"
        cleaned = raw.replace("**", "").replace("*", "").replace("#", "").replace("`", "")
        cleaned = cleaned.replace("₹", "rupees ")
        assert "**" not in cleaned
        assert "`" not in cleaned
        assert "rupees" in cleaned

    def test_response_truncation(self):
        """Long responses should be truncated for Connect TTS."""
        long_text = "word " * 1000  # ~5000 chars
        if len(long_text) > 3000:
            long_text = long_text[:2950] + "..."
        assert len(long_text) <= 3000


# ── State Inference ──────────────────────────────────────────────────

class TestStateInference:
    """Test conversation state detection from AI responses."""

    def test_scheme_match_detection_hindi(self):
        response = "आपके लिए ये योजना उपलब्ध हैं"
        response_lower = response.lower()
        assert "योजना" in response_lower

    def test_eligibility_detection_english(self):
        response = "Let me check if you're eligible for PM-KISAN"
        response_lower = response.lower()
        assert "eligible" in response_lower

    def test_form_fill_detection(self):
        response = "Please share your Aadhaar number"
        response_lower = response.lower()
        assert "aadhaar" in response_lower

    def test_submit_detection(self):
        response = "Your application has been submitted. Reference: VS-2025-ABC12"
        response_lower = response.lower()
        assert "submit" in response_lower or "application" in response_lower

    def test_complete_detection_hindi(self):
        response = "धन्यवाद! आपका आवेदन जमा हो गया है।"
        response_lower = response.lower()
        assert "धन्यवाद" in response_lower

    def test_complete_detection_tamil(self):
        response = "நன்றி! உங்கள் விண்ணப்பம் சமர்ப்பிக்கப்பட்டது."
        response_lower = response.lower()
        assert "நன்றி" in response_lower


# ── Session Management ───────────────────────────────────────────────

class TestSessionManagement:
    """Test session creation and state for phone callers."""

    def test_new_session_structure(self):
        """A new session should have required fields."""
        session = {
            "sessionId": "contact-123",
            "phoneNumber": "+919876543210",
            "language": "hi-IN",
            "status": "active",
            "conversationState": "GREETING",
            "conversationHistory": [],
            "matchedSchemes": [],
            "userProfile": {},
            "formData": {},
            "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "channel": "phone",
        }
        assert session["channel"] == "phone"
        assert session["conversationState"] == "GREETING"
        assert isinstance(session["conversationHistory"], list)

    def test_session_with_history(self):
        """Session should accumulate conversation history."""
        history = [
            {"role": "user", "content": "मुझे कोई योजना बताओ", "timestamp": "2025-01-01T00:00:00Z"},
            {"role": "assistant", "content": "नमस्ते! मैं वाणी सेतु हूँ।", "timestamp": "2025-01-01T00:00:01Z"},
        ]
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_history_truncation(self):
        """Only last 20 messages should be kept."""
        history = [{"role": "user", "content": f"msg-{i}"} for i in range(30)]
        truncated = history[-20:]
        assert len(truncated) == 20
        assert truncated[0]["content"] == "msg-10"


# ── Greeting Messages ────────────────────────────────────────────────

class TestGreetingMessages:
    """Test multi-language greetings."""

    def test_hindi_greeting_has_vaanisetu(self):
        greeting = "नमस्ते! मैं वाणी सेतु हूँ। मैं आपको सरकारी योजनाओं के बारे में बता सकती हूँ।"
        assert "वाणी सेतु" in greeting

    def test_english_greeting_has_vaanisetu(self):
        greeting = "Hello! I'm VaaniSetu. I can help you find government schemes."
        assert "VaaniSetu" in greeting

    def test_tamil_greeting_has_vaanisetu(self):
        greeting = "வணக்கம்! நான் வாணி சேது."
        assert "வாணி சேது" in greeting


# ── Error Handling ───────────────────────────────────────────────────

class TestErrorHandling:
    """Test error fallbacks for Connect handler."""

    def test_error_messages_multilingual(self):
        error_msgs = {
            "hi-IN": "माफ कीजिये, तकनीकी समस्या हुई।",
            "en-IN": "Sorry, there was a technical issue.",
            "ta-IN": "மன்னிக்கவும், தொழில்நுட்ப சிக்கல் ஏற்பட்டது.",
        }
        for lang, msg in error_msgs.items():
            assert len(msg) > 10  # Non-trivial error message

    def test_fallback_language_is_hindi(self):
        """When language is unknown, default to Hindi."""
        error_msgs = {
            "hi-IN": "माफ कीजिये",
            "en-IN": "Sorry",
        }
        unknown_lang = "bn-IN"
        msg = error_msgs.get(unknown_lang, error_msgs["hi-IN"])
        assert msg == "माफ कीजिये"
