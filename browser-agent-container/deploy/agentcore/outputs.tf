# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# =============================================================================
# Browser Agent — Terraform Outputs
# =============================================================================

# ----------------------------------------------------------
#                Runtime Outputs
# ----------------------------------------------------------

output "agent_runtime_id" {
  description = "AgentCore runtime ID"
  value       = module.browser_agent.agent_runtime_id
}

output "agent_runtime_arn" {
  description = "ARN of the Browser AgentCore Runtime"
  value       = module.browser_agent.agent_runtime_arn
}

output "agent_runtime_name" {
  description = "AgentCore runtime name"
  value       = module.browser_agent.agent_runtime_name
}

output "agent_runtime_version" {
  description = "AgentCore runtime version"
  value       = module.browser_agent.agent_runtime_version
}

output "endpoint_arn" {
  description = "AgentCore endpoint ARN"
  value       = module.browser_agent.endpoint_arn
}

output "endpoint_name" {
  description = "AgentCore endpoint name"
  value       = module.browser_agent.endpoint_name
}

output "workload_identity_arn" {
  description = "Workload identity ARN"
  value       = module.browser_agent.workload_identity_arn
}

output "invocation_url" {
  description = "WebSocket invocation URL for the Browser Agent"
  value       = "wss://bedrock-agentcore.${var.aws_region}.amazonaws.com/runtimes/${urlencode(module.browser_agent.agent_runtime_arn)}/ws"
}
