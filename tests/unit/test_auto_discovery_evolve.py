"""조건식 진화 루프 단위 테스트."""

import os
import sys
import json
import random

import pytest
from unittest.mock import patch, MagicMock
from dataclasses import asdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from cli.auto_discovery import (
    AutoDiscoveryConfig,
    AutoEvolutionConfig,
    _mutate_config,
    _select_best,
    _create_population,
    auto_discover_evolve,
)


# ---------------------------------------------------------------------------
# TestAutoEvolutionConfig
# ---------------------------------------------------------------------------

class TestAutoEvolutionConfig:
    """AutoEvolutionConfig 기본 테스트."""

    def test_default_values(self):
        config = AutoEvolutionConfig()
        assert config.max_generations == 5
        assert config.population_size == 4
        assert config.objective == 'tpi'
        assert config.stagnation_limit == 2
        assert config.mutation_strength == 0.3

    def test_all_fields_exist(self):
        config = AutoEvolutionConfig()
        assert hasattr(config, 'base_config')
        assert hasattr(config, 'alpha_range')
        assert hasattr(config, 'top_n_range')
        assert hasattr(config, 'min_samples_range')
        assert hasattr(config, 'quantiles_range')
        assert hasattr(config, 'ml_weight_range')
        assert hasattr(config, 'ml_feature_limit_range')

    def test_from_config_path(self, tmp_path):
        config_file = tmp_path / 'evo.json'
        config_file.write_text(json.dumps({
            'buy_strategy': 'TestBuy',
            'sell_strategy': 'TestSell',
            'start_date': 20250401,
            'end_date': 20250430,
            'train_window_days': 30,
            'test_window_days': 10,
            'evolution': {
                'max_generations': 3,
                'population_size': 2,
            },
        }), encoding='utf-8')

        evo = AutoEvolutionConfig.from_config_path(str(config_file))
        assert evo.base_config.buy_strategy == 'TestBuy'
        assert evo.max_generations == 3
        assert evo.population_size == 2


# ---------------------------------------------------------------------------
# TestMutateConfig
# ---------------------------------------------------------------------------

class TestMutateConfig:
    """_mutate_config() 변이 테스트."""

    def test_within_range(self):
        base = AutoDiscoveryConfig(alpha=0.05, top_n=5, min_samples=30,
                                    quantiles=10, ml_weight=0.0, ml_feature_limit=0)
        evo = AutoEvolutionConfig(mutation_strength=0.5)
        rng = random.Random(42)

        for _ in range(20):
            mutated = _mutate_config(base, evo, rng)
            assert evo.alpha_range[0] <= mutated.alpha <= evo.alpha_range[1]
            assert evo.top_n_range[0] <= mutated.top_n <= evo.top_n_range[1]
            assert evo.min_samples_range[0] <= mutated.min_samples <= evo.min_samples_range[1]
            assert evo.quantiles_range[0] <= mutated.quantiles <= evo.quantiles_range[1]
            assert evo.ml_weight_range[0] <= mutated.ml_weight <= evo.ml_weight_range[1]

    def test_immutability_preserved(self):
        """원본 config가 변이되지 않음."""
        base = AutoDiscoveryConfig(alpha=0.05, top_n=5)
        evo = AutoEvolutionConfig(mutation_strength=0.5)
        rng = random.Random(42)

        _mutate_config(base, evo, rng)
        assert base.alpha == 0.05
        assert base.top_n == 5

    def test_seed_reproducibility(self):
        """같은 시드면 같은 결과."""
        base = AutoDiscoveryConfig(alpha=0.05, top_n=5, min_samples=30)
        evo = AutoEvolutionConfig(mutation_strength=0.3)

        m1 = _mutate_config(base, evo, random.Random(123))
        m2 = _mutate_config(base, evo, random.Random(123))
        assert m1.alpha == m2.alpha
        assert m1.top_n == m2.top_n
        assert m1.min_samples == m2.min_samples

    def test_different_from_base(self):
        """변이 결과는 원본과 (높은 확률로) 다름."""
        base = AutoDiscoveryConfig(alpha=0.10, top_n=5, min_samples=50)
        evo = AutoEvolutionConfig(mutation_strength=0.5)

        any_different = False
        for seed in range(10):
            m = _mutate_config(base, evo, random.Random(seed))
            if m.alpha != base.alpha or m.top_n != base.top_n:
                any_different = True
                break
        assert any_different


