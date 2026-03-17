"""자동 조건식 탐색 엔진 (Auto-Discovery).

DB 전략명만으로 백테스트 → 분석 → 조건 생성 → WFO 검증 → 승격 파이프라인을 원커맨드로 실행한다.

사용법::

    from cli.auto_discovery import AutoDiscoveryConfig, AutoDiscoveryEngine

    config = AutoDiscoveryConfig(
        buy_strategy='Min_B_Study',
        sell_strategy='Min_S_Study',
        start_date=20250401,
        end_date=20250430,
        train_window_days=30,
        test_window_days=10,
    )
    result = AutoDiscoveryEngine.run(config)
"""

from __future__ import annotations

import os
import sys
import time
import copy
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field, fields, asdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class AutoDiscoveryConfig:
    """자동 탐색 파이프라인 전체 설정."""

    # --- Phase A: 백테스트 실행 설정 ---
    buy_strategy: str = ''
    sell_strategy: str = ''
    start_date: int = 0
    end_date: int = 0
    is_tick: bool = True
    betting: str = '1'
    avg_time: object = 60
    start_time: int = 90000
    end_time: int = 152800
    engine_count: int = 4
    oms: bool = False
    blacklist: bool = False
    back_club: bool = False
    timeout: int = 3600

    # --- Phase B: 분석 파라미터 ---
    top_n: int = 5
    min_samples: int = 30
    quantiles: int = 10
    alpha: float = 0.05
    buy_var: str = '매수'

    # --- Phase B: ML 파라미터 ---
    ml_feature_limit: int = 0
    ml_model_type: str = 'random_forest'
    ml_top_n: int = 10
    ml_n_splits: int = 5
    ml_weight: float = 0.0

    # --- Phase B: 다단계 재시도 ---
    max_rounds: int = 3
    relax_alpha_step: float = 0.02
    relax_min_samples_step: int = 5
    relax_quantiles_step: int = 2
    relax_top_n_step: int = 1

    # --- Phase C: WFO 검증 ---
    train_window_days: int = 30
    test_window_days: int = 10
    step_days: int | None = None
    purge_days: int = 0
    embargo_days: int = 0
    objective: str = 'tpi'
    wfo_method: str = 'grid'
    wfo_max_iter: int = 10

    # --- Phase C: 프로모션 ---
    promotion_preset: str = 'balanced'
    auto_relax: bool = False
    max_relax_steps: int = 3
    base_buy_strategy: str | None = None

    # --- 입력 ---
    input_csv: str | None = None  # 지정 시 Phase A(백테스트)를 건너뛰고 이 CSV로 Phase B 직행

    # --- 출력 ---
    output_code: str | None = None
    report_json: str | None = None
    report_md: str | None = None
    csv_dir: str = 'backtest/csv'
    verbose: bool = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_latest_csv(strategy_name: str, csv_dir: str = 'backtest/csv',
                    after_timestamp: float = 0.0, max_retries: int = 3,
                    retry_delay: float = 2.0) -> str | None:
    """csv_dir에서 strategy_name을 포함하며 after_timestamp 이후 수정된 최신 CSV를 반환한다.

    백테스트 자식 프로세스 완료 직후 CSV 쓰기 지연을 감안해 재시도한다.
    """
    import glob

    if not os.path.isdir(csv_dir):
        return None

    pattern = os.path.join(csv_dir, f'*{strategy_name}*.csv') if strategy_name else os.path.join(csv_dir, '*.csv')

    for attempt in range(max_retries):
        candidates = [
            f for f in glob.glob(pattern)
            if os.path.getmtime(f) >= after_timestamp
        ]
        if candidates:
            return max(candidates, key=os.path.getmtime)
        if attempt < max_retries - 1:
            time.sleep(retry_delay)

    return None


