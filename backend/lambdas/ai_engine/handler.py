"""AI Engine Lambda — Core conversation handler using Amazon Bedrock Claude.

Processes user messages through the conversation state machine,
calls Bedrock Claude for natural language understanding & generation,
and manages scheme matching, eligibility, and form filling.
"""

import json
import logging
import os
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import boto3
from botocore.exceptions import ClientError

from prompts import SYSTEM_PROMPT, STATE_PROMPTS, SCHEMES_CONTEXT_TEMPLATE
from scheme_matcher import search_schemes, get_scheme_by_id, get_all_schemes, get_schemes_summary
from eligibility import check_eligibility, match_schemes_to_profile
from benefit_stacker import compute_benefit_stack
from form_filler import validate_field, get_next_field, get_form_progress, format_form_summary

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment
REGION = os.environ.get("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
BEDROCK_FALLBACK_MODEL_ID = os.environ.get("BEDROCK_FALLBACK_MODEL_ID", "amazon.nova-lite-v1:0")
SCHEMES_TABLE = os.environ.get("SCHEMES_TABLE", "vaanisetu-schemes")
APPLICATIONS_TABLE = os.environ.get("APPLICATIONS_TABLE", "vaanisetu-applications")
GUARDRAIL_ID = os.environ.get("GUARDRAIL_ID", "")
GUARDRAIL_VERSION = os.environ.get("GUARDRAIL_VERSION", "1")

# AWS clients
_bedrock = boto3.client("bedrock-runtime", region_name=REGION)
_dynamodb = boto3.resource("dynamodb", region_name=REGION)
_applications_table = _dynamodb.Table(APPLICATIONS_TABLE)


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


def _sanitize_for_bedrock(obj):
    """Recursively convert Decimal → int/float so Bedrock converse() can serialize it.

    DynamoDB returns Decimal for all numbers; boto3's converse API rejects them.
    """
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    if isinstance(obj, dict):
        return {k: _sanitize_for_bedrock(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_bedrock(i) for i in obj]
    return obj


def _clean_ai_response(text: str) -> str:
    """Clean up raw AI model output.

    Strips <thinking> tags and extracts clean text from JSON-wrapped responses.
    Some models (especially Nova) wrap their reply in JSON or add reasoning tags.
    """
    if not text:
        return text

    # 1. Strip <thinking>...</thinking> blocks
    text = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL).strip()

    # 2. If the model returned a JSON object with a "response" key, extract it
    if text.startswith("{") and text.endswith("}"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict) and "response" in parsed:
                text = parsed["response"]
        except (json.JSONDecodeError, KeyError):
            pass

    # 3. Strip leading/trailing whitespace and stray newlines
    text = text.strip()

    return text


# ── Bedrock Tool Definitions ─────────────────────────────────────────
TOOLS = [
    {
        "toolSpec": {
            "name": "search_schemes",
            "description": "Search government schemes matching the user's needs. Use this when the user describes their situation or needs.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "User's need in natural language"},
                        "category": {
                            "type": "string",
                            "description": "Scheme category",
                            "enum": ["agriculture", "housing", "healthcare", "finance", "education", "food", "energy", "savings", "insurance"]
                        },
                    },
                    "required": ["query"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "check_eligibility",
            "description": "Check if a user is eligible for a specific government scheme based on their profile.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "scheme_id": {"type": "string", "description": "The scheme ID to check eligibility for"},
                    },
                    "required": ["scheme_id"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "validate_field",
            "description": "Validate a form field value (e.g., Aadhaar number, phone number, IFSC code).",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "field_type": {
                            "type": "string",
                            "description": "Type of field to validate",
                            "enum": ["aadhaar", "phone", "ifsc", "pincode", "name", "date", "amount", "land_size", "bank_account", "state", "text"]
                        },
                        "value": {"type": "string", "description": "The value to validate"},
                    },
                    "required": ["field_type", "value"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "submit_application",
            "description": "Submit the completed application form for a government scheme.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "scheme_id": {"type": "string", "description": "The scheme ID"},
                        "form_data": {"type": "object", "description": "The completed form data"},
                    },
                    "required": ["scheme_id", "form_data"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "send_sms",
            "description": "Send an SMS confirmation to the user with application details.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "phone_number": {"type": "string", "description": "User's phone number"},
                        "message": {"type": "string", "description": "SMS message content"},
                    },
                    "required": ["phone_number", "message"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "get_benefit_stack",
            "description": "Calculate the TOTAL combined annual benefit from ALL eligible government schemes for this user. Use this proactively when users ask about their overall benefits, how many schemes they qualify for, or what their total entitlement is. Shows synergies between schemes.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "update_user_profile",
            "description": "Extract and store structured user details from the conversation. ALWAYS call this tool BEFORE check_eligibility when the user provides personal information like occupation, location, income, land size, family details, etc. The stored profile is used by check_eligibility to assess scheme eligibility.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "occupation": {"type": "string", "description": "User's occupation: farmer, laborer, business_owner, student, unemployed, etc."},
                        "state": {"type": "string", "description": "Indian state name in English, e.g. Bihar, Uttar Pradesh, Tamil Nadu"},
                        "district": {"type": "string", "description": "District name"},
                        "annualIncome": {"type": "number", "description": "Annual income in INR"},
                        "landSize": {"type": "number", "description": "Land size in acres (0 if landless)"},
                        "familySize": {"type": "number", "description": "Number of family members"},
                        "age": {"type": "number", "description": "User's age"},
                        "gender": {"type": "string", "description": "male or female"},
                        "casteCategory": {"type": "string", "description": "SC, ST, OBC, General"},
                        "isBPL": {"type": "boolean", "description": "Whether the user is Below Poverty Line"}
                    },
                    "required": []
                }
            }
        }
    },
]


