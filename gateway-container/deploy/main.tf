# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Concierge Gateway Container — ECS Fargate + ALB Deployment
# Uses ecs-fargate module for service + ALB, iam module for task/execution roles

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

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  account_id      = data.aws_caller_identity.current.account_id
  container_image = "${var.aws_account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${var.ecr_repository_name}:${var.image_tag}"

  common_tags = {
    Project     = "Concierge-Gateway"
    Component   = "Gateway"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ---------------------------------------------------------------------------
# IAM — ECS Task Execution Role (ECR pull + CloudWatch logs)
# ---------------------------------------------------------------------------
module "execution_role" {
  source = "../../deployment/terraform/modules/iam"

  role_name      = "${var.task_role_name}-execution"
  principal_name = "ecs-tasks.amazonaws.com"

  inline_policies = [
    {
      name = "EcrPullPolicy"
      policy = {
        Version = "2012-10-17"
        Statement = [
          {
            Sid    = "EcrPull"
            Effect = "Allow"
            Action = [
              "ecr:GetDownloadUrlForLayer",
              "ecr:BatchGetImage",
              "ecr:BatchCheckLayerAvailability"
            ]
            Resource = [
              "arn:aws:ecr:${var.aws_region}:${var.aws_account_id}:repository/${var.ecr_repository_name}"
            ]
          },
          {
            Sid    = "EcrAuth"
            Effect = "Allow"
            Action = [
              "ecr:GetAuthorizationToken"
            ]
            Resource = ["*"]
          }
        ]
      }
    },
    {
      name = "CloudWatchLogsPolicy"
      policy = {
        Version = "2012-10-17"
        Statement = [
          {
            Sid    = "CloudWatchLogs"
            Effect = "Allow"
            Action = [
              "logs:CreateLogStream",
              "logs:PutLogEvents"
            ]
            Resource = [
              "arn:aws:logs:${var.aws_region}:${var.aws_account_id}:log-group:/ecs/${var.task_family}:*"
            ]
          }
        ]
      }
    }
  ]

  role_tags = local.common_tags
}

# ---------------------------------------------------------------------------
# IAM — ECS Task Role (minimal — NGINX container makes no AWS API calls)
# ---------------------------------------------------------------------------
module "task_role" {
  source = "../../deployment/terraform/modules/iam"

  role_name      = var.task_role_name
  principal_name = "ecs-tasks.amazonaws.com"

  inline_policies = []

  role_tags = local.common_tags
}

# ---------------------------------------------------------------------------
# ECS Fargate + ALB
# ---------------------------------------------------------------------------
module "gateway" {
  source = "../../deployment/terraform/modules/ecs-fargate"

  # Service pattern
  enable_service = true
  enable_alb     = true
  enable_https   = true

  # Container configuration
  container_name  = var.container_name
  container_image = local.container_image
  container_port  = 80
  task_family     = var.task_family

  # Resources
  cpu           = 256
  memory        = 512
  desired_count = 2

  # IAM
  task_role_arn      = module.task_role.role_arn
  execution_role_arn = module.execution_role.role_arn

  # Networking
  vpc_id                 = var.vpc_id
  subnet_ids             = var.subnet_ids
  security_group_ids     = var.security_group_ids
  alb_subnets            = var.alb_subnets
  alb_security_group_ids = var.alb_security_group_ids
  assign_public_ip       = var.assign_public_ip

  # TLS
  certificate_arn = var.certificate_arn

  # Health check
  health_check_path = "/health"

  # Environment variables — passthrough map pattern
  environment_variables = var.environment_variables

  tags = local.common_tags
}
