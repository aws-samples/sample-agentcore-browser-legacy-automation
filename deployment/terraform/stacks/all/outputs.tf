# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# =============================================================================
# Single-Apply Stack — Outputs
# =============================================================================
# Consumed by:
#   - scripts/deploy-ui.sh       (CloudFront + Cognito + gateway endpoint)
#   - scripts/teardown.sh        (bucket name to empty before destroy)
#   - browser-agent-container scripts/docker_build_ecr.sh (ECR URL)
#   - gateway-container scripts/docker_build_ecr.sh       (ECR URL)
# =============================================================================

# -----------------------------------------------------------------------------
# UI — CloudFront
# -----------------------------------------------------------------------------
output "cloudfront_domain" {
  description = "CloudFront distribution domain name (e.g. d1234abcd.cloudfront.net). UI is reachable at https://<this>."
  value       = module.ui.distribution_domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID. Used by deploy-ui.sh to invalidate the cache after an upload."
  value       = module.ui.distribution_id
}

output "ui_bucket_name" {
  description = "Name of the private S3 bucket that backs the CloudFront UI. Used by deploy-ui.sh for `aws s3 sync` and by teardown.sh to empty the bucket before destroy."
  value       = module.ui.bucket_name
}

# -----------------------------------------------------------------------------
# Cognito
# -----------------------------------------------------------------------------
output "cognito_user_pool_id" {
  description = "Cognito user pool ID."
  value       = module.cognito.user_pool_id
}

output "cognito_user_pool_issuer" {
  description = "OIDC issuer URL for the Cognito user pool (feed to the UI __OIDC_AUTHORITY__ build-time variable)."
  value       = module.cognito.user_pool_issuer
}

output "cognito_discovery_url" {
  description = "OIDC discovery URL (.well-known/openid-configuration)."
  value       = module.cognito.discovery_url
}

output "ui_app_client_id" {
  description = "SPA app client ID (feed to the UI __OIDC_CLIENT_ID__ build-time variable)."
  value       = module.cognito.ui_app_client_id
}

output "m2m_app_client_id" {
  description = "Machine-to-machine app client ID (used by integration tests)."
  value       = module.cognito.m2m_app_client_id
}

output "m2m_app_client_secret" {
  description = "Machine-to-machine app client secret. Sensitive."
  value       = module.cognito.m2m_app_client_secret
  sensitive   = true
}

output "m2m_token_endpoint" {
  description = "OAuth2 token endpoint for the M2M client_credentials grant."
  value       = module.cognito.m2m_token_endpoint
}

output "cognito_hosted_ui_domain" {
  description = "Cognito hosted-UI base domain."
  value       = module.cognito.hosted_ui_domain
}

# -----------------------------------------------------------------------------
# ECR repositories
# -----------------------------------------------------------------------------
output "browser_agent_ecr_url" {
  description = "ECR repository URL for the browser-agent-container image."
  value       = module.browser_agent_ecr.repository_url
}

output "gateway_ecr_url" {
  description = "ECR repository URL for the gateway-container image."
  value       = module.gateway_ecr.repository_url
}

# -----------------------------------------------------------------------------
# AgentCore Runtime
# -----------------------------------------------------------------------------
output "agentcore_runtime_arn" {
  description = "ARN of the Bedrock AgentCore Runtime hosting the browser agent."
  value       = module.browser_agent.agent_runtime_arn
}

output "agentcore_runtime_id" {
  description = "ID of the Bedrock AgentCore Runtime."
  value       = module.browser_agent.agent_runtime_id
}

output "agentcore_invocation_url" {
  description = "WebSocket invocation URL for the browser agent — used by gateway to reach AgentCore."
  value       = "wss://bedrock-agentcore.${data.aws_region.current.region}.amazonaws.com/runtimes/${urlencode(module.browser_agent.agent_runtime_arn)}/ws"
}

# -----------------------------------------------------------------------------
# Gateway ALB
# -----------------------------------------------------------------------------
output "gateway_alb_dns_name" {
  description = "DNS name of the gateway Application Load Balancer. Used directly when no custom hostname is set; otherwise gateway_public_url is preferred."
  value       = module.gateway.alb_dns_name
}

output "gateway_public_url" {
  description = "Public HTTPS base URL for the gateway. Resolves to https://<gateway_public_hostname> when set, otherwise http://<alb-dns>. Consumed by deploy-ui.sh to bake __WEBSOCKET_URL__ into the UI bundle."
  value       = local.ui_gateway_public_url
}

# -----------------------------------------------------------------------------
# Session store
# -----------------------------------------------------------------------------
output "s3_sessions_bucket" {
  description = "Name of the S3 bucket used by the browser agent for session persistence."
  value       = module.session_bucket.bucket_name
}
