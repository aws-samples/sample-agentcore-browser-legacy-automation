# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Pytest configuration for gateway-container tests."""

import os
import sys

from dotenv import load_dotenv
from pathlib import Path
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


@pytest.fixture(scope="class", autouse=True)
def load_env(request):
    """Load environment for testing.

    Unit tests: loads project root .env
    Integration tests: loads project root .env then .env.dev (last wins)
    """
    conftest_dir = Path(__file__).resolve().parent

    test_path = str(request.node.fspath) if hasattr(request.node, 'fspath') else ""
    is_unit_test = "unit" in test_path or "/unit/" in test_path

    if is_unit_test:
        env_path = conftest_dir / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=True)
        return

    # Integration tests: load .env first, then .env.dev overrides
    env_file = conftest_dir / ".env"
    env_dev_file = conftest_dir / ".env.dev"

    if env_file.exists():
        load_dotenv(env_file, override=True)
    if env_dev_file.exists():
        load_dotenv(env_dev_file, override=True)
