# Wide v1 v5 Runtime Failure Recovery Design

## 1. Background

Wide v1 v5 `best_feature_mix_v5` was run with `candidate_count=10` to verify whether actual backtest CSV row-set representatives could be selected reliably after v4 proxy row-set diversification.

The run did not complete:

- `runtime-preflight` passed.
- Candidate CSV files were created for `cand001` through `cand006`, and later `cand008`.
- `cand007` was missing.
- After `cand008`, the parent and worker processes showed no useful CPU or file progress for more than ten minutes.
- `backtest\temp\wide_v1_iteration_v5_20260424.json` was not created.
- The decision was recorded as `HOLD_V5_RUNTIME_FAILURE`.

The failure does not prove that v5 generated poor conditions or insufficient actual row-set diversity. It proves that the CLI research loop lacks enough runtime recovery evidence when a long candidate run stalls or times out.

## 2. Decision

Use the **research loop checkpoint approach**.

The recovery layer will be added primarily around `cli\research_loop.py` and `discovery research` CLI plumbing. It will not perform a broad rewrite of `cli\runner.py` or the core STOM backtest engine in this iteration.

Chosen policy:

- Add explicit runtime output file support for `discovery research`.
- Persist candidate-level checkpoint JSON during execution.
- Treat individual candidate failures as structured candidate items.
- Continue after individual candidate failure.
- Abort after **3 consecutive candidate failures**.
- Write a structured final runtime JSON for both success and failure.
- Do not promote or run WFO from partial candidate CSVs.

## 3. Goals

1. A long research run must leave a useful JSON file even when it fails.
2. Candidate execution progress must be inspectable without relying on stdout capture.
3. Individual candidate failures must not automatically destroy the whole research run.
4. Repeated candidate failures must stop the run before wasting many more hours.
5. v5 actual row-set analysis must only run when enough successful candidates exist.
6. The next v5 run must be diagnosable from `runtime_output_path` alone.

## 4. Non-Goals

This design intentionally does not include:

- Deep refactoring of the backtest engine.
- Broad multiprocessing process-tree management changes in `cli\runner.py`.
- GUI behavior changes.
- New third-party dependencies.
- Automatic resume from a partial run.
- v6 condition generation expansion.
- promote or WFO execution.

Nested worker cleanup remains important, but this spec only records and preserves existing runner diagnostics. If runner cleanup remains faulty after this recovery layer, it should be handled in a separate narrow branch.

## 5. User-Facing CLI Contract

Add a research runtime output option:

```powershell
python .\stom_backtest.py discovery research WideV1IterationV5_20260424 `
  --runtime-output backtest\temp\wide_v1_iteration_v5_20260425.json `
  ...
```

The option should be specific to `discovery research` or equivalent research execution config. It should not change unrelated CLI commands.

Behavior:

- If `--runtime-output` is provided, the research loop writes JSON to that path.
- The file is overwritten at each checkpoint with the latest recoverable payload.
- Final stdout remains JSON for existing CLI compatibility.
- If `--runtime-output` cannot be written, the command returns structured error JSON and exits non-zero.

## 6. Architecture

### 6.1 Runtime Output Writer

Introduce a small internal writer concept for research runtime payloads.

Responsibilities:

- Resolve and create the parent directory for the runtime output path.
- Serialize JSON with `ensure_ascii=False`, `indent=2`, and `default=str`.
- Write atomically enough for normal CLI use by writing to a temporary sibling file and replacing the destination.
- Keep failures explicit.

This can be implemented as helper functions rather than a large class if that matches local style.

### 6.2 Candidate Checkpoint State

The research loop should maintain a checkpoint list in memory and persist it after meaningful events.

Recommended checkpoint events:

- `iteration_started`
- `analysis_completed`
- `candidate_pool_selected`
- `candidate_started`
- `candidate_succeeded`
- `candidate_failed`
- `candidate_failure_warning`
- `actual_rowset_selection_started`
- `actual_rowset_selection_completed`
- `iteration_completed`
- `iteration_aborted`

Each checkpoint should include:

- event name
- elapsed seconds
- candidate strategy name when relevant
- candidate index when relevant
- phase
- message
- consecutive failure count when relevant

### 6.3 Failure Policy

Add config fields:

- `runtime_output_path: str | None`
- `max_consecutive_candidate_failures: int = 3`

Policy:

- A candidate success resets consecutive failures to `0`.
- A candidate failure increments consecutive failures.
- At 2 consecutive failures, add a warning checkpoint but continue.
- At 3 consecutive failures, stop evaluating more candidates.
- The run returns:

```json
{
  "status": "error",
  "phase": "candidate_iteration_runtime_failure"
}
```

The response must include all candidates evaluated so far.

### 6.4 Actual Row-Set Gate

For `best_feature_mix_v5`, actual row-set representative selection should only run when the number of successful candidates is at least the requested `candidate_count`.

If success count is insufficient:

```json
{
  "actual_rowset_selection": {
    "status": "not_run",
    "reason": "insufficient_successful_candidates",
    "requested_count": 10,
    "successful_candidate_count": 7
  }
}
```

This prevents partial runs from being interpreted as valid actual row-set selection.

## 7. Data Flow

