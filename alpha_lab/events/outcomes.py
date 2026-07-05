"""사건 결과 측정·층화·셀 통계·플라시보 — P1과 동일 비용 모형 재사용.

동일 파이프 원칙(실사건·플라시보 2종이 같은 측정 경로를 지난다):

    detect_events → measure_event_outcomes → attach_cells(stratify)
    → aggregate_cells → compare_with_placebo

- 진입: (t_e+1초) 행의 ``매도호가1`` (결측 또는 <=0 → 사건 표본 제외).
- 청산: 각 지평 h∈{60,180,300} 의 (t_e+h초) 행 ``매수호가1``.
  전 지평 행이 존재할 때만 채택(정직 제외 — P1 표본 규약 미러).
- 비용: alpha_lab.dataset.labels 의 ``adverse_fill``(tick2 불리 체결)·
  ``net_rate``(수수료·세금) 를 그대로 재사용한다 — 재구현 금지
  (slippage_profiles 정합은 그 모듈의 대조 테스트로 봉인돼 있다).
- 층화: 시가총액(cap_bins_억) × 시간밴드(band_minutes) × 등락율(chg_bins_pct).
- 셀 통계: min_n 필터 → 일 블록 부트스트랩(stat='mean') EV·95% CI·
  p_one_sided → BH-FDR(q) 생존 마스크 (alpha_lab.stats_common 단일 원본).
- 플라시보 2종: random_time_matched(동일 종목·일 사건 아닌 관측 초 seed 표집),
  shift_plus_60(사건 +60초). 각각 같은 파이프로 측정 후 compare_with_placebo
  가 셀별 {cell, ev, placebo_ev_random, placebo_ev_shift, ...} 로 병합한다.
"""
from __future__ import annotations

import logging
import random
import zlib
from bisect import bisect_right
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from alpha_lab.dataset.labels import adverse_fill, net_rate
from alpha_lab.dataset.schema import as_float
from alpha_lab.events.detectors import ts_shift, ts_to_datetime
from alpha_lab.stats_common import bh_fdr, day_block_bootstrap

__all__ = [
    "DEFAULT_HORIZONS",
    "MIN_N",
    "PLACEBO_SHIFT_SEC",
    "aggregate_cells",
    "attach_cells",
    "compare_with_placebo",
    "measure_event_outcomes",
    "random_time_matched",
    "shift_plus_60",
    "stratify",
]

logger = logging.getLogger(__name__)

DEFAULT_HORIZONS = (60, 180, 300)  # 청산 지평(초) — P1과 동일(봉인).
MIN_N = 200                        # 셀 최소 표본 — 봉인 기본값.
PLACEBO_SHIFT_SEC = 60             # 시프트 플라시보 오프셋(초) — 봉인.

_HMS_MOD = 1_000_000


def measure_event_outcomes(
    events: Sequence[Mapping[str, Any]],
    rows: Mapping[int, Mapping[str, Any]],
    *,
    day: int,
    code: str,
    horizons: Sequence[int] = DEFAULT_HORIZONS,
) -> List[Dict[str, Any]]:
    """사건 목록의 지평별 net_rate 를 측정한다(정직 제외 포함).

    Args:
        events: [{"event": 사건족, "t0": int}] — detect_events 또는 플라시보 출력.
        rows: {int t0: 행 dict} — dataset.reader.load_stock_rows 형태.
        day/code: 표본 메타(일 블록 부트스트랩·식별용).
        horizons: 청산 지평(초).

    Returns:
        [{"event","day","code","t0","row","net"}] — net 은 {h: net_rate},
        row 는 사건 시각 행 참조(층화용, 복사 아님). 진입 초 결측·ask<=0·
        지평 결측·사건 시각 행 결측(시프트 플라시보 케이스)은 표본 제외.
    """
    horizon_tuple = tuple(int(h) for h in horizons)
    samples: List[Dict[str, Any]] = []
    for event in events:
        sample = _outcome_at(
            int(event["t0"]), str(event["event"]), rows,
            day=int(day), code=str(code), horizons=horizon_tuple)
        if sample is not None:
            samples.append(sample)
    logger.debug("measure_event_outcomes: code=%s in=%d kept=%d",
                 code, len(events), len(samples))
    return samples


