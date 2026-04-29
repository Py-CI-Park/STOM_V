# Wide v2 CLI Subcommands Research Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split `discovery research` and `discovery optimize-wide-v2` parser/handler wiring out of `cli/subcommands.py` without changing CLI behavior.

**Architecture:** Create `cli/commands/research.py` as the single owner of Wide v2 research command argument registration, payload building, optimizer config building, JSON output, and exit-code handling. Keep `cli/subcommands.py` as the top-level parser/router and delegate only the two research-heavy discovery actions to the new module.

**Tech Stack:** Python, argparse, pytest, STOM CLI modules, PowerShell, Git.

---

## Current Refactoring Flow

This plan is part of the refactoring flow that starts from merge point `e4981a143b9e75c725f48b77b69147245b10f499`.

```text
[completed] 1. Wide v2 closeout and custom inventory
  -> PR #29
  -> merge point e4981a14

[completed] 2. research_loop.py helper responsibility split
  -> PR #30
  -> merge point 4f900fea

[completed] 3. subcommands.py research wiring design
  -> commit 9211a7ce

[current] 4. subcommands.py research wiring implementation plan
  -> this plan

[next] 5. subcommands.py research wiring implementation
  -> create cli/commands/research.py
  -> keep CLI contract unchanged

[later] 6. choose next command-family split, likely WFO or runtime-preflight

[later] 7. compare latest 2U against 2U_C custom diff

[final] 8. resume condition auto-improvement loop development
```

## Scope

In scope:

- Create `cli/commands/__init__.py`.
- Create `cli/commands/research.py`.
- Move `discovery research` parser registration into `add_research_parser()`.
- Move `discovery optimize-wide-v2` parser registration into `add_optimize_wide_v2_parser()`.
- Move `research_strategy_once()` payload building into `build_research_strategy_payload()`.
- Move `WideV2OptimizerConfig` construction into `build_wide_v2_optimizer_config()`.
- Move JSON printing and exit-code handling for the two actions into `handle_research()` and `handle_optimize_wide_v2()`.
- Keep `cli/subcommands.py` as top-level parser/router.
- Add direct unit tests for the new payload/config helper functions.
- Keep existing `tests/unit/test_subcommands.py` behavior passing.

Out of scope:

- Do not split all `discovery` commands.
- Do not move WFO, runtime-preflight, formula, strategy, setting, tune, report, or db commands.
- Do not change CLI option names, defaults, choices, JSON output, or exit codes.
- Do not change condition generation, ranking, optimizer behavior, WFO/OOS behavior, or backtest execution.
- Do not touch `backtest/graph/`, `backtest/temp/`, `backtest/csv/`, or `utility/strategy.db`.

## File Structure

Create:

- `cli/commands/__init__.py`
  - Marks the command wiring package.
  - Contains no runtime imports.

- `cli/commands/research.py`
  - Owns parser registration and handler wiring for:
    - `discovery research`
    - `discovery optimize-wide-v2`
  - Does not import `AIBacktestController` unless handler is called without an injected controller.
  - Imports `WideV2OptimizerConfig` and `run_wide_v2_optimizer` lazily inside the optimizer builder/handler to preserve existing patch paths.

- `tests/unit/test_research_command_wiring.py`
  - Direct tests for `build_research_strategy_payload()`.
  - Direct tests for `build_wide_v2_optimizer_config()`.
  - Direct tests for `handle_research()` and `handle_optimize_wide_v2()` using injected fake controller/patches.

Modify:

- `cli/subcommands.py`
  - Import parser registration helpers in `create_subcommand_parser()`.
  - Replace inline parser blocks with helper calls.
  - Delegate `research` and `optimize-wide-v2` branches in `_handle_discovery()`.

Test:

- `tests/unit/test_research_command_wiring.py`
- `tests/unit/test_subcommands.py`
- `tests/unit/test_research_loop.py`
- `tests/unit/test_research_optimizer.py`
- `tests/unit/test_research_optimizer_report.py`
- `tests/unit/test_research_optimizer_state.py`

---

### Task 1: Baseline Verification

**Files:**
- Read only.

- [ ] **Step 1: Confirm branch and protected untracked data**

Run:

```powershell
git status --short --branch
```

Expected:

```text
## feature/cli-subcommands-refactor-plan
?? backtest/graph/
```

- [ ] **Step 2: Run baseline subcommand tests**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py -q
```

Expected:

```text
All tests pass.
```

- [ ] **Step 3: Run baseline research loop tests**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py -q
```

Expected:

```text
All tests pass.
```

### Task 2: Add Direct Tests for Research Command Wiring

**Files:**
- Create: `tests/unit/test_research_command_wiring.py`
- Test: `tests/unit/test_research_command_wiring.py`

- [ ] **Step 1: Create failing tests for payload/config helper functions**

Use `apply_patch`:

