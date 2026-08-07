**[ITERATE]**

**Justification**: The planner is directionally correct and Option A fits the brownfield spec, but it is not approval-ready because Architect COMMENT/WATCH items close real ambiguity that executors would otherwise resolve by guesswork. Current files confirm the gaps: BacktestJobSpec and BacktestJobRecord carry names, status, csv, metrics, and mode_result but no durable condition/evidence identity; restored running/pending jobs are collapsed to status=error and phase=stale; /bt/result has job and run/gen branches with similar fields but no canonical ResultDetail identity contract; BtRunPanel auto-opens only success while library rows already treat no_trades as openable; BtResultArea is both source fetch container and renderer; records is still campaign/update-log lookup; Workbench still renders _RpRunCompare and _RpHistory in rp-heatmap.jsx; replay keeps full client bars but uses fixed render caps. These are amendment-sized issues, not a reason to reject the whole approach.

**Summary**:
- Clarity: Good phase order and ownership intent, but identity semantics and Workbench History/Compare migration are underspecified.
- Verifiability: Existing test targets are real and verified, but acceptance must add tests for code-hash identity/legacy confidence, rp-heatmap demotion, no_trades auto-open, ResultDetail body/container split, additive /bt/result, and render-only replay adaptation.
- Completeness: Broadly covers the spec, including recovery, ResultDetail, History, IA, editor, replay, variables, and BackFinder; missing explicit incorporation of Architect COMMENT items.
- Big Picture: Option A is the right brownfield path; History-first and new domain-store options are correctly not selected.
- Principle/Option Consistency: Principles match Option A. Identity-first is not yet concrete enough to guide implementation safely.
- Alternatives Depth: Fair enough for approval once amendments are merged; no need to reroute to a new architecture.
- Risk/Verification Rigor: Risks are named, but mitigations need executable contracts for legacy identity confidence, duplicated Workbench surfaces, API compatibility, and replay data preservation.

**Representative implementation simulation**:
1. Phase 1 identity/status: adding condition_identity from current strategy code is straightforward for fresh jobs, but old job JSON and run/gen rows can only point at mutable names unless the plan defines code_hash vs name_only_legacy and a visible confidence/artifact note.
2. Phase 2 History/ResultDetail: adding a History route under ui-contract.jsx and remodeling research-records-panel.jsx would duplicate existing _RpHistory/_RpRunCompare unless rp-heatmap.jsx is explicitly migrated or demoted.
3. Phase 4 replay: existing barsRef and server frames can support adaptive render derivation, but the plan must forbid truncating authoritative bars/history and require viewport/count-budget render inputs only.

**Required fixes before approval**:
1. Define exact identity contract: evidence_id = job:<job_id> | gen:<run_id>:<gen_no> | history:<id>, condition_identity.kind = code_hash | name_only_legacy, normalized buy/sell code hashes when available, and legacy confidence/artifact notes for name-only or missing-code cases.
2. Add ai_strategy_loop/dashboard/frontend/rp-heatmap.jsx to Phase 2/3 file-level changes and state whether _RpHistory and _RpRunCompare move into History or are demoted to History links only.
3. Amend BacktestTab acceptance/verification so no_trades post-run auto-opens detail just like success, while failed/cancelled/stale expose status-aware open/recover/rerun actions.
4. Require a presentational ResultDetailBody split from source containers for job, run/gen, and history item; preserve /bt/result fields available, job_id, run_id, gen_no, status, metrics, analysis, mode_result additively.
5. Add explicit verification for architect amendments: static/source tests for identity fields and legacy confidence, rp-heatmap History/Compare ownership, no_trades auto-open hook, shared ResultDetail import/body separation, additive API fields, and render-only replay adaptation.
6. Keep Phase 4 replay adaptation render-only: full barsRef, server frames, seek/export/signal logic stay authoritative; only per-engine render arrays are windowed/decimated by viewport/device/count budget.

Architect COMMENT items must be incorporated before execution approval. After these amendments, the plan can proceed without re-architecture.
