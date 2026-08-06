#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# =============================================================================
# Update AgentCore Runtime with Custom JWT Claims — Browser Agent
# =============================================================================
#
# Configures custom JWT claims validation (e.g., Auth0 'azp' claim) on an
# existing AgentCore Runtime, working around the Terraform provider limitation
# (~> 6.18) that does not support the customClaims block.
#
# TWO-STEP DEPLOYMENT:
#   1. Terraform deploys basic JWT config (discovery URL, audience)
#   2. This script adds customClaims via AWS CLI
#
# USAGE:
#   cd deploy/agentcore
#   export AWS_REGION=us-west-2
#   export AWS_PROFILE=your-profile
#   export OIDC_DISCOVERY_URL=https://your-tenant.auth0.com/.well-known/openid-configuration
#   export JWT_AUDIENCE=https://your-api-audience
#   export JWT_CLIENT_ID=your-m2m-client-id
#   export JWT_CLAIM_NAME=azp   # optional, defaults to 'azp'
#   ./update-custom-claims.sh
#
# Adapted from: concierge-agent-container/deploy/agentcore/update-custom-claims.sh
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
AWS_REGION="${AWS_REGION:-}"
AWS_PROFILE="${AWS_PROFILE:-}"
OIDC_DISCOVERY_URL="${OIDC_DISCOVERY_URL:-}"
JWT_AUDIENCE="${JWT_AUDIENCE:-}"
JWT_CLIENT_ID="${JWT_CLIENT_ID:-}"
JWT_CLAIM_NAME="${JWT_CLAIM_NAME:-azp}"
RUNTIME_ID="${RUNTIME_ID:-}"

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
    [ -z "$AWS_REGION" ]          && missing_vars+=("AWS_REGION")
    [ -z "$AWS_PROFILE" ]         && missing_vars+=("AWS_PROFILE")
    [ -z "$OIDC_DISCOVERY_URL" ]  && missing_vars+=("OIDC_DISCOVERY_URL")
    [ -z "$JWT_AUDIENCE" ]        && missing_vars+=("JWT_AUDIENCE")
    [ -z "$JWT_CLIENT_ID" ]       && missing_vars+=("JWT_CLIENT_ID")

    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        echo ""
        echo "Example usage:"
        echo "  export AWS_REGION=us-west-2"
        echo "  export AWS_PROFILE=your-profile"
        echo "  export OIDC_DISCOVERY_URL=https://your-provider/.well-known/openid-configuration"
        echo "  export JWT_AUDIENCE=https://your-api-audience"
        echo "  export JWT_CLIENT_ID=your-m2m-client-id"
        echo "  export JWT_CLAIM_NAME=azp  # optional, defaults to 'azp'"
        echo "  ./update-custom-claims.sh"
        exit 1
    fi

    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not found. Please install AWS CLI v2."
        exit 1
    fi

    if ! command -v jq &> /dev/null; then
        log_error "jq not found. Please install jq."
        echo "  macOS: brew install jq"
        echo "  Linux: apt-get install jq"
        exit 1
    fi

    if ! aws sts get-caller-identity --profile "$AWS_PROFILE" --region "$AWS_REGION" &> /dev/null; then
        log_error "AWS credentials not configured or invalid for profile: $AWS_PROFILE"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

list_runtimes() {
    log_info "Listing AgentCore Runtimes..."

    local runtimes
    runtimes=$(aws bedrock-agentcore-control list-agent-runtimes \
        --profile "$AWS_PROFILE" \
        --region "$AWS_REGION" \
        --output json 2>/dev/null || echo '{"agentRuntimes":[]}')

    local count
    count=$(echo "$runtimes" | jq '.agentRuntimes | length')

    if [ "$count" -eq 0 ]; then
        log_warning "No AgentCore Runtimes found in region $AWS_REGION"
        return 1
    fi

    echo ""
    echo "Found $count runtime(s):"
    echo ""
    echo "$runtimes" | jq -r '.agentRuntimes[] | "  ID: \(.agentRuntimeId)\n  Name: \(.agentRuntimeName)\n  Status: \(.status)\n"'

    echo "$runtimes" | jq -r '.agentRuntimes[0].agentRuntimeId'
}

