"""Run the sealed, outcome-free RES-02 Event Gate against an immutable SQLite DB."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from ai_strategy_loop.revision.mcap_event_contract import (
    CandidateManifest,
    EventGateContractError,
    Res01Preregistration,
    SourceFingerprint,
)
from ai_strategy_loop.revision.mcap_event_inputs import validate_sealed_candidates
from ai_strategy_loop.revision.mcap_event_report import (
    CandidateEventRow,
    DatabaseIdentity,
    EventGateEvidence,
    EventThresholds,
    ManifestIdentity,
    ScanStatistics,
    select_event_eligible,
)
from ai_strategy_loop.revision.mcap_event_scan import scan_event_gate
from utility.sqlite_readonly import sqlite_fingerprint

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = (
    ROOT
    / "docs/research/quant_scoring_pipeline/evidence/2026-08-15_d3_candidate_manifest.json"
)
DEFAULT_PREREG = (
    ROOT
    / "docs/research/quant_scoring_pipeline/evidence/2026-08-26_res01_lt3000_prereg.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "docs/research/quant_scoring_pipeline/evidence/2026-08-26_res02_event_gate.json"
)


@dataclass(frozen=True, slots=True)
class CliArgs:
    database: Path
    manifest: Path
    prereg: Path
    output: Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _git_value(*arguments: str) -> str:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def _progress(done: int, total: int, code: str) -> None:
    print(f"[RES02_EVENT] symbols={done}/{total} last={code}", flush=True)


def _validate_database(path: Path, prereg: Res01Preregistration) -> SourceFingerprint:
    fingerprint = SourceFingerprint.model_validate(sqlite_fingerprint(path))
    source = prereg.source
    if (
        fingerprint.size != source.database_expected_bytes
        or fingerprint.hash_mode != source.database_fingerprint_mode
        or fingerprint.sha256 != source.database_fingerprint_sha256
    ):
        raise EventGateContractError("source database identity mismatch")
    return fingerprint


def run(
    *,
    database: Path,
    manifest_path: Path,
    prereg_path: Path,
) -> EventGateEvidence:
    manifest = CandidateManifest.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )
    prereg = Res01Preregistration.model_validate_json(
        prereg_path.read_text(encoding="utf-8")
    )
    file_sha = _sha256(manifest_path)
    candidates, canonical_sha = validate_sealed_candidates(
        manifest, prereg, manifest_file_sha256=file_sha
    )
    fingerprint = _validate_database(database, prereg)
    outcome = scan_event_gate(
        database,
        candidates=candidates,
        folds=prereg.development_folds,
        gate=prereg.event_gate,
        window_start=prereg.source.window_start,
        window_end_exclusive=prereg.source.window_end_exclusive,
        progress=_progress,
    )
    selected_by_family = select_event_eligible(
        candidates,
        outcome.estimates,
        manifest,
        prereg.candidate_universe.families,
    )
    selected_ids = tuple(
        candidate_id
        for family in prereg.candidate_universe.families
        for candidate_id in selected_by_family[family]
    )
    estimates = {row.candidate_id: row for row in outcome.estimates}
    selected_set = set(selected_ids)
    candidate_rows = tuple(
        CandidateEventRow(
            candidate_id=candidate.candidate_id,
            family_id=candidate.family_id,
            parameters=candidate.parameters,
            source_sha256=candidate.source_sha256,
            total_events=estimates[candidate.candidate_id].total_events,
            distinct_days=estimates[candidate.candidate_id].distinct_days,
            distinct_symbols=estimates[candidate.candidate_id].distinct_symbols,
            fold_counts=estimates[candidate.candidate_id].fold_counts,
            verdict=estimates[candidate.candidate_id].verdict,
            selected_for_official_execution=candidate.candidate_id in selected_set,
        )
        for candidate in candidates
    )
    eligible_counts = {
        family: sum(
            row.family_id == family and row.verdict == "EVENT_COUNT_PASS"
            for row in candidate_rows
        )
        for family in prereg.candidate_universe.families
    }
    passed = bool(selected_ids)
    return EventGateEvidence(
        generated_at=datetime.now(timezone.utc).isoformat(),
        contract_id=prereg.contract_id,
        authority=prereg.authority,
        implementation_branch=_git_value("branch", "--show-current"),
        implementation_head_sha=_git_value("rev-parse", "HEAD"),
        database=DatabaseIdentity(
            path=fingerprint.path,
            size_bytes=fingerprint.size,
            modified_ns=fingerprint.mtime_ns,
            fingerprint_mode=fingerprint.hash_mode,
            fingerprint_sha256=fingerprint.sha256,
        ),
        manifest=ManifestIdentity(
            path=manifest_path.relative_to(ROOT).as_posix(),
            file_sha256=file_sha,
            canonical_sha256=canonical_sha,
            window_contract_sha256=manifest.window_contract.contract_sha256,
            candidate_count=len(candidates),
            source_identity_match_count=len(candidates),
        ),
        thresholds=EventThresholds(
            min_total_events=prereg.event_gate.min_total_events,
            min_events_per_fold=prereg.event_gate.min_events_per_fold,
            min_distinct_days=prereg.event_gate.min_distinct_days,
            min_distinct_symbols=prereg.event_gate.min_distinct_symbols,
        ),
        scan=ScanStatistics(
            moneytop_rows=outcome.stats.moneytop_rows,
            scheduled_symbols=outcome.stats.scheduled_symbols,
            missing_symbol_tables=outcome.stats.missing_symbol_tables,
            code_days=outcome.stats.code_days,
            scanned_code_days=outcome.stats.scanned_code_days,
            tick_rows=outcome.stats.tick_rows,
            base_eligible_tick_rows=outcome.stats.base_eligible_tick_rows,
            elapsed_seconds=outcome.stats.elapsed_seconds,
        ),
        candidates=candidate_rows,
        family_eligible_counts=eligible_counts,
        selected_by_family=selected_by_family,
        selected_candidate_ids=selected_ids,
        selection_method="performance_blind_maximin_within_event_eligible_family",
        verdict="EVENT_GATE_PASS" if passed else "EVENT_GATE_STOP",
        stop_code=None if passed else "STOP_NO_EVENT_QUALIFIED_G0_CANDIDATE",
        next_gate="RES02_G0_OFFICIAL_FOLD_EXECUTION" if passed else "RES02_STOP",
    )


def _parse_args() -> CliArgs:
    parser = argparse.ArgumentParser()
    _ = parser.add_argument("--database", type=Path, required=True)
    _ = parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    _ = parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    _ = parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    namespace = parser.parse_args()
    return CliArgs(
        database=cast(Path, namespace.database),
        manifest=cast(Path, namespace.manifest),
        prereg=cast(Path, namespace.prereg),
        output=cast(Path, namespace.output),
    )


def main() -> None:
    args = _parse_args()
    output = args.output.resolve()
    if output.exists():
        raise EventGateContractError(
            f"append-only Event Gate output already exists: {output}"
        )
    report = run(
        database=args.database.resolve(),
        manifest_path=args.manifest.resolve(),
        prereg_path=args.prereg.resolve(),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    _ = output.write_text(
        report.model_dump_json(indent=2, by_alias=True) + "\n", encoding="utf-8"
    )
    print(
        f"[RES02_EVENT] verdict={report.verdict} selected={len(report.selected_candidate_ids)} output={output}",
        flush=True,
    )


if __name__ == "__main__":
    main()
