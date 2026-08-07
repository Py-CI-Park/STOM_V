# Task 5 Tick 09:20~09:25 Readiness Review

## Verdict

Tick late generation is contractually ready to create candidates, especially through TMAP. It is not yet proven that the system can repeatedly discover a profitable new 09:20~09:25 condition.

## LLM Generation Readiness

- Ready pieces: `time_cap_bucket_generation_enabled=True`, `time_cap_bucket_end_time=93000`, classification generation, filter gates, meaningful time-window guard, and complexity guard are wired into the generator path.
- The prompt explicitly names the 09:20~09:25 and 09:25~09:30 extended buckets and tells the model to test 09:20~09:25 as a standalone branch.
- Missing proof: no current successful LLM run shows a generated late-tick candidate with CSV, positive metrics, OOS, and WF evidence.

## TMAP Generation Readiness

- `tick_late_0920_0925_continuation.json` defaults to `entry_start=92000` and `entry_end=92500`.
- Template validation tests pass, so candidate creation is syntactically and scope-wise ready.
- Existing T2C/T2C3 evidence is promising:
  - `t2_corner_log.txt` has THETA and T2C candidates with positive/gate-true train results.
  - `wf_t2c3_aggregate.json` has 4 ok windows, policy total 9,882,323 vs baseline 8,933,830.
- Caveat: the aggregate is a sibling file, not `wf_t2c3_20260613/aggregate.json`; the evidence is useful but the runbook path contract should be fixed.

## THETA Separation

THETA is the current champion/baseline, not proof that 09:20~09:25 discovery is complete. THETA validates the seed-family baseline and the need for conservative OOS gates. It should be used as the comparison target for late-tick candidates.

## Required Future Evidence

1. 2-quarter smoke: run the exact 09:20~09:25 template on two separated train-like quarters before full sweep.
2. Full train sweep: sweep selected T2/T3 axes with canonical `--run-id` and `--manifest-out`.
3. 2022/2026 OOS: only after a candidate is frozen by predeclared criteria.
4. 4-window WF aggregate: create a canonical aggregate path and compare policy vs baseline.
5. Exact-window attribution: report whether the edge comes from 09:20~09:25, 09:25~09:30, or earlier extension spillover.

## Development Order

1. Fix runbook command contract for TMAP sweeps.
2. Run exact late-tick 2-quarter smoke.
3. Run full train sweep only if smoke avoids overfire and remains positive.
4. Produce canonical WF aggregate.
5. Feed surviving lessons into LLM prompt context for a second batch.

