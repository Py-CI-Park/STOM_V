# Revision 105 planner artifact

Status: pending approval only. No implementation, tests, builds, backtests, live/export/operating DB, V3K, KHOPENAPI, or Transformer/ML work is authorized.

## Required corrections from architect BLOCK

1. Score authority is advisory only. `performance_score_100` and `condition_quality_score_100` are display, explanation, sorting, triage, and ranking fields. They never grant promotion authority, never set `promotion_gate_passed`, never override hard gates, never override evidence blockers, and never replace frozen-candidate review or explicit human approval.
2. Evidence completeness is explicit. Missing required CSV, trade rows, equity series, prompt record, or validation evidence yields `evidence_status=evidence_blocker`, `candidate_status=not_promotable`, and stable blocker reasons. Missing evidence never passes by default.
3. Tick/min policy is preset-scoped. Raw defaults remain backward compatible. Research and promotion presets default to tick 09:00-09:28. Min research or promotion must use full-session 09:00 through the verified 15:18/15:19 min boundary; otherwise it is promotion-ineligible.
4. Pattern cards are anti-copy artifacts. They require schema fields, normalized hashes, dedup, source labels, no threshold copying, no full expression copying, and negative acceptance cases.
5. Transformer/ML remains deferred. No live/export/operating DB, V3K, or KHOPENAPI access. Final plan remains pending approval.

## Recommended option

Option B-narrow staged remains recommended over Option A minimal labels, Option B-wide all-at-once, and Option C ML selector. Narrow Option B adds backend contract fields in stop-point phases and preserves current loop behavior. It does not treat scores as promotion authority.

## Architect WATCH invariants

- Raw `LoopConfig()` defaults remain compatible; preset overlays are explicit.
- Existing hard gate and graded selection semantics remain unchanged.
- 100-point scores are advisory/ranking only.
- Evidence completeness is a separate blocking authority.
- Promotion preset marks candidates only; it never exports or activates.
- No live/export/operating DB, V3K, or KHOPENAPI.
- UI worktree remains separate after backend contract approval.
- Buy prompts and generated buy code must not use sell-only variables.
- Transformer/ML is future research only.

## Authority model

Advisory fields:
- `performance_score_100`
- `condition_quality_score_100`
- `condition_quality_reasons`
- `mdd_gate_stage`

These fields may rank and explain. They must not make a strategy promotable.

Promotion and evidence fields:
- `evidence_status`: `complete`, `partial`, `evidence_blocker`, `not_required`
- `evidence_blockers`: stable reason list
- `csv_evidence_status`: `present`, `missing`, `unreadable`, `empty`
- `trade_evidence_status`: `present`, `missing`, `zero_trades`, `insufficient_rows`
- `equity_evidence_status`: `present`, `missing`, `unreadable`, `insufficient_points`
- `prompt_evidence_status`: `present`, `missing`, `hash_only`, `disabled`
- `validation_evidence_status`: `present`, `missing`, `failed`
- `candidate_status`: `discovery_only`, `research_candidate`, `not_promotable`, `promotion_candidate_pending_approval`
- `promotion_ineligible_reasons`: stable reason list
- `promotion_gate_passed`: hard/evidence/policy field, not score-derived

Required failure behavior:
- Missing CSV => blocker `missing_csv_evidence`
- Empty or zero-trade CSV => blocker `zero_trade_evidence`
- Missing or insufficient equity => blocker `missing_equity_evidence` or `insufficient_equity_points`
- Required prompt evidence missing => blocker `missing_prompt_evidence`
- Static validation evidence missing or failed => blocker `missing_validation_evidence` or `validation_failed`
- Any blocker => `candidate_status=not_promotable` and `promotion_gate_passed=false`

## Preset-scoped tick/min policy

Fast preset: quick discovery only; no promotion eligibility.

Research preset: default tick, 09:00-09:28. Min override is allowed only as research-min and must use 09:00 through verified 15:18/15:19 full-session boundary for any later promotion consideration.

Promotion preset: default tick, 09:00-09:28. Min promotion must use 09:00 through verified 15:18/15:19. Candidate must be frozen. LLM mutation is not allowed during promotion review. Advisory scores only rank candidates.

