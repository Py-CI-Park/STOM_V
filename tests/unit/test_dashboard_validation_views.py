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


class TestFreezeVerdict:
    """2026-06-11 — 검증 결산(결정 카드 라이브): 무예외·부분 결과 계약."""

    def test_payload_structure_and_graceful(self, seeded_validation_db):
        from ai_strategy_loop.dashboard.app import _freeze_verdict_payload

        out = _freeze_verdict_payload()  # 증거 파일 일부 부재여도 예외 없이.
        assert isinstance(out.get("lines"), list)
        assert isinstance(out.get("alerts"), list)
        # D2 — PROMOTE 체크리스트: 항상 리스트, 상태값은 4종 중 하나.
        checklist = out.get("promote_checklist")
        assert isinstance(checklist, list) and len(checklist) >= 4
        assert all(c["status"] in ("pass", "warn", "fail", "pending") for c in checklist)


class TestNicheCompare:
    """D3(2026-06-11) — 니치 지도 비교: 자동 발굴·1-D 요약·무예외 계약."""

    def test_discovers_tmap_runs_and_summarizes(self, seeded_validation_db):
        from ai_strategy_loop.dashboard.app import _niche_compare_payload

        db = seeded_validation_db["db"]
        st = LoopState(db_path=str(db), snapshot_dir=str(Path(db).parent / "s3"))
        st.start_run(LoopConfig(), run_id="tmapNiche1")
        rows = [("TMAP __default__", 500_000.0), ("TMAP cap_max=2000", 700_000.0),
                ("TMAP cap_max=2500", 650_000.0)]
        for i, (gist, profit) in enumerate(rows):
            st.record_generation(
                "tmapNiche1", i, buy_name=f"B{i}", sell_name=f"S{i}", status="ok",
                score=1.0, gate_passed=True, reason="ok", trade_count=50,
                mdd=6.0, profit=profit, strategy_gist=gist,
            )
        st.close()

        out = _niche_compare_payload("")  # 자동 발굴 — 'tmap%'만.
        ids = [r["run_id"] for r in out["runs"]]
        assert ids == ["tmapNiche1"]  # runV(비-tmap)는 제외.
        entry = out["runs"][0]
        assert entry["baseline"]["profit"] == 500_000.0
        assert entry["top_slot"]["param"] == "cap_max"
        assert entry["best_profit"] == 700_000.0

    def test_explicit_ids_and_graceful_on_unknown(self, seeded_validation_db):
        from ai_strategy_loop.dashboard.app import _niche_compare_payload

        out = _niche_compare_payload("no_such_run")
        assert out["count"] == 1
        assert out["runs"][0]["gens_ok"] == 0  # 무예외 — 빈 요약.


class TestDecisions:
    """F3/P-D(2026-06-11) — V6 결정 기록: append-only·검증값 거부·이력 순서."""

    def test_record_and_list_roundtrip(self, seeded_validation_db, tmp_path, monkeypatch):
        from fastapi.testclient import TestClient

        import ai_strategy_loop.dashboard.app as A

        monkeypatch.setattr(A, "DECISIONS_FILE", str(tmp_path / "decisions.jsonl"))
        client = TestClient(A.create_app())
        r1 = client.post("/record_decision", json={"verdict": "hold", "note": "검증 추가 대기"})
        assert r1.json()["status"] == "ok"
        r2 = client.post("/record_decision", json={"verdict": "promote", "note": "OOS 통과"})
        assert r2.json()["status"] == "ok"
        hist = client.get("/decisions").json()
        assert hist["count"] == 2
        assert hist["decisions"][0]["verdict"] == "hold"  # append-only 순서 보존.
        assert "ts" in hist["decisions"][0]

    def test_invalid_verdict_rejected(self, tmp_path, monkeypatch):
        import ai_strategy_loop.dashboard.app as A

        monkeypatch.setattr(A, "DECISIONS_FILE", str(tmp_path / "d.jsonl"))
        out = A._record_decision("yolo", "x")
        assert out["status"] == "invalid"
        assert A._decisions_payload()["count"] == 0  # 무효 입력은 기록 안 됨.


