# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

output "loggroup_arn" {
  value = aws_cloudwatch_log_group.cw.arn
}

output "loggroup_name" {
  value = aws_cloudwatch_log_group.cw.name
}