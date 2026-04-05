# STOM Project Guidelines (STOM_Version_2U_C)

> **워크트리 위치**: `STOM_V.wt-dev/`
> **브랜치 역할**: `STOM_Version_2U_C` 단일 기준선 작업 레인
> **관련 문서**: `C:/System_Trading/STOM/STOM_V/docs/WORKTREE_STRATEGY.md`, `C:/System_Trading/STOM/STOM_V/docs/UPSTREAM_SYNC_STRATEGY.md`

## Read First

- `C:/System_Trading/STOM/STOM_V/docs/FORMAL_UPDATE_OPERATING_SYSTEM.md`
- `C:/System_Trading/STOM/STOM_V/docs/CARRY_FORWARD_REGISTRY.md`
- `C:/System_Trading/STOM/STOM_V/docs/update_log/2026-04-05_v274_v277_cycle_status.md`
- `C:/System_Trading/STOM/STOM_V.wt-dev/docs/update_log/2026-04-04_v274_v277_cli_v267_baseline_note.md`

## Branch Gate

- `python scripts/verify_nonrelease_sync.py`
- `python -m pytest tests/unit/ -q`
- `backtest/graph/` is protected result data.

## Branch Model

`STOM_Version_2U_C` is the single baseline branch for custom development and CLI automation.

Propagation order:

```text
V2 -> 2U -> 2U_C -> research/init
```

## Worktree Roles

- `STOM_V.wt-dev/` is the primary active checkout for `STOM_Version_2U_C`.
- `STOM_V.wt-2uc/` is the companion checkout for the same baseline branch.
- `STOM_V.wt-lab/` is the `research/init` lane.

## Working Rules

- All active feature work starts from `2U_C`.
- Keep custom development, CLI automation, runtime wiring, and result-data boundaries in the baseline branch.
- Do not route live coding through a downstream CLI child lane.
- `backtest/graph/` is protected result data and must not be used as a source path.
- Historical downstream lane names are retired and are not part of the live operating model.

## When to Use Other Lanes

- Use `research/init` only for formal research, experimentation, or branch-local proof-of-concept work.
- Use `STOM_Version_2` and `STOM_Version_2U` as upstream inputs, not as live editing lanes for the 2U_C baseline.
