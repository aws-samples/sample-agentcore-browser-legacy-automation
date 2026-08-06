# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Pluggable session store with three backends: in-memory, DynamoDB, S3.

Provides SessionRecord dataclass and SessionStoreBase ABC with async CRUD
methods. Backend is selected at startup via BA_SESSION_STORE_TYPE env var.

Validates: Requirements 10.1–10.12
"""

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from logging import Logger
from typing import Dict, List, Optional, Tuple

from utils.logging_helper import get_logger
from utils.session_helper import get_boto3_session, get_boto3_client_config


# Valid session status values
VALID_STATUSES: List[str] = ['active', 'paused_hitl', 'completed', 'stopped', 'error']

# Valid status transitions: source -> set of allowed targets
VALID_TRANSITIONS: Dict[str, List[str]] = {
    'active': ['paused_hitl', 'stopped', 'completed', 'error'],
    'paused_hitl': ['active'],
}


@dataclass
class SessionRecord:
    """Data structure tracking a browser automation session.

    Attributes:
        user_id: Partition key — from JWT (sanitized).
        session_id: Sort key — brws_{YYYYMMDD}_{HHMMSS}_{hex8}.
        browser_session_id: Internal AgentCore Browser microVM ID.
        status: One of active, paused_hitl, completed, stopped, error.
        created_at: ISO 8601 timestamp.
        last_activity: ISO 8601 timestamp, updated on every access.
        item_ttl: DDB TTL epoch for auto-cleanup.
        steps_completed: Count of browser actions.
        live_view_url: Temporary DCV URL.
        conversation_history: List of {role, content, timestamp} dicts.
        screenshots: List of {timestamp, title, filename} metadata dicts.
    """

    user_id: str
    session_id: str
    browser_session_id: str = ""
    status: str = "active"
    created_at: str = ""
    last_activity: str = ""
    item_ttl: int = 0
    steps_completed: int = 0
    live_view_url: str = ""
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    screenshots: List[Dict[str, str]] = field(default_factory=list)


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()



class SessionStoreBase(ABC):
    """Abstract base class for session persistence backends.

    All operations are scoped by user_id — a user can only access
    their own sessions. Every get/update call updates last_activity.
    """

    @abstractmethod
    async def create(self, user_id: str, session: SessionRecord) -> None:
        """Persist a new session record."""
        ...

    @abstractmethod
    async def get(self, user_id: str, session_id: str) -> Optional[SessionRecord]:
        """Retrieve a session by user_id + session_id. Returns None if not found."""
        ...

    @abstractmethod
    async def update(self, user_id: str, session_id: str, updates: dict) -> None:
        """Apply partial updates to an existing session."""
        ...

    @abstractmethod
    async def delete(self, user_id: str, session_id: str) -> None:
        """Remove a session record."""
        ...

    @abstractmethod
    async def list_sessions(
        self, user_id: str, limit: int = 20
    ) -> List[SessionRecord]:
        """List sessions for a user, sorted by created_at descending."""
        ...


class InMemorySessionStore(SessionStoreBase):
    """Dict-backed session store for local development and testing.

    Keyed by (user_id, session_id) tuples.
    """

    logger: Logger = get_logger(f"{__name__}.InMemorySessionStore")

    def __init__(self) -> None:
        self._store: Dict[Tuple[str, str], SessionRecord] = {}

    async def create(self, user_id: str, session: SessionRecord) -> None:
        """Store a new session record."""
        if not session.created_at:
            session.created_at = _now_iso()
        session.last_activity = _now_iso()
        self._store[(user_id, session.session_id)] = session
        self.logger.debug(
            "Created session: user=%s session=%s", user_id, session.session_id
        )

    async def get(self, user_id: str, session_id: str) -> Optional[SessionRecord]:
        """Retrieve session, updating last_activity on hit."""
        record = self._store.get((user_id, session_id))
        if record is not None:
            record.last_activity = _now_iso()
        return record

    async def update(self, user_id: str, session_id: str, updates: dict) -> None:
        """Apply partial updates to an existing session."""
        record = self._store.get((user_id, session_id))
        if record is None:
            self.logger.warning(
                "Update on missing session: user=%s session=%s", user_id, session_id
            )
            return
        for key, value in updates.items():
            if hasattr(record, key):
                setattr(record, key, value)
        record.last_activity = _now_iso()

    async def delete(self, user_id: str, session_id: str) -> None:
        """Remove session from store."""
        self._store.pop((user_id, session_id), None)
        self.logger.debug(
            "Deleted session: user=%s session=%s", user_id, session_id
        )

    async def list_sessions(
        self, user_id: str, limit: int = 20
    ) -> List[SessionRecord]:
        """Return user's sessions sorted by created_at descending."""
        sessions = [
            rec for (uid, _), rec in self._store.items() if uid == user_id
        ]
        sessions.sort(key=lambda s: s.created_at, reverse=True)
        return sessions[:limit]



