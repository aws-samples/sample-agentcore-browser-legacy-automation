# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# =============================================================================
# Browser Agent Reference Architecture — Single-Apply Stack
# =============================================================================
# Provisions every cloud resource for the blog reference architecture in one
# `terraform apply`:
#
#   1. Cognito user pool + hosted UI + SPA and M2M app clients
#   2. S3 session-store bucket
#   3. IAM execution role for the AgentCore runtime (8 inline policies)
#   4. ECR repositories for browser-agent and gateway containers
#   5. CloudWatch log group for the gateway ECS tasks
#   6. Bedrock AgentCore Runtime for the browser agent
#   7. ECS Fargate service + ALB for the gateway
#   8. CloudFront distribution + private S3 bucket for the UI
#
# Container images must exist in ECR before the AgentCore Runtime and ECS
# service resources can succeed. The recommended workflow is:
#   a. terraform apply -target=module.browser_agent_ecr -target=module.gateway_ecr
#   b. Build & push images using scripts/docker_build_ecr.sh
#   c. terraform apply (full stack)
#
# After apply, deploy the UI with scripts/deploy-ui.sh.
# =============================================================================

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.region

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    Stack       = "browser-agent-blog-all"
  }

  # ECR repository names — keep stable so developers can build + push independently.
  browser_agent_ecr_name = "${var.project_name}-browser-agent"
  gateway_ecr_name       = "${var.project_name}-gateway"

  # Image references — digest pin wins when set; otherwise fall back to the
  # mutable tag. Digest format produces `repo@sha256:...` (immutable, what
  # AgentCore + ECS will pull); tag format produces `repo:tag` (mutable,
  # rolled by `force-new-deployment` or `update-agent-runtime`).
  browser_agent_image_ref = (
    var.browser_agent_image_digest != ""
    ? "@${var.browser_agent_image_digest}"
    : ":${var.browser_agent_image_tag}"
  )
  gateway_image_ref = (
    var.gateway_image_digest != ""
    ? "@${var.gateway_image_digest}"
    : ":${var.gateway_image_tag}"
  )

  browser_agent_container_uri = "${local.account_id}.dkr.ecr.${local.region}.amazonaws.com/${local.browser_agent_ecr_name}${local.browser_agent_image_ref}"
  gateway_container_uri       = "${local.account_id}.dkr.ecr.${local.region}.amazonaws.com/${local.gateway_ecr_name}${local.gateway_image_ref}"

  # S3 session bucket name — blog pattern, includes account + region for uniqueness.
  session_bucket_name = "${var.project_name}-sessions-${local.account_id}-${local.region}"

  # CloudFront UI bucket name.
  ui_bucket_name = "${var.project_name}-ui-${local.account_id}-${local.region}"

  # CloudWatch log group for the gateway.
  gateway_log_group_name = "/ecs/${var.project_name}-gateway"

  # Effective TLS cert ARN. Either Terraform requested one (when
  # manage_acm_certificate + gateway_public_hostname + route53_zone_id are
  # all set) or the user brought one via acm_certificate_arn.
  gateway_should_request_cert = (
    var.gateway_public_hostname != "" &&
    var.route53_zone_id != "" &&
    var.manage_acm_certificate &&
    var.acm_certificate_arn == ""
  )
  # Whether the gateway will have HTTPS once apply finishes. Computed from
  # input variables only (not resolved resource attributes) so it is knowable
  # at plan time — the ecs-fargate module's HTTPS listener uses this in a
  # count argument that must be statically resolvable.
  gateway_has_https = (
    var.acm_certificate_arn != "" || local.gateway_should_request_cert
  )
  effective_acm_certificate_arn = (
    local.gateway_should_request_cert
    ? aws_acm_certificate_validation.gateway[0].certificate_arn
    : var.acm_certificate_arn
  )

  # Public base URL used by the UI to reach the gateway. Single source of
  # truth for both the gateway_public_url output and the CSP connect-src.
  ui_gateway_public_url = (
    var.gateway_public_hostname != ""
    ? "https://${var.gateway_public_hostname}"
    : (
      local.gateway_has_https
      ? "https://${module.gateway.alb_dns_name}"
      : "http://${module.gateway.alb_dns_name}"
    )
  )

  # CloudFront origin used for the OAuth redirect URLs.
  ui_origin = "https://${module.ui.distribution_domain_name}"

  # Auto-derived OAuth redirect URLs for the SPA client. Users can extend
  # them via var.ui_callback_urls / var.ui_logout_urls (e.g. for localhost
  # during development); the auto-derived CloudFront URL is always included.
  ui_default_callback_url = "${local.ui_origin}/callback"
  ui_default_logout_url   = "${local.ui_origin}/login"

  effective_ui_callback_urls = distinct(concat(
    [local.ui_default_callback_url],
    var.ui_callback_urls,
  ))
  effective_ui_logout_urls = distinct(concat(
    [local.ui_default_logout_url],
    var.ui_logout_urls,
  ))

  # Browser-agent runtime env vars: caller-supplied map plus the
  # session-store bucket name (sourced from the module that creates it).
  # Caller-supplied values win on key conflicts.
  effective_environment_variables = merge(
    {
      BA_SESSION_STORE_BUCKET = module.session_bucket.bucket_name
    },
    var.environment_variables,
  )

  # Gateway env vars: caller-supplied map plus the AgentCore runtime ARN
  # and AgentCore endpoint. Caller wins on key conflicts.
  effective_gateway_environment_variables = merge(
    {
      BROWSER_AGENT_ARN          = module.browser_agent.agent_runtime_arn
      BROWSER_AGENTCORE_ENDPOINT = "bedrock-agentcore.${local.region}.amazonaws.com"
    },
    var.gateway_environment_variables,
  )

  # WebSocket origin for the CSP connect-src. Built from the custom hostname
  # variable only (not the ALB module output) to avoid a dependency cycle:
  # cognito -> ui (callbacks) -> gateway (ALB dns) -> browser_agent -> cognito.
  # wss:// only functions when a custom hostname is set; in HTTP-only dev mode
  # the browser cannot open the socket anyway, so an empty entry is harmless.
  ui_ws_origin = var.gateway_public_hostname != "" ? "wss://${var.gateway_public_hostname}" : ""

  # Content-Security-Policy for the UI distribution. Built from real
  # deployment origins so it is correct for any account/domain:
  #   - default-src 'self'                       — everything defaults to same-origin
  #   - connect-src: the gateway WebSocket, the Cognito discovery/jwks host,
  #     and the Cognito hosted-UI token/userinfo host
  #   - script-src 'self'                        — the webpack bundle only
  #   - style-src 'self' 'unsafe-inline'         — MUI/Emotion inject inline styles
  #   - img-src 'self' data: + S3               — pre-signed screenshot URLs render
  #   - font-src 'self' data:                    — bundled + data-URI fonts
  #   - frame-ancestors 'none'                   — clickjacking, pairs with X-Frame-Options
  # Cognito hosted-UI host, derived from the domain prefix + region rather
  # than the cognito module output — referencing the module output here
  # would create a cycle (cognito already depends on the CloudFront domain
  # for its callback URLs).
  cognito_hosted_ui_host = "${var.cognito_domain_prefix}.auth.${local.region}.amazoncognito.com"

  ui_content_security_policy = join(" ", [
    "default-src 'self';",
    "connect-src 'self' ${local.ui_ws_origin} https://cognito-idp.${local.region}.amazonaws.com https://${local.cognito_hosted_ui_host};",
    "script-src 'self';",
    "style-src 'self' 'unsafe-inline';",
    "img-src 'self' data: https://*.s3.amazonaws.com https://*.s3.${local.region}.amazonaws.com https://s3.${local.region}.amazonaws.com;",
    "font-src 'self' data:;",
    "frame-ancestors 'none';",
    "base-uri 'self';",
    "form-action 'self' https://${local.cognito_hosted_ui_host};",
  ])

  # Policies for the AgentCore runtime execution role — 8 JSON files in ./policies/
  # with the account / region / bucket / table placeholders templated in at apply
  # time. Each file carries a leading "_comment" key documenting its rationale;
  # that key is stripped before the policy object is handed to aws_iam_role_policy.
  agentcore_policy_files = {
    AgentCorePolicy  = templatefile("${path.module}/policies/agentcore-policy.json", {})
    BedrockPolicy    = templatefile("${path.module}/policies/bedrock-policy.json", {})
    BrowserPolicy    = templatefile("${path.module}/policies/browser-policy.json", {})
    CloudWatchPolicy = templatefile("${path.module}/policies/cloudwatch-policy.json", {})
    DynamoDBPolicy = templatefile("${path.module}/policies/dynamodb-session-policy.json", {
      account_id = local.account_id
      region     = local.region
    })
    EcrPolicy = templatefile("${path.module}/policies/ecr-policy.json", {
      repository_name = local.browser_agent_ecr_name
    })
    S3SessionPolicy = templatefile("${path.module}/policies/s3-session-policy.json", {
      bucket_name = local.session_bucket_name
    })
  }

  # Decode the policies and remove the documentation-only "_comment" key so IAM
  # receives a clean policy document.
  agentcore_policies = {
    for name, raw in local.agentcore_policy_files :
    name => { for k, v in jsondecode(raw) : k => v if k != "_comment" }
  }
}

