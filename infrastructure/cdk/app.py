#!/usr/bin/env python3
"""VaaniSetu CDK Application - AWS Infrastructure as Code."""

import aws_cdk as cdk

from stacks.data_stack import DataStack
from stacks.api_stack import ApiStack
from stacks.ai_stack import AIStack
from stacks.hosting_stack import HostingStack

app = cdk.App()

env = cdk.Environment(region="us-east-1")

# Phase 1: Data infrastructure (DynamoDB + S3)
data_stack = DataStack(app, "VaaniSetu-Data", env=env)

# Phase 2: AI infrastructure (Bedrock KB)
ai_stack = AIStack(app, "VaaniSetu-AI", env=env, data_stack=data_stack)
ai_stack.add_dependency(data_stack)

# Phase 3: API + Lambda functions (REST + WebSocket)
api_stack = ApiStack(app, "VaaniSetu-API", env=env, data_stack=data_stack, ai_stack=ai_stack)
api_stack.add_dependency(data_stack)
api_stack.add_dependency(ai_stack)

# Phase 4: Frontend hosting (S3 + CloudFront)
hosting_stack = HostingStack(app, "VaaniSetu-Hosting", env=env)
hosting_stack.add_dependency(api_stack)

app.synth()