class TestOpsStatus:
    """2026-06-11 — 운영 현황 라우트·run 정렬(최신 우선·running 최상단)."""

    def test_running_run_listed_active_with_health(self, seeded_validation_db):
        from ai_strategy_loop.dashboard.app import _ops_status_payload

        out = _ops_status_payload()
        active = {a["run_id"]: a for a in out["active"]}
        assert "runV" in active  # start_run 후 미종료 → running.
        assert active["runV"]["health"] == "active"  # 방금 세대 기록 — 무진행 짧음.
        assert active["runV"]["gens"] == 3
        assert "evidence" in out and "walkforward" in out  # 부분 결과 허용 키.

    def test_runs_payload_recent_and_running_first(self, seeded_validation_db):
        import sqlite3

        from ai_strategy_loop.dashboard.app import _runs_payload

        db = seeded_validation_db["db"]
        st = LoopState(db_path=str(db), snapshot_dir=str(Path(db).parent / "s2"))
        st.start_run(LoopConfig(), run_id="runOld")
        st.finish_run("runOld", status="complete")
        st.close()
        con = sqlite3.connect(str(db))
        con.execute("UPDATE runs SET started_at = started_at - 86400 WHERE run_id='runOld'")
        con.commit()
        con.close()

        ids = [r["run_id"] for r in _runs_payload(None)["runs"]]
        assert ids[0] == "runV"  # running 최상단 + 최신 우선.
        assert ids.index("runV") < ids.index("runOld")


class TestFreezeVerdictOosDiffCi:
    """과업1(2026-06-12) — /freeze_verdict 응답에 oos_diff_ci 키 존재 + 기존 키 불변."""

    def test_oos_diff_ci_key_present_and_existing_keys_intact(self, seeded_validation_db, monkeypatch):
        """OOS run(run_id에 oos_2022·oos_2026 포함)이 있으면 oos_diff_ci 키가 등장한다.

        양쪽 시리즈가 있으면 dict, csv_path 부재면 None — 둘 다 허용(값 None 허용 계약).
        기존 키(lines·alerts·promote_checklist)는 반드시 유지.
        """
        from pathlib import Path

        db = seeded_validation_db["db"]
        # OOS run 2개 심기 — run_id가 oos_2022·oos_2026 패턴을 포함해야 쿼리에 걸린다.
        csv_frozen_2022 = _make_trade_csv(Path(db).parent / "bt_frozen_2022.csv", [
            ("20220103090100", "20220103090300", 1.5, 120000.0),
            ("20220210090100", "20220210090300", 0.8, 60000.0),
        ])
        csv_seed_2022 = _make_trade_csv(Path(db).parent / "bt_seed_2022.csv", [
            ("20220104090100", "20220104090300", 0.5, 40000.0),
            ("20220211090100", "20220211090300", -0.3, -20000.0),
        ])
        st = LoopState(db_path=str(db), snapshot_dir=str(Path(db).parent / "s_oos"))
        st.start_run(LoopConfig(), run_id="cldgen_oos_2022_ci_test")
        st.record_generation(
            "cldgen_oos_2022_ci_test", 0,
            buy_name="SEED_B", sell_name="SEED_S", status="ok",
            score=0.5, gate_passed=True, reason="ok", trade_count=2,
            daily_avg_trades=0.1, mdd=5.0, profit=20000.0,
            payoff_ratio=1.0, csv_path=csv_seed_2022, strategy_gist="BASE_SEED",
        )
        st.record_generation(
            "cldgen_oos_2022_ci_test", 1,
            buy_name="SEED_B", sell_name="SEED_S", status="ok",
            score=0.8, gate_passed=True, reason="ok", trade_count=2,
            daily_avg_trades=0.1, mdd=4.0, profit=180000.0,
            payoff_ratio=1.5, csv_path=csv_frozen_2022, strategy_gist="FROZEN",
        )
        st.close()

        from ai_strategy_loop.dashboard.app import _freeze_verdict_payload

        out = _freeze_verdict_payload()
        # oos_diff_ci 키 존재 — 값이 dict 또는 None 어느 쪽이든 허용(표본 부족 시 None).
        assert "oos_diff_ci" in out, "oos_diff_ci 키가 응답에 없음"
        ci_map = out["oos_diff_ci"]
        assert isinstance(ci_map, dict)
        # 2022 연도 항목이 등장하면 dict 구조를 확인한다.
        if ci_map.get("2022") is not None:
            ci = ci_map["2022"]
            assert "total_diff" in ci
            assert "ci_low" in ci
            assert "ci_high" in ci
            assert "p_diff_le_0" in ci
        # 기존 키 불변.
        assert isinstance(out.get("lines"), list)
        assert isinstance(out.get("alerts"), list)
        assert isinstance(out.get("promote_checklist"), list)

    def test_oos_diff_ci_graceful_without_oos_runs(self, seeded_validation_db):
        """OOS run이 없으면 oos_diff_ci 키 자체가 없거나 빈 dict — 예외 없이 통과."""
        from ai_strategy_loop.dashboard.app import _freeze_verdict_payload

        out = _freeze_verdict_payload()
        # OOS run 없으면 키가 아예 없어도 되고, 있어도 빈 dict면 OK.
        ci_map = out.get("oos_diff_ci", {})
        assert isinstance(ci_map, dict)
        assert isinstance(out.get("lines"), list)


