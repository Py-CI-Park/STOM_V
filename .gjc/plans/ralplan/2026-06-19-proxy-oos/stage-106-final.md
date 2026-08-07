# Pending Approval Plan — Evolution Dashboard Condition Discovery System Improvements

Status: **PENDING APPROVAL — planning only.** This plan does not authorize implementation, tests, source edits, OOS runs, exports, live trading, V3K/KHOPENAPI work, Transformer/ML work, or operating DB changes.

Source request: improve STOM's evolution-dashboard condition-discovery system while deferring Transformer/ML to a later research plan. Current scope focuses on condition-generation quality, staged presets/gates, scoring visibility, prompt/equity persistence, autopsy hypothesis feedback, and a human-condition composition library used for creativity rather than performance copying.

## Consensus Receipts

| Stage | Artifact | Verdict |
|---|---|---|
| Planner | `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-103-planner.md` | Option B recommended |
| Critic 1 | `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-103-critic.md` | ITERATE |
| Revision 1 | `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-104-revision.md` | narrowed staged plan |
| Architect 2 | `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-104-architect.md` | REQUEST CHANGES |
| Revision 2 | `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-105-revision.md` | blockers resolved |
| Architect final | `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-105-architect.md` | APPROVE / WATCH |
| Critic final | `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-105-critic.md` | OKAY |

## Decision

Proceed, after explicit execution approval only, with **Option B-narrow staged**: implement backend-first evolution-dashboard improvements in phase stop points. Do not implement a broad all-at-once refactor, do not start Transformer/ML work, and do not change live/export/operating DB/V3K/KHOPENAPI boundaries.

## Principles

1. **Research and promotion are separate authorities.** Research scores may rank or explain; only hard gates, complete evidence, frozen-candidate review, and explicit human approval can create a promotion candidate.
2. **Preserve raw compatibility.** Existing raw `LoopConfig()` behavior remains compatible unless an explicit preset resolver is invoked.
3. **Make evidence health explicit.** Missing CSV, trade, equity, prompt, or validation evidence is not a soft warning; it blocks promotion metadata.
4. **Learn human composition grammar, not human thresholds.** Human DB conditions may supply pattern cards and structural creativity, never literal thresholds, full expressions, or performance truth.
5. **Keep scope research-only.** No live/export/operating DB, V3K, KHOPENAPI, frontend work in this lane, or Transformer/ML implementation.

## Decision Drivers

| Driver | Plan response |
|---|---|
| User wants tick-first condition research | Research/promotion presets default to tick 09:00-09:28. |
| User wants min full-session behavior | Min research/promotion requires full session 09:00 through verified 15:18/15:19 boundary. |
| User wants less misleading gates/scores | Separate hard gates, advisory 100-point scores, and evidence blockers. |
| User wants better condition creativity | Add validated human-composition pattern cards and anti-copy few-shot support. |
| User wants reproducibility | Prompt/equity evidence states become first-class; research/promotion presets require them. |

## Non-Goals

- No Transformer/ML model work in this plan; keep it as a future research item.
- No live trading, export, operating DB mutation, KHOPENAPI, V3K, or broker runtime work.
- No UI/frontend edits in this worktree; backend contract can be handed to the UI worktree later.
- No direct promotion, activation, or 실매매 use from a score alone.
- No copying human DB expressions, literal thresholds, or exact bands.

## Planned Scope

### Phase 1 — Preset and evidence contract

Target surfaces: `ai_strategy_loop/config.py`, `ai_strategy_loop/launch_config.py`, state/serialization seams.

| Item | Contract |
|---|---|
| Presets | `fast`, `research`, `promotion` explicit resolver. |
| Raw defaults | Existing raw defaults remain compatible. |
| Research preset | Tick default, 09:00-09:28, prompt/equity evidence preferred or required by policy. |
| Promotion preset | Tick default, 09:00-09:28, frozen candidate, complete evidence, no LLM mutation during review. |
| Min policy | Research/promotion min requires full session 09:00 through verified 15:18/15:19 boundary. |
| Evidence fields | Add `evidence_status`, component evidence states, blockers, and promotion-ineligible reasons. |

Stop point: architect review before score implementation.

### Phase 2 — Advisory 100-point score fields

