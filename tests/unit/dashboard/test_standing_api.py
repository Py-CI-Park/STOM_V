# -*- coding: utf-8 -*-
"""페이지 29 상설화 API 계약 테스트.

계약:
  1. 알 수 없는 레인은 조용히 tick 으로 흘리지 않고 거부한다.
  2. `today` 를 안 주면 재검증 계획을 만들지 않는다 — 서버가 몰래 시계를 읽으면
     화면이 무엇을 기준으로 "오래됐다"고 하는지 검증할 수 없다.
  3. 후보 기록이 없으면 빈 목록이다 — 후보를 지어내지 않는다.
  4. 응답은 항상 "계획 전용"임을 밝힌다.
"""
from __future__ import annotations

from ai_strategy_loop.dashboard import autoloop_api as api


def test_unknown_lane_is_refused():
    payload = api.standing(lane="coin")
    assert payload["available"] is False
    assert payload["reason"] == "unknown_lane"


def test_default_out_name_is_controller_canonical_default(monkeypatch):
    from ai_strategy_loop.controller import standing as st

    observed = {}

    def fake_status(out_name, lane, **kwargs):
        observed["out_name"] = out_name
        return {"available": True}

    monkeypatch.setattr(st, "standing_status", fake_status)
    payload = api.standing()
    assert payload["available"] is True
    assert observed["out_name"] == st.DEFAULT_OUT_NAME


def test_without_today_no_revalidation_plan(monkeypatch):
    monkeypatch.setattr(api, "_standing_candidates", lambda: [{"name": "run-A"}])
    payload = api.standing(today=0)
    assert payload["available"] is True
    assert payload["revalidation"] is None
    assert payload["actions_are_planned_only"] is True


def test_with_today_builds_revalidation_plan(monkeypatch):
    monkeypatch.setattr(api, "_standing_candidates",
                        lambda: [{"name": "run-A", "last_verdict_day": 20250601}])
    payload = api.standing(today=20250825, max_age_days=30)
    assert payload["revalidation"]["due_count"] == 1
    assert payload["revalidation"]["max_age_days"] == 30
    assert payload["candidate_count"] == 1


def test_no_candidates_is_empty_not_invented(monkeypatch):
    monkeypatch.setattr(api, "_standing_candidates", lambda: [])
    payload = api.standing(today=20250825, max_age_days=30)
    assert payload["candidate_count"] == 0
    assert payload["revalidation"]["due"] == []


def test_backfill_section_is_always_present(monkeypatch):
    monkeypatch.setattr(api, "_standing_candidates", lambda: [])
    payload = api.standing()
    assert "backfill" in payload
    assert payload["backfill"]["holdout_locked"] is True


def test_candidates_parse_dates_defensively(monkeypatch):
    """run_id 타임스탬프가 이상해도 죽지 않고 '판정 이력 없음'이 된다."""
    monkeypatch.setattr(api, "_rows", lambda *a, **k: [
        {"run_id": "r1", "last_at": "2025-08-25T10:00:00"},
        {"run_id": "r2", "last_at": ""},
        {"run_id": "r3", "last_at": None},
    ])
    rows = api._standing_candidates()
    assert rows[0]["last_verdict_day"] == 20250825
    assert rows[1]["last_verdict_day"] is None
    assert rows[2]["last_verdict_day"] is None
