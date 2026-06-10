# P2 Time-Bucket x Market-Cap 09:00..09:20 Preflight

## Verdict

Status: page-complete for P2 bounded preflight.

This proves the time-bucket x market-cap buy-generation path can produce a
generated candidate with real CSV+metrics inside the bounded `09:00..09:20`
research window. It is research-only evidence, not a human-level, OOS, or
production-readiness claim.

## Commands

```powershell
$env:PYTHONUTF8='1'; python -m ai_strategy_loop.scripts.tick_seed_timeout_probe run-loop --config-json .omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p2-timecap-900-920-config.json --run-id tick_p2_timecap_900_920_preflight_20260606 --wall-cap 600 --out .omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p2-timecap-900-920-result.json

$env:PYTHONUTF8='1'; python -m ai_strategy_loop.scripts.tick_seed_timeout_probe run-loop --config-json .omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p2-timecap-900-920-config.json --run-id tick_p2_timecap_900_920_preflight_guarded_20260606 --wall-cap 600 --out .omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p2-timecap-900-920-guarded-result.json

$env:PYTHONUTF8='1'; python -m ai_strategy_loop.scripts.tick_seed_timeout_probe run-loop --config-json .omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p2-timecap-900-920-config.json --run-id tick_p2_timecap_900_920_preflight_guarded2_20260606 --wall-cap 600 --out .omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p2-timecap-900-920-guarded2-result.json
```

## Runtime Results

| Run | Result | Interpretation |
|---|---:|---|
| `preflight_20260606` | gen0 seed CSV ok; gen1 timeout | meaningful time window existed, but generated buy code was too large |
| `preflight_guarded_20260606` | attempt 1 rejected; attempt 2 saved but timeout | first complexity gate worked, but threshold was still too loose |
| `preflight_guarded2_20260606` | gen1 CSV+metrics ok | stricter numeric budget produced a bounded candidate |

`guarded2` generated candidate:

| Metric | Seed gen0 | Generated gen1 |
|---|---:|---:|
| status | ok | ok |
| CSV | yes | yes |
| elapsed | 12.5s | 11.6s |
| score | 1.0 | 6.903167973883284 |
| gate_passed | true | true |
| profit | 229,983 | 76,127 |
| trades | 1 | 5 |
| MDD | 4.59 | 0.97 |
| payoff_ratio | 999.0 | 2.055147058823529 |
| max_hold_count | 1 | 3 |

Generated buy code structural budget:

| Field | Value |
|---|---:|
| non-comment code lines | 37 |
| AST if nodes | 16 |
| AST assignment nodes | 21 |
| time window | `90500 <= 시분초 < 91000` |
| market-cap band | `시가총액 < 5000` |
| complexity rejection reason | none |

CSV:

```text
backtest/csv\stock_bt_AILOOP_tick_p2_timecap_900_920_preflight_guarded2_20260606_g1_buy_20260606065007.csv
```

The CSV has 5 trades. The first rows include `SG글로벌`, `에이직랜드`,
`랩지노믹스`, `코위버`, then `SG글로벌` again; cumulative profit ends at
`76,127`.

## What Changed

- Added a default-OFF time-cap buy complexity gate in
  `ai_strategy_loop/brain/time_cap_bucket.py`.
- Hooked it into `ai_strategy_loop/brain/generator.py` only when
  `time_cap_bucket_generation_enabled=True` and `kind=="buy"`.
- Tightened the time-cap prompt with a bounded preflight budget:
  - 40 non-comment lines or fewer
  - 16 `if` nodes or fewer
  - 25 assignments or fewer
  - 8-12 strongest filters
- Increased this evidence config to `max_retries=2` so the model can retry after
  deterministic pre-save rejection.

## Verification

```powershell
$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_time_cap_bucket_generation.py -q
# 10 passed

$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_time_cap_bucket_generation.py tests/unit/test_time_window.py tests/unit/test_filter_gate.py tests/unit/test_sparse_positive_prompt.py -q
# 72 passed

$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_config.py tests/unit/test_launch_config.py tests/unit/test_state_contract.py tests/unit/test_state_schema_migration.py tests/unit/test_prompt_logging.py -q
# 122 passed

$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_tick_seed_timeout_probe.py tests/unit/test_warm_session_window.py -q
# 13 passed

$env:PYTHONUTF8='1'; python scripts/verify_nonrelease_sync.py
# pass

git diff --check
# pass; line-ending warnings only
```

## UltraQA Notes

- malformed input: config parser still rejects unsupported
  `time_cap_bucket_end_time`; tests cover this.
- prompt injection: generated strategy path remains token-checked; no
  `final_approval`, `export_winner`, live, or V3K action was invoked.
- cancel/resume: every runtime was launched through the scoped timeout probe
  with `--wall-cap 600`; cleanup was `null` because children exited.
- stale state: each run used a unique `run_id`; generations and prompt rows were
  read back from the current loop DB.
- dirty worktree: broad existing dirty tree was preserved; protected-path status
  was empty before runtime.
- hung or long commands: failed runs timed out inside warm-run timeout; wrappers
  stayed under wall cap.
- flaky tests: focused unit suites were rerun after red/green changes.
- misleading success: wrapper `status=ok` was not counted as P2 pass until gen1
  had CSV+metrics.
- repeated interruptions: plan, ledger, config, and evidence files now make P2
  resumable and auditable.

## Next

Proceed to P3: sell-strategy generation from existing forms. The current gen1
success used an AI-generated sell too, but P3 should study and harden sell
families deliberately before larger windows or multi-year runs.
