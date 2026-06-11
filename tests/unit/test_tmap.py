"""TMAP G1~G5(2026-06-11) — 템플릿·경향성·포트폴리오·전진분석·라우트 테스트.

설계 계약(docs/update_log/2026-06-11_tmap_process_redesign.md):
  - G1: 기본값 렌더 = 원본 시드 구조 보존(슬롯 잔존 0) + 기존 생성 가드 통과.
  - G3: 고원(연속 흑자 구간) > 피크 — 비단조·경로의존 면역의 핵심.
  - G5: 결합 score(profit/MDD금액) 단조 증가 + 상관 상한 준수.
  - G4: 정책 v1 선택 규칙(plateau_score 최고·평균손익>베이스라인·흑자율>=0.5).
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
from ai_strategy_loop.tmap.portfolio import combined_metrics, greedy_portfolio  # noqa: E402
from ai_strategy_loop.tmap.template import (  # noqa: E402
    coordinate_points,
    load_template,
    parse_point_label,
    render,
    strategy_names,
    validate_rendered,
)
from ai_strategy_loop.tmap.resume import resume_done_map, resume_row  # noqa: E402
from ai_strategy_loop.tmap.tendency import (  # noqa: E402
    center_yearly_consistency,
    plateau_metrics,
    summarize_tendency,
)
from ai_strategy_loop.scripts.tmap_walkforward import (  # noqa: E402
    apply_washout,
    parse_windows,
    select_theta,
)


# =====================================================================
# G1 — 템플릿
# =====================================================================
class TestTemplate:
    def test_load_and_defaults_render_restores_seed_literals(self) -> None:
        t = load_template("seed_902905")
        assert len(t.params) == 13
        buy, sell = render(t)  # 기본값
        # 슬롯 잔존 0(완전 렌더).
        assert "{" not in buy and "{" not in sell
        # 원본 시드의 리터럴이 정확히 복원된다(identity의 표본 검증).
        assert "시가총액 < 3000" in buy
        assert "체결강도 >= 50 and 체결강도 <= 300" in buy
        assert "90200 <= 시분초 < 90500" in buy
        assert "수익률 >= 5 or 수익률 <= -5.0" in sell
        assert "최고수익률 > 6 and 최고수익률 * 0.6 >= 수익률" in sell

    def test_defaults_pass_existing_guards(self) -> None:
        t = load_template("seed_902905")
        buy, sell = render(t)
        assert validate_rendered(buy, sell, t.timeframe) == []

    def test_varied_theta_renders_and_passes_guards(self) -> None:
        t = load_template("seed_902905")
        buy, sell = render(t, {"cap_max": 2000, "window_end": 91500, "stop_deep": -1.5})
        assert "시가총액 < 2000" in buy
        assert "90200 <= 시분초 < 91500" in buy
        assert "수익률 <= -1.5" in sell
        assert validate_rendered(buy, sell, t.timeframe) == []

    def test_unknown_param_rejected(self) -> None:
        t = load_template("seed_902905")
        with pytest.raises(KeyError):
            render(t, {"no_such": 1})

    def test_coordinate_points_and_label_roundtrip(self) -> None:
        t = load_template("seed_902905")
        pts = coordinate_points(t)
        assert pts[0]["param"] == "__default__"
        assert len(pts) == 1 + sum(len(p.values) - 1 for p in t.params)
        for p in pts[1:3]:
            name, value = parse_point_label(p["label"])
            assert name == p["param"] and value == pytest.approx(float(p["value"]))
        assert parse_point_label("TMAP __default__") == ("__default__", None)
        assert parse_point_label("not tmap") is None

    def test_strategy_names_ascii(self) -> None:
        t = load_template("seed_902905")
        bn, sn = strategy_names(t, 7)
        assert bn == "TMAP_seed_902905_007_B" and sn == "TMAP_seed_902905_007_S"


# =====================================================================
# G3 — 경향성(고원/절벽)
# =====================================================================
def _pt(value, profit, ok=True):
    return {"value": value, "profit": profit, "mdd": 5.0, "trades": 50,
            "status": "ok" if ok else "error", "ok": ok}


class TestTendency:
    def test_plateau_prefers_wide_positive_run_over_single_peak(self) -> None:
        # 피크(1점 +900) vs 고원(3점 +400대) — 고원이 최장 연속 구간으로 잡혀야 한다.
        curve = [_pt(1, -100), _pt(2, 900), _pt(3, -50),
                 _pt(4, 400), _pt(5, 450), _pt(6, 420), _pt(7, -10)]
        m = plateau_metrics(curve)
        assert m["plateau"]["width"] == 3
        assert m["plateau"]["center_value"] == 5
        assert m["cliff"]["jump"] == 1000  # 1→2 (-100 → 900)가 최대 점프.
        assert m["cliff"]["between"] == [1, 2]

    def test_all_negative_curve_has_no_plateau(self) -> None:
        m = plateau_metrics([_pt(1, -10), _pt(2, -20)])
        assert m["plateau"] is None
        assert m["positive_ratio"] == 0.0

    def test_error_points_break_runs(self) -> None:
        curve = [_pt(1, 100), _pt(2, 100, ok=False), _pt(3, 100), _pt(4, 100)]
        m = plateau_metrics(curve)
        assert m["plateau"]["width"] == 2  # error가 연속을 끊는다.

    def test_summarize_from_seeded_db(self, monkeypatch, tmp_path) -> None:
        db = tmp_path / "loop_runs.db"
        monkeypatch.setattr(S, "LOOP_RUNS_DB", db)
        st = LoopState(db_path=str(db), snapshot_dir=str(tmp_path / "s"))
        st.start_run(LoopConfig(), run_id="sweepT")
        rows = [("TMAP __default__", 500_000.0), ("TMAP cap_max=1500", -50_000.0),
                ("TMAP cap_max=2000", 700_000.0), ("TMAP cap_max=2500", 650_000.0),
                ("TMAP cap_max=4000", 100_000.0), ("not tmap row", 999.0)]
        for i, (gist, profit) in enumerate(rows):
            st.record_generation(
                "sweepT", i, buy_name=f"B{i}", sell_name=f"S{i}", status="ok",
                score=1.0, gate_passed=True, reason="ok", trade_count=50,
                daily_avg_trades=0.2, mdd=6.0, profit=profit, payoff_ratio=1.2,
                strategy_gist=gist,
            )
        st.close()

        out = summarize_tendency("sweepT")
        assert out["baseline"]["profit"] == 500_000.0
        cap = out["params"]["cap_max"]
        assert cap["plateau"]["width"] == 3  # 2000·2500·4000 연속 흑자.
        assert cap["plateau_score"] > 0
        assert "not tmap row" not in str(out["params"].keys())


# =====================================================================
# G5 — 포트폴리오
# =====================================================================
def _series(days_profits):
    return {f"202301{i:02d}": float(p) for i, p in enumerate(days_profits, start=1)}


class TestPortfolio:
    def test_combined_metrics_math(self) -> None:
        m = combined_metrics([_series([100, -50, 200]), _series([50, -50, 100])])
        assert m["profit"] == 350.0
        assert m["mdd_amount"] == 100.0  # 150 -> 50 낙폭.
        assert m["n_days"] == 3

    def test_greedy_prefers_low_correlation_and_monotonic_score(self) -> None:
        base = [100, -80, 120, -60, 140, -40, 110, -70, 130, -50,
                100, -80, 120, -60, 140, -40, 110, -70, 130, -50]
        a = _series(base)
        b = _series([60 - x * 0.8 for x in base])  # 반상관이면서 합은 양수 — 결합 시 MDD 급감.
        c = _series([x * 0.99 for x in base])      # a와 완전 상관 — corr_cap에 걸림.
        out = greedy_portfolio({"A": a, "B": b, "C": c}, max_size=3, corr_cap=0.5,
                               require_positive=True)
        # 첫 선택 = 단독 score(profit/MDD금액) 최고 — B(720/≈52) > A(600/80).
        assert out["selection"][0] == "B"
        assert "A" in out["selection"]          # 반상관 추가 → 결합 score 상승.
        assert "C" not in out["selection"]      # A와 완전 상관 → corr_cap 배제.
        scores = [s["score"] for s in out["steps"]]
        assert all(b2 >= a2 for a2, b2 in zip(scores, scores[1:]))  # 단조 증가.

    def test_negative_candidates_excluded_by_default(self) -> None:
        out = greedy_portfolio({"L": _series([-10] * 10)})
        assert out["selection"] == []


# =====================================================================
# G4 — 전진분석(순수 헬퍼)
# =====================================================================
class TestWalkforward:
    def test_parse_windows(self) -> None:
        w = parse_windows("20230101-20231231:20240101-20240630, 20240101-20241231:20250101-20250630")
        assert len(w) == 2
        assert w[0] == {"fit_start": 20230101, "fit_end": 20231231,
                        "eval_start": 20240101, "eval_end": 20240630}

    def test_select_theta_policy_v1(self) -> None:
        summary = {
            "baseline": {"profit": 500_000.0},
            "params": {
                "good": {"positive_ratio": 0.8, "plateau_score": 3.0,
                         "plateau": {"center_value": 2000, "width": 3,
                                     "mean_profit": 700_000.0}},
                "weak_ratio": {"positive_ratio": 0.4, "plateau_score": 9.0,
                               "plateau": {"center_value": 1, "width": 4,
                                           "mean_profit": 900_000.0}},
                "below_base": {"positive_ratio": 0.9, "plateau_score": 8.0,
                               "plateau": {"center_value": 5, "width": 4,
                                           "mean_profit": 400_000.0}},
            },
        }
        theta, basis = select_theta(summary)
        assert theta == {"good": 2000}
        assert basis["plateau_score"] == 3.0

    def test_select_theta_fallback_to_baseline(self) -> None:
        theta, basis = select_theta({"baseline": {"profit": 1.0}, "params": {}})
        assert theta is None
        assert "fallback" in basis["reason"]

    def test_apply_washout_pushes_adjacent_eval_start(self) -> None:
        """C3/N7 — fit_end 인접 eval_start는 (days+1)일 뒤로, 이미 늦으면 무변경."""
        w = parse_windows("20230101-20231231:20240101-20240630")
        out = apply_washout(w, days=2)
        assert out[0]["eval_start"] == 20240103  # 12/31 + 3일.
        assert out[0]["eval_end"] == 20240630  # 종료는 불변.
        late = parse_windows("20230101-20231231:20240201-20240630")
        assert apply_washout(late, days=2)[0]["eval_start"] == 20240201  # 무변경.
        assert apply_washout(w, days=0) == w  # 기본값 — 기존 동작 보존.

    def test_apply_washout_crosses_month_boundary(self) -> None:
        w = parse_windows("20220101-20220630:20220701-20221231")
        out = apply_washout(w, days=3)
        assert out[0]["eval_start"] == 20220704

    def test_select_theta_rejects_less_bad_loss_on_negative_baseline(self) -> None:
        """N9 회귀 — 적자 베이스라인에서 '덜 나쁜' 적자 고원을 알파로 오인 금지.

        베이스라인 -300만일 때 평균 -50만 고원은 (덜 나쁘지만) 적자다 —
        종전 규칙(mean > base)은 통과시켰다. 교정 후엔 절대 흑자만 적격.
        """
        trap = {
            "baseline": {"profit": -3_000_000.0},
            "params": {
                "less_bad": {"positive_ratio": 0.6, "plateau_score": 5.0,
                             "plateau": {"center_value": 10, "width": 4,
                                         "mean_profit": -500_000.0}},
            },
        }
        theta, basis = select_theta(trap)
        assert theta is None  # 절대 흑자 없음 → 베이스라인 유지.
        assert "fallback" in basis["reason"]

        # 같은 적자 베이스라인이라도 절대 흑자 고원은 적격.
        trap["params"]["truly_positive"] = {
            "positive_ratio": 0.7, "plateau_score": 2.0,
            "plateau": {"center_value": 7, "width": 3, "mean_profit": 400_000.0},
        }
        theta, _ = select_theta(trap)
        assert theta == {"truly_positive": 7}


# =====================================================================
# 라우트 — /tmap_map, /portfolio_preview
# =====================================================================
def _make_trade_csv(path: Path, day_profits) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["종목명", "매수시간", "매도시간", "수익률", "수익금"])
        w.writeheader()
        for i, p in enumerate(day_profits, start=1):
            w.writerow({"종목명": "T", "매수시간": f"202301{i:02d}090100",
                        "매도시간": f"202301{i:02d}090300",
                        "수익률": 1.0 if p > 0 else -0.5, "수익금": p})
    return str(path)


class TestRoutes:
    @pytest.fixture
    def client(self, monkeypatch, tmp_path):
        db = tmp_path / "loop_runs.db"
        monkeypatch.setattr(S, "LOOP_RUNS_DB", db)
        csv_a = _make_trade_csv(tmp_path / "a.csv", [100000, -50000] * 8)
        csv_b = _make_trade_csv(tmp_path / "b.csv", [-40000, 90000] * 8)
        st = LoopState(db_path=str(db), snapshot_dir=str(tmp_path / "s"))
        st.start_run(LoopConfig(), run_id="runP")
        for i, (gist, csvp, profit) in enumerate([
            ("TMAP __default__", csv_a, 400_000.0),
            ("TMAP cap_max=2000", csv_b, 400_000.0),
        ]):
            st.record_generation(
                "runP", i, buy_name=f"B{i}", sell_name=f"S{i}", status="ok",
                score=1.0, gate_passed=True, reason="ok", trade_count=16,
                daily_avg_trades=0.2, mdd=6.0, profit=profit, payoff_ratio=1.2,
                csv_path=csvp, strategy_gist=gist,
            )
        st.close()
        from fastapi.testclient import TestClient
        from ai_strategy_loop.dashboard.app import create_app
        return TestClient(create_app())

    def test_tmap_map_route(self, client) -> None:
        body = client.get("/tmap_map", params={"run_id": "runP"}).json()
        assert body["baseline"]["profit"] == 400_000.0
        assert "cap_max" in body["params"]

    def test_tmap_map_graceful_on_non_sweep_run(self, client) -> None:
        body = client.get("/tmap_map", params={"run_id": "nope"}).json()
        assert body["count"] == 0

    def test_portfolio_preview_route(self, client) -> None:
        body = client.get("/portfolio_preview", params={"run_id": "runP"}).json()
        assert body["status"] == "ok", body
        assert body["combined"]["profit"] > 0
        assert len(body["selection"]) >= 1
        assert "note" in body  # 낙관 편향 공시.

    def test_portfolio_preview_graceful(self, client) -> None:
        assert client.get("/portfolio_preview", params={"run_id": "nope"}).json()["status"] in (
            "no_series", "unavailable",
        )

    def test_tmap_map_compare_param(self, client) -> None:
        """M12 — compare_run_id로 다른 창 지도를 병기(구간 발산 가시화)."""
        body = client.get(
            "/tmap_map", params={"run_id": "runP", "compare_run_id": "runP"}
        ).json()
        assert body["compare"]["run_id"] == "runP"
        assert "cap_max" in body["compare"]["params"]

    def test_portfolio_time_dispersion_gate(self, client) -> None:
        """N6 — 전 후보가 같은 30분 진입 창이면 경고(시간 분산 0 공시)."""
        body = client.get("/portfolio_preview", params={"run_id": "runP"}).json()
        td = body.get("time_dispersion") or {}
        assert td.get("union_bucket_count") == 1  # 픽스처 전 거래가 09:01 진입.
        assert "warning" in td


class TestNewStructureTemplates:
    """C10(M8 exit2)·C12(P4 F07) — 신규 구조 템플릿 로드·가드·니치 계약."""

    def test_exit2_defaults_pass_guards_and_buy_is_fixed(self) -> None:
        t = load_template("seed_902905_exit2")
        buy, sell = render(t)
        assert validate_rendered(buy, sell, t.timeframe) == []
        assert "{" not in buy  # 매수는 시드 기본값 리터럴 고정(변인 통제).
        assert "보유시간 >= 600" in sell  # 시간 청산(신규 구조).
        assert "최고수익률 - 수익률 >= 2.0" in sell  # 절대 격차 트레일(신규 구조).

    def test_f07_covers_post_0905_niche(self) -> None:
        t = load_template("orderflow_f07_ignition")
        buy, sell = render(t)
        assert validate_rendered(buy, sell, t.timeframe) == []
        assert "90500 <= 시분초 < 91500" in buy  # 시드 사각지대(09:05~) 니치.
        assert "등락율각도(60)" in buy  # F07 횡보 감지(유계 윈도우 — 계산예산 안전).
        b2, s2 = render(t, {"window_end": 92500, "burst_min": 8.0})
        assert "시분초 < 92500" in b2
        assert validate_rendered(b2, s2, t.timeframe) == []


class TestYearlyConsistency:
    """P2 — θ* 중심점 연도 일관성(흑자 연도 >= 2). 알파 감쇠 차단 회귀."""

    @staticmethod
    def _yearly_csv(path: Path, year_profits: dict) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["종목명", "매수시간", "매도시간", "수익률", "수익금"])
            w.writeheader()
            for year, profit in year_profits.items():
                w.writerow({"종목명": "T", "매수시간": f"{year}0102090100",
                            "매도시간": f"{year}0102090300",
                            "수익률": 1.0 if profit > 0 else -0.5, "수익금": profit})
        return str(path)

    def test_alpha_decay_pattern_fails(self, tmp_path) -> None:
        # 시드의 실측 패턴 모사: 2023 大흑자가 합산을 가리는 케이스 — 차단돼야 한다.
        csvp = self._yearly_csv(tmp_path / "decay.csv",
                                {2023: 2_000_000, 2024: -100_000, 2025: -500_000})
        curve = [{"value": 9, "csv_path": csvp, "ok": True}]
        out = center_yearly_consistency(curve, 9)
        assert out["passed"] is False
        assert out["positive_years"] == 1
        assert "yearly consistency fail" in out["reason"]

    def test_two_positive_years_pass(self, tmp_path) -> None:
        csvp = self._yearly_csv(tmp_path / "ok.csv",
                                {2023: 900_000, 2024: 400_000, 2025: -100_000})
        out = center_yearly_consistency([{"value": 7, "csv_path": csvp}], 7)
        assert out["passed"] is True
        assert out["years"]["2023"] == 900_000

    def test_graceful_on_missing_csv_or_value(self, tmp_path) -> None:
        assert center_yearly_consistency([{"value": 1, "csv_path": None}], 1) is None
        assert center_yearly_consistency(
            [{"value": 1, "csv_path": str(tmp_path / "nope.csv")}], 1
        ) is None
        assert center_yearly_consistency([{"value": 1, "csv_path": "x"}], 99) is None


class TestResume:
    """--resume 스킵 판정 — W1 본 스윕 gen14 프로세스 중단 사건의 회귀 방지.

    계약: ok 세대만 스킵 후보 / error·누락 세대는 재평가 / 라벨 불일치는
    스킵하지 않는다(템플릿 변경 시 오래된 결과를 새 포인트로 오인 금지).
    """

    def test_done_map_and_skip_rules(self, tmp_path) -> None:
        st = LoopState(db_path=str(tmp_path / "loop_runs.db"),
                       snapshot_dir=str(tmp_path / "s"))
        st.start_run(LoopConfig(), run_id="runR")
        st.record_generation(
            "runR", 0, buy_name="B0", sell_name="S0", status="ok",
            score=1.0, gate_passed=True, reason="ok", profit=100.0,
            mdd=1.0, trade_count=10, strategy_gist="TMAP __default__",
        )
        st.record_generation(
            "runR", 1, buy_name="B1", sell_name="S1", status="error",
            score=0.0, gate_passed=False, reason="backtest failed: child exit 1",
            strategy_gist="TMAP cap_max=1500",
        )
        done = resume_done_map(st, "runR")
        st.close()

        assert set(done) == {0}  # error 세대는 스킵 후보에서 제외 → 자동 재시도.
        assert resume_row(done, 0, "TMAP __default__")["profit"] == 100.0
        assert resume_row(done, 0, "TMAP other=1") is None  # 라벨 불일치 → 재평가.
        assert resume_row(done, 1, "TMAP cap_max=1500") is None
        assert resume_row(done, 2, "TMAP cap_max=2000") is None  # 누락 → 평가.


class TestFrontendContract:
    def test_validation_panel_has_tmap_map(self) -> None:
        frontend = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"
        src = (frontend / "research-lab.jsx").read_text(encoding="utf-8")
        assert "/tmap_map?run_id=" in src
        assert "TMAP 지도" in src
        assert "plateau score" in src
        index = (frontend / "index.html").read_text(encoding="utf-8")
        assert "research-lab.jsx?v=20260611e" in index
