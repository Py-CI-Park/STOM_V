"""HOF5 — 고고학 2종(회전율·전일비 완화)을 분할 구간에서 엔진으로 재판정한다.

사전 등록: `docs/research/quant_scoring_pipeline/2026-08-12_HOF5_사전등록.md`
(커밋 `4a7e3ffb` — 실행 전)

## 이것은 재측정이다

W7 이 전 구간에서 쟀고 당시 자본 희소 정책으로 REJECT 된 후보들이다.
자본 정책이 사람 결정(W8·2,000만원 limit)으로 바뀌어 판정 근거가 무효화됐다.
같은 후보를 **학습→검증 분할**에서 현행 정책으로 새로 판정하고, 원장에는
"정책 변경 재판정"으로 명시한다. 전 구간 수치는 오염이므로 판정에 쓰지 않는다.

사용:
    python -m ai_strategy_loop.labeling.run_hof5_relax --out-name design_v5 \\
        --capital-limit 20000000 --stage train
    # 1차(train) 통과 후보가 있을 때만:
    python -m ai_strategy_loop.labeling.run_hof5_relax ... --stage valid
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from typing import Final

from ai_strategy_loop.labeling import champion_clauses as cc
from ai_strategy_loop.labeling.lanes import LANES
from ai_strategy_loop.labeling.run_engine_measure import (
    CHAMPION_BUY, CHAMPION_SELL, _METRIC_KEYS, _run_arm)
from ai_strategy_loop.labeling.run_entry_relax import champion_buy_code
from ai_strategy_loop.labeling.run_p5 import Client
from ai_strategy_loop.labeling.run_trade_autopsy import calendar_days, split_days

_LABEL_ROOT = os.path.join(os.path.dirname(__file__), "..", "state", "labels")

#: 이 러너가 쓸 수 있는 유일한 이름공간.
OWNED_PREFIX: Final = "HOF5_B_"

#: 사전 등록 §3 — 후보 2종 고정. 추가 금지.
CANDIDATES: Final = ("902_회전율", "905_전일비")


def hof5_gate(baseline: dict, engine: dict, *, capital_limit_krw: float) -> dict:
    """사전 등록 §4 — A 총수익금 초과 · B 흑자 · C 자금 · D 거래 증가(검증용)."""
    def num(src: dict, key: str) -> float | None:
        value = src.get(key)
        return None if value is None else float(value)

    money, base_money = num(engine, "total_profit_krw"), num(baseline, "total_profit_krw")
    seed = num(engine, "seed_capital")
    trades = engine.get("trade_count") or 0
    base_trades = baseline.get("trade_count") or 0
    per, base_per = num(engine, "avg_profit_pct"), num(baseline, "avg_profit_pct")

    beats = money is not None and base_money is not None and money > base_money
    positive = money is not None and money > 0
    capital = seed is not None and seed <= float(capital_limit_krw)
    more = trades >= base_trades
    return {
        "capital_policy": "limit", "capital_limit_krw": float(capital_limit_krw),
        "money_pass": bool(beats), "positive_pass": bool(positive),
        "capital_pass": bool(capital), "more_trades": bool(more),
        "per_trade_ref": bool(per is not None and base_per is not None
                              and per >= base_per),
        "trade_gain": trades - base_trades,
        "pass": bool(beats and positive and capital and more),
    }


def sync_ledger(report: dict, *, stage: str) -> int:
    """정책 변경 재판정임을 원장에 명시한다. 진입 계열 — PROMISING 상한."""
    from datetime import datetime, timezone

    from ai_strategy_loop.controller.strategy_ledger import CandidateRecord, append

    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    span = report.get("span") or [None, None]
    written = 0
    for outcome in report.get("outcomes") or []:
        if outcome.get("arm") == "baseline" or not outcome.get("gate"):
            continue
        engine, gate = outcome.get("engine") or {}, outcome["gate"]
        if stage == "train":
            verdict = "MIXED" if gate.get("pass") else "REJECT"
            reason = (f"HOF5 1차(학습 411일) {'통과 — 검증 대기' if gate.get('pass') else '실패'} · "
                      f"총수익금 {engine.get('total_profit_krw')} vs "
                      f"{report['baseline_metrics'].get('total_profit_krw')}")
        else:
            verdict = "PROMISING" if gate.get("pass") else "REJECT"
            reason = (f"HOF5 2차(검증 203일) {'통과' if gate.get('pass') else '실패'} · "
                      f"총수익금 {engine.get('total_profit_krw')} vs "
                      f"{report['baseline_metrics'].get('total_profit_krw')}")
        append(CandidateRecord(
            candidate_id=f"{outcome.get('buy')}::{CHAMPION_SELL}",
            family="entry", source="ai", lane="tick",
            verdict=verdict, recorded_at=stamp,
            buy_name=outcome.get("buy"), sell_name=CHAMPION_SELL,
            period_start=span[0], period_end=span[1],
            job_id=outcome.get("job_id"),
            trades=engine.get("trade_count"), win_rate=engine.get("win_rate"),
            avg_profit_pct=engine.get("avg_profit_pct"),
            total_profit_krw=engine.get("total_profit_krw"),
            seed_capital=engine.get("seed_capital"),
            total_profit_pct=engine.get("total_profit_pct"),
            cagr=engine.get("cagr"), mdd_pct=engine.get("mdd_pct"),
            tpi=engine.get("tpi"), avg_hold_sec=engine.get("avg_hold_time"),
            max_hold_count=engine.get("max_hold_count"),
            baseline_id=f"{CHAMPION_BUY}::{CHAMPION_SELL}",
            verdict_reason=reason,
            notes=("W7 완화의 **정책 변경 재판정**(ratio→limit, W8 사용자 확정). "
                   "짝지은 검정 없음(진입 상이) — PROMISING 이 상한. "
                   "표본 밖 확인 전이며 실전 후보가 아니다. "
                   "사전 등록: 2026-08-12_HOF5_사전등록.md"),
        ))
        written += 1
    return written


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-name", default="design_v5")
    parser.add_argument("--lane", choices=sorted(LANES), default="tick")
    parser.add_argument("--capital-limit", type=float, required=True)
    parser.add_argument("--stage", choices=("train", "valid"), required=True)
    parser.add_argument("--engines", type=int, default=16)
    parser.add_argument("--timeout", type=int, default=9000)
    args = parser.parse_args()

    lane = LANES[args.lane]
    split = split_days(calendar_days(args.out_name))
    days = split[args.stage]
    span = (days[0], days[-1])
    out_path = os.path.join(_LABEL_ROOT, args.out_name,
                            f"_hof5_relax_{args.stage}.json")

    keys = list(CANDIDATES)
    if args.stage == "valid":
        train_path = os.path.join(_LABEL_ROOT, args.out_name, "_hof5_relax_train.json")
        if not os.path.exists(train_path):
            raise SystemExit("1차(train) 결과가 없다 — 순서를 지켜라")
        with open(train_path, "r", encoding="utf-8") as handle:
            train_report = json.load(handle)
        keys = [o["clause"] for o in train_report.get("outcomes") or []
                if o.get("gate") and o["gate"].get("pass")]
        if not keys:
            raise SystemExit("1차 통과 후보가 없다 — 검증을 돌 이유가 없다")
        print(f"[2차] 1차 통과 후보만 검증: {keys}", flush=True)

    champion = champion_buy_code()
    client = Client()
    outcomes: list[dict] = []
    report = {
        "stage": args.stage, "span": list(span), "days": len(days),
        "prereg": "2026-08-12_HOF5_사전등록.md (4a7e3ffb)",
        "baseline_metrics": {}, "outcomes": outcomes, "complete": False,
    }

    def save() -> None:
        with open(out_path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=1, default=float)

    t0 = time.time()
    print(f"[구간] {args.stage} {len(days)}일 {span}", flush=True)
    print(f"[기준] {CHAMPION_BUY} + {CHAMPION_SELL}", flush=True)
    base = _run_arm(client, buy=CHAMPION_BUY, sell=CHAMPION_SELL, lane=lane,
                    engines=args.engines, timeout=args.timeout, period=span)
    report["baseline_metrics"] = {k: base["metrics"].get(k) for k in _METRIC_KEYS}
    outcomes.append({"arm": "baseline", "buy": CHAMPION_BUY,
                     "job_id": base.get("job_id"), "status": base["status"],
                     "engine": report["baseline_metrics"], "gate": None})
    print(f"    → {base['status']} 거래={base['metrics'].get('trade_count')} "
          f"총수익금={base['metrics'].get('total_profit_krw')}", flush=True)
    save()

    for key in keys:
        buy_name = f"{OWNED_PREFIX}RELAX_{key}"
        if not buy_name.startswith(OWNED_PREFIX):
            raise SystemExit(f"쓰기 금지 이름: {buy_name}")
        code = cc.drop_clause_from_dsl(champion, key)
        saved = client.call("POST", "/bt/strategy",
                            {"kind": "buy", "name": buy_name, "code": code,
                             "overwrite": True})
        print(f"[후보 {key}] 등록 {saved.get('status')}", flush=True)
        run = _run_arm(client, buy=buy_name, sell=CHAMPION_SELL, lane=lane,
                       engines=args.engines, timeout=args.timeout, period=span)
        metrics = {k: run["metrics"].get(k) for k in _METRIC_KEYS}
        gate = hof5_gate(report["baseline_metrics"], metrics,
                         capital_limit_krw=args.capital_limit)
        outcomes.append({"arm": f"relax_{key}", "clause": key, "buy": buy_name,
                         "job_id": run.get("job_id"), "status": run["status"],
                         "engine": metrics, "gate": gate})
        print(f"    → {run['status']} 거래={metrics.get('trade_count')} "
              f"({gate['trade_gain']:+d}) 건당={metrics.get('avg_profit_pct')}% "
              f"총수익금={metrics.get('total_profit_krw')} "
              f"{'PASS' if gate['pass'] else 'FAIL'}", flush=True)
        save()

    report["complete"] = True
    save()
    written = sync_ledger(report, stage=args.stage)

    print(f"\n=== HOF5 {args.stage} ({len(days)}일 · {time.time()-t0:.0f}초 "
          f"· 원장 {written}행) ===")
    print(f" {'팔':<26}{'거래':>6}{'건당':>9}{'총수익금':>12}{'자금':>12}  판정")
    for row in outcomes:
        engine = row["engine"]
        verdict = "기준" if row["arm"] == "baseline" else (
            "PASS" if row["gate"]["pass"] else "FAIL")
        print(f" {row['buy']:<26}{engine.get('trade_count'):>6}"
              f"{engine.get('avg_profit_pct'):>8}%{engine.get('total_profit_krw'):>12,.0f}"
              f"{engine.get('seed_capital'):>12,.0f}  {verdict}")
    print(f"\n기록: {out_path}", flush=True)


if __name__ == "__main__":
    main()
