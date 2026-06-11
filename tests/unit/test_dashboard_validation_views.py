"""D1/D2/D4/D5(2026-06-10) — 검증 뷰 백엔드·프런트 계약 테스트.

- D1 /run_yearly: per-trade CSV의 연도 분해(거래·손익·승률) — 읽기 전용·무예외.
- D2 /autopsy: 공식 부검(진입/청산) NL 요약 노출 — CSV 없으면 no_csv.
- D4 /selector_preview: 선택기 진단 미리보기(sparse|seed_relative) — 쓰기 없음.
- D5 run 목록 대표 라벨(strategy_gist) 병기.
- 프런트 소스 계약: Validation 탭/패널·라벨 표시·index.html 캐시 버전.

실DB/백테 미사용: tmp SQLite + 합성 CSV만 쓴다(기존 dashboard 테스트 패턴).
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402
from ai_strategy_loop.dashboard.app import (  # noqa: E402
    _attach_run_labels,
    _autopsy_payload,
    _run_yearly_payload,
    _selector_preview_payload,
)

FRONTEND = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"


def _make_trade_csv(path: Path, trades: list) -> str:
    """per-trade CSV(매수시간/매도시간/수익률/수익금)를 만든다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["종목명", "매수시간", "매도시간", "수익률", "수익금"]
        )
        writer.writeheader()
        for buy_time, sell_time, pct, profit in trades:
            writer.writerow({
                "종목명": "테스트", "매수시간": buy_time, "매도시간": sell_time,
                "수익률": pct, "수익금": profit,
            })
    return str(path)


@pytest.fixture
def seeded_validation_db(monkeypatch, tmp_path):
    """tmp loop_runs.db에 BASE_SEED + 후보 2개(통과형/실패형) + error 세대를 심는다."""
    db = tmp_path / "loop_runs.db"
    snaps = tmp_path / "snaps"
    monkeypatch.setattr(S, "LOOP_RUNS_DB", db)

    csv_seed = _make_trade_csv(tmp_path / "bt_seed.csv", [
        ("20230102090100", "20230102090300", 1.0, 100000.0),
        ("20240103090100", "20240103090300", -0.5, -40000.0),
        ("20250104090100", "20250104090300", 2.0, 150000.0),
    ])
    csv_cand = _make_trade_csv(tmp_path / "bt_cand.csv", [
        ("20230105090100", "20230105090200", 1.2, 90000.0),
        ("20240106090100", "20240106090200", 0.8, 60000.0),
        ("20250107090100", "20250107090200", -0.3, -20000.0),
    ])

    st = LoopState(db_path=str(db), snapshot_dir=str(snaps))
    st.start_run(LoopConfig(), run_id="runV")
    st.record_generation(
        "runV", 0, buy_name="SEED_B", sell_name="SEED_S", status="ok",
        score=1.0, gate_passed=True, reason="ok", trade_count=300,
        daily_avg_trades=0.4, mdd=17.0, profit=8_000_000.0,
        payoff_ratio=1.4, csv_path=csv_seed, strategy_gist="BASE_SEED",
    )
    st.record_generation(
        "runV", 1, buy_name="CAND_B", sell_name="CAND_S", status="ok",
        score=1.0, gate_passed=True, reason="ok", trade_count=120,
        daily_avg_trades=0.2, mdd=9.0, profit=1_500_000.0,
        payoff_ratio=1.3, csv_path=csv_cand, strategy_gist="C_TEST",
    )
    st.record_generation(
        "runV", 2, buy_name="BAD_B", sell_name="BAD_S", status="error",
        score=0.0, gate_passed=False,
        reason="backtest failed/timeout: ... (elapsed 337s)",
    )
    st.close()
    return {"db": db, "csv_seed": csv_seed, "csv_cand": csv_cand}


class TestRunYearly:
    def test_yearly_breakdown_per_generation(self, seeded_validation_db):
        p = _run_yearly_payload("runV")
        assert p["run_id"] == "runV"
        assert p["count"] == 3
        g0 = p["generations"][0]
        assert g0["label"] == "BASE_SEED"
        years = {y["year"]: y for y in g0["years"]}
        assert set(years) == {"2023", "2024", "2025"}
        assert years["2023"]["profit"] == 100000.0
        assert years["2024"]["trades"] == 1
        assert years["2024"]["win_rate"] == 0.0
        assert years["2025"]["win_rate"] == 1.0

    def test_error_generation_has_empty_years(self, seeded_validation_db):
        p = _run_yearly_payload("runV")
        assert p["generations"][2]["years"] == []

    def test_missing_run_is_graceful(self, seeded_validation_db):
        p = _run_yearly_payload("no_such_run")
        assert p["generations"] == []
        assert p["count"] == 0


