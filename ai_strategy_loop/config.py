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
    model: str = "gpt-5.6-terra"
    reasoning_effort: str = "high"  # xhigh | high | medium | low; provider may capability-gate
    base_url: Optional[str] = None  # None이면 provider 기본값 사용
    api_key: Optional[str] = None  # None이면 provider별 env에서 로드
    max_retries: int = 2
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

    # --- 루프 파라미터 placeholder (이후 단계용, 아직 미사용) ---
    mdd_cap: float = 40.0
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
    # full_session_enabled: min(분봉) 타임프레임에서 장중 윈도우를 시초 28분(92800)이 아니라
    #   풀세션(bt_min_universe_end_time)까지 연다. 기본 OFF → 기존과 byte-identical(min도 92800).
    #   엔진엔 명시적 시간 게이트가 없고 start/end_time은 데이터 로딩 윈도우라, end_time을
    #   풀세션으로 열면 전략이 그 시각까지 거래 가능해진다(_build_warm_btconfig에서만 분기).
    #   tick은 데이터 자체가 09:30 캡이라 이 토글의 영향을 받지 않는다.
    full_session_enabled: bool = False
    # bt_min_universe_end_time: full_session_enabled+min일 때 쓰는 장중 윈도우 종료(HHMMSS).
    #   min 백DB(stock_min_back.db)는 15:18~moneytop 15:19까지 커버한다. 151900=15:19:00.
    bt_min_universe_end_time: int = 151900
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
    max_generations: int = 200
    # cost_cap_generations: gpt_auth(불투명 $ 과금)처럼 토큰 비용을 합산할 수
    #   없는 provider의 비용 안전장치. 누적 LLM 호출이 (세대 단위로 본)
    #   이 한도에 도달하면 종료한다. 토큰 cap을 쓸 수 있는 provider에서는
    #   cost_cap_tokens가 우선한다.
    cost_cap_generations: int = 200
    # feedback_window: 다음 세대 프롬프트에 설명/요약으로 전달할 최근 부검 개수.
    # 실제 autopsy_fn 구현이 더 좁은 경로를 쓰더라도 설정 UI는 이 값을 "피드백 참고 창"으로
    # 설명해 사용자가 피드백 윈도우 의미를 이해하게 한다.
    feedback_window: int = 8
    # Dashboard resource defaults. These are advisory/config-snapshot fields; concrete warm engine
    # paths keep their own safe engine counters unless explicitly wired.
    engine_workers: int = 0  # 0이면 launch_config가 logical CPU * 90% 기본값을 제안
    engine_mem_cap_mb: int = 0  # 0이면 launch_config가 host total memory 기반 기본값을 제안
    engine_chunk_days: int = 0  # 0이면 bt_window_days_universe 기반 최대 청크 기본값을 제안
    # cost_cap_tokens: None이면 토큰 기반 cap 없음 (gpt_auth 기본 경로).
    #   값이 있으면 누적 total_tokens >= cost_cap_tokens 일 때 종료한다.
    cost_cap_tokens: Optional[int] = None

    # --- 부검 피드백 (US-006 Phase 3) ---
    # autopsy_enabled: True면 루프 CLI가 기본 autopsy_fn(working-window 거래 통계
    #   → 다음 세대 프롬프트 NL 피드백)을 자동으로 공급한다. run_loop에 명시적
    #   autopsy_fn을 넘기면 그쪽이 우선한다. 기본 ON (loop CLI 학습 신호).
    autopsy_enabled: bool = True

    # --- Phase C-2: 5분 시초 시간대 세분 (세그먼트 부검 토글) ---
    # segment_fine_time: True면 세그먼트 부검(analyze_segments)의 시간축을 5분 시초
    #   셀(FINE_TIME_BUCKETS; 0900-0905 … 0920+ + 오전/점심/오후)로 세분한다. 비-시드
    #   생성 전략이 시초 시간대 신호를 드러내도록 한다. 기본 OFF면 기존 30분 coarse
    #   버킷이라 세그먼트 결과가 byte-동일(하위호환).
    segment_fine_time: bool = False

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
    seed_mode: str = "best_refine"  # fresh | manual_seed | best_refine
    seed_source: str = "passing"  # passing | seed_db | manual
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
    #   'multiyear'     — 다년 전구간 우상향 우선(② 다년 학습). graded 통과 분기를
    #                     composite×stability_term으로 매기며, stability_term은 결과 CSV
    #                     전구간 단일 누적곡선의 우상향 R²다(연도별 균등성 아님 — 중간 하락·
    #                     기울기 변동 허용, 사용자 평가기준 §3.21). 다년 참여 게이트로 단일년
    #                     행운만 거른다. winner는 gate 통과 중 graded 최대(강한 다년-우상향이
    #                     균등하지만 약한 전략을 이김). winner_objective!='multiyear'이면
    #                     평가조차 안 돼 기존 동작이 byte-동일 보존된다.
    #   gate 실패 분기(profit_term×mean)는 objective와 무관하게 그대로 유지한다
    #     (이미 수익을 곱셈 게이트로 반영). 통과(graded≥1.0)>실패(<1.0) 불변식도 유지.
    winner_objective: str = "risk_adjusted"  # 'risk_adjusted' | 'profit' | 'balanced' | 'multi' | 'uptrend' | 'multiyear'
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
    # --- 다년(winner_objective='multiyear') 설정 (② 다년 학습) ---
    #   multiyear는 결과 CSV 전구간 단일 누적곡선의 우상향 R²를 stability_term으로 삼아
    #   gate-passed graded에 곱한다(연도 균등성 아님 §3.21). 아래 2개는 '다년 참여 게이트'
    #   기준이다. winner_objective!='multiyear'이면 평가조차 안 돼 기존 동작 byte-동일 보존.
    multiyear_min_years: int = 2          # 참여 게이트: 유효연도<이 값이면 term=None→중립.
    multiyear_min_trades_per_year: int = 20  # 유효연도 판정 거래수 하한(부분/희소 연도 제외).
    # var_norm/cv_norm: 균등성 항 제거(§3.21)로 stability_term 산출에는 미사용 — per-year
    #   진단 필드 참고용으로만 남긴 예약 상수.
    multiyear_var_norm: float = 0.2       # (예약) stability_term 미사용.
    multiyear_cv_norm: float = 1.0        # (예약) stability_term 미사용.

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

    # --- 청산 효율 환류: edge_ratio 부검 발견을 매도(청산) 프롬프트에 환류 ---
    # Exit-edge feedback: feed the edge_ratio autopsy finding into the SELL prompt.
    # 데이터 근거(fitness/edge_ratio.py, 시드 pooled trades): edge_ratio ≈ 1.54로
    #   진입에는 방향성 엣지가 존재한다(유리 변동 > 불리 변동). 그러나
    #   mae_efficiency ≈ 0.20 — 최고 평가익의 ~20%만 실현하고 ~80%를 반납하며,
    #   손실거래의 평균 불리 변동(|MAE|)이 승리거래보다 ~2.6배 깊다(손실을 오래
    #   끌어 깊은 역행을 허용). 결론: 진입 엣지는 있고 손익을 가르는 건 *청산*이다 —
    #   손실을 더 빨리 끊고(비대칭 역행 차단), 최고 평가익을 더 많이 확정하라.
    #   The exit, not the entry, decides P/L: cut losers faster, capture more of peak.
    # exit_edge_feedback_enabled: True면 build_messages가 매도(kind=='sell') 프롬프트에
    #   이 부검 발견을 가르치는 블록을 기존 청산 지침에 더해 추가한다(타임프레임 무관
    #   범주명 — 수익률/매수후최고수익률/매수후최저수익률 — 만 사용). kind=='sell'일
    #   때만 반영되며 매수(buy)에는 영향이 없다. 기본 OFF면 이 블록이 미추가되어
    #   build_messages 출력이 기존과 byte-동일하다(하위호환).
    exit_edge_feedback_enabled: bool = False

    # --- T4 반복 정제 폐루프: 패배 세그먼트 avoid 가이드 환류 (매수 프롬프트 토글) ---
    # 데이터 근거(fitness/edge_ratio.edge_by_segment): 백테 결과를 시간대×시총×등락률
    #   셀로 쪼개면 일부 셀이 만성 적자/저승률(예: 특정 시초 5분 × 상승 3~6% 구간이
    #   적자)이다. 이 '패배·불필요 구간'을 다음 세대 매수 프롬프트에 'avoid 가이드'로
    #   환류해, 루프가 스스로 불필요 구간을 줄이며 재생성하게 한다("실행→분석→불필요
    #   구간 제거→재생성" 폐루프). **하드게이트·엔진·backtest_graph 불변** — 전부
    #   프롬프트 넛지/토글/하위호환이다.
    # segment_feedback_enabled: True면 loop가 직전(또는 best) 세대 per-trade CSV를
    #   edge_by_segment(fine_time=segment_fine_time)로 분석해 '패배 셀'(total_profit<0
    #   또는 win_rate<0.45 AND count>=segment_feedback_min_count)을 NL avoid 라인으로
    #   만들어 매수(kind=='buy') 프롬프트에 추가한다(build_messages). kind=='sell'엔
    #   영향이 없다. 기본 OFF면 환류 산출/주입이 평가조차 안 돼 build_messages 출력이
    #   기존과 byte-동일하다(하위호환). 데이터 없음/부족은 빈 가이드로 흡수(graceful).
    segment_feedback_enabled: bool = False
    # segment_feedback_min_count: 패배 셀로 지목되려면 필요한 셀 최소 표본 수(잡음 배제).
    #   작은 셀의 우연한 적자/저승률을 avoid로 환류하지 않도록 하한을 둔다. 기본 8.
    #   segment_feedback_enabled=False면 이 값은 평가되지 않는다(무영향).
    segment_feedback_min_count: int = 8

    # --- Phase C-3: 생성 진입 시간 분산 유도 (매수 프롬프트 토글) ---
    # 데이터 근거: 시드는 거래가 09:00~09:05 한 분에 몰려 시간대 신호가 degenerate하다.
    #   비-시드 생성 전략이 시초 시간대(09:00~09:20)에 진입을 분산하도록 유도하면
    #   Phase C-2 5분 세분 측정으로 time-of-day 신호를 드러낼 수 있다.
    # encourage_time_dispersion: True면 build_messages가 매수(kind=='buy') 프롬프트에
    #   "진입 시점을 09:00~09:20에 분산하라" 소프트 가이드 한 줄을 추가한다. 시간 분산은
    #   정적으로 신뢰성 있게 탐지할 수 없으므로 reject/retry 게이트가 아닌 **프롬프트
    #   넛지 전용**이다(효과는 Phase D에서 측정). 매도(sell)에는 영향이 없다. 기본 OFF면
    #   이 줄이 미추가되어 build_messages 출력이 기존과 byte-동일하다(하위호환).
    encourage_time_dispersion: bool = False

    # --- 생성 품질 (A): 필터 범주 게이트 강제 + 시드급 게이팅 프롬프트 (과발화 방지) ---
    # 데이터 근거(§3.22 over-firing): refine가 빈도를 올릴 때 LLM이 진입 필터를
    #   느슨하게/적게 만들어 과발화한다(매수=True·단일조건 → 750+ 거래·OOM). 인간
    #   시드는 ~20개 필터 범주를 AND로 결합하고 시초 시간창에 한정해 307 거래로
    #   적정 게이트된다. R7.4가 입증한 "품질 판정기"는 불가능하므로, 더 거친
    #   "충분히 게이트됐는가?"라는 구조적(범주 수) 검사로 우회한다(달성 가능).
    # require_filter_gates: True면 generate_strategy가 매수(kind=='buy') 전략을 저장하기
    #   전에 서로 다른 필터 범주를 min_filter_categories개 이상 비교 조건으로 결합했는지
    #   검증하고, 부족하면 prior_error 설정 후 재시도(reject→재생성)한다. 매도(sell)에는
    #   적용하지 않는다. 또한 build_messages가 매수 프롬프트에 시드 게이팅 구조 가이드를
    #   주입한다. 기본 OFF면 이 검증/프롬프트가 평가조차 안 돼 동작이 기존과 byte-동일하다.
    require_filter_gates: bool = False
    # min_filter_categories: require_filter_gates=True일 때 매수 진입에 요구하는 최소 필터
    #   범주 수(시드는 9개 범주를 충족). 기본 5면 시총·가격/등락율·거래대금·체결강도·호가/
    #   시간창 정도의 결합을 강제한다. 튜너블 — 너무 높이면 생성이 어려워지고 너무 낮으면
    #   과발화를 못 막는다. require_filter_gates=False면 이 값은 평가되지 않는다(무영향).
    # ⚠️ 한계(구조 검사): 이 게이트는 "범주 *폭*"만 보고 "조건의 *선별성*"은 못 본다.
    #   다중 토큰 항상참 라인(예: 현재가>0 and 등락율>0 and 시가총액<9e9 and 당일거래대금>0
    #   = 4범주지만 전부 항상참)은 통과시킬 수 있다. 항상참 회피는 프롬프트 가드레일
    #   (build_messages)이 보완한다. 둘은 짝(가르침+구조하한)으로 동작한다.
    min_filter_categories: int = 5

    # --- T3 (넓은 생성 강화): 무의미한 전범위 시간창(no-op) reject (매수 PRE-SAVE 토글) ---
    # 데이터 근거(사용자 T3 + 등락률 -30~30 no-op 통찰과 동형): 생성 전략의 '시간창'을
    #   토큰 존재가 아니라 값 범위(시분초 lo/hi)로 측정하면, 일부 전략이 시간 게이트를
    #   아예 안 두거나 세션 전범위(예: `시분초 < 153000`만)를 덮어 사실상 시간 무게이트가
    #   된다. 이는 시간 분산 생성 관점에서 '작성 안 한 것'과 동치다. 이를 약하게 교정한다.
    # ⚠️ 과도강제 금지(핵심): 인간 시드 Tick_902는 09:02~09:05(3분) **좁은** 창인데
    #   다년강건 골드다. 따라서 '넓은 창 강제'로 좁은-good 전략을 reject하면 안 된다.
    #   이 토글은 **no-op(전범위=시간게이트 없음)만** reject하며, 좁은 창은 절대 reject하지
    #   않는다(is_noop_time_window가 좁은 창을 no-op으로 보지 않음 — filter_gate.py).
    # require_meaningful_time_window: True면 generate_strategy가 매수(kind=='buy') 전략을
    #   저장하기 전에 시간창이 세션 전범위를 덮는 no-op(사실상 시간 무게이트)인지 검사하고,
    #   no-op이면 prior_error 설정 후 재시도(reject→재생성)한다(require_filter_gates 미러).
    #   매도(sell)에는 적용하지 않는다. 기본 OFF면 이 검증이 평가조차 안 돼 generate_strategy
    #   동작이 기존과 byte-동일하다(하위호환). T3의 핵심은 측정·가시화이고 강제는 약한 형태만.
    require_meaningful_time_window: bool = False

    # --- 생성 few-shot 샘플 주입 (#67): 검증된 우수 전략을 K개 프롬프트에 주입 ---
    # 사용자 아이디어(#67): 검증된 우수 전략(인간 study / 게이트 통과 조건식)을 AI 생성
    #   프롬프트에 few-shot 샘플로 주면 LLM이 "변수 조합 + 다중 필터 AND 게이팅" 구조를
    #   학습해 과발화/저빈도를 줄일 수 있다. 지금까지 시드(Tick_902)만 base_code(refine
    #   출발점)로 주입됐고, 다양한 통과 전략 K개를 few-shot 코드로 주는 메커니즘은 없었다.
    # 핵심 제약(§3.14): few-shot은 **구조 학습용**이지 맹목 복제용이 아니다. 프롬프트가
    #   "구조/게이팅을 학습하되 변수값·조건을 그대로 베끼지 말라"고 명시하고, 다양성(정규화
    #   해시) 중복 제거로 단일 시드 반복을 막으며, require_filter_gates/liquidity_gate reject
    #   게이트는 그대로 유지한다(few-shot은 샘플 선택 전용 — 게이트를 우회하지 않는다).
    # few_shot_enabled: True면 _generate_pair가 select_exemplars(kind/timeframe/k/source)로
    #   few-shot 샘플을 골라 generate_strategy→build_messages에 주입한다. 기본 OFF면
    #   샘플 선택·주입이 평가조차 안 돼 생성 프롬프트가 기존과 byte-동일하다(하위호환).
    few_shot_enabled: bool = False
    # few_shot_k: 주입할 few-shot 샘플 최대 개수. 토큰 비용/다양성 균형(3 권장). 0 이하면
    #   사실상 비활성(select_exemplars가 빈 리스트). few_shot_enabled=False면 미사용(무영향).
    few_shot_k: int = 3
    # few_shot_source: 'passing'(기본) — loop_runs.db gate_passed 통과 전략 코드.
    #                  'seed_db' — 운영 _database/strategy.db 인간 study 전략(읽기 전용).
    #   few_shot_enabled=False면 미사용(무영향).
    few_shot_source: str = "passing"  # 'passing' | 'seed_db'

    # --- 생성 분류축 유도 (매수 프롬프트 토글): 넓은 시간창 + 시가총액 구분 + 등락률 구분 ---
    # 사용자 요청: 그동안 refine가 시드(09:00~09:05 5분 스캘프) 구조를 상속해 좁은 한 점에
    #   고착했다. 인간 고수 19명은 시초 전체 시간창(09:00~09:30)을 쓰고, 시가총액 티어와
    #   등락률 국면부터 의도적으로 골라 니치를 잡는다. 그래서 생성을 그 3개 분류축
    #   (시총 티어·등락률 국면·시초 전체 시간창)에서 일관된 니치를 먼저 고르도록 유도한다.
    # classification_generation_enabled: True면 build_messages가 매수(kind=='buy') 프롬프트에
    #   3개 분류축(①시가총액 구분 ②등락률 구분 ③넓은 시간창 09:00~09:30)에서 매 세대 서로
    #   다른 일관된 니치를 의도적으로 선택해 설계하라는 블록을 추가한다. require_filter_gates
    #   (범주 폭 구조 게이트)와 짝 — 넓게 고르되(축 선택) 좁게 게이트하라(니치 내 선별).
    #   kind=='buy'에만 반영되며 매도(sell)엔 영향이 없다. 기본 OFF면 이 블록이 미주입되어
    #   build_messages 출력이 기존과 byte-동일하다(하위호환).
    classification_generation_enabled: bool = False
    # Explicit 5-minute time-bucket x market-cap generation guidance for buy prompts.
    # Default OFF keeps existing prompt/gate/engine behavior unchanged.
    time_cap_bucket_generation_enabled: bool = False
    # 92000 means 09:00~09:20; 93000 adds 09:20~09:30 after bounded preflight.
    time_cap_bucket_end_time: int = 92000
    # Research OOS policy for discovery dashboards and candidate pool artifacts.
    # disabled: no OOS rejection; advisory: reference only; promotion_only: strict frozen review only.
    research_oos_mode: str = "disabled"
    # Condition-discovery preset is an additive research-governance selector.
    # fast: broad exploration, research: evidence-preserving research, promotion: frozen review.
    # It does not export/live-wire anything; policy helpers keep scores advisory and evidence authoritative.
    condition_discovery_preset: str = "fast"  # 'fast' | 'research' | 'promotion'
    condition_discovery_process: Optional[str] = None  # optional canonical selector: 1/2/3 or fast-discovery/process-research/promotion-review
    # research 프리셋 한정 tick 연구 시간창 서브밴드(HHMMSS). None(기본)이면 기존 고정
    # 90000~92800 그대로(행동 불변). 지정 시 90000 <= start < end <= 93000만 허용하고
    # 위반은 condition_discovery 해석 시점에 ValueError. fast/promotion 프리셋은
    # 오버라이드를 무시하고 고정 창을 유지한다(기존 tick 강제 패턴).
    condition_discovery_tick_window_start: Optional[int] = None
    condition_discovery_tick_window_end: Optional[int] = None
    # Sparse-positive prompt guidance for TICK candidate generation.
    # Default OFF keeps the existing prompt, hard gates, and selector behavior unchanged.
    sparse_positive_prompt_enabled: bool = False

    # --- 계산예산(exec-budget) 가드 (2026-06-10 실측: 타임아웃 지배변수는 매도식) ---
    # 데이터 근거(11/11 완벽 분리, docs/update_log/2026-06-10_condition_research_root_cause_and_plan.md §2 원인3):
    #   고가미갱신지속틱수() 같은 비유계 역스캔 + 보유 틱당 윈도우 호출 다수를 쓴 매도식은
    #   warm run 300초 타임아웃을 유발한다(같은 매수가 스칼라 매도로는 21초). 매도식은
    #   보유 종목의 모든 틱에서 평가되므로 비용이 (보유 수×보유 시간)에 곱해진다.
    # exec_budget_prompt_enabled: True면 build_messages가 매수/매도 프롬프트에 계산예산
    #   지침을 추가한다 — 매수: 싼 스칼라 게이트(좁은 시간창>초당거래대금 하한>체결강도
    #   밴드) 선행·윈도우 함수 후행(지연계산); 매도: 스칼라(수익률/최고수익률/보유시간)
    #   우선·미갱신류는 보유시간 상한과 함께만. 기본 OFF면 미추가되어 출력이 기존과
    #   byte-동일하다(하위호환).
    exec_budget_prompt_enabled: bool = False
    # sell_exec_budget_guard_enabled: True면 generate_strategy가 매도(kind=='sell') 전략을
    #   저장하기 전에 계산예산 정적 검사(brain/exec_budget.check_sell_exec_budget)를 적용해
    #   ①비유계 스캔 함수(고가/저가미갱신지속틱수) 사용(무조건 — 보유시간 상한이 있어도
    #   스캔 깊이는 당일 이력에 비례해 타임아웃됨이 실측됨), ②윈도우 함수 호출 수 >
    #   sell_max_window_calls 를 reject→prior_error 재시도한다.
    #   매수(buy)에는 적용하지 않는다(매수는 기존 구조 게이트가 담당). 기본 OFF면 이
    #   검사가 평가조차 안 돼 generate_strategy 동작이 기존과 byte-동일하다(하위호환).
    sell_exec_budget_guard_enabled: bool = False
    # sell_max_window_calls: 매도식에 허용하는 윈도우/구간 집계 함수 호출 수 상한.
    #   S_DYN(타임아웃) 8개 vs 시드매도(고속) 2~3개 실측에 근거한 기본 8. 검사 자체가
    #   OFF면 미사용(무영향).
    sell_max_window_calls: int = 8
    # --- v5.0 오더플로우 리포트 원리 어휘 주입 (매수/매도 프롬프트 토글) ---
    # 데이터 근거(같은 문서 §2 원인4·§5): 리포트 임계값 직이식 니치는 5/5 음수였으나
    #   원리 어휘 자체는 유효하다 — 시드 부검이 F11(전일동시간비) 원리를 독립 재발견.
    #   따라서 임계값이 아닌 **원리/필터 어휘**만 가르치고, 단위 보정(시가총액=억,
    #   금액류=백만원)과 "임계값은 부검 분위수로 보정"을 명시한다.
    # report_principles_enabled: True면 build_messages가 매수/매도 프롬프트에 v5.0 원리
    #   어휘 블록을 추가한다. 기본 OFF면 미추가되어 출력이 기존과 byte-동일하다(하위호환).
    report_principles_enabled: bool = False
    # --- 차트술사 구조론 핵심 원리 주입 (A-2, 2026-07-12 전수검사 보고서 P-3) ---
    # 데이터 근거: 인간 우수전략의 정의적 특성이 '구조 문맥'(박스/눌림/리테스트)인데
    #   기존 생성 어휘는 필터 조합에 갇혀 있었다(CSC-03이 정확히 이 결핍을 위반으로 정의).
    # structure_principles_prompt_enabled: True면 build_messages가 매수/매도 프롬프트에
    #   차트술사 구조론 정제 블록(principles.md P0~P15 + CSC 핵심)을 추가한다. 전문은
    #   연구 Context Pack(_FULL_STOM_SOURCE_ASSETS)이 보유. 수치 임계값은 무근거 가설로
    #   명시되며 부검 분위수 보정을 지시한다. 기본 OFF면 출력이 기존과 byte-동일하다(하위호환).
    structure_principles_prompt_enabled: bool = False

    # --- A-5: 백파인더 밴드 시드 힌트 주입 (T2 채굴 → 생성 프롬프트 배선) ---
    # band_seed_hint_enabled: True면 run 시작 시 밴드 시드 아티팩트(band_seeds.json —
    #   scripts/mine_band_seeds.py 산출)를 1회 로드해 매수 프롬프트에 '데이터 채굴 진입
    #   밴드 힌트' 블록으로 주입한다. lookahead/survivorship 편향이 있는 **생성 시드
    #   전용** 힌트라 '복제 금지·부검 분위수 보정' 고지를 함께 주입한다. 파일 없음/파싱
    #   실패는 조용히 미주입(graceful). 기본 OFF면 출력이 기존과 byte-동일하다(하위호환).
    band_seed_hint_enabled: bool = False
    # band_seed_hint_path: 아티팩트 경로. 빈 문자열이면 기본 state/band_seeds.json.
    band_seed_hint_path: str = ""
    # band_seed_hint_max_lines: 주입할 최대 힌트 라인 수(lift 내림차순 상위).
    band_seed_hint_max_lines: int = 8

    # --- 분석→생성 환류 업그레이드 (R1·R2, 2026-06-11 검토 보고서 §5) ---
    # 데이터 근거(G1): 부검이 "기준을 높여라/낮춰라"(방향)만 주면 LLM이 임의 숫자를
    #   찍는다 — 직이식 임계 5/5 음수 실측. 반사실 실증: 시드 train 307건에서
    #   '시가총액<=2100' 상한 = 총손익 106% + 2025 쇠퇴 구간 4.4배 개선을 백테 0회로 발견.
    # quantile_feedback_enabled: True면 부검 변별 라인에 승자 분위수 임계 후보를 병기
    #   (높여라→하한 후보 승자Q25/중앙값, 낮춰라→상한 후보 승자Q75/중앙값 + 인샘플 주의).
    #   기본 OFF면 summarize 출력이 기존과 byte-동일하다(하위호환).
    quantile_feedback_enabled: bool = False
    # counterfactual_feedback_enabled: True면 진입 부검 피드백 뒤에 반사실 필터 제안
    #   (fitness/counterfactual.suggest_filters — 총손익이 깎이지 않는 강화 필터만,
    #   손익 영향 숫자 포함)을 덧붙인다. 분석 전용·인샘플 advisory이며 어떤 게이트/선택도
    #   바꾸지 않는다. 기본 OFF면 피드백이 기존과 byte-동일하다(하위호환).
    counterfactual_feedback_enabled: bool = False

    # --- P3: 세그먼트별 feature_importance 환류 (매수 프롬프트 토글) ---
    # 데이터 근거: fitness/feature_importance(현재 대시보드 전용)는 결과 CSV의 B_* 진입
    #   피처가 **시간대×시총 세그먼트마다** 승/패를 얼마나 가르나(분위 승률 격차)를 산출한다.
    #   기존 부검(autopsy)은 전역 단변량만 봐서 "어느 시간대×시총에서 어느 변수가 결정적인가"
    #   라는 세그먼트별 신호가 빠졌다(예: 초소형에서 거래대금증감이 강하게 가르지만 소형에선
    #   약해지거나 뒤집힘). 이를 다음 세대 매수 프롬프트에 'prefer 힌트'로 환류한다.
    # feature_importance_feedback_enabled: True면 loop가 직전(또는 best) 세대 train CSV를
    #   feature_importance_by_segment로 분석해, 분위 승률 격차가 큰 셀×피처를 매수(kind=='buy')
    #   프롬프트에 한국어 힌트 라인으로 추가한다(build_segment_avoid와 동일 채널 재사용,
    #   매도 무영향). 신호는 train CSV에서만 산출한다(holdout 가드). 기본 OFF면 분석/주입이
    #   평가조차 안 돼 생성 프롬프트가 기존과 byte-동일하다(하위호환). 데이터 없음/부족은 빈
    #   힌트로 흡수(graceful).
    feature_importance_feedback_enabled: bool = False
    # feature_importance_feedback_min_cell: 한 세그먼트 셀이 힌트로 채택되려면 필요한 최소
    #   거래 수(잡음 셀 배제). feature_importance_feedback_enabled=False면 평가되지 않는다.
    feature_importance_feedback_min_cell: int = 20

    # --- P5: 청산 포렌식 환류 (매도 프롬프트 토글) ---
    # 데이터 근거: analyze_exits가 R_MFE/R_MAE로 산출하는 Exit Regret(조기청산 후회 —
    #   익절기회 있던 수익거래가 고점 절반도 못 지킴)·False-Break(가짜 돌파 — 손실거래가
    #   진입 후 한 번도 못 오름)는 give-back/MAE보다 한 겹 깊은 포렌식이다. 전자는 청산
    #   타이밍(트레일링/부분익절), 후자는 진입 품질을 가리킨다.
    # exit_forensics_feedback_enabled: True면 summarize_exits가 후회율·가짜돌파율이 경보
    #   문턱 이상일 때 매도(SELL) 프롬프트에 포렌식 라인을 덧붙인다. 기본 OFF면 평가조차
    #   안 돼 summarize_exits 출력이 기존과 byte-동일하다(하위호환). analyze_exits의 필드
    #   산출은 토글과 무관하게 항상 가법 수행(기존 소비자는 신규 필드 무시 → byte-동일).
    exit_forensics_feedback_enabled: bool = False

    # --- 프롬프트 영속화 (P1c): LLM 호출별 프롬프트를 loop_runs.db에 기록 ---
    # 데이터 근거(재현성): 현재 LLM 호출별 프롬프트(system+user 메시지)가 어디에도
    #   저장되지 않고 완전 휘발한다(재현성 0). 어떤 프롬프트가 어떤 전략을 낳았는지
    #   사후에 추적·재현할 수 없다. 이를 옵트인 토글로 영속화한다.
    # prompt_logging_enabled: True면 generate_strategy가 매 LLM 호출 성공 직후 그
    #   프롬프트(system_sha + user 전문 + 주입 피처 + 토큰/응답 해시)를 loop_runs.db의
    #   prompts 테이블에 기록한다. 기본 OFF면 콜백이 None으로 전달돼 프롬프트 로깅이
    #   평가조차 안 되므로 동작이 기존과 byte-동일하다(하위호환). system 전문은 정적
    #   v1 자산이라 sha만 저장하고, user 전문은 동적이라 전문 저장한다(용량 가드).
    prompt_logging_enabled: bool = False

    # --- 백테 시계열 영속화 (O2): 누적수익곡선·일별손익·낙폭을 loop_runs.db에 다운샘플 영속 ---
    # 데이터 근거(P1b 감사): 백테 결과의 누적 수익곡선/일별손익/낙폭 시계열은 현재
    #   거래 CSV 파일에만 있어 CSV가 지워지면 영구 소실된다. 이를 DB로 다운샘플 영속해
    #   ①CSV 삭제 후에도 곡선 보존 ②AI가 SQL로 낙폭구간·레짐전환·세대간 곡선 비교를
    #   분석하게 한다(후속 O1 대시보드 BacktestDetailChart가 같은 파서를 재사용).
    # equity_points_enabled: True면 record_generation 직후 결과 CSV(이미 디스크에 있는
    #   파일)를 parse_backtest_series로 읽어 시계열을 equity_points 테이블에 영속한다
    #   (추가 백테 0회·읽기 전용). 기본 OFF면 이 영속이 평가조차 안 돼 동작이 기존과
    #   byte-동일하다(하위호환). CSV 없음/파싱 실패는 no-op으로 흡수(루프 안 막음).
    equity_points_enabled: bool = False

    # --- 적응형 레짐-타이밍 (분석 전용): 시드 자기 자본곡선 추종 오버레이 ---
    # KR: **분석 전용 — 하드게이트·적합도 스코어·생성(brain) 경로에 무영향이다.** 결과
    #   CSV의 월별 손익 시계열을 만들어, 각 달에 대해 직전 lookback개월 손익 합이 음수면
    #   그 달은 FLAT(0 기여)로 두고(워밍업은 맨 앞 lookback개월만 원본 유지) always-on 대비
    #   위험조정(수익/MDD)을 비교한다. 인과적(미래 미참조) 오버레이로, 다년(2022~2026)
    #   연속 시계열 OOS에서 시드의 수익/MDD를 ~3.5배 개선함이 검증되었다. 루프 hot path에서
    #   읽히지 않으며, 대시보드(/adaptive_timing)·오프라인 분석에서만 소비한다.
    # EN: ANALYSIS-ONLY equity-curve-following overlay (no engine/gate/score/generation
    #   effect). Go FLAT in a month when the trailing lookback-month P&L sum < 0; compare
    #   risk-adjusted return vs always-on. Validated ~3.5x return/MDD across multi-year OOS.
    # adaptive_timing_enabled: 토글이지만 루프 어디서도 읽지 않는다(분석 전용). 켜고 끔이
    #   대시보드/외부 분석의 의사 표시일 뿐, 루프 동작은 기본 OFF든 ON이든 byte-동일하다.
    adaptive_timing_enabled: bool = False
    # adaptive_timing_lookback: 적응형 규칙의 trailing 윈도우(개월). 기본 2(다년 OOS 검증값).
    adaptive_timing_lookback: int = 2

    # --- 가정(Hypothesis) 루프 코어 (P2a): 부검 방향성 예측을 1급 객체로 채택/기각 ---
    # 데이터 근거(§3.16-D 천장 의심): 부검(gate_failure_directive)은 이미 방향성 예측을
    #   만든다("MDD 초과→매도 손절강화", "손익 음수→진입품질↑", "거래 부족→진입완화").
    #   그러나 이 예측이 NL 문자열로 즉시 소모되고 **채택/기각 판정이 없어** refine가
    #   같은 빗나간 가정을 반복한다. 이를 1급 Hypothesis 객체로 만들고, 이미 영속되는
    #   부모 대비 숫자 델타(P1b)로 자동 채택/기각한다(추가 백테 0회). "실행→분석→가정→
    #   개선→실행" 과학적 방법 루프의 핵심 고리다.
    # hypothesis_tracking_enabled: True면 run_loop이 매 세대 부검 분기와 동일 인자로
    #   build_hypotheses(...)도 호출해 가정을 방출하고, 다음 세대로 carry한 뒤 그 세대의
    #   부모 대비 델타로 adjudicate(채택/기각)해 hypotheses_json으로 영속한다. 기본 OFF면
    #   가정 방출·저장·판정이 전혀 일어나지 않아 기존 NL 피드백·프롬프트·생성 경로가
    #   byte-동일하다(하위호환). 가정 산출/판정 실패는 흡수한다(학습 보조 경로).
    hypothesis_tracking_enabled: bool = False

    # --- T4.1: 차트술사 구조론 원리 문서 3종 (principles/constraints/idioms) ---
    # 데이터 근거: chart_sulsa_stom_quant_insight_report_v7_0.html §1.15 원문 마스터
    #   프롬프트 0~28장. 단, 문서 자체가 백테스트 미검증 가설 체계이며 모든 임계값은
    #   무근거 가설로 라벨되어 있다(문서 서두 명시).
    # principle_docs_enabled: True면 **후속 Phase 2의 Context Pack**이
    #   brain/principles.py 로더(load_principles/load_constraints/load_idioms)로
    #   원리 문서를 소비할 수 있음을 표시한다. 현 시점에는 어떤 코드 경로도 이 토글을
    #   읽지 않는다 — build_messages/generate_strategy에 연결되어 있지 않아 기본 OFF든
    #   ON이든 생성 프롬프트가 기존과 byte-동일하다(하위호환).
    principle_docs_enabled: bool = False

    # --- T4.3: 원리 일관성 게이트 (opt-in PRE-SAVE 게이트) ---
    # principle_gate_enabled: True면 generate_strategy(principle_gate_enabled=True)로
    #   배선된 경로에서 brain/principle_gate.check_principle_consistency 의 reject
    #   severity 위반(CSC-06 돌파-무거래량 / CSC-07 손절 부재 / CSC-10 tick 시간창)
    #   시 저장 거부→재시도한다. advisory(PG-META-01)는 로그만 남긴다.
    #   2026-07-12(A-3): controller/loop.py::_generate_pair가 이 토글을 getattr로 읽어
    #   generate_strategy(principle_gate_enabled=...)에 전달한다(배선 완료). 기본 OFF면
    #   어떤 코드 경로도 게이트를 평가하지 않아 동작이 기존과 byte-동일하다(하위호환).
    principle_gate_enabled: bool = False
    # --- CL-R05/R06 review fix (G003): declared evidence-ledger feature flag ---
    # evidence_ledger_enabled: canonical evidence ledger (CandidatePassport/
    #   FeedbackEnvelope/FeedbackConsumption/RunReceipt append-only wiring in
    #   controller/loop.py) 기동 토글. 기본 OFF면 evidence_store 관련 코드 경로
    #   전체가 스킵되어 동작이 기존과 byte-동일하다(하위호환). 이전에는 config.py에
    #   선언되지 않은 채 loop.py에서 getattr(config, "evidence_ledger_enabled", False)로
    #   ad-hoc 읽혔다 — 오타(예: evidence_ledger_enable)가 조용히 OFF로 흡수되는 것을
    #   막기 위해 여기 정식 필드로 선언한다(R07 활성화 전 CL-R05/R06 리뷰 시정).
    evidence_ledger_enabled: bool = False
    # --- DR-02: Manifest v2 (additive, opt-in) — controller/loop.py + evidence_contract.py ---
    # manifest_v2_enabled: True면 run 시작 시 이미 만들어지는 EvaluationManifest(v1) 옆에
    #   evidence_contract.ManifestV2(효과적 프로파일 해시/이름 + data/universe/engine/
    #   cost/fill/capital/session/prompt/seed/code/config 전체 바인딩)를 추가로 빌드한다.
    #   v1 EvaluationManifest/DB 스키마/evidence_store는 전혀 건드리지 않으며(영속화 없음),
    #   빌드 실패는 흡수한다(루프를 막지 않음). 기본 OFF면 run_loop 동작이 기존과
    #   byte-동일하다(하위호환) — v11 기동 불변.
    manifest_v2_enabled: bool = False
    # v2_certification_enabled: True면 (향후 인증 파이프라인이) ManifestV2 필수 카테고리
    #   결측을 fail-closed로 차단해야 한다는 선언적 의도 플래그다. 현재 어떤 코드 경로도
    #   이 플래그를 평가하지 않는다(순수 선언; 하위호환). Manifest v2 자체의 fail-closed
    #   검증(evidence_contract.build_manifest_v2/ManifestV2.__post_init__)은 이 플래그와
    #   무관하게 항상 적용된다.
    v2_certification_enabled: bool = False
    # --- DR-05 / DR-04 review fix (아키텍트 재리뷰): 토글을 정식 LoopConfig 필드로 선언 ---
    # analysis_card_v3_enabled: DR-05 AnalysisCardV3(영속·해시 카드) 산출/환류 토글.
    #   이전에는 config.py에 미선언 상태로 loop.py에서 ad-hoc getattr만 읽혀,
    #   run_loop이 config = effective_condition_discovery_runtime_config(config)로
    #   dataclasses.replace() 복제한 '뒤'에 읽는 이 플래그가 항상 False로 떨어져(복제가
    #   ad-hoc 속성을 버림) DR-05가 운영 경로에서 절대 켜지지 않았다. 정식 필드로 선언해
    #   from_dict/프리셋 도달 + replace() 생존을 보장한다(manifest_v2_enabled와 동일 패턴).
    #   기본 OFF면 카드 산출/환류가 전혀 안 일어나 byte-동일(하위호환).
    analysis_card_v3_enabled: bool = False
    # candidate_dedup_enabled / seed_plan_enabled: DR-04 후보 run-wide 중복제거 / SeedPlan
    #   토글. 종전엔 미선언 ad-hoc 속성이라 setattr로만 켤 수 있고 from_dict/프리셋으로는
    #   도달 불가했다(replace() 직전 로컬 캡처로 setattr 경로만 보존). 정식 필드로 선언해
    #   토글 선언 규약을 통일하고 from_dict 도달성을 확보한다. 기본 OFF면 byte-동일.
    candidate_dedup_enabled: bool = False
    seed_plan_enabled: bool = False

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


