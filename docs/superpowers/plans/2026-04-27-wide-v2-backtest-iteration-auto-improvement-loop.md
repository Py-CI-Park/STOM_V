# Wide v2 Backtest Iteration Auto Improvement Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Wide v2 CLI loop that repeatedly runs candidate backtests, promotes each round's best candidate into the next round seed, records a leaderboard, and hands only the final candidate to later WFO validation.

**Architecture:** Reuse the existing `cli.research_loop.run_research_iteration()` path for candidate generation, backtest execution, ranking, runtime output, and v5 actual row-set selection. Add a thin optimizer layer split into state/leaderboard helpers, a multi-round coordinator, a Markdown report writer, and a discoverable `discovery optimize-wide-v2` CLI action.

**Tech Stack:** Python 3.11, argparse, dataclasses, pathlib, json, pytest, existing STOM CLI research modules.

---

## Scope Check

The approved spec covers one connected subsystem: a Wide v2 optimizer wrapper around the existing research iteration flow. It has three internal responsibilities, but they are not independent products:

- state and leaderboard data helpers
- multi-round coordinator
- report and CLI integration

This plan keeps those pieces in separate files and separate commits so each task is reviewable. It does not implement WFO, live trading, paper trading, broad `cli/` refactoring, or new candidate-generation families beyond what existing Wide v1 v5 helpers already provide.

## File Structure

- Create: `cli/research_optimizer_state.py`
  - Owns `WideV2OptimizerConfig`, round/result data conversion, JSON-safe normalization, leaderboard entry construction, global best selection, path derivation, and score improvement helpers.
- Create: `cli/research_optimizer.py`
  - Owns the multi-round loop, `ResearchLoopConfig` construction per round, stop condition handling, seed propagation, and runtime JSON writing for optimizer-level summary/leaderboard.
- Create: `cli/research_optimizer_report.py`
  - Owns Markdown summary and leaderboard rendering for curated reports under `docs/research/condition_research/pilot_logs/`.
- Modify: `cli/research_loop.py`
  - Adds a small `iteration_v2_trade_amount_feature` config field so existing v3/v4/v5 helpers can parse WideV1Final-style two-condition seeds whose second feature is `B_등락율`, while preserving the default `B_당일거래대금` behavior.
- Modify: `cli/subcommands.py`
  - Adds `discovery optimize-wide-v2`, parses optimizer options, calls `run_wide_v2_optimizer()`, and prints JSON result.
- Modify: `tests/unit/test_research_loop.py`
  - Adds regression coverage for configurable v3/v4/v5 seed second feature parsing.
- Create: `tests/unit/test_research_optimizer_state.py`
  - Tests config defaults, JSON-safe serialization, leaderboard entries, global best selection, and improvement scoring.
- Create: `tests/unit/test_research_optimizer.py`
  - Tests multi-round happy path, seed propagation, stop reasons, runtime JSON writing, and completed-round preservation on failure with mocked `run_research_iteration()`.
- Create: `tests/unit/test_research_optimizer_report.py`
  - Tests Markdown report sections and WFO handoff wording.
- Modify: `tests/unit/test_subcommands.py`
  - Adds parser and handler coverage for `discovery optimize-wide-v2`.
- Create: `docs/pr/2026-04-27_wide_v2_backtest_iteration_auto_improvement_loop_pr.md`
  - Korean PR report for the implementation branch after code is complete.

Do not modify or stage these paths:

- `utility/strategy.db`
- `backtest/graph/`
- `backtest/temp/` runtime JSON outputs by default
- `backtest/csv/` generated CSV outputs
- Wide v1 freeze reports and WFO evidence files

---

### Task 0: Research Loop Seed Feature Compatibility

**Files:**
- Modify: `tests/unit/test_research_loop.py`
- Modify: `tests/unit/test_subcommands.py`
- Modify: `cli/research_loop.py`
- Modify: `cli/subcommands.py`

- [ ] **Step 1: Add failing research loop config and validation tests**

Append these tests near the existing iteration v2 field and validation tests in `tests/unit/test_research_loop.py`:

```python
def test_research_loop_config_has_iteration_v2_trade_amount_feature():
    names = {field.name for field in fields(ResearchLoopConfig)}
    assert 'iteration_v2_trade_amount_feature' in names

    config = ResearchLoopConfig()
    assert config.iteration_v2_trade_amount_feature == 'B_당일거래대금'


def test_validate_research_iteration_accepts_custom_second_seed_feature(tmp_path):
    result = research_loop.validate_research_iteration_config(
        ResearchLoopConfig(
            name='CustomSecondFeature',
            baseline_csv=str(tmp_path / 'baseline.csv'),
            run_candidates=True,
            candidate_count=2,
            iteration_v2_mode='best_feature_mix_v5',
            iteration_v2_best_candidate='WideV1Final_B_20260425',
            iteration_v2_best_expression='66.999 <= 시가총액 < 2_580 and 등락율 > 4.83',
            iteration_v2_primary_feature='B_시가총액',
            iteration_v2_trade_amount_feature='B_등락율',
        )
    )

    assert result['status'] == 'ok'


def test_validate_research_iteration_rejects_custom_second_feature_mismatch(tmp_path):
    result = research_loop.validate_research_iteration_config(
        ResearchLoopConfig(
            name='CustomSecondFeatureMismatch',
            baseline_csv=str(tmp_path / 'baseline.csv'),
            run_candidates=True,
            candidate_count=2,
            iteration_v2_mode='best_feature_mix_v5',
            iteration_v2_best_candidate='WideV1Final_B_20260425',
            iteration_v2_best_expression='66.999 <= 시가총액 < 2_580 and 등락율 > 4.83',
            iteration_v2_primary_feature='B_시가총액',
            iteration_v2_trade_amount_feature='B_당일거래대금',
        )
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'invalid_iteration_v2_best_expression'
```

- [ ] **Step 2: Add failing discovery research parser and handler tests**

Append these tests near the existing `iteration_v2` CLI tests in `tests/unit/test_subcommands.py`:

```python
def test_discovery_research_parser_accepts_iteration_v2_trade_amount_feature():
    parser = create_subcommand_parser()

    args = parser.parse_args([
        'discovery', 'research', 'V5Run',
        '--input', 'baseline.csv',
        '--base-buy-strategy', 'BaseBuy',
        '--sell', 'BaseSell',
        '--start', '20250101',
        '--end', '20251231',
        '--run-candidates',
        '--iteration-v2-mode', 'best_feature_mix_v5',
        '--iteration-v2-best-candidate', 'WideV1Final_B_20260425',
        '--iteration-v2-best-expression', '66.999 <= 시가총액 < 2_580 and 등락율 > 4.83',
        '--iteration-v2-primary-feature', 'B_시가총액',
        '--iteration-v2-trade-amount-feature', 'B_등락율',
    ])

    assert args.iteration_v2_trade_amount_feature == 'B_등락율'


def test_discovery_research_handler_passes_iteration_v2_trade_amount_feature():
    with patch('cli.ai_controller.AIBacktestController.research_strategy_once') as mock:
        mock.return_value = {'status': 'ok'}
        result = handle_subcommand([
            'discovery', 'research', 'V5Run',
            '--input', 'baseline.csv',
            '--base-buy-strategy', 'BaseBuy',
            '--sell', 'BaseSell',
            '--start', '20250101',
            '--end', '20251231',
            '--run-candidates',
            '--iteration-v2-mode', 'best_feature_mix_v5',
            '--iteration-v2-best-candidate', 'WideV1Final_B_20260425',
            '--iteration-v2-best-expression', '66.999 <= 시가총액 < 2_580 and 등락율 > 4.83',
            '--iteration-v2-primary-feature', 'B_시가총액',
            '--iteration-v2-trade-amount-feature', 'B_등락율',
        ])

    payload = mock.call_args.args[0]
    assert result == 0
    assert payload['iteration_v2_trade_amount_feature'] == 'B_등락율'
```

- [ ] **Step 3: Run the focused failing tests**

Run:

```powershell
python -m pytest `
  tests/unit/test_research_loop.py::test_research_loop_config_has_iteration_v2_trade_amount_feature `
  tests/unit/test_research_loop.py::test_validate_research_iteration_accepts_custom_second_seed_feature `
  tests/unit/test_research_loop.py::test_validate_research_iteration_rejects_custom_second_feature_mismatch `
  tests/unit/test_subcommands.py::test_discovery_research_parser_accepts_iteration_v2_trade_amount_feature `
  tests/unit/test_subcommands.py::test_discovery_research_handler_passes_iteration_v2_trade_amount_feature `
  -q
```

Expected now:

```text
FAILED
```

The failures should mention the missing dataclass field or unrecognized `--iteration-v2-trade-amount-feature`.

- [ ] **Step 4: Add the `ResearchLoopConfig` field**

In `cli/research_loop.py`, add this field immediately after `iteration_v2_primary_feature`:

```python
    iteration_v2_trade_amount_feature: str = 'B_당일거래대금'
```

- [ ] **Step 5: Include the field in the iteration plan**

In `_build_iteration_plan()` in `cli/research_loop.py`, add this key after `iteration_v2_primary_feature`:

