"""US-007 — 공유 launch-config (CLI = GUI).

CLI 인자 파서와 GUI/REST 폼이 **같은 경로**로 LoopConfig를 만들도록 하는 단일
진입점이다. 어느 쪽에서 들어오든 dict → config_from_dict → LoopConfig 로
수렴하므로, CLI와 대시보드가 동일한 설정 의미론을 공유한다.

  - config_from_dict(d)   : dict → LoopConfig (알 수 없는 키 무시, 누락 → 기본값).
                            LoopConfig.from_dict를 감싸 가벼운 검증을 더한다.
  - config_field_specs()  : GUI가 start-settings 폼을 렌더할 수 있게 각 사용자
                            설정 필드의 {name,label,type,default,help}를 기술한다.
"""

from __future__ import annotations

from typing import Any, Dict, List

from ai_strategy_loop.config import LoopConfig


def config_from_dict(data: Dict[str, Any] | None) -> LoopConfig:
    """dict에서 LoopConfig를 만든다 (CLI 파서 + GUI 폼 공용 경로).

    LoopConfig.from_dict는 이미 알 수 없는 키 무시 + 누락 → 기본값을 처리한다.
    여기서는 그 위에 가벼운 경계 검증을 더한다(명백히 잘못된 값은 ValueError).

    Raises:
        ValueError: provider가 허용 목록 밖이거나, max_generations < 1 등
            명백한 경계 위반 시.
    """
    cfg = LoopConfig.from_dict(data or {})

    valid_providers = ("gpt_auth", "openrouter", "codex_proxy")
    if cfg.provider not in valid_providers:
        raise ValueError(
            f"provider는 {valid_providers} 중 하나여야 합니다 (받음: {cfg.provider!r})"
        )
    if cfg.bt_timeframe not in ("min", "tick"):
        raise ValueError(
            f"bt_timeframe는 'min'|'tick'이어야 합니다 (받음: {cfg.bt_timeframe!r})"
        )
    if int(cfg.max_generations) < 1:
        raise ValueError(f"max_generations는 1 이상이어야 합니다 (받음: {cfg.max_generations})")
    if float(cfg.mdd_cap) < 0:
        raise ValueError(f"mdd_cap은 0 이상이어야 합니다 (받음: {cfg.mdd_cap})")
    if int(cfg.min_trades) < 0:
        raise ValueError(f"min_trades는 0 이상이어야 합니다 (받음: {cfg.min_trades})")

    return cfg


