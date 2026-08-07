---
slug: ai-condition-loop-canonical-rebuild-20260711
status: approved
intent: clear
pending-action: write .omo/plans/ai-condition-loop-canonical-rebuild-20260711.md
approach: Preserve the existing controller and official backtest boundary, make evidence/feedback durable and attributable, prove a bounded mini-loop, then open sealed OOS and normalized human benchmarking only through predecessor gates.
---

# Draft: ai-condition-loop-canonical-rebuild-20260711

## Components (topology ledger)
<!-- Lock the SHAPE before depth. One row per top-level component that can succeed or fail independently. -->
<!-- id | outcome (one line) | status: active|deferred | evidence path -->

| id | outcome | status | evidence path |
|---|---|---|---|
| C1 | CL-D0..D4 produce one authoritative design contract plus subordinate receipts and a safe new-agent handoff | active | `docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md:146-160` |
| C2 | CL-R01..R04 establish the north star, collision-free versions, controller ownership, Candidate Passport, Run Ledger, and evaluation manifest | active | `docs/update_log/2026-07-11_ai_condition_loop_goal_process_reset_audit.md:128-183` |
| C3 | CL-R05..R06 prove durable feedback consumption, B-only provenance, semantic diversity, and entry/exit causal separation | active | `ai_strategy_loop/controller/loop.py:1197-1219`, `cli/condition_generator.py:159-255` |
| C4 | CL-R07..R08 run only a bounded two-to-three-round learning proof and preregistered min-primary performance experiment | active | `docs/update_log/2026-07-11_ai_condition_loop_goal_process_reset_audit.md:208-221` |
| C5 | CL-R09..R10 execute sealed OOS/walk-forward and same-cohort human benchmarking before any promotion review | active | `docs/update_log/2026-07-11_ai_condition_loop_goal_process_reset_audit.md:165-174` |
| C6 | Dashboard/state surfaces show provenance, lineage, stale-state conflicts, semantic versions, and cohort comparability without becoming an execution owner | active | `ai_strategy_loop/dashboard/app.py:739-961`, `ai_strategy_loop/controller/state.py:973-1086` |

## Open assumptions (announced defaults)
<!-- Record any default you adopt instead of asking, so the user can veto it at the gate. -->
<!-- assumption | adopted default | rationale | reversible? -->

| assumption | adopted default | rationale | reversible? |
|---|---|---|---|
| Evidence storage | Add append-only evidence tables to the existing `loop_runs.db` schema and mirror each accepted passport/feedback/run receipt in readable JSON snapshots | Existing `LoopState` already owns WAL, idempotent migrations, read-only dashboard access, and snapshots; avoids a second source of truth | yes, additive schema only |
| Canonical execution owner | `ai_strategy_loop/controller/loop.py::run_loop` is the only component allowed to advance the final generation lineage | Batch/research paths currently evaluate or propose candidates but do not prove autonomous generation | yes, adapters remain usable as evidence producers |
| Primary research lane | min-primary for CL-R07/R08; tick remains diagnostic/stress-only until an explicit later gate | Existing V3 design plan requires min primary and tick diagnostic | yes, requires a new preregistered profile version |
| Human comparison | Only identical cohort keys may be ranked; non-tick or otherwise non-comparable candidates remain visible but unranked against the human reference cohort | Current Hall of Fame mixes incompatible methodology/timeframe cohorts | yes, presentation-only until normalized evidence exists |
| Test strategy | Contract TDD for CL-R01..R06, tests-after for dashboard presentation, isolated official/manual gates for CL-R07..R10 | The highest risks are schema/lineage/leakage/feedback attribution; performance cannot be proven by mocks | yes |
| Version names | Use namespaced `CL-D0..CL-D4` and `CL-R01..CL-R10`; preserve T0-T4/P0-P11 only as legacy aliases | Bare V/P/R labels collide throughout the repository | yes, documentation/API labels only |

## Findings (cited - path:lines)

