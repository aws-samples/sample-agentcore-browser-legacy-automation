# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Unit tests for screenshot storage — LocalScreenshotStorage file write,
S3ScreenshotStorage put_object, path hierarchy, factory coupling.

Validates: Requirements 16.4
"""

# pylint: disable=import-error,unused-import
try:
    import __setup__
except ModuleNotFoundError:
    import tests.unit.handlers.__setup__
# pylint: enable=import-error,unused-import

import os
import unittest
from unittest.mock import MagicMock, patch, mock_open, call

from handlers.screenshot_storage import (
    ScreenshotStorageBase,
    LocalScreenshotStorage,
    S3ScreenshotStorage,
    create_screenshot_storage,
)


class TestLocalScreenshotStorage(unittest.TestCase):
    """Tests for LocalScreenshotStorage file operations."""

    def test_save_creates_directory_and_writes_file(self) -> None:
        """save() creates directory tree and writes bytes to file."""
        storage = LocalScreenshotStorage(base_dir="test_sessions")
        data = b"\x89PNG\r\n\x1a\nfake_png_data"

        m = mock_open()
        with patch("builtins.open", m), patch("os.makedirs") as mock_makedirs:
            result = storage.save("user1", "sess1", "screenshot.png", data)

        mock_makedirs.assert_called_once_with(
            os.path.join("test_sessions", "user1", "sess1", "screenshots"),
            exist_ok=True,
        )
        m.assert_called_once_with(
            os.path.join("test_sessions", "user1", "sess1", "screenshots", "screenshot.png"),
            "wb",
        )
        m().write.assert_called_once_with(data)
        expected_path = os.path.join(
            "test_sessions", "user1", "sess1", "screenshots", "screenshot.png"
        )
        self.assertEqual(result, expected_path)

    def test_save_path_hierarchy(self) -> None:
        """save() constructs {base_dir}/{user_id}/{session_id}/screenshots/{filename}."""
        storage = LocalScreenshotStorage(base_dir="sessions")
        m = mock_open()
        with patch("builtins.open", m), patch("os.makedirs"):
            result = storage.save(
                "user_abc", "brws_20260101_120000_abcd1234",
                "2026-01-01T12-00-00_homepage.png", b"data",
            )
        expected = os.path.join(
            "sessions", "user_abc", "brws_20260101_120000_abcd1234",
            "screenshots", "2026-01-01T12-00-00_homepage.png",
        )
        self.assertEqual(result, expected)

    def test_default_base_dir(self) -> None:
        """Default base_dir is 'sessions'."""
        storage = LocalScreenshotStorage()
        self.assertEqual(storage._base_dir, "sessions")

    def test_custom_base_dir(self) -> None:
        """Custom base_dir is respected."""
        storage = LocalScreenshotStorage(base_dir="/tmp/my_sessions")
        self.assertEqual(storage._base_dir, "/tmp/my_sessions")


class TestS3ScreenshotStorage(unittest.TestCase):
    """Tests for S3ScreenshotStorage with mocked boto3."""

    def setUp(self) -> None:
        self.mock_client = MagicMock()
        with patch(
            'handlers.screenshot_storage.get_boto3_session'
        ) as mock_session, patch(
            'handlers.screenshot_storage.get_boto3_client_config'
        ):
            mock_session.return_value.client.return_value = self.mock_client
            self.storage = S3ScreenshotStorage(
                bucket="amzn-s3-demo-bucket", prefix="test-prefix"
            )

    def test_save_calls_put_object(self) -> None:
        """save() calls put_object with correct bucket, key, body."""
        data = b"\x89PNG\r\n\x1a\nfake_png_data"
        result = self.storage.save("user1", "sess1", "screenshot.png", data)

        self.mock_client.put_object.assert_called_once_with(
            Bucket="amzn-s3-demo-bucket",
            Key="test-prefix/user1/sess1/screenshots/screenshot.png",
            Body=data,
            ContentType="image/png",
        )
        self.assertEqual(
            result,
            "s3://amzn-s3-demo-bucket/test-prefix/user1/sess1/screenshots/screenshot.png",
        )

    def test_save_s3_key_hierarchy(self) -> None:
        """save() constructs {prefix}/{user_id}/{session_id}/screenshots/{filename}."""
        self.storage.save(
            "user_abc", "brws_20260101_120000_abcd1234",
            "2026-01-01T12-00-00_homepage.png", b"data",
        )
        expected_key = (
            "test-prefix/user_abc/brws_20260101_120000_abcd1234"
            "/screenshots/2026-01-01T12-00-00_homepage.png"
        )
        actual_key = self.mock_client.put_object.call_args[1]['Key']
        self.assertEqual(actual_key, expected_key)

    def test_save_returns_s3_url(self) -> None:
        """save() returns s3://{bucket}/{key} URL."""
        result = self.storage.save("u1", "s1", "img.png", b"data")
        self.assertTrue(result.startswith("s3://amzn-s3-demo-bucket/"))
        self.assertIn("screenshots/img.png", result)

    def test_default_prefix(self) -> None:
        """Default prefix is 'browser-sessions'."""
        with patch(
            'handlers.screenshot_storage.get_boto3_session'
        ) as mock_session, patch(
            'handlers.screenshot_storage.get_boto3_client_config'
        ):
            mock_session.return_value.client.return_value = MagicMock()
            storage = S3ScreenshotStorage(bucket="b")
        self.assertEqual(storage._prefix, "browser-sessions")


