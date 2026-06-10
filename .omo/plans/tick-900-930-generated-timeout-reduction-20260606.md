# Tick 09:00-09:30 Generated Strategy Timeout Reduction 20260606

## TL;DR

> **Summary**: Reduce the bounded `09:00..09:30` generated-strategy timeout before any 2024-2026 broad research. The last P7 run proved dashboard visibility and seed reproduction, but generated gen1 timed out at the `180s` warm backtest cap and produced no CSV.
> **Goal**: Make generated `09:00..09:30` candidates small and diagnosable enough to produce bounded CSV+metrics, or prove with evidence that the window must be split before broad research.
> **Deliverables**:
> - Runtime/complexity diagnostic artifact for the timed-out generated gen1.
> - Default-OFF or research-config-only prompt/guard improvements.
> - Split-probe configs for `09:20..09:25` and `09:25..09:30` before retrying full `09:00..09:30`.
> - Browser/API proof that dashboard still shows code, diff, prompt, status, logs, and OOS-disabled label.
> - Final decision card: retry full 09:30, keep split windows, or block broad research.
> **Critical Path**: P0 safety -> P1 timeout autopsy -> P2 prompt/guard refinement -> P3 split probes -> P4 full bounded retry -> P5 report/update.

## Canonical Inputs

- `docs/AGENT_HANDOFF.md`
- `docs/update_log/2026-06-05_direction_review_through_84acb6cb.md`
- `.omo/plans/condition-research-end-to-end-master-roadmap-20260606.md`
- `.omo/plans/tick-human-like-research-criteria-dashboard-20260605.md`
- `.omo/evidence/condition-research-end-to-end-master-roadmap-20260606/roadmap-status.md`
- `.omo/evidence/condition-research-end-to-end-master-roadmap-20260606/page-progress.md`
- `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p7-bounded-research-run-sequence.md`
- `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p7-timecap-900-930-result.stdout.txt`

## Current Evidence

`tick_p7_timecap_900_930_bounded_20260606`:

| Gen | Period | Window | Trades | Profit | MDD | CSV | Status |
|---:|---|---|---:|---:|---:|---|---|
| 0 seed | `2025-01-03` | `09:00..09:30` | 1 | 229,983 | 4.59 | yes | success |
| 1 generated | `2025-01-03` | generated first lines show `09:05..09:10` | 0 | 0 | 0 | no | warm timeout at 180s |

Important interpretation:

- The timeout is not solved by dashboard work; dashboard visibility already works for the bounded run.
- The generated buy code starts with a narrow 5-minute branch but still times out, so the next work must capture richer diagnostics and test split probes, not only lower line/if/assign caps.
- OOS is disabled for this discovery work. Any result remains research-only.

## Guardrails

- Do not edit official backtest engines.
- Do not edit hard-gate scoring/promotion contracts as a shortcut.
- Do not edit `backtest/graph`.
- New behavior must be default OFF or research config only.
- Do not use `final_approval`, `export_winner`, production export, live broker/KHOPENAPI, order wiring, or V3K gate advancement.
- Do not use blanket `taskkill`; only PID-scoped owned-process cleanup.
- Do not write protected runtime paths: `_database/`, `_database_v3k_shadow/`, `_log/`, `backup/`, `*.db`, `backtest/graph/`, `.omx/reports/`, `v3k_settings*.json`, `_v3k_sidecar/v3k_gui_settings.json`.
- Do not start 2024-2026 broad research until a generated bounded candidate produces CSV+metrics or a documented split-window decision exists.

## Implementation Scope

### Likely Files To Touch

| File | Purpose |
|---|---|
| `ai_strategy_loop/brain/time_cap_bucket.py` | Time-bucket labels, prompt helper, complexity diagnostics/limits |
| `ai_strategy_loop/brain/prompt.py` | Buy-only generation guidance for smaller probes |
| `ai_strategy_loop/brain/generator.py` | Prompt logging and retry reason metadata |
| `ai_strategy_loop/config.py` | Default-OFF/research-only knobs if a new split-probe knob is needed |
| `ai_strategy_loop/launch_config.py` | Dashboard config spec exposure if a config knob is added |
| `ai_strategy_loop/controller/loop.py` | Pass-through only if a new config knob is added |
| `ai_strategy_loop/scripts/tick_seed_timeout_probe.py` | Only if extra diagnostic output is required; preserve owned cleanup |
| `tests/unit/test_time_cap_bucket_generation.py` | Prompt/guard/config tests |
| `tests/unit/test_tick_seed_timeout_probe.py` | Probe safety/diagnostic tests |

