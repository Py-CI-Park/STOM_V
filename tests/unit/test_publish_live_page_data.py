"""M1 — `_publish_live`가 contract v2 page_data를 운반하는지 단위 테스트.

검증:
  - `_publish_live(..., page_data={...})` 호출 시 발행되는 LoopState에 그 page_data가
    실린다.
  - page_data 무인자(기존 호출부)면 빈 dict로 발행된다(하위호환).
  - 발행은 publish_loop_state를 통하므로, 그 함수를 가로채 발행 페이로드를 검사한다.

네트워크/실DB 미사용: 인메모리 tmp DB에 세대 1개만 기록하고 _publish_live를 직접 호출한다.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import loop as L  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402


def _make_state_with_one_gen(tmp_path):
    """tmp DB에 run 1개 + 세대 1개를 넣은 LoopState(SQLite)를 만든다."""
    st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "snaps"))
    rid = st.start_run(LoopConfig(provider="gpt_auth", max_generations=3), run_id="pdrun")
    st.record_generation(
        rid, 0,
        buy_name="AILOOP_pdrun_g0_buy", sell_name="AILOOP_pdrun_g0_sell",
        status="ok", score=1.2, gate_passed=True, reason="ok",
        trade_count=42, mdd=12.0, profit=150000.0, strategy_gist="gist",
    )
    return st, rid


def test_publish_live_carries_page_data(monkeypatch, tmp_path):
    """page_data를 주면 발행 LoopState.page_data에 그대로 실린다."""
    st, rid = _make_state_with_one_gen(tmp_path)
    captured = {}
    # publish_loop_state를 가로채 발행 객체를 캡처(파일 IO 회피).
    monkeypatch.setattr(L, "publish_loop_state", lambda snapshot: captured.update(snap=snapshot))

    config = LoopConfig(provider="gpt_auth", max_generations=3)
    page_data = {"autopsy": {"segments": [1, 2, 3]}, "meta": {"x": True}}
    L._publish_live(
        st, rid, config,
        status="running", current_gen=0, cumulative_tokens=10,
        phase="채점중", page_data=page_data,
    )
    st.close()

    snap = captured.get("snap")
    assert snap is not None
    assert snap.page_data == page_data
    assert snap.contract_version == 2


def test_publish_live_defaults_page_data_empty(monkeypatch, tmp_path):
    """page_data 무인자(기존 호출부) → 빈 dict로 발행(하위호환)."""
    st, rid = _make_state_with_one_gen(tmp_path)
    captured = {}
    monkeypatch.setattr(L, "publish_loop_state", lambda snapshot: captured.update(snap=snapshot))

    config = LoopConfig(provider="gpt_auth", max_generations=3)
    L._publish_live(
        st, rid, config,
        status="running", current_gen=0, cumulative_tokens=10,
        phase="채점중",
    )
    st.close()

    snap = captured.get("snap")
    assert snap is not None
    assert snap.page_data == {}


def test_publish_live_page_data_survives_json_serialization(monkeypatch, tmp_path):
    """발행 객체가 실제 JSON 직렬화될 때 page_data가 보존되는지(WS 경로 모사)."""
    import json
    from ai_strategy_loop.controller import contract as C

    st, rid = _make_state_with_one_gen(tmp_path)
    captured = {}
    monkeypatch.setattr(L, "publish_loop_state", lambda snapshot: captured.update(snap=snapshot))

    config = LoopConfig(provider="gpt_auth", max_generations=3)
    page_data = {"lineage": {"parent_gen": 0, "diff": "+RSI 필터"}}
    L._publish_live(
        st, rid, config,
        status="running", current_gen=0, cumulative_tokens=10,
        phase="부검 작성", page_data=page_data,
    )
    st.close()

    snap = captured["snap"]
    # current_state.json → WS가 하는 직렬화/역직렬화를 재현.
    revalidated = C.LoopState.model_validate(json.loads(snap.model_dump_json()))
    assert revalidated.page_data == page_data
