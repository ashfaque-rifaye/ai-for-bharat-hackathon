"""Tests for eligibility engine and form filler."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "lambdas" / "ai_engine"))

from eligibility import check_eligibility, match_schemes_to_profile, _evaluate_rule
from form_filler import validate_field, get_next_field, get_form_progress, format_form_summary


# ── Eligibility Check ────────────────────────────────────────────────

class TestCheckEligibility:
    def test_fully_eligible(self, sample_scheme, sample_user_profile):
        result = check_eligibility(sample_scheme, sample_user_profile)
        assert result["eligible"] is True
        assert result["confidence"] >= 90
        assert len(result["failedRules"]) == 0

    def test_ineligible_age(self, sample_scheme):
        result = check_eligibility(sample_scheme, {"age": 15, "occupation": "farmer", "annual_income": 100000})
        assert result["eligible"] is False
        assert any(r["field"] == "age" for r in result["failedRules"])

    def test_ineligible_income(self, sample_scheme):
        result = check_eligibility(sample_scheme, {"age": 30, "occupation": "farmer", "annual_income": 500000})
        assert result["eligible"] is False

    def test_missing_info(self, sample_scheme):
        result = check_eligibility(sample_scheme, {"age": 30})
        assert len(result["missingInfo"]) > 0
        assert result["eligible"] is True  # Tentatively eligible
        assert result["confidence"] < 95

    def test_no_rules(self):
        result = check_eligibility({"eligibilityRules": []}, {})
        assert result["eligible"] is True
        assert result["confidence"] == 50

    def test_wrong_occupation(self, sample_scheme):
        result = check_eligibility(sample_scheme, {"age": 30, "occupation": "teacher", "annual_income": 100000})
        assert result["eligible"] is False


class TestEvaluateRule:
    def test_eq_string(self):
        assert _evaluate_rule("farmer", "eq", "farmer") is True
        assert _evaluate_rule("teacher", "eq", "farmer") is False

    def test_eq_case_insensitive(self):
        assert _evaluate_rule("Farmer", "eq", "farmer") is True

    def test_gte(self):
        assert _evaluate_rule(25, "gte", 18) is True
        assert _evaluate_rule(15, "gte", 18) is False

    def test_lte(self):
        assert _evaluate_rule(100000, "lte", 200000) is True
        assert _evaluate_rule(300000, "lte", 200000) is False

    def test_in_list(self):
        assert _evaluate_rule("farmer", "in", ["farmer", "laborer"]) is True
        assert _evaluate_rule("teacher", "in", ["farmer", "laborer"]) is False

    def test_contains(self):
        assert _evaluate_rule("small farmer with land", "contains", "farmer") is True


class TestMatchSchemesToProfile:
    def test_matches_single_scheme(self, sample_scheme, sample_user_profile):
        results = match_schemes_to_profile([sample_scheme], sample_user_profile)
        assert len(results) == 1
        assert results[0]["eligible"] is True

    def test_skips_inactive_schemes(self, sample_scheme, sample_user_profile):
        sample_scheme["isActive"] = False
        results = match_schemes_to_profile([sample_scheme], sample_user_profile)
        assert len(results) == 0


# ── Form Filler ──────────────────────────────────────────────────────

class TestFormFieldValidation:
    def test_valid_aadhaar(self):
        result = validate_field("aadhaar", "234567890123")
        assert result["valid"] is True
        assert "-" in result["normalized"]

    def test_invalid_aadhaar(self):
        result = validate_field("aadhaar", "123")
        assert result["valid"] is False

    def test_valid_phone(self):
        result = validate_field("phone", "9876543210")
        assert result["valid"] is True
        assert result["normalized"].startswith("+91")

    def test_valid_phone_with_country_code(self):
        result = validate_field("phone", "+919876543210")
        assert result["valid"] is True

    def test_valid_ifsc(self):
        result = validate_field("ifsc", "SBIN0001234")
        assert result["valid"] is True

    def test_valid_pincode(self):
        result = validate_field("pincode", "110001")
        assert result["valid"] is True

    def test_valid_name(self):
        result = validate_field("name", "राहुल कुमार")
        assert result["valid"] is True

    def test_valid_date(self):
        result = validate_field("date", "15/08/1990")
        assert result["valid"] is True
        assert result["normalized"] == "15/08/1990"

    def test_valid_amount(self):
        result = validate_field("amount", "1,50,000")
        assert result["valid"] is True

    def test_valid_land_size(self):
        result = validate_field("land_size", "2.5 acres")
        assert result["valid"] is True

    def test_valid_state(self):
        result = validate_field("state", "Tamil Nadu")
        assert result["valid"] is True

    def test_text_fallback(self):
        result = validate_field("text", "anything goes")
        assert result["valid"] is True

    def test_empty_text_fails(self):
        result = validate_field("text", "")
        assert result["valid"] is False


class TestGetNextField:
    def test_first_field(self, sample_scheme):
        field = get_next_field(sample_scheme["formFields"], {})
        assert field["id"] == "full_name"

    def test_second_field_after_first(self, sample_scheme):
        field = get_next_field(sample_scheme["formFields"], {"full_name": "Rahul"})
        assert field["id"] == "aadhaar"

    def test_all_filled(self, sample_scheme):
        all_data = {f["id"]: "value" for f in sample_scheme["formFields"]}
        field = get_next_field(sample_scheme["formFields"], all_data)
        assert field is None


class TestGetFormProgress:
    def test_empty_form(self, sample_scheme):
        progress = get_form_progress(sample_scheme["formFields"], {})
        assert progress["completed"] == 0
        assert progress["total"] == 5
        assert progress["percentage"] == 0

    def test_partial_form(self, sample_scheme):
        progress = get_form_progress(sample_scheme["formFields"], {"full_name": "Rahul", "aadhaar": "234567890123"})
        assert progress["completed"] == 2
        assert progress["remaining"] == 3

    def test_complete_form(self, sample_scheme):
        all_data = {f["id"]: "value" for f in sample_scheme["formFields"]}
        progress = get_form_progress(sample_scheme["formFields"], all_data)
        assert progress["completed"] == 5
        assert progress["percentage"] == 100


class TestFormatFormSummary:
    def test_format_with_masking(self, sample_scheme):
        data = {"full_name": "Rahul Kumar", "aadhaar": "234567890123"}
        summary = format_form_summary(sample_scheme["formFields"], data, "en")
        assert "Rahul Kumar" in summary
        assert "XXXX" in summary  # Aadhaar should be masked
        assert "234567890123" not in summary
