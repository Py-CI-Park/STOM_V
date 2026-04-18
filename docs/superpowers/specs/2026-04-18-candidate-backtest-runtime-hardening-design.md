# 2026-04-18 candidate backtest runtime hardening design

## Context

`STOM_Version_2U_C` now has a fast `discovery research` loop:

```text
baseline CSV/backtest
-> result analysis
-> filter candidate generation
-> optional filtered candidate strategy
-> optional candidate backtest
-> baseline/candidate comparison
-> research report
```

WFO was removed from `discovery research` because it made the research path too heavy. After that change, a real pilot showed a second runtime problem:

```text
discovery research ... --run-candidate
-> candidate strategy was saved
-> candidate backtest timed out
-> candidate strategy had to be deleted manually
```

Preview mode works:

```text
discovery research ... --input baseline.csv
-> status ok
-> candidate expression generated
```

The bottleneck is now the candidate backtest stage, not WFO.

## Position In The Overall Roadmap

This phase is an execution-stability phase between the current research foundation and the future iteration engine.

```text
Completed:
- segment research loop foundation
- WFO role separation

Current phase:
- candidate backtest runtime hardening

Next phase:
- backtest iteration research loop
```

The future iteration loop will run many candidates. It cannot be reliable if a single candidate timeout leaves strategy DB residue or gives no structured failure report.

## Goals

- Make candidate backtest execution observable before it starts.
- Allow candidate backtest date range to be shorter than the baseline analysis range.
- Allow candidate backtest timeout to be controlled from `discovery research`.
- Automatically clean up failed or timed-out candidate strategies by default.
- Allow failed candidate strategies to be kept only when explicitly requested.
- Return structured failure phases and cleanup results.
- Add candidate runtime information to the research report.
- Keep core `backtest/`, `trade/`, and GUI paths unchanged.

## Non-Goals

- Do not implement the full multi-candidate iteration loop yet.
- Do not add opportunity-universe logging.
- Do not reintroduce WFO to `discovery research`.
- Do not change default backtest CLI behavior.
- Do not change `cli.runner.run_backtest()` unless a later plan proves it is required.

## Proposed CLI Additions

Add candidate-only controls to `discovery research`:

```text
--candidate-start YYYYMMDD
--candidate-end YYYYMMDD
--candidate-timeout SECONDS
--candidate-plan-only
--keep-failed-candidate
```

Example:

```powershell
python stom_backtest.py discovery research AutoResearchPilot01 `
  --input backtest/csv/stock_bt_Min_B_Study_251227_20260415220536.csv `
  --base-buy-strategy Min_B_Study_251227 `
  --sell Min_S_Study_251227 `
  --start 20250407 `
  --end 20250418 `
  --timeframe min `
  --run-candidate `
  --candidate-start 20250407 `
  --candidate-end 20250408 `
  --candidate-timeout 300
```

## Configuration Contract

Extend `ResearchLoopConfig`:

```text
candidate_start_date: int | None = None
candidate_end_date: int | None = None
candidate_timeout: int | None = None
candidate_plan_only: bool = False
keep_failed_candidate: bool = False
```

Rules:

- `candidate_start_date` defaults to `start_date`.
- `candidate_end_date` defaults to `end_date`.
- `candidate_timeout` defaults to the existing backtest timeout behavior.
- `candidate_plan_only=True` prevents strategy save and candidate backtest execution.
- `keep_failed_candidate=False` means failed/timed-out candidate strategies are deleted automatically.

## Candidate Plan

After expressions are generated and before any strategy DB write, build a `candidate_plan`.

Example:

```json
{
  "strategy_name": "AutoResearchPilot01",
  "base_buy_strategy": "Min_B_Study_251227",
  "sell_strategy": "Min_S_Study_251227",
  "expression": "시가총액 <= 2793.5",
  "candidate_start_date": 20250407,
  "candidate_end_date": 20250408,
  "candidate_timeout": 300,
  "will_save_strategy": true,
  "will_run_backtest": true
}
```

The plan should be present in every result:

- preview
- plan-only
- candidate backtest success
- candidate backtest failure
- candidate timeout
- comparison failure

## Plan-Only Mode

`candidate_plan_only=True` means:

```text
baseline CSV analysis runs
candidate expression is generated
candidate_plan is returned
candidate strategy is not saved
candidate backtest is not run
comparison is not run
promotion is not run
```

Return:

```text
status = ok
phase = candidate_plan
```

This gives the user a cheap way to confirm the candidate expression and candidate execution scope before spending backtest time.

