"""Test auto language detection on first message."""
import boto3
import json

lam = boto3.client("lambda", region_name="us-east-1")

# Create a session (default: hi-IN)
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
print("INITIAL LANG:", create_body.get("language"))

# Send a Tamil message — should auto-detect and switch
print("\n--- Sending Tamil message to Hindi session ---")
resp = lam.invoke(
    FunctionName="vaanisetu-orchestrator",
    Payload=json.dumps({
        "httpMethod": "POST",
        "path": "/sessions/{}/message".format(session_id),
        "pathParameters": {"id": session_id},
        "body": json.dumps({
            "text": "வணக்கம்! நான் ஒரு விவசாயி. எனக்கு என்ன திட்டங்கள் கிடைக்கும்?",
            "language": "hi-IN",
        }),
    }),
)
body = json.loads(json.loads(resp["Payload"].read())["body"])
print("DETECTED_LANG:", body.get("detectedLanguage"))
print("SENTIMENT:", body.get("sentiment", {}).get("sentiment"))
print("AI RESPONSE:", body.get("response", "")[:200])

# Send an English message to a fresh session
print("\n--- Sending English message ---")
create2 = lam.invoke(
    FunctionName="vaanisetu-orchestrator",
    Payload=json.dumps({
        "httpMethod": "POST",
        "path": "/sessions",
        "body": json.dumps({"language": "hi-IN"}),
    }),
)
sid2 = json.loads(json.loads(create2["Payload"].read())["body"])["sessionId"]
resp2 = lam.invoke(
    FunctionName="vaanisetu-orchestrator",
    Payload=json.dumps({
        "httpMethod": "POST",
        "path": "/sessions/{}/message".format(sid2),
        "pathParameters": {"id": sid2},
        "body": json.dumps({
            "text": "Hello! I am a farmer from Uttar Pradesh. What schemes can I apply for?",
            "language": "hi-IN",
        }),
    }),
)
body2 = json.loads(json.loads(resp2["Payload"].read())["body"])
print("DETECTED_LANG:", body2.get("detectedLanguage"))
print("AI RESPONSE:", body2.get("response", "")[:200])
