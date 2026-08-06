#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# =============================================================================
# Build Docker Image and Tag for ECR
# =============================================================================
# Builds the Browser Agent container image and tags it for ECR push.
#
# USAGE:
#   ./scripts/docker_build_ecr.sh
#
# ENVIRONMENT VARIABLES:
#   AWS_ACCOUNT_ID      - AWS account ID (auto-detected if not set)
#   AWS_REGION          - AWS region (default: us-west-2)
#   ECR_REPOSITORY_NAME - ECR repository name (default: browser-agent-container)
#   IMAGE_TAG           - Image tag (default: linux-arm64)
#   PLATFORM            - Docker platform (default: linux/arm64)
#   SCM_TOKEN_NAME      - SCM token name for private packages (optional)
#   SCM_TOKEN_SECRET    - SCM token secret for private packages (optional)
#   EXTRA_INDEX_URLS    - Comma-separated extra-index-url entries (optional)
#   TRUSTED_HOSTS       - Comma-separated trusted-host entries (optional)
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
ECR_REPOSITORY_NAME="${ECR_REPOSITORY_NAME:-browser-agent-container}"
IMAGE_TAG="${IMAGE_TAG:-linux-arm64}"
PLATFORM="${PLATFORM:-linux/arm64}"
SCM_TOKEN_NAME="${SCM_TOKEN_NAME:-}"
SCM_TOKEN_SECRET="${SCM_TOKEN_SECRET:-}"
EXTRA_INDEX_URLS="${EXTRA_INDEX_URLS:-}"
TRUSTED_HOSTS="${TRUSTED_HOSTS:-}"

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
echo "Browser Agent — Docker Build for ECR"
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

BUILD_ARGS="--platform $PLATFORM --build-arg LOG_LEVEL=${LOG_LEVEL:-DEBUG} --build-arg AWS_REGION=$AWS_REGION"

# Pass private registry build args (flag-based setup_pip.sh)
if [ -n "$SCM_TOKEN_NAME" ] && [ -n "$SCM_TOKEN_SECRET" ]; then
    BUILD_ARGS="$BUILD_ARGS --build-arg SCM_TOKEN_NAME=$SCM_TOKEN_NAME --build-arg SCM_TOKEN_SECRET=$SCM_TOKEN_SECRET"
    log_info "Private package registry: SCM token enabled"
fi

if [ -n "$EXTRA_INDEX_URLS" ]; then
    BUILD_ARGS="$BUILD_ARGS --build-arg EXTRA_INDEX_URLS=$EXTRA_INDEX_URLS"
    log_info "Extra index URLs: enabled"
fi

if [ -n "$TRUSTED_HOSTS" ]; then
    BUILD_ARGS="$BUILD_ARGS --build-arg TRUSTED_HOSTS=$TRUSTED_HOSTS"
    log_info "Trusted hosts: enabled"
fi

docker buildx build \
    --progress=plain \
    --no-cache \
    --provenance=false \
    $BUILD_ARGS \
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
