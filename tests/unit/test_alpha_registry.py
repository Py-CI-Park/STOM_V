"""alpha_lab.registry 단위 테스트 — 봉인 결정성·멱등·위반 검출 + n_trials 원장.

실DB 불필요(전부 tmp_path 합성). 실행: python -m pytest tests/unit/test_alpha_registry.py -q
"""

import datetime as dt
import hashlib
import json

import pytest

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
        append_trials(ledger, program="P1", batch="first", n=3, now=NOW)
        first_bytes = ledger.read_bytes()
        append_trials(ledger, program="P5", batch="second", n=4, now=NOW)
        data = ledger.read_bytes()
        assert data.startswith(first_bytes)
        lines = data.decode("utf-8").splitlines()
        assert len(lines) == 2
        rec0 = json.loads(lines[0])
        assert rec0["batch"] == "first"
        assert rec0["n"] == 3
        assert rec0["program"] == "P1"

    def test_now_injection_reflected(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        injected = dt.datetime(2031, 1, 2, 3, 4, 5)
        append_trials(ledger, program="P3", batch="b", n=1, now=injected)
        rec = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
        assert rec["ts"] == "2031-01-02T03:04:05"
        assert rec["program"] == "P3"
        assert rec["meta"] is None

    def test_total_rejects_unknown_program_filter(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        append_trials(ledger, program="P1", batch="b", n=1, now=NOW)
        with pytest.raises(ValueError):
            total_trials(ledger, "P9")


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

    def test_allowed_set_is_exactly_six(self):
        from alpha_lab.registry import ALLOWED_PROGRAMS

        assert ALLOWED_PROGRAMS == frozenset(
            {"P1", "P2", "P3", "P5", "V2M", "V2F"}
        )

    def test_unknown_tag_still_rejected(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        with pytest.raises(ValueError):
            append_trials(ledger, program="V2X", batch="b", n=1, now=NOW)
        with pytest.raises(ValueError):
            total_trials(tmp_path / "none.jsonl", "V3M")