get_runtime_config() {
    local runtime_id="$1"

    echo -e "${BLUE}ℹ️  Getting current runtime configuration: $runtime_id${NC}" >&2

    local tmp_file
    tmp_file=$(mktemp)

    if ! aws bedrock-agentcore-control get-agent-runtime \
        --agent-runtime-id "$runtime_id" \
        --profile "$AWS_PROFILE" \
        --region "$AWS_REGION" \
        --output json > "$tmp_file" 2>&1; then
        echo -e "${RED}❌ AWS CLI command failed${NC}" >&2
        cat "$tmp_file" >&2
        rm -f "$tmp_file"
        exit 1
    fi

    local result
    result=$(cat "$tmp_file")
    rm -f "$tmp_file"

    if ! echo "$result" | jq . > /dev/null 2>&1; then
        echo -e "${RED}❌ Invalid JSON response from AWS CLI${NC}" >&2
        exit 1
    fi

    echo "$result"
}

update_runtime_with_custom_claims() {
    local runtime_id="$1"

    log_info "Fetching current runtime configuration..."

    local runtime_config
    runtime_config=$(get_runtime_config "$runtime_id")

    local container_uri
    container_uri=$(echo "$runtime_config" | jq -r '.agentRuntimeArtifact.containerConfiguration.containerUri')

    local role_arn
    role_arn=$(echo "$runtime_config" | jq -r '.roleArn')

    local status
    status=$(echo "$runtime_config" | jq -r '.status')

    local network_mode
    network_mode=$(echo "$runtime_config" | jq -r '.networkConfiguration.networkMode')

    local env_vars
    env_vars=$(echo "$runtime_config" | jq -c '.environmentVariables // {}')

    local server_protocol
    server_protocol=$(echo "$runtime_config" | jq -r '.protocolConfiguration.serverProtocol // "HTTP"')

    local request_header_allowlist
    request_header_allowlist=$(echo "$runtime_config" | jq -c '.requestHeaderConfiguration.requestHeaderAllowlist // []')

    local idle_timeout
    idle_timeout=$(echo "$runtime_config" | jq -r '.lifecycleConfiguration.idleRuntimeSessionTimeout // empty')

    local max_lifetime
    max_lifetime=$(echo "$runtime_config" | jq -r '.lifecycleConfiguration.maxLifetime // empty')

    local description
    description=$(echo "$runtime_config" | jq -r '.description // empty')

    echo ""
    echo "Current Runtime Configuration:"
    echo "  Container URI: $container_uri"
    echo "  Role ARN: $role_arn"
    echo "  Network Mode: $network_mode"
    echo "  Server Protocol: $server_protocol"
    echo "  Status: $status"
    echo "  Environment Variables: $(echo "$env_vars" | jq -r 'keys | length') variables"
    echo ""

    if [ "$status" != "READY" ]; then
        log_warning "Runtime is not in READY state (current: $status). Waiting..."
        sleep 5
    fi

    local authorizer_config
    authorizer_config=$(cat <<EOF
{
    "customJWTAuthorizer": {
        "discoveryUrl": "$OIDC_DISCOVERY_URL",
        "allowedAudience": ["$JWT_AUDIENCE"],
        "customClaims": [
            {
                "inboundTokenClaimName": "$JWT_CLAIM_NAME",
                "inboundTokenClaimValueType": "STRING",
                "authorizingClaimMatchValue": {
                    "claimMatchValue": {
                        "matchValueString": "$JWT_CLIENT_ID"
                    },
                    "claimMatchOperator": "EQUALS"
                }
            }
        ]
    }
}
EOF
)

    log_info "New authorizer configuration:"
    echo "$authorizer_config" | jq .
    echo ""

    local network_config
    if [ "$network_mode" == "VPC" ]; then
        local subnets
        subnets=$(echo "$runtime_config" | jq -c '.networkConfiguration.networkModeConfig.subnets')
        local security_groups
        security_groups=$(echo "$runtime_config" | jq -c '.networkConfiguration.networkModeConfig.securityGroups')
        network_config="{\"networkMode\": \"VPC\", \"networkModeConfig\": {\"subnets\": $subnets, \"securityGroups\": $security_groups}}"
    else
        network_config='{"networkMode": "PUBLIC"}'
    fi

    local protocol_config
    protocol_config="{\"serverProtocol\": \"$server_protocol\"}"

    log_info "Updating runtime with custom claims..."

    local cmd_args=()
    cmd_args+=(--agent-runtime-id "$runtime_id")
    cmd_args+=(--agent-runtime-artifact "{\"containerConfiguration\": {\"containerUri\": \"$container_uri\"}}")
    cmd_args+=(--role-arn "$role_arn")
    cmd_args+=(--network-configuration "$network_config")
    cmd_args+=(--authorizer-configuration "$authorizer_config")
    cmd_args+=(--protocol-configuration "$protocol_config")

    if [ "$env_vars" != "{}" ] && [ "$env_vars" != "null" ]; then
        cmd_args+=(--environment-variables "$env_vars")
    fi

    if [ "$request_header_allowlist" != "[]" ] && [ "$request_header_allowlist" != "null" ]; then
        cmd_args+=(--request-header-configuration "{\"requestHeaderAllowlist\": $request_header_allowlist}")
    fi

    if [ -n "$idle_timeout" ] || [ -n "$max_lifetime" ]; then
        local lifecycle_config="{"
        local first=true
        if [ -n "$idle_timeout" ]; then
            lifecycle_config+="\"idleRuntimeSessionTimeout\": $idle_timeout"
            first=false
        fi
        if [ -n "$max_lifetime" ]; then
            [ "$first" = false ] && lifecycle_config+=","
            lifecycle_config+="\"maxLifetime\": $max_lifetime"
        fi
        lifecycle_config+="}"
        cmd_args+=(--lifecycle-configuration "$lifecycle_config")
    fi

    if [ -n "$description" ]; then
        cmd_args+=(--description "$description")
    fi

    cmd_args+=(--profile "$AWS_PROFILE")
    cmd_args+=(--region "$AWS_REGION")
    cmd_args+=(--output json)

    local update_result
    update_result=$(aws bedrock-agentcore-control update-agent-runtime "${cmd_args[@]}" 2>&1) || {
        log_error "Update failed!"
        echo "$update_result"
        exit 1
    }

    echo ""
    log_success "Runtime updated successfully!"
    echo ""
    echo "Update Result:"
    echo "$update_result" | jq '{agentRuntimeId, agentRuntimeArn, status, agentRuntimeVersion}'
}

