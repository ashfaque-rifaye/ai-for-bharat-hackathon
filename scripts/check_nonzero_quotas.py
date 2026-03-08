"""Find any Bedrock model with non-zero on-demand quota."""
import boto3

client = boto3.client('service-quotas', region_name='us-east-1')
paginator = client.get_paginator('list_service_quotas')

print("=== Bedrock quotas with NON-ZERO values (on-demand/inference) ===\n")
for page in paginator.paginate(ServiceCode='bedrock'):
    for q in page['Quotas']:
        name = q.get('QuotaName', '')
        val = q.get('Value', 0)
        # Only show on-demand inference quotas that are > 0
        if val > 0 and ('inference' in name.lower() or 'invocation' in name.lower()):
            if 'tokens' in name.lower() or 'requests' in name.lower():
                print(f"  {name}: {val}")
