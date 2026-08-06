# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Unit tests for logging_config module.

Validates: Requirements 1.1, 1.2, 1.3 (Requirement 16.5)
"""

# pylint: disable=import-error,unused-import
try:
    import __setup__
except ModuleNotFoundError:
    import tests.unit.utils.__setup__
# pylint: enable=import-error,unused-import

import logging
import sys
import unittest

from utils.logging_config import NOISY_LOGGERS, configure_agentcore_logging


class TestLoggingConfig(unittest.TestCase):
    """Unit tests for configure_agentcore_logging."""

    def setUp(self) -> None:
        """Capture original root handler state for restoration."""
        self._original_handlers = logging.root.handlers[:]
        self._original_levels: dict = {}
        for name in NOISY_LOGGERS:
            lgr = logging.getLogger(name)
            self._original_levels[name] = lgr.level

    def tearDown(self) -> None:
        """Restore original root handler state."""
        logging.root.handlers = self._original_handlers
        for name, level in self._original_levels.items():
            logging.getLogger(name).setLevel(level)

    def test_stderr_redirected_to_stdout(self) -> None:
        """Root handler writing to stderr is redirected to stdout (Req 1.1)."""
        # Set up a root handler pointing to stderr
        handler = logging.StreamHandler(sys.stderr)
        logging.root.handlers = [handler]
        self.assertIs(handler.stream, sys.stderr)

        configure_agentcore_logging()

        self.assertIs(handler.stream, sys.stdout)

    def test_noisy_loggers_includes_playwright(self) -> None:
        """NOISY_LOGGERS list includes 'playwright' (Req 1.3)."""
        self.assertIn('playwright', NOISY_LOGGERS)

    def test_all_noisy_loggers_set_to_warning(self) -> None:
        """All NOISY_LOGGERS are set to WARNING level after configure (Req 1.2)."""
        # Reset all noisy loggers to DEBUG first
        for name in NOISY_LOGGERS:
            logging.getLogger(name).setLevel(logging.DEBUG)

        configure_agentcore_logging()

        for name in NOISY_LOGGERS:
            self.assertEqual(
                logging.getLogger(name).level,
                logging.WARNING,
                "Logger '%s' should be WARNING" % name,
            )

    def test_non_stderr_handler_not_modified(self) -> None:
        """Handlers already writing to stdout are not modified (Req 1.1)."""
        handler = logging.StreamHandler(sys.stdout)
        logging.root.handlers = [handler]

        configure_agentcore_logging()

        self.assertIs(handler.stream, sys.stdout)

    def test_noisy_loggers_contains_expected_entries(self) -> None:
        """NOISY_LOGGERS contains all expected third-party logger names (Req 1.2)."""
        expected = [
            'botocore', 'urllib3', 'httpx', 'a2a',
            'strands_tools', 'strands.telemetry', 'opentelemetry',
            'playwright',
        ]
        for name in expected:
            self.assertIn(name, NOISY_LOGGERS)

    def test_idempotent_call(self) -> None:
        """Calling configure_agentcore_logging twice does not raise."""
        handler = logging.StreamHandler(sys.stderr)
        logging.root.handlers = [handler]

        configure_agentcore_logging()
        configure_agentcore_logging()

        self.assertIs(handler.stream, sys.stdout)


if __name__ == "__main__":
    unittest.main()