```diff
*** Begin Patch
*** Add File: tests/unit/test_research_command_wiring.py
+"""Tests for discovery research command wiring helpers."""
+
+from __future__ import annotations
+
+from argparse import Namespace
+from unittest.mock import patch
+
+from cli.commands.research import (
+    build_research_strategy_payload,
+    build_wide_v2_optimizer_config,
+    handle_optimize_wide_v2,
+    handle_research,
+)
+
+
+def _research_args(**overrides):
+    values = {
+        'name': 'ResearchRun',
+        'input_file': 'baseline.csv',
+        'score_reference_csv': 'root.csv',
+        'base_buy_strategy': 'BaseBuy',
+        'sell': 'BaseSell',
+        'start': 20250101,
+        'end': 20250131,
+        'timeframe': 'min',
+        'betting': '2',
+        'avg_time': 30,
+        'start_time': 90100,
+        'end_time': 145500,
+        'engines': 2,
+        'top_n': 3,
+        'min_samples': 20,
+        'quantiles': 8,
+        'alpha': 0.1,
+        'run_candidate': False,
+        'run_candidates': True,
+        'candidate_count': 7,
+        'candidate_name_prefix': 'Batch',
+        'cleanup_best_candidate': True,
+        'keep_loser_candidates': True,
+        'min_estimated_retention': 0.55,
+        'allow_retention_fallback': False,
+        'use_retention_penalty': False,
+        'candidate_pool_multiplier': 4,
+        'candidate_start': 20250102,
+        'candidate_end': 20250130,
+        'candidate_timeout': 300,
+        'candidate_plan_only': True,
+        'keep_failed_candidate': True,
+        'runtime_output_path': 'backtest/temp/research.json',
+        'max_consecutive_candidate_failures': 5,
+        'iteration_v2_mode': 'best_feature_mix_v5',
+        'iteration_v2_best_candidate': 'SeedCandidate',
+        'iteration_v2_best_expression': 'B_등락율 > 1',
+        'iteration_v2_primary_feature': 'B_시가총액',
+        'iteration_v2_trade_amount_feature': 'B_등락율',
+        'iteration_v2_secondary_features': 'B_거래대금',
+        'iteration_v2_include_secondary_only': False,
+        'iteration_v2_max_secondary_only': 0,
+        'iteration_v2_duplicate_retention_tolerance': 0.03,
+    }
+    values.update(overrides)
+    return Namespace(**values)
+
+
+def _optimizer_args(**overrides):
+    values = {
+        'name': 'WideV2AutoLoop',
+        'input_file': 'baseline.csv',
+        'score_reference_csv': 'root.csv',
+        'base_buy_strategy': 'WideV1Final',
+        'sell': 'BaseSell',
+        'seed_candidate': 'SeedCandidate',
+        'seed_expression': 'B_등락율 > 1',
+        'start': 20250101,
+        'end': 20251231,
+        'timeframe': 'tick',
+        'betting': '1',
+        'avg_time': 60,
+        'start_time': 90000,
+        'end_time': 152800,
+        'engines': 4,
+        'top_n': 1,
+        'min_samples': 30,
+        'quantiles': 10,
+        'alpha': 0.05,
+        'candidate_count': 10,
+        'candidate_timeout': 1200,
+        'cleanup_best_candidate': False,
+        'keep_loser_candidates': False,
+        'keep_failed_candidate': True,
+        'min_estimated_retention': 0.4,
+        'allow_retention_fallback': True,
+        'use_retention_penalty': True,
+        'candidate_pool_multiplier': 3,
+        'iteration_v2_mode': 'best_feature_mix_v5',
+        'iteration_v2_primary_feature': 'B_시가총액',
+        'iteration_v2_trade_amount_feature': 'B_당일거래대금',
+        'iteration_v2_secondary_features': '',
+        'iteration_v2_include_secondary_only': True,
+        'iteration_v2_max_secondary_only': 1,
+        'iteration_v2_duplicate_retention_tolerance': 0.02,
+        'max_rounds': 3,
+        'min_improvement': 0.01,
+        'stop_after_no_improvement': 2,
+        'max_consecutive_candidate_failures': 3,
+        'runtime_output_path': 'backtest/temp/runtime.json',
+        'leaderboard_output_path': 'backtest/temp/leaderboard.json',
+        'summary_output_path': 'backtest/temp/summary.json',
+        'report_path': 'docs/research/condition_research/pilot_logs/report.md',
+    }
+    values.update(overrides)
+    return Namespace(**values)
+
+
+class _FakeController:
+    def __init__(self, result):
+        self.result = result
+        self.payloads = []
+
+    def research_strategy_once(self, payload):
+        self.payloads.append(payload)
+        return self.result
+
+
+def test_build_research_strategy_payload_preserves_cli_contract():
+    payload = build_research_strategy_payload(_research_args())
+
+    assert payload == {
+        'name': 'ResearchRun',
+        'baseline_csv': 'baseline.csv',
+        'score_reference_csv': 'root.csv',
+        'base_buy_strategy': 'BaseBuy',
+        'sell_strategy': 'BaseSell',
+        'start_date': 20250101,
+        'end_date': 20250131,
+        'is_tick': False,
+        'betting': '2',
+        'avg_time': 30,
+        'start_time': 90100,
+        'end_time': 145500,
+        'engine_count': 2,
+        'top_n': 3,
+        'min_samples': 20,
+        'quantiles': 8,
+        'alpha': 0.1,
+        'run_candidate': False,
+        'run_candidates': True,
+        'candidate_count': 7,
+        'candidate_name_prefix': 'Batch',
+        'cleanup_best_candidate': True,
+        'keep_loser_candidates': True,
+        'min_estimated_retention': 0.55,
+        'allow_retention_fallback': False,
+        'use_retention_penalty': False,
+        'candidate_pool_multiplier': 4,
+        'candidate_start_date': 20250102,
+        'candidate_end_date': 20250130,
+        'candidate_timeout': 300,
+        'candidate_plan_only': True,
+        'keep_failed_candidate': True,
+        'runtime_output_path': 'backtest/temp/research.json',
+        'max_consecutive_candidate_failures': 5,
+        'iteration_v2_mode': 'best_feature_mix_v5',
+        'iteration_v2_best_candidate': 'SeedCandidate',
+        'iteration_v2_best_expression': 'B_등락율 > 1',
+        'iteration_v2_primary_feature': 'B_시가총액',
+        'iteration_v2_trade_amount_feature': 'B_등락율',
+        'iteration_v2_secondary_features': 'B_거래대금',
+        'iteration_v2_include_secondary_only': False,
+        'iteration_v2_max_secondary_only': 0,
+        'iteration_v2_duplicate_retention_tolerance': 0.03,
+    }
+
+
+def test_build_research_strategy_payload_handles_missing_input():
+    payload = build_research_strategy_payload(_research_args(input_file=None, timeframe='tick'))
+
+    assert payload['baseline_csv'] is None
+    assert payload['is_tick'] is True
+
+
+def test_build_wide_v2_optimizer_config_preserves_cli_contract():
+    config = build_wide_v2_optimizer_config(_optimizer_args())
+
+    assert config.name == 'WideV2AutoLoop'
+    assert config.baseline_csv == 'baseline.csv'
+    assert config.score_reference_csv == 'root.csv'
+    assert config.base_buy_strategy == 'WideV1Final'
+    assert config.sell_strategy == 'BaseSell'
+    assert config.seed_candidate == 'SeedCandidate'
+    assert config.seed_expression == 'B_등락율 > 1'
+    assert config.start_date == 20250101
+    assert config.end_date == 20251231
+    assert config.is_tick is True
+    assert config.candidate_count == 10
+    assert config.candidate_timeout == 1200
+    assert config.keep_failed_candidate is True
+    assert config.iteration_v2_mode == 'best_feature_mix_v5'
+    assert config.max_rounds == 3
+    assert config.runtime_output_path == 'backtest/temp/runtime.json'
+    assert config.leaderboard_output_path == 'backtest/temp/leaderboard.json'
+    assert config.summary_output_path == 'backtest/temp/summary.json'
+    assert config.report_path == 'docs/research/condition_research/pilot_logs/report.md'
+
+
+def test_handle_research_prints_json_and_returns_exit_code(capsys):
+    controller = _FakeController({'status': 'ok', 'run_id': 'ResearchRun'})
+
+    exit_code = handle_research(_research_args(), controller)
+
+    assert exit_code == 0
+    assert controller.payloads[0]['name'] == 'ResearchRun'
+    assert 'ResearchRun' in capsys.readouterr().out
+
+
+def test_handle_research_returns_nonzero_for_error(capsys):
+    controller = _FakeController({'status': 'error', 'phase': 'failed'})
+
+    exit_code = handle_research(_research_args(), controller)
+
+    assert exit_code == 1
+    assert 'failed' in capsys.readouterr().out
+
+
+def test_handle_optimize_wide_v2_prints_json_and_returns_exit_code(capsys):
+    with patch('cli.research_optimizer.run_wide_v2_optimizer') as mock:
+        mock.return_value = {'status': 'ok', 'run_id': 'WideV2AutoLoop'}
+
+        exit_code = handle_optimize_wide_v2(_optimizer_args(), _FakeController({'status': 'unused'}))
+
+    assert exit_code == 0
+    config = mock.call_args.args[0]
+    assert config.name == 'WideV2AutoLoop'
+    assert 'WideV2AutoLoop' in capsys.readouterr().out
+*** End Patch
```

