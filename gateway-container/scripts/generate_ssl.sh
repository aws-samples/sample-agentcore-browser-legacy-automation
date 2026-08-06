#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# =============================================================================
# Generate Self-Signed SSL Certificates
# =============================================================================
# Generates self-signed SSL certificates in nginx/ssl/ for local development.
# These certificates are git-ignored and should NOT be used in production.
#
# USAGE:
#   ./scripts/generate_ssl.sh
#
# ENVIRONMENT VARIABLES:
#   SSL_DAYS    - Certificate validity in days (default: 365)
#   SSL_CN      - Common Name (default: localhost)
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
SSL_DAYS="${SSL_DAYS:-365}"
SSL_CN="${SSL_CN:-localhost}"

# Resolve project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SSL_DIR="$PROJECT_DIR/nginx/ssl"

echo "============================================================"
echo "Concierge Gateway — Generate Self-Signed SSL Certificates"
echo "============================================================"
echo ""
echo "Configuration:"
echo "  Output Dir:   $SSL_DIR"
echo "  Validity:     $SSL_DAYS days"
echo "  Common Name:  $SSL_CN"
echo ""

# =============================================================================
# Ensure output directory exists
# =============================================================================
mkdir -p "$SSL_DIR"

# =============================================================================
# Check for existing certificates
# =============================================================================
if [ -f "$SSL_DIR/server.crt" ] && [ -f "$SSL_DIR/server.key" ]; then
    log_info "Existing certificates found in $SSL_DIR"
    read -p "Overwrite? (y/N): " CONFIRM
    if [ "${CONFIRM,,}" != "y" ]; then
        echo "Aborted."
        exit 0
    fi
fi

# =============================================================================
# Generate self-signed certificate
# =============================================================================
log_info "Generating self-signed certificate..."

openssl req -x509 \
    -nodes \
    -days "$SSL_DAYS" \
    -newkey rsa:2048 \
    -keyout "$SSL_DIR/server.key" \
    -out "$SSL_DIR/server.crt" \
    -subj "/C=CA/ST=Local/L=Dev/O=BlogReference/CN=$SSL_CN" \
    -addext "subjectAltName=DNS:localhost,DNS:$SSL_CN,IP:127.0.0.1"

# Set restrictive permissions on private key
chmod 600 "$SSL_DIR/server.key"
chmod 644 "$SSL_DIR/server.crt"

log_success "SSL certificates generated"

echo ""
echo "============================================================"
echo "SSL Generation Complete!"
echo "============================================================"
echo ""
echo "Files created:"
echo "  Certificate:  $SSL_DIR/server.crt"
echo "  Private Key:  $SSL_DIR/server.key"
echo ""
echo "WARNING: These are self-signed certificates for LOCAL"
echo "DEVELOPMENT ONLY. Do NOT use in production."
echo ""
echo "These files are git-ignored via .gitignore."
echo ""