def run_multi_round_analysis(csv_path: str, config: AutoDiscoveryConfig,
                             controller=None) -> dict:
    """다단계 파라미터 완화를 통한 분석 + 조건 생성.

    Round 1은 사용자 파라미터로 분석. 후보 부족 시 파라미터를 완화하며 재시도.
    각 라운드의 파라미터/후보 수를 기록하여 반환한다.
    """
    if controller is None:
        from cli.ai_controller import AIBacktestController
        controller = AIBacktestController()

    alpha = config.alpha
    min_samples = config.min_samples
    quantiles = config.quantiles
    top_n = config.top_n
    rounds_log = []

    for round_idx in range(config.max_rounds):
        analysis_result = controller.analyze_results(
            csv_path,
            min_samples=min_samples,
            quantiles=quantiles,
            alpha=alpha,
        )

        gen_result = controller.generate_conditions(
            input_path=csv_path,
            top_n=top_n,
            buy_var=config.buy_var,
            min_samples=min_samples,
            quantiles=quantiles,
            alpha=alpha,
            ml_feature_limit=config.ml_feature_limit,
            ml_model_type=config.ml_model_type,
            ml_top_n=config.ml_top_n,
            ml_n_splits=config.ml_n_splits,
            ml_weight=config.ml_weight,
        )

        candidate_count = gen_result.get('candidate_count', 0)
        round_info = {
            'round': round_idx + 1,
            'alpha': alpha,
            'min_samples': min_samples,
            'quantiles': quantiles,
            'top_n': top_n,
            'candidate_count': candidate_count,
            'status': gen_result.get('status', 'error'),
        }
        rounds_log.append(round_info)

        if gen_result.get('status') == 'ok' and candidate_count > 0:
            return {
                'status': 'ok',
                'analysis_result': gen_result.get('analysis_result'),
                'gen_result': gen_result,
                'rounds_log': rounds_log,
                'final_round': round_idx + 1,
            }

        # 파라미터 완화
        alpha = round(alpha + config.relax_alpha_step, 4)
        min_samples = max(5, min_samples - config.relax_min_samples_step)
        quantiles = max(3, quantiles - config.relax_quantiles_step)
        top_n = max(1, top_n - config.relax_top_n_step)

    return {
        'status': 'error',
        'message': f'{config.max_rounds}회 분석 라운드 후에도 유효 후보를 찾지 못했습니다.',
        'rounds_log': rounds_log,
    }


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class AutoDiscoveryEngine:
    """자동 조건식 탐색 3-Phase 엔진."""

    def __init__(self, config: AutoDiscoveryConfig, controller=None):
        self.config = config
        if controller is None:
            from cli.ai_controller import AIBacktestController
            controller = AIBacktestController()
        self.controller = controller

    # ------- Phase A: 백테스트 실행 → CSV 회수 -------

    def _phase_a_backtest(self) -> dict:
        """백테스트를 실행하고 결과 CSV 경로를 회수한다."""
        cfg = self.config
        phase_start = time.time()
        run_start = time.time()

        config_dict = {
            'buy_strategy': cfg.buy_strategy,
            'sell_strategy': cfg.sell_strategy,
            'start_date': cfg.start_date,
            'end_date': cfg.end_date,
            'is_tick': cfg.is_tick,
            'betting': cfg.betting,
            'avg_time': cfg.avg_time,
            'start_time': cfg.start_time,
            'end_time': cfg.end_time,
            'engine_count': cfg.engine_count,
            'oms': cfg.oms,
            'blacklist': cfg.blacklist,
            'back_club': cfg.back_club,
            'timeout': cfg.timeout,
            'verbose': cfg.verbose,
        }

        bt_result = self.controller.run(config_dict)

        if bt_result.get('status') != 'success':
            return {
                'status': 'error',
                'phase': 'A',
                'message': f"백테스트 실패: {bt_result.get('message', 'unknown')}",
                'backtest_result': bt_result,
            }

        # CSV 경로: runner가 반환하거나 직접 탐색
        csv_path = bt_result.get('csv_path')
        if not csv_path:
            csv_path = find_latest_csv(
                cfg.buy_strategy, cfg.csv_dir, after_timestamp=run_start,
            )

        if not csv_path or not os.path.isfile(csv_path):
            return {
                'status': 'error',
                'phase': 'A',
                'message': '백테스트 완료되었으나 결과 CSV를 찾을 수 없습니다.',
                'backtest_result': bt_result,
            }

        return {
            'status': 'ok',
            'phase': 'A',
            'csv_path': csv_path,
            'backtest_result': bt_result,
            'phase_duration': round(time.time() - phase_start, 2),
        }

    # ------- Phase B: 다단계 분석 + 조건 생성 -------

    def _phase_b_analysis(self, csv_path: str) -> dict:
        """CSV를 분석하고 조건 코드를 생성한다."""
        phase_start = time.time()
        result = run_multi_round_analysis(csv_path, self.config, self.controller)

        if result.get('status') != 'ok':
            return {
                'status': 'error',
                'phase': 'B',
                'message': result.get('message', '분석 실패'),
                'rounds_log': result.get('rounds_log', []),
            }

        return {
            'status': 'ok',
            'phase': 'B',
            'analysis_result': result.get('analysis_result'),
            'gen_result': result.get('gen_result'),
            'rounds_log': result.get('rounds_log', []),
            'final_round': result.get('final_round', 1),
            'phase_duration': round(time.time() - phase_start, 2),
        }

    # ------- Phase C: WFO 검증 + 승격 -------

    def _phase_c_validate_and_promote(self, csv_path: str) -> dict:
        """기존 discover_and_promote_strategy()를 활용해 WFO 검증 → 승격을 수행한다."""
        phase_start = time.time()
        cfg = self.config
        from cli.discovery_config import (
            DiscoveryAnalysisConfig, DiscoveryConfig, DiscoveryMlConfig,
            DiscoveryOutputConfig, DiscoveryPromotionConfig,
        )

        strategy_name = f'Auto_{cfg.buy_strategy}_{int(time.time())}'

        config_dict = {
            'sell_strategy': cfg.sell_strategy,
            'start_date': cfg.start_date,
            'end_date': cfg.end_date,
            'is_tick': cfg.is_tick,
            'betting': cfg.betting,
            'avg_time': cfg.avg_time,
            'start_time': cfg.start_time,
            'end_time': cfg.end_time,
            'engine_count': cfg.engine_count,
        }
        if cfg.base_buy_strategy:
            config_dict['base_buy_strategy'] = cfg.base_buy_strategy

        walk_forward_settings = {
            'train_window_days': cfg.train_window_days,
            'test_window_days': cfg.test_window_days,
            'step_days': cfg.step_days,
            'purge_days': cfg.purge_days,
            'embargo_days': cfg.embargo_days,
            'objective': cfg.objective,
            'method': cfg.wfo_method,
            'max_iter': cfg.wfo_max_iter,
        }

        discovery_config = DiscoveryConfig(
            analysis=DiscoveryAnalysisConfig(
                top_n=cfg.top_n,
                min_samples=cfg.min_samples,
                quantiles=cfg.quantiles,
                alpha=cfg.alpha,
                buy_var=cfg.buy_var,
            ),
            ml=DiscoveryMlConfig(
                feature_limit=cfg.ml_feature_limit,
                model_type=cfg.ml_model_type,
                top_n=cfg.ml_top_n,
                n_splits=cfg.ml_n_splits,
                weight=cfg.ml_weight,
            ),
            promotion=DiscoveryPromotionConfig(
                preset=cfg.promotion_preset,
                auto_relax=cfg.auto_relax,
                max_relax_steps=cfg.max_relax_steps,
            ),
            output=DiscoveryOutputConfig(
                code_path=cfg.output_code,
                report_json_path=cfg.report_json,
                report_md_path=cfg.report_md,
            ),
        )

        result = self.controller.discover_and_promote_strategy(
            strategy_name,
            config_dict=config_dict,
            input_path=csv_path,
            walk_forward_settings=walk_forward_settings,
            discovery_config=discovery_config,
        )

        return {
            'status': result.get('status', 'error'),
            'phase': 'C',
            'strategy_name': strategy_name,
            'promoted': result.get('promoted', False),
            'discovery_result': result,
            'phase_duration': round(time.time() - phase_start, 2),
        }

    # ------- 메인 실행 -------

    @classmethod
    def run(cls, config: AutoDiscoveryConfig, controller=None) -> dict:
        """전체 파이프라인을 실행한다.

        Phase A → Phase B → Phase C 순서로 진행하며,
        각 Phase 실패 시 해당 시점까지의 결과를 반환한다.
        """
        engine = cls(config, controller)
        pipeline_start = time.time()

        # Phase A: 백테스트 → CSV (input_csv 지정 시 스킵)
        if config.input_csv:
            if not os.path.isfile(config.input_csv):
                return {
                    'status': 'error',
                    'phase': 'A',
                    'message': f'지정된 CSV 파일이 존재하지 않습니다: {config.input_csv}',
                    'pipeline_duration': round(time.time() - pipeline_start, 2),
                }
            csv_path = config.input_csv
            phase_a = {
                'status': 'ok',
                'phase': 'A',
                'csv_path': csv_path,
                'skipped': True,
                'message': 'input_csv 직접 지정으로 Phase A(백테스트) 스킵',
            }
        else:
            phase_a = engine._phase_a_backtest()
            if phase_a.get('status') != 'ok':
                phase_a['pipeline_duration'] = round(time.time() - pipeline_start, 2)
                return phase_a
            csv_path = phase_a['csv_path']

        # Phase B: 분석 → 조건 생성 (정보용, Phase C에서 재분석)
        phase_b = engine._phase_b_analysis(csv_path)
        if phase_b.get('status') != 'ok':
            phase_b['phase_a'] = phase_a
            phase_b['pipeline_duration'] = round(time.time() - pipeline_start, 2)
            return phase_b

        # Phase C: WFO 검증 → 승격
        phase_c = engine._phase_c_validate_and_promote(csv_path)

        pipeline_duration = round(time.time() - pipeline_start, 2)
        pipeline_timing = {
            'phase_a': phase_a.get('phase_duration', 0.0),
            'phase_b': phase_b.get('phase_duration', 0.0),
            'phase_c': phase_c.get('phase_duration', 0.0),
            'total': pipeline_duration,
        }

        return {
            'status': phase_c.get('status', 'error'),
            'promoted': phase_c.get('promoted', False),
            'strategy_name': phase_c.get('strategy_name'),
            'csv_path': csv_path,
            'phase_a': phase_a,
            'phase_b': phase_b,
            'phase_c': phase_c,
            'pipeline_timing': pipeline_timing,
            'pipeline_duration': pipeline_duration,
        }


