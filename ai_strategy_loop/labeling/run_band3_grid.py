"""HOF3 — 밴드 3 격자를 **학습 구간에서만** 엔진으로 잰다.

사전 등록: `docs/research/quant_scoring_pipeline/2026-08-10_HOF3_사전등록.md`
(커밋 `993cd723` — 실행 전)

## 판정 대상은 코호트 C 뿐이다

밴드 1·2 를 손대지 않으므로 코호트 A·B 는 그대로여야 한다. 그래서 밴드 3 의
순효과는 **코호트 C(09:05~09:20)의 총수익금**으로 분리된다. HOF1 에서 이
분리가 비트 단위로 성립함이 확인됐다(A·B 가 기준선과 완전히 동일했다).

## K0 기준을 같은 세션에서 다시 잰다

사전 등록의 K0 값(+44,216원)은 **전 구간 실측을 학습 구간으로 잘라** 얻은
것이다. 학습 구간만 도는 이번 실행과는 워밍업이 달라 값이 어긋날 수 있다.
그래서 K0(=HOF1 후보)을 **같은 세션에서 한 번 더** 잰다. 이는 새 가설이
아니라 **기준 측정**이므로 격자 예산(6셀)에 들어가지 않는다.

사용:
    python -m ai_strategy_loop.labeling.run_band3_grid \\
        --out-name design_v5 --cells 0.5,1.0,1.5,2.0,swap \\
        --capital-limit 20000000 --timeout 9000
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time

import pandas as pd

from ai_strategy_loop.labeling import band3
from ai_strategy_loop.labeling.lanes import LANES
from ai_strategy_loop.labeling.run_engine_ladder import _tables, resolve_table
from ai_strategy_loop.labeling.run_engine_measure import (
    CHAMPION_BUY, CHAMPION_SELL, _METRIC_KEYS, _run_arm)
from ai_strategy_loop.labeling.run_entry_relax import champion_buy_code
from ai_strategy_loop.labeling.run_p5 import Client
from ai_strategy_loop.labeling.run_trade_autopsy import (
    calendar_days, load_trades, split_days)

_LABEL_ROOT = os.path.join(os.path.dirname(__file__), "..", "state", "labels")
_BT_DB = os.path.join(os.path.dirname(__file__), "..", "..",
                      "_database", "backtest.db")

#: 이 러너가 쓸 수 있는 유일한 이름공간.
OWNED_PREFIX = "HOF3_B_"

#: 사전 등록 §4 — 표본 하한.
MIN_TRADES = 30

#: K0 기준(사전 등록 기록값). 같은 세션 재측정이 있으면 그것을 쓴다.
PREREG_K0_KRW = 44_216.0


def cohort_summary(table: str, days: set[int]) -> dict:
    """결과 테이블을 코호트별로 요약한다(주어진 거래일만)."""
    frame = load_trades(table)
    frame = frame[frame["일자"].isin(days)]
    out = {}
    for name in ("A", "B", "C"):
        part = frame[frame["코호트"] == name]
        out[name] = {
            "trades": int(len(part)),
            "profit_krw": float(part["수익금"].sum()),
            "avg_pct": float(part["수익률"].mean()) if len(part) else 0.0,
        }
    out["all"] = {"trades": int(len(frame)),
                  "profit_krw": float(frame["수익금"].sum())}
    return out


def gate(cohort: dict, metrics: dict, *, reference_krw: float,
         capital_limit_krw: float) -> dict:
    """사전 등록 §4 합격선 그대로 — A~D 필수.

    | # | 조건 |
    |---|---|
    | A | 학습 코호트 C 총수익금 > 0 |
    | B | 학습 코호트 C 총수익금 > K0 기준 |
    | C | 코호트 C 거래 >= 30 |
    | D | 필요자금 <= 한도 |
    """
    c = cohort.get("C") or {}
    profit = float(c.get("profit_krw") or 0.0)
    trades = int(c.get("trades") or 0)
    seed = metrics.get("seed_capital")
    positive = profit > 0
    beats = profit > float(reference_krw)
    enough = trades >= MIN_TRADES
    capital = seed is not None and float(seed) <= float(capital_limit_krw)
    return {
        "cohort_c_profit_krw": profit, "cohort_c_trades": trades,
        "reference_krw": float(reference_krw),
        "positive_pass": bool(positive), "beats_reference": bool(beats),
        "sample_pass": bool(enough), "capital_pass": bool(capital),
        "pass": bool(positive and beats and enough and capital),
    }


def ab_unchanged(cohort: dict, baseline: dict, *, tolerance: float = 1.0) -> dict:
    """밴드 1·2 가 그대로인지 확인한다(사전 등록 §4 E항).

    다르면 밴드 3 만 바뀌었다는 전제가 깨진 것이므로 그 측정은 신뢰할 수 없다.
    """
    detail = {}
    same = True
    for name in ("A", "B"):
        mine, base = cohort.get(name) or {}, baseline.get(name) or {}
        trades_ok = int(mine.get("trades") or 0) == int(base.get("trades") or 0)
        profit_ok = abs(float(mine.get("profit_krw") or 0.0)
                        - float(base.get("profit_krw") or 0.0)) <= tolerance
        detail[name] = {"trades_same": trades_ok, "profit_same": profit_ok,
                        "mine": mine.get("trades"), "base": base.get("trades")}
        same = same and trades_ok and profit_ok
    return {"unchanged": bool(same), "detail": detail}


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-name", default="design_v5")
    parser.add_argument("--lane", choices=sorted(LANES), default="tick")
    parser.add_argument("--cells", default="0.5,1.0,1.5,2.0,swap",
                        help="사전 등록 격자. 셀 추가 금지")
    parser.add_argument("--capital-limit", type=float, required=True)
    parser.add_argument("--engines", type=int, default=16)
    parser.add_argument("--timeout", type=int, default=9000)
    args = parser.parse_args()

    lane = LANES[args.lane]
    split = split_days(calendar_days(args.out_name))
    train = split["train"]
    train_days, span = set(train), (train[0], train[-1])
    cells = [c.strip() for c in args.cells.split(",") if c.strip()]
    if len(cells) > 5:
        raise SystemExit(f"격자 예산 초과: {len(cells)}셀 (사전 등록 5셀 + K0 기준)")

    champion = champion_buy_code()
    client = Client()
    out_path = os.path.join(_LABEL_ROOT, args.out_name, "_hof3_band3.json")
    outcomes: list[dict] = []
    report = {
        "lane": lane.name, "train_span": list(span),
        "train_days": len(train), "cells": cells,
        "capital_limit_krw": args.capital_limit,
        "prereg": "2026-08-10_HOF3_사전등록.md (993cd723)",
        "outcomes": outcomes, "complete": False,
        "note": ("학습 구간만 측정한다. 검증은 상위 <=2 셀만, 확인은 예약. "
                 "판정 대상은 코호트 C 총수익금(밴드 1·2 는 불변)."),
    }

    def save() -> None:
        with open(out_path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=1, default=float)

    def measure(label: str, buy_name: str) -> dict:
        run = _run_arm(client, buy=buy_name, sell=CHAMPION_SELL, lane=lane,
                       engines=args.engines, timeout=args.timeout, period=span)
        metrics = run["metrics"]
        table = resolve_table(_tables(os.path.abspath(_BT_DB)), buy_name,
                              run.get("job_id") or "")
        cohort = cohort_summary(table, train_days) if table else {}
        print(f"    → {run['status']} 거래={metrics.get('trade_count')} "
              f"코호트C={cohort.get('C', {}).get('trades')}건 "
              f"{cohort.get('C', {}).get('profit_krw', 0):,.0f}원", flush=True)
        return {"label": label, "buy": buy_name, "job_id": run.get("job_id"),
                "status": run["status"], "table": table,
                "engine": {k: metrics.get(k) for k in _METRIC_KEYS},
                "cohort": cohort}

    t0 = time.time()
    print(f"[구간] 학습 {len(train)}일 {span} — 검증·확인은 읽지 않는다", flush=True)

    # 기준 1: 챔피언(밴드 1·2 만) — 코호트 A·B 불변 확인의 대조.
    print(f"[기준] 챔피언 {CHAMPION_BUY}", flush=True)
    champ = measure("champion", CHAMPION_BUY)
    outcomes.append(champ)
    save()

    # 기준 2: K0(=HOF1 후보) 같은 세션 재측정.
    print("[기준] K0 = HOF1_B_WINDOW_920 (밴드 2 절 그대로)", flush=True)
    k0 = measure("K0", "HOF1_B_WINDOW_920")
    outcomes.append(k0)
    save()
    reference = float((k0["cohort"].get("C") or {}).get("profit_krw", PREREG_K0_KRW))
    print(f"[기준] K0 학습 코호트 C = {reference:,.0f}원 "
          f"(사전 등록 기록값 {PREREG_K0_KRW:,.0f}원)", flush=True)

    for cell in cells:
        name = f"{OWNED_PREFIX}BAND3_{band3.cell_name(cell)}"
        if not name.startswith(OWNED_PREFIX):
            raise SystemExit(f"쓰기 금지 이름: {name}")
        code = band3.attach_band3(champion, cell)
        saved = client.call("POST", "/bt/strategy",
                            {"kind": "buy", "name": name, "code": code,
                             "overwrite": True})
        print(f"[셀 {cell}] 등록 {name} {saved.get('status')}", flush=True)
        row = measure(cell, name)
        row["gate"] = gate(row["cohort"], row["engine"],
                           reference_krw=reference,
                           capital_limit_krw=args.capital_limit)
        row["ab_check"] = ab_unchanged(row["cohort"], champ["cohort"])
        if not row["ab_check"]["unchanged"]:
            print("    ⚠ 코호트 A·B 가 기준선과 다르다 — 밴드 3 분리 전제 깨짐", flush=True)
        print(f"    판정 {'PASS' if row['gate']['pass'] else 'FAIL'} "
              f"(기준 {reference:,.0f}원)", flush=True)
        outcomes.append(row)
        save()

    report["reference_krw"] = reference
    report["complete"] = True
    save()

    graded = [o for o in outcomes if o.get("gate")]
    print(f"\n=== HOF3 밴드 3 격자 (학습 {len(train)}일 · {time.time() - t0:.0f}초) ===")
    print(f" {'셀':<8}{'전체거래':>8}{'코호트C':>8}{'C총수익금':>13}{'C건당':>8}  판정")
    print(f" {'K0':<8}{k0['engine'].get('trade_count'):>8}"
          f"{(k0['cohort'].get('C') or {}).get('trades'):>8}{reference:>13,.0f}"
          f"{(k0['cohort'].get('C') or {}).get('avg_pct', 0):>7.3f}%  기준")
    for row in graded:
        c = row["cohort"].get("C") or {}
        print(f" {row['label']:<8}{row['engine'].get('trade_count'):>8}"
              f"{c.get('trades'):>8}{c.get('profit_krw', 0):>13,.0f}"
              f"{c.get('avg_pct', 0):>7.3f}%  "
              f"{'PASS' if row['gate']['pass'] else 'FAIL'}")
    passed = [o for o in graded if o["gate"]["pass"]]
    print(f"\n통과 {len(passed)}셀 / {len(graded)}셀 · 기록: {out_path}", flush=True)
    if not passed:
        print("사전 등록 §4: 통과 셀 0 → 밴드 3 방향을 닫는다(등록부 §3).", flush=True)


if __name__ == "__main__":
    main()
