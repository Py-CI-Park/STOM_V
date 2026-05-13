# V3K Page 079 GUI sidecar gate1 execution plan

`V3K_GUI_SIDECAR_GATE1_EXECUTION_PLAN`

## Goal

Treat the user message `gate 1 approved` as explicit approval for the first gate, `gui-sidecar-write-await-user-approval`, and limit execution to writing the default-OFF seed at `_v3k_sidecar/v3k_gui_settings.json`.

## Scope

- Approval gate: `gui-sidecar-write-await-user-approval`
- Canonical approval phrase: `I approve gui-sidecar-write-await-user-approval only`
- Runtime artifact: `_v3k_sidecar/v3k_gui_settings.json`
- Writer: `scripts/write_v3k_gui_sidecar_from_preview.py`
- Rollback: `scripts/rollback_v3k_gui_sidecar.py`
- Audit: `scripts/audit_v3k_gui_sidecar_gate1_execution.py`

## Out of scope

- No DB cutover
- No KHOPENAPI connect/login
- No Phase F/G/H ON
- No live order/exit wiring
- No MainWindow/pyd wrapper mutation
- No Kiwoom live runtime mutation
- No direct LS Securities dependency

## Verification

```powershell
$env:V3K_GUI_SIDECAR_USER_ACK='1'; python scripts/preflight_v3k_gui_sidecar_write_gate.py --phrase "I approve gui-sidecar-write-await-user-approval only" --format json
$env:V3K_GUI_SIDECAR_USER_ACK='1'; python scripts/write_v3k_gui_sidecar_from_preview.py --approve "I approve gui-sidecar-write-await-user-approval only" --format json
python scripts/audit_v3k_gui_sidecar_gate1_execution.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
git ls-files _v3k_sidecar/v3k_gui_settings.json
```

## Stop condition

- `V3K_GUI_SIDECAR_GATE1_EXECUTION` audit passes.
- Actual gate execution progress becomes `1/6`.
- Next gate is `phase-f-f4-on-await-user-approval`.
- `_v3k_sidecar` runtime artifact remains uncommitted.
