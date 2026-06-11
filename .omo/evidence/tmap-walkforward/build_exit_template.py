"""C10/M8 (2026-06-11) — 매도 '구조' 템플릿 생성기: seed_902905_exit2.

근거: W1 본 스윕의 우세 고원 3개 중 2개(take_hard·trail_start)가 매도
다이얼 — 청산이 수익을 지배하는데 구조 탐색은 매수에 편중돼 있었다.
이 템플릿은 **매수를 시드 기본값으로 고정**(리터럴 — 변인 통제)하고
청산 구조 자체를 6θ로 모수화한다:

  - 시간 청산(max_hold_sec): 시드에 없던 절대 보유시간 한도.
  - 손익분기 스탑(be_trigger/be_floor): 이익이 떴다가 본전 부근으로
    되돌아오면 청산 — 비율 트레일과 다른 메커니즘(절대 바닥).
  - 절대 격차 트레일(trail_gap): 최고수익률 - 수익률 >= gap (시드의
    비율 유지(trail_keep)와 대조되는 구조).
  - 하드 익절/손절(take_hard/stop_hard): 시드와 동일 프레임(공정 비교 앵커).

계산예산 안전: 스칼라 변수만 사용 — 윈도우/역스캔 함수 0회(B3·N4 무관).
실행: PYTHONUTF8=1 python .omo/evidence/tmap-walkforward/build_exit_template.py
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

OUT = REPO / "ai_strategy_loop/tmap/templates/seed_902905_exit2.json"

SELL_TEMPLATE = """\
# ================================
#  매도 조건 — 구조 탐색용 exit2 (스칼라 전용·계산예산 안전)
# ================================
매도 = False

if 등락율 > 29.5:
    매도 = True
elif 수익률 >= {take_hard} or 수익률 <= {stop_hard}:
    매도 = True
elif 보유시간 >= {max_hold_sec}:
    매도 = True
elif 최고수익률 >= {be_trigger} and 수익률 <= {be_floor}:
    매도 = True
elif 최고수익률 > {trail_start} and 최고수익률 - 수익률 >= {trail_gap}:
    매도 = True

if 매도:
    self.Sell()
"""

PARAMS = [
    {"name": "take_hard", "default": 5, "values": [3, 4, 5, 7, 9],
     "side": "sell", "note": "하드 익절 — 시드와 동일 프레임(비교 앵커)"},
    {"name": "stop_hard", "default": -5.0, "values": [-3.0, -4.0, -5.0, -7.0],
     "side": "sell", "note": "하드 손절"},
    {"name": "max_hold_sec", "default": 600, "values": [90, 180, 300, 600, 1200],
     "side": "sell", "note": "시간 청산(신규 구조) — 시드 부검: 손실의 다수가 장기 보유 구간"},
    {"name": "be_trigger", "default": 3, "values": [2, 3, 4, 6],
     "side": "sell", "note": "손익분기 스탑 발동 최고수익률(신규 구조)"},
    {"name": "be_floor", "default": 0.3, "values": [0.1, 0.3, 0.5, 1.0],
     "side": "sell", "note": "손익분기 스탑 바닥(수익률 %)"},
    {"name": "trail_gap", "default": 2.0, "values": [1.0, 1.5, 2.0, 3.0, 4.0],
     "side": "sell", "note": "절대 격차 트레일(신규 구조) — 시드 비율 유지와 대조"},
    {"name": "trail_start", "default": 6, "values": [3, 4, 6, 8],
     "side": "sell", "note": "트레일 시작 최고수익률"},
]


def main() -> int:
    seed = load_template("seed_902905")
    # 매수 = 시드 기본값 고정 렌더(리터럴) — 변인 통제: 청산 구조만 움직인다.
    buy_fixed, _seed_sell = render(seed, {})
    assert "{" not in buy_fixed, "매수 고정 렌더에 슬롯 잔존"

    defaults = {p["name"]: p["default"] for p in PARAMS}
    sell_default = SELL_TEMPLATE.format(**defaults)
    errors = validate_rendered(buy_fixed, sell_default, "tick")
    assert errors == [], f"기본값 렌더 가드 실패: {errors}"

    # 슬롯 값 전 조합이 아닌 좌표 후보 각각도 가드를 통과해야 한다(스윕 전 보증).
    for p in PARAMS:
        for v in p["values"]:
            theta = {**defaults, p["name"]: v}
            errs = validate_rendered(buy_fixed, SELL_TEMPLATE.format(**theta), "tick")
            assert errs == [], f"{p['name']}={v} 가드 실패: {errs}"

    spec = {
        "name": "seed_902905_exit2",
        "timeframe": "tick",
        "source": "seed_902905 buy(기본값 고정) + 신규 청산 구조(M8)",
        "description": (
            "M8 매도 구조 탐색 — 매수는 시드 기본값 리터럴 고정(변인 통제), "
            "청산을 7θ(시간청산·손익분기스탑·절대격차트레일·하드익절손절)로 모수화. "
            "W1 근거: 우세 고원 3중 2가 매도 다이얼. 스칼라 전용(계산예산 안전)."
        ),
        "buy_code": buy_fixed,
        "sell_code": SELL_TEMPLATE,
        "params": PARAMS,
    }
    OUT.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")

    rebuilt = load_template("seed_902905_exit2")
    b2, s2 = render(rebuilt, {})
    assert b2 == buy_fixed and s2 == sell_default, "재로드 identity 실패"
    n_points = 1 + sum(len(p["values"]) - 1 for p in PARAMS)
    print(f"OK seed_902905_exit2: {len(PARAMS)}θ, 좌표 {n_points}점 -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
