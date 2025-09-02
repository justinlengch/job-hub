import base64
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import RedirectResponse
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from pydantic import BaseModel

from ..core.auth import get_current_user
from ..core.config import settings
from ..services.crypto.crypto_service import crypto_service
from ..services.google.gmail_service import gmail_service
from ..services.supabase.supabase_client import supabase_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


class OAuthStartResponse(BaseModel):
    auth_url: str


class OAuthCallbackResponse(BaseModel):
    success: bool
    message: str
    gmail_email: Optional[str] = None


def _b64url_encode(data: dict) -> str:
    raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _b64url_decode(s: str) -> dict:
    return json.loads(base64.urlsafe_b64decode(s.encode("ascii")).decode("utf-8"))


def _build_google_auth_url(redirect_uri: str, state: Optional[str]) -> str:
    scopes = " ".join(s.strip() for s in settings.GMAIL_SCOPES.split(",") if s.strip())
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scopes,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    }
    if state:
        params["state"] = state
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)


@router.get("/google/start", response_model=OAuthStartResponse)
async def google_oauth_start(
    redirect_uri: str,
    success_url: Optional[str] = None,
    state: Optional[str] = None,
    current_user_id: str = Depends(get_current_user),
) -> OAuthStartResponse:
    """
    Start backend-only Google OAuth flow; returns the Google consent URL.
    """
    packed_state = state
    if success_url:
        packed_state = _b64url_encode({"success_url": success_url})
    return OAuthStartResponse(
        auth_url=_build_google_auth_url(redirect_uri, packed_state)
    )


@router.get("/google/callback", response_model=OAuthCallbackResponse)
async def google_oauth_callback(
    code: str,
    redirect_uri: str,
    background_tasks: BackgroundTasks,
    setup_gmail_automation: bool = True,
    label_name: Optional[str] = "Job Applications",
    state: Optional[str] = None,
    current_user_id: str = Depends(get_current_user),
) -> OAuthCallbackResponse:
    """
    Handle Google OAuth redirect: exchange code server-side, encrypt refresh token,
    and upsert into user_preferences for the current user.
    """
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            token_url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=400, detail="Failed to exchange code with Google"
        )

    payload = resp.json()
    refresh_token = payload.get("refresh_token")
    access_token = payload.get("access_token")
    id_token_jwt = payload.get("id_token")

    if not refresh_token:
        # Google may omit refresh_token if it was previously granted; ensure prompt=consent and access_type=offline in start URL
        raise HTTPException(
            status_code=400, detail="Missing refresh_token from Google response"
        )

    gmail_email: Optional[str] = None
    if id_token_jwt:
        try:
            claims = id_token.verify_oauth2_token(
                id_token_jwt, Request(), settings.GOOGLE_CLIENT_ID
            )
            gmail_email = claims.get("email")
        except Exception:
            # Non-fatal; continue without email if verification fails
            gmail_email = None

    # Encrypt and persist refresh token
    enc = crypto_service.encrypt(refresh_token)

    try:
        supabase = await supabase_service.get_client()
        await (
            supabase.table("user_preferences")
            .upsert(
                {
                    "user_id": current_user_id,
                    "gmail_email": gmail_email,
                    "gmail_refresh_cipher_b64": enc["gmail_refresh_cipher_b64"],
                    "gmail_refresh_nonce_b64": enc["gmail_refresh_nonce_b64"],
                    "gmail_key_version": int(enc["gmail_key_version"]),
                    "updated_at": "now()",
                }
            )
            .execute()
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to persist Gmail credentials: {str(e)}"
        )

    # Optionally kick off Gmail automation setup in the background (no token persisted in logs/DB)
    if setup_gmail_automation and access_token:
        background_tasks.add_task(
            setup_user_gmail_automation,
            current_user_id,
            access_token,
            refresh_token,
            label_name or "Job Applications",
        )

    success_url_val = None
    if state:
        try:
            decoded = _b64url_decode(state)
            success_url_val = decoded.get("success_url")
        except Exception:
            success_url_val = None

    if success_url_val:
        fe_base = settings.FRONTEND_BASE_URL or ""
        if fe_base and success_url_val.startswith(fe_base):
            return RedirectResponse(url=success_url_val, status_code=302)

    return OAuthCallbackResponse(
        success=True,
        message="Google account linked and refresh token stored (encrypted).",
        gmail_email=gmail_email,
    )


class AuthCallbackRequest(BaseModel):
    user_id: str
    access_token: str
    refresh_token: str
    provider: str = "google"


class UserSetupRequest(BaseModel):
    access_token: str
    refresh_token: str
    setup_gmail_automation: bool = True
    label_name: Optional[str] = "Job Applications"


