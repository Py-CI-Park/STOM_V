# Research WFO Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add optional Walk-Forward validation to `discovery research` so a generated candidate strategy can be checked against forward/OOS windows before being treated as promotion-ready.

**Architecture:** Reuse existing WFO assets instead of creating a new validation engine. Extend `ResearchLoopConfig` and `run_research_once()` with opt-in WFO fields, call the existing controller `walk_forward()` and `evaluate_walk_forward_result()` methods, then write combined research/WFO decisions into the existing research report. Add CLI options as thin parser/handler glue.

**Tech Stack:** Python 3.11, existing STOM CLI modules, `cli.wfo`, `cli.promotion`, `AIBacktestController`, pytest.

---

## Scope Check

This plan implements only Phase 2 validation:

```text
research candidate
-> candidate backtest/comparison
-> optional WFO
-> WFO evaluation
-> combined decision
-> report
```

Out of scope:

- opportunity-universe logging
- AI/API condition generation
- condition mutation/removal/branch editing
- default backtest path changes
- `discovery promote` behavior changes

## File Structure

- Modify `cli/research_loop.py`
  - Add WFO fields to `ResearchLoopConfig`.
  - Add `_wfo_settings_dict()`, `_evaluate_wfo()`, and `_combined_evaluation()`.
  - Call WFO only when `run_wfo=True`.

- Modify `cli/research_report.py`
  - Add WFO and final decision sections to report dict and Markdown.

- Modify `cli/subcommands.py`
  - Add `discovery research` WFO CLI options.
  - Pass WFO config into `research_strategy_once()`.

- Modify tests:
  - `tests/unit/test_research_loop.py`
  - `tests/unit/test_research_report.py`
  - `tests/unit/test_subcommands.py`

No core `backtest/`, `trade/`, or GUI files should change.

---

### Task 1: Research Loop WFO Configuration Gates

**Files:**
- Modify: `cli/research_loop.py`
- Test: `tests/unit/test_research_loop.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_research_loop.py`:

```python
def test_research_loop_rejects_wfo_without_candidate(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(monkeypatch)

    result = run_research_once(
        ResearchLoopConfig(
            name='WfoNeedsCandidate',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_wfo=True,
            train_window_days=20,
            test_window_days=5,
        ),
        DummyController(None),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'wfo_config'
    assert 'run_candidate' in result['message']


def test_research_loop_rejects_wfo_without_train_or_test_windows(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(monkeypatch)

    result = run_research_once(
        ResearchLoopConfig(
            name='WfoNeedsWindows',
            baseline_csv=str(baseline),
            run_candidate=True,
            base_buy_strategy='BaseBuy',
            run_wfo=True,
        ),
        DummyController(str(baseline)),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'wfo_config'
    assert 'train_window_days' in result['message']
    assert 'test_window_days' in result['message']
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_research_loop_rejects_wfo_without_candidate tests/unit/test_research_loop.py::test_research_loop_rejects_wfo_without_train_or_test_windows -q
```

Expected:

```text
TypeError: ResearchLoopConfig.__init__() got an unexpected keyword argument 'run_wfo'
```

- [ ] **Step 3: Implement WFO config fields and gate**

Modify `cli/research_loop.py`.

Add imports:

```python
from dataclasses import asdict, dataclass, field
```

Replace the existing dataclass import if needed.

Add fields to `ResearchLoopConfig`:

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

Add helper:

```python
def _validate_wfo_config(config: ResearchLoopConfig) -> dict | None:
    """Return a structured error when WFO settings are incomplete."""
    if not config.run_wfo:
        return None
    if not config.run_candidate:
        return _error('wfo_config', 'run_wfo requires run_candidate=True')
    if config.train_window_days is None or config.test_window_days is None:
        return _error('wfo_config', 'run_wfo requires train_window_days and test_window_days')
    return None
```

In `run_research_once()`, after baseline CSV is known and before candidate strategy preparation, add:

```python
    wfo_config_error = _validate_wfo_config(config)
    if wfo_config_error is not None:
        return {**wfo_config_error, 'baseline_csv': baseline_csv, 'baseline_result': baseline_result}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_research_loop_rejects_wfo_without_candidate tests/unit/test_research_loop.py::test_research_loop_rejects_wfo_without_train_or_test_windows -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Run the full research loop tests**

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
git commit -m "연구 루프 WFO 설정 게이트를 추가한다" -m "research 명령에서 WFO를 선택 실행할 수 있도록 설정 필드를 추가하고, 후보 전략 생성 없이 WFO가 실행되지 않도록 방어했다.

Constraint: WFO는 비용이 크므로 명시 옵션일 때만 실행
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_loop.py -q"
```

