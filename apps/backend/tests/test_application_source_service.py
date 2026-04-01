from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.models.api.application_event import ApplicationEventType
from app.models.llm.llm_email import EmailIntent, LLMEmailOutput
from app.models.api.job_application import ApplicationStatus
import app.services.supabase.application_source_service as application_source_module
from app.services.supabase.application_matcher_service import (
    AUTO_MERGE_THRESHOLD,
    REVIEW_THRESHOLD,
    CandidateMatch,
    application_matcher_service,
)
from app.services.supabase.application_source_service import application_source_service


def _application(
    application_id: str,
    *,
    status: str = ApplicationStatus.APPLIED.value,
    applied_date: datetime | None = None,
    application_inferred: bool = False,
) -> dict:
    return {
        "application_id": application_id,
        "status": status,
        "applied_date": applied_date.isoformat() if applied_date else None,
        "application_inferred": application_inferred,
    }


def _event(application_id: str, event_type: str, event_date: datetime) -> dict:
    return {
        "application_id": application_id,
        "event_type": event_type,
        "event_date": event_date.isoformat(),
    }


class _FakeQuery:
    def __init__(self, table_name: str, datasets: dict):
        self.table_name = table_name
        self.datasets = datasets
        self.user_id = None
        self.application_ids = None
        self.company = None
        self.source_type = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, field: str, value):
        if field == "user_id":
            self.user_id = value
        elif field == "canonical_source":
            self.source_type = value
        return self

    def ilike(self, field: str, value):
        if field == "company":
            self.company = value
        return self

    def in_(self, field: str, values):
        if field == "application_id":
            self.application_ids = list(values)
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    async def execute(self):
        if self.table_name == "job_applications":
            rows = [
                row
                for row in self.datasets["job_applications"]
                if self.user_id is None or row.get("user_id") == self.user_id
            ]
            if self.company:
                company_filter = self.company.strip("%").lower()
                rows = [
                    row for row in rows if company_filter in (row.get("company") or "").lower()
                ]
            if self.source_type:
                rows = [
                    row
                    for row in rows
                    if row.get("canonical_source") == self.source_type
                ]
            return SimpleNamespace(data=rows)

        if self.table_name == "application_events":
            rows = [
                row
                for row in self.datasets["application_events"]
                if self.user_id is None or row.get("user_id") == self.user_id
            ]
            if self.application_ids is not None:
                rows = [
                    row for row in rows if row.get("application_id") in self.application_ids
                ]
            return SimpleNamespace(data=rows)

        return SimpleNamespace(data=[])


class _FakeSupabaseClient:
    def __init__(self, datasets: dict):
        self.datasets = datasets

    def table(self, table_name: str):
        return _FakeQuery(table_name, self.datasets)


def test_parse_upload_rows_supports_aliases_and_reports_errors():
    csv_payload = """Company Name,Job Title,Application Date,Application Status,Job Url,Contact Email,Resume Name,Question And Answers
OpenAI,Software Engineer,"10/13/25, 1:07 AM",Submitted,https://jobs.example/openai,test@example.com,resume.pdf,"What is your GPA?:4.0"
Broken Row,,2026-01-11,Submitted,https://jobs.example/bad
"""

    rows, errors, skipped = application_source_service.parse_upload_rows(
        "linkedin.csv", csv_payload.encode("utf-8")
    )

    assert len(rows) == 1
    assert rows[0]["company"] == "OpenAI"
    assert rows[0]["role"] == "Software Engineer"
    assert rows[0]["status_text"] == "Submitted"
    assert rows[0]["job_url"] == "https://jobs.example/openai"
    assert rows[0]["applied_at"] == datetime(2025, 10, 13, 1, 7, tzinfo=timezone.utc)
    assert rows[0]["payload_json"] == {
        "company": "OpenAI",
        "role": "Software Engineer",
        "applied_at": "10/13/25, 1:07 AM",
        "status_text": "Submitted",
        "job_url": "https://jobs.example/openai",
    }
    assert len(errors) == 1
    assert errors[0]["row_number"] == 2
    assert skipped == []


