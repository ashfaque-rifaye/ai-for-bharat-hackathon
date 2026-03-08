"""Test the /analytics endpoint."""
import boto3
import json

c = boto3.client("lambda", region_name="us-east-1")

payload = {
    "httpMethod": "GET",
    "path": "/analytics",
}

print("Invoking analytics...")
r = c.invoke(FunctionName="vaanisetu-orchestrator", Payload=json.dumps(payload))
j = json.loads(r["Payload"].read())
print("STATUS:", j.get("statusCode"))

body = json.loads(j.get("body", "{}"))
if "error" in body:
    print("ERROR:", body["error"])
else:
    print("KEYS:", list(body.keys()))
    print(json.dumps(body, indent=2, ensure_ascii=False)[:2000])