# =====================================================================
# 연구 환류 오버라이드 세트 (명시적 opt-in 스위치 묶음)
# =====================================================================
def research_feedback_config_overrides() -> Dict[str, bool]:
    """연구 레인 환류 토글 4종을 한 번에 켜는 오버라이드 dict를 돌려준다(문서화된 opt-in).

    "실행→분석→환류→재생성" 폐루프를 구성하는 4종 토글의 정본(canonical) 세트다:
      - segment_feedback_enabled: 패배 구간 avoid 라인 환류(T4).
      - quantile_feedback_enabled: 부검 변별 라인에 승자 분위수 임계 후보 병기(R1).
      - hypothesis_tracking_enabled: 부검 방향성 가정 방출·채택/기각 판정(P2a).
      - feature_importance_feedback_enabled: 세그먼트별 결정 피처 prefer 힌트(P3).

    전역 LoopConfig 기본값은 전부 OFF(False)로 유지한다 — 이 함수는 기본값을 바꾸지
    않고, 호출부가 명시적으로 병합할 때만 켜진다(예: LoopConfig.from_dict({**base,
    **research_feedback_config_overrides()})). 연구 레인 전용이며 승격/export/live
    권한과 무관하다(분석·프롬프트 보조 토글만 포함).

    매 호출마다 새 dict를 만들어 돌려준다(공유 상태 변이 방지 — 호출부가 자유롭게
    병합/수정해도 서로 간섭하지 않는다).
    """
    return {
        "segment_feedback_enabled": True,
        "quantile_feedback_enabled": True,
        "hypothesis_tracking_enabled": True,
        "feature_importance_feedback_enabled": True,
    }
