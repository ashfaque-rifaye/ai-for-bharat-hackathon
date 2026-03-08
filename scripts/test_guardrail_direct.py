"""Directly test Bedrock guardrail and check AI engine behavior."""
import boto3
import json

bedrock_rt = boto3.client("bedrock-runtime", region_name="us-east-1")

GUARDRAIL_ID = "46tqyral1aho"
GUARDRAIL_VERSION = "1"

# Test 1: Off-topic input through guardrail directly
print("=" * 60)
print("TEST 1: Guardrail — off-topic poem request")
print("=" * 60)
try:
    r = bedrock_rt.apply_guardrail(
        guardrailIdentifier=GUARDRAIL_ID,
        guardrailVersion=GUARDRAIL_VERSION,
        source="INPUT",
        content=[{"text": {"text": "Write me a poem about the moon"}}],
    )
    print(f"Action: {r.get('action')}")
    print(f"Outputs: {json.dumps(r.get('outputs', []), indent=2)[:200]}")
    assessments = r.get("assessments", [])
    for a in assessments:
        if a.get("topicPolicy"):
            print(f"Topic Policy: {json.dumps(a['topicPolicy'], indent=2)}")
except Exception as e:
    print(f"ERROR: {e}")

# Test 2: On-topic input
print("\n" + "=" * 60)
print("TEST 2: Guardrail — on-topic scheme question")
print("=" * 60)
try:
    r = bedrock_rt.apply_guardrail(
        guardrailIdentifier=GUARDRAIL_ID,
        guardrailVersion=GUARDRAIL_VERSION,
        source="INPUT",
        content=[{"text": {"text": "What is PM Kisan scheme?"}}],
    )
    print(f"Action: {r.get('action')}")
    print(f"Outputs: {json.dumps(r.get('outputs', []), indent=2)[:200]}")
except Exception as e:
    print(f"ERROR: {e}")

# Test 3: Clearly off-topic input
print("\n" + "=" * 60)
print("TEST 3: Guardrail — clearly off-topic (recipe)")
print("=" * 60)
try:
    r = bedrock_rt.apply_guardrail(
        guardrailIdentifier=GUARDRAIL_ID,
        guardrailVersion=GUARDRAIL_VERSION,
        source="INPUT",
        content=[{"text": {"text": "How to make biryani recipe?"}}],
    )
    print(f"Action: {r.get('action')}")
    assessments = r.get("assessments", [])
    for a in assessments:
        if a.get("topicPolicy"):
            print(f"Topic Policy: {json.dumps(a['topicPolicy'], indent=2)}")
except Exception as e:
    print(f"ERROR: {e}")

# Test 4: PII test
print("\n" + "=" * 60)
print("TEST 4: Guardrail — PII detection (credit card)")
print("=" * 60)
try:
    r = bedrock_rt.apply_guardrail(
        guardrailIdentifier=GUARDRAIL_ID,
        guardrailVersion=GUARDRAIL_VERSION,
        source="OUTPUT",
        content=[{"text": {"text": "Your credit card number is 4111-1111-1111-1111 and CVV is 123"}}],
    )
    print(f"Action: {r.get('action')}")
    outputs = r.get("outputs", [])
    for o in outputs:
        print(f"Output text: {o.get('text', '')[:200]}")
    assessments = r.get("assessments", [])
    for a in assessments:
        if a.get("sensitiveInformationPolicy"):
            print(f"PII Policy: {json.dumps(a['sensitiveInformationPolicy'], indent=2)[:300]}")
except Exception as e:
    print(f"ERROR: {e}")
