# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

resource "aws_cloudwatch_log_group" "cw" {
  name = var.loggroup_name

  retention_in_days = var.retention_in_days

  kms_key_id = var.kms_key_id

  tags = var.tags
}
