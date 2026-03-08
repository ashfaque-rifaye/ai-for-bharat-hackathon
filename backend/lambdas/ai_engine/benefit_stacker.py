"""Benefit Stacker — Cross-scheme benefit analysis engine.

Why this matters:
  Most citizens don't know they can avail MULTIPLE schemes at once.  A farmer
  might qualify for PM-KISAN *and* PM-FASAL-BIMA *and* SOIL-HEALTH-CARD — but
  no one tells them that.  This module calculates the **combined** annual value
  of all eligible schemes and highlights synergies so the AI (or the frontend
  panel) can present a compelling "total benefit" number.

How it works:
  1. Takes a user profile (occupation, income, land size, etc.)
  2. Runs *every* active scheme through the eligibility engine
  3. Groups eligible schemes by category
  4. Sums up monetary benefits (where amounts are known)
  5. Detects "synergy clusters" — sets of schemes that naturally complement
     each other (e.g. farming cluster: PM-KISAN + FASAL BIMA + SOIL HEALTH)
"""

import logging
from decimal import Decimal
from typing import Any

from eligibility import check_eligibility, match_schemes_to_profile
from scheme_matcher import get_all_schemes, get_scheme_by_id

logger = logging.getLogger(__name__)

# ── Synergy Definitions ──────────────────────────────────────────────
# Each synergy cluster is a set of scheme IDs that work well together.
# "label" is shown to the user; "schemes" list at least two IDs.
SYNERGY_CLUSTERS = [
    {
        "id": "farmer-income",
        "label": {
            "en": "Farmer Income Shield",
            "hi": "किसान आय सुरक्षा कवच",
            "ta": "விவசாயி வருமான பாதுகாப்பு",
            "bn": "কৃষক আয় সুরক্ষা",
            "te": "రైతు ఆదాయ రక్షణ",
            "mr": "शेतकरी उत्पन्न संरक्षण",
            "kn": "ರೈತ ಆದಾಯ ರಕ್ಷಣೆ",
            "ml": "കർഷക വരുമാന സംരക്ഷണം",
        },
        "schemes": ["PM-KISAN", "PM-FASAL-BIMA", "SOIL-HEALTH-CARD"],
        "description": {
            "en": "Income support + crop insurance + soil optimization = maximum farm productivity",
            "hi": "आय सहायता + फसल बीमा + मिट्टी स्वास्थ्य = अधिकतम कृषि उत्पादकता",
        },
    },
    {
        "id": "rural-welfare",
        "label": {
            "en": "Rural Family Welfare Bundle",
            "hi": "ग्रामीण परिवार कल्याण बंडल",
            "ta": "கிராமப்புற குடும்ப நலத் தொகுப்பு",
            "bn": "গ্রামীণ পরিবার কল্যাণ বান্ডিল",
            "te": "గ్రామీణ కుటుంబ సంక్షేమ బండిల్",
            "mr": "ग्रामीण कुटुंब कल्याण बंडल",
            "kn": "ಗ್ರಾಮೀಣ ಕುಟುಂಬ ಕಲ್ಯಾಣ ಬಂಡಲ್",
            "ml": "ഗ്രാമീണ കുടുംബ ക്ഷേമ ബണ്ടിൽ",
        },
        "schemes": ["PM-AWAS-GRAMIN", "PM-UJJWALA", "PM-GARIB-KALYAN-ANNA"],
        "description": {
            "en": "Housing + clean cooking fuel + free food grains = basic needs covered",
            "hi": "आवास + स्वच्छ रसोई ईंधन + मुफ्त खाद्यान्न = बुनियादी जरूरतें पूरी",
        },
    },
    {
        "id": "health-finance",
        "label": {
            "en": "Health + Finance Safety Net",
            "hi": "स्वास्थ्य + वित्तीय सुरक्षा जाल",
            "ta": "சுகாதாரம் + நிதி பாதுகாப்பு வலை",
            "bn": "স্বাস্থ্য + আর্থিক নিরাপত্তা জাল",
            "te": "ఆరోగ్యం + ఆర్థిక భద్రత",
            "mr": "आरोग्य + आर्थिक सुरक्षा जाळे",
            "kn": "ಆರೋಗ್ಯ + ಹಣಕಾಸು ಸುರಕ್ಷತಾ ಜಾಲ",
            "ml": "ആരോഗ്യം + സാമ്പത്തിക സുരക്ഷാ വല",
        },
        "schemes": ["AYUSHMAN-BHARAT", "PM-MUDRA"],
        "description": {
            "en": "Health insurance up to ₹5 lakh + business loan up to ₹10 lakh",
            "hi": "₹5 लाख तक स्वास्थ्य बीमा + ₹10 लाख तक व्यापार ऋण",
        },
    },
    {
        "id": "girl-child",
        "label": {
            "en": "Girl Child Future Fund",
            "hi": "बेटी भविष्य कोष",
            "ta": "பெண் குழந்தை எதிர்கால நிதி",
            "bn": "কন্যা শিশু ভবিষ্যৎ তহবিল",
            "te": "బాలిక భవిష్యత్ నిధి",
            "mr": "मुलगी भविष्य निधी",
            "kn": "ಹೆಣ್ಣುಮಗಳ ಭವಿಷ್ಯ ನಿಧಿ",
            "ml": "പെൺകുട്ടി ഭാവി ഫണ്ട്",
        },
        "schemes": ["SUKANYA-SAMRIDDHI", "AYUSHMAN-BHARAT"],
        "description": {
            "en": "Savings up to ₹1.5 lakh/year (tax-free) + health cover for the family",
            "hi": "₹1.5 लाख/वर्ष तक बचत (कर-मुक्त) + परिवार स्वास्थ्य कवर",
        },
    },
]


