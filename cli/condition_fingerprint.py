"""Semantic condition fingerprinting + B-only ingestion guard (CL-R04 9a).

Pure stdlib (ast, hashlib, decimal, unicodedata, re, enum, dataclasses, types).
No DB/network/backtest/provider imports and no file side effects at import
time -- this module is imported at the ingestion gate, before any candidate
is accepted, and must stay side-effect free.

See docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/
lattice_v3_design_spec_20260709.md sections 6 (B-only approved inputs) and
11 (semantic/rowset fingerprint identity) for the design this implements.
"""

from __future__ import annotations

import ast
import enum
import hashlib
import re
import types
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Mapping

from ai_strategy_loop.brain.variable_scope import check_variable_scope

_HEX64_RE = re.compile(r'^[0-9a-fA-F]{64}$')

# fit_role values that indicate a full-dataset/out-of-sample/validation
# partition. Thresholds derived from these leak evaluation information back
# into the training signal and must never be accepted as fit provenance.
_FORBIDDEN_FIT_ROLES = frozenset({'full_baseline', 'oos', 'validation'})

_LEAKY_NAME_PREFIXES = ('R_', 'S_')
_LEAKY_BARE_NAMES = frozenset({'result', 'R', 'S'})

_FORBIDDEN_VALIDATION_NODE_TYPES = (ast.Call, ast.Attribute, ast.Subscript)

_COMPARE_OP_NAMES = {
    ast.Lt: 'lt',
    ast.LtE: 'le',
    ast.Gt: 'gt',
    ast.GtE: 'ge',
    ast.Eq: 'eq',
    ast.NotEq: 'ne',
}


class FingerprintError(Exception):
    """Raised when an expression cannot be reduced to an allowed AST shape."""


class ThresholdEstimator(enum.Enum):
    BUCKET = 'bucket'
    QUANTILE = 'quantile'
    MEDIAN_TTEST = 'median_ttest'
    MODEL_IMPORTANCE = 'model_importance'


@dataclass(frozen=True)
class ThresholdProvenance:
    """Immutable record of how a threshold was fit -- never on full/oos/validation data."""

    estimator: ThresholdEstimator
    parameters: Mapping[str, object]
    fit_role: str
    period: str
    row_count: int
    row_signature: str
    dataset_sha: str
    fold_id: str
    source_receipt: str

    def __post_init__(self) -> None:
        if not isinstance(self.estimator, ThresholdEstimator):
            raise TypeError(
                f'estimator must be a ThresholdEstimator member, got {self.estimator!r}'
            )
        for field_name in (
            'fit_role', 'period', 'row_signature', 'dataset_sha', 'fold_id', 'source_receipt',
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f'{field_name} must be a non-empty string')
        if not isinstance(self.row_count, int) or isinstance(self.row_count, bool) or self.row_count <= 0:
            raise ValueError(f'row_count must be a positive int, got {self.row_count!r}')
        if not _HEX64_RE.match(self.dataset_sha):
            raise ValueError(f'dataset_sha must be 64 hex characters, got {self.dataset_sha!r}')
        if self.fit_role in _FORBIDDEN_FIT_ROLES:
            raise ValueError(
                f'fit_role={self.fit_role!r} is a full-baseline/oos/validation partition; '
                'thresholds must be fit on train/fit partitions only'
            )
        object.__setattr__(self, 'parameters', types.MappingProxyType(dict(self.parameters)))

    def to_dict(self) -> dict:
        return {
            'estimator': self.estimator.value,
            'parameters': dict(self.parameters),
            'fit_role': self.fit_role,
            'period': self.period,
            'row_count': self.row_count,
            'row_signature': self.row_signature,
            'dataset_sha': self.dataset_sha,
            'fold_id': self.fold_id,
            'source_receipt': self.source_receipt,
        }


def _canonical_constant(value: object) -> str:
    if isinstance(value, bool):
        raise FingerprintError('boolean constants are not allowed in condition expressions')
    if isinstance(value, (int, float)):
        try:
            normalized = Decimal(str(value)).normalize()
        except InvalidOperation as exc:
            raise FingerprintError(f'non-decimal-representable numeric constant: {value!r}') from exc
        text = format(normalized, 'f')
        return f'const:{text}'
    raise FingerprintError(f'unsupported constant type: {type(value).__name__}')


