"""P2b-2 — 가정(Hypothesis) 루프 대시보드 가시화 검증.

백엔드: to_loop_state가 generations.hypotheses_json(유효 JSON 리스트)을
GenerationInfo.hypotheses로 파싱하고, NULL/빈/깨진 JSON/리스트 아님 → []로 폴백하는지
(하위호환). GenerationInfo 기본 [] 하위호환.

프론트: 빌드 없는 브라우저 JSX라 정적 read로 HypothesisPanel/verdict 뱃지 문자열 존재만
회귀 가드(phase_mapping 테스트 패턴과 동일).
"""

import json
from pathlib import Path

from ai_strategy_loop.controller import contract as C
from ai_strategy_loop.controller.state import to_loop_state

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND = PROJECT_ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _gen_row(gen_no: int, hypotheses_json=None) -> dict:
    """to_loop_state가 받는 generations 행(dict) 최소 형태."""
    return {
        "gen_no": gen_no,
        "status": "ok",
        "score": 1.0,
        "gate_passed": False,
        "reason": "",
        "trade_count": 10,
        "hypotheses_json": hypotheses_json,
    }


def _valid_hyps_json() -> str:
    return json.dumps([
        {
            "side": "sell", "text": "매도 손절 강화로 MDD 감소 기대",
            "target_metric": "mdd", "expected_direction": -1,
            "source": "gate_mdd", "basis": "MDD 18>cap 12",
            "verdict": "rejected", "observed_delta": 2.5,
        },
        {
            "side": "buy", "text": "진입 완화로 일평균 거래 증가 기대",
            "target_metric": "daily_avg_trades", "expected_direction": 1,
            "source": "gate_trades", "basis": "5<10",
            "verdict": "accepted", "observed_delta": 1.3,
        },
    ])


class TestGenerationInfoHypothesesField:
    """GenerationInfo.hypotheses 기본값/하위호환."""

    def test_default_is_empty_list(self):
        # 이 필드를 발행하지 않던 구 상태(state)도 그대로 검증 통과(기본 []).
        gi = C.GenerationInfo(gen_no=0)
        assert gi.hypotheses == []

    def test_accepts_list_of_dicts(self):
        gi = C.GenerationInfo(gen_no=1, hypotheses=[{"text": "x", "verdict": "accepted"}])
        assert gi.hypotheses == [{"text": "x", "verdict": "accepted"}]


class TestToLoopStateHypothesesParse:
    """to_loop_state가 hypotheses_json을 파싱/폴백하는지."""

    def test_valid_json_list_parsed(self):
        rows = [_gen_row(0, _valid_hyps_json())]
        ls = to_loop_state({"run_id": "r"}, rows)
        hyps = ls.generations[0].hypotheses
        assert len(hyps) == 2
        assert hyps[0]["verdict"] == "rejected"
        assert hyps[0]["target_metric"] == "mdd"
        assert hyps[1]["verdict"] == "accepted"

    def test_null_falls_back_to_empty(self):
        rows = [_gen_row(0, None)]
        ls = to_loop_state({"run_id": "r"}, rows)
        assert ls.generations[0].hypotheses == []

    def test_missing_key_falls_back_to_empty(self):
        # hypotheses_json 키 자체가 없는 구 DB 행(컬럼 없음).
        row = {"gen_no": 0, "status": "ok", "score": 1.0}
        ls = to_loop_state({"run_id": "r"}, [row])
        assert ls.generations[0].hypotheses == []

    def test_empty_string_falls_back_to_empty(self):
        rows = [_gen_row(0, "")]
        ls = to_loop_state({"run_id": "r"}, rows)
        assert ls.generations[0].hypotheses == []

    def test_broken_json_falls_back_to_empty(self):
        rows = [_gen_row(0, "{not valid json")]
        ls = to_loop_state({"run_id": "r"}, rows)
        assert ls.generations[0].hypotheses == []

    def test_non_list_json_falls_back_to_empty(self):
        # 유효 JSON이지만 리스트가 아님(dict) → [] (방어).
        rows = [_gen_row(0, json.dumps({"a": 1}))]
        ls = to_loop_state({"run_id": "r"}, rows)
        assert ls.generations[0].hypotheses == []


class TestHypothesisPanelFrontend:
    """프론트 정적 회귀 가드(빌드 없음)."""

    def test_panel_defined_and_exposed(self):
        src = (FRONTEND / "hypothesis.jsx").read_text(encoding="utf-8")
        assert "function HypothesisPanel(" in src
        tail = src[src.rfind("Object.assign(window"):]
        assert "HypothesisPanel" in tail

    def test_panel_renders_verdict_badges(self):
        src = (FRONTEND / "hypothesis.jsx").read_text(encoding="utf-8")
        # 4종 verdict 라벨 매핑 존재(accepted/rejected/inconclusive/untested).
        for verdict in ("accepted", "rejected", "inconclusive", "untested"):
            assert verdict in src, f"verdict {verdict} 매핑 누락"
        # 색 토큰은 var(--...)만 사용.
        assert "var(--teal)" in src
        assert "var(--red)" in src
        assert "var(--ink-3)" in src

    def test_panel_consumes_hypotheses(self):
        src = (FRONTEND / "hypothesis.jsx").read_text(encoding="utf-8")
        assert "hypotheses" in src
        # 가정 dict 핵심 필드 참조.
        assert "verdict" in src
        assert "target_metric" in src
        assert "expected_direction" in src

    def test_html_loads_jsx_before_app(self):
        # 신규 jsx가 HTML 로드 순서상 app.jsx보다 먼저여야 한다(전역 공유).
        for html_name in ("STOM AI Dashboard.html", "index.html"):
            html = (FRONTEND / html_name).read_text(encoding="utf-8")
            hyp_idx = html.find("hypothesis.jsx")
            app_idx = html.find("app.jsx")
            assert hyp_idx != -1, f"{html_name}에 hypothesis.jsx 스크립트 누락"
            assert app_idx != -1
            assert hyp_idx < app_idx, f"{html_name}: hypothesis.jsx가 app.jsx보다 늦게 로드됨"

    def test_app_wires_hypothesis_panel(self):
        src = (FRONTEND / "app.jsx").read_text(encoding="utf-8")
        assert "<HypothesisPanel state={state}" in src
