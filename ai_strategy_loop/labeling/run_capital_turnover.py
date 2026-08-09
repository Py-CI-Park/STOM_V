"""S4 — 자본 회전 교정 A/B.

## 무엇을 고치려는가

트레일링 후보 3종은 건당 수익률에서 챔피언을 이겼지만 **자본 대비로 졌다**.

| | 챔피언 | B3(trailing 5/2) |
|---|---:|---:|
| 건당 | +0.50% | +0.92% |
| 평균 보유 | 373초 | 540초 |
| 최대동시보유 | 1 | **2** |
| 필요자금 | 1,004,275원 | **1,998,220원** |
| **총수익률** | **80.17%** | 71.17% |

원인은 하나다. 보유가 길어져 자본이 두 배로 묶였고, 총수익률 = 총수익금 /
필요자금 이므로 분모가 커진 만큼 졌다. 그래서 **보유를 끊는 규칙 한 줄**을
얹어 최대동시보유를 1로 되돌린다.

## 실행 계약

- 진입은 챔피언 고정. 매도만 바꾼다(헌법 7항).
- 조기 청산 규칙은 `assembler.EARLY_EXIT_RULES` 허용 목록에서만 온다.
- 기준선은 **다시 재지 않고** 같은 구간의 기존 실측을 읽어 온다 — 같은
  진입·매도·구간이면 엔진은 결정적이라 재측정은 시간 낭비다.
- 게이트: 총수익률 ≥ 챔피언, 최대동시보유 ≤ 1.

사용:
    python -m ai_strategy_loop.labeling.run_capital_turnover \\
        --out-name design_v4 --tag _ext --arm 5 --give 2
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time

from ai_strategy_loop.labeling.assembler import (
    EARLY_EXIT_RULES, render_capital_turnover_sell_expression)
from ai_strategy_loop.labeling.lanes import LANES
from ai_strategy_loop.labeling.run_engine_measure import (
    CHAMPION_BUY, CHAMPION_SELL, _METRIC_KEYS, _run_arm)
from ai_strategy_loop.labeling.run_p5 import Client

_LABEL_ROOT = os.path.join(os.path.dirname(__file__), "..", "state", "labels")

#: 이 러너가 쓸 수 있는 유일한 이름공간.
OWNED_PREFIX = "W6_S_"


def _assert_owned(name: str) -> None:
    if not name.startswith(OWNED_PREFIX):
        raise ValueError(f"쓰기 금지 이름: {name} (허용 접두 {OWNED_PREFIX!r})")


def _load_baseline(out_name: str, tag: str) -> tuple[dict, list[int], dict]:
    """같은 구간의 기준선 실측을 읽는다 — 없으면 만들라고 말하고 멈춘다.

    기준선 **팔 전체**(job_id 포함)도 함께 돌려준다. 짝지은 검정은 기준선의
    거래 기록이 있어야 하고, 그 기록은 job_id 로만 찾을 수 있다.
    """
    path = os.path.join(_LABEL_ROOT, out_name, f"_p5_engine_report{tag}.json")
    if not os.path.exists(path):
        raise SystemExit(f"기준선 실측이 없다: {path}\n"
                         f"  먼저 run_engine_measure 를 같은 --tag 로 돌려라.")
    with open(path, "r", encoding="utf-8") as handle:
        report = json.load(handle)
    metrics = report.get("baseline_metrics") or {}
    if not metrics.get("trade_count"):
        raise SystemExit("기준선 거래 수가 없다 — 실측이 완료되지 않았다.")
    arm = next((o for o in report.get("outcomes") or []
                if o.get("arm") == "baseline"), None)
    if arm is None:
        raise SystemExit("기준선 팔 기록이 없다 — 짝지은 검정을 할 수 없다.")
    return metrics, list(report.get("design") or []), arm


def write_standard_report(path: str, *, lane_name: str, span: list[int],
                          baseline_arm: dict, baseline: dict,
                          outcomes: list[dict], note: str) -> None:
    """심판·원장 러너가 읽는 **표준 모양**으로 한 벌 더 남긴다.

    두 러너(`run_engine_ladder`·`run_ledger_sync`)는 `_p5_engine_report*.json`
    한 가지 모양만 안다. 자본 회전 실험을 위해 그 둘을 고치는 대신, 이쪽에서
    같은 모양을 한 벌 더 써 준다 — 심판 경로는 하나로 유지하는 편이 안전하다.
    """
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({
            "lane": lane_name, "design": span,
            "champion_buy": CHAMPION_BUY, "baseline_sell": CHAMPION_SELL,
            "baseline_metrics": baseline,
            "outcomes": [baseline_arm] + outcomes,
            "note": note,
        }, handle, ensure_ascii=False, indent=1, default=float)


def _gate(baseline: dict, engine: dict) -> dict:
    """자본 회전 교정의 합격 조건 — 건당이 아니라 **자본 대비**로 잰다."""
    base_tpp = baseline.get("total_profit_pct")
    tpp = engine.get("total_profit_pct")
    hold = engine.get("max_hold_count")
    capital_ok = (tpp is not None and base_tpp is not None
                  and float(tpp) >= float(base_tpp))
    hold_ok = hold is not None and int(hold) <= 1
    return {
        "capital_pass": bool(capital_ok),
        "hold_pass": bool(hold_ok),
        "pass": bool(capital_ok and hold_ok),
        "baseline_total_profit_pct": base_tpp,
        "total_profit_pct": tpp,
        "max_hold_count": hold,
        "note": ("총수익률이 챔피언 이상이고 최대동시보유가 1이어야 자본 회전이 "
                 "교정된 것이다. 건당만 이기는 것은 이미 B3 가 했다."),
    }


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-name", default="design_v4")
    parser.add_argument("--lane", choices=sorted(LANES), default="tick")
    parser.add_argument("--tag", default="_ext", help="기준선 리포트 접미(구간 구분)")
    parser.add_argument("--arm", type=float, default=5.0, help="B3 무장 임계")
    parser.add_argument("--give", type=float, default=2.0, help="B3 되돌림 폭")
    parser.add_argument("--engines", type=int, default=16)
    parser.add_argument("--timeout", type=int, default=9000)
    parser.add_argument("--rules", default=",".join(sorted(EARLY_EXIT_RULES)))
    args = parser.parse_args()

    lane = LANES[args.lane]
    rules = [r.strip() for r in args.rules.split(",") if r.strip()]
    unknown = [r for r in rules if r not in EARLY_EXIT_RULES]
    if unknown:
        raise SystemExit(f"허용되지 않은 규칙: {unknown} (가능: {sorted(EARLY_EXIT_RULES)})")

    baseline, span, baseline_arm = _load_baseline(args.out_name, args.tag)
    print(f"[기준선] {CHAMPION_BUY} + {CHAMPION_SELL} 구간 {span} "
          f"거래={baseline.get('trade_count')} 건당={baseline.get('avg_profit_pct')}% "
          f"총수익률={baseline.get('total_profit_pct')}% "
          f"필요자금={baseline.get('seed_capital')}", flush=True)

    client = Client()
    out_path = os.path.join(_LABEL_ROOT, args.out_name,
                            f"_capital_turnover{args.tag}.json")
    outcomes: list[dict] = []
    t0 = time.time()

    note = ("B3(트레일링)에 조기 청산 한 줄씩만 얹은 A/B. "
            "판정은 자본 대비(총수익률·최대동시보유)로 한다.")
    report_path = os.path.join(_LABEL_ROOT, args.out_name,
                               f"_p5_engine_report{args.tag}_turn.json")

    def _save() -> None:
        """팔 하나가 끝날 때마다 저장한다 — 엔진 시간을 잃으면 아프다."""
        with open(out_path, "w", encoding="utf-8") as handle:
            json.dump({
                "lane": lane.name, "design": span,
                "champion_buy": CHAMPION_BUY, "baseline_sell": CHAMPION_SELL,
                "baseline_metrics": baseline,
                "base_rule": {"arm_pct": args.arm, "give_pct": args.give},
                "outcomes": outcomes,
                "complete": len(outcomes) == len(rules),
                "note": note,
            }, handle, ensure_ascii=False, indent=1, default=float)
        # 심판·원장이 읽는 표준 모양으로 한 벌 더.
        write_standard_report(report_path, lane_name=lane.name, span=span,
                              baseline_arm=baseline_arm, baseline=baseline,
                              outcomes=outcomes, note=note)

    for index, rule_key in enumerate(rules, start=1):
        label, _ = EARLY_EXIT_RULES[rule_key]
        sell_name = f"{OWNED_PREFIX}TURN_{rule_key.upper()}"
        _assert_owned(sell_name)
        code = render_capital_turnover_sell_expression(
            name=sell_name, arm_pct=args.arm, give_pct=args.give,
            horizon=lane.barrier_horizon, rule_key=rule_key,
            forced_exit=lane.forced_exit,
        )
        saved = client.call("POST", "/bt/strategy",
                            {"kind": "sell", "name": sell_name, "code": code,
                             "overwrite": True})
        print(f"[C{index}] 매도 등록 {sell_name} ({label}) {saved.get('status')}", flush=True)

        run = _run_arm(client, buy=CHAMPION_BUY, sell=sell_name, lane=lane,
                       engines=args.engines, timeout=args.timeout,
                       period=(span[0], span[1]) if len(span) == 2 else None)
        metrics = run["metrics"]
        outcomes.append({
            "name": sell_name, "rule": f"trailing({args.arm:g}/{args.give:g})+{label}",
            "rule_key": rule_key, "arm": f"turnover_{index}",
            "buy": CHAMPION_BUY, "sell": sell_name,
            "job_id": run.get("job_id"), "status": run["status"],
            "predicted": None,          # 지도에 대응 셀이 없다 — 엔진 축 전용 실험이다
            "engine": {k: metrics.get(k) for k in _METRIC_KEYS},
            "gate": _gate(baseline, metrics),
            "transfer_ratio": None,
        })
        gate = outcomes[-1]["gate"]
        print(f"    → {run['status']} 거래={metrics.get('trade_count')} "
              f"건당={metrics.get('avg_profit_pct')}% "
              f"보유={metrics.get('avg_hold_time')}초 "
              f"동시보유={gate['max_hold_count']} "
              f"총수익률={gate['total_profit_pct']}% "
              f"{'PASS' if gate['pass'] else 'FAIL'}", flush=True)
        _save()

    print(f"\n=== 자본 회전 교정 요약 (구간 {span}) · {time.time() - t0:.0f}초 ===", flush=True)
    print(f" {'후보':<28} {'거래':>5} {'건당':>8} {'보유초':>7} {'동시':>4} {'총수익률':>9}  판정")
    print(f" {'챔피언(합격선)':<28} {baseline.get('trade_count'):>5} "
          f"{baseline.get('avg_profit_pct'):>7}% {baseline.get('avg_hold_time'):>7} "
          f"{baseline.get('max_hold_count'):>4} {baseline.get('total_profit_pct'):>8}%  —")
    for row in outcomes:
        e, g = row["engine"], row["gate"]
        print(f" {row['name']:<28} {e.get('trade_count'):>5} "
              f"{e.get('avg_profit_pct'):>7}% {e.get('avg_hold_time'):>7} "
              f"{e.get('max_hold_count'):>4} {e.get('total_profit_pct'):>8}%  "
              f"{'PASS' if g['pass'] else 'FAIL'}")
    print(f"\n기록: {out_path}", flush=True)


if __name__ == "__main__":
    main()
