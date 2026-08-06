# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

output "agent_runtime_arn" {
  description = "ARN of the Bedrock AgentCore runtime"
  value       = aws_bedrockagentcore_agent_runtime.this.agent_runtime_arn
}

output "agent_runtime_name" {
  description = "Name of the Bedrock AgentCore runtime"
  value       = aws_bedrockagentcore_agent_runtime.this.agent_runtime_name
}

output "agent_runtime_id" {
  description = "Unique identifier of the Bedrock AgentCore runtime"
  value       = aws_bedrockagentcore_agent_runtime.this.agent_runtime_id
}

output "agent_runtime_version" {
  description = "Version of the Bedrock AgentCore runtime"
  value       = aws_bedrockagentcore_agent_runtime.this.agent_runtime_version
}

output "network_mode" {
  description = "Network mode of the agent runtime"
  value       = aws_bedrockagentcore_agent_runtime.this.network_configuration[0].network_mode
}

output "workload_identity_details" {
  description = "Workload identity details for the agent runtime"
  value       = aws_bedrockagentcore_agent_runtime.this.workload_identity_details
}

# ----------------------------------------------------------
#              CloudWatch Log Group Outputs
# ----------------------------------------------------------
output "application_log_group_name" {
  description = "Name of the application log group (null if not using auto-created CWL)"
  value       = var.enable_log_delivery && var.log_destination_type == "CWL" && var.log_destination_arn == null ? aws_cloudwatch_log_group.application[0].name : null
}

output "application_log_group_arn" {
  description = "ARN of the application log group (null if not using auto-created CWL)"
  value       = var.enable_log_delivery && var.log_destination_type == "CWL" && var.log_destination_arn == null ? aws_cloudwatch_log_group.application[0].arn : null
}

output "usage_log_group_name" {
  description = "Name of the usage log group (null if not using auto-created CWL)"
  value       = var.enable_usage_log_delivery && var.usage_log_destination_type == "CWL" && var.usage_log_destination_arn == null ? aws_cloudwatch_log_group.usage[0].name : null
}

output "usage_log_group_arn" {
  description = "ARN of the usage log group (null if not using auto-created CWL)"
  value       = var.enable_usage_log_delivery && var.usage_log_destination_type == "CWL" && var.usage_log_destination_arn == null ? aws_cloudwatch_log_group.usage[0].arn : null
}

output "endpoint_log_group_name" {
  description = "Name of the endpoint log group"
  value       = data.aws_cloudwatch_log_group.endpoint.name
}

output "endpoint_log_group_arn" {
  description = "ARN of the endpoint log group"
  value       = data.aws_cloudwatch_log_group.endpoint.arn
}

output "workload_identity_arn" {
  description = "ARN of the workload identity"
  value       = try(aws_bedrockagentcore_agent_runtime.this.workload_identity_details[0].workload_identity_arn, null)
}

output "tags_all" {
  description = "A map of tags assigned to the resource, including provider default_tags"
  value       = aws_bedrockagentcore_agent_runtime.this.tags_all
}

# Endpoint outputs (when created)
output "endpoint_arn" {
  description = "ARN of the agent runtime endpoint (if created)"
  value       = var.create_endpoint ? aws_bedrockagentcore_agent_runtime_endpoint.this[0].agent_runtime_endpoint_arn : null
}

output "endpoint_name" {
  description = "Name of the agent runtime endpoint (if created)"
  value       = var.create_endpoint ? aws_bedrockagentcore_agent_runtime_endpoint.this[0].name : null
}

output "endpoint_agent_runtime_arn" {
  description = "ARN of the associated agent runtime from endpoint (if created)"
  value       = var.create_endpoint ? aws_bedrockagentcore_agent_runtime_endpoint.this[0].agent_runtime_arn : null
}
