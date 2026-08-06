# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Property-based tests for agent.py.

Properties:
  6: User ID sanitization (Req 17.5, 10b.3)
  9: JWT claim priority extraction (Req 10b.1)
"""

# pylint: disable=import-error,unused-import
try:
    import __setup__
except ModuleNotFoundError:
    import tests.unit.__setup__
# pylint: enable=import-error,unused-import

import base64
import json
import re
import unittest

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from agent import _extract_user_id_from_jwt


ALLOWED_PATTERN = re.compile(r'^[a-zA-Z0-9\-_/]+$')
SANITIZE_RE = re.compile(r'[^a-zA-Z0-9\-_/]')

safe_claim = st.from_regex(r'[a-zA-Z][a-zA-Z0-9\-]{0,29}', fullmatch=True)


def _make_jwt(payload: dict) -> str:
    """Build a fake JWT with the given payload dict."""
    header = base64.urlsafe_b64encode(b'{"alg":"RS256"}').rstrip(b'=').decode()
    body = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).rstrip(b'=').decode()
    return "%s.%s.fake-sig" % (header, body)


def _sanitize(value: str) -> str:
    """Apply the same sanitization as agent.py."""
    return SANITIZE_RE.sub('_', value)


# ============================================================
# Property 6: User ID sanitization
# Feature: 86-browser-agent-container-deployment, Property 6: User ID sanitization
# Validates: Requirements 17.5, 10b.3
# ============================================================

class TestUserIdSanitizationProperty(unittest.TestCase):
    """Property 6: User ID sanitization."""

    @settings(max_examples=100)
    @given(st.text(min_size=1, max_size=200))
    def test_sanitized_output_contains_only_allowed_chars(
        self, raw_user_id: str
    ) -> None:
        """Every sanitized user_id contains only [a-zA-Z0-9\\-_/]."""
        assume(raw_user_id.strip())
        jwt = _make_jwt({"sub": raw_user_id})
        result = _extract_user_id_from_jwt("Bearer %s" % jwt)
        self.assertTrue(
            ALLOWED_PATTERN.match(result),
            "Sanitized user_id '%s' contains disallowed characters "
            "(original: '%s')" % (result, raw_user_id),
        )

    @settings(max_examples=100)
    @given(st.text(
        alphabet=st.sampled_from(list("abcdefghijklmnopqrstuvwxyz0123456789-_/")),
        min_size=1,
        max_size=50,
    ))
    def test_allowed_chars_preserved(self, safe_user_id: str) -> None:
        """Characters in [a-zA-Z0-9\\-_/] are preserved unchanged."""
        jwt = _make_jwt({"sub": safe_user_id})
        result = _extract_user_id_from_jwt("Bearer %s" % jwt)
        self.assertEqual(result, safe_user_id)

    @settings(max_examples=100)
    @given(st.text(
        alphabet=st.sampled_from(list("@.#!$%^&*()+={}[]|\\:;\"'<>,? ")),
        min_size=1,
        max_size=50,
    ))
    def test_special_chars_replaced_with_underscore(
        self, special_chars: str
    ) -> None:
        """Special characters are replaced with underscores."""
        raw = "a" + special_chars
        jwt = _make_jwt({"sub": raw})
        result = _extract_user_id_from_jwt("Bearer %s" % jwt)
        self.assertTrue(
            ALLOWED_PATTERN.match(result),
            "Result '%s' has disallowed chars" % result,
        )
        self.assertTrue(result.startswith("a"))

    @settings(max_examples=100)
    @given(st.text(min_size=1, max_size=100))
    def test_output_length_equals_input_length(
        self, raw_user_id: str
    ) -> None:
        """Sanitization replaces chars 1:1, so output length equals input length."""
        assume(raw_user_id.strip())
        jwt = _make_jwt({"sub": raw_user_id})
        result = _extract_user_id_from_jwt("Bearer %s" % jwt)
        self.assertEqual(
            len(result), len(raw_user_id),
            "Length mismatch: input=%d output=%d" % (
                len(raw_user_id), len(result)
            ),
        )

    @settings(max_examples=100)
    @given(st.from_regex(r'[a-zA-Z0-9][a-zA-Z0-9@.\-_/]{0,49}', fullmatch=True))
    def test_idempotent_sanitization(self, raw_user_id: str) -> None:
        """Sanitizing an already-sanitized value produces the same result."""
        jwt1 = _make_jwt({"sub": raw_user_id})
        first_pass = _extract_user_id_from_jwt("Bearer %s" % jwt1)
        jwt2 = _make_jwt({"sub": first_pass})
        second_pass = _extract_user_id_from_jwt("Bearer %s" % jwt2)
        self.assertEqual(first_pass, second_pass)


# ============================================================
# Property 9: JWT claim priority extraction
# Feature: 86-browser-agent-container-deployment, Property 9: JWT claim priority extraction
# Validates: Requirements 10b.1
# ============================================================

class TestJwtClaimPriorityProperty(unittest.TestCase):
    """Property 9: JWT claim priority extraction."""

    @settings(max_examples=100)
    @given(oid=safe_claim, sub=safe_claim, uid=safe_claim)
    def test_oid_takes_priority_over_sub_and_uid(
        self, oid: str, sub: str, uid: str
    ) -> None:
        """When oid is present, it is always selected."""
        assume(oid != sub and oid != uid)
        jwt = _make_jwt({"oid": oid, "sub": sub, "uid": uid})
        result = _extract_user_id_from_jwt("Bearer %s" % jwt)
        self.assertEqual(result, _sanitize(oid))

    @settings(max_examples=100)
    @given(oid=safe_claim, sub=safe_claim)
    def test_oid_takes_priority_over_sub(
        self, oid: str, sub: str
    ) -> None:
        """When oid and sub are present (no uid), oid is selected."""
        assume(oid != sub)
        jwt = _make_jwt({"oid": oid, "sub": sub})
        result = _extract_user_id_from_jwt("Bearer %s" % jwt)
        self.assertEqual(result, _sanitize(oid))

    @settings(max_examples=100)
    @given(oid=safe_claim, uid=safe_claim)
    def test_oid_takes_priority_over_uid(
        self, oid: str, uid: str
    ) -> None:
        """When oid and uid are present (no sub), oid is selected."""
        assume(oid != uid)
        jwt = _make_jwt({"oid": oid, "uid": uid})
        result = _extract_user_id_from_jwt("Bearer %s" % jwt)
        self.assertEqual(result, _sanitize(oid))

    @settings(max_examples=100)
    @given(sub=safe_claim, uid=safe_claim)
    def test_sub_takes_priority_over_uid(
        self, sub: str, uid: str
    ) -> None:
        """When sub and uid are present (no oid), sub is selected."""
        assume(sub != uid)
        jwt = _make_jwt({"sub": sub, "uid": uid})
        result = _extract_user_id_from_jwt("Bearer %s" % jwt)
        self.assertEqual(result, _sanitize(sub))

    @settings(max_examples=100)
    @given(oid=safe_claim)
    def test_oid_only(self, oid: str) -> None:
        """When only oid is present, it is selected."""
        jwt = _make_jwt({"oid": oid})
        result = _extract_user_id_from_jwt("Bearer %s" % jwt)
        self.assertEqual(result, _sanitize(oid))

    @settings(max_examples=100)
    @given(sub=safe_claim)
    def test_sub_only(self, sub: str) -> None:
        """When only sub is present, it is selected."""
        jwt = _make_jwt({"sub": sub})
        result = _extract_user_id_from_jwt("Bearer %s" % jwt)
        self.assertEqual(result, _sanitize(sub))

    @settings(max_examples=100)
    @given(uid=safe_claim)
    def test_uid_only(self, uid: str) -> None:
        """When only uid is present, it is selected."""
        jwt = _make_jwt({"uid": uid})
        result = _extract_user_id_from_jwt("Bearer %s" % jwt)
        self.assertEqual(result, _sanitize(uid))

    @settings(max_examples=100)
    @given(st.integers(min_value=0, max_value=99))
    def test_no_claims_raises_value_error(self, _iteration: int) -> None:
        """When no oid/sub/uid claims exist, ValueError is raised."""
        jwt = _make_jwt({"iss": "https://example.com", "aud": "my-app"})
        with self.assertRaises(ValueError):
            _extract_user_id_from_jwt("Bearer %s" % jwt)

    @settings(max_examples=100)
    @given(st.integers(min_value=0, max_value=99))
    def test_empty_auth_header_returns_local(self, _iteration: int) -> None:
        """Empty authorization header returns 'local'."""
        result = _extract_user_id_from_jwt("")
        self.assertEqual(result, "local")


if __name__ == "__main__":
    unittest.main()
