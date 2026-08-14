"""Offline canonical STOM condition-source representation.

This module is deliberately line-oriented and conservative: it records known STOM
condition constructs, keeps unknown text visible, and only uses Python's parser to
inspect syntax. It does not run strategy source or grant adoption authority.
"""

from __future__ import annotations

import ast
import hashlib
import io
import json
import tokenize
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional, Sequence

SCHEMA_VERSION = "condition_ast_v1"
CANONICALIZER_VERSION = "condition_ast_canonicalizer_v1"
AUTHORITY = "diagnostic_only_no_adoption_authority"
SEED_VALUE = "condition_ast_deterministic_seed_v1"


# ---------------------------------------------------------------------------
# Receipts and immutable payload helpers


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _receipt(schema: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    body = {"schema": schema, **dict(payload)}
    return {**body, "sha256": _sha256_text(_canonical_json(body))}


def _seed_receipt() -> dict[str, Any]:
    return _receipt(
        "condition_ast_seed_receipt_v1",
        {"seed": SEED_VALUE, "random_used": False},
    )


def _canonicalizer_receipt() -> dict[str, Any]:
    return _receipt(
        "condition_ast_config_receipt_v1",
        {
            "canonicalizer_version": CANONICALIZER_VERSION,
            "line_model": "comments_blanks_assignments_if_elif_unknown_v1",
            "normalization": "ast_unparse_for_known_python_fragments",
        },
    )


def _static_config_receipt(
    *,
    allowed_functions: Sequence[str],
    max_clauses: int,
    max_lookback: float,
    max_unknown_lines: int,
) -> dict[str, Any]:
    return _receipt(
        "condition_ast_static_config_receipt_v1",
        {
            "canonicalizer_version": CANONICALIZER_VERSION,
            "allowed_functions": list(allowed_functions),
            "max_clauses": int(max_clauses),
            "max_lookback": float(max_lookback),
            "max_unknown_lines": int(max_unknown_lines),
        },
    )


# ---------------------------------------------------------------------------
# Public data model


@dataclass(frozen=True, slots=True)
class NumericLookback:
    """Literal numeric argument found inside a function call."""

    line_no: int
    function: str
    argument_index: int
    value: int | float
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "line_no": self.line_no,
            "function": self.function,
            "argument_index": self.argument_index,
            "value": self.value,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class ConditionLine:
    """One preserved source line in the conservative condition model."""

    line_no: int
    kind: str
    raw: str
    indent: int
    keyword: str = ""
    target: str = ""
    expression: str = ""
    normalized: str = ""
    inline_body: str = ""
    inline_normalized: str = ""
    inline_kind: str = ""
    comment: str = ""
    parse_error: str = ""
    called_functions: tuple[str, ...] = ()
    numeric_lookbacks: tuple[NumericLookback, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "line_no": self.line_no,
            "kind": self.kind,
            "raw": self.raw,
            "indent": self.indent,
            "keyword": self.keyword,
            "target": self.target,
            "expression": self.expression,
            "normalized": self.normalized,
            "inline_body": self.inline_body,
            "inline_normalized": self.inline_normalized,
            "inline_kind": self.inline_kind,
            "comment": self.comment,
            "parse_error": self.parse_error,
            "called_functions": list(self.called_functions),
            "numeric_lookbacks": [item.to_dict() for item in self.numeric_lookbacks],
        }


@dataclass(frozen=True, slots=True)
class ConditionComplexity:
    """Small deterministic complexity counters for diagnostics only."""

    total_lines: int
    assignment_count: int
    clause_count: int
    comment_count: int
    blank_count: int
    unknown_line_count: int
    function_call_count: int
    unique_function_count: int
    numeric_lookback_count: int
    max_numeric_lookback: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_lines": self.total_lines,
            "assignment_count": self.assignment_count,
            "clause_count": self.clause_count,
            "comment_count": self.comment_count,
            "blank_count": self.blank_count,
            "unknown_line_count": self.unknown_line_count,
            "function_call_count": self.function_call_count,
            "unique_function_count": self.unique_function_count,
            "numeric_lookback_count": self.numeric_lookback_count,
            "max_numeric_lookback": self.max_numeric_lookback,
        }


