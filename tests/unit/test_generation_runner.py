"""G-0e 세대 수렴 판정 계약.

판정 입력은 **홀드아웃 건당 손익**이다 — 총손익은 거래를 줄이기만 해도 좋아지므로
수렴 판정에 쓰지 않는다.
"""

from __future__ import annotations

import pytest

from ai_strategy_loop.revision import generation_runner as gr


def _record(generation, holdout, *, design=None, retention=1.0, lane="tick"):
    return gr.GenerationRecord(
        lane=lane, generation=generation, candidate_id=f"G{generation}",
        clauses=(f"절{generation}",),
        design_per_trade=design if design is not None else holdout - 400.0,
        holdout_per_trade=holdout,
        design_retention=retention, holdout_retention=retention,
        cumulative_retention=retention,
    )


def test_no_records_is_not_started():
    state, reason = gr.verdict(())
    assert state == "not_started"
    assert "세대가 없습니다" in reason


def test_improving_generations_keep_running():
    records = (_record(1, -5000.0), _record(2, -4600.0), _record(3, -4200.0))
    assert gr.verdict(records)[0] == "running"


def test_three_flat_generations_converge():
    """개선이 3세대 연속 50원 미만이면 멈춘다."""
    records = (
        _record(1, -5000.0), _record(2, -4980.0),
        _record(3, -4970.0), _record(4, -4960.0),
    )
    state, reason = gr.verdict(records)
    assert state == "converged"
    assert "수렴" in reason


def test_two_flat_generations_are_not_enough():
    records = (_record(1, -5000.0), _record(2, -4980.0), _record(3, -4970.0))
    assert gr.verdict(records)[0] == "running"


def test_two_worsening_generations_diverge_and_name_the_rollback():
    records = (
        _record(1, -5000.0), _record(2, -4500.0),
        _record(3, -4700.0), _record(4, -4900.0),
    )
    state, reason = gr.verdict(records)
    assert state == "diverged"
    assert "롤백" in reason
    assert gr.rollback_target(records) == 2


def test_budget_exhaustion_wins_over_other_verdicts():
    """유지율 하한을 깨면 개선 여부와 무관하게 멈춘다."""
    records = (_record(1, -5000.0), _record(2, -3000.0, retention=0.35))
    state, reason = gr.verdict(records)
    assert state == "budget_exhausted"
    assert "하한" in reason


def test_rollback_target_is_none_when_not_diverged():
    assert gr.rollback_target((_record(1, -5000.0), _record(2, -4000.0))) is None


# --------------------------------------------------------------------------- 저장

def test_records_round_trip_per_lane(tmp_path, monkeypatch):
    monkeypatch.setattr(gr, "_STATE_PATH", tmp_path / "gen.jsonl")
    monkeypatch.setattr(gr, "_path", lambda: tmp_path / "gen.jsonl")
    gr.append(_record(1, -5000.0, lane="tick"))
    gr.append(_record(1, -3000.0, lane="min"))
    gr.append(_record(2, -4600.0, lane="tick"))
    tick = gr.load("tick")
    assert [row.generation for row in tick] == [1, 2]
    assert all(row.lane == "tick" for row in tick)
    assert len(gr.load("min")) == 1


def test_corrupted_line_is_skipped_not_fatal(tmp_path, monkeypatch):
    path = tmp_path / "gen.jsonl"
    monkeypatch.setattr(gr, "_path", lambda: path)
    gr.append(_record(1, -5000.0))
    with path.open("a", encoding="utf-8") as handle:
        handle.write("{not json\n")
    gr.append(_record(2, -4600.0))
    assert [row.generation for row in gr.load("tick")] == [1, 2]


def test_history_payload_reports_deltas_and_rule(tmp_path, monkeypatch):
    monkeypatch.setattr(gr, "_path", lambda: tmp_path / "gen.jsonl")
    gr.append(_record(1, -5000.0))
    gr.append(_record(2, -4600.0))
    payload = gr.history_payload(lane="tick")
    assert payload["available"] is True
    assert payload["authority"] == "official"
    assert payload["verdict"] == "running"
    assert payload["generations"][1]["holdout_delta"] == pytest.approx(400.0)
    assert payload["cumulative_floor"] == 0.40
    assert "수렴" in payload["rule"]


def test_history_payload_on_empty_lane(tmp_path, monkeypatch):
    monkeypatch.setattr(gr, "_path", lambda: tmp_path / "missing.jsonl")
    payload = gr.history_payload(lane="min")
    assert payload["generations"] == []
    assert payload["verdict"] == "not_started"
    assert payload["rollback_to"] is None
