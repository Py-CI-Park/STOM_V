"""Offline deterministic denoising primitives for canonical condition sources."""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

from ai_strategy_loop.revision.condition_ast import ConditionAst, parse_condition_source

MASK_TOKEN = "__CONDITION_DENOISING_MASK__"

_GUARD_KINDS = {"if", "elif", "clause", "guard", "guard_clause"}
_ASSIGNMENT_KINDS = {"assignment", "assign"}
_NUMERIC_RE = re.compile(r"(?<![\w.])[-+]?(?:\d+\.\d+|\d+|\.\d+)(?![\w.])")
_GUARD_RE = re.compile(r"^(?P<indent>\s*)(?P<keyword>if|elif)\b.*:\s*(?:#.*)?$")
_MISSING = object()


@dataclass(frozen=True)
class DenoisingConfig:
    seed: int = 0
    numeric_delta: float = 1.0
    mask_token: str = MASK_TOKEN
    max_experiment_cases: int = 128


@dataclass(frozen=True)
class DenoisingReceipt:
    seed: int
    config_hash: str
    config_items: tuple[tuple[str, str], ...]
    adoption_authority: bool = False
    authority_scope: str = "none"
    evidence_scope: tuple[str, ...] = ("canonical_condition_nodes",)


@dataclass(frozen=True)
class CorruptionTarget:
    clause_index: int
    node_index: int
    line_number: int
    literal_index: int | None = None


@dataclass(frozen=True)
class CorruptionResult:
    ok: bool
    operator: str
    source: str
    ast: ConditionAst | None
    target: CorruptionTarget | None
    reason: str
    receipt: DenoisingReceipt
    original_literal: str | None = None
    new_literal: str | None = None
    absolute_delta: float | None = None


@dataclass(frozen=True)
class RepairAction:
    kind: str
    clause_index: int
    line_number: int


@dataclass(frozen=True)
class RepairResult:
    ok: bool
    source: str
    ast: ConditionAst | None
    actions: tuple[RepairAction, ...]
    reason: str
    receipt: DenoisingReceipt


@dataclass(frozen=True)
class EvaluationSummary:
    canonical_equal: bool
    syntax_valid: bool
    static_valid: bool
    complexity_delta: int
    clean_canonical_hash: str
    candidate_canonical_hash: str
    receipt: DenoisingReceipt


@dataclass(frozen=True)
class ShuffledTemplateResult:
    ok: bool
    source: str
    ast: ConditionAst | None
    order: tuple[int, ...]
    reason: str
    receipt: DenoisingReceipt


@dataclass(frozen=True)
class ExperimentCase:
    source_index: int
    operator: str
    clean_template_exact: bool
    shuffled_template_exact: bool
    clean_repair_reason: str
    shuffled_repair_reason: str


@dataclass(frozen=True)
class ExperimentSummary:
    case_count: int
    clean_template_exact_repairs: int
    shuffled_template_exact_repairs: int
    clean_template_exact_repair_rate: float
    shuffled_template_exact_repair_rate: float
    cases: tuple[ExperimentCase, ...]
    receipt: DenoisingReceipt


@dataclass(frozen=True)
class _NodeView:
    index: int
    kind: str
    line_number: int
    text: str
    canonical_text: str
    called_functions: tuple[str, ...]


@dataclass(frozen=True)
class _SourceView:
    source: str
    lines: tuple[str, ...]
    final_newline: bool
    nodes: tuple[_NodeView, ...]


@dataclass(frozen=True)
class _GuardBlock:
    clause_index: int
    header: _NodeView
    body: _NodeView

    @property
    def header_line_index(self) -> int:
        return self.header.line_number - 1

    @property
    def body_line_index(self) -> int:
        return self.body.line_number - 1

    @property
    def header_keyword(self) -> str:
        match = _GUARD_RE.match(self.header.text)
        return match.group("keyword") if match else self.header.kind

    @property
    def key(self) -> str:
        return f"{self.header.canonical_text}\n{self.body.canonical_text}"


