# STOM_Version_2U_C - AI Agent Instructions

## Branch Role

`STOM_Version_2U_C` is the single baseline branch for both custom development and CLI automation.
The propagation chain is:

```text
V2 -> 2U(pyd→py) -> 2U_C(custom+CLI) -> research/init
```

## Worktree Layout

```text
C:/System_Trading/STOM/
├── STOM_V/       -> STOM_Version_2
├── STOM_V.wt-2u/ -> STOM_Version_2U
├── STOM_V.wt-2uc/-> STOM_Version_2U_C
├── STOM_V.wt-dev/-> STOM_Version_2U_C
└── STOM_V.wt-lab/-> research/init
```

- `STOM_V.wt-dev/` is the primary active checkout for the baseline lane.
- `STOM_V.wt-2uc/` is a companion checkout for the same baseline lane.
- `STOM_V.wt-lab/` is reserved for `research/init`.

## Serial Key Policy

Do not add serial-key code in this branch family.

- The V2 upstream may contain serial-key authentication in pyd files.
- The 2U family intentionally removes serial-key behavior.
- Never infer serial-key logic back into `2U_C`.

## Upstream Sync Policy

- Sync upstream changes by cherry-pick, not by overlay merge.
- Preserve CLI-specific customizations that belong in the single baseline branch.
- Keep the propagation order strictly one lane at a time.

Required sync order:

```text
V2 -> 2U -> 2U_C -> research/init
```

## Verification Rules

- After upstream sync or branch propagation, run `pytest tests/unit/ -q`.
- If the sync touches non-release paths, also run `python scripts/verify_nonrelease_sync.py`.
- Treat `backtest/graph/` as protected result data.

## Commit Rules

- Use explicit file staging; do not use `git add -A`.
- Keep changes small and reviewable.
- Commit messages must use Korean titles and Korean markdown bodies.

## Strategy Generation Notes

If a task concerns trading-condition generation:

1. Read `utility/ai_agent/strategy.txt`.
2. Read `utility/ai_agent/rules.txt`.
3. Generate STOM syntax in the branch-local text format.
4. Save the generated strategy under `utility/ai_agent/`.
