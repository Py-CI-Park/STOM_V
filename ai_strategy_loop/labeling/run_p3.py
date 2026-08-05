"""QSP10 P3 실행기 — 배리어 규칙 그리드 × 수렴 루프 → 손익분기 돌파 탐색.

산출: state/labels/<out>/_p3_report.json (관측 권위). 게이트 판정 포함:
기대값 > 0 이고 일 클러스터 유의(p<0.05)한 조합이 1개 이상인가.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import time

import pandas as pd

from ai_strategy_loop.labeling.converge import converge
from ai_strategy_loop.labeling.lanes import LANES
from ai_strategy_loop.labeling.universe import apply_universe

_LABEL_ROOT = os.path.join(os.path.dirname(__file__), "..", "state", "labels")

#: 배리어 규칙 그리드 — (익절%, 손절%, 익절열, 손절열)
RULES = (
    (2.0, 1.0, "hit_up_2", "hit_dn_1"),
    (1.0, 1.0, "hit_up_1", "hit_dn_1"),
    (3.0, 1.0, "hit_up_3", "hit_dn_1"),
    (2.0, 2.0, "hit_up_2", "hit_dn_2"),
    (3.0, 2.0, "hit_up_3", "hit_dn_2"),
    (5.0, 3.0, "hit_up_5", "hit_dn_3"),
)

TICK_VARIABLES = [
    "등락율", "체결강도", "초당거래대금", "초당순매수금액", "당일거래대금", "거래대금증감",
    "전일비", "회전율", "전일동시간비", "시가총액", "고저평균대비등락율", "저가대비고가등락율",
    "매도총잔량", "매수총잔량", "시가등락율", "시가대비등락율", "spread_pct", "일중위치", "분",
]
MIN_VARIABLES = [v.replace("초당", "분당") for v in TICK_VARIABLES]


def _load(out_name: str, columns: list[str], warmup: int) -> pd.DataFrame:
    directory = os.path.join(_LABEL_ROOT, out_name)
    files = sorted(glob.glob(os.path.join(directory, "day=*.parquet")))
    if not files:
        raise SystemExit(f"라벨이 없습니다: {directory}")
    sample = pd.read_parquet(files[0])
    # 중복 열 이름은 반드시 제거한다 — 중복이 있으면 frame[name] 이 DataFrame 을 돌려주고
    #   불리언 마스크 연산이 NotImplemented 로 죽는다(실측: spread_pct 가 기본·변수 양쪽에).
    keep = list(dict.fromkeys(c for c in columns if c in sample.columns))
    frame = pd.concat([pd.read_parquet(f, columns=keep) for f in files], ignore_index=True)
    return apply_universe(frame, warmup=warmup)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", choices=sorted(LANES), default="tick")
    parser.add_argument("--out-name", default="design_v2")
    parser.add_argument("--warmup", type=int, default=60)
    args = parser.parse_args()

    lane = LANES[args.lane]
    variables = TICK_VARIABLES if lane.name == "tick" else MIN_VARIABLES
    timeout_label = f"frA_{lane.path_window}"
    base_columns = ["일자", "종목코드", "시분초", "경과", "관심종목", "현재가", "spread_pct",
                    timeout_label, "flag_no_trade", "flag_limit_up", "flag_vi_near"]
    hit_columns = sorted({c for rule in RULES for c in rule[2:]})

    t0 = time.time()
    frame = _load(args.out_name, base_columns + hit_columns + variables, args.warmup)
    print(f"집행 우주 {len(frame):,}행 · {time.time()-t0:.0f}s", flush=True)

    available = [v for v in variables if v in frame.columns]
    results = []
    for tp_pct, sl_pct, tp, sl in RULES:
        if tp not in frame.columns or sl not in frame.columns:
            continue
        outcome = converge(frame, variables=available, tp_pct=tp_pct, sl_pct=sl_pct,
                           tp=tp, sl=sl, horizon=lane.barrier_horizon,
                           timeout_label=timeout_label)
        final = outcome.steps[-1] if outcome.steps else None
        record = {
            "rule": f"TP{tp_pct}/SL{sl_pct}",
            "base": outcome.rule["base"],
            "clauses": outcome.clauses(),
            "final": final.stats if final else outcome.rule["base"],
            "cluster": final.cluster if final else None,
            "day_p_value": final.day_p_value if final else 1.0,
            "day_clusters": final.day_clusters if final else 0,
        }
        results.append(record)
        stats_ = record["final"]
        print(f"{record['rule']}: 절 {len(record['clauses'])}개 · n={stats_['n']:,} · "
              f"승률 {stats_['win_rate']:.3f} (분기 {stats_['breakeven_win_rate']:.3f}) · "
              f"기대값 {stats_['expectancy_pct']:+.4f}%/건 · p={record['day_p_value']:.4f} "
              f"(일수 {record['day_clusters']}) · {time.time()-t0:.0f}s", flush=True)

    passing = [r for r in results
               if r["final"]["expectancy_pct"] > 0 and r["day_p_value"] < 0.05]
    report = {"lane": lane.name, "universe_rows": int(len(frame)),
              "universe_version": frame.attrs.get("universe_version"),
              "warmup": args.warmup, "results": results,
              "gate_breakeven_passed": bool(passing),
              "passing_rules": [r["rule"] for r in passing],
              "elapsed_sec": round(time.time() - t0, 1)}
    path = os.path.join(_LABEL_ROOT, args.out_name, "_p3_report.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2, default=float)
    print(json.dumps({"gate": report["gate_breakeven_passed"],
                      "passing": report["passing_rules"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
