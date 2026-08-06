# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

data "aws_region" "current" {}

locals {
  # Determine if VPC configuration is needed
  enable_vpc_config = var.network_mode == "VPC" && length(var.vpc_subnet_ids) > 0

  # Validate VPC configuration when VPC mode is selected
  vpc_validation_error = var.network_mode == "VPC" && (length(var.vpc_subnet_ids) == 0 || length(var.vpc_security_group_ids) == 0)

  # Determine if lifecycle configuration is needed
  enable_lifecycle_config = var.idle_runtime_session_timeout != null || var.max_lifetime != null

  # Determine if request header configuration is needed
  enable_request_header_config = length(var.request_header_allowlist) > 0

  # Endpoint configuration
  endpoint_name = var.endpoint_name != "" ? var.endpoint_name : "${var.agent_runtime_name}-endpoint"

  # Merge default tags with user-provided tags
  default_tags = {
    Name        = var.agent_runtime_name
    ManagedBy   = "terraform"
    Service     = "bedrock-agentcore"
    NetworkMode = var.network_mode
    Protocol    = var.server_protocol
  }

  merged_tags = merge(local.default_tags, var.tags)
}

# Validation for VPC configuration
resource "null_resource" "vpc_validation" {
  count = local.vpc_validation_error ? 1 : 0

  provisioner "local-exec" {
    command = "echo 'Error: VPC mode requires both vpc_subnet_ids and vpc_security_group_ids to be specified' && exit 1"
  }
}

# ----------------------------------------------------------
#              Bedrock AgentCore Runtime
# ----------------------------------------------------------
resource "aws_bedrockagentcore_agent_runtime" "this" {
  depends_on = [null_resource.vpc_validation]

  agent_runtime_name = var.agent_runtime_name
  description        = var.description != "" ? var.description : null
  role_arn           = var.role_arn

  # Dynamic authorization configuration
  # NOTE: Custom claims (customClaims) are NOT yet supported by the AWS Terraform provider.
  # Use the update-custom-claims.sh script post-deployment to configure custom claims.
  # See: browser-agent-container/deploy/agentcore/README.md
  dynamic "authorizer_configuration" {
    for_each = var.enable_custom_jwt_authorizer ? [1] : []
    content {
      custom_jwt_authorizer {
        discovery_url    = var.jwt_discovery_url
        allowed_audience = length(var.jwt_allowed_audience) > 0 ? var.jwt_allowed_audience : null
        allowed_clients  = length(var.jwt_allowed_clients) > 0 ? var.jwt_allowed_clients : null
      }
    }
  }

  # Agent runtime artifact configuration
  agent_runtime_artifact {
    container_configuration {
      container_uri = var.container_uri
    }
  }

  # Network configuration with VPC support
  network_configuration {
    network_mode = var.network_mode

    dynamic "network_mode_config" {
      for_each = local.enable_vpc_config ? [1] : []
      content {
        subnets         = var.vpc_subnet_ids
        security_groups = var.vpc_security_group_ids
      }
    }
  }

  # Protocol configuration
  protocol_configuration {
    server_protocol = var.server_protocol
  }

  # Lifecycle configuration
  dynamic "lifecycle_configuration" {
    for_each = local.enable_lifecycle_config ? [1] : []
    content {
      idle_runtime_session_timeout = var.idle_runtime_session_timeout
      max_lifetime                 = var.max_lifetime
    }
  }

  # Request header configuration
  dynamic "request_header_configuration" {
    for_each = local.enable_request_header_config ? [1] : []
    content {
      request_header_allowlist = var.request_header_allowlist
    }
  }

  # Environment variables
  environment_variables = length(var.environment_variables) > 0 ? var.environment_variables : null

  tags = local.merged_tags
}

# ----------------------------------------------------------
#              Agent Runtime Endpoint (Optional)
# ----------------------------------------------------------
resource "aws_bedrockagentcore_agent_runtime_endpoint" "this" {
  count = var.create_endpoint ? 1 : 0

  name                  = local.endpoint_name
  agent_runtime_id      = aws_bedrockagentcore_agent_runtime.this.agent_runtime_id
  description           = var.endpoint_description != "" ? var.endpoint_description : "Endpoint for ${var.agent_runtime_name}"
  agent_runtime_version = var.agent_runtime_version != "" ? var.agent_runtime_version : null
  region                = var.region != "" ? var.region : null

  tags = merge(local.merged_tags, {
    Name = local.endpoint_name
    Type = "endpoint"
  })
}
