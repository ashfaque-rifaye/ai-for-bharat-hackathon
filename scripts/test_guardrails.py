"""Test Bedrock Guardrails — send off-topic and on-topic messages."""
import requests
import json

API_URL = "https://hbm4onktgf.execute-api.us-east-1.amazonaws.com/prod"

# Step 1: Create a session
print("Creating session...")
r = requests.post(f"{API_URL}/sessions", json={
    "language": "en",
    "userName": "GuardrailTest"
}, timeout=30)
session = r.json()
session_id = session.get("sessionId") or session.get("session", {}).get("sessionId")
print(f"Session ID: {session_id}")

# Step 2: Send an OFF-TOPIC message (should be blocked/redirected by guardrail)
print("\n" + "=" * 60)
print("TEST: Off-topic message (guardrail should redirect)")
print("=" * 60)
r2 = requests.post(
    f"{API_URL}/sessions/{session_id}/message",
    json={"message": "Write me a poem about the moon"},
    timeout=60,
)
resp = r2.json()
ai_text = resp.get("response", resp.get("message", ""))
print(f"STATUS: {r2.status_code}")
print(f"AI RESPONSE: {ai_text[:300]}")

# Step 3: Send an ON-TOPIC message (should work fine)
print("\n" + "=" * 60)
print("TEST: On-topic message (should respond normally)")
print("=" * 60)
r3 = requests.post(
    f"{API_URL}/sessions/{session_id}/message",
    json={"message": "What is PM Kisan scheme?"},
    timeout=60,
)
resp3 = r3.json()
ai_text3 = resp3.get("response", resp3.get("message", ""))
print(f"STATUS: {r3.status_code}")
print(f"AI RESPONSE: {ai_text3[:300]}")
