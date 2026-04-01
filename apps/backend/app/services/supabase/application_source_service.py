import csv
import io
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from app.models.api.application_event import ApplicationEventType
from app.models.api.application_source import (
    ApplicationMergeStatus,
    ApplicationSourceType,
    SankeyLink,
    SankeyLinkKind,
    SankeyMeta,
    SankeyNode,
    SankeyNodeKind,
    SankeyResponse,
)
from app.models.api.job_application import (
    ApplicationDatePrecision,
    ApplicationOrigin,
    ApplicationStatus,
)
from app.models.llm.llm_email import EmailIntent, LLMEmailOutput
from app.services.base_service import BaseService, ServiceOperationError
from app.services.supabase.application_matcher_service import (
    AUTO_MERGE_THRESHOLD,
    REVIEW_THRESHOLD,
    CandidateMatch,
    application_matcher_service,
)
from app.services.supabase.supabase_client import supabase_service


SANKY_STAGE_ORDER = [
    "APPLIED",
    "GHOSTED",
    "REJECTED",
    "ASSESSMENT",
    "INTERVIEW",
    "FINAL_ROUND",
    "OFFERED",
    "ACCEPTED",
    "WITHDRAWN",
]

SANKY_STAGE_KIND = {
    "APPLIED": SankeyNodeKind.ROOT,
    "ASSESSMENT": SankeyNodeKind.PROGRESS,
    "INTERVIEW": SankeyNodeKind.PROGRESS,
    "FINAL_ROUND": SankeyNodeKind.PROGRESS,
    "OFFERED": SankeyNodeKind.PROGRESS,
    "ACCEPTED": SankeyNodeKind.TERMINAL,
    "REJECTED": SankeyNodeKind.TERMINAL,
    "WITHDRAWN": SankeyNodeKind.TERMINAL,
    "GHOSTED": SankeyNodeKind.GHOSTED,
}

SANKY_STAGE_COLUMN = {
    "APPLIED": 0,
    "GHOSTED": 1,
    "REJECTED": 2,
    "ASSESSMENT": 3,
    "INTERVIEW": 4,
    "FINAL_ROUND": 5,
    "OFFERED": 6,
    "ACCEPTED": 7,
    "WITHDRAWN": 7,
}

SANKY_STAGE_RANK = {
    "APPLIED": 0,
    "ASSESSMENT": 1,
    "INTERVIEW": 2,
    "FINAL_ROUND": 3,
    "OFFERED": 4,
    "ACCEPTED": 5,
    "REJECTED": 5,
    "WITHDRAWN": 5,
    "GHOSTED": 6,
}