```python
        'iteration_v2_trade_amount_feature': config.iteration_v2_trade_amount_feature,
```

- [ ] **Step 6: Use the configurable second feature in validation**

In `validate_research_iteration_config()` in `cli/research_loop.py`, replace the local `trade_amount_feature` assignment block with:

```python
        trade_amount_feature = config.iteration_v2_trade_amount_feature
```

Keep the existing `parse_best_expression_conditions(...)` call, but pass this configurable value.

- [ ] **Step 7: Pass the field to v3/v4/v5 candidate builders**

In `run_research_iteration()` in `cli/research_loop.py`, update both `build_v3_candidate_pool(...)` and `build_v4_candidate_pool(...)` calls to include:

```python
            trade_amount_feature=config.iteration_v2_trade_amount_feature,
```

The v5 path uses `build_v4_candidate_pool(...)`, so this single v4 call also covers v5.

- [ ] **Step 8: Add the discovery research CLI argument**

In the `discovery research` parser block in `cli/subcommands.py`, add this argument after `--iteration-v2-primary-feature`:

```python
    disc_research.add_argument('--iteration-v2-trade-amount-feature', default='B_당일거래대금')
```

- [ ] **Step 9: Pass the CLI value to the controller payload**

In the `parsed.discovery_action == 'research'` payload in `cli/subcommands.py`, add this key after `iteration_v2_primary_feature`:

```python
            'iteration_v2_trade_amount_feature': parsed.iteration_v2_trade_amount_feature,
```

- [ ] **Step 10: Run the Task 0 tests**

Run:

```powershell
python -m pytest `
  tests/unit/test_research_loop.py::test_research_loop_config_has_iteration_v2_trade_amount_feature `
  tests/unit/test_research_loop.py::test_validate_research_iteration_accepts_custom_second_seed_feature `
  tests/unit/test_research_loop.py::test_validate_research_iteration_rejects_custom_second_feature_mismatch `
  tests/unit/test_subcommands.py::test_discovery_research_parser_accepts_iteration_v2_trade_amount_feature `
  tests/unit/test_subcommands.py::test_discovery_research_handler_passes_iteration_v2_trade_amount_feature `
  -q
```

Expected:

```text
5 passed
```

- [ ] **Step 11: Commit Task 0**

Run:

```powershell
git add cli/research_loop.py cli/subcommands.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py
git commit -m "Wide v1 final seed의 두 번째 feature를 설정 가능하게 한다" -m "WideV1Final_B_20260425처럼 시가총액과 등락율을 조합한 seed expression을 Wide v2/v5 루프에 넘길 수 있도록 iteration_v2 두 번째 필수 feature를 설정 가능하게 한다.

Constraint: 기존 기본값 B_당일거래대금 동작은 유지해야 한다
Rejected: Wide v2 smoke에서 가짜 당일거래대금 seed 사용 | 실제 Wide v1 final 조건식과 달라 후속 연구가 왜곡된다
Confidence: medium
Scope-risk: moderate
Tested: python -m pytest tests/unit/test_research_loop.py::test_research_loop_config_has_iteration_v2_trade_amount_feature tests/unit/test_research_loop.py::test_validate_research_iteration_accepts_custom_second_seed_feature tests/unit/test_research_loop.py::test_validate_research_iteration_rejects_custom_second_feature_mismatch tests/unit/test_subcommands.py::test_discovery_research_parser_accepts_iteration_v2_trade_amount_feature tests/unit/test_subcommands.py::test_discovery_research_handler_passes_iteration_v2_trade_amount_feature -q
Not-tested: 실제 백테스트 실행"
```

---

### Task 1: Optimizer State And Leaderboard Helpers

**Files:**
- Create: `tests/unit/test_research_optimizer_state.py`
- Create: `cli/research_optimizer_state.py`

- [ ] **Step 1: Write failing state and leaderboard tests**

Create `tests/unit/test_research_optimizer_state.py` with this content:

```python
import json
import math

from cli.research_optimizer_state import (
    WideV2OptimizerConfig,
    build_leaderboard_entries,
    compute_improvement,
    json_safe_value,
    mark_global_best,
    round_runtime_output_path,
    select_global_best_candidate,
)


def _candidate(name, expression, score, *, selected=False, status='ok', index=1):
    return {
        'index': index,
        'strategy_name': name,
        'expression': expression,
        'status': status,
        'selected_as_best': selected,
        'actual_rowset_selected': selected,
        'candidate_csv': f'backtest/csv/{name}.csv',
        'rank_score': {
            'promotion_passed': score > 0,
            'promotion_score': score,
            'adjusted_score': score,
            'score_basis': 'reference',
            'trade_count': 100 + index,
            'trade_count_retention': 0.5,
            'date_concentration': 0.2,
            'symbol_concentration': 0.1,
        },
        'comparison': {
            'candidate_summary': {
                'trade_count': 100 + index,
                'date_concentration': 0.2,
                'symbol_concentration': 0.1,
            },
            'trade_count_retention': 0.5,
        },
    }


def test_optimizer_config_defaults_are_mvp_safe():
    config = WideV2OptimizerConfig(
        name='WideV2Run',
        base_buy_strategy='WideV1Final_B_20260425',
        sell_strategy='ResearchTest_Tick_S_090000_092800_Wide_20260419',
        start_date=20250101,
        end_date=20251231,
    )

    assert config.candidate_count == 10
    assert config.max_rounds == 3
    assert config.min_improvement == 0.01
    assert config.stop_after_no_improvement == 2
    assert config.iteration_v2_mode == 'best_feature_mix_v5'
    assert config.iteration_v2_trade_amount_feature == 'B_당일거래대금'
    assert config.run_id == 'WideV2Run'


def test_round_runtime_output_path_derives_round_specific_json():
    config = WideV2OptimizerConfig(
        name='WideV2Run',
        runtime_output_path='backtest/temp/wide_v2_run.json',
    )

    assert round_runtime_output_path(config, 2) == 'backtest/temp/wide_v2_run_round002.json'


def test_json_safe_value_normalizes_non_finite_numbers():
    payload = {
        'good': 1.5,
        'nan': math.nan,
        'inf': math.inf,
        'items': [1, math.nan],
    }

    safe = json_safe_value(payload)

    assert safe == {'good': 1.5, 'nan': None, 'inf': None, 'items': [1, None]}
    json.dumps(safe)


def test_build_leaderboard_entries_uses_candidate_rank_score():
    round_result = {
        'status': 'ok',
        'best_candidate': _candidate('Round1__cand002', '등락율 > 4.8', 2.0, selected=True, index=2),
        'candidates': [
            _candidate('Round1__cand001', '등락율 > 4.0', 1.0, index=1),
            _candidate('Round1__cand002', '등락율 > 4.8', 2.0, selected=True, index=2),
        ],
    }

    entries = build_leaderboard_entries(
        run_id='WideV2Run',
        round_index=1,
        round_result=round_result,
        source_baseline='WideV1Final_B_20260425',
        source_candidate='WideV1Final_B_20260425',
    )

    assert len(entries) == 2
    assert entries[1]['run_id'] == 'WideV2Run'
    assert entries[1]['round_index'] == 1
    assert entries[1]['candidate_index'] == 2
    assert entries[1]['strategy_name'] == 'Round1__cand002'
    assert entries[1]['expression'] == '등락율 > 4.8'
    assert entries[1]['promotion_passed'] is True
    assert entries[1]['adjusted_score'] == 2.0
    assert entries[1]['selected_as_round_best'] is True
    assert entries[1]['selected_as_global_best'] is False
    assert entries[1]['runtime_json_path'] is None
    assert entries[1]['candidate_csv_path'] == 'backtest/csv/Round1__cand002.csv'


def test_select_and_mark_global_best_candidate():
    entries = [
        build_leaderboard_entries(
            run_id='WideV2Run',
            round_index=1,
            round_result={'candidates': [_candidate('R1__cand001', 'A', 1.0, selected=True)]},
            source_baseline='Base',
            source_candidate='Seed',
        )[0],
        build_leaderboard_entries(
            run_id='WideV2Run',
            round_index=2,
            round_result={'candidates': [_candidate('R2__cand001', 'B', 3.0, selected=True)]},
            source_baseline='Base',
            source_candidate='R1__cand001',
        )[0],
    ]

    best = select_global_best_candidate(entries)
    marked = mark_global_best(entries, best)

    assert best['strategy_name'] == 'R2__cand001'
    assert marked[0]['selected_as_global_best'] is False
    assert marked[1]['selected_as_global_best'] is True


def test_compute_improvement_uses_adjusted_score_delta():
    previous = {'adjusted_score': 1.25}
    current = {'adjusted_score': 1.50}

    assert compute_improvement(current, previous) == 0.25
    assert compute_improvement(current, None) is None
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_research_optimizer_state.py -q
```

Expected now:

```text
FAILED
```

The failure should mention `ModuleNotFoundError: No module named 'cli.research_optimizer_state'`.

- [ ] **Step 3: Create the optimizer state helper**

Create `cli/research_optimizer_state.py` with this content:

