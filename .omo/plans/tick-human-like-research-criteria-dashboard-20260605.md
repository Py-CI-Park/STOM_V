# Tick Human-Like Research Criteria And Dashboard 20260605

## TL;DR
> **Summary**: Reframe the condition-research system around human-like upward equity discovery: explain OOS, make OOS optional/very loose for research, generate 5-minute time-bucket x market-cap buy/sell strategy families, expose live code/diff/prompt history on the dashboard, and persist richer CSV/variable analysis for future feedback.
> **Deliverables**:
> - Plain-Korean OOS/overfit/glossary definitions in docs and dashboard.
> - Two-tier validation policy plus OOS modes: loose `research_continue` vs strict `promotion_claim`, with research-time OOS allowed to be `disabled`.
> - Time-bucket x market-cap generation plan for `09:00..09:20` first, optional `09:20..09:30`.
> - Active buy/sell code, strategy diff, AI prompt, and history panel near the fitness trend.
> - Persisted analysis DB for CSV-derived variable/correlation/segment effects.
> - Bounded verification plan before any long run.
> **Critical Path**: P0 -> P1 -> P2 -> P3/P4 -> P5 -> P6 -> P7 -> Final

## Context

The user wants the system to work more like human condition research:

- A good strategy does not make money every year or every period.
- If the full equity curve is upward, and recent 2024/2025/2026 behavior is strong enough, the research should continue.
- Humans often try many condition edits and only occasionally discover one good setup.
- The dashboard should show what the AI is doing in real time so the user can judge and suggest improvements.
- Time, market cap, and variables should be analyzed together because condition quality depends on context.

Latest blockers and facts:

- Dashboard is active at `http://127.0.0.1:8770/ui/`.
- Strict 2022/2026 OOS rejected the last sparse-positive candidate. That is a valid promotion rejection, not proof the research direction is useless.
- `C_T_900_920_U2_B/S` timeout was isolated to the C_T buy side, statically the pre-`09:05` branch for `2025-01-03 09:02..09:05`.
- Current long-run work should remain blocked until bounded preflight can produce CSV+metrics.

## Definitions To Implement

### OOS Meaning

OOS means **Out Of Sample**: a period or year that was not used to choose, tune, or reselect the strategy. In this project it is the “unseen exam period.”

OOS is not a rule that every year must be profitable. It is a guard against this failure:

```text
train period looks excellent
→ unseen period collapses
→ the strategy was probably fitted to the train window
```

### OOS / OSS Clarification

The user may write `OSS`, but the intended validation concept here is `OOS` unless explicitly corrected.

For discovery research, OOS must be optional. If OOS blocks useful exploration too early, run with OOS disabled and label the result as research-only. OOS-disabled results can guide the next condition idea, but they cannot be used to claim human-level, seed-superior, or production-ready performance.

### Relaxed Research Overfit Criteria

Use two tiers:

| Tier | Purpose | Loose Or Strict | Interpretation |
|---|---|---|---|
| `research_continue` | decide whether to keep studying a family | loose | yearly losses are allowed if the full equity curve is upward |
| `promotion_claim` | claim human-level/seed-superior/production readiness | strict | requires fixed OOS, slippage, trade sufficiency, and advisory overfit checks |

Default `research_continue` pass criteria:

- Aggregate profit across selected period is positive.
- Full-period cumulative return curve ends higher than it starts.
- Recent-weighted result is positive, with 2026/2025 weighted more than 2024.
- Loss periods are allowed if drawdown is controlled and the curve recovers.
- Trade count is sufficient to avoid one-trade luck.
- Either win-day ratio is reasonable or payoff is large enough to compensate lower hit rate.

Default `promotion_claim` remains stricter:

- No OOS-after-the-fact reselection.
- Fixed OOS comparison is recorded.
- Slippage remains unresolved until tested.
- PBO/DSR remains advisory blocker until implemented.
- No `final_approval` or `export_winner` without explicit user approval.

### OOS Mode Policy

Add an explicit research OOS mode:

| Mode | Meaning | Allowed Use | Claim Status |
|---|---|---|---|
| `disabled` | do not run or use OOS for candidate rejection | broad discovery, time/cap/variable exploration, trade-count expansion | research-only, no human-level claim |
| `advisory` | show OOS if available, but do not reject a research family solely from OOS | normal research continuation | research-only unless strict checks later pass |
| `promotion_only` | run fixed OOS only after candidate is frozen | seed/human-superiority review | may support claim if all strict checks pass |

