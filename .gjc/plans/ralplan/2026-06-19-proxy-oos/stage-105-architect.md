## Summary
Revision 105 resolves the blockers from the stage 104 architect review. The plan now separates advisory scores from promotion authority, makes missing evidence promotion-blocking, scopes tick/min policy to presets while preserving raw defaults, hardens pattern-card anti-copy rules, and keeps live/export/operating DB/V3K/KHOPENAPI and Transformer work out of scope.

Recommendation is APPROVE for the planning artifact, with WATCH status during implementation because the phase stop points and authority boundaries must be preserved exactly.

## Analysis
Reviewed `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-105-revision.md`, blocking review `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-104-architect.md`, repository guidance in `AGENTS.md` and `ai_strategy_loop/AGENTS.md`, plus targeted read-only source context for existing hard gates and raw defaults. No product files were edited. No tests, formatters, builds, backtests, project-wide commands, live/export actions, operating DB access, V3K access, KHOPENAPI access, or Transformer/ML work were run.

Stage 104 blockers and revision 105 resolution:
- Stage 104 blocked approval because 100-point score fields could influence promotion candidacy and because `evidence_status` plus missing prompt/equity evidence semantics were absent (`stage-104-architect.md:22-30`). Revision 105 now states that `performance_score_100` and `condition_quality_score_100` are only display, explanation, sorting, triage, and ranking fields, and that they never grant promotion authority, set `promotion_gate_passed`, override hard gates, override evidence blockers, or replace frozen-candidate review or explicit human approval (`stage-105-revision.md:7`, `:31-37`, `:115`, `:121`).
- Revision 105 defines explicit evidence states and blocker behavior for CSV, trade rows, equity, prompt, and validation evidence. Missing required evidence yields `evidence_status=evidence_blocker`, `candidate_status=not_promotable`, stable blocker reasons, and `promotion_gate_passed=false` (`stage-105-revision.md:8`, `:40-57`, `:107`, `:115`, `:120`, `:125`).
- The preset policy is now scoped to named presets. Fast is discovery only, research and promotion default to tick 09:00-09:28, min research or promotion requires the full-session 09:00 through 15:18/15:19 boundary, and raw defaults remain unchanged unless the explicit preset resolver is invoked (`stage-105-revision.md:9`, `:59-67`, `:103`, `:119`). Current raw defaults are still `bt_timeframe="min"`, `bt_engine_mode="warm"`, `bt_universe_end_time=92800`, `full_session_enabled=False`, and `bt_min_universe_end_time=151900` (`ai_strategy_loop/config.py:94`, `:125`, `:129-138`).
- The pattern-card lane is no longer a loose example-copy mechanism. Revision 105 requires card schema fields, source labels, normalized expression/threshold/dedup hashes, threshold policy, forbidden copy units, hash and near-duplicate dedup, no literal threshold or full expression copying, and negative acceptance cases for copied expressions, copied thresholds, missing schema/hash, and importing human DB performance as truth (`stage-105-revision.md:69-101`, `:109`, `:123`).
- Operational boundaries are retained: planning remains pending approval only; live/export/operating DB/V3K/KHOPENAPI and Transformer/ML work are unauthorized; promotion can only mark pending approval and stops before export or activation (`stage-105-revision.md:3`, `:11`, `:23-27`, `:111`, `:115`, `:126`, `:128-130`). Repository guidance supports this boundary: the AI loop is research/control-plane code, export is gated through `controller/export.py` and dashboard final approval, operating DB/live wiring is prohibited without the approved gate, and V3K features remain default-off (`ai_strategy_loop/AGENTS.md`).

Existing source seams remain compatible with the revised plan. `compute_fitness` owns hard `gate_passed` using frequency, MDD, positive profit, and optional TPI gates (`ai_strategy_loop/fitness/score.py:251-312`), while `run_loop` uses graded score for best selection but winner/graduation only when `fit.gate_passed and holdout_ok` (`ai_strategy_loop/controller/loop.py:1471-1519`). Revision 105 preserves those seams by making new scores advisory and requiring evidence/policy completion for promotion metadata.

## Root Cause
The stage 104 blocker was an authority-boundary ambiguity: research diagnostics, evidence health, and promotion eligibility were not cleanly separated. Revision 105 fixes the root issue by assigning advisory scores no promotion authority and making evidence completeness a distinct blocking authority.

## Findings