@dataclass(frozen=True, slots=True)
class ConditionAst:
    """Canonical representation plus original source for exact round-trip."""

    original_source: str
    original_sha256: str
    lines: tuple[ConditionLine, ...]
    canonical_text: str
    canonical_sha256: str
    called_functions: tuple[str, ...]
    numeric_lookbacks: tuple[NumericLookback, ...]
    complexity: ConditionComplexity
    schema: str = SCHEMA_VERSION
    authority: str = AUTHORITY
    no_adoption_authority: bool = True
    config_receipt: Mapping[str, Any] = field(default_factory=_canonicalizer_receipt)
    seed_receipt: Mapping[str, Any] = field(default_factory=_seed_receipt)

    @property
    def canonical_hash(self) -> str:
        """Alias for callers that name the normalized digest as a hash."""
        return self.canonical_sha256

    @property
    def original_hash(self) -> str:
        """Alias for the exact-source SHA-256 digest."""
        return self.original_sha256

    def round_trip_source(self) -> str:
        """Return the exact source bytes as a decoded string supplied by caller."""
        return self.original_source

    def to_dict(self, *, include_original_source: bool = True) -> dict[str, Any]:
        data = {
            "schema": self.schema,
            "original_sha256": self.original_sha256,
            "original_hash": self.original_sha256,
            "canonical_text": self.canonical_text,
            "canonical_sha256": self.canonical_sha256,
            "canonical_hash": self.canonical_sha256,
            "called_functions": list(self.called_functions),
            "numeric_lookbacks": [item.to_dict() for item in self.numeric_lookbacks],
            "complexity": self.complexity.to_dict(),
            "lines": [line.to_dict() for line in self.lines],
            "authority": self.authority,
            "no_adoption_authority": self.no_adoption_authority,
            "config_receipt": dict(self.config_receipt),
            "seed_receipt": dict(self.seed_receipt),
        }
        if include_original_source:
            data["original_source"] = self.original_source
        return data


ConditionAST = ConditionAst


@dataclass(frozen=True, slots=True)
class StaticViolation:
    """Fail-closed static check violation."""

    code: str
    detail: str
    line_no: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "detail": self.detail, "line_no": self.line_no}


@dataclass(frozen=True, slots=True)
class StaticCheckResult:
    """Conservative static check result with diagnostic-only work estimate."""

    ok: bool
    violations: tuple[StaticViolation, ...]
    estimated_work: float
    estimated_work_basis: str
    parsed: ConditionAst
    authority: str = AUTHORITY
    no_adoption_authority: bool = True
    config_receipt: Mapping[str, Any] = field(default_factory=_canonicalizer_receipt)
    seed_receipt: Mapping[str, Any] = field(default_factory=_seed_receipt)

    def to_dict(self, *, include_original_source: bool = False) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "violations": [item.to_dict() for item in self.violations],
            "estimated_work": self.estimated_work,
            "estimated_work_basis": self.estimated_work_basis,
            "parsed": self.parsed.to_dict(include_original_source=include_original_source),
            "authority": self.authority,
            "no_adoption_authority": self.no_adoption_authority,
            "config_receipt": dict(self.config_receipt),
            "seed_receipt": dict(self.seed_receipt),
        }


# ---------------------------------------------------------------------------
# Source parsing and canonicalization


def parse_condition_source(source: str) -> ConditionAst:
    """Build the offline canonical model for STOM condition source."""
    original_source = "" if source is None else str(source)
    lines = tuple(
        _parse_line(line_no, raw)
        for line_no, raw in enumerate(original_source.splitlines(), start=1)
    )
    canonical_text = "\n".join(_canonical_line(line) for line in lines)
    called_functions = _unique(
        function for line in lines for function in line.called_functions
    )
    numeric_lookbacks = tuple(
        lookback for line in lines for lookback in line.numeric_lookbacks
    )
    complexity = _complexity(lines, called_functions, numeric_lookbacks)
    return ConditionAst(
        original_source=original_source,
        original_sha256=_sha256_text(original_source),
        lines=lines,
        canonical_text=canonical_text,
        canonical_sha256=_sha256_text(canonical_text),
        called_functions=called_functions,
        numeric_lookbacks=numeric_lookbacks,
        complexity=complexity,
    )


# Backward-readable alias for call sites that prefer the AST verb.
build_condition_ast = parse_condition_source
canonicalize_condition_source = parse_condition_source
parse_condition_ast = parse_condition_source


def canonical_text(source: str) -> str:
    """Return only the normalized canonical text."""
    return parse_condition_source(source).canonical_text


def canonical_sha256(source: str) -> str:
    """Return only the normalized canonical SHA-256."""
    return parse_condition_source(source).canonical_sha256


