"""CL-R06: bounded candidate-pool selector (todo 12).

Pure, deterministic, side-effect-free selection of ONE official candidate
from an exact 4-proposal round shape (2 lane='repair' + 2 lane='discovery').

This module does NOT run backtests, hit any DB/provider, or perform network
IO. It only reads proposal dicts and reuses ``cli.condition_fingerprint``
for semantic-duplicate detection and structural validity checks.

Proposal dict shape consumed here (see ASSUMPTIONS in the module docstring
of the accompanying test file for the authoritative list):

    {
        'candidate_id': str,               # lexicographic tiebreak key
        'lane': 'repair' | 'discovery',
        'family': str,                     # coarse family bucket for quota
        'expression': str,                 # buy-side boolean expression
        'novelty': float,                  # higher = more novel (default 0.0)
        'threshold_provenance': [...] | {...},  # provenance completeness input
    }

Provenance completeness is scored via
``cli.condition_fingerprint.ThresholdProvenance`` when the proposal carries
enough fields to construct one; otherwise it falls back to a simple
presence/field-count heuristic over ``threshold_provenance`` entries. Either
way the scoring is a pure function of the proposal dict.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Optional

from cli.condition_fingerprint import (
    FingerprintError,
    ThresholdProvenance,
    ast_fingerprint,
    validate_b_only,
)
from cli.condition_generator import (
    ApprovedBRegistryV2,
    candidate_ai_performance_eligible,
    reconcile_approved_b_features,
)

REQUIRED_PROPOSAL_COUNT = 4
REQUIRED_LANE_COUNTS = {'repair': 2, 'discovery': 2}
MAX_PER_FAMILY = 2

# Fields a ThresholdProvenance dataclass instance requires. When a proposal's
# 'threshold_provenance' mapping supplies all of them we build the real
# dataclass (which validates shape); otherwise we fall back to a heuristic
# completeness score so pool selection never raises on partial data.
_PROVENANCE_FIELDS = tuple(field.name for field in dataclasses.fields(ThresholdProvenance))


def _proposal_expression(proposal: dict) -> str:
    return str(proposal.get('expression') or '').strip()


def _proposal_timeframe(proposal: dict, default_timeframe: str) -> str:
    return str(proposal.get('timeframe') or default_timeframe)


def _fingerprint_of(proposal: dict, *, timeframe: str, methodology_version: str) -> str | None:
    expression = _proposal_expression(proposal)
    if not expression:
        return None
    try:
        return ast_fingerprint(expression, timeframe=timeframe, methodology_version=methodology_version)
    except FingerprintError:
        return None


def _is_structurally_valid(proposal: dict, *, timeframe: str) -> bool:
    expression = _proposal_expression(proposal)
    if not expression:
        return False
    reasons = validate_b_only(expression, timeframe=timeframe, kind='buy')
    return not reasons


def _provenance_completeness(proposal: dict) -> float:
    """Return a deterministic completeness score in [0, 1].

    Prefers constructing the real ``ThresholdProvenance`` dataclass (score 1.0
    on success, since the dataclass's own __post_init__ already enforces
    non-oos/full/validation fit roles and required fields). Falls back to a
    fraction-of-fields-present heuristic for partial/free-form provenance
    payloads so the ranking stays total (never raises).
    """

    raw = proposal.get('threshold_provenance')
    if isinstance(raw, dict):
        candidate_kwargs = {key: raw[key] for key in _PROVENANCE_FIELDS if key in raw}
        if len(candidate_kwargs) == len(_PROVENANCE_FIELDS):
            try:
                ThresholdProvenance(**candidate_kwargs)
                return 1.0
            except (TypeError, ValueError):
                pass
        if not _PROVENANCE_FIELDS:
            return 0.0
        return len(candidate_kwargs) / len(_PROVENANCE_FIELDS)
    if isinstance(raw, (list, tuple)):
        # A lineage list of provenance-like entries: completeness scales with
        # how many non-empty entries are present, capped at 1.0.
        non_empty = sum(1 for item in raw if item)
        return min(1.0, non_empty / max(1, MAX_PER_FAMILY))
    return 0.0


def _novelty_of(proposal: dict) -> float:
    novelty = proposal.get('novelty')
    if isinstance(novelty, (int, float)):
        return float(novelty)
    if isinstance(novelty, dict):
        score = novelty.get('score')
        if isinstance(score, (int, float)):
            return float(score)
    return 0.0


def _sort_key(entry: dict) -> tuple:
    # Higher validity, provenance completeness, and novelty rank first;
    # descending numeric fields are negated so a plain ascending sort works.
    # candidate_id breaks remaining ties lexicographically (ascending).
    return (
        0 if entry['valid'] else 1,
        -entry['provenance_completeness'],
        -entry['novelty'],
        str(entry['proposal'].get('candidate_id') or ''),
    )


def select_official_candidate(
    proposals: list[dict],
    *,
    timeframe: str,
    methodology_version: str,
) -> dict:
    """Select exactly one official candidate from a 4-proposal round.

    Returns {'selected': dict | None, 'rejected': [...], 'pool_blockers': [...]}.
    Never mutates the input list; never calls any evaluator/provider/DB.
    """

    pool_blockers: list[str] = []
    proposals = list(proposals or [])

    if len(proposals) != REQUIRED_PROPOSAL_COUNT:
        pool_blockers.append(
            f'wrong_proposal_count:expected_{REQUIRED_PROPOSAL_COUNT}_got_{len(proposals)}'
        )

    lane_counts: dict[str, int] = {}
    for proposal in proposals:
        lane = proposal.get('lane')
        lane_counts[lane] = lane_counts.get(lane, 0) + 1
    for lane, required in REQUIRED_LANE_COUNTS.items():
        if lane_counts.get(lane, 0) != required:
            pool_blockers.append(
                f'wrong_lane_count:{lane}:expected_{required}_got_{lane_counts.get(lane, 0)}'
            )
    unexpected_lanes = sorted(set(lane_counts) - set(REQUIRED_LANE_COUNTS))
    for lane in unexpected_lanes:
        pool_blockers.append(f'unexpected_lane:{lane}')

    # family over-quota check (applies regardless of count/lane blockers so
    # the report is maximally informative to the caller).
    family_counts: dict[str, int] = {}
    for proposal in proposals:
        family = proposal.get('family')
        if family is None:
            continue
        family_counts[family] = family_counts.get(family, 0) + 1
    family_over_quota = sorted(
        family for family, count in family_counts.items() if count > MAX_PER_FAMILY
    )
    for family in family_over_quota:
        pool_blockers.append(f'family_over_quota:{family}')

    # semantic-duplicate check via ast_fingerprint on the buy expression.
    fingerprint_to_ids: dict[str, list[str]] = {}
    entries: list[dict] = []
    for index, proposal in enumerate(proposals):
        candidate_timeframe = _proposal_timeframe(proposal, timeframe)
        fingerprint = _fingerprint_of(
            proposal, timeframe=candidate_timeframe, methodology_version=methodology_version,
        )
        candidate_id = str(proposal.get('candidate_id') or f'__unindexed_{index}')
        if fingerprint is not None:
            fingerprint_to_ids.setdefault(fingerprint, []).append(candidate_id)
        entries.append({
            'proposal': proposal,
            'candidate_id': candidate_id,
            'fingerprint': fingerprint,
            'valid': _is_structurally_valid(proposal, timeframe=candidate_timeframe),
            'provenance_completeness': _provenance_completeness(proposal),
            'novelty': _novelty_of(proposal),
        })

    duplicate_fingerprints = sorted(
        fingerprint for fingerprint, ids in fingerprint_to_ids.items() if len(ids) > 1
    )
    duplicate_candidate_ids: set[str] = set()
    for fingerprint in duplicate_fingerprints:
        pool_blockers.append(f'semantic_duplicate:{fingerprint}')
        duplicate_candidate_ids.update(fingerprint_to_ids[fingerprint])

    rejected: list[dict] = []
    if pool_blockers:
        for entry in entries:
            reasons = list(pool_blockers)
            rejected.append({'candidate': entry['proposal'], 'reasons': reasons})
        return {'selected': None, 'rejected': rejected, 'pool_blockers': pool_blockers}

    # Round shape is valid: rank deterministically and select exactly one.
    ranked = sorted(entries, key=_sort_key)
    winner = ranked[0]

    # G003 CL-R06 review fix: a structurally-invalid top rank must never be
    # promoted to official — an all-invalid round should spend zero official
    # quota rather than crown the "least-bad" invalid candidate.
    if not winner['valid']:
        pool_blockers.append('no_structurally_valid_candidate')
        for entry in ranked:
            reasons = list(pool_blockers)
            if not entry['valid']:
                reasons.append('not_structurally_valid')
            rejected.append({'candidate': entry['proposal'], 'reasons': reasons})
        return {'selected': None, 'rejected': rejected, 'pool_blockers': pool_blockers}

    selected = winner['proposal']

    for entry in ranked[1:]:
        reasons = []
        if not entry['valid']:
            reasons.append('not_structurally_valid')
        if entry['provenance_completeness'] < winner['provenance_completeness']:
            reasons.append('lower_provenance_completeness')
        if entry['novelty'] < winner['novelty']:
            reasons.append('lower_novelty')
        if not reasons:
            reasons.append('lost_candidate_id_tiebreak')
        rejected.append({'candidate': entry['proposal'], 'reasons': reasons})

    return {'selected': selected, 'rejected': rejected, 'pool_blockers': []}


# ===================================================================
# DR-04 -- final-owner lifecycle additions (additive, default-driven by the
#   caller). `select_official_candidate` above is UNCHANGED (still the single
#   selection owner, byte-identical signature/behavior); everything below is
#   a thin, opt-in pre-selection pipeline that narrows the round BEFORE
#   delegating the actual pick to the unchanged function.
# ===================================================================


@dataclasses.dataclass
class RunWideDedupArchive:
    """In-memory, run-scoped fingerprint archive (no I/O, no DB, caller-owned)."""

    ast_fingerprints: set = dataclasses.field(default_factory=set)
    rowset_fingerprints: set = dataclasses.field(default_factory=set)


def new_run_wide_dedup_archive() -> RunWideDedupArchive:
    return RunWideDedupArchive()


def check_run_wide_duplicate(
    archive: RunWideDedupArchive,
    *,
    ast_fingerprint: Optional[str] = None,
    rowset_fingerprint: Optional[str] = None,
) -> list[str]:
    """Return reason codes when either fingerprint already exists in `archive`.

    Pure read -- never mutates `archive`. Duplicates found here must be
    rejected BEFORE any evaluation budget is spent (see
    `select_official_candidate_v2` / controller.loop DR-04 wiring).
    """

    reasons: list[str] = []
    if ast_fingerprint and ast_fingerprint in archive.ast_fingerprints:
        reasons.append(f'run_wide_ast_duplicate:{ast_fingerprint}')
    if rowset_fingerprint and rowset_fingerprint in archive.rowset_fingerprints:
        reasons.append(f'run_wide_rowset_duplicate:{rowset_fingerprint}')
    return reasons


def register_run_wide_fingerprints(
    archive: RunWideDedupArchive,
    *,
    ast_fingerprint: Optional[str] = None,
    rowset_fingerprint: Optional[str] = None,
) -> None:
    """Record fingerprints as seen. Callers register only ACCEPTED lineage
    (e.g. the round's official selection), never rejected/duplicate rounds --
    otherwise a rejected round would poison the archive for future rounds.
    """

    if ast_fingerprint:
        archive.ast_fingerprints.add(ast_fingerprint)
    if rowset_fingerprint:
        archive.rowset_fingerprints.add(rowset_fingerprint)


@dataclasses.dataclass(frozen=True)
class SeedPlan:
    """DR-04 SeedPlan -- ``fresh`` mode reads no seed body and earns zero credit."""

    schema: int
    mode: str
    source: str
    buy_body: Optional[str]
    sell_body: Optional[str]
    body_consumed: bool
    selected_before_results: bool
    seed_credit: int = 0


def fresh_seed_plan() -> SeedPlan:
    """A fresh-mode SeedPlan: no seed body is read, body_consumed=False, credit=0."""

    return SeedPlan(
        schema=2,
        mode='fresh',
        source='none',
        buy_body=None,
        sell_body=None,
        body_consumed=False,
        selected_before_results=True,
        seed_credit=0,
    )


MAX_PER_COVERAGE_BUCKET = 2


def _coverage_bucket_of(proposal: dict) -> Optional[str]:
    keys = proposal.get('coverage_bucket_keys')
    if isinstance(keys, (list, tuple)) and keys:
        return str(keys[0])
    gap_id = proposal.get('coverage_gap_id')
    return str(gap_id) if gap_id else None


def apply_coverage_quota_before_selection(proposals: list[dict]) -> tuple[list[dict], list[str]]:
    """Reject proposals over `MAX_PER_COVERAGE_BUCKET`, applied BEFORE selection.

    Returns (kept_proposals, blocker_reason_codes). Proposals without a
    coverage-bucket key are always kept -- the quota only bounds labeled
    discovery-lane coverage buckets, never the whole round.
    """

    bucket_counts: dict[str, int] = {}
    for proposal in proposals:
        bucket = _coverage_bucket_of(proposal)
        if bucket is None:
            continue
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
    over_quota = sorted(
        bucket for bucket, count in bucket_counts.items() if count > MAX_PER_COVERAGE_BUCKET
    )
    if not over_quota:
        return list(proposals), []
    reasons = [f'coverage_bucket_over_quota:{bucket}' for bucket in over_quota]
    kept: list[dict] = []
    seen_bucket_counts: dict[str, int] = {}
    for proposal in proposals:
        bucket = _coverage_bucket_of(proposal)
        if bucket is None:
            kept.append(proposal)
            continue
        seen_bucket_counts[bucket] = seen_bucket_counts.get(bucket, 0) + 1
        if seen_bucket_counts[bucket] <= MAX_PER_COVERAGE_BUCKET:
            kept.append(proposal)
    return kept, reasons


def select_official_candidate_v2(
    proposals: list[dict],
    *,
    timeframe: str,
    methodology_version: str,
    approved_b_registry: Optional[ApprovedBRegistryV2] = None,
    run_wide_archive: Optional[RunWideDedupArchive] = None,
    seed_plan: Optional[SeedPlan] = None,
) -> dict:
    """DR-04 final-owner wrapper.

    Pipeline: AI-performance-accounting classification (bullet 7) -> coverage
    quotas (bullet 5) -> approved-B registry reconciliation (bullet 8) ->
    run-wide AST/rowset dedup before any evaluation budget is spent (bullet
    4) -> the UNCHANGED ``select_official_candidate`` (still the single,
    final selection owner). Every extra check is opt-in: passing ``None`` for
    a keyword is a full no-op for that check, so callers that pass nothing
    but ``proposals``/``timeframe``/``methodology_version`` get exactly the
    same result as calling ``select_official_candidate`` directly.
    """

    working = list(proposals or [])
    pre_selection_blockers: list[str] = []

    # bullet 7 -- fallback/control-origin candidates never count toward AI
    # performance accounting. Tracked separately; NOT removed from the round
    # (removing them would corrupt the required lane shape).
    ai_performance_excluded = [
        str(proposal.get('candidate_id') or '')
        for proposal in working
        if not candidate_ai_performance_eligible(proposal)
    ]

    # bullet 5 -- coverage quotas BEFORE selection (family quota already lives
    # inside select_official_candidate; this adds the coverage-bucket axis).
    working, coverage_reasons = apply_coverage_quota_before_selection(working)
    pre_selection_blockers.extend(coverage_reasons)

    # bullet 8 -- approved-B registry reconciliation.
    if approved_b_registry is not None:
        registry_rejected_ids: set = set()
        for proposal in working:
            expression = str(proposal.get('expression') or '')
            candidate_timeframe = _proposal_timeframe(proposal, timeframe)
            reasons = reconcile_approved_b_features(
                expression, timeframe=candidate_timeframe, registry=approved_b_registry,
            )
            if reasons:
                candidate_id = str(proposal.get('candidate_id') or '')
                registry_rejected_ids.add(candidate_id)
                pre_selection_blockers.extend(f'{candidate_id}:{reason}' for reason in reasons)
        if registry_rejected_ids:
            working = [
                proposal for proposal in working
                if str(proposal.get('candidate_id') or '') not in registry_rejected_ids
            ]

    # bullet 4 -- run-wide AST/rowset dedup BEFORE evaluation budget is spent:
    # anything already registered in `run_wide_archive` is dropped from this
    # round entirely (it must never reach selection).
    if run_wide_archive is not None:
        duplicate_ids: set = set()
        for proposal in working:
            candidate_id = str(proposal.get('candidate_id') or '')
            candidate_timeframe = _proposal_timeframe(proposal, timeframe)
            fingerprint = _fingerprint_of(
                proposal, timeframe=candidate_timeframe, methodology_version=methodology_version,
            )
            rowset_fp = proposal.get('rowset_fingerprint')
            dup_reasons = check_run_wide_duplicate(
                run_wide_archive, ast_fingerprint=fingerprint, rowset_fingerprint=rowset_fp,
            )
            if dup_reasons:
                duplicate_ids.add(candidate_id)
                pre_selection_blockers.extend(f'{candidate_id}:{reason}' for reason in dup_reasons)
        if duplicate_ids:
            working = [
                proposal for proposal in working
                if str(proposal.get('candidate_id') or '') not in duplicate_ids
            ]

    result = dict(select_official_candidate(
        working, timeframe=timeframe, methodology_version=methodology_version,
    ))
    result['pool_blockers'] = list(result.get('pool_blockers') or []) + pre_selection_blockers
    result['ai_performance_excluded_ids'] = ai_performance_excluded
    result['seed_plan'] = dataclasses.asdict(seed_plan) if seed_plan is not None else None

    # Register only the ACCEPTED winner so a rejected/duplicate round never
    # poisons the archive for future rounds.
    if run_wide_archive is not None and result.get('selected') is not None:
        selected = result['selected']
        candidate_timeframe = _proposal_timeframe(selected, timeframe)
        fingerprint = _fingerprint_of(
            selected, timeframe=candidate_timeframe, methodology_version=methodology_version,
        )
        register_run_wide_fingerprints(
            run_wide_archive,
            ast_fingerprint=fingerprint,
            rowset_fingerprint=selected.get('rowset_fingerprint'),
        )

    return result
