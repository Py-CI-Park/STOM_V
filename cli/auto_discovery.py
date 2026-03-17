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
from dataclasses import dataclass, field

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
        }

    # ------- Phase B: 다단계 분석 + 조건 생성 -------

    def _phase_b_analysis(self, csv_path: str) -> dict:
        """CSV를 분석하고 조건 코드를 생성한다."""
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
        }

    # ------- Phase C: WFO 검증 + 승격 -------

    def _phase_c_validate_and_promote(self, csv_path: str) -> dict:
        """기존 discover_and_promote_strategy()를 활용해 WFO 검증 → 승격을 수행한다."""
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

        return {
            'status': phase_c.get('status', 'error'),
            'promoted': phase_c.get('promoted', False),
            'strategy_name': phase_c.get('strategy_name'),
            'csv_path': csv_path,
            'phase_a': phase_a,
            'phase_b': phase_b,
            'phase_c': phase_c,
            'pipeline_duration': round(time.time() - pipeline_start, 2),
        }
