"""P2-9 변수 카탈로그 원장 — 표현가능성·누출 금지·레인 분리 계약."""

from __future__ import annotations

import ast

from ai_strategy_loop.revision.variable_catalog import (
    CATALOG,
    candidate_pool,
    catalog_for_lane,
    template_block,
    validate_catalog,
)


def test_catalog_self_validation_is_clean() -> None:
    assert validate_catalog() == ()


def test_every_template_is_valid_python_and_defines_its_own_name() -> None:
    for item in CATALOG:
        if not item.stom_template:
            continue
        tree = ast.parse(item.stom_template)
        assign = tree.body[0]
        # 표현가능성 계약: 템플릿은 조건식 상단에 그대로 붙는 단일 정의여야 한다.
        assert isinstance(assign, ast.Assign), item.name
        assert isinstance(assign.targets[0], ast.Name)
        assert assign.targets[0].id == item.name


def test_lane_separation_keeps_tick_and_min_exclusive_variables_apart() -> None:
    tick_names = {item.name for item in catalog_for_lane("tick")}
    min_names = {item.name for item in catalog_for_lane("min")}
    assert "초당순매수수량" in tick_names and "초당순매수수량" not in min_names
    assert "분당순매수금액" in min_names and "분당순매수금액" not in tick_names


def test_template_block_orders_chained_dependencies() -> None:
    block = template_block(("시가갭수익률",), "min")
    # 전일종가추정이 시가갭수익률보다 먼저 정의돼야 실행 가능하다.
    assert block.index("전일종가추정 =") < block.index("시가갭수익률 =")
    # 그대로 실행 가능한 파이썬이어야 한다(0나눗셈 가드 포함).
    namespace = {"현재가": 10_000.0, "등락율": 5.0, "분봉시가": 9_800.0}
    exec(block, {}, namespace)  # noqa: S102 - 결정적 템플릿 자가검증
    assert namespace["시가갭수익률"] != 0


def test_candidate_pool_excludes_analysis_only_variables() -> None:
    for lane in ("tick", "min"):
        assert all(not item.analysis_only for item in candidate_pool(lane))
        assert len(candidate_pool(lane)) >= 10
