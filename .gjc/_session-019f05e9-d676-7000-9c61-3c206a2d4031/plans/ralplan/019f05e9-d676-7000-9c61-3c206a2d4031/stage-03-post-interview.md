# Intent Reconciliation — STOM Dashboard Remodel 100-Point Plan

Status: open-confirmations-pending (automated ralplan mode; no interactive questions asked).

## Source artifacts reviewed

- Planner pass 1: `.gjc/_session-019f0b7b-b0a1-7000-9f2d-80757688fa91/plans/ralplan/019f0b7b-b0a1-7000-9f2d-80757688fa91/stage-01-planner.md`
- Planner revision pass 2: `.gjc/_session-019f0b7b-b0a1-7000-9f2d-80757688fa91/plans/ralplan/019f0b7b-b0a1-7000-9f2d-80757688fa91/stage-02-revision.md`
- Architect pass 2: `.gjc/_session-019f0b8e-5c18-7000-9018-3192e7b0ce09/plans/ralplan/019f0b8e-5c18-7000-9018-3192e7b0ce09/stage-02-architect.md`
- Critic pass 2: `.gjc/_session-019f0b93-31fc-7000-9196-a9770d31c444/plans/ralplan/019f0b93-31fc-7000-9196-a9770d31c444/stage-02-critic.md`
- Prior pending plan: `.gjc/_session-019f05e9-d676-7000-9c61-3c206a2d4031/plans/ralplan/019f05e9-d676-7000-9c61-3c206a2d4031/pending-approval.md`

## Open confirmations carried to pending approval

1. Architecture pivot: prior pending plan preferred a hybrid production React/component reuse path and disallowed vanilla `frontend/remodel/src/app.js` as production renderer. The revised plan intentionally pivots to a zip-first static shell with bounded production-contract adapters because the user later identified visual/capture mismatch and demanded 100-point completion against the provided zip/captures.
2. Visual scoring priority: revised plan treats provided zip captures/DOM as visual source of truth and requires reference-mode capture gates.
3. Function depth priority: Backtest and Chart Replay must regain production `/bt/*` and `/sim/*` depth even though the render shell remains zip-first. Static-only success is explicitly rejected.
4. Reference mode: `?demo=reference` disables REST, WS, timers, random values, localStorage side effects, and mutations. Separate live-mode evidence remains required so reference mode cannot hide live regressions.
5. Safety: live order, broker login, account/balance/trading controls, hidden or automatic production export, mutable audit edit/delete, and hidden `final_approval` remain forbidden. Local research/backtest mutations are allowed only in live mode with visible research semantics and confirmation where destructive.
6. Route promotion: `/ui/remodel/*` remains replacement candidate until all gates pass. Canonical `/ui/evolution`, `/ui/backtest`, `/ui/chart-replay` remain preserved controls. Default-route promotion requires later explicit approval.
7. Data usage: verification may use fixtures, safe local endpoints, or read-only references to existing `_database` data, but must not create operating DB writes or live-broker side effects.

## Prior-context conflicts

- Conflict with prior pending plan Gate B lines 68-73: prior plan required remodel to bootstrap the production React component graph and rejected vanilla remodel `src/app.js` as accepted production renderer. Revised plan conflicts by choosing zip-first static shell plus production-contract adapters. Rationale: user-visible visual/capture mismatch made production-bundle-first path insufficient for the current request.
- Alignment with prior plan lines 88-95 and 114-150: both plans agree that Backtest and Chart Replay require real `/bt/*` and `/sim/*` behavior rather than static mocks.
- Alignment with prior plan lines 75-80 and 217-222: both plans preserve safety constraints and approval/audit separation.

## Reconciliation status

open-confirmations-pending; no further planning revision required because Architect pass 2 returned CLEAR/APPROVE and Critic pass 2 returned OKAY with no required revisions. These open confirmations must be reviewed at pending approval before execution.
