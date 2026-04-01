import re
from dataclasses import dataclass
from datetime import date, datetime
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.models.api.application_event import ApplicationEventType
from app.models.api.job_application import ApplicationStatus

from ..base_service import BaseService, ServiceOperationError
from .supabase_client import supabase_service


AUTO_MERGE_THRESHOLD = 0.85
REVIEW_THRESHOLD = 0.60


@dataclass
class CandidateMatch:
    application_id: str
    company: str
    role: str
    score: float
    reason: str
    applied_date: Optional[datetime] = None
    location: Optional[str] = None
    job_posting_url: Optional[str] = None


class ApplicationMatcherService(BaseService):
    """Service for matching and updating job applications."""

    PLATFORM_DOMAINS = {
        "greenhouse.io",
        "lever.co",
        "ashbyhq.com",
        "workday.com",
        "hackerrank.com",
        "codesignal.com",
    }

    COMPANY_SUFFIXES = (
        "inc",
        "inc.",
        "llc",
        "ltd",
        "ltd.",
        "corp",
        "corp.",
        "corporation",
        "company",
    )

    def _initialize(self) -> None:
        self._log_operation("Application matcher service initialized")

    @staticmethod
    def _normalize_text(text: Optional[str]) -> str:
        if not text:
            return ""
        value = text.lower().strip()
        value = re.sub(r"[\(\)\[\]\{\}]", " ", value)
        value = re.sub(r"[^a-z0-9\s\-./]", " ", value)
        value = re.sub(r"\s+", " ", value)
        return value.strip()

    def normalize_company(self, text: Optional[str]) -> str:
        normalized = self._normalize_text(text)
        for suffix in self.COMPANY_SUFFIXES:
            if normalized.endswith(f" {suffix}"):
                normalized = normalized[: -len(suffix) - 1].strip()
        return normalized

    def normalize_role(self, text: Optional[str]) -> str:
        normalized = self._normalize_text(text)
        replacements = {
            "swe": "software engineer",
            "sde": "software engineer",
            "software dev": "software engineer",
            "developer": "engineer",
        }
        for source, target in replacements.items():
            normalized = normalized.replace(source, target)
        return normalized

    @staticmethod
    def extract_domain(value: Optional[str]) -> str:
        if not value:
            return ""
        parsed = urlparse(value if "://" in value else f"https://{value}")
        host = parsed.netloc or parsed.path
        host = host.lower().strip()
        if host.startswith("www."):
            host = host[4:]
        parts = host.split(".")
        if len(parts) >= 2:
            return ".".join(parts[-2:])
        return host

    def sender_domain(self, sender: Optional[str]) -> str:
        if not sender:
            return ""
        if "@" in sender:
            sender = sender.split("@", 1)[1]
        return self.extract_domain(sender)

    def _token_overlap_score(self, left: str, right: str) -> float:
        if not left or not right:
            return 0.0
        left_tokens = set(left.split())
        right_tokens = set(right.split())
        if not left_tokens or not right_tokens:
            return 0.0
        overlap = len(left_tokens & right_tokens)
        universe = len(left_tokens | right_tokens)
        return overlap / universe if universe else 0.0

    def _date_score(
        self, left: Optional[datetime], right: Optional[datetime]
    ) -> float:
        if not left or not right:
            return 0.0
        left_date = left.date() if isinstance(left, datetime) else left
        right_date = right.date() if isinstance(right, datetime) else right
        delta = abs((left_date - right_date).days)
        if delta == 0:
            return 1.0
        if delta <= 7:
            return 0.95
        if delta <= 14:
            return 0.8
        if delta <= 30:
            return 0.55
        if delta <= 60:
            return 0.25
        return 0.0

    def _company_score(
        self,
        left_company: str,
        right_company: str,
        sender_domain: str = "",
        source_url: str = "",
        candidate_url: str = "",
    ) -> tuple[float, List[str]]:
        reasons: List[str] = []
        if not left_company or not right_company:
            return 0.0, reasons

        if left_company == right_company:
            reasons.append("company exact match")
            score = 1.0
        else:
            seq = SequenceMatcher(None, left_company, right_company).ratio()
            token = self._token_overlap_score(left_company, right_company)
            score = max(seq, token)
            if token >= 0.5:
                reasons.append("company token overlap")
            elif seq >= 0.75:
                reasons.append("company fuzzy match")

        if sender_domain and sender_domain not in self.PLATFORM_DOMAINS:
            domain_hint = sender_domain.split(".")[0]
            if domain_hint and domain_hint in right_company:
                score = max(score, 0.95)
                reasons.append("sender domain matches company")

        if source_url and candidate_url:
            if self.extract_domain(source_url) == self.extract_domain(candidate_url):
                score = max(score, 0.95)
                reasons.append("source url domain matches candidate")

        return min(score, 1.0), reasons

    def _role_score(self, left_role: str, right_role: str) -> tuple[float, List[str]]:
        reasons: List[str] = []
        if not left_role or not right_role:
            return 0.0, reasons

        if left_role == right_role:
            return 1.0, ["role exact match"]

        seq = SequenceMatcher(None, left_role, right_role).ratio()
        token = self._token_overlap_score(left_role, right_role)
        score = max(seq, token)
        if token >= 0.5:
            reasons.append("role token overlap")
        elif seq >= 0.75:
            reasons.append("role fuzzy match")

        return min(score, 1.0), reasons

    def score_candidate(
        self,
        *,
        company: str,
        role: str,
        candidate_company: str,
        candidate_role: str,
        observed_at: Optional[datetime] = None,
        candidate_applied_at: Optional[datetime] = None,
        sender_domain: str = "",
        source_url: str = "",
        candidate_url: str = "",
        location: Optional[str] = None,
        candidate_location: Optional[str] = None,
    ) -> CandidateMatch:
        normalized_company = self.normalize_company(company)
        normalized_candidate_company = self.normalize_company(candidate_company)
        normalized_role = self.normalize_role(role)
        normalized_candidate_role = self.normalize_role(candidate_role)

        company_score, company_reasons = self._company_score(
            normalized_company,
            normalized_candidate_company,
            sender_domain=sender_domain,
            source_url=source_url,
            candidate_url=candidate_url,
        )
        role_score, role_reasons = self._role_score(
            normalized_role, normalized_candidate_role
        )
        date_score = self._date_score(observed_at, candidate_applied_at)
        reasons = company_reasons + role_reasons

        if location and candidate_location and self._normalize_text(location) == self._normalize_text(candidate_location):
            reasons.append("location exact match")
            location_score = 0.1
        else:
            location_score = 0.0

        score = (
            company_score * 0.5
            + role_score * 0.25
            + date_score * 0.2
            + location_score
        )

        if sender_domain:
            if sender_domain in self.PLATFORM_DOMAINS:
                score += 0.02
                reasons.append("platform sender observed")
            elif sender_domain and sender_domain.split(".")[0] in normalized_candidate_company:
                score += 0.05

        return CandidateMatch(
            application_id="",
            company=candidate_company,
            role=candidate_role,
            score=min(score, 1.0),
            reason=", ".join(reasons) if reasons else "heuristic score",
            applied_date=candidate_applied_at,
            location=candidate_location,
            job_posting_url=candidate_url or None,
        )

    async def list_candidate_applications(
        self, user_id: str
    ) -> List[Dict[str, Any]]:
        supabase = await supabase_service.get_client()
        response = (
            await supabase.table("job_applications")
            .select(
                "application_id,company,role,location,job_posting_url,applied_date,status,canonical_source,application_origin,application_inferred"
            )
            .eq("user_id", user_id)
            .execute()
        )
        return response.data or []

    async def rank_matches(
        self,
        *,
        user_id: str,
        company: str,
        role: str,
        observed_at: Optional[datetime] = None,
        sender: Optional[str] = None,
        source_url: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 5,
    ) -> List[CandidateMatch]:
        candidates = await self.list_candidate_applications(user_id)
        sender_domain = self.sender_domain(sender)
        scored: List[CandidateMatch] = []
        for row in candidates:
            applied_at = row.get("applied_date")
            if isinstance(applied_at, str):
                try:
                    applied_at = datetime.fromisoformat(applied_at.replace("Z", "+00:00"))
                except Exception:
                    applied_at = None
            scored.append(
                self.score_candidate(
                    company=company,
                    role=role,
                    candidate_company=row.get("company") or "",
                    candidate_role=row.get("role") or "",
                    observed_at=observed_at,
                    candidate_applied_at=applied_at,
                    sender_domain=sender_domain,
                    source_url=source_url or "",
                    candidate_url=row.get("job_posting_url") or "",
                    location=location,
                    candidate_location=row.get("location"),
                )
            )
            scored[-1].application_id = row.get("application_id") or ""

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:limit]

    async def find_best_application_match(
        self,
        user_id: str,
        company: str,
        role: str,
        location: Optional[str] = None,
        observed_at: Optional[datetime] = None,
        sender: Optional[str] = None,
        source_url: Optional[str] = None,
    ) -> Optional[CandidateMatch]:
        try:
            ranked = await self.rank_matches(
                user_id=user_id,
                company=company,
                role=role,
                observed_at=observed_at,
                sender=sender,
                source_url=source_url,
                location=location,
                limit=3,
            )
            if not ranked:
                self._log_operation(
                    "no matching application found", f"company: {company}, role: {role}"
                )
                return None
            best = ranked[0]
            if best.score < REVIEW_THRESHOLD:
                self._log_operation(
                    "best match below review threshold",
                    f"company: {company}, role: {role}, score: {best.score:.2f}",
                )
                return None
            if len(ranked) > 1 and (best.score - ranked[1].score) < 0.05:
                self._log_operation(
                    "ambiguous top matches",
                    f"company: {company}, role: {role}, score: {best.score:.2f}",
                )
                return None
            best.application_id = best.application_id or ""
            return best
        except Exception as e:
            self._log_error("finding matching application", e)
            raise ServiceOperationError(
                f"Failed to find matching application: {str(e)}"
            )

    async def find_matching_application(
        self,
        user_id: str,
        company: str,
        role: str,
        location: Optional[str] = None,
        observed_at: Optional[datetime] = None,
        sender: Optional[str] = None,
        source_url: Optional[str] = None,
    ) -> Optional[str]:
        match = await self.find_best_application_match(
            user_id=user_id,
            company=company,
            role=role,
            location=location,
            observed_at=observed_at,
            sender=sender,
            source_url=source_url,
        )
        if match and match.score >= AUTO_MERGE_THRESHOLD and match.application_id:
            self._log_operation(
                "match found",
                f"company: {company}, role: {role}, score: {match.score:.2f}",
            )
            return match.application_id
        return None

    async def find_existing_application_exact(
        self,
        *,
        user_id: str,
        company: str,
        role: str,
        location: Optional[str] = None,
        source_url: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        candidates = await self.list_candidate_applications(user_id)
        normalized_company = self.normalize_company(company)
        normalized_role = self.normalize_role(role)
        normalized_source_domain = self.extract_domain(source_url)
        normalized_location = self._normalize_text(location)

        exact_matches: List[Dict[str, Any]] = []
        for row in candidates:
            if self.normalize_company(row.get("company")) != normalized_company:
                continue
            if self.normalize_role(row.get("role")) != normalized_role:
                continue

            candidate_domain = self.extract_domain(row.get("job_posting_url"))
            if normalized_source_domain and candidate_domain:
                if normalized_source_domain != candidate_domain:
                    continue

            candidate_location = self._normalize_text(row.get("location"))
            if normalized_location and candidate_location:
                if normalized_location != candidate_location:
                    continue

            exact_matches.append(row)

        if not exact_matches:
            return None

        def sort_key(row: Dict[str, Any]) -> tuple[int, str]:
            applied_date = row.get("applied_date") or ""
            return (1 if applied_date else 0, str(applied_date))

        exact_matches.sort(key=sort_key, reverse=True)
        return exact_matches[0]

    @staticmethod
    def infer_status_from_text(status_text: Optional[str]) -> ApplicationStatus:
        normalized = (status_text or "").lower()
        if any(token in normalized for token in ["reject", "no longer", "not moving"]):
            return ApplicationStatus.REJECTED
        if any(token in normalized for token in ["offer", "offered"]):
            return ApplicationStatus.OFFERED
        if any(token in normalized for token in ["accept", "accepted", "hired"]):
            return ApplicationStatus.ACCEPTED
        if any(token in normalized for token in ["withdraw", "withdrawn"]):
            return ApplicationStatus.WITHDRAWN
        if any(token in normalized for token in ["interview", "onsite", "final round"]):
            return ApplicationStatus.INTERVIEW
        if any(token in normalized for token in ["assessment", "hackerrank", "codesignal", "oa"]):
            return ApplicationStatus.ASSESSMENT
        return ApplicationStatus.APPLIED

    @staticmethod
    def event_type_from_status(
        status: ApplicationStatus,
    ) -> ApplicationEventType:
        mapping = {
            ApplicationStatus.APPLIED: ApplicationEventType.APPLICATION_SUBMITTED,
            ApplicationStatus.ASSESSMENT: ApplicationEventType.ASSESSMENT_RECEIVED,
            ApplicationStatus.INTERVIEW: ApplicationEventType.INTERVIEW_SCHEDULED,
            ApplicationStatus.REJECTED: ApplicationEventType.APPLICATION_REJECTED,
            ApplicationStatus.OFFERED: ApplicationEventType.OFFER_RECEIVED,
            ApplicationStatus.ACCEPTED: ApplicationEventType.OFFER_ACCEPTED,
            ApplicationStatus.WITHDRAWN: ApplicationEventType.APPLICATION_WITHDRAWN,
        }
        return mapping.get(status, ApplicationEventType.APPLICATION_RECEIVED)


application_matcher_service = ApplicationMatcherService()
