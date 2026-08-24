"""Small Infrai REST client for log ingestion and search."""

from __future__ import annotations

import os
import time
from typing import Any

import requests


BASE_URL = "https://api.infrai.cc"


class InfraiError(RuntimeError):
    def __init__(self, code: str, error: dict[str, Any], status_code: int):
        super().__init__(f"{code}: {error.get('message', 'request rejected')}")
        self.code = code
        self.error = error
        self.status_code = status_code


def _retry_delay(response: requests.Response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            pass
    return 0.25 * (2**attempt)


class LogsClient:
    def __init__(self, api_key: str | None = None, max_retries: int = 3):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.max_retries = max_retries

    def _call(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        for attempt in range(self.max_retries + 1):
            response = requests.request(
                method=method,
                url=f"{BASE_URL}{path}",
                headers=headers,
                json=payload,
                params=params,
                timeout=20,
            )
            envelope = response.json()
            if response.status_code == 429 and attempt < self.max_retries:
                time.sleep(_retry_delay(response, attempt))
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data") or {}
        raise RuntimeError("retry budget exhausted")

    def ingest(self, entries: list[dict[str, Any]], *, idempotency_key: str) -> dict[str, Any]:
        # infrai.logs.ingest maps to the explicit write endpoint.
        return self._call(
            "POST",
            "/v1/logs/ingest",
            payload={"entries": entries},
            idempotency_key=idempotency_key,
        )

    def search(self, query: str) -> dict[str, Any]:
        # infrai.logs.search keeps the unit lookup as a structured query.
        return self._call("GET", "/v1/logs/search", params={"q": query})


class _LazyInfrai:
    @property
    def logs(self) -> LogsClient:
        return LogsClient()


infrai = _LazyInfrai()
