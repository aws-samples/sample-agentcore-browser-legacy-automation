# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Centralized logger factory.

Provides ``get_logger(module_name)`` — a thin wrapper around
``logging.getLogger`` that applies a project-wide format and honors
the ``LOG_LEVEL`` environment variable.

Module-level ``logging.basicConfig(force=True)`` ensures every logger
obtained through this helper inherits the same format regardless of
import order or any prior ``logging`` configuration.
"""
import logging
import os


# Project-wide log format. ``force=True`` overrides any prior root
# logger configuration (e.g. from third-party libraries imported
# earlier in the process).
_DEFAULT_LOG_ARGS = {
    "format": "[%(levelname)s] [%(name)s] %(message)s",
    "datefmt": "%d-%b-%y %H:%M",
    "force": True,
}

logging.basicConfig(**_DEFAULT_LOG_ARGS)


def get_logger(module_name: str) -> logging.Logger:
    """Return a logger for ``module_name`` with the project log format.

    The logger's level is taken from the ``LOG_LEVEL`` environment
    variable (case-insensitive). If unset or invalid, the level falls
    back to ``INFO``.

    Args:
        module_name: Fully-qualified logger name, typically
            ``f"{__name__}.{ClassName}"`` or ``__name__``.

    Returns:
        A configured ``logging.Logger`` instance.
    """
    logger = logging.getLogger(module_name)

    env_log_level = os.environ.get("LOG_LEVEL")
    if env_log_level:
        try:
            logger.setLevel(env_log_level.upper())
        except (ValueError, TypeError):
            logger.setLevel(logging.INFO)

    return logger
