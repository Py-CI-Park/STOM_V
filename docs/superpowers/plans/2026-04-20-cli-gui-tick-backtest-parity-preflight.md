# CLI/GUI Tick Backtest Parity Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CLI runtime preflight and checkpoint layer so STOM CLI tick backtests can prove they are using the same strategy DB, data DB, config, and execution inputs as the GUI/STOM baseline before Wide v1 Retention-Aware candidate runs resume.

**Architecture:** Add a focused `cli/runtime_preflight.py` module that validates runtime paths, strategy code health, and backtest config without starting a heavy backtest. Add a focused `cli/backtest_checkpoints.py` module and wire it into `cli/runner.py` so timeout results include the last known execution checkpoint. Expose preflight through a top-level `runtime-preflight` subcommand, then document how it gates the next Wide v1 candidate loop.

**Tech Stack:** Python 3.11, argparse, SQLite, dataclasses, pytest, existing STOM CLI modules (`cli.paths`, `cli.config`, `cli.strategy`, `cli.runner`).

---

## Scope

This plan implements PR 1 from the spec:

```text
[PR 1: CLI/GUI Tick Backtest Parity Preflight]
        |
        v
[PR 2: Wide v1 Retention-Aware 후보 개선 재실행]
```

In scope:

- Add `runtime-preflight` as an independent CLI diagnostic command.
- Validate runtime DB paths before heavy tick execution.
- Validate buy/sell strategy presence and code health before heavy tick execution.
- Print the CLI backtest config that will be compared against GUI/STOM logs.
- Add timeout checkpoint recording to `cli.runner.run_backtest()`.
- Add unit tests for preflight, CLI parsing/handling, and checkpoint reporting.
- Add an update log explaining the new preflight gate and remaining risks.

Out of scope:

- Do not run Wide v1 candidate_count=5 in this PR.
- Do not build multi-round improvement loop v2.
- Do not add WFO back into `discovery research`.
- Do not commit runtime DB, generated CSV, or `backtest/graph/`.
- Do not attempt to make every GUI feature available from CLI in this PR.

## File Structure

Create:

- `cli/runtime_preflight.py`
  - Owns runtime path checks, strategy code checks, and config summary generation.
  - Has no dependency on heavy backtest engine imports.

- `cli/backtest_checkpoints.py`
  - Owns lightweight checkpoint recording for `run_backtest()`.
  - Returns plain dictionaries suitable for JSON output.

- `tests/unit/test_runtime_preflight.py`
  - Unit tests for path validation, strategy validation, and preflight result shape.

- `tests/unit/test_backtest_checkpoints.py`
  - Unit tests for checkpoint order, elapsed time, and timeout payload shape.

- `docs/update_log/2026-04-20_cli_gui_tick_backtest_parity_preflight.md`
  - Korean update log for the implemented preflight gate and next phase.

Modify:

- `cli/subcommands.py`
  - Add top-level `runtime-preflight` parser and handler.

- `cli/runner.py`
  - Add checkpoint marks at major runtime stages.
  - Include `checkpoints` and `last_checkpoint` in timeout/error/success results.

- `tests/unit/test_subcommands.py`
  - Add parser and handler tests for `runtime-preflight`.

- `tests/unit/test_runner_helpers.py`
  - Add source contract checks that `run_backtest()` records checkpoints in the timeout path.

## Design Rules

- Keep preflight separate from `discovery research` in this PR.
- Return JSON-friendly dictionaries only.
- Avoid importing GUI modules in preflight.
- Fail fast before heavy backtest starts when strategy code is missing, suspicious, or invalid.
- Treat `????` strategy code as a hard preflight failure.
- Do not require exact GUI/CLI trade-count equality in this PR; this PR creates the gate and diagnostics needed before that comparison.

---

### Task 1: Runtime Preflight Module

**Files:**
- Create: `cli/runtime_preflight.py`
- Test: `tests/unit/test_runtime_preflight.py`

- [ ] **Step 1: Write failing runtime preflight tests**

Create `tests/unit/test_runtime_preflight.py` with this content:

