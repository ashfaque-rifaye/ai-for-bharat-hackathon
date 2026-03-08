"""Tests for shared utility functions — validation, formatting, masking."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "shared"))

from utils import (
    validate_aadhaar,
    validate_phone,
    validate_ifsc,
    validate_pincode,
    validate_name,
    validate_date,
    validate_amount,
    validate_state,
    validate_field,
    mask_aadhaar,
    mask_phone,
    mask_bank_account,
    format_currency,
    get_ttl,
)


# ── Aadhaar Validation ──────────────────────────────────────────────

class TestValidateAadhaar:
    def test_valid_aadhaar(self):
        valid, msg = validate_aadhaar("234567890123")
        assert valid is True

    def test_valid_aadhaar_with_spaces(self):
        valid, msg = validate_aadhaar("2345 6789 0123")
        assert valid is True

    def test_valid_aadhaar_with_dashes(self):
        valid, msg = validate_aadhaar("2345-6789-0123")
        assert valid is True

    def test_aadhaar_wrong_length(self):
        valid, msg = validate_aadhaar("12345")
        assert valid is False
        assert "12 digits" in msg

    def test_aadhaar_starts_with_zero(self):
        valid, msg = validate_aadhaar("034567890123")
        assert valid is False
        assert "start with 0" in msg

    def test_aadhaar_starts_with_one(self):
        valid, msg = validate_aadhaar("134567890123")
        assert valid is False

    def test_aadhaar_non_digits(self):
        valid, msg = validate_aadhaar("abcdefghijkl")
        assert valid is False


# ── Phone Validation ─────────────────────────────────────────────────

class TestValidatePhone:
    def test_valid_phone(self):
        valid, msg = validate_phone("9876543210")
        assert valid is True

    def test_valid_phone_with_country_code(self):
        valid, msg = validate_phone("+919876543210")
        assert valid is True

    def test_valid_phone_with_91_prefix(self):
        valid, msg = validate_phone("919876543210")
        assert valid is True

    def test_phone_wrong_length(self):
        valid, msg = validate_phone("12345")
        assert valid is False

    def test_phone_invalid_start(self):
        valid, msg = validate_phone("1234567890")
        assert valid is False
        assert "6, 7, 8, or 9" in msg


# ── IFSC Validation ──────────────────────────────────────────────────

class TestValidateIfsc:
    def test_valid_ifsc(self):
        valid, msg = validate_ifsc("SBIN0001234")
        assert valid is True

    def test_valid_ifsc_lowercase(self):
        valid, msg = validate_ifsc("sbin0001234")
        assert valid is True

    def test_invalid_ifsc(self):
        valid, msg = validate_ifsc("INVALID")
        assert valid is False


# ── PIN Code Validation ──────────────────────────────────────────────

class TestValidatePincode:
    def test_valid_pincode(self):
        valid, msg = validate_pincode("110001")
        assert valid is True

    def test_pincode_starts_with_zero(self):
        valid, msg = validate_pincode("010001")
        assert valid is False

    def test_pincode_wrong_length(self):
        valid, msg = validate_pincode("1234")
        assert valid is False


# ── Name Validation ──────────────────────────────────────────────────

class TestValidateName:
    def test_valid_name(self):
        valid, msg = validate_name("Rahul Kumar")
        assert valid is True

    def test_valid_hindi_name(self):
        valid, msg = validate_name("राहुल कुमार")
        assert valid is True

    def test_empty_name(self):
        valid, msg = validate_name("")
        assert valid is False

    def test_name_too_short(self):
        valid, msg = validate_name("A")
        assert valid is False

    def test_name_too_long(self):
        valid, msg = validate_name("A" * 101)
        assert valid is False


# ── Date Validation ──────────────────────────────────────────────────

class TestValidateDate:
    def test_valid_dd_mm_yyyy(self):
        valid, msg = validate_date("15/08/1990")
        assert valid is True

    def test_valid_dd_mm_yyyy_dash(self):
        valid, msg = validate_date("15-08-1990")
        assert valid is True

    def test_valid_iso_format(self):
        valid, msg = validate_date("1990-08-15")
        assert valid is True

    def test_invalid_date(self):
        valid, msg = validate_date("not-a-date")
        assert valid is False


# ── Amount Validation ────────────────────────────────────────────────

class TestValidateAmount:
    def test_valid_amount(self):
        valid, msg = validate_amount("50000")
        assert valid is True

    def test_valid_amount_with_commas(self):
        valid, msg = validate_amount("1,50,000")
        assert valid is True

    def test_valid_amount_with_rupee_symbol(self):
        valid, msg = validate_amount("₹50000")
        assert valid is True

    def test_negative_amount(self):
        valid, msg = validate_amount("-100")
        assert valid is False

    def test_invalid_amount(self):
        valid, msg = validate_amount("not-a-number")
        assert valid is False


# ── State Validation ─────────────────────────────────────────────────

class TestValidateState:
    def test_valid_state(self):
        valid, msg = validate_state("Uttar Pradesh")
        assert valid is True

    def test_partial_state_name(self):
        valid, msg = validate_state("tamil")
        assert valid is True

    def test_invalid_state(self):
        valid, msg = validate_state("Atlantis")
        assert valid is False


# ── Field Validation Router ──────────────────────────────────────────

class TestValidateField:
    def test_routes_aadhaar(self):
        valid, msg = validate_field("aadhaar", "234567890123")
        assert valid is True

    def test_routes_phone(self):
        valid, msg = validate_field("phone", "9876543210")
        assert valid is True

    def test_unknown_type_passes(self):
        valid, msg = validate_field("unknown_type", "anything")
        assert valid is True


# ── Masking Functions ────────────────────────────────────────────────

class TestMasking:
    def test_mask_aadhaar(self):
        assert mask_aadhaar("234567890123") == "XXXX-XXXX-0123"

    def test_mask_aadhaar_short(self):
        assert mask_aadhaar("12345") == "XXXX-XXXX-XXXX"

    def test_mask_phone(self):
        assert mask_phone("9876543210") == "+91XXXXX3210"

    def test_mask_bank_account(self):
        result = mask_bank_account("12345678901234")
        assert result.endswith("1234")
        assert "X" in result


# ── Currency Formatting ──────────────────────────────────────────────

class TestFormatCurrency:
    def test_small_amount(self):
        assert format_currency(500) == "₹500"

    def test_thousands(self):
        assert format_currency(6000) == "₹6,000"

    def test_lakhs(self):
        assert format_currency(150000) == "₹1,50,000"

    def test_crores(self):
        assert format_currency(10000000) == "₹1,00,00,000"


# ── TTL Helper ───────────────────────────────────────────────────────

class TestGetTTL:
    def test_returns_future_timestamp(self):
        import time
        ttl = get_ttl(3600)
        assert ttl > time.time()
        assert ttl < time.time() + 7200
