"""VaaniSetu Data Stack — DynamoDB tables and S3 buckets."""

from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    CfnOutput,
)
from constructs import Construct


class DataStack(Stack):
    """Creates DynamoDB tables and S3 buckets for VaaniSetu."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── DynamoDB: Sessions Table ─────────────────────────────────
        self.sessions_table = dynamodb.Table(
            self,
            "SessionsTable",
            table_name="vaanisetu-sessions",
            partition_key=dynamodb.Attribute(
                name="sessionId", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl",
        )

        # GSI: lookup sessions by phone number
        self.sessions_table.add_global_secondary_index(
            index_name="phone-index",
            partition_key=dynamodb.Attribute(
                name="phoneNumber", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="createdAt", type=dynamodb.AttributeType.STRING
            ),
        )

        # ── DynamoDB: Schemes Table ──────────────────────────────────
        self.schemes_table = dynamodb.Table(
            self,
            "SchemesTable",
            table_name="vaanisetu-schemes",
            partition_key=dynamodb.Attribute(
                name="schemeId", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # GSI: query schemes by category
        self.schemes_table.add_global_secondary_index(
            index_name="category-index",
            partition_key=dynamodb.Attribute(
                name="category", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="schemeId", type=dynamodb.AttributeType.STRING
            ),
        )

        # ── DynamoDB: Applications Table ─────────────────────────────
        self.applications_table = dynamodb.Table(
            self,
            "ApplicationsTable",
            table_name="vaanisetu-applications",
            partition_key=dynamodb.Attribute(
                name="applicationId", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # GSI: lookup applications by session
        self.applications_table.add_global_secondary_index(
            index_name="session-index",
            partition_key=dynamodb.Attribute(
                name="sessionId", type=dynamodb.AttributeType.STRING
            ),
        )

        # ── DynamoDB: Connections Table (WebSocket) ──────────────────
        self.connections_table = dynamodb.Table(
            self,
            "ConnectionsTable",
            table_name="vaanisetu-connections",
            partition_key=dynamodb.Attribute(
                name="connectionId", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl",
        )

        # ── S3: Scheme Documents Bucket ──────────────────────────────
        self.scheme_docs_bucket = s3.Bucket(
            self,
            "SchemeDocsBucket",
            bucket_name=None,  # Auto-generated unique name
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=False,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        # ── S3: Audio / Temporary Storage Bucket ─────────────────────
        self.audio_bucket = s3.Bucket(
            self,
            "AudioBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            lifecycle_rules=[
                s3.LifecycleRule(
                    expiration=Duration.days(1),  # Auto-delete audio after 1 day
                )
            ],
        )

        # ── Outputs ──────────────────────────────────────────────────
        CfnOutput(self, "SessionsTableName", value=self.sessions_table.table_name)
        CfnOutput(self, "SchemesTableName", value=self.schemes_table.table_name)
        CfnOutput(self, "ApplicationsTableName", value=self.applications_table.table_name)
        CfnOutput(self, "ConnectionsTableName", value=self.connections_table.table_name)
        CfnOutput(self, "SchemeDocsBucketName", value=self.scheme_docs_bucket.bucket_name)
        CfnOutput(self, "AudioBucketName", value=self.audio_bucket.bucket_name)
