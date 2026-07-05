"""E1~E5 사건족 감지기 — 정렬된 (t0, row) 1회 순회 인과 상태기계.

사건족 조작 정의(2026-07-05 설계서 §4.1 봉인 — 판정에 t 이하 데이터만,
'직전'은 직전 관측 행을 뜻한다. 결측 초는 관측이 없으므로 참조 불가):

- E1 VI 해제 재개: ``VI해제시간`` 값이 직전 관측과 달라지고 새 값의
  날짜==당일 AND 시각>09:00:00 이면 후보 → 그 행부터 첫 ``초당거래대금>0``
  행에서 발화(전이 행 자체가 거래 재개 행이면 그 행에서 즉시 발화).
  불응기에 억제된 후보는 소멸한다(이월 없음).
- E2 당일 신고가 돌파: ``고가 > 직전 관측 고가`` AND ``현재가 >= 고가``.
- E3 거래대금 서지: ``초당거래대금 >= SURGE_K × max(당일거래대금/max(경과초,1), 1)``,
  경과초 = t0 시각 − 09:00:00 (SURGE_K=10 봉인).
- E4 갭 상승 개장: 종목당 1회, t0 ∈ [09:00:01, 09:00:30] 창 안 첫 행에서만.
  갭% = (시가/전일종가 − 1)×100, 전일종가 = 현재가/(1+등락율/100)
  — 둘 다 첫 관측행 기준으로 봉인. 갭% >= 0 인 종목만 발화
  (갭 구간 분류는 outcomes 층화 소관).
- E5 라운드피겨 이탈: ``라운드피겨위5호가이내`` 직전 관측 1 → 현재 0 전이.

불응기(refractory): 사건족별 독립, 종목(=입력 시퀀스)당 직전 발화로부터
``refractory_sec`` 미만이면 무시. 경과 == refractory_sec 은 발화 허용.
억제된 발화 시도는 불응기 시계를 리셋하지 않는다.

시각 산술은 전부 datetime 파싱 기반(+1초/+h초 분·시 롤오버 정확 처리).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from alpha_lab.dataset.schema import as_float

__all__ = [
    "EVENT_FAMILIES",
    "REFRACTORY_SEC",
    "SURGE_K",
    "datetime_to_ts",
    "detect_events",
    "ts_shift",
    "ts_to_datetime",
]

logger = logging.getLogger(__name__)

EVENT_FAMILIES = ("E1", "E2", "E3", "E4", "E5")
REFRACTORY_SEC = 120       # 사건족별 독립 불응기(초) — 봉인.
SURGE_K = 10.0             # E3 서지 배수 — 봉인.

_TS_FORMAT = "%Y%m%d%H%M%S"
_HMS_MOD = 1_000_000       # int YYYYMMDDHHMMSS → HHMMSS 모듈러.
_OPEN_HMS = 90000          # 09:00:00 — E1 유효 해제시각은 이보다 커야 한다.
_E4_WINDOW_HMS = (90001, 90030)  # E4 발화 허용 창 [시작, 끝] (경계 포함).
_UNSET = object()          # E4 갭 미계산 상태(계산 결과 None과 구분).


def ts_to_datetime(t0: int) -> datetime:
    """int YYYYMMDDHHMMSS → datetime (시각 산술 단일 경로)."""
    return datetime.strptime(str(int(t0)), _TS_FORMAT)


def datetime_to_ts(moment: datetime) -> int:
    """datetime → int YYYYMMDDHHMMSS."""
    return int(moment.strftime(_TS_FORMAT))


def ts_shift(t0: int, seconds: int) -> int:
    """t0에 +seconds 초 (분·시 롤오버 정확) — datetime 파싱 기반."""
    return datetime_to_ts(ts_to_datetime(t0) + timedelta(seconds=int(seconds)))


def detect_events(
    rows_sorted: Iterable[Tuple[int, Mapping[str, Any]]],
    *,
    day: int,
    refractory_sec: int = REFRACTORY_SEC,
) -> List[Dict[str, Any]]:
    """정렬된 (t0, row) 시퀀스에서 E1~E5 사건을 감지한다.

    Args:
        rows_sorted: 한 종목·하루의 (int t0, 54컬럼 행 dict) 오름차순 시퀀스.
            비오름차순 입력은 ValueError(인과성 전제 보호).
        day: 당일 int YYYYMMDD — E1 해제시각의 당일 여부 판정에 쓴다.
        refractory_sec: 사건족별 독립 불응기(초).

    Returns:
        [{"event": "E1".."E5", "t0": int}] — 행 순서(=시각 오름차순) 그대로.
        입력 row는 절대 수정하지 않는다.
    """
    state = _new_state()
    events: List[Dict[str, Any]] = []
    for t0_raw, row in rows_sorted:
        t0 = int(t0_raw)
        if state["last_t0"] is not None and t0 <= state["last_t0"]:
            raise ValueError(
                f"rows_sorted는 t0 순오름차순이어야 한다: {t0} <= {state['last_t0']}")
        state["last_t0"] = t0
        moment = ts_to_datetime(t0)
        for family in _fired_families(state, moment, t0, row, int(day)):
            if _refractory_ok(state["last_fire"].get(family), moment, refractory_sec):
                state["last_fire"][family] = moment
                events.append({"event": family, "t0": t0})
        _remember_row(state, row)
    logger.debug("detect_events: day=%s events=%d", day, len(events))
    return events


def _new_state() -> Dict[str, Any]:
    """종목 하나 분량의 감지 상태 — detect_events 호출 로컬 전용."""
    return {
        "last_t0": None,
        "prev_vi": None, "e1_pending": False,     # E1
        "prev_high": None,                        # E2
        "e4_gap": _UNSET, "e4_done": False,       # E4
        "prev_round": None,                       # E5
        "last_fire": {},                          # 사건족별 마지막 발화 datetime
    }


def _fired_families(
    state: Dict[str, Any], moment: datetime, t0: int, row: Mapping[str, Any], day: int
) -> List[str]:
    """현재 행에서 조건이 성립한 사건족(불응기 적용 전)."""
    fired = []
    if _check_e1(state, row, day):
        fired.append("E1")
    if _check_e2(state, row):
        fired.append("E2")
    if _check_e3(moment, row):
        fired.append("E3")
    if _check_e4(state, t0, row):
        fired.append("E4")
    if _check_e5(state, row):
        fired.append("E5")
    return fired


def _check_e1(state: Dict[str, Any], row: Mapping[str, Any], day: int) -> bool:
    """VI 해제 유효 전이 후보 → 첫 초당거래대금>0 행 발화."""
    vi = as_float(row.get("VI해제시간"))
    prev = state["prev_vi"]
    if prev is not None and vi != prev and _is_today_release(vi, day):
        state["e1_pending"] = True
    if state["e1_pending"] and as_float(row.get("초당거래대금")) > 0.0:
        state["e1_pending"] = False
        return True
    return False


def _is_today_release(vi_value: float, day: int) -> bool:
    """VI해제시간 float(YYYYMMDDHHMMSS.0)이 당일이고 09:00:00 초과인지."""
    stamp = int(vi_value)
    return stamp // _HMS_MOD == int(day) and stamp % _HMS_MOD > _OPEN_HMS


def _check_e2(state: Dict[str, Any], row: Mapping[str, Any]) -> bool:
    """당일 러닝 신고가 갱신: 고가 > 직전 관측 고가 AND 현재가 >= 고가."""
    prev_high = state["prev_high"]
    if prev_high is None:
        return False
    high = as_float(row.get("고가"))
    return high > prev_high and as_float(row.get("현재가")) >= high


def _check_e3(moment: datetime, row: Mapping[str, Any]) -> bool:
    """초당거래대금 >= SURGE_K × max(당일거래대금/max(경과초,1), 1)."""
    open_moment = moment.replace(hour=9, minute=0, second=0, microsecond=0)
    elapsed = (moment - open_moment).total_seconds()
    baseline = max(as_float(row.get("당일거래대금")) / max(elapsed, 1.0), 1.0)
    return as_float(row.get("초당거래대금")) >= SURGE_K * baseline


def _check_e4(state: Dict[str, Any], t0: int, row: Mapping[str, Any]) -> bool:
    """갭 상승 개장 — 창 안 첫 행에서 종목당 1회 확정 판정."""
    if state["e4_done"]:
        return False
    if state["e4_gap"] is _UNSET:
        state["e4_gap"] = _gap_pct(row)  # 첫 관측행 기준(창 밖이어도 여기서 봉인)
    hms = t0 % _HMS_MOD
    if hms > _E4_WINDOW_HMS[1]:
        state["e4_done"] = True  # 창 경과 — 영구 비발화
        return False
    if hms < _E4_WINDOW_HMS[0]:
        return False
    state["e4_done"] = True      # 창 안 첫 행에서 판정 확정(종목당 1회)
    gap = state["e4_gap"]
    return gap is not None and gap >= 0.0


def _gap_pct(row: Mapping[str, Any]) -> Optional[float]:
    """갭% = (시가/전일종가 − 1)×100, 전일종가 = 현재가/(1+등락율/100).

    분모 0 이하·가격 0 이하는 판정 불가 → None(비발화).
    """
    price = as_float(row.get("현재가"))
    open_price = as_float(row.get("시가"))
    denom = 1.0 + as_float(row.get("등락율")) / 100.0
    if price <= 0.0 or open_price <= 0.0 or denom <= 0.0:
        return None
    prev_close = price / denom
    return (open_price / prev_close - 1.0) * 100.0


def _check_e5(state: Dict[str, Any], row: Mapping[str, Any]) -> bool:
    """라운드피겨위5호가이내 직전 관측 1 → 현재 0 전이(0/1 플래그)."""
    prev = state["prev_round"]
    if prev is None:
        return False
    return prev >= 0.5 and as_float(row.get("라운드피겨위5호가이내")) < 0.5


def _refractory_ok(
    last: Optional[datetime], moment: datetime, refractory_sec: int
) -> bool:
    """직전 발화 후 refractory_sec 이상 경과(또는 첫 발화)일 때만 허용."""
    return last is None or (moment - last).total_seconds() >= float(refractory_sec)


def _remember_row(state: Dict[str, Any], row: Mapping[str, Any]) -> None:
    """다음 행 판정용 '직전 관측' 스냅샷 갱신(입력 row는 수정하지 않음)."""
    state["prev_vi"] = as_float(row.get("VI해제시간"))
    state["prev_high"] = as_float(row.get("고가"))
    state["prev_round"] = as_float(row.get("라운드피겨위5호가이내"))