### Explicitly Out Of Scope

- Multi-year 2024-2026 research run.
- Fixed 2022/2026 OOS promotion run.
- PBO/DSR implementation.
- Production strategy export.
- Live trading.

## Work Waves

## TODOs

- [x] P0 - Safety And Baseline Snapshot
- [x] P1 - Timeout Autopsy And Diagnostic Gap
- [x] P2 - Prompt And Guard Refinement
- [ ] P3 - Split Probe Configs Before Full Retry (blocked: provider HTTP 429 before generated code)
- [ ] P4 - Full 09:00..09:30 Bounded Retry (deferred until provider/fallback is available)
- [x] P5 - Decision Card And Master Roadmap Update
- [ ] Final Verification Wave

### P0 - Safety And Baseline Snapshot

**Do**

- Confirm dashboard health on `http://127.0.0.1:8770/health`.
- Capture branch, HEAD, dirty count, protected-path status.
- Confirm the current P7 artifacts exist.
- Record the active dashboard PID if port `8770` is listening.

**Evidence**

- `.omo/evidence/tick-900-930-generated-timeout-reduction-20260606/p0-safety-baseline.md`

**Acceptance**

- Protected-path status is empty.
- No process is killed.
- Dirty worktree is recorded as pre-existing unless this plan's later edits change files.

### P1 - Timeout Autopsy And Diagnostic Gap

**Do**

- Parse the timed-out gen1 buy/sell code from `/strategy_code` or local loop DB.
- Record:
  - non-comment line count
  - AST `if` count
  - assignment count
  - time-window bounds
  - market-cap conditions
  - banned token/scope check result
  - first 30 code lines
  - prompt feature flags
- Compare this against current `time_cap_bucket_complexity_reason`.
- Decide whether the current guard missed a runtime-expensive pattern.

**Evidence**

- `.omo/evidence/tick-900-930-generated-timeout-reduction-20260606/p1-timeout-autopsy.json`
- `.omo/evidence/tick-900-930-generated-timeout-reduction-20260606/p1-timeout-autopsy.md`

**Acceptance**

- The timeout is classified as one of:
  - `code_too_large_guard_missed`
  - `engine_runtime_pathology_despite_small_code`
  - `sell_side_exit_pathology`
  - `data/window_runtime_issue`
  - `unknown_needs_probe`
- Classification is evidence-backed, not guessed.

### P2 - Prompt And Guard Refinement

**Do**

- Keep existing default-OFF `time_cap_bucket_generation_enabled`.
- Prefer a research-only refinement over broad behavior change.
- If evidence says current guard missed risky code, add a small diagnostic or stricter guard in `time_cap_bucket.py`.
- If evidence says prompt pressure is the issue, adjust buy-only prompt text to require exactly one selected 5-minute window and one selected market-cap band for the 09:30 expansion.
- Keep sell prompts byte-stable unless P1 proves sell-side pathology.

**Tests**

```powershell
python -m pytest tests/unit/test_time_cap_bucket_generation.py -q
```

Add or update tests so they prove:

- default OFF remains byte-stable.
- `93000` prompt still includes `09:20~09:25` and `09:25~09:30`.
- new/refined guard rejects the P7 timeout-shaped pattern if classification says guard missed it.
- retry reason is visible in the next prompt.

**Evidence**

- `.omo/evidence/tick-900-930-generated-timeout-reduction-20260606/p2-prompt-guard-refinement.md`

**Acceptance**

- Tests pass.
- No official engine/hard-gate/protected-path edits.
- Change is limited to generation guidance/diagnostic guard, not production promotion logic.

### P3 - Split Probe Configs Before Full Retry

**Do**

- Create bounded research configs under evidence only:
  - `09:20..09:25`
  - `09:25..09:30`
- Use one-day or similarly bounded period first.
- Use low warm engine count and explicit wall cap.
- Keep `research_oos_mode=disabled`.
- Run through `ai_strategy_loop.scripts.tick_seed_timeout_probe run-loop`.

**Commands Template**

```powershell
python -m ai_strategy_loop.scripts.tick_seed_timeout_probe run-loop --config-json .omo/evidence/tick-900-930-generated-timeout-reduction-20260606/<config>.json --run-id <run_id> --wall-cap 600 --out .omo/evidence/tick-900-930-generated-timeout-reduction-20260606/<result>.json
```

**Evidence**

