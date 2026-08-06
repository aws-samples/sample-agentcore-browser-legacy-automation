# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Concierge Gateway Container — Terraform Outputs

# ============================================================================
# ALB
# ============================================================================

output "alb_dns_name" {
  description = "ALB DNS name for the gateway"
  value       = module.gateway.alb_dns_name
}

output "alb_arn" {
  description = "ALB ARN"
  value       = module.gateway.alb_arn
}

output "alb_https_url" {
  description = "Gateway HTTPS URL (WebSocket: wss://<dns>/ws?token=<JWT>&profile=<profile>)"
  value       = "https://${module.gateway.alb_dns_name}"
}

# ============================================================================
# ECS
# ============================================================================

output "cluster_arn" {
  description = "ECS cluster ARN"
  value       = module.gateway.cluster_arn
}

output "service_name" {
  description = "ECS service name"
  value       = module.gateway.service_name
}

output "service_arn" {
  description = "ECS service ARN"
  value       = module.gateway.service_arn
}

output "task_definition_arn" {
  description = "ECS task definition ARN"
  value       = module.gateway.task_definition_arn
}

output "task_definition_revision" {
  description = "ECS task definition revision number"
  value       = module.gateway.task_definition_revision
}

# ============================================================================
# Observability
# ============================================================================

output "log_group_name" {
  description = "CloudWatch log group name"
  value       = module.gateway.log_group_name
}

# ============================================================================
# IAM
# ============================================================================

output "task_role_arn" {
  description = "ECS task role ARN"
  value       = module.task_role.role_arn
}

output "execution_role_arn" {
  description = "ECS task execution role ARN"
  value       = module.execution_role.role_arn
}
