"""
Check agreement availability for ALL text models in us-east-1.
Finds which models need AWS Marketplace subscription vs already subscribed.
"""
import boto3
import json

bedrock = boto3.client("bedrock", region_name="us-east-1")

resp = bedrock.list_foundation_models()
models = [m for m in resp["modelSummaries"]
          if m.get("modelLifecycle", {}).get("status") == "ACTIVE"
          and "ON_DEMAND" in m.get("inferenceTypesSupported", [])
          and "TEXT" in m.get("inputModalities", [])
          and "embed" not in m["modelId"].lower()]

not_available = []
available_models = []

for m in sorted(models, key=lambda x: x["modelId"]):
    model_id = m["modelId"]
    try:
        avail = bedrock.get_foundation_model_availability(modelId=model_id)
        agreement = avail.get("agreementAvailability", {}).get("status", "UNKNOWN")
        auth = avail.get("authorizationStatus", "UNKNOWN")
        entitle = avail.get("entitlementAvailability", "UNKNOWN")
        region_status = avail.get("regionAvailability", "UNKNOWN")

        entry = {
            "id": model_id,
            "name": m.get("modelName", ""),
            "provider": m.get("providerName", ""),
            "agreement": agreement,
            "auth": auth,
            "entitle": entitle,
            "region": region_status,
        }

        if agreement == "NOT_AVAILABLE":
            not_available.append(entry)
        else:
            available_models.append(entry)
    except Exception as e:
        print(f"  ERROR: {model_id} - {str(e)[:80]}")

print("=" * 70)
print("MODELS NEEDING SUBSCRIPTION (agreementAvailability: NOT_AVAILABLE):")
print("=" * 70)
for m in not_available:
    print(f"  {m['id']}")
    print(f"    Name: {m['name']} | Provider: {m['provider']}")
    print(f"    Auth: {m['auth']} | Entitle: {m['entitle']} | Region: {m['region']}")

print(f"\nTotal needing subscription: {len(not_available)}")

print(f"\n{'='*70}")
print(f"ALREADY SUBSCRIBED ({len(available_models)} models):")
print("=" * 70)
for m in available_models:
    print(f"  {m['id']} - {m['name']} ({m['provider']})")
