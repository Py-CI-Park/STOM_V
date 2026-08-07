## Summary
Revision 104 is improved and carries several prior guardrails, but it is not yet approvable because two required WATCH invariants are either missing or contradicted: 100-point scores are later allowed to influence promotion candidacy, and `evidence_status`/promotion-ineligible semantics for prompt/equity evidence are absent. Recommendation is `REQUEST CHANGES`: keep the plan pending and revise before critic re-review.

## Analysis
Reviewed `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-104-revision.md`, prior critic `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-103-critic.md`, prior architect `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-103-architect.md`, repository rules, and targeted source context. No source edits, tests, formatters, builds, backtests, live runs, export actions, operating DB access, or project-wide commands were run.

Positive carry-forward evidence:
- Pending-approval boundary is explicit: no source edits/tests/builds/backtests/live/export/operating DB access are authorized (`stage-104-revision.md:1-3`, `:54`, `:137-139`).
- Pure preset overlay intent is present: raw `LoopConfig()` defaults stay behavior-compatible and research tick default applies only through an explicit resolver (`stage-104-revision.md:13`, `:77-79`). Current source defaults confirm why this matters: `bt_timeframe="min"`, `bt_engine_mode="warm"`, `bt_universe_end_time=92800`, `full_session_enabled=False`, and `bt_min_universe_end_time=151900` in `ai_strategy_loop/config.py:29-150`.
- Operational boundaries and ML deferral are carried: no live/export/operating DB/V3K/KHOPENAPI access and Transformer/ML are out of scope (`stage-104-revision.md:15`, `:19`, `:54`, `:95`, `:127`). Repository rules confirm `controller/export.py`/dashboard final approval is the export boundary and operating DB/live wiring is protected (`AGENTS.md`, `ai_strategy_loop/AGENTS.md`).
- The source seams support the intended separation: `compute_fitness` owns hard gates and `gate_passed` (`ai_strategy_loop/fitness/score.py:224-320`); `run_loop` keeps best as graded selection and winner/graduation behind hard-gate pass (`ai_strategy_loop/controller/loop.py:1000-1030`, `:1450-1525`); research OOS criteria already emit `promotion_claim=False` for research continuation (`ai_strategy_loop/fitness/research_criteria.py:1-180`).

Critical gaps against the prior critic/architect contract:
- Stage 103 critic required advisory-only 100-point scores, evidence-health semantics, normalized anti-copy pattern cards, pure preset overlay, explicit tick/min policy, hard operational boundaries, concrete verification, and stop points (`stage-103-critic.md:27-37`). Stage 103 architect made approval conditional on carrying all WATCH items and said dropping any should become `REQUEST CHANGES` (`stage-103-architect.md:32-60`, `:88`).
- Revision 104 now has stop points and many negative acceptances, but it still needs explicit constraints where the remaining WATCH items are either absent or ambiguous.

## Root Cause
The plan is trying to add explanatory dashboard/research fields while also defining promotion-candidate metadata. Without a hard separation between advisory diagnostics, evidence health, and promotion authority, executor interpretation can quietly turn research conveniences into selection or promotion gates.

## Findings

1. **HIGH — BLOCK: Keep 100-point scores advisory-only; Phase 7 currently contradicts that invariant.**
   - Reference: Revision 104 correctly says new 100-point scores are additive until separately approved as selectors (`stage-104-revision.md:14`, `:60`, `:84-87`), but Phase 7 then requires promotion candidacy only when “score thresholds pass, and quality score threshold passes” (`stage-104-revision.md:123-127`). Prior critic required these fields to never feed `compute_fitness`, `gate_passed`, `winner_*`, `target_score`, OOS, export, or promotion approval (`stage-103-critic.md:27-29`).
   - Impact: Implemented literally, the new scores stop being advisory and become promotion authority without separate approval, breaking the existing hard-gate/OOS/human approval boundary.
   - Fix: Rewrite Phase 7 so `performance_score_100` and `condition_quality_score_100`/`generation_quality_score_100` are display/research-ranking diagnostics only. Promotion candidacy may depend on frozen candidate state, existing hard gates, required fixed OOS/persistence evidence, and human approval metadata, but not on new 100-point score thresholds unless a later plan explicitly approves selector semantics.

2. **HIGH — BLOCK: Add explicit `evidence_status` and missing-evidence promotion-ineligible semantics.**
   - Reference: Prior critic required `evidence_status`/warning semantics where research may continue degraded, but promotion claims are blocked or marked ineligible when required prompt/equity evidence is missing, and failures are recorded in state/payloads (`stage-103-critic.md:29`, `:35-36`). Revision 104 mentions prompt/equity persistence policy in scope (`stage-104-revision.md:7`, `:52`) and `promotion_ineligible_reasons` in several places (`stage-104-revision.md:76`, `:92`, `:116`, `:124-126`), but it never defines `evidence_status`, evidence warnings, required evidence fields, prompt/equity persistence failure behavior, or missing-evidence negative acceptance.
   - Impact: A run could appear promotion-ready while prompt/equity audit evidence is absent or persistence failed, recreating the exact silent no-op risk identified in source (`ai_strategy_loop/config.py:460-570`, `ai_strategy_loop/controller/loop.py:560-610`, `:1220-1460`, `ai_strategy_loop/brain/generator.py:220-285`).
   - Fix: Add fields such as `evidence_status`, `evidence_warnings`, `prompt_evidence_status`, and `equity_evidence_status`; require persistence failures to be recorded in run/generation payloads; allow degraded research continuation; add `missing_prompt_evidence`/`missing_equity_evidence` to `promotion_ineligible_reasons`; add verification for missing prompt log, missing equity curve, parse failure, old-run null compatibility, and promotion-ineligible rendering.

