"""T3.3 변이축 효과 원장(AxisLedger) 단위 테스트.

핵심 검증:
  - JSONL append-only record/iter_entries 왕복 + 필수 필드 검증.
  - recorded_at 은 호출자 주입 — 누락 시 거부(모듈 내 시계 금지 규약).
  - aggregate_axis_priors 의 축별 {n, improve_rate, mean_delta_profit,
    std, mean_delta_mdd, last_verdicts} 산출.
  - to_prompt_lines 한국어 라인 (유망 축 + 반복 악화 축 경고).
  - banned_axes 가 기존 수동 금지 사례(turnover_min_902 1.5 -> 3.0)를
    데이터만으로 재현.
  - 결정론: 같은 원장 → 같은 집계 / 같은 라인.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import json  # noqa: E402

import pytest  # noqa: E402

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.controller.axis_ledger import (  # noqa: E402
    AXIS_LEDGER_SCHEMA_VERSION,
    AxisLedger,
    aggregate_axis_priors,
    banned_axes,
    to_prompt_lines,
)


def _entry(**overrides):
    base = {
        "run_id": "run_20260702_a",
        "parent_id": "GATE_rr8_12_turnover_min_902_1_5_B",
        "candidate_id": "prv2_20260702_c001",
        "axis": "turnover_min_902",
        "param": "turnover_min_902",
        "from_value": 1.5,
        "to_value": 3.0,
        "delta_profit": -524_096.0,
        "delta_mdd": 6.62,
        "delta_trades": -38,
        "delta_win_rate": -0.03,
        "slippage_profile": "baseline",
        "window": "2025_full",
        "verdict": "executed_and_rejected_below_parent",
        "recorded_at": "2026-07-02T09:00:00+09:00",
    }
    return {**base, **overrides}


def _ledger(tmp_path):
    return AxisLedger(tmp_path / "axis_ledger.jsonl")


# ---------------------------------------------------------------- record


def test_record_appends_jsonl_and_returns_copy_without_mutating_input(tmp_path):
    ledger = _ledger(tmp_path)
    source = _entry()
    before = dict(source)

    stored = ledger.record(source)

    assert source == before  # 입력 불변
    assert stored["schema_version"] == AXIS_LEDGER_SCHEMA_VERSION
    assert stored["axis"] == "turnover_min_902"

    raw_lines = ledger.path.read_text(encoding="utf-8").splitlines()
    assert len(raw_lines) == 1
    parsed = json.loads(raw_lines[0])
    assert parsed["candidate_id"] == "prv2_20260702_c001"
    assert parsed["recorded_at"] == "2026-07-02T09:00:00+09:00"


def test_record_is_append_only_across_calls(tmp_path):
    ledger = _ledger(tmp_path)
    ledger.record(_entry(candidate_id="c1"))
    ledger.record(_entry(candidate_id="c2"))
    ids = [e["candidate_id"] for e in ledger.iter_entries()]
    assert ids == ["c1", "c2"]  # 기록 순서 보존


def test_record_rejects_missing_recorded_at_no_module_clock(tmp_path):
    """recorded_at 은 호출자 주입 필수 — 모듈이 시계로 채워주면 안 된다."""
    ledger = _ledger(tmp_path)
    bad = _entry()
    del bad["recorded_at"]
    with pytest.raises(ValueError) as exc:
        ledger.record(bad)
    assert "missing_field:recorded_at" in str(exc.value)
    assert not ledger.path.exists()  # 거부된 레코드는 기록되지 않는다


def test_record_rejects_missing_and_invalid_fields_with_joined_reasons(tmp_path):
    ledger = _ledger(tmp_path)
    bad = _entry(axis="", delta_profit="worse")
    del bad["window"]
    with pytest.raises(ValueError) as exc:
        ledger.record(bad)
    reasons = str(exc.value).split("|")
    assert "missing_field:window" in reasons
    assert "non_empty_string_required:axis" in reasons
    assert "numeric_required:delta_profit" in reasons


def test_record_rejects_bool_as_numeric_delta(tmp_path):
    ledger = _ledger(tmp_path)
    with pytest.raises(ValueError) as exc:
        ledger.record(_entry(delta_trades=True))
    assert "numeric_required:delta_trades" in str(exc.value)


# ---------------------------------------------------------- iter_entries


def test_iter_entries_empty_when_file_missing(tmp_path):
    assert list(_ledger(tmp_path).iter_entries()) == []


def test_iter_entries_equality_filter(tmp_path):
    ledger = _ledger(tmp_path)
    ledger.record(_entry(candidate_id="c1", axis="turnover_min_902"))
    ledger.record(_entry(candidate_id="c2", axis="trailing_giveback", delta_profit=210_000.0))
    ledger.record(_entry(candidate_id="c3", axis="trailing_giveback", window="2024_h2"))

    got = list(ledger.iter_entries({"axis": "trailing_giveback", "window": "2025_full"}))
    assert [e["candidate_id"] for e in got] == ["c2"]


def test_iter_entries_raises_loudly_on_corrupt_line(tmp_path):
    ledger = _ledger(tmp_path)
    ledger.record(_entry())
    with ledger.path.open("a", encoding="utf-8") as handle:
        handle.write("{not json}\n")
    with pytest.raises(ValueError) as exc:
        list(ledger.iter_entries())
    assert "corrupt_ledger_line" in str(exc.value)
    assert ":2" in str(exc.value)


# ------------------------------------------------- aggregate_axis_priors


def _seed_mixed_ledger(ledger):
    """turnover_min_902 3회 반복 악화 + trailing_giveback 2/3 개선."""
    worsen = [
        ("run_a", "c_t1", "2025_full", "baseline", -524_096.0, 6.62),
        ("run_b", "c_t2", "2025_h1", "stress", -310_000.0, 4.10),
        ("run_c", "c_t3", "2024_h2", "baseline", -120_500.0, 1.75),
    ]
    for i, (run_id, cid, window, slip, dp, dm) in enumerate(worsen):
        ledger.record(_entry(
            run_id=run_id, candidate_id=cid, window=window,
            slippage_profile=slip, delta_profit=dp, delta_mdd=dm,
            recorded_at=f"2026-07-02T09:0{i}:00+09:00",
        ))
    improve = [
        ("c_g1", 210_000.0, -0.80, "executed_and_kept_above_parent"),
        ("c_g2", 90_000.0, -0.20, "executed_and_kept_above_parent"),
        ("c_g3", -30_000.0, 0.30, "executed_and_rejected_below_parent"),
    ]
    for i, (cid, dp, dm, verdict) in enumerate(improve):
        ledger.record(_entry(
            candidate_id=cid, axis="trailing_giveback", param="trail_keep",
            from_value=0.6, to_value=0.7, delta_profit=dp, delta_mdd=dm,
            verdict=verdict, recorded_at=f"2026-07-02T10:0{i}:00+09:00",
        ))


def test_aggregate_axis_priors_shape_and_values(tmp_path):
    ledger = _ledger(tmp_path)
    _seed_mixed_ledger(ledger)

    priors = ledger.aggregate_axis_priors()
    assert sorted(priors) == ["trailing_giveback", "turnover_min_902"]

    worse = priors["turnover_min_902"]
    assert worse["n"] == 3
    assert worse["improve_rate"] == 0.0
    assert worse["mean_delta_profit"] == pytest.approx(-318_198.6667, abs=0.01)
    assert worse["std"] == pytest.approx(164_838.0, rel=1e-3)
    assert worse["mean_delta_mdd"] == pytest.approx(4.156667, abs=1e-6)
    assert worse["last_verdicts"] == ["executed_and_rejected_below_parent"] * 3

    good = priors["trailing_giveback"]
    assert good["n"] == 3
    assert good["improve_rate"] == pytest.approx(2 / 3)
    assert good["mean_delta_profit"] == pytest.approx(90_000.0)
    assert good["last_verdicts"][-1] == "executed_and_rejected_below_parent"


def test_aggregate_last_verdicts_keeps_recent_five(tmp_path):
    ledger = _ledger(tmp_path)
    for i in range(7):
        ledger.record(_entry(
            candidate_id=f"c{i}", verdict=f"v{i}",
            recorded_at=f"2026-07-02T09:00:0{i}+09:00",
        ))
    priors = ledger.aggregate_axis_priors()
    assert priors["turnover_min_902"]["last_verdicts"] == ["v2", "v3", "v4", "v5", "v6"]


def test_aggregate_single_entry_std_zero(tmp_path):
    ledger = _ledger(tmp_path)
    ledger.record(_entry())
    priors = ledger.aggregate_axis_priors()
    assert priors["turnover_min_902"]["std"] == 0.0


def test_aggregate_empty_ledger_returns_empty(tmp_path):
    assert _ledger(tmp_path).aggregate_axis_priors() == {}


# --------------------------------------------------------- 결정론


def test_determinism_same_ledger_same_priors_and_lines(tmp_path):
    ledger = _ledger(tmp_path)
    _seed_mixed_ledger(ledger)

    priors_1 = ledger.aggregate_axis_priors()
    priors_2 = AxisLedger(ledger.path).aggregate_axis_priors()
    assert priors_1 == priors_2
    assert list(priors_1) == list(priors_2)  # 축 순서까지 동일

    lines_1 = to_prompt_lines(priors_1, top_k=3, bottom_k=2)
    lines_2 = to_prompt_lines(priors_2, top_k=3, bottom_k=2)
    assert lines_1 == lines_2

    assert banned_axes(priors_1) == banned_axes(priors_2)


def test_aggregate_free_function_matches_method(tmp_path):
    ledger = _ledger(tmp_path)
    _seed_mixed_ledger(ledger)
    assert aggregate_axis_priors(list(ledger.iter_entries())) == ledger.aggregate_axis_priors()


# ------------------------------------------------------ to_prompt_lines


def test_to_prompt_lines_promising_then_warning_korean(tmp_path):
    ledger = _ledger(tmp_path)
    _seed_mixed_ledger(ledger)
    lines = to_prompt_lines(ledger.aggregate_axis_priors(), top_k=3, bottom_k=2)

    assert lines[0].startswith("## 변이축 사전확률")
    promising = [l for l in lines if "[유망 축]" in l]
    warning = [l for l in lines if "[경고 축]" in l]
    assert len(promising) == 1 and "trailing_giveback" in promising[0]
    assert "개선확률 67%" in promising[0]
    assert len(warning) == 1 and "turnover_min_902" in warning[0]
    assert "반복 악화" in warning[0]
    assert "재시도는 지양" in warning[0]
    assert "executed_and_rejected_below_parent" in warning[0]
    # 유망 축이 경고 축보다 먼저 나온다.
    assert lines.index(promising[0]) < lines.index(warning[0])


def test_to_prompt_lines_empty_priors_returns_empty():
    assert to_prompt_lines({}, top_k=3, bottom_k=2) == []


def test_to_prompt_lines_respects_top_k_and_bottom_k():
    priors = {
        f"axis_up_{i}": {
            "n": 4, "improve_rate": 0.75 - i * 0.05,
            "mean_delta_profit": 100_000.0 - i, "std": 1.0,
            "mean_delta_mdd": -0.5, "last_verdicts": ["kept"],
        }
        for i in range(4)
    }
    priors.update({
        f"axis_down_{i}": {
            "n": 3, "improve_rate": 0.0,
            "mean_delta_profit": -200_000.0 - i, "std": 1.0,
            "mean_delta_mdd": 2.0, "last_verdicts": ["rejected"],
        }
        for i in range(3)
    })
    lines = to_prompt_lines(priors, top_k=2, bottom_k=1)
    assert sum(1 for l in lines if "[유망 축]" in l) == 2
    assert sum(1 for l in lines if "[경고 축]" in l) == 1
    # 최악(가장 낮은 mean_delta_profit) 축이 경고로 선택된다.
    assert any("axis_down_2" in l for l in lines if "[경고 축]" in l)


def test_to_prompt_lines_ban_eligible_axis_never_labeled_promising():
    """금지 적격 축(n>=3, 개선확률<=0.2)은 개선확률>0 이어도 유망 축이 아니다."""
    priors = {
        "ban_eligible_axis": {
            "n": 3, "improve_rate": 0.2, "mean_delta_profit": -150_000.0,
            "std": 1.0, "mean_delta_mdd": 2.5,
            "last_verdicts": ["rejected", "rejected", "kept"],
        },
        "healthy_axis": {
            "n": 3, "improve_rate": 2 / 3, "mean_delta_profit": 90_000.0,
            "std": 1.0, "mean_delta_mdd": -0.4, "last_verdicts": ["kept"],
        },
    }
    lines = to_prompt_lines(priors, top_k=3, bottom_k=2)
    promising = [l for l in lines if "[유망 축]" in l]
    warning = [l for l in lines if "[경고 축]" in l]

    assert len(promising) == 1 and "healthy_axis" in promising[0]
    assert all("ban_eligible_axis" not in l for l in promising)
    # 금지 적격 축은 경고 축으로 강등된다.
    assert any("ban_eligible_axis" in l for l in warning)
    # 같은 priors 의 banned_axes 목록과 프롬프트 라벨이 모순되지 않는다.
    for axis in banned_axes(priors):
        assert all(axis not in l for l in promising)


def test_to_prompt_lines_low_rate_axis_below_ban_min_n_still_promising():
    """시도 2회(n < ban_min_n=3)면 개선확률 0.2 라도 아직 유망 축 후보다."""
    priors = {
        "young_axis": {
            "n": 2, "improve_rate": 0.2, "mean_delta_profit": 10_000.0,
            "std": 0.0, "mean_delta_mdd": 0.1, "last_verdicts": ["kept"],
        },
    }
    assert banned_axes(priors) == []
    lines = to_prompt_lines(priors, top_k=1, bottom_k=0)
    assert any("[유망 축]" in l and "young_axis" in l for l in lines)


# ---------------------------------------------------------- banned_axes


def test_banned_axes_reproduces_turnover_min_902_manual_ban_from_data(tmp_path):
    """수동 금지였던 turnover_min_902 1.5→3.0 반복 악화가 데이터로 재현된다."""
    ledger = _ledger(tmp_path)
    _seed_mixed_ledger(ledger)

    banned = banned_axes(ledger.aggregate_axis_priors(), min_n=3, max_improve_rate=0.2)
    assert banned == ["turnover_min_902"]
    assert "trailing_giveback" not in banned  # 개선 이력 있는 축은 금지되지 않는다


def test_banned_axes_requires_min_n(tmp_path):
    """악화 2회뿐이면(min_n=3 미달) 아직 금지하지 않는다."""
    ledger = _ledger(tmp_path)
    for i in range(2):
        ledger.record(_entry(
            candidate_id=f"c{i}", recorded_at=f"2026-07-02T09:00:0{i}+09:00",
        ))
    assert banned_axes(ledger.aggregate_axis_priors()) == []


def test_banned_axes_threshold_boundary_and_sorted_output():
    priors = {
        "z_axis": {"n": 3, "improve_rate": 0.2, "mean_delta_profit": -1.0,
                   "std": 0.0, "mean_delta_mdd": 1.0, "last_verdicts": []},
        "a_axis": {"n": 5, "improve_rate": 0.0, "mean_delta_profit": -2.0,
                   "std": 0.0, "mean_delta_mdd": 2.0, "last_verdicts": []},
        "ok_axis": {"n": 10, "improve_rate": 0.21, "mean_delta_profit": 1.0,
                    "std": 0.0, "mean_delta_mdd": -1.0, "last_verdicts": []},
    }
    # improve_rate == max_improve_rate 는 포함(<=), 초과는 제외. 이름순 정렬.
    assert banned_axes(priors, min_n=3, max_improve_rate=0.2) == ["a_axis", "z_axis"]