Target surface: `ai_strategy_loop/fitness/score.py` or a narrow helper.

| Score | Authority | Purpose |
|---|---|---|
| `performance_score_100` | Advisory only | Display, sorting, triage, explanation. |
| `condition_quality_score_100` | Advisory only | Static/generative quality explanation. |
| Existing hard gates | Authoritative for research pass/fail | Must remain unchanged unless separately approved. |
| Evidence status | Authoritative for promotion blocking | Missing evidence blocks promotion regardless of score. |

Performance score proposal, 100 points:

| Dimension | Points |
|---|---:|
| Profit / baseline-relative return | 20 |
| MDD / drawdown control | 20 |
| Calmar / risk-adjusted return | 15 |
| Uptrend smoothness / equity R² | 15 |
| Trade frequency health | 10 |
| Exit quality / payoff / TPI display | 10 |
| Multi-period stability | 10 |

Condition-generation-quality score proposal, 100 points:

| Dimension | Points |
|---|---:|
| STOM syntax and forbidden-token safety | 15 |
| Variable-family diversity | 15 |
| Market niche clarity | 15 |
| Composition creativity | 20 |
| Overfire and always-true prevention | 10 |
| Execution-cost safety | 10 |
| Exit-structure quality | 15 |

Stop point: formula review. Verify scores cannot set `promotion_gate_passed`.

### Phase 3 — Loop persistence and evidence health

Target surfaces: `ai_strategy_loop/controller/loop.py`, `ai_strategy_loop/controller/state.py`, dashboard-state payloads.

Persist:
- resolved preset and session policy,
- advisory scores and reason lists,
- evidence status fields,
- candidate status,
- stable promotion-ineligible reasons,
- old-run null compatibility.

Required blocker behavior:

| Missing/invalid evidence | Required state |
|---|---|
| Missing CSV | `evidence_status=evidence_blocker`, reason `missing_csv_evidence` |
| Empty or zero-trade CSV | reason `zero_trade_evidence` |
| Missing/insufficient equity | reason `missing_equity_evidence` or `insufficient_equity_points` |
| Missing prompt evidence where required | reason `missing_prompt_evidence` |
| Missing/failed validation | reason `missing_validation_evidence` or `validation_failed` |
| Any blocker | `candidate_status=not_promotable`, `promotion_gate_passed=false` |

Stop point: state contract freeze.

### Phase 4 — Prompt and standard condition-form improvements

Target surfaces: `ai_strategy_loop/brain/prompt.py`, `ai_strategy_loop/brain/generator.py`, `utility/ai_agent/system_prompt/v1/system_prompt.md`, `utility/ai_agent/system_prompt/v1/forbidden.md`.

Buy-side prompt direction:
- prefer `매수 = False` then enable only when all intended filters pass,
- require explicit market niche statement,
- guide filter families: time, market-cap/price zone, liquidity, price regime, execution strength, order-book pressure,
- forbid sell-only variables in buy code,
- reject always-true or meaningless gates.

Sell-side prompt direction:
- require bounded exit structure: stop-loss, give-back/trailing/profit-protection, and time exit,
- constrain expensive repeated window calls,
- keep MDD-control and exit-edge feedback preset-scoped,
- do not optimize solely for one short interval.

Stop point: critic snapshot review of prompt text and negative cases.

### Phase 5 — Human DB composition library and pattern cards

Human DB conditions are used as **composition grammar** only.

Required card schema:

| Field | Purpose |
|---|---|
| `card_id` | Stable card id |
| `source_label` | Provenance label, not performance proof |
| `source_kind` | `human_composition`, `loop_candidate`, or `research_pattern` |
| `timeframe_scope` | `tick`, `min`, or `both` |
| `side` | `buy`, `sell`, or `pair` |
| `pattern_summary` | Natural-language structure |
| `variable_families` | Price/liquidity/execution/order-book/time/cap families |
| `composition_skeleton` | Threshold-stripped structure |
| `threshold_policy` | `stripped`, `bucketed`, or `forbidden_to_copy` |
| `forbidden_copy_units` | Tokens/expressions/thresholds not reusable |
| `normalized_expression_hash` | Full-expression copy guard |
| `normalized_threshold_hash` | Threshold-copy guard |
| `dedup_hash` | Duplicate/near-duplicate guard |
| `allowed_prompt_excerpt` | Safe prompt snippet |

