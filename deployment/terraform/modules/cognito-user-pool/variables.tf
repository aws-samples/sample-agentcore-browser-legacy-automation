# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# =============================================================================
# Cognito User Pool Module — Variables
# =============================================================================

variable "user_pool_name" {
  description = "Name of the Cognito user pool."
  type        = string
}

variable "domain_prefix" {
  description = "Globally unique Cognito hosted-UI domain prefix (e.g. \"browser-agent-blog-123abc\"). Must be unique across all AWS accounts in the region."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", var.domain_prefix))
    error_message = "domain_prefix must be 1-63 chars, lowercase alphanumeric plus hyphens, and cannot start or end with a hyphen."
  }
}

variable "callback_urls" {
  description = "List of allowed OAuth callback URLs for the SPA app client (e.g. the CloudFront URL + /login callback)."
  type        = list(string)
  default     = []
}

variable "logout_urls" {
  description = "List of allowed post-logout redirect URLs for the SPA app client."
  type        = list(string)
  default     = []
}

variable "allow_admin_create_user_only" {
  description = "When true (default), only administrators can create users (via aws cognito-idp admin-create-user); public self-signup at the hosted UI is disabled. Recommended for a demo / reference deployment behind a public URL. Set to false only if you intend to allow open self-registration."
  type        = bool
  default     = true
}

variable "create_ui_app_client" {
  description = "If true, create the SPA (browser) app client with PKCE + authorization-code grant."
  type        = bool
  default     = true
}

variable "ui_app_client_name" {
  description = "Name for the SPA app client."
  type        = string
  default     = "chat-bot-ui"
}

variable "create_m2m_app_client" {
  description = "If true, create the machine-to-machine app client with client_credentials grant (for integration tests)."
  type        = bool
  default     = true
}

variable "m2m_app_client_name" {
  description = "Name for the M2M app client."
  type        = string
  default     = "integration-tests-m2m"
}

variable "resource_server_identifier" {
  description = "Identifier for the Cognito resource server (used to namespace M2M scopes)."
  type        = string
  default     = "browser-agent"
}

variable "m2m_scopes" {
  description = "List of custom OAuth scopes to register on the resource server. Each scope gets exposed as \"<resource_server_identifier>/<name>\"."
  type = list(object({
    name        = string
    description = string
  }))
  default = [
    {
      name        = "invoke"
      description = "Invoke the browser agent"
    }
  ]
}

variable "password_policy" {
  description = "Password policy for the user pool."
  type = object({
    minimum_length    = number
    require_lowercase = bool
    require_numbers   = bool
    require_symbols   = bool
    require_uppercase = bool
  })
  default = {
    minimum_length    = 12
    require_lowercase = true
    require_numbers   = true
    require_symbols   = false
    require_uppercase = true
  }
}

variable "mfa_configuration" {
  description = "MFA configuration: OFF | ON | OPTIONAL."
  type        = string
  default     = "OFF"

  validation {
    condition     = contains(["OFF", "ON", "OPTIONAL"], var.mfa_configuration)
    error_message = "mfa_configuration must be OFF, ON, or OPTIONAL."
  }
}

variable "tags" {
  description = "Tags to apply to all resources created by this module."
  type        = map(string)
  default     = {}
}