class TestCreateScreenshotStorageFactory(unittest.TestCase):
    """Tests for create_screenshot_storage factory coupling."""

    def test_memory_returns_local_storage(self) -> None:
        """memory store type → LocalScreenshotStorage."""
        storage = create_screenshot_storage("memory")
        self.assertIsInstance(storage, LocalScreenshotStorage)

    @patch.dict(os.environ, {'BA_SESSIONS_DIR': 'custom_dir'})
    def test_memory_uses_sessions_dir_env(self) -> None:
        """memory mode reads BA_SESSIONS_DIR for base_dir."""
        storage = create_screenshot_storage("memory")
        self.assertEqual(storage._base_dir, "custom_dir")

    @patch.dict(os.environ, {
        'BA_SESSION_STORE_BUCKET': 'my-bucket',
        'BA_SESSION_STORE_PREFIX': 'my-prefix',
    })
    @patch('handlers.screenshot_storage.get_boto3_session')
    @patch('handlers.screenshot_storage.get_boto3_client_config')
    def test_dynamodb_returns_s3_storage(
        self, _mock_config, mock_session
    ) -> None:
        """dynamodb store type → S3ScreenshotStorage."""
        mock_session.return_value.client.return_value = MagicMock()
        storage = create_screenshot_storage("dynamodb")
        self.assertIsInstance(storage, S3ScreenshotStorage)
        self.assertEqual(storage._bucket, "my-bucket")
        self.assertEqual(storage._prefix, "my-prefix")

    @patch.dict(os.environ, {
        'BA_SESSION_STORE_BUCKET': 'my-bucket',
        'BA_SESSION_STORE_PREFIX': 'my-prefix',
    })
    @patch('handlers.screenshot_storage.get_boto3_session')
    @patch('handlers.screenshot_storage.get_boto3_client_config')
    def test_s3_returns_s3_storage(self, _mock_config, mock_session) -> None:
        """s3 store type → S3ScreenshotStorage."""
        mock_session.return_value.client.return_value = MagicMock()
        storage = create_screenshot_storage("s3")
        self.assertIsInstance(storage, S3ScreenshotStorage)

    def test_unknown_type_returns_local_storage(self) -> None:
        """Unknown store type defaults to LocalScreenshotStorage."""
        storage = create_screenshot_storage("unknown")
        self.assertIsInstance(storage, LocalScreenshotStorage)


if __name__ == "__main__":
    unittest.main()