def mask_one_clause(
    condition: ConditionAst,
    *,
    seed: int = 0,
    clause_index: int | None = None,
    mask_token: str = MASK_TOKEN,
) -> CorruptionResult:
    """Replace one guard condition with a deterministic syntax-level mask token."""

    receipt = _receipt(
        seed,
        {
            "operator": "mask_one_clause",
            "clause_index": clause_index,
            "mask_token": mask_token,
        },
    )
    try:
        view = _source_view(condition)
        blocks = _guard_blocks(view)
        selected = _select_block(blocks, seed, clause_index)
        lines = list(view.lines)
        lines[selected.header_line_index] = _masked_guard_line(selected.header.text, mask_token)
        source = _join_lines(lines, view.final_newline)
        parsed = _parse(source)
        if parsed is None:
            return _failed_corruption("mask_one_clause", view.source, receipt, "masked_source_not_parseable")
        return CorruptionResult(
            ok=True,
            operator="mask_one_clause",
            source=source,
            ast=parsed,
            target=_target(selected),
            reason="ok",
            receipt=receipt,
        )
    except ValueError as exc:
        source = _source_or_empty(condition)
        return _failed_corruption("mask_one_clause", source, receipt, str(exc))


def perturb_numeric_threshold(
    condition: ConditionAst,
    *,
    max_delta: float,
    seed: int = 0,
    clause_index: int | None = None,
    literal_index: int | None = None,
) -> CorruptionResult:
    """Move one declared numeric literal by no more than ``max_delta``."""

    receipt = _receipt(
        seed,
        {
            "operator": "perturb_numeric_threshold",
            "clause_index": clause_index,
            "literal_index": literal_index,
            "max_delta": max_delta,
        },
    )
    if not _finite_positive(max_delta):
        return _failed_corruption(
            "perturb_numeric_threshold",
            _source_or_empty(condition),
            receipt,
            "max_delta_must_be_finite_positive",
        )
    try:
        view = _source_view(condition)
        blocks = _guard_blocks(view)
        block = _select_block(blocks, seed, clause_index)
        if block.header.called_functions:
            raise ValueError("selected_clause_contains_function_call_literals")
        matches = tuple(_NUMERIC_RE.finditer(block.header.text))
        if not matches:
            raise ValueError("selected_clause_has_no_numeric_literal")
        number_count = _declared_number_count(block.header)
        if number_count == 0:
            raise ValueError("selected_clause_has_no_declared_numeric_literal")
        if len(matches) > number_count:
            matches = matches[:number_count]
        chosen_literal_index = _select_index(len(matches), seed, literal_index, "literal_index")
        match = matches[chosen_literal_index]
        original_literal = match.group(0)
        new_literal, absolute_delta = _perturbed_literal(original_literal, max_delta, seed)
        line = block.header.text[: match.start()] + new_literal + block.header.text[match.end() :]
        lines = list(view.lines)
        lines[block.header_line_index] = line
        source = _join_lines(lines, view.final_newline)
        parsed = _parse(source)
        if parsed is None:
            return _failed_corruption("perturb_numeric_threshold", view.source, receipt, "perturbed_source_not_parseable")
        return CorruptionResult(
            ok=True,
            operator="perturb_numeric_threshold",
            source=source,
            ast=parsed,
            target=_target(block, chosen_literal_index),
            reason="ok",
            receipt=receipt,
            original_literal=original_literal,
            new_literal=new_literal,
            absolute_delta=absolute_delta,
        )
    except ValueError as exc:
        source = _source_or_empty(condition)
        return _failed_corruption("perturb_numeric_threshold", source, receipt, str(exc))


def reorder_independent_consecutive_guards(
    condition: ConditionAst,
    *,
    seed: int = 0,
    first_clause_index: int | None = None,
) -> CorruptionResult:
    """Swap only adjacent ``elif`` guard blocks with identical pure body actions."""

    receipt = _receipt(
        seed,
        {
            "operator": "reorder_independent_consecutive_guards",
            "first_clause_index": first_clause_index,
        },
    )
    try:
        view = _source_view(condition)
        blocks = _guard_blocks(view)
        candidates = tuple(i for i in range(len(blocks) - 1) if _can_reorder(blocks[i], blocks[i + 1]))
        if first_clause_index is not None:
            if first_clause_index not in candidates:
                raise ValueError("selected_pair_is_not_independent_consecutive_elif_guards")
            pair_index = first_clause_index
        else:
            if not candidates:
                raise ValueError("no_independent_consecutive_elif_guard_pair")
            pair_index = candidates[_select_index(len(candidates), seed, None, "pair_index")]
        left = blocks[pair_index]
        right = blocks[pair_index + 1]
        lines = list(view.lines)
        left_chunk = lines[left.header_line_index : left.body_line_index + 1]
        right_chunk = lines[right.header_line_index : right.body_line_index + 1]
        lines[left.header_line_index : right.body_line_index + 1] = right_chunk + left_chunk
        source = _join_lines(lines, view.final_newline)
        parsed = _parse(source)
        if parsed is None:
            return _failed_corruption(
                "reorder_independent_consecutive_guards",
                view.source,
                receipt,
                "reordered_source_not_parseable",
            )
        return CorruptionResult(
            ok=True,
            operator="reorder_independent_consecutive_guards",
            source=source,
            ast=parsed,
            target=_target(left),
            reason="ok",
            receipt=receipt,
        )
    except ValueError as exc:
        source = _source_or_empty(condition)
        return _failed_corruption("reorder_independent_consecutive_guards", source, receipt, str(exc))


