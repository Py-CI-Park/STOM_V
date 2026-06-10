"""seed_relative_v1 — 시드 상대 기준 OOS-blind 후보 선택기 (2026-06-10 원인1 대응).

배경(docs/update_log/2026-06-10_condition_research_root_cause_and_plan.md §2 원인1):
sparse_positive_v1의 절대 기준(MDD<=10, 거래 20~250)은 같은 측정계로 잰 인간 시드
(train MDD 17.44, 거래 307)조차 탈락시킨다. 그 기준을 통과할 수 있는 건 "저거래·저MDD
모양"뿐이고, 그 모양은 train 우연적합(gen4)일 확률이 높아 OOS 붕괴→REJECT가 구조적으로
반복됐다. seed_relative_v1은 임계값을 **같은 측정계의 시드 프로파일에 상대화**한다.

원칙:
  - 기존 선택기(sparse_positive_v1/yearly_sparse_robust_v1)는 무수정·병기한다.
  - OOS-blind: 입력 행에 OOS 필드가 있으면 parse 단계(parse_candidate_generation)가
    거부한다. 본 선택기는 train 행에만 적용하고 동결 이후 재선택을 금지한다.
  - 연도별 흑자는 **advisory**(순위 신호)다 — 자격(eligibility)을 좌우하지 않는다
    (사용자가 per-year 균등성 하드 게이트를 명시적으로 거부한 §3.21 이력 존중).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional, Sequence, Tuple

from ._candidate_selection_core import CandidateGeneration

SEED_RELATIVE_VERSION = "seed_relative_v1"


@dataclass(frozen=True, slots=True)
class SeedRelativeThresholds:
    """시드 상대 임계값. mdd 한도 = max(mdd_abs_floor, seed_mdd * mdd_seed_mult)."""

    mdd_abs_floor: float = 20.0
    mdd_seed_mult: float = 1.1
    min_trade_count: int = 50
    max_trade_count: int = 400
    min_daily_avg_trades: float = 0.05
    min_payoff_ratio: float = 1.05
    # advisory: 관측 연도 중 흑자 연도 수가 이 값 이상이면 meets_yearly_advisory=True.
    advisory_min_positive_years: int = 2


@dataclass(frozen=True, slots=True)
class SeedProfile:
    """같은 측정계(같은 run/윈도우)로 잰 시드 기준점."""

    mdd: float
    trade_count: int
    profit: float = 0.0
    source: str = ""  # 예: "BASE_SEED gen0 of cldgen_train_2023_2025_20260610"


@dataclass(frozen=True, slots=True)
class YearlyAdvisory:
    """연도별 손익 분해(advisory 전용 — 자격에 영향 없음)."""

    years: Tuple[Tuple[str, float], ...]  # (("2023", 1954268.0), ...)
    positive_years: int
    observed_years: int
    meets_advisory: bool


@dataclass(frozen=True, slots=True)
class SeedRelativeEligible:
    gen_no: int
    rank_key: Tuple[float, float, float, float, int]
    yearly: Optional[YearlyAdvisory]


@dataclass(frozen=True, slots=True)
class SeedRelativeRejected:
    gen_no: int
    reasons: Tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SeedRelativeResult:
    selector_version: str
    run_id: str
    config_path: str
    config_hash: str
    seed_profile: Optional[SeedProfile]
    mdd_limit: float
    selected: bool
    blocked: bool
    blocker: str
    selected_candidate: Optional[CandidateGeneration]
    selected_yearly: Optional[YearlyAdvisory]
    eligible_candidates: Tuple[SeedRelativeEligible, ...]
    rejected_candidates: Tuple[SeedRelativeRejected, ...]
    selection_timestamp: str
    oos_excluded: bool
    diagnostic_only: bool
    forbidden_oos_fields_present: bool


DEFAULT_SEED_RELATIVE_THRESHOLDS = SeedRelativeThresholds()


def yearly_profit_breakdown(csv_path: str) -> Optional[Tuple[Tuple[str, float], ...]]:
    """결과 CSV(거래당 1행)에서 연도별 수익금 합계를 구한다.

    `매수시간`(YYYYMMDDHHMMSS) 앞 4자리를 연도로, `수익금`을 손익으로 쓴다.
    어떤 실패(파일 없음/컬럼 없음/파싱 오류)도 None으로 흡수한다(advisory 전용 —
    선택 자격에 영향을 주지 않으므로 graceful해야 한다).
    """
    try:
        import pandas as pd  # noqa: PLC0415 - 무거운 import는 호출 시점에만.

        path = Path(csv_path)
        if not path.is_file():
            return None
        df = pd.read_csv(path, encoding="utf-8-sig")
        if "매수시간" not in df.columns or "수익금" not in df.columns:
            return None
        years = df["매수시간"].astype(str).str[:4]
        grouped = df.groupby(years)["수익금"].sum()
        return tuple((str(year), float(total)) for year, total in grouped.items())
    except Exception:
        return None


def _yearly_advisory(
    candidate: CandidateGeneration,
    thresholds: SeedRelativeThresholds,
    csv_loader: Callable[[str], Optional[Tuple[Tuple[str, float], ...]]],
) -> Optional[YearlyAdvisory]:
    if not candidate.csv_path:
        return None
    years = csv_loader(candidate.csv_path)
    if not years:
        return None
    positive = sum(1 for _, total in years if total > 0)
    return YearlyAdvisory(
        years=tuple(years),
        positive_years=positive,
        observed_years=len(years),
        meets_advisory=positive >= thresholds.advisory_min_positive_years,
    )


def _rejection_reasons(
    candidate: CandidateGeneration,
    thresholds: SeedRelativeThresholds,
    mdd_limit: float,
) -> list:
    reasons = []
    if candidate.status != "ok":
        reasons.append("status != ok")
    if not candidate.buy_name or not candidate.sell_name:
        reasons.append("missing strategy name")
    if candidate.profit <= 0.0:
        reasons.append("profit <= 0")
    if candidate.mdd > mdd_limit:
        reasons.append(f"mdd > {mdd_limit:.2f} (seed-relative limit)")
    if candidate.trade_count < thresholds.min_trade_count:
        reasons.append(f"trade_count < {thresholds.min_trade_count}")
    if candidate.trade_count > thresholds.max_trade_count:
        reasons.append(f"trade_count > {thresholds.max_trade_count}")
    if candidate.daily_avg_trades < thresholds.min_daily_avg_trades:
        reasons.append(f"daily_avg_trades < {thresholds.min_daily_avg_trades}")
    if candidate.payoff_ratio < thresholds.min_payoff_ratio:
        reasons.append(f"payoff_ratio < {thresholds.min_payoff_ratio}")
    return reasons


def _rank_key(
    candidate: CandidateGeneration,
    yearly: Optional[YearlyAdvisory],
) -> Tuple[float, float, float, float, int]:
    """정렬 키(오름차순 정렬에서 앞 = 우선). 연도별 흑자 advisory가 1차 신호다."""
    positive_years = yearly.positive_years if yearly is not None else -1
    profit_per_mdd = candidate.profit / max(candidate.mdd, 1.0)
    return (
        -float(positive_years),
        -profit_per_mdd,
        candidate.mdd,
        -candidate.payoff_ratio,
        candidate.gen_no,
    )


def select_seed_relative_v1(
    candidates: Sequence[CandidateGeneration],
    *,
    run_id: str,
    config_path: str,
    config_hash: str,
    seed_profile: Optional[SeedProfile] = None,
    diagnostic_only: bool = False,
    selection_timestamp: Optional[str] = None,
    thresholds: SeedRelativeThresholds = DEFAULT_SEED_RELATIVE_THRESHOLDS,
    csv_loader: Callable[[str], Optional[Tuple[Tuple[str, float], ...]]] = yearly_profit_breakdown,
) -> SeedRelativeResult:
    """시드 상대 기준으로 OOS-blind 연구 후보 1개를 고른다.

    Args:
        candidates: parse_candidate_generation으로 만든 train 행들(베이스라인 제외는
            호출부 책임 — 출처 기준 BASE_ 제외).
        seed_profile: 같은 측정계로 잰 시드 기준점. None이면 mdd 한도는
            thresholds.mdd_abs_floor만 적용된다.
        csv_loader: csv_path -> 연도별 손익 tuple (advisory 전용, graceful).
    """
    if seed_profile is not None:
        mdd_limit = max(
            thresholds.mdd_abs_floor, seed_profile.mdd * thresholds.mdd_seed_mult
        )
    else:
        mdd_limit = thresholds.mdd_abs_floor

    eligible: list = []
    rejected: list = []
    for candidate in candidates:
        reasons = _rejection_reasons(candidate, thresholds, mdd_limit)
        if reasons:
            rejected.append(SeedRelativeRejected(candidate.gen_no, tuple(reasons)))
            continue
        yearly = _yearly_advisory(candidate, thresholds, csv_loader)
        eligible.append(
            (
                SeedRelativeEligible(
                    gen_no=candidate.gen_no,
                    rank_key=_rank_key(candidate, yearly),
                    yearly=yearly,
                ),
                candidate,
            )
        )

    eligible.sort(key=lambda item: item[0].rank_key)
    selected_pair = eligible[0] if eligible else None
    selected_candidate = selected_pair[1] if selected_pair is not None else None
    selected_yearly = selected_pair[0].yearly if selected_pair is not None else None

    return SeedRelativeResult(
        selector_version=SEED_RELATIVE_VERSION,
        run_id=run_id,
        config_path=config_path,
        config_hash=config_hash,
        seed_profile=seed_profile,
        mdd_limit=mdd_limit,
        selected=selected_candidate is not None,
        blocked=selected_candidate is None,
        blocker="" if selected_candidate is not None else (
            "no candidate qualified for seed_relative_v1"
        ),
        selected_candidate=selected_candidate,
        selected_yearly=selected_yearly,
        eligible_candidates=tuple(item[0] for item in eligible),
        rejected_candidates=tuple(rejected),
        selection_timestamp=selection_timestamp or datetime.now(timezone.utc).isoformat(),
        oos_excluded=True,
        diagnostic_only=diagnostic_only,
        forbidden_oos_fields_present=False,
    )


def write_seed_relative_artifact(result: SeedRelativeResult, output_path: Path) -> None:
    """동결(freeze) 아티팩트를 JSON으로 영속한다(OOS 이전 필수 산출물)."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(result)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
