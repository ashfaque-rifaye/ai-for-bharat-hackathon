"""
HostingStack — S3 + CloudFront for serving the VaaniSetu frontend.

Why CloudFront + S3?
- S3 stores the built React files (HTML, JS, CSS)
- CloudFront is a CDN that caches files at edge locations worldwide,
  so evaluators get fast load times from anywhere
- CloudFront gives a free HTTPS URL (https://dXXXXX.cloudfront.net)

How it works:
  User visits URL → CloudFront edge → S3 bucket → serves index.html
  React app loads → calls production API Gateway → full AI flow works
"""

from aws_cdk import (
    Stack,
    RemovalPolicy,
    CfnOutput,
    Duration,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
)
from constructs import Construct
import os


class HostingStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── S3 Bucket — holds the built frontend files (HTML/JS/CSS) ──
        site_bucket = s3.Bucket(
            self,
            "VaaniSetuSiteBucket",
            website_index_document="index.html",
            website_error_document="index.html",  # SPA fallback
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # ── CloudFront Distribution — CDN layer in front of S3 ──
        # This gives a globally-accessible HTTPS URL
        distribution = cloudfront.Distribution(
            self,
            "VaaniSetuDistribution",
            comment="VaaniSetu Frontend - AI Government Scheme Assistant",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(site_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
            ),
            default_root_object="index.html",
            # SPA routing: any 403/404 from S3 → serve index.html
            # so React Router paths like /chat still work
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
            ],
        )

        # ── Deploy frontend files from dist/ to S3 ──
        # Automatically uploads everything and invalidates CloudFront cache
        dist_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "frontend", "dist"
        )

        if os.path.exists(dist_path):
            s3deploy.BucketDeployment(
                self,
                "DeployFrontend",
                sources=[s3deploy.Source.asset(dist_path)],
                destination_bucket=site_bucket,
                distribution=distribution,
                distribution_paths=["/*"],
            )

        # ── Outputs — printed after deployment ──
        CfnOutput(self, "SiteBucketName",
                  value=site_bucket.bucket_name,
                  description="S3 bucket holding the frontend files")

        CfnOutput(self, "DistributionId",
                  value=distribution.distribution_id,
                  description="CloudFront Distribution ID")

        CfnOutput(self, "PrototypeURL",
                  value=f"https://{distribution.distribution_domain_name}",
                  description="SHARE THIS URL WITH EVALUATORS")