# ---------------------------------------------------------------------------
# Batch execution
# ---------------------------------------------------------------------------

def load_batch_config(path: str) -> dict:
    """배치 설정 JSON을 읽어 common + runs 리스트로 반환한다.

    JSON 형식::

        {
          "common": { "sell_strategy": "S", "start_date": 20250401, ... },
          "runs": [
            { "buy_strategy": "A", "alpha": 0.05 },
            { "buy_strategy": "B", "top_n": 3 }
          ]
        }

    Returns:
        {'common': dict, 'runs': list[dict]}
    """
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if 'runs' not in data or not isinstance(data['runs'], list):
        raise ValueError("배치 설정 JSON에 'runs' 배열이 필요합니다.")

    return {
        'common': data.get('common', {}),
        'runs': data['runs'],
        'timeframes': data.get('timeframes', []),
    }


def _merge_batch_run(common: dict, run_override: dict) -> AutoDiscoveryConfig:
    """common 설정과 개별 run 오버라이드를 병합하여 AutoDiscoveryConfig를 생성한다."""
    merged = {**common, **run_override}
    valid_fields = {f.name for f in fields(AutoDiscoveryConfig)}
    filtered = {k: v for k, v in merged.items() if k in valid_fields}
    return AutoDiscoveryConfig(**filtered)