---

### Task 2: Candidate WFO Execution And Evaluation

**Files:**
- Modify: `cli/research_loop.py`
- Test: `tests/unit/test_research_loop.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_research_loop.py`:

```python
class WfoController(DummyController):
    def __init__(self, candidate_csv, wfo_result=None, wfo_eval=None):
        super().__init__(candidate_csv)
        self.walk_forward_calls = []
        self.wfo_result = wfo_result or {'status': 'ok', 'summary': {'round_count': 2, 'success_rate': 1.0, 'mean_oos_metric': 0.5, 'mean_trade_count': 30, 'zero_trade_rounds': 0}, 'rounds': []}
        self.wfo_eval = wfo_eval or {'status': 'ok', 'passed': True, 'reasons': [], 'summary': {'round_count': 2, 'success_rate': 1.0, 'mean_oos_metric': 0.5, 'avg_trade_count': 30, 'zero_trade_rounds': 0}}

    def walk_forward(self, config_dict, param_space, **settings):
        self.walk_forward_calls.append({'config': config_dict, 'param_space': param_space, 'settings': settings})
        return self.wfo_result

    def evaluate_walk_forward_result(self, walk_forward_result, **criteria):
        return self.wfo_eval


def test_research_loop_runs_wfo_and_combines_success(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    candidate = tmp_path / 'candidate.csv'
    _write_trade_csv(baseline, name='A')
    _write_trade_csv(candidate, name='B')
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)

    controller = WfoController(str(candidate))
    result = run_research_once(
        ResearchLoopConfig(
            name='WfoCandidate',
            baseline_csv=str(baseline),
            base_buy_strategy='BaseBuy',
            sell_strategy='BaseSell',
            start_date=20250101,
            end_date=20250131,
            run_candidate=True,
            run_wfo=True,
            train_window_days=20,
            test_window_days=5,
            param_space={'avg_time': [60]},
        ),
        controller,
    )

    assert result['status'] == 'ok'
    assert result['wfo_result']['status'] == 'ok'
    assert result['wfo_evaluation']['passed'] is True
    assert result['combined_evaluation']['mode'] == 'research_plus_wfo'
    assert result['combined_evaluation']['passed'] is True
    assert controller.walk_forward_calls[0]['config']['buy_strategy'] == 'WfoCandidate'
    assert controller.walk_forward_calls[0]['config']['sell_strategy'] == 'BaseSell'
    assert controller.walk_forward_calls[0]['param_space'] == {'avg_time': [60]}
    assert controller.walk_forward_calls[0]['settings']['train_window_days'] == 20
    assert controller.walk_forward_calls[0]['settings']['test_window_days'] == 5


def test_research_loop_combined_evaluation_fails_when_wfo_fails(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    candidate = tmp_path / 'candidate.csv'
    _write_trade_csv(baseline, name='A')
    _write_trade_csv(candidate, name='B')
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)

    controller = WfoController(
        str(candidate),
        wfo_eval={'status': 'ok', 'passed': False, 'reasons': ['mean_oos_metric<0.0'], 'summary': {'zero_trade_rounds': 0}},
    )
    result = run_research_once(
        ResearchLoopConfig(
            name='WfoReject',
            baseline_csv=str(baseline),
            base_buy_strategy='BaseBuy',
            sell_strategy='BaseSell',
            run_candidate=True,
            run_wfo=True,
            train_window_days=20,
            test_window_days=5,
        ),
        controller,
    )

    assert result['status'] == 'ok'
    assert result['wfo_evaluation']['passed'] is False
    assert result['combined_evaluation']['passed'] is False
    assert 'wfo:mean_oos_metric<0.0' in result['combined_evaluation']['reasons']
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_research_loop_runs_wfo_and_combines_success tests/unit/test_research_loop.py::test_research_loop_combined_evaluation_fails_when_wfo_fails -q
```

Expected:

```text
KeyError: 'wfo_result'
```

- [ ] **Step 3: Implement WFO helpers**

Modify `cli/research_loop.py`.

Add imports:

```python
from cli.promotion import resolve_promotion_criteria
```

Add helpers:

