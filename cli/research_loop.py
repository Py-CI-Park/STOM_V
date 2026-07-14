"""One-shot research loop for improving an existing buy strategy."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
import math
from pathlib import Path

from cli.analyzer import analyze_result_csv
from ai_strategy_loop.brain.prompt import (
    DISCOVERY_RESEARCH_PROMPT_VERSION,
    REPAIR_RESEARCH_PROMPT_VERSION,
    build_research_prompt_receipt,
    validate_research_candidate_response,
)
from ai_strategy_loop.controller.condition_discovery import (
    LANE_DISCOVERY,
    LANE_REPAIR,
    MIN_SLOTS_PER_LANE,
    PROCESS_RESEARCH,
    assess_discovery_novelty,
    build_evidence_health,
    build_research_analysis_card,
    build_research_loop_policy,
    build_validation_provenance,
    preset_policy,
    resolve_hybrid_research_slots,
    resolve_condition_discovery_process_projection,
    score_research_lane,
)
from ai_strategy_loop.controller.replay_profile import (
    CANONICAL_REPLAY_PROFILE_V1,
    ReplayProfile,
    canonical_execution_diff,
    condition_code_sha256,
)
from ai_strategy_loop.fitness.slippage_profiles import slippage_profiles_from_csv
from cli.condition_generator import (
    expression_result_from_candidate_pack,
    generate_condition_expressions_from_analysis,
    mark_diagnostic_fallback,
)
from cli.paths import DB_STOCK_BACK_MIN, DB_STOCK_BACK_TICK, DB_STRATEGY
from cli.research_iteration_v2 import build_v2_candidate_pool, candidate_from_expression
from cli.research_iteration_v3 import build_v3_candidate_pool, parse_best_expression_conditions
from cli.research_iteration_v4 import (
    annotate_candidate_rowset_proxy,
    build_v4_candidate_pool,
    select_rowset_diverse_candidates,
)
from cli.research_iteration_v5 import (
    apply_actual_rowset_selection,
    planned_v5_execution_count,
    select_actual_rowset_representatives,
)
from cli.research_iteration_v5_recovery import build_v5_recovery_candidate_pool
from cli.research_compare import (
    INSTRUMENT_COLUMNS,
    OPTIONAL_KEY_COLUMNS,
    REQUIRED_KEY_COLUMNS,
    build_round_comparison_matrix,
    compare_trade_sets,
    render_matrix_md,
)
from cli.research_metrics import NUMERIC_COLUMNS, normalize_trade_frame
from cli.research_promotion import evaluate_research_candidate
from cli.research_cleanup import (
    _CLEANUP_SAFE_FAILURE_PHASES,
    _apply_iteration_cleanup as _apply_iteration_cleanup_impl,
    _candidate_not_created_cleanup,
    _cleanup_candidate_by_name as _cleanup_candidate_by_name_impl,
    _cleanup_summary,
)
from cli.research_ranking import (
    _numeric_value,
    _rank_candidate_results,
    _rank_key,
    _rank_score,
)
from cli.research_retention import (
    annotate_candidate_retention,
    select_retention_aware_candidates,
)
from cli.research_report import build_research_report
from cli.research_runtime_metadata import (
    _candidate_expression,
    _candidate_field,
    _elapsed_value,
    _runtime_timing_summary,
)
from cli.research_runtime_output import ResearchRuntimeRecorder, ResearchRuntimeWriteError
from cli.strategy_generator import delete_strategy_from_db, generate_buy_filter_strategy, save_strategy_to_db
from cli.strategy_loader import load_strategy_from_db


_TRADE_COLUMN_ALIASES = {
    '종목코드': INSTRUMENT_COLUMNS[0],
    '종목명': INSTRUMENT_COLUMNS[1],
    '매수시간': REQUIRED_KEY_COLUMNS[0],
    '매도시간': NUMERIC_COLUMNS[1],
    '매수가': OPTIONAL_KEY_COLUMNS[0],
    '매도가': NUMERIC_COLUMNS[3],
    '수익률': NUMERIC_COLUMNS[5],
    '수익금': NUMERIC_COLUMNS[6],
}

_RETENTION_METADATA_KEYS = (
    'retention_estimate',
    'retention_filter_passed',
    'retention_fallback_used',
)

_RESEARCH_METADATA_KEYS = (
    'research_lane',
    'research_contract',
    'strict_response_validation',
    'prompt_receipt',
    'analysis_card',
    'validation_provenance',
    'discovery_novelty',
    'research_score_detail',
    'research_lane_score',
    'context_pack_id',
    'context_pack_sha256',
    'candidate_contract_id',
    'candidate_pack_id',
    'hypothesis_id',
    'mutation_axis',
    'fallback_used',
    'fallback_reason',
    'prompt_maturity_credit_allowed',
    'parent_buy_id',
    'parent_sell_id',
    'parent_buy_code',
    'parent_buy_sha256',
    'parent_sell_code',
    'parent_sell_sha256',
    'preserves_parent_structure',
)

@dataclass
class ResearchLoopConfig:
    name: str = 'AutoResearch'
    baseline_csv: str | None = None
    score_reference_csv: str | None = None
    base_buy_strategy: str = ''
    sell_strategy: str = ''
    start_date: int = 0
    end_date: int = 0
    is_tick: bool = True
    betting: str = '1'
    avg_time: object = 60
    start_time: int = 90000
    end_time: int = 152800
    engine_count: int = 4
    top_n: int = 5
    min_samples: int = 30
    quantiles: int = 10
    alpha: float = 0.05
    run_candidate: bool = True
    run_candidates: bool = False
    candidate_count: int = 5
    candidate_name_prefix: str | None = None
    cleanup_best_candidate: bool = False
    keep_loser_candidates: bool = False
    candidate_start_date: int | None = None
    candidate_end_date: int | None = None
    candidate_timeout: int | None = None
    candidate_plan_only: bool = False
    keep_failed_candidate: bool = False
    runtime_output_path: str | None = None
    max_consecutive_candidate_failures: int = 3
    min_estimated_retention: float = 0.40
    allow_retention_fallback: bool = True
    use_retention_penalty: bool = True
    candidate_pool_multiplier: int = 3
    iteration_v2_mode: str = ''
    iteration_v2_best_candidate: str = ''
    iteration_v2_best_expression: str = ''
    iteration_v2_primary_feature: str = 'B_시가총액'
    iteration_v2_trade_amount_feature: str = 'B_당일거래대금'
    iteration_v2_secondary_features: str = ''
    iteration_v2_include_secondary_only: bool = True
    iteration_v2_max_secondary_only: int = 1
    iteration_v2_duplicate_retention_tolerance: float = 0.02
    condition_discovery_preset: str = 'fast'
    condition_discovery_process: str | None = None
    hybrid_research_enabled: bool = False
    # True면 결과 dict에 replay_profile 영수증(additive 필드)을 기록한다.
    # 기본 False라 기존 결과 스키마/동작은 byte-동일(하위호환).
    record_replay_profile: bool = False
    # True면 후보 CSV로 슬리피지 다중 프로파일(tick0/1/2/3, advisory)을 계산해
    # 후보 결과에 additive 필드(slippage_profiles)로 병기한다.
    # 기본 False라 기존 결과 스키마/동작은 byte-동일(하위호환).
    slippage_profiles_enabled: bool = False
    # True면 분석 성공 후 연구 Context Pack(부모 전문+공식 지표+STOM 규칙 원천,
    # 250k 예산 fail-closed)을 조립하되 관측/영수증 전용으로만 기록한다:
    # analysis_result에 additive 추적 키(context_pack_id/context_pack_sha256/
    # research_context_pack_receipt)만 남기고 팩 전문은 결과·체크포인트 JSON에
    # 영속하지 않는다. 현 배선에서 후보 생성은 이 팩을 소비하지 않는다
    # (결정론 생성기는 해당 키를 무시하고, LLM 후보팩은 이 주입과 별개 경로에서
    # 생산된다). 소스 부족/조립 실패 시 진행을 막지 않고 context_pack_error만
    # 기록한다. 기본 False(하위호환).
    context_pack_enabled: bool = False
    # True이고 run_research_iteration(provider=...)로 provider 콜러블이 주입되면
    # 분석 성공 후 context_pack_builder.produce_research_candidate_pack으로
    # LLM 후보팩을 실생산해 analysis_result['research_candidate_pack']에 넣는다.
    # 생산 실패/None/provider 미주입은 기존 결정론 폴백(mark_diagnostic_fallback,
    # prompt credit 0)으로 자연 낙하한다. 이 모듈은 LLM을 직접 호출하지 않는다 —
    # provider는 호출자가 주입하는 Callable[[list[dict]], str]이다.
    # 기본 False(하위호환, 기존 결과 스키마 byte-동일).
    llm_candidate_pack_enabled: bool = False
    # DR-04 -- True이면 LLM 후보팩을 candidate_pool.select_official_candidate
    # (변경되지 않은 단일 최종 소유자)로 라우팅해 pack['final_owner_selection']에
    # 그 선택 결과를 additive로 싣는다. 기본 False(하위호환, 기존 결과 스키마
    # byte-동일) -- llm_candidate_pack_enabled 자체가 False면 이 플래그는 아무
    # 효과도 없다(팩 생산 자체가 스킵되므로).
    final_owner_selection_enabled: bool = False
    # 변이축 효과 원장(JSONL) 경로. 설정 시 (a) LLM 팩 생산 프롬프트에 축
    # 사전확률 라인(AxisLedger.to_prompt_lines)을 주입하고, (b) 라운드 후보
    # 평가 완료 후 각 후보의 부모 대비 delta를 AxisLedger.record로 기록한다.
    # recorded_at은 analysis_result의 기존 created_at 타임스탬프를 재사용한다
    # (원장 모듈 내 시계 금지 규약). 필수 필드 미확보 후보는 기록을 스킵하고
    # 사유만 남긴다(집계 오염 금지). 빈 문자열이면 미사용(기본, 하위호환).
    axis_ledger_path: str = ''
    # 연구 레인(process-research/hybrid) 한정 라운드 슬롯 확장 opt-in.
    # None(기본)이면 기존 4슬롯 정책 불변(byte-동일). 설정 시
    # RESEARCH_SLOTS_OVERRIDE_MIN(2)..RESEARCH_SLOTS_OVERRIDE_MAX(12) 범위의
    # 정수만 허용하고 위반은 fail-closed(validate가 반복 시작을 거부)다.
    # 확장 값은 라운드 후보 수·LLM 팩 생산 lanes·결정론 폴백 후보 수에 일관
    # 적용되며, promotion-review/fast-discovery 레인에는 영향이 없다.
    candidate_slots_override: int | None = None
    # candidate_slots_override 사용 시 레인별 쿼터 {repair: n, discovery: m}.
    # 두 레인 모두 MIN_SLOTS_PER_LANE(1) 이상 정수이고 합계가
    # candidate_slots_override와 같아야 한다(불일치·미지 레인은 fail-closed).
    # 생략하면 균등 분할(홀수면 repair 우선). candidate_slots_override 없이
    # 단독 설정도 거부한다. 기본 None(하위호환).
    candidate_lane_quota: dict | None = None
    # 라운드 교차비교 매트릭스 opt-in(T3.4). True면 반복 라운드 종료 시
    # build_round_comparison_matrix로 후보×지표(profit/MDD/trades/win_rate/
    # 슬리피지 tick2/랭크/레인/변이축) 매트릭스와 부모 대비 delta(변이 귀속),
    # baseline 대비 개선 후보 수를 계산해 JSON+Markdown 아티팩트로 저장한다.
    # 결과 dict에는 additive 요약 키(round_matrix: 경로+개선 후보 수)만 남고
    # 매트릭스 본문은 결과에 영속하지 않는다. 저장 실패/디렉터리 미해결은
    # 진행을 막지 않고 round_matrix.error에만 기록한다(무차단, advisory).
    # 기본 False(하위호환, 기존 결과 스키마 byte-동일).
    round_matrix_enabled: bool = False
    # 매트릭스 아티팩트 저장 디렉터리. 빈 문자열(기본)이면 runtime_output_path의
    # 부모 디렉터리를 쓰고, 둘 다 없으면 저장을 스킵하고 사유만 기록한다.
    # round_matrix_enabled=False면 이 값은 무시된다(하위호환).
    round_matrix_output_dir: str = ''


def _base_config_dict(config: ResearchLoopConfig) -> dict:
    """Build the backtest config for the existing baseline strategy."""
    return {
        'buy_strategy': config.base_buy_strategy,
        'sell_strategy': config.sell_strategy,
        'start_date': config.start_date,
        'end_date': config.end_date,
        'is_tick': config.is_tick,
        'betting': config.betting,
        'avg_time': config.avg_time,
        'start_time': config.start_time,
        'end_time': config.end_time,
        'engine_count': config.engine_count,
    }


def _candidate_config_dict(config: ResearchLoopConfig, strategy_name: str | None = None) -> dict:
    candidate = _base_config_dict(config)
    candidate['buy_strategy'] = strategy_name or config.name
    candidate['start_date'] = _candidate_start_date(config)
    candidate['end_date'] = _candidate_end_date(config)
    if config.candidate_timeout is not None:
        candidate['timeout'] = config.candidate_timeout
    return candidate


def _candidate_start_date(config: ResearchLoopConfig) -> int:
    return config.start_date if config.candidate_start_date is None else config.candidate_start_date


def _candidate_end_date(config: ResearchLoopConfig) -> int:
    return config.end_date if config.candidate_end_date is None else config.candidate_end_date


def _candidate_name_prefix(config: ResearchLoopConfig) -> str:
    return config.candidate_name_prefix or config.name


def _condition_discovery_projection(config: ResearchLoopConfig) -> dict:
    selector = config.condition_discovery_process
    if selector is not None and str(selector).strip():
        return resolve_condition_discovery_process_projection(selector=selector)
    return resolve_condition_discovery_process_projection(
        selector=None,
        preset=config.condition_discovery_preset,
    )


def _process_research_enabled(config: ResearchLoopConfig) -> bool:
    projection = _condition_discovery_projection(config)
    return bool(config.hybrid_research_enabled or projection['process'] == PROCESS_RESEARCH)


# 연구 레인 한정 슬롯 확장(opt-in)의 하드 경계 — 하한 2, 상한 12.
RESEARCH_SLOTS_OVERRIDE_MIN = 2
RESEARCH_SLOTS_OVERRIDE_MAX = 12
_SLOTS_OVERRIDE_LANES = (LANE_REPAIR, LANE_DISCOVERY)
_SLOTS_OVERRIDE_DECISION_REASON = 'config_candidate_slots_override'


def _candidate_slots_override_error(config: ResearchLoopConfig) -> str:
    """슬롯 확장 opt-in 필드 검증 — 문제 없으면 '' (미설정 포함).

    fail-closed 규약: 여기서 사유가 나오면 validate_research_iteration_config가
    반복 시작 자체를 거부한다. 조용한 축소/보정은 하지 않는다.
    """
    override = getattr(config, 'candidate_slots_override', None)
    quota = getattr(config, 'candidate_lane_quota', None)
    if override is None and quota is None:
        return ''
    if override is None:
        return 'candidate_lane_quota requires candidate_slots_override'
    if isinstance(override, bool) or not isinstance(override, int):
        return 'candidate_slots_override must be an integer'
    if not RESEARCH_SLOTS_OVERRIDE_MIN <= override <= RESEARCH_SLOTS_OVERRIDE_MAX:
        return (
            f'candidate_slots_override must be between {RESEARCH_SLOTS_OVERRIDE_MIN} '
            f'and {RESEARCH_SLOTS_OVERRIDE_MAX}'
        )
    if quota is None:
        return ''
    if not isinstance(quota, dict):
        return 'candidate_lane_quota must be a dict of lane -> slot count'
    unknown = sorted(str(lane) for lane in quota if str(lane) not in _SLOTS_OVERRIDE_LANES)
    if unknown:
        return f"candidate_lane_quota has unsupported lanes: {', '.join(unknown)}"
    for lane in _SLOTS_OVERRIDE_LANES:
        value = quota.get(lane)
        if value is None:
            return f'candidate_lane_quota must include lane {lane}'
        if isinstance(value, bool) or not isinstance(value, int):
            return f'candidate_lane_quota[{lane}] must be an integer'
        if value < MIN_SLOTS_PER_LANE:
            return f'candidate_lane_quota[{lane}] must be >= {MIN_SLOTS_PER_LANE}'
    quota_total = sum(int(quota[lane]) for lane in _SLOTS_OVERRIDE_LANES)
    if quota_total != override:
        return (
            f'candidate_lane_quota sum ({quota_total}) must equal '
            f'candidate_slots_override ({override})'
        )
    return ''


def _resolve_candidate_slots_override(config: ResearchLoopConfig) -> dict | None:
    """검증된 슬롯 확장 해석 — 미설정이면 None(기존 4슬롯 정책 경로 불변).

    검증 실패는 ValueError로 즉시 중단한다(fail-closed 방어선 —
    validate_research_iteration_config를 거친 경로에서는 발생하지 않는다).
    쿼터 생략 시 균등 분할(홀수면 repair 우선)로 결정론 파생한다.
    """
    override = getattr(config, 'candidate_slots_override', None)
    quota = getattr(config, 'candidate_lane_quota', None)
    if override is None and quota is None:
        return None
    error = _candidate_slots_override_error(config)
    if error:
        raise ValueError(f'candidate_slots_override_invalid: {error}')
    total = int(override)
    if quota is None:
        repair_slots = (total + 1) // 2
        slots_by_lane = {LANE_REPAIR: repair_slots, LANE_DISCOVERY: total - repair_slots}
    else:
        slots_by_lane = {lane: int(quota[lane]) for lane in _SLOTS_OVERRIDE_LANES}
    return {'slots_total': total, 'slots_by_lane': slots_by_lane}


def _override_hybrid_slots(resolution: dict) -> dict:
    """config 슬롯 확장을 resolve_hybrid_research_slots 반환 골격으로 투영.

    오버라이드는 config가 고정(pin)한 배분이라 라운드 간 시프트가 없다 —
    previous와 현재 배분이 같고 better_lane/shift는 중립값이다.
    """
    slots_by_lane = dict(resolution['slots_by_lane'])
    return {
        'schema_version': int(build_research_loop_policy()['schema_version']),
        'slots_total': int(resolution['slots_total']),
        'previous_slots_by_lane': dict(slots_by_lane),
        'slots_by_lane': slots_by_lane,
        'better_lane': None,
        'shift_applied': {'from': None, 'to': None, 'count': 0},
        'decision_reason': _SLOTS_OVERRIDE_DECISION_REASON,
        'repair_lane_score': None,
        'discovery_lane_score': None,
        'tie_breaks_used': [],
        'blockers': [],
        'authority': 'research_budget_steering_only',
    }


def _research_candidate_count(config: ResearchLoopConfig) -> int:
    if _process_research_enabled(config):
        slots_override = _resolve_candidate_slots_override(config)
        if slots_override is not None:
            return int(slots_override['slots_total'])
        return int(build_research_loop_policy()['slots_total'])
    return config.candidate_count


def _candidate_pool_size(config: ResearchLoopConfig) -> int:
    count = _research_candidate_count(config)
    return max(config.top_n, count * config.candidate_pool_multiplier)


def _split_csv_values(value: str | None) -> list[str]:
    return [item.strip() for item in (value or '').split(',') if item.strip()]


def _effective_top_n(config: ResearchLoopConfig) -> int:
    return _candidate_pool_size(config) if config.run_candidates else config.top_n


def _build_hybrid_research_plan(config: ResearchLoopConfig) -> dict:
    projection = _condition_discovery_projection(config)
    enabled = _process_research_enabled(config)
    policy = build_research_loop_policy()
    slots_override = _resolve_candidate_slots_override(config) if enabled else None
    if not enabled:
        slots = None
        candidate_count = config.candidate_count
    elif slots_override is not None:
        slots = _override_hybrid_slots(slots_override)
        candidate_count = int(slots_override['slots_total'])
    else:
        slots = resolve_hybrid_research_slots()
        candidate_count = policy['slots_total']
    plan = {
        'enabled': enabled,
        'preset': projection['preset'],
        'process': projection['process'],
        'policy': policy,
        'slots': slots,
        'candidate_count': candidate_count,
        'authority': 'research_only_no_export_live_or_final_promotion',
    }
    if slots_override is not None:
        # additive: 오버라이드가 활성일 때만 키가 생긴다 (기본 결과 스키마 불변).
        plan['candidate_slots_override'] = {
            'slots_total': int(slots_override['slots_total']),
            'slots_by_lane': dict(slots_override['slots_by_lane']),
        }
    return plan


def _iteration_candidate_count(config: ResearchLoopConfig, iteration_plan: dict | None = None) -> int:
    if iteration_plan and (iteration_plan.get('research_loop') or {}).get('enabled'):
        return int((iteration_plan.get('research_loop') or {}).get('candidate_count') or _research_candidate_count(config))
    return _research_candidate_count(config)


def _build_iteration_plan(config: ResearchLoopConfig) -> dict:
    research_loop = _build_hybrid_research_plan(config)
    candidate_count = _iteration_candidate_count(config, {'research_loop': research_loop})
    return {
        'candidate_count': candidate_count,
        'requested_candidate_count': config.candidate_count,
        'candidate_name_prefix': _candidate_name_prefix(config),
        'score_reference_csv': config.score_reference_csv,
        'effective_top_n': _effective_top_n(config),
        'candidate_pool_multiplier': config.candidate_pool_multiplier,
        'candidate_pool_size': _candidate_pool_size(config),
        'min_estimated_retention': config.min_estimated_retention,
        'allow_retention_fallback': config.allow_retention_fallback,
        'use_retention_penalty': config.use_retention_penalty,
        'candidate_start_date': _candidate_start_date(config),
        'candidate_end_date': _candidate_end_date(config),
        'candidate_timeout': config.candidate_timeout,
        'cleanup_best_candidate': config.cleanup_best_candidate,
        'keep_loser_candidates': config.keep_loser_candidates,
        'keep_failed_candidate': config.keep_failed_candidate,
        'iteration_v2_mode': config.iteration_v2_mode,
        'iteration_v2_best_candidate': config.iteration_v2_best_candidate,
        'iteration_v2_best_expression': config.iteration_v2_best_expression,
        'iteration_v2_primary_feature': config.iteration_v2_primary_feature,
        'iteration_v2_trade_amount_feature': config.iteration_v2_trade_amount_feature,
        'iteration_v2_secondary_features': _split_csv_values(config.iteration_v2_secondary_features),
        'iteration_v2_include_secondary_only': config.iteration_v2_include_secondary_only,
        'iteration_v2_max_secondary_only': config.iteration_v2_max_secondary_only,
        'iteration_v2_duplicate_retention_tolerance': config.iteration_v2_duplicate_retention_tolerance,
        'research_loop': research_loop,
    }


def _iteration_generation_metadata(
    iteration_v2: dict[str, object] | None,
    iteration_v3: dict[str, object] | None,
    iteration_v4: dict[str, object] | None = None,
    iteration_v5: dict[str, object] | None = None,
) -> dict[str, object]:
    metadata: dict[str, object] = {}
    if iteration_v2:
        metadata['iteration_v2'] = iteration_v2
    if iteration_v3:
        metadata['iteration_v3'] = iteration_v3
    if iteration_v4:
        metadata['iteration_v4'] = iteration_v4
    if iteration_v5:
        metadata['iteration_v5'] = iteration_v5
    return metadata


def _v5_candidate_pool_metadata(
    iteration_v5: dict[str, object] | None,
    retention_selection: dict | None = None,
) -> dict[str, object]:
    if not iteration_v5:
        return {}
    recovery = iteration_v5.get('recovery')
    if not isinstance(recovery, dict):
        recovery = {}
    eligible_count = iteration_v5.get('eligible_count')
    if isinstance(retention_selection, dict):
        eligible_count = retention_selection.get('eligible_count', eligible_count)
    return {
        'initial_v4_candidate_count': iteration_v5.get('initial_v4_candidate_count'),
        'recovery_attempted': recovery.get('recovery_attempted', False),
        'recovery_reason': recovery.get('recovery_reason'),
        'recovery_family_counts': recovery.get('recovery_family_counts') or {},
        'final_candidate_pool_count': recovery.get('final_candidate_pool_count'),
        'recovery_needed_count': recovery.get('recovery_needed_count'),
        'eligible_count': eligible_count,
        'execution_count': iteration_v5.get('execution_count'),
        'planned_execution_count': iteration_v5.get('planned_execution_count'),
    }


def _hybrid_lane_sequence(slots: dict | None) -> list[str]:
    if not slots:
        return []
    slots_by_lane = slots.get('slots_by_lane') or {}
    counts = {
        LANE_REPAIR: int(slots_by_lane.get(LANE_REPAIR, 0) or 0),
        LANE_DISCOVERY: int(slots_by_lane.get(LANE_DISCOVERY, 0) or 0),
    }
    sequence: list[str] = []
    while counts[LANE_REPAIR] > 0 or counts[LANE_DISCOVERY] > 0:
        for lane in (LANE_REPAIR, LANE_DISCOVERY):
            if counts[lane] > 0:
                sequence.append(lane)
                counts[lane] -= 1
    return sequence


def _prompt_version_for_lane(lane: str) -> str:
    return DISCOVERY_RESEARCH_PROMPT_VERSION if lane == LANE_DISCOVERY else REPAIR_RESEARCH_PROMPT_VERSION


def _research_prompt_timeframe(config: ResearchLoopConfig) -> str:
    return 'tick' if config.is_tick else 'min'


def _source_response_text(source_candidate: object) -> str:
    if not isinstance(source_candidate, dict):
        return ''
    for key in ('response_text', 'raw_response', 'llm_response', 'candidate_response'):
        value = source_candidate.get(key)
        if value:
            return str(value)
    return ''


def _default_strict_response_validation(
    *,
    lane: str,
    prompt_version: str,
    kind: str,
    timeframe: str,
) -> dict:
    return {
        'schema_version': 1,
        'valid': True,
        'lane': lane,
        'prompt_version': prompt_version,
        'kind': kind,
        'timeframe': timeframe,
        'code': '',
        'metadata': {},
        'code_block_count': 0,
        'metadata_present': False,
        'metadata_json_safe': True,
        'failure_reason': '',
        'source': 'non_llm_expression_candidate',
        'authority': 'mandatory_for_repair_discovery_prompt_paths',
    }


def _strict_response_validation_for_spec(
    config: ResearchLoopConfig,
    source_candidate: object,
    *,
    lane: str,
) -> dict:
    prompt_version = _prompt_version_for_lane(lane)
    timeframe = _research_prompt_timeframe(config)
    if isinstance(source_candidate, dict):
        existing = source_candidate.get('strict_response_validation')
        if isinstance(existing, dict):
            return dict(existing)
        response_text = _source_response_text(source_candidate)
        if response_text:
            return validate_research_candidate_response(
                response_text,
                expected_lane=lane,
                expected_prompt_version=prompt_version,
                expected_kind='buy',
                expected_timeframe=timeframe,
            )
    return _default_strict_response_validation(
        lane=lane,
        prompt_version=prompt_version,
        kind='buy',
        timeframe=timeframe,
    )


def _prompt_receipt_for_spec(
    config: ResearchLoopConfig,
    spec: dict,
    source_candidate: object,
    strict_validation: dict,
) -> dict:
    lane = spec.get('research_lane') or LANE_REPAIR
    prompt_version = strict_validation.get('prompt_version') or _prompt_version_for_lane(lane)
    source = source_candidate if isinstance(source_candidate, dict) else {}
    failure_reason = strict_validation.get('failure_reason') or ''
    downstream_result = 'invalid' if strict_validation.get('valid') is False else str(source.get('downstream_result') or 'not_evaluated')
    prompt_score = source.get('prompt_score', source.get('prompt_maturity_score', 50))
    if source.get('prompt_maturity_credit_allowed') is False:
        prompt_score = 0
    prompt_score_value = 50 if prompt_score in (None, '') else prompt_score
    intended_hypothesis = (
        source.get('intended_hypothesis')
        or source.get('hypothesis')
        or _format_candidate_reason(source)
        or f"analysis_candidate={spec.get('expression')}"
    )
    return build_research_prompt_receipt(
        receipt_id=f"{spec.get('strategy_name')}__prompt",
        round_id=str(source.get('round_id') or source.get('iteration_id') or 'research-loop'),
        slot_id=str(source.get('slot_id') or f"slot-{spec.get('index')}"),
        lane=lane,
        prompt_version=prompt_version,
        prompt_score=int(float(prompt_score_value)),
        intended_hypothesis=str(intended_hypothesis),
        context_pack_id=source.get('context_pack_id'),
        context_pack_sha256=source.get('context_pack_sha256'),
        candidate_pack_id=source.get('candidate_pack_id'),
        candidate_contract_id=source.get('candidate_contract_id'),
        mode_authority=source.get('mode_authority') or 'research_only',
        generation_allowed=source.get('generation_allowed'),
        full_stom_sources_included=source.get('full_stom_sources_included'),
        prompt_budget_estimated_tokens=source.get('prompt_budget_estimated_tokens'),
        parent_id=source.get('parent_id') or source.get('parent_buy_id'),
        analysis_card_id=source.get('analysis_card_id'),
        parent_buy_id=source.get('parent_buy_id') or source.get('parent_id'),
        parent_sell_id=source.get('parent_sell_id'),
        parent_buy_code=str(source.get('parent_buy_code') or source.get('parent_code') or ''),
        parent_sell_code=str(source.get('parent_sell_code') or ''),
        preserves_parent_structure=source.get('preserves_parent_structure'),
        mutation_axis=source.get('mutation_axis'),
        coverage_gap_id=source.get('coverage_gap_id'),
        discovery_target_coverage=source.get('discovery_target_coverage') or source.get('coverage_bucket_keys') or {},
        risk_note=str(source.get('risk_note') or ''),
        output_candidate_id=spec.get('strategy_name'),
        failure_reason=failure_reason,
        downstream_result=downstream_result,
        strict_response_validation=strict_validation,
    )


def _attach_research_contract_to_spec(
    config: ResearchLoopConfig,
    spec: dict,
    source_candidate: object,
    *,
    lane: str,
) -> None:
    strict_validation = _strict_response_validation_for_spec(config, source_candidate, lane=lane)
    spec['research_lane'] = lane
    prompt_receipt = _prompt_receipt_for_spec(config, spec, source_candidate, strict_validation)
    source = source_candidate if isinstance(source_candidate, dict) else {}
    for key in (
        'context_pack_id',
        'context_pack_sha256',
        'candidate_pack_id',
        'candidate_contract_id',
        'hypothesis_id',
        'mutation_axis',
        'fallback_used',
        'fallback_reason',
        'prompt_maturity_credit_allowed',
        'parent_buy_id',
        'parent_buy_code',
        'parent_buy_sha256',
        'parent_sell_id',
        'parent_sell_code',
        'parent_sell_sha256',
        'preserves_parent_structure',
    ):
        if key in source:
            spec[key] = source[key]
    contract = {
        'schema_version': 1,
        'enabled': True,
        'lane': lane,
        'strict_response_validation': strict_validation,
        'prompt_receipt': prompt_receipt,
        'context_pack_id': source.get('context_pack_id'),
        'context_pack_sha256': source.get('context_pack_sha256'),
        'candidate_contract_id': source.get('candidate_contract_id'),
        'candidate_pack_id': source.get('candidate_pack_id'),
        'hypothesis_id': source.get('hypothesis_id'),
        'mutation_axis': source.get('mutation_axis'),
        'parent_buy_id': source.get('parent_buy_id') or source.get('parent_id'),
        'parent_sell_id': source.get('parent_sell_id'),
        'preserves_parent_structure': source.get('preserves_parent_structure'),
        'parent_conditions': prompt_receipt.get('parent_conditions'),
        'fallback_used': bool(source.get('fallback_used')),
        'fallback_reason': source.get('fallback_reason') or '',
        'prompt_maturity_credit_allowed': source.get('prompt_maturity_credit_allowed') is not False,
        'authority': 'research_only_no_export_live_or_final_promotion',
    }
    spec.update({
        'research_lane': lane,
        'research_contract': contract,
        'strict_response_validation': strict_validation,
        'prompt_receipt': prompt_receipt,
    })

def _build_candidate_specs(
    config: ResearchLoopConfig,
    expression_result: dict,
    *,
    candidate_count: int | None = None,
) -> list[dict]:
    specs = []
    expressions = expression_result.get('expressions') or []
    selected = expression_result.get('selected_candidates') or []
    research_plan = _build_hybrid_research_plan(config)
    candidate_limit = (
        _iteration_candidate_count(config, {'research_loop': research_plan})
        if candidate_count is None
        else max(int(candidate_count), 0)
    )
    lane_sequence = _hybrid_lane_sequence(research_plan.get('slots')) if research_plan.get('enabled') else []
    for index, expression in enumerate(expressions[:candidate_limit], start=1):
        source_candidate = selected[index - 1] if index - 1 < len(selected) else None
        spec = {
            'index': index,
            'strategy_name': f'{_candidate_name_prefix(config)}__cand{index:03d}',
            'expression': expression,
            'expressions': [expression],
            'source_candidate': source_candidate,
        }
        if source_candidate:
            for key in _RETENTION_METADATA_KEYS:
                if key in source_candidate:
                    spec[key] = source_candidate[key]
        if research_plan.get('enabled'):
            source_lane = source_candidate.get('lane') if isinstance(source_candidate, dict) else None
            lane = source_lane if source_lane in (LANE_REPAIR, LANE_DISCOVERY) else (
                lane_sequence[index - 1] if index - 1 < len(lane_sequence) else LANE_REPAIR
            )
            _attach_research_contract_to_spec(config, spec, source_candidate, lane=lane)
        specs.append(spec)
    return specs


def _retention_candidate_diagnostics(
    candidates: list[dict],
    selected_candidates: list[dict] | None = None,
) -> list[dict]:
    selected_candidates = selected_candidates or []
    selected_by_index = {
        candidate.get('original_index'): candidate
        for candidate in selected_candidates
        if candidate.get('original_index') is not None
    }
    selected_by_expression = {
        candidate.get('expression'): candidate
        for candidate in selected_candidates
        if candidate.get('expression') is not None
    }
    diagnostics = []
    for candidate in candidates:
        selected = selected_by_index.get(candidate.get('original_index'))
        if selected is None:
            selected = selected_by_expression.get(candidate.get('expression'))
        item = {'expression': candidate.get('expression')}
        for key in (
            'original_index',
            'retention_estimate',
            'retention_filter_passed',
            'retention_fallback_used',
            'source',
            'feature',
        ):
            if key in candidate:
                item[key] = candidate[key]
        if selected is not None and 'retention_fallback_used' in selected:
            item['retention_fallback_used'] = selected['retention_fallback_used']
        diagnostics.append(item)
    return diagnostics


def _build_candidate_plan(
    config: ResearchLoopConfig,
    candidate: dict,
    strategy_name: str | None = None,
    will_save_override: bool | None = None,
) -> dict:
    """Build a stable plan describing candidate execution before side effects."""
    will_save = (
        will_save_override
        if will_save_override is not None
        else bool(config.run_candidate and not config.candidate_plan_only)
    )
    return {
        'strategy_name': strategy_name or config.name,
        'base_buy_strategy': config.base_buy_strategy,
        'sell_strategy': config.sell_strategy,
        'expression': candidate.get('expression'),
        'expressions': candidate.get('expressions', []),
        'candidate_start_date': _candidate_start_date(config),
        'candidate_end_date': _candidate_end_date(config),
        'candidate_timeout': config.candidate_timeout,
        'will_save_strategy': will_save,
        'will_run_backtest': will_save,
        'keep_failed_candidate': config.keep_failed_candidate,
    }


def _candidate_failure_phase(candidate_result: dict) -> str:
    message = str(candidate_result.get('message') or '')
    if '시간 초과' in message or 'timeout' in message.lower():
        return 'candidate_backtest_timeout'
    return 'candidate_backtest'


def _cleanup_candidate_strategy(
    config: ResearchLoopConfig,
    reason: str,
    strategy_name: str | None = None,
) -> dict:
    """Delete failed candidate strategy unless the user requested preservation."""
    candidate_name = strategy_name or config.name
    if config.keep_failed_candidate:
        return {
            'attempted': False,
            'reason': 'keep_failed_candidate',
            'strategy_name': candidate_name,
        }
    try:
        result = delete_strategy_from_db(DB_STRATEGY, candidate_name, 'buy')
    except Exception as e:
        return {
            'attempted': True,
            'reason': reason,
            'strategy_name': candidate_name,
            'status': 'error',
            'message': str(e),
        }
    return {
        'attempted': True,
        'reason': reason,
        'strategy_name': candidate_name,
        'status': result.get('status'),
        'message': result.get('message'),
        'action': result.get('action'),
    }


def _cleanup_candidate_by_name(strategy_name: str, reason: str) -> dict:
    return _cleanup_candidate_by_name_impl(
        strategy_name,
        reason,
        delete_strategy_func=delete_strategy_from_db,
    )


def _apply_iteration_cleanup(config: ResearchLoopConfig, candidates: list[dict]) -> tuple[list[dict], dict]:
    return _apply_iteration_cleanup_impl(
        config,
        candidates,
        delete_strategy_func=delete_strategy_from_db,
    )


def _error(phase: str, message: str, **extra) -> dict:
    return {'status': 'error', 'phase': phase, 'message': message, **extra}


def _initial_failure_policy(config: ResearchLoopConfig) -> dict:
    return {
        'max_consecutive_candidate_failures': config.max_consecutive_candidate_failures,
        'consecutive_candidate_failures': 0,
        'total_candidate_failures': 0,
        'aborted': False,
        'abort_reason': None,
    }


def _runtime_write_failure(path: str | None, exc: Exception, **extra) -> dict:
    return _error(
        'runtime_output_write_failure',
        str(exc),
        runtime_output_path=path,
        **extra,
    )


def _empty_cleanup_summary() -> dict:
    return {
        'attempted_count': 0,
        'deleted_count': 0,
        'kept_count': 0,
        'failed_count': 0,
        'items': [],
    }


def _finalize_research_runtime_result(
    config: ResearchLoopConfig,
    recorder: ResearchRuntimeRecorder,
    result_payload: dict,
    failure_policy: dict,
) -> dict:
    result_payload = {
        # opt-in replay 프로파일 영수증(additive). 기본 OFF면 빈 dict라 불변.
        **_replay_profile_receipt_fields(config),
        **result_payload,
        'failure_policy': failure_policy,
        'runtime_timing': _runtime_timing_summary(
            recorder,
            candidate_specs=result_payload.get('candidate_specs') or [],
            candidates=result_payload.get('candidates') or [],
        ),
    }
    result_payload = recorder.decorate(result_payload)
    try:
        recorder.write(result_payload)
    except ResearchRuntimeWriteError as exc:
        return _build_result(config, _runtime_write_failure(
            config.runtime_output_path,
            exc,
            strategy_name=result_payload.get('strategy_name', config.name),
            config=result_payload.get('config', asdict(config)),
            failure_policy=failure_policy,
            candidates=result_payload.get('candidates', []),
        ))
    return _build_result(config, result_payload)


def _flush_research_runtime_checkpoint(
    config: ResearchLoopConfig,
    recorder: ResearchRuntimeRecorder,
    *,
    phase: str,
    failure_policy: dict,
    message: str = 'research iteration in progress',
    **extra,
) -> dict | None:
    if not config.runtime_output_path:
        return None
    lightweight_extra = {
        key: value
        for key, value in extra.items()
        if key not in {
            'analysis_result',
            'baseline_result',
            'expression_result',
            'retention_candidates',
            'retention_selection',
        }
    }
    result_payload = {
        'status': 'running',
        'phase': phase,
        'message': message,
        'strategy_name': config.name,
        'config': asdict(config),
        'failure_policy': failure_policy,
        'runtime_timing': _runtime_timing_summary(
            recorder,
            candidate_specs=lightweight_extra.get('candidate_specs') or [],
            candidates=lightweight_extra.get('candidates') or [],
        ),
        **lightweight_extra,
    }
    try:
        recorder.write(result_payload)
    except ResearchRuntimeWriteError as exc:
        return _build_result(config, _runtime_write_failure(
            config.runtime_output_path,
            exc,
            strategy_name=config.name,
            config=asdict(config),
            failure_policy=failure_policy,
            candidates=extra.get('candidates', []),
        ))
    return None


def validate_research_iteration_config(config: ResearchLoopConfig) -> dict:
    projection = _condition_discovery_projection(config)
    if projection.get('process') == 'promotion-review':
        return _error(
            'promotion_review_generation_blocked',
            'promotion-review is zero-generation evidence health only; repair/discovery generation is disabled',
            condition_discovery_process=projection.get('process'),
            condition_discovery_preset=projection.get('preset'),
        )
    slots_override_error = _candidate_slots_override_error(config)
    if slots_override_error:
        # fail-closed: 슬롯 확장 opt-in 필드가 설정됐지만 유효하지 않으면
        # 반복을 시작하지 않는다 (조용한 4슬롯 축소/보정 금지).
        return _error(
            'invalid_candidate_slots_override',
            slots_override_error,
            candidate_slots_override=config.candidate_slots_override,
            candidate_lane_quota=config.candidate_lane_quota,
        )
    if config.candidate_plan_only and config.run_candidates:
        return _error(
            'candidate_plan_only_iteration_conflict',
            'candidate_plan_only cannot be used with run_candidates',
        )
    if config.run_candidates and config.candidate_count < 1:
        return _error(
            'invalid_candidate_count',
            'candidate_count must be greater than or equal to 1',
        )
    if config.run_candidates and not 0 <= config.min_estimated_retention <= 1:
        return _error(
            'invalid_min_estimated_retention',
            'min_estimated_retention must be between 0 and 1',
        )
    if config.run_candidates and config.candidate_pool_multiplier < 1:
        return _error(
            'invalid_candidate_pool_multiplier',
            'candidate_pool_multiplier must be greater than or equal to 1',
        )
    allowed_iteration_modes = {
        'best_feature_mix',
        'best_feature_mix_v3',
        'best_feature_mix_v4',
        'best_feature_mix_v5',
    }
    if config.run_candidates and config.iteration_v2_mode and config.iteration_v2_mode not in allowed_iteration_modes:
        return _error(
            'invalid_iteration_v2_mode',
            (
                'iteration_v2_mode must be empty, best_feature_mix, best_feature_mix_v3, '
                'best_feature_mix_v4, or best_feature_mix_v5'
            ),
        )
    if config.run_candidates and config.iteration_v2_max_secondary_only < 0:
        return _error(
            'invalid_iteration_v2_max_secondary_only',
            'iteration_v2_max_secondary_only must be greater than or equal to 0',
        )
    if config.run_candidates and config.iteration_v2_mode and not config.iteration_v2_best_expression:
        return _error(
            'missing_iteration_v2_best_expression',
            'iteration_v2_best_expression is required when iteration_v2_mode is set',
        )
    if config.run_candidates and config.iteration_v2_mode in {
        'best_feature_mix_v3',
        'best_feature_mix_v4',
        'best_feature_mix_v5',
    }:
        trade_amount_feature = config.iteration_v2_trade_amount_feature
        try:
            parse_best_expression_conditions(
                config.iteration_v2_best_expression,
                primary_feature=config.iteration_v2_primary_feature,
                trade_amount_feature=trade_amount_feature,
            )
        except ValueError:
            return _error(
                'invalid_iteration_v2_best_expression',
                f'{config.iteration_v2_mode} iteration_v2_best_expression must contain exactly two parseable conditions',
            )
    if config.run_candidate and config.run_candidates:
        return _error(
            'run_candidate_and_run_candidates_conflict',
            'run_candidate and run_candidates cannot both be true',
        )
    return {'status': 'ok'}


def _csv_path_from_run(result: dict) -> str | None:
    csv_path = result.get('csv_path') or result.get('output_csv')
    if csv_path:
        return csv_path
    metrics = result.get('metrics') or {}
    return metrics.get('csv_path')


def _trade_frame_for_compare(csv_path: str):
    frame = normalize_trade_frame(csv_path)
    aliases = {
        source: target
        for source, target in _TRADE_COLUMN_ALIASES.items()
        if source in frame.columns and target not in frame.columns
    }
    if aliases:
        frame = frame.rename(columns=aliases)
        frame = normalize_trade_frame(frame)
    return frame


def _score_reference_csv(config: ResearchLoopConfig) -> str | None:
    return config.score_reference_csv or None


def _build_reference_evaluation(config: ResearchLoopConfig, candidate_csv: str) -> dict:
    reference_csv = _score_reference_csv(config)
    if not reference_csv:
        return {}
    if not Path(reference_csv).exists():
        return {
            'score_reference_csv': reference_csv,
            'reference_error': {
                'phase': 'score_reference_csv_missing',
                'message': f'score_reference_csv does not exist: {reference_csv}',
                'score_reference_csv': reference_csv,
            },
        }
    reference_comparison = compare_trade_sets(
        _trade_frame_for_compare(reference_csv),
        _trade_frame_for_compare(candidate_csv),
    )
    reference_promotion = evaluate_research_candidate(reference_comparison)
    return {
        'score_reference_csv': reference_csv,
        'reference_comparison': reference_comparison,
        'reference_promotion': reference_promotion,
    }


def _reference_promotion_score(reference_evaluation: dict | None) -> float | None:
    reference_promotion = (reference_evaluation or {}).get('reference_promotion') or {}
    score = reference_promotion.get('score')
    if score is None:
        return None
    try:
        normalized = float(score)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(normalized):
        return None
    return normalized


def _safe_reference_promotion_score(config: ResearchLoopConfig, candidate_csv: str) -> float | None:
    try:
        return _reference_promotion_score(_build_reference_evaluation(config, candidate_csv))
    except Exception:
        return None


def _replay_db_identifier(is_tick: bool) -> str:
    """백테스트 DB 식별자(머신 독립 상대 표기). 절대 경로는 sha 안정성을 깨서 제외한다."""
    raw = DB_STOCK_BACK_TICK if is_tick else DB_STOCK_BACK_MIN
    return f'_database/{Path(raw).name}'


def _replay_strategy_code_sha256(name: str, strategy_type: str) -> str:
    """전략 코드 sha256. 조회 실패 시 빈 문자열(영수증이 replay를 막지 않도록)."""
    if not name:
        return ''
    try:
        loaded = load_strategy_from_db(DB_STRATEGY, name, strategy_type)
    except Exception:
        return ''
    if not isinstance(loaded, dict) or loaded.get('status') != 'ok':
        return ''
    return condition_code_sha256(str(loaded.get('code') or ''))


def _coerce_replay_avg_time(value: object) -> object:
    """avg_time을 int로 정규화(불가하면 문자열 유지) — sha 안정성 확보."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return str(value)


