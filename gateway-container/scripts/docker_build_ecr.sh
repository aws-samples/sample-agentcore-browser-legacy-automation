#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# =============================================================================
# Build Docker Image and Tag for ECR
# =============================================================================
# Builds the Concierge Gateway container image and tags it for ECR push.
#
# USAGE:
#   ./scripts/docker_build_ecr.sh
#
# ENVIRONMENT VARIABLES:
#   AWS_ACCOUNT_ID      - AWS account ID (auto-detected if not set)
#   AWS_REGION          - AWS region (default: us-west-2)
#   ECR_REPOSITORY_NAME - ECR repository name (default: gateway-container)
#   IMAGE_TAG           - Image tag (default: latest)
#   PLATFORM            - Docker platform (default: linux/amd64)
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
IMAGE_TAG="${IMAGE_TAG:-latest}"
PLATFORM="${PLATFORM:-linux/amd64}"

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

ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
FULL_IMAGE="${ECR_URI}/${ECR_REPOSITORY_NAME}:${IMAGE_TAG}"

# =============================================================================
# Resolve project root (script lives in scripts/)
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "============================================================"
echo "Concierge Gateway — Docker Build for ECR"
echo "============================================================"
echo ""
echo "Configuration:"
echo "  Project Dir:    $PROJECT_DIR"
echo "  AWS Account:    $AWS_ACCOUNT_ID"
echo "  AWS Region:     $AWS_REGION"
echo "  ECR Repository: $ECR_REPOSITORY_NAME"
echo "  Image Tag:      $IMAGE_TAG"
echo "  Platform:       $PLATFORM"
echo "  Full Image:     $FULL_IMAGE"
echo ""

# =============================================================================
# Create ECR repository if it doesn't exist
# =============================================================================
log_info "Ensuring ECR repository exists..."
aws ecr describe-repositories \
    --repository-names "$ECR_REPOSITORY_NAME" \
    --region "$AWS_REGION" > /dev/null 2>&1 || \
aws ecr create-repository \
    --repository-name "$ECR_REPOSITORY_NAME" \
    --region "$AWS_REGION" \
    --image-scanning-configuration scanOnPush=true > /dev/null
log_success "ECR repository ready: $ECR_REPOSITORY_NAME"

# =============================================================================
# Build Docker image
# =============================================================================
log_info "Building Docker image..."

docker buildx build \
    --progress=plain \
    --no-cache \
    --provenance=false \
    --platform "$PLATFORM" \
    -t "${ECR_REPOSITORY_NAME}:${IMAGE_TAG}" \
    -t "$FULL_IMAGE" \
    "$PROJECT_DIR"

log_success "Image built: $FULL_IMAGE"

echo ""
echo "============================================================"
echo "Build Complete!"
echo "============================================================"
echo ""
echo "Local image:  ${ECR_REPOSITORY_NAME}:${IMAGE_TAG}"
echo "ECR image:    $FULL_IMAGE"
echo ""
echo "Next step — push to ECR:"
echo "  ./scripts/docker_push_ecr.sh"
echo ""
