"""Check Bedrock quotas for Nova Lite model."""
import boto3

client = boto3.client('service-quotas', region_name='us-east-1')

paginator = client.get_paginator('list_service_quotas')
for page in paginator.paginate(ServiceCode='bedrock'):
    for q in page['Quotas']:
        name = q.get('QuotaName', '')
        if 'nova' in name.lower() and 'lite' in name.lower():
            print(f"  {name}: {q['Value']}")
