"""alpha_lab.discipline 단위 테스트 (WBS v3 P1-1·P1-5 — A1/A21/A6/A4).

실행: python -m pytest tests/unit/test_alpha_discipline.py -q
실DB 불필요 — 합성 픽스처(tmp_path) 중심. 실물 원장/코퍼스 테스트는
존재할 때만(skipif) 읽기 전용으로 수행한다.
"""

from __future__ import annotations

import ast
import datetime as dt
import contextlib
import importlib.machinery
import hashlib
import json
import os
import multiprocessing
from pathlib import Path
import shutil
import subprocess

import pytest

from alpha_lab.discipline import evidence, ledger, lint, measure_gate, prereg, trials_report, windows

ROOT = Path(__file__).resolve().parents[2]
REAL_LEDGER = (
    ROOT
    / "docs"
    / "research"
    / "condition_research"
    / "research_runs"
    / "alpha_restart_20260710"
    / "n_trials_ledger.jsonl"
)
REAL_RUNS_DIR = REAL_LEDGER.parent

VALID_ROW = {
    "ts": "2026-07-14T00:03:00+00:00",
    "series": "D1",
    "window": "2022-03-23~2023-12-31(발견창)",
    "trial_type": "b(오프라인 봉인 판정)",
    "target": "테스트 대상 요약",
    "result": "테스트 결과 요약",
    "session": "unit-test",
}


def _row(**overrides) -> dict:
    return {**VALID_ROW, **overrides}


# ---------------------------------------------------------------------------
# windows — 창-지위 가드
# ---------------------------------------------------------------------------


class TestWindowsGuard:
    def test_discovery_window_passes(self):
        status = windows.assert_measurement_window(
            "2022-03-23", "2023-12-31", "S-트랙 지도"
        )
        assert status == "DISCOVERY"

    def test_known_overlap_rejected_with_ledger_quote(self):
        with pytest.raises(windows.WindowViolation) as excinfo:
            windows.assert_measurement_window("2024-06-01", "2025-03-01", "S-트랙 지도")
        message = str(excinfo.value)
        assert "선택·튜닝 금지" in message  # 원장 §1 known 행 인용
        assert "veto 전용" in message

    def test_full_known_window_rejected(self):
        with pytest.raises(windows.WindowViolation):
            windows.assert_measurement_window("2025-01-01", "2026-02-27", "신규 가설")

    def test_absent_window_rejected(self):
        with pytest.raises(windows.WindowViolation) as excinfo:
            windows.assert_measurement_window("2026-03-01", "2026-06-01", "신규 가설")
        assert "데이터 없음, 수집하지 않음" in str(excinfo.value)

    def test_pre_data_rejected(self):
        with pytest.raises(windows.WindowViolation):
            windows.assert_measurement_window("2021-01-01", "2022-06-01", "신규 가설")

    def test_2024_known_for_exit_lever_series(self):
        with pytest.raises(windows.WindowViolation) as excinfo:
            windows.assert_measurement_window(
                "2024-01-01", "2024-12-31", "청산 레버(P5·D5 계열)"
            )
        assert "청산 레버·챔피언 선정 계열 가설에는 known" in str(excinfo.value)

    def test_2024_known_for_champion_series(self):
        with pytest.raises(windows.WindowViolation):
            windows.assert_measurement_window(
                "2024-03-01", "2024-04-01", "챔피언 선정·앙상블(v4 계열)"
            )

    def test_2024_conditional_requires_prereg(self):
        with pytest.raises(windows.WindowViolation) as excinfo:
            windows.assert_measurement_window("2024-01-01", "2024-06-30", "신규 스냅샷 가설")
        assert "사전등록 필수" in str(excinfo.value)

    def test_2024_conditional_passes_with_prereg(self):
        status = windows.assert_measurement_window(
            "2024-01-01",
            "2024-06-30",
            "신규 스냅샷 가설",
            conditional_2024_prereg="봉인 문서 plans/2026-07-xx_x.md (커밋 deadbeef)",
        )
        assert status == "CONDITIONAL_2024"

    def test_reversed_range_valueerror(self):
        with pytest.raises(ValueError):
            windows.assert_measurement_window("2023-12-31", "2022-03-23", "신규 가설")

    def test_empty_series_kind_rejected(self):
        with pytest.raises(ValueError):
            windows.assert_measurement_window("2022-04-01", "2022-05-01", "  ")


class TestDateTokens:
    def test_parse_date_formats(self):
        assert windows.parse_date("2025-04-07") == dt.date(2025, 4, 7)
        assert windows.parse_date("20250407") == dt.date(2025, 4, 7)
        assert windows.parse_date(dt.date(2022, 3, 23)) == dt.date(2022, 3, 23)
        with pytest.raises(ValueError):
            windows.parse_date("2025/04/07")

    def test_extract_iso_compact_yearmonth(self):
        tokens = windows.extract_date_tokens("경계 2025-04-07, 표본 20250526, 이후 2025-04")
        kinds = {t["kind"] for t in tokens}
        assert kinds == {"full", "compact", "yearmonth"}
        yearmonth = next(t for t in tokens if t["kind"] == "yearmonth")
        assert yearmonth["start"] == dt.date(2025, 4, 1)
        assert yearmonth["end"] == dt.date(2025, 4, 30)

    def test_invalid_dates_skipped(self):
        assert windows.extract_date_tokens("20259999 2025-13-01 값 20,250,526원") == []

    def test_iso_not_double_counted_as_yearmonth(self):
        tokens = windows.extract_date_tokens("2025-04-07 하루만")
        assert [t["kind"] for t in tokens] == ["full"]


# ---------------------------------------------------------------------------
# ledger — 단일 기입 API
# ---------------------------------------------------------------------------


class TestAppendTrial:
    def test_v1_writer_is_blocked_before_creating_an_arbitrary_path(self, tmp_path):
        path = tmp_path / "arbitrary-v1.jsonl"
        with pytest.raises(ledger.LegacyLedgerWriteBlockedError):
            ledger.append_trial(path=path, **VALID_ROW)
        assert not path.exists()
def _sealed_contract(*, roots, dynamic_python=(), non_python=(), authority_paths=None, ledger_path="ledger.jsonl") -> str:
    contract = {
        "schema_version": 2,
        "hypothesis_id": "H-unit",
        "discovery_window": {"start": "2022-03-23", "end": "2023-12-31"},
        "primary_estimand": "mean spread",
        "sample_floors": {"qualified": 2},
        "multiplicity_family": "unit family",
        "kill_rule": "non-positive effect",
        "ledger_path": ledger_path,
        "authority_paths": authority_paths if authority_paths is not None else {
            "seal_dir": "seals",
            "promotions_dir": "promotions",
            "catalog_dir": "catalog",
            "target_db": "measure.py",
            "journal_dir": "journal",
            "backup_dir": "backups",
        },
        "dependency_roots": list(roots),
        "dynamic_python_dependencies": list(dynamic_python),
        "non_python_dependencies": list(non_python),
    }
    return "> 지위: **SEALED**\n완성본\n```json prereg-contract-v2\n" + json.dumps(contract, sort_keys=True) + "\n```\n"
def _canonical_seal_path(root, document):
    return root / "seals" / f"{hashlib.sha256(document.read_bytes()).hexdigest()}.seal.json"
@contextlib.contextmanager
def _temporary_trusted_external_root(root):
    """Expose a synthetic external package through sysconfig, never sys.path."""
    original_get_paths = prereg.sysconfig.get_paths

    def get_paths(*args, **kwargs):
        paths = original_get_paths(*args, **kwargs)
        paths["purelib"] = str(root)
        return paths

    prereg.sysconfig.get_paths = get_paths
    try:
        yield
    finally:
        prereg.sysconfig.get_paths = original_get_paths



def _bindings(tmp_path):
    input_file, result_file = tmp_path / "input.json", tmp_path / "result.json"
    input_file.write_text('{"input": 1}\n', encoding="utf-8")
    result_file.write_text('{"result": 1}\n', encoding="utf-8")
    ref = lambda file: {"path": file.name, "sha256": hashlib.sha256(file.read_bytes()).hexdigest()}
    return [ref(input_file)], [ref(result_file)], [{"name": "candidate-a", "buy_sha256": "b" * 64, "sell_sha256": "c" * 64}]

def _v2_chain(tmp_path):
    if shutil.which("git") is None:
        pytest.skip("git is required for authoritative v2 receipt fixtures")
    tmp_path.mkdir(parents=True, exist_ok=True)
    doc = tmp_path / "prereg.md"
    code = tmp_path / "measure.py"
    code.write_text("value = 1\n", encoding="utf-8")
    doc.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "prereg.md", "measure.py"], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "-c", "user.name=tester", "-c", "user.email=t@example.com",
         "commit", "-q", "-m", "fixture"],
        check=True,
    )
    prereg.finalize_prereg(
        doc,
        repo_root=tmp_path,
        code_files=(code,),
        manifest_path=_canonical_seal_path(tmp_path, doc),
        sealed_at="2026-07-14T00:00:00+00:00",
    )
    receipt = measure_gate.issue_gate_receipt_v2(
        tmp_path,
        _canonical_seal_path(tmp_path, doc),
        issued_at="2026-07-14T00:01:00+00:00",
        nonce="unit-run",
    )
    receipt_path = tmp_path / "receipts" / f"{receipt['receipt_id']}.json"
    measure_gate.claim_gate_receipt_v2(
        receipt_path,
        repo_root=tmp_path,
        consumer="unit-batch",
        consumed_at="2026-07-14T00:02:00+00:00",
    )
    usage_path = tmp_path / "claims" / f"{receipt['receipt_id']}.json"
    return receipt_path, usage_path, *_bindings(tmp_path)
def _append_v2_worker(queue, kwargs):
    try:
        ledger.append_trial_v2(**kwargs)
    except ledger.LedgerSchemaError as exc:
        queue.put(("rejected", str(exc)))
    else:
        queue.put(("appended", ""))