Raw defaults: unchanged unless explicit preset resolver is invoked.

## Pattern-card anti-copy schema

Required card fields:
- `card_id`
- `source_label`
- `source_kind`: `human_composition`, `loop_candidate`, or `research_pattern`
- `timeframe_scope`: `tick`, `min`, or `both`
- `side`: `buy`, `sell`, or `pair`
- `pattern_summary`
- `variable_families`
- `composition_skeleton`
- `threshold_policy`: `stripped`, `bucketed`, or `forbidden_to_copy`
- `forbidden_copy_units`
- `normalized_expression_hash`
- `normalized_threshold_hash`
- `dedup_hash`
- `provenance_note`
- `allowed_prompt_excerpt`

Rules:
- Normalize whitespace, comments, aliases, numeric literals, comparison operators, and boolean ordering before hashing.
- Deduplicate by `dedup_hash` and near-duplicate skeleton hash.
- Do not inject cards missing source label, threshold policy, or hashes.
- Do not copy literal thresholds, exact bands, or full expressions.
- Source labels are provenance only, not performance proof.

Negative acceptance:
- Full expression copied from card => quality fail.
- Numeric threshold or exact band copied from card => quality fail.
- Missing schema or hash => card not injectable.
- Human DB performance field imported as truth => fail.

## Staged implementation and stop points

Phase 1, preset and evidence contract. Modules: `ai_strategy_loop/config.py`, `ai_strategy_loop/launch_config.py`. Fields: preset, resolved session, evidence status, ineligible reasons. Stop for architect review.

Phase 2, advisory scores. Module: `ai_strategy_loop/fitness/score.py` or narrow helper. Add 0..100 score fields. Existing hard/graded scores unchanged. Stop for formula review.

Phase 3, loop persistence. Module: `ai_strategy_loop/controller/loop.py` plus state schema. Persist preset, evidence, advisory scores, quality reasons. Evidence blockers force not promotable. Stop for state contract freeze.

Phase 4, prompt and pattern cards. Modules: `ai_strategy_loop/brain/prompt.py`, `utility/ai_agent/system_prompt/v1/system_prompt.md`, `utility/ai_agent/system_prompt/v1/forbidden.md`. Add buy/sell standard forms, anti-copy text, pattern-card validation. Stop for critic snapshot review.

Phase 5, hypothesis feedback. Module: `ai_strategy_loop/controller/loop.py`. Add deltas for advisory scores and evidence blockers while keeping hypotheses non-authoritative. Stop for example review.

Phase 6, dashboard contract handoff. Backend serialization only. UI worktree separate and separately approved. Stop before frontend edits.

Phase 7, promotion guard. Candidate can be pending approval only when hard gates pass, preset policy passes, evidence is complete, candidate is frozen, and promotion review policy passes. Scores are not sufficient. Stop before any export or activation plan.

## Focused verification matrix for future approved work

- Preset tests: raw compatibility, research tick 09:00-09:28, promotion tick 09:00-09:28, min full-session 09:00 to 15:18/15:19, invalid preset failure.
- Evidence tests: missing CSV, unreadable CSV, empty CSV, zero trades, missing equity, insufficient equity, missing prompt evidence, missing validation evidence all block promotion.
- Score authority tests: high scores plus missing evidence remain not promotable; high scores plus hard-gate failure remain not promotable; scores do not set promotion fields.
- Quality tests: valid buy/sell, sell-only variable in buy, forbidden token, missing terminal call, always-true gate, too few filter categories, expensive sell windows.
- Pattern-card tests: schema required, source labels, hash dedup, threshold-copy detection, full-expression-copy detection, no performance truth import.
- Prompt snapshots: min/tick guidance, buy/sell templates, anti-copy few-shot, no live/export wording.
- Loop fake-state tests: persist fields without backtests; old-run null compatibility; evidence blockers serialize.
- Isolation review: no live/export/operating DB, V3K, KHOPENAPI.

## Pending approval

This pass remains pending approval. After explicit approval only, recommended ledger handoff is `/skill:ultragoal <pending-approval.md>`. Use phase stop points and do not implement all at once.