def _build_replay_profile(config: ResearchLoopConfig) -> ReplayProfile:
    """replay 실행 설정(_base_config_dict와 동일 입력)에서 ReplayProfile을 구성한다.

    divid_mode는 research loop가 넘기지 않아 BTConfig 기본값(cli/config.py:34)이
    적용되므로 그 값을 그대로 기록한다. 영수증 전용이며 실행 경로는 불변이다.
    """
    is_tick = bool(config.is_tick)
    return ReplayProfile(
        profile_id='research_loop_baseline_replay',
        is_tick=is_tick,
        universe='stock',
        betting=str(config.betting),
        avg_time=_coerce_replay_avg_time(config.avg_time),
        engine_count=int(config.engine_count),
        fallback_engine_count=0,
        start_date=int(config.start_date),
        end_date=int(config.end_date),
        start_time=int(config.start_time),
        end_time=int(config.end_time),
        divid_mode='종목코드별 분류',
        db_path=_replay_db_identifier(is_tick),
        buy_strategy_name=str(config.base_buy_strategy or ''),
        sell_strategy_name=str(config.sell_strategy or ''),
        buy_condition_sha256=_replay_strategy_code_sha256(config.base_buy_strategy, 'buy'),
        sell_condition_sha256=_replay_strategy_code_sha256(config.sell_strategy, 'sell'),
    )