```python
import sqlite3
from pathlib import Path

from cli.config import BacktestConfig


def _make_strategy_db(path: Path, buy_code: str, sell_code: str) -> None:
    con = sqlite3.connect(path)
    try:
        con.execute('CREATE TABLE stockbuy (`index` TEXT PRIMARY KEY, "전략코드" TEXT)')
        con.execute('CREATE TABLE stocksell (`index` TEXT PRIMARY KEY, "전략코드" TEXT)')
        con.execute('INSERT INTO stockbuy VALUES (?, ?)', ('BuyWide', buy_code))
        con.execute('INSERT INTO stocksell VALUES (?, ?)', ('SellWide', sell_code))
        con.commit()
    finally:
        con.close()


def _make_runtime_files(tmp_path: Path, buy_code: str, sell_code: str) -> dict:
    strategy_db = tmp_path / 'strategy.db'
    setting_db = tmp_path / 'setting.db'
    backtest_db = tmp_path / 'backtest.db'
    tick_db = tmp_path / 'stock_tick_back.db'
    csv_dir = tmp_path / 'csv'
    _make_strategy_db(strategy_db, buy_code, sell_code)
    setting_db.write_bytes(b'setting')
    backtest_db.write_bytes(b'backtest')
    tick_db.write_bytes(b'tick')
    csv_dir.mkdir()
    return {
        'strategy_db': str(strategy_db),
        'setting_db': str(setting_db),
        'backtest_db': str(backtest_db),
        'stock_tick_back_db': str(tick_db),
        'stock_min_back_db': str(tmp_path / 'stock_min_back.db'),
        'csv_dir': str(csv_dir),
    }


def _wide_config() -> BacktestConfig:
    return BacktestConfig(
        buy_strategy='BuyWide',
        sell_strategy='SellWide',
        start_date=20250101,
        end_date=20251231,
        start_time=90000,
        end_time=92800,
        avg_time=30,
        engine_count=32,
        is_tick=True,
        timeout=900,
    )


def test_runtime_preflight_passes_with_valid_paths_and_strategies(tmp_path):
    from cli.runtime_preflight import run_runtime_preflight

    paths = _make_runtime_files(
        tmp_path,
        buy_code='매수 = True\nif 매수:\n    self.Buy()',
        sell_code='매도 = True\nif 매도:\n    self.Sell()',
    )

    result = run_runtime_preflight(_wide_config(), paths=paths)

    assert result['status'] == 'ok'
    assert result['runtime_profile']['strategy_db_path'] == paths['strategy_db']
    assert result['runtime_profile']['stock_back_db_path'] == paths['stock_tick_back_db']
    assert result['runtime_profile']['csv_output_dir'] == paths['csv_dir']
    assert result['strategies']['buy']['status'] == 'ok'
    assert result['strategies']['sell']['status'] == 'ok'
    assert result['config']['start'] == 20250101
    assert result['config']['end_time'] == 92800
    assert result['config']['engines'] == 32


def test_runtime_preflight_fails_when_strategy_code_is_question_marks(tmp_path):
    from cli.runtime_preflight import run_runtime_preflight

    paths = _make_runtime_files(
        tmp_path,
        buy_code='????',
        sell_code='매도 = True\nif 매도:\n    self.Sell()',
    )

    result = run_runtime_preflight(_wide_config(), paths=paths)

    assert result['status'] == 'error'
    assert result['strategies']['buy']['status'] == 'error'
    assert result['strategies']['buy']['reason'] == 'suspicious_question_marks'
    assert 'buy_strategy' in result['failed_checks']


def test_runtime_preflight_fails_when_strategy_code_is_too_short(tmp_path):
    from cli.runtime_preflight import run_runtime_preflight

    paths = _make_runtime_files(
        tmp_path,
        buy_code='pass',
        sell_code='매도 = True\nif 매도:\n    self.Sell()',
    )

    result = run_runtime_preflight(_wide_config(), paths=paths)

    assert result['status'] == 'error'
    assert result['strategies']['buy']['status'] == 'error'
    assert result['strategies']['buy']['reason'] == 'code_too_short'


def test_runtime_preflight_fails_when_tick_db_is_missing(tmp_path):
    from cli.runtime_preflight import run_runtime_preflight

    paths = _make_runtime_files(
        tmp_path,
        buy_code='매수 = True\nif 매수:\n    self.Buy()',
        sell_code='매도 = True\nif 매도:\n    self.Sell()',
    )
    Path(paths['stock_tick_back_db']).unlink()

    result = run_runtime_preflight(_wide_config(), paths=paths)

    assert result['status'] == 'error'
    assert result['runtime_profile']['stock_back_db_exists'] is False
    assert 'stock_back_db' in result['failed_checks']
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_runtime_preflight.py -q
```

Expected:

```text
FAILED tests/unit/test_runtime_preflight.py::test_runtime_preflight_passes_with_valid_paths_and_strategies
ModuleNotFoundError: No module named 'cli.runtime_preflight'
```

- [ ] **Step 3: Add the runtime preflight implementation**

Create `cli/runtime_preflight.py` with this content:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from cli.config import BacktestConfig
from cli.paths import (
    PROJECT_ROOT,
    DB_SETTING,
    DB_STRATEGY,
    DB_BACKTEST,
    DB_STOCK_BACK_TICK,
    DB_STOCK_BACK_MIN,
)
from cli.strategy import evaluate_strategy


MIN_STRATEGY_CODE_LENGTH = 12


def default_runtime_paths() -> dict[str, str]:
    csv_dir = Path(PROJECT_ROOT) / 'backtest' / 'csv'
    return {
        'project_root': str(PROJECT_ROOT),
        'strategy_db': DB_STRATEGY,
        'setting_db': DB_SETTING,
        'backtest_db': DB_BACKTEST,
        'stock_tick_back_db': DB_STOCK_BACK_TICK,
        'stock_min_back_db': DB_STOCK_BACK_MIN,
        'csv_dir': str(csv_dir),
    }


def _path_status(path: str) -> dict[str, Any]:
    resolved = Path(path)
    exists = resolved.exists()
    return {
        'path': str(resolved),
        'exists': exists,
        'size_bytes': resolved.stat().st_size if exists and resolved.is_file() else 0,
    }


def _is_question_mark_code(code: str) -> bool:
    compact = ''.join(str(code).split())
    return bool(compact) and set(compact) == {'?'}


