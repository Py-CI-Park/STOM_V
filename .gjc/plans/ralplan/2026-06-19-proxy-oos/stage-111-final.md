# Pending Approval Plan — Evolution Dashboard Condition-Discovery Update Based on `210bba854d03a8680ffebfb94f2544c52e81858b`

Status: **PENDING APPROVAL — planning only.** This plan does not authorize implementation, tests, source edits, OOS runs, exports, live trading, V3K/KHOPENAPI work, Transformer/ML work, operating DB changes, or promotion/export activation.

## Consensus Receipts

| Stage | Artifact | Verdict |
|---|---|---|
| Planner | `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-110-planner.md` | contract-first additive extension |
| Architect | `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-110-architect.md` | APPROVE / WATCH |
| Critic | `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-110-critic.md` | OKAY |

## Baseline Research Verdict

Baseline `210bba854d03a8680ffebfb94f2544c52e81858b` already includes the dashboard foundations that the older UI-aware plan treated as blocked or deferred:

| Baseline fact | Planning consequence |
|---|---|
| `LoopState.page_data` exists as additive consumer-safe pass-through. | Use it for condition-discovery page data instead of inventing a parallel state channel. |
| `GenerationInfo` carries telemetry events and telemetry contract metadata. | Preserve telemetry constraints when adding new condition-discovery signals. |
| `controller/state.py` supports prompt/equity storage and `to_loop_state(..., page_data=...)`. | New evidence/persistence fields can be derived into status/page-data. |
| `controller/telemetry.py` has closed, bounded, offline dashboard telemetry with source allowlist and protected-origin rejection. | Do not make new promotion/evidence decisions from arbitrary telemetry; extend only through the contract if needed. |
| `/status` already attaches telemetry. | Publish backend truth through existing status/page-data seams. |
| `/ui/evolution` routes/subtabs already exist. | Do not freeze `dashboard/app.py` as if the UI shell is absent; avoid broad route rewrites and extend existing UI deliberately. |
| Research index/records/frontend/webui-build support exists. | Condition-discovery panels should integrate with existing dashboard structure, not replace it. |
| Telemetry tests exist. | Preserve and extend those tests for new payloads. |

### Items still worth reflecting

| Requested item | Verdict |
|---|---|
| `fast / research / promotion` preset split | Reflect. Still needed. |
| Tick research/promotion `09:00-09:28` | Reflect. Still needed. |
| Min research/promotion full-session `09:00` to verified `15:18/15:19` | Reflect with explicit boundary verification. |
| Staged MDD gates | Reflect as hard gates. |
| 100-point performance score | Reflect as advisory only. |
| 100-point condition-generation-quality score | Reflect as advisory only. |
| CSV/trade/equity/prompt/validation evidence blockers | Reflect as promotion blockers. |
| System prompt and buy/sell standard-form improvements | Reflect. |
| Prompt/equity persistence policy | Reflect using existing persistence seams. |
| Autopsy hypothesis feedback | Reflect as non-authoritative prompt context. |
| Human DB composition library/pattern cards/few-shot | Reflect for creativity only; forbid copying thresholds/full expressions/performance truth. |
| Transformer/ML | Defer to future research. |
| Live/export/operating DB/V3K/KHOPENAPI | Keep out of scope. |

## Decision

Use **contract-first additive extension on top of 210bba**:

1. Establish a clean execution baseline at or consciously reconciled with `210bba`.
2. Add backend contracts/policies/state for presets, gates, evidence, advisory scores, prompt/equity persistence, autopsy hypotheses, and human-pattern-card metadata.
3. Publish backend truth through existing 210bba `/status`, `LoopState.page_data`, telemetry-safe seams, and evolution-dashboard structure.
4. Extend UI panels only after backend payload shape is stable.
5. Preserve human approval/export boundaries and keep Transformer/ML for a later plan.

## Principles

1. **Backend truth first.** UI displays only backend-published truth; it must not invent pass/fail status.
2. **Scores are advisory.** `performance_score_100` and `condition_quality_score_100` explain/rank only; they never promote or export.
3. **Evidence and hard gates are authoritative.** Missing required CSV/trade/equity/prompt/validation evidence blocks promotion regardless of score.
4. **Human approval is mandatory.** Promotion/export/operating DB/live use remains behind explicit approval.
5. **Use human DB as grammar, not answers.** Pattern cards may teach composition; threshold/full-expression/performance copying is forbidden.
6. **Use 210bba seams.** Extend `/status`, `page_data`, telemetry, and `/ui/evolution` incrementally; avoid broad route rewrites.

## Alternatives Considered

| Option | Pros | Cons | Decision |
|---|---|---|---|
| Contract-first additive extension | Safe, testable, matches 210bba seams. | Requires backend work before full UI payoff. | Chosen. |
| UI-first prototype | Fast visual feedback. | Risk of dashboard showing states not enforced by backend. | Rejected. |
| Backend-only policy phase | Lowest behavior risk. | Weak operator visibility and less dashboard validation. | Not enough. |
| Old app-freeze plan | Merge-safe when UI absent. | Obsolete because 210bba already has UI routes/status telemetry. | Rejected. |

## Phased Plan

### Phase 0 — Baseline hygiene

| Work | Acceptance |
|---|---|
| Start from clean `210bba` baseline or explicit reconciliation branch. | Execution worktree is not a dirty mix of local evidence/runtime/UI changes. |
| Preserve 210bba telemetry/status/dashboard behavior. | Existing telemetry/status/dashboard tests pass before changes. |
| Exclude runtime artifacts. | `.gjc/`, `_database/`, `ai_strategy_loop/state/`, caches, generated evidence, and accidental runtime DBs are not source inputs. |

