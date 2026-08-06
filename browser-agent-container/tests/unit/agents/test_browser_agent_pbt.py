# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Feature: 86-browser-agent-core-tools, Property 10: BrowserAgentFactory applies environment variable defaults
"""Property-based test: BrowserAgentFactory applies environment variable defaults.

Validates: Requirements 6.1
"""

import tests.__setup__  # noqa: F401
import os
import unittest
from unittest.mock import patch, MagicMock

from hypothesis import given, settings, strategies as st

from agents.browser_agent import BrowserAgentFactory


# The three env vars and their defaults
ENV_VARS = {
    "AWS_DEFAULT_REGION": "us-west-2",
    "BA_BROWSER_MODEL_ID": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "BA_SESSION_TIMEOUT": "3600",
}

# Strategy: generate a subset of env var keys to OMIT (power set of 3 keys)
env_var_subsets = st.frozensets(st.sampled_from(list(ENV_VARS.keys())))


class TestPropertyBrowserAgentFactoryDefaults(unittest.TestCase):
    """Property 10: For any subset of env vars that are absent, factory uses correct defaults."""

    @given(omitted_keys=env_var_subsets)
    @settings(max_examples=100)
    def test_prop_factory_env_defaults(self, omitted_keys: frozenset) -> None:
        """For any subset of omitted env vars, factory applies the correct defaults."""
        # Build env dict with only the keys NOT in omitted_keys
        custom_values = {
            "AWS_DEFAULT_REGION": "ap-northeast-1",
            "BA_BROWSER_MODEL_ID": "custom-model-v2",
            "BA_SESSION_TIMEOUT": "900",
        }
        env = {
            k: custom_values[k]
            for k in ENV_VARS
            if k not in omitted_keys
        }

        with patch.dict("os.environ", env, clear=True):
            factory = BrowserAgentFactory()

            # Check region
            if "AWS_DEFAULT_REGION" in omitted_keys:
                self.assertEqual(factory.region, "us-west-2")
            else:
                self.assertEqual(factory.region, "ap-northeast-1")

            # Check model_id
            if "BA_BROWSER_MODEL_ID" in omitted_keys:
                self.assertEqual(
                    factory.model_id,
                    "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
                )
            else:
                self.assertEqual(factory.model_id, "custom-model-v2")

            # Check session_timeout
            if "BA_SESSION_TIMEOUT" in omitted_keys:
                self.assertEqual(factory.session_timeout, 3600)
            else:
                self.assertEqual(factory.session_timeout, 900)


if __name__ == "__main__":
    unittest.main()
