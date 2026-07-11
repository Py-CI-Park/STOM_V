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
from typing import Any

from cli.condition_fingerprint import (
    FingerprintError,
    ThresholdProvenance,
    ast_fingerprint,
    validate_b_only,
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
