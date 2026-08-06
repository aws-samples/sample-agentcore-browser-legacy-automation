# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Property-based test: __setup__.py path resolves to src/ at any depth.

Verifies that every __setup__.py file in the tests/ directory tree has a
sys.path.insert statement whose relative path correctly resolves to the
project's src/ directory.

Feature: 86-browser-agent-scaffolding, Property 1: __setup__.py path resolves to src/ at any depth
Validates: Requirements 1.6
"""

# pylint: disable=import-error,unused-import
try:
    import __setup__
except ModuleNotFoundError:
    import tests.unit.__setup__
# pylint: enable=import-error,unused-import

import os
import re
import unittest
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st


# Project root: browser-agent-container/
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
SRC_DIR: Path = PROJECT_ROOT / "src"


def _collect_setup_files() -> list:
    """Collect all __setup__.py files under tests/."""
    tests_dir = PROJECT_ROOT / "tests"
    return sorted(tests_dir.rglob("__setup__.py"))


def _extract_relative_path(setup_file: Path) -> str | None:
    """Extract the relative path string from a __setup__.py file.

    Looks for patterns like:
        os.path.join(os.path.dirname(__file__), "../src")
        os.path.join(os.path.dirname(__file__), "..", "..", "src")
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "src")
    """
    content = setup_file.read_text()

    # Match: os.path.join(os.path.dirname(__file__), <args>)
    # where <args> is a comma-separated list of string literals
    pattern = r'os\.path\.join\(\s*os\.path\.dirname\(__file__\)\s*,\s*(.+?)\)'
    match = re.search(pattern, content)
    if not match:
        return None

    args_str = match.group(1)
    # Extract all quoted string arguments
    parts = re.findall(r'"([^"]+)"|\'([^\']+)\'', args_str)
    # Each match is a tuple of (double-quoted, single-quoted); take whichever is non-empty
    path_parts = [p[0] or p[1] for p in parts]
    if not path_parts:
        return None

    return os.path.join(*path_parts)


class TestSetupPathResolution(unittest.TestCase):
    """Property-based tests for __setup__.py path resolution."""

    # Feature: 86-browser-agent-scaffolding, Property 1: __setup__.py path resolves to src/ at any depth
    @settings(max_examples=100)
    @given(depth=st.integers(min_value=1, max_value=5))
    def test_prop_setup_path_resolves_to_src(self, depth: int) -> None:
        """The relative path pattern '../' * depth + 'src' resolves to src/ from depth N.

        For a __setup__.py at depth N below the project root (tests/ = 1,
        tests/unit/ = 2, tests/unit/utils/ = 3, etc.), the relative path
        consisting of N '..' segments followed by 'src' should resolve to
        the project's src/ directory.

        Validates: Requirements 1.6
        """
        # Simulate a __setup__.py at the given depth
        # depth=1 → tests/__setup__.py → "../src"
        # depth=2 → tests/unit/__setup__.py → "../../src"
        # depth=3 → tests/unit/utils/__setup__.py → "../../../src"
        parts = [".."] * depth + ["src"]
        relative_path = os.path.join(*parts)

        # Build the simulated file location
        subdirs = ["tests"] + ["sub%d" % i for i in range(depth - 1)]
        simulated_dir = PROJECT_ROOT
        for subdir in subdirs:
            simulated_dir = simulated_dir / subdir

        # Resolve the relative path from the simulated location
        resolved = os.path.normpath(os.path.join(str(simulated_dir), relative_path))

        self.assertEqual(
            resolved,
            str(SRC_DIR),
            "At depth %d, relative path '%s' from '%s' should resolve to '%s', got '%s'"
            % (depth, relative_path, simulated_dir, SRC_DIR, resolved),
        )

    def test_all_existing_setup_files_resolve_to_src(self) -> None:
        """Every existing __setup__.py resolves its sys.path.insert to src/.

        This is a concrete test that validates all actual __setup__.py files
        in the project, complementing the property test above.
        """
        setup_files = _collect_setup_files()
        self.assertTrue(
            len(setup_files) > 0,
            "Expected at least one __setup__.py file under tests/",
        )

        for setup_file in setup_files:
            relative_path = _extract_relative_path(setup_file)
            self.assertIsNotNone(
                relative_path,
                "Could not extract relative path from %s" % setup_file,
            )

            # Resolve from the __setup__.py file's directory
            setup_dir = setup_file.parent
            resolved = Path(
                os.path.normpath(os.path.join(str(setup_dir), relative_path))
            )

            self.assertEqual(
                resolved,
                SRC_DIR,
                "__setup__.py at '%s' resolves to '%s', expected '%s'"
                % (setup_file, resolved, SRC_DIR),
            )


if __name__ == "__main__":
    unittest.main()