- [ ] **Step 2: Run the new tests and confirm they fail**

Run:

```powershell
python -m pytest tests/unit/test_research_command_wiring.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'cli.commands'
```

### Task 3: Create Research Command Wiring Module

**Files:**
- Create: `cli/commands/__init__.py`
- Create: `cli/commands/research.py`
- Test: `tests/unit/test_research_command_wiring.py`

- [ ] **Step 1: Create `cli/commands/__init__.py`**

Use `apply_patch`:

```diff
*** Begin Patch
*** Add File: cli/commands/__init__.py
+"""Focused command wiring helpers for the STOM CLI."""
*** End Patch
```

- [ ] **Step 2: Create `cli/commands/research.py`**

Use `apply_patch`:

```diff
*** Begin Patch
*** Add File: cli/commands/research.py
+"""Discovery research command parser and handler wiring."""
+
+from __future__ import annotations
+
+import json
+from typing import Any
+
+
+ITERATION_V2_MODE_CHOICES = [
+    'best_feature_mix',
+    'best_feature_mix_v3',
+    'best_feature_mix_v4',
+    'best_feature_mix_v5',
+]
+
+
+def add_research_parser(disc_sub):
+    disc_research = disc_sub.add_parser('research', help='run one discovery research iteration')
+    disc_research.add_argument('name', help='strategy name to create')
+    disc_research.add_argument('--input', '-i', dest='input_file', help='baseline CSV file')
+    disc_research.add_argument('--score-reference-csv', help='root baseline CSV for cumulative score comparison')
+    disc_research.add_argument('--base-buy-strategy', required=True, help='existing buy strategy name')
+    disc_research.add_argument('--sell', required=True, help='existing sell strategy name')
+    disc_research.add_argument('--start', type=int, required=True, help='start date YYYYMMDD')
+    disc_research.add_argument('--end', type=int, required=True, help='end date YYYYMMDD')
+    disc_research.add_argument('--timeframe', choices=['tick', 'min'], default='tick')
+    disc_research.add_argument('--betting', default='1')
+    disc_research.add_argument('--avg-time', type=int, default=60)
+    disc_research.add_argument('--start-time', type=int, default=90000)
+    disc_research.add_argument('--end-time', type=int, default=152800)
+    disc_research.add_argument('--engines', type=int, default=4)
+    disc_research.add_argument('--top-n', type=int, default=1)
+    disc_research.add_argument('--min-samples', type=int, default=30)
+    disc_research.add_argument('--quantiles', type=int, default=10)
+    disc_research.add_argument('--alpha', type=float, default=0.05)
+    candidate_mode = disc_research.add_mutually_exclusive_group()
+    candidate_mode.add_argument('--run-candidate', action='store_true', default=False)
+    candidate_mode.add_argument('--run-candidates', action='store_true', default=False)
+    disc_research.add_argument('--candidate-count', type=int, default=5)
+    disc_research.add_argument('--candidate-name-prefix')
+    disc_research.add_argument('--cleanup-best-candidate', action='store_true', default=False)
+    disc_research.add_argument('--keep-loser-candidates', action='store_true', default=False)
+    disc_research.add_argument('--min-estimated-retention', type=float, default=0.4)
+    disc_research.add_argument('--no-retention-fallback', dest='allow_retention_fallback', action='store_false', default=True)
+    disc_research.add_argument('--no-retention-penalty', dest='use_retention_penalty', action='store_false', default=True)
+    disc_research.add_argument('--candidate-pool-multiplier', type=int, default=3)
+    disc_research.add_argument('--candidate-start', type=int)
+    disc_research.add_argument('--candidate-end', type=int)
+    disc_research.add_argument('--candidate-timeout', type=int)
+    disc_research.add_argument('--candidate-plan-only', action='store_true', default=False)
+    disc_research.add_argument('--keep-failed-candidate', action='store_true', default=False)
+    disc_research.add_argument('--runtime-output', dest='runtime_output_path')
+    disc_research.add_argument('--max-consecutive-candidate-failures', type=int, default=3)
+    disc_research.add_argument(
+        '--iteration-v2-mode',
+        choices=ITERATION_V2_MODE_CHOICES,
+        default='',
+    )
+    disc_research.add_argument('--iteration-v2-best-candidate', default='')
+    disc_research.add_argument('--iteration-v2-best-expression', default='')
+    disc_research.add_argument('--iteration-v2-primary-feature', default='B_시가총액')
+    disc_research.add_argument('--iteration-v2-trade-amount-feature', default='B_당일거래대금')
+    disc_research.add_argument('--iteration-v2-secondary-features', default='')
+    disc_research.add_argument(
+        '--no-iteration-v2-secondary-only',
+        dest='iteration_v2_include_secondary_only',
+        action='store_false',
+        default=True,
+    )
+    disc_research.add_argument('--iteration-v2-max-secondary-only', type=int, default=1)
+    disc_research.add_argument('--iteration-v2-duplicate-retention-tolerance', type=float, default=0.02)
+    return disc_research
+
+
+def add_optimize_wide_v2_parser(disc_sub):
+    disc_optimize_v2 = disc_sub.add_parser('optimize-wide-v2', help='run Wide v2 multi-round backtest optimizer')
+    disc_optimize_v2.add_argument('--name', required=True, help='optimizer run id')
+    disc_optimize_v2.add_argument('--input', '-i', dest='input_file', help='baseline CSV file')
+    disc_optimize_v2.add_argument('--score-reference-csv', help='root baseline CSV for cumulative score comparison')
+    disc_optimize_v2.add_argument('--base-buy-strategy', required=True, help='existing buy strategy name')
+    disc_optimize_v2.add_argument('--sell', required=True, help='existing sell strategy name')
+    disc_optimize_v2.add_argument('--seed-candidate', default='', help='initial seed strategy name')
+    disc_optimize_v2.add_argument('--seed-expression', default='', help='initial seed expression for v5 candidate generation')
+    disc_optimize_v2.add_argument('--start', type=int, required=True, help='start date YYYYMMDD')
+    disc_optimize_v2.add_argument('--end', type=int, required=True, help='end date YYYYMMDD')
+    disc_optimize_v2.add_argument('--timeframe', choices=['tick', 'min'], default='tick')
+    disc_optimize_v2.add_argument('--betting', default='1')
+    disc_optimize_v2.add_argument('--avg-time', type=int, default=60)
+    disc_optimize_v2.add_argument('--start-time', type=int, default=90000)
+    disc_optimize_v2.add_argument('--end-time', type=int, default=152800)
+    disc_optimize_v2.add_argument('--engines', type=int, default=4)
+    disc_optimize_v2.add_argument('--top-n', type=int, default=1)
+    disc_optimize_v2.add_argument('--min-samples', type=int, default=30)
+    disc_optimize_v2.add_argument('--quantiles', type=int, default=10)
+    disc_optimize_v2.add_argument('--alpha', type=float, default=0.05)
+    disc_optimize_v2.add_argument('--candidate-count', type=int, default=10)
+    disc_optimize_v2.add_argument('--candidate-timeout', type=int)
+    disc_optimize_v2.add_argument('--cleanup-best-candidate', action='store_true', default=False)
+    disc_optimize_v2.add_argument('--keep-loser-candidates', action='store_true', default=False)
+    disc_optimize_v2.add_argument('--keep-failed-candidate', action='store_true', default=False)
+    disc_optimize_v2.add_argument('--min-estimated-retention', type=float, default=0.4)
+    disc_optimize_v2.add_argument('--no-retention-fallback', dest='allow_retention_fallback', action='store_false', default=True)
+    disc_optimize_v2.add_argument('--no-retention-penalty', dest='use_retention_penalty', action='store_false', default=True)
+    disc_optimize_v2.add_argument('--candidate-pool-multiplier', type=int, default=3)
+    disc_optimize_v2.add_argument(
+        '--iteration-v2-mode',
+        choices=ITERATION_V2_MODE_CHOICES,
+        default='best_feature_mix_v5',
+    )
+    disc_optimize_v2.add_argument('--iteration-v2-primary-feature', default='B_시가총액')
+    disc_optimize_v2.add_argument('--iteration-v2-trade-amount-feature', default='B_당일거래대금')
+    disc_optimize_v2.add_argument('--iteration-v2-secondary-features', default='')
+    disc_optimize_v2.add_argument(
+        '--no-iteration-v2-secondary-only',
+        dest='iteration_v2_include_secondary_only',
+        action='store_false',
+        default=True,
+    )
+    disc_optimize_v2.add_argument('--iteration-v2-max-secondary-only', type=int, default=1)
+    disc_optimize_v2.add_argument('--iteration-v2-duplicate-retention-tolerance', type=float, default=0.02)
+    disc_optimize_v2.add_argument('--max-rounds', type=int, default=3)
+    disc_optimize_v2.add_argument('--min-improvement', type=float, default=0.01)
+    disc_optimize_v2.add_argument('--stop-after-no-improvement', type=int, default=2)
+    disc_optimize_v2.add_argument('--max-consecutive-candidate-failures', type=int, default=3)
+    disc_optimize_v2.add_argument('--runtime-output', dest='runtime_output_path')
+    disc_optimize_v2.add_argument('--leaderboard-output', dest='leaderboard_output_path')
+    disc_optimize_v2.add_argument('--summary-output', dest='summary_output_path')
+    disc_optimize_v2.add_argument('--report-path')
+    return disc_optimize_v2
+
+
+def build_research_strategy_payload(parsed) -> dict[str, Any]:
+    return {
+        'name': parsed.name,
+        'baseline_csv': getattr(parsed, 'input_file', None),
+        'score_reference_csv': parsed.score_reference_csv,
+        'base_buy_strategy': parsed.base_buy_strategy,
+        'sell_strategy': parsed.sell,
+        'start_date': parsed.start,
+        'end_date': parsed.end,
+        'is_tick': parsed.timeframe == 'tick',
+        'betting': parsed.betting,
+        'avg_time': parsed.avg_time,
+        'start_time': parsed.start_time,
+        'end_time': parsed.end_time,
+        'engine_count': parsed.engines,
+        'top_n': parsed.top_n,
+        'min_samples': parsed.min_samples,
+        'quantiles': parsed.quantiles,
+        'alpha': parsed.alpha,
+        'run_candidate': parsed.run_candidate,
+        'run_candidates': parsed.run_candidates,
+        'candidate_count': parsed.candidate_count,
+        'candidate_name_prefix': parsed.candidate_name_prefix,
+        'cleanup_best_candidate': parsed.cleanup_best_candidate,
+        'keep_loser_candidates': parsed.keep_loser_candidates,
+        'min_estimated_retention': parsed.min_estimated_retention,
+        'allow_retention_fallback': parsed.allow_retention_fallback,
+        'use_retention_penalty': parsed.use_retention_penalty,
+        'candidate_pool_multiplier': parsed.candidate_pool_multiplier,
+        'candidate_start_date': parsed.candidate_start,
+        'candidate_end_date': parsed.candidate_end,
+        'candidate_timeout': parsed.candidate_timeout,
+        'candidate_plan_only': parsed.candidate_plan_only,
+        'keep_failed_candidate': parsed.keep_failed_candidate,
+        'runtime_output_path': parsed.runtime_output_path,
+        'max_consecutive_candidate_failures': parsed.max_consecutive_candidate_failures,
+        'iteration_v2_mode': parsed.iteration_v2_mode,
+        'iteration_v2_best_candidate': parsed.iteration_v2_best_candidate,
+        'iteration_v2_best_expression': parsed.iteration_v2_best_expression,
+        'iteration_v2_primary_feature': parsed.iteration_v2_primary_feature,
+        'iteration_v2_trade_amount_feature': parsed.iteration_v2_trade_amount_feature,
+        'iteration_v2_secondary_features': parsed.iteration_v2_secondary_features,
+        'iteration_v2_include_secondary_only': parsed.iteration_v2_include_secondary_only,
+        'iteration_v2_max_secondary_only': parsed.iteration_v2_max_secondary_only,
+        'iteration_v2_duplicate_retention_tolerance': parsed.iteration_v2_duplicate_retention_tolerance,
+    }
+
+
+def build_wide_v2_optimizer_config(parsed):
+    from cli.research_optimizer_state import WideV2OptimizerConfig
+
+    return WideV2OptimizerConfig(
+        name=parsed.name,
+        baseline_csv=getattr(parsed, 'input_file', None),
+        score_reference_csv=parsed.score_reference_csv,
+        base_buy_strategy=parsed.base_buy_strategy,
+        sell_strategy=parsed.sell,
+        seed_candidate=parsed.seed_candidate,
+        seed_expression=parsed.seed_expression,
+        start_date=parsed.start,
+        end_date=parsed.end,
+        is_tick=parsed.timeframe == 'tick',
+        betting=parsed.betting,
+        avg_time=parsed.avg_time,
+        start_time=parsed.start_time,
+        end_time=parsed.end_time,
+        engine_count=parsed.engines,
+        top_n=parsed.top_n,
+        min_samples=parsed.min_samples,
+        quantiles=parsed.quantiles,
+        alpha=parsed.alpha,
+        candidate_count=parsed.candidate_count,
+        candidate_timeout=parsed.candidate_timeout,
+        cleanup_best_candidate=parsed.cleanup_best_candidate,
+        keep_loser_candidates=parsed.keep_loser_candidates,
+        keep_failed_candidate=parsed.keep_failed_candidate,
+        min_estimated_retention=parsed.min_estimated_retention,
+        allow_retention_fallback=parsed.allow_retention_fallback,
+        use_retention_penalty=parsed.use_retention_penalty,
+        candidate_pool_multiplier=parsed.candidate_pool_multiplier,
+        iteration_v2_mode=parsed.iteration_v2_mode,
+        iteration_v2_primary_feature=parsed.iteration_v2_primary_feature,
+        iteration_v2_trade_amount_feature=parsed.iteration_v2_trade_amount_feature,
+        iteration_v2_secondary_features=parsed.iteration_v2_secondary_features,
+        iteration_v2_include_secondary_only=parsed.iteration_v2_include_secondary_only,
+        iteration_v2_max_secondary_only=parsed.iteration_v2_max_secondary_only,
+        iteration_v2_duplicate_retention_tolerance=parsed.iteration_v2_duplicate_retention_tolerance,
+        max_rounds=parsed.max_rounds,
+        min_improvement=parsed.min_improvement,
+        stop_after_no_improvement=parsed.stop_after_no_improvement,
+        max_consecutive_candidate_failures=parsed.max_consecutive_candidate_failures,
+        runtime_output_path=parsed.runtime_output_path,
+        leaderboard_output_path=parsed.leaderboard_output_path,
+        summary_output_path=parsed.summary_output_path,
+        report_path=parsed.report_path,
+    )
+
+
+def _controller_or_default(controller):
+    if controller is not None:
+        return controller
+    from cli.ai_controller import AIBacktestController
+
+    return AIBacktestController()
+
+
+def handle_research(parsed, controller=None) -> int:
+    controller = _controller_or_default(controller)
+    result = controller.research_strategy_once(build_research_strategy_payload(parsed))
+    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
+    return 0 if result.get('status') == 'ok' else 1
+
+
+def handle_optimize_wide_v2(parsed, controller=None) -> int:
+    from cli.research_optimizer import run_wide_v2_optimizer
+
+    controller = _controller_or_default(controller)
+    result = run_wide_v2_optimizer(build_wide_v2_optimizer_config(parsed), controller)
+    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
+    return 0 if result.get('status') == 'ok' else 1
+*** End Patch
```