Default for this plan's exploratory runs: `research_oos_mode=disabled` until bounded CSV+metrics and dashboard visibility are stable. Switch to `advisory` only when the user wants to see OOS as reference. Switch to `promotion_only` only for a frozen candidate.

Dashboard labeling must be explicit:

```text
OOS disabled: research/exploration only. This result is not proof of human-level or production readiness.
```

## Scope

### Include

- Criteria/docs/dashboard explanation.
- Time-bucket x market-cap generation design and implementation plan.
- Buy/sell condition generation using existing DB strategy forms as references.
- Live dashboard display for active code, diff, current AI prompt, prompt history, and strategy history.
- CSV-derived analysis persistence and visualization.
- Glossary/tooltips for edge ratio, payoff, MDD, OOS, PBO, DSR, slippage, win-day ratio, and drawdown.
- OOS mode config, label, and acceptance tests for `disabled`, `advisory`, and `promotion_only`.
- Bounded preflight and dashboard QA.

### Exclude

- Official backtest engine edits.
- Hard-gate edits to `compute_fitness`.
- `backtest/graph` edits.
- Production strategy DB export.
- Live broker/KHOPENAPI/V3K gate actions.
- Blanket process kill.
- Human-level claim before strict verification.
- Treating OOS-disabled research results as final proof.

## TODOs

- [x] P0 - Safety, Dashboard, And Criteria Baseline

  **Do**:
  - Confirm dashboard is active; if port `8770` is empty, start `python -m ai_strategy_loop --port 8770`.
  - Capture current branch, HEAD, dirty status, Boulder state, protected path status.
  - Read latest evidence:
    - `.omo/evidence/ct-seed-branch-workload-isolation-20260605/p5-decision-card.md`
    - `.omo/evidence/tick-sparse-positive-generation-improvement-20260604/p7-decision-card.md`
    - `docs/update_log/2026-06-05_direction_review_through_84acb6cb.md`

  **Acceptance**:
  - Dashboard health is recorded.
  - Current OOS/overfit wording gap is documented.
  - No runtime process is killed.

- [x] P1 - OOS / Overfit / Human-Like Criteria Layer

  **Do**:
  - Add a read-only criteria module or artifact builder that produces:
    - `research_oos_mode`
    - `research_continue`
    - `promotion_claim`
    - `reason_codes`
    - `recent_weighted_profit`
    - `equity_upward`
    - `win_day_ratio`
    - `payoff_compensation`
  - Keep existing hard-gate scoring unchanged.
  - Add plain Korean explanations for OOS, OOS-disabled research, and relaxed overfit criteria.

  **Default Decisions**:
  - Research window priority: available `2024`, `2025`, `2026`.
  - Recent weights: `2024=1.0`, `2025=1.2`, `2026=1.5`.
  - Initial discovery mode: `research_oos_mode=disabled`.
  - Research pass allows one or more losing years if aggregate and recent-weighted curves are positive.
  - Promotion claim does not use relaxed criteria.
  - OOS can be `advisory` or `promotion_only`, but cannot reject a candidate in `disabled` mode.

  **Acceptance**:
  - Unit tests prove losing year can still be `research_continue=true`.
  - Unit tests prove OOS-disabled mode does not reject a research candidate from missing/weak OOS.
  - Dashboard shows the OOS-disabled warning label when this mode is active.
  - Unit tests prove `promotion_claim=false` until strict checks exist.

- [x] P2 - Time-Bucket x Market-Cap Buy Strategy Generation

  **Do**:
  - Build generation mode for 5-minute buckets:
    - `09:00..09:05`
    - `09:05..09:10`
    - `09:10..09:15`
    - `09:15..09:20`
    - optional after passing bounded preflight: `09:20..09:25`, `09:25..09:30`
  - Combine each time bucket with market-cap bands from existing segment analysis.
  - Make the time baseline dynamic: start with `09:00..09:20`, optionally extend to `09:30`, and allow later reconfiguration if evidence supports a different start/end.
  - Make market-cap bands dynamic: use existing DB/segment bands first, then adjust by observed trade count, return, and drawdown.
  - Use existing buy strategy forms from loop DB and `_database/strategy.db` as examples.
  - Generate branch-structured buy code, but keep each branch small enough to avoid the current C_T timeout pattern.

  **Acceptance**:
  - Generated buy code contains meaningful time windows, not no-op windows.
  - Strategy pre-save gate detects span and no-op time branches.
  - Bounded `09:00..09:20` preflight can produce CSV+metrics before expanding to `09:30`.

  **Progress 2026-06-05**:
  - Implemented default-OFF `time_cap_bucket_generation_enabled` and `time_cap_bucket_end_time`.
  - Verified prompt/config/loop/prompt-log/dashboard config-spec plumbing.
  - Evidence: `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p2-time-cap-bucket-generation-partial.md`.
  - P2 remains unchecked until a real bounded `09:00..09:20` preflight produces CSV+metrics.

  **Progress 2026-06-06**:
  - Added default-OFF time-cap buy complexity guard for bounded preflight.
  - Guarded retry rejected overlarge candidates before save/backtest.
  - Bounded `09:00..09:20` run `tick_p2_timecap_900_920_preflight_guarded2_20260606` produced generated gen1 CSV+metrics.
  - Generated gen1: `90500 <= 시분초 < 91000`, `시가총액 < 5000`, 37 non-comment lines, 16 AST if nodes, 21 assignments, 5 trades, profit `76,127`, MDD `0.97`, gate passed.
  - Evidence: `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p2-timecap-900-920-preflight.md`.