class TestPortfolioSim:
    """과업2(2026-06-12) — /portfolio_sim 엔드포인트 계약."""

    def test_two_runs_returns_portfolio_report(self, seeded_validation_db):
        """ok 세대 csv_path를 가진 run 2개 → combined_total·combined_mdd·diversification_gain."""
        from pathlib import Path

        db = seeded_validation_db["db"]
        # seeded_validation_db 에는 runV가 있고 gen0(csv_seed)·gen1(csv_cand)에 csv_path 있음.
        # 두 번째 run을 추가한다.
        csv_b = _make_trade_csv(Path(db).parent / "bt_runB.csv", [
            ("20230110090100", "20230110090300", 2.0, 200000.0),
            ("20240115090100", "20240115090300", -1.0, -80000.0),
            ("20250120090100", "20250120090300", 1.5, 130000.0),
        ])
        st = LoopState(db_path=str(db), snapshot_dir=str(Path(db).parent / "s_psim"))
        st.start_run(LoopConfig(), run_id="runB")
        st.record_generation(
            "runB", 0, buy_name="B_BUY", sell_name="B_SELL", status="ok",
            score=1.2, gate_passed=True, reason="ok", trade_count=3,
            daily_avg_trades=0.3, mdd=8.0, profit=250000.0,
            payoff_ratio=1.6, csv_path=csv_b, strategy_gist="B_STRAT",
        )
        st.close()

        from ai_strategy_loop.dashboard.app import _portfolio_sim_payload

        out = _portfolio_sim_payload("runV,runB")
        assert "error" not in out, f"예상치 못한 오류: {out.get('error')}"
        assert "combined_total" in out
        assert "combined_mdd" in out
        assert "diversification_gain" in out
        # 상관 행렬 존재 여부 — 날짜 겹침이 충분하면 등장한다(없으면 None 허용).
        assert "correlation" in out

    def test_one_run_returns_error(self, seeded_validation_db):
        """유효 시리즈 1개 → portfolio_report의 error 응답을 200으로 반환한다."""
        from ai_strategy_loop.dashboard.app import _portfolio_sim_payload

        out = _portfolio_sim_payload("runV")
        assert "error" in out

    def test_empty_runs_returns_error(self, seeded_validation_db):
        """빈 파라미터 → error 응답."""
        from ai_strategy_loop.dashboard.app import _portfolio_sim_payload

        out = _portfolio_sim_payload("")
        assert "error" in out

    def test_frontend_has_portfolio_sim_panel(self):
        """결합 시뮬 패널·/portfolio_sim 라우트가 존재한다.

        P5.6 분해: 검증 탭(결합 시뮬 포함) 본문은 rl-validation.jsx 로 이동(research-lab.jsx 는 배럴).
        """
        src = (FRONTEND / "rl-validation.jsx").read_text(encoding="utf-8")
        assert "/portfolio_sim" in src
        assert "결합 시뮬" in src
        assert "combined_total" in src
        assert "diversification_gain" in src