# ---------------------------------------------------------------------------
# TestSelectBest
# ---------------------------------------------------------------------------

class TestSelectBest:
    """_select_best() 선택 로직 테스트."""

    def test_promoted_priority(self):
        """promoted 결과 우선."""
        results = [
            {'status': 'ok', 'promoted': False, 'pipeline_duration': 5.0},
            {'status': 'ok', 'promoted': True, 'pipeline_duration': 20.0},
        ]
        best = _select_best(results, 'tpi')
        assert best['promoted'] is True

    def test_objective_sorting(self):
        """promoted 없으면 pipeline_duration fallback."""
        results = [
            {'status': 'ok', 'promoted': False, 'pipeline_duration': 20.0},
            {'status': 'ok', 'promoted': False, 'pipeline_duration': 10.0},
        ]
        best = _select_best(results, 'tpi')
        # pipeline_duration fallback: -duration으로 정렬, 10이 -10, 20이 -20
        # -10 > -20 이므로 duration=10이 선택됨
        assert best['pipeline_duration'] == 10.0

    def test_empty_results(self):
        assert _select_best([], 'tpi') is None


# ---------------------------------------------------------------------------
# TestCreatePopulation
# ---------------------------------------------------------------------------

class TestCreatePopulation:
    """_create_population() 테스트."""

    def test_population_size(self):
        base = AutoDiscoveryConfig(alpha=0.05)
        evo = AutoEvolutionConfig(population_size=6)
        population = _create_population(base, evo, random.Random(42))
        assert len(population) == 6

    def test_diversity(self):
        """개체들이 서로 다름."""
        base = AutoDiscoveryConfig(alpha=0.05, top_n=5)
        evo = AutoEvolutionConfig(population_size=5, mutation_strength=0.5)
        population = _create_population(base, evo, random.Random(42))

        alphas = [p.alpha for p in population]
        # 최소 2개는 서로 다를 것
        assert len(set(alphas)) >= 2


# ---------------------------------------------------------------------------
# TestAutoDiscoverEvolve
# ---------------------------------------------------------------------------