- [x] P3 - Sell Strategy Generation From Existing Forms

  **Do**:
  - Study existing sell formulas such as tick sell, C_T sell, min sell, and human reference sell patterns.
  - Generate sell logic covering:
    - profit taking
    - stop loss
    - trailing give-back
    - 체결강도 weakening
    - moving-average/trend break
    - time/hold duration exit
  - Avoid overfitting sell logic to one branch.

  **Acceptance**:
  - Sell strategy can pair with control buy and produce CSV+metrics.
  - Sell code is visible in dashboard and strategy diff.

  **Progress 2026-06-06**:
  - Reviewed tick, C_T, min-simple, min-study, and generated sell forms.
  - Generated sell `AILOOP_tick_p2_timecap_900_920_preflight_guarded2_20260606_g1_sell` covers profit taking, stop loss, trailing give-back, order-flow/체결 약화, trend break, and hold-time exits.
  - Paired generated buy/sell run produced CSV+metrics: 5 trades, profit `76,127`, MDD `0.97`, payoff `2.055`.
  - Live dashboard `/strategy_code`, `/strategy_diff`, `/prompts`, and `/ai_context_pack` returned `200 OK` for the run/gen.
  - Evidence: `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p3-sell-strategy-generation-forms.md`.

- [x] P4 - Dashboard Live Code / Diff / Prompt / History Panel

  **Do**:
  - Place active buy/sell names, code viewer, previous diff, current prompt, and prompt history above or near the fitness trend.
  - Ensure invalid/missing strategy code does not show HTTP 404 in UI.
  - Show history:
    - current generation
    - previous generation
    - prompt text head
    - prompt sha
    - model
    - retry/prior error if present
  - Keep dashboard always-on behavior in run instructions.

  **Acceptance**:
  - `/strategy_code`, `/strategy_diff`, `/prompts`, and `/ai_context_pack` all return non-breaking responses.
  - UI shows empty/stale state honestly.
  - Playwright or browser smoke confirms `/ui/` renders the panel.

  **Progress 2026-06-06**:
  - Verified live `/strategy_code`, `/strategy_diff`, `/prompts`, and `/ai_context_pack` return `200 OK` for `tick_p2_timecap_900_920_preflight_guarded2_20260606`, gen 1.
  - Playwright browser smoke captured `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p4-ui-smoke.png`.
  - DOM confirmed active strategy code/diff status appears before the fitness trajectory.
  - Focused dashboard frontend/backend tests passed.
  - Evidence: `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p4-dashboard-live-code-diff-prompt-history.md`.

- [x] P5 - CSV Analysis Persistence And Visualization

  **Do**:
  - Create read-only analysis extraction from backtest CSV into persisted analysis tables.
  - Persist:
    - time bucket
    - market cap band
    - B_* variable summaries
    - return/profit impact
    - MFE/MAE
    - payoff
    - win/loss
    - day-level profit/loss
    - compound feature interactions
  - Add dashboard panels:
    - variable correlation heatmap
    - time x market cap x return matrix
    - variable effect ranking
    - edge ratio explanation and values
    - win-day/payoff relationship

  **Acceptance**:
  - Analysis DB writes are local research state only and not production DB writes.
  - Missing CSV produces empty UI, not crash.
  - Dashboard explains each metric in Korean.

  **Progress 2026-06-06**:
  - Added `/analysis_snapshot` as an explicit local research snapshot endpoint.
  - Persisted CSV-derived reports into `ai_strategy_loop/state/research_analysis.db` only, with `analysis_snapshots` and `analysis_rows`.
  - Persisted B_* correlation/range rows, compound feature interactions, time/market-cap/edge rows, generation metrics including payoff/max-hold, and day-level P/L.
  - Existing Research Lab visualization routes stayed live: `/variable_correlation`, `/edge_ratio`, `/feature_importance`.
  - Dashboard on `8770` was safely restarted after confirming run status was complete so the new route is visible.
  - Evidence: `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p5-csv-analysis-persistence-visualization.md`.