3. **MEDIUM — BLOCK UNTIL EXPLICIT: Complete the preset-scoped tick/min policy.**
   - Reference: Revision 104 preserves raw defaults and says research resolves to tick (`stage-104-revision.md:13`, `:77-79`), and it checks promotion+min+`full_session_enabled=False` (`stage-104-revision.md:77`). Prior critic required the full preset-scoped policy: research tick/warm 09:00:00-09:28:00, min research/promotion full-session through the verified 15:18/15:19 boundary currently represented by `151900`, promotion freezes timeframe/window with the candidate, and fast/custom remains unchanged (`stage-103-critic.md:31-32`). Current config has `bt_universe_end_time=92800`, `full_session_enabled=False`, and `bt_min_universe_end_time=151900` (`ai_strategy_loop/config.py:29-150`).
   - Impact: Executors still have room to apply tick/min window semantics globally or inconsistently, causing default drift or incomparable promotion candidates.
   - Fix: Add the exact policy to Phase 1/7: research preset = tick + warm + 09:00:00-09:28:00 unless explicitly overridden; min research/promotion requires full-session and `bt_min_universe_end_time=151900` unless replaced by cited evidence; promotion freezes timeframe/start/end/window with the candidate; fast/custom keeps current defaults unless named preset is selected.

4. **MEDIUM — NEEDS TIGHTENING: Human pattern-card anti-copy contract is only partially explicit.**
   - Reference: Revision 104 carries pattern cards and threshold-copy prohibitions (`stage-104-revision.md:15`, `:33`, `:54`, `:99-104`, `:131-134`), and current prompt/generator already has whitelist, sell-only-variable, forbidden-token, timeframe, and few-shot structure-not-copy controls (`ai_strategy_loop/brain/prompt.py:1-100`, `:340-700`; `ai_strategy_loop/brain/generator.py:64-160`, `:345-450`; `utility/ai_agent/system_prompt/v1/system_prompt.md:1-100`; `utility/ai_agent/system_prompt/v1/forbidden.md:1-100`). The prior critic also required normalized grammar cards, stripped raw expressions/numeric constants, bounded/diversified K, provenance/risk notes, fingerprint/dedup checks, and negative-copy tests (`stage-103-critic.md:30`).
   - Impact: “Pre-curated pattern cards” and “no threshold copy” are directionally right, but without a card schema and fingerprint/dedup acceptance, source expressions or numeric fingerprints can leak through a curated path.
   - Fix: Add a pattern-card schema and acceptance: no raw code/expression storage in cards; numeric constants generalized into ranges/roles; provenance/risk note required; bounded and diversified `condition_library_k`; fingerprint/dedup/similarity checks against source expressions and generated candidates; prompt snapshot verifies raw thresholds and source expressions are absent.

5. **LOW — CLEAR: Operational boundaries, UI-worktree separation, prompt safety, and Transformer deferral are carried.**
   - Reference: Revision 104 excludes live/export/operating DB/V3K/KHOPENAPI, direct activation, frontend execution in this worktree, and Transformer/ML (`stage-104-revision.md:15-19`, `:54`, `:95`, `:111`, `:119`, `:127`). Prompt safety for sell-only variables and whitelist/forbidden-token safety is explicitly included (`stage-104-revision.md:18`, `:101-103`).
   - Impact: These items are acceptable as long as the blocking fixes above are incorporated and retained.
   - Fix: Keep unchanged in the next revision.

## Recommendations
1. Revise before critic re-review. This cannot move to final approval while Phase 7 contradicts advisory-only score semantics and evidence-health semantics are absent.
2. Make WATCH items explicit constraints, not implications: add a single carry-forward invariant table mapping each prior WATCH item to exact fields, phases, negative acceptance, and verification.
3. Add the evidence-health verification cases and the exact tick/min preset policy to the focused verification matrix.
4. Keep the plan pending approval only; continue to forbid source edits/tests/builds/backtests/live/export/operating DB access during planning.

## Architectural Status
`BLOCK`

## Product Status
`BLOCK`

## Code Status
`BLOCK`

## Code Review Recommendation
`REQUEST CHANGES`

## Trade-offs
| Tension | Safer choice | Riskier choice | Recommendation |
|---|---|---|---|
| Advisory scores vs promotion authority | Display/research-ranking only | Let new scores gate promotion candidates | Keep advisory-only until a separate selector plan is approved |
| Evidence failure behavior | Degraded research + promotion-ineligible | Silent no-op persistence | Add explicit `evidence_status` and ineligibility reasons |
| Preset policy | Named overlay with frozen candidate window | Mutate raw defaults or infer windows | Preserve raw defaults; state exact tick/min windows |
| Human library | Normalized grammar cards with dedup/provenance | Raw expressions/thresholds in examples | Require schema, stripping, K cap, and negative-copy tests |
