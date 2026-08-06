"""W5 상설화 — 시간을 데이터로 바꾸는 두 가지 일의 **계획**만 만든다.

연구가 한 번의 캠페인으로 끝나면, 그 결과는 캠페인이 끝난 날부터 썩기 시작한다.
상설화는 두 가지를 상시로 돌린다:

  1. **백필** — 새 거래일이 DB 에 들어오면 라벨도 따라 만든다.
  2. **상설 재검증** — 보유 후보를 주기적으로 다시 판정한다(시간이 표본을 준다).

이 모듈은 **계획만** 만든다. 실행(라벨 빌드·엔진 런)은 러너가 한다. 계획과 실행을
나누는 이유: 계획은 순수 함수라 시험할 수 있고, "무엇을 하려 하는지"를 실행 전에
화면에 띄울 수 있다.

## 절대 규칙 — 홀드아웃은 자동으로 만들지 않는다

빠진 날 중 홀드아웃 구간에 속한 날은 **계획에 넣되 잠금 표시**를 한다. 자동
백필이 홀드아웃을 조용히 채우면, 그날부터 홀드아웃은 홀드아웃이 아니다.
개봉은 언제나 사람의 결정이다.
"""

from __future__ import annotations

import glob
import os
from typing import Any, Final

from ai_strategy_loop.labeling.lanes import LANES, LaneSpec

_DB_DIR: Final = os.path.join(os.path.dirname(__file__), "..", "..", "_database")
_LABEL_ROOT: Final = os.path.join(os.path.dirname(__file__), "..", "state", "labels")

#: 후보 판정이 이보다 오래되면 다시 판정한다. 30일 = 대략 한 달 치 새 표본.
DEFAULT_MAX_AGE_DAYS: Final = 30

#: 한 번에 백필할 최대 일수 — 무한정 도는 계획을 만들지 않는다.
DEFAULT_BACKFILL_BATCH: Final = 20


def db_days(lane: LaneSpec, *, db_dir: str | None = None) -> list[int]:
    """DB 에 존재하는 거래일 — 라벨의 상한이다."""
    root = db_dir or _DB_DIR
    files = glob.glob(os.path.join(root, f"{lane.db_pattern}2*.db"))
    prefix = len(lane.db_pattern)
    days: set[int] = set()
    for path in files:
        stem = os.path.basename(path)[prefix:prefix + 8]
        if stem.isdigit():
            days.add(int(stem))
    return sorted(days)


def label_days(out_name: str, *, label_root: str | None = None) -> list[int]:
    """이미 라벨이 만들어진 거래일."""
    root = label_root or _LABEL_ROOT
    files = glob.glob(os.path.join(root, out_name, "day=*.parquet"))
    days: set[int] = set()
    for path in files:
        stem = os.path.basename(path)[4:12]
        if stem.isdigit():
            days.add(int(stem))
    return sorted(days)


def backfill_plan(
    out_name: str,
    lane_name: str = "tick",
    *,
    batch: int = DEFAULT_BACKFILL_BATCH,
    db_dir: str | None = None,
    label_root: str | None = None,
) -> dict[str, Any]:
    """DB 에는 있는데 라벨이 없는 날의 목록 — 설계 구간과 홀드아웃을 **나눠서**.

    설계 구간 결손은 그냥 만들면 된다. 홀드아웃 결손은 잠긴 채로 보고만 한다.
    """
    lane = LANES[lane_name]
    have = set(label_days(out_name, label_root=label_root))
    missing = [d for d in db_days(lane, db_dir=db_dir) if d not in have]

    design = [d for d in missing if d < lane.holdout_start]
    holdout = [d for d in missing if d >= lane.holdout_start]
    batched = design[:batch]

    return {
        "lane": lane.name,
        "out_name": out_name,
        "label_day_count": len(have),
        "missing_total": len(missing),
        # 이번에 실제로 만들 날 — 배치 상한을 넘으면 다음 회차로 넘긴다.
        "design_missing": design,
        "next_batch": batched,
        "next_batch_range": [batched[0], batched[-1]] if batched else None,
        "deferred_count": max(0, len(design) - len(batched)),
        # 홀드아웃 결손은 목록만 보여 준다. 자동으로 만들지 않는다.
        "holdout_missing": holdout,
        "holdout_locked": True,
        "holdout_start": lane.holdout_start,
        "note": ("홀드아웃 결손은 자동으로 채우지 않습니다. 채우는 순간 그날부터 "
                 "홀드아웃이 아니게 됩니다 — 개봉은 사람의 결정입니다."),
    }


def _age_in_days(boundary: int | None, today: int) -> int | None:
    """YYYYMMDD 두 개의 **달력 일수** 차이 — 거래일이 아니라 달력이다.

    거래일 수로 세려면 달력을 알아야 하는데, 여기서 필요한 것은 "얼마나
    오래됐나"의 근사이므로 달력 차이면 충분하다.
    """
    if boundary is None:
        return None
    from datetime import date

    def _to_date(value: int) -> date:
        return date(value // 10000, (value // 100) % 100, value % 100)

    try:
        return (_to_date(today) - _to_date(boundary)).days
    except ValueError:
        return None


def revalidation_plan(
    records: list[dict[str, Any]],
    *,
    today: int,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
) -> dict[str, Any]:
    """보유 후보 중 다시 판정할 것 — 판정이 오래됐거나 아예 없는 것.

    Args:
        records: 후보 원장 행. `name` 과 `last_verdict_day`(YYYYMMDD, 없으면 None).
        today: 오늘(YYYYMMDD). 시스템 시각을 이 함수 안에서 읽지 않는다 —
            시각을 인자로 받아야 시험할 수 있다.
    """
    due: list[dict[str, Any]] = []
    fresh: list[dict[str, Any]] = []
    for record in records:
        age = _age_in_days(record.get("last_verdict_day"), today)
        row = {
            "name": record.get("name"),
            "last_verdict_day": record.get("last_verdict_day"),
            "age_days": age,
            # 판정 이력이 아예 없는 것은 "오래된 것"보다 먼저 본다.
            "reason": "never_validated" if age is None else "stale",
        }
        if age is None or age >= max_age_days:
            due.append(row)
        else:
            fresh.append({**row, "reason": "fresh"})

    due.sort(key=lambda r: (r["reason"] != "never_validated", -(r["age_days"] or 0)))
    return {
        "today": today,
        "max_age_days": max_age_days,
        "due": due,
        "due_count": len(due),
        "fresh_count": len(fresh),
        "note": ("재판정은 표본을 늘리는 일이지 성적을 고치는 일이 아닙니다. "
                 "결과가 나빠지면 그것이 새 사실입니다."),
    }


def standing_status(
    out_name: str = "design_v4",
    lane_name: str = "tick",
    *,
    records: list[dict[str, Any]] | None = None,
    today: int = 0,
    db_dir: str | None = None,
    label_root: str | None = None,
) -> dict[str, Any]:
    """상설화 한 장 요약 — 백필 계획 + 재검증 계획."""
    backfill = backfill_plan(out_name, lane_name, db_dir=db_dir, label_root=label_root)
    revalidation = (
        revalidation_plan(records or [], today=today) if today else None
    )
    return {
        "authority": "diagnostic",
        "backfill": backfill,
        "revalidation": revalidation,
        "actions_are_planned_only": True,
        "note": "이 화면은 계획만 보여 줍니다. 실행은 러너가 하고, 채택은 사람이 합니다.",
    }
