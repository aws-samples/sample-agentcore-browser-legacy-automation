# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Unit tests for session store — CRUD for all three backends,
status transitions, list ordering, TTL, user isolation, factory.

Validates: Requirements 16.3
"""

# pylint: disable=import-error,unused-import
try:
    import __setup__
except ModuleNotFoundError:
    import tests.unit.handlers.__setup__
# pylint: enable=import-error,unused-import

import asyncio
import json
import os
import unittest
from decimal import Decimal
from io import BytesIO
from unittest.mock import MagicMock, patch, call

from handlers.session_store import (
    SessionRecord,
    InMemorySessionStore,
    DynamoDBSessionStore,
    S3SessionStore,
    create_session_store,
    VALID_STATUSES,
    VALID_TRANSITIONS,
    _now_iso,
)


def run_async(coro):
    """Helper to run async coroutines in sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


class TestSessionRecord(unittest.TestCase):
    """Tests for SessionRecord dataclass."""

    def test_default_values(self) -> None:
        """SessionRecord has correct defaults."""
        record = SessionRecord(user_id="u1", session_id="s1")
        self.assertEqual(record.user_id, "u1")
        self.assertEqual(record.session_id, "s1")
        self.assertEqual(record.status, "active")
        self.assertEqual(record.browser_session_id, "")
        self.assertEqual(record.created_at, "")
        self.assertEqual(record.last_activity, "")
        self.assertEqual(record.item_ttl, 0)
        self.assertEqual(record.steps_completed, 0)
        self.assertEqual(record.live_view_url, "")
        self.assertEqual(record.conversation_history, [])
        self.assertEqual(record.screenshots, [])

    def test_custom_values(self) -> None:
        """SessionRecord accepts custom field values."""
        history = [{"role": "user", "content": "hello", "timestamp": "t1"}]
        screenshots = [{"timestamp": "t1", "title": "home", "filename": "home.png"}]
        record = SessionRecord(
            user_id="u1", session_id="s1",
            browser_session_id="bsid", status="paused_hitl",
            created_at="2026-01-01T00:00:00", last_activity="2026-01-01T00:01:00",
            item_ttl=9999, steps_completed=5, live_view_url="https://example.com",
            conversation_history=history, screenshots=screenshots,
        )
        self.assertEqual(record.status, "paused_hitl")
        self.assertEqual(record.steps_completed, 5)
        self.assertEqual(len(record.conversation_history), 1)
        self.assertEqual(len(record.screenshots), 1)

    def test_valid_statuses_defined(self) -> None:
        """VALID_STATUSES contains all expected values."""
        expected = {'active', 'paused_hitl', 'completed', 'stopped', 'error'}
        self.assertEqual(set(VALID_STATUSES), expected)

    def test_valid_transitions_defined(self) -> None:
        """VALID_TRANSITIONS maps active and paused_hitl correctly."""
        self.assertIn('paused_hitl', VALID_TRANSITIONS['active'])
        self.assertIn('stopped', VALID_TRANSITIONS['active'])
        self.assertIn('completed', VALID_TRANSITIONS['active'])
        self.assertIn('error', VALID_TRANSITIONS['active'])
        self.assertIn('active', VALID_TRANSITIONS['paused_hitl'])



