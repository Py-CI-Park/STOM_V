# 2026-06-18 OOS 2023~2025 Combo Experiments

## Objective

Run the requested experiment priorities 1~5 in one coordinated pass:

1. Add 2023~2025 OOS checks for `r8_4`, `exit2 balance`, and `r2full MDD`.
2. Break down monthly PnL and MDD so performance concentration is visible.
3. Compare weekday/hourly loss overlap across the three strategies.
4. Decide the stronger 2-strategy candidate: `r8_4 + exit2` vs `r8_4 + r2full`.
5. Re-evaluate whether the 3-strategy portfolio is worth the extra capital.

## Scope

- Evidence lives under `.omo/evidence/tmap-walkforward/`.
- Research journal lives under `docs/update_log/`.
- Runtime DB/CSV output from the official OOS runner is evidence only, not a source edit.
- Do not change `backtest/backtest.py` in this work. That remains a separate contract-stabilization task.

## TODOs

- [x] Create OOS configs for 2023, 2024, and 2025 and capture baseline run-id state.
- [x] Run official OOS for `r8_4`, `exit2 balance`, and `r2full MDD` across 2023~2025.
- [x] Build monthly PnL/MDD breakdown from the completed OOS CSV outputs.
- [x] Build weekday/hourly loss-overlap analysis for the three strategies.
- [x] Compare 2-strategy and 3-strategy portfolios across 2022~2026 and write the research journal.

## Final Verification Wave

- [x] Validate JSON artifacts, protected-path status, and the research journal; then mark Boulder complete.

## Evidence Targets

- `.omo/evidence/tmap-walkforward/oos-2023-2025-r8-exit2-r2full-20260618.json`
- `.omo/evidence/tmap-walkforward/monthly-regime-r8-exit2-r2full-20260618.json`
- `.omo/evidence/tmap-walkforward/weekday-hourly-overlap-r8-exit2-r2full-20260618.json`
- `.omo/evidence/tmap-walkforward/portfolio-r8-exit2-r2full-2023-2026-20260618.json`
- `docs/update_log/2026-06-18_oos_2023_2025_combo_experiment_log.md`

## Reporting

Give the user progress and performance status while long OOS commands run. If the work exceeds one hour, include an hourly table with completed runs, remaining runs, elapsed time, and current best candidate.
