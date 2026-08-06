# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# =============================================================================
# Cognito User Pool Module
# =============================================================================
# Creates a user pool with:
#   - Hosted UI domain (Cognito-managed subdomain)
#   - Resource server with custom scopes (for M2M)
#   - Optional SPA app client (PKCE + authorization code, no secret)
#   - Optional M2M app client (client_credentials grant, with secret)
#
# Discovery URL: https://cognito-idp.<region>.amazonaws.com/<user-pool-id>/.well-known/openid-configuration
# =============================================================================

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.18"
    }
  }
}

data "aws_region" "current" {}

# -----------------------------------------------------------------------------
# User Pool
# -----------------------------------------------------------------------------
resource "aws_cognito_user_pool" "this" {
  name = var.user_pool_name

  password_policy {
    minimum_length    = var.password_policy.minimum_length
    require_lowercase = var.password_policy.require_lowercase
    require_numbers   = var.password_policy.require_numbers
    require_symbols   = var.password_policy.require_symbols
    require_uppercase = var.password_policy.require_uppercase
  }

  mfa_configuration = var.mfa_configuration

  # Auto-verified attributes so password-reset / email-as-username works out of the box.
  auto_verified_attributes = ["email"]

  username_attributes = ["email"]

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  admin_create_user_config {
    allow_admin_create_user_only = var.allow_admin_create_user_only
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Hosted UI Domain (Cognito-managed subdomain)
# -----------------------------------------------------------------------------
resource "aws_cognito_user_pool_domain" "this" {
  domain       = var.domain_prefix
  user_pool_id = aws_cognito_user_pool.this.id
}

# -----------------------------------------------------------------------------
# Resource Server (for M2M custom scopes)
# -----------------------------------------------------------------------------
resource "aws_cognito_resource_server" "this" {
  identifier   = var.resource_server_identifier
  name         = var.resource_server_identifier
  user_pool_id = aws_cognito_user_pool.this.id

  dynamic "scope" {
    for_each = var.m2m_scopes
    content {
      scope_name        = scope.value.name
      scope_description = scope.value.description
    }
  }
}

# -----------------------------------------------------------------------------
# SPA App Client (UI) — PKCE + authorization code grant, no secret
# -----------------------------------------------------------------------------
resource "aws_cognito_user_pool_client" "ui" {
  count = var.create_ui_app_client ? 1 : 0

  name         = var.ui_app_client_name
  user_pool_id = aws_cognito_user_pool.this.id

  generate_secret = false

  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "profile", "email"]

  supported_identity_providers = ["COGNITO"]

  callback_urls = var.callback_urls
  logout_urls   = var.logout_urls

  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]

  prevent_user_existence_errors = "ENABLED"

  # Dependency: the hosted UI domain must exist so the authorization endpoint works.
  depends_on = [aws_cognito_user_pool_domain.this]
}

# -----------------------------------------------------------------------------
# M2M App Client — client_credentials grant, with generated secret
# -----------------------------------------------------------------------------
resource "aws_cognito_user_pool_client" "m2m" {
  count = var.create_m2m_app_client ? 1 : 0

  name         = var.m2m_app_client_name
  user_pool_id = aws_cognito_user_pool.this.id

  generate_secret = true

  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["client_credentials"]
  allowed_oauth_scopes = [
    for s in var.m2m_scopes : "${var.resource_server_identifier}/${s.name}"
  ]

  supported_identity_providers = ["COGNITO"]

  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]

  prevent_user_existence_errors = "ENABLED"

  # Depends on the resource server so the scopes exist before the client references them.
  depends_on = [
    aws_cognito_resource_server.this,
    aws_cognito_user_pool_domain.this,
  ]
}