class TestInMemorySessionStore(unittest.TestCase):
    """Tests for InMemorySessionStore CRUD operations."""

    def setUp(self) -> None:
        self.store = InMemorySessionStore()

    def test_create_and_get(self) -> None:
        """Create then get returns the same record."""
        record = SessionRecord(user_id="u1", session_id="s1", status="active")
        run_async(self.store.create("u1", record))
        result = run_async(self.store.get("u1", "s1"))
        self.assertIsNotNone(result)
        self.assertEqual(result.user_id, "u1")
        self.assertEqual(result.session_id, "s1")
        self.assertEqual(result.status, "active")

    def test_create_sets_timestamps(self) -> None:
        """Create sets created_at and last_activity if empty."""
        record = SessionRecord(user_id="u1", session_id="s1")
        run_async(self.store.create("u1", record))
        result = run_async(self.store.get("u1", "s1"))
        self.assertNotEqual(result.created_at, "")
        self.assertNotEqual(result.last_activity, "")

    def test_create_preserves_existing_created_at(self) -> None:
        """Create preserves pre-set created_at."""
        record = SessionRecord(
            user_id="u1", session_id="s1", created_at="2026-01-01T00:00:00"
        )
        run_async(self.store.create("u1", record))
        result = run_async(self.store.get("u1", "s1"))
        self.assertEqual(result.created_at, "2026-01-01T00:00:00")

    def test_get_nonexistent_returns_none(self) -> None:
        """Get on missing session returns None."""
        result = run_async(self.store.get("u1", "nonexistent"))
        self.assertIsNone(result)

    def test_get_updates_last_activity(self) -> None:
        """Get updates last_activity timestamp."""
        record = SessionRecord(
            user_id="u1", session_id="s1", last_activity="old"
        )
        run_async(self.store.create("u1", record))
        result = run_async(self.store.get("u1", "s1"))
        self.assertNotEqual(result.last_activity, "old")

    def test_update_applies_changes(self) -> None:
        """Update modifies specified fields."""
        record = SessionRecord(user_id="u1", session_id="s1", status="active")
        run_async(self.store.create("u1", record))
        run_async(self.store.update("u1", "s1", {"status": "paused_hitl", "steps_completed": 3}))
        result = run_async(self.store.get("u1", "s1"))
        self.assertEqual(result.status, "paused_hitl")
        self.assertEqual(result.steps_completed, 3)

    def test_update_nonexistent_no_error(self) -> None:
        """Update on missing session does not raise."""
        run_async(self.store.update("u1", "missing", {"status": "stopped"}))

    def test_update_updates_last_activity(self) -> None:
        """Update refreshes last_activity."""
        record = SessionRecord(
            user_id="u1", session_id="s1", last_activity="old"
        )
        run_async(self.store.create("u1", record))
        run_async(self.store.update("u1", "s1", {"status": "stopped"}))
        result = run_async(self.store.get("u1", "s1"))
        self.assertNotEqual(result.last_activity, "old")

    def test_delete_removes_session(self) -> None:
        """Delete then get returns None."""
        record = SessionRecord(user_id="u1", session_id="s1")
        run_async(self.store.create("u1", record))
        run_async(self.store.delete("u1", "s1"))
        result = run_async(self.store.get("u1", "s1"))
        self.assertIsNone(result)

    def test_delete_nonexistent_no_error(self) -> None:
        """Delete on missing session does not raise."""
        run_async(self.store.delete("u1", "missing"))

    def test_list_sessions_returns_user_sessions(self) -> None:
        """list_sessions returns only the specified user's sessions."""
        for i in range(3):
            record = SessionRecord(
                user_id="u1", session_id="s%d" % i,
                created_at="2026-01-0%dT00:00:00" % (i + 1),
            )
            run_async(self.store.create("u1", record))
        sessions = run_async(self.store.list_sessions("u1"))
        self.assertEqual(len(sessions), 3)

    def test_list_sessions_sorted_descending(self) -> None:
        """list_sessions returns sessions sorted by created_at descending."""
        for i in range(3):
            record = SessionRecord(
                user_id="u1", session_id="s%d" % i,
                created_at="2026-01-0%dT00:00:00" % (i + 1),
            )
            run_async(self.store.create("u1", record))
        sessions = run_async(self.store.list_sessions("u1"))
        dates = [s.created_at for s in sessions]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_list_sessions_respects_limit(self) -> None:
        """list_sessions respects the limit parameter."""
        for i in range(5):
            record = SessionRecord(
                user_id="u1", session_id="s%d" % i,
                created_at="2026-01-0%dT00:00:00" % (i + 1),
            )
            run_async(self.store.create("u1", record))
        sessions = run_async(self.store.list_sessions("u1", limit=2))
        self.assertEqual(len(sessions), 2)

    def test_user_isolation(self) -> None:
        """User A cannot see User B's sessions."""
        rec_a = SessionRecord(user_id="user_a", session_id="sa1")
        rec_b = SessionRecord(user_id="user_b", session_id="sb1")
        run_async(self.store.create("user_a", rec_a))
        run_async(self.store.create("user_b", rec_b))

        # user_a sees only their session
        sessions_a = run_async(self.store.list_sessions("user_a"))
        self.assertEqual(len(sessions_a), 1)
        self.assertEqual(sessions_a[0].session_id, "sa1")

        # user_a cannot get user_b's session
        cross = run_async(self.store.get("user_a", "sb1"))
        self.assertIsNone(cross)