- [ ] **Step 3: Run direct wiring tests**

Run:

```powershell
python -m pytest tests/unit/test_research_command_wiring.py -q
```

Expected:

```text
All tests pass.
```

### Task 4: Delegate Parser Registration from `cli/subcommands.py`

**Files:**
- Modify: `cli/subcommands.py`
- Test: `tests/unit/test_subcommands.py`

- [ ] **Step 1: Import parser registration helpers inside `create_subcommand_parser()`**

Use `apply_patch` near the `disc_sub = disc_parser.add_subparsers(dest='discovery_action')` line:

```diff
*** Begin Patch
*** Update File: cli/subcommands.py
@@
     disc_parser = sub.add_parser('discovery', help='자동 조건식 탐색')
     disc_sub = disc_parser.add_subparsers(dest='discovery_action')
+    from cli.commands.research import add_optimize_wide_v2_parser, add_research_parser
*** End Patch
```

- [ ] **Step 2: Remove inline `discovery research` and `optimize-wide-v2` parser blocks**

Use `apply_patch` to replace the full block from `# discovery research` through `disc_optimize_v2.add_argument('--report-path')` with helper calls:

```diff
*** Begin Patch
*** Update File: cli/subcommands.py
@@
-    # discovery research
-    disc_research = disc_sub.add_parser('research', help='run one discovery research iteration')
-    disc_research.add_argument('name', help='strategy name to create')
-    disc_research.add_argument('--input', '-i', dest='input_file', help='baseline CSV file')
-    disc_research.add_argument('--score-reference-csv', help='root baseline CSV for cumulative score comparison')
-    disc_research.add_argument('--base-buy-strategy', required=True, help='existing buy strategy name')
-    disc_research.add_argument('--sell', required=True, help='existing sell strategy name')
-    disc_research.add_argument('--start', type=int, required=True, help='start date YYYYMMDD')
-    disc_research.add_argument('--end', type=int, required=True, help='end date YYYYMMDD')
-    disc_research.add_argument('--timeframe', choices=['tick', 'min'], default='tick')
-    disc_research.add_argument('--betting', default='1')
-    disc_research.add_argument('--avg-time', type=int, default=60)
-    disc_research.add_argument('--start-time', type=int, default=90000)
-    disc_research.add_argument('--end-time', type=int, default=152800)
-    disc_research.add_argument('--engines', type=int, default=4)
-    disc_research.add_argument('--top-n', type=int, default=1)
-    disc_research.add_argument('--min-samples', type=int, default=30)
-    disc_research.add_argument('--quantiles', type=int, default=10)
-    disc_research.add_argument('--alpha', type=float, default=0.05)
-    candidate_mode = disc_research.add_mutually_exclusive_group()
-    candidate_mode.add_argument('--run-candidate', action='store_true', default=False)
-    candidate_mode.add_argument('--run-candidates', action='store_true', default=False)
-    disc_research.add_argument('--candidate-count', type=int, default=5)
-    disc_research.add_argument('--candidate-name-prefix')
-    disc_research.add_argument('--cleanup-best-candidate', action='store_true', default=False)
-    disc_research.add_argument('--keep-loser-candidates', action='store_true', default=False)
-    disc_research.add_argument('--min-estimated-retention', type=float, default=0.4)
-    disc_research.add_argument('--no-retention-fallback', dest='allow_retention_fallback', action='store_false', default=True)
-    disc_research.add_argument('--no-retention-penalty', dest='use_retention_penalty', action='store_false', default=True)
-    disc_research.add_argument('--candidate-pool-multiplier', type=int, default=3)
-    disc_research.add_argument('--candidate-start', type=int)
-    disc_research.add_argument('--candidate-end', type=int)
-    disc_research.add_argument('--candidate-timeout', type=int)
-    disc_research.add_argument('--candidate-plan-only', action='store_true', default=False)
-    disc_research.add_argument('--keep-failed-candidate', action='store_true', default=False)
-    disc_research.add_argument('--runtime-output', dest='runtime_output_path')
-    disc_research.add_argument('--max-consecutive-candidate-failures', type=int, default=3)
-    disc_research.add_argument(
-        '--iteration-v2-mode',
-        choices=['best_feature_mix', 'best_feature_mix_v3', 'best_feature_mix_v4', 'best_feature_mix_v5'],
-        default='',
-    )
-    disc_research.add_argument('--iteration-v2-best-candidate', default='')
-    disc_research.add_argument('--iteration-v2-best-expression', default='')
-    disc_research.add_argument('--iteration-v2-primary-feature', default='B_시가총액')
-    disc_research.add_argument('--iteration-v2-trade-amount-feature', default='B_당일거래대금')
-    disc_research.add_argument('--iteration-v2-secondary-features', default='')
-    disc_research.add_argument(
-        '--no-iteration-v2-secondary-only',
-        dest='iteration_v2_include_secondary_only',
-        action='store_false',
-        default=True,
-    )
-    disc_research.add_argument('--iteration-v2-max-secondary-only', type=int, default=1)
-    disc_research.add_argument('--iteration-v2-duplicate-retention-tolerance', type=float, default=0.02)
-
-    # discovery optimize-wide-v2
-    disc_optimize_v2 = disc_sub.add_parser('optimize-wide-v2', help='run Wide v2 multi-round backtest optimizer')
-    disc_optimize_v2.add_argument('--name', required=True, help='optimizer run id')
-    disc_optimize_v2.add_argument('--input', '-i', dest='input_file', help='baseline CSV file')
-    disc_optimize_v2.add_argument('--score-reference-csv', help='root baseline CSV for cumulative score comparison')
-    disc_optimize_v2.add_argument('--base-buy-strategy', required=True, help='existing buy strategy name')
-    disc_optimize_v2.add_argument('--sell', required=True, help='existing sell strategy name')
-    disc_optimize_v2.add_argument('--seed-candidate', default='', help='initial seed strategy name')
-    disc_optimize_v2.add_argument('--seed-expression', default='', help='initial seed expression for v5 candidate generation')
-    disc_optimize_v2.add_argument('--start', type=int, required=True, help='start date YYYYMMDD')
-    disc_optimize_v2.add_argument('--end', type=int, required=True, help='end date YYYYMMDD')
-    disc_optimize_v2.add_argument('--timeframe', choices=['tick', 'min'], default='tick')
-    disc_optimize_v2.add_argument('--betting', default='1')
-    disc_optimize_v2.add_argument('--avg-time', type=int, default=60)
-    disc_optimize_v2.add_argument('--start-time', type=int, default=90000)
-    disc_optimize_v2.add_argument('--end-time', type=int, default=152800)
-    disc_optimize_v2.add_argument('--engines', type=int, default=4)
-    disc_optimize_v2.add_argument('--top-n', type=int, default=1)
-    disc_optimize_v2.add_argument('--min-samples', type=int, default=30)
-    disc_optimize_v2.add_argument('--quantiles', type=int, default=10)
-    disc_optimize_v2.add_argument('--alpha', type=float, default=0.05)
-    disc_optimize_v2.add_argument('--candidate-count', type=int, default=10)
-    disc_optimize_v2.add_argument('--candidate-timeout', type=int)
-    disc_optimize_v2.add_argument('--cleanup-best-candidate', action='store_true', default=False)
-    disc_optimize_v2.add_argument('--keep-loser-candidates', action='store_true', default=False)
-    disc_optimize_v2.add_argument('--keep-failed-candidate', action='store_true', default=False)
-    disc_optimize_v2.add_argument('--min-estimated-retention', type=float, default=0.4)
-    disc_optimize_v2.add_argument('--no-retention-fallback', dest='allow_retention_fallback', action='store_false', default=True)
-    disc_optimize_v2.add_argument('--no-retention-penalty', dest='use_retention_penalty', action='store_false', default=True)
-    disc_optimize_v2.add_argument('--candidate-pool-multiplier', type=int, default=3)
-    disc_optimize_v2.add_argument(
-        '--iteration-v2-mode',
-        choices=['best_feature_mix', 'best_feature_mix_v3', 'best_feature_mix_v4', 'best_feature_mix_v5'],
-        default='best_feature_mix_v5',
-    )
-    disc_optimize_v2.add_argument('--iteration-v2-primary-feature', default='B_시가총액')
-    disc_optimize_v2.add_argument('--iteration-v2-trade-amount-feature', default='B_당일거래대금')
-    disc_optimize_v2.add_argument('--iteration-v2-secondary-features', default='')
-    disc_optimize_v2.add_argument(
-        '--no-iteration-v2-secondary-only',
-        dest='iteration_v2_include_secondary_only',
-        action='store_false',
-        default=True,
-    )
-    disc_optimize_v2.add_argument('--iteration-v2-max-secondary-only', type=int, default=1)
-    disc_optimize_v2.add_argument('--iteration-v2-duplicate-retention-tolerance', type=float, default=0.02)
-    disc_optimize_v2.add_argument('--max-rounds', type=int, default=3)
-    disc_optimize_v2.add_argument('--min-improvement', type=float, default=0.01)
-    disc_optimize_v2.add_argument('--stop-after-no-improvement', type=int, default=2)
-    disc_optimize_v2.add_argument('--max-consecutive-candidate-failures', type=int, default=3)
-    disc_optimize_v2.add_argument('--runtime-output', dest='runtime_output_path')
-    disc_optimize_v2.add_argument('--leaderboard-output', dest='leaderboard_output_path')
-    disc_optimize_v2.add_argument('--summary-output', dest='summary_output_path')
-    disc_optimize_v2.add_argument('--report-path')
+    add_research_parser(disc_sub)
+    add_optimize_wide_v2_parser(disc_sub)
*** End Patch
```

