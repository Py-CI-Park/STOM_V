"""분석 카드 API (페이지 25) — Analysis Card v2 를 화면·에이전트에 공급한다.

배경(마스터 웨이브 W1): 부검 모듈은 이미 근본원인(root_cause)과 변이축
(mutation_axis)을 산출하는데, 그 카드를 **아무도 볼 수 없었다** — 대시보드
소비자가 0이었고 AI 프롬프트로만 흘렀다. 이 라우터가 그 공백을 메운다.

권위 계약: 카드는 **연구 분석 전용**이다(authority='research_analysis_card_only').
승격·실전 권한 키를 실어 나르지 않으며, 화면은 관측만 한다(자율 루프의 수정
결정은 Claude 가 같은 카드를 읽고 내린다 — 사람 승인 단계가 아니다).

성능 계약: 카드는 job_id + CSV 지문으로 캐시한다(같은 결과를 두 번 계산하지 않음).
"""

from __future__ import annotations

import os
from typing import Annotated, Any, Final

import pandas as pd
from fastapi import APIRouter
from pydantic import StringConstraints

from ai_strategy_loop.autopsy.analysis_card import build_analysis_card
from ai_strategy_loop.dashboard.trade_path_source import resolve_job_source

analysis_card_router = APIRouter()

#: 카드 캐시 — (job_id, csv_sha256) → 카드. 프로세스 수명 동안 유지.
_card_cache: dict[tuple[str, str], dict[str, Any]] = {}
_CACHE_LIMIT: Final = 32

JobId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


def _read_trades(csv_path: str) -> pd.DataFrame | None:
    if not csv_path or not os.path.exists(csv_path):
        return None
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig")
    except (OSError, ValueError, UnicodeDecodeError):
        try:
            return pd.read_csv(csv_path, encoding="cp949")
        except (OSError, ValueError, UnicodeDecodeError):
            return None


def _result_meta(source: Any, trades: pd.DataFrame | None) -> dict[str, Any]:
    """카드 헤더용 공식 지표 — 거래행에서 직접 집계(임의 키 밀반입 없음)."""
    meta: dict[str, Any] = {
        "run_id": getattr(source, "run_id", ""),
        "timeframe": getattr(getattr(source, "timeframe", None), "value", ""),
        "strategy_buy": getattr(source, "strategy_buy_name", "") or getattr(source, "strategy_buy", ""),
        "strategy_sell": getattr(source, "strategy_sell_name", "") or getattr(source, "strategy_sell", ""),
    }
    if trades is None or trades.empty:
        return meta
    for column, key in (("수익률", "avg_return_pct"), ("수익금", "profit")):
        if column in trades.columns:
            series = pd.to_numeric(trades[column], errors="coerce").dropna()
            if not series.empty:
                meta[key] = float(series.mean() if key == "avg_return_pct" else series.sum())
    meta["trades"] = int(len(trades))
    if "수익률" in trades.columns:
        returns = pd.to_numeric(trades["수익률"], errors="coerce").dropna()
        if not returns.empty:
            meta["win_rate"] = float((returns > 0).mean())
    return meta


@analysis_card_router.get("/bt/analysis-card")
def analysis_card(job_id: JobId, fine_time: bool = False) -> dict[str, Any]:
    """완료된 백테스트 job 의 분석 카드(v2)를 반환한다.

    실패·미완료 job 은 카드를 만들지 않는다(불완전 산출물을 근거로 삼지 않는다).
    """
    try:
        resolved = resolve_job_source(job_id)
    except ValueError as exc:
        return {"available": False, "reason": str(exc),
                "authority": "research_analysis_card_only"}

    source = resolved.source
    cache_key = (job_id, getattr(source, "csv_sha256", ""))
    if not fine_time and cache_key in _card_cache:
        return {"available": True, "cached": True, **_card_cache[cache_key]}

    trades = _read_trades(getattr(source, "csv_path", ""))
    if trades is None:
        return {"available": False, "reason": "trade_csv_unreadable",
                "authority": "research_analysis_card_only"}

    card = build_analysis_card(_result_meta(source, trades), trades, fine_time=fine_time)
    payload = {
        "authority": "research_analysis_card_only",
        "job_id": job_id,
        "csv_sha256": getattr(source, "csv_sha256", ""),
        "trade_count": int(len(trades)),
        "card": card,
    }
    if not fine_time:
        if len(_card_cache) >= _CACHE_LIMIT:
            _card_cache.pop(next(iter(_card_cache)))
        _card_cache[cache_key] = payload
    return {"available": True, "cached": False, **payload}


@analysis_card_router.get("/bt/analysis-card/losers")
def analysis_card_losers(job_id: JobId, limit: int = 20) -> dict[str, Any]:
    """카드의 근본원인을 눈으로 확인할 손실 거래 목록(리플레이 연결용).

    수정 결정의 근거를 '숫자'뿐 아니라 '실제 거래'로도 볼 수 있게 한다.
    """
    limit = max(1, min(int(limit), 200))
    try:
        resolved = resolve_job_source(job_id)
    except ValueError as exc:
        return {"available": False, "reason": str(exc), "rows": []}

    trades = _read_trades(getattr(resolved.source, "csv_path", ""))
    if trades is None or trades.empty or "수익률" not in trades.columns:
        return {"available": False, "reason": "trade_csv_unreadable", "rows": []}

    frame = trades.copy()
    frame["_ret"] = pd.to_numeric(frame["수익률"], errors="coerce")
    worst = frame.dropna(subset=["_ret"]).nsmallest(limit, "_ret")
    keep = [c for c in ("일자", "종목명", "종목코드", "매수시간", "매도시간", "수익률",
                        "수익금", "보유시간", "매도조건") if c in worst.columns]
    rows = worst[keep].to_dict("records") if keep else []
    return {
        "available": True,
        "authority": "research_analysis_card_only",
        "job_id": job_id,
        "rows": [{str(k): (None if pd.isna(v) else v) for k, v in row.items()} for row in rows],
    }
