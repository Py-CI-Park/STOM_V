# Intent Reconciliation — V3 dashboard UX/UI maturity plan

Status: open-confirmations-pending (automated ralplan mode). No product source was mutated.

## Source artifacts reviewed
- Revised Planner stage 2: `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel/.gjc/_session-019f1675-7246-7000-9215-83dbd4af3e27/plans/ralplan/019f1675-7246-7000-9215-83dbd4af3e27/stage-02-revision.md`
- Architect pass 2: `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel/.gjc/_session-019f168b-47cf-7000-8d83-1d60ad03b83b/plans/ralplan/019f168b-47cf-7000-8d83-1d60ad03b83b/stage-02-architect.md`
- Critic pass 2: `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel/.gjc/_session-019f1690-a156-7000-833d-8e88881958a1/plans/ralplan/019f1690-a156-7000-833d-8e88881958a1/stage-02-critic.md`
- Original approved V3 rebuild plan: `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel/.gjc/_session-019f05e9-d676-7000-9c61-3c206a2d4031/plans/ralplan/019f05e9-d676-7000-9c61-3c206a2d4031/pending-approval.md`

## Open confirmations for pending approval
1. V2 remains the default baseline; V3 remains explicit/selectable via `/ui/remodel/*` or `dashboard_version=v3` until a separate default-cutover approval.
2. Execution should start with Tranche 0 only: human UX verifier, V2/current-V3 baseline captures, and machine-checkable storyboards before any UI/product-source churn.
3. The new human-centered rubric complements rather than replaces existing safety, route parity, visual, V2/V3 compare, and protected-path gates.
4. Contract/safety/provenance detail may move into progressive-disclosure drawers, but required safety/contract DOM markers must remain discoverable and hard-fail if missing.
5. Backtest and Chart Replay are the first high-risk UX pages after Tranche 0; they require storyboard proof before broader page redesign.
6. The consensus plan proposes final human-rubric thresholds of V3 score >=90, no category <70, and mean V3-V2 delta >=15 for task orientation, visualization readability, workflow quality, and cognitive load. The user may raise this threshold at approval time if they want a stricter “100-point target” interpretation.
7. Default switch, live trading, broker login, account trading, hidden production export, protected runtime writes, and unapproved mutating calls remain out of scope.

## Prior-context conflict check
- No `deep-interview-*.md` specs were found under `.gjc/**/specs/` during the automated cross-check.
- The new plan is consistent with the original approved plan’s core constraints: V2 default preservation, V3 explicit/selectable route, no live order/broker/account/hidden export/protected writes, and no page-load mutating calls.
- The new plan refines rather than contradicts the original deterministic 100/100 gate: it identifies that the prior rubric over-weighted required text/safety/evidence and adds a task-based human UX delta gate before further UI work.
- Potential approval-time tension: the original plan used “100/100” as the completion language, while the revised plan proposes a stricter human-centered 100-point rubric with a practical pass threshold (`>=90`, no category `<70`, and named V2 deltas). This is intentionally listed as an open confirmation rather than silently assumed.

## Routing
Consensus is clean enough to finalize a pending-approval plan. Architect pass 2 is CLEAR / APPROVE; Critic pass 2 is OKAY / APPROVE. Execution remains blocked until explicit user approval.