def handler(event, context):
    """Main AI Engine handler — processes a user message and returns AI response."""
    logger.info(f"AI Engine event: {json.dumps(event, default=str)[:500]}")

    try:
        # ── Special action dispatch (non-conversation) ───────────
        action = event.get("action")
        if action == "benefit_stack":
            user_profile = event.get("userProfile", {})
            language = event.get("language", "hi-IN")
            return compute_benefit_stack(user_profile, language)

        session_id = event["sessionId"]
        user_message = event["userMessage"]
        language = event.get("language", "hi-IN")
        conversation_state = event.get("conversationState", "GREETING")
        conversation_history = event.get("conversationHistory", [])
        user_profile = event.get("userProfile", {})
        matched_schemes = event.get("matchedSchemes", [])
        selected_scheme = event.get("selectedScheme")
        form_data = event.get("formData", {})
        sentiment = event.get("sentiment", {})

        # ── Quick Scheme Detection ───────────────────────────────
        # If the user mentions a specific scheme by name, override any
        # previously selected scheme and jump straight to FORM_FILL.
        # This is checked even when selectedScheme is already set so
        # the user can switch schemes (e.g. "I want PM Kisan" after
        # the AI auto-selected RKVY).
        scheme_just_detected = False
        if conversation_state in ("SCHEME_MATCH", "NEED_ASSESSMENT", "FORM_FILL", "ELIGIBILITY_CHECK"):
            detected = _detect_scheme_in_message(user_message)
            if detected and detected != selected_scheme:
                logger.info(
                    f"Quick scheme detection: {detected} "
                    f"(was: {selected_scheme}), advancing to FORM_FILL"
                )
                selected_scheme = detected
                conversation_state = "FORM_FILL"
                form_data = {}          # reset form for the new scheme
                scheme_just_detected = True
            elif detected and detected == selected_scheme and conversation_state != "FORM_FILL":
                conversation_state = "FORM_FILL"
                scheme_just_detected = True
                logger.info(f"Quick scheme detection (same): {detected}, advancing to FORM_FILL")

        # ── Deterministic Form Processing ────────────────────────
        # When in FORM_FILL state, handle form input WITHOUT calling
        # Bedrock at all. This ensures:
        #   1. Fields are filled in strict sequential order
        #   2. form_data is keyed by field ID (not type), avoiding collisions
        #   3. Responses are 100% deterministic (no hallucination)
        #   4. Faster + cheaper (no Bedrock call for form turns)
        if conversation_state == "FORM_FILL" and selected_scheme:
            if scheme_just_detected:
                # Scheme was just selected in THIS message — don't treat
                # the message as a form field value. Pre-populate known
                # fields and ask for the first one.
                scheme_obj = get_scheme_by_id(selected_scheme)
                ffields = scheme_obj.get("formFields", []) if scheme_obj else []
                sname = scheme_obj.get("name", {}).get("en", selected_scheme) if scheme_obj else selected_scheme
                lang_key = language[:2] if language else "en"
                # Pre-populate from user profile
                if ffields and user_profile:
                    for pk, fid in {"state": "state", "landSize": "landSize"}.items():
                        if fid not in form_data and pk in user_profile:
                            val = str(user_profile[pk])
                            matching = [f for f in ffields if f["id"] == fid]
                            if matching:
                                vr = validate_field(matching[0]["type"], val)
                                if vr["valid"]:
                                    form_data[fid] = vr["normalized"]
                nf = get_next_field(ffields, form_data) if ffields else None
                progress = get_form_progress(ffields, form_data) if ffields else None
                if nf:
                    q = nf.get("question", {})
                    fq = q.get(lang_key, q.get("en", nf["id"])) if isinstance(q, dict) else str(q)
                    n = (progress["completed"] + 1) if progress else 1
                    t = progress["total"] if progress else len(ffields)
                    if lang_key == "hi":
                        resp_text = f"बढ़िया! चलिए {sname} का आवेदन भरते हैं। सवाल {n}/{t}: {fq}"
                    else:
                        resp_text = f"Great! Let's fill the {sname} application. Question {n} of {t}: {fq}"
                else:
                    resp_text = "All fields are already complete. Please confirm."
                return {
                    "response": resp_text,
                    "conversationState": "FORM_FILL",
                    "userProfile": user_profile,
                    "matchedSchemes": matched_schemes,
                    "selectedScheme": selected_scheme,
                    "formData": form_data,
                    "formProgress": progress,
                    "applicationId": None,
                }
            else:
                # Normal form turn — validate input deterministically
                result = _process_form_input(
                    selected_scheme, form_data, user_message, language,
                    user_profile=user_profile,
                )
                if result.get("response"):
                    return {
                        "response": result["response"],
                        "conversationState": result["next_state"],
                        "userProfile": user_profile,
                        "matchedSchemes": matched_schemes,
                        "selectedScheme": selected_scheme,
                        "formData": result["form_data"],
                        "formProgress": result["progress"],
                        "applicationId": None,
                    }

        # ── Deterministic Submission on REVIEW confirm ───────────
        # When the user confirms during REVIEW, submit immediately
        # rather than relying on the AI to call submit_application.
        if conversation_state == "REVIEW" and selected_scheme:
            confirm_words = [
                "yes", "correct", "sahi", "theek", "haan", "ha", "ok",
                "confirm", "submit", "जी", "हां", "ठीक", "सही", "सब ठीक",
            ]
            msg_lower = user_message.lower().strip()
            if any(w in msg_lower for w in confirm_words):
                application = _submit_application(session_id, selected_scheme, form_data)
                app_id = application.get("applicationId", "")
                scheme_name = application.get("schemeName", selected_scheme)
                lang = language[:2] if language else "en"
                if lang == "hi":
                    resp_text = (
                        f"बधाई हो! 🎉 आपका आवेदन सफलतापूर्वक जमा हो गया है।\n"
                        f"आवेदन ID: {app_id}\n"
                        f"योजना: {scheme_name}\n"
                        f"आपको SMS द्वारा पुष्टि भेजी जाएगी।"
                    )
                else:
                    resp_text = (
                        f"Congratulations! 🎉 Your application has been submitted successfully.\n"
                        f"Application ID: {app_id}\n"
                        f"Scheme: {scheme_name}\n"
                        f"You will receive an SMS confirmation shortly."
                    )
                return {
                    "response": resp_text,
                    "conversationState": "COMPLETE",
                    "userProfile": user_profile,
                    "matchedSchemes": None,
                    "selectedScheme": selected_scheme,
                    "formData": form_data,
                    "formProgress": None,
                    "applicationId": app_id,
                }

        # Build context for the AI (uses updated form_data from above)
        context_info = _build_context(
            conversation_state, user_profile, matched_schemes,
            selected_scheme, form_data, language, sentiment
        )

        try:
            # Determine which tools to provide based on conversation state
            has_precomputed = "Pre-computed Eligibility Results" in context_info

            # ── Pre-Bedrock state correction ──────────────────────
            # The state from the session is always one turn behind. When the
            # user already has a rich profile and pre-computed schemes, advance
            # the state so the correct tools are available for THIS turn.
            if conversation_state in ("GREETING", "NEED_ASSESSMENT") and has_precomputed:
                if selected_scheme or form_data:
                    conversation_state = "FORM_FILL"
                elif len(user_profile) >= 3:
                    conversation_state = "SCHEME_MATCH"

            state_tools = _get_tools_for_state(conversation_state, has_precomputed)
            logger.info(f"State: {conversation_state}, tools: {[t['toolSpec']['name'] for t in state_tools]}, precomputed: {has_precomputed}")

            # Call Bedrock
            response = _invoke_bedrock(
                user_message=user_message,
                conversation_history=conversation_history,
                context_info=context_info,
                language=language,
                tools=state_tools if state_tools else None,
            )

            # Process tool calls if any
            result = _process_response(
                response=response,
                session_id=session_id,
                user_message=user_message,
                user_profile=user_profile,
                matched_schemes=matched_schemes,
                selected_scheme=selected_scheme,
                form_data=form_data,
                language=language,
                conversation_state=conversation_state,
                conversation_history=conversation_history,
                context_info=context_info,
            )

            logger.info(f"AI response state: {result.get('conversationState')}")
            return result

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "ThrottlingException":
                logger.warning(f"Bedrock throttled, using smart fallback for: {user_message}")
                return _fallback_response(
                    user_message=user_message,
                    language=language,
                    conversation_state=conversation_state,
                    user_profile=user_profile,
                    matched_schemes=matched_schemes,
                    selected_scheme=selected_scheme,
                    form_data=form_data,
                    session_id=session_id,
                )
            raise

    except Exception as e:
        logger.exception(f"AI Engine error: {e}")
        return {
            "response": "क्षमा करें, कुछ गड़बड़ हो गई। कृपया फिर से कोशिश करें। (Sorry, something went wrong. Please try again.)",
            "conversationState": "ERROR",
        }