def check_strategy_code(
    strategy_db: str,
    strategy_name: str,
    strategy_type: str,
    *,
    min_code_length: int = MIN_STRATEGY_CODE_LENGTH,
) -> dict[str, Any]:
    result = evaluate_strategy(strategy_db, strategy_name, strategy_type)
    code = result.get('code') or ''
    code_length = len(code)
    base = {
        'strategy_name': strategy_name,
        'strategy_type': strategy_type,
        'status': result.get('status'),
        'message': result.get('message', ''),
        'code_length': code_length,
    }

    if _is_question_mark_code(code):
        return {
            **base,
            'status': 'error',
            'reason': 'suspicious_question_marks',
            'message': 'strategy code is only question marks',
        }

    if code and code_length < min_code_length:
        return {
            **base,
            'status': 'error',
            'reason': 'code_too_short',
            'message': 'strategy code is shorter than the minimum safe length',
        }

    if result.get('status') != 'ok':
        return {
            **base,
            'status': 'error',
            'reason': 'evaluate_failed',
        }

    return {
        **base,
        'status': 'ok',
        'reason': 'ok',
    }


def _config_summary(config: BacktestConfig) -> dict[str, Any]:
    return {
        'buy_strategy': config.buy_strategy,
        'sell_strategy': config.sell_strategy,
        'start': config.start_date,
        'end': config.end_date,
        'timeframe': 'tick' if config.is_tick else 'min',
        'avg_time': config.avg_time,
        'start_time': config.start_time,
        'end_time': config.end_time,
        'engines': config.engine_count,
        'timeout': config.timeout,
        'betting': config.betting,
        'oms': config.oms,
        'blacklist': config.blacklist,
        'back_club': config.back_club,
        'divid_mode': config.divid_mode,
        'one_code': config.one_code,
    }