def static_check_condition_source(
    source: str | ConditionAst,
    *,
    allowed_functions: Iterable[str] | None,
    max_clauses: int,
    max_lookback: int | float,
    max_unknown_lines: int,
) -> StaticCheckResult:
    """Validate source against explicit offline limits and allowed functions."""
    parsed = source if isinstance(source, ConditionAst) else parse_condition_source(source)
    allowed = tuple(sorted(str(item) for item in (allowed_functions or ())))
    allowed_set = set(allowed)
    violations: list[StaticViolation] = []

    if allowed_functions is None:
        violations.append(
            StaticViolation(
                "allowed_functions_missing",
                "allowed_functions must be supplied explicitly",
            )
        )
    if int(max_clauses) < 0:
        violations.append(StaticViolation("invalid_limit", "max_clauses must be >= 0"))
    if float(max_lookback) < 0:
        violations.append(StaticViolation("invalid_limit", "max_lookback must be >= 0"))
    if int(max_unknown_lines) < 0:
        violations.append(
            StaticViolation("invalid_limit", "max_unknown_lines must be >= 0")
        )

    for line in parsed.lines:
        if line.parse_error:
            violations.append(
                StaticViolation("syntax_error", line.parse_error, line_no=line.line_no)
            )

    if parsed.complexity.clause_count > int(max_clauses):
        violations.append(
            StaticViolation(
                "clauses_exceeded",
                f"clauses={parsed.complexity.clause_count} > max_clauses={int(max_clauses)}",
            )
        )
    if parsed.complexity.unknown_line_count > int(max_unknown_lines):
        violations.append(
            StaticViolation(
                "unknown_lines_exceeded",
                (
                    f"unknown_lines={parsed.complexity.unknown_line_count} "
                    f"> max_unknown_lines={int(max_unknown_lines)}"
                ),
            )
        )

    for function in parsed.called_functions:
        if function not in allowed_set:
            violations.append(
                StaticViolation(
                    "disallowed_function",
                    f"function {function!r} is not in allowed_functions",
                )
            )
    for lookback in parsed.numeric_lookbacks:
        if abs(float(lookback.value)) > float(max_lookback):
            violations.append(
                StaticViolation(
                    "lookback_exceeded",
                    (
                        f"{lookback.function} arg{lookback.argument_index}="
                        f"{lookback.value} > max_lookback={float(max_lookback):g}"
                    ),
                    line_no=lookback.line_no,
                )
            )

    config_receipt = _static_config_receipt(
        allowed_functions=allowed,
        max_clauses=max_clauses,
        max_lookback=float(max_lookback),
        max_unknown_lines=max_unknown_lines,
    )
    return StaticCheckResult(
        ok=not violations,
        violations=tuple(violations),
        estimated_work=_estimate_work(parsed),
        estimated_work_basis=(
            "diagnostic_only: clause_count + sum(abs(numeric_call_args))/100; "
            "no adoption authority"
        ),
        parsed=parsed,
        config_receipt=config_receipt,
        seed_receipt=_seed_receipt(),
    )


check_condition_source = static_check_condition_source
static_check = static_check_condition_source


def estimate_diagnostic_work(source: str | ConditionAst) -> float:
    """Return the deterministic diagnostic work scalar used by static checks."""
    parsed = source if isinstance(source, ConditionAst) else parse_condition_source(source)
    return _estimate_work(parsed)


# ---------------------------------------------------------------------------
# Internal parsing helpers


def _parse_line(line_no: int, raw: str) -> ConditionLine:
    indent = _indent_width(raw)
    stripped = raw.lstrip(" \t")
    if stripped == "":
        return ConditionLine(line_no=line_no, kind="blank", raw=raw, indent=indent)

    code, comment = _split_comment(stripped)
    normalized_comment = _compact(comment)
    if not code and comment:
        return ConditionLine(
            line_no=line_no,
            kind="comment",
            raw=raw,
            indent=indent,
            comment=normalized_comment,
            normalized=normalized_comment,
        )
    if not code:
        return ConditionLine(line_no=line_no, kind="blank", raw=raw, indent=indent)

    clause = _split_if_clause(code)
    if clause is not None:
        keyword, expression, inline_body = clause
        normalized, parse_error = _normalize_expression(expression)
        calls, lookbacks = _metadata_from_expression(expression, line_no)
        inline_normalized, inline_kind, inline_error, inline_calls, inline_lookbacks = (
            _parse_inline_body(inline_body, line_no)
        )
        return ConditionLine(
            line_no=line_no,
            kind="clause",
            raw=raw,
            indent=indent,
            keyword=keyword,
            expression=expression,
            normalized=normalized,
            inline_body=inline_body,
            inline_normalized=inline_normalized,
            inline_kind=inline_kind,
            comment=normalized_comment,
            parse_error=_join_errors(parse_error, inline_error),
            called_functions=_unique((*calls, *inline_calls)),
            numeric_lookbacks=(*lookbacks, *inline_lookbacks),
        )

    assignment = _parse_assignment(code, line_no)
    if assignment is not None:
        target, normalized, calls, lookbacks, parse_error = assignment
        return ConditionLine(
            line_no=line_no,
            kind="assignment",
            raw=raw,
            indent=indent,
            target=target,
            expression=code,
            normalized=normalized,
            comment=normalized_comment,
            parse_error=parse_error,
            called_functions=calls,
            numeric_lookbacks=lookbacks,
        )

    calls, lookbacks = _metadata_from_statement(code, line_no)
    return ConditionLine(
        line_no=line_no,
        kind="unknown",
        raw=raw,
        indent=indent,
        expression=code,
        normalized=_compact(code),
        comment=normalized_comment,
        called_functions=calls,
        numeric_lookbacks=lookbacks,
    )


def _indent_width(raw: str) -> int:
    prefix = raw[: len(raw) - len(raw.lstrip(" \t"))]
    return len(prefix.expandtabs(4))


def _split_comment(text: str) -> tuple[str, str]:
    try:
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type == tokenize.COMMENT:
                return text[: token.start[1]].rstrip(), token.string.strip()
    except tokenize.TokenError:
        return text.rstrip(), ""
    return text.rstrip(), ""


def _split_if_clause(code: str) -> Optional[tuple[str, str, str]]:
    parts = code.split(maxsplit=1)
    if len(parts) != 2 or parts[0] not in {"if", "elif"}:
        return None
    keyword, rest = parts
    colon_index = _top_level_colon_index(rest)
    if colon_index is None:
        return None
    expression = rest[:colon_index].strip()
    inline_body = rest[colon_index + 1 :].strip()
    if not expression:
        return None
    return keyword, expression, inline_body


def _top_level_colon_index(text: str) -> Optional[int]:
    depth = 0
    try:
        tokens = tokenize.generate_tokens(io.StringIO(text).readline)
        for token in tokens:
            if token.type == tokenize.OP:
                if token.string in "([{":
                    depth += 1
                elif token.string in ")]}":
                    depth = max(0, depth - 1)
                elif token.string == ":" and depth == 0:
                    return token.start[1]
    except tokenize.TokenError:
        return text.find(":") if ":" in text else None
    return None


def _parse_inline_body(
    inline_body: str,
    line_no: int,
) -> tuple[str, str, str, tuple[str, ...], tuple[NumericLookback, ...]]:
    if not inline_body:
        return "", "", "", (), ()
    assignment = _parse_assignment(inline_body, line_no)
    if assignment is not None:
        _target, normalized, calls, lookbacks, parse_error = assignment
        return normalized, "assignment", parse_error, calls, lookbacks
    normalized, parse_error = _normalize_statement(inline_body)
    calls, lookbacks = _metadata_from_statement(inline_body, line_no)
    return normalized, "unknown", parse_error, calls, lookbacks


def _parse_assignment(
    code: str,
    line_no: int,
) -> Optional[
    tuple[str, str, tuple[str, ...], tuple[NumericLookback, ...], str]
]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    if len(tree.body) != 1:
        return None
    stmt = tree.body[0]
    value: ast.AST | None = None
    targets: list[ast.AST] = []
    if isinstance(stmt, ast.Assign):
        value = stmt.value
        targets = list(stmt.targets)
    elif isinstance(stmt, ast.AnnAssign):
        value = stmt.value
        targets = [stmt.target]
    elif isinstance(stmt, ast.AugAssign):
        value = stmt.value
        targets = [stmt.target]
    else:
        return None
    target = ",".join(_safe_unparse(item) for item in targets)
    calls, lookbacks = _metadata_from_node(value, line_no) if value is not None else ((), ())
    normalized, parse_error = _normalize_statement(code)
    return target, normalized, calls, lookbacks, parse_error


def _normalize_expression(expression: str) -> tuple[str, str]:
    try:
        node = ast.parse(expression, mode="eval").body
    except SyntaxError as exc:
        return _compact(expression), f"line expression syntax: {exc.msg}"
    return _safe_unparse(node), ""


def _normalize_statement(statement: str) -> tuple[str, str]:
    try:
        tree = ast.parse(statement)
    except SyntaxError as exc:
        return _compact(statement), f"line statement syntax: {exc.msg}"
    return "; ".join(_safe_unparse(stmt) for stmt in tree.body), ""