def _fallback_response(
    user_message: str,
    language: str,
    conversation_state: str,
    user_profile: dict,
    matched_schemes: list,
    selected_scheme: str,
    form_data: dict,
    session_id: str,
) -> dict:
    """Smart rule-based fallback when Bedrock is throttled.

    Uses keyword matching to find relevant schemes and returns
    structured responses without AI generation.
    """
    lang = language[:2] if language else "hi"
    query_lower = user_message.lower()

    # ── Category detection from user message ───────────────────────
    CATEGORY_KEYWORDS = {
        "agriculture": [
            "खेती", "किसान", "kisan", "farming", "farmer", "crop", "फसल", "कृषि", "agriculture", "खाद",
            "চাষ", "কৃষি", "কৃষক",  # Bengali
            "వ్యవసాయం", "రైతు", "పంట",  # Telugu
            "शेती", "शेतकरी",  # Marathi
            "ಕೃಷಿ", "ರೈತ", "ಬೆಳೆ",  # Kannada
            "കൃഷി", "കർഷകൻ", "വിള",  # Malayalam
        ],
        "housing": [
            "मकान", "घर", "house", "housing", "आवास", "ghar", "awas", "home",
            "বাড়ি", "আবাসন",  # Bengali
            "ఇల్లు", "గృహం",  # Telugu
            "घर", "गृहनिर्माण",  # Marathi
            "ಮನೆ", "ವಸತಿ",  # Kannada
            "വീട്", "ഭവനം",  # Malayalam
        ],
        "healthcare": [
            "स्वास्थ्य", "health", "hospital", "बीमारी", "doctor", "इलाज", "ayushman", "आयुष्मान", "treatment",
            "স্বাস্থ্য", "চিকিৎসা", "হাসপাতাল",  # Bengali
            "ఆరోగ్యం", "వైద్యం", "ఆసుపత్రి",  # Telugu
            "आरोग्य", "उपचार",  # Marathi
            "ಆರೋಗ್ಯ", "ಚಿಕಿತ್ಸೆ",  # Kannada
            "ആരോഗ്യം", "ചികിത്സ",  # Malayalam
        ],
        "finance": [
            "ऋण", "loan", "पैसा", "money", "business", "व्यापार", "mudra", "मुद्रा", "कर्ज",
            "ঋণ", "টাকা", "ব্যবসা",  # Bengali
            "రుణం", "డబ్బు", "వ్యాపారం",  # Telugu
            "कर्ज", "पैसा", "व्यवसाय",  # Marathi
            "ಸಾಲ", "ಹಣ", "ವ್ಯಾಪಾರ",  # Kannada
            "വായ്പ", "പണം", "ബിസിനസ്",  # Malayalam
        ],
        "food": [
            "राशन", "अनाज", "food", "ration", "खाना", "garib", "anna", "अन्न",
            "রেশন", "খাবার", "খাদ্য",  # Bengali
            "రేషన్", "ఆహారం",  # Telugu
            "रेशन", "अन्न", "धान्य",  # Marathi
            "ಪಡಿತರ", "ಆಹಾರ",  # Kannada
            "റേഷൻ", "ഭക്ഷണം",  # Malayalam
        ],
        "energy": [
            "गैस", "gas", "एलपीजी", "LPG", "ujjwala", "उज्ज्वला", "सिлेंडर", "cylinder",
            "গ্যাস", "সিলিন্ডার",  # Bengali
            "గ్యాస్", "సిలిండర్",  # Telugu
            "गॅस", "सिलिंडर",  # Marathi
            "ಗ್ಯಾಸ್", "ಸಿಲಿಂಡರ್",  # Kannada
            "ഗ്യാസ്", "സിലിണ്ടർ",  # Malayalam
        ],
        "savings": [
            "बचत", "savings", "बेटी", "daughter", "girl", "sukanya", "सुकन्या",
            "সঞ্চয়", "মেয়ে",  # Bengali
            "పొదుపు", "కూతురు",  # Telugu
            "बचत", "मुलगी",  # Marathi
            "ಉಳಿತಾಯ", "ಮಗಳು",  # Kannada
            "സമ്പാദ്യം", "മകൾ",  # Malayalam
        ],
        "insurance": [
            "बीमा", "insurance", "fasal bima", "फसल बीमा", "crop insurance",
            "বীমা", "ফসল বীমা",  # Bengali
            "భీమా", "పంట భీమా",  # Telugu
            "विमा", "पीक विमा",  # Marathi
            "ವಿಮೆ", "ಬೆಳೆ ವಿಮೆ",  # Kannada
            "ഇൻഷുറൻസ്", "വിള ഇൻഷുറൻസ്",  # Malayalam
        ],
    }

    detected_category = None
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in query_lower:
                detected_category = cat
                break
        if detected_category:
            break

    # ── Search schemes ─────────────────────────────────────────────
    schemes = search_schemes(user_message, detected_category, language=lang)

    # If no results from keyword, get all schemes as context
    if not schemes:
        schemes = get_all_schemes()

    # ── Build response based on conversation state ─────────────────
    if conversation_state == "GREETING" or not matched_schemes:
        # Show matching schemes
        if schemes:
            scheme_list = []
            for i, s in enumerate(schemes[:5], 1):
                name = s.get("name", {}).get(lang, s.get("name", {}).get("en", ""))
                desc = s.get("shortDescription", s.get("description", {})).get(lang, "")
                if not desc:
                    desc = s.get("shortDescription", s.get("description", {})).get("en", "")
                scheme_list.append(f"{i}. **{name}** — {desc}")

            if lang == "hi":
                intro = "आपकी ज़रूरत के अनुसार ये सरकारी योजनाएं मिली हैं:"
                outro = "\nकिसी भी योजना का नंबर बताएं, मैं उसकी पूरी जानकारी दूंगी। उदाहरण: '1 बताओ' या योजना का नाम बताएं।"
            elif lang == "bn":
                intro = "আপনার প্রয়োজন অনুযায়ী এই সরকারি প্রকল্পগুলি পাওয়া গেছে:"
                outro = "\nযেকোনো প্রকল্পের নম্বর বলুন, আমি বিস্তারিত জানাবো। উদাহরণ: '1 বলুন' বা প্রকল্পের নাম বলুন।"
            elif lang == "te":
                intro = "మీ అవసరానికి తగిన ప్రభుత్వ పథకాలు ఇవి:"
                outro = "\nఏదైనా పథకం నంబర్ చెప్పండి, నేను పూర్తి వివరాలు చెప్తాను. ఉదా: '1 చెప్పండి' లేదా పథకం పేరు చెప్పండి."
            elif lang == "mr":
                intro = "तुमच्या गरजेनुसार या सरकारी योजना सापडल्या:"
                outro = "\nकोणत्याही योजनेचा क्रमांक सांगा, मी पूर्ण माहिती देईन. उदा: '1 सांगा' किंवा योजनेचे नाव सांगा."
            elif lang == "kn":
                intro = "ನಿಮ್ಮ ಅಗತ್ಯಕ್ಕೆ ತಕ್ಕ ಸರ್ಕಾರಿ ಯೋಜನೆಗಳು ಇಲ್ಲಿವೆ:"
                outro = "\nಯಾವುದೇ ಯೋಜನೆಯ ಸಂಖ್ಯೆ ಹೇಳಿ, ನಾನು ಪೂರ್ಣ ವಿವರ ನೀಡುತ್ತೇನೆ. ಉದಾ: '1 ಹೇಳಿ' ಅಥವಾ ಯೋಜನೆ ಹೆಸರು ಹೇಳಿ."
            elif lang == "ml":
                intro = "നിങ്ങളുടെ ആവശ്യത്തിന് അനുയോജ്യമായ സർക്കാർ പദ്ധതികൾ:"
                outro = "\nഏതെങ്കിലും പദ്ധതിയുടെ നമ്പർ പറയൂ, ഞാൻ പൂർണ്ണ വിവരം നൽകാം. ഉദാ: '1 പറയൂ' അല്ലെങ്കിൽ പദ്ധതിയുടെ പേര് പറയൂ."
            elif lang == "ta":
                intro = "உங்கள் தேவைக்கேற்ற அரசு திட்டங்கள்:"
                outro = "\nஎந்த திட்டத்தின் எண்ணையும் சொல்லுங்கள், விவரங்கள் தருகிறேன். உதா: '1 சொல்லுங்கள்' அல்லது திட்ட பெயரை சொல்லுங்கள்."
            else:
                intro = "Here are relevant government schemes for you:"
                outro = "\nTell me the scheme number for more details, e.g., 'tell me about 1' or say the scheme name."

            response_text = f"{intro}\n\n" + "\n".join(scheme_list) + outro

            # Build matched schemes in the expected format
            matched = []
            for s in schemes[:5]:
                matched.append({
                    "schemeId": s["schemeId"],
                    "name": s["name"].get(lang, s["name"].get("en", "")),
                    "shortDescription": s.get("shortDescription", {}).get(lang, ""),
                    "category": s.get("category", ""),
                })

            return {
                "response": response_text,
                "conversationState": "SCHEME_MATCH",
                "userProfile": user_profile,
                "matchedSchemes": matched,
                "selectedScheme": selected_scheme,
                "formData": form_data,
                "formProgress": None,
                "applicationId": None,
            }

    # ── Scheme selection (user might be asking about a specific scheme) ─
    if matched_schemes and conversation_state in ("SCHEME_MATCH", "NEED_ASSESSMENT"):
        # Normalize matched_schemes: orchestrator may store as string IDs
        # (e.g. ["PM-KISAN", "RKVY"]) instead of full objects.
        normalized_schemes = []
        for s in matched_schemes:
            if isinstance(s, str):
                full = get_scheme_by_id(s)
                if full:
                    normalized_schemes.append({
                        "schemeId": full["schemeId"],
                        "name": full["name"].get(lang, full["name"].get("en", "")),
                        "shortDescription": full.get("shortDescription", {}).get(lang, ""),
                        "category": full.get("category", ""),
                    })
            elif isinstance(s, dict):
                normalized_schemes.append(s)
        matched_schemes = normalized_schemes

        # Try to find which scheme the user selected
        selected = None
        for s in matched_schemes:
            s_name = s.get("name", "").lower() if isinstance(s.get("name"), str) else ""
            s_id = s.get("schemeId", "").lower()
            if s_name and s_name in query_lower:
                selected = s
                break
            if s_id and s_id.lower() in query_lower:
                selected = s
                break

        # Check numeric selection like "1", "2", "1 बताओ", "pahla"
        if not selected:
            import re as _re
            # Try "N बताओ" pattern first (e.g. "1 बताओ", "2 बताओ")
            batao_match = _re.search(r'(\d)\s*बताओ', query_lower)
            if batao_match:
                idx = int(batao_match.group(1)) - 1
                if 0 <= idx < len(matched_schemes):
                    selected = matched_schemes[idx]

            if not selected:
                num_map = {"1": 0, "2": 1, "3": 2, "4": 3, "5": 4,
                           "pahla": 0, "dusra": 1, "teesra": 2,
                           "पहला": 0, "दूसरा": 1, "तीसरा": 2, "चौथा": 3, "पांचवा": 4,
                           "first": 0, "second": 1, "third": 2,
                           # Bengali ordinals
                           "প্রথম": 0, "দ্বিতীয়": 1, "তৃতীয়": 2,
                           # Telugu ordinals
                           "మొదటి": 0, "రెండవ": 1, "మూడవ": 2,
                           # Marathi ordinals
                           "पहिला": 0, "दुसरा": 1, "तिसरा": 2,
                           # Kannada ordinals
                           "ಮೊದಲ": 0, "ಎರಡನೆ": 1, "ಮೂರನೆ": 2,
                           # Malayalam ordinals
                           "ഒന്നാമത്തെ": 0, "രണ്ടാമത്തെ": 1, "മൂന്നാമത്തെ": 2,
                           # Tamil ordinals
                           "முதல்": 0, "இரண்டாவது": 1, "மூன்றாவது": 2,
                           }
                for key, idx in num_map.items():
                    if key in query_lower and idx < len(matched_schemes):
                        selected = matched_schemes[idx]
                        break

        if selected:
            scheme_id = selected.get("schemeId", "")
            full_scheme = get_scheme_by_id(scheme_id)
            if full_scheme:
                name = full_scheme["name"].get(lang, full_scheme["name"].get("en", ""))
                desc = full_scheme.get("description", {}).get(lang, full_scheme.get("description", {}).get("en", ""))
                benefits = full_scheme.get("benefits", {}).get(lang, full_scheme.get("benefits", {}).get("en", ""))

                elig_rules = full_scheme.get("eligibilityRules", [])
                elig_text = "\n".join([f"  • {rule}" for rule in elig_rules]) if elig_rules else ""

                # ── Multi-language response templates ──
                DETAIL_TEMPLATES = {
                    "hi": {
                        "desc_label": "📋 विवरण",
                        "benefits_label": "✅ लाभ",
                        "elig_label": "📌 पात्रता",
                        "apply_prompt": "क्या आप इस योजना के लिए आवेदन करना चाहते हैं? 'हां' बोलें।",
                    },
                    "bn": {
                        "desc_label": "📋 বিবরণ",
                        "benefits_label": "✅ সুবিধা",
                        "elig_label": "📌 যোগ্যতা",
                        "apply_prompt": "আপনি কি এই প্রকল্পের জন্য আবেদন করতে চান? 'হ্যাঁ' বলুন।",
                    },
                    "te": {
                        "desc_label": "📋 వివరణ",
                        "benefits_label": "✅ ప్రయోజనాలు",
                        "elig_label": "📌 అర్హత",
                        "apply_prompt": "ఈ పథకానికి దరఖాస్తు చేయాలనుకుంటున్నారా? 'అవును' అని చెప్పండి.",
                    },
                    "mr": {
                        "desc_label": "📋 वर्णन",
                        "benefits_label": "✅ फायदे",
                        "elig_label": "📌 पात्रता",
                        "apply_prompt": "तुम्हाला या योजनेसाठी अर्ज करायचा आहे का? 'होय' म्हणा.",
                    },
                    "kn": {
                        "desc_label": "📋 ವಿವರಣೆ",
                        "benefits_label": "✅ ಪ್ರಯೋಜನಗಳು",
                        "elig_label": "📌 ಅರ್ಹತೆ",
                        "apply_prompt": "ಈ ಯೋಜನೆಗೆ ಅರ್ಜಿ ಸಲ್ಲಿಸಲು ಬಯಸುವಿರಾ? 'ಹೌದು' ಎನ್ನಿ.",
                    },
                    "ml": {
                        "desc_label": "📋 വിവരണം",
                        "benefits_label": "✅ ആനുകൂല്യങ്ങൾ",
                        "elig_label": "📌 യോഗ്യത",
                        "apply_prompt": "ഈ പദ്ധതിക്ക് അപേക്ഷിക്കാൻ ആഗ്രഹിക്കുന്നുണ്ടോ? 'അതെ' എന്ന് പറയൂ.",
                    },
                    "ta": {
                        "desc_label": "📋 விவரம்",
                        "benefits_label": "✅ பலன்கள்",
                        "elig_label": "📌 தகுதி",
                        "apply_prompt": "இந்த திட்டத்திற்கு விண்ணப்பிக்க விரும்புகிறீர்களா? 'ஆம்' என்று சொல்லுங்கள்.",
                    },
                    "en": {
                        "desc_label": "Description",
                        "benefits_label": "Benefits",
                        "elig_label": "Eligibility",
                        "apply_prompt": "Would you like to apply for this scheme? Say 'yes'.",
                    },
                }
                tmpl = DETAIL_TEMPLATES.get(lang, DETAIL_TEMPLATES["en"])
                response_text = (
                    f"**{name}**\n\n"
                    f"{tmpl['desc_label']}: {desc}\n\n"
                    f"{tmpl['benefits_label']}: {benefits}\n\n"
                )
                if elig_text:
                    response_text += f"{tmpl['elig_label']}:\n{elig_text}\n\n"
                response_text += tmpl["apply_prompt"]

                return {
                    "response": response_text,
                    "conversationState": "ELIGIBILITY_CHECK",
                    "userProfile": user_profile,
                    "matchedSchemes": matched_schemes,
                    "selectedScheme": scheme_id,
                    "formData": form_data,
                    "formProgress": None,
                    "applicationId": None,
                }

    # ── Form filling state ─────────────────────────────────────────
    if conversation_state == "FORM_FILL" and selected_scheme:
        scheme = get_scheme_by_id(selected_scheme)
        if scheme:
            form_fields = scheme.get("formFields", [])
            next_field = get_next_field(form_fields, form_data)
            if next_field:
                field_label = next_field.get("question", {}).get(lang, next_field.get("question", {}).get("en", next_field.get("id", "")))
                if lang == "hi":
                    response_text = f"कृपया अपना {field_label} बताएं:"
                else:
                    response_text = f"Please provide your {field_label}:"

                return {
                    "response": response_text,
                    "conversationState": "FORM_FILL",
                    "userProfile": user_profile,
                    "matchedSchemes": matched_schemes,
                    "selectedScheme": selected_scheme,
                    "formData": form_data,
                    "formProgress": get_form_progress(form_fields, form_data),
                    "applicationId": None,
                }

    # ── Default fallback ───────────────────────────────────────────
    all_schemes = get_all_schemes()
    scheme_names = [s["name"].get(lang, s["name"].get("en", "")) for s in all_schemes[:10]]
    if lang == "hi":
        response_text = (
            "मैं वाणी सेतु हूँ — सरकारी योजनाओं की जानकारी के लिए आपकी AI सहायक।\n\n"
            "मेरे पास इन योजनाओं की जानकारी है:\n"
            + "\n".join([f"  {i+1}. {n}" for i, n in enumerate(scheme_names)])
            + "\n\nआपको किस तरह की मदद चाहिए? किसान, स्वास्थ्य, आवास, राशन, या कोई और — बताएं!"
        )
    else:
        response_text = (
            "I'm VaaniSetu — your AI assistant for government schemes.\n\n"
            "I have information about these schemes:\n"
            + "\n".join([f"  {i+1}. {n}" for i, n in enumerate(scheme_names)])
            + "\n\nWhat kind of help do you need? Agriculture, health, housing, food, or others — tell me!"
        )

    return {
        "response": response_text,
        "conversationState": "NEED_ASSESSMENT",
        "userProfile": user_profile,
        "matchedSchemes": None,
        "selectedScheme": selected_scheme,
        "formData": form_data,
        "formProgress": None,
        "applicationId": None,
    }


