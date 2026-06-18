"""플라시보(무작위 진입) 매수 전략 생성기 (R6, 2026-06-11 — 연구 전용).

목적: "매수 신호가 무작위 진입보다 나은가?"를 검정하는 베이스라인을 만든다.
후보의 **매도 전략은 그대로** 두고 매수만 결정론 의사난수 진입으로 바꿔 같은
윈도우에서 배치 평가하면, 후보 손익이 (a) 진입 신호의 알파인지 (b) 시간창×유니버스
(+매도 규칙)의 베타인지를 분리할 수 있다. 6/10 실증에서 C3/C9 등 음수 후보들이
"신호가 아니라 추격매수 베타"였는지 사후 검정하는 데도 쓴다.

설계:
  - 진입 = `(현재가 * 31 + 시분초 * 7 + 데이터길이) % 1000 < rate` — 외부 상태/난수
    없이 **결정론**(재현 가능)이면서 가격·시각에 준-무작위로 분포한다.
  - rate(천분율)는 보정 대상이다: 발화 빈도는 유니버스 틱 수에 비례하므로, 여러
    rate 변형을 만들어 스모크로 목표 일평균 거래수에 맞는 것을 고른다(절차 ↓).
  - 생성 코드는 생성기와 동일한 PRE-SAVE 가드(compile/token/scope)를 통과해야 저장된다.

사용 절차(advisory — 어떤 게이트/선택도 바꾸지 않는다):
  1) PYTHONUTF8=1 python -m ai_strategy_loop.scripts.gen_placebo_strategy \
         --prefix PLACEBO_0611 --rates 2,5,10,20 --start 90030 --end 92000
  2) pairs.json에 [{"label":"PLACEBO_r5","buy":"PLACEBO_0611_R5_B","sell":"<후보의 매도>"}...]
     를 넣고 claude_candidate_batch_eval로 스모크 → 후보와 비슷한 거래수의 rate 선택.
  3) 같은 train 윈도우에서 플라시보 N개(rate 동일·시프트 변형) 평가 → 후보 손익이
     플라시보 분포의 상위 꼬리(예: >p95)에 있는지 결정 카드에 advisory로 기록.
"""

from __future__ import annotations

import argparse

import ai_strategy_loop.bootstrap as bootstrap
from ai_strategy_loop.brain.token_check import check_tokens
from ai_strategy_loop.brain.variable_scope import check_variable_scope
from cli.strategy_generator import save_strategy_to_db

_TEMPLATE = """# 플라시보(무작위 진입) 베이스라인 — R6 연구 전용 (결정론 의사난수, rate={rate}/1000)
# 목적: 동일 매도·동일 윈도우에서 매수 신호의 초과 성과를 검정한다(advisory).
매수 = True
if not ({start} <= 시분초 < {end}):
    매수 = False
elif not (관심종목 == 1):
    매수 = False
elif not (데이터길이 >= 31):
    매수 = False
elif not (1000 <= 현재가 <= 100000):
    매수 = False
elif not ((현재가 * 31 + 시분초 * 7 + 데이터길이 + {shift}) % 1000 < {rate}):
    매수 = False

if 매수:
    self.Buy()
"""


def build_placebo_code(rate: int, start: int, end: int, shift: int = 0) -> str:
    """플라시보 매수 코드 문자열을 만든다(결정론 — 같은 인자면 같은 코드)."""
    return _TEMPLATE.format(rate=int(rate), start=int(start), end=int(end), shift=int(shift))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="PLACEBO")
    ap.add_argument("--rates", default="2,5,10", help="천분율 발화 확률 목록(쉼표)")
    ap.add_argument("--start", type=int, default=90030)
    ap.add_argument("--end", type=int, default=92000)
    ap.add_argument("--shifts", default="0", help="의사난수 시프트 변형 목록(쉼표)")
    args = ap.parse_args()

    db = str(bootstrap.LOOP_DB_STRATEGY)
    failed = False
    for rate in [int(r) for r in args.rates.split(",") if r.strip()]:
        for shift in [int(s) for s in args.shifts.split(",") if s.strip()]:
            name = f"{args.prefix}_R{rate}" + (f"_S{shift}" if shift else "") + "_B"
            code = build_placebo_code(rate, args.start, args.end, shift)
            try:
                compile(code, "<string>", "exec")
            except SyntaxError as exc:
                print(f"[FAIL] {name}: compile {exc}")
                failed = True
                continue
            ok, msg = check_tokens(code)
            if not ok:
                print(f"[FAIL] {name}: token {msg}")
                failed = True
                continue
            ok, missing = check_variable_scope(code, "tick", "buy")
            if not ok:
                print(f"[FAIL] {name}: scope {missing}")
                failed = True
                continue
            res = save_strategy_to_db(db, name, code, "buy")
            print(f"[{res.get('status', '?').upper()}] {name} {res.get('action', '')}")
            failed = failed or res.get("status") != "ok"
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
