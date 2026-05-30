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
    # min_daily_trades: 일평균거래횟수(거래수/거래일수) 하한 — 빈도 게이트의 주 기준.
    #   일일 시스템 트레이딩 기준 2~3일에 1회 이상(>=0.5)이 정상 빈도다. 절대
    #   거래수(min_trades)는 1년 기준이면 너무 희소해 루프가 희소 전략(일평균
    #   0.08~0.4회)으로 잘못 수렴했다. 그래서 게이트 주 기준을 일평균으로 옮긴다.
    #   metrics에 daily_avg_trades가 있으면 이 값으로 게이트를 판정하고, 없으면(구
    #   데이터/테스트) min_trades 절대 하한으로 폴백한다(하위호환).
    min_daily_trades: float = 0.5
    # overtrade_softcap: 거래수가 이 값을 넘으면 graded에서 과매매 감점을 준다.
    #   시드 105건은 안전(<=150), 과매매 248건은 감점(softcap/trade_count<1). 0이면
    #   페널티 비활성(하위호환: 기존 동작 그대로).
    overtrade_softcap: int = 150
    tpi_gate: float = 1.2
    # tpi_gate_enabled: True면 하드게이트(compute_fitness)에 매매성능지수(tpi) 조건을
    #   AND로 추가한다(빈도·MDD·흑자 다음). winner 판정 기준인 tpi>=tpi_gate(우수전략
    #   보고서 기준 1.25)를 게이트로 강제하려는 옵션이다. 기본 OFF이라 기존 게이트는
    #   불변(byte-동일) — 모든 기존 테스트가 보존된다. enabled=True여도 metrics에 tpi
    #   키가 없으면 무영향(하위호환). enabled+tpi 존재일 때만 tpi<tpi_gate를 탈락시킨다.
    tpi_gate_enabled: bool = False
    # --- 청산 품질(exit-quality) 레버 (give-back/payoff 부검 환류) ---
    # 부검(1년치): 손실의 70~88%가 give-back(평가익 2~3% 찍고 -2~-3%로 토해냄)이고
    #   payoff ratio 붕괴(1.20→0.61)가 적자 원인. 진입 피처는 승패를 못 가르고
    #   청산이 결정함. 그래서 청산 품질을 적합도 선택압력 + 프롬프트로 반영한다.
    #   **하드게이트는 불변** — 전부 가산/소프트/토글/하위호환이다.
    # exit_quality_enabled: True면 게이트-실패 graded 분기에 청산품질 항을 가산한다.
    #   metrics에 payoff_ratio/give_back_rate가 있을 때만 동작(없으면 무영향). 기본 ON.
    exit_quality_enabled: bool = True
    # payoff_target: 목표 payoff ratio(평균이익/평균손실). payoff_comp 정규화 기준.
    #   부검 목표는 1.1 이상으로 끌어올리는 것.
    payoff_target: float = 1.1
    # give_back_weight: 청산품질 항에서 give-back 억제 신호의 가중치 w∈[0,1].
    #   payoff 신호 가중치는 (1-w). 0.5면 둘을 동등하게 본다.
    give_back_weight: float = 0.5
    # give_back_mfe_threshold: give-back으로 셀 R_MFE 하한(%). 이 이상 평가익을
    #   냈는데도 손실로 마감한 거래를 give-back으로 카운트한다(loop가 CSV에서 산출).
    give_back_mfe_threshold: float = 1.5
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
    # bt_window_select: small_universe 백테 윈도우 선택 방식.
    #   'earliest' — 기본·하위호환. subset moneytop 거래일 중 **앞쪽** window_days일.
    #                (가장 이른 구간이라 종목이 아직 비활성일 수 있어 데이터 빈약 가능.)
    #   'richest'  — moneytop coverage(그 날 담긴 코드 수) 합이 최대인 연속 window_days
    #                구간. 활성 종목이 가장 많은 구간을 골라 백테 신호를 풍부하게 한다.
    #                동률이면 더 이른 구간 선택(결정론). 기본 OFF이라 기존 동작/테스트 불변.
    bt_window_select: str = "earliest"  # 'earliest' | 'richest'

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
    # freeze_buy_on_mdd_only: 타깃 처방 — best가 **MDD만 부족**(빈도·수익 통과)할 때
    #   매수(진입)를 동결(시드/best 코드 그대로 복제)하고 매도(청산)만 재생성한다.
    #   매수 LLM 호출/토큰 0. 거래수·빈도·수익을 보존한 채 청산만 탐색해 MDD를 깎는다.
    #   refine 모드 + base_buy_code 확보 + best가 MDD-only 실패일 때만 발동한다.
    #   기본 ON이지만 위 조건이 안 맞으면 무영향(하위호환). 가역적·토글.
    freeze_buy_on_mdd_only: bool = True

    # --- 우승/선택 목표 (P7 절대수익 최적화) ---
    # winner_objective: best(graded) 선택과 winner(졸업) 갱신을 어느 목표로 할지 결정.
    #   'risk_adjusted' — 기존 기본. graded 통과 분기는 1.0+composite(Calmar×R²),
    #                     winner는 하드 composite(fit.score) 최고. **하위호환 보장.**
    #   'profit'        — 절대수익 우선. graded 통과 분기는 1.0+profit_term(정규화 수익
    #                     로지스틱)이라 통과 전략 중 수익 클수록 graded 높다. winner는
    #                     gate 통과 중 total_profit 최대(동률이면 MDD 낮은 것).
    #   'balanced'      — 위험조정·수익 블렌드. graded 통과 분기는
    #                     1.0+(composite·(1-w)+profit_term·w), winner는 같은 블렌드 점수.
    #   'multi'         — 다목적(4레버 ①). graded 통과 분기를 calmar·R²·일평균빈도·payoff를
    #                     [0,1]로 정규화한 **동일가중 평균**으로 매긴다(1.0+그 평균). profit
    #                     단일 시드만 뽑아 다양성이 죽는 현 obj 대비, '고빈도이면서
    #                     위험조정 좋은' 세대를 winner/refine 방향으로 우대한다. gate 실패
    #                     분기는 다른 objective와 똑같이 불변이다(아래 참조).
    #   'uptrend'       — 우상향 추세 우선. graded 통과 분기를 composite×R²(=Calmar×R²×R²)로
    #                     매겨 누적수익 곡선이 장기 우상향(uptrend_r2 높음)에 가까운 전략을
    #                     winner/best로 우대한다(보고서 우수전략의 정의적 특성). winner는 gate
    #                     통과 중 uptrend_r2 최대(동률이면 composite). winner_objective!='uptrend'
    #                     이면 평가조차 안 돼 기존 동작이 byte-동일 보존된다.
    #   gate 실패 분기(profit_term×mean)는 objective와 무관하게 그대로 유지한다
    #     (이미 수익을 곱셈 게이트로 반영). 통과(graded≥1.0)>실패(<1.0) 불변식도 유지.
    winner_objective: str = "risk_adjusted"  # 'risk_adjusted' | 'profit' | 'balanced' | 'multi' | 'uptrend'
    # profit_weight: 'balanced' 목표에서 수익항(profit_term) 가중치 w∈[0,1].
    #   composite 가중치는 (1-w). 0이면 risk_adjusted와 동일, 1이면 profit와 유사.
    profit_weight: float = 0.5
    # --- 다목적(winner_objective='multi') 정규화 상수 (4레버 ①) ---
    # multi 분기는 calmar·R²·일평균빈도·payoff 4항을 각각 [0,1]로 정규화해 동일가중
    #   평균한다. 아래 3개는 그 정규화 기준선(보고서 우수전략 통계에 맞춘 기본값)이다.
    #   winner_objective!='multi'이면 평가조차 안 돼 기존 동작이 byte-동일 보존된다.
    # multi_calmar_norm: calmar를 [0,1]로 누르는 분모(보고서 calmar 평균선).
    #   clamp01(calmar/multi_calmar_norm) — 이 값 이상이면 1.0에 포화.
    multi_calmar_norm: float = 30.0
    # multi_payoff_norm: payoff_ratio 정규화 타겟(보고서 payoff 타겟). payoff 항은
    #   clamp01((payoff_ratio-1.0)/(multi_payoff_norm-1.0)) — 1.0(손익분기)에서 0,
    #   타겟 이상이면 1.0. 1.0 이하로 설정하면 안전하게 폴백한다(score.py).
    multi_payoff_norm: float = 1.3
    # multi_daily_target: 일평균거래수 정규화 하한(보고서 일평균 하한). 빈도 항은
    #   clamp01(daily_avg_trades/multi_daily_target) — 이 값 이상이면 1.0에 포화.
    #   '고빈도 우대'의 핵심 — 저빈도 세대를 이 항이 끌어내린다.
    multi_daily_target: float = 10.0

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

    # --- Track B 1차: 다종목 분산 기반 고빈도 유도 (분산매매 토글) ---
    # 데이터 근거: 보고서 우수전략의 고빈도(일평균10~23)는 "한 종목 다발 진입"이
    #   아니라 "여러 종목에 1~2회씩 분산된 진입"에서 온다(흑자 gen0이 24종목에 1회씩
    #   완전 분산). 현재 (1) seed-refine 프롬프트가 "거래 줄여라"로 저빈도를 압박하고,
    #   (2) 적합도가 종목분산(동시보유 max_hold_count)을 전혀 보상하지 않는다. 이를
    #   토글로 교정한다. **하드게이트 불변** — 전부 가산/소프트/토글/하위호환이다.
    # dispersion_prompt_enabled: True면 매수 seed-refine 경로의 저빈도 압력 문장을
    #   분산매매(종목당 발화↓·종목 수↑) 유도 문장으로 치환하고, 단일 종목 과발화
    #   억제 한 줄을 더한다. 기본 OFF면 기존 프롬프트가 byte-동일 유지된다(하위호환).
    dispersion_prompt_enabled: bool = False  # 프롬프트 분산 유도
    # dispersion_enabled: True면 게이트-실패 graded 분기에 동시보유(max_hold_count)
    #   보상 항을 가산한다(exit_quality_term과 동일 방식). metrics에 max_hold_count가
    #   있을 때만 동작(없으면 무영향). 기본 OFF면 graded 점수가 기존과 완전 동일하다.
    dispersion_enabled: bool = False  # 적합도 동시보유 보상
    # min_hold_symbols: 보고서 6~12 동시보유 하한(분산 보상 기준). dispersion_term은
    #   clamp01(max_hold_count / min_hold_symbols)이라, 이 값 이상이면 1.0에 포화한다.
    min_hold_symbols: float = 6.0  # 보고서 6~12 동시보유 하한(보상 기준)
    # target_daily_trades: 프롬프트 산식 노출용 목표 일평균거래수. 주어지면
    #   _report_pattern_lines(buy)의 "적정 보유 종목 수(6~12)" 문구에 산식을 덧붙인다
    #   ("6~12종목 × 종목당 일평균 1.5~2회 ≈ 일평균 {target}회"). None이면 기존 문구 그대로.
    target_daily_trades: Optional[float] = None  # 프롬프트 산식 노출용 목표 일평균거래수

    # --- Track B 2차: 거래대금 유동성 게이트 코드 강제 (PRE-SAVE 검증 토글) ---
    # 데이터 근거(R7): refine가 빈도를 올릴 때 LLM이 흑자의 핵심인 거래대금 유동성
    #   게이트(당일거래대금 절대바닥 + 당일거래대금각도 가속 윈도우 등)를 삭제해 흑자가
    #   깨진다(fullevo3·trackb1 양쪽 확인). 흑자 세대는 게이트 유지, 손실 세대는 통째 삭제.
    # require_liquidity_gate: True면 generate_strategy가 매수(kind=='buy') 전략을 저장하기
    #   전에 "거래대금 계열 변수가 비교 조건과 함께 등장"하는지 검증하고, 없으면
    #   prior_error 설정 후 재시도(reject→재생성)한다. 매도(sell)에는 적용하지 않는다.
    #   기본 OFF면 이 검증은 평가조차 안 돼 generate_strategy 동작이 기존과 byte-동일하다.
    require_liquidity_gate: bool = False

    # --- Track B 3차: MDD 제어 강화 (매도 프롬프트 토글) ---
    # 데이터 근거(trackb3 3개월): 고빈도 세대(72~348거래)가 전부 MDD 15~31로 게이트
    #   (mdd_cap 10) 탈락 → MDD 제어가 진짜 병목. 청산(매도) 품질이 MDD를 결정한다
    #   (부검: 손실의 70~88%가 give-back). 그래서 매도 프롬프트에 MDD 억제를 강화한다.
    # mdd_control_enabled: True면 build_messages가 매도(kind=='sell') 프롬프트에 MDD
    #   억제 최우선 블록(타이트 손절·트레일링·시간 손절·손실구간 신규노출 자제)을
    #   기존 청산 지침에 더해 추가한다. 매수(buy)에는 영향이 없다. 기본 OFF면 이 블록이
    #   미추가되어 build_messages 출력이 기존과 byte-동일하다(하위호환).
    mdd_control_enabled: bool = False

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
