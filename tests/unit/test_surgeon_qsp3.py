# -*- coding: utf-8 -*-
"""QSP3 P1 — 리프 대수술(drop_leaf) 제안·적용·검증 테스트."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ai_strategy_loop.revision import surgeon
from ai_strategy_loop.revision.hier_ast import parse_leaves

SEED = Path("docs/research/quant_scoring_pipeline/seed_drafts/QSP2_T_ANCH_900_920_B.py")
CODE = SEED.read_text(encoding="utf-8")
TARGET_LEAF = ("시분초<90200", "시가총액<3000")   # B1×소형
SPEC = {"action": "drop_leaf", "leaf": list(TARGET_LEAF), "leaf_label": "B1_900_902×S_3000미만"}


def test_apply_and_verify_drop_roundtrip():
    new_code, reason = surgeon.apply_drop(SPEC, CODE)
    assert new_code, reason
    ok, why = surgeon.verify_drop(SPEC, CODE, new_code)
    assert ok, why
    assert surgeon.is_dropped(new_code, TARGET_LEAF)
    # 다른 리프는 그대로.
    h = parse_leaves(new_code)
    other = ("시분초<90200", "3000<=시가총액<5000")
    assert h.leaves[other][0].ident != "?"


def test_verify_drop_rejects_out_of_scope_change():
    new_code, _ = surgeon.apply_drop(SPEC, CODE)
    tampered = new_code.replace("0.5 <= 등락율 <= 22.0", "0.5 <= 등락율 <= 44.0", 1)
    assert tampered != new_code  # 다른 리프(B1×중소)의 상수 변조.
    ok, why = surgeon.verify_drop(SPEC, CODE, tampered)
    assert not ok, why  # 라인 diff 가드 또는 리프 대조 어느 쪽이든 거부되면 된다.


def test_apply_drop_refuses_already_dropped():
    new_code, _ = surgeon.apply_drop(SPEC, CODE)
    again, reason = surgeon.apply_drop(SPEC, new_code)
    assert again is None and "이미" in reason


def _csv(path, rows):
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    return str(path)


def _mk_rows(cap, pnl_each, n, hhmmss="090105"):
    return [{
        "종목명": f"X{cap}", "시가총액": cap, "매수시간": f"20250407{hhmmss}",
        "수익률": 0.1 if pnl_each > 0 else -0.1, "수익금": pnl_each,
        "B_현재가": 10000, "B_등락율": 5.0, "B_매수총잔량": 100, "B_매도총잔량": 100,
        "B_당일거래대금": 100, "B_시가총액": cap, "B_체결강도": 100,
        "B_전일동시간비": 1.0,
    } for _ in range(n)]


def test_propose_drops_requires_both_windows_losing(tmp_path):
    # B1×소형: 설계·홀드 모두 손실 → 후보. B1×중소: 설계만 손실 → 제외(가짜 판단 방지).
    design = _mk_rows(1000, -10_000, 40) + _mk_rows(4000, -8_000, 40)
    hold = _mk_rows(1000, -12_000, 40) + _mk_rows(4000, +9_000, 40)
    d = _csv(tmp_path / "d.csv", design)
    h = _csv(tmp_path / "h.csv", hold)
    specs = surgeon.propose_drops(d, h, CODE, top_k=3, timeframe="tick")
    labels = [s["leaf_label"] for s in specs]
    assert any("S_3000미만" in l for l in labels), labels
    assert not any("M1_3000_5000" in l for l in labels), labels
    sp = specs[0]
    assert sp["action"] == "drop_leaf" and sp["est_delta_design"] > 0


def test_propose_drops_respects_exclude(tmp_path):
    design = _mk_rows(1000, -10_000, 40)
    hold = _mk_rows(1000, -12_000, 40)
    d = _csv(tmp_path / "d.csv", design)
    h = _csv(tmp_path / "h.csv", hold)
    base = surgeon.propose_drops(d, h, CODE, top_k=3, timeframe="tick")
    assert base
    again = surgeon.propose_drops(d, h, CODE, top_k=3, timeframe="tick",
                                  exclude_leaves={base[0]["leaf_label"]})
    assert all(s["leaf_label"] != base[0]["leaf_label"] for s in again)


def test_verify_drop_rejects_marker_forgery():
    """감사1호 BUG-Q3 — `if False:`/`if 0:` 위조 마커는 드롭으로 인정하지 않는다."""
    new_code, _ = surgeon.apply_drop(SPEC, CODE)
    forged = new_code.replace("if True:  # DROP_LEAF", "if False:  # DROP_LEAF", 1)
    assert forged != new_code
    ok, why = surgeon.verify_drop(SPEC, CODE, forged)
    assert not ok, "의미 반전(if False) 위조가 통과되면 안 된다"


def test_verify_drop_rejects_body_tamper():
    """감사1호 BUG-Q4 — 드롭 줄 외의 라인 변경(리프 본문 매수=True 등) 거부."""
    new_code, _ = surgeon.apply_drop(SPEC, CODE)
    lines = new_code.split(chr(10))
    for i, ln in enumerate(lines):
        if "DROP_LEAF" in ln:
            lines[i + 1] = lines[i + 1].replace("매수 = False", "매수 = True")
            break
    tampered = chr(10).join(lines)
    assert tampered != new_code
    ok, why = surgeon.verify_drop(SPEC, CODE, tampered)
    assert not ok, "본문 변조가 통과되면 안 된다"
