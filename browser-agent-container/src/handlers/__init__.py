# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Request handlers for the browser agent container."""

from handlers.browser_handler import BrowserHandler
from handlers.starlette_websocket_adapter import StarletteWebSocketAdapter
from handlers.session_store import SessionStoreBase, SessionRecord
from handlers.screenshot_storage import ScreenshotStorageBase

__all__ = [
    "BrowserHandler",
    "StarletteWebSocketAdapter",
    "SessionStoreBase",
    "SessionRecord",
    "ScreenshotStorageBase",
]
