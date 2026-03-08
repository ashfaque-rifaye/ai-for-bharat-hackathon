"""VaaniSetu Connect Handler — Lambda invoked by Amazon Connect contact flows.

This Lambda bridges Amazon Connect phone calls with the Bedrock AI engine.
It handles:
- Session creation/retrieval for phone callers
- Language detection from contact attributes
- Bedrock conversation for scheme discovery
- Response formatting for Connect TTS
"""

import json
import os
import time
import uuid
import traceback

import boto3
from boto3.dynamodb.conditions import Key

# ── AWS Clients ──────────────────────────────────────────────────────
REGION = os.environ.get("AWS_REGION_NAME", "us-east-1")
dynamodb = boto3.resource("dynamodb", region_name=REGION)
bedrock_runtime = boto3.client("bedrock-runtime", region_name=REGION)
bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name=REGION)

SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE", "vaanisetu-sessions")
SCHEMES_TABLE = os.environ.get("SCHEMES_TABLE", "vaanisetu-schemes")
APPLICATIONS_TABLE = os.environ.get("APPLICATIONS_TABLE", "vaanisetu-applications")
KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID", "")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")

sessions_table = dynamodb.Table(SESSIONS_TABLE)
schemes_table = dynamodb.Table(SCHEMES_TABLE)

# ── System Prompt ────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are VaaniSetu (वाणी सेतु), a friendly government scheme assistant for Indian citizens.

IMPORTANT RULES:
1. You help people discover and apply for government schemes
2. Speak in the user's language (Hindi/English/Tamil)
3. Keep responses SHORT (2-3 sentences max) — this will be spoken over phone
4. Be warm and respectful — many callers are from rural areas
5. Ask ONE question at a time
6. Use simple language, avoid jargon
7. When listing schemes, give max 2-3 at a time with brief descriptions

CONVERSATION FLOW:
1. GREETING: Welcome the caller, ask what help they need
2. NEED_ASSESSMENT: Understand their situation (occupation, family size, income, etc.)
3. SCHEME_MATCH: Suggest relevant schemes based on their profile
4. ELIGIBILITY_CHECK: Verify they qualify for selected scheme
5. FORM_FILL: Collect required details one field at a time
6. REVIEW: Summarize collected info, confirm
7. SUBMIT: Submit application, share reference number
8. COMPLETE: Thank them, offer to help with more schemes

