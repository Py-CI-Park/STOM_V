"""R1(2026-06-11) — 부검 분위수 임계 환류 테스트.

방향만 주는 부검("높여라/낮춰라")에 승자 분위수 임계 후보(숫자)를 병기하는 토글.
OFF(기본)면 summarize 출력이 기존과 byte-동일해야 한다(하위호환).
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.autopsy.analyze import analyze_trades  # noqa: E402
from ai_strategy_loop.autopsy.summarize import summarize  # noqa: E402
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.launch_config import config_field_specs  # noqa: E402


def _make_csv(path: Path, rows: list) -> str:
    """rows: [(수익률, 수익금, 시가총액, 체결강도)]"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "종목명", "매수시간", "매도시간", "수익률", "수익금", "B_시가총액", "B_체결강도",
        ])
        w.writeheader()
        for i, (pct, krw, cap, strength) in enumerate(rows):
            w.writerow({
                "종목명": "T", "매수시간": f"202301{(i % 28) + 1:02d}090100",
                "매도시간": f"202301{(i % 28) + 1:02d}090300",
                "수익률": pct, "수익금": krw, "B_시가총액": cap, "B_체결강도": strength,
            })
    return str(path)


def _fixture_csv(tmp_path: Path) -> str:
    # 승자: 시가총액 낮음(1000~1300)·체결강도 높음(150~180) / 패자: 반대.
    rows = []
    for i in range(15):
        rows.append((1.0, 100000, 1000 + i * 20, 150 + i * 2))   # 승자 15
        rows.append((-0.5, -50000, 3000 + i * 20, 100 + i * 2))  # 패자 15
    return _make_csv(tmp_path / "bt.csv", rows)


def test_config_default_off_and_spec() -> None:
    cfg = LoopConfig()
    assert cfg.quantile_feedback_enabled is False
    assert LoopConfig.from_dict({"quantile_feedback_enabled": True}).quantile_feedback_enabled is True
    names = {f["name"] for f in config_field_specs()}
    assert "quantile_feedback_enabled" in names


def test_analyze_trades_fills_winner_quantiles(tmp_path) -> None:
    result = analyze_trades(_fixture_csv(tmp_path), min_trades=10)
    assert result.status == "ok"
    cap = next(d for d in result.discriminators if d.column == "B_시가총액")
    assert cap.win_q25 is not None and cap.win_q50 is not None and cap.win_q75 is not None
    assert cap.win_q25 <= cap.win_q50 <= cap.win_q75
    # 승자 시가총액은 1000~1280 범위 — 분위수도 그 안.
    assert 1000 <= cap.win_q25 <= 1280


def test_summarize_off_is_byte_identical(tmp_path) -> None:
    result = analyze_trades(_fixture_csv(tmp_path), min_trades=10)
    base = summarize(result, None)
    off = summarize(result, LoopConfig())  # 기본 OFF
    assert base == off
    assert "후보" not in base  # 분위수 제안 미포함.


def test_summarize_on_appends_quantile_candidates(tmp_path) -> None:
    result = analyze_trades(_fixture_csv(tmp_path), min_trades=10)
    cfg = LoopConfig.from_dict({"quantile_feedback_enabled": True})
    text = summarize(result, cfg)
    # 시가총액(패자가 큼 → 낮춰라)엔 상한 후보, 체결강도(승자가 큼 → 높여라)엔 하한 후보.
    assert "상한 후보: ≤" in text
    assert "하한 후보: ≥" in text
    assert "승자 중앙값" in text
    assert "인샘플" in text  # 정직성 주의 문구.


def test_loop_default_autopsy_fn_respects_toggle(tmp_path) -> None:
    from ai_strategy_loop.controller.loop import _default_autopsy_fn

    csv_path = _fixture_csv(tmp_path)
    off_fb = _default_autopsy_fn(LoopConfig.from_dict({"min_trades": 10}))(csv_path)
    on_fb = _default_autopsy_fn(LoopConfig.from_dict({
        "min_trades": 10, "quantile_feedback_enabled": True,
    }))(csv_path)
    assert "후보" not in (off_fb or "")
    assert "하한 후보: ≥" in (on_fb or "")
