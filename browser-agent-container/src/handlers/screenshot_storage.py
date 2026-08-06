# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Pluggable screenshot storage with two backends: local filesystem and S3.

Backend is coupled to the session store type via create_screenshot_storage():
  memory → LocalScreenshotStorage
  dynamodb/s3 → S3ScreenshotStorage

Validates: Requirements 10a.1–10a.7
"""

import os
from abc import ABC, abstractmethod
from logging import Logger

from utils.logging_helper import get_logger
from utils.session_helper import get_boto3_session, get_boto3_client_config


class ScreenshotStorageBase(ABC):
    """Abstract base class for screenshot persistence."""

    @abstractmethod
    def save(
        self, user_id: str, session_id: str, filename: str, data: bytes
    ) -> str:
        """Save screenshot bytes. Returns the storage path or URL."""
        ...


class LocalScreenshotStorage(ScreenshotStorageBase):
    """Writes screenshots to local filesystem.

    Path: {base_dir}/{user_id}/{session_id}/screenshots/{filename}
    """

    logger: Logger = get_logger(f"{__name__}.LocalScreenshotStorage")

    def __init__(self, base_dir: str = "sessions") -> None:
        self._base_dir: str = base_dir

    def save(
        self, user_id: str, session_id: str, filename: str, data: bytes
    ) -> str:
        """Write screenshot bytes to local filesystem."""
        dir_path = os.path.join(
            self._base_dir, user_id, session_id, "screenshots"
        )
        os.makedirs(dir_path, exist_ok=True)
        filepath = os.path.join(dir_path, filename)
        with open(filepath, "wb") as f:
            f.write(data)
        self.logger.debug("Saved screenshot: %s", filepath)
        return filepath


class S3ScreenshotStorage(ScreenshotStorageBase):
    """Writes screenshots to S3.

    Key: {prefix}/{user_id}/{session_id}/screenshots/{filename}
    """

    logger: Logger = get_logger(f"{__name__}.S3ScreenshotStorage")

    def __init__(self, bucket: str, prefix: str = "browser-sessions") -> None:
        session = get_boto3_session()
        self._client = session.client('s3', config=get_boto3_client_config())
        self._bucket: str = bucket
        self._prefix: str = prefix

    def save(
        self, user_id: str, session_id: str, filename: str, data: bytes
    ) -> str:
        """Upload screenshot bytes to S3."""
        key = "%s/%s/%s/screenshots/%s" % (
            self._prefix, user_id, session_id, filename
        )
        self._client.put_object(
            Bucket=self._bucket, Key=key, Body=data,
            ContentType='image/png',
        )
        s3_url = "s3://%s/%s" % (self._bucket, key)
        self.logger.debug("Saved screenshot: %s", s3_url)
        return s3_url


def create_screenshot_storage(store_type: str) -> ScreenshotStorageBase:
    """Factory function coupling screenshot storage to session store type.

    Args:
        store_type: One of 'memory', 'dynamodb', 's3'.

    Returns:
        LocalScreenshotStorage for memory mode,
        S3ScreenshotStorage for dynamodb/s3 modes.
    """
    if store_type in ('dynamodb', 's3'):
        return S3ScreenshotStorage(
            bucket=os.environ['BA_SESSION_STORE_BUCKET'],
            prefix=os.environ.get('BA_SESSION_STORE_PREFIX', 'browser-sessions'),
        )
    return LocalScreenshotStorage(
        base_dir=os.environ.get('BA_SESSIONS_DIR', 'sessions'),
    )
