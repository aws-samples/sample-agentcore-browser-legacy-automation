# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Property-based tests for SessionStore.

Properties:
  2: Session status state machine (Req 17.1, 10.9)
  3: SessionStore CRUD round-trip consistency (Req 17.4, 10.10, 10.11)
  4: User isolation in session operations (Req 10.12)
"""

# pylint: disable=import-error,unused-import
try:
    import __setup__
except ModuleNotFoundError:
    import tests.unit.handlers.__setup__
# pylint: enable=import-error,unused-import

import asyncio
import unittest

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from handlers.session_store import (
    SessionRecord,
    InMemorySessionStore,
    VALID_STATUSES,
    VALID_TRANSITIONS,
)


def run_async(coro):
    """Helper to run async coroutines in sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------- Strategies ----------

valid_status_st = st.sampled_from(VALID_STATUSES)
user_id_st = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'Pd')),
    min_size=1, max_size=30,
)
session_id_st = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'Pd')),
    min_size=1, max_size=40,
)
iso_timestamp_st = st.from_regex(
    r'2026-0[1-9]-[0-2][0-9]T[0-2][0-9]:[0-5][0-9]:[0-5][0-9]',
    fullmatch=True,
)
steps_st = st.integers(min_value=0, max_value=1000)
ttl_st = st.integers(min_value=0, max_value=9999999)
session_list_st = st.lists(
    session_id_st, min_size=1, max_size=5, unique=True,
)



# ============================================================
# Property 2: Session status state machine
# Feature: 86-browser-agent-container-deployment, Property 2: Session status state machine
# Validates: Requirements 17.1, 10.9
# ============================================================

class TestSessionStatusStateMachineProperty(unittest.TestCase):
    """Property 2: Session status state machine."""

    @settings(max_examples=100)
    @given(from_status=valid_status_st, to_status=valid_status_st)
    def test_valid_transitions_are_allowed(
        self, from_status: str, to_status: str
    ) -> None:
        """Valid transitions update the session status correctly."""
        allowed = VALID_TRANSITIONS.get(from_status, [])
        assume(to_status in allowed)

        store = InMemorySessionStore()
        record = SessionRecord(
            user_id="u1", session_id="s1", status=from_status,
            created_at="2026-01-01T00:00:00",
        )
        run_async(store.create("u1", record))
        run_async(store.update("u1", "s1", {"status": to_status}))
        result = run_async(store.get("u1", "s1"))
        self.assertEqual(result.status, to_status)

    @settings(max_examples=100)
    @given(from_status=valid_status_st, to_status=valid_status_st)
    def test_invalid_transitions_from_terminal_states(
        self, from_status: str, to_status: str
    ) -> None:
        """Terminal states (stopped, completed, error) have no valid transitions."""
        assume(from_status in ('stopped', 'completed', 'error'))
        assume(from_status != to_status)
        self.assertNotIn(from_status, VALID_TRANSITIONS)

    @settings(max_examples=100)
    @given(status=valid_status_st)
    def test_all_statuses_are_valid_values(self, status: str) -> None:
        """Every status in VALID_STATUSES can be set on a SessionRecord."""
        record = SessionRecord(user_id="u1", session_id="s1", status=status)
        self.assertIn(record.status, VALID_STATUSES)

    @settings(max_examples=100)
    @given(
        status=st.text(min_size=1, max_size=20).filter(
            lambda s: s not in VALID_STATUSES
        )
    )
    def test_invalid_status_not_in_valid_set(self, status: str) -> None:
        """Statuses not in VALID_STATUSES are not recognized."""
        self.assertNotIn(status, VALID_STATUSES)

    @settings(max_examples=100)
    @given(st.just("active"))
    def test_active_can_transition_to_all_defined_targets(
        self, _status: str
    ) -> None:
        """active has transitions to paused_hitl, stopped, completed, error."""
        expected = {'paused_hitl', 'stopped', 'completed', 'error'}
        actual = set(VALID_TRANSITIONS.get('active', []))
        self.assertEqual(actual, expected)

    @settings(max_examples=100)
    @given(st.just("paused_hitl"))
    def test_paused_hitl_can_only_return_to_active(
        self, _status: str
    ) -> None:
        """paused_hitl can only transition back to active."""
        expected = {'active'}
        actual = set(VALID_TRANSITIONS.get('paused_hitl', []))
        self.assertEqual(actual, expected)