AVAILABLE SCHEMES (respond based on user profile):
- PM-KISAN: ₹6000/year for farmers with <2 hectares land
- PM Awas Yojana: Housing subsidy for BPL families
- Ayushman Bharat: ₹5 lakh health insurance for poor families
- PM Ujjwala Yojana: Free LPG connection for BPL women
- PM Mudra Yojana: Business loans up to ₹10 lakh
- PM Garib Kalyan Anna: Free ration for poor families
- PM Fasal Bima: Crop insurance for farmers
- Sukanya Samriddhi: Savings scheme for girl child
- Soil Health Card: Free soil testing for farmers
- RKVY: Agricultural development support
"""

# ── Greeting Messages ────────────────────────────────────────────────
GREETINGS = {
    "hi-IN": "नमस्ते! मैं वाणी सेतु हूँ। मैं आपको सरकारी योजनाओं के बारे में बता सकती हूँ। आप क्या जानना चाहते हैं?",
    "en-IN": "Hello! I'm VaaniSetu. I can help you find government schemes. What would you like to know?",
    "ta-IN": "வணக்கம்! நான் வாணி சேது. அரசு திட்டங்களை கண்டறிய உங்களுக்கு உதவ முடியும். நீங்கள் என்ன தெரிந்து கொள்ள விரும்புகிறீர்கள்?",
}


def handler(event, context):
    """
    Amazon Connect Lambda handler.

    Connect passes contact attributes and customer input as event data.
    We return response text that Connect speaks via Polly TTS.
    """
    print(f"Connect event: {json.dumps(event)}")

    try:
        # Extract Connect contact info
        contact_data = event.get("Details", {})
        contact_attrs = contact_data.get("ContactData", {}).get("Attributes", {})
        parameters = contact_data.get("Parameters", {})

        # Get caller info
        phone_number = (
            contact_data.get("ContactData", {})
            .get("CustomerEndpoint", {})
            .get("Address", "unknown")
        )
        contact_id = contact_data.get("ContactData", {}).get("ContactId", str(uuid.uuid4()))
        language = contact_attrs.get("language", "hi-IN")

        # Get or create session
        session = _get_or_create_session(contact_id, phone_number, language)
        session_id = session["sessionId"]

        # Get user input (voice transcription from Connect)
        user_input = parameters.get("UserInput", "")

        # If no input yet (first invocation), send greeting
        if not user_input and session.get("conversationState") == "GREETING":
            greeting = GREETINGS.get(language, GREETINGS["hi-IN"])
            _update_session(session_id, "conversationState", "NEED_ASSESSMENT")
            return _connect_response(greeting, session_id, "NEED_ASSESSMENT")

        # Process user input through AI
        ai_response = _process_with_bedrock(session, user_input, language)

        return _connect_response(
            ai_response["text"],
            session_id,
            ai_response.get("state", session.get("conversationState", "NEED_ASSESSMENT")),
        )

    except Exception as e:
        print(f"Error: {traceback.format_exc()}")
        error_msgs = {
            "hi-IN": "माफ कीजिये, तकनीकी समस्या हुई। कृपया दोबारा बोलिए।",
            "en-IN": "Sorry, there was a technical issue. Please try again.",
            "ta-IN": "மன்னிக்கவும், தொழில்நுட்ப சிக்கல் ஏற்பட்டது. மீண்டும் முயற்சிக்கவும்.",
        }
        lang = event.get("Details", {}).get("ContactData", {}).get("Attributes", {}).get("language", "hi-IN")
        return _connect_response(error_msgs.get(lang, error_msgs["hi-IN"]), "", "ERROR")


def _get_or_create_session(contact_id: str, phone_number: str, language: str) -> dict:
    """Get existing session or create new one for the caller."""
    # Try to find existing session by contact ID
    try:
        result = sessions_table.get_item(Key={"sessionId": contact_id})
        if "Item" in result:
            return result["Item"]
    except Exception:
        pass

    # Create new session
    session = {
        "sessionId": contact_id,
        "phoneNumber": phone_number,
        "language": language,
        "status": "active",
        "conversationState": "GREETING",
        "conversationHistory": [],
        "matchedSchemes": [],
        "userProfile": {},
        "formData": {},
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "channel": "phone",
    }
    sessions_table.put_item(Item=session)
    return session


def _process_with_bedrock(session: dict, user_input: str, language: str) -> dict:
    """Process user input through Bedrock Claude and return AI response."""
    session_id = session["sessionId"]

    # Build conversation history for Bedrock
    history = session.get("conversationHistory", [])
    messages = []
    for msg in history[-10:]:  # Keep last 10 messages for context
        messages.append({"role": msg["role"], "content": [{"text": msg["content"]}]})

    # Add current user message
    messages.append({"role": "user", "content": [{"text": user_input}]})

    # Search knowledge base for relevant scheme info
    kb_context = ""
    if KNOWLEDGE_BASE_ID and user_input:
        kb_context = _search_knowledge_base(user_input)

    # Build enhanced system prompt
    system_prompt = SYSTEM_PROMPT
    if kb_context:
        system_prompt += f"\n\nRELEVANT SCHEME INFORMATION:\n{kb_context}"

    system_prompt += f"\n\nCurrent language: {language}"
    system_prompt += f"\nConversation state: {session.get('conversationState', 'NEED_ASSESSMENT')}"

    if session.get("userProfile"):
        system_prompt += f"\nUser profile so far: {json.dumps(session['userProfile'], ensure_ascii=False)}"

    if session.get("matchedSchemes"):
        system_prompt += f"\nMatched schemes: {json.dumps(session['matchedSchemes'], ensure_ascii=False)}"

    # Call Bedrock
    try:
        response = bedrock_runtime.converse(
            modelId=BEDROCK_MODEL_ID,
            messages=messages,
            system=[{"text": system_prompt}],
            inferenceConfig={
                "maxTokens": 300,  # Short for phone conversations
                "temperature": 0.7,
                "topP": 0.9,
            },
        )

        ai_text = response["output"]["message"]["content"][0]["text"]

        # Update session with new messages
        new_history = history + [
            {"role": "user", "content": user_input, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
            {"role": "assistant", "content": ai_text, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
        ]

        # Infer conversation state from AI response
        new_state = _infer_state(ai_text, session.get("conversationState", "NEED_ASSESSMENT"))

        # Update session
        sessions_table.update_item(
            Key={"sessionId": session_id},
            UpdateExpression="SET conversationHistory = :h, conversationState = :s, updatedAt = :u",
            ExpressionAttributeValues={
                ":h": new_history[-20:],  # Keep last 20 messages
                ":s": new_state,
                ":u": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        )

        return {"text": ai_text, "state": new_state}

    except Exception as e:
        print(f"Bedrock error: {e}")
        fallback = {
            "hi-IN": "माफ करें, मुझे समझ नहीं आया। कृपया दोबारा बोलिए।",
            "en-IN": "Sorry, I didn't understand. Could you please repeat?",
            "ta-IN": "மன்னிக்கவும், புரியவில்லை. மீண்டும் சொல்லுங்கள்.",
        }
        return {"text": fallback.get(language, fallback["hi-IN"]), "state": session.get("conversationState")}


def _search_knowledge_base(query: str) -> str:
    """Search Bedrock Knowledge Base for relevant scheme information."""
    if not KNOWLEDGE_BASE_ID:
        return ""

    try:
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": 3,
                }
            },
        )

        results = []
        for item in response.get("retrievalResults", []):
            text = item.get("content", {}).get("text", "")
            score = item.get("score", 0)
            if score > 0.3 and text:
                results.append(text[:500])

        return "\n---\n".join(results) if results else ""

    except Exception as e:
        print(f"KB search error: {e}")
        return ""


def _infer_state(ai_response: str, current_state: str) -> str:
    """Infer conversation state from AI response content."""
    response_lower = ai_response.lower()

    state_signals = {
        "SCHEME_MATCH": ["योजना", "scheme", "recommend", "suggest", "திட்ட"],
        "ELIGIBILITY_CHECK": ["eligible", "पात्र", "qualify", "தகுதி", "check"],
        "FORM_FILL": ["aadhaar", "आधार", "phone number", "फोन", "naam", "name", "பெயர்", "details"],
        "REVIEW": ["confirm", "review", "verify", "जांच", "check details", "சரிபார்"],
        "SUBMIT": ["submit", "जमा", "application", "आवेदन", "reference", "சமர்ப்பி"],
        "COMPLETE": ["thank", "धन्यवाद", "complete", "नन्றி", "நன்றி"],
    }

    for state, signals in state_signals.items():
        if any(signal in response_lower for signal in signals):
            return state

    return current_state


def _update_session(session_id: str, key: str, value: str):
    """Update a single attribute in the session."""
    sessions_table.update_item(
        Key={"sessionId": session_id},
        UpdateExpression=f"SET #k = :v, updatedAt = :u",
        ExpressionAttributeNames={"#k": key},
        ExpressionAttributeValues={
            ":v": value,
            ":u": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    )


def _connect_response(text: str, session_id: str, state: str) -> dict:
    """Format response for Amazon Connect."""
    # Clean text for TTS (remove markdown, special chars)
    clean_text = text.replace("**", "").replace("*", "").replace("#", "").replace("`", "")
    clean_text = clean_text.replace("₹", "rupees ").strip()

    # Truncate for Connect (max 8000 chars for SSML)
    if len(clean_text) > 3000:
        clean_text = clean_text[:2950] + "..."

    return {
        "aiResponse": clean_text,
        "ssmlResponse": f"<speak>{clean_text}</speak>",
        "sessionId": session_id,
        "conversationState": state,
    }
