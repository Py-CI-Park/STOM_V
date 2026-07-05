"""P3 MCL 오프라인 스크리닝 코어 — 보수 설계 확정안 구현 (docs-first, ML-free).

설계 원본: docs/research/condition_research/plans/
2026-07-05_p3_mcl_remediation_preregistration_draft.md — 본 모듈은 그 확정
사항(§3 A안 라벨 교체, §4 dedup 4-튜플, §6.3 시행 통계, §7 판정 보정)의
코드 구현이다. 실 CSV 스캔·tick 재조인 실행·봉인 파일 생성
(p3_mcl_preregistration_v1.json)은 다음 라운드 소관 — 여기서는 순수 함수
코어와 합성 데이터 테스트만 제공한다(엔진 0회·DB 접근 0회).

세 기둥(임무 계약):
(a) 라벨 교체(§3.2 A안) — 절단된 R_MFE/MAE 대신 alpha_lab.dataset.labels 의
    고정지평 net_rate 라벨을 진입 시각 tick 재조인 행으로 재계산한다.
    표적 6종 = L1_60/L1_180/L1_300(l1_label), L2(l2_triple_barrier),
    MFE_300/MAE_300(고정창 300초 경로 net_rate 극값 — "L2가 이미 순회하는
    경로의 부산물" 조항 그대로, dataset.reader._bid_path 와 동일한
    오프셋 1..300 관측 초 규약).
(b) 거래 dedup(§4) — identity 4-튜플(전략명, 종목코드, 진입일자, 진입시각)과
    중복 제거는 alpha_lab.distill.ledger_wiring(identity/dedup_records)
    재사용. C1/C2/C4 충돌 감사는 §4.2 규칙. C3(동명이식 sha 분리)은
    DB_BACKTEST 대조가 필요한 상류(스캔 러너) 소관 — 본 모듈 입력의
    전략명은 이미 분리 완료됐다고 전제한다.
(c) 분위수 lift 스크리닝(§6.3) — 통계는 alpha_lab.stats_common
    (lift/day_block_bootstrap/bh_fdr)만 사용(재구현 금지), ML-free.

시행(trial) 규약 — 봉인 확정 대상 기본값(§8 봉인 전 초안 지위):
- 시행 = (피처,윈도우) × 라벨 표적 1건. 표적은 전부 0/1 지표율로 조작화한다
  (lift = 양성률 배율이라는 stats_common 정의 유지): L1_h 그대로,
  L2 는 TP first-touch(=1) 지표, MFE_300 은 극값 ≥ L1_NET_THRESHOLD 도달
  지표, MAE_300 은 풀 하위 MAE_TAIL_PCT% 심꼬리 소속 지표 — §7-1 의
  "MAE P95 억제형"은 심꼬리 소속률 lift < 1 의 CI 분리로 판정한다.
- 4분위 셀: 경계 = 풀 분위수, 경계값과 같은 값은 상위 빈
  (bisect_right — events.stratify 규약 정합). 셀당 n < MIN_CELL_N 이면
  그 시행은 '판정 불가'(p_trial=1.0 로 FDR 모수에 잔류 — 보수, §6.3 의
  "150 시행 전체에 일괄" 유지).
- 시행 p = min(1, 2×min(p_Q1, p_Q4)) — 양끝 셀 단측 p 의 2배
  (상위/하위 방향 쇼핑에 대한 본페로니 방어, §7-1 "상위(또는 하위)").
- 단조성 = 셀 lift 약단조 AND 양끝 상이. 연도 폴드(§7-4 보정) =
  부호 일치 연도 비율 ≥ 2/3 AND 불일치 연도 CI 가 lift 널값 1을 포함.
- BH-FDR 은 apply_fdr 로 전 시행 일괄(q=FDR_Q=0.05 — §7-2 강화 통일).
- apply_fdr 의 survivor 는 FDR·단조·연도 3게이트만 반영한다. 공식 성공
  판정(§7 원문)은 이중 플라시보 소멸 게이트(다음 라운드)까지 통과한
  플래그로 screen_verdict 를 호출해야 한다.
"""
from __future__ import annotations

import logging
import math
import zlib
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from alpha_lab.dataset.labels import (
    L1_NET_THRESHOLD,
    TIMEOUT_SEC,
    adverse_fill,
    l1_label,
    l2_triple_barrier,
    net_rate,
)
from alpha_lab.dataset.schema import as_float
from alpha_lab.distill.ledger_wiring import dedup_records, identity
from alpha_lab.events.detectors import ts_shift
from alpha_lab.stats_common import bh_fdr, day_block_bootstrap

