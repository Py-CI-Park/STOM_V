"""QSP7 single-trade STOM sell-expression trace API."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from ai_strategy_loop.autopsy.ablation import parse_top_level_clauses
from ai_strategy_loop.autopsy.market_path import MarketPathRepository
from ai_strategy_loop.autopsy.sell_dsl_replay import replay_sell_strategy
from ai_strategy_loop.autopsy.trade_episode import SymbolResolver
from ai_strategy_loop.autopsy.trade_path_clock import liquidation_timestamp
from ai_strategy_loop.autopsy.trade_path_models import ActualExit, Timeframe
from ai_strategy_loop.dashboard.trade_path_jobs import trade_path_coordinator
from ai_strategy_loop.dashboard.trade_path_source import resolve_job_source


sell_dsl_router = APIRouter(tags=["trade-path"])


class FrozenResponse(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)


class ClauseResponse(FrozenResponse):
    index: int
    text: str
    expression: str
    combinator: str
    variables: tuple[str, ...]
    derived_variables: tuple[str, ...]
    source: str


class ReplayResponse(FrozenResponse):
    status: str
    triggered: bool
    exit_timestamp: int | None
    exit_price: float | None
    rule_order: int | None
    condition: str
    net_return_pct: float | None
    profit_krw: int | None
    delta_profit_krw: int | None
    strategy_sha256: str
    unsupported: tuple[str, ...]
    note: str


class ActualExitResponse(FrozenResponse):
    timestamp: int
    price: float
    profit_pct: float
    profit_krw: int
    reason: str


class DataQualityResponse(FrozenResponse):
    source_db: str
    pre_entry_rows: int
    bounded_at: int
    read_only: bool
    capped: bool


class SellDslEnvelope(FrozenResponse):
    available: bool
    authority: Literal["diagnostic", "advisory"]
    reason: str = ""
    timeframe: Literal["tick", "min"] | None = None
    strategy_sell: str = ""
    clauses: tuple[ClauseResponse, ...] = ()
    replay: ReplayResponse | None = None
    actual_exit: ActualExitResponse | None = None
    data_quality: DataQualityResponse | None = None
    limitations: tuple[str, ...] = ()


def _day_start(date: int, timeframe: Timeframe) -> int:
    return date * (1_000_000 if timeframe is Timeframe.TICK else 10_000)


@sell_dsl_router.get("/sell-dsl-trace", response_model=SellDslEnvelope)
def sell_dsl_trace(analysis_id: str = "", trade_key: str = "") -> SellDslEnvelope:
    """Replay the original ordered sell DSL; never read past forced liquidation."""
    job = trade_path_coordinator().get(analysis_id)
    result = job.result if job is not None and job.status == "success" else None
    summary = None if result is None else next(
        (item for item in result.episodes if item.trade_key == trade_key), None,
    )
    row = None if summary is None else next(
        (item for item in result.rows if item.row_id == summary.row_id), None,
    )
    if result is None or row is None:
        return SellDslEnvelope(available=False, reason="trade_not_found", authority="diagnostic")
    code = result.source.strategy_sell.strip()
    if not code:
        return SellDslEnvelope(available=False, reason="sell_code_missing", authority="diagnostic")
    try:
        resolved = resolve_job_source(
            result.source.run_id,
            forced_liquidation_time=result.source.forced_liquidation_time,
        )
        code_value = SymbolResolver(resolved.code_info_db).resolve(row.name)
        timeframe = result.source.timeframe
        unit = 1_000_000 if timeframe is Timeframe.TICK else 10_000
        date = row.buy_time // unit
        boundary = liquidation_timestamp(date, result.source.forced_liquidation_time, timeframe)
        market = MarketPathRepository(database_dir=resolved.database_dir).load(
            date=date, code=code_value, timeframe=timeframe,
            start_timestamp=_day_start(date, timeframe), end_timestamp=boundary,
        )
        replay = replay_sell_strategy(
            code=code, points=market.points, entry_timestamp=row.buy_time,
            boundary_timestamp=boundary, timeframe=timeframe, buy_price=row.buy_price,
            buy_amount=row.buy_amount,
            actual_exit=ActualExit(row.sell_time, row.sell_price, row.profit_pct,
                                   row.profit_krw, row.exit_reason),
        )
        clauses = tuple(ClauseResponse.model_validate(item) for item in parse_top_level_clauses(code))
    except (OSError, ValueError) as exc:
        return SellDslEnvelope(available=False, reason=str(exc), authority="diagnostic")
    pre_entry = sum(1 for point in market.points if point.timestamp < row.buy_time)
    actual_exit = ActualExit(row.sell_time, row.sell_price, row.profit_pct,
                             row.profit_krw, row.exit_reason)
    return SellDslEnvelope(
        available=True,
        authority="advisory",
        timeframe=timeframe.value,
        strategy_sell=code,
        clauses=clauses,
        replay=ReplayResponse.model_validate(replay),
        actual_exit=ActualExitResponse.model_validate(actual_exit),
        data_quality=DataQualityResponse(
            source_db=market.source_db,
            pre_entry_rows=pre_entry,
            bounded_at=boundary,
            read_only=market.read_only,
            capped=market.capped,
        ),
        limitations=(
            "가상 재생은 동일 진입·단일 보유를 고정한 자문 결과입니다.",
            "추가매수·체결슬리피지는 공식 재백테스트에서만 확정됩니다.",
            "전체청산 이후 데이터는 평가하지 않습니다.",
        ),
    )
