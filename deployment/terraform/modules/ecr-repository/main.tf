# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

resource "aws_ecr_repository" "ecr_repository" {
  #checkov:skip=CKV_AWS_136:encryption is mandatory using either KMS or AES256 - both are encrypted
  #checkov:skip=CKV_AWS_51:tag mutability not a concern for demo account
  name                 = var.ecr_name
  image_tag_mutability = var.ecr_image_tag_mutability
  force_delete         = var.ecr_force_delete

  tags = merge(var.common_tags, var.ecr_tags)

  image_scanning_configuration {
    scan_on_push = var.ecr_scan_on_push
  }

  dynamic "encryption_configuration" {
    for_each = var.ecr_encryption_type == "KMS" ? [1] : []
    content {
      encryption_type = "KMS"
      kms_key         = var.ecr_kms_master_key_arn
    }
  }

  dynamic "encryption_configuration" {
    for_each = var.ecr_encryption_type == "AES256" ? [1] : []
    content {
      encryption_type = "AES256"
    }
  }
}
