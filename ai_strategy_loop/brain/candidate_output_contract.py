"""Versioned LLM candidate-output boundary.

The V2 envelope binds generated text to the consumer that may admit it.  It is
pure parsing/validation code: callers must validate before compiling, saving,
or otherwise consuming ``body``.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping, Optional

CANDIDATE_PAYLOAD_SCHEMA_VERSION = 11
FULL_STRATEGY = "full_strategy"
BUY_EXCLUSION_EXPR = "buy_exclusion_expr"
STRATEGY_SAVER_CONSUMER = "strategy_saver/generator"
RESEARCH_FILTER_CONSUMER = "research_filter"

_OUTPUT_KINDS = (FULL_STRATEGY, BUY_EXCLUSION_EXPR)
_SIDES = ("buy", "sell")
_TIMEFRAMES = ("min", "tick")
_JSON_FENCE_RE = re.compile(r"```json\s*\n(\{.*\})\s*```", re.DOTALL | re.IGNORECASE)
_PAYLOAD_KEYS = {
    "schema_version",
    "output_kind",
    "side",
    "timeframe",
    "body",
    "canonical_body_sha256",
    "expected_consumer",
}
_ALLOWED_BOOL_OPS = (ast.And, ast.Or)
_ALLOWED_COMPARE_OPS = (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn)
_ALLOWED_ARITHMETIC_OPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)


@dataclass(frozen=True)
class CandidatePayloadV2:
    output_kind: str
    side: str
    timeframe: str
    body: str
    canonical_body_sha256: str
    schema_version: int = CANDIDATE_PAYLOAD_SCHEMA_VERSION
    expected_consumer: str = STRATEGY_SAVER_CONSUMER

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "output_kind": self.output_kind,
            "side": self.side,
            "timeframe": self.timeframe,
            "body": self.body,
            "canonical_body_sha256": self.canonical_body_sha256,
            "expected_consumer": self.expected_consumer,
        }


def canonicalize_body(body: str) -> str:
    """Canonical body is LF-normalized with only outer blank space removed."""
    return body.replace("\r\n", "\n").replace("\r", "\n").strip()


def canonical_body_sha256(body: str) -> str:
    return hashlib.sha256(canonicalize_body(body).encode("utf-8")).hexdigest()


def make_candidate_payload(
    *, output_kind: str, side: str, timeframe: str, body: str, expected_consumer: str
) -> CandidatePayloadV2:
    canonical_body = canonicalize_body(body)
    return CandidatePayloadV2(
        output_kind=output_kind,
        side=side,
        timeframe=timeframe,
        body=canonical_body,
        canonical_body_sha256=canonical_body_sha256(canonical_body),
        expected_consumer=expected_consumer,
    )


def render_candidate_payload_contract(
    *, output_kind: str, side: str, timeframe: str, expected_consumer: str
) -> str:
    """Single source of truth rendered into both system and user messages."""
    predicate_rule = (
        "body must be exactly one Python eval-mode Boolean predicate; no statements, "
        "assignment, code fence, metadata, or explanation."
        if output_kind == BUY_EXCLUSION_EXPR
        else "body must be one complete STOM strategy source; no explanation outside the JSON object."
    )
    example = make_candidate_payload(
        output_kind=output_kind,
        side=side,
        timeframe=timeframe,
        body="현재가 > 시가" if output_kind == BUY_EXCLUSION_EXPR else "매수 = False\nif 매수:\n    self.Buy()",
        expected_consumer=expected_consumer,
    ).as_dict()
    return "\n".join((
        "CandidatePayloadV2 output contract (mandatory):",
        f"- schema_version must be {CANDIDATE_PAYLOAD_SCHEMA_VERSION}.",
        f"- output_kind must be {output_kind!r}; side must be {side!r}; timeframe must be {timeframe!r}.",
        f"- expected_consumer must be {expected_consumer!r}.",
        "- canonical_body_sha256 must be SHA-256 of body after LF normalization and outer whitespace stripping.",
        f"- {predicate_rule}",
        "- Return exactly one ```json fenced object and nothing else. Example:",
        f"```json\n{json.dumps(example, ensure_ascii=False, sort_keys=True)}\n```",
    ))


def _parse_payload(response_text: str) -> tuple[Optional[Mapping[str, Any]], str]:
    match = _JSON_FENCE_RE.fullmatch((response_text or "").strip())
    if match is None:
        return None, "candidate_payload_missing_or_extra_content"

    def _reject_duplicate_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate key: {key}")
            result[key] = value
        return result

    try:
        payload = json.loads(match.group(1), object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError:
        return None, "candidate_payload_not_json"
    except ValueError:
        return None, "candidate_payload_duplicate_key"
    if not isinstance(payload, Mapping):
        return None, "candidate_payload_not_object"
    if set(payload) != _PAYLOAD_KEYS:
        return None, "candidate_payload_schema_fields_mismatch"
    return payload, ""


def _is_boolean_predicate(body: str) -> bool:
    try:
        parsed = ast.parse(body, mode="eval")
    except (SyntaxError, ValueError):
        return False

    def safe_value(node: ast.AST) -> bool:
        if isinstance(node, ast.Name):
            return isinstance(node.ctx, ast.Load)
        if isinstance(node, ast.Constant):
            return isinstance(node.value, (str, int, float, bool)) and not isinstance(
                node.value, complex
            )
        if isinstance(node, ast.BinOp):
            return (
                isinstance(node.op, _ALLOWED_ARITHMETIC_OPS)
                and safe_value(node.left)
                and safe_value(node.right)
            )
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            return safe_value(node.operand)
        return False

    def safe_predicate(node: ast.AST) -> bool:
        if isinstance(node, ast.BoolOp):
            return (
                isinstance(node.op, _ALLOWED_BOOL_OPS)
                and len(node.values) >= 2
                and all(safe_predicate(value) for value in node.values)
            )
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return safe_predicate(node.operand)
        if isinstance(node, ast.Compare):
            return (
                all(isinstance(op, _ALLOWED_COMPARE_OPS) for op in node.ops)
                and safe_value(node.left)
                and all(safe_value(value) for value in node.comparators)
            )
        return isinstance(node, ast.Constant) and isinstance(node.value, bool)

    return safe_predicate(parsed.body)


def validate_candidate_payload(
    response_text: str,
    *,
    expected_output_kind: str,
    expected_side: str,
    expected_timeframe: str,
    expected_consumer: str,
) -> dict[str, Any]:
    """Parse and admit a V2 envelope with stable pre-side-effect reason codes."""
    payload, parse_reason = _parse_payload(response_text)
    reasons: list[str] = [parse_reason] if parse_reason else []
    value = payload or {}
    output_kind = value.get("output_kind")
    side = value.get("side")
    timeframe = value.get("timeframe")
    body = value.get("body")
    consumer = value.get("expected_consumer")
    if value.get("schema_version") != CANDIDATE_PAYLOAD_SCHEMA_VERSION:
        reasons.append("candidate_payload_schema_version_mismatch")
    if output_kind not in _OUTPUT_KINDS:
        reasons.append("candidate_payload_invalid_output_kind")
    if side not in _SIDES:
        reasons.append("candidate_payload_invalid_side")
    if timeframe not in _TIMEFRAMES:
        reasons.append("candidate_payload_invalid_timeframe")
    if output_kind == FULL_STRATEGY and consumer != STRATEGY_SAVER_CONSUMER:
        reasons.append("candidate_payload_cross_kind_consumer")
    if output_kind == BUY_EXCLUSION_EXPR and (consumer != RESEARCH_FILTER_CONSUMER or side != "buy"):
        reasons.append("candidate_payload_cross_kind_consumer")
    if output_kind != expected_output_kind:
        reasons.append("candidate_payload_output_kind_mismatch")
    if consumer != expected_consumer:
        reasons.append("candidate_payload_expected_consumer_mismatch")
    if side != expected_side:
        reasons.append("candidate_payload_side_mismatch")
    if timeframe != expected_timeframe:
        reasons.append("candidate_payload_timeframe_mismatch")
    if not isinstance(body, str) or not body.strip():
        reasons.append("candidate_payload_body_missing")
        canonical_body = ""
    else:
        canonical_body = canonicalize_body(body)
        if value.get("canonical_body_sha256") != canonical_body_sha256(canonical_body):
            reasons.append("candidate_payload_body_sha256_mismatch")
        if output_kind == BUY_EXCLUSION_EXPR and not _is_boolean_predicate(canonical_body):
            reasons.append("candidate_payload_invalid_boolean_predicate")
    reason = "|".join(dict.fromkeys(reason for reason in reasons if reason))
    return {
        "valid": not reason,
        "failure_reason": reason,
        "payload": dict(value),
        "body": canonical_body,
        "output_kind": output_kind,
        "side": side,
        "timeframe": timeframe,
        "expected_consumer": consumer,
    }