class TestAutopsy:
    def test_no_csv_status(self, seeded_validation_db):
        out = _autopsy_payload("runV", 2)
        assert out["status"] == "no_csv"

    def test_with_csv_returns_summaries_contract(self, seeded_validation_db):
        out = _autopsy_payload("runV", 0)
        assert out["status"] == "ok"
        assert "entry_status" in out and "exit_status" in out
        assert isinstance(out["entry_summary"], str)
        assert isinstance(out["exit_summary"], str)

    def test_missing_gen_is_graceful(self, seeded_validation_db):
        out = _autopsy_payload("runV", 99)
        assert out["status"] == "unavailable"


class TestSelectorPreview:
    def test_sparse_selects_passing_candidate_and_excludes_baseline(self, seeded_validation_db):
        out = _selector_preview_payload("runV", "sparse_positive_v1")
        assert out["selector"] == "sparse_positive_v1"
        assert out["diagnostic_only"] is True
        assert out["selected"] is True
        assert out["selected_candidate"]["gen_no"] == 1
        # BASE_SEED는 후보 풀에서 출처 기준 제외 — eligible/rejected 어디에도 없다.
        gens = {e["gen_no"] for e in out["eligible"]} | {r["gen_no"] for r in out["rejected"]}
        assert 0 not in gens

    def test_seed_relative_uses_baseline_profile(self, seeded_validation_db):
        out = _selector_preview_payload("runV", "seed_relative_v1")
        assert out["selector"] == "seed_relative_v1"
        assert out["seed_profile"] == {"mdd": 17.0, "trade_count": 300}
        assert out["mdd_limit"] == pytest.approx(20.0)  # max(20, 17*1.1=18.7)
        assert out["selected"] is True
        assert out["selected_candidate"]["gen_no"] == 1

    def test_missing_run_is_graceful(self, seeded_validation_db):
        out = _selector_preview_payload("no_such_run", "seed_relative_v1")
        assert out["selected"] is False
        assert out["eligible"] == []


class TestRunLabels:
    def test_attach_run_labels_sets_first_gist(self, seeded_validation_db):
        result = {"runs": [{"run_id": "runV"}, {"run_id": "unknown"}]}
        _attach_run_labels(result)
        assert result["runs"][0]["label"] == "BASE_SEED"
        assert "C_TEST" in result["runs"][0]["labels"]
        assert "label" not in result["runs"][1]

    def test_attach_run_labels_graceful_on_empty(self):
        result = {"runs": []}
        _attach_run_labels(result)  # 예외 없이 통과해야 한다.
        assert result["runs"] == []


class TestFrontendContract:
    def test_research_lab_has_validation_tab_and_panel(self):
        src = (FRONTEND / "research-lab.jsx").read_text(encoding="utf-8")
        assert '{ id: "validation", label: "Validation" }' in src
        assert "function _ValidationPanel" in src
        assert "/run_yearly?run_id=" in src
        assert "/selector_preview?run_id=" in src
        # 2026-06-11 R2/R3 확장으로 autopsy fetch가 공용 쿼리 변수(q)를 쓴다 —
        #   URL 리터럴 대신 라우트 경로 존재를 계약으로 검증한다.
        assert '"/autopsy"' in src
        assert 'tab === "validation"' in src

    def test_app_jsx_shows_run_label(self):
        src = (FRONTEND / "app.jsx").read_text(encoding="utf-8")
        assert 'r.label ? " · " + r.label : ""' in src

    def test_index_html_cache_bumped(self):
        src = (FRONTEND / "index.html").read_text(encoding="utf-8")
        # research-lab.jsx는 2026-06-11 TMAP 지도 추가로 v20260611d로 재범프됐다(M12 비교·P3 형태 열).
        assert "research-lab.jsx?v=20260611d" in src
        assert "app.jsx?v=20260611a" in src
