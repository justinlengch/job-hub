#!/usr/bin/env python3
"""
Heroku Scheduler Watch Refresh Script
=====================================

Purpose:
    This script is intended to be run periodically (e.g., every 10–15 minutes)
    by Heroku Scheduler (or any external scheduler) to refresh Gmail push
    watches for all users who have linked a Gmail account.

Why:
    - The in-app background loop only runs while the web dyno is awake.
    - Sleeping dynos allow Gmail watches (~7 day lifetime) to expire.
    - Expired watches stop Pub/Sub push deliveries, halting automation.

Behavior:
    1. Imports the shared batch procedure `perform_watch_refresh_batch`.
    2. Executes it inside an asyncio event loop.
    3. Logs structured summary statistics to stdout (captured by Heroku logs):
       checked_rows, candidates, refreshed, invalid_tokens, errors, duration_ms.
    4. Exits with code 0 (success) or 1 (fatal error).

Environment Variables Required:
    SUPABASE_URL
    SUPABASE_SERVICE_ROLE_KEY
    CRYPTO_KEY_B64
    GOOGLE_CLIENT_ID
    GOOGLE_CLIENT_SECRET
    PUBSUB_TOPIC_FQN

Optional:
    WATCH_REFRESH_THRESHOLD_SECONDS (default set in config.py)
    LOG_LEVEL (INFO by default)

Security Notes:
    - No plaintext refresh tokens are logged.
    - Decryption is limited to in-memory usage inside the batch logic.
    - This script itself does not expose an HTTP surface.

Idempotency:
    Safe to run multiple times per hour. Accounts far from expiration are skipped.

Usage (Heroku Scheduler Command):
    python job-hub/apps/backend/scripts/run_refresh.py
    or (with module path):
    python -m apps.backend.scripts.run_refresh

If you rearrange the repository layout, update the path accordingly.

Extensibility:
    - To mark revoked tokens, extend the batch logic to update a flag
      (e.g., gmail_refresh_invalid) when creation/auth fails with invalid_grant.
    - To add metrics shipping, hook into the summary dict before exit.

"""

import asyncio
import logging
import os
import sys
from typing import Any, Dict

# Adjust Python path if needed (Heroku one-off dyno sometimes starts at repo root)
# This ensures `app.*` imports resolve correctly if the working directory differs.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)

# Configure logging early
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    stream=sys.stdout,
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("run_refresh")

try:
    # Import after path adjustments
    from app.core.config import settings
    from app.tasks.gmail_watch_refresh import perform_watch_refresh_batch
except Exception as import_err:
    logger.error(f"Import failure: {import_err}")
    sys.exit(1)


async def _async_main() -> int:
    """
    Async entrypoint: performs the watch refresh batch and logs summary.
    Returns process exit code.
    """
    # Quick environment sanity checks
    missing = [
        var
        for var in [
            "SUPABASE_URL",
            "SUPABASE_SERVICE_ROLE_KEY",
            "CRYPTO_KEY_B64",
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
        ]
        if not os.getenv(var)
    ]
    if missing:
        logger.warning(f"Missing expected env vars: {','.join(missing)}")

    if not settings.PUBSUB_TOPIC_FQN:
        logger.info("PUBSUB_TOPIC_FQN not set; nothing to refresh. Exiting cleanly.")
        return 0

    logger.info("Starting Gmail watch refresh batch via run_refresh script")
    try:
        stats: Dict[str, Any] = await perform_watch_refresh_batch()
        # Log structured summary
        logger.info(
            "run_refresh complete " + " ".join(f"{k}={v}" for k, v in stats.items())
        )
        return 0
    except Exception as e:
        logger.error(f"Fatal error during refresh batch: {e}")
        return 1


def main() -> None:
    """
    Synchronous entrypoint for script execution.
    """
    exit_code = asyncio.run(_async_main())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