def insert_exact_duplicate(
    condition: ConditionAst,
    *,
    seed: int = 0,
    clause_index: int | None = None,
) -> CorruptionResult:
    """Insert an exact adjacent duplicate of one guard block."""

    receipt = _receipt(
        seed,
        {
            "operator": "insert_exact_duplicate",
            "clause_index": clause_index,
        },
    )
    try:
        view = _source_view(condition)
        blocks = _guard_blocks(view)
        selected = _select_block(blocks, seed, clause_index)
        lines = list(view.lines)
        chunk = lines[selected.header_line_index : selected.body_line_index + 1]
        insert_at = selected.body_line_index + 1
        lines[insert_at:insert_at] = chunk
        source = _join_lines(lines, view.final_newline)
        parsed = _parse(source)
        if parsed is None:
            return _failed_corruption("insert_exact_duplicate", view.source, receipt, "duplicated_source_not_parseable")
        return CorruptionResult(
            ok=True,
            operator="insert_exact_duplicate",
            source=source,
            ast=parsed,
            target=_target(selected),
            reason="ok",
            receipt=receipt,
        )
    except ValueError as exc:
        source = _source_or_empty(condition)
        return _failed_corruption("insert_exact_duplicate", source, receipt, str(exc))


def repair_masked_and_duplicate(
    corrupted: ConditionAst,
    clean_template: ConditionAst,
    *,
    seed: int = 0,
    mask_token: str = MASK_TOKEN,
) -> RepairResult:
    """Repair only masked guards and exact duplicate guard blocks from a clean template."""

    receipt = _receipt(
        seed,
        {
            "operator": "repair_masked_and_duplicate",
            "mask_token": mask_token,
        },
        evidence_scope=("canonical_condition_nodes", "clean_template"),
    )
    try:
        corrupt_view = _source_view(corrupted)
        template_view = _source_view(clean_template)
        template_blocks = _guard_blocks(template_view)
        lines = list(corrupt_view.lines)
        actions: list[RepairAction] = []

        corrupt_blocks = _guard_blocks(corrupt_view)
        for block in corrupt_blocks:
            if mask_token not in block.header.text:
                continue
            if block.clause_index >= len(template_blocks):
                raise ValueError("masked_clause_has_no_clean_template_slot")
            template_block = template_blocks[block.clause_index]
            lines[block.header_line_index] = template_view.lines[template_block.header_line_index]
            actions.append(RepairAction("mask_replaced", block.clause_index, block.header.line_number))

        masked_source = _join_lines(lines, corrupt_view.final_newline)
        masked_ast = _parse(masked_source)
        if masked_ast is None:
            raise ValueError("mask_repair_not_parseable")

        dedup_view = _source_view(masked_ast)
        dedup_lines = list(dedup_view.lines)
        ranges = _duplicate_ranges(dedup_view, template_view)
        for block in ranges:
            actions.append(RepairAction("duplicate_removed", block.clause_index, block.header.line_number))
        for block in reversed(ranges):
            del dedup_lines[block.header_line_index : block.body_line_index + 1]

        repaired_source = _join_lines(dedup_lines, dedup_view.final_newline)
        repaired_ast = _parse(repaired_source)
        if repaired_ast is None:
            raise ValueError("duplicate_repair_not_parseable")
        reason = "ok" if actions else "no_repairable_mask_or_duplicate"
        return RepairResult(
            ok=bool(actions),
            source=repaired_source,
            ast=repaired_ast,
            actions=tuple(actions),
            reason=reason,
            receipt=receipt,
        )
    except ValueError as exc:
        source = _source_or_empty(corrupted)
        return RepairResult(False, source, None, (), str(exc), receipt)


