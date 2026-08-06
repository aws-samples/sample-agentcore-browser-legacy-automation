# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""ScreenshotTool — captures, persists, and returns screenshots as ImageBlock.

Refactored for Spec 3: accepts pluggable ScreenshotStorageBase, delegates
file persistence to storage backend, uses {user_id}/{session_id}/screenshots/
path hierarchy.

Validates: Requirements 10c.1, 10c.2, 10c.3, 10c.4, 10c.5, 10c.6
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from logging import Logger

from utils.logging_helper import get_logger

from handlers.screenshot_storage import ScreenshotStorageBase, LocalScreenshotStorage


class ScreenshotTool:
    """Captures page screenshots, persists via pluggable storage, returns as Bedrock ImageBlock."""

    logger: Logger = get_logger(f"{__name__}.ScreenshotTool")

    def __init__(
        self,
        browser_tool: Any,
        storage: Optional[ScreenshotStorageBase] = None,
    ) -> None:
        """Initialize with a reference to the parent VisualBrowserTool.

        Args:
            browser_tool: VisualBrowserTool instance (provides get_session_page,
                          validate_session, _execute_async).
            storage: Optional ScreenshotStorageBase instance. Defaults to
                     LocalScreenshotStorage with BA_SESSIONS_DIR.
        """
        self.browser_tool = browser_tool
        self._storage: ScreenshotStorageBase = storage or LocalScreenshotStorage()
        self._user_id: str = "local"
        self._session_id: str = ""

    def set_context(
        self,
        user_id: str,
        session_id: str,
        storage: Optional[ScreenshotStorageBase] = None,
    ) -> None:
        """Set user and session context for screenshot path hierarchy.

        Args:
            user_id: User identifier from JWT extraction.
            session_id: Browser session identifier (brws_...).
            storage: Optional storage backend override. When provided,
                     replaces the default LocalScreenshotStorage with the
                     correct backend (e.g., S3ScreenshotStorage for production).
        """
        self._user_id = user_id
        self._session_id = session_id
        if storage is not None:
            self._storage = storage

    def capture(self, session_name: str, title: str, full_page: bool = False) -> Dict[str, Any]:
        """Capture screenshot, persist via storage backend, return as ImageBlock.

        Args:
            session_name: Browser session name.
            title: Descriptive title for the screenshot (slugified for filename).
            full_page: Capture entire page vs viewport only.

        Returns:
            Tool result with image content block and text confirmation.
        """
        self.logger.debug("Capturing screenshot: session=%s, title=%s, full_page=%s",
                          session_name, title, full_page)

        error = self.browser_tool.validate_session(session_name)
        if error:
            self.logger.error("Session validation failed: session=%s", session_name)
            return error

        page = self.browser_tool.get_session_page(session_name)
        if not page:
            self.logger.error("No active page for session: %s", session_name)
            return {"status": "error", "content": [{"text": "No active page"}]}

        try:
            screenshot_bytes = self.browser_tool._execute_async(
                page.screenshot(type="png", full_page=full_page)
            )

            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S-%f")[:-3]
            safe_title = re.sub(r"[^a-z0-9-]", "-", title.lower().strip())[:80]
            filename = "%s_%s.png" % (timestamp, safe_title)

            saved_path = self._storage.save(
                self._user_id, self._session_id, filename, screenshot_bytes
            )

            self.logger.info("Screenshot saved: %s", saved_path)

            return {
                "status": "success",
                "content": [
                    {"image": {"format": "png", "source": {"bytes": screenshot_bytes}}},
                    {"text": "Screenshot saved: %s. Analyze visually to identify elements." % saved_path},
                ],
            }
        except Exception as e:
            self.logger.error("Screenshot capture failed: %s", str(e))
            return {"status": "error", "content": [{"text": "Error: %s" % str(e)}]}
