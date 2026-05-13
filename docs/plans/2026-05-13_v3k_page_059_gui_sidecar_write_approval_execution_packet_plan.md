# V3K Page 059 GUI sidecar write approval execution packet plan

| Field | Value |
| --- | --- |
| Date | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| page | Page 059 |
| source | Page057 GUI sidecar write preflight, Page058 approval order reconciliation |
| marker | `GUI_SIDECAR_WRITE_APPROVAL_EXECUTION_PACKET` |
| status | plan |
| gate | `gui-sidecar-write-await-user-approval` |

---

## 1. Purpose

Page059 prepares the execution packet for the first recommended approval gate, GUI actual sidecar write. This page does not perform the write. It fixes the approval evidence, source of truth, owner roles, rollback path, monitoring path, and fallback triggers that must exist before a later approved write can happen.

No ON/DB/live execution. No USER_ACK creation. No enable registry creation. No KHOPENAPI connect or login. No operating `_database/` write. No DB file commit. No `_v3k_sidecar` artifact creation. No writer implementation. No MainWindow wiring. No Kiwoom live runtime change. No live order/exit rule wiring. No direct LS Securities dependency.

---

## 2. Execution packet fields

| Field | Required value before actual write |
| --- | --- |
| approval record | explicit user approval plus `V3K_GUI_SIDECAR_USER_ACK=1` or equivalent update log record |
| source of truth | `_v3k_sidecar/v3k_gui_settings.json` only after approval |
| first payload | default-OFF V3K settings seed, not live runtime decisions |
| writer entrypoint | isolated approved command or script, not automatic MainWindow persistence |
| rollback owner | user operator plus execution agent for backup restore and sidecar disable |
| monitoring owner | user operator for first run plus execution agent for log and artifact review |
| fallback trigger | schema mismatch, load failure, unexpected artifact status, audit failure, or user stop |
| fallback action | disable sidecar use, remove or quarantine sidecar file, keep V2 settings active |
| commit policy | commit code and docs only, never commit `_v3k_sidecar` runtime artifact |

---

## 3. Approval checklist

| Requirement | Status before approval |
| --- | --- |
| explicit user approval text | missing |
| USER_ACK or equivalent approval record | missing |
| source of truth accepted | candidate only |
| rollback owner accepted | role defined, not yet accepted |
| monitoring owner accepted | role defined, not yet accepted |
| fallback trigger accepted | role defined, not yet accepted |
| V3K audit suite green | required again at execution time |
| `verify_nonrelease_sync.py` green | required again at execution time |
| forbidden artifact status clean | required again before and after execution |

---

## 4. Later approved execution shape

A later approved commit may implement only the following narrow shape.

1. Create or use an isolated writer surface for `_v3k_sidecar/v3k_gui_settings.json`.
2. Validate payload with the existing schema validator before replace.
3. Write to a temp file in the same sidecar directory.
4. Re-read and validate the temp file.
5. Replace the target atomically where the platform allows.
6. Keep an immediately restorable backup or quarantine path.
7. Run the read-only loader smoke after the write.
8. Run the V3K audit suite, nonrelease sync, diff check, and artifact guard.
9. Keep the runtime artifact untracked and uncommitted.

MainWindow persistence remains out of scope for this packet. Live order and exit decisions remain out of scope for this packet.

---

## 5. STOP condition

Stop before actual write if any item below is missing.

- explicit user approval
- USER_ACK or equivalent approval record
- source of truth acceptance
- rollback owner acceptance
- monitoring owner acceptance
- fallback trigger acceptance
- V3K audit suite green
- `verify_nonrelease_sync.py` green
- forbidden artifact status clean

Directive: `GUI_SIDECAR_WRITE_APPROVAL_EXECUTION_PACKET` is an approval packet only. It is not approval for actual sidecar write, USER_ACK creation, writer implementation, MainWindow wiring, ON transition, DB cutover, KHOPENAPI connect or login, Kiwoom live runtime change, or live order/exit rule connection.
