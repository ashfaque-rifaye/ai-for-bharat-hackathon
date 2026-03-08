"""VaaniSetu Utilities — Helper functions for validation, formatting, etc."""

import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

try:
    from .constants import FieldType, INDIAN_STATES, SESSION_TTL_SECONDS
except ImportError:
    from constants import FieldType, INDIAN_STATES, SESSION_TTL_SECONDS


def get_ttl(seconds: int = SESSION_TTL_SECONDS) -> int:
    """Generate a TTL epoch timestamp."""
    return int(time.time()) + seconds


def mask_aadhaar(aadhaar: str) -> str:
    """Mask Aadhaar number for display: XXXX-XXXX-1234."""
    digits = re.sub(r"\D", "", aadhaar)
    if len(digits) == 12:
        return f"XXXX-XXXX-{digits[-4:]}"
    return "XXXX-XXXX-XXXX"


def mask_phone(phone: str) -> str:
    """Mask phone number: +91XXXXX6789."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) >= 10:
        return f"+91XXXXX{digits[-4:]}"
    return "+91XXXXXXXXXX"


def mask_bank_account(account: str) -> str:
    """Mask bank account: XXXXXXXX5678."""
    digits = re.sub(r"\D", "", account)
    if len(digits) >= 4:
        return f"{'X' * (len(digits) - 4)}{digits[-4:]}"
    return "XXXXXXXXXXXX"


def validate_aadhaar(value: str) -> tuple[bool, str]:
    """Validate Aadhaar number (12 digits, Verhoeff checksum optional)."""
    digits = re.sub(r"[\s\-]", "", value)
    if not digits.isdigit():
        return False, "Aadhaar should contain only digits"
    if len(digits) != 12:
        return False, "Aadhaar must be exactly 12 digits"
    if digits[0] == "0" or digits[0] == "1":
        return False, "Aadhaar cannot start with 0 or 1"
    return True, "Valid"


def validate_phone(value: str) -> tuple[bool, str]:
    """Validate Indian phone number."""
    digits = re.sub(r"[\s\-\+]", "", value)
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    if not digits.isdigit():
        return False, "Phone number should contain only digits"
    if len(digits) != 10:
        return False, "Phone number must be 10 digits"
    if digits[0] not in "6789":
        return False, "Indian phone numbers start with 6, 7, 8, or 9"
    return True, "Valid"


def validate_ifsc(value: str) -> tuple[bool, str]:
    """Validate IFSC code."""
    value = value.strip().upper()
    if not re.match(r"^[A-Z]{4}0[A-Z0-9]{6}$", value):
        return False, "IFSC must be 11 characters: 4 letters, 0, then 6 alphanumeric"
    return True, "Valid"


def validate_pincode(value: str) -> tuple[bool, str]:
    """Validate Indian PIN code."""
    digits = re.sub(r"\s", "", value)
    if not digits.isdigit() or len(digits) != 6:
        return False, "PIN code must be exactly 6 digits"
    if digits[0] == "0":
        return False, "PIN code cannot start with 0"
    return True, "Valid"


def validate_name(value: str) -> tuple[bool, str]:
    """Validate a name field (allows Hindi/Tamil/English characters)."""
    if not value or len(value.strip()) < 2:
        return False, "Name must be at least 2 characters"
    if len(value) > 100:
        return False, "Name is too long"
    return True, "Valid"


def validate_date(value: str) -> tuple[bool, str]:
    """Validate date in DD/MM/YYYY or DD-MM-YYYY format."""
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(value.strip(), fmt)
            if dt.year < 1900 or dt > datetime.now():
                return False, "Date seems invalid"
            return True, "Valid"
        except ValueError:
            continue
    return False, "Date must be in DD/MM/YYYY format"


def validate_amount(value: str) -> tuple[bool, str]:
    """Validate an amount (numeric, potentially with commas)."""
    cleaned = re.sub(r"[,\s₹]", "", value)
    try:
        amt = float(cleaned)
        if amt < 0:
            return False, "Amount cannot be negative"
        return True, "Valid"
    except ValueError:
        return False, "Please enter a valid number"


def validate_state(value: str) -> tuple[bool, str]:
    """Validate Indian state name."""
    normalized = value.strip().title()
    if normalized in INDIAN_STATES:
        return True, "Valid"
    # Fuzzy match
    for state in INDIAN_STATES:
        if normalized.lower() in state.lower() or state.lower() in normalized.lower():
            return True, state  # Return the correct state name
    return False, f"'{value}' is not a recognized Indian state"


def validate_field(field_type: str, value: str) -> tuple[bool, str]:
    """Route field validation based on type."""
    validators = {
        FieldType.AADHAAR: validate_aadhaar,
        FieldType.PHONE: validate_phone,
        FieldType.IFSC: validate_ifsc,
        FieldType.PINCODE: validate_pincode,
        FieldType.NAME: validate_name,
        FieldType.DATE: validate_date,
        FieldType.AMOUNT: validate_amount,
        FieldType.STATE: validate_state,
    }
    validator = validators.get(field_type, lambda v: (True, "Valid"))
    return validator(value)


def format_currency(amount: int | float) -> str:
    """Format Indian currency: 1,23,456."""
    s = str(int(amount))
    if len(s) <= 3:
        return f"₹{s}"
    last3 = s[-3:]
    rest = s[:-3]
    # Add commas every 2 digits for Indian numbering
    parts = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    return f"₹{','.join(parts)},{last3}"


def clean_for_dynamodb(obj: dict) -> dict:
    """Remove None values and convert sets/tuples for DynamoDB compatibility."""
    cleaned = {}
    for key, value in obj.items():
        if value is None:
            continue
        if isinstance(value, dict):
            cleaned[key] = clean_for_dynamodb(value)
        elif isinstance(value, list):
            cleaned[key] = [
                clean_for_dynamodb(v) if isinstance(v, dict) else v
                for v in value
                if v is not None
            ]
        else:
            cleaned[key] = value
    return cleaned
