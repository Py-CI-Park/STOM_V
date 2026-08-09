"""엔진 축 사다리 실행기 — 엔진 A/B 결과를 실제 체결 기록으로 재심판한다.

`run_engine_measure` 가 남긴 `_p5_engine_report.json` 의 job 들을 백테스트 DB 에서
찾아 팔로 만들고, 챔피언을 합격선으로 도전자를 심판한다. 산출은 페이지 28 이 읽는다.

사용:
    python -m ai_strategy_loop.labeling.run_engine_ladder --out-name design_v4
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sqlite3
import sys
import time

from ai_strategy_loop.labeling.engine_ladder import Arm, judge, load_arm

_LABEL_ROOT = os.path.join(os.path.dirname(__file__), "..", "state", "labels")
_DB = os.path.join(os.path.dirname(__file__), "..", "..", "_database", "backtest.db")

_METRIC_KEYS = ("seed_capital", "cagr", "mdd_pct", "total_profit_pct")


def _tables(db_path: str) -> list[str]:
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        return [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    finally:
        con.close()


def resolve_table(tables: list[str], buy_name: str, job_id: str) -> str | None:
    """job_id → 결과 테이블.

    테이블 이름은 `stock_bt_<매수전략>_<완료시각>` 이고 job_id 는 **시작** 시각이라
    정확히 일치하지 않는다. 같은 매수전략 테이블 중 job 시작 시각 **직후**의 것을
    고른다(엔진은 job 을 순차 실행하므로 그 사이에 다른 완료가 끼지 않는다).
    """
    stamp = "".join(ch for ch in job_id.split("_")[0] + job_id.split("_")[1]
                    if ch.isdigit())[:14]
    prefix = f"stock_bt_{buy_name}_"
    candidates = sorted(t for t in tables if t.startswith(prefix))
    after = [t for t in candidates if t[len(prefix):] >= stamp]
    return after[0] if after else None


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-name", default="design_v4")
    parser.add_argument("--segments", type=int, default=4)
    # 구간을 바꿔 잰 실측(예: `_ext`)을 정본과 나란히 심판하기 위한 접미.
    parser.add_argument("--tag", default="", help="리포트 접미(_ext 등)")
    args = parser.parse_args()

    report_path = os.path.join(_LABEL_ROOT, args.out_name,
                               f"_p5_engine_report{args.tag}.json")
    with open(report_path, "r", encoding="utf-8") as handle:
        report = json.load(handle)

    db_path = os.path.abspath(_DB)
    tables = _tables(db_path)
    t0 = time.time()

    arms: dict[str, Arm] = {}
    order: list[str] = []
    for outcome in report.get("outcomes") or []:
        job_id = outcome.get("job_id")
        buy = outcome.get("buy") or report.get("champion_buy")
        if not job_id or not buy:
            continue
        table = resolve_table(tables, str(buy), str(job_id))
        if table is None:
            print(f"[건너뜀] 결과 테이블을 못 찾음: {outcome.get('rule')} ({job_id})", flush=True)
            continue
        engine = outcome.get("engine") or {}
        arm = load_arm(db_path, table, str(outcome.get("rule")),
                       seed_capital=None, cagr=engine.get("cagr"),
                       mdd_pct=engine.get("mdd_pct"),
                       total_profit_pct=engine.get("total_profit_pct"))
        arms[outcome["arm"]] = arm
        order.append(outcome["arm"])
        print(f"읽음: {arm.name:<28} {len(arm.trades):>4}건  ({table})", flush=True)

    baseline = arms.get("baseline")
    if baseline is None:
        raise SystemExit("기준선(챔피언) 팔이 없다 — 엔진 A/B 를 기준선 포함으로 다시 돌려라.")

    results = []
    for key in order:
        if key == "baseline":
            continue
        verdict = judge(baseline, arms[key], segments=args.segments)
        results.append(verdict)

    print(f"\n=== 엔진 축 사다리 (합격선 = 챔피언) ===", flush=True)
    base_pos = results[0]["regime"]["baseline_positive"] if results else None
    print(f"챔피언 국면 양수 {base_pos}/{args.segments} ← 이것이 합격선이다\n", flush=True)
    for r in results:
        p = r["paired"]
        print(f" {r['challenger']:<28} {r['verdict']:<10} "
              f"국면 {r['regime']['challenger_positive']}/{args.segments} · "
              f"짝지은 차이 {p.get('mean_diff_pct', float('nan')):+.4f}%p "
              f"(95% [{p.get('ci95', [float('nan')]*2)[0]:+.3f}, "
              f"{p.get('ci95', [float('nan')]*2)[1]:+.3f}]) · "
              f"개선 {p.get('improved_trades')}건/악화 {p.get('worsened_trades')}건", flush=True)
        if p.get("available") and not p.get("significant"):
            need = p.get("required_pairs")
            print(f"   └ 표본 {p['pairs']}건 → 확정하려면 {need:,.0f}건 필요 "
                  f"({p.get('sample_shortfall_ratio', 0):.1f}배)", flush=True)

    out_path = os.path.join(_LABEL_ROOT, args.out_name, f"_engine_ladder{args.tag}.json")
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump({
            "axis": "engine_executed_trades",
            "baseline": baseline.name,
            "segments": args.segments,
            "results": results,
            "note": ("심판은 엔진 체결 기록이다. 합격선은 절대 기준이 아니라 챔피언이며, "
                     "챔피언이 떨어지는 기준은 기준이 틀린 것이다."),
        }, handle, ensure_ascii=False, indent=1, default=float)
    print(f"\n저장: {os.path.abspath(out_path)} · {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
