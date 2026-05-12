# V3K 미션 완료 판정 운영 절차

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-12 KST |
| trigger | Phase A plan §K.6 V3K 미션 완료 판정의 운영 절차가 명시되지 않음 |
| 적용 범위 | Phase G 종료 또는 audit §6.2 8 항목 종착 시점에 누가 어떻게 미션 완료를 선언하는지 |
| Phase A plan freeze 영향 | 없음 (§K.6 보강 메타) |

---

## 0. 요지

```text
V3K 미션 완료는 audit §6.2의 7개 달성 항목이 모두 S4(operational) + 1개 영구 금지 항목(L7)이 보존도 100%일 때 선언된다.
선언은 사용자 명시 승인 + closeout audit 통과 + closeout commit으로 3단계 gate를 거친다.
선언 후에는 V3K-CLOSURE registry 등록 + audit 보고서 갱신 + V3K freeze 정책 적용.
선언 전 단 한 단계라도 S4 미달이면 미션은 진행 중 상태로 유지된다.
```

---

## 1. 완료 판정 기준 (closeout gate)

### 1.1 audit §6.2 8 항목 종착 조건

| # | 항목 | 종착 단계 (산식 F6 §1.1) | 검증 명령 |
| ---: | --- | --- | --- |
| 1 | shadow DB 생성 + cutover | S4 (운영 cutover 완료) | `python scripts/audit_v3k_db_cutover.py --read-only` PASS |
| 2 | production learning DB read | S4 (production read 작동) | `python scripts/smoke_v3k_production_learning_read.py` PASS |
| 3 | GUI setting persistence | S4 (실제 write 작동) | `python scripts/smoke_v3k_gui_settings_write.py` PASS |
| 4 | runtime `globals().update(...)` | S4 (runtime hook 작동) | `python scripts/smoke_v3k_formula_runtime_hook.py` PASS |
| 5 | live Kiwoom dry-run hook (letter H) | S4 (dry-run hook live) | `python scripts/smoke_v3k_phase_h_kiwoom_dryrun.py` PASS |
| 6 | analyzer output 전략 반영 | S4 (전략/주문/청산 판단 적용) | `python scripts/smoke_v3k_phase_f_analyzer_strategy.py` PASS + backtest 회귀 PASS |
| 7 | V3 microstructure engine | S4 (G-1/G-2/G-3 모두 종착) | `python scripts/smoke_v3k_phase_g_microstructure.py` PASS + parity benchmark PASS |
| 8 | LS Securities 직접 의존 보존 (L7) | 보존도 100% | F6 §5 산식: LS marker 매치 파일 = 0건 |

### 1.2 lifetime invariant 보존 조건

audit §6.2와 별도로 L1–L9 lifetime invariant가 모두 무회귀로 유지되어야 한다.

| # | invariant | 검증 |
| ---: | --- | --- |
| L1 | schema_hash semantic hash 정의 | `pytest tests/unit/test_v3k_shadow_schema_hash.py -q` PASS |
| L2 | `init_v3k_shadow_db.py` 외부 동작 보존 | manifest JSON 포맷 + `--dry-run required` 무회귀 |
| L3 | sentinel `_v3kshadow_smokeA_` 접두 | `Select-String _v3kshadow_smokeA_` 일관성 |
| L4 | `_database_v3k_shadow/` 형제 위치 | 디렉터리 위치 검증 |
| L5 | feature flag default-OFF | `v3k_feature_flags` 사용자 ON 외 row 검증 |
| L6 | `last_update < backtest_date` | learning DB read 시 규칙 검증 |
| L7 | LS 직접 의존 금지 | F6 §5 보존도 100% |
| L8 | 운영 `_database/`, `*.db` 파일 git commit 금지 | `git log --all -- '*.db'` 0건 |
| L9 | STOM CLI surface 보존 | backtest/realtime/init CLI 외부 동작 무회귀 |

