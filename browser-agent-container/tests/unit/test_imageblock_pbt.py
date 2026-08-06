# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Property-based test: @tool decorator ImageBlock round-trip.

Validates that arbitrary PNG byte sequences survive the Strands @tool
decorator passthrough without alteration.

Feature: 86-browser-agent-scaffolding, Property 6: @tool decorator ImageBlock round-trip
Validates: Requirements 5.2
"""

# pylint: disable=import-error,unused-import
try:
    import __setup__
except ModuleNotFoundError:
    import tests.unit.__setup__
# pylint: enable=import-error,unused-import

import base64
import unittest
import zlib

from hypothesis import given, settings, assume
from hypothesis import strategies as st
from strands import tool


# ---------------------------------------------------------------------------
# Strategy: generate valid-ish PNG byte sequences
# ---------------------------------------------------------------------------
def _create_png_with_payload(payload: bytes) -> bytes:
    """Create a minimal valid PNG wrapping arbitrary payload in an ancillary chunk.

    This produces a structurally valid PNG that embeds the given payload
    bytes inside a tEXt ancillary chunk, ensuring the overall file is
    a real PNG that starts with the magic bytes.
    """
    signature = b'\x89PNG\r\n\x1a\n'

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        raw = chunk_type + data
        crc = zlib.crc32(raw) & 0xFFFFFFFF
        return len(data).to_bytes(4, 'big') + raw + crc.to_bytes(4, 'big')

    # IHDR: 1×1, 8-bit RGB
    ihdr_data = (
        (1).to_bytes(4, 'big')
        + (1).to_bytes(4, 'big')
        + b'\x08\x02\x00\x00\x00'
    )
    ihdr = _chunk(b'IHDR', ihdr_data)

    # tEXt chunk with payload (ancillary, safe to include arbitrary data)
    text_data = b'Comment\x00' + payload
    text_chunk = _chunk(b'tEXt', text_data)

    # IDAT: single white pixel
    raw_row = b'\x00\xff\xff\xff'
    compressed = zlib.compress(raw_row)
    idat = _chunk(b'IDAT', compressed)

    # IEND
    iend = _chunk(b'IEND', b'')

    return signature + ihdr + text_chunk + idat + iend


# Strategy that generates valid PNG byte sequences of varying sizes
png_bytes_strategy = st.binary(min_size=1, max_size=200).map(_create_png_with_payload)


class TestImageBlockRoundTrip(unittest.TestCase):
    """Property-based tests for @tool decorator ImageBlock passthrough."""

    # Feature: 86-browser-agent-scaffolding, Property 6: @tool decorator ImageBlock round-trip
    @settings(max_examples=100)
    @given(png_data=png_bytes_strategy)
    def test_prop_imageblock_round_trip(self, png_data: bytes) -> None:
        """PNG bytes returned as image content block are identical after @tool passthrough.

        Validates: Requirements 5.2
        """
        # Encode as base64 (matching the Bedrock Converse API image format)
        encoded = base64.b64encode(png_data).decode("utf-8")

        # Define a @tool function that returns the image block
        @tool
        def imageblock_tool(session_name: str = "test") -> dict:
            """Return image content block with the test PNG."""
            return {
                "status": "success",
                "content": [
                    {
                        "image": {
                            "format": "png",
                            "source": {"bytes": encoded},
                        }
                    }
                ],
            }

        # Invoke the tool
        result = imageblock_tool(session_name="pbt-test")

        # Extract the image block
        content = result.get("content", [])
        self.assertTrue(len(content) > 0, "content should not be empty")

        image_block = None
        for block in content:
            if isinstance(block, dict) and "image" in block:
                image_block = block["image"]
                break

        self.assertIsNotNone(image_block, "image block should be present")
        self.assertEqual(image_block["format"], "png")

        # Decode and compare bytes
        returned_bytes = base64.b64decode(image_block["source"]["bytes"])
        self.assertEqual(
            returned_bytes,
            png_data,
            "PNG bytes must survive @tool decorator round-trip unchanged",
        )


if __name__ == "__main__":
    unittest.main()
