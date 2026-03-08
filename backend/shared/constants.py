"""VaaniSetu Constants — Enums, language maps, and configuration."""

from enum import Enum


# ── Session States ───────────────────────────────────────────────────
class SessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class ConversationState(str, Enum):
    GREETING = "GREETING"
    NEED_ASSESSMENT = "NEED_ASSESSMENT"
    SCHEME_MATCH = "SCHEME_MATCH"
    ELIGIBILITY_CHECK = "ELIGIBILITY_CHECK"
    FORM_FILL = "FORM_FILL"
    REVIEW = "REVIEW"
    SUBMIT = "SUBMIT"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"


class ApplicationStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"


# ── Scheme Categories ────────────────────────────────────────────────
class SchemeCategory(str, Enum):
    AGRICULTURE = "agriculture"
    HOUSING = "housing"
    HEALTHCARE = "healthcare"
    FINANCE = "finance"
    EDUCATION = "education"
    FOOD = "food"
    ENERGY = "energy"
    SAVINGS = "savings"
    INSURANCE = "insurance"


# ── Supported Languages ─────────────────────────────────────────────
class Language(str, Enum):
    HINDI = "hi-IN"
    TAMIL = "ta-IN"
    ENGLISH = "en-IN"
    BENGALI = "bn-IN"
    TELUGU = "te-IN"
    MARATHI = "mr-IN"
    KANNADA = "kn-IN"
    MALAYALAM = "ml-IN"


# Transcribe language codes
TRANSCRIBE_LANGUAGE_MAP = {
    Language.HINDI: "hi-IN",
    Language.TAMIL: "ta-IN",
    Language.ENGLISH: "en-IN",
    Language.BENGALI: "bn-IN",
    Language.TELUGU: "te-IN",
    Language.MARATHI: "mr-IN",
    Language.KANNADA: "kn-IN",
    Language.MALAYALAM: "ml-IN",
}

# Polly voice mapping
# Note: Neural voices for Bengali/Telugu/Marathi/Kannada/Malayalam are limited.
# We use Kajal (Hindi neural) as fallback with AWS Translate for unsupported langs.
POLLY_VOICE_MAP = {
    Language.HINDI: {"VoiceId": "Kajal", "Engine": "neural", "LanguageCode": "hi-IN"},
    Language.ENGLISH: {"VoiceId": "Kajal", "Engine": "neural", "LanguageCode": "en-IN"},
    Language.TAMIL: {"VoiceId": "Kajal", "Engine": "neural", "LanguageCode": "hi-IN"},  # Fallback via translate
    Language.BENGALI: {"VoiceId": "Kajal", "Engine": "neural", "LanguageCode": "hi-IN"},  # Fallback via translate
    Language.TELUGU: {"VoiceId": "Kajal", "Engine": "neural", "LanguageCode": "hi-IN"},  # Fallback via translate
    Language.MARATHI: {"VoiceId": "Kajal", "Engine": "neural", "LanguageCode": "hi-IN"},  # Fallback via translate
    Language.KANNADA: {"VoiceId": "Kajal", "Engine": "neural", "LanguageCode": "hi-IN"},  # Fallback via translate
    Language.MALAYALAM: {"VoiceId": "Kajal", "Engine": "neural", "LanguageCode": "hi-IN"},  # Fallback via translate
}

# ── Field Types for Validation ───────────────────────────────────────
class FieldType(str, Enum):
    AADHAAR = "aadhaar"
    PHONE = "phone"
    IFSC = "ifsc"
    PINCODE = "pincode"
    NAME = "name"
    DATE = "date"
    AMOUNT = "amount"
    STATE = "state"
    DISTRICT = "district"
    OCCUPATION = "occupation"
    BANK_ACCOUNT = "bank_account"
    LAND_SIZE = "land_size"


# ── DynamoDB Table Names ─────────────────────────────────────────────
SESSIONS_TABLE = "vaanisetu-sessions"
SCHEMES_TABLE = "vaanisetu-schemes"
APPLICATIONS_TABLE = "vaanisetu-applications"
CONNECTIONS_TABLE = "vaanisetu-connections"

# ── AWS Configuration ────────────────────────────────────────────────
AWS_REGION = "us-east-1"

# Bedrock model IDs
BEDROCK_MODEL_HAIKU = "anthropic.claude-3-haiku-20240307-v1:0"
BEDROCK_MODEL_SONNET = "anthropic.claude-3-sonnet-20240229-v1:0"
DEFAULT_BEDROCK_MODEL = BEDROCK_MODEL_HAIKU  # Use Haiku for cost savings

# Session TTL: 90 days
SESSION_TTL_SECONDS = 90 * 24 * 60 * 60

# Connection TTL: 2 hours
CONNECTION_TTL_SECONDS = 2 * 60 * 60

# Indian states for validation
INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
    "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
]
