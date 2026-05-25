"""US-007 — 루프↔대시보드 상태 계약 (frozen state contract).

이 모듈은 헤드리스 진화 루프(`controller/loop.py`)가 생성해 대시보드
(`dashboard/app.py`)가 소비하는 **단일 스냅샷 스키마**를 정의한다.

설계 원칙:
  - 계약은 **버전이 박혀** 있다(`CONTRACT_VERSION`). 루프와 대시보드는 서로
    다른 프로세스이므로(루프는 서브프로세스, 대시보드는 FastAPI), 이 스키마가
    둘 사이의 안정적 seam이다. 필드를 깨는 변경은 CONTRACT_VERSION을 올린다.
  - 루프는 매 세대 + 백테스트 시작/종료 시점에 `current_state.json`에 이
    스키마를 atomic write 한다. 대시보드는 그 파일을 폴링/푸시한다.
  - pydantic BaseModel을 쓴다 — JSON 직렬화/검증을 한 곳에서 보장한다.

자세한 계약 문서는 STATE_CONTRACT.md 참조.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

# 계약 버전. 깨는 변경(필드 제거/타입 변경) 시 +1. seam의 단일 진실원.
CONTRACT_VERSION = 1

# status 머신 상태값 (idle | running | stopping | complete | error).
STATUS_IDLE = "idle"
STATUS_RUNNING = "running"
STATUS_STOPPING = "stopping"
STATUS_COMPLETE = "complete"
STATUS_ERROR = "error"
VALID_STATUSES = (
    STATUS_IDLE,
    STATUS_RUNNING,
    STATUS_STOPPING,
    STATUS_COMPLETE,
    STATUS_ERROR,
)


class BestInfo(BaseModel):
    """현재까지 GRADED 최고 세대 요약 (선택 그래디언트 기준)."""

    gen: int = -1
    graded_score: Optional[float] = None
    gate_passed: bool = False
    buy_name: Optional[str] = None
    sell_name: Optional[str] = None


class WinnerInfo(BaseModel):
    """하드 게이트를 통과한 우승 세대 요약 (졸업/export 후보).

    통과 세대가 아직 없으면 LoopState.winner = None.
    """

    gen: int = -1
    score: Optional[float] = None
    buy_name: Optional[str] = None
    sell_name: Optional[str] = None


class GenerationInfo(BaseModel):
    """한 세대의 대시보드용 요약 행."""

    gen_no: int
    status: str = STATUS_IDLE  # ok | error | running
    graded_score: float = 0.0
    gate_passed: bool = False
    gate_reason: str = ""
    trade_count: int = 0
    mdd: float = 0.0
    profit: float = 0.0
    strategy_gist: str = ""


class LatestInfo(BaseModel):
    """현재 진행 중인 백테스트/단계의 라이브 상태."""

    phase: str = ""  # 예: 'backtest_start' | 'backtest_end' | 'generation_done'
    last_checkpoint: str = ""
    message: str = ""


class CumulativeInfo(BaseModel):
    """누적 비용/사용량 (토큰 cap 또는 세대 cap 비용 안전장치 가시화)."""

    tokens: int = 0
    # gpt_auth처럼 토큰 합산이 불가능한 provider에선 세대 수가 비용 프록시다.
    cost_or_count: int = 0


class LoopState(BaseModel):
    """루프가 대시보드로 push 하는 단일 스냅샷.

    `current_state.json`의 내용 = 이 모델의 JSON 직렬화.
    """

    contract_version: int = CONTRACT_VERSION
    run_id: Optional[str] = None
    status: str = STATUS_IDLE
    current_gen: int = -1
    max_generations: int = 0
    provider: str = ""
    bt_timeframe: str = ""

    best: BestInfo = Field(default_factory=BestInfo)
    winner: Optional[WinnerInfo] = None

    generations: List[GenerationInfo] = Field(default_factory=list)
    latest: LatestInfo = Field(default_factory=LatestInfo)
    cumulative: CumulativeInfo = Field(default_factory=CumulativeInfo)

    updated_at: float = 0.0


def idle_state(
    *,
    provider: str = "",
    bt_timeframe: str = "",
    max_generations: int = 0,
) -> LoopState:
    """루프가 돌고 있지 않을 때 대시보드가 보여줄 기본 idle 상태."""
    return LoopState(
        status=STATUS_IDLE,
        provider=provider,
        bt_timeframe=bt_timeframe,
        max_generations=max_generations,
    )
