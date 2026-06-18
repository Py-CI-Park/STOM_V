# Source Inventory - Current-State Rereview 20260618

## Scope

This review covers completed condition-generation, OOS, portfolio-defense, and dashboard-research work through 2026-06-18. It does not execute the deferred official OOS cleanup plan.

## Completed Work Reviewed

| Date | Work | Status | Evidence |
|---|---|---|---|
| 2026-06-17 | Condition generation breadth evaluation | complete | `docs/update_log/2026-06-17_condition_generation_breadth_evaluation.md` |
| 2026-06-18 | Dashboard research records and OOS follow-up | complete | `docs/update_log/2026-06-18_dashboard_research_records_oos_followup.md` |
| 2026-06-18 | OOS 2023~2025 combo experiment | complete | `docs/update_log/2026-06-18_oos_2023_2025_combo_experiment_log.md` |
| 2026-06-18 | Q4 defense, prior rule, half exit2, dashboard check | complete | `docs/update_log/2026-06-18_q4_defense_prerule_halfexit_dashboard.md` |
| 2026-06-18 | Q4 defense next four follow-ups | complete | `docs/update_log/2026-06-18_post_q4_defense_next4.md` |
| 2026-06-18 | Post-Q4 3H bulk research | complete | `docs/update_log/2026-06-18_post_q4_3h_bulk_research.md` |
| 2026-06-18 | Post-session handoff | complete | `docs/update_log/2026-06-18_post_20260618_research_dashboard_handoff.md` |

## Numeric Evidence Reviewed

| Area | Key Numbers | Interpretation |
|---|---:|---|
| Template generation breadth | 149 templates, 111 tick / 38 min, 149/149 default-valid | Broad structure exists. |
| AND richness | 149/149 templates use AND, average AND count 17.07 | Strong multi-filter construction. |
| OR/branch diversity | literal OR 38/149, if/elif branch 121/149 | Branching exists, but branch contribution is not attributed. |
| Cold/stateful LLM generation | full_stateful_n40 PROMISING 0/40 | Cold generation remains weak. |
| Anchor mutation | 399 adopted, best +13,928,386 KRW / MDD 9.62 | Verified-seed mutation is the strongest generation route, but originally train-gate. |
| 2022/2026 OOS follow-up | 4/4 complete and gate-pass | OOS coverage improved for fixed candidates. |
| 2023~2025 OOS | 9/9 complete and gate-pass | Multi-year fixed-candidate proof improved materially. |
| 2025 Q4 official OOS | r8_4 failed, r2full_mdd and exit2_balance passed | Stress failure source is now identified. |
| Portfolio 2022~2026 | all major combos positive 5/5 periods | Portfolio-level robustness improved, but capital efficiency differs. |
| Bulk candidate grid | 64 combined candidates, robust primary score 90.5884 | Next official OOS candidate is selected but not yet executed. |
| Dashboard visibility | latest campaign visible, rank 1, detail 200, campaign_count 17 | Research management is now partly productized in dashboard. |

## Source Files and Surfaces

| Surface | Files | Review Finding |
|---|---|---|
| Research records API | `ai_strategy_loop/dashboard/research_records.py`, `research_api.py` | Campaign indexing and detail endpoint exist. |
| Evolution GUI parity | `ai_strategy_loop/dashboard/evolution_gui_parity.py` | Selected generation can expose hourly/weekday parity when CSV exists. |
| Dashboard panels | `research-records-panel.jsx`, `evolution-gui-parity-panel.jsx`, `app.jsx` | Research records and GUI parity are mounted in Evolution. |
| Dashboard tests | `test_research_records.py`, `test_evolution_gui_parity.py`, `test_research_records_frontend.py` | Contract tests exist. |
| Deferred next plan | `.omo/plans/post-20260618-official-oos-dashboard-cleanup.md` | Explicitly deferred until named by user; not executed in this review. |

## Key Separation

| Evidence Type | What It Proves | What It Does Not Prove |
|---|---|---|
| Broad templates | AI can create many structured condition families | It does not prove cold generation can find winners. |
| Anchor mutation | Good seeds can be improved with bounded mutation | It does not prove arbitrary bad formulas become good. |
| Fixed-candidate OOS | r8_4, exit2_balance, r2full_mdd have multi-year evidence | It does not prove the newly selected robust filtered combo has completed official OOS. |
| CSV/portfolio reanalysis | Filters and allocation rules look promising | It is not the same as an official runner pass for the final candidate. |
| Dashboard visibility | Research is easier to inspect | It does not solve candidate quality by itself. |
