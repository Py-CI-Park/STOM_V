"""시드 격자 커버리지 지도 + CLI (T1.4) 단위 테스트.

검증:
  - build_coverage_map: 셀별 시드 수/거래수/손익 분포 집계 정확성,
    cell_id·buy_sha256 결과 귀속, 유연 스키마(동의 키), unmatched 집계,
    필수 필드(trades/profit) 누락 거부.
  - coverage_gaps: 경계 판정(299 → gap, 300 → 충족), discovery 프롬프트
    coverage_gap 계약 필드(coverage_gap_id/coverage_bucket_keys) 충족 —
    build_discovery_research_messages 에 실제로 주입해 확인 (prompt.py 는
    읽기 전용 소비).
  - JSON 왕복: save/load 동등성, 스키마 불일치 거부.
  - passport 렌더: 필수 필드 표 + 코드 펜스, condition_id 포맷 단일 출처
    (custom created_reason 이어도 정본 포맷 유지).
  - CLI: build 가 seeds JSON + passport md 를 생성, coverage 가 map/gaps
    JSON 을 생성 (tmp_path).

실DB/백테 미사용: 결과 요약은 합성 dict 다.
"""

import json
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.brain.prompt import build_discovery_research_messages  # noqa: E402
from ai_strategy_loop.seeds import (  # noqa: E402
    COVERAGE_MAP_SCHEMA,
    build_coverage_map,
    build_seed,
    coverage_gaps,
    enumerate_cells,
    load_coverage_map,
    passport_condition_id,
    render_passport,
    save_coverage_map,
    seed_condition_id,
)


@pytest.fixture(scope="module")
def two_cells():
    """tick 셀 1개 + min 셀 1개 (결정론 순서 앞쪽)."""
    cells = enumerate_cells()
    return cells[0], next(c for c in cells if c.lane == "min")


@pytest.fixture(scope="module")
def two_seeds(two_cells):
    """두 셀에 momentum_breakout 시드 하나씩."""
    a, b = two_cells
    return build_seed(a, "momentum_breakout"), build_seed(b, "momentum_breakout")


# --------------------------------------------------------------------------
# 집계 정확성
# --------------------------------------------------------------------------
def test_coverage_aggregation_accuracy(two_cells, two_seeds):
    """셀별 seed_count/trades/손익 분포(n·total·mean·min·max·wins) 집계."""
    cell_a, cell_b = two_cells
    seed_a, seed_b = two_seeds
    results = [
        # cell_id 직접 귀속.
        {"cell_id": cell_a.cell_id, "trades": 120, "profit": 1000.0},
        {"cell_id": cell_a.cell_id, "trades": 80, "profit": -400.0},
        # buy_sha256 으로 시드 인덱스 귀속.
        {"buy_sha256": seed_b.buy_sha256, "trades": 350, "profit": 250.0},
    ]
    cov = build_coverage_map([seed_a, seed_b], results)

    assert cov["schema"] == COVERAGE_MAP_SCHEMA
    assert cov["totals"]["cells"] == 144  # 기본 격자 전 셀 유지 (0시드 셀 포함)
    assert cov["totals"]["seeds"] == 2
    assert cov["totals"]["matched_results"] == 3
    assert cov["totals"]["unmatched_results"] == 0
    assert cov["totals"]["trades"] == 120 + 80 + 350

    a = cov["cells"][cell_a.cell_id]
    assert a["seed_count"] == 1
    assert a["result_count"] == 2
    assert a["trades"] == 200
    ps = a["profit_summary"]
    assert ps["n"] == 2
    assert ps["total"] == pytest.approx(600.0)
    assert ps["mean"] == pytest.approx(300.0)
    assert ps["min"] == pytest.approx(-400.0)
    assert ps["max"] == pytest.approx(1000.0)
    assert ps["wins"] == 1

    b = cov["cells"][cell_b.cell_id]
    assert (b["seed_count"], b["result_count"], b["trades"]) == (1, 1, 350)

    # 시드/결과 없는 셀도 0 집계로 존재.
    empty = next(v for k, v in cov["cells"].items() if k not in (cell_a.cell_id, cell_b.cell_id))
    assert (empty["seed_count"], empty["trades"], empty["profit_summary"]["n"]) == (0, 0, 0)


