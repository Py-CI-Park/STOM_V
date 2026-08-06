# -*- coding: utf-8 -*-
"""W5 상설화 계약 테스트 — 백필 계획 · 재검증 계획.

계약:
  1. 라벨이 없는 거래일만 백필 대상이다(멱등).
  2. **홀드아웃 결손은 자동 대상이 아니다** — 목록에 넣되 잠근다. 자동으로 채우면
     그날부터 홀드아웃이 홀드아웃이 아니게 된다.
  3. 배치 상한을 넘는 날은 다음 회차로 미루고, 미룬 수를 보고한다(조용한 절단 금지).
  4. 재검증 대상은 "판정이 오래된 것"과 "판정이 아예 없는 것" 둘 다이며,
     없는 쪽을 먼저 본다.
  5. 오늘 날짜는 **인자로 받는다** — 함수가 시계를 읽으면 시험할 수 없다.
  6. 계획은 계획일 뿐 실행하지 않는다(파일을 만들지 않는다).
"""
from __future__ import annotations

import pytest

from ai_strategy_loop.controller import standing as st
from ai_strategy_loop.labeling.lanes import LANES


@pytest.fixture()
def dirs(tmp_path):
    db = tmp_path / "_database"
    labels = tmp_path / "labels" / "design_v4"
    db.mkdir()
    labels.mkdir(parents=True)
    return db, labels


def _make_db_days(db_dir, days, pattern="stock_tick_"):
    for day in days:
        (db_dir / f"{pattern}{day}.db").write_bytes(b"")


def _make_label_days(label_dir, days):
    for day in days:
        (label_dir / f"day={day}.parquet").write_bytes(b"")


def _plan(dirs, **kwargs):
    db, labels = dirs
    return st.backfill_plan("design_v4", "tick", db_dir=str(db),
                            label_root=str(labels.parent), **kwargs)


# ---------------------------------------------------------------------------
# 백필
# ---------------------------------------------------------------------------

def test_only_unlabeled_days_are_planned(dirs):
    db, labels = dirs
    _make_db_days(db, [20240304, 20240305, 20240306])
    _make_label_days(labels, [20240304])

    plan = _plan(dirs)
    assert plan["design_missing"] == [20240305, 20240306]
    assert plan["label_day_count"] == 1


def test_holdout_days_are_listed_but_locked(dirs):
    """★ 자동 백필은 홀드아웃 경계에서 멈춘다."""
    db, labels = dirs
    holdout_start = LANES["tick"].holdout_start
    _make_db_days(db, [20240304, holdout_start, holdout_start + 1])

    plan = _plan(dirs)
    assert plan["design_missing"] == [20240304]
    assert plan["holdout_missing"] == [holdout_start, holdout_start + 1]
    assert plan["holdout_locked"] is True
    # 잠긴 날이 실행 배치에 절대 섞이지 않는다.
    assert all(day < holdout_start for day in plan["next_batch"])


def test_batch_limit_reports_what_it_deferred(dirs):
    """조용한 절단 금지 — 미룬 수를 반드시 보고한다."""
    db, labels = dirs
    days = [20240300 + n for n in range(1, 26)]
    _make_db_days(db, days)

    plan = _plan(dirs, batch=10)
    assert len(plan["next_batch"]) == 10
    assert plan["deferred_count"] == 15
    assert plan["missing_total"] == 25
    assert plan["next_batch_range"] == [days[0], days[9]]


def test_empty_when_nothing_missing(dirs):
    db, labels = dirs
    _make_db_days(db, [20240304])
    _make_label_days(labels, [20240304])

    plan = _plan(dirs)
    assert plan["design_missing"] == []
    assert plan["next_batch"] == []
    assert plan["next_batch_range"] is None


def test_plan_creates_no_files(dirs):
    db, labels = dirs
    _make_db_days(db, [20240304, 20240305])
    before = sorted(p.name for p in labels.iterdir())
    _plan(dirs)
    assert sorted(p.name for p in labels.iterdir()) == before


def test_min_lane_uses_its_own_pattern_and_boundary(dirs):
    db, labels = dirs
    _make_db_days(db, [20250407], pattern="stock_min_")
    _make_db_days(db, [20240304], pattern="stock_tick_")

    plan = st.backfill_plan("min_design_v4", "min", db_dir=str(db),
                            label_root=str(labels.parent))
    assert plan["design_missing"] == [20250407]        # tick 파일은 보지 않는다
    assert plan["holdout_start"] == LANES["min"].holdout_start


# ---------------------------------------------------------------------------
# 재검증
# ---------------------------------------------------------------------------

def test_never_validated_comes_first():
    plan = st.revalidation_plan(
        [{"name": "old", "last_verdict_day": 20250601},
         {"name": "never", "last_verdict_day": None},
         {"name": "fresh", "last_verdict_day": 20250820}],
        today=20250825, max_age_days=30,
    )
    assert [r["name"] for r in plan["due"]] == ["never", "old"]
    assert plan["due"][0]["reason"] == "never_validated"
    assert plan["fresh_count"] == 1


def test_age_boundary_is_inclusive():
    """정확히 max_age 일이면 재판정한다 — 경계에서 미루지 않는다."""
    plan = st.revalidation_plan(
        [{"name": "edge", "last_verdict_day": 20250726}], today=20250825, max_age_days=30,
    )
    assert plan["due_count"] == 1
    assert plan["due"][0]["age_days"] == 30


def test_invalid_date_is_treated_as_never_validated():
    plan = st.revalidation_plan(
        [{"name": "bad", "last_verdict_day": 20251345}], today=20250825,
    )
    assert plan["due"][0]["reason"] == "never_validated"


def test_no_records_is_empty_not_error():
    plan = st.revalidation_plan([], today=20250825)
    assert plan["due"] == [] and plan["due_count"] == 0


def test_standing_status_skips_revalidation_without_today(dirs):
    db, labels = dirs
    _make_db_days(db, [20240304])
    status = st.standing_status("design_v4", "tick", records=[{"name": "a"}],
                                db_dir=str(db), label_root=str(labels.parent))
    assert status["revalidation"] is None       # 시계를 몰래 읽지 않는다
    assert status["actions_are_planned_only"] is True