# ── Conversational phrases that indicate "yes, go ahead" not a field value ──
_CONVERSATIONAL_STARTERS = {
    "yes", "ok", "sure", "start", "apply", "begin", "let's", "lets",
    "haan", "ji", "ha", "theek", "shuru", "chalo", "karo",
    "हां", "जी", "ठीक", "शुरू", "चलो", "करो", "आवेदन",
    "ஆமா", "சரி", "yes please", "okay", "go ahead", "proceed",
    "want", "kisan", "pm-kisan", "pm kisan",
}

# ── Scheme name patterns for quick detection ────────────────────────
_SCHEME_KEYWORDS = {
    "PM-KISAN": ["pm kisan", "pm-kisan", "pmkisan", "kisan yojana", "किसान सम्मान", "पीएम किसान"],
    "PM-AWAS-GRAMIN": ["pm awas", "pm-awas", "awas yojana", "pmay", "प्रधानमंत्री आवास", "housing scheme"],
    "RKVY": ["rkvy", "rashtriya krishi", "राष्ट्रीय कृषि"],
    "PM-FASAL-BIMA": ["fasal bima", "pm-fasal", "crop insurance", "फसल बीमा"],
    "SOIL-HEALTH-CARD": ["soil health", "मृदा स्वास्थ्य", "soil card"],
    "PM-UJJWALA": ["ujjwala", "उज्ज्वला", "gas cylinder", "lpg"],
    "AYUSHMAN-BHARAT": ["ayushman", "आयुष्मान", "health card", "pmjay"],
    "PM-MUDRA": ["mudra", "मुद्रा", "mudra loan", "business loan"],
    "SUKANYA-SAMRIDDHI": ["sukanya", "सुकन्या", "girl child"],
    "PM-GARIB-KALYAN-ANNA": ["garib kalyan", "anna yojana", "ration", "अन्न योजना", "free ration"],
}


