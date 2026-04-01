from datetime import datetime, timezone

from app.models.api.application_event import ApplicationEventType
from app.models.api.job_application import ApplicationStatus
from app.services.supabase.application_matcher_service import (
    AUTO_MERGE_THRESHOLD,
    REVIEW_THRESHOLD,
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
        node.id == "OFFERED" and node.kind.value == "progress" and node.column == 4
        for node in graph.nodes
    )
