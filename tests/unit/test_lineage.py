"""P3 — 계보 트리 + 버전 diff + run 비교 단위 테스트 (loop_runs.db 직접).

검증:
  - build_lineage_tree: parent_gen 체인으로 children/best_path(시드→best) 구성.
  - diff_generations: 지표 diff(항상) + 코드 diff(namespaced 재조회 성공 시).
  - compare_runs: loop_runs.db의 여러 run을 지표/우승전략으로 비교(cli/history.py 아님).
  - to_page_data: LIVE 계보 패널용 직렬화(JSON-안전).

합성 데이터만 사용(백테/루프 실행 없음). 코드 diff는 tmp 전략 DB에
namespaced(stockbuy/stocksell) 코드를 직접 심어 _read_strategy_code 경로를 탄다.
"""

import os
import sqlite3
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import lineage as LN  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402


def _seed_lineage_run(st, rid):
    """parent_gen 체인이 있는 합성 run을 만든다: 0←1←2(best), 3은 0에서 분기."""
    st.start_run(LoopConfig(), run_id=rid)
    # gen0: 루트(부모 없음).
    st.record_generation(rid, 0, buy_name=f"AILOOP_{rid}_g0_buy",
                         sell_name=f"AILOOP_{rid}_g0_sell", status="ok",
                         score=1.0, gate_passed=True, trade_count=40, mdd=15.0, profit=100000.0,
                         strategy_gist="if 체결강도 > 120:")
    # gen1: 0을 개선.
    st.record_generation(rid, 1, buy_name=f"AILOOP_{rid}_g1_buy",
                         sell_name=f"AILOOP_{rid}_g1_sell", status="ok",
                         score=1.2, gate_passed=True, trade_count=38, mdd=13.0, profit=130000.0,
                         parent_gen=0, diff_from_parent="gen0 대비: graded +0.2",
                         strategy_gist="if 체결강도 > 130:")
    # gen2: 1을 개선(best).
    st.record_generation(rid, 2, buy_name=f"AILOOP_{rid}_g2_buy",
                         sell_name=f"AILOOP_{rid}_g2_sell", status="ok",
                         score=1.6, gate_passed=True, trade_count=36, mdd=11.0, profit=180000.0,
                         parent_gen=1, diff_from_parent="gen1 대비: graded +0.4",
                         strategy_gist="if 체결강도 > 130 and 등락율 > 3:")
    # gen3: 0에서 분기(개선 아님).
    st.record_generation(rid, 3, buy_name=f"AILOOP_{rid}_g3_buy",
                         sell_name=f"AILOOP_{rid}_g3_sell", status="ok",
                         score=0.8, gate_passed=False, trade_count=200, mdd=40.0, profit=-50000.0,
                         parent_gen=0, diff_from_parent="gen0 대비: graded -0.2 거래 +160")