1. **HIGH resolved - Advisory score authority is now non-promotional.**
   - Reference: `stage-104-architect.md:22-25`; `stage-105-revision.md:7`, `:31-37`, `:115`, `:121`.
   - Impact: The prior risk was that 100-point fields could become hidden selector or promotion gates. Revision 105 now explicitly forbids scores from setting `promotion_gate_passed`, overriding hard/evidence gates, or replacing frozen-candidate review and human approval.
   - Fix status: Resolved. Keep score fields display, explanation, sorting, triage, and ranking only.

2. **HIGH resolved - Evidence completeness has explicit blocker and promotion-ineligible semantics.**
   - Reference: `stage-104-architect.md:27-30`; `stage-105-revision.md:8`, `:40-57`, `:107`, `:115`, `:120`, `:125`.
   - Impact: The prior risk was silent promotion readiness with missing CSV, trade, equity, prompt, or validation evidence. Revision 105 now requires stable blocker reasons, `candidate_status=not_promotable`, and `promotion_gate_passed=false` for any blocker.
   - Fix status: Resolved. Implementation must persist these fields rather than swallowing evidence failures.

3. **MEDIUM resolved - Tick/min policy is preset-scoped and raw defaults are preserved.**
   - Reference: `stage-104-architect.md:32-39`; `stage-105-revision.md:9`, `:59-67`, `:103`, `:119`; `ai_strategy_loop/config.py:94`, `:125`, `:129-138`.
   - Impact: The prior risk was global default drift or incomparable promotion candidates. Revision 105 confines behavior to explicit presets and requires full-session min evidence for any later promotion consideration.
   - Fix status: Resolved. Implementation should leave raw `LoopConfig()` behavior byte-compatible and perform all changes through the preset resolver.

4. **MEDIUM resolved - Pattern cards have an anti-copy schema, hashes, dedup, and negative acceptance.**
   - Reference: `stage-104-architect.md:34-40`; `stage-105-revision.md:69-101`, `:109`, `:123`.
   - Impact: The prior risk was leaking human or historical expressions, thresholds, or performance claims through curated prompt examples. Revision 105 requires schema validation, normalized hashes, dedup, no threshold/full-expression copy, and fail cases for copied artifacts or imported performance truth.
   - Fix status: Resolved. Implementation should reject nonconforming cards before prompt injection.

5. **LOW clear - Operational isolation and Transformer deferral are carried.**
   - Reference: `stage-104-architect.md:42-45`; `stage-105-revision.md:3`, `:11`, `:23-27`, `:111`, `:115`, `:126`, `:128-130`; `ai_strategy_loop/AGENTS.md`.
   - Impact: The plan remains planning-only and does not authorize live/export/operating DB/V3K/KHOPENAPI, direct activation, frontend work in this lane, or Transformer/ML work.
   - Fix status: Clear.

## Recommendations
1. Approve revision 105 as the final planning artifact for this Ralplan pass.
2. Preserve the stop points exactly: Phase 1 architect review, Phase 2 formula review, Phase 3 state contract freeze, Phase 4 critic snapshot review, Phase 5 example review, Phase 6 stop before frontend edits, and Phase 7 stop before export or activation.
3. During implementation, treat advisory score fields as non-authoritative and evidence completeness as the blocking source of truth for promotion metadata.
4. Keep the work pending explicit execution approval; this review approves the plan, not source mutation, tests, live/export work, DB writes, V3K/KHOPENAPI access, or Transformer/ML work.

## Architectural Status
`WATCH`

## Product Status
`WATCH`

## Code Status
`CLEAR`

## Code Review Recommendation
`APPROVE`

## Trade-offs
| Tension | Safer choice in revision 105 | Alternative rejected | Verdict |
|---|---|---|---|
| Advisory diagnostics vs promotion authority | Scores rank and explain only | Scores gate promotion or override evidence | Safer choice approved |
| Missing evidence behavior | Stable blockers plus not promotable | Silent degraded state that can still promote | Safer choice approved |
| Tick/min policy | Preset-scoped overlays with raw defaults preserved | Mutate `LoopConfig()` defaults globally | Safer choice approved |
| Pattern-card reuse | Normalized, hashed, deduped anti-copy cards | Raw expressions, thresholds, or performance truth in prompts | Safer choice approved |
| Promotion path | Pending approval metadata only | Export, activation, operating DB, live, V3K, KHOPENAPI | Safer choice approved |
