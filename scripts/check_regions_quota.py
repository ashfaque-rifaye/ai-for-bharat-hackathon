"""
Check Bedrock Nova Lite quotas across ALL supported regions.
Goal: Find a region where AISPL account has non-zero quotas.
"""
import boto3
import json

# All regions where Nova Lite is available
REGIONS = [
    "us-east-1",       # N. Virginia
    "us-east-2",       # Ohio
    "us-west-2",       # Oregon
    "ap-south-1",      # Mumbai (India)
    "ap-southeast-1",  # Singapore
    "ap-southeast-2",  # Sydney
    "ap-northeast-1",  # Tokyo
    "eu-west-1",       # Ireland
    "eu-west-2",       # London
    "eu-central-1",    # Frankfurt
    "ca-central-1",    # Canada
    "sa-east-1",       # São Paulo
]

MODEL_ID = "amazon.nova-lite-v1:0"

# Service Quotas code for "On-demand model inference tokens per minute" for Nova Lite
# We'll also check if the model is even listed in each region
QUOTA_CODE = "L-D8E0583E"  # Nova Lite tokens/min
SERVICE_CODE = "bedrock"

print("=" * 80)
print("BEDROCK NOVA LITE QUOTA CHECK ACROSS ALL REGIONS")
print("=" * 80)

results = []

for region in REGIONS:
    print(f"\n--- {region} ---")
    try:
        # Check if model exists in this region
        bedrock_client = boto3.client("bedrock", region_name=region)
        try:
            model_info = bedrock_client.get_foundation_model(modelIdentifier=MODEL_ID)
            model_status = model_info["modelDetails"]["modelLifecycle"]["status"]
            print(f"  Model Status: {model_status}")
        except Exception as e:
            print(f"  Model not available: {e}")
            results.append({"region": region, "model": "NOT AVAILABLE", "quotas": {}})
            continue

        # Check quotas via Service Quotas
        sq_client = boto3.client("service-quotas", region_name=region)

        # List all Bedrock quotas in this region
        quota_values = {}
        paginator = sq_client.get_paginator("list_service_quotas")
        for page in paginator.paginate(ServiceCode=SERVICE_CODE):
            for q in page["Quotas"]:
                name = q["QuotaName"]
                value = q["Value"]
                adjustable = q.get("Adjustable", False)
                # Only show Nova Lite related quotas
                if "nova lite" in name.lower() or "Nova Lite" in name:
                    quota_values[name] = {"value": value, "adjustable": adjustable}
                    marker = "✓" if value > 0 else "✗"
                    adj = "Adjustable" if adjustable else "NOT Adjustable"
                    print(f"  {marker} {name}: {value} ({adj})")

        if not quota_values:
            print("  No Nova Lite specific quotas found, checking defaults...")
            # Try listing default quotas
            for page in paginator.paginate(ServiceCode=SERVICE_CODE):
                for q in page["Quotas"]:
                    name = q["QuotaName"]
                    value = q["Value"]
                    if "nova lite" in name.lower():
                        quota_values[name] = {"value": value, "adjustable": q.get("Adjustable", False)}
                        print(f"  {name}: {value}")

        results.append({"region": region, "model": model_status, "quotas": quota_values})

    except Exception as e:
        print(f"  Error: {e}")
        results.append({"region": region, "model": "ERROR", "quotas": {}, "error": str(e)})

print("\n" + "=" * 80)
print("SUMMARY: Regions with NON-ZERO Nova Lite quotas")
print("=" * 80)

found_any = False
for r in results:
    for qname, qinfo in r["quotas"].items():
        if qinfo["value"] > 0:
            found_any = True
            print(f"  ★ {r['region']}: {qname} = {qinfo['value']} (Adjustable: {qinfo['adjustable']})")

if not found_any:
    print("  None found. All regions have 0 quotas for Nova Lite.")
    print("\n  Checking cross-region inference profiles...")

# Also check cross-region inference profiles
print("\n" + "=" * 80)
print("CHECKING CROSS-REGION INFERENCE PROFILES")
print("=" * 80)

for region in ["us-east-1", "us-west-2", "ap-south-1"]:
    try:
        client = boto3.client("bedrock", region_name=region)
        response = client.list_inference_profiles()
        profiles = response.get("inferenceProfileSummaries", [])
        if profiles:
            print(f"\n  {region}: Found {len(profiles)} inference profiles:")
            for p in profiles:
                print(f"    - {p['inferenceProfileName']} ({p['inferenceProfileId']})")
                print(f"      Status: {p.get('status', 'N/A')}, Type: {p.get('type', 'N/A')}")
        else:
            print(f"\n  {region}: No inference profiles found")
    except Exception as e:
        print(f"\n  {region}: Error listing profiles: {e}")

# Also check if we can invoke via cross-region profile ID
print("\n" + "=" * 80)
print("TRYING CROSS-REGION INFERENCE (us.amazon.nova-lite-v1:0)")
print("=" * 80)

for region in ["us-east-1", "us-west-2"]:
    try:
        runtime = boto3.client("bedrock-runtime", region_name=region)
        response = runtime.invoke_model(
            modelId="us.amazon.nova-lite-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "messages": [{"role": "user", "content": [{"text": "Say hello in Hindi"}]}],
                "inferenceConfig": {"maxNewTokens": 50}
            })
        )
        result = json.loads(response["body"].read())
        print(f"  ★★★ {region} CROSS-REGION WORKS! ★★★")
        output_text = result.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "")
        print(f"  Response: {output_text[:200]}")
        break
    except Exception as e:
        print(f"  {region}: {e}")
