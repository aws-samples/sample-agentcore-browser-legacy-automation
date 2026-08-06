# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# =============================================================================
# Browser Agent — AgentCore Runtime Deployment
# =============================================================================
# Deploys the Browser Automation Agent to Bedrock AgentCore Runtime.
# No Identity or Memory modules — uses pluggable SessionStore instead.
#
# Resources created:
#   1. AgentCore Runtime — container runtime for the browser agent
#
# Protocol: HTTP (WebSocket + HTTP on port 8080)
# Auth:     JWT authorization enabled by default
#
# Usage:
#   cp terraform.tfvars.example user-terraform.tfvars
#   # Edit user-terraform.tfvars with your values
#   terraform init
#   terraform plan  -var-file=user-terraform.tfvars
#   terraform apply -var-file=user-terraform.tfvars
# =============================================================================

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.18"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}

# -----------------------------------------------------------------------------
# Container URI — always use tag-based URI (AgentCore requires tag format)
# -----------------------------------------------------------------------------
locals {
  container_uri = "${var.aws_account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${var.ecr_repository_name}:${var.image_tag}"
}

# -----------------------------------------------------------------------------
# Bedrock AgentCore Runtime Module
# -----------------------------------------------------------------------------
# No Identity module (no A2A M2M auth needed)
# No Memory module (uses pluggable SessionStore — memory/DynamoDB/S3)
# -----------------------------------------------------------------------------
module "browser_agent" {
  source = "../../../deployment/terraform/modules/bedrock-agentcore-runtime"

  # Agent configuration (REQUIRED)
  agent_runtime_name = var.agent_name
  description        = var.agent_description
  role_arn           = var.execution_role_arn

  # Container configuration (REQUIRED)
  container_uri = local.container_uri
  region        = var.aws_region

  # Network configuration
  network_mode = var.network_mode

  # Protocol — HTTP for WebSocket + HTTP on port 8080
  server_protocol = var.server_protocol

  # JWT Authorization — enabled by default for OIDC integration testing
  enable_custom_jwt_authorizer = var.enable_jwt_authorizer
  jwt_discovery_url            = var.jwt_discovery_url
  jwt_allowed_audience         = var.jwt_allowed_audience
  jwt_allowed_clients          = var.jwt_allowed_clients

  # Forward Authorization header for JWT token
  request_header_allowlist = var.enable_jwt_authorizer ? ["Authorization"] : []

  # Passthrough map pattern — no assembly in main.tf
  environment_variables = var.environment_variables

  # Use DEFAULT endpoint (auto-created by AgentCore)
  create_endpoint = false

  tags = {
    Project     = "Browser-Agent"
    Component   = "BrowserAgent"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
