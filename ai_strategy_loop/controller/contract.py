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

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# 계약 버전. 깨는 변경(필드 제거/타입 변경) 시 +1. seam의 단일 진실원.
#   v2: page_data 패스스루 한 필드 추가(가산적·하위호환). 후속 페이지(P1~P6)가
#       자기 데이터를 page_data["<page>"]에 실어 보내고 자기 패널과 함께 머지한다.
#       기존 필드는 이름/타입 불변이라 v1 소비자(구 프론트)는 page_data를 무시하고
#       그대로 동작한다(하위호환).
CONTRACT_VERSION = 2

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
    # 일평균거래횟수(거래수/거래일수). 빈도 게이트의 주 기준값을 대시보드에 노출한다.
    #   기본 0.0이라 이 값을 발행하지 않던 구 상태(state)도 그대로 검증 통과한다(하위호환).
    daily_avg_trades: float = 0.0
    mdd: float = 0.0
    profit: float = 0.0  # 수익금(총 실현 손익, 원).
    # P10 — 수익률(총수익률, %). 기존 profit(원)과 별개로 발행한다. 기본 None이라
    #   이 값을 발행하지 않던 구 상태(state)·구 run·에러 세대(DB NULL)는 None으로 통과한다.
    #   None은 '미측정'을 뜻하며, 프론트(table.jsx)가 NULL을 0%로 잘못 표시하지 않고
    #   "—"로 구분 표시하도록 0.0 강제 폴백을 제거했다(정보 손실 수정).
    total_profit_pct: Optional[float] = None
    strategy_gist: str = ""
    # 청산 품질 지표 — fitness/score.py GradedResult에서 전파. 기본 0.0이라
    #   이 값을 발행하지 않던 구 상태(state)도 그대로 검증 통과한다(하위호환).
    payoff_ratio: float = 0.0
    give_back_rate: float = 0.0
    # R8 품질지표 LIVE 노출 — generations DB의 calmar/uptrend_r2(이미 영속) 컬럼을
    #   세대 행에 실어 대시보드 테이블이 위험조정 품질을 표시한다. 기본 0.0이라
    #   이 값을 발행하지 않던 구 상태(state)도 그대로 검증 통과한다(하위호환).
    calmar: float = 0.0
    uptrend_r2: float = 0.0
    # R8 — 다종목 분산/동시보유 지표(GradedResult.dispersion_term/max_hold_count).
    #   dispersion_term은 기본 1.0(분산 보상 없음=중립), max_hold_count는 기본 0.0.
    #   generations DB에 컬럼이 신설(state.py SCHEMA v6)되며, 발행하지 않던 구 상태도
    #   기본값으로 검증 통과한다(하위호환).
    dispersion_term: float = 1.0
    max_hold_count: float = 0.0
    # P2b-2 가정 루프 가시화 — generations.hypotheses_json 파싱. 토글 OFF/구 상태는 [].
    hypotheses: List[Dict[str, Any]] = Field(default_factory=list)


class LatestInfo(BaseModel):
    """현재 진행 중인 백테스트/단계의 라이브 상태."""

    phase: str = ""  # 예: 'backtest_start' | 'backtest_end' | 'generation_done'
    last_checkpoint: str = ""
    message: str = ""
    # 프로세스 플로우 패널용 필드. 구 current_state.json 미포함 시 기본값으로 파싱(하위호환).
    recent_logs: List[str] = Field(default_factory=list)   # 최근 ~50 로그 라인.
    current_step: int = -1  # -1=없음 0=생성 1=백테 2=채점 3=부검 4=반복.


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

    # v2 패스스루 한 필드. 각 후속 페이지가 자기 키에 자기 데이터를 넣는다
    #   (예: page_data["autopsy"], ["population"], ["lineage"], ["meta"], ["holdout"]).
    #   계약은 이 dict의 내부 구조를 강제하지 않는다 — 페이지가 자기 패널과 함께
    #   자기 차례에 스키마를 가져온다(추측 추상화 금지, 단순성). 기본은 빈 dict라
    #   아무 페이지도 발행하지 않으면 v1과 동일한 직렬화 결과를 유지한다.
    page_data: Dict[str, Any] = Field(default_factory=dict)

    # R8 — 활성 config/토글 스냅샷. 루프가 적용한 주요 설정·안전토글을 dict로 실어
    #   대시보드가 "지금 무슨 설정으로 돌고 있나"를 LIVE로 보여준다(폼·상태에 안 보이던
    #   5종 안전토글 + evolution_mode/winner_objective/bt_* 등). 계약은 내부 구조를
    #   강제하지 않는다(page_data와 동일한 패스스루 철학). 기본 빈 dict라 이 값을
    #   발행하지 않던 구 상태(state)도 그대로 검증 통과한다(하위호환).
    active_config: Dict[str, Any] = Field(default_factory=dict)

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
