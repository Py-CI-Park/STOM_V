"""엔진 실측 → 조건식 성과 원장 적재.

`_p5_engine_report.json`(엔진 A/B)과 `_engine_ladder.json`(엔진 축 심판)을 읽어
후보마다 원장 행을 하나씩 쌓는다. 원장은 append-only 라 다시 돌리면 새 행이 쌓인다
— 그것이 의도다(재측정 이력이 남아야 한다).

사용:
    python -m ai_strategy_loop.labeling.run_ledger_sync --out-name design_v4
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

from ai_strategy_loop.controller.strategy_ledger import CandidateRecord, append, summary
from ai_strategy_loop.labeling.run_engine_ladder import resolve_table, _tables

_LABEL_ROOT = os.path.join(os.path.dirname(__file__), "..", "state", "labels")
_BT_DB = os.path.join(os.path.dirname(__file__), "..", "..", "_database", "backtest.db")


def _read(out_name: str, filename: str) -> dict | None:
    path = os.path.join(_LABEL_ROOT, out_name, filename)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def _table_stats(db_path: str, table: str) -> dict:
    """결과 테이블에서 자본 지표를 직접 낸다 — 엔진 요약에 없는 값이 있다."""
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = con.execute(
            f'SELECT 매수시간, 매도시간, 매수금액, 수익금, 보유시간 FROM "{table}"').fetchall()
    finally:
        con.close()
    if not rows:
        return {}
    events: list[tuple[str, float]] = []
    for buy, sell, amount, _profit, _hold in rows:
        events.append((str(buy), float(amount)))
        events.append((str(sell), -float(amount)))
    events.sort()
    current = peak = 0.0
    count = peak_count = 0
    for _stamp, amount in events:
        current += amount
        count += 1 if amount > 0 else -1
        peak = max(peak, current)
        peak_count = max(peak_count, count)
    return {"peak_capital": peak, "max_hold_count": peak_count,
            "avg_hold_sec": sum(float(r[4]) for r in rows) / len(rows)}


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-name", default="design_v4")
    parser.add_argument("--source", default="ai", choices=("human", "ai", "optimizer"))
    parser.add_argument("--tag", default="", help="리포트 접미(_ext 등)")
    args = parser.parse_args()

    report = _read(args.out_name, f"_p5_engine_report{args.tag}.json")
    if report is None:
        raise SystemExit("엔진 A/B 리포트가 없다 — run_engine_measure 를 먼저 돌려라.")
    ladder = _read(args.out_name, f"_engine_ladder{args.tag}.json") or {}
    judged = {str(r.get("challenger")): r for r in ladder.get("results") or []}

    db_path = os.path.abspath(_BT_DB)
    tables = _tables(db_path)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    design = report.get("design") or [None, None]
    baseline_id = None

    written = 0
    for outcome in report.get("outcomes") or []:
        rule = str(outcome.get("rule"))
        engine = outcome.get("engine") or {}
        buy = outcome.get("buy") or report.get("champion_buy")
        table = resolve_table(tables, str(buy), str(outcome.get("job_id") or ""))
        stats = _table_stats(db_path, table) if table else {}

        is_baseline = outcome.get("arm") == "baseline"
        verdict_row = judged.get(rule) or {}
        paired = verdict_row.get("paired") or {}
        regime = verdict_row.get("regime") or {}

        candidate_id = f"{report.get('champion_buy')}::{outcome.get('sell') or rule}"
        if is_baseline:
            baseline_id = candidate_id

        record = CandidateRecord(
            candidate_id=candidate_id,
            family="exit",                       # 이번 라운드는 매도만 바꿨다
            source="human" if is_baseline else args.source,
            lane=str(report.get("lane") or "tick"),
            verdict="BASELINE" if is_baseline else str(verdict_row.get("verdict") or "PROMISING"),
            recorded_at=stamp,
            buy_name=str(buy) if buy else None,
            sell_name=str(outcome.get("sell") or ""),
            period_start=design[0], period_end=design[1],
            job_id=str(outcome.get("job_id") or ""),
            result_table=table,
            trades=engine.get("trade_count"),
            win_rate=engine.get("win_rate"),
            avg_profit_pct=engine.get("avg_profit_pct"),
            total_profit_krw=engine.get("total_profit_krw"),
            # 엔진이 낸 필요자금이 정본이다. 내 이벤트 재구성은 동시 타임스탬프
            #   처리가 엔진과 달라 과대 추정된다(실측 300만 vs 엔진 100만).
            seed_capital=engine.get("seed_capital", stats.get("peak_capital")),
            total_profit_pct=engine.get("total_profit_pct"),
            cagr=engine.get("cagr"),
            mdd_pct=engine.get("mdd_pct"),
            tpi=engine.get("tpi"),
            avg_hold_sec=engine.get("avg_hold_time", stats.get("avg_hold_sec")),
            max_hold_count=engine.get("max_hold_count", stats.get("max_hold_count")),
            baseline_id=None if is_baseline else baseline_id,
            paired_pairs=paired.get("pairs"),
            paired_mean_diff_pct=paired.get("mean_diff_pct"),
            paired_ci_low=(paired.get("ci95") or [None, None])[0],
            paired_ci_high=(paired.get("ci95") or [None, None])[1],
            paired_significant=paired.get("significant"),
            paired_required=paired.get("required_pairs"),
            regime_positive=regime.get("challenger_positive"),
            regime_baseline=regime.get("baseline_positive"),
            map_expectancy_pct=(outcome.get("predicted") or {}).get("expectancy_pct"),
            transfer_ratio=outcome.get("transfer_ratio"),
            verdict_reason=verdict_row.get("verdict_meaning")
                           or ("합격선(챔피언) 그 자체" if is_baseline else None),
            notes=f"엔진 A/B · 진입 고정 · out_name={args.out_name}",
        )
        append(record)
        written += 1
        print(f"기록: {rule:<28} {record.verdict:<10} 건당={record.avg_profit_pct} "
              f"필요자금={record.seed_capital:,.0f}원" if record.seed_capital
              else f"기록: {rule:<28} {record.verdict}", flush=True)

    state = summary()
    print(f"\n=== 원장 요약 ===")
    print(f" 후보 {state['candidates']}종 · 누적 기록 {state['records']}행")
    print(f" 판정 분포: {state['verdicts']}")
    print(f" 승격(PASS) {state['promoted']}종")
    best = state.get("best_by_avg_profit")
    if best:
        print(f" 최고 건당: {best['sell_name']} {best['avg_profit_pct']}% "
              f"({best['verdict']})")
    print(f"\n적재 {written}행 · DB: _database/strategy_ledger.db", flush=True)


if __name__ == "__main__":
    main()
