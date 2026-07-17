"""P5 재현게이트 + 청산격자 오프라인 평가 오케스트레이션.

봉인: p5_preregistration_v1.json — replay_gate(오차 중앙값 ≤0.1%p AND 95% 거래
≤1틱, 미달 시 청산 축 전면 폐기)·exit_grid(192 전수)·n_trials(측정 착수 직전
192 선계상). 원장이 유일한 거래 입력, tick DB는 read-only(mode=ro) 전용.

종목명→코드 해석은 P3 봉인 규약 재사용: primary=stock_tick_back.db::stockinfo,
fallback=code_info.db::stockinfo(alpha_lab.mcl.rejoin.load_stockinfo_map),
최종 검증은 '그 거래일에 행이 실재하는 후보가 정확히 1개'로 수행한다
(back DB는 종목 단일 테이블이므로 일 테이블 실재 검증의 등가 형태).
"""
from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from alpha_lab.distill.ledger_wiring import read_ledger
from alpha_lab.distill.replay import (
    CHAMPION_SELL_CONDS,
    FORCE_EXIT_HHMMSS,
    connect_back_ro,
    exit_grid_policies,
    load_day_rows,
    precompute_windows,
    replay_champion_exit,
    replay_path,
    simulate_exit,
    tick_distance,
)
from alpha_lab.mcl.rejoin import load_stockinfo_map
from alpha_lab.stats_common import day_block_bootstrap

__all__ = [
    "GRID_BOOTSTRAP_SEED",
    "N_BOOT",
    "prepare_trades",
    "run_exit_grid",
    "run_replay_gate",
]

logger = logging.getLogger(__name__)

GRID_BOOTSTRAP_SEED = 20260706
N_BOOT = 1000
_CHAMPION_COND_TEXTS = frozenset(CHAMPION_SELL_CONDS.values())


def _day_has_rows(conn: sqlite3.Connection, code: str, day: int) -> bool:
    try:
        row = conn.execute(
            f'SELECT 1 FROM "{code}" WHERE "index" BETWEEN ? AND ? LIMIT 1',
            (day * 1_000_000, day * 1_000_000 + 235959),
        ).fetchone()
    except sqlite3.OperationalError:
        return False  # 테이블 부재.
    return row is not None


def _resolve_code(
    name: str, day: int, conn: sqlite3.Connection,
    primary: Mapping[str, Sequence[str]], fallback: Mapping[str, Sequence[str]],
    cache: Dict[Tuple[str, int], Tuple[Optional[str], str]],
) -> Tuple[Optional[str], str]:
    """종목명 → (코드|None, method|사유) — 거래일 행 실재 검증 포함(캐시)."""
    key = (name, day)
    if key in cache:
        return cache[key]
    candidates = list(primary.get(name, ()))
    method = "primary"
    if not candidates:
        candidates = list(fallback.get(name, ()))
        method = "fallback"
    if not candidates and name.isdigit() and len(name) == 6:
        candidates, method = [name], "code_literal"
    if not candidates:
        cache[key] = (None, "unmapped")
        return cache[key]
    with_rows = [c for c in candidates if _day_has_rows(conn, c, day)]
    if not with_rows:
        cache[key] = (None, "no_day_rows")
    elif len(with_rows) > 1:
        cache[key] = (None, "ambiguous_day_rows")
    else:
        cache[key] = (with_rows[0], method)
    return cache[key]


def prepare_trades(
    records: Sequence[Mapping], conn: sqlite3.Connection,
    primary: Mapping[str, Sequence[str]], fallback: Mapping[str, Sequence[str]],
) -> Tuple[List[dict], Dict[str, int]]:
    """원장 행 → 재현 가능 거래 목록 + 제외 사유 카운트(정직 신고).

    제외 사유: unmapped/no_day_rows/ambiguous_day_rows(매핑),
    foreign_sell_condition(챔피언 매도식에 없는 절 — 변형 런 산출),
    qty_invalid(매수금액/매수가 비정수).
    """
    trades: List[dict] = []
    excl: Dict[str, int] = {}
    cache: Dict[Tuple[str, int], Tuple[Optional[str], str]] = {}
    for rec in records:
        cond = str(rec["매도조건"])
        if cond not in _CHAMPION_COND_TEXTS:
            excl["foreign_sell_condition"] = excl.get("foreign_sell_condition", 0) + 1
            continue
        qty_f = float(rec["매수금액"]) / float(rec["매수가"])
        qty = int(round(qty_f))
        if qty < 1 or abs(qty_f - qty) > 1e-6:
            excl["qty_invalid"] = excl.get("qty_invalid", 0) + 1
            continue
        day = int(str(rec["진입일자"]))
        code, method = _resolve_code(
            str(rec["종목코드"]), day, conn, primary, fallback, cache,
        )
        if code is None:
            excl[method] = excl.get(method, 0) + 1
            continue
        trades.append({
            "code6": code, "진입일자": str(rec["진입일자"]),
            "진입시각": str(rec["진입시각"]), "매수시간": int(rec["매수시간"]),
            "매수가": float(rec["매수가"]), "qty": qty,
            "원장_매도시간": int(rec["매도시간"]), "원장_매도가": float(rec["매도가"]),
            "원장_수익률": float(rec["수익률"]), "원장_매도조건": cond,
            "원장_MFE": float(rec["R_매수후최고수익률"]),
            "원장_MAE": float(rec["R_매수후최저수익률"]),
        })
    return trades, excl


