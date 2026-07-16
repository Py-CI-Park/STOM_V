"""Persistence, hypothesis, and human-pattern-card helpers for condition discovery.

The helpers are read-only/data-contract utilities. They do not query operating DBs,
run backtests, import performance truth into prompts, or approve promotion.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from ai_strategy_loop.controller.condition_discovery import preset_policy

_NUMBER_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")
_WHITESPACE_RE = re.compile(r"\s+")
_OPERATOR_SPACE_RE = re.compile(r"\s*([<>=!+\-*/%(),:&|]+)\s*")
_ALLOWED_HYPOTHESIS_STATUS = {"accepted", "rejected", "deferred", "inconclusive"}
# 시간축 게이트(예: 90000 <= 시분초 < 93000)는 생성 가드가 구조적으로 요구하고
# 인간 시드도 같은 세션 상수를 쓸 수밖에 없다. 시간축 비교는 "고유 임계값"이
# 아니므로 항목 단위 복사 판정에서 제외한다(전체 숫자집합 동일 판정에는 남는다).
_TIME_AXIS_VARIABLES = frozenset({"시분초", "시간"})
_IDENTIFIER = r"[가-힣A-Za-z_][가-힣A-Za-z_0-9]*"
_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
_COMPARISON_RE = re.compile(rf"({_IDENTIFIER})\s*(<=|>=|==|!=|<|>)\s*({_NUMBER})")
_REVERSED_COMPARISON_RE = re.compile(rf"({_NUMBER})\s*(<=|>=|<|>)\s*({_IDENTIFIER})")
_FLIPPED_OPERATOR = {"<": ">", ">": "<", "<=": ">=", ">=": "<="}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _compact(text: Any) -> str:
    return _WHITESPACE_RE.sub(" ", str(text or "")).strip()


def _canonical_number(text: str) -> str:
    try:
        number = Decimal(text)
    except (InvalidOperation, ValueError):
        return text
    rendered = format(number.normalize(), "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    if rendered == "-0":
        return "0"
    return rendered


def strip_numeric_thresholds(text: Any) -> str:
    """Replace numeric literals so prompt excerpts teach structure, not thresholds."""

    return _NUMBER_RE.sub("<N>", _compact(text))


def _canonical_thresholds(text: Any) -> List[str]:
    return [_canonical_number(v) for v in _NUMBER_RE.findall(str(text or ""))]


def _comparison_threshold_items(text: Any) -> List[str]:
    """비교식에서 (변수, 연산자, 정규화 숫자) 항목을 추출한다.

    맨숫자(bare number)가 아니라 문맥 있는 임계값만 항목으로 삼아,
    0/1/100 같은 보편 상수 공유가 복사로 오판되는 것을 막는다.
    시간축 변수 비교는 제외한다(_TIME_AXIS_VARIABLES 참조).
    """
    source = str(text or "")
    items = set()
    for var, op, num in _COMPARISON_RE.findall(source):
        if var in _TIME_AXIS_VARIABLES:
            continue
        items.add(f"{var}{op}{_canonical_number(num)}")
    for num, op, var in _REVERSED_COMPARISON_RE.findall(source):
        if var in _TIME_AXIS_VARIABLES:
            continue
        items.add(f"{var}{_FLIPPED_OPERATOR[op]}{_canonical_number(num)}")
    return sorted(items)


def _threshold_fingerprint(text: Any) -> tuple[List[str], str, List[str]]:
    """(전체 숫자 목록, 숫자집합 해시, 문맥 임계값 항목 해시)를 반환한다.

    - 숫자집합 해시: 표현식의 모든 숫자를 통째로 베낀 경우를 잡는 조밀 판정.
    - 항목 해시: 변수+연산자+숫자 삼중항 단위 판정. 단일 숫자 겹침만으로는
      차단하지 않는다(2026-07-16 실 A/B에서 100% 오차단이 확인된 결함 수정).
    """
    values = _canonical_thresholds(text)
    canonical_set = sorted(set(values))
    normalized = ",".join(canonical_set)
    item_hashes = [_sha(item) for item in _comparison_threshold_items(text)]
    return values, _sha(normalized) if canonical_set else "", item_hashes


def normalize_expression_for_hash(text: Any) -> str:
    compacted = _compact(text).lower()
    without_operator_space = _OPERATOR_SPACE_RE.sub(r"\1", compacted)
    return _WHITESPACE_RE.sub("", without_operator_space)


def build_persistence_state(
    config: Any,
    *,
    prompt_records: Optional[int] = None,
    equity_points: Optional[int] = None,
) -> Dict[str, Any]:
    """Publish prompt/equity persistence health without reading runtime DBs."""

    policy = preset_policy(getattr(config, "condition_discovery_preset", "fast"))
    prompt_enabled = bool(getattr(config, "prompt_logging_enabled", False))
    equity_enabled = bool(getattr(config, "equity_points_enabled", False))

    def row(kind: str, enabled: bool, required: bool, count: Optional[int]) -> Dict[str, Any]:
        if not required and not enabled:
            status = "not_required"
        elif not enabled:
            status = "missing"
        elif count is None:
            status = "unavailable"
        elif int(count) > 0:
            status = "present"
        else:
            status = "missing"
        blocker = required and status in {"missing", "unavailable", "failed"}
        return {
            "kind": kind,
            "enabled": enabled,
            "required": required,
            "count": count,
            "status": status,
            "blocker_reason": f"missing_{kind}_persistence" if blocker else "",
        }

    rows = [
        row("prompt", prompt_enabled, policy.prompt_logging_required, prompt_records),
        row("equity", equity_enabled, policy.equity_points_required, equity_points),
    ]
    blockers = [r["blocker_reason"] for r in rows if r["blocker_reason"]]
    return {
        "status": "evidence_blocker" if blockers else "complete",
        "items": rows,
        "blockers": blockers,
        "authority": "persistence_evidence_only_no_generation_or_promotion_authority",
    }


def normalize_hypotheses(
    hypotheses: Optional[Iterable[Mapping[str, Any]]],
    *,
    default_source: str = "autopsy",
) -> Dict[str, Any]:
    """Normalize advisory autopsy hypotheses with provenance and safe statuses."""

    rows: List[Dict[str, Any]] = []
    for idx, raw in enumerate(hypotheses or []):
        if not isinstance(raw, Mapping):
            raw = {"text": raw, "status": "deferred", "source": default_source}
        status = _compact(raw.get("status") or raw.get("verdict") or "deferred").lower()
        if status not in _ALLOWED_HYPOTHESIS_STATUS:
            status = "deferred"
        rows.append({
            "id": _compact(raw.get("id") or f"hypothesis-{idx + 1}"),
            "status": status,
            "hypothesis": _compact(raw.get("hypothesis") or raw.get("text")),
            "source": _compact(raw.get("source") or default_source),
            "provenance": _compact(raw.get("provenance") or raw.get("evidence") or "autopsy_feedback"),
            "advisory_only": True,
        })
    return {
        "status": "ok" if rows else "empty",
        "items": rows,
        "authority": "advisory_prompt_context_only",
    }


def build_pattern_card(
    *,
    card_id: str,
    source_label: str,
    side: str,
    expression: str,
    pattern_summary: str,
    variable_families: Sequence[str],
    composition_tags: Optional[Sequence[str]] = None,
    performance: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a human-DB composition card without copying thresholds or returns."""

    normalized_expression = normalize_expression_for_hash(expression)
    thresholds, threshold_hash, threshold_item_hashes = _threshold_fingerprint(expression)
    skeleton = strip_numeric_thresholds(expression)
    prompt_excerpt = strip_numeric_thresholds(pattern_summary)
    rejected_perf = sorted(str(k) for k in (performance or {}).keys())
    return {
        "card_id": _compact(card_id),
        "source_label": _compact(source_label),
        "side": _compact(side or "pair"),
        "pattern_summary": prompt_excerpt,
        "variable_families": sorted({_compact(v) for v in variable_families if _compact(v)}),
        "composition_tags": sorted({_compact(v) for v in (composition_tags or []) if _compact(v)}),
        "composition_skeleton": skeleton,
        "threshold_policy": "thresholds_stripped_do_not_copy_numbers",
        "normalized_expression_hash": _sha(normalized_expression),
        "normalized_threshold_hash": threshold_hash,
        "threshold_item_hashes": threshold_item_hashes,
        "threshold_count": len(thresholds),
        "allowed_prompt_excerpt": prompt_excerpt,
        "performance_imported": False,
        "rejected_performance_fields": rejected_perf,
        "authority": "creativity_seed_only_not_performance_truth",
    }