async def setup_user_gmail_automation(
    user_id: str,
    access_token: str,
    refresh_token: str,
    label_name: str = "Job Applications",
) -> Dict[str, Any]:
    """
    Background task to set up Gmail automation for a user.
    This runs asynchronously after user authentication.
    """
    try:
        # Create Gmail client with user credentials
        credentials = {"access_token": access_token, "refresh_token": refresh_token}

        if not gmail_service.create_gmail_client(credentials):
            logger.error(f"Failed to create Gmail client for user {user_id}")
            return {"success": False, "error": "Failed to authenticate with Gmail"}

        # Fetch Gmail profile email (fallback if OAuth id_token lacked email)
        profile_email: Optional[str] = None
        try:
            prof = gmail_service.service.users().getProfile(userId="me").execute()
            profile_email = prof.get("emailAddress")
        except Exception:
            profile_email = None

        # Set up label and filter
        label_id = gmail_service.setup_job_application_labeling(label_name)

        # Optionally start Gmail watch and capture initial history/expiration
        watch_info = None
        try:
            if settings.PUBSUB_TOPIC_FQN:
                watch_info = gmail_service.start_watch(
                    settings.PUBSUB_TOPIC_FQN, [label_id]
                )
                logger.info(f"Started Gmail watch for user {user_id}: {watch_info}")
            else:
                logger.info(
                    "PUBSUB_TOPIC_FQN not configured; skipping Gmail watch start"
                )
        except Exception as e:
            logger.error(f"Failed to start Gmail watch for user {user_id}: {str(e)}")

        # Store the label_id in user preferences (and later, watch info)
        supabase = await supabase_service.get_client()

        # Check if gmail_email is already set; only fill it if missing
        existing_pref = await (
            supabase.table("user_preferences")
            .select("gmail_email")
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        update_payload: Dict[str, Any] = {
            "gmail_label_id": label_id,
            "gmail_automation_enabled": True,
            "updated_at": "now()",
        }
        if profile_email and (
            not existing_pref.data or not existing_pref.data.get("gmail_email")
        ):
            update_payload["gmail_email"] = profile_email

        # First update existing row to avoid overwriting encrypted fields with nulls
        update_resp = await (
            supabase.table("user_preferences")
            .update(update_payload)
            .eq("user_id", user_id)
            .execute()
        )
        # If no existing row, insert a new one
        if not update_resp.data:
            insert_payload = {
                "user_id": user_id,
                "gmail_label_id": label_id,
                "gmail_automation_enabled": True,
                "updated_at": "now()",
            }
            if profile_email:
                insert_payload["gmail_email"] = profile_email
            await supabase.table("user_preferences").insert(insert_payload).execute()

        # Persist watch info if available
        if watch_info:
            try:
                exp_iso = None
                try:
                    exp_ms = watch_info.get("expiration")
                    if exp_ms:
                        exp_iso = datetime.fromtimestamp(
                            int(exp_ms) / 1000, tz=timezone.utc
                        ).isoformat()
                except Exception:
                    exp_iso = None
                await (
                    supabase.table("user_preferences")
                    .update(
                        {
                            "gmail_last_history_id": watch_info.get("history_id"),
                            "gmail_watch_expiration": exp_iso,
                            "updated_at": "now()",
                        }
                    )
                    .eq("user_id", user_id)
                    .execute()
                )
            except Exception as e:
                logger.warning(
                    f"Failed to persist watch info for user {user_id}: {str(e)}"
                )

        logger.info(f"Successfully set up Gmail automation for user {user_id}")
        return {
            "success": True,
            "label_id": label_id,
            "message": f"Gmail automation set up successfully with label '{label_name}'",
        }

    except Exception as e:
        logger.error(f"Error setting up Gmail automation for user {user_id}: {str(e)}")
        return {"success": False, "error": str(e)}


@router.post("/setup-user")
async def setup_new_user(
    request: UserSetupRequest,
    background_tasks: BackgroundTasks,
    current_user_id: str = Depends(get_current_user),
):
    """
    Set up a new user after authentication.
    This endpoint should be called from the frontend after successful OAuth.
    """
    try:
        if request.setup_gmail_automation:
            # Add background task to set up Gmail automation
            background_tasks.add_task(
                setup_user_gmail_automation,
                current_user_id,
                request.access_token,
                request.refresh_token,
                request.label_name or "Job Applications",
            )

            return {
                "success": True,
                "message": "User setup initiated. Gmail automation will be configured shortly.",
                "user_id": current_user_id,
            }
        else:
            return {
                "success": True,
                "message": "User setup complete (Gmail automation skipped).",
                "user_id": current_user_id,
            }

    except Exception as e:
        logger.error(f"Error in user setup: {str(e)}")
        raise HTTPException(status_code=500, detail=f"User setup failed: {str(e)}")


@router.get("/user-preferences")
async def get_user_preferences(current_user_id: str = Depends(get_current_user)):
    """
    Get user preferences including Gmail automation status.
    """
    try:
        supabase = await supabase_service.get_client()
        result = (
            await supabase.table("user_preferences")
            .select("*")
            .eq("user_id", current_user_id)
            .execute()
        )

        if result.data:
            return {"success": True, "preferences": result.data[0]}
        else:
            return {
                "success": True,
                "preferences": {
                    "user_id": current_user_id,
                    "gmail_automation_enabled": False,
                    "gmail_label_id": None,
                },
            }

    except Exception as e:
        logger.error(f"Error fetching user preferences: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch user preferences")
