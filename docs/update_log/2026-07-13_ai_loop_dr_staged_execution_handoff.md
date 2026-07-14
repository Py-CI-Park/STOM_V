# AI 조건식 루프 DR 단계별 실행 인계

> 작성일: 2026-07-13
> 브랜치: `feature/loop-remaining-research-plan-20260713`
> 기준 커밋: `09f5244ad03468d8cee3a03e76ba9925336846cc`
> 목적: 조건식 AI 루프 심층 검토 이후 작업을 안전하게 이어가기 위한 실행 순서·권한 경계·첫 명령 기록

## 1. 이 문서의 역할

이 문서는 다음 작업자가 이전 대화나 장시간의 Ralplan 검토를 다시 추적하지 않고도 후속 작업을 정확히 재개하도록 만든 인계 기록이다.

직접 근거 문서는 다음과 같다.

- 심층 검토 보고서: `docs/update_log/2026-07-13_ai_condition_generation_backtest_analysis_research_review.md`
- 이전 완료·잔여 보고서: `docs/update_log/2026-07-12_ai_condition_loop_deepening_completion_and_remaining_work.md`
- 정본 master: `docs/research/condition_research/plans/2026-07-11_ai_condition_loop_canonical_rebuild_master_plan.md`
- 마지막 전체 Ralplan 최선안: `.gjc/_session-019f5522-62d4-7000-a6be-c94d40c766b9/plans/ralplan/019f5522-62d4-7000-a6be-c94d40c766b9/stage-11-revision.md`
- 마지막 Architect 검토: 같은 디렉터리의 `stage-11-architect.md`
- 마지막 Critic 검토: 같은 디렉터리의 `stage-11-critic.md`

`stage-11-revision.md`는 연구·설계 근거로 보존하지만 Architect `BLOCK`, Critic `REJECT`이므로 실행 권한이나 승인된 계획으로 취급하지 않는다.

## 2. 현재 확정 상태

| 항목 | 상태 |
|---|---|
| G1~G5 기능 개발과 대시보드 V4 | 구현·기존 검증 기록 존재 |
| `system_built` | true |
| CL-R07 `learning_proved` | 격리 run#6 기록상 true, 이번 검토에서 재증명하지 않음 |
| `performance_proved` | false |
| `human_comparison_proved` | false |
| `live_authorized` | false |
| 신규 데이터 추가 | 오너 별도 결정 전 보류 |
| 전역 기능 기본값 | OFF 유지 |
| 보호 DB·결과 | 읽기 전용, 직접 수정 금지 |
| CL-R08~R10 | 정확 승인 문구 전 실행 금지 |
| 최종 Ralplan 실행 합의 | 미달성 |
| 제품 코드 변경 | 이번 계획 작업에서는 없음 |

## 3. 전체 권장 흐름

```text
현재 심층 검토 보고서
  ↓
DR-00 정본 문서·권한 개정
  ↓
DR-00 정확 승인 및 한국어 커밋
  ↓
DR-01~05 코드 통합 계획
  ↓
Ultragoal B — 코드 구현·통합 QA
  ↓
DR-06 읽기 전용 R08 준비도 감사 계획
  ↓
Ultragoal C — 읽기 전용 감사
  ↓
HARD_STOP_AWAITING_CL_R08_DECISION
  ↓
오너의 별도 정확한 CL-R08 승인
  ↓
CL-R08 제한 역사 성능 검증
  ↓
데이터 정책 해제 시 CL-R09
  ↓
CL-R10 동일 조건 인간 전략 비교
```

## 4. 단계별 작업과 권한

