"""Form Filler — Manages conversational form filling with validation."""

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


def validate_field(field_type: str, value: str) -> dict:
    """
    Validate a form field value.

    Returns:
        {"valid": True/False, "message": "...", "normalized": "cleaned_value"}
    """
    validators = {
        "aadhaar": _validate_aadhaar,
        "phone": _validate_phone,
        "ifsc": _validate_ifsc,
        "pincode": _validate_pincode,
        "name": _validate_name,
        "date": _validate_date,
        "amount": _validate_amount,
        "land_size": _validate_land_size,
        "bank_account": _validate_bank_account,
        "state": _validate_state,
        "text": _validate_text,
    }

    validator = validators.get(field_type, _validate_text)
    return validator(value)


def get_next_field(form_fields: list[dict], form_data: dict) -> Optional[dict]:
    """Get the next unfilled required form field."""
    for field in form_fields:
        if field.get("required", True) and field["id"] not in form_data:
            return field
    return None  # All fields filled


def get_form_progress(form_fields: list[dict], form_data: dict) -> dict:
    """Get form completion progress."""
    required_fields = [f for f in form_fields if f.get("required", True)]
    total = len(required_fields)
    completed = sum(1 for f in required_fields if f["id"] in form_data)
    return {
        "completed": completed,
        "total": total,
        "percentage": int((completed / total) * 100) if total > 0 else 0,
        "remaining": total - completed,
    }


def format_form_summary(form_fields: list[dict], form_data: dict, language: str = "en") -> str:
    """Format form data for review, with PII masking."""
    lines = []
    for field in form_fields:
        if field["id"] in form_data:
            question = field["question"].get(language, field["question"].get("en", field["id"]))
            value = form_data[field["id"]]

            # Mask sensitive fields
            if field["type"] == "aadhaar":
                value = _mask_aadhaar(str(value))
            elif field["type"] == "bank_account":
                value = _mask_bank_account(str(value))

            lines.append(f"• {question}: {value}")
    return "\n".join(lines)


# ── Validators ───────────────────────────────────────────────────────

def _validate_aadhaar(value: str) -> dict:
    digits = re.sub(r"[\s\-]", "", value)
    if not digits.isdigit():
        return {"valid": False, "message": "Aadhaar should contain only numbers", "normalized": value}
    if len(digits) != 12:
        return {"valid": False, "message": "Aadhaar must be exactly 12 digits", "normalized": value}
    if digits[0] in "01":
        return {"valid": False, "message": "Aadhaar cannot start with 0 or 1", "normalized": value}
    formatted = f"{digits[:4]}-{digits[4:8]}-{digits[8:]}"
    return {"valid": True, "message": "Valid Aadhaar number", "normalized": formatted}


def _validate_phone(value: str) -> dict:
    digits = re.sub(r"[\s\-\+]", "", value)
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    if not digits.isdigit():
        return {"valid": False, "message": "Phone number should contain only digits", "normalized": value}
    if len(digits) != 10:
        return {"valid": False, "message": "Phone number must be 10 digits", "normalized": value}
    if digits[0] not in "6789":
        return {"valid": False, "message": "Indian numbers start with 6, 7, 8, or 9", "normalized": value}
    return {"valid": True, "message": "Valid phone number", "normalized": f"+91{digits}"}


def _validate_ifsc(value: str) -> dict:
    cleaned = value.strip().upper()
    if not re.match(r"^[A-Z]{4}0[A-Z0-9]{6}$", cleaned):
        return {"valid": False, "message": "IFSC must be 11 characters: 4 letters, 0, then 6 alphanumeric", "normalized": value}
    return {"valid": True, "message": "Valid IFSC code", "normalized": cleaned}


def _validate_pincode(value: str) -> dict:
    digits = re.sub(r"\s", "", value)
    if not digits.isdigit() or len(digits) != 6:
        return {"valid": False, "message": "PIN code must be exactly 6 digits", "normalized": value}
    if digits[0] == "0":
        return {"valid": False, "message": "PIN code cannot start with 0", "normalized": value}
    return {"valid": True, "message": "Valid PIN code", "normalized": digits}


