"""LLM 다중가설 후보팩 생산자 (T3.1, 연구 레인 전용).

역할:
  - brain.prompt 의 repair/discovery 연구 프롬프트 빌더와 strict 응답 검증기를
    **읽기 전용 import** 로만 소비해, cli/condition_generator.py 의
    validate_multi_hypothesis_candidate_pack 을 통과하는 research_candidate_pack
    dict 를 조립한다 (이 모듈은 cli.* 를 import 하지 않는다).
  - provider 는 Callable[[list[dict]], str] 로 주입된다. 이 모듈에는 LLM
    실호출 코드가 없다 (연구 레인 규약).
  - provider 예외는 terminal 이다 (brain.generator 의 provider 실패 규약과
    동일 — 재시도 없음). candidate_pack=None + 실패 사유 리스트를 돌려주면
    cli.research_loop 의 결정론 폴백(mark_diagnostic_fallback, prompt credit 0)
    이 자연 발동한다. 폴백 자체는 이 모듈 범위 밖이다.
  - 레인별 요구 수 미달 시 레인당 최대 RETRY_MAX_PER_LANE(2)회 추가 재시도하고,
    그래도 미달이면 partial pack 의 'shortfall' 필드에 정직하게 기록한다.
  - 모든 provider 호출에 대해 prompt.build_research_prompt_receipt 로
    결정론적 프롬프트 영수증을 만든다 (모듈 내 시계 없음 — 같은 입력과 같은
    응답이면 팩/영수증이 바이트 단위로 동일하다).

안전 규약:
  - 후보/팩은 화이트리스트 필드로만 조립한다 — LLM metadata 를 그대로 병합하지
    않는다 (권한 키 밀반입 차단).
  - 팩에 내장되는 영수증의 strict_response_validation 은 원문 metadata 를 뺀
    요약본이다. 거부된 응답의 metadata 에 권한 키(can_promote 등)가 있어도
    팩 레벨 authority 스캔(pack_authority_smuggling)이 오염되지 않는다.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Mapping, Optional

from .prompt import (
    DISCOVERY_RESEARCH_PROMPT_VERSION,
    REPAIR_RESEARCH_PROMPT_VERSION,
    build_discovery_research_messages,
    build_repair_research_messages,
    build_research_prompt_receipt,
    estimate_research_context_pack_budget,
    validate_research_candidate_response,
)
from .candidate_output_contract import (
    BUY_EXCLUSION_EXPR,
    RESEARCH_FILTER_CONSUMER,
    canonical_body_sha256,
    validate_candidate_payload,
)

PACK_PRODUCER_VERSION = "pack_producer_v1"
CANDIDATE_PACK_VERSION = "multi_hypothesis_candidate_pack_v1"
DEFAULT_LANES = {"repair": 2, "discovery": 2}
RETRY_MAX_PER_LANE = 2

_RESEARCH_LANES = ("repair", "discovery")
_LANE_PROMPT_VERSIONS = {
    "repair": REPAIR_RESEARCH_PROMPT_VERSION,
    "discovery": DISCOVERY_RESEARCH_PROMPT_VERSION,
}
_VALID_KINDS = ("buy", "sell")
_VALID_TIMEFRAMES = ("min", "tick")
_NOVELTY_AXIS_KEYS = ("coverage_regime", "feature_family", "market_segment")
_AUTHORITY_NOTE = "research_only_no_export_live_or_final_promotion"
# 팩 내장 영수증에 남기는 strict 검증 요약 필드 (원문 metadata 제외).
_VALIDATION_SUMMARY_KEYS = (
    "schema_version",
    "valid",
    "lane",
    "prompt_version",
    "kind",
    "timeframe",
    "code_block_count",
    "metadata_present",
    "metadata_block_count",
    "metadata_json_safe",
    "failure_reason",
    "authority",
)

__all__ = [
    "PACK_PRODUCER_VERSION",
    "CANDIDATE_PACK_VERSION",
    "DEFAULT_LANES",
    "RETRY_MAX_PER_LANE",
    "produce_candidate_pack",
    "produce_candidate_pack_result",
]


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _parent_side(context: Mapping[str, Any], side: str) -> dict:
    """context 의 parents.{side} 또는 flat parent_{side}_* 키에서 부모 전문을 뽑는다."""

    parents = context.get("parents") if isinstance(context.get("parents"), Mapping) else {}
    parent = parents.get(side) if isinstance(parents.get(side), Mapping) else {}
    code = str(parent.get("code") or context.get(f"parent_{side}_code") or "")
    parent_id = str(parent.get("id") or context.get(f"parent_{side}_id") or "")
    return {
        "role": side,
        "id": parent_id,
        "code": code,
        "sha256": _sha256_text(code) if code else "",
    }


def _normalized_lanes(lanes: Optional[Mapping[str, int]]) -> tuple[dict, list[str]]:
    source = DEFAULT_LANES if lanes is None else lanes
    if not isinstance(source, Mapping):
        return {lane: 0 for lane in _RESEARCH_LANES}, ["lanes_not_object"]
    reasons: list[str] = []
    counts: dict[str, int] = {}
    for name, value in source.items():
        if name not in _RESEARCH_LANES:
            reasons.append(f"unknown_lane:{name}")
            continue
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            reasons.append(f"invalid_lane_count:{name}")
            continue
        counts[str(name)] = int(value)
    normalized = {lane: counts.get(lane, 0) for lane in _RESEARCH_LANES}
    if not reasons and sum(normalized.values()) <= 0:
        reasons.append("no_candidates_requested")
    return normalized, reasons


def _input_failure_reasons(
    context: Any,
    lane_counts: Mapping[str, int],
    axis_prompt_lines: Any,
) -> list[str]:
    if not isinstance(context, Mapping):
        return ["context_not_object"]
    reasons: list[str] = []
    if (context.get("kind") or "buy") not in _VALID_KINDS:
        reasons.append("invalid_kind")
    if context.get("timeframe") not in _VALID_TIMEFRAMES:
        reasons.append("invalid_timeframe")
    if axis_prompt_lines is not None and (
        not isinstance(axis_prompt_lines, (list, tuple))
        or any(not isinstance(line, str) for line in axis_prompt_lines)
    ):
        reasons.append("invalid_axis_prompt_lines")
    if lane_counts.get("repair", 0) > 0:
        if not _parent_side(context, "buy")["code"].strip():
            reasons.append("missing_parent_buy_code")
        if not _parent_side(context, "sell")["code"].strip():
            reasons.append("missing_parent_sell_code")
        card = context.get("analysis_card")
        if not isinstance(card, Mapping):
            reasons.append("missing_analysis_card")
        else:
            if not (card.get("analysis_id") or card.get("analysis_card_id")):
                reasons.append("missing_analysis_card_id")
            if not (card.get("candidate_id") or card.get("parent_id")):
                reasons.append("missing_analysis_card_parent_reference")
    if lane_counts.get("discovery", 0) > 0:
        gap = context.get("coverage_gap")
        if not isinstance(gap, Mapping):
            reasons.append("missing_coverage_gap")
        else:
            if not (gap.get("coverage_gap_id") or gap.get("id")):
                reasons.append("missing_coverage_gap_id")
            if not gap.get("coverage_bucket_keys"):
                reasons.append("missing_coverage_bucket_keys")
        if not isinstance(context.get("novelty_context"), Mapping):
            reasons.append("missing_novelty_context")
    return reasons


def _repair_analysis_card(analysis_card: Mapping[str, Any], axis_prompt_lines: Any) -> dict:
    """axis_prompt_lines 를 분석 카드 사본에만 추가한다 (원본 불변, repair 전용).

    build_repair_research_messages 는 analysis_card 를 JSON 블록으로 그대로
    렌더하므로, 빌더 수정 없이 입력 파라미터만으로 변이축 사전확률 라인이
    repair 프롬프트의 분석 컨텍스트에 나타난다.
    """

    card = dict(analysis_card)
    if axis_prompt_lines:
        card["axis_priors"] = [str(line) for line in axis_prompt_lines]
        card["axis_priors_source"] = "axis_ledger_to_prompt_lines"
    return card


def _context_pack_trace(research_context_pack: Optional[Mapping[str, Any]]) -> dict:
    if not isinstance(research_context_pack, Mapping):
        return {"id": None, "sha256": None, "tokens": None, "full_sources": None}
    budget = research_context_pack.get("budget")
    budget = budget if isinstance(budget, Mapping) else {}
    sha = budget.get("rendered_sha256")
    tokens = budget.get("estimated_tokens")
    if not sha:
        estimated = estimate_research_context_pack_budget(research_context_pack)
        sha = estimated["rendered_sha256"]
        tokens = estimated["estimated_tokens"]
    stom_sources = research_context_pack.get("stom_sources")
    stom_sources = stom_sources if isinstance(stom_sources, Mapping) else {}
    full_sources = stom_sources.get("all_available_sources_included")
    return {
        "id": research_context_pack.get("context_pack_id") or None,
        "sha256": sha,
        "tokens": int(tokens) if tokens is not None else None,
        "full_sources": bool(full_sources) if full_sources is not None else None,
    }


def _build_lane_messages(
    lane: str,
    *,
    kind: str,
    timeframe: str,
    parents: Mapping[str, Mapping[str, str]],
    analysis_card: Mapping[str, Any],
    coverage_gap: Mapping[str, Any],
    novelty_context: Mapping[str, Any],
    research_context_pack: Optional[Mapping[str, Any]],
    strict_candidate_payload_v2: bool = False,
) -> list[dict]:
    if lane == "repair":
        # repair 대상 부모 전문은 요청 kind 쪽 코드다 — sell repair 에
        # buy 부모를 수리 대상으로 내장하면 안 된다.
        return build_repair_research_messages(
            kind,
            timeframe=timeframe,
            parent_code=parents[kind]["code"],
            analysis_card=analysis_card,
            research_context_pack=research_context_pack,
            strict_candidate_payload_v2=strict_candidate_payload_v2,
        )
    return build_discovery_research_messages(
        kind,
        timeframe=timeframe,
        coverage_gap=coverage_gap,
        novelty_context=novelty_context,
        research_context_pack=research_context_pack,
        strict_candidate_payload_v2=strict_candidate_payload_v2,
    )


def _derived_novelty(metadata: Mapping[str, Any], novelty_context: Mapping[str, Any]) -> dict:
    """novelty 축을 metadata → novelty_context 순으로 화이트리스트 키만 복사한다."""

    for source in (metadata.get("novelty"), novelty_context):
        if isinstance(source, Mapping):
            axes = {key: source[key] for key in _NOVELTY_AXIS_KEYS if source.get(key)}
            if axes:
                return axes
    return {}


def _mutation_axis(
    lane: str,
    metadata: Mapping[str, Any],
    analysis_card: Mapping[str, Any],
    novelty: Mapping[str, Any],
) -> str:
    axis = metadata.get("mutation_axis")
    if axis:
        return str(axis)
    if lane == "repair":
        fallback = analysis_card.get("mutation_axis") if isinstance(analysis_card, Mapping) else None
        return str(fallback) if fallback else ""
    for key in _NOVELTY_AXIS_KEYS:
        if novelty.get(key):
            return f"novelty:{key}={novelty[key]}"
    return ""


def _unique_hypothesis_id(
    lane: str,
    metadata: Mapping[str, Any],
    expression: str,
    seen_hypothesis_ids: set[str],
) -> str:
    raw = str(metadata.get("hypothesis_id") or "").strip()
    if raw and raw not in seen_hypothesis_ids:
        return raw
    # expression 은 팩 내 유일하므로 파생 id 도 유일·결정론적이다.
    return f"{lane}_h_{_sha256_text(f'{lane}|{expression}')[:12]}"


def _assemble_candidate(
    lane: str,
    validation: Mapping[str, Any],
    *,
    parents: Mapping[str, Mapping[str, str]],
    analysis_card: Mapping[str, Any],
    novelty_context: Mapping[str, Any],
    kind: str,
    timeframe: str,
    seen_expressions: set[str],
    seen_hypothesis_ids: set[str],
) -> tuple[Optional[dict], list[str]]:
    """strict 검증을 통과한 응답에서 후보 dict 를 화이트리스트로 조립한다."""

    metadata = validation.get("metadata") or {}
    expression = str(validation.get("code") or "").strip()
    failures: list[str] = []
    if not expression:
        failures.append("empty_candidate_code_block")
    elif expression in seen_expressions:
        failures.append("duplicate_expression")
    novelty = _derived_novelty(metadata, novelty_context) if lane == "discovery" else {}
    mutation_axis = _mutation_axis(lane, metadata, analysis_card, novelty)
    if not mutation_axis:
        failures.append("missing_mutation_axis")
    if lane == "repair" and metadata.get("preserves_parent_structure") is False:
        failures.append("repair_parent_structure_not_preserved")
    if lane == "discovery" and not novelty:
        failures.append("missing_discovery_novelty_axis")
    if failures:
        return None, failures

    intended = str(metadata.get("intended_hypothesis") or "")
    expected_effect = str(metadata.get("expected_effect") or "")
    if not expected_effect:
        expected_effect = f"intended_hypothesis 기반 기대 효과: {intended}"
    candidate: dict[str, Any] = {
        "lane": lane,
        "expression": expression,
        "hypothesis_id": _unique_hypothesis_id(lane, metadata, expression, seen_hypothesis_ids),
        "intended_hypothesis": intended,
        "mutation_axis": mutation_axis,
        "expected_effect": expected_effect,
        "risk_note": str(metadata.get("risk_note") or ""),
        "kind": kind,
        "timeframe": timeframe,
        "prompt_version": _LANE_PROMPT_VERSIONS[lane],
    }
    if lane == "repair":
        parent_buy_id = str(metadata.get("parent_id") or parents["buy"]["id"])
        candidate.update({
            "parent_id": parent_buy_id,
            "parent_buy_id": parent_buy_id,
            "parent_sell_id": parents["sell"]["id"],
            "parent_buy_code": parents["buy"]["code"],
            "parent_sell_code": parents["sell"]["code"],
            "analysis_card_id": str(metadata.get("analysis_card_id") or ""),
            "preserves_parent_structure": bool(metadata.get("preserves_parent_structure", True)),
        })
    else:
        coverage = metadata.get("discovery_target_coverage")
        coverage_keys = list(coverage) if isinstance(coverage, (list, tuple)) else [str(coverage)]
        candidate.update({
            "coverage_gap_id": str(metadata.get("coverage_gap_id") or ""),
            "coverage_bucket_keys": coverage_keys,
            "discovery_target_coverage": list(coverage_keys),
            "novelty_rationale": str(metadata.get("novelty_rationale") or ""),
            "novelty": novelty,
        })
    return candidate, []


def _fill_lane(
    lane: str,
    required: int,
    *,
    provider: Callable[[list[dict]], str],
    kind: str,
    timeframe: str,
    parents: Mapping[str, Mapping[str, str]],
    analysis_card: Mapping[str, Any],
    coverage_gap: Mapping[str, Any],
    novelty_context: Mapping[str, Any],
    research_context_pack: Optional[Mapping[str, Any]],
    seen_expressions: set[str],
    seen_hypothesis_ids: set[str],
    retry_max: int,
    strict_candidate_payload_v2: bool = False,
) -> dict:
    """레인 하나를 채운다. provider 예외는 terminal=True 로 즉시 반환한다."""

    accepted: list[dict] = []
    records: list[dict] = []
    reasons: list[str] = []
    attempts = 0
    max_attempts = required + max(int(retry_max), 0)
    while len(accepted) < required and attempts < max_attempts:
        attempts += 1
        messages = _build_lane_messages(
            lane,
            kind=kind,
            timeframe=timeframe,
            parents=parents,
            analysis_card=analysis_card,
            coverage_gap=coverage_gap,
            novelty_context=novelty_context,
            research_context_pack=research_context_pack,
            strict_candidate_payload_v2=strict_candidate_payload_v2,
        )
        payload_budget = estimate_research_context_pack_budget(messages)
        try:
            raw = provider(messages)
        except Exception as exc:  # provider 실패는 재시도하지 않는 terminal 오류.
            reasons.append(f"{lane}_provider_exception:{type(exc).__name__}:{exc}")
            return {
                "accepted": accepted,
                "records": records,
                "failure_reasons": reasons,
                "attempts": attempts,
                "terminal": True,
            }
        response_text = raw if isinstance(raw, str) else ("" if raw is None else str(raw))
        if strict_candidate_payload_v2:
            payload_validation = validate_candidate_payload(
                response_text,
                expected_output_kind=BUY_EXCLUSION_EXPR,
                expected_side="buy",
                expected_timeframe=timeframe,
                expected_consumer=RESEARCH_FILTER_CONSUMER,
            )
            metadata = {
                "intended_hypothesis": f"{lane} buy exclusion predicate",
                "risk_note": "research filter exclusion may reduce coverage",
                "mutation_axis": str(analysis_card.get("mutation_axis") or "buy_exclusion"),
                "parent_id": str(analysis_card.get("candidate_id") or analysis_card.get("parent_id") or ""),
                "analysis_card_id": str(analysis_card.get("analysis_id") or analysis_card.get("analysis_card_id") or ""),
                "coverage_gap_id": str(coverage_gap.get("coverage_gap_id") or coverage_gap.get("id") or ""),
                "discovery_target_coverage": coverage_gap.get("coverage_bucket_keys") or [],
                "novelty_rationale": "payload-bound discovery exclusion",
                "novelty": novelty_context.get("novelty") or novelty_context,
            }
            validation = {
                "valid": payload_validation["valid"],
                "failure_reason": payload_validation["failure_reason"],
                "code": payload_validation["body"],
                "metadata": metadata,
                "schema_version": 11,
                "lane": lane,
                "prompt_version": _LANE_PROMPT_VERSIONS[lane],
                "kind": "buy",
                "timeframe": timeframe,
                "code_block_count": 0,
                "metadata_present": True,
                "metadata_block_count": 1,
                "metadata_json_safe": True,
                "authority": "candidate_payload_v2",
            }
        else:
            validation = validate_research_candidate_response(
                response_text,
                expected_lane=lane,
                expected_prompt_version=_LANE_PROMPT_VERSIONS[lane],
                expected_kind=kind,
                expected_timeframe=timeframe,
            )
        candidate: Optional[dict] = None
        extra_failures: list[str] = []
        if validation["valid"]:
            candidate, extra_failures = _assemble_candidate(
                lane,
                validation,
                parents=parents,
                analysis_card=analysis_card,
                novelty_context=novelty_context,
                kind=kind,
                timeframe=timeframe,
                seen_expressions=seen_expressions,
                seen_hypothesis_ids=seen_hypothesis_ids,
            )
            if candidate is not None and strict_candidate_payload_v2:
                candidate["candidate_payload_v2"] = {
                    "schema_version": 11,
                    "output_kind": payload_validation["output_kind"],
                    "side": payload_validation["side"],
                    "timeframe": payload_validation["timeframe"],
                    "expected_consumer": payload_validation["expected_consumer"],
                    "canonical_body_sha256": canonical_body_sha256(
                        payload_validation["body"]
                    ),
                }
        accepted_flag = candidate is not None and not extra_failures
        failure_parts = [part for part in (validation["failure_reason"], *extra_failures) if part]
        combined_failure = "|".join(dict.fromkeys(failure_parts))
        records.append({
            "lane": lane,
            "attempt": attempts,
            "slot_id": f"{lane}_slot_{attempts}",
            "validation": validation,
            "estimated_tokens": payload_budget["estimated_tokens"],
            "payload_sha256": payload_budget["rendered_sha256"],
            "accepted": accepted_flag,
            "failure_reason": combined_failure,
            "hypothesis_id": candidate["hypothesis_id"] if accepted_flag else "",
        })
        if accepted_flag:
            accepted.append(candidate)
            seen_expressions.add(candidate["expression"])
            seen_hypothesis_ids.add(candidate["hypothesis_id"])
        else:
            reasons.append(f"{lane}_attempt_{attempts}:{combined_failure or 'unknown_rejection'}")
    return {
        "accepted": accepted,
        "records": records,
        "failure_reasons": reasons,
        "attempts": attempts,
        "terminal": False,
    }


def _validation_summary(validation: Mapping[str, Any]) -> dict:
    """팩 내장용 strict 검증 요약 — 원문 metadata/code 는 제외한다 (권한 키 차단)."""

    summary = {key: validation.get(key) for key in _VALIDATION_SUMMARY_KEYS}
    code = str(validation.get("code") or "")
    summary["code_sha256"] = _sha256_text(code) if code else ""
    summary["raw_metadata_excluded"] = True
    return summary


def _receipt_for_attempt(
    record: Mapping[str, Any],
    *,
    context_trace: Mapping[str, Any],
    round_id: str,
    prompt_score: int,
    parents: Mapping[str, Mapping[str, str]],
    analysis_card: Mapping[str, Any],
    pack_id: Optional[str],
) -> dict:
    validation = record["validation"]
    metadata = validation.get("metadata") or {}
    lane = str(record["lane"])
    accepted = bool(record["accepted"])
    receipt_id = "rr_" + _sha256_text(_canonical_json({
        "round_id": round_id,
        "lane": lane,
        "attempt": record["attempt"],
        "payload_sha256": record["payload_sha256"],
    }))[:16]
    kwargs: dict[str, Any] = {
        "receipt_id": receipt_id,
        "round_id": round_id,
        "slot_id": str(record["slot_id"]),
        "lane": lane,
        "prompt_version": _LANE_PROMPT_VERSIONS[lane],
        "prompt_score": prompt_score,
        "intended_hypothesis": str(metadata.get("intended_hypothesis") or ""),
        "strict_response_validation": _validation_summary(validation),
        "context_pack_id": context_trace["id"],
        "context_pack_sha256": context_trace["sha256"],
        "candidate_pack_id": pack_id,
        "candidate_contract_id": (
            f"{pack_id}::{record['hypothesis_id']}" if accepted and pack_id else None
        ),
        "mode_authority": "research_only",
        "generation_allowed": True,
        "full_stom_sources_included": context_trace["full_sources"],
        "prompt_budget_estimated_tokens": int(record["estimated_tokens"]),
        "risk_note": str(metadata.get("risk_note") or ""),
        "output_candidate_id": str(record["hypothesis_id"]) or None,
        "failure_reason": "" if accepted else (str(record["failure_reason"]) or "invalid_response"),
        "downstream_result": "not_evaluated" if accepted else "invalid",
    }
    if lane == "repair":
        card_axis = analysis_card.get("mutation_axis") if isinstance(analysis_card, Mapping) else None
        kwargs.update({
            "parent_id": str(metadata.get("parent_id") or parents["buy"]["id"] or "") or None,
            "analysis_card_id": str(metadata.get("analysis_card_id") or "") or None,
            "parent_buy_id": parents["buy"]["id"] or None,
            "parent_sell_id": parents["sell"]["id"] or None,
            "parent_buy_code": parents["buy"]["code"],
            "parent_sell_code": parents["sell"]["code"],
            "preserves_parent_structure": bool(metadata.get("preserves_parent_structure", True)),
            "mutation_axis": str(metadata.get("mutation_axis") or card_axis or "") or None,
        })
    else:
        kwargs.update({
            "coverage_gap_id": str(metadata.get("coverage_gap_id") or "") or None,
            "discovery_target_coverage": metadata.get("discovery_target_coverage") or [],
        })
    return build_research_prompt_receipt(**kwargs)


def _error_envelope(
    failure_reasons: list[str],
    *,
    shortfall: Mapping[str, Any],
    receipts: Optional[list[dict]] = None,
    payload_shas: Optional[Mapping[str, str]] = None,
    lane_accepted: Optional[Mapping[str, int]] = None,
    provider_call_count: int = 0,
) -> dict:
    return {
        "schema_version": 1,
        "status": "error",
        "candidate_pack": None,
        "failure_reasons": list(dict.fromkeys(failure_reasons)),
        "shortfall": dict(shortfall),
        "prompt_receipts": list(receipts or []),
        "prompt_payload_shas": dict(payload_shas or {}),
        "lane_accepted_counts": dict(lane_accepted or {lane: 0 for lane in _RESEARCH_LANES}),
        "provider_call_count": int(provider_call_count),
        "authority": _AUTHORITY_NOTE,
    }


# DR-04 -- optional final-owner wiring (default OFF via `final_owner_enabled`).
#   Maps an assembled candidate dict (see `_assemble_candidate`) onto the
#   candidate_pool proposal shape so `select_official_candidate` (the
#   UNCHANGED, single selection owner) can pick exactly one official
#   candidate from this pack's 4 accepted candidates. Import is local -- this
#   module stays free of any top-level `ai_strategy_loop.controller` import
#   when the feature is OFF (the default), keeping the OFF path byte-for-byte
#   identical to before this feature existed.
_FINAL_OWNER_ROUND_SIZE = 4


def _candidate_pool_proposal(candidate: Mapping[str, Any]) -> dict:
    novelty = candidate.get("novelty")
    novelty_value = float(len(novelty)) if isinstance(novelty, Mapping) else 0.0
    return {
        "candidate_id": str(candidate.get("hypothesis_id") or ""),
        "lane": str(candidate.get("lane") or ""),
        "family": str(candidate.get("mutation_axis") or "unspecified"),
        "expression": str(candidate.get("expression") or ""),
        "timeframe": str(candidate.get("timeframe") or ""),
        "novelty": novelty_value,
        "threshold_provenance": {},
    }


def produce_candidate_pack_result(
    context: Mapping[str, Any],
    provider: Callable[[list[dict]], str],
    *,
    lanes: Optional[Mapping[str, int]] = None,
    axis_prompt_lines: Optional[list[str]] = None,
    retry_max_per_lane: int = RETRY_MAX_PER_LANE,
    final_owner_enabled: bool = False,
    methodology_version: str = "clr04_v1",
    strict_candidate_payload_v2: bool = False,
) -> dict:
    """repair/discovery 레인별로 provider 를 호출해 후보팩 결과 봉투를 만든다.

    반환 봉투: {status: ok|partial|error, candidate_pack: dict|None,
    failure_reasons, shortfall, prompt_receipts, prompt_payload_shas,
    lane_accepted_counts, provider_call_count}. candidate_pack 은
    cli/condition_generator.validate_multi_hypothesis_candidate_pack 을
    통과하도록 조립되며, terminal 실패(provider 예외/입력 위반/후보 0개)면
    None 이다 — research_loop 의 결정론 폴백이 자연 발동한다.
    """

    lane_counts, lane_reasons = _normalized_lanes(lanes)
    input_reasons = lane_reasons + _input_failure_reasons(context, lane_counts, axis_prompt_lines)
    if input_reasons:
        shortfall = {
            lane: {"requested": count, "accepted": 0, "missing": count}
            for lane, count in lane_counts.items()
            if count > 0
        }
        return _error_envelope(input_reasons, shortfall=shortfall)
    if not callable(provider):
        return _error_envelope(["provider_not_callable"], shortfall={})

    kind = str(context.get("kind") or "buy")
    if strict_candidate_payload_v2 and kind != "buy":
        return _error_envelope(
            ["candidate_payload_side_mismatch"],
            shortfall={
                lane: {"requested": count, "accepted": 0, "missing": count}
                for lane, count in lane_counts.items() if count > 0
            },
        )
    timeframe = str(context.get("timeframe") or "")
    parents = {side: _parent_side(context, side) for side in ("buy", "sell")}
    raw_context_pack = context.get("research_context_pack")
    research_context_pack = raw_context_pack if isinstance(raw_context_pack, Mapping) else None
    raw_card = context.get("analysis_card")
    analysis_card = dict(raw_card) if isinstance(raw_card, Mapping) else {}
    repair_card = _repair_analysis_card(analysis_card, axis_prompt_lines)
    raw_gap = context.get("coverage_gap")
    coverage_gap = dict(raw_gap) if isinstance(raw_gap, Mapping) else {}
    raw_novelty = context.get("novelty_context")
    novelty_context = dict(raw_novelty) if isinstance(raw_novelty, Mapping) else {}
    context_trace = _context_pack_trace(research_context_pack)
    round_id = str(context.get("round_id") or "")
    prompt_score = int(context.get("prompt_score") or 0)

    seen_expressions: set[str] = set()
    seen_hypothesis_ids: set[str] = set()
    accepted: list[dict] = []
    records: list[dict] = []
    failure_reasons: list[str] = []
    total_attempts = 0
    terminal = False
    for lane in _RESEARCH_LANES:
        required = lane_counts.get(lane, 0)
        if required <= 0:
            continue
        outcome = _fill_lane(
            lane,
            required,
            provider=provider,
            kind=kind,
            timeframe=timeframe,
            parents=parents,
            analysis_card=repair_card,
            coverage_gap=coverage_gap,
            novelty_context=novelty_context,
            research_context_pack=research_context_pack,
            strict_candidate_payload_v2=strict_candidate_payload_v2,
            seen_expressions=seen_expressions,
            seen_hypothesis_ids=seen_hypothesis_ids,
            retry_max=retry_max_per_lane,
        )
        accepted.extend(outcome["accepted"])
        records.extend(outcome["records"])
        failure_reasons.extend(outcome["failure_reasons"])
        total_attempts += outcome["attempts"]
        if outcome["terminal"]:
            terminal = True
            break

    lane_accepted = {
        lane: sum(1 for item in accepted if item["lane"] == lane) for lane in _RESEARCH_LANES
    }
    shortfall = {
        lane: {
            "requested": lane_counts.get(lane, 0),
            "accepted": lane_accepted[lane],
            "missing": lane_counts.get(lane, 0) - lane_accepted[lane],
        }
        for lane in _RESEARCH_LANES
        if lane_counts.get(lane, 0) > lane_accepted[lane]
    }
    payload_shas = {record["slot_id"]: record["payload_sha256"] for record in records}

    if terminal or not accepted:
        if not terminal:
            failure_reasons = [*failure_reasons, "no_valid_candidates_produced"]
        receipts = [
            _receipt_for_attempt(
                record,
                context_trace=context_trace,
                round_id=round_id,
                prompt_score=prompt_score,
                parents=parents,
                analysis_card=repair_card,
                pack_id=None,
            )
            for record in records
        ]
        return _error_envelope(
            failure_reasons,
            shortfall=shortfall,
            receipts=receipts,
            payload_shas=payload_shas,
            lane_accepted=lane_accepted,
            provider_call_count=total_attempts,
        )

    pack_id = "cpk_" + _sha256_text(_canonical_json({
        "kind": kind,
        "timeframe": timeframe,
        "parents": parents,
        "lanes": lane_counts,
        "expressions": [item["expression"] for item in accepted],
        "hypothesis_ids": [item["hypothesis_id"] for item in accepted],
    }))[:16]
    receipts = [
        _receipt_for_attempt(
            record,
            context_trace=context_trace,
            round_id=round_id,
            prompt_score=prompt_score,
            parents=parents,
            analysis_card=repair_card,
            pack_id=pack_id,
        )
        for record in records
    ]
    pack: dict[str, Any] = {
        "schema_version": 1,
        "candidate_pack_version": CANDIDATE_PACK_VERSION,
        "candidate_pack_id": pack_id,
        "producer": PACK_PRODUCER_VERSION,
        "kind": kind,
        "timeframe": timeframe,
        "parents": parents,
        "candidates": accepted,
        "lanes_requested": dict(lane_counts),
        "lane_accepted_counts": lane_accepted,
        "shortfall": shortfall,
        "production_failures": list(failure_reasons),
        "prompt_receipts": receipts,
        "prompt_payload_shas": payload_shas,
        "mode_authority": "research_only",
        "generation_allowed": True,
    }
    if context_trace["id"]:
        pack["context_pack_id"] = context_trace["id"]
    if context_trace["sha256"]:
        pack["context_pack_sha256"] = context_trace["sha256"]
    if context_trace["full_sources"] is not None:
        pack["full_stom_sources_included"] = context_trace["full_sources"]
    if context_trace["tokens"] is not None:
        pack["prompt_budget_estimated_tokens"] = context_trace["tokens"]

    final_owner_selection: Optional[dict] = None
    if final_owner_enabled and not shortfall and len(accepted) == _FINAL_OWNER_ROUND_SIZE:
        from ai_strategy_loop.controller.candidate_pool import (  # noqa: PLC0415
            select_official_candidate,
        )
        pool_proposals = [_candidate_pool_proposal(item) for item in accepted]
        final_owner_selection = select_official_candidate(
            pool_proposals, timeframe=timeframe, methodology_version=methodology_version,
        )
        pack["final_owner_selection"] = final_owner_selection

    result: dict[str, Any] = {
        "schema_version": 1,
        "status": "ok" if not shortfall else "partial",
        "candidate_pack": pack,
        "failure_reasons": list(failure_reasons),
        "shortfall": shortfall,
        "prompt_receipts": list(receipts),
        "prompt_payload_shas": dict(payload_shas),
        "lane_accepted_counts": dict(lane_accepted),
        "provider_call_count": total_attempts,
        "authority": _AUTHORITY_NOTE,
    }
    if final_owner_selection is not None:
        result["final_owner_selection"] = final_owner_selection
    return result


def produce_candidate_pack(
    context: Mapping[str, Any],
    provider: Callable[[list[dict]], str],
    *,
    lanes: Optional[Mapping[str, int]] = None,
    axis_prompt_lines: Optional[list[str]] = None,
    retry_max_per_lane: int = RETRY_MAX_PER_LANE,
    strict_candidate_payload_v2: bool = False,
) -> Optional[dict]:
    """research_candidate_pack dict 를 반환한다. terminal 실패면 None.

    None 을 analysis_result['research_candidate_pack'] 에 넣으면 falsy 라서
    cli.research_loop 의 결정론 폴백(mark_diagnostic_fallback, credit 0)이
    자연 발동한다. 실패 사유 리스트/영수증이 필요하면
    produce_candidate_pack_result 를 사용한다.
    """

    result = produce_candidate_pack_result(
        context,
        provider,
        lanes=lanes,
        axis_prompt_lines=axis_prompt_lines,
        retry_max_per_lane=retry_max_per_lane,
        strict_candidate_payload_v2=strict_candidate_payload_v2,
    )
    return result["candidate_pack"]
