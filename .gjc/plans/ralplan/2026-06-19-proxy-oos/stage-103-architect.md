## Summary
Stage 103 is architecturally viable as a pending-approval plan, not as execution authority. I recommend `COMMENT` with `WATCH` status: proceed only if the final execution plan carries the hard-gate, persistence, preset, and anti-copy constraints below as explicit invariants.

## Analysis
Scope reviewed: `.gjc/plans/ralplan/2026-06-19-proxy-oos/stage-103-planner.md`; source context inspected only to verify the planner claims. No product files were edited and no tests/builds/formatters/project commands were run.

Evidence from the planner artifact:
- The artifact preserves the planning boundary and says no source execution is authorized (`stage-103-planner.md:1-3`, `:135-138`).
- It chooses Option B: preset-first contracts plus scoring/prompt/library improvements, while rejecting minimal tuning and deferring Transformer integration (`stage-103-planner.md:19-29`, `:112-115`).
- It explicitly excludes live/export/operating DB writes, V3K/KHOPENAPI/live broker changes, direct promotion, and Transformer implementation (`stage-103-planner.md:45-51`).
- It calls for tick research defaults, min full-session policy, staged gates, display/ranking scores, prompt/equity persistence, autopsy hypotheses, and a human composition library (`stage-103-planner.md:33-42`, `:56-72`, `:76-88`, `:91-110`).

Evidence from current source context:
- Current defaults are conservative/backward-compatible: `LoopConfig.mdd_cap=35.0`, `bt_timeframe="min"`, `bt_engine_mode="warm"`, `bt_universe_end_time=92800`, `full_session_enabled=False`, and `bt_min_universe_end_time=151900` (`ai_strategy_loop/config.py:29-138`). The launch surface validates `bt_timeframe` and exposes `research_oos_mode`, full-session, min end-time, and warm/cold controls (`ai_strategy_loop/launch_config.py:37-57`, `:101-137`, `:173-220`).
- Hard gates currently live in `compute_fitness`: frequency, MDD cap, positive profit, optional TPI; `score` is `calmar * uptrend_r2 * gate`, and `gate_passed`/`reason` are explicit (`ai_strategy_loop/fitness/score.py:224-320`). `run_loop` comments and wiring keep `best` as graded selection while `winner`/graduation update only from hard-gate-passed generations (`ai_strategy_loop/controller/loop.py:1008-1023`, `:1230-1450`).
- Research criteria already separate loose research continuation from promotion: `research_continue` can be true under loose thresholds, but `promotion_claim=False` and `promotion_requires_fixed_oos` is always emitted (`ai_strategy_loop/fitness/research_criteria.py:1-180`).
- Prompt/equity persistence are default-OFF and intentionally no-op on failure today: prompt logging only connects a callback when `prompt_logging_enabled` is true, callback exceptions are swallowed, and equity persistence catches parse/store failures and continues (`ai_strategy_loop/config.py:545-562`, `ai_strategy_loop/controller/loop.py:580-603`, `:1431-1446`, `ai_strategy_loop/brain/generator.py:220-285`).
- Prompt/generation contracts already include system assets, forbidden-token and whitelist rules, timeframe-specific variable guidance, variable-scope checks, optional filter/liquidity/time-window/exec-budget gates, and few-shot structure-not-copy wording (`ai_strategy_loop/brain/prompt.py:1-90`, `:340-683`; `ai_strategy_loop/brain/generator.py:64-160`, `:345-450`; `utility/ai_agent/system_prompt/v1/system_prompt.md:1-90`; `utility/ai_agent/system_prompt/v1/forbidden.md:1-80`).
- Repository and local rules confirm `ai_strategy_loop/` is research/control-plane code; `controller/export.py`/dashboard final approval are the export boundary, and operating `_database/`, live wiring, V3K, and protected runtime paths must not be touched without explicit gates (`AGENTS.md:82-111`; `ai_strategy_loop/AGENTS.md:1-40`).

