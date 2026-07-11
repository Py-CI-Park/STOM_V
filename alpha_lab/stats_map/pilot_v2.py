"""V2-B 파일럿 오케스트레이션 — L1 온셋에 h300 교정 + L3_replay 라벨 병렬 산출.

봉인: S-트랙 사전등록 V2-A. 파일럿 창 1개월(기본 2022-03-23~2022-04-30)의
L1 서지 온셋 표본(v1 정의 그대로 재사용: 2.0×·쿨다운 30초·관심종목 게이트·
entry 존재)에 두 라벨을 붙인다.

  - h300(교정판): 고정 300초 뒤 청산, 새 경계로 버킷화, 연도 세율(대조군).
  - L3_replay   : 챔피언 현직 매도식(RR8_12 계열) 리플레이 실현 순손익, 연도
    세율. **RR8_12 출구에 조건부인 라벨** — 다른 출구면 다른 지도.

라벨 규율(라벨-only):
  - 온셋 정의·시간대·시총 축·창은 v1 봉인 재사용(extract._load_dense,
    extract._moneytop_by_code, axes.surge_ratio/surge_onset_mask). 갭·돌파·축
    변경 없음.
  - 등락율 버킷만 새 경계(config_v2.UPDOWN_EDGES_V2)로 교체.
  - L3 발화 타이밍(exit_time·clause)은 봉인 챔피언 매도식(labels_v2.
    build_l3_labels — kiwoom_pgsgsp 0.18% 엔진 수익률로 발화) 그대로 재사용하고,
    **실현 순손익만** 연도 세율로 재계상한다(§1 기반 교정 = 비용 회계 교정,
    전략 재시뮬 아님). h300 도 동일하게 연도 세율만 교정.

재현 게이트(§3): 같은 온셋에 순수/벡터 두 엔진의 L3 발화를 돌려 청산 시각·
가격·순손익 일치를 검정한다. 순수 경로가 기준(기존 labels_v2 코드) — 벡터가
미달이면 벡터 경로 금지, 순수 경로만 채택.

원본 tick DB 접근은 read-only URI 전용. 엔진 백테 0회. print 금지 — logging.
"""
from __future__ import annotations

import hashlib
import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence

import numpy as np

from alpha_lab.dataset import reader
from alpha_lab.dataset.labels_v2 import CHAMPION_SELL_SHA256, build_l3_labels
from alpha_lab.dataset.schema import as_float
from alpha_lab.stats_common import day_block_bootstrap
from alpha_lab.stats_map import axes, config, config_v2, costs_v2, extract

logger = logging.getLogger(__name__)

_W = config.WINDOW_SECONDS            # 1800 (09:00:00~09:30:00 오프셋 상한).
_GRID_START = config.GRID_START_OFFSET  # 1 (t0 첫 오프셋 = 09:00:01).
_MIN_CELL_N = config.MIN_CELL_N
_ENGINES = ("pure", "vector")

# 파일럿 온셋 컬럼 스키마(columnar accumulator).
_ONSET_KEYS = (
    "day", "off", "time_b", "updown_q", "mktcap_b",
    "h300_net", "h300_valid", "h300_censored",
    "l3_net_pure", "l3_exit_pure", "l3_price_pure", "l3_clause_pure",
    "l3_labeled_pure",
    "l3_net_vector", "l3_exit_vector", "l3_price_vector", "l3_labeled_vector",
)


# ---------------------------------------------------------------------------
# 축 버킷 — v2 등락율 경계(교정), 시간대·시총은 v1 재사용.
# ---------------------------------------------------------------------------

def updown_quartile_v2(updown: np.ndarray) -> np.ndarray:
    """등락율 → 4분위 인덱스 0..3(새 경계 1.59/3.56/6.88, 경계값 상단 포함)."""
    return np.searchsorted(np.asarray(config_v2.UPDOWN_EDGES_V2),
                           np.asarray(updown, dtype=np.float64), side="right")


def _offset_to_index(day: int, off: int) -> int:
    """오프셋(09:00:00 기준 초) → int YYYYMMDDHHMMSS."""
    total = 9 * 3600 + int(off)
    hh, rem = divmod(total, 3600)
    mm, ss = divmod(rem, 60)
    return int(day) * 1_000_000 + hh * 10000 + mm * 100 + ss


# ---------------------------------------------------------------------------
# 온셋 검출 — v1 봉인 로직 재사용(extract/axes 재사용, 드리프트 금지).
# ---------------------------------------------------------------------------

