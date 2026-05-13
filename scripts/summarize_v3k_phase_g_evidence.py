from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / ".omx" / "reports"
PARITY_REPORT = REPORT_DIR / "v3k-phase-g-parity-latest.json"
BENCHMARK_REPORT = REPORT_DIR / "v3k-phase-g-benchmark-latest.json"

POLICY_MARKER = "V3K_PHASE_G_EVIDENCE_ARCHIVE_POLICY"
RAW_ARTIFACT_POLICY = "RAW_OMX_REPORTS_MUST_REMAIN_UNCOMMITTED"


@dataclass(frozen=True)
class EvidenceFile:
    label: str
    path: Path
    payload: dict[str, Any]
    sha256: str

    @property
    def relative_path(self) -> str:
        return self.path.relative_to(ROOT).as_posix()


def _load_report(label: str, path: Path) -> EvidenceFile:
    if not path.is_file():
        raise FileNotFoundError(
            f"{label} report is missing: {path}. Run scripts/run_v3k_audit_suite.py first."
        )
    raw = path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    return EvidenceFile(label=label, path=path, payload=payload, sha256=hashlib.sha256(raw).hexdigest())


def _assert_common_safety(payload: dict[str, Any], label: str) -> None:
    expected_false = (
        "broker_runtime_called",
        "live_decision_consumption",
        "operating_store_written",
        "runtime_hook_connected",
    )
    if payload.get("passed") is not True:
        raise AssertionError(f"{label} evidence did not pass")
    unsafe = [key for key in expected_false if payload.get(key) is not False]
    if unsafe:
        raise AssertionError(f"{label} evidence has unsafe runtime markers: {unsafe}")


def _parity_summary(report: EvidenceFile) -> dict[str, Any]:
    payload = report.payload
    _assert_common_safety(payload, report.label)
    scenario_summaries = []
    worst_delta = 0.0
    for scenario in payload.get("scenarios", []):
        checks = scenario.get("checks", [])
        scenario_worst = max((float(check.get("relative_delta", 0.0)) for check in checks), default=0.0)
        worst_delta = max(worst_delta, scenario_worst)
        scenario_summaries.append(
            {
                "scenario": scenario.get("scenario"),
                "passed": scenario.get("passed"),
                "result_signal": scenario.get("result_signal"),
                "risk_level": scenario.get("risk_level"),
                "worst_relative_delta": scenario_worst,
            }
        )
    return {
        "schema": payload.get("schema"),
        "generated_at_utc": payload.get("generated_at_utc"),
        "passed": payload.get("passed"),
        "mode": payload.get("mode"),
        "parity_limit": payload.get("parity_limit"),
        "worst_relative_delta": worst_delta,
        "scenarios": scenario_summaries,
        "sha256": report.sha256,
        "relative_path": report.relative_path,
    }


def _benchmark_summary(report: EvidenceFile) -> dict[str, Any]:
    payload = report.payload
    _assert_common_safety(payload, report.label)
    return {
        "schema": payload.get("schema"),
        "generated_at_utc": payload.get("generated_at_utc"),
        "passed": payload.get("passed"),
        "mode": payload.get("mode"),
        "operations": payload.get("operations"),
        "iterations": payload.get("iterations"),
        "elapsed_seconds": payload.get("elapsed_seconds"),
        "max_seconds": payload.get("max_seconds"),
        "baseline_seconds": payload.get("baseline_seconds"),
        "performance_limit": payload.get("performance_limit"),
        "peak_bytes": payload.get("peak_bytes"),
        "max_peak_bytes": payload.get("max_peak_bytes"),
        "baseline_peak_bytes": payload.get("baseline_peak_bytes"),
        "sha256": report.sha256,
        "relative_path": report.relative_path,
    }


def build_summary() -> dict[str, Any]:
    parity = _load_report("phase_g_parity", PARITY_REPORT)
    benchmark = _load_report("phase_g_benchmark", BENCHMARK_REPORT)
    return {
        "policy_marker": POLICY_MARKER,
        "raw_artifact_policy": RAW_ARTIFACT_POLICY,
        "commit_safe": True,
        "raw_reports_committed": False,
        "archive_rule": "Commit docs/update_log summaries and SHA-256 hashes only; keep .omx/reports raw JSON ignored/local unless a later explicit policy changes this.",
        "commands": (
            "python scripts/run_v3k_audit_suite.py",
            "python scripts/summarize_v3k_phase_g_evidence.py --format markdown",
        ),
        "parity": _parity_summary(parity),
        "benchmark": _benchmark_summary(benchmark),
    }


def _emit_markdown(summary: dict[str, Any]) -> str:
    parity = summary["parity"]
    benchmark = summary["benchmark"]
    lines = [
        "# V3K Phase G evidence summary",
        "",
        f"- Policy marker: `{summary['policy_marker']}`",
        f"- Raw artifact policy: `{summary['raw_artifact_policy']}`",
        f"- Commit-safe: `{summary['commit_safe']}`",
        f"- Raw reports committed: `{summary['raw_reports_committed']}`",
        f"- Archive rule: {summary['archive_rule']}",
        "",
        "## Parity evidence",
        "",
        f"- Report: `{parity['relative_path']}`",
        f"- SHA-256: `{parity['sha256']}`",
        f"- Schema: `{parity['schema']}`",
        f"- Generated UTC: `{parity['generated_at_utc']}`",
        f"- Passed: `{parity['passed']}`",
        f"- Parity limit: `{parity['parity_limit']}`",
        f"- Worst relative delta: `{parity['worst_relative_delta']}`",
        "- Scenarios:",
    ]
    for scenario in parity["scenarios"]:
        lines.append(
            "  - "
            f"`{scenario['scenario']}`: passed=`{scenario['passed']}`, "
            f"signal=`{scenario['result_signal']}`, risk=`{scenario['risk_level']}`, "
            f"worst_delta=`{scenario['worst_relative_delta']}`"
        )
    lines.extend(
        [
            "",
            "## Benchmark evidence",
            "",
            f"- Report: `{benchmark['relative_path']}`",
            f"- SHA-256: `{benchmark['sha256']}`",
            f"- Schema: `{benchmark['schema']}`",
            f"- Generated UTC: `{benchmark['generated_at_utc']}`",
            f"- Passed: `{benchmark['passed']}`",
            f"- Operations: `{benchmark['operations']}`",
            f"- Iterations: `{benchmark['iterations']}`",
            f"- Elapsed seconds: `{benchmark['elapsed_seconds']}` / max `{benchmark['max_seconds']}`",
            f"- Peak bytes: `{benchmark['peak_bytes']}` / max `{benchmark['max_peak_bytes']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print a commit-safe V3K Phase G evidence summary without committing raw .omx reports."
    )
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Output format. Default: json.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(tuple(argv or sys.argv[1:]))
    summary = build_summary()
    if args.format == "markdown":
        print(_emit_markdown(summary), end="")
    else:
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
