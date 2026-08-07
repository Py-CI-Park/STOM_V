# -*- coding: utf-8 -*-
"""페이지 28 매도 축 종합 API 계약 테스트.

계약:
  1. 세 출처(게이트·워크포워드·엔진)를 **규칙 이름으로 조인**한다.
  2. 없는 출처는 없다고 답한다 — 추정치를 채우지 않는다(엔진 미실측 = null).
  3. 상한 셀도 표에 싣되 `judgeable=False` 로 표시한다(전셀 보고 + 판정 분리).
  4. 기준선(baseline)은 규칙 행이 아니다 — 따로 뺀다.
  5. 기준선 Δ는 엔진 값이 양쪽 다 있을 때만 계산한다.
  6. 지도 기대값 내림차순으로 정렬한다(없는 값은 뒤로).
"""
from __future__ import annotations

import json

import pytest

from ai_strategy_loop.dashboard import exit_axis_api as ea


def _gate():
    return {
        "verdict": "PASS",
        "entry_seconds": 1612,
        "entry_positions": 344,
        "champion_engine": {"trades": 182, "avg_profit_pct": 0.35},
        "reproduction_ratio": 1 / 3,
        "reproducing": ["trailing(arm+3/give1.5)"],
        "cells": [
            {"rule": "trailing(arm+3/give1.5)", "family": "trailing_exact",
             "exactness": "exact", "expectancy_pct": 0.2493, "day_mean_pct": 0.2862,
             "day_positive_ratio": 0.564, "n": 344},
            {"rule": "mfe_capture(600s)", "family": "mfe_capture",
             "exactness": "upper_bound", "expectancy_pct": 3.4747,
             "day_mean_pct": 3.5, "day_positive_ratio": 0.9, "n": 344},
            {"rule": "barrier(TP+3/SL-2, 600s)", "family": "barrier",
             "exactness": "exact", "expectancy_pct": -0.0078, "day_mean_pct": 0.0283,
             "day_positive_ratio": 0.498, "n": 344},
        ],
    }


def _walkforward():
    return {
        "verdict": "PASS", "candidates": 28,
        "mean_valid_day_mean_pct": 0.1506, "positive_folds": 3,
        "mean_train_valid_gap_pct": 0.1805, "selection_bias_pct_large_scale": 0.6225,
        "folds": [
            {"fold": 1, "chosen": "trailing(arm+3/give1)", "train_days": 120,
             "valid_days": 21, "train_day_mean_pct": 0.3637,
             "valid_day_mean_pct": -0.0718, "gap_pct": 0.4354},
            {"fold": 2, "chosen": "trailing(arm+3/give1.5)", "train_days": 141,
             "valid_days": 21, "train_day_mean_pct": 0.3137,
             "valid_day_mean_pct": 0.4400, "gap_pct": -0.1263},
            {"fold": 3, "chosen": "trailing(arm+3/give1.5)", "train_days": 162,
             "valid_days": 21, "train_day_mean_pct": 0.36,
             "valid_day_mean_pct": 0.37, "gap_pct": -0.01},
        ],
    }


def _engine():
    return {
        "lane": "tick", "design": [20240304, 20250822],
        "outcomes": [
            {"name": "W4_A_champion_baseline", "rule": "챔피언 원본 매도(8종)",
             "arm": "baseline", "job_id": "job-A",
             "engine": {"trade_count": 182, "avg_profit_pct": 0.35, "cagr": 33.24,
                        "mdd_pct": 18.68},
             "transfer_ratio": None, "predicted": None},
            {"name": "W4_S_TRAIL_3_1p5", "rule": "trailing(arm+3/give1.5)",
             "arm": "challenger_1", "job_id": "job-B",
             "engine": {"trade_count": 340, "avg_profit_pct": 0.18, "cagr": 21.0,
                        "mdd_pct": 15.0},
             "transfer_ratio": 0.722,
             "predicted": {"expectancy_pct": 0.2493, "rows": 344}},
        ],
    }


@pytest.fixture()
def labels(tmp_path, monkeypatch):
    root = tmp_path / "design_v4"
    root.mkdir(parents=True)
    monkeypatch.setattr(ea, "_LABEL_ROOT", str(tmp_path))
    return root