def _onset_offsets(dense: Mapping[str, np.ndarray],
                   uni_off: np.ndarray) -> np.ndarray:
    """한 종목 dense → L1 서지 온셋 t0 오프셋(v1 채택 규칙 + 온셋 마스크)."""
    present = dense["present"]
    ask = dense["매도호가1"]
    ratio = axes.surge_ratio(dense["초당거래대금"], present)
    onset = axes.surge_onset_mask(ratio, present)
    offs = np.arange(_GRID_START, _W)             # t0 ∈ 09:00:01..09:29:59.
    in_uni = np.isin(offs, uni_off)
    entry_ok = present[offs + 1] & (ask[offs + 1] > 0.0)
    cand = present[offs] & in_uni & entry_ok & onset[offs]
    return offs[cand]


# ---------------------------------------------------------------------------
# 라벨 — h300 교정판(대조군) + L3_replay(순수/벡터).
# ---------------------------------------------------------------------------

def _h300_labels(dense: Mapping[str, np.ndarray], onset_off: np.ndarray,
                 year: int):
    """온셋 오프셋별 h300 교정 net·유효·절단(고정 300초, 연도 세율).

    valid = 창 내(off+300<=1800) ∧ 청산 초 관측. censored = off+300>1800.
    net 은 config_v2 세율(vector 경로 costs_v2.net_from_quotes_year).
    """
    present, ask, bid = dense["present"], dense["매도호가1"], dense["매수호가1"]
    exit_off = onset_off + config_v2.H300_HORIZON
    censored = exit_off > _W
    within = ~censored
    exit_present = np.zeros(onset_off.size, dtype=bool)
    exit_present[within] = present[exit_off[within]]
    valid = within & exit_present
    net = np.full(onset_off.size, np.nan, dtype=np.float64)
    if valid.any():
        entry_ask = ask[onset_off[valid] + 1]
        exit_bid = bid[exit_off[valid]]
        net[valid] = costs_v2.net_from_quotes_year(entry_ask, exit_bid, year)
    return net, valid, censored


def _l3_labels(rows: Mapping[int, dict], t0_ints: Sequence[int],
               entry_ask: np.ndarray, sell_text: str, engine: str, year: int,
               expected_sha: str):
    """온셋 t0별 L3 실현 net·청산시각·청산가·절(연도 세율 재계상).

    발화(exit_time·clause)는 봉인 build_l3_labels(engine) 그대로. 실현 순손익은
    회복한 청산 매수호가1 에 연도 세율을 적용해 재계산한다(엔진 무관 회계).
    """
    labels, _ = build_l3_labels(
        rows, t0_ints, sell_text, engine=engine, expected_sha=expected_sha)
    n = len(t0_ints)
    net = np.full(n, np.nan, dtype=np.float64)
    price = np.full(n, np.nan, dtype=np.float64)
    exit_t = np.zeros(n, dtype=np.int64)
    clause = np.full(n, -1, dtype=np.int64)
    labeled = np.zeros(n, dtype=bool)
    exit_bid = np.zeros(n, dtype=np.float64)
    for i, t0 in enumerate(t0_ints):
        lab = labels[int(t0)]
        if lab is None:
            continue
        exit_time = int(lab["exit_time"])
        exit_bid[i] = as_float(rows[exit_time].get("매수호가1"))
        exit_t[i] = exit_time
        clause[i] = int(lab["clause"])
        labeled[i] = True
    m = labeled
    if m.any():
        buy_fill, sell_fill = costs_v2.adverse_fill_year(entry_ask[m], exit_bid[m])
        tax = config_v2.year_tax_rate(year)
        net[m] = costs_v2.net_rate_year_vec(buy_fill, sell_fill, tax)
        price[m] = sell_fill
    return net, exit_t, price, clause, labeled


