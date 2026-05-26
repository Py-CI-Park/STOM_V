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
    mdd_cap: float = 35.0
    min_trades: int = 30
    # overtrade_softcap: 거래수가 이 값을 넘으면 graded에서 과매매 감점을 준다.
    #   시드 105건은 안전(<=150), 과매매 248건은 감점(softcap/trade_count<1). 0이면
    #   페널티 비활성(하위호환: 기존 동작 그대로).
    overtrade_softcap: int = 150
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
    # bt_scope:
    #   'single_stock'  — '한종목 로딩' 단일 종목 + 짧은 윈도우 (MVP fast, 노이지).
    #   'small_universe'— curated subset back-DB(N개 종목) + '종목코드별 분류'.
    #                     단일 종목보다 fitness 신호가 안정적(다변화로 노이즈↓,
    #                     과적합↓)이다. 비용은 ~N배 무거우므로 N과 윈도우를 작게 둔다.
    #   'universe'      — 풀 유니버스(1379 종목). 세대 루프엔 너무 느림(~1시간).
    bt_scope: str = "single_stock"  # 'single_stock' | 'small_universe' | 'universe'
    bt_one_code: Optional[str] = None  # None이면 런타임에 유동성 높은 종목 자동 선택
    bt_start: Optional[int] = None  # YYYYMMDD; None이면 min DB 거래일에서 자동 산출
    bt_end: Optional[int] = None  # YYYYMMDD; None이면 자동 산출
    bt_universe_cap: int = 1  # single_stock 스코프에서 평가할 종목 수 (MVP=1)
    bt_engine_count: int = 1  # 단일 종목은 엔진 1개로 충분 (윈도우 일자 수 >= 엔진 수 제약 회피)
    bt_window_days: int = 5  # 단일 종목 백테스트 윈도우 거래일 수
    #   (1일 윈도우는 집계 프로토콜이 멈추는 경향이 있어 5일이 안전한 하한.
    #    검증된 단일 종목 5일 런은 ~수십초에 csv_detected까지 도달한다.)
    bt_timeout: int = 300  # 초; BOUNDED 스코프는 이 한참 아래에서 끝나야 한다
    # bt_warm_run_timeout: per-run 백테 join 타임아웃(초). over-firing 전략 fail-fast용.
    #   데이터로딩 타임아웃(BacktestConfig.timeout)과 분리된 값으로, warm_session.run의
    #   BackTest join에만 쓰인다(prepare/재로딩엔 안 쓰임). over-firing 전략은 300초까지
    #   기다릴 필요 없이 120초에 빨리 포기하고 리셋+재로딩 후 다음 run으로 넘어간다.
    #   좋은 전략(~50초)에는 영향이 없다. 미설정 시 기본 120.
    bt_warm_run_timeout: int = 120

    # --- warm 엔진 모드 (전체유니버스 웜풀 백테 세션) ---
    # bt_engine_mode:
    #   'warm' — 신규 기본. WarmBacktestSession으로 엔진 32개+데이터를 1회 prepare한 뒤
    #            세대마다 run()만 호출해 전략만 바꿔 백테한다(세대당 ~60초). 전체유니버스
    #            충실도를 유지하면서 세대별 subprocess(273초)를 제거한다.
    #   'cold' — 기존 폴백. 세대마다 stom_backtest.py 서브프로세스를 새로 띄운다
    #            (run_backtest_for 경로; BOUNDED single_stock/small_universe 스코프).
    bt_engine_mode: str = "warm"  # 'warm' | 'cold'
    bt_full_start: int = 20250101  # warm 전체유니버스 시작일 (YYYYMMDD)
    bt_full_end: int = 20251231    # warm 전체유니버스 종료일 (YYYYMMDD)
    bt_universe_start_time: int = 90000  # tick 장중 윈도우 시작 (HHMMSS)
    bt_universe_end_time: int = 92800    # tick 장중 윈도우 종료 (28분; 사용자 Tick 전략 범위)
    bt_betting: str = "5"  # 종목당 배팅(백만원 단위; 사용자 GUI=5=500만원, fidelity 핵심)
    bt_avg_time: int = 30  # 평균 틱수 (사용자=30)
    bt_warm_engine_count: int = 32  # warm 모드 엔진 수(전체유니버스; single_stock용 bt_engine_count와 별도)

    # --- small_universe 스코프 (다변화된 소형 유니버스) ---
    # bt_subset_db: build_subset_db.py가 만드는 curated subset back-DB 경로.
    #   small_universe 스코프에서 백테 서브프로세스의 STOM_CLI_DB_STRATEGY 와는
    #   별개로 STOM_CLI_DB_STOCK_BACK_MIN 을 이 경로로 오버라이드한다(cli/paths.py).
    #   그 subset의 moneytop이 N개 종목만 담으므로 '종목코드별 분류'가 정확히
    #   그 N개 종목 위에서 백테한다(엔진/CLI 무수정).
    bt_subset_db: Optional[str] = None  # None이면 런타임에 기본 경로(state/min_subset.db)
    # bt_universe_size: subset 유니버스 종목 수 N (빌더 기본 12와 일치). engine_count는
    #   '종목코드별 분류' 제약(distinct 종목 수 >= 엔진 수)을 만족하도록 N 이하로 둔다.
    bt_universe_size: int = 12
    # bt_window_days_universe: small_universe에서 쓰는 더 긴 윈도우(거래일).
    #   더 많은 종목 × 더 긴 윈도우가 신호를 안정화한다. single_stock의
    #   bt_window_days(5)는 그대로 두고, small_universe만 이 값(기본 20)을 쓴다.
    #   속도/충실도: N×window가 클수록 1회 백테가 느려지므로 bt_timeout 아래로 유지.
    bt_window_days_universe: int = 20

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

    # --- 메타분석 환류 (P4) ---
    # meta_seed_enabled: True면 생성 프롬프트에 누적 메타 인사이트(과거 여러 run에서
    #   학습한 "통과 전략 공통 변수/개선 변경/실패 패턴")를 주입한다. 기본 OFF
    #   (하위호환 — 기존 run의 프롬프트는 변하지 않는다). ON이면 run 시작 시
    #   meta_insights.json을 로드해 build_messages(meta_seed=...)로 전달한다.
    #   신호 유효성은 A/B(주입 vs 미주입)로 검증한다(계획 P4 수용기준).
    meta_seed_enabled: bool = False

    # --- seed-and-refine (시드 출발 + 점진 개선 hill-climb) ---
    # seed_buy/seed_sell: gen-0에서 생성 대신 평가할 기존 전략 이름(루프 DB).
    #   주어지면 시드가 곧 첫 출발점이 되고, refine 모드면 gen1+가 이 코드를
    #   점진 개선한다. None이면 gen-0도 fresh 생성한다(하위호환).
    seed_buy: Optional[str] = None
    seed_sell: Optional[str] = None
    # bt_refine_from_best: True면 gen1+가 현재 best 전략 코드를 출발점으로
    #   점진 개선한다(seed-and-refine hill-climb). best가 갱신되면 새 best 코드가
    #   다음 세대의 출발점이 된다. False면 매 세대 백지에서 fresh 생성(기존 동작).
    bt_refine_from_best: bool = True

    # --- 우승/선택 목표 (P7 절대수익 최적화) ---
    # winner_objective: best(graded) 선택과 winner(졸업) 갱신을 어느 목표로 할지 결정.
    #   'risk_adjusted' — 기존 기본. graded 통과 분기는 1.0+composite(Calmar×R²),
    #                     winner는 하드 composite(fit.score) 최고. **하위호환 보장.**
    #   'profit'        — 절대수익 우선. graded 통과 분기는 1.0+profit_term(정규화 수익
    #                     로지스틱)이라 통과 전략 중 수익 클수록 graded 높다. winner는
    #                     gate 통과 중 total_profit 최대(동률이면 MDD 낮은 것).
    #   'balanced'      — 위험조정·수익 블렌드. graded 통과 분기는
    #                     1.0+(composite·(1-w)+profit_term·w), winner는 같은 블렌드 점수.
    #   gate 실패 분기(profit_term×mean)는 objective와 무관하게 그대로 유지한다
    #     (이미 수익을 곱셈 게이트로 반영). 통과(graded≥1.0)>실패(<1.0) 불변식도 유지.
    winner_objective: str = "risk_adjusted"  # 'risk_adjusted' | 'profit' | 'balanced'
    # profit_weight: 'balanced' 목표에서 수익항(profit_term) 가중치 w∈[0,1].
    #   composite 가중치는 (1-w). 0이면 risk_adjusted와 동일, 1이면 profit와 유사.
    profit_weight: float = 0.5

    # --- 진화 모드 (P2 GA — population 기반 진화) ---
    # evolution_mode:
    #   'hillclimb' — 기존 기본. best 1개를 출발점으로 점진 개선하는 greedy
    #                 hill-climb(seed-and-refine). run_loop의 세대 루프를 그대로 탄다.
    #   'ga'        — population 기반 진화(선택+crossover+mutation+elitism).
    #                 run_loop이 워밍업 직후 controller/ga.run_ga_loop로 단일 분기한다.
    #                 hillclimb 경로/기존 테스트는 절대 건드리지 않는다(자기완결 격리).
    #   하위호환: 기본 'hillclimb'이라 기존 run은 동작이 변하지 않는다.
    evolution_mode: str = "hillclimb"  # 'hillclimb' | 'ga'
    # ga_population: GA 한 세대의 개체 수 K. 세대당 warm_session.run을 K회 직렬
    #   호출하므로(병렬 불가), 세대당 wall-clock ≈ K×(warm run~50s)다. 작게 시작.
    ga_population: int = 6
    # ga_elite: 세대 간 무변이 보존하는 상위 개체 수(elitism). graded 상위
    #   ga_elite개는 다음 세대에 그대로 복제돼 회귀를 막는다(0 < ga_elite < ga_population).
    ga_elite: int = 2
    # ga_crossover_rate: 비-엘리트 자식 중 crossover(부모 2개 결합)로 만드는 비율.
    #   나머지는 mutation(부모 1개 점진 개선). [0,1]. 0이면 전부 mutation,
    #   1이면 전부 crossover. 기본 0.5.
    ga_crossover_rate: float = 0.5

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
