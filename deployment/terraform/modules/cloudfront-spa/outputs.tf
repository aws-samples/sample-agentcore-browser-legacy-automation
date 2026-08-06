# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# =============================================================================
# CloudFront SPA Module — Outputs
# =============================================================================

output "distribution_id" {
  description = "CloudFront distribution ID (used by `aws cloudfront create-invalidation`)."
  value       = aws_cloudfront_distribution.this.id
}

output "distribution_arn" {
  description = "CloudFront distribution ARN."
  value       = aws_cloudfront_distribution.this.arn
}

output "distribution_domain_name" {
  description = "CloudFront *.cloudfront.net domain (viewer-facing when aliases is empty)."
  value       = aws_cloudfront_distribution.this.domain_name
}

output "bucket_name" {
  description = "Name of the private S3 bucket backing the distribution."
  value       = aws_s3_bucket.this.bucket
}

output "bucket_regional_domain_name" {
  description = "Regional domain name of the backing S3 bucket (used as the CloudFront origin)."
  value       = aws_s3_bucket.this.bucket_regional_domain_name
}

output "oac_id" {
  description = "Origin Access Control ID used to sign S3 requests from CloudFront."
  value       = aws_cloudfront_origin_access_control.this.id
}