- [ ] **Step 3: Run parser contract tests**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py::test_discovery_research_parser_accepts_existing_strategy_inputs tests/unit/test_subcommands.py::test_discovery_optimize_wide_v2_parser_accepts_optimizer_options -q
```

Expected:

```text
2 passed
```

### Task 5: Delegate Research Handlers from `cli/subcommands.py`

**Files:**
- Modify: `cli/subcommands.py`
- Test: `tests/unit/test_subcommands.py`

- [ ] **Step 1: Replace inline `research` handler branch**

Use `apply_patch` to replace the current `elif parsed.discovery_action == 'research':` branch body:

```diff
*** Begin Patch
*** Update File: cli/subcommands.py
@@
     elif parsed.discovery_action == 'research':
-        result = controller.research_strategy_once({
-            'name': parsed.name,
-            'baseline_csv': getattr(parsed, 'input_file', None),
-            'score_reference_csv': parsed.score_reference_csv,
-            'base_buy_strategy': parsed.base_buy_strategy,
-            'sell_strategy': parsed.sell,
-            'start_date': parsed.start,
-            'end_date': parsed.end,
-            'is_tick': parsed.timeframe == 'tick',
-            'betting': parsed.betting,
-            'avg_time': parsed.avg_time,
-            'start_time': parsed.start_time,
-            'end_time': parsed.end_time,
-            'engine_count': parsed.engines,
-            'top_n': parsed.top_n,
-            'min_samples': parsed.min_samples,
-            'quantiles': parsed.quantiles,
-            'alpha': parsed.alpha,
-            'run_candidate': parsed.run_candidate,
-            'run_candidates': parsed.run_candidates,
-            'candidate_count': parsed.candidate_count,
-            'candidate_name_prefix': parsed.candidate_name_prefix,
-            'cleanup_best_candidate': parsed.cleanup_best_candidate,
-            'keep_loser_candidates': parsed.keep_loser_candidates,
-            'min_estimated_retention': parsed.min_estimated_retention,
-            'allow_retention_fallback': parsed.allow_retention_fallback,
-            'use_retention_penalty': parsed.use_retention_penalty,
-            'candidate_pool_multiplier': parsed.candidate_pool_multiplier,
-            'candidate_start_date': parsed.candidate_start,
-            'candidate_end_date': parsed.candidate_end,
-            'candidate_timeout': parsed.candidate_timeout,
-            'candidate_plan_only': parsed.candidate_plan_only,
-            'keep_failed_candidate': parsed.keep_failed_candidate,
-            'runtime_output_path': parsed.runtime_output_path,
-            'max_consecutive_candidate_failures': parsed.max_consecutive_candidate_failures,
-            'iteration_v2_mode': parsed.iteration_v2_mode,
-            'iteration_v2_best_candidate': parsed.iteration_v2_best_candidate,
-            'iteration_v2_best_expression': parsed.iteration_v2_best_expression,
-            'iteration_v2_primary_feature': parsed.iteration_v2_primary_feature,
-            'iteration_v2_trade_amount_feature': parsed.iteration_v2_trade_amount_feature,
-            'iteration_v2_secondary_features': parsed.iteration_v2_secondary_features,
-            'iteration_v2_include_secondary_only': parsed.iteration_v2_include_secondary_only,
-            'iteration_v2_max_secondary_only': parsed.iteration_v2_max_secondary_only,
-            'iteration_v2_duplicate_retention_tolerance': parsed.iteration_v2_duplicate_retention_tolerance,
-        })
-        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
-        return 0 if result.get('status') == 'ok' else 1
+        from cli.commands.research import handle_research
+        return handle_research(parsed, controller)
*** End Patch
```

- [ ] **Step 2: Replace inline `optimize-wide-v2` handler branch**

Use `apply_patch` to replace the current `elif parsed.discovery_action == 'optimize-wide-v2':` branch body:

```diff
*** Begin Patch
*** Update File: cli/subcommands.py
@@
     elif parsed.discovery_action == 'optimize-wide-v2':
