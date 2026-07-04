# Dashboard V4 Handoff Evidence - Branch Divergence

## Captured State

Captured on 2026-07-04 KST during `codex:dashboard-v4-remodel-research-handoff-20260704`.

| Item | Value |
|---|---|
| V3 worktree | `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel` |
| V3 branch | `feature/dashboard-remodel-20260626` |
| V3 HEAD | `db0a60f70e56595dcbe9f614286893a41602a105` |
| V2 reference worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| V2 reference branch | `loop/process-research-pipeline` |
| V2 reference HEAD | `611473b5acc9f7074ce8997abfe35edbe21cd91d` |

## Relevant Ahead Changes In wt-dev

`git log --oneline HEAD..611473b5... -- ai_strategy_loop/dashboard/frontend ai_strategy_loop/dashboard/app.py ai_strategy_loop/dashboard/backtest_report.py` reported:

```text
a79b2b27e 조건식 연구 측정 재현성 기반 구축
332106f24 조건식 연구 컨텍스트팩과 다중 후보 루프 개선
47798adce 프로세스 연구 벤치마크 우선 실행
```

Interpretation:

- `47798adc` updates the V2 React dashboard process selector, research/production boundary copy, Lab/Workbench heatmap sizing, and process research browser evidence.
- `332106f2` adds V2 React research observability UI for Research Pack / Branch Tree, Candidate Pack, Analysis Cards, Prompt Receipts, and Promotion Blockers.
- `a79b2b27` adds measurement frame labeling in `backtest_report.py` plus replay/slippage measurement foundations outside the remodel UI.

## V3 Remodel Branch Shape

The V3 remodel branch has the static remodel prototype:

```text
ai_strategy_loop/dashboard/frontend/remodel/src/app.js   3132 lines
ai_strategy_loop/dashboard/frontend/remodel/src/data.js  3867 lines
ai_strategy_loop/dashboard/frontend/remodel/styles/theme.css 1600 lines
ai_strategy_loop/dashboard/frontend/*.jsx                71 files
```

Interpretation:

- V2 has a mature React component split and build flow.
- V3 has a useful IA/prototype layer, but its main implementation is oversized and not yet a good long-term production base.
- Latest `wt-dev` V2 changes are not fully reflected in V3.

## Dirty Worktree Notes

- V3 worktree had only this task's `.omo/boulder.json` and plan edits plus the pre-existing untracked `.omo/evidence/tmap-walkforward/_discovery_feedback.txt`.
- `wt-dev` is dirty with many unrelated user/runtime research artifacts and was used read-only as a reference. Nothing was edited there.