```python
"""State and leaderboard helpers for Wide v2 optimizer runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class WideV2OptimizerConfig:
    name: str = 'WideV2AutoLoop'
    baseline_csv: str | None = None
    score_reference_csv: str | None = None
    base_buy_strategy: str = ''
    sell_strategy: str = ''
    seed_candidate: str = ''
    seed_expression: str = ''
    start_date: int = 0
    end_date: int = 0
    is_tick: bool = True
    betting: str = '1'
    avg_time: object = 60
    start_time: int = 90000
    end_time: int = 152800
    engine_count: int = 4
    top_n: int = 1
    min_samples: int = 30
    quantiles: int = 10
    alpha: float = 0.05
    candidate_count: int = 10
    candidate_timeout: int | None = None
    cleanup_best_candidate: bool = False
    keep_loser_candidates: bool = False
    keep_failed_candidate: bool = False
    min_estimated_retention: float = 0.40
    allow_retention_fallback: bool = True
    use_retention_penalty: bool = True
    candidate_pool_multiplier: int = 3
    iteration_v2_mode: str = 'best_feature_mix_v5'
    iteration_v2_primary_feature: str = 'B_시가총액'
    iteration_v2_trade_amount_feature: str = 'B_당일거래대금'
    iteration_v2_secondary_features: str = ''
    iteration_v2_include_secondary_only: bool = True
    iteration_v2_max_secondary_only: int = 1
    iteration_v2_duplicate_retention_tolerance: float = 0.02
    max_rounds: int = 3
    min_improvement: float = 0.01
    stop_after_no_improvement: int = 2
    max_consecutive_candidate_failures: int = 3
    runtime_output_path: str | None = None
    leaderboard_output_path: str | None = None
    summary_output_path: str | None = None
    report_path: str | None = None

    @property
    def run_id(self) -> str:
        return self.name


@dataclass(frozen=True)
class WideV2RoundState:
    round_index: int
    status: str
    stop_reason: str | None
    source_candidate: str
    runtime_json_path: str | None
    round_best_candidate: dict[str, Any] | None


@dataclass(frozen=True)
class WideV2OptimizerResult:
    status: str
    run_id: str
    stop_reason: str
    rounds: list[dict[str, Any]]
    leaderboard: list[dict[str, Any]]
    final_best_candidate: dict[str, Any] | None
    wfo_candidate: dict[str, Any] | None
    summary_output_path: str | None = None
    leaderboard_output_path: str | None = None
    report_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return json_safe_value(asdict(self))


def json_safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, list):
        return [json_safe_value(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_safe_value(item) for key, item in value.items()}
    return str(value)


def _path_with_suffix(path: str, suffix: str) -> str:
    original = Path(path)
    return str(original.with_name(f'{original.stem}_{suffix}{original.suffix or ".json"}'))


def round_runtime_output_path(config: WideV2OptimizerConfig, round_index: int) -> str | None:
    if not config.runtime_output_path:
        return None
    return _path_with_suffix(config.runtime_output_path, f'round{round_index:03d}')


def default_summary_output_path(config: WideV2OptimizerConfig) -> str | None:
    if config.summary_output_path:
        return config.summary_output_path
    if config.runtime_output_path:
        return _path_with_suffix(config.runtime_output_path, 'summary')
    return None


def default_leaderboard_output_path(config: WideV2OptimizerConfig) -> str | None:
    if config.leaderboard_output_path:
        return config.leaderboard_output_path
    if config.runtime_output_path:
        return _path_with_suffix(config.runtime_output_path, 'leaderboard')
    return None


def _score_dict(candidate: dict[str, Any]) -> dict[str, Any]:
    return candidate.get('rank_score') or {}


def _float_value(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _candidate_score(candidate_or_entry: dict[str, Any]) -> float:
    score = candidate_or_entry.get('adjusted_score')
    if score is None:
        score = candidate_or_entry.get('promotion_score')
    if score is None:
        score = _score_dict(candidate_or_entry).get('adjusted_score')
    if score is None:
        score = _score_dict(candidate_or_entry).get('promotion_score')
    return _float_value(score, default=float('-inf'))


def _candidate_type(candidate: dict[str, Any]) -> str | None:
    for key in ('v5_candidate_type', 'v4_candidate_type', 'v3_candidate_type', 'v2_candidate_type'):
        if candidate.get(key):
            return str(candidate[key])
    return None


def _candidate_csv_path(candidate: dict[str, Any]) -> str | None:
    if candidate.get('candidate_csv'):
        return str(candidate['candidate_csv'])
    candidate_result = candidate.get('candidate_result') or {}
    csv_path = candidate_result.get('csv_path') or candidate_result.get('output_csv')
    return str(csv_path) if csv_path else None


def build_leaderboard_entries(
    *,
    run_id: str,
    round_index: int,
    round_result: dict[str, Any],
    source_baseline: str,
    source_candidate: str,
    runtime_json_path: str | None = None,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for position, candidate in enumerate(round_result.get('candidates') or [], start=1):
        score = _score_dict(candidate)
        comparison = candidate.get('comparison') or {}
        candidate_summary = comparison.get('candidate_summary') or {}
        promotion_score = _float_value(score.get('promotion_score'))
        adjusted_score = _float_value(score.get('adjusted_score', promotion_score))
        entry = {
            'run_id': run_id,
            'round_index': round_index,
            'candidate_index': int(candidate.get('index') or position),
            'strategy_name': candidate.get('strategy_name'),
            'expression': candidate.get('expression'),
            'source_baseline': source_baseline,
            'source_candidate': source_candidate,
            'candidate_type': _candidate_type(candidate),
            'status': candidate.get('status'),
            'promotion_passed': score.get('promotion_passed') is True,
            'promotion_score': promotion_score,
            'adjusted_score': adjusted_score,
            'score_basis': score.get('score_basis', 'incremental'),
            'trade_count': _float_value(score.get('trade_count', candidate_summary.get('trade_count'))),
            'trade_count_retention': _float_value(
                score.get('trade_count_retention', comparison.get('trade_count_retention'))
            ),
            'date_concentration': _float_value(
                score.get('date_concentration', candidate_summary.get('date_concentration')),
                default=float('inf'),
            ),
            'symbol_concentration': _float_value(
                score.get('symbol_concentration', candidate_summary.get('symbol_concentration')),
                default=float('inf'),
            ),
            'actual_rowset_selected': candidate.get('actual_rowset_selected') is True,
            'selected_as_round_best': candidate.get('selected_as_best') is True,
            'selected_as_global_best': False,
            'runtime_json_path': runtime_json_path,
            'candidate_csv_path': _candidate_csv_path(candidate),
            'failure_phase': candidate.get('phase') if candidate.get('status') != 'ok' else None,
            'failure_message': candidate.get('message') if candidate.get('status') != 'ok' else None,
            'rank': candidate.get('rank'),
            'rank_score': score,
            'retention_penalty': score.get('retention_penalty'),
            'reference_promotion_score': score.get('reference_promotion_score'),
            'incremental_promotion_score': score.get('incremental_promotion_score'),
        }
        entries.append(json_safe_value(entry))
    return entries


def select_global_best_candidate(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    eligible = [entry for entry in entries if entry.get('status') == 'ok']
    if not eligible:
        return None
    return min(
        eligible,
        key=lambda entry: (
            entry.get('promotion_passed') is not True,
            -_candidate_score(entry),
            -_float_value(entry.get('trade_count')),
            -_float_value(entry.get('trade_count_retention')),
            _float_value(entry.get('date_concentration'), default=float('inf')),
            _float_value(entry.get('symbol_concentration'), default=float('inf')),
            int(entry.get('round_index') or 0),
            int(entry.get('candidate_index') or 0),
        ),
    )


def mark_global_best(
    entries: list[dict[str, Any]],
    global_best: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not global_best:
        return [{**entry, 'selected_as_global_best': False} for entry in entries]
    return [
        {
            **entry,
            'selected_as_global_best': (
                entry.get('round_index') == global_best.get('round_index')
                and entry.get('candidate_index') == global_best.get('candidate_index')
                and entry.get('strategy_name') == global_best.get('strategy_name')
            ),
        }
        for entry in entries
    ]


def compute_improvement(
    current: dict[str, Any] | None,
    previous: dict[str, Any] | None,
) -> float | None:
    if not current or not previous:
        return None
    return round(_candidate_score(current) - _candidate_score(previous), 10)
```

- [ ] **Step 4: Run the Task 1 tests**

Run:

```powershell
python -m pytest tests/unit/test_research_optimizer_state.py -q
```

Expected:

```text
6 passed
```

- [ ] **Step 5: Commit Task 1**

Run:

```powershell
git add cli/research_optimizer_state.py tests/unit/test_research_optimizer_state.py
git commit -m "Wide v2 optimizer 상태와 leaderboard 기반을 추가한다" -m "Wide v2 자동 조건식 개선 루프가 여러 라운드 후보를 비교할 수 있도록 config, JSON-safe serialization, leaderboard entry, global best 선택 helper를 추가한다.

Constraint: 기존 research_loop ranking 결과를 재사용해야 한다
Rejected: leaderboard를 research_loop.py 안에 추가 | 파일 크기와 책임이 더 커진다
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_optimizer_state.py -q
Not-tested: 실제 백테스트 실행"
```

---

### Task 2: Multi-Round Optimizer Coordinator