def _write(root, name, payload):
    (root / name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------

def test_joins_three_sources_on_rule_name(labels):
    _write(labels, ea._GATE, _gate())
    _write(labels, ea._WALKFORWARD, _walkforward())
    _write(labels, ea._ENGINE, _engine())

    payload = ea.exit_axis()
    assert payload["available"] is True
    assert payload["sources"] == {"reproduction_gate": True, "walkforward": True,
                                  "engine": True, "ladder": False, "engine_ladder": False}

    row = next(r for r in payload["rows"] if r["rule"] == "trailing(arm+3/give1.5)")
    assert row["map_expectancy_pct"] == pytest.approx(0.2493)      # 지도
    assert row["walkforward_chosen_count"] == 2                     # 폴드 2·3 이 골랐다
    assert row["engine_avg_profit_pct"] == pytest.approx(0.18)      # 엔진
    assert row["transfer_ratio"] == pytest.approx(0.722)
    assert row["reproduces_champion"] is True


def test_missing_engine_leaves_nulls_not_estimates(labels):
    """★ 엔진이 없으면 없다고 답한다 — 지도 값으로 추정해 채우면 그게 사고다."""
    _write(labels, ea._GATE, _gate())
    _write(labels, ea._WALKFORWARD, _walkforward())

    payload = ea.exit_axis()
    assert payload["sources"]["engine"] is False
    assert payload["engine_baseline"] is None
    for row in payload["rows"]:
        assert row["engine_avg_profit_pct"] is None
        assert row["transfer_ratio"] is None
        assert row["engine_delta_vs_baseline_pct"] is None


def test_upper_bound_is_listed_but_not_judgeable(labels):
    """전셀은 싣되(헌법 2항) 판정 근거에서는 뺀다(헌법 5항)."""
    _write(labels, ea._GATE, _gate())

    payload = ea.exit_axis()
    rules = {r["rule"]: r for r in payload["rows"]}
    assert rules["mfe_capture(600s)"]["judgeable"] is False
    assert rules["trailing(arm+3/give1.5)"]["judgeable"] is True
    assert rules["barrier(TP+3/SL-2, 600s)"]["judgeable"] is True


def test_baseline_is_not_a_rule_row(labels):
    _write(labels, ea._GATE, _gate())
    _write(labels, ea._ENGINE, _engine())

    payload = ea.exit_axis()
    assert "챔피언 원본 매도(8종)" not in [r["rule"] for r in payload["rows"]]
    assert payload["engine_baseline"]["avg_profit_pct"] == pytest.approx(0.35)
    assert payload["engine_baseline"]["job_id"] == "job-A"


def test_delta_vs_baseline_only_when_both_measured(labels):
    _write(labels, ea._GATE, _gate())
    _write(labels, ea._ENGINE, _engine())

    payload = ea.exit_axis()
    measured = next(r for r in payload["rows"] if r["rule"] == "trailing(arm+3/give1.5)")
    assert measured["engine_delta_vs_baseline_pct"] == pytest.approx(0.18 - 0.35)
    unmeasured = next(r for r in payload["rows"] if r["rule"] == "mfe_capture(600s)")
    assert unmeasured["engine_delta_vs_baseline_pct"] is None


def test_rows_sorted_by_map_expectancy_desc(labels):
    _write(labels, ea._GATE, _gate())
    values = [r["map_expectancy_pct"] for r in ea.exit_axis()["rows"]]
    assert values == sorted(values, reverse=True)


def test_absent_files_are_reported_not_faked(labels):
    payload = ea.exit_axis()
    assert payload["available"] is False
    assert payload["rows"] == []
    assert payload["gate"] is None and payload["walkforward"] is None


def test_corrupt_json_does_not_raise(labels):
    (labels / ea._GATE).write_text("{not json", encoding="utf-8")
    payload = ea.exit_axis()
    assert payload["available"] is False
    assert payload["sources"]["reproduction_gate"] is False


def test_reading_rules_are_always_shipped(labels):
    _write(labels, ea._GATE, _gate())
    rules = ea.exit_axis()["reading_rules"]
    assert any("상한" in r for r in rules)
    assert any("나누지" in r for r in rules)


# ---------------------------------------------------------------------------
# 사다리 — 엔진보다 앞선 관문
# ---------------------------------------------------------------------------

def _ladder(rule, verdict, regime_verdict="FAIL"):
    return {
        "rule": rule, "verdict": verdict,
        "plateau": {"verdict": "PASS"},
        "cost_stress": {"verdict": "PASS"},
        "regime": {"verdict": regime_verdict, "segments": [
            {"segment": 1, "day_from": 20240304, "day_to": 20240719,
             "days": 56, "n": 79, "day_mean_pct": 0.4870},
            {"segment": 2, "day_from": 20240722, "day_to": 20241129,
             "days": 56, "n": 79, "day_mean_pct": -0.2511},
        ]},
    }


def test_ladder_verdict_sits_next_to_engine_value(labels):
    """★ 엔진 수치가 좋아도 사다리가 FAIL 이면 같은 줄에서 보여야 한다."""
    _write(labels, ea._GATE, _gate())
    _write(labels, ea._ENGINE, _engine())
    _write(labels, "_exit_ladder_3_1.5.json", _ladder("trailing(arm+3/give1.5)", "FAIL"))

    payload = ea.exit_axis()
    row = next(r for r in payload["rows"] if r["rule"] == "trailing(arm+3/give1.5)")
    assert row["engine_avg_profit_pct"] == pytest.approx(0.18)   # 엔진은 양수인데
    assert row["ladder_verdict"] == "FAIL"                        # 사다리는 탈락
    assert row["ladder_rungs"]["regime"] == "FAIL"
    assert row["ladder_rungs"]["plateau"] == "PASS"
    assert payload["sources"]["ladder"] is True


def test_rules_without_ladder_report_none_not_pass(labels):
    """안 태운 것과 통과한 것을 구분한다 — None 을 PASS 로 읽으면 관문이 사라진다."""
    _write(labels, ea._GATE, _gate())
    payload = ea.exit_axis()
    for row in payload["rows"]:
        assert row["ladder_verdict"] is None
        assert row["ladder_rungs"] is None


def test_regime_segments_are_carried_for_display(labels):
    _write(labels, ea._GATE, _gate())
    _write(labels, "_exit_ladder_3_1.5.json", _ladder("trailing(arm+3/give1.5)", "FAIL"))
    row = next(r for r in ea.exit_axis()["rows"] if r["rule"] == "trailing(arm+3/give1.5)")
    assert len(row["ladder_regime_segments"]) == 2
    assert row["ladder_regime_segments"][1]["day_mean_pct"] == pytest.approx(-0.2511)


def test_corrupt_ladder_file_is_skipped(labels):
    _write(labels, ea._GATE, _gate())
    (labels / "_exit_ladder_bad.json").write_text("{not json", encoding="utf-8")
    payload = ea.exit_axis()
    assert payload["sources"]["ladder"] is False


def test_reading_rules_mention_ladder_precedence(labels):
    _write(labels, ea._GATE, _gate())
    assert any("사다리" in rule for rule in ea.exit_axis()["reading_rules"])
