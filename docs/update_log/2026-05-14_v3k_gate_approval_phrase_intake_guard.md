# V3K gate approval phrase intake guard

| Field | Value |
| --- | --- |
| Date | 2026-05-14 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| page | Page 070 |
| source | Page065 gate matrix, Page067 one-gate sequence guard, Page068/069 goal handoff audits |
| marker | `V3K_GATE_APPROVAL_PHRASE_INTAKE_GUARD` |
| audit version | `V3K_GATE_APPROVAL_PHRASE_INTAKE_AUDIT_V1` |
| status | completed-review-only-intake-guard |

---

## 1. 결론

승인 gate 실행 전에 사용자 문구를 review-only로 검사하는 intake guard를 추가했다. 이 guard는 첫 gate의 정확한 문구만 accepted로 판정하고, broad approval과 out-of-order gate phrase를 거부한다.

No ON/DB/live execution. No USER_ACK creation. No enable registry creation. No KHOPENAPI connect or login. No operating `_database/` write. No DB file commit. No `_v3k_sidecar` artifact creation. No actual writer implementation. No MainWindow wiring. No Kiwoom live runtime change. No live order/exit rule wiring. No direct LS Securities dependency.

---

## 2. Accepted review-only phrase

```text
I approve gui-sidecar-write-await-user-approval only
```

accepted verdict는 즉시 gate execution이 아니다. 의미는 다음 gate cycle을 시작하기 위한 문구 intake가 통과했다는 뜻이며, 실제 실행 전에는 preflight, USER_ACK handling, rollback owner, monitoring owner, green audit이 추가로 필요하다.

---

## 3. Rejected examples

| Phrase type | Verdict |
| --- | --- |
| `approve all gates` | rejected broad approval |
| `I approve all gates` | rejected broad approval |
| `turn everything on` | rejected broad approval |
| `모두 승인` | rejected broad approval |
| `전체 승인` | rejected broad approval |
| `I approve phase-f-f4-on-await-user-approval only` | rejected out-of-order |
| `I approve gui-sidecar-write-await-user-approval` | rejected inexact |

---

## 4. Audit suite integration

| Item | Value |
| --- | --- |
| CLI checker | `scripts/check_v3k_gate_approval_phrase.py` |
| audit script | `scripts/audit_v3k_gate_approval_phrase_intake.py` |
| suite step | `gate_approval_phrase_intake` |
| suite status | V3K audit suite expands from 21 steps to 22 steps |

Directive: 이 page는 승인 문구 검증 guard이며 실제 승인 실행이 아니다. 다음 실제 gate는 여전히 `gui-sidecar-write-await-user-approval` 하나이고, broad approval은 수용하지 않는다.
