"""Fix the Bedrock Guardrail — redefine topics with positive descriptions.

The original guardrail had an inverted topic filter because the "Off-Topic"
definition used a negation ("Questions NOT related to...") which confused
Bedrock's semantic classifier. The fix: describe what to BLOCK as positive topics.

We delete the old guardrail and create a corrected one.
"""

import json
import boto3

bedrock = boto3.client("bedrock", region_name="us-east-1")

OLD_GUARDRAIL_ID = "pvdx279hci2j"

# Step 1: Delete the old guardrail
print("Deleting old guardrail...")
try:
    bedrock.delete_guardrail(guardrailIdentifier=OLD_GUARDRAIL_ID)
    print(f"  Deleted: {OLD_GUARDRAIL_ID}")
except Exception as e:
    print(f"  Warning: {e}")

# Step 2: Create corrected guardrail with positive topic definitions
print("\nCreating corrected guardrail...")
response = bedrock.create_guardrail(
    name="vaanisetu-guardrail-v2",
    description="VaaniSetu content safety — keeps AI on-topic (Indian government schemes) and blocks harmful content",

    # Topic policy — POSITIVE definitions of what to block
    topicPolicyConfig={
        "topicsConfig": [
            {
                "name": "Entertainment-Content",
                "definition": "Requests for creative writing, poetry, stories, jokes, songs, movie reviews, or entertainment content",
                "examples": [
                    "Write me a poem about the moon",
                    "Tell me a joke",
                    "Recommend a good movie",
                    "Write a love letter for me",
                    "Sing me a song",
                ],
                "type": "DENY",
            },
            {
                "name": "General-Knowledge",
                "definition": "Questions about science, technology, cooking, recipes, sports, mathematics, geography, or general education unrelated to government welfare",
                "examples": [
                    "How do I make biryani?",
                    "What is the capital of France?",
                    "Explain quantum physics",
                    "What is the stock price of Tesla?",
                    "Help me write Python code",
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
            {
                "name": "Hacking-Illegal",
                "definition": "Requests for hacking, illegal activities, fraud, document forgery, or bypassing security systems",
                "examples": [
                    "How do I hack a website?",
                    "How to create fake Aadhaar card?",
                    "How to cheat on government exams?",
                    "Help me forge documents",
                ],
                "type": "DENY",
            },
        ]
    },

    # Content filters — block harmful content
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

    # Sensitive information filters — anonymize PII
    sensitiveInformationPolicyConfig={
        "piiEntitiesConfig": [
            {"type": "CREDIT_DEBIT_CARD_NUMBER", "action": "ANONYMIZE"},
            {"type": "CREDIT_DEBIT_CARD_CVV", "action": "ANONYMIZE"},
            {"type": "CREDIT_DEBIT_CARD_EXPIRY", "action": "ANONYMIZE"},
            {"type": "US_SOCIAL_SECURITY_NUMBER", "action": "ANONYMIZE"},
            {"type": "PASSWORD", "action": "ANONYMIZE"},
            {"type": "PIN", "action": "ANONYMIZE"},
        ]
    },

    blockedInputMessaging="I'm sorry, I can only help with Indian government schemes and benefits. Please ask me about schemes like PM-KISAN, Ayushman Bharat, PM Awas Yojana, etc.",
    blockedOutputsMessaging="I'm sorry, I can only help with Indian government schemes and benefits. Please ask me about schemes like PM-KISAN, Ayushman Bharat, PM Awas Yojana, etc.",
)

guardrail_id = response["guardrailId"]
guardrail_arn = response["guardrailArn"]
print(f"  Created! ID: {guardrail_id}")
print(f"  ARN: {guardrail_arn}")

# Step 3: Publish version 1
print("\nPublishing version 1...")
pub = bedrock.create_guardrail_version(
    guardrailIdentifier=guardrail_id,
    description="v1 — corrected topic filters (positive definitions)",
)
version = pub["version"]
print(f"  Published version: {version}")

# Step 4: Save config
config = {"guardrailId": guardrail_id, "guardrailVersion": version}
with open("guardrail_config.json", "w") as f:
    json.dump(config, f, indent=2)
print(f"\nConfig saved: {json.dumps(config)}")
print(f"\n>>> Update CDK & AI engine with new GUARDRAIL_ID: {guardrail_id}")
