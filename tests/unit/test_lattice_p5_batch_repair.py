# -*- coding: utf-8 -*-
"""Regression tests for Plan B P5 root-cause repair."""

import sys

from ai_strategy_loop.controller import loop as L
from ai_strategy_loop.scripts import claude_candidate_batch_eval as batch_eval


def test_warm_success_without_csv_or_metrics_is_no_trades_not_error():
    outcome = L._warm_to_outcome({
        "status": "success",
        "message": "backtest complete",
        "csv_path": None,
        "metrics": None,
    })

    assert outcome.ok is False
    assert outcome.status == "no_trades"
    assert "no_trades" in outcome.reason
    assert "csv=no" in outcome.reason
    assert "metrics=no" in outcome.reason


def test_batch_eval_payload_preserves_no_trades_status():
    outcome = L.BacktestOutcome(
        False,
        "no_trades",
        None,
        None,
        "warm backtest no_trades: status=success csv=no metrics=no",
    )

    payload = batch_eval._failed_generation_payload(
        "lattice_v1:tick_0900_small_low:momentum_breakout",
        outcome,
    )

    assert payload["status"] == "no_trades"
    assert payload["gate_passed"] is False
    assert payload["trade_count"] == 0
    assert payload["daily_avg_trades"] == 0.0
    assert payload["strategy_gist"] == "lattice_v1:tick_0900_small_low:momentum_breakout"
    assert "backtest failed" not in payload["reason"]


def test_batch_eval_fail_fast_timeout_records_row_and_aborts(monkeypatch):
    pairs = [
        {"label": "timeout_pair", "buy": "BUY_TIMEOUT", "sell": "SELL_TIMEOUT"},
        {"label": "must_not_run", "buy": "BUY_LATE", "sell": "SELL_LATE"},
    ]
    recorded = []
    finished = []

    class _Cfg:
        bt_warm_run_timeout = 1

    class _State:
        def start_run(self, config, run_id=None):
            return run_id

        def record_generation(self, run_id, gen_no, **payload):
            recorded.append((run_id, gen_no, payload))

        def finish_run(self, run_id, status="complete"):
            finished.append((run_id, status))

    class _Warm:
        def __init__(self, config):
            self.calls = 0

        def prepare(self):
            return {"status": "ok", "back_count": 1}

        def run(self, buy, sell, *, timeout=None, recover_on_timeout=True):
            self.calls += 1
            assert buy == "BUY_TIMEOUT"
            assert recover_on_timeout is False
            return {
                "status": "error",
                "message": "백테스트 시간 초과 (1초) (엔진 복구 생략: fail-fast timeout)",
                "metrics": None,
            }

        def close(self):
            pass

    def _load_json(path):
        return pairs if path == "pairs.json" else {}

    monkeypatch.setattr(batch_eval, "_load_json", _load_json)
    monkeypatch.setattr(batch_eval, "config_from_dict", lambda data: _Cfg())
    monkeypatch.setattr(batch_eval, "_build_warm_btconfig", lambda config: object())
    # v5.13.2 — 이 테스트가 지키는 계약은 "타임아웃이 나면 1건 기록하고 즉시 중단"이다.
    #   배치에 사전 검증(preflight) 게이트가 생기면서, 실재하지 않는 합성 전략명은
    #   엔진에 닿기 전에 걸러져 타임아웃 경로를 아예 밟지 못한다. 검증 대상이 다르므로
    #   여기서는 preflight 를 통과시켜 타임아웃 경로만 시험한다(게이트 자체는
    #   test_strategy_preflight 가 검증).
    import ai_strategy_loop.controller.strategy_preflight as _preflight
    monkeypatch.setattr(_preflight, "preflight_pair",
                        lambda buy, sell, **kw: _preflight.PreflightResult(True))
    monkeypatch.setattr(batch_eval.bootstrap, "ensure_loop_db_engine_compat", lambda: None)
    monkeypatch.setattr(batch_eval, "LoopState", _State)
    monkeypatch.setattr(batch_eval, "WarmBacktestSession", _Warm)
    monkeypatch.setattr(batch_eval, "publish_batch_state", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "claude_candidate_batch_eval",
            "--pairs-json",
            "pairs.json",
            "--config-json",
            "config.json",
            "--run-id",
            "rid",
            "--fail-fast-timeout",
        ],
    )

    assert batch_eval.main() == 0

    assert len(recorded) == 1
    run_id, gen_no, payload = recorded[0]
    assert (run_id, gen_no) == ("rid", 0)
    assert payload["status"] == "error"
    assert payload["strategy_gist"] == "timeout_pair"
    assert "시간 초과" in payload["reason"]
    assert finished == [("rid", "complete")]
