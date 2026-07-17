"""D9 측정 오케스트레이션 — R1(전이 온셋 추출·체크포인트) + R3(서브모집단 대조).

R1: 발견창 437일 루프 — 일별 parquet 체크포인트(parts/tr_{date}.parquet + meta_{date}.json),
    재시작 시 완료 일 건너뜀. 소비 후 consolidate → d9_transition_bank.parquet(git 제외).
    행 패리티(§14-7)·재현 게이트(§4.2, 스팟 일)·서브모집단 카운트·표본 하한을 R1 리포트로.
R3: d9_transition_bank + 기존 onset_l3_bank(서지 기준선) → 겹침률(§8) + 3 서브모집단 Δ 판정
    (judge_d9). 패리티 게이트·겹침 게이트 미통과 시 판정 정지(§10 kill-3·§14-7 정지 규칙).

원본 tick DB read-only. 엔진 백테 0회. git 커밋은 메인 세션 몫.
"""
from __future__ import annotations

import json
import logging
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from alpha_lab.clause_lab.bank import day_list
from alpha_lab.d9lab import judge_d9, overlap, transitions

logger = logging.getLogger(__name__)

__all__ = [
    "PARITY_GATE_MIN",
    "consolidate_r1",
    "load_surge_baseline",
    "load_transition_bank",
    "run_r1",
    "run_r3",
    "spot_reproduction_check",
]

PARITY_GATE_MIN = 0.999    # §14-7 — 엔진-가시 vs GT 일치율 하한(미달 시 R3 진입 금지).
_REPRO_MIN = 0.999         # §4.2 L3 순수/벡터 재현 게이트.


