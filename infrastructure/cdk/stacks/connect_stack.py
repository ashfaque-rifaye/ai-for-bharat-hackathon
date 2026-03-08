"""VaaniSetu Connect Stack — Amazon Connect telephony layer for voice IVR."""

from aws_cdk import (
    Stack,
    CfnOutput,
    Duration,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_connect as connect,
)
from constructs import Construct
import os
from pathlib import Path

BACKEND_DIR = str(Path(__file__).resolve().parents[3] / "backend")


class ConnectStack(Stack):
    """
    Amazon Connect integration for VaaniSetu telephony.

    Creates:
    - Connect instance (or references existing)
    - Contact flow for voice IVR
    - Lambda integration for Bedrock Agent
    - Lex bot integration for language detection
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        data_stack,
        ai_stack=None,
        api_stack=None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── Connect Instance ─────────────────────────────────────────
        # Note: Connect instances are best created via Console first,
        # then referenced here. CDK support for Connect is via L1 (Cfn).
        self.connect_instance = connect.CfnInstance(
            self,
            "ConnectInstance",
            identity_management_type="CONNECT_MANAGED",
            attributes=connect.CfnInstance.AttributesProperty(
                inbound_calls=True,
                outbound_calls=True,
                contactflow_logs=True,
                auto_resolve_best_voices=True,
            ),
            instance_alias="vaanisetu",
        )

        instance_arn = self.connect_instance.attr_arn

        # ── Connect-Bedrock Integration Lambda ───────────────────────
        # This Lambda bridges Connect contact flows with our AI Engine
        self.connect_handler_fn = _lambda.Function(
            self,
            "ConnectHandlerFn",
            function_name="vaanisetu-connect-handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=_lambda.Code.from_asset(
                os.path.join(BACKEND_DIR, "lambdas", "connect_handler")
            ),
            timeout=Duration.seconds(30),
            memory_size=512,
            log_retention=logs.RetentionDays.ONE_WEEK,
            environment={
                "SESSIONS_TABLE": data_stack.sessions_table.table_name,
                "SCHEMES_TABLE": data_stack.schemes_table.table_name,
                "APPLICATIONS_TABLE": data_stack.applications_table.table_name,
                "AUDIO_BUCKET": data_stack.audio_bucket.bucket_name,
                "KNOWLEDGE_BASE_ID": ai_stack.knowledge_base_id if ai_stack else "",
                "AWS_REGION_NAME": "us-east-1",
                "BEDROCK_MODEL_ID": "anthropic.claude-3-haiku-20240307-v1:0",
                "CONNECT_INSTANCE_ARN": instance_arn,
            },
        )

        # DynamoDB access
        self.connect_handler_fn.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:Query",
                ],
                resources=[
                    data_stack.sessions_table.table_arn,
                    f"{data_stack.sessions_table.table_arn}/index/*",
                    data_stack.schemes_table.table_arn,
                    f"{data_stack.schemes_table.table_arn}/index/*",
                    data_stack.applications_table.table_arn,
                ],
            )
        )

        # Bedrock access
        self.connect_handler_fn.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:Converse",
                    "bedrock:Retrieve",
                    "bedrock:RetrieveAndGenerate",
                    "bedrock:InvokeAgent",
                ],
                resources=["*"],
            )
        )

        # Polly + Transcribe + Translate
        self.connect_handler_fn.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "polly:SynthesizeSpeech",
                    "transcribe:StartTranscriptionJob",
                    "transcribe:GetTranscriptionJob",
                    "translate:TranslateText",
                ],
                resources=["*"],
            )
        )

        # S3 access for audio
        self.connect_handler_fn.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
                resources=[
                    data_stack.audio_bucket.bucket_arn,
                    f"{data_stack.audio_bucket.bucket_arn}/*",
                ],
            )
        )

        # SNS for SMS notifications
        self.connect_handler_fn.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["sns:Publish"],
                resources=["*"],
            )
        )

        # Connect permissions for the Lambda
        self.connect_handler_fn.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "connect:UpdateContactAttributes",
                    "connect:GetContactAttributes",
                    "connect:StartOutboundVoiceContact",
                ],
                resources=[f"{instance_arn}/*"],
            )
        )

        # ── Post-Call Analytics Lambda ───────────────────────────────
        self.post_call_fn = _lambda.Function(
            self,
            "PostCallFn",
            function_name="vaanisetu-post-call",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=_lambda.Code.from_asset(
                os.path.join(BACKEND_DIR, "lambdas", "post_call")
            ),
            timeout=Duration.seconds(60),
            memory_size=256,
            log_retention=logs.RetentionDays.ONE_WEEK,
            environment={
                "SESSIONS_TABLE": data_stack.sessions_table.table_name,
                "APPLICATIONS_TABLE": data_stack.applications_table.table_name,
                "AWS_REGION_NAME": "us-east-1",
            },
        )

        self.post_call_fn.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["dynamodb:GetItem", "dynamodb:UpdateItem", "dynamodb:Query"],
                resources=[
                    data_stack.sessions_table.table_arn,
                    data_stack.applications_table.table_arn,
                ],
            )
        )

        # SNS for follow-up SMS
        self.post_call_fn.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["sns:Publish"],
                resources=["*"],
            )
        )

        # ── Lambda Permission for Connect ────────────────────────────
        # Allow Connect to invoke our Lambda
        _lambda.CfnPermission(
            self,
            "ConnectInvokeLambdaPermission",
            function_name=self.connect_handler_fn.function_name,
            action="lambda:InvokeFunction",
            principal="connect.amazonaws.com",
            source_arn=instance_arn,
        )

        # ── Associate Lambda with Connect Instance ───────────────────
        connect.CfnIntegrationAssociation(
            self,
            "LambdaAssociation",
            instance_id=instance_arn,
            integration_arn=self.connect_handler_fn.function_arn,
            integration_type="LAMBDA_FUNCTION",
        )

        # ── Contact Flow ─────────────────────────────────────────────
        # The contact flow JSON is generated for multi-language IVR
        contact_flow_content = self._generate_contact_flow()

        self.contact_flow = connect.CfnContactFlow(
            self,
            "VaaniSetuContactFlow",
            instance_arn=instance_arn,
            name="VaaniSetu-MainFlow",
            type="CONTACT_FLOW",
            description="VaaniSetu main IVR flow with language selection and AI conversation",
            content=contact_flow_content,
        )

        # ── Hours of Operation ───────────────────────────────────────
        self.hours = connect.CfnHoursOfOperation(
            self,
            "Hours247",
            instance_arn=instance_arn,
            name="VaaniSetu-24x7",
            time_zone="Asia/Kolkata",
            config=[
                connect.CfnHoursOfOperation.HoursOfOperationConfigProperty(
                    day="MONDAY",
                    end_time=connect.CfnHoursOfOperation.HoursOfOperationTimeSliceProperty(hours=23, minutes=59),
                    start_time=connect.CfnHoursOfOperation.HoursOfOperationTimeSliceProperty(hours=0, minutes=0),
                ),
                connect.CfnHoursOfOperation.HoursOfOperationConfigProperty(
                    day="TUESDAY",
                    end_time=connect.CfnHoursOfOperation.HoursOfOperationTimeSliceProperty(hours=23, minutes=59),
                    start_time=connect.CfnHoursOfOperation.HoursOfOperationTimeSliceProperty(hours=0, minutes=0),
                ),
                connect.CfnHoursOfOperation.HoursOfOperationConfigProperty(
                    day="WEDNESDAY",
                    end_time=connect.CfnHoursOfOperation.HoursOfOperationTimeSliceProperty(hours=23, minutes=59),
                    start_time=connect.CfnHoursOfOperation.HoursOfOperationTimeSliceProperty(hours=0, minutes=0),
                ),
                connect.CfnHoursOfOperation.HoursOfOperationConfigProperty(
                    day="THURSDAY",
                    end_time=connect.CfnHoursOfOperation.HoursOfOperationTimeSliceProperty(hours=23, minutes=59),
                    start_time=connect.CfnHoursOfOperation.HoursOfOperationTimeSliceProperty(hours=0, minutes=0),
                ),
                connect.CfnHoursOfOperation.HoursOfOperationConfigProperty(
                    day="FRIDAY",
                    end_time=connect.CfnHoursOfOperation.HoursOfOperationTimeSliceProperty(hours=23, minutes=59),
                    start_time=connect.CfnHoursOfOperation.HoursOfOperationTimeSliceProperty(hours=0, minutes=0),
                ),
                connect.CfnHoursOfOperation.HoursOfOperationConfigProperty(
                    day="SATURDAY",
                    end_time=connect.CfnHoursOfOperation.HoursOfOperationTimeSliceProperty(hours=23, minutes=59),
                    start_time=connect.CfnHoursOfOperation.HoursOfOperationTimeSliceProperty(hours=0, minutes=0),
                ),
                connect.CfnHoursOfOperation.HoursOfOperationConfigProperty(
                    day="SUNDAY",
                    end_time=connect.CfnHoursOfOperation.HoursOfOperationTimeSliceProperty(hours=23, minutes=59),
                    start_time=connect.CfnHoursOfOperation.HoursOfOperationTimeSliceProperty(hours=0, minutes=0),
                ),
            ],
        )

        # ── Outputs ──────────────────────────────────────────────────
        CfnOutput(self, "ConnectInstanceArn", value=instance_arn)
        CfnOutput(self, "ConnectInstanceAlias", value="vaanisetu")
        CfnOutput(self, "ConnectHandlerFnName", value=self.connect_handler_fn.function_name)
        CfnOutput(self, "PostCallFnName", value=self.post_call_fn.function_name)
        CfnOutput(self, "ContactFlowId", value=self.contact_flow.attr_contact_flow_arn)

    def _generate_contact_flow(self) -> str:
        """Generate Amazon Connect contact flow JSON for VaaniSetu IVR."""
        import json

        flow = {
            "Version": "2019-10-30",
            "StartAction": "welcome-prompt",
            "Actions": [
                # 1. Welcome prompt
                {
                    "Identifier": "welcome-prompt",
                    "Type": "MessageParticipant",
                    "Parameters": {
                        "Text": "नमस्ते! वाणी सेतु में आपका स्वागत है। सरकारी योजनाओं की जानकारी के लिए हम यहाँ हैं।\n\nWelcome to VaaniSetu! We help you find and apply for government schemes."
                    },
                    "Transitions": {
                        "NextAction": "language-selection",
                        "Errors": [{"NextAction": "language-selection", "ErrorType": "NoMatchingError"}],
                    },
                },
                # 2. Language selection via DTMF
                {
                    "Identifier": "language-selection",
                    "Type": "GetParticipantInput",
                    "Parameters": {
                        "Text": "भाषा चुनने के लिए:\nहिंदी के लिए 1 दबाएं\nFor English press 2\nதமிழுக்கு 3 அழுத்தவும்",
                        "InputTimeLimitSeconds": "10",
                        "StoreInput": "True",
                        "DTMFConfiguration": {
                            "InputTerminationSequence": "#",
                            "MaxDigits": 1,
                        },
                    },
                    "Transitions": {
                        "NextAction": "set-language",
                        "Conditions": [
                            {"NextAction": "set-hindi", "Condition": {"Operator": "Equals", "Operands": ["1"]}},
                            {"NextAction": "set-english", "Condition": {"Operator": "Equals", "Operands": ["2"]}},
                            {"NextAction": "set-tamil", "Condition": {"Operator": "Equals", "Operands": ["3"]}},
                        ],
                        "Errors": [{"NextAction": "set-hindi", "ErrorType": "NoMatchingError"}],
                    },
                },
                # 3a. Set Hindi
                {
                    "Identifier": "set-hindi",
                    "Type": "UpdateContactAttributes",
                    "Parameters": {
                        "Attributes": {"language": "hi-IN", "languageName": "Hindi"}
                    },
                    "Transitions": {"NextAction": "set-voice-hindi"},
                },
                # 3b. Set English
                {
                    "Identifier": "set-english",
                    "Type": "UpdateContactAttributes",
                    "Parameters": {
                        "Attributes": {"language": "en-IN", "languageName": "English"}
                    },
                    "Transitions": {"NextAction": "set-voice-english"},
                },
                # 3c. Set Tamil
                {
                    "Identifier": "set-tamil",
                    "Type": "UpdateContactAttributes",
                    "Parameters": {
                        "Attributes": {"language": "ta-IN", "languageName": "Tamil"}
                    },
                    "Transitions": {"NextAction": "set-voice-hindi"},  # Tamil uses Hindi voice
                },
                # 4a. Set Hindi voice (Kajal)
                {
                    "Identifier": "set-voice-hindi",
                    "Type": "UpdateContactTextToSpeechVoice",
                    "Parameters": {
                        "TextToSpeechVoice": "Kajal",
                        "TextToSpeechEngine": "Neural",
                    },
                    "Transitions": {"NextAction": "invoke-lambda"},
                },
                # 4b. Set English voice
                {
                    "Identifier": "set-voice-english",
                    "Type": "UpdateContactTextToSpeechVoice",
                    "Parameters": {
                        "TextToSpeechVoice": "Kajal",
                        "TextToSpeechEngine": "Neural",
                    },
                    "Transitions": {"NextAction": "invoke-lambda"},
                },
                # 5. Invoke Lambda to start conversation
                {
                    "Identifier": "invoke-lambda",
                    "Type": "InvokeLambdaFunction",
                    "Parameters": {
                        "LambdaFunctionARN": "$.ConnectHandlerFnArn",
                        "InvocationTimeLimitSeconds": "8",
                    },
                    "Transitions": {
                        "NextAction": "speak-response",
                        "Errors": [{"NextAction": "error-handler", "ErrorType": "NoMatchingError"}],
                    },
                },
                # 6. Speak AI response
                {
                    "Identifier": "speak-response",
                    "Type": "MessageParticipant",
                    "Parameters": {
                        "Text": "$.External.aiResponse",
                        "SSML": "$.External.ssmlResponse",
                    },
                    "Transitions": {"NextAction": "get-user-input"},
                },
                # 7. Get user voice input (loop)
                {
                    "Identifier": "get-user-input",
                    "Type": "GetParticipantInput",
                    "Parameters": {
                        "Text": " ",
                        "InputTimeLimitSeconds": "15",
                        "DTMFConfiguration": {
                            "InputTerminationSequence": "#",
                            "MaxDigits": 1,
                        },
                    },
                    "Transitions": {
                        "NextAction": "invoke-lambda",
                        "Conditions": [
                            {"NextAction": "end-call", "Condition": {"Operator": "Equals", "Operands": ["0"]}},
                        ],
                        "Errors": [
                            {"NextAction": "silence-timeout", "ErrorType": "InputTimeLimitExceeded"},
                            {"NextAction": "invoke-lambda", "ErrorType": "NoMatchingError"},
                        ],
                    },
                },
                # 8. Silence timeout
                {
                    "Identifier": "silence-timeout",
                    "Type": "MessageParticipant",
                    "Parameters": {
                        "Text": "क्या आप वहां हैं? कुछ और पूछना है तो बोलिए, या फोन काटने के लिए 0 दबाएं।"
                    },
                    "Transitions": {"NextAction": "get-user-input"},
                },
                # 9. End call
                {
                    "Identifier": "end-call",
                    "Type": "MessageParticipant",
                    "Parameters": {
                        "Text": "धन्यवाद! वाणी सेतु पर कॉल करने के लिए शुक्रिया। जय हिंद!\n\nThank you for calling VaaniSetu. Jai Hind!"
                    },
                    "Transitions": {"NextAction": "disconnect"},
                },
                # 10. Disconnect
                {
                    "Identifier": "disconnect",
                    "Type": "DisconnectParticipant",
                    "Parameters": {},
                    "Transitions": {},
                },
                # 11. Error handler
                {
                    "Identifier": "error-handler",
                    "Type": "MessageParticipant",
                    "Parameters": {
                        "Text": "माफ़ कीजिये, एक तकनीकी समस्या हुई है। कृपया कुछ देर बाद दोबारा कॉल करें।\n\nSorry, we encountered a technical issue. Please call back later."
                    },
                    "Transitions": {"NextAction": "disconnect"},
                },
                # Default language fallback
                {
                    "Identifier": "set-language",
                    "Type": "UpdateContactAttributes",
                    "Parameters": {
                        "Attributes": {"language": "hi-IN", "languageName": "Hindi"}
                    },
                    "Transitions": {"NextAction": "set-voice-hindi"},
                },
            ],
        }

        return json.dumps(flow)