```python
def _wfo_settings_dict(config: ResearchLoopConfig) -> dict:
    """Build keyword arguments for controller.walk_forward()."""
    return {
        'train_window_days': config.train_window_days,
        'test_window_days': config.test_window_days,
        'step_days': config.step_days,
        'purge_days': config.purge_days,
        'embargo_days': config.embargo_days,
        'objective': config.objective,
        'method': config.wfo_method,
        'max_iter': config.wfo_max_iter,
    }


def _wfo_eval_criteria(config: ResearchLoopConfig) -> dict:
    """Resolve WFO promotion criteria from existing presets."""
    criteria = resolve_promotion_criteria(config.promotion_preset, config.promotion_criteria)
    return {
        'min_rounds': criteria['min_rounds'],
        'min_success_rate': criteria['min_success_rate'],
        'min_mean_oos_metric': criteria['min_mean_oos_metric'],
        'min_avg_trade_count': criteria['min_avg_trade_count'],
    }


def _combined_evaluation(research_promotion: dict | None, wfo_evaluation: dict | None, run_wfo: bool) -> dict:
    """Combine CSV-comparison and WFO pass/fail evidence."""
    research_passed = bool((research_promotion or {}).get('passed'))
    wfo_passed = bool((wfo_evaluation or {}).get('passed')) if run_wfo else None
    reasons = []
    for reason in (research_promotion or {}).get('reasons') or []:
        reasons.append(f'research:{reason}')
    if run_wfo:
        for reason in (wfo_evaluation or {}).get('reasons') or []:
            reasons.append(f'wfo:{reason}')
    passed = research_passed and (wfo_passed if run_wfo else True)
    if not passed and not reasons:
        if not research_passed:
            reasons.append('research:not_passed')
        if run_wfo and not wfo_passed:
            reasons.append('wfo:not_passed')
    return {
        'mode': 'research_plus_wfo' if run_wfo else 'research_only',
        'passed': passed,
        'research_passed': research_passed,
        'wfo_passed': wfo_passed,
        'reasons': reasons,
    }
```

After `promotion = evaluate_research_candidate(comparison)` in `run_research_once()`, add:

```python
    wfo_result = None
    wfo_evaluation = None
    if config.run_wfo:
        wfo_config = _candidate_config_dict(config)
        wfo_result = controller.walk_forward(wfo_config, config.param_space, **_wfo_settings_dict(config))
        if wfo_result.get('status') != 'ok':
            return _error(
                'wfo_execution',
                wfo_result.get('message', 'WFO execution failed'),
                baseline_csv=baseline_csv,
                candidate_csv=candidate_csv,
                candidate=candidate,
                wfo_result=wfo_result,
            )
        wfo_evaluation = controller.evaluate_walk_forward_result(wfo_result, **_wfo_eval_criteria(config))
        if wfo_evaluation.get('status') != 'ok':
            return _error(
                'wfo_evaluation',
                wfo_evaluation.get('message', 'WFO evaluation failed'),
                baseline_csv=baseline_csv,
                candidate_csv=candidate_csv,
                candidate=candidate,
                wfo_result=wfo_result,
                wfo_evaluation=wfo_evaluation,
            )
    combined = _combined_evaluation(promotion, wfo_evaluation, config.run_wfo)
```

Include these keys in the final `_build_result()` payload:

```python
        'wfo_result': wfo_result,
        'wfo_evaluation': wfo_evaluation,
        'combined_evaluation': combined,
```

For non-WFO candidate runs, also set `combined_evaluation = _combined_evaluation(promotion, None, False)`.

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_research_loop_runs_wfo_and_combines_success tests/unit/test_research_loop.py::test_research_loop_combined_evaluation_fails_when_wfo_fails -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Run full research-loop tests**

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
git commit -m "연구 루프에 WFO 검증을 연결한다" -m "후보 전략 백테스트 이후 선택적으로 WFO를 실행하고, CSV 비교 결과와 WFO 평가를 결합하는 판단 값을 추가했다.

