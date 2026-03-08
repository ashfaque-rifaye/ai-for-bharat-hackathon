"""
Test ALL 43 available text models in ap-south-1 (Mumbai).
Uses the Converse API which works with a standard format across models.
"""
import boto3
import json

region = "ap-south-1"
bedrock = boto3.client("bedrock", region_name=region)
runtime = boto3.client("bedrock-runtime", region_name=region)

# Get all available text models
resp = bedrock.list_foundation_models()
models = [m for m in resp.get("modelSummaries", [])
          if m.get("modelLifecycle", {}).get("status") == "ACTIVE"
          and "ON_DEMAND" in m.get("inferenceTypesSupported", [])
          and "TEXT" in m.get("inputModalities", [])]

print(f"TESTING ALL {len(models)} TEXT MODELS IN {region}")
print("=" * 70)

working = []
failed = []

for m in sorted(models, key=lambda x: x["modelId"]):
    model_id = m["modelId"]
    name = m.get("modelName", model_id)
    provider = m.get("providerName", "Unknown")
    
    # Skip embedding-only models
    if "embed" in model_id.lower():
        print(f"  SKIP >> {model_id} (embedding model)")
        continue
    
    # Try the Converse API first (works with most models)
    try:
        resp = runtime.converse(
            modelId=model_id,
            messages=[{
                "role": "user",
                "content": [{"text": "Say hello in Hindi in 5 words or less"}]
            }],
            inferenceConfig={
                "maxTokens": 30,
                "temperature": 0.1
            }
        )
        output = resp.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "")
        working.append({"id": model_id, "name": name, "provider": provider})
        print(f"  WORKS >> {model_id} ({provider})")
        print(f"           Response: {output[:80]}")
    except Exception as e:
        err = str(e)
        if "ThrottlingException" in err:
            reason = "THROTTLED (quota=0)"
        elif "AccessDeniedException" in err:
            reason = "ACCESS DENIED"
        elif "ValidationException" in err:
            # Try invoke_model as fallback for models that don't support Converse
            try:
                # Generic messages format
                body = json.dumps({
                    "messages": [{"role": "user", "content": "Say hello"}],
                    "max_tokens": 30
                })
                resp2 = runtime.invoke_model(
                    modelId=model_id,
                    contentType="application/json",
                    accept="application/json",
                    body=body
                )
                result = json.loads(resp2["body"].read())
                working.append({"id": model_id, "name": name, "provider": provider})
                print(f"  WORKS >> {model_id} ({provider}) [via invoke_model]")
                print(f"           Response: {str(result)[:80]}")
                continue
            except Exception as e2:
                reason = f"VALIDATION: {str(e2)[:80]}"
        elif "ResourceNotFoundException" in err:
            reason = "NOT FOUND"
        elif "ModelNotReadyException" in err:
            reason = "NOT READY"
        else:
            reason = err[:120]
        failed.append({"id": model_id, "reason": reason})
        print(f"  FAIL  >> {model_id} — {reason}")

print(f"\n{'='*70}")
if working:
    print(f"\nWORKING MODELS IN {region} ({len(working)}):")
    for w in working:
        print(f"  ★ {w['id']} — {w['name']} ({w['provider']})")
else:
    print(f"\nNO WORKING MODELS IN {region}")
    print("\nAll failures:")
    for f in failed:
        print(f"  {f['id']} — {f['reason']}")
print(f"{'='*70}")