- `.omo/evidence/tick-900-930-generated-timeout-reduction-20260606/p3-split-probe-0920-0925.md`
- `.omo/evidence/tick-900-930-generated-timeout-reduction-20260606/p3-split-probe-0925-0930.md`
- `.omo/evidence/tick-900-930-generated-timeout-reduction-20260606/p3-provider-quota-blocker.md`
- stdout/stderr/result JSON for each run.

**Current Blocker - 2026-06-06**

- Both split probes ended inside the `600s` wall cap.
- Both gen0 seed runs returned `csv=no` and no metrics for the split window.
- Both gen1 generated runs failed before generated code existed because `gpt_auth` returned HTTP 429 `usage_limit_reached`.
- Alternate provider env preflight found no `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `CODEX_PROXY_BASE_URL`, or `CODEX_PROXY_API_KEY` in the current shell.
- P4 full retry is deferred because it would not answer the timeout question while provider generation is unavailable.

**Acceptance**

- Each split probe ends within wall cap.
- Each result is honestly classified:
  - generated CSV+metrics
  - seed-only success
  - generated timeout
  - empty/no-trade result
- No split-probe result is called human-level proof.

### P4 - Full 09:00..09:30 Bounded Retry

**Do**

- Retry full `09:00..09:30` only after P2/P3 evidence.
- Use bounded period and wall cap.
- Capture `/status`, `/strategy_code`, `/strategy_diff`, `/prompts`, `/ai_context_pack`, `/analysis_snapshot`, and UI screenshot/DOM.
- Keep OOS disabled and label research-only.

**Evidence**

- `.omo/evidence/tick-900-930-generated-timeout-reduction-20260606/p4-full-900-930-retry.md`
- `.omo/evidence/tick-900-930-generated-timeout-reduction-20260606/p4-ui.png`
- `.omo/evidence/tick-900-930-generated-timeout-reduction-20260606/p4-ui-dom.txt`

**Acceptance**

- Generated candidate produces CSV+metrics, or the plan records why full 09:30 must stay split.
- Dashboard shows the exact run, period, time window, config, prompt, diff, timeout/metrics, and OOS-disabled label.

### P5 - Decision Card And Master Roadmap Update

**Do**

- Write a decision card that chooses one of:
  - `PROCEED_TO_RECENT_RESEARCH`: generated full 09:30 CSV+metrics exists.
  - `PROCEED_WITH_SPLIT_WINDOWS`: split probes work but full window still times out.
  - `BLOCK_LONG_RESEARCH`: generated path still cannot produce bounded CSV+metrics.
- Update `.omo/evidence/condition-research-end-to-end-master-roadmap-20260606/roadmap-status.md` and `page-progress.md` as a routine status update, not a roadmap decision change.

**Evidence**

- `.omo/evidence/tick-900-930-generated-timeout-reduction-20260606/p5-decision-card.md`

**Acceptance**

- Next command is explicit.
- Human-level/seed-superior claim remains blocked unless strict validation exists.

## Verification Wave

Run at minimum:

```powershell
python -m pytest tests/unit/test_time_cap_bucket_generation.py tests/unit/test_tick_seed_timeout_probe.py -q
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json _v3k_sidecar/v3k_gui_settings.json
```

If dashboard files or routes are touched, also run focused dashboard tests and capture browser proof:

```powershell
python -m pytest tests/unit/test_dashboard_strategy_prompt_frontend.py tests/unit/test_dashboard_engine_progress_contract.py -q
```

## Report Format

Every report must include:

| Section | Required Content |
|---|---|
| Master roadmap progress | M0-M11 table, current percentages, evidence |
| Current page progress | P0-P5 table with complete/partial/blocked |
| Performance | run ID, period, window, OOS mode, profit, return, MDD, trades, payoff, CSV status |
| Evidence | tests, HTTP/API, browser screenshot, protected status, cleanup |
| Risks | timeout, trade count, overfit, OOS disabled, token bloat, complexity |
| Next command | one executable `$start-work` or `$ulw-plan` command |

## Recommended Start Command

```text
$start-work tick-900-930-generated-timeout-reduction-20260606
```

## Expected Unlock

```text
P0 safety
 -> P1 timeout autopsy
 -> P2 prompt/guard refinement
 -> P3 09:20~09:25 and 09:25~09:30 split probes
 -> P4 full 09:00~09:30 bounded retry
 -> P5 decision card
 -> only then decide whether 2024/2025/available 2026 research is allowed
```