def _replay_profile_receipt_fields(config: ResearchLoopConfig) -> dict:
    """opt-in replay 프로파일 영수증(additive 필드만). 실패해도 결과를 막지 않는다."""
    if not getattr(config, 'record_replay_profile', False):
        return {}
    try:
        profile = _build_replay_profile(config)
        diff = canonical_execution_diff(profile)
        return {
            'replay_profile': profile.to_receipt(),
            'replay_profile_sha256': profile.profile_sha256(),
            'replay_profile_canonical_id': CANONICAL_REPLAY_PROFILE_V1.profile_id,
            'replay_profile_canonical_diff': diff,
            'replay_profile_matches_canonical': not diff,
        }
    except Exception as exc:
        return {'replay_profile_error': str(exc)}


def _candidate_slippage_fields(config: ResearchLoopConfig, candidate_csv: str | None) -> dict:
    """opt-in 슬리피지 프로파일(advisory, additive 필드만). 실패해도 평가를 막지 않는다."""
    if not getattr(config, 'slippage_profiles_enabled', False):
        return {}
    if not candidate_csv:
        return {}
    try:
        return {'slippage_profiles': slippage_profiles_from_csv(candidate_csv)}
    except Exception as exc:
        return {'slippage_profiles_error': str(exc)}


def _load_condition_code(name: str | None, strategy_type: str) -> str:
    """전략 DB에서 조건식 전문을 로드한다 (실패/부재 시 빈 문자열, 무예외)."""
    if not name:
        return ''
    try:
        loaded = load_strategy_from_db(DB_STRATEGY, name, strategy_type)
    except Exception:
        return ''
    if not isinstance(loaded, dict) or loaded.get('status') != 'ok':
        return ''
    return str(loaded.get('code') or '')


