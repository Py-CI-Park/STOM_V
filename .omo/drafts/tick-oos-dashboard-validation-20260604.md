# Draft: TICK OOS Dashboard Validation 20260604

## Requirements (confirmed)
- User requested `$start-work` and then "위 내용 바탕으로 plan 진행".
- Existing `.omo/plans` are all complete; no active Boulder work exists.
- Next objective comes from `docs/AGENT_HANDOFF.md` and `docs/update_log/2026-06-03_tick_program_complete_handoff.md`: TICK toggles-ON multiyear research run plus 2022/2026 OOS split validation.
- Use the newly completed research dashboard upgrade evidence under `.omo/evidence/tick-research-dashboard-upgrade-20260603/`.

## Technical Decisions
- Create a new Prometheus plan rather than reusing completed `tick-oos-validation-20260603`.
- New plan slug: `tick-oos-dashboard-validation-20260604`.
- Treat 2026-06-03 OOS result as baseline prior: `REJECT_CANDIDATE`.
- Require current-code dashboard verification on an owned port if 8770 is stale.
- Do not edit engines, hard gates, `backtest/graph/`, live broker code, production strategy DB, or protected paths.

## Research Findings
- `run_tickwide_config.json` is the toggles-ON short-run template.
- Seed OOS config templates exist for 2022 and 2026.
- Dashboard upgrade final QA verified new APIs on owned port 8798; existing 8770 was stale until restart.
- Final verification from the dashboard upgrade passed `git diff --check`, `verify_nonrelease_sync.py`, protected path status, and 208 focused tests.

## Open Questions
- None blocking. Default assumption: produce a new executable plan first, then user can run `$start-work tick-oos-dashboard-validation-20260604`.

## Scope Boundaries
- INCLUDE: evidence capture, safe dashboard restart/owned-port handling, short reproduction run, 2023~2025 training run, dashboard-based analysis, fixed 2022/2026 OOS seed-vs-AI comparison, decision card, final verification.
- EXCLUDE: source-code changes, engine/hard-gate edits, final approval/export, live broker/V3K gate actions, production DB writes, blanket process killing.
