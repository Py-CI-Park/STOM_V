"""손실 영역 API(G-0c) — 페이지 17~21 데이터 공급자.

권위 구분:
  - `loss-profile` / `loss-pockets` / `split-diagnostics` → **관찰**. 진단·정본 수치다.
  - `removal-simulate` / `region-candidates` → **자문**. 추정치이며 재유입을 반영하지
    못한다. R2 실측에서 필터 적용 후 거래가 오히려 늘었다(유지율 100.7%).
    따라서 순위용이며 공식 pair/gate 판정을 대체하지 않는다.

평가 프로토콜 v2:
  후보당 백테스트 1회. 연속 1회 런 CSV 를 `lane_manifest.split_boundary` 로 나눠
  설계/홀드아웃을 만든다. 연속 런은 자본이 이어지므로 "OOS" 가 아니라 "홀드아웃"이다.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Final

from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from pydantic import Field, StringConstraints, field_validator

from ai_strategy_loop.autopsy import loss_profile as lp
from ai_strategy_loop.dashboard.backtest_jobs import get_job_manager
from ai_strategy_loop.dashboard.lane_manifest import LANE_MANIFESTS, baseline_code
from ai_strategy_loop.dashboard.trade_path_api_models import FrozenPayload, ShortText
from ai_strategy_loop.revision import region_proposer as rp
from ai_strategy_loop.revision.buy_filter_proposer import RUNTIME_EXPRESSION


loss_region_router = APIRouter()

_DEFAULT_PAIR_VARIABLES: Final = (
    "B_등락율", "B_체결강도", "B_회전율", "B_시분초", "B_시가총액", "B_전일비",
)
_CACHE_LIMIT: Final = 2
_run_cache: dict[tuple[str, float], lp.RunColumns] = {}

REENTRY_CAVEAT: Final = (
    "제거 시뮬레이션 추정입니다. 자금이 풀려 다른 종목으로 재유입되는 효과를 "
    "반영하지 못하므로 순위용이며, 판정은 공식 pair/gate 가 합니다."
)
CONTINUOUS_CAVEAT: Final = (
    "연속 1회 런이라 자본이 이어집니다. 홀드아웃은 독립 OOS 가 아니므로 "
    "총손익보다 건당 손익으로 판단하세요."
)


def clear_run_cache() -> None:
    _run_cache.clear()


# --------------------------------------------------------------------------- 입력 모델

class IntervalPayload(FrozenPayload):
    column: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
    low: float | None = None
    high: float | None = None


class ClausePayload(FrozenPayload):
    # 바깥 리스트 = OR, 안쪽 리스트 = AND.
    terms: tuple[tuple[IntervalPayload, ...], ...] = Field(min_length=1, max_length=4)

    @field_validator("terms", mode="before")
    @classmethod
    def _tuple_terms(cls, value: object) -> object:
        # FrozenPayload 는 strict 라 JSON 리스트가 튜플로 자동 변환되지 않는다.
        if isinstance(value, list):
            return tuple(tuple(group) if isinstance(group, list) else group for group in value)
        return value


class RemovalSimulateRequest(FrozenPayload):
    job_id: ShortText
    lane: Annotated[str, StringConstraints(pattern="^(tick|min)$")]
    split: int | None = None
    clauses: tuple[ClausePayload, ...] = Field(min_length=1, max_length=8)

    @field_validator("clauses", mode="before")
    @classmethod
    def _tuple_clauses(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value


class RegionCandidateRequest(FrozenPayload):
    job_id: ShortText
    lane: Annotated[str, StringConstraints(pattern="^(tick|min)$")]
    split: int | None = None
    generation: int = Field(default=1, ge=1, le=20)
    prior_retention: float = Field(default=1.0, gt=0.0, le=1.0)
    max_clauses: int = Field(default=4, ge=1, le=4)
    variables: str = ""


# --------------------------------------------------------------------------- 공통

def _unavailable(reason: str, authority: str = "diagnostic") -> dict[str, object]:
    return {"available": False, "reason": reason, "authority": authority}


def _resolve(job_id: str, lane: str, split: int | None):
    """job → (설계 RunColumns, 홀드아웃 RunColumns, 분할일). 실패는 사유 문자열."""
    manifest = LANE_MANIFESTS.get(lane)
    if manifest is None:
        return None, "unknown_lane"
    record = get_job_manager().get(job_id, log_tail=0)
    if not record.get("available") or record.get("status") != "success":
        return None, "backtest_result_missing"
    raw = record.get("csv_path")
    path = Path(str(raw)) if raw else None
    if path is None or not path.is_file():
        return None, "backtest_result_missing"
    boundary = int(split or manifest.split_boundary)
    key = (str(path.resolve()), path.stat().st_mtime)
    run = _run_cache.get(key)
    if run is None:
        run = lp._read_run(path, None)
        if len(_run_cache) >= _CACHE_LIMIT:
            _run_cache.clear()
        _run_cache[key] = run
    design, holdout = lp.split_run(run, boundary)
    return (design, holdout, boundary, run), None


def _pick_variables(raw: str) -> tuple[str, ...]:
    if not raw.strip():
        return _DEFAULT_PAIR_VARIABLES
    return tuple(name.strip() for name in raw.split(",") if name.strip())


def _to_clause(payload: ClausePayload) -> rp.RegionClause | None:
    terms: list[tuple[rp.Interval, ...]] = []
    for group in payload.terms:
        built: list[rp.Interval] = []
        for interval in group:
            variable = RUNTIME_EXPRESSION.get(interval.column)
            if variable is None or (interval.low is None and interval.high is None):
                return None
            built.append(rp.Interval(
                column=interval.column, variable=variable,
                low=interval.low, high=interval.high,
            ))
        terms.append(tuple(built))
    kind = "pocket_2d" if any(len(group) > 1 for group in terms) else (
        "multi_band" if len(terms) > 1 else "single"
    )
    return rp.RegionClause(
        kind=kind, card_id=f"manual_{kind}", terms=tuple(terms), source="화면 입력",
        design_share=0.0, holdout_share=0.0,
        design_per_trade=0.0, holdout_per_trade=0.0,
    )


# --------------------------------------------------------------------------- 17

@loss_region_router.get("/loss-profile")
def loss_profile(job_id: str = "", lane: str = "tick", split: int | None = None) -> dict:
    """변수별 10분위·형태·최악 구간·파레토(관찰)."""
    resolved, reason = _resolve(job_id, lane, split)
    if resolved is None:
        return _unavailable(reason or "unknown")
    design, holdout, boundary, _ = resolved
    payload = lp.profile_payload_from_runs(design=design, holdout=holdout)
    payload["split"] = boundary
    payload["lane"] = lane
    payload["job_id"] = job_id
    return jsonable_encoder(payload)


# --------------------------------------------------------------------------- 18

@loss_region_router.get("/loss-pockets")
def loss_pockets(
    job_id: str = "", lane: str = "tick", split: int | None = None, variables: str = "",
) -> dict:
    """2D 손실 포켓 — Welch t + BH-FDR 통과 칸만(관찰)."""
    resolved, reason = _resolve(job_id, lane, split)
    if resolved is None:
        return _unavailable(reason or "unknown")
    design, holdout, boundary, _ = resolved
    names = tuple(name for name in _pick_variables(variables) if name in design.columns)
    if len(names) < 2:
        return {
            "available": True, "authority": "diagnostic", "pockets": [],
            "reason": "no_eligible_pair", "variables": list(names), "split": boundary,
            "note": "2D 포켓은 변수 2개 이상이 필요합니다.",
        }
    pockets = lp.pocket_scan(
        design=lp.samples_from(design, names),
        holdout=lp.samples_from(holdout, names),
        variables=names,
        min_cell=max(50, len(design.pnls) // 2000),
    )
    return jsonable_encoder({
        "available": True, "authority": "diagnostic", "lane": lane, "split": boundary,
        "variables": list(names), "fdr_alpha": lp.FDR_ALPHA,
        "pockets": [asdict(pocket) for pocket in pockets],
        "reason": "" if pockets else "no_significant_pocket",
        "note": "FDR 통과 칸으로만 연결 성분을 만들고 직사각형 근사 낭비 30% 이하만 남깁니다.",
    })


# --------------------------------------------------------------------------- 19

@loss_region_router.post("/removal-simulate")
def removal_simulate(payload: RemovalSimulateRequest) -> dict:
    """제거 조합 즉시 계산(자문) — 백테스트가 아니라 CSV 재계산이다."""
    resolved, reason = _resolve(payload.job_id, payload.lane, payload.split)
    if resolved is None:
        return _unavailable(reason or "unknown", "advisory")
    design, holdout, boundary, _ = resolved
    clauses = [_to_clause(item) for item in payload.clauses]
    if any(clause is None for clause in clauses):
        return _unavailable("unknown_runtime_variable", "advisory")
    built = [clause for clause in clauses if clause is not None]
    columns = tuple({
        interval.column for clause in built
        for group in clause.terms for interval in group
    })
    base = baseline_code(payload.lane, "buy")
    if not base:
        return _unavailable("baseline_buy_missing", "advisory")
    try:
        code = rp.derive_region_code(base, built)
        rp.validate_region_code(code=code, base_code=base, clauses=built)
    except rp.RegionValidationError as error:
        return _unavailable(str(error), "advisory")

    design_samples = lp.samples_from(design, columns)
    holdout_samples = lp.samples_from(holdout, columns)
    design_kept, design_removed = rp.apply_clauses(design_samples, built)
    holdout_kept, holdout_removed = rp.apply_clauses(holdout_samples, built)

    def per_trade(rows) -> float:
        return round(sum(row.pnl for row in rows) / len(rows), 2) if rows else 0.0

    design_retention = round(len(design_kept) / len(design_samples), 4) if design_samples else 0.0
    holdout_retention = (
        round(len(holdout_kept) / len(holdout_samples), 4) if holdout_samples else 0.0
    )
    return jsonable_encoder({
        "available": True, "authority": "advisory", "lane": payload.lane,
        "split": boundary,
        "design_retention": design_retention,
        "holdout_retention": holdout_retention,
        "design_removed_pnl": design_removed,
        "holdout_removed_pnl": holdout_removed,
        "design_per_trade_before": per_trade(design_samples),
        "design_per_trade_after": per_trade(design_kept),
        "holdout_per_trade_before": per_trade(holdout_samples),
        "holdout_per_trade_after": per_trade(holdout_kept),
        "budget": rp.budget_verdict(
            generation=1, retention=design_retention, prior_retention=1.0,
            holdout_retention=holdout_retention,
        ),
        "cumulative_floor": rp.CUMULATIVE_FLOOR,
        "expression": [clause.expression for clause in built],
        "stom_code": code,
        "caveat": REENTRY_CAVEAT,
    })


# --------------------------------------------------------------------------- 후보

@loss_region_router.post("/region-candidates")
def region_candidates(payload: RegionCandidateRequest) -> dict:
    """확인된 손실 구간 → 복합 제거 절 묶음 후보(자문)."""
    resolved, reason = _resolve(payload.job_id, payload.lane, payload.split)
    if resolved is None:
        return _unavailable(reason or "unknown", "advisory")
    design, holdout, boundary, _ = resolved
    base = baseline_code(payload.lane, "buy")
    if not base:
        return _unavailable("baseline_buy_missing", "advisory")

    profile = lp.profile_payload_from_runs(design=design, holdout=holdout)
    if not profile.get("available"):
        return _unavailable(str(profile.get("reason") or "sample_too_small"), "advisory")
    min_bucket = int(profile["min_bucket"])          # type: ignore[arg-type]
    profiles = []
    for name in design.pool:
        pairs = [
            (value, pnl) for value, pnl in zip(design.columns[name], design.pnls)
            if value is not None
        ]
        holdout_pairs = [
            (value, pnl) for value, pnl in zip(holdout.columns.get(name, []), holdout.pnls)
            if value is not None
        ]
        if len(pairs) < min_bucket * 4 or not holdout_pairs:
            continue
        profiles.append(lp._profile_series(
            variable=name,
            design_values=[value for value, _ in pairs],
            design_pnls=[pnl for _, pnl in pairs],
            holdout_values=[value for value, _ in holdout_pairs],
            holdout_pnls=[pnl for _, pnl in holdout_pairs],
            min_bucket=min_bucket,
        ))
    names = tuple(name for name in _pick_variables(payload.variables) if name in design.columns)
    pockets = lp.pocket_scan(
        design=lp.samples_from(design, names),
        holdout=lp.samples_from(holdout, names),
        variables=names, min_cell=max(50, len(design.pnls) // 2000),
    ) if len(names) >= 2 else ()

    columns = tuple(dict.fromkeys(
        [item.variable for item in profiles] + [name for name in names]
    ))
    candidates, skipped = rp.propose_regions(
        profiles=tuple(profiles), pockets=pockets,
        design=lp.samples_from(design, columns),
        holdout=lp.samples_from(holdout, columns),
        base_code=base, generation=payload.generation,
        prior_retention=payload.prior_retention, max_clauses=payload.max_clauses,
    )
    return jsonable_encoder({
        "available": True, "authority": "advisory", "lane": payload.lane,
        "split": boundary, "generation": payload.generation,
        "candidates": [asdict(candidate) for candidate in candidates],
        "skipped": [dict(item) for item in skipped],
        "profiles_tested": len(profiles), "pockets_found": len(pockets),
        "caveat": REENTRY_CAVEAT,
    })


# --------------------------------------------------------------------------- 21

@loss_region_router.get("/split-diagnostics")
def split_diagnostics(job_id: str = "", lane: str = "tick", split: int | None = None) -> dict:
    """구간 분할 요약 — 두 구간 합계가 전체와 맞는지 검산한다(정본 수치)."""
    resolved, reason = _resolve(job_id, lane, split)
    if resolved is None:
        return _unavailable(reason or "unknown", "official")
    design, holdout, boundary, whole = resolved

    def summary(run: lp.RunColumns) -> dict[str, object]:
        total = sum(run.pnls)
        wins = sum(1 for value in run.pnls if value > 0)
        return {
            "trades": len(run.pnls),
            "profit_krw": round(total, 2),
            "per_trade_krw": round(total / len(run.pnls), 2) if run.pnls else 0.0,
            "win_rate": round(wins / len(run.pnls), 4) if run.pnls else 0.0,
            "first_date": min(run.dates) if run.dates else 0,
            "last_date": max(run.dates) if run.dates else 0,
        }

    design_summary, holdout_summary = summary(design), summary(holdout)
    whole_summary = summary(whole)
    reconciled = (
        design_summary["trades"] + holdout_summary["trades"] == whole_summary["trades"]
    )
    return jsonable_encoder({
        "available": True, "authority": "official", "lane": lane, "job_id": job_id,
        "split": boundary,
        "design": design_summary, "holdout": holdout_summary, "whole": whole_summary,
        "reconciled": reconciled,
        "analysis_endpoints": {
            "equity": f"/bt/analysis/equity?job_id={job_id}",
            "underwater": f"/bt/analysis/underwater?job_id={job_id}",
            "heatmap": f"/bt/analysis/heatmap?job_id={job_id}",
        },
        "caveat": CONTINUOUS_CAVEAT,
    })


# --------------------------------------------------------------------------- 20

@loss_region_router.get("/generations")
def generations(lane: str = "tick") -> dict:
    """세대 이력·수렴 판정. 아직 세대 러너가 기록을 남기지 않으면 빈 목록이 정상."""
    from ai_strategy_loop.revision.generation_runner import history_payload

    return jsonable_encoder(history_payload(lane=lane))
