"""Create a Bedrock Guardrail for VaaniSetu.

This guardrail ensures the AI assistant stays on-topic (government schemes)
and blocks harmful, hateful, or inappropriate content.

Run once:  python scripts/create_guardrail.py
"""

import json
import boto3

bedrock = boto3.client("bedrock", region_name="us-east-1")

GUARDRAIL_NAME = "vaanisetu-guardrail"

# Check if guardrail already exists
try:
    existing = bedrock.list_guardrails(maxResults=100)
    for g in existing.get("guardrails", []):
        if g["name"] == GUARDRAIL_NAME:
            print(f"Guardrail already exists: {g['id']} (version: {g['version']})")
            print(f"ARN: {g['arn']}")
            exit(0)
except Exception as e:
    print(f"Warning checking existing guardrails: {e}")

# Create the guardrail
response = bedrock.create_guardrail(
    name=GUARDRAIL_NAME,
    description="VaaniSetu content safety guardrail - keeps AI focused on Indian government schemes and blocks harmful content",

    # Topic policy - block off-topic conversations
    topicPolicyConfig={
        "topicsConfig": [
            {
                "name": "Off-Topic",
                "definition": "Questions not related to Indian government schemes, benefits, eligibility, applications, or social welfare programs",
                "examples": [
                    "How do I hack a website?",
                    "Write me a love letter",
                    "What is the stock price of Tesla?",
                    "Tell me a joke about politicians",
                    "Help me write code",
                ],
                "type": "DENY",
            },
            {
                "name": "Political-Opinion",
                "definition": "Requests for political opinions, party preferences, election advice, or criticism of specific political parties or leaders",
                "examples": [
                    "Which political party is better?",
                    "Should I vote for BJP or Congress?",
                    "Is the PM doing a good job?",
                    "Which government was better for farmers?",
                ],
                "type": "DENY",
            },
        ]
    },

    # Content filters - block harmful content
    contentPolicyConfig={
        "filtersConfig": [
            {"type": "SEXUAL", "inputStrength": "HIGH", "outputStrength": "HIGH"},
            {"type": "VIOLENCE", "inputStrength": "HIGH", "outputStrength": "HIGH"},
            {"type": "HATE", "inputStrength": "HIGH", "outputStrength": "HIGH"},
            {"type": "INSULTS", "inputStrength": "MEDIUM", "outputStrength": "HIGH"},
            {"type": "MISCONDUCT", "inputStrength": "HIGH", "outputStrength": "HIGH"},
            {"type": "PROMPT_ATTACK", "inputStrength": "HIGH", "outputStrength": "NONE"},
        ]
    },

    # Sensitive information filters
    sensitiveInformationPolicyConfig={
        "piiEntitiesConfig": [
            {"type": "CREDIT_DEBIT_CARD_NUMBER", "action": "ANONYMIZE"},
            {"type": "CREDIT_DEBIT_CARD_CVV", "action": "ANONYMIZE"},
            {"type": "CREDIT_DEBIT_CARD_EXPIRY", "action": "ANONYMIZE"},
            {"type": "US_SOCIAL_SECURITY_NUMBER", "action": "ANONYMIZE"},
            {"type": "PASSWORD", "action": "ANONYMIZE"},
            {"type": "PIN", "action": "ANONYMIZE"},
        ],
    },

    # Blocked messaging
    blockedInputMessaging=(
        "I'm sorry, I can only help with Indian government schemes and benefits. "
        "Please ask me about schemes like PM-KISAN, Ayushman Bharat, PM Awas Yojana, etc."
    ),
    blockedOutputsMessaging=(
        "I apologize, I cannot provide that information. I'm here to help you with "
        "Indian government schemes and benefits only. How can I assist you with that?"
    ),
)

guardrail_id = response["guardrailId"]
version = response["version"]
guardrail_arn = response["guardrailArn"]

print(f"Guardrail created!")
print(f"  ID:      {guardrail_id}")
print(f"  Version: {version}")
print(f"  ARN:     {guardrail_arn}")

# Save config for CDK reference
config = {
    "guardrailId": guardrail_id,
    "guardrailVersion": version,
    "guardrailArn": guardrail_arn,
}
with open("guardrail_config.json", "w") as f:
    json.dump(config, f, indent=2)
print(f"\nConfig saved to guardrail_config.json")
