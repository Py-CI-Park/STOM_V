"""챔피언 재현 게이트 (W3) — 지도가 검증된 흑자 전략을 재현하는가.

**이 게이트를 통과하기 전에는 매도 축 탐색을 시작하지 않는다.**

이유: 지도가 챔피언(902/905)의 실전 성적을 부호·크기로 재현하지 못하면, 지도가
찾아내는 어떤 청산 규칙도 엔진에서 재현될 이유가 없다. QSP10~13 이 반복해서
당한 것이 정확히 그것이다(지도 통과 → 엔진 뒤집힘).

측정:
  진입 = 902/905 조건(verify_human_strategy 재사용, 진입 단위 교정 적용)
  청산 = exit_axis 격자 전셀
  대조 = 챔피언 엔진 실측 (182거래 · CAGR +33.24% · 건당 약 +0.35%)

판정:
  PASS   — 격자 중 **정확(exact) 또는 하한(lower_bound)** 셀 하나 이상이
           엔진 실측과 같은 부호이고 크기가 1/3 이상.
  FAIL   — 그런 셀이 없다. 지도의 청산 표현력이 부족하다는 뜻이므로,
           탐색이 아니라 **지도 보강**이 먼저다.
  상한(upper_bound) 셀은 판정 근거가 아니다 — 미래를 참조하기 때문이다.

사용:
    python -m ai_strategy_loop.labeling.run_reproduction_gate --out-name design_v3
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd

from ai_strategy_loop.labeling.entries import entry_positions
from ai_strategy_loop.labeling.exit_axis import default_grid, evaluate
from ai_strategy_loop.labeling.lanes import LANES
from ai_strategy_loop.labeling.trailing import TRAILING_GRID, resolve_grid
from ai_strategy_loop.labeling.run_p3 import RULES, _load
from ai_strategy_loop.labeling.verify_human_strategy import _mask_902, _mask_905

_LABEL_ROOT = os.path.join(os.path.dirname(__file__), "..", "state", "labels")

#: 챔피언 엔진 실측 — 902/905 페어 공식 백테스트(설계 구간).
CHAMPION_ENGINE = {
    "trades": 182,
    "cagr_pct": 33.24,
    "mdd_pct": 18.68,
    "avg_profit_pct": 0.35,     # 건당 약 +3,479원 / 진입 100만원 기준
}

#: 재현 인정 하한 — 엔진 실측의 이 비율 이상이면 "크기까지 재현"으로 본다.
REPRODUCTION_RATIO = 1.0 / 3.0


def _champion_columns() -> set[str]:
    """챔피언 마스크 함수가 참조하는 프레임 열 이름을 소스에서 추출한다.

    `frame["<열>"]` 패턴을 읽는다 — 조건이 바뀌어도 목록이 저절로 따라온다.
    """
    import inspect
    import re

    names: set[str] = set()
    for func in (_mask_902, _mask_905):
        source = inspect.getsource(func)
        names.update(re.findall(r'frame\[\s*"([^"]+)"\s*\]', source))
    return names


def _day_stats(values: np.ndarray, day_codes: np.ndarray, n_days: int) -> dict:
    if values.size == 0:
        return {"n": 0, "expectancy_pct": float("nan"), "day_mean_pct": float("nan"),
                "day_positive_ratio": float("nan"), "days": 0}
    counts = np.bincount(day_codes, minlength=n_days)
    sums = np.bincount(day_codes, weights=values, minlength=n_days)
    active = counts > 0
    daily = sums[active] / counts[active]
    return {"n": int(values.size), "expectancy_pct": float(values.mean()),
            "day_mean_pct": float(daily.mean()),
            "day_positive_ratio": float((daily > 0).mean()), "days": int(len(daily))}


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-name", default="design_v3")
    parser.add_argument("--grid", default="default",
                        help="트레일링 격자: default(6쌍) | wide(36쌍)")
    parser.add_argument("--warmup", type=int, default=60)
    # 격자를 바꿔 돌릴 때 정본 게이트를 덮어쓰지 않기 위한 접미.
    #   `--grid wide` 를 태그 없이 돌리면 엔진 후보 선택의 근거였던 default 격자
    #   게이트가 사라져 그 라운드를 재현할 수 없게 된다.
    parser.add_argument("--tag", default="", help="산출 파일 접미(_wide 등)")
    args = parser.parse_args()

    lane = LANES["tick"]
    hits = sorted({c for rule in RULES for c in rule[2:]})
    envelopes = [f"mfe_{h}" for h in (30, 60, 120, 300, 600)]
    horizons = [f"frA_{h}" for h in lane.horizons] + [f"frB_{h}" for h in lane.horizons]
    # 챔피언 마스크가 실제로 참조하는 열을 **소스에서 추출**한다. 손으로 나열하면
    #   빠진다(실측: '고저평균대비등락율' 누락으로 게이트가 그대로 죽었다).
    variables = sorted(_champion_columns())
    base = ["일자", "종목코드", "시분초", "경과", "관심종목", "spread_pct",
            "flag_no_trade", "flag_limit_up", "flag_vi_near"]
    grid = resolve_grid(args.grid)
    trail_cols = [f"trail_{a:g}_{g:g}" for a, g in grid]

    t0 = time.time()
    columns = base + hits + envelopes + horizons + variables + trail_cols
    frame = _load(args.out_name, columns, args.warmup)
    frame = frame.reset_index(drop=True)
    print(f"집행 우주 {len(frame):,}행 · 로딩 {time.time()-t0:.0f}s", flush=True)

    try:
        mask = (_mask_902(frame) | _mask_905(frame)).to_numpy()
    except KeyError as exc:
        print(f"[불가] 챔피언 조건 열 부재: {exc}", flush=True)
        return

    # 진입 단위 교정 — 엔진은 조건이 참인 첫 초에만 진입한다(QSP12 결함 교정).
    positions = entry_positions(frame, mask, horizon=lane.barrier_horizon)
    print(f"챔피언 진입: 조건 참 {int(mask.sum()):,}초 → 진입 단위 {positions.size:,}건",
          flush=True)
    if positions.size == 0:
        print("[FAIL] 챔피언 진입이 0건이다 — 지도가 이 전략을 표현하지 못한다.", flush=True)
        return

    subset = frame.iloc[positions].reset_index(drop=True)
    day_codes = pd.factorize(subset["일자"].to_numpy())[0]
    n_days = int(day_codes.max() + 1) if day_codes.size else 0

    cells = []
    for rule in default_grid(trailing_grid=grid):
        try:
            values = evaluate(subset, rule)
        except (KeyError, ValueError):
            continue
        stats = _day_stats(values, day_codes, n_days)
        cells.append({"rule": rule.label, "family": rule.family,
                      "exactness": rule.exactness, **stats})

    target = CHAMPION_ENGINE["avg_profit_pct"]
    judgeable = [c for c in cells if c["exactness"] in ("exact", "lower_bound")]
    reproducing = [
        c for c in judgeable
        if c["expectancy_pct"] > 0 and c["expectancy_pct"] >= target * REPRODUCTION_RATIO
    ]
    verdict = "PASS" if reproducing else "FAIL"

    print(f"\n=== 챔피언 재현 게이트: {verdict} ===", flush=True)
    print(f"엔진 실측 대조: 건당 +{target}% · {CHAMPION_ENGINE['trades']}거래 · "
          f"CAGR +{CHAMPION_ENGINE['cagr_pct']}%", flush=True)
    for cell in sorted(cells, key=lambda c: -c["expectancy_pct"])[:12]:
        flag = "★" if cell in reproducing else " "
        print(f" {flag}{cell['rule']:<34} [{cell['exactness']:<11}] "
              f"n={cell['n']:>6,} 건당={cell['expectancy_pct']:+.4f}% "
              f"일평균={cell['day_mean_pct']:+.4f}% 흑자일={cell['day_positive_ratio']:.3f}",
              flush=True)

    if verdict == "FAIL":
        print("\n판정: 지도의 청산 표현력이 챔피언을 재현하지 못한다.", flush=True)
        print("      → 매도 축 탐색을 시작하지 않는다. 지도 보강이 먼저다.", flush=True)

    out_path = os.path.join(_LABEL_ROOT, args.out_name,
                            f"_reproduction_gate{args.tag}.json")
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump({
            "verdict": verdict,
            "grid": args.grid,
            "champion_engine": CHAMPION_ENGINE,
            "reproduction_ratio": REPRODUCTION_RATIO,
            "entry_seconds": int(mask.sum()),
            "entry_positions": int(positions.size),
            "cells": cells,
            "reproducing": [c["rule"] for c in reproducing],
            "note": "상한(upper_bound) 셀은 미래 참조라 판정 근거가 아니다.",
        }, handle, ensure_ascii=False, indent=1)
    print(f"\n저장: {os.path.abspath(out_path)} · 총 {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