```text
CLI command
  -> parse --runtime-output and --max-consecutive-candidate-failures
  -> ResearchLoopConfig
  -> run_research_iteration()
  -> checkpoint iteration_started
  -> analyze baseline CSV
  -> checkpoint analysis_completed
  -> build v4/v5 candidate pool
  -> checkpoint candidate_pool_selected
  -> for each selected execution candidate:
       checkpoint candidate_started
       run candidate backtest
       on success: append ok candidate, checkpoint candidate_succeeded
       on failure: append error candidate, checkpoint candidate_failed
       persist runtime output
       if consecutive failures reaches 3: checkpoint iteration_aborted, return error JSON
  -> if enough successful candidates: run actual row-set selection
  -> otherwise actual_rowset_selection.status=not_run
  -> final runtime output
  -> stdout JSON
```

## 8. Runtime JSON Shape

The runtime JSON should keep the existing successful result fields and add recovery fields.

Required fields:

- `status`
- `phase`
- `message`
- `strategy_name`
- `config`
- `iteration_plan`
- `candidate_specs`
- `candidates`
- `best_candidate`
- `actual_rowset_selection`
- `cleanup_summary`
- `failure_policy`
- `checkpoint_summary`
- `checkpoints`

`failure_policy` example:

```json
{
  "max_consecutive_candidate_failures": 3,
  "consecutive_candidate_failures": 1,
  "total_candidate_failures": 2,
  "aborted": false,
  "abort_reason": null
}
```

Candidate error item example:

```json
{
  "index": 7,
  "strategy_name": "WideV1IterationV5_20260424__cand007",
  "status": "error",
  "phase": "candidate_backtest_timeout",
  "message": "candidate run failed or timed out",
  "consecutive_failure_count": 1,
  "candidate_result": {
    "checkpoint_status": "timeout",
    "last_checkpoint": "backtest_process_started",
    "cleanup_status": "process_killed"
  }
}
```

## 9. Error Handling

### 9.1 Candidate Success

On success:

- Verify candidate CSV path exists.
- Compare with baseline.
- Evaluate promotion/reference score.
- Append full candidate item.
- Reset consecutive failure count.
- Persist runtime output.

### 9.2 Recoverable Candidate Failure

Recoverable candidate failures include:

- candidate strategy generation failure
- candidate strategy save failure
- candidate backtest timeout
- candidate CSV missing
- comparison failure

On recoverable failure:

- Append `status=error` candidate item.
- Preserve `candidate_result` diagnostics.
- Preserve cleanup result.
- Increment consecutive failure count.
- Persist runtime output.
- Continue unless the consecutive failure limit is reached.

### 9.3 Abort Failure

Abort failures include:

- three consecutive candidate failures
- runtime output write failure
- baseline run failure
- analysis failure
- retention/candidate pool failure before candidate execution

Abort payloads must still include as much context as available.

### 9.4 Runtime Output Write Failure

Runtime output write failure is fatal because this feature exists to make the run recoverable.

Behavior:

- Return structured error JSON to stdout.
- Include the write path and exception message.
- Exit non-zero.

## 10. Testing Strategy

Use unit tests with mock controllers. Do not rely on a full long backtest in the implementation PR.

Required tests:

1. Runtime output file is written for a successful research iteration.
2. Runtime output file is written for a failed research iteration.
3. Candidate checkpoints are recorded in order.
4. A single candidate failure is appended and the next candidate continues.
5. Consecutive failures reset after a successful candidate.
6. Three consecutive candidate failures abort the iteration.
7. v5 actual row-set selection is not run when successful candidate count is below requested count.
8. Runtime output write failure returns `phase=runtime_output_write_failure`.
9. CLI parser passes `--runtime-output` and `--max-consecutive-candidate-failures` into `ResearchLoopConfig`.

Focused verification command:

```powershell
python -m pytest tests/unit/test_research_loop_runtime_recovery.py tests/unit/test_research_iteration_v5.py tests/unit/test_wide_v1_v5_analysis.py -q
```

Existing v5 tests must remain green.

## 11. Implementation Scope

Expected files:

- `cli\subcommands.py`
- `cli\research_loop.py`
- `tests\unit\test_research_loop_runtime_recovery.py`
- `docs\pr\2026-04-25_wide_v1_v5_runtime_failure_recovery_pr.md`

Possible supporting file if the helper grows large:

- `cli\research_runtime_output.py`

Prefer keeping helper code small and local unless tests show the behavior is easier to isolate in its own module.

## 12. Review Criteria

The implementation is acceptable when:

- `discovery research --runtime-output` writes a recoverable JSON file.
- Candidate progress is visible in the runtime file before final completion.
- Candidate failures are represented as data, not lost exceptions.
- Three consecutive candidate failures abort the run with a structured error.
- Partial success does not trigger actual row-set selection when success count is insufficient.
- Unit tests prove the policy without running a long v5 backtest.
- No backtest result artifacts under `backtest\csv`, `backtest\graph`, or `backtest\temp` are committed.

## 13. Next Step After This Spec

After review approval, create an implementation plan with:

```text
$writing-plans Wide v1 v5 runtime failure recovery 구현 계획 작성
```

