# Revision 104 planner artifact: STOM AI strategy-loop evolution dashboard condition-discovery plan

Status: pending approval only. This revision incorporates critic stage 103 feedback. It proposes future implementation only and authorizes no source edits, tests, builds, formatters, backtests, live runs, export actions, or operating DB access.

## Summary

Recommended path is a narrower staged Option B: preset-first dashboard contract plus explicit scores, but delivered behind additive fields and stop points. Do not redesign the loop at once. Preserve current hard gate and graded score behavior while adding resolved preset metadata, staged MDD labels, `performance_score_100`, `condition_quality_score_100`, prompt/equity persistence policy, human composition pattern cards, and hypothesis feedback.

Evidence basis from prior planner inspection: `ai_strategy_loop/config.py`, `ai_strategy_loop/launch_config.py`, `ai_strategy_loop/brain/prompt.py`, `ai_strategy_loop/fitness/score.py`, `ai_strategy_loop/controller/loop.py`, `utility/ai_agent/system_prompt/v1/system_prompt.md`, and `utility/ai_agent/system_prompt/v1/forbidden.md`.

## Architect WATCH invariants to carry

1. Backward compatibility invariant: raw `LoopConfig()` defaults must remain behavior-compatible. Research tick default applies only through an explicit preset resolver, not by silently changing raw defaults.
2. Scoring invariant: existing hard gate and graded selection semantics stay intact. New 100-point scores are additive fields until separately approved as selectors.
3. DB isolation invariant: no live DB, export DB, operating DB, V3K, or KHOPENAPI access. Human condition material must be pre-curated pattern cards outside the loop hot path.
4. Promotion invariant: promotion preset can mark frozen candidates and ineligibility reasons only. It must not export, activate, trade, or write operating state.
5. UI worktree invariant: backend state contract first; frontend/dashboard implementation remains a separate approved worktree step.
6. Prompt safety invariant: buy strategy must not use sell-only variables; generated code remains whitelist-only and forbidden-token safe.
7. ML invariant: Transformer or ML selector work is deferred to separate future research and excluded from this implementation.

## RALPLAN-DR

### Principles
- Separate exploration from promotion.
- Add explainable additive fields before changing selectors.
- Use human strategies as composition examples only, never performance truth or threshold source.
- Preserve operational isolation and UI worktree separation.
- Stop at phase gates instead of implementing all at once.

### Top 3 decision drivers
1. Avoid false confidence from short or in-sample discovery while preserving iteration speed.
2. Make dashboard status explainable through preset, gate stage, score fields, persistence, and hypothesis evidence.
3. Prevent LLM generation failure modes: invalid variables, buy/sell leakage, threshold copying, overfire, undertrade, MDD avoidance through zero trades, and timeout-prone sell formulas.

### Options

Option A, minimal wrapper: add only preset labels over current config.
Pros: smallest change. Cons: does not satisfy score, quality, prompt, and stop-point needs.

Option B-wide, original: full preset-first contract with scores, prompt revisions, pattern cards, persistence, hypotheses, and UI.
Pros: complete target coverage. Cons: too broad for one implementation wave and risks cross-layer coupling.

Option B-narrow staged, recommended: implement backend additive contract in gated slices, stopping after each phase for review.
Pros: satisfies target while limiting blast radius; preserves invariants; gives critic/architect checkpoints. Cons: needs multiple approval checkpoints.

Option C, ML selector now: deferred. Pros: possible later insight. Cons: violates ML deferral and adds research uncertainty.

Chosen recommendation: Option B-narrow staged.

## In scope and out of scope

In scope after explicit approval: fast/research/promotion preset resolver, research tick default through preset, min full-session promotion policy, staged MDD labels, two additive 100-point scores, prompt/system-prompt standard-form improvements, curated pattern-card composition library, preset-aware prompt/equity persistence, autopsy hypothesis feedback, and backend contract for later UI.

