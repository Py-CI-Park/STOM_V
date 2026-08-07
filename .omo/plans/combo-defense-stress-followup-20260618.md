# 2026-06-18 Combo Defense Stress Follow-up

## Objective

Execute the next requested work items 1~4 from the prior OOS report:

1. Re-check recent-regime stress for `r8_4 + r2full`.
2. Test monthly loss-defense diagnostics for the worst months.
3. Test weak weekday+5-minute slot restriction diagnostics.
4. Re-evaluate the 3-strategy portfolio as a separate capital-efficiency scenario.

## Scope

- This is a diagnostic follow-up over completed official OOS CSV/DB evidence.
- Do not change `backtest/backtest.py`.
- Do not mutate protected runtime paths manually.
- Diagnostic simulations are not deployable strategy rules until validated by a later official OOS or forward test.

## TODOs

- [x] Capture baseline source artifacts, prior report, and run coverage for the 2022~2026 OOS set.
- [x] Build recent-regime stress analysis for `r8_4 + r2full`.
- [x] Build monthly loss-defense simulations for worst months.
- [x] Build weak weekday+5-minute slot restriction simulations.
- [x] Build 3-strategy capital-efficiency scenarios and write the follow-up research journal.

## Final Verification Wave

- [x] Validate JSON artifacts, research journal encoding, protected-path status, and Boulder completion.

## Evidence Targets

- `.omo/evidence/tmap-walkforward/recent-stress-r8-r2full-20260618.json`
- `.omo/evidence/tmap-walkforward/monthly-defense-sim-r8-exit2-r2full-20260618.json`
- `.omo/evidence/tmap-walkforward/slot-restriction-sim-r8-exit2-r2full-20260618.json`
- `.omo/evidence/tmap-walkforward/three-strategy-capital-efficiency-20260618.json`
- `docs/update_log/2026-06-18_combo_defense_stress_followup.md`

## Reporting

Report the result as tables: recent stress, monthly defense, slot restriction, 3-strategy capital scenario, and next recommended work.
