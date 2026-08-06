#!/usr/bin/env bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
#
# teardown.sh — safely destroy the Browser Agent blog reference-architecture
# stack. Prompts for explicit confirmation, empties the CloudFront and session
# S3 buckets (CloudFront origins can't be destroyed while they still hold
# objects), then runs `terraform destroy`.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

command -v aws >/dev/null 2>&1 || {
  echo "error: aws CLI is not installed." >&2
  exit 1
}
command -v jq >/dev/null 2>&1 || {
  echo "error: jq is not installed." >&2
  exit 1
}

# -----------------------------------------------------------------------------
# Confirmation prompt
# -----------------------------------------------------------------------------
echo "This will destroy every resource in the Browser Agent blog stack:"
echo "  - Cognito user pool (all users will be deleted)"
echo "  - AgentCore runtime"
echo "  - ECS Fargate service + ALB"
echo "  - CloudFront distribution + its S3 origin bucket contents"
echo "  - ECR repositories (all pushed container images will be deleted)"
echo "  - S3 session-store bucket contents"
echo ""
read -r -p "Type 'destroy' to continue: " CONFIRMATION
if [[ "${CONFIRMATION}" != "destroy" ]]; then
  echo "Aborted."
  exit 1
fi

# -----------------------------------------------------------------------------
# Read the bucket names from terraform state so we can empty them first
# -----------------------------------------------------------------------------
TF_OUTPUTS_JSON="$(terraform -chdir="${SCRIPT_DIR}" output -json 2>/dev/null || echo '{}')"

UI_BUCKET_NAME="$(echo "${TF_OUTPUTS_JSON}" | jq -r '.ui_bucket_name.value // empty')"
SESSIONS_BUCKET_NAME="$(echo "${TF_OUTPUTS_JSON}" | jq -r '.s3_sessions_bucket.value // empty')"

empty_bucket() {
  local bucket="$1"
  if [[ -z "${bucket}" ]]; then
    return 0
  fi
  if aws s3 ls "s3://${bucket}" >/dev/null 2>&1; then
    echo "==> Emptying s3://${bucket} ..."
    aws s3 rm "s3://${bucket}/" --recursive
  else
    echo "==> Bucket ${bucket} does not exist or is not accessible; skipping empty."
  fi
}

empty_bucket "${UI_BUCKET_NAME}"
empty_bucket "${SESSIONS_BUCKET_NAME}"

# -----------------------------------------------------------------------------
# Destroy
# -----------------------------------------------------------------------------
VAR_FILE="${SCRIPT_DIR}/terraform.tfvars"
if [[ ! -f "${VAR_FILE}" ]]; then
  echo "error: ${VAR_FILE} not found. Nothing to destroy." >&2
  exit 1
fi

echo "==> Running terraform destroy..."
terraform -chdir="${SCRIPT_DIR}" destroy -var-file="${VAR_FILE}" -auto-approve

echo ""
echo "Stack destroyed."
