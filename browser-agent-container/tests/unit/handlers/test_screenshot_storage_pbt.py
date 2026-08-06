# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Property-based tests for ScreenshotStorage.

Property 7: Screenshot storage path construction (Req 17.6, 10a.3, 10a.4, 10c.2)
"""

# pylint: disable=import-error,unused-import
try:
    import __setup__
except ModuleNotFoundError:
    import tests.unit.handlers.__setup__
# pylint: enable=import-error,unused-import

import os
import unittest
from unittest.mock import MagicMock, patch, mock_open

from hypothesis import given, settings
from hypothesis import strategies as st

from handlers.screenshot_storage import (
    LocalScreenshotStorage,
    S3ScreenshotStorage,
)


path_segment_st = st.text(
    alphabet=st.characters(
        whitelist_categories=('L', 'N', 'Pd'),
        blacklist_characters='/',
    ),
    min_size=1, max_size=30,
)
filename_st = st.from_regex(
    r'[a-zA-Z0-9_\-]{1,20}\.png', fullmatch=True,
)


# ============================================================
# Property 7: Screenshot storage path construction
# Feature: 86-browser-agent-container-deployment, Property 7: Screenshot storage path construction
# Validates: Requirements 17.6, 10a.3, 10a.4, 10c.2
# ============================================================

class TestScreenshotPathConstructionProperty(unittest.TestCase):
    """Property 7: Screenshot storage path construction."""

    @settings(max_examples=100)
    @given(
        base_dir=path_segment_st,
        user_id=path_segment_st,
        session_id=path_segment_st,
        filename=filename_st,
    )
    def test_local_path_matches_hierarchy(
        self, base_dir: str, user_id: str, session_id: str, filename: str,
    ) -> None:
        """LocalScreenshotStorage constructs {base_dir}/{user_id}/{session_id}/screenshots/{filename}."""
        storage = LocalScreenshotStorage(base_dir=base_dir)
        m = mock_open()
        with patch("builtins.open", m), patch("os.makedirs"):
            result = storage.save(user_id, session_id, filename, b"data")

        expected = os.path.join(
            base_dir, user_id, session_id, "screenshots", filename
        )
        self.assertEqual(result, expected)

    @settings(max_examples=100)
    @given(
        base_dir=path_segment_st,
        user_id=path_segment_st,
        session_id=path_segment_st,
        filename=filename_st,
    )
    def test_local_path_no_double_slashes(
        self, base_dir: str, user_id: str, session_id: str, filename: str,
    ) -> None:
        """Local paths never contain double slashes."""
        storage = LocalScreenshotStorage(base_dir=base_dir)
        m = mock_open()
        with patch("builtins.open", m), patch("os.makedirs"):
            result = storage.save(user_id, session_id, filename, b"data")
        self.assertNotIn("//", result)

    @settings(max_examples=100)
    @given(
        prefix=path_segment_st,
        user_id=path_segment_st,
        session_id=path_segment_st,
        filename=filename_st,
    )
    def test_s3_key_matches_hierarchy(
        self, prefix: str, user_id: str, session_id: str, filename: str,
    ) -> None:
        """S3ScreenshotStorage constructs {prefix}/{user_id}/{session_id}/screenshots/{filename}."""
        mock_client = MagicMock()
        with patch(
            'handlers.screenshot_storage.get_boto3_session'
        ) as mock_session, patch(
            'handlers.screenshot_storage.get_boto3_client_config'
        ):
            mock_session.return_value.client.return_value = mock_client
            storage = S3ScreenshotStorage(bucket="amzn-s3-demo-bucket", prefix=prefix)

        result = storage.save(user_id, session_id, filename, b"data")

        expected_key = "%s/%s/%s/screenshots/%s" % (
            prefix, user_id, session_id, filename
        )
        expected_url = "s3://amzn-s3-demo-bucket/%s" % expected_key
        self.assertEqual(result, expected_url)

        actual_key = mock_client.put_object.call_args[1]['Key']
        self.assertEqual(actual_key, expected_key)

    @settings(max_examples=100)
    @given(
        prefix=path_segment_st,
        user_id=path_segment_st,
        session_id=path_segment_st,
        filename=filename_st,
    )
    def test_s3_key_no_double_slashes(
        self, prefix: str, user_id: str, session_id: str, filename: str,
    ) -> None:
        """S3 keys never contain double slashes."""
        mock_client = MagicMock()
        with patch(
            'handlers.screenshot_storage.get_boto3_session'
        ) as mock_session, patch(
            'handlers.screenshot_storage.get_boto3_client_config'
        ):
            mock_session.return_value.client.return_value = mock_client
            storage = S3ScreenshotStorage(bucket="amzn-s3-demo-bucket", prefix=prefix)

        storage.save(user_id, session_id, filename, b"data")
        actual_key = mock_client.put_object.call_args[1]['Key']
        self.assertNotIn("//", actual_key)

    @settings(max_examples=100)
    @given(
        prefix=path_segment_st,
        user_id=path_segment_st,
        session_id=path_segment_st,
        filename=filename_st,
    )
    def test_s3_key_no_empty_segments(
        self, prefix: str, user_id: str, session_id: str, filename: str,
    ) -> None:
        """S3 key path segments are never empty."""
        mock_client = MagicMock()
        with patch(
            'handlers.screenshot_storage.get_boto3_session'
        ) as mock_session, patch(
            'handlers.screenshot_storage.get_boto3_client_config'
        ):
            mock_session.return_value.client.return_value = mock_client
            storage = S3ScreenshotStorage(bucket="amzn-s3-demo-bucket", prefix=prefix)

        storage.save(user_id, session_id, filename, b"data")
        actual_key = mock_client.put_object.call_args[1]['Key']
        segments = actual_key.split("/")
        for segment in segments:
            self.assertNotEqual(
                segment, "",
                "Empty path segment in S3 key: %s" % actual_key,
            )


if __name__ == "__main__":
    unittest.main()
