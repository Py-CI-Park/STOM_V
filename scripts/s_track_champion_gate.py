"""W4-2b 챔피언 칸 게이트 + advisory 밴드 오버레이 러너(연구 전용).

사전등록 §6. 본 적재(stats_map.db)가 완성된 뒤 실행한다. 원본·strategy.db는
read-only, 엔진 백테 0회. 산출: w4_champion_overlay.json.

  ① 챔피언 게이트: ALP_V4 4종 발견창(<=2023-12-31) 진입점 → 칸 사상 →
     occupied 칸 L1 mean_net(h300) vs 전체 L1 평균, >=3/4 통과 판정.
  ② tick DB 동치 스팟체크: 표본 진입의 tick DB 등락율/시총이 원장 B_ 값과 동일함
     (=진입 시점 tick 조회와 동치)을 max_abs_err로 증명.
  ③ advisory 오버레이: 인간 전당 공통 밴드(09:00~09:30 전 버킷) + 파싱 가능한
     챔피언·902905 시드 조건식 밴드의 상대 EV.

사용:
  STOM_ALLOW_MINIMAL_SETTING=1 python scripts/s_track_champion_gate.py
"""
from __future__ import annotations

import argparse
import glob
import json
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from alpha_lab.dataset.reader import connect_ro  # noqa: E402
from alpha_lab.stats_map import champion, config, extract, overlay  # noqa: E402

_RUN_DIR = (_REPO / "docs/research/condition_research/research_runs"
            / "alpha_restart_20260710")
_DEFAULT_DB = _RUN_DIR / "stats_map" / "stats_map.db"
_CHAMPIONS = ("RR8_0", "RR8_21", "RR8_12", "GPTAUTH_G8")
_DISCOVERY_END = 20231231


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="W4-2b 챔피언 칸 게이트 + 오버레이")
    ap.add_argument("--db", default=str(_DEFAULT_DB))
    ap.add_argument("--db-dir", default=str(_REPO / "_database"))
    ap.add_argument("--strategy-db", default=str(_REPO / "_database/strategy.db"))
    ap.add_argument("--out", default=str(_RUN_DIR / "w4_champion_overlay.json"))
    return ap.parse_args(argv)


def pick_discovery_csv(key: str) -> Optional[str]:
    """챔피언 key의 발견창 포함(2022 시작) per-trade CSV 경로 — 결정론 선택."""
    best = None
    for f in sorted(glob.glob(
            str(_REPO / f"backtest/csv/stock_bt_ALP_V4_{key}_*.csv"))):
        bt = pd.read_csv(f, encoding="utf-8")["매수시간"].astype("int64")
        if int(bt.min()) // 1_000_000 <= _DISCOVERY_END:
            best = f
    return best


def name_to_code(db_dir) -> Dict[str, str]:
    """code_info.stockinfo → {종목명: 6자리코드}(첫 매칭). 스팟체크 전용."""
    conn = sqlite3.connect(
        f"file:{(Path(db_dir) / 'code_info.db').as_posix()}?mode=ro", uri=True)
    try:
        out: Dict[str, str] = {}
        for idx, nm, _ in conn.execute(
                "SELECT \"index\",종목명,코스닥 FROM stockinfo"):
            out.setdefault(str(nm), str(idx))
        return out
    finally:
        conn.close()


