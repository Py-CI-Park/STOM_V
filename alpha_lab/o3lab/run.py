"""O-3 측정 오케스트레이션 — 추출(체크포인트) + 게이트 G1~G4 + 판정 (run.py 미러).

phase:
- extract : 발견창 437일 루프 — 일별 parquet 체크포인트(parts/o3_{date}.parquet +
  meta_{date}.json), 재시작 시 완료 일 건너뜀. 소비 후 consolidate →
  o3_breakout_onset_bank.parquet(bank.write_bank — v2+variant, git 제외).
- gates   : G1 정의 스팟(변형별 100, 원시 행 독립 재계산) · G2 VI 필드 덤프(20) ·
  G3 순수/벡터 재현(스팟 일) · G4 서지 정확일치 L3 bit-identical(서지 은행 대비).
- judge   : 변형×모집단(전체/서지-비중첩 ±30) 단독 EV 판정(judge_all_o3) + 서술
  (겹침·forced_cap·유형간 중복). 자격(분모)은 L3 분포 관측 전 확정.

서지 온셋은 기존 onset_l3_bank.parquet 을 read-only 로만 소비(겹침·G4). 원본 tick DB
read-only(URI mode=ro). 엔진 백테 0회. git 커밋은 메인 세션 몫.
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
from alpha_lab.d9lab import overlap
from alpha_lab.dataset import reader
from alpha_lab.dataset.schema import as_float
from alpha_lab.o3lab import bank, breakouts, detect, judge
from alpha_lab.stats_map import extract

logger = logging.getLogger(__name__)

__all__ = [
    "G1_SPOT_N", "G2_VI_N", "REPRO_MIN", "SURGE_WINDOW",
    "consolidate", "gate_g1_definition", "gate_g2_vi_dump", "gate_g4_bank_anchor",
    "load_bank", "run_extract", "run_judge", "spot_reproduction_check",
    "surge_overlap_flags",
]

_W = extract.config.WINDOW_SECONDS
G1_SPOT_N = 100               # §4 G1 변형별 스팟 수.
G2_VI_N = 20                  # §4 G2 VI 수동 확인 표본 수.
REPRO_MIN = 0.999             # §4 G3 순수/벡터 청산 시각 일치 하한.
SURGE_WINDOW = overlap.PRIMARY_WINDOW   # ±30초(서지-비중첩 판정, F2).


def _log(progress: Path, msg: str) -> None:
    line = f"{datetime.now().isoformat()} {msg}"
    with open(progress, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    logger.info(msg)


# ---------------------------------------------------------------------------
# extract — 일 체크포인트 루프(재시작 가능).
# ---------------------------------------------------------------------------

def run_extract(
    db_dir, run_dir, parts_dir, sell_text: str,
    *, days: Optional[Sequence[Tuple[str, Path]]] = None,
    spot_days: Sequence[str] = (), progress_name: str = "o3_extract_progress.txt",
) -> Dict[str, object]:
    """추출 일 루프 — 일별 돌파 온셋 parquet + meta 체크포인트, 재시작 가능."""
    parts = Path(parts_dir)
    parts.mkdir(parents=True, exist_ok=True)
    progress = Path(run_dir) / progress_name
    spot = set(spot_days)
    day_paths = list(days) if days is not None else day_list(db_dir)
    _log(progress, f"O3-EXTRACT start: {len(day_paths)} days spot={sorted(spot)} parts={parts}")

    t_all = time.monotonic()
    done = 0
    for date, path in day_paths:
        part = parts / f"o3_{date}.parquet"
        meta_p = parts / f"meta_{date}.json"
        if part.exists() and meta_p.exists():
            done += 1
            continue
        t0 = time.monotonic()
        try:
            rec, meta = breakouts.build_day_breakouts(
                path, date, sell_text, spot_pure=(date in spot))
            frame = pd.DataFrame({k: rec[k] for k in rec})
            tmp = parts / f"o3_{date}.tmp.parquet"
            frame.to_parquet(tmp, index=False)
            tmp.replace(part)
            meta_p.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
            done += 1
            pv = meta["per_variant"]
            _log(progress, f"  {date}: onsets={meta['n_onsets']} "
                 + " ".join(f"{v}={pv[v]['n']}" for v in detect.VARIANTS)
                 + f" ({time.monotonic()-t0:.1f}s) [{done}/{len(day_paths)}]")
        except Exception as exc:  # noqa: BLE001 — 정직 신고 후 계속(재시작 가능).
            _log(progress, f"  {date}: ERROR {exc!r}\n{traceback.format_exc()}")
    _log(progress, f"O3-EXTRACT done: {done}/{len(day_paths)} days, {(time.monotonic()-t_all)/60:.1f} min")
    return {"days_done": done, "days_total": len(day_paths)}


def consolidate(parts_dir, bank_path, *, window: Optional[tuple] = None
                ) -> Dict[str, object]:
    """일별 parts → o3_breakout_onset_bank.parquet(bank.write_bank) + 변형별 census."""
    parts = sorted(Path(parts_dir).glob("o3_*.parquet"))
    if not parts:
        raise FileNotFoundError(f"parts 없음: {parts_dir}")
    frames = [pd.read_parquet(p) for p in parts]
    full = pd.concat(frames, ignore_index=True)
    keep = [c for c in breakouts.BREAKOUT_COLUMNS if c in full.columns]
    write_receipt = bank.write_bank(full[keep].copy(), bank_path, window=window)

    variant = full["variant"].to_numpy()
    lab = full["l3_labeled"].to_numpy().astype(bool)
    yr = full["year"].to_numpy()
    census: Dict[str, object] = {}
    for v in detect.VARIANTS:
        m = variant == v
        census[v] = {
            "n_onsets": int(m.sum()), "n_labeled": int((m & lab).sum()),
            "n_2022": int((m & (yr == 2022)).sum()),
            "n_2023": int((m & (yr == 2023)).sum()),
        }
    return {
        "n_parts": len(parts), "n_onsets": int(full.shape[0]),
        "n_labeled": int(lab.sum()), "per_variant": census,
        "bank_write": write_receipt, "bank_path": str(bank_path),
    }


def load_bank(bank_path) -> pd.DataFrame:
    """o3_breakout_onset_bank.parquet 로드(전 컬럼)."""
    return pd.read_parquet(bank_path)


# ---------------------------------------------------------------------------
# 서지 겹침 — 모집단 분리(±30, F2) — d9lab.overlap 재사용.
# ---------------------------------------------------------------------------

def surge_overlap_flags(
    df: pd.DataFrame, surge_bank_path, *, window: int = SURGE_WINDOW,
    restrict_days: Optional[Sequence[int]] = None,
) -> np.ndarray:
    """각 돌파 온셋이 ±window 내 서지 온셋과 겹치는지 bool(_overlap_mask_one_day 재사용).

    restrict_days 지정 시 서지 인덱스를 그 일자로 제한(스모크 관통 — 동일-일 기준).
    """
    surge = overlap._surge_index(surge_bank_path)
    if restrict_days is not None:
        keep = set(int(d) for d in restrict_days)
        surge = {k: v for k, v in surge.items() if k[0] in keep}
    n = df.shape[0]
    flags = np.zeros(n, dtype=bool)
    if n == 0:
        return flags
    code = df["code"].to_numpy()
    day = df["day"].to_numpy()
    off = df["off"].to_numpy().astype(np.int64)
    order = np.lexsort((off, code, day))
    start = 0
    keys = list(zip(day[order], code[order]))
    while start < len(keys):
        end = start
        while end < len(keys) and keys[end] == keys[start]:
            end += 1
        g = order[start:end]
        sg = surge.get((int(day[g[0]]), str(code[g[0]])), np.empty(0, np.int64))
        flags[g] = overlap._overlap_mask_one_day(off[g], sg, window)
        start = end
    return flags


# ---------------------------------------------------------------------------
# G3 재현 — 순수/벡터 청산 시각·net 일치(스팟 일).
# ---------------------------------------------------------------------------

def spot_reproduction_check(parts_dir, spot_days: Sequence[str]) -> Dict[str, object]:
    """스팟 일 순수 vs 벡터 L3 청산 시각·net 일치(§4 G3) — 벡터 경로 허가 근거."""
    out: Dict[str, object] = {"spot_days": list(spot_days), "per_day": []}
    all_pass = True
    for date in spot_days:
        p = Path(parts_dir) / f"o3_{date}.parquet"
        if not p.exists():
            out["per_day"].append({"day": date, "status": "part_missing"})
            all_pass = False
            continue
        d = pd.read_parquet(p)
        if "l3_net_pure" not in d.columns:
            out["per_day"].append({"day": date, "status": "no_pure_columns"})
            all_pass = False
            continue
        both = (d["l3_labeled"].to_numpy().astype(bool)
                & d["l3_labeled_pure"].to_numpy().astype(bool))
        net_v = d["l3_net"].to_numpy(dtype=np.float64)[both]
        net_p = d["l3_net_pure"].to_numpy(dtype=np.float64)[both]
        exit_v = d["l3_exit"].to_numpy(dtype=np.int64)[both]
        exit_p = d["l3_exit_pure"].to_numpy(dtype=np.int64)[both]
        net_err = float(np.max(np.abs(net_v - net_p))) if both.any() else 0.0
        exit_match = float(np.mean(exit_v == exit_p)) if both.any() else 1.0
        day_pass = bool(net_err <= 1e-12 and exit_match >= REPRO_MIN)
        all_pass = all_pass and day_pass
        out["per_day"].append({"day": date, "n_paired": int(both.sum()),
                               "net_max_abs_err": net_err,
                               "exit_match_rate": exit_match, "pass": day_pass})
    out["reproduction_pass"] = bool(all_pass)
    return out


# ---------------------------------------------------------------------------
# G1 정의 스팟 — 원시 행 직접 판독 독립 재계산(벡터 경로 무관).
# ---------------------------------------------------------------------------

def _raw_present(rows: Mapping[int, dict]):
    """{ts:row} → (창 내 present 오프셋 정렬, off→row 맵) — dense 재구성과 독립 판독."""
    items = []
    for ts, row in rows.items():
        off = extract._hms_to_offset(int(ts) % 1_000_000)
        if 0 <= off <= _W:
            items.append((off, row))
    items.sort(key=lambda x: x[0])
    pres = np.array([o for o, _ in items], dtype=np.int64)
    return pres, {int(o): r for o, r in items}


def _state_price_raw(pres, vmap, off, n, min_obs) -> bool:
    if off is None:
        return False
    cur = as_float(vmap[off].get("현재가"))
    prior = [as_float(vmap[int(p)].get("현재가")) for p in pres if off - n <= p <= off - 1]
    if len(prior) < min_obs:
        return False
    return cur > max(prior)


def _state_op_raw(vmap, off) -> bool:
    if off is None:
        return False
    op = as_float(vmap[off].get("시가"))
    return op > 0.0 and as_float(vmap[off].get("현재가")) > op


def _is_onset_raw(pres, vmap, variant, off, day) -> bool:
    """원시 행 직접 판독으로 (변형, off) 가 참 온셋(상승 교차/사건)인지 — G1 독립 판정."""
    pos = int(np.searchsorted(pres, off))
    if pos >= pres.size or int(pres[pos]) != off:
        return False
    prev_off = int(pres[pos - 1]) if pos > 0 else None
    if variant in detect.PRICE_WINDOW:
        n, mo = detect.PRICE_WINDOW[variant]
        return (_state_price_raw(pres, vmap, off, n, mo)
                and not _state_price_raw(pres, vmap, prev_off, n, mo))
    if variant == "OP":
        return _state_op_raw(vmap, off) and not _state_op_raw(vmap, prev_off)
    if variant == "DH":
        if prev_off is None:
            return False
        return as_float(vmap[off].get("고가")) > as_float(vmap[prev_off].get("고가"))
    # VI — VI해제시간>0 ∧ 체결시간≥해제 ∧ 해당 VI값 첫 자격 present 행.
    vi = as_float(vmap[off].get("VI해제시간"))
    ts = detect._offset_to_index(day, off)
    if not (vi > 0.0 and ts >= vi):
        return False
    for p in pres:
        if int(p) >= off:
            break
        if (as_float(vmap[int(p)].get("VI해제시간")) == vi
                and detect._offset_to_index(day, int(p)) >= vi):
            return False
    return True


def gate_g1_definition(df: pd.DataFrame, db_dir, *, n_spot: int = G1_SPOT_N,
                       seed: int = judge.SEED) -> Dict[str, object]:
    """변형별 무작위 n_spot 온셋을 원시 행 독립 재계산으로 사건 판정 일치 검정(§4 G1)."""
    paths = {int(d): p for d, p in day_list(db_dir)}
    rng = np.random.default_rng(seed)
    per: Dict[str, object] = {}
    all_pass = True
    variant = df["variant"].to_numpy()
    for v in detect.VARIANTS:
        idx = np.flatnonzero(variant == v)
        if idx.size == 0:
            per[v] = {"n_checked": 0, "n_match": 0, "match_rate": None}
            continue
        pick = idx if idx.size <= n_spot else rng.choice(idx, n_spot, replace=False)
        sub = df.iloc[pick]
        n_match = 0
        # (day,code) 그룹별 rows 1회 로드.
        rows_cache: Dict[Tuple[int, str], tuple] = {}
        for _, r in sub.iterrows():
            day, code, off = int(r["day"]), str(r["code"]), int(r["off"])
            key = (day, code)
            if key not in rows_cache:
                path = paths.get(day)
                if path is None:
                    rows_cache[key] = (np.empty(0, np.int64), {})
                else:
                    conn = reader.connect_ro(Path(path))
                    try:
                        rows_cache[key] = _raw_present(reader.load_stock_rows(conn, code))
                    finally:
                        conn.close()
            pres, vmap = rows_cache[key]
            if off in vmap and _is_onset_raw(pres, vmap, v, off, day):
                n_match += 1
        n_checked = int(len(sub))
        rate = n_match / n_checked if n_checked else None
        per[v] = {"n_checked": n_checked, "n_match": int(n_match), "match_rate": rate}
        all_pass = all_pass and (rate == 1.0 if rate is not None else True)
    return {"per_variant": per, "gate_pass": bool(all_pass), "n_spot": n_spot}


def gate_g2_vi_dump(df: pd.DataFrame, db_dir, *, n_sample: int = G2_VI_N,
                    seed: int = judge.SEED) -> Dict[str, object]:
    """VI 온셋 표본 n_sample 의 VI해제시간·체결시간·라벨 덤프(§4 G2 수동 확인용)."""
    paths = {int(d): p for d, p in day_list(db_dir)}
    vi = df[df["variant"] == "VI"]
    if vi.shape[0] == 0:
        return {"n_vi": 0, "samples": []}
    rng = np.random.default_rng(seed)
    take = vi if vi.shape[0] <= n_sample else vi.iloc[
        rng.choice(vi.shape[0], n_sample, replace=False)]
    samples: List[dict] = []
    for _, r in take.iterrows():
        day, code, off = int(r["day"]), str(r["code"]), int(r["off"])
        vi_release = None
        path = paths.get(day)
        if path is not None:
            conn = reader.connect_ro(Path(path))
            try:
                rows = reader.load_stock_rows(conn, code)
                _pres, vmap = _raw_present(rows)
                if off in vmap:
                    vi_release = as_float(vmap[off].get("VI해제시간"))
            finally:
                conn.close()
        samples.append({
            "day": day, "code": code, "off": off, "t0": int(r["t0"]),
            "체결시간": detect._offset_to_index(day, off),
            "VI해제시간": vi_release, "l3_labeled": bool(r["l3_labeled"]),
            "l3_net_pp": round(float(r["l3_net"]) * 100.0, 4),
        })
    return {"n_vi": int(vi.shape[0]), "n_sample": len(samples), "samples": samples}


# ---------------------------------------------------------------------------
# G4 은행 교차 앵커 — 서지 정확일치 (day,code,off) L3 bit-identical.
# ---------------------------------------------------------------------------

def gate_g4_bank_anchor(df: pd.DataFrame, surge_bank_path) -> Dict[str, object]:
    """서지 온셋과 (day,code,off) 정확 일치하는 돌파 온셋의 L3 를 서지 은행과 대조(§4 G4).

    동일 행·동일 출구·동일 비용이므로 bit-identical 이어야 한다(미달 = 파이프라인 결함).
    """
    sg = pd.read_parquet(surge_bank_path, columns=["code", "day", "off", "l3_net", "l3_labeled"])
    sg = sg[sg["l3_labeled"].to_numpy().astype(bool)]
    sg_map = {(int(d), str(c), int(o)): float(n) for c, d, o, n in
              zip(sg["code"], sg["day"], sg["off"], sg["l3_net"])}
    lab = df[df["l3_labeled"].to_numpy().astype(bool)]
    n_cmp = n_mismatch = 0
    max_err = 0.0
    examples: List[dict] = []
    for c, d, o, net in zip(lab["code"], lab["day"], lab["off"], lab["l3_net"]):
        key = (int(d), str(c), int(o))
        if key not in sg_map:
            continue
        n_cmp += 1
        err = abs(float(net) - sg_map[key])
        if err > max_err:
            max_err = err
        if err > 0.0:
            n_mismatch += 1
            if len(examples) < 10:
                examples.append({"day": key[0], "code": key[1], "off": key[2],
                                 "o3_l3_net": float(net), "surge_l3_net": sg_map[key]})
    return {
        "n_exact_overlap": n_cmp, "n_mismatch": n_mismatch,
        "max_abs_err": max_err,
        "gate_pass": bool(n_mismatch == 0),
        "examples": examples,
    }


# ---------------------------------------------------------------------------
# judge — 변형×모집단 단독 EV 판정 + 서술.
# ---------------------------------------------------------------------------

def _forced_cap_rate(df: pd.DataFrame, mask: np.ndarray) -> Optional[float]:
    """라벨된 온셋 중 강제 캡(l3_clause==0) 비율(F4 서술)."""
    lab = df["l3_labeled"].to_numpy().astype(bool) & mask
    n = int(lab.sum())
    if n == 0:
        return None
    return float((df["l3_clause"].to_numpy()[lab] == 0).sum()) / n


def _type_cross_matrix(df: pd.DataFrame) -> Dict[str, int]:
    """유형간 중복 — 같은 (day,code,off)를 공유하는 변형 쌍 카운트(§3 포함관계 서술)."""
    key = list(zip(df["day"].to_numpy(), df["code"].to_numpy(), df["off"].to_numpy()))
    by_key: Dict[tuple, set] = {}
    for k, v in zip(key, df["variant"].to_numpy()):
        by_key.setdefault(k, set()).add(str(v))
    out: Dict[str, int] = {}
    vs = detect.VARIANTS
    for i in range(len(vs)):
        for j in range(i + 1, len(vs)):
            pair = f"{vs[i]}&{vs[j]}"
            out[pair] = sum(1 for s in by_key.values() if vs[i] in s and vs[j] in s)
    return out


def run_judge(
    bank_path, surge_bank_path, *, match_surge_days: bool = False,
) -> Dict[str, object]:
    """판정 — 변형×모집단(전체/서지-비중첩) 단독 EV(judge_all_o3) + 서술(겹침·forced_cap·중복)."""
    df = load_bank(bank_path)
    restrict = np.unique(df["day"].to_numpy()).tolist() if match_surge_days else None
    overlapped = surge_overlap_flags(df, surge_bank_path, restrict_days=restrict)
    surge_nonoverlap = ~overlapped

    net_pp = df["l3_net"].to_numpy(dtype=np.float64) * 100.0
    units = judge.split_qualified_units(
        df["variant"].to_numpy(), net_pp, df["day"].to_numpy(),
        df["year"].to_numpy(), df["l3_labeled"].to_numpy().astype(bool),
        surge_nonoverlap, variants=detect.VARIANTS)
    judgment = judge.judge_all_o3(units)

    # 서술 — 겹침률·forced_cap·유형간 중복.
    variant = df["variant"].to_numpy()
    desc_overlap = {"pooled_rate": float(overlapped.mean()) if df.shape[0] else None,
                    "per_variant": {}}
    forced_cap: Dict[str, object] = {}
    for v in detect.VARIANTS:
        vm = variant == v
        desc_overlap["per_variant"][v] = (float(overlapped[vm].mean())
                                          if vm.any() else None)
        for pop in judge.POPULATIONS:
            m = vm & (surge_nonoverlap if pop == "surge_nonoverlap" else np.ones_like(vm))
            forced_cap[judge.unit_name(v, pop)] = _forced_cap_rate(df, m)

    return {
        "kind": "o3_breakout_judgment",
        "generated": datetime.now(timezone.utc).isoformat(),
        "preregistration": bank.SOURCE_SEAL,
        "judgment": judgment,
        "surge_overlap": desc_overlap,
        "forced_cap_rate": forced_cap,
        "type_cross_matrix": _type_cross_matrix(df),
        "match_surge_days": bool(match_surge_days),
    }
