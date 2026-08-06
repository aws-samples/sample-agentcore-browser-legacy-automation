#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# =============================================================================
# Run Gateway Container Locally
# =============================================================================
# Runs the Concierge Gateway NGINX container locally with environment
# variables loaded from .env for development testing.
#
# USAGE:
#   ./scripts/docker_run.sh
#
# ENVIRONMENT VARIABLES:
#   CONTAINER_NAME      - Container name (default: concierge-gateway)
#   IMAGE_NAME          - Docker image name (default: gateway-container)
#   IMAGE_TAG           - Image tag (default: latest)
#   HOST_PORT           - Host port to bind (default: 8080)
#   CONTAINER_PORT      - Container port (default: 80)
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
CONTAINER_NAME="${CONTAINER_NAME:-concierge-gateway}"
IMAGE_NAME="${IMAGE_NAME:-gateway-container}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
HOST_PORT="${HOST_PORT:-8080}"
CONTAINER_PORT="${CONTAINER_PORT:-80}"

# Resolve project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_DIR/.env"

# Validate .env file exists
if [ ! -f "$ENV_FILE" ]; then
    log_error ".env file not found at $ENV_FILE"
    echo "Copy .env.sample to .env and configure your environment variables."
    exit 1
fi

echo "============================================================"
echo "Concierge Gateway — Local Docker Run"
echo "============================================================"
echo ""
echo "Configuration:"
echo "  Project Dir:    $PROJECT_DIR"
echo "  Container:      $CONTAINER_NAME"
echo "  Image:          ${IMAGE_NAME}:${IMAGE_TAG}"
echo "  Port Mapping:   ${HOST_PORT}:${CONTAINER_PORT}"
echo "  Env File:       $ENV_FILE"
echo ""

# =============================================================================
# Stop existing container if running
# =============================================================================
if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
    log_info "Stopping existing container: $CONTAINER_NAME"
    docker stop "$CONTAINER_NAME" > /dev/null 2>&1
    docker rm "$CONTAINER_NAME" > /dev/null 2>&1
    log_success "Existing container removed"
elif docker ps -aq -f name="$CONTAINER_NAME" | grep -q .; then
    log_info "Removing stopped container: $CONTAINER_NAME"
    docker rm "$CONTAINER_NAME" > /dev/null 2>&1
fi

# =============================================================================
# Run container
# =============================================================================
log_info "Starting container..."

docker run -d \
    --name "$CONTAINER_NAME" \
    --env-file "$ENV_FILE" \
    -p "${HOST_PORT}:${CONTAINER_PORT}" \
    "${IMAGE_NAME}:${IMAGE_TAG}"

log_success "Container started: $CONTAINER_NAME"

echo ""
echo "============================================================"
echo "Gateway Running!"
echo "============================================================"
echo ""
echo "Health check:  http://localhost:${HOST_PORT}/health"
echo "WebSocket:     ws://localhost:${HOST_PORT}/ws?token=JWT&profile=concierge"
echo ""
echo "Useful commands:"
echo "  docker logs -f $CONTAINER_NAME    # Follow logs"
echo "  docker stop $CONTAINER_NAME       # Stop container"
echo "  curl http://localhost:${HOST_PORT}/health  # Test health"
echo ""
