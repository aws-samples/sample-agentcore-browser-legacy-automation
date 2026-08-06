#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# =============================================================================
# Create Security Groups for ALB and ECS
# =============================================================================
# Creates the required security groups for the Concierge Gateway:
#   1. ALB Security Group — allows inbound HTTPS (443) from anywhere
#   2. ECS Security Group — allows inbound HTTP (80) from ALB only
#
# USAGE:
#   ./deploy/create-security-groups.sh
#
# ENVIRONMENT VARIABLES:
#   AWS_REGION          - AWS region (default: us-west-2)
#   VPC_ID              - VPC ID (required)
#   PROJECT_NAME        - Project name for tagging (default: concierge-gateway)
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
PROJECT_NAME="${PROJECT_NAME:-concierge-gateway}"

if [ -z "${VPC_ID:-}" ]; then
    log_error "VPC_ID environment variable is required."
    echo "Usage: VPC_ID=vpc-xxx ./deploy/create-security-groups.sh"
    exit 1
fi

ALB_SG_NAME="${PROJECT_NAME}-alb-sg"
ECS_SG_NAME="${PROJECT_NAME}-ecs-sg"

echo "============================================================"
echo "Concierge Gateway — Create Security Groups"
echo "============================================================"
echo ""
echo "Configuration:"
echo "  AWS Region:     $AWS_REGION"
echo "  VPC ID:         $VPC_ID"
echo "  ALB SG Name:    $ALB_SG_NAME"
echo "  ECS SG Name:    $ECS_SG_NAME"
echo ""

# =============================================================================
# Helper: create or find security group
# =============================================================================
find_or_create_sg() {
    local sg_name="$1"
    local sg_description="$2"

    # Check if SG already exists
    local existing_sg
    existing_sg=$(aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=$sg_name" "Name=vpc-id,Values=$VPC_ID" \
        --region "$AWS_REGION" \
        --query 'SecurityGroups[0].GroupId' \
        --output text 2>/dev/null || echo "None")

    if [ "$existing_sg" != "None" ] && [ -n "$existing_sg" ]; then
        log_info "Security group already exists: $sg_name ($existing_sg)" >&2
        echo "$existing_sg"
        return 0
    fi

    # Create security group
    local sg_id
    sg_id=$(aws ec2 create-security-group \
        --group-name "$sg_name" \
        --description "$sg_description" \
        --vpc-id "$VPC_ID" \
        --region "$AWS_REGION" \
        --query 'GroupId' \
        --output text)

    # Tag the security group
    aws ec2 create-tags \
        --resources "$sg_id" \
        --region "$AWS_REGION" \
        --tags Key=Name,Value="$sg_name" \
               Key=Project,Value=Concierge-Gateway \
               Key=Component,Value=Gateway \
               Key=ManagedBy,Value=Script

    log_success "Created security group: $sg_name ($sg_id)" >&2
    echo "$sg_id"
}

# =============================================================================
# Create ALB Security Group
# =============================================================================
log_info "Creating ALB security group..."
ALB_SG_ID=$(find_or_create_sg "$ALB_SG_NAME" "Concierge Gateway ALB - allows HTTPS inbound")

# Add inbound rule: HTTPS (443) from anywhere
aws ec2 authorize-security-group-ingress \
    --group-id "$ALB_SG_ID" \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0 \
    --region "$AWS_REGION" 2>/dev/null || log_info "ALB HTTPS ingress rule already exists"

log_success "ALB security group configured: $ALB_SG_ID"

# =============================================================================
# Create ECS Security Group
# =============================================================================
log_info "Creating ECS security group..."
ECS_SG_ID=$(find_or_create_sg "$ECS_SG_NAME" "Concierge Gateway ECS - allows HTTP from ALB only")

# Add inbound rule: HTTP (80) from ALB security group only
aws ec2 authorize-security-group-ingress \
    --group-id "$ECS_SG_ID" \
    --protocol tcp \
    --port 80 \
    --source-group "$ALB_SG_ID" \
    --region "$AWS_REGION" 2>/dev/null || log_info "ECS HTTP ingress rule already exists"

log_success "ECS security group configured: $ECS_SG_ID"

echo ""
echo "============================================================"
echo "Security Groups Created!"
echo "============================================================"
echo ""
echo "ALB Security Group:  $ALB_SG_ID  ($ALB_SG_NAME)"
echo "ECS Security Group:  $ECS_SG_ID  ($ECS_SG_NAME)"
echo ""
echo "Add these to your terraform.tfvars:"
echo "  alb_security_group_ids = [\"$ALB_SG_ID\"]"
echo "  security_group_ids     = [\"$ECS_SG_ID\"]"
echo ""
