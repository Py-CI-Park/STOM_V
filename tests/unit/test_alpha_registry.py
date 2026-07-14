"""alpha_lab.registry 단위 테스트 — 봉인 결정성·멱등·위반 검출 + n_trials 원장.

실DB 불필요(전부 tmp_path 합성). 실행: python -m pytest tests/unit/test_alpha_registry.py -q
"""

import datetime as dt
import hashlib
import json
import os
import tempfile
from pathlib import Path

import pytest

from alpha_lab import registry
from alpha_lab.discipline import ledger as authority_ledger
from alpha_lab.registry import (
    SealViolation,
    append_trials,
    canonical_json,
    seal,
    sha256_of,
    total_trials,
    verify_seal,
)

NOW = dt.datetime(2026, 7, 5, 9, 30, 0)
DEFAULT_LEGACY_NON_AUTHORITATIVE_LEDGER_ROOT = (
    registry.LEGACY_NON_AUTHORITATIVE_LEDGER_ROOT
)


@pytest.fixture(autouse=True)
def legacy_non_authoritative_ledger_root(tmp_path, monkeypatch):
    """Keep legacy-ledger tests inside their isolated archive root."""
    monkeypatch.setattr(registry, "LEGACY_NON_AUTHORITATIVE_LEDGER_ROOT", tmp_path)


def test_default_legacy_archive_root_is_external_runtime_location():
    assert DEFAULT_LEGACY_NON_AUTHORITATIVE_LEDGER_ROOT == (
        Path(tempfile.gettempdir())
        / registry.LEGACY_NON_AUTHORITATIVE_ARCHIVE_DIRECTORY
    )
    assert not DEFAULT_LEGACY_NON_AUTHORITATIVE_LEDGER_ROOT.is_relative_to(
        Path(registry.__file__).resolve().parents[1]
    )



def _payload_a() -> dict:
    return {"b": [1, 2, 3], "a": {"y": "한글", "x": 0.05}, "c": 1}


def _payload_a_shuffled() -> dict:
    """_payload_a와 내용 동일, 키 순서만 뒤섞음."""
    return {"c": 1, "a": {"x": 0.05, "y": "한글"}, "b": [1, 2, 3]}


class TestCanonicalJson:
    def test_key_order_invariant(self):
        assert canonical_json(_payload_a()) == canonical_json(_payload_a_shuffled())

    def test_format_contract(self):
        text = canonical_json({"b": 1, "a": "한글"})
        assert text == '{"a": "한글","b": 1}\n'

    def test_single_trailing_newline(self):
        text = canonical_json(_payload_a())
        assert text.endswith("\n")
        assert not text.endswith("\n\n")


class TestSeal:
    def test_sha_deterministic_across_key_order(self, tmp_path):
        sha1 = seal(_payload_a(), tmp_path / "s1.json")
        sha2 = seal(_payload_a_shuffled(), tmp_path / "s2.json")
        assert sha1 == sha2
        assert len(sha1) == 64

    def test_seal_sha_matches_file_bytes(self, tmp_path):
        path = tmp_path / "s.json"
        sha = seal(_payload_a(), path)
        assert sha == sha256_of(path)
        assert sha == hashlib.sha256(path.read_bytes()).hexdigest()

    def test_reseal_same_payload_idempotent(self, tmp_path):
        path = tmp_path / "s.json"
        sha1 = seal(_payload_a(), path)
        before = path.read_bytes()
        sha2 = seal(_payload_a_shuffled(), path)
        assert sha1 == sha2
        assert path.read_bytes() == before

    def test_reseal_different_payload_rejected(self, tmp_path):
        path = tmp_path / "s.json"
        seal(_payload_a(), path)
        before = path.read_bytes()
        with pytest.raises(SealViolation):
            seal({"tampered": True}, path)
        assert path.read_bytes() == before

    def test_verify_seal_ok_then_mismatch(self, tmp_path):
        path = tmp_path / "s.json"
        sha = seal(_payload_a(), path)
        verify_seal(path, sha)
        with pytest.raises(SealViolation):
            verify_seal(path, "0" * 64)

    def test_verify_seal_detects_file_tampering(self, tmp_path):
        path = tmp_path / "s.json"
        sha = seal(_payload_a(), path)
        path.write_bytes(path.read_bytes() + b" ")
        with pytest.raises(SealViolation):
            verify_seal(path, sha)