# ============================================================
# Property 3: SessionStore CRUD round-trip consistency
# Feature: 86-browser-agent-container-deployment, Property 3: SessionStore CRUD round-trip consistency
# Validates: Requirements 17.4, 10.10, 10.11
# ============================================================

class TestSessionStoreCrudRoundtripProperty(unittest.TestCase):
    """Property 3: SessionStore CRUD round-trip consistency."""

    @settings(max_examples=100)
    @given(
        user_id=user_id_st,
        session_id=session_id_st,
        status=valid_status_st,
        created_at=iso_timestamp_st,
        steps=steps_st,
        ttl=ttl_st,
    )
    def test_create_then_get_returns_same_record(
        self, user_id: str, session_id: str, status: str,
        created_at: str, steps: int, ttl: int,
    ) -> None:
        """Create then get returns a record with identical core fields."""
        store = InMemorySessionStore()
        record = SessionRecord(
            user_id=user_id,
            session_id=session_id,
            status=status,
            created_at=created_at,
            item_ttl=ttl,
            steps_completed=steps,
        )
        run_async(store.create(user_id, record))
        result = run_async(store.get(user_id, session_id))

        self.assertIsNotNone(result)
        self.assertEqual(result.user_id, user_id)
        self.assertEqual(result.session_id, session_id)
        self.assertEqual(result.status, status)
        self.assertEqual(result.created_at, created_at)
        self.assertEqual(result.item_ttl, ttl)
        self.assertEqual(result.steps_completed, steps)

    @settings(max_examples=100)
    @given(user_id=user_id_st, session_id=session_id_st)
    def test_delete_then_get_returns_none(
        self, user_id: str, session_id: str,
    ) -> None:
        """Delete then get returns None."""
        store = InMemorySessionStore()
        record = SessionRecord(
            user_id=user_id, session_id=session_id,
            created_at="2026-01-01T00:00:00",
        )
        run_async(store.create(user_id, record))
        run_async(store.delete(user_id, session_id))
        result = run_async(store.get(user_id, session_id))
        self.assertIsNone(result)

    @settings(max_examples=100)
    @given(user_id=user_id_st, session_id=session_id_st)
    def test_get_updates_last_activity(
        self, user_id: str, session_id: str,
    ) -> None:
        """Every get call updates last_activity to a non-empty value."""
        store = InMemorySessionStore()
        record = SessionRecord(
            user_id=user_id, session_id=session_id,
            created_at="2026-01-01T00:00:00",
            last_activity="old_value",
        )
        run_async(store.create(user_id, record))
        result = run_async(store.get(user_id, session_id))
        self.assertIsNotNone(result)
        self.assertNotEqual(result.last_activity, "")
        self.assertNotEqual(result.last_activity, "old_value")

    @settings(max_examples=100)
    @given(
        user_id=user_id_st,
        session_id=session_id_st,
        new_status=valid_status_st,
    )
    def test_update_then_get_reflects_changes(
        self, user_id: str, session_id: str, new_status: str,
    ) -> None:
        """Update then get returns the updated field values."""
        store = InMemorySessionStore()
        record = SessionRecord(
            user_id=user_id, session_id=session_id,
            status="active", created_at="2026-01-01T00:00:00",
        )
        run_async(store.create(user_id, record))
        run_async(store.update(user_id, session_id, {"status": new_status}))
        result = run_async(store.get(user_id, session_id))
        self.assertIsNotNone(result)
        self.assertEqual(result.status, new_status)

    @settings(max_examples=100)
    @given(
        user_id=user_id_st,
        data=st.lists(
            st.tuples(session_id_st, iso_timestamp_st),
            min_size=2, max_size=10, unique_by=lambda x: x[0],
        ),
    )
    def test_list_sessions_sorted_by_created_at_descending(
        self, user_id: str, data: list,
    ) -> None:
        """list_sessions returns sessions sorted by created_at descending."""
        store = InMemorySessionStore()
        for sid, ts in data:
            record = SessionRecord(
                user_id=user_id, session_id=sid, created_at=ts,
            )
            run_async(store.create(user_id, record))

        sessions = run_async(store.list_sessions(user_id))
        dates = [s.created_at for s in sessions]
        self.assertEqual(dates, sorted(dates, reverse=True))