class TestAutoDiscoverEvolve:
    """auto_discover_evolve() 메인 루프 테스트."""

    def _make_result(self, promoted=False, duration=10.0, status='ok'):
        return {
            'status': status,
            'promoted': promoted,
            'strategy_name': 'Auto_Test' if promoted else None,
            'csv_path': '/tmp/test.csv',
            'pipeline_duration': duration,
            'phase_a': {}, 'phase_b': {}, 'phase_c': {},
            'pipeline_timing': {'phase_a': 1.0, 'phase_b': 2.0, 'phase_c': 3.0,
                                'total': duration},
        }

    def test_first_promotion_stops(self):
        """첫 승격 시 즉시 중단."""
        controller = MagicMock()

        call_count = [0]
        def mock_run(config, ctrl):
            call_count[0] += 1
            # 3번째 호출에서 승격
            return self._make_result(promoted=(call_count[0] == 3))

        with patch('cli.auto_discovery.AutoDiscoveryEngine.run', side_effect=mock_run):
            evo = AutoEvolutionConfig(
                base_config=AutoDiscoveryConfig(buy_strategy='A', sell_strategy='S',
                                                 train_window_days=30, test_window_days=10),
                max_generations=5,
                population_size=4,
            )
            result = auto_discover_evolve(evo, controller=controller)

        assert result['promoted'] is True
        assert result['total_runs'] == 3  # 3번째에서 중단

    def test_stagnation_stops(self):
        """개선 없으면 stagnation_limit에서 중단."""
        controller = MagicMock()

        with patch('cli.auto_discovery.AutoDiscoveryEngine.run',
                   return_value=self._make_result(promoted=False, duration=10.0)):
            evo = AutoEvolutionConfig(
                base_config=AutoDiscoveryConfig(buy_strategy='A', sell_strategy='S',
                                                 train_window_days=30, test_window_days=10),
                max_generations=10,
                population_size=2,
                stagnation_limit=2,
            )
            result = auto_discover_evolve(evo, controller=controller)

        assert result['promoted'] is False
        assert result['stagnation_stopped'] is True
        # 첫 세대에서 best 설정, 이후 2세대 정체 → 3세대 실행 후 중단
        assert result['generations'] <= 4

    def test_all_generations_exhausted(self):
        """전 세대 소진."""
        controller = MagicMock()
        gen_count = [0]

        def improving_run(config, ctrl):
            gen_count[0] += 1
            # 매번 조금씩 duration 줄여 개선
            return self._make_result(promoted=False, duration=100.0 - gen_count[0])

        with patch('cli.auto_discovery.AutoDiscoveryEngine.run', side_effect=improving_run):
            evo = AutoEvolutionConfig(
                base_config=AutoDiscoveryConfig(buy_strategy='A', sell_strategy='S',
                                                 train_window_days=30, test_window_days=10),
                max_generations=3,
                population_size=2,
                stagnation_limit=10,  # 높게 설정하여 stagnation으로 중단되지 않도록
            )
            result = auto_discover_evolve(evo, controller=controller)

        assert result['promoted'] is False
        assert result['generations'] == 3
        assert result['total_runs'] == 6  # 3 gens × 2 pop

    def test_improvement_tracking(self):
        """best_result가 개선됨."""
        controller = MagicMock()
        call_idx = [0]

        def run_with_decreasing_duration(config, ctrl):
            call_idx[0] += 1
            return self._make_result(promoted=False, duration=50.0 - call_idx[0])

        with patch('cli.auto_discovery.AutoDiscoveryEngine.run',
                   side_effect=run_with_decreasing_duration):
            evo = AutoEvolutionConfig(
                base_config=AutoDiscoveryConfig(buy_strategy='A', sell_strategy='S',
                                                 train_window_days=30, test_window_days=10),
                max_generations=2,
                population_size=2,
                stagnation_limit=10,
            )
            result = auto_discover_evolve(evo, controller=controller)

        assert result['best_result'] is not None
        assert result['best_config'] is not None
        assert 'total_duration' in result

    def test_returns_generations_log(self):
        """generations_log 구조 확인."""
        controller = MagicMock()

        with patch('cli.auto_discovery.AutoDiscoveryEngine.run',
                   return_value=self._make_result(promoted=False)):
            evo = AutoEvolutionConfig(
                base_config=AutoDiscoveryConfig(buy_strategy='A', sell_strategy='S',
                                                 train_window_days=30, test_window_days=10),
                max_generations=2,
                population_size=2,
                stagnation_limit=3,
            )
            result = auto_discover_evolve(evo, controller=controller)

        log = result['generations_log']
        assert len(log) >= 1
        assert 'generation' in log[0]
        assert 'population_size' in log[0]


# ---------------------------------------------------------------------------
# TestEvolveCliParsing
# ---------------------------------------------------------------------------

class TestEvolveCliParsing:
    """discovery evolve CLI 파싱 테스트."""

    def test_evolve_help(self):
        from cli.subcommands import create_subcommand_parser
        parser = create_subcommand_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(['discovery', 'evolve', '--help'])
        assert exc_info.value.code == 0

    def test_evolve_parse_args(self):
        from cli.subcommands import create_subcommand_parser
        parser = create_subcommand_parser()
        args = parser.parse_args([
            'discovery', 'evolve', '--config', 'base.json',
            '--max-generations', '3', '--population-size', '6',
            '--objective', 'cagr', '--stagnation-limit', '1',
            '--mutation-strength', '0.5', '--parallel', '2', '--seed', '42',
        ])
        assert args.discovery_action == 'evolve'
        assert args.evolve_config == 'base.json'
        assert args.max_generations == 3
        assert args.population_size == 6
        assert args.objective == 'cagr'
        assert args.stagnation_limit == 1
        assert args.mutation_strength == 0.5
        assert args.parallel == 2
        assert args.seed == 42

    def test_evolve_missing_config(self):
        from cli.subcommands import create_subcommand_parser
        parser = create_subcommand_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(['discovery', 'evolve'])
        assert exc_info.value.code != 0