- The original north star is autonomous generation -> official STOM evaluation -> scoring -> autopsy -> repeat, not fixed batch evaluation: `docs/AGENT_HANDOFF.md:10`.
- Latest V2 is closed: seven metric-bearing rows all lost money and exceeded MDD 35, one row had no metrics, and survivor/hold counts are zero: `docs/update_log/2026-07-09_lattice_v2_closeout_or_new_design_review.md:19-25,39-53`.
- Current V3 outputs are absent and its plan is design-only with no generation/DB/replay/OOS/Plan D: `docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md:67-111,164-411`.
- Canonical `run_loop` creates a real provider; `provider=batch` is publication from the fixed-pair evaluator and never calls generation/autopsy: `ai_strategy_loop/controller/loop.py:1099-1180,2666-2699`, `ai_strategy_loop/scripts/claude_candidate_batch_eval.py:72-171`, `ai_strategy_loop/controller/state.py:737-766`.
- Feedback exists but is held in transient `next_*` variables and is not reloaded on resume: `ai_strategy_loop/controller/loop.py:1176-1219,1385-1414,1517-1528,1722-1756`.
- Generated candidates have no general immutable passport binding; `generations` stores metrics/parent/diffs but not candidate/passport IDs or buy/sell hashes: `ai_strategy_loop/controller/state.py:121-246,301-430`.
- Seed passports and Trade Ledger provide reusable identity patterns but are not wired into the controller loop: `ai_strategy_loop/seeds/passport.py:83-133`, `ai_strategy_loop/autopsy/trade_ledger.py:72-125,502-548`.
- Candidate-pack ingestion rejects literal R_/S_ leakage but does not positively require an approved B_* variable; exact duplicate detection is raw-string equality: `cli/condition_generator.py:25-155,159-255`.
- Threshold candidates lack dataset/window/fold/estimator provenance and semantic fingerprints: `cli/analyzer.py:67-68,114-175,247-343`, `cli/research_loop.py:1268-1480,2549-2581`.
- Existing holdout slices the same full-result CSV and is not sealed future OOS; the frozen replay profile is tick/2025, conflicting with the new min-primary design: `ai_strategy_loop/fitness/holdout.py:19-27,200-208`, `ai_strategy_loop/controller/replay_profile.py:109-129`.
- Hall of Fame merges non-comparable human/AI cohorts; reference metadata is dropped before sorting: `ai_strategy_loop/dashboard/reference_strategies.json:2-7`, `ai_strategy_loop/dashboard/app.py:739-961`, `ai_strategy_loop/dashboard/frontend/chart-hall-of-fame.jsx:53-69`.
- Historical run reconstruction drops live lineage/feedback page data and current-state freshness conflicts are not surfaced: `ai_strategy_loop/dashboard/app.py:177-187,1464-1469`, `ai_strategy_loop/controller/state.py:973-1086`.
- The dirty worktree has hundreds of unrelated tracked/untracked artifacts; every task must stage explicit paths only and reject unrelated files.

## Decisions (with rationale)

1. The new master plan is the sole top-level execution roadmap. The Jul-09 V3 design-only plan remains the subordinate CL-D0..D4 execution contract; the Jul-11 audit remains the current goal/status authority.
2. `lattice_v3_design_spec_20260709.md` is the sole canonical design specification. Receipts, lesson matrices, protocol, and handoff are supporting evidence and may not redefine the contract.
3. Introduce dedicated typed modules instead of growing `loop.py`, `state.py`, and `prompt.py`: `controller/evidence_contract.py`, `controller/evidence_store.py`, and `cli/condition_fingerprint.py`.
4. Compose an `EvidenceStore` with the existing `LoopState` SQLite connection. Add append-only `candidate_passports`, `feedback_envelopes`, `feedback_consumptions`, `evaluation_manifests`, and `run_receipts` tables through an idempotent schema migration; never commit runtime DB contents.
5. Define content identity as buy/sell code hashes plus timeframe/methodology context, while passport identity remains run/generation/slot scoped. Link all evidence by `run_id`, `round_no`, `gen_no`, `candidate_id`, and `passport_id`.
6. Persist feedback before the next generation, restore the latest unconsumed envelope on resume, and append an immutable `feedback_consumptions` row only after the prompt receipt records the feedback ID. Derive consumption state by query; evidence tables never use UPDATE/DELETE. A rendered string without an ID link does not count as learning evidence.
7. Enforce approved B_* variable scope at every external/LLM candidate ingestion boundary. Record threshold estimator, parameters, fit partition, data/window/rowset hashes, and fold ID.
8. Use both canonical AST fingerprints and actual selected-row fingerprints. Static semantic duplicates consume no provider/backtest quota.
9. Attribute entry and exit effects with a preregistered 2x2 parent/candidate buy/sell matrix; do not infer buy-only or sell-only quality from the combined strategy result.
10. Version a min-primary replay profile for bounded learning. Preserve the existing tick profile as historical; never silently mutate it.
11. Sealed OOS is inaccessible until candidate/config/profile hashes are frozen and preregistered. Same-CSV holdout is validation evidence only, never final OOS proof.
12. Hall of Fame comparison requires identical cohort keys covering timeframe, period, universe, engine/methodology, capital, cost/fill policy, and session window. Non-comparable rows are grouped or marked, never globally ranked together.
13. No phase can open itself. Every CL-R transition requires a machine-readable predecessor receipt; missing/invalid evidence fails closed.
14. Separate predecessor evidence from authority. `$start-work` initially authorizes only CL-D0..D4. Exact later approval phrases are: `I approve CL-R01-R06 code integration only`, `I approve CL-R07 bounded mini-loop only`, `I approve CL-R08 bounded min performance only`, `I approve CL-R09 sealed OOS/WF only`, and `I approve CL-R10 benchmark promotion review only`.
15. Freeze the learning/validation/OOS/human-cohort manifests before the first result-bearing CL-R07 run. CL-R07 cannot change CL-R08/R09/R10 thresholds after seeing results.
16. CL-R07 uses exactly three rounds. Each round requests four proposals (two repair, two discovery), accepts zero semantic duplicates, permits at most two proposals from one family, and evaluates one statically selected candidate. One positive and one negative control run once; the final candidate receives one four-arm 2x2 ablation. Maximum official evaluations: nine; maximum provider pack calls: three; wall-clock cap: 120 minutes; any cap breach ends the phase `no_go_budget_exhausted`.
17. CL-R07 uses the existing bounded min defaults as the frozen learning profile: `single_stock`, five trading days, engine count 1, betting `5`, avg_time 30, timeout 300 seconds, warm-run timeout 120 seconds, MDD cap 40, minimum 30 trades with daily-average fallback 0.5. It proves process wiring, not final alpha.
18. CL-R08 derives a deterministic historical profile from data available before 2026-07-11: the last 60 complete min trading days, first 40 for train and last 20 for validation; a train-only top-20 liquid-symbol subset; maximum eight preregistered candidates; MDD <=35, profit after engine costs >0, daily average >=0.5, no timeout/error, and worst-half-period profit >0. Failure opens no OOS.
19. CL-R09 uses prospective data only: first 20 complete trading days strictly after 2026-07-11, supplied only through `STOM_AI_LOOP_SEALED_OOS_DB`. A custodian subprocess withholds the path from generation, records pre-open hash/ACL/read receipt, opens once after candidate/config/profile freeze, and writes an immutable access receipt. Any generation after opening invalidates the OOS claim.
20. CL-R10 requires executable human buy/sell bodies plus hashes and an identical cohort manifest. If only screenshot/reported metrics exist, the result is `not_comparable_missing_executable_reference`; the UI must not rank AI against humans and no human-level claim is allowed.
21. Dirty-worktree protection is per todo: capture a baseline porcelain snapshot, use an explicit allowlist, fail if any unexpected path changes, stage only listed paths, and never include runtime DB/CSV/log/evidence bulk files in Git.