def _detect_scheme_in_message(message: str) -> str:
    """Detect if the user mentions a specific scheme name.

    Returns the scheme ID if found, empty string otherwise.
    """
    msg_lower = message.lower()
    for scheme_id, keywords in _SCHEME_KEYWORDS.items():
        if any(kw in msg_lower for kw in keywords):
            return scheme_id
    return ""


def _process_form_input(
    selected_scheme: str, form_data: dict, user_message: str, language: str,
    user_profile: dict = None,
) -> dict:
    """Deterministic form field processing — validates and returns a response.

    Returns a dict with:
      - response: the natural-language text to show the user
      - next_state: "FORM_FILL" or "REVIEW"
      - form_data: the (possibly updated) form data dict
      - progress: the form progress dict

    Why this exists: Letting the AI model decide which field to validate was
    unreliable (collisions, wrong order, hallucinated questions). This
    function bypasses Bedrock entirely for form filling, making responses
    100% deterministic, faster, and cheaper.
    """
    empty = {"response": "", "next_state": "FORM_FILL", "form_data": form_data, "progress": None}

    if not selected_scheme:
        return empty

    scheme = get_scheme_by_id(selected_scheme)
    if not scheme:
        return empty

    form_fields = scheme.get("formFields", [])
    if not form_fields:
        return empty

    lang_key = language[:2] if language else "en"
    scheme_name = scheme.get("name", {}).get("en", selected_scheme)

    # ── Pre-populate form_data from user_profile ─────────────────
    if user_profile:
        _PROFILE_TO_FORM = {
            "state": "state",
            "district": "district",
            "landSize": "landSize",
        }
        for profile_key, field_id in _PROFILE_TO_FORM.items():
            if field_id not in form_data and profile_key in user_profile:
                val = str(user_profile[profile_key])
                matching_fields = [f for f in form_fields if f["id"] == field_id]
                if matching_fields:
                    vr = validate_field(matching_fields[0]["type"], val)
                    if vr["valid"]:
                        form_data[field_id] = vr["normalized"]
                        logger.info(f"Pre-filled form field '{field_id}' from user_profile")

    current_field = get_next_field(form_fields, form_data)
    progress = get_form_progress(form_fields, form_data)

    if not current_field:
        # All fields already filled → review
        summary = format_form_summary(form_fields, form_data, lang_key)
        if lang_key == "hi":
            resp = f"सभी {progress['total']} फील्ड भरे गए हैं। कृपया जानकारी की पुष्टि करें:\n\n{summary}\n\nक्या सब सही है?"
        else:
            resp = f"All {progress['total']} fields are complete. Please review your information:\n\n{summary}\n\nIs everything correct?"
        return {"response": resp, "next_state": "REVIEW", "form_data": form_data, "progress": progress}

    current_q = current_field["question"].get(
        lang_key, current_field["question"].get("en", current_field["id"])
    )

    # ── Validate user input ──────────────────────────────────────
    validation = validate_field(current_field["type"], user_message)

    if validation["valid"]:
        # Check for conversational starters on the first name field
        if progress["completed"] == 0 and current_field["type"] == "name":
            msg_lower = user_message.lower().strip()
            if any(msg_lower.startswith(w) or msg_lower == w for w in _CONVERSATIONAL_STARTERS):
                # Treat as greeting, don't save — ask for first field
                if lang_key == "hi":
                    resp = f"बढ़िया! चलिए {scheme_name} का आवेदन भरते हैं। सवाल 1/{progress['total']}: {current_q}"
                else:
                    resp = f"Great! Let's fill the {scheme_name} form. Question 1 of {progress['total']}: {current_q}"
                return {"response": resp, "next_state": "FORM_FILL", "form_data": form_data, "progress": progress}

        # Accept the value
        form_data[current_field["id"]] = validation["normalized"]
        next_field = get_next_field(form_fields, form_data)
        new_progress = get_form_progress(form_fields, form_data)

        if next_field:
            next_q = next_field["question"].get(
                lang_key, next_field["question"].get("en", next_field["id"])
            )
            n = new_progress["completed"] + 1
            t = new_progress["total"]
            if lang_key == "hi":
                resp = f"धन्यवाद! सवाल {n}/{t}: {next_q}"
            else:
                resp = f"Thank you! Question {n} of {t}: {next_q}"
            return {"response": resp, "next_state": "FORM_FILL", "form_data": form_data, "progress": new_progress}
        else:
            # All fields complete → review
            summary = format_form_summary(form_fields, form_data, lang_key)
            if lang_key == "hi":
                resp = f"सभी फील्ड भरे गए! कृपया जानकारी की पुष्टि करें:\n\n{summary}\n\nक्या सब सही है?"
            else:
                resp = f"All fields are complete! Please review:\n\n{summary}\n\nIs everything correct?"
            return {"response": resp, "next_state": "REVIEW", "form_data": form_data, "progress": new_progress}
    else:
        # Validation failed
        if progress["completed"] == 0:
            msg_lower = user_message.lower().strip()
            is_conversational = any(
                msg_lower.startswith(w) or msg_lower == w
                for w in _CONVERSATIONAL_STARTERS
            )
            if is_conversational or len(msg_lower.split()) > 6:
                if lang_key == "hi":
                    resp = f"बढ़िया! चलिए {scheme_name} का आवेदन भरते हैं। सवाल 1/{progress['total']}: {current_q}"
                else:
                    resp = f"Great! Let's fill the {scheme_name} form. Question 1 of {progress['total']}: {current_q}"
                return {"response": resp, "next_state": "FORM_FILL", "form_data": form_data, "progress": progress}

        # Genuine validation error
        err = validation.get("message", validation.get("error", "Invalid input"))
        n = progress["completed"] + 1
        t = progress["total"]
        if lang_key == "hi":
            resp = f"यह मान्य नहीं है: {err}। कृपया फिर से प्रयास करें। सवाल {n}/{t}: {current_q}"
        else:
            resp = f"That doesn't look right: {err}. Please try again. Question {n} of {t}: {current_q}"
        return {"response": resp, "next_state": "FORM_FILL", "form_data": form_data, "progress": progress}


def _build_context(
    state: str, user_profile: dict, matched_schemes: list,
    selected_scheme: str, form_data: dict, language: str,
    sentiment: dict = None,
) -> str:
    """Build contextual information for Claude based on conversation state."""
    parts = []

    # ── Sentiment guidance (if available) ────────────────────────
    if sentiment and sentiment.get("sentiment"):
        mood = sentiment["sentiment"]
        TONE_MAP = {
            "POSITIVE": "The user sounds happy/positive. Match their enthusiasm and be encouraging.",
            "NEGATIVE": "The user sounds frustrated or upset. Be extra empathetic, patient, and reassuring. Acknowledge their difficulty.",
            "MIXED": "The user has mixed emotions. Be supportive and clear in your explanations.",
            "NEUTRAL": "",  # No special guidance needed
        }
        tone_hint = TONE_MAP.get(mood, "")
        if tone_hint:
            parts.append(f"## User Mood: {mood}\n{tone_hint}\n")

    # Schemes context
    lang_key = language[:2] if language else "en"
    schemes_summary = get_schemes_summary(lang_key)
    parts.append(SCHEMES_CONTEXT_TEMPLATE.format(schemes_list=schemes_summary))

    # ── PRE-COMPUTE scheme matches when we have a meaningful profile ────
    # This is the KEY speed optimization: by providing pre-computed eligibility
    # results in the context, the model does NOT need to call search_schemes or
    # check_eligibility tools (which would each require an extra Bedrock roundtrip).
    if user_profile and any(k in user_profile for k in ('occupation', 'state', 'landSize', 'annualIncome')):
        all_schemes = get_all_schemes()
        ranked = match_schemes_to_profile(all_schemes, user_profile)
        if ranked:
            pre_lines = []
            for s in ranked[:5]:
                name = s.get('name', {}).get(lang_key, s.get('name', {}).get('en', s['schemeId']))
                elig = 'ELIGIBLE' if s.get('eligible') else 'NOT ELIGIBLE'
                conf = s.get('confidence', 0)
                reason = s.get('reason', '')
                missing = s.get('missingInfo', [])
                benefit_amt = s.get('benefits', {}).get('amount', 'N/A')
                pre_lines.append(
                    f"- {s['schemeId']} ({name}): {elig} ({conf}% confidence). "
                    f"Benefit: ₹{benefit_amt}/year. {reason}"
                    + (f" Missing: {', '.join(missing)}" if missing else '')
                )
            parts.append(
                "\n## Pre-computed Eligibility Results\n"
                "The following eligibility analysis is ALREADY DONE based on the user's profile. "
                "Use these results directly — do NOT call search_schemes or check_eligibility "
                "unless the user asks about a scheme NOT listed here.\n"
                + "\n".join(pre_lines)
            )

    # State-specific context
    state_prompt = STATE_PROMPTS.get(state, "")
    if state_prompt:
        # Fill in template variables
        context_vars = {
            "questions_asked": len([k for k in user_profile if k not in ("language",)]),
            "user_profile": json.dumps(user_profile, ensure_ascii=False) if user_profile else "{}",
            "matched_schemes": json.dumps(matched_schemes, ensure_ascii=False, cls=DecimalEncoder) if matched_schemes else "[]",
            "selected_scheme": selected_scheme or "None",
            "form_data": json.dumps(form_data, ensure_ascii=False) if form_data else "{}",
            "eligibility_rules": "",
            "form_fields": "",
            "completed_fields": json.dumps(list(form_data.keys())) if form_data else "[]",
            "current_field": "",
            "completed": len(form_data),
            "total": 0,
            "application_id": "",
        }

        # Get scheme-specific context
        if selected_scheme:
            scheme = get_scheme_by_id(selected_scheme)
            if scheme:
                context_vars["eligibility_rules"] = json.dumps(
                    scheme.get("eligibilityRules", []), ensure_ascii=False, cls=DecimalEncoder
                )
                form_fields = scheme.get("formFields", [])
                context_vars["form_fields"] = json.dumps(form_fields, ensure_ascii=False)
                context_vars["total"] = len([f for f in form_fields if f.get("required", True)])

                next_field = get_next_field(form_fields, form_data)
                if next_field:
                    lang_key = language[:2] if language else "en"
                    context_vars["current_field"] = json.dumps(next_field, ensure_ascii=False)

        try:
            formatted = state_prompt.format(**context_vars)
            parts.append(f"\n## Current State: {state}\n{formatted}")
        except (KeyError, IndexError):
            parts.append(f"\n## Current State: {state}\n{state_prompt}")

    return "\n".join(parts)


