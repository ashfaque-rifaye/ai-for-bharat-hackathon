"""Tests for Pydantic data models."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "shared"))

from models import (
    Session,
    ConversationMessage,
    Scheme,
    Application,
    CreateSessionRequest,
    SendMessageRequest,
    generate_session_id,
    generate_application_id,
    utc_now_iso,
)
from constants import (
    ConversationState,
    Language,
    SessionStatus,
    ApplicationStatus,
    SchemeCategory,
)


class TestGenerateIds:
    def test_session_id_is_uuid(self):
        sid = generate_session_id()
        assert len(sid) == 36  # UUID format
        assert sid.count("-") == 4

    def test_application_id_format(self):
        aid = generate_application_id()
        assert aid.startswith("VS-")
        parts = aid.split("-")
        assert len(parts) == 3
        assert parts[1].isdigit()  # year

    def test_unique_session_ids(self):
        ids = {generate_session_id() for _ in range(100)}
        assert len(ids) == 100

    def test_utc_now_iso(self):
        ts = utc_now_iso()
        assert "T" in ts
        assert "+" in ts or "Z" in ts


class TestSessionModel:
    def test_default_session(self):
        session = Session()
        assert session.sessionId
        assert session.language == Language.HINDI
        assert session.status == SessionStatus.ACTIVE
        assert session.conversationState == ConversationState.GREETING
        assert session.conversationHistory == []
        assert session.matchedSchemes == []

    def test_session_with_phone(self):
        session = Session(phoneNumber="+919876543210")
        assert session.phoneNumber == "+919876543210"

    def test_session_serialization(self):
        session = Session(language=Language.ENGLISH)
        data = session.model_dump()
        assert data["language"] == "en-IN"
        assert data["status"] == "active"


class TestConversationMessage:
    def test_valid_user_message(self):
        msg = ConversationMessage(role="user", content="hello")
        assert msg.role == "user"
        assert msg.timestamp

    def test_valid_assistant_message(self):
        msg = ConversationMessage(role="assistant", content="namaste")
        assert msg.role == "assistant"

    def test_invalid_role_rejected(self):
        with pytest.raises(Exception):
            ConversationMessage(role="invalid", content="test")


class TestSchemeModel:
    def test_scheme_creation(self, sample_scheme):
        scheme = Scheme(**sample_scheme)
        assert scheme.schemeId == "pm_kisan"
        assert scheme.name.en == "PM-KISAN"
        assert scheme.category == SchemeCategory.AGRICULTURE
        assert scheme.isActive is True

    def test_scheme_with_rules(self, sample_scheme):
        scheme = Scheme(**sample_scheme)
        assert len(scheme.eligibilityRules) == 3
        assert scheme.eligibilityRules[0].field == "age"


class TestApplicationModel:
    def test_default_application(self):
        app = Application(sessionId="s-123", schemeId="pm_kisan")
        assert app.applicationId.startswith("VS-")
        assert app.status == ApplicationStatus.DRAFT
        assert app.formData == {}

    def test_submitted_application(self):
        app = Application(
            sessionId="s-123",
            schemeId="pm_kisan",
            status=ApplicationStatus.SUBMITTED,
            submittedAt="2025-01-01T00:00:00Z",
        )
        assert app.status == ApplicationStatus.SUBMITTED


class TestRequestModels:
    def test_create_session_defaults(self):
        req = CreateSessionRequest()
        assert req.language == Language.HINDI

    def test_create_session_english(self):
        req = CreateSessionRequest(language=Language.ENGLISH)
        assert req.language == Language.ENGLISH

    def test_send_message(self):
        req = SendMessageRequest(text="मुझे योजना चाहिए")
        assert req.text == "मुझे योजना चाहिए"


class TestConstants:
    def test_conversation_states(self):
        assert ConversationState.GREETING == "GREETING"
        assert ConversationState.COMPLETE == "COMPLETE"

    def test_languages(self):
        assert Language.HINDI == "hi-IN"
        assert Language.ENGLISH == "en-IN"
        assert Language.TAMIL == "ta-IN"

    def test_scheme_categories(self):
        assert SchemeCategory.AGRICULTURE == "agriculture"
        assert SchemeCategory.HEALTHCARE == "healthcare"
