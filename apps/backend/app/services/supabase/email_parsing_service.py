from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.models.llm.llm_email import EmailIntent, LLMEmailInput, LLMEmailOutput
from app.services.ai.llm_service import extract_job_info
from app.services.base_service import BaseService, ServiceOperationError
from app.services.supabase.job_application_service import job_application_service
from app.services.supabase.supabase_client import supabase_service


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
    ) -> Dict[str, Any]:
        """
        Main email processing workflow WITHOUT storing full email contents.
        - Deduplicate and persist a minimal reference in `email_refs`
        - Link to job_applications/application_events based on intent
        """
        try:
            supabase = await supabase_service.get_client()

            # Idempotency: check existing minimal reference
            existing_ref = (
                await supabase.table("email_refs")
                .select("email_id")
                .eq("user_id", user_id)
                .eq("external_email_id", raw_email_id)
                .limit(1)
                .execute()
            )

            if existing_ref.data:
                self._log_operation("email_ref already exists", f"ID: {raw_email_id}")
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

            ref_insert = (
                await supabase.table("email_refs").insert(ref_payload).execute()
            )
            if not ref_insert.data:
                raise ServiceOperationError("Failed to insert email reference")

            email_id = ref_insert.data[0]["email_id"]

            # For non-job emails, skip creating application/events, keep the ref only
            if parsed.intent == EmailIntent.GENERAL:
                self._log_operation(
                    "non job-related email skipped",
                    f"ID: {raw_email_id} - not job related",
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

    def _collect_text(part) -> str:
        if not part:
            return ""
        text = ""
        body = part.get("body", {})
        data = body.get("data")
        if data:
            import base64

            try:
                decoded = base64.urlsafe_b64decode(data).decode(
                    "utf-8", errors="ignore"
                )
                # Use only plain text parts preferentially; fallback accumulates all
                if "plain" in part.get("mimeType", ""):
                    text += decoded
                else:
                    text += ("\n" + decoded) if text else decoded
            except Exception:
                pass
        for sub in part.get("parts", []) or []:
            sub_text = _collect_text(sub)
            if sub_text:
                text += ("\n" + sub_text) if text else sub_text
        return text

    body_text = _collect_text(payload).strip()

    email_input = LLMEmailInput(
        subject=subject,
        body_text=body_text or "(empty)",
        body_html=None,
    )
    parsed = await extract_job_info(email_input)

    return await email_parsing_service.process_email(
        parsed=parsed,
        raw_email_id=ref["messageId"],
        user_id=user_id,
        sender=sender,
        subject=subject,
        body_text=body_text,
        body_html=None,
        received_at=received_at_dt,
        thread_id=ref.get("threadId"),
        history_id=ref.get("historyId"),
    )