| 순서 | 단계 | 작업 | 실행 조건 | 종료 상태 |
|---:|---|---|---|---|
| 1 | DR-00 | CL-R01~R07 receipt 처리, DR 코드 권한, DR-06·HARD STOP 경계 문서화 | 새 DR-00 전용 Ralplan 합의 | 문서 커밋 후 코드 전 정지 |
| 2 | DR-01 | signed R², 첫 손실 MDD, 중립 거래, CSV 정렬·별칭 교정 | DR-00 코드 권한 승인 | 수학·CSV 테스트 통과 |
| 3 | DR-02 | 09:00~15:00 effective profile, Manifest v2, 비용·체결·DB·엔진 hash | DR-00 승인 | 진입점별 effective hash 동일 |
| 4 | DR-03 | 실제 prompt ID/FK, evidence fail-closed, additive schema, resume | DR-02 기반 | 인과 사슬·중단 재개 검증 |
| 5 | DR-04 | repair/discovery 후보팩, SeedPlan, run-wide 중복 제거, OR 분기 게이트 | DR-03 기반 | 생성 파이프라인 통합 |
| 6 | DR-05 | AnalysisCardV3, FDR·CI·표본수, train-only 환류 | DR-01~03 기반 | 통계 안전한 feedback |
| 7 | 통합 QA | DR-01~05 전체 frozen snapshot 검증 | 모든 slice 통과 | 코드 통합 완료 |
| 8 | DR-06 | run#6·R08 preregistration 읽기 전용 감사 | 별도 Ralplan·승인 | readiness verdict 후 HARD STOP |
| 9 | CL-R08 | 60일 train40/validation20 제한 역사 검증 | `R08_READY`와 정확 승인 | survivor 또는 NO-GO |
| 10 | CL-R09 | prospective OOS/WF | 신규 20거래일과 정확 승인 | 현재 데이터 정책상 차단 |
| 11 | CL-R10 | 동일 cohort 인간 전략 비교 | 앞 단계와 정확 승인 | 승격 검토 |

DR-01~05는 구현 slice를 나눌 수 있지만 validation-coupled이므로 최종 완료 판정은 하나의 통합 QA 경계에서 수행한다.

## 5. Ultragoal 분리 원칙

한 Ultragoal에 인간 승인 경계를 모두 넣지 않는다. Ultragoal 실행 중에는 질문·승인 처리가 제한되므로 아래처럼 세 실행으로 분리한다.

### Ultragoal A — DR-00 문서 개정

```text
DR-00 전용 Ralplan 합의
  → G001 amendment 문서 작성
  → G002 기존 CL 문구·receipt 비변경 검증
  → G003 한국어 커밋·SHA 기록
  → 코드 권한 승인 전 정지
```

제품 코드, SQLite schema, provider, 백테스트는 변경하거나 실행하지 않는다.

### Ultragoal B — DR-01~05 코드 통합

```text
승인된 DR-00
  → S0 phase guard
  → DR-01 계산 정확성
  → DR-02 profile/Manifest
  → DR-03 evidence/resume
  → DR-04 후보 생성 통합
  → DR-05 AnalysisCardV3
  → validation-coupled 통합 QA
  → DR-06 승인 전 정지
```

불확실한 외부 side effect는 자동 복구하지 않는다.

```text
provider/evaluator 실행 여부 불확실
  → INDETERMINATE_EXTERNAL_EFFECT
  → 자동 재시도 금지
  → GO receipt 금지
  → 별도 권한 전 정지
```

### Ultragoal C — DR-06 읽기 전용 감사

```text
별도 DR-06 계획·승인
  → 명시적 경로와 hash 검사
  → 원본 SQLite를 직접 열지 않음
  → main/WAL/SHM 완전 복사본만 개방
  → R08_READY 또는 R08_CONTRACT_AMENDMENT_REQUIRED 또는 READINESS_BLOCKED
  → 무조건 HARD_STOP_AWAITING_CL_R08_DECISION
```

## 6. HARD STOP 상태의 정확한 의미

다음 안전 방향은 독립 검토에서 반복적으로 유지됐다.

- DR-06 결과와 무관하게 자동으로 CL-R08을 실행하지 않는다.
- `performance_proved=false`, `human_comparison_proved=false`, `live_authorized=false`를 유지한다.
- `R08_READY`도 실행 승인이 아니다.
- 기존 CL-R08 정확 승인 문구를 별도로 받아야 한다.

다만 새 `HARD_STOP_AWAITING_CL_R08_DECISION` 상태는 아직 정본 amendment로 승인·구현되지 않았다. 따라서 안전 원칙은 합의 방향이지만 현재 runtime 실행 권한은 아니다.

기존 CL-R08 정확 문구:

```text
I approve CL-R08 bounded min performance only
```

이 문구는 DR-06에서 `R08_READY`가 나온 뒤 별도 intake에서만 사용할 수 있다.

## 7. 이전 Ralplan 실패 원인

