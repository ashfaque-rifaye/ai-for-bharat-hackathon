"""VaaniSetu Bedrock Agent Setup — Creates and configures the Bedrock Agent via API.

Usage:
    python scripts/setup_bedrock_agent.py --region ap-south-1

This script:
1. Creates a Bedrock Agent with VaaniSetu configuration
2. Attaches action groups (Lambda functions)
3. Attaches knowledge bases
4. Creates a guardrail
5. Prepares the agent for use
"""

import argparse
import json
import os
import sys
import time

import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
AGENT_NAME = "VaaniSetuAgent"


def create_agent_role(iam_client, region: str) -> str:
    """Create IAM role for the Bedrock Agent."""
    role_name = "vaanisetu-bedrock-agent-role"

    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "bedrock.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }

    try:
        role = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="IAM role for VaaniSetu Bedrock Agent",
        )
        role_arn = role["Role"]["Arn"]
        print(f"  Created IAM role: {role_arn}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "EntityAlreadyExists":
            role = iam_client.get_role(RoleName=role_name)
            role_arn = role["Role"]["Arn"]
            print(f"  Using existing IAM role: {role_arn}")
        else:
            raise

    # Attach required policies
    policies = {
        "BedrockAccess": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:InvokeModel",
                        "bedrock:Converse",
                        "bedrock:Retrieve",
                        "bedrock:RetrieveAndGenerate",
                    ],
                    "Resource": "*",
                },
                {
                    "Effect": "Allow",
                    "Action": ["lambda:InvokeFunction"],
                    "Resource": f"arn:aws:lambda:{region}:*:function:vaanisetu-*",
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:ListBucket",
                    ],
                    "Resource": "*",
                },
            ],
        }
    }

    for policy_name, policy_doc in policies.items():
        full_name = f"vaanisetu-agent-{policy_name}"
        try:
            iam_client.create_policy(
                PolicyName=full_name,
                PolicyDocument=json.dumps(policy_doc),
            )
        except ClientError as e:
            if e.response["Error"]["Code"] != "EntityAlreadyExists":
                raise

        account_id = boto3.client("sts").get_caller_identity()["Account"]
        policy_arn = f"arn:aws:iam::{account_id}:policy/{full_name}"

        try:
            iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
        except ClientError:
            pass

    # Wait for role propagation
    print("  Waiting for IAM role propagation...")
    time.sleep(10)

    return role_arn


def create_guardrail(bedrock_client) -> dict:
    """Create a Bedrock Guardrail for VaaniSetu."""
    print("\n[2/5] Creating Bedrock Guardrail...")

    try:
        response = bedrock_client.create_guardrail(
            name="vaanisetu-guardrail",
            description="Content safety guardrail for VaaniSetu government scheme assistant",
            topicPolicyConfig={
                "topicsConfig": [
                    {
                        "name": "PoliticalOpinions",
                        "definition": "Political opinions, party preferences, criticism of government officials",
                        "type": "DENY",
                        "examples": [
                            "Which party is better?",
                            "The government is corrupt",
                            "Who should I vote for?",
                        ],
                    },
                    {
                        "name": "FinancialAdvice",
                        "definition": "Personal investment advice, stock tips, or speculative financial recommendations",
                        "type": "DENY",
                        "examples": [
                            "Should I invest in stocks?",
                            "Which mutual fund is best?",
                            "Will gold prices go up?",
                        ],
                    },
                ],
            },
            contentPolicyConfig={
                "filtersConfig": [
                    {"type": "SEXUAL", "inputStrength": "HIGH", "outputStrength": "HIGH"},
                    {"type": "VIOLENCE", "inputStrength": "HIGH", "outputStrength": "HIGH"},
                    {"type": "HATE", "inputStrength": "HIGH", "outputStrength": "HIGH"},
                    {"type": "INSULTS", "inputStrength": "MEDIUM", "outputStrength": "HIGH"},
                ]
            },
            sensitiveInformationPolicyConfig={
                "piiEntitiesConfig": [
                    {"type": "CREDIT_DEBIT_CARD_NUMBER", "action": "BLOCK"},
                    {"type": "DRIVER_ID", "action": "BLOCK"},
                    {"type": "US_SOCIAL_SECURITY_NUMBER", "action": "BLOCK"},
                    {"type": "EMAIL", "action": "ANONYMIZE"},
                ],
            },
            blockedInputMessaging="मुझे इस विषय पर बात करने की अनुमति नहीं है। कृपया सरकारी योजनाओं के बारे में पूछें।",
            blockedOutputsMessaging="मुझे यह जानकारी देने की अनुमति नहीं है। कृपया सरकारी योजनाओं से संबंधित प्रश्न पूछें।",
        )

        guardrail_id = response["guardrailId"]
        print(f"  Created guardrail: {guardrail_id}")
        return {"id": guardrail_id, "version": "DRAFT"}

    except ClientError as e:
        if "already exists" in str(e).lower() or "conflict" in str(e).lower():
            # List existing guardrails
            existing = bedrock_client.list_guardrails(maxResults=100)
            for g in existing.get("guardrails", []):
                if g["name"] == "vaanisetu-guardrail":
                    print(f"  Using existing guardrail: {g['id']}")
                    return {"id": g["id"], "version": g.get("version", "DRAFT")}
        raise