### 1.3 종합 closeout 조건

```text
(audit §6.2 #1~#7 모두 S4) AND (audit §6.2 #8 보존도 100%) AND (L1~L9 모두 무회귀)
```

위 3-tuple이 모두 PASS여야 closeout gate 통과.

---

## 2. 선언 절차 (3단계 gate)

### Gate 1 — Closeout audit 통과

작업자는 다음 audit script(또는 동등 수동 검증)를 실행하여 §1.3 종합 조건을 자동 검증한다.

```powershell
python scripts/audit_v3k_closeout_gate.py --strict
```

PASS 조건:
- exit 0
- stdout `closeout audit passed`
- 각 §6.2 항목별 단계 출력 표가 `audit §6.2 #N: S4` 또는 `보존도 100%`
- L1–L9 검증 결과 모두 `PASS`

FAIL 시 closeout 진행 중단.

`audit_v3k_closeout_gate.py`는 closeout 단계의 별도 task로 신설된다 (현재 미작성, Phase G 종료 직전 작성 권장).

### Gate 2 — 사용자 명시 승인

closeout audit 통과 후 작업자는 사용자에게 다음 form으로 승인을 요청한다.

```text
V3K 미션 완료 판정을 위한 사용자 명시 승인을 요청합니다.

- audit §6.2 #1~#7: 모두 S4 (operational activation 완료)
- audit §6.2 #8 (LS 직접 의존 보존): 보존도 100% (LS marker 0건)
- lifetime invariant L1~L9: 모두 무회귀

closeout audit script 실행 결과: PASS
관련 commit 범위: <closeout 시점의 cd6f5bd2..HEAD 범위>

승인 시 V3K 미션을 "완료(closure)" 상태로 선언하고
docs/update_log/<날짜>_v3k_closure_declaration.md와 V3K-CLOSURE registry 항목을 commit합니다.
승인하시겠습니까?
```

사용자가 명시적으로 "승인"하지 않으면 미션은 진행 중 상태 유지.

### Gate 3 — Closeout commit

사용자 승인 후 다음 단일 commit을 수행한다.

#### 신규 파일

- `docs/update_log/<날짜>_v3k_closure_declaration.md` — 미션 완료 선언 본문

#### 수정 파일

- `docs/CARRY_FORWARD_REGISTRY.md` — `## V3K-CLOSURE` 섹션 추가
- `docs/update_log/2026-05-10_2uc_v3k_full_feature_audit.md` — 본 audit 정본의 §11 또는 별도 절에 "V3K closure 선언일: <날짜>" 한 줄 추가 (이때만 audit freeze 예외)

#### Commit message (한국어, CLAUDE.md `## Commit Language Rules` 정렬)

```text
V3K 미션 완료를 선언한다

- audit §6.2 #1~#7이 모두 S4 operational activation을 만족한다.
- audit §6.2 #8 LS 직접 의존 보존도가 100%다.
- lifetime invariant L1~L9가 모두 무회귀로 유지된다.
- closeout audit 통과와 사용자 명시 승인 후 본 선언을 commit한다.
```

---

## 3. 선언 본문(`<날짜>_v3k_closure_declaration.md`) 표준 양식

```markdown
# V3K 미션 완료 선언

| 항목 | 값 |
| --- | --- |
| 선언일 | <날짜> KST |
| 선언자 | <작업자> (사용자 명시 승인: <date>) |
| baseline commit | cd6f5bd2 |
| closeout commit | <closeout-commit-sha> |

## 1. closeout audit 결과
(audit_v3k_closeout_gate.py stdout 인용)

## 2. audit §6.2 8 항목 종착 증거
(각 항목별 S4 commit sha + smoke 통과 증거)

## 3. lifetime invariant L1~L9 무회귀 증거
(검증 명령 + 결과)

## 4. V3K 미션 statement 최종 확인
(Phase A plan §0.1 미션 statement 재인용 + 100% 부합 선언)

## 5. 사용자 명시 승인 기록
("승인" 발화 일시 + 본 commit sha)

## 6. 후속 freeze 정책
- audit 보고서: closure 선언 후에도 freeze
- Phase A plan: freeze (§K.7 그대로)
- letter remapping decision: freeze
- 모든 phase plan: freeze
- 본 선언 문서: freeze
```