# -----------------------------------------------------------------------------
# 1. Cognito User Pool
# -----------------------------------------------------------------------------
module "cognito" {
  source = "../../modules/cognito-user-pool"

  user_pool_name = "${var.project_name}-users"
  domain_prefix  = var.cognito_domain_prefix

  callback_urls = local.effective_ui_callback_urls
  logout_urls   = local.effective_ui_logout_urls

  create_ui_app_client  = true
  ui_app_client_name    = "${var.project_name}-ui"
  create_m2m_app_client = true
  m2m_app_client_name   = "${var.project_name}-m2m"

  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# 2. S3 Session-Store Bucket
# -----------------------------------------------------------------------------
module "session_bucket" {
  source = "../../modules/s3"

  bucket_name        = local.session_bucket_name
  versioning_enabled = false
  force_destroy      = var.session_bucket_force_destroy

  bucket_tags = local.common_tags
}

# -----------------------------------------------------------------------------
# 3. IAM — AgentCore Runtime Execution Role
# -----------------------------------------------------------------------------
# Uses raw aws_iam_role + aws_iam_role_policy resources rather than the iam
# module because Terraform cannot unify the list-element types for the 7
# heterogeneous AgentCore policies when passing them through the module's
# list(object({name, policy=any})) input.
resource "aws_iam_role" "agentcore_execution_role" {
  name = "${var.project_name}-agentcore-execution-role"
  assume_role_policy = jsonencode({
    for k, v in jsondecode(templatefile("${path.module}/policies/trust-policy.json", {})) :
    k => v if k != "_comment"
  })
  tags = local.common_tags
}

resource "aws_iam_role_policy" "agentcore_execution_inline" {
  for_each = local.agentcore_policies

  name   = each.key
  role   = aws_iam_role.agentcore_execution_role.name
  policy = jsonencode(each.value)
}

# -----------------------------------------------------------------------------
# 4. IAM — ECS Task Execution Role (ECR pull + CloudWatch Logs)
# -----------------------------------------------------------------------------
module "gateway_execution_role" {
  source = "../../modules/iam"