def _get_tools_for_state(state: str, has_precomputed: bool) -> list:
    """Return only the tools relevant for the current conversation state.

    Why: Providing ALL tools to Bedrock every time causes the model to
    consider calling tools it doesn't need (e.g. search_schemes when we
    already have pre-computed results). Fewer tools → fewer roundtrips
    → faster responses.

    Tool mapping by state:
    - GREETING / NEED_ASSESSMENT: only update_user_profile
    - SCHEME_MATCH with pre-computed: none (single Bedrock call!)
    - SCHEME_MATCH without pre-computed: search_schemes, check_eligibility
    - ELIGIBILITY_CHECK: check_eligibility, update_user_profile
    - FORM_FILL: validate_field, update_user_profile
    - REVIEW: none
    - SUBMIT: submit_application, send_sms
    - COMPLETE: get_benefit_stack, send_sms
    """
    TOOL_NAME_MAP = {t["toolSpec"]["name"]: t for t in TOOLS}

    state_tools = {
        "GREETING": ["update_user_profile", "search_schemes", "check_eligibility"],
        "NEED_ASSESSMENT": ["update_user_profile", "search_schemes", "check_eligibility"],
        "SCHEME_MATCH": ["submit_application", "send_sms"] if has_precomputed else ["search_schemes", "check_eligibility"],
        "ELIGIBILITY_CHECK": ["check_eligibility", "update_user_profile"],
        "FORM_FILL": ["submit_application", "send_sms", "update_user_profile"],
        "REVIEW": ["submit_application", "send_sms"],
        "SUBMIT": ["submit_application", "send_sms"],
        "COMPLETE": ["get_benefit_stack", "send_sms"],
    }

    names = state_tools.get(state, list(TOOL_NAME_MAP.keys()))
    return [TOOL_NAME_MAP[n] for n in names if n in TOOL_NAME_MAP]


def _invoke_bedrock(
    user_message: str,
    conversation_history: list,
    context_info: str,
    language: str,
    tools: list = None,
) -> dict:
    """Invoke Bedrock Claude with conversation history and tools."""

    # Build messages array
    messages = []

    # Add conversation history (last 10 messages — smaller = faster Bedrock calls)
    for msg in conversation_history[-10:]:
        if msg["role"] in ("user", "assistant"):
            text = (msg.get("content") or "").strip()
            if not text:
                continue  # Skip blank messages — Bedrock rejects them
            messages.append({
                "role": msg["role"],
                "content": [{"text": text}]
            })

    # Add current user message
    messages.append({
        "role": "user",
        "content": [{"text": user_message}]
    })

    # Ensure messages start with user role
    while messages and messages[0]["role"] == "assistant":
        messages = messages[1:]

    # Ensure alternating roles
    messages = _ensure_alternating_roles(messages)

    # Map language codes to clear names for the model
    LANG_NAMES = {
        "hi-IN": "Hindi", "hi": "Hindi",
        "en-IN": "English", "en": "English",
        "ta-IN": "Tamil", "ta": "Tamil",
        "bn-IN": "Bengali", "bn": "Bengali",
        "te-IN": "Telugu", "te": "Telugu",
        "mr-IN": "Marathi", "mr": "Marathi",
        "kn-IN": "Kannada", "kn": "Kannada",
        "ml-IN": "Malayalam", "ml": "Malayalam",
    }
    lang_name = LANG_NAMES.get(language, "Hindi")
    system_prompt = f"{SYSTEM_PROMPT}\n\n{context_info}\n\nIMPORTANT: User's language is {lang_name} ({language}). You MUST respond ONLY in {lang_name}. Do not use any other language."

    # Build optional guardrail config
    guardrail_kwargs = {}
    if GUARDRAIL_ID:
        guardrail_kwargs["guardrailConfig"] = {
            "guardrailIdentifier": GUARDRAIL_ID,
            "guardrailVersion": GUARDRAIL_VERSION,
        }
        logger.info(f"Guardrail enabled: {GUARDRAIL_ID} v{GUARDRAIL_VERSION}")

    _INFERENCE_CONFIG = {
        "maxTokens": 512,
        "temperature": 0.3,
        "topP": 0.9,
    }
    # Only include toolConfig when tools are provided — no tools = single Bedrock call
    tool_kwargs = {"toolConfig": {"tools": tools}} if tools else {}

    # Retry once on "invalid sequence" errors (intermittent Haiku bug)
    for attempt in range(2):
        try:
            response = _bedrock.converse(
                modelId=BEDROCK_MODEL_ID,
                messages=messages,
                system=[{"text": system_prompt}],
                inferenceConfig=_INFERENCE_CONFIG,
                **tool_kwargs,
                **guardrail_kwargs,
            )
            # If guardrail intervened, retry without it
            if response.get("stopReason") == "guardrail_intervened" and guardrail_kwargs:
                logger.warning("Guardrail intervened — retrying without guardrail")
                response = _bedrock.converse(
                    modelId=BEDROCK_MODEL_ID,
                    messages=messages,
                    system=[{"text": system_prompt}],
                    inferenceConfig=_INFERENCE_CONFIG,
                    **tool_kwargs,
                )
            return response
        except Exception as e:
            err_msg = str(e)
            # Retry once for "invalid sequence" model errors
            if attempt == 0 and "invalid sequence" in err_msg.lower():
                logger.warning(f"Model produced invalid sequence — retrying (attempt {attempt + 1})")
                continue
            # Try fallback model
            logger.warning(f"Primary model ({BEDROCK_MODEL_ID}) failed: {e}. Trying fallback ({BEDROCK_FALLBACK_MODEL_ID})...")
            try:
                response = _bedrock.converse(
                    modelId=BEDROCK_FALLBACK_MODEL_ID,
                    messages=messages,
                    system=[{"text": system_prompt}],
                    inferenceConfig=_INFERENCE_CONFIG,
                    **tool_kwargs,
                )
                logger.info(f"Fallback model ({BEDROCK_FALLBACK_MODEL_ID}) succeeded.")
                return response
            except Exception as fallback_err:
                logger.exception(f"Fallback model also failed: {fallback_err}")
                raise e


def _ensure_alternating_roles(messages: list) -> list:
    """Ensure messages alternate between user and assistant roles."""
    if not messages:
        return messages

    cleaned = [messages[0]]
    for msg in messages[1:]:
        if msg["role"] == cleaned[-1]["role"]:
            # Merge content if same role
            cleaned[-1]["content"].extend(msg["content"])
        else:
            cleaned.append(msg)

    return cleaned


