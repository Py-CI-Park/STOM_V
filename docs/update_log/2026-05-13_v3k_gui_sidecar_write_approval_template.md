# V3K GUI sidecar write approval template

| Field | Value |
| --- | --- |
| Date | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| page | Page 063 |
| source | Page059 approval packet, Page060 readiness audit, Page061 blocker audit, Page062 payload preview |
| marker | `GUI_SIDECAR_WRITE_APPROVAL_TEMPLATE` |
| status | completed-template-only |
| gate | `gui-sidecar-write-await-user-approval` |

---

## 1. Conclusion

The GUI sidecar actual write gate now has a fixed approval template, command-shape boundary, rollback-shape boundary, and post-write validation checklist. This reduces ambiguity for the later approval cycle while keeping the repository in the current blocked state.

No ON/DB/live execution. No USER_ACK creation. No enable registry creation. No KHOPENAPI connect or login. No operating `_database/` write. No DB file commit. No `_v3k_sidecar` artifact creation. No actual writer implementation. No MainWindow wiring. No Kiwoom live runtime change. No live order/exit rule wiring. No direct LS Securities dependency.

---

## 2. Approval phrase template

A later approval must explicitly state the following template or an equivalent update_log approval record:

`I approve gui-sidecar-write-await-user-approval only, with V3K_GUI_SIDECAR_USER_ACK=1, default-OFF payload only, target _v3k_sidecar/v3k_gui_settings.json only, rollback accepted, and no Phase F/G/H ON, no DB cutover, no KHOPENAPI login, no live order/exit decision wiring.`

Current state: the phrase is documented only and is not approval.

---

## 3. Command and rollback template

| Type | Template | Current state |
| --- | --- | --- |
| Review command | `python scripts/preview_v3k_gui_sidecar_default_payload.py --format markdown` | allowed, no write |
| Future approved execution command template | `$env:V3K_GUI_SIDECAR_USER_ACK='1'; python scripts/write_v3k_gui_sidecar_from_preview.py --target _v3k_sidecar/v3k_gui_settings.json --default-off-only --create-backup --atomic-replace` | blocked, writer intentionally absent |
| Future rollback command template | `python scripts/rollback_v3k_gui_sidecar.py --target _v3k_sidecar/v3k_gui_settings.json --quarantine --restore-backup-if-present` | blocked, rollback command intentionally absent |

The future execution and rollback commands are intentionally not implemented in this page. Implementing them is part of a later approved gate cycle.

---

## 4. Post-write validation checklist

| Check | Required evidence |
| --- | --- |
| pre-write suite | `python scripts/run_v3k_audit_suite.py` green immediately before execution |
| approval | explicit approval phrase plus `V3K_GUI_SIDECAR_USER_ACK=1` |
| payload | `python scripts/preview_v3k_gui_sidecar_default_payload.py --format json` output validates default-OFF |
| target | `_v3k_sidecar/v3k_gui_settings.json` only |
| schema | `validate_v3k_gui_sidecar_payload` valid |
| fallback | missing or invalid sidecar returns default-OFF fallback |
| runtime | no MainWindow wiring, no Phase F/G/H ON, no DB cutover, no KHOPENAPI login, no live order/exit connection |
| post-write suite | V3K audit suite, nonrelease sync, diff check, artifact status |
| rollback | rollback command and owner accepted before execution |

---

## 5. Audit integration

`scripts/audit_v3k_gui_sidecar_approval_template.py` verifies that the template exists while the gate remains blocked. It fails if USER_ACK is already set, if `_v3k_sidecar` exists, if current writer or rollback scripts appear before approval, or if the required approval/rollback/post-write tokens are missing.

Directive: Page063 is template-only. Passing it means the later approval cycle has less ambiguity; it does not approve sidecar write, USER_ACK creation, writer implementation, MainWindow wiring, Phase F/G/H ON, DB cutover, KHOPENAPI connect/login, Kiwoom live runtime change, or live order/exit rule consumption.