def evaluate_repair(
    clean: ConditionAst,
    candidate: ConditionAst,
    *,
    syntax_valid: bool,
    static_valid: bool,
    seed: int = 0,
) -> EvaluationSummary:
    """Summarize caller-supplied validity flags and canonical equality."""

    receipt = _receipt(
        seed,
        {
            "operator": "evaluate_repair",
            "syntax_valid": syntax_valid,
            "static_valid": static_valid,
        },
    )
    clean_hash = _canonical_hash(clean)
    candidate_hash = _canonical_hash(candidate)
    return EvaluationSummary(
        canonical_equal=clean_hash == candidate_hash,
        syntax_valid=bool(syntax_valid),
        static_valid=bool(static_valid),
        complexity_delta=_complexity(candidate) - _complexity(clean),
        clean_canonical_hash=clean_hash,
        candidate_canonical_hash=candidate_hash,
        receipt=receipt,
    )


def shuffled_template_negative_control(
    clean_template: ConditionAst,
    *,
    seed: int = 0,
) -> ShuffledTemplateResult:
    """Build a deterministic shuffled clean-template control with no adoption authority."""

    receipt = _receipt(seed, {"operator": "shuffled_template_negative_control"})
    try:
        view = _source_view(clean_template)
        blocks = _guard_blocks(view)
        movable = [block for block in blocks if block.header_keyword == "elif"]
        if len(movable) < 2:
            raise ValueError("need_at_least_two_elif_guards_to_shuffle_template")
        order = _deranged_order(tuple(block.clause_index for block in movable), seed)
        by_index = {block.clause_index: block for block in blocks}
        lines = list(view.lines)
        chunks = {
            block.clause_index: lines[block.header_line_index : block.body_line_index + 1]
            for block in movable
        }
        for destination, source_index in zip((block.clause_index for block in movable), order):
            block = by_index[destination]
            lines[block.header_line_index : block.body_line_index + 1] = chunks[source_index]
        source = _join_lines(lines, view.final_newline)
        parsed = _parse(source)
        if parsed is None:
            raise ValueError("shuffled_template_not_parseable")
        return ShuffledTemplateResult(True, source, parsed, order, "ok", receipt)
    except ValueError as exc:
        source = _source_or_empty(clean_template)
        return ShuffledTemplateResult(False, source, None, (), str(exc), receipt)


def run_fixed_seed_experiment(
    clean_sources: Sequence[str],
    *,
    seed: int = 0,
    max_cases: int = 128,
) -> ExperimentSummary:
    """Run deterministic mask/duplicate repair checks against clean and shuffled templates."""

    receipt = _receipt(
        seed,
        {
            "operator": "run_fixed_seed_experiment",
            "max_cases": max_cases,
            "operators": "mask_one_clause,insert_exact_duplicate",
        },
        evidence_scope=("canonical_condition_nodes", "clean_template", "shuffled_template_control"),
    )
    if max_cases < 1:
        raise ValueError("max_cases_must_be_positive")

    cases: list[ExperimentCase] = []
    for source_index, source in enumerate(clean_sources):
        if len(cases) >= max_cases:
            break
        clean_ast = parse_condition_source(source)
        operator_specs = (
            ("mask_one_clause", mask_one_clause),
            ("insert_exact_duplicate", insert_exact_duplicate),
        )
        for operator_name, operator in operator_specs:
            if len(cases) >= max_cases:
                break
            case_seed = _derive_seed(seed, source_index, operator_name)
            kwargs: dict[str, Any] = {}
            if operator_name == "mask_one_clause":
                kwargs["clause_index"] = _preferred_mask_clause(clean_ast)
            corrupted = operator(clean_ast, seed=case_seed, **kwargs)
            if not corrupted.ok or corrupted.ast is None:
                cases.append(
                    ExperimentCase(source_index, operator_name, False, False, corrupted.reason, "not_run")
                )
                continue

            clean_repair = repair_masked_and_duplicate(corrupted.ast, clean_ast, seed=case_seed)
            clean_exact = clean_repair.ast is not None and _canonical_hash(clean_repair.ast) == _canonical_hash(clean_ast)

            shuffled = shuffled_template_negative_control(clean_ast, seed=_derive_seed(case_seed, "shuffle"))
            if shuffled.ok and shuffled.ast is not None:
                shuffled_repair = repair_masked_and_duplicate(corrupted.ast, shuffled.ast, seed=case_seed)
                shuffled_exact = shuffled_repair.ast is not None and _canonical_hash(shuffled_repair.ast) == _canonical_hash(clean_ast)
                shuffled_reason = shuffled_repair.reason
            else:
                shuffled_exact = False
                shuffled_reason = shuffled.reason

            cases.append(
                ExperimentCase(
                    source_index=source_index,
                    operator=operator_name,
                    clean_template_exact=clean_exact,
                    shuffled_template_exact=shuffled_exact,
                    clean_repair_reason=clean_repair.reason,
                    shuffled_repair_reason=shuffled_reason,
                )
            )

    clean_count = sum(1 for case in cases if case.clean_template_exact)
    shuffled_count = sum(1 for case in cases if case.shuffled_template_exact)
    case_count = len(cases)
    return ExperimentSummary(
        case_count=case_count,
        clean_template_exact_repairs=clean_count,
        shuffled_template_exact_repairs=shuffled_count,
        clean_template_exact_repair_rate=_rate(clean_count, case_count),
        shuffled_template_exact_repair_rate=_rate(shuffled_count, case_count),
        cases=tuple(cases),
        receipt=receipt,
    )


