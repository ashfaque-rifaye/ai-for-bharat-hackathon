"""
Check ALL Bedrock model quotas in us-east-1 and also try listing available models.
Read-only - no changes made.
"""
import boto3
import json

region = "us-east-1"

# Part 1: Check which foundation models are available
print("=" * 80)
print("PART 1: AVAILABLE FOUNDATION MODELS IN us-east-1")
print("=" * 80)

bedrock = boto3.client("bedrock", region_name=region)
response = bedrock.list_foundation_models()
models = response.get("modelSummaries", [])

# Group by provider
providers = {}
for m in models:
    provider = m.get("providerName", "Unknown")
    if provider not in providers:
        providers[provider] = []
    providers[provider].append({
        "id": m["modelId"],
        "name": m.get("modelName", ""),
        "status": m.get("modelLifecycle", {}).get("status", ""),
        "input": m.get("inputModalities", []),
        "output": m.get("outputModalities", []),
        "inference": m.get("inferenceTypesSupported", []),
    })

for provider, model_list in sorted(providers.items()):
    active = [m for m in model_list if m["status"] == "ACTIVE"]
    if active:
        print(f"\n{provider} ({len(active)} active models):")
        for m in active:
            if "ON_DEMAND" in m["inference"] and "TEXT" in m["input"]:
                print(f"  {m['id']} - {m['name']} [{m['status']}]")

# Part 2: Service Quotas
print("\n" + "=" * 80)
print("PART 2: ALL NON-ZERO BEDROCK QUOTAS")
print("=" * 80)

sq = boto3.client("service-quotas", region_name=region)
paginator = sq.get_paginator("list_service_quotas")

found = []
for page in paginator.paginate(ServiceCode="bedrock"):
    for q in page["Quotas"]:
        if q["Value"] > 0:
            found.append({
                "name": q["QuotaName"],
                "value": q["Value"],
                "adjustable": q.get("Adjustable", False),
            })

if found:
    for f in found:
        print(f"  {f['name']}: {f['value']} (Adjustable: {f['adjustable']})")
else:
    print("  NO non-zero quotas found!")

print(f"\nTotal non-zero: {len(found)}")

# Part 3: Try invoking a few models directly to see which actually work
print("\n" + "=" * 80)
print("PART 3: QUICK INVOKE TEST (text models)")
print("=" * 80)

runtime = boto3.client("bedrock-runtime", region_name=region)

test_models = [
    # Claude models
    ("anthropic.claude-3-5-sonnet-20241022-v2:0", "claude-messages"),
    ("anthropic.claude-3-haiku-20240307-v1:0", "claude-messages"),
    ("anthropic.claude-3-sonnet-20240229-v1:0", "claude-messages"),
    # Llama models
    ("meta.llama3-8b-instruct-v1:0", "llama-messages"),
    ("meta.llama3-1-8b-instruct-v1:0", "llama-messages"),
    # Mistral
    ("mistral.mistral-7b-instruct-v0:2", "mistral"),
    ("mistral.mistral-large-2407-v1:0", "mistral-messages"),
    # Titan
    ("amazon.titan-text-express-v1", "titan"),
    ("amazon.titan-text-lite-v1", "titan"),
    # Nova (cross-region)
    ("us.amazon.nova-lite-v1:0", "nova"),
    ("us.amazon.nova-micro-v1:0", "nova"),
    # Cohere
    ("cohere.command-r-v1:0", "cohere-messages"),
    # AI21
    ("ai21.jamba-1-5-mini-v1:0", "ai21-messages"),
]

for model_id, fmt in test_models:
    try:
        if fmt == "claude-messages":
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 20,
                "messages": [{"role": "user", "content": "Say hi"}]
            })
        elif fmt == "nova":
            body = json.dumps({
                "messages": [{"role": "user", "content": [{"text": "Say hi"}]}],
                "inferenceConfig": {"maxNewTokens": 20}
            })
        elif fmt in ("llama-messages", "mistral-messages", "cohere-messages", "ai21-messages"):
            body = json.dumps({
                "messages": [{"role": "user", "content": "Say hi"}],
                "max_tokens": 20
            })
        elif fmt == "mistral":
            body = json.dumps({
                "prompt": "<s>[INST] Say hi [/INST]",
                "max_tokens": 20
            })
        elif fmt == "titan":
            body = json.dumps({
                "inputText": "Say hi",
                "textGenerationConfig": {"maxTokenCount": 20}
            })
        else:
            continue

        resp = runtime.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=body
        )
        result = json.loads(resp["body"].read())
        print(f"  ✓ {model_id} — WORKS!")
    except Exception as e:
        err = str(e)
        if "ThrottlingException" in err:
            reason = "Throttled (quota=0)"
        elif "AccessDeniedException" in err:
            reason = "Access Denied"
        elif "ValidationException" in err:
            reason = "Validation Error (model may exist but format wrong)"
        elif "ResourceNotFoundException" in err:
            reason = "Not found in region"
        else:
            reason = err[:80]
        print(f"  ✗ {model_id} — {reason}")
