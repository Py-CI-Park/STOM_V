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
import ctypes
import os
from datetime import datetime

from typing import Any, Dict, List

from ai_strategy_loop.brain.time_cap_bucket import (
    TimeCapBucketEndTimeParseError,
    normalize_time_cap_bucket_end_time,
)
from ai_strategy_loop.config import LoopConfig
from ai_strategy_loop.controller.condition_discovery import (
    VALID_PRESETS as CONDITION_DISCOVERY_PRESETS,
    PROCESS_CATALOG as CONDITION_DISCOVERY_PROCESS_CATALOG,
    resolve_condition_discovery_process_projection,
)
from ai_strategy_loop.fitness.research_criteria import ResearchOosModeParseError, normalize_research_oos_mode


_MDD_CAP_MAX = 40.0


def _logical_cpu_count() -> int:
    return max(1, int(os.cpu_count() or 1))


def _default_worker_count() -> int:
    return max(1, int(_logical_cpu_count() * 0.9))


def _default_memory_cap_mb() -> int:
    """Return a safe host-memory default in MB without adding dependencies."""
    try:
        class _MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = _MemoryStatus()
        status.dwLength = ctypes.sizeof(_MemoryStatus)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):  # type: ignore[attr-defined]
            total_mb = int(status.ullTotalPhys // (1024 * 1024))
            return max(1024, int(total_mb * 0.9))
    except Exception:
        pass
    return 8192


def _default_chunk_days(d: LoopConfig) -> int:
    return max(1, int(getattr(d, "bt_window_days_universe", 20) or 20))


def _with_bounds(spec: Dict[str, Any], *, minimum: Any | None = None,
                 maximum: Any | None = None, step: Any | None = None) -> Dict[str, Any]:
    if minimum is not None:
        spec["min"] = minimum
    if maximum is not None:
        spec["max"] = maximum
    if step is not None:
        spec["step"] = step
    return spec

def config_from_dict(data: Dict[str, Any] | None) -> LoopConfig:
    """dict에서 LoopConfig를 만든다 (CLI 파서 + GUI 폼 공용 경로).

    LoopConfig.from_dict는 이미 알 수 없는 키 무시 + 누락 → 기본값을 처리한다.
    여기서는 그 위에 가벼운 경계 검증을 더한다(명백히 잘못된 값은 ValueError).

    Raises:
        ValueError: provider가 허용 목록 밖이거나, max_generations < 1 등
            명백한 경계 위반 시.
    """
    raw_data = data or {}
    cfg = LoopConfig.from_dict(raw_data)

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
    if float(cfg.mdd_cap) > _MDD_CAP_MAX:
        raise ValueError(f"mdd_cap은 {_MDD_CAP_MAX:g} 이하이어야 합니다 (받음: {cfg.mdd_cap})")
    if int(cfg.min_trades) < 0:
        raise ValueError(f"min_trades는 0 이상이어야 합니다 (받음: {cfg.min_trades})")
    if float(getattr(cfg, "min_daily_trades", 0.0) or 0.0) < 0:
        raise ValueError(f"min_daily_trades는 0 이상이어야 합니다 (받음: {cfg.min_daily_trades})")
    if int(getattr(cfg, "engine_workers", 0) or 0) < 0:
        raise ValueError(f"engine_workers는 0 이상이어야 합니다 (받음: {cfg.engine_workers})")
    if int(getattr(cfg, "engine_workers", 0) or 0) > _logical_cpu_count():
        raise ValueError(
            f"engine_workers는 논리 CPU 수({_logical_cpu_count()}) 이하이어야 합니다 "
            f"(받음: {cfg.engine_workers})"
        )
    if int(getattr(cfg, "engine_mem_cap_mb", 0) or 0) < 0:
        raise ValueError(f"engine_mem_cap_mb는 0 이상이어야 합니다 (받음: {cfg.engine_mem_cap_mb})")
    if int(getattr(cfg, "engine_chunk_days", 0) or 0) < 0:
        raise ValueError(f"engine_chunk_days는 0 이상이어야 합니다 (받음: {cfg.engine_chunk_days})")
    if getattr(cfg, "reasoning_effort", "xhigh") not in ("xhigh", "high", "medium", "low"):
        raise ValueError("reasoning_effort는 xhigh|high|medium|low 중 하나여야 합니다")
    if getattr(cfg, "seed_mode", "best_refine") not in ("fresh", "manual_seed", "best_refine"):
        raise ValueError("seed_mode는 fresh|manual_seed|best_refine 중 하나여야 합니다")
    if getattr(cfg, "seed_source", "passing") not in ("passing", "seed_db", "manual"):
        raise ValueError("seed_source는 passing|seed_db|manual 중 하나여야 합니다")
    normalized_dates: Dict[str, str] = {}
    for date_field in ("bt_start", "bt_end"):
        value = getattr(cfg, date_field, None)
        if value == "":
            setattr(cfg, date_field, None)
            continue
        if value is None:
            continue
        text = str(value)
        if len(text) != 8 or not text.isdigit():
            raise ValueError(f"{date_field}는 YYYYMMDD 정수 또는 빈 값이어야 합니다 (받음: {value})")
        try:
            datetime.strptime(text, "%Y%m%d")
        except ValueError as exc:
            raise ValueError(f"{date_field}는 실제 달력 날짜여야 합니다 (받음: {value})") from exc
        normalized_dates[date_field] = text
    if "bt_start" in normalized_dates and "bt_end" in normalized_dates and int(normalized_dates["bt_start"]) > int(normalized_dates["bt_end"]):
        raise ValueError(f"bt_start는 bt_end 이하이어야 합니다 ({cfg.bt_start}>{cfg.bt_end})")

    try:
        normalize_research_oos_mode(cfg.research_oos_mode)
    except ResearchOosModeParseError as exc:
        raise ValueError(str(exc)) from exc
    try:
        provided_process = raw_data.get("condition_discovery_process")
        provided_preset = raw_data.get("condition_discovery_preset")
        has_process = provided_process is not None and str(provided_process).strip() != ""
        has_preset = provided_preset is not None and str(provided_preset).strip() != ""
        projection = resolve_condition_discovery_process_projection(
            provided_process if has_process else None,
            provided_preset if has_preset else (None if has_process else getattr(cfg, "condition_discovery_preset", "fast")),
        )
        cfg.condition_discovery_preset = projection["preset"]
        if has_process or has_preset:
            cfg.condition_discovery_process = projection["process"]
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    try:
        cfg.time_cap_bucket_end_time = normalize_time_cap_bucket_end_time(cfg.time_cap_bucket_end_time)
    except TimeCapBucketEndTimeParseError as exc:
        raise ValueError(str(exc)) from exc

    return cfg


def config_field_specs() -> List[Dict[str, Any]]:
    """GUI/대시보드 start-settings 폼용 사용자 설정 필드 명세.

    각 항목: {name, label, type, default, help}.
      - type: 'select' | 'number' | 'bool' | 'text'
      - select 항목은 'choices'를 추가로 가진다.
      - default는 LoopConfig 기본값과 일치한다 (CLI=GUI 동일 기본값).

    경계값(mdd_cap, min_trades, target_score), 데이터 범위/스코프(bt_*),
    provider/model 을 포함한다.

    graduation_holdout/holdout_recent_days는 run_loop에 배선 완료되어
    (P5: gate 통과 후보를 CSV 거래일 기준 train/holdout으로 분할해 졸업검사)
    폼에 노출한다. 2026-07-16 실 A/B 파일럿에서 홀드아웃 게이트 로그로
    실동작을 확인했다.
    """
    d = LoopConfig()  # 기본값 출처 (단일 진실원).
    return [
        {
            "name": "provider", "label": "LLM Provider", "type": "select",
            "choices": ["gpt_auth", "openrouter", "codex_proxy"],
            "default": d.provider,
            "help": "전략 생성에 쓸 LLM provider. gpt_auth는 로컬 ChatGPT OAuth 프록시를 안전하게 점검한 뒤 사용한다.",
        },
        {
            "name": "model", "label": "Model", "type": "select",
            "choices": ["gpt-5.6-sol", "gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.5", "gpt-5.5-mini", "openai-codex/gpt-5.5"],
            "default": d.model,
            "help": "기본 GPT 5.6-terra. reasoning_effort는 별도 필드로 표시하며, provider가 지원하지 않으면 상태 배지로 fallback을 알린다.",
        },
        {
            "name": "reasoning_effort", "label": "Reasoning effort", "type": "select",
            "choices": ["xhigh", "high", "medium", "low"],
            "default": d.reasoning_effort,
            "help": "gpt_auth/지원 provider에서 사용할 추론 강도 선호값. 기본 high이며 미지원이면 모델 호출은 차단하지 않고 상태에 표시한다.",
        },
        _with_bounds({
            "name": "max_generations", "label": "최대 세대", "type": "number",
            "default": d.max_generations,
            "help": "생성 세대 수 상한. 장기 연구가 가능하도록 기본값을 크게 잡되, 검증 스모크는 1~2세대로 낮춰 실행한다.",
        }, minimum=1, step=1),
        _with_bounds({
            "name": "target_score", "label": "목표 적합도", "type": "number",
            "default": d.target_score,
            "help": "비우면 조기 종료 없음. 공식: gate 통과 winner_score >= 목표값이면 졸업. objective별 score는 risk_adjusted=Calmar×우상향R², multi=Calmar·R²·일평균거래·payoff 평균.",
        }, minimum=0, step="any"),
        _with_bounds({
            "name": "mdd_cap", "label": "MDD 상한(%)", "type": "number",
            "default": d.mdd_cap,
            "help": "하드 게이트: 최대 낙폭(MDD)이 이 값을 넘으면 탈락. 기본/최대 40%. 더 큰 값은 UI/백엔드에서 거부한다.",
        }, minimum=0, maximum=_MDD_CAP_MAX, step="any"),
        _with_bounds({
            "name": "min_daily_trades", "label": "일평균 거래 하한", "type": "number",
            "default": d.min_daily_trades,
            "help": "일평균 거래 빈도 게이트의 주 기준. 공식: daily_avg_trades = 거래수 / 거래일수. 이 값 미만이면 과소거래로 탈락/감점한다.",
        }, minimum=0, step="any"),
        _with_bounds({
            "name": "min_trades", "label": "최소 거래수(폴백)", "type": "number",
            "default": d.min_trades,
            "help": "구형 결과처럼 일평균 거래수가 없을 때만 쓰는 폴백 하한. 주 기준은 위의 일평균 거래 하한이다.",
        }, minimum=0, step=1),
        _with_bounds({
            "name": "feedback_window", "label": "피드백 윈도우", "type": "number",
            "default": d.feedback_window,
            "help": "피드백 윈도우: 다음 세대 프롬프트에 참고할 최근 부검/실패 원인 개수. 많을수록 더 긴 연구 맥락을 보지만 토큰 비용이 늘어난다.",
        }, minimum=0, step=1),
        {
            "name": "graduation_holdout", "label": "홀드아웃 졸업검사", "type": "bool",
            "default": d.graduation_holdout,
            "help": "ON이면 gate 통과 후보를 결과 CSV의 최근 거래일 구간(홀드아웃)으로 재판정해, 홀드아웃에서도 게이트를 통과해야 졸업한다. 추가 백테스트 없이 과적합을 걸러낸다.",
        },
        _with_bounds({
            "name": "holdout_recent_days", "label": "홀드아웃 최근 거래일수", "type": "number",
            "default": d.holdout_recent_days,
            "help": "홀드아웃으로 떼어 둘 윈도우 끝 최근 거래일 수. 홀드아웃 졸업검사가 ON일 때만 적용된다.",
        }, minimum=1, step=1),
        {
            "name": "research_oos_mode", "label": "Research OOS Mode", "type": "select",
            "choices": ["disabled", "advisory", "promotion_only"], "default": d.research_oos_mode,
            "help": "disabled=OOS 없이 탐색, advisory=참고 표시만, promotion_only=후보 고정 후 최종 검증용.",
        },
        {
            "name": "condition_discovery_preset", "label": "Condition Discovery Preset", "type": "select",
            "choices": list(CONDITION_DISCOVERY_PRESETS), "default": d.condition_discovery_preset,
            "help": "fast/research는 생성·백테스트·전체기간 분석·개선 루프를 바로 연구로 실행한다. promotion은 동결 후보 승격 검토 전용이다. 점수는 advisory이고 export/live/final promotion은 별도 승인 전 차단.",
        },
        {
            "name": "condition_discovery_process", "label": "Condition Discovery Process", "type": "select",
            "choices": [entry.code for entry in CONDITION_DISCOVERY_PROCESS_CATALOG],
            "default": d.condition_discovery_process,
            "help": "프로세스 번호/코드 선택. 1 fast-discovery=빠른 연구 시작, 2 process-research=전체기간 분석·조건식 개선 루프, 3 promotion-review=동결 승격 검토. preset과 불일치하면 거부한다.",
        },
        {
            "name": "bt_timeframe", "label": "Backtest Timeframe", "type": "select",
            "choices": ["min", "tick"], "default": d.bt_timeframe,
            "help": "세대별 평가 백테스트 타임프레임. min(분봉)이 검증된 빠른 기본값.",
        },
        {
            "name": "full_session_enabled", "label": "MIN 풀세션(15시까지)", "type": "bool",
            "default": d.full_session_enabled,
            "help": "켜면 min(분봉) 백테 장중 윈도우를 시초 28분이 아니라 풀세션"
                    "(bt_min_universe_end_time)까지 연다. tick은 데이터 09:30 캡이라 무영향. 기본 OFF.",
        },
        {
            "name": "bt_min_universe_end_time", "label": "MIN 풀세션 종료(HHMMSS)", "type": "number",
            "default": d.bt_min_universe_end_time,
            "help": "full_session_enabled+min일 때 장중 윈도우 종료 시각(HHMMSS). 기본 151900(15:19).",
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
            "name": "bt_start", "label": "백테스트 시작일(YYYYMMDD)", "type": "text",
            "default": d.bt_start,
            "help": "비우면 사용 가능한 DB 최소 거래일을 자동 사용한다. 명시하면 YYYYMMDD 형식으로 검증한다.",
        },
        {
            "name": "bt_end", "label": "백테스트 종료일(YYYYMMDD)", "type": "text",
            "default": d.bt_end,
            "help": "비우면 사용 가능한 DB 최대 거래일을 자동 사용한다. 시작일보다 앞서면 실행 전 거부한다.",
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
        _with_bounds({
            "name": "engine_workers", "label": "병렬 워커수", "type": "number",
            "default": _default_worker_count(),
            "help": f"논리 CPU의 90%를 기본값으로 제안한다. 현재 감지 CPU={_logical_cpu_count()}, 기본={_default_worker_count()}. 0은 자동.",
        }, minimum=0, maximum=_logical_cpu_count(), step=1),
        _with_bounds({
            "name": "engine_mem_cap_mb", "label": "메모리 상한(MB)", "type": "number",
            "default": _default_memory_cap_mb(),
            "help": "호스트 물리 메모리의 약 90%를 기본값으로 제안한다. 0은 자동이며, 실제 엔진 경로는 자체 안전 한도를 유지한다.",
        }, minimum=0, step=1),
        _with_bounds({
            "name": "engine_chunk_days", "label": "청크 크기(일)", "type": "number",
            "default": _default_chunk_days(d),
            "help": "한 워커가 한 번에 처리하는 백테스트 날짜 청크. 기본은 현재 스코프의 최대 윈도우 기준이며 0은 자동.",
        }, minimum=0, step=1),
        {
            "name": "seed_mode", "label": "시드 선택 방식", "type": "select",
            "choices": ["fresh", "manual_seed", "best_refine"],
            "default": d.seed_mode,
            "help": "fresh=백지 생성, manual_seed=아래 seed_buy/seed_sell에서 시작, best_refine=현재 best를 점진 개선.",
        },
        {
            "name": "seed_source", "label": "시드 출처", "type": "select",
            "choices": ["passing", "seed_db", "manual"],
            "default": d.seed_source,
            "help": "passing=루프 통과 전략, seed_db=운영 DB 읽기 전용 후보, manual=직접 이름 입력. 저장/DB 쓰기는 하지 않는다.",
        },
        {
            "name": "seed_buy", "label": "매수 시드 이름", "type": "text",
            "default": d.seed_buy,
            "help": "manual_seed일 때 gen-0 매수 전략 이름. 빈 값이면 fresh 또는 best_refine 흐름을 따른다.",
        },
        {
            "name": "seed_sell", "label": "매도 시드 이름", "type": "text",
            "default": d.seed_sell,
            "help": "manual_seed일 때 gen-0 매도 전략 이름. 빈 값이면 fresh 또는 best_refine 흐름을 따른다.",
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
            "help": "켜면 매수 프롬프트에 3개 분류축(시가총액 구분·등락률 구분·넓은 시간창 09:00~09:30)에서 "
                    "일관된 니치를 골라 설계하라는 가이드를 추가한다(시드 5분 고착 탈피). 필터 범주 게이트와 "
                    "짝(넓게 고르되 좁게 게이트). 기본 OFF.",
        },
        # 생성 few-shot 샘플 주입 (#67) — 검증된 우수 전략을 K개 프롬프트에 주입(구조 학습).
        {
            "name": "time_cap_bucket_generation_enabled", "label": "5분 시간x시총 생성(매수)",
            "type": "bool", "default": d.time_cap_bucket_generation_enabled,
            "help": "켜면 매수 프롬프트에 09:00 기준 5분 시간버킷과 소형/중형/대형 시가총액 "
                    "밴드 조합 탐색 가이드를 넣는다. 기본 OFF.",
        },
        {
            "name": "time_cap_bucket_end_time", "label": "시간x시총 종료(HHMMSS)",
            "type": "select", "choices": [92000, 93000], "default": d.time_cap_bucket_end_time,
            "help": "92000=09:00~09:20 우선 탐색, 93000=09:20~09:30까지 확장. "
                    "C_T timeout 방지를 위해 92000부터 검증한다.",
        },
        {
            "name": "sparse_positive_prompt_enabled", "label": "Sparse-positive prompt", "type": "bool",
            "default": d.sparse_positive_prompt_enabled,
            "help": "Default-OFF sparse_positive_v1 generation guidance: profit > 0, MDD <= 10, trade_count 20-250, daily_avg_trades >= 0.05, payoff_ratio >= 1.05. It does not relax hard gates or selector rules.",
        },
        {
            "name": "exec_budget_prompt_enabled", "label": "계산예산 프롬프트 지침", "type": "bool",
            "default": d.exec_budget_prompt_enabled,
            "help": "켜면 매수=싼 스칼라 게이트 선행·윈도우 함수 후행(지연계산), 매도=스칼라 우선·"
                    "미갱신류는 보유시간 상한 필수 지침을 프롬프트에 추가한다(2026-06-10 실측: "
                    "타임아웃 지배변수는 매도식). 기본 OFF.",
        },
        {
            "name": "sell_exec_budget_guard_enabled", "label": "매도 계산예산 가드(PRE-SAVE)", "type": "bool",
            "default": d.sell_exec_budget_guard_enabled,
            "help": "켜면 매도 코드를 저장 전에 정적 검사해 비유계 스캔(고가/저가미갱신지속틱수, "
                    "무조건 금지 — 보유시간 상한이 있어도 타임아웃 실측)과 윈도우 호출 수 초과를 "
                    "reject→재생성한다. 기본 OFF.",
        },
        {
            "name": "sell_max_window_calls", "label": "매도 윈도우 호출 상한", "type": "number",
            "default": d.sell_max_window_calls,
            "help": "매도식에 허용하는 윈도우/구간 집계 함수 호출 수 상한(실측: 타임아웃 매도 8개 vs "
                    "고속 매도 2~3개). 가드 OFF면 무영향.",
        },
        {
            "name": "report_principles_enabled", "label": "v5.0 리포트 원리 어휘", "type": "bool",
            "default": d.report_principles_enabled,
            "help": "켜면 오더플로우 연구 리포트의 원리 어휘(수급 우위·전일동시간비·위험 필터·"
                    "시총별 동적 청산)를 프롬프트에 추가한다 — 임계값 직이식 금지·단위 보정"
                    "(시총=억, 금액=백만원) 명시. 기본 OFF.",
        },
        {
            "name": "structure_principles_prompt_enabled", "label": "차트술사 구조론 원리", "type": "bool",
            "default": d.structure_principles_prompt_enabled,
            "help": "켜면 차트술사 구조론 핵심 원리(박스/추세 이분법·종가 우선·사건거래대금·"
                    "눌림 구조·진입근거 상실 청산 — CSC 핵심)를 프롬프트에 추가한다. "
                    "수치 임계값은 무근거 가설로 명시하고 부검 분위수 보정을 지시. 기본 OFF.",
        },
        {
            "name": "band_seed_hint_enabled", "label": "백파인더 밴드 시드 힌트", "type": "bool",
            "default": d.band_seed_hint_enabled,
            "help": "켜면 채굴 아티팩트(state/band_seeds.json — scripts/mine_band_seeds.py 산출)의 "
                    "승자 셋업 밴드(q25~q75)를 매수 프롬프트 힌트로 주입한다. lookahead 편향이 "
                    "있는 생성 시드 전용(복제 금지·부검 보정 고지 포함). 파일 없으면 무시. 기본 OFF.",
        },
        {
            "name": "principle_gate_enabled", "label": "구조론 원리 일관성 게이트(T4.3)", "type": "bool",
            "default": d.principle_gate_enabled,
            "help": "켜면 저장 전 조건식 쌍을 CSC 핵심 규칙(CSC-06 무거래량 돌파 / CSC-07 손절 부재 / "
                    "CSC-10 tick 시간창)으로 검사해 reject 위반 시 재생성한다. 기본 OFF.",
        },
        {
            "name": "quantile_feedback_enabled", "label": "부검 분위수 임계 환류(R1)", "type": "bool",
            "default": d.quantile_feedback_enabled,
            "help": "켜면 진입 부검의 '높여라/낮춰라'에 승자 분위수 임계 후보(Q25/중앙값/Q75)를 "
                    "병기한다 — 방향만 주면 LLM이 임의 숫자를 찍는 문제(G1) 해소. 기본 OFF.",
        },
        {
            "name": "counterfactual_feedback_enabled", "label": "반사실 필터 환류(R2)", "type": "bool",
            "default": d.counterfactual_feedback_enabled,
            "help": "켜면 직전 백테 CSV에 '강화 필터를 걸었다면'을 백테 0회로 평가해, 총손익이 "
                    "깎이지 않는 필터 후보만 손익 영향 숫자와 함께 매수 피드백에 덧붙인다"
                    "(인샘플 advisory). 기본 OFF.",
        },
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
