# /// script
# requires-python = ">=3.13"
# dependencies = ["fastapi", "uvicorn"]
# ///
# Run with the existing STOM interpreter: python tests/manual/sq01_browser_fixture.py
"""Synthetic read-only UI fixture using production JSX and data-contract API.

No main app import, operating DB, research execution, or POST route is exposed.
Temporary CSVs live under a new OS temporary directory and are removed on exit.
"""

from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from typing import Final, TypedDict

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT: Final = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ai_strategy_loop.dashboard import trade_contract_api  # noqa: E402
from ai_strategy_loop.dashboard import backtest_api  # noqa: E402
from tests.unit.dashboard.trade_quality_fixtures import official_pair  # noqa: E402


class Spec(TypedDict):
    timeframe: str
    buy: str
    sell: str


class Metrics(TypedDict):
    trade_count: int


class Job(TypedDict):
    job_id: str
    available: bool
    status: str
    csv_path: str | None
    csv_exists: bool
    spec: Spec
    metrics: Metrics


class Jobs(TypedDict):
    jobs: list[Job]


class Preflight(TypedDict):
    available: bool
    forced_liquidation_time: int
    source: Spec
    trade_count: int
    date_count: int
    covered_date_count: int


class Flag(TypedDict):
    available: bool


def make_app(directory: Path) -> FastAPI:
    """Compose only the production read-only route and synthetic source discovery."""
    header, row = official_pair()
    row = row.replace("20250102090000", "202501020900").replace("20250102090100", "202501020901")
    cases = (
        ("normal", "정상 CSV", "success", row, 1),
        ("empty", "정상 무거래", "success", "", 0),
        ("partial", "부분 파싱", "success", row + "bad\n", 2),
        ("failed", "실행 실패·정상 CSV", "error", row, 1),
        ("missing", "CSV 파일 없음", "success", None, 1),
        ("slow", "지연 응답 A", "success", row, 1),
    )
    records: dict[str, Job] = {}
    release = Event()
    for key, label, status, body, count in cases:
        path = directory / f"{key}.csv"
        if body is not None:
            path.write_text(header + body, encoding="utf-8")
        records[key] = Job(
            job_id=key, available=True, status=status, csv_path=str(path),
            csv_exists=body is not None, spec=Spec(timeframe="min", buy=label, sell="합성 입력"),
            metrics=Metrics(trade_count=count),
        )

    class Manager:
        def get(self, job_id: str, log_tail: int = 0) -> Job:
            return records[job_id]

    trade_contract_api.get_job_manager = Manager
    backtest_api.get_job_manager = Manager
    backtest_api.REPO_ROOT = directory
    app = FastAPI()
    app.include_router(trade_contract_api.trade_contract_router, prefix="/bt/trade-path")
    app.mount("/ui", StaticFiles(directory=ROOT / "ai_strategy_loop/dashboard/frontend"))

    @app.get("/bt/result")
    def result(job_id: str) -> JSONResponse:
        return JSONResponse(backtest_api.get_result(job_id=job_id))

    @app.get("/bt/analysis/montecarlo")
    def no_research() -> JSONResponse:
        return JSONResponse({"montecarlo": None, "reason": "fixture_does_not_execute_research"})

    @app.get("/bt/jobs")
    def jobs() -> Jobs:
        return Jobs(jobs=list(records.values()))

    @app.get("/bt/trade-path/lane-manifest")
    def manifest() -> Flag:
        return Flag(available=False)

    @app.get("/bt/trade-path/preflight")
    def preflight(job_id: str) -> Preflight:
        if job_id == "slow":
            release.wait(timeout=45)
        return Preflight(
            available=True, forced_liquidation_time=93000,
            source=records[job_id]["spec"], trade_count=records[job_id]["metrics"]["trade_count"],
            date_count=1, covered_date_count=1,
        )

    @app.get("/fixture/release")
    def release_response() -> Flag:
        release.set()
        return Flag(available=True)

    @app.get("/", response_class=HTMLResponse)
    def page() -> str:
        return """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SQ01 합성 CSV 품질 QA</title>
<link rel="stylesheet" href="/ui/styles.css"><link rel="stylesheet" href="/ui/v4.css">
<link rel="stylesheet" href="/ui/trade-path.css">
<script src="/ui/vendor-react.js"></script><script src="/ui/vendor-react-dom.js"></script>
<script type="module" src="/ui/bundle/stom-ui.js"></script>
<script>window.__STOM_NO_AUTO_MOUNT__=true;</script></head>
<body style="padding:20px;background:var(--bg-0);color:var(--ink-1)">
<h1>SQ01 합성 입력 검증</h1><p>실제 생산 컴포넌트·데이터 계약 API / 시장 연구·주문 없음</p>
<button onclick="fetch('/fixture/release')">대기 응답 해제</button><main id="root"></main>
<script defer src="/ui/bundle/app.js"></script><script>
document.addEventListener('DOMContentLoaded', function () {
ReactDOM.createRoot(document.getElementById('root')).render(
 React.createElement(window.BtTradePathTab,{baseUrl:location.origin}));
});
</script></body></html>"""

    @app.get("/result-view", response_class=HTMLResponse)
    def result_page() -> str:
        return page().replace(
            "window.BtTradePathTab,{baseUrl:location.origin}",
            "window.BtResultArea,{baseUrl:location.origin,jobId:new URLSearchParams(location.search).get('job')||'normal'}",
        )

    return app


if __name__ == "__main__":
    with TemporaryDirectory(prefix="stom-sq01-ui-") as temporary:
        uvicorn.run(make_app(Path(temporary)), host="127.0.0.1", port=18765)
