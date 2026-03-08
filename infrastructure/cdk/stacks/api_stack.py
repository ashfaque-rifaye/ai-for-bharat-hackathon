"""VaaniSetu API Stack — REST API, WebSocket API, and Lambda functions."""

import os
from pathlib import Path

from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_iam as iam,
    aws_logs as logs,
)
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import aws_apigatewayv2_integrations as apigwv2_integrations
from constructs import Construct

BACKEND_DIR = str(Path(__file__).resolve().parents[3] / "backend")


class ApiStack(Stack):
    """Creates REST API, WebSocket API, and Lambda functions."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        data_stack,
        ai_stack=None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── Shared Lambda Layer ──────────────────────────────────────
        shared_layer = _lambda.LayerVersion(
            self,
            "SharedLayer",
            code=_lambda.Code.from_asset(os.path.join(BACKEND_DIR, "shared")),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
            description="VaaniSetu shared utilities, models, and constants",
        )

        # ── Common Lambda environment variables ──────────────────────
        common_env = {
            "SESSIONS_TABLE": data_stack.sessions_table.table_name,
            "SCHEMES_TABLE": data_stack.schemes_table.table_name,
            "APPLICATIONS_TABLE": data_stack.applications_table.table_name,
            "CONNECTIONS_TABLE": data_stack.connections_table.table_name,
            "SCHEME_DOCS_BUCKET": data_stack.scheme_docs_bucket.bucket_name,
            "AUDIO_BUCKET": data_stack.audio_bucket.bucket_name,
            "AWS_REGION_NAME": "us-east-1",
            "POWERTOOLS_SERVICE_NAME": "vaanisetu",
            "BEDROCK_MODEL_ID": "anthropic.claude-3-haiku-20240307-v1:0",
            "BEDROCK_FALLBACK_MODEL_ID": "amazon.nova-pro-v1:0",
            "GUARDRAIL_ID": "46tqyral1aho",
            "GUARDRAIL_VERSION": "1",
        }

        if ai_stack and hasattr(ai_stack, "knowledge_base_id"):
            common_env["KNOWLEDGE_BASE_ID"] = ai_stack.knowledge_base_id

        # ── IAM Policies ─────────────────────────────────────────────
        dynamodb_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Query",
                "dynamodb:Scan",
                "dynamodb:BatchWriteItem",
            ],
            resources=[
                data_stack.sessions_table.table_arn,
                f"{data_stack.sessions_table.table_arn}/index/*",
                data_stack.schemes_table.table_arn,
                f"{data_stack.schemes_table.table_arn}/index/*",
                data_stack.applications_table.table_arn,
                f"{data_stack.applications_table.table_arn}/index/*",
                data_stack.connections_table.table_arn,
            ],
        )

        s3_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"],
            resources=[
                data_stack.scheme_docs_bucket.bucket_arn,
                f"{data_stack.scheme_docs_bucket.bucket_arn}/*",
                data_stack.audio_bucket.bucket_arn,
                f"{data_stack.audio_bucket.bucket_arn}/*",
            ],
        )

        bedrock_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "bedrock:InvokeModel",
                "bedrock:Converse",
                "bedrock:Retrieve",
                "bedrock:RetrieveAndGenerate",
                "bedrock:ApplyGuardrail",
            ],
            resources=["*"],
        )

        transcribe_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "transcribe:StartTranscriptionJob",
                "transcribe:GetTranscriptionJob",
                "transcribe:DeleteTranscriptionJob",
            ],
            resources=["*"],
        )

        polly_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["polly:SynthesizeSpeech"],
            resources=["*"],
        )

        translate_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["translate:TranslateText"],
            resources=["*"],
        )

        sns_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["sns:Publish"],
            resources=["*"],
        )

        comprehend_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["comprehend:DetectSentiment", "comprehend:DetectDominantLanguage"],
            resources=["*"],
        )

        eventbridge_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["events:PutEvents"],
            resources=["*"],
        )

        # ── AI Engine Lambda ─────────────────────────────────────────
        self.ai_engine_fn = _lambda.Function(
            self,
            "AIEngineFn",
            function_name="vaanisetu-ai-engine",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=_lambda.Code.from_asset(os.path.join(BACKEND_DIR, "lambdas", "ai_engine")),
            layers=[shared_layer],
            environment={**common_env},
            timeout=Duration.seconds(60),
            memory_size=512,
            log_retention=logs.RetentionDays.ONE_WEEK,
        )
        self.ai_engine_fn.add_to_role_policy(dynamodb_policy)
        self.ai_engine_fn.add_to_role_policy(bedrock_policy)
        self.ai_engine_fn.add_to_role_policy(s3_policy)
        self.ai_engine_fn.add_to_role_policy(sns_policy)

        # ── Notification Lambda ──────────────────────────────────────
        self.notification_fn = _lambda.Function(
            self,
            "NotificationFn",
            function_name="vaanisetu-notification",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=_lambda.Code.from_asset(os.path.join(BACKEND_DIR, "lambdas", "notification")),
            layers=[shared_layer],
            environment={**common_env},
            timeout=Duration.seconds(30),
            memory_size=256,
            log_retention=logs.RetentionDays.ONE_WEEK,
        )
        self.notification_fn.add_to_role_policy(dynamodb_policy)
        self.notification_fn.add_to_role_policy(sns_policy)

        # ── Orchestrator Lambda ──────────────────────────────────────
        orchestrator_env = {
            **common_env,
            "AI_ENGINE_FUNCTION": self.ai_engine_fn.function_name,
            "NOTIFICATION_FUNCTION": self.notification_fn.function_name,
        }

        self.orchestrator_fn = _lambda.Function(
            self,
            "OrchestratorFn",
            function_name="vaanisetu-orchestrator",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=_lambda.Code.from_asset(os.path.join(BACKEND_DIR, "lambdas", "orchestrator")),
            layers=[shared_layer],
            environment=orchestrator_env,
            timeout=Duration.seconds(60),
            memory_size=256,
            log_retention=logs.RetentionDays.ONE_WEEK,
        )
        self.orchestrator_fn.add_to_role_policy(dynamodb_policy)
        self.orchestrator_fn.add_to_role_policy(s3_policy)
        self.orchestrator_fn.add_to_role_policy(polly_policy)
        self.orchestrator_fn.add_to_role_policy(transcribe_policy)
        self.orchestrator_fn.add_to_role_policy(translate_policy)
        self.orchestrator_fn.add_to_role_policy(comprehend_policy)
        self.orchestrator_fn.add_to_role_policy(eventbridge_policy)

        # Grant orchestrator permission to invoke AI Engine & Notification
        self.ai_engine_fn.grant_invoke(self.orchestrator_fn)
        self.notification_fn.grant_invoke(self.orchestrator_fn)

        # ── WhatsApp Webhook Lambda ──────────────────────────────────
        self.whatsapp_fn = _lambda.Function(
            self,
            "WhatsAppFn",
            function_name="vaanisetu-whatsapp",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=_lambda.Code.from_asset(os.path.join(BACKEND_DIR, "lambdas", "whatsapp")),
            layers=[shared_layer],
            environment={
                **common_env,
                "AI_ENGINE_FUNCTION": self.ai_engine_fn.function_name,
                "TWILIO_ACCOUNT_SID": os.environ.get("TWILIO_ACCOUNT_SID", ""),
                "TWILIO_AUTH_TOKEN": os.environ.get("TWILIO_AUTH_TOKEN", ""),
            },
            timeout=Duration.seconds(60),
            memory_size=256,
            log_retention=logs.RetentionDays.ONE_WEEK,
        )
        self.whatsapp_fn.add_to_role_policy(dynamodb_policy)
        self.ai_engine_fn.grant_invoke(self.whatsapp_fn)

        # ── REST API Gateway ─────────────────────────────────────────
        self.rest_api = apigw.RestApi(
            self,
            "RestAPI",
            rest_api_name="VaaniSetu-API",
            description="VaaniSetu REST API for scheme discovery and application",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization", "X-Session-Id"],
            ),
            deploy_options=apigw.StageOptions(stage_name="prod"),
        )

        # Lambda integration for REST
        orchestrator_integration = apigw.LambdaIntegration(
            self.orchestrator_fn,
            proxy=True,
        )

        # REST routes
        # /sessions
        sessions = self.rest_api.root.add_resource("sessions")
        sessions.add_method("POST", orchestrator_integration)  # Create session

        session = sessions.add_resource("{sessionId}")
        session.add_method("GET", orchestrator_integration)  # Get session

        session_message = session.add_resource("message")
        session_message.add_method("POST", orchestrator_integration)  # Send message

        # /schemes
        schemes = self.rest_api.root.add_resource("schemes")
        schemes.add_method("GET", orchestrator_integration)  # List schemes

        scheme = schemes.add_resource("{schemeId}")
        scheme.add_method("GET", orchestrator_integration)  # Get scheme detail

        scheme_search = schemes.add_resource("search")
        scheme_search.add_method("POST", orchestrator_integration)  # Search schemes

        # /applications
        applications = self.rest_api.root.add_resource("applications")
        application = applications.add_resource("{applicationId}")
        application.add_method("GET", orchestrator_integration)  # Get application

        # /synthesize — Text-to-Speech via Amazon Polly
        synthesize = self.rest_api.root.add_resource("synthesize")
        synthesize.add_method("POST", orchestrator_integration)

        # /transcribe — Speech-to-Text via Amazon Transcribe
        transcribe = self.rest_api.root.add_resource("transcribe")
        transcribe.add_method("POST", orchestrator_integration)

        # /benefit-summary — Cross-scheme benefit stacking analysis
        benefit_summary = self.rest_api.root.add_resource("benefit-summary")
        benefit_summary.add_method("POST", orchestrator_integration)

        # /analytics — Lightweight usage stats
        analytics = self.rest_api.root.add_resource("analytics")
        analytics.add_method("GET", orchestrator_integration)

        # /generate-pdf — Generate PDF reports (benefit summary / application)
        generate_pdf = self.rest_api.root.add_resource("generate-pdf")
        generate_pdf.add_method("POST", orchestrator_integration)

        # /whatsapp — Twilio WhatsApp webhook
        whatsapp_resource = self.rest_api.root.add_resource("whatsapp")
        whatsapp_resource.add_method("POST", apigw.LambdaIntegration(self.whatsapp_fn, proxy=True))
        whatsapp_resource.add_method("GET", apigw.LambdaIntegration(self.whatsapp_fn, proxy=True))

        # /health
        health = self.rest_api.root.add_resource("health")
        health.add_method("GET", orchestrator_integration)

        # ── WebSocket API Gateway ────────────────────────────────────
        # Voice Processor Lambda
        self.voice_processor_fn = _lambda.Function(
            self,
            "VoiceProcessorFn",
            function_name="vaanisetu-voice-processor",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=_lambda.Code.from_asset(os.path.join(BACKEND_DIR, "lambdas", "voice_processor")),
            layers=[shared_layer],
            environment={
                **common_env,
                "AI_ENGINE_FUNCTION": self.ai_engine_fn.function_name,
            },
            timeout=Duration.seconds(60),
            memory_size=512,
            log_retention=logs.RetentionDays.ONE_WEEK,
        )
        self.voice_processor_fn.add_to_role_policy(dynamodb_policy)
        self.voice_processor_fn.add_to_role_policy(s3_policy)
        self.voice_processor_fn.add_to_role_policy(transcribe_policy)
        self.voice_processor_fn.add_to_role_policy(polly_policy)
        self.voice_processor_fn.add_to_role_policy(translate_policy)
        self.ai_engine_fn.grant_invoke(self.voice_processor_fn)

        # WebSocket API
        self.ws_api = apigwv2.WebSocketApi(
            self,
            "WebSocketAPI",
            api_name="VaaniSetu-WS",
            description="VaaniSetu WebSocket API for real-time voice/chat",
            connect_route_options=apigwv2.WebSocketRouteOptions(
                integration=apigwv2_integrations.WebSocketLambdaIntegration(
                    "ConnectIntegration", self.voice_processor_fn
                ),
            ),
            disconnect_route_options=apigwv2.WebSocketRouteOptions(
                integration=apigwv2_integrations.WebSocketLambdaIntegration(
                    "DisconnectIntegration", self.voice_processor_fn
                ),
            ),
            default_route_options=apigwv2.WebSocketRouteOptions(
                integration=apigwv2_integrations.WebSocketLambdaIntegration(
                    "DefaultIntegration", self.voice_processor_fn
                ),
            ),
        )

        ws_stage = apigwv2.WebSocketStage(
            self,
            "WebSocketStage",
            web_socket_api=self.ws_api,
            stage_name="prod",
            auto_deploy=True,
        )

        # Grant voice processor permission to post back to WS clients
        ws_manage_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["execute-api:ManageConnections"],
            resources=[
                f"arn:aws:execute-api:{self.region}:{self.account}:{self.ws_api.api_id}/prod/*",
            ],
        )
        self.voice_processor_fn.add_to_role_policy(ws_manage_policy)

        # Set WebSocket endpoint env var on voice processor
        self.voice_processor_fn.add_environment(
            "WEBSOCKET_API_ENDPOINT",
            f"https://{self.ws_api.api_id}.execute-api.{self.region}.amazonaws.com/prod",
        )

        # ── Outputs ──────────────────────────────────────────────────
        CfnOutput(self, "RestAPIUrl", value=self.rest_api.url)
        CfnOutput(self, "WebSocketUrl", value=ws_stage.url)
        CfnOutput(
            self,
            "WebSocketCallbackUrl",
            value=f"https://{self.ws_api.api_id}.execute-api.{self.region}.amazonaws.com/prod",
        )
        CfnOutput(self, "OrchestratorFnName", value=self.orchestrator_fn.function_name)
        CfnOutput(self, "AIEngineFnName", value=self.ai_engine_fn.function_name)
        CfnOutput(self, "VoiceProcessorFnName", value=self.voice_processor_fn.function_name)
        CfnOutput(self, "NotificationFnName", value=self.notification_fn.function_name)
        CfnOutput(self, "WhatsAppFnName", value=self.whatsapp_fn.function_name)
        CfnOutput(
            self,
            "WhatsAppWebhookUrl",
            value=f"{self.rest_api.url}whatsapp",
            description="Set this as Twilio WhatsApp webhook URL",
        )
