# P7 - Bounded Research Run Sequence

## Scope

P7 verifies the staged research sequence without starting an unbounded multi-year/OOS run:

1. Keep OOS disabled for discovery.
2. Confirm bounded `09:00..09:20` evidence from P2.
3. Run bounded `09:00..09:30` expansion on the same one-day TICK setup.
4. Confirm dashboard/status/code/diff/prompt visibility.
5. Reconfirm relaxed research criteria: losing periods can remain research-continuable, but promotion/human-level claims stay blocked.

## Inputs

Prior `09:00..09:20` evidence:

- Run: `tick_p2_timecap_900_920_preflight_guarded2_20260606`
- Generated gen1 CSV+metrics existed.
- Generated gen1: 5 trades, profit `76,127`, MDD `0.97`, payoff `2.055`, max hold `3`.
- Evidence: `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p2-timecap-900-920-preflight.md`

New `09:00..09:30` config:

- `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p7-timecap-900-930-config.json`
- Run ID: `tick_p7_timecap_900_930_bounded_20260606`
- Period: `2025-01-03..2025-01-03`
- Timeframe/window: `tick`, `09:00:00..09:30:00`
- Warm engines: `1`
- `bt_warm_run_timeout=180`
- `wall_cap=600`
- `time_cap_bucket_end_time=93000`
- `research_oos_mode=disabled`

Inspect artifact:

- `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p7-timecap-900-930-inspect.json`

## Run Result

Command:

```powershell
python -m ai_strategy_loop.scripts.tick_seed_timeout_probe run-loop --config-json .omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p7-timecap-900-930-config.json --run-id tick_p7_timecap_900_930_bounded_20260606 --wall-cap 600 --out .omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p7-timecap-900-930-result.json
```

Process result:

- status: `ok`
- timeout: `false`
- elapsed: `316.745s`
- cleanup: `null` because the owned process exited normally.

Generation result:

| Gen | Strategy | Status | Trades | Profit | MDD | CSV | Notes |
|---:|---|---|---:|---:|---:|---|---|
| 0 | `Tick_B_902_905_Update_2` / `Tick_S_902_905_Update_2` | ok | 1 | 229,983 | 4.59 | yes | seed reproduces in `09:00..09:30` |
| 1 | `AILOOP_tick_p7_timecap_900_930_bounded_20260606_g1_*` | error | 0 | 0 | 0 | no | generated strategy warm backtest timed out at 180s |

DB evidence:

- `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p7-db-generations-900-930.json`

Analysis snapshot:

- `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p7-analysis-snapshot-900-930.json`
- `csv_count=1`
- pooled trades: `1`
- edge ratio: `5.25`
- Because only the seed CSV exists, this is a reference signal, not a generated-candidate proof.

## Dashboard And Route Visibility

Dashboard:

- URL: `http://127.0.0.1:8770/ui/`
- Screenshot: `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p7-ui-after-900-930.png`
- DOM text: `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p7-ui-after-900-930-dom.txt`

Status artifacts:

- During run: `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p7-status-during-900-930.json`
- During gen1: `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p7-status-during-900-930-2.json`
- After completion: `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p7-status-after-900-930.json`

Completed status showed:

- `status=complete`
- `current_gen=2`
- `progress=100.0`
- `research_oos_mode=disabled`
- `time_cap_bucket_end_time=93000`
- active config includes tick timeframe, warm mode, engine count, period, time window, timeout, and recent logs.

Route artifacts:

- `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p7-strategy-code-gen1.json`: `code_status=ok`
- `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p7-strategy-diff-gen1.json`: `diff_status=ok`
- `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p7-prompts-gen1.json`
- `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p7-ai-context-gen1.json`: `prompt_count=3`

Research criteria route:

- `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p7-research-criteria-disabled.json`
- `label=OOS disabled`
- `claim_status=research-only`
- warning: `research/exploration only; not proof of human-level or production readiness.`

## Criteria Verification

Command:

```powershell
python -m pytest tests/unit/test_candidate_research_pool_v2.py tests/unit/test_promotion_diagnostics.py tests/unit/test_dashboard_strategy_prompt_frontend.py -q
```

Result:

- `22 passed in 0.91s`

Final focused wave:

```powershell
python -m pytest tests/unit/test_candidate_research_pool_v2.py tests/unit/test_promotion_diagnostics.py tests/unit/test_dashboard_strategy_prompt_frontend.py tests/unit/test_dashboard_engine_progress_contract.py -q
```

Result:

- `31 passed in 5.06s`

The tests cover:

- a candidate can remain in `research_continue=true` with one losing year when aggregate and recent-weighted results are positive.
- `promotion_claim=false` under the relaxed research policy.
- OOS-disabled is displayed as research-only.
- dashboard engine progress exposes period, tick/min, timeout, engine config, and logs.

## Safety Verification

```powershell
python scripts\verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json _v3k_sidecar/v3k_gui_settings.json ai_strategy_loop/state/research_analysis.db
```

Results:

- `verify_nonrelease_sync.py`: pass.
- `git diff --check`: pass, line-ending warnings only.
- Protected path status: empty.

## Adversarial QA

- malformed input: the route surface was queried with explicit run/gen; incorrect `strategy_code` param shape produced safe `missing_run`, then correct `run/gen` returned `code_status=ok`.
- prompt injection: generated prompts/routes stayed read-only; no `final_approval`, `export_winner`, live broker, or V3K action.
- cancel/resume: run used `tick_seed_timeout_probe` owned process with `wall_cap=600`; process exited normally.
- stale state: `/status` captured warm prepare, gen1 backtest, and complete states; UI screenshot after completion confirmed live dashboard visibility.
- dirty worktree: broad existing dirty tree preserved; no unrelated change reverted.
- hung or long commands: gen1 hit bounded `180s` warm timeout; wrapper returned within `600s`.
- flaky tests: focused criteria/dashboard suites reran after live run and passed.
- misleading success: process `status=ok` was not treated as generated-candidate success because gen1 had no CSV and timed out.
- repeated interruptions: plan, ledger, and evidence now record P7 completion boundary.

## Verdict

P7 complete as a bounded sequence.

What is good:

- `09:00..09:20` generated candidate succeeded in P2.
- `09:00..09:30` seed baseline reproduces quickly and profitably on the one-day bounded window.
- Dashboard now shows the run, engine settings, progress, generated code/diff/prompt, and OOS-disabled research-only status.

What is still blocked:

- `09:00..09:30` generated gen1 timed out at `180s` and produced no CSV.
- This does not yet prove trade-count expansion or human-level performance.
- No 2023~2025 long research run and no 2022/2026 fixed OOS should be started until the generated 09:30 timeout/complexity issue is reduced.

Recommended next work:

```text
$ulw-plan tick 09:00~09:30 generated strategy timeout reduction plan: use .omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p7-bounded-research-run-sequence.md and p7-timecap-900-930-result.stdout.txt as primary evidence. Reduce generated buy/sell complexity or split 09:20~09:30 into smaller bounded probes before retrying multi-year research. Preserve official engines, hard gates, backtest_graph, protected paths, final_approval/export_winner/live/V3K guardrails.
```