## Scope IN

- Correct the Jul-11 audit numbering and introduce the `CL-D`/`CL-R` alias table.
- Create the durable master plan and a self-contained new-agent handoff; update stale handoff pointers without deleting historical content.
- Design and implement typed candidate, feedback, evaluation-manifest, and run-receipt contracts with additive SQLite persistence and readable snapshots.
- Wire CLI research evidence into the canonical controller without making CLI/batch a competing generation owner.
- Add positive B_* scope validation, threshold provenance, semantic fingerprinting, and family/slot quotas.
- Add durable feedback restore/consume proof and entry/exit ablation.
- Prove a bounded mini-loop, then a preregistered min performance page, sealed OOS/WF, normalized human benchmark, and promotion review in strict order.
- Update dashboard/API/state reconstruction for lineage, provenance, semantic versions, freshness conflicts, and cohort-safe HOF display.
- Add focused contract tests, isolated SQLite tests, official bounded QA receipts, browser QA, and final scope/protected-path audits.

## Scope OUT (Must NOT have)

- Alpha Lab, V3K migration/gates, Kiwoom/live broker wiring, live order/exit behavior, or production deployment.
- Reopening Broad-Grid-576, failed V2 bodies, unlimited Plan D, full tick/min 288, portfolio construction, export, live, or final promotion.
- Operating `_database/`, runtime `*.db`, `_log/`, `backup/`, `backtest/graph/`, `.omx/reports/`, or user-owned dirty artifacts.
- Any OOS access before freeze/preregistration, any random time-series split, or any result-variable/S_*/R_* leakage into buy-condition generation.
- A second autonomous loop, a second dashboard framework, a second canonical state database, or a new dependency without explicit user approval.
- Treating unit tests, a smoke winner, one month, or a dashboard rank as performance proof.

## Open questions

None. The user approved the announced defaults by replying `계획 작성` after the approval brief on 2026-07-11.

## Approval gate
status: approved
approved-input: `계획 작성`
approved-scope: write one decision-complete `.omo` plan; do not implement code, DB, backtests, OOS, or durable docs until `$start-work`
<!-- When exploration is exhausted and unknowns are answered, set status: awaiting-approval. -->
<!-- That durable record is the loop guard: on a later turn read it and resume at the gate instead of re-running exploration. -->
