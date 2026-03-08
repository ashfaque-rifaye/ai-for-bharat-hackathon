"""
Test Bedrock model invocation in ap-south-1 (Mumbai).
Read-only — sends tiny "Say hi" prompt to each model.
"""
import boto3
import json

region = "ap-south-1"
runtime = boto3.client("bedrock-runtime", region_name=region)

# First check what models are available in this region
bedrock = boto3.client("bedrock", region_name=region)
resp = bedrock.list_foundation_models()
available = [m["modelId"] for m in resp.get("modelSummaries", [])
             if m.get("modelLifecycle", {}).get("status") == "ACTIVE"
             and "ON_DEMAND" in m.get("inferenceTypesSupported", [])
             and "TEXT" in m.get("inputModalities", [])]

print(f"AVAILABLE TEXT MODELS IN {region}: {len(available)}")
for m in sorted(available):
    print(f"  {m}")

print(f"\n{'='*70}")
print(f"INVOKE TEST — {region}")
print(f"{'='*70}")

test_models = [
    # Claude
    ("anthropic.claude-3-5-sonnet-20241022-v2:0", "claude"),
    ("anthropic.claude-3-haiku-20240307-v1:0", "claude"),
    ("anthropic.claude-v2", "claude-v2"),
    # Cross-region Claude  
    ("us.anthropic.claude-3-5-sonnet-20241022-v2:0", "claude"),
    # Llama
    ("meta.llama3-8b-instruct-v1:0", "llama"),
    ("us.meta.llama3-2-1b-instruct-v1:0", "llama"),
    # Mistral
    ("mistral.mistral-7b-instruct-v0:2", "mistral-old"),
    # Titan
    ("amazon.titan-text-express-v1", "titan"),
    ("amazon.titan-text-lite-v1", "titan"),
    # Nova
    ("amazon.nova-lite-v1:0", "nova"),
    ("amazon.nova-micro-v1:0", "nova"),
    ("us.amazon.nova-lite-v1:0", "nova"),
    ("us.amazon.nova-micro-v1:0", "nova"),
    # Cohere
    ("cohere.command-r-v1:0", "cohere"),
    # AI21
    ("ai21.jamba-1-5-mini-v1:0", "ai21"),
]

working = []

for model_id, fmt in test_models:
    try:
        if fmt == "claude":
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 20,
                "messages": [{"role": "user", "content": "Say hi in Hindi"}]
            })
        elif fmt == "claude-v2":
            body = json.dumps({
                "prompt": "\n\nHuman: Say hi\n\nAssistant:",
                "max_tokens_to_sample": 20
            })
        elif fmt == "nova":
            body = json.dumps({
                "messages": [{"role": "user", "content": [{"text": "Say hi in Hindi"}]}],
                "inferenceConfig": {"maxNewTokens": 20}
            })
        elif fmt in ("llama", "cohere", "ai21"):
            body = json.dumps({
                "messages": [{"role": "user", "content": "Say hi in Hindi"}],
                "max_tokens": 20
            })
        elif fmt == "mistral-old":
            body = json.dumps({
                "prompt": "<s>[INST] Say hi [/INST]",
                "max_tokens": 20
            })
        elif fmt == "titan":
            body = json.dumps({
                "inputText": "Say hi in Hindi",
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
        working.append(model_id)
        
        # Try to extract the response text
        text = ""
        if fmt == "claude":
            text = result.get("content", [{}])[0].get("text", "")
        elif fmt == "claude-v2":
            text = result.get("completion", "")
        elif fmt == "nova":
            text = result.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "")
        elif fmt == "titan":
            text = result.get("results", [{}])[0].get("outputText", "")
        else:
            text = str(result)[:100]
        
        print(f"  WORKS >> {model_id}")
        print(f"           Response: {text[:80]}")
    except Exception as e:
        err = str(e)
        if "ThrottlingException" in err:
            reason = "THROTTLED (quota=0)"
        elif "AccessDeniedException" in err:
            reason = "ACCESS DENIED"
        elif "ValidationException" in err:
            reason = "VALIDATION ERROR"
        elif "ResourceNotFoundException" in err:
            reason = "NOT FOUND"
        else:
            reason = err[:120]
        print(f"  FAIL  >> {model_id} — {reason}")

print(f"\n{'='*70}")
if working:
    print(f"WORKING MODELS IN {region} ({len(working)}):")
    for m in working:
        print(f"  * {m}")
else:
    print(f"NO WORKING MODELS IN {region}")
print(f"{'='*70}")