## Candidate Backtest Config

Candidate backtest config should be derived from the normal baseline config but override candidate-specific fields.

```text
buy_strategy = candidate strategy name
sell_strategy = configured sell strategy
start_date = candidate_start_date or start_date
end_date = candidate_end_date or end_date
timeout = candidate_timeout if provided
```

The baseline analysis CSV is not changed by candidate date overrides.

This distinction matters:

```text
baseline analysis range:
  broad historical result CSV

candidate verification range:
  smaller pilot backtest range
```

## Cleanup Policy

Default:

```text
failed or timed-out candidate strategies are deleted
```

Keep only when:

```text
--keep-failed-candidate
```

Cleanup should run for:

- candidate backtest failure
- candidate backtest timeout
- candidate CSV missing
- comparison failure

Cleanup should not run for:

- candidate plan-only
- failures before candidate strategy save
- successful candidate backtest and comparison
- `keep_failed_candidate=True`

Cleanup result should not hide the original failure.

Example:

```json
{
  "status": "error",
  "phase": "candidate_backtest_timeout",
  "message": "백테스트 시간 초과 (300초)",
  "cleanup": {
    "attempted": true,
    "strategy_name": "AutoResearchPilot01",
    "reason": "candidate_backtest_timeout",
    "status": "ok",
    "action": "deleted"
  }
}
```

If cleanup fails:

```json
{
  "status": "error",
  "phase": "candidate_backtest_timeout",
  "message": "백테스트 시간 초과 (300초)",
  "cleanup": {
    "attempted": true,
    "status": "error",
    "message": "..."
  }
}
```

## Timeout Phase Detection

Candidate backtest failures should be classified:

```text
candidate_backtest_timeout
candidate_backtest
```

Timeout detection:

```text
message contains "시간 초과"
or message contains "timeout" case-insensitive
```

This allows the future iteration loop to treat timeout candidates differently from normal strategy errors.

## Report Additions

Add a section:

```text
## Candidate Runtime
- 후보 백테스트 실행 여부
- 후보 백테스트 시작일
- 후보 백테스트 종료일
- 후보 timeout
- 후보 전략 저장 여부
- cleanup 실행 여부
- cleanup 결과
```

Report dict should include:

```text
candidate_plan
cleanup
```

The report must remain useful when:

- plan-only
- candidate timeout
- candidate backtest failure
- candidate CSV missing
- comparison failure

## Error Phases

Use existing phases where possible and add specific timeout phase:

```text
candidate_plan
candidate_strategy
candidate_backtest
candidate_backtest_timeout
candidate_csv_missing
comparison
candidate_cleanup
```

Cleanup failure should be recorded inside `cleanup`, not replace the main phase unless the only failure is cleanup itself.

## Testing Strategy

Unit tests should cover:

- `candidate_plan_only` does not save strategy.
- `candidate_plan_only` does not run backtest.
- `candidate_plan` is present in preview and candidate runs.
- `candidate_start_date` and `candidate_end_date` override candidate run config.
- `candidate_timeout` is passed to candidate run config.
- timeout message returns `phase="candidate_backtest_timeout"`.
- timeout triggers cleanup by default.
- backtest failure triggers cleanup by default.
- missing candidate CSV triggers cleanup.
- comparison failure triggers cleanup.
- `keep_failed_candidate=True` skips cleanup.
- successful candidate comparison does not cleanup.
- report includes `Candidate Runtime`.
- CLI passes candidate runtime options to `research_strategy_once()`.

Focused verification:

```powershell
python -m pytest tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py -q
```

Full verification:

```powershell
python -m pytest tests/unit/ -q
python scripts/verify_nonrelease_sync.py
```

## Risks

- Candidate backtest may still be slow even with shorter date ranges.
- Timeout cleanup deletes failed candidate strategies by default, so debugging requires `--keep-failed-candidate`.
- Candidate date range can be too short to be statistically meaningful. It is a runtime pilot control, not final validation.
- This phase does not solve multi-candidate iteration yet; it creates the safety layer needed for it.

## Acceptance Criteria

- Candidate preview remains fast and unchanged.
- Candidate plan-only returns a candidate plan and performs no DB write.
- Candidate backtest can use a shorter date range than baseline analysis.
- Candidate backtest timeout is user-configurable.
- Failed/timed-out candidates are automatically deleted by default.
- Cleanup results are included in JSON/report output.
- `discovery research` remains WFO-free.
- Core backtest/trade files remain unchanged.
