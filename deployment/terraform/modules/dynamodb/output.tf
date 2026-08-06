# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

output "table_name" {
  description = "Table name of the DynamoDB table"
  value       = aws_dynamodb_table.dynamodb_table.name
}

output "table_arn" {
  description = "ARN of the DynamoDB table"
  value       = aws_dynamodb_table.dynamodb_table.arn
}
