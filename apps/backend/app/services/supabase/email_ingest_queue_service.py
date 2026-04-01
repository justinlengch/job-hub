import socket
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.services.base_service import BaseService, ServiceOperationError
from app.services.supabase.supabase_client import supabase_service


class EmailIngestQueueService(BaseService):
    def _initialize(self) -> None:
        self._log_operation("Email ingest queue service initialized")

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    async def enqueue_refs(
        self, *, user_id: str, refs: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        if not refs:
            return {"inserted": 0, "requeued": 0, "skipped": 0}

        supabase = await supabase_service.get_client()
        message_ids = [ref["messageId"] for ref in refs if ref.get("messageId")]
        existing_resp = (
            await supabase.table("email_ingest_queue")
            .select("*")
            .eq("user_id", user_id)
            .in_("external_email_id", message_ids)
            .execute()
        )
        existing_map = {
            row["external_email_id"]: row for row in (existing_resp.data or [])
        }

        inserted = 0
        requeued = 0
        skipped = 0
        now_iso = self._utc_now().isoformat()

        for ref in refs:
            message_id = ref.get("messageId")
            if not message_id:
                continue

            current = existing_map.get(message_id)
            payload = {
                "user_id": user_id,
                "external_email_id": message_id,
                "thread_id": ref.get("threadId"),
                "history_id": str(ref.get("historyId")) if ref.get("historyId") else None,
                "received_at": now_iso,
            }
            if not current:
                await (
                    supabase.table("email_ingest_queue")
                    .insert(
                        {
                            **payload,
                            "status": "pending",
                            "attempt_count": 0,
                            "next_retry_at": now_iso,
                        }
                    )
                    .execute()
                )
                inserted += 1
                continue

            status = current.get("status")
            updates: Dict[str, Any] = {
                "thread_id": ref.get("threadId") or current.get("thread_id"),
                "history_id": str(ref.get("historyId")) if ref.get("historyId") else current.get("history_id"),
                "received_at": current.get("received_at") or now_iso,
            }

            if status == "failed":
                retry_at = current.get("next_retry_at")
                retry_dt = None
                if retry_at:
                    try:
                        retry_dt = datetime.fromisoformat(str(retry_at).replace("Z", "+00:00"))
                    except Exception:
                        retry_dt = None
                if retry_dt is None or retry_dt <= self._utc_now():
                    updates.update(
                        {
                            "status": "pending",
                            "next_retry_at": now_iso,
                            "locked_at": None,
                            "lock_owner": None,
                            "last_error": None,
                        }
                    )
                    requeued += 1
                else:
                    skipped += 1
            elif status in {"pending", "processing", "done"}:
                skipped += 1
            else:
                updates.update({"status": "pending", "next_retry_at": now_iso})
                requeued += 1

            await (
                supabase.table("email_ingest_queue")
                .update(updates)
                .eq("queue_id", current["queue_id"])
                .eq("user_id", user_id)
                .execute()
            )

        return {"inserted": inserted, "requeued": requeued, "skipped": skipped}

    async def claim_batch(
        self, *, worker_id: str, limit: int, lease_seconds: int
    ) -> List[Dict[str, Any]]:
        supabase = await supabase_service.get_client()
        response = await supabase.rpc(
            "claim_email_ingest_queue_batch",
            {
                "p_worker_id": worker_id,
                "p_limit": limit,
                "p_lease_seconds": lease_seconds,
            },
        ).execute()
        return response.data or []

    async def mark_done(
        self,
        *,
        queue_id: str,
        worker_id: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> None:
        supabase = await supabase_service.get_client()
        updates: Dict[str, Any] = {
            "status": "done",
            "locked_at": None,
            "lock_owner": None,
            "next_retry_at": None,
            "last_error": None,
        }
        if result is not None:
            updates["payload_snapshot"] = result
        await (
            supabase.table("email_ingest_queue")
            .update(updates)
            .eq("queue_id", queue_id)
            .eq("lock_owner", worker_id)
            .execute()
        )

    async def mark_failed(
        self,
        *,
        queue_id: str,
        worker_id: str,
        error: str,
        attempt_count: int,
        retryable: bool,
        max_attempts: int,
    ) -> None:
        supabase = await supabase_service.get_client()
        updates: Dict[str, Any] = {
            "status": "failed",
            "locked_at": None,
            "lock_owner": None,
            "last_error": error[:2000],
        }
        if retryable and attempt_count < max_attempts:
            backoff_seconds = min(300, 2 ** max(attempt_count - 1, 0))
            updates["next_retry_at"] = (
                self._utc_now() + timedelta(seconds=backoff_seconds)
            ).isoformat()
        else:
            updates["next_retry_at"] = None
        await (
            supabase.table("email_ingest_queue")
            .update(updates)
            .eq("queue_id", queue_id)
            .eq("lock_owner", worker_id)
            .execute()
        )

    @staticmethod
    def make_worker_id(prefix: str = "email-ingest-worker") -> str:
        return f"{prefix}:{socket.gethostname()}:{datetime.now(timezone.utc).timestamp()}"


email_ingest_queue_service = EmailIngestQueueService()