class ApplicationSourceService(BaseService):
    CSV_HEADER_ALIASES = {
        "company": {"company", "company name", "employer"},
        "role": {"role", "title", "job title", "position"},
        "applied_at": {
            "applied at",
            "applied_on",
            "application date",
            "date applied",
            "submitted at",
            "submitted_on",
        },
        "status_text": {"status", "application status"},
        "job_url": {"job url", "job posting url", "posting url", "job link"},
        "location": {"location", "job location"},
        "source_url": {"source url", "application url", "easy apply url"},
        "external_source_id": {"external source id", "application id", "id"},
    }

    def _initialize(self) -> None:
        self._log_operation("Application source service initialized")

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        text = str(value).strip()
        if not text:
            return None
        candidates = [text]
        if text.endswith("Z"):
            candidates.append(text.replace("Z", "+00:00"))
        for candidate in candidates:
            try:
                parsed = datetime.fromisoformat(candidate)
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        for fmt in (
            "%m/%d/%y, %I:%M %p",
            "%m/%d/%Y, %I:%M %p",
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%Y/%m/%d",
            "%b %d, %Y",
            "%B %d, %Y",
        ):
            try:
                return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return None

    @staticmethod
    def _extract_relevant_linkedin_payload(
        row: Dict[str, Any],
        *,
        company: str,
        role: str,
        applied_at_raw: str,
        status_text: Optional[str],
        job_url: Optional[str],
        location: Optional[str],
        source_url: Optional[str],
        external_source_id: Optional[str],
    ) -> Dict[str, Any]:
        payload = {
            "company": company,
            "role": role,
            "applied_at": applied_at_raw,
        }
        if status_text:
            payload["status_text"] = status_text
        if job_url:
            payload["job_url"] = job_url
        if location:
            payload["location"] = location
        if source_url:
            payload["source_url"] = source_url
        if external_source_id:
            payload["external_source_id"] = external_source_id

        # Preserve recognized LinkedIn export columns that are still job-specific.
        lowered = {str(k).lower().strip(): v for k, v in row.items()}
        extra_job_fields = {
            "application status": "status_text",
            "status": "status_text",
            "job location": "location",
            "location": "location",
            "easy apply url": "source_url",
            "application url": "source_url",
            "source url": "source_url",
            "application id": "external_source_id",
            "external source id": "external_source_id",
            "id": "external_source_id",
        }
        for raw_key, normalized_key in extra_job_fields.items():
            value = ApplicationSourceService._clean_str(lowered.get(raw_key))
            if value and normalized_key not in payload:
                payload[normalized_key] = value
        return payload

    @staticmethod
    def _clean_str(value: Any) -> Optional[str]:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    def _canonical_header_map(self, headers: Iterable[str]) -> Dict[str, str]:
        mapping: Dict[str, str] = {}
        normalized = {header.lower().strip(): header for header in headers if header}
        for canonical, aliases in self.CSV_HEADER_ALIASES.items():
            for alias in aliases:
                if alias in normalized:
                    mapping[canonical] = normalized[alias]
                    break
        return mapping

    def _normalize_linkedin_row(self, row: Dict[str, Any], row_number: int) -> Dict[str, Any]:
        lowered = {str(k).lower().strip(): v for k, v in row.items()}
        header_map = self._canonical_header_map(lowered.keys())

        def resolve(field: str) -> Optional[str]:
            header = header_map.get(field)
            return self._clean_str(lowered.get(header.lower().strip())) if header else None

        company = resolve("company")
        role = resolve("role")
        applied_at_raw = resolve("applied_at")
        if not company or not role or not applied_at_raw:
            missing = [
                field
                for field, value in (
                    ("company", company),
                    ("role", role),
                    ("applied_at", applied_at_raw),
                )
                if not value
            ]
            raise ValueError(f"missing required fields: {', '.join(missing)}")

        applied_at = self._parse_datetime(applied_at_raw)
        if not applied_at:
            raise ValueError("invalid applied_at value")

        status_text = resolve("status_text")
        job_url = resolve("job_url")
        location = resolve("location")
        source_url = resolve("source_url")
        external_source_id = resolve("external_source_id")

        return {
            "row_number": row_number,
            "company": company,
            "role": role,
            "applied_at": applied_at,
            "status_text": status_text,
            "job_url": job_url,
            "location": location,
            "source_url": source_url,
            "external_source_id": external_source_id,
            "payload_json": self._extract_relevant_linkedin_payload(
                row,
                company=company,
                role=role,
                applied_at_raw=applied_at_raw,
                status_text=status_text,
                job_url=job_url,
                location=location,
                source_url=source_url,
                external_source_id=external_source_id,
            ),
        }

    def parse_upload_rows(
        self, filename: str, payload: bytes
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        suffix = (filename or "").lower()
        decoded = payload.decode("utf-8-sig")
        parsed_rows: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []

        if suffix.endswith(".json"):
            raw = json.loads(decoded)
            rows = raw if isinstance(raw, list) else raw.get("rows", [])
        else:
            reader = csv.DictReader(io.StringIO(decoded))
            rows = list(reader)

        for index, row in enumerate(rows, start=1):
            try:
                parsed_rows.append(self._normalize_linkedin_row(row, index))
            except Exception as exc:
                errors.append({"row_number": index, "message": str(exc)})

        return parsed_rows, errors

    async def _create_source_record(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        supabase = await supabase_service.get_client()
        try:
            response = await supabase.table("application_sources").insert(payload).execute()
            if not response.data:
                raise ServiceOperationError("Failed to create application source record")
            return response.data[0]
        except Exception:
            external_source_id = payload.get("external_source_id")
            source_type = payload.get("source_type")
            user_id = payload.get("user_id")
            if external_source_id and source_type and user_id:
                existing = await self._fetch_source_by_external_source(
                    user_id=user_id,
                    source_type=source_type,
                    external_source_id=external_source_id,
                )
                if existing:
                    return existing
            raise

    async def _update_source_record(
        self, source_id: str, user_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        supabase = await supabase_service.get_client()
        response = (
            await supabase.table("application_sources")
            .update(updates)
            .eq("source_id", source_id)
            .eq("user_id", user_id)
            .execute()
        )
        if not response.data:
            raise ServiceOperationError("Failed to update application source record")
        return response.data[0]

    async def _fetch_source_by_external_source(
        self, *, user_id: str, source_type: str, external_source_id: str
    ) -> Optional[Dict[str, Any]]:
        supabase = await supabase_service.get_client()
        response = (
            await supabase.table("application_sources")
            .select("*")
            .eq("user_id", user_id)
            .eq("source_type", source_type)
            .eq("external_source_id", external_source_id)
            .order("created_at", desc=False)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    async def _fetch_source(self, source_id: str, user_id: str) -> Dict[str, Any]:
        supabase = await supabase_service.get_client()
        response = (
            await supabase.table("application_sources")
            .select("*")
            .eq("source_id", source_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if not response.data:
            raise ServiceOperationError("Source record not found")
        return response.data[0]

    async def _fetch_application(self, application_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        supabase = await supabase_service.get_client()
        response = (
            await supabase.table("job_applications")
            .select("*")
            .eq("application_id", application_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    async def _fetch_event_by_source(
        self, source_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        supabase = await supabase_service.get_client()
        response = (
            await supabase.table("application_events")
            .select("*")
            .eq("source_id", source_id)
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    async def _create_application(
        self,
        *,
        user_id: str,
        company: str,
        role: str,
        status: ApplicationStatus,
        application_origin: ApplicationOrigin,
        canonical_source: str,
        applied_date: Optional[datetime],
        applied_date_precision: ApplicationDatePrecision,
        application_inferred: bool,
        inferred_reason: Optional[str],
        match_confidence: Optional[float],
        needs_review: bool,
        location: Optional[str] = None,
        salary_range: Optional[str] = None,
        notes: Optional[str] = None,
        job_posting_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        supabase = await supabase_service.get_client()
        payload = {
            "user_id": user_id,
            "company": company,
            "role": role,
            "status": status.value if isinstance(status, ApplicationStatus) else status,
            "job_posting_url": job_posting_url,
            "location": location,
            "salary_range": salary_range,
            "notes": notes,
            "applied_date": applied_date.isoformat() if applied_date else None,
            "canonical_source": canonical_source,
            "application_origin": application_origin.value
            if isinstance(application_origin, ApplicationOrigin)
            else application_origin,
            "application_inferred": application_inferred,
            "inferred_reason": inferred_reason,
            "applied_date_precision": applied_date_precision.value
            if isinstance(applied_date_precision, ApplicationDatePrecision)
            else applied_date_precision,
            "match_confidence": match_confidence,
            "needs_review": needs_review,
            "last_updated_at": self._utc_now().isoformat(),
        }
        response = await supabase.table("job_applications").insert(payload).execute()
        if not response.data:
            raise ServiceOperationError("Failed to create job application")
        return response.data[0]

    async def _update_application(
        self, application_id: str, user_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        supabase = await supabase_service.get_client()
        updates["last_updated_at"] = self._utc_now().isoformat()
        response = (
            await supabase.table("job_applications")
            .update(updates)
            .eq("application_id", application_id)
            .eq("user_id", user_id)
            .execute()
        )
        if not response.data:
            raise ServiceOperationError("Failed to update job application")
        return response.data[0]

    async def _update_event(
        self, event_id: str, user_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        supabase = await supabase_service.get_client()
        response = (
            await supabase.table("application_events")
            .update(updates)
            .eq("event_id", event_id)
            .eq("user_id", user_id)
            .execute()
        )
        if not response.data:
            raise ServiceOperationError("Failed to update application event")
        return response.data[0]

    async def _create_event(
        self,
        *,
        application_id: str,
        user_id: str,
        event_type: ApplicationEventType,
        event_date: Optional[datetime],
        description: Optional[str],
        source_type: Optional[str],
        source_id: Optional[str],
        email_id: Optional[str] = None,
        is_inferred: bool = False,
        confidence_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        supabase = await supabase_service.get_client()
        payload = {
            "application_id": application_id,
            "user_id": user_id,
            "event_type": event_type.value if isinstance(event_type, ApplicationEventType) else event_type,
            "event_date": (event_date or self._utc_now()).isoformat(),
            "description": description,
            "email_id": email_id,
            "source_type": source_type,
            "source_id": source_id,
            "is_inferred": is_inferred,
            "confidence_score": confidence_score,
        }
        try:
            response = await supabase.table("application_events").insert(payload).execute()
            if not response.data:
                raise ServiceOperationError("Failed to create application event")
            return response.data[0]
            # Unique source_id violations should return the existing derived event.
        except Exception:
            if source_id:
                existing = await self._fetch_event_by_source(source_id, user_id)
                if existing:
                    return existing
            raise

    async def _find_existing_final_round(
        self, application_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        supabase = await supabase_service.get_client()
        response = (
            await supabase.table("application_events")
            .select("*")
            .eq("application_id", application_id)
            .eq("user_id", user_id)
            .eq("event_type", ApplicationEventType.FINAL_ROUND.value)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    async def _build_source_payload_from_email(
        self,
        *,
        user_id: str,
        parsed: LLMEmailOutput,
        email_id: str,
        sender: str,
        subject: str,
        received_at: Optional[datetime],
        merge_status: ApplicationMergeStatus,
        merge_confidence: Optional[float],
        candidate_application_id: Optional[str],
        review_reason: Optional[str],
        application_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        sender_domain = application_matcher_service.sender_domain(sender)
        return {
            "user_id": user_id,
            "source_type": ApplicationSourceType.EMAIL.value,
            "application_id": application_id,
            "candidate_application_id": candidate_application_id,
            "external_source_id": email_id,
            "company_raw": parsed.company,
            "role_raw": parsed.role,
            "applied_at": None,
            "observed_at": (received_at or parsed.event_date or self._utc_now()).isoformat(),
            "sender_domain": sender_domain,
            "payload_json": {
                "intent": parsed.intent.value,
                "status": parsed.status.value,
                "event_type": parsed.event_type.value if parsed.event_type else None,
                "event_date": parsed.event_date.isoformat() if parsed.event_date else None,
                "event_description": parsed.event_description,
                "location": parsed.location,
                "salary_range": parsed.salary_range,
                "notes": parsed.notes,
                "email_id": email_id,
                "subject": subject,
            },
            "merge_confidence": merge_confidence,
            "merge_status": merge_status.value,
            "review_reason": review_reason,
        }

    async def process_email_source(
        self,
        *,
        user_id: str,
        parsed: LLMEmailOutput,
        email_id: str,
        sender: str,
        subject: str,
        received_at: Optional[datetime],
    ) -> Dict[str, Any]:
        observed_at = parsed.event_date or received_at or self._utc_now()
        existing_source = await self._fetch_source_by_external_source(
            user_id=user_id,
            source_type=ApplicationSourceType.EMAIL.value,
            external_source_id=email_id,
        )

        if existing_source:
            payload = await self._build_source_payload_from_email(
                user_id=user_id,
                parsed=parsed,
                email_id=email_id,
                sender=sender,
                subject=subject,
                received_at=received_at,
                merge_status=ApplicationMergeStatus(
                    existing_source.get("merge_status")
                    or ApplicationMergeStatus.UNMATCHED.value
                ),
                merge_confidence=existing_source.get("merge_confidence"),
                candidate_application_id=existing_source.get("candidate_application_id"),
                review_reason=existing_source.get("review_reason"),
                application_id=existing_source.get("application_id"),
            )

            source = await self._update_source_record(
                existing_source["source_id"],
                user_id,
                payload,
            )

            application_id = existing_source.get("application_id")
            if application_id:
                inferred = parsed.intent == EmailIntent.APPLICATION_EVENT and (
                    parsed.status != ApplicationStatus.APPLIED
                    or (
                        parsed.event_type
                        and parsed.event_type
                        != ApplicationEventType.APPLICATION_SUBMITTED
                    )
                )
                application = await self._update_application(
                    application_id,
                    user_id,
                    {
                        "company": parsed.company,
                        "role": parsed.role,
                        "status": parsed.status.value,
                        "location": parsed.location,
                        "salary_range": parsed.salary_range,
                        "notes": parsed.notes,
                        "application_origin": ApplicationOrigin.EMAIL.value,
                        "match_confidence": existing_source.get("merge_confidence"),
                        "application_inferred": inferred,
                        "inferred_reason": "FIRST_SIGNAL_WAS_LATER_STAGE"
                        if inferred
                        else None,
                        "last_email_received_at": observed_at.isoformat(),
                    },
                )
                event_type = parsed.event_type
                if parsed.intent == EmailIntent.NEW_APPLICATION and not event_type:
                    event_type = ApplicationEventType.APPLICATION_SUBMITTED
                elif not event_type:
                    event_type = application_matcher_service.event_type_from_status(
                        parsed.status
                    )

                existing_event = await self._fetch_event_by_source(
                    source["source_id"], user_id
                )
                event_updates = {
                    "application_id": application_id,
                    "event_type": event_type.value
                    if isinstance(event_type, ApplicationEventType)
                    else event_type,
                    "event_date": observed_at.isoformat(),
                    "description": parsed.event_description or subject,
                    "email_id": email_id,
                    "source_type": ApplicationSourceType.EMAIL.value,
                    "source_id": source["source_id"],
                    "confidence_score": existing_source.get("merge_confidence"),
                }
                if existing_event:
                    event = await self._update_event(
                        existing_event["event_id"], user_id, event_updates
                    )
                else:
                    event = await self._create_event(
                        application_id=application_id,
                        user_id=user_id,
                        event_type=event_type,
                        event_date=observed_at,
                        description=parsed.event_description or subject,
                        source_type=ApplicationSourceType.EMAIL.value,
                        source_id=source["source_id"],
                        email_id=email_id,
                        confidence_score=existing_source.get("merge_confidence"),
                    )
                return {"application": application, "event": event, "source": source}

            return {"source": source, "pending_review": True}

        best_match = await application_matcher_service.find_best_application_match(
            user_id=user_id,
            company=parsed.company,
            role=parsed.role,
            location=parsed.location,
            observed_at=observed_at,
            sender=sender,
        )

        if best_match and best_match.score >= AUTO_MERGE_THRESHOLD:
            source = await self._create_source_record(
                await self._build_source_payload_from_email(
                    user_id=user_id,
                    parsed=parsed,
                    email_id=email_id,
                    sender=sender,
                    subject=subject,
                    received_at=received_at,
                    merge_status=ApplicationMergeStatus.AUTO_MERGED,
                    merge_confidence=best_match.score,
                    candidate_application_id=best_match.application_id,
                    review_reason=best_match.reason,
                    application_id=best_match.application_id,
                )
            )
            application = await self._update_application(
                best_match.application_id,
                user_id,
                {
                    "status": parsed.status.value,
                    "location": parsed.location,
                    "salary_range": parsed.salary_range,
                    "notes": parsed.notes,
                    "canonical_source": "MERGED",
                    "match_confidence": best_match.score,
                    "needs_review": False,
                    "last_email_received_at": observed_at.isoformat(),
                },
            )
            event = await self._create_event(
                application_id=best_match.application_id,
                user_id=user_id,
                event_type=parsed.event_type
                or application_matcher_service.event_type_from_status(parsed.status),
                event_date=observed_at,
                description=parsed.event_description or subject,
                source_type=ApplicationSourceType.EMAIL.value,
                source_id=source["source_id"],
                email_id=email_id,
                confidence_score=best_match.score,
            )
            return {"application": application, "event": event}

        if best_match and best_match.score >= REVIEW_THRESHOLD:
            source = await self._create_source_record(
                await self._build_source_payload_from_email(
                    user_id=user_id,
                    parsed=parsed,
                    email_id=email_id,
                    sender=sender,
                    subject=subject,
                    received_at=received_at,
                    merge_status=ApplicationMergeStatus.PENDING_REVIEW,
                    merge_confidence=best_match.score,
                    candidate_application_id=best_match.application_id,
                    review_reason=best_match.reason,
                )
            )
            return {"source": source, "pending_review": True}

        existing_application = await application_matcher_service.find_existing_application_exact(
            user_id=user_id,
            company=parsed.company,
            role=parsed.role,
            location=parsed.location,
        )
        if existing_application and existing_application.get("application_id"):
            source = await self._create_source_record(
                await self._build_source_payload_from_email(
                    user_id=user_id,
                    parsed=parsed,
                    email_id=email_id,
                    sender=sender,
                    subject=subject,
                    received_at=received_at,
                    merge_status=ApplicationMergeStatus.AUTO_MERGED,
                    merge_confidence=1.0,
                    candidate_application_id=existing_application["application_id"],
                    review_reason="exact company and role match",
                    application_id=existing_application["application_id"],
                )
            )
            application = await self._update_application(
                existing_application["application_id"],
                user_id,
                {
                    "status": parsed.status.value,
                    "location": parsed.location,
                    "salary_range": parsed.salary_range,
                    "notes": parsed.notes,
                    "canonical_source": "MERGED",
                    "application_origin": ApplicationOrigin.EMAIL.value,
                    "match_confidence": 1.0,
                    "needs_review": False,
                    "last_email_received_at": observed_at.isoformat(),
                },
            )
            event_type = parsed.event_type
            if parsed.intent == EmailIntent.NEW_APPLICATION and not event_type:
                event_type = ApplicationEventType.APPLICATION_SUBMITTED
            elif not event_type:
                event_type = application_matcher_service.event_type_from_status(
                    parsed.status
                )
            event = await self._create_event(
                application_id=existing_application["application_id"],
                user_id=user_id,
                event_type=event_type,
                event_date=observed_at,
                description=parsed.event_description or subject,
                source_type=ApplicationSourceType.EMAIL.value,
                source_id=source["source_id"],
                email_id=email_id,
                confidence_score=1.0,
            )
            return {"application": application, "event": event, "source": source}

        inferred = parsed.intent == EmailIntent.APPLICATION_EVENT and (
            parsed.status != ApplicationStatus.APPLIED
            or (parsed.event_type and parsed.event_type != ApplicationEventType.APPLICATION_SUBMITTED)
        )
        application = await self._create_application(
            user_id=user_id,
            company=parsed.company,
            role=parsed.role,
            status=parsed.status or ApplicationStatus.APPLIED,
            application_origin=ApplicationOrigin.EMAIL,
            canonical_source="EMAIL",
            applied_date=observed_at,
            applied_date_precision=ApplicationDatePrecision.INFERRED
            if inferred
            else ApplicationDatePrecision.EXACT,
            application_inferred=inferred,
            inferred_reason="FIRST_SIGNAL_WAS_LATER_STAGE" if inferred else None,
            match_confidence=best_match.score if best_match else None,
            needs_review=False,
            location=parsed.location,
            salary_range=parsed.salary_range,
            notes=parsed.notes,
        )
        source = await self._create_source_record(
            await self._build_source_payload_from_email(
                user_id=user_id,
                parsed=parsed,
                email_id=email_id,
                sender=sender,
                subject=subject,
                received_at=received_at,
                merge_status=ApplicationMergeStatus.UNMATCHED,
                merge_confidence=best_match.score if best_match else None,
                candidate_application_id=best_match.application_id if best_match else None,
                review_reason=best_match.reason if best_match else None,
                application_id=application["application_id"],
            )
        )
        event_type = parsed.event_type
        if parsed.intent == EmailIntent.NEW_APPLICATION and not event_type:
            event_type = ApplicationEventType.APPLICATION_SUBMITTED
        elif not event_type:
            event_type = application_matcher_service.event_type_from_status(parsed.status)

        event = await self._create_event(
            application_id=application["application_id"],
            user_id=user_id,
            event_type=event_type,
            event_date=observed_at,
            description=parsed.event_description or subject,
            source_type=ApplicationSourceType.EMAIL.value,
            source_id=source["source_id"],
            email_id=email_id,
            confidence_score=best_match.score if best_match else None,
        )
        return {"application": application, "event": event}

    async def _create_linkedin_application(
        self,
        *,
        user_id: str,
        row: Dict[str, Any],
        match: Optional[CandidateMatch],
        needs_review: bool,
    ) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        status = application_matcher_service.infer_status_from_text(row.get("status_text"))
        application = await self._create_application(
            user_id=user_id,
            company=row["company"],
            role=row["role"],
            status=status,
            application_origin=ApplicationOrigin.LINKEDIN_EASY_APPLY,
            canonical_source="LINKEDIN",
            applied_date=row["applied_at"],
            applied_date_precision=ApplicationDatePrecision.EXACT,
            application_inferred=False,
            inferred_reason=None,
            match_confidence=match.score if match else None,
            needs_review=needs_review,
            location=row.get("location"),
            job_posting_url=row.get("job_url"),
            notes=row.get("status_text"),
        )
        source = await self._create_source_record(
            {
                "user_id": user_id,
                "source_type": ApplicationSourceType.LINKEDIN_EASY_APPLY.value,
                "application_id": application["application_id"],
                "candidate_application_id": match.application_id if match else None,
                "external_source_id": row.get("external_source_id"),
                "company_raw": row["company"],
                "role_raw": row["role"],
                "applied_at": row["applied_at"].isoformat(),
                "observed_at": row["applied_at"].isoformat(),
                "source_url": row.get("source_url") or row.get("job_url"),
                "payload_json": row.get("payload_json"),
                "merge_confidence": match.score if match else None,
                "merge_status": ApplicationMergeStatus.UNMATCHED.value,
                "review_reason": match.reason if match else None,
            }
        )
        event = await self._create_event(
            application_id=application["application_id"],
            user_id=user_id,
            event_type=ApplicationEventType.APPLICATION_SUBMITTED,
            event_date=row["applied_at"],
            description="Imported from LinkedIn Easy Apply history",
            source_type=ApplicationSourceType.LINKEDIN_EASY_APPLY.value,
            source_id=source["source_id"],
            confidence_score=match.score if match else None,
        )
        return application, source, event

    async def import_linkedin_rows(
        self, user_id: str, rows: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        outcomes: List[Dict[str, Any]] = []
        created_count = 0
        merged_count = 0
        review_count = 0
        failed_count = 0

        for row in rows:
            try:
                best_match = await application_matcher_service.find_best_application_match(
                    user_id=user_id,
                    company=row["company"],
                    role=row["role"],
                    location=row.get("location"),
                    observed_at=row["applied_at"],
                    source_url=row.get("source_url") or row.get("job_url"),
                )
                if best_match and best_match.score >= AUTO_MERGE_THRESHOLD:
                    source = await self._create_source_record(
                        {
                            "user_id": user_id,
                            "source_type": ApplicationSourceType.LINKEDIN_EASY_APPLY.value,
                            "application_id": best_match.application_id,
                            "candidate_application_id": best_match.application_id,
                            "external_source_id": row.get("external_source_id"),
                            "company_raw": row["company"],
                            "role_raw": row["role"],
                            "applied_at": row["applied_at"].isoformat(),
                            "observed_at": row["applied_at"].isoformat(),
                            "source_url": row.get("source_url") or row.get("job_url"),
                            "payload_json": row.get("payload_json"),
                            "merge_confidence": best_match.score,
                            "merge_status": ApplicationMergeStatus.AUTO_MERGED.value,
                            "review_reason": best_match.reason,
                        }
                    )
                    application = await self._update_application(
                        best_match.application_id,
                        user_id,
                        {
                            "canonical_source": "MERGED",
                            "application_origin": ApplicationOrigin.LINKEDIN_EASY_APPLY.value,
                            "job_posting_url": row.get("job_url"),
                            "location": row.get("location"),
                            "match_confidence": best_match.score,
                            "needs_review": False,
                            "applied_date": row["applied_at"].isoformat(),
                            "applied_date_precision": ApplicationDatePrecision.EXACT.value,
                        },
                    )
                    await self._create_event(
                        application_id=best_match.application_id,
                        user_id=user_id,
                        event_type=ApplicationEventType.APPLICATION_SUBMITTED,
                        event_date=row["applied_at"],
                        description="Imported from LinkedIn Easy Apply history",
                        source_type=ApplicationSourceType.LINKEDIN_EASY_APPLY.value,
                        source_id=source["source_id"],
                        confidence_score=best_match.score,
                    )
                    merged_count += 1
                    outcomes.append(
                        {
                            "row_number": row["row_number"],
                            "status": "merged",
                            "application_id": application["application_id"],
                            "source_id": source["source_id"],
                            "confidence": best_match.score,
                            "reason": best_match.reason,
                        }
                    )
                    continue

                if best_match and best_match.score >= REVIEW_THRESHOLD:
                    source = await self._create_source_record(
                        {
                            "user_id": user_id,
                            "source_type": ApplicationSourceType.LINKEDIN_EASY_APPLY.value,
                            "candidate_application_id": best_match.application_id,
                            "external_source_id": row.get("external_source_id"),
                            "company_raw": row["company"],
                            "role_raw": row["role"],
                            "applied_at": row["applied_at"].isoformat(),
                            "observed_at": row["applied_at"].isoformat(),
                            "source_url": row.get("source_url") or row.get("job_url"),
                            "payload_json": row.get("payload_json"),
                            "merge_confidence": best_match.score,
                            "merge_status": ApplicationMergeStatus.PENDING_REVIEW.value,
                            "review_reason": best_match.reason,
                        }
                    )
                    review_count += 1
                    outcomes.append(
                        {
                            "row_number": row["row_number"],
                            "status": "review",
                            "source_id": source["source_id"],
                            "confidence": best_match.score,
                            "reason": best_match.reason,
                        }
                    )
                    continue

                application, source, _ = await self._create_linkedin_application(
                    user_id=user_id,
                    row=row,
                    match=best_match,
                    needs_review=False,
                )
                created_count += 1
                outcomes.append(
                    {
                        "row_number": row["row_number"],
                        "status": "created",
                        "application_id": application["application_id"],
                        "source_id": source["source_id"],
                        "confidence": best_match.score if best_match else None,
                        "reason": best_match.reason if best_match else None,
                    }
                )
            except Exception as exc:
                failed_count += 1
                outcomes.append(
                    {
                        "row_number": row["row_number"],
                        "status": "failed",
                        "reason": str(exc),
                    }
                )

        return {
            "summary": {
                "processed_rows": len(rows),
                "created_applications": created_count,
                "merged_applications": merged_count,
                "review_items": review_count,
                "failed_rows": failed_count,
                "message": "LinkedIn import completed",
            },
            "errors": [
                {"row_number": row["row_number"], "message": row["reason"]}
                for row in outcomes
                if row["status"] == "failed"
            ],
            "outcomes": outcomes,
        }

    async def get_review_queue(self, user_id: str) -> Dict[str, Any]:
        supabase = await supabase_service.get_client()
        response = (
            await supabase.table("application_sources")
            .select("*")
            .eq("user_id", user_id)
            .eq("merge_status", ApplicationMergeStatus.PENDING_REVIEW.value)
            .order("created_at", desc=True)
            .execute()
        )
        items = response.data or []
        candidate_ids = [item.get("candidate_application_id") for item in items if item.get("candidate_application_id")]
        candidate_map: Dict[str, Dict[str, Any]] = {}
        if candidate_ids:
            candidate_resp = (
                await supabase.table("job_applications")
                .select("application_id,company,role")
                .in_("application_id", candidate_ids)
                .execute()
            )
            candidate_map = {
                row["application_id"]: row for row in (candidate_resp.data or [])
            }

        shaped = []
        for item in items:
            candidate = candidate_map.get(item.get("candidate_application_id"))
            payload = item.get("payload_json") or {}
            shaped.append(
                {
                    "source_id": item["source_id"],
                    "source_type": item["source_type"],
                    "company": item["company_raw"],
                    "role": item["role_raw"],
                    "sender_domain": item.get("sender_domain"),
                    "candidate_application_id": item.get("candidate_application_id"),
                    "candidate_company": candidate.get("company") if candidate else None,
                    "candidate_role": candidate.get("role") if candidate else None,
                    "confidence_score": item.get("merge_confidence") or 0,
                    "review_reason": item.get("review_reason") or "Manual review required",
                    "observed_at": item.get("observed_at"),
                    "applied_at": item.get("applied_at"),
                    "status_text": payload.get("status") or payload.get("status_text"),
                    "source_url": item.get("source_url"),
                }
            )
        return {"items": shaped, "pending_count": len(shaped)}

    async def _materialize_source_into_application(
        self, user_id: str, source: Dict[str, Any], application_id: Optional[str]
    ) -> Dict[str, Any]:
        payload = source.get("payload_json") or {}
        source_type = source.get("source_type")
        if source_type == ApplicationSourceType.EMAIL.value:
            target_application_id = application_id
            if not target_application_id:
                status = ApplicationStatus(payload.get("status", ApplicationStatus.APPLIED.value))
                observed_at = self._parse_datetime(
                    payload.get("event_date") or source.get("observed_at")
                ) or self._utc_now()
                inferred = status != ApplicationStatus.APPLIED
                app = await self._create_application(
                    user_id=user_id,
                    company=source["company_raw"],
                    role=source["role_raw"],
                    status=status,
                    application_origin=ApplicationOrigin.EMAIL,
                    canonical_source="EMAIL",
                    applied_date=observed_at,
                    applied_date_precision=ApplicationDatePrecision.INFERRED
                    if inferred
                    else ApplicationDatePrecision.EXACT,
                    application_inferred=inferred,
                    inferred_reason="FIRST_SIGNAL_WAS_LATER_STAGE" if inferred else None,
                    match_confidence=source.get("merge_confidence"),
                    needs_review=False,
                    location=payload.get("location"),
                    salary_range=payload.get("salary_range"),
                    notes=payload.get("notes"),
                )
                target_application_id = app["application_id"]
            else:
                status = ApplicationStatus(payload.get("status", ApplicationStatus.APPLIED.value))
                await self._update_application(
                    target_application_id,
                    user_id,
                    {
                        "status": status.value,
                        "canonical_source": "MERGED",
                        "match_confidence": source.get("merge_confidence"),
                        "needs_review": False,
                        "last_email_received_at": source.get("observed_at"),
                    },
                )

            event_type = payload.get("event_type")
            resolved_event_type = (
                ApplicationEventType(event_type)
                if event_type
                else application_matcher_service.event_type_from_status(
                    ApplicationStatus(payload.get("status", ApplicationStatus.APPLIED.value))
                )
            )
            event = await self._create_event(
                application_id=target_application_id,
                user_id=user_id,
                event_type=resolved_event_type,
                event_date=self._parse_datetime(
                    payload.get("event_date") or source.get("observed_at")
                ),
                description=payload.get("event_description") or payload.get("subject"),
                source_type=source_type,
                source_id=source["source_id"],
                email_id=payload.get("email_id"),
                confidence_score=source.get("merge_confidence"),
            )
            return {"application_id": target_application_id, "event": event}

        target_application_id = application_id
        if not target_application_id:
            status = application_matcher_service.infer_status_from_text(
                payload.get("status_text") or payload.get("status")
            )
            app = await self._create_application(
                user_id=user_id,
                company=source["company_raw"],
                role=source["role_raw"],
                status=status,
                application_origin=ApplicationOrigin.LINKEDIN_EASY_APPLY,
                canonical_source="LINKEDIN",
                applied_date=self._parse_datetime(source.get("applied_at")) or self._utc_now(),
                applied_date_precision=ApplicationDatePrecision.EXACT,
                application_inferred=False,
                inferred_reason=None,
                match_confidence=source.get("merge_confidence"),
                needs_review=False,
                location=payload.get("location"),
                job_posting_url=payload.get("job_url"),
                notes=payload.get("status_text"),
            )
            target_application_id = app["application_id"]
            await self._create_event(
                application_id=target_application_id,
                user_id=user_id,
                event_type=ApplicationEventType.APPLICATION_SUBMITTED,
                event_date=self._parse_datetime(source.get("applied_at")),
                description="Imported from LinkedIn Easy Apply history",
                source_type=source_type,
                source_id=source["source_id"],
                confidence_score=source.get("merge_confidence"),
            )
        else:
            await self._update_application(
                target_application_id,
                user_id,
                {
                    "canonical_source": "MERGED",
                    "application_origin": ApplicationOrigin.LINKEDIN_EASY_APPLY.value,
                    "match_confidence": source.get("merge_confidence"),
                    "needs_review": False,
                },
            )
            await self._create_event(
                application_id=target_application_id,
                user_id=user_id,
                event_type=ApplicationEventType.APPLICATION_SUBMITTED,
                event_date=self._parse_datetime(source.get("applied_at")),
                description="Imported from LinkedIn Easy Apply history",
                source_type=source_type,
                source_id=source["source_id"],
                confidence_score=source.get("merge_confidence"),
            )
        return {"application_id": target_application_id}

    async def confirm_review_queue_item(self, user_id: str, source_id: str) -> Dict[str, Any]:
        source = await self._fetch_source(source_id, user_id)
        target_application_id = source.get("candidate_application_id") or source.get("application_id")
        result = await self._materialize_source_into_application(
            user_id, source, target_application_id
        )
        updated_source = await self._update_source_record(
            source_id,
            user_id,
            {
                "application_id": result["application_id"],
                "merge_status": ApplicationMergeStatus.MANUALLY_CONFIRMED.value,
                "review_reason": None,
            },
        )
        return {"success": True, "source_id": source_id, "merge_status": updated_source["merge_status"]}

    async def separate_review_queue_item(self, user_id: str, source_id: str) -> Dict[str, Any]:
        source = await self._fetch_source(source_id, user_id)
        result = await self._materialize_source_into_application(user_id, source, None)
        updated_source = await self._update_source_record(
            source_id,
            user_id,
            {
                "application_id": result["application_id"],
                "merge_status": ApplicationMergeStatus.MANUALLY_SEPARATED.value,
                "candidate_application_id": None,
                "review_reason": None,
            },
        )
        return {"success": True, "source_id": source_id, "merge_status": updated_source["merge_status"]}

    async def toggle_final_round(
        self, user_id: str, application_id: str, enabled: bool
    ) -> Dict[str, Any]:
        existing = await self._find_existing_final_round(application_id, user_id)
        supabase = await supabase_service.get_client()
        if enabled:
            if existing:
                return {
                    "application_id": application_id,
                    "is_final_round": True,
                    "event_id": existing.get("event_id"),
                }
            created = await self._create_event(
                application_id=application_id,
                user_id=user_id,
                event_type=ApplicationEventType.FINAL_ROUND,
                event_date=self._utc_now(),
                description="Marked as final round",
                source_type="MANUAL",
                source_id=None,
            )
            await self._update_application(
                application_id,
                user_id,
                {"status": ApplicationStatus.INTERVIEW.value},
            )
            return {
                "application_id": application_id,
                "is_final_round": True,
                "event_id": created.get("event_id"),
            }

        if existing:
            await (
                supabase.table("application_events")
                .delete()
                .eq("event_id", existing["event_id"])
                .eq("user_id", user_id)
                .execute()
            )
        return {"application_id": application_id, "is_final_round": False, "event_id": None}

    @staticmethod
    def _stage_from_event(event_type: str) -> Optional[str]:
        mapping = {
            ApplicationEventType.APPLICATION_SUBMITTED.value: "APPLIED",
            ApplicationEventType.APPLICATION_RECEIVED.value: "APPLIED",
            ApplicationEventType.APPLICATION_VIEWED.value: "APPLIED",
            ApplicationEventType.APPLICATION_REVIEWED.value: "APPLIED",
            ApplicationEventType.ASSESSMENT_RECEIVED.value: "ASSESSMENT",
            ApplicationEventType.ASSESSMENT_COMPLETED.value: "ASSESSMENT",
            ApplicationEventType.INTERVIEW_SCHEDULED.value: "INTERVIEW",
            ApplicationEventType.INTERVIEW_COMPLETED.value: "INTERVIEW",
            ApplicationEventType.REFERENCE_REQUESTED.value: "INTERVIEW",
            ApplicationEventType.FINAL_ROUND.value: "FINAL_ROUND",
            ApplicationEventType.OFFER_RECEIVED.value: "OFFERED",
            ApplicationEventType.OFFER_ACCEPTED.value: "ACCEPTED",
            ApplicationEventType.OFFER_DECLINED.value: "WITHDRAWN",
            ApplicationEventType.APPLICATION_REJECTED.value: "REJECTED",
            ApplicationEventType.APPLICATION_WITHDRAWN.value: "WITHDRAWN",
        }
        return mapping.get(event_type)

    @staticmethod
    def _stage_from_status(status: str) -> str:
        mapping = {
            ApplicationStatus.APPLIED.value: "APPLIED",
            ApplicationStatus.ASSESSMENT.value: "ASSESSMENT",
            ApplicationStatus.INTERVIEW.value: "INTERVIEW",
            ApplicationStatus.OFFERED.value: "OFFERED",
            ApplicationStatus.ACCEPTED.value: "ACCEPTED",
            ApplicationStatus.REJECTED.value: "REJECTED",
            ApplicationStatus.WITHDRAWN.value: "WITHDRAWN",
        }
        return mapping.get(status, "APPLIED")

    @staticmethod
    def _is_terminal_stage(stage: str) -> bool:
        return stage in {"ACCEPTED", "REJECTED", "WITHDRAWN"}

    @staticmethod
    def _stage_rank(stage: str) -> int:
        return SANKY_STAGE_RANK.get(stage, 0)

    @staticmethod
    def _stage_kind(stage: str) -> SankeyNodeKind:
        return SANKY_STAGE_KIND.get(stage, SankeyNodeKind.PROGRESS)

    @staticmethod
    def _stage_column(stage: str) -> int:
        return SANKY_STAGE_COLUMN.get(stage, 5)

    def _is_ghosted_application(
        self,
        application: Dict[str, Any],
        events: List[Dict[str, Any]],
    ) -> bool:
        if application.get("application_inferred"):
            return False

        if self._stage_from_status(application.get("status") or "APPLIED") != "APPLIED":
            return False

        has_downstream_signal = any(
            self._stage_from_event(event.get("event_type"))
            in {"ASSESSMENT", "INTERVIEW", "FINAL_ROUND", "OFFERED", "ACCEPTED", "REJECTED", "WITHDRAWN"}
            for event in events
        )
        return not has_downstream_signal

    def _build_application_path(
        self,
        application: Dict[str, Any],
        events: List[Dict[str, Any]],
    ) -> List[str]:
        path: List[str] = ["APPLIED"]
        ordered_events = sorted(
            events,
            key=lambda event: self._parse_datetime(event.get("event_date")) or self._utc_now(),
        )
        last_rank = self._stage_rank("APPLIED")
        last_stage = "APPLIED"

        for event in ordered_events:
            stage = self._stage_from_event(event.get("event_type"))
            if not stage or stage == "APPLIED":
                continue
            stage_rank = self._stage_rank(stage)
            if stage_rank < last_rank:
                continue
            if stage == last_stage:
                continue
            path.append(stage)
            last_stage = stage
            last_rank = stage_rank
            if self._is_terminal_stage(stage):
                break

        if len(path) == 1:
            if self._is_ghosted_application(application, ordered_events):
                path.append("GHOSTED")
            else:
                status_stage = self._stage_from_status(application.get("status") or "APPLIED")
                if status_stage != "APPLIED":
                    path.append(status_stage)
        else:
            if not self._is_terminal_stage(path[-1]):
                status_stage = self._stage_from_status(application.get("status") or "APPLIED")
                if self._is_terminal_stage(status_stage) and status_stage not in path:
                    path.append(status_stage)

        deduped: List[str] = []
        for stage in path:
            if not deduped or deduped[-1] != stage:
                deduped.append(stage)
        return deduped

    def build_sankey_graph(
        self,
        applications: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
        *,
        pending_review_count: int = 0,
    ) -> SankeyResponse:
        grouped_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for event in events:
            application_id = event.get("application_id")
            if application_id:
                grouped_events[application_id].append(event)

        node_counts: Dict[str, int] = defaultdict(int)
        link_counts: Dict[tuple[str, str], int] = defaultdict(int)
        link_app_ids: Dict[tuple[str, str], List[str]] = defaultdict(list)
        ghosted_count = 0
        inferred_count = 0
        total_applications = 0

        for application in applications:
            application_id = application.get("application_id")
            if not application_id:
                continue

            total_applications += 1
            if application.get("application_inferred"):
                inferred_count += 1

            app_events = grouped_events.get(application_id, [])
            path = self._build_application_path(application, app_events)
            if "GHOSTED" in path:
                ghosted_count += 1

            for stage in path:
                node_counts[stage] += 1
            for source_stage, target_stage in zip(path, path[1:]):
                key = (source_stage, target_stage)
                link_counts[key] += 1
                link_app_ids[key].append(application_id)

        nodes = [
            SankeyNode(
                id=stage,
                label=stage.replace("_", " ").title(),
                count=node_counts.get(stage, 0),
                kind=self._stage_kind(stage),
                column=self._stage_column(stage),
            )
            for stage in SANKY_STAGE_ORDER
            if node_counts.get(stage, 0) > 0
        ]
        nodes.sort(key=lambda node: (node.column, node.kind.value, node.id))

        links = [
            SankeyLink(
                source=source_stage,
                target=target_stage,
                value=count,
                kind=SankeyLinkKind(self._stage_kind(target_stage).value),
                application_ids=link_app_ids[(source_stage, target_stage)],
            )
            for (source_stage, target_stage), count in sorted(link_counts.items())
            if count > 0
        ]

        return SankeyResponse(
            nodes=nodes,
            links=links,
            meta=SankeyMeta(
                total_applications=total_applications,
                ghosted_count=ghosted_count,
                inferred_count=inferred_count,
                pending_review_count=pending_review_count,
            ),
        )

    async def generate_sankey_data(
        self,
        user_id: str,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        source_type: Optional[str] = None,
        company: Optional[str] = None,
    ) -> SankeyResponse:
        supabase = await supabase_service.get_client()
        query = supabase.table("job_applications").select("*").eq("user_id", user_id)
        if company:
            query = query.ilike("company", f"%{company}%")
        if source_type:
            query = query.eq("canonical_source", source_type)
        app_resp = await query.execute()
        applications = app_resp.data or []

        application_ids = [row["application_id"] for row in applications if row.get("application_id")]
        events: List[Dict[str, Any]] = []
        if application_ids:
            event_query = (
                supabase.table("application_events")
                .select("*")
                .eq("user_id", user_id)
                .in_("application_id", application_ids)
            )
            event_resp = await event_query.execute()
            events = event_resp.data or []

        start_dt = self._parse_datetime(start_date)
        end_dt = self._parse_datetime(end_date)
        if start_dt or end_dt:
            filtered_apps = []
            for application in applications:
                applied_at = self._parse_datetime(application.get("applied_date"))
                if applied_at:
                    if start_dt and applied_at < start_dt:
                        continue
                    if end_dt and applied_at > end_dt:
                        continue
                filtered_apps.append(application)
            applications = filtered_apps
            allowed_ids = {row["application_id"] for row in applications if row.get("application_id")}
            events = [event for event in events if event.get("application_id") in allowed_ids]

        review_queue = await self.get_review_queue(user_id)
        graph = self.build_sankey_graph(
            applications,
            events,
            pending_review_count=review_queue["pending_count"],
        )
        return graph

    async def get_sankey_data(
        self,
        user_id: str,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        source_type: Optional[str] = None,
        company: Optional[str] = None,
    ) -> SankeyResponse:
        return await self.generate_sankey_data(
            user_id,
            start_date=start_date,
            end_date=end_date,
            source_type=source_type,
            company=company,
        )


application_source_service = ApplicationSourceService()
