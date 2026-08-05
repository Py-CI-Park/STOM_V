"""후보 규칙 진단 — 풀링 기대값과 일평균이 갈리는 이유를 수치로 드러낸다.

"기대값이 +0.45%/건인데 일 검정 p=1.0" 같은 결과를 만나면, 통계 코드의 결함인지
실제 편중인지 반드시 구분해야 한다. 이 모듈은 일별 분포를 통째로 보여준다.

사용:
    python -m ai_strategy_loop.labeling.diagnose_rule --rule "TP3.0/SL2.0"
"""

from __future__ import annotations

import argparse
import json
import os

import numpy as np
import pandas as pd
from scipy import stats

from ai_strategy_loop.labeling.lanes import LANES
from ai_strategy_loop.labeling.run_p3 import MIN_VARIABLES, RULES, TICK_VARIABLES, _load
from ai_strategy_loop.labeling.universe import expectancy

_LABEL_ROOT = os.path.join(os.path.dirname(__file__), "..", "state", "labels")


def _apply(frame: pd.DataFrame, clauses: list[dict]) -> pd.DataFrame:
    mask = pd.Series(True, index=frame.index)
    for clause in clauses:
        column = frame[clause["변수"]]
        mask &= column > clause["임계"] if clause["연산자"] == ">" else column <= clause["임계"]
    return frame[mask]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", choices=sorted(LANES), default="tick")
    parser.add_argument("--out-name", default="design_v2")
    parser.add_argument("--rule", required=True, help='예: "TP3.0/SL2.0"')
    parser.add_argument("--warmup", type=int, default=60)
    args = parser.parse_args()

    lane = LANES[args.lane]
    report = json.load(open(os.path.join(_LABEL_ROOT, args.out_name, "_p3_report.json"),
                            encoding="utf-8"))
    pick = next(r for r in report["results"] if r["rule"] == args.rule)
    tp_pct = float(args.rule.split("/")[0].removeprefix("TP"))
    sl_pct = float(args.rule.split("/")[1].removeprefix("SL"))
    tp_col, sl_col = next((t, s) for a, b, t, s in RULES
                          if abs(a - tp_pct) < 1e-9 and abs(b - sl_pct) < 1e-9)

    variables = TICK_VARIABLES if lane.name == "tick" else MIN_VARIABLES
    timeout_label = f"frA_{lane.path_window}"
    base = ["일자", "종목코드", "시분초", "경과", "관심종목", "현재가", "spread_pct",
            timeout_label, "flag_no_trade", "flag_limit_up", "flag_vi_near"]
    frame = _load(args.out_name, base + [tp_col, sl_col] + variables, args.warmup)
    subset = _apply(frame, pick["clauses"])

    rule = dict(tp_pct=tp_pct, sl_pct=sl_pct, tp=tp_col, sl=sl_col,
                horizon=lane.barrier_horizon, timeout_label=timeout_label)
    pooled = expectancy(subset, **rule)

    rows = []
    for day, group in subset.groupby("일자"):
        stat = expectancy(group, **rule)
        rows.append({"일자": int(day), "n": stat["n"], "exp": stat["expectancy_pct"],
                     "win": stat["win_n"], "loss": stat["loss_n"], "timeout": stat["timeout_n"]})
    daily = pd.DataFrame(rows)
    values = daily["exp"].to_numpy()
    t_stat, p_two = stats.ttest_1samp(values, 0.0)

    print(f"규칙 {args.rule} · 절 {len(pick['clauses'])}개")
    for clause in pick["clauses"]:
        print(f"   {clause['변수']} {clause['연산자']} {clause['임계']:.6g} (분위 {clause['분위']})")
    print(f"\n풀링: n={pooled['n']:,} · 기대값 {pooled['expectancy_pct']:+.4f}% · "
          f"승 {pooled['win_n']} 패 {pooled['loss_n']} 시간종료 {pooled['timeout_n']}")
    print(f"일수 {len(daily)} · 일평균 기대값 {values.mean():+.4f}% · 중앙값 {np.median(values):+.4f}% · "
          f"양수 일수 {(values > 0).sum()}/{len(values)} ({(values > 0).mean()*100:.1f}%)")
    print(f"t={t_stat:.3f} p(양측)={p_two:.4f} → 단측 p={p_two/2 if t_stat > 0 else 1.0:.4f}")
    print(f"NaN 일수: {int(np.isnan(values).sum())}")

    daily = daily.sort_values("exp", ascending=False)
    print("\n상위 5일:"); print(daily.head(5).to_string(index=False))
    print("\n하위 5일:"); print(daily.tail(5).to_string(index=False))
    top5 = daily.head(5)
    contribution = float((top5["exp"] * top5["n"]).sum() /
                         (daily["exp"] * daily["n"]).sum() * 100) if pooled["expectancy_pct"] else 0.0
    print(f"\n상위 5일이 총손익에 기여한 비중: {contribution:.1f}%")
    print(f"거래수 상위 20% 일의 평균 기대값: "
          f"{daily.nlargest(max(len(daily)//5, 1), 'n')['exp'].mean():+.4f}%")
    print(f"거래수 하위 80% 일의 평균 기대값: "
          f"{daily.nsmallest(len(daily) - max(len(daily)//5, 1), 'n')['exp'].mean():+.4f}%")


if __name__ == "__main__":
    main()
