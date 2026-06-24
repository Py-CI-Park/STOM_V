"""P5 — 청산 포렌식 확장: Exit Regret(조기청산 후회) · False-Break(가짜 돌파).

analyze_exits에 가법 산출(기존 소비자는 신규 필드 무시 → byte-identical), summarize_exits는
토글(exit_forensics_feedback_enabled) ON일 때만 포렌식 라인을 덧붙인다(OFF면 byte-동일).
신호는 R_매수후최고/최저수익률(R_MFE/R_MAE) + 수익률에서 산출 — 모두 결과 CSV에 존재.
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
from ai_strategy_loop.autopsy.analyze import analyze_exits  # noqa: E402
from ai_strategy_loop.autopsy.summarize import summarize_exits  # noqa: E402
from ai_strategy_loop.config import LoopConfig  # noqa: E402


def _make_csv(path: Path) -> str:
    """수익률 + R_MFE/R_MAE 픽스처. 수익거래 10(조기청산 5/정상 5), 손실거래 10(가짜돌파 6/정상 4)."""
    rows = []
    # 수익거래: 조기청산 후회 5건(MFE 5.0, 실현 1.0 = 고점 20%만 지킴).
    for _ in range(5):
        rows.append((1.0, 5.0, -0.5))
    # 수익거래: 정상 5건(MFE 3.0, 실현 2.8 = 고점 93% 지킴 → 후회 아님).
    for _ in range(5):
        rows.append((2.8, 3.0, -0.3))
    # 손실거래: 가짜 돌파 6건(MFE 0.2 = 한 번도 못 오름).
    for _ in range(6):
        rows.append((-2.0, 0.2, -2.5))
    # 손실거래: 올랐다가 실패 4건(MFE 3.0 = 돌파는 했음).
    for _ in range(4):
        rows.append((-1.0, 3.0, -1.5))
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "종목명", "수익률", "R_매수후최고수익률", "R_매수후최저수익률", "보유시간", "매도조건",
        ])
        w.writeheader()
        for i, (ret, mfe, mae) in enumerate(rows):
            w.writerow({
                "종목명": "T", "수익률": ret,
                "R_매수후최고수익률": mfe, "R_매수후최저수익률": mae,
                "보유시간": 30, "매도조건": "수익률 >= 5",
            })
    return str(path)


def test_analyze_exits_computes_regret_and_false_break(tmp_path) -> None:
    r = analyze_exits(_make_csv(tmp_path / "bt.csv"), min_trades=10)
    assert r.status == "ok"
    # Exit Regret: 익절기회 있던 수익거래 10건 중 5건이 고점 절반도 못 지킴 → 0.5.
    assert r.exit_regret_eligible == 10
    assert abs(r.exit_regret_ratio - 0.5) < 1e-9
    # 평균 후회폭 = mean(MFE-실현) = ((5-1)*5 + (3-2.8)*5)/10 = 2.1.
    assert abs(r.avg_exit_regret - 2.1) < 1e-6
    # False-Break: 손실거래 10건 중 6건이 +0.5% 미만(가짜돌파) → 0.6.
    assert r.false_break_losers == 6
    assert abs(r.false_break_ratio - 0.6) < 1e-9


def test_summarize_exits_off_is_byte_identical(tmp_path) -> None:
    r = analyze_exits(_make_csv(tmp_path / "bt.csv"), min_trades=10)
    base = summarize_exits(r, None)
    off = summarize_exits(r, LoopConfig())  # 토글 기본 OFF.
    assert base == off
    assert "조기청산 후회" not in base and "가짜 돌파" not in base


def test_summarize_exits_on_appends_forensic_lines(tmp_path) -> None:
    r = analyze_exits(_make_csv(tmp_path / "bt.csv"), min_trades=10)
    cfg = LoopConfig.from_dict({"exit_forensics_feedback_enabled": True})
    text = summarize_exits(r, cfg)
    assert "조기청산 후회" in text
    assert "가짜 돌파" in text


def test_exit_forensics_graceful_without_mfe(tmp_path) -> None:
    # R_MFE 컬럼이 없으면 포렌식 필드는 0으로 두고 예외 없이 ok.
    p = tmp_path / "nomfe.csv"
    p.write_text("수익률\n1.0\n-1.0\n" * 1, encoding="utf-8-sig")
    rows = "\n".join(["수익률"] + ["1.0", "-1.0"] * 10)
    p.write_text(rows + "\n", encoding="utf-8-sig")
    r = analyze_exits(str(p), min_trades=5)
    assert r.exit_regret_eligible == 0
    assert r.false_break_losers == 0
    assert r.false_break_ratio == 0.0