def _outcome_at(
    t0: int,
    family: str,
    rows: Mapping[int, Mapping[str, Any]],
    *,
    day: int,
    code: str,
    horizons: Tuple[int, ...],
) -> Optional[Dict[str, Any]]:
    """사건 하나의 표본 dict — 규약 위반은 None(정직 제외)."""
    row_at_event = rows.get(t0)
    if row_at_event is None:
        return None  # 층화 불가(사건 시각 행 없음 — 시프트 플라시보 등)
    entry_row = rows.get(ts_shift(t0, 1))
    if entry_row is None:
        return None
    entry_ask = as_float(entry_row.get("매도호가1"))
    if entry_ask <= 0.0:
        return None
    net: Dict[int, float] = {}
    for h in horizons:
        exit_row = rows.get(ts_shift(t0, h))
        if exit_row is None:
            return None  # 전 지평 존재 시에만 채택(P1 미러)
        buy_fill, sell_fill = adverse_fill(entry_ask, as_float(exit_row.get("매수호가1")))
        net[h] = net_rate(buy_fill, sell_fill)
    return {"event": family, "day": day, "code": code, "t0": t0,
            "row": row_at_event, "net": net}


def stratify(
    row_at_event: Mapping[str, Any],
    *,
    cap_bins_억: Sequence[float],
    band_minutes: int = 5,
    chg_bins_pct: Sequence[float],
) -> str:
    """사건 시각 행 → 층화 셀 키 'cap{i}|t{j}|chg{k}'.

    - cap i = bisect_right(cap_bins_억, 시가총액) — 경계값은 상위 빈.
    - t j = (t0 시각 − 09:00:00 경과분) // band_minutes (음수는 0 클램프).
    - chg k = bisect_right(chg_bins_pct, 등락율).
    빈 경계는 오름차순이어야 한다(아니면 ValueError).
    """
    cap_edges = [float(v) for v in cap_bins_억]
    chg_edges = [float(v) for v in chg_bins_pct]
    if cap_edges != sorted(cap_edges) or chg_edges != sorted(chg_edges):
        raise ValueError("빈 경계는 오름차순이어야 한다")
    moment = ts_to_datetime(int(row_at_event["index"]))
    open_moment = moment.replace(hour=9, minute=0, second=0, microsecond=0)
    minutes = max(int((moment - open_moment).total_seconds() // 60), 0)
    band = minutes // int(band_minutes)
    cap_idx = bisect_right(cap_edges, as_float(row_at_event.get("시가총액")))
    chg_idx = bisect_right(chg_edges, as_float(row_at_event.get("등락율")))
    return f"cap{cap_idx}|t{band}|chg{chg_idx}"


def attach_cells(
    samples: Sequence[Mapping[str, Any]],
    *,
    cap_bins_억: Sequence[float],
    band_minutes: int = 5,
    chg_bins_pct: Sequence[float],
) -> List[Dict[str, Any]]:
    """표본의 'row' 를 층화 셀 키 'cell' 로 치환한 새 dict 목록(원본 불변)."""
    out: List[Dict[str, Any]] = []
    for sample in samples:
        cell = stratify(sample["row"], cap_bins_억=cap_bins_억,
                        band_minutes=band_minutes, chg_bins_pct=chg_bins_pct)
        slim = {k: v for k, v in sample.items() if k != "row"}
        slim["cell"] = cell
        out.append(slim)
    return out


def aggregate_cells(
    event_samples: Sequence[Mapping[str, Any]],
    *,
    min_n: int = MIN_N,
    n_boot: int = 1000,
    seed: int = 0,
    fdr_q: float = 0.05,
) -> List[Dict[str, Any]]:
    """(사건족, 셀)별 지평 EV·CI·p·FDR 생존을 계산한다.

    min_n 은 (사건족, 셀) 표본 수 기준(지평은 같은 표본을 공유). 통계는
    stats_common.day_block_bootstrap(stat='mean') — EV=point, 95% CI,
    p_one_sided(mean<=0 방향). BH-FDR 은 전 (사건족,셀,지평) 행에 일괄 적용.
    seed 는 (사건족,셀,지평) 키 crc32 로 파생해 행별 결정성을 보장한다.

    Returns:
        [{"event","cell","horizon","n","ev","ci_low","ci_high","p","fdr_pass"}]
        — (event, cell, horizon) 오름차순.
    """
    groups = _group_by_cell(event_samples)
    rows: List[Dict[str, Any]] = []
    for family, cell in sorted(groups):
        cell_samples = groups[(family, cell)]
        if len(cell_samples) < int(min_n):
            continue
        for horizon in sorted(cell_samples[0]["net"]):
            rows.append(_cell_row(family, cell, int(horizon), cell_samples,
                                  n_boot=int(n_boot), seed=int(seed)))
    if rows:
        survived = bh_fdr([r["p"] for r in rows], q=float(fdr_q))
        rows = [dict(r, fdr_pass=bool(f)) for r, f in zip(rows, survived)]
    logger.debug("aggregate_cells: samples=%d cells=%d rows=%d",
                 len(event_samples), len(groups), len(rows))
    return rows


def _group_by_cell(
    event_samples: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str], List[Mapping[str, Any]]]:
    groups: Dict[Tuple[str, str], List[Mapping[str, Any]]] = {}
    for sample in event_samples:
        groups.setdefault((str(sample["event"]), str(sample["cell"])), []).append(sample)
    return groups


def _cell_row(
    family: str,
    cell: str,
    horizon: int,
    cell_samples: Sequence[Mapping[str, Any]],
    *,
    n_boot: int,
    seed: int,
) -> Dict[str, Any]:
    day_ids = np.asarray([int(s["day"]) for s in cell_samples])
    y = np.asarray([float(s["net"][horizon]) for s in cell_samples], dtype=np.float64)
    boot = day_block_bootstrap(
        day_ids, y, np.ones(y.shape[0], dtype=bool),
        n_boot=n_boot, seed=_derive_seed(seed, family, cell, horizon), stat="mean")
    return {"event": family, "cell": cell, "horizon": int(horizon),
            "n": int(y.shape[0]), "ev": float(boot["point"]),
            "ci_low": float(boot["ci_low"]), "ci_high": float(boot["ci_high"]),
            "p": float(boot["p_one_sided"])}


def _derive_seed(seed: int, family: str, cell: str, horizon: int) -> int:
    """행별 결정적 부트스트랩 seed — 전달 seed와 셀 키 crc32의 XOR."""
    key = f"{family}|{cell}|{horizon}".encode("utf-8")
    return (int(seed) & 0xFFFFFFFF) ^ zlib.crc32(key)


def random_time_matched(
    events: Sequence[Mapping[str, Any]],
    rows: Mapping[int, Mapping[str, Any]],
    *,
    seed: int,
) -> List[Dict[str, Any]]:
    """플라시보 1 — 동일 종목·일에서 사건이 아닌 관측 초를 seed 표집한다.

    후보 = rows 의 관측 초 − 사건 t0 전체. 사건 수만큼(후보 부족 시 후보
    수만큼) 비복원 표집해 사건족 라벨을 순서대로 이어받는다. 같은 seed 는
    같은 결과(재현성 규율 — seed 필수 키워드).
    """
    event_ts = {int(e["t0"]) for e in events}
    candidates = sorted(int(t) for t in rows if int(t) not in event_ts)
    if not candidates or not events:
        return []
    rng = random.Random(int(seed))
    k = min(len(events), len(candidates))
    picks = rng.sample(candidates, k)
    return [{"event": str(e["event"]), "t0": int(t)}
            for e, t in zip(list(events)[:k], picks)]


def shift_plus_60(events: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """플라시보 2 — 각 사건을 +60초(PLACEBO_SHIFT_SEC 봉인) 시프트한 사본."""
    return [{"event": str(e["event"]), "t0": ts_shift(int(e["t0"]), PLACEBO_SHIFT_SEC)}
            for e in events]


def compare_with_placebo(
    real_cells: Sequence[Mapping[str, Any]],
    placebo_random_cells: Sequence[Mapping[str, Any]],
    placebo_shift_cells: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """실사건 셀 행에 플라시보 2종 EV를 병합한 새 목록(원본 불변).

    키 (event, cell, horizon) 로 대응시키며, 해당 플라시보 셀이 없으면
    nan — '플라시보 표본이 그 셀에서 측정 불가/미달'을 명시적으로 남긴다.
    반환 행: 실측 행 전 키 + placebo_ev_random + placebo_ev_shift.
    """
    random_ev = _ev_by_key(placebo_random_cells)
    shift_ev = _ev_by_key(placebo_shift_cells)
    out: List[Dict[str, Any]] = []
    for row in real_cells:
        key = (str(row["event"]), str(row["cell"]), int(row["horizon"]))
        merged = dict(row)
        merged["placebo_ev_random"] = random_ev.get(key, float("nan"))
        merged["placebo_ev_shift"] = shift_ev.get(key, float("nan"))
        out.append(merged)
    return out


def _ev_by_key(
    cells: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, int], float]:
    return {(str(r["event"]), str(r["cell"]), int(r["horizon"])): float(r["ev"])
            for r in cells}
