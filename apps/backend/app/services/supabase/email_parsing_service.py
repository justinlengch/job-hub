import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.models.llm.llm_email import EmailIntent, LLMEmailInput, LLMEmailOutput
from app.services.ai.llm_service import extract_job_info
from app.services.base_service import BaseService, ServiceOperationError
from app.services.supabase.job_application_service import job_application_service
from app.services.supabase.supabase_client import supabase_service

logger = logging.getLogger(__name__)


class EmailParsingService(BaseService):
    """
    Service for parsing emails into job applications or events.
    Handles deduplication, raw email insertion, and intent-based processing.
    """

    def _initialize(self) -> None:
        """Initialize email parsing service."""
        self._log_operation("Email parsing service initialized")

    async def process_email(
        self,
        parsed: LLMEmailOutput,
        raw_email_id: str,
        user_id: str,
        sender: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        received_at: Optional[datetime] = None,
        thread_id: Optional[str] = None,
        history_id: Optional[int] = None,
        max_retries: int = 3,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Main email processing workflow WITHOUT storing full email contents.
        - Deduplicate and persist a minimal reference in `email_refs`
        - Link to job_applications/application_events based on intent
        """
        try:
            supabase = await supabase_service.get_client()
            self.logger.info(
                f"email_process begin user={user_id} raw_email_id={raw_email_id} subject={subject!r} sender={sender!r} "
                f"body_text_len={(len(body_text) if body_text else 0)} body_html_len={(len(body_html) if body_html else 0)} "
                f"received_at={received_at} thread_id={thread_id} history_id={history_id} intent={parsed.intent.value}"
            )

            # Idempotency: check existing minimal reference
            existing_ref = (
                await supabase.table("email_refs")
                .select("email_id")
                .eq("user_id", user_id)
                .eq("external_email_id", raw_email_id)
                .limit(1)
                .execute()
            )

            if existing_ref.data and not force:
                self._log_operation("email_ref already exists", f"ID: {raw_email_id}")
                self.logger.info(
                    f"email_process duplicate user={user_id} raw_email_id={raw_email_id}"
                )
                return {
                    "status": "duplicate",
                    "email_id": existing_ref.data[0]["email_id"],
                }

            # Insert minimal reference (no bodies)
            ref_payload: Dict[str, Any] = {
                "user_id": user_id,
                "external_email_id": raw_email_id,
                "received_at": received_at.isoformat()
                if received_at
                else datetime.now().isoformat(),
            }
            if thread_id:
                ref_payload["thread_id"] = thread_id
            if history_id is not None:
                try:
                    ref_payload["history_id"] = int(history_id)
                except Exception:
                    ref_payload["history_id"] = history_id

            # Determine or create the email_ref record
            if existing_ref.data:
                email_id = existing_ref.data[0]["email_id"]
                if force:
                    self.logger.info(
                        f"email_process force_bypass_dedupe user={user_id} raw_email_id={raw_email_id} email_id={email_id}"
                    )
            else:
                ref_insert = (
                    await supabase.table("email_refs").insert(ref_payload).execute()
                )
                if not ref_insert.data:
                    raise ServiceOperationError("Failed to insert email reference")
                email_id = ref_insert.data[0]["email_id"]
                self.logger.info(
                    f"email_process ref_inserted user={user_id} raw_email_id={raw_email_id} email_id={email_id}"
                )

            # For non-job emails, skip creating application/events, keep the ref only
            if parsed.intent == EmailIntent.GENERAL:
                self._log_operation(
                    "non job-related email skipped",
                    f"ID: {raw_email_id} - not job related",
                )
                self.logger.info(
                    f"email_process skipped_non_job user={user_id} raw_email_id={raw_email_id} email_id={email_id} "
                    f"subject={subject!r} sender={sender!r}"
                )
                return {
                    "status": "skipped",
                    "intent": parsed.intent.value,
                    "reason": "not_job_related",
                    "email_id": email_id,
                }

            result = {
                "status": "processed",
                "email_id": email_id,
                "intent": parsed.intent.value,
            }

            if parsed.intent == EmailIntent.NEW_APPLICATION:
                application_data = await job_application_service.handle_new_application(
                    user_id, parsed, email_id
                )
                result["application"] = application_data

            elif parsed.intent == EmailIntent.APPLICATION_EVENT:
                event_data = await job_application_service.handle_application_event(
                    user_id, parsed, email_id
                )
                result["event"] = event_data
                if isinstance(event_data, dict) and event_data.get(
                    "created_new_application"
                ):
                    self.logger.info(
                        f"email_process created_new_application user={user_id} raw_email_id={raw_email_id} email_id={email_id} "
                        f"company={parsed.company} role={parsed.role}"
                    )

            self.logger.info(
                f"email_process done user={user_id} raw_email_id={raw_email_id} email_id={email_id} "
                f"status=processed intent={parsed.intent.value}"
            )
            return result

        except Exception as e:
            self._log_error("processing email intent", e)
            raise ServiceOperationError(f"Failed to process email: {str(e)}")


email_parsing_service = EmailParsingService()


async def parse_and_persist(ref: dict, user_id: str, gmail_client) -> dict:
    """
    Fetch Gmail message (full), run LLM parsing, persist minimal ref + link via existing workflow.
    ref keys: messageId, threadId, historyId
    """
    msg = (
        gmail_client.users()
        .messages()
        .get(userId="me", id=ref["messageId"], format="full")
        .execute()
    )
    payload = msg.get("payload", {})
    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
    subject = headers.get("subject", "")
    sender = headers.get("from", "")

    # Compute received_at from Gmail internalDate (ms since epoch)
    received_at_dt: Optional[datetime] = None
    try:
        internal_ms = msg.get("internalDate")
        if internal_ms:
            received_at_dt = datetime.fromtimestamp(
                int(internal_ms) / 1000, tz=timezone.utc
            )
    except Exception:
        received_at_dt = None

    # Helpers localized to avoid global deps
    import base64
    import re

    from bs4 import BeautifulSoup

    def _b64url_decode(data: str) -> str:
        if not data:
            return ""
        try:
            padding = "=" * (-len(data) % 4)
            return base64.urlsafe_b64decode((data + padding).encode("utf-8")).decode(
                "utf-8", errors="ignore"
            )
        except Exception:
            return ""

    def _walk_collect(part: dict, plain: list[str], html: list[str]) -> None:
        if not part:
            return
        mime = (part.get("mimeType") or "").lower()
        body = part.get("body") or {}
        data = body.get("data")
        if data:
            decoded = _b64url_decode(data)
            if "text/plain" in mime:
                plain.append(decoded)
            elif "text/html" in mime:
                html.append(decoded)
        for sub in part.get("parts") or []:
            _walk_collect(sub, plain, html)

    def _parse_html(html_text: str) -> tuple[str, str]:
        if not html_text:
            return "", ""
        soup = BeautifulSoup(html_text, "lxml")
        for tag in soup(["script", "style", "noscript", "template", "head"]):
            tag.decompose()
        # Use BeautifulSoup to get readable text and cleaned HTML
        text = soup.get_text(separator="\n", strip=True)
        text = re.sub(r"[ \t\x0b\f\r]+", " ", text)
        text = re.sub(r"\n\s*\n\s*", "\n\n", text).strip()
        cleaned_html = str(soup)
        return text, cleaned_html

    def _html_to_text(html_text: str) -> str:
        """Deprecated shim: uses BeautifulSoup via _parse_html"""
        if not html_text:
            return ""
        text, _ = _parse_html(html_text)
        return text

    # padding
    # padding
    # padding
    # padding
    # padding

    def _truncate(s: str, limit: int = 20000) -> str:
        if s and len(s) > limit:
            return s[:limit] + "\n...[truncated]..."
        return s

    # Collect plain-text and HTML parts recursively
    plain_parts: list[str] = []
    html_parts: list[str] = []
    _walk_collect(payload, plain_parts, html_parts)

    body_html_raw = "\n".join([p for p in html_parts if p]).strip()
    html_text_from_html, cleaned_html = (
        _parse_html(body_html_raw) if body_html_raw else ("", "")
    )
    body_html_clean = _truncate(cleaned_html) if cleaned_html else ""

    # Choose the larger between plain text and HTML-derived text
    candidate_plain = (
        "\n".join([p for p in plain_parts if p]).strip() if plain_parts else ""
    )
    candidate_html = html_text_from_html.strip() if html_text_from_html else ""
    if len(candidate_html) > len(candidate_plain):
        body_text = candidate_html
    elif candidate_plain:
        body_text = candidate_plain
    else:
        # Fallback: attempt to decode whatever is in the payload body
        decoded = _b64url_decode((payload.get("body") or {}).get("data", ""))
        body_text = decoded.strip()

    # Force-parse label support
    FORCE_LABEL_NAME = "JobHub Force Parse"

    def _get_or_create_label_id(gmail_client, label_name: str) -> Optional[str]:
        try:
            labels_result = gmail_client.users().labels().list(userId="me").execute()
            labels = labels_result.get("labels", []) or []
            for label in labels:
                if label.get("name") == label_name:
                    return label.get("id")
            # Create if not found
            result = (
                gmail_client.users()
                .labels()
                .create(
                    userId="me",
                    body={
                        "name": label_name,
                        "labelListVisibility": "labelShow",
                        "messageListVisibility": "show",
                    },
                )
                .execute()
            )
            return result.get("id")
        except Exception:
            return None

    def _remove_label(gmail_client, message_id: str, label_id: Optional[str]) -> None:
        if not label_id:
            return
        try:
            gmail_client.users().messages().modify(
                userId="me", id=message_id, body={"removeLabelIds": [label_id]}
            ).execute()
        except Exception:
            pass

    force_label_id = _get_or_create_label_id(gmail_client, FORCE_LABEL_NAME)
    force_parse = force_label_id in set(msg.get("labelIds") or [])

    # Early duplicate short-circuit (before LLM) unless force_parse is applied
    supabase = await supabase_service.get_client()
    existing_ref = (
        await supabase.table("email_refs")
        .select("email_id")
        .eq("user_id", user_id)
        .eq("external_email_id", ref["messageId"])
        .limit(1)
        .execute()
    )
    if existing_ref.data and not force_parse:
        logger.info(
            f"email_ingest duplicate_short_circuit user={user_id} msg_id={ref.get('messageId')} email_id={existing_ref.data[0]['email_id']}"
        )
        return {
            "status": "duplicate",
            "email_id": existing_ref.data[0]["email_id"],
        }

    email_input = LLMEmailInput(
        subject=subject,
        body_text=body_text or "(empty)",
        body_html=body_html_clean or None,
    )
    logger.info(
        f"email_ingest payload_summary user={user_id} msg_id={ref.get('messageId')} subject={subject!r} sender={sender!r} "
        f"body_text_len={(len(body_text) if body_text else 0)} body_html_len={(len(body_html_clean) if body_html_clean else 0)}"
    )
    parsed = await extract_job_info(email_input)

    logger.info(
        f"email_ingest llm_result user={user_id} msg_id={ref.get('messageId')} intent={parsed.intent.value} "
        f"company={parsed.company} role={parsed.role} status={parsed.status.value} "
        f"event_type={(parsed.event_type.value if parsed.event_type else None)}"
    )
    result = await email_parsing_service.process_email(
        parsed=parsed,
        raw_email_id=ref["messageId"],
        user_id=user_id,
        sender=sender,
        subject=subject,
        body_text=body_text,
        body_html=body_html_clean or None,
        received_at=received_at_dt,
        thread_id=ref.get("threadId"),
        history_id=ref.get("historyId"),
        force=force_parse,
    )
    # If force-parse label is present, remove it after processing (keep Job Applications label intact)
    if force_parse and force_label_id:
        try:
            _remove_label(gmail_client, ref["messageId"], force_label_id)
            logger.info(
                f"email_ingest force_label_removed user={user_id} msg_id={ref.get('messageId')} label_id={force_label_id}"
            )
        except Exception as e:
            logger.warning(
                f"email_ingest force_label_remove_failed user={user_id} msg_id={ref.get('messageId')} err={e}"
            )
    return result
