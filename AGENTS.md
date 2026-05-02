# STOM_Version_2U_C - AI Agent Instructions

## pyd ?? ?? ?? ???

- `STOM_Version_2U_C`? 2U?? ??? pyd ?? ??? ?? ???? ????.
- `.pyd` ??? ?? ???? ??? ????? upstream? ???? ??, 2U_C ?? ??? ?? ??? ?? ??? ???.
- pyd ???? ?? `.py` ??? ???? MainWindow ?? ??? ?? ??? ???? ??.
- ?? ?? ????? ???? ???. GUI ????? ?? ??, ????/?? ?????, ???? `activated` wrapper, ??/??? ?????? ????.
- `sactivated_*`/`cactivated_*` ?? ??? alias ??? ??? ????, ?? ?? ??? `activated_XX(self, 'stock'/'coin')`? ????.
- 2U?? ??? pyd ?? ??? 2U_C?? ?? ??? ??? ?? ???? ????.
- ??? ??? ?? `verify_pyd_gui_contract.py`, `smoke_offline_gui.py`, ?? ??? ?? `verify_nonrelease_sync.py` ? ?? ???? ????.


## Branch Role

This checkout is the active `STOM_Version_2U_C` lane for the current official V2 update wave.

Current execution state:

- `STOM_V.wt-dev/` -> `STOM_Version_2U_C`
- `STOM_V.wt-2uc/` -> `integration/adopt-cli-v267-into-2uc` (archive/transition checkout kept off `STOM_Version_2U_C` to respect git worktree branch occupancy)

Active propagation chain:

```text
V2 -> 2U -> 2U_C
```

## Worktree Layout

Current active layout:

```text
C:/System_Trading/STOM/
├── STOM_V/       -> STOM_Version_2
├── STOM_V.wt-2u/ -> STOM_Version_2U
├── STOM_V.wt-2uc/-> integration/adopt-cli-v267-into-2uc
├── STOM_V.wt-dev/-> STOM_Version_2U_C
```

- `STOM_Version_2U_C` must be checked out only in `STOM_V.wt-dev/` while this layout is active.
- `STOM_V.wt-2uc/` keeps promotion history and execution logs on the integration/archive branch.

## Serial Key Policy

Do not add serial-key code in this branch family.

- The V2 upstream may contain serial-key authentication in pyd files.
- The 2U family intentionally removes serial-key behavior.
- Never infer serial-key logic back into `2U_C`.

## Upstream Sync Policy

- Sync upstream changes by cherry-pick, not by overlay merge.
- Preserve CLI-specific customizations that have already been absorbed into the single baseline branch.
- Do not recreate a downstream CLI child lane as the live propagation path.
- Do not check out `STOM_Version_2U_C` in `wt-2uc` while `wt-dev` is the active baseline holder.

Current live sync flow:

```text
V2 -> 2U -> STOM_Version_2U_C
```

`research/init` and V3 work are excluded from the current V2.78/V2.79 wave.

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