def _validate_name(value: str) -> dict:
    if not value or len(value.strip()) < 2:
        return {"valid": False, "message": "Name must be at least 2 characters", "normalized": value}
    if len(value) > 100:
        return {"valid": False, "message": "Name seems too long", "normalized": value}
    return {"valid": True, "message": "Valid name", "normalized": value.strip()}


def _validate_date(value: str) -> dict:
    from datetime import datetime
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(value.strip(), fmt)
            return {"valid": True, "message": "Valid date", "normalized": dt.strftime("%d/%m/%Y")}
        except ValueError:
            continue
    return {"valid": False, "message": "Please use DD/MM/YYYY format (e.g., 15/08/1990)", "normalized": value}


def _validate_amount(value: str) -> dict:
    cleaned = re.sub(r"[,\s₹]", "", value)
    try:
        amt = float(cleaned)
        if amt < 0:
            return {"valid": False, "message": "Amount cannot be negative", "normalized": value}
        return {"valid": True, "message": "Valid amount", "normalized": str(int(amt))}
    except ValueError:
        return {"valid": False, "message": "Please enter a valid number", "normalized": value}


def _validate_land_size(value: str) -> dict:
    cleaned = re.sub(r"[,\s]", "", value.lower().replace("acres", "").replace("acre", "").replace("एकड़", "").replace("ஏக்கர்", ""))
    try:
        size = float(cleaned)
        if size < 0:
            return {"valid": False, "message": "Land size cannot be negative", "normalized": value}
        if size > 1000:
            return {"valid": False, "message": "Please check the land size — it seems too large", "normalized": value}
        return {"valid": True, "message": "Valid", "normalized": str(size)}
    except ValueError:
        return {"valid": False, "message": "Please enter land size as a number (e.g., 2.5)", "normalized": value}


def _validate_bank_account(value: str) -> dict:
    digits = re.sub(r"[\s\-]", "", value)
    if not digits.isdigit():
        return {"valid": False, "message": "Bank account should contain only digits", "normalized": value}
    if len(digits) < 9 or len(digits) > 18:
        return {"valid": False, "message": "Bank account must be 9-18 digits", "normalized": value}
    return {"valid": True, "message": "Valid bank account", "normalized": digits}


def _validate_state(value: str) -> dict:
    states = {
        "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
        "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand",
        "karnataka", "kerala", "madhya pradesh", "maharashtra", "manipur",
        "meghalaya", "mizoram", "nagaland", "odisha", "punjab",
        "rajasthan", "sikkim", "tamil nadu", "telangana", "tripura",
        "uttar pradesh", "uttarakhand", "west bengal",
        "delhi", "jammu and kashmir", "ladakh", "puducherry", "chandigarh",
    }
    normalized = value.strip().lower()
    for state in states:
        if normalized in state or state in normalized:
            return {"valid": True, "message": "Valid state", "normalized": state.title()}
    return {"valid": False, "message": f"'{value}' is not recognized. Please tell your state name.", "normalized": value}


def _validate_text(value: str) -> dict:
    if not value or not value.strip():
        return {"valid": False, "message": "This field cannot be empty", "normalized": value}
    return {"valid": True, "message": "Valid", "normalized": value.strip()}


# ── PII Masking ──────────────────────────────────────────────────────

def _mask_aadhaar(aadhaar: str) -> str:
    digits = re.sub(r"\D", "", aadhaar)
    if len(digits) == 12:
        return f"XXXX-XXXX-{digits[-4:]}"
    return "XXXX-XXXX-XXXX"


def _mask_bank_account(account: str) -> str:
    digits = re.sub(r"\D", "", account)
    if len(digits) >= 4:
        return f"{'X' * (len(digits) - 4)}{digits[-4:]}"
    return "XXXXXXXXXXXX"
