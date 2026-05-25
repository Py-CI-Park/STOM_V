"""AI strategy loop 공유 설정 스키마.

provider 선택 + 모델 + (이후 단계용) 루프 파라미터 placeholder를 담는다.
US-002 단계에서는 provider/model 필드만 사용되며, 루프 파라미터(mdd_cap 등)는
다음 단계에서 쓰일 자리만 잡아둔다.

dict로부터 로드 가능하다 (이후 launch-config가 이 dict를 공급).
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, Dict, Optional


@dataclass
class LoopConfig:
    """AI strategy loop 전체 설정."""

    # --- provider 레이어 (US-002에서 사용) ---
    provider: str = "gpt_auth"  # gpt_auth | openrouter | codex_proxy
    model: str = "gpt-5.5"
    base_url: Optional[str] = None  # None이면 provider 기본값 사용
    api_key: Optional[str] = None  # None이면 provider별 env에서 로드
    max_retries: int = 2
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

    # --- 루프 파라미터 placeholder (이후 단계용, 아직 미사용) ---
    mdd_cap: float = 25.0
    min_trades: int = 30
    tpi_gate: float = 1.2
    graduation_holdout: bool = False
    # graduation_holdout가 켜졌을 때 train 윈도우 끝에서 떼어 두는 최근 거래일 수.
    # 이 구간은 iteration 점수에서 제외되며, 졸업하려면 holdout에서도 gate를 통과해야 한다.
    holdout_recent_days: int = 30

    # --- 백테스트 스코프 (per-generation 평가용 BOUNDED 스코프) ---
    # 속도/충실도 트레이드오프:
    #   풀 유니버스(1379 종목) 백테스트는 분 단위가 아니라 ~1시간이 걸려
    #   세대별 평가 루프에는 부적합하다. 그래서 기본 스코프는 단일 종목
    #   ('한종목 로딩') + 짧은 분봉 윈도우로 좁혀, 백테스트 1회를 수초~저분
    #   단위로 끝낸다. 신호 충실도(유니버스 다양성)는 낮아지지만, 세대마다
    #   빠르게 PASS/FAIL 신호를 받는 것이 루프 진화에는 더 중요하다.
    #   더 높은 충실도가 필요하면 launch-config(RV2-2)에서 이 필드를
    #   넓은 스코프로 오버라이드한다.
    #
    # 주의: BacktestConfig에는 "상위 N개 유니버스 cap" 기능이 없다
    #   (divid_mode는 '종목코드별 분류' | '일자별 분류' | '한종목 로딩'뿐).
    #   엔진을 건드리지 않고 스코프를 좁히는 가장 단순한 방법은
    #   '한종목 로딩' 단일 종목 + 짧은 날짜 윈도우다.
    # bt_timeframe: 'min' | 'tick'.
    #   기본값이 'min'인 이유(MVP): 생성기(brain)가 타임프레임 인지로 전략을 만든다.
    #   prompt.py가 timeframe별 변수 계열만 쓰도록 지시하고, generator의 변수 스코프
    #   가드(brain/variable_scope.check_variable_scope)가 타임프레임에 없는 변수를
    #   백테스트 **이전**에 결정론적으로 거부한다. 따라서 과거의 NameError-데드락
    #   (MIN 엔진에 초당* TICK 변수 사용 → exec(buystg) 죽음 → '백테완료' 미전송 →
    #   BackTest child 데드락)이 더 이상 발생하지 않는다. 검증된 빠른 스코프는
    #   단일 종목 MIN 5일 윈도우(~수십초)다.
    bt_timeframe: str = "min"  # 'min' | 'tick'
    bt_scope: str = "single_stock"  # 'single_stock' (MVP fast) | 'universe' (느림)
    bt_one_code: Optional[str] = None  # None이면 런타임에 유동성 높은 종목 자동 선택
    bt_start: Optional[int] = None  # YYYYMMDD; None이면 min DB 거래일에서 자동 산출
    bt_end: Optional[int] = None  # YYYYMMDD; None이면 자동 산출
    bt_universe_cap: int = 1  # single_stock 스코프에서 평가할 종목 수 (MVP=1)
    bt_engine_count: int = 1  # 단일 종목은 엔진 1개로 충분 (윈도우 일자 수 >= 엔진 수 제약 회피)
    bt_window_days: int = 5  # 단일 종목 백테스트 윈도우 거래일 수
    #   (1일 윈도우는 집계 프로토콜이 멈추는 경향이 있어 5일이 안전한 하한.
    #    검증된 단일 종목 5일 런은 ~수십초에 csv_detected까지 도달한다.)
    bt_timeout: int = 300  # 초; BOUNDED 스코프는 이 한참 아래에서 끝나야 한다

    # --- 루프 종료/비용 제어 (US-005 Phase 2b) ---
    # target_score: None이면 점수 기반 조기 종료 없음. 값이 있으면
    #   best_score >= target_score 일 때 루프가 조기 종료한다.
    target_score: Optional[float] = None
    # max_generations: 생성 세대 수 상한. 이 세대 수에 도달하면 종료한다.
    max_generations: int = 20
    # cost_cap_generations: gpt_auth(불투명 $ 과금)처럼 토큰 비용을 합산할 수
    #   없는 provider의 비용 안전장치. 누적 LLM 호출이 (세대 단위로 본)
    #   이 한도에 도달하면 종료한다. 토큰 cap을 쓸 수 있는 provider에서는
    #   cost_cap_tokens가 우선한다.
    cost_cap_generations: int = 50
    # cost_cap_tokens: None이면 토큰 기반 cap 없음 (gpt_auth 기본 경로).
    #   값이 있으면 누적 total_tokens >= cost_cap_tokens 일 때 종료한다.
    cost_cap_tokens: Optional[int] = None

    # --- 부검 피드백 (US-006 Phase 3) ---
    # autopsy_enabled: True면 루프 CLI가 기본 autopsy_fn(working-window 거래 통계
    #   → 다음 세대 프롬프트 NL 피드백)을 자동으로 공급한다. run_loop에 명시적
    #   autopsy_fn을 넘기면 그쪽이 우선한다. 기본 ON (loop CLI 학습 신호).
    autopsy_enabled: bool = True

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "LoopConfig":
        """dict에서 LoopConfig 생성. 알 수 없는 키는 무시한다."""
        if not data:
            return cls()
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    def to_dict(self) -> Dict[str, Any]:
        """현재 설정을 dict로 직렬화."""
        return {f.name: getattr(self, f.name) for f in fields(self)}