class TestDynamoDBSessionStore(unittest.TestCase):
    """Tests for DynamoDBSessionStore with mocked boto3."""

    def setUp(self) -> None:
        self.mock_table = MagicMock()
        with patch(
            'handlers.session_store.get_boto3_session'
        ) as mock_session, patch(
            'handlers.session_store.get_boto3_client_config'
        ):
            mock_resource = MagicMock()
            mock_resource.Table.return_value = self.mock_table
            mock_session.return_value.resource.return_value = mock_resource
            self.store = DynamoDBSessionStore(table_name="test-table")

    def test_create_puts_item(self) -> None:
        """Create calls put_item with correct key schema."""
        record = SessionRecord(user_id="u1", session_id="s1", status="active")
        run_async(self.store.create("u1", record))
        self.mock_table.put_item.assert_called_once()
        item = self.mock_table.put_item.call_args[1]['Item']
        self.assertEqual(item['pk'], "u1")
        self.assertEqual(item['sk'], "s1")
        self.assertEqual(item['status'], "active")
        self.assertNotEqual(item['created_at'], "")
        self.assertNotEqual(item['last_activity'], "")

    def test_create_preserves_existing_created_at(self) -> None:
        """Create preserves pre-set created_at."""
        record = SessionRecord(
            user_id="u1", session_id="s1",
            created_at="2026-01-01T00:00:00",
        )
        run_async(self.store.create("u1", record))
        item = self.mock_table.put_item.call_args[1]['Item']
        self.assertEqual(item['created_at'], "2026-01-01T00:00:00")

    def test_get_returns_record(self) -> None:
        """Get returns SessionRecord from DDB item."""
        self.mock_table.get_item.return_value = {
            'Item': {
                'pk': 'u1', 'sk': 's1', 'status': 'active',
                'created_at': '2026-01-01T00:00:00',
                'last_activity': '2026-01-01T00:00:00',
                'browser_session_id': 'bsid',
                'item_ttl': Decimal('9999'),
                'steps_completed': Decimal('3'),
                'live_view_url': '',
                'conversation_history': [],
                'screenshots': [],
            }
        }
        result = run_async(self.store.get("u1", "s1"))
        self.assertIsNotNone(result)
        self.assertEqual(result.user_id, "u1")
        self.assertEqual(result.session_id, "s1")
        self.assertEqual(result.item_ttl, 9999)
        self.assertEqual(result.steps_completed, 3)
        # Verify last_activity was updated
        self.mock_table.update_item.assert_called_once()

    def test_get_nonexistent_returns_none(self) -> None:
        """Get on missing item returns None."""
        self.mock_table.get_item.return_value = {}
        result = run_async(self.store.get("u1", "missing"))
        self.assertIsNone(result)

    def test_update_calls_update_item(self) -> None:
        """Update calls update_item with expression."""
        run_async(self.store.update("u1", "s1", {"status": "stopped"}))
        self.mock_table.update_item.assert_called_once()
        kwargs = self.mock_table.update_item.call_args[1]
        self.assertEqual(kwargs['Key'], {'pk': 'u1', 'sk': 's1'})
        self.assertIn('SET', kwargs['UpdateExpression'])

    def test_update_includes_last_activity(self) -> None:
        """Update always includes last_activity in the expression."""
        run_async(self.store.update("u1", "s1", {"status": "stopped"}))
        kwargs = self.mock_table.update_item.call_args[1]
        # last_activity should be in the attribute values
        values = kwargs['ExpressionAttributeValues']
        has_last_activity = any(
            'last_activity' in str(kwargs['ExpressionAttributeNames'].get(k, ''))
            for k in kwargs['ExpressionAttributeNames']
        )
        self.assertTrue(has_last_activity)

    def test_update_empty_dict_no_call(self) -> None:
        """Update with empty dict does not call update_item."""
        run_async(self.store.update("u1", "s1", {}))
        self.mock_table.update_item.assert_not_called()

    def test_delete_calls_delete_item(self) -> None:
        """Delete calls delete_item with correct key."""
        run_async(self.store.delete("u1", "s1"))
        self.mock_table.delete_item.assert_called_once_with(
            Key={'pk': 'u1', 'sk': 's1'}
        )

    def test_list_sessions_queries_by_user(self) -> None:
        """list_sessions queries with pk = user_id."""
        self.mock_table.query.return_value = {
            'Items': [
                {
                    'pk': 'u1', 'sk': 's1', 'status': 'active',
                    'created_at': '2026-01-02T00:00:00',
                    'last_activity': '', 'browser_session_id': '',
                    'item_ttl': 0, 'steps_completed': 0,
                    'live_view_url': '', 'conversation_history': [],
                    'screenshots': [],
                },
                {
                    'pk': 'u1', 'sk': 's2', 'status': 'completed',
                    'created_at': '2026-01-01T00:00:00',
                    'last_activity': '', 'browser_session_id': '',
                    'item_ttl': 0, 'steps_completed': 0,
                    'live_view_url': '', 'conversation_history': [],
                    'screenshots': [],
                },
            ]
        }
        sessions = run_async(self.store.list_sessions("u1"))
        self.assertEqual(len(sessions), 2)
        # Sorted by created_at descending
        self.assertEqual(sessions[0].session_id, "s1")
        self.assertEqual(sessions[1].session_id, "s2")

    def test_list_sessions_respects_limit(self) -> None:
        """list_sessions passes limit to DDB query."""
        self.mock_table.query.return_value = {'Items': []}
        run_async(self.store.list_sessions("u1", limit=5))
        kwargs = self.mock_table.query.call_args[1]
        self.assertEqual(kwargs['Limit'], 5)

    def test_item_to_record_handles_decimals(self) -> None:
        """_item_to_record converts DDB Decimal to int."""
        item = {
            'pk': 'u1', 'sk': 's1', 'status': 'active',
            'created_at': '', 'last_activity': '',
            'browser_session_id': '',
            'item_ttl': Decimal('3600'),
            'steps_completed': Decimal('10'),
            'live_view_url': '',
            'conversation_history': [],
            'screenshots': [],
        }
        record = DynamoDBSessionStore._item_to_record(item)
        self.assertIsInstance(record.item_ttl, int)
        self.assertIsInstance(record.steps_completed, int)
        self.assertEqual(record.item_ttl, 3600)
        self.assertEqual(record.steps_completed, 10)