DR-00~DR-06을 한 계획으로 묶으면서 다음 서로 다른 문제를 동시에 완결하려 했다.

```text
정본 권한
+ Windows 게시 장애 복구
+ SQLite migration
+ provider exactly-once 복구
+ 조건식 생성
+ 통계 분석
+ 과거 DB 감사
```

그 결과 계획의 중심이 조건식 루프 개선에서 증거 게시·장애 복구 플랫폼 설계로 이동했다. 최종 차단점은 다음이었다.

1. G1 백업·게시·복구 작업별 source/destination 상태표가 완결되지 않았다.
2. G3 PREPARE에 hash만 있고 장애 후 복원할 실제 출력·terminal 바이트가 없었다.
3. event hash chain은 있었지만 PREPARE 없는 APPLIED나 terminal 뒤 이벤트를 막는 의미 상태 검증이 부족했다.
4. 통계 아티팩트는 124개 hypothesis와 실제 RNG/FDR 자료를 포함했지만 reducer·최종 receipt 골든까지 있다고 과장했다.

이 실패는 DR-01~05 개선 방향의 부정이 아니다. 한 계획에 과도한 거버넌스·장애 복구 계약을 결합한 범위 설계 실패다.

## 8. 실패 핵심을 해결하는 원칙

### 8.1 DR-00은 문서만 처리

- 새 Windows publisher를 만들지 않는다.
- 새 event-log runtime을 만들지 않는다.
- Ralplan receipt와 Git commit SHA를 amendment identity로 사용한다.
- 기존 CL 승인 문구를 변경하지 않는다.

### 8.2 외부 호출은 fail-closed

외부 호출이 정확히 완료됐는지 증명할 수 없으면 자동 exactly-once 복구 시스템을 만들지 않고 `INDETERMINATE_EXTERNAL_EFFECT`로 중단한다.

### 8.3 통계 골든은 구현 테스트에서 검증

계획 단계에서 동결할 것은 공식, sample gate, FDR, seed, train-only 경계다. 124개 registry hash와 reducer 골든은 코드 구현 후 단위 테스트·통합 테스트가 생성하고 검증한다.

### 8.4 DR-06은 별도 계획

DR-06은 보호된 과거 증거를 다루므로 DR-01~05 코드 통합과 동일 계획·권한으로 실행하지 않는다.

## 9. 지금 실행할 첫 번째 명령

다음 명령은 DR-00 문서 개정만 계획한다. 제품 코드나 백테스트를 실행하지 않는다.

```text
/skill:ralplan --deliberate "DR-00 정본 post-completion amendment만 계획하라. docs/update_log/2026-07-13_ai_condition_generation_backtest_analysis_research_review.md와 docs/update_log/2026-07-13_ai_loop_dr_staged_execution_handoff.md를 근거로 기존 CL-R01~R07 receipt 보존·한정·재검증 범위, DR-01~05 코드 변경 권한, DR-06 읽기 전용 감사 경계와 HARD STOP을 문서화한다. Git commit SHA와 Ralplan receipt만 publication identity로 사용한다. 새로운 Windows publisher, event-log runtime, SQLite schema, 제품 코드, provider, 백테스트, CL-R08~R10은 범위에서 제외한다."
```

합의 후 승인 화면에서는 다음을 선택한다.

```text
Approve execution via ultragoal
```

그 승인으로 실행되는 Ultragoal A는 문서 개정·검증·한국어 커밋까지만 수행하고 코드 변경 전에 종료해야 한다.

## 10. 재개 체크리스트

- [ ] 현재 브랜치가 `feature/loop-remaining-research-plan-20260713`인지 확인
- [ ] 기준 커밋이 `09f5244a` 이후인지 확인
- [ ] 이 문서와 2026-07-13 심층 검토 보고서를 읽음
- [ ] 이전 `stage-11-revision.md`를 승인된 실행계획으로 사용하지 않음
- [ ] DR-00 전용 Ralplan만 시작
- [ ] 새 publisher/event-log/SQLite/product code를 DR-00에 포함하지 않음
- [ ] 합의 후 Ultragoal A로 문서만 변경
- [ ] 코드 변경 전 별도 DR-01~05 Ralplan과 권한을 받음
- [ ] DR-06은 별도 계획·승인으로 실행
- [ ] DR-06 뒤 무조건 HARD STOP