__all__ = [
    "C1_RETURN_TOL",
    "DISCOVERY_END_DAY",
    "ENTRY_HMS_MAX",
    "ENTRY_HMS_MIN",
    "FDR_Q",
    "L1_HORIZONS",
    "LABEL_TARGETS",
    "MAE_TAIL_PCT",
    "MAE_TARGET",
    "MFE_TARGET",
    "MIN_CELL_N",
    "MIN_POOL_N",
    "N_QUANTILES",
    "PATH_WINDOW_SEC",
    "TRIAL_INSUFFICIENT",
    "TRIAL_NO_POSITIVES",
    "TRIAL_OK",
    "VALID_TRIAL_MIN_FRACTION",
    "YEAR_AGREE_MIN_FRACTION",
    "apply_fdr",
    "build_targets",
    "dedup_trades",
    "filter_discovery",
    "quantile_cells",
    "relabel_trade",
    "relabel_trades",
    "screen_trials",
    "screen_verdict",
]

logger = logging.getLogger(__name__)

# --- 라벨 규약(§3.2 A안 — 봉인 확정 대상) --------------------------------
L1_HORIZONS: Tuple[int, ...] = (60, 180, 300)   # P1/P2 와 동일 지평(초).
PATH_WINDOW_SEC = TIMEOUT_SEC                    # 고정창 300초 — L2 경로 재사용.
MFE_TARGET = "MFE_300"
MAE_TARGET = "MAE_300"
LABEL_TARGETS: Tuple[str, ...] = (
    "L1_60", "L1_180", "L1_300", "L2", MFE_TARGET, MAE_TARGET,
)
MAE_TAIL_PCT = 5.0  # MAE 심꼬리 분위(하위 5% = 'P95 손실 깊이' 대응, §7-1).

# 진입 적격 시각(HHMMSS int): tick DB 커버리지 시작 09:00:01(§3.2),
# 컷오프 = 그리드 끝 09:30:00 − PATH_WINDOW_SEC(300초) = 09:25:00
# (절단 방지 그리드 규칙 재사용 — reader 규약과 동일 파생).
ENTRY_HMS_MIN = 90001
ENTRY_HMS_MAX = 92500

# --- dedup·발견창 규약(§4 — 봉인 확정 대상) ------------------------------
DISCOVERY_END_DAY = "20241231"  # 발견창 상한(§4.3-③) — 검증창 접촉 금지.
C1_RETURN_TOL = 1e-9            # C1 완전 중복 판정: 수익률 절대차 허용(§4.2).

# --- 시행 판정 규약(§7 보정 — 봉인 확정 대상) ----------------------------
MIN_POOL_N = 2000               # dedup 후 풀 최소 표본(§7-3).
MIN_CELL_N = 500                # 분위수 셀당 최소 표본(§7-3).
FDR_Q = 0.05                    # BH-FDR q — 강화 통일(§7-2).
N_QUANTILES = 4                 # 4분위(§6.3).
YEAR_AGREE_MIN_FRACTION = 2.0 / 3.0   # 연도 부호 일치 최소 비율(§7-4).
VALID_TRIAL_MIN_FRACTION = 0.5        # 유효 시행 비율 하한(§7-5-iii 과반).

TRIAL_OK = "ok"
TRIAL_INSUFFICIENT = "insufficient_cell"
TRIAL_NO_POSITIVES = "no_positives"

_VERDICTS = ("success", "abandon", "inconclusive", "below_threshold")


# ---------------------------------------------------------------------------
# (b) 발견창 필터 + 거래 dedup — ledger_wiring 재사용.
# ---------------------------------------------------------------------------
def filter_discovery(
    records: Iterable[Mapping], *, end_day: str = DISCOVERY_END_DAY
) -> Tuple[List[Mapping], int]:
    """발견창 필터(§4.3-③): 진입일자 <= end_day 만 통과 — (통과, 제외 수).

    end_day 는 8자리 YYYYMMDD 문자열(경계 포함). 레코드는 변형하지 않는다
    (참조 반환). identity 필드 결측 레코드는 ledger_wiring.identity 계약대로
    ValueError.
    """
    if not (isinstance(end_day, str) and len(end_day) == 8 and end_day.isdigit()):
        raise ValueError(f"end_day 는 8자리 YYYYMMDD 문자열이어야 한다: {end_day!r}")
    kept: List[Mapping] = []
    dropped = 0
    for rec in records:
        if identity(rec)[2] <= end_day:  # 8자리 문자열 비교 = 수치 비교.
            kept.append(rec)
        else:
            dropped += 1
    logger.info("filter_discovery end_day=%s kept=%d dropped=%d",
                end_day, len(kept), dropped)
    return kept, dropped


