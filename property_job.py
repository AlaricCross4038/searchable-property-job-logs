"""Property operations decision and structured log boundary."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel

from infrai_logs import infrai


class MaintenanceRequest(BaseModel):
    request_id: str
    unit_id: str
    category: str
    safety_related: bool


class TenantDocument(BaseModel):
    document_id: str
    unit_id: str
    document_type: Literal["lease", "insurance", "move-in-report"]
    received: bool


class InspectionReminder(BaseModel):
    inspection_id: str
    unit_id: str
    due_on: date


class PropertyJobRequest(BaseModel):
    job_id: str
    maintenance: MaintenanceRequest
    document: TenantDocument
    inspection: InspectionReminder


class JobDecision(BaseModel):
    job_id: str
    maintenance_queue: Literal["urgent", "standard"]
    document_status: Literal["received", "awaiting"]
    inspection_reminder: bool


def decide_job(request: PropertyJobRequest, *, today: date) -> JobDecision:
    """Choose the visible worker state before emitting any logs."""
    days_until_inspection = (request.inspection.due_on - today).days
    return JobDecision(
        job_id=request.job_id,
        maintenance_queue="urgent" if request.maintenance.safety_related else "standard",
        document_status="received" if request.document.received else "awaiting",
        inspection_reminder=0 <= days_until_inspection <= 2,
    )


def log_entries(
    request: PropertyJobRequest,
    decision: JobDecision,
    *,
    recorded_at: datetime,
) -> list[dict[str, Any]]:
    shared = {
        "service": "property-operations-job",
        "level": "info",
        "trace_id": request.job_id,
        "timestamp": recorded_at.astimezone(timezone.utc).isoformat(),
    }
    return [
        {
            **shared,
            "message": "maintenance request routed",
            "metadata": {
                "request_id": request.maintenance.request_id,
                "unit_id": request.maintenance.unit_id,
                "category": request.maintenance.category,
                "queue": decision.maintenance_queue,
            },
        },
        {
            **shared,
            "message": "tenant document checked",
            "metadata": {
                "document_id": request.document.document_id,
                "unit_id": request.document.unit_id,
                "document_type": request.document.document_type,
                "status": decision.document_status,
            },
        },
        {
            **shared,
            "message": "inspection reminder evaluated",
            "metadata": {
                "inspection_id": request.inspection.inspection_id,
                "unit_id": request.inspection.unit_id,
                "due_on": request.inspection.due_on.isoformat(),
                "reminder": decision.inspection_reminder,
            },
        },
    ]


def run_property_job(request: PropertyJobRequest, *, today: date) -> JobDecision:
    decision = decide_job(request, today=today)
    recorded_at = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
    infrai.logs.ingest(
        log_entries(request, decision, recorded_at=recorded_at),
        idempotency_key=request.job_id,
    )
    return decision


def find_unit_history(unit_id: str) -> dict[str, Any]:
    return infrai.logs.search(f"service:property-operations-job unit_id:{unit_id}")