def _context_pack_sources(config: ResearchLoopConfig, analysis_result: dict, baseline_csv: str | None) -> dict:
    """연구 Context Pack 조립용 sources dict (부모 전문은 전략 DB에서 로드)."""
    projection = _condition_discovery_projection(config)
    recommended = analysis_result.get('recommended_candidates') or []
    return {
        'mode': projection.get('process') or 'research-loop',
        'timeframe': 'tick' if config.is_tick else 'min',
        'parent_buy_id': config.base_buy_strategy,
        'parent_buy_code': _load_condition_code(config.base_buy_strategy, 'buy'),
        'parent_sell_id': config.sell_strategy,
        'parent_sell_code': _load_condition_code(config.sell_strategy, 'sell'),
        'official_metrics': {
            'status': analysis_result.get('status'),
            'row_count': analysis_result.get('row_count'),
            'recommended_candidate_count': len(recommended),
        },
        'feature_importance': {
            'source': 'analysis_result',
            'recommended_candidates': recommended,
        },
        'validation_provenance': {
            'process': projection.get('process'),
            'preset': projection.get('preset'),
            'research_only': True,
            'baseline_csv': baseline_csv,
        },
    }


def _apply_research_context_pack(config: ResearchLoopConfig, analysis_result: dict, baseline_csv: str | None) -> dict:
    """opt-in 연구 Context Pack 영수증 주입(additive 키만, 새 dict 반환).

    관측/영수증 전용 배선이다 — 팩 전문(최대 250k 토큰)은 결과·체크포인트
    JSON에 영속하지 않고 영수증(research_context_pack_receipt)만 남긴다.
    현 배선에서 후보 생성은 이 팩을 소비하지 않는다(결정론 생성기는 키를
    무시하고, LLM 후보팩은 별개 경로에서 생산된다).
    소스 부족/조립 실패(예산 초과 포함)는 context_pack_error로만 기록하고
    진행을 막지 않는다. 기본 OFF면 입력을 그대로 돌려준다(byte-동일).
    """
    if not getattr(config, 'context_pack_enabled', False):
        return analysis_result
    try:
        from ai_strategy_loop.controller.context_pack_builder import (
            build_context_pack_receipt,
            build_research_context_pack,
        )
        sources = _context_pack_sources(config, analysis_result, baseline_csv)
        pack = build_research_context_pack(sources)
        receipt = build_context_pack_receipt(pack)
        return {
            **analysis_result,
            'research_context_pack_receipt': receipt,
            'context_pack_id': receipt['context_pack_id'],
            'context_pack_sha256': receipt['context_pack_sha256'],
        }
    except Exception as exc:
        return {**analysis_result, 'context_pack_error': str(exc)}


_LLM_PACK_AUTHORITY = 'research_only_no_export_live_or_final_promotion'

# 축 원장 verdict 어휘 — prompt_receipt downstream_result와 동일 계열을 쓴다.
_AXIS_LEDGER_VERDICT_IMPROVED = 'improved'
_AXIS_LEDGER_VERDICT_REJECTED = 'rejected'


def _axis_ledger_prompt_lines(config: ResearchLoopConfig) -> tuple[list[str], str]:
    """축 원장 사전확률 프롬프트 라인. 미사용/집계 실패 시 (빈 목록, 사유).

    원장 손상(corrupt_ledger_line)은 팩 생산을 막지 않고 사유만 영수증에
    남긴다 — 프롬프트 주입은 advisory 경로라 진행 차단 대상이 아니다.
    """
    path = str(getattr(config, 'axis_ledger_path', '') or '').strip()
    if not path:
        return [], ''
    try:
        from ai_strategy_loop.controller.axis_ledger import AxisLedger, to_prompt_lines
        return to_prompt_lines(AxisLedger(path).aggregate_axis_priors()), ''
    except Exception as exc:
        return [], f'axis_ledger_priors_error:{exc}'


def _llm_pack_lanes(config: ResearchLoopConfig) -> dict | None:
    """팩 생산 레인 배분 — 슬롯 확장 쿼터 우선, 아니면 4슬롯 정책 slots_by_lane."""
    if not _process_research_enabled(config):
        return None
    slots_override = _resolve_candidate_slots_override(config)
    slots_by_lane = (
        slots_override['slots_by_lane']
        if slots_override is not None
        else resolve_hybrid_research_slots().get('slots_by_lane') or {}
    )
    lanes = {
        str(lane): int(count)
        for lane, count in slots_by_lane.items()
        if int(count or 0) > 0
    }
    return lanes or None


def _llm_pack_sources(
    config: ResearchLoopConfig,
    analysis_result: dict,
    baseline_csv: str | None,
) -> dict:
    """LLM 팩 생산용 sources — 영수증용 sources에 pack_producer 필수 입력을 보강.

    pack_producer는 repair 레인에 analysis_card(analysis_id+parent 참조),
    discovery 레인에 coverage_gap(id+bucket keys)/novelty_context를 요구한다.
    analysis_result가 이미 제공하면 그대로 쓰고, 없으면 분석 결과에서
    결정론적으로 조립한다(모듈 내 시계/LLM 호출 없음).
    """
    sources = _context_pack_sources(config, analysis_result, baseline_csv)
    recommended = analysis_result.get('recommended_candidates') or []
    parent_reference = config.base_buy_strategy or config.name
    analysis_card = analysis_result.get('analysis_card')
    if not isinstance(analysis_card, dict) or not analysis_card:
        analysis_card = {
            'analysis_id': f'{config.name}__baseline_analysis',
            'candidate_id': parent_reference,
            'parent_id': parent_reference,
            'root_cause': analysis_result.get('root_cause') or 'baseline_analysis_result',
            'feature_importance': {
                'source': 'analysis_result',
                'recommended_candidates': recommended,
            },
        }
    coverage_gap = analysis_result.get('coverage_gap')
    if not isinstance(coverage_gap, dict) or not coverage_gap:
        bucket_keys = [
            str(item.get('feature'))
            for item in recommended
            if isinstance(item, dict) and item.get('feature')
        ]
        coverage_gap = {
            'coverage_gap_id': f'{config.name}__coverage_gap',
            'coverage_bucket_keys': bucket_keys or ['uncovered_segment_unknown'],
        }
    novelty_context = analysis_result.get('novelty_context')
    if not isinstance(novelty_context, dict) or not novelty_context:
        novelty_context = {
            'source': 'research_loop_baseline_analysis',
            'existing_fingerprints': [],
        }
    return {
        **sources,
        'round_id': config.name,
        'analysis_card': analysis_card,
        'coverage_gap': coverage_gap,
        'novelty_context': novelty_context,
    }


def _apply_llm_candidate_pack(
    config: ResearchLoopConfig,
    analysis_result: dict,
    baseline_csv: str | None,
    provider,
) -> dict:
    """opt-in LLM 후보팩 실생산 배선 (additive 키만, 실패 시 진행 무차단).

    성공 시 analysis_result에 research_candidate_pack(팩 전문)과
    research_candidate_pack_wiring(영수증)을 additive로 주입한다. 생산이
    None/예외/provider 미주입이면 팩을 넣지 않아 기존 결정론 폴백
    (mark_diagnostic_fallback, prompt credit 0)이 자연 발동한다.
    외부에서 이미 주입된 research_candidate_pack은 덮지 않는다(기존 경로 무변경).
    기본 OFF면 입력을 그대로 돌려준다(is-동일).
    """
    if not getattr(config, 'llm_candidate_pack_enabled', False):
        return analysis_result
    if analysis_result.get('research_candidate_pack'):
        return analysis_result
    wiring = {
        'schema_version': 1,
        'enabled': True,
        'status': 'error',
        'failure_reason': '',
        'axis_prompt_line_count': 0,
        'axis_priors_error': '',
        'authority': _LLM_PACK_AUTHORITY,
    }
    if provider is None:
        wiring['status'] = 'skipped'
        wiring['failure_reason'] = 'llm_pack_provider_missing'
        return {**analysis_result, 'research_candidate_pack_wiring': wiring}
    try:
        from ai_strategy_loop.controller.context_pack_builder import (
            produce_research_candidate_pack,
        )
        axis_lines, axis_error = _axis_ledger_prompt_lines(config)
        wiring['axis_prompt_line_count'] = len(axis_lines)
        wiring['axis_priors_error'] = axis_error
        sources = _llm_pack_sources(config, analysis_result, baseline_csv)
        if axis_lines:
            sources['axis_prompt_lines'] = axis_lines
        pack = produce_research_candidate_pack(
            sources,
            provider,
            lanes=_llm_pack_lanes(config),
            axis_prompt_lines=axis_lines or None,
            final_owner_enabled=bool(getattr(config, 'final_owner_selection_enabled', False)),
        )
    except Exception as exc:
        wiring['failure_reason'] = f'llm_pack_production_error:{exc}'
        return {**analysis_result, 'research_candidate_pack_wiring': wiring}
    if not pack:
        wiring['failure_reason'] = 'llm_pack_production_failed'
        return {**analysis_result, 'research_candidate_pack_wiring': wiring}
    wiring['status'] = 'ok'
    return {
        **analysis_result,
        'research_candidate_pack': pack,
        'research_candidate_pack_wiring': wiring,
    }


def _metric_number(mapping, keys: tuple[str, ...]) -> float | None:
    """dict에서 첫 유한 수치를 뽑는다 (bool 제외, 미확보 None)."""
    if not isinstance(mapping, dict):
        return None
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            return float(value)
    return None


def _axis_ledger_slippage_profile(config: ResearchLoopConfig) -> str:
    """프리셋 정책의 슬리피지 게이트 프로파일 (미설정 프리셋은 'unprofiled')."""
    try:
        policy = preset_policy(_condition_discovery_projection(config)['preset'])
        profile = str(getattr(policy, 'slippage_gate_profile', '') or '')
    except Exception:
        profile = ''
    return profile or 'unprofiled'


