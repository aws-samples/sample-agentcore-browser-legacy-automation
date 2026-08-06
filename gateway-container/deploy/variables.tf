# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Concierge Gateway Container — Terraform Variables

# ============================================================================
# AWS Configuration
# ============================================================================

variable "aws_region" {
  type        = string
  description = "AWS region for deployment"
  default     = "us-west-2"
}

variable "aws_profile" {
  type        = string
  description = "AWS CLI profile name"
  default     = "demo"
}

variable "aws_account_id" {
  type        = string
  description = "AWS account ID for ECR image URI"
}

# ============================================================================
# Container Configuration
# ============================================================================

variable "ecr_repository_name" {
  type        = string
  description = "ECR repository name for the gateway container image"
  default     = "gateway-container"
}

variable "image_tag" {
  type        = string
  description = "Docker image tag"
  default     = "latest"
}

variable "container_name" {
  type        = string
  description = "ECS container name"
  default     = "concierge-gateway"
}

variable "task_family" {
  type        = string
  description = "ECS task definition family name"
  default     = "concierge-gateway"
}

variable "task_role_name" {
  type        = string
  description = "IAM role name prefix for ECS task and execution roles"
  default     = "concierge-gateway-role"
}

# ============================================================================
# Networking
# ============================================================================

variable "vpc_id" {
  type        = string
  description = "VPC ID for ECS service and ALB"
}

variable "subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs for ECS tasks"
}

variable "security_group_ids" {
  type        = list(string)
  description = "Security group IDs for ECS tasks"
}

variable "alb_subnets" {
  type        = list(string)
  description = "Public subnet IDs for ALB (minimum 2 in different AZs)"
}

variable "alb_security_group_ids" {
  type        = list(string)
  description = "Security group IDs for ALB"
}

# ============================================================================
# TLS
# ============================================================================

variable "certificate_arn" {
  type        = string
  description = "ACM certificate ARN for ALB HTTPS listener"
}

# ============================================================================
# Environment
# ============================================================================

variable "environment_variables" {
  type        = map(string)
  description = "Container environment variables (passthrough map pattern)"
  default     = {}
}

variable "assign_public_ip" {
  type        = bool
  description = "Assign public IP to ECS tasks (required when subnets do not auto-assign public IPs)"
  default     = false
}

variable "environment" {
  type        = string
  description = "Deployment environment tag (dev, staging, prod)"
  default     = "dev"
}
