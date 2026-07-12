"""O-1G 시가갭×시총 조합표 추출·집계 — 사전등록(2026-07-11) 봉인 구현.

봉인 근거: docs/research/condition_research/plans/
2026-07-11_o1g_gap_feasibility_preregistration.md
  §2 갭 공식   : 전일종가 = 현재가/(1+등락율/100)(same-row), 시가갭% =
                 (시가/전일종가-1)*100. 시가<=0·전일종가<=0·등락율=-100 → 제외.
  §3 조합표    : 갭 6구간 × 시총 3구간 × 진입창 2 × 출구 4 = 144 셀(사후 추가 금지).
  §4 셀 지표   : n·mean_net·P(net>=0)·P(net>=+1%)·median·q25/q75·MFE/MAE 평균·
                 일블록 부트스트랩 95% CI(n_boot 400)·연도별 부호·censor/제외율.
  §7 실행 규칙 : 원본 DB read-only(URI mode=ro)·엔진 백테 0회·stats_map 인프라
                 재사용(갭 파생만 추가).

표본 = 관심종목=1 (종목,초) 그리드(L0) 중 진입창(09:00:01~09:09:59) 내 시점.
관심종목=1 은 moneytop 유니버스와 동일함을 실측 확인(2022-03-23 전 행 48,092
행 100% 일치) — 봉인 v1 L0 정의(extract 모듈)를 그대로 재사용한다.

비용 = V2-A 승계: 수수료 0.015%x2 + 연도 세율(2022=0.23%/2023=0.20%) +
2틱 불리(costs_v2 단일 출처). L3 = 챔피언 RR8_12 매도식 리플레이(labels_v2,
V2-B 재현게이트 4/4 통과로 벡터 경로 허용 — 임의 2일 순수 스팟 재검 동반).

원본 tick DB 접근은 reader.connect_ro(URI mode=ro) 전용. print 금지 — logging.
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from alpha_lab.dataset import reader
from alpha_lab.dataset.labels_v2 import CHAMPION_SELL_SHA256, build_l3_labels
from alpha_lab.stats_common import day_block_bootstrap
from alpha_lab.stats_map import axes, config, config_v2, costs_v2, extract

logger = logging.getLogger(__name__)

__all__ = [
    "ENTRY_MAX_OFF",
    "EXIT_KINDS",
    "GAP_EDGES",
    "GAP_LABELS",
    "HORIZONS_O1G",
    "MKTCAP_LABELS",
    "WIN_LABELS",
    "WIN_SPLIT_OFF",
    "aggregate_cells",
    "extract_day_o1g",
    "gap_bucket",
    "gap_percent",
    "l3_pure_spot_check",
    "param_sha_o1g",
    "spearman_matrix",
]

# ── 조합표 축(§3 고정 경계 — 측정 후 변경 금지). ─────────────────────────────
GAP_EDGES = (0.0, 2.0, 5.0, 10.0, 20.0)          # 6구간: (-inf,0)/[0,2)/[2,5)/[5,10)/[10,20)/[20,inf)
GAP_LABELS = ("lt0", "0-2", "2-5", "5-10", "10-20", "ge20")
MKTCAP_LABELS = ("lt1000", "1000-3000", "ge3000")  # v1 MKTCAP_EDGES 재사용.
WIN_SPLIT_OFF = 300                                # 09:05:00 오프셋(진입창 경계).
ENTRY_MAX_OFF = 599                                # 09:09:59 (진입창 상한).
WIN_LABELS = ("0900-0904", "0905-0909")
HORIZONS_O1G = (60, 120, 300)                      # 고정지평 출구(교정 비용).
EXIT_KINDS = ("h60", "h120", "h300", "l3")         # 출구 4종(§3).
GAP_CONSTANCY_TOL_PP = 0.05                        # 갭 상수성 스팟검증 허용(%p).

_W = config.WINDOW_SECONDS
_MIN_CELL_N = config.MIN_CELL_N

# dense 적재 컬럼 — v1 8컬럼에 갭 파생용 현재가·시가만 추가(§7 갭 파생만 추가).
_COLUMNS_O1G = (
    "매도호가1", "매수호가1", "초당거래대금", "등락율", "시가총액",
    "체결강도", "현재가", "시가",
)

# 상관 원자료 변수(표본 수준) — 과제 지시 5종.
CORR_VARS_O1G = ("gap", "mktcap", "updown", "tramount", "strength")

# 표본 레코드 스키마(columnar).
_REC_KEYS = (
    "day", "off", "win", "gap_b", "mktcap_b",
    "gap", "mktcap", "updown", "tramount", "strength",
    "net_60", "valid_60", "censored_60", "mfe_60", "mae_60",
    "net_120", "valid_120", "censored_120", "mfe_120", "mae_120",
    "net_300", "valid_300", "censored_300", "mfe_300", "mae_300",
    "l3_net", "l3_labeled", "l3_clause", "l3_exit_off", "l3_mfe", "l3_mae",
    "code",
)


# ---------------------------------------------------------------------------
# 갭 파생(§2) — same-row 봉인 파생.
# ---------------------------------------------------------------------------

def gap_percent(cur: np.ndarray, updown: np.ndarray,
                open_: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """시가갭%(§2 공식)와 유효 마스크를 반환한다.

    전일종가 = 현재가/(1+등락율/100), 시가갭% = (시가/전일종가-1)*100.
    무효(시가<=0 · 전일종가<=0 · 등락율=-100)는 gap=NaN, valid=False.
    """
    cur_f = np.asarray(cur, dtype=np.float64)
    ud_f = np.asarray(updown, dtype=np.float64)
    open_f = np.asarray(open_, dtype=np.float64)
    denom = 1.0 + ud_f / 100.0
    safe = denom != 0.0
    prev_close = np.full(cur_f.shape, np.nan, dtype=np.float64)
    prev_close[safe] = cur_f[safe] / denom[safe]
    valid = safe & (open_f > 0.0) & (prev_close > 0.0) & (ud_f != -100.0)
    gap = np.full(cur_f.shape, np.nan, dtype=np.float64)
    gap[valid] = (open_f[valid] / prev_close[valid] - 1.0) * 100.0
    return gap, valid


def gap_bucket(gap: np.ndarray) -> np.ndarray:
    """시가갭% → 6구간 인덱스 0..5(경계값은 상단 구간 포함 — [a,b) 규약)."""
    return np.searchsorted(np.asarray(GAP_EDGES),
                           np.asarray(gap, dtype=np.float64), side="right")


# ---------------------------------------------------------------------------
# dense 적재 — v1 extract._load_dense 패턴에 갭 컬럼(현재가·시가)만 추가.
# ---------------------------------------------------------------------------

def _load_dense_o1g(conn, code: str) -> Optional[Dict[str, np.ndarray]]:
    """한 종목 테이블 → 오프셋 dense 배열(present 포함, 이름 기반 UTF-8)."""
    cur = conn.execute(
        f'SELECT "index","' + '","'.join(_COLUMNS_O1G) + f'" FROM "{code}"')
    rows = cur.fetchall()
    if not rows:
        return None
    present = np.zeros(_W + 1, dtype=bool)
    cols = {name: np.zeros(_W + 1, dtype=np.float64) for name in _COLUMNS_O1G}
    for row in rows:
        off = extract._hms_to_offset(int(row[0]) % 1_000_000)
        if 0 <= off <= _W:
            present[off] = True
            for name, value in zip(_COLUMNS_O1G, row[1:]):
                cols[name][off] = float(value) if value is not None else 0.0
    cols["present"] = present
    return cols


# ---------------------------------------------------------------------------
# 고정지평 라벨 — 교정 비용(연도 세율, costs_v2 단일 출처).
# ---------------------------------------------------------------------------

def _horizon_labels(dense: Mapping[str, np.ndarray], t0: np.ndarray,
                    h: int, year: int):
    """t0별 h초 지평 net·valid·censored·MFE·MAE(연도 세율, 2틱 불리)."""
    present, ask, bid = dense["present"], dense["매도호가1"], dense["매수호가1"]
    entry_ask = ask[t0 + 1]
    exit_off = t0 + h
    censored = exit_off > _W
    within = ~censored
    exit_present = np.zeros(t0.size, dtype=bool)
    exit_present[within] = present[exit_off[within]]
    valid = within & exit_present
    net = np.full(t0.size, np.nan, dtype=np.float64)
    if valid.any():
        net[valid] = costs_v2.net_from_quotes_year(
            entry_ask[valid], bid[exit_off[valid]], year)
    maxb, minb = extract._rolling_extremes(bid, present, h)
    mfe = np.full(t0.size, np.nan)
    mae = np.full(t0.size, np.nan)
    ok = valid & np.isfinite(maxb[t0])
    if ok.any():
        mfe[ok] = costs_v2.net_from_quotes_year(entry_ask[ok], maxb[t0][ok], year)
        mae[ok] = costs_v2.net_from_quotes_year(entry_ask[ok], minb[t0][ok], year)
    return net, valid, censored, mfe, mae


# ---------------------------------------------------------------------------
# L3 라벨 — 봉인 labels_v2 발화 재사용 + 연도 세율 재계상(pilot_v2 회계 동형).
# ---------------------------------------------------------------------------

def _offset_to_index(day: int, off: int) -> int:
    """오프셋(09:00:00 기준 초) → int YYYYMMDDHHMMSS."""
    total = 9 * 3600 + int(off)
    hh, rem = divmod(total, 3600)
    mm, ss = divmod(rem, 60)
    return int(day) * 1_000_000 + hh * 10000 + mm * 100 + ss


def _l3_labels_o1g(rows: Mapping[int, dict], t0: np.ndarray,
                   dense: Mapping[str, np.ndarray], day: int, year: int,
                   sell_text: str, engine: str, l3_stats: Dict[str, int]):
    """t0별 L3 실현 net(연도 세율)·절·청산오프셋·경로 MFE/MAE.

    발화(exit_time·clause)는 봉인 build_l3_labels 그대로. 실현 순손익은 청산
    매수호가1에 연도 세율(costs_v2)을 적용해 재계상한다(V2-B 회계 동형).
    MFE/MAE 는 보유 경로 (t0+1..exit_off] 관측 매수호가1 극값의 net.
    """
    t0_ints = [_offset_to_index(day, int(o)) for o in t0]
    labels, stats = build_l3_labels(rows, t0_ints, sell_text, engine=engine)
    for key in ("entry_missing", "entry_quote_bad", "path_empty",
                "no_exit_quote", "fired", "forced_cap", "labeled"):
        l3_stats[key] = l3_stats.get(key, 0) + int(stats[key])
    present, ask, bid = dense["present"], dense["매도호가1"], dense["매수호가1"]
    bid_nan = np.where(present, bid, np.nan)
    entry_ask = ask[t0 + 1]
    n = t0.size
    net = np.full(n, np.nan, dtype=np.float64)
    clause = np.full(n, -1, dtype=np.int8)
    exit_off = np.zeros(n, dtype=np.int16)
    mfe = np.full(n, np.nan)
    mae = np.full(n, np.nan)
    labeled = np.zeros(n, dtype=bool)
    tax = config_v2.year_tax_rate(year)
    for i, t0_int in enumerate(t0_ints):
        lab = labels[int(t0_int)]
        if lab is None:
            continue
        e_off = extract._hms_to_offset(int(lab["exit_time"]) % 1_000_000)
        exit_bid = float(bid[e_off])
        buy_fill, sell_fill = costs_v2.adverse_fill_year(
            np.asarray([entry_ask[i]]), np.asarray([exit_bid]))
        net[i] = float(costs_v2.net_rate_year_vec(buy_fill, sell_fill, tax)[0])
        clause[i] = int(lab["clause"])
        exit_off[i] = e_off
        labeled[i] = True
        path = bid_nan[int(t0[i]) + 1: e_off + 1]
        if path.size and np.isfinite(path).any():
            ext = np.asarray([np.nanmax(path), np.nanmin(path)])
            bf, sf = costs_v2.adverse_fill_year(
                np.asarray([entry_ask[i], entry_ask[i]]), ext)
            vals = costs_v2.net_rate_year_vec(bf, sf, tax)
            mfe[i], mae[i] = float(vals[0]), float(vals[1])
    return net, labeled, clause, exit_off, mfe, mae


# ---------------------------------------------------------------------------
# 일 추출 — 진입창(09:00:01~09:09:59) L0 표본 + 갭 파생 + 4종 출구.
# ---------------------------------------------------------------------------

def _candidate_t0(dense: Mapping[str, np.ndarray],
                  uni_off: np.ndarray) -> np.ndarray:
    """진입창 내 L0 후보 t0(봉인 v1 규약: present∧관심종목∧entry ask>0)."""
    present, ask = dense["present"], dense["매도호가1"]
    offs = np.arange(config.GRID_START_OFFSET, ENTRY_MAX_OFF + 1)
    in_uni = np.isin(offs, uni_off)
    entry_ok = present[offs + 1] & (ask[offs + 1] > 0.0)
    cand = present[offs] & in_uni & entry_ok
    return offs[cand]


def _gap_constancy(dense: Mapping[str, np.ndarray]) -> Optional[float]:
    """종목-일 내 갭 재계산 값 스프레드(%p) — 관측 유효행 <2 이면 None."""
    present = dense["present"]
    gap_all, valid_all = gap_percent(
        dense["현재가"], dense["등락율"], dense["시가"])
    use = present & valid_all
    if int(use.sum()) < 2:
        return None
    vals = gap_all[use]
    return float(np.max(vals) - np.min(vals))


def _extract_code_o1g(conn, code: str, day: int, uni_off: np.ndarray,
                      sell_text: str, engine: str, include_l3: bool,
                      meta: Dict[str, object]) -> Optional[Dict[str, np.ndarray]]:
    """한 종목의 진입창 표본 레코드 — 후보 0 또는 전량 제외 시 None."""
    dense = _load_dense_o1g(conn, code)
    if dense is None:
        return None
    t0 = _candidate_t0(dense, uni_off)
    if t0.size == 0:
        return None
    meta["n_candidates"] = int(meta.get("n_candidates", 0)) + int(t0.size)
    spread = _gap_constancy(dense)
    if spread is not None:
        meta["gap_spread_max"] = max(float(meta.get("gap_spread_max", 0.0)), spread)
        meta["gap_spread_n"] = int(meta.get("gap_spread_n", 0)) + 1
        if spread > GAP_CONSTANCY_TOL_PP:
            meta["gap_spread_violations"] = int(
                meta.get("gap_spread_violations", 0)) + 1
    gap_all, valid_all = gap_percent(
        dense["현재가"], dense["등락율"], dense["시가"])
    keep = valid_all[t0]
    meta["n_gap_excluded"] = int(meta.get("n_gap_excluded", 0)) + int((~keep).sum())
    t0 = t0[keep]
    if t0.size == 0:
        return None
    year = day // 10000
    rec: Dict[str, np.ndarray] = {
        "day": np.full(t0.size, day, dtype=np.int32),
        "off": t0.astype(np.int16),
        "win": (t0 >= WIN_SPLIT_OFF).astype(np.int8),
        "gap_b": gap_bucket(gap_all[t0]).astype(np.int8),
        "mktcap_b": axes.mktcap_bucket(dense["시가총액"][t0]).astype(np.int8),
        "gap": gap_all[t0].astype(np.float32),
        "mktcap": dense["시가총액"][t0].astype(np.float32),
        "updown": dense["등락율"][t0].astype(np.float32),
        "tramount": dense["초당거래대금"][t0].astype(np.float32),
        "strength": dense["체결강도"][t0].astype(np.float32),
        "code": np.full(t0.size, str(code), dtype="U6"),
    }
    for h in HORIZONS_O1G:
        net, valid, censored, mfe, mae = _horizon_labels(dense, t0, h, year)
        rec[f"net_{h}"] = net.astype(np.float32)
        rec[f"valid_{h}"] = valid
        rec[f"censored_{h}"] = censored
        rec[f"mfe_{h}"] = mfe.astype(np.float32)
        rec[f"mae_{h}"] = mae.astype(np.float32)
    if include_l3:
        rows = reader.load_stock_rows(conn, code)
        l3_stats: Dict[str, int] = meta.setdefault("l3_stats", {})  # type: ignore[assignment]
        net, labeled, clause, exit_off, mfe, mae = _l3_labels_o1g(
            rows, t0, dense, day, year, sell_text, engine, l3_stats)
        rec["l3_net"] = net.astype(np.float32)
        rec["l3_labeled"] = labeled
        rec["l3_clause"] = clause
        rec["l3_exit_off"] = exit_off
        rec["l3_mfe"] = mfe.astype(np.float32)
        rec["l3_mae"] = mae.astype(np.float32)
    else:
        n = t0.size
        rec["l3_net"] = np.full(n, np.nan, dtype=np.float32)
        rec["l3_labeled"] = np.zeros(n, dtype=bool)
        rec["l3_clause"] = np.full(n, -1, dtype=np.int8)
        rec["l3_exit_off"] = np.zeros(n, dtype=np.int16)
        rec["l3_mfe"] = np.full(n, np.nan, dtype=np.float32)
        rec["l3_mae"] = np.full(n, np.nan, dtype=np.float32)
    return rec


def extract_day_o1g(db_path, date: str, sell_text: str, *,
                    engine: str = "vector", include_l3: bool = True,
                    ) -> Tuple[Dict[str, np.ndarray], Dict[str, object]]:
    """일 DB 하나의 진입창 표본(4종 출구 라벨) + 일 메타 — 결정론.

    Returns:
        (sample, meta). sample 은 _REC_KEYS columnar dict(빈 날은 빈 배열),
        meta 는 후보수·갭 제외수·갭 상수성 스팟·L3 stats.
    """
    conn = reader.connect_ro(Path(db_path))
    meta: Dict[str, object] = {"date": str(date)}
    try:
        uni = extract._moneytop_by_code(conn)
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        codes = [n for (n,) in cur if n.isdigit() and len(n) == 6]
        day = int(date)
        chunks: List[Dict[str, np.ndarray]] = []
        for code in codes:
            uni_off = uni.get(code, np.empty(0, np.int64))
            if uni_off.size == 0 or int(uni_off.min()) > ENTRY_MAX_OFF:
                continue  # 진입창 내 유니버스 소속 없음 — 후보 불가.
            rec = _extract_code_o1g(
                conn, code, day, uni_off, sell_text, engine, include_l3, meta)
            if rec is not None:
                chunks.append(rec)
    finally:
        conn.close()
    if not chunks:
        return {k: np.empty(0, dtype=_empty_dtype(k)) for k in _REC_KEYS}, meta
    sample = {k: np.concatenate([c[k] for c in chunks]) for k in _REC_KEYS}
    meta["n_samples"] = int(sample["off"].size)
    return sample, meta


def _empty_dtype(key: str):
    if key == "day":
        return np.int32
    if key in ("off", "l3_exit_off"):
        return np.int16
    if key in ("win", "gap_b", "mktcap_b", "l3_clause"):
        return np.int8
    if key.startswith(("valid_", "censored_")) or key == "l3_labeled":
        return bool
    if key == "code":
        return "U6"
    return np.float32


# ---------------------------------------------------------------------------
# 셀 집계(§4) — 144셀 전수, 판정 수치는 §5 기준용 원자료까지만.
# ---------------------------------------------------------------------------

def _cell_seed(*keys: object) -> int:
    """셀 키 → 결정론 부트스트랩 시드(BUILD_SEED+셀 지문, 해시시드 무관)."""
    blob = ("|".join(str(k) for k in keys)).encode("utf-8")
    digest = int(hashlib.sha256(blob).hexdigest()[:8], 16)
    return (config.BUILD_SEED + digest) % (2 ** 32)


def _exit_arrays(sample: Mapping[str, np.ndarray], exit_kind: str):
    """출구 종류 → (net, valid, censored, mfe, mae). L3 censor=강제캡."""
    if exit_kind == "l3":
        labeled = sample["l3_labeled"]
        censored = labeled & (sample["l3_clause"] == 0)  # 09:30 강제 청산.
        return (sample["l3_net"], labeled, censored,
                sample["l3_mfe"], sample["l3_mae"])
    h = int(exit_kind[1:])
    return (sample[f"net_{h}"], sample[f"valid_{h}"], sample[f"censored_{h}"],
            sample[f"mfe_{h}"], sample[f"mae_{h}"])


def _year_means(net: np.ndarray, years: np.ndarray,
                used: np.ndarray) -> Dict[str, Optional[float]]:
    """연도별 mean_net(2022/2023) — 그 해 표본 0이면 None."""
    out: Dict[str, Optional[float]] = {}
    for y in (2022, 2023):
        m = used & (years == y)
        out[f"mean_net_{y}"] = float(np.mean(net[m].astype(np.float64))) \
            if m.any() else None
    return out


def _cell_row(sample: Mapping[str, np.ndarray], years: np.ndarray,
              membership: np.ndarray, exit_kind: str,
              gb: int, mb: int, wb: int) -> Dict[str, object]:
    """한 셀(§3 좌표 + 출구)의 §4 전 지표 행."""
    net, valid, censored, mfe, mae = _exit_arrays(sample, exit_kind)
    used = membership & valid
    vals = net[used].astype(np.float64)
    n_members = int(membership.sum())
    row: Dict[str, object] = {
        "exit": exit_kind, "gap_b": gb, "gap_label": GAP_LABELS[gb],
        "mktcap_b": mb, "mktcap_label": MKTCAP_LABELS[mb],
        "win": wb, "win_label": WIN_LABELS[wb],
        "n": int(vals.size), "n_candidates": n_members,
        "exclusion_rate": (1.0 - vals.size / n_members) if n_members else None,
        "censor_rate": (float((membership & censored).sum()) / n_members)
        if n_members else None,
        "insufficient": int(vals.size < _MIN_CELL_N),
    }
    if vals.size:
        q25, med, q75 = np.percentile(vals, [25, 50, 75])
        mfe_v = mfe[used].astype(np.float64)
        mae_v = mae[used].astype(np.float64)
        row.update({
            "mean_net": float(np.mean(vals)),
            "p_net_ge0": float(np.mean(vals >= 0.0)),
            "p_net_ge1": float(np.mean(vals >= 0.01)),
            "median_net": float(med),
            "q25_net": float(q25), "q75_net": float(q75),
            "mfe_mean": float(np.nanmean(mfe_v)) if np.isfinite(mfe_v).any() else None,
            "mae_mean": float(np.nanmean(mae_v)) if np.isfinite(mae_v).any() else None,
        })
        boot = day_block_bootstrap(
            sample["day"], np.nan_to_num(net.astype(np.float64)), used,
            n_boot=config.N_BOOT, seed=_cell_seed("o1g", exit_kind, gb, mb, wb),
            stat="mean")
        row["ci_low"] = _finite(boot["ci_low"])
        row["ci_high"] = _finite(boot["ci_high"])
        row["p_one_sided"] = _finite(boot["p_one_sided"])
        row.update(_year_means(net, years, used))
        m22 = row["mean_net_2022"]
        m23 = row["mean_net_2023"]
        row["year_sign_2022"] = _sign(m22)
        row["year_sign_2023"] = _sign(m23)
        row["year_same_sign_pos"] = bool(
            m22 is not None and m23 is not None and m22 > 0.0 and m23 > 0.0)
    else:
        for k in ("mean_net", "p_net_ge0", "p_net_ge1", "median_net", "q25_net",
                  "q75_net", "mfe_mean", "mae_mean", "ci_low", "ci_high",
                  "p_one_sided", "mean_net_2022", "mean_net_2023",
                  "year_sign_2022", "year_sign_2023"):
            row[k] = None
        row["year_same_sign_pos"] = False
    return row


def _sign(value: Optional[float]) -> Optional[int]:
    if value is None:
        return None
    return 1 if value > 0.0 else (-1 if value < 0.0 else 0)


def _finite(value) -> Optional[float]:
    return float(value) if value is not None and np.isfinite(value) else None


def aggregate_cells(sample: Mapping[str, np.ndarray]) -> List[Dict[str, object]]:
    """전 표본 → 144셀(§3 조합표 전수) 지표 행 목록 — 순서 결정론."""
    years = (sample["day"] // 10000).astype(np.int64)
    rows: List[Dict[str, object]] = []
    for gb in range(len(GAP_LABELS)):
        for mb in range(len(MKTCAP_LABELS)):
            for wb in range(len(WIN_LABELS)):
                membership = ((sample["gap_b"] == gb)
                              & (sample["mktcap_b"] == mb)
                              & (sample["win"] == wb))
                for exit_kind in EXIT_KINDS:
                    rows.append(_cell_row(
                        sample, years, membership, exit_kind, gb, mb, wb))
    return rows


# ---------------------------------------------------------------------------
# 상관 원자료 — 표본 변수 5종 vs 출구 net 4종 스피어만.
# ---------------------------------------------------------------------------

def spearman_matrix(sample: Mapping[str, np.ndarray]) -> Dict[str, object]:
    """스피어만 상관 행렬 {vars×exits} — 유효쌍(net valid ∧ 변수 유한)만."""
    from scipy.stats import spearmanr

    rho: List[List[Optional[float]]] = []
    n_pairs: List[List[int]] = []
    for var in CORR_VARS_O1G:
        x = sample[var].astype(np.float64)
        rho_row: List[Optional[float]] = []
        n_row: List[int] = []
        for exit_kind in EXIT_KINDS:
            net, valid, _c, _f, _a = _exit_arrays(sample, exit_kind)
            m = valid & np.isfinite(x) & np.isfinite(net)
            n = int(m.sum())
            if n >= 3:
                res = spearmanr(x[m], net[m].astype(np.float64))
                rho_row.append(float(res.statistic))
            else:
                rho_row.append(None)
            n_row.append(n)
        rho.append(rho_row)
        n_pairs.append(n_row)
    return {"vars": list(CORR_VARS_O1G), "exits": list(EXIT_KINDS),
            "spearman_rho": rho, "n_pairs": n_pairs}


# ---------------------------------------------------------------------------
# L3 순수 스팟 재검 — 임의 일의 표본 부분집합을 pure 엔진으로 재라벨·비교.
# ---------------------------------------------------------------------------

def l3_pure_spot_check(db_path, date: str, day_sample: Mapping[str, np.ndarray],
                       indices: np.ndarray, sell_text: str) -> Dict[str, object]:
    """선정 표본 인덱스들을 pure 엔진으로 재라벨해 vector 결과와 대조한다.

    비교 항목: labeled 일치, 청산 오프셋 일치, net 일치(1e-12). 순수 경로가
    기준 — 불일치 목록을 그대로 보고한다(조용한 드리프트 금지).
    """
    day = int(date)
    year = day // 10000
    tax = config_v2.year_tax_rate(year)
    by_code: Dict[str, List[int]] = {}
    for i in indices.tolist():
        by_code.setdefault(str(day_sample["code"][i]), []).append(i)
    n_cmp = n_match = 0
    mismatches: List[dict] = []
    conn = reader.connect_ro(Path(db_path))
    try:
        for code, idx_list in sorted(by_code.items()):
            rows = reader.load_stock_rows(conn, code)
            t0_ints = [_offset_to_index(day, int(day_sample["off"][i]))
                       for i in idx_list]
            labels, _ = build_l3_labels(rows, t0_ints, sell_text, engine="pure")
            for i, t0_int in zip(idx_list, t0_ints):
                lab = labels[int(t0_int)]
                vec_labeled = bool(day_sample["l3_labeled"][i])
                n_cmp += 1
                if lab is None:
                    ok = not vec_labeled
                    pure_off = None
                    pure_net = None
                else:
                    pure_off = extract._hms_to_offset(
                        int(lab["exit_time"]) % 1_000_000)
                    exit_bid = float(rows[int(lab["exit_time"])].get("매수호가1") or 0.0)
                    entry_int = _offset_to_index(day, int(day_sample["off"][i]) + 1)
                    entry_ask = float(rows[entry_int].get("매도호가1") or 0.0)
                    bf, sf = costs_v2.adverse_fill_year(
                        np.asarray([entry_ask]), np.asarray([exit_bid]))
                    pure_net = float(costs_v2.net_rate_year_vec(bf, sf, tax)[0])
                    ok = (vec_labeled
                          and int(day_sample["l3_exit_off"][i]) == pure_off
                          and abs(float(day_sample["l3_net"][i]) - pure_net) < 1e-6)
                if ok:
                    n_match += 1
                elif len(mismatches) < 20:
                    mismatches.append({
                        "code": code, "off": int(day_sample["off"][i]),
                        "vec_labeled": vec_labeled,
                        "vec_exit_off": int(day_sample["l3_exit_off"][i]),
                        "vec_net": float(day_sample["l3_net"][i]),
                        "pure_exit_off": pure_off, "pure_net": pure_net,
                    })
    finally:
        conn.close()
    return {"date": str(date), "n_compared": n_cmp, "n_match": n_match,
            "match_rate": (n_match / n_cmp) if n_cmp else None,
            "mismatches": mismatches, "passed": bool(n_cmp and n_match == n_cmp)}


# ---------------------------------------------------------------------------
# 파라미터 지문 — 빌드 영수증용(sha 사후 변경 감지).
# ---------------------------------------------------------------------------

def param_sha_o1g() -> str:
    """O-1G 봉인 파라미터 묶음 sha256(16자리) — v2 지문 결합 포함."""
    payload = {
        "gap_edges": list(GAP_EDGES),
        "mktcap_edges": list(config.MKTCAP_EDGES),
        "entry_windows": [[config.GRID_START_OFFSET, WIN_SPLIT_OFF - 1],
                          [WIN_SPLIT_OFF, ENTRY_MAX_OFF]],
        "horizons": list(HORIZONS_O1G),
        "exit_kinds": list(EXIT_KINDS),
        "min_cell_n": _MIN_CELL_N,
        "n_boot": config.N_BOOT,
        "build_seed": config.BUILD_SEED,
        "gap_constancy_tol_pp": GAP_CONSTANCY_TOL_PP,
        "champion_sell_sha256": CHAMPION_SELL_SHA256,
        "param_sha_v2": config_v2.param_sha_v2(),
        "corr_vars": list(CORR_VARS_O1G),
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]
