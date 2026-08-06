# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Pytest configuration for browser-agent-container tests.
Configures logging to show only application component logs during test execution.
"""

import logging
import os
from pathlib import Path
import pkgutil
import pytest
from dotenv import load_dotenv

# Application logger prefixes that the test runner should surface at DEBUG level.
# Add the prefix of any helper library the container imports for logging.
APP_LOGGER_PREFIXES: tuple[str, ...] = (
    "agent",
    "agents",
    "handlers",
    "streaming",
    "tools",
    "utils",
    "models",
    "prompts",
)


def configure_logging():
    """
    Configure logging to show only application component logs.
    Filters out logs from other libraries like boto3, urllib, playwright, etc.
    """
    os.environ["LOG_LEVEL"] = "DEBUG"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)

    app_loggers = [
        name for _, name, _ in pkgutil.iter_modules()
        if name.startswith(APP_LOGGER_PREFIXES)
    ]
    for logger_name in app_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.propagate = True

    noisy_loggers = [
        "boto3", "botocore", "urllib3", "requests",
        "httpx", "httpcore", "starlette", "uvicorn",
        "websockets", "openai", "anthropic",
        "playwright", "asyncio",
    ]
    for logger_name in noisy_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)
        logger.propagate = False


@pytest.fixture(scope="class", autouse=True)
def load_env(request):
    """Load environment for testing.

    Unit tests: loads project root .env
    Integration tests: loads project root .env.dev first (with override),
        then tests/integration/.env.dev (with override) for test-specific vars.
        Falls back to .env.cicd for CI/CD pipelines.
    """
    conftest_dir = Path(__file__).resolve().parent

    test_path = str(request.node.fspath) if hasattr(request.node, 'fspath') else ""
    is_unit_test = "unit" in test_path or "/unit/" in test_path

    if is_unit_test:
        env_path = conftest_dir / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=True)
        return

    # Integration tests: load project root .env.dev (or .env.cicd) for BA_ vars
    env_dev_file = conftest_dir / ".env.dev"
    if not env_dev_file.exists():
        env_dev_file = conftest_dir / ".env.cicd"

    if env_dev_file.exists():
        load_dotenv(env_dev_file, override=True)
    else:
        env_file = conftest_dir / ".env"
        if env_file.exists():
            load_dotenv(env_file, override=True)

    # Then load tests/integration/.env.dev for test-specific vars
    integration_dir = conftest_dir / "tests" / "integration"
    integration_env_dev = integration_dir / ".env.dev"
    if integration_env_dev.exists():
        load_dotenv(integration_env_dev, override=True)


@pytest.fixture(scope="session", autouse=True)
def setup_logging():
    """Automatically configure logging for all test sessions."""
    configure_logging()


def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
