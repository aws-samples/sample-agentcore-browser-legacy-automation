#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# =============================================================================
# Create ECR Repository
# =============================================================================
# Creates the ECR repository for the Concierge Gateway container image
# with image scanning enabled and lifecycle policy for image cleanup.
#
# USAGE:
#   ./deploy/create-ecr-repository.sh
#
# ENVIRONMENT VARIABLES:
#   AWS_ACCOUNT_ID      - AWS account ID (auto-detected if not set)
#   AWS_REGION          - AWS region (default: us-west-2)
#   ECR_REPOSITORY_NAME - ECR repository name (default: gateway-container)
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_error()   { echo -e "${RED}❌ $1${NC}"; }

# =============================================================================
# Configuration
# =============================================================================
AWS_REGION="${AWS_REGION:-us-west-2}"
ECR_REPOSITORY_NAME="${ECR_REPOSITORY_NAME:-gateway-container}"

# Auto-detect AWS account ID
if [ -z "${AWS_ACCOUNT_ID:-}" ]; then
    log_info "Auto-detecting AWS Account ID..."
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    if [ -z "$AWS_ACCOUNT_ID" ]; then
        log_error "Failed to auto-detect AWS_ACCOUNT_ID. Ensure AWS credentials are configured."
        exit 1
    fi
    log_success "AWS Account ID: $AWS_ACCOUNT_ID"
fi

echo "============================================================"
echo "Concierge Gateway — Create ECR Repository"
echo "============================================================"
echo ""
echo "Configuration:"
echo "  AWS Account:    $AWS_ACCOUNT_ID"
echo "  AWS Region:     $AWS_REGION"
echo "  Repository:     $ECR_REPOSITORY_NAME"
echo ""

# =============================================================================
# Check if repository already exists
# =============================================================================
if aws ecr describe-repositories \
    --repository-names "$ECR_REPOSITORY_NAME" \
    --region "$AWS_REGION" > /dev/null 2>&1; then
    log_info "ECR repository already exists: $ECR_REPOSITORY_NAME"
    echo ""
    echo "Repository URI: ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY_NAME}"
    exit 0
fi

# =============================================================================
# Create ECR repository
# =============================================================================
log_info "Creating ECR repository..."

aws ecr create-repository \
    --repository-name "$ECR_REPOSITORY_NAME" \
    --region "$AWS_REGION" \
    --image-scanning-configuration scanOnPush=true \
    --image-tag-mutability MUTABLE \
    --tags Key=Project,Value=Concierge-Gateway Key=Component,Value=Gateway Key=ManagedBy,Value=Script

log_success "ECR repository created: $ECR_REPOSITORY_NAME"

# =============================================================================
# Set lifecycle policy (keep last 10 untagged images)
# =============================================================================
log_info "Setting lifecycle policy..."

aws ecr put-lifecycle-policy \
    --repository-name "$ECR_REPOSITORY_NAME" \
    --region "$AWS_REGION" \
    --lifecycle-policy-text '{
        "rules": [
            {
                "rulePriority": 1,
                "description": "Keep last 10 untagged images",
                "selection": {
                    "tagStatus": "untagged",
                    "countType": "imageCountMoreThan",
                    "countNumber": 10
                },
                "action": {
                    "type": "expire"
                }
            }
        ]
    }'

log_success "Lifecycle policy applied"

echo ""
echo "============================================================"
echo "ECR Repository Created!"
echo "============================================================"
echo ""
echo "Repository URI: ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY_NAME}"
echo ""
echo "Next step — build and push:"
echo "  ./scripts/docker_build_ecr.sh"
echo "  ./scripts/docker_push_ecr.sh"
echo ""
