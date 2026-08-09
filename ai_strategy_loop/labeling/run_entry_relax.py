"""S7-b — 진입 완화 후보를 엔진으로 확인한다.

## 규율

지도(`run_entry_ablation`)에서 "완화 후보"로 나온 절을 **챔피언 매도와 함께**
엔진에 올린다. 매도를 B3 로 바꾸지 않는 이유는 헌법 7항이다:
**진입과 매도를 동시에 바꾸지 않는다.** 둘을 같이 바꾸면 어느 쪽이 효과인지
가릴 수 없다.

따라서 이 실험의 기준선은 챔피언 페어(진입+매도 원본)이고, 바뀌는 것은
**매수식의 절 하나**뿐이다.

## 게이트

| 판정 | 조건 |
|---|---|
| **완화 채택 후보** | 거래 증가 + 건당 ≥ 기준선 + 총수익률 ≥ 기준선 |
| 값 지불 | 거래는 늘었으나 위를 하나라도 못 넘음 |

빈도를 위해 기대값을 팔지 않는다.

사용:
    python -m ai_strategy_loop.labeling.run_entry_relax \\
        --out-name design_v4 --tag _ext --clauses 905_시가대비,905_거래대금급증
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sqlite3
import sys
import time

from ai_strategy_loop.labeling import champion_clauses as cc
from ai_strategy_loop.labeling.lanes import LANES
from ai_strategy_loop.labeling.run_capital_turnover import _load_baseline
from ai_strategy_loop.labeling.run_engine_measure import (
    CHAMPION_BUY, CHAMPION_SELL, _METRIC_KEYS, _run_arm)
from ai_strategy_loop.labeling.run_p5 import Client

_LABEL_ROOT = os.path.join(os.path.dirname(__file__), "..", "state", "labels")
_STRATEGY_DB = os.path.join(os.path.dirname(__file__), "..", "..",
                            "_database", "strategy.db")

#: 이 러너가 쓸 수 있는 유일한 이름공간.
OWNED_PREFIX = "W7_B_"


def _assert_owned(name: str) -> None:
    if not name.startswith(OWNED_PREFIX):
        raise ValueError(f"쓰기 금지 이름: {name} (허용 접두 {OWNED_PREFIX!r})")


def champion_buy_code(db_path: str | None = None) -> str:
    """챔피언 매수식 원문을 **읽기 전용**으로 가져온다."""
    path = os.path.abspath(db_path or _STRATEGY_DB)
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        row = con.execute('SELECT 전략코드 FROM stockbuy WHERE "index"=?',
                          (CHAMPION_BUY,)).fetchone()
    finally:
        con.close()
    if not row:
        raise SystemExit(f"챔피언 매수식이 없다: {CHAMPION_BUY}")
    return str(row[0])


def _gate(baseline: dict, engine: dict) -> dict:
    """완화는 **공짜여야** 채택 후보다 — 셋 다 넘어야 한다."""
    def ge(key: str) -> bool:
        mine, base = engine.get(key), baseline.get(key)
        return mine is not None and base is not None and float(mine) >= float(base)

    more = (engine.get("trade_count") or 0) > (baseline.get("trade_count") or 0)
    per_trade, capital = ge("avg_profit_pct"), ge("total_profit_pct")
    return {
        "more_trades": bool(more),
        "per_trade_pass": bool(per_trade),
        "capital_pass": bool(capital),
        "pass": bool(more and per_trade and capital),
        "trade_gain": (engine.get("trade_count") or 0) - (baseline.get("trade_count") or 0),
        "note": "빈도를 위해 기대값을 팔지 않는다 — 건당·총수익률이 함께 유지돼야 한다.",
    }


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-name", default="design_v4")
    parser.add_argument("--lane", choices=sorted(LANES), default="tick")
    parser.add_argument("--tag", default="_ext")
    parser.add_argument("--clauses", default="905_시가대비",
                        help="쉼표 구분. DSL 앵커가 등록된 절만 가능")
    parser.add_argument("--engines", type=int, default=16)
    parser.add_argument("--timeout", type=int, default=9000)
    args = parser.parse_args()

    lane = LANES[args.lane]
    keys = [k.strip() for k in args.clauses.split(",") if k.strip()]
    unknown = [k for k in keys if k not in cc.DSL_ANCHOR]
    if unknown:
        raise SystemExit(f"DSL 앵커가 없는 절: {unknown} (등록됨: {sorted(cc.DSL_ANCHOR)})")

    baseline, span, baseline_arm = _load_baseline(args.out_name, args.tag)
    champion = champion_buy_code()
    print(f"[기준선] {CHAMPION_BUY} + {CHAMPION_SELL} 구간 {span} "
          f"거래={baseline.get('trade_count')} 건당={baseline.get('avg_profit_pct')}% "
          f"총수익률={baseline.get('total_profit_pct')}%", flush=True)

    client = Client()
    outcomes: list[dict] = []
    out_path = os.path.join(_LABEL_ROOT, args.out_name, f"_entry_relax{args.tag}.json")
    t0 = time.time()

    def _save() -> None:
        with open(out_path, "w", encoding="utf-8") as handle:
            json.dump({
                "lane": lane.name, "design": span,
                "champion_buy": CHAMPION_BUY, "baseline_sell": CHAMPION_SELL,
                "baseline_metrics": baseline, "outcomes": outcomes,
                "complete": len(outcomes) == len(keys),
                "note": ("진입 절 하나만 뺀 A/B. 매도는 챔피언 원본 그대로다 "
                         "— 진입과 매도를 동시에 바꾸지 않는다(헌법 7항)."),
            }, handle, ensure_ascii=False, indent=1, default=float)

    for index, key in enumerate(keys, start=1):
        buy_name = f"{OWNED_PREFIX}RELAX_{key}"
        _assert_owned(buy_name)
        code = cc.drop_clause_from_dsl(champion, key)
        saved = client.call("POST", "/bt/strategy",
                            {"kind": "buy", "name": buy_name, "code": code,
                             "overwrite": True})
        print(f"[R{index}] 매수 등록 {buy_name} ({cc.clause_by_key(key).label}) "
              f"{saved.get('status')}", flush=True)

        run = _run_arm(client, buy=buy_name, sell=CHAMPION_SELL, lane=lane,
                       engines=args.engines, timeout=args.timeout,
                       period=(span[0], span[1]) if len(span) == 2 else None)
        metrics = run["metrics"]
        gate = _gate(baseline, metrics)
        outcomes.append({
            "name": buy_name, "rule": f"champion − {key}", "clause": key,
            "arm": f"relax_{index}", "buy": buy_name, "sell": CHAMPION_SELL,
            "job_id": run.get("job_id"), "status": run["status"],
            "predicted": None,
            "engine": {k: metrics.get(k) for k in _METRIC_KEYS},
            "gate": gate, "transfer_ratio": None,
        })
        print(f"    → {run['status']} 거래={metrics.get('trade_count')} "
              f"({gate['trade_gain']:+d}) 건당={metrics.get('avg_profit_pct')}% "
              f"총수익률={metrics.get('total_profit_pct')}% "
              f"{'PASS' if gate['pass'] else 'FAIL'}", flush=True)
        _save()

    print(f"\n=== 진입 완화 요약 (구간 {span}) · {time.time() - t0:.0f}초 ===")
    print(f" {'후보':<30}{'거래':>6}{'건당':>9}{'총수익률':>10}  판정")
    print(f" {'챔피언(합격선)':<30}{baseline.get('trade_count'):>6}"
          f"{baseline.get('avg_profit_pct'):>8}%{baseline.get('total_profit_pct'):>9}%  —")
    for row in outcomes:
        e, g = row["engine"], row["gate"]
        print(f" {row['rule']:<30}{e.get('trade_count'):>6}"
              f"{e.get('avg_profit_pct'):>8}%{e.get('total_profit_pct'):>9}%  "
              f"{'PASS' if g['pass'] else 'FAIL'}")
    print(f"\n기록: {out_path}", flush=True)


if __name__ == "__main__":
    main()
