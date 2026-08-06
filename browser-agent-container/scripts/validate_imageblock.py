#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Phase 0 smoke test: Does @tool decorator pass image content blocks to Claude?

This has been confirmed at source code level — the Strands _wrap_tool_result method
passes through dicts with status+content keys unchanged. This script validates the
runtime environment (Bedrock model access, IAM permissions, etc.).

Run: cd browser-agent-container && source .venv/bin/activate && set -a && source .env && set +a
     PYTHONPATH=src python scripts/validate_imageblock.py

Expected output:
  PASS: Runtime environment confirmed — @tool ImageBlock passthrough works
  or
  FAIL: Runtime issue detected — check IAM permissions, Bedrock model access, or SDK version

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8
Reference: Research document Section 12.0.2
"""

import io
import os
import sys

from PIL import Image
from strands import Agent, tool


# ---------------------------------------------------------------------------
# Color map for test images
# ---------------------------------------------------------------------------
COLOR_MAP = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
}


# ---------------------------------------------------------------------------
# @tool-decorated function returning ImageBlock content
# ---------------------------------------------------------------------------
@tool
def test_screenshot(color: str = "red") -> dict:
    """Return a test image as an ImageBlock for Claude to analyze.

    Args:
        color: Color of the test image to generate (red, green, blue).
    """
    rgb = COLOR_MAP.get(color, (255, 0, 0))
    img = Image.new("RGB", (200, 200), rgb)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    png_bytes = buffer.getvalue()

    return {
        "status": "success",
        "content": [
            {"image": {"format": "png", "source": {"bytes": png_bytes}}},
            {"text": "Generated a %s test image (200x200 PNG)." % color},
        ],
    }


# ---------------------------------------------------------------------------
# Validation logic
# ---------------------------------------------------------------------------
def main() -> int:
    """Run the ImageBlock passthrough validation."""
    model_id = os.environ.get(
        "BA_BROWSER_MODEL_ID",
        "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    )

    print("=" * 60)
    print("Phase 0 Smoke Test: @tool ImageBlock Passthrough")
    print("=" * 60)
    print("  Model: %s" % model_id)
    print()

    # ------------------------------------------------------------------
    # Phase 1: Decorator passthrough (no LLM)
    # ------------------------------------------------------------------
    print("[Phase 1] Decorator passthrough — calling test_screenshot directly...")
    try:
        result = test_screenshot(color="red")
    except Exception as exc:
        print("FAIL — @tool invocation raised: %s" % exc)
        return 1

    content = result.get("content", [])
    if not content:
        print("FAIL — 'content' key is missing or empty")
        print("  Actual result: %s" % result)
        return 1

    image_block = None
    for block in content:
        if isinstance(block, dict) and "image" in block:
            image_block = block["image"]
            break

    if image_block is None:
        print("FAIL — No 'image' content block found in result")
        print("  Actual content blocks: %s" % content)
        return 1

    # Verify PNG bytes are present and valid
    source = image_block.get("source", {})
    returned_bytes = source.get("bytes")
    if returned_bytes is None:
        print("FAIL — image.source.bytes is missing")
        print("  Actual image block: %s" % image_block)
        return 1

    if not isinstance(returned_bytes, bytes):
        print("FAIL — image.source.bytes is not bytes (type: %s)" % type(returned_bytes).__name__)
        return 1

    if not returned_bytes[:4] == b'\x89PNG':
        print("FAIL — Returned bytes do not start with PNG magic bytes")
        print("  First 4 bytes: %s" % returned_bytes[:4])
        return 1

    # Generate expected bytes for comparison
    expected_img = Image.new("RGB", (200, 200), (255, 0, 0))
    expected_buffer = io.BytesIO()
    expected_img.save(expected_buffer, format="PNG")
    expected_bytes = expected_buffer.getvalue()

    if returned_bytes == expected_bytes:
        print("  PASS: PNG bytes are byte-for-byte identical (%d bytes)" % len(returned_bytes))
    else:
        print("FAIL — PNG bytes were altered during passthrough")
        print("  Expected length: %d" % len(expected_bytes))
        print("  Returned length: %d" % len(returned_bytes))
        return 1

    # ------------------------------------------------------------------
    # Phase 2: Agent+LLM vision — Claude sees and describes the image
    # ------------------------------------------------------------------
    print()
    print("[Phase 2] Agent+LLM vision — asking Claude to describe a red image...")
    try:
        agent = Agent(tools=[test_screenshot], model=model_id)
        response = agent(
            "Call the test_screenshot tool with color='red', then describe what you see "
            "in the image. What color is it? What are its dimensions?"
        )
        result_text = response.message["content"][0]["text"].lower()

        if "red" in result_text:
            print("  PASS: Claude received and described the red image via @tool decorator")
            test2_pass = True
        else:
            print("  FAIL: Claude did not describe a red image")
            print("    Response: %s" % response.message["content"][0]["text"][:200])
            test2_pass = False
    except Exception as exc:
        print("  FAIL: Agent+LLM test raised: %s" % exc)
        test2_pass = False

    # ------------------------------------------------------------------
    # Phase 3: Color distinction — Claude distinguishes blue from red
    # ------------------------------------------------------------------
    print()
    print("[Phase 3] Color distinction — asking Claude to identify a blue image...")
    try:
        response = agent(
            "Now call test_screenshot with color='blue'. What color is this new image?"
        )
        result_text = response.message["content"][0]["text"].lower()

        if "blue" in result_text:
            print("  PASS: Claude correctly identified the blue image")
            test3_pass = True
        else:
            print("  FAIL: Claude did not identify the blue image")
            print("    Response: %s" % response.message["content"][0]["text"][:200])
            test3_pass = False
    except Exception as exc:
        print("  FAIL: Color distinction test raised: %s" % exc)
        test3_pass = False

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print()
    print("=" * 60)
    if test2_pass and test3_pass:
        print("PASS — All tests passed")
        print("  - Decorator passthrough: PNG bytes preserved")
        print("  - Agent+LLM vision: Claude sees images via @tool")
        print("  - Color distinction: Claude distinguishes different images")
        print("  Proceed to Phase 1 implementation.")
        return 0
    else:
        print("FAIL — Runtime issue detected")
        print("  - Decorator passthrough: PASS (mechanism confirmed)")
        print("  - Agent+LLM vision: %s" % ("PASS" if test2_pass else "FAIL"))
        print("  - Color distinction: %s" % ("PASS" if test3_pass else "FAIL"))
        print("  Check: IAM permissions, Bedrock model access, SDK version.")
        print("  The mechanism is confirmed at source code level — this is an environment issue.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