-        from cli.research_optimizer import run_wide_v2_optimizer
-        from cli.research_optimizer_state import WideV2OptimizerConfig
-
-        config = WideV2OptimizerConfig(
-            name=parsed.name,
-            baseline_csv=getattr(parsed, 'input_file', None),
-            score_reference_csv=parsed.score_reference_csv,
-            base_buy_strategy=parsed.base_buy_strategy,
-            sell_strategy=parsed.sell,
-            seed_candidate=parsed.seed_candidate,
-            seed_expression=parsed.seed_expression,
-            start_date=parsed.start,
-            end_date=parsed.end,
-            is_tick=parsed.timeframe == 'tick',
-            betting=parsed.betting,
-            avg_time=parsed.avg_time,
-            start_time=parsed.start_time,
-            end_time=parsed.end_time,
-            engine_count=parsed.engines,
-            top_n=parsed.top_n,
-            min_samples=parsed.min_samples,
-            quantiles=parsed.quantiles,
-            alpha=parsed.alpha,
-            candidate_count=parsed.candidate_count,
-            candidate_timeout=parsed.candidate_timeout,
-            cleanup_best_candidate=parsed.cleanup_best_candidate,
-            keep_loser_candidates=parsed.keep_loser_candidates,
-            keep_failed_candidate=parsed.keep_failed_candidate,
-            min_estimated_retention=parsed.min_estimated_retention,
-            allow_retention_fallback=parsed.allow_retention_fallback,
-            use_retention_penalty=parsed.use_retention_penalty,
-            candidate_pool_multiplier=parsed.candidate_pool_multiplier,
-            iteration_v2_mode=parsed.iteration_v2_mode,
-            iteration_v2_primary_feature=parsed.iteration_v2_primary_feature,
-            iteration_v2_trade_amount_feature=parsed.iteration_v2_trade_amount_feature,
-            iteration_v2_secondary_features=parsed.iteration_v2_secondary_features,
-            iteration_v2_include_secondary_only=parsed.iteration_v2_include_secondary_only,
-            iteration_v2_max_secondary_only=parsed.iteration_v2_max_secondary_only,
-            iteration_v2_duplicate_retention_tolerance=parsed.iteration_v2_duplicate_retention_tolerance,
-            max_rounds=parsed.max_rounds,
-            min_improvement=parsed.min_improvement,
-            stop_after_no_improvement=parsed.stop_after_no_improvement,
-            max_consecutive_candidate_failures=parsed.max_consecutive_candidate_failures,
-            runtime_output_path=parsed.runtime_output_path,
-            leaderboard_output_path=parsed.leaderboard_output_path,
-            summary_output_path=parsed.summary_output_path,
-            report_path=parsed.report_path,
-        )
-        result = run_wide_v2_optimizer(config, controller)
-        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
-        return 0 if result.get('status') == 'ok' else 1
+        from cli.commands.research import handle_optimize_wide_v2
+        return handle_optimize_wide_v2(parsed, controller)
*** End Patch
```

- [ ] **Step 3: Run handler contract tests**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py::test_discovery_research_handler_calls_controller tests/unit/test_subcommands.py::test_discovery_optimize_wide_v2_handler_calls_optimizer tests/unit/test_subcommands.py::test_discovery_research_handler_returns_nonzero_on_error_status -q
```

