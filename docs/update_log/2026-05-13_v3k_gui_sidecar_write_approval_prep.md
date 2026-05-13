# V3K GUI sidecar write approval prep

| ?? | ? |
| --- | --- |
| ??? | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| page | Page 049 |
| source | Page048 approval-gate-selection |
| marker | `GUI_SIDECAR_WRITE_APPROVAL_PREP` |
| ?? | `completed-approval-prep` |
| next candidate | `gui-sidecar-write-await-user-approval` |

---

## 1. ??

GUI actual sidecar write gate? ?? approval gate ? ?? ?? ??? ? ?? ????, ?? ????? ?? write? ???? ???.

?? ??? source-of-truth, prompt-to-artifact checklist, rollback/monitoring, STOP condition? ???? ?? ?? ???.

No actual write execution: actual sidecar write ??, sidecar artifact ??, Phase F/G/H ON, enable registry, USER_ACK ??, Kiwoom live runtime, ?? `_database/` write, DB ?? commit, `.omx/reports` raw artifact commit, live order/exit rule ??? ???? ???.

---

## 2. ?? ??

| ?? | ?? |
| --- | --- |
| `strategy/v3k_gui_sidecar.py` | read-only validation/loader/merge contract? ?? |
| `scripts/audit_v3k_gui_sidecar_write_guard.py` | strategy module writer ??, actual write approval required ?? |
| `scripts/smoke_v3k_gui_sidecar_tempfile_writer.py` | tempfile-only atomic write, backup-before-replace, rollback, corrupt reject proof |
| `scripts/run_v3k_audit_suite.py` | V3K ?? safety/audit runner |
| `scripts/audit_v3k_verify_1a.py` | Kiwoom/runtime untouched, LS dependency marker, artifact guard |

---

## 3. Prompt-to-artifact checklist

| ???? | concrete evidence | ?? ?? |
| --- | --- | --- |
| LS Securities ?? | VERIFY-1A, Phase G LS excise | ?? |
| Kiwoom ?? ??/??/live runtime ?? | VERIFY-1A | ?? |
| sidecar actual write ? ?? ?? | VERIFY-1B USER_APPROVAL_REQUIRED | ?? |
| sidecar strategy module read-only | write guard audit | ?? |
| missing/invalid sidecar default-OFF | loader + write guard audit | ?? |
| tempfile writer proof | tempfile writer smoke | ?? |
| repo sidecar artifact ?? | sidecar write guard + audit suite artifact status | ?? |
| ?? DB write ?? | audit suite artifact status | ?? |

---

## 4. Actual write ?? ? ??? ???

1. `GUI actual sidecar write` gate? ??? ?? ??
2. source-of-truth ??: `_v3k_sidecar/v3k_gui_settings.json` ?? ??
3. writer ?? ??: GUI ?? ??, ?? ? ??, ?? ?? ? ??
4. rollback ??: backup-before-replace, corrupt reject, temp cleanup, disable path
5. monitoring ??: ??/?? log, schema mismatch, default-OFF fallback ??

---

## 5. ?? ??

?? ??? `gui-sidecar-write-await-user-approval`??. ???? ? gate? ????? ???? ??? actual writer ???? ???? ???.

Directive: `GUI_SIDECAR_WRITE_APPROVAL_PREP`? ?? ?? ???? actual sidecar write ??, USER_ACK, ON ??, DB cutover, Kiwoom live runtime ???? ???? ? ??.
