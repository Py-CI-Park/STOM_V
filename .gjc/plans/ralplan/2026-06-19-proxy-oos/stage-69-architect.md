## Summary
Backend status publication is additive and mostly preserves the existing LoopState.page_data and /status seams. The review blocks on a governance/runtime split: the new preset policy publishes staged MDD, full-session, and OOS semantics as hard policy, but the loop still scores, selects winners, and builds hypotheses from the raw LoopConfig values.

## Analysis
- Seam preservation is good in isolation. controller/contract.py:24-29 keeps contract v2 as an additive page_data pass-through, controller/contract.py:162-167 leaves page_data schema-owned by each panel, controller/state.py:912-1082 forwards dict(page_data or {}) into LoopState, and dashboard/app.py:177-185 plus dashboard/app.py:2754-2756 return the current state through /status. loop.py:935-963 copies incoming page_data, attaches condition-discovery sections only when absent, and passes the merged payload to to_loop_state. condition_discovery.py:300-309 preserves peer keys while adding condition_discovery.
- Preset and evidence model exists. condition_discovery.py:60-86 defines staged MDD, prompt/equity requirements, promotion permission, human approval, and required evidence. condition_discovery.py:94-128 defines fast, research, and promotion. condition_discovery.py:220-254 makes missing required evidence blocking and explicitly states evidence blockers override advisory scores.
- Advisory score authority is contained. advisory_scores.py:71-75 returns advisory_only plus can_promote/can_export/can_select_winner false. advisory_scores.py:201-214 adds hard_gate_not_passed and human_approval_required blockers and still keeps export_allowed false.
- Prompt/equity persistence is opt-in and evidence-backed. loop.py:605-609 only installs a prompt callback when prompt_logging_enabled and state exist; loop.py:1463-1473 only records equity points when equity_points_enabled and a csv path exist. condition_discovery_feedback.py:75-109 reports missing required prompt/equity persistence as evidence blockers, not promotion authority.
- Hypothesis feedback is wired. loop.py:1419-1455 adjudicates prior hypotheses and stores hypotheses_json, loop.py:1579 emits next hypotheses, loop.py:1248-1250 and 658-662 feed judged hypotheses back into generation when enabled, and loop.py:1966-1978 publishes them into condition_feedback.

## Root Cause
The implementation split condition-discovery governance into a dashboard policy projection without creating a single effective runtime policy consumed by scoring, winner selection, hypothesis feedback, OOS mode, and backtest window construction. That lets the UI say hard gate while runtime still uses the old raw config path.

## Findings
1. HIGH - ai_strategy_loop/controller/condition_discovery.py:70-86 and 275-287, ai_strategy_loop/controller/loop.py:1513-1514, 1953-1963, 2069-2070, 2175-2176, 2313-2315, ai_strategy_loop/fitness/score.py:273-286. Staged MDD is published as a hard gate but not enforced by the loop. condition_discovery.py computes effective_mdd_cap with min(configured, preset cap) and publishes it under hard_gates.mdd.authority hard_gate. The actual fitness path still calls compute_fitness and compute_graded_fitness with the original config, and fitness/score.py gates on config.mdd_cap. MDD-only refinement, gate-failure feedback, and hypothesis building also read config.mdd_cap directly. Impact: promotion can display cap 15 while a candidate with MDD between 15 and the raw config cap can still be gate_passed, become winner, and reach human approval/export paths under the wrong authority model. Fix: derive one effective condition-discovery policy before scoring and use the effective cap everywhere gate status, gate distance, best_is_mdd_only, hypotheses, holdout/promotion checks, and final approval consume MDD. Alternatively, downgrade page_data wording from hard_gate to display-only, but that does not meet the governance acceptance.

2. HIGH - ai_strategy_loop/controller/condition_discovery.py:178-190, ai_strategy_loop/controller/loop.py:385-391 and 294-339, ai_strategy_loop/launch_config.py:57-63 and 128-135. Preset time-window and OOS semantics are descriptive only. condition_discovery.py marks research/promotion MIN as full_session_required and policy.oos_mode as advisory or promotion_only, but loop.py only opens the warm MIN window when full_session_enabled is separately true, and the cold subprocess path does not pass a preset-derived start/end time at all. launch_config.py validates research_oos_mode independently and leaves condition_discovery_preset independent, so selecting promotion can still run with active_config.research_oos_mode disabled. Impact: /status can claim research/promotion governance while runtime backtests and OOS criteria follow another policy. Fix: apply preset-derived effective settings to runtime config, or explicitly publish both configured and effective values and only call them hard policy when applied.

3. MEDIUM - ai_strategy_loop/controller/condition_discovery_feedback.py:139-206 and ai_strategy_loop/controller/loop.py:1974-1980. Human DB pattern-card anti-copy guards are helper-only and loop publication is always empty. The helper can strip thresholds and detect full-expression, threshold, or performance-truth copying, but loop.py passes pattern_cards=[] and no inspected caller validates generated expressions with validate_pattern_card_usage. Impact: the dashboard can state anti-copy guard protection while no runtime generation path is actually guarded. Fix: wire a read-only card source, publish cards, and call validate_pattern_card_usage before save/export or clearly label this as unavailable instead of guarded.

4. MEDIUM - ai_strategy_loop/controller/loop.py:939-943 and ai_strategy_loop/controller/condition_discovery_feedback.py:121-122. Page-data projection failures are masked as omission. A malformed hypotheses_json list item can reach normalize_hypotheses and call raw.get on a non-mapping, then _publish_live catches the exception and drops the whole condition-discovery projection while /status stays successful. Impact: an accepted dashboard panel can disappear without a machine-readable status. Fix: normalize non-mapping hypotheses defensively and publish condition_discovery/condition_feedback with status error and reason when projection fails.

## Recommendations
1. Build one effective_condition_discovery_policy helper and feed it into scoring, winner, holdout/promotion, hypothesis, feedback, and page_data. Do not let page_data hard_gates diverge from compute_fitness.
2. Make research/promotion presets actually set effective full-session and OOS behavior, including cold subprocess parameters, or remove hard-policy language from the preset projection.
3. Connect pattern-card source and validation before claiming anti-copy protection in live page_data.
4. Replace broad omission fallback with fail-closed status payloads for condition discovery sections.
5. Add targeted tests that prove a promotion preset with raw mdd_cap 35 rejects MDD 20, a research MIN preset opens full-session in both warm and cold paths, and malformed hypotheses_json does not erase page_data.

## Architectural Status
BLOCK

## Code Review Recommendation
REQUEST CHANGES

## Trade-offs
| Option | Pros | Cons |
|---|---|---|
| Apply preset policy to runtime | Makes hard-gate and UI authority truthful; safest for promotion | Requires touching scoring/window/OOS callsites and tests |
| Keep preset display-only | Smallest change and preserves old runtime exactly | Misleading hard-gate language and unsafe promotion mismatch |
| Fail-closed page_data error payload | /status remains observable and debuggable | Slightly more UI states to handle |
| Silent omission on projection errors | Keeps loop running with minimal code | Masks accepted governance panels and breaks dashboard evidence |
