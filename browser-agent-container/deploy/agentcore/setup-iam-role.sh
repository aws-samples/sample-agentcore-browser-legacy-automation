#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# =============================================================================
# Setup IAM Role for Browser Agent — AgentCore Runtime
# =============================================================================
#
# Creates or updates the IAM role required for the Browser Agent on
# AgentCore Runtime. If the role exists, policies are added/updated without
# removing existing ones. If the role doesn't exist, it is created with the
# trust policy.
#
# USAGE:
#   cd deploy/agentcore
#   ./setup-iam-role.sh
#
# ENVIRONMENT VARIABLES:
#   ROLE_NAME   - IAM role name (default: browser-agent-role)
#   AWS_PROFILE - AWS CLI profile (required)
#   AWS_REGION  - AWS region (required)
#
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# =============================================================================
# Configuration
# =============================================================================
ROLE_NAME="${ROLE_NAME:-browser-agent-role}"
AWS_PROFILE="${AWS_PROFILE:-}"
AWS_REGION="${AWS_REGION:-}"
POLICIES_DIR="policies"

# =============================================================================
# Helper Functions
# =============================================================================

log_info()    { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error()   { echo -e "${RED}❌ $1${NC}"; }

check_prerequisites() {
    log_info "Checking prerequisites..."

    local missing_vars=()
    [ -z "$AWS_PROFILE" ] && missing_vars+=("AWS_PROFILE")
    [ -z "$AWS_REGION" ]  && missing_vars+=("AWS_REGION")

    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        echo ""
        echo "Example usage:"
        echo "  export AWS_PROFILE=your-profile"
        echo "  export AWS_REGION=us-west-2"
        echo "  export ROLE_NAME=browser-agent-role  # optional"
        echo "  ./setup-iam-role.sh"
        exit 1
    fi

    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not found. Please install AWS CLI v2."
        exit 1
    fi

    if ! aws sts get-caller-identity --profile "$AWS_PROFILE" --region "$AWS_REGION" &> /dev/null; then
        log_error "AWS credentials not configured or invalid for profile: $AWS_PROFILE"
        exit 1
    fi

    if [ ! -d "$POLICIES_DIR" ]; then
        log_error "Policies directory not found: $POLICIES_DIR"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

role_exists() {
    aws iam get-role --role-name "$ROLE_NAME" --profile "$AWS_PROFILE" &> /dev/null
}

create_role() {
    log_info "Creating IAM role: $ROLE_NAME"

    if [ ! -f "$POLICIES_DIR/trust-policy.json" ]; then
        log_error "Trust policy not found: $POLICIES_DIR/trust-policy.json"
        exit 1
    fi

    aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document "file://$POLICIES_DIR/trust-policy.json" \
        --description "IAM role for AgentCore Runtime - Browser Agent" \
        --profile "$AWS_PROFILE" \
        --output json > /dev/null

    log_success "Role created: $ROLE_NAME"
}

attach_inline_policy() {
    local policy_name="$1"
    local policy_file="$2"

    if [ ! -f "$policy_file" ]; then
        log_warning "Policy file not found, skipping: $policy_file"
        return
    fi

    log_info "Attaching policy: $policy_name"

    aws iam put-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-name "$policy_name" \
        --policy-document "file://$policy_file" \
        --profile "$AWS_PROFILE"

    log_success "Attached: $policy_name"
}

list_attached_policies() {
    echo ""
    log_info "Listing attached inline policies:"
    aws iam list-role-policies \
        --role-name "$ROLE_NAME" \
        --profile "$AWS_PROFILE" \
        --output table

    echo ""
    log_info "Listing attached managed policies:"
    aws iam list-attached-role-policies \
        --role-name "$ROLE_NAME" \
        --profile "$AWS_PROFILE" \
        --output table 2>/dev/null || echo "  (none)"
}

get_role_arn() {
    aws iam get-role \
        --role-name "$ROLE_NAME" \
        --profile "$AWS_PROFILE" \
        --query 'Role.Arn' \
        --output text
}

# =============================================================================
# Main
# =============================================================================

main() {
    echo "============================================================"
    echo "Browser Agent — AgentCore IAM Role Setup"
    echo "============================================================"
    echo ""
    echo "Configuration:"
    echo "  Role Name:    $ROLE_NAME"
    echo "  AWS Profile:  $AWS_PROFILE"
    echo "  AWS Region:   $AWS_REGION"
    echo "  Policies Dir: $POLICIES_DIR"
    echo ""

    check_prerequisites

    if role_exists; then
        log_info "Role already exists: $ROLE_NAME"
        log_info "Adding/updating policies (existing policies will not be removed)"
    else
        log_info "Role does not exist. Creating..."
        create_role
    fi

    echo ""
    log_info "Attaching inline policies..."
    echo ""

    # Core policies (shared with all AgentCore containers)
    attach_inline_policy "ECRAccess"                "$POLICIES_DIR/ecr-policy.json"
    attach_inline_policy "BedrockAccess"            "$POLICIES_DIR/bedrock-policy.json"
    attach_inline_policy "CloudWatchAccess"         "$POLICIES_DIR/cloudwatch-policy.json"
    attach_inline_policy "AgentCoreAccess"          "$POLICIES_DIR/agentcore-policy.json"

    # Browser-specific: AgentCore Browser session management
    attach_inline_policy "BrowserAccess"            "$POLICIES_DIR/browser-policy.json"

    # Session persistence: S3 for screenshots + session data
    attach_inline_policy "S3SessionAccess"          "$POLICIES_DIR/s3-session-policy.json"

    # Session persistence: DynamoDB for session metadata
    attach_inline_policy "DynamoDBSessionAccess"    "$POLICIES_DIR/dynamodb-session-policy.json"

    list_attached_policies

    local role_arn
    role_arn=$(get_role_arn)

    echo ""
    echo "============================================================"
    echo "🎉 IAM Role Setup Complete!"
    echo "============================================================"
    echo ""
    echo "Role ARN (use in user-terraform.tfvars):"
    echo "  $role_arn"
    echo ""
    echo "Next steps:"
    echo "  1. cp terraform.tfvars.example user-terraform.tfvars"
    echo "  2. Set execution_role_arn to the role ARN above"
    echo "  3. terraform init"
    echo "  4. terraform apply -var-file=user-terraform.tfvars"
    echo ""
}

main "$@"
