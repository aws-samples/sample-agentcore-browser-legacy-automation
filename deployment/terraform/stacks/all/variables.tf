# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# =============================================================================
# Single-Apply Stack — Variables
# =============================================================================
# Inputs for the consolidated Browser Agent reference-architecture stack.
# Fill these in terraform.tfvars; see terraform.tfvars.sample for placeholders.
# =============================================================================

# -----------------------------------------------------------------------------
# AWS provider
# -----------------------------------------------------------------------------
variable "aws_region" {
  description = "AWS region into which all resources are deployed."
  type        = string
  default     = "us-west-2"
}

variable "aws_profile" {
  description = "AWS CLI profile to use (empty string = default credential chain)."
  type        = string
  default     = ""
}

# -----------------------------------------------------------------------------
# Project metadata + tagging
# -----------------------------------------------------------------------------
variable "project_name" {
  description = "Short project identifier used to name and tag resources (e.g. \"browser-agent-blog\")."
  type        = string
  default     = "browser-agent-blog"
}

variable "environment" {
  description = "Environment tag applied to all resources (dev | staging | prod)."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

# -----------------------------------------------------------------------------
# Cognito
# -----------------------------------------------------------------------------
variable "cognito_domain_prefix" {
  description = "Globally unique Cognito hosted-UI domain prefix. Must be unique across the region."
  type        = string
}

variable "ui_callback_urls" {
  description = "Optional override for the SPA OAuth callback URLs. When empty (default), the stack derives them from the CloudFront domain (`https://<cloudfront>/callback`). Set this only if you need additional callbacks (e.g. localhost for development)."
  type        = list(string)
  default     = []
}

variable "ui_logout_urls" {
  description = "Optional override for the SPA post-logout redirect URLs. When empty (default), the stack derives them from the CloudFront domain (`https://<cloudfront>/login`)."
  type        = list(string)
  default     = []
}

# -----------------------------------------------------------------------------
# Container images
# -----------------------------------------------------------------------------
# Each image can be pinned by either a mutable tag (`*_image_tag`) or an
# immutable digest (`*_image_digest`, format `sha256:...`). The digest takes
# precedence when both are set on the same image. Setting only the digest is
# the recommended production path: every image refresh becomes a Terraform
# `apply` instead of an out-of-band `aws ecs update-service` /
# `aws bedrock-agentcore-control update-agent-runtime` call, and rollbacks are
# a one-line `terraform.tfvars` revert.
variable "browser_agent_image_tag" {
  description = "Tag of the browser-agent-container image to deploy. Used when browser_agent_image_digest is empty. Push the image with this tag to the ECR repo before apply."
  type        = string
  default     = "linux-arm64"
}

variable "browser_agent_image_digest" {
  description = "Optional immutable digest of the browser-agent-container image (format `sha256:...`). When set, takes precedence over browser_agent_image_tag and produces a `repo@sha256:...` URI. The push script prints the digest after every push — copy it here and run `terraform apply` to roll the AgentCore runtime onto the new image."
  type        = string
  default     = ""

  validation {
    condition     = var.browser_agent_image_digest == "" || can(regex("^sha256:[0-9a-f]{64}$", var.browser_agent_image_digest))
    error_message = "browser_agent_image_digest must be empty or in the form sha256:<64 hex chars>."
  }
}

variable "gateway_image_tag" {
  description = "Tag of the gateway-container (NGINX) image to deploy. Used when gateway_image_digest is empty."
  type        = string
  default     = "latest"
}

variable "gateway_image_digest" {
  description = "Optional immutable digest of the gateway-container image (format `sha256:...`). When set, takes precedence over gateway_image_tag and produces a `repo@sha256:...` URI. The push script prints the digest after every push — copy it here and run `terraform apply` to roll the ECS service onto the new image."
  type        = string
  default     = ""

  validation {
    condition     = var.gateway_image_digest == "" || can(regex("^sha256:[0-9a-f]{64}$", var.gateway_image_digest))
    error_message = "gateway_image_digest must be empty or in the form sha256:<64 hex chars>."
  }
}

# -----------------------------------------------------------------------------
# Gateway ECS Fargate sizing
# -----------------------------------------------------------------------------
variable "ecs_cpu" {
  description = "CPU units for the gateway Fargate task (256, 512, 1024, 2048, 4096)."
  type        = number
  default     = 256
}

variable "ecs_memory" {
  description = "Memory (MiB) for the gateway Fargate task. Must be Fargate-compatible with ecs_cpu."
  type        = number
  default     = 512
}

variable "gateway_desired_count" {
  description = "Number of gateway tasks to run."
  type        = number
  default     = 2
}

# -----------------------------------------------------------------------------
# Gateway networking — required because ECS Fargate + ALB need explicit VPC config
# -----------------------------------------------------------------------------
variable "vpc_id" {
  description = "VPC ID for the gateway ECS service and ALB."
  type        = string
}

variable "gateway_subnet_ids" {
  description = "Subnet IDs for the gateway ECS tasks. Private subnets with NAT access are recommended."
  type        = list(string)
}

variable "gateway_security_group_ids" {
  description = "Security group IDs attached to the gateway tasks."
  type        = list(string)
}

variable "alb_subnet_ids" {
  description = "Subnet IDs for the gateway ALB. At least 2 subnets in different AZs."
  type        = list(string)
}

variable "alb_security_group_ids" {
  description = "Security group IDs attached to the gateway ALB."
  type        = list(string)
}

variable "alb_assign_public_ip" {
  description = "Assign a public IP to the gateway tasks. Typically false when using private subnets + NAT."
  type        = bool
  default     = false
}

# -----------------------------------------------------------------------------
# TLS / CloudFront
# -----------------------------------------------------------------------------
variable "acm_certificate_arn" {
  description = "Existing ACM certificate ARN for the gateway ALB HTTPS listener. Use this when you want to bring your own certificate. When empty AND gateway_public_hostname is set AND manage_acm_certificate is true, the stack requests a new DNS-validated certificate via Route 53 in route53_zone_id. When all three are empty/false, the ALB runs HTTP-only (development mode — browsers block wss:// from https:// origins)."
  type        = string
  default     = ""
}

# -----------------------------------------------------------------------------
# Custom domain for the gateway ALB
# -----------------------------------------------------------------------------
# Setting all three of these together is the production path. Setting none of
# them keeps the ALB in HTTP-only mode (development only).
variable "gateway_public_hostname" {
  description = "Public hostname for the gateway ALB (e.g. gateway.example.com). When set, the stack attaches an ACM certificate to the ALB's HTTPS listener and bakes wss://<this>/ws into the UI bundle. Leave empty to keep the ALB on HTTP only."
  type        = string
  default     = ""
}

variable "route53_zone_id" {
  description = "Route 53 hosted zone ID for the parent domain. When set together with gateway_public_hostname, Terraform creates the ACM cert-validation record and a gateway alias record automatically. Leave empty if your DNS is managed outside Route 53; you must then provide acm_certificate_arn yourself and add the gateway DNS record at your registrar."
  type        = string
  default     = ""
}

variable "manage_acm_certificate" {
  description = "When true and gateway_public_hostname + route53_zone_id are set, the stack requests a new ACM certificate via DNS validation. Set to false to bring an existing cert via acm_certificate_arn."
  type        = bool
  default     = true
}

variable "cloudfront_price_class" {
  description = "CloudFront price class: PriceClass_100 (US/CA/EU) | PriceClass_200 | PriceClass_All."
  type        = string
  default     = "PriceClass_100"
}

variable "cloudfront_acm_certificate_arn" {
  description = "ACM certificate ARN in us-east-1 for a custom CloudFront domain. Empty string = use the default *.cloudfront.net certificate."
  type        = string
  default     = ""
}

variable "cloudfront_aliases" {
  description = "Custom-domain aliases for the CloudFront distribution. Requires cloudfront_acm_certificate_arn."
  type        = list(string)
  default     = []
}

# -----------------------------------------------------------------------------
# Environment variables passthrough (per steering tech.md)
# -----------------------------------------------------------------------------
variable "environment_variables" {
  description = "Passthrough map(string) of container environment variables injected into the browser-agent AgentCore runtime. The stack automatically merges in `BA_SESSION_STORE_BUCKET` (from the session-store bucket output) so callers don't have to wire it manually. Per steering tech.md: assembled in terraform.tfvars, passed through to the module unchanged otherwise."
  type        = map(string)
  default     = {}
}

variable "gateway_environment_variables" {
  description = "Passthrough map(string) of environment variables for the gateway ECS task. The stack automatically merges in `BROWSER_AGENT_ARN` (from the AgentCore runtime ARN) and `BROWSER_AGENTCORE_ENDPOINT` (derived from `aws_region`) so callers don't have to wire them manually. Anything in this map (e.g. `LOG_LEVEL`) takes precedence over the auto-derived defaults."
  type        = map(string)
  default     = {}
}

# -----------------------------------------------------------------------------
# S3 session-store bucket
# -----------------------------------------------------------------------------
variable "session_bucket_force_destroy" {
  description = "If true, S3 session bucket can be destroyed by terraform destroy even when non-empty. Useful for blog reference-architecture tear-down."
  type        = bool
  default     = true
}