def _receipt(
    seed: int,
    config: Mapping[str, Any],
    *,
    evidence_scope: tuple[str, ...] = ("canonical_condition_nodes",),
) -> DenoisingReceipt:
    items = tuple((str(key), _stable_value(value)) for key, value in sorted(config.items()))
    payload = {
        "seed": int(seed),
        "config_items": items,
        "adoption_authority": False,
        "authority_scope": "none",
        "evidence_scope": evidence_scope,
    }
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return DenoisingReceipt(
        seed=int(seed),
        config_hash=hashlib.sha256(blob.encode("utf-8")).hexdigest(),
        config_items=items,
        adoption_authority=False,
        authority_scope="none",
        evidence_scope=evidence_scope,
    )


def _stable_value(value: Any) -> str:
    if value is None:
        return "None"
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, (tuple, list)):
        return json.dumps([_stable_value(item) for item in value], ensure_ascii=False, separators=(",", ":"))
    return str(value)


def _failed_corruption(operator: str, source: str, receipt: DenoisingReceipt, reason: str) -> CorruptionResult:
    return CorruptionResult(False, operator, source, None, None, reason, receipt)


def _parse(source: str) -> ConditionAst | None:
    try:
        return parse_condition_source(source)
    except Exception:
        return None


def _source_or_empty(condition: ConditionAst) -> str:
    try:
        return _source_text(condition)
    except ValueError:
        return ""


def _source_view(condition: ConditionAst) -> _SourceView:
    source = _source_text(condition)
    lines = tuple(source.splitlines())
    final_newline = source.endswith(("\n", "\r\n"))
    records = _node_records(condition)
    nodes: list[_NodeView] = []
    for index, record in enumerate(records):
        line_number = _line_number(record, index + 1)
        if line_number < 1 or line_number > len(lines):
            raise ValueError("node_line_number_out_of_source_range")
        text = _node_text(record)
        if not text:
            text = lines[line_number - 1]
        nodes.append(
            _NodeView(
                index=index,
                kind=_node_kind(record),
                line_number=line_number,
                text=text,
                canonical_text=_node_canonical_text(record, text),
                called_functions=_called_functions(record),
            )
        )
    if not nodes:
        raise ValueError("condition_ast_has_no_node_records")
    return _SourceView(source, lines, final_newline, tuple(nodes))


def _source_text(condition: ConditionAst) -> str:
    value = _read(condition, ("original_source", "source", "text", "raw_source"), _MISSING)
    if isinstance(value, str):
        return value
    value = _read(condition, ("canonical_text", "normalized_text", "canonical_source"), _MISSING)
    if isinstance(value, str):
        return value
    raise ValueError("condition_ast_has_no_source_text")


def _canonical_hash(condition: ConditionAst) -> str:
    value = _read(condition, ("canonical_sha256", "canonical_hash", "hash", "fingerprint"), _MISSING)
    if isinstance(value, str) and value:
        return value
    return hashlib.sha256(_canonical_text(condition).encode("utf-8")).hexdigest()


