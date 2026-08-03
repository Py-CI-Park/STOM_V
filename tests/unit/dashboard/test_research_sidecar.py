"""P4 sidecar 연구 원장 — 멱등 ingest·복원·rebuild 해시 계약."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from ai_strategy_loop.autopsy.market_path import MarketPathRepository
from ai_strategy_loop.autopsy.trade_episode import EpisodeBuilder
from ai_strategy_loop.autopsy.trade_path_analysis import analyze_trade_paths, source_contract
from ai_strategy_loop.autopsy.trade_path_models import Timeframe
from ai_strategy_loop.dashboard.research_sidecar import ResearchSidecar


def _fixture_analysis(tmp_path: Path, analysis_id: str = "tp-test-1"):
    database_dir = tmp_path / "database"
    database_dir.mkdir(exist_ok=True)
    db = database_dir / "stock_tick_20250102.db"
    if not db.is_file():
        with sqlite3.connect(db) as connection:
            connection.execute(
                'CREATE TABLE "005930" ("index" INTEGER PRIMARY KEY, "현재가" REAL)'
            )
            connection.executemany(
                'INSERT INTO "005930" VALUES (?, ?)',
                [(20250102090000 + i, 1000 - i * 5) for i in range(4)],
            )
        with sqlite3.connect(database_dir / "code_info.db") as connection:
            connection.execute('CREATE TABLE stockinfo ("index" TEXT, "종목명" TEXT)')
            connection.execute('INSERT INTO stockinfo VALUES ("005930", "삼성전자")')
    csv_path = tmp_path / "trades.csv"
    if not csv_path.is_file():
        fields = ["종목명", "매수시간", "매도시간", "보유시간", "매수가", "매도가",
                  "매수금액", "매도금액", "수익률", "수익금", "매도조건", "추가매수시간"]
        with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerow({"종목명": "삼성전자", "매수시간": "20250102090000",
                             "매도시간": "20250102090002", "보유시간": "2", "매수가": "1000",
                             "매도가": "990", "매수금액": "1000000", "매도금액": "988000",
                             "수익률": "-1.2", "수익금": "-12000",
                             "매도조건": "손절", "추가매수시간": "[]"})
    builder = EpisodeBuilder(
        repository=MarketPathRepository(database_dir=database_dir),
        code_info_db=database_dir / "code_info.db",
    )
    source = source_contract(
        run_id="job-1", csv_path=csv_path, timeframe=Timeframe.TICK,
        forced_liquidation_time=90003,
    )
    return analyze_trade_paths(
        analysis_id=analysis_id, source=source, builder=builder,
        decision_horizons=(1,), continuation_horizons=(1,),
    )


def test_same_csv_twice_creates_zero_duplicate_artifacts(tmp_path: Path) -> None:
    sidecar = ResearchSidecar(tmp_path / "sidecar.db")
    first = _fixture_analysis(tmp_path, "tp-a")
    second = _fixture_analysis(tmp_path, "tp-b")

    sidecar.ingest_analysis(first)
    sidecar.ingest_analysis(second)   # 같은 CSV(같은 sha·행수)의 두 번째 분석
    sidecar.ingest_analysis(second)   # 완전 동일 재-ingest

    counts = sidecar.counts()
    assert counts["artifacts"] == 1   # 멱등: 중복 0
    assert counts["analyses"] == 2


def test_analysis_round_trips_identically_after_restart(tmp_path: Path) -> None:
    original = _fixture_analysis(tmp_path)
    ResearchSidecar(tmp_path / "sidecar.db").ingest_analysis(original)

    # "재시작": 새 인스턴스가 같은 파일을 연다.
    restored = ResearchSidecar(tmp_path / "sidecar.db").load_analysis(original.analysis_id)

    assert restored is not None
    assert restored.source == original.source
    assert restored.totals == original.totals
    assert restored.episodes == original.episodes
    assert restored.rows == original.rows
    assert restored.continuation_horizons == original.continuation_horizons


def test_rebuild_hash_is_stable_for_identical_content(tmp_path: Path) -> None:
    analysis = _fixture_analysis(tmp_path)
    a, b = ResearchSidecar(tmp_path / "a.db"), ResearchSidecar(tmp_path / "b.db")
    a.ingest_analysis(analysis)
    b.ingest_analysis(analysis)
    assert a.rebuild_hash() == b.rebuild_hash()
    assert len(a.rebuild_hash()) == 64


def test_coordinator_survives_restart_via_sidecar(tmp_path: Path) -> None:
    from ai_strategy_loop.dashboard.trade_path_jobs import TradePathCoordinator
    from ai_strategy_loop.dashboard.trade_path_ledger import TradePathLedger

    analysis = _fixture_analysis(tmp_path)
    sidecar_path = tmp_path / "sidecar.db"
    ResearchSidecar(sidecar_path).ingest_analysis(analysis)

    fresh = TradePathCoordinator(
        ledger=TradePathLedger(tmp_path / "ledger.jsonl"),
        sidecar=ResearchSidecar(sidecar_path),
    )
    revived = fresh.get(analysis.analysis_id)

    assert revived is not None
    assert revived.status == "success"
    assert revived.result is not None
    assert revived.result.totals == analysis.totals
