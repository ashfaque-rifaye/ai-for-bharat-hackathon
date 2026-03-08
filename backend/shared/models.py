"""VaaniSetu Data Models — Pydantic models for request/response validation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

try:
    from .constants import (
        ApplicationStatus,
        ConversationState,
        Language,
        SchemeCategory,
        SessionStatus,
    )
except ImportError:
    from constants import (
        ApplicationStatus,
        ConversationState,
        Language,
        SchemeCategory,
        SessionStatus,
    )


# ── Helper Functions ─────────────────────────────────────────────────
def generate_session_id() -> str:
    return str(uuid.uuid4())


def generate_application_id() -> str:
    year = datetime.now(timezone.utc).year
    short_id = uuid.uuid4().hex[:5].upper()
    return f"VS-{year}-{short_id}"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Conversation Message ─────────────────────────────────────────────
class ConversationMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    timestamp: str = Field(default_factory=utc_now_iso)
    language: Optional[str] = None


# ── Session Model ────────────────────────────────────────────────────
class Session(BaseModel):
    sessionId: str = Field(default_factory=generate_session_id)
    connectionId: Optional[str] = None
    phoneNumber: Optional[str] = None
    language: Language = Language.HINDI
    status: SessionStatus = SessionStatus.ACTIVE
    conversationState: ConversationState = ConversationState.GREETING
    conversationHistory: list[ConversationMessage] = Field(default_factory=list)
    detectedIntent: Optional[str] = None
    matchedSchemes: list[str] = Field(default_factory=list)
    selectedScheme: Optional[str] = None
    userProfile: dict[str, Any] = Field(default_factory=dict)
    formData: dict[str, Any] = Field(default_factory=dict)
    formFieldsCompleted: int = 0
    formFieldsTotal: int = 0
    applicationId: Optional[str] = None
    createdAt: str = Field(default_factory=utc_now_iso)
    updatedAt: str = Field(default_factory=utc_now_iso)
    ttl: Optional[int] = None


# ── Eligibility Rule ─────────────────────────────────────────────────
class EligibilityRule(BaseModel):
    field: str
    operator: str  # eq, neq, lt, lte, gt, gte, in, contains
    value: Any
    unit: Optional[str] = None


# ── Multilingual Text ────────────────────────────────────────────────
class MultiLangText(BaseModel):
    en: str
    hi: str
    ta: Optional[str] = None


# ── Form Field Definition ────────────────────────────────────────────
class FormField(BaseModel):
    id: str
    type: str  # text, aadhaar, phone, ifsc, pincode, date, amount, select
    question: MultiLangText
    required: bool = True
    validation: Optional[str] = None  # regex or field type for validation
    options: Optional[list[str]] = None  # For select type


# ── Required Document ────────────────────────────────────────────────
class RequiredDocument(BaseModel):
    id: str
    name: MultiLangText
    mandatory: bool = True


# ── Scheme Benefits ──────────────────────────────────────────────────
class SchemeBenefit(BaseModel):
    amount: Optional[int] = None
    description: MultiLangText
    frequency: Optional[str] = None  # annual, monthly, one-time


# ── Scheme Model ─────────────────────────────────────────────────────
class Scheme(BaseModel):
    schemeId: str
    name: MultiLangText
    description: MultiLangText
    shortDescription: MultiLangText
    category: SchemeCategory
    ministry: str
    eligibility: dict[str, Any] = Field(default_factory=dict)
    eligibilityRules: list[EligibilityRule] = Field(default_factory=list)
    benefits: SchemeBenefit
    requiredDocuments: list[RequiredDocument] = Field(default_factory=list)
    formFields: list[FormField] = Field(default_factory=list)
    deadline: Optional[str] = None
    isActive: bool = True
    updatedAt: str = Field(default_factory=utc_now_iso)


# ── Application Model ───────────────────────────────────────────────
class Application(BaseModel):
    applicationId: str = Field(default_factory=generate_application_id)
    sessionId: str
    phoneNumber: Optional[str] = None
    schemeId: str
    schemeName: Optional[str] = None
    formData: dict[str, Any] = Field(default_factory=dict)
    status: ApplicationStatus = ApplicationStatus.DRAFT
    submittedAt: Optional[str] = None
    smsHistory: list[dict[str, Any]] = Field(default_factory=list)
    createdAt: str = Field(default_factory=utc_now_iso)


# ── API Request/Response Models ──────────────────────────────────────
class CreateSessionRequest(BaseModel):
    language: Language = Language.HINDI
    phoneNumber: Optional[str] = None


class CreateSessionResponse(BaseModel):
    sessionId: str
    language: Language
    status: SessionStatus
    greeting: str


class SendMessageRequest(BaseModel):
    text: str
    language: Optional[Language] = None


class SendMessageResponse(BaseModel):
    response: str
    conversationState: ConversationState
    matchedSchemes: Optional[list[dict[str, Any]]] = None
    formProgress: Optional[dict[str, int]] = None
    applicationId: Optional[str] = None
    audio: Optional[str] = None  # Base64 encoded audio


class SchemeSearchRequest(BaseModel):
    query: str
    category: Optional[SchemeCategory] = None
    state: Optional[str] = None
    language: Language = Language.HINDI


class SchemeSearchResponse(BaseModel):
    schemes: list[dict[str, Any]]
    totalResults: int


class EligibilityCheckRequest(BaseModel):
    schemeId: str
    userProfile: dict[str, Any]


class EligibilityCheckResponse(BaseModel):
    eligible: bool
    confidence: int  # 0-100
    reason: str
    missingInfo: list[str] = Field(default_factory=list)


# ── WebSocket Message Models ─────────────────────────────────────────
class WSIncomingMessage(BaseModel):
    action: str  # startSession, audioChunk, endTurn, switchLanguage, endSession, message
    data: Optional[str] = None  # Base64 audio or text
    language: Optional[str] = None
    sessionId: Optional[str] = None


class WSOutgoingMessage(BaseModel):
    type: str  # languageDetected, transcription, aiResponse, schemeMatch, formProgress, applicationSubmitted, error
    data: Optional[dict[str, Any]] = None
    text: Optional[str] = None
    audio: Optional[str] = None  # Base64 encoded audio
    sessionId: Optional[str] = None