def _process_response(
    response: dict,
    session_id: str,
    user_message: str,
    user_profile: dict,
    matched_schemes: list,
    selected_scheme: str,
    form_data: dict,
    language: str,
    conversation_state: str,
    conversation_history: list,
    context_info: str,
) -> dict:
    """Process Bedrock response, handling tool use and extracting state updates."""

    output = response.get("output", {})
    message = output.get("message", {})
    content_blocks = message.get("content", [])
    stop_reason = response.get("stopReason", "end_turn")

    result = {
        "response": "",
        "conversationState": conversation_state,
        "userProfile": user_profile,
        "matchedSchemes": None,
        "selectedScheme": selected_scheme,
        "formData": form_data,
        "formProgress": None,
        "applicationId": None,
    }

    # Process content blocks
    text_parts = []
    tool_use_blocks = []

    for block in content_blocks:
        if "text" in block:
            text_parts.append(block["text"])
        elif "toolUse" in block:
            tool_use_blocks.append(block["toolUse"])

    # If there are tool calls, execute them in a loop (up to MAX_TOOL_ROUNDS)
    if tool_use_blocks and stop_reason == "tool_use":
        MAX_TOOL_ROUNDS = 2

        # Determine which tools are relevant for follow-up calls
        has_precomputed = "Pre-computed Eligibility Results" in context_info
        state_tools = _get_tools_for_state(conversation_state, has_precomputed)
        followup_tool_kwargs = {"toolConfig": {"tools": state_tools}} if state_tools else {}

        # Clear initial text_parts — we only want the FINAL response
        # (intermediate text is usually just <thinking> tags)
        text_parts = []

        # Build the base message sequence from conversation history
        followup_messages = []
        for m in (conversation_history[-10:] if conversation_history else []):
            if m["role"] in ("user", "assistant"):
                text = (m.get("content") or "").strip()
                if not text:
                    continue
                followup_messages.append({"role": m["role"], "content": [{"text": text}]})

        # Add the user's original message
        followup_messages.append({"role": "user", "content": [{"text": user_message}]})

        LANG_NAMES = {
            "hi-IN": "Hindi", "hi": "Hindi",
            "en-IN": "English", "en": "English",
            "ta-IN": "Tamil", "ta": "Tamil",
            "bn-IN": "Bengali", "bn": "Bengali",
            "te-IN": "Telugu", "te": "Telugu",
            "mr-IN": "Marathi", "mr": "Marathi",
            "kn-IN": "Kannada", "kn": "Kannada",
            "ml-IN": "Malayalam", "ml": "Malayalam",
        }
        lang_name = LANG_NAMES.get(language, "Hindi")
        system_prompt = f"{SYSTEM_PROMPT}\n\n{context_info}\n\nIMPORTANT: User's language is {lang_name} ({language}). You MUST respond ONLY in {lang_name}. Do not use any other language."

        current_content_blocks = content_blocks
        current_stop_reason = stop_reason

        for round_num in range(MAX_TOOL_ROUNDS):
            # Extract tool-use blocks from the current response
            current_tool_blocks = [b["toolUse"] for b in current_content_blocks if "toolUse" in b]

            if not current_tool_blocks or current_stop_reason != "tool_use":
                # No more tools — extract final text from this response
                for block in current_content_blocks:
                    if "text" in block:
                        text_parts.append(block["text"])
                break

            logger.info(f"Tool round {round_num + 1}: executing {[t['name'] for t in current_tool_blocks]}")

            # Execute each tool call
            tool_results = []
            for tool_call in current_tool_blocks:
                tool_result = _execute_tool(
                    tool_name=tool_call["name"],
                    tool_input=tool_call["input"],
                    tool_use_id=tool_call["toolUseId"],
                    session_id=session_id,
                    user_profile=user_profile,
                    form_data=form_data,
                    language=language,
                )
                tool_results.append(tool_result)
                _update_state_from_tool(
                    tool_call["name"], tool_call["input"],
                    tool_result, result
                )

            # Append assistant tool-use message
            followup_messages.append({"role": "assistant", "content": current_content_blocks})

            # Append user tool-result message
            tool_result_content = []
            for tr in tool_results:
                tool_result_content.append({
                    "toolResult": {
                        "toolUseId": tr["toolUseId"],
                        "content": [{"json": _sanitize_for_bedrock(tr["result"])}],
                    }
                })
            followup_messages.append({"role": "user", "content": tool_result_content})

            # Fix: Bedrock requires messages to start with "user" role
            if followup_messages and followup_messages[0]["role"] == "assistant":
                followup_messages.insert(0, {"role": "user", "content": [{"text": user_message}]})

            followup_messages = _ensure_alternating_roles(followup_messages)

            # Call Bedrock with the accumulated conversation
            try:
                try:
                    followup_response = _bedrock.converse(
                        modelId=BEDROCK_MODEL_ID,
                        messages=followup_messages,
                        system=[{"text": system_prompt}],
                        inferenceConfig={"maxTokens": 512, "temperature": 0.3, "topP": 0.9},
                        **followup_tool_kwargs,
                    )
                except Exception as primary_err:
                    logger.warning(f"Followup round {round_num + 1} primary model failed: {primary_err}. Trying fallback...")
                    followup_response = _bedrock.converse(
                        modelId=BEDROCK_FALLBACK_MODEL_ID,
                        messages=followup_messages,
                        system=[{"text": system_prompt}],
                        inferenceConfig={"maxTokens": 512, "temperature": 0.3, "topP": 0.9},
                        **followup_tool_kwargs,
                    )

                current_content_blocks = followup_response.get("output", {}).get("message", {}).get("content", [])
                current_stop_reason = followup_response.get("stopReason", "end_turn")

            except Exception as e:
                logger.error(f"Followup round {round_num + 1} invocation error: {e}", exc_info=True)
                # Generate fallback response from accumulated tool results
                if result.get("matchedSchemes"):
                    schemes = result["matchedSchemes"]
                    lang = language[:2] if language else "en"
                    scheme_names = []
                    for s in schemes[:5]:
                        name = s.get("name", "") if isinstance(s.get("name"), str) else s.get("name", {}).get(lang, s.get("name", {}).get("en", str(s.get("schemeId", ""))))
                        scheme_names.append(name)
                    if lang == "hi":
                        text_parts.append(f"आपके लिए ये सरकारी योजनाएं मिली हैं: {', '.join(scheme_names)}। किसी भी योजना के बारे में और जानना चाहें तो बताएं।")
                    else:
                        text_parts.append(f"I found these government schemes for you: {', '.join(scheme_names)}. Would you like to know more about any of them?")
                break
        else:
            # MAX_TOOL_ROUNDS exhausted — extract any remaining text
            for block in current_content_blocks:
                if "text" in block:
                    text_parts.append(block["text"])

    # Only keep non-thinking text parts (strip thinking before joining)
    cleaned_parts = []
    for part in text_parts:
        cleaned = re.sub(r"<thinking>.*?</thinking>", "", part, flags=re.DOTALL).strip()
        if cleaned:
            cleaned_parts.append(cleaned)

    result["response"] = "\n".join(cleaned_parts) if cleaned_parts else ""

    # Clean up AI response (parse JSON wrappers, strip leftovers)
    result["response"] = _clean_ai_response(result["response"])

    # Final fallback guard: if still empty, provide a meaningful response
    if not result["response"]:
        if result.get("matchedSchemes"):
            schemes = result["matchedSchemes"]
            lang = language[:2] if language else "en"
            scheme_names = []
            for s in schemes[:5]:
                name = s.get("name", "") if isinstance(s.get("name"), str) else s.get("name", {}).get(lang, s.get("name", {}).get("en", str(s.get("schemeId", ""))))
                scheme_names.append(name)
            if lang == "hi":
                result["response"] = f"आपके लिए ये सरकारी योजनाएं मिली हैं: {', '.join(scheme_names)}। किसी भी योजना के बारे में और जानना चाहें तो बताएं।"
            else:
                result["response"] = f"I found these government schemes for you: {', '.join(scheme_names)}. Would you like to know more about any of them?"
        else:
            FALLBACKS = {
                "hi-IN": "मैं समझ नहीं पाई। कृपया दोबारा बताएं।",
                "en-IN": "I couldn't understand that. Could you please rephrase?",
                "ta-IN": "என்னால் புரிந்துகொள்ள முடியவில்லை. தயவுசெய்து மீண்டும் சொல்லுங்கள்.",
            }
            result["response"] = FALLBACKS.get(language, FALLBACKS.get("en-IN"))

    # Infer state transitions
    result["conversationState"] = _infer_next_state(
        current_state=conversation_state,
        response_text=result["response"],
        user_profile=result.get("userProfile", {}),
        matched_schemes=result.get("matchedSchemes"),
        form_data=result.get("formData", {}),
        selected_scheme=result.get("selectedScheme"),
        application_id=result.get("applicationId"),
    )

    return result


