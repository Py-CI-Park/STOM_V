"""absolute_niche_v1 — 절대 기준 + 니치 자격 OOS-blind 후보 선택기.

배경(docs/update_log/2026-06-11_evening_dev_ledger_and_next_queue.md §3):
seed_relative_v1(동결 선택기)는 "시드 MDD·거래수 대비" 기준이라 빈도·종목군·
시간창이 다른 독립 니치(F07·F10·min)에는 자가 기준이 없어 동결 불가.
absolute_niche_v1은 절대 기준 + 니치 자격(동결 후보와의 독립성)을 사전선언한다.

원칙:
  - 기존 선택기(sparse_positive_v1/yearly_sparse_robust_v1/seed_relative_v1)는
    무수정·병기한다. 신규 파일만 추가.
  - OOS-blind: oos_excluded=True 고정. 선택기는 train 지표만 소비.
  - niche_metrics는 **외부 주입**(N6/F1 실측치). 선택기는 계산하지 않는다.
  - corr/overlap 둘 다 None인 후보는 판정 불가 → 사유 명시 후 기각(침묵 통과 금지).
  - graded_score는 CandidateGeneration 기존 필드 재사용 — 중복 구현 금지.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Sequence, TypeAlias

from ._candidate_selection_core import CandidateGeneration

# ---------------------------------------------------------------------------
# 버전 상수
# ---------------------------------------------------------------------------

ABSOLUTE_NICHE_VERSION: Final = "absolute_niche_v1"

# ---------------------------------------------------------------------------
# 타입 별칭 (JSON 직렬화용)
# ---------------------------------------------------------------------------

JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | dict[str, "JsonValue"] | list["JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]

# ---------------------------------------------------------------------------
# NicheMetricEntry — 주입받는 단일 후보 니치 계측치
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class NicheMetricEntry:
    """gen_no별 니치 자격 측정치 (N6/F1 실측값 주입).

    corr_vs_frozen:      동결 후보와의 일별 수익 상관계수 (None이면 미측정).
    time_bucket_overlap: 진입 시간버킷 비중첩 여부 False=겹침, True=비중첩 (None이면 미측정).
    """

    corr_vs_frozen: float | None
    time_bucket_overlap: bool | None


# ---------------------------------------------------------------------------
# 임계값 dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AbsoluteNicheThresholds:
    """absolute_niche_v1 적격 기준 (스펙 §3 기본값 고정).

    profit > 0:              총 손익 양수
    min_positive_years:      거래 있는 연도 중 흑자 연도 수 ≥ 2 (P2 연도 일관성)
    max_mdd:                 MDD ≤ 20.0 (절대 상한)
    min_trade_count:         총 거래 ≥ 50
    min_payoff_ratio:        payoff_ratio ≥ 1.05
    max_corr_vs_frozen:      동결 후보와 일별 상관 < 0.5 (니치 자격 OR 분기 기준)
    """

    min_positive_years: int = 2
    max_mdd: float = 20.0
    min_trade_count: int = 50
    min_payoff_ratio: float = 1.05
    max_corr_vs_frozen: float = 0.5  # 상관 < 이 값이면 니치 자격


DEFAULT_ABSOLUTE_NICHE_THRESHOLDS: Final = AbsoluteNicheThresholds()

# ---------------------------------------------------------------------------
# 결과 dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AbsoluteNicheEligible:
    gen_no: int
    graded_score: float
    niche_metric: NicheMetricEntry | None


@dataclass(frozen=True, slots=True)
class AbsoluteNicheRejected:
    gen_no: int
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AbsoluteNicheResult:
    selector_version: str
    run_id: str
    config_path: str
    config_hash: str
    selected: bool
    blocked: bool
    blocker: str
    selected_candidate: CandidateGeneration | None
    selected_niche_metric: NicheMetricEntry | None
    eligible_candidates: tuple[AbsoluteNicheEligible, ...]
    rejected_candidates: tuple[AbsoluteNicheRejected, ...]
    selection_timestamp: str
    oos_excluded: bool
    diagnostic_only: bool
    forbidden_oos_fields_present: bool


# ---------------------------------------------------------------------------
# 연도 일관성 헬퍼 (P2 — csv 없이 aggregate 지표로 판단하는 경량 경로)
# ---------------------------------------------------------------------------


def _count_positive_years_from_csv(csv_path: str) -> int | None:
    """결과 CSV에서 거래 있는 연도 중 흑자 연도 수를 센다.

    파일이 없거나 파싱 실패 시 None(graceful). 거래 있는 연도 중 흑자 ≥ 2 판정에만 사용.
    칼럼명은 _yearly_sparse_robust_selection이 사용하는 _read_holdout_rows 패턴을 따른다.
    """
    if not csv_path:
        return None
    try:
        from ai_strategy_loop.fitness.holdout import _read_holdout_rows

        raw_rows = _read_holdout_rows(csv_path)
        rows = tuple((int(day), float(profit)) for day, profit in raw_rows)
        if not rows:
            return None
        profits_by_year: dict[int, float] = {}
        for day, profit in rows:
            year = day // 10000
            profits_by_year[year] = profits_by_year.get(year, 0.0) + profit
        positive = sum(1 for p in profits_by_year.values() if p > 0)
        return positive
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 적격 판정 내부 함수
# ---------------------------------------------------------------------------


def _base_rejection_reasons(
    candidate: CandidateGeneration,
    thresholds: AbsoluteNicheThresholds,
) -> list[str]:
    """기본 지표 기반 기각 사유를 반환한다."""
    reasons: list[str] = []
    if candidate.profit <= 0.0:
        reasons.append("profit <= 0")
    if candidate.mdd > thresholds.max_mdd:
        reasons.append(f"mdd > {thresholds.max_mdd} (absolute ceiling)")
    if candidate.trade_count < thresholds.min_trade_count:
        reasons.append(f"trade_count < {thresholds.min_trade_count}")
    if candidate.payoff_ratio < thresholds.min_payoff_ratio:
        reasons.append(f"payoff_ratio < {thresholds.min_payoff_ratio}")
    return reasons


def _yearly_consistency_reason(
    candidate: CandidateGeneration,
    thresholds: AbsoluteNicheThresholds,
) -> str | None:
    """P2 연도 일관성 기각 사유. 통과이면 None."""
    positive_years = _count_positive_years_from_csv(candidate.csv_path)
    if positive_years is None:
        # CSV 없거나 파싱 불가 — conservative: 자격 기준 충족 여부 불명
        # 기존 타 선택기와 달리 절대 기준 선택기는 csv 없으면 연도 일관성 판정 불가로 기각
        return "yearly_consistency_undetermined: csv unavailable or unreadable"
    if positive_years < thresholds.min_positive_years:
        return (
            f"positive_years {positive_years} < {thresholds.min_positive_years} "
            f"(P2 yearly consistency)"
        )
    return None


def _niche_qualification_reason(
    metric: NicheMetricEntry | None,
    thresholds: AbsoluteNicheThresholds,
) -> str | None:
    """니치 자격 판정. 적격이면 None, 기각이면 사유 문자열."""
    if metric is None:
        return "niche_metric_missing: no entry for this gen_no"

    corr = metric.corr_vs_frozen
    overlap = metric.time_bucket_overlap

    # 둘 다 None → 판정 불가 → 기각
    if corr is None and overlap is None:
        return (
            "niche_qualification_undetermined: "
            "corr_vs_frozen=None and time_bucket_overlap=None — cannot determine niche status"
        )

    # OR 조건: 상관 < 0.5 OR 시간버킷 비중첩(overlap==False)
    corr_qualifies = corr is not None and corr < thresholds.max_corr_vs_frozen
    bucket_qualifies = overlap is not None and overlap is False

    if corr_qualifies or bucket_qualifies:
        return None  # 적격

    # 적격 미달 — 구체 수치 포함 사유
    parts: list[str] = []
    if corr is not None:
        parts.append(f"corr_vs_frozen={corr:.3f} >= {thresholds.max_corr_vs_frozen}")
    if overlap is not None:
        parts.append(f"time_bucket_overlap={overlap} (not False)")
    return "niche_disqualified: " + "; ".join(parts)


# ---------------------------------------------------------------------------
# 공개 선택 함수
# ---------------------------------------------------------------------------


def select_absolute_niche_v1(
    candidates: Sequence[CandidateGeneration],
    *,
    niche_metrics: dict[int, NicheMetricEntry],
    run_id: str,
    config_path: str,
    config_hash: str,
    thresholds: AbsoluteNicheThresholds = DEFAULT_ABSOLUTE_NICHE_THRESHOLDS,
    diagnostic_only: bool = False,
    selection_timestamp: str | None = None,
) -> AbsoluteNicheResult:
    """절대 기준 + 니치 자격으로 OOS-blind 후보 1개를 고른다.

    Args:
        candidates:     parse_candidate_generation 산출물 리스트 (train 행).
        niche_metrics:  {gen_no: NicheMetricEntry} — N6/F1 실측치 외부 주입.
                        선택기는 계산하지 않는다.
        run_id:         실행 ID.
        config_path:    설정 파일 경로.
        config_hash:    설정 파일 해시.
        thresholds:     적격 임계값 (기본값 = 스펙 §3).
        diagnostic_only: True이면 실제 동결 없이 결과만 반환.
        selection_timestamp: ISO 타임스탬프 (None이면 현재 UTC).

    Returns:
        AbsoluteNicheResult — selected_candidate는 graded_score 최대 적격 후보.
    """
    eligible: list[tuple[AbsoluteNicheEligible, CandidateGeneration]] = []
    rejected: list[AbsoluteNicheRejected] = []

    for candidate in candidates:
        reasons: list[str] = []

        # 1) 기본 지표 기각 검사
        reasons.extend(_base_rejection_reasons(candidate, thresholds))

        # 2) 연도 일관성 (P2)
        yearly_reason = _yearly_consistency_reason(candidate, thresholds)
        if yearly_reason is not None:
            reasons.append(yearly_reason)

        # 3) 니치 자격 (corr < 0.5 OR time_bucket_overlap == False)
        metric = niche_metrics.get(candidate.gen_no)
        niche_reason = _niche_qualification_reason(metric, thresholds)
        if niche_reason is not None:
            reasons.append(niche_reason)

        if reasons:
            rejected.append(AbsoluteNicheRejected(candidate.gen_no, tuple(reasons)))
            continue

        eligible.append(
            (
                AbsoluteNicheEligible(
                    gen_no=candidate.gen_no,
                    graded_score=candidate.graded_score,
                    niche_metric=metric,
                ),
                candidate,
            )
        )

    # 적격 풀에서 graded_score 최대 선택 (내림차순 정렬 후 첫 번째)
    eligible.sort(key=lambda item: -item[0].graded_score)
    selected_pair = eligible[0] if eligible else None
    selected_candidate = selected_pair[1] if selected_pair is not None else None
    selected_metric = selected_pair[0].niche_metric if selected_pair is not None else None

    return AbsoluteNicheResult(
        selector_version=ABSOLUTE_NICHE_VERSION,
        run_id=run_id,
        config_path=config_path,
        config_hash=config_hash,
        selected=selected_candidate is not None,
        blocked=selected_candidate is None,
        blocker=(
            ""
            if selected_candidate is not None
            else "no candidate qualified for absolute_niche_v1"
        ),
        selected_candidate=selected_candidate,
        selected_niche_metric=selected_metric,
        eligible_candidates=tuple(item[0] for item in eligible),
        rejected_candidates=tuple(rejected),
        selection_timestamp=selection_timestamp or datetime.now(timezone.utc).isoformat(),
        oos_excluded=True,
        diagnostic_only=diagnostic_only,
        forbidden_oos_fields_present=False,
    )


# ---------------------------------------------------------------------------
# 아티팩트 writer
# ---------------------------------------------------------------------------


def write_absolute_niche_artifact(result: AbsoluteNicheResult, path: Path) -> None:
    """동결 아티팩트를 JSON으로 영속한다 (OOS 이전 필수 산출물).

    기존 write_yearly_sparse_robust_artifact / write_seed_relative_artifact 패턴 동일.
    oos_excluded=True 포함 보장.
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _result_payload(result)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _result_payload(result: AbsoluteNicheResult) -> JsonObject:
    selected = result.selected_candidate
    return {
        "selector_version": result.selector_version,
        "run_id": result.run_id,
        "config_path": result.config_path,
        "config_hash": result.config_hash,
        "selected": result.selected,
        "blocked": result.blocked,
        "blocker": result.blocker,
        "selected_generation": _candidate_payload(selected) if selected is not None else None,
        "selected_niche_metric": _metric_payload(result.selected_niche_metric),
        "selection_timestamp": result.selection_timestamp,
        "oos_excluded": result.oos_excluded,
        "diagnostic_only": result.diagnostic_only,
        "forbidden_oos_fields_present": result.forbidden_oos_fields_present,
        "eligible_candidates": [_eligible_payload(e) for e in result.eligible_candidates],
        "rejected_candidates": [_rejected_payload(r) for r in result.rejected_candidates],
    }