class TestFrontendContract:
    def test_research_lab_has_validation_tab_and_panel(self):
        # P5.6 분해: 탭 정의(RESEARCH_TABS)는 rl-panel.jsx, _ValidationPanel 본문은 rl-validation.jsx.
        src = (FRONTEND / "rl-panel.jsx").read_text(encoding="utf-8") + "\n" + (
            FRONTEND / "rl-validation.jsx"
        ).read_text(encoding="utf-8")
        assert '{ id: "validation", label: "검증" }' in src
        assert "function _ValidationPanel" in src
        assert "/run_yearly?run_id=" in src
        assert "/selector_preview?run_id=" in src
        # 2026-06-11 R2/R3 확장으로 autopsy fetch가 공용 쿼리 변수(q)를 쓴다 —
        #   URL 리터럴 대신 라우트 경로 존재를 계약으로 검증한다.
        assert '"/autopsy"' in src
        assert 'tab === "validation"' in src
        # 2026-06-11 — Ops 패널(운영 현황 10초 폴링) 계약.
        assert "/ops_status" in src
        assert "운영 현황" in src
        assert "정체 의심" in src
        # 2026-06-11 — 검증 결산(결정 카드 라이브) 계약.
        assert "/freeze_verdict" in src
        assert "검증 결산" in src
        # D2/D3(2026-06-11) — PROMOTE 체크리스트·니치 비교 계약.
        assert "promote_checklist" in src
        assert "/niche_compare" in src
        assert "니치 비교" in src
        # 2026-06-11 — 전체 화면 토글·탭 공통 운영 띠 계약.
        assert "전체 화면" in src
        assert "opsStrip" in src
        # E1/E2/E5(2026-06-11) — 전용 lab 페이지·수익곡선·히트맵 토글 계약.
        assert "/equity_curve" in src
        assert "_EquityChart" in src
        # F1/F2/F7/F10(2026-06-11) — 니치 확장열·run 자동완성·탭 경고·WF 표 계약.
        assert "rl-run-options" in src
        assert "동결상관" in src
        assert "기권(시드 유지)" in src
        # Phase9 — 사이드바·연구실 로직은 dashboard-pages.jsx(window.LabPage)로 단일화됐고
        #   lab.html 은 그 전역을 마운트한다. verdict 로직도 window.VerdictPanel 로 이동.
        lab = (FRONTEND / "lab.html").read_text(encoding="utf-8")
        assert "bundle/app.js" in lab  # Phase14.7: research-lab 포함 전 컴포넌트는 번들로 로드
        assert "window.LabPage" in lab
        dp = (FRONTEND / "dashboard-pages.jsx").read_text(encoding="utf-8")
        assert "ResearchLabPanel" in dp
        assert "run 목록" in dp
        assert "/record_decision" in dp
        assert "결정 이력" in dp

    def test_app_jsx_shows_run_label(self):
        src = (FRONTEND / "app.jsx").read_text(encoding="utf-8")
        assert 'r.label ? " · " + r.label : ""' in src
        # Phase4 correction — 연구실/워크벤치/결정/기록은 상단 탭이 아니라 진화 홈 하위 탭이다.
        contract = (FRONTEND / "ui-contract.jsx").read_text(encoding="utf-8")
        assert 'key: "workbench"' in contract and 'key: "records"' in contract and 'key: "verdict"' in contract
        assert 'pro: "workbench"' in contract
        assert 'from "./dashboard-pages.jsx"' in src
        assert "<VerdictPanel" in src and "EvolutionSubtabNav" in src

    def test_phase4_track_a_tabnav_scale_up(self):
        """Phase4 트랙A(2026-06-12) — 전역 UX 스케일 업 계약.

        탭 내비는 styles.css 의 .stom-tabnav/.stom-tab(.stom-tab-active) 클래스로
        대형화·강한 활성 대비를 구동한다(app.jsx 인라인 사이즈 prop 제거). 와이드
        화면(>1800px) 미디어쿼리로 grid-main 확장·폰트 스케일 업을 추가한다.
        """
        app = (FRONTEND / "app.jsx").read_text(encoding="utf-8")
        # 탭바·탭에 신규 클래스가 적용되고 탭 아이콘이 존재한다.
        assert 'className="stom-tabnav"' in app
        assert '"stom-tab" + (active ? " stom-tab-active" : "")' in app
        assert "stom-tab-ico" in app
        css = (FRONTEND / "styles.css").read_text(encoding="utf-8")
        # 대형화(높이 ~48px+·폰트 15px+)와 활성 대비(글로우) 룰이 존재한다.
        assert ".stom-tab {" in css
        assert ".stom-tab-active" in css
        assert "min-height: 48px" in css
        # 와이드 화면 활용 미디어쿼리(>1800px) — grid-main 확장.
        assert "@media (min-width: 1800px)" in css

    def test_index_html_cache_bumped(self):
        src = (FRONTEND / "index.html").read_text(encoding="utf-8")
        # index.html 에 직접 존재하는 자산(벤더/스타일/빌드 번들).
        assert "styles.css?v=20260620g004" in src   # G006/G007: readability/design tokens cache bust.
        assert "vendor-lightweight-charts.js?v=20260612a" in src
        # Phase14.4/14.5: 운영 컴포넌트는 단일 번들 bundle/app.js(+stom-ui.js)로 로드.
        #   ?v= 는 content-hash(자동) — 값은 하드코딩하지 않는다(일관성은 test_p14 가 검증).
        assert "bundle/app.js?v=" in src
        assert "bundle/stom-ui.js?v=" in src
        # 모델-무관 마이그레이션: concat "==== X.jsx ====" 마커 존재 검사 → 각 모듈이 정의하는
        #   심볼 존재로 교체(concat·bundle 양쪽 통과). 정의/로드 텍스트 순서(_ord index 비교)는
        #   모듈 스코프에선 무의미하므로 DROP(런타임 정의-전 의존은 Track Z 하니스가 별도 검증).
        app_bundle = (FRONTEND / "bundle" / "app.js").read_text(encoding="utf-8")
        for sym in (
            "FitnessChart",            # chart.jsx
            "ResearchLabPanel",        # research-lab.jsx
            "EvolutionAnalysisPanel",  # evolution-analysis.jsx
            "LabPage",                 # dashboard-pages.jsx
            "ResearchProPanel",        # research-pro.jsx
            "BtResultArea",            # backtest-charts.jsx
            "BacktestTab",             # backtest.jsx
            "SimLiveChart",            # sim-live-chart.jsx
            "SimCandleChart",          # simulation-charts.jsx
            "SimulationTab",           # simulation.jsx
            "function App(",           # app.jsx (엔트리)
        ):
            assert sym in app_bundle, f"app.js 에 {sym} 누락"