def _canonicalize(node: ast.AST) -> str:
    if isinstance(node, ast.Expression):
        return _canonicalize(node.body)
    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            op_name = 'and'
        elif isinstance(node.op, ast.Or):
            op_name = 'or'
        else:
            raise FingerprintError(f'forbidden boolean operator: {type(node.op).__name__}')
        children = sorted(_canonicalize(value) for value in node.values)
        return f'({op_name} ' + ' '.join(children) + ')'
    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.Not):
            return f'(not {_canonicalize(node.operand)})'
        if isinstance(node.op, (ast.USub, ast.UAdd)) and isinstance(node.operand, ast.Constant):
            sign = -1 if isinstance(node.op, ast.USub) else 1
            value = node.operand.value
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise FingerprintError(
                    f'unsupported constant type under unary operator: {type(value).__name__}'
                )
            return _canonical_constant(sign * value)
        raise FingerprintError(f'forbidden unary operator: {type(node.op).__name__}')
    if isinstance(node, ast.Compare):
        left = _canonicalize(node.left)
        pieces = []
        for op, comparator in zip(node.ops, node.comparators):
            op_name = _COMPARE_OP_NAMES.get(type(op))
            if op_name is None:
                raise FingerprintError(f'forbidden comparison operator: {type(op).__name__}')
            pieces.append(f'{op_name}:{_canonicalize(comparator)}')
        return '(compare ' + left + ' ' + ' '.join(pieces) + ')'
    if isinstance(node, ast.Name):
        if not isinstance(node.ctx, ast.Load):
            raise FingerprintError(f'forbidden name context: {type(node.ctx).__name__}')
        return 'name:' + unicodedata.normalize('NFC', node.id)
    if isinstance(node, ast.Constant):
        return _canonical_constant(node.value)
    raise FingerprintError(f'forbidden node type: {type(node).__name__}')


def ast_fingerprint(expression: str, *, timeframe: str, methodology_version: str) -> str:
    """Return a stable sha256 hex identity for the semantic content of `expression`.

    Whitespace, parenthesization, AND/OR child order, and equivalent numeric
    literal spellings (`1` vs `1.0`) all collapse to the same fingerprint.
    Different `timeframe` or `methodology_version` always differ.

    Raises FingerprintError if the expression contains anything outside the
    allowed Boolean/Compare/Name/numeric-Constant grammar (Call, Attribute,
    Subscript, Lambda, comprehensions, arithmetic BinOp, etc.).
    """

    try:
        tree = ast.parse(expression.strip(), mode='eval')
    except SyntaxError as exc:
        raise FingerprintError(f'unparseable expression: {exc}') from exc
    canonical = _canonicalize(tree)
    payload = f'{timeframe}|{methodology_version}|{canonical}'
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def rowset_fingerprint(*, dataset_sha: str, window: str, row_keys: list[str]) -> str:
    """Return a stable sha256 hex identity for a dataset/window/rowset triple.

    Row key order does not matter (sorted before hashing); a different
    dataset_sha, window, or row-key set always yields a different fingerprint.
    """

    payload = dataset_sha + '|' + window + '|' + '\n'.join(sorted(row_keys))
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def validate_b_only(expression: str, *, timeframe: str, kind: str = 'buy') -> list[str]:
    """Return blocker reason codes for `expression` against the B-only approved surface.

    Empty list means the expression is safe to ingest. Never raises for bad
    input -- unparseable/forbidden content is reported as reason codes.
    """

    try:
        tree = ast.parse(expression.strip(), mode='eval')
    except SyntaxError:
        return ['unparseable_expression']

    reasons: list[str] = []

    forbidden_node_types: set[str] = set()
    leaky_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, _FORBIDDEN_VALIDATION_NODE_TYPES):
            forbidden_node_types.add(type(node).__name__)
        elif isinstance(node, ast.Name):
            if node.id.startswith(_LEAKY_NAME_PREFIXES) or node.id in _LEAKY_BARE_NAMES:
                leaky_names.add(node.id)

    for name in sorted(leaky_names):
        reasons.append(f'leaky_result_variable:{name}')
    for node_type in sorted(forbidden_node_types):
        reasons.append(f'forbidden_node:{node_type}')

    ok, offending = check_variable_scope(expression, timeframe, kind)
    if not ok:
        for name in offending:
            if name in leaky_names:
                continue  # already reported as a leaky result/diagnostic variable
            reasons.append(f'non_approved_variable:{name}')

    return reasons