def run_replay_gate(
    ledger_path, back_db_path, fallback_db_path, out_path,
    *, generated: str,
) -> dict:
    """재현게이트 전수 실행 → p5_replay_gate_report.json 기록 + 보고 dict 반환."""
    records = read_ledger(ledger_path)
    primary, _ = load_stockinfo_map(back_db_path)
    fallback, _ = load_stockinfo_map(fallback_db_path)
    conn = connect_back_ro(back_db_path)
    try:
        trades, excl = prepare_trades(records, conn, primary, fallback)
        rows_cache: Dict[Tuple[str, int], tuple] = {}
        results: List[dict] = []
        for tr in trades:
            key = (tr["code6"], int(tr["진입일자"]))
            if key not in rows_cache:
                idxs, arr, ci = load_day_rows(conn, key[0], key[1])
                rows_cache[key] = (idxs, arr, ci, precompute_windows(arr, ci))
            idxs, arr, ci, pre = rows_cache[key]
            rep = replay_champion_exit(
                idxs, arr, ci, pre, buy_time=tr["매수시간"],
                buy_price=tr["매수가"], qty=tr["qty"],
            )
            if rep["status"] != "ok":
                excl[rep["status"]] = excl.get(rep["status"], 0) + 1
                continue
            day = int(tr["진입일자"])
            results.append({
                **{k: tr[k] for k in (
                    "code6", "진입일자", "진입시각", "원장_매도시간",
                    "원장_매도가", "원장_수익률", "원장_매도조건")},
                "재현_매도시간": rep["sell_time"], "재현_매도가": rep["sell_price"],
                "재현_수익률": rep["profit_pct"],
                "재현_매도조건": CHAMPION_SELL_CONDS[int(rep["cond"])],
                "error_pp": round(abs(rep["profit_pct"] - tr["원장_수익률"]), 4),
                "tick_dist": round(tick_distance(rep["sell_price"], tr["원장_매도가"], day), 4),
                "time_match": int(rep["sell_time"] == tr["원장_매도시간"]),
                "cond_match": int(CHAMPION_SELL_CONDS[int(rep["cond"])] == tr["원장_매도조건"]),
                "mfe_err": round(abs(rep["best"] - tr["원장_MFE"]), 4),
                "mae_err": round(abs(rep["worst"] - tr["원장_MAE"]), 4),
            })
        report = _gate_report(results, excl, len(records), generated)
        Path(out_path).write_text(
            json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8",
        )
        logger.info(
            "replay gate: n=%d median=%.4f within1tick=%.4f pass=%s",
            report["n_trades"], report["error_median_pp"],
            report["pct_within_1tick"], report["gate_pass"],
        )
        return report
    finally:
        conn.close()


def _gate_report(results, excl, n_ledger, generated) -> dict:
    err = np.array([r["error_pp"] for r in results], dtype=np.float64)
    dist = np.array([r["tick_dist"] for r in results], dtype=np.float64)
    n = err.size
    median = float(np.median(err)) if n else float("nan")
    within = float(np.mean(dist <= 1.0 + 1e-9)) if n else 0.0
    gate_pass = bool(n > 0 and median <= 0.1 and within >= 0.95)
    return {
        "kind": "p5_replay_gate",
        "generated": generated,
        "sealed_thresholds": {"error_median_pp_max": 0.1, "pct_within_1tick_min": 0.95},
        "n_ledger_rows": n_ledger,
        "n_trades": int(n),
        "exclusions": dict(sorted(excl.items())),
        "error_median_pp": round(median, 6),
        "error_mean_pp": round(float(err.mean()), 6) if n else None,
        "error_p95_pp": round(float(np.percentile(err, 95)), 6) if n else None,
        "error_max_pp": round(float(err.max()), 6) if n else None,
        "pct_within_1tick": round(within, 6),
        "pct_zero_tick": round(float(np.mean(dist <= 1e-9)), 6) if n else None,
        "tick_dist_p95": round(float(np.percentile(dist, 95)), 6) if n else None,
        "tick_dist_max": round(float(dist.max()), 6) if n else None,
        "time_match_rate": round(float(np.mean([r["time_match"] for r in results])), 6) if n else None,
        "cond_match_rate": round(float(np.mean([r["cond_match"] for r in results])), 6) if n else None,
        "mfe_err_median_pp": round(float(np.median([r["mfe_err"] for r in results])), 6) if n else None,
        "mae_err_median_pp": round(float(np.median([r["mae_err"] for r in results])), 6) if n else None,
        "gate_pass": gate_pass,
        "mismatches_top": sorted(
            (r for r in results if r["error_pp"] > 0 or r["tick_dist"] > 0),
            key=lambda r: -r["error_pp"],
        )[:20],
    }


