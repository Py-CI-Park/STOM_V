"""P4 (2026-06-12) — 오더플로우 원리 템플릿 3호: orderflow_f04_absorption.

v5.0 보고서 '구조 차용'(임계 이식 금지) 3번째 적용 — 로드맵 §B 2순위.
F04 매도흡수재돌파: 최근 10초 매도 출회가 우위였는데(흡수 대상) 가격이
시가권을 방어하고 **지금 이 순간 매수가 받아치며 신고가를 재돌파**하는
순간을 잡는다. F14(매도벽소화)의 매수 공격 우위를 돌파 확인자로 결합.

전략적 의미: 시드(순수 매수 모멘텀)와 **같은 시간창에서 다른 메커니즘**
(매도 흡수) — 같은 시간대 내 상관 분리 분산 후보. window_end 축(09:03~
09:15)이 시간 확장 실험을 겸한다(시드 종료 09:05 너머 응답 측정).

계산 안전: 유계 윈도우 함수만(누적초당×2·최고현재가·초당거래대금평균),
역스캔 0회, 시프트는 과거 방향(1)만 — N4 가드가 전 좌표 재검증.
실행: PYTHONUTF8=1 python .omo/evidence/tmap-walkforward/build_f04_template.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.tmap.template import (  # noqa: E402
    load_template,
    render,
    validate_rendered,
)

OUT = REPO / "ai_strategy_loop/tmap/templates/orderflow_f04_absorption.json"

BUY_TEMPLATE = """\
# ================================
#  F04 매도흡수재돌파 + F14 매도벽소화 (P4 구조 차용)
#  창: 09:00:30~ — 시드와 같은 시간, 다른 메커니즘(매도 출회 흡수 후 재돌파)
# ================================
VI아래5호가 = VI가격 - VI호가단위 * 5
매수 = True

if not (관심종목 == 1):
    매수 = False
elif not ({window_start} <= 시분초 < {window_end}):
    매수 = False
elif not (1000 < 현재가 <= 50000):
    매수 = False
elif not (0.5 < 등락율 <= 20.0):
    매수 = False
elif not (시가총액 < {cap_max}):
    매수 = False
elif not (현재가 < VI아래5호가):
    매수 = False
elif 라운드피겨위5호가이내:
    매수 = False
elif not (누적초당매도수량(10) >= 누적초당매수수량(10) * {sell_dom}):
    매수 = False                                  # F04 — 매도 출회 존재(흡수 대상)
elif not (현재가 >= 시가 - 호가단위 * {open_band}):
    매수 = False                                  # F04 — 시가권 방어(흡수 성공 증거)
elif not (현재가 > 최고현재가({brk_window}, 1)):
    매수 = False                                  # F04 — 고가 재돌파
elif not (초당거래대금 > 초당거래대금평균({brk_window}, 1) * {vol_mult}):
    매수 = False                                  # F04 — 거래대금 동반
elif not (초당매수수량 > 초당매도수량 * {atk_ratio}):
    매수 = False                                  # F14 — 돌파 순간 매수 공격 우위
elif not (체결강도 >= {strength_min}):
    매수 = False

if 매수:
    self.Buy()
"""

SELL_TEMPLATE = """\
# ================================
#  F04 니치 청산 — 스칼라 전용(계산예산 안전)
# ================================
매도 = False

if 등락율 > 29.5:
    매도 = True
elif 수익률 >= {take_hard} or 수익률 <= {stop_hard}:
    매도 = True
elif 보유시간 >= {max_hold_sec}:
    매도 = True
elif 최고수익률 > 4 and 최고수익률 * 0.6 >= 수익률:
    매도 = True

if 매도:
    self.Sell()
"""

PARAMS = [
    {"name": "window_start", "default": 90030, "values": [90010, 90030, 90100],
     "side": "buy", "note": "F04 창 시작 — 흡수 관측에 10틱 필요"},
    {"name": "window_end", "default": 90500, "values": [90300, 90500, 91000, 91500],
     "side": "buy", "note": "창 종료 — **시간 확장 축**(시드 종료 09:05 너머 응답)"},
    {"name": "cap_max", "default": 3000, "values": [1500, 2500, 3000, 5000],
     "side": "buy", "note": "시총 상한(억) — 챔피언 mesa(2500) 좌표 포함"},
    {"name": "sell_dom", "default": 0.75, "values": [0.5, 0.75, 1.0, 1.3],
     "side": "buy", "note": "F04 매도 출회 강도(매도/매수 10초 누적 비율 하한)"},
    {"name": "open_band", "default": 2, "values": [0, 2, 5],
     "side": "buy", "note": "시가 방어 밴드(호가단위 배수 — 0=시가 위만)"},
    {"name": "brk_window", "default": 10, "values": [5, 10, 30],
     "side": "buy", "note": "재돌파 기준 신고가/거래대금 평균 창(틱)"},
    {"name": "vol_mult", "default": 2.0, "values": [1.5, 2.0, 3.0],
     "side": "buy", "note": "F04 돌파 거래대금 배수"},
    {"name": "atk_ratio", "default": 1.0, "values": [0.8, 1.0, 1.5],
     "side": "buy", "note": "F14 돌파 틱 매수/매도 공격 배수"},
    {"name": "strength_min", "default": 100, "values": [90, 100, 120],
     "side": "buy", "note": "체결강도 하한"},
    {"name": "take_hard", "default": 5, "values": [3, 5, 7],
     "side": "sell", "note": "하드 익절"},
    {"name": "stop_hard", "default": -3.0, "values": [-2.0, -3.0, -5.0],
     "side": "sell", "note": "하드 손절"},
    {"name": "max_hold_sec", "default": 300, "values": [120, 300, 600],
     "side": "sell", "note": "시간 청산 — 흡수 실패 시 빠른 이탈 기본"},
]


def main() -> int:
    defaults = {p["name"]: p["default"] for p in PARAMS}
    buy = BUY_TEMPLATE.format(**defaults)
    sell = SELL_TEMPLATE.format(**defaults)
    errors = validate_rendered(buy, sell, "tick")
    assert errors == [], f"기본값 렌더 가드 실패: {errors}"
    for p in PARAMS:
        for v in p["values"]:
            theta = {**defaults, p["name"]: v}
            errs = validate_rendered(
                BUY_TEMPLATE.format(**theta), SELL_TEMPLATE.format(**theta), "tick"
            )
            assert errs == [], f"{p['name']}={v} 가드 실패: {errs}"

    spec = {
        "name": "orderflow_f04_absorption",
        "timeframe": "tick",
        "source": "v5.0 보고서 F04+F14 구조 차용 (P4 — 로드맵 §B 2순위)",
        "description": (
            "P4 오더플로우 원리 템플릿 — F04 매도흡수재돌파(10초 매도 우위가"
            " 흡수되며 신고가 재돌파) + F14 돌파 틱 매수 공격 확인. 시드와 같은"
            " 창의 역신호 니치 + window_end 시간 확장 축(09:03~09:15)."
            " 12θ, 유계 윈도우 4회·역스캔 0."
        ),
        "buy_code": BUY_TEMPLATE,
        "sell_code": SELL_TEMPLATE,
        "params": PARAMS,
    }
    OUT.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")

    rebuilt = load_template("orderflow_f04_absorption")
    b2, s2 = render(rebuilt, {})
    assert b2 == buy and s2 == sell, "재로드 identity 실패"
    n_points = 1 + sum(len(p["values"]) - 1 for p in PARAMS)
    print(f"OK orderflow_f04_absorption: {len(PARAMS)}θ, 좌표 {n_points}점 -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