class DynamoDBSessionStore(SessionStoreBase):
    """DynamoDB-backed session store with pk=user_id, sk=session_id.

    Uses item_ttl attribute for DDB TTL auto-cleanup. Table schema is
    documented in ``deployment/terraform/modules/dynamodb/``.
    """

    logger: Logger = get_logger(f"{__name__}.DynamoDBSessionStore")

    def __init__(self, table_name: str) -> None:
        session = get_boto3_session()
        self._table = session.resource(
            'dynamodb', config=get_boto3_client_config()
        ).Table(table_name)
        self._table_name: str = table_name

    async def create(self, user_id: str, session: SessionRecord) -> None:
        """Put session item into DynamoDB."""
        if not session.created_at:
            session.created_at = _now_iso()
        session.last_activity = _now_iso()
        item: dict = {
            'pk': user_id,
            'sk': session.session_id,
            'browser_session_id': session.browser_session_id,
            'status': session.status,
            'created_at': session.created_at,
            'last_activity': session.last_activity,
            'item_ttl': session.item_ttl,
            'steps_completed': session.steps_completed,
            'live_view_url': session.live_view_url,
            'conversation_history': session.conversation_history,
            'screenshots': session.screenshots,
        }
        self._table.put_item(Item=item)
        self.logger.debug(
            "Created DDB session: table=%s user=%s session=%s",
            self._table_name, user_id, session.session_id,
        )

    async def get(self, user_id: str, session_id: str) -> Optional[SessionRecord]:
        """Get session item, update last_activity on hit."""
        response = self._table.get_item(Key={'pk': user_id, 'sk': session_id})
        item = response.get('Item')
        if item is None:
            return None
        # Update last_activity
        now = _now_iso()
        self._table.update_item(
            Key={'pk': user_id, 'sk': session_id},
            UpdateExpression='SET last_activity = :la',
            ExpressionAttributeValues={':la': now},
        )
        return self._item_to_record(item, last_activity_override=now)

    async def update(self, user_id: str, session_id: str, updates: dict) -> None:
        """Apply partial updates via UpdateItem."""
        if not updates:
            return
        updates['last_activity'] = _now_iso()
        # Map field names to DDB attribute names (pk/sk are reserved)
        expr_parts: List[str] = []
        attr_values: dict = {}
        attr_names: dict = {}
        for i, (key, value) in enumerate(updates.items()):
            placeholder_name = "#k%d" % i
            placeholder_val = ":v%d" % i
            attr_names[placeholder_name] = key
            attr_values[placeholder_val] = value
            expr_parts.append("%s = %s" % (placeholder_name, placeholder_val))

        self._table.update_item(
            Key={'pk': user_id, 'sk': session_id},
            UpdateExpression='SET %s' % ', '.join(expr_parts),
            ExpressionAttributeNames=attr_names,
            ExpressionAttributeValues=attr_values,
        )

    async def delete(self, user_id: str, session_id: str) -> None:
        """Delete session item from DynamoDB."""
        self._table.delete_item(Key={'pk': user_id, 'sk': session_id})
        self.logger.debug(
            "Deleted DDB session: user=%s session=%s", user_id, session_id
        )

    async def list_sessions(
        self, user_id: str, limit: int = 20
    ) -> List[SessionRecord]:
        """Query sessions by user_id, sort by created_at descending."""
        response = self._table.query(
            KeyConditionExpression='pk = :uid',
            ExpressionAttributeValues={':uid': user_id},
            ScanIndexForward=False,
            Limit=limit,
        )
        records = [self._item_to_record(item) for item in response.get('Items', [])]
        records.sort(key=lambda s: s.created_at, reverse=True)
        return records[:limit]

    @staticmethod
    def _item_to_record(
        item: dict, last_activity_override: Optional[str] = None
    ) -> SessionRecord:
        """Convert DDB item dict to SessionRecord."""
        return SessionRecord(
            user_id=item.get('pk', ''),
            session_id=item.get('sk', ''),
            browser_session_id=item.get('browser_session_id', ''),
            status=item.get('status', 'active'),
            created_at=item.get('created_at', ''),
            last_activity=last_activity_override or item.get('last_activity', ''),
            item_ttl=int(item.get('item_ttl', 0)),
            steps_completed=int(item.get('steps_completed', 0)),
            live_view_url=item.get('live_view_url', ''),
            conversation_history=item.get('conversation_history', []),
            screenshots=item.get('screenshots', []),
        )