Expected:

```text
3 passed
```

### Task 6: Focused Regression Verification

**Files:**
- Read only.

- [ ] **Step 1: Run direct wiring tests**

Run:

```powershell
python -m pytest tests/unit/test_research_command_wiring.py -q
```

Expected:

```text
All tests pass.
```

- [ ] **Step 2: Run all subcommand tests**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py -q
```

Expected:

```text
All tests pass.
```

- [ ] **Step 3: Run research loop tests**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py -q
```

Expected:

```text
All tests pass.
```

- [ ] **Step 4: Run optimizer tests**

Run:

```powershell
python -m pytest tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_report.py tests/unit/test_research_optimizer_state.py -q
```

Expected:

```text
All tests pass.
```

- [ ] **Step 5: Run compile and diff checks**

Run:

```powershell
python -m compileall -q cli
git diff --check --ignore-cr-at-eol HEAD
```

Expected:

```text
Both commands exit 0.
```

### Task 7: Write Korean PR Report

**Files:**
- Create: `docs/pr/2026-04-29_wide_v2_cli_subcommands_research_wiring_refactor_pr.md`

- [ ] **Step 1: Create PR report**

Use `apply_patch`:

```diff
*** Begin Patch
*** Add File: docs/pr/2026-04-29_wide_v2_cli_subcommands_research_wiring_refactor_pr.md
+# Wide v2 CLI subcommands research 명령 wiring 리팩터링
+
+## 목적
+
+이번 PR은 `cli/subcommands.py`에서 Wide v2 조건식 개선에 직접 연결된 `discovery research`와 `discovery optimize-wide-v2` 명령 wiring을 분리하는 동작 보존 리팩터링입니다.
+
+최종 목표는 조건식 자동 개선 루프를 다시 개발하기 전에 CLI 커스텀 코드를 작게 나누고, 이후 2U 정규 업데이트를 cherry-pick 방식으로 받을 때 충돌 범위를 줄이는 것입니다.
+
+## 전체 리팩터링 플로우
+
+```text
+e4981a14: Wide v2 개발 정리와 CLI 리팩터링 준비
+-> PR #30: research_loop.py helper 책임 분리
+-> 이번 PR: subcommands.py research 명령 wiring 분리
+-> 다음 단계: WFO/runtime-preflight 등 남은 command family 분리 필요성 판단
+-> 업스트림 준비: 2U 최신 코드와 2U_C 커스텀 diff 재검토
+-> 최종 목표: 조건식 자동 개선 루프 후속 개발 재개
+```
+
+## 이번 PR에서 한 일
+
+- `cli/commands/__init__.py` 추가
+- `cli/commands/research.py` 추가
+- `discovery research` parser 등록을 새 모듈로 이동
+- `discovery optimize-wide-v2` parser 등록을 새 모듈로 이동
+- `research_strategy_once()` payload 변환을 `build_research_strategy_payload()`로 분리
+- `WideV2OptimizerConfig` 변환을 `build_wide_v2_optimizer_config()`로 분리
+- `cli/subcommands.py`는 top-level parser/router 역할만 유지
+- 직접 unit test로 새 wiring helper contract 고정
+
+## 유지한 동작
+
+- CLI 명령 이름 유지: `discovery research`
+- CLI 명령 이름 유지: `discovery optimize-wide-v2`
+- 옵션 이름, 기본값, choices 유지
+- JSON 출력 포맷 유지
+- 성공 exit code `0`, 실패 exit code `1` 유지
+- 기존 `tests/unit/test_subcommands.py` contract 유지
+
+## 하지 않은 일
+
+- discovery command family 전체 분리
+- WFO/runtime-preflight/formula/strategy/db 명령 분리
+- 조건식 생성 알고리즘 변경
+- 수익률 목적함수 추가
+- full backtest 또는 WFO/OOS 재실행
+- `backtest/graph/`, `backtest/temp/`, `backtest/csv/`, `utility/strategy.db` 변경
+
+## 검증
+
+```powershell
+python -m pytest tests/unit/test_research_command_wiring.py -q
+python -m pytest tests/unit/test_subcommands.py -q
+python -m pytest tests/unit/test_research_loop.py -q
+python -m pytest tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_report.py tests/unit/test_research_optimizer_state.py -q
+python -m compileall -q cli
+git diff --check --ignore-cr-at-eol HEAD
+```
+
+## 현재 단계와 남은 단계
+
+```text
+[완료] Wide v2 closeout
+[완료] research_loop.py 1차 분리
+[완료] subcommands.py research wiring 설계
+[이번 PR] subcommands.py research wiring 구현
+[다음] 남은 command family 분리 필요성 판단
+[후속] 2U 최신 코드 대비 커스텀 diff 재검토
+[최종] 조건식 자동 개선 루프 후속 개발 재개
+```
+
+## Merge 후 다음 추천 명령
+
+```text
+$brainstorming Wide v2 CLI 남은 command family 리팩터링 필요성 및 업스트림 업데이트 준비 순서 검토
+```
*** End Patch
```

