# Post-20260618 Official OOS and Dashboard Cleanup

## TL;DR
> **Summary**: Start after 2026-06-18. Run official OOS for the robust post-Q4 candidate, compare the high-overfit shadow candidate, and clean up dashboard/research visibility so future work is understandable.
> **Status**: Deferred next research. Do not execute until the user explicitly starts this plan.
> **Primary command**: `$start-work .omo/plans/post-20260618-official-oos-dashboard-cleanup.md`

## Context
- The completed pre-selection research is documented in `docs/update_log/2026-06-18_post_q4_3h_bulk_research.md`.
- The next official OOS recommendations are in `.omo/evidence/tmap-walkforward/post-q4-3h-official-oos-recommendations-20260618.json`.
- The recommended robust candidate is `r8_exclude_cap_lt_1500__exit2_skip_after_prior_exit2_loss_500k_else_full`.
- The raw score winner is `r8_exclude_month_11__exit2_skip_after_prior_exit2_loss_500k_else_full`, but it is high-overfit risk and should be shadow comparison only.

## Guardrails
- Do not modify `backtest.py` unless a later plan explicitly approves a concrete exit-rule redesign.
- Do not touch live trading, V3K gate state, serial-key behavior, protected runtime paths, or `*.db`.
- Keep official OOS, portfolio-layer reanalysis, and dashboard documentation clearly labeled as different evidence types.
- Use friendly Korean aliases in reports so long internal candidate names are not the only user-facing explanation.

## TODOs
- [ ] 1. Refresh context and verify source artifacts.
  - Confirm the pre-selection artifacts exist and parse.
  - Confirm Research Records exposes `post-q4-3h-bulk-research-20260618`.
  - Re-check protected path status before running anything.

- [ ] 2. Run official OOS for the robust primary candidate.
  - Friendly name: `저시총 제외 방어 조합`.
  - Internal candidate: `r8_exclude_cap_lt_1500__exit2_skip_after_prior_exit2_loss_500k_else_full`.
  - Purpose: confirm the low-overfit candidate still works in the official engine.
  - Expected time: 45 minutes.

- [ ] 3. Run shadow comparison for the raw-score winner.
  - Friendly name: `11월 제외 비교용 후보`.
  - Internal candidate: `r8_exclude_month_11__exit2_skip_after_prior_exit2_loss_500k_else_full`.
  - Purpose: compare against the robust candidate without treating it as adoption-ready.
  - Expected time: 35 minutes.

- [ ] 4. Produce an official portfolio-layer report for the exit2 rule.
  - Friendly name: `exit2 월별 ON/OFF 규칙`.
  - Internal rule: `exit2_full_after_prior_r8r2_loss_else_off`.
  - Purpose: validate a condition-expression-free allocation rule for dashboard reporting.
  - Expected time: 25 minutes.

- [ ] 5. Run standalone official OOS for the r8 low-cap filter.
  - Friendly name: `r8 저시총 제외 단독`.
  - Internal candidate: `r8_exclude_cap_lt_1500`.
  - Purpose: isolate whether r8 defense alone is responsible for the improvement.
  - Expected time: 40 minutes.

- [ ] 6. Clean up dashboard research visibility.
  - Add or verify friendly aliases for hard candidate names.
  - Ensure each record is labeled as `공식 OOS`, `CSV 재분석`, `포트폴리오 규칙`, or `설계/보류`.
  - Expose the latest research journal in the dashboard documentation surface, or document the code gap if implementation is deferred.
  - Confirm whether weekday/hourly profit charts from backtest GUI are visible or still missing in the Evolution Dashboard for tested candidates.
  - Expected time: 60-90 minutes depending on whether implementation is included.

- [ ] 7. Write the next handoff and research summary.
  - Include purpose, results, failures, missing work, and the next recommended command.
  - Update Research Records campaign artifacts and `docs/update_log/`.
  - Expected time: 20 minutes.

## Final Verification Wave
- [ ] F1. Validate JSON artifacts, research journal encoding, dashboard visibility, protected paths, `*.db` status, OOS process cleanup, and focused dashboard tests.

## Expected Outputs
- Official OOS run record artifact for the robust candidate.
- Shadow comparison artifact for the high-overfit calendar candidate.
- Portfolio-layer exit2 rule report.
- r8 standalone filter official OOS report.
- Dashboard cleanup/visibility evidence.
- New dated handoff document under `docs/update_log/`.
