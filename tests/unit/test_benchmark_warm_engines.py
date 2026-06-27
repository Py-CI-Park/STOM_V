from pathlib import Path

from ai_strategy_loop.scripts import benchmark_warm_engines as B


class _FakeSession:
    closed = False

    def __init__(self, config):
        self.config = config
        self.i = 0

    def prepare(self):
        return {
            "status": "ok",
            "back_count": 7,
            "timing": {
                "prepare_elapsed": 30.0,
                "engine_count": self.config.engine_count,
                "back_count": 7,
                "status": "ok",
            },
        }

    def run(self, buy, sell, timeout=None):
        self.i += 1
        return {
            "status": "success",
            "csv_path": f"result-{self.i}.csv",
            "metrics": {"trade_count": self.i},
            "timing": {
                "run_elapsed": 10.0 + self.i,
                "timeout": False,
                "timeout_count": 0,
                "recovery_attempts": 0,
                "engine_count": self.config.engine_count,
                "back_count": 7,
                "status": "success",
            },
        }

    def close(self):
        self.closed = True


def _args(**overrides):
    base = dict(
        engines=[32, 64],
        repeat=3,
        buy="C_S_3_B_902_Min",
        sell="C_S_3_S_902_Min",
        timeframe="min",
        start=20250101,
        end=20251231,
        start_time=90000,
        end_time=92800,
        full_session=False,
        avg_time=30,
        betting="5",
        timeout=600,
        run_timeout=120,
        process=None,
        preset="fast",
        out=Path("artifacts/bench.json"),
    )
    base.update(overrides)
    return B.BenchmarkArgs(**base)


def test_run_engine_measurement_records_prepare_run_and_fixed_config():
    measurement = B.run_engine_measurement(_args(repeat=2), 32, session_cls=_FakeSession)

    assert measurement["engine_count"] == 32
    assert measurement["status"] == "ok"
    assert measurement["prepare"]["back_count"] == 7
    assert measurement["summary"]["repeat_requested"] == 2
    assert measurement["summary"]["repeat_completed"] == 2
    assert measurement["summary"]["success_rate"] == 1.0
    assert measurement["summary"]["run_elapsed_sec"]["p50"] == 11.5
    assert measurement["summary"]["amortized_total_p50_sec"] == 26.5
    assert measurement["config"]["engine_count"] == 32


def test_decision_selects_64_when_threshold_passes_without_regression():
    baseline = {
        "engine_count": 32,
        "status": "ok",
        "summary": {
            "success_rate": 1.0,
            "timeout_count": 0,
            "recovery_attempts": 0,
            "amortized_total_p50_sec": 100.0,
            "run_elapsed_sec": {"p50": 80.0, "p95": 100.0},
        },
    }
    candidate = {
        "engine_count": 64,
        "status": "ok",
        "summary": {
            "success_rate": 1.0,
            "timeout_count": 0,
            "recovery_attempts": 0,
            "amortized_total_p50_sec": 80.0,
            "run_elapsed_sec": {"p50": 60.0, "p95": 75.0},
        },
    }

    decision = B.decide_engine_count([baseline, candidate])

    assert decision["selected_engine_count"] == 64
    assert decision["changed_default"] is True
    assert decision["reason"] == "candidate_passed_threshold_without_stability_regression"


def test_decision_keeps_32_when_64_has_timeout_regression():
    baseline = {
        "engine_count": 32,
        "status": "ok",
        "summary": {
            "success_rate": 1.0,
            "timeout_count": 0,
            "recovery_attempts": 0,
            "amortized_total_p50_sec": 100.0,
            "run_elapsed_sec": {"p50": 80.0, "p95": 100.0},
        },
    }
    candidate = {
        "engine_count": 64,
        "status": "ok",
        "summary": {
            "success_rate": 1.0,
            "timeout_count": 1,
            "recovery_attempts": 1,
            "amortized_total_p50_sec": 50.0,
            "run_elapsed_sec": {"p50": 40.0, "p95": 45.0},
        },
    }

    decision = B.decide_engine_count([baseline, candidate])

    assert decision["selected_engine_count"] == 32
    assert decision["changed_default"] is False
    assert decision["reason"] == "candidate_stability_regression_or_failure"

def test_decision_keeps_32_when_candidate_measurement_missing():
    baseline = {
        "engine_count": 32,
        "status": "ok",
        "summary": {
            "success_rate": 1.0,
            "timeout_count": 0,
            "recovery_attempts": 0,
            "amortized_total_p50_sec": 100.0,
            "run_elapsed_sec": {"p50": 80.0, "p95": 100.0},
        },
    }

    decision = B.decide_engine_count([baseline])

    assert decision["selected_engine_count"] == 32
    assert decision["changed_default"] is False
    assert decision["reason"] == "baseline_or_candidate_missing"


def test_decision_keeps_32_when_baseline_measurement_missing_even_if_64_succeeds():
    candidate = {
        "engine_count": 64,
        "status": "ok",
        "summary": {
            "success_rate": 1.0,
            "timeout_count": 0,
            "recovery_attempts": 0,
            "amortized_total_p50_sec": 50.0,
            "run_elapsed_sec": {"p50": 40.0, "p95": 45.0},
        },
    }

    decision = B.decide_engine_count([candidate])

    assert decision["selected_engine_count"] == 32
    assert decision["changed_default"] is False
    assert decision["reason"] == "baseline_or_candidate_missing"


def test_decision_keeps_32_when_no_successful_runs():
    baseline = {
        "engine_count": 32,
        "status": "ok",
        "summary": {
            "success_rate": 0.0,
            "timeout_count": 0,
            "recovery_attempts": 0,
            "amortized_total_p50_sec": 100.0,
            "run_elapsed_sec": {"p50": 80.0, "p95": 100.0},
        },
    }
    candidate = {
        "engine_count": 64,
        "status": "ok",
        "summary": {
            "success_rate": 0.0,
            "timeout_count": 0,
            "recovery_attempts": 0,
            "amortized_total_p50_sec": 50.0,
            "run_elapsed_sec": {"p50": 40.0, "p95": 45.0},
        },
    }

    decision = B.decide_engine_count([baseline, candidate])

    assert decision["selected_engine_count"] == 32
    assert decision["changed_default"] is False
    assert decision["reason"] == "no_successful_baseline_or_candidate_runs"

def test_artifact_contains_input_set_and_decision():
    args = _args()
    artifact = B.build_artifact(args, [])

    assert artifact["schemaVersion"] == 1
    assert artifact["kind"] == "process-research-engine-benchmark"
    assert artifact["inputSet"]["engines"] == [32, 64]
    assert artifact["inputSet"]["buy"] == "C_S_3_B_902_Min"
    assert artifact["decision"]["selected_engine_count"] == 32
