# V3K-PHASE-E4: GUI sidecar write guard/rollback decision

작성일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`

---

## 1. 작업 목적

2U_C의 V3K 목표는 Kiwoom을 유지하면서 V3 기능을 안전하게 이행하는 것이다. Page 023은 GUI sidecar persistence를 성급하게 write로 전환하지 않고, 실제 write 허용 전에 필요한 guard/rollback 기준을 확정하기 위한 decision page다.

결론은 **write 보류**다. Page 022의 read-only loader는 완료되었지만, actual write는 backup-before-replace, atomic write, rollback, corruption recovery, no-DB-sync, session override 우선순위, artifact 미커밋 조건이 구현과 smoke로 증명되기 전까지 허용하지 않는다.

---

## 2. 위험/조건 테이블

| 위험 | 필요한 조건 | 현재 결정 |
| --- | --- | --- |
| partial file | atomic write 후 replace가 실패해도 기존 파일이 보존되어야 함 | 미구현이므로 write 보류 |
| 기존 설정 손실 | backup-before-replace가 보장되어야 함 | 미구현이므로 write 보류 |
| corrupt sidecar | corruption recovery가 default-OFF fallback과 백업 복구 규칙을 가져야 함 | loader fallback만 존재하므로 write 보류 |
| DB 동기화 혼선 | operating `_database/setting.db`와 no-DB-sync 원칙이 문서/검증되어야 함 | no-DB-sync 유지 |
| 세션 우선순위 역전 | session override가 sidecar보다 항상 우선해야 함 | Page 021/022에서 검증, 유지 |
| artifact 커밋 위험 | `_v3k_sidecar/`, `_database`, `_log`, `*.db`, `backtest/graph` artifact가 생성/커밋되지 않아야 함 | audit로 유지 |
| live runtime 영향 | Kiwoom 주문/청산/live runtime에 연결되지 않아야 함 | VERIFY-1A guard 유지 |

---

## 3. Approval gate

다음 조건이 모두 충족되기 전까지 actual sidecar write는 진행하지 않는다.

1. writer는 기본 repo 경로에 즉시 쓰지 않고, tempfile-only smoke로 먼저 검증한다.
2. atomic write 방식은 partial file을 남기지 않아야 한다.
3. backup-before-replace는 기존 valid sidecar를 복구 가능하게 보존해야 한다.
4. rollback은 writer 실패, corrupt payload, schema mismatch, permission/read 실패를 모두 default-OFF 또는 기존 valid state로 되돌려야 한다.
5. corruption recovery는 기존 파일을 자동 overwrite하지 않아야 한다.
6. no-DB-sync 원칙에 따라 operating `setting.db`에는 어떤 write도 하지 않아야 한다.
7. session override 우선순위는 sidecar보다 높아야 한다.
8. artifact status는 `_v3k_sidecar`, `_database`, `_database_v3k_shadow`, `_log`, `backup`, `*.db`, `backtest/graph` 기준으로 clean이어야 한다.
9. `audit_v3k_verify_1b_closure.py`의 `Actual GUI sidecar write implementation`은 별도 승인 전까지 `USER_APPROVAL_REQUIRED`에 남아야 한다.

---

## 4. 추가 검증

신규 audit:

- `scripts/audit_v3k_gui_sidecar_write_guard.py`

검증 내용:

- Page 023/024 문서 존재
- write guard decision marker 존재
- `strategy/v3k_gui_sidecar.py`가 read-only 상태인지 확인
- missing sidecar가 default-OFF fallback으로 닫히는지 확인
- actual sidecar write가 여전히 approval-required인지 확인
- repo sidecar/DB/runtime artifact가 생성되지 않았는지 확인

---

## 5. 다음 단계

Page 024는 actual writer가 아니라 `V3K-PHASE-E5: read-only sidecar preview initialization bridge`로 진행한다.

Page 024의 목적은 사용자가 수동으로 만든 valid sidecar 파일이 있을 때, 이를 session-only preview 초기값으로만 읽어오는 안전 경계를 검토하는 것이다. 이 단계에서도 write, DB sync, live runtime, formula/global runtime hook, analyzer trading decision은 금지한다.
