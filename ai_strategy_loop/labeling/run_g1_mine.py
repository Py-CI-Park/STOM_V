"""G1 — 승자 셋업 채굴. 새 골격의 씨앗을 데이터에서 캔다.

사전 등록: `docs/research/quant_scoring_pipeline/2026-08-12_G1_사전등록.md`
(커밋 `0a7f5c80` — 실행 전)

## 이것은 발굴이지 판정이 아니다

`backfinder_principle` 은 **전방 고가 도달**(lookahead) 라벨러다 — 산출 lift 는
"그 셀의 승자 비율이 전체보다 몇 배냐"이지 **실현 수익이 아니다**. 여기서 나온
어떤 분위도 채택되지 않는다. 판정은 G4 엔진 A/B 만 한다.

## 우주 제약이 코드로 강제된다

HOF4 실측: 놓친 승자의 69%가 관심종목 밖이었다. 제약 없이 캐면 **실전에서 살 수
없는 종목**의 시드가 나온다. 그래서 채굴 대상은 그날 09:00~09:20 moneytop 에
등재된 종목 ∩ DB 보유 테이블로 한정한다(`watchlist_codes`).

사용:
    python -m ai_strategy_loop.labeling.run_g1_mine --out-name design_v5
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sqlite3
import sys
import time
from typing import Any, Final, Sequence

import pandas as pd

from ai_strategy_loop.fitness.backfinder_principle import (
    DEFAULT_FEATURE_COLS, mine_tick_window, winning_setup_distribution)
from ai_strategy_loop.labeling.run_trade_autopsy import (
    _LABEL_ROOT, calendar_days, split_days)

_TICK_DB: Final = os.path.join(os.path.dirname(__file__), "..", "..",
                               "_database", "stock_tick_back.db")

#: 사전 등록 §4 — 실행 전 고정. 값을 바꾸려면 새 라운드를 등록해야 한다.
WINDOW_LO: Final = 90000
WINDOW_HI: Final = 92000          # 사용자 확정: 09:20 이 최대
LOOKAHEAD_TICKS: Final = 300
THRESHOLD_PCT: Final = 5.0        # 모듈 기본 10.0 에서 이탈 — HOF4 승자 정의와 정렬
MIN_CELL_COUNT: Final = 30        # 모듈 세그먼트 하한

#: 사전 등록 §5 — 시드 게이트.
GATE_MIN_COUNT: Final = 200
GATE_MIN_LIFT: Final = 1.30
GATE_MIN_WINNERS: Final = 30
SEED_BUDGET: Final = 8


def watchlist_codes(con: sqlite3.Connection, day: int, tables: set[str]) -> list[str]:
    """그날 창 안에서 moneytop 에 오른 종목 ∩ DB 보유 테이블.

    '관심종목' 우주를 코드로 강제하는 지점이다(사전 등록 §3.1).
    """
    lo = day * 1_000_000 + WINDOW_LO
    hi = day * 1_000_000 + WINDOW_HI
    rows = con.execute(
        'SELECT 거래대금순위 FROM moneytop WHERE "index" BETWEEN ? AND ?', (lo, hi)
    ).fetchall()
    codes: set[str] = set()
    for (text,) in rows:
        codes.update(str(text).split(";"))
    return sorted(codes & tables)


def apply_gate(cells: Sequence[dict], *, budget: int = SEED_BUDGET) -> list[dict]:
    """사전 등록 §5 게이트 — count·lift·winner_count 를 넘긴 셀만, 세그먼트당 1개.

    lift 내림차순으로 고르되 **시간 세그먼트당 하나**만 남긴다(가설 예산 15항 —
    같은 시간대에서 여러 시총 셀을 다 가져가면 예산이 한 시간대에 몰린다).
    """
    passed = [
        c for c in cells
        if (c.get("count") or 0) >= GATE_MIN_COUNT
        and (c.get("lift") is not None and float(c["lift"]) >= GATE_MIN_LIFT)
        and (c.get("winner_count") or 0) >= GATE_MIN_WINNERS
    ]
    passed.sort(key=lambda c: float(c.get("lift") or 0.0), reverse=True)
    seen: set[str] = set()
    seeds: list[dict] = []
    for cell in passed:
        segment = str(cell.get("time_segment") or cell.get("_time_segment") or "")
        if segment in seen:
            continue
        seen.add(segment)
        seeds.append(cell)
        if len(seeds) >= budget:
            break
    return seeds


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-name", default="design_v5")
    parser.add_argument("--db", default=_TICK_DB)
    parser.add_argument("--limit-days", type=int, default=0,
                        help="0 이면 학습 구간 전체(사전 등록 값). 스모크용")
    args = parser.parse_args()

    db_path = os.path.abspath(args.db)
    split = split_days(calendar_days(args.out_name))
    days = split["train"]
    if args.limit_days:
        days = days[:args.limit_days]

    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        tables = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        universe = {day: watchlist_codes(con, day, tables) for day in days}
    finally:
        con.close()

    total_codes = sum(len(v) for v in universe.values())
    print(f"[구간] 학습 {len(days)}일 ({days[0]}~{days[-1]}) — 검증·확인 미접촉", flush=True)
    print(f"[우주] moneytop 교집합 종목-일 {total_codes:,} "
          f"(일평균 {total_codes/max(1,len(days)):.0f})", flush=True)
    print(f"[정의] 창 {WINDOW_LO}~{WINDOW_HI} · {LOOKAHEAD_TICKS}틱 · "
          f"문턱 {THRESHOLD_PCT}% (모듈 기본 10.0 에서 이탈 — 사전 등록 §4)", flush=True)

    frames: list[pd.DataFrame] = []
    winners = 0
    t0 = time.time()
    for i, day in enumerate(days, 1):
        codes = universe[day]
        if not codes:
            continue
        out = mine_tick_window(db_path, codes, [day],
                               time_lo=WINDOW_LO, time_hi=WINDOW_HI,
                               lookahead_ticks=LOOKAHEAD_TICKS,
                               threshold_pct=THRESHOLD_PCT,
                               feature_cols=DEFAULT_FEATURE_COLS)
        frame = out.get("all")
        if frame is None or frame.empty:
            continue
        frames.append(frame)
        winners += int(frame["is_winner"].sum())
        if i % 50 == 0:
            rows = sum(len(f) for f in frames)
            print(f"  … {i}/{len(days)}일 · 라벨 {rows:,} · 승자 {winners:,} "
                  f"({time.time()-t0:.0f}초)", flush=True)

    if not frames:
        print("라벨 행 0 — 채굴 실패. 사전 등록 §5: 재실행 금지, 새 라운드로 등록한다.")
        return
    labeled = pd.concat(frames, ignore_index=True)
    base_rate = float(labeled["is_winner"].mean())
    cells = winning_setup_distribution(labeled, DEFAULT_FEATURE_COLS,
                                       fine_time=True, min_count=MIN_CELL_COUNT)
    seeds = apply_gate(cells)

    report: dict[str, Any] = {
        "prereg": "2026-08-12_G1_사전등록.md (0a7f5c80)",
        "train_span": [days[0], days[-1]], "train_days": len(days),
        "universe_code_days": total_codes,
        "window": [WINDOW_LO, WINDOW_HI],
        "lookahead_ticks": LOOKAHEAD_TICKS, "threshold_pct": THRESHOLD_PCT,
        "labeled_rows": int(len(labeled)), "winner_rows": int(winners),
        "base_rate": base_rate,
        "gate": {"min_count": GATE_MIN_COUNT, "min_lift": GATE_MIN_LIFT,
                 "min_winners": GATE_MIN_WINNERS, "budget": SEED_BUDGET},
        "cells": cells, "seeds": seeds,
        "note": ("시드 전용 — lift 는 lookahead(전방 고가 도달) 라벨 기준이며 "
                 "실현 수익이 아니다. 채택 판정은 G4 엔진 A/B 만 한다."),
    }
    out_dir = os.path.join(_LABEL_ROOT, args.out_name)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "_g1_setup_distribution.json")
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=1, default=float)

    print(f"\n=== G1 채굴 ({len(days)}일 · {time.time()-t0:.0f}초) ===")
    print(f" 라벨 행 {len(labeled):,} · 승자 {winners:,} · 기저 승률 {base_rate*100:.3f}%")
    print(f" 세그먼트 셀 {len(cells)} · **게이트 통과 시드 {len(seeds)}**")
    print(f"\n {'시간대':<14}{'시총':<10}{'count':>9}{'winners':>9}{'lift':>7}  게이트")
    for cell in sorted(cells, key=lambda c: float(c.get("lift") or 0), reverse=True)[:15]:
        ok = "통과" if cell in seeds else ""
        print(f" {str(cell.get('time_segment')):<14}{str(cell.get('market_cap_segment')):<10}"
              f"{cell.get('count', 0):>9,}{cell.get('winner_count', 0):>9,}"
              f"{float(cell.get('lift') or 0):>7.2f}  {ok}")
    if not seeds:
        print("\n사전 등록 §5: 통과 0 → '진입 직전 피처로 승자 예측 불가' 확정 절차로 간다.")
    print(f"\n기록: {out_path}", flush=True)


if __name__ == "__main__":
    main()
