#!/usr/bin/env bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
#
# deploy-ui.sh — build the chat-bot UI with the stack's Cognito / gateway /
# CloudFront values, upload the `dist/` output to S3, and invalidate CloudFront.
#
# Prerequisites:
#   - `terraform apply` has succeeded in this directory
#   - yarn and aws-cli installed locally
#   - AWS credentials that can `s3 sync` + `cloudfront create-invalidation`
#
# Run from anywhere: the script resolves its own path.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
UI_DIR="${REPO_ROOT}/chat-bot-ui"

command -v yarn >/dev/null 2>&1 || {
  echo "error: yarn is not installed. Install Node.js + yarn first." >&2
  exit 1
}
command -v aws >/dev/null 2>&1 || {
  echo "error: aws CLI is not installed." >&2
  exit 1
}
command -v jq >/dev/null 2>&1 || {
  echo "error: jq is not installed." >&2
  exit 1
}

if [[ ! -d "${UI_DIR}" ]]; then
  echo "error: UI source not found at ${UI_DIR}" >&2
  exit 1
fi

# -----------------------------------------------------------------------------
# Read Terraform outputs
# -----------------------------------------------------------------------------
echo "==> Reading terraform outputs..."
TF_OUTPUTS_JSON="$(terraform -chdir="${SCRIPT_DIR}" output -json)"

CLOUDFRONT_DOMAIN="$(echo "${TF_OUTPUTS_JSON}" | jq -r '.cloudfront_domain.value')"
CLOUDFRONT_DISTRIBUTION_ID="$(echo "${TF_OUTPUTS_JSON}" | jq -r '.cloudfront_distribution_id.value')"
UI_BUCKET_NAME="$(echo "${TF_OUTPUTS_JSON}" | jq -r '.ui_bucket_name.value')"
COGNITO_AUTHORITY="$(echo "${TF_OUTPUTS_JSON}" | jq -r '.cognito_user_pool_issuer.value')"
UI_APP_CLIENT_ID="$(echo "${TF_OUTPUTS_JSON}" | jq -r '.ui_app_client_id.value')"
GATEWAY_PUBLIC_URL="$(echo "${TF_OUTPUTS_JSON}" | jq -r '.gateway_public_url.value')"

for var in CLOUDFRONT_DOMAIN CLOUDFRONT_DISTRIBUTION_ID UI_BUCKET_NAME COGNITO_AUTHORITY UI_APP_CLIENT_ID GATEWAY_PUBLIC_URL; do
  if [[ -z "${!var:-}" || "${!var}" == "null" ]]; then
    echo "error: required terraform output ${var} is empty. Did \`terraform apply\` finish successfully?" >&2
    exit 1
  fi
done

# The UI's buildWebSocketUrl appends "/ws?token=...&profile=browser" to
# the base URL, so __WEBSOCKET_URL__ must be the bare wss://host (no path).
# Convert https://host -> wss://host ; http://host -> ws://host.
if [[ "${GATEWAY_PUBLIC_URL}" == https://* ]]; then
  WEBSOCKET_URL="wss://${GATEWAY_PUBLIC_URL#https://}"
else
  WEBSOCKET_URL="ws://${GATEWAY_PUBLIC_URL#http://}"
  echo "warning: gateway is HTTP-only (${GATEWAY_PUBLIC_URL}). Browsers will refuse ws:// from an https:// origin." >&2
  echo "         Set gateway_public_hostname + route53_zone_id (or acm_certificate_arn) in terraform.tfvars to enable wss://." >&2
fi

echo "   CloudFront domain      : ${CLOUDFRONT_DOMAIN}"
echo "   UI bucket              : ${UI_BUCKET_NAME}"
echo "   Cognito authority      : ${COGNITO_AUTHORITY}"
echo "   UI app client ID       : ${UI_APP_CLIENT_ID}"
echo "   WebSocket URL          : ${WEBSOCKET_URL}"

# -----------------------------------------------------------------------------
# Build the UI with the resolved values as build-time constants
# -----------------------------------------------------------------------------
echo "==> Installing UI dependencies..."
yarn --cwd "${UI_DIR}" install --frozen-lockfile

echo "==> Building UI (webpack DefinePlugin picks up these env vars)..."
OIDC_AUTHORITY="${COGNITO_AUTHORITY}" \
  OIDC_CLIENT_ID="${UI_APP_CLIENT_ID}" \
  WEBSOCKET_URL="${WEBSOCKET_URL}" \
  PUBLIC_PATH="/" \
  yarn --cwd "${UI_DIR}" build

DIST_DIR="${UI_DIR}/dist"
if [[ ! -d "${DIST_DIR}" ]]; then
  echo "error: build output not found at ${DIST_DIR}" >&2
  exit 1
fi

# -----------------------------------------------------------------------------
# Upload to S3 + invalidate CloudFront
# -----------------------------------------------------------------------------
echo "==> Syncing ${DIST_DIR} to s3://${UI_BUCKET_NAME}/ ..."
aws s3 sync "${DIST_DIR}/" "s3://${UI_BUCKET_NAME}/" --delete

echo "==> Creating CloudFront invalidation..."
INVALIDATION_ID="$(
  aws cloudfront create-invalidation \
    --distribution-id "${CLOUDFRONT_DISTRIBUTION_ID}" \
    --paths '/*' \
    --query 'Invalidation.Id' \
    --output text
)"

echo ""
echo "UI deployed. Open: https://${CLOUDFRONT_DOMAIN}"
echo "CloudFront invalidation ID: ${INVALIDATION_ID} (may take a few minutes to propagate)."
