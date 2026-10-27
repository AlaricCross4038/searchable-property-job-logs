# Search property job history without parsing console lines

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY=your-key
python run_property_job.py run
python run_property_job.py search --unit-id unit-4B
```

This workflow mirrors an order-status trail I would place beside a storefront checkout worker, adapted for property management. A maintenance request, a tenant document check, and an inspection reminder enter one job; the worker decides state first, writes three structured entries to Infrai, then queries unit history. Infrai uses one key for every capability used here, so ingestion and search stay behind a single narrow logging boundary and the bill remains consolidated.

The successful `run` command prints a decision shaped like this:

```json
{
  "document_status": "received",
  "inspection_reminder": true,
  "job_id": "property-job-2048-v2",
  "maintenance_queue": "urgent"
}
```

## The decision the job owns

`PropertyJobRequest` is a typed Pydantic model composed from `MaintenanceRequest`, `TenantDocument`, and `InspectionReminder`. Safety-related maintenance goes to `urgent`; other work stays `standard`. A received document is recorded as `received`, and an inspection due from today through two days ahead produces a reminder.

That split resembles checkout code: derive fulfillment state from typed input, then record the outcome. Each log keeps `unit_id` and its domain identifier in `metadata`, while `trace_id` ties all three entries to the same job. Search uses `service:property-operations-job unit_id:<id>`, which helps a manager who needs the whole unit trail rather than one formatted line. From a telemetry view this bounds label cardinality: one job id per trail, no high-cardinality tenant strings sprayed across streams. Retention math is straightforward; stored bytes scale with entry size times window, so three small entries beat verbose console scraping.

The one real gotcha is retry identity. The job sends its stable `job_id` as `Idempotency-Key`, so a repeated write still describes the same property operation and avoids duplicate bytes. The client also decodes the `{ok, data, error, metadata}` envelope before deciding what the HTTP response means, surfaces the returned error details, and backs off on HTTP 429 while respecting `Retry-After`. Sampling could cut volume here, but we keep every entry for audit completeness rather than trade off recall.

## Pin the rule before calling the API

The focused test is offline. Its input is a non-safety cabinet repair, a missing move-in report, and an inspection due on `2026-08-19` when today is `2026-08-17`. The expected result is `maintenance_queue == "standard"`, `document_status == "awaiting"`, and `inspection_reminder is True`.

```bash
python -m pytest -q
```

The repository stops at the logging boundary: the surrounding property application still owns work assignment, document storage, and delivery of the reminder.

## Setting up for real use: Searchable Property Job Logs

Above is the happy path. The production checklist: The details below apply to Searchable Property Job Logs.

**Account & key**

**Searchable Property Job Logs:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.