def _candidate_payload(candidate: CandidateGeneration) -> JsonObject:
    return {
        "gen_no": candidate.gen_no,
        "status": candidate.status,
        "graded_score": candidate.graded_score,
        "gate_passed": candidate.gate_passed,
        "gate_reason": candidate.gate_reason,
        "profit": candidate.profit,
        "total_profit_pct": candidate.total_profit_pct,
        "mdd": candidate.mdd,
        "trade_count": candidate.trade_count,
        "daily_avg_trades": candidate.daily_avg_trades,
        "payoff_ratio": candidate.payoff_ratio,
        "max_hold_count": candidate.max_hold_count,
        "buy_name": candidate.buy_name,
        "sell_name": candidate.sell_name,
        "csv_path": candidate.csv_path,
    }


def _metric_payload(metric: NicheMetricEntry | None) -> JsonObject | None:
    if metric is None:
        return None
    return {
        "corr_vs_frozen": metric.corr_vs_frozen,
        "time_bucket_overlap": metric.time_bucket_overlap,
    }


def _eligible_payload(item: AbsoluteNicheEligible) -> JsonObject:
    return {
        "gen_no": item.gen_no,
        "graded_score": item.graded_score,
        "niche_metric": _metric_payload(item.niche_metric),
    }


def _rejected_payload(item: AbsoluteNicheRejected) -> JsonObject:
    return {"gen_no": item.gen_no, "reasons": list(item.reasons)}
