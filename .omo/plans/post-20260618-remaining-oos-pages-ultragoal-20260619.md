Shared constraints:
- Continue from the completed setup pages P0-P6 documented in docs/update_log/2026-06-19_ai_loop_research_recommended_start_scope.md and .omo/evidence/tmap-walkforward/post-20260618-official-oos-command-mapping-20260619.md.
- Preserve the prior guardrails: no backtest.py edits, no UI frontend/bundle work in this worktree, no live trading/V3K/serial/export/final-approval path, no protected runtime path writes, no manual protected *.db mutation.
- Keep evidence taxonomy explicit: 공식 OOS, CSV 재분석, 포트폴리오 규칙, 설계/보류.
- Use evidence-local artifacts under .omo/evidence/tmap-walkforward/ for new official OOS outputs and reports.
- Do not claim official OOS success until actual wrapper-backed runs complete and artifacts are inspected.

@goal: Run robust primary official OOS
Execute P7 and P8 for the robust primary research candidate. Run Q4 stress official OOS first for r8_exclude_cap_lt_1500 using .omo/evidence/tmap-walkforward/run_post_q4_oos_wrapper_20260619.py, then run annual 2022-2026 official OOS only if Q4 execution is usable. Capture raw logs/results, elapsed time, and process cleanup evidence. Stop and checkpoint failure if official OOS requires forbidden paths or cannot produce inspectable artifacts.

@goal: Build robust decision and portfolio report
Execute P9 and P10. Combine the new r8 low-cap official OOS outputs with the pre-registered exit2 prior-month portfolio rule as a separately labeled portfolio-layer report. Produce a robust candidate decision card with status oos_passed, deferred, or rejected. Do not mislabel portfolio reanalysis as pure official OOS.

@goal: Run shadow and standalone follow-up checks
Execute P11 and P12 if the robust primary official outputs are usable. Run the 11월 제외 comparison only as a shadow/high-overfit comparison, and run r8 저시총 제외 단독 or equivalent standalone attribution check. Keep both separated from promotion evidence.

@goal: Finalize research records and handoff
Execute P13 and P14. Update research-facing evidence summaries without UI code changes, write a dated handoff/update-log with full page progress and results, run final JSON/protected-path/process verification, and recommend whether the research can stop, should continue with a next OOS pass, or should return to generation.