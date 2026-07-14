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

# 산술 이항 연산자 허용 목록 — 실전 STOM 조건식(예: `시가 * 1.02`,
#   `매수총잔량 * 0.2`)의 스케일/비율 비교를 지문 문법에 수용한다.
#   이전에는 BinOp이 무조건 에러였으므로 기존 식형 지문은 전부 불변이다.
_BINARY_OP_NAMES = {
    ast.Add: 'add',
    ast.Sub: 'sub',
    ast.Mult: 'mul',
    ast.Div: 'div',
}
# 가환 연산은 자식 정준 정렬로 `a*b`와 `b*a`를 동일 지문으로 만든다.
_COMMUTATIVE_BINARY_OPS = (ast.Add, ast.Mult)


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
    if isinstance(node, ast.BinOp):
        op_name = _BINARY_OP_NAMES.get(type(node.op))
        if op_name is None:
            raise FingerprintError(f'forbidden binary operator: {type(node.op).__name__}')
        left = _canonicalize(node.left)
        right = _canonicalize(node.right)
        if isinstance(node.op, _COMMUTATIVE_BINARY_OPS):
            left, right = sorted((left, right))
        return f'({op_name} {left} {right})'
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

    tree = _parse_condition_tree(expression)
    canonical = _canonicalize(tree)
    payload = f'{timeframe}|{methodology_version}|{canonical}'
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def _statement_condition_tests(text: str) -> list:
    """Collect `if`/`elif` test expressions from a statement-form snippet."""

    module = ast.parse(text, mode='exec')
    return [node.test for node in ast.walk(module) if isinstance(node, ast.If)]


def _parse_condition_tree(expression: str) -> ast.Expression:
    """Parse a condition into an eval-mode AST.

    Accepts either a bare boolean expression (기존 계약) or a canonical STOM
    statement snippet (`if <조건>: self.Buy()` / elif 체인 — pack_producer가
    발행하는 후보 `expression` 형태). Statement 입력은 `if`/`elif` test 식만
    추출해 OR로 결합한다(어느 분기든 액션에 도달하면 조건 발화). 이전에는
    statement 입력이 무조건 에러였으므로 기존 식형 지문은 전부 불변이다.

    Raises FingerprintError when neither parse succeeds or no condition
    expression exists in the snippet.
    """

    text = expression.strip()
    try:
        return ast.parse(text, mode='eval')
    except SyntaxError as eval_exc:
        try:
            tests = _statement_condition_tests(text)
        except SyntaxError as exc:
            raise FingerprintError(f'unparseable expression: {exc}') from exc
        if not tests:
            raise FingerprintError(f'unparseable expression: {eval_exc}') from eval_exc
        if len(tests) == 1:
            body = tests[0]
        else:
            body = ast.BoolOp(op=ast.Or(), values=list(tests))
        return ast.Expression(body=body)


def rowset_fingerprint(*, dataset_sha: str, window: str, row_keys: list[str]) -> str:
    """Return a stable sha256 hex identity for a dataset/window/rowset triple.

    Row key order does not matter (sorted before hashing); a different
    dataset_sha, window, or row-key set always yields a different fingerprint.
    """

    payload = dataset_sha + '|' + window + '|' + '\n'.join(sorted(row_keys))
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


# DR-04 -- additive only. ``ast_fingerprint``/``rowset_fingerprint`` above keep
# their exact pre-DR-04 signatures/semantics; this section only adds a version
# constant and a pure helper for building canonical full-row keys (a row's
# *entire* semantic content, not just ``trade_id:net_pnl``) that callers may
# feed into the unchanged ``rowset_fingerprint(row_keys=...)`` contract for
# run-wide rowset-duplicate detection. No new fingerprint algorithm is
# introduced -- callers still hash through the one ``rowset_fingerprint``.
DR04_DEDUP_CONTRACT_VERSION = 'dr04_run_wide_dedup_v1'


def canonical_full_row_key(row: Mapping[str, object]) -> str:
    """Return one canonical full-semantic-row key for a rowset membership row.

    Sorted-key JSON of the *whole* row (not just a trade_id/net_pnl subset) so
    two rows are considered the same member only when every recorded field
    matches. Pure/stdlib-only; never touches a DB/file/network.
    """

    import json  # noqa: PLC0415 -- kept local; the module has no top-level json import.

    return json.dumps(dict(row), ensure_ascii=False, sort_keys=True, default=str)


def validate_b_only(expression: str, *, timeframe: str, kind: str = 'buy') -> list[str]:
    """Return blocker reason codes for `expression` against the B-only approved surface.

    Empty list means the expression is safe to ingest. Never raises for bad
    input -- unparseable/forbidden content is reported as reason codes.
    """

    try:
        tree = _parse_condition_tree(expression)
    except FingerprintError:
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

    try:
        condition_source = ast.unparse(tree.body)
    except Exception:  # noqa: BLE001 — 방어적 폴백(원문 그대로 검사)
        condition_source = expression
    ok, offending = check_variable_scope(condition_source, timeframe, kind)
    if not ok:
        for name in offending:
            if name in leaky_names:
                continue  # already reported as a leaky result/diagnostic variable
            reasons.append(f'non_approved_variable:{name}')

    return reasons
