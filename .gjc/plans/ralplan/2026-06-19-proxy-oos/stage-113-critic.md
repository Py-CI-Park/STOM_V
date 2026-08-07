**[OKAY]**

**Justification**: Stage 113 is APPROVE-ready for the pending-approval final plan. The deep-interview spec, revised plan, stage 113 Architect review, and stage 112 Critic amendments were read. The six stage 112 required fixes are incorporated with concrete acceptance and verification. Representative source checks confirm the plan targets real seams and gives executors enough contract detail without guessing. No product execution is implied.

**Summary**:
- Clarity: Clear phase order: identity/recovery, shared detail/history, IA cleanup, then editor/replay/variable/BackFinder.
- Verifiability: Concrete post-approval tests cover identity hashes and legacy notes, additive `/bt/result`, `no_trades` auto-open, ResultDetail split, `rp-heatmap` ownership, History/Compare routing, and render-only replay.
- Completeness: Covers the spec topology: result recovery, GUI parity core, shared ResultDetail, History, IA ownership, home layout, replay, variable tooling, self.vars, and BackFinder staging.
- Big Picture: Option A fits brownfield constraints and avoids duplicate top-level pages; History-first and new domain store are correctly rejected.
- Principle/Option Consistency: Code-hash-first identity, evidence namespace, one ResultDetail body, History-owned archive/Compare, and render-only replay align with the selected option.
- Alternatives Depth: Sufficient for execution planning; no re-architecture needed before user approval.
- Risk/Verification Rigor: Key risks have executable mitigations: identity drift, Workbench duplication, API breakage, detail duplication, replay data loss, and legacy BackFinder/self.vars risk.

**Stage 112 amendment check**:
1. Identity contract: incorporated with `evidence_id`, `condition_identity.kind`, buy/sell hashes, display names, confidence, and artifact notes.
2. `rp-heatmap.jsx` ownership: incorporated in Phase 2 and Phase 3, requiring `_RpHistory` and `_RpRunCompare` migration or demotion to History links.
3. `no_trades` auto-open: incorporated in file-level changes, sequencing, acceptance, and verification.
4. ResultDetail split and additive `/bt/result`: incorporated with presentational `ResultDetailBody`, source containers, and compatibility fields preserved.
5. Explicit verification: incorporated with named static/component/unit targets for each architect/critic amendment.
6. Replay render-only constraint: incorporated with full `barsRef`, server frames, seek/history, export, and signal logic preserved while only render arrays are adapted.

**Reference and source verification**: Verified spec, revision, Architect 113, Critic 112, and all nonoptional plan file references by file lookup. Optional `ai_strategy_loop/dashboard/frontend/result-detail.jsx` is absent, which is allowed because the plan says it is optional. Representative source reads confirmed: `backtest_jobs.py` currently restores running/pending as `status=error`, `phase=stale`; `backtest_api.py` has job and run/gen `/bt/result` branches with existing compatibility fields; `bt-tab-run.jsx` currently auto-opens only success while rows treat success and no_trades as clickable; `bt-result-area.jsx` currently combines fetching and rendering; `rp-heatmap.jsx` currently owns `_RpRunCompare` and `_RpHistory`; `ui-contract.jsx` still labels records as 기록 검색; replay code keeps client `barsRef` and backend frames/seek/history semantics.

**Representative implementation simulation**:
1. Phase 1 identity/status can add an adapter around existing job specs, current strategy code lookup, old job JSON fallback, and run/gen rows because the plan defines exact namespaces, legacy confidence, artifact notes, additive fields, and status actions.
2. Phase 2 ResultDetail/History can extract rendering from `BtResultArea` and move or demote Workbench `_RpHistory` and `_RpRunCompare` because the plan names source containers, body ownership, alias preservation, and Compare owner.
3. Phase 4 replay can derive per-engine `renderBars` without data loss because existing `barsRef`, server frames, history snapshots, seek, and signal code remain authoritative and the plan forbids truncating them.

**Required fixes before approval**: none.

**Verdict**: OKAY / APPROVE-ready.