class TestTrialsLedger:
    def test_append_and_total_with_program_filter(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        append_trials(ledger, program="P1", batch="b1", n=10, now=NOW)
        append_trials(ledger, program="P2", batch="b2", n=5, now=NOW)
        append_trials(ledger, program="P1", batch="b3", n=7, now=NOW, meta={"k": 1})
        assert total_trials(ledger) == 22
        assert total_trials(ledger, "P1") == 17
        assert total_trials(ledger, "P2") == 5
        assert total_trials(ledger, "P3") == 0

    def test_total_on_missing_ledger_is_zero(self, tmp_path):
        assert total_trials(tmp_path / "none.jsonl") == 0

    def test_invalid_program_rejected(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        with pytest.raises(ValueError):
            append_trials(ledger, program="P4", batch="b", n=1, now=NOW)
        assert not ledger.exists()

    def test_negative_n_rejected(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        with pytest.raises(ValueError):
            append_trials(ledger, program="P1", batch="b", n=-1, now=NOW)

    def test_append_only_preserves_first_line(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        mapped = registry._legacy_archive_ledger_path(ledger)
        append_trials(ledger, program="P1", batch="first", n=3, now=NOW)
        first_bytes = mapped.read_bytes()
        append_trials(ledger, program="P5", batch="second", n=4, now=NOW)
        data = mapped.read_bytes()
        assert data.startswith(first_bytes)
        assert not ledger.exists()
        lines = data.decode("utf-8").splitlines()
        assert len(lines) == 2
        rec0 = json.loads(lines[0])
        assert rec0["batch"] == "first"
        assert rec0["n"] == 3
        assert rec0["program"] == "P1"

    def test_now_injection_reflected(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        append_trials(
            ledger,
            program="P3",
            batch="b",
            n=1,
            now=dt.datetime(2031, 1, 2, 3, 4, 5),
        )
        mapped = registry._legacy_archive_ledger_path(ledger)
        rec = json.loads(mapped.read_text(encoding="utf-8").splitlines()[0])
        assert rec["ts"] == "2031-01-02T03:04:05"
        assert rec["program"] == "P3"
        assert rec["meta"] is None

    def test_total_rejects_unknown_program_filter(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        append_trials(ledger, program="P1", batch="b", n=1, now=NOW)
        with pytest.raises(ValueError):
            total_trials(ledger, "P9")

    def test_arbitrary_logical_path_writes_only_fixed_mapped_archive(self, tmp_path):
        logical = tmp_path.parent / "run-local" / "ledger.jsonl"
        mapped = registry._legacy_archive_ledger_path(logical)

        append_trials(logical, program="P1", batch="legacy", n=1, now=NOW)

        assert mapped.parent == tmp_path
        assert mapped.name == (
            f"{hashlib.sha256(str(logical.resolve()).encode('utf-8')).hexdigest()}.jsonl"
        )
        assert mapped.exists()
        assert not logical.exists()
        assert total_trials(logical) == 1

    def test_distinct_logical_paths_map_to_distinct_archives(self, tmp_path):
        first = tmp_path.parent / "run-one" / "ledger.jsonl"
        second = tmp_path.parent / "run-two" / "ledger.jsonl"

        append_trials(first, program="P1", batch="first", n=3, now=NOW)
        append_trials(second, program="P2", batch="second", n=4, now=NOW)

        assert (
            registry._legacy_archive_ledger_path(first)
            != registry._legacy_archive_ledger_path(second)
        )
        assert total_trials(first) == 3
        assert total_trials(second) == 4
        assert not first.exists()
        assert not second.exists()

    def test_canonical_authority_logical_path_maps_without_mutation(
        self, tmp_path, monkeypatch
    ):
        canonical = tmp_path / "authority" / "n_trials_ledger.jsonl"
        canonical.parent.mkdir()
        canonical.write_bytes(b'{"existing": "authority"}\n')
        monkeypatch.setattr(authority_ledger, "DEFAULT_LEDGER_PATH", canonical)
        before = canonical.read_bytes()

        append_trials(
            canonical.parent / "." / canonical.name,
            program="P1",
            batch="legacy",
            n=1,
            now=NOW,
        )

        mapped = registry._legacy_archive_ledger_path(canonical)
        assert mapped != canonical
        assert canonical.read_bytes() == before
        assert total_trials(canonical) == 1

    def test_logical_symlink_is_canonicalized_without_writing_through_it(self, tmp_path):
        actual = tmp_path / "actual"
        actual.mkdir()
        alias = tmp_path / "alias"
        try:
            alias.symlink_to(actual, target_is_directory=True)
        except OSError as error:
            pytest.skip(f"symlink unavailable: {error}")

        append_trials(alias / "ledger.jsonl", program="P1", batch="legacy", n=1, now=NOW)

        assert (
            registry._legacy_archive_ledger_path(alias / "ledger.jsonl")
            == registry._legacy_archive_ledger_path(actual / "ledger.jsonl")
        )
        assert not (actual / "ledger.jsonl").exists()

    def test_symlinked_archive_root_rejected_before_mutation(self, tmp_path, monkeypatch):
        actual = tmp_path / "actual-root"
        actual.mkdir()
        alias = tmp_path / "alias-root"
        try:
            alias.symlink_to(actual, target_is_directory=True)
        except OSError as error:
            pytest.skip(f"symlink unavailable: {error}")
        monkeypatch.setattr(registry, "LEGACY_NON_AUTHORITATIVE_LEDGER_ROOT", alias)

        with pytest.raises(ValueError, match="root must not use a symlink"):
            append_trials(
                tmp_path / "logical.jsonl",
                program="P1",
                batch="legacy",
                n=1,
                now=NOW,
            )

        assert not tuple(actual.iterdir())

    def test_symlinked_mapped_destination_rejected_before_mutation(self, tmp_path):
        logical = tmp_path.parent / "logical.jsonl"
        mapped = registry._legacy_archive_ledger_path(logical)
        target = tmp_path / "target.jsonl"
        target.write_bytes(b"unchanged\n")
        try:
            mapped.symlink_to(target)
        except OSError as error:
            pytest.skip(f"symlink unavailable: {error}")

        with pytest.raises(ValueError, match="destination must not use a symlink"):
            append_trials(logical, program="P1", batch="legacy", n=1, now=NOW)

        assert target.read_bytes() == b"unchanged\n"
    def test_hardlinked_mapped_destination_rejected_before_mutation(self, tmp_path):
        logical = tmp_path.parent / "logical-hardlink.jsonl"
        mapped = registry._legacy_archive_ledger_path(logical)
        target = tmp_path / "target-hardlink.jsonl"
        target.write_bytes(b"unchanged\n")
        os.link(target, mapped)

        with pytest.raises(ValueError, match="destination must not use a hardlink"):
            append_trials(logical, program="P1", batch="legacy", n=1, now=NOW)
        with pytest.raises(ValueError, match="destination must not use a hardlink"):
            total_trials(logical)

        assert target.read_bytes() == b"unchanged\n"

    def test_hardlinked_authority_destination_rejected_before_mutation(
        self, tmp_path, monkeypatch
    ):
        canonical = tmp_path / "authority.jsonl"
        canonical.write_bytes(b'{"existing": "authority"}\n')
        monkeypatch.setattr(authority_ledger, "DEFAULT_LEDGER_PATH", canonical)
        logical = tmp_path.parent / "logical.jsonl"
        mapped = registry._legacy_archive_ledger_path(logical)
        os.link(canonical, mapped)

        with pytest.raises(ValueError, match="canonical authority ledger"):
            append_trials(logical, program="P1", batch="legacy", n=1, now=NOW)
        with pytest.raises(ValueError, match="canonical authority ledger"):
            total_trials(logical)

        assert canonical.read_bytes() == b'{"existing": "authority"}\n'

    def test_isolated_legacy_ledger_is_append_only_not_v2_authority(self, tmp_path):
        legacy = tmp_path / "legacy-runs" / "trial_counter.jsonl"
        mapped = registry._legacy_archive_ledger_path(legacy)
        append_trials(legacy, program="P1", batch="first", n=3, now=NOW)
        first_bytes = mapped.read_bytes()
        append_trials(legacy, program="P2", batch="second", n=4, now=NOW)

        assert mapped.read_bytes().startswith(first_bytes)
        assert not legacy.exists()
        assert total_trials(legacy) == 7
        assert registry.LEGACY_NON_AUTHORITATIVE_SCHEMA != authority_ledger.REQUIRED_KEYS
        with pytest.raises(authority_ledger.LedgerSchemaError, match="필수 키 누락"):
            authority_ledger.read_all(mapped)

class TestV2ProgramTags:
    """알파 랩 v2 additive 태그(V2M·V2F) — 기존 4태그 불변 + 신규 허용."""

    def test_v2_tags_accepted_and_filterable(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        append_trials(ledger, program="V2M", batch="mining", n=12, now=NOW)
        append_trials(ledger, program="V2F", batch="filter_ab", n=6, now=NOW)
        append_trials(ledger, program="V2M", batch="mining2", n=3, now=NOW)
        assert total_trials(ledger, "V2M") == 15
        assert total_trials(ledger, "V2F") == 6
        assert total_trials(ledger) == 21

    def test_legacy_four_tags_still_accepted(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        for tag in ("P1", "P2", "P3", "P5"):
            append_trials(ledger, program=tag, batch="b", n=1, now=NOW)
        assert total_trials(ledger) == 4
        for tag in ("P1", "P2", "P3", "P5"):
            assert total_trials(ledger, tag) == 1

    def test_allowed_set_is_exactly_ten(self):
        from alpha_lab.registry import ALLOWED_PROGRAMS

        assert ALLOWED_PROGRAMS == frozenset(
            {"P1", "P2", "P3", "P5", "V2M", "V2F", "V3M", "V3H", "V4E", "V5C"}
        )

    def test_unknown_tag_still_rejected(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        with pytest.raises(ValueError):
            append_trials(ledger, program="V2X", batch="b", n=1, now=NOW)
        with pytest.raises(ValueError):
            total_trials(tmp_path / "none.jsonl", "V3X")


class TestV3ProgramTags:
    """알파 랩 v3 additive 태그(V3M·V3H) — 기존 6태그 불변 + 신규 허용
    (preregistration_v3.json 봉인 50d3d38a — ledger.tags)."""

    def test_v3_tags_accepted_and_filterable(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        append_trials(ledger, program="V3M", batch="ev_mining", n=98, now=NOW)
        append_trials(ledger, program="V3H", batch="hillclimb", n=40, now=NOW)
        append_trials(ledger, program="V3M", batch="ev_mining2", n=5, now=NOW)
        assert total_trials(ledger, "V3M") == 103
        assert total_trials(ledger, "V3H") == 40
        assert total_trials(ledger) == 143


class TestV4ProgramTags:
    """알파 랩 v4 additive 태그(V4E=레짐-적응 챔피언 앙상블 엔진 시행) — 기존 8태그
    불변 + 신규 허용(preregistration_v4.json 봉인 87821aaa... — ledger.tags)."""

    def test_v4_tag_accepted_and_filterable(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        append_trials(ledger, program="V4E", batch="r0_discovery_chunk1", n=3, now=NOW)
        append_trials(ledger, program="V4E", batch="r0_discovery_chunk2", n=2, now=NOW)
        assert total_trials(ledger, "V4E") == 5
        assert total_trials(ledger) == 5
