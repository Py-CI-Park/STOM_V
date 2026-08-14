"""S7-b — 진입 완화 후보를 엔진으로 확인한다.

## 규율

지도(`run_entry_ablation`)에서 "완화 후보"로 나온 절을 **챔피언 매도와 함께**
엔진에 올린다. 매도를 B3 로 바꾸지 않는 이유는 헌법 7항이다:
**진입과 매도를 동시에 바꾸지 않는다.** 둘을 같이 바꾸면 어느 쪽이 효과인지
가릴 수 없다.

따라서 이 실험의 기준선은 챔피언 페어(진입+매도 원본)이고, 바뀌는 것은
**매수식의 절 하나**뿐이다.

## 게이트

| 판정 | 조건 |
|---|---|
| **완화 채택 후보** | 거래 증가 + 건당 ≥ 기준선 + 총수익률 ≥ 기준선 |
| 값 지불 | 거래는 늘었으나 위를 하나라도 못 넘음 |

빈도를 위해 기대값을 팔지 않는다.

사용:
    python -m ai_strategy_loop.labeling.run_entry_relax \\
        --out-name design_v4 --tag _ext --clauses 905_시가대비,905_거래대금급증
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sqlite3
import sys
import time

from ai_strategy_loop.labeling import champion_clauses as cc
from ai_strategy_loop.labeling.lanes import LANES
from ai_strategy_loop.labeling.run_capital_turnover import _load_baseline
from ai_strategy_loop.labeling.run_engine_measure import (
    CHAMPION_BUY, CHAMPION_SELL, _METRIC_KEYS, _run_arm)
from ai_strategy_loop.labeling.run_p5 import Client

_LABEL_ROOT = os.path.join(os.path.dirname(__file__), "..", "state", "labels")
_STRATEGY_DB = os.path.join(os.path.dirname(__file__), "..", "..",
                            "_database", "strategy.db")

#: 이 러너가 쓸 수 있는 유일한 이름공간.
OWNED_PREFIX = "W7_B_"


def _assert_owned(name: str) -> None:
    if not name.startswith(OWNED_PREFIX):
        raise ValueError(f"쓰기 금지 이름: {name} (허용 접두 {OWNED_PREFIX!r})")


def champion_buy_code(db_path: str | None = None) -> str:
    """챔피언 매수식 원문을 **읽기 전용**으로 가져온다."""
    path = os.path.abspath(db_path or _STRATEGY_DB)
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        row = con.execute('SELECT 전략코드 FROM stockbuy WHERE "index"=?',
                          (CHAMPION_BUY,)).fetchone()
    finally:
        con.close()
    if not row:
        raise SystemExit(f"챔피언 매수식이 없다: {CHAMPION_BUY}")
    return str(row[0])


def sync_ledger(report: dict, *, source: str = "ai") -> int:
    """진입 후보를 원장에 적재한다.

    ## 왜 별도 경로인가 — 짝지은 검정이 성립하지 않는다

    짝지은 비교의 전제는 두 팔이 **같은 진입을 공유**한다는 것이다. 진입 절을
    빼면 그 전제가 깨진다: 공유되는 거래는 매도가 같으니 차이가 정확히 0 이고,
    새로 늘어난 거래는 짝이 없다. 그래서 `run_ledger_sync`(짝지은 필드 포함)를
    쓰지 않고 **집계 지표만** 적는다.

    ## 진입 후보는 PASS 를 받을 수 없다

    원장에서 `PASS` 는 "챔피언 이상 **+ 통계적으로 확정**"이다. 진입 후보는 짝지은
    검정을 쓸 수 없으므로 통계 확정 수단이 없다 — 집계 지표가 아무리 좋아도
    `PROMISING`(방향은 맞으나 확정 못 함)이 상한이다.

    이 구분을 흐리면 원장의 `승격 0종`이라는 핵심 정보가 무의미해진다.
    확정은 홀드아웃 또는 독립 구간에서만 온다.

    폐기된 후보도 남긴다 — "이건 이미 해 봤다"를 아는 것이 원장의 값이다.
    """
    from datetime import datetime, timezone

    from ai_strategy_loop.controller.strategy_ledger import CandidateRecord, append

    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    design = report.get("design") or [None, None]
    written = 0
    for outcome in report.get("outcomes") or []:
        engine = outcome.get("engine") or {}
        gate = outcome.get("gate") or {}
        append(CandidateRecord(
            candidate_id=f"{outcome.get('buy')}::{outcome.get('sell')}",
            family="entry", source=source, lane=str(report.get("lane") or "tick"),
            verdict="PROMISING" if gate.get("pass") else "REJECT",
            recorded_at=stamp,
            buy_name=outcome.get("buy"), sell_name=outcome.get("buy"),
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
            baseline_id=f"{report.get('champion_buy')}::{report.get('baseline_sell')}",
            verdict_reason=(
                f"진입 절 제거 · 거래 {gate.get('trade_gain'):+d} · "
                f"건당 {'통과' if gate.get('per_trade_pass') else '미달'} · "
                f"자본 {'통과' if gate.get('capital_pass') else '미달'}"),
            notes=("짝지은 검정 없음 — 진입이 다르면 짝이 성립하지 않는다. "
                   "따라서 통계 확정 수단이 없어 PROMISING 이 상한이다."),
        ))
        written += 1
    return written


def resolve_baseline(report: dict, sell_name: str) -> tuple[dict, dict]:
    """**그 매도식을 쓰는** 기준선을 고른다.

    ## 왜 필요한가 (W6 실패의 교정)

    W6 진입 완화는 지도에서 `trailing(5/2)` 청산으로 재고, 엔진 확인은 챔피언
    청산으로 했다. 그래서 지도 예측과 엔진 실측의 **부호가 뒤집혔다**
    (지도 +0.063%p → 엔진 −0.27%p). 거래 수 예측은 정확했으니 틀린 것은
    비교 대상이었다.

    진입 절 하나만 바꾸는 실험이 되려면 기준선의 **매도식이 후보와 같아야 한다**
    (헌법 10항 — 비교하려면 나머지 축이 같아야 한다).

    반환: (지표, 팔 전체). 팔에는 job_id 가 들어 있다.
    """
    if sell_name == CHAMPION_SELL:
        arm = next((o for o in report.get("outcomes") or []
                    if o.get("arm") == "baseline"), None)
        metrics = report.get("baseline_metrics") or {}
    else:
        arm = next((o for o in report.get("outcomes") or []
                    if o.get("sell") == sell_name), None)
        metrics = (arm or {}).get("engine") or {}
    if arm is None or not metrics.get("trade_count"):
        available = sorted({str(o.get("sell")) for o in report.get("outcomes") or []})
        raise SystemExit(
            f"매도식 {sell_name!r} 을 쓰는 기준선 실측이 없다.\n"
            f"  이 리포트에 있는 매도식: {available}\n"
            f"  같은 구간에서 그 매도식을 먼저 재라 — 기준선이 다르면 비교가 성립하지 않는다.")
    return metrics, arm


def _gate(baseline: dict, engine: dict, *,
          capital_limit_krw: float | None = None) -> dict:
    """완화는 **공짜여야** 채택 후보다 — 셋 다 넘어야 한다.

    자본 축은 `engine_ladder.capital_gate` 와 **같은 두 정책**을 쓴다:

    | 정책 | 자본 게이트 | 수익 게이트 |
    |---|---|---|
    | `ratio`(기본) | 총수익률 ≥ 기준선 | 건당 ≥ 기준선 |
    | `limit` | 필요자금 ≤ 한도 | 건당 ≥ 기준선 **AND 총수익금 ≥ 기준선** |

    자본이 구속하지 않으면 볼 것은 **총수익금**이다. 총수익률로 재면 자본을
    더 쓰고 더 버는 후보가 부당하게 떨어진다(심판과 같은 결함을 진입 쪽에
    남겨 두지 않는다).
    """
    def ge(key: str) -> bool:
        mine, base = engine.get(key), baseline.get(key)
        return mine is not None and base is not None and float(mine) >= float(base)

    more = (engine.get("trade_count") or 0) > (baseline.get("trade_count") or 0)
    per_trade = ge("avg_profit_pct")
    if capital_limit_krw is None:
        policy, capital, money = "ratio", ge("total_profit_pct"), True
    else:
        seed = engine.get("seed_capital")
        policy = "limit"
        capital = seed is not None and float(seed) <= float(capital_limit_krw)
        money = ge("total_profit_krw")
    return {
        "capital_policy": policy,
        "capital_limit_krw": capital_limit_krw,
        "more_trades": bool(more),
        "per_trade_pass": bool(per_trade),
        "capital_pass": bool(capital),
        "money_pass": bool(money),
        "pass": bool(more and per_trade and capital and money),
        "trade_gain": (engine.get("trade_count") or 0) - (baseline.get("trade_count") or 0),
        "note": ("빈도를 위해 기대값을 팔지 않는다 — 건당이 유지돼야 한다. "
                 + ("자본은 실행 가능성만 본다(총수익금으로 순위)."
                    if policy == "limit" else "자본은 총수익률로 잰다.")),
    }


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-name", default="design_v4")
    parser.add_argument("--lane", choices=sorted(LANES), default="tick")
    parser.add_argument("--tag", default="_ext")
    parser.add_argument("--clauses", default="905_시가대비",
                        help="쉼표 구분. DSL 앵커가 등록된 절만 가능")
    # 매도식을 고를 수 있어야 지도와 같은 축에서 비교된다(헌법 10항).
    #   기준선도 이 매도식을 쓰는 팔로 자동으로 바뀐다.
    parser.add_argument("--sell", default=CHAMPION_SELL,
                        help=f"고정할 매도식. 기본 {CHAMPION_SELL} "
                             f"(지도와 맞추려면 W4_S_TRAIL_5_2)")
    parser.add_argument("--out-tag", default=None,
                        help="산출 파일 접미. 생략하면 --tag 와 같다")
    parser.add_argument("--capital-limit", type=float, default=None,
                        help="운용 가능 자본(원). 주면 자본 축이 실행 가능성으로 바뀐다")
    parser.add_argument("--engines", type=int, default=16)
    parser.add_argument("--timeout", type=int, default=9000)
    parser.add_argument("--sync-only", action="store_true",
                        help="엔진 실행 없이 기존 결과를 원장에 적재만 한다")
    args = parser.parse_args()

    lane = LANES[args.lane]
    keys = [k.strip() for k in args.clauses.split(",") if k.strip()]
    unknown = [k for k in keys if k not in cc.DSL_ANCHOR]
    if unknown:
        raise SystemExit(f"DSL 앵커가 없는 절: {unknown} (등록됨: {sorted(cc.DSL_ANCHOR)})")

    out_tag = args.out_tag if args.out_tag is not None else args.tag
    out_path = os.path.join(_LABEL_ROOT, args.out_name, f"_entry_relax{out_tag}.json")

    if args.sync_only:
        if not os.path.exists(out_path):
            raise SystemExit(f"적재할 결과가 없다: {out_path}")
        with open(out_path, "r", encoding="utf-8") as handle:
            written = sync_ledger(json.load(handle))
        print(f"원장 적재 {written}행 (진입 계열 · 짝지은 검정 없음)")
        return

    report_path = os.path.join(_LABEL_ROOT, args.out_name,
                               f"_p5_engine_report{args.tag}.json")
    if not os.path.exists(report_path):
        raise SystemExit(f"기준선 실측이 없다: {report_path}")
    with open(report_path, "r", encoding="utf-8") as handle:
        report = json.load(handle)
    span = list(report.get("design") or [])
    baseline, baseline_arm = resolve_baseline(report, args.sell)

    champion = champion_buy_code()
    print(f"[기준선] {CHAMPION_BUY} + {args.sell} 구간 {span} "
          f"거래={baseline.get('trade_count')} 건당={baseline.get('avg_profit_pct')}% "
          f"총수익률={baseline.get('total_profit_pct')}%", flush=True)

    client = Client()
    outcomes: list[dict] = []
    t0 = time.time()

    def _save() -> None:
        with open(out_path, "w", encoding="utf-8") as handle:
            json.dump({
                "lane": lane.name, "design": span,
                "champion_buy": CHAMPION_BUY, "baseline_sell": args.sell,
                "baseline_metrics": baseline, "outcomes": outcomes,
                "complete": len(outcomes) == len(keys),
                "note": (f"진입 절 하나만 뺀 A/B. 매도는 {args.sell} 로 고정 "
                         "— 진입과 매도를 동시에 바꾸지 않는다(헌법 7항). "
                         "기준선도 같은 매도식을 쓴다(헌법 10항)."),
            }, handle, ensure_ascii=False, indent=1, default=float)

    for index, key in enumerate(keys, start=1):
        buy_name = f"{OWNED_PREFIX}RELAX_{key}"
        _assert_owned(buy_name)
        code = cc.drop_clause_from_dsl(champion, key)
        saved = client.call("POST", "/bt/strategy",
                            {"kind": "buy", "name": buy_name, "code": code,
                             "overwrite": True})
        print(f"[R{index}] 매수 등록 {buy_name} ({cc.clause_by_key(key).label}) "
              f"{saved.get('status')}", flush=True)

        run = _run_arm(client, buy=buy_name, sell=args.sell, lane=lane,
                       engines=args.engines, timeout=args.timeout,
                       period=(span[0], span[1]) if len(span) == 2 else None)
        metrics = run["metrics"]
        gate = _gate(baseline, metrics, capital_limit_krw=args.capital_limit)
        outcomes.append({
            "name": buy_name, "rule": f"champion − {key}", "clause": key,
            "arm": f"relax_{index}", "buy": buy_name, "sell": args.sell,
            "job_id": run.get("job_id"), "status": run["status"],
            "predicted": None,
            "engine": {k: metrics.get(k) for k in _METRIC_KEYS},
            "gate": gate, "transfer_ratio": None,
        })
        print(f"    → {run['status']} 거래={metrics.get('trade_count')} "
              f"({gate['trade_gain']:+d}) 건당={metrics.get('avg_profit_pct')}% "
              f"총수익률={metrics.get('total_profit_pct')}% "
              f"{'PASS' if gate['pass'] else 'FAIL'}", flush=True)
        _save()

    print(f"\n=== 진입 완화 요약 (구간 {span} · 매도 {args.sell}) "
          f"· {time.time() - t0:.0f}초 ===")
    print(f" {'후보':<30}{'거래':>6}{'건당':>9}{'총수익률':>10}  판정")
    print(f" {'기준선 ' + args.sell:<30}{baseline.get('trade_count'):>6}"
          f"{baseline.get('avg_profit_pct'):>8}%{baseline.get('total_profit_pct'):>9}%  —")
    for row in outcomes:
        e, g = row["engine"], row["gate"]
        print(f" {row['rule']:<30}{e.get('trade_count'):>6}"
              f"{e.get('avg_profit_pct'):>8}%{e.get('total_profit_pct'):>9}%  "
              f"{'PASS' if g['pass'] else 'FAIL'}")
    print(f"\n기록: {out_path}", flush=True)


if __name__ == "__main__":
    main()
