"""Report consumers cannot bypass the production result quality boundary."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ai_strategy_loop.dashboard import backtest_analysis as analysis
from ai_strategy_loop.dashboard import backtest_api as api
from ai_strategy_loop.dashboard import backtest_report as report
from tests.unit.dashboard.trade_quality_fixtures import official_pair

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("source", ["job", "generation"])
@pytest.mark.parametrize("case", ["partial", "error", "count"])
def test_report_rejects_invalid_sources_before_analysis(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, source: str, case: str,
) -> None:
    header, row = official_pair()
    path = tmp_path / "report.csv"
    path.write_text(header + row + ("bad\n" if case == "partial" else ""), encoding="utf-8")
    record = {"available": True, "status": "error" if case == "error" else "success",
              "csv_path": str(path), "metrics": {"trade_count": 2 if case == "count" else 1},
              "spec": {}}

    class Manager:
        def get(self, *args, **kwargs):
            return record

    generation = {"status": "error" if case == "error" else "ok",
                  "csv_path": str(path), "trade_count": record["metrics"]["trade_count"]}
    monkeypatch.setattr(api, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(api, "get_job_manager", Manager)
    monkeypatch.setattr(api, "_gen_row_readonly", lambda *args: generation)
    calls: list[str] = []

    def forbidden(*args, **kwargs):
        calls.append("computed")
        return {"summary": {"trade_count": 0}}

    monkeypatch.setattr(analysis, "full_analysis", forbidden)
    monkeypatch.setattr(analysis, "monte_carlo", forbidden)
    payload = (api._report_payload_for_job("fixture", None, None) if source == "job"
               else api._report_payload_for_run("fixture", 1))
    assert calls == []
    assert payload["analysis"] is None and payload["montecarlo"] is None
    assert payload["analysis_ready"] is False
    html = report.render_report(payload)
    assert "자료 품질" in html
    assert 'id="stom-report-quality"' in html


@pytest.mark.parametrize("source", ["job", "generation"])
def test_report_uses_checked_snapshot_without_legacy_reread(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, source: str,
) -> None:
    header, row = official_pair()
    path = tmp_path / "report.csv"
    path.write_text(header + row, encoding="utf-8")

    class Manager:
        def get(self, *args, **kwargs):
            return {"available": True, "status": "success", "csv_path": str(path),
                    "metrics": {"trade_count": 1}, "spec": {}}

    monkeypatch.setattr(api, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(api, "get_job_manager", Manager)
    monkeypatch.setattr(api, "_gen_row_readonly", lambda *args: {
        "status": "ok", "csv_path": str(path), "trade_count": 1})
    rereads: list[str] = []

    def legacy(path):
        rereads.append(str(path))
        return []

    monkeypatch.setattr(analysis, "load_trades_csv", legacy)
    payload = (api._report_payload_for_job("fixture", None, None) if source == "job"
               else api._report_payload_for_run("fixture", 1))
    assert rereads == []
    assert payload["analysis_ready"] is True
    assert payload["analysis"]["summary"]["trade_count"] == 1
    assert payload["data_quality"]["source_sha256"] in report.render_report(payload)


def test_missing_generation_report_is_summary_without_empty_chart_sections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(api, "_gen_row_readonly", lambda *args: {
        "status": "rejected", "csv_path": None, "trade_count": 0,
        "profit": -5000, "mdd": float("nan"), "created_at": 1e300,
    })
    payload = api._report_payload_for_run("fixture", 1)
    html = report.render_report(payload)
    assert "저장된 미검증 요약" in html and "-5,000" in html
    assert 'id="sec-equity"' not in html and 'class="toc"' not in html
    assert payload["montecarlo"] is None and payload["analysis"] is None
    assert payload["meta"]["trade_count"] == 0


def test_quality_json_is_finite_and_script_safe() -> None:
    from ai_strategy_loop.dashboard.report_quality import quality_html
    value = quality_html({"analysis_ready": False, "execution_status": "</script><script>alert(1)</script>",
                          "data_quality": {"status": '<img src=x onerror="alert(1)">', "raw_count": float("nan")}})
    assert '<script>alert(1)</script>' not in value
    assert '<img src=x' not in value
    assert '"raw_count": null' in value
