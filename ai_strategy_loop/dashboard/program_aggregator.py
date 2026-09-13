"""ANA-07 — Program Fold/Control aggregator + A/B 거래 분해.

완료 Gate 계약:
- NO_TRADES 를 0% 성과로 합성하지 않는다 — cell 상태는 별도 어휘를 쓴다.
- missing Fold 하나면 program complete 가 될 수 없다.
- missing cell 을 0/PASS 로 대체하지 않는다.
- PnL 기반 candidate 선택은 별도 authority 없이 불가하다.
- 모든 q/posterior 는 multiplicity family 와 receipt 를 가진다.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


class AggregatorError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code


# cell 상태 어휘 — missing 은 절대 0/PASS 로 치환하지 않는다.
CELL_OBSERVED = "OBSERVED"
CELL_NO_TRADES = "NO_TRADES"      # 검증된 무거래 — 0% 성과가 아니라 별도 상태.
CELL_MISSING = "MISSING"          # 자료 부재.
CELL_NOT_EVALUABLE = "NOT_EVALUABLE"  # 실행 실패/불완전.


@dataclass(frozen=True, slots=True)
class ProgramManifest:
    """프로그램 입력 계약 — candidate/fold/control/family 정의."""

    program_id: str
    candidate_ids: tuple[str, ...]
    folds: tuple[str, ...]
    controls: tuple[str, ...] = ()
    families: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    development_rule: str = ""
    stop_rule: str = ""

    def manifest_sha256(self) -> str:
        blob = json.dumps(
            {
                "program_id": self.program_id,
                "candidates": list(self.candidate_ids),
                "folds": list(self.folds),
                "controls": list(self.controls),
                "families": {k: list(v) for k, v in sorted(self.families.items())},
                "development_rule": self.development_rule,
                "stop_rule": self.stop_rule,
            },
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        )
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class CellResult:
    """candidate×fold 셀 하나의 관측 상태."""

    candidate_id: str
    fold: str
    status: str  # CELL_*
    bundle_sha256: str | None = None
    reason: str = ""


def completion_matrix(
    manifest: ProgramManifest,
    cells: Sequence[CellResult],
) -> dict[str, Any]:
    """candidate×fold 완료 행렬 — missing cell 은 MISSING 으로 남는다."""
    seen = {(c.candidate_id, c.fold): c for c in cells}
    matrix: dict[str, dict[str, str]] = {}
    missing: list[str] = []
    for cand in manifest.candidate_ids:
        row: dict[str, str] = {}
        for fold in manifest.folds:
            cell = seen.get((cand, fold))
            row[fold] = cell.status if cell is not None else CELL_MISSING
            if row[fold] in (CELL_MISSING, CELL_NOT_EVALUABLE):
                missing.append(f"{cand}×{fold}")
        matrix[cand] = row
    complete = not missing and bool(manifest.candidate_ids) and bool(manifest.folds)
    return {
        "program_id": manifest.program_id,
        "manifest_sha256": manifest.manifest_sha256(),
        "matrix": matrix,
        "missing_cells": missing,
        "program_complete": complete,
        "complete_reason": None if complete else (
            "missing_or_unevaluable_cells" if missing else "empty_manifest"
        ),
    }


# ---------------------------------------------------------------------------
# A/B 거래 분해 — 공통/제거/신규. 키는 (symbol, entry_ts) 정본.
# ---------------------------------------------------------------------------
def trade_key_of(trade: Mapping[str, Any]) -> str:
    symbol = str(trade.get("name") or trade.get("symbol") or "")
    entry = str(trade.get("buy_time") or trade.get("entry_ts") or "")
    return f"{symbol}|{entry}"


def decompose_trades(
    a_trades: Sequence[Mapping[str, Any]],
    b_trades: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """A→B 거래 집합 분해: common/removed/new.

    같은 (symbol, entry) 키는 같은 거래로 본다. 결과는 결정론적 정렬.
    """
    a_keys = {trade_key_of(t) for t in a_trades}
    b_keys = {trade_key_of(t) for t in b_trades}
    common = sorted(a_keys & b_keys)
    removed = sorted(a_keys - b_keys)
    new = sorted(b_keys - a_keys)
    return {
        "key_basis": "symbol|entry_ts",
        "n_a": len(a_keys),
        "n_b": len(b_keys),
        "common": common,
        "removed": removed,
        "new": new,
        "n_common": len(common),
        "n_removed": len(removed),
        "n_new": len(new),
    }


def ab_eligible(
    side_a: Mapping[str, Any] | None,
    side_b: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """A/B 비교 적격성 — B5 admission 상태를 소비한다(재검증 아님)."""
    reasons: list[str] = []
    for tag, side in (("a", side_a), ("b", side_b)):
        if side is None:
            reasons.append(f"{tag}_unresolved")
        elif side.get("admitted") is not True:
            reasons.append(f"{tag}_not_admitted")
    return {
        "eligible": not reasons,
        "reasons": reasons,
    }


# ---------------------------------------------------------------------------
# Multiplicity ledger — q/posterior 는 family 와 receipt 를 반드시 가진다.
# ---------------------------------------------------------------------------
def multiplicity_ledger(
    manifest: ProgramManifest,
    hypotheses: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """검정한 가설 목록을 family 별로 묶고 q 방법론 receipt 를 부여한다."""
    entries = []
    for h in hypotheses:
        family = str(h.get("family") or "")
        if manifest.families and family not in manifest.families:
            raise AggregatorError("hypothesis_family_not_in_manifest", family)
        q = h.get("q")
        posterior = h.get("posterior")
        receipt = {
            "family": family,
            "q_method": h.get("q_method") if q is not None else None,
            "posterior_method": (
                h.get("posterior_method") if posterior is not None else None
            ),
        }
        if q is not None and not receipt["q_method"]:
            raise AggregatorError("q_without_method_receipt", str(h.get("hypothesis_id")))
        if posterior is not None and not receipt["posterior_method"]:
            raise AggregatorError(
                "posterior_without_method_receipt", str(h.get("hypothesis_id"))
            )
        entries.append({
            "hypothesis_id": h.get("hypothesis_id"),
            "family": family,
            "status": h.get("status", "tested"),
            "receipt": receipt,
        })
    return {
        "program_id": manifest.program_id,
        "n_tested": len(entries),
        "by_family": {
            fam: sum(1 for e in entries if e["family"] == fam)
            for fam in sorted({e["family"] for e in entries})
        },
        "entries": entries,
    }


def program_decision(
    manifest: ProgramManifest,
    matrix: Mapping[str, Any],
    *,
    authority: str,
    pnl_ranked: Sequence[str] = (),
) -> dict[str, Any]:
    """프로그램 판정 — 불완전 프로그램은 complete=False 로만 닫힌다.

    PnL 기반 선택은 별도 authority 없이 금지한다.
    """
    if not matrix.get("program_complete"):
        return {
            "complete": False,
            "reason": matrix.get("complete_reason"),
            "next_gate": "complete_all_folds",
        }
    if pnl_ranked and authority not in ("REVIEW_APPROVED", "FROZEN_OOS"):
        raise AggregatorError(
            "pnl_selection_requires_authority",
            f"authority={authority}",
        )
    return {
        "complete": True,
        "authority": authority,
        "selected": list(pnl_ranked),
        "next_gate": "economic_review",
    }
