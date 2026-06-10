# Current Page And Dashboard Progress - 2026-06-06

## Active Detailed Plan

Plan: `.omo/plans/tick-900-930-generated-timeout-reduction-20260606.md`

| Step | Status | Evidence | What It Proves | Remaining Caveat |
|---|---|---|---|---|
| P0 Safety and baseline snapshot | complete | `p0-safety-baseline.md` | Dashboard, branch/HEAD, protected status, P7 source artifacts were checked before timeout work | Recheck before future runs |
| P1 Timeout autopsy and diagnostic gap | complete | `p1-timeout-autopsy.json`, `p1-timeout-autopsy.md` | P7 generated code shape alone did not explain the timeout; split probes were needed | Classification remained `unknown_needs_probe` until P3 |
| P2 Prompt and guard refinement | complete as no-code decision | `p2-prompt-guard-refinement.md` | Existing guard tests pass and no blind prompt/guard change was made before split evidence | Does not fix the P7 timeout by itself |
| P3 Split probe configs before full retry | blocked by provider quota | `p3-split-probe-0920-0925.md`, `p3-split-probe-0925-0930.md`, `p3-provider-quota-blocker.md` | Both split probes ended within wall cap; generated code did not exist because `gpt_auth` hit HTTP 429 | Need provider reset, `openrouter`/`codex_proxy`, or approved offline fallback |
| P4 Full 09:00..09:30 bounded retry | pending / do not run now | n/a | n/a | Would likely reproduce provider 429 before answering timeout question |
| P5 Decision card and master roadmap update | partial | `p3-provider-quota-blocker.md`, roadmap status update | Current decision: do not proceed to broad 2024-2026 research yet | Needs provider/fallback decision |
| Final verification wave | pending | n/a | n/a | Run after P4/P5 are resolved |

Previous completed page: `.omo/plans/tick-human-like-research-criteria-dashboard-20260605.md`

| Step | Status | Evidence | What It Proves | Remaining Caveat |
|---|---|---|---|---|
| P0 Safety/dashboard baseline | complete | `p0-safety-baseline.md` | Dashboard and guardrails were checked before implementation | Recheck before each new run |
| P1 OOS/overfit/human-like criteria | complete | `p1-oos-overfit-human-like-criteria.md` | OOS-disabled/advisory/promotion-only policy exists and is dashboard-visible | Research-only mode is not a claim |
| P2 Time x market-cap buy generation | complete for bounded 09:00..09:20 | `p2-timecap-900-920-preflight.md` | Generated candidate produced CSV+metrics in bounded setup | Does not prove 09:30 or multi-year behavior |
| P3 Sell generation from existing forms | complete for bounded pair | `p3-sell-strategy-generation-forms.md` | Sell logic paired with generated buy and produced metrics | Needs broader period validation |
| P4 Live code/diff/prompt/history | complete for tested run | `p4-dashboard-live-code-diff-prompt-history.md`, `p4-ui-smoke.png` | `/strategy_code`, `/strategy_diff`, `/prompts`, `/ai_context_pack` are non-breaking and visible | Re-test after future UI edits |
| P5 CSV analysis persistence/UI | complete for local research snapshot | `p5-csv-analysis-persistence-visualization.md` | Analysis persists to local research state and dashboard routes work | Need prove feedback loop into next prompt choices |
| P6 Glossary/explanations | complete | `p6-glossary-human-readable-metric-explanations.md`, `p6-research-glossary-panel.png` | OOS, MDD, payoff, edge ratio, PBO/DSR, slippage, etc. are explained | Keep terms near each new metric |
| P7 Bounded research sequence | complete as bounded sequence | `p7-bounded-research-run-sequence.md` | 09:00..09:30 seed reproduced; generated code/prompt visible; timeout captured as evidence | Generated gen1 timed out at 180s and has no CSV |
| Final verification | complete for this page | `final-verification.md` | Focused tests, nonrelease verifier, diff check, and protected status passed | Does not cover future long research |

## ULW Prompt Context Page