def _is_c1_duplicate(dup: Mapping, rep: Mapping) -> bool:
    """C1(완전 중복) 판정(§4.2): 수익률 절대차 <= 1e-9 AND 매도시간 동일.

    어느 한쪽이라도 매도시간·수익률이 없으면 완전 중복을 확인할 수 없으므로
    C2 로 분류한다(보수 — A안 라벨 하에서 분류는 감사 카운트에만 영향).
    """
    ret_dup, ret_rep = dup.get("수익률"), rep.get("수익률")
    sell_dup, sell_rep = dup.get("매도시간"), rep.get("매도시간")
    if ret_dup is None or ret_rep is None or sell_dup is None or sell_rep is None:
        return False
    return abs(float(ret_dup) - float(ret_rep)) <= C1_RETURN_TOL and sell_dup == sell_rep


def _c4_poisoned_keys(
    groups: Mapping[Tuple[str, str, str, str], List[Mapping]], file_key: str
) -> set:
    """C4(동일 파일 내 동일 4-튜플 2행 — 데이터 이상) identity 집합(§4.2).

    파일 태그(file_key)가 있는 레코드끼리만 판정한다 — ledger_wiring 의
    source 는 전략명이라(파일 타임스탬프 제거) 같은 전략의 정상 재실행
    CSV(C1)와 같은 파일 내 이상(C4)을 구분할 수 없기 때문이다. 태그가 없는
    입력에서는 C4 를 감지하지 않는다(스캔 러너가 다음 라운드에 태그 부착).
    """
    poisoned = set()
    for key, members in groups.items():
        tags = [m.get(file_key) for m in members]
        tags = [t for t in tags if t not in (None, "")]
        if len(tags) != len(set(tags)):
            poisoned.add(key)
    return poisoned


def dedup_trades(
    records: Iterable[Mapping], *, file_key: str = "source_file"
) -> Tuple[List[dict], Dict[str, int]]:
    """identity 4-튜플 거래 dedup(§4) — (고유 레코드, 충돌 감사 카운트).

    - identity·중복 제거는 ledger_wiring 의 identity/dedup_records 재사용.
    - C4: 같은 파일 태그 안에서 동일 4-튜플 2행 → 그 4-튜플 전체 제외(보수).
    - C1/C2: 교차 런 중복 — 대표 1건(입력 순서 최초 등장 = dedup_records
      first-wins). 봉인된 C2 대표 우선순위(동결 프로파일 > save_time 최신 >
      파일명 사전순)는 호출측이 입력 순서로 구현한다(스캔 러너가 CSV 목록을
      우선순위로 정렬해 공급). A안 라벨 교체 하에서 대표 선택은 라벨에 영향
      없음(§4.1) — 분류는 감사 카운트다.
    - C3(동명이식)은 상류 소관 — 전략명은 이미 sha 분리 완료 전제.

    감사 카운트 키: input_rows / identity_groups / file_tagged_rows /
    c1_rows_dropped / c2_rows_dropped / c4_identities / c4_rows_dropped /
    unique_rows. 항등식 input_rows == unique_rows + c1 + c2 + c4_rows 를
    내부 검증한다(위반 시 계약 드리프트 → RuntimeError).
    """
    recs = list(records)
    groups: Dict[Tuple[str, str, str, str], List[Mapping]] = {}
    for rec in recs:
        groups.setdefault(identity(rec), []).append(rec)

    poisoned = _c4_poisoned_keys(groups, file_key)
    c4_rows = sum(len(groups[key]) for key in poisoned)
    clean = [rec for rec in recs if identity(rec) not in poisoned]
    unique, dup_count = dedup_records(clean)

    c1 = c2 = 0
    for key, members in groups.items():
        if key in poisoned or len(members) < 2:
            continue
        rep = members[0]
        for dup in members[1:]:
            if _is_c1_duplicate(dup, rep):
                c1 += 1
            else:
                c2 += 1
    if dup_count != c1 + c2:
        raise RuntimeError(
            f"dedup 감사 항등식 위반: dup={dup_count} != c1={c1}+c2={c2}"
        )
    audit = {
        "input_rows": len(recs),
        "identity_groups": len(groups),
        "file_tagged_rows": sum(1 for r in recs if r.get(file_key) not in (None, "")),
        "c1_rows_dropped": c1,
        "c2_rows_dropped": c2,
        "c4_identities": len(poisoned),
        "c4_rows_dropped": c4_rows,
        "unique_rows": len(unique),
    }
    logger.info("dedup_trades %s", audit)
    return unique, audit


