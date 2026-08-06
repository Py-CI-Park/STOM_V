"""QSP12 P5 — 계층 후보를 엔진으로 실측하고 전이율을 기록한다.

지도(탐색)와 엔진(심판)의 격차는 가정하지 않고 측정한다. 지도에서 쓴 분기·절·배리어
규칙을 **그대로** 렌더해야 전이율 비교가 성립한다.

사용(서버 8771 필요):
    python -m ai_strategy_loop.labeling.run_p5_hierarchy --out-name design_v3
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
import urllib.parse

from ai_strategy_loop.labeling.assembler import render_hierarchical_buy, render_sell_expression
from ai_strategy_loop.labeling.lanes import LANES
from ai_strategy_loop.labeling.run_p5 import Client, wait_for

_LABEL_ROOT = os.path.join(os.path.dirname(__file__), "..", "state", "labels")


def main() -> None:
    # Windows 콘솔(cp949)에서 유니코드가 깨져 죽는 것을 막는다. **임포트 시점이
    #   아니라 실행 시점에** 바꾼다 — 모듈 임포트가 전역 stdout 을 갈아치우면
    #   그 모듈을 불러 쓰는 다른 스크립트의 출력이 끊긴다(실측 결함).
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", choices=sorted(LANES), default="tick")
    parser.add_argument("--out-name", default="design_v3")
    parser.add_argument("--top", type=int, default=2)
    parser.add_argument("--engines", type=int, default=16)
    args = parser.parse_args()

    lane = LANES[args.lane]
    path = os.path.join(_LABEL_ROOT, args.out_name, "_hierarchy_report.json")
    report = json.load(open(path, encoding="utf-8"))

    # 게이트 통과분만 — 일평균·합계 둘 다 양수이고 유의해야 한다.
    passing = [r for r in report["rules"]
               if r["combined"]["day_mean_pct"] > 0
               and r["combined"]["expectancy_pct"] > 0
               and r["combined"]["p_value"] < 0.05]
    if not passing:
        raise SystemExit("게이트 통과 규칙이 없습니다 — 엔진 검증 대상이 없습니다.")
    picks = sorted(passing, key=lambda r: r["combined"]["day_mean_pct"], reverse=True)[:args.top]

    client = Client()
    outcomes = []
    for index, pick in enumerate(picks, start=1):
        tp_pct = float(pick["rule"].split("/")[0].removeprefix("TP"))
        sl_pct = float(pick["rule"].split("/")[1].removeprefix("SL"))
        buy_name = f"QSP12_{args.lane}_H{index}"
        sell_name = f"QSP12_{args.lane}_S{index}"
        buy_code = render_hierarchical_buy(name=buy_name, branches=pick["branches"])
        sell_code = render_sell_expression(name=sell_name, tp_pct=tp_pct, sl_pct=sl_pct,
                                           horizon=lane.barrier_horizon,
                                           forced_exit=lane.forced_exit)
        for kind, name, code in (("buy", buy_name, buy_code), ("sell", sell_name, sell_code)):
            saved = client.call("POST", "/bt/strategy",
                                {"kind": kind, "name": name, "code": code, "overwrite": True})
            print(f"{kind}: {name} {saved.get('status')} {saved.get('message', '')}", flush=True)

        started = client.call("POST", "/bt/run", {
            "buy": buy_name, "sell": sell_name,
            "start": lane.design[0], "end": lane.design[1],
            "start_time": 90000, "end_time": lane.forced_exit,
            "timeframe": lane.name, "engines": args.engines, "timeout": 3600,
        })
        job_id = started.get("job_id")
        print(f"run: {buy_name} ({pick['rule']}) → {job_id} {started.get('status')}", flush=True)
        if not job_id:
            outcomes.append({"name": buy_name, "error": started})
            continue
        status = wait_for(client, job_id)
        result = client.call("GET", f"/bt/result?job_id={urllib.parse.quote(job_id)}")
        metrics = result.get("metrics") or {}
        predicted = pick["combined"]
        transfer = None
        if metrics.get("avg_profit_pct") is not None and predicted["expectancy_pct"]:
            transfer = float(metrics["avg_profit_pct"]) / predicted["expectancy_pct"]
        outcomes.append({
            "name": buy_name, "rule": pick["rule"], "job_id": job_id, "status": status,
            "branches": len(pick["branches"]), "predicted": predicted,
            "engine": {k: metrics.get(k) for k in
                       ("trade_count", "win_rate", "avg_profit_pct", "total_profit_krw",
                        "cagr", "mdd_pct", "tpi", "day_count", "daily_avg_trades")},
            "transfer_ratio": transfer,
        })
        print(f"done: {buy_name} status={status} 거래 {metrics.get('trade_count')} · "
              f"건당 {metrics.get('avg_profit_pct')}% · 총 {metrics.get('total_profit_krw')} · "
              f"전이율 {transfer}", flush=True)

    out = os.path.join(_LABEL_ROOT, args.out_name, "_p5_hierarchy_report.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump({"lane": lane.name, "outcomes": outcomes}, handle,
                  ensure_ascii=False, indent=2, default=float)
    print("saved:", os.path.abspath(out))


if __name__ == "__main__":
    main()