class TestLedgerV2:
    def test_append_v2_valid_identity_and_mixed_reading(self, tmp_path):
        receipt_path, usage_path, input_artifacts, result_artifacts, candidate_set = _v2_chain(tmp_path)
        path = tmp_path / "ledger.jsonl"
        ledger._append_record(path, VALID_ROW)
        record = ledger.append_trial_v2(
            path=path,
            repo_root=tmp_path,
            gate_receipt_path=receipt_path,
            gate_usage_path=usage_path,
            input_artifacts=input_artifacts,
            result_artifacts=result_artifacts,
            candidate_set=candidate_set,
            **_row(ts="2026-07-14T00:03:00+00:00"),
        )
        assert list(record) == list(ledger.V2_REQUIRED_KEYS)
        assert record["evidence_id"] == evidence.sha256_canonical(record["evidence"])
        assert [row.get("schema_version", 1) for row in ledger.read_all(path)] == [1, 2]
    def test_append_v2_replay_is_rejected_without_a_second_row(self, tmp_path):
        receipt_path, usage_path, inputs, results, candidates = _v2_chain(tmp_path)
        kwargs = {
            "repo_root": tmp_path, "gate_receipt_path": receipt_path, "gate_usage_path": usage_path,
            "input_artifacts": inputs, "result_artifacts": results, "candidate_set": candidates,
            "path": tmp_path / "ledger.jsonl", **_row(),
        }
        ledger.append_trial_v2(**kwargs)
        with pytest.raises(ledger.LedgerSchemaError, match="gate receipt claim"):
            ledger.append_trial_v2(**kwargs)
        assert len(ledger.read_all(tmp_path / "ledger.jsonl")) == 1

    def test_append_v2_concurrent_claim_attempts_create_one_row(self, tmp_path):
        receipt_path, usage_path, inputs, results, candidates = _v2_chain(tmp_path)
        kwargs = {
            "repo_root": tmp_path, "gate_receipt_path": receipt_path, "gate_usage_path": usage_path,
            "input_artifacts": inputs, "result_artifacts": results, "candidate_set": candidates,
            "path": tmp_path / "ledger.jsonl", **_row(),
        }
        context = multiprocessing.get_context("spawn")
        queue = context.Queue()
        processes = [context.Process(target=_append_v2_worker, args=(queue, kwargs)) for _ in range(2)]
        for process in processes:
            process.start()
        outcomes = [queue.get(timeout=30)[0] for _ in processes]
        for process in processes:
            process.join(timeout=30)
            assert process.exitcode == 0
        assert sorted(outcomes) == ["appended", "rejected"]
        assert len(ledger.read_all(tmp_path / "ledger.jsonl")) == 1

    def test_append_v2_rejects_noncontract_ledger_path(self, tmp_path):
        receipt_path, usage_path, inputs, results, candidates = _v2_chain(tmp_path)
        with pytest.raises(ledger.LedgerSchemaError, match="sealed contract ledger_path"):
            ledger.append_trial_v2(
                repo_root=tmp_path, gate_receipt_path=receipt_path, gate_usage_path=usage_path,
                input_artifacts=inputs, result_artifacts=results, candidate_set=candidates,
                path=tmp_path / "side-ledger.jsonl", **_row(),
            )

    def test_append_v2_rejects_backdated_ledger_timestamp(self, tmp_path):
        receipt_path, usage_path, inputs, results, candidates = _v2_chain(tmp_path)
        with pytest.raises(ledger.LedgerSchemaError, match="ledger.ts must not precede consumed_at"):
            ledger.append_trial_v2(
                repo_root=tmp_path, gate_receipt_path=receipt_path, gate_usage_path=usage_path,
                input_artifacts=inputs, result_artifacts=results, candidate_set=candidates,
                path=tmp_path / "ledger.jsonl", **_row(ts="2026-07-14T00:01:30+00:00"))

    def test_append_v2_rejects_relocated_evidence_files(self, tmp_path):
        receipt_path, usage_path, inputs, results, candidates = _v2_chain(tmp_path)
        relocated = tmp_path / "receipt-copy.json"
        relocated.write_bytes(receipt_path.read_bytes())
        with pytest.raises(ledger.LedgerSchemaError, match="canonical receipt path"):
            ledger.append_trial_v2(
                repo_root=tmp_path, gate_receipt_path=relocated, gate_usage_path=usage_path,
                input_artifacts=inputs, result_artifacts=results, candidate_set=candidates,
                path=tmp_path / "ledger.jsonl", **_row())


    def test_append_v2_rejects_usage_mismatch_and_changed_code(self, tmp_path):
        receipt_path, usage_path, input_artifacts, result_artifacts, candidate_set = _v2_chain(tmp_path)
        usage = json.loads(usage_path.read_text(encoding="utf-8"))
        usage["receipt_id"] = "b" * 64
        usage_path.write_text(json.dumps(usage), encoding="utf-8")
        with pytest.raises(ledger.LedgerSchemaError):
            ledger.append_trial_v2(
                repo_root=tmp_path,
                gate_receipt_path=receipt_path,
                gate_usage_path=usage_path,
                input_artifacts=input_artifacts,
                result_artifacts=result_artifacts,
                candidate_set=candidate_set,
                path=tmp_path / "ledger.jsonl",
                **_row(),
            )
        receipt_path, usage_path, input_artifacts, result_artifacts, candidate_set = _v2_chain(tmp_path / "second")
        (tmp_path / "second" / "measure.py").write_text("value = 2\n", encoding="utf-8")
        with pytest.raises(ledger.LedgerSchemaError):
            ledger.append_trial_v2(
                repo_root=tmp_path / "second",
                gate_receipt_path=receipt_path,
                gate_usage_path=usage_path,
                path=tmp_path / "second" / "ledger.jsonl",
                input_artifacts=input_artifacts,
                result_artifacts=result_artifacts,
                candidate_set=candidate_set,
                **_row(),
            )

    def test_append_v2_rejects_artifact_tamper_and_candidate_mismatch(self, tmp_path):
        receipt_path, usage_path, inputs, results, candidates = _v2_chain(tmp_path)
        (tmp_path / "input.json").write_text('{"input": 2}\n', encoding="utf-8")
        with pytest.raises(ledger.LedgerSchemaError):
            ledger.append_trial_v2(repo_root=tmp_path, gate_receipt_path=receipt_path, gate_usage_path=usage_path, input_artifacts=inputs, result_artifacts=results, candidate_set=candidates, path=tmp_path / "ledger.jsonl", **_row())
        inputs, results, candidates = _bindings(tmp_path)
        with pytest.raises(ledger.LedgerSchemaError):
            ledger.append_trial_v2(repo_root=tmp_path, gate_receipt_path=receipt_path, gate_usage_path=usage_path, input_artifacts=inputs, result_artifacts=results, candidate_set=list(reversed(candidates)) + [{"name": "candidate-a", "buy_sha256": "d" * 64, "sell_sha256": "e" * 64}], path=tmp_path / "ledger.jsonl", **_row())

    def test_append_v2_allows_empty_candidates_only_for_negative_kill(self, tmp_path):
        receipt_path, usage_path, inputs, results, _ = _v2_chain(tmp_path)
        with pytest.raises(ledger.LedgerSchemaError):
            ledger.append_trial_v2(repo_root=tmp_path, gate_receipt_path=receipt_path, gate_usage_path=usage_path, input_artifacts=inputs, result_artifacts=results, candidate_set=[], path=tmp_path / "ledger.jsonl", **_row())
        record = ledger.append_trial_v2(repo_root=tmp_path, gate_receipt_path=receipt_path, gate_usage_path=usage_path, input_artifacts=inputs, result_artifacts=results, candidate_set=[], negative_or_kill=True, path=tmp_path / "ledger.jsonl", **_row())
        assert record["evidence"]["candidate_set_sha256"] == evidence.sha256_canonical([])
    def test_candidate_identity_requires_exact_buy_sell_hashes_and_name(self, tmp_path):
        receipt_path, usage_path, inputs, results, candidates = _v2_chain(tmp_path)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        usage = json.loads(usage_path.read_text(encoding="utf-8"))
        evidence_id, identity = evidence.build_evidence_identity(
            receipt, usage, input_artifacts=inputs, result_artifacts=results,
            candidate_set=candidates, negative_or_kill=False, repo_root=tmp_path,
        )
        assert identity["candidate_set"] == candidates
        renamed = [{**candidates[0], "name": "candidate-b"}]
        changed_buy = [{**candidates[0], "buy_sha256": "d" * 64}]
        renamed_id, _ = evidence.build_evidence_identity(
            receipt, usage, input_artifacts=inputs, result_artifacts=results,
            candidate_set=renamed, negative_or_kill=False, repo_root=tmp_path,
        )
        changed_buy_id, _ = evidence.build_evidence_identity(
            receipt, usage, input_artifacts=inputs, result_artifacts=results,
            candidate_set=changed_buy, negative_or_kill=False, repo_root=tmp_path,
        )
        assert evidence_id not in {renamed_id, changed_buy_id}
        with pytest.raises(evidence.EvidenceSchemaError):
            evidence.validate_measurement_bindings(
                input_artifacts=inputs, result_artifacts=results,
                candidate_set=[{"name": "candidate-a", "sha256": "c" * 64}],
                negative_or_kill=False, repo_root=tmp_path,
            )
    def test_promotion_manifest_issuer_is_exclusive_and_canonical(self, tmp_path):
        receipt_path, usage_path, inputs, results, candidates = _v2_chain(tmp_path)
        ledger_path = tmp_path / "ledger.jsonl"
        record = ledger.append_trial_v2(
            repo_root=tmp_path, gate_receipt_path=receipt_path, gate_usage_path=usage_path,
            input_artifacts=inputs, result_artifacts=results, candidate_set=candidates,
            path=ledger_path, **_row(),
        )
        with pytest.raises(evidence.EvidenceSchemaError, match="promotions_dir"):
            evidence.issue_promotion_manifest_v2(
                tmp_path, gate_receipt_path=receipt_path, gate_claim_path=usage_path,
                ledger_path=ledger_path, evidence_id=record["evidence_id"],
                created_at="2026-07-14T00:04:00+00:00", output_dir=tmp_path / "caller-output",
            )
        with pytest.raises(evidence.EvidenceSchemaError, match="PRE.created_at must not precede ledger.ts"):
            evidence.issue_promotion_manifest_v2(
                tmp_path, gate_receipt_path=receipt_path, gate_claim_path=usage_path,
                ledger_path=ledger_path, evidence_id=record["evidence_id"],
                created_at="2026-07-14T00:02:30+00:00", output_dir=tmp_path / "promotions",
            )
        manifest = evidence.issue_promotion_manifest_v2(
            tmp_path, gate_receipt_path=receipt_path, gate_claim_path=usage_path,
            ledger_path=ledger_path, evidence_id=record["evidence_id"],
            created_at="2026-07-14T00:04:00+00:00", output_dir=tmp_path / "promotions",
        )
        manifest_path = tmp_path / "promotions" / f"{record['evidence_id']}.pre.json"
        assert evidence.verify_promotion_manifest_v2(manifest_path, repo_root=tmp_path)[0] == manifest
        assert set(manifest["ledger"]) == {
            "path", "row_ordinal", "record_sha256", "evidence_id",
        }
        ledger._append_record(ledger_path, VALID_ROW)
        assert evidence.verify_promotion_manifest_v2(manifest_path, repo_root=tmp_path)[0] == manifest
        rows = ledger_path.read_text(encoding="utf-8").splitlines()
        ledger_path.write_text("\n".join(reversed(rows)) + "\n", encoding="utf-8")
        with pytest.raises(evidence.EvidenceSchemaError, match="committed ledger row"):
            evidence.verify_promotion_manifest_v2(manifest_path, repo_root=tmp_path)
        ledger_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        tampered = json.loads(rows[0])
        tampered["result"] = "tampered"
        ledger_path.write_text(json.dumps(tampered, ensure_ascii=False) + "\n" + rows[1] + "\n", encoding="utf-8")
        with pytest.raises(evidence.EvidenceSchemaError):
            evidence.verify_promotion_manifest_v2(manifest_path, repo_root=tmp_path)
        ledger_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        copied = tmp_path / "copied.json"
        copied.write_bytes(manifest_path.read_bytes())
        with pytest.raises(evidence.EvidenceSchemaError, match="path is not canonical"):
            evidence.verify_promotion_manifest_v2(copied, repo_root=tmp_path)
        with pytest.raises(evidence.EvidenceSchemaError, match="ledger_path"):
            evidence.issue_promotion_manifest_v2(
                tmp_path, gate_receipt_path=receipt_path, gate_claim_path=usage_path,
                ledger_path=tmp_path / "alternate.jsonl", evidence_id=record["evidence_id"],
                created_at="2026-07-14T00:04:00+00:00", output_dir=tmp_path / "promotions",
            )
        with pytest.raises(FileExistsError):
            evidence.issue_promotion_manifest_v2(
                tmp_path, gate_receipt_path=receipt_path, gate_claim_path=usage_path,
                ledger_path=ledger_path, evidence_id=record["evidence_id"],
                created_at="2026-07-14T00:04:00+00:00", output_dir=tmp_path / "promotions",
            )
        ledger._append_record(ledger_path, record)
        with pytest.raises(evidence.EvidenceSchemaError, match="exactly one v2 row"):
            evidence.issue_promotion_manifest_v2(
                tmp_path, gate_receipt_path=receipt_path, gate_claim_path=usage_path,
                ledger_path=ledger_path, evidence_id=record["evidence_id"],
                created_at="2026-07-14T00:04:00+00:00", output_dir=tmp_path / "promotions",
            )


class TestStrictV1Reads:
    @pytest.mark.parametrize("bad", [
        {**VALID_ROW, "extra": "no"},
        _row(target=1),
        _row(ts="not-a-timestamp"),
        _row(trial_type="d(disallowed)"),
    ])
    def test_malformed_v1_rows_fail_closed(self, tmp_path, bad):
        path = tmp_path / "ledger.jsonl"
        path.write_text(json.dumps(bad, ensure_ascii=False) + "\n", encoding="utf-8")
        with pytest.raises(ledger.LedgerSchemaError):
            ledger.read_all(path)

    def test_valid_historical_v1_roundtrip(self, tmp_path):
        path = tmp_path / "ledger.jsonl"
        raw = json.dumps(VALID_ROW, ensure_ascii=False)
        path.write_text(raw + "\n", encoding="utf-8")
        assert ledger._serialize(ledger.read_all(path)[0]) == raw
    def test_malformed_v2_read_fails_closed_with_line_number(self, tmp_path):
        path = tmp_path / "ledger.jsonl"
        broken = {
            **VALID_ROW,
            "schema_version": 2,
            "evidence_id": "a" * 64,
            "evidence": {},
        }
        path.write_text(json.dumps(broken, ensure_ascii=False) + "\n", encoding="utf-8")
        with pytest.raises(ledger.LedgerSchemaError) as excinfo:
            ledger.read_all(path)
        assert "1행" in str(excinfo.value)


class TestReadAggregate:
    def test_read_all_missing_file_empty(self, tmp_path):
        assert ledger.read_all(tmp_path / "none.jsonl") == []

    def test_read_all_malformed_line_fail_closed(self, tmp_path):
        path = tmp_path / "l.jsonl"
        path.write_text('{"ts": "x"\n', encoding="utf-8")
        with pytest.raises(ledger.LedgerSchemaError) as excinfo:
            ledger.read_all(path)
        assert "1행" in str(excinfo.value)

    def test_read_all_missing_key_fail_closed(self, tmp_path):
        path = tmp_path / "l.jsonl"
        path.write_text('{"ts": "2026-07-12T00:00:00"}\n', encoding="utf-8")
        with pytest.raises(ledger.LedgerSchemaError) as excinfo:
            ledger.read_all(path)
        assert "필수 키 누락" in str(excinfo.value)

    def test_aggregate_counts_and_sqrt(self, tmp_path):
        path = tmp_path / "l.jsonl"
        ledger._append_record(path, _row(series="D1"))
        ledger._append_record(path, _row(series="D1", trial_type="a(엔진 확인)"))
        ledger._append_record(path, _row(series="S-트랙"))
        agg = ledger.aggregate(path)
        assert agg["total"] == 3
        assert agg["by_series"]["D1"]["n"] == 2
        assert agg["by_series"]["S-트랙"]["n"] == 1
        assert agg["by_trial_type"] == {"a": 1, "b": 2}
        assert agg["sqrt_2_ln_total"] == pytest.approx(1.4823, abs=1e-3)
        assert agg["by_series"]["S-트랙"]["sqrt_2_ln_n"] == 0.0

    def test_sqrt_2_ln_edges(self):
        assert ledger.sqrt_2_ln(0) == 0.0
        assert ledger.sqrt_2_ln(1) == 0.0
        assert ledger.sqrt_2_ln(53) == pytest.approx(2.8180, abs=1e-3)


