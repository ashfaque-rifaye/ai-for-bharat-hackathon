"""Tests for AI Engine Lambda — Bedrock conversation, tool use, and state machine."""

import json
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, ANY

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "shared"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "lambdas" / "ai_engine"))

from eligibility import check_eligibility, match_schemes_to_profile, _evaluate_rule
from form_filler import (
    validate_field,
    get_next_field,
    get_form_progress,
    format_form_summary,
)


# ── Eligibility Engine Tests ─────────────────────────────────────────

class TestCheckEligibility:
    """Test the rule-based eligibility engine."""

    def test_fully_eligible(self, sample_scheme, sample_user_profile):
        result = check_eligibility(sample_scheme, sample_user_profile)
        assert result["eligible"] is True
        assert result["confidence"] >= 90
        assert len(result["failedRules"]) == 0

    def test_ineligible_by_age(self, sample_scheme):
        profile = {"age": 15, "occupation": "farmer", "annual_income": 100000}
        result = check_eligibility(sample_scheme, profile)
        assert result["eligible"] is False
        assert any(r["field"] == "age" for r in result["failedRules"])

    def test_ineligible_by_income(self, sample_scheme):
        profile = {"age": 30, "occupation": "farmer", "annual_income": 500000}
        result = check_eligibility(sample_scheme, profile)
        assert result["eligible"] is False
        assert any(r["field"] == "annual_income" for r in result["failedRules"])

    def test_ineligible_by_occupation(self, sample_scheme):
        profile = {"age": 30, "occupation": "teacher", "annual_income": 100000}
        result = check_eligibility(sample_scheme, profile)
        assert result["eligible"] is False
        assert any(r["field"] == "occupation" for r in result["failedRules"])

    def test_missing_fields_tentatively_eligible(self, sample_scheme):
        result = check_eligibility(sample_scheme, {"age": 30})
        assert result["eligible"] is True  # Tentatively eligible
        assert result["confidence"] < 95
        assert len(result["missingInfo"]) > 0
        assert "occupation" in result["missingInfo"]

    def test_empty_rules_scheme(self):
        result = check_eligibility({"eligibilityRules": []}, {"age": 25})
        assert result["eligible"] is True
        assert result["confidence"] == 50

    def test_all_fields_missing(self, sample_scheme):
        result = check_eligibility(sample_scheme, {})
        assert result["eligible"] is True  # Tentatively eligible
        assert result["confidence"] <= 30
        assert len(result["missingInfo"]) == 3


class TestEvaluateRule:
    """Test individual rule evaluation operators."""

    def test_eq_match(self):
        assert _evaluate_rule("farmer", "eq", "farmer") is True

    def test_eq_mismatch(self):
        assert _evaluate_rule("teacher", "eq", "farmer") is False

    def test_eq_case_insensitive(self):
        assert _evaluate_rule("Farmer", "eq", "farmer") is True
        assert _evaluate_rule("FARMER", "eq", "farmer") is True

    def test_neq(self):
        assert _evaluate_rule("teacher", "neq", "farmer") is True
        assert _evaluate_rule("farmer", "neq", "farmer") is False

    def test_gte(self):
        assert _evaluate_rule(25, "gte", 18) is True
        assert _evaluate_rule(18, "gte", 18) is True
        assert _evaluate_rule(15, "gte", 18) is False

    def test_lte(self):
        assert _evaluate_rule(100000, "lte", 200000) is True
        assert _evaluate_rule(200000, "lte", 200000) is True
        assert _evaluate_rule(300000, "lte", 200000) is False

    def test_gt(self):
        assert _evaluate_rule(20, "gt", 18) is True
        assert _evaluate_rule(18, "gt", 18) is False

    def test_lt(self):
        assert _evaluate_rule(15, "lt", 18) is True
        assert _evaluate_rule(18, "lt", 18) is False

    def test_in_list(self):
        assert _evaluate_rule("farmer", "in", ["farmer", "laborer"]) is True
        assert _evaluate_rule("teacher", "in", ["farmer", "laborer"]) is False

    def test_contains(self):
        assert _evaluate_rule("small farmer with land", "contains", "farmer") is True
        assert _evaluate_rule("teacher", "contains", "farmer") is False

    def test_unknown_operator_lenient(self):
        # Unknown operators should not reject — be lenient
        assert _evaluate_rule("anything", "unknown_op", "anything") is True

    def test_string_number_conversion(self):
        assert _evaluate_rule("25", "gte", 18) is True
        assert _evaluate_rule("10", "gte", 18) is False


