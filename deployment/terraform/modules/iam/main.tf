# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0


resource "aws_iam_role" "role" {
  name = var.role_name
  assume_role_policy = var.custom_role_policy != null ? jsonencode(var.custom_role_policy) : jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : [
          "sts:AssumeRole"
        ],
        "Principal" : {
          "Service" : [
            "${var.principal_name}"
          ]
        }
      }
    ]
  })
  tags = var.role_tags
}

resource "aws_iam_role_policy" "inline_policy" {
  for_each = { for i, policy in var.inline_policies : i => policy }
  name     = each.value.name
  role     = aws_iam_role.role.name

  policy = jsonencode(each.value.policy)
}
