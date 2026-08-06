# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Configuration validator for the Browser Agent container.

Validates BA_ prefixed environment variables at startup, ensuring required
variables are present, numeric variables contain valid integer values,
session store type is valid, and conditional dependencies are satisfied.

Validates: Requirements 3.1–3.8, 11.1–11.10
"""

import os
from logging import Logger
from typing import Dict, List

from utils.logging_helper import get_logger


class ConfigValidator:
    """Validates BA_ environment variables for the Browser Agent.

    Validates required environment variables, optional variables with defaults,
    numeric constraints, session store type, and conditional store dependencies.
    Logs a configuration summary at startup.

    Environment variable prefix convention:
        BA_ = Browser Agent (NOT SA_ which is for Strands Agent concierge)
    """

    logger: Logger = get_logger(f"{__name__}.ConfigValidator")

    # Required variables — startup fails if missing
    REQUIRED_VARS: List[str] = [
        'AWS_DEFAULT_REGION',
    ]

    # Optional variables with their default values
    OPTIONAL_VARS_WITH_DEFAULTS: Dict[str, str] = {
        'BA_BROWSER_MODEL_ID': 'us.anthropic.claude-sonnet-4-5-20250929-v1:0',
        'BA_SESSION_TIMEOUT': '3600',
        'BA_SESSIONS_DIR': 'sessions',
        'BA_MAX_STEPS_PER_SESSION': '100',
        'BA_DISCONNECT_GRACE_SECONDS': '30',
        'BA_HITL_TIMEOUT_SECONDS': '300',
        'BA_SCREENSHOT_URL_EXPIRY_MINUTES': '240',
        'BA_SESSION_STORE_TYPE': 'memory',
        'BA_SESSION_STORE_PREFIX': 'browser-sessions',
        'LOG_LEVEL': 'INFO',
    }

    # Numeric variables that must parse as int
    NUMERIC_VARS: List[str] = [
        'BA_SESSION_TIMEOUT',
        'BA_MAX_STEPS_PER_SESSION',
        'BA_DISCONNECT_GRACE_SECONDS',
        'BA_HITL_TIMEOUT_SECONDS',
        'BA_SCREENSHOT_URL_EXPIRY_MINUTES',
    ]

    # Valid session store backend types
    VALID_STORE_TYPES: List[str] = ['memory', 'dynamodb', 's3']

    @classmethod
    def validate_and_log(cls) -> None:
        """Validate configuration and log summary. Raises ValueError on failure.

        Checks:
            1. All REQUIRED_VARS are present and non-empty in os.environ
            2. All NUMERIC_VARS contain valid integer strings
            3. BA_SESSION_STORE_TYPE is one of VALID_STORE_TYPES
            4. Conditional: BA_SESSION_STORE_TABLE required when type=dynamodb
            5. Conditional: BA_SESSION_STORE_BUCKET required when type=dynamodb or s3
            6. Logs resolved values for all variables (masking sensitive ones)

        Raises:
            ValueError: If any validation check fails.
        """
        errors: List[str] = []

        # Validate required variables
        for var in cls.REQUIRED_VARS:
            if not os.environ.get(var):
                errors.append("Missing required: %s" % var)

        # Validate numeric variables
        for var in cls.NUMERIC_VARS:
            val = os.environ.get(var, cls.OPTIONAL_VARS_WITH_DEFAULTS.get(var, ''))
            if val:
                try:
                    int(val)
                except ValueError:
                    errors.append("%s must be numeric, got: %s" % (var, val))

        # Validate session store type
        store_type: str = os.environ.get(
            'BA_SESSION_STORE_TYPE',
            cls.OPTIONAL_VARS_WITH_DEFAULTS.get('BA_SESSION_STORE_TYPE', 'memory'),
        )
        if store_type not in cls.VALID_STORE_TYPES:
            errors.append(
                "BA_SESSION_STORE_TYPE must be one of %s, got: %s"
                % (cls.VALID_STORE_TYPES, store_type)
            )

        # Conditional validation: dynamodb requires table name
        if store_type == 'dynamodb':
            if not os.environ.get('BA_SESSION_STORE_TABLE'):
                errors.append(
                    "BA_SESSION_STORE_TABLE required when "
                    "BA_SESSION_STORE_TYPE=dynamodb"
                )

        # Conditional validation: dynamodb or s3 requires bucket
        if store_type in ('dynamodb', 's3'):
            if not os.environ.get('BA_SESSION_STORE_BUCKET'):
                errors.append(
                    "BA_SESSION_STORE_BUCKET required when "
                    "BA_SESSION_STORE_TYPE=%s" % store_type
                )

        if errors:
            for err in errors:
                cls.logger.error("Config error: %s", err)
            raise ValueError(
                "Configuration validation failed: %s" % '; '.join(errors)
            )

        # Log configuration summary
        cls.logger.info("=== Browser Agent Configuration ===")
        for var in cls.REQUIRED_VARS:
            cls.logger.info("  %s = %s", var, os.environ.get(var, ''))
        for var, default in cls.OPTIONAL_VARS_WITH_DEFAULTS.items():
            val = os.environ.get(var, default)
            display = '***' if 'SECRET' in var or 'TOKEN' in var else val
            cls.logger.info("  %s = %s (default: %s)", var, display, default)
        # Log conditional store vars if relevant
        if store_type == 'dynamodb':
            cls.logger.info(
                "  BA_SESSION_STORE_TABLE = %s",
                os.environ.get('BA_SESSION_STORE_TABLE', ''),
            )
        if store_type in ('dynamodb', 's3'):
            cls.logger.info(
                "  BA_SESSION_STORE_BUCKET = %s",
                os.environ.get('BA_SESSION_STORE_BUCKET', ''),
            )
        cls.logger.info("===================================")
