"""
Quick test: try invoking various Bedrock models to see which ones actually respond.
Read-only test — sends a tiny "Say hi" prompt to each model.
"""
import boto3
import json

region = "us-east-1"
runtime = boto3.client("bedrock-runtime", region_name=region)

test_models = [
    # Claude models (Anthropic)
    ("anthropic.claude-3-5-sonnet-20241022-v2:0", "claude"),
    ("anthropic.claude-3-haiku-20240307-v1:0", "claude"),
    ("anthropic.claude-3-sonnet-20240229-v1:0", "claude"),
    ("anthropic.claude-instant-v1", "claude"),
    # Cross-region Claude
    ("us.anthropic.claude-3-5-sonnet-20241022-v2:0", "claude"),
    ("us.anthropic.claude-3-haiku-20240307-v1:0", "claude"),
    # Llama models (Meta)
    ("meta.llama3-8b-instruct-v1:0", "llama"),
    ("meta.llama3-1-8b-instruct-v1:0", "llama"),
    ("us.meta.llama3-2-1b-instruct-v1:0", "llama"),
    # Mistral
    ("mistral.mistral-7b-instruct-v0:2", "mistral-old"),
    ("mistral.mistral-large-2407-v1:0", "mistral"),
    # Amazon Titan
    ("amazon.titan-text-express-v1", "titan"),
    ("amazon.titan-text-lite-v1", "titan"),
    # Amazon Nova (direct + cross-region)
    ("amazon.nova-lite-v1:0", "nova"),
    ("us.amazon.nova-lite-v1:0", "nova"),
    ("us.amazon.nova-micro-v1:0", "nova"),
    # Cohere
    ("cohere.command-r-v1:0", "cohere"),
    ("cohere.command-light-text-v14", "cohere-old"),
    # AI21
    ("ai21.jamba-1-5-mini-v1:0", "ai21"),
    ("ai21.jamba-1-5-large-v1:0", "ai21"),
]

print("BEDROCK MODEL INVOKE TEST — us-east-1")
print("=" * 70)

working = []

for model_id, fmt in test_models:
    try:
        if fmt == "claude":
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
        elif fmt in ("llama", "mistral", "cohere", "ai21"):
            body = json.dumps({
                "messages": [{"role": "user", "content": "Say hi"}],
                "max_tokens": 20
            })
        elif fmt == "mistral-old":
            body = json.dumps({
                "prompt": "<s>[INST] Say hi [/INST]",
                "max_tokens": 20
            })
        elif fmt == "cohere-old":
            body = json.dumps({
                "prompt": "Say hi",
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
        working.append(model_id)
        print(f"  WORKS >> {model_id}")
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
            reason = err[:100]
        print(f"  FAIL  >> {model_id} — {reason}")

print("\n" + "=" * 70)
if working:
    print(f"WORKING MODELS ({len(working)}):")
    for m in working:
        print(f"  * {m}")
else:
    print("NO WORKING MODELS FOUND in us-east-1")
print("=" * 70)