---

## 4. closure 이후 운영

### 4.1 V3K freeze 정책

closure 선언 후 다음이 freeze된다.

| 대상 | freeze 시점 | freeze 범위 |
| --- | --- | --- |
| audit 보고서 | 본래부터 freeze (closure 시 §11 1줄 예외) | 본문 freeze |
| Phase A plan | 본래부터 freeze (§K.7) | 본문 freeze |
| letter remapping decision | 본래부터 freeze | 본문 freeze |
| 모든 phase plan (A–G + H) | closure 시 freeze | 본문 freeze |
| 모든 update_log | 본래부터 snapshot (date-stamped) | 본문 freeze |
| 본 selectout 절차 문서 | closure 후 freeze | 본문 freeze |
| `_database_v3k_shadow/` (이미 cutover됨) | closure 시점 이후 별도 정책 (§4.3) | — |

### 4.2 신규 V3 기능 도입 시 정책

closure 이후 V3 branch에서 추가 신기능이 도입되면 **V3K v2 또는 별도 미션**으로 분리한다. 본 closure는 "현 V3K 정의 = 본 closure 시점의 7 항목"으로 freeze.

### 4.3 `_database_v3k_shadow/` 정책 (Phase G 또는 closure 시점 결정)

closure 시점에 다음 중 하나로 결정한다.

| 옵션 | 설명 |
| --- | --- |
| A | shadow 디렉터리 영구 cleanup (운영 cutover 완료이므로 불필요) |
| B | shadow 디렉터리 보존 (recovery/rollback 용) |
| C | shadow 디렉터리를 archive 디렉터리로 이동 |

Phase A plan §I.Follow-ups F3에 명시된 결정 항목. closure 선언 본문 §3-6 footer에서 옵션을 명시한다.

---

## 5. closure 선언 거부 사유 (FAIL 시)

다음 중 하나라도 발현되면 closure 거부 + 진행 중 상태 유지.

| 거부 사유 | 대응 |
| --- | --- |
| audit §6.2 항목 1개 이상 S3 이하 | 해당 항목 phase plan 진행 재개 |
| L1–L9 invariant 회귀 발견 | invariant 위반 commit 식별 + rollback |
| 보존도 < 100% (LS marker 1건 이상) | 위반 import 제거 + 보존도 재측정 |
| closeout audit script 미작성 | Phase G 종료 직전 작성 후 재시도 |
| 사용자 명시 승인 부재 | 사용자 응답 대기 또는 명시적 거부 시 진행 중 유지 |

---

## 6. 본 절차의 freeze 정책

- **freeze 시점**: 본 commit
- **변경 trigger**: closure 절차 자체가 바뀌어야 할 때만 신규 procedure 문서 신설
- **갱신 금지**: 본 문서를 amend하여 단계 추가/제거 금지

---

## 7. 관련 문서

- `docs/plans/2026-05-10_v3k_phase_a_shadow_db_plan.md` (§K.6 미션 완료 판정 - 본 절차의 전조)
- `docs/update_log/2026-05-10_2uc_v3k_full_feature_audit.md` (§6.2 8 항목)
- `docs/update_log/2026-05-12_v3k_phase_letter_remapping_decision.md` (letter H 등 미래 letter)
- `docs/update_log/2026-05-12_v3k_progress_metric_methodology.md` (S0–S4 산식, closure 기준의 정량 정의)
- `docs/update_log/2026-05-12_v3k_midpoint_checkpoint_cd6f5bd_to_e1c4619c.md` (closure baseline)