# ---------------------------------------------------------------------------
# (a) 라벨 교체 — 진입 시각 tick 재조인 재라벨(labels.py 재사용).
# ---------------------------------------------------------------------------
def _bid_path(rows: Mapping[int, Mapping], t0: int) -> List[Tuple[int, float]]:
    """t0+1..t0+PATH_WINDOW_SEC 관측 초의 (오프셋, 매수호가1) 경로.

    dataset.reader._bid_path 와 동일 규약(오프셋 1..300 포함, 결측 초 제외)
    — L2 와 MFE/MAE 가 같은 경로를 공유한다(§3.2 "부산물" 조항).
    """
    path: List[Tuple[int, float]] = []
    for offset in range(1, PATH_WINDOW_SEC + 1):
        row = rows.get(ts_shift(t0, offset))
        if row is not None:
            path.append((offset, as_float(row.get("매수호가1"))))
    return path


def relabel_trade(
    rows: Optional[Mapping[int, Mapping]],
    t0: int,
    *,
    horizons: Sequence[int] = L1_HORIZONS,
) -> Tuple[Optional[Dict[str, float]], str]:
    """챔피언 거래 1건 재라벨(§3.2 A안) — (라벨 dict | None, 제외 사유).

    Args:
        rows: {int YYYYMMDDHHMMSS: 행 dict} — dataset.reader.load_stock_rows
            형태. None 이면 재조인 불가("rows_missing").
        t0: 진입 신호 초(매수시간) int YYYYMMDDHHMMSS.
        horizons: L1 지평(초) — 전부 PATH_WINDOW_SEC 이하여야 한다.

    Returns:
        (labels, "ok") 또는 (None, 사유). labels 키 = L1_{h}…, L2,
        MFE_300/MAE_300. 사유 ∈ {rows_missing, time_ineligible,
        entry_missing, entry_ask_nonpositive, horizon_missing, path_empty}.
        진입 = (t0+1초) 매도호가1(결측·<=0 제외), L1 청산 = (t0+h초)
        매수호가1(전 지평 관측 시에만 채택), MFE/MAE = 경로 net_rate 극값.
    """
    horizon_tuple = tuple(int(h) for h in horizons)
    if not horizon_tuple or max(horizon_tuple) > PATH_WINDOW_SEC:
        raise ValueError(f"horizons 는 1..{PATH_WINDOW_SEC} 초여야 한다: {horizon_tuple}")
    if rows is None:
        return None, "rows_missing"
    hms = int(t0) % 1_000_000
    if not (ENTRY_HMS_MIN <= hms <= ENTRY_HMS_MAX):
        return None, "time_ineligible"
    entry_row = rows.get(ts_shift(int(t0), 1))
    if entry_row is None:
        return None, "entry_missing"
    entry_ask = as_float(entry_row.get("매도호가1"))
    if entry_ask <= 0.0:
        return None, "entry_ask_nonpositive"
    exit_bids: List[float] = []
    for h in horizon_tuple:
        exit_row = rows.get(ts_shift(int(t0), h))
        if exit_row is None:
            return None, "horizon_missing"  # 전 지평 관측 시에만 채택(§3.2).
        exit_bids.append(as_float(exit_row.get("매수호가1")))
    path = _bid_path(rows, int(t0))
    if not path:
        return None, "path_empty"
    rates = [net_rate(*adverse_fill(entry_ask, bid)) for _, bid in path]
    labels: Dict[str, float] = {
        f"L1_{h}": float(l1_label(entry_ask, bid))
        for h, bid in zip(horizon_tuple, exit_bids)
    }
    labels["L2"] = float(l2_triple_barrier(entry_ask, path))
    labels[MFE_TARGET] = float(max(rates))
    labels[MAE_TARGET] = float(min(rates))
    return labels, "ok"


