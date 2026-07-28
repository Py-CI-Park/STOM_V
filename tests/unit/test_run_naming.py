"""연구 run 이름 규칙(v5.13.2) — 사람이 읽고 시간순 정렬되는 run_id.

사용자 지적(2026-07-29): "연구 이름 지정하는거 이름 규칙 더 개선 및 이해하기 쉽고
언제 진행하고 시작한건지 알수있도록". 기존 이름은 `run_1781139038` 처럼 시각도
목적도 읽을 수 없거나, 날짜가 이름 끝에 붙어 문자열 정렬이 시간순과 어긋났다.
"""

from __future__ import annotations

import time

from ai_strategy_loop.controller.run_naming import describe_run_id, make_run_id

_WHEN = time.mktime((2026, 7, 29, 10, 42, 0, 0, 0, -1))


def test_canonical_name_puts_datetime_first():
    assert make_run_id("wide-open30", "tick", when=_WHEN) == "20260729-1042_tick_wide-open30"


def test_variant_is_appended():
    assert make_run_id("wide-open30", "tick", variant="oos2023", when=_WHEN) == (
        "20260729-1042_tick_wide-open30_oos2023")


def test_free_text_purpose_is_slugified():
    assert make_run_id("Exit Grid 실험", "min", when=_WHEN).startswith("20260729-1042_min_exit-grid")


def test_unknown_timeframe_falls_back_to_tick():
    assert "_tick_" in make_run_id("x", "5분봉", when=_WHEN)


def test_string_sort_matches_chronological_order():
    """이름 앞이 날짜-시각이므로 문자열 정렬 = 시간순(구 이름의 핵심 결함)."""
    earlier = make_run_id("a", "tick", when=_WHEN - 3600)
    later = make_run_id("a", "tick", when=_WHEN)
    assert sorted([later, earlier]) == [earlier, later]


def test_same_day_runs_are_distinguishable():
    """같은 날 두 번 돌려도 시각(HHMM)으로 구분된다."""
    assert make_run_id("a", "tick", when=_WHEN) != make_run_id("a", "tick", when=_WHEN + 600)


def test_describe_parses_canonical_name():
    d = describe_run_id("20260729-1042_tick_wide-open30_oos2023")
    assert d["canonical"] is True
    assert (d["date"], d["time"], d["timeframe"]) == ("2026-07-29", "10:42", "tick")
    assert "wide-open30" in d["purpose"] and "oos2023" in d["purpose"]


def test_describe_legacy_uses_started_at_for_time():
    """구 이름은 시각을 담지 않으므로 runs.started_at 으로 채운다 — 화면에 '언제'가 항상 나온다."""
    d = describe_run_id("clw30_r7oos_2023_20260728", started_at=_WHEN)
    assert d["canonical"] is False
    assert d["date"] == "2026-07-29" and d["time"] == "10:42"
    assert "20260728" not in d["purpose"]  # 이름 속 날짜 토막은 목적에서 제거


def test_describe_legacy_without_started_at_falls_back_to_embedded_date():
    d = describe_run_id("clw30_r7oos_2023_20260728")
    assert d["date"] == "2026-07-28"
    assert d["time"] is None


def test_describe_never_raises_on_garbage():
    for rid in ("", None, "!!!", "run_", 12345):
        assert isinstance(describe_run_id(rid)["display"], str)