class S3SessionStore(SessionStoreBase):
    """S3-backed session store with session.json at
    {prefix}/{user_id}/{session_id}/session.json.

    Lists sessions via ListObjectsV2 with prefix and delimiter.
    Deletes sessions by removing the entire {session_id}/ prefix.
    """

    logger: Logger = get_logger(f"{__name__}.S3SessionStore")

    def __init__(self, bucket: str, prefix: str = "browser-sessions") -> None:
        session = get_boto3_session()
        self._client = session.client('s3', config=get_boto3_client_config())
        self._bucket: str = bucket
        self._prefix: str = prefix

    def _session_key(self, user_id: str, session_id: str) -> str:
        """Build S3 key for session.json."""
        return "%s/%s/%s/session.json" % (self._prefix, user_id, session_id)

    async def create(self, user_id: str, session: SessionRecord) -> None:
        """Write session.json to S3."""
        if not session.created_at:
            session.created_at = _now_iso()
        session.last_activity = _now_iso()
        key = self._session_key(user_id, session.session_id)
        body = json.dumps(asdict(session), default=str)
        self._client.put_object(
            Bucket=self._bucket, Key=key, Body=body,
            ContentType='application/json',
        )
        self.logger.debug(
            "Created S3 session: bucket=%s key=%s", self._bucket, key
        )

    async def get(self, user_id: str, session_id: str) -> Optional[SessionRecord]:
        """Read session.json from S3, update last_activity."""
        key = self._session_key(user_id, session_id)
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            data = json.loads(response['Body'].read().decode('utf-8'))
        except self._client.exceptions.NoSuchKey:
            return None
        except Exception as exc:
            self.logger.warning("S3 get failed: key=%s error=%s", key, str(exc))
            return None
        record = SessionRecord(**data)
        # Update last_activity and write back
        record.last_activity = _now_iso()
        body = json.dumps(asdict(record), default=str)
        self._client.put_object(
            Bucket=self._bucket, Key=key, Body=body,
            ContentType='application/json',
        )
        return record

    async def update(self, user_id: str, session_id: str, updates: dict) -> None:
        """Read-modify-write session.json."""
        record = await self.get(user_id, session_id)
        if record is None:
            self.logger.warning(
                "Update on missing S3 session: user=%s session=%s",
                user_id, session_id,
            )
            return
        for key_name, value in updates.items():
            if hasattr(record, key_name):
                setattr(record, key_name, value)
        record.last_activity = _now_iso()
        s3_key = self._session_key(user_id, session_id)
        body = json.dumps(asdict(record), default=str)
        self._client.put_object(
            Bucket=self._bucket, Key=s3_key, Body=body,
            ContentType='application/json',
        )

    async def delete(self, user_id: str, session_id: str) -> None:
        """Delete all objects under {prefix}/{user_id}/{session_id}/."""
        prefix = "%s/%s/%s/" % (self._prefix, user_id, session_id)
        response = self._client.list_objects_v2(
            Bucket=self._bucket, Prefix=prefix,
        )
        objects = response.get('Contents', [])
        if objects:
            self._client.delete_objects(
                Bucket=self._bucket,
                Delete={'Objects': [{'Key': obj['Key']} for obj in objects]},
            )
        self.logger.debug(
            "Deleted S3 session: bucket=%s prefix=%s objects=%d",
            self._bucket, prefix, len(objects),
        )

    async def list_sessions(
        self, user_id: str, limit: int = 20
    ) -> List[SessionRecord]:
        """List sessions by scanning {prefix}/{user_id}/ for session.json files."""
        prefix = "%s/%s/" % (self._prefix, user_id)
        response = self._client.list_objects_v2(
            Bucket=self._bucket, Prefix=prefix, Delimiter='/',
        )
        records: List[SessionRecord] = []
        for common_prefix in response.get('CommonPrefixes', []):
            # Each common prefix is {prefix}/{user_id}/{session_id}/
            session_prefix = common_prefix['Prefix']
            session_key = session_prefix + 'session.json'
            try:
                obj = self._client.get_object(Bucket=self._bucket, Key=session_key)
                data = json.loads(obj['Body'].read().decode('utf-8'))
                records.append(SessionRecord(**data))
            except Exception as exc:
                self.logger.warning(
                    "Failed to read session: key=%s error=%s", session_key, str(exc)
                )
        records.sort(key=lambda s: s.created_at, reverse=True)
        return records[:limit]


def create_session_store(store_type: str) -> SessionStoreBase:
    """Factory function to create the appropriate session store backend.

    Args:
        store_type: One of 'memory', 'dynamodb', 's3'.

    Returns:
        Configured SessionStoreBase implementation.
    """
    if store_type == 'dynamodb':
        return DynamoDBSessionStore(
            table_name=os.environ['BA_SESSION_STORE_TABLE'],
        )
    elif store_type == 's3':
        return S3SessionStore(
            bucket=os.environ['BA_SESSION_STORE_BUCKET'],
            prefix=os.environ.get('BA_SESSION_STORE_PREFIX', 'browser-sessions'),
        )
    return InMemorySessionStore()
