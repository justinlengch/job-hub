"""
Gmail Watch Refresh Batch Task
==============================

Purpose:
    Heroku Scheduler (or any external scheduler) can invoke this module as:
        python -m app.tasks.gmail_watch_refresh
    to proactively refresh Gmail push watches for all linked user accounts.

Why:
    The in-process background loop in `app.main` won't run if the web dyno
    sleeps. Without periodic refresh, Gmail watches expire (~7 days) and
    push notifications cease. This task keeps watches alive even when the
    main dyno is idle.

Behavior Summary:
    1. Fetch rows from `user_preferences` containing encrypted refresh tokens.
    2. Determine which users need a watch (missing expiration) or a refresh
       (expiration within threshold seconds).
    3. Decrypt refresh token (AES‑GCM) in-memory only.
    4. Build Gmail client with refresh token (library mints new access token).
    5. Call `refresh_watch_if_needed`; if refreshed, persist new expiration &
       history id.
    6. Track stats (checked, candidates, refreshed, invalid tokens, errors).
    7. Output a structured summary log line for observability.

Idempotency:
    Safe to run multiple times. Users far from expiration are skipped.

Security:
    - Never logs plaintext tokens.
    - Decrypted token remains in local scope.
    - Errors are sanitized (no secrets).

Environment:
    Requires:
        GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET (for gmail_service scopes)
        SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (direct DB access)
        CRYPTO_KEY_B64 (AES‑GCM master key)
        PUBSUB_TOPIC_FQN (Gmail Pub/Sub topic; if absent, task exits early)
    Optional:
        WATCH_REFRESH_THRESHOLD_SECONDS
        LOG_LEVEL

Extensibility:
    Add columns (e.g., gmail_refresh_invalid) if you later mark revoked tokens.

Usage (Heroku Scheduler Command Example):
    python -m app.tasks.gmail_watch_refresh

Exit Codes:
    0 on success (even if no accounts refreshed).
    1 on unexpected fatal error.

"""

import asyncio
import logging
import os
import sys
import time
from typing import Any, Dict, Optional

from app.core.config import settings
from app.services.crypto import decrypt_refresh_token
from app.services.google.gmail_service import gmail_service
from app.services.supabase.supabase_client import supabase_service

# Configure logging (stdout for Heroku Scheduler one-off dyno)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    stream=sys.stdout,
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("gmail_watch_refresh")


class RefreshStats:
    """Mutable container for batch statistics."""

    def __init__(self) -> None:
        self.checked_rows: int = 0
        self.candidates: int = 0
        self.refreshed: int = 0
        self.invalid_tokens: int = 0
        self.errors: int = 0
        self.start_ms: int = int(time.time() * 1000)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "checked_rows": self.checked_rows,
            "candidates": self.candidates,
            "refreshed": self.refreshed,
            "invalid_tokens": self.invalid_tokens,
            "errors": self.errors,
            "duration_ms": int(time.time() * 1000) - self.start_ms,
        }


def _parse_watch_expiration(raw: Any) -> Optional[int]:
    """
    Normalize stored expiration to milliseconds since epoch.
    Accepts:
        - int / float (already ms)
        - ISO8601 string
        - None / empty => None
    """
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    if isinstance(raw, str) and raw.strip():
        try:
            from datetime import datetime

            dt = datetime.fromisoformat(raw)
            return int(dt.timestamp() * 1000)
        except Exception:
            return None
    return None


async def _fetch_user_rows() -> list[Dict[str, Any]]:
    """
    Fetch rows containing Gmail linkage metadata.
    NOTE: Stored in user_preferences for now. If refactored into a dedicated
    table, adapt the select accordingly.
    """
    supabase = await supabase_service.get_client()
    resp = await (
        supabase.table("user_preferences")
        .select(
            "user_id,gmail_label_id,gmail_watch_expiration,"
            "gmail_refresh_cipher_b64,gmail_refresh_nonce_b64"
        )
        .execute()
    )
    return resp.data or []


def _needs_refresh(exp_ms: Optional[int], now_ms: int, threshold_ms: int) -> bool:
    """
    Determine whether a watch should be refreshed or created.
    Conditions:
        - No expiration recorded (exp_ms is None)
        - Already expired (exp_ms <= now_ms)
        - Will expire within threshold window
    """
    if exp_ms is None:
        return True
    remaining = exp_ms - now_ms
    return remaining <= threshold_ms


