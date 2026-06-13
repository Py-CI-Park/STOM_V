"""T2 (2026-06-13) — 3분기 차등 구조: seed_902905_t2late.

T3 부검 실측 설계: 09:05 이후 한계 거래는 시총 2,500억+ 만 흑자(+230만,
승률 47.4%) — 초반과 정반대. 제3분기(90500~{ext_end})를 추가하되 시총
밴드를 반전({cap_lo_late}~{cap_hi_late})시킨다. 초반 2분기는 THETA θ 고정.
신규 구조 → 스모크 2-분기 규약 적용 대상.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.tmap.template import load_template, render, validate_rendered  # noqa: E402

OUT = REPO / "ai_strategy_loop/tmap/templates/seed_902905_t2late.json"
THETA = {"cap_max": 2500, "take_hard": 9, "trail_start": 4}

def main() -> int:
    t = load_template("seed_902905")
    buy, sell = render(t, THETA)
    lines = buy.splitlines()
    # 분기2 블록 추출: 'elif 90200 <= 시분초 < 90500:' 부터 'if 매수:' 직전까지
    i2 = next(i for i, ln in enumerate(lines) if ln.startswith("elif 90200 <= 시분초 < 90500:"))
    # 삽입점: 말미 'else:'(09:05 이후 차단) 직전 주석 줄 — elif는 else 앞이어야 한다
    iend = next(i for i, ln in enumerate(lines) if "09:05:00 이후" in ln)
    block = lines[i2:iend]
    # 빈 꼬리 제거
    while block and not block[-1].strip():
        block.pop()
    late = []
    for ln in block:
        s = ln
        s = s.replace("elif 90200 <= 시분초 < 90500:", "elif 90500 <= 시분초 < {ext_end}:")
        s = s.replace("if 시가총액 < 2500:", "if {cap_lo_late} <= 시가총액 < {cap_hi_late}:")
        s = s.replace("초당거래대금 / 초당거래대금평균(30) > 2.0", "초당거래대금 / 초당거래대금평균(30) > {burst_late}")
        late.append(s)
    assert any("{ext_end}" in s for s in late) and any("{cap_lo_late}" in s for s in late) and any("{burst_late}" in s for s in late)
    code = "\n".join(lines[:iend] + late + [""] + lines[iend:])
    PARAMS = [
        {"name": "ext_end", "default": 92000, "values": [91000, 91500, 92000, 92500], "side": "buy", "note": "제3분기 종료 — 09:10~09:25"},
        {"name": "cap_lo_late", "default": 2500, "values": [1500, 2500, 4000], "side": "buy", "note": "후반 시총 하한 — T3 부검 반전 설계"},
        {"name": "cap_hi_late", "default": 20000, "values": [10000, 20000, 99999], "side": "buy", "note": "후반 시총 상한"},
        {"name": "burst_late", "default": 2.0, "values": [2.0, 3.0, 4.0], "side": "buy", "note": "후반 거래대금 폭발(상향 여지)"},
    ]
    defaults = {p["name"]: p["default"] for p in PARAMS}
    base = code.format(**defaults)
    errs = validate_rendered(base, sell, "tick")
    assert errs == [], errs
    for p in PARAMS:
        for v in p["values"]:
            th = {**defaults, p["name"]: v}
            es = validate_rendered(code.format(**th), sell, "tick")
            assert es == [], (p["name"], v, es)
    spec = {"name": "seed_902905_t2late", "timeframe": "tick",
            "source": "T2 — 3분기 차등(시총 반전) 구조, T3 부검 실측 설계",
            "description": "THETA(09:05까지 소형) + 제3분기 09:05~{ext_end} 시총 2500+ 반전. 4θ.",
            "buy_code": code, "sell_code": sell, "params": PARAMS}
    OUT.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    n = 1 + sum(len(p["values"]) - 1 for p in PARAMS)
    print(f"OK seed_902905_t2late: {len(PARAMS)}θ, {n}점")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
