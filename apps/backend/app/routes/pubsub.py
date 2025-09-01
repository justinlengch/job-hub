import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Request, Response

from app.services.crypto import decrypt_refresh_token
from app.services.google.gmail_history_service import gmail_history_service
from app.services.google.gmail_service import gmail_service
from app.services.google.pubsub_service import pubsub_service
from app.services.supabase.email_parsing_service import parse_and_persist
from app.services.supabase.supabase_client import supabase_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["pubsub"])


async def _resolve_user_by_email(
    supabase, email_address: str
) -> Optional[Dict[str, Any]]:
    """
    Deterministically resolve a user row by exact match on user_preferences.gmail_email.
    Returns a dict with fields needed by the pipeline, or None if not found.
    """
    resp = (
        await supabase.table("user_preferences")
        .select(
            "user_id,gmail_label_id,gmail_last_history_id,gmail_watch_expiration,gmail_refresh_cipher_b64,gmail_refresh_nonce_b64"
        )
        .eq("gmail_email", email_address)
        .limit(1)
        .execute()
    )

    if not resp.data:
        return None

    row = resp.data[0]
    return {
        "user_id": row.get("user_id"),
        "gmail_label_id": row.get("gmail_label_id"),
        "gmail_last_history_id": row.get("gmail_last_history_id"),
        "gmail_watch_expiration": row.get("gmail_watch_expiration"),
        "gmail_refresh_cipher_b64": row.get("gmail_refresh_cipher_b64"),
        "gmail_refresh_nonce_b64": row.get("gmail_refresh_nonce_b64"),
    }


async def handle_gmail_push(email_address: str, pushed_history_id: str) -> None:
    """
    End-to-end dispatcher for a Gmail push notification.
    - Resolve user
    - Ensure Gmail client
    - Process history diff
    - Parse & persist each referenced message
    - Update last_history_id
    """
    try:
        supabase = await supabase_service.get_client()
        user_state = await _resolve_user_by_email(supabase, email_address)
        if not user_state:
            logger.warning(
                f"gmail_push user_not_found email={email_address} history_id={pushed_history_id}"
            )
            return

        user_id = user_state["user_id"]
        label_id = user_state.get("gmail_label_id")
        last_history_id = user_state.get("gmail_last_history_id")

        if not user_id or not label_id:
            logger.warning(
                f"gmail_push missing_state email={email_address} user={user_id} label_id={label_id}"
            )
            return

        cipher_b64 = user_state.get("gmail_refresh_cipher_b64")
        nonce_b64 = user_state.get("gmail_refresh_nonce_b64")
        if not cipher_b64 or not nonce_b64:
            logger.warning(
                f"gmail_push missing_encrypted_refresh user={user_id} email={email_address}"
            )
            return

        try:
            refresh_token = decrypt_refresh_token(nonce_b64, cipher_b64)
        except Exception as e:
            logger.error(
                f"gmail_push decrypt_failed user={user_id} email={email_address} err={e}"
            )
            return

        creds = {
            "access_token": None,
            "refresh_token": refresh_token,
        }

        if not gmail_service.create_gmail_client(creds):
            logger.error(
                f"gmail_push gmail_client_init_failed user={user_id} email={email_address}"
            )
            return

        since = last_history_id or pushed_history_id
        refs, latest_history_id = gmail_history_service.process_history(
            user_id=user_id,
            gmail_client=gmail_service.service,
            since_history_id=since,
            label_id=label_id,
        )

        if not refs:
            logger.info(
                f"gmail_push no_new_refs user={user_id} email={email_address} since={since}"
            )
        else:
            logger.info(
                f"gmail_push refs_found count={len(refs)} user={user_id} email={email_address}"
            )

        for ref in refs:
            try:
                await parse_and_persist(ref, user_id, gmail_service.service)
            except Exception as e:
                logger.exception(
                    f"gmail_push parse_and_persist_failed user={user_id} msg={ref.get('messageId')} err={e}"
                )

        # Persist latest_history_id (best-effort)
        try:
            await (
                supabase.table("user_preferences")
                .update(
                    {"gmail_last_history_id": latest_history_id, "updated_at": "now()"}
                )
                .eq("user_id", user_id)
                .execute()
            )
        except Exception as e:
            logger.warning(
                f"gmail_push persist_last_history_failed user={user_id} err={e}"
            )

    except Exception as e:
        logger.exception(f"gmail_push unhandled_error email={email_address} err={e}")


@router.post("/gmail/push")
async def gmail_pubsub_push(
    request: Request, background_tasks: BackgroundTasks
) -> Response:
    """
    Google Pub/Sub push endpoint for Gmail watch notifications.
    Verifies OIDC token, decodes envelope, schedules background processing,
    and returns 204 quickly.
    """
    delivery_attempt = request.headers.get("X-Goog-Delivery-Attempt")
    auth_header = request.headers.get("Authorization")

    try:
        # Verify OIDC token
        claims = pubsub_service.verify_token(auth_header)
        body = await request.json()
        decoded = pubsub_service.decode_envelope(body)

        logger.info(
            "gmail_push received "
            f"email={decoded['email_address']} history_id={decoded['history_id']} "
            f"pubsub_msg={decoded.get('message_id')} publish_time={decoded.get('publish_time')} "
            f"attempt={delivery_attempt} iss={claims.get('iss')}"
        )

        # Fire background processing
        background_tasks.add_task(
            handle_gmail_push, decoded["email_address"], decoded["history_id"]
        )

        # Always 204 on success so Pub/Sub acks
        return Response(status_code=204)

    except Exception as e:
        # Log and return 500 so Pub/Sub will retry (limited attempts)
        logger.exception(f"gmail_push error err={e}")
        return Response(status_code=500)