async def _persist_watch_refresh(user_id: str, refreshed: Dict[str, Any]) -> None:
    """
    Persist refreshed watch metadata (history_id + new expiration).
    Converts expiration ms -> ISO8601 UTC for storage consistency.
    """
    supabase = await supabase_service.get_client()
    exp_iso = None
    try:
        exp_ms = refreshed.get("expiration")
        if exp_ms:
            from datetime import datetime, timezone

            exp_iso = datetime.fromtimestamp(
                int(exp_ms) / 1000, tz=timezone.utc
            ).isoformat()
    except Exception:
        exp_iso = None

    await (
        supabase.table("user_preferences")
        .update(
            {
                "gmail_last_history_id": refreshed.get("history_id"),
                "gmail_watch_expiration": exp_iso,
                "updated_at": "now()",
            }
        )
        .eq("user_id", user_id)
        .execute()
    )


async def perform_watch_refresh_batch() -> Dict[str, Any]:
    """
    Core batch procedure. Returns stats dict.
    """
    stats = RefreshStats()

    if not settings.PUBSUB_TOPIC_FQN:
        logger.info("PUBSUB_TOPIC_FQN not configured; skipping refresh batch.")
        return stats.as_dict()

    try:
        rows = await _fetch_user_rows()
    except Exception as e:
        logger.error(f"Failed to fetch user_preferences rows: {e}")
        stats.errors += 1
        return stats.as_dict()

    now_ms = int(time.time() * 1000)
    threshold_ms = settings.WATCH_REFRESH_THRESHOLD_SECONDS * 1000

    for row in rows:
        stats.checked_rows += 1
        user_id = row.get("user_id")
        label_id = row.get("gmail_label_id")
        cipher_b64 = row.get("gmail_refresh_cipher_b64")
        nonce_b64 = row.get("gmail_refresh_nonce_b64")
        exp_ms = _parse_watch_expiration(row.get("gmail_watch_expiration"))

        # Skip rows missing required linkage data
        if not user_id or not label_id or not cipher_b64 or not nonce_b64:
            continue

        if not _needs_refresh(exp_ms, now_ms, threshold_ms):
            continue

        stats.candidates += 1

        try:
            # Decrypt refresh token; only keep in local scope.
            refresh_token = decrypt_refresh_token(nonce_b64, cipher_b64)

            # Build Gmail client with just refresh token (access token minted on demand)
            created = gmail_service.create_gmail_client(
                {"refresh_token": refresh_token}
            )
            if not created:
                # Could mark token invalid in DB (future enhancement)
                logger.warning(f"user={user_id} gmail_client_creation_failed")
                stats.invalid_tokens += 1
                continue

            refreshed = gmail_service.refresh_watch_if_needed(
                topic_fqn=settings.PUBSUB_TOPIC_FQN,
                label_ids=[label_id],
                watch_expiration_ms=exp_ms,
                threshold_seconds=settings.WATCH_REFRESH_THRESHOLD_SECONDS,
            )

            if refreshed:
                await _persist_watch_refresh(user_id, refreshed)
                stats.refreshed += 1
                logger.info(
                    f"user={user_id} watch_refreshed history_id={refreshed.get('history_id')} "
                    f"expiration_ms={refreshed.get('expiration')}"
                )
            else:
                # If no refresh performed and no prior expiration recorded, start_watch might have failed.
                if exp_ms is None:
                    logger.warning(f"user={user_id} watch_start_or_refresh_skipped")
        except Exception as e:
            stats.errors += 1
            logger.warning(f"user={user_id} watch_refresh_error err={e}")

    summary = stats.as_dict()
    logger.info(
        "gmail_watch_refresh_batch summary "
        + " ".join(f"{k}={v}" for k, v in summary.items())
    )
    return summary


async def _async_main() -> int:
    """
    Async entrypoint; executes batch and returns exit code.
    """
    try:
        await perform_watch_refresh_batch()
        return 0
    except Exception as e:
        logger.error(f"Fatal error during watch refresh batch: {e}")
        return 1


def main() -> None:
    """
    Synchronous entrypoint for `python -m app.tasks.gmail_watch_refresh`.
    """
    exit_code = asyncio.run(_async_main())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