def config_field_specs() -> List[Dict[str, Any]]:
    """GUI/대시보드 start-settings 폼용 사용자 설정 필드 명세.

    각 항목: {name, label, type, default, help}.
      - type: 'select' | 'number' | 'bool' | 'text'
      - select 항목은 'choices'를 추가로 가진다.
      - default는 LoopConfig 기본값과 일치한다 (CLI=GUI 동일 기본값).

    경계값(mdd_cap, min_trades, target_score), 데이터 범위/스코프(bt_*),
    provider/model 을 포함한다.

    NOTE: graduation_holdout/holdout_recent_days는 현재 run_loop가 적용하지
    않는 no-op이라 GUI 폼에서 의도적으로 제외한다(노출되면 사용자가 켜도
    아무 효과 없는 거짓 UI가 된다). LoopConfig 필드 자체는 보존한다.
    TODO: holdout-graduation 배선(run_loop에서 holdout 윈도우 분리 + 게이트
    재평가)을 후속 작업으로 끝낸 뒤 이 두 필드를 폼에 복원한다.
    """
    d = LoopConfig()  # 기본값 출처 (단일 진실원).
    return [
        {
            "name": "provider", "label": "LLM Provider", "type": "select",
            "choices": ["gpt_auth", "openrouter", "codex_proxy"],
            "default": d.provider,
            "help": "전략 생성에 쓸 LLM provider. gpt_auth는 로컬 OAuth 프록시 경유.",
        },
        {
            "name": "model", "label": "Model", "type": "text", "default": d.model,
            "help": "provider별 모델명 (예: gpt-5.5).",
        },
        {
            "name": "max_generations", "label": "Max Generations", "type": "number",
            "default": d.max_generations,
            "help": "생성 세대 수 상한. 이 세대 수에 도달하면 루프가 종료한다.",
        },
        {
            "name": "target_score", "label": "Target Score", "type": "number",
            "default": d.target_score,
            "help": "비우면 점수 기반 조기 종료 없음. 값이 있으면 하드 게이트 통과 "
                    "winner 점수가 이 값 이상일 때 조기 졸업 종료.",
        },
        {
            "name": "mdd_cap", "label": "MDD Cap (%)", "type": "number",
            "default": d.mdd_cap,
            "help": "하드 게이트 경계: MDD가 이 값을 넘으면 게이트 실패.",
        },
        {
            "name": "min_trades", "label": "Min Trades", "type": "number",
            "default": d.min_trades,
            "help": "하드 게이트 경계: 거래 수가 이 값 미만이면 게이트 실패.",
        },
        # graduation_holdout / holdout_recent_days 는 run_loop 미배선(no-op)이라
        #   폼에서 제외한다 (위 docstring의 TODO 참조). LoopConfig 필드는 유지.
        {
            "name": "bt_timeframe", "label": "Backtest Timeframe", "type": "select",
            "choices": ["min", "tick"], "default": d.bt_timeframe,
            "help": "세대별 평가 백테스트 타임프레임. min(분봉)이 검증된 빠른 기본값.",
        },
        {
            "name": "bt_scope", "label": "Backtest Scope", "type": "select",
            "choices": ["single_stock", "universe"], "default": d.bt_scope,
            "help": "single_stock=MVP 빠른 평가(단일 종목), universe=느린 전체 유니버스.",
        },
        {
            "name": "bt_window_days", "label": "Backtest Window (days)", "type": "number",
            "default": d.bt_window_days,
            "help": "단일 종목 백테스트 윈도우 거래일 수 (5일이 안전한 하한).",
        },
        {
            "name": "bt_timeout", "label": "Backtest Timeout (s)", "type": "number",
            "default": d.bt_timeout,
            "help": "백테스트 1회 타임아웃(초). BOUNDED 스코프는 이 한참 아래에서 끝난다.",
        },
        {
            "name": "autopsy_enabled", "label": "Autopsy Feedback", "type": "bool",
            "default": d.autopsy_enabled,
            "help": "켜면 매 세대 거래 통계를 분석해 다음 세대 프롬프트에 NL 피드백을 준다.",
        },
        # R8 — 진화/우승 목표 (대시보드 활성 설정 패널과 함께 노출).
        {
            "name": "evolution_mode", "label": "Evolution Mode", "type": "select",
            "choices": ["hillclimb", "ga"], "default": d.evolution_mode,
            "help": "hillclimb=best 1개 점진 개선, ga=population 기반 진화(선택/교배/변이).",
        },
        {
            "name": "winner_objective", "label": "Winner Objective", "type": "select",
            "choices": ["risk_adjusted", "profit", "balanced", "multi", "uptrend", "multiyear"],
            "default": d.winner_objective,
            "help": "best/winner 선택 목표. risk_adjusted=Calmar×R², profit=절대수익, "
                    "balanced=둘의 블렌드(profit_weight), multi=calmar·R²·빈도·payoff 동일가중, "
                    "uptrend=우상향 R²(Calmar×R²×R²), multiyear=연도교차 안정성(②, composite×stability).",
        },
        {
            "name": "bt_engine_mode", "label": "Engine Mode", "type": "select",
            "choices": ["warm", "cold"], "default": d.bt_engine_mode,
            "help": "warm=전체유니버스 엔진 1회 prepare 후 세대마다 run(빠름), "
                    "cold=세대마다 서브프로세스(폴백).",
        },
        # R8 — 5종 안전/Track B 토글 (지금까지 폼·상태 어디에도 안 보이던 것).
        {
            "name": "dispersion_prompt_enabled", "label": "분산매매 프롬프트", "type": "bool",
            "default": d.dispersion_prompt_enabled,
            "help": "켜면 매수 프롬프트의 저빈도 압력을 다종목 분산(종목 수↑·종목당 발화↓) "
                    "유도로 치환한다. 기본 OFF.",
        },
        {
            "name": "dispersion_enabled", "label": "분산 적합도 보상", "type": "bool",
            "default": d.dispersion_enabled,
            "help": "켜면 게이트-실패 graded 분기에 동시보유(max_hold_count) 분산 보상항을 "
                    "가산한다. 기본 OFF.",
        },
        {
            "name": "min_hold_symbols", "label": "분산 보상 기준(동시보유 하한)", "type": "number",
            "default": d.min_hold_symbols,
            "help": "분산 보상 기준 동시보유 종목 수(보고서 6~12). 이 값 이상이면 보상항 1.0 포화.",
        },
        {
            "name": "require_liquidity_gate", "label": "거래대금 유동성 게이트 강제", "type": "bool",
            "default": d.require_liquidity_gate,
            "help": "켜면 매수 전략 저장 전 거래대금 계열 변수+비교 조건 존재를 검증하고 "
                    "없으면 재생성. 기본 OFF.",
        },
        {
            "name": "mdd_control_enabled", "label": "MDD 제어 강화(매도)", "type": "bool",
            "default": d.mdd_control_enabled,
            "help": "켜면 매도 프롬프트에 MDD 억제 최우선 블록(타이트 손절·트레일링·시간 손절)을 "
                    "추가한다. 기본 OFF.",
        },
        {
            "name": "exit_edge_feedback_enabled", "label": "청산 효율 환류(매도)", "type": "bool",
            "default": d.exit_edge_feedback_enabled,
            "help": "켜면 매도 프롬프트에 edge_ratio 부검 발견(손실 MAE가 승리 대비 ~2.6배 깊음·"
                    "최고평가익의 ~20%만 실현)을 환류하는 블록(손실 빠르게 끊기·트레일 익절)을 "
                    "추가한다. 기본 OFF.",
        },
        {
            "name": "freeze_buy_on_mdd_only", "label": "MDD-only 시 매수 동결", "type": "bool",
            "default": d.freeze_buy_on_mdd_only,
            "help": "best가 MDD만 부족(빈도·수익 통과)할 때 매수를 동결하고 매도(청산)만 재생성. 기본 ON.",
        },
        # ②C — 시초 5분 시간대 세분 / 생성 진입 시간 분산 유도 토글.
        {
            "name": "segment_fine_time", "label": "시초 5분 시간대 세분(부검)", "type": "bool",
            "default": d.segment_fine_time,
            "help": "켜면 세그먼트 부검의 시간축을 5분 시초 셀(0900-0905…0920+)로 세분한다. "
                    "비-시드 생성 전략의 시초 시간대 신호 측정용. 기본 OFF(30분 coarse).",
        },
        {
            "name": "encourage_time_dispersion", "label": "진입 시간 분산 유도(매수)", "type": "bool",
            "default": d.encourage_time_dispersion,
            "help": "켜면 매수 프롬프트에 진입을 09:00~09:20에 분산하라는 소프트 가이드를 추가한다 "
                    "(reject 아닌 넛지). 기본 OFF.",
        },
        # 생성 품질 (A) — 필터 범주 게이트 강제 + 시드급 게이팅 프롬프트(과발화 방지).
        {
            "name": "require_filter_gates", "label": "필터 범주 게이트 강제(매수)", "type": "bool",
            "default": d.require_filter_gates,
            "help": "켜면 매수 전략 저장 전 서로 다른 필터 범주를 최소 N개(아래) 비교 조건으로 "
                    "결합했는지 검증하고 부족하면 재생성한다(과발화 방지). 매수 프롬프트에 시드 "
                    "게이팅 가이드도 주입한다. 기본 OFF.",
        },
        {
            "name": "min_filter_categories", "label": "최소 필터 범주 수", "type": "number",
            "default": d.min_filter_categories,
            "help": "필터 범주 게이트 강제 ON일 때 매수 진입에 요구하는 최소 필터 범주 수(시드는 9). "
                    "높일수록 게이팅이 엄격해진다.",
        },
        # 생성 분류축 유도(매수) — 넓은 시간창 + 시가총액 구분 + 등락률 구분부터 고려한 생성.
        {
            "name": "classification_generation_enabled", "label": "분류축 유도 생성(매수)", "type": "bool",
            "default": d.classification_generation_enabled,
            "help": "켜면 매수 프롬프트에 3개 분류축(시가총액 구분·등락률 구분·넓은 시간창 09:00~09:28)에서 "
                    "일관된 니치를 골라 설계하라는 가이드를 추가한다(시드 5분 고착 탈피). 필터 범주 게이트와 "
                    "짝(넓게 고르되 좁게 게이트). 기본 OFF.",
        },
        # 생성 few-shot 샘플 주입 (#67) — 검증된 우수 전략을 K개 프롬프트에 주입(구조 학습).
        {
            "name": "few_shot_enabled", "label": "few-shot 샘플 주입", "type": "bool",
            "default": d.few_shot_enabled,
            "help": "켜면 검증된 우수 전략(통과/인간 study) K개를 생성 프롬프트에 few-shot 코드로 "
                    "주입해 변수조합·필터 게이팅 구조를 학습시킨다(변수값 복제는 금지하도록 명시). "
                    "기본 OFF.",
        },
        {
            "name": "few_shot_k", "label": "few-shot 샘플 수(K)", "type": "number",
            "default": d.few_shot_k,
            "help": "주입할 few-shot 샘플 최대 개수(토큰/다양성 균형, 3 권장). few-shot 주입 OFF면 무영향.",
        },
        {
            "name": "few_shot_source", "label": "few-shot 출처", "type": "select",
            "choices": ["passing", "seed_db"], "default": d.few_shot_source,
            "help": "passing=루프 게이트 통과 전략, seed_db=운영 strategy.db 인간 study 전략(읽기 전용). "
                    "few-shot 주입 OFF면 무영향.",
        },
        # 프롬프트 영속화 (P1c) — LLM 호출별 프롬프트를 loop_runs.db에 기록(재현성).
        {
            "name": "prompt_logging_enabled", "label": "프롬프트 DB 영속화", "type": "bool",
            "default": d.prompt_logging_enabled,
            "help": "켜면 매 LLM 호출의 프롬프트(system 해시+user 전문+주입 피처+토큰/응답 해시)를 "
                    "loop_runs.db prompts 테이블에 기록해 사후 재현을 가능하게 한다. 기본 OFF.",
        },
        # 백테 시계열 영속화 (O2) — 누적수익곡선·일별손익·낙폭을 loop_runs.db에 다운샘플 영속.
        {
            "name": "equity_points_enabled", "label": "백테 시계열 DB 영속화", "type": "bool",
            "default": d.equity_points_enabled,
            "help": "켜면 세대마다 결과 CSV(이미 디스크에 있는 파일)의 누적수익곡선·일별손익·낙폭을 "
                    "다운샘플해 loop_runs.db equity_points 테이블에 영속한다(추가 백테 없음). CSV 삭제 "
                    "후에도 곡선이 보존되고 SQL 분석이 가능해진다. 기본 OFF.",
        },
        # 가정(Hypothesis) 루프 코어 (P2a) — 부검 방향성 예측을 1급 객체로 채택/기각.
        {
            "name": "hypothesis_tracking_enabled", "label": "가정 추적(채택/기각)", "type": "bool",
            "default": d.hypothesis_tracking_enabled,
            "help": "켜면 부검 방향성 예측(MDD↓/진입품질↑/진입완화 등)을 1급 가정으로 방출하고 "
                    "다음 세대의 부모 대비 델타로 자동 채택/기각해 generations.hypotheses_json에 "
                    "기록한다(추가 백테 없음). 기본 OFF.",
        },
    ]
