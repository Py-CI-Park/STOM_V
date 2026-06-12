"""P4 (2026-06-12) — 오더플로우 원리 템플릿 4호: orderflow_f18_reentry.

v5.0 보고서 '구조 차용'(임계 이식 금지) 4번째 적용 — 로드맵 §B 3순위
(F18+F03 묶음). F18 시가상단재진입: **과거에 시가 아래로 눌렸던**(되돌림
존재) 종목이 거래대금·매수 공격을 동반하며 시가 위로 재진입하는 순간.
F03 강갭눌림회복의 저점 회복 폭 조건을 확인자로 결합한다.

전략적 의미: 모멘텀(시드)·흡수(F04)와 다른 **되돌림-재진입 계열** —
시드가 추격하는 첫 돌파가 아니라 '한 번 실패했다 살아나는' 두 번째 기회를
잡는다. window 축(09:00:30~09:15)이 시간 확장 실험을 겸한다.

계산 안전: 유계 윈도우 함수만(현재가N·최저현재가·초당거래대금평균),
역스캔 0회 — N4 가드가 전 좌표 재검증.
실행: PYTHONUTF8=1 python .omo/evidence/tmap-walkforward/build_f18_template.py
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

OUT = REPO / "ai_strategy_loop/tmap/templates/orderflow_f18_reentry.json"

BUY_TEMPLATE = """\
# ================================
#  F18 시가상단재진입 + F03 눌림회복 (P4 구조 차용 — 되돌림-재진입 계열)
#  과거 시가 아래 눌림 → 거래대금·매수 동반 시가 위 재진입
# ================================
VI아래5호가 = VI가격 - VI호가단위 * 5
매수 = True

if not (관심종목 == 1):
    매수 = False
elif not ({window_start} <= 시분초 < {window_end}):
    매수 = False
elif not (1000 < 현재가 <= 50000):
    매수 = False
elif not ({chg_min} < 등락율 <= 20.0):
    매수 = False
elif not (시가총액 < {cap_max}):
    매수 = False
elif not (현재가 < VI아래5호가):
    매수 = False
elif 라운드피겨위5호가이내:
    매수 = False
elif not (현재가N({dip_lookback}) < 시가):
    매수 = False                                  # F18 — 과거 시가 아래(되돌림 존재)
elif not (현재가 >= 시가 + 호가단위 * {reentry_band}):
    매수 = False                                  # F18 — 지금은 시가 위 재진입
elif not (현재가 >= 최저현재가({dip_lookback}) + 호가단위 * {recover_ticks}):
    매수 = False                                  # F03 — 저점 대비 회복 폭
elif not (초당거래대금 > 초당거래대금평균(30, 1) * {vol_mult}):
    매수 = False                                  # F18 — 거래대금 동반
elif not (초당매수수량 > 초당매도수량 * {atk_ratio}):
    매수 = False                                  # F18 — 매수 공격 우위
elif not (체결강도 >= {strength_min}):
    매수 = False

if 매수:
    self.Buy()
"""

SELL_TEMPLATE = """\
# ================================
#  F18 니치 청산 — 스칼라 전용(계산예산 안전)
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
    {"name": "window_start", "default": 90100, "values": [90030, 90100, 90200],
     "side": "buy", "note": "창 시작 — F03(09:00대)~F18(09:02) 영역"},
    {"name": "window_end", "default": 91000, "values": [90500, 91000, 91500],
     "side": "buy", "note": "창 종료 — **시간 확장 축**(09:05~09:15)"},
    {"name": "cap_max", "default": 3000, "values": [1500, 2500, 3000, 5000],
     "side": "buy", "note": "시총 상한(억)"},
    {"name": "chg_min", "default": 1.0, "values": [0.5, 1.0, 2.0],
     "side": "buy", "note": "등락율 하한 — 되돌림 후에도 양봉권 유지"},
    {"name": "dip_lookback", "default": 30, "values": [10, 30, 60],
     "side": "buy", "note": "되돌림 관측 과거 틱 수(유계)"},
    {"name": "reentry_band", "default": 1, "values": [1, 2, 3],
     "side": "buy", "note": "재진입 확인 밴드(시가+호가단위 배수)"},
    {"name": "recover_ticks", "default": 3, "values": [2, 3, 5],
     "side": "buy", "note": "F03 저점 대비 회복 호가 수"},
    {"name": "vol_mult", "default": 2.0, "values": [1.5, 2.0, 3.0],
     "side": "buy", "note": "재진입 거래대금 배수(30틱 평균 대비)"},
    {"name": "atk_ratio", "default": 1.2, "values": [1.0, 1.2, 1.5],
     "side": "buy", "note": "매수/매도 공격 배수"},
    {"name": "strength_min", "default": 100, "values": [90, 100, 120],
     "side": "buy", "note": "체결강도 하한"},
    {"name": "take_hard", "default": 5, "values": [3, 5, 7],
     "side": "sell", "note": "하드 익절"},
    {"name": "stop_hard", "default": -3.0, "values": [-2.0, -3.0, -5.0],
     "side": "sell", "note": "하드 손절 — 재진입 실패는 빠르게"},
    {"name": "max_hold_sec", "default": 300, "values": [120, 300, 600],
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
        "name": "orderflow_f18_reentry",
        "timeframe": "tick",
        "source": "v5.0 보고서 F18+F03 구조 차용 (P4 — 로드맵 §B 3순위)",
        "description": (
            "P4 오더플로우 원리 템플릿 — F18 시가상단재진입(과거 시가 아래"
            " 눌림 후 거래대금·매수 동반 시가 위 재진입) + F03 저점 회복 폭"
            " 확인. 되돌림-재진입 계열(모멘텀·흡수와 상이) + window 시간"
            " 확장 축. 13θ, 유계 윈도우 3회·역스캔 0."
        ),
        "buy_code": BUY_TEMPLATE,
        "sell_code": SELL_TEMPLATE,
        "params": PARAMS,
    }
    OUT.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")

    rebuilt = load_template("orderflow_f18_reentry")
    b2, s2 = render(rebuilt, {})
    assert b2 == buy and s2 == sell, "재로드 identity 실패"
    n_points = 1 + sum(len(p["values"]) - 1 for p in PARAMS)
    print(f"OK orderflow_f18_reentry: {len(PARAMS)}θ, 좌표 {n_points}점 -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
