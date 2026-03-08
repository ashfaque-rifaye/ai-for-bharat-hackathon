"""Eligibility Engine — Rule-based eligibility checking for government schemes."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def check_eligibility(scheme: dict, user_profile: dict) -> dict:
    """
    Check if a user is eligible for a scheme based on eligibility rules.

    Returns:
        {
            "eligible": True/False,
            "confidence": 0-100,
            "matchedRules": [...],
            "failedRules": [...],
            "missingInfo": [...]
        }
    """
    rules = scheme.get("eligibilityRules", [])
    if not rules:
        return {
            "eligible": True,
            "confidence": 50,
            "reason": "No specific eligibility rules defined — likely eligible",
            "matchedRules": [],
            "failedRules": [],
            "missingInfo": [],
        }

    matched_rules = []
    failed_rules = []
    missing_info = []

    for rule in rules:
        field = rule["field"]
        operator = rule["operator"]
        expected_value = rule["value"]

        user_value = user_profile.get(field)

        if user_value is None:
            missing_info.append(field)
            continue

        # Evaluate rule
        result = _evaluate_rule(user_value, operator, expected_value)
        if result:
            matched_rules.append({"field": field, "status": "passed"})
        else:
            failed_rules.append({
                "field": field,
                "status": "failed",
                "expected": f"{operator} {expected_value}",
                "actual": str(user_value),
            })

    # Calculate eligibility and confidence
    total_rules = len(rules)
    evaluated_rules = len(matched_rules) + len(failed_rules)
    missing_count = len(missing_info)

    if failed_rules:
        eligible = False
        confidence = 90  # High confidence in rejection
    elif missing_count > 0:
        eligible = True  # Tentatively eligible
        confidence = max(30, int((evaluated_rules / total_rules) * 100))
    else:
        eligible = True
        confidence = 95

    # Generate reason
    if eligible and not missing_info:
        reason = "You appear to be fully eligible for this scheme!"
    elif eligible and missing_info:
        reason = f"You seem eligible, but we need more information about: {', '.join(missing_info)}"
    else:
        failed_fields = [r["field"] for r in failed_rules]
        reason = f"Unfortunately, you may not be eligible. Issues with: {', '.join(failed_fields)}"

    return {
        "eligible": eligible,
        "confidence": confidence,
        "reason": reason,
        "matchedRules": matched_rules,
        "failedRules": failed_rules,
        "missingInfo": missing_info,
    }


def _evaluate_rule(user_value: Any, operator: str, expected_value: Any) -> bool:
    """Evaluate a single eligibility rule."""
    try:
        # Normalize values for comparison
        if isinstance(expected_value, (int, float)):
            user_value = _to_number(user_value)

        if operator == "eq":
            return _normalize(user_value) == _normalize(expected_value)
        elif operator == "neq":
            return _normalize(user_value) != _normalize(expected_value)
        elif operator == "lt":
            return float(user_value) < float(expected_value)
        elif operator == "lte":
            return float(user_value) <= float(expected_value)
        elif operator == "gt":
            return float(user_value) > float(expected_value)
        elif operator == "gte":
            return float(user_value) >= float(expected_value)
        elif operator == "in":
            if isinstance(expected_value, list):
                return _normalize(user_value) in [_normalize(v) for v in expected_value]
            return _normalize(user_value) in _normalize(expected_value)
        elif operator == "contains":
            return _normalize(expected_value) in _normalize(str(user_value))
        else:
            logger.warning(f"Unknown operator: {operator}")
            return True  # Be lenient with unknown operators

    except (ValueError, TypeError) as e:
        logger.warning(f"Rule evaluation error: {e}")
        return True  # Be lenient on errors


def _normalize(value: Any) -> Any:
    """Normalize a value for comparison."""
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, bool):
        return value
    return value


def _to_number(value: Any) -> float:
    """Convert a value to a number."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Remove common formatting
        cleaned = value.replace(",", "").replace("₹", "").replace(" ", "")
        return float(cleaned)
    return 0.0


def match_schemes_to_profile(schemes: list[dict], user_profile: dict) -> list[dict]:
    """
    Match all schemes against a user profile and return ranked results.

    Returns list of dicts sorted by confidence:
        [{"scheme": {...}, "eligibility": {...}}, ...]
    """
    results = []

    for scheme in schemes:
        if not scheme.get("isActive", True):
            continue

        eligibility = check_eligibility(scheme, user_profile)
        results.append({
            "schemeId": scheme["schemeId"],
            "name": scheme["name"],
            "shortDescription": scheme.get("shortDescription", {}),
            "category": scheme["category"],
            "benefits": scheme.get("benefits", {}),
            "eligible": eligibility["eligible"],
            "confidence": eligibility["confidence"],
            "reason": eligibility["reason"],
            "missingInfo": eligibility["missingInfo"],
        })

    # Sort: eligible first, then by confidence descending
    results.sort(key=lambda x: (-int(x["eligible"]), -x["confidence"]))

    return results