Constraint: WFO는 opt-in으로 유지하고 기존 research 빠른 흐름을 깨지 않음
Confidence: high
Scope-risk: moderate
Tested: python -m pytest tests/unit/test_research_loop.py -q"
```

---

### Task 3: WFO Error Phases

**Files:**
- Modify: `cli/research_loop.py`
- Test: `tests/unit/test_research_loop.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_research_loop.py`:

```python
def test_research_loop_returns_wfo_execution_phase(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    candidate = tmp_path / 'candidate.csv'
    _write_trade_csv(baseline, name='A')
    _write_trade_csv(candidate, name='B')
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)

    controller = WfoController(str(candidate), wfo_result={'status': 'error', 'message': 'wfo failed'})
    result = run_research_once(
        ResearchLoopConfig(
            name='WfoExecutionFail',
            baseline_csv=str(baseline),
            base_buy_strategy='BaseBuy',
            run_candidate=True,
            run_wfo=True,
            train_window_days=20,
            test_window_days=5,
        ),
        controller,
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'wfo_execution'
    assert 'wfo failed' in result['message']


def test_research_loop_returns_wfo_evaluation_phase(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    candidate = tmp_path / 'candidate.csv'
    _write_trade_csv(baseline, name='A')
    _write_trade_csv(candidate, name='B')
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)

    controller = WfoController(str(candidate), wfo_eval={'status': 'error', 'message': 'evaluation failed'})
    result = run_research_once(
        ResearchLoopConfig(
            name='WfoEvalFail',
            baseline_csv=str(baseline),
            base_buy_strategy='BaseBuy',
            run_candidate=True,
            run_wfo=True,
            train_window_days=20,
            test_window_days=5,
        ),
        controller,
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'wfo_evaluation'
    assert 'evaluation failed' in result['message']
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py::test_research_loop_returns_wfo_execution_phase tests/unit/test_research_loop.py::test_research_loop_returns_wfo_evaluation_phase -q
```

Expected before Task 2 implementation:

```text
KeyError or assertion failure because WFO errors are not structured
```

If Task 2 already made them pass, document that in the commit body and still keep the tests.

- [ ] **Step 3: Ensure implementation returns structured phases**

Confirm `run_research_once()` returns:

```python
return _error('wfo_execution', ...)
```

when `controller.walk_forward()` returns non-ok.

Confirm it returns:

```python
return _error('wfo_evaluation', ...)
```

when `controller.evaluate_walk_forward_result()` returns non-ok.

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m pytest tests/unit/test_research_loop.py -q
```

Expected:

```text
all tests in test_research_loop.py passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add cli/research_loop.py tests/unit/test_research_loop.py
git commit -m "연구 WFO 오류 단계를 구분한다" -m "WFO 실행 실패와 평가 실패를 각각 구조화된 phase로 반환하도록 테스트와 오류 처리를 보강했다.

Constraint: CLI에서 자동 복구와 원인 파악이 가능하도록 phase를 분리해야 함
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_loop.py -q"
```

---

### Task 4: Research Report WFO Sections

**Files:**
- Modify: `cli/research_report.py`
- Test: `tests/unit/test_research_report.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/unit/test_research_report.py`:

```python
def test_render_research_report_markdown_contains_wfo_and_final_decision():
    result = _result()
    result['wfo_result'] = {
        'status': 'ok',
        'summary': {
            'round_count': 2,
            'success_rate': 1.0,
            'mean_oos_metric': 0.5,
            'mean_trade_count': 30,
            'zero_trade_rounds': 0,
        },
    }
    result['wfo_evaluation'] = {'status': 'ok', 'passed': True, 'reasons': [], 'summary': {'avg_trade_count': 30}}
    result['combined_evaluation'] = {
        'mode': 'research_plus_wfo',
        'passed': True,
        'research_passed': True,
        'wfo_passed': True,
        'reasons': [],
    }

    report = build_research_report(result, strategy_name='AutoResearch')
    markdown = render_research_report_markdown(report)

    assert '## WFO 검증' in markdown
    assert '## 최종 판단' in markdown
    assert 'research_plus_wfo' in markdown
    assert report['wfo_result']['summary']['round_count'] == 2
    assert report['combined_evaluation']['passed'] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/test_research_report.py::test_render_research_report_markdown_contains_wfo_and_final_decision -q
```

Expected:

```text
AssertionError: '## WFO 검증' not in markdown
```

- [ ] **Step 3: Update report dict and renderer**

Modify `build_research_report()` to include:

```python
        'wfo_result': result.get('wfo_result'),
        'wfo_evaluation': result.get('wfo_evaluation'),
        'combined_evaluation': result.get('combined_evaluation'),
```

Modify `render_research_report_markdown()` by adding before or after Promotion:

```python
    lines.extend(['', '## WFO 검증'])
    wfo_result = report.get('wfo_result') or {}
    wfo_summary = wfo_result.get('summary') or {}
    wfo_evaluation = report.get('wfo_evaluation') or {}
    if wfo_result:
        lines.append(f"- 실행 여부: 실행됨")
        lines.append(f"- 라운드 수: {wfo_summary.get('round_count')}")
        lines.append(f"- 성공률: {wfo_summary.get('success_rate')}")
        lines.append(f"- 평균 OOS 지표: {wfo_summary.get('mean_oos_metric')}")
        lines.append(f"- 평균 거래 수: {wfo_summary.get('mean_trade_count')}")
        lines.append(f"- 무거래 라운드 수: {wfo_summary.get('zero_trade_rounds')}")
        lines.append(f"- WFO 통과 여부: {wfo_evaluation.get('passed')}")
        for reason in wfo_evaluation.get('reasons') or []:
            lines.append(f"- WFO 탈락 사유: {reason}")
    else:
        lines.append("- 실행 여부: 실행 안 함")

    lines.extend(['', '## 최종 판단'])
    combined = report.get('combined_evaluation') or {}
    if combined:
        lines.append(f"- 판단 모드: {combined.get('mode')}")
        lines.append(f"- CSV 비교 통과 여부: {combined.get('research_passed')}")
        lines.append(f"- WFO 통과 여부: {combined.get('wfo_passed')}")
        lines.append(f"- 최종 통과 여부: {combined.get('passed')}")
        for reason in combined.get('reasons') or []:
            lines.append(f"- 최종 탈락 사유: {reason}")
    else:
        lines.append("- none")
```

The existing JSON save normalization should automatically handle non-finite WFO fields.

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m pytest tests/unit/test_research_report.py -q
```

Expected:

```text
all tests in test_research_report.py passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add cli/research_report.py tests/unit/test_research_report.py
git commit -m "연구 리포트에 WFO 판단을 표시한다" -m "WFO 검증 요약과 CSV 비교/WFO 결합 최종 판단을 한국어 연구 리포트에 포함했다.

Constraint: 후보 채택 판단의 근거가 리포트에서 누락되면 안 됨
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_research_report.py -q"
```

---

### Task 5: Discovery Research WFO CLI

**Files:**
- Modify: `cli/subcommands.py`
- Test: `tests/unit/test_subcommands.py`

- [ ] **Step 1: Write failing parser/handler tests**

Append to `tests/unit/test_subcommands.py`:

```python
def test_discovery_research_parser_accepts_wfo_options():
    parser = create_subcommand_parser()
    args = parser.parse_args([
        'discovery', 'research',
        'AutoResearchWfo',
        '--base-buy-strategy', 'BaseBuy',
        '--sell', 'BaseSell',
        '--start', '20250101',
        '--end', '20250131',
        '--run-candidate',
        '--run-wfo',
        '--train-window-days', '20',
        '--test-window-days', '5',
        '--step-days', '5',
        '--purge-days', '1',
        '--embargo-days', '1',
        '--objective', 'tpi',
        '--wfo-method', 'random',
        '--wfo-max-iter', '3',
        '--promotion-preset', 'conservative',
        '--param-space-json', '{"avg_time":[60]}',
    ])

    assert args.discovery_action == 'research'
    assert args.run_wfo is True
    assert args.train_window_days == 20
    assert args.test_window_days == 5
    assert args.wfo_method == 'random'
    assert args.wfo_max_iter == 3
    assert args.promotion_preset == 'conservative'
    assert args.param_space_json == '{"avg_time":[60]}'


def test_discovery_research_handler_passes_wfo_config(capsys):
    with patch('cli.ai_controller.AIBacktestController.research_strategy_once') as mock:
        mock.return_value = {'status': 'ok', 'report': {'strategy_name': 'AutoResearchWfo'}}
        exit_code = handle_subcommand([
            'discovery', 'research',
            'AutoResearchWfo',
            '--base-buy-strategy', 'BaseBuy',
            '--sell', 'BaseSell',
            '--start', '20250101',
            '--end', '20250131',
            '--run-candidate',
            '--run-wfo',
            '--train-window-days', '20',
            '--test-window-days', '5',
            '--param-space-json', '{"avg_time":[60]}',
        ])

    assert exit_code == 0
    payload = mock.call_args.args[0]
    assert payload['run_candidate'] is True
    assert payload['run_wfo'] is True
    assert payload['train_window_days'] == 20
    assert payload['test_window_days'] == 5
    assert payload['param_space'] == {'avg_time': [60]}
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py::test_discovery_research_parser_accepts_wfo_options tests/unit/test_subcommands.py::test_discovery_research_handler_passes_wfo_config -q
```

Expected:

```text
SystemExit: 2
```

because WFO options are not registered.

- [ ] **Step 3: Add parser args and handler payload**

In `create_subcommand_parser()`, add to `disc_research`:

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

In the `research` handler payload, add:

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
            'param_space': _load_param_space(parsed),
```

Use existing `_load_param_space(parsed)`.

- [ ] **Step 4: Run targeted tests and CLI help**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py::test_discovery_research_parser_accepts_wfo_options tests/unit/test_subcommands.py::test_discovery_research_handler_passes_wfo_config -q
python stom_backtest.py discovery research --help
```

Expected:

```text
2 passed
```

Help output contains:

```text
--run-wfo
--train-window-days
--test-window-days
```

- [ ] **Step 5: Run related tests**

Run:

```powershell
python -m pytest tests/unit/test_subcommands.py tests/unit/test_research_loop.py -q
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 6: Commit**

Run:

```powershell
git add cli/subcommands.py tests/unit/test_subcommands.py
git commit -m "연구 WFO CLI 옵션을 연결한다" -m "discovery research 명령에서 WFO 검증 옵션과 파라미터 공간 입력을 연구 루프로 전달하게 했다.

Constraint: WFO는 명시적으로 --run-wfo를 지정한 경우에만 실행
Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/test_subcommands.py tests/unit/test_research_loop.py -q"
```

---

### Task 6: Integration Verification And Update Log

**Files:**
- Create: `docs/update_log/2026-04-17_research_wfo_validation.md`

- [ ] **Step 1: Run focused WFO research tests**

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

- [ ] **Step 3: Run full unit suite**

Run:

```powershell
python -m pytest tests/unit/ -q
```

Expected:

```text
all unit tests passed
```

- [ ] **Step 4: Run non-release sync guardrails**

Run:

```powershell
python scripts/verify_nonrelease_sync.py
```

Expected:

```text
모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

- [ ] **Step 5: Create update log**

Create `docs/update_log/2026-04-17_research_wfo_validation.md`:

```markdown
# 2026-04-17 research WFO validation

## 개요

`discovery research` 후보 전략 검증에 선택형 WFO 검증을 연결했다.

## 변경 사항

- `--run-wfo` 옵션 추가
- WFO train/test window 옵션 추가
- 기존 WFO/프로모션 기준 재사용
- 연구 리포트에 WFO 검증과 최종 판단 섹션 추가
- CSV 비교 통과와 WFO 통과를 모두 반영한 combined evaluation 추가

## 검증

- `python -m pytest tests/unit/ -q`
- `python scripts/verify_nonrelease_sync.py`

## 남은 리스크

- WFO는 과최적화 위험을 줄이지만 수익을 보장하지 않는다.
- 실제 장기간 데이터에 대한 운영 파일럿은 별도 수행이 필요하다.
- 기회집합 로그와 조건식 변형은 후속 Phase이다.
```

- [ ] **Step 6: Commit**

Run:

```powershell
git add docs/update_log/2026-04-17_research_wfo_validation.md
git commit -m "연구 WFO 검증 연결 기록을 남긴다" -m "discovery research WFO 검증 연결의 변경 사항과 검증 결과, 남은 리스크를 업데이트 로그로 남겼다.

Confidence: high
Scope-risk: narrow
Tested: python -m pytest tests/unit/ -q; python scripts/verify_nonrelease_sync.py"
```

---

## Self-Review

Spec coverage:

- Optional `--run-wfo`: Task 5.
- Existing WFO reuse: Task 2.
- Combined research/WFO decision: Task 2.
- Structured WFO error phases: Task 1 and Task 3.
- Report additions: Task 4.
- CLI options and payload: Task 5.
- Verification and update log: Task 6.

Known boundaries:

- This plan does not implement opportunity-universe logging.
- This plan does not generate new strategy seeds.
- This plan does not mutate existing conditions.
- WFO remains opt-in and can be expensive.

Completion scan:

- Every code task includes test code, implementation code, expected commands, and commit commands.
- The plan keeps changes isolated to `cli/research_loop.py`, `cli/research_report.py`, `cli/subcommands.py`, tests, and one update log.
