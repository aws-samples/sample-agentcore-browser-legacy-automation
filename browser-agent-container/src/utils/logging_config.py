# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
AgentCore Runtime logging configuration for the Browser Agent.

Provides ``configure_agentcore_logging()`` which must be called once in
``agent.py`` after all imports complete. It fixes two independent issues
that suppress Python logging output from AgentCore Runtime's
``[runtime-logs]`` CloudWatch stream:

1. **stderr not captured after async** — AgentCore Runtime reliably
   captures ``stdout`` throughout the container lifecycle but captures
   ``stderr`` inconsistently after async operations begin (e.g. after
   the first ``await`` in the Starlette lifespan). Since
   ``utils.logging_helper`` calls ``logging.basicConfig(force=True)``
   without a ``stream`` parameter, the root handler defaults to
   ``sys.stderr`` and all ``get_logger()`` output is lost after
   startup.

   Fix: redirect the root handler's stream from stderr to stdout.

2. **OTEL LoggingHandler intercepts records** — When the container runs
   under ``opentelemetry-instrument``, the ADOT bootstrap can install an
   ``OTELLogHandler`` on the root logger that routes log records to the
   OTEL pipeline (``otel-rt-logs``) instead of stdout.

   Upstream issue: https://github.com/open-telemetry/opentelemetry-python/issues/2594

   Fix: set env var ``OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED=false``
   in Terraform environment variables. This prevents OTEL from installing
   its handler. The env var is documented here rather than applied in code
   because it must be set before ``opentelemetry-instrument`` bootstraps
   (i.e. before Python starts).

Usage::

    # In agent.py, after ALL imports:
    from utils.logging_config import configure_agentcore_logging
    configure_agentcore_logging()
"""

import logging
import sys
from typing import List


# Third-party loggers to silence at WARNING level.
# These emit verbose INFO output that clutters [runtime-logs].
# Add or remove entries as needed.
NOISY_LOGGERS: List[str] = [
    'botocore',
    'urllib3',
    'httpx',
    'a2a',
    'strands_tools',
    'strands.telemetry',
    'opentelemetry',
    'playwright',  # Browser-specific: Playwright emits verbose DEBUG during browser ops
]


def configure_agentcore_logging() -> None:
    """Configure Python logging for AgentCore Runtime.

    Must be called once in ``agent.py`` after all imports complete.
    This ensures ``utils.logging_helper``'s module-level
    ``basicConfig(force=True)`` has already executed, so the stderr →
    stdout redirect applied here is not overwritten.

    Actions:
        1. Redirect root logger's stderr ``StreamHandler`` to stdout.
        2. Silence noisy third-party loggers at WARNING level.
    """
    root = logging.getLogger()

    # Swap stderr → stdout on the root handler
    for handler in root.handlers:
        if (isinstance(handler, logging.StreamHandler)
                and getattr(handler, 'stream', None) is sys.stderr):
            handler.setStream(sys.stdout)

    # Silence noisy third-party loggers
    for name in NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
