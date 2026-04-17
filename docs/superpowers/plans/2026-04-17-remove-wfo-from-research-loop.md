# Remove WFO From Research Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove WFO from `discovery research` while preserving existing WFO functionality in `cli.wfo`, `AIBacktestController.walk_forward()`, `discovery promote`, and `auto_discovery`.

**Architecture:** This is a simplification change. Remove WFO-only fields, helpers, CLI options, report sections, and tests from the research loop; do not touch core backtest/trade code or existing WFO/promote paths. Keep the fast CSV-analysis -> candidate-filter -> candidate-backtest -> comparison -> promotion report flow intact.

**Tech Stack:** Python 3.11, existing STOM CLI modules, pytest.

---

## Scope Check

This plan removes only the WFO connection from `discovery research`.

Keep:

- `cli/wfo.py`
- `AIBacktestController.walk_forward()`
- `AIBacktestController.evaluate_walk_forward_result()`
- `discovery promote`
- `auto_discovery` WFO phase

Remove from `discovery research`:

- user-facing WFO options
- WFO config fields in `ResearchLoopConfig`
- WFO helpers and execution branches
- WFO report sections
- WFO-only research tests

Out of scope:

- Backtest iteration loop implementation.
- Opportunity-universe logging.
- AI condition generation.
- Any core `backtest/`, `trade/`, or GUI changes.

## File Structure

- Modify `cli/research_loop.py`
  - Remove WFO dataclass fields, helpers, execution payload keys.

- Modify `cli/research_report.py`
  - Remove WFO and final-decision fields/Markdown sections.

- Modify `cli/subcommands.py`
  - Remove WFO options from only `discovery research`.
  - Remove research-specific param-space loading branch.

- Modify tests:
  - `tests/unit/test_research_loop.py`
  - `tests/unit/test_research_report.py`
  - `tests/unit/test_subcommands.py`

- Add update log:
  - `docs/update_log/2026-04-17_remove_wfo_from_research_loop.md`

---

### Task 1: Remove WFO From ResearchLoopConfig And Execution

**Files:**
- Modify: `cli/research_loop.py`
- Modify: `tests/unit/test_research_loop.py`

- [ ] **Step 1: Write failing tests that assert WFO fields are gone**

Add to `tests/unit/test_research_loop.py`:

```python
from dataclasses import fields


def test_research_loop_config_has_no_wfo_fields():
    names = {field.name for field in fields(ResearchLoopConfig)}
    assert 'run_wfo' not in names
    assert 'train_window_days' not in names
    assert 'test_window_days' not in names
    assert 'param_space' not in names


def test_research_result_has_no_wfo_payload(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    candidate = tmp_path / 'candidate.csv'
    _write_trade_csv(baseline, name='A')
    _write_trade_csv(candidate, name='B')
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)

    result = run_research_once(
        ResearchLoopConfig(
            name='NoWfoPayload',
            baseline_csv=str(baseline),
            base_buy_strategy='BaseBuy',
            run_candidate=True,
        ),
        DummyController(str(candidate)),
    )

    assert result['status'] == 'ok'
    assert 'wfo_result' not in result
    assert 'wfo_evaluation' not in result
    assert 'combined_evaluation' not in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_research_loop_config_has_no_wfo_fields tests/unit/test_research_loop.py::test_research_result_has_no_wfo_payload -q
```

Expected:

```text
FAILED because WFO fields/payload still exist
```

- [ ] **Step 3: Remove WFO code from `cli/research_loop.py`**

Edit `cli/research_loop.py`:

Remove imports that are only used by WFO:

```python
from dataclasses import field
import math
from cli.promotion import resolve_promotion_criteria
```

Keep:

```python
from dataclasses import asdict, dataclass
```

Remove constant:

```python
_WFO_CRITERIA_KEYS = (...)
```

Remove these `ResearchLoopConfig` fields:

```python
    run_wfo: bool = False
    train_window_days: int | None = None
    test_window_days: int | None = None
    step_days: int | None = None
    purge_days: int = 0
    embargo_days: int = 0
    objective: str = 'tpi'
    wfo_method: str = 'grid'
    wfo_max_iter: int = 10
    promotion_preset: str = 'balanced'
    promotion_criteria: dict | None = None
    param_space: dict = field(default_factory=dict)
```

