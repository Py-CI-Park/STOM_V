"""V2-C 챔피언 칸 게이트 v2 — family vote(감사 §8.3 채택).

봉인: S-트랙 사전등록 V2-A §4. v1 챔피언 게이트(champion.py, 0/4 point 비교)를
다음으로 교체한다:
  - **family vote**: RR8 가문(RR8_0·21·12 합집합, 상관 0.84~0.93이므로 1표,
    내부 3전략 민감도 병기) + GPTAUTH 가문(1표).
  - **라벨**: L3_replay(교정판 — 새 경계·연도 세율). 대조군으로 h300도 병기.
  - **판정량**: 가문 점유 칸의 라벨 mean − 전체 L1 라벨 mean(개선폭).
  - **통과**: 개선폭 ≥ +0.10%p ∧ 일자 블록 부트스트랩(n_boot 400) CI 하한 > 0.
  - **약신호 대역**: +0.05~0.10%p ∧ CI>0(통과 아님, 보고만).

칸 사상은 v1 파이프라인(champion.load_champion_trades — 진입 매수시간 −1초를
t0 오프셋으로, B_등락율/B_시가총액 스냅샷 버킷화, 사상 오차 0 검증됨)을 재사용하되
등락율 버킷만 v2 경계(pilot_v2.updown_quartile_v2)로 교체한다. 점유 판정은 온셋
멤버십(합집합) 기준이며(부트스트랩 가능), v1식 거래가중 점유 EV는 민감도로 병기한다.

원본 read-only. 엔진 백테 0회.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from alpha_lab.stats_map import champion, config, pilot_v2

# 봉인 게이트 문턱(사전등록 §4).
IMPROVE_PASS = 0.0010      # 개선폭 ≥ +0.10%p.
IMPROVE_WEAK = 0.0005      # 약신호 하한 +0.05%p.
N_BOOT = config.N_BOOT     # 400.

# 라벨별 (net, valid) 컬럼 접근자.
_LABELS = {
    "l3": ("l3_net_pure", "l3_labeled_pure"),
    "h300": ("h300_net", "h300_valid"),
}


# ---------------------------------------------------------------------------
# 챔피언 거래 → v2 칸 사상(v1 파이프라인 재사용, 등락율만 v2 경계).
# ---------------------------------------------------------------------------

def family_trade_cells(csv_paths: Sequence[Path]) -> Dict[str, object]:
    """한 가문의 CSV들 → 점유 칸 좌표(거래수) + 커버리지(v1 사상, v2 등락율).

    반환: {"cells_2axis": {(tb,uq): cnt}, "cells_3axis": {(tb,uq,mc): cnt},
           "n_trades": int, "coverage": {...}}. 여러 CSV는 합집합(가문 vote).
    """
    tb_all: List[int] = []
    uq_all: List[int] = []
    mc_all: List[int] = []
    cov = {"total": 0, "discovery": 0, "in_window_of_discovery": 0,
           "outside_window": 0, "after_discovery": 0}
    for csv_path in csv_paths:
        t = champion.load_champion_trades(csv_path)
        a = t["arrays"]
        # v1 사상 재사용, 등락율 버킷만 v2 경계로 재계산(time_b·mktcap_b는 동일).
        uq_v2 = pilot_v2.updown_quartile_v2(a["updown"])
        tb_all.extend(a["time_b"].tolist())
        uq_all.extend(uq_v2.tolist())
        mc_all.extend(a["mktcap_b"].tolist())
        for k, v in t["coverage"].items():
            cov[k] = cov.get(k, 0) + int(v)
    cells2: Dict[Tuple[int, int], int] = {}
    cells3: Dict[Tuple[int, int, int], int] = {}
    for tb, uq, mc in zip(tb_all, uq_all, mc_all):
        cells2[(tb, uq)] = cells2.get((tb, uq), 0) + 1
        cells3[(tb, uq, mc)] = cells3.get((tb, uq, mc), 0) + 1
    return {"cells_2axis": cells2, "cells_3axis": cells3,
            "n_trades": len(tb_all), "coverage": cov}


# ---------------------------------------------------------------------------
# 개선폭 + 일자 블록 부트스트랩 CI.
# ---------------------------------------------------------------------------

def _improvement_ci(day: np.ndarray, net: np.ndarray, occ_mask: np.ndarray,
                    all_mask: np.ndarray, *, seed: int, n_boot: int = N_BOOT
                    ) -> Dict[str, object]:
    """개선폭(점유 mean − 전체 mean) + 일자 블록 부트스트랩 CI(비율의 합 벡터화).

    occ_mask ⊆ all_mask 가정. 점유/전체 각 일별 (Σnet, cnt)를 만든 뒤 일 인덱스를
    복원 재표집해 두 평균의 차를 재계산한다(일중 상관 보존).
    """
    _, inv = np.unique(day, return_inverse=True)
    n_days = int(inv.max()) + 1 if inv.size else 0
    net = np.nan_to_num(np.asarray(net, dtype=np.float64))
    occ_w = occ_mask.astype(np.float64)
    all_w = all_mask.astype(np.float64)
    occ_sum = np.bincount(inv, weights=net * occ_w, minlength=n_days)
    occ_cnt = np.bincount(inv, weights=occ_w, minlength=n_days)
    all_sum = np.bincount(inv, weights=net * all_w, minlength=n_days)
    all_cnt = np.bincount(inv, weights=all_w, minlength=n_days)

    def diff(os_, oc_, as_, ac_):
        with np.errstate(divide="ignore", invalid="ignore"):
            return (os_ / oc_) - (as_ / ac_)

    occ_mean = float(occ_sum.sum() / occ_cnt.sum()) if occ_cnt.sum() else float("nan")
    all_mean = float(all_sum.sum() / all_cnt.sum()) if all_cnt.sum() else float("nan")
    point = occ_mean - all_mean
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n_days, size=(n_boot, n_days)) if n_days else None
    if idx is None:
        return {"occ_mean": None, "all_mean": None, "improvement": None,
                "ci_low": None, "ci_high": None, "n_occ": 0}
    reps = diff(occ_sum[idx].sum(1), occ_cnt[idx].sum(1),
                all_sum[idx].sum(1), all_cnt[idx].sum(1))
    reps = reps[np.isfinite(reps)]
    ci_low = float(np.percentile(reps, 2.5)) if reps.size else None
    ci_high = float(np.percentile(reps, 97.5)) if reps.size else None
    return {"occ_mean": occ_mean, "all_mean": all_mean, "improvement": point,
            "ci_low": ci_low, "ci_high": ci_high, "n_occ": int(occ_mask.sum())}


def _occ_mask(sample: Mapping[str, np.ndarray], occupied: set, axis: str
              ) -> np.ndarray:
    """온셋별 점유 칸 소속 여부(2축=시간대·등락율, 3축=+시총)."""
    tb, uq = sample["time_b"], sample["updown_q"]
    if axis == "time_ud":
        keys = list(zip(tb.tolist(), uq.tolist()))
    else:
        mc = sample["mktcap_b"]
        keys = list(zip(tb.tolist(), uq.tolist(), mc.tolist()))
    return np.array([k in occupied for k in keys], dtype=bool)


def _trade_weighted_ev(sample, cells_cnt, label: str, axis: str
                       ) -> Optional[float]:
    """v1식 거래가중 점유 EV(민감도 병기) — Σ(칸 mean × 거래수)/Σ거래수."""
    net_key, valid_key = _LABELS[label]
    net, valid = sample[net_key], sample[valid_key]
    tb, uq = sample["time_b"], sample["updown_q"]
    mc = sample["mktcap_b"]
    num = den = 0.0
    for key, cnt in cells_cnt.items():
        if axis == "time_ud":
            m = (tb == key[0]) & (uq == key[1]) & valid
        else:
            m = (tb == key[0]) & (uq == key[1]) & (mc == key[2]) & valid
        vals = net[m]
        if vals.size:
            num += float(vals.mean()) * cnt
            den += cnt
    return (num / den) if den > 0 else None


def occupied_judgment(sample: Mapping[str, np.ndarray], trade_cells: Dict,
                      *, label: str, axis: str, seed: int) -> Dict[str, object]:
    """한 라벨·축의 점유 판정(개선폭·CI·거래가중 민감도·커버리지)."""
    net_key, valid_key = _LABELS[label]
    valid = sample[valid_key].astype(bool)
    cells_cnt = trade_cells["cells_2axis" if axis == "time_ud" else "cells_3axis"]
    occupied = set(cells_cnt)
    occ = _occ_mask(sample, occupied, axis) & valid
    stat = _improvement_ci(sample["day"], sample[net_key], occ, valid, seed=seed)
    covered = sum(c for k, c in cells_cnt.items()
                  if _cell_has_onsets(sample, k, axis, valid))
    stat.update({
        "label": label, "axis": axis,
        "n_occupied_cells": len(occupied),
        "trade_weighted_ev": _trade_weighted_ev(sample, cells_cnt, label, axis),
        "trades_total": trade_cells["n_trades"],
        "trades_in_judged_cells": int(covered),
    })
    return stat


def _cell_has_onsets(sample, key, axis, valid) -> bool:
    tb, uq = sample["time_b"], sample["updown_q"]
    if axis == "time_ud":
        m = (tb == key[0]) & (uq == key[1]) & valid
    else:
        m = (tb == key[0]) & (uq == key[1]) & (sample["mktcap_b"] == key[2]) & valid
    return bool(m.any())


# ---------------------------------------------------------------------------
# 가문 게이트 + 해석 사다리.
# ---------------------------------------------------------------------------

def _verdict(improvement: Optional[float], ci_low: Optional[float]) -> str:
    """개선폭·CI 하한 → 판정(pass/weak/fail)."""
    if improvement is None or ci_low is None:
        return "fail"
    if ci_low > 0.0 and improvement >= IMPROVE_PASS:
        return "pass"
    if ci_low > 0.0 and improvement >= IMPROVE_WEAK:
        return "weak"
    return "fail"


def run_family_gate(sample: Mapping[str, np.ndarray], name: str,
                    csv_paths: Sequence[Path], *, seed: int) -> Dict[str, object]:
    """한 가문의 게이트 — L3(주판정, 2축) + 대조군 h300 + 3축 민감도."""
    trade_cells = family_trade_cells(csv_paths)
    l3_2 = occupied_judgment(sample, trade_cells, label="l3", axis="time_ud",
                             seed=seed)
    l3_3 = occupied_judgment(sample, trade_cells, label="l3", axis="time_mc_ud",
                             seed=seed + 1)
    h300_2 = occupied_judgment(sample, trade_cells, label="h300", axis="time_ud",
                               seed=seed + 2)
    verdict = _verdict(l3_2["improvement"], l3_2["ci_low"])
    return {
        "family": name, "coverage": trade_cells["coverage"],
        "n_trades_mapped": trade_cells["n_trades"],
        "l3_time_ud": l3_2, "l3_time_mc_ud": l3_3, "h300_time_ud": h300_2,
        "verdict": verdict,
        "verdict_h300_control": _verdict(h300_2["improvement"], h300_2["ci_low"]),
    }


def run_gate_v2c(sample: Mapping[str, np.ndarray],
                 families: Mapping[str, Sequence[Path]],
                 rr8_members: Mapping[str, Path], *, seed: int = config.BUILD_SEED
                 ) -> Dict[str, object]:
    """V2-C 전체 — RR8 가문 + GPTAUTH 가문 vote + RR8 내부 3전략 민감도 + 사다리."""
    fam_results = {
        name: run_family_gate(sample, name, paths, seed=seed + 100 * i)
        for i, (name, paths) in enumerate(families.items())
    }
    rr8_sensitivity = {
        member: occupied_judgment(
            sample, family_trade_cells([path]), label="l3", axis="time_ud",
            seed=seed + 500 + j)
        for j, (member, path) in enumerate(rr8_members.items())
    }
    verdicts = {name: r["verdict"] for name, r in fam_results.items()}
    n_pass = sum(1 for v in verdicts.values() if v == "pass")
    ladder = _ladder(verdicts)
    return {
        "n_families": len(fam_results),
        "families": fam_results,
        "rr8_internal_sensitivity_l3_time_ud": rr8_sensitivity,
        "verdicts": verdicts,
        "n_pass": n_pass,
        "interpretation_ladder": ladder,
        "gate_thresholds": {
            "improve_pass_pp": IMPROVE_PASS * 100, "improve_weak_pp": IMPROVE_WEAK * 100,
            "ci": "day_block_bootstrap n_boot=400, ci_low>0", "primary_label": "l3",
            "primary_axis": "time_ud",
        },
    }


def _ladder(verdicts: Mapping[str, str]) -> Dict[str, object]:
    """해석 사다리(사전등록 §4): RR8만=positive control / 양=제한적 일반화 / 0=kill."""
    rr8 = verdicts.get("RR8") == "pass"
    gpt = verdicts.get("GPTAUTH") == "pass"
    if rr8 and gpt:
        pos, msg = "limited_generalization", "제한적 일반화 신호(양 가문 통과)"
    elif rr8:
        pos, msg = "positive_control", "positive control(RR8_12 출구 조건부 지도 작동)"
    elif gpt:
        pos, msg = "gptauth_only", "GPTAUTH만 통과 — RR8 미통과(해석 주의)"
    else:
        pos, msg = "kill", ("0 가문 통과 → 현재 축·서지 온셋·RR8_12 출구 조건부 "
                            "칸-조준 폐기(칸 방법론 전체 폐기 아님, 함정 지도 유지)")
    return {"position": pos, "message": msg,
            "n_pass": sum(1 for v in verdicts.values() if v == "pass")}