def compute_benefit_stack(user_profile: dict, language: str = "en") -> dict:
    """Compute the combined benefit summary for all eligible schemes.

    Args:
        user_profile: Dict with keys like occupation, income, landSize, etc.
        language:     2-letter language code ("en", "hi", "ta", …).

    Returns:
        {
            "totalAnnualBenefit":  42000,
            "eligibleSchemes":    [...],
            "synergies":          [...],
            "summaryText":        "Based on your profile …"
        }
    """
    lang = language[:2] if language else "en"
    all_schemes = get_all_schemes()

    if not all_schemes:
        return _empty_result(lang)

    # ── Step 1: Check eligibility for every scheme ────────────────
    eligible_schemes = []
    for scheme in all_schemes:
        if not scheme.get("isActive", True):
            continue
        result = check_eligibility(scheme, user_profile)
        if result["eligible"]:
            benefit_amount = _extract_benefit_amount(scheme)
            eligible_schemes.append({
                "schemeId": scheme["schemeId"],
                "name": scheme.get("name", {}).get(lang, scheme.get("name", {}).get("en", "")),
                "category": scheme.get("category", ""),
                "benefitAmount": benefit_amount,
                "benefitDescription": (
                    scheme.get("benefits", {})
                    .get("description", {})
                    .get(lang, scheme.get("benefits", {}).get("description", {}).get("en", ""))
                ),
                "confidence": result["confidence"],
                "missingInfo": result["missingInfo"],
            })

    # ── Step 2: Calculate total annual monetary benefit ───────────
    total_annual = sum(s["benefitAmount"] for s in eligible_schemes)

    # ── Step 3: Detect active synergy clusters ────────────────────
    eligible_ids = {s["schemeId"] for s in eligible_schemes}
    active_synergies = []
    for cluster in SYNERGY_CLUSTERS:
        matched_ids = [sid for sid in cluster["schemes"] if sid in eligible_ids]
        if len(matched_ids) >= 2:
            active_synergies.append({
                "id": cluster["id"],
                "label": cluster["label"].get(lang, cluster["label"].get("en", "")),
                "description": cluster["description"].get(lang, cluster["description"].get("en", "")),
                "schemes": matched_ids,
                "allMatched": len(matched_ids) == len(cluster["schemes"]),
            })

    # ── Step 4: Build human-readable summary ──────────────────────
    summary = _build_summary_text(
        eligible_schemes, total_annual, active_synergies, lang
    )

    return {
        "totalAnnualBenefit": total_annual,
        "eligibleCount": len(eligible_schemes),
        "eligibleSchemes": eligible_schemes,
        "synergies": active_synergies,
        "summaryText": summary,
    }