  role_name      = "${var.project_name}-gateway-execution-role"
  principal_name = "ecs-tasks.amazonaws.com"

  inline_policies = [
    for p in [
      {
        name = "EcrPull"
        policy = {
          Version = "2012-10-17"
          Statement = [
            {
              Sid    = "EcrPull"
              Effect = "Allow"
              Action = [
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:BatchCheckLayerAvailability",
              ]
              Resource = [
                "arn:aws:ecr:${local.region}:${local.account_id}:repository/${local.gateway_ecr_name}",
              ]
            },
            {
              Sid      = "EcrAuth"
              Effect   = "Allow"
              Action   = ["ecr:GetAuthorizationToken"]
              Resource = ["*"]
            },
          ]
        }
      },
      {
        name = "CloudWatchLogs"
        policy = {
          Version = "2012-10-17"
          Statement = [
            {
              Sid    = "CloudWatchLogs"
              Effect = "Allow"
              Action = [
                "logs:CreateLogStream",
                "logs:PutLogEvents",
              ]
              Resource = [
                "arn:aws:logs:${local.region}:${local.account_id}:log-group:${local.gateway_log_group_name}:*",
              ]
            },
          ]
        }
      },
      ] : {
      name   = p.name
      policy = jsondecode(jsonencode(p.policy))
    }
  ]