def validate_pattern_card_usage(
    generated_expression: str,
    card: Mapping[str, Any],
    *,
    imported_performance: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Detect full-expression, threshold, or performance-truth copying."""

    normalized = normalize_expression_for_hash(generated_expression)
    thresholds, threshold_hash, threshold_item_hashes = _threshold_fingerprint(generated_expression)
    card_item_hashes = set(card.get("threshold_item_hashes") or [])
    blockers: List[str] = []
    if card.get("normalized_expression_hash") == _sha(normalized):
        blockers.append("full_expression_copy")
    if (
        thresholds
        and (
            threshold_hash == card.get("normalized_threshold_hash")
            or bool(card_item_hashes.intersection(threshold_item_hashes))
        )
    ):
        blockers.append("threshold_copy")
    if imported_performance:
        blockers.append("performance_truth_import")
    return {
        "status": "blocked" if blockers else "ok",
        "blockers": blockers,
        "threshold_count": len(thresholds),
        "authority": "anti_copy_guard_creativity_only",
    }


def build_feedback_page_data(
    config: Any,
    *,
    prompt_records: Optional[int] = None,
    equity_points: Optional[int] = None,
    hypotheses: Optional[Iterable[Mapping[str, Any]]] = None,
    pattern_cards: Optional[Iterable[Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    """Assemble feedback payload for later page_data publication."""

    cards = list(pattern_cards or [])
    return {
        "schema_version": 1,
        "persistence": build_persistence_state(
            config,
            prompt_records=prompt_records,
            equity_points=equity_points,
        ),
        "hypotheses": normalize_hypotheses(hypotheses),
        "pattern_cards": {
            "status": "ok" if cards else "empty",
            "items": cards,
            "authority": "human_db_composition_grammar_only_no_threshold_or_performance_copy",
        },
    }


__all__ = [
    "build_feedback_page_data",
    "build_pattern_card",
    "build_persistence_state",
    "normalize_expression_for_hash",
    "normalize_hypotheses",
    "strip_numeric_thresholds",
    "validate_pattern_card_usage",
]