def _axis_ledger_entry_for_candidate(
    config: ResearchLoopConfig,
    candidate: dict,
    *,
    recorded_at: str,
    baseline_metrics: dict,
) -> tuple[dict | None, list[str]]:
    """후보 1건의 원장 레코드. 필수 필드 미확보 시 (None, 스킵 사유 목록).

    delta는 comparison의 baseline/candidate summary(부모 대비)에서, MDD는
    candidate_result/baseline metrics에서만 취한다 — 미확보 값은 0으로
    채우지 않고 스킵한다(집계 오염 금지).
    """
    if candidate.get('status') != 'ok':
        return None, ['candidate_not_evaluated']
    reasons: list[str] = []
    axis = str(candidate.get('mutation_axis') or '').strip()
    if not axis:
        reasons.append('missing_mutation_axis')
    if not recorded_at:
        reasons.append('missing_recorded_at')
    comparison = candidate.get('comparison') if isinstance(candidate.get('comparison'), dict) else {}
    baseline_summary = comparison.get('baseline_summary') if isinstance(comparison.get('baseline_summary'), dict) else {}
    candidate_summary = comparison.get('candidate_summary') if isinstance(comparison.get('candidate_summary'), dict) else {}
    deltas: dict[str, float] = {}
    for field, keys in (
        ('delta_profit', ('total_profit', 'profit')),
        ('delta_trades', ('trade_count',)),
        ('delta_win_rate', ('win_rate',)),
    ):
        base_value = _metric_number(baseline_summary, keys)
        cand_value = _metric_number(candidate_summary, keys)
        if base_value is None or cand_value is None:
            reasons.append(f'missing_{field}')
        else:
            deltas[field] = cand_value - base_value
    # 실 컨트롤러 run metrics 는 'mdd_pct'(cli/runner.py) — 이 키를 1순위로,
    # 합성/구형 페이로드용 'mdd'/'max_drawdown' 은 폴백으로 유지한다.
    mdd_keys = ('mdd_pct', 'mdd', 'max_drawdown')
    cand_mdd = _metric_number((candidate.get('candidate_result') or {}).get('metrics'), mdd_keys)
    if cand_mdd is None:
        cand_mdd = _metric_number(candidate_summary, mdd_keys)
    base_mdd = _metric_number(baseline_metrics, mdd_keys)
    if base_mdd is None:
        base_mdd = _metric_number(baseline_summary, mdd_keys)
    if cand_mdd is None or base_mdd is None:
        reasons.append('missing_delta_mdd')
    else:
        deltas['delta_mdd'] = cand_mdd - base_mdd
    prompt_receipt = candidate.get('prompt_receipt') if isinstance(candidate.get('prompt_receipt'), dict) else {}
    parent_id = str(
        candidate.get('parent_buy_id')
        or prompt_receipt.get('parent_buy_id')
        or prompt_receipt.get('parent_id')
        or config.base_buy_strategy
        or ''
    ).strip()
    if not parent_id:
        reasons.append('missing_parent_id')
    candidate_id = str(candidate.get('strategy_name') or '').strip()
    if not candidate_id:
        reasons.append('missing_candidate_id')
    if reasons:
        return None, reasons
    promotion = candidate.get('promotion') if isinstance(candidate.get('promotion'), dict) else {}
    entry = {
        # run_id 는 이 라운드의 안정 식별자 — config.name(라운드 이름) 우선,
        # 후보가 명시 round_id 를 갖고 있으면 그것을 쓴다.
        'run_id': str(candidate.get('round_id') or config.name or prompt_receipt.get('round_id') or 'research-loop'),
        'parent_id': parent_id,
        'candidate_id': candidate_id,
        'axis': axis,
        # 구조화된 param 정보가 없으면 축 이름을 그대로 쓴다 —
        # 집계(aggregate_axis_priors)는 axis/delta/verdict만 사용한다.
        'param': str(candidate.get('mutation_param') or axis),
        'from_value': candidate.get('mutation_from'),
        'to_value': candidate.get('mutation_to'),
        'delta_profit': deltas['delta_profit'],
        'delta_mdd': deltas['delta_mdd'],
        'delta_trades': deltas['delta_trades'],
        'delta_win_rate': deltas['delta_win_rate'],
        'slippage_profile': _axis_ledger_slippage_profile(config),
        'window': f'{_candidate_start_date(config)}-{_candidate_end_date(config)}',
        'verdict': (
            _AXIS_LEDGER_VERDICT_IMPROVED
            if promotion.get('passed') is True
            else _AXIS_LEDGER_VERDICT_REJECTED
        ),
        'recorded_at': recorded_at,
    }
    return entry, []


def _record_axis_ledger_entries(
    config: ResearchLoopConfig,
    candidates: list[dict],
    *,
    analysis_result: dict,
    baseline_result: dict | None,
) -> dict | None:
    """라운드 평가 완료 후 축 원장 기록 (opt-in, 무차단, additive 요약 반환).

    recorded_at은 analysis_result의 기존 created_at을 재사용한다(모듈 내
    시계 금지 규약). axis_ledger_path 미설정이면 None(결과 스키마 불변).
    """
    path = str(getattr(config, 'axis_ledger_path', '') or '').strip()
    if not path:
        return None
    recorded_at = str((analysis_result or {}).get('created_at') or '').strip()
    baseline_metrics = (baseline_result or {}).get('metrics') if isinstance(baseline_result, dict) else {}
    if not isinstance(baseline_metrics, dict):
        baseline_metrics = {}
    summary = {
        'schema_version': 1,
        'path': path,
        'recorded_count': 0,
        'skipped': [],
        'error': '',
        'authority': 'research_prompt_prior_only',
    }
    try:
        from ai_strategy_loop.controller.axis_ledger import AxisLedger
        ledger = AxisLedger(path)
    except Exception as exc:
        summary['error'] = f'axis_ledger_unavailable:{exc}'
        return summary
    for candidate in candidates or []:
        if not isinstance(candidate, dict):
            continue
        entry, skip_reasons = _axis_ledger_entry_for_candidate(
            config,
            candidate,
            recorded_at=recorded_at,
            baseline_metrics=baseline_metrics,
        )
        if skip_reasons:
            summary['skipped'].append({
                'candidate_id': str(candidate.get('strategy_name') or ''),
                'reasons': skip_reasons,
            })
            continue
        try:
            ledger.record(entry)
        except ValueError as exc:
            # 원장 검증 실패 — 기록하지 않고 사유만 남긴다(집계 오염 금지).
            summary['skipped'].append({
                'candidate_id': entry['candidate_id'],
                'reasons': str(exc).split('|'),
            })
            continue
        except Exception as exc:
            summary['error'] = f'axis_ledger_write_error:{exc}'
            break
        summary['recorded_count'] += 1
    return summary


_ROUND_MATRIX_SUMMARY_SCHEMA_VERSION = 1
_ROUND_MATRIX_AUTHORITY = 'research_observability_only'


def _round_matrix_artifact_stem(config: ResearchLoopConfig) -> str:
    """아티팩트 파일 이름 stem — 라운드 이름을 파일계 안전 문자로 정규화."""
    name = str(config.name or '').strip() or 'research-round'
    return ''.join(
        char if (char.isalnum() or char in '._-') else '_'
        for char in name
    )


def _round_matrix_output_dir(config: ResearchLoopConfig) -> Path | None:
    """매트릭스 저장 디렉터리 — 명시 dir 우선, 없으면 runtime_output_path 부모."""
    explicit = str(getattr(config, 'round_matrix_output_dir', '') or '').strip()
    if explicit:
        return Path(explicit)
    runtime_path = str(getattr(config, 'runtime_output_path', '') or '').strip()
    if runtime_path:
        return Path(runtime_path).parent
    return None


def _write_round_matrix_artifacts(config: ResearchLoopConfig, result_payload: dict) -> dict | None:
    """라운드 종료 시 교차비교 매트릭스 아티팩트 기록 (opt-in, 무차단, additive).

    round_matrix_enabled=False(기본)면 None — 결과 스키마 불변(byte-동일).
    ON이면 JSON+Markdown을 저장하고 경로+요약(개선 후보 수)만 반환한다 —
    매트릭스 본문은 결과 dict/체크포인트에 영속하지 않는다. 조립/저장 실패는
    진행을 막지 않고 error만 남긴다.
    """
    if not getattr(config, 'round_matrix_enabled', False):
        return None
    summary = {
        'schema_version': _ROUND_MATRIX_SUMMARY_SCHEMA_VERSION,
        'status': 'skipped',
        'json_path': '',
        'md_path': '',
        'candidate_count': 0,
        'improved_over_baseline_count': 0,
        'error': '',
        'authority': _ROUND_MATRIX_AUTHORITY,
    }
    output_dir = _round_matrix_output_dir(config)
    if output_dir is None:
        return {**summary, 'error': 'round_matrix_output_dir_unresolved'}
    try:
        matrix = build_round_comparison_matrix(result_payload)
        markdown = render_matrix_md(matrix)
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = _round_matrix_artifact_stem(config)
        json_path = output_dir / f'{stem}_round_matrix.json'
        md_path = output_dir / f'{stem}_round_matrix.md'
        json_path.write_text(
            json.dumps(matrix, ensure_ascii=False, indent=2, default=str),
            encoding='utf-8',
        )
        md_path.write_text(markdown, encoding='utf-8')
    except Exception as exc:
        return {**summary, 'status': 'error', 'error': f'round_matrix_write_error:{exc}'}
    return {
        **summary,
        'status': 'written',
        'json_path': str(json_path),
        'md_path': str(md_path),
        'candidate_count': int(matrix.get('candidate_count') or 0),
        'improved_over_baseline_count': int(matrix.get('improved_over_baseline_count') or 0),
    }


def _context_pack_result_fields(config: ResearchLoopConfig, result: dict) -> dict:
    """opt-in Context Pack 추적 필드(additive만) — analysis_result에서 승격."""
    if not getattr(config, 'context_pack_enabled', False):
        return {}
    analysis_result = result.get('analysis_result')
    if not isinstance(analysis_result, dict):
        return {}
    fields = {}
    for key in ('context_pack_id', 'context_pack_sha256', 'context_pack_error'):
        value = analysis_result.get(key)
        if value:
            fields[key] = value
    return fields


def _build_result(config: ResearchLoopConfig, result: dict) -> dict:
    receipt_fields = _replay_profile_receipt_fields(config)
    if receipt_fields:
        # additive 병합: 기존 result 키가 항상 우선(스키마 불변 보장).
        result = {**receipt_fields, **result}
    context_pack_fields = _context_pack_result_fields(config, result)
    if context_pack_fields:
        # additive 병합: 기존 result 키가 항상 우선(스키마 불변 보장).
        result = {**context_pack_fields, **result}
    result['report'] = build_research_report(result, strategy_name=config.name)
    return result


def _first_expression(expression_result: dict) -> str | None:
    expressions = expression_result.get('expressions') or []
    return expressions[0] if expressions else None


def _is_strategy_not_found(result: dict) -> bool:
    message = str(result.get('message') or '').lower()
    not_found_markers = (
        'not found',
        'strategy not found',
        '전략 없음',
        '전략이 없습니다',
        '전략이 db에 없습니다',
        '전략을 찾을 수 없습니다',
        '테이블에 없습니다',
    )
    return any(marker in message for marker in not_found_markers)


def _format_candidate_reason(candidate: object) -> str:
    if isinstance(candidate, dict):
        parts = []
        for key in ('source', 'label', 'feature', 'count'):
            value = candidate.get(key)
            if value not in (None, ''):
                parts.append(f'{key}={value}')
        if parts:
            return ' | '.join(parts)
    if candidate not in (None, ''):
        return str(candidate)
    return ''


def _candidate_reason(expression_result: dict) -> str:
    selected_candidates = expression_result.get('selected_candidates') or []
    if selected_candidates:
        reason = _format_candidate_reason(selected_candidates[0])
        if reason:
            return reason
    reason = _format_candidate_reason(expression_result.get('analysis_candidate'))
    if reason:
        return reason
    expression = _first_expression(expression_result)
    if expression:
        return f'analysis_candidate={expression}'
    return 'analysis_candidate=unavailable'


def _candidate_from_spec(spec: dict) -> dict:
    source_candidate = spec.get('source_candidate')
    return {
        'expression': spec.get('expression'),
        'expressions': spec.get('expressions') or [],
        'reason': _format_candidate_reason(source_candidate)
        or f"analysis_candidate={spec.get('expression')}",
        'candidate_count': 1,
        'selected_candidates': [source_candidate] if source_candidate else [],
    }


def _candidate_item_error(spec: dict, phase: str, message: str, **extra) -> dict:
    item = {
        'index': spec.get('index'),
        'strategy_name': spec.get('strategy_name'),
        'expression': spec.get('expression'),
        'status': 'error',
        'phase': phase,
        'message': message,
        'rank': None,
        'rank_score': None,
        'selected_as_best': False,
    }
    for key in _RETENTION_METADATA_KEYS:
        if key in spec:
            item[key] = spec[key]
    for key in _RESEARCH_METADATA_KEYS:
        if key in spec:
            item[key] = spec[key]
    item.update(extra)
    return item


def _prepare_candidate_strategy(
    config: ResearchLoopConfig,
    expressions: list[str],
    strategy_name: str | None = None,
) -> dict:
    candidate_name = strategy_name or config.name
    if not config.base_buy_strategy:
        return _error(
            'candidate_strategy',
            'base_buy_strategy is required when run_candidate is True',
        )
    if candidate_name == config.base_buy_strategy:
        return _error(
            'candidate_name_conflict',
            'name must differ from base_buy_strategy to preserve the base strategy',
        )

    base_result = load_strategy_from_db(DB_STRATEGY, config.base_buy_strategy, 'buy')
    if base_result.get('status') != 'ok':
        return _error(
            'base_strategy_load',
            base_result.get('message', 'failed to load base_buy_strategy'),
            base_strategy_result=base_result,
        )

    candidate_name_result = load_strategy_from_db(DB_STRATEGY, candidate_name, 'buy')
    if candidate_name_result.get('status') == 'ok':
        return _error(
            'candidate_name_conflict',
            f"candidate buy strategy '{candidate_name}' already exists",
            candidate_strategy_result=candidate_name_result,
        )
    if not _is_strategy_not_found(candidate_name_result):
        return _error(
            'candidate_name_lookup',
            candidate_name_result.get('message', 'failed to check candidate buy strategy name'),
            candidate_strategy_result=candidate_name_result,
        )

    strategy_result = generate_buy_filter_strategy(
        candidate_name,
        base_result.get('code', ''),
        expressions,
    )
    if strategy_result.get('status') != 'ok':
        return _error(
            'filter_generation',
            strategy_result.get('message', 'failed to generate filtered buy strategy'),
            strategy_result=strategy_result,
        )

    save_result = save_strategy_to_db(
        DB_STRATEGY,
        candidate_name,
        strategy_result.get('code', ''),
        'buy',
    )
    if save_result.get('status') != 'ok':
        return _error(
            'candidate_strategy_save',
            save_result.get('message', 'failed to save candidate buy strategy'),
            strategy_result=save_result,
        )

    return {
        'status': 'ok',
        'base_strategy_result': base_result,
        'generated_strategy': strategy_result,
        'strategy_result': save_result,
    }


def _candidate_research_metrics(candidate_result: dict, comparison: dict, promotion: dict) -> dict:
    metrics = dict(candidate_result.get('metrics') or {})
    candidate_summary = (comparison.get('candidate_summary') or {}) if isinstance(comparison, dict) else {}
    for source_key, target_key in (
        ('profit', 'profit'),
        ('total_profit', 'profit'),
        ('수익금', 'profit'),
        ('mdd', 'mdd'),
        ('max_drawdown', 'mdd'),
        ('trade_count', 'trade_count'),
    ):
        if target_key not in metrics and source_key in candidate_summary:
            metrics[target_key] = candidate_summary[source_key]
    if 'profit' not in metrics and promotion.get('score') is not None:
        metrics['profit'] = promotion.get('score')
    return metrics


