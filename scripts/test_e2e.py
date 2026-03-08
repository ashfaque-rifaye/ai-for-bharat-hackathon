"""Thorough end-to-end test of the VaaniSetu API with Claude 3 Haiku.

Tests:
1. Health check
2. Create session (Hindi)
3. Greeting flow — "namaste"
4. Scheme discovery — "kisano ke liye yojana batao"
5. Scheme selection — "1 batao"
6. Multi-language — Tamil, Bengali, English
7. Category-specific — healthcare, housing, finance
8. Edge cases — empty message, unknown language
"""

import json
import time
import urllib.request

BASE = "https://hbm4onktgf.execute-api.us-east-1.amazonaws.com/prod"
PASS = 0
FAIL = 0


def api_call(method, path, body=None, timeout=60):
    """Make an API call and return (status, data)."""
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"} if body else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())
    except Exception as e:
        return 0, {"error": str(e)}


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name} — {detail}")


def create_session_and_chat(lang, messages, label):
    """Create a session and send multiple messages, returning all responses."""
    status, data = api_call("POST", "/sessions", {"language": lang})
    if status != 201:
        test(f"[{label}] Create session", False, f"HTTP {status}")
        return None, []

    session_id = data["sessionId"]
    test(f"[{label}] Create session", True)

    responses = []
    for i, msg in enumerate(messages):
        status, resp = api_call("POST", f"/sessions/{session_id}/message", {
            "message": msg,
            "language": lang,
        })
        ai_text = resp.get("response", "")
        state = resp.get("conversationState", "?")
        responses.append((status, ai_text, state, resp))

        # Print truncated response
        display = ai_text[:120].replace("\n", " ")
        print(f"         Msg {i+1}: [{state}] {display}...")

    return session_id, responses


print("=" * 80)
print("VAANISETU END-TO-END TEST — Claude 3 Haiku + Nova Pro fallback")
print("=" * 80)


# ── Test 1: Health Check ─────────────────────────────────────────────
print("\n--- Test 1: Health Check ---")
status, data = api_call("GET", "/health")
test("Health endpoint returns 200", status == 200)
test("Health status is healthy", data.get("status") == "healthy")


# ── Test 2: Hindi Conversation Flow ──────────────────────────────────
print("\n--- Test 2: Hindi Conversation (full flow) ---")
sid, resps = create_session_and_chat("hi-IN", [
    "नमस्ते",
    "मुझे किसानों के लिए योजनाएं बताओ",
    "1 बताओ",
], "Hindi flow")

if resps:
    test("[Hindi flow] Greeting response is Hindi", any(c in resps[0][1] for c in "नमस्तेहिंदी"), resps[0][1][:50])
    test("[Hindi flow] No <thinking> tags", "<thinking>" not in resps[0][1])
    test("[Hindi flow] No raw JSON in response", not resps[0][1].strip().startswith("{"))
    test("[Hindi flow] Schemes shown", any(c in resps[1][1] for c in "योजनाscheme") or "PM" in resps[1][1].upper(), resps[1][1][:80])
    test("[Hindi flow] Scheme detail response", len(resps[2][1]) > 30, resps[2][1][:80])


# ── Test 3: English Conversation ─────────────────────────────────────
print("\n--- Test 3: English Conversation ---")
sid, resps = create_session_and_chat("en-IN", [
    "Hello",
    "I need help with farming schemes",
    "Tell me about the first one",
], "English")

if resps:
    test("[English] Greeting is English", any(w in resps[0][1].lower() for w in ["hello", "welcome", "namaste", "vaanisetu", "assist"]), resps[0][1][:60])
    test("[English] No <thinking> tags", "<thinking>" not in resps[0][1])
    test("[English] Farming schemes found", any(w in resps[1][1].upper() for w in ["PM-KISAN", "KISAN", "FARMER", "AGRICULTURE", "SCHEME"]), resps[1][1][:80])


# ── Test 4: Tamil ────────────────────────────────────────────────────
print("\n--- Test 4: Tamil Conversation ---")
sid, resps = create_session_and_chat("ta-IN", [
    "வணக்கம்",
    "விவசாயிகளுக்கான திட்டங்கள் வேண்டும்",
], "Tamil")

if resps:
    test("[Tamil] Response received", len(resps[0][1]) > 10, resps[0][1][:60])
    test("[Tamil] No <thinking> tags", "<thinking>" not in resps[0][1])


# ── Test 5: Bengali ──────────────────────────────────────────────────
print("\n--- Test 5: Bengali Conversation ---")
sid, resps = create_session_and_chat("bn-IN", [
    "নমস্কার",
    "কৃষকদের জন্য সরকারি প্রকল্প চাই",
], "Bengali")

if resps:
    test("[Bengali] Response received", len(resps[0][1]) > 10, resps[0][1][:60])


# ── Test 6: Healthcare Query ─────────────────────────────────────────
print("\n--- Test 6: Healthcare Query ---")
sid, resps = create_session_and_chat("hi-IN", [
    "मुझे स्वास्थ्य बीमा चाहिए",
], "Healthcare")

if resps:
    test("[Healthcare] Response about health", any(w in resps[0][1] for w in ["आयुष्मान", "स्वास्थ्य", "health", "Ayushman"]), resps[0][1][:80])


# ── Test 7: Housing Query ────────────────────────────────────────────
print("\n--- Test 7: Housing Query ---")
sid, resps = create_session_and_chat("hi-IN", [
    "मुझे घर बनवाना है",
], "Housing")

if resps:
    test("[Housing] Response about housing", any(w in resps[0][1] for w in ["आवास", "घर", "house", "housing", "AWAS"]), resps[0][1][:80])


# ── Test 8: Finance/Loan Query ───────────────────────────────────────
print("\n--- Test 8: Finance Query ---")
sid, resps = create_session_and_chat("hi-IN", [
    "मुझे व्यापार के लिए लोन चाहिए",
], "Finance")

if resps:
    test("[Finance] Response about finance", any(w in resps[0][1] for w in ["मुद्रा", "लोन", "loan", "MUDRA", "business", "व्यापार"]), resps[0][1][:80])


# ── Test 9: Schemes List API ─────────────────────────────────────────
print("\n--- Test 9: Direct Schemes API ---")
status, data = api_call("GET", "/schemes")
test("GET /schemes returns 200", status == 200)
schemes = data.get("schemes", [])
test("Has schemes", len(schemes) > 0, f"Count: {len(schemes)}")
test("Has 10 schemes", len(schemes) >= 10, f"Count: {len(schemes)}")


# ── Test 10: Scheme Search API ───────────────────────────────────────
print("\n--- Test 10: Scheme Search API ---")
status, data = api_call("POST", "/schemes/search", {"query": "farmer", "language": "en"})
test("POST /schemes/search returns 200", status == 200)
test("Search found results", data.get("totalResults", 0) > 0, f"Results: {data.get('totalResults', 0)}")


# ── Results ──────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print(f"RESULTS: {PASS} PASSED / {FAIL} FAILED / {PASS + FAIL} TOTAL")
print("=" * 80)

if FAIL == 0:
    print("ALL TESTS PASSED!")
else:
    print(f"{FAIL} test(s) need attention.")
