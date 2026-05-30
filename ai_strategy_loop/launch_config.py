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
            "choices": ["risk_adjusted", "profit", "balanced", "uptrend"],
            "default": d.winner_objective,
            "help": "best/winner 선택 목표. risk_adjusted=Calmar×R², profit=절대수익, "
                    "balanced=둘의 블렌드(profit_weight), uptrend=우상향 R²(Calmar×R²×R²).",
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
            "name": "freeze_buy_on_mdd_only", "label": "MDD-only 시 매수 동결", "type": "bool",
            "default": d.freeze_buy_on_mdd_only,
            "help": "best가 MDD만 부족(빈도·수익 통과)할 때 매수를 동결하고 매도(청산)만 재생성. 기본 ON.",
        },
    ]
