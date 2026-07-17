"""셀 통계 + 상관행렬 — 사전등록 §4 라벨(필수 8종+보조) 산출.

전 표본 배열(builder가 일별 추출을 이어붙인 것)에 셀 마스크를 씌워 계산한다.
CI는 stats_common.day_block_bootstrap(일블록, mean, n_boot 400)을 재사용한다
(중복 구현 금지). 상관행렬은 스피어만(순위 피어슨) + IC(변수 vs net 순위상관).
"""
from __future__ import annotations

import hashlib
from itertools import combinations
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from alpha_lab.stats_common import day_block_bootstrap
from alpha_lab.stats_map import config

# corr 계산 상한(결정론 스트라이드 서브샘플 — 게이트 아님, 속도 방어).
_CORR_CAP = 500_000


def cell_stats(net: np.ndarray, day_ids: np.ndarray, cell_cand: np.ndarray,
               valid: np.ndarray, censored: np.ndarray, year: np.ndarray,
               mfe: np.ndarray, mae: np.ndarray, *, seed: int,
               insufficient: bool) -> Dict[str, object]:
    """한 셀·지평의 라벨 8종+보조 dict. cell_cand=셀 소속 후보(절단 포함)."""
    used = cell_cand & valid
    vals = net[used].astype(np.float64)
    row: Dict[str, object] = {
        "n": int(vals.size),
        "n_candidates": int(cell_cand.sum()),
        "censor_rate": _safe_rate(int((cell_cand & censored).sum()),
                                  int(cell_cand.sum())),
        "insufficient": int(insufficient),
    }
    row.update(_distribution(vals))
    row.update(_bootstrap_ci(net, day_ids, used, seed))
    row.update(_year_signs(vals, year[used]))
    row.update(_winrate_payoff(vals))
    row["mfe_mean"] = _finite_mean(mfe[used])
    row["mae_mean"] = _finite_mean(mae[used])
    return row


def _safe_rate(num: int, den: int) -> Optional[float]:
    return float(num) / float(den) if den > 0 else None


def _distribution(vals: np.ndarray) -> Dict[str, object]:
    """P(net≥0)·P(net≥+1%)·mean·median·q25·q75(빈 셀은 None)."""
    if vals.size == 0:
        keys = ("p_net_ge0", "p_net_ge1", "mean_net", "median_net",
                "q25_net", "q75_net")
        return {k: None for k in keys}
    q25, med, q75 = np.percentile(vals, [25, 50, 75])
    return {
        "p_net_ge0": float(np.mean(vals >= config.PROB_THRESHOLDS[0])),
        "p_net_ge1": float(np.mean(vals >= config.PROB_THRESHOLDS[1])),
        "mean_net": float(np.mean(vals)),
        "median_net": float(med), "q25_net": float(q25), "q75_net": float(q75),
    }


def _bootstrap_ci(net: np.ndarray, day_ids: np.ndarray, used: np.ndarray,
                  seed: int) -> Dict[str, Optional[float]]:
    """일블록 부트스트랩 mean CI(표본 없으면 None)."""
    if not used.any():
        return {"ci_low": None, "ci_high": None}
    out = day_block_bootstrap(
        day_ids, np.nan_to_num(net), used,
        n_boot=config.N_BOOT, seed=seed, stat="mean",
    )
    return {"ci_low": _finite(out["ci_low"]), "ci_high": _finite(out["ci_high"])}


def _year_signs(vals: np.ndarray, years: np.ndarray) -> Dict[str, object]:
    """연도별(2022/2023) mean_net과 부호 — 해당 연도 표본 없으면 None."""
    out: Dict[str, object] = {}
    for yr in (2022, 2023):
        sub = vals[years == yr]
        if sub.size:
            mean = float(np.mean(sub))
            out[f"year{yr}_mean"] = mean
            out[f"year{yr}_sign"] = int(np.sign(mean))
        else:
            out[f"year{yr}_mean"] = None
            out[f"year{yr}_sign"] = None
    return out


def _winrate_payoff(vals: np.ndarray) -> Dict[str, Optional[float]]:
    """승률(net>0)·손익비(평균이익/평균손실 절댓값) — 분해 보조 지표."""
    if vals.size == 0:
        return {"winrate": None, "payoff": None}
    wins = vals[vals > 0.0]
    losses = vals[vals < 0.0]
    payoff = None
    if wins.size and losses.size:
        payoff = float(np.mean(wins) / abs(np.mean(losses)))
    return {"winrate": float(wins.size) / float(vals.size), "payoff": payoff}


def _finite_mean(arr: np.ndarray) -> Optional[float]:
    finite = arr[np.isfinite(arr)]
    return float(np.mean(finite)) if finite.size else None


def _finite(value: float) -> Optional[float]:
    return float(value) if np.isfinite(value) else None


def spearman(x: np.ndarray, y: np.ndarray) -> Optional[float]:
    """스피어만 순위상관(공통 유한 표본) — 표본<3이면 None."""
    mask = np.isfinite(x) & np.isfinite(y)
    if int(mask.sum()) < 3:
        return None
    rx = pd.Series(x[mask]).rank().to_numpy()
    ry = pd.Series(y[mask]).rank().to_numpy()
    if rx.std() == 0.0 or ry.std() == 0.0:
        return None
    return float(np.corrcoef(rx, ry)[0, 1])


def corr_rows(sample: Dict[str, np.ndarray]) -> List[Dict[str, object]]:
    """corr_matrix 행 목록 — 변수쌍 스피어만 + 변수별 IC(vs net 지평별)."""
    idx = _corr_subsample(sample["off"].size)
    varv = {v: sample[v][idx].astype(np.float64) for v in config.CORR_VARS}
    rows: List[Dict[str, object]] = []
    for a, b in combinations(config.CORR_VARS, 2):
        rows.append(_corr_row("var_var", a, b, spearman(varv[a], varv[b]),
                              varv[a], varv[b]))
    for h in config.HORIZONS:
        net = np.where(sample[f"valid_{h}"][idx], sample[f"net_{h}"][idx], np.nan)
        for v in config.CORR_VARS:
            rows.append(_corr_row("ic", v, f"net_{h}", spearman(varv[v], net),
                                  varv[v], net))
    return rows


def _corr_row(kind, a, b, value, xa, xb) -> Dict[str, object]:
    mask = np.isfinite(xa) & np.isfinite(xb)
    return {"kind": kind, "var1": a, "var2": b,
            "value": value, "n": int(mask.sum())}


def _corr_subsample(size: int) -> np.ndarray:
    """corr 계산 대상 인덱스(상한 초과 시 결정론 스트라이드)."""
    if size <= _CORR_CAP:
        return np.arange(size)
    step = int(np.ceil(size / _CORR_CAP))
    return np.arange(0, size, step)


def cell_seed(*keys: object) -> int:
    """셀 키 → 결정론 부트스트랩 시드(BUILD_SEED에 셀 지문 결합)."""
    blob = ("|".join(str(k) for k in keys)).encode("utf-8")
    digest = int(hashlib.sha256(blob).hexdigest()[:8], 16)
    return (config.BUILD_SEED + digest) % (2**32)
