"""VaaniSetu AWS Clients — Shared boto3 client wrappers."""

import os
import boto3
from functools import lru_cache

try:
    from .constants import AWS_REGION
except ImportError:
    from constants import AWS_REGION


def _get_region():
    return os.environ.get("AWS_REGION", AWS_REGION)


@lru_cache(maxsize=1)
def get_dynamodb_resource():
    """Get DynamoDB resource (cached)."""
    return boto3.resource("dynamodb", region_name=_get_region())


@lru_cache(maxsize=1)
def get_dynamodb_client():
    """Get DynamoDB client (cached)."""
    return boto3.client("dynamodb", region_name=_get_region())


@lru_cache(maxsize=1)
def get_bedrock_runtime_client():
    """Get Bedrock Runtime client for model invocation."""
    return boto3.client("bedrock-runtime", region_name=_get_region())


@lru_cache(maxsize=1)
def get_bedrock_agent_runtime_client():
    """Get Bedrock Agent Runtime client."""
    return boto3.client("bedrock-agent-runtime", region_name=_get_region())


@lru_cache(maxsize=1)
def get_transcribe_client():
    """Get Amazon Transcribe client."""
    return boto3.client("transcribe", region_name=_get_region())


@lru_cache(maxsize=1)
def get_polly_client():
    """Get Amazon Polly client."""
    return boto3.client("polly", region_name=_get_region())


@lru_cache(maxsize=1)
def get_translate_client():
    """Get Amazon Translate client."""
    return boto3.client("translate", region_name=_get_region())


@lru_cache(maxsize=1)
def get_sns_client():
    """Get Amazon SNS client."""
    return boto3.client("sns", region_name=_get_region())


@lru_cache(maxsize=1)
def get_s3_client():
    """Get Amazon S3 client."""
    return boto3.client("s3", region_name=_get_region())


@lru_cache(maxsize=1)
def get_apigateway_management_client():
    """Get API Gateway Management API client for WebSocket push."""
    endpoint = os.environ.get("WEBSOCKET_API_ENDPOINT", "")
    if endpoint:
        return boto3.client(
            "apigatewaymanagementapi",
            endpoint_url=endpoint,
            region_name=_get_region(),
        )
    return None


def get_sessions_table():
    """Get DynamoDB sessions table resource."""
    table_name = os.environ.get("SESSIONS_TABLE", "vaanisetu-sessions")
    return get_dynamodb_resource().Table(table_name)


def get_schemes_table():
    """Get DynamoDB schemes table resource."""
    table_name = os.environ.get("SCHEMES_TABLE", "vaanisetu-schemes")
    return get_dynamodb_resource().Table(table_name)


def get_applications_table():
    """Get DynamoDB applications table resource."""
    table_name = os.environ.get("APPLICATIONS_TABLE", "vaanisetu-applications")
    return get_dynamodb_resource().Table(table_name)


def get_connections_table():
    """Get DynamoDB connections table resource."""
    table_name = os.environ.get("CONNECTIONS_TABLE", "vaanisetu-connections")
    return get_dynamodb_resource().Table(table_name)