Out of scope: source edits in this planning stage, tests in this planning stage, project-wide commands, backtests, live/export/operating DB, performance claims from human DB, threshold copying, frontend execution in this worktree, Transformer/ML.

## Sequencing with stop points

Phase 1, preset resolver only. Add resolved policy metadata in config/launch layer. Stop after resolver and validation tests. Do not add scores yet.

Phase 2, additive score helpers only. Add pure `performance_score_100` and `condition_quality_score_100` data model. Stop after unit tests and architect review. Do not wire dashboard mutation yet.

Phase 3, loop persistence wiring only. Persist resolved preset and scores in generation/run state. Stop after fake-state tests. Do not change winner selection or export behavior.

Phase 4, prompt and pattern-card policy only. Update prompt assets and prompt builder with buy/sell standard forms, anti-copy, and curated pattern-card input. Stop after prompt snapshots and static negative cases.

Phase 5, hypothesis feedback expansion only. Extend autopsy hypothesis feedback with score deltas and quality reasons. Stop after fake generation tests.

Phase 6, UI contract handoff only. Produce backend contract for separate UI worktree. Stop before frontend edits unless separately approved.

Phase 7, promotion candidate guard only. Ensure promotion preset produces candidate status and ineligibility reasons, never export/live actions. Stop before any activation workflow.

## Phase acceptance criteria with exact fields, modules, failure behavior, and negative acceptance

### Phase 1 preset resolver
Modules: `ai_strategy_loop/config.py`, `ai_strategy_loop/launch_config.py`.
Fields: `dashboard_preset`, `resolved_preset_name`, `resolved_bt_timeframe`, `resolved_gate_stage`, `promotion_ineligible_reasons`.
Acceptance: `research` resolves `resolved_bt_timeframe=tick`; raw legacy config still resolves as legacy compatible unless preset explicitly set; `promotion` plus min plus `full_session_enabled=False` records ineligibility reason `min_full_session_required`.
Failure behavior: invalid preset raises validation error before loop start.
Negative acceptance: no change to raw `LoopConfig.bt_timeframe` default; no DB writes; no run loop side effects.
Stop point: reviewer approves resolved policy examples before Phase 2.

### Phase 2 scores
Modules: `ai_strategy_loop/fitness/score.py` plus any narrow quality helper module if needed.
Fields: `performance_score_100`, `condition_quality_score_100`, `mdd_gate_stage`, `condition_quality_reasons`.
Acceptance: deterministic scores from metrics/equity/static validation facts; score range clamped 0..100; existing `FitnessResult.score` and `GradedResult.graded` unchanged for same inputs.
Failure behavior: missing optional metrics produce neutral or explicit reason, not exception.
Negative acceptance: new scores do not select best/winner and do not relax hard gates.
Stop point: architect reviews formulas and edge cases before persistence wiring.

### Phase 3 loop persistence
Module: `ai_strategy_loop/controller/loop.py` plus state schema layer as needed.
Fields persisted per generation: `resolved_preset_name`, `performance_score_100`, `condition_quality_score_100`, `condition_quality_reasons`, `mdd_gate_stage`, `promotion_ineligible_reasons`.
Acceptance: fake outcome recording stores fields; absent fields on old runs render safely as null or default; winner remains hard-gate candidate only.
Failure behavior: score persistence failure is logged or captured as generation reason without crashing loop if optional, but schema migration failure fails fast before run start.
Negative acceptance: no export DB, no live DB, no operating DB, no strategy activation.
Stop point: state contract frozen before prompt changes and UI handoff.

### Phase 4 prompt and pattern-card policy
Modules: `ai_strategy_loop/brain/prompt.py`, `utility/ai_agent/system_prompt/v1/system_prompt.md`, `utility/ai_agent/system_prompt/v1/forbidden.md`.
Fields or inputs: `condition_library_enabled`, `condition_library_k`, `pattern_card_ids`, `threshold_copy_penalty_enabled`.
Acceptance: prompts include buy/sell standard forms; pattern-card block says copy composition grammar only; threshold copying is forbidden; min/tick variable guidance remains present.
Failure behavior: missing pattern-card source produces no examples and a quality reason, not loop crash.
Negative acceptance: no raw operating DB reads; no threshold literal copy from pattern cards; no sell-only variable in buy prompt examples.
Stop point: critic reviews prompt snapshots and anti-copy wording before any loop feedback expansion.

