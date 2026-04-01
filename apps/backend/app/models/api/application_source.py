from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ApplicationSourceType(str, Enum):
    EMAIL = "EMAIL"
    LINKEDIN_EASY_APPLY = "LINKEDIN_EASY_APPLY"


class ApplicationMergeStatus(str, Enum):
    AUTO_MERGED = "AUTO_MERGED"
    PENDING_REVIEW = "PENDING_REVIEW"
    UNMATCHED = "UNMATCHED"
    MANUALLY_CONFIRMED = "MANUALLY_CONFIRMED"
    MANUALLY_SEPARATED = "MANUALLY_SEPARATED"


class ApplicationSourceCreate(BaseModel):
    user_id: str
    source_type: ApplicationSourceType
    external_source_id: Optional[str] = None
    application_id: Optional[str] = None
    candidate_application_id: Optional[str] = None
    company_raw: str
    role_raw: str
    applied_at: Optional[datetime] = None
    observed_at: Optional[datetime] = None
    sender_domain: Optional[str] = None
    source_url: Optional[str] = None
    payload_json: Optional[Dict[str, Any]] = None
    merge_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    merge_status: ApplicationMergeStatus = ApplicationMergeStatus.UNMATCHED
    review_reason: Optional[str] = None


class ApplicationSourceRead(ApplicationSourceCreate):
    source_id: str
    created_at: datetime


class ApplicationSourceReviewItem(BaseModel):
    source_id: str
    application_id: Optional[str] = None
    candidate_application_id: Optional[str] = None
    source_type: ApplicationSourceType
    company_raw: str
    role_raw: str
    applied_at: Optional[datetime] = None
    observed_at: Optional[datetime] = None
    sender_domain: Optional[str] = None
    source_url: Optional[str] = None
    merge_confidence: Optional[float] = None
    merge_status: ApplicationMergeStatus
    review_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    candidate_company: Optional[str] = None
    candidate_role: Optional[str] = None
    status_text: Optional[str] = None


class ImportRowOutcome(BaseModel):
    row_number: int
    status: str
    application_id: Optional[str] = None
    source_id: Optional[str] = None
    confidence: Optional[float] = None
    reason: Optional[str] = None


class LinkedInImportResponse(BaseModel):
    processed_count: int
    created_count: int
    merged_count: int
    review_count: int
    failed_count: int
    outcomes: List[ImportRowOutcome]


class ReviewActionResponse(BaseModel):
    success: bool
    source_id: str
    merge_status: ApplicationMergeStatus


class SankeyNode(BaseModel):
    id: str
    label: str
    count: int


class SankeyLink(BaseModel):
    source: str
    target: str
    value: int


class SankeyResponse(BaseModel):
    nodes: List[SankeyNode]
    links: List[SankeyLink]
    meta: Dict[str, Any]
