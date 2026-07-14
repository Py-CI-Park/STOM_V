"""CL-R02 불변 증거 계약(evidence contract) 단위 테스트.

5개 frozen dataclass(CandidatePassport / FeedbackEnvelope / FeedbackConsumption /
EvaluationManifest / RunReceipt)의 구성/직렬화(canonical_json)/복원(round-trip)/
해시 결정성(cross-process 포함)/불변 컬렉션/경계 검증(reject)을 검증한다.

design spec: docs/research/condition_research/generated_conditions/
lattice_v3_design_20260709/lattice_v3_design_spec_20260709.md §7-8
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from types import MappingProxyType
import json
import os
import subprocess
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.controller.evidence_contract import (  # noqa: E402
    CANDIDATE_PASSPORT_SCHEMA,
    EVALUATION_MANIFEST_SCHEMA,
    FEEDBACK_CONSUMPTION_SCHEMA,
    FEEDBACK_ENVELOPE_SCHEMA,
    ID_PREFIX_CANDIDATE,
    ID_PREFIX_CANDIDATE_PASSPORT,
    ID_PREFIX_EVALUATION_MANIFEST,
    ID_PREFIX_FEEDBACK_CONSUMPTION,
    ID_PREFIX_FEEDBACK_ENVELOPE,
    ID_PREFIX_RENDERED_PROMPT,
    ID_PREFIX_RUN_RECEIPT,
    OUTCOME_GO,
    OUTCOME_INDETERMINATE_EXTERNAL_EFFECT,
    OUTCOME_NO_GO,
    RUN_RECEIPT_SCHEMA,
    CandidateMode,
    CandidatePassport,
    EvaluationManifest,
    FeedbackConsumption,
    FeedbackEnvelope,
    FeedbackSide,
    RunReceipt,
    canonical_json,
    compute_candidate_id,
    compute_passport_id,
    compute_rendered_prompt_id,
    content_sha256,
    sha256_hex,
    text_sha256,
)


def _sha(payload: str = "x") -> str:
    return sha256_hex(payload)


def _now() -> str:
    return "2026-07-11T00:00:00Z"


def _candidate_id() -> str:
    return compute_candidate_id(_sha("buy"), _sha("sell"), "min_primary", "min")


def _passport_id(run_id="run-1", round_no=0, gen_no=0, slot_no=0) -> str:
    return compute_passport_id(run_id, round_no, gen_no, slot_no)


def _manifest_id() -> str:
    return f"{ID_PREFIX_EVALUATION_MANIFEST}{_sha('manifest')}"


def make_passport(**overrides) -> CandidatePassport:
    kwargs = dict(
        schema=CANDIDATE_PASSPORT_SCHEMA,
        passport_id=_passport_id(),
        candidate_id=_candidate_id(),
        run_id="run-1",
        round_no=0,
        gen_no=0,
        slot_no=0,
        parent_passport_id=None,
        mode=CandidateMode.SEED.value,
        lane="min",
        family="breakout",
        timeframe="min",
        buy_strategy_name="BuyA",
        sell_strategy_name="SellA",
        buy_sha256=_sha("buy"),
        sell_sha256=_sha("sell"),
        ast_fingerprint="ast-fp-1",
        rowset_fingerprint="rowset-fp-1",
        evidence_ids=("ev-1", "ev-2"),
        threshold_provenance={"source": "seed", "value": 1},
        manifest_id=_manifest_id(),
        created_at=_now(),
    )
    kwargs.update(overrides)
    return CandidatePassport(**kwargs)


def make_feedback(**overrides) -> FeedbackEnvelope:
    rendered_text = "buy leg underperformed on segment X"
    kwargs = dict(
        schema=FEEDBACK_ENVELOPE_SCHEMA,
        feedback_id=f"{ID_PREFIX_FEEDBACK_ENVELOPE}{_sha('feedback')}",
        source_passport_id=_passport_id(),
        autopsy_kind="buy_autopsy",
        side=FeedbackSide.BUY.value,
        source_result_sha256=_sha("result"),
        directives=("tighten_entry", "widen_stop"),
        rendered_text=rendered_text,
        rendered_sha256=text_sha256(rendered_text),
        created_at=_now(),
    )
    kwargs.update(overrides)
    return FeedbackEnvelope(**kwargs)


def make_consumption(**overrides) -> FeedbackConsumption:
    kwargs = dict(
        schema=FEEDBACK_CONSUMPTION_SCHEMA,
        consumption_id=f"{ID_PREFIX_FEEDBACK_CONSUMPTION}{_sha('consumption')}",
        feedback_id=f"{ID_PREFIX_FEEDBACK_ENVELOPE}{_sha('feedback')}",
        prompt_id="prompt-1",
        target_passport_id=_passport_id(run_id="run-1", round_no=1),
        created_at=_now(),
    )
    kwargs.update(overrides)
    return FeedbackConsumption(**kwargs)


def make_manifest(**overrides) -> EvaluationManifest:
    kwargs = dict(
        schema=EVALUATION_MANIFEST_SCHEMA,
        manifest_id=_manifest_id(),
        run_id="run-1",
        profile="official_replay_v1_20260702",
        data="stock_min_back",
        universe="stock",
        methodology="min_primary",
        timeframe="min",
        scope="single_stock",
        session={"start_time": 90000, "end_time": 152800},
        period={"start_date": 20260101, "end_date": 20260630},
        capital=5000000,
        cost="engine_builtin",
        fill="engine_builtin_hoga_sweep",
        role="train",
        code_hash=_sha("code"),
        config_hash=_sha("config"),
        created_at=_now(),
    )
    kwargs.update(overrides)
    return EvaluationManifest(**kwargs)


def make_receipt(**overrides) -> RunReceipt:
    kwargs = dict(
        schema=RUN_RECEIPT_SCHEMA,
        receipt_id=f"{ID_PREFIX_RUN_RECEIPT}{_sha('receipt')}",
        run_id="run-1",
        phase_id="CL-R07",
        outcome="go",
        stop_reason=None,
        budget_counters={"provider_calls": 1, "official_evaluations": 4},
        predecessor_ids=("prev-receipt-1",),
        artifact_hashes={"ledger": _sha("ledger"), "manifest": _sha("manifest")},
        created_at=_now(),
    )
    kwargs.update(overrides)
    return RunReceipt(**kwargs)


# ---------------------------------------------------------------------
# construct / serialize / round-trip / hash — all five types
# ---------------------------------------------------------------------

ALL_FACTORIES = [make_passport, make_feedback, make_consumption, make_manifest, make_receipt]


@pytest.mark.parametrize("factory", ALL_FACTORIES)
def test_construct_serialize_roundtrip_hash(factory):
    instance = factory()
    payload = instance.to_dict()
    text = canonical_json(payload)
    assert isinstance(text, str)
    restored = type(instance).from_dict(json.loads(text))
    assert restored == instance
    sha = content_sha256(instance)
    assert len(sha) == 64
    assert all(ch in "0123456789abcdef" for ch in sha)
    assert content_sha256(restored) == sha


def test_candidate_id_stable_across_runs_same_body_and_methodology():
    a = compute_candidate_id(_sha("buy"), _sha("sell"), "min_primary", "min")
    b = compute_candidate_id(_sha("buy"), _sha("sell"), "min_primary", "min")
    assert a == b
    assert a.startswith(ID_PREFIX_CANDIDATE)


def test_passport_id_distinct_per_proposal_even_for_same_candidate_id():
    candidate_id = _candidate_id()
    p1 = make_passport(candidate_id=candidate_id, passport_id=_passport_id(round_no=0))
    p2 = make_passport(candidate_id=candidate_id, passport_id=_passport_id(round_no=1))
    assert p1.candidate_id == p2.candidate_id
    assert p1.passport_id != p2.passport_id
    assert p1.passport_id.startswith(ID_PREFIX_CANDIDATE_PASSPORT)


# ---------------------------------------------------------------------
# cross-process determinism (golden SHA)
# ---------------------------------------------------------------------

def test_cross_process_hash_determinism_for_receipt():
    receipt = make_receipt()
    in_process_sha = content_sha256(receipt)

    script = (
        "import sys; sys.path.insert(0, r'{root}');"
        "import ai_strategy_loop.bootstrap;"
        "from ai_strategy_loop.controller.evidence_contract import RunReceipt, content_sha256;"
        "import json;"
        "data = json.loads(sys.argv[1]);"
        "receipt = RunReceipt.from_dict(data);"
        "print(content_sha256(receipt))"
    ).format(root=PROJECT_ROOT)

    result = subprocess.run(
        [sys.executable, "-c", script, canonical_json(receipt.to_dict())],
        capture_output=True,
        text=True,
        check=True,
    )
    cross_process_sha = result.stdout.strip()
    assert cross_process_sha == in_process_sha
    assert len(cross_process_sha) == 64


def test_cross_process_hash_determinism_for_passport():
    passport = make_passport()
    in_process_sha = content_sha256(passport)

    script = (
        "import sys; sys.path.insert(0, r'{root}');"
        "import ai_strategy_loop.bootstrap;"
        "from ai_strategy_loop.controller.evidence_contract import CandidatePassport, content_sha256;"
        "import json;"
        "data = json.loads(sys.argv[1]);"
        "passport = CandidatePassport.from_dict(data);"
        "print(content_sha256(passport))"
    ).format(root=PROJECT_ROOT)

    result = subprocess.run(
        [sys.executable, "-c", script, canonical_json(passport.to_dict())],
        capture_output=True,
        text=True,
        check=True,
    )
    cross_process_sha = result.stdout.strip()
    assert cross_process_sha == in_process_sha


# ---------------------------------------------------------------------
# CRLF/CR vs LF and NFC-equivalent unicode hash identically
# ---------------------------------------------------------------------

def test_crlf_and_lf_hash_identically():
    lf = make_feedback(
        rendered_text="line1\nline2",
        rendered_sha256=text_sha256("line1\nline2"),
    )
    crlf = make_feedback(
        rendered_text="line1\r\nline2",
        rendered_sha256=text_sha256("line1\r\nline2"),
    )
    lone_cr = make_feedback(
        rendered_text="line1\rline2",
        rendered_sha256=text_sha256("line1\rline2"),
    )
    assert content_sha256(lf) == content_sha256(crlf) == content_sha256(lone_cr)


def test_nfc_equivalent_unicode_hashes_identically():
    # 'e' + combining acute (NFD) vs precomposed 'e' (NFC) — same visible glyph.
    nfd_text = "caf\u0065\u0301"
    nfc_text = "caf\u00e9"
    assert nfd_text != nfc_text
    first = make_feedback(rendered_text=nfd_text, rendered_sha256=text_sha256(nfd_text))
    second = make_feedback(rendered_text=nfc_text, rendered_sha256=text_sha256(nfc_text))
    assert content_sha256(first) == content_sha256(second)
    assert text_sha256(nfd_text) == text_sha256(nfc_text)


# ---------------------------------------------------------------------
# immutable collections / frozen dataclasses
# ---------------------------------------------------------------------

def test_evidence_ids_stored_as_tuple_and_not_mutable():
    passport = make_passport(evidence_ids=["ev-1", "ev-2"])
    assert isinstance(passport.evidence_ids, tuple)
    with pytest.raises(AttributeError):
        passport.evidence_ids.append("ev-3")  # tuples have no append


def test_threshold_provenance_stored_as_immutable_mapping():
    passport = make_passport(threshold_provenance={"a": 1})
    assert isinstance(passport.threshold_provenance, MappingProxyType)
    with pytest.raises(TypeError):
        passport.threshold_provenance["a"] = 2  # type: ignore[index]


def test_mutating_input_after_construction_does_not_affect_stored_value():
    source_ids = ["ev-1", "ev-2"]
    source_provenance = {"a": 1}
    passport = make_passport(evidence_ids=source_ids, threshold_provenance=source_provenance)
    source_ids.append("ev-3")
    source_provenance["a"] = 999
    source_provenance["b"] = 2
    assert passport.evidence_ids == ("ev-1", "ev-2")
    assert dict(passport.threshold_provenance) == {"a": 1}


@pytest.mark.parametrize("factory", ALL_FACTORIES)
def test_dataclass_is_frozen(factory):
    instance = factory()
    field_name = next(iter(instance.to_dict()))
    with pytest.raises(FrozenInstanceError):
        setattr(instance, field_name, "mutated")


def test_budget_counters_and_artifact_hashes_are_immutable_mappings():
    receipt = make_receipt()
    assert isinstance(receipt.budget_counters, MappingProxyType)
    assert isinstance(receipt.artifact_hashes, MappingProxyType)
    assert isinstance(receipt.predecessor_ids, tuple)
    with pytest.raises(TypeError):
        receipt.budget_counters["provider_calls"] = 99  # type: ignore[index]


# ---------------------------------------------------------------------
# parent/root candidates and mode enum
# ---------------------------------------------------------------------

def test_seed_root_passport_has_no_parent():
    root = make_passport(parent_passport_id=None, mode=CandidateMode.SEED.value)
    assert root.parent_passport_id is None
    assert root.mode == "seed"


@pytest.mark.parametrize("mode", ["seed", "fresh", "refine"])
def test_all_modes_accepted(mode):
    passport = make_passport(mode=mode, parent_passport_id=(_passport_id() if mode != "seed" else None))
    assert passport.mode == mode


def test_refine_passport_references_parent():
    parent_id = _passport_id(round_no=0)
    child = make_passport(mode=CandidateMode.REFINE.value, parent_passport_id=parent_id)
    assert child.parent_passport_id == parent_id


def test_unknown_mode_rejected():
    with pytest.raises(ValueError):
        make_passport(mode="mutant")


@pytest.mark.parametrize("side", ["buy", "sell", "risk", "error", "segment", "feature", "hypothesis"])
def test_all_feedback_sides_accepted(side):
    feedback = make_feedback(side=side)
    assert feedback.side == side


def test_unknown_side_rejected():
    with pytest.raises(ValueError):
        make_feedback(side="not_a_side")


# ---------------------------------------------------------------------
# boundary rejects
# ---------------------------------------------------------------------

def test_rejects_nan_in_manifest_capital():
    with pytest.raises(ValueError):
        make_manifest(capital=float("nan"))


def test_rejects_infinity_in_manifest_capital():
    with pytest.raises(ValueError):
        make_manifest(capital=float("inf"))


def test_rejects_nan_nested_in_budget_counters():
    with pytest.raises(ValueError):
        make_receipt(budget_counters={"provider_calls": float("nan")})


def test_rejects_missing_buy_sha256():
    with pytest.raises(ValueError):
        make_passport(buy_sha256="")


def test_rejects_non_hex_sha():
    with pytest.raises(ValueError):
        make_passport(buy_sha256="not-a-valid-sha256-value-------------------------------------")


def test_rejects_short_sha():
    with pytest.raises(ValueError):
        make_passport(sell_sha256=_sha("sell")[:63])


def test_rejects_naive_timestamp():
    with pytest.raises(ValueError):
        make_passport(created_at="2026-07-11T00:00:00")


def test_rejects_local_offset_timestamp():
    with pytest.raises(ValueError):
        make_passport(created_at="2026-07-11T09:00:00+09:00")


def test_accepts_explicit_utc_offset_timestamp():
    passport = make_passport(created_at="2026-07-11T00:00:00+00:00")
    assert passport.created_at == "2026-07-11T00:00:00+00:00"


def test_rejects_mutable_set_for_sequence_field():
    with pytest.raises(ValueError):
        make_passport(evidence_ids={"ev-1", "ev-2"})


def test_rejects_bad_id_prefix():
    with pytest.raises(ValueError):
        make_passport(passport_id="wrong_prefix_" + _sha("x"))


def test_rejects_wrong_id_family():
    with pytest.raises(ValueError):
        make_receipt(receipt_id=f"{ID_PREFIX_CANDIDATE_PASSPORT}{_sha('receipt')}")


def test_feedback_rendered_sha_must_match_rendered_text():
    with pytest.raises(ValueError):
        make_feedback(rendered_text="actual text", rendered_sha256=_sha("different text"))


def test_manifest_rejects_missing_code_hash():
    with pytest.raises(ValueError):
        make_manifest(code_hash="")


def test_receipt_rejects_non_mapping_budget_counters():
    with pytest.raises(ValueError):
        make_receipt(budget_counters=["not", "a", "mapping"])


# ---------------------------------------------------------------------
# DR-03 — real content-addressed prompt FK (compute_rendered_prompt_id) +
#   fail-closed certification outcome vocabulary.
# ---------------------------------------------------------------------

def test_rendered_prompt_id_deterministic_for_same_content():
    a = compute_rendered_prompt_id("buy", 1, _sha("system"), _sha("user"))
    b = compute_rendered_prompt_id("buy", 1, _sha("system"), _sha("user"))
    assert a == b
    assert a.startswith(ID_PREFIX_RENDERED_PROMPT)


def test_rendered_prompt_id_independent_of_run_and_gen_coordinates():
    # Same content -> same id regardless of caller-side run_id/gen_no (content
    # identity, not run/gen identity) — this is what makes the id verifiable
    # across an interrupted+resumed run (DR-03 acceptance #5).
    a = compute_rendered_prompt_id("buy", 1, _sha("system"), _sha("user"))
    b = compute_rendered_prompt_id("buy", 1, _sha("system"), _sha("user"))
    assert a == b


def test_rendered_prompt_id_distinguishes_kind_attempt_and_content():
    base = compute_rendered_prompt_id("buy", 1, _sha("system"), _sha("user"))
    diff_kind = compute_rendered_prompt_id("sell", 1, _sha("system"), _sha("user"))
    diff_attempt = compute_rendered_prompt_id("buy", 2, _sha("system"), _sha("user"))
    diff_user = compute_rendered_prompt_id("buy", 1, _sha("system"), _sha("other"))
    assert len({base, diff_kind, diff_attempt, diff_user}) == 4


def test_rendered_prompt_id_rejects_non_sha256_inputs():
    with pytest.raises(ValueError):
        compute_rendered_prompt_id("buy", 1, "not-a-sha", _sha("user"))


def test_rendered_prompt_id_rejects_negative_attempt():
    with pytest.raises(ValueError):
        compute_rendered_prompt_id("buy", -1, _sha("system"), _sha("user"))


def test_outcome_labels_are_distinct_nonempty_strings():
    labels = {OUTCOME_GO, OUTCOME_NO_GO, OUTCOME_INDETERMINATE_EXTERNAL_EFFECT}
    assert len(labels) == 3
    for label in labels:
        assert isinstance(label, str) and label


def test_run_receipt_accepts_indeterminate_external_effect_outcome():
    # RunReceipt.outcome stays a free nonempty string (v1 contract unchanged) —
    # the new label is just additive vocabulary, not a new validated enum.
    receipt = make_receipt(outcome=OUTCOME_INDETERMINATE_EXTERNAL_EFFECT, stop_reason="evidence_io_failure")
    assert receipt.outcome == OUTCOME_INDETERMINATE_EXTERNAL_EFFECT
    assert receipt.stop_reason == "evidence_io_failure"