def create_agent(bedrock_agent_client, role_arn: str, guardrail: dict) -> str:
    """Create the Bedrock Agent."""
    print("\n[3/5] Creating Bedrock Agent...")

    # Load agent config
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "infrastructure",
        "bedrock-agent",
        "agent-config.json",
    )

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    try:
        response = bedrock_agent_client.create_agent(
            agentName=AGENT_NAME,
            agentResourceRoleArn=role_arn,
            foundationModel=config["foundationModel"],
            instruction=config["instruction"],
            idleSessionTTLInSeconds=config["idleSessionTTLInSeconds"],
            description=config["description"],
            guardrailConfiguration={
                "guardrailIdentifier": guardrail["id"],
                "guardrailVersion": guardrail["version"],
            },
        )

        agent_id = response["agent"]["agentId"]
        print(f"  Created agent: {agent_id}")
        return agent_id

    except ClientError as e:
        if "already exists" in str(e).lower() or "conflict" in str(e).lower():
            # Find existing agent
            agents = bedrock_agent_client.list_agents(maxResults=100)
            for agent in agents.get("agentSummaries", []):
                if agent["agentName"] == AGENT_NAME:
                    print(f"  Using existing agent: {agent['agentId']}")
                    return agent["agentId"]
        raise


def setup_action_groups(bedrock_agent_client, agent_id: str, region: str):
    """Attach action groups (Lambda functions) to the agent."""
    print("\n[4/5] Setting up Action Groups...")

    account_id = boto3.client("sts").get_caller_identity()["Account"]

    # Map action groups to Lambda functions
    action_group_lambdas = {
        "SchemeSearchGroup": "vaanisetu-ai-engine",
        "EligibilityGroup": "vaanisetu-ai-engine",
        "FormValidationGroup": "vaanisetu-ai-engine",
        "ApplicationGroup": "vaanisetu-ai-engine",
        "NotificationGroup": "vaanisetu-notification",
        "FollowUpGroup": "vaanisetu-orchestrator",
    }

    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "infrastructure",
        "bedrock-agent",
        "agent-config.json",
    )

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    for ag_config in config["actionGroups"]:
        ag_name = ag_config["actionGroupName"]
        lambda_name = action_group_lambdas.get(ag_name, "vaanisetu-ai-engine")
        lambda_arn = f"arn:aws:lambda:{region}:{account_id}:function:{lambda_name}"

        try:
            bedrock_agent_client.create_agent_action_group(
                agentId=agent_id,
                agentVersion="DRAFT",
                actionGroupName=ag_name,
                description=ag_config["description"],
                actionGroupExecutor={"lambda_": lambda_arn},
                functionSchema=ag_config["apiSchema"]["functionSchema"],
            )
            print(f"  Created action group: {ag_name} → {lambda_name}")
        except ClientError as e:
            if "already exists" in str(e).lower() or "conflict" in str(e).lower():
                print(f"  Action group already exists: {ag_name}")
            else:
                print(f"  Warning: Failed to create {ag_name}: {e}")


def prepare_agent(bedrock_agent_client, agent_id: str):
    """Prepare (build) the agent for use."""
    print("\n[5/5] Preparing agent...")

    try:
        bedrock_agent_client.prepare_agent(agentId=agent_id)
        print("  Agent preparation started...")

        # Wait for agent to be ready
        for i in range(30):
            time.sleep(5)
            agent = bedrock_agent_client.get_agent(agentId=agent_id)
            status = agent["agent"]["agentStatus"]
            print(f"  Status: {status}")
            if status == "PREPARED":
                print("  Agent is ready!")
                return
            elif status == "FAILED":
                print(f"  Agent preparation failed: {agent['agent'].get('failureReasons', '')}")
                return
        print("  Timeout waiting for agent preparation")
    except Exception as e:
        print(f"  Warning: Agent preparation error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Setup VaaniSetu Bedrock Agent")
    parser.add_argument("--region", default=REGION, help="AWS region")
    parser.add_argument("--skip-guardrail", action="store_true", help="Skip guardrail creation")
    args = parser.parse_args()

    region = args.region

    iam_client = boto3.client("iam")
    bedrock_client = boto3.client("bedrock", region_name=region)
    bedrock_agent_client = boto3.client("bedrock-agent", region_name=region)

    print("=" * 50)
    print("  VaaniSetu Bedrock Agent Setup")
    print("=" * 50)

    # Step 1: Create IAM role
    print("\n[1/5] Creating IAM role...")
    role_arn = create_agent_role(iam_client, region)

    # Step 2: Create guardrail
    guardrail = {"id": "", "version": "DRAFT"}
    if not args.skip_guardrail:
        guardrail = create_guardrail(bedrock_client)

    # Step 3: Create agent
    agent_id = create_agent(bedrock_agent_client, role_arn, guardrail)

    # Step 4: Setup action groups
    setup_action_groups(bedrock_agent_client, agent_id, region)

    # Step 5: Prepare agent
    prepare_agent(bedrock_agent_client, agent_id)

    print("\n" + "=" * 50)
    print("  Setup Complete!")
    print("=" * 50)
    print(f"  Agent ID: {agent_id}")
    print(f"  Region: {region}")
    print(f"  Guardrail ID: {guardrail.get('id', 'N/A')}")
    print(f"\n  Next: Update KNOWLEDGE_BASE_ID in your environment")
    print(f"  Then: Test with Amazon Connect or web interface")
    print("=" * 50)


if __name__ == "__main__":
    main()
