"""연구 run 이름 규칙 — 사람이 읽고 시간순으로 정렬되는 run_id 를 만든다(v5.13.2).

배경(사용자 지적, 2026-07-29):
  기존 run_id 는 규칙이 없어 무엇을 언제 한 연구인지 알 수 없었다.
    run_1781139038                                        ← 언제·무엇인지 둘 다 모름
    lat_plan_d_rank03_r1_selected1_oos_min_warm64_retry03_20260707
                                                          ← 날짜는 끝에, 시각은 없음
    clw30_r7oos_2023_20260728                             ← 접두어 뜻을 아는 사람만 읽음
  같은 날 여러 번 돌리면 구분도 안 되고, 문자열 정렬이 시간순과 어긋난다.

규칙(정본):
    YYYYMMDD-HHMM_<타임프레임>_<목적>[_<변형>]
    예) 20260729-1042_tick_wide-open30
        20260729-1042_tick_wide-open30_oos2023
        20260729-1105_min_exit-grid

  ① 날짜-시각이 **맨 앞** — 문자열 정렬 = 시간순이고, 같은 날 여러 번도 구분된다.
  ② 타임프레임이 이름에 있다 — tick/min 을 결과 열기 전에 안다.
  ③ 목적은 영문 소문자 케밥 — 사람이 읽는 부분. 축약어 대신 뜻이 보이게 쓴다.
  ④ 변형(선택)은 OOS 구간·재시도처럼 같은 목적의 갈래를 구분한다.

하위호환: 기존 run_id 를 바꾸지 않는다(1,000+ 개가 결과 CSV·문서와 묶여 있다).
describe_run_id() 가 구·신 이름을 모두 읽어 화면 표기용 dict 로 정규화한다.
"""

from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Any, Dict, Optional

# 정본 형식: 20260729-1042_tick_wide-open30[_oos2023]
_CANONICAL = re.compile(
    r"^(?P<date>\d{8})-(?P<time>\d{4})_(?P<tf>tick|min)_(?P<purpose>[a-z0-9][a-z0-9-]*)"
    r"(?:_(?P<variant>[a-z0-9][a-z0-9-]*))?$"
)
# 레거시에서 날짜만이라도 건지기: 이름 어딘가의 8자리 YYYYMMDD.
_LEGACY_DATE = re.compile(r"(?<!\d)(20\d{6})(?!\d)")

_VALID_TIMEFRAMES = ("tick", "min")


def _slug(text: Any, fallback: str) -> str:
    """자유 문자열 → 영문 소문자 케밥 슬러그. 비면 fallback."""
    s = re.sub(r"[^a-zA-Z0-9]+", "-", str(text or "")).strip("-").lower()
    s = re.sub(r"-{2,}", "-", s)
    return s[:40] or fallback


def make_run_id(purpose: str, timeframe: str = "tick",
                variant: Optional[str] = None, when: Optional[float] = None) -> str:
    """정본 규칙으로 run_id 를 만든다.

    purpose   연구 목적(예: "wide-open30", "exit-grid"). 슬러그로 정규화된다.
    timeframe "tick" | "min" (그 외 값은 tick 으로 보정 — 이름에 거짓을 넣지 않기 위해
              호출측이 명시하도록 기본을 두지 않는 편이 낫지만, 실사용상 tick 이 다수다).
    variant   같은 목적의 갈래(예: "oos2023", "retry02"). 없으면 생략.
    when      unix 시각(테스트에서 고정). 기본은 현재 시각.
    """
    stamp = datetime.fromtimestamp(time.time() if when is None else float(when))
    tf = str(timeframe) if str(timeframe) in _VALID_TIMEFRAMES else "tick"
    parts = [stamp.strftime("%Y%m%d-%H%M"), tf, _slug(purpose, "research")]
    if variant:
        parts.append(_slug(variant, ""))
    return "_".join(p for p in parts if p)


def describe_run_id(run_id: str, started_at: Optional[float] = None,
                    timeframe: Optional[str] = None) -> Dict[str, Any]:
    """run_id(구·신 모두) → 화면 표기용 dict.

    반환: {run_id, canonical(bool), date("YYYY-MM-DD"|None), time("HH:MM"|None),
           timeframe("tick"|"min"|None), purpose(str), display(str)}
    started_at(runs 테이블의 시작 시각)이 있으면 레거시 이름에도 날짜·시각을 채운다 —
    이름에서 못 읽어도 화면에는 "언제 시작했는지"가 반드시 나오게 한다.
    """
    rid = str(run_id or "")
    m = _CANONICAL.match(rid)
    date_s: Optional[str] = None
    time_s: Optional[str] = None
    tf: Optional[str] = timeframe if timeframe in _VALID_TIMEFRAMES else None
    purpose = rid

    if m:
        d, t = m.group("date"), m.group("time")
        date_s = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
        time_s = f"{t[:2]}:{t[2:]}"
        tf = m.group("tf")
        purpose = m.group("purpose") + (f" · {m.group('variant')}" if m.group("variant") else "")
    else:
        # 레거시 — 시작 시각(DB)이 이름보다 정확하다. 없으면 이름 속 날짜라도 쓴다.
        if started_at:
            try:
                stamp = datetime.fromtimestamp(float(started_at))
                date_s, time_s = stamp.strftime("%Y-%m-%d"), stamp.strftime("%H:%M")
            except (ValueError, TypeError, OSError):
                pass
        if date_s is None:
            hit = _LEGACY_DATE.search(rid)
            if hit:
                d = hit.group(1)
                date_s = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
        # 이름에서 날짜 토막을 떼어내면 남는 부분이 대체로 '목적'이다.
        purpose = _LEGACY_DATE.sub("", rid).strip("_-") or rid

    display_bits = [b for b in (date_s, time_s) if b]
    if tf:
        display_bits.append(tf)
    display_bits.append(purpose)
    return {
        "run_id": rid,
        "canonical": bool(m),
        "date": date_s,
        "time": time_s,
        "timeframe": tf,
        "purpose": purpose,
        "display": " · ".join(display_bits),
    }