Remove helper functions:

```python
_resolve_wfo_eval_criteria
_validate_wfo_config
_wfo_settings_dict
_wfo_eval_criteria
_combined_evaluation
```

Remove this block from `run_research_once()`:

```python
    wfo_eval_criteria, wfo_config_error = _resolve_wfo_eval_criteria(config)
    if wfo_config_error is not None:
        return {**wfo_config_error, 'baseline_csv': baseline_csv, 'baseline_result': baseline_result}
```

Remove WFO execution block after promotion:

```python
    wfo_result = None
    wfo_evaluation = None
    if config.run_wfo:
        ...
    combined = _combined_evaluation(...)
```

Remove final payload keys:

```python
        'wfo_result': wfo_result,
        'wfo_evaluation': wfo_evaluation,
        'combined_evaluation': combined,
```

- [ ] **Step 4: Remove WFO-only tests**

Delete WFO-only tests and helper class from `tests/unit/test_research_loop.py`:

- `test_research_loop_rejects_wfo_without_candidate`
- `test_research_loop_rejects_wfo_without_train_or_test_windows`
- `WfoController`
- WFO criteria validation tests
- WFO success/failure tests
- WFO execution/evaluation phase tests

Keep non-WFO tests for:

- preview path
- candidate generation
- base strategy required
- analysis failure
- no expressions
- base strategy load failure
- candidate name conflict
- filter generation failure
- save failure
- candidate backtest failure
- candidate CSV missing

- [ ] **Step 5: Run focused tests**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py -q
```

Expected:

```text
all tests in test_research_loop.py passed
```

- [ ] **Step 6: Commit**

Run:

```powershell
git add cli/research_loop.py tests/unit/test_research_loop.py
git commit -m "연구 루프에서 WFO 실행 경로를 제거한다" -m "discovery research를 빠른 백테스트 반복 연구 루프로 유지하기 위해 WFO 설정과 실행, 결합 평가를 research_loop에서 제거했다.

Constraint: WFO는 discovery promote와 cli.wfo 최종 검증 경로로 유지
Confidence: high
Scope-risk: moderate
Tested: python -m pytest tests/unit/test_research_loop.py -q"
```

---

### Task 2: Remove WFO Sections From Research Report

**Files:**
- Modify: `cli/research_report.py`
- Modify: `tests/unit/test_research_report.py`

- [ ] **Step 1: Write failing report tests**

Add to `tests/unit/test_research_report.py`:

```python
def test_research_report_has_no_wfo_sections():
    markdown = render_research_report_markdown(build_research_report(_result(), strategy_name='AutoResearch'))
    assert '## WFO 검증' not in markdown
    assert '## 최종 판단' not in markdown


def test_build_research_report_does_not_include_wfo_fields():
    result = _result()
    result['wfo_result'] = {'status': 'ok'}
    result['wfo_evaluation'] = {'passed': True}
    result['combined_evaluation'] = {'passed': True}
    report = build_research_report(result, strategy_name='AutoResearch')

    assert 'wfo_result' not in report
    assert 'wfo_evaluation' not in report
    assert 'combined_evaluation' not in report
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_research_report.py::test_research_report_has_no_wfo_sections tests/unit/test_research_report.py::test_build_research_report_does_not_include_wfo_fields -q
```

Expected:

```text
FAILED because report still contains WFO sections/fields
```

- [ ] **Step 3: Remove WFO report fields and Markdown**

Edit `cli/research_report.py`.

Remove fields from `build_research_report()`:

```python
        'wfo_result': result.get('wfo_result'),
        'wfo_evaluation': result.get('wfo_evaluation'),
        'combined_evaluation': result.get('combined_evaluation'),