def test_coverage_flexible_schema_and_unmatched(two_seeds):
    """동의 키(prior_trades/prior_profit) 수용 + 귀속 불가 결과는 unmatched."""
    seed_a, _ = two_seeds
    results = [
        {"cell_id": seed_a.cell_id, "prior_trades": 10, "prior_profit": 5},
        {"trades": 99, "profit": 1.0},                     # 귀속 정보 없음
        {"buy_sha256": "없는sha", "trades": 7, "profit": 2.0},  # 미지 sha
    ]
    cov = build_coverage_map([seed_a], results)
    assert cov["cells"][seed_a.cell_id]["trades"] == 10
    assert cov["totals"]["unmatched_results"] == 2
    assert {u["index"] for u in cov["unmatched"]} == {1, 2}
    # unmatched 는 셀 집계에 섞이지 않는다.
    assert cov["totals"]["trades"] == 10


def test_coverage_rejects_missing_required_fields(two_seeds):
    """trades/profit 필수 — 누락·비수치는 ValueError."""
    seed_a, _ = two_seeds
    with pytest.raises(ValueError):
        build_coverage_map([seed_a], [{"cell_id": seed_a.cell_id, "profit": 1.0}])
    with pytest.raises(ValueError):
        build_coverage_map([seed_a], [{"cell_id": seed_a.cell_id, "trades": 5}])
    with pytest.raises(ValueError):
        build_coverage_map([seed_a], [{"cell_id": seed_a.cell_id, "trades": "많이", "profit": 1.0}])
    with pytest.raises(ValueError):
        build_coverage_map([{"family": "x"}], [])  # 시드 cell_id 누락


# --------------------------------------------------------------------------
# gap 판정 경계 + discovery 프롬프트 계약
# --------------------------------------------------------------------------
def test_coverage_gap_boundary_299_vs_300(two_cells, two_seeds):
    """299 거래 → gap, 300 거래 → 충족 (min_trades=300 반열림 경계)."""
    cell_a, cell_b = two_cells
    seed_a, seed_b = two_seeds
    cov = build_coverage_map([seed_a, seed_b], [
        {"cell_id": cell_a.cell_id, "trades": 299, "profit": 0.0},
        {"cell_id": cell_b.cell_id, "trades": 300, "profit": 0.0},
    ])
    gaps = coverage_gaps(cov, min_trades=300)
    gap_ids = {g["cell_id"] for g in gaps}
    assert cell_a.cell_id in gap_ids
    assert cell_b.cell_id not in gap_ids
    # 결과 없는 나머지 142셀도 전부 gap.
    assert len(gaps) == 144 - 1

    gap_a = next(g for g in gaps if g["cell_id"] == cell_a.cell_id)
    assert gap_a["trades"] == 299
    assert gap_a["trade_deficit"] == 1
    assert gap_a["reason"] == "insufficient_train_trades"
    empty_gap = next(g for g in gaps if g["seed_count"] == 0)
    assert empty_gap["reason"] == "no_seeds"

    with pytest.raises(ValueError):
        coverage_gaps(cov, min_trades=0)
    with pytest.raises(ValueError):
        coverage_gaps({"schema": "다른것", "cells": {}})


