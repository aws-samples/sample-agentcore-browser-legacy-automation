# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Setup for models unit tests."""

import os
import sys

# Add src to path for imports
src_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "src")
)
if src_path not in sys.path:
    sys.path.insert(0, src_path)
