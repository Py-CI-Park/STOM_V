# 2025 Q4 Defense, Prior Rule, Half Exit2, Dashboard Follow-up

## Scope
- Execute the next four research steps requested after `combo-defense-stress-followup-20260618`.
- Keep this as research/OOS evidence work only. Do not modify `backtest.py`, V3K gate state, live trading paths, or protected runtime paths.
- Use official OOS runs where new backtest evidence is needed, then derive portfolio/defense diagnostics from the completed CSV and SQLite records.

## TODOs
- [x] Prepare the 2025 Q4 official OOS run config, verify run-id collisions, and record baseline coverage.
- [x] Run official 2025 Q4 OOS for `r8_4`, `r2full_mdd`, and `exit2_balance`.
- [x] Analyze 2025 Q4 defense behavior and `half_exit2` portfolio expansion from official OOS outputs.
- [x] Convert the prior monthly defense idea into causal pre-rules and simulate them across completed OOS CSVs.
- [x] Confirm the dashboard research-record surface exposes the latest research logs and artifacts.
- [x] Write the research journal with results, remaining risks, and next experiment priorities.

## Final Verification Wave
- [x] Validate all new JSON artifacts, run focused dashboard research-record tests, check protected paths, check no OOS process remains, and mark Boulder complete.

## Expected Artifacts
- `.omo/evidence/tmap-walkforward/oos-2025-q4-e32-config.json`
- `.omo/evidence/tmap-walkforward/q4-oos-baseline-coverage-20260618.json`
- `.omo/evidence/tmap-walkforward/q4-defense-official-oos-20260618.json`
- `.omo/evidence/tmap-walkforward/half-exit2-official-oos-20260618.json`
- `.omo/evidence/tmap-walkforward/monthly-prerule-sim-r8-exit2-r2full-20260618.json`
- `.omo/evidence/tmap-walkforward/dashboard-research-records-check-20260618.json`
- `docs/update_log/2026-06-18_q4_defense_prerule_halfexit_dashboard.md`

## Acceptance Notes
- Q4 OOS results must be sourced from newly completed official runner records or explicitly reuse already completed matching run IDs if collisions exist.
- Monthly defense pre-rules must be prior-only: the decision for month N may use month N-1 or earlier, never month N realized PnL.
- `half_exit2` is a portfolio-layer capital overlay unless the official runner supports native fractional strategy capital.
- Dashboard confirmation can use a FastAPI/TestClient request or focused dashboard tests plus direct research-record discovery evidence.