def _build_candidate_research_artifacts(
    config: ResearchLoopConfig,
    spec: dict,
    *,
    candidate_result: dict,
    comparison: dict,
    promotion: dict,
) -> dict:
    if not spec.get('research_contract'):
        return {}
    lane = spec.get('research_lane') or LANE_REPAIR
    metrics = _candidate_research_metrics(candidate_result, comparison, promotion)
    prompt_receipt = dict(spec.get('prompt_receipt') or {})
    candidate_metrics = candidate_result.get('metrics') or {}
    candidate_csv = candidate_result.get('csv_path') or candidate_result.get('output_csv')
    evidence_payload = {
        'csv': bool(candidate_csv),
        'trades': bool(metrics.get('trade_count')),
        'equity': bool(
            candidate_result.get('equity_path')
            or candidate_result.get('equity_curve')
            or candidate_metrics.get('equity_curve')
        ),
        'prompt': bool(prompt_receipt),
        'validation': bool(comparison) and bool(promotion),
    }
    evidence_health = build_evidence_health(
        evidence_payload,
        preset=_condition_discovery_projection(config)['preset'],
    )
    validation_provenance = build_validation_provenance(
        used_for_prompt_or_allocation=True,
        frozen=False,
        fresh_holdout=False,
        evidence_health=evidence_health,
        artifact_ids=[spec.get('strategy_name')],
    )
    source_candidate = spec.get('source_candidate') if isinstance(spec.get('source_candidate'), dict) else {}
    novelty = {}
    if lane == LANE_DISCOVERY:
        novelty = assess_discovery_novelty(
            {
                'candidate_id': spec.get('strategy_name'),
                'structural_fingerprint': source_candidate.get('structural_fingerprint') or spec.get('expression'),
                'coverage_bucket_keys': source_candidate.get('coverage_bucket_keys') or source_candidate.get('discovery_target_coverage') or [],
                'entry_exit_family': source_candidate.get('entry_exit_family') or source_candidate.get('family') or lane,
                'evidence': evidence_payload,
            },
            [],
        )
    downstream_result = 'improved' if promotion.get('passed') is True else 'rejected'
    prompt_receipt.update({
        'downstream_result': downstream_result,
        'official_backtest_result': {
            'status': candidate_result.get('status'),
            'promotion_passed': promotion.get('passed') is True,
            'promotion_score': promotion.get('score'),
            'candidate_csv': candidate_result.get('csv_path'),
            'trade_count': metrics.get('trade_count'),
        },
    })
    analysis_card = build_research_analysis_card(
        analysis_id=f"{spec.get('strategy_name')}__analysis",
        candidate_id=spec.get('strategy_name'),
        lane=lane,
        metrics=metrics,
        parent_id=prompt_receipt.get('parent_id'),
        round_id=prompt_receipt.get('round_id'),
        slot_id=prompt_receipt.get('slot_id'),
        context_pack_id=prompt_receipt.get('context_pack_id') or spec.get('context_pack_id'),
        parent_comparison=comparison,
        root_cause=source_candidate.get('root_cause') or source_candidate.get('root_cause_decomposition') or 'candidate_result_comparison',
        segment_contribution=source_candidate.get('segment_contribution') or source_candidate.get('segment_notes') or {},
        next_recommendation=source_candidate.get('next_recommendation') or 'review official backtest result and mutate one bounded axis',
        evidence_health=evidence_health,
        validation_provenance=validation_provenance,
        prompt_receipt=prompt_receipt,
    )
    return {
        'analysis_card': analysis_card,
        'prompt_receipt': prompt_receipt,
        'validation_provenance': validation_provenance,
        'discovery_novelty': novelty,
    }

def _execute_candidate_spec(
    config: ResearchLoopConfig,
    spec: dict,
    controller,
    baseline_csv: str,
) -> dict:
    strategy_name = spec['strategy_name']
    candidate = _candidate_from_spec(spec)
    candidate_plan = _build_candidate_plan(
        config,
        candidate,
        strategy_name=strategy_name,
        will_save_override=True,
    )
    strict_validation = spec.get('strict_response_validation')
    if isinstance(strict_validation, dict) and strict_validation.get('valid') is False:
        return _candidate_item_error(
            spec,
            'candidate_prompt_validation',
            strict_validation.get('failure_reason') or 'strict repair/discovery response validation failed',
            candidate=candidate,
            candidate_plan=candidate_plan,
            cleanup=_candidate_not_created_cleanup(strategy_name),
        )

    strategy_flow = _prepare_candidate_strategy(
        config,
        spec['expressions'],
        strategy_name=strategy_name,
    )
    if strategy_flow.get('status') != 'ok':
        return _candidate_item_error(
            spec,
            strategy_flow.get('phase', 'candidate_strategy'),
            strategy_flow.get('message', 'failed to prepare candidate strategy'),
            candidate=candidate,
            candidate_plan=candidate_plan,
            cleanup=_candidate_not_created_cleanup(strategy_name),
            strategy_flow=strategy_flow,
        )
    candidate['strategy_result'] = strategy_flow['strategy_result']
    candidate['generated_strategy'] = strategy_flow['generated_strategy']

    candidate_result = controller.run(_candidate_config_dict(config, strategy_name=strategy_name))
    if candidate_result.get('status') not in ('ok', 'success'):
        phase = _candidate_failure_phase(candidate_result)
        cleanup = _cleanup_candidate_strategy(config, phase, strategy_name=strategy_name)
        return _candidate_item_error(
            spec,
            phase,
            candidate_result.get('message', 'candidate run failed'),
            candidate=candidate,
            candidate_plan=candidate_plan,
            cleanup=cleanup,
            candidate_result=candidate_result,
        )

    candidate_csv = _csv_path_from_run(candidate_result)
    if not candidate_csv:
        cleanup = _cleanup_candidate_strategy(
            config,
            'candidate_csv_missing',
            strategy_name=strategy_name,
        )
        return _candidate_item_error(
            spec,
            'candidate_csv_missing',
            'candidate run did not return csv_path',
            candidate=candidate,
            candidate_plan=candidate_plan,
            cleanup=cleanup,
            candidate_result=candidate_result,
        )
    if not Path(candidate_csv).exists():
        cleanup = _cleanup_candidate_strategy(
            config,
            'candidate_csv_missing',
            strategy_name=strategy_name,
        )
        return _candidate_item_error(
            spec,
            'candidate_csv_missing',
            f'candidate csv_path does not exist: {candidate_csv}',
            candidate=candidate,
            candidate_plan=candidate_plan,
            cleanup=cleanup,
            candidate_csv=candidate_csv,
            candidate_result=candidate_result,
        )

    try:
        comparison = compare_trade_sets(
            _trade_frame_for_compare(baseline_csv),
            _trade_frame_for_compare(candidate_csv),
        )
        promotion = evaluate_research_candidate(comparison)
        reference_evaluation = _build_reference_evaluation(config, candidate_csv)
    except Exception as e:
        cleanup = _cleanup_candidate_strategy(config, 'comparison', strategy_name=strategy_name)
        return _candidate_item_error(
            spec,
            'comparison',
            str(e),
            candidate=candidate,
            candidate_plan=candidate_plan,
            cleanup=cleanup,
            candidate_csv=candidate_csv,
            candidate_result=candidate_result,
        )
    research_artifacts = _build_candidate_research_artifacts(
        config,
        spec,
        candidate_result=candidate_result,
        comparison=comparison,
        promotion=promotion,
    )


    return {
        'index': spec.get('index'),
        'strategy_name': strategy_name,
        'expression': spec.get('expression'),
        **{
            key: spec[key]
            for key in _RETENTION_METADATA_KEYS
            if key in spec
        },
        **{
            key: spec[key]
            for key in _RESEARCH_METADATA_KEYS
            if key in spec
        },
        'status': 'ok',
        'phase': 'candidate_evaluated',
        'candidate': candidate,
        'candidate_plan': candidate_plan,
        'candidate_csv': candidate_csv,
        'candidate_result': candidate_result,
        'comparison': comparison,
        'promotion': promotion,
        **reference_evaluation,
        **research_artifacts,
        **_candidate_slippage_fields(config, candidate_csv),
        'rank': None,
        'rank_score': None,
        'selected_as_best': False,
        'cleanup': None,
    }


def _lane_score_candidate_payload(candidate: dict) -> dict:
    analysis_card = candidate.get('analysis_card') or {}
    prompt_receipt = candidate.get('prompt_receipt') or {}
    return {
        'candidate_id': candidate.get('strategy_name'),
        'lane': candidate.get('research_lane') or LANE_REPAIR,
        'metrics': analysis_card.get('metrics') or (candidate.get('candidate_result') or {}).get('metrics') or {},
        'parent_metrics': analysis_card.get('parent_metrics') or {},
        'insight_score': analysis_card.get('insight_score'),
        'prompt_receipt': prompt_receipt,
        'evidence_health': analysis_card.get('evidence_health'),
        'validation_provenance': candidate.get('validation_provenance'),
        'discovery_novelty': candidate.get('discovery_novelty'),
        'downstream_result': prompt_receipt.get('downstream_result'),
    }


def _attach_hybrid_research_scores(
    config: ResearchLoopConfig,
    iteration_plan: dict,
    candidates: list[dict],
) -> dict:
    research_plan = iteration_plan.get('research_loop') or {}
    if not research_plan.get('enabled'):
        return {}
    lane_payloads = {
        LANE_REPAIR: [
            _lane_score_candidate_payload(candidate)
            for candidate in candidates
            if candidate.get('research_lane') == LANE_REPAIR
        ],
        LANE_DISCOVERY: [
            _lane_score_candidate_payload(candidate)
            for candidate in candidates
            if candidate.get('research_lane') == LANE_DISCOVERY
        ],
    }
    preset = _condition_discovery_projection(config)['preset']
    repair_lane = score_research_lane(lane_payloads[LANE_REPAIR], preset=preset)
    discovery_lane = score_research_lane(lane_payloads[LANE_DISCOVERY], preset=preset)
    detail_by_id = {
        detail.get('candidate_id'): detail
        for lane in (repair_lane, discovery_lane)
        for detail in lane.get('candidate_scores', [])
    }
    for candidate in candidates:
        detail = detail_by_id.get(candidate.get('strategy_name'))
        if detail:
            candidate['research_score_detail'] = detail
            candidate['research_lane_score'] = detail.get('candidate_score')
    next_allocation = resolve_hybrid_research_slots({
        'previous_slots_by_lane': (research_plan.get('slots') or {}).get('slots_by_lane'),
        'repair_lane': repair_lane,
        'discovery_lane': discovery_lane,
    })
    return {
        'schema_version': 1,
        'enabled': True,
        'repair_lane': repair_lane,
        'discovery_lane': discovery_lane,
        'next_allocation': next_allocation,
        'authority': 'advisory_research_budget_only',
    }

def run_research_once(config: ResearchLoopConfig, controller) -> dict:
    """Run one analyze-generate-compare research iteration."""
    validation = validate_research_iteration_config(config)
    if validation.get('status') != 'ok':
        return validation

    baseline_result = None
    baseline_csv = config.baseline_csv
    if not baseline_csv:
        baseline_result = controller.run(_base_config_dict(config))
        if baseline_result.get('status') not in ('ok', 'success'):
            return _error('baseline_run', baseline_result.get('message', 'baseline run failed'), run_result=baseline_result)
        baseline_csv = _csv_path_from_run(baseline_result)
        if not baseline_csv:
            return _error('baseline_run', 'baseline run did not return csv_path', run_result=baseline_result)

    analysis_result = analyze_result_csv(
        baseline_csv,
        min_samples=config.min_samples,
        quantiles=config.quantiles,
        alpha=config.alpha,
    )
    if analysis_result.get('status') != 'ok':
        return _error(
            'analysis',
            analysis_result.get('message', 'analysis failed'),
            baseline_csv=baseline_csv,
            analysis_result=analysis_result,
        )
    analysis_result = _apply_research_context_pack(config, analysis_result, baseline_csv)

    expression_result = generate_condition_expressions_from_analysis(
        analysis_result,
        top_n=config.top_n,
    )
    expressions = expression_result.get('expressions') or []
    if expression_result.get('status') != 'ok' or not expressions:
        return _error(
            'no_expressions',
            expression_result.get('message', 'no candidate expressions generated'),
            baseline_csv=baseline_csv,
            analysis_result=analysis_result,
            expression_result=expression_result,
        )

    candidate = {
        'expression': _first_expression(expression_result),
        'expressions': expressions,
        'reason': _candidate_reason(expression_result),
        'candidate_count': expression_result.get('candidate_count', len(expressions)),
        'selected_candidates': expression_result.get('selected_candidates', []),
    }
    candidate_plan = _build_candidate_plan(config, candidate)

    if config.candidate_plan_only:
        return _build_result(config, {
            'status': 'ok',
            'phase': 'candidate_plan',
            'strategy_name': config.name,
            'config': asdict(config),
            'baseline_csv': baseline_csv,
            'candidate_csv': None,
            'baseline_result': baseline_result,
            'analysis_result': analysis_result,
            'expression_result': expression_result,
            'candidate': candidate,
            'candidate_plan': candidate_plan,
            'comparison': None,
            'promotion': None,
        })

    if config.run_candidate and not config.base_buy_strategy:
        return _build_result(config, _error(
            'candidate_strategy',
            'base_buy_strategy is required when run_candidate is True',
            baseline_csv=baseline_csv,
            baseline_result=baseline_result,
            candidate=candidate,
            candidate_plan=candidate_plan,
        ))

    if not config.run_candidate:
        return _build_result(config, {
            'status': 'ok',
            'strategy_name': config.name,
            'config': asdict(config),
            'baseline_csv': baseline_csv,
            'candidate_csv': None,
            'baseline_result': baseline_result,
            'analysis_result': analysis_result,
            'expression_result': expression_result,
            'candidate': candidate,
            'candidate_plan': candidate_plan,
            'comparison': None,
            'promotion': None,
        })

    strategy_flow = _prepare_candidate_strategy(config, expressions)
    if strategy_flow.get('status') != 'ok':
        return _build_result(config, {
            **strategy_flow,
            'baseline_csv': baseline_csv,
            'baseline_result': baseline_result,
            'analysis_result': analysis_result,
            'expression_result': expression_result,
            'candidate': candidate,
            'candidate_plan': candidate_plan,
        })
    candidate['strategy_result'] = strategy_flow['strategy_result']
    candidate['generated_strategy'] = strategy_flow['generated_strategy']

    candidate_result = controller.run(_candidate_config_dict(config))
    if candidate_result.get('status') not in ('ok', 'success'):
        phase = _candidate_failure_phase(candidate_result)
        cleanup = _cleanup_candidate_strategy(config, phase)
        return _build_result(config, _error(
            phase,
            candidate_result.get('message', 'candidate run failed'),
            baseline_csv=baseline_csv,
            candidate=candidate,
            candidate_plan=candidate_plan,
            cleanup=cleanup,
            run_result=candidate_result,
        ))
    candidate_csv = _csv_path_from_run(candidate_result)
    if not candidate_csv:
        cleanup = _cleanup_candidate_strategy(config, 'candidate_csv_missing')
        return _build_result(config, _error(
            'candidate_csv_missing',
            'candidate run did not return csv_path',
            baseline_csv=baseline_csv,
            candidate=candidate,
            candidate_plan=candidate_plan,
            cleanup=cleanup,
            run_result=candidate_result,
        ))
    if not Path(candidate_csv).exists():
        cleanup = _cleanup_candidate_strategy(config, 'candidate_csv_missing')
        return _build_result(config, _error(
            'candidate_csv_missing',
            f'candidate csv_path does not exist: {candidate_csv}',
            baseline_csv=baseline_csv,
            candidate_csv=candidate_csv,
            candidate=candidate,
            candidate_plan=candidate_plan,
            cleanup=cleanup,
            run_result=candidate_result,
        ))

    try:
        comparison = compare_trade_sets(
            _trade_frame_for_compare(baseline_csv),
            _trade_frame_for_compare(candidate_csv),
        )
        promotion = evaluate_research_candidate(comparison)
    except Exception as e:
        cleanup = _cleanup_candidate_strategy(config, 'comparison')
        return _build_result(config, _error(
            'comparison',
            str(e),
            baseline_csv=baseline_csv,
            candidate_csv=candidate_csv,
            candidate=candidate,
            candidate_plan=candidate_plan,
            cleanup=cleanup,
            run_result=candidate_result,
        ))

    return _build_result(config, {
        'status': 'ok',
        'strategy_name': config.name,
        'config': asdict(config),
        'baseline_csv': baseline_csv,
        'candidate_csv': candidate_csv,
        'baseline_result': baseline_result,
        'candidate_result': candidate_result,
        'analysis_result': analysis_result,
        'expression_result': expression_result,
        'candidate': candidate,
        'candidate_plan': candidate_plan,
        'comparison': comparison,
        'promotion': promotion,
        **_candidate_slippage_fields(config, candidate_csv),
    })