### Phase 1 — Backend contract and policy

| Work | Acceptance |
|---|---|
| Add condition-discovery contract/payload fields. | Additive and null-safe; old status consumers still parse. |
| Define presets. | `fast`, `research`, `promotion` documented with eligibility semantics. |
| Define time windows. | Research/promotion tick defaults to `09:00-09:28`; min requires verified full session `09:00-15:18/15:19`. |
| Define staged MDD gates. | MDD gates are hard blockers, not score decorations. |
| Define evidence schema. | CSV/trade/equity/prompt/validation states and blocker reasons explicit. |

### Phase 2 — Advisory scoring and promotion authority

| Work | Acceptance |
|---|---|
| Add `performance_score_100`. | 0-100, advisory only, reasoned. |
| Add `condition_quality_score_100`. | 0-100, advisory only, reasoned. |
| Protect authority boundary. | Tests prove high scores cannot override evidence blockers, hard gates, or human approval. |
| Keep promotion/export inert. | Candidate can be marked pending review only; no export/live/DB action. |

### Phase 3 — Persistence and feedback integration

| Work | Acceptance |
|---|---|
| Publish prompt/equity persistence state. | Prompt/equity present/missing/unavailable states visible and auditable. |
| Add autopsy hypotheses. | Accepted/rejected/deferred hypotheses include provenance and are advisory prompt context only. |
| Add human DB pattern-card metadata. | Schema, source labels, normalized hashes, threshold stripping, dedup, anti-copy checks. |
| Enforce anti-copy. | Threshold/full-expression/performance copying rejected or flagged. |

### Phase 4 — Status/page-data publication

| Work | Acceptance |
|---|---|
| Publish through 210bba seams. | Use existing `/status`, `LoopState.page_data`, `GenerationInfo`, and telemetry-safe structures. |
| Preserve telemetry contract. | Closed source allowlist, bounded event count, protected-origin rejection remain true. |
| Avoid route churn. | No broad `dashboard/app.py` route rewrite; any route change is minimal and justified. |

### Phase 5 — Dashboard UI extension

| Work | Acceptance |
|---|---|
| Add dashboard panels/subtabs inside existing `/ui/evolution` structure. | Panels show presets, evidence health, hard gates, advisory scores, prompt/equity state, hypotheses, pattern cards, and approval state. |
| Visual hierarchy. | Hard blockers > human approval > advisory scores. |
| Existing UI conventions. | Integrate with 210bba dashboard-pages/research-index/records/webui-build patterns. |
| Frontend tests. | Dashboard tests cover missing fields, blocked states, advisory labeling, and approval-required states. |

### Phase 6 — ADR and acceptance hardening

| Work | Acceptance |
|---|---|
| ADR | Documents advisory scoring, evidence authority, human approval, human-pattern-card constraints, no live/export/DB/V3K/KHOPENAPI/Transformer, and use of 210bba seams. |
| Focused verification | Backend, dashboard, telemetry, prompt/pattern, and boundary tests pass. |
| Review | Architect/Critic/QA review confirms no authority leaks or operational boundary violations. |

## Verification Matrix

| Area | Required verification |
|---|---|
| Baseline preservation | 210bba dashboard/status/telemetry tests pass before and after changes. |
| Contract compatibility | New fields are additive/null-safe; absent/unknown fields are tolerated. |
| Presets/windows | Tests cover `fast`, `research`, `promotion`, tick `09:00-09:28`, min full-session boundary handling. |
| MDD gates | Staged MDD failures block promotion even when scores are high. |
| Advisory scores | Scores bounded 0-100 and cannot set promotion/export/final approval. |
| Evidence health | Missing CSV/trade/equity/prompt/validation produces explicit blockers. |
| Persistence | Prompt/equity present/missing/unavailable states published correctly. |
| Autopsy | Hypotheses preserve provenance and remain advisory. |
| Human DB safety | Pattern/few-shot usage rejects threshold/full-expression/performance copying. |
| Telemetry | Source allowlist, bounded payloads, and protected-origin rejection remain intact. |
| Dashboard UI | Panels render blockers, advisory labels, preset state, evidence health, and approval-required promotion/export state. |
| Boundaries | Static/code review confirms no live/export/operating DB/V3K/KHOPENAPI/Transformer implementation. |

## Risks and Controls

| Risk | Control |
|---|---|
| Advisory score becomes de facto approval. | UI labels, tests, and ADR make evidence/hard gates/human approval dominant. |
| UI diverges from backend truth. | Backend-first payload contracts; UI consumes only published truth. |
| Human DB examples leak into generated code. | Pattern-card hashes, threshold stripping, provenance, anti-copy tests. |
| `15:18/15:19` ambiguity causes inconsistent min promotion. | Boundary verification before promotion eligibility. |
| Telemetry expansion becomes decision authority. | Keep telemetry observational; decisions derive from contract/evidence/hard gates. |
| Dirty worktree contaminates execution. | Execute from clean 210bba baseline or explicit reconciliation branch. |

## Pending Approval

This plan is complete for consensus planning and remains **pending approval**. Recommended execution handoff after explicit approval:

```text
/skill:ultragoal .gjc/plans/ralplan/2026-06-19-proxy-oos/pending-approval.md
```

Execution instruction should say: use `210bba854d03a8680ffebfb94f2544c52e81858b` as the baseline, first establish a clean/reconciled execution worktree, then implement contract-first additive phases. Do not implement live/export/operating DB/V3K/KHOPENAPI/Transformer work, and do not treat advisory scores as promotion authority.