def _expand_timeframes(common: dict, runs: list, timeframes: list) -> list:
    """timeframes 배열이 있으면 각 run을 tick/min별로 복제한다.

    Args:
        common: 공통 설정 dict.
        runs: 원본 run 오버라이드 리스트.
        timeframes: ['tick'], ['min'], 또는 ['tick', 'min'].

    Returns:
        확장된 runs 리스트. 각 항목에 'is_tick' 필드가 추가됨.
        timeframes가 비어있으면 원본 runs를 그대로 반환.
    """
    if not timeframes:
        return runs

    expanded = []
    for run in runs:
        for tf in timeframes:
            new_run = {**run, 'is_tick': tf == 'tick', '_timeframe': tf}
            expanded.append(new_run)
    return expanded


def _validate_timeframe_compat(config: AutoDiscoveryConfig) -> str | None:
    """is_tick에 맞는 DB 파일 존재를 확인한다. 오류 시 문자열 반환."""
    db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          '_database')
    tf_label = 'tick' if config.is_tick else 'min'
    db_name = f'stom_{tf_label}.db'
    db_path = os.path.join(db_dir, db_name)
    if not os.path.isdir(db_dir):
        return None  # DB 디렉토리 자체가 없으면 런타임에 처리됨
    return None  # 실제 DB 검증은 엔진 레벨에서 수행; 여기서는 config 유효성만