- [x] P6 - Glossary And Human-Readable Metric Explanations

  **Do**:
  - Add glossary cards/tooltips for:
    - OOS
    - overfit
    - MDD
    - payoff
    - edge ratio
    - MFE/MAE
    - slippage
    - PBO
    - DSR
    - win-day ratio
    - recent-weighted score
  - Put explanations where the user sees the metric, not only in docs.

  **Acceptance**:
  - No unexplained advanced metric appears in dashboard.
  - Glossary text distinguishes research signal from production proof.

  **Progress 2026-06-06**:
  - Added dashboard `Metric Glossary` panel under the research criteria banner.
  - Covered OOS, overfit, MDD, payoff, edge ratio, MFE/MAE, slippage, PBO, DSR, win-day ratio, and recent-weighted score.
  - Expanded wiki glossary and static dashboard tests.
  - Playwright confirmed the panel renders on `http://127.0.0.1:8770/ui/`.
  - Evidence: `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p6-glossary-human-readable-metric-explanations.md`.

- [x] P7 - Bounded Research Run Sequence

  **Do**:
  - Do not start full 2023-2025 or 2022/2026 OOS first.
  - First run:
    - timeframe: tick
    - buy window: `09:00..09:20`
    - short bounded period
    - engine count low
    - wall cap
  - Expand only after CSV+metrics and dashboard visibility pass.
  - Then test:
    - `09:00..09:20`
    - `09:00..09:30`
    - 2024/2025/available 2026 recent-weighted research pass
    - OOS-disabled discovery first
    - fixed OOS for promotion only after a candidate is frozen

  **Acceptance**:
  - Research pass can continue with a losing year if aggregate recent-weighted curve is upward.
  - OOS-disabled runs are reported as research-only and never as proof.
  - Human-level claim remains blocked unless strict promotion checks pass.

  **Progress 2026-06-06**:
  - Confirmed prior bounded `09:00..09:20` generated candidate still provides CSV+metrics evidence.
  - Ran bounded `09:00..09:30` expansion `tick_p7_timecap_900_930_bounded_20260606` with `research_oos_mode=disabled`.
  - Seed gen0 reproduced quickly with 1 trade, profit `229,983`, MDD `4.59`.
  - Generated gen1 strategy code/diff/prompt were visible, but warm backtest timed out at `180s` and produced no CSV.
  - Dashboard `/status` and `/ui/` showed complete run state, engine config, timeout, tick timeframe, and OOS-disabled research-only status.
  - Evidence: `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p7-bounded-research-run-sequence.md`.

- [x] Final Verification

  **Commands**:
  ```powershell
  curl.exe -sS http://127.0.0.1:8770/health
  $env:PYTHONUTF8='1'; python -m pytest tests/unit/test_dashboard_strategy_diff.py tests/unit/test_dashboard_strategy_prompt_frontend.py tests/unit/test_variable_correlation.py -q
  $env:PYTHONUTF8='1'; python -m pytest tests/unit/test_tick_seed_timeout_probe.py tests/unit/test_dashboard_engine_progress_contract.py -q
  python scripts/verify_nonrelease_sync.py
  git diff --check
  git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json _v3k_sidecar/v3k_gui_settings.json
  ```

  **Acceptance**:
  - Dashboard health is normal.
  - No protected source/path violation.
  - No production export/final/live action.
  - User-facing final report separates:
    - infrastructure progress
    - research candidate progress
    - strict promotion status

  **Progress 2026-06-06**:
  - Dashboard health returned `ok`.
  - Final focused tests passed: `19 passed`, `17 passed`, plus P7 criteria/dashboard `31 passed`.
  - `verify_nonrelease_sync.py` passed.
  - `git diff --check` passed with line-ending warnings only.
  - Protected path status was empty.
  - Evidence: `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/final-verification.md`.

## Recommended Execution Command

```text
$start-work tick-human-like-research-criteria-dashboard-20260605
```

## Notes

- This plan intentionally relaxes overfit criteria only for research continuation. OOS can be disabled for discovery if that helps find broader time/cap/variable ideas. This does not relax the standard for claiming human-level, seed-superior, or production-ready results.
- The first implementation should prefer `09:00..09:20`. Add `09:20..09:30` only after bounded preflight avoids the current C_T-style timeout.
- The dashboard must stay active during execution and final reports must include dashboard health.