def test_parse_upload_rows_skips_rows_outside_applied_date_range():
    csv_payload = """Company Name,Job Title,Application Date,Job Url
OpenAI,Software Engineer,"10/13/25, 1:07 AM",https://jobs.example/openai
Anthropic,Research Engineer,"02/10/26, 9:30 AM",https://jobs.example/anthropic
"""

    rows, errors, skipped = application_source_service.parse_upload_rows(
        "linkedin.csv",
        csv_payload.encode("utf-8"),
        min_applied_date=date(2026, 1, 1),
        max_applied_date=date(2026, 12, 31),
    )

    assert errors == []
    assert len(rows) == 1
    assert rows[0]["company"] == "Anthropic"
    assert len(skipped) == 1
    assert skipped[0]["row_number"] == 1


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


def test_build_sankey_graph_marks_non_inferred_applied_only_paths_as_ghosted():
    applications = [
        _application(
            "app-ghosted",
            applied_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
        ),
        _application(
            "app-withdrawn",
            status=ApplicationStatus.WITHDRAWN.value,
            applied_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
        ),
    ]

    graph = application_source_service.build_sankey_graph(applications, [])

    assert graph.meta.ghosted_count == 1
    assert graph.meta.total_applications == 2

    ghosted_node = next(node for node in graph.nodes if node.id == "GHOSTED")
    assert ghosted_node.kind.value == "ghosted"
    assert ghosted_node.column == 5
    assert ghosted_node.count == 1

    applied_node = next(node for node in graph.nodes if node.id == "APPLIED")
    assert applied_node.kind.value == "root"
    assert applied_node.column == 0
    assert applied_node.count == 2

    assert any(
        link.source == "APPLIED" and link.target == "GHOSTED" and link.value == 1
        for link in graph.links
    )
    assert not any(link.target == "GHOSTED" and link.value > 1 for link in graph.links)
    assert any(
        link.source == "APPLIED" and link.target == "WITHDRAWN" and link.value == 1
        for link in graph.links
    )