**Files:**
- Create: `tests/unit/test_research_optimizer.py`
- Create: `cli/research_optimizer.py`

- [ ] **Step 1: Write failing coordinator tests**

Create `tests/unit/test_research_optimizer.py` with this content:

```python
import json

from cli.research_optimizer import run_wide_v2_optimizer
from cli.research_optimizer_state import WideV2OptimizerConfig


class DummyController:
    pass


def _round_result(name, expression, score):
    return {
        'status': 'ok',
        'phase': 'candidates_evaluated',
        'best_candidate': {
            'index': 1,
            'strategy_name': name,
            'expression': expression,
            'status': 'ok',
            'selected_as_best': True,
            'actual_rowset_selected': True,
            'rank_score': {
                'promotion_passed': True,
                'promotion_score': score,
                'adjusted_score': score,
                'score_basis': 'reference',
                'trade_count': 100,
                'trade_count_retention': 0.5,
                'date_concentration': 0.2,
                'symbol_concentration': 0.1,
            },
        },
        'candidates': [
            {
                'index': 1,
                'strategy_name': name,
                'expression': expression,
                'status': 'ok',
                'selected_as_best': True,
                'actual_rowset_selected': True,
                'rank_score': {
                    'promotion_passed': True,
                    'promotion_score': score,
                    'adjusted_score': score,
                    'score_basis': 'reference',
                    'trade_count': 100,
                    'trade_count_retention': 0.5,
                    'date_concentration': 0.2,
                    'symbol_concentration': 0.1,
                },
            }
        ],
    }


def test_optimizer_runs_two_rounds_and_promotes_round_best_seed():
    calls = []
    results = [
        _round_result('WideV2__round001__cand001', '66.999 <= 시가총액 < 2_580 and 등락율 > 4.90', 1.0),
        _round_result('WideV2__round002__cand001', '66.999 <= 시가총액 < 2_580 and 등락율 > 5.10', 2.0),
    ]

    def fake_runner(config, controller):
        calls.append(config)
        return results[len(calls) - 1]

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2',
            base_buy_strategy='WideV1Final_B_20260425',
            sell_strategy='ResearchTest_Tick_S_090000_092800_Wide_20260419',
            seed_expression='66.999 <= 시가총액 < 2_580 and 등락율 > 4.83',
            iteration_v2_trade_amount_feature='B_등락율',
            start_date=20250101,
            end_date=20251231,
            candidate_count=2,
            max_rounds=2,
            min_improvement=0.01,
        ),
        DummyController(),
        research_runner=fake_runner,
    )

    assert result['status'] == 'ok'
    assert result['stop_reason'] == 'max_rounds_reached'
    assert len(calls) == 2
    assert calls[0].candidate_name_prefix == 'WideV2__round001'
    assert calls[0].iteration_v2_best_candidate == 'WideV1Final_B_20260425'
    assert calls[0].iteration_v2_best_expression == '66.999 <= 시가총액 < 2_580 and 등락율 > 4.83'
    assert calls[0].iteration_v2_trade_amount_feature == 'B_등락율'
    assert calls[1].candidate_name_prefix == 'WideV2__round002'
    assert calls[1].iteration_v2_best_candidate == 'WideV2__round001__cand001'
    assert calls[1].iteration_v2_best_expression == '66.999 <= 시가총액 < 2_580 and 등락율 > 4.90'
    assert calls[1].iteration_v2_trade_amount_feature == 'B_등락율'
    assert result['final_best_candidate']['strategy_name'] == 'WideV2__round002__cand001'
    assert result['wfo_candidate']['strategy_name'] == 'WideV2__round002__cand001'


def test_optimizer_stops_after_no_improvement_streak():
    calls = []
    results = [
        _round_result('R1__cand001', '66.999 <= 시가총액 < 2_580 and 등락율 > 4.90', 1.0),
        _round_result('R2__cand001', '66.999 <= 시가총액 < 2_580 and 등락율 > 4.70', 1.0),
    ]

    def fake_runner(config, controller):
        calls.append(config)
        return results[len(calls) - 1]

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2NoImprove',
            base_buy_strategy='Base',
            sell_strategy='Sell',
            seed_expression='66.999 <= 시가총액 < 2_580 and 등락율 > 4.83',
            iteration_v2_trade_amount_feature='B_등락율',
            start_date=20250101,
            end_date=20251231,
            candidate_count=2,
            max_rounds=3,
            stop_after_no_improvement=1,
            min_improvement=0.01,
        ),
        DummyController(),
        research_runner=fake_runner,
    )

    assert len(calls) == 2
    assert result['status'] == 'ok'
    assert result['stop_reason'] == 'no_improvement_streak_reached'
    assert result['final_best_candidate']['strategy_name'] == 'R1__cand001'


def test_optimizer_stops_before_next_round_when_seed_expression_is_invalid():
    calls = []

    def fake_runner(config, controller):
        calls.append(config)
        return _round_result('R1__cand001', 'not parseable', 1.0)

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2InvalidSeed',
            base_buy_strategy='Base',
            sell_strategy='Sell',
            seed_expression='66.999 <= 시가총액 < 2_580 and 등락율 > 4.83',
            iteration_v2_trade_amount_feature='B_등락율',
            start_date=20250101,
            end_date=20251231,
            max_rounds=2,
        ),
        DummyController(),
        research_runner=fake_runner,
    )

    assert len(calls) == 1
    assert result['status'] == 'error'
    assert result['stop_reason'] == 'invalid_seed_expression'
    assert result['completed_round_count'] == 1


def test_optimizer_maps_research_runtime_error_and_preserves_completed_rounds():
    calls = []
    results = [
        _round_result('R1__cand001', '66.999 <= 시가총액 < 2_580 and 등락율 > 4.90', 1.0),
        {'status': 'error', 'phase': 'candidate_iteration_runtime_failure', 'message': 'maximum consecutive candidate failures reached'},
    ]

    def fake_runner(config, controller):
        calls.append(config)
        return results[len(calls) - 1]

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2RuntimeFailure',
            base_buy_strategy='Base',
            sell_strategy='Sell',
            seed_expression='66.999 <= 시가총액 < 2_580 and 등락율 > 4.83',
            iteration_v2_trade_amount_feature='B_등락율',
            start_date=20250101,
            end_date=20251231,
            max_rounds=3,
        ),
        DummyController(),
        research_runner=fake_runner,
    )

    assert len(calls) == 2
    assert result['status'] == 'error'
    assert result['stop_reason'] == 'runtime_failure'
    assert result['completed_round_count'] == 1
    assert result['rounds'][1]['failure_message'] == 'maximum consecutive candidate failures reached'


def test_optimizer_writes_summary_and_leaderboard_json(tmp_path):
    runtime_output = tmp_path / 'wide_v2.json'

    def fake_runner(config, controller):
        return _round_result('R1__cand001', '66.999 <= 시가총액 < 2_580 and 등락율 > 4.90', 1.0)

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2RuntimeOutput',
            base_buy_strategy='Base',
            sell_strategy='Sell',
            seed_expression='66.999 <= 시가총액 < 2_580 and 등락율 > 4.83',
            iteration_v2_trade_amount_feature='B_등락율',
            start_date=20250101,
            end_date=20251231,
            max_rounds=1,
            runtime_output_path=str(runtime_output),
        ),
        DummyController(),
        research_runner=fake_runner,
    )

    summary_path = tmp_path / 'wide_v2_summary.json'
    leaderboard_path = tmp_path / 'wide_v2_leaderboard.json'
    assert result['summary_output_path'] == str(summary_path)
    assert result['leaderboard_output_path'] == str(leaderboard_path)
    assert json.loads(summary_path.read_text(encoding='utf-8'))['stop_reason'] == 'max_rounds_reached'
    assert json.loads(leaderboard_path.read_text(encoding='utf-8'))[0]['strategy_name'] == 'R1__cand001'
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_research_optimizer.py -q
```

Expected now:

```text
FAILED
```

The failure should mention `ModuleNotFoundError: No module named 'cli.research_optimizer'`.

- [ ] **Step 3: Create the optimizer coordinator**

Create `cli/research_optimizer.py` with this content:

```python
"""Wide v2 multi-round optimizer coordinator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from cli.research_iteration_v3 import parse_best_expression_conditions
from cli.research_loop import ResearchLoopConfig, run_research_iteration
from cli.research_optimizer_state import (
    WideV2OptimizerConfig,
    build_leaderboard_entries,
    compute_improvement,
    default_leaderboard_output_path,
    default_summary_output_path,
    json_safe_value,
    mark_global_best,
    round_runtime_output_path,
    select_global_best_candidate,
)

ResearchRunner = Callable[[ResearchLoopConfig, Any], dict[str, Any]]


def _write_json(path: str | None, payload: Any) -> str | None:
    if not path:
        return None
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(json_safe_value(payload), ensure_ascii=False, indent=2, default=str),
        encoding='utf-8',
    )
    return str(output_path)


def _seed_from_previous(
    config: WideV2OptimizerConfig,
    previous_best: dict[str, Any] | None,
) -> tuple[str, str]:
    if previous_best:
        return str(previous_best.get('strategy_name') or ''), str(previous_best.get('expression') or '')
    return config.seed_candidate or config.base_buy_strategy, config.seed_expression


def _validate_seed_expression(config: WideV2OptimizerConfig, expression: str) -> bool:
    if not config.iteration_v2_mode:
        return True
    if not expression:
        return False
    if config.iteration_v2_mode == 'best_feature_mix':
        return True
    try:
        parse_best_expression_conditions(
            expression,
            primary_feature=config.iteration_v2_primary_feature,
            trade_amount_feature=config.iteration_v2_trade_amount_feature,
        )
    except ValueError:
        return False
    return True


def build_round_research_config(
    config: WideV2OptimizerConfig,
    *,
    round_index: int,
    previous_best: dict[str, Any] | None,
) -> ResearchLoopConfig:
    seed_candidate, seed_expression = _seed_from_previous(config, previous_best)
    round_name = f'{config.name}__round{round_index:03d}'
    return ResearchLoopConfig(
        name=round_name,
        baseline_csv=config.baseline_csv,
        score_reference_csv=config.score_reference_csv or config.baseline_csv,
        base_buy_strategy=config.base_buy_strategy,
        sell_strategy=config.sell_strategy,
        start_date=config.start_date,
        end_date=config.end_date,
        is_tick=config.is_tick,
        betting=config.betting,
        avg_time=config.avg_time,
        start_time=config.start_time,
        end_time=config.end_time,
        engine_count=config.engine_count,
        top_n=config.top_n,
        min_samples=config.min_samples,
        quantiles=config.quantiles,
        alpha=config.alpha,
        run_candidate=False,
        run_candidates=True,
        candidate_count=config.candidate_count,
        candidate_name_prefix=round_name,
        cleanup_best_candidate=config.cleanup_best_candidate,
        keep_loser_candidates=config.keep_loser_candidates,
        candidate_timeout=config.candidate_timeout,
        keep_failed_candidate=config.keep_failed_candidate,
        runtime_output_path=round_runtime_output_path(config, round_index),
        max_consecutive_candidate_failures=config.max_consecutive_candidate_failures,
        min_estimated_retention=config.min_estimated_retention,
        allow_retention_fallback=config.allow_retention_fallback,
        use_retention_penalty=config.use_retention_penalty,
        candidate_pool_multiplier=config.candidate_pool_multiplier,
        iteration_v2_mode=config.iteration_v2_mode,
        iteration_v2_best_candidate=seed_candidate,
        iteration_v2_best_expression=seed_expression,
        iteration_v2_primary_feature=config.iteration_v2_primary_feature,
        iteration_v2_trade_amount_feature=config.iteration_v2_trade_amount_feature,
        iteration_v2_secondary_features=config.iteration_v2_secondary_features,
        iteration_v2_include_secondary_only=config.iteration_v2_include_secondary_only,
        iteration_v2_max_secondary_only=config.iteration_v2_max_secondary_only,
        iteration_v2_duplicate_retention_tolerance=config.iteration_v2_duplicate_retention_tolerance,
    )


def _failure_stop_reason(round_result: dict[str, Any]) -> str:
    phase = round_result.get('phase')
    if phase in {'insufficient_expressions', 'insufficient_retention_candidates'}:
        return 'insufficient_candidates'
    actual_rowset = round_result.get('actual_rowset_selection') or {}
    if actual_rowset.get('row_set_identity_status') == 'duplicate_only':
        return 'duplicate_rowset_only'
    return 'runtime_failure'


def _wfo_candidate(best: dict[str, Any] | None) -> dict[str, Any] | None:
    if not best:
        return None
    return {
        'strategy_name': best.get('strategy_name'),
        'expression': best.get('expression'),
        'source_round': best.get('round_index'),
        'source_candidate': best.get('strategy_name'),
        'reason_selected': 'global_best_candidate',
        'next_command': 'Use $writing-plans Wide v2 final candidate WFO validation plan before running WFO.',
    }


def run_wide_v2_optimizer(
    config: WideV2OptimizerConfig,
    controller: Any,
    *,
    research_runner: ResearchRunner = run_research_iteration,
) -> dict[str, Any]:
    rounds: list[dict[str, Any]] = []
    leaderboard: list[dict[str, Any]] = []
    previous_best: dict[str, Any] | None = None
    previous_global_best: dict[str, Any] | None = None
    no_improvement_streak = 0
    stop_reason = 'max_rounds_reached'
    status = 'ok'

    for round_index in range(1, config.max_rounds + 1):
        seed_candidate, seed_expression = _seed_from_previous(config, previous_best)
        if not _validate_seed_expression(config, seed_expression):
            status = 'error'
            stop_reason = 'invalid_seed_expression'
            break

        round_config = build_round_research_config(
            config,
            round_index=round_index,
            previous_best=previous_best,
        )
        round_result = research_runner(round_config, controller)
        runtime_path = round_config.runtime_output_path
        round_state = {
            'round_index': round_index,
            'status': round_result.get('status'),
            'phase': round_result.get('phase'),
            'source_candidate': seed_candidate,
            'source_expression': seed_expression,
            'runtime_json_path': runtime_path,
            'round_best_candidate': round_result.get('best_candidate'),
            'failure_message': round_result.get('message'),
        }
        rounds.append(json_safe_value(round_state))

        entries = build_leaderboard_entries(
            run_id=config.run_id,
            round_index=round_index,
            round_result=round_result,
            source_baseline=config.base_buy_strategy,
            source_candidate=seed_candidate,
            runtime_json_path=runtime_path,
        )
        leaderboard.extend(entries)

        if round_result.get('status') != 'ok':
            status = 'error'
            stop_reason = _failure_stop_reason(round_result)
            break

        round_best = round_result.get('best_candidate')
        if not round_best:
            status = 'error'
            stop_reason = 'insufficient_candidates'
            break

        current_global_best = select_global_best_candidate(leaderboard)
        improvement = compute_improvement(current_global_best, previous_global_best)
        if improvement is not None and improvement < config.min_improvement:
            no_improvement_streak += 1
        else:
            no_improvement_streak = 0
        previous_global_best = current_global_best
        previous_best = round_best

        if no_improvement_streak >= config.stop_after_no_improvement:
            stop_reason = 'no_improvement_streak_reached'
            break

    final_best = select_global_best_candidate(leaderboard)
    leaderboard = mark_global_best(leaderboard, final_best)
    if final_best:
        final_best = next(
            entry for entry in leaderboard
            if entry.get('selected_as_global_best') is True
        )

    summary_output_path = default_summary_output_path(config)
    leaderboard_output_path = default_leaderboard_output_path(config)
    result = {
        'status': status,
        'run_id': config.run_id,
        'stop_reason': stop_reason,
        'completed_round_count': sum(1 for item in rounds if item.get('status') == 'ok'),
        'rounds': rounds,
        'leaderboard': leaderboard,
        'final_best_candidate': final_best,
        'wfo_candidate': _wfo_candidate(final_best),
        'summary_output_path': summary_output_path,
        'leaderboard_output_path': leaderboard_output_path,
        'report_path': config.report_path,
        'wfo_was_run': False,
    }
    _write_json(summary_output_path, result)
    _write_json(leaderboard_output_path, leaderboard)
    return json_safe_value(result)
```

- [ ] **Step 4: Run the Task 2 tests**

Run:

```powershell
python -m pytest tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_state.py -q
```

Expected:

```text
11 passed
```

- [ ] **Step 5: Commit Task 2**

Run:

```powershell
git add cli/research_optimizer.py tests/unit/test_research_optimizer.py
git commit -m "Wide v2 다중 라운드 optimizer coordinator를 추가한다" -m "기존 run_research_iteration 경로를 재사용해 round별 ResearchLoopConfig를 만들고, best_candidate를 다음 round seed로 승격하는 Wide v2 coordinator를 추가한다.

Constraint: WFO는 optimizer loop 내부에서 실행하지 않는다
Rejected: 새 백테스트 엔진 구현 | 기존 v5 runtime, ranking, actual row-set 검증을 재사용하는 것이 MVP에 맞다
Confidence: medium
Scope-risk: moderate
Tested: python -m pytest tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_state.py -q
Not-tested: 실제 STOM 백테스트 프로세스"
```

---

### Task 3: Optimizer Markdown Report

**Files:**
- Create: `tests/unit/test_research_optimizer_report.py`
- Create: `cli/research_optimizer_report.py`

- [ ] **Step 1: Write failing report tests**

Create `tests/unit/test_research_optimizer_report.py` with this content:

```python
from cli.research_optimizer_report import render_optimizer_summary_markdown, write_optimizer_report


def _result():
    return {
        'status': 'ok',
        'run_id': 'WideV2Run',
        'stop_reason': 'max_rounds_reached',
        'completed_round_count': 2,
        'rounds': [
            {
                'round_index': 1,
                'status': 'ok',
                'source_candidate': 'WideV1Final_B_20260425',
                'round_best_candidate': {'strategy_name': 'R1__cand001', 'expression': 'A'},
            },
            {
                'round_index': 2,
                'status': 'ok',
                'source_candidate': 'R1__cand001',
                'round_best_candidate': {'strategy_name': 'R2__cand001', 'expression': 'B'},
            },
        ],
        'leaderboard': [
            {
                'round_index': 2,
                'candidate_index': 1,
                'strategy_name': 'R2__cand001',
                'expression': 'B',
                'adjusted_score': 2.0,
                'promotion_passed': True,
                'selected_as_global_best': True,
            }
        ],
        'final_best_candidate': {
            'strategy_name': 'R2__cand001',
            'expression': 'B',
            'adjusted_score': 2.0,
        },
        'wfo_candidate': {
            'strategy_name': 'R2__cand001',
            'expression': 'B',
            'next_command': '$writing-plans Wide v2 final candidate WFO validation plan',
        },
        'wfo_was_run': False,
    }


def test_render_optimizer_summary_markdown_contains_required_sections():
    markdown = render_optimizer_summary_markdown(_result())

    assert '# Wide v2 optimizer summary' in markdown
    assert '## Run configuration' in markdown
    assert '## Round summary' in markdown
    assert '## Global leaderboard' in markdown
    assert '## Final best candidate' in markdown
    assert '## WFO handoff' in markdown
    assert 'WFO was not run inside the optimizer loop.' in markdown
    assert 'The final candidate is a WFO candidate, not a live-trading approval.' in markdown
    assert 'R2__cand001' in markdown


def test_write_optimizer_report_creates_parent_directories(tmp_path):
    report_path = tmp_path / 'nested' / 'wide_v2_summary.md'

    written = write_optimizer_report(_result(), str(report_path))

    assert written == str(report_path)
    assert report_path.read_text(encoding='utf-8').startswith('# Wide v2 optimizer summary')
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_research_optimizer_report.py -q
```

Expected now:

```text
FAILED
```

The failure should mention `ModuleNotFoundError: No module named 'cli.research_optimizer_report'`.

- [ ] **Step 3: Create the report helper**

Create `cli/research_optimizer_report.py` with this content:

```python
"""Markdown report rendering for Wide v2 optimizer runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _value(value: Any) -> str:
    if value is None:
        return ''
    return str(value)


def _round_rows(result: dict[str, Any]) -> list[str]:
    rows = [
        '| round | status | source_candidate | round_best | expression |',
        '| --- | --- | --- | --- | --- |',
    ]
    for item in result.get('rounds') or []:
        best = item.get('round_best_candidate') or {}
        rows.append(
            '| {round_index} | {status} | {source_candidate} | {best_name} | {expression} |'.format(
                round_index=_value(item.get('round_index')),
                status=_value(item.get('status')),
                source_candidate=_value(item.get('source_candidate')),
                best_name=_value(best.get('strategy_name')),
                expression=_value(best.get('expression')).replace('|', '\\|'),
            )
        )
    return rows


def _leaderboard_rows(result: dict[str, Any]) -> list[str]:
    rows = [
        '| round | candidate | strategy | adjusted_score | promotion_passed | global_best |',
        '| --- | --- | --- | --- | --- | --- |',
    ]
    for item in result.get('leaderboard') or []:
        rows.append(
            '| {round_index} | {candidate_index} | {strategy_name} | {adjusted_score} | {promotion_passed} | {global_best} |'.format(
                round_index=_value(item.get('round_index')),
                candidate_index=_value(item.get('candidate_index')),
                strategy_name=_value(item.get('strategy_name')),
                adjusted_score=_value(item.get('adjusted_score')),
                promotion_passed=_value(item.get('promotion_passed')),
                global_best=_value(item.get('selected_as_global_best')),
            )
        )
    return rows


def render_optimizer_summary_markdown(result: dict[str, Any]) -> str:
    final_best = result.get('final_best_candidate') or {}
    wfo_candidate = result.get('wfo_candidate') or {}
    lines = [
        '# Wide v2 optimizer summary',
        '',
        '## Run configuration',
        '',
        f"- run_id={_value(result.get('run_id'))}",
        f"- status={_value(result.get('status'))}",
        f"- stop_reason={_value(result.get('stop_reason'))}",
        f"- completed_round_count={_value(result.get('completed_round_count'))}",
        '',
        '## Round summary',
        '',
        *_round_rows(result),
        '',
        '## Global leaderboard',
        '',
        *_leaderboard_rows(result),
        '',
        '## Final best candidate',
        '',
        f"- strategy_name={_value(final_best.get('strategy_name'))}",
        f"- expression={_value(final_best.get('expression'))}",
        f"- adjusted_score={_value(final_best.get('adjusted_score'))}",
        '',
        '## WFO handoff',
        '',
        'WFO was not run inside the optimizer loop.',
        'The final candidate is a WFO candidate, not a live-trading approval.',
        '',
        f"- strategy_name={_value(wfo_candidate.get('strategy_name'))}",
        f"- expression={_value(wfo_candidate.get('expression'))}",
        f"- next_command={_value(wfo_candidate.get('next_command'))}",
        '',
    ]
    return '\n'.join(lines)


def write_optimizer_report(result: dict[str, Any], report_path: str | None) -> str | None:
    if not report_path:
        return None
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_optimizer_summary_markdown(result), encoding='utf-8')
    return str(path)
```

- [ ] **Step 4: Wire report writing into the coordinator**

In `cli/research_optimizer.py`, add this import:

```python
from cli.research_optimizer_report import write_optimizer_report
```

Then in `run_wide_v2_optimizer()`, after the `result` dict is built and before `return`, replace the final write block with:

```python
    _write_json(summary_output_path, result)
    _write_json(leaderboard_output_path, leaderboard)
    report_path = write_optimizer_report(result, config.report_path)
    result['report_path'] = report_path
    if summary_output_path:
        _write_json(summary_output_path, result)
    return json_safe_value(result)
```

- [ ] **Step 5: Run report and coordinator tests**

Run:

```powershell
python -m pytest tests/unit/test_research_optimizer_report.py tests/unit/test_research_optimizer.py -q
```

Expected:

```text
7 passed
```

- [ ] **Step 6: Commit Task 3**

Run:

```powershell
git add cli/research_optimizer_report.py cli/research_optimizer.py tests/unit/test_research_optimizer_report.py tests/unit/test_research_optimizer.py
git commit -m "Wide v2 optimizer Markdown 보고서를 추가한다" -m "Wide v2 자동 개선 루프의 라운드 요약, global leaderboard, final_best_candidate, WFO handoff를 사람이 검토 가능한 Markdown으로 기록한다.

Constraint: backtest/temp runtime JSON은 기본 commit 대상이 아니다
Rejected: runtime JSON만으로 PR 근거를 남김 | 사용자가 후보 개선 흐름을 읽기 어렵다
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_optimizer_report.py tests/unit/test_research_optimizer.py -q
Not-tested: 실제 장시간 백테스트 실행"
```

---

### Task 4: CLI Integration

**Files:**
- Modify: `tests/unit/test_subcommands.py`
- Modify: `cli/subcommands.py`

- [ ] **Step 1: Add failing parser and handler tests**

Append these tests to `tests/unit/test_subcommands.py` near the existing discovery research tests:

```python
def test_discovery_optimize_wide_v2_parser_accepts_optimizer_options():
    parser = create_subcommand_parser()

    args = parser.parse_args([
        'discovery', 'optimize-wide-v2',
        '--name', 'WideV2AutoLoop_20260427',
        '--base-buy-strategy', 'WideV1Final_B_20260425',
        '--sell', 'ResearchTest_Tick_S_090000_092800_Wide_20260419',
        '--seed-expression', '66.999 <= 시가총액 < 2_580 and 등락율 > 4.83',
        '--start', '20250101',
        '--end', '20251231',
        '--candidate-count', '10',
        '--max-rounds', '3',
        '--min-improvement', '0.01',
        '--stop-after-no-improvement', '2',
        '--iteration-v2-trade-amount-feature', 'B_등락율',
        '--runtime-output', 'backtest/temp/wide_v2_auto_loop.json',
        '--leaderboard-output', 'backtest/temp/wide_v2_auto_loop_leaderboard.json',
        '--report-path', 'docs/research/condition_research/pilot_logs/2026-04-27_wide_v2_auto_loop_summary.md',
    ])

    assert args.command == 'discovery'
    assert args.discovery_action == 'optimize-wide-v2'
    assert args.name == 'WideV2AutoLoop_20260427'
    assert args.seed_expression == '66.999 <= 시가총액 < 2_580 and 등락율 > 4.83'
    assert args.iteration_v2_trade_amount_feature == 'B_등락율'
    assert args.candidate_count == 10
    assert args.max_rounds == 3
    assert args.min_improvement == 0.01
    assert args.stop_after_no_improvement == 2
    assert args.runtime_output_path == 'backtest/temp/wide_v2_auto_loop.json'
    assert args.leaderboard_output_path == 'backtest/temp/wide_v2_auto_loop_leaderboard.json'
    assert args.report_path.endswith('wide_v2_auto_loop_summary.md')


def test_discovery_optimize_wide_v2_handler_calls_optimizer(capsys):
    with patch('cli.research_optimizer.run_wide_v2_optimizer') as mock:
        mock.return_value = {
            'status': 'ok',
            'run_id': 'WideV2AutoLoop_20260427',
            'stop_reason': 'max_rounds_reached',
        }
        exit_code = handle_subcommand([
            'discovery', 'optimize-wide-v2',
            '--name', 'WideV2AutoLoop_20260427',
            '--base-buy-strategy', 'WideV1Final_B_20260425',
            '--sell', 'ResearchTest_Tick_S_090000_092800_Wide_20260419',
            '--seed-expression', '66.999 <= 시가총액 < 2_580 and 등락율 > 4.83',
            '--start', '20250101',
            '--end', '20251231',
            '--iteration-v2-trade-amount-feature', 'B_등락율',
            '--candidate-count', '2',
            '--max-rounds', '2',
        ])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert 'WideV2AutoLoop_20260427' in out
    config = mock.call_args.args[0]
    assert config.name == 'WideV2AutoLoop_20260427'
    assert config.base_buy_strategy == 'WideV1Final_B_20260425'
    assert config.sell_strategy == 'ResearchTest_Tick_S_090000_092800_Wide_20260419'
    assert config.seed_expression == '66.999 <= 시가총액 < 2_580 and 등락율 > 4.83'
    assert config.iteration_v2_trade_amount_feature == 'B_등락율'
    assert config.candidate_count == 2
    assert config.max_rounds == 2
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```powershell
python -m pytest `
  tests/unit/test_subcommands.py::test_discovery_optimize_wide_v2_parser_accepts_optimizer_options `
  tests/unit/test_subcommands.py::test_discovery_optimize_wide_v2_handler_calls_optimizer `
  -q
```

