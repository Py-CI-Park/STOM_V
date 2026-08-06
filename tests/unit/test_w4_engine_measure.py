# -*- coding: utf-8 -*-
"""W4-b 엔진 실측 러너 계약 테스트 — 엔진 없이 검증 가능한 부분 전부.

계약:
  1. 재현 게이트가 PASS 이고 **정확(exact)** 트레일링 셀만 엔진에 올린다
     (상한 셀은 미래 참조라 엔진 시간을 쓰지 않는다 — 헌법 5항).
  2. 규칙 라벨 ↔ (arm, give) 파싱이 왕복한다.
  3. 남의 전략 이름은 쓰지 않는다 — `W4_S_` 이름공간 밖은 거부한다.
  4. 러너가 남기는 리포트를 **페이지 12 전이율 원장이 그대로 읽는다**
     (형식이 어긋나면 실측하고도 원장에 안 남는다 — 조립 공백의 전형).
  5. 기준선(챔피언 원본)은 지도 예측이 없으므로 계수 표본에 들어가지 않는다.
"""
from __future__ import annotations

import json

import pytest

from ai_strategy_loop.labeling import run_engine_measure as rem


# ---------------------------------------------------------------------------
# 셀 선별 · 파싱 · 이름공간
# ---------------------------------------------------------------------------

def _gate_payload():
    return {
        "verdict": "PASS",
        "reproducing": ["trailing(arm+3/give1.5)", "trailing(arm+3/give1)"],
        "cells": [
            {"rule": "trailing(arm+3/give1.5)", "exactness": "exact",
             "expectancy_pct": 0.2493, "n": 344, "day_mean_pct": 0.2862},
            {"rule": "trailing(arm+3/give1)", "exactness": "exact",
             "expectancy_pct": 0.2320, "n": 344, "day_mean_pct": 0.2655},
            # 상한 셀 — reproducing 에 없고 라벨 모양도 다르다. 선별에서 빠져야 한다.
            {"rule": "mfe_capture(600s)", "exactness": "upper_bound",
             "expectancy_pct": 3.4747, "n": 344},
            {"rule": "trailing_max(arm+1/give0.5, 300s)", "exactness": "upper_bound",
             "expectancy_pct": 1.1976, "n": 344},
        ],
    }


def test_only_exact_reproducing_cells_reach_engine(tmp_path, monkeypatch):
    root = tmp_path / "labels" / "design_v4"
    root.mkdir(parents=True)
    (root / "_reproduction_gate.json").write_text(
        json.dumps(_gate_payload(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(rem, "_LABEL_ROOT", str(tmp_path / "labels"))

    gate, cells = rem._gate_cells("design_v4")
    assert gate["verdict"] == "PASS"
    assert [c["rule"] for c in cells] == [
        "trailing(arm+3/give1.5)", "trailing(arm+3/give1)",      # 기대값 내림차순
    ]


def test_upper_bound_labels_never_parse_as_trailing():
    for label in ("mfe_capture(600s)", "trailing_max(arm+1/give0.5, 300s)",
                  "trailing_min(arm+3/give1.5, 600s)", "barrier(TP+3/SL-2, 600s)"):
        with pytest.raises(ValueError):
            rem._parse_rule(label)


@pytest.mark.parametrize("arm,give", [(3.0, 1.5), (3.0, 1.0), (5.0, 2.0), (1.0, 0.5)])
def test_rule_label_round_trips(arm, give):
    label = f"trailing(arm+{arm:g}/give{give:g})"
    assert rem._parse_rule(label) == (arm, give)


def test_refuses_names_outside_owned_namespace():
    rem._assert_owned("W4_S_TRAIL_3_1p5")            # 통과
    for name in (rem.CHAMPION_SELL, rem.CHAMPION_BUY, "Tick_S_902_905_Update", "QSP10_P5_tick_S1"):
        with pytest.raises(ValueError):
            rem._assert_owned(name)


# ---------------------------------------------------------------------------
# ★ 리포트 ↔ 전이율 원장 배선
# ---------------------------------------------------------------------------

def _report_payload():
    """러너가 실제로 쓰는 모양(엔진 결과만 채운 것)."""
    return {
        "lane": "tick",
        "design": [20240304, 20250822],
        "champion_buy": rem.CHAMPION_BUY,
        "baseline_sell": rem.CHAMPION_SELL,
        "baseline_metrics": {"trade_count": 182, "avg_profit_pct": 0.35},
        "outcomes": [
            {"name": "W4_A_champion_baseline", "rule": "챔피언 원본 매도(8종)",
             "arm": "baseline", "job_id": "job-A", "status": "done",
             "predicted": None,
             "engine": {"trade_count": 182, "avg_profit_pct": 0.35, "cagr": 33.24,
                        "mdd_pct": 18.68, "total_profit_krw": 633_000},
             "transfer_ratio": None},
            {"name": "W4_S_TRAIL_3_1p5", "rule": "trailing(arm+3/give1.5)",
             "arm": "challenger_1", "job_id": "job-B", "status": "done",
             "predicted": {"expectancy_pct": 0.2493, "rows": 344},
             "engine": {"trade_count": 340, "avg_profit_pct": 0.18, "cagr": 21.0,
                        "mdd_pct": 15.0, "total_profit_krw": 612_000},
             "transfer_ratio": 0.7220},
        ],
    }


def test_report_is_readable_by_transfer_ledger(tmp_path, monkeypatch):
    """★ 러너 산출을 페이지 12 원장이 해석한다 — 배선이 실제로 이어졌는가."""
    from ai_strategy_loop.dashboard import transfer_ledger_api as tl

    root = tmp_path / "design_v4"
    root.mkdir(parents=True)
    (root / "_p5_engine_report.json").write_text(
        json.dumps(_report_payload(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(tl, "_LABEL_ROOT", str(tmp_path))

    ledger = tl.transfer_ledger()
    assert ledger["available"] is True
    rules = [r["rule"] for r in ledger["records"]]
    # 기준선은 지도 예측이 없으므로 원장 표본이 아니다(계수를 왜곡하면 안 된다).
    assert rules == ["trailing(arm+3/give1.5)"]
    row = ledger["records"][0]
    assert row["map_expectancy_pct"] == pytest.approx(0.2493)
    assert row["engine_avg_profit_pct"] == pytest.approx(0.18)
    assert row["transfer_ratio"] == pytest.approx(0.7220)
    assert row["sign_flip"] is False


def test_sign_flip_is_flagged_not_averaged(tmp_path, monkeypatch):
    """지도 양수 → 엔진 음수는 감쇠 계수가 아니라 경고다(QSP12 −1.18)."""
    from ai_strategy_loop.dashboard import transfer_ledger_api as tl

    payload = _report_payload()
    payload["outcomes"][1]["engine"]["avg_profit_pct"] = -0.29
    payload["outcomes"][1]["transfer_ratio"] = -1.16
    root = tmp_path / "design_v4"
    root.mkdir(parents=True)
    (root / "_p5_engine_report.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(tl, "_LABEL_ROOT", str(tmp_path))

    ledger = tl.transfer_ledger()
    assert ledger["sign_flip_count"] == 1
    assert ledger["aligned_count"] == 0
    assert ledger["conservative_coefficient"] is None
