"""Request Bedrock quota increases for Nova Lite model."""
import boto3

client = boto3.client('service-quotas', region_name='us-east-1')

# Find the specific quota codes for Nova Lite on-demand
TARGET_QUOTAS = [
    "On-demand model inference tokens per minute for Amazon Nova Lite",
    "Model invocation max tokens per day for Amazon Nova Lite",
]

paginator = client.get_paginator('list_service_quotas')
found = []
for page in paginator.paginate(ServiceCode='bedrock'):
    for q in page['Quotas']:
        name = q.get('QuotaName', '')
        if name in TARGET_QUOTAS:
            found.append(q)
            print(f"Found: {name}")
            print(f"  Code: {q['QuotaCode']}")
            print(f"  Current value: {q['Value']}")
            print(f"  Adjustable: {q.get('Adjustable', 'N/A')}")
            print()

# Try to request increases
for q in found:
    if q['Value'] == 0.0 and q.get('Adjustable'):
        desired = 100000 if 'per minute' in q['QuotaName'] else 1000000
        print(f"Requesting increase for: {q['QuotaName']}")
        print(f"  From: {q['Value']} -> To: {desired}")
        try:
            resp = client.request_service_quota_increase(
                ServiceCode='bedrock',
                QuotaCode=q['QuotaCode'],
                DesiredValue=desired,
            )
            print(f"  Request ID: {resp['RequestedQuota']['Id']}")
            print(f"  Status: {resp['RequestedQuota']['Status']}")
        except Exception as e:
            print(f"  Error: {e}")
        print()

if not found:
    print("Could not find the target quotas. Try the AWS Console instead:")
    print("  AWS Console -> Service Quotas -> Bedrock -> search 'Nova Lite'")
