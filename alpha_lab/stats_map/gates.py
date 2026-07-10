"""W4-2a 품질 게이트 — 재현성·sanity·절단 계단·비용식 패리티.

각 게이트는 {passed, ...근거수치} dict를 돌려준다(사전등록 §6 파일럿 게이트).
실패는 예외가 아니라 passed=False로 정직 공시한다 — 확장 여부 판단은 호출측.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from alpha_lab.stats_map import builder, config, costs, extract, schema

# sanity 허용대(기존 그리드 평균 ≈ -1.0% 부호·규모 정합).
_SANITY_LOW, _SANITY_HIGH = -0.02, -0.003
# 절단 계단: 09:25 이전 버킷 censor는 이 값 이하여야 0 계단으로 본다.
_STEP_EPS = 1e-9
# 절단 overall 대조(프로파일링 실측 %)와 허용 오차(pp).
_TRUNC_REF = {60: 3.36, 180: 10.26, 300: 17.15}
_TRUNC_TOL = 2.0


def gate_reproducibility(sample: Dict[str, np.ndarray], first_sha: str,
                         reextract: Optional[Dict[str, object]] = None
                         ) -> Dict[str, object]:
    """동일 표본 재조립 sha가 최초 빌드 sha와 동일 + (선택) 재추출 배열 동일.

    first_sha = build_pilot이 낸 최초 빌드의 summary_sha(=빌드 1). 여기서
    같은 표본으로 다시 조립해(빌드 2) sha를 비교한다 — "동일 창 2회 빌드".
    """
    sha2 = _sha(builder.build_all(sample))
    result: Dict[str, object] = {
        "sha_build_1": first_sha, "sha_build_2": sha2,
        "sha_match": first_sha == sha2,
    }
    if reextract is not None:
        result["extract_match"] = _reextract_match(reextract)
    else:
        result["extract_match"] = None
    result["passed"] = bool(result["sha_match"]) and \
        (result["extract_match"] in (None, True))
    return result


def _sha(built: Dict[str, object]) -> str:
    return schema.summary_sha(built["cells"], built["corr"])  # type: ignore[index]


def _reextract_match(spec: Dict[str, object]) -> bool:
    """한 일자를 새로 추출해 캐시 npz와 배열 원소까지 동일한지 확인."""
    fresh = extract.extract_day(spec["db_path"], spec["date"])  # type: ignore[index]
    with np.load(Path(spec["npz_path"])) as cached:  # type: ignore[index]
        if set(cached.files) != set(fresh.keys()):
            return False
        return all(np.array_equal(cached[k], fresh[k], equal_nan=True)
                   for k in fresh)


def gate_sanity(sample: Dict[str, np.ndarray]) -> Dict[str, object]:
    """L0 전체 mean_net(h300)이 음수이고 규모(≈ -1%)가 정합인지."""
    valid = sample["valid_300"]
    mean_net = float(np.nanmean(sample["net_300"][valid]))
    passed = _SANITY_LOW <= mean_net <= _SANITY_HIGH
    return {
        "l0_mean_net_h300": mean_net, "n": int(valid.sum()),
        "expected_band": [_SANITY_LOW, _SANITY_HIGH], "passed": passed,
    }


def gate_censor(cell_rows_l0: List[Dict[str, object]]) -> Dict[str, object]:
    """절단율이 규약 계단인지 — 09:25 이전 버킷 0, overall 프로파일링 정합."""
    two_axis = [r for r in cell_rows_l0
                if r["axis_set"] == config.AXIS_TIME_UD]
    early_max = _early_bucket_max_censor(two_axis)
    overall = _overall_censor(two_axis)
    ref_ok = all(abs(overall[h] - _TRUNC_REF[h]) <= _TRUNC_TOL
                 for h in config.HORIZONS)
    step_ok = early_max <= _STEP_EPS
    return {
        "early_bucket_max_censor": early_max, "overall_censor_pct": overall,
        "profiling_ref_pct": _TRUNC_REF, "step_ok": step_ok,
        "ref_ok": ref_ok, "passed": bool(step_ok and ref_ok),
    }


def _early_bucket_max_censor(rows: List[Dict[str, object]]) -> float:
    """09:25 이전 버킷(900-920)의 최대 censor_rate — 계단이면 0."""
    vals = [r["censor_rate"] for r in rows
            if r["time_label"] < 925 and r["censor_rate"] is not None]
    return float(max(vals)) if vals else 0.0


def _overall_censor(rows: List[Dict[str, object]]) -> Dict[int, float]:
    """지평별 전체 censor_rate(%) — 후보 가중 합산."""
    out: Dict[int, float] = {}
    for h in config.HORIZONS:
        hr = [r for r in rows if r["h"] == h]
        cand = sum(r["n_candidates"] for r in hr)
        cens = sum((r["censor_rate"] or 0.0) * r["n_candidates"] for r in hr)
        out[h] = round(100.0 * cens / cand, 2) if cand else 0.0
    return out


def gate_cost_parity(db_path, date: str, n: int = 1000) -> Dict[str, object]:
    """실 호가쌍 n행에서 벡터식 vs labels.py max_err(0이면 완전 정합)."""
    entry, exit_ = _sample_quote_pairs(db_path, date, n)
    max_err = costs.parity_max_err(entry, exit_)
    return {"n_pairs": int(entry.size), "max_err": max_err,
            "passed": max_err == 0.0}


def _sample_quote_pairs(db_path, date: str, n: int):
    """일 DB에서 실 (entry 매도호가1, exit 매수호가1) 쌍 n개(결정론)."""
    conn = extract.connect_ro(Path(db_path))
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        codes = [c for (c,) in cur if c.isdigit() and len(c) == 6]
        entry: List[float] = []
        exit_: List[float] = []
        for code in codes:
            dense = extract._load_dense(conn, code)
            if dense is None:
                continue
            _collect_pairs(dense, entry, exit_)
            if len(entry) >= n:
                break
    finally:
        conn.close()
    return np.asarray(entry[:n]), np.asarray(exit_[:n])


def _collect_pairs(dense, entry: List[float], exit_: List[float]) -> None:
    """한 종목 dense에서 entry(t0+1)·exit(t0+300) 유효 호가쌍을 모은다."""
    present, ask, bid = dense["present"], dense["매도호가1"], dense["매수호가1"]
    for off in range(config.GRID_START_OFFSET, config.WINDOW_SECONDS - 300):
        ex = off + 300
        if present[off + 1] and ask[off + 1] > 0 and present[ex] and bid[ex] > 0:
            entry.append(ask[off + 1])
            exit_.append(bid[ex])