Expected now:

```text
FAILED
```

The parser failure should mention invalid choice or missing `optimize-wide-v2`.

- [ ] **Step 3: Add the CLI parser**

In `cli/subcommands.py`, add this parser block after the existing `discovery research` argument block and before `discovery promote`:

```python
    # discovery optimize-wide-v2
    disc_optimize_v2 = disc_sub.add_parser('optimize-wide-v2', help='run Wide v2 multi-round backtest optimizer')
    disc_optimize_v2.add_argument('--name', required=True, help='optimizer run id')
    disc_optimize_v2.add_argument('--input', '-i', dest='input_file', help='baseline CSV file')
    disc_optimize_v2.add_argument('--score-reference-csv', help='root baseline CSV for cumulative score comparison')
    disc_optimize_v2.add_argument('--base-buy-strategy', required=True, help='existing buy strategy name')
    disc_optimize_v2.add_argument('--sell', required=True, help='existing sell strategy name')
    disc_optimize_v2.add_argument('--seed-candidate', default='', help='initial seed strategy name')
    disc_optimize_v2.add_argument('--seed-expression', default='', help='initial seed expression for v5 candidate generation')
    disc_optimize_v2.add_argument('--start', type=int, required=True, help='start date YYYYMMDD')
    disc_optimize_v2.add_argument('--end', type=int, required=True, help='end date YYYYMMDD')
    disc_optimize_v2.add_argument('--timeframe', choices=['tick', 'min'], default='tick')
    disc_optimize_v2.add_argument('--betting', default='1')
    disc_optimize_v2.add_argument('--avg-time', type=int, default=60)
    disc_optimize_v2.add_argument('--start-time', type=int, default=90000)
    disc_optimize_v2.add_argument('--end-time', type=int, default=152800)
    disc_optimize_v2.add_argument('--engines', type=int, default=4)
    disc_optimize_v2.add_argument('--top-n', type=int, default=1)
    disc_optimize_v2.add_argument('--min-samples', type=int, default=30)
    disc_optimize_v2.add_argument('--quantiles', type=int, default=10)
    disc_optimize_v2.add_argument('--alpha', type=float, default=0.05)
    disc_optimize_v2.add_argument('--candidate-count', type=int, default=10)
    disc_optimize_v2.add_argument('--candidate-timeout', type=int)
    disc_optimize_v2.add_argument('--cleanup-best-candidate', action='store_true', default=False)
    disc_optimize_v2.add_argument('--keep-loser-candidates', action='store_true', default=False)
    disc_optimize_v2.add_argument('--keep-failed-candidate', action='store_true', default=False)
    disc_optimize_v2.add_argument('--min-estimated-retention', type=float, default=0.4)
    disc_optimize_v2.add_argument('--no-retention-fallback', dest='allow_retention_fallback', action='store_false', default=True)
    disc_optimize_v2.add_argument('--no-retention-penalty', dest='use_retention_penalty', action='store_false', default=True)
    disc_optimize_v2.add_argument('--candidate-pool-multiplier', type=int, default=3)
    disc_optimize_v2.add_argument('--iteration-v2-mode', choices=['best_feature_mix', 'best_feature_mix_v3', 'best_feature_mix_v4', 'best_feature_mix_v5'], default='best_feature_mix_v5')
    disc_optimize_v2.add_argument('--iteration-v2-primary-feature', default='B_시가총액')
    disc_optimize_v2.add_argument('--iteration-v2-trade-amount-feature', default='B_당일거래대금')
    disc_optimize_v2.add_argument('--iteration-v2-secondary-features', default='')
    disc_optimize_v2.add_argument('--no-iteration-v2-secondary-only', dest='iteration_v2_include_secondary_only', action='store_false', default=True)
    disc_optimize_v2.add_argument('--iteration-v2-max-secondary-only', type=int, default=1)
    disc_optimize_v2.add_argument('--iteration-v2-duplicate-retention-tolerance', type=float, default=0.02)
    disc_optimize_v2.add_argument('--max-rounds', type=int, default=3)
    disc_optimize_v2.add_argument('--min-improvement', type=float, default=0.01)
    disc_optimize_v2.add_argument('--stop-after-no-improvement', type=int, default=2)
    disc_optimize_v2.add_argument('--max-consecutive-candidate-failures', type=int, default=3)
    disc_optimize_v2.add_argument('--runtime-output', dest='runtime_output_path')
    disc_optimize_v2.add_argument('--leaderboard-output', dest='leaderboard_output_path')
    disc_optimize_v2.add_argument('--summary-output', dest='summary_output_path')
    disc_optimize_v2.add_argument('--report-path')
```

- [ ] **Step 4: Add the CLI handler**

In `_handle_discovery(parsed)` in `cli/subcommands.py`, add this branch after the existing `parsed.discovery_action == 'research'` branch:

```python
    elif parsed.discovery_action == 'optimize-wide-v2':
        from cli.research_optimizer import run_wide_v2_optimizer
        from cli.research_optimizer_state import WideV2OptimizerConfig

        config = WideV2OptimizerConfig(
            name=parsed.name,
            baseline_csv=getattr(parsed, 'input_file', None),
            score_reference_csv=parsed.score_reference_csv,
            base_buy_strategy=parsed.base_buy_strategy,
            sell_strategy=parsed.sell,
            seed_candidate=parsed.seed_candidate,
            seed_expression=parsed.seed_expression,
            start_date=parsed.start,
            end_date=parsed.end,
            is_tick=parsed.timeframe == 'tick',
            betting=parsed.betting,
            avg_time=parsed.avg_time,
            start_time=parsed.start_time,
            end_time=parsed.end_time,
            engine_count=parsed.engines,
            top_n=parsed.top_n,
            min_samples=parsed.min_samples,
            quantiles=parsed.quantiles,
            alpha=parsed.alpha,
            candidate_count=parsed.candidate_count,
            candidate_timeout=parsed.candidate_timeout,
            cleanup_best_candidate=parsed.cleanup_best_candidate,
            keep_loser_candidates=parsed.keep_loser_candidates,
            keep_failed_candidate=parsed.keep_failed_candidate,
            min_estimated_retention=parsed.min_estimated_retention,
            allow_retention_fallback=parsed.allow_retention_fallback,
            use_retention_penalty=parsed.use_retention_penalty,
            candidate_pool_multiplier=parsed.candidate_pool_multiplier,
            iteration_v2_mode=parsed.iteration_v2_mode,
            iteration_v2_primary_feature=parsed.iteration_v2_primary_feature,
            iteration_v2_trade_amount_feature=parsed.iteration_v2_trade_amount_feature,
            iteration_v2_secondary_features=parsed.iteration_v2_secondary_features,
            iteration_v2_include_secondary_only=parsed.iteration_v2_include_secondary_only,
            iteration_v2_max_secondary_only=parsed.iteration_v2_max_secondary_only,
            iteration_v2_duplicate_retention_tolerance=parsed.iteration_v2_duplicate_retention_tolerance,
            max_rounds=parsed.max_rounds,
            min_improvement=parsed.min_improvement,
            stop_after_no_improvement=parsed.stop_after_no_improvement,
            max_consecutive_candidate_failures=parsed.max_consecutive_candidate_failures,
            runtime_output_path=parsed.runtime_output_path,
            leaderboard_output_path=parsed.leaderboard_output_path,
            summary_output_path=parsed.summary_output_path,
            report_path=parsed.report_path,
        )
        result = run_wide_v2_optimizer(config, controller)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0 if result.get('status') == 'ok' else 1
```

- [ ] **Step 5: Run CLI tests**

Run:

```powershell
python -m pytest `
  tests/unit/test_subcommands.py::test_discovery_optimize_wide_v2_parser_accepts_optimizer_options `
  tests/unit/test_subcommands.py::test_discovery_optimize_wide_v2_handler_calls_optimizer `
  -q
