#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# =============================================================================
# Push Docker Image to ECR
# =============================================================================
# Authenticates with ECR and pushes the Browser Agent container image.
# Pushes both a versioned tag and a platform tag (like concierge-agent-container).
# Outputs the image digest for use in terraform.tfvars (image_digest).
#
# USAGE:
#   ./scripts/docker_push_ecr.sh
#
# ENVIRONMENT VARIABLES:
#   AWS_ACCOUNT_ID      - AWS account ID (auto-detected if not set)
#   AWS_REGION          - AWS region (default: us-west-2)
#   AWS_PROFILE         - AWS profile (optional)
#   ECR_REPOSITORY_NAME - ECR repository name (default: browser-agent-container)
#   IMAGE_TAG           - Image tag (default: linux-arm64)
#   PLATFORM            - Docker platform (default: linux/arm64)
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

# Resolve project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

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

# =============================================================================
# Extract version from pyproject.toml
# =============================================================================
VERSION="latest"
if [ -f "$PROJECT_DIR/pyproject.toml" ]; then
    EXTRACTED=$(grep -E '^version\s*=\s*"[0-9]+\.[0-9]+\.[0-9]+"' "$PROJECT_DIR/pyproject.toml" | cut -d'"' -f2)
    if [ -n "$EXTRACTED" ]; then
        VERSION="$EXTRACTED"
    else
        log_info "Could not extract version from pyproject.toml, using 'latest'"
    fi
else
    log_info "pyproject.toml not found, using 'latest'"
fi

# =============================================================================
# Build tag names (version tag + platform tag)
# =============================================================================
PLATFORM_SUFFIX=$(echo "$PLATFORM" | tr '/' '-')

if [ "$PLATFORM" = "linux/amd64" ]; then
    VERSION_TAG="${ECR_URI}/${ECR_REPOSITORY_NAME}:${VERSION}"
    PLATFORM_TAG="${ECR_URI}/${ECR_REPOSITORY_NAME}:latest"
else
    VERSION_TAG="${ECR_URI}/${ECR_REPOSITORY_NAME}:${VERSION}-${PLATFORM_SUFFIX}"
    PLATFORM_TAG="${ECR_URI}/${ECR_REPOSITORY_NAME}:${PLATFORM_SUFFIX}"
fi

echo "============================================================"
echo "Browser Agent — Push to ECR"
echo "============================================================"
echo ""
echo "Configuration:"
echo "  AWS Account:    $AWS_ACCOUNT_ID"
echo "  AWS Region:     $AWS_REGION"
echo "  ECR Repository: $ECR_REPOSITORY_NAME"
echo "  Platform:       $PLATFORM"
echo "  Version:        $VERSION"
echo "  Version Tag:    $VERSION_TAG"
echo "  Platform Tag:   $PLATFORM_TAG"
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
# Authenticate with ECR
# =============================================================================
log_info "Authenticating with ECR..."
aws ecr get-login-password --region "$AWS_REGION" | \
    docker login --username AWS --password-stdin "$ECR_URI"
log_success "ECR authentication successful"

# =============================================================================
# Tag and push both tags
# =============================================================================
# The build script tags as ECR_REPOSITORY_NAME:IMAGE_TAG locally.
# Re-tag to version tag and platform tag for ECR.
LOCAL_IMAGE="${ECR_REPOSITORY_NAME}:${IMAGE_TAG}"

log_info "Tagging image..."
docker tag "$LOCAL_IMAGE" "$VERSION_TAG"
docker tag "$LOCAL_IMAGE" "$PLATFORM_TAG"

log_info "Pushing version tag: $VERSION_TAG"
docker push "$VERSION_TAG"

log_info "Pushing platform tag: $PLATFORM_TAG"
docker push "$PLATFORM_TAG"

log_success "Both tags pushed successfully"

# =============================================================================
# Retrieve and display image digest
# =============================================================================
log_info "Retrieving image digest..."
IMAGE_DIGEST=$(aws ecr describe-images \
    --repository-name "$ECR_REPOSITORY_NAME" \
    --image-ids imageTag="${IMAGE_TAG}" \
    --region "$AWS_REGION" \
    --query 'imageDetails[0].imageDigest' \
    --output text 2>/dev/null || true)

# Fallback: try the version-platform tag
if [ -z "$IMAGE_DIGEST" ] || [ "$IMAGE_DIGEST" = "None" ]; then
    IMAGE_DIGEST=$(aws ecr describe-images \
        --repository-name "$ECR_REPOSITORY_NAME" \
        --image-ids imageTag="${VERSION}-${PLATFORM_SUFFIX}" \
        --region "$AWS_REGION" \
        --query 'imageDetails[0].imageDigest' \
        --output text 2>/dev/null || true)
fi

echo ""
echo "============================================================"
echo "Push Complete!"
echo "============================================================"
echo ""
echo "Images pushed to ECR:"
echo "  - $VERSION_TAG"
echo "  - $PLATFORM_TAG"
echo ""

if [ -n "$IMAGE_DIGEST" ] && [ "$IMAGE_DIGEST" != "None" ]; then
    echo "============================================"
    echo "IMAGE DIGEST (for Terraform deployment):"
    echo "============================================"
    echo "image_digest = \"$IMAGE_DIGEST\""
    echo ""
    echo "Add this to your user-terraform.tfvars to deploy"
    echo "a new AgentCore version."
    echo "============================================"
else
    echo "WARNING: Could not fetch image digest"
fi

echo ""
echo "Next step — deploy to AgentCore:"
echo "  ./scripts/deploy_agentcore.sh"
echo ""