def _execute_tool(
    tool_name: str, tool_input: dict, tool_use_id: str,
    session_id: str, user_profile: dict, form_data: dict, language: str
) -> dict:
    """Execute a tool call and return the result."""
    logger.info(f"Executing tool: {tool_name} with input: {tool_input}")

    try:
        if tool_name == "search_schemes":
            query = tool_input.get("query", "")
            category = tool_input.get("category")
            schemes = search_schemes(query, category, language=language[:2] if language else "en")

            # Also run eligibility matching
            if user_profile:
                ranked = match_schemes_to_profile(schemes, user_profile)
                result_data = {"schemes": ranked[:5], "count": len(ranked)}
            else:
                lang_key = language[:2] if language else "en"
                result_data = {
                    "schemes": [
                        {
                            "schemeId": s["schemeId"],
                            "name": s["name"].get(lang_key, s["name"]["en"]),
                            "shortDescription": s.get("shortDescription", {}).get(lang_key, ""),
                            "category": s["category"],
                        }
                        for s in schemes[:5]
                    ],
                    "count": len(schemes),
                }

            return {"toolUseId": tool_use_id, "result": result_data}

        elif tool_name == "check_eligibility":
            scheme_id = tool_input.get("scheme_id", "")
            scheme = get_scheme_by_id(scheme_id)
            if not scheme:
                return {"toolUseId": tool_use_id, "result": {"error": f"Scheme {scheme_id} not found"}}
            eligibility = check_eligibility(scheme, user_profile)
            return {"toolUseId": tool_use_id, "result": eligibility}

        elif tool_name == "validate_field":
            field_type = tool_input.get("field_type", "text")
            value = tool_input.get("value", "")
            validation = validate_field(field_type, value)
            return {"toolUseId": tool_use_id, "result": validation}

        elif tool_name == "submit_application":
            scheme_id = tool_input.get("scheme_id", "")
            submitted_form = tool_input.get("form_data", form_data)
            application = _submit_application(session_id, scheme_id, submitted_form)
            return {"toolUseId": tool_use_id, "result": application}

        elif tool_name == "send_sms":
            phone = tool_input.get("phone_number", "")
            message = tool_input.get("message", "")
            sms_result = _send_sms(phone, message)
            return {"toolUseId": tool_use_id, "result": sms_result}

        elif tool_name == "get_benefit_stack":
            stack = compute_benefit_stack(user_profile, language)
            return {"toolUseId": tool_use_id, "result": stack}

        elif tool_name == "update_user_profile":
            # Merge extracted fields into user_profile (in-place so subsequent
            # tool calls in the same turn see the updated values)
            for key, value in tool_input.items():
                if value is not None and value != "":
                    user_profile[key] = value
            logger.info(f"Updated user profile: {user_profile}")
            return {"toolUseId": tool_use_id, "result": {"status": "profile_updated", "profile": user_profile}}

        else:
            return {"toolUseId": tool_use_id, "result": {"error": f"Unknown tool: {tool_name}"}}

    except Exception as e:
        logger.exception(f"Tool execution error: {e}")
        return {"toolUseId": tool_use_id, "result": {"error": str(e)}}


def _update_state_from_tool(tool_name: str, tool_input: dict, tool_result: dict, result: dict):
    """Update the result state based on tool execution."""
    data = tool_result.get("result", {})

    if tool_name == "search_schemes":
        schemes = data.get("schemes", [])
        if schemes:
            result["matchedSchemes"] = schemes

    elif tool_name == "submit_application":
        if "applicationId" in data:
            result["applicationId"] = data["applicationId"]
        # Capture selected scheme from submit input
        scheme_id = tool_input.get("scheme_id", "")
        if scheme_id:
            result["selectedScheme"] = scheme_id
        # Capture the form data that was submitted
        submitted_form = tool_input.get("form_data", {})
        if submitted_form:
            result["formData"] = submitted_form

    elif tool_name == "update_user_profile":
        # Propagate the updated profile into the result dict so the
        # orchestrator persists it to the session.
        if "profile" in data:
            result["userProfile"] = data["profile"]

    elif tool_name == "validate_field":
        # Safety net: If validate_field is somehow still called (e.g., in
        # SCHEME_MATCH state), save by field_id when possible.
        # The deterministic form processing in _process_form_input handles
        # the main FORM_FILL flow, so this is a fallback.
        if data.get("valid"):
            field_type = tool_input.get("field_type", "")
            field_id = tool_input.get("field_id", field_type)  # prefer field_id
            normalized = data.get("normalized", tool_input.get("value", ""))
            if field_id and normalized:
                if not result.get("formData"):
                    result["formData"] = {}
                result["formData"][field_id] = normalized

    elif tool_name == "check_eligibility":
        # Capture eligibility results — the scheme the user checked
        scheme_id = tool_input.get("scheme_id", "")
        if scheme_id:
            result["selectedScheme"] = scheme_id


def _submit_application(session_id: str, scheme_id: str, form_data: dict) -> dict:
    """Submit an application to DynamoDB."""
    import uuid

    year = datetime.now(timezone.utc).year
    short_id = uuid.uuid4().hex[:5].upper()
    application_id = f"VS-{year}-{short_id}"

    scheme = get_scheme_by_id(scheme_id)
    scheme_name = scheme["name"]["en"] if scheme else scheme_id

    application = {
        "applicationId": application_id,
        "sessionId": session_id,
        "schemeId": scheme_id,
        "schemeName": scheme_name,
        "formData": form_data,
        "status": "submitted",
        "submittedAt": datetime.now(timezone.utc).isoformat(),
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }

    # Extract phone from form data
    phone = form_data.get("phone", "")
    if phone:
        application["phoneNumber"] = phone

    _applications_table.put_item(Item=application)
    logger.info(f"Submitted application {application_id} for {scheme_id}")

    return {
        "applicationId": application_id,
        "status": "submitted",
        "schemeName": scheme_name,
    }


def _send_sms(phone_number: str, message: str) -> dict:
    """Send SMS via SNS (or mock for hackathon)."""
    try:
        sns = boto3.client("sns", region_name=REGION)
        response = sns.publish(
            PhoneNumber=phone_number,
            Message=message,
            MessageAttributes={
                "AWS.SNS.SMS.SenderID": {
                    "DataType": "String",
                    "StringValue": "VaaniSetu"
                },
                "AWS.SNS.SMS.SMSType": {
                    "DataType": "String",
                    "StringValue": "Transactional"
                }
            }
        )
        return {"sent": True, "messageId": response.get("MessageId", "")}
    except Exception as e:
        logger.error(f"SMS send error: {e}")
        return {"sent": False, "error": str(e)}


def _infer_next_state(
    current_state: str, response_text: str,
    user_profile: dict, matched_schemes: list,
    form_data: dict, selected_scheme: str,
    application_id: str,
) -> str:
    """Infer the next conversation state based on context.

    Why this is important: The AI model doesn't return explicit state
    transitions. We infer the state from the accumulated context (profile
    completeness, scheme selection, form progress, etc.) to determine
    which tools to provide and how to guide the conversation.
    """
    resp_lower = response_text.lower() if response_text else ""

    if application_id:
        return "COMPLETE"

    if current_state == "GREETING":
        return "NEED_ASSESSMENT"

    if current_state == "NEED_ASSESSMENT":
        if matched_schemes:
            return "SCHEME_MATCH"
        if len(user_profile) >= 3:
            return "SCHEME_MATCH"
        return "NEED_ASSESSMENT"

    if current_state == "SCHEME_MATCH":
        # Fast-track: if response mentions form fields or asks for personal
        # details like Aadhaar/name/phone, we're effectively in FORM_FILL
        form_keywords = ["aadhaar", "आधार", "name", "नाम", "phone", "mobile",
                         "bank account", "ifsc", "question 1", "question 2",
                         "सवाल", "form", "application"]
        if any(kw in resp_lower for kw in form_keywords):
            return "FORM_FILL"
        if selected_scheme:
            return "FORM_FILL"
        return "SCHEME_MATCH"

    if current_state == "ELIGIBILITY_CHECK":
        if selected_scheme:
            return "FORM_FILL"
        return "ELIGIBILITY_CHECK"

    if current_state == "FORM_FILL":
        if selected_scheme:
            scheme = get_scheme_by_id(selected_scheme)
            if scheme:
                required_fields = [f for f in scheme.get("formFields", []) if f.get("required", True)]
                if len(form_data) >= len(required_fields):
                    return "REVIEW"
        return "FORM_FILL"

    if current_state == "REVIEW":
        return "SUBMIT"

    if current_state == "SUBMIT":
        return "COMPLETE"

    return current_state