class TestRegimeReport:
    """과업1(2026-06-12) — /regime_report 엔드포인트: 정상(tmp JSON) + 파일 부재."""

    def test_returns_data_when_file_exists(self, tmp_path, monkeypatch):
        import ai_strategy_loop.dashboard.app as A

        regime_data = {
            "THETA": {"active_months": 8, "active_profit": 1200000, "contracted_profit": 800000,
                      "concentration": 0.72},
            "SEED": {"active_months": 6, "active_profit": 900000, "contracted_profit": 600000},
        }
        evidence_dir = tmp_path / ".omo" / "evidence" / "tmap-walkforward"
        evidence_dir.mkdir(parents=True)
        regime_file = evidence_dir / "regime_report_20260612.json"
        regime_file.write_text(__import__("json").dumps(regime_data), encoding="utf-8")

        monkeypatch.setattr(A, "REPO_ROOT", str(tmp_path))
        out = A._regime_report_payload()
        assert "THETA" in out
        assert out["THETA"]["active_profit"] == 1200000

    def test_unavailable_when_no_file(self, tmp_path, monkeypatch):
        import ai_strategy_loop.dashboard.app as A

        monkeypatch.setattr(A, "REPO_ROOT", str(tmp_path))
        out = A._regime_report_payload()
        assert out["status"] == "unavailable"