def _extract_code(conn: sqlite3.Connection, code: str, day: int,
                  uni_off: np.ndarray, sell_text: str,
                  expected_sha: str) -> Optional[Dict[str, np.ndarray]]:
    """한 종목의 온셋 표본 레코드(h300 + L3 pure/vector). 온셋 0이면 None."""
    dense = extract._load_dense(conn, code)
    if dense is None:
        return None
    onset_off = _onset_offsets(dense, uni_off)
    if onset_off.size == 0:
        return None
    year = day // 10000
    entry_ask = dense["매도호가1"][onset_off + 1]
    t0_ints = [_offset_to_index(day, int(o)) for o in onset_off]
    rows = reader.load_stock_rows(conn, code)
    h300_net, h300_valid, h300_censored = _h300_labels(dense, onset_off, year)
    net_p, exit_p, price_p, clause_p, lab_p = _l3_labels(
        rows, t0_ints, entry_ask, sell_text, "pure", year, expected_sha)
    net_v, exit_v, price_v, _clause_v, lab_v = _l3_labels(
        rows, t0_ints, entry_ask, sell_text, "vector", year, expected_sha)
    return {
        "day": np.full(onset_off.size, day, dtype=np.int32),
        "off": onset_off.astype(np.int16),
        "time_b": axes.time_bucket_offset(onset_off).astype(np.int8),
        "updown_q": updown_quartile_v2(dense["등락율"][onset_off]).astype(np.int8),
        "mktcap_b": axes.mktcap_bucket(dense["시가총액"][onset_off]).astype(np.int8),
        "h300_net": h300_net, "h300_valid": h300_valid,
        "h300_censored": h300_censored,
        "l3_net_pure": net_p, "l3_exit_pure": exit_p, "l3_price_pure": price_p,
        "l3_clause_pure": clause_p.astype(np.int8), "l3_labeled_pure": lab_p,
        "l3_net_vector": net_v, "l3_exit_vector": exit_v,
        "l3_price_vector": price_v, "l3_labeled_vector": lab_v,
    }


def extract_day(db_path, date: str, sell_text: str,
                expected_sha: str = CHAMPION_SELL_SHA256) -> Dict[str, np.ndarray]:
    """일 DB 하나의 전 종목 L1 온셋 표본(h300+L3) 배열 dict — 결정론."""
    conn = reader.connect_ro(Path(db_path))
    try:
        uni = extract._moneytop_by_code(conn)
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        codes = [n for (n,) in cur if n.isdigit() and len(n) == 6]
        day = int(date)
        chunks: List[Dict[str, np.ndarray]] = []
        for code in codes:
            rec = _extract_code(
                conn, code, day, uni.get(code, np.empty(0, np.int64)), sell_text,
                expected_sha)
            if rec is not None:
                chunks.append(rec)
    finally:
        conn.close()
    if not chunks:
        return {key: np.empty(0, dtype=_empty_dtype(key)) for key in _ONSET_KEYS}
    return {key: np.concatenate([c[key] for c in chunks]) for key in _ONSET_KEYS}


def _empty_dtype(key: str):
    if key in ("day",):
        return np.int32
    if key in ("off",):
        return np.int16
    if key in ("time_b", "updown_q", "mktcap_b", "l3_clause_pure"):
        return np.int8
    if key in ("l3_exit_pure", "l3_exit_vector"):
        return np.int64
    if key in ("h300_valid", "h300_censored", "l3_labeled_pure",
               "l3_labeled_vector"):
        return bool
    return np.float64


# ---------------------------------------------------------------------------
# 재현 게이트 — 순수 vs 벡터(§3 전 기준). 순수 = 기존 labels_v2 기준.
# ---------------------------------------------------------------------------

def reproduction_gate(sample: Mapping[str, np.ndarray]) -> Dict[str, object]:
    """L3 순수/벡터 청산 시각·가격·순손익 일치 게이트(§3 전 기준 동시 충족).

    기준: 청산 시각·가격 동시 일치율 ≥ 0.999, 수익률 오차 중앙값 0.0%p,
    p99 ≤ 0.10%p, 최대 오차 보고, 불일치 원인 분류. 순수가 기준이므로 벡터가
    미달이면 벡터 경로 금지(순수만 채택).
    """
    both = sample["l3_labeled_pure"] & sample["l3_labeled_vector"]
    only_pure = int((sample["l3_labeled_pure"] & ~sample["l3_labeled_vector"]).sum())
    only_vec = int((~sample["l3_labeled_pure"] & sample["l3_labeled_vector"]).sum())
    n = int(both.sum())
    exit_p = sample["l3_exit_pure"][both]
    exit_v = sample["l3_exit_vector"][both]
    price_p = sample["l3_price_pure"][both]
    price_v = sample["l3_price_vector"][both]
    net_p = sample["l3_net_pure"][both]
    net_v = sample["l3_net_vector"][both]
    time_match = exit_p == exit_v
    price_match = price_p == price_v
    both_match = time_match & price_match
    err_pp = np.abs(net_p - net_v) * 100.0
    match_rate = float(both_match.mean()) if n else 0.0
    median_pp = float(np.median(err_pp)) if n else 0.0
    p99_pp = float(np.percentile(err_pp, 99)) if n else 0.0
    max_pp = float(err_pp.max()) if n else 0.0
    mismatches = _classify_mismatches(sample, both, time_match, price_match)
    criteria = {
        "match_rate_ge_999": match_rate >= 0.999,
        "err_median_0pp": median_pp <= 1e-9,
        "err_p99_le_010pp": p99_pp <= 0.10,
    }
    return {
        "n_paired": n,
        "only_pure_labeled": only_pure,
        "only_vector_labeled": only_vec,
        "time_match_rate": float(time_match.mean()) if n else 0.0,
        "price_match_rate": float(price_match.mean()) if n else 0.0,
        "time_and_price_match_rate": match_rate,
        "err_median_pp": median_pp,
        "err_p99_pp": p99_pp,
        "err_max_pp": max_pp,
        "n_mismatch": int((~both_match).sum()),
        "mismatch_causes": mismatches,
        "criteria": criteria,
        "gate_pass": bool(n > 0 and all(criteria.values())
                          and only_pure == 0 and only_vec == 0),
    }


