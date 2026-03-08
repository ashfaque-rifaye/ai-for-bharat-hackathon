"""Quick check: verify WhatsApp Lambda exists and has correct env vars."""
import boto3

lam = boto3.client("lambda", region_name="us-east-1")

try:
    r = lam.get_function(FunctionName="vaanisetu-whatsapp")
    cfg = r["Configuration"]
    env = cfg.get("Environment", {}).get("Variables", {})
    print("WhatsApp Lambda EXISTS")
    print(f"  Runtime:           {cfg['Runtime']}")
    print(f"  Handler:           {cfg['Handler']}")
    print(f"  AI_ENGINE_FUNCTION: {env.get('AI_ENGINE_FUNCTION', 'NOT SET')}")
    print(f"  GUARDRAIL_ID:      {env.get('GUARDRAIL_ID', 'NOT SET')}")
    print(f"  SESSIONS_TABLE:    {env.get('SESSIONS_TABLE', 'NOT SET')}")
    print(f"  TWILIO_ACCOUNT_SID: {'SET' if env.get('TWILIO_ACCOUNT_SID') else 'NOT SET'}")
except lam.exceptions.ResourceNotFoundException:
    print("WhatsApp Lambda NOT FOUND")

# Also check AI Engine has guardrails
try:
    r2 = lam.get_function(FunctionName="vaanisetu-ai-engine")
    env2 = r2["Configuration"].get("Environment", {}).get("Variables", {})
    print(f"\nAI Engine GUARDRAIL_ID:      {env2.get('GUARDRAIL_ID', 'NOT SET')}")
    print(f"AI Engine GUARDRAIL_VERSION: {env2.get('GUARDRAIL_VERSION', 'NOT SET')}")
except Exception as e:
    print(f"AI Engine check failed: {e}")
