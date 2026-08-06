# -*- coding: utf-8 -*-
"""페이지 26 자율 루프 관제 API 계약 테스트.

계약:
  1. 읽기 전용 — 조회가 DB 에 쓰지 않는다(WAL/DDL/파일 변경 없음).
  2. 가설 판정 집계와 적중률(accepted / judged) 산출.
  3. 수정 예산(아이디어당 15회) 초과 표시.
  4. 선택 편의 0.6225%p 차감본을 원값과 함께 제시한다.
  5. 기록이 없어도 예외 없이 available=False 로 정직하게 응답한다.
"""
from __future__ import annotations

import json
import sqlite3

import pytest

from ai_strategy_loop.dashboard import autoloop_api as api

_SCHEMA = """
CREATE TABLE generations (
  run_id TEXT, gen_no INTEGER, parent_gen INTEGER, diff_from_parent TEXT,
  status TEXT, gate_passed INTEGER, reason TEXT, score REAL, trade_count INTEGER,
  mdd REAL, profit REAL, daily_avg_trades REAL, payoff_ratio REAL,
  d_graded REAL, d_mdd REAL, d_profit REAL, d_daily_trades REAL,
  hypotheses_json TEXT, created_at REAL
);
"""


def _hypotheses(*verdicts):
    return json.dumps([
        {"side": "buy", "text": f"가정 {i}", "target_metric": "profit",
         "expected_direction": 1, "source": "gate_profit", "basis": "", "verdict": v}
        for i, v in enumerate(verdicts)
    ])


@pytest.fixture()
def loop_db(tmp_path, monkeypatch):
    path = tmp_path / "loop_runs.db"
    con = sqlite3.connect(path)
    con.executescript(_SCHEMA)
    rows = [
        ("run-A", 1, 0, "매수 1절 추가", "ok", 0, "mdd 30 > cap 25", 0.10, 100,
         30.0, -50000.0, 1.0, 1.2, 0.0, 0.0, 0.0, 0.0, _hypotheses("accepted"), 100.0),
        ("run-A", 2, 1, "손절 -1→-2", "ok", 1, "", 0.42, 120,
         18.0, 240000.0, 1.4, 1.6, 0.32, -12.0, 290000.0, 0.4,
         _hypotheses("accepted", "rejected"), 200.0),
        ("run-B", 1, 0, "시간창 축소", "ok", 0, "trades 3 < 5", 0.05, 30,
         12.0, -8000.0, 0.3, 0.9, 0.0, 0.0, 0.0, 0.0, _hypotheses("inconclusive"), 300.0),
    ]
    con.executemany("INSERT INTO generations VALUES (" + ",".join("?" * 19) + ")", rows)
    con.commit()
    con.close()

    class _ReadOnlyState:
        def __init__(self, *_args, readonly=False, **_kwargs):
            assert readonly is True, "관제 조회는 반드시 읽기 전용이어야 한다"
            self._con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
            self._con.row_factory = sqlite3.Row

    monkeypatch.setattr(api, "LoopState", _ReadOnlyState)
    return path


def test_runs_report_budget(loop_db):
    payload = api.autonomy_runs()
    assert payload["available"] is True
    runs = {row["run_id"]: row for row in payload["runs"]}
    assert runs["run-A"]["generations"] == 2
    assert runs["run-A"]["revision_budget"] == api.REVISION_BUDGET
    assert runs["run-A"]["budget_remaining"] == api.REVISION_BUDGET - 2
    assert runs["run-A"]["over_budget"] is False


def test_generations_aggregate_hypothesis_verdicts(loop_db):
    payload = api.autonomy_generations(run_id="run-A")
    assert payload["available"] is True
    assert [g["gen_no"] for g in payload["generations"]] == [2, 1]   # 최신 우선
    verdicts = payload["hypothesis_verdicts"]
    assert verdicts["accepted"] == 2 and verdicts["rejected"] == 1
    assert payload["hypothesis_hit_rate"] == pytest.approx(2 / 3)
    # 원본 JSON 문자열이 아니라 파싱된 객체로 나간다
    assert isinstance(payload["generations"][0]["hypotheses"], list)
    assert "hypotheses_json" not in payload["generations"][0]


def test_budget_reports_bias_adjusted_value(loop_db):
    payload = api.autonomy_budget(run_id="run-A")
    assert payload["available"] is True
    assert payload["selection_bias_pct"] == pytest.approx(0.6225)
    assert payload["best_generation"]["gen_no"] == 2       # score 최대
    raw = payload["design_per_trade_pct"]
    assert raw is not None
    assert payload["bias_adjusted_pct"] == pytest.approx(raw - 0.6225)


def test_over_budget_flag(tmp_path, monkeypatch):
    path = tmp_path / "loop_runs.db"
    con = sqlite3.connect(path)
    con.executescript(_SCHEMA)
    con.executemany(
        "INSERT INTO generations VALUES (" + ",".join("?" * 19) + ")",
        [("run-C", n, n - 1, "", "ok", 0, "", 0.1, 10, 5.0, 0.0, 0.1, 1.0,
          0.0, 0.0, 0.0, 0.0, None, float(n)) for n in range(1, api.REVISION_BUDGET + 3)],
    )
    con.commit(); con.close()

    class _ReadOnlyState:
        def __init__(self, *_a, readonly=False, **_k):
            assert readonly is True
            self._con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
            self._con.row_factory = sqlite3.Row
    monkeypatch.setattr(api, "LoopState", _ReadOnlyState)

    row = api.autonomy_runs()["runs"][0]
    assert row["over_budget"] is True
    assert row["budget_remaining"] == 0


def test_missing_db_is_honest(monkeypatch):
    def _raise(*_a, **_k):
        raise sqlite3.OperationalError("unable to open database file")
    monkeypatch.setattr(api, "LoopState", _raise)

    assert api.autonomy_runs()["available"] is False
    assert api.autonomy_generations()["available"] is False
    budget = api.autonomy_budget()
    assert budget["available"] is False and budget["reason"] == "no_run_records"
