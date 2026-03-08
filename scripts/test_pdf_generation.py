"""Test PDF generation endpoint."""
import boto3
import json

lam = boto3.client("lambda", region_name="us-east-1")

# Test 1: Benefit Summary PDF
print("=" * 60)
print("TEST 1: Benefit Summary PDF")
print("=" * 60)

payload = {
    "httpMethod": "POST",
    "path": "/generate-pdf",
    "body": json.dumps({
        "type": "benefit-summary",
        "language": "hi-IN",
        "userProfile": {
            "occupation": "farmer",
            "income": 80000,
            "state": "Uttar Pradesh",
            "landSize": 2.5,
            "age": 45,
            "gender": "male",
            "familySize": 5,
            "caste": "OBC",
            "hasDaughters": True,
        },
    }),
}

resp = lam.invoke(
    FunctionName="vaanisetu-orchestrator",
    Payload=json.dumps(payload),
)
result = json.loads(resp["Payload"].read())
print(f"STATUS: {result.get('statusCode')}")
body = json.loads(result.get("body", "{}"))
if result.get("statusCode") == 200:
    print(f"PDF URL: {body.get('pdfUrl', '')[:100]}...")
    print(f"File: {body.get('fileName')}")
    print(f"Size: {body.get('sizeBytes')} bytes")
else:
    print(f"ERROR: {body.get('error')}")

# Test 2: Application Confirmation PDF
print("\n" + "=" * 60)
print("TEST 2: Application Confirmation PDF")
print("=" * 60)

payload2 = {
    "httpMethod": "POST",
    "path": "/generate-pdf",
    "body": json.dumps({
        "type": "application-confirmation",
        "language": "en-IN",
        "applicationData": {
            "applicationId": "APP-2026-PM-KISAN-001",
            "status": "SUBMITTED",
            "submittedAt": "2026-03-01T23:00:00Z",
            "fields": {
                "Full Name": "Ramesh Kumar",
                "Aadhaar Number": "XXXX-XXXX-1234",
                "Bank Account": "XXXX-5678",
                "Mobile": "+91-98765-43210",
                "Land Size": "2.5 acres",
                "Village": "Shantipur",
                "District": "Lucknow",
                "State": "Uttar Pradesh",
            },
        },
        "schemeData": {
            "schemeId": "PM-KISAN",
            "name": {"en": "PM Kisan Samman Nidhi", "hi": "पीएम किसान सम्मान निधि"},
            "category": "agriculture",
        },
    }),
}

resp2 = lam.invoke(
    FunctionName="vaanisetu-orchestrator",
    Payload=json.dumps(payload2),
)
result2 = json.loads(resp2["Payload"].read())
print(f"STATUS: {result2.get('statusCode')}")
body2 = json.loads(result2.get("body", "{}"))
if result2.get("statusCode") == 200:
    print(f"PDF URL: {body2.get('pdfUrl', '')[:100]}...")
    print(f"File: {body2.get('fileName')}")
    print(f"Size: {body2.get('sizeBytes')} bytes")
else:
    print(f"ERROR: {body2.get('error')}")
