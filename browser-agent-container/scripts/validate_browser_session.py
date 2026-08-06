#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Phase 0 smoke test: AgentCore Browser session lifecycle.

Validates: start session → navigate → screenshot → page access → direct bytes → close.
No agent, no LLM — pure Playwright via AgentCoreBrowser.

Run: cd browser-agent-container && source .venv/bin/activate && set -a && source .env && set +a
     PYTHONPATH=src python scripts/validate_browser_session.py

Expected output:
  PASS: Browser session lifecycle works end-to-end

Validates: Requirements 6.1–6.10, 7.1–7.4
Reference: Research document Section 12.0.3
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# Load environment variables from .env if not already set
# ---------------------------------------------------------------------------
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path, override=False)


# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------
REGION: str = os.environ.get("AWS_DEFAULT_REGION", "us-west-2")
SESSION_TIMEOUT: int = int(os.environ.get("BA_SESSION_TIMEOUT", "900"))
SCREENSHOTS_DIR: str = os.environ.get("BA_SCREENSHOTS_DIR", "screenshots")
SESSION_NAME: str = "phase0-validation-test"
TARGET_URL: str = "https://example.com"

# PNG magic bytes
PNG_MAGIC: bytes = b'\x89PNG'


# ---------------------------------------------------------------------------
# Go/No-Go diagnostic recommendations (Req 7.2, 7.3, 7.4)
# ---------------------------------------------------------------------------
GO_NO_GO = {
    "browser_fail": (
        "RECOMMENDATION: Debug IAM permissions (bedrock-agentcore:* actions), "
        "region config (%s), and AgentCore Browser availability. "
        "Verify AWS credentials are valid and the region supports AgentCore Browser."
    ),
    "both_fail": (
        "RECOMMENDATION: Check AWS credentials, VPC connectivity, and "
        "service availability in region %s. Verify network access to AWS APIs."
    ),
}


def _pass(msg: str) -> None:
    print("  PASS: %s" % msg)


def _fail(msg: str, detail: str = "") -> None:
    print("  FAIL: %s" % msg)
    if detail:
        print("        %s" % detail)


def main() -> int:
    """Run the browser session lifecycle validation."""
    print("=" * 60)
    print("Phase 0 Smoke Test: AgentCore Browser Session Lifecycle")
    print("=" * 60)
    print("  Region:  %s" % REGION)
    print("  Timeout: %ss" % SESSION_TIMEOUT)
    print()

    # Late import — fails fast if deps are missing
    try:
        from strands_tools.browser import AgentCoreBrowser
    except ImportError as exc:
        print("FAIL — Missing required dependency: %s" % exc)
        print(GO_NO_GO["both_fail"] % REGION)
        return 1

    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    browser = AgentCoreBrowser(region=REGION, session_timeout=SESSION_TIMEOUT)

    # ------------------------------------------------------------------
    # Test 1: Init session via browser() unified method
    # ------------------------------------------------------------------
    print("[Test 1] Initializing browser session...")
    try:
        result = browser.browser(browser_input={
            "action": {
                "type": "init_session",
                "description": "Phase 0 validation session",
                "session_name": SESSION_NAME,
            }
        })
        if result.get("status") == "success":
            _pass("Session initialized")
        else:
            _fail("Session init returned error", str(result))
            print("\n" + GO_NO_GO["browser_fail"] % REGION)
            return 1
    except Exception as exc:
        _fail("Session initialization", str(exc))
        print("\n" + GO_NO_GO["browser_fail"] % REGION)
        return 1

    # ------------------------------------------------------------------
    # Test 2: Navigate via browser() unified method
    # ------------------------------------------------------------------
    print("[Test 2] Navigating to %s..." % TARGET_URL)
    try:
        result = browser.browser(browser_input={
            "action": {
                "type": "navigate",
                "session_name": SESSION_NAME,
                "url": TARGET_URL,
            }
        })
        if result.get("status") == "success":
            _pass("Navigation successful")
        else:
            _fail("Navigation returned error", str(result))
            _close(browser)
            return 1
    except Exception as exc:
        _fail("Navigation", str(exc))
        _close(browser)
        return 1

    # ------------------------------------------------------------------
    # Test 3: Screenshot via browser() unified method
    # ------------------------------------------------------------------
    print("[Test 3] Taking screenshot...")
    try:
        result = browser.browser(browser_input={
            "action": {
                "type": "screenshot",
                "session_name": SESSION_NAME,
            }
        })
        if result.get("status") == "success":
            text = result.get("content", [{}])[0].get("text", "")
            _pass("Screenshot saved: %s" % text)
        else:
            _fail("Screenshot returned error", str(result))
            _close(browser)
            return 1
    except Exception as exc:
        _fail("Screenshot", str(exc))
        _close(browser)
        return 1

    # ------------------------------------------------------------------
    # Test 4: get_session_page() — validates subclass access pattern
    # ------------------------------------------------------------------
    print("[Test 4] Accessing Playwright Page via get_session_page()...")
    try:
        page = browser.get_session_page(SESSION_NAME)
        if page is not None:
            title = browser._execute_async(page.title())
            _pass("Page title: %s" % title)
        else:
            _fail("get_session_page returned None")
            _close(browser)
            return 1
    except Exception as exc:
        _fail("get_session_page", str(exc))
        _close(browser)
        return 1

    # ------------------------------------------------------------------
    # Test 5: Direct screenshot bytes — validates screenshot_for_vision path
    # ------------------------------------------------------------------
    print("[Test 5] Capturing screenshot bytes via page.screenshot()...")
    try:
        screenshot_bytes = browser._execute_async(page.screenshot(type="png"))
        if not isinstance(screenshot_bytes, bytes) or len(screenshot_bytes) == 0:
            _fail("screenshot did not return bytes")
            _close(browser)
            return 1

        if screenshot_bytes[:4] != PNG_MAGIC:
            _fail(
                "Screenshot is not valid PNG",
                "First 4 bytes: %s (expected: %s)" % (screenshot_bytes[:4], PNG_MAGIC),
            )
            _close(browser)
            return 1

        # Persist with timestamped filename
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S-%f")[:-3]
        filename = "%s_smoke-test-example-com.png" % timestamp
        filepath = os.path.join(SCREENSHOTS_DIR, filename)
        Path(filepath).write_bytes(screenshot_bytes)

        _pass("Screenshot bytes: %d bytes, PNG verified, saved to %s" % (len(screenshot_bytes), filepath))
    except Exception as exc:
        _fail("Direct screenshot bytes", str(exc))
        _close(browser)
        return 1

    # ------------------------------------------------------------------
    # Test 6: Close session
    # ------------------------------------------------------------------
    print("[Test 6] Closing session...")
    if not _close(browser):
        return 1

    print()
    print("=" * 60)
    print("PASS — AgentCore Browser session lifecycle works")
    print("  Browser init, navigate, screenshot, page access, and close all verified.")
    print("  Proceed to Phase 1 implementation.")
    print("=" * 60)
    return 0


def _close(browser: object) -> bool:
    """Attempt to close the browser session. Returns True on success."""
    try:
        result = browser.browser(browser_input={  # type: ignore[union-attr]
            "action": {
                "type": "close",
                "session_name": SESSION_NAME,
            }
        })
        _pass("Session closed")
        return True
    except Exception as exc:
        _fail("Session close", str(exc))
        return False


if __name__ == "__main__":
    sys.exit(main())
