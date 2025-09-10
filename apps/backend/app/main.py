import asyncio
import logging
import os
import sys

# Configure root logging to stdout for Heroku/uvicorn
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

root_logger = logging.getLogger()
if not root_logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
root_logger.setLevel(LOG_LEVEL)

# Align uvicorn loggers with root log level
logging.getLogger("uvicorn").setLevel(LOG_LEVEL)
logging.getLogger("uvicorn.error").setLevel(LOG_LEVEL)
logging.getLogger("uvicorn.access").setLevel(LOG_LEVEL)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routes.auth import router as auth_router
from app.routes.gmail import router as gmail_router
from app.routes.parse import router as parse_router
from app.routes.pubsub import router as pubsub_router
from app.services.crypto import decrypt_refresh_token
from app.services.google.gmail_service import gmail_service
from app.services.supabase.supabase_client import supabase_service

app = FastAPI(
    title="Job Hub API",
    description="API for parsing job application emails and managing job applications",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "https://job-hub-web.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "message": "Job Hub API is healthy"}


@app.get("/")
async def health_check():
    return {"status": "ok", "message": "Job Hub API is running"}


logger = logging.getLogger(__name__)
_refresh_task = None


async def _refresh_gmail_watches_once():
    if not settings.PUBSUB_TOPIC_FQN:
        return
    try:
        supabase = await supabase_service.get_client()
        resp = await (
            supabase.table("user_preferences")
            .select(
                "user_id,gmail_label_id,gmail_watch_expiration,gmail_refresh_cipher_b64,gmail_refresh_nonce_b64"
            )
            .execute()
        )
        rows = resp.data or []
        for row in rows:
            label_id = row.get("gmail_label_id")
            exp_raw = row.get("gmail_watch_expiration")
            # Normalize expiration to milliseconds since epoch (int)
            exp_ms = None
            if isinstance(exp_raw, (int, float)):
                exp_ms = int(exp_raw)
            elif isinstance(exp_raw, str) and exp_raw:
                try:
                    from datetime import datetime

                    dt = datetime.fromisoformat(exp_raw)
                    exp_ms = int(dt.timestamp() * 1000)
                except Exception:
                    exp_ms = None
            cipher_b64 = row.get("gmail_refresh_cipher_b64")
            nonce_b64 = row.get("gmail_refresh_nonce_b64")
            if not label_id or not cipher_b64 or not nonce_b64:
                continue
            try:
                refresh_token = decrypt_refresh_token(nonce_b64, cipher_b64)
                if not gmail_service.create_gmail_client(
                    {"refresh_token": refresh_token}
                ):
                    continue
                refreshed = gmail_service.refresh_watch_if_needed(
                    topic_fqn=settings.PUBSUB_TOPIC_FQN,
                    label_ids=[label_id],
                    watch_expiration_ms=exp_ms,
                    threshold_seconds=settings.WATCH_REFRESH_THRESHOLD_SECONDS,
                )
                if refreshed:
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
                        .eq("user_id", row.get("user_id"))
                        .execute()
                    )
            except Exception as e:
                logger.warning(f"watch_refresh user={row.get('user_id')} err={e}")
    except Exception as e:
        logger.error(f"watch_refresh batch err={e}")


async def _refresh_loop():
    interval = settings.WATCH_REFRESH_INTERVAL_SECONDS
    while True:
        await _refresh_gmail_watches_once()
        await asyncio.sleep(interval)


@app.on_event("startup")
async def _on_startup():
    global _refresh_task
    if settings.PUBSUB_TOPIC_FQN:
        _refresh_task = asyncio.create_task(_refresh_loop())


@app.on_event("shutdown")
async def _on_shutdown():
    global _refresh_task
    if _refresh_task:
        _refresh_task.cancel()
        try:
            await _refresh_task
        except Exception:
            pass


app.include_router(parse_router, prefix="/api")
app.include_router(gmail_router)
app.include_router(auth_router)
app.include_router(pubsub_router, prefix="/api")
