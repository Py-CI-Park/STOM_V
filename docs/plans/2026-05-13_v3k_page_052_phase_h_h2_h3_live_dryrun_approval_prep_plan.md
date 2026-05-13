# V3K Page 052 - Phase H H-2/H-3 Kiwoom live dry-run approval prep 계획

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 page | Page 051 / Phase G G-3 ON approval prep |
| 현재 page | Page 052 / Phase H H-2/H-3 Kiwoom live dry-run approval prep |
| 상태 | `completed-approval-prep` |
| 다음 후보 | `phase-h-h2-h3-live-dryrun-await-user-approval` |
| 목적 | H-2/H-3 Kiwoom live dry-run 전에 필요한 KHOPENAPI 환경, 사용자 승인, USER_ACK, zero-order evidence, rollback, monitoring 조건을 문서와 감사 도구에 고정한다. |
| 위험도 | approval prep은 낮음, actual KHOPENAPI connect/login과 ON은 critical |
| 실제 live dry-run 여부 | 아님. KHOPENAPI connect/login 없이 approval prep 문서화만 수행한다. |

---

## 1. 목표 재확인

V3K의 목표는 **LS Securities 직접 의존성을 제외하고 Kiwoom API/주문/청산/live runtime을 유지한 채 V3의 학습/분석/DB/backtest/realtime 기능을 `STOM_Version_2U_C`에 이행**하는 것이다.

Phase H는 Kiwoom live runtime과 가장 가까운 영역이다. H-1에서는 contract-only dry-run hook과 sentinel audit만 준비했으며, H-2/H-3는 실제 KHOPENAPI 호환 환경과 사용자 승인이 필요하다. Page052는 actual live dry-run을 실행하지 않고, 승인 전에 반드시 만족해야 하는 조건만 고정한다.

---

## 2. 현재 Phase H 준비 상태

| 증거 | 역할 | 현재 상태 |
| --- | --- | --- |
| `strategy/v3k_kiwoom_dryrun_hook.py` | H-1 contract-only dry-run hook | staged |
| `scripts/smoke_v3k_phase_h_hook_unit.py` | default-OFF, login-only registration, idempotent diagnostic, sentinel guard 검증 | PASS 대상 |
| `scripts/audit_v3k_phase_h_env_check.py --stdout` | KHOPENAPI 환경 유무를 보고하되 live connect를 시도하지 않는 sentinel audit | PASS 대상 |
| `scripts/audit_v3k_verify_1a.py --base 57496d24` | Kiwoom 주문/청산/live runtime 경로 보존 | PASS 대상 |
| `scripts/run_v3k_audit_suite.py` | 전체 V3K default-OFF, LS excise, artifact guard | PASS 대상 |

---

## 3. Prompt-to-artifact checklist

| 요구사항 | concrete evidence | Page052 처리 |
| --- | --- | --- |
| Kiwoom 주문/청산/live runtime 유지 | VERIFY-1A, runtime activation gap | actual runtime 미변경 |
| LS Securities 직접 의존 금지 | VERIFY-1A / LS marker audit | Phase H approval prep에도 LS broker 의존성 금지 |
| H-1 contract-only hook 유지 | hook unit smoke, env sentinel audit | actual connect/login 없이 유지 |
| KHOPENAPI 환경 없는 실행 금지 | `audit_v3k_phase_h_env_check.py --stdout` | compatible environment 필요 조건 명시 |
| USER_ACK 없는 live dry-run 금지 | Page052 docs + VERIFY-1B guard | `V3K_PHASE_H_USER_ACK=1` 필요 조건 명시 |
| H feature flag default-OFF 유지 | `V3K_PHASE_H_KIWOOM_DRYRUN` default-OFF | actual enable 없이 유지 |
| rollback/kill switch 없는 실행 금지 | Page052 docs | `V3K_PHASE_H_DISABLE=1` 또는 동등 rollback 조건 명시 |
| 주문 API 0건 증거 필요 | Page052 docs | zero-order evidence를 post-health 필수 조건으로 명시 |
| 운영 DB write 금지 | audit suite artifact guard | `_database/`, DB 파일, live artifact commit 금지 |
| live order/exit rule 연결 금지 | VERIFY-1A guarded runtime files | actual live decision path 미연결 |

---

## 4. Actual H-2 live dry-run 전 필수 승인 조건

1. 사용자가 `Phase H H-2 Kiwoom live dry-run` gate를 명시적으로 승인한다.
2. KHOPENAPI 호환 환경이 준비되어 있고, 세션에서 사용할 수 있음을 사용자가 확인한다.
3. `V3K_PHASE_H_USER_ACK=1` 또는 동등한 승인 기록이 생성된다.
4. `V3K_KHOPENAPI_DLL` 또는 동등 sentinel path가 실제 파일로 확인된다.
5. `V3K_PHASE_H_KIWOOM_DRYRUN` enable 범위가 read-only diagnostic 1회로 제한된다.
6. 주문 API 호출 0건, 계좌/포지션/주문 history 변화 0건을 post-health로 증명한다.
7. `V3K_PHASE_H_DISABLE=1` 또는 동등 rollback/kill switch path가 검증된다.
8. 아래 검증이 모두 PASS한다.

```powershell
python scripts/smoke_v3k_phase_h_hook_unit.py
python scripts/audit_v3k_phase_h_env_check.py --stdout
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/run_v3k_audit_suite.py
```

---

## 5. Actual H-3 ON 전 필수 승인 조건

H-3 ON은 H-2 live dry-run 승인과 별개다. H-2가 통과하더라도 H-3 ON에는 다음 별도 승인과 증거가 필요하다.

1. 사용자가 `Phase H H-3 ON` gate를 별도로 명시 승인한다.
2. H-2 dry-run post-health가 주문 API 0건, 계좌/주문/포지션 변화 0건을 증명한다.
3. 7일 monitoring 범위, alert, rollback owner, fallback trigger가 확정된다.
4. live order/exit rule consumption과 연결되는 경우 별도 critical gate로 분리한다.
5. 운영 `_database/` write, DB file commit, raw report commit은 계속 금지한다.

---

## 6. STOP condition

다음 중 하나라도 충족되지 않으면 H-2/H-3 live dry-run 또는 ON을 수행하지 않는다.

- 사용자 명시 gate 승인 부재
- KHOPENAPI 호환 환경 미확인
- `V3K_PHASE_H_USER_ACK=1` 또는 동등 승인 기록 부재
- `V3K_KHOPENAPI_DLL` sentinel 미확인
- `V3K_PHASE_H_DISABLE=1` 또는 동등 rollback/kill switch 부재
- zero-order evidence 수집 계획 부재
- post-health와 7일 monitoring 계획 부재
- Kiwoom 주문/청산/live runtime 코드 변경 발생
- LS Securities 직접 의존 발생
- 운영 `_database/`, DB 파일, live artifact, `.omx/reports` raw artifact commit 위험 발생

---

## 7. 다음 단계

현재 Page052의 결론은 `phase-h-h2-h3-live-dryrun-await-user-approval`이다. 다음 실제 실행은 사용자 승인과 KHOPENAPI 호환 환경 확인 전에는 수행하지 않는다. 승인 전 안전 작업으로는 F1 actual DB cutover approval prep 재정리 또는 live order/exit rule consumption gate 정리만 허용한다.