def _classify_mismatches(sample, both, time_match, price_match) -> Dict[str, object]:
    """불일치 원인 분류(체결 컨벤션/절단/데이터 결측) + 대표 사례."""
    bad_idx = np.flatnonzero(both)[~(time_match & price_match)]
    causes = {"vector_later_exit": 0, "vector_earlier_exit": 0,
              "same_exit_price_diff": 0}
    examples: List[dict] = []
    exit_p = sample["l3_exit_pure"]
    exit_v = sample["l3_exit_vector"]
    for i in bad_idx.tolist():
        ep, ev = int(exit_p[i]), int(exit_v[i])
        if ev > ep:
            causes["vector_later_exit"] += 1     # 벡터 발화 누락 → 늦은 청산.
        elif ev < ep:
            causes["vector_earlier_exit"] += 1
        else:
            causes["same_exit_price_diff"] += 1  # 체결 컨벤션 차이.
        if len(examples) < 10:
            examples.append({
                "day": int(sample["day"][i]), "off": int(sample["off"][i]),
                "exit_pure": ep, "exit_vector": ev,
                "price_pure": float(sample["l3_price_pure"][i]),
                "price_vector": float(sample["l3_price_vector"][i]),
                "clause_pure": int(sample["l3_clause_pure"][i]),
            })
    causes["examples"] = examples
    return causes


# ---------------------------------------------------------------------------
# 셀 집계 — 시간대×등락율[×시총], h300 vs L3(순수). 게이트 판정은 하지 않는다.
# ---------------------------------------------------------------------------

def _cell_stats(net: np.ndarray, day_ids: np.ndarray, membership: np.ndarray,
                valid: np.ndarray, censored: np.ndarray, *, seed: int,
                insufficient: bool) -> Dict[str, object]:
    """한 셀·라벨의 분포 요약(v1 stats 의미론 미러, 관찰용 — 판정 아님)."""
    used = membership & valid
    vals = net[used].astype(np.float64)
    row: Dict[str, object] = {
        "n": int(vals.size),
        "n_candidates": int(membership.sum()),
        "censor_rate": (float((membership & censored).sum()) /
                        float(membership.sum()) if membership.any() else None),
        "insufficient": int(insufficient),
    }
    if vals.size:
        q25, med, q75 = np.percentile(vals, [25, 50, 75])
        wins = vals[vals > 0.0]
        losses = vals[vals < 0.0]
        row.update({
            "p_net_ge0": float(np.mean(vals >= 0.0)),
            "p_net_ge1": float(np.mean(vals >= 0.01)),
            "mean_net": float(np.mean(vals)),
            "median_net": float(med), "q25_net": float(q25), "q75_net": float(q75),
            "winrate": float(wins.size) / float(vals.size),
            "payoff": (float(np.mean(wins) / abs(np.mean(losses)))
                       if wins.size and losses.size else None),
        })
        boot = day_block_bootstrap(day_ids, np.nan_to_num(net), used,
                                   n_boot=config.N_BOOT, seed=seed, stat="mean")
        row["ci_low"] = _finite(boot["ci_low"])
        row["ci_high"] = _finite(boot["ci_high"])
    else:
        for k in ("p_net_ge0", "p_net_ge1", "mean_net", "median_net", "q25_net",
                  "q75_net", "winrate", "payoff", "ci_low", "ci_high"):
            row[k] = None
    return row


def _finite(value) -> Optional[float]:
    return float(value) if value is not None and np.isfinite(value) else None


