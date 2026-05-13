# V3K Page 070 gate approval phrase intake guard plan

| Field | Value |
| --- | --- |
| Date | 2026-05-14 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| page | Page 070 |
| source | Page065 gate matrix, Page067 one-gate sequence guard, Page068 goal handoff |
| status | planned-review-only-intake-guard |

---

## 1. 목적

남은 gate를 한 번에 하나씩 진행하기 위해, 사용자 승인 문구를 side-effect 없이 검사하는 review-only intake guard를 추가한다.

---

## 2. 허용 범위

- 첫 gate의 정확한 승인 문구만 review-only로 인식한다.
- broad approval, out-of-order gate phrase, inexact phrase는 거부한다.
- USER_ACK, enable registry, sidecar actual write, DB cutover, KHOPENAPI login, live order/exit wiring은 실행하지 않는다.

---

## 3. 첫 gate 문구

```text
I approve gui-sidecar-write-await-user-approval only
```

이 문구가 accepted로 판정되어도 즉시 실행 승인이 완료된 것이 아니라, 다음 preflight/USER_ACK 처리 cycle을 시작할 수 있는 review-level intake가 통과했다는 뜻이다.

---

## 4. 검증

- `python scripts/check_v3k_gate_approval_phrase.py --phrase "I approve gui-sidecar-write-await-user-approval only" --expect accepted`
- `python scripts/audit_v3k_gate_approval_phrase_intake.py`
- `python scripts/run_v3k_audit_suite.py`
- `python scripts/verify_nonrelease_sync.py`
- `git diff --check`
- guarded artifact status
