# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

resource "aws_dynamodb_table" "dynamodb_table" {
  #checkov:skip=CKV2_AWS_16:Not use billing_mode to set size parameters - not intended for autoscale
  name           = var.dynamodb_table_name
  billing_mode   = var.billing_mode
  read_capacity  = var.billing_mode == "PROVISIONED" ? var.read_capacity : null
  write_capacity = var.billing_mode == "PROVISIONED" ? var.write_capacity : null

  server_side_encryption {
    enabled     = var.enable_server_side_encryption
    kms_key_arn = var.kms_key_arn != null ? var.kms_key_arn : null
  }

  dynamic "attribute" {
    for_each = var.attributes

    content {
      name = attribute.value.name
      type = attribute.value.type
    }
  }

  hash_key  = var.hash_key
  range_key = var.range_key

  ttl {
    attribute_name = var.ttl.attribute_name
    enabled        = var.ttl.enabled
  }

  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  lifecycle {
    prevent_destroy = false
  }

  tags = var.tags
}
