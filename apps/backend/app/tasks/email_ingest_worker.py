import asyncio
import logging
from typing import Any, Dict, Optional

from app.core.config import settings
from app.services.crypto import decrypt_refresh_token
from app.services.google.gmail_service import gmail_service
from app.services.supabase.email_ingest_queue_service import (
    email_ingest_queue_service,
)
from app.services.supabase.email_parsing_service import parse_and_persist
from app.services.supabase.supabase_client import supabase_service

logger = logging.getLogger("email_ingest_worker")


def _is_retryable_error(exc: Exception) -> bool:
    text = str(exc).lower()
    retry_tokens = (
        "429",
        "rate limit",
        "quota",
        "resource exhausted",
        "temporar",
        "timeout",
        "connection reset",
        "service unavailable",
        "internal error",
        "deadline exceeded",
        "backend error",
    )
    return any(token in text for token in retry_tokens)


async def _resolve_user_state_by_user_id(user_id: str) -> Optional[Dict[str, Any]]:
    supabase = await supabase_service.get_client()
    resp = (
        await supabase.table("user_preferences")
        .select("user_id,gmail_refresh_cipher_b64,gmail_refresh_nonce_b64")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


async def _process_queue_item(worker_id: str, item: Dict[str, Any]) -> None:
    queue_id = item["queue_id"]
    attempt_count = int(item.get("attempt_count") or 1)
    try:
        user_state = await _resolve_user_state_by_user_id(item["user_id"])
        if not user_state:
            raise ValueError("Missing user state for queued email")

        cipher_b64 = user_state.get("gmail_refresh_cipher_b64")
        nonce_b64 = user_state.get("gmail_refresh_nonce_b64")
        if not cipher_b64 or not nonce_b64:
            raise ValueError("Missing Gmail refresh token for queued email")

        refresh_token = decrypt_refresh_token(nonce_b64, cipher_b64)
        gmail_client = gmail_service.build_gmail_client(
            {"access_token": None, "refresh_token": refresh_token}
        )

        result = await parse_and_persist(
            {
                "messageId": item["external_email_id"],
                "threadId": item.get("thread_id"),
                "historyId": item.get("history_id"),
            },
            item["user_id"],
            gmail_client,
        )
        await email_ingest_queue_service.mark_done(
            queue_id=queue_id, worker_id=worker_id, result=result
        )
        logger.info(
            "email_ingest_worker processed "
            f"queue_id={queue_id} user={item['user_id']} message_id={item['external_email_id']} "
            f"status={result.get('status')}"
        )
    except Exception as exc:
        retryable = _is_retryable_error(exc)
        await email_ingest_queue_service.mark_failed(
            queue_id=queue_id,
            worker_id=worker_id,
            error=str(exc),
            attempt_count=attempt_count,
            retryable=retryable,
            max_attempts=settings.EMAIL_INGEST_MAX_ATTEMPTS,
        )
        logger.exception(
            "email_ingest_worker failed "
            f"queue_id={queue_id} user={item.get('user_id')} "
            f"message_id={item.get('external_email_id')} retryable={retryable}"
        )


async def run_worker() -> None:
    worker_id = email_ingest_queue_service.make_worker_id()
    concurrency = max(1, settings.EMAIL_INGEST_WORKER_CONCURRENCY)
    batch_size = max(concurrency, settings.EMAIL_INGEST_WORKER_BATCH_SIZE)
    lease_seconds = max(30, settings.EMAIL_INGEST_QUEUE_LEASE_SECONDS)
    poll_seconds = max(1, settings.EMAIL_INGEST_WORKER_POLL_SECONDS)

    logger.info(
        "email_ingest_worker starting "
        f"worker_id={worker_id} concurrency={concurrency} batch_size={batch_size}"
    )

    semaphore = asyncio.Semaphore(concurrency)

    async def _run_one(item: Dict[str, Any]) -> None:
        async with semaphore:
            await _process_queue_item(worker_id, item)

    while True:
        claimed = await email_ingest_queue_service.claim_batch(
            worker_id=worker_id, limit=batch_size, lease_seconds=lease_seconds
        )
        if not claimed:
            await asyncio.sleep(poll_seconds)
            continue
        await asyncio.gather(*[_run_one(item) for item in claimed])


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(run_worker())
        return 0
    except KeyboardInterrupt:
        logger.info("email_ingest_worker stopped")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
