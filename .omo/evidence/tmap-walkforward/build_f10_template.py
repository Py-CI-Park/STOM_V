"""P4 2순위 (2026-06-11) — F10 대형주추세 템플릿: orderflow_f10_largecap_trend.

로드맵(2026-06-11_f_principles_templating_roadmap.md) 1순위: F10은 시드와
**종목군(대형주)·시간(09:05~25)·메커니즘(추세 지속)** 전부 독립 — 포트폴리오
분산 가치 최대. F20(오더플로우 지속 — 누적 매수우위)을 보조 필터로 결합.

계산 안전: 이동평균 3회·누적 2회(전부 유계 윈도우), 역스캔 0회.
실행: PYTHONUTF8=1 python .omo/evidence/tmap-walkforward/build_f10_template.py
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

OUT = REPO / "ai_strategy_loop/tmap/templates/orderflow_f10_largecap_trend.json"

BUY_TEMPLATE = """\
# ================================
#  F10 대형주추세 + F20 오더플로우지속 (P4 구조 차용 — 시드와 완전 독립 니치)
# ================================
매수 = True

if not (관심종목 == 1):
    매수 = False
elif not (90500 <= 시분초 < {window_end}):
    매수 = False
elif not (시가총액 >= {cap_min}):
    매수 = False                                  # F10 — 대형주(시드와 종목군 분리)
elif not (0.5 < 등락율 <= {chg_max}):
    매수 = False
elif not (현재가 > 이동평균({ma_window})):
    매수 = False                                  # F10 — 이평 위 추세
elif not (이동평균({ma_window}) > 이동평균({ma_window}, {ma_shift})):
    매수 = False                                  # F10 — 이평 자체가 상승 중
elif not (누적초당매수수량(30) > 누적초당매도수량(30) * {flow_ratio}):
    매수 = False                                  # F20 — 매수 오더플로우 지속
elif not (체결강도 >= {strength_min}):
    매수 = False

if 매수:
    self.Buy()
"""

SELL_TEMPLATE = """\
# ================================
#  F10 니치 청산 — 스칼라 전용(대형주: 타이트 익절·손절 기본값)
# ================================
매도 = False

if 등락율 > 29.5:
    매도 = True
elif 수익률 >= {take_hard} or 수익률 <= {stop_hard}:
    매도 = True
elif 보유시간 >= {max_hold_sec}:
    매도 = True
elif 최고수익률 > 2 and 최고수익률 * 0.6 >= 수익률:
    매도 = True

if 매도:
    self.Sell()
"""

PARAMS = [
    {"name": "window_end", "default": 92500, "values": [91500, 92000, 92500],
     "side": "buy", "note": "F10 창 종료(09:15~25) — 시간 확대 축"},
    {"name": "cap_min", "default": 10000, "values": [5000, 10000, 20000],
     "side": "buy", "note": "시총 하한(억) — 시드(상한 2500)와 종목군 완전 분리"},
    {"name": "chg_max", "default": 10, "values": [5, 10, 15],
     "side": "buy", "note": "등락율 상한 — 대형주 과열 배제"},
    {"name": "ma_window", "default": 60, "values": [30, 60, 120],
     "side": "buy", "note": "F10 추세 이평 틱 수(유계)"},
    {"name": "ma_shift", "default": 30, "values": [10, 30, 60],
     "side": "buy", "note": "이평 상승 판정 시프트(과거 방향 — N4 안전)"},
    {"name": "flow_ratio", "default": 1.0, "values": [0.8, 1.0, 1.2, 1.5],
     "side": "buy", "note": "F20 누적 매수/매도 우위 배수"},
    {"name": "strength_min", "default": 100, "values": [90, 100, 120],
     "side": "buy", "note": "체결강도 하한"},
    {"name": "take_hard", "default": 3, "values": [2, 3, 5],
     "side": "sell", "note": "익절 — 대형주는 변동폭 작아 타이트 기본값"},
    {"name": "stop_hard", "default": -2.0, "values": [-1.5, -2.0, -3.0],
     "side": "sell", "note": "손절"},
    {"name": "max_hold_sec", "default": 600, "values": [300, 600, 1200],
     "side": "sell", "note": "시간 청산"},
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
        "name": "orderflow_f10_largecap_trend",
        "timeframe": "tick",
        "source": "v5.0 보고서 F10+F20 구조 차용 (P4 — 로드맵 1순위)",
        "description": (
            "F10 대형주추세 — 시드와 종목군(시총 1조+ vs 2500억-)·시간(09:05~25)·"
            "메커니즘(추세 지속 vs 모멘텀 폭발) 전부 독립인 분산 니치. F20 누적"
            " 매수우위 보조. 10θ, 윈도우 함수 5회(전부 유계)·역스캔 0."
        ),
        "buy_code": BUY_TEMPLATE,
        "sell_code": SELL_TEMPLATE,
        "params": PARAMS,
    }
    OUT.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")

    rebuilt = load_template("orderflow_f10_largecap_trend")
    b2, s2 = render(rebuilt, {})
    assert b2 == buy and s2 == sell, "재로드 identity 실패"
    n_points = 1 + sum(len(p["values"]) - 1 for p in PARAMS)
    print(f"OK orderflow_f10_largecap_trend: {len(PARAMS)}θ, 좌표 {n_points}점 -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
