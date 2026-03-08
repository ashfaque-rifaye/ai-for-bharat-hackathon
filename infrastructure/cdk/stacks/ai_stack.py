"""VaaniSetu AI Stack — Bedrock IAM roles and configuration.

Simplified: skips OpenSearch Serverless KB creation (too expensive for hackathon).
AI engine uses DynamoDB scheme data directly with Claude for responses.
"""

from aws_cdk import (
    Stack,
    CfnOutput,
    aws_iam as iam,
)
from constructs import Construct


class AIStack(Stack):
    """
    Creates Bedrock-related IAM roles and configuration.

    The AI engine Lambda queries DynamoDB for scheme data and uses
    Bedrock Claude directly — no Knowledge Base needed for the hackathon.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        data_stack,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Placeholder — KB not used; AI engine reads DynamoDB directly
        self.knowledge_base_id = "none"

        # ── Bedrock KB IAM Role (kept for future KB integration) ─────
        self.kb_role = iam.Role(
            self,
            "BedrockKBRole",
            role_name="vaanisetu-bedrock-kb-role",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description="Role assumed by Bedrock Knowledge Base to access S3 data source",
        )

        # Allow Bedrock to read scheme documents from S3
        self.kb_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=[
                    data_stack.scheme_docs_bucket.bucket_arn,
                    f"{data_stack.scheme_docs_bucket.bucket_arn}/*",
                ],
            )
        )

        # Allow Bedrock to use embedding model
        self.kb_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:InvokeModel"],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/amazon.titan-embed-text-v2:0",
                    f"arn:aws:bedrock:{self.region}::foundation-model/amazon.titan-embed-text-v1",
                ],
            )
        )

        # ── Outputs ──────────────────────────────────────────────────
        CfnOutput(self, "KBRoleArn", value=self.kb_role.role_arn)
        CfnOutput(self, "KnowledgeBaseId", value=self.knowledge_base_id)
        CfnOutput(
            self,
            "SchemeDocsBucketRef",
            value=data_stack.scheme_docs_bucket.bucket_name,
        )
