"""Quick test to verify form filling flow against the live API.

Happy path: farmer from Bihar → PM-KISAN → fill 8 fields
(state and landSize are pre-populated from user profile).

Field order: name → fatherName → aadhaar → phone → [state:pre-filled]
→ district → village → [landSize:pre-filled] → bankAccount → ifsc
"""

import json
import requests
import time

API = "https://hbm4onktgf.execute-api.us-east-1.amazonaws.com/prod"


def send(sid: str, text: str, step: int, label: str, long: bool = False) -> dict:
    """Send a message and print the response."""
    print(f"\n{'=' * 60}")
    print(f"STEP {step}: '{text}' ({label})")
    r = requests.post(f"{API}/sessions/{sid}/message", json={"text": text})
    d = r.json()
    print(f"  State : {d.get('conversationState')}")
    if d.get("applicationId"):
        print(f"  App ID: {d['applicationId']}")
    limit = 400 if long else 200
    print(f"  AI    : {d.get('response', '')[:limit]}")
    time.sleep(1)
    return d


def test_form_flow():
    # 1. Create session
    print("=" * 60)
    print("STEP 1: Create session")
    resp = requests.post(f"{API}/sessions", json={"language": "en-IN"})
    data = resp.json()
    sid = data["sessionId"]
    print(f"  Session ID: {sid}")
    print(f"  Greeting  : {data.get('greeting', '')[:120]}...")
    time.sleep(1)

    # 2. User describes themselves → sets user_profile (state=Bihar, landSize=2)
    send(sid, "I am a farmer from Bihar with 2 acres of land", 2, "user profile")

    # 3. Select PM-KISAN → scheme detected, state→FORM_FILL
    send(sid, "I want to apply for PM Kisan", 3, "select PM-KISAN")

    # 4-7: Fields that need user input
    send(sid, "Rajesh Kumar",  4, "name")
    send(sid, "Suresh Kumar",  5, "fatherName")
    send(sid, "234567890123",  6, "aadhaar")
    send(sid, "9876543210",    7, "phone")

    # (state is pre-filled from profile → skipped)

    # 8. District
    send(sid, "Patna", 8, "district")

    # 9. Village
    send(sid, "Danapur", 9, "village")

    # (landSize is pre-filled from profile → skipped)

    # 10. Bank account
    send(sid, "12345678901234", 10, "bankAccount")

    # 11. IFSC → last field → should transition to REVIEW
    d = send(sid, "SBIN0001234", 11, "ifsc → REVIEW", long=True)

    # 12. Confirm → deterministic submission
    d = send(sid, "Yes, everything is correct", 12, "confirm → SUBMIT", long=True)

    print(f"\n{'=' * 60}")
    if d.get("applicationId"):
        print(f"SUCCESS! Application submitted: {d['applicationId']}")
    else:
        print("ISSUE: No application ID returned.")


if __name__ == "__main__":
    test_form_flow()
