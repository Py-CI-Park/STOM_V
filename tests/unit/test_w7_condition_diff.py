# -*- coding: utf-8 -*-
"""W7-4 계약 테스트 — 조건식 비교 뷰어(페이지 33).

계약:
  1. **조건식을 실행하지 않는다.** 텍스트만 읽는다 — exec/eval/compile 금지.
  2. 절 층은 `active`/`commented`/`absent` 를 구분한다. 주석 처리(제거 실험의
     흔적)를 "없음"과 같게 취급하면 무엇을 뺐는지 알 수 없다.
  3. 줄 층은 바뀐 덩어리와 문맥만 낸다 — 131줄을 다 뿌리면 차이를 못 찾는다.
  4. 차이가 없으면 없다고 말한다.
  5. 임계만 바꾼 변화(절 이름 없는 변화)도 줄 층에서 잡힌다.
"""
from __future__ import annotations

import inspect

import pytest

from ai_strategy_loop.controller import condition_diff as cd
from ai_strategy_loop.labeling import champion_clauses as cc
from tests.seed_db_guard import open_seed_database

LEFT = """\
매수 = True
if not (관심종목 == 1):
    매수 = False
elif 90200 <= 시분초 < 90500:
    if not (2.0 < 등락율 <= 15.0):
        매수 = False
    elif not (3.0 <= 시가대비등락율 < 8.0):
        매수 = False
    elif not (회전율 > 2):
        매수 = False
if 매수:
    self.Buy()
"""


# ---------------------------------------------------------------------------
# 안전
# ---------------------------------------------------------------------------

def test_module_never_executes_the_condition():
    """★ 이 모듈은 조건식을 읽기만 한다.

    아래 문자열들은 **금지 목록**이다 — 호출이 아니라 소스에 없는지 검사하는
    대상이다. 조건식은 `strategy.db` 에서 온 텍스트이므로, 비교 화면이 그것을
    실행하면 임의 코드 실행 통로가 된다.
    """
    import ast

    banned = {"exec", "eval", "compile", "__import__"}
    tree = ast.parse(inspect.getsource(cd))
    called = {n.func.id for n in ast.walk(tree)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    # 이름 호출만 본다 — `re.compile` 은 속성 호출이라 걸리지 않아야 한다.
    assert not (called & banned), called & banned


# ---------------------------------------------------------------------------
# 절 층
# ---------------------------------------------------------------------------

def test_clause_state_separates_commented_from_absent():
    """★ 주석 처리와 부재를 같게 보면 '무엇을 뺐나'를 알 수 없다."""
    dropped = cc.drop_clause_from_dsl(LEFT, "905_시가대비")
    state = cd.clause_state(dropped)
    assert state["905_시가대비"] == "commented"
    assert state["902_회전율"] == "active"       # 앵커 '회전율 > 2' 가 살아 있다
    assert state["905_전일비"] == "absent"       # 이 조건식에 없다


def test_clause_delta_reports_only_what_changed():
    dropped = cc.drop_clause_from_dsl(LEFT, "905_시가대비")
    delta = cd.clause_delta(LEFT, dropped)
    assert len(delta) == 1
    assert delta[0]["clause"] == "905_시가대비"
    assert (delta[0]["left"], delta[0]["right"]) == ("active", "commented")
    assert delta[0]["label"]                      # 사람 말이 비면 화면이 빈다


def test_no_clause_delta_when_only_thresholds_move():
    """임계 변경은 절 층에 안 잡힌다 — 그래서 줄 층이 필요하다."""
    other = LEFT.replace("2.0 < 등락율 <= 15.0", "2.5 < 등락율 <= 15.0")
    assert cd.clause_delta(LEFT, other) == []
    assert cd.compare("a", LEFT, "b", other)["changed_lines"] == 2


# ---------------------------------------------------------------------------
# 줄 층
# ---------------------------------------------------------------------------

def test_diff_marks_removed_and_added_lines():
    dropped = cc.drop_clause_from_dsl(LEFT, "905_시가대비")
    rows = cd.diff_lines(LEFT, dropped)
    assert any(r["op"] == "del" and "시가대비등락율" in r["text"] for r in rows)
    assert any(r["op"] == "add" and r["text"].lstrip().startswith("#") for r in rows)


def test_identical_inputs_say_so():
    rows = cd.diff_lines(LEFT, LEFT)
    assert len(rows) == 1 and rows[0]["op"] == "identical"
    assert cd.compare("a", LEFT, "b", LEFT)["identical"] is True


def test_long_files_are_elided_not_dumped():
    """★ 131줄을 다 뿌리면 화면에서 차이를 못 찾는다."""
    left = "\n".join(f"line {i}" for i in range(200))
    right = left.replace("line 100", "line 100 CHANGED")
    rows = cd.diff_lines(left, right, context=2)
    assert len(rows) < 12                                  # 문맥만
    assert any("생략" in r["text"] for r in rows) or len(rows) <= 6


def test_gap_marker_appears_between_distant_changes():
    left = "\n".join(f"line {i}" for i in range(200))
    right = left.replace("line 10", "line 10 X").replace("line 150", "line 150 Y")
    rows = cd.diff_lines(left, right, context=1)
    assert any(r["op"] == "gap" for r in rows)


# ---------------------------------------------------------------------------
# 요약
# ---------------------------------------------------------------------------

def test_comment_only_change_is_flagged():
    """절 제거 실험은 '주석 처리뿐'인 변화로 나타난다."""
    dropped = cc.drop_clause_from_dsl(LEFT, "905_시가대비")
    assert cd.compare("a", LEFT, "b", dropped)["comment_only"] is True


def test_threshold_change_is_not_comment_only():
    other = LEFT.replace("회전율 > 2", "회전율 > 1.5")
    assert cd.compare("a", LEFT, "b", other)["comment_only"] is False


def test_compare_counts_code_lines_excluding_comments():
    dropped = cc.drop_clause_from_dsl(LEFT, "905_시가대비")
    view = cd.compare("champ", LEFT, "relaxed", dropped)
    assert view["left"]["code_lines"] - view["right"]["code_lines"] == 2
    assert view["left"]["name"] == "champ" and view["right"]["name"] == "relaxed"


def test_known_clauses_cover_every_anchor():
    keys = {r["clause"] for r in cd.known_clauses()}
    assert keys == set(cc.DSL_ANCHOR)
    assert all(r["label"] for r in cd.known_clauses())


def test_pick_pairs_keeps_only_our_namespace():
    names = ["Tick_B_902_905", "W7_B_RELAX_905_전일비", "W4_S_TRAIL_5_2"]
    assert cd.pick_pairs(names, prefix="W7_B_") == ["W7_B_RELAX_905_전일비"]


@pytest.mark.parametrize("key", sorted(cc.DSL_ANCHOR))
def test_every_anchor_is_classifiable_on_the_real_champion(key):
    """실제 챔피언 매수식에서 모든 앵커가 active 로 읽혀야 한다."""
    with open_seed_database(
        "_database/strategy.db", required_tables=("stockbuy",)
    ) as con:
        row = con.execute('SELECT 전략코드 FROM stockbuy WHERE "index"=?',
                          ("Tick_B_902_905",)).fetchone()
    if row is None:
        pytest.skip("챔피언 매수식이 이 환경에 없다")
    assert cd.clause_state(str(row[0]))[key] == "active"
