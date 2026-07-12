"""F2 화이트리스트 게이트 + §6 P3 재현 게이트 — 효과 관측 전 1회 실행.

사전등록 §4·§13-F2: 측정 시작 전 각 U-보류 절의 로컬 정의식을 원문 그대로
재현해 스팟 패리티(표본 1,000행, 원문 로컬 수식 대비 오차 0) 통과 시 M 편입,
실패 절만 U 제외. 순수 중복(#15≡#39)은 게이트 단계에서 1절 병합(§8). FDR 분모 =
게이트 확정 자격 절 수(상한 39 봉인). 이 게이트는 어떤 절의 Δ도 계산하기 전에
1회 실행되어 M/U 를 확정하고 그 분할을 기록한 뒤 변경하지 않는다.

§6 P3: 표본 온셋 100건에서 벡터 절 값 vs 엔진 exec(스칼라 per-온셋) 경로 절 값
동시 일치율 100%(재현 게이트 정신) — 벡터 술어 전사 오류를 차단.

원본 tick DB read-only. 엔진 백테 0회.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from alpha_lab.clause_lab.clauses import (
    CLAUSE_SPECS,
    LOCAL_DEF_SPECS,
    NAMESPACE_SYMBOLS,
    PURE_DUPLICATE_PAIRS,
    RAW_EXPR,
    ClauseSpec,
    evaluate_clause_bits,
)
from alpha_lab.clause_lab.onset_features import build_onset_namespace, load_window_frame
from alpha_lab.dataset.reader import connect_ro
from alpha_lab.dataset.schema import as_float

logger = logging.getLogger(__name__)

__all__ = [
    "P3_SAMPLE",
    "PARITY_SAMPLE",
    "determine_qualified_set",
    "local_def_parity",
    "n1_delay_parity",
    "p3_reproduction_gate",
    "run_f2_gate",
    "sample_onset_namespace",
]

PARITY_SAMPLE = 1000     # §13-F2 로컬 정의 스팟 표본 행수.
P3_SAMPLE = 100          # §6 P3 재현 게이트 온셋 표본수.

# U-보류 6절과 그 근거 심볼(로컬 정의/지연). §3.1.
U_HOLD_NUMS: Tuple[int, ...] = (10, 12, 13, 19, 20, 36)
# U-보류 절 → 승격에 필요한 심볼(패리티 대상).
U_SYMBOL_OF: Dict[int, str] = {
    10: "VI아래5호가", 12: "시가등락율", 13: "시가대비등락율",
    19: "시가등락율", 20: "시가대비등락율", 36: "초당거래대금N1",
}


def _scalar_open_change(현재가: float, 시가: float, 등락율: float) -> float:
    """시가등락율 원문 로컬 수식 스칼라 참조(전일종가 경유)."""
    전일종가 = 현재가 / (1 + (등락율 / 100))
    return ((시가 - 전일종가) / 전일종가) * 100


def _scalar_open_vs(현재가: float, 시가: float) -> float:
    return ((현재가 - 시가) / 시가) * 100


def _scalar_vi_below5(vi가격: float, vi호가단위: float) -> float:
    return vi가격 - vi호가단위 * 5


def local_def_parity(
    rows: Mapping[str, np.ndarray], sample: int = PARITY_SAMPLE,
) -> Dict[str, Dict[str, object]]:
    """저장-컬럼 표본 행에서 로컬 정의 재현식 vs 원문 스칼라 수식 최대 절대오차.

    시가등락율·시가대비등락율·VI아래5호가 3종(U-보류 #10/#12/#13/#19/#20 근거).
    벡터(build_local_definitions 경로)와 per-row 원문 수식이 원소 동일(오차 0)이면 통과.
    """
    n = int(min(sample, rows["현재가"].shape[0]))
    ns: Dict[str, np.ndarray] = {k: np.asarray(v[:n], dtype=np.float64)
                                 for k, v in rows.items()}
    from alpha_lab.clause_lab.clauses import build_local_definitions
    build_local_definitions(ns)

    out: Dict[str, Dict[str, object]] = {}
    with np.errstate(divide="ignore", invalid="ignore"):
        refs = {
            "시가등락율": np.array([
                _scalar_open_change(float(ns["현재가"][i]), float(ns["시가"][i]),
                                    float(ns["등락율"][i])) for i in range(n)]),
            "시가대비등락율": np.array([
                _scalar_open_vs(float(ns["현재가"][i]), float(ns["시가"][i]))
                for i in range(n)]),
            "VI아래5호가": np.array([
                _scalar_vi_below5(float(ns["VI가격"][i]), float(ns["VI호가단위"][i]))
                for i in range(n)]),
        }
    for name, ref in refs.items():
        vec = ns[name]
        finite = np.isfinite(ref) & np.isfinite(vec)
        max_err = (float(np.max(np.abs(vec[finite] - ref[finite])))
                   if finite.any() else 0.0)
        out[name] = {
            "n": n, "max_abs_err": max_err,
            "n_nonfinite": int((~finite).sum()),
            "pass": bool(max_err == 0.0),
        }
    return out


def n1_delay_parity(
    idx: np.ndarray, df, sample: int = PARITY_SAMPLE,
) -> Dict[str, object]:
    """초당거래대금N(1) 지연 재현 패리티 — 벡터 shift-1 vs per-row 직전 관측 행.

    엔진 _Parameter_Previous(초당거래대금, 1) = arry_code[indexn-1] 미러. 표본은
    창의 앞쪽 sample 행(첫 행 0 규약 포함).
    """
    amt = df["초당거래대금"].to_numpy(dtype=np.float64)
    n = int(min(sample, amt.shape[0]))
    vec = np.where(np.arange(n) >= 1, amt[np.clip(np.arange(n) - 1, 0, amt.size - 1)], 0.0)
    ref = np.array([amt[i - 1] if i >= 1 else 0.0 for i in range(n)])
    max_err = float(np.max(np.abs(vec - ref))) if n else 0.0
    return {"symbol": "초당거래대금N1", "n": n, "max_abs_err": max_err,
            "pass": bool(max_err == 0.0)}


def _scalar_namespace(ns: Mapping[str, np.ndarray], i: int) -> Dict[str, object]:
    """온셋 i 의 스칼라 네임스페이스(엔진 exec 미러) — 심볼 스칼라 + 파생 함수 클로저."""
    g: Dict[str, object] = {s: float(ns[s][i]) for s in NAMESPACE_SYMBOLS}
    ang = float(ns["당일거래대금각도30"][i])
    avg = float(ns["초당거래대금평균30"][i])
    cum_b = float(ns["누적초당매수수량30"][i])
    cum_s = float(ns["누적초당매도수량30"][i])
    n1 = float(ns["초당거래대금N1"][i])
    g["당일거래대금각도"] = lambda tick, pre=0: ang
    g["초당거래대금평균"] = lambda tick, pre=0: avg
    g["누적초당매수수량"] = lambda tick, pre=0: cum_b
    g["누적초당매도수량"] = lambda tick, pre=0: cum_s
    g["초당거래대금N"] = lambda pre: n1
    return g


def p3_reproduction_gate(
    ns: Mapping[str, np.ndarray], specs: Sequence[ClauseSpec] = CLAUSE_SPECS,
    sample: int = P3_SAMPLE, seed: int = 20260712,
) -> Dict[str, object]:
    """벡터 절 값 vs 스칼라 exec(RAW_EXPR) 절 값 100% 일치 검정(§6 P3).

    스칼라 경로는 원문 술어식을 온셋별로 eval 한다(엔진 exec 미러). 분모 0(#34/#35)은
    ZeroDivisionError → False(단독 술어 denom<=0 정책, 벡터 _ratio_gt 와 동일).
    """
    total = int(ns["현재가"].shape[0])
    n = int(min(sample, total))
    rng = np.random.default_rng(seed)
    sel = np.sort(rng.choice(total, size=n, replace=False)) if total > n else np.arange(total)
    bits = evaluate_clause_bits(ns, specs)
    per_clause: Dict[int, int] = {s.num: 0 for s in specs}
    mism: List[dict] = []
    for i in sel.tolist():
        g = _scalar_namespace(ns, i)
        for spec in specs:
            try:
                ref = bool(eval(RAW_EXPR[spec.num], {"__builtins__": {}}, g))
            except ZeroDivisionError:
                ref = False
            vec = bool(bits[spec.num][i])
            if ref == vec:
                per_clause[spec.num] += 1
            elif len(mism) < 20:
                mism.append({"onset_row": int(i), "clause": spec.num,
                             "raw": RAW_EXPR[spec.num], "vec": vec, "scalar": ref})
    n_eval = len(sel)
    agree = sum(per_clause.values())
    n_pairs = n_eval * len(specs)
    return {
        "n_onsets": n_eval, "n_clauses": len(specs), "n_pairs": n_pairs,
        "n_agree": agree, "agreement_pct": (100.0 * agree / n_pairs) if n_pairs else 0.0,
        "n_mismatch": n_pairs - agree,
        "per_clause_agree": per_clause,
        "mismatches": mism,
        "pass": bool(n_pairs > 0 and agree == n_pairs),
    }


def determine_qualified_set(
    local_parity: Mapping[str, Dict[str, object]],
    n1_parity: Mapping[str, object],
) -> Dict[str, object]:
    """M/U 확정 + 순수 중복 병합 → 자격 절 집합·FDR 분모(상한 39 봉인).

    U-보류 절은 근거 심볼 패리티(오차 0) 통과 시 M 승격. #15≡#39 순수 중복은 1절 병합
    (분모 중복 계상 금지, §8). 자격 = M(승격 포함) − 병합 중복.
    """
    sym_pass: Dict[str, bool] = {
        name: bool(res["pass"]) for name, res in local_parity.items()
    }
    sym_pass["초당거래대금N1"] = bool(n1_parity["pass"])

    promoted, held = [], []
    for num in U_HOLD_NUMS:
        symbol = U_SYMBOL_OF[num]
        (promoted if sym_pass.get(symbol, False) else held).append(num)

    # 기본 M(비 U-보류) = 33절, U 승격분 추가.
    base_m = [s.num for s in CLAUSE_SPECS if s.num not in U_HOLD_NUMS]
    qualified = sorted(set(base_m) | set(promoted))

    # 순수 중복 병합: 각 쌍에서 대표(작은 #)만 남기고 짝은 분모에서 제거.
    merged_out: List[int] = []
    for a, b in PURE_DUPLICATE_PAIRS:
        if a in qualified and b in qualified:
            qualified.remove(b)
            merged_out.append(b)

    return {
        "qualified_nums": qualified,
        "n_qualified": len(qualified),
        "fdr_denominator": len(qualified),
        "sealed_cap": 39,
        "u_promoted": promoted,
        "u_held_excluded": held,
        "pure_dup_merged_out": merged_out,
        "pure_dup_pairs": [list(p) for p in PURE_DUPLICATE_PAIRS],
        "symbol_parity_pass": sym_pass,
        "base_m_count": len(base_m),
    }


def _sample_window_rows(
    db_dir, days: Sequence[str], n_rows: int,
) -> Dict[str, np.ndarray]:
    """앞쪽 일들의 창에서 저장-컬럼 표본 행 n_rows 개를 모은다(로컬 정의 패리티용)."""
    from alpha_lab.clause_lab.onset_features import STORED_CLAUSE_COLUMNS
    acc: Dict[str, List[float]] = {c: [] for c in STORED_CLAUSE_COLUMNS}
    got = 0
    for day in days:
        if got >= n_rows:
            break
        path = Path(db_dir) / f"stock_tick_{day}.db"
        conn = connect_ro(path)
        try:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            codes = [c for (c,) in cur if c.isdigit() and len(c) == 6]
            for code in codes:
                loaded = load_window_frame(conn, code, int(day))
                if loaded is None:
                    continue
                _idx, df = loaded
                take = min(len(df), n_rows - got)
                for c in STORED_CLAUSE_COLUMNS:
                    col = df[c].to_numpy() if c in df.columns else [None] * len(df)
                    acc[c].extend(as_float(v) for v in col[:take])
                got += take
                if got >= n_rows:
                    break
        finally:
            conn.close()
    return {c: np.asarray(v, dtype=np.float64) for c, v in acc.items()}


def sample_onset_namespace(
    db_dir, days: Sequence[str], min_onsets: int,
) -> Tuple[Dict[str, np.ndarray], Optional[Tuple[np.ndarray, object]]]:
    """앞쪽 일들에서 온셋 네임스페이스(≥min_onsets)와 N1 패리티용 창 1개를 모은다.

    P3 재현 게이트·N1 지연 패리티 표본용. 봉인 온셋 경로(pilot_v2._onset_offsets) 재사용.
    """
    from collections import defaultdict

    from alpha_lab.clause_lab.clauses import NAMESPACE_SYMBOLS
    from alpha_lab.stats_map import extract, pilot_v2

    acc = defaultdict(list)
    got = 0
    first_window: Optional[Tuple[np.ndarray, object]] = None
    for day in days:
        if got >= min_onsets:
            break
        path = Path(db_dir) / f"stock_tick_{day}.db"
        conn = connect_ro(path)
        try:
            uni = extract._moneytop_by_code(conn)
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            codes = [c for (c,) in cur if c.isdigit() and len(c) == 6]
            for code in codes:
                dense = extract._load_dense(conn, code)
                if dense is None:
                    continue
                oo = pilot_v2._onset_offsets(dense, uni.get(code, np.empty(0, np.int64)))
                if oo.size == 0:
                    continue
                t0i = [pilot_v2._offset_to_index(int(day), int(o)) for o in oo]
                loaded = load_window_frame(conn, code, int(day))
                if loaded is None:
                    continue
                idx, df = loaded
                if first_window is None:
                    first_window = (idx, df)
                ns = build_onset_namespace(idx, df, t0i)
                for k in NAMESPACE_SYMBOLS:
                    acc[k].append(ns[k])
                got += oo.size
                if got >= min_onsets:
                    break
        finally:
            conn.close()
    return {k: np.concatenate(v) for k, v in acc.items()}, first_window


def run_f2_gate(
    db_dir, days: Sequence[str], *, parity_sample: int = PARITY_SAMPLE,
    p3_sample: int = P3_SAMPLE,
) -> Dict[str, object]:
    """F2 화이트리스트 게이트 1회 실행 → M/U 확정·자격 절 수·패리티·P3 리포트.

    효과 관측 전 실행. days 는 앞쪽 표본 일(패리티·P3 표본 추출용, L3 미접촉).
    """
    rows = _sample_window_rows(db_dir, days, parity_sample)
    local_par = local_def_parity(rows, sample=parity_sample)
    onset_ns, window = sample_onset_namespace(db_dir, days, max(p3_sample, 300))
    if window is None:
        raise RuntimeError("N1 패리티용 창 표본 없음")
    idx, df = window
    n1_par = n1_delay_parity(idx, df, sample=parity_sample)
    p3 = p3_reproduction_gate(onset_ns, sample=p3_sample)
    qualified = determine_qualified_set(local_par, n1_par)
    return {
        "gate_kind": "d1_f2_whitelist",
        "sample_days": list(days),
        "local_def_parity": local_par,
        "n1_delay_parity": n1_par,
        "p3_reproduction": {k: p3[k] for k in (
            "n_onsets", "n_clauses", "n_pairs", "n_agree", "agreement_pct",
            "n_mismatch", "pass")},
        "p3_mismatches": p3["mismatches"],
        "qualified": qualified,
        "gate_pass": bool(
            all(v["pass"] for v in local_par.values())
            and n1_par["pass"] and p3["pass"]),
    }
