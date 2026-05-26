"""P3/P4 — loop.py 배선 단위 테스트 (parent diff / live page_data / meta seed).

검증(백테/루프 실행 없음, tmp DB + monkeypatch):
  - _build_parent_diff: 부모 대비 지표 델타 NL 요약(부모 없으면 None).
  - _build_live_page_data: autopsy + lineage(+meta) 를 한 page_data로 합친다.
  - _refresh_meta_insights: 누적 generations에서 meta_insights.json 영속.
  - _load_meta_seed: 영속 파일에서 환류 가이드 로드(없으면 None).
  - page_data 직렬화(contract v2 LoopState round-trip).
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


def _seed_run(st, rid="wrun"):
    st.start_run(LoopConfig(), run_id=rid)
    st.record_generation(rid, 0, buy_name=f"AILOOP_{rid}_g0_buy",
                         sell_name=f"AILOOP_{rid}_g0_sell", status="ok",
                         score=1.0, gate_passed=True, trade_count=40, mdd=15.0, profit=100000.0,
                         strategy_gist="if 체결강도 > 120:")
    st.record_generation(rid, 1, buy_name=f"AILOOP_{rid}_g1_buy",
                         sell_name=f"AILOOP_{rid}_g1_sell", status="ok",
                         score=1.4, gate_passed=True, trade_count=38, mdd=11.0, profit=160000.0,
                         parent_gen=0, diff_from_parent="gen0 대비: graded +0.4",
                         strategy_gist="if 체결강도 > 130:")
    return rid


class TestParentDiff:
    def test_parent_diff_none_when_no_parent(self, tmp_path):
        st = LoopState(db_path=str(tmp_path / "p.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            rid = _seed_run(st)
            assert L._build_parent_diff(st, rid, None, 1.0, 10.0, 40, 1.0) is None
        finally:
            st.close()

    def test_parent_diff_summarizes_deltas(self, tmp_path):
        st = LoopState(db_path=str(tmp_path / "p2.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            rid = _seed_run(st)
            # child graded 1.6 vs parent gen1 graded 1.4 → +0.2; mdd 9 vs 11 → -2.
            diff = L._build_parent_diff(st, rid, 1, 1.6, 9.0, 36, 200000.0)
        finally:
            st.close()
        assert diff is not None
        assert "gen1 대비" in diff
        assert "+0.2" in diff
        assert "-2" in diff


class TestLivePageData:
    def test_includes_lineage_and_autopsy(self, tmp_path):
        st = LoopState(db_path=str(tmp_path / "lp.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            rid = _seed_run(st)
            autopsy_pd = {"status": "ok", "trade_count": 38, "market_cap_segments": []}
            pd = L._build_live_page_data(st, rid, LoopConfig(), autopsy_pd)
        finally:
            st.close()
        assert pd is not None
        assert pd["autopsy"] == autopsy_pd
        # lineage 섹션 발행됨.
        assert "lineage" in pd
        assert pd["lineage"]["status"] == "ok"
        assert pd["lineage"]["best_gen"] == 1

    def test_page_data_survives_loopstate_serialization(self, tmp_path):
        import json
        from ai_strategy_loop.controller import contract as C

        st = LoopState(db_path=str(tmp_path / "lp2.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            rid = _seed_run(st)
            pd = L._build_live_page_data(st, rid, LoopConfig(), None)
            ls = C.LoopState(page_data=pd or {})
            revalidated = C.LoopState.model_validate(json.loads(ls.model_dump_json()))
        finally:
            st.close()
        assert revalidated.page_data.get("lineage", {}).get("status") == "ok"


class TestMetaRefreshAndSeed:
    def test_refresh_then_load_seed(self, tmp_path, monkeypatch):
        # meta_insights.json 경로를 tmp로 격리.
        import ai_strategy_loop.meta.analyze as MA

        meta_path = tmp_path / "meta_insights.json"
        monkeypatch.setattr(MA, "META_INSIGHTS_FILE", meta_path)

        st = LoopState(db_path=str(tmp_path / "m.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            # 통과 세대 2개(체결강도 공통) → 의미 있는 메타 신호.
            r = st.start_run(LoopConfig(), run_id="mr")
            st.record_generation(r, 0, buy_name="b0", sell_name="s0", status="ok",
                                 score=1.0, gate_passed=True, trade_count=40, mdd=10.0, profit=1.0,
                                 strategy_gist="if 체결강도 > 120:")
            st.record_generation(r, 1, buy_name="b1", sell_name="s1", status="ok",
                                 score=1.2, gate_passed=True, trade_count=38, mdd=9.0, profit=2.0,
                                 strategy_gist="if 체결강도 > 130 and 등락율 > 3:",
                                 parent_gen=0, diff_from_parent="MDD 감소")
            L._refresh_meta_insights(st)
        finally:
            st.close()

        assert meta_path.exists()
        # _load_meta_seed가 그 파일을 읽어 NL 가이드를 만든다.
        seed = L._load_meta_seed()
        assert seed is not None
        assert "체결강도" in seed

    def test_load_seed_none_when_no_file(self, tmp_path, monkeypatch):
        import ai_strategy_loop.meta.analyze as MA
        monkeypatch.setattr(MA, "META_INSIGHTS_FILE", tmp_path / "absent.json")
        assert L._load_meta_seed() is None