def run_exit_grid(
    ledger_path, back_db_path, fallback_db_path, out_path,
    *, generated: str, seed: int = GRID_BOOTSTRAP_SEED, n_boot: int = N_BOOT,
) -> dict:
    """봉인 격자 192 전수 반사실 평가 → p5_exit_grid_report.json.

    호출 전 게이트 통과 + n_trials 192 선계상이 전제다(오케스트레이션 소관).
    """
    records = read_ledger(ledger_path)
    primary, _ = load_stockinfo_map(back_db_path)
    fallback, _ = load_stockinfo_map(fallback_db_path)
    conn = connect_back_ro(back_db_path)
    try:
        trades, excl = prepare_trades(records, conn, primary, fallback)
        paths: List[Tuple[dict, List[Tuple[int, float]]]] = []
        for tr in trades:
            path = replay_path(tr, conn, force_exit_hhmmss=FORCE_EXIT_HHMMSS)
            if not path:
                excl["path_empty"] = excl.get("path_empty", 0) + 1
                continue
            paths.append((tr, path))
    finally:
        conn.close()
    day_ids = np.array([int(tr["진입일자"]) for tr, _ in paths], dtype=np.int64)
    order = np.lexsort((
        np.array([tr["매수시간"] for tr, _ in paths], dtype=np.int64), day_ids,
    ))
    mask = np.ones(len(paths), dtype=bool)
    policies = exit_grid_policies()
    rows: List[dict] = []
    for pol_idx, policy in enumerate(policies):
        rates = np.empty(len(paths), dtype=np.float64)
        secs = np.empty(len(paths), dtype=np.float64)
        reasons: Dict[str, int] = {}
        for j, (tr, path) in enumerate(paths):
            sim = simulate_exit(path, policy, entry_price=tr["매수가"])
            rates[j] = sim["net_rate"]
            secs[j] = sim["exit_sec"]
            reasons[sim["reason"]] = reasons.get(sim["reason"], 0) + 1
        boot = day_block_bootstrap(
            day_ids, rates, mask, n_boot=n_boot, seed=seed + pol_idx, stat="mean",
        )
        cum = np.cumsum(rates[order] * 100.0)
        peak = np.maximum.accumulate(np.concatenate(([0.0], cum)))[1:]
        mdd_pp = float(np.max(peak - cum)) if cum.size else float("nan")
        rows.append({
            "policy": policy,
            "n_trades": int(len(paths)),
            "ev_pct": round(float(rates.mean() * 100.0), 4),
            "ev_ci_low_pct": round(boot["ci_low"] * 100.0, 4),
            "ev_ci_high_pct": round(boot["ci_high"] * 100.0, 4),
            "p_one_sided": round(boot["p_one_sided"], 4),
            "mdd_pp": round(mdd_pp, 2),
            "hold_mean_sec": round(float(secs.mean()), 1),
            "hold_p50_sec": round(float(np.percentile(secs, 50)), 1),
            "hold_p90_sec": round(float(np.percentile(secs, 90)), 1),
            "reasons": dict(sorted(reasons.items())),
        })
        if (pol_idx + 1) % 24 == 0:
            logger.info("exit grid progress: %d/%d", pol_idx + 1, len(policies))
    best_idx = int(np.argmax([r["ev_ci_low_pct"] for r in rows]))
    report = {
        "kind": "p5_exit_grid",
        "generated": generated,
        "n_policies": len(rows),
        "n_trades": int(len(paths)),
        "exclusions": dict(sorted(excl.items())),
        "bootstrap": {"n_boot": n_boot, "seed_base": seed, "stat": "mean",
                      "block": "entry_day"},
        "force_exit_hhmmss": FORCE_EXIT_HHMMSS,
        "best_by_ev_ci_low": rows[best_idx],
        "top10_by_ev_ci_low": sorted(
            rows, key=lambda r: -r["ev_ci_low_pct"])[:10],
        "champion_analog": next(
            (r for r in rows if r["policy"]["hard_stop_pct"] == -5.0
             and r["policy"]["trailing_pct"] == 60.0
             and r["policy"]["time_stop_sec"] is None
             and r["policy"]["profit_cap_pct"] is None), None),
        "policies": rows,
    }
    Path(out_path).write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8",
    )
    logger.info("exit grid done: %d policies, best ci_low=%.4f%%",
                len(rows), rows[best_idx]["ev_ci_low_pct"])
    return report
