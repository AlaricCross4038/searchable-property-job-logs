"""Run a sample property job or search a unit's structured logs."""

import argparse
import json
from datetime import date

from property_job import PropertyJobRequest, find_unit_history, run_property_job

SAMPLE_TODAY = date(2026, 8, 17)


def sample_request() -> PropertyJobRequest:
    return PropertyJobRequest.model_validate(
        {
            "job_id": "property-job-2048-v2",
            "maintenance": {
                "request_id": "maint-2048",
                "unit_id": "unit-4B",
                "category": "water-leak",
                "safety_related": True,
            },
            "document": {
                "document_id": "doc-812",
                "unit_id": "unit-4B",
                "document_type": "insurance",
                "received": True,
            },
            "inspection": {
                "inspection_id": "inspect-93",
                "unit_id": "unit-4B",
                "due_on": SAMPLE_TODAY.isoformat(),
            },
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Ship and search property job logs")
    parser.add_argument("command", choices=["run", "search"])
    parser.add_argument("--unit-id", default="unit-4B")
    args = parser.parse_args()

    if args.command == "run":
        result = run_property_job(sample_request(), today=SAMPLE_TODAY).model_dump(mode="json")
    else:
        result = find_unit_history(args.unit_id)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