def test_gap_feeds_discovery_prompt_contract(two_seeds):
    """gap dict 가 discovery 프롬프트 계약을 그대로 만족한다 (읽기 전용 소비)."""
    seed_a, seed_b = two_seeds
    cov = build_coverage_map([seed_a, seed_b], [])
    gaps = coverage_gaps(cov)
    assert gaps, "결과 0건이면 전 셀이 gap 이어야 한다"
    gap = gaps[0]

    # 계약 필드 형식: coverage_gap_id 문자열 + coverage_bucket_keys 문자열 리스트.
    assert isinstance(gap["coverage_gap_id"], str) and gap["coverage_gap_id"]
    assert isinstance(gap["coverage_bucket_keys"], list) and gap["coverage_bucket_keys"]
    assert all(isinstance(k, str) for k in gap["coverage_bucket_keys"])
    json.dumps(gap, ensure_ascii=False)  # 프롬프트 JSON 블록 직렬화 가능

    messages = build_discovery_research_messages(
        "buy",
        timeframe="tick",
        coverage_gap=gap,
        novelty_context={"existing_fingerprints": []},
    )
    user = messages[1]["content"]
    assert gap["coverage_gap_id"] in user
    assert gap["coverage_bucket_keys"][0] in user


# --------------------------------------------------------------------------
# JSON 왕복
# --------------------------------------------------------------------------
def test_coverage_map_json_roundtrip(tmp_path, two_cells, two_seeds):
    """save → load 가 dict 동등성을 보존하고, 잘못된 스키마는 거부."""
    cell_a, _ = two_cells
    seed_a, seed_b = two_seeds
    cov = build_coverage_map([seed_a, seed_b], [
        {"cell_id": cell_a.cell_id, "trades": 42, "profit": -3.5},
    ])
    p = save_coverage_map(cov, tmp_path / "sub" / "coverage_map.json")
    assert p.exists()
    loaded = load_coverage_map(p)
    assert loaded == cov
    assert list(loaded["cells"]) == list(cov["cells"])  # 셀 순서 보존

    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"schema": "다른것"}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_coverage_map(bad)
    with pytest.raises(ValueError):
        save_coverage_map({"schema": "다른것"}, tmp_path / "x.json")


# --------------------------------------------------------------------------
# passport 렌더
# --------------------------------------------------------------------------
def test_render_passport_required_fields(two_seeds):
    """필수 필드 표 + Core hypothesis + Buy/Sell 코드 펜스 + 연구 고정 상태값."""
    seed_a, _ = two_seeds
    md = render_passport(seed_a)
    for token in (
        "# Condition Passport —",
        f"| condition_id | `lattice_v1:{seed_a.cell_id}:{seed_a.family}` |",
        "| human_name |", "| role | `lattice_seed` |",
        "| buy_strategy_id |", "| sell_strategy_id |",
        f"| buy_code_sha256 | `{seed_a.buy_sha256}` |",
        f"| sell_code_sha256 | `{seed_a.sell_sha256}` |",
        "| prior_profit | `n/a` |", "| prior_mdd | `n/a` |", "| prior_trades | `n/a` |",
        "| promotion_status | `research_only / not_promoted` |",
        "## Core hypothesis", "## Buy condition full code", "## Sell condition full code",
    ):
        assert token in md, token
    assert seed_a.buy_code in md and seed_a.sell_code in md
    # prior 갱신 렌더.
    md2 = render_passport(seed_a, prior_profit=12345, prior_mdd=7.7, prior_trades=310)
    assert "| prior_trades | `310` |" in md2


def test_condition_id_single_source_with_custom_reason(two_cells):
    """condition_id 포맷 단일 출처: custom created_reason 이어도 정본 포맷 유지."""
    cell_a, _ = two_cells
    expected = seed_condition_id(cell_a.cell_id, "momentum_breakout")
    assert expected == f"lattice_v1:{cell_a.cell_id}:momentum_breakout"

    # 기본 created_reason 은 정본 condition_id 와 동일 값 (같은 함수 출처).
    default = build_seed(cell_a, "momentum_breakout")
    assert default.created_reason == passport_condition_id(default) == expected

    # custom reason 은 사유 태그만 바꾸고 condition_id 는 정본 포맷을 유지한다.
    custom = build_seed(cell_a, "momentum_breakout", created_reason="manual_experiment_01")
    assert custom.created_reason == "manual_experiment_01"
    assert passport_condition_id(custom) == expected
    md = render_passport(custom)
    assert f"| condition_id | `{expected}` |" in md
    assert "manual_experiment_01" in md  # 사유 태그는 가설 본문에 노출