# =============================================================================
# Main
# =============================================================================

main() {
    echo "============================================================"
    echo "Browser Agent — Custom JWT Claims Updater"
    echo "============================================================"
    echo ""
    echo "Configuration:"
    echo "  AWS Region:          $AWS_REGION"
    echo "  AWS Profile:         $AWS_PROFILE"
    echo "  OIDC Discovery URL:  $OIDC_DISCOVERY_URL"
    echo "  JWT Audience:        $JWT_AUDIENCE"
    echo "  JWT Client ID:       $JWT_CLIENT_ID"
    echo "  JWT Claim Name:      $JWT_CLAIM_NAME"
    echo ""

    check_prerequisites

    if [ -z "$RUNTIME_ID" ]; then
        log_info "No RUNTIME_ID provided. Auto-detecting..."
        RUNTIME_ID=$(list_runtimes | tail -1)

        if [ -z "$RUNTIME_ID" ] || [ "$RUNTIME_ID" == "null" ]; then
            log_error "Could not auto-detect runtime ID. Set RUNTIME_ID env var."
            exit 1
        fi

        log_info "Auto-detected runtime ID: $RUNTIME_ID"
        echo ""
        read -p "Continue with this runtime? (y/N) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Aborted."
            exit 0
        fi
    fi

    update_runtime_with_custom_claims "$RUNTIME_ID"

    echo ""
    echo "============================================================"
    echo "🎉 Browser Agent now validates '$JWT_CLAIM_NAME' claim"
    echo "============================================================"
    echo ""
    echo "Next steps:"
    echo "  1. Test with your M2M token via wscat or the UI"
    echo "  2. Run integration tests:"
    echo "     cd ../../ && PYTHONPATH=src python -m pytest tests/integration/ -v"
    echo ""
}

main "$@"