def _canonical_text(condition: ConditionAst) -> str:
    value = _read(condition, ("canonical_text", "normalized_text", "canonical_source"), _MISSING)
    if isinstance(value, str):
        return value
    raise ValueError("condition_ast_has_no_canonical_text")


def _complexity(condition: ConditionAst) -> int:
    value = _read(condition, ("complexity",), 0)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return int(value)
    if isinstance(value, Mapping):
        for key in ("total", "score", "nodes", "clauses"):
            item = value.get(key)
            if isinstance(item, (int, float)) and not isinstance(item, bool):
                return int(item)
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        data = to_dict()
        if isinstance(data, Mapping):
            return int(
                sum(
                    float(item)
                    for key, item in data.items()
                    if key != "max_numeric_lookback" and isinstance(item, (int, float)) and not isinstance(item, bool)
                )
            )
    total_lines = _read(value, ("total_lines",), _MISSING)
    clause_count = _read(value, ("clause_count",), _MISSING)
    assignment_count = _read(value, ("assignment_count",), _MISSING)
    unknown_line_count = _read(value, ("unknown_line_count",), _MISSING)
    function_call_count = _read(value, ("function_call_count",), _MISSING)
    numeric_lookback_count = _read(value, ("numeric_lookback_count",), _MISSING)
    parts = (
        total_lines,
        clause_count,
        assignment_count,
        unknown_line_count,
        function_call_count,
        numeric_lookback_count,
    )
    if any(part is not _MISSING for part in parts):
        return int(
            sum(
                float(part)
                for part in parts
                if isinstance(part, (int, float)) and not isinstance(part, bool)
            )
        )
    return 0


def _node_records(condition: ConditionAst) -> tuple[Any, ...]:
    records = _read(condition, ("nodes", "node_records", "records", "lines"), _MISSING)
    if records is _MISSING or isinstance(records, str):
        raise ValueError("condition_ast_has_no_node_records")
    try:
        return tuple(records)
    except TypeError as exc:
        raise ValueError("condition_ast_node_records_not_iterable") from exc


def _read(obj: Any, names: tuple[str, ...], default: Any) -> Any:
    for name in names:
        if isinstance(obj, Mapping) and name in obj:
            value = obj[name]
        elif hasattr(obj, name):
            value = getattr(obj, name)
        else:
            continue
        if callable(value):
            try:
                return value()
            except TypeError:
                return value
        return value
    return default


def _line_number(record: Any, default: int) -> int:
    value = _read(record, ("lineno", "line_number", "line_no", "line", "start_lineno"), default)
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("node_line_number_not_integer") from exc


def _node_kind(record: Any) -> str:
    value = _read(record, ("kind", "node_kind", "type"), "")
    return str(value).lower()


def _node_text(record: Any) -> str:
    value = _read(record, ("text", "raw_text", "source", "line_text"), "")
    return value if isinstance(value, str) else ""


def _node_canonical_text(record: Any, fallback: str) -> str:
    value = _read(record, ("canonical_text", "normalized_text", "canonical", "normalized"), "")
    if isinstance(value, str) and value:
        return value
    return "".join(fallback.split())


def _called_functions(record: Any) -> tuple[str, ...]:
    value = _read(record, ("called_functions", "calls", "function_calls"), ())
    if value is None or isinstance(value, str):
        return () if value is None else (value,)
    try:
        return tuple(str(item) for item in value)
    except TypeError:
        return ()


def _declared_number_count(node: _NodeView) -> int:
    # ConditionAst owns number extraction; this function only falls back to lexical spans
    # when the representation does not expose per-node numeric metadata.
    return max(1, len(tuple(_NUMERIC_RE.finditer(node.text))))


def _guard_blocks(view: _SourceView) -> tuple[_GuardBlock, ...]:
    blocks: list[_GuardBlock] = []
    for position, node in enumerate(view.nodes[:-1]):
        if node.kind not in _GUARD_KINDS:
            continue
        if _GUARD_RE.match(node.text) is None:
            continue
        body = view.nodes[position + 1]
        if body.line_number != node.line_number + 1:
            continue
        if body.kind not in _ASSIGNMENT_KINDS:
            continue
        blocks.append(_GuardBlock(len(blocks), node, body))
    if not blocks:
        raise ValueError("condition_has_no_guard_clause_blocks")
    return tuple(blocks)