def run_runtime_preflight(
    config: BacktestConfig,
    *,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    runtime_paths = dict(default_runtime_paths())
    if paths:
        runtime_paths.update(paths)

    stock_back_key = 'stock_tick_back_db' if config.is_tick else 'stock_min_back_db'
    stock_back_status = _path_status(runtime_paths[stock_back_key])

    runtime_profile = {
        'project_root': runtime_paths.get('project_root', str(PROJECT_ROOT)),
        'strategy_db_path': runtime_paths['strategy_db'],
        'setting_db_path': runtime_paths['setting_db'],
        'backtest_db_path': runtime_paths['backtest_db'],
        'stock_back_db_path': runtime_paths[stock_back_key],
        'stock_back_db_kind': 'tick' if config.is_tick else 'min',
        'csv_output_dir': runtime_paths['csv_dir'],
        'strategy_db_exists': _path_status(runtime_paths['strategy_db'])['exists'],
        'setting_db_exists': _path_status(runtime_paths['setting_db'])['exists'],
        'backtest_db_exists': _path_status(runtime_paths['backtest_db'])['exists'],
        'stock_back_db_exists': stock_back_status['exists'],
        'csv_output_dir_exists': Path(runtime_paths['csv_dir']).exists(),
    }

    buy_check = check_strategy_code(
        runtime_paths['strategy_db'],
        config.buy_strategy,
        'buy',
    )
    sell_check = check_strategy_code(
        runtime_paths['strategy_db'],
        config.sell_strategy,
        'sell',
    )

    failed_checks: list[str] = []
    if not runtime_profile['strategy_db_exists']:
        failed_checks.append('strategy_db')
    if not runtime_profile['setting_db_exists']:
        failed_checks.append('setting_db')
    if not runtime_profile['backtest_db_exists']:
        failed_checks.append('backtest_db')
    if not runtime_profile['stock_back_db_exists']:
        failed_checks.append('stock_back_db')
    if not runtime_profile['csv_output_dir_exists']:
        failed_checks.append('csv_output_dir')
    if buy_check['status'] != 'ok':
        failed_checks.append('buy_strategy')
    if sell_check['status'] != 'ok':
        failed_checks.append('sell_strategy')

    status = 'ok' if not failed_checks else 'error'
    return {
        'status': status,
        'message': 'runtime preflight passed' if status == 'ok' else 'runtime preflight failed',
        'failed_checks': failed_checks,
        'runtime_profile': runtime_profile,
        'strategies': {
            'buy': buy_check,
            'sell': sell_check,
        },
        'config': _config_summary(config),
    }
```

- [ ] **Step 4: Run the runtime preflight tests and verify they pass**

Run:

```powershell
python -m pytest tests/unit/test_runtime_preflight.py -q
```

Expected:

```text
4 passed
```

- [ ] **Step 5: Commit Task 1**

Run:

```powershell
git add cli/runtime_preflight.py tests/unit/test_runtime_preflight.py
git commit -m "CLI 런타임 프리플라이트 검증을 추가한다" -m "GUI 백테스트와 CLI 백테스트가 같은 runtime DB와 전략코드를 보는지 확인하기 위해 독립 preflight 모듈을 추가했다.

전략코드가 물음표로 깨진 경우, 코드 길이가 비정상적으로 짧은 경우, tick DB가 없는 경우를 heavy 백테스트 전에 차단한다.

Constraint: heavy tick 백테스트를 unit test에 포함하지 않음
Rejected: discovery research 내부에 직접 구현 | 실패 원인 분리가 어려워 독립 모듈로 시작
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_runtime_preflight.py -q
Not-tested: 실제 wt-dev tick DB preflight"
```

---

### Task 2: Runtime Preflight CLI Command

**Files:**
- Modify: `cli/subcommands.py`
- Test: `tests/unit/test_subcommands.py`

- [ ] **Step 1: Add failing parser and handler tests**

Append these tests to `tests/unit/test_subcommands.py`:

```python
def test_runtime_preflight_parser_accepts_tick_inputs():
    parser = create_subcommand_parser()
    args = parser.parse_args([
        'runtime-preflight',
        '--buy', 'BuyWide',
        '--sell', 'SellWide',
        '--start', '20250101',
        '--end', '20251231',
        '--timeframe', 'tick',
        '--avg-time', '30',
        '--start-time', '90000',
        '--end-time', '92800',
        '--engines', '32',
        '--timeout', '900',
    ])

    assert args.command == 'runtime-preflight'
    assert args.buy == 'BuyWide'
    assert args.sell == 'SellWide'
    assert args.timeframe == 'tick'
    assert args.avg_time == 30
    assert args.engines == 32
    assert args.timeout == 900


def test_runtime_preflight_handler_outputs_json(capsys):
    with patch('cli.runtime_preflight.run_runtime_preflight') as mock:
        mock.return_value = {
            'status': 'ok',
            'message': 'runtime preflight passed',
            'failed_checks': [],
            'runtime_profile': {'strategy_db_path': 'strategy.db'},
            'strategies': {},
            'config': {},
        }
        exit_code = handle_subcommand([
            'runtime-preflight',
            '--buy', 'BuyWide',
            '--sell', 'SellWide',
            '--start', '20250101',
            '--end', '20251231',
            '--timeframe', 'tick',
            '--avg-time', '30',
            '--start-time', '90000',
            '--end-time', '92800',
            '--engines', '32',
            '--timeout', '900',
        ])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['status'] == 'ok'
    config = mock.call_args.args[0]
    assert config.buy_strategy == 'BuyWide'
    assert config.sell_strategy == 'SellWide'
    assert config.start_date == 20250101
    assert config.end_date == 20251231
    assert config.is_tick is True
    assert config.avg_time == 30
    assert config.engine_count == 32
    assert config.timeout == 900


def test_runtime_preflight_handler_returns_error_code_on_failed_preflight(capsys):
    with patch('cli.runtime_preflight.run_runtime_preflight') as mock:
        mock.return_value = {
            'status': 'error',
            'message': 'runtime preflight failed',
            'failed_checks': ['buy_strategy'],
            'runtime_profile': {},
            'strategies': {},
            'config': {},
        }
        exit_code = handle_subcommand([
            'runtime-preflight',
            '--buy', 'BrokenBuy',
            '--sell', 'SellWide',
            '--start', '20250101',
            '--end', '20251231',
        ])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload['failed_checks'] == ['buy_strategy']
```

- [ ] **Step 2: Run the new subcommand tests and verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py::test_runtime_preflight_parser_accepts_tick_inputs tests/unit/test_subcommands.py::test_runtime_preflight_handler_outputs_json tests/unit/test_subcommands.py::test_runtime_preflight_handler_returns_error_code_on_failed_preflight -q
```

Expected:

```text
FAILED tests/unit/test_subcommands.py::test_runtime_preflight_parser_accepts_tick_inputs
SystemExit: 2
```

- [ ] **Step 3: Add the parser**

In `cli/subcommands.py`, inside `create_subcommand_parser()` after `sub = parser.add_subparsers(dest='command')`, add:

```python
    runtime_preflight = sub.add_parser(
        'runtime-preflight',
        help='CLI 백테스트 실행 전 runtime DB, 전략코드, 실행 조건을 검증',
    )
    runtime_preflight.add_argument('--buy', required=True, help='매수 전략명')
    runtime_preflight.add_argument('--sell', required=True, help='매도 전략명')
    runtime_preflight.add_argument('--start', type=int, required=True, help='시작일 YYYYMMDD')
    runtime_preflight.add_argument('--end', type=int, required=True, help='종료일 YYYYMMDD')
    runtime_preflight.add_argument('--timeframe', choices=['tick', 'min'], default='tick')
    runtime_preflight.add_argument('--betting', default='1')
    runtime_preflight.add_argument('--avg-time', type=int, default=60)
    runtime_preflight.add_argument('--start-time', type=int, default=90000)
    runtime_preflight.add_argument('--end-time', type=int, default=152800)
    runtime_preflight.add_argument('--engines', type=int, default=4)
    runtime_preflight.add_argument('--timeout', type=int, default=3600)
    runtime_preflight.add_argument('--oms', action='store_true', default=False)
    runtime_preflight.add_argument('--blacklist', action='store_true', default=False)
    runtime_preflight.add_argument('--back-club', action='store_true', default=False)
    runtime_preflight.add_argument('--divid-mode', default='종목코드별 분류')
    runtime_preflight.add_argument('--one-code', default='')
```

- [ ] **Step 4: Add the handler dispatch**

In `cli/subcommands.py`, inside `handle_subcommand()`, add this branch before the final `else`:

```python
    elif parsed.command == 'runtime-preflight':
        return _handle_runtime_preflight(parsed)
```

- [ ] **Step 5: Add the runtime preflight handler**

In `cli/subcommands.py`, add this function before `_handle_formula(parsed)`:

```python
def _handle_runtime_preflight(parsed):
    from cli.config import BacktestConfig
    from cli.runtime_preflight import run_runtime_preflight

    config = BacktestConfig(
        buy_strategy=parsed.buy,
        sell_strategy=parsed.sell,
        start_date=parsed.start,
        end_date=parsed.end,
        betting=parsed.betting,
        avg_time=parsed.avg_time,
        start_time=parsed.start_time,
        end_time=parsed.end_time,
        engine_count=parsed.engines,
        is_tick=parsed.timeframe == 'tick',
        oms=parsed.oms,
        blacklist=parsed.blacklist,
        back_club=parsed.back_club,
        divid_mode=parsed.divid_mode,
        one_code=parsed.one_code,
        timeout=parsed.timeout,
    )
    result = run_runtime_preflight(config)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result.get('status') == 'ok' else 1
```

- [ ] **Step 6: Run the subcommand tests and verify they pass**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py::test_runtime_preflight_parser_accepts_tick_inputs tests/unit/test_subcommands.py::test_runtime_preflight_handler_outputs_json tests/unit/test_subcommands.py::test_runtime_preflight_handler_returns_error_code_on_failed_preflight -q
```

Expected:

```text
3 passed
```

- [ ] **Step 7: Commit Task 2**

Run:

```powershell
git add cli/subcommands.py tests/unit/test_subcommands.py
git commit -m "런타임 프리플라이트 CLI 명령을 추가한다" -m "runtime-preflight 명령을 추가해 heavy 백테스트 전에 CLI가 보는 DB 경로와 전략코드 상태를 JSON으로 확인할 수 있게 했다.

Wide v1 후보 루프는 이 명령으로 baseline 실행 조건을 확인한 뒤 재개한다.

Constraint: discovery research 동작은 이번 커밋에서 변경하지 않음
Rejected: discovery research 내부에 preflight를 즉시 강제 | 독립 진단 경로 검증이 먼저 필요함
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_subcommands.py::test_runtime_preflight_parser_accepts_tick_inputs tests/unit/test_subcommands.py::test_runtime_preflight_handler_outputs_json tests/unit/test_subcommands.py::test_runtime_preflight_handler_returns_error_code_on_failed_preflight -q
Not-tested: 실제 wt-dev runtime-preflight 명령"
```

---

### Task 3: Backtest Checkpoint Recorder

**Files:**
- Create: `cli/backtest_checkpoints.py`
- Test: `tests/unit/test_backtest_checkpoints.py`

- [ ] **Step 1: Write failing checkpoint tests**

Create `tests/unit/test_backtest_checkpoints.py` with this content:

```python
from cli.backtest_checkpoints import BacktestCheckpointRecorder


def test_checkpoint_recorder_tracks_last_checkpoint():
    recorder = BacktestCheckpointRecorder()

    recorder.mark('preflight_started')
    recorder.mark('strategy_validated')

    assert recorder.last_checkpoint == 'strategy_validated'
    assert [item['name'] for item in recorder.events] == [
        'preflight_started',
        'strategy_validated',
    ]


def test_checkpoint_recorder_builds_timeout_payload():
    recorder = BacktestCheckpointRecorder()
    recorder.mark('shared_data_loaded', detail={'back_count': 1638})

    payload = recorder.to_result_fields(
        status='timeout',
        cleanup_status='ok',
    )

    assert payload['last_checkpoint'] == 'shared_data_loaded'
    assert payload['checkpoints'][0]['detail'] == {'back_count': 1638}
    assert payload['checkpoint_status'] == 'timeout'
    assert payload['cleanup_status'] == 'ok'
    assert payload['elapsed_seconds'] >= 0
```

- [ ] **Step 2: Run the checkpoint tests and verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_backtest_checkpoints.py -q
```

Expected:

```text
FAILED tests/unit/test_backtest_checkpoints.py::test_checkpoint_recorder_tracks_last_checkpoint
ModuleNotFoundError: No module named 'cli.backtest_checkpoints'
```

- [ ] **Step 3: Add the checkpoint recorder implementation**

Create `cli/backtest_checkpoints.py` with this content:

```python
from __future__ import annotations

import time
from typing import Any


class BacktestCheckpointRecorder:
    def __init__(self) -> None:
        self.started_at = time.time()
        self.events: list[dict[str, Any]] = []

    def mark(self, name: str, detail: dict[str, Any] | None = None) -> None:
        self.events.append({
            'name': name,
            'elapsed_seconds': round(time.time() - self.started_at, 3),
            'detail': detail or {},
        })

    @property
    def last_checkpoint(self) -> str | None:
        if not self.events:
            return None
        return self.events[-1]['name']

    def to_result_fields(
        self,
        *,
        status: str,
        cleanup_status: str | None = None,
    ) -> dict[str, Any]:
        fields = {
            'checkpoint_status': status,
            'last_checkpoint': self.last_checkpoint,
            'elapsed_seconds': round(time.time() - self.started_at, 3),
            'checkpoints': list(self.events),
        }
        if cleanup_status is not None:
            fields['cleanup_status'] = cleanup_status
        return fields
```

- [ ] **Step 4: Run the checkpoint tests and verify they pass**

Run:

```powershell
python -m pytest tests/unit/test_backtest_checkpoints.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit Task 3**

Run:

```powershell
git add cli/backtest_checkpoints.py tests/unit/test_backtest_checkpoints.py
git commit -m "백테스트 체크포인트 기록기를 추가한다" -m "CLI 백테스트 timeout 원인을 분리할 수 있도록 실행 단계 checkpoint를 누적하고 JSON 결과 필드로 변환하는 작은 기록기를 추가했다.

이 기록기는 runner에 연결되기 전 독립 단위 테스트로 동작을 고정한다.

Constraint: checkpoint는 JSON 직렬화 가능한 값만 저장해야 함
Rejected: 로그 문자열 파싱 | 구조화된 결과 필드가 리포트와 테스트에 더 안정적임
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_backtest_checkpoints.py -q
Not-tested: runner 통합"
```

---

### Task 4: Runner Timeout Checkpoint Integration

**Files:**
- Modify: `cli/runner.py`
- Modify: `tests/unit/test_runner_helpers.py`

- [ ] **Step 1: Add failing source contract tests**

Append these tests to `tests/unit/test_runner_helpers.py`:

```python
def test_runner_imports_checkpoint_recorder():
    runner_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'cli', 'runner.py',
    )
    with open(runner_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert 'from cli.backtest_checkpoints import BacktestCheckpointRecorder' in content


def test_runner_records_timeout_checkpoint_fields():
    runner_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'cli', 'runner.py',
    )
    with open(runner_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert "checkpoint.mark('preflight_started')" in content
    assert "checkpoint.mark('shared_data_loaded'" in content
    assert "checkpoint.mark('backtest_process_started')" in content
    assert "checkpoint.to_result_fields(status='timeout'" in content
    assert "result.update(checkpoint.to_result_fields(status='success'" in content
```

- [ ] **Step 2: Run the source contract tests and verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_runner_helpers.py::test_runner_imports_checkpoint_recorder tests/unit/test_runner_helpers.py::test_runner_records_timeout_checkpoint_fields -q
```

Expected:

```text
FAILED tests/unit/test_runner_helpers.py::test_runner_imports_checkpoint_recorder
AssertionError
```

- [ ] **Step 3: Import the checkpoint recorder**

In `cli/runner.py`, add this import near other `cli.*` imports:

```python
from cli.backtest_checkpoints import BacktestCheckpointRecorder
```

- [ ] **Step 4: Create the recorder at the start of `run_backtest()`**

Inside `run_backtest(config)`, immediately after `_run_start_time = time.time()`, add:

```python
    checkpoint = BacktestCheckpointRecorder()
    checkpoint.mark('preflight_started', detail={
        'buy_strategy': config.buy_strategy,
        'sell_strategy': config.sell_strategy,
        'start_date': config.start_date,
        'end_date': config.end_date,
        'is_tick': config.is_tick,
        'engine_count': config.engine_count,
    })
```

- [ ] **Step 5: Mark the major runner stages**

In `cli/runner.py`, add these checkpoint marks at the matching existing locations:

After `dict_set = _sync_dict_set(config)`:

```python
    checkpoint.mark('dict_set_synced')
```

After `backtest_rowid_watermark = _get_backtest_last_rowid()`:

```python
        checkpoint.mark('backtest_watermark_ready', detail={
            'backtest_rowid_watermark': backtest_rowid_watermark,
        })
```

After selecting `db = DB_STOCK_BACK_TICK if config.is_tick else DB_STOCK_BACK_MIN`:

```python
        checkpoint.mark('stock_back_db_selected', detail={'db_path': db})
```

After `df_mt = pd.read_sql(query, con)` and before `if df_mt is None or df_mt.empty:`:

```python
        checkpoint.mark('moneytop_loaded', detail={'rows': 0 if df_mt is None else len(df_mt)})
```

After `windowQ.put((1.4, f'{log_gubun} 데이터 로딩 완료'))` equivalent in the source:

```python
        checkpoint.mark('shared_data_loaded', detail={'back_count': len(shared_info)})
```

After `back_count = len(shared_info)`:

```python
        checkpoint.mark('back_count_ready', detail={'back_count': back_count})
```

Immediately after `proc_backtest.start()`:

```python
        checkpoint.mark('backtest_process_started', detail={'pid': proc_backtest.pid})
```

Immediately after the `proc_backtest.join(timeout=timeout)` call when the process is no longer alive:

```python
        checkpoint.mark('backtest_process_finished', detail={'exitcode': proc_backtest.exitcode})
```

After `csv_path = _find_latest_csv(config.buy_strategy, _run_start_time)`:

```python
        checkpoint.mark('csv_detected', detail={'csv_path': csv_path})
```

- [ ] **Step 6: Add checkpoint fields to early error returns**

For early return branches inside `run_backtest(config)`, before `return result`, add:

```python
            result.update(checkpoint.to_result_fields(status='error'))
```

Apply this to the branches where:

```text
df_mt is None or df_mt.empty
len(code_set) < multi
len(day_list) < multi
one_code not in code_days
len(code_days.get(one_code, set())) < multi
```

- [ ] **Step 7: Add checkpoint fields to timeout result**

In the `if proc_backtest.is_alive():` branch, after setting `result['message']`, add:

```python
            result.update(checkpoint.to_result_fields(status='timeout', cleanup_status='process_killed'))
```

- [ ] **Step 8: Add checkpoint fields to success result**

In the `if metrics:` success branch, before setting `result['config']`, add:

```python
            result.update(checkpoint.to_result_fields(status='success'))
```

In the branch where metrics are missing and the result stays error, add:

```python
            result.update(checkpoint.to_result_fields(status='error'))
```

- [ ] **Step 9: Run the source contract tests and verify they pass**

Run:

```powershell
python -m pytest tests/unit/test_runner_helpers.py::test_runner_imports_checkpoint_recorder tests/unit/test_runner_helpers.py::test_runner_records_timeout_checkpoint_fields -q
```

Expected:

```text
2 passed
```

- [ ] **Step 10: Run runner helper tests**

Run:

```powershell
python -m pytest tests/unit/test_runner_helpers.py -q
```

Expected:

```text
all tests pass
```

- [ ] **Step 11: Commit Task 4**

Run:

```powershell
git add cli/runner.py tests/unit/test_runner_helpers.py
git commit -m "CLI 백테스트 timeout 체크포인트를 연결한다" -m "run_backtest 실행 단계에 checkpoint 기록을 연결해 timeout 또는 조기 실패 시 마지막 진행 지점을 JSON 결과에 남기도록 했다.

후보 백테스트가 timeout될 때 조건식 문제인지 데이터 로딩 문제인지 BackTest 프로세스 문제인지 분리할 수 있는 근거를 제공한다.

Constraint: heavy backtest integration test는 unit suite에 포함하지 않음
Rejected: stdout 로그만 추가 | 자동 연구 리포트에서 구조화된 필드가 필요함
Confidence: medium
Scope-risk: moderate
Tested: python -m pytest tests/unit/test_runner_helpers.py -q
Not-tested: 실제 timeout 발생 시 checkpoint payload 확인"
```

---

### Task 5: Focused Verification and Update Log

**Files:**
- Create: `docs/update_log/2026-04-20_cli_gui_tick_backtest_parity_preflight.md`

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m pytest tests/unit/test_runtime_preflight.py tests/unit/test_backtest_checkpoints.py tests/unit/test_subcommands.py tests/unit/test_runner_helpers.py -q
```

Expected:

```text
all tests pass
```

- [ ] **Step 2: Run full unit tests**

Run:

```powershell
python -m pytest tests/unit/ -q
```

Expected:

```text
all tests pass
```

- [ ] **Step 3: Run non-release sync verification**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
```

Expected:

```text
verification passed
```

- [ ] **Step 4: Write the update log**

After Steps 1-3 pass, create `docs/update_log/2026-04-20_cli_gui_tick_backtest_parity_preflight.md` with this content:

```markdown
# 2026-04-20 CLI/GUI Tick Backtest Parity Preflight

## 목적

GUI/STOM에서 1분 내 완료된 Wide v1 tick 백테스트를 CLI 자동 연구 루프가 같은 조건으로 재현할 수 있도록, heavy 백테스트 전 runtime preflight와 timeout checkpoint 기반을 추가했다.

## 전체 개발 흐름

```text
[Wide v1 GUI/STOM 백테스트 성공]
        |
        v
[CLI/GUI Tick Backtest Parity Preflight]  <- 이번 작업
        |
        v
[CLI baseline 1회 검증]
        |
        v
[Wide v1 Retention-Aware 후보 5개 실행]
        |
        v
[반복 개선 루프 v2]
        |
        v
[최종 promote/WFO 검증]
```

## 변경 사항

- `cli/runtime_preflight.py` 추가
- `runtime-preflight` CLI 명령 추가
- `cli/backtest_checkpoints.py` 추가
- `cli.runner.run_backtest()` timeout checkpoint 필드 연결
- runtime preflight, subcommand, checkpoint 단위 테스트 추가

## 검증

- focused tests: PASS
- full unit tests: PASS
- verify_nonrelease_sync.py: PASS

## 남은 리스크

- 이번 작업은 실제 Wide v1 후보 5개 백테스트를 수행하지 않는다.
- CLI baseline 1회가 GUI 결과와 같은지 확인하는 파일럿은 후속 작업이다.
- `strategy.db`가 다시 `????` 상태로 깨지는 경우 preflight가 차단해야 한다.
- feature worktree heavy tick 실행은 runtime profile이 명확해질 때까지 `wt-dev` 기준으로 제한한다.

## 다음 단계

```text
1. wt-dev에서 runtime-preflight 실행
2. ResearchTest wide 조건식 코드 정상성 확인
3. CLI baseline 1회 백테스트 실행
4. GUI 기준 결과와 비교
5. 통과 시 Wide v1 Retention-Aware 후보 5개 실행 재개
```
```

- [ ] **Step 5: Commit Task 5**

Run:

```powershell
git add docs/update_log/2026-04-20_cli_gui_tick_backtest_parity_preflight.md
git commit -m "CLI GUI 백테스트 정합성 변경 기록을 남긴다" -m "runtime preflight와 timeout checkpoint 변경 목적, 검증 결과, 다음 Wide v1 후보 개선 재개 조건을 update_log에 기록했다.

Constraint: 실제 Wide v1 후보 5개 실행은 후속 작업으로 분리
Confidence: high
Scope-risk: narrow
Tested: focused unit tests, full unit tests, verify_nonrelease_sync.py
Not-tested: wt-dev 실제 tick baseline CLI 파일럿"
```

---

### Task 6: Manual wt-dev Runtime Preflight Pilot

**Files:**
- No tracked file changes unless the command output reveals a documentation correction is required.

- [ ] **Step 1: Confirm working tree state**

Run:

```powershell
git status --short --branch
```

Expected:

```text
## feature/cli-gui-tick-backtest-parity-preflight...
?? backtest/graph/
```

If the branch name is different, confirm it is the implementation branch for this plan before continuing. `backtest/graph/` remains protected generated output and must not be staged.

- [ ] **Step 2: Run Wide v1 runtime preflight in wt-dev runtime**

Run from `C:\System_Trading\STOM\STOM_V.wt-dev`:

```powershell
python stom_backtest.py runtime-preflight `
  --buy ResearchTest_Tick_B_090000_092800_Wide_20260419 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --avg-time 30 `
  --start-time 90000 `
  --end-time 92800 `
  --engines 32 `
  --timeout 900
```

Expected success shape:

```json
{
  "status": "ok",
  "failed_checks": [],
  "runtime_profile": {
    "strategy_db_exists": true,
    "stock_back_db_exists": true,
    "csv_output_dir_exists": true
  },
  "strategies": {
    "buy": {"status": "ok"},
    "sell": {"status": "ok"}
  },
  "config": {
    "start": 20250101,
    "end": 20251231,
    "timeframe": "tick",
    "avg_time": 30,
    "start_time": 90000,
    "end_time": 92800,
    "engines": 32,
    "timeout": 900
  }
}
```

Expected failure shape when strategy code is still corrupted:

```json
{
  "status": "error",
  "failed_checks": ["buy_strategy", "sell_strategy"],
  "strategies": {
    "buy": {"status": "error", "reason": "suspicious_question_marks"},
    "sell": {"status": "error", "reason": "suspicious_question_marks"}
  }
}
```

- [ ] **Step 3: Decide the next action from the preflight result**

If the result is `status=ok`, proceed to the next plan or PR step for CLI baseline 1회 백테스트.

If the result is `status=error`, do not run candidate_count=5. Record the failing check and fix the runtime DB/strategy loading issue first.

- [ ] **Step 4: Record pilot result in the PR report or update log**

If the branch will be PR'd immediately, include the exact preflight result in `docs/pr/<date>_cli_gui_tick_backtest_parity_preflight_pr.md`.

If the branch will continue into CLI baseline work first, append the exact preflight result to `docs/update_log/2026-04-20_cli_gui_tick_backtest_parity_preflight.md` and commit that update with:

```powershell
git add docs/update_log/2026-04-20_cli_gui_tick_backtest_parity_preflight.md
git commit -m "Wide v1 런타임 프리플라이트 결과를 기록한다" -m "wt-dev 기준 ResearchTest wide 조건식의 CLI runtime-preflight 결과를 기록해 baseline CLI 백테스트 진행 가능 여부를 판단할 수 있게 했다.

Constraint: 후보 5개 백테스트는 preflight 통과 후에만 실행
Confidence: medium
Scope-risk: narrow
Tested: python stom_backtest.py runtime-preflight for ResearchTest wide
Not-tested: candidate_count=5 run"
```

---

## Final Verification Before PR

Run:

```powershell
python -m pytest tests/unit/test_runtime_preflight.py tests/unit/test_backtest_checkpoints.py tests/unit/test_subcommands.py tests/unit/test_runner_helpers.py -q
python -m pytest tests/unit/ -q
python scripts/verify_nonrelease_sync.py
git status --short --branch
```

Expected:

```text
focused tests pass
full unit tests pass
verify_nonrelease_sync.py passes
only protected/generated untracked files remain unstaged
```

## PR Report Requirements

When implementation is complete, create `docs/pr/2026-04-20_cli_gui_tick_backtest_parity_preflight_pr.md` with:

```text
1. 이번 PR의 목적
2. 전체 자동 조건식 연구 흐름에서의 위치
3. GUI 성공 Wide v1 결과 요약
4. runtime-preflight 변경 사항
5. timeout checkpoint 변경 사항
6. 테스트 결과
7. wt-dev runtime-preflight 파일럿 결과
8. 남은 리스크
9. 다음 단계 명령어
```

The next work after this PR is:

```text
$brainstorming Wide v1 CLI Baseline Backtest Gate 및 Retention-Aware 후보 실행 재개 설계
```

That follow-up should only start after `runtime-preflight` proves the ResearchTest wide strategies and tick DB are valid from CLI.

## Self-Review Checklist

Spec coverage:

```text
runtime DB 경로 출력: Task 1, Task 2
strategy code 정상성 검증: Task 1
???? 차단: Task 1
baseline gate 선행: Task 6 and follow-up command
timeout checkpoint: Task 3, Task 4
feature worktree runtime caution: Task 5, Task 6
후보 5개 실행 분리: Scope and PR Report Requirements
```

Type consistency:

```text
run_runtime_preflight(config, paths=None)
check_strategy_code(strategy_db, strategy_name, strategy_type, min_code_length=...)
BacktestCheckpointRecorder.mark(name, detail=None)
BacktestCheckpointRecorder.to_result_fields(status=..., cleanup_status=None)
```

No runtime DB, CSV, or graph files should be staged.