class TestLineageTree:
    def test_tree_children_and_best_path(self, tmp_path):
        st = LoopState(db_path=str(tmp_path / "t.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            _seed_lineage_run(st, "runA")
            tree = LN.build_lineage_tree(st, "runA")
        finally:
            st.close()

        assert tree["best_gen"] == 2  # graded 최고.
        # 시드→best 경로 = 0 → 1 → 2.
        assert tree["best_path"] == [0, 1, 2]
        # 루트는 parent_gen 없는 gen0.
        assert tree["roots"] == [0]
        # gen0의 children = [1, 3].
        nodes = {n["gen_no"]: n for n in tree["nodes"]}
        assert nodes[0]["children"] == [1, 3]
        assert nodes[1]["children"] == [2]
        assert nodes[3]["children"] == []

    def test_empty_run_returns_empty_tree(self, tmp_path):
        st = LoopState(db_path=str(tmp_path / "e.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            tree = LN.build_lineage_tree(st, "nope")
        finally:
            st.close()
        assert tree["nodes"] == []
        assert tree["best_gen"] == -1
        assert tree["best_path"] == []


class TestDiffGenerations:
    def test_metrics_diff_always_present(self, tmp_path):
        st = LoopState(db_path=str(tmp_path / "d.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            _seed_lineage_run(st, "runB")
            # 코드 DB에 namespaced 코드가 없으니 code_diff는 비고, metrics_diff는 채워진다.
            res = LN.diff_generations(st, "runB", 1, 2, kind="buy")
        finally:
            st.close()
        md = res["metrics_diff"]
        assert md["score"]["a"] == 1.2
        assert md["score"]["b"] == 1.6
        assert abs(md["score"]["delta"] - 0.4) < 1e-9
        assert md["mdd"]["delta"] == -2.0  # 13 → 11.

    def test_missing_generation_returns_note(self, tmp_path):
        st = LoopState(db_path=str(tmp_path / "d2.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            _seed_lineage_run(st, "runC")
            res = LN.diff_generations(st, "runC", 1, 99)
        finally:
            st.close()
        assert res["code_diff"] == ""
        assert "미존재" in res["note"]

    def test_code_diff_when_namespaced_code_exists(self, tmp_path, monkeypatch):
        # tmp 전략 DB에 namespaced buy 코드를 심어 _read_strategy_code 경로를 탄다.
        strat_db = str(tmp_path / "loop_strategies.db")
        con = sqlite3.connect(strat_db)
        con.execute('CREATE TABLE stockbuy ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
        con.execute('INSERT INTO stockbuy VALUES (?, ?)',
                    ("AILOOP_runD_g1_buy", "매수 = False\nif 체결강도 > 120:\n    매수 = True\nif 매수: self.Buy()"))
        con.execute('INSERT INTO stockbuy VALUES (?, ?)',
                    ("AILOOP_runD_g2_buy", "매수 = False\nif 체결강도 > 130:\n    매수 = True\nif 매수: self.Buy()"))
        con.commit()
        con.close()

        from ai_strategy_loop.controller import loop as L
        monkeypatch.setattr(L.bootstrap, "LOOP_DB_STRATEGY", strat_db)

        st = LoopState(db_path=str(tmp_path / "d3.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            _seed_lineage_run(st, "runD")
            res = LN.diff_generations(st, "runD", 1, 2, kind="buy")
        finally:
            st.close()
        # 코드 텍스트 diff에 변경된 임계값 라인이 보인다.
        assert "체결강도 > 120" in res["code_diff"]
        assert "체결강도 > 130" in res["code_diff"]
        assert res["note"] == ""


class TestCompareRuns:
    def test_compare_multiple_runs(self, tmp_path):
        st = LoopState(db_path=str(tmp_path / "c.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            _seed_lineage_run(st, "runX")
            # 두 번째 run: 통과 세대 없음.
            st.start_run(LoopConfig(), run_id="runY")
            st.record_generation("runY", 0, buy_name="b", sell_name="s", status="ok",
                                 score=0.5, gate_passed=False, trade_count=10, mdd=20.0, profit=-1000.0)
            cmp = LN.compare_runs(st)
        finally:
            st.close()
        assert cmp["count"] == 2
        by_run = {r["run_id"]: r for r in cmp["runs"]}
        # runX: best graded 1.6, 통과 세대 3개(0,1,2), 우승=gen2.
        assert by_run["runX"]["best_graded"] == 1.6
        assert by_run["runX"]["gate_passed_count"] == 3
        assert by_run["runX"]["winner"]["gen_no"] == 2
        # runY: 통과 0 → winner None.
        assert by_run["runY"]["gate_passed_count"] == 0
        assert by_run["runY"]["winner"] is None

    def test_compare_subset_of_runs(self, tmp_path):
        st = LoopState(db_path=str(tmp_path / "c2.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            _seed_lineage_run(st, "r1")
            _seed_lineage_run(st, "r2")
            cmp = LN.compare_runs(st, run_ids=["r1"])
        finally:
            st.close()
        assert cmp["count"] == 1
        assert cmp["runs"][0]["run_id"] == "r1"


class TestLineagePageData:
    def test_to_page_data_json_safe(self, tmp_path):
        import json
        st = LoopState(db_path=str(tmp_path / "p.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            _seed_lineage_run(st, "runP")
            pd = LN.to_page_data(st, "runP")
        finally:
            st.close()
        assert pd["status"] == "ok"
        assert pd["best_gen"] == 2
        assert pd["best_path"] == [0, 1, 2]
        # JSON 직렬화 가능(기본 타입만).
        json.dumps(pd)
