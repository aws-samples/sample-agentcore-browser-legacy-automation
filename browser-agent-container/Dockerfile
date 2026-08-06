# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Browser Agent Container — Amazon Linux 2023 base
# Default: AgentCore Runtime (port 8080) with OpenTelemetry instrumentation
# ECS override: docker run <image> python server.py
#
# Build Arguments:
#   SCM_TOKEN_NAME:    SCM token name for private package authentication
#   SCM_TOKEN_SECRET:  SCM token secret for private package authentication
#   EXTRA_INDEX_URLS:  Comma-separated extra-index-url entries for pip
#   TRUSTED_HOSTS:     Comma-separated trusted-host entries for pip
#   LOG_LEVEL:         Logging level (default: DEBUG)
#   AWS_REGION:        AWS region (default: us-west-2)
#
# Multi-stage layout:
#   Stage 1 (build):   Python 3.12 + pip + gcc + devel + setup_pip.sh +
#                      requirements.txt → /opt/venv.
#   Stage 2 (runtime): Python 3.12 only, COPY /opt/venv from build stage.
#                      No gcc, no pip, no SCM tokens, no perl.
#
# Usage:
#   docker build \
#     --build-arg SCM_TOKEN_NAME=$SCM_TOKEN_NAME \
#     --build-arg SCM_TOKEN_SECRET=$SCM_TOKEN_SECRET \
#     --build-arg EXTRA_INDEX_URLS=$EXTRA_INDEX_URLS \
#     --build-arg TRUSTED_HOSTS=$TRUSTED_HOSTS \
#     --platform linux/arm64 -t browser-agent:agentcore .
#
# IMPORTANT: Pass secrets via --build-arg at build time.
#            Do NOT hardcode secrets in this file.

# syntax=docker/dockerfile:1

# -----------------------------------------------------------------------------
# Stage 1 — build
# -----------------------------------------------------------------------------
FROM public.ecr.aws/amazonlinux/amazonlinux:2023 AS build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Apply AL2023 security updates and install the build toolchain. python3.12
# pulls in the runtime; python3.12-pip + python3.12-devel + gcc handle
# wheels that compile native extensions (cryptography, cffi, lxml, etc.).
RUN dnf -y upgrade --releasever=latest && \
    dnf -y install python3.12 python3.12-pip python3.12-devel gcc && \
    dnf clean all && rm -rf /var/cache/dnf

# Build the venv that will be carried into the runtime stage.
RUN python3.12 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

# Build args for private package registry — passed at build time, not hardcoded.
ARG SCM_TOKEN_NAME=""
ARG SCM_TOKEN_SECRET=""
ARG EXTRA_INDEX_URLS=""
ARG TRUSTED_HOSTS=""

# Copy scripts and setup pip.conf for private packages (generic flag-based pattern).
COPY scripts/ ./scripts/
RUN chmod 755 scripts/setup_pip.sh && \
    scripts/setup_pip.sh -t "${SCM_TOKEN_NAME}" -s "${SCM_TOKEN_SECRET}" \
                         -e "${EXTRA_INDEX_URLS}" -h "${TRUSTED_HOSTS}"

# Install Python dependencies into the venv.
# Note: Playwright Chromium is NOT installed locally — the browser runs on
# AgentCore Browser's remote microVM. We connect via CDP WebSocket. The
# playwright Python package (transitive dep of strands-agents-tools[use_browser])
# provides the async API and CDP client without needing a local browser binary.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir "aws-opentelemetry-distro>=0.10.1"

# Strip pip.conf so SCM tokens never reach the runtime stage.
RUN rm -f /etc/pip.conf

# -----------------------------------------------------------------------------
# Stage 2 — runtime
# -----------------------------------------------------------------------------
FROM public.ecr.aws/amazonlinux/amazonlinux:2023 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:${PATH}"

# Apply AL2023 security updates and install only the Python runtime —
# no pip, no gcc, no devel headers. AL2023 also ships curl-minimal in the
# base, which the HEALTHCHECK uses below. shadow-utils provides useradd
# (not present in the AL2023 minimal base) so the non-root user can be
# created.
RUN dnf -y upgrade --releasever=latest && \
    dnf -y install python3.12 shadow-utils && \
    dnf clean all && rm -rf /var/cache/dnf

WORKDIR /app

# Carry the prebuilt venv over from the build stage.
COPY --from=build /opt/venv /opt/venv

COPY pyproject.toml .
# Flatten src/ into /app/ — agent.py lives at /app/agent.py.
COPY src/ .

EXPOSE 8080

ARG LOG_LEVEL="DEBUG"
ARG AWS_REGION="us-west-2"
ENV LOG_LEVEL=${LOG_LEVEL} \
    AWS_REGION=${AWS_REGION} \
    AWS_DEFAULT_REGION=${AWS_REGION}

RUN useradd -m -u 1000 bedrock_agentcore || true
USER bedrock_agentcore

# Localhost-only health probe; uses AL2023's curl-minimal.
HEALTHCHECK --interval=30s --timeout=5s \
    CMD curl -fsS http://127.0.0.1:8080/ping || exit 1

# AgentCore Runtime: OpenTelemetry instrumented agent on port 8080.
# For ECS: override with "python server.py" via task definition or docker run.
CMD ["opentelemetry-instrument", "python", "agent.py"]