Negative acceptance:
- full expression copied from a card => fail,
- numeric threshold or exact band copied => fail,
- missing schema/hash/source label => not injectable,
- human DB performance imported as truth => fail.

Stop point: example review with at least one valid card and rejected copy case.

### Phase 6 — Autopsy hypothesis feedback

Target surface: `ai_strategy_loop/controller/loop.py` and existing autopsy feedback seams.

Add structured, non-authoritative hypothesis records:
- accepted/rejected/deferred hypotheses,
- recent-N-generation repeated patterns,
- buy vs sell failure separation,
- parent/child delta summaries,
- rejected hypotheses as prompt avoid-signals,
- evidence-blocker awareness.

Stop point: example review. Hypotheses must not override gates or evidence.

### Phase 7 — Dashboard contract handoff and promotion guard

Backend serialization only in this plan. UI/frontend implementation remains separate.

Promotion candidate can only be marked pending approval when:
- hard gates pass,
- preset policy passes,
- required evidence is complete,
- candidate is frozen,
- review policy passes,
- explicit human approval remains required before export/live use.

Scores alone are never sufficient.

Stop point: stop before any frontend edits, export, or activation plan.

## Verification Matrix for Approved Execution

| Area | Required checks |
|---|---|
| Presets | raw compatibility; research tick 09:00-09:28; promotion tick 09:00-09:28; min full-session 09:00 to verified 15:18/15:19; invalid preset failure. |
| Evidence blockers | missing CSV, unreadable CSV, empty CSV, zero trades, missing equity, insufficient equity, missing prompt evidence, missing validation evidence all block promotion. |
| Score authority | high scores plus missing evidence remain not promotable; high scores plus hard-gate failure remain not promotable; scores do not set promotion fields. |
| Condition quality | valid buy/sell; sell-only variable in buy; forbidden token; missing terminal call; always-true gate; too few filter categories; expensive sell windows. |
| Pattern cards | schema required; source labels; normalized hashes; dedup; threshold-copy detection; full-expression-copy detection; no performance truth import. |
| Prompt snapshots | tick/min guidance, buy/sell templates, anti-copy few-shot, no live/export wording. |
| Loop fake-state | new fields persist without backtests; old-run null compatibility; evidence blockers serialize. |
| Isolation | no live/export/operating DB, V3K, KHOPENAPI, Transformer/ML implementation. |

## Risks and Controls

| Risk | Control |
|---|---|
| 100-point scores become hidden promotion gates | Explicit advisory-only fields plus tests that scores never set promotion status. |
| Missing evidence is hidden by good scores | Evidence blockers override promotion metadata. |
| Tick/min default changes break existing runs | Raw defaults unchanged; preset resolver is explicit. |
| Human DB few-shot becomes copy engine | Threshold stripping, normalized hashes, anti-copy negative tests. |
| Scope creeps into UI/live/export/ML | Phase stop points and explicit non-goals. |

## ADR

- **Decision:** Use Option B-narrow staged backend contract and prompt-quality improvement plan.
- **Drivers:** Improve condition-generation quality, preserve safety boundaries, separate exploration from promotion, and increase reproducibility.
- **Alternatives considered:**
  - Option A minimal labels: safer but too shallow; would not fix prompt quality, evidence health, or composition creativity.
  - Option B-wide all-at-once: too risky and too broad for this worktree.
  - Option C Transformer/ML selector: premature; deferred to future research.
- **Why chosen:** It addresses the user's requested improvements while preserving repository boundaries and adding stop points.
- **Consequences:** Execution must proceed phase-by-phase with reviews. Scores remain advisory. UI/frontend and ML work require separate plans.
- **Follow-ups:** After backend contract approval/execution, hand UI schema to the UI worktree; later create a separate Transformer/ML feasibility plan.

## Pending Approval

This plan is complete for consensus planning and remains **pending approval**. Recommended execution handoff after explicit approval:

```text
/skill:ultragoal .gjc/plans/ralplan/2026-06-19-proxy-oos/pending-approval.md
```

Do not implement directly from this conversation without explicit execution approval.