class TestMatchSchemesToProfile:
    """Test scheme-to-profile matching and ranking."""

    def test_matches_single_scheme(self, sample_scheme, sample_user_profile):
        results = match_schemes_to_profile([sample_scheme], sample_user_profile)
        assert len(results) == 1
        assert results[0]["eligible"] is True
        assert results[0]["schemeId"] == "pm_kisan"

    def test_skips_inactive_schemes(self, sample_scheme, sample_user_profile):
        sample_scheme["isActive"] = False
        results = match_schemes_to_profile([sample_scheme], sample_user_profile)
        assert len(results) == 0

    def test_returns_scheme_metadata(self, sample_scheme, sample_user_profile):
        results = match_schemes_to_profile([sample_scheme], sample_user_profile)
        r = results[0]
        assert "schemeId" in r
        assert "name" in r
        assert "category" in r
        assert "benefits" in r
        assert "confidence" in r
        assert "reason" in r

    def test_sorts_eligible_first(self, sample_scheme, sample_user_profile):
        scheme2 = sample_scheme.copy()
        scheme2["schemeId"] = "test_scheme"
        scheme2["eligibilityRules"] = [
            {"field": "age", "operator": "gte", "value": 99}  # Will fail
        ]
        results = match_schemes_to_profile([scheme2, sample_scheme], sample_user_profile)
        assert results[0]["eligible"] is True
        assert results[1]["eligible"] is False


# ── Form Filler Tests ────────────────────────────────────────────────

class TestFormFieldValidation:
    """Test form field validation via form_filler module."""

    def test_valid_aadhaar(self):
        r = validate_field("aadhaar", "234567890123")
        assert r["valid"] is True
        assert "-" in r["normalized"]

    def test_invalid_aadhaar_short(self):
        r = validate_field("aadhaar", "12345")
        assert r["valid"] is False

    def test_invalid_aadhaar_starts_with_zero(self):
        r = validate_field("aadhaar", "034567890123")
        assert r["valid"] is False

    def test_valid_phone(self):
        r = validate_field("phone", "9876543210")
        assert r["valid"] is True
        assert r["normalized"].startswith("+91")

    def test_valid_phone_with_country_code(self):
        r = validate_field("phone", "+919876543210")
        assert r["valid"] is True

    def test_invalid_phone(self):
        r = validate_field("phone", "12345")
        assert r["valid"] is False

    def test_valid_ifsc(self):
        r = validate_field("ifsc", "SBIN0001234")
        assert r["valid"] is True
        assert r["normalized"] == "SBIN0001234"

    def test_invalid_ifsc(self):
        r = validate_field("ifsc", "INVALID")
        assert r["valid"] is False

    def test_valid_pincode(self):
        r = validate_field("pincode", "110001")
        assert r["valid"] is True

    def test_invalid_pincode(self):
        r = validate_field("pincode", "000001")
        assert r["valid"] is False

    def test_valid_name_english(self):
        r = validate_field("name", "Rahul Kumar")
        assert r["valid"] is True

    def test_valid_name_hindi(self):
        r = validate_field("name", "राहुल कुमार")
        assert r["valid"] is True

    def test_invalid_name_empty(self):
        r = validate_field("name", "")
        assert r["valid"] is False

    def test_valid_date(self):
        r = validate_field("date", "15/08/1990")
        assert r["valid"] is True
        assert r["normalized"] == "15/08/1990"

    def test_valid_date_iso(self):
        r = validate_field("date", "1990-08-15")
        assert r["valid"] is True

    def test_invalid_date(self):
        r = validate_field("date", "not-a-date")
        assert r["valid"] is False

    def test_valid_amount(self):
        r = validate_field("amount", "1,50,000")
        assert r["valid"] is True

    def test_valid_amount_with_rupee(self):
        r = validate_field("amount", "₹50000")
        assert r["valid"] is True

    def test_invalid_amount(self):
        r = validate_field("amount", "abc")
        assert r["valid"] is False

    def test_valid_land_size(self):
        r = validate_field("land_size", "2.5 acres")
        assert r["valid"] is True

    def test_invalid_land_size_too_large(self):
        r = validate_field("land_size", "5000")
        assert r["valid"] is False

    def test_valid_state(self):
        r = validate_field("state", "Tamil Nadu")
        assert r["valid"] is True

    def test_invalid_state(self):
        r = validate_field("state", "Atlantis")
        assert r["valid"] is False

    def test_text_field_valid(self):
        r = validate_field("text", "some text")
        assert r["valid"] is True

    def test_text_field_empty(self):
        r = validate_field("text", "")
        assert r["valid"] is False

    def test_bank_account_valid(self):
        r = validate_field("bank_account", "12345678901234")
        assert r["valid"] is True

    def test_bank_account_too_short(self):
        r = validate_field("bank_account", "1234")
        assert r["valid"] is False


