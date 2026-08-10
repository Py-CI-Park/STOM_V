"""HOF1 — 시간창 확장(09:05→09:20) 후보를 엔진 A/B 로 확인한다.

## 왜 이 실험인가

챔피언 `Tick_B_902_905` 는 사람 전략군에서 가장 좁은 창(09:00~09:05)을 쓴다.
지도 실측: 09:20 까지 열면 진입 기회 3.6배(739→2,682 진입 단위). 그러나
지도는 진입축 수익을 예측하지 못한다(6전 1승) — 그래서 엔진으로 잰다.

## 규율

- 매수식의 시간창 **한 줄만** 바꾼다(`widen_window`). 매도는 챔피언 매도
  그대로 — 진입과 매도를 동시에 바꾸지 않는다(헌법 7항).
- 기준선(챔피언 페어)도 **같은 세션에서 함께** 잰다 — 세션 간 드리프트
  (±0.15M)를 A/B 안에서 상쇄한다.
- 진입이 다르므로 짝지은 검정 불가 → 판정 상한 `PROMISING`(원장 규칙).
- 게이트는 사전 등록(`2026-08-10_HOF1_사전등록.md`, 실행 전 커밋) 그대로:
  거래 증가 AND 총수익금 >= 기준선 AND 후보 총수익금 > 0 AND
  필요자금 <= 한도. **건당은 참고**(창이 넓으면 떨어질 수 있다).

사용:
    python -m ai_strategy_loop.labeling.run_window_widen \\
        --out-name design_v5 --start 20220323 --end 20250822 \\
        --capital-limit 20000000 --timeout 9000
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time

from ai_strategy_loop.labeling.lanes import LANES
from ai_strategy_loop.labeling.run_engine_measure import (
    CHAMPION_BUY, CHAMPION_SELL, _METRIC_KEYS, _run_arm)
from ai_strategy_loop.labeling.run_entry_relax import champion_buy_code
from ai_strategy_loop.labeling.run_p5 import Client

_LABEL_ROOT = os.path.join(os.path.dirname(__file__), "..", "state", "labels")

#: 이 러너가 쓸 수 있는 유일한 이름공간.
OWNED_PREFIX = "HOF1_B_"

#: 챔피언 매수식에서 바꿀 유일한 줄. 원문에 정확히 1회 있어야 한다.
WINDOW_LINE = "elif 90200 <= 시분초 < 90500:"

#: 확장 표식 — 이미 확장된 코드를 다시 확장하는 것을 막는다.
_MARKER = "# HOF1 시간창 확장"

#: 사용자 확정(2026-08-10): 09:20 이 최대. 09:30 시도 금지.
MAX_END = 92000


def widen_window(code: str, end_hhmmss: int = MAX_END) -> str:
    """챔피언 매수식의 시간창 상한 한 줄을 바꾼 새 코드를 돌려준다.

    원본은 절대 수정하지 않는다(새 문자열 반환). 다음이면 거부한다:
    - 대상 줄이 정확히 1회가 아니다 (다른 전략이거나 구조가 바뀌었다)
    - 이미 확장된 코드다 (표식 존재)
    - 상한이 (90500, 92000] 밖이다 (사용자 확정: 09:20 이 최대)
    """
    end = int(end_hhmmss)
    if not 90500 < end <= MAX_END:
        raise ValueError(
            f"시간창 상한 {end} 은 허용 범위 (90500, {MAX_END}] 밖이다 — "
            "사용자 확정(2026-08-10): 09:20 이 최대")
    if _MARKER in code:
        raise ValueError("이미 시간창이 확장된 코드다 — 원본 챔피언 코드를 넣어라")
    count = code.count(WINDOW_LINE)
    if count != 1:
        raise ValueError(
            f"대상 줄이 {count}회 발견됐다(정확히 1회여야 한다): {WINDOW_LINE!r}")
    replaced = f"elif 90200 <= 시분초 < {end}:  {_MARKER} (원본 90500)"
    return code.replace(WINDOW_LINE, replaced)


def hof1_gate(baseline: dict, engine: dict, *,
              capital_limit_krw: float) -> dict:
    """사전 등록 합격선 그대로. A~D 필수 · E(건당)는 참고만.

    | # | 조건 |
    |---|---|
    | A | 거래 수 증가 |
    | B | 총수익금 >= 기준선(같은 세션 실측) |
    | C | 후보 총수익금 > 0 (헌법 12항 절대 조건) |
    | D | 필요자금 <= 한도 (자본 정책 `limit`) |
    """
    def num(src: dict, key: str) -> float | None:
        value = src.get(key)
        return None if value is None else float(value)

    trades = engine.get("trade_count") or 0
    base_trades = baseline.get("trade_count") or 0
    money, base_money = num(engine, "total_profit_krw"), num(baseline, "total_profit_krw")
    seed = num(engine, "seed_capital")
    per, base_per = num(engine, "avg_profit_pct"), num(baseline, "avg_profit_pct")

    more = trades > base_trades
    money_pass = money is not None and base_money is not None and money >= base_money
    positive = money is not None and money > 0
    capital = seed is not None and seed <= float(capital_limit_krw)
    per_trade_ref = (per is not None and base_per is not None and per >= base_per)
    return {
        "capital_policy": "limit",
        "capital_limit_krw": float(capital_limit_krw),
        "more_trades": bool(more),
        "money_pass": bool(money_pass),
        "positive_pass": bool(positive),
        "capital_pass": bool(capital),
        "per_trade_ref": bool(per_trade_ref),
        "pass": bool(more and money_pass and positive and capital),
        "trade_gain": trades - base_trades,
        "note": ("A 거래증가·B 총수익금·C 후보흑자·D 자금한도 전부 필수. "
                 "건당(E)은 참고 — 창이 넓으면 떨어질 수 있다(사전 등록)."),
    }


def sync_ledger(report: dict, *, source: str = "ai") -> int:
    """진입 계열이므로 짝지은 필드 없이 집계 지표만 적는다.

    짝지은 비교의 전제는 두 팔이 같은 진입을 공유한다는 것이다. 시간창을
    넓히면 그 전제가 깨진다 — 공유 거래는 차이가 0 이고, 새 거래는 짝이
    없다. 그래서 통계 확정 수단이 없고 **`PROMISING` 이 상한**이다.
    """
    from datetime import datetime, timezone

    from ai_strategy_loop.controller.strategy_ledger import CandidateRecord, append

    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    design = report.get("design") or [None, None]
    baseline = report.get("baseline_metrics") or {}
    written = 0
    for outcome in report.get("outcomes") or []:
        if outcome.get("arm") == "baseline":
            continue
        engine = outcome.get("engine") or {}
        gate = outcome.get("gate") or {}
        append(CandidateRecord(
            candidate_id=f"{outcome.get('buy')}::{outcome.get('sell')}",
            family="entry", source=source, lane=str(report.get("lane") or "tick"),
            verdict="PROMISING" if gate.get("pass") else "REJECT",
            recorded_at=stamp,
            buy_name=outcome.get("buy"), sell_name=outcome.get("sell"),
            period_start=design[0], period_end=design[1],
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
            verdict_reason=(
                f"HOF1 시간창 확장(90500→{report.get('end_hhmmss')}) · "
                f"거래 {gate.get('trade_gain'):+d} · "
                f"총수익금 {'통과' if gate.get('money_pass') else '미달'}"
                f"({engine.get('total_profit_krw')} vs {baseline.get('total_profit_krw')}) · "
                f"흑자 {'통과' if gate.get('positive_pass') else '미달'} · "
                f"자금 {'통과' if gate.get('capital_pass') else '미달'}"),
            notes=("짝지은 검정 없음 — 진입이 다르면 짝이 성립하지 않는다. "
                   "PROMISING 이 상한. 사전 등록: 2026-08-10_HOF1_사전등록.md. "
                   f"자본 정책 limit {gate.get('capital_limit_krw')}원."),
        ))
        written += 1
    return written


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-name", default="design_v5")
    parser.add_argument("--lane", choices=sorted(LANES), default="tick")
    parser.add_argument("--end-hhmmss", type=int, default=MAX_END)
    parser.add_argument("--start", type=int, default=20220323)
    parser.add_argument("--end", type=int, default=20250822)
    parser.add_argument("--capital-limit", type=float, required=True,
                        help="운용 가능 자본(원). 사전 등록 값 20000000")
    parser.add_argument("--engines", type=int, default=16)
    parser.add_argument("--timeout", type=int, default=9000)
    parser.add_argument("--sync-only", action="store_true",
                        help="엔진 실행 없이 기존 결과를 원장에 적재만 한다")
    args = parser.parse_args()

    lane = LANES[args.lane]
    out_path = os.path.join(_LABEL_ROOT, args.out_name, "_window_widen_hof1.json")

    if args.sync_only:
        if not os.path.exists(out_path):
            raise SystemExit(f"적재할 결과가 없다: {out_path}")
        with open(out_path, "r", encoding="utf-8") as handle:
            written = sync_ledger(json.load(handle))
        print(f"원장 적재 {written}행 (진입 계열 · PROMISING 상한)")
        return

    buy_name = f"{OWNED_PREFIX}WINDOW_{args.end_hhmmss // 100}"
    if not buy_name.startswith(OWNED_PREFIX):
        raise SystemExit(f"쓰기 금지 이름: {buy_name}")
    code = widen_window(champion_buy_code(), args.end_hhmmss)
    span = (args.start, args.end)

    client = Client()
    saved = client.call("POST", "/bt/strategy",
                        {"kind": "buy", "name": buy_name, "code": code,
                         "overwrite": True})
    print(f"[등록] {buy_name} (90500→{args.end_hhmmss}) {saved.get('status')}",
          flush=True)

    outcomes: list[dict] = []
    report = {
        "lane": lane.name, "design": list(span),
        "end_hhmmss": args.end_hhmmss,
        "champion_buy": CHAMPION_BUY, "baseline_sell": CHAMPION_SELL,
        "baseline_metrics": {}, "outcomes": outcomes, "complete": False,
        "note": ("시간창 한 줄만 바꾼 A/B. 매도는 챔피언 고정(헌법 7항). "
                 "두 팔을 같은 세션에서 재어 드리프트를 상쇄. "
                 "사전 등록: 2026-08-10_HOF1_사전등록.md"),
    }

    def _save() -> None:
        with open(out_path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=1, default=float)

    t0 = time.time()
    print(f"[A] 기준선 {CHAMPION_BUY} + {CHAMPION_SELL} 구간 {span}", flush=True)
    base_run = _run_arm(client, buy=CHAMPION_BUY, sell=CHAMPION_SELL, lane=lane,
                        engines=args.engines, timeout=args.timeout, period=span)
    baseline = base_run["metrics"]
    report["baseline_metrics"] = {k: baseline.get(k) for k in _METRIC_KEYS}
    outcomes.append({
        "arm": "baseline", "buy": CHAMPION_BUY, "sell": CHAMPION_SELL,
        "job_id": base_run.get("job_id"), "status": base_run["status"],
        "engine": report["baseline_metrics"], "gate": None,
    })
    print(f"    → {base_run['status']} 거래={baseline.get('trade_count')} "
          f"건당={baseline.get('avg_profit_pct')}% "
          f"총수익금={baseline.get('total_profit_krw')}", flush=True)
    _save()

    print(f"[B] 후보 {buy_name} + {CHAMPION_SELL} 구간 {span}", flush=True)
    cand_run = _run_arm(client, buy=buy_name, sell=CHAMPION_SELL, lane=lane,
                        engines=args.engines, timeout=args.timeout, period=span)
    metrics = cand_run["metrics"]
    gate = hof1_gate(report["baseline_metrics"], metrics,
                     capital_limit_krw=args.capital_limit)
    outcomes.append({
        "arm": "candidate", "buy": buy_name, "sell": CHAMPION_SELL,
        "job_id": cand_run.get("job_id"), "status": cand_run["status"],
        "engine": {k: metrics.get(k) for k in _METRIC_KEYS}, "gate": gate,
    })
    report["complete"] = True
    _save()

    print(f"    → {cand_run['status']} 거래={metrics.get('trade_count')} "
          f"({gate['trade_gain']:+d}) 건당={metrics.get('avg_profit_pct')}% "
          f"총수익금={metrics.get('total_profit_krw')} "
          f"{'PASS(게이트)' if gate['pass'] else 'FAIL'}", flush=True)

    written = sync_ledger(report)
    print(f"\n=== HOF1 요약 (구간 {span} · {time.time() - t0:.0f}초 · "
          f"원장 {written}행) ===")
    print(f" {'팔':<26}{'거래':>6}{'건당':>9}{'총수익금':>12}{'필요자금':>12}")
    for row in outcomes:
        e = row["engine"]
        print(f" {row['buy']:<26}{e.get('trade_count'):>6}"
              f"{e.get('avg_profit_pct'):>8}%{e.get('total_profit_krw'):>12}"
              f"{e.get('seed_capital'):>12}")
    print(f"\n기록: {out_path}", flush=True)


if __name__ == "__main__":
    main()
