# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

output "bucket_arn" {
  description = "S3 bucket ARN"
  value       = length(var.bucket_name) > 0 ? aws_s3_bucket.this[0].arn : ""
}

output "bucket_name" {
  description = "S3 bucket name"
  value       = length(var.bucket_name) > 0 ? aws_s3_bucket.this[0].bucket : ""
}
