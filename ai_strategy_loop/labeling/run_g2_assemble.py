"""G2~G4 — G1 시드로 **새 골격**을 조립하고 엔진으로 판정한다.

사전 등록: `docs/research/quant_scoring_pipeline/2026-08-13_G2_G4_사전등록.md`
(커밋 `57782f64` — 실행 전)

## 챔피언 절을 하나도 쓰지 않는다

지금까지의 모든 라운드는 챔피언의 변형이었다(닫힌 방향 12건). 이 골격은
G1 채굴이 지목한 **세그먼트(초소형 × 이른 시각)** 에서 새로 만든다.
공통 안전절(관심종목·가격·VI·라운드피겨)은 전략이 아니라 **체결 가능성** 확보다.

## 세 변형을 전부 올린다

조립 전 실측에서 **승자 IQR 밴드가 판별력을 못 보였다**(사전 등록 §1.1).
그래서 밴드를 씌우는 정도만 다른 세 변형을 모두 엔진에 올려 판정한다.

사용:
    python -m ai_strategy_loop.labeling.run_g2_assemble --out-name design_v5 --stage train
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from typing import Any, Final, Sequence

from ai_strategy_loop.labeling.lanes import LANES
from ai_strategy_loop.labeling.run_engine_measure import (
    CHAMPION_BUY, CHAMPION_SELL, _METRIC_KEYS, _run_arm)
from ai_strategy_loop.labeling.run_p5 import Client
from ai_strategy_loop.labeling.run_trade_autopsy import (
    _LABEL_ROOT, calendar_days, split_days)

#: 이 러너가 쓸 수 있는 유일한 이름공간.
OWNED_PREFIX: Final = "G2_B_"

#: 사전 등록 §4 — 격자 3셀 고정. 추가 금지.
VARIANTS: Final = ("SEG_ONLY", "LOWER", "IQR")

#: 초소형 상한(`cli/research_segments.DEFAULT_MARKET_CAP_BUCKETS` 의 '초소형' = 0~1000).
MICRO_CAP_MAX: Final = 1000

#: 시간밴드 ↔ G1 세그먼트 이름.
BANDS: Final = ((90000, 90500, "0900-0905"),
                (90500, 91000, "0905-0910"),
                (91000, 91500, "0910-0915"))

#: 밴드 조건에 쓸 피처(시분초=시간분기·시가총액=세그먼트로 이미 사용 — 중복 배제).
BAND_FEATURES: Final = ("등락율", "체결강도", "당일거래대금", "회전율",
                        "초당거래대금", "고저평균대비등락율")

#: 사전 등록 §6 게이트.
GATE_MIN_TRADES: Final = 30


def _fmt(value: float) -> str:
    return f"{float(value):g}"


def render_band_clauses(features: dict, variant: str, *, indent: str,
                        quantile: str = "q25") -> list[str]:
    """한 시간밴드의 피처 절을 만든다. `SEG_ONLY` 는 빈 목록.

    `quantile` 은 하한으로 쓸 분위(G5 선택도 사다리가 q50·q75 로 올린다).
    기본 `q25` 는 G2 사전 등록 값이라 기존 산출과 바이트 동일하다.
    """
    if variant == "SEG_ONLY":
        return []
    lines: list[str] = []
    for name in BAND_FEATURES:
        stats = features.get(name)
        if not stats or quantile not in stats:
            continue
        lo, hi = float(stats[quantile]), float(stats.get("q75", 0.0))
        if variant == "LOWER":
            lines.append(f"{indent}if not ({name} >= {_fmt(lo)}):")
        else:                                    # IQR
            if hi <= lo:
                continue
            lines.append(f"{indent}if not ({_fmt(lo)} <= {name} < {_fmt(hi)}):")
        lines.append(f"{indent}    매수 = False")
    return lines


def render_strategy(seeds: Sequence[dict], variant: str, *,
                    quantile: str = "q25",
                    bands: Sequence[tuple] = BANDS) -> str:
    """G1 시드 → 새 골격 매수식. 챔피언 절은 쓰지 않는다.

    `quantile`·`bands` 는 G5 선택도 사다리용 파라미터다. 기본값은 G2 사전 등록
    값이라 기존 호출부의 산출이 바뀌지 않는다.
    """
    if variant not in VARIANTS:
        raise ValueError(f"격자 밖 변형: {variant} (허용 {VARIANTS})")
    if not bands:
        raise ValueError("시간밴드가 비었다 — 매수 시점이 없는 조건식이 된다")
    by_segment = {str(s.get("time_segment")): (s.get("features") or {}) for s in seeds}

    out: list[str] = [
        f"# G2 새 골격 — 변형 {variant} · G1 채굴 시드(초소형×이른 시각)",
        "# 사전 등록: 2026-08-13_G2_G4_사전등록.md (57782f64)",
        "",
        "매수 = True",
        "",
        "# --- 공통 안전절(체결 가능성 · 전략 아님) ---",
        "if not (관심종목 == 1):",
        "    매수 = False",
        "elif not (현재가 > 1000):",
        "    매수 = False",
        "elif not (현재가 < VI아래5호가):",
        "    매수 = False",
        "elif 라운드피겨위5호가이내:",
        "    매수 = False",
        "",
        "# --- 세그먼트: 초소형 ---",
        f"elif not (시가총액 < {MICRO_CAP_MAX}):",
        "    매수 = False",
        "",
    ]
    for lo, hi, segment in bands:
        out.append(f"# --- 밴드 {segment} ---")
        out.append(f"elif {lo} <= 시분초 < {hi}:")
        clauses = render_band_clauses(by_segment.get(segment, {}), variant,
                                      indent="    ", quantile=quantile)
        out.extend(clauses if clauses else ["    pass"])
        out.append("")
    out += ["# --- 밴드 밖 ---", "else:", "    매수 = False", "",
            "if 매수:", "    self.Buy()", ""]
    return "\n".join(out)


def gate(metrics: dict, *, champion_krw: float, capital_limit_krw: float) -> dict:
    """사전 등록 §6 — A 흑자 · B 챔피언 이상 · C 표본 · D 자금."""
    def num(key: str) -> float | None:
        value = metrics.get(key)
        return None if value is None else float(value)

    money, seed = num("total_profit_krw"), num("seed_capital")
    trades = metrics.get("trade_count") or 0
    positive = money is not None and money > 0
    beats = money is not None and money >= float(champion_krw)
    enough = trades >= GATE_MIN_TRADES
    capital = seed is not None and seed <= float(capital_limit_krw)
    return {
        "positive_pass": bool(positive), "champion_pass": bool(beats),
        "sample_pass": bool(enough), "capital_pass": bool(capital),
        "champion_krw": float(champion_krw),
        "pass": bool(positive and beats and enough and capital),
    }


def sync_ledger(report: dict, *, stage: str) -> int:
    """진입 계열 — `PROMISING` 이 상한. 새 골격임을 notes 에 남긴다."""
    from datetime import datetime, timezone

    from ai_strategy_loop.controller.strategy_ledger import CandidateRecord, append

    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    span = report.get("span") or [None, None]
    written = 0
    for outcome in report.get("outcomes") or []:
        if not outcome.get("gate"):
            continue
        engine, g = outcome["engine"], outcome["gate"]
        if stage == "train":
            verdict = "MIXED" if g["pass"] else "REJECT"
        else:
            verdict = "PROMISING" if g["pass"] else "REJECT"
        append(CandidateRecord(
            candidate_id=f"{outcome['buy']}::{CHAMPION_SELL}",
            family="entry", source="ai", lane="tick",
            verdict=verdict, recorded_at=stamp,
            buy_name=outcome["buy"], sell_name=CHAMPION_SELL,
            period_start=span[0], period_end=span[1], job_id=outcome.get("job_id"),
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
                f"G2 {stage} · 변형 {outcome['variant']} · "
                f"총수익금 {engine.get('total_profit_krw')} vs 챔피언 {g['champion_krw']:.0f} · "
                f"{'통과' if g['pass'] else '실패'}"),
            notes=("G 생성 레인 — 챔피언 절을 쓰지 않는 **독립 골격**"
                   "(G1 채굴 시드: 초소형×이른 시각). 짝지은 검정 없음 — "
                   "PROMISING 이 상한. 사전 등록: 2026-08-13_G2_G4_사전등록.md"),
        ))
        written += 1
    return written


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-name", default="design_v5")
    parser.add_argument("--stage", choices=("train", "valid"), required=True)
    parser.add_argument("--capital-limit", type=float, default=20_000_000)
    parser.add_argument("--engines", type=int, default=16)
    parser.add_argument("--timeout", type=int, default=9000)
    parser.add_argument("--render-only", action="store_true")
    args = parser.parse_args()

    root = os.path.join(_LABEL_ROOT, args.out_name)
    with open(os.path.join(root, "_g1_setup_distribution.json"),
              encoding="utf-8") as handle:
        seeds = json.load(handle)["seeds"]
    if not seeds:
        raise SystemExit("G1 시드가 없다 — G2 를 돌 이유가 없다")

    if args.render_only:
        for variant in VARIANTS:
            print(f"===== {variant} =====")
            print(render_strategy(seeds, variant))
        return

    lane = LANES["tick"]
    split = split_days(calendar_days(args.out_name))
    days = split[args.stage]
    span = (days[0], days[-1])
    variants = list(VARIANTS)
    if args.stage == "valid":
        train_path = os.path.join(root, "_g2_assemble_train.json")
        if not os.path.exists(train_path):
            raise SystemExit("1차(train) 결과가 없다 — 순서를 지켜라")
        with open(train_path, encoding="utf-8") as handle:
            passed = [o["variant"] for o in json.load(handle)["outcomes"]
                      if o.get("gate", {}).get("pass")]
        if not passed:
            raise SystemExit("1차 통과 셀이 없다 — 검증을 돌 이유가 없다")
        variants = passed[:2]
        print(f"[2차] 1차 통과만 검증: {variants}", flush=True)

    client = Client()
    outcomes: list[dict] = []
    report: dict[str, Any] = {
        "stage": args.stage, "span": list(span), "days": len(days),
        "prereg": "2026-08-13_G2_G4_사전등록.md (57782f64)",
        "champion_metrics": {}, "outcomes": outcomes, "complete": False,
    }
    out_path = os.path.join(root, f"_g2_assemble_{args.stage}.json")

    def save() -> None:
        with open(out_path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=1, default=float)

    t0 = time.time()
    print(f"[구간] {args.stage} {len(days)}일 {span}", flush=True)
    print(f"[기준] 챔피언 {CHAMPION_BUY} + {CHAMPION_SELL}", flush=True)
    champ = _run_arm(client, buy=CHAMPION_BUY, sell=CHAMPION_SELL, lane=lane,
                     engines=args.engines, timeout=args.timeout, period=span)
    report["champion_metrics"] = {k: champ["metrics"].get(k) for k in _METRIC_KEYS}
    champion_krw = float(report["champion_metrics"].get("total_profit_krw") or 0.0)
    print(f"    → {champ['status']} 거래={champ['metrics'].get('trade_count')} "
          f"총수익금={champion_krw:,.0f}", flush=True)
    save()

    for variant in variants:
        name = f"{OWNED_PREFIX}{variant}"
        code = render_strategy(seeds, variant)
        saved = client.call("POST", "/bt/strategy",
                            {"kind": "buy", "name": name, "code": code,
                             "overwrite": True})
        print(f"[{variant}] 등록 {name} {saved.get('status')}", flush=True)
        run = _run_arm(client, buy=name, sell=CHAMPION_SELL, lane=lane,
                       engines=args.engines, timeout=args.timeout, period=span)
        metrics = {k: run["metrics"].get(k) for k in _METRIC_KEYS}
        g = gate(metrics, champion_krw=champion_krw,
                 capital_limit_krw=args.capital_limit)
        outcomes.append({"variant": variant, "buy": name,
                         "job_id": run.get("job_id"), "status": run["status"],
                         "engine": metrics, "gate": g})
        print(f"    → {run['status']} 거래={metrics.get('trade_count')} "
              f"건당={metrics.get('avg_profit_pct')}% "
              f"총수익금={metrics.get('total_profit_krw')} "
              f"{'PASS' if g['pass'] else 'FAIL'}", flush=True)
        save()

    report["complete"] = True
    save()
    written = sync_ledger(report, stage=args.stage)

    print(f"\n=== G2 {args.stage} ({len(days)}일 · {time.time()-t0:.0f}초 "
          f"· 원장 {written}행) ===")
    print(f" {'팔':<18}{'거래':>7}{'건당':>9}{'총수익금':>13}{'자금':>12}  판정")
    print(f" {'챔피언(기준)':<18}{report['champion_metrics'].get('trade_count'):>7}"
          f"{report['champion_metrics'].get('avg_profit_pct'):>8}%{champion_krw:>13,.0f}"
          f"{report['champion_metrics'].get('seed_capital'):>12,.0f}  기준")
    for row in outcomes:
        e = row["engine"]
        print(f" {row['variant']:<18}{e.get('trade_count'):>7}"
              f"{e.get('avg_profit_pct'):>8}%{e.get('total_profit_krw') or 0:>13,.0f}"
              f"{e.get('seed_capital') or 0:>12,.0f}  "
              f"{'PASS' if row['gate']['pass'] else 'FAIL'}")
    if not any(o["gate"]["pass"] for o in outcomes):
        print("\n사전 등록 §6: 1차 전멸 → 반대 가설 성립 절차로 간다.")
    print(f"\n기록: {out_path}", flush=True)


if __name__ == "__main__":
    main()
