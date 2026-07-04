# Dashboard V4 Remodel Research Handoff - 2026-07-04

## Context

This plan records the user-requested handoff after the V2/V3 dashboard reassessment. Scope is documentation, evidence, and commit only. No production UI code, broker path, database path, live order path, V3K gate, or runtime setting is changed.

Working branch:

- Worktree: `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel`
- Branch: `feature/dashboard-remodel-20260626`
- Baseline commit: `db0a60f70e56595dcbe9f614286893a41602a105`
- Reference V2 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
- Reference V2 branch: `loop/process-research-pipeline`
- Reference V2 commit: `611473b5acc9f7074ce8997abfe35edbe21cd91d`

## TODOs

- [x] 1. Reconfirm branch/worktree state and V2/V3 divergence evidence.
- [x] 2. Write objective V2/V3/V4 research report and handoff.
- [x] 3. Verify documentation artifacts and commit the handoff.

## Final Verification Wave

- [x] F1. Reread generated documents, run repository hygiene checks, and confirm protected runtime paths remain untouched.

## Acceptance Criteria

- The report states that V2 currently wins on calm theme, React stack maturity, graph size, and operational usability.
- The report states that V3 currently wins on workflow framing, safety gates, audit vocabulary, and process traceability.
- The report explicitly says V3 does not yet fully reflect latest `wt-dev` V2 work.
- The report evaluates V4 feasibility using V2 React/theme strengths plus V3 process/safety lessons.
- The handoff gives concrete next steps for a future V4 implementation.
- Commit uses a Korean title and Korean markdown body.
