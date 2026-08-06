# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

output "role_arn" {
  value = aws_iam_role.role.arn
}