def _metadata_from_expression(
    expression: str,
    line_no: int,
) -> tuple[tuple[str, ...], tuple[NumericLookback, ...]]:
    try:
        node = ast.parse(expression, mode="eval").body
    except SyntaxError:
        return (), ()
    return _metadata_from_node(node, line_no)


def _metadata_from_statement(
    statement: str,
    line_no: int,
) -> tuple[tuple[str, ...], tuple[NumericLookback, ...]]:
    try:
        tree = ast.parse(statement)
    except SyntaxError:
        return (), ()
    return _metadata_from_node(tree, line_no)


def _metadata_from_node(
    node: ast.AST | None,
    line_no: int,
) -> tuple[tuple[str, ...], tuple[NumericLookback, ...]]:
    if node is None:
        return (), ()
    visitor = _CallMetadataVisitor(line_no)
    visitor.visit(node)
    return _unique(visitor.called_functions), tuple(visitor.numeric_lookbacks)


class _CallMetadataVisitor(ast.NodeVisitor):
    def __init__(self, line_no: int) -> None:
        self._line_no = line_no
        self.called_functions: list[str] = []
        self.numeric_lookbacks: list[NumericLookback] = []

    def visit_Call(self, node: ast.Call) -> Any:  # noqa: N802
        function = _call_name(node.func)
        if function:
            self.called_functions.append(function)
            for index, arg in enumerate(node.args):
                value = _literal_number(arg)
                if value is not None:
                    self.numeric_lookbacks.append(
                        NumericLookback(
                            line_no=self._line_no,
                            function=function,
                            argument_index=index,
                            value=value,
                            source=_safe_unparse(arg),
                        )
                    )
        self.generic_visit(node)


def _call_name(func: ast.AST) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return _safe_unparse(func).replace(" ", "")
    return _safe_unparse(func).replace(" ", "")


def _literal_number(node: ast.AST) -> int | float | None:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool):
            return None
        if isinstance(node.value, int):
            return node.value
        if isinstance(node.value, float):
            return node.value
        return None
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _literal_number(node.operand)
        if value is None:
            return None
        return value if isinstance(node.op, ast.UAdd) else -value
    return None


def _safe_unparse(node: ast.AST) -> str:
    try:
        return ast.unparse(node).strip()
    except Exception:  # noqa: BLE001
        return ast.dump(node, annotate_fields=True, include_attributes=False)


def _compact(text: str) -> str:
    return " ".join(str(text or "").strip().split())


def _join_errors(*errors: str) -> str:
    return "; ".join(error for error in errors if error)


def _unique(items: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return tuple(out)


def _canonical_line(line: ConditionLine) -> str:
    parts = [line.kind, f"indent={line.indent}"]
    if line.keyword:
        parts.append(f"keyword={line.keyword}")
    if line.target:
        parts.append(f"target={line.target}")
    if line.normalized:
        parts.append(f"text={line.normalized}")
    if line.inline_normalized:
        parts.append(f"inline={line.inline_kind}:{line.inline_normalized}")
    elif line.inline_kind:
        parts.append(f"inline={line.inline_kind}")
    if line.comment:
        parts.append(f"comment={line.comment}")
    if line.parse_error:
        parts.append(f"parse_error={line.parse_error}")
    return "|".join(parts)


def _complexity(
    lines: Sequence[ConditionLine],
    called_functions: Sequence[str],
    numeric_lookbacks: Sequence[NumericLookback],
) -> ConditionComplexity:
    assignment_count = sum(1 for line in lines if line.kind == "assignment")
    assignment_count += sum(1 for line in lines if line.inline_kind == "assignment")
    unknown_count = sum(1 for line in lines if line.kind == "unknown")
    unknown_count += sum(1 for line in lines if line.inline_kind == "unknown")
    max_lookback = max((abs(float(item.value)) for item in numeric_lookbacks), default=0.0)
    return ConditionComplexity(
        total_lines=len(lines),
        assignment_count=assignment_count,
        clause_count=sum(1 for line in lines if line.kind == "clause"),
        comment_count=sum(1 for line in lines if line.kind == "comment"),
        blank_count=sum(1 for line in lines if line.kind == "blank"),
        unknown_line_count=unknown_count,
        function_call_count=sum(len(line.called_functions) for line in lines),
        unique_function_count=len(called_functions),
        numeric_lookback_count=len(numeric_lookbacks),
        max_numeric_lookback=max_lookback,
    )


def _estimate_work(parsed: ConditionAst) -> float:
    lookback_sum = sum(abs(float(item.value)) for item in parsed.numeric_lookbacks)
    return round(float(parsed.complexity.clause_count) + lookback_sum / 100.0, 6)