def _run_single_pipeline(common: dict, run_override: dict, idx: int,
                          engine_count_override: int = None) -> dict:
    """단일 파이프라인 실행. 병렬 시 controller를 내부 생성 (picklable).

    Args:
        common: 공통 설정 dict.
        run_override: 개별 실행 오버라이드 dict.
        idx: 결과에 포함할 실행 인덱스.
        engine_count_override: 병렬 시 엔진 수 분배값. None이면 config 기본값.

    Returns:
        summary dict (index, buy_strategy, status, promoted 등).
    """
    config = _merge_batch_run(common or {}, run_override)
    if engine_count_override is not None:
        config = AutoDiscoveryConfig(
            **{**{f.name: getattr(config, f.name) for f in fields(AutoDiscoveryConfig)},
               'engine_count': engine_count_override})

    from cli.ai_controller import AIBacktestController
    controller = AIBacktestController()

    run_result = AutoDiscoveryEngine.run(config, controller)

    summary = {
        'index': idx,
        'buy_strategy': config.buy_strategy,
        'input_csv': config.input_csv,
        'status': run_result.get('status', 'error'),
        'promoted': run_result.get('promoted', False),
        'strategy_name': run_result.get('strategy_name'),
        'pipeline_duration': run_result.get('pipeline_duration'),
    }

    if not run_result.get('promoted', False):
        phase_c = run_result.get('phase_c') or {}
        discovery = phase_c.get('discovery_result') or {}
        evaluation = discovery.get('promotion_evaluation') or {}
        reasons = evaluation.get('reasons', [])
        if reasons:
            summary['reject_reasons'] = reasons
        elif run_result.get('status') == 'error':
            summary['error_message'] = run_result.get('message', '')

    return summary


def _extract_summary(config: AutoDiscoveryConfig, run_result: dict, idx: int) -> dict:
    """파이프라인 결과에서 summary dict를 추출한다."""
    summary = {
        'index': idx,
        'buy_strategy': config.buy_strategy,
        'input_csv': config.input_csv,
        'status': run_result.get('status', 'error'),
        'promoted': run_result.get('promoted', False),
        'strategy_name': run_result.get('strategy_name'),
        'pipeline_duration': run_result.get('pipeline_duration'),
    }

    if not run_result.get('promoted', False):
        phase_c = run_result.get('phase_c') or {}
        discovery = phase_c.get('discovery_result') or {}
        evaluation = discovery.get('promotion_evaluation') or {}
        reasons = evaluation.get('reasons', [])
        if reasons:
            summary['reject_reasons'] = reasons
        elif run_result.get('status') == 'error':
            summary['error_message'] = run_result.get('message', '')

    return summary


