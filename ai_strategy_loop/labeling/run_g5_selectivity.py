"""G5 — 선택도 사다리. 밀도를 낮추면 lift 가 남는지 판정한다.

사전 등록: `docs/research/quant_scoring_pipeline/2026-08-13_G5_사전등록.md`
(커밋 `78908436` — 실행 전)

## G2 가 남긴 질문

G2 는 3셀 전부 엔진 타임아웃했고, 원인은 수익성이 아니라 **신호 밀도**였다
(초소형 3,212초/일 vs 챔피언 0.43건/일 = 7,469배). G5 는 같은 세그먼트에
선택도 제약만 걸어 밀도를 낮추고, 그 지점에서 우위가 남는지 엔진으로 묻는다.

## 이 라운드가 G 레인의 마지막 질문이다

전 셀이 흑자에 실패하면 "채굴 lift 는 밀도를 낮추면 사라진다"가 확정되고
생성 레인을 근거를 갖고 닫는다(사전 등록 §4 판정 규칙).

사용:
    python -m ai_strategy_loop.labeling.run_g5_selectivity --out-name design_v5 --stage train
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from typing import Any, Final

from ai_strategy_loop.labeling.lanes import LANES
from ai_strategy_loop.labeling.run_engine_measure import (
    CHAMPION_BUY, CHAMPION_SELL, _METRIC_KEYS, _run_arm)
from ai_strategy_loop.labeling.run_g2_assemble import BANDS, gate, render_strategy
from ai_strategy_loop.labeling.run_p5 import Client
from ai_strategy_loop.labeling.run_trade_autopsy import (
    _LABEL_ROOT, calendar_days, split_days)

OWNED_PREFIX: Final = "G5_B_"

#: 사전 등록 §3 — 격자 3셀 고정. (이름, 분위 수위, 밴드)
CELLS: Final = (
    ("Q50_ALL", "q50", BANDS),
    ("Q50_BAND1", "q50", BANDS[:1]),
    ("Q75_ALL", "q75", BANDS),
)

#: 사전 등록 §3 — 셀당 상한 90분(G2 에서 2.5시간을 소진한 경험 반영).
CELL_TIMEOUT: Final = 5400


def cell_names() -> list[str]:
    return [name for name, _, _ in CELLS]


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-name", default="design_v5")
    parser.add_argument("--stage", choices=("train", "valid"), required=True)
    parser.add_argument("--capital-limit", type=float, default=20_000_000)
    parser.add_argument("--engines", type=int, default=16)
    parser.add_argument("--render-only", action="store_true")
    args = parser.parse_args()

    root = os.path.join(_LABEL_ROOT, args.out_name)
    with open(os.path.join(root, "_g1_setup_distribution.json"),
              encoding="utf-8") as handle:
        seeds = json.load(handle)["seeds"]
    if not seeds:
        raise SystemExit("G1 시드가 없다")

    if args.render_only:
        for name, quantile, bands in CELLS:
            print(f"===== {name} (={quantile} · 밴드 {len(bands)}) =====")
            print(render_strategy(seeds, "LOWER", quantile=quantile, bands=bands))
        return

    lane = LANES["tick"]
    split = split_days(calendar_days(args.out_name))
    days = split[args.stage]
    span = (days[0], days[-1])
    cells = list(CELLS)
    if args.stage == "valid":
        train_path = os.path.join(root, "_g5_selectivity_train.json")
        if not os.path.exists(train_path):
            raise SystemExit("1차(train) 결과가 없다 — 순서를 지켜라")
        with open(train_path, encoding="utf-8") as handle:
            passed = [o["cell"] for o in json.load(handle)["outcomes"]
                      if o.get("gate", {}).get("pass")]
        if not passed:
            raise SystemExit("1차 통과 셀이 없다 — 검증을 돌 이유가 없다")
        cells = [c for c in CELLS if c[0] in passed][:2]
        print(f"[2차] 1차 통과만 검증: {[c[0] for c in cells]}", flush=True)

    client = Client()
    outcomes: list[dict] = []
    report: dict[str, Any] = {
        "stage": args.stage, "span": list(span), "days": len(days),
        "prereg": "2026-08-13_G5_사전등록.md (78908436)",
        "cell_timeout": CELL_TIMEOUT,
        "champion_metrics": {}, "outcomes": outcomes, "complete": False,
    }
    out_path = os.path.join(root, f"_g5_selectivity_{args.stage}.json")

    def save() -> None:
        with open(out_path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=1, default=float)

    t0 = time.time()
    print(f"[구간] {args.stage} {len(days)}일 {span} · 셀 상한 {CELL_TIMEOUT}초", flush=True)
    champ = _run_arm(client, buy=CHAMPION_BUY, sell=CHAMPION_SELL, lane=lane,
                     engines=args.engines, timeout=CELL_TIMEOUT, period=span)
    report["champion_metrics"] = {k: champ["metrics"].get(k) for k in _METRIC_KEYS}
    champion_krw = float(report["champion_metrics"].get("total_profit_krw") or 0.0)
    print(f"[기준] 챔피언 {champ['status']} "
          f"거래={champ['metrics'].get('trade_count')} "
          f"총수익금={champion_krw:,.0f}", flush=True)
    save()

    for name, quantile, bands in cells:
        buy_name = f"{OWNED_PREFIX}{name}"
        code = render_strategy(seeds, "LOWER", quantile=quantile, bands=bands)
        saved = client.call("POST", "/bt/strategy",
                            {"kind": "buy", "name": buy_name, "code": code,
                             "overwrite": True})
        print(f"[{name}] 등록 ({quantile} · 밴드 {len(bands)}) {saved.get('status')}",
              flush=True)
        started = time.time()
        run = _run_arm(client, buy=buy_name, sell=CHAMPION_SELL, lane=lane,
                       engines=args.engines, timeout=CELL_TIMEOUT, period=span)
        metrics = {k: run["metrics"].get(k) for k in _METRIC_KEYS}
        g = gate(metrics, champion_krw=champion_krw,
                 capital_limit_krw=args.capital_limit)
        # 사전 등록 §4-E: 완주하지 못하면 통과 불가.
        g["finished_pass"] = run["status"] == "success"
        g["pass"] = bool(g["pass"] and g["finished_pass"])
        outcomes.append({"cell": name, "quantile": quantile,
                         "bands": len(bands), "buy": buy_name,
                         "job_id": run.get("job_id"), "status": run["status"],
                         "elapsed_sec": round(time.time() - started),
                         "engine": metrics, "gate": g})
        print(f"    → {run['status']} ({time.time()-started:.0f}초) "
              f"거래={metrics.get('trade_count')} "
              f"동시보유={metrics.get('max_hold_count')} "
              f"총수익금={metrics.get('total_profit_krw')} "
              f"{'PASS' if g['pass'] else 'FAIL'}", flush=True)
        save()

    report["complete"] = True
    save()

    print(f"\n=== G5 {args.stage} ({len(days)}일 · {time.time()-t0:.0f}초) ===")
    print(f" {'셀':<12}{'상태':<9}{'거래':>7}{'동시':>5}{'건당':>8}{'총수익금':>13}  판정")
    print(f" {'챔피언':<12}{champ['status']:<9}"
          f"{report['champion_metrics'].get('trade_count'):>7}"
          f"{report['champion_metrics'].get('max_hold_count'):>5}"
          f"{report['champion_metrics'].get('avg_profit_pct'):>7}%"
          f"{champion_krw:>13,.0f}  기준")
    for row in outcomes:
        e = row["engine"]
        print(f" {row['cell']:<12}{row['status']:<9}"
              f"{e.get('trade_count') or 0:>7}{e.get('max_hold_count') or 0:>5}"
              f"{e.get('avg_profit_pct') or 0:>7}%"
              f"{e.get('total_profit_krw') or 0:>13,.0f}  "
              f"{'PASS' if row['gate']['pass'] else 'FAIL'}")
    if not any(o["gate"]["pass"] for o in outcomes):
        print("\n사전 등록 §4: 1차 전멸 → 반대 가설 성립 · G 레인 종결 절차로 간다.")
    print(f"\n기록: {out_path}", flush=True)


if __name__ == "__main__":
    main()