  role_tags = local.common_tags
}

# -----------------------------------------------------------------------------
# 5. IAM — ECS Task Role (minimal; NGINX container makes no AWS API calls)
# -----------------------------------------------------------------------------
module "gateway_task_role" {
  source = "../../modules/iam"

  role_name       = "${var.project_name}-gateway-task-role"
  principal_name  = "ecs-tasks.amazonaws.com"
  inline_policies = []

  role_tags = local.common_tags
}

# -----------------------------------------------------------------------------
# 6. ECR — browser-agent-container + gateway-container
# -----------------------------------------------------------------------------
module "browser_agent_ecr" {
  source = "../../modules/ecr-repository"

  ecr_name         = local.browser_agent_ecr_name
  ecr_force_delete = true
  common_tags      = local.common_tags
  ecr_tags         = local.common_tags
}

module "gateway_ecr" {
  source = "../../modules/ecr-repository"

  ecr_name         = local.gateway_ecr_name
  ecr_force_delete = true
  common_tags      = local.common_tags
  ecr_tags         = local.common_tags
}

# -----------------------------------------------------------------------------
# 7. CloudWatch log group for the gateway ECS tasks
# -----------------------------------------------------------------------------
# NOTE: The ecs-fargate module auto-creates its own log group using
# `/ecs/<task_family>`. This standalone log group is retained for documentation /
# alignment with the blog narrative but is NOT consumed by the gateway module —
# the module's internal log group is the one that backs the tasks.
module "gateway_log_group" {
  source = "../../modules/cloudwatch-log-group"

  loggroup_name     = "${local.gateway_log_group_name}-metadata"
  retention_in_days = 365
  tags              = local.common_tags
}

# -----------------------------------------------------------------------------
# 8. Bedrock AgentCore Runtime — browser agent
# -----------------------------------------------------------------------------
# Wires Cognito JWT authorizer using the discovery URL + UI client ID.
# The M2M client ID is also allowed so integration tests can authenticate.
# environment_variables is a pure passthrough per steering tech.md.
module "browser_agent" {
  source = "../../modules/bedrock-agentcore-runtime"

  agent_runtime_name = replace("${var.project_name}_browser_agent", "-", "_")
  description        = "Browser automation agent for the blog reference architecture"
  role_arn           = aws_iam_role.agentcore_execution_role.arn
  container_uri      = local.browser_agent_container_uri
  region             = local.region

  network_mode    = "PUBLIC"
  server_protocol = "HTTP"

  enable_custom_jwt_authorizer = true
  jwt_discovery_url            = module.cognito.discovery_url
  jwt_allowed_clients = compact([
    module.cognito.ui_app_client_id,
    module.cognito.m2m_app_client_id,
  ])
  request_header_allowlist = ["Authorization"]

  environment_variables = local.effective_environment_variables

  create_endpoint = false

  tags = local.common_tags