@pytest.mark.skipif(not REAL_LEDGER.exists(), reason="실물 원장 부재 환경")
class TestRealLedgerRoundTrip:
    def test_all_existing_rows_roundtrip_byte_identical(self):
        """기존 전체 행 파싱 왕복(필수) — 단일 기입 경로의 스키마 호환 증명."""
        raw_lines = [
            line
            for line in REAL_LEDGER.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        entries = ledger.read_all(REAL_LEDGER)
        assert len(entries) == len(raw_lines)
        assert len(entries) >= 53  # 2026-07-12 시점 실측 하한(append-only)
        for raw, entry in zip(raw_lines, entries):
            assert ledger._serialize(entry) == raw

    def test_real_aggregate_series_present(self):
        agg = ledger.aggregate(REAL_LEDGER)
        assert agg["total"] >= 53
        assert "D1" in agg["by_series"]
        assert agg["window_unparsed"] == 0


# ---------------------------------------------------------------------------
# prereg — 스켈레톤 생성기
# ---------------------------------------------------------------------------


class TestPrereg:
    REQUIRED_HEADINGS = (
        "## 0. 결론 먼저",
        "## 2. 가설",
        "## 3. 모집단·대상 봉인",
        "## 5. 표본·라벨 — 표본 하한",
        "## 7. 판정 기준",
        "## 10. Kill 기준",
        "## 11. 엔진 예산 · n_trials",
        "## 13. 미결 결정",
    )

    def test_skeleton_contains_required_sections(self):
        text = prereg.build_skeleton(title="테스트 검정", series_kind="신규 스냅샷 가설")
        for heading in self.REQUIRED_HEADINGS:
            assert heading in text
        assert "BH-FDR" in text and "부트스트랩" in text  # 보정 명시
        assert "+0.10%p" in text  # 효과크기 하한 기본값
        assert "0회" in text  # 엔진 예산 기본값
        assert "1,100+" in text  # 구 프로그램 누계 병기 규약

    def test_skeleton_quotes_window_ledger(self):
        text = prereg.build_skeleton(title="테스트 검정", series_kind="신규 스냅샷 가설")
        assert windows.LEDGER_DOC_PATH in text
        assert "선택·튜닝 금지" in text

    def test_known_window_skeleton_rejected(self):
        with pytest.raises(windows.WindowViolation):
            prereg.build_skeleton(
                title="위반 시도",
                series_kind="신규 가설",
                window_start="2025-01-01",
                window_end="2025-12-31",
            )

    def test_conditional_2024_requires_flag(self):
        with pytest.raises(windows.WindowViolation):
            prereg.build_skeleton(
                title="조건부 시도",
                series_kind="신규 가설",
                window_start="2024-01-01",
                window_end="2024-06-30",
            )
        text = prereg.build_skeleton(
            title="조건부 시도",
            series_kind="신규 가설",
            window_start="2024-01-01",
            window_end="2024-06-30",
            conditional_2024=True,
        )
        assert "CONDITIONAL_2024" in text

    def test_write_skeleton_refuses_overwrite(self, tmp_path):
        target = tmp_path / "prereg.md"
        prereg.write_skeleton(target, title="테스트", series_kind="신규 가설")
        with pytest.raises(FileExistsError):
            prereg.write_skeleton(target, title="테스트", series_kind="신규 가설")
    def test_finalize_prereg_uses_only_canonical_seal_path_and_binds_authority(self, tmp_path):
        code = tmp_path / "measure.py"
        code.write_text("VALUE = 1\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")
        canonical = _canonical_seal_path(tmp_path, document)
        with pytest.raises(evidence.EvidenceSchemaError, match="canonical contract seal path"):
            prereg.finalize_prereg(
                document, repo_root=tmp_path, code_files=(code,),
                manifest_path=tmp_path / "arbitrary.seal.json", sealed_at="2026-07-14T00:00:00+00:00",
            )
        seal = prereg.finalize_prereg(
            document, repo_root=tmp_path, code_files=(code,),
            manifest_path=canonical, sealed_at="2026-07-14T00:00:00+00:00",
        )
        assert canonical.is_file()
        assert seal["ledger_path"] == "ledger.jsonl"
        assert seal["authority_paths"]["promotions_dir"] == "promotions"
        tampered = {**seal, "authority_paths": {**seal["authority_paths"], "seal_dir": "other-seals"}}
        with pytest.raises(evidence.EvidenceSchemaError, match="authority_paths"):
            evidence.validate_prereg_seal(tampered, repo_root=tmp_path)

    def test_finalize_prereg_rejects_parent_swap_before_write(self, tmp_path, monkeypatch):
        code = tmp_path / "measure.py"
        code.write_text("VALUE = 1\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")
        canonical = _canonical_seal_path(tmp_path, document)
        events = []

        class SwappedGuard:
            def hold_path(self, path):
                events.append(("hold", Path(path)))
            def validate_file(self, path):
                events.append(("validate", Path(path)))
                raise evidence.EvidenceSchemaError("authority parent identity changed")

        @contextlib.contextmanager
        def swapped_guard(*args, **kwargs):
            yield SwappedGuard()

        monkeypatch.setattr(prereg, "authority_mutation_guard", swapped_guard)
        with pytest.raises(evidence.EvidenceSchemaError, match="identity changed"):
            prereg.finalize_prereg(
                document, repo_root=tmp_path, code_files=(code,),
                manifest_path=canonical, sealed_at="2026-07-14T00:00:00+00:00",
            )
        assert events and not canonical.exists()
    def test_hold_path_establishes_missing_parent_and_rejects_substitution(self, tmp_path, monkeypatch):
        target_db = tmp_path / "measure.py"
        target_db.write_text("VALUE = 1\n", encoding="utf-8")
        authority = {
            "seal_dir": "promotion_journal/nested",
            "promotions_dir": "promotions",
            "catalog_dir": "catalog",
            "target_db": "measure.py",
            "journal_dir": "journal",
            "backup_dir": "backups",
        }
        target = tmp_path / "promotion_journal" / "nested" / "seal.json"

        with prereg.authority_mutation_guard(tmp_path, authority, fields=("seal_dir",)) as guard:
            guard.hold_path(target)
            assert target.parent.is_dir()
            if os.name == "nt":
                assert guard._windows_handles
            else:
                assert guard._path_key(target.parent) in guard._target_dir_fds
            assert not target.exists()

        (tmp_path / "promotion_journal" / "nested").rmdir()
        (tmp_path / "promotion_journal").rmdir()
        replacement = tmp_path / "replacement"
        replacement.mkdir()
        original_mkdir = os.mkdir
        substituted = False

        def substitute_component(path, *args, **kwargs):
            nonlocal substituted
            result = original_mkdir(path, *args, **kwargs)
            if not substituted and Path(path).name == "promotion_journal":
                candidate = tmp_path / "promotion_journal"
                candidate.rmdir()
                try:
                    candidate.symlink_to(replacement, target_is_directory=True)
                except OSError:
                    pytest.skip("symlink/junction creation is unavailable")
                substituted = True
            return result

        monkeypatch.setattr(prereg.os, "mkdir", substitute_component)
        with pytest.raises(evidence.EvidenceSchemaError, match="non-symlink|reparse|securely hold"):
            with prereg.authority_mutation_guard(tmp_path, authority, fields=("seal_dir",)) as guard:
                guard.hold_path(target)
        assert substituted
    @pytest.mark.parametrize(("source", "dynamic_python"), [
        ("import package.plugin\n", ()),
        ("__import__('package.plugin')\n", ("package/plugin.py",)),
        (
            "import importlib\nimportlib.import_module('package.plugin')\n",
            ("package/plugin.py",),
        ),
    ])
    def test_finalize_prereg_rejects_redirected_package_path_before_import(
        self, tmp_path, source, dynamic_python,
    ):
        package = tmp_path / "package"
        package.mkdir()
        measure, initializer, plugin = (
            tmp_path / "measure.py",
            package / "__init__.py",
            package / "plugin.py",
        )
        measure.write_text(source, encoding="utf-8")
        initializer.write_text("__path__ = ['redirected']\n", encoding="utf-8")
        plugin.write_text("VALUE = 1\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(
            _sealed_contract(roots=("measure.py",), dynamic_python=dynamic_python),
            encoding="utf-8",
        )

        with pytest.raises(
            evidence.EvidenceSchemaError,
            match="import-resolution/runtime identity global binding",
        ):
            prereg.finalize_prereg(
                document,
                repo_root=tmp_path,
                code_files=(measure, initializer, plugin),
                manifest_path=_canonical_seal_path(tmp_path, document),
                sealed_at="2026-07-14T00:00:00+00:00",
            )

    @pytest.mark.parametrize("initializer_source", [
        "(__path__,) = (['redirected'],)\n",
        "__path__ += ['redirected']\n",
        "del __path__\n",
        "for __path__ in (['redirected'],):\n    pass\n",
        "[None for __path__ in (['redirected'],)]\n",
        "(__path__ := ['redirected'])\n",
        "match ['redirected']:\n    case __path__:\n        pass\n",
        "from sys import path as __path__\n",
    ])
    def test_finalize_prereg_rejects_alternate_package_path_bindings(
        self, tmp_path, initializer_source,
    ):
        package = tmp_path / "package"
        package.mkdir()
        measure, initializer, plugin = (
            tmp_path / "measure.py",
            package / "__init__.py",
            package / "plugin.py",
        )
        measure.write_text("import package.plugin\n", encoding="utf-8")
        initializer.write_text(initializer_source, encoding="utf-8")
        plugin.write_text("VALUE = 1\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")

        with pytest.raises(
            evidence.EvidenceSchemaError,
            match="identity global binding|sealed mutation",
        ):
            prereg.finalize_prereg(
                document,
                repo_root=tmp_path,
                code_files=(measure, initializer, plugin),
                manifest_path=_canonical_seal_path(tmp_path, document),
                sealed_at="2026-07-14T00:00:00+00:00",
            )

    def test_finalize_prereg_allows_package_identity_global_reads(self, tmp_path):
        package = tmp_path / "package"
        package.mkdir()
        measure, initializer, plugin = (
            tmp_path / "measure.py",
            package / "__init__.py",
            package / "plugin.py",
        )
        measure.write_text("import package.plugin\n", encoding="utf-8")
        initializer.write_text("observed_path = __path__\n", encoding="utf-8")
        plugin.write_text("VALUE = 1\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")

        seal = prereg.finalize_prereg(
            document,
            repo_root=tmp_path,
            code_files=(measure, initializer, plugin),
            manifest_path=_canonical_seal_path(tmp_path, document),
            sealed_at="2026-07-14T00:00:00+00:00",
        )

        assert "package/__init__.py" in [item["path"] for item in seal["code_manifest"]]
    @pytest.mark.parametrize("source", [
        "import runpy\nrunpy.run_path('plugin.py')\n",
        "from builtins import exec as execute\nexecute('x = 1')\n",
        "loaders = {'run': __import__}\nloaders['run']('plugin')\n",
        "eval(compile(open('plugin.py').read(), 'plugin.py', 'exec'))\n",
        "from functools import partial\nimport importlib\nload = partial(importlib.import_module, 'plugin')\nload()\n",
        "import importlib\nload = importlib.import_module\nload('plugin')\n",
        "import importlib\nloaders = (importlib.import_module,)\nloaders[0]('plugin')\n",
        "def wrapper(loader):\n    loader('plugin')\nwrapper(__import__)\n",
        "import importlib\nfor loader in (importlib,):\n    loader.import_module('plugin')\n",
        "import importlib\n[loader.import_module('plugin') for loader in (importlib,)]\n",
        "import importlib\nlist(map(lambda module: module.import_module(\"local_plugin\"), [importlib]))\n",
        "import importlib\nimportlib.import_module('builtins').eval('1 + 1')\n",
        "import builtins\nimport importlib\nlist(map(builtins.getattr(importlib, 'import_module'), ['local_plugin']))\n",
        "type(object).__getattribute__(object, '__class__')\n",
        "import pickle\npickle.loads(b'payload')\n",
        "import importlib\ndef run():\n    for loader in (importlib,):\n        loader.import_module('plugin')\nrun()\n",
        "import importlib\nclass Executed:\n    for loader in (importlib,):\n        loader.import_module('plugin')\n",
        "import importlib\ndef outer():\n    class Holder:\n        pass\n    holder = Holder()\n    holder.importlib.import_module('plugin')\nouter()\n",
        "import importlib\n[loader.import_module('plugin') for (loader,) in ((importlib,),)]\n",
        "import pydoc\nlist(map(pydoc.importfile, ['plugin.py']))\n",
        "import pydoc\nlist(filter(pydoc.importfile, ['plugin.py']))\n",
        "import pydoc\nsorted(['plugin.py'], key=pydoc.importfile)\n",
        "import pydoc\nmin(['plugin.py'], key=pydoc.importfile)\n",
        "import pydoc\nmax(['plugin.py'], key=pydoc.importfile)\n",
        "import pydoc\niter(pydoc.importfile, None)\n",
        "import runpy\nimport sys\nsys.modules[__name__].run_path = runpy.run_path\nrun_path('plugin.py')\n",
    ])
    def test_finalize_prereg_rejects_indirect_or_unprovable_execution(self, tmp_path, source):
        measure, plugin = tmp_path / "measure.py", tmp_path / "plugin.py"
        measure.write_text(source, encoding="utf-8")
        plugin.write_text("VALUE = 1\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")
        with pytest.raises(evidence.EvidenceSchemaError):
            prereg.finalize_prereg(
                document, repo_root=tmp_path, code_files=(measure, plugin),
                manifest_path=_canonical_seal_path(tmp_path, document),
                sealed_at="2026-07-14T00:00:00+00:00",
            )

    def test_finalize_prereg_rejects_decorated_callback_carrier_through_map(self, tmp_path):
        measure = tmp_path / "measure.py"
        measure.write_text(
            "import pydoc\n"
            "def replace(function):\n    return pydoc.importfile\n"
            "@replace\n"
            "def carrier(path):\n    return path\n"
            "list(map(carrier, ['plugin.py']))\n",
            encoding="utf-8",
        )
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")

        with pytest.raises(evidence.EvidenceSchemaError, match="unproven callback"):
            prereg.finalize_prereg(
                document,
                repo_root=tmp_path,
                code_files=(measure,),
                manifest_path=_canonical_seal_path(tmp_path, document),
                sealed_at="2026-07-14T00:00:00+00:00",
            )
    @pytest.mark.parametrize("source", [
        "import pydoc\nstr = pydoc.importfile\nlist(map(str, ['plugin.py']))\n",
        "import pydoc\nint = pydoc.importfile\nlist(map(int, ['plugin.py']))\n",
        "from pydoc import importfile as str\nlist(map(str, ['plugin.py']))\n",
        "import pydoc\ndef run(str):\n    list(map(str, ['plugin.py']))\nrun(pydoc.importfile)\n",
        "import pydoc\ndef run(str=pydoc.importfile):\n    list(map(str, ['plugin.py']))\nrun()\n",
        "import pydoc\nlist(map(str, ['plugin.py']) for str in [pydoc.importfile])\n",
        "import pydoc\nmatch pydoc.importfile:\n    case str:\n        list(map(str, ['plugin.py']))\n",
        "def decorate(callback):\n    return callback\n@decorate\ndef str(path):\n    return path\nlist(map(str, ['plugin.py']))\n",
    ])
    def test_finalize_prereg_rejects_shadowed_safe_builtin_callback(self, tmp_path, source):
        measure = tmp_path / "measure.py"
        measure.write_text(source, encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")

        with pytest.raises(evidence.EvidenceSchemaError):
            prereg.finalize_prereg(
                document,
                repo_root=tmp_path,
                code_files=(measure,),
                manifest_path=_canonical_seal_path(tmp_path, document),
                sealed_at="2026-07-14T00:00:00+00:00",
            )


    @pytest.mark.parametrize("source", [
        "import runpy\nimport sys\nsys.modules[__name__].run_path = runpy.run_path\nrun_path('plugin.py')\n",
        "import runpy\nimport sys\nnamespace = sys.modules[__name__]\nnamespace.run_path = runpy.run_path\n",
        "import runpy\nimport sys\nnamespace = sys.modules[__name__].__dict__\nnamespace['run_path'] = runpy.run_path\n",
        "import runpy\nimport sys\ndef namespace():\n    return sys.modules[__name__]\nnamespace().run_path = runpy.run_path\n",
        "import runpy\nsys.__dict__['run_path'] = runpy.run_path\n",
        "import runpy\nglobals()['run_path'] = runpy.run_path\n",
        "import runpy\nlocals()['run_path'] = runpy.run_path\n",
        "import runpy\nvars()['run_path'] = runpy.run_path\n",
    ])
    def test_finalize_prereg_rejects_namespace_export_mutation(self, tmp_path, source):
        measure = tmp_path / "measure.py"
        measure.write_text(source, encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")

        with pytest.raises(
            evidence.EvidenceSchemaError,
            match="namespace export mutation|module-level object mutation|higher-order or unsafe executable callable",
        ):
            prereg.finalize_prereg(
                document,
                repo_root=tmp_path,
                code_files=(measure,),
                manifest_path=_canonical_seal_path(tmp_path, document),
                sealed_at="2026-07-14T00:00:00+00:00",
            )
    @pytest.mark.parametrize("source", [
        "import pydoc\ndef rebind():\n    global str\n    str = pydoc.importfile\nrebind()\nlist(map(str, ['plugin.py']))\n",
        "import builtins\nimport pydoc\nbuiltins.str = pydoc.importfile\nlist(map(str, ['plugin.py']))\n",
        "import pydoc\ndef namespace():\n    return globals()\nalias = namespace\nalias()['str'] = pydoc.importfile\nlist(map(str, ['plugin.py']))\n",
        "import pydoc\ndef namespace():\n    marker = None\n    return globals()\nnamespace()['str'] = pydoc.importfile\nlist(map(str, ['plugin.py']))\n",
        "import pydoc\nsetattr(globals(), 'str', pydoc.importfile)\n",
        "import pydoc\ndelattr(pydoc, 'render_doc')\n",
        "import builtins\nimport pydoc\ndef namespace():\n    marker = None\n    return builtins.__dict__\ndef mutate(callback):\n    callback().update({'str': pydoc.importfile})\nmutate(namespace)\nlist(map(str, ['plugin.py']))\n",
        "import runpy\nimport sys\ndef self_module():\n    marker = None\n    return sys.modules[__name__]\ndef mutate(callback):\n    callback().__dict__.__setitem__('run_path', runpy.run_path)\nmutate(self_module)\nrun_path('plugin.py')\n",
    ], ids=(
        "global_str_callback", "builtins_str", "alias_return_helper",
        "multi_statement_helper", "setattr", "delattr",
        "multi_statement_builtins_dict_helper_update_callback",
        "self_module_helper_setitem_mutator",
    ))
    @pytest.mark.parametrize("package", [False, True], ids=("module", "package_initializer"))
    def test_finalize_prereg_rejects_sealed_global_export_mutation(
        self, tmp_path, source, package
    ):
        carrier_dir = tmp_path / "carrier" if package else tmp_path
        carrier_dir.mkdir(exist_ok=True)
        carrier = carrier_dir / "__init__.py" if package else carrier_dir / "carrier.py"
        measure = tmp_path / "measure.py"
        measure.write_text("import carrier\n", encoding="utf-8")
        carrier.write_text(source, encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")

        with pytest.raises(evidence.EvidenceSchemaError, match=(
            "global or nonlocal|builtins namespace|module-level object|dynamic attribute"
            "|function-body object mutation|function-body mutating method"
        )):
            prereg.finalize_prereg(
                document,
                repo_root=tmp_path,
                code_files=(measure, carrier),
                manifest_path=_canonical_seal_path(tmp_path, document),
                sealed_at="2026-07-14T00:00:00+00:00",
            )

    @pytest.mark.parametrize("source", [
        "import builtins\nbuiltins.sealed_export, local = (1, 2)\n",
        "namespace = globals()\nnamespace |= {'sealed_export': 1}\n",
    ], ids=("builtins_tuple_destructuring", "namespace_name_ior"))
    def test_finalize_prereg_rejects_recursive_store_and_name_augassign(
        self, tmp_path, source
    ):
        measure = tmp_path / "measure.py"
        measure.write_text(source, encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")

        with pytest.raises(evidence.EvidenceSchemaError, match="sealed mutation"):
            prereg.finalize_prereg(
                document,
                repo_root=tmp_path,
                code_files=(measure,),
                manifest_path=_canonical_seal_path(tmp_path, document),
                sealed_at="2026-07-14T00:00:00+00:00",
            )

    @pytest.mark.parametrize("package", [False, True], ids=("module", "package_initializer"))
    @pytest.mark.parametrize("statement", [
        "for carrier.sealed_export in (1,):\n    pass\n",
        "import contextlib\nwith contextlib.nullcontext() as carrier.sealed_export:\n    pass\n",
    ], ids=("for_target", "with_target"))
    def test_finalize_prereg_rejects_carrier_store_targets_before_seal(
        self, tmp_path, package, statement
    ):
        carrier_dir = tmp_path / "carrier" if package else tmp_path
        carrier_dir.mkdir(exist_ok=True)
        carrier = carrier_dir / "__init__.py" if package else carrier_dir / "carrier.py"
        carrier.write_text("VALUE = 1\n", encoding="utf-8")
        measure = tmp_path / "measure.py"
        measure.write_text(f"import carrier\n{statement}", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")

        with pytest.raises(evidence.EvidenceSchemaError, match="sealed mutation"):
            prereg.finalize_prereg(
                document,
                repo_root=tmp_path,
                code_files=(measure, carrier),
                manifest_path=_canonical_seal_path(tmp_path, document),
                sealed_at="2026-07-14T00:00:00+00:00",
            )

    def test_finalize_prereg_allows_pure_name_assignment_and_arithmetic(self, tmp_path):
        measure = tmp_path / "measure.py"
        measure.write_text("value = 1\nresult = value + 2\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")

        seal = prereg.finalize_prereg(
            document,
            repo_root=tmp_path,
            code_files=(measure,),
            manifest_path=_canonical_seal_path(tmp_path, document),
            sealed_at="2026-07-14T00:00:00+00:00",
        )

        assert [item["path"] for item in seal["code_manifest"]] == ["measure.py"]
    def test_dynamic_dependency_rejects_comprehension_attribute_store(self, tmp_path):
        tree = ast.parse("result = [item for item in values]\n")
        tree.body[0].value.generators[0].target = ast.Attribute(
            value=ast.Name(id="carrier", ctx=ast.Load()),
            attr="sealed_export",
            ctx=ast.Store(),
        )

        with pytest.raises(evidence.EvidenceSchemaError, match="sealed mutation"):
            prereg._dynamic_local_dependencies(tree, tmp_path / "measure.py", tmp_path)
    @pytest.mark.parametrize("source", [
        "def update(state):\n    state.value = 1\n",
        "def update(state):\n    state['value'] = 2\n",
        "def update(state):\n    state.update({'value': 3})\n",
        "def update(state):\n    state.__setitem__('value', 4)\n",
    ], ids=("attribute_store", "subscript_store", "update", "setitem"))
    def test_dynamic_dependency_rejects_function_body_object_mutation(self, tmp_path, source):
        with pytest.raises(
            evidence.EvidenceSchemaError,
            match="function-body object mutation|function-body mutating method|unresolved executable receiver parameter",
        ):
            prereg._dynamic_local_dependencies(
                ast.parse(source), tmp_path / "measure.py", tmp_path
            )
    @pytest.mark.parametrize("source", [
        "import importlib\ndef carrier():\n    pass\ncarrier.loader = importlib\ncarrier.loader.import_module('plugin')\n",
        "import importlib\nclass Carrier:\n    pass\nCarrier.loader = importlib\nCarrier.loader.import_module('plugin')\n",
        "import importlib\ndef carrier():\n    pass\ncarrier.loader = {}\ncarrier.loader['module'] = importlib\ncarrier.loader['module'].import_module('plugin')\n",
        "import importlib\ndef carrier():\n    pass\ncarrier.holder = carrier\ncarrier.holder.loader = importlib\ncarrier.holder.loader.import_module('plugin')\n",
    ])
    def test_dynamic_dependency_rejects_attribute_capability_carriers(self, tmp_path, source):
        with pytest.raises(
            evidence.EvidenceSchemaError,
            match="module-level object mutation|unresolved executable receiver",
        ):
            prereg._dynamic_local_dependencies(ast.parse(source), tmp_path / "measure.py", tmp_path)
    @pytest.mark.parametrize(("carrier_source", "receiver"), [
        (
            "import importlib\ndef holder():\n    pass\nholder.loader = importlib\n",
            "carrier.holder.loader.import_module('plugin')",
        ),
        (
            "import importlib\nclass Holder:\n    pass\nHolder.loader = importlib\n",
            "carrier.Holder.loader.import_module('plugin')",
        ),
        (
            "import importlib\nclass Holder:\n    pass\nholder = Holder()\nholder.__dict__['loader'] = importlib\n",
            "carrier.holder.__dict__['loader'].import_module('plugin')",
        ),
        (
            "import importlib\ndef exported():\n    pass\nexported.import_module = importlib.import_module\n",
            "loader = carrier.exported\nloader.import_module('plugin')",
        ),
        (
            "import importlib\nclass Exported:\n    pass\nExported.import_module = importlib.import_module\n",
            "loader = carrier.Exported\nloader.import_module('plugin')",
        ),
        (
            "import importlib\nclass Exported:\n    pass\nexported = Exported()\nexported.__dict__['import_module'] = importlib.import_module\n",
            "loader = carrier.exported\nloader.import_module('plugin')",
        ),
    ])
    def test_finalize_prereg_rejects_cross_module_capability_carriers(
        self, tmp_path, carrier_source, receiver
    ):
        measure, carrier, plugin = (
            tmp_path / "measure.py",
            tmp_path / "carrier.py",
            tmp_path / "plugin.py",
        )
        measure.write_text(f"import carrier\n{receiver}\n", encoding="utf-8")
        carrier.write_text(carrier_source, encoding="utf-8")
        plugin.write_text("VALUE = 1\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")

        with pytest.raises(
            evidence.EvidenceSchemaError,
            match="module-level object mutation|unresolved executable receiver",
        ):
            prereg.finalize_prereg(
                document,
                repo_root=tmp_path,
                code_files=(measure, carrier, plugin),
                manifest_path=_canonical_seal_path(tmp_path, document),
                sealed_at="2026-07-14T00:00:00+00:00",
            )

    def test_finalize_prereg_rejects_local_module_reexported_run_path(self, tmp_path):
        measure, carrier, plugin = (
            tmp_path / "measure.py",
            tmp_path / "carrier.py",
            tmp_path / "plugin.py",
        )
        measure.write_text("import carrier\ncarrier.run_path('plugin.py')\n", encoding="utf-8")
        carrier.write_text(
            "def run_path(path):\n    return path\nfrom runpy import run_path\n",
            encoding="utf-8",
        )
        plugin.write_text("VALUE = 1\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")

        with pytest.raises(evidence.EvidenceSchemaError, match="unresolved executable receiver"):
            prereg.finalize_prereg(
                document,
                repo_root=tmp_path,
                code_files=(measure, carrier),
                manifest_path=_canonical_seal_path(tmp_path, document),
                sealed_at="2026-07-14T00:00:00+00:00",
            )

    def test_finalize_prereg_rejects_package_initializer_reexported_run_path(self, tmp_path):
        package = tmp_path / "carrier"
        package.mkdir()
        measure, initializer, plugin = (
            tmp_path / "measure.py",
            package / "__init__.py",
            tmp_path / "plugin.py",
        )
        measure.write_text("import carrier\ncarrier.run_path('plugin.py')\n", encoding="utf-8")
        initializer.write_text(
            "def run_path(path):\n    return path\nfrom runpy import run_path\n",
            encoding="utf-8",
        )
        plugin.write_text("VALUE = 1\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")

        with pytest.raises(evidence.EvidenceSchemaError, match="unresolved executable receiver"):
            prereg.finalize_prereg(
                document,
                repo_root=tmp_path,
                code_files=(measure, initializer),
                manifest_path=_canonical_seal_path(tmp_path, document),
                sealed_at="2026-07-14T00:00:00+00:00",
            )
    @pytest.mark.parametrize("package", [False, True], ids=("module", "package_initializer"))
    def test_finalize_prereg_rejects_decorator_replaced_local_run_path(self, tmp_path, package):
        package_dir = tmp_path / "carrier" if package else tmp_path
        package_dir.mkdir(exist_ok=True)
        measure = tmp_path / "measure.py"
        carrier = package_dir / "__init__.py" if package else package_dir / "carrier.py"
        measure.write_text("import carrier\ncarrier.run_path('plugin.py')\n", encoding="utf-8")
        carrier.write_text(
            "import pydoc\n"
            "def replace(function):\n    return pydoc.importfile\n"
            "@replace\n"
            "def run_path(path):\n    return path\n",
            encoding="utf-8",
        )
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")

        with pytest.raises(evidence.EvidenceSchemaError, match="unresolved executable receiver"):
            prereg.finalize_prereg(
                document,
                repo_root=tmp_path,
                code_files=(measure, carrier),
                manifest_path=_canonical_seal_path(tmp_path, document),
                sealed_at="2026-07-14T00:00:00+00:00",
            )


    @pytest.mark.parametrize("source", [
        (
            "class Loader:\n"
            "    def run_path(path):\n"
            "        return path\n"
            "Loader.run_path('plugin.py')\n"
        ),
        (
            "class Loader:\n"
            "    class Nested:\n"
            "        def run_path(path):\n"
            "            return path\n"
            "Loader.Nested.run_path('plugin.py')\n"
        ),
        (
            "import runpy\n"
            "class Loader:\n"
            "    for Loader in (runpy,):\n"
            "        Loader.run_path('plugin.py')\n"
        ),
        (
            "def outer():\n"
            "    class Loader:\n"
            "        def run_path(path):\n"
            "            return path\n"
            "    return Loader.run_path('plugin.py')\n"
            "outer()\n"
        ),
    ], ids=("class_method", "nested_class_method", "class_for_rebind", "nested_function_class"))
    def test_finalize_prereg_rejects_unproven_class_callable_api(self, tmp_path, source):
        measure = tmp_path / "measure.py"
        measure.write_text(source, encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")

        with pytest.raises(evidence.EvidenceSchemaError, match="unresolved executable receiver"):
            prereg.finalize_prereg(
                document,
                repo_root=tmp_path,
                code_files=(measure,),
                manifest_path=_canonical_seal_path(tmp_path, document),
                sealed_at="2026-07-15T00:00:00+00:00",
            )

    @pytest.mark.parametrize("source", [
        "import pydoc\nmodule_value: pydoc.importfile('plugin.py')\n",
        (
            "import pydoc\n"
            "class Holder:\n"
            "    class_value: pydoc.importfile('plugin.py')\n"
        ),
        (
            "import pydoc\n"
            "def outer():\n"
            "    def inner(value: pydoc.importfile('plugin.py')) -> int:\n"
            "        return 1\n"
            "    return inner('value')\n"
        ),
        "import pydoc\ndef annotated(value: pydoc.importfile('plugin.py'), /):\n    return value\n",
        "import pydoc\ndef annotated(*items: pydoc.importfile('plugin.py')):\n    return items\n",
        "import pydoc\ndef annotated(*, item: pydoc.importfile('plugin.py')):\n    return item\n",
        "import pydoc\ndef annotated(**items: pydoc.importfile('plugin.py')):\n    return items\n",
        "import pydoc\ndef annotated() -> pydoc.importfile('plugin.py'):\n    return None\n",
    ], ids=("module", "class", "nested_function", "posonly", "vararg", "kwonly", "kwarg", "return"))
    def test_finalize_prereg_rejects_executable_annotations(self, tmp_path, source):
        measure = tmp_path / "measure.py"
        measure.write_text(source, encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")

        with pytest.raises(evidence.EvidenceSchemaError, match="executable annotation"):
            prereg.finalize_prereg(
                document,
                repo_root=tmp_path,
                code_files=(measure,),
                manifest_path=_canonical_seal_path(tmp_path, document),
                sealed_at="2026-07-15T00:00:00+00:00",
            )
    @pytest.mark.parametrize("source", [
        "__import__('plugin', globals=None, locals=None)\n",
        "__import__('plugin', fromlist=('not_local',))\n",
        "__import__('plugin', level=0)\n",
        "from builtins import __import__ as load\nload('plugin', None, None)\n",
        "import importlib\nimportlib.import_module('.plugin')\n",
        "import importlib as loader\nloader.import_module('plugin', package='package')\n",
        "from importlib import import_module as load\nload('plugin', None)\n",
    ], ids=(
        "builtin_globals_locals", "builtin_fromlist", "builtin_level",
        "builtin_alias", "relative_target", "package_keyword", "import_module_alias",
    ))
    def test_finalize_prereg_rejects_non_exact_dynamic_module_imports(self, tmp_path, source):
        measure, plugin = tmp_path / "measure.py", tmp_path / "plugin.py"
        measure.write_text(source, encoding="utf-8")
        plugin.write_text("VALUE = 1\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")

        with pytest.raises(evidence.EvidenceSchemaError, match="dynamic module import"):
            prereg.finalize_prereg(
                document,
                repo_root=tmp_path,
                code_files=(measure, plugin),
                manifest_path=_canonical_seal_path(tmp_path, document),
                sealed_at="2026-07-15T00:00:00+00:00",
            )

    @pytest.mark.parametrize("source", [
        "value: Trigger['go']\n",
        "class Holder:\n    value: Trigger['go']\n",
        "def outer():\n    value: Trigger['go']\n",
    ], ids=("module", "class", "nested_function"))
    def test_finalize_prereg_rejects_implicit_protocol_annotations(self, tmp_path, source):
        measure = tmp_path / "measure.py"
        measure.write_text(source, encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")

        with pytest.raises(evidence.EvidenceSchemaError, match="executable annotation"):
            prereg.finalize_prereg(
                document,
                repo_root=tmp_path,
                code_files=(measure,),
                manifest_path=_canonical_seal_path(tmp_path, document),
                sealed_at="2026-07-15T00:00:00+00:00",
            )

    def test_dynamic_dependency_rejects_implicit_protocol_type_alias(self, tmp_path):
        tree = ast.parse("marker = None\n")
        type_alias = type("TypeAlias", (ast.AST,), {"_fields": ("value", "type_params")})()
        type_alias.value = ast.parse("Trigger['go']", mode="eval").body
        type_alias.type_params = []
        tree.body.append(type_alias)

        with pytest.raises(evidence.EvidenceSchemaError, match="executable annotation"):
            prereg._dynamic_local_dependencies(tree, tmp_path / "measure.py", tmp_path)

    def test_finalize_prereg_allows_simple_non_call_annotations(self, tmp_path):
        measure = tmp_path / "measure.py"
        measure.write_text(
            "module_value: (int, 'str')\n"
            "def pure(value: int, legacy: 'str', /, *items: str, named: float = 1.0, **extra: bool) -> 'int':\n"
            "    return value\n"
            "pure(1)\n",
            encoding="utf-8",
        )
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")

        manifest = prereg.finalize_prereg(
            document,
            repo_root=tmp_path,
            code_files=(measure,),
            manifest_path=_canonical_seal_path(tmp_path, document),
            sealed_at="2026-07-15T00:00:00+00:00",
        )

        assert [item["path"] for item in manifest["code_manifest"]] == ["measure.py"]

    def test_dynamic_dependency_rejects_executable_type_parameter_bound(self, tmp_path):
        tree = ast.parse("def generic():\n    pass\n")
        function = tree.body[0]
        function.type_params = [type(
            "TypeParameter",
            (),
            {"bound": ast.parse("pydoc.importfile('plugin.py')", mode="eval").body, "default_value": None},
        )()]

        with pytest.raises(evidence.EvidenceSchemaError, match="executable annotation"):
            prereg._dynamic_local_dependencies(tree, tmp_path / "measure.py", tmp_path)
    def test_finalize_prereg_rejects_unclassified_static_module_call(self, tmp_path):
        measure, plugin = tmp_path / "measure.py", tmp_path / "plugin.py"
        measure.write_text("import pydoc\npydoc.importfile('plugin.py')\n", encoding="utf-8")
        plugin.write_text("VALUE = 1\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")

        with pytest.raises(evidence.EvidenceSchemaError, match="unresolved executable receiver"):
            prereg.finalize_prereg(
                document,
                repo_root=tmp_path,
                code_files=(measure,),
                manifest_path=_canonical_seal_path(tmp_path, document),
                sealed_at="2026-07-14T00:00:00+00:00",
            )
    @pytest.mark.parametrize("source", [
        "from pydoc import importfile as print\nprint('plugin.py')\n",
        "import pydoc\ndef relay(print):\n    print('plugin.py')\nrelay(pydoc.importfile)\n",
        "import pydoc\n[print('plugin.py') for print in [pydoc.importfile]]\n",
        "import pydoc\nmatch pydoc.importfile:\n    case print:\n        print('plugin.py')\n",
    ])
    def test_finalize_prereg_rejects_shadowed_or_parameter_bare_callable(
        self, tmp_path, source
    ):
        measure = tmp_path / "measure.py"
        measure.write_text(source, encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")

        with pytest.raises(evidence.EvidenceSchemaError, match="unresolved callable alias"):
            prereg.finalize_prereg(
                document,
                repo_root=tmp_path,
                code_files=(measure,),
                manifest_path=_canonical_seal_path(tmp_path, document),
                sealed_at="2026-07-14T00:00:00+00:00",
            )
    def test_finalize_prereg_allows_unshadowed_builtin_in_comprehension(self, tmp_path):
        measure = tmp_path / "measure.py"
        measure.write_text(
            "values = [print(value) for value in ['ok']]\n",
            encoding="utf-8",
        )
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")

        manifest = prereg.finalize_prereg(
            document,
            repo_root=tmp_path,
            code_files=(measure,),
            manifest_path=_canonical_seal_path(tmp_path, document),
            sealed_at="2026-07-14T00:00:00+00:00",
        )

        assert [item["path"] for item in manifest["code_manifest"]] == ["measure.py"]
    def test_finalize_prereg_allows_unshadowed_safe_builtin_callback(self, tmp_path):
        measure = tmp_path / "measure.py"
        measure.write_text(
            "values = list(map(str, [1, 2]))\n",
            encoding="utf-8",
        )
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")

        manifest = prereg.finalize_prereg(
            document,
            repo_root=tmp_path,
            code_files=(measure,),
            manifest_path=_canonical_seal_path(tmp_path, document),
            sealed_at="2026-07-14T00:00:00+00:00",
        )

        assert [item["path"] for item in manifest["code_manifest"]] == ["measure.py"]
    @pytest.mark.parametrize(("carrier_source", "measure_source"), [
        (
            "def exported(name):\n    return name\n",
            "from carrier import exported\nexported('plugin')\n",
        ),
        (
            "class exported:\n    def __init__(self, name):\n        self.name = name\n",
            "from carrier import exported\nexported('plugin')\n",
        ),
        (
            "class Carrier:\n    pass\nexported = Carrier.__dict__\n",
            "from carrier import exported\nexported('plugin')\n",
        ),
    ])
    def test_finalize_prereg_rejects_direct_local_imported_callable_carriers(
        self, tmp_path, carrier_source, measure_source
    ):
        measure, carrier = tmp_path / "measure.py", tmp_path / "carrier.py"
        measure.write_text(measure_source, encoding="utf-8")
        carrier.write_text(carrier_source, encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")

        with pytest.raises(evidence.EvidenceSchemaError, match="unresolved callable alias"):
            prereg.finalize_prereg(
                document,
                repo_root=tmp_path,
                code_files=(measure, carrier),
                manifest_path=_canonical_seal_path(tmp_path, document),
                sealed_at="2026-07-14T00:00:00+00:00",
            )
    @pytest.mark.parametrize(("declaration", "relative"), [
        ("def exported(name):\n    return name\n", False),
        ("class exported:\n    def __init__(self, name):\n        self.name = name\n", False),
        ("def exported(name):\n    return name\n", True),
        ("class exported:\n    def __init__(self, name):\n        self.name = name\n", True),
    ])
    def test_finalize_prereg_rejects_importfrom_shadowing_local_callable(
        self, tmp_path, declaration, relative
    ):
        package = tmp_path / "package" if relative else tmp_path
        package.mkdir(exist_ok=True)
        initializer = package / "__init__.py"
        if relative:
            initializer.write_text("", encoding="utf-8")
        measure, carrier = package / "measure.py", package / "carrier.py"
        import_statement = "from .carrier import exported" if relative else "from carrier import exported"
        measure.write_text(
            f"{declaration}{import_statement}\nexported('plugin')\n", encoding="utf-8"
        )
        carrier.write_text("VALUE = 1\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        root = "package/measure.py" if relative else "measure.py"
        document.write_text(_sealed_contract(roots=(root,)), encoding="utf-8")
        code_files = (measure, carrier, initializer) if relative else (measure, carrier)

        if relative:
            (tmp_path / "measure.py").write_text("VALUE = 1\n", encoding="utf-8")
        with pytest.raises(
            evidence.EvidenceSchemaError,
            match="unresolved callable alias|function-body object mutation",
        ):
            prereg.finalize_prereg(
                document,
                repo_root=tmp_path,
                code_files=code_files,
                manifest_path=_canonical_seal_path(tmp_path, document),
                sealed_at="2026-07-14T00:00:00+00:00",
            )

    @pytest.mark.parametrize(("declaration", "relative"), [
        ("def exported(name):\n    return name\n", False),
        ("class exported:\n    def __init__(self, name):\n        self.name = name\n", False),
        ("def exported(name):\n    return name\n", True),
        ("class exported:\n    def __init__(self, name):\n        self.name = name\n", True),
    ])
    def test_finalize_prereg_rejects_local_wildcard_import_after_callable_declaration(
        self, tmp_path, declaration, relative
    ):
        package = tmp_path / "package" if relative else tmp_path
        package.mkdir(exist_ok=True)
        initializer = package / "__init__.py"
        if relative:
            initializer.write_text("", encoding="utf-8")
        measure, carrier = package / "measure.py", package / "carrier.py"
        import_statement = "from .carrier import *" if relative else "from carrier import *"
        measure.write_text(
            f"{declaration}{import_statement}\nexported('plugin')\n", encoding="utf-8"
        )
        carrier.write_text(
            "import importlib\ndef exported(name):\n    return importlib.import_module(name)\n",
            encoding="utf-8",
        )
        document = tmp_path / "prereg.md"
        root = "package/measure.py" if relative else "measure.py"
        document.write_text(_sealed_contract(roots=(root,)), encoding="utf-8")
        code_files = (measure, carrier, initializer) if relative else (measure, carrier)

        if relative:
            (tmp_path / "measure.py").write_text("VALUE = 1\n", encoding="utf-8")
        with pytest.raises(
            evidence.EvidenceSchemaError, match="wildcard import is unsupported|sealed mutation"
        ):
            prereg.finalize_prereg(
                document,
                repo_root=tmp_path,
                code_files=code_files,
                manifest_path=_canonical_seal_path(tmp_path, document),
                sealed_at="2026-07-14T00:00:00+00:00",
            )
    def test_finalize_prereg_allows_direct_local_module_function_and_scans_plugin(self, tmp_path):
        measure, carrier, plugin = (
            tmp_path / "measure.py",
            tmp_path / "carrier.py",
            tmp_path / "plugin.py",
        )
        measure.write_text("import carrier\ncarrier.safe_func()\n", encoding="utf-8")
        carrier.write_text(
            "import importlib\ndef safe_func():\n    return importlib.import_module('plugin')\n",
            encoding="utf-8",
        )
        plugin.write_text("VALUE = 1\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(
            _sealed_contract(
                roots=("measure.py",), dynamic_python=("plugin.py",)
            ),
            encoding="utf-8",
        )

        assert prereg.derive_prereg_code_manifest(document.read_text(encoding="utf-8"), tmp_path) == {
            "measure.py", "carrier.py", "plugin.py"
        }
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")
        with pytest.raises(
            evidence.EvidenceSchemaError, match="dynamic_python_dependencies"
        ):
            prereg.derive_prereg_code_manifest(document.read_text(encoding="utf-8"), tmp_path)
    @pytest.mark.parametrize(("source", "dynamic_python"), [
        ("import package.plugin\n", ()),
        ("__import__('package.plugin')\n", ("package/plugin.py",)),
        (
            "import importlib\nimportlib.import_module('package.plugin')\n",
            ("package/plugin.py",),
        ),
    ])
    def test_code_manifest_rejects_package_module_collision_for_every_import_form(
        self, tmp_path, source, dynamic_python,
    ):
        package = tmp_path / "package"
        package.mkdir()
        (tmp_path / "measure.py").write_text(source, encoding="utf-8")
        (tmp_path / "package.py").write_text("DECOY = True\n", encoding="utf-8")
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "plugin.py").write_text("VALUE = 1\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(
            _sealed_contract(
                roots=("measure.py",), dynamic_python=dynamic_python
            ),
            encoding="utf-8",
        )

        with pytest.raises(
            evidence.EvidenceSchemaError,
            match=r"ambiguous local module/package resolution: package",
        ):
            prereg.derive_prereg_code_manifest(
                document.read_text(encoding="utf-8"), tmp_path
            )
    def test_local_receiver_provenance_rejects_package_module_collision(self, tmp_path):
        package = tmp_path / "package"
        package.mkdir()
        (tmp_path / "package.py").write_text("DECOY = True\n", encoding="utf-8")
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "plugin.py").write_text("VALUE = 1\n", encoding="utf-8")
        source = "import package.plugin\npackage.plugin.run()\n"
        tree = ast.parse(source)
        _, aliases = prereg._dynamic_call_kinds(tree)

        with pytest.raises(
            evidence.EvidenceSchemaError,
            match=r"ambiguous local module/package resolution: package",
        ):
            prereg._reject_unresolved_module_receivers(
                tree, aliases, tmp_path / "measure.py", tmp_path
            )
    @pytest.mark.parametrize(("source_template", "dynamic_python"), [
        ("import {target}\n", ()),
        ("from {target} import VALUE\n", ()),
        ("__import__('{target}')\n", ("{target_path}",)),
        (
            "import importlib\nimportlib.import_module('{target}')\n",
            ("{target_path}",),
        ),
    ], ids=("import", "import_from", "builtin_dynamic", "importlib_dynamic"))
    @pytest.mark.parametrize(("parts", "target"), [
        ((), "plugin"),
        (("package",), "package.plugin"),
        (("package", "nested"), "package.nested.plugin"),
    ], ids=("root", "regular_package", "nested_package"))
    @pytest.mark.parametrize("suffix", [
        importlib.machinery.BYTECODE_SUFFIXES[0],
        importlib.machinery.EXTENSION_SUFFIXES[0],
    ], ids=("bytecode", "extension"))
    def test_code_manifest_rejects_importable_artifact_for_every_import_form(
        self, tmp_path, source_template, dynamic_python, parts, target, suffix,
    ):
        package = tmp_path
        for part in parts:
            package /= part
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
        plugin = package / "plugin.py"
        plugin.write_text("VALUE = 1\n", encoding="utf-8")
        plugin.with_suffix(suffix).write_bytes(b"unsealed executable artifact")
        (tmp_path / "measure.py").write_text(
            source_template.format(target=target), encoding="utf-8"
        )
        document = tmp_path / "prereg.md"
        target_path = plugin.relative_to(tmp_path).as_posix()
        document.write_text(
            _sealed_contract(
                roots=("measure.py",),
                dynamic_python=tuple(
                    item.format(target_path=target_path) for item in dynamic_python
                ),
            ),
            encoding="utf-8",
        )

        with pytest.raises(
            evidence.EvidenceSchemaError,
            match="bytecode/native import artifact",
        ):
            prereg.derive_prereg_code_manifest(
                document.read_text(encoding="utf-8"), tmp_path
            )

    @pytest.mark.parametrize("artifact_part", [0, 1, 2], ids=(
        "root_package", "nested_package", "module",
    ))
    @pytest.mark.parametrize("suffix", [
        importlib.machinery.BYTECODE_SUFFIXES[0],
        importlib.machinery.EXTENSION_SUFFIXES[0],
    ])
    def test_local_receiver_provenance_rejects_artifact_in_every_import_segment(
        self, tmp_path, artifact_part, suffix,
    ):
        package = tmp_path
        package_parts = ("package", "nested")
        for part in package_parts:
            package /= part
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
        plugin = package / "plugin.py"
        plugin.write_text("def run():\n    return None\n", encoding="utf-8")
        segments = (
            tmp_path / "package",
            tmp_path / "package" / "nested",
            plugin,
        )
        artifact = (
            segments[artifact_part] / f"__init__{suffix}"
            if artifact_part < 2
            else plugin.with_suffix(suffix)
        )
        artifact.write_bytes(b"unsealed executable artifact")
        source = "import package.nested.plugin\npackage.nested.plugin.run()\n"
        tree = ast.parse(source)
        _, aliases = prereg._dynamic_call_kinds(tree)

        with pytest.raises(
            evidence.EvidenceSchemaError,
            match="bytecode/native import artifact",
        ):
            prereg._reject_unresolved_module_receivers(
                tree, aliases, tmp_path / "measure.py", tmp_path
            )

    @pytest.mark.parametrize(("source_template", "dynamic_python"), [
        ("import {target}\n", ()),
        ("__import__('{target}')\n", ("{target_path}",)),
        (
            "import importlib\nimportlib.import_module('{target}')\n",
            ("{target_path}",),
        ),
    ], ids=("static_import", "builtin_import", "importlib_import"))
    @pytest.mark.parametrize(("namespace_parts", "target", "target_path"), [
        (("namespace",), "namespace.target", "namespace/target/__init__.py"),
        (
            ("package", "namespace"),
            "package.namespace.target",
            "package/namespace/target/__init__.py",
        ),
    ], ids=("root_namespace", "nested_namespace"))
    def test_code_manifest_rejects_implicit_namespace_for_every_import_form(
        self, tmp_path, source_template, dynamic_python, namespace_parts, target, target_path,
    ):
        target_file = tmp_path / target_path
        target_file.parent.mkdir(parents=True)
        target_file.write_text("", encoding="utf-8")
        for index in range(1, len(namespace_parts)):
            package = tmp_path.joinpath(*namespace_parts[:index])
            (package / "__init__.py").write_text("", encoding="utf-8")
        (tmp_path / "measure.py").write_text(
            source_template.format(target=target), encoding="utf-8"
        )
        document = tmp_path / "prereg.md"
        document.write_text(
            _sealed_contract(
                roots=("measure.py",),
                dynamic_python=tuple(
                    item.format(target_path=target_path) for item in dynamic_python
                ),
            ),
            encoding="utf-8",
        )

        with pytest.raises(
            evidence.EvidenceSchemaError,
            match=rf"implicit namespace package is unsupported: {'.'.join(namespace_parts)}",
        ):
            prereg.derive_prereg_code_manifest(
                document.read_text(encoding="utf-8"), tmp_path
            )
    @pytest.mark.parametrize(("namespace_parts", "target", "target_path"), [
        (("namespace",), "namespace.target", "namespace/target/__init__.py"),
        (
            ("package", "namespace"),
            "package.namespace.target",
            "package/namespace/target/__init__.py",
        ),
    ], ids=("root_namespace", "nested_namespace"))
    def test_local_receiver_provenance_rejects_implicit_namespace(
        self, tmp_path, namespace_parts, target, target_path,
    ):
        target_file = tmp_path / target_path
        target_file.parent.mkdir(parents=True)
        target_file.write_text("def run():\n    return None\n", encoding="utf-8")
        for index in range(1, len(namespace_parts)):
            package = tmp_path.joinpath(*namespace_parts[:index])
            (package / "__init__.py").write_text("", encoding="utf-8")
        tree = ast.parse(f"import {target}\n{target}.run()\n")
        _, aliases = prereg._dynamic_call_kinds(tree)

        with pytest.raises(
            evidence.EvidenceSchemaError,
            match=rf"implicit namespace package is unsupported: {'.'.join(namespace_parts)}",
        ):
            prereg._reject_unresolved_module_receivers(
                tree, aliases, tmp_path / "measure.py", tmp_path
            )

    @pytest.mark.parametrize(("source_template", "dynamic_python"), [
        ("import {target}\n", ()),
        ("__import__('{target}')\n", ("{target_path}",)),
        (
            "import importlib\nimportlib.import_module('{target}')\n",
            ("{target_path}",),
        ),
    ], ids=("static_import", "builtin_import", "importlib_import"))
    @pytest.mark.parametrize("target", [
        "namespace.target",
        "package.namespace.target",
    ], ids=("root_package", "nested_package"))
    def test_code_manifest_allows_sealed_packages_for_every_import_form(
        self, tmp_path, source_template, dynamic_python, target,
    ):
        package = tmp_path
        expected = {"measure.py"}
        for part in target.split("."):
            package /= part
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            expected.add((package / "__init__.py").relative_to(tmp_path).as_posix())
        target_path = "/".join((*target.split("."), "__init__.py"))
        (tmp_path / "measure.py").write_text(
            source_template.format(target=target), encoding="utf-8"
        )
        document = tmp_path / "prereg.md"
        document.write_text(
            _sealed_contract(
                roots=("measure.py",),
                dynamic_python=tuple(
                    item.format(target_path=target_path) for item in dynamic_python
                ),
            ),
            encoding="utf-8",
        )

        assert prereg.derive_prereg_code_manifest(
            document.read_text(encoding="utf-8"), tmp_path
        ) == expected

    @pytest.mark.parametrize(("namespace_parts", "target_path"), [
        (("namespace",), "namespace/target/__init__.py"),
        (
            ("package", "namespace"),
            "package/namespace/target/__init__.py",
        ),
    ], ids=("root_namespace", "nested_namespace"))
    def test_dependency_roots_reject_implicit_namespace_ancestry(
        self, tmp_path, namespace_parts, target_path,
    ):
        target_file = tmp_path / target_path
        target_file.parent.mkdir(parents=True)
        target_file.write_text("", encoding="utf-8")
        for index in range(1, len(namespace_parts)):
            package = tmp_path.joinpath(*namespace_parts[:index])
            (package / "__init__.py").write_text("", encoding="utf-8")
        (tmp_path / "measure.py").write_text("VALUE = 1\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(
            _sealed_contract(roots=(target_path,)), encoding="utf-8"
        )

        with pytest.raises(
            evidence.EvidenceSchemaError,
            match=rf"implicit namespace package is unsupported: {'.'.join(namespace_parts)}",
        ):
            prereg.derive_prereg_code_manifest(
                document.read_text(encoding="utf-8"), tmp_path
            )
    @pytest.mark.parametrize("suffix", [
        importlib.machinery.BYTECODE_SUFFIXES[0],
        importlib.machinery.EXTENSION_SUFFIXES[0],
    ], ids=("bytecode", "extension"))
    def test_unimported_dependency_root_artifact_is_inert(self, tmp_path, suffix):
        code = tmp_path / "code"
        code.mkdir()
        (code / "entry.py").write_text("VALUE = 1\n", encoding="utf-8")
        (code / "entry.py").with_suffix(suffix).write_bytes(b"inert artifact")
        (tmp_path / "measure.py").write_text("VALUE = 1\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(
            _sealed_contract(roots=("code/entry.py",)), encoding="utf-8"
        )

        assert prereg.derive_prereg_code_manifest(
            document.read_text(encoding="utf-8"), tmp_path
        ) == {"code/entry.py"}
    def test_direct_script_rejects_legacy_plugin_pyc_sibling(self, tmp_path):
        code = tmp_path / "code"
        code.mkdir()
        (code / "entry.py").write_text("import plugin\n", encoding="utf-8")
        (code / "plugin.pyc").write_bytes(b"legacy bytecode")
        (tmp_path / "measure.py").write_text("VALUE = 1\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("code/entry.py",)), encoding="utf-8")

        with pytest.raises(
            evidence.EvidenceSchemaError,
            match=r"unsealed direct-script local import candidate: plugin",
        ):
            prereg.derive_prereg_code_manifest(document.read_text(encoding="utf-8"), tmp_path)

    @pytest.mark.parametrize("kind", ("source", "package", "namespace", "extension"))
    def test_direct_script_rejects_local_import_sibling_kinds(self, tmp_path, kind):
        code = tmp_path / "code"
        code.mkdir()
        (code / "entry.py").write_text("import plugin\n", encoding="utf-8")
        if kind == "source":
            (code / "plugin.py").write_text("VALUE = 1\n", encoding="utf-8")
        elif kind == "extension":
            (code / f"plugin{importlib.machinery.EXTENSION_SUFFIXES[0]}").write_bytes(b"extension")
        else:
            plugin = code / "plugin"
            plugin.mkdir()
            if kind == "package":
                (plugin / "__init__.py").write_text("", encoding="utf-8")
        (tmp_path / "measure.py").write_text("VALUE = 1\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("code/entry.py",)), encoding="utf-8")

        with pytest.raises(
            evidence.EvidenceSchemaError,
            match=r"unsealed direct-script local import candidate: plugin",
        ):
            prereg.derive_prereg_code_manifest(document.read_text(encoding="utf-8"), tmp_path)

    def test_direct_script_rejects_shadow_in_imported_dependency(self, tmp_path):
        code = tmp_path / "code"
        code.mkdir()
        (code / "entry.py").write_text("import shared\n", encoding="utf-8")
        (code / "alpha.py").write_text("DECOY = True\n", encoding="utf-8")
        (tmp_path / "shared.py").write_text("import alpha\n", encoding="utf-8")
        (tmp_path / "alpha.py").write_text("VALUE = 1\n", encoding="utf-8")
        (tmp_path / "measure.py").write_text("VALUE = 1\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("code/entry.py",)), encoding="utf-8")

        with pytest.raises(
            evidence.EvidenceSchemaError,
            match=r"unsealed direct-script local import candidate: alpha",
        ):
            prereg.derive_prereg_code_manifest(document.read_text(encoding="utf-8"), tmp_path)

    def test_direct_script_rejects_multiple_dependency_root_parent_ambiguity(self, tmp_path):
        for directory in ("one", "two"):
            script_dir = tmp_path / directory
            script_dir.mkdir()
            (script_dir / "entry.py").write_text("import plugin\n", encoding="utf-8")
            (script_dir / "plugin.py").write_text("VALUE = 1\n", encoding="utf-8")
        (tmp_path / "measure.py").write_text("VALUE = 1\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(
            _sealed_contract(roots=("one/entry.py", "two/entry.py")),
            encoding="utf-8",
        )

        with pytest.raises(
            evidence.EvidenceSchemaError,
            match=r"ambiguous direct-script import across dependency-root parents: plugin",
        ):
            prereg.derive_prereg_code_manifest(document.read_text(encoding="utf-8"), tmp_path)

    def test_direct_script_allows_repo_package_without_sibling(self, tmp_path):
        code = tmp_path / "code"
        code.mkdir()
        (code / "entry.py").write_text("import alpha.plugin\n", encoding="utf-8")
        alpha = tmp_path / "alpha"
        alpha.mkdir()
        (alpha / "__init__.py").write_text("", encoding="utf-8")
        (alpha / "plugin.py").write_text("VALUE = 1\n", encoding="utf-8")
        (tmp_path / "measure.py").write_text("VALUE = 1\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("code/entry.py",)), encoding="utf-8")

        assert prereg.derive_prereg_code_manifest(
            document.read_text(encoding="utf-8"), tmp_path
        ) == {"code/entry.py", "alpha/__init__.py", "alpha/plugin.py"}
    def test_code_manifest_rejects_nested_package_module_collision(self, tmp_path):
        package = tmp_path / "package"
        nested = package / "nested"
        nested.mkdir(parents=True)
        (tmp_path / "measure.py").write_text(
            "import package.nested.plugin\n", encoding="utf-8"
        )
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "nested.py").write_text("DECOY = True\n", encoding="utf-8")
        (nested / "__init__.py").write_text("", encoding="utf-8")
        (nested / "plugin.py").write_text("VALUE = 1\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")

        with pytest.raises(
            evidence.EvidenceSchemaError,
            match=r"ambiguous local module/package resolution: package\.nested",
        ):
            prereg.derive_prereg_code_manifest(
                document.read_text(encoding="utf-8"), tmp_path
            )
    def test_code_manifest_rejects_collision_in_package_initializer_closure(self, tmp_path):
        package = tmp_path / "package"
        package.mkdir()
        (tmp_path / "package.py").write_text("DECOY = True\n", encoding="utf-8")
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "plugin.py").write_text("VALUE = 1\n", encoding="utf-8")
        (tmp_path / "measure.py").write_text("VALUE = 1\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(
            _sealed_contract(roots=("package/plugin.py",)), encoding="utf-8"
        )

        with pytest.raises(
            evidence.EvidenceSchemaError,
            match=r"ambiguous local module/package resolution: package",
        ):
            prereg.derive_prereg_code_manifest(
                document.read_text(encoding="utf-8"), tmp_path
            )

    def test_code_manifest_resolves_nonambiguous_module_and_package(self, tmp_path):
        package = tmp_path / "package"
        package.mkdir()
        measure, module, initializer, plugin = (
            tmp_path / "measure.py",
            tmp_path / "module.py",
            package / "__init__.py",
            package / "plugin.py",
        )
        measure.write_text("import module\nimport package.plugin\n", encoding="utf-8")
        module.write_text("VALUE = 1\n", encoding="utf-8")
        initializer.write_text("", encoding="utf-8")
        plugin.write_text("VALUE = 1\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")

        assert prereg.derive_prereg_code_manifest(
            document.read_text(encoding="utf-8"), tmp_path
        ) == {"measure.py", "module.py", "package/__init__.py", "package/plugin.py"}

    def test_dynamic_dependency_allows_static_module_and_sealed_local_calls(self, tmp_path):
        source = "import numpy as np\ndef sealed_local():\n    return np.mean([1, 2])\nsealed_local()\n"
        assert prereg._dynamic_local_dependencies(
            ast.parse(source), tmp_path / "measure.py", tmp_path
        ) == set()
    def test_code_manifest_allows_trusted_external_from_sysconfig_root(self, tmp_path):
        trusted = tmp_path / "trusted"
        trusted.mkdir()
        (trusted / "numpy.py").write_text("VALUE = 1\n", encoding="utf-8")
        measure = tmp_path / "measure.py"
        measure.write_text("import numpy\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")

        with _temporary_trusted_external_root(trusted):
            assert prereg.derive_prereg_code_manifest(
                document.read_text(encoding="utf-8"), tmp_path
            ) == {"measure.py"}

    def test_code_manifest_rejects_unresolved_external_import_before_seal(self, tmp_path):
        measure = tmp_path / "measure.py"
        measure.write_text("import sealed_unknown_plugin\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")

        with pytest.raises(
            evidence.EvidenceSchemaError, match=r"unresolved external import: sealed_unknown_plugin"
        ):
            prereg.finalize_prereg(
                document,
                repo_root=tmp_path,
                code_files=(measure,),
                manifest_path=_canonical_seal_path(tmp_path, document),
                sealed_at="2026-07-15T00:00:00+00:00",
            )

        (tmp_path / "sealed_unknown_plugin.py").write_text("VALUE = 1\n", encoding="utf-8")
        with pytest.raises(
            evidence.EvidenceSchemaError,
            match="code_files must equal derived Python dependency closure",
        ):
            prereg.finalize_prereg(
                document,
                repo_root=tmp_path,
                code_files=(measure,),
                manifest_path=_canonical_seal_path(tmp_path, document),
                sealed_at="2026-07-15T00:00:00+00:00",
            )
        assert not _canonical_seal_path(tmp_path, document).exists()

    def test_code_manifest_rejects_post_added_local_shadow_of_trusted_external(self, tmp_path):
        trusted = tmp_path / "trusted"
        trusted.mkdir()
        (trusted / "numpy.py").write_text("VALUE = 1\n", encoding="utf-8")
        measure = tmp_path / "measure.py"
        measure.write_text("import numpy\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(_sealed_contract(roots=("measure.py",)), encoding="utf-8")

        with _temporary_trusted_external_root(trusted):
            assert prereg.derive_prereg_code_manifest(
                document.read_text(encoding="utf-8"), tmp_path
            ) == {"measure.py"}
            (tmp_path / "numpy.py").write_text("VALUE = 2\n", encoding="utf-8")
            with pytest.raises(
                evidence.EvidenceSchemaError, match=r"ambiguous local/external import: numpy"
            ):
                prereg.derive_prereg_code_manifest(document.read_text(encoding="utf-8"), tmp_path)
    def test_dynamic_dependency_allows_direct_static_module_alias(self, tmp_path):
        plugin = tmp_path / "plugin.py"
        plugin.write_text("VALUE = 1\n", encoding="utf-8")
        source = (
            "import importlib as imported_module\n"
            "loader = imported_module\n"
            "loader.import_module('plugin')\n"
        )
        assert prereg._dynamic_local_dependencies(
            ast.parse(source), tmp_path / "measure.py", tmp_path
        ) == {plugin.resolve()}
    def test_finalize_prereg_allows_hashed_direct_dynamic_import(self, tmp_path):
        measure, plugin = tmp_path / "measure.py", tmp_path / "plugin.py"
        measure.write_text("from importlib import import_module\ndef sealed_local():\n    return 'ok'\nsealed_local()\nplugin = import_module('plugin')\n", encoding="utf-8")
        plugin.write_text("VALUE = 1\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(
            _sealed_contract(roots=("measure.py",), dynamic_python=("plugin.py",)),
            encoding="utf-8",
        )
        seal = prereg.finalize_prereg(
            document,
            repo_root=tmp_path,
            code_files=(measure, plugin),
            manifest_path=_canonical_seal_path(tmp_path, document),
            sealed_at="2026-07-14T00:00:00+00:00",
        )
        assert [item["path"] for item in seal["code_manifest"]] == ["measure.py", "plugin.py"]
    def test_finalize_prereg_allows_exact_builtin_dynamic_import(self, tmp_path):
        measure, plugin = tmp_path / "measure.py", tmp_path / "plugin.py"
        measure.write_text("plugin = __import__('plugin')\n", encoding="utf-8")
        plugin.write_text("VALUE = 1\n", encoding="utf-8")
        document = tmp_path / "prereg.md"
        document.write_text(
            _sealed_contract(roots=("measure.py",), dynamic_python=("plugin.py",)),
            encoding="utf-8",
        )

        seal = prereg.finalize_prereg(
            document,
            repo_root=tmp_path,
            code_files=(measure, plugin),
            manifest_path=_canonical_seal_path(tmp_path, document),
            sealed_at="2026-07-15T00:00:00+00:00",
        )

        assert [item["path"] for item in seal["code_manifest"]] == ["measure.py", "plugin.py"]
    def test_recheck_authority_paths_rejects_case_nested_hardlink_and_symlink_aliases(self, tmp_path):
        target = tmp_path / "measure.py"
        target.write_text("VALUE = 1\n", encoding="utf-8")
        authority = {
            "seal_dir": "seals",
            "promotions_dir": "promotions",
            "catalog_dir": "catalog",
            "target_db": "measure.py",
            "journal_dir": "journal",
            "backup_dir": "backups",
        }
        assert prereg.revalidate_authority_paths(tmp_path, authority) == authority

        protected = {**authority, "target_db": "_DATABASE/measure.py"}
        (tmp_path / "_DATABASE").mkdir()
        (tmp_path / "_DATABASE" / "measure.py").write_text("VALUE = 1\n", encoding="utf-8")
        with pytest.raises(evidence.EvidenceSchemaError, match="protected"):
            prereg.recheck_authority_paths(protected, tmp_path)
        with pytest.raises(evidence.EvidenceSchemaError, match="semantically distinct"):
            prereg.recheck_authority_paths({**authority, "promotions_dir": "Seals"}, tmp_path)
        with pytest.raises(evidence.EvidenceSchemaError, match="semantically distinct"):
            prereg.recheck_authority_paths({**authority, "promotions_dir": "seals/archive"}, tmp_path)

        hardlink = tmp_path / "hardlink.py"
        hardlink.hardlink_to(target)
        document = tmp_path / "hardlink-prereg.md"
        document.write_text(
            _sealed_contract(
                roots=("measure.py",),
                authority_paths={**authority, "target_db": "hardlink.py"},
            ),
            encoding="utf-8",
        )
        canonical = _canonical_seal_path(tmp_path, document)
        original_document = document.read_bytes()
        with pytest.raises(evidence.EvidenceSchemaError, match="hardlink"):
            prereg.finalize_prereg(
                document,
                repo_root=tmp_path,
                code_files=(target,),
                manifest_path=canonical,
                sealed_at="2026-07-14T00:00:00+00:00",
            )
        assert document.read_bytes() == original_document
        assert not canonical.exists()
        hardlink.unlink()
        ledger_source = tmp_path / "ledger-source.jsonl"
        ledger_source.write_text("{}\n", encoding="utf-8")
        ledger_alias = tmp_path / "ledger-alias.jsonl"
        ledger_alias.hardlink_to(ledger_source)
        document = tmp_path / "ledger-hardlink-prereg.md"
        document.write_text(
            _sealed_contract(roots=("measure.py",), ledger_path="ledger-alias.jsonl"),
            encoding="utf-8",
        )
        with pytest.raises(evidence.EvidenceSchemaError, match="ledger_path.*hardlink"):
            prereg.finalize_prereg(
                document,
                repo_root=tmp_path,
                code_files=(target,),
                manifest_path=_canonical_seal_path(tmp_path, document),
                sealed_at="2026-07-14T00:00:00+00:00",
            )
        ledger_alias.unlink()

        linked = tmp_path / "linked"
        try:
            linked.symlink_to(tmp_path / "seals", target_is_directory=True)
        except OSError:
            pytest.skip("symlink creation is unavailable")
        with pytest.raises(evidence.EvidenceSchemaError, match="symlink or reparse"):
            prereg.recheck_authority_paths({**authority, "seal_dir": "linked"}, tmp_path)
        seals = tmp_path / "seals"
        seals.mkdir()
        assert prereg.revalidate_authority_paths(tmp_path, authority) == authority
        seals.rmdir()
        seals.write_text("swapped", encoding="utf-8")
        with pytest.raises(evidence.EvidenceSchemaError, match="directory"):
            prereg.revalidate_authority_paths(tmp_path, authority)
    @pytest.mark.skipif(os.name != "nt", reason="Windows final-handle hardlink validation")
    def test_absent_ledger_hardlink_race_is_rejected_before_append(self, tmp_path):
        target_db = tmp_path / "measure.py"
        target_db.write_text("VALUE = 1\n", encoding="utf-8")
        authority = {
            "seal_dir": "seals",
            "promotions_dir": "promotions",
            "catalog_dir": "catalog",
            "target_db": "measure.py",
            "journal_dir": "journal",
            "backup_dir": "backups",
        }
        target, source = tmp_path / "ledger.jsonl", tmp_path / "race-source.jsonl"
        source.write_text("{}\n", encoding="utf-8")
        source_before = source.read_bytes()
        with prereg.authority_mutation_guard(tmp_path, authority, fields=("seal_dir",)) as guard:
            guard.hold_path(target)
            original_open = guard.open_path
            raced = False

            def open_after_hardlink(path, flags, mode=0o666):
                nonlocal raced
                if Path(path) == target and flags == os.O_RDONLY and not raced:
                    target.hardlink_to(source)
                    raced = True
                return original_open(path, flags, mode)

            guard.open_path = open_after_hardlink
            with pytest.raises(evidence.EvidenceSchemaError, match="hardlinked"):
                ledger._append_record(target, VALID_ROW, guard=guard)
        assert raced
        assert source.read_bytes() == source_before

# ---------------------------------------------------------------------------
# trials_report — 시행 병기 블록 (소비 전용)
# ---------------------------------------------------------------------------


class TestTrialsReport:
    def _make_ledger(self, tmp_path) -> Path:
        path = tmp_path / "l.jsonl"
        for i in range(3):
            ledger._append_record(path, _row(series="D1", target=f"절 #{i}"))
        ledger._append_record(path, _row(series="S-트랙"))
        return path

    def test_block_contents(self, tmp_path):
        path = self._make_ledger(tmp_path)
        block = trials_report.build_trials_block(
            family_label="D1 절-단위 A/B(자격 절)",
            family_denominator=34,
            series="D1",
            path=path,
            generated_ts="2026-07-12T23:59:00",
        )
        assert "| 족 분모(FDR) | 34 |" in block
        assert "| 계열(D1) 누계 | 3" in block
        assert "| 전역 누계(본 프로그램) | 4" in block
        assert "√(2·ln N)" in block
        assert "1,100+" in block  # 구 프로그램 누계 병기
        assert "기입하지 않는다" in block  # 소비 전용 명시

    def test_unknown_series_rejected(self, tmp_path):
        path = self._make_ledger(tmp_path)
        with pytest.raises(ValueError):
            trials_report.build_trials_block(
                family_label="족", family_denominator=1, series="없는계열", path=path
            )

    def test_denominator_validation(self, tmp_path):
        path = self._make_ledger(tmp_path)
        for bad in (0, -1, True, "34"):
            with pytest.raises(ValueError):
                trials_report.build_trials_block(
                    family_label="족", family_denominator=bad, path=path
                )

    def test_module_has_no_write_path(self):
        """A6 채택 조건 — 리포터는 원장 기입 API를 노출·재정의하지 않는다."""
        assert not hasattr(trials_report, "append_trial")


# ---------------------------------------------------------------------------
# lint — known 창 접촉 문서 린터 (보고 전용)
# ---------------------------------------------------------------------------

V1_FIXTURE = "\n".join(
    [
        "# W3 프로파일링 표본일 목록",
        "",
        "**tick 표본일 20일**:",
        "- 2022: 20220517, 20220714",
        "- 2025: 20250507, 20250728, 20250908",
        "",
        "등락율 축 경계 산정은 pooled 20일 표본으로 수행했다.",
    ]
)

CLEAN_FIXTURE = "\n".join(
    [
        "# 발견창 측정 계획",
        "- 측정창: 2022-03-23~2023-12-31 표본 863,446건 적재",
        "- 작성일: 2026-07-12 (문서 날짜 — 데이터 아님)",
        "- 후속 백테 예산은 0회다.",
    ]
)

POLICY_FIXTURE = "\n".join(
    [
        "## 창 지위",
        "| 2025-01-01 ~ 2026-02-27 | known/audit | 선택·튜닝 금지. veto 전용. 적재 시 별도 파티션 |",
    ]
)


class TestLint:
    def test_v1_fixture_redetected(self):
        findings = lint.scan_text(V1_FIXTURE, source="v1_fixture.md")
        flagged = [f for f in findings if any(t.startswith("2025") for t in f["date_tokens"])]
        assert flagged, "V-1형 known 2025 표본일이 재검출돼야 한다"
        assert flagged[0]["zone"] == "KNOWN"
        assert "표본" in flagged[0]["keywords"] or "산정" in flagged[0]["keywords"]
        assert flagged[0]["category"] == "measurement_context"

    def test_proximity_keyword_within_3_lines(self):
        text = "온셋 20250908 목록\n줄1\n줄2\n표본 하한 검토"
        assert lint.scan_text(text)  # 3행 아래 키워드 — 근접 인정
        text_far = "온셋 20250908 목록\n줄1\n줄2\n줄3\n줄4\n표본 하한 검토"
        assert lint.scan_text(text_far) == []  # 4행 밖 — 근접 아님

    def test_clean_discovery_and_doc_dates_not_flagged(self):
        assert lint.scan_text(CLEAN_FIXTURE, source="clean.md") == []

    def test_policy_line_classified_as_policy_context(self):
        findings = lint.scan_text(POLICY_FIXTURE, source="ledger_doc.md")
        assert findings  # 보고는 유지(억제하지 않음)
        assert findings[0]["category"] == "policy_context"

    def test_2024_flagged_only_with_exit_series_context(self):
        neutral = "신규 가설 측정 표본: 2024-05-13 포함"
        assert lint.scan_text(neutral) == []
        exit_ctx = "청산 레버 반사실 측정 표본: 2024-05-13 포함"
        findings = lint.scan_text(exit_ctx)
        assert findings and "CONDITIONAL_2024" in findings[0]["zone"]

    def test_scan_paths_and_render(self, tmp_path):
        (tmp_path / "a.md").write_text(V1_FIXTURE, encoding="utf-8")
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "b.md").write_text(CLEAN_FIXTURE, encoding="utf-8")
        result = lint.scan_paths([tmp_path])
        assert result["files_scanned"] == 2
        assert result["summary"]["flagged_lines"] >= 1
        report = lint.render_report(result)
        assert "보고 전용" in report and "a.md" in report

    def test_cli_main_always_exit_zero(self, tmp_path, capsys):
        """A4 채택 조건 — 플래그가 있어도 차단하지 않는다(exit 0)."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "ledger_lint_cli", ROOT / "scripts" / "ledger_lint.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        (tmp_path / "v1.md").write_text(V1_FIXTURE, encoding="utf-8")
        assert module.main([str(tmp_path)]) == 0
        assert "보고 전용" in capsys.readouterr().out


@pytest.mark.skipif(not REAL_RUNS_DIR.exists(), reason="실물 코퍼스 부재 환경")
class TestLintRealCorpus:
    def test_v1_redetected_in_w3_profiling_report(self):
        """합격 기준(A4): 원장 §6 V-1 — W3 known 2025 표본 접촉 재검출."""
        result = lint.scan_paths([REAL_RUNS_DIR])
        w3_hits = [
            f
            for f in result["findings"]
            if Path(f["file"]).name == "w3_profiling_report.md"
            and any(t.startswith("2025") for t in f["date_tokens"])
        ]
        assert w3_hits, "V-1(W3 known 2025 표본일) 재검출 실패"
