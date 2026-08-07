# Planner Stage 103 — Evolution Dashboard Condition Discovery Improvements

Status: planning artifact only; pending approval. No source execution is authorized by this plan.

## RALPLAN-DR Summary

### Principles
1. Separate exploration from promotion: fast, research, and promotion presets must have different risk and evidence thresholds.
2. Preserve official STOM evidence boundaries: condition candidates remain research artifacts until official OOS and human approval.
3. Improve generation creativity without copying: human DB conditions teach composition grammar, not thresholds or performance truth.
4. Make feedback scientific: autopsy outputs should become testable hypotheses with accepted/rejected status.
5. Keep Transformer/ML deferred: use it later as a helper layer, not as a direct trading-decision authority.

### Decision Drivers
1. User goal: discover condition expressions that can eventually support live-trading candidates, not just CSV combinations.
2. Current implementation facts: `LoopConfig` defaults include MDD 35%, `bt_timeframe="min"`, prompt/equity persistence OFF, many quality gates OFF, and warm STOM backtest engine support.
3. Operational safety: no live/export/operating DB/V3K/KHOPENAPI mutation; dashboard final approval remains the export boundary.

### Viable Options

| Option | Summary | Pros | Cons | Verdict |
|---|---|---|---|---|
| A | Minimal tuning only | Low risk; changes few defaults | Does not fix creativity/reproducibility/score interpretation | Reject |
| B | Preset-first contract + scoring/prompt/library improvements | Clear phases, preserves compatibility, addresses user concerns | More surfaces to implement and test | Recommended |
| C | Full ML/Transformer integration now | Ambitious; may improve prediction later | Too high-risk; leakage/overfit risk; not needed before generation basics improve | Defer |

Recommendation: Option B.

## Proposed Scope

### In scope
- Define fast/research/promotion presets for the evolution dashboard.
- Add or expose a tick-oriented research preset: tick, 09:00:00-09:28:00, warm engine, prompt/equity persistence enabled.
- Define min full-session policy: min research/promotion uses 09:00 through the verified 15:18/15:19 database boundary.
- Replace one-size gate interpretation with staged gate policy: discovery loose, research medium, promotion strict.
- Add a deterministic 100-point performance score for display/ranking.
- Add a deterministic 100-point generation-quality score for condition-code quality independent of PnL.
- Improve prompt/system guidance and buy/sell standard forms without bypassing existing whitelist/forbidden rules.
- Turn autopsy feedback into structured hypotheses with parent-delta adjudication and rejected-hypothesis feedback.
- Build a human-condition composition library from read-only human DB/source conditions: pattern cards, composition grammar, few-shot examples, anti-copy safeguards.
- Keep Transformer/ML as a future research section with no implementation in this plan.

### Out of scope
- Live/export/operating strategy DB writes.
- V3K/KHOPENAPI/live broker changes.
- Direct execution or official promotion of any generated condition.
- Transformer/ML model training or inference implementation in this cycle.
- UI redesign beyond planned dashboard fields/contracts; current UI worktree should own frontend changes if execution is later approved.

## Proposed Implementation Phases

| Phase | Work | Files likely affected after approval | Acceptance |
|---:|---|---|---|
| 1 | Preset model and config contracts | `ai_strategy_loop/config.py`, `ai_strategy_loop/launch_config.py`, tests | `fast/research/promotion` presets are deterministic; raw custom config remains backward compatible |
| 2 | Timeframe/session policy | config/launch helpers, warm config tests | Research preset defaults to tick 09:00-09:28; min policy documents/uses full-session boundary for research/promotion |
| 3 | Staged gate policy | `fitness/score.py` or new criteria module | Discovery/research/promotion thresholds are visible and do not silently relax promotion |
| 4 | 100-point performance score | `fitness/score.py`, dashboard payloads | Score decomposes into profit, MDD, Calmar, uptrend R2, frequency, exit quality, multi-period stability |
| 5 | 100-point generation-quality score | brain analysis module, dashboard payloads | Syntax, whitelist/scope, category diversity, niche clarity, no-op avoidance, compute budget, exit structure are scored |
| 6 | Prompt and standard forms | `brain/prompt.py`, system prompt assets | Buy template prefers explicit niche + gated `매수=False` pattern; sell template enforces stop/trailing/time-exit and compute budget |
| 7 | Autopsy hypothesis feedback | `controller/loop.py`, hypothesis helpers, state schema if needed | Autopsy emits structured hypotheses and later accepts/rejects via parent deltas; rejected hypotheses feed prompts |
| 8 | Human composition library | read-only ingestion from human DB/source refs; new research artifact/module | Pattern cards capture composition grammar only; thresholds/numeric constants are not copied; few-shot K remains bounded |
| 9 | Governance and verification | tests/docs | No protected path mutations; final plan remains pending approval until user authorizes execution |

## Preset Targets

| Setting | Fast | Research | Promotion |
|---|---:|---:|---:|
| Purpose | cheap exploration | serious candidate discovery | promotion review candidate |
| Timeframe default | user selectable | tick default | strategy-specific but frozen |
| Tick window | 09:00-09:28 | 09:00-09:28 | 09:00-09:28 |
| Min window | bounded allowed | full-session policy | full-session policy |
| MDD cap | 35% | 20-25% | 10-15% |
| `prompt_logging_enabled` | optional | ON | ON required |
| `equity_points_enabled` | optional | ON | ON required |
| `research_oos_mode` | disabled/advisory | advisory | promotion_only |
| Human approval/export | forbidden | forbidden | separate approval only |

## 100-Point Score Drafts

Performance score:
- Profit: 20
- MDD: 20
- Calmar: 15
- Uptrend R2: 15
- Frequency: 10
- Exit quality/TPI/payoff: 10
- Multi-period stability: 10

Generation-quality score:
- Syntax/whitelist/scope safety: 15
- Variable-category diversity: 15
- Market niche clarity: 15
- Composition creativity: 20
- Overfire/no-op prevention: 10
- Compute-budget safety: 10
- Sell/exit structure quality: 15

## Human Composition Library Rules

- Treat human DB conditions as composition grammar, not signal proof.
- Extract variable categories, gate ordering, time/cap/regime niches, and exit motifs.
- Do not copy thresholds or whole expressions.
- Tag each pattern card with source, timeframe, side, categories, risk notes, and anti-copy guidance.
- Few-shot examples should be bounded, diversified, and normalized to prevent seed fingerprint repetition.

## Transformer/ML Future Research

Deferred research only. Later viable directions: parameter suggestion, regime classifier, candidate second-stage filter, surrogate fitness model. End-to-end trading prediction is last priority due to leakage and explainability risk.

## Verification Plan After Approval

- Focused unit tests for preset resolution and config validation.
- Unit tests for staged gate thresholds and 100-point score decomposition.
- Unit tests for generation-quality scorer with safe/unsafe buy/sell snippets.
- Prompt snapshot tests for system prompt additions and anti-copy language.
- State/payload tests for prompt/equity persistence flags and dashboard contracts.
- No project-wide test delegation to subagents; parent runs final focused tests.

## Pending Approval Boundary

This artifact does not execute implementation. Recommended execution after explicit approval: `/skill:ultragoal <pending-approval.md>`.
