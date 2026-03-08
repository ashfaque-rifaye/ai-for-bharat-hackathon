"""Test WhatsApp webhook endpoint — simulate a Twilio WhatsApp POST."""
import requests
import urllib.parse

API_URL = "https://hbm4onktgf.execute-api.us-east-1.amazonaws.com/prod"

# Test 1: GET /whatsapp — Twilio health validation
print("=" * 60)
print("TEST 1: GET /whatsapp (Twilio validation)")
print("=" * 60)
try:
    r = requests.get(f"{API_URL}/whatsapp", timeout=15)
    print(f"STATUS: {r.status_code}")
    print(f"BODY:   {r.text[:200]}")
except Exception as e:
    print(f"ERROR: {e}")

# Test 2: POST /whatsapp — simulate Twilio webhook
print("\n" + "=" * 60)
print("TEST 2: POST /whatsapp (simulated Twilio message)")
print("=" * 60)
form_data = {
    "From": "whatsapp:+919876543210",
    "Body": "Tell me about PM Kisan Yojana",
    "ProfileName": "Test User",
    "To": "whatsapp:+14155238886",
    "MessageSid": "SM1234567890",
    "AccountSid": "ACtest123",
    "NumMedia": "0",
}
try:
    r = requests.post(
        f"{API_URL}/whatsapp",
        data=urllib.parse.urlencode(form_data),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=60,
    )
    print(f"STATUS: {r.status_code}")
    print(f"Content-Type: {r.headers.get('Content-Type')}")
    body = r.text[:500]
    print(f"BODY:\n{body}")
except Exception as e:
    print(f"ERROR: {e}")