class TestS3SessionStore(unittest.TestCase):
    """Tests for S3SessionStore with mocked boto3."""

    def setUp(self) -> None:
        self.mock_client = MagicMock()
        with patch(
            'handlers.session_store.get_boto3_session'
        ) as mock_session, patch(
            'handlers.session_store.get_boto3_client_config'
        ):
            mock_session.return_value.client.return_value = self.mock_client
            self.store = S3SessionStore(bucket="amzn-s3-demo-bucket", prefix="test-prefix")

    def test_create_puts_session_json(self) -> None:
        """Create writes session.json to correct S3 key."""
        record = SessionRecord(user_id="u1", session_id="s1", status="active")
        run_async(self.store.create("u1", record))
        self.mock_client.put_object.assert_called_once()
        kwargs = self.mock_client.put_object.call_args[1]
        self.assertEqual(kwargs['Bucket'], "amzn-s3-demo-bucket")
        self.assertEqual(kwargs['Key'], "test-prefix/u1/s1/session.json")
        self.assertEqual(kwargs['ContentType'], "application/json")
        # Verify body is valid JSON with correct fields
        body = json.loads(kwargs['Body'])
        self.assertEqual(body['user_id'], "u1")
        self.assertEqual(body['session_id'], "s1")

    def test_create_sets_timestamps(self) -> None:
        """Create sets created_at and last_activity."""
        record = SessionRecord(user_id="u1", session_id="s1")
        run_async(self.store.create("u1", record))
        body = json.loads(self.mock_client.put_object.call_args[1]['Body'])
        self.assertNotEqual(body['created_at'], "")
        self.assertNotEqual(body['last_activity'], "")

    def test_get_reads_session_json(self) -> None:
        """Get reads and deserializes session.json."""
        session_data = {
            'user_id': 'u1', 'session_id': 's1',
            'browser_session_id': '', 'status': 'active',
            'created_at': '2026-01-01T00:00:00',
            'last_activity': '2026-01-01T00:00:00',
            'item_ttl': 0, 'steps_completed': 2,
            'live_view_url': '', 'conversation_history': [],
            'screenshots': [],
        }
        body_bytes = json.dumps(session_data).encode('utf-8')
        self.mock_client.get_object.return_value = {
            'Body': BytesIO(body_bytes)
        }
        result = run_async(self.store.get("u1", "s1"))
        self.assertIsNotNone(result)
        self.assertEqual(result.user_id, "u1")
        self.assertEqual(result.steps_completed, 2)
        # Verify last_activity was updated (put_object called to write back)
        self.assertEqual(self.mock_client.put_object.call_count, 1)

    def test_get_nonexistent_returns_none(self) -> None:
        """Get on missing key returns None."""
        error_response = {'Error': {'Code': 'NoSuchKey', 'Message': 'Not found'}}
        self.mock_client.exceptions.NoSuchKey = type(
            'NoSuchKey', (Exception,), {}
        )
        self.mock_client.get_object.side_effect = (
            self.mock_client.exceptions.NoSuchKey(error_response, 'GetObject')
        )
        result = run_async(self.store.get("u1", "missing"))
        self.assertIsNone(result)

    def test_update_read_modify_write(self) -> None:
        """Update reads, modifies, and writes back."""
        session_data = {
            'user_id': 'u1', 'session_id': 's1',
            'browser_session_id': '', 'status': 'active',
            'created_at': '2026-01-01T00:00:00',
            'last_activity': '2026-01-01T00:00:00',
            'item_ttl': 0, 'steps_completed': 0,
            'live_view_url': '', 'conversation_history': [],
            'screenshots': [],
        }
        body_bytes = json.dumps(session_data).encode('utf-8')
        self.mock_client.get_object.return_value = {
            'Body': BytesIO(body_bytes)
        }
        run_async(self.store.update("u1", "s1", {"status": "stopped", "steps_completed": 5}))
        # get calls put_object once (last_activity update), update calls it again
        self.assertEqual(self.mock_client.put_object.call_count, 2)
        last_put = self.mock_client.put_object.call_args_list[-1]
        body = json.loads(last_put[1]['Body'])
        self.assertEqual(body['status'], "stopped")
        self.assertEqual(body['steps_completed'], 5)

    def test_delete_removes_all_objects(self) -> None:
        """Delete lists and removes all objects under session prefix."""
        self.mock_client.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'test-prefix/u1/s1/session.json'},
                {'Key': 'test-prefix/u1/s1/screenshots/img.png'},
            ]
        }
        run_async(self.store.delete("u1", "s1"))
        self.mock_client.delete_objects.assert_called_once()
        delete_arg = self.mock_client.delete_objects.call_args[1]['Delete']
        self.assertEqual(len(delete_arg['Objects']), 2)

    def test_delete_empty_prefix_no_delete_call(self) -> None:
        """Delete with no objects does not call delete_objects."""
        self.mock_client.list_objects_v2.return_value = {'Contents': []}
        run_async(self.store.delete("u1", "s1"))
        self.mock_client.delete_objects.assert_not_called()

    def test_list_sessions_uses_common_prefixes(self) -> None:
        """list_sessions uses CommonPrefixes to discover sessions."""
        session_data = {
            'user_id': 'u1', 'session_id': 's1',
            'browser_session_id': '', 'status': 'active',
            'created_at': '2026-01-01T00:00:00',
            'last_activity': '', 'item_ttl': 0,
            'steps_completed': 0, 'live_view_url': '',
            'conversation_history': [], 'screenshots': [],
        }
        self.mock_client.list_objects_v2.return_value = {
            'CommonPrefixes': [
                {'Prefix': 'test-prefix/u1/s1/'},
            ]
        }
        body_bytes = json.dumps(session_data).encode('utf-8')
        self.mock_client.get_object.return_value = {
            'Body': BytesIO(body_bytes)
        }
        sessions = run_async(self.store.list_sessions("u1"))
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].session_id, "s1")
        # Verify list call used correct prefix and delimiter
        list_kwargs = self.mock_client.list_objects_v2.call_args[1]
        self.assertEqual(list_kwargs['Prefix'], "test-prefix/u1/")
        self.assertEqual(list_kwargs['Delimiter'], "/")

    def test_session_key_format(self) -> None:
        """_session_key builds correct S3 path."""
        key = self.store._session_key("user_abc", "brws_20260101_120000_abcd1234")
        self.assertEqual(
            key,
            "test-prefix/user_abc/brws_20260101_120000_abcd1234/session.json"
        )