def relabel_trades(
    records: Sequence[Mapping],
    rows_by_day_code: Mapping[Tuple[str, str], Mapping[int, Mapping]],
    *,
    horizons: Sequence[int] = L1_HORIZONS,
) -> Tuple[List[dict], Dict[str, int]]:
    """dedup 후 챔피언 거래들을 일괄 재라벨 — (표본 목록, 제외 사유 카운트).

    rows_by_day_code 키 = (진입일자 8자리, 종목코드) — 종목명→코드 매핑과
    테이블 실재 검증(§4.1)은 호출측(다음 라운드 스캔 러너) 소관이며, 키
    부재는 "rows_missing" 으로 정직 카운트한다. 표본 dict 는
    {strategy, code, day(int), t0(int)} + 라벨 6종.
    """
    counts: Dict[str, int] = {
        "input": len(records), "ok": 0, "rows_missing": 0, "time_ineligible": 0,
        "entry_missing": 0, "entry_ask_nonpositive": 0, "horizon_missing": 0,
        "path_empty": 0,
    }
    samples: List[dict] = []
    for rec in records:
        strategy, code, day, hms = identity(rec)
        t0 = int(day + hms)
        labels, reason = relabel_trade(
            rows_by_day_code.get((day, code)), t0, horizons=horizons
        )
        counts[reason] += 1
        if labels is not None:
            samples.append(
                {"strategy": strategy, "code": code, "day": int(day), "t0": t0, **labels}
            )
    logger.info("relabel_trades %s", counts)
    return samples, counts


def build_targets(
    samples: Sequence[Mapping],
    *,
    mfe_threshold: float = L1_NET_THRESHOLD,
    mae_tail_pct: float = MAE_TAIL_PCT,
) -> Tuple[Dict[str, np.ndarray], Dict[str, float]]:
    """라벨 6종 → 0/1 표적 벡터 + 조작화 임계 기록 — (targets, thresholds).

    - L1_60/180/300: 라벨 그대로(이미 0/1).
    - L2: TP first-touch(라벨 == 1) 지표.
    - MFE_300: 경로 극값 >= mfe_threshold(기본 L1_NET_THRESHOLD) 도달 지표.
    - MAE_300: 경로 극값 <= 풀 하위 mae_tail_pct% 분위값 — 심꼬리 소속 지표
      (§7-1 "MAE P95 억제형"의 조작 정의; 억제 = 셀 lift < 1 CI 분리).
    thresholds 는 감사·봉인 기록용 {MFE_300: 임계, MAE_300: 심꼬리 분위값}.
    """
    if not samples:
        raise ValueError("samples 가 비었다 — 빈 풀에는 표적을 정의할 수 없다")
    if not (0.0 < float(mae_tail_pct) < 100.0):
        raise ValueError(f"mae_tail_pct 는 (0,100) 이어야 한다: {mae_tail_pct}")

    def _column(name: str) -> np.ndarray:
        try:
            return np.asarray([float(s[name]) for s in samples], dtype=np.float64)
        except KeyError as exc:
            raise ValueError(f"표본에 라벨이 없다: {name}") from exc

    targets: Dict[str, np.ndarray] = {
        f"L1_{h}": _column(f"L1_{h}") for h in L1_HORIZONS
    }
    targets["L2"] = (_column("L2") == 1.0).astype(np.float64)
    mfe = _column(MFE_TARGET)
    mae = _column(MAE_TARGET)
    mae_tail_value = float(np.quantile(mae, float(mae_tail_pct) / 100.0))
    targets[MFE_TARGET] = (mfe >= float(mfe_threshold)).astype(np.float64)
    targets[MAE_TARGET] = (mae <= mae_tail_value).astype(np.float64)
    thresholds = {MFE_TARGET: float(mfe_threshold), MAE_TARGET: mae_tail_value}
    return targets, thresholds


# ---------------------------------------------------------------------------
# (c) 분위수 lift 스크리닝 — stats_common 재사용(재구현 금지).
# ---------------------------------------------------------------------------
def quantile_cells(
    values: Sequence[float], n_quantiles: int = N_QUANTILES
) -> Tuple[np.ndarray, np.ndarray]:
    """유한값 벡터 → (셀 인덱스 0..n_quantiles-1, 분위 경계값).

    경계값과 같은 값은 상위 빈(searchsorted side='right' —
    events.stratify 의 bisect_right 규약 정합). 경계는 Phase 2 번역의
    '분위수 경계값 고정' 임계 원천이므로 반환에 포함한다. 결측(NaN)은
    호출 전에 제거해야 한다(시행별 정직 제외 규율 — ValueError).
    """
    vals = np.asarray(values, dtype=np.float64)
    if vals.ndim != 1 or vals.size == 0:
        raise ValueError("values 는 비어있지 않은 1차원 벡터여야 한다")
    if not np.all(np.isfinite(vals)):
        raise ValueError("values 에 비유한값 — 결측은 시행별로 먼저 제거하라")
    if int(n_quantiles) < 2:
        raise ValueError(f"n_quantiles 는 2 이상이어야 한다: {n_quantiles}")
    probs = np.arange(1, int(n_quantiles)) / float(n_quantiles)
    edges = np.quantile(vals, probs)
    cells = np.searchsorted(edges, vals, side="right").astype(np.int64)
    return cells, edges


