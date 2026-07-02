"""T5.1 — 양성대조(positive control) 자동 판정 단위 테스트.

검증:
  (a) 합성 챔피언 4/4 통과 → verdict=gate_healthy, all_passed=True.
  (b) 1개 실패 → verdict=gate_regression_suspected + 실패 사유 노출.
  (c) 증거 부재(빈 목록 / metrics 없음 / 기준선 파일 없음 / 수익 지표 없음)
      → 정직 에러(조용한 통과 금지).
  (d) scripts/run_positive_control.py receipt 스키마 + 쓰기 정책(--report만).
  (e) 판정이 기존 하드 게이트(compute_fitness)와 동일 기준임(간접 —
      mdd_cap/min_daily 위반 사유 문자열이 게이트 사유와 일치).
"""

import importlib.util
import json
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_strategy_loop.fitness.positive_control import (
    AUTHORITY,
    VERDICT_HEALTHY,
    VERDICT_REGRESSION,
    PositiveControlGateConfig,
    evaluate_positive_control,
    load_champion_baselines,
)


def _champion(name, *, profit=10_000_000, mdd=10.0, daily=0.4, trades=300, cagr=15.0):
    """발굴 게이트(mdd_cap=20 · min_daily 0.05)를 여유 통과하는 합성 챔피언."""
    return {
        "name": name,
        "metrics": {
            "cagr": cagr,
            "mdd_pct": mdd,
            "trade_count": trades,
            "total_profit_krw": profit,
            "daily_avg_trades": daily,
        },
    }


def _four_champions():
    """2026-06-16 진단(4/4 통과)을 본뜬 합성 챔피언 4종."""
    return [
        _champion("FROZEN_THETA", profit=10_965_479, mdd=10.04, daily=0.40, trades=272),
        _champion("T2C1", profit=9_550_593, mdd=13.76, daily=0.40, trades=317),
        _champion("T2C2", profit=9_642_207, mdd=13.89, daily=0.40, trades=322),
        _champion("T2C3", profit=9_866_240, mdd=11.30, daily=0.50, trades=356),
    ]


class TestEvaluatePositiveControl:
    def test_all_pass_is_gate_healthy(self):
        result = evaluate_positive_control(_four_champions())
        assert result["total"] == 4
        assert result["passed_count"] == 4
        assert result["all_passed"] is True
        assert result["verdict"] == VERDICT_HEALTHY
        assert result["authority"] == AUTHORITY == "advisory_only"
        assert all(c["passed"] for c in result["per_champion"])
        assert all(c["reasons"] == [] for c in result["per_champion"])

    def test_one_failure_is_regression_suspected_with_reason(self):
        champions = _four_champions()
        champions[2] = _champion("T2C2", mdd=35.0)  # mdd_cap=20 초과 → 게이트 탈락.
        result = evaluate_positive_control(champions)
        assert result["passed_count"] == 3
        assert result["all_passed"] is False
        assert result["verdict"] == VERDICT_REGRESSION
        failed = [c for c in result["per_champion"] if not c["passed"]]
        assert len(failed) == 1
        assert failed[0]["name"] == "T2C2"
        # 사유는 기존 게이트(compute_fitness)의 first-violation 문자열.
        assert failed[0]["reasons"] and "mdd" in failed[0]["reasons"][0]
        assert "mdd_cap" in failed[0]["reasons"][0]

    def test_loss_champion_fails_with_profit_reason(self):
        champions = [_champion("LOSER", profit=-1_000_000)]
        result = evaluate_positive_control(champions)
        assert result["verdict"] == VERDICT_REGRESSION
        assert "total_profit" in result["per_champion"][0]["reasons"][0]

    def test_low_frequency_fails_daily_gate(self):
        champions = [_champion("SPARSE", daily=0.01)]  # min_daily_trades=0.05 미만.
        result = evaluate_positive_control(champions)
        assert result["all_passed"] is False
        assert "min_daily_trades" in result["per_champion"][0]["reasons"][0]

    def test_gate_config_mapping_override(self):
        # 기본 게이트(20)로는 통과하는 mdd=15 챔피언이 mdd_cap=10에서는 탈락.
        champions = [_champion("EDGE", mdd=15.0)]
        healthy = evaluate_positive_control(champions)
        assert healthy["all_passed"] is True
        strict = evaluate_positive_control(champions, gate_config={"mdd_cap": 10.0})
        assert strict["verdict"] == VERDICT_REGRESSION
        assert strict["gate_config"]["mdd_cap"] == 10.0

    def test_gate_config_object_passthrough(self):
        config = PositiveControlGateConfig(mdd_cap=5.0)
        result = evaluate_positive_control([_champion("EDGE", mdd=15.0)], config)
        assert result["all_passed"] is False

    def test_empty_champions_honest_error(self):
        with pytest.raises(ValueError, match="비어"):
            evaluate_positive_control([])

    def test_missing_metrics_honest_error(self):
        with pytest.raises(ValueError, match="metrics"):
            evaluate_positive_control([{"name": "NO_EVIDENCE"}])

    def test_flat_runner_output_entry_accepted(self):
        flat = {
            "name": "FLAT",
            "cagr": 20.0,
            "mdd_pct": 8.0,
            "trade_count": 100,
            "total_profit_krw": 5_000_000,
            "daily_avg_trades": 0.4,
        }
        result = evaluate_positive_control([flat])
        assert result["all_passed"] is True


