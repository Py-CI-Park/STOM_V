"""Deterministic, read-only v5.8 dashboard scale performance gate.

The fixture is created beneath a temporary directory and routes are exercised through
``create_app`` and ``TestClient``.  It never opens the runtime evidence or loop DB.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fastapi.testclient import TestClient

from ai_strategy_loop.dashboard import history_api, research_api, research_records
from ai_strategy_loop.dashboard.app import create_app

RUN_COUNT = 1_054
GENERATION_COUNT = 10_728
WIKI_METADATA_ROWS = 1_860
CAMPAIGN_COUNT = 34
HISTORY_COLD_BUDGET_SECONDS = 1.0
HISTORY_WARM_BUDGET_SECONDS = 0.10
WIKI_COLD_BUDGET_SECONDS = 1.0
WIKI_WARM_BUDGET_SECONDS = 0.15
_DOC_INDEX_SCHEMA = "stom-research-doc-index-v1"


class PerformanceGateError(RuntimeError):
    """A measured request or payload violated the v5.8 performance contract."""


def _generation_rows() -> Iterator[tuple[str, int, str, int, float, float, float]]:
    """Yield exactly GENERATION_COUNT deterministic generation rows."""
    remaining_extra = GENERATION_COUNT - (RUN_COUNT * 10)
    for run_number in range(RUN_COUNT):
        count = 11 if run_number < remaining_extra else 10
        run_id = f"scale_run_{run_number:04d}"
        for generation in range(count):
            yield (
                run_id,
                generation,
                "ok",
                int(generation % 2 == 0),
                float(generation),
                float(-generation),
                float(generation + 1),
            )


def build_fixture(root: Path) -> dict[str, Path]:
    """Build only temporary evidence, SQLite, and documentation-index inputs."""
    evidence_root = root / "evidence"
    evidence_root.mkdir(parents=True)
    loop_db = root / "loop_runs.db"
    docs_sidecar = root / "docs" / "generated_reports" / "research_docs_index.json"
    docs_sidecar.parent.mkdir(parents=True)

    with sqlite3.connect(loop_db) as connection:
        connection.executescript(
            """
            CREATE TABLE runs (
                run_id TEXT PRIMARY KEY, started_at REAL, config_json TEXT,
                status TEXT, best_gen INTEGER, best_score REAL, finished_at REAL
            );
            CREATE TABLE generations (
                run_id TEXT, gen_no INTEGER, buy_name TEXT, sell_name TEXT,
                status TEXT, score REAL, calmar REAL, uptrend_r2 REAL,
                gate_passed INTEGER, reason TEXT, csv_path TEXT, trade_count INTEGER,
                mdd REAL, profit REAL, strategy_gist TEXT, created_at REAL,
                PRIMARY KEY (run_id, gen_no)
            );
            """
        )
        connection.executemany(
            "INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (f"scale_run_{number:04d}", float(number), "{}", "finished", 0, 0.0, float(number + 1))
                for number in range(RUN_COUNT)
            ],
        )
        connection.executemany(
            """INSERT INTO generations
            (run_id, gen_no, status, gate_passed, score, mdd, profit)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            _generation_rows(),
        )

    for campaign_number in range(CAMPAIGN_COUNT):
        campaign = f"scale_campaign_{campaign_number:02d}"
        (evidence_root / f"{campaign}.jsonl").write_text(
            json.dumps(
                {
                    "event": "cand", "label": f"candidate_{campaign_number:02d}",
                    "profit": float(campaign_number + 1), "mdd": -1.0,
                    "trades": campaign_number + 1, "gate": True, "ts": 1_700_000_000 + campaign_number,
                },
                sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )

    docs_sidecar.write_text(
        json.dumps(
            {
                "schema_version": _DOC_INDEX_SCHEMA,
                "docs": [
                    {
                        "id": f"docs/research/condition_research/wiki/scale_{number:04d}.md",
                        "title": f"Scale wiki {number:04d}", "category": "wiki",
                        "updated_at": "2026-01-01T00:00:00+00:00", "size": number + 1,
                    }
                    for number in range(WIKI_METADATA_ROWS)
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return {"evidence_root": evidence_root, "loop_db": loop_db, "docs_sidecar": docs_sidecar}
def _validate_fixture(paths: dict[str, Path]) -> None:
    """Prove the temporary inputs have the required scale before timing HTTP paths."""
    with sqlite3.connect(paths["loop_db"]) as connection:
        run_count = connection.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        generation_count = connection.execute("SELECT COUNT(*) FROM generations").fetchone()[0]
    campaign_count = len(list(paths["evidence_root"].glob("*.jsonl")))
    sidecar = json.loads(paths["docs_sidecar"].read_text(encoding="utf-8"))
    wiki_count = len(sidecar.get("docs", [])) if isinstance(sidecar, dict) else 0
    expected = {
        "runs": RUN_COUNT,
        "generations": GENERATION_COUNT,
        "campaigns": CAMPAIGN_COUNT,
        "wiki_metadata_rows": WIKI_METADATA_ROWS,
    }
    actual = {
        "runs": run_count,
        "generations": generation_count,
        "campaigns": campaign_count,
        "wiki_metadata_rows": wiki_count,
    }
    if actual != expected:
        raise PerformanceGateError(f"fixture scale mismatch: {json.dumps(actual, sort_keys=True)}")




def _clear_caches() -> None:
    research_records._RECORD_CACHE.clear()
    history_api._INDEX_CACHE.clear()
    history_api._INDEX_CACHE_PROBE.clear()
    history_api._INDEX_CACHE_CHECKED_AT.clear()
    research_api._DOC_INDEX_CACHE = None
    research_api._DOC_INDEX_CHECKED_AT = 0.0


@contextmanager
def isolated_dashboard_sources(paths: dict[str, Path]) -> Iterator[None]:
    """Temporarily direct the read-only routes at temporary fixture sources."""
    original = (
        research_records.EVIDENCE_ROOT, history_api.EVIDENCE_ROOT, history_api.LOOP_RUNS_DB,
        research_api.REPO_ROOT, research_api._DOC_INDEX_SIDECAR,
    )
    try:
        research_records.EVIDENCE_ROOT = paths["evidence_root"]
        history_api.EVIDENCE_ROOT = paths["evidence_root"]
        history_api.LOOP_RUNS_DB = paths["loop_db"]
        research_api.REPO_ROOT = paths["docs_sidecar"].parents[2]
        research_api._DOC_INDEX_SIDECAR = paths["docs_sidecar"]
        _clear_caches()
        yield
    finally:
        (
            research_records.EVIDENCE_ROOT, history_api.EVIDENCE_ROOT, history_api.LOOP_RUNS_DB,
            research_api.REPO_ROOT, research_api._DOC_INDEX_SIDECAR,
        ) = original
        _clear_caches()


def _request(client: TestClient, path: str) -> tuple[float, dict[str, Any]]:
    started = time.perf_counter()
    response = client.get(path)
    elapsed = time.perf_counter() - started
    if response.status_code != 200:
        raise PerformanceGateError(f"{path} returned HTTP {response.status_code}")
    payload = response.json()
    if not isinstance(payload, dict):
        raise PerformanceGateError(f"{path} returned a non-object payload")
    return elapsed, payload


def _validate_history(payload: dict[str, Any]) -> None:
    if payload.get("total") != RUN_COUNT + CAMPAIGN_COUNT:
        raise PerformanceGateError("history total does not match fixture scale")
    coverage = payload.get("coverage")
    if not isinstance(coverage, dict) or coverage.get("campaign", {}).get("total") != CAMPAIGN_COUNT:
        raise PerformanceGateError("history campaign coverage is incorrect")
    if coverage.get("loop_run", {}).get("total") != RUN_COUNT:
        raise PerformanceGateError("history run coverage is incorrect")
    items = payload.get("items")
    if not isinstance(items, list) or len(items) != 100:
        raise PerformanceGateError("history page payload is not the requested 100 rows")
    if not all(
        isinstance(item, dict) and item.get("source_kind") in {"campaign", "loop_run"}
        for item in items
    ):
        raise PerformanceGateError("history payload has an invalid source kind")


def _validate_wiki(payload: dict[str, Any]) -> None:
    if payload.get("count") != WIKI_METADATA_ROWS or payload.get("total") != WIKI_METADATA_ROWS:
        raise PerformanceGateError("wiki metadata count does not match fixture scale")
    docs = payload.get("docs")
    if not isinstance(docs, list) or len(docs) != WIKI_METADATA_ROWS:
        raise PerformanceGateError("wiki payload does not contain every fixture metadata row")
    if (
        not all(isinstance(doc, dict) and doc.get("category") == "wiki" for doc in docs)
        or not docs[-1].get("id", "").endswith("1859.md")
    ):
        raise PerformanceGateError("wiki payload metadata is incorrect")


def _enforce_budgets(timings: dict[str, float]) -> None:
    budgets = {
        "history_cold_seconds": HISTORY_COLD_BUDGET_SECONDS,
        "history_warm_seconds": HISTORY_WARM_BUDGET_SECONDS,
        "wiki_cold_seconds": WIKI_COLD_BUDGET_SECONDS,
        "wiki_warm_seconds": WIKI_WARM_BUDGET_SECONDS,
    }
    exceeded = {key: {"seconds": timings[key], "budget_seconds": budget} for key, budget in budgets.items() if timings[key] > budget}
    if exceeded:
        raise PerformanceGateError(f"performance budget exceeded: {json.dumps(exceeded, sort_keys=True)}")


def run_gate() -> dict[str, Any]:
    """Execute the real HTTP-path scale check and return structured evidence."""
    with tempfile.TemporaryDirectory(prefix="dashboard-v58-scale-") as temporary:
        paths = build_fixture(Path(temporary))
        _validate_fixture(paths)
        with isolated_dashboard_sources(paths):
            with TestClient(create_app(), base_url="http://127.0.0.1") as client:
                history_cold, history_payload = _request(client, "/history/index?source_kind=all&limit=100")
                _validate_history(history_payload)
                history_warm, warm_history_payload = _request(client, "/history/index?source_kind=all&limit=100")
                _validate_history(warm_history_payload)
                research_api._DOC_INDEX_CACHE = None
                research_api._DOC_INDEX_CHECKED_AT = 0.0
                wiki_cold, wiki_payload = _request(client, "/research_docs")
                _validate_wiki(wiki_payload)
                wiki_warm, warm_wiki_payload = _request(client, "/research_docs")
                _validate_wiki(warm_wiki_payload)
    timings = {
        "history_cold_seconds": history_cold, "history_warm_seconds": history_warm,
        "wiki_cold_seconds": wiki_cold, "wiki_warm_seconds": wiki_warm,
    }
    _enforce_budgets(timings)
    return {
        "gate": "dashboard_v58_scale", "passed": True, "performance_proved": False,
        "fixture": {"runs": RUN_COUNT, "generations": GENERATION_COUNT, "wiki_metadata_rows": WIKI_METADATA_ROWS, "campaigns": CAMPAIGN_COUNT},
        "budgets_seconds": {"history_cold": HISTORY_COLD_BUDGET_SECONDS, "history_warm": HISTORY_WARM_BUDGET_SECONDS, "wiki_cold": WIKI_COLD_BUDGET_SECONDS, "wiki_warm": WIKI_WARM_BUDGET_SECONDS},
        "measurements_seconds": timings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional JSON evidence output path.")
    args = parser.parse_args(argv)
    try:
        evidence = run_gate()
    except Exception as exc:  # fail closed, including fixture/request validation failures.
        evidence = {"gate": "dashboard_v58_scale", "passed": False, "performance_proved": False, "error": str(exc)}
        status = 1
    else:
        status = 0
    encoded = json.dumps(evidence, ensure_ascii=False, sort_keys=True)
    if args.output is not None:
        try:
            args.output.write_text(encoded + "\n", encoding="utf-8")
        except OSError as exc:
            evidence = {
                "gate": "dashboard_v58_scale",
                "passed": False,
                "performance_proved": False,
                "error": f"evidence_write_failed: {exc}",
            }
            encoded = json.dumps(evidence, ensure_ascii=False, sort_keys=True)
            status = 1
    print(encoded)
    return status


if __name__ == "__main__":
    sys.exit(main())