```

Remove Markdown sections:

```python
## WFO 검증
## 최종 판단
```

Keep:

- Candidate
- Trade Set Comparison
- Baseline vs Candidate
- Excluded/New trades
- Promotion
- JSON save normalization
- save helper try/except behavior

- [ ] **Step 4: Remove WFO-only report test**

Remove this WFO-only test:

```python
test_render_research_report_markdown_contains_wfo_and_final_decision
```

- [ ] **Step 5: Run report tests**

Run:

```powershell
python -m pytest tests/unit/test_research_report.py -q
```

Expected:

```text
all tests in test_research_report.py passed
```

- [ ] **Step 6: Commit**

Run:

```powershell
git add cli/research_report.py tests/unit/test_research_report.py
git commit -m "연구 리포트에서 WFO 섹션을 제거한다" -m "discovery research 리포트를 빠른 백테스트 연구 결과에 집중하도록 WFO 검증과 최종 판단 섹션을 제거했다.

Constraint: WFO 결과 리포트는 discovery promote 경로에서 다루는 것이 역할상 적절함
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_report.py -q"
```

---

### Task 3: Remove WFO CLI Options From discovery research

**Files:**
- Modify: `cli/subcommands.py`
- Modify: `tests/unit/test_subcommands.py`

- [ ] **Step 1: Write failing CLI tests**

Add to `tests/unit/test_subcommands.py`:

```python
def test_discovery_research_parser_rejects_wfo_options():
    parser = create_subcommand_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([
            'discovery', 'research',
            'AutoResearchWfo',
            '--base-buy-strategy', 'BaseBuy',
            '--sell', 'BaseSell',
            '--start', '20250101',
            '--end', '20250131',
            '--run-wfo',
        ])


def test_discovery_research_handler_payload_has_no_wfo_keys():
    with patch('cli.ai_controller.AIBacktestController.research_strategy_once') as mock:
        mock.return_value = {'status': 'ok', 'report': {'strategy_name': 'AutoResearch01'}}
        exit_code = handle_subcommand([
            'discovery', 'research',
            'AutoResearch01',
            '--input', 'baseline.csv',
            '--base-buy-strategy', 'BaseBuy',
            '--sell', 'BaseSell',
            '--start', '20250101',
            '--end', '20250131',
        ])

    assert exit_code == 0
    payload = mock.call_args.args[0]
    assert 'run_wfo' not in payload
    assert 'train_window_days' not in payload
    assert 'param_space' not in payload
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py::test_discovery_research_parser_rejects_wfo_options tests/unit/test_subcommands.py::test_discovery_research_handler_payload_has_no_wfo_keys -q
```

Expected:

```text
FAILED because --run-wfo is still accepted and payload still has WFO keys
```

- [ ] **Step 3: Remove WFO args from `discovery research`**

In `cli/subcommands.py`, remove only these `disc_research` args:

```python
    disc_research.add_argument('--run-wfo', action='store_true', default=False)
    disc_research.add_argument('--train-window-days', type=int)
    disc_research.add_argument('--test-window-days', type=int)
    disc_research.add_argument('--step-days', type=int)
    disc_research.add_argument('--purge-days', type=int, default=0)
    disc_research.add_argument('--embargo-days', type=int, default=0)
    disc_research.add_argument('--objective', default='tpi')
    disc_research.add_argument('--wfo-method', choices=['grid', 'random'], default='grid')
    disc_research.add_argument('--wfo-max-iter', type=int, default=10)
    disc_research.add_argument('--promotion-preset', choices=['conservative', 'balanced', 'aggressive'], default='balanced')
    disc_research.add_argument('--param-space-json')
    disc_research.add_argument('--param-space-file')
```

Do not remove the same options from `discovery promote`, `wfo`, `optimize`, or other commands.

- [ ] **Step 4: Remove WFO payload and param-space handling from research handler**

In `_handle_discovery(parsed)` research branch, remove:

```python
        try:
            param_space = _load_param_space(parsed)
        except (json.JSONDecodeError, FileNotFoundError, OSError) as exc:
            ...
```

Remove payload keys:

```python
            'run_wfo': parsed.run_wfo,
            'train_window_days': parsed.train_window_days,
            'test_window_days': parsed.test_window_days,
            'step_days': parsed.step_days,
            'purge_days': parsed.purge_days,
            'embargo_days': parsed.embargo_days,
            'objective': parsed.objective,
            'wfo_method': parsed.wfo_method,
            'wfo_max_iter': parsed.wfo_max_iter,
            'promotion_preset': parsed.promotion_preset,
            'param_space': param_space,