def tick_equivalence_spotcheck(csv_by_champ: Dict[str, str], db_dir,
                               per_champ: int = 15) -> Dict[str, object]:
    """진입 표본의 tick DB 등락율/시총이 원장 B_ 값과 동일함을 max_abs_err로 확인."""
    n2c = name_to_code(db_dir)
    errs_ud: List[float] = []
    errs_mc: List[float] = []
    checked = misses = 0
    for key, path in csv_by_champ.items():
        df = pd.read_csv(path, encoding="utf-8")
        df = df[(df["매수시간"] // 1_000_000) <= _DISCOVERY_END].head(per_champ)
        for _, r in df.iterrows():
            code = n2c.get(r["종목명"])
            day = int(r["매수시간"]) // 1_000_000
            hms = int(r["매수시간"]) % 1_000_000
            dbp = Path(db_dir) / f"stock_tick_{day}.db"
            if not code or not dbp.exists():
                misses += 1
                continue
            conn = connect_ro(dbp)
            dense = extract._load_dense(conn, code)
            conn.close()
            if dense is None:
                misses += 1
                continue
            off = champion._entry_offset(hms)
            if not (0 <= off <= config.WINDOW_SECONDS):
                misses += 1
                continue
            errs_ud.append(abs(float(dense["등락율"][off]) - float(r["B_등락율"])))
            errs_mc.append(abs(float(dense["시가총액"][off]) - float(r["B_시가총액"])))
            checked += 1
    return {
        "n_checked": checked, "n_missed": misses,
        "max_abs_err_updown": max(errs_ud) if errs_ud else None,
        "max_abs_err_mktcap": max(errs_mc) if errs_mc else None,
    }


def seed_strategy_names(strategy_db, limit: int = 4) -> List[str]:
    """strategy.db stockbuy에서 902/905 시드 계보 전략명(결정론 상위 N)."""
    conn = sqlite3.connect(
        f"file:{Path(strategy_db).as_posix()}?mode=ro", uri=True)
    try:
        names = sorted(n for (n,) in conn.execute(
            'SELECT "index" FROM stockbuy')
            if ("902905" in str(n)) or ("902_905" in str(n)))
        return names[:limit]
    finally:
        conn.close()


def human_hall_common_band(db_path) -> Dict[str, object]:
    """인간 전당 공통 밴드(09:00~09:30 전 버킷·전 분위) 상대 EV — 비차별 확인."""
    l0 = champion.read_cells(db_path, "cells_l0", config.AXIS_TIME_UD, 300)
    l1 = champion.read_cells(db_path, "cells_l1", config.AXIS_TIME_UD, 300)
    allcells = [(tb, uq, -1) for tb in range(6) for uq in range(4)]
    return {
        "band": "09:00-09:30 all buckets, all updown quartiles (only recorded "
                "human-hall band; reference_strategies.json)",
        "l0": overlay.band_relative_ev(l0, allcells),
        "l1": overlay.band_relative_ev(l1, allcells),
    }


def main(argv=None) -> int:
    args = parse_args(argv)
    db = args.db
    csv_by_champ = {k: pick_discovery_csv(k) for k in _CHAMPIONS}
    missing = [k for k, v in csv_by_champ.items() if v is None]
    if missing:
        print(f"WARN: no discovery CSV for {missing}", file=sys.stderr)
    gate = champion.run_gate(
        {k: v for k, v in csv_by_champ.items() if v}, db)
    spot = tick_equivalence_spotcheck(
        {k: v for k, v in csv_by_champ.items() if v}, args.db_dir)
    strat_names = list(f"ALP_V4_{k}" for k in _CHAMPIONS) \
        + seed_strategy_names(args.strategy_db)
    band_overlay = overlay.overlay(db, strat_names, args.strategy_db)
    payload = {
        "champion_gate": gate,
        "tick_equivalence_spotcheck": spot,
        "overlay_advisory": {
            "human_hall_common_band": human_hall_common_band(db),
            "strategy_condition_bands": band_overlay,
        },
        "csv_files": {k: (Path(v).name if v else None)
                      for k, v in csv_by_champ.items()},
    }
    Path(args.out).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8")
    _digest(payload)
    print(f"overlay summary -> {args.out}")
    return 0


def _digest(payload: Dict[str, object]) -> None:
    g = payload["champion_gate"]
    s = payload["tick_equivalence_spotcheck"]
    print("=== W4-2b 챔피언 칸 게이트 ===")
    print(f"gate_passed={g['gate_passed']}  통과 {g['n_pass_l1']}/{g['n_champions']}")
    for c in g["champions"]:
        print(f"  {c['champion']:<12} champ_L1_EV={_f(c['champ_l1_cell_ev'])} "
              f"pooled_L1={_f(c['pooled_l1_mean_net'])} adv={_f(c['l1_advantage'])} "
              f"cov={c['l1_coverage_pct']}%  {'PASS' if c['passed'] else 'FAIL'}")
    print(f"tick 동치 스팟체크: n={s['n_checked']} "
          f"max_err(ud)={s['max_abs_err_updown']} max_err(mc)={s['max_abs_err_mktcap']}")


def _f(x) -> str:
    return f"{x*100:.3f}%" if isinstance(x, float) else "NA"


if __name__ == "__main__":
    raise SystemExit(main())