def _select_block(blocks: Sequence[_GuardBlock], seed: int, clause_index: int | None) -> _GuardBlock:
    return blocks[_select_index(len(blocks), seed, clause_index, "clause_index")]


def _select_index(count: int, seed: int, selected: int | None, name: str) -> int:
    if count < 1:
        raise ValueError(f"no_available_{name}")
    if selected is not None:
        if selected < 0 or selected >= count:
            raise ValueError(f"{name}_out_of_range")
        return selected
    return random.Random(seed).randrange(count)


def _target(block: _GuardBlock, literal_index: int | None = None) -> CorruptionTarget:
    return CorruptionTarget(block.clause_index, block.header.index, block.header.line_number, literal_index)


def _masked_guard_line(line: str, mask_token: str) -> str:
    match = _GUARD_RE.match(line)
    if match is None:
        raise ValueError("guard_line_not_maskable")
    return f"{match.group('indent')}{match.group('keyword')} {mask_token}:"


def _finite_positive(value: float) -> bool:
    try:
        return math.isfinite(float(value)) and float(value) > 0
    except (TypeError, ValueError):
        return False


def _perturbed_literal(literal: str, max_delta: float, seed: int) -> tuple[str, float]:
    try:
        original = Decimal(literal)
        bound = Decimal(str(max_delta))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("numeric_literal_not_decimal") from exc
    rng = random.Random(seed)
    scale = Decimal(str(rng.random()))
    if scale == 0:
        scale = Decimal("0.5")
    amount = bound * scale
    if amount == 0:
        amount = bound
    sign = Decimal(-1 if rng.randrange(2) == 0 else 1)
    changed = original + sign * amount
    text = _format_decimal(changed)
    if Decimal(text) == original:
        changed = original + bound
        text = _format_decimal(changed)
    return text, float(abs(Decimal(text) - original))


def _format_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text == "-0":
        return "0"
    return text


def _can_reorder(left: _GuardBlock, right: _GuardBlock) -> bool:
    if left.header_keyword != "elif" or right.header_keyword != "elif":
        return False
    if left.body_line_index + 1 != right.header_line_index:
        return False
    if left.body.line_number != left.header.line_number + 1:
        return False
    if right.body.line_number != right.header.line_number + 1:
        return False
    if left.body.canonical_text != right.body.canonical_text:
        return False
    if _indent(left.body.text) != _indent(right.body.text):
        return False
    if left.header.called_functions or right.header.called_functions:
        return False
    if MASK_TOKEN in left.header.text or MASK_TOKEN in right.header.text:
        return False
    return True


def _indent(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]


def _duplicate_ranges(corrupt_view: _SourceView, template_view: _SourceView) -> tuple[_GuardBlock, ...]:
    corrupt_blocks = _guard_blocks(corrupt_view)
    template_blocks = _guard_blocks(template_view)
    template_counts = Counter(_block_raw_key(template_view, block) for block in template_blocks)
    seen: Counter[str] = Counter()
    ranges: list[_GuardBlock] = []
    previous_key: str | None = None
    for block in corrupt_blocks:
        key = _block_raw_key(corrupt_view, block)
        seen[key] += 1
        if key == previous_key and seen[key] > template_counts.get(key, 0):
            ranges.append(block)
        previous_key = key
    return tuple(ranges)


def _preferred_mask_clause(condition: ConditionAst) -> int | None:
    try:
        for block in _guard_blocks(_source_view(condition)):
            if block.header_keyword == "elif":
                return block.clause_index
    except ValueError:
        return None
    return None


def _block_raw_key(view: _SourceView, block: _GuardBlock) -> str:
    return "\n".join(view.lines[block.header_line_index : block.body_line_index + 1])


def _deranged_order(values: tuple[int, ...], seed: int) -> tuple[int, ...]:
    shuffled = list(values)
    random.Random(seed).shuffle(shuffled)
    if all(left != right for left, right in zip(values, shuffled)):
        return tuple(shuffled)
    if len(values) == 2:
        return (values[1], values[0])
    return tuple(values[1:] + values[:1])


def _derive_seed(seed: int, *parts: Any) -> int:
    blob = "|".join((str(seed), *(str(part) for part in parts)))
    return int(hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16], 16)


def _join_lines(lines: Sequence[str], final_newline: bool) -> str:
    return "\n".join(lines) + ("\n" if final_newline else "")


def _rate(numerator: int, denominator: int) -> float:
    return float(numerator / denominator) if denominator else 0.0