def run_research_iteration(config: ResearchLoopConfig, controller, *, provider=None) -> dict:
    """Run one baseline analysis and evaluate multiple candidate expressions.

    provider(additive, 기본 None): LLM 후보팩 생산용 Callable[[list[dict]], str].
    config.llm_candidate_pack_enabled=True이면서 provider가 주입된 경우에만
    팩 생산을 시도한다 — 미주입/실패는 기존 결정론 폴백(credit 0)으로 낙하한다.
    """
    validation = validate_research_iteration_config(config)
    if validation.get('status') != 'ok':
        return validation
    config = replace(config, run_candidate=False, run_candidates=True)
    recorder = ResearchRuntimeRecorder(config.runtime_output_path)
    failure_policy = _initial_failure_policy(config)
    recorder.mark('iteration_started', phase='candidate_iteration')
    checkpoint_result = _flush_research_runtime_checkpoint(
        config,
        recorder,
        phase='candidate_iteration',
        failure_policy=failure_policy,
        candidate_specs=[],
        candidates=[],
        actual_rowset_selection=None,
    )
    if checkpoint_result is not None:
        return checkpoint_result

    baseline_result = None
    baseline_csv = config.baseline_csv
    if not baseline_csv:
        baseline_result = controller.run(_base_config_dict(config))
        if baseline_result.get('status') not in ('ok', 'success'):
            recorder.mark(
                'iteration_aborted',
                phase='baseline_run',
                message=baseline_result.get('message', 'baseline run failed'),
            )
            return _finalize_research_runtime_result(
                config,
                recorder,
                _error(
                    'baseline_run',
                    baseline_result.get('message', 'baseline run failed'),
                    strategy_name=config.name,
                    config=asdict(config),
                    run_result=baseline_result,
                    candidate_specs=[],
                    candidates=[],
                    best_candidate=None,
                    actual_rowset_selection=None,
                    cleanup_summary=_empty_cleanup_summary(),
                ),
                failure_policy,
            )
        baseline_csv = _csv_path_from_run(baseline_result)
        if not baseline_csv:
            recorder.mark(
                'iteration_aborted',
                phase='baseline_run',
                message='baseline run did not return csv_path',
            )
            return _finalize_research_runtime_result(
                config,
                recorder,
                _error(
                    'baseline_run',
                    'baseline run did not return csv_path',
                    strategy_name=config.name,
                    config=asdict(config),
                    run_result=baseline_result,
                    candidate_specs=[],
                    candidates=[],
                    best_candidate=None,
                    actual_rowset_selection=None,
                    cleanup_summary=_empty_cleanup_summary(),
                ),
                failure_policy,
            )

    analysis_result = analyze_result_csv(
        baseline_csv,
        min_samples=config.min_samples,
        quantiles=config.quantiles,
        alpha=config.alpha,
    )
    if analysis_result.get('status') != 'ok':
        recorder.mark(
            'iteration_aborted',
            phase='analysis',
            message=analysis_result.get('message', 'analysis failed'),
        )
        return _finalize_research_runtime_result(
            config,
            recorder,
            _error(
                'analysis',
                analysis_result.get('message', 'analysis failed'),
                strategy_name=config.name,
                config=asdict(config),
                baseline_csv=baseline_csv,
                baseline_result=baseline_result,
                analysis_result=analysis_result,
                candidate_specs=[],
                candidates=[],
                best_candidate=None,
                actual_rowset_selection=None,
                cleanup_summary=_empty_cleanup_summary(),
            ),
            failure_policy,
        )
    analysis_result = _apply_research_context_pack(config, analysis_result, baseline_csv)
    analysis_result = _apply_llm_candidate_pack(config, analysis_result, baseline_csv, provider)
    recorder.mark('analysis_completed', phase='analysis')
    checkpoint_result = _flush_research_runtime_checkpoint(
        config,
        recorder,
        phase='analysis',
        failure_policy=failure_policy,
        baseline_csv=baseline_csv,
        baseline_result=baseline_result,
        analysis_result=analysis_result,
        candidate_specs=[],
        candidates=[],
        actual_rowset_selection=None,
    )
    if checkpoint_result is not None:
        return checkpoint_result

    iteration_plan = _build_iteration_plan(config)
    planned_candidate_count = _iteration_candidate_count(config, iteration_plan)
    research_loop_enabled = bool((iteration_plan.get('research_loop') or {}).get('enabled'))
    candidate_pack_result = {}
    if research_loop_enabled:
        candidate_pack = (
            analysis_result.get('research_candidate_pack')
            or analysis_result.get('llm_candidate_pack')
            or analysis_result.get('candidate_pack')
            or {}
        )
        if candidate_pack:
            candidate_pack_result = expression_result_from_candidate_pack(
                candidate_pack,
                planned_count=planned_candidate_count,
                min_candidates=2,
            )
    if candidate_pack_result.get('status') == 'ok':
        expression_result = candidate_pack_result
    else:
        expression_result = generate_condition_expressions_from_analysis(
            analysis_result,
            top_n=iteration_plan['effective_top_n'],
        )
        if research_loop_enabled:
            wiring_failure_reason = str(
                (analysis_result.get('research_candidate_pack_wiring') or {}).get('failure_reason') or ''
            )
            expression_result = mark_diagnostic_fallback(
                expression_result,
                reason=(
                    candidate_pack_result.get('fallback_reason')
                    or wiring_failure_reason
                    or 'llm_candidate_pack_missing'
                ),
            )
    expressions = expression_result.get('expressions') or []
    if expression_result.get('source') == 'llm_multi_hypothesis_candidate_pack' and len(expressions) >= 2:
        planned_candidate_count = len(expressions)
    if expression_result.get('status') != 'ok' or not expressions:
        recorder.mark(
            'iteration_aborted',
            phase='no_expressions',
            message=expression_result.get('message', 'no candidate expressions generated'),
        )
        return _finalize_research_runtime_result(
            config,
            recorder,
            _error(
                'no_expressions',
                expression_result.get('message', 'no candidate expressions generated'),
                strategy_name=config.name,
                config=asdict(config),
                baseline_csv=baseline_csv,
                baseline_result=baseline_result,
                analysis_result=analysis_result,
                expression_result=expression_result,
                iteration_plan=iteration_plan,
                candidate_specs=[],
                candidates=[],
                best_candidate=None,
                actual_rowset_selection=None,
                cleanup_summary=_empty_cleanup_summary(),
            ),
            failure_policy,
        )
    if len(expressions) < planned_candidate_count:
        message = f"candidate_count={planned_candidate_count} requested but only {len(expressions)} expressions generated"
        recorder.mark(
            'iteration_aborted',
            phase='insufficient_expressions',
            message=message,
        )
        return _finalize_research_runtime_result(
            config,
            recorder,
            _error(
                'insufficient_expressions',
                message,
                strategy_name=config.name,
                config=asdict(config),
                baseline_csv=baseline_csv,
                baseline_result=baseline_result,
                analysis_result=analysis_result,
                expression_result=expression_result,
                iteration_plan=iteration_plan,
                requested_candidate_count=planned_candidate_count,
                expression_count=len(expressions),
                candidate_specs=[],
                candidates=[],
                best_candidate=None,
                actual_rowset_selection=None,
                cleanup_summary=_empty_cleanup_summary(),
            ),
            failure_policy,
        )

    source_candidates = expression_result.get('selected_candidates') or []
    expression_candidates = []
    for index, expression in enumerate(expressions):
        source_candidate = (
            dict(source_candidates[index])
            if index < len(source_candidates) and isinstance(source_candidates[index], dict)
            else {}
        )
        source_candidate['expression'] = expression
        source_candidate['original_index'] = index
        expression_candidates.append(source_candidate)
    iteration_v2 = None
    iteration_v3 = None
    iteration_v4 = None
    iteration_v5 = None
    actual_rowset_selection = None
    candidate_execution_count = planned_candidate_count
    if config.iteration_v2_mode == 'best_feature_mix':
        best_context = {
            'strategy_name': config.iteration_v2_best_candidate,
            'expression': config.iteration_v2_best_expression,
            'source_candidate': candidate_from_expression(
                config.iteration_v2_best_expression,
                feature=config.iteration_v2_primary_feature,
            ),
        }
        iteration_v2 = build_v2_candidate_pool(
            expression_candidates,
            best_context=best_context,
            primary_feature=config.iteration_v2_primary_feature,
            secondary_features=_split_csv_values(config.iteration_v2_secondary_features),
            include_secondary_only=config.iteration_v2_include_secondary_only,
            max_secondary_only=config.iteration_v2_max_secondary_only,
            retention_tolerance=config.iteration_v2_duplicate_retention_tolerance,
        )
        expression_candidates = iteration_v2.get('candidates') or []
        expression_result = {
            **expression_result,
            'selected_candidates': expression_candidates,
            'expressions': [candidate['expression'] for candidate in expression_candidates],
            'candidate_count': len(expression_candidates),
            'iteration_v2': iteration_v2,
        }
        expressions = expression_result['expressions']
    elif config.iteration_v2_mode == 'best_feature_mix_v3':
        best_context = {
            'strategy_name': config.iteration_v2_best_candidate,
            'expression': config.iteration_v2_best_expression,
        }
        if _score_reference_csv(config):
            best_context['reference_adjusted_score'] = _safe_reference_promotion_score(config, baseline_csv)
        iteration_v3 = build_v3_candidate_pool(
            expression_candidates,
            best_context=best_context,
            primary_feature=config.iteration_v2_primary_feature,
            trade_amount_feature=config.iteration_v2_trade_amount_feature,
            secondary_features=_split_csv_values(config.iteration_v2_secondary_features),
            min_estimated_retention=config.min_estimated_retention,
            retention_tolerance=config.iteration_v2_duplicate_retention_tolerance,
        )
        expression_candidates = iteration_v3.get('candidates') or []
        expression_result = {
            **expression_result,
            'selected_candidates': expression_candidates,
            'expressions': [candidate['expression'] for candidate in expression_candidates],
            'candidate_count': len(expression_candidates),
            'iteration_v3': iteration_v3,
        }
        expressions = expression_result['expressions']
    elif config.iteration_v2_mode in {'best_feature_mix_v4', 'best_feature_mix_v5'}:
        best_context = {
            'strategy_name': config.iteration_v2_best_candidate,
            'expression': config.iteration_v2_best_expression,
        }
        if _score_reference_csv(config):
            best_context['reference_adjusted_score'] = _safe_reference_promotion_score(config, baseline_csv)
        iteration_v4 = build_v4_candidate_pool(
            expression_candidates,
            best_context=best_context,
            primary_feature=config.iteration_v2_primary_feature,
            trade_amount_feature=config.iteration_v2_trade_amount_feature,
            secondary_features=_split_csv_values(config.iteration_v2_secondary_features),
            min_estimated_retention=config.min_estimated_retention,
            retention_tolerance=config.iteration_v2_duplicate_retention_tolerance,
        )
        expression_candidates = iteration_v4.get('candidates') or []
        if config.iteration_v2_mode == 'best_feature_mix_v5':
            recovery_result = build_v5_recovery_candidate_pool(
                full_recommended_candidates=analysis_result.get('recommended_candidates') or [],
                existing_v4_result=iteration_v4,
                best_context=best_context,
                primary_feature=config.iteration_v2_primary_feature,
                trade_amount_feature=config.iteration_v2_trade_amount_feature,
                secondary_features=_split_csv_values(config.iteration_v2_secondary_features),
                candidate_count=planned_candidate_count,
            )
            expression_candidates = recovery_result.get('candidates') or []
            iteration_v5 = {
                'status': 'pool_built',
                'mode': 'best_feature_mix_v5',
                'requested_count': planned_candidate_count,
                'v4_candidate_count': len(iteration_v4.get('candidates') or []),
                'initial_v4_candidate_count': recovery_result.get('initial_v4_candidate_count'),
                'recovery': {
                    'recovery_attempted': recovery_result.get('recovery_attempted'),
                    'recovery_reason': recovery_result.get('recovery_reason'),
                    'recovery_family_counts': recovery_result.get('recovery_family_counts') or {},
                    'final_candidate_pool_count': recovery_result.get('final_candidate_pool_count'),
                    'requested_candidate_count': recovery_result.get('requested_candidate_count'),
                    'recovery_needed_count': recovery_result.get('recovery_needed_count'),
                },
            }
        expression_result = {
            **expression_result,
            'selected_candidates': expression_candidates,
            'expressions': [candidate['expression'] for candidate in expression_candidates],
            'candidate_count': len(expression_candidates),
            'iteration_v4': iteration_v4,
        }
        if config.iteration_v2_mode == 'best_feature_mix_v5':
            expression_result['iteration_v5_recovery'] = (iteration_v5 or {}).get('recovery')
        expressions = expression_result['expressions']
    baseline_frame = _trade_frame_for_compare(baseline_csv)
    if config.iteration_v2_mode in {'best_feature_mix_v4', 'best_feature_mix_v5'}:
        annotated_candidates = annotate_candidate_rowset_proxy(
            expression_candidates,
            baseline_frame,
            min_retention=config.min_estimated_retention,
        )
        rowset_selection_count = candidate_execution_count
        if config.iteration_v2_mode == 'best_feature_mix_v5':
            eligible_count = sum(
                1 for candidate in annotated_candidates
                if candidate.get('retention_filter_passed') is True
            )
            if research_loop_enabled:
                rowset_selection_count = planned_candidate_count
            else:
                rowset_selection_count = planned_v5_execution_count(
                    requested_count=planned_candidate_count,
                    eligible_count=eligible_count,
                )
            candidate_execution_count = rowset_selection_count
        selected_candidates, retention_selection = select_rowset_diverse_candidates(
            annotated_candidates,
            candidate_count=rowset_selection_count,
            min_retention=config.min_estimated_retention,
        )
        if config.iteration_v2_mode == 'best_feature_mix_v5':
            iteration_v5 = {
                **(iteration_v5 or {}),
                'status': 'execution_pool_selected',
                'requested_count': planned_candidate_count,
                'eligible_count': eligible_count,
                'execution_count': len(selected_candidates),
                'planned_execution_count': rowset_selection_count,
            }
    else:
        annotated_candidates = annotate_candidate_retention(
            expression_candidates,
            baseline_frame,
            min_retention=config.min_estimated_retention,
        )
        selected_candidates, retention_selection = select_retention_aware_candidates(
            annotated_candidates,
            candidate_count=candidate_execution_count,
            allow_fallback=config.allow_retention_fallback,
            min_retention=config.min_estimated_retention,
        )
    retention_candidates = _retention_candidate_diagnostics(
        annotated_candidates,
        selected_candidates,
    )
    retention_selection = {
        **retention_selection,
        'retention_candidates': retention_candidates,
    }
    expression_result = {
        **expression_result,
        'selected_candidates': selected_candidates,
        'retention_selection': retention_selection,
        'retention_candidates': retention_candidates,
    }
    if retention_selection.get('status') != 'ok':
        phase = retention_selection.get('phase', 'insufficient_retention_candidates')
        message = retention_selection.get('message', 'insufficient retention-aware candidates')
        recorder.mark(
            'iteration_aborted',
            phase=phase,
            message=message,
        )
        return _finalize_research_runtime_result(
            config,
            recorder,
            _error(
                phase,
                message,
                strategy_name=config.name,
                config=asdict(config),
                baseline_csv=baseline_csv,
                baseline_result=baseline_result,
                analysis_result=analysis_result,
                expression_result=expression_result,
                iteration_plan=iteration_plan,
                **_iteration_generation_metadata(iteration_v2, iteration_v3, iteration_v4, iteration_v5),
                retention_selection=retention_selection,
                retention_candidates=retention_candidates,
                candidate_specs=[],
                candidates=[],
                best_candidate=None,
                actual_rowset_selection=None,
                cleanup_summary=_empty_cleanup_summary(),
            ),
            failure_policy,
        )
    required_selected_count = planned_candidate_count if config.iteration_v2_mode == 'best_feature_mix_v5' else candidate_execution_count
    if len(selected_candidates) < required_selected_count:
        message = (
            f"candidate_count={required_selected_count} requested but only "
            f"{len(selected_candidates)} candidates selected after retention filtering"
        )
        recorder.mark(
            'iteration_aborted',
            phase='insufficient_retention_candidates',
            message=message,
        )
        return _finalize_research_runtime_result(
            config,
            recorder,
            _error(
                'insufficient_retention_candidates',
                message,
                strategy_name=config.name,
                config=asdict(config),
                baseline_csv=baseline_csv,
                baseline_result=baseline_result,
                analysis_result=analysis_result,
                expression_result=expression_result,
                iteration_plan=iteration_plan,
                **_iteration_generation_metadata(iteration_v2, iteration_v3, iteration_v4, iteration_v5),
                retention_selection=retention_selection,
                retention_candidates=retention_candidates,
                requested_candidate_count=required_selected_count,
                selected_candidate_count=len(selected_candidates),
                **_v5_candidate_pool_metadata(iteration_v5, retention_selection),
                candidate_specs=[],
                candidates=[],
                best_candidate=None,
                actual_rowset_selection=None,
                cleanup_summary=_empty_cleanup_summary(),
            ),
            failure_policy,
        )
    expression_result = {
        **expression_result,
        'expressions': [candidate['expression'] for candidate in selected_candidates],
        'selected_candidates': selected_candidates,
    }

    specs = _build_candidate_specs(
        config,
        expression_result,
        candidate_count=candidate_execution_count,
    )
    recorder.mark(
        'candidate_pool_selected',
        phase='candidate_pool',
        detail={
            'candidate_spec_count': len(specs),
            'requested_count': planned_candidate_count,
            'execution_count': candidate_execution_count,
        },
    )
    checkpoint_result = _flush_research_runtime_checkpoint(
        config,
        recorder,
        phase='candidate_pool',
        failure_policy=failure_policy,
        baseline_csv=baseline_csv,
        baseline_result=baseline_result,
        analysis_result=analysis_result,
        expression_result=expression_result,
        iteration_plan=iteration_plan,
        **_iteration_generation_metadata(iteration_v2, iteration_v3, iteration_v4, iteration_v5),
        retention_selection=retention_selection,
        retention_candidates=retention_candidates,
        candidate_specs=specs,
        candidates=[],
        actual_rowset_selection=None,
    )
    if checkpoint_result is not None:
        return checkpoint_result
    candidates = []
    for spec in specs:
        recorder.mark(
            'candidate_started',
            phase='candidate_execution',
            candidate_index=spec.get('index'),
            strategy_name=spec.get('strategy_name'),
        )
        checkpoint_result = _flush_research_runtime_checkpoint(
            config,
            recorder,
            phase='candidate_execution',
            failure_policy=failure_policy,
            baseline_csv=baseline_csv,
            baseline_result=baseline_result,
            analysis_result=analysis_result,
            expression_result=expression_result,
            iteration_plan=iteration_plan,
            **_iteration_generation_metadata(iteration_v2, iteration_v3, iteration_v4, iteration_v5),
            retention_selection=retention_selection,
            retention_candidates=retention_candidates,
            candidate_specs=specs,
            candidates=candidates,
            active_candidate=spec,
            actual_rowset_selection=None,
        )
        if checkpoint_result is not None:
            return checkpoint_result
        candidate = _execute_candidate_spec(config, spec, controller, baseline_csv)
        candidates.append(candidate)
        if candidate.get('status') == 'ok':
            failure_policy['consecutive_candidate_failures'] = 0
            recorder.mark(
                'candidate_succeeded',
                phase=candidate.get('phase'),
                candidate_index=candidate.get('index'),
                strategy_name=candidate.get('strategy_name'),
            )
            checkpoint_result = _flush_research_runtime_checkpoint(
                config,
                recorder,
                phase=candidate.get('phase') or 'candidate_execution',
                failure_policy=failure_policy,
                baseline_csv=baseline_csv,
                baseline_result=baseline_result,
                analysis_result=analysis_result,
                expression_result=expression_result,
                iteration_plan=iteration_plan,
                **_iteration_generation_metadata(iteration_v2, iteration_v3, iteration_v4, iteration_v5),
                retention_selection=retention_selection,
                retention_candidates=retention_candidates,
                candidate_specs=specs,
                candidates=candidates,
                actual_rowset_selection=None,
            )
            if checkpoint_result is not None:
                return checkpoint_result
        else:
            failure_policy['consecutive_candidate_failures'] += 1
            failure_policy['total_candidate_failures'] += 1
            candidate['consecutive_failure_count'] = failure_policy['consecutive_candidate_failures']
            recorder.mark(
                'candidate_failed',
                phase=candidate.get('phase'),
                message=candidate.get('message'),
                candidate_index=candidate.get('index'),
                strategy_name=candidate.get('strategy_name'),
                consecutive_failure_count=failure_policy['consecutive_candidate_failures'],
            )
            checkpoint_result = _flush_research_runtime_checkpoint(
                config,
                recorder,
                phase=candidate.get('phase') or 'candidate_execution',
                failure_policy=failure_policy,
                baseline_csv=baseline_csv,
                baseline_result=baseline_result,
                analysis_result=analysis_result,
                expression_result=expression_result,
                iteration_plan=iteration_plan,
                **_iteration_generation_metadata(iteration_v2, iteration_v3, iteration_v4, iteration_v5),
                retention_selection=retention_selection,
                retention_candidates=retention_candidates,
                candidate_specs=specs,
                candidates=candidates,
                actual_rowset_selection=None,
            )
            if checkpoint_result is not None:
                return checkpoint_result
            if failure_policy['consecutive_candidate_failures'] == max(
                config.max_consecutive_candidate_failures - 1,
                1,
            ):
                recorder.mark(
                    'candidate_failure_warning',
                    phase='candidate_iteration',
                    message='consecutive candidate failures are approaching the abort threshold',
                    consecutive_failure_count=failure_policy['consecutive_candidate_failures'],
                )
            if (
                config.max_consecutive_candidate_failures > 0
                and failure_policy['consecutive_candidate_failures'] >= config.max_consecutive_candidate_failures
            ):
                failure_policy['aborted'] = True
                failure_policy['abort_reason'] = 'max_consecutive_candidate_failures'
                recorder.mark(
                    'iteration_aborted',
                    phase='candidate_iteration_runtime_failure',
                    message='maximum consecutive candidate failures reached',
                    consecutive_failure_count=failure_policy['consecutive_candidate_failures'],
                )
                break
    if failure_policy['aborted']:
        cleanup_candidates, cleanup_summary = _apply_iteration_cleanup(config, candidates)
        result_payload = {
            'status': 'error',
            'phase': 'candidate_iteration_runtime_failure',
            'message': 'maximum consecutive candidate failures reached',
            'strategy_name': config.name,
            'config': asdict(config),
            'baseline_csv': baseline_csv,
            'baseline_result': baseline_result,
            'analysis_result': analysis_result,
            'expression_result': expression_result,
            'iteration_plan': iteration_plan,
            **_iteration_generation_metadata(iteration_v2, iteration_v3, iteration_v4, iteration_v5),
            'retention_selection': retention_selection,
            'retention_candidates': retention_candidates,
            'candidate_specs': specs,
            'candidates': cleanup_candidates,
            'best_candidate': None,
            'actual_rowset_selection': {
                'status': 'not_run',
                'reason': 'candidate_iteration_runtime_failure',
                'requested_count': planned_candidate_count,
                'successful_candidate_count': 0,
            },
            'cleanup_summary': cleanup_summary,
            'failure_policy': failure_policy,
        }
        return _finalize_research_runtime_result(
            config,
            recorder,
            result_payload,
            failure_policy,
        )
    hybrid_research_result = _attach_hybrid_research_scores(config, iteration_plan, candidates)
    ranked_candidates, best_candidate = _rank_candidate_results(candidates, config)
    if config.iteration_v2_mode == 'best_feature_mix_v5':
        successful_candidates = [
            candidate
            for candidate in ranked_candidates
            if candidate.get('status') == 'ok'
        ]
        if len(successful_candidates) < planned_candidate_count:
            actual_rowset_selection = {
                'status': 'not_run',
                'reason': 'insufficient_successful_candidates',
                'requested_count': planned_candidate_count,
                'successful_candidate_count': len(successful_candidates),
            }
            iteration_v5 = {
                **(iteration_v5 or {}),
                'status': 'not_run',
                'requested_count': planned_candidate_count,
                'execution_count': len(specs),
                'actual_selected_count': 0,
                'row_set_identity_status': 'not_evaluated',
            }
        else:
            recorder.mark(
                'actual_rowset_selection_started',
                phase='actual_rowset_selection',
            )
            _, actual_rowset_selection = select_actual_rowset_representatives(
                ranked_candidates,
                runtime_root=Path.cwd(),
                requested_count=planned_candidate_count,
            )
            ranked_candidates, best_candidate = apply_actual_rowset_selection(
                ranked_candidates,
                actual_rowset_selection,
            )
            iteration_v5 = {
                **(iteration_v5 or {}),
                'status': actual_rowset_selection.get('status'),
                'requested_count': planned_candidate_count,
                'execution_count': len(specs),
                'actual_selected_count': actual_rowset_selection.get('selected_count'),
                'row_set_identity_status': actual_rowset_selection.get('row_set_identity_status'),
            }
            recorder.mark(
                'actual_rowset_selection_completed',
                phase='actual_rowset_selection',
                detail={
                    'status': actual_rowset_selection.get('status'),
                    'selected_count': actual_rowset_selection.get('selected_count'),
                    'row_set_identity_status': actual_rowset_selection.get('row_set_identity_status'),
                },
            )
    ranked_candidates, cleanup_summary = _apply_iteration_cleanup(config, ranked_candidates)
    best_candidate = next(
        (
            candidate
            for candidate in ranked_candidates
            if candidate.get('selected_as_best') is True
        ),
        None,
    )

    has_best_candidate = best_candidate is not None
    axis_ledger_recording = _record_axis_ledger_entries(
        config,
        ranked_candidates,
        analysis_result=analysis_result,
        baseline_result=baseline_result,
    )
    result_payload = {
        'status': 'ok' if has_best_candidate else 'error',
        'phase': 'candidates_evaluated' if has_best_candidate else 'candidate_iteration',
        'message': None if has_best_candidate else 'no candidate evaluated successfully',
        'strategy_name': config.name,
        'config': asdict(config),
        'baseline_csv': baseline_csv,
        'baseline_result': baseline_result,
        'analysis_result': analysis_result,
        'expression_result': expression_result,
        'iteration_plan': iteration_plan,
        **_iteration_generation_metadata(iteration_v2, iteration_v3, iteration_v4, iteration_v5),
        'hybrid_research': hybrid_research_result,
        'retention_selection': retention_selection,
        'retention_candidates': retention_candidates,
        'candidate_specs': specs,
        'candidates': ranked_candidates,
        'best_candidate': best_candidate,
        'actual_rowset_selection': actual_rowset_selection,
        **_v5_candidate_pool_metadata(iteration_v5, retention_selection),
        'cleanup_summary': cleanup_summary,
        'failure_policy': failure_policy,
        # opt-in 축 원장 기록 요약 — axis_ledger_path 미설정이면 키 자체가 없다.
        **({'axis_ledger_recording': axis_ledger_recording} if axis_ledger_recording is not None else {}),
    }
    # opt-in 라운드 교차비교 매트릭스(T3.4) — round_matrix_enabled 미설정이면
    # 키 자체가 없다. 매트릭스 본문은 아티팩트(JSON+md)로만 저장하고 결과에는
    # 경로+개선 후보 수 요약만 additive로 남긴다.
    round_matrix_summary = _write_round_matrix_artifacts(config, result_payload)
    if round_matrix_summary is not None:
        result_payload = {**result_payload, 'round_matrix': round_matrix_summary}
    recorder.mark(
        'iteration_completed' if has_best_candidate else 'iteration_aborted',
        phase=result_payload['phase'],
        message=result_payload['message'],
    )
    return _finalize_research_runtime_result(
        config,
        recorder,
        result_payload,
        failure_policy,
    )