| Criterion | Status | Evidence | Notes |
|---|---|---|---|
| C001 HTTP/API prompt-context proof | pass | `.omo/ulw-loop/evidence/G001-C001-prompt-context-proof.json` | Context pack has guide/diff/analysis/correlation sections |
| C002 Browser dashboard proof | pass | `.omo/ulw-loop/evidence/G001-C002-dashboard-context-proof.png`, DOM text | Dashboard shows AI Context Pack, strategy/prompt, diff, and OOS-disabled label |
| C003 Regression/safety proof | pass | `.omo/ulw-loop/evidence/G001-C003-regression-safety-transcript.txt` | 38 tests passed; nonrelease/diff/protected/malformed HTTP checks passed |

Note: the active ULW goal remains active because the full master roadmap is not complete. These criteria prove only the Page 1 prompt-context slice.

## Dashboard Page / Panel Status

| Dashboard Page / Panel | Current State | Required Next State |
|---|---|---|
| Engine status/progress/logs | Partial-complete. P7 showed progress, period, tick mode, timeout, config, and logs for bounded run. | Reconfirm during next bounded timeout-reduction run and long-run prep. |
| Strategy inspector | Complete for tested run. `/strategy_code` and `/strategy_diff` returned 200 and UI rendered code/diff. | Keep graceful stale/empty state tests as future run IDs change. |
| Fitness/equity chart | Improved, with clearer profit/return fields and period labels in tests. | Browser-verify readability after longer multi-generation runs. |
| Hall of Fame | Backend/frontend tests indicate total profit and profit percent support exists. | Browser evidence for horizontal scroll and sorting is still needed. |
| Phase detail | Partial. Engine/progress state improved, but ambiguous "live data waiting" style empty states need continued copy QA. | Verify Korean empty-state wording in browser. |
| Research Wiki | Partial. Wiki docs exist and docs API discovers them, but `research_wiki` query style still returned HTTP 404 in this check. | Add/repair query route or update UI to use existing docs API; capture browser proof. |
| AI Context Pack | Complete for tested run. `/ai_context_pack` returned 200 and panel rendered `context_pack`. | Extend from metadata visibility to actual analysis-feedback prompt wiring proof. |
| Run Compare console | Partial. More metrics are present than before, but long-run comparison evidence is missing. | Add profit, return, MDD, trades, period, OOS mode, elapsed time in real compare proof. |
| Analysis/heatmaps | Partial-complete. `/analysis_snapshot`, `/variable_correlation`, `/edge_ratio`, `/feature_importance` are available for CSV-backed runs. | Prove time x market-cap x variable insights alter the next generation prompt. |

## Current Bottleneck

The current blocker is not dashboard visibility. The immediate blocker is LLM provider availability for generated strategy creation:

```text
Run: tick_p3_split_0920_0925_20260606
Gen0 seed: csv=no, no metrics
Gen1 generated: gpt_auth HTTP 429 usage_limit_reached before code generation

Run: tick_p3_split_0925_0930_20260606
Gen0 seed: csv=no, no metrics
Gen1 generated: gpt_auth HTTP 429 usage_limit_reached before code generation
```

This means the next page should target provider preflight / alternate provider / safe offline candidate fallback before another P4 retry or 2024-2026 broad research.

## Next Page Recommendation

| Candidate Next Page | Why |
|---|---|
| `provider preflight and safe offline candidate fallback` | Directly unlocks the current P3 blocker: no generated code can be created while `gpt_auth` is rate-limited and no alternate provider is configured. |
| `tick 09:00~09:30 generated strategy timeout reduction` | Still needed after provider availability is restored; P3/P4 cannot finish without generated code. |
| `research wiki query route repair` | Useful dashboard polish, but lower priority than generated timeout because it does not unlock candidate discovery. |
| `2024~2026 recent-weighted run` | Too early until generated 09:30 bounded CSV+metrics exists and provider availability is stable. |

Recommended command:

```text
$ulw-plan provider preflight and safe offline candidate fallback plan: use .omo/evidence/tick-900-930-generated-timeout-reduction-20260606/p3-provider-quota-blocker.md and .omo/plans/tick-900-930-generated-timeout-reduction-20260606.md as primary evidence. Add a research-only preflight for gpt_auth/openrouter/codex_proxy availability, and if no provider is available, plan a Codex-assisted offline candidate-generation path that writes evidence artifacts first and does not touch official engines, hard gates, backtest_graph, protected paths, production export, final_approval, live, or V3K.
```