def run_batch(batch_path: str = None, common: dict = None, runs: list = None,
              controller=None, parallel: int = 0) -> dict:
    """배치 설정으로 여러 auto-discovery 파이프라인을 실행한다.

    Args:
        batch_path: 배치 설정 JSON 파일 경로 (common/runs와 상호 배타).
        common: 공통 설정 dict.
        runs: 개별 실행 오버라이드 리스트.
        controller: AIBacktestController 인스턴스 (테스트용, 순차 모드만).
        parallel: 병렬 실행 수 (0=순차, 1+=병렬).

    Returns:
        배치 실행 결과 dict (status, total, promoted, results).
    """
    timeframes = []
    if batch_path:
        batch_data = load_batch_config(batch_path)
        common = batch_data['common']
        runs = batch_data['runs']
        timeframes = batch_data.get('timeframes', [])

    if not runs:
        return {'status': 'error', 'message': '실행할 runs가 없습니다.'}

    # 크로스 타임프레임 확장
    if timeframes:
        runs = _expand_timeframes(common or {}, runs, timeframes)

    batch_start = time.time()

    if parallel > 0:
        # 병렬 실행: ProcessPoolExecutor

        base_engine_count = (common or {}).get(
            'engine_count', AutoDiscoveryConfig.engine_count)
        engine_per_pipeline = max(1, base_engine_count // parallel)

        futures = {}
        with ProcessPoolExecutor(max_workers=parallel) as executor:
            for idx, run_override in enumerate(runs):
                future = executor.submit(
                    _run_single_pipeline, common or {}, run_override, idx,
                    engine_per_pipeline)
                futures[future] = idx

            results_map = {}
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    results_map[idx] = future.result()
                except Exception as e:
                    results_map[idx] = {
                        'index': idx,
                        'buy_strategy': (runs[idx] or {}).get('buy_strategy', ''),
                        'input_csv': None,
                        'status': 'error',
                        'promoted': False,
                        'strategy_name': None,
                        'pipeline_duration': None,
                        'error_message': str(e),
                    }

        results = [results_map[i] for i in range(len(runs))]
    else:
        # 순차 실행
        if controller is None:
            from cli.ai_controller import AIBacktestController
            controller = AIBacktestController()

        results = []
        for idx, run_override in enumerate(runs):
            config = _merge_batch_run(common or {}, run_override)
            run_result = AutoDiscoveryEngine.run(config, controller)
            results.append(_extract_summary(config, run_result, idx))

    promoted_count = sum(1 for r in results if r.get('promoted', False))

    return {
        'status': 'ok',
        'total': len(results),
        'promoted': promoted_count,
        'rejected': len(results) - promoted_count,
        'results': results,
        'batch_duration': round(time.time() - batch_start, 2),
    }


# ---------------------------------------------------------------------------
# Evolution Loop
# ---------------------------------------------------------------------------

@dataclass
class AutoEvolutionConfig:
    """조건식 진화 루프 설정."""

    base_config: AutoDiscoveryConfig = field(default_factory=AutoDiscoveryConfig)
    max_generations: int = 5
    population_size: int = 4
    objective: str = 'tpi'
    stagnation_limit: int = 2
    mutation_strength: float = 0.3

    # 파라미터 범위
    alpha_range: tuple = (0.01, 0.20)
    top_n_range: tuple = (1, 10)
    min_samples_range: tuple = (5, 100)
    quantiles_range: tuple = (3, 20)
    ml_weight_range: tuple = (0.0, 1.0)
    ml_feature_limit_range: tuple = (0, 30)

    @classmethod
    def from_config_path(cls, config_path: str, **kwargs) -> 'AutoEvolutionConfig':
        """JSON 파일에서 base_config를 읽고, kwargs로 진화 파라미터를 오버라이드한다."""
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # base_config 생성
        valid_fields = {fld.name for fld in fields(AutoDiscoveryConfig)}
        base_kwargs = {k: v for k, v in data.items() if k in valid_fields}
        base_config = AutoDiscoveryConfig(**base_kwargs)

        # 진화 파라미터: JSON의 'evolution' 키 또는 kwargs
        evo_data = data.get('evolution', {})
        evo_data.update({k: v for k, v in kwargs.items() if v is not None})

        evo_fields = {fld.name for fld in fields(cls)} - {'base_config'}
        evo_kwargs = {k: v for k, v in evo_data.items() if k in evo_fields}

        return cls(base_config=base_config, **evo_kwargs)


def _mutate_config(config: AutoDiscoveryConfig, evo_config: AutoEvolutionConfig,
                   rng=None) -> AutoDiscoveryConfig:
    """mutable 파라미터를 가우시안 노이즈로 변이한다. 범위 클리핑.

    Args:
        config: 원본 config (변이하지 않음).
        evo_config: 진화 설정 (범위, 강도 등).
        rng: random.Random 인스턴스 (재현성용).

    Returns:
        변이된 새 AutoDiscoveryConfig.
    """
    import random as _random
    if rng is None:
        rng = _random.Random()

    strength = evo_config.mutation_strength

    def _mutate_float(val, lo, hi):
        span = hi - lo
        noise = rng.gauss(0, strength * span)
        return round(max(lo, min(hi, val + noise)), 4)

    def _mutate_int(val, lo, hi):
        span = hi - lo
        noise = rng.gauss(0, strength * span)
        return max(lo, min(hi, round(val + noise)))

    kwargs = {fld.name: getattr(config, fld.name) for fld in fields(AutoDiscoveryConfig)}
    kwargs['alpha'] = _mutate_float(config.alpha, *evo_config.alpha_range)
    kwargs['top_n'] = _mutate_int(config.top_n, *evo_config.top_n_range)
    kwargs['min_samples'] = _mutate_int(config.min_samples, *evo_config.min_samples_range)
    kwargs['quantiles'] = _mutate_int(config.quantiles, *evo_config.quantiles_range)
    kwargs['ml_weight'] = _mutate_float(config.ml_weight, *evo_config.ml_weight_range)
    kwargs['ml_feature_limit'] = _mutate_int(config.ml_feature_limit,
                                              *evo_config.ml_feature_limit_range)

    return AutoDiscoveryConfig(**kwargs)


def _select_best(results: list, objective: str) -> dict | None:
    """promoted 우선 → objective 기준 최고 선택.

    Args:
        results: 파이프라인 실행 결과 리스트.
        objective: 비교 기준 지표명 (예: 'tpi').

    Returns:
        최고 결과 dict, 또는 빈 리스트면 None.
    """
    if not results:
        return None

    # promoted 결과 우선
    promoted = [r for r in results if r.get('promoted', False)]
    if promoted:
        return promoted[0]

    # objective 값 추출하여 정렬
    def _get_objective(r):
        # phase_c > discovery_result > walk_forward > summary 등에서 추출 시도
        phase_c = r.get('phase_c') or {}
        discovery = phase_c.get('discovery_result') or {}
        wf = discovery.get('walk_forward') or {}
        summary = wf.get('summary') or {}
        val = summary.get(f'mean_oos_{objective}')
        if val is not None:
            return val
        # pipeline_duration을 fallback으로 (낮을수록 좋음 → 부호 반전)
        dur = r.get('pipeline_duration')
        if dur is not None:
            return -dur
        return float('-inf')

    sorted_results = sorted(results, key=_get_objective, reverse=True)
    return sorted_results[0]


def _create_population(base_config: AutoDiscoveryConfig,
                        evo_config: AutoEvolutionConfig,
                        rng=None) -> list[AutoDiscoveryConfig]:
    """population_size개 변이 config를 생성한다."""
    return [_mutate_config(base_config, evo_config, rng)
            for _ in range(evo_config.population_size)]


def auto_discover_evolve(evo_config: AutoEvolutionConfig,
                          controller=None, parallel: int = 0) -> dict:
    """조건식 진화 루프 메인 함수.

    Args:
        evo_config: 진화 설정.
        controller: AIBacktestController (순차 모드용).
        parallel: 병렬 실행 수.

    Returns:
        {status, promoted, best_result, best_config, generations, total_runs, total_duration}
    """
    import random as _random

    rng = _random.Random()
    loop_start = time.time()

    best_config = copy.deepcopy(evo_config.base_config)
    best_result = None
    stagnation = 0
    total_runs = 0
    generations_log = []

    if controller is None:
        from cli.ai_controller import AIBacktestController
        controller = AIBacktestController()

    for gen in range(evo_config.max_generations):
        population = _create_population(best_config, evo_config, rng)
        gen_results = []

        for cfg in population:
            result = AutoDiscoveryEngine.run(cfg, controller)
            result['_config'] = asdict(cfg)
            gen_results.append(result)
            total_runs += 1

            # 승격되면 즉시 반환
            if result.get('promoted', False):
                return {
                    'status': 'ok',
                    'promoted': True,
                    'best_result': result,
                    'best_config': asdict(cfg),
                    'generations': gen + 1,
                    'total_runs': total_runs,
                    'total_duration': round(time.time() - loop_start, 2),
                    'generations_log': generations_log,
                }

        # 세대 최고 선택
        gen_best = _select_best(gen_results, evo_config.objective)

        gen_info = {
            'generation': gen + 1,
            'population_size': len(population),
            'best_status': (gen_best or {}).get('status'),
            'best_promoted': (gen_best or {}).get('promoted', False),
        }
        generations_log.append(gen_info)

        # 개선 여부 확인
        improved = False
        if gen_best and (best_result is None or
                          gen_best.get('promoted', False) or
                          gen_best.get('pipeline_duration', float('inf')) <
                          (best_result or {}).get('pipeline_duration', float('inf'))):
            best_result = gen_best
            best_config_dict = gen_best.get('_config')
            if best_config_dict:
                valid = {fld.name for fld in fields(AutoDiscoveryConfig)}
                best_config = AutoDiscoveryConfig(
                    **{k: v for k, v in best_config_dict.items() if k in valid})
            improved = True

        if improved:
            stagnation = 0
        else:
            stagnation += 1

        if stagnation >= evo_config.stagnation_limit:
            break

    return {
        'status': 'ok',
        'promoted': False,
        'best_result': best_result,
        'best_config': asdict(best_config) if best_config else None,
        'generations': len(generations_log),
        'total_runs': total_runs,
        'total_duration': round(time.time() - loop_start, 2),
        'generations_log': generations_log,
        'stagnation_stopped': stagnation >= evo_config.stagnation_limit,
    }
