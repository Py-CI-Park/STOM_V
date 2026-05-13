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

- `STOM_V/` -> `STOM_Version_2`
- `STOM_V.wt-2u/` -> `STOM_Version_2U`
- `STOM_V.wt-3/` -> `STOM_Version_3`
- `STOM_V.wt-3u/` -> `STOM_Version_3U`
- `STOM_V.wt-dev/` -> `STOM_Version_2U_C`
- `STOM_V.wt-2uc/` is retired/not active in the current five-worktree layout.

Active propagation chain:

```text
V2 -> 2U -> 2U_C
```

## Worktree Layout

Current active layout:

```text
C:/System_Trading/STOM/
STOM_V/          -> STOM_Version_2
STOM_V.wt-2u/    -> STOM_Version_2U
STOM_V.wt-3/     -> STOM_Version_3
STOM_V.wt-3u/    -> STOM_Version_3U
STOM_V.wt-dev/   -> STOM_Version_2U_C
```

- `STOM_Version_2U_C` must be checked out only in `STOM_V.wt-dev/` while this layout is active.
- `STOM_V.wt-2uc/` is no longer an active worktree. Do not recreate it unless the user explicitly reopens an archive lane.

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

`research/init` and V3 work are excluded from the current formal V2.78/V2.79 wave.
The V3K section below is the separate active custom 2U_C V3-feature lane and does
not change the formal V2 release-ingress rules.

## V3K / 2U_C V3 Feature Goal Entry Point

`V3K_2UC_AGENT_ENTRYPOINT_CONTRACT`

This branch is also the active custom V3K lane after the V2 official propagation
work. V3K means:

```text
V3K = V3 features + Kiwoom retained
```

The goal is to bring V3 learning, analysis, DB, backtest, realtime, GUI setting,
and live-decision features into `STOM_Version_2U_C` while preserving the current
Kiwoom API/order/exit/live runtime and excluding LS Securities REST/TR/REAL direct
broker dependency.

Before V3K work in this checkout, read:

1. `docs/update_log/2026-05-08_v3k_full_feature_migration_goal_reset.md`
2. `docs/update_log/2026-05-08_v3_2uc_unmet_features_audit_and_research.md`
3. `docs/CARRY_FORWARD_REGISTRY.md`
4. `docs/update_log/2026-05-14_v3k_goal_completion_audit_checklist.md`
5. `docs/update_log/2026-05-14_v3k_gui_sidecar_gate1_execution.md`
6. `docs/update_log/2026-05-14_v3k_phase_f_gate2_execution.md`
7. `docs/update_log/2026-05-14_v3k_gate_approval_phrase_intake_guard.md`

Current approval-gated state:

- Actual approval gate execution is `2/6`.
- Gate 1 `gui-sidecar-write-await-user-approval` has been approved/executed as
  a default-OFF local sidecar seed only.
- Gate 2 `phase-f-f4-on-await-user-approval` has been approved/executed as a
  Phase F analyzer-strategy sidecar enable only.
- `_v3k_sidecar/v3k_gui_settings.json` is a local ignored runtime artifact and
  must not be committed. It may carry `V3K_PHASE_F_ANALYZER_STRATEGY=true`
  after gate 2.
- Do not call `update_goal(status="complete")` until all six approval gates have
  concrete evidence.
- Do not create additional USER_ACK, enable registry headings, operating
  `_database/` writes, DB cutover, KHOPENAPI connect/login, or live order/exit
  rule wiring without the exact approved gate phrase for that later gate.
- Do not create live order/exit rule wiring without the exact approved gate phrase.
- feature flags must remain default-OFF.
- For this 2U_C lane use `python scripts/verify_nonrelease_sync.py`, not
  `python scripts/verify_release_sync.py`.

Remaining gate order:

1. `gui-sidecar-write-await-user-approval` — completed as default-OFF sidecar write
2. `phase-f-f4-on-await-user-approval` — completed as Phase F sidecar enable
3. `phase-g-g3-on-await-user-approval` — next approval gate
4. `phase-h-h2-h3-live-dryrun-await-user-approval`
5. `f1-actual-db-cutover-await-user-approval`
6. `live-order-exit-rule-consumption-await-user-approval`

The next executable approval phrase is exactly:

```text
I approve phase-g-g3-on-await-user-approval only
```

Continuation must keep gate-specific and nonrelease checks green:

```powershell
python scripts/audit_v3k_phase_f_gate2_execution.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
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