def _derive_seed(seed: int, *parts: str) -> int:
    """결정적 부트스트랩 seed — 전달 seed 와 키 crc32 의 XOR(events 규약 미러)."""
    key = "|".join(parts).encode("utf-8")
    return (int(seed) & 0xFFFFFFFF) ^ zlib.crc32(key)


def _sign_vs_one(point: float) -> int:
    """lift 점추정의 널값(1.0) 대비 부호 — nan/정확히 1 은 0."""
    if not math.isfinite(point):
        return 0
    if point > 1.0:
        return 1
    if point < 1.0:
        return -1
    return 0


def _year_stability(
    days: np.ndarray,
    y: np.ndarray,
    extreme_mask: np.ndarray,
    *,
    ref_point: float,
    n_boot: int,
    seed: int,
    feature: str,
    target: str,
) -> Dict[str, object]:
    """연도 폴드 부호 안정(§7-4 보정) — {year_lifts, year_stable}.

    극단 셀 lift 의 연도별 재계산: 부호 일치 연도 비율 >= 2/3 AND 불일치
    연도의 CI 가 널값 1을 포함(유의한 역부호 불허)이면 안정. 기준 부호가
    0(널/nan)이면 불안정(보수). 연도 = 진입일자 // 10000.
    """
    ref_sign = _sign_vs_one(ref_point)
    year_of = days // 10000
    years = [int(v) for v in np.unique(year_of)]
    year_lifts: Dict[str, float] = {}
    agree = 0
    significant_reverse = False
    for year in years:
        sel = year_of == year
        boot = day_block_bootstrap(
            days[sel], y[sel], extreme_mask[sel],
            n_boot=n_boot, seed=_derive_seed(seed, feature, target, f"year{year}"),
            stat="lift",
        )
        point = float(boot["point"])
        year_lifts[str(year)] = point
        if _sign_vs_one(point) == ref_sign and ref_sign != 0:
            agree += 1
            continue
        lo, hi = float(boot["ci_low"]), float(boot["ci_high"])
        ci_contains_null = (
            not (math.isfinite(lo) and math.isfinite(hi)) or lo <= 1.0 <= hi
        )
        if not ci_contains_null:
            significant_reverse = True
    stable = (
        ref_sign != 0
        and not significant_reverse
        and (agree / len(years)) >= YEAR_AGREE_MIN_FRACTION - 1e-12
    )
    return {"year_lifts": year_lifts, "year_stable": bool(stable)}


def _trial_base(
    feature: str, target: str, *, n: int, n_missing: int, positives: float,
    edges: np.ndarray, cell_n: np.ndarray,
) -> Dict[str, object]:
    """시행 행 공통 골격 — verdict 무관 동일 스키마(JSON 직렬화 가능)."""
    return {
        "feature": feature,
        "target": target,
        "n": int(n),
        "n_missing": int(n_missing),
        "positives": int(positives),
        "base_rate": float(positives / n) if n else float("nan"),
        "edges": [float(e) for e in edges],
        "cell_n": [int(c) for c in cell_n],
        "verdict": TRIAL_OK,
        "cells": [],
        "direction": None,
        "monotone": False,
        "p_trial": 1.0,
        "extreme_cell": None,
        "opposite_cell": None,
        "year_lifts": {},
        "year_stable": False,
        "mae_suppressor": False,
    }


def _bootstrap_cells(
    ds: np.ndarray,
    ys: np.ndarray,
    cells: np.ndarray,
    cell_n: np.ndarray,
    *,
    n_boot: int,
    seed: int,
    feature: str,
    target: str,
    n_quantiles: int,
) -> List[Dict[str, float]]:
    """분위수 셀별 일 블록 부트스트랩(stat='lift') — 셀 행 목록.

    셀 k 의 seed 는 (피처,표적,셀) crc32 파생으로 행별 결정적이다.
    """
    cell_rows: List[Dict[str, float]] = []
    for k in range(n_quantiles):
        boot = day_block_bootstrap(
            ds, ys, cells == k,
            n_boot=n_boot, seed=_derive_seed(seed, feature, target, str(k)),
            stat="lift",
        )
        cell_rows.append({
            "cell": k, "n": int(cell_n[k]), "lift": float(boot["point"]),
            "ci_low": float(boot["ci_low"]), "ci_high": float(boot["ci_high"]),
            "p": float(boot["p_one_sided"]),
        })
    return cell_rows


