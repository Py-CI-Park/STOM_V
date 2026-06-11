"""C1·M10·M11(2026-06-11) — 플라시보 위치·서킷브레이커 반사실·사이징 advisory 테스트.

공통 계약: 전부 advisory(판정 미사용) / 어떤 실패도 None·빈 결과로 흡수 /
해석·권고 규칙은 사전선언(코드 docstring)과 일치해야 한다.
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.fitness.circuit_breaker import (  # noqa: E402
    daily_stop_counterfactual,
    suggest_daily_stop,
)
from ai_strategy_loop.fitness.placebo_check import placebo_position  # noqa: E402
from ai_strategy_loop.fitness.sizing import sizing_advisory  # noqa: E402


# ── C1 플라시보 위치 ─────────────────────────────────────────────────────
class TestPlaceboPosition:
    def test_candidate_above_all_negative_placebos(self) -> None:
        out = placebo_position(10_000_000, [-9e8, -1.6e9, -2e9, -9.2e8])
        assert out["exceeds_all"] is True
        assert out["percentile"] == 1.0
        assert "진입 신호" in out["interpretation"]

    def test_candidate_inside_distribution_flags_review(self) -> None:
        out = placebo_position(50, [10, 100, 200])
        assert out["exceeds_all"] is False
        assert "재검토" in out["interpretation"]

    def test_too_few_samples_none(self) -> None:
        assert placebo_position(1.0, [1.0, 2.0]) is None


# ── M10 서킷브레이커 반사실 ──────────────────────────────────────────────
def _csv(path: Path, rows) -> str:
    """rows: (매수시간, 수익금)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["종목명", "매수시간", "수익금"])
        w.writeheader()
        for t, p in rows:
            w.writerow({"종목명": "T", "매수시간": t, "수익금": p})
    return str(path)


class TestDailyStop:
    def test_stop_removes_trades_after_nth_loss(self, tmp_path) -> None:
        # 1일차: 손실 2건 도달 후 +500 거래가 제거됨 / 2일차: 트리거 없음.
        p = _csv(tmp_path / "a.csv", [
            ("20230102090100", -100), ("20230102090200", -100), ("20230102090300", 500),
            ("20230103090100", 300), ("20230103090200", -50),
        ])
        out = daily_stop_counterfactual(p, max_daily_losses=2)
        assert out["base_profit"] == 550.0
        assert out["kept_profit"] == 50.0  # -100-100(중단) +300-50.
        assert out["trades_removed"] == 1
        assert out["days_triggered"] == 1

    def test_suggest_returns_only_non_decreasing(self, tmp_path) -> None:
        # 손실 뒤 회복이 큰 패턴 — 중단 규칙이 손익을 깎으므로 제안 없음.
        p = _csv(tmp_path / "b.csv", [
            ("20230102090100", -100), ("20230102090200", -100), ("20230102090300", 900),
        ])
        assert suggest_daily_stop(p, candidates=(2,)) == []
        # 손실 연쇄가 이어지는 패턴 — 중단이 이득이므로 제안됨.
        q = _csv(tmp_path / "c.csv", [
            ("20230102090100", -100), ("20230102090200", -100), ("20230102090300", -300),
            ("20230103090100", 700),
        ])
        sug = suggest_daily_stop(q, candidates=(2,))
        assert len(sug) == 1 and sug[0]["profit_ratio"] > 1.0

    def test_graceful(self, tmp_path) -> None:
        assert daily_stop_counterfactual(str(tmp_path / "no.csv"), 2) is None
        assert daily_stop_counterfactual("x.csv", 0) is None


