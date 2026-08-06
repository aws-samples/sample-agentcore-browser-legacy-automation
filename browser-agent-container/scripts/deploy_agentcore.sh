#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# =============================================================================
# Deploy Browser Agent to AgentCore Runtime via Terraform
# =============================================================================
# Runs terraform init + apply against the deploy/agentcore/ configuration
# using user-terraform.tfvars (or a custom var file).
#
# USAGE:
#   ./scripts/deploy_agentcore.sh                          # default: user-terraform.tfvars
#   ./scripts/deploy_agentcore.sh my-custom.tfvars         # custom var file
#   PLAN_ONLY=true ./scripts/deploy_agentcore.sh           # plan without applying
#
# ENVIRONMENT VARIABLES:
#   PLAN_ONLY - Set to "true" to run plan only (default: false)
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error()   { echo -e "${RED}❌ $1${NC}"; }

# =============================================================================
# Configuration
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DEPLOY_DIR="$PROJECT_DIR/deploy/agentcore"
PLAN_ONLY="${PLAN_ONLY:-false}"

# Var file: first argument or default to user-terraform.tfvars
VAR_FILE="${1:-user-terraform.tfvars}"

echo "============================================================"
echo "Browser Agent — Terraform Deployment"
echo "============================================================"
echo ""
echo "Configuration:"
echo "  Deploy Dir: $DEPLOY_DIR"
echo "  Var File:   $VAR_FILE"
echo "  Plan Only:  $PLAN_ONLY"
echo ""

# =============================================================================
# Validate prerequisites
# =============================================================================
if ! command -v terraform &> /dev/null; then
    log_error "Terraform not found. Please install Terraform >= 1.0."
    exit 1
fi

if [ ! -d "$DEPLOY_DIR" ]; then
    log_error "Deploy directory not found: $DEPLOY_DIR"
    exit 1
fi

VAR_FILE_PATH="$DEPLOY_DIR/$VAR_FILE"
if [ ! -f "$VAR_FILE_PATH" ]; then
    log_error "Var file not found: $VAR_FILE_PATH"
    echo ""
    echo "Create one from the example:"
    echo "  cp $DEPLOY_DIR/terraform.tfvars.example $VAR_FILE_PATH"
    echo "  # Edit $VAR_FILE_PATH with your values"
    exit 1
fi

log_success "Prerequisites validated"

# =============================================================================
# Terraform init
# =============================================================================
log_info "Running terraform init..."
terraform -chdir="$DEPLOY_DIR" init
log_success "Terraform initialized"

# =============================================================================
# Terraform plan
# =============================================================================
log_info "Running terraform plan..."
terraform -chdir="$DEPLOY_DIR" plan -var-file="$VAR_FILE"

if [ "$PLAN_ONLY" = "true" ]; then
    echo ""
    log_info "Plan-only mode — skipping apply."
    exit 0
fi

# =============================================================================
# Terraform apply
# =============================================================================
echo ""
log_info "Running terraform apply..."
terraform -chdir="$DEPLOY_DIR" apply -auto-approve -var-file="$VAR_FILE"

echo ""
echo "============================================================"
echo "Deployment Complete!"
echo "============================================================"
echo ""
log_info "Terraform outputs:"
terraform -chdir="$DEPLOY_DIR" output
echo ""
