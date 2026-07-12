# Intent Reconciliation

Status: open-confirmations-pending because this run is automated and no interactive ask gate was used.

## Confirmed from user context
- User wants V3 UX/UI to be judged by UX/UI expert standards, not by API 200 or visual-only gates.
- User found V3 charts and Process page dummy-like; the plan treats that as a real blocker, not a subjective preference.
- User wants V2 and V3 compared, with V3 becoming better than V2, while V2 remains available.
- User approved planning for later full execution, but this Ralplan phase remains planning-only and pending approval.

## Open confirmations at pending approval gate
1. V2 remains default until the rebuilt V3 passes the deterministic 100-point UX/UI gate.
2. V3 implementation may replace current static SVG chart helpers with V3-native interactive primitives rather than directly porting the V2 React bundle.
3. Live mode completion must fail if payloads do not drive visible DOM state, even when REST endpoints return 200 OK.
4. Start/Stop, export, approval, /ws, /sim/ws, backtest POSTs, and settings/localStorage must be classified in Phase 0 before product-source mutation.

## Prior-context conflicts
No prior approved instruction requires V3 to become default immediately. No instruction permits live order, broker login, account trading, hidden export, or protected runtime writes. The current plan preserves those boundaries.

## Source artifacts
- Planner revision: C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel/.gjc/_session-019f1343-f51d-7000-aed1-3bb8c3807e3b/plans/ralplan/019f1343-f51d-7000-aed1-3bb8c3807e3b/stage-02-revision.md
- Architect pass 2: C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel/.gjc/_session-019f1354-06b2-7000-a3d9-1e61faa398f7/plans/ralplan/019f1354-06b2-7000-a3d9-1e61faa398f7/stage-02-architect.md
- Critic pass 2: C:/System_Trading/STOM/STOM_V.wt-dev/.gjc/_session-019f1358-4fc2-7000-9b51-c15fc131d130/plans/ralplan/019f1358-4fc2-7000-9b51-c15fc131d130/stage-02-critic.md