def test_build_sankey_graph_branches_through_rejection_and_final_round():
    application = _application(
        "app-1",
        status=ApplicationStatus.OFFERED.value,
        applied_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    events = [
        _event(
            "app-1",
            ApplicationEventType.ASSESSMENT_RECEIVED.value,
            datetime(2026, 1, 5, tzinfo=timezone.utc),
        ),
        _event(
            "app-1",
            ApplicationEventType.INTERVIEW_SCHEDULED.value,
            datetime(2026, 1, 10, tzinfo=timezone.utc),
        ),
        _event(
            "app-1",
            ApplicationEventType.FINAL_ROUND.value,
            datetime(2026, 1, 15, tzinfo=timezone.utc),
        ),
        _event(
            "app-1",
            ApplicationEventType.OFFER_RECEIVED.value,
            datetime(2026, 1, 20, tzinfo=timezone.utc),
        ),
    ]

    graph = application_source_service.build_sankey_graph([application], events)

    assert [node.id for node in graph.nodes] == [
        "APPLIED",
        "ASSESSMENT",
        "INTERVIEW",
        "FINAL_ROUND",
        "OFFERED",
    ]
    assert [node.column for node in graph.nodes] == [0, 1, 2, 3, 4]
    assert [link.source + "->" + link.target for link in graph.links] == [
        "APPLIED->ASSESSMENT",
        "ASSESSMENT->INTERVIEW",
        "FINAL_ROUND->OFFERED",
        "INTERVIEW->FINAL_ROUND",
    ]
    assert graph.meta.ghosted_count == 0
    assert graph.meta.inferred_count == 0


def test_build_sankey_graph_branches_through_rejection():
    application = _application(
        "app-rejected",
        status=ApplicationStatus.REJECTED.value,
        applied_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    events = [
        _event(
            "app-rejected",
            ApplicationEventType.ASSESSMENT_RECEIVED.value,
            datetime(2026, 1, 5, tzinfo=timezone.utc),
        ),
        _event(
            "app-rejected",
            ApplicationEventType.INTERVIEW_SCHEDULED.value,
            datetime(2026, 1, 10, tzinfo=timezone.utc),
        ),
        _event(
            "app-rejected",
            ApplicationEventType.APPLICATION_REJECTED.value,
            datetime(2026, 1, 20, tzinfo=timezone.utc),
        ),
    ]

    graph = application_source_service.build_sankey_graph([application], events)

    assert [node.id for node in graph.nodes] == [
        "APPLIED",
        "ASSESSMENT",
        "INTERVIEW",
        "REJECTED",
    ]
    assert [link.source + "->" + link.target for link in graph.links] == [
        "APPLIED->ASSESSMENT",
        "ASSESSMENT->INTERVIEW",
        "INTERVIEW->REJECTED",
    ]
    assert graph.meta.ghosted_count == 0


def test_build_sankey_graph_ignores_repeated_same_stage_events_and_handles_inferred_first_signal():
    applications = [
        _application(
            "app-repeat",
            applied_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
        _application(
            "app-inferred",
            status=ApplicationStatus.INTERVIEW.value,
            application_inferred=True,
            applied_date=None,
        ),
    ]
    events = [
        _event(
            "app-repeat",
            ApplicationEventType.INTERVIEW_SCHEDULED.value,
            datetime(2026, 1, 5, tzinfo=timezone.utc),
        ),
        _event(
            "app-repeat",
            ApplicationEventType.INTERVIEW_COMPLETED.value,
            datetime(2026, 1, 6, tzinfo=timezone.utc),
        ),
        _event(
            "app-repeat",
            ApplicationEventType.FINAL_ROUND.value,
            datetime(2026, 1, 8, tzinfo=timezone.utc),
        ),
        _event(
            "app-repeat",
            ApplicationEventType.OFFER_RECEIVED.value,
            datetime(2026, 1, 10, tzinfo=timezone.utc),
        ),
        _event(
            "app-inferred",
            ApplicationEventType.INTERVIEW_SCHEDULED.value,
            datetime(2026, 1, 9, tzinfo=timezone.utc),
        ),
    ]

    graph = application_source_service.build_sankey_graph(
        applications,
        events,
    )

    assert graph.meta.inferred_count == 1
    assert graph.meta.ghosted_count == 0

    assert not any(link.source == "INTERVIEW" and link.target == "INTERVIEW" for link in graph.links)
    assert any(link.source == "APPLIED" and link.target == "INTERVIEW" and link.value == 2 for link in graph.links)
        assert any(
            link.source == "INTERVIEW" and link.target == "FINAL_ROUND" and link.value == 1
            for link in graph.links
        )
        assert any(
            node.id == "INTERVIEW" and node.kind.value == "progress" and node.column == 2
            for node in graph.nodes
        )
    assert any(
        node.id == "OFFERED" and node.kind.value == "progress" and node.column == 6
        for node in graph.nodes
    )


@pytest.mark.asyncio
async def test_force_reparse_updates_existing_email_source_without_creating_application(
    monkeypatch,
):
    parsed = LLMEmailOutput(
        company="OpenAI",
        role="Software Engineer",
        status=ApplicationStatus.INTERVIEW,
        intent=EmailIntent.APPLICATION_EVENT,
        location="Singapore",
        salary_range=None,
        notes="Interview scheduled",
        event_type=ApplicationEventType.INTERVIEW_SCHEDULED,
        event_description="Interview scheduled",
        event_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )
    existing_source = {
        "source_id": "source-1",
        "application_id": "app-1",
        "candidate_application_id": None,
        "merge_status": "UNMATCHED",
        "merge_confidence": 0.92,
        "review_reason": None,
    }
    updated_source = {"source_id": "source-1", "application_id": "app-1"}
    updated_application = {"application_id": "app-1"}
    updated_event = {"event_id": "event-1", "application_id": "app-1"}

    monkeypatch.setattr(
        application_source_service,
        "_fetch_source_by_external_source",
        AsyncMock(return_value=existing_source),
    )
    monkeypatch.setattr(
        application_source_service,
        "_build_source_payload_from_email",
        AsyncMock(return_value={"application_id": "app-1"}),
    )
    monkeypatch.setattr(
        application_source_service,
        "_update_source_record",
        AsyncMock(return_value=updated_source),
    )
    monkeypatch.setattr(
        application_source_service,
        "_update_application",
        AsyncMock(return_value=updated_application),
    )
    monkeypatch.setattr(
        application_source_service,
        "_fetch_event_by_source",
        AsyncMock(return_value={"event_id": "event-1"}),
    )
    monkeypatch.setattr(
        application_source_service,
        "_update_event",
        AsyncMock(return_value=updated_event),
    )
    create_application = AsyncMock()
    monkeypatch.setattr(
        application_source_service, "_create_application", create_application
    )

    result = await application_source_service.process_email_source(
        user_id="user-1",
        parsed=parsed,
        email_id="email-1",
        sender="jobs@openai.com",
        subject="Interview scheduled",
        received_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )

    assert result["application"] == updated_application
    assert result["event"] == updated_event
    create_application.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_email_source_reuses_exact_existing_application_before_create(
    monkeypatch,
):
    parsed = LLMEmailOutput(
        company="OpenAI",
        role="Software Engineer",
        status=ApplicationStatus.APPLIED,
        intent=EmailIntent.NEW_APPLICATION,
        location="Singapore",
        salary_range=None,
        notes="Applied",
        event_type=None,
        event_description=None,
        event_date=None,
    )

    monkeypatch.setattr(
        application_source_service,
        "_fetch_source_by_external_source",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        application_matcher_service,
        "find_best_application_match",
        AsyncMock(
            return_value=CandidateMatch(
                application_id="",
                company="Other Company",
                role="Different Role",
                score=0.2,
                reason="below threshold",
            )
        ),
    )
    monkeypatch.setattr(
        application_matcher_service,
        "find_existing_application_exact",
        AsyncMock(
            return_value={
                "application_id": "app-1",
                "company": "OpenAI",
                "role": "Software Engineer",
            }
        ),
    )
    monkeypatch.setattr(
        application_source_service,
        "_create_source_record",
        AsyncMock(return_value={"source_id": "source-1"}),
    )
    monkeypatch.setattr(
        application_source_service,
        "_build_source_payload_from_email",
        AsyncMock(return_value={"application_id": "app-1"}),
    )
    monkeypatch.setattr(
        application_source_service,
        "_update_application",
        AsyncMock(return_value={"application_id": "app-1"}),
    )
    monkeypatch.setattr(
        application_source_service,
        "_create_event",
        AsyncMock(return_value={"event_id": "event-1", "application_id": "app-1"}),
    )
    create_application = AsyncMock()
    monkeypatch.setattr(
        application_source_service, "_create_application", create_application
    )

    result = await application_source_service.process_email_source(
        user_id="user-1",
        parsed=parsed,
        email_id="email-2",
        sender="jobs@openai.com",
        subject="Application received",
        received_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )

    assert result["application"]["application_id"] == "app-1"
    assert result["event"]["application_id"] == "app-1"
    create_application.assert_not_awaited()


@pytest.mark.asyncio
async def test_generate_sankey_data_filters_to_requested_date_range(monkeypatch):
    datasets = {
        "job_applications": [
            {
                "application_id": "app-before",
                "user_id": "user-1",
                "status": ApplicationStatus.OFFERED.value,
                "applied_date": datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat(),
                "application_inferred": False,
            },
            {
                "application_id": "app-in-range",
                "user_id": "user-1",
                "status": ApplicationStatus.APPLIED.value,
                "applied_date": datetime(2026, 1, 20, tzinfo=timezone.utc).isoformat(),
                "application_inferred": False,
            },
        ],
        "application_events": [
            {
                "application_id": "app-before",
                "user_id": "user-1",
                "event_type": ApplicationEventType.ASSESSMENT_RECEIVED.value,
                "event_date": datetime(2026, 1, 5, tzinfo=timezone.utc).isoformat(),
            },
            {
                "application_id": "app-before",
                "user_id": "user-1",
                "event_type": ApplicationEventType.INTERVIEW_SCHEDULED.value,
                "event_date": datetime(2026, 1, 10, tzinfo=timezone.utc).isoformat(),
            },
        ],
    }
    fake_client = _FakeSupabaseClient(datasets)
    monkeypatch.setattr(
        application_source_module.supabase_service,
        "get_client",
        AsyncMock(return_value=fake_client),
    )
    monkeypatch.setattr(
        application_source_service,
        "get_review_queue",
        AsyncMock(return_value={"items": [], "pending_count": 0}),
    )

    graph = await application_source_service.generate_sankey_data(
        "user-1",
        start_date="2026-01-10",
        end_date="2026-01-31",
    )

    assert graph.meta.total_applications == 1
    assert graph.meta.ghosted_count == 1
    assert [node.id for node in graph.nodes] == ["APPLIED", "GHOSTED"]
    assert [link.source + "->" + link.target for link in graph.links] == [
        "APPLIED->GHOSTED"
    ]