### Strongest steelman antithesis
The strongest objection is that Option B may be too broad for one approval: presets, tick/min policies, staged gates, two new scores, prompt templates, hypothesis state, and human-condition library ingestion all change selection pressure and operator interpretation at once. A minimal-tuning plan would reduce blast radius, avoid false precision from 100-point scores, avoid prompt/equity state bloat, and avoid the highest-risk leakage path: using human DB/source conditions in generation. Under this antithesis, better discovery should first come from tightening existing gates and exposing existing diagnostics, not adding new ranking surfaces or examples.

### Synthesis
The antithesis is valid on risk, but not sufficient for the stated product goal: condition discovery needs better exploration contracts, reproducibility evidence, and composition guidance, not only threshold tweaks. Option B is the right direction only if execution preserves three separations: (1) preset resolution must not mutate raw defaults, (2) display/advisory scores must not replace hard promotion gates, and (3) human-condition knowledge must be normalized into pattern grammar without raw threshold/code copying.

## Root Cause
The underlying design tension is that the dashboard is trying to improve creative condition discovery while sharing code paths with scoring, persistence, and eventual promotion/export boundaries. Without explicit contracts, research convenience features can accidentally become selection or promotion authority.

## Findings

1. **MEDIUM — WATCH: Keep 100-point scores display/advisory, not hard-gate authority.**
   - Reference: planner score phases (`stage-103-planner.md:61-65`, `:91-105`); existing hard-gate and winner contracts (`ai_strategy_loop/fitness/score.py:224-320`, `ai_strategy_loop/controller/loop.py:1008-1023`).
   - Impact: Writing a new 100-point score into the existing `score` column, `target_score`, `winner_score`, or promotion path would blur the current invariant that hard-gate-passed generations are the only winner/export candidates.
   - Fix: Final plan must require separate fields such as `performance_score_100` and `generation_quality_score_100` in dashboard/state payloads, with explicit display/research ranking only; never used by `compute_fitness`, `gate_passed`, `winner_*`, `target_score`, OOS, or export/promotion approval.

2. **MEDIUM — WATCH: Required prompt/equity persistence needs evidence-health semantics.**
   - Reference: planner requires prompt/equity ON for research/promotion (`stage-103-planner.md:76-87`); current implementation makes these optional and swallows failures (`ai_strategy_loop/config.py:545-562`, `ai_strategy_loop/controller/loop.py:580-603`, `:1431-1446`, `ai_strategy_loop/brain/generator.py:220-285`).
   - Impact: If research/promotion presets require reproducibility evidence but logging/parsing failures remain silent no-ops, the dashboard may present a candidate as research/promotion-ready while missing the audit trail needed to reproduce or diagnose it.
   - Fix: Final plan must carry an `evidence_status`/warning contract: research may continue degraded, but promotion claims must be blocked or marked ineligible when required prompt or equity evidence is missing. Persistence failures should be recorded in run state/payload, not only printed or swallowed.

3. **MEDIUM — WATCH: Human DB composition library must prevent copy/leakage by construction.**
   - Reference: planner composition-library rules (`stage-103-planner.md:39-42`, `:106-110`); existing prompt/generator has only few-shot structure-not-copy wording and validation gates (`ai_strategy_loop/brain/prompt.py:524-683`, `ai_strategy_loop/brain/generator.py:345-450`).
   - Impact: Human-condition examples are the highest leakage/overfit risk. Raw code, thresholds, or seed fingerprints can make generated candidates look good by copying historical artifacts rather than discovering transferable condition grammar.
   - Fix: Final plan must require read-only ingestion from non-operating sources, normalized pattern cards only, stripped numeric constants/thresholds, bounded diversified few-shot K, provenance/risk notes, fingerprint/dedup checks against source expressions, and tests that raw expressions/threshold constants are not copied into prompts or generated candidates.

