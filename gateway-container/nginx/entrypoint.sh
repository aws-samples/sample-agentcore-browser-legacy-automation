#!/bin/sh
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

set -e

# Required environment variables (single-profile gateway: browser only)
REQUIRED_VARS="BROWSER_AGENTCORE_ENDPOINT BROWSER_AGENT_ARN"

echo "=== Gateway Container Startup ==="

# Validate required environment variables
for var in $REQUIRED_VARS; do
    eval val=\$var
    if [ -z "$val" ]; then
        echo "ERROR: Required environment variable $var is not set"
        exit 1
    fi
    echo "  $var = [set]"
done

echo "=== Generating NGINX configuration ==="

# Substitute environment variables in template
envsubst '${BROWSER_AGENTCORE_ENDPOINT} ${BROWSER_AGENT_ARN}' \
    < /etc/nginx/templates/nginx.conf.template \
    > /etc/nginx/nginx.conf

echo "=== Validating NGINX configuration ==="
nginx -t

if [ $? -ne 0 ]; then
    echo "ERROR: NGINX configuration validation failed"
    exit 1
fi

echo "=== Starting NGINX ==="
exec "$@"
