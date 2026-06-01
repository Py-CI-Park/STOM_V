"""명예의 전당 — GET /hall_of_fame 백엔드 + 프론트 구조 단위 테스트.

검증:
  백엔드:
    - reference_strategies.json 로드 → 인간 벤치마크 19개(kind='human').
    - AI 산식: profit/total_profit_pct로 운영금 역산, 연평균 window 산출, 단기 플래그.
    - gate 미통과 / 적자(profit<=0) / total_profit_pct<=0 세대는 AI에서 제외.
    - JSON/DB 없음 → 빈 목록(무예외). 라우트 무예외(200).
    - graded(score) 내림차순 상위 ai_limit 정렬.
  프론트(빌드 없는 정적 가드):
    - HallOfFamePanel 정의·window 등록·app.jsx 마운트·'명예의 전당' 제목·human/ai 구분.

실DB/백테 미사용: tmp SQLite + TestClient + reference_strategies.json만 쓴다.
"""

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

FRONTEND = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"


def _read_front(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


@pytest.fixture
def client(monkeypatch, tmp_path):
    """대시보드 TestClient. state 파일을 tmp 격리."""
    from fastapi.testclient import TestClient
    from ai_strategy_loop.dashboard.app import create_app

    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    return TestClient(create_app())


@pytest.fixture
def seeded_hof_db(monkeypatch, tmp_path):
    """tmp loop_runs.db에 다양한 세대(흑자·적자·gate미통과·단기창)를 심는다."""
    db = tmp_path / "loop_runs.db"
    snaps = tmp_path / "snaps"
    monkeypatch.setattr(S, "LOOP_RUNS_DB", db)

    st = LoopState(db_path=str(db), snapshot_dir=str(snaps))

    # runA: 1년 창(2025-01-01 ~ 2025-12-31) → window≈0.997년 (연평균≈total_pct).
    cfg_year = LoopConfig(bt_full_start=20250101, bt_full_end=20251231)
    st.start_run(cfg_year, run_id="runA")
    # gen0 — 흑자·gate 통과. profit=8_000_000, total_pct=80.0 → 운영금=10_000_000.
    st.record_generation(
        "runA", 0,
        buy_name="AILOOP_runA_g0_buy", sell_name="AILOOP_runA_g0_sell",
        status="ok", score=2.77, gate_passed=True, reason="ok",
        trade_count=105, daily_avg_trades=2.5, mdd=17.76, profit=8_000_000.0,
        total_profit_pct=80.0, calmar=3.19, payoff_ratio=1.8, max_hold_count=3.0,
        csv_path="x.csv",
    )
    # gen1 — gate 미통과(제외 대상). 흑자지만 gate_passed=False.
    st.record_generation(
        "runA", 1,
        buy_name="AILOOP_runA_g1_buy", sell_name="AILOOP_runA_g1_sell",
        status="ok", score=0.4, gate_passed=False, reason="점수 미달",
        trade_count=10, daily_avg_trades=0.2, mdd=15.0, profit=500_000.0,
        total_profit_pct=5.0,
    )
    # gen2 — 적자(제외 대상). gate 통과지만 profit<=0.
    st.record_generation(
        "runA", 2,
        buy_name="AILOOP_runA_g2_buy", sell_name="AILOOP_runA_g2_sell",
        status="ok", score=1.0, gate_passed=True, reason="ok",
        trade_count=20, daily_avg_trades=1.0, mdd=40.0, profit=-1_000_000.0,
        total_profit_pct=-10.0,
    )
    # gen3 — total_profit_pct<=0(제외 대상). profit>0이나 수익률<=0(운영금 역산 불가).
    st.record_generation(
        "runA", 3,
        buy_name="AILOOP_runA_g3_buy", sell_name="AILOOP_runA_g3_sell",
        status="ok", score=0.9, gate_passed=True, reason="ok",
        trade_count=15, daily_avg_trades=0.8, mdd=12.0, profit=100_000.0,
        total_profit_pct=0.0,
    )

    # runB: 1개월 창(2025-01-01 ~ 2025-01-31) → window<0.25 → annual_unreliable.
    cfg_short = LoopConfig(bt_full_start=20250101, bt_full_end=20250131)
    st.start_run(cfg_short, run_id="runB")
    # gen0 — 흑자·gate 통과·짧은 창. profit=790_121, total_pct=10.0 → 운영금=7_901_210.
    st.record_generation(
        "runB", 0,
        buy_name="AILOOP_runB_g0_buy", sell_name="AILOOP_runB_g0_sell",
        status="ok", score=1.5, gate_passed=True, reason="ok",
        trade_count=49, daily_avg_trades=4.9, mdd=5.12, profit=790_121.0,
        total_profit_pct=10.0, payoff_ratio=1.4, max_hold_count=2.7,
        csv_path="y.csv",
    )
    st.close()
    return {"db": db}


# =====================================================================
# 1) 인간 벤치마크 — reference_strategies.json 로드(19개).
# =====================================================================
class TestHumanBenchmark:
    def test_human_count_19(self, client):
        resp = client.get("/hall_of_fame")
        assert resp.status_code == 200
        body = resp.json()
        assert "human" in body and "ai" in body
        assert len(body["human"]) == 19

    def test_human_fields_mapped(self, client):
        body = client.get("/hall_of_fame").json()
        h = body["human"][0]
        assert h["kind"] == "human"
        # 공통 스키마 필드 매핑(profit_krw→total_return_krw 등).
        for key in ("label", "total_return_krw", "total_return_pct",
                    "annual_return_pct", "mdd_pct", "payoff", "trades",
                    "daily_avg_trades", "max_holdings", "operating_capital_krw"):
            assert key in h
        # #1 전략 알려진 값(reference_strategies.json) 정합.
        s1 = next(x for x in body["human"] if x["label"] == "#1")
        assert s1["total_return_krw"] == 305178048
        assert s1["operating_capital_krw"] == 120000000

    def test_human_period_and_days(self, client):
        """인간 행에 백테 기간(period 문자열)과 days(거래일수)가 들어간다."""
        body = client.get("/hall_of_fame").json()
        s1 = next(x for x in body["human"] if x["label"] == "#1")
        # reference_strategies.json의 period/days 그대로 매핑.
        assert s1["period"] == "2022-03-31 ~ 2023-03-31"
        assert s1["days"] == 249


# =====================================================================
# 2) AI 산식 — 운영금 역산 + 연평균 + 단기 플래그 + 제외 규칙.
# =====================================================================
class TestAiFormula:
    def test_only_gate_passed_profitable_included(self, client, seeded_hof_db):
        """gate 통과 + profit>0 + total_pct>0 인 세대만 AI에 포함된다."""
        body = client.get("/hall_of_fame").json()
        labels = {a["label"] for a in body["ai"]}
        assert "runA/g0" in labels   # 흑자·gate 통과 → 포함
        assert "runB/g0" in labels   # 흑자·gate 통과·단기창 → 포함
        assert "runA/g1" not in labels  # gate 미통과 → 제외
        assert "runA/g2" not in labels  # 적자 → 제외
        assert "runA/g3" not in labels  # total_pct<=0 → 제외
        assert len(body["ai"]) == 2

    def test_operating_capital_reverse_engineered(self, client, seeded_hof_db):
        """운영금 = profit / total_profit_pct × 100."""
        body = client.get("/hall_of_fame").json()
        by = {a["label"]: a for a in body["ai"]}
        # runA/g0: 8_000_000 / 80.0 × 100 = 10_000_000.
        assert by["runA/g0"]["operating_capital_krw"] == pytest.approx(10_000_000.0)
        # runB/g0: 790_121 / 10.0 × 100 = 7_901_210.
        assert by["runB/g0"]["operating_capital_krw"] == pytest.approx(7_901_210.0)

    def test_total_return_fields(self, client, seeded_hof_db):
        body = client.get("/hall_of_fame").json()
        by = {a["label"]: a for a in body["ai"]}
        assert by["runA/g0"]["total_return_krw"] == pytest.approx(8_000_000.0)
        assert by["runA/g0"]["total_return_pct"] == pytest.approx(80.0)
        assert by["runA/g0"]["kind"] == "ai"
        assert by["runA/g0"]["run_id"] == "runA"
        assert by["runA/g0"]["gen_no"] == 0

    def test_annual_return_simple_division(self, client, seeded_hof_db):
        """연평균 = total_return_pct / window_years (단리). runA window≈0.997."""
        body = client.get("/hall_of_fame").json()
        by = {a["label"]: a for a in body["ai"]}
        # window = (2025-12-31 − 2025-01-01).days/365.25 = 364/365.25 ≈ 0.99658.
        expected = 80.0 / (364 / 365.25)
        assert by["runA/g0"]["annual_return_pct"] == pytest.approx(expected, rel=1e-6)
        assert by["runA/g0"]["annual_unreliable"] is False

    def test_short_window_flagged_unreliable(self, client, seeded_hof_db):
        """1개월 창(window<0.25)은 annual_unreliable=True (과대 환산 경고)."""
        body = client.get("/hall_of_fame").json()
        by = {a["label"]: a for a in body["ai"]}
        assert by["runB/g0"]["annual_unreliable"] is True
        # 연평균은 그대로 계산된다(회색 표기 + 단기 라벨은 프론트 책임).
        assert isinstance(by["runB/g0"]["annual_return_pct"], (int, float))

    def test_ai_quality_fields_present(self, client, seeded_hof_db):
        body = client.get("/hall_of_fame").json()
        by = {a["label"]: a for a in body["ai"]}
        g0 = by["runA/g0"]
        assert g0["mdd_pct"] == pytest.approx(17.76)
        assert g0["calmar"] == pytest.approx(3.19)
        assert g0["payoff"] == pytest.approx(1.8)
        assert g0["trades"] == 105
        assert g0["daily_avg_trades"] == pytest.approx(2.5)
        assert g0["max_hold_count"] == pytest.approx(3.0)

    def test_ai_sorted_by_score_desc(self, client, seeded_hof_db):
        """AI는 graded(score) 내림차순. runA/g0(2.77) > runB/g0(1.5)."""
        body = client.get("/hall_of_fame").json()
        labels = [a["label"] for a in body["ai"]]
        assert labels.index("runA/g0") < labels.index("runB/g0")

    def test_ai_period_from_config_window(self, client, seeded_hof_db):
        """AI 행의 period는 run config_json의 bt_full_start/end를 ISO 기간 문자열로 포맷한다."""
        body = client.get("/hall_of_fame").json()
        by = {a["label"]: a for a in body["ai"]}
        # runA: 2025-01-01 ~ 2025-12-31 창.
        assert by["runA/g0"]["period"] == "2025-01-01 ~ 2025-12-31"
        # runB: 1개월 창.
        assert by["runB/g0"]["period"] == "2025-01-01 ~ 2025-01-31"


# =====================================================================
# 3) 무예외 계약 — DB 없음 / 라우트.
# =====================================================================
class TestNoExcept:
    def test_no_db_returns_human_only(self, client, monkeypatch, tmp_path):
        """loop_runs.db 없을 때 AI는 빈 목록, 인간은 정상(무예외)."""
        monkeypatch.setattr(S, "LOOP_RUNS_DB", tmp_path / "nonexistent.db")
        resp = client.get("/hall_of_fame")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ai"] == []
        assert len(body["human"]) == 19

    def test_payload_direct_no_db(self, monkeypatch, tmp_path):
        """_hall_of_fame_payload 직접 호출 — DB 없어도 무예외."""
        from ai_strategy_loop.dashboard import app as A
        monkeypatch.setattr(S, "LOOP_RUNS_DB", tmp_path / "none.db")
        out = A._hall_of_fame_payload()
        assert isinstance(out, dict)
        assert out["ai"] == []
        assert len(out["human"]) == 19

    def test_missing_reference_json_empty_human(self, client, monkeypatch):
        """reference_strategies.json 부재 → human 빈 목록(무예외)."""
        from ai_strategy_loop.dashboard import app as A
        monkeypatch.setattr(A, "_REFERENCE_STRATEGIES_JSON", "/no/such/reference.json")
        resp = client.get("/hall_of_fame")
        assert resp.status_code == 200
        assert resp.json()["human"] == []

    def test_window_helper_robust(self):
        """_window_years_from_config — 잘못된 입력은 None(무예외)."""
        from ai_strategy_loop.dashboard.app import _window_years_from_config
        assert _window_years_from_config(None) is None
        assert _window_years_from_config("not json") is None
        assert _window_years_from_config("{}") is None
        # 정상: 1년 창 ≈ 0.9966.
        wy = _window_years_from_config('{"bt_full_start": 20250101, "bt_full_end": 20251231}')
        assert wy == pytest.approx(364 / 365.25, rel=1e-6)
        # end<=start → None.
        assert _window_years_from_config('{"bt_full_start": 20251231, "bt_full_end": 20250101}') is None

    def test_period_helper_robust(self):
        """_period_string_from_config — 잘못된 입력은 None, 정상은 ISO 기간 문자열(무예외)."""
        from ai_strategy_loop.dashboard.app import _period_string_from_config
        assert _period_string_from_config(None) is None
        assert _period_string_from_config("not json") is None
        assert _period_string_from_config("{}") is None
        # 정상: 3년 창.
        ps = _period_string_from_config('{"bt_full_start": 20230101, "bt_full_end": 20251231}')
        assert ps == "2023-01-01 ~ 2025-12-31"
        # end<=start → None.
        assert _period_string_from_config('{"bt_full_start": 20251231, "bt_full_end": 20230101}') is None
        # 필드 부재 → None.
        assert _period_string_from_config('{"bt_full_start": 20250101}') is None

    def test_ai_limit_caps_results(self, monkeypatch, tmp_path):
        """ai_limit 상위 N개만 반환한다."""
        from ai_strategy_loop.dashboard import app as A
        db = tmp_path / "loop_runs.db"
        snaps = tmp_path / "snaps"
        monkeypatch.setattr(S, "LOOP_RUNS_DB", db)
        st = LoopState(db_path=str(db), snapshot_dir=str(snaps))
        st.start_run(LoopConfig(bt_full_start=20250101, bt_full_end=20251231), run_id="big")
        for i in range(5):
            st.record_generation(
                "big", i, buy_name=f"b{i}", sell_name=f"s{i}",
                status="ok", score=float(i), gate_passed=True,
                trade_count=10, profit=1_000_000.0, total_profit_pct=10.0,
            )
        st.close()
        out = A._hall_of_fame_payload(ai_limit=3)
        assert len(out["ai"]) == 3
        # score 내림차순 상위 3개(4,3,2).
        assert [a["gen_no"] for a in out["ai"]] == [4, 3, 2]


# =====================================================================
# 3b) 인간 결과 스크린샷 — /reference_screenshots 목록 + StaticFiles 마운트.
# =====================================================================
class TestReferenceScreenshots:
    def test_endpoint_lists_png_screenshots(self, client):
        """GET /reference_screenshots — .png 결과 스크린샷 파일명만(보조 크롭/줌 제외)."""
        resp = client.get("/reference_screenshots")
        assert resp.status_code == 200
        body = resp.json()
        assert "screenshots" in body and "count" in body
        files = body["screenshots"]
        assert body["count"] == len(files)
        # 모두 .png 이미지이고 언더스코어 보조 파일(_zoom_*, _crops 등)은 제외.
        assert all(f.lower().endswith(".png") for f in files)
        assert all(not f.startswith("_") for f in files)
        # 결과 스크린샷 디렉토리가 있으면 17장(STOM_Good_Result_Screenshot (1..17).png).
        from ai_strategy_loop.dashboard import app as A
        if os.path.isdir(A._REFERENCE_SCREENSHOTS_DIR):
            assert body["count"] == 17

    def test_screenshots_sorted(self, client):
        """파일명은 정렬되어 반환된다(결정론적 갤러리 순서)."""
        files = client.get("/reference_screenshots").json()["screenshots"]
        assert files == sorted(files)

    def test_screenshots_empty_when_dir_missing(self, client, monkeypatch):
        """디렉토리 부재 → 빈 목록(무예외 계약)."""
        from ai_strategy_loop.dashboard import app as A
        monkeypatch.setattr(A, "_REFERENCE_SCREENSHOTS_DIR", "/no/such/screenshots/dir")
        resp = client.get("/reference_screenshots")
        assert resp.status_code == 200
        assert resp.json() == {"screenshots": [], "count": 0}

    def test_reference_img_mounted_when_dir_exists(self):
        """디렉토리가 있으면 /reference_img StaticFiles 마운트가 import 시 생성된다."""
        import os as _os
        from ai_strategy_loop.dashboard import app as A
        app_obj = A.create_app()
        mount_paths = [r.path for r in app_obj.routes if hasattr(r, "path")]
        if _os.path.isdir(A._REFERENCE_SCREENSHOTS_DIR):
            assert "/reference_img" in mount_paths
        # 디렉토리 유무와 무관하게 앱 생성은 무예외(이 시점까지 도달 = 성공).


# =====================================================================
# 4) 프론트엔드 구조 계약(빌드 없는 정적 검증).
# =====================================================================
class TestFrontendStructure:
    def test_component_defined_in_chart_jsx(self):
        src = _read_front("chart.jsx")
        assert "function HallOfFamePanel(" in src

    def test_component_exposed_on_window(self):
        src = _read_front("chart.jsx")
        tail = src[src.rfind("Object.assign(window"):]
        assert "HallOfFamePanel" in tail

    def test_component_uses_hall_of_fame_endpoint(self):
        src = _read_front("chart.jsx")
        hof = src[src.find("function HallOfFamePanel("):]
        assert "/hall_of_fame" in hof

    def test_component_has_title(self):
        src = _read_front("chart.jsx")
        hof = src[src.find("function HallOfFamePanel("):]
        assert "명예의 전당" in hof

    def test_component_distinguishes_human_and_ai(self):
        src = _read_front("chart.jsx")
        hof = src[src.find("function HallOfFamePanel("):]
        # human/ai 구분(뱃지·필터) + 운영금/연평균 표시.
        assert "인간" in hof and "AI" in hof
        assert "연평균" in hof
        assert "운영금" in hof

    def test_component_has_refresh_mechanism(self):
        src = _read_front("chart.jsx")
        hof = src[src.find("function HallOfFamePanel("):]
        assert "setInterval" in hof
        assert "새로고침" in hof

    def test_component_has_total_return_krw_and_period_columns(self):
        """총수익금(원) 컬럼 유지 + 백테 기간 컬럼 추가."""
        src = _read_front("chart.jsx")
        hof = src[src.find("function HallOfFamePanel("):]
        assert "총수익금(원)" in hof   # 1) 총수익금 표기 유지
        assert "백테 기간" in hof       # 2) 백테 기간 컬럼 추가
        assert "r.period" in hof        # AI/인간 공통 period 필드 렌더

    def test_component_has_short_window_tooltip_and_legend(self):
        """3) AI '단기' 라벨 tooltip + 범례 안내."""
        src = _read_front("chart.jsx")
        hof = src[src.find("function HallOfFamePanel("):]
        # 단기 라벨에 설명 tooltip(data-tip/title) — 연평균 과대추정 경고.
        assert "과대추정" in hof
        # 범례 한 줄 안내.
        assert "단기=연환산 신뢰낮음" in hof

    def test_reference_gallery_defined_and_wired(self):
        """4) 인간 결과 스크린샷 갤러리 — 컴포넌트 정의·엔드포인트·버튼·이미지 경로."""
        src = _read_front("chart.jsx")
        assert "function ReferenceGallery(" in src
        # /reference_screenshots 로 목록 fetch + /reference_img/ 로 이미지 src.
        assert "/reference_screenshots" in src
        assert "/reference_img/" in src
        # 패널 헤더 버튼 + 모달 패턴(modal-bd).
        assert "인간 결과 스크린샷" in src
        assert "modal-bd" in src
        # window 노출(빌드 없는 text/babel 전역 등록).
        tail = src[src.rfind("Object.assign(window"):]
        assert "ReferenceGallery" in tail

    def test_app_jsx_mounts_hall_of_fame_panel(self):
        src = _read_front("app.jsx")
        assert "<HallOfFamePanel" in src

    def test_app_jsx_passes_base_url_and_ws_status(self):
        src = _read_front("app.jsx")
        idx = src.find("<HallOfFamePanel")
        snippet = src[idx: idx + 200]
        assert "baseUrl={baseUrl}" in snippet
        assert "wsStatus={wsStatus}" in snippet
