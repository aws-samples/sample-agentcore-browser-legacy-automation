# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# =============================================================================
# Network bootstrap stack — Variables
# =============================================================================

# -----------------------------------------------------------------------------
# AWS provider
# -----------------------------------------------------------------------------
variable "aws_region" {
  description = "AWS region into which networking resources are deployed."
  type        = string
  default     = "us-west-2"
}

variable "aws_profile" {
  description = "AWS CLI profile to use (empty string = default credential chain)."
  type        = string
  default     = ""
}

# -----------------------------------------------------------------------------
# Project metadata + tagging
# -----------------------------------------------------------------------------
variable "project_name" {
  description = "Short project identifier used to name and tag resources."
  type        = string
  default     = "browser-agent-blog"
}

variable "environment" {
  description = "Environment tag applied to all resources (dev | staging | prod)."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

# -----------------------------------------------------------------------------
# CIDRs + AZs
# -----------------------------------------------------------------------------
variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "AZs to spread subnets across. Must be exactly 2 (public + private subnet per AZ)."
  type        = list(string)
  default     = ["us-west-2a", "us-west-2b"]

  validation {
    condition     = length(var.availability_zones) == 2
    error_message = "availability_zones must contain exactly 2 entries."
  }
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for the public subnets (ALB). One per AZ, same order as availability_zones."
  type        = list(string)
  default     = ["10.0.0.0/24", "10.0.1.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for the private subnets (Fargate tasks). One per AZ, same order as availability_zones."
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}

# -----------------------------------------------------------------------------
# Security groups
# -----------------------------------------------------------------------------
variable "enable_http_redirect" {
  description = "Open port 80 on the ALB security group so the ALB's HTTP listener can 301-redirect visitors to HTTPS. Left false by default for HTTPS-only, which avoids a public 0.0.0.0/0 rule on port 80 (Checkov CKV_AWS_260). Set true if you want plain http:// URLs to auto-redirect to https://."
  type        = bool
  default     = false
}
