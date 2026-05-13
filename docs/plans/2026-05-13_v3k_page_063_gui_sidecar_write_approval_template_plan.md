# V3K Page 063 GUI sidecar write approval template plan

| Field | Value |
| --- | --- |
| Date | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| page | Page 063 |
| source | Page059 approval packet, Page060 readiness audit, Page061 blocker audit, Page062 payload preview |
| marker | `GUI_SIDECAR_WRITE_APPROVAL_TEMPLATE` |
| status | plan |
| gate | `gui-sidecar-write-await-user-approval` |

---

## 1. Purpose

Page063 fixes the approval template for the first GUI sidecar actual write gate. The repository still has no approval and no actual writer. This page only defines the text, command shape, rollback shape, and post-write checklist that must be accepted before a later approved execution cycle.

No ON/DB/live execution. No USER_ACK creation. No enable registry creation. No KHOPENAPI connect or login. No operating `_database/` write. No DB file commit. No `_v3k_sidecar` artifact creation. No actual writer implementation. No MainWindow wiring. No Kiwoom live runtime change. No live order/exit rule wiring. No direct LS Securities dependency.

---

## 2. Approval template to be accepted later

The later approval record must explicitly name only this gate:

`I approve gui-sidecar-write-await-user-approval only, with V3K_GUI_SIDECAR_USER_ACK=1, default-OFF payload only, target _v3k_sidecar/v3k_gui_settings.json only, rollback accepted, and no Phase F/G/H ON, no DB cutover, no KHOPENAPI login, no live order/exit decision wiring.`

This phrase is a template only. It is not present approval.

---

## 3. Command template boundary

| Type | Template |
| --- | --- |
| current allowed review command | `python scripts/preview_v3k_gui_sidecar_default_payload.py --format markdown` |
| future approved execution command template | `$env:V3K_GUI_SIDECAR_USER_ACK='1'; python scripts/write_v3k_gui_sidecar_from_preview.py --target _v3k_sidecar/v3k_gui_settings.json --default-off-only --create-backup --atomic-replace` |
| future rollback command template | `python scripts/rollback_v3k_gui_sidecar.py --target _v3k_sidecar/v3k_gui_settings.json --quarantine --restore-backup-if-present` |
| current execution status | blocked because writer and rollback commands are intentionally not implemented before approval |

---

## 4. Post-write validation checklist for later approval cycle

1. Rerun `python scripts/run_v3k_audit_suite.py` immediately before execution.
2. Confirm `V3K_GUI_SIDECAR_USER_ACK=1` is set only for the approved execution session.
3. Generate the payload with `python scripts/preview_v3k_gui_sidecar_default_payload.py --format json`.
4. Execute only the approved writer command after it exists in an approved gate commit.
5. Validate `_v3k_sidecar/v3k_gui_settings.json` schema and default-OFF settings.
6. Confirm no MainWindow wiring, no Phase F/G/H ON, no DB cutover, no KHOPENAPI login, and no live order/exit rule connection.
7. Rerun V3K audit suite, nonrelease sync, diff check, and artifact status after execution.
8. If any schema mismatch, load failure, unexpected artifact, or user stop occurs, execute rollback and return to default-OFF fallback.

---

## 5. STOP condition

Stop before execution if any of these are missing: explicit approval phrase, USER_ACK, owner acceptance, rollback acceptance, green pre-write audit, approved writer implementation, post-write validation owner.

Directive: `GUI_SIDECAR_WRITE_APPROVAL_TEMPLATE` is a template-only page. It does not approve or execute sidecar write and must not be used to create USER_ACK, writer implementation, sidecar artifact, MainWindow wiring, Phase F/G/H ON, DB cutover, KHOPENAPI login, Kiwoom live runtime changes, or live order/exit decision wiring.