def _log(progress: Path, msg: str) -> None:
    line = f"{datetime.now().isoformat()} {msg}"
    with open(progress, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    logger.info(msg)


def run_r1(
    db_dir, run_dir, parts_dir, sell_text: str,
    *, days: Optional[Sequence[Tuple[str, Path]]] = None,
    spot_days: Sequence[str] = (), progress_name: str = "d5_d9_r1_progress.txt",
) -> Dict[str, object]:
    """R1 일 루프 — 일별 전이 온셋 parquet + meta 체크포인트, 재시작 가능.

    days 미지정 시 발견창 437일 전체. spot_days 는 순수 경로 L3 도 산출(재현 게이트용).
    """
    parts = Path(parts_dir)
    parts.mkdir(parents=True, exist_ok=True)
    progress = Path(run_dir) / progress_name
    spot = set(spot_days)
    day_paths = list(days) if days is not None else day_list(db_dir)
    _log(progress, f"D5-D9-R1 start: {len(day_paths)} days spot={sorted(spot)} parts={parts}")

    t_all = time.monotonic()
    done = 0
    for date, path in day_paths:
        part = parts / f"tr_{date}.parquet"
        meta_p = parts / f"meta_{date}.json"
        if part.exists() and meta_p.exists():
            done += 1
            continue
        t0 = time.monotonic()
        try:
            rec, meta = transitions.build_day_transitions(
                path, date, sell_text, spot_pure=(date in spot))
            frame = pd.DataFrame({k: rec[k] for k in rec})
            tmp = parts / f"tr_{date}.tmp.parquet"
            frame.to_parquet(tmp, index=False)
            tmp.replace(part)
            meta_p.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
            done += 1
            _log(progress, f"  {date}: onsets={meta['n_onsets']} obs={meta['n_observable']} "
                 f"new={meta['n_new']} re={meta['n_reentry']} labeled={meta['n_labeled']} "
                 f"parity={meta['parity_n_match']}/{meta['parity_n_rows']} "
                 f"({time.monotonic()-t0:.1f}s) [{done}/{len(day_paths)}]")
        except Exception as exc:  # noqa: BLE001 — 정직 신고 후 계속(재시작 가능).
            _log(progress, f"  {date}: ERROR {exc!r}\n{traceback.format_exc()}")
    _log(progress, f"D5-D9-R1 done: {done}/{len(day_paths)} days, {(time.monotonic()-t_all)/60:.1f} min")
    return {"days_done": done, "days_total": len(day_paths)}


def consolidate_r1(parts_dir, bank_path) -> Dict[str, object]:
    """일별 parts → d9_transition_bank.parquet + 집계 메타(패리티·서브모집단·하한 실측)."""
    parts = sorted(Path(parts_dir).glob("tr_*.parquet"))
    if not parts:
        raise FileNotFoundError(f"parts 없음: {parts_dir}")
    frames = [pd.read_parquet(p) for p in parts]
    full = pd.concat(frames, ignore_index=True)
    keep = [c for c in transitions.TRANSITION_COLUMNS if c in full.columns]
    bank = full[keep].copy()
    Path(bank_path).parent.mkdir(parents=True, exist_ok=True)
    bank.to_parquet(bank_path, index=False)

    p_rows = p_match = 0
    for p in parts:
        meta_p = p.parent / f"meta_{p.name[len('tr_'):-len('.parquet')]}.json"
        if meta_p.exists():
            m = json.loads(meta_p.read_text(encoding="utf-8"))
            p_rows += int(m.get("parity_n_rows", 0))
            p_match += int(m.get("parity_n_match", 0))
    parity_pct = (p_match / p_rows) if p_rows else float("nan")

    obs = bank["observable"].to_numpy().astype(bool)
    re = bank["is_reentry"].to_numpy().astype(bool)
    lab = bank["l3_labeled"].to_numpy().astype(bool)
    yr = bank["year"].to_numpy()
    return {
        "n_parts": len(parts), "n_onsets": int(bank.shape[0]),
        "n_observable": int(obs.sum()),
        "n_new_obs": int((obs & ~re).sum()), "n_reentry_obs": int((obs & re).sum()),
        "n_labeled_obs": int((obs & lab).sum()),
        "parity_n_rows": p_rows, "parity_n_match": p_match,
        "parity_match_pct": parity_pct,
        "parity_gate_pass": bool(np.isfinite(parity_pct) and parity_pct >= PARITY_GATE_MIN),
        "floors": _floor_measure(bank, obs, re, lab, yr),
        "bank_path": str(bank_path),
    }


def _floor_measure(bank, obs, re, lab, yr) -> Dict[str, object]:
    """서브모집단별 관측가능·라벨 표본 하한 실측(§5·§14-4)."""
    base = obs & lab
    out: Dict[str, object] = {}
    for name, mask in (("new", base & ~re), ("reentry", base & re), ("pooled", base)):
        total, per_year = judge_d9.SUBPOP_FLOORS[name]
        n = int(mask.sum())
        n22 = int((mask & (yr == 2022)).sum())
        n23 = int((mask & (yr == 2023)).sum())
        out[name] = {
            "n": n, "n_2022": n22, "n_2023": n23,
            "floor_total": total, "floor_year": per_year,
            "floor_pass": bool(n >= total and n22 >= per_year and n23 >= per_year),
        }
    return out


def spot_reproduction_check(parts_dir, spot_days: Sequence[str]) -> Dict[str, object]:
    """스팟 일 순수 vs 벡터 L3 청산시각·net 일치(§4.2 재현 게이트) — 벡터 경로 허가 근거."""
    out: Dict[str, object] = {"spot_days": list(spot_days), "per_day": []}
    all_pass = True
    for date in spot_days:
        p = Path(parts_dir) / f"tr_{date}.parquet"
        if not p.exists():
            out["per_day"].append({"day": date, "status": "part_missing"})
            all_pass = False
            continue
        d = pd.read_parquet(p)
        if "l3_net_pure" not in d.columns:
            out["per_day"].append({"day": date, "status": "no_pure_columns"})
            all_pass = False
            continue
        both = d["l3_labeled"].to_numpy().astype(bool) & d["l3_labeled_pure"].to_numpy().astype(bool)
        net_v = d["l3_net"].to_numpy(dtype=np.float64)[both]
        net_p = d["l3_net_pure"].to_numpy(dtype=np.float64)[both]
        exit_v = d["l3_exit"].to_numpy(dtype=np.int64)[both]
        exit_p = d["l3_exit_pure"].to_numpy(dtype=np.int64)[both]
        net_err = float(np.max(np.abs(net_v - net_p))) if both.any() else 0.0
        exit_match = float(np.mean(exit_v == exit_p)) if both.any() else 1.0
        day_pass = bool(net_err <= 1e-12 and exit_match >= _REPRO_MIN)
        all_pass = all_pass and day_pass
        out["per_day"].append({"day": date, "n_paired": int(both.sum()),
                               "net_max_abs_err": net_err,
                               "exit_match_rate": exit_match, "pass": day_pass})
    out["reproduction_pass"] = bool(all_pass)
    return out


def load_transition_bank(bank_path) -> Tuple[pd.DataFrame, Dict[str, np.ndarray]]:
    """d9_transition_bank → (전체 df, 관측가능·라벨된 {net_pp, day, year, is_reentry})."""
    df = pd.read_parquet(bank_path)
    m = df["observable"].to_numpy().astype(bool) & df["l3_labeled"].to_numpy().astype(bool)
    tr = {
        "net_pp": df["l3_net"].to_numpy(dtype=np.float64)[m] * 100.0,
        "day": df["day"].to_numpy(dtype=np.int64)[m],
        "year": df["year"].to_numpy(dtype=np.int64)[m],
        "is_reentry": df["is_reentry"].to_numpy().astype(bool)[m],
    }
    return df, tr


def load_surge_baseline(
    surge_bank_path, *, restrict_days: Optional[Sequence[int]] = None,
) -> Dict[str, np.ndarray]:
    """기존 onset_l3_bank(서지) → 라벨된 {net_pp, day, year} (read-only).

    restrict_days 지정 시 그 일자만(스모크 관통용 동일-일 기준선 — 판정 아님).
    """
    df = pd.read_parquet(surge_bank_path, columns=["day", "year", "l3_net", "l3_labeled"])
    m = df["l3_labeled"].to_numpy().astype(bool)
    if restrict_days is not None:
        m = m & df["day"].isin(list(restrict_days)).to_numpy()
    return {
        "net_pp": df["l3_net"].to_numpy(dtype=np.float64)[m] * 100.0,
        "day": df["day"].to_numpy(dtype=np.int64)[m],
        "year": df["year"].to_numpy(dtype=np.int64)[m],
    }


def run_r3(
    transition_bank_path, surge_bank_path, r1_summary: Mapping[str, object],
    *, match_surge_days: bool = False,
) -> Dict[str, object]:
    """R3 판정 — 겹침률(§8) + 3 서브모집단 Δ(judge_d9). 게이트 미통과 시 판정 정지.

    r1_summary 는 consolidate_r1 결과(패리티 게이트 확인용, §14-7 정지 규칙).
    match_surge_days=True 면 서지 기준선을 전이 은행의 일자로 제한(스모크 관통 전용).
    """
    df, tr = load_transition_bank(transition_bank_path)
    restrict = np.unique(df["day"].to_numpy()).tolist() if match_surge_days else None
    sg = load_surge_baseline(surge_bank_path, restrict_days=restrict)
    ov = overlap.compute_overlap(df, surge_bank_path)

    parity_pass = bool(r1_summary.get("parity_gate_pass"))
    proceed = parity_pass and ov["gate_pass"]
    result: Dict[str, object] = {
        "kind": "d5_d9_r3",
        "generated": datetime.now(timezone.utc).isoformat(),
        "preregistration": "2026-07-12_d5_d9_transition_onset_preregistration.md (§14 봉인)",
        "parity_gate_pass": parity_pass,
        "overlap": ov,
        "proceed_to_judgment": proceed,
    }
    if not proceed:
        reason = []
        if not parity_pass:
            reason.append("패리티 <99.9%(§14-7 정지 규칙 — R3 진입 금지)")
        if not ov["gate_pass"]:
            reason.append(f"겹침률 {ov['primary_pooled_rate']:.4f} >0.50(§8 kill-3)")
        result["halt_reason"] = "; ".join(reason)
        result["judgment"] = None
        return result

    result["judgment"] = judge_d9.judge_all_d9(tr, sg)
    return result


def build_r1_summary(
    consolidate_meta: Mapping[str, object], overlap_result: Mapping[str, object],
    repro: Mapping[str, object], *, days_measured: int,
) -> Dict[str, object]:
    """R1 정본 summary — 패리티·재현·겹침·서브모집단·하한을 한 페이로드로."""
    return {
        "kind": "d5_d9_r1_summary",
        "generated": datetime.now(timezone.utc).isoformat(),
        "preregistration": "2026-07-12_d5_d9_transition_onset_preregistration.md (§14 봉인)",
        "days_measured": days_measured,
        "consolidate": dict(consolidate_meta),
        "reproduction_gate": dict(repro),
        "overlap": dict(overlap_result),
    }