class TestGetNextField:
    """Test form field sequencing."""

    def test_first_field(self, sample_scheme):
        field = get_next_field(sample_scheme["formFields"], {})
        assert field["id"] == "full_name"

    def test_second_field(self, sample_scheme):
        field = get_next_field(sample_scheme["formFields"], {"full_name": "Rahul"})
        assert field["id"] == "aadhaar"

    def test_all_filled_returns_none(self, sample_scheme):
        all_data = {f["id"]: "value" for f in sample_scheme["formFields"]}
        field = get_next_field(sample_scheme["formFields"], all_data)
        assert field is None


class TestGetFormProgress:
    """Test form progress tracking."""

    def test_empty_form(self, sample_scheme):
        progress = get_form_progress(sample_scheme["formFields"], {})
        assert progress["completed"] == 0
        assert progress["total"] == 5
        assert progress["percentage"] == 0
        assert progress["remaining"] == 5

    def test_partial_form(self, sample_scheme):
        progress = get_form_progress(sample_scheme["formFields"], {"full_name": "Rahul", "aadhaar": "234567890123"})
        assert progress["completed"] == 2
        assert progress["remaining"] == 3
        assert 30 <= progress["percentage"] <= 50

    def test_complete_form(self, sample_scheme):
        all_data = {f["id"]: "value" for f in sample_scheme["formFields"]}
        progress = get_form_progress(sample_scheme["formFields"], all_data)
        assert progress["completed"] == 5
        assert progress["percentage"] == 100
        assert progress["remaining"] == 0


class TestFormatFormSummary:
    """Test form summary with PII masking."""

    def test_masks_aadhaar_in_summary(self, sample_scheme):
        data = {"full_name": "Rahul Kumar", "aadhaar": "234567890123"}
        summary = format_form_summary(sample_scheme["formFields"], data, "en")
        assert "Rahul Kumar" in summary
        assert "XXXX" in summary
        assert "234567890123" not in summary

    def test_hindi_summary(self, sample_scheme):
        data = {"full_name": "राहुल"}
        summary = format_form_summary(sample_scheme["formFields"], data, "hi")
        assert "राहुल" in summary

    def test_empty_form_summary(self, sample_scheme):
        summary = format_form_summary(sample_scheme["formFields"], {}, "en")
        assert summary == ""  # No data to show


# ── AI Handler Structure Tests ───────────────────────────────────────

class TestAIHandlerTools:
    """Test the tool definitions used by Bedrock Converse API."""

    def test_tool_definitions_importable(self):
        """Verify the TOOLS list can be imported from handler."""
        # We mock boto3 to avoid real AWS calls during import
        mock_boto3 = MagicMock()
        mock_boto3.client.return_value = MagicMock()
        mock_boto3.resource.return_value = MagicMock()

        with patch.dict("sys.modules", {"boto3": mock_boto3}):
            # Force-import the ai_engine handler specifically
            import importlib.util
            ai_handler_path = Path(__file__).resolve().parent.parent / "backend" / "lambdas" / "ai_engine" / "handler.py"
            spec = importlib.util.spec_from_file_location("ai_engine_handler", str(ai_handler_path))
            h = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(h)
            assert hasattr(h, "TOOLS")
            assert isinstance(h.TOOLS, list)
            assert len(h.TOOLS) >= 3

            # Check tool names
            tool_names = [t["toolSpec"]["name"] for t in h.TOOLS]
            assert "search_schemes" in tool_names
            assert "check_eligibility" in tool_names
            assert "validate_field" in tool_names

    def test_tool_schemas_have_required_fields(self):
        """Each tool must have name, description, and inputSchema."""
        mock_boto3 = MagicMock()
        mock_boto3.client.return_value = MagicMock()
        mock_boto3.resource.return_value = MagicMock()

        with patch.dict("sys.modules", {"boto3": mock_boto3}):
            import importlib.util
            ai_handler_path = Path(__file__).resolve().parent.parent / "backend" / "lambdas" / "ai_engine" / "handler.py"
            spec = importlib.util.spec_from_file_location("ai_engine_handler", str(ai_handler_path))
            h = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(h)

            for tool in h.TOOLS:
                tspec = tool["toolSpec"]
                assert "name" in tspec
                assert "description" in tspec
                assert "inputSchema" in tspec
                assert "json" in tspec["inputSchema"]
