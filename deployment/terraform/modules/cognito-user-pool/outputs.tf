# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# =============================================================================
# Cognito User Pool Module — Outputs
# =============================================================================

output "user_pool_id" {
  description = "Cognito user pool ID."
  value       = aws_cognito_user_pool.this.id
}

output "user_pool_arn" {
  description = "Cognito user pool ARN."
  value       = aws_cognito_user_pool.this.arn
}

output "user_pool_issuer" {
  description = "OIDC issuer URL for this user pool (used as the JWT `iss` claim and as the base for discovery)."
  value       = "https://cognito-idp.${data.aws_region.current.region}.amazonaws.com/${aws_cognito_user_pool.this.id}"
}

output "discovery_url" {
  description = "OIDC discovery URL (.well-known/openid-configuration) — feed this to AgentCore jwt_discovery_url and to the UI OIDC authority."
  value       = "https://cognito-idp.${data.aws_region.current.region}.amazonaws.com/${aws_cognito_user_pool.this.id}/.well-known/openid-configuration"
}

output "ui_app_client_id" {
  description = "SPA app client ID (empty string if create_ui_app_client = false)."
  value       = var.create_ui_app_client ? aws_cognito_user_pool_client.ui[0].id : ""
}

output "m2m_app_client_id" {
  description = "M2M app client ID (empty string if create_m2m_app_client = false)."
  value       = var.create_m2m_app_client ? aws_cognito_user_pool_client.m2m[0].id : ""
}

output "m2m_app_client_secret" {
  description = "M2M app client secret (empty string if create_m2m_app_client = false). Sensitive."
  value       = var.create_m2m_app_client ? aws_cognito_user_pool_client.m2m[0].client_secret : ""
  sensitive   = true
}

output "m2m_token_endpoint" {
  description = "OAuth2 token endpoint for the client_credentials grant."
  value       = "https://${aws_cognito_user_pool_domain.this.domain}.auth.${data.aws_region.current.region}.amazoncognito.com/oauth2/token"
}

output "hosted_ui_domain" {
  description = "Cognito hosted-UI base domain (e.g. my-prefix.auth.us-west-2.amazoncognito.com)."
  value       = "${aws_cognito_user_pool_domain.this.domain}.auth.${data.aws_region.current.region}.amazoncognito.com"
}
