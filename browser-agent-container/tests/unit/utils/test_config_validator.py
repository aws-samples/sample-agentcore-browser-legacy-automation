# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Unit tests for ConfigValidator.

Validates: Requirements 4.1–4.7 (Spec 1), 16.9 (Spec 3)
"""

# pylint: disable=import-error,unused-import
try:
    import __setup__
except ModuleNotFoundError:
    import tests.unit.utils.__setup__
# pylint: enable=import-error,unused-import

import logging
import os
import unittest
from unittest.mock import patch

from utils.config_validator import ConfigValidator


class TestConfigValidator(unittest.TestCase):
    """Unit tests for ConfigValidator using unittest.mock.patch.dict."""

    # ------------------------------------------------------------------
    # Spec 1 tests (preserved)
    # ------------------------------------------------------------------

    @patch.dict(os.environ, {
        "AWS_DEFAULT_REGION": "us-west-2",
        "BA_SESSION_TIMEOUT": "3600",
        "BA_MAX_STEPS_PER_SESSION": "100",
    }, clear=True)
    def test_validate_success_all_vars_present(self) -> None:
        """No error when all required vars present and numeric vars valid (Req 4.1)."""
        ConfigValidator.validate_and_log()  # Should not raise

    @patch.dict(os.environ, {}, clear=True)
    def test_validate_fails_missing_region(self) -> None:
        """ValueError raised when AWS_DEFAULT_REGION is missing (Req 4.2)."""
        with self.assertRaises(ValueError) as ctx:
            ConfigValidator.validate_and_log()
        self.assertIn("AWS_DEFAULT_REGION", str(ctx.exception))

    @patch.dict(os.environ, {"AWS_DEFAULT_REGION": ""}, clear=True)
    def test_validate_fails_empty_region(self) -> None:
        """ValueError raised when AWS_DEFAULT_REGION is empty string (Req 4.2)."""
        with self.assertRaises(ValueError) as ctx:
            ConfigValidator.validate_and_log()
        self.assertIn("Missing required", str(ctx.exception))

    @patch.dict(os.environ, {
        "AWS_DEFAULT_REGION": "us-west-2",
        "BA_SESSION_TIMEOUT": "abc",
    }, clear=True)
    def test_validate_fails_non_integer_session_timeout(self) -> None:
        """ValueError for non-integer BA_SESSION_TIMEOUT (Req 4.3)."""
        with self.assertRaises(ValueError) as ctx:
            ConfigValidator.validate_and_log()
        msg = str(ctx.exception)
        self.assertIn("BA_SESSION_TIMEOUT", msg)
        self.assertIn("abc", msg)

    @patch.dict(os.environ, {
        "AWS_DEFAULT_REGION": "us-west-2",
        "BA_MAX_STEPS_PER_SESSION": "xyz",
    }, clear=True)
    def test_validate_fails_non_integer_max_steps(self) -> None:
        """ValueError for non-integer BA_MAX_STEPS_PER_SESSION (Req 4.4)."""
        with self.assertRaises(ValueError) as ctx:
            ConfigValidator.validate_and_log()
        msg = str(ctx.exception)
        self.assertIn("BA_MAX_STEPS_PER_SESSION", msg)
        self.assertIn("xyz", msg)

    @patch.dict(os.environ, {"AWS_DEFAULT_REGION": "us-east-1"}, clear=True)
    def test_defaults_applied_when_vars_not_set(self) -> None:
        """Optional vars resolve to defaults when not set in environment (Req 4.5)."""
        ConfigValidator.validate_and_log()  # Should not raise
        defaults = ConfigValidator.OPTIONAL_VARS_WITH_DEFAULTS
        self.assertEqual(defaults['BA_BROWSER_MODEL_ID'],
                         'us.anthropic.claude-sonnet-4-5-20250929-v1:0')
        self.assertEqual(defaults['BA_SESSION_TIMEOUT'], '3600')
        self.assertEqual(defaults['BA_MAX_STEPS_PER_SESSION'], '100')
        self.assertEqual(defaults['LOG_LEVEL'], 'INFO')

    @patch.dict(os.environ, {"AWS_DEFAULT_REGION": "us-west-2"}, clear=True)
    def test_summary_log_produced_on_success(self) -> None:
        """Configuration summary log is produced on successful validation (Req 4.6)."""
        with self.assertLogs(
            "utils.config_validator.ConfigValidator", level=logging.INFO
        ) as cm:
            ConfigValidator.validate_and_log()

        log_output = "\n".join(cm.output)
        self.assertIn("Browser Agent Configuration", log_output)
        self.assertIn("AWS_DEFAULT_REGION", log_output)
        self.assertIn("BA_BROWSER_MODEL_ID", log_output)
        self.assertIn("BA_SESSION_TIMEOUT", log_output)

    # ------------------------------------------------------------------
    # Spec 3 tests — new env vars, store type, conditional validation
    # ------------------------------------------------------------------

    def test_ba_sessions_dir_in_optional_defaults(self) -> None:
        """BA_SESSIONS_DIR is in OPTIONAL_VARS_WITH_DEFAULTS with default 'sessions' (Req 11.5)."""
        self.assertIn('BA_SESSIONS_DIR', ConfigValidator.OPTIONAL_VARS_WITH_DEFAULTS)
        self.assertEqual(
            ConfigValidator.OPTIONAL_VARS_WITH_DEFAULTS['BA_SESSIONS_DIR'],
            'sessions',
        )

    def test_ba_screenshots_dir_removed(self) -> None:
        """BA_SCREENSHOTS_DIR is NOT in OPTIONAL_VARS_WITH_DEFAULTS (Req 11.10)."""
        self.assertNotIn(
            'BA_SCREENSHOTS_DIR', ConfigValidator.OPTIONAL_VARS_WITH_DEFAULTS
        )

    def test_disconnect_grace_seconds_in_optional_and_numeric(self) -> None:
        """BA_DISCONNECT_GRACE_SECONDS is optional (default 30) and numeric (Req 11.1, 11.3)."""
        self.assertIn(
            'BA_DISCONNECT_GRACE_SECONDS',
            ConfigValidator.OPTIONAL_VARS_WITH_DEFAULTS,
        )
        self.assertEqual(
            ConfigValidator.OPTIONAL_VARS_WITH_DEFAULTS['BA_DISCONNECT_GRACE_SECONDS'],
            '30',
        )
        self.assertIn('BA_DISCONNECT_GRACE_SECONDS', ConfigValidator.NUMERIC_VARS)

    def test_hitl_timeout_seconds_in_optional_and_numeric(self) -> None:
        """BA_HITL_TIMEOUT_SECONDS is optional (default 300) and numeric (Req 11.2, 11.3)."""
        self.assertIn(
            'BA_HITL_TIMEOUT_SECONDS',
            ConfigValidator.OPTIONAL_VARS_WITH_DEFAULTS,
        )
        self.assertEqual(
            ConfigValidator.OPTIONAL_VARS_WITH_DEFAULTS['BA_HITL_TIMEOUT_SECONDS'],
            '300',
        )
        self.assertIn('BA_HITL_TIMEOUT_SECONDS', ConfigValidator.NUMERIC_VARS)

    def test_session_store_type_default_memory(self) -> None:
        """BA_SESSION_STORE_TYPE defaults to 'memory' (Req 11.4)."""
        self.assertEqual(
            ConfigValidator.OPTIONAL_VARS_WITH_DEFAULTS['BA_SESSION_STORE_TYPE'],
            'memory',
        )

    def test_session_store_prefix_default(self) -> None:
        """BA_SESSION_STORE_PREFIX defaults to 'browser-sessions' (Req 11.8)."""
        self.assertEqual(
            ConfigValidator.OPTIONAL_VARS_WITH_DEFAULTS['BA_SESSION_STORE_PREFIX'],
            'browser-sessions',
        )

    @patch.dict(os.environ, {
        "AWS_DEFAULT_REGION": "us-west-2",
        "BA_SESSION_STORE_TYPE": "invalid",
    }, clear=True)
    def test_invalid_store_type_rejected(self) -> None:
        """Invalid BA_SESSION_STORE_TYPE raises ValueError (Req 11.4)."""
        with self.assertRaises(ValueError) as ctx:
            ConfigValidator.validate_and_log()
        msg = str(ctx.exception)
        self.assertIn("BA_SESSION_STORE_TYPE", msg)
        self.assertIn("invalid", msg)

    @patch.dict(os.environ, {
        "AWS_DEFAULT_REGION": "us-west-2",
        "BA_SESSION_STORE_TYPE": "dynamodb",
    }, clear=True)
    def test_dynamodb_requires_table(self) -> None:
        """type=dynamodb without BA_SESSION_STORE_TABLE raises ValueError (Req 11.6)."""
        with self.assertRaises(ValueError) as ctx:
            ConfigValidator.validate_and_log()
        self.assertIn("BA_SESSION_STORE_TABLE", str(ctx.exception))

    @patch.dict(os.environ, {
        "AWS_DEFAULT_REGION": "us-west-2",
        "BA_SESSION_STORE_TYPE": "dynamodb",
        "BA_SESSION_STORE_TABLE": "my-table",
    }, clear=True)
    def test_dynamodb_requires_bucket(self) -> None:
        """type=dynamodb without BA_SESSION_STORE_BUCKET raises ValueError (Req 11.7)."""
        with self.assertRaises(ValueError) as ctx:
            ConfigValidator.validate_and_log()
        self.assertIn("BA_SESSION_STORE_BUCKET", str(ctx.exception))

    @patch.dict(os.environ, {
        "AWS_DEFAULT_REGION": "us-west-2",
        "BA_SESSION_STORE_TYPE": "s3",
    }, clear=True)
    def test_s3_requires_bucket(self) -> None:
        """type=s3 without BA_SESSION_STORE_BUCKET raises ValueError (Req 11.7)."""
        with self.assertRaises(ValueError) as ctx:
            ConfigValidator.validate_and_log()
        self.assertIn("BA_SESSION_STORE_BUCKET", str(ctx.exception))

    @patch.dict(os.environ, {
        "AWS_DEFAULT_REGION": "us-west-2",
        "BA_SESSION_STORE_TYPE": "dynamodb",
        "BA_SESSION_STORE_TABLE": "my-table",
        "BA_SESSION_STORE_BUCKET": "my-bucket",
    }, clear=True)
    def test_dynamodb_valid_with_table_and_bucket(self) -> None:
        """type=dynamodb passes when both table and bucket are set (Req 11.6, 11.7)."""
        ConfigValidator.validate_and_log()  # Should not raise

    @patch.dict(os.environ, {
        "AWS_DEFAULT_REGION": "us-west-2",
        "BA_SESSION_STORE_TYPE": "s3",
        "BA_SESSION_STORE_BUCKET": "my-bucket",
    }, clear=True)
    def test_s3_valid_with_bucket(self) -> None:
        """type=s3 passes when bucket is set (Req 11.7)."""
        ConfigValidator.validate_and_log()  # Should not raise

    @patch.dict(os.environ, {
        "AWS_DEFAULT_REGION": "us-west-2",
        "BA_DISCONNECT_GRACE_SECONDS": "not_a_number",
    }, clear=True)
    def test_disconnect_grace_non_numeric_rejected(self) -> None:
        """Non-numeric BA_DISCONNECT_GRACE_SECONDS raises ValueError (Req 11.3)."""
        with self.assertRaises(ValueError) as ctx:
            ConfigValidator.validate_and_log()
        self.assertIn("BA_DISCONNECT_GRACE_SECONDS", str(ctx.exception))

    @patch.dict(os.environ, {
        "AWS_DEFAULT_REGION": "us-west-2",
        "BA_HITL_TIMEOUT_SECONDS": "not_a_number",
    }, clear=True)
    def test_hitl_timeout_non_numeric_rejected(self) -> None:
        """Non-numeric BA_HITL_TIMEOUT_SECONDS raises ValueError (Req 11.3)."""
        with self.assertRaises(ValueError) as ctx:
            ConfigValidator.validate_and_log()
        self.assertIn("BA_HITL_TIMEOUT_SECONDS", str(ctx.exception))

    @patch.dict(os.environ, {
        "AWS_DEFAULT_REGION": "us-west-2",
        "BA_SESSION_STORE_TYPE": "dynamodb",
        "BA_SESSION_STORE_TABLE": "my-table",
        "BA_SESSION_STORE_BUCKET": "my-bucket",
    }, clear=True)
    def test_summary_logs_conditional_store_vars(self) -> None:
        """Config summary includes conditional store vars when relevant (Req 11.9)."""
        with self.assertLogs(
            "utils.config_validator.ConfigValidator", level=logging.INFO
        ) as cm:
            ConfigValidator.validate_and_log()

        log_output = "\n".join(cm.output)
        self.assertIn("BA_SESSION_STORE_TABLE", log_output)
        self.assertIn("BA_SESSION_STORE_BUCKET", log_output)
        self.assertIn("BA_SESSION_STORE_TYPE", log_output)

    @patch.dict(os.environ, {
        "AWS_DEFAULT_REGION": "us-west-2",
        "BA_SESSION_STORE_TYPE": "memory",
    }, clear=True)
    def test_valid_store_types_accepted(self) -> None:
        """All VALID_STORE_TYPES are accepted without error (Req 11.4)."""
        for store_type in ConfigValidator.VALID_STORE_TYPES:
            env = {"AWS_DEFAULT_REGION": "us-west-2",
                   "BA_SESSION_STORE_TYPE": store_type}
            if store_type == 'dynamodb':
                env["BA_SESSION_STORE_TABLE"] = "t"
                env["BA_SESSION_STORE_BUCKET"] = "b"
            elif store_type == 's3':
                env["BA_SESSION_STORE_BUCKET"] = "b"
            with patch.dict(os.environ, env, clear=True):
                ConfigValidator.validate_and_log()  # Should not raise


if __name__ == "__main__":
    unittest.main()