def _screen_one(
    feature: str,
    x: np.ndarray,
    target: str,
    y: np.ndarray,
    days: np.ndarray,
    *,
    n_boot: int,
    seed: int,
    min_cell_n: int,
    n_quantiles: int,
) -> Dict[str, object]:
    """시행 1건 = (피처,윈도우) × 표적 — 셀 통계·단조·p_trial·연도 안정."""
    valid = np.isfinite(x)
    xs, ys, ds = x[valid], y[valid], days[valid]
    positives = float(ys.sum())
    if xs.size == 0:
        cells, edges = np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.float64)
    else:
        cells, edges = quantile_cells(xs, n_quantiles)
    cell_n = np.bincount(cells, minlength=n_quantiles)
    row = _trial_base(
        feature, target, n=xs.size, n_missing=int(x.size - xs.size),
        positives=positives, edges=edges, cell_n=cell_n,
    )
    if xs.size == 0 or int(cell_n.min()) < int(min_cell_n):
        row["verdict"] = TRIAL_INSUFFICIENT  # 셀 최소 표본 미달 → 판정 불가(§7-3).
        return row
    if positives <= 0.0:
        row["verdict"] = TRIAL_NO_POSITIVES  # 양성 0 → lift 정의 불가(정직 제외).
        return row

    cell_rows = _bootstrap_cells(
        ds, ys, cells, cell_n,
        n_boot=n_boot, seed=seed, feature=feature, target=target,
        n_quantiles=int(n_quantiles),
    )
    points = [c["lift"] for c in cell_rows]
    diffs = np.diff(points)
    direction = "up" if points[-1] >= points[0] else "down"
    extreme = int(n_quantiles) - 1 if direction == "up" else 0
    opposite = 0 if direction == "up" else int(n_quantiles) - 1
    year = _year_stability(
        ds, ys, cells == extreme, ref_point=points[extreme],
        n_boot=n_boot, seed=seed, feature=feature, target=target,
    )
    opp_hi = cell_rows[opposite]["ci_high"]
    row.update({
        "cells": cell_rows,
        "direction": direction,
        "monotone": bool(
            (np.all(diffs >= 0.0) or np.all(diffs <= 0.0))
            and points[-1] != points[0]
        ),
        "p_trial": float(min(1.0, 2.0 * min(cell_rows[0]["p"], cell_rows[-1]["p"]))),
        "extreme_cell": extreme,
        "opposite_cell": opposite,
        "year_lifts": year["year_lifts"],
        "year_stable": year["year_stable"],
        "mae_suppressor": bool(
            target == MAE_TARGET and math.isfinite(opp_hi) and opp_hi < 1.0
        ),
    })
    return row


def _validate_screen_inputs(
    features: Mapping[str, Sequence[float]],
    targets: Mapping[str, Sequence[float]],
    days: np.ndarray,
) -> None:
    if days.ndim != 1:
        raise ValueError("day_ids 는 1차원이어야 한다")
    for name, vec in features.items():
        arr = np.asarray(vec, dtype=np.float64)
        if arr.ndim != 1 or arr.shape[0] != days.shape[0]:
            raise ValueError(f"피처 {name!r} 길이가 day_ids 와 다르다")
    for name, vec in targets.items():
        arr = np.asarray(vec, dtype=np.float64)
        if arr.ndim != 1 or arr.shape[0] != days.shape[0]:
            raise ValueError(f"표적 {name!r} 길이가 day_ids 와 다르다")
        if not np.all(np.isfinite(arr)) or not np.all(np.isin(arr, (0.0, 1.0))):
            raise ValueError(f"표적 {name!r} 은 0/1 벡터여야 한다 — build_targets 를 거쳐라")


