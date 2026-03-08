import boto3
import time

cf = boto3.client('cloudfront', region_name='us-east-1')
resp = cf.create_invalidation(
    DistributionId='EPDYEGTXUQA0Z',
    InvalidationBatch={
        'Paths': {'Quantity': 1, 'Items': ['/screenshots/*']},
        'CallerReference': str(int(time.time()))
    }
)
inv_id = resp['Invalidation']['Id']
status = resp['Invalidation']['Status']
print(f'Invalidation created: {inv_id}')
print(f'Status: {status}')
