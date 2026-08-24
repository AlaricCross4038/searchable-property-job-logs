from datetime import date

from datetime import datetime, timezone

from property_job import PropertyJobRequest, decide_job, log_entries


def test_near_inspection_creates_reminder_without_escalating_repair() -> None:
    request = PropertyJobRequest.model_validate(
        {
            "job_id": "job-17",
            "maintenance": {
                "request_id": "maint-17",
                "unit_id": "unit-2A",
                "category": "cabinet-hinge",
                "safety_related": False,
            },
            "document": {
                "document_id": "doc-17",
                "unit_id": "unit-2A",
                "document_type": "move-in-report",
                "received": False,
            },
            "inspection": {
                "inspection_id": "inspect-17",
                "unit_id": "unit-2A",
                "due_on": "2026-08-19",
            },
        }
    )

    decision = decide_job(request, today=date(2026, 8, 17))

    assert decision.maintenance_queue == "standard"
    assert decision.document_status == "awaiting"
    assert decision.inspection_reminder is True

    recorded_at = datetime(2026, 8, 17, tzinfo=timezone.utc)
    first_attempt = log_entries(request, decision, recorded_at=recorded_at)
    retry_attempt = log_entries(request, decision, recorded_at=recorded_at)

    assert retry_attempt == first_attempt