### Task 8: Commit Implementation

**Files:**
- Stage only intended files.

- [ ] **Step 1: Confirm status**

Run:

```powershell
git status --short --branch
```

Expected changed/untracked paths:

```text
 M cli/subcommands.py
?? cli/commands/
?? tests/unit/test_research_command_wiring.py
?? docs/pr/2026-04-29_wide_v2_cli_subcommands_research_wiring_refactor_pr.md
?? backtest/graph/
```

- [ ] **Step 2: Stage explicit files**

Run:

```powershell
git add cli/subcommands.py
git add cli/commands/__init__.py
git add cli/commands/research.py
git add tests/unit/test_research_command_wiring.py
git add docs/pr/2026-04-29_wide_v2_cli_subcommands_research_wiring_refactor_pr.md
```

- [ ] **Step 3: Confirm staged diff**

Run:

```powershell
git diff --cached --stat
git diff --cached --check --ignore-cr-at-eol
```

Expected:

```text
Only intended files are staged.
Diff check exits 0.
```

- [ ] **Step 4: Commit with Korean Lore message**

Run:

```powershell
git commit -m "Wide v2 research 명령 wiring 충돌 면적을 줄인다" -m "조건식 자동 개선 후속 개발과 2U 업스트림 업데이트 준비를 위해 discovery research와 optimize-wide-v2 명령 wiring을 subcommands.py에서 분리했다. CLI 옵션과 출력 contract는 유지하고 payload/config 변환을 cli/commands/research.py로 모아 이후 research 옵션 변경 위치를 좁힌다." -m "Constraint: STOM_Version_2U_C는 업스트림 변경을 cherry-pick으로 받아야 하므로 subcommands.py 충돌 면적을 줄여야 한다" -m "Rejected: discovery 전체 분리 | 첫 구현 PR 범위가 넓어 테스트와 리뷰 위험이 커진다" -m "Confidence: high" -m "Scope-risk: moderate" -m "Directive: 다음 command family 분리 전에는 이번 research wiring contract 테스트를 먼저 통과시킬 것" -m "Tested: python -m pytest tests/unit/test_research_command_wiring.py -q; python -m pytest tests/unit/test_subcommands.py -q; python -m pytest tests/unit/test_research_loop.py -q; python -m pytest tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_report.py tests/unit/test_research_optimizer_state.py -q; python -m compileall -q cli; git diff --check --ignore-cr-at-eol HEAD" -m "Not-tested: full backtest; WFO/OOS rerun"
```

### Task 9: Push, Create PR, Merge, and Verify Baseline

**Files:**
- No edits expected.

- [ ] **Step 1: Push feature branch**

Run:

```powershell
git push -u origin feature/cli-subcommands-refactor-plan
```

Expected:

```text
Branch pushed to origin.
```

- [ ] **Step 2: Create GitHub PR**

Run:

```powershell
gh pr create --base STOM_Version_2U_C --head feature/cli-subcommands-refactor-plan --title "Wide v2 CLI subcommands research 명령 wiring 리팩터링" --body-file docs/pr/2026-04-29_wide_v2_cli_subcommands_research_wiring_refactor_pr.md
```

Expected:

```text
GitHub PR URL is printed.
```

- [ ] **Step 3: Merge PR and delete remote branch**

Run:

```powershell
gh pr merge <PR_NUMBER> --merge --delete-branch
```

Expected:

```text
PR merged into STOM_Version_2U_C.
```

- [ ] **Step 4: Verify merged baseline**

Run:

```powershell
python -m pytest tests/unit/ -q
python scripts/verify_nonrelease_sync.py
```

Expected:

```text
All unit tests pass.
All nonrelease sync guardrails pass.
```

- [ ] **Step 5: Create next planning branch**

Run:

```powershell
git switch -c feature/cli-command-family-refactor-review
```

Expected:

```text
Switched to a new branch 'feature/cli-command-family-refactor-review'
```

## Handoff Summary

After this plan is executed, report:

- PR URL and merge commit.
- Changed files.
- Test commands and pass counts.
- Whether `backtest/graph/` remained untracked and untouched.
- Current branch after creating the next planning branch.
- Next recommended command:

```text
$brainstorming Wide v2 CLI 남은 command family 리팩터링 필요성 및 업스트림 업데이트 준비 순서 검토
```