class TestRevivalRegistry:
    """과업2(2026-06-12) — /revival_registry 엔드포인트: 정상(tmp JSON) + 파일 부재."""

    def test_returns_data_when_file_exists(self, tmp_path, monkeypatch):
        import ai_strategy_loop.dashboard.app as A

        registry_data = {
            "candidates": [
                {"label": "C7_SEEDPLUS", "rejected_at": "2026-06-01", "reject_basis": "mdd>20%"},
                {"label": "C8_TEST", "rejected_at": "2026-06-05", "reject_basis": "profit<0"},
            ]
        }
        evidence_dir = tmp_path / ".omo" / "evidence" / "tmap-walkforward"
        evidence_dir.mkdir(parents=True)
        (evidence_dir / "rejected_registry.json").write_text(
            __import__("json").dumps(registry_data), encoding="utf-8"
        )

        monkeypatch.setattr(A, "REPO_ROOT", str(tmp_path))
        out = A._revival_registry_payload()
        assert isinstance(out["candidates"], list)
        assert len(out["candidates"]) == 2
        assert out["candidates"][0]["label"] == "C7_SEEDPLUS"

    def test_unavailable_when_no_file(self, tmp_path, monkeypatch):
        import ai_strategy_loop.dashboard.app as A

        monkeypatch.setattr(A, "REPO_ROOT", str(tmp_path))
        out = A._revival_registry_payload()
        assert out["status"] == "unavailable"


class TestPipelineStatus:
    """과업3(2026-06-12) — /pipeline_status 엔드포인트: 정상(tmp state.json들) + 디렉토리 없음."""

    def test_returns_items_when_state_files_exist(self, tmp_path, monkeypatch):
        import ai_strategy_loop.dashboard.app as A

        pipeline_dir = tmp_path / ".omo" / "evidence" / "pipeline"
        for prefix, stages in [
            ("run_alpha", {"fetch": True, "backtest": True, "evaluate": False}),
            ("run_beta",  {"fetch": True, "backtest": False, "evaluate": False}),
        ]:
            d = pipeline_dir / prefix
            d.mkdir(parents=True)
            (d / "state.json").write_text(
                __import__("json").dumps(stages), encoding="utf-8"
            )

        monkeypatch.setattr(A, "REPO_ROOT", str(tmp_path))
        out = A._pipeline_status_payload()
        assert out["count"] == 2
        prefixes = {item["prefix"] for item in out["items"]}
        assert "run_alpha" in prefixes
        assert "run_beta" in prefixes
        alpha = next(item for item in out["items"] if item["prefix"] == "run_alpha")
        assert alpha["stages"]["fetch"] is True
        assert alpha["stages"]["evaluate"] is False

    def test_empty_when_no_pipeline_dir(self, tmp_path, monkeypatch):
        import ai_strategy_loop.dashboard.app as A

        monkeypatch.setattr(A, "REPO_ROOT", str(tmp_path))
        out = A._pipeline_status_payload()
        assert out["items"] == []
        assert out["count"] == 0


class TestNewFrontendContract:
    """과업1~3(2026-06-12) — 새 엔드포인트·패널 프런트 계약."""

    def test_verdict_html_has_regime_and_revival_blocks(self):
        # Phase9 — verdict 로직은 dashboard-pages.jsx(window.VerdictPanel)로 이동, verdict.html 은 마운트만.
        src = (FRONTEND / "dashboard-pages.jsx").read_text(encoding="utf-8")
        assert "/regime_report" in src
        assert "레짐 분해 (advisory)" in src
        assert "/revival_registry" in src
        assert "패자부활 레지스트리" in src
        assert "신규 데이터 도착 시 전수 자동 재검증" in src

    def test_research_lab_has_pipeline_checkpoint_panel(self):
        # P5.6 분해: _PipelineCheckpointPanel 정의는 rl-analysis.jsx 로 이동(research-lab.jsx 는 배럴).
        src = (FRONTEND / "rl-analysis.jsx").read_text(encoding="utf-8")
        assert "/pipeline_status" in src
        assert "파이프라인 체크포인트" in src
        assert "_PipelineCheckpointPanel" in src

    def test_lab_html_cache_bumped(self):
        src = (FRONTEND / "lab.html").read_text(encoding="utf-8")
        # Phase14.7: lab.html 은 content-hash 번들 bundle/app.js 로 캐시 버전됨(research-lab 포함).
        assert "bundle/app.js?v=" in src


