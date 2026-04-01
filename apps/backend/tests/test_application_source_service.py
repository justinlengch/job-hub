from datetime import datetime, timezone

from app.models.api.application_event import ApplicationEventType
from app.models.api.job_application import ApplicationStatus
from app.services.supabase.application_matcher_service import (
    AUTO_MERGE_THRESHOLD,
    REVIEW_THRESHOLD,
    application_matcher_service,
)
from app.services.supabase.application_source_service import application_source_service


def test_parse_upload_rows_supports_aliases_and_reports_errors():
    csv_payload = """Company Name,Job Title,Date Applied,Application Status,Job Link
OpenAI,Software Engineer,2026-01-10,Submitted,https://jobs.example/openai
Broken Row,,2026-01-11,Submitted,https://jobs.example/bad
"""

    rows, errors = application_source_service.parse_upload_rows(
        "linkedin.csv", csv_payload.encode("utf-8")
    )

    assert len(rows) == 1
    assert rows[0]["company"] == "OpenAI"
    assert rows[0]["role"] == "Software Engineer"
    assert rows[0]["status_text"] == "Submitted"
    assert rows[0]["job_url"] == "https://jobs.example/openai"
    assert len(errors) == 1
    assert errors[0]["row_number"] == 2


def test_ranker_distinguishes_auto_merge_and_review_scores():
    observed_at = datetime(2026, 1, 15, tzinfo=timezone.utc)

    exact = application_matcher_service.score_candidate(
        company="OpenAI",
        role="Software Engineer",
        candidate_company="OpenAI",
        candidate_role="Software Engineer",
        observed_at=observed_at,
        candidate_applied_at=datetime(2026, 1, 10, tzinfo=timezone.utc),
        sender_domain="openai.com",
    )
    assert exact.score >= AUTO_MERGE_THRESHOLD

    review = application_matcher_service.score_candidate(
        company="Open AI",
        role="Software Engineer, Platform",
        candidate_company="OpenAI",
        candidate_role="Software Engineer",
        observed_at=observed_at,
        candidate_applied_at=datetime(2025, 12, 20, tzinfo=timezone.utc),
        sender_domain="greenhouse.io",
    )
    assert REVIEW_THRESHOLD <= review.score < AUTO_MERGE_THRESHOLD


def test_build_stage_path_infers_applied_but_keeps_final_round():
    application = {
        "application_id": "app-1",
        "status": ApplicationStatus.OFFERED.value,
        "application_inferred": True,
        "applied_date": None,
    }
    events = [
        {
            "event_type": ApplicationEventType.INTERVIEW_SCHEDULED.value,
            "event_date": "2026-01-10T00:00:00+00:00",
        },
        {
            "event_type": ApplicationEventType.FINAL_ROUND.value,
            "event_date": "2026-01-20T00:00:00+00:00",
        },
        {
            "event_type": ApplicationEventType.OFFER_RECEIVED.value,
            "event_date": "2026-01-25T00:00:00+00:00",
        },
    ]

    path = application_source_service._build_stage_path(application, events)

    assert path == ["APPLIED", "INTERVIEW", "FINAL_ROUND", "OFFERED"]
