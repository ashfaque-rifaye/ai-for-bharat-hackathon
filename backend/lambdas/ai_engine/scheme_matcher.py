"""Scheme Matcher — RAG and keyword-based scheme search."""

import json
import logging
import os
from decimal import Decimal
from typing import Any, Optional

import boto3

logger = logging.getLogger(__name__)

# Environment
SCHEMES_TABLE = os.environ.get("SCHEMES_TABLE", "vaanisetu-schemes")
BEDROCK_KB_ID = os.environ.get("BEDROCK_KB_ID", "")
REGION = os.environ.get("AWS_REGION", "us-east-1")

_dynamodb = boto3.resource("dynamodb", region_name=REGION)
_schemes_table = _dynamodb.Table(SCHEMES_TABLE)


def search_schemes(
    query: str,
    category: Optional[str] = None,
    state: Optional[str] = None,
    language: str = "en",
) -> list[dict]:
    """
    Search for schemes matching a user's query.

    Uses Bedrock Knowledge Base if available, falls back to keyword search.
    """
    # Try RAG search first
    if BEDROCK_KB_ID:
        try:
            return _rag_search(query, category)
        except Exception as e:
            logger.warning(f"RAG search failed, falling back to keyword: {e}")

    # Fallback: keyword search over DynamoDB
    return _keyword_search(query, category)


def _rag_search(query: str, category: Optional[str] = None) -> list[dict]:
    """Search using Bedrock Knowledge Base (RAG)."""
    client = boto3.client("bedrock-agent-runtime", region_name=REGION)

    response = client.retrieve(
        knowledgeBaseId=BEDROCK_KB_ID,
        retrievalQuery={"text": query},
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "numberOfResults": 5,
            }
        },
    )

    results = []
    seen_scheme_ids = set()

    for result in response.get("retrievalResults", []):
        content = result.get("content", {}).get("text", "")
        score = result.get("score", 0)

        # Extract scheme ID from the content
        scheme_id = _extract_scheme_id(content)
        if scheme_id and scheme_id not in seen_scheme_ids:
            seen_scheme_ids.add(scheme_id)
            # Fetch full scheme from DynamoDB
            scheme = get_scheme_by_id(scheme_id)
            if scheme:
                if category and scheme.get("category") != category:
                    continue
                scheme["_ragScore"] = score
                results.append(scheme)

    return results


def _keyword_search(query: str, category: Optional[str] = None) -> list[dict]:
    """Simple keyword search over DynamoDB schemes."""
    # Get all schemes (for MVP with 10 schemes this is fine)
    if category:
        response = _schemes_table.query(
            IndexName="category-index",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("category").eq(category),
        )
    else:
        response = _schemes_table.scan()

    items = response.get("Items", [])
    query_lower = query.lower()

    # Score each scheme by keyword relevance
    scored = []
    for item in items:
        if not item.get("isActive", True):
            continue

        score = _calculate_keyword_score(item, query_lower)
        if score > 0:
            item["_keywordScore"] = score
            scored.append(item)

    # Sort by score descending
    scored.sort(key=lambda x: x.get("_keywordScore", 0), reverse=True)
    return scored[:5]  # Top 5 results


def _calculate_keyword_score(scheme: dict, query: str) -> int:
    """Calculate a simple relevance score for keyword search."""
    score = 0
    searchable_text = json.dumps(scheme, ensure_ascii=False, default=str).lower()

    # Split query into words
    words = query.split()
    for word in words:
        if len(word) < 2:
            continue
        if word in searchable_text:
            score += 10

    # Category keyword matching
    category_keywords = {
        "agriculture": ["खेती", "किसान", "farming", "farmer", "crop", "फसल", "कृषि", "விவசாயம்"],
        "housing": ["मकान", "घर", "house", "housing", "आवास", "வீடு"],
        "healthcare": ["स्वास्थ्य", "health", "hospital", "बीमारी", "இலாஜ", "சுகாதாரம்"],
        "finance": ["ऋण", "loan", "पैसा", "money", "business", "व्यापार", "கடன்"],
        "food": ["राशन", "अनाज", "food", "ration", "खाना", "உணவு"],
        "energy": ["गैस", "gas", "एलपीजी", "LPG", "ஆற்றல்"],
        "savings": ["बचत", "savings", "बेटी", "daughter", "girl", "சேமிப்பு"],
        "insurance": ["बीमा", "insurance", "फसल बीमा", "காப்பீடு"],
    }

    for cat, keywords in category_keywords.items():
        for kw in keywords:
            if kw.lower() in query:
                if scheme.get("category") == cat:
                    score += 20  # Boost matching category
                break

    return score


def _extract_scheme_id(text: str) -> Optional[str]:
    """Extract scheme ID from RAG result text."""
    import re

    # Look for "Scheme ID: XXX" pattern
    match = re.search(r"Scheme ID:\s*(\S+)", text)
    if match:
        return match.group(1)

    # Look for known scheme IDs
    known_ids = [
        "PM-KISAN", "PM-AWAS-GRAMIN", "RKVY", "PM-FASAL-BIMA",
        "SOIL-HEALTH-CARD", "PM-UJJWALA", "AYUSHMAN-BHARAT",
        "PM-MUDRA", "SUKANYA-SAMRIDDHI", "PM-GARIB-KALYAN-ANNA",
    ]
    for sid in known_ids:
        if sid in text:
            return sid

    return None


def get_scheme_by_id(scheme_id: str) -> Optional[dict]:
    """Get a scheme by its ID from DynamoDB."""
    response = _schemes_table.get_item(Key={"schemeId": scheme_id})
    return response.get("Item")


def get_all_schemes() -> list[dict]:
    """Get all active schemes."""
    response = _schemes_table.scan()
    return [item for item in response.get("Items", []) if item.get("isActive", True)]


def get_schemes_summary(language: str = "en") -> str:
    """Get a text summary of all schemes for AI context."""
    schemes = get_all_schemes()
    lines = []
    for s in schemes:
        name = s["name"].get(language, s["name"]["en"])
        desc = s.get("shortDescription", s.get("description", {})).get(language, "")
        category = s.get("category", "")
        lines.append(f"- **{s['schemeId']}** ({category}): {name} — {desc}")
    return "\n".join(lines)
