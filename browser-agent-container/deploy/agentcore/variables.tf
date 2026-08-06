# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# =============================================================================
# Browser Agent — Terraform Variables
# =============================================================================

# ----------------------------------------------------------
#                Common Variables
# ----------------------------------------------------------

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-west-2"
}

variable "aws_profile" {
  description = "AWS CLI profile to use"
  type        = string
  default     = "demo"
}

variable "aws_account_id" {
  description = "AWS account ID for ECR repository URI"
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "aws_account_id must be a 12-digit AWS account ID."
  }
}

variable "execution_role_arn" {
  description = "IAM execution role ARN for AgentCore Runtime"
  type        = string

  validation {
    condition     = can(regex("^arn:aws:iam::", var.execution_role_arn))
    error_message = "execution_role_arn must be a valid IAM role ARN."
  }
}

# ----------------------------------------------------------
#                Agent Configuration
# ----------------------------------------------------------

variable "agent_name" {
  description = "Name of the AgentCore runtime (no hyphens for AgentCore compliance)"
  type        = string
  default     = "browser_agent"
}

variable "agent_description" {
  description = "Description of the AgentCore agent"
  type        = string
  default     = "Browser automation agent — Strands-based browser control with HITL, session management, and screenshot streaming"
}

variable "environment" {
  description = "Environment name for tagging (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

# ----------------------------------------------------------
#                Container Configuration
# ----------------------------------------------------------

variable "ecr_repository_name" {
  description = "ECR repository name for the browser agent container image"
  type        = string
  default     = "browser-agent-container"
}

variable "image_tag" {
  description = "Docker image tag — change this value to trigger a new AgentCore runtime version"
  type        = string
  default     = "linux-arm64"
}

# ----------------------------------------------------------
#                Network Configuration
# ----------------------------------------------------------

variable "network_mode" {
  description = "Network mode for AgentCore (PUBLIC or VPC)"
  type        = string
  default     = "PUBLIC"

  validation {
    condition     = contains(["PUBLIC", "VPC"], var.network_mode)
    error_message = "network_mode must be PUBLIC or VPC."
  }
}

# ----------------------------------------------------------
#                Protocol Configuration
# ----------------------------------------------------------

variable "server_protocol" {
  description = "Server protocol for AgentCore Runtime (HTTP, MCP, or A2A)"
  type        = string
  default     = "HTTP"

  validation {
    condition     = contains(["HTTP", "MCP", "A2A"], var.server_protocol)
    error_message = "server_protocol must be HTTP, MCP, or A2A."
  }
}

# ----------------------------------------------------------
#                JWT Authorization Configuration
# ----------------------------------------------------------

variable "enable_jwt_authorizer" {
  description = "Enable JWT authorization for AgentCore"
  type        = bool
  default     = true
}

variable "jwt_discovery_url" {
  description = "OIDC discovery URL for JWT validation (e.g., https://your-tenant.auth0.com/.well-known/openid-configuration)"
  type        = string
  default     = ""
}

variable "jwt_allowed_audience" {
  description = "List of allowed audiences for JWT authorizer (e.g., API identifier)"
  type        = list(string)
  default     = []
}

variable "jwt_allowed_clients" {
  description = "List of allowed client IDs for JWT authorizer (validated against the client_id claim in the JWT token)"
  type        = list(string)
  default     = []
}

# ----------------------------------------------------------
#                Environment Variables
# ----------------------------------------------------------

variable "environment_variables" {
  type        = map(string)
  description = "A map containing environment variables for the AgentCore runtime. Both the key and value must be strings. Passed directly to the module via passthrough map pattern."
  default     = {}
}
