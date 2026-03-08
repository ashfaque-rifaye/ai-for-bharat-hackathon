"""Quick test for /synthesize endpoint with SSML."""
import boto3
import json
import sys

client = boto3.client("lambda", region_name="us-east-1")

payload = {
    "httpMethod": "POST",
    "path": "/synthesize",
    "body": json.dumps({
        "text": "Namaste! PM-KISAN yojana ke tahat aapko 6000 rupaye milte hain.",
        "language": "hi-IN",
    }),
}

print("Invoking synthesize...")
resp = client.invoke(
    FunctionName="vaanisetu-orchestrator",
    Payload=json.dumps(payload),
)

result = json.loads(resp["Payload"].read())
status = result.get("statusCode", "?")
body = json.loads(result.get("body", "{}"))

print(f"STATUS: {status}")
print(f"ERROR: {body.get('error', 'none')}")
print(f"AUDIO_LEN: {len(body.get('audio', ''))}")
print(f"CONTENT_TYPE: {body.get('contentType', '')}")

if body.get("audio"):
    print("SUCCESS - Audio generated!")
else:
    print("FAILED - No audio returned")
    if "error" in body:
        print(f"  Error detail: {body['error']}")
    sys.exit(1)
