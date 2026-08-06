"""W4-b 엔진 실측 — 지도 축과 엔진 축을 **같은 자**로 재는 유일한 방법.

지도(재현 게이트)는 "챔피언 진입 위에서 trailing(arm+3/give1.5)이 건당 +0.2493%"
라고 말한다. 그러나 지도는 자본 경로(동시보유·자본 한도)도, 호가 체결도, 챔피언의
실제 매도 8종도 모르는 근사다. 엔진만이 심판이다.

## 설계 — 진입 고정 A/B

진입은 챔피언 원본(`Tick_B_902_905`) 그대로 두고 **매도만 바꾼다**. 진입까지 바꾸면
성적 차이가 매도에서 온 것인지 진입에서 온 것인지 분리할 수 없다.

| 팔 | 매도 | 역할 |
|---|---|---|
| A | `Tick_S_902_905` (원본 8종) | 기준선 — 같은 설정에서 재측정 |
| B~ | 렌더된 trailing (재현 게이트 통과 셀) | 도전자 |

A 를 "기록된 과거 수치"가 아니라 **이번 런에서 다시 재는** 이유: 기간·엔진 수·설정이
조금만 달라도 비교가 무의미해진다. 같은 런에서 재야 A/B 다.

## 안전 경계

- 챔피언 전략 행(`Tick_B_902_905` / `Tick_S_902_905`)은 **읽기만** 한다.
- 새 매도식은 `W4_S_*` 이름공간에만 쓴다 — 기존 행 덮어쓰기 시도는 거부한다.
- 판정·채택은 하지 않는다. 결과를 기록하고 전이율 원장에 넘길 뿐이다.

사용(서버 8771 필요):
    python -m ai_strategy_loop.labeling.run_engine_measure --out-name design_v4
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import time
import urllib.parse

from ai_strategy_loop.labeling.assembler import render_trailing_sell_expression
from ai_strategy_loop.labeling.lanes import LANES
from ai_strategy_loop.labeling.run_p5 import Client, wait_for

_LABEL_ROOT = os.path.join(os.path.dirname(__file__), "..", "state", "labels")

#: 챔피언 페어 — 진입은 여기서 그대로 쓰고, 매도 A 는 기준선으로 재측정한다.
CHAMPION_BUY = "Tick_B_902_905"
CHAMPION_SELL = "Tick_S_902_905"

#: 우리가 쓸 수 있는 유일한 이름공간. 그 밖은 남의 자산이다.
OWNED_PREFIX = "W4_S_"

#: 재현 게이트 산출에서 이 규칙군만 엔진에 올린다 — 상한(미래 참조)은 판정 근거가
#: 아니므로 엔진 시간을 쓰지 않는다(헌법 5항).
_TRAILING_LABEL = re.compile(r"^trailing\(arm\+([0-9.]+)/give([0-9.]+)\)$")


def _gate_cells(out_name: str) -> tuple[dict, list[dict]]:
    """재현 게이트 결과에서 엔진에 올릴 셀을 뽑는다(정확 셀만)."""
    path = os.path.join(_LABEL_ROOT, out_name, "_reproduction_gate.json")
    with open(path, "r", encoding="utf-8") as handle:
        gate = json.load(handle)
    reproducing = set(gate.get("reproducing") or [])
    cells = [c for c in gate.get("cells", [])
             if c["rule"] in reproducing and _TRAILING_LABEL.match(c["rule"])]
    cells.sort(key=lambda c: -c["expectancy_pct"])
    return gate, cells


def _parse_rule(label: str) -> tuple[float, float]:
    match = _TRAILING_LABEL.match(label)
    if match is None:
        raise ValueError(f"트레일링 규칙 라벨이 아니다: {label}")
    return float(match.group(1)), float(match.group(2))


def _assert_owned(name: str) -> None:
    if not name.startswith(OWNED_PREFIX):
        raise ValueError(f"쓰기 금지 이름: {name} (허용 접두 {OWNED_PREFIX!r})")


def _run_arm(client: Client, *, buy: str, sell: str, lane, engines: int,
             timeout: int) -> dict:
    """한 팔을 엔진에 올리고 끝날 때까지 기다린다."""
    started = client.call("POST", "/bt/run", {
        "buy": buy, "sell": sell,
        "start": lane.design[0], "end": lane.design[1],
        "start_time": lane.entry_start if lane.name == "min" else 90000,
        "end_time": lane.forced_exit,
        "timeframe": lane.name, "engines": engines, "timeout": timeout,
    })
    job_id = started.get("job_id")
    if not job_id:
        return {"status": "no_job", "error": started, "metrics": {}}
    status = wait_for(client, job_id, timeout=timeout)
    result = client.call("GET", f"/bt/result?job_id={urllib.parse.quote(job_id)}")
    return {"job_id": job_id, "status": status, "metrics": result.get("metrics") or {}}


_METRIC_KEYS = ("trade_count", "win_rate", "avg_profit_pct", "total_profit_krw",
                "cagr", "mdd_pct", "tpi")


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-name", default="design_v4")
    parser.add_argument("--lane", choices=sorted(LANES), default="tick")
    parser.add_argument("--top", type=int, default=3, help="엔진에 올릴 트레일링 셀 수")
    parser.add_argument("--engines", type=int, default=16)
    parser.add_argument("--timeout", type=int, default=5400)
    parser.add_argument("--skip-baseline", action="store_true",
                        help="기준선(A) 재측정을 건너뛴다 — 비교가 약해지므로 기본 아님")
    args = parser.parse_args()

    lane = LANES[args.lane]
    gate, cells = _gate_cells(args.out_name)
    if gate.get("verdict") != "PASS":
        raise SystemExit(f"재현 게이트가 {gate.get('verdict')} 다 — 엔진 실측 대상이 아니다.")
    if not cells:
        raise SystemExit("엔진에 올릴 정확(exact) 트레일링 셀이 없다.")
    picks = cells[:args.top]

    client = Client()
    t0 = time.time()
    outcomes: list[dict] = []

    # --- A: 기준선(챔피언 원본 매도) ------------------------------------------
    baseline_metrics: dict = {}
    if not args.skip_baseline:
        print(f"[A] 기준선 {CHAMPION_BUY} + {CHAMPION_SELL} 재측정 …", flush=True)
        arm = _run_arm(client, buy=CHAMPION_BUY, sell=CHAMPION_SELL, lane=lane,
                       engines=args.engines, timeout=args.timeout)
        baseline_metrics = arm["metrics"]
        outcomes.append({
            "name": "W4_A_champion_baseline",
            "rule": "챔피언 원본 매도(8종)",
            "arm": "baseline",
            "buy": CHAMPION_BUY, "sell": CHAMPION_SELL,
            "job_id": arm.get("job_id"), "status": arm["status"],
            # 지도에 대응 값이 없다 — 원본 매도는 지도 축으로 평가되지 않았다.
            "predicted": None,
            "engine": {k: baseline_metrics.get(k) for k in _METRIC_KEYS},
            "transfer_ratio": None,
        })
        print(f"    → {arm['status']} 거래={baseline_metrics.get('trade_count')} "
              f"건당={baseline_metrics.get('avg_profit_pct')}%", flush=True)

    # --- B~: 도전자(렌더된 트레일링) ------------------------------------------
    for index, cell in enumerate(picks, start=1):
        arm_pct, give_pct = _parse_rule(cell["rule"])
        sell_name = f"{OWNED_PREFIX}TRAIL_{arm_pct:g}_{give_pct:g}".replace(".", "p")
        _assert_owned(sell_name)
        code = render_trailing_sell_expression(
            name=sell_name, arm_pct=arm_pct, give_pct=give_pct,
            horizon=lane.barrier_horizon, forced_exit=lane.forced_exit,
        )
        saved = client.call("POST", "/bt/strategy",
                            {"kind": "sell", "name": sell_name, "code": code,
                             "overwrite": True})
        print(f"[B{index}] 매도 등록 {sell_name} {saved.get('status')}", flush=True)

        run = _run_arm(client, buy=CHAMPION_BUY, sell=sell_name, lane=lane,
                       engines=args.engines, timeout=args.timeout)
        metrics = run["metrics"]
        map_pct = float(cell["expectancy_pct"])
        engine_pct = metrics.get("avg_profit_pct")
        transfer = (float(engine_pct) / map_pct) if (engine_pct is not None and map_pct) else None
        outcomes.append({
            "name": sell_name,
            "rule": cell["rule"],
            "arm": f"challenger_{index}",
            "buy": CHAMPION_BUY, "sell": sell_name,
            "job_id": run.get("job_id"), "status": run["status"],
            # 지도 예측 — 재현 게이트가 챔피언 진입 위에서 잰 값 그대로.
            "predicted": {"expectancy_pct": map_pct, "rows": cell["n"],
                          "day_mean_pct": cell.get("day_mean_pct")},
            "engine": {k: metrics.get(k) for k in _METRIC_KEYS},
            "transfer_ratio": transfer,
        })
        print(f"    → {run['status']} 거래={metrics.get('trade_count')} "
              f"건당={engine_pct}% 전이율={transfer}", flush=True)

    # --- 요약 ------------------------------------------------------------------
    base_pct = baseline_metrics.get("avg_profit_pct")
    print(f"\n=== 엔진 실측 요약 (설계 {lane.design[0]}~{lane.design[1]}) ===", flush=True)
    for row in outcomes:
        engine = row["engine"]
        delta = ""
        if base_pct is not None and engine.get("avg_profit_pct") is not None \
                and row["arm"] != "baseline":
            delta = f" Δ건당={float(engine['avg_profit_pct']) - float(base_pct):+.4f}%p"
        print(f" {row['rule']:<34} 거래={engine.get('trade_count')} "
              f"건당={engine.get('avg_profit_pct')}% CAGR={engine.get('cagr')} "
              f"MDD={engine.get('mdd_pct')}{delta}", flush=True)

    out_path = os.path.join(_LABEL_ROOT, args.out_name, "_p5_engine_report.json")
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump({
            "lane": lane.name,
            "design": list(lane.design),
            "champion_buy": CHAMPION_BUY,
            "baseline_sell": CHAMPION_SELL,
            "baseline_metrics": {k: baseline_metrics.get(k) for k in _METRIC_KEYS},
            "outcomes": outcomes,
            "note": ("진입 고정 A/B — 매도만 바꿨다. 전이율은 지도(재현 게이트) 대비 "
                     "엔진 실측 비율이며, 부호가 뒤집히면 감쇠가 아니라 구조 불일치다."),
        }, handle, ensure_ascii=False, indent=1, default=float)
    print(f"\n저장: {os.path.abspath(out_path)} · 총 {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