def screen_trials(
    features: Mapping[str, Sequence[float]],
    targets: Mapping[str, Sequence[float]],
    day_ids: Sequence[int],
    *,
    n_boot: int = 1000,
    seed: int = 0,
    min_cell_n: int = MIN_CELL_N,
    n_quantiles: int = N_QUANTILES,
) -> List[dict]:
    """전 시행 스크리닝(§6.3) — 피처×표적 순서의 시행 행 목록(FDR 전).

    features 값의 NaN 은 '그 (피처,윈도우) 시행에서만 표본 제외'(§5 결측
    규칙 — n_missing 카운트), targets 는 0/1 완전 벡터여야 한다. 시행 p 는
    양끝 셀 단측 p 의 2배(min 1.0), 부트스트랩 seed 는 (피처,표적,셀)
    crc32 파생으로 행별 결정적. FDR 은 apply_fdr 에서 전 시행 일괄 —
    150 시행을 여러 호출로 나눠 계산해도 한 번에 보정할 수 있게 분리했다.
    """
    days = np.asarray(day_ids)
    _validate_screen_inputs(features, targets, days)
    rows: List[dict] = []
    for fname, fvec in features.items():
        x = np.asarray(fvec, dtype=np.float64)
        for tname, tvec in targets.items():
            rows.append(_screen_one(
                fname, x, tname, np.asarray(tvec, dtype=np.float64), days,
                n_boot=int(n_boot), seed=int(seed),
                min_cell_n=int(min_cell_n), n_quantiles=int(n_quantiles),
            ))
    logger.info(
        "screen_trials features=%d targets=%d trials=%d n=%d",
        len(features), len(targets), len(rows), int(days.shape[0]),
    )
    return rows


def apply_fdr(trial_rows: Sequence[Mapping], *, q: float = FDR_Q) -> List[dict]:
    """BH-FDR 일괄 적용(§6.3) — fdr_pass·survivor 를 부착한 새 행 목록.

    p_trial 전체(판정 불가 시행의 p=1.0 포함 — 모수 고정, 보수)에
    stats_common.bh_fdr 를 1회 적용한다. survivor = FDR 생존 ∧ 단조 ∧
    연도 안정 ∧ verdict=='ok' — 플라시보 소멸 게이트(§6.3 이중 플라시보)는
    다음 라운드에서 이 플래그에 추가로 결합해야 공식 성공 판정이 된다.
    """
    rows = [dict(r) for r in trial_rows]
    if not rows:
        return []
    mask = bh_fdr([float(r["p_trial"]) for r in rows], q=float(q))
    out = []
    for row, passed in zip(rows, mask):
        survivor = bool(
            passed and row["monotone"] and row["year_stable"]
            and row["verdict"] == TRIAL_OK
        )
        out.append({**row, "fdr_pass": bool(passed), "survivor": survivor})
    logger.info("apply_fdr trials=%d q=%.3f fdr_pass=%d survivors=%d",
                len(out), q, int(mask.sum()), sum(r["survivor"] for r in out))
    return out


def screen_verdict(
    trial_rows: Sequence[Mapping], *, pool_n: int, min_pool_n: int = MIN_POOL_N
) -> Dict[str, object]:
    """판정 3분지 + 기준미달(§7-5) — 카운트와 verdict 문자열.

    - inconclusive(판정 불가): pool_n < min_pool_n 또는 유효 시행 비율 <
      1/2(시행 과반 탈락) 또는 시행 0건 — 포기 결론을 기록하지 않는다.
    - success(성공): survivor >= 2 AND 그중 mae_suppressor >= 1.
    - abandon(포기): 시행은 유효했으나 survivor 0 — 'orderbook 축 엣지
      없음' 결론 기록 대상.
    - below_threshold: 그 사이(성공 아님·포기 결론도 아님).
    trial_rows 는 apply_fdr 를 거쳐야 하며(survivor 키), 공식 판정에는
    플라시보 게이트 결합 후의 survivor 로 호출해야 한다(§7 원문).
    """
    rows = list(trial_rows)
    for row in rows:
        if "survivor" not in row:
            raise ValueError("apply_fdr 미적용 시행 행 — FDR 을 먼저 일괄 적용하라")
    trials = len(rows)
    valid = sum(1 for r in rows if r["verdict"] == TRIAL_OK)
    survivors = [r for r in rows if r["survivor"]]
    suppressors = sum(1 for r in survivors if r.get("mae_suppressor"))
    if trials == 0 or int(pool_n) < int(min_pool_n) \
            or valid < trials * VALID_TRIAL_MIN_FRACTION:
        verdict = "inconclusive"
    elif len(survivors) >= 2 and suppressors >= 1:
        verdict = "success"
    elif not survivors:
        verdict = "abandon"
    else:
        verdict = "below_threshold"
    summary = {
        "verdict": verdict,
        "pool_n": int(pool_n),
        "trials": trials,
        "valid_trials": valid,
        "survivors": len(survivors),
        "mae_suppressors": suppressors,
    }
    logger.info("screen_verdict %s", summary)
    return summary
