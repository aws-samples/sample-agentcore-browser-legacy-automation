# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

resource "aws_s3_bucket" "this" {
  #checkov:skip=CKV2_AWS_62:Event notification not required
  #checkov:skip=CKV_AWS_18:Access logging will be enabled ad-hoc or through CloudTrail data access logging ad-hoc
  #checkov:skip=CKV2_AWS_61:Lifecycle configuration is not required
  #checkov:skip=CKV2_AWS_6:S3 bucket does block public access via aws_s3_bucket_public_access_block
  #checkov:skip=CKV_AWS_21:S3 bucket does have versioning enabled via aws_s3_bucket_versioning
  #checkov:skip=CKV_AWS_144:Cross region replication not necessary
  #checkov:skip=CKV_AWS_145:SSE-S3 is default encryption and appropriate for common use cases
  count         = length(var.bucket_name) > 0 ? 1 : 0
  bucket        = var.bucket_name
  force_destroy = var.force_destroy

  tags = var.bucket_tags
}


resource "aws_s3_bucket_public_access_block" "this" {
  bucket                  = aws_s3_bucket.this[0].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "this" {
  count  = var.versioning_enabled ? 1 : 0
  bucket = aws_s3_bucket.this[0].id
  versioning_configuration {
    status = "Enabled"
  }
}
