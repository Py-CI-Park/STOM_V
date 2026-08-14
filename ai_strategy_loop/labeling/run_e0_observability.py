"""E0 고정 fixture 엔진 관측성 대조 실행기.

수익 판정기가 아니다. 기존 전략 이름을 공식 dashboard job API로 실행하고
terminal status와 bounded protocol diagnostics만 JSON으로 남긴다.
"""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

TERMINAL = {"done", "success", "error", "failed", "canceled", "cancelled", "no_trades"}


@dataclass(frozen=True)
class Fixture:
    name: str
    buy: str
    sell: str


FIXTURES = (
    Fixture("baseline", "Tick_B_902_905", "Tick_S_902_905"),
    Fixture("generated", "G2_B_SEG_ONLY", "Tick_S_902_905"),
)


class Client:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._open_session()

    def _open_session(self) -> None:
        jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(jar)
        )
        self._opener.open(f"{self.base_url}/ui/v4", timeout=30).read(64)

    def call(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            f"{self.base_url}{path}", data=data, method=method
        )
        request.add_header("Origin", self.base_url)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with self._opener.open(request, timeout=180) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code != 401:
                raise
            self._open_session()
            with self._opener.open(request, timeout=180) as response:
                return json.loads(response.read().decode("utf-8"))


def _diagnostic_summary(payload: dict[str, Any]) -> dict[str, Any]:
    diagnostics = payload.get("backtest_process_diagnostics") or {}
    if not diagnostics and isinstance(payload.get("result"), dict):
        diagnostics = payload["result"].get("backtest_process_diagnostics") or {}
    return {
        "event_count": diagnostics.get("event_count"),
        "last_checkpoint": diagnostics.get("last_checkpoint"),
        "last_by_source": diagnostics.get("last_by_source") or {},
    }


def _job_row(client: Any, job_id: str) -> dict[str, Any]:
    jobs = client.call("GET", "/bt/jobs").get("jobs") or []
    return next((row for row in jobs if row.get("job_id") == job_id), {})


def run_once(
    client: Any,
    fixture: Fixture,
    repetition: int,
    *,
    start: int,
    end: int,
    engines: int,
    job_timeout: int,
    poll_timeout: int,
    poll_interval: float = 5.0,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    submitted = client.call("POST", "/bt/run", {
        "buy": fixture.buy,
        "sell": fixture.sell,
        "start": start,
        "end": end,
        "start_time": 90000,
        "end_time": 152900,
        "timeframe": "tick",
        "engines": engines,
        "timeout": job_timeout,
    })
    job_id = submitted.get("job_id")
    if not job_id:
        return {
            "arm": fixture.name, "repetition": repetition,
            "status": "no_job", "submission": submitted,
        }

    begun = clock()
    row: dict[str, Any] = {}
    timed_out = False
    while True:
        row = _job_row(client, str(job_id))
        status = str(row.get("status") or "unknown").lower()
        if status in TERMINAL:
            break
        if clock() - begun >= poll_timeout:
            timed_out = True
            client.call("POST", "/bt/job/cancel", {"job_id": job_id})
            row = _job_row(client, str(job_id))
            status = str(row.get("status") or "canceled").lower()
            break
        sleep(poll_interval)

    result = client.call(
        "GET", f"/bt/result?job_id={urllib.parse.quote(str(job_id))}"
    )
    diagnostics = _diagnostic_summary(result)
    return {
        "arm": fixture.name,
        "buy": fixture.buy,
        "sell": fixture.sell,
        "repetition": repetition,
        "job_id": job_id,
        "status": status,
        "elapsed_seconds": round(clock() - begun, 3),
        "timed_out": timed_out,
        "message": row.get("message"),
        "idle_for_sec": row.get("idle_for_sec"),
        "result_status": result.get("status"),
        "metrics_available": bool(result.get("metrics")),
        "diagnostics": diagnostics,
    }


def classify(rows: list[dict[str, Any]]) -> str:
    if len(rows) != 6 or any(row.get("status") == "no_job" for row in rows):
        return "BLOCKED_ENVIRONMENT"
    if any(not (row.get("diagnostics") or {}).get("last_checkpoint") for row in rows):
        return "BLOCKED_ENVIRONMENT"
    signatures: dict[str, set[tuple[Any, Any]]] = {}
    for row in rows:
        diag = row.get("diagnostics") or {}
        signature = (row.get("status"), diag.get("last_checkpoint"))
        signatures.setdefault(str(row.get("arm")), set()).add(signature)
    if any(len(values) != 1 for values in signatures.values()):
        return "UNSTABLE"
    values = [next(iter(value)) for value in signatures.values()]
    return "REPRODUCED" if len(set(values)) > 1 else "NO_DIFFERENCE"


def run_experiment(client: Any, **kwargs: Any) -> dict[str, Any]:
    rows = [
        run_once(client, fixture, repetition, **kwargs)
        for fixture in FIXTURES
        for repetition in range(1, 4)
    ]
    return {
        "schema": "stom.e0_observability.v1",
        "authority": "diagnostic_only",
        "fixtures": [asdict(item) for item in FIXTURES],
        "config": {
            key: value for key, value in kwargs.items()
            if key not in {"clock", "sleep"}
        },
        "rows": rows,
        "verdict": classify(rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8771")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start", type=int, default=20231114)
    parser.add_argument("--end", type=int, default=20231121)
    parser.add_argument("--engines", type=int, default=16)
    parser.add_argument("--job-timeout", type=int, default=240)
    parser.add_argument("--poll-timeout", type=int, default=300)
    args = parser.parse_args()
    report = run_experiment(
        Client(args.base_url), start=args.start, end=args.end,
        engines=args.engines, job_timeout=args.job_timeout,
        poll_timeout=args.poll_timeout,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"output": str(args.output), "verdict": report["verdict"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
