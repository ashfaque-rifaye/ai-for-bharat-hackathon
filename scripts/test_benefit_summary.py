"""Test the /benefit-summary endpoint."""
import boto3
import json

c = boto3.client("lambda", region_name="us-east-1")

payload = {
    "httpMethod": "POST",
    "path": "/benefit-summary",
    "body": json.dumps({
        "sessionId": "test-benefit-001",
        "userProfile": {
            "age": 35,
            "gender": "male",
            "state": "uttar_pradesh",
            "occupation": "farmer",
            "income": 80000,
            "landOwnership": True,
            "caste": "obc",
            "hasLpgConnection": False,
            "hasBankAccount": True,
            "hasDaughter": True
        },
        "language": "hi-IN"
    })
}

r = c.invoke(FunctionName="vaanisetu-orchestrator", Payload=json.dumps(payload))
j = json.loads(r["Payload"].read())
print("STATUS:", j.get("statusCode"))

body = json.loads(j.get("body", "{}"))
if "error" in body:
    print("ERROR:", body["error"])
else:
    print("TOTAL_BENEFIT: Rs", body.get("totalAnnualBenefit"))
    print("ELIGIBLE_COUNT:", body.get("eligibleCount"))
    print()
    for s in body.get("eligibleSchemes", []):
        print("  {} ({}): Rs {}".format(s["schemeId"], s["category"], s["benefitAmount"]))
    print()
    for sy in body.get("synergies", []):
        print("  SYNERGY: {} - {} ({} matched, allMatched={})".format(
            sy["id"], sy["label"], len(sy["schemes"]), sy["allMatched"]
        ))
    print()
    print("SUMMARY:", body.get("summaryText", "")[:400])
