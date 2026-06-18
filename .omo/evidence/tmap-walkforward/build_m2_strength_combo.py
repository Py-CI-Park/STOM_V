"""M2 (2026-06-13) — min 결합 구조: min_p4_strength_combo.

M1 지도 결론: 6 프리미티브 중 P4강도급등(체결강도>평균 + 매수우위)만 빈도가
자연 통제되고 12시대 손익분기 근접. M2 = P4 코어 + 신고가 돌파 + 빈도축
(분당거래대금)으로 승률 보강. 11~14시 진입, 강제청산 14:59.
스모크 2-분기 규약(2025-05 + 2025-09) 대상. 모든 임계값 params 슬롯.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.tmap.template import load_template, render, validate_rendered  # noqa: E402

OUT = REPO / "ai_strategy_loop/tmap/templates/min_p4_strength_combo.json"

BUY = """\
# min P4강도급등 결합 — 11~14시, 강제청산은 매도부
매수 = True
if not (관심종목 == 1):
    매수 = False
elif not ({entry_start} <= 시분초 < {entry_end}):
    매수 = False
elif not (데이터길이 >= 31):
    매수 = False
elif not (1000 < 현재가 <= 100000):
    매수 = False
elif not ({rate_min} <= 등락율 <= {rate_max}):
    매수 = False
elif not (시가총액 <= {cap_max}):
    매수 = False
elif not (체결강도 > 체결강도평균({strength_win}, 1) * {strength_mult}):
    매수 = False                                  # P4 코어 — 강도 급등
elif not (분당매수수량 > 분당매도수량 * {buy_dom}):
    매수 = False                                  # P4 코어 — 매수 우위
elif not (현재가 > 최고현재가({high_win}, 1)):
    매수 = False                                  # 보조 — 신고가 돌파
elif not (분당거래대금 > 분당거래대금평균({money_win}, 1) * {money_mult}):
    매수 = False                                  # 빈도축 — 대금 동반

if 매수:
    self.Buy()
"""

SELL = """\
매도 = False
if 시분초 >= 145900:
    매도 = True                                   # 강제청산 14:59
elif 수익률 >= {take_rate} or 수익률 <= {stop_rate}:
    매도 = True
elif 보유시간 >= {hold_max}:
    매도 = True
elif 최고수익률 > {trail_arm} and 최고수익률 * {trail_keep} >= 수익률:
    매도 = True
if 매도:
    self.Sell()
"""

PARAMS = [
    {"name": "entry_start", "default": 110000, "values": [100000, 110000, 120000, 130000], "side": "buy", "note": "진입창 시작(11~13시)"},
    {"name": "entry_end", "default": 143000, "values": [140000, 143000, 144500], "side": "buy", "note": "진입창 종료"},
    {"name": "rate_min", "default": 1.0, "values": [0.0, 1.0, 2.0], "side": "buy", "note": ""},
    {"name": "rate_max", "default": 20.0, "values": [12.0, 20.0, 28.0], "side": "buy", "note": ""},
    {"name": "cap_max", "default": 5000, "values": [2000, 5000, 20000], "side": "buy", "note": "시총 상한(억)"},
    {"name": "strength_win", "default": 20, "values": [10, 20, 30], "side": "buy", "note": "체결강도 평균 창"},
    {"name": "strength_mult", "default": 1.2, "values": [1.1, 1.2, 1.4], "side": "buy", "note": "P4 강도 급등 배수"},
    {"name": "buy_dom", "default": 1.2, "values": [1.0, 1.2, 1.5], "side": "buy", "note": "매수 우위 배수"},
    {"name": "high_win", "default": 30, "values": [15, 30, 60], "side": "buy", "note": "신고가 창(분)"},
    {"name": "money_win", "default": 20, "values": [10, 20, 30], "side": "buy", "note": "대금 평균 창"},
    {"name": "money_mult", "default": 2.0, "values": [1.5, 2.0, 3.0], "side": "buy", "note": "빈도축 — 대금 폭발 배수"},
    {"name": "take_rate", "default": 5.0, "values": [3.0, 5.0, 7.0], "side": "sell", "note": "익절"},
    {"name": "stop_rate", "default": -3.0, "values": [-2.0, -3.0, -4.0], "side": "sell", "note": "손절"},
    {"name": "hold_max", "default": 3600, "values": [1800, 3600, 7200], "side": "sell", "note": "보유 상한(초)"},
    {"name": "trail_arm", "default": 3.0, "values": [2.0, 3.0, 4.0], "side": "sell", "note": "트레일 발동 수익률"},
    {"name": "trail_keep", "default": 0.6, "values": [0.5, 0.6, 0.7], "side": "sell", "note": "트레일 유지 비율"},
]

def main() -> int:
    defaults = {p["name"]: p["default"] for p in PARAMS}
    buy = BUY.format(**defaults)
    sell = SELL.format(**defaults)
    errs = validate_rendered(buy, sell, "min")
    assert errs == [], errs
    for p in PARAMS:
        for v in p["values"]:
            th = {**defaults, p["name"]: v}
            es = validate_rendered(BUY.format(**th), SELL.format(**th), "min")
            assert es == [], (p["name"], v, es)
    spec = {"name": "min_p4_strength_combo", "timeframe": "min",
            "source": "M2 — M1 P4강도급등 코어 + 신고가 + 빈도축 결합",
            "description": "min 11~14시 강도급등 결합 구조. 16θ, 강제청산 14:59.",
            "buy_code": BUY, "sell_code": SELL, "params": PARAMS}
    OUT.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    n = 1 + sum(len(p["values"]) - 1 for p in PARAMS)
    print(f"OK min_p4_strength_combo: {len(PARAMS)}θ, {n}점")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