def _cell_seed(*keys: object) -> int:
    """셀 키 → 결정론 부트스트랩 시드(BUILD_SEED + 셀 지문, PYTHONHASHSEED 무관)."""
    blob = ("|".join(str(k) for k in keys)).encode("utf-8")
    digest = int(hashlib.sha256(blob).hexdigest()[:8], 16)
    return (config.BUILD_SEED + digest) % (2**32)


def aggregate_cells(sample: Mapping[str, np.ndarray]) -> List[Dict[str, object]]:
    """온셋 표본 → 셀 행 목록(라벨 h300/l3 × 2축/3축, 새 경계 버킷)."""
    day_ids = sample["day"]
    labels = {
        "h300": (sample["h300_net"], sample["h300_valid"], sample["h300_censored"]),
        "l3": (sample["l3_net_pure"], sample["l3_labeled_pure"],
               np.zeros(sample["day"].size, dtype=bool)),
    }
    rows: List[Dict[str, object]] = []
    for tb in range(len(config.TIME_BUCKETS)):
        for uq in range(4):
            base2 = (sample["time_b"] == tb) & (sample["updown_q"] == uq)
            rows += _cells_for_membership(labels, day_ids, base2,
                                          "time_ud", tb, uq, -1)
            for mc in range(3):
                base3 = base2 & (sample["mktcap_b"] == mc)
                rows += _cells_for_membership(labels, day_ids, base3,
                                              "time_mc_ud", tb, uq, mc)
    return rows


def _cells_for_membership(labels, day_ids, membership, axis_set, tb, uq, mc):
    """한 셀(멤버십)·전 라벨의 행. 3축만 MIN_CELL_N insufficient 판정."""
    out: List[Dict[str, object]] = []
    for label_kind, (net, valid, censored) in labels.items():
        n_used = int((membership & valid).sum())
        insufficient = axis_set == "time_mc_ud" and n_used < _MIN_CELL_N
        seed = _cell_seed(label_kind, axis_set, tb, uq, mc)
        stat = _cell_stats(net, day_ids, membership, valid, censored,
                           seed=seed, insufficient=insufficient)
        stat.update({
            "label_kind": label_kind, "axis_set": axis_set,
            "time_label": config.TIME_BUCKETS[tb], "time_b": tb, "updown_q": uq,
            "mktcap_b": mc, "h": config_v2.H300_HORIZON,
        })
        out.append(stat)
    return out


# ---------------------------------------------------------------------------
# v2 파티션 DB 적재 — 빌드ID v2a_pilot_*, v1 stats_map.db 와 분리.
# ---------------------------------------------------------------------------

_CELL_DB_COLUMNS = (
    "label_kind", "axis_set", "time_label", "time_b", "updown_q", "mktcap_b", "h",
    "n", "n_candidates", "censor_rate", "insufficient",
    "p_net_ge0", "p_net_ge1", "mean_net", "median_net", "q25_net", "q75_net",
    "ci_low", "ci_high", "winrate", "payoff",
)


def write_pilot_db(db_path, cell_rows: List[Dict[str, object]],
                   receipt: Dict[str, object]) -> None:
    """v2a 파일럿 파티션 DB(cells_pilot_v2 + build_receipts_v2) 생성·적재."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("DROP TABLE IF EXISTS cells_pilot_v2")
        cols = ", ".join(f'"{c}" TEXT' if c in ("label_kind", "axis_set")
                         else f'"{c}" REAL' for c in _CELL_DB_COLUMNS)
        conn.execute(f"CREATE TABLE cells_pilot_v2 ({cols})")
        ph = ", ".join("?" for _ in _CELL_DB_COLUMNS)
        conn.executemany(
            f"INSERT INTO cells_pilot_v2 VALUES ({ph})",
            [tuple(r.get(c) for c in _CELL_DB_COLUMNS) for r in cell_rows])
        conn.execute("DROP TABLE IF EXISTS build_receipts_v2")
        rc = ("build_id", "date_start", "date_end", "input_files", "n_onsets",
              "param_sha", "updown_edges", "year_tax", "sell_sha256",
              "gate_pass", "created_at")
        conn.execute(
            f"CREATE TABLE build_receipts_v2 ({', '.join(f'{c} TEXT' for c in rc)})")
        conn.execute(
            f"INSERT INTO build_receipts_v2 VALUES ({', '.join('?' for _ in rc)})",
            tuple(str(receipt.get(c)) for c in rc))
        conn.commit()
    finally:
        conn.close()
