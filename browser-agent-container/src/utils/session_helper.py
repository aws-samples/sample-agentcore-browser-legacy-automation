# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Boto3 session and client-config factories.

Provides:

* ``get_boto3_session()`` — returns a ``boto3.Session``. On local
  developer machines (macOS/Windows or VS Code dev containers) the
  session honors ``AWS_PROFILE``; in container/Lambda environments it
  uses the default credential chain.
* ``get_boto3_client_config()`` — returns a ``botocore.config.Config``
  that respects the ``BOTO3_*`` environment variables for timeouts,
  retries, and proxy settings. Optional caller-supplied ``Config`` is
  merged in (caller takes precedence).
"""
import json
import os
import sys
from typing import Optional

import boto3
from boto3 import Session
from botocore.config import Config

from utils.logging_helper import get_logger

logger = get_logger(__name__)


def is_local() -> bool:
    """Return True if running on a local developer machine.

    Treats macOS, Windows, and VS Code dev containers as local.
    """
    if sys.platform in ("win32", "darwin"):
        return True
    return os.environ.get("REMOTE_CONTAINERS") == "true"


def get_aws_region_name() -> str:
    """Return the AWS region from ``AWS_REGION``, defaulting to us-east-1."""
    env_region = os.environ.get("AWS_REGION")
    if env_region:
        return env_region
    logger.warning("AWS_REGION environment variable is not set. Defaulting to us-east-1")
    return "us-east-1"


def get_boto3_session() -> Session:
    """Create a ``boto3.Session`` appropriate for the runtime environment.

    On local developer machines the session uses ``AWS_PROFILE`` (or
    ``"default"`` if unset). In container/Lambda environments it uses
    the default credential chain — no profile lookup, no explicit
    region (boto3 picks it up from the standard env vars).
    """
    if is_local():
        profile_name = os.environ.get("AWS_PROFILE", "default")
        if not os.environ.get("AWS_PROFILE"):
            logger.debug(
                "AWS_PROFILE environment variable is not set. Using profile: %s",
                profile_name,
            )
        return boto3.Session(
            profile_name=profile_name,
            region_name=get_aws_region_name(),
        )

    return Session()


def get_boto3_client_config(config: Optional[Config] = None) -> Config:
    """Build a ``botocore.config.Config`` with project-wide defaults.

    Reads optional environment variables:

    * ``BOTO3_CONNECT_TIMEOUT`` / ``BOTO3_READ_TIMEOUT`` (seconds, float)
    * ``BOTO3_PROXIES`` — JSON-like dict, e.g.
      ``{"http": "proxy:3128"}``. Single quotes are tolerated.
    * ``BOTO3_PROXY_CA_BUNDLE`` / ``BOTO3_PROXY_CLIENT_CERT`` /
      ``BOTO3_PROXY_USE_FORWARDING_FOR_HTTPS``
    * ``BOTO3_TOTAL_MAX_ATTEMPTS`` / ``BOTO3_MAX_ATTEMPTS`` (default 5)
    * ``BOTO3_RETRY_MODE`` (default ``"standard"``)

    If a caller supplies its own ``Config``, it is merged on top of the
    defaults — caller takes precedence on overlapping keys.
    """
    kwargs: dict = {}

    connect_timeout = os.environ.get("BOTO3_CONNECT_TIMEOUT")
    if connect_timeout:
        kwargs["connect_timeout"] = float(connect_timeout)

    read_timeout = os.environ.get("BOTO3_READ_TIMEOUT")
    if read_timeout:
        kwargs["read_timeout"] = float(read_timeout)

    proxies_string = os.environ.get("BOTO3_PROXIES")
    if proxies_string:
        try:
            kwargs["proxies"] = json.loads(proxies_string.replace("'", '"'))
        except json.JSONDecodeError:
            logger.warning("BOTO3_PROXIES is set but not valid JSON; ignoring")

    proxies_config = {
        k: v
        for k, v in {
            "proxy_ca_bundle": os.environ.get("BOTO3_PROXY_CA_BUNDLE"),
            "proxy_client_cert": os.environ.get("BOTO3_PROXY_CLIENT_CERT"),
            "proxy_use_forwarding_for_https": os.environ.get(
                "BOTO3_PROXY_USE_FORWARDING_FOR_HTTPS"
            ),
        }.items()
        if v is not None
    }
    if proxies_config:
        kwargs["proxies_config"] = proxies_config

    retries = {
        "max_attempts": int(os.environ.get("BOTO3_MAX_ATTEMPTS", "5")),
        "mode": os.environ.get("BOTO3_RETRY_MODE", "standard"),
    }
    total_max = os.environ.get("BOTO3_TOTAL_MAX_ATTEMPTS")
    if total_max:
        retries["total_max_attempts"] = int(total_max)
    kwargs["retries"] = retries

    base_config = Config(**kwargs)

    if config:
        return base_config.merge(config)
    return base_config
