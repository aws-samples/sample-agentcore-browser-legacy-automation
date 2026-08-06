# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# ----------------------------------------------------------
#                Agent Runtime Configuration
# ----------------------------------------------------------
variable "agent_runtime_name" {
  type        = string
  description = "Name of the Bedrock AgentCore runtime"
  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9_]{0,47}$", var.agent_runtime_name))
    error_message = "Agent runtime name must start with a letter and contain only letters, numbers, and underscores (max 48 characters)."
  }
}

variable "description" {
  type        = string
  description = "Description of the agent runtime"
  default     = ""
}

variable "role_arn" {
  type        = string
  description = "ARN of the IAM role for the AgentCore runtime"
  validation {
    condition     = can(regex("^arn:aws:iam::[0-9]{12}:role/.+", var.role_arn))
    error_message = "Role ARN must be a valid IAM role ARN format."
  }
}

variable "container_uri" {
  type        = string
  description = "ECR container URI for the agent runtime"
  validation {
    condition     = can(regex("^[0-9]{12}\\.dkr\\.ecr\\.[a-z0-9-]+\\.amazonaws\\.com/.+", var.container_uri))
    error_message = "Container URI must be a valid ECR repository URI."
  }
}

variable "region" {
  type        = string
  description = "AWS region for the agent runtime"
  default     = ""
}

# ----------------------------------------------------------
#                Authorization Configuration
# ----------------------------------------------------------
variable "enable_custom_jwt_authorizer" {
  type        = bool
  description = "Enable custom JWT authorizer for the agent runtime"
  default     = false
}

variable "jwt_discovery_url" {
  type        = string
  description = "JWT discovery URL for custom authorizer (must end with .well-known/openid-configuration)"
  default     = ""
  validation {
    condition     = var.jwt_discovery_url == "" || can(regex("^https://.*\\.well-known/openid-configuration$", var.jwt_discovery_url))
    error_message = "JWT discovery URL must be a valid HTTPS URL ending with .well-known/openid-configuration or empty."
  }
}

variable "jwt_allowed_audience" {
  type        = list(string)
  description = "List of allowed audiences for JWT authorizer"
  default     = []
}

variable "jwt_allowed_clients" {
  type        = list(string)
  description = "List of allowed client IDs for JWT authorizer (validated against the client_id claim in the JWT token)"
  default     = []
}

# ----------------------------------------------------------
#                Network Configuration
# ----------------------------------------------------------
variable "network_mode" {
  type        = string
  description = "Network mode for the agent runtime"
  default     = "PUBLIC"
  validation {
    condition     = contains(["PUBLIC", "VPC"], var.network_mode)
    error_message = "Network mode must be either PUBLIC or VPC."
  }
}

variable "vpc_subnet_ids" {
  type        = list(string)
  description = "List of VPC subnet IDs for the agent runtime (required when network_mode is VPC)"
  default     = []
}

variable "vpc_security_group_ids" {
  type        = list(string)
  description = "List of VPC security group IDs for the agent runtime (required when network_mode is VPC)"
  default     = []
}

# ----------------------------------------------------------
#                Protocol Configuration
# ----------------------------------------------------------
variable "server_protocol" {
  type        = string
  description = "Server protocol for the agent runtime"
  default     = "MCP"
  validation {
    condition     = contains(["HTTP", "MCP", "A2A"], var.server_protocol)
    error_message = "Server protocol must be HTTP, MCP, or A2A."
  }
}

# ----------------------------------------------------------
#                Lifecycle Configuration
# ----------------------------------------------------------
variable "idle_runtime_session_timeout" {
  type        = number
  description = "Timeout in seconds for idle runtime sessions"
  default     = null
}

variable "max_lifetime" {
  type        = number
  description = "Maximum lifetime for the instance in seconds"
  default     = null
}

# ----------------------------------------------------------
#                Request Header Configuration
# ----------------------------------------------------------
variable "request_header_allowlist" {
  type        = list(string)
  description = "List of HTTP request headers allowed to be passed through to the runtime"
  default     = []
}

# ----------------------------------------------------------
#                Endpoint Configuration
# ----------------------------------------------------------
variable "create_endpoint" {
  type        = bool
  description = "Create an agent runtime endpoint for external access"
  default     = false
}

variable "endpoint_name" {
  type        = string
  description = "Name of the agent runtime endpoint (defaults to agent_runtime_name-endpoint)"
  default     = ""
}

variable "endpoint_description" {
  type        = string
  description = "Description of the agent runtime endpoint"
  default     = ""
}

variable "agent_runtime_version" {
  type        = string
  description = "Version of the agent runtime to use for the endpoint"
  default     = ""
}

# ----------------------------------------------------------
#                Environment Variables
# ----------------------------------------------------------
variable "environment_variables" {
  type        = map(string)
  description = "Environment variables for the agent runtime"
  default = {
    LOG_LEVEL = "INFO"
    ENV       = "production"
  }
  validation {
    condition = alltrue([
      for k, v in var.environment_variables : can(regex("^[A-Z_][A-Z0-9_]*$", k))
    ])
    error_message = "Environment variable names must be uppercase with underscores."
  }
}

# ----------------------------------------------------------
#                         Tags
# ----------------------------------------------------------
variable "tags" {
  type        = map(string)
  description = "A map containing tags for the agent runtime resources"
  default     = {}
}

# ----------------------------------------------------------
#                CloudWatch Logging
# ----------------------------------------------------------
variable "enable_log_delivery" {
  type        = bool
  description = "Enable application log delivery for the agent runtime."
  default     = true
}

variable "log_destination_type" {
  type        = string
  description = "Destination type for application log delivery. CWL (CloudWatch Logs), S3 (Amazon S3), FH (Amazon Data Firehose)."
  default     = "CWL"
  validation {
    condition     = contains(["CWL", "S3", "FH"], var.log_destination_type)
    error_message = "log_destination_type must be one of: CWL, S3, FH."
  }
}

variable "log_destination_arn" {
  type        = string
  description = "ARN of the application log destination. When null and destination is CWL, a log group is auto-created."
  default     = null
}

variable "log_output_format" {
  type        = string
  description = "Output format for log delivery. Valid values: json, plain, w3c, raw, parquet."
  default     = "json"
  validation {
    condition     = contains(["json", "plain", "w3c", "raw", "parquet"], var.log_output_format)
    error_message = "log_output_format must be one of: json, plain, w3c, raw, parquet."
  }
}

variable "enable_usage_log_delivery" {
  type        = bool
  description = "Enable usage log delivery for the agent runtime."
  default     = true
}

variable "usage_log_destination_type" {
  type        = string
  description = "Destination type for usage log delivery. CWL (CloudWatch Logs), S3 (Amazon S3), FH (Amazon Data Firehose)."
  default     = "CWL"
  validation {
    condition     = contains(["CWL", "S3", "FH"], var.usage_log_destination_type)
    error_message = "usage_log_destination_type must be one of: CWL, S3, FH."
  }
}

variable "usage_log_destination_arn" {
  type        = string
  description = "ARN of the usage log destination. When null and destination is CWL, a log group is auto-created."
  default     = null
}

variable "enable_trace_delivery" {
  type        = bool
  description = "Enable X-Ray trace delivery for the agent runtime."
  default     = false
}

variable "log_retention_days" {
  type        = number
  description = "CloudWatch log retention in days. Only used for auto-created CWL log groups."
  default     = 7
}