# ── M11 사이징 advisory ─────────────────────────────────────────────────
class TestSizing:
    def test_downscale_applied_fully(self) -> None:
        out = sizing_advisory({"mdd_p95": 4_000_000}, current_betting=100, max_dd_amount=2_000_000)
        assert out["raw_scale"] == 0.5
        assert out["applied_scale"] == 0.5  # 축소는 그대로.
        assert out["recommended_betting"] == 50.0

    def test_upscale_applied_half_conservatively(self) -> None:
        out = sizing_advisory({"mdd_p95": 1_000_000}, current_betting=100, max_dd_amount=2_000_000)
        assert out["raw_scale"] == 2.0
        assert out["applied_scale"] == 1.5  # 상향분 50%만(슬리피지 비선형 보수성).
        assert out["recommended_betting"] == 150.0

    def test_graceful_on_bad_inputs(self) -> None:
        assert sizing_advisory({}, 100, 1) is None
        assert sizing_advisory({"mdd_p95": 0}, 100, 1) is None
        assert sizing_advisory({"mdd_p95": 10}, 0, 1) is None


# ── M4 챔피언-챌린저 ─────────────────────────────────────────────────────
class TestChampionChallenger:
    def test_decay_and_dominance_alerts(self) -> None:
        from ai_strategy_loop.fitness.champion_challenger import championship_report

        champ = {"20250105": 100.0, "20250205": -50.0, "20250305": -30.0}
        chall = {"20250105": 50.0, "20250205": 20.0, "20250305": 10.0}
        out = championship_report(champ, chall, consecutive_alert=2)
        assert out["max_champion_negative_streak"] == 2
        assert any("champion_decay" in a for a in out["alerts"])
        assert any("challenger_dominance" in a for a in out["alerts"])
        assert out["months"][0]["winner"] == "champion"
        assert out["months"][2]["winner"] == "challenger"

    def test_healthy_champion_no_alerts(self) -> None:
        from ai_strategy_loop.fitness.champion_challenger import championship_report

        champ = {"20250105": 100.0, "20250205": 80.0}
        chall = {"20250105": 10.0, "20250205": 20.0}
        out = championship_report(champ, chall)
        assert out["alerts"] == []

    def test_graceful_on_single_month(self) -> None:
        from ai_strategy_loop.fitness.champion_challenger import championship_report

        assert championship_report({"20250105": 1.0}, {"20250106": 1.0}) is None


# ── M5 다중 시드 발굴 ────────────────────────────────────────────────────
class TestMultiseedPairs:
    def test_top_pairs_excludes_derivatives_and_ranks(self, tmp_path) -> None:
        from ai_strategy_loop.config import LoopConfig
        from ai_strategy_loop.controller.state import LoopState
        from ai_strategy_loop.scripts.gen_multiseed_pairs import top_pairs

        db = tmp_path / "loop_runs.db"
        st = LoopState(db_path=str(db), snapshot_dir=str(tmp_path / "s"))
        st.start_run(LoopConfig(), run_id="hist")
        rows = [
            ("CLDGEN_A_B", "CLDGEN_A_S", "후보A", 5_000_000.0, 100, True),
            ("CLDGEN_B_B", "CLDGEN_B_S", "후보B", 9_000_000.0, 80, True),
            ("THETA_x_B", "THETA_x_S", "THETA cap=1", 99_000_000.0, 100, True),  # 파생물 제외.
            ("CLDGEN_C_B", "CLDGEN_C_S", "후보C", 8_000_000.0, 10, True),  # 거래수 미달.
            ("CLDGEN_D_B", "CLDGEN_D_S", "후보D", 7_000_000.0, 100, False),  # 게이트 탈락.
        ]
        for i, (b, s, gist, profit, trades, gate) in enumerate(rows):
            st.record_generation(
                "hist", i, buy_name=b, sell_name=s, status="ok", score=1.0,
                gate_passed=gate, reason="ok", profit=profit, trade_count=trades,
                strategy_gist=gist,
            )
        st.close()

        out = top_pairs(str(db), top=10, min_trades=30)
        names = [p["buy"] for p in out]
        assert names == ["CLDGEN_B_B", "CLDGEN_A_B"]  # 순위 + 제외 규칙.
        assert out[0]["history_best_profit"] == 9_000_000.0

    def test_graceful_on_missing_db(self, tmp_path) -> None:
        from ai_strategy_loop.scripts.gen_multiseed_pairs import top_pairs

        assert top_pairs(str(tmp_path / "none.db")) == []
