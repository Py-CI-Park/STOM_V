# -*- coding: utf-8 -*-
"""페이지 12 강화 — 전이율 누적 원장 계약 테스트.

계약:
  1. P5 리포트에서만 원장을 만든다(기록 없으면 조작하지 않고 비어 있다).
  2. 보수 계수 = **부호 일치** 건의 중앙값. 부호 반전 건은 계수에서 제외한다.
  3. 부호 반전은 별도 카운트로 노출한다(구조 불일치 경고 — QSP12 −1.18 사건).
  4. 표본이 최소치 미만이면 status='accumulating' 이고 환산기는 거부한다.
"""
from __future__ import annotations

import json

import pytest

from ai_strategy_loop.dashboard import transfer_ledger_api as api


def _outcome(name, map_pct, engine_pct, *, ratio=None, rows=500, trades=600):
    return {
        "name": name, "rule": "TP3.0/SL2.0", "job_id": f"job-{name}",
        "predicted": {"rows": rows, "days": 200, "expectancy_pct": map_pct},
        "engine": {"trade_count": trades, "avg_profit_pct": engine_pct,
                   "total_profit_krw": 100000, "cagr": 12.0, "mdd_pct": 10.0},
        "transfer_ratio": ratio if ratio is not None else (engine_pct / map_pct if map_pct else None),
    }


@pytest.fixture()
def label_root(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "_LABEL_ROOT", str(tmp_path))
    def write(name, payload):
        directory = tmp_path / "design_v3"
        directory.mkdir(exist_ok=True)
        (directory / name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return write


def test_empty_ledger_is_honest(label_root):
    payload = api.transfer_ledger()
    assert payload["available"] is False
    assert payload["records"] == []
    assert payload["conservative_coefficient"] is None
    assert payload["status"] == "accumulating"


def test_coefficient_is_median_of_aligned(label_root):
    label_root("_p5_hierarchy_report.json", {"lane": "tick", "outcomes": [
        _outcome("H1", 0.35, 0.12),     # ratio ≈ 0.343
        _outcome("H2", 0.30, 0.06),     # ratio = 0.20
        _outcome("H3", 0.40, 0.20),     # ratio = 0.50
    ]})
    payload = api.transfer_ledger()

    assert payload["available"] is True
    assert payload["record_count"] == 3
    assert payload["aligned_count"] == 3
    assert payload["conservative_coefficient"] == pytest.approx(0.342857, rel=1e-4)  # 중앙값
    assert payload["status"] == "ready"


def test_sign_flip_excluded_from_coefficient(label_root):
    label_root("_p5_report.json", {"lane": "tick", "outcomes": [
        _outcome("A", 0.30, 0.15),      # 0.50 (일치)
        _outcome("B", 0.30, 0.09),      # 0.30 (일치)
        _outcome("C", 0.35, 0.15),      # 0.4286 (일치)
        _outcome("FLIP", 0.085, -0.10), # 부호 반전 — 계수에서 제외
    ]})
    payload = api.transfer_ledger()

    assert payload["record_count"] == 4
    assert payload["aligned_count"] == 3
    assert payload["sign_flip_count"] == 1
    flip = next(r for r in payload["records"] if r["name"] == "FLIP")
    assert flip["sign_flip"] is True
    # 반전 건(음수 비율)이 섞였다면 중앙값이 내려갔을 것 — 일치 3건의 중앙값이어야 한다
    assert payload["conservative_coefficient"] == pytest.approx(0.428571, rel=1e-4)


def test_estimate_requires_minimum_records(label_root):
    label_root("_p5_report.json", {"lane": "tick", "outcomes": [_outcome("A", 0.30, 0.15)]})
    result = api.transfer_estimate(map_expectancy_pct=0.4)
    assert result["available"] is False
    assert result["reason"] == "insufficient_records"


def test_estimate_applies_coefficient(label_root):
    label_root("_p5_report.json", {"lane": "tick", "outcomes": [
        _outcome("A", 0.30, 0.15), _outcome("B", 0.30, 0.15), _outcome("C", 0.30, 0.15),
    ]})
    result = api.transfer_estimate(map_expectancy_pct=0.40)
    assert result["available"] is True
    assert result["coefficient"] == pytest.approx(0.5)
    assert result["engine_estimate_pct"] == pytest.approx(0.20)


def test_malformed_report_is_skipped(label_root, tmp_path):
    (tmp_path / "design_v3").mkdir(exist_ok=True)
    (tmp_path / "design_v3" / "_p5_broken_report.json").write_text("{not json", encoding="utf-8")
    label_root("_p5_report.json", {"lane": "tick", "outcomes": [_outcome("A", 0.30, 0.15)]})

    payload = api.transfer_ledger()
    assert payload["record_count"] == 1     # 깨진 파일은 조용히 건너뛴다(예외 없음)