```

- [ ] **Step 5: Remove WFO-only subcommand tests**

Remove tests that only validate research WFO options:

- `test_discovery_research_parser_accepts_wfo_options`
- `test_discovery_research_handler_passes_wfo_config`
- `test_discovery_research_handler_rejects_invalid_param_space_json`
- `test_discovery_research_handler_rejects_missing_param_space_file`

Keep existing non-WFO research parser/handler tests.

- [ ] **Step 6: Run tests and help smoke**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py -q
python stom_backtest.py discovery research --help
```

Expected:

```text
test_subcommands.py passes
help output has no --run-wfo and no --train-window-days
```

- [ ] **Step 7: Commit**

Run:

```powershell
git add cli/subcommands.py tests/unit/test_subcommands.py
git commit -m "연구 CLI에서 WFO 옵션을 제거한다" -m "discovery research를 빠른 조건식 연구 명령으로 유지하기 위해 WFO 옵션과 파라미터 공간 입력을 제거했다.

Constraint: WFO는 discovery promote와 cli.wfo에 남겨 최종 검증 역할로 분리
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_subcommands.py -q; python stom_backtest.py discovery research --help"
```

---

### Task 4: Update Logs And Verification

**Files:**
- Create: `docs/update_log/2026-04-17_remove_wfo_from_research_loop.md`

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py -q
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 2: Run broader research tests**

Run:

```powershell
python -m pytest tests/unit/test_research_metrics.py tests/unit/test_research_segments.py tests/unit/test_research_candidates.py tests/unit/test_research_compare.py tests/unit/test_research_promotion.py tests/unit/test_research_report.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py -q
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 3: Run full unit tests**

Run:

```powershell
python -m pytest tests/unit/ -q
```

Expected:

```text
all unit tests passed
```

- [ ] **Step 4: Run non-release sync verification**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
```

Expected:

```text
모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

- [ ] **Step 5: Create update log**

Create `docs/update_log/2026-04-17_remove_wfo_from_research_loop.md`:

```markdown
# 2026-04-17 discovery research WFO 연결 제거

## 개요

`discovery research`를 빠른 백테스트 반복 연구 루프로 유지하기 위해 WFO 연결을 제거했다.

## 변경 사항

- `discovery research --run-wfo` 제거
- research 루프 내부 WFO 설정/실행/평가 제거
- research 리포트 WFO 섹션 제거
- research WFO 테스트 제거/정리

## 유지되는 WFO 기능

- `cli/wfo.py`
- `AIBacktestController.walk_forward()`
- `discovery promote`
- `auto_discovery` WFO 검증 구조

## 검증

- `python -m pytest tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py -q`
- `python -m pytest tests/unit/ -q`
- `python scripts/verify_nonrelease_sync.py`

## 남은 리스크

- `discovery research`는 더 이상 직접 WFO 검증을 하지 않는다.
- 최종 후보 검증은 `discovery promote` 또는 별도 WFO 경로로 수행해야 한다.
- 다음 개발은 백테스트 반복 개선 루프이다.
```

- [ ] **Step 6: Commit**

Run:

```powershell
git add docs/update_log/2026-04-17_remove_wfo_from_research_loop.md
git commit -m "연구 루프 WFO 제거 기록을 남긴다" -m "discovery research에서 WFO 연결을 제거한 이유와 유지되는 WFO 경로, 검증 결과를 업데이트 로그로 남겼다.

Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/ -q; python scripts/verify_nonrelease_sync.py"
```

---

## Self-Review

Spec coverage:

- Remove WFO fields and execution from `research_loop.py`: Task 1.
- Remove WFO sections from reports: Task 2.
- Remove research WFO CLI options and payload: Task 3.
- Keep WFO elsewhere: Task 3 explicitly limits removal to `discovery research`.
- Update logs and verification: Task 4.

Known boundaries:

- This plan does not implement the next backtest iteration loop.
- This plan does not delete `cli/wfo.py`.
- This plan does not change `discovery promote`.

Completion scan:

- Each task includes concrete file paths, tests, implementation instructions, commands, expected results, and commit commands.
