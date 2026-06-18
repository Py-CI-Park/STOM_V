# Condition Research Master Roadmap Status - 2026-06-06

## Snapshot

| Item | Value |
|---|---|
| Branch | `lazycodex/tick-sparse-positive-generation-improvement-20260604` |
| HEAD | `84acb6cb` |
| Dashboard | `http://127.0.0.1:8770/ui/` |
| Dashboard health | `200 {"status":"ok","contract_version":2}` |
| Dashboard PID | `114272` |
| Dirty worktree | 90 entries; broad pre-existing research/dashboard worktree, not reverted |
| Protected paths | clean in latest protected-path status check |
| Current strict claim | blocked; no human-level, seed-superior, or production-ready claim |

Protected-path command used:

```powershell
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json _v3k_sidecar/v3k_gui_settings.json
```

Result: no protected-path changes reported.

## Guardrails

- Do not edit official backtest engines.
- Do not edit hard-gate scoring/promotion contracts as a shortcut.
- Do not edit `backtest/graph`.
- Keep new toggles default OFF or research-config-only.
- Do not use `final_approval`, `export_winner`, production export, live broker/KHOPENAPI, live order wiring, or V3K gate advancement.
- Do not use blanket `taskkill`; use PID-scoped process handling only.
- OOS-disabled or advisory research results are research-only and cannot prove human-level performance.

## Change Control

Routine updates can be made without new user consent:

- Marking a step complete, partial, blocked, or superseded by evidence.
- Adding evidence links.
- Updating observed metrics from a run.
- Recommending the next command.

Master roadmap decision changes require explicit user consent:

- Changing stage order.
- Adding or removing a major stage.
- Weakening or strengthening claim criteria.
- Changing protected-path, live-trading, export, or OOS guardrails.
- Reclassifying a research-only result as a promotion/human-level result.

Readable consent phrase:

```text
마스터 로드맵 변경 승인: <변경 요약>
```

## Master Roadmap Progress

| Stage | Status | Progress | Current Evidence | Blocker / Next Unlock |
|---|---|---:|---|---|
| M0 Canonical safety baseline | complete | 100% | `docs/AGENT_HANDOFF.md`, current branch/HEAD/protected snapshot above | Maintain before every run |
| M1 Governance | complete | 100% | `.omo/plans/condition-research-end-to-end-master-roadmap-20260606.md`, this status artifact | Only user-approved roadmap decision changes |
| M2 Always-on dashboard/process visibility | partial | 80% | P4/P7 UI screenshots, `/health`, `/status`, `/ai_context_pack`, `/strategy_diff` evidence | Browser-verify every new page/panel; Wiki query route still has 404 gap |
| M3 Condition generation families | partial | 70% | P2 time-cap buy, P3 sell generation, prompt context pack G001, P3 split-probe provider blocker | `gpt_auth` quota now blocks generated candidates before timeout diagnosis |
| M4 Bounded backtest preflight | partial | 75% | P2 `09:00..09:20` generated CSV+metrics; P7 `09:00..09:30` bounded run; P3 split probes ended within wall cap | `09:00..09:30` generated gen1 previously timed out; P3 generated split probes are blocked by provider HTTP 429 |
| M5 Quant analysis | partial | 70% | P5 `/analysis_snapshot`, local `research_analysis.db`, `/variable_correlation`, `/edge_ratio` | Prove analysis feeds next-generation prompt, not only dashboard display |
| M6 Feedback/wiki loop | partial | 55% | G001 prompt context pack, autopsy/history/few-shot plumbing, P6 glossary | Wiki query route/UI needs non-404 browser proof |
| M7 Recent-weighted exploratory research | pending | 25% | P7 OOS-disabled label and bounded sequence; no 2024-2026 broad run yet | Restore a working LLM provider, then finish generated 09:30 split/full decision before broad research |
| M8 Strict promotion validation | blocked | 15% | Prior 2022/2026 OOS rejected candidate; no frozen candidate now | Frozen candidate, fixed OOS, slippage, PBO/DSR, no-reselection proof |
| M9 Wiki/knowledge base | partial | 45% | `docs/research/condition_research/wiki/*`, P6 glossary | Dashboard Wiki query route still needs repair/evidence |
| M10 Human comparison report | partial | 35% | Human reference graph doc and seed/OOS comparison history | Numeric extraction and same-period verdict card still pending |
| M11 Operating loop | pending | 10% | Process concept exists in roadmap | Needs stable M7/M8 evidence before routine operation |

## Current Performance Status

| Layer | Status |
|---|---|
| Infrastructure | Stronger. Dashboard, active code/diff/prompt/context, engine state/progress/log visibility, glossary, and CSV analysis are now materially better. |
| Research candidate | Mixed. `09:00..09:20` generated candidate produced CSV+metrics. `09:00..09:30` seed reproduced, but generated gen1 timed out. |
| Strict promotion | Not achieved. No frozen candidate and no fresh fixed 2022/2026 OOS, slippage, PBO/DSR, or no-reselection proof. |

## Key Current Metrics

| Run | Period | Mode | Gen | Trades | Profit | MDD | Payoff | Status |
|---|---|---|---:|---:|---:|---:|---:|---|
| `tick_p2_timecap_900_920_preflight_guarded2_20260606` | `2025-01-03` | tick, OOS disabled research | 1 | 5 | 76,127 | 0.97 | 2.055 | generated CSV+metrics exists |
| `tick_p7_timecap_900_930_bounded_20260606` | `2025-01-03` | tick, OOS disabled research | 0 seed | 1 | 229,983 | 4.59 | n/a | seed reproduced |
| `tick_p7_timecap_900_930_bounded_20260606` | `2025-01-03` | tick, OOS disabled research | 1 generated | 0 | 0 | 0 | n/a | warm backtest timeout at 180s, no CSV |
| `tick_p3_split_0920_0925_20260606` | `2025-01-03` | tick, OOS disabled research | 0 seed | n/a | n/a | n/a | n/a | seed no metrics, csv=no |
| `tick_p3_split_0920_0925_20260606` | `2025-01-03` | tick, OOS disabled research | 1 generated | n/a | n/a | n/a | n/a | provider HTTP 429 before generated code |
| `tick_p3_split_0925_0930_20260606` | `2025-01-03` | tick, OOS disabled research | 0 seed | n/a | n/a | n/a | n/a | seed no metrics, csv=no |
| `tick_p3_split_0925_0930_20260606` | `2025-01-03` | tick, OOS disabled research | 1 generated | n/a | n/a | n/a | n/a | provider HTTP 429 before generated code |

## Immediate Next Unlock

The next work should restore a working strategy-generation provider or define a safe Codex-assisted offline generation fallback. The latest split probes show orchestration works and no wall-cap hang occurred, but `gpt_auth` hit HTTP 429 usage limit before generated code existed. Long 2024-2026 research should wait until the generated path again produces CSV+metrics in a bounded run.

Recommended next command:

```text
$ulw-plan provider preflight and safe offline candidate fallback plan: use .omo/evidence/tick-900-930-generated-timeout-reduction-20260606/p3-provider-quota-blocker.md and .omo/plans/tick-900-930-generated-timeout-reduction-20260606.md as primary evidence. Add a research-only preflight for gpt_auth/openrouter/codex_proxy availability, and if no provider is available, plan a Codex-assisted offline candidate-generation path that writes evidence artifacts first and does not touch official engines, hard gates, backtest_graph, protected paths, production export, final_approval, live, or V3K.
```