  # Eventual-consistency guard: Cognito hosted UI domain must be reachable
  # before AgentCore is allowed to fetch the OIDC discovery document.
  depends_on = [
    module.cognito,
  ]
}

# -----------------------------------------------------------------------------
# 9. ECS Fargate — gateway (NGINX reverse proxy in front of AgentCore Runtime)
# -----------------------------------------------------------------------------
module "gateway" {
  source = "../../modules/ecs-fargate"

  task_family        = "${var.project_name}-gateway"
  container_name     = "gateway"
  container_image    = local.gateway_container_uri
  task_role_arn      = module.gateway_task_role.role_arn
  execution_role_arn = module.gateway_execution_role.role_arn

  enable_service = true
  enable_alb     = true
  enable_https   = local.gateway_has_https

  container_port = 80
  cpu            = var.ecs_cpu
  memory         = var.ecs_memory
  desired_count  = var.gateway_desired_count

  vpc_id                 = var.vpc_id
  subnet_ids             = var.gateway_subnet_ids
  security_group_ids     = var.gateway_security_group_ids
  alb_subnets            = var.alb_subnet_ids
  alb_security_group_ids = var.alb_security_group_ids
  assign_public_ip       = var.alb_assign_public_ip

  certificate_arn   = local.effective_acm_certificate_arn
  health_check_path = "/health"

  environment_variables = local.effective_gateway_environment_variables

  tags = local.common_tags

  # Gateway needs ECR image + the AgentCore runtime to route to.
  depends_on = [
    module.gateway_ecr,
    module.browser_agent,
  ]
}

# -----------------------------------------------------------------------------
# 10. CloudFront + private S3 — UI
# -----------------------------------------------------------------------------
module "ui" {
  source = "../../modules/cloudfront-spa"

  distribution_name   = "${var.project_name}-ui"
  bucket_name         = local.ui_bucket_name
  price_class         = var.cloudfront_price_class
  acm_certificate_arn = var.cloudfront_acm_certificate_arn
  aliases             = var.cloudfront_aliases

  enable_security_headers = true
  content_security_policy = local.ui_content_security_policy

  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# 11. ACM certificate + Route 53 records for the gateway public hostname
# -----------------------------------------------------------------------------
# These resources only exist when the user opts into Terraform-managed TLS by
# setting gateway_public_hostname + route53_zone_id (and leaving
# acm_certificate_arn empty + manage_acm_certificate true). Without those, the
# ALB stays on the explicit acm_certificate_arn (if any) or HTTP-only.

resource "aws_acm_certificate" "gateway" {
  count             = local.gateway_should_request_cert ? 1 : 0
  domain_name       = var.gateway_public_hostname
  validation_method = "DNS"

  tags = local.common_tags

  lifecycle {
    create_before_destroy = true
  }
}

# DNS-validation CNAME record. Using for_each rather than count so plans stay
# stable even if AWS rotates the validation token.
resource "aws_route53_record" "gateway_cert_validation" {
  for_each = local.gateway_should_request_cert ? {
    for dvo in aws_acm_certificate.gateway[0].domain_validation_options :
    dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = var.route53_zone_id
}

resource "aws_acm_certificate_validation" "gateway" {
  count                   = local.gateway_should_request_cert ? 1 : 0
  certificate_arn         = aws_acm_certificate.gateway[0].arn
  validation_record_fqdns = [for r in aws_route53_record.gateway_cert_validation : r.fqdn]
}

# Public alias record pointing the gateway hostname at the ALB. Created
# whenever the user supplied both a hostname and a zone, regardless of
# whether Terraform requested the cert or the user brought one — both paths
# need DNS to point at the ALB.
resource "aws_route53_record" "gateway_alias" {
  count   = (var.gateway_public_hostname != "" && var.route53_zone_id != "") ? 1 : 0
  zone_id = var.route53_zone_id
  name    = var.gateway_public_hostname
  type    = "A"

  alias {
    name                   = module.gateway.alb_dns_name
    zone_id                = module.gateway.alb_zone_id
    evaluate_target_health = true
  }
}