```

Expected:

```text
2 passed
```

- [ ] **Step 6: Run optimizer and existing subcommand regression tests**

Run:

```powershell
python -m pytest `
  tests/unit/test_research_optimizer_state.py `
  tests/unit/test_research_optimizer.py `
  tests/unit/test_research_optimizer_report.py `
  tests/unit/test_subcommands.py `
  -q
```

Expected:

```text
passed
```

- [ ] **Step 7: Commit Task 4**

Run:

```powershell
git add cli/subcommands.py tests/unit/test_subcommands.py
git commit -m "Wide v2 optimizer CLI를 discovery에 연결한다" -m "사용자가 조건식 자동 개선 루프를 명확하게 실행할 수 있도록 discovery optimize-wide-v2 action을 추가하고 optimizer config로 연결한다.

Constraint: 기존 discovery research 계약은 유지한다
Rejected: discovery research에 optimizer-mode 옵션만 추가 | Wide v2 실행 의도가 CLI에서 덜 명확하다
Confidence: high
Scope-risk: moderate
Tested: python -m pytest tests/unit/test_research_optimizer_state.py tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_report.py tests/unit/test_subcommands.py -q
Not-tested: 실제 장시간 candidate_count=10 실행"
```

---

### Task 5: PR Report And Smoke Command Documentation

**Files:**
- Create: `docs/pr/2026-04-27_wide_v2_backtest_iteration_auto_improvement_loop_pr.md`

- [ ] **Step 1: Create the Korean PR report**

Create `docs/pr/2026-04-27_wide_v2_backtest_iteration_auto_improvement_loop_pr.md` with this content:

````markdown
# Wide v2 백테스트 반복 기반 조건식 자동 개선루프 구현

## 목적

이번 PR은 Wide v1에서 완성한 단일 라운드 후보 생성/백테스트/ranking 기반을 재사용하여, Wide v2의 다중 라운드 자동 개선 루프를 구현한다.

최종 목표는 다음 흐름을 CLI에서 재현 가능하게 만드는 것이다.

```text
기준 조건식
-> 백테스트
-> 결과 기록
-> 데이터/퀀트 분석
-> 개선 후보 조건식 생성
-> 후보별 백테스트
-> best_candidate 선택
-> best_candidate를 다음 라운드 baseline/seed로 승격
-> 반복
-> 전체 leaderboard 기준 final_best_candidate 선택
-> 최종 후보만 WFO 검증 계획으로 handoff
```

## 포함 범위

- Wide v2 optimizer config/state helper
- 라운드별 leaderboard entry 생성
- global best candidate 선택
- 기존 `run_research_iteration()` 재사용 multi-round coordinator
- stop condition 처리
- optimizer summary/leaderboard JSON 출력
- Markdown summary report 출력
- `discovery optimize-wide-v2` CLI action
- unit test

## 제외 범위

- WFO 실행
- 실거래 또는 paper trading
- `utility/strategy.db` 변경
- `backtest/temp` runtime JSON commit
- `backtest/csv`/`backtest/graph` 결과물 commit
- 대규모 `cli/` 리팩토링

## 주요 설계 판단

Wide v2는 새 백테스트 엔진이 아니다. 이미 검증된 `run_research_iteration()`을 round 단위로 호출하고, optimizer는 다음 책임만 가진다.

```text
1. round config 생성
2. run_research_iteration() 호출
3. round_best_candidate 추출
4. leaderboard 누적
5. global_best_candidate 갱신
6. stop condition 판단
7. WFO handoff 정보 기록
```

WFO는 optimizer loop 안에서 실행하지 않는다. 최종 후보가 정해진 뒤 별도 계획과 검증 PR에서 실행한다.

## 검증

```powershell
python -m pytest tests/unit/test_research_optimizer_state.py tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_report.py tests/unit/test_subcommands.py -q
python -m pytest tests/unit/test_research_runtime_output.py tests/unit/test_research_loop.py tests/unit/test_research_iteration_v5.py tests/unit/test_wide_v1_v5_analysis.py -q
python scripts/verify_nonrelease_sync.py
git diff --check --ignore-cr-at-eol
```

## Smoke 명령

실제 장시간 full run 전에는 candidate 2개, round 2개로 smoke를 먼저 실행한다.

```powershell
python .\stom_backtest.py discovery optimize-wide-v2 `
  --name WideV2Smoke_20260427 `
  --base-buy-strategy WideV1Final_B_20260425 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --seed-expression "66.999 <= 시가총액 < 2_580 and 등락율 > 4.83" `
  --iteration-v2-trade-amount-feature B_등락율 `
  --start 20250101 `
  --end 20251231 `
  --candidate-count 2 `
  --max-rounds 2 `
  --candidate-timeout 900 `
  --runtime-output backtest\temp\wide_v2_smoke_20260427.json `
  --report-path docs\research\condition_research\pilot_logs\2026-04-27_wide_v2_smoke_summary.md
```

## 다음 단계

1. PR merge 후 smoke 실행 계획 작성
2. smoke 실행 결과 확인
3. 문제가 없으면 candidate_count=10, max_rounds=3 full run 계획 작성
4. final_best_candidate가 선택되면 별도 WFO 검증 계획 작성
````

- [ ] **Step 2: Verify runtime artifact references are documented only as exclusions or smoke output**

Run:

```powershell
Select-String -Path docs/pr/2026-04-27_wide_v2_backtest_iteration_auto_improvement_loop_pr.md -Pattern 'backtest/temp|backtest/csv|backtest/graph'
```

Expected:

```text
Matches are allowed only in the excluded-scope section or in the smoke command output paths.
```

- [ ] **Step 3: Commit Task 5**

Run:

```powershell
git add docs/pr/2026-04-27_wide_v2_backtest_iteration_auto_improvement_loop_pr.md
git commit -m "Wide v2 optimizer PR 보고서를 기록한다" -m "Wide v2 백테스트 반복 기반 조건식 자동 개선루프의 목적, 포함 범위, 제외 범위, 검증 명령, smoke 명령을 한국어 PR 보고서로 기록한다.

Constraint: runtime 결과물은 기본 commit 대상이 아니다
Rejected: 코드 변경만으로 PR 작성 | 조건식 연구 루프는 의도와 검증 범위를 문서화해야 추적 가능하다
Confidence: high
Scope-risk: narrow
Tested: Select-String PR report runtime artifact commit target scan
Not-tested: 실제 smoke run"
```

---

### Task 6: Final Verification Before PR

**Files:**
- Verify only

- [ ] **Step 1: Run focused Wide v2 tests**

Run:

```powershell
python -m pytest `
  tests/unit/test_research_optimizer_state.py `
  tests/unit/test_research_optimizer.py `
  tests/unit/test_research_optimizer_report.py `
  tests/unit/test_subcommands.py `
  -q
```

Expected:

```text
passed
```

- [ ] **Step 2: Run research regression tests**

Run:

```powershell
python -m pytest `
  tests/unit/test_research_runtime_output.py `
  tests/unit/test_research_loop.py `
  tests/unit/test_research_iteration_v5.py `
  tests/unit/test_wide_v1_v5_analysis.py `
  -q
```

Expected:

```text
passed
```

- [ ] **Step 3: Run repository checks**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
git diff --check --ignore-cr-at-eol
```

Expected:

```text
No sync violation output from verify_nonrelease_sync.py
No whitespace error output from git diff --check
```

- [ ] **Step 4: Confirm protected runtime paths are not staged or modified by this PR**

Run:

```powershell
git status --short
```

Expected after the task commits:

```text
No staged files from this PR.
No modified files under backtest/temp, backtest/csv, or backtest/graph.
```

Existing untracked `backtest/graph/` may remain visible and must not be staged.

- [ ] **Step 5: Prepare the PR body**

Use the content from:

```text
docs/pr/2026-04-27_wide_v2_backtest_iteration_auto_improvement_loop_pr.md
```

The PR target branch is:

```text
STOM_Version_2U_C
```

Recommended PR title:

```text
Wide v2 백테스트 반복 기반 조건식 자동 개선루프 구현
```

---

## Self-Review

Spec coverage:

- Purpose and MVP scope are covered by Tasks 1-4.
- WideV1Final seed compatibility for `B_등락율` as the second required feature is covered by Task 0.
- Existing `run_research_iteration()` reuse is covered by Task 2.
- Round state, leaderboard, global best, stop conditions, and WFO handoff are covered by Tasks 1-3.
- CLI shape is covered by Task 4.
- Report and curated Markdown output are covered by Tasks 3 and 5.
- WFO exclusion and protected paths are covered by Tasks 3, 5, and 6.

Type consistency:

- `WideV2OptimizerConfig` is defined in Task 1 and used in Tasks 2 and 4.
- `run_wide_v2_optimizer()` is defined in Task 2 and used in Task 4.
- `write_optimizer_report()` is defined in Task 3 and used in Task 3 coordinator wiring.
- CLI argument names map directly to `WideV2OptimizerConfig` field names.

Verification coverage:

- Unit tests isolate state, coordinator, report, and CLI.
- Regression tests protect existing research runtime and v5 behavior.
- Repository checks protect sync and whitespace.