# ── Private Helpers ──────────────────────────────────────────────────

def _extract_benefit_amount(scheme: dict) -> int:
    """Pull out the numeric annual benefit from a scheme's `benefits` key.

    Handles different structures:
      • {"benefits": {"amount": 6000}}          → 6000
      • {"benefits": {"amount": "5,00,000"}}    → 500000
    """
    benefits = scheme.get("benefits", {})
    raw = benefits.get("amount", 0)

    if isinstance(raw, (int, float, Decimal)):
        return int(raw)

    if isinstance(raw, str):
        cleaned = raw.replace(",", "").replace("₹", "").replace(" ", "")
        try:
            return int(float(cleaned))
        except ValueError:
            return 0

    return 0


def _build_summary_text(
    schemes: list,
    total: int,
    synergies: list,
    lang: str,
) -> str:
    """Build a user-friendly paragraph summarising the benefit stack."""
    count = len(schemes)

    if count == 0:
        NO_MATCH = {
            "en": "We couldn't find eligible schemes with the information provided. Please share more details about your occupation and family.",
            "hi": "दी गई जानकारी से कोई योजना मिलान नहीं हो पाई। कृपया अपने व्यवसाय और परिवार की जानकारी दें।",
        }
        return NO_MATCH.get(lang, NO_MATCH["en"])

    # Format rupee amount with Indian comma grouping (12,34,567)
    formatted_total = _format_inr(total)

    scheme_names = ", ".join(s["name"] for s in schemes[:5])
    synergy_note = ""
    if synergies:
        labels = " + ".join(syn["label"] for syn in synergies)
        synergy_note_map = {
            "en": f" You also qualify for the {labels} combo — these schemes work even better together!",
            "hi": f" आप {labels} कॉम्बो के लिए भी पात्र हैं — ये योजनाएं साथ मिलकर और भी बेहतर काम करती हैं!",
        }
        synergy_note = synergy_note_map.get(lang, synergy_note_map["en"])

    TEMPLATES = {
        "en": (
            f"Great news! Based on your profile, you are eligible for {count} government scheme(s): "
            f"{scheme_names}. "
            f"Combined, these can provide up to ₹{formatted_total} in annual benefits."
            f"{synergy_note}"
        ),
        "hi": (
            f"बढ़िया खबर! आपकी जानकारी के आधार पर, आप {count} सरकारी योजना(ओं) के लिए पात्र हैं: "
            f"{scheme_names}। "
            f"मिलाकर, ये योजनाएं आपको सालाना ₹{formatted_total} तक का लाभ दे सकती हैं।"
            f"{synergy_note}"
        ),
    }

    return TEMPLATES.get(lang, TEMPLATES["en"])


def _format_inr(amount: int) -> str:
    """Format a number in Indian grouping: 1,23,456."""
    s = str(amount)
    if len(s) <= 3:
        return s
    last3 = s[-3:]
    rest = s[:-3]
    groups = []
    while rest:
        groups.insert(0, rest[-2:])
        rest = rest[:-2]
    return ",".join(groups) + "," + last3


def _empty_result(lang: str) -> dict:
    msg = {
        "en": "No schemes available at this time.",
        "hi": "इस समय कोई योजना उपलब्ध नहीं है।",
    }
    return {
        "totalAnnualBenefit": 0,
        "eligibleCount": 0,
        "eligibleSchemes": [],
        "synergies": [],
        "summaryText": msg.get(lang, msg["en"]),
    }
