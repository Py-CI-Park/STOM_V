# V3K Page 040 — Phase G G-3 approval gate 계획

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 page | Page 039 / Phase G G-2 parity·benchmark work |
| 현재 page | Page 040 / Phase G G-3 approval gate |
| 목적 | G-2 proof가 있어도 Phase G를 바로 ON 하지 않고, 사용자 승인·rollback·monitoring·registry 조건을 gate로 고정한다. |
| 위험도 | critical |
| 기본 결론 | 사용자 명시 승인 없이는 ON 실행 금지 |

---

## 1. Page040에서 확인할 조건

Page040은 아래 조건을 점검하고 문서화하는 gate page다.

1. Page039 parity report PASS 여부
2. Page039 benchmark report PASS 여부
3. `V3K_PHASE_G_USER_ACK=1`를 사용할 수 있는 명시적 사용자 승인 존재 여부
4. `V3K-PHASE-G-ENABLE` registry 생성 필요성과 rollback 조건
5. Phase G output이 live order/exit rule에 연결될 때의 rollback plan
6. 최소 24h monitoring 계획
7. Kiwoom runtime 변경 범위와 금지 범위 재확인
8. 운영 DB/sidecar/report artifact commit 금지 확인

---

## 2. Page040에서 금지되는 동작

사용자가 별도 ON cycle을 명시적으로 승인하지 않는 한 Page040에서도 아래를 실행하지 않는다.

- `V3K_PHASE_G_MICROSTRUCTURE_ENGINE=True` 기본값 변경
- `V3K-PHASE-G-ENABLE` registry 생성
- `V3K_PHASE_G_USER_ACK=1` 사용
- live order/exit rule 연결
- KHOPENAPI login/connect 또는 주문 API 호출
- 운영 `_database/` write
- DB 파일 commit

---

## 3. 완료 조건

Page040은 다음 중 하나로 완료된다.

| 결과 | 의미 | 다음 처리 |
| --- | --- | --- |
| `blocked-awaiting-user-approval` | 승인 조건이 충족되지 않아 ON을 보류 | 다른 safe candidate로 이동 |
| `approved-on-plan-only` | 사용자가 ON을 승인했지만 아직 실행 전 계획만 완료 | 별도 execution page 필요 |
| `rejected` | ON 하지 않기로 결정 | Phase G는 default-OFF staged feature로 유지 |

현재 기본 예상은 `blocked-awaiting-user-approval`이다.

Directive: Page040은 approval gate다. 승인 없는 ON 실행은 금지하며, Page039 proof만으로 registry나 live runtime 변경을 수행하지 않는다.