# --------------------------------------------------------------------------
# CLI (main(argv) 직접 호출 — tmp_path 산출 확인)
# --------------------------------------------------------------------------
def _run_build(tmp_path, extra=()):
    from cli.seed_lattice import main
    out_dir = tmp_path / "lattice"
    rc = main(["build", "--out-dir", str(out_dir),
               "--lane", "tick", "--family", "momentum_breakout", *extra])
    assert rc == 0
    return out_dir


def test_cli_build_creates_seeds_json_and_passports(tmp_path, capsys):
    """build: seeds JSON(72시드) + passport md 72개 생성, 요약 JSON 출력."""
    out_dir = _run_build(tmp_path)
    seeds_path = out_dir / "lattice_seeds.json"
    assert seeds_path.exists()
    data = json.loads(seeds_path.read_text(encoding="utf-8"))
    assert data["schema"] == "seed_lattice_seeds_v1"
    assert data["seed_count"] == 72  # tick 72셀 × 1패밀리
    assert len(data["seeds"]) == 72
    first = data["seeds"][0]
    for key in ("condition_id", "cell_id", "family", "buy_code", "sell_code",
                "buy_sha256", "sell_sha256", "params", "created_reason", "passport_md"):
        assert key in first, key

    passports = sorted((out_dir / "passports").glob("*.md"))
    assert len(passports) == 72
    sample = passports[0].read_text(encoding="utf-8")
    assert "# Condition Passport —" in sample and "```python" in sample

    summary = json.loads(capsys.readouterr().out)
    assert summary["command"] == "build" and summary["seed_count"] == 72


def test_cli_coverage_creates_map_and_gaps(tmp_path, capsys):
    """coverage: 결과 JSON → coverage map + gaps 파일 생성, 경계 반영."""
    out_dir = _run_build(tmp_path, extra=("--skip-passports",))
    seeds_path = out_dir / "lattice_seeds.json"
    seeds = json.loads(seeds_path.read_text(encoding="utf-8"))["seeds"]

    results_path = tmp_path / "results.json"
    results_path.write_text(json.dumps({"results": [
        {"cell_id": seeds[0]["cell_id"], "trades": 300, "profit": 10.0},
        {"buy_sha256": seeds[1]["buy_sha256"], "trades": 299, "profit": -1.0},
    ]}), encoding="utf-8")

    from cli.seed_lattice import main
    map_path = tmp_path / "cov" / "coverage_map.json"
    gaps_path = tmp_path / "cov" / "coverage_gaps.json"
    rc = main(["coverage", "--seeds", str(seeds_path),
               "--results", str(results_path),
               "--out", str(map_path), "--gaps-out", str(gaps_path)])
    assert rc == 0
    capsys.readouterr()

    cov = load_coverage_map(map_path)
    assert cov["cells"][seeds[0]["cell_id"]]["trades"] == 300
    assert cov["cells"][seeds[1]["cell_id"]]["trades"] == 299

    gaps_doc = json.loads(gaps_path.read_text(encoding="utf-8"))
    assert gaps_doc["schema"] == "seed_lattice_coverage_gaps_v1"
    gap_cells = {g["cell_id"] for g in gaps_doc["gaps"]}
    assert seeds[0]["cell_id"] not in gap_cells   # 300 → 충족
    assert seeds[1]["cell_id"] in gap_cells       # 299 → gap
    assert gaps_doc["gap_count"] == len(gaps_doc["gaps"]) == 144 - 1
