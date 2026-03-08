"""
Subscribe to Claude and other NOT_AVAILABLE models via AWS Marketplace.
Steps:
1. Submit Anthropic FTU form (PutUseCaseForModelAccess)
2. List agreement offers to get offer tokens
3. Create agreements for each model
4. Test invocation
"""
import boto3
import json
import base64
import time

region = "us-east-1"
bedrock = boto3.client("bedrock", region_name=region)
runtime = boto3.client("bedrock-runtime", region_name=region)

# ============================================================
# STEP 1: Submit Anthropic FTU form
# ============================================================
print("STEP 1: Submitting Anthropic First-Time Use form...")
print("=" * 60)

ftu_data = {
    "companyName": "VaaniSetu",
    "companyWebsite": "https://vaanisetu.in",
    "intendedUsers": 2,  # Internal and External
    "industryOption": "Government",
    "otherIndustryOption": "Public Services",
    "useCases": "VaaniSetu is an AI-powered voice assistant that helps Indian citizens access government welfare schemes in their native languages. It uses AI to have natural conversations about schemes like PM-KISAN, Ayushman Bharat, PM-AWAS etc, helping farmers and rural citizens understand eligibility and apply for benefits. Built for the AWS AI for Bharat Hackathon."
}

try:
    encoded = base64.b64encode(json.dumps(ftu_data).encode()).decode()
    resp = bedrock.put_use_case_for_model_access(formData=encoded)
    print(f"  FTU form submitted successfully!")
    print(f"  Response: {json.dumps(resp.get('ResponseMetadata', {}), indent=2)}")
except Exception as e:
    print(f"  FTU form result: {e}")

# ============================================================
# STEP 2: Get offer tokens and create agreements
# ============================================================
print("\nSTEP 2: Getting offer tokens and creating agreements...")
print("=" * 60)

models_to_subscribe = [
    "anthropic.claude-3-haiku-20240307-v1:0",
    "ai21.jamba-1-5-mini-v1:0",
    "ai21.jamba-1-5-large-v1:0",
    "cohere.command-r-v1:0",
    "cohere.command-r-plus-v1:0",
]

for model_id in models_to_subscribe:
    print(f"\n--- {model_id} ---")
    try:
        # Get offer token
        offers = bedrock.list_foundation_model_agreement_offers(modelId=model_id)
        offer_list = offers.get("modelAccessOffers", [])
        if not offer_list:
            print(f"  No offers found for {model_id}")
            continue

        offer_token = offer_list[0].get("offerToken", "")
        print(f"  Offer token found: {offer_token[:50]}...")

        # Create agreement
        agreement = bedrock.create_foundation_model_agreement(
            modelId=model_id,
            offerToken=offer_token
        )
        print(f"  Agreement created! Status: {agreement.get('modelAccessStatus', 'unknown')}")
    except Exception as e:
        print(f"  Error: {e}")

# ============================================================
# STEP 3: Wait for subscriptions to activate
# ============================================================
print("\n\nSTEP 3: Waiting 30 seconds for subscriptions to activate...")
print("=" * 60)
time.sleep(30)

# ============================================================
# STEP 4: Verify availability
# ============================================================
print("\nSTEP 4: Verifying model availability...")
print("=" * 60)

for model_id in models_to_subscribe:
    try:
        avail = bedrock.get_foundation_model_availability(modelId=model_id)
        agreement = avail.get("agreementAvailability", {}).get("status", "UNKNOWN")
        auth = avail.get("authorizationStatus", "UNKNOWN")
        print(f"  {model_id}: agreement={agreement}, auth={auth}")
    except Exception as e:
        print(f"  {model_id}: Error - {e}")

# ============================================================
# STEP 5: Test invocation
# ============================================================
print("\nSTEP 5: Testing model invocation...")
print("=" * 60)

# Test Claude 3 Haiku
print("\n--- Testing Claude 3 Haiku ---")
try:
    resp = runtime.converse(
        modelId="anthropic.claude-3-haiku-20240307-v1:0",
        messages=[{
            "role": "user",
            "content": [{"text": "Say namaste in Hindi. Keep it brief."}]
        }],
        inferenceConfig={"maxTokens": 50, "temperature": 0.1}
    )
    output = resp.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "")
    print(f"  WORKS! Response: {output}")
except Exception as e:
    print(f"  FAIL: {e}")

# Test AI21 Jamba
print("\n--- Testing AI21 Jamba 1.5 Mini ---")
try:
    resp = runtime.converse(
        modelId="ai21.jamba-1-5-mini-v1:0",
        messages=[{
            "role": "user",
            "content": [{"text": "Say namaste in Hindi. Keep it brief."}]
        }],
        inferenceConfig={"maxTokens": 50, "temperature": 0.1}
    )
    output = resp.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "")
    print(f"  WORKS! Response: {output}")
except Exception as e:
    print(f"  FAIL: {e}")

# Test Cohere Command R
print("\n--- Testing Cohere Command R ---")
try:
    resp = runtime.converse(
        modelId="cohere.command-r-v1:0",
        messages=[{
            "role": "user",
            "content": [{"text": "Say namaste in Hindi. Keep it brief."}]
        }],
        inferenceConfig={"maxTokens": 50, "temperature": 0.1}
    )
    output = resp.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "")
    print(f"  WORKS! Response: {output}")
except Exception as e:
    print(f"  FAIL: {e}")

# Also retry Nova Lite (already subscribed)
print("\n--- Retesting Nova Lite (already subscribed) ---")
try:
    resp = runtime.converse(
        modelId="amazon.nova-lite-v1:0",
        messages=[{
            "role": "user",
            "content": [{"text": "Say namaste in Hindi. Keep it brief."}]
        }],
        inferenceConfig={"maxTokens": 50, "temperature": 0.1}
    )
    output = resp.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "")
    print(f"  WORKS! Response: {output}")
except Exception as e:
    print(f"  FAIL: {e}")

print("\n" + "=" * 60)
print("DONE!")