### Phase 5 hypothesis feedback
Module: `ai_strategy_loop/controller/loop.py` using existing hypothesis tracking path.
Fields: `hypotheses_json`, `d_performance_score_100`, `d_condition_quality_score_100`, quality failure reason deltas.
Acceptance: accepted/rejected hypotheses can cite MDD, trade frequency, payoff/give-back, performance score, and quality score deltas.
Failure behavior: hypothesis build/adjudication failure is absorbed and leaves null hypotheses, matching existing auxiliary behavior.
Negative acceptance: hypotheses do not alter hard gate, do not export, and do not read OOS/live data.
Stop point: review hypothesis examples before dashboard contract.

### Phase 6 dashboard contract
Modules: backend state serialization only; UI worktree separate.
Fields: all persisted fields above plus `candidate_status` and `promotion_ineligible_reasons`.
Acceptance: contract document or fixture shows old run compatibility and new run full field set.
Failure behavior: missing optional fields render as unknown, not failed run.
Negative acceptance: no frontend edits in backend phase.
Stop point: explicit UI-worktree approval required.

### Phase 7 promotion guard
Modules: config/loop/state only.
Fields: `candidate_status`, `promotion_gate_passed`, `promotion_ineligible_reasons`.
Acceptance: promotion preset can produce `candidate_status=promotion_candidate` only when frozen, persisted, full-session/OOS rules pass, score thresholds pass, and quality score threshold passes.
Failure behavior: unmet condition records ineligibility reason and keeps candidate non-promotable.
Negative acceptance: no export, no activation, no live DB write, no operating DB write.
Stop point: separate explicit approval required for any future export/activation plan.

## Focused verification matrix for future approved work

Preset resolver: unit tests for raw legacy config, fast, research tick default, promotion min full-session fail, invalid preset fail.
Score helpers: unit tests for zero trades, negative profit, MDD over cap, smooth profitable equity, missing payoff, high give-back, score clamp.
Quality score: static tests for valid buy, valid sell, sell-only variable in buy, forbidden token, missing terminal call, always-true gate, too few filter categories, expensive sell windows, threshold-copy similarity.
Loop persistence: fake state tests only; no backtest. Verify old-run null compatibility and new fields persisted.
Prompt snapshots: min/tick guidance, buy/sell templates, anti-copy few-shot, no live/export wording.
Hypothesis feedback: fake parent/current deltas for accepted, rejected, inconclusive outcomes.
DB isolation review: static path/config review proving no live/export/operating DB access in new paths.
UI contract: fixture-based contract tests in separate UI worktree after approval.

## Risks and mitigations

Risk: default behavior drift. Mitigation: explicit preset resolver only and tests for raw defaults.
Risk: all-at-once cross-layer churn. Mitigation: mandatory stop points after each phase.
Risk: score misuse as approval. Mitigation: candidate status and ineligibility reasons remain separate from scores.
Risk: threshold overfit. Mitigation: pattern-card abstraction, threshold stripping, anti-copy prompt, quality penalty.
Risk: prompt bloat. Mitigation: cap examples, use cards not full code, snapshot token size.
Risk: persistence bloat. Mitigation: downsample equity and store bounded prompt metadata.
Risk: promotion leakage. Mitigation: candidate metadata only; no export/live/operating DB code path.

## Handoff

After explicit approval only, recommended ledger handoff is `/skill:ultragoal <pending-approval.md>`. Use executor for bounded phases, architect before score/schema wiring, critic at stop points, team only if backend and UI worktrees are both approved.

## Pending approval

This revision remains pending approval and authorizes no implementation or verification commands.
