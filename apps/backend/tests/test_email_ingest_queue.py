from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import app.routes.pubsub as pubsub_module
import app.services.supabase.email_ingest_queue_service as queue_service_module
import app.tasks.email_ingest_worker as worker_module
from app.routes.pubsub import handle_gmail_push
from app.services.supabase.email_ingest_queue_service import (
    email_ingest_queue_service,
)


class _QueueTable:
    def __init__(self, datasets: dict):
        self.datasets = datasets
        self._selected = None
        self._updates = None
        self._table = None
        self._user_id = None
        self._message_ids = None
        self._queue_id = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, field: str, value):
        if field == "user_id":
            self._user_id = value
        elif field == "queue_id":
            self._queue_id = value
        return self

    def in_(self, field: str, values):
        if field == "external_email_id":
            self._message_ids = list(values)
        return self

    def insert(self, payload):
        self.datasets["inserted"].append(payload)
        return self

    def update(self, payload):
        self._updates = payload
        return self

    def limit(self, *_args, **_kwargs):
        return self

    async def execute(self):
        if self._updates is not None and self._queue_id:
            self.datasets["updated"].append((self._queue_id, self._updates))
            return SimpleNamespace(data=[self._updates])
        if self._message_ids is not None:
            rows = [
                row
                for row in self.datasets["existing"]
                if row["external_email_id"] in self._message_ids
                and row["user_id"] == self._user_id
            ]
            return SimpleNamespace(data=rows)
        return SimpleNamespace(data=[])


class _UserPreferencesTable:
    def __init__(self, row: dict):
        self.row = row
        self._updates = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def update(self, payload):
        self._updates = payload
        return self

    async def execute(self):
        if self._updates is not None:
            return SimpleNamespace(data=[self._updates])
        return SimpleNamespace(data=[self.row])


class _SupabaseClient:
    def __init__(self, queue_datasets=None, user_row=None):
        self.queue_datasets = queue_datasets
        self.user_row = user_row or {}

    def table(self, name: str):
        if name == "email_ingest_queue":
            return _QueueTable(self.queue_datasets)
        if name == "user_preferences":
            return _UserPreferencesTable(self.user_row)
        raise AssertionError(f"Unexpected table {name}")


@pytest.mark.asyncio
async def test_enqueue_refs_inserts_and_requeues_failed_rows(monkeypatch):
    now = datetime.now(timezone.utc)
    datasets = {
        "existing": [
            {
                "queue_id": "q-failed",
                "user_id": "user-1",
                "external_email_id": "msg-failed",
                "status": "failed",
                "next_retry_at": (now - timedelta(minutes=1)).isoformat(),
            },
            {
                "queue_id": "q-done",
                "user_id": "user-1",
                "external_email_id": "msg-done",
                "status": "done",
                "next_retry_at": None,
            },
        ],
        "inserted": [],
        "updated": [],
    }
    monkeypatch.setattr(
        pubsub_module.supabase_service,
        "get_client",
        AsyncMock(return_value=_SupabaseClient(queue_datasets=datasets)),
    )
    monkeypatch.setattr(
        queue_service_module.supabase_service,
        "get_client",
        AsyncMock(return_value=_SupabaseClient(queue_datasets=datasets)),
    )

    result = await email_ingest_queue_service.enqueue_refs(
        user_id="user-1",
        refs=[
            {"messageId": "msg-new", "threadId": "thread-1", "historyId": "1"},
            {"messageId": "msg-failed", "threadId": "thread-2", "historyId": "2"},
            {"messageId": "msg-done", "threadId": "thread-3", "historyId": "3"},
        ],
    )

    assert result == {"inserted": 1, "requeued": 1, "skipped": 1}
    assert datasets["inserted"][0]["external_email_id"] == "msg-new"
    assert datasets["updated"][0][0] == "q-failed"
    assert datasets["updated"][0][1]["status"] == "pending"


@pytest.mark.asyncio
async def test_handle_gmail_push_enqueues_refs_without_parsing(monkeypatch):
    user_row = {
        "user_id": "user-1",
        "gmail_label_id": "label-1",
        "gmail_last_history_id": "10",
        "gmail_refresh_cipher_b64": "cipher",
        "gmail_refresh_nonce_b64": "nonce",
    }
    fake_supabase = _SupabaseClient(user_row=user_row)
    monkeypatch.setattr(
        pubsub_module.supabase_service, "get_client", AsyncMock(return_value=fake_supabase)
    )
    monkeypatch.setattr(pubsub_module, "decrypt_refresh_token", lambda *_args: "refresh")
    monkeypatch.setattr(pubsub_module.gmail_service, "build_gmail_client", lambda *_args: object())
    monkeypatch.setattr(
        pubsub_module.gmail_history_service,
        "process_history",
        lambda **_kwargs: ([{"messageId": "msg-1", "threadId": "t-1", "historyId": "11"}], "11"),
    )
    enqueue_refs = AsyncMock(return_value={"inserted": 1, "requeued": 0, "skipped": 0})
    monkeypatch.setattr(pubsub_module.email_ingest_queue_service, "enqueue_refs", enqueue_refs)

    await handle_gmail_push("user@example.com", "11")

    enqueue_refs.assert_awaited_once()


@pytest.mark.asyncio
async def test_worker_marks_retryable_failure(monkeypatch):
    item = {
        "queue_id": "q-1",
        "user_id": "user-1",
        "external_email_id": "msg-1",
        "thread_id": "t-1",
        "history_id": "12",
        "attempt_count": 2,
    }
    monkeypatch.setattr(
        worker_module,
        "_resolve_user_state_by_user_id",
        AsyncMock(
            return_value={
                "gmail_refresh_cipher_b64": "cipher",
                "gmail_refresh_nonce_b64": "nonce",
            }
        ),
    )
    monkeypatch.setattr(worker_module, "decrypt_refresh_token", lambda *_args: "refresh")
    monkeypatch.setattr(
        worker_module.gmail_service, "build_gmail_client", lambda *_args: object()
    )
    monkeypatch.setattr(
        worker_module, "parse_and_persist", AsyncMock(side_effect=Exception("429 quota exceeded"))
    )
    mark_failed = AsyncMock()
    monkeypatch.setattr(
        worker_module.email_ingest_queue_service, "mark_failed", mark_failed
    )

    await worker_module._process_queue_item("worker-1", item)

    mark_failed.assert_awaited_once()
    assert mark_failed.await_args.kwargs["retryable"] is True