class TestCreateSessionStoreFactory(unittest.TestCase):
    """Tests for create_session_store factory function."""

    def test_memory_returns_in_memory_store(self) -> None:
        """Factory returns InMemorySessionStore for 'memory'."""
        store = create_session_store("memory")
        self.assertIsInstance(store, InMemorySessionStore)

    @patch.dict(os.environ, {
        'BA_SESSION_STORE_TABLE': 'my-table',
    })
    @patch('handlers.session_store.get_boto3_session')
    @patch('handlers.session_store.get_boto3_client_config')
    def test_dynamodb_returns_dynamodb_store(
        self, _mock_config, mock_session
    ) -> None:
        """Factory returns DynamoDBSessionStore for 'dynamodb'."""
        mock_resource = MagicMock()
        mock_session.return_value.resource.return_value = mock_resource
        store = create_session_store("dynamodb")
        self.assertIsInstance(store, DynamoDBSessionStore)

    @patch.dict(os.environ, {
        'BA_SESSION_STORE_BUCKET': 'my-bucket',
        'BA_SESSION_STORE_PREFIX': 'my-prefix',
    })
    @patch('handlers.session_store.get_boto3_session')
    @patch('handlers.session_store.get_boto3_client_config')
    def test_s3_returns_s3_store(self, _mock_config, mock_session) -> None:
        """Factory returns S3SessionStore for 's3'."""
        mock_session.return_value.client.return_value = MagicMock()
        store = create_session_store("s3")
        self.assertIsInstance(store, S3SessionStore)

    @patch.dict(os.environ, {
        'BA_SESSION_STORE_BUCKET': 'my-bucket',
    })
    @patch('handlers.session_store.get_boto3_session')
    @patch('handlers.session_store.get_boto3_client_config')
    def test_s3_uses_default_prefix(self, _mock_config, mock_session) -> None:
        """Factory uses default prefix 'browser-sessions' for S3."""
        mock_session.return_value.client.return_value = MagicMock()
        store = create_session_store("s3")
        self.assertEqual(store._prefix, "browser-sessions")

    def test_unknown_type_returns_in_memory(self) -> None:
        """Factory defaults to InMemorySessionStore for unknown types."""
        store = create_session_store("unknown")
        self.assertIsInstance(store, InMemorySessionStore)


if __name__ == "__main__":
    unittest.main()