4. **LOW — WATCH: Preserve raw/default backward compatibility through a pure preset resolver.**
   - Reference: planner acceptance says raw custom config remains backward compatible (`stage-103-planner.md:56-58`); current defaults are `min`, MDD 35, prompt/equity OFF, `research_oos_mode="disabled"` (`ai_strategy_loop/config.py:29-138`, `:460-563`).
   - Impact: Mutating `LoopConfig` defaults to research/promotion values would change existing CLI/dashboard behavior and invalidate low-risk fast/custom runs.
   - Fix: Final plan must specify a pure `preset -> LoopConfig overlay` contract. Bare `LoopConfig()` and raw custom config must remain unchanged; only named presets apply stricter values.

5. **LOW — WATCH: Tick/min policy is directionally sound but must be expressed as preset policy, not global time semantics.**
   - Reference: planner tick and min targets (`stage-103-planner.md:34-35`, `:59-60`, `:76-81`); current config already has tick 09:00-09:28 and min full-session toggle/end-time (`ai_strategy_loop/config.py:128-138`).
   - Impact: Applying min full-session globally would slow fast exploration and change existing min behavior; using tick defaults in promotion without freezing strategy-specific settings could reduce comparability.
   - Fix: Final plan must carry: research preset defaults to tick/warm 09:00-09:28; min research/promotion uses `full_session_enabled=True` and end `151900`; promotion freezes timeframe/window with the candidate; fast/custom keeps current defaults unless explicitly selected.

6. **LOW — CLEAR: Transformer deferral and live/export/operating DB boundaries are correct.**
   - Reference: planner excludes Transformer/ML implementation and live/export/V3K/KHOPENAPI/operating strategy DB writes (`stage-103-planner.md:45-51`, `:112-115`); repo/local rules reserve export for dashboard final approval and forbid operating DB/live bypasses (`AGENTS.md:82-111`; `ai_strategy_loop/AGENTS.md:1-40`).
   - Impact: No architecture blocker if final execution obeys these boundaries.
   - Fix: Keep these as explicit out-of-scope guardrails in the final plan and implementation checklist.

## Recommendations
1. Approve planning continuation with `WATCH` constraints, not source execution yet.
2. Carry the six findings above into the final execution plan as acceptance criteria, especially the separate score fields and promotion-ineligible evidence-health rule.
3. Route critic review to confirm the final plan still preserves: raw defaults, hard gates, OOS/human approval, no live/export/operating DB writes, Transformer deferral, and anti-copy library construction.
4. When execution is later approved, verification should be focused unit/contract tests only, matching the planner non-project-wide verification approach.

## Architectural Status
`WATCH`

## Product Status
`WATCH`

## Code Status
`WATCH`

## Code Review Recommendation
`COMMENT`

## Trade-offs
| Tension | Option 1 | Option 2 | Recommendation |
|---|---|---|---|
| Creativity vs copy/leakage | Use human examples/few-shot aggressively | Use normalized composition grammar only | Use grammar-only pattern cards; strip thresholds/raw code; bounded K |
| Discovery speed vs evidence fidelity | Keep fast min/default runs cheap | Turn on tick/full-session/persistence for serious runs | Preserve fast/custom defaults; apply stricter evidence only to research/promotion presets |
| Score usability vs gate integrity | One 100-point score drives ranking and promotion | Hard gates stay authoritative; 100-point scores explain/display | Separate display/advisory scores from `compute_fitness`, winner, OOS, and export |
| Reproducibility vs loop robustness | Fail the run whenever evidence persistence fails | Continue research but surface degraded evidence | Continue research degraded; block/mark promotion ineligible without required prompt/equity evidence |

Final plan carry-forward requirement: all WATCH items are non-blocking only if they are copied into the final plan as explicit invariants and acceptance criteria. Dropping any of them should change the recommendation to `REQUEST CHANGES`.
