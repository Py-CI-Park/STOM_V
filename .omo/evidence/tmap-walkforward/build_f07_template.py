"""C12/P4 (2026-06-11) — 오더플로우 원리 기반 신규 템플릿: orderflow_f07_ignition.

v5.0 보고서 원리의 '구조 차용'(임계 이식 실패 5/5의 교훈 — 숫자가 아니라
구조를 가져온다): F07 횡보후발화(09:05~09:20 횡보 후 거래대금 발화) 골격에
F06 체결강도호가압력·F11 전일동시간비를 보조 필터로 결합한다.

전략적 의미: 시드(09:00~09:05 모멘텀)의 **사각지대인 09:05 이후**를 덮는
독립 니치 — N6 시간분산 게이트가 "포트폴리오 결합에 필요"라고 증명한 그 조각.

계산 안전: 윈도우 함수 2회(등락율각도·초당거래대금평균 — 유계)·역스캔 0회.
모든 변수는 시드 코드에 등장하는 검증된 스코프만 사용(가드가 재검증).
실행: PYTHONUTF8=1 python .omo/evidence/tmap-walkforward/build_f07_template.py
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

OUT = REPO / "ai_strategy_loop/tmap/templates/orderflow_f07_ignition.json"

BUY_TEMPLATE = """\
# ================================
#  F07 횡보후발화 + F06 체결강도호가압력 + F11 전일동시간비 (P4 구조 차용)
#  창: 09:05(시드 종료) 이후 — 시드와 독립인 시간 니치
# ================================
VI아래5호가 = VI가격 - VI호가단위 * 5
매수 = True

if not (관심종목 == 1):
    매수 = False
elif not (90500 <= 시분초 < {window_end}):
    매수 = False
elif not (1000 < 현재가 <= 50000):
    매수 = False
elif not (2.0 < 등락율 <= 20.0):
    매수 = False
elif not (시가총액 < {cap_max}):
    매수 = False
elif not (현재가 < VI아래5호가):
    매수 = False
elif 라운드피겨위5호가이내:
    매수 = False
elif not (-{flat_angle} < 등락율각도({flat_window}) < {flat_angle}):
    매수 = False                                  # F07 — 횡보(각도 평탄) 감지
elif not (초당거래대금 / 초당거래대금평균(30) > {burst_min}):
    매수 = False                                  # F07 — 거래대금 발화
elif not (체결강도 >= {strength_min}):
    매수 = False                                  # F06 — 체결 압력
elif not (초당매수수량 > 매도총잔량 * {absorb_ratio}):
    매수 = False                                  # F06/F14 — 매도벽 소화
elif not (전일동시간비 > {prev_ratio_min}):
    매수 = False                                  # F11 — 전일 대비 활성

if 매수:
    self.Buy()
"""

SELL_TEMPLATE = """\
# ================================
#  F07 니치 청산 — 스칼라 전용(계산예산 안전)
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
    {"name": "window_end", "default": 91500, "values": [91000, 91500, 92000, 92500],
     "side": "buy", "note": "F07 창 종료 — 시간 확대 축(09:10~09:25)"},
    {"name": "cap_max", "default": 3000, "values": [1500, 2000, 3000, 5000],
     "side": "buy", "note": "시총 상한(억)"},
    {"name": "flat_angle", "default": 2.0, "values": [1.0, 2.0, 3.0],
     "side": "buy", "note": "F07 횡보 판정 각도 한계(절대값)"},
    {"name": "flat_window", "default": 60, "values": [30, 60, 120],
     "side": "buy", "note": "횡보 관측 틱 수(유계 윈도우)"},
    {"name": "burst_min", "default": 4.0, "values": [3.0, 4.0, 5.0, 8.0],
     "side": "buy", "note": "F07 발화 배수(초당거래대금/30틱 평균)"},
    {"name": "strength_min", "default": 120, "values": [100, 120, 150],
     "side": "buy", "note": "F06 체결강도 하한 — C7 부검: 승자 155.9"},
    {"name": "absorb_ratio", "default": 0.3, "values": [0.2, 0.3, 0.5],
     "side": "buy", "note": "F06/F14 매도벽 소화 비율"},
    {"name": "prev_ratio_min", "default": 100, "values": [0, 100, 500, 1000],
     "side": "buy", "note": "F11 전일동시간비 하한 — 시드 부검 최강 판별자"},
    {"name": "take_hard", "default": 5, "values": [3, 5, 7],
     "side": "sell", "note": "하드 익절"},
    {"name": "stop_hard", "default": -3.0, "values": [-2.0, -3.0, -5.0],
     "side": "sell", "note": "하드 손절 — 횡보 니치는 시드보다 타이트 기본값"},
    {"name": "max_hold_sec", "default": 600, "values": [180, 300, 600],
     "side": "sell", "note": "시간 청산(발화 실패 시 이탈)"},
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
        "name": "orderflow_f07_ignition",
        "timeframe": "tick",
        "source": "v5.0 보고서 F07+F06+F11 구조 차용 (P4)",
        "description": (
            "P4 오더플로우 원리 템플릿 — F07 횡보후발화(09:05 이후 횡보+거래대금"
            " 발화) 골격 + F06 체결압력 + F11 전일 활성. 시드 사각지대(09:05~)의"
            " 독립 시간 니치(N6 시간분산 충족용). 11θ, 윈도우 함수 2회·역스캔 0."
        ),
        "buy_code": BUY_TEMPLATE,
        "sell_code": SELL_TEMPLATE,
        "params": PARAMS,
    }
    OUT.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")

    rebuilt = load_template("orderflow_f07_ignition")
    b2, s2 = render(rebuilt, {})
    assert b2 == buy and s2 == sell, "재로드 identity 실패"
    n_points = 1 + sum(len(p["values"]) - 1 for p in PARAMS)
    print(f"OK orderflow_f07_ignition: {len(PARAMS)}θ, 좌표 {n_points}점 -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