class TestPortfolioVerdict:
    """V6 채택 추천 포트폴리오(2026-06-13) — /portfolio_verdict 정상·파일 부재 계약."""

    def test_adopted_when_complement_decision_and_m4_exist(self, tmp_path, monkeypatch):
        """decisions.jsonl(complement) + m4_monitor_baseline.json 픽스처 → adopted=true."""
        import json as _json

        import ai_strategy_loop.dashboard.app as A

        # decisions.jsonl 픽스처
        decisions_file = tmp_path / "decisions.jsonl"
        decisions_file.write_text(
            _json.dumps({"ts": 1000.0, "verdict": "complement",
                         "note": "V6 test note", "candidate": None}) + "\n",
            encoding="utf-8",
        )

        # m4_monitor_baseline.json 픽스처
        m4_dir = tmp_path / ".omo" / "evidence" / "tmap-walkforward"
        m4_dir.mkdir(parents=True)
        m4_data = {
            "report": {
                "months": [{"month": "202301", "champion": 100, "challenger": 80}],
                "champion_total": 13000000,
                "challenger_total": 10000000,
                "alerts": [],
            }
        }
        (m4_dir / "m4_monitor_baseline.json").write_text(
            _json.dumps(m4_data), encoding="utf-8"
        )

        monkeypatch.setattr(A, "DECISIONS_FILE", str(decisions_file))
        monkeypatch.setattr(A, "M4_MONITOR_BASELINE_FILE",
                            str(m4_dir / "m4_monitor_baseline.json"))

        out = A._portfolio_verdict_payload()
        assert out["adopted"] is True
        assert isinstance(out["members"], list)
        assert len(out["members"]) == 2
        assert out["members"][0]["name"] == "THETA"
        assert out["members"][1]["name"] == "T2C3"
        assert out["m4"]["champion_total"] == 13000000
        assert out["m4"]["challenger_total"] == 10000000
        assert out["m4"]["n_months"] == 1
        assert isinstance(out["m4"]["alerts"], list)
        assert out["decision_note"] == "V6 test note"
        assert "findings_doc" in out

    def test_unavailable_when_no_files(self, tmp_path, monkeypatch):
        """decisions.jsonl·m4_monitor_baseline.json 모두 없으면 unavailable."""
        import ai_strategy_loop.dashboard.app as A

        monkeypatch.setattr(A, "DECISIONS_FILE", str(tmp_path / "no_decisions.jsonl"))
        monkeypatch.setattr(A, "M4_MONITOR_BASELINE_FILE",
                            str(tmp_path / "no_m4.json"))

        out = A._portfolio_verdict_payload()
        assert out["adopted"] is False
        assert out.get("status") == "unavailable"

    def test_endpoint_returns_200(self, tmp_path, monkeypatch):
        """TestClient로 /portfolio_verdict GET → 200 + adopted 키 존재."""
        import json as _json

        from fastapi.testclient import TestClient

        import ai_strategy_loop.dashboard.app as A

        decisions_file = tmp_path / "d.jsonl"
        decisions_file.write_text(
            _json.dumps({"ts": 1.0, "verdict": "complement", "note": "ok",
                         "candidate": None}) + "\n",
            encoding="utf-8",
        )
        m4_dir = tmp_path / ".omo" / "evidence" / "tmap-walkforward"
        m4_dir.mkdir(parents=True)
        (m4_dir / "m4_monitor_baseline.json").write_text(
            _json.dumps({"report": {"months": [], "champion_total": 1,
                                    "challenger_total": 2, "alerts": []}}),
            encoding="utf-8",
        )
        monkeypatch.setattr(A, "DECISIONS_FILE", str(decisions_file))
        monkeypatch.setattr(A, "M4_MONITOR_BASELINE_FILE",
                            str(m4_dir / "m4_monitor_baseline.json"))

        client = TestClient(A.create_app())
        r = client.get("/portfolio_verdict")
        assert r.status_code == 200
        data = r.json()
        assert "adopted" in data

    def test_verdict_html_has_portfolio_panel(self):
        """V6 포트폴리오 패널 — Phase9 SPA 통합으로 verdict 로직이 dashboard-pages.jsx
        (window.VerdictPanel)로 단일화됐다. 부모 Phase3 의 포트폴리오 패널이 그 안에 포팅돼
        있어야 한다(verdict.html 은 전역 마운트만)."""
        src = (FRONTEND / "dashboard-pages.jsx").read_text(encoding="utf-8")
        assert "/portfolio_verdict" in src
        assert "V6 채택 추천 포트폴리오" in src
        assert "portfolio.adopted" in src
        assert "findings_doc" in src
