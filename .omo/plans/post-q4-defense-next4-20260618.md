# Post-Q4 Defense Next 4 Follow-up

## Scope
- Execute the next four follow-up tasks from `docs/update_log/2026-06-18_q4_defense_prerule_halfexit_dashboard.md`.
- Keep this as research, evidence, dashboard-record, and design work unless a later plan explicitly authorizes production code changes.
- Do not modify `backtest.py`, V3K gate state, live trading paths, or protected runtime paths.
- Record elapsed wall time per major step and report it at completion.

## TODOs
- [x] Prepare the follow-up plan, Boulder state, baseline coverage, and timing ledger.
- [x] Validate `r8_4 + exit2_balance` prior-month `-500,000 KRW` exclusion by year and half-year.
- [x] Test dynamic `exit2_balance` allocation rules across none/half/full portfolio modes.
- [x] Decompose `r8_4` 2025 Q4 loss by month, weekday, time bucket, market-cap bucket, and stock concentration.
- [x] Design markdown research-journal auto-exposure improvements for the dashboard documentation surface.
- [x] Write the research journal, dashboard campaign record, and elapsed-time summary.

## Final Verification Wave
- [x] Validate new JSON artifacts, dashboard record visibility, research journal encoding, protected paths, git diff hygiene, and Boulder completion.

## Expected Artifacts
- `.omo/evidence/tmap-walkforward/post-q4-next4-baseline-20260618.json`
- `.omo/evidence/tmap-walkforward/r8-exit2-prior-loss-500k-split-20260618.json`
- `.omo/evidence/tmap-walkforward/exit2-dynamic-allocation-20260618.json`
- `.omo/evidence/tmap-walkforward/r8-q4-loss-decomposition-20260618.json`
- `.omo/evidence/tmap-walkforward/research-docs-auto-exposure-design-20260618.json`
- `.omo/evidence/tmap-walkforward/post-q4-next4-duration-20260618.json`
- `.omo/evidence/tmap-walkforward/post-q4-next4-20260618_summary.json`
- `.omo/evidence/tmap-walkforward/post-q4-next4-20260618.jsonl`
- `.omo/evidence/tmap-walkforward/post-q4-next4-20260618_log.txt`
- `docs/update_log/2026-06-18_post_q4_defense_next4.md`

## Acceptance Notes
- Step 1 must split the promising rule by year and half-year, not only aggregate it.
- Step 2 must compare `exit2_balance` modes: off, half, full, and at least one prior-month dynamic rule.
- Step 3 must use official Q4 `r8_4` CSV evidence from `q4-official-oos-run-records-20260618.json`.
- Step 4 is a design task: produce an implementable dashboard exposure design and verify the current surface limitations from code/API evidence.
- Completion report must include elapsed time per requested step.
