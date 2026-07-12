"""O-1G Build — 시가갭×시총 조합표(144셀) 발견창 전수 추출·집계.

사전등록: docs/research/condition_research/plans/
2026-07-11_o1g_gap_feasibility_preregistration.md (봉인 — 조합표·공식·판정 불변).

파이프라인:
  1) 발견창(2022-03-23~2023-12-31) 일별 추출(gap_o1g.extract_day_o1g) —
     일 단위 npz 체크포인트(.done.json 마커)로 재시작 가능.
  2) 전량 결합 → 144셀 §4 지표 + 스피어만 상관 행렬 + §5 판정 원자료(BH-FDR).
  3) L3 순수 스팟 재검(임의 2일, 일당 최대 2,000표본) + 갭 상수성 스팟 집계.
  4) o1g_grid_summary.json(수치 정본) 기록. DB류 대용량 산출 없음.

원본 tick DB read-only(URI mode=ro) · 엔진 백테 0회 · git add/commit 금지.

사용:
  python scripts/o1g_gap_analysis.py [--start 20220323] [--end 20231231]
      [--workspace C:/Temp/o1g_extract] [--engine vector] [--phase all]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from alpha_lab.dataset import reader                              # noqa: E402
from alpha_lab.dataset.labels_v2 import (                         # noqa: E402
    CHAMPION_SELL_SHA256, load_champion_sell_expr, verify_sell_expr,
)
from alpha_lab.stats_common import bh_fdr                         # noqa: E402
from alpha_lab.stats_map import config, config_v2, gap_o1g        # noqa: E402

_RUN_DIR = (_REPO / "docs/research/condition_research/research_runs"
            / "alpha_restart_20260710" / "o1g")
_DEFAULT_PROGRESS = _RUN_DIR / "o1g_progress.txt"
_DEFAULT_SUMMARY = _RUN_DIR / "o1g_grid_summary.json"
_DEFAULT_WORKSPACE = Path("C:/Temp/o1g_extract")
_STRATEGY_DB = _REPO / "_database" / "strategy.db"
_FDR_Q = 0.10           # §5 BH-FDR q(분모 144, 봉인).
_SPOT_DAYS = 2          # L3 순수 스팟 재검 일수(과제 지시).
_SPOT_CAP = 2000        # 일당 스팟 재검 표본 상한(순수 경로 계산량 한계).


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="O-1G 갭 조합표 빌드")
    ap.add_argument("--start", default="20220323")
    ap.add_argument("--end", default="20231231")
    ap.add_argument("--db-dir", default=str(_REPO / "_database"))
    ap.add_argument("--workspace", default=str(_DEFAULT_WORKSPACE))
    ap.add_argument("--out", default=str(_DEFAULT_SUMMARY))
    ap.add_argument("--progress", default=str(_DEFAULT_PROGRESS))
    ap.add_argument("--engine", default="vector", choices=["vector", "pure"])
    ap.add_argument("--phase", default="all", choices=["extract", "aggregate", "all"])
    ap.add_argument("--limit-days", type=int, default=0,
                    help="0=전체, N>0 이면 앞 N일만(타이밍 측정용)")
    return ap.parse_args(argv)


def _log(progress: Path, msg: str) -> None:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with progress.open("a", encoding="utf-8") as fh:
        fh.write(f"{stamp}  {msg}\n")
        fh.flush()


def _load_sell_expr() -> str:
    text = load_champion_sell_expr(_STRATEGY_DB)
    verify_sell_expr(text, CHAMPION_SELL_SHA256)
    return text


def _dates_in_window(db_dir: str, start: str, end: str) -> List[Tuple[str, Path]]:
    return [(d, p) for d, p in reader.list_day_dbs(db_dir) if start <= d <= end]


# ---------------------------------------------------------------------------
# 1단계 — 일별 추출(체크포인트·재시작).
# ---------------------------------------------------------------------------

def extract_all(dates: List[Tuple[str, Path]], workspace: Path, progress: Path,
                sell_text: str, engine: str) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    total = len(dates)
    for i, (date, db_path) in enumerate(dates, start=1):
        npz = workspace / f"o1g_{date}.npz"
        done = workspace / f"o1g_{date}.done.json"
        if npz.exists() and done.exists():
            if i % 25 == 0 or i == total:
                _log(progress, f"extract {i}/{total} date={date} cache")
            continue
        t_start = datetime.now(timezone.utc)
        sample, meta = gap_o1g.extract_day_o1g(
            db_path, date, sell_text, engine=engine)
        np.savez_compressed(npz, **sample)
        done.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        secs = (datetime.now(timezone.utc) - t_start).total_seconds()
        _log(progress, f"extract {i}/{total} date={date} new "
             f"n={meta.get('n_samples', 0):,} "
             f"cand={meta.get('n_candidates', 0):,} {secs:.1f}s")
    _log(progress, f"extract DONE {total} days")


def _load_all(dates: List[Tuple[str, Path]], workspace: Path
              ) -> Tuple[Dict[str, np.ndarray], List[Dict[str, object]]]:
    chunks: List[Dict[str, np.ndarray]] = []
    metas: List[Dict[str, object]] = []
    for date, _ in dates:
        npz = workspace / f"o1g_{date}.npz"
        done = workspace / f"o1g_{date}.done.json"
        with np.load(npz) as data:
            chunks.append({k: data[k] for k in data.files})
        metas.append(json.loads(done.read_text(encoding="utf-8")))
    keys = chunks[0].keys()
    sample = {k: np.concatenate([c[k] for c in chunks]) for k in keys}
    return sample, metas


# ---------------------------------------------------------------------------
# 2단계 — 집계·판정 원자료·스팟 재검·요약 기록.
# ---------------------------------------------------------------------------

def _meta_totals(metas: List[Dict[str, object]]) -> Dict[str, object]:
    """일 메타 → 전체 제외·갭 상수성·L3 stats 합산."""
    tot: Dict[str, object] = {
        "n_candidates": 0, "n_gap_excluded": 0, "n_samples": 0,
        "gap_spread_max_pp": 0.0, "gap_spread_codedays": 0,
        "gap_spread_violations": 0, "l3_stats": {},
    }
    for m in metas:
        tot["n_candidates"] += int(m.get("n_candidates", 0))
        tot["n_gap_excluded"] += int(m.get("n_gap_excluded", 0))
        tot["n_samples"] += int(m.get("n_samples", 0))
        tot["gap_spread_max_pp"] = max(
            float(tot["gap_spread_max_pp"]), float(m.get("gap_spread_max", 0.0)))
        tot["gap_spread_codedays"] += int(m.get("gap_spread_n", 0))
        tot["gap_spread_violations"] += int(m.get("gap_spread_violations", 0))
        for k, v in (m.get("l3_stats") or {}).items():
            tot["l3_stats"][k] = int(tot["l3_stats"].get(k, 0)) + int(v)
    n_cand = max(int(tot["n_candidates"]), 1)
    tot["gap_exclusion_rate"] = round(int(tot["n_gap_excluded"]) / n_cand, 6)
    return tot


def _judgment(cells: List[Dict[str, object]]) -> Dict[str, object]:
    """§5 판정 원자료 — BH-FDR(q=0.10, 분모 144) + strong/weak/insufficient/kill.

    최종 확정은 메인 세션 검토 몫 — 여기서는 봉인 기준의 기계 적용만 기록한다.
    """
    pvals = [1.0 if c["p_one_sided"] is None else float(c["p_one_sided"])
             for c in cells]
    survivors = bh_fdr(pvals, q=_FDR_Q)
    strong: List[int] = []
    weak: List[int] = []
    insufficient: List[int] = []
    for i, cell in enumerate(cells):
        if cell["n"] is None or int(cell["n"]) < config.MIN_CELL_N:
            insufficient.append(i)
            continue
        ci_low = cell["ci_low"]
        mean = cell["mean_net"]
        same_pos = bool(cell["year_same_sign_pos"])
        if bool(survivors[i]) and ci_low is not None and ci_low > 0.0 and same_pos:
            strong.append(i)
        elif mean is not None and mean > 0.0 and same_pos:
            weak.append(i)
    ci_highs = [c["ci_high"] for c in cells if c["ci_high"] is not None]
    kill = bool(ci_highs) and all(h < 0.0 for h in ci_highs)
    return {
        "fdr_q": _FDR_Q, "fdr_denominator": len(cells),
        "n_fdr_survivors": int(survivors.sum()),
        "fdr_survivor_cells": [i for i in range(len(cells)) if survivors[i]],
        "strong_cells": strong, "weak_cells": weak,
        "insufficient_cells": insufficient,
        "kill_all_ci_high_negative": kill,
        "note": "봉인 §5 기준의 기계 적용 — 확정 판정은 메인 세션 검토 후",
    }


def _spot_check_days(dates: List[Tuple[str, Path]]) -> List[Tuple[str, Path]]:
    """L3 순수 스팟 재검 임의 2일 — BUILD_SEED 결정론 추출."""
    rng = np.random.default_rng(config.BUILD_SEED + 1)
    picks = rng.choice(len(dates), size=min(_SPOT_DAYS, len(dates)),
                       replace=False)
    return [dates[int(i)] for i in sorted(picks)]


def _run_l3_spot(dates, workspace: Path, sell_text: str,
                 progress: Path) -> List[Dict[str, object]]:
    reports: List[Dict[str, object]] = []
    for date, db_path in _spot_check_days(dates):
        npz = workspace / f"o1g_{date}.npz"
        with np.load(npz) as data:
            day_sample = {k: data[k] for k in data.files}
        n = int(day_sample["off"].size)
        rng = np.random.default_rng(config.BUILD_SEED + int(date))
        if n > _SPOT_CAP:
            indices = np.sort(rng.choice(n, size=_SPOT_CAP, replace=False))
        else:
            indices = np.arange(n)
        _log(progress, f"l3 pure spot date={date} n={indices.size}")
        rep = gap_o1g.l3_pure_spot_check(
            db_path, date, day_sample, indices, sell_text)
        rep["cap"] = _SPOT_CAP
        reports.append(rep)
        _log(progress, f"l3 pure spot date={date} "
             f"match={rep['n_match']}/{rep['n_compared']} passed={rep['passed']}")
    return reports


def aggregate_and_write(dates, workspace: Path, out_path: Path, progress: Path,
                        sell_text: str, engine: str) -> Dict[str, object]:
    _log(progress, "aggregate: loading day checkpoints ...")
    sample, metas = _load_all(dates, workspace)
    rows_total = int(sample["off"].size)
    _log(progress, f"aggregate: rows_total={rows_total:,} → cells ...")
    cells = gap_o1g.aggregate_cells(sample)
    _log(progress, "aggregate: spearman ...")
    corr = gap_o1g.spearman_matrix(sample)
    judgment = _judgment(cells)
    totals = _meta_totals(metas)
    _log(progress, "aggregate: l3 pure spot check ...")
    l3_spot = _run_l3_spot(dates, workspace, sell_text, progress)
    payload = {
        "doc": "O-1G 갭 조합표 144셀 전수 측정(수치 정본)",
        "preregistration": "docs/research/condition_research/plans/"
                           "2026-07-11_o1g_gap_feasibility_preregistration.md",
        "generated": datetime.now(timezone.utc).isoformat(),
        "build_receipt": {
            "date_start": dates[0][0], "date_end": dates[-1][0],
            "input_days": len(dates), "rows_total": rows_total,
            "n_candidates": totals["n_candidates"],
            "gap_excluded": totals["n_gap_excluded"],
            "gap_exclusion_rate": totals["gap_exclusion_rate"],
            "param_sha_o1g": gap_o1g.param_sha_o1g(),
            "param_sha_v2": config_v2.param_sha_v2(),
            "champion_sell_sha256": CHAMPION_SELL_SHA256,
            "l3_engine": engine,
            "l3_vector_authorization": "V2-B 재현게이트 4/4(시각·가격 일치 1.0) "
                                       "— v2b_pilot_summary.json reproduction_gate",
            "year_tax": {"2022": 0.0023, "2023": 0.0020},
            "fee_rate": 0.00015, "adverse_ticks": 2,
            "n_boot": config.N_BOOT, "build_seed": config.BUILD_SEED,
            "universe_note": "관심종목=1 ≡ moneytop 유니버스(실측 100% 일치) — "
                             "봉인 v1 L0 정의 재사용",
        },
        "spot_checks": {
            "gap_constancy": {
                "codedays_checked": totals["gap_spread_codedays"],
                "max_spread_pp": totals["gap_spread_max_pp"],
                "tolerance_pp": gap_o1g.GAP_CONSTANCY_TOL_PP,
                "violations": totals["gap_spread_violations"],
            },
            "l3_pure_recheck": l3_spot,
        },
        "l3_stats": totals["l3_stats"],
        "cells": cells,
        "corr_matrix": corr,
        "judgment_raw": judgment,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1, allow_nan=False),
        encoding="utf-8")
    _log(progress, f"summary written -> {out_path}")
    return payload


def main(argv=None) -> int:
    args = parse_args(argv)
    workspace = Path(args.workspace)
    progress = Path(args.progress)
    progress.parent.mkdir(parents=True, exist_ok=True)
    _log(progress, f"START phase={args.phase} window={args.start}..{args.end} "
         f"engine={args.engine} param_sha_o1g={gap_o1g.param_sha_o1g()}")
    dates = _dates_in_window(args.db_dir, args.start, args.end)
    if args.limit_days > 0:
        dates = dates[: args.limit_days]
    _log(progress, f"dates resolved: {len(dates)} tick DBs")
    if not dates:
        _log(progress, "ABORT: no tick DBs in window")
        return 2
    sell_text = _load_sell_expr()
    if args.phase in ("extract", "all"):
        extract_all(dates, workspace, progress, sell_text, args.engine)
    if args.phase in ("aggregate", "all"):
        payload = aggregate_and_write(
            dates, workspace, Path(args.out), progress, sell_text, args.engine)
        j = payload["judgment_raw"]
        _log(progress, f"ALL DONE cells=144 rows={payload['build_receipt']['rows_total']:,} "
             f"fdr_survivors={j['n_fdr_survivors']} strong={len(j['strong_cells'])} "
             f"weak={len(j['weak_cells'])} insufficient={len(j['insufficient_cells'])} "
             f"kill={j['kill_all_ci_high_negative']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