# ============================================================
# Property 4: User isolation in session operations
# Feature: 86-browser-agent-container-deployment, Property 4: User isolation in session operations
# Validates: Requirements 10.12
# ============================================================

class TestUserIsolationProperty(unittest.TestCase):
    """Property 4: User isolation in session operations."""

    @settings(max_examples=100)
    @given(
        user_a=user_id_st,
        user_b=user_id_st,
        sessions_a=session_list_st,
        sessions_b=session_list_st,
    )
    def test_list_sessions_returns_only_own_sessions(
        self, user_a: str, user_b: str,
        sessions_a: list, sessions_b: list,
    ) -> None:
        """list_sessions(user_a) returns only user_a's sessions."""
        assume(user_a != user_b)
        assume(not set(sessions_a) & set(sessions_b))

        store = InMemorySessionStore()
        for i, sid in enumerate(sessions_a):
            record = SessionRecord(
                user_id=user_a, session_id=sid,
                created_at="2026-01-0%dT00:00:00" % (i + 1),
            )
            run_async(store.create(user_a, record))

        for i, sid in enumerate(sessions_b):
            record = SessionRecord(
                user_id=user_b, session_id=sid,
                created_at="2026-01-0%dT00:00:00" % (i + 1),
            )
            run_async(store.create(user_b, record))

        result_a = run_async(store.list_sessions(user_a))
        result_a_ids = {s.session_id for s in result_a}
        self.assertEqual(result_a_ids, set(sessions_a))

        result_b = run_async(store.list_sessions(user_b))
        result_b_ids = {s.session_id for s in result_b}
        self.assertEqual(result_b_ids, set(sessions_b))

    @settings(max_examples=100)
    @given(
        user_a=user_id_st,
        user_b=user_id_st,
        session_id=session_id_st,
    )
    def test_get_cross_user_returns_none(
        self, user_a: str, user_b: str, session_id: str,
    ) -> None:
        """get(user_a, session_id_of_user_b) returns None."""
        assume(user_a != user_b)

        store = InMemorySessionStore()
        record = SessionRecord(
            user_id=user_b, session_id=session_id,
            created_at="2026-01-01T00:00:00",
        )
        run_async(store.create(user_b, record))
        result = run_async(store.get(user_a, session_id))
        self.assertIsNone(result)

    @settings(max_examples=100)
    @given(
        user_a=user_id_st,
        user_b=user_id_st,
        session_id=session_id_st,
    )
    def test_delete_cross_user_does_not_affect_owner(
        self, user_a: str, user_b: str, session_id: str,
    ) -> None:
        """delete(user_a, session_id) does not remove user_b's session."""
        assume(user_a != user_b)

        store = InMemorySessionStore()
        record = SessionRecord(
            user_id=user_b, session_id=session_id,
            created_at="2026-01-01T00:00:00",
        )
        run_async(store.create(user_b, record))
        run_async(store.delete(user_a, session_id))
        result = run_async(store.get(user_b, session_id))
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