class TestLoadChampionBaselines:
    def test_loads_real_reference_file(self):
        champions = load_champion_baselines()
        assert len(champions) == 19  # 인간 우수 전략 19종 전부 수익 지표 보유.
        first = champions[0]
        assert set(first) == {"name", "metrics"}
        m = first["metrics"]
        assert m["total_profit_krw"] > 0
        assert "mdd_pct" in m and "daily_avg_trades" in m and "tpi" in m

    def test_real_baselines_pass_discovery_gate(self):
        # 실제 기준선 19종은 기본 발굴 게이트를 전원 통과해야 한다(양성대조 성립).
        result = evaluate_positive_control(load_champion_baselines())
        assert result["verdict"] == VERDICT_HEALTHY

    def test_missing_file_honest_error(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="기준선"):
            load_champion_baselines(str(tmp_path / "nope.json"))

    def test_no_profit_strategies_honest_error(self, tmp_path):
        path = tmp_path / "ref.json"
        path.write_text(
            json.dumps({"strategies": [{"id": "#1", "mdd_pct": 3.0}]}),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="profit_krw"):
            load_champion_baselines(str(path))

    def test_empty_strategies_honest_error(self, tmp_path):
        path = tmp_path / "ref.json"
        path.write_text(json.dumps({"strategies": []}), encoding="utf-8")
        with pytest.raises(ValueError, match="strategies"):
            load_champion_baselines(str(path))


def _load_script_module():
    """scripts/run_positive_control.py를 모듈로 로드한다(패키지 아님)."""
    script_path = os.path.join(PROJECT_ROOT, "scripts", "run_positive_control.py")
    spec = importlib.util.spec_from_file_location("run_positive_control", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestRunPositiveControlScript:
    def _write_results(self, tmp_path, champions):
        path = tmp_path / "champ_results.json"
        path.write_text(json.dumps(champions, ensure_ascii=False), encoding="utf-8")
        return path

    def test_receipt_schema_and_report_write(self, tmp_path, capsys):
        mod = _load_script_module()
        results = self._write_results(tmp_path, _four_champions())
        report = tmp_path / "out" / "receipt.json"
        code = mod.main([str(results), "--report", str(report)])
        assert code == 0  # gate_healthy.

        receipt = json.loads(report.read_text(encoding="utf-8"))
        # receipt 스키마 계약.
        for key in (
            "schema", "generated_at", "authority", "inputs", "passed_count",
            "total", "all_passed", "per_champion", "verdict", "gate_config",
        ):
            assert key in receipt, f"receipt에 {key} 누락"
        assert receipt["schema"] == mod.RECEIPT_SCHEMA == "positive_control_receipt_v1"
        assert receipt["authority"] == "advisory_only"
        assert receipt["inputs"] == [str(results)]
        assert receipt["total"] == 4 and receipt["all_passed"] is True
        per = receipt["per_champion"][0]
        assert {"name", "passed", "reasons", "gate_metrics"} <= set(per)
        # stdout에도 동일 receipt(print 아님 — sys.stdout.write) 출력.
        out = capsys.readouterr().out
        assert json.loads(out)["schema"] == "positive_control_receipt_v1"

    def test_regression_exit_code_and_reasons(self, tmp_path, capsys):
        mod = _load_script_module()
        champions = _four_champions()
        champions[0] = _champion("FROZEN_THETA", mdd=35.0)
        results = self._write_results(tmp_path, champions)
        code = mod.main([str(results)])
        assert code == 1  # gate_regression_suspected.
        receipt = json.loads(capsys.readouterr().out)
        assert receipt["verdict"] == "gate_regression_suspected"

    def test_gate_config_json_extraction(self, tmp_path, capsys):
        mod = _load_script_module()
        gate_json = tmp_path / "run_cfg.json"
        gate_json.write_text(
            json.dumps({"mdd_cap": 5.0, "min_daily_trades": 0.05, "unrelated": 1}),
            encoding="utf-8",
        )
        results = self._write_results(tmp_path, [_champion("EDGE", mdd=15.0)])
        code = mod.main([str(results), "--gate-config", str(gate_json)])
        assert code == 1  # mdd 15 > cap 5 → 회귀 의심.
        receipt = json.loads(capsys.readouterr().out)
        assert receipt["gate_config"]["mdd_cap"] == 5.0

    def test_no_input_is_usage_error(self, capsys):
        mod = _load_script_module()
        assert mod.main([]) == 2
        assert "입력이 없습니다" in capsys.readouterr().err

    def test_missing_results_file_honest_error(self, tmp_path, capsys):
        mod = _load_script_module()
        assert mod.main([str(tmp_path / "ghost.json")]) == 2
        assert "정직 에러" in capsys.readouterr().err

    def test_bare_csv_input_rejected(self, tmp_path, capsys):
        mod = _load_script_module()
        csv_path = tmp_path / "trades.csv"
        csv_path.write_text("수익금합계\n100\n", encoding="utf-8")
        assert mod.main([str(csv_path)]) == 2
        assert "CSV" in capsys.readouterr().err

    def test_result_csv_attaches_equity(self, tmp_path, capsys):
        mod = _load_script_module()
        csv_path = tmp_path / "trades.csv"
        csv_path.write_text(
            "수익금합계\n100\n200\n300\n", encoding="utf-8"
        )
        champion = {**_champion("WITH_CSV"), "result_csv": str(csv_path)}
        results = self._write_results(tmp_path, [champion])
        assert mod.main([str(results)]) == 0
        receipt = json.loads(capsys.readouterr().out)
        assert receipt["all_passed"] is True

    def test_no_writes_without_report_flag(self, tmp_path, capsys, monkeypatch):
        """--report 미지정 시 어떤 파일도 새로 만들지 않는다(쓰기 정책)."""
        mod = _load_script_module()
        results = self._write_results(tmp_path, _four_champions())
        workdir = tmp_path / "cwd"
        workdir.mkdir()
        monkeypatch.chdir(workdir)
        before = set(os.listdir(workdir))
        assert mod.main([str(results)]) == 0
        capsys.readouterr()
        assert set(os.listdir(workdir)) == before
