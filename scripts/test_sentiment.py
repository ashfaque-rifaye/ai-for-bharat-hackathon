"""Test Comprehend Sentiment integration in /sessions/{id}/message."""
import boto3
import json

lam = boto3.client("lambda", region_name="us-east-1")

# First create a session
create_resp = lam.invoke(
    FunctionName="vaanisetu-orchestrator",
    Payload=json.dumps({
        "httpMethod": "POST",
        "path": "/sessions",
        "body": json.dumps({"language": "hi-IN"}),
    }),
)
create_body = json.loads(json.loads(create_resp["Payload"].read())["body"])
session_id = create_body["sessionId"]
print("SESSION:", session_id)

# Test 1: Positive message
print("\n--- Positive Message ---")
resp = lam.invoke(
    FunctionName="vaanisetu-orchestrator",
    Payload=json.dumps({
        "httpMethod": "POST",
        "path": "/sessions/{}/message".format(session_id),
        "pathParameters": {"id": session_id},
        "body": json.dumps({
            "text": "Bahut achha! Mujhe PM-KISAN ke baare mein batayein. Main bahut khush hoon!",
            "language": "hi-IN",
        }),
    }),
)
body = json.loads(json.loads(resp["Payload"].read())["body"])
sentiment = body.get("sentiment", {})
print("SENTIMENT:", sentiment.get("sentiment"))
print("SCORES:", {k: round(v, 3) for k, v in sentiment.get("scores", {}).items()})
print("AI RESPONSE:", body.get("response", "")[:150])

# Test 2: Negative/frustrated message
print("\n--- Negative Message ---")
resp2 = lam.invoke(
    FunctionName="vaanisetu-orchestrator",
    Payload=json.dumps({
        "httpMethod": "POST",
        "path": "/sessions/{}/message".format(session_id),
        "pathParameters": {"id": session_id},
        "body": json.dumps({
            "text": "Mujhe koi madad nahi mil rahi. Bahut mushkil hai. Koi scheme kaam nahi karti.",
            "language": "hi-IN",
        }),
    }),
)
body2 = json.loads(json.loads(resp2["Payload"].read())["body"])
sentiment2 = body2.get("sentiment", {})
print("SENTIMENT:", sentiment2.get("sentiment"))
print("SCORES:", {k: round(v, 3) for k, v in sentiment2.get("scores", {}).items()})
print("AI RESPONSE:", body2.get("response", "")[:150])
