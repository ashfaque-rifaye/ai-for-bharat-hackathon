import boto3
import json

bedrock = boto3.client("bedrock", region_name="us-east-1")
r = bedrock.create_guardrail_version(
    guardrailIdentifier="pvdx279hci2j",
    description="v1 - content safety for VaaniSetu",
)
version = r["version"]
print(f"Published version: {version}")

config = {"guardrailId": "pvdx279hci2j", "guardrailVersion": version}
with open("guardrail_config.json", "w") as f:
    json.dump(config, f, indent=2)
print("Config updated")
