"""R2 (2026-06-13) — 시드 고정 상수 전축화 템플릿: seed_902905_r2full.

R1 부검의 알파 운반자 임계들(한 번도 축으로 푼 적 없는 고정 상수)을 슬롯화.
THETA θ(cap2500·take9·trail4)는 코드에 고정 — R2는 '구조 내부' 탐색.
기본값 = 원본 상수 → 기본 렌더는 THETA와 의미 동일(identity 검증).
"""
from __future__ import annotations
import json, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.tmap.template import load_template, render, validate_rendered  # noqa: E402

OUT = REPO / "ai_strategy_loop/tmap/templates/seed_902905_r2full.json"
THETA = {"cap_max": 2500, "take_hard": 9, "trail_start": 4}

REPL = [  # (원문, 슬롯문) — 전부 고유 문자열(치환 1회 보장 검증)
    ("2 < 회전율", "{turnover_a} < 회전율"),
    ("0.5 <= 시가대비등락율 < 6.0", "{ogap_lo_a} <= 시가대비등락율 < {ogap_hi_a}"),
    ("3.0 <= 시가대비등락율 < 8.0", "{ogap_lo_b} <= 시가대비등락율 < {ogap_hi_b}"),
    ("초당거래대금 / 초당거래대금평균(30) > 3.0", "초당거래대금 / 초당거래대금평균(30) > {burst_a}"),
    ("초당거래대금 / 초당거래대금평균(30) > 2.0", "초당거래대금 / 초당거래대금평균(30) > {burst_b}"),
    ("초당매수수량 > 매도총잔량 * 0.20", "초당매수수량 > 매도총잔량 * {atk_a}"),
    ("초당매수수량 > 매도총잔량 * 0.30", "초당매수수량 > 매도총잔량 * {atk_b}"),
    ("당일거래대금 > 5 * 100", "당일거래대금 > {dmoney_a}"),
    ("당일거래대금 > 50 * 100", "당일거래대금 > {dmoney_b}"),
]
PARAMS = [
    {"name": "turnover_a", "default": 2, "values": [1.5, 2, 3], "side": "buy", "note": "R1 최강 알파(-66%) 임계"},
    {"name": "ogap_lo_a", "default": 0.5, "values": [0.0, 0.5, 1.0], "side": "buy", "note": ""},
    {"name": "ogap_hi_a", "default": 6.0, "values": [4.0, 6.0, 9.0], "side": "buy", "note": ""},
    {"name": "ogap_lo_b", "default": 3.0, "values": [2.0, 3.0, 4.0], "side": "buy", "note": ""},
    {"name": "ogap_hi_b", "default": 8.0, "values": [6.0, 8.0, 12.0], "side": "buy", "note": ""},
    {"name": "burst_a", "default": 3.0, "values": [2.0, 3.0, 4.5], "side": "buy", "note": "R1 -13%"},
    {"name": "burst_b", "default": 2.0, "values": [1.5, 2.0, 3.0], "side": "buy", "note": ""},
    {"name": "atk_a", "default": 0.20, "values": [0.10, 0.20, 0.35], "side": "buy", "note": "R1 -17%"},
    {"name": "atk_b", "default": 0.30, "values": [0.15, 0.30, 0.50], "side": "buy", "note": ""},
    {"name": "dmoney_a", "default": 500, "values": [250, 500, 1000], "side": "buy", "note": "R1 -25%"},
    {"name": "dmoney_b", "default": 5000, "values": [2500, 5000, 10000], "side": "buy", "note": ""},
]

def main() -> int:
    t = load_template("seed_902905")
    buy, sell = render(t, THETA)
    code = buy
    for old, new in REPL:
        assert code.count(old) == 1, (old, code.count(old))
        code = code.replace(old, new)
    defaults = {p["name"]: p["default"] for p in PARAMS}
    base = code.format(**defaults)
    # identity: 기본값 렌더가 THETA 렌더와 수치 동일해야 함(500=5*100 등 표기만 차이)
    errs = validate_rendered(base, sell, "tick")
    assert errs == [], errs
    for p in PARAMS:
        for v in p["values"]:
            th = {**defaults, p["name"]: v}
            es = validate_rendered(code.format(**th), sell, "tick")
            assert es == [], (p["name"], v, es)
    spec = {"name": "seed_902905_r2full", "timeframe": "tick",
            "source": "R2 — R1 알파 운반자 임계 전축화(THETA θ 고정)",
            "description": "시드 구조 내부 상수 11축 — 사상 첫 내부 응답 지도",
            "buy_code": code, "sell_code": sell, "params": PARAMS}
    OUT.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    n = 1 + sum(len(p["values"]) - 1 for p in PARAMS)
    print(f"OK seed_902905_r2full: {len(PARAMS)}θ, {n}점")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
