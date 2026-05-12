# V3K 진척률 측정 산식 방법론

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-12 KST |
| trigger | mid-checkpoint(`3da98175`) W2 — 진척률 % 추정이 산식 없이 임의였음 |
| 적용 범위 | audit §6.2 8 항목 진척률 측정, mid-checkpoint 갱신, 미래 진척 보고 |
| Phase A plan freeze 영향 | 없음 (산식 정의는 별도 메타) |

---

## 0. 요지

```text
audit §6.2 8 항목의 진척률은 다음 4단계 가중치로 측정한다.
0%(미진행) → 25%(설계 완료) → 50%(safe-staged 완료) → 75%(read-only/dry-run 완료) → 100%(operational activation 완료)
각 항목은 산식이 정해진 PASS/FAIL 명령으로 단계 판정이 자동화된다.
영구 금지 항목(L7 LS)은 진척률에 포함하지 않고 보존도(preservation rate) 별도 측정.
```

---

## 1. 산식 정의

### 1.1 4단계 가중치

| 단계 | 가중치 | 의미 |
| --- | --- | --- |
| S0 | **0%** | 미진행. plan/설계 문서 없음 또는 작성 중 |
| S1 | **25%** | 설계 완료. plan 문서 + ralplan 합의(또는 동등 검토) 통과. 코드 변경 없음 |
| S2 | **50%** | safe-staged 완료. adapter/contract/no-op boundary 신설. feature flag default-OFF. 운영 경로 미변경 |
| S3 | **75%** | read-only/dry-run 완료. 실제 데이터 read 또는 dry-run hook 작동. write/runtime 영향 없음 |
| S4 | **100%** | operational activation 완료. live write/runtime 영향 발생. 사용자 명시 승인 후 |

### 1.2 단계 전이 trigger

| 전이 | trigger |
| --- | --- |
| S0 → S1 | 해당 phase plan 문서 commit + (ralplan 합의 OR 사용자 명시 승인) |
| S1 → S2 | safe-staged 코드 commit + 해당 phase smoke 통과 + lifetime invariant L1–L9 무회귀 |
| S2 → S3 | read-only/dry-run smoke 통과 + audit guard PASS |
| S3 → S4 | live write/runtime commit + V01–Vn 통과 + 사용자 명시 승인 |

### 1.3 measurement 명령 (단계별 PASS/FAIL)

| 단계 | 측정 명령 패턴 | PASS 기준 |
| --- | --- | --- |
| S1 | `Test-Path docs/plans/<phase>_plan.md` + `git log --grep=<phase>` | plan 파일 존재 + ralplan 합의 commit 기록 |
| S2 | `python -m pytest tests/unit/<phase>_*.py -q` + `python scripts/smoke_v3k_<phase>.py` | exit 0 양쪽 |
| S3 | `python scripts/smoke_v3k_<phase>_readonly.py` + V01–Vn 통과 | exit 0 + smoke output PASS |
| S4 | `python scripts/audit_v3k_<phase>_operational.py` + `verify_release_sync.py` | exit 0 + "release sync preflight passed" |

---

## 2. audit §6.2 8 항목별 현재 단계 (e1c4619c 시점)

| # | 항목 | 단계 | % | 산식 적용 결과 |
| ---: | --- | :---: | ---: | --- |
| 1 | shadow DB 생성 + cutover | S2 | **50%** | shadow 생성(`1196946a`) S2 / cutover S0 (별도 phase plan 미작성, F1로 해소 예정) |
| 2 | production learning DB read | S2 | **50%** | shadow read-only(`3eac14ec`) S2 / production read S0 (F5로 해소 예정) |
| 3 | GUI setting persistence | S3 | **75%** | bridge(`88335424`) + inert(`92436a8e`) + preview(`5c1b9f7a`) + read-only sidecar(`eb7d5631`) + preview init(`e1c4619c`) 모두 S3 / write S0 (Page 025–026+ 예정) |
| 4 | runtime `globals().update(...)` | S2 | **50%** | facade(`c67fdf9b`) + dry-run adapter S2 / runtime hook 보류 (D2 결정) |
| 5 | live Kiwoom dry-run hook | S0 | **0%** | letter H로 재배치, plan 미작성 |
| 6 | analyzer output 전략 반영 | S0 | **0%** | Phase F plan 미작성 (F3로 해소 예정) |
| 7 | V3 microstructure engine | S0 | **0%** | Phase G plan 미작성 (F4로 해소 예정) |
| 8 | LS 직접 의존 (L7) | n/a | n/a | 진척률 미포함. **보존도 100%** (LS marker 0건) |

### 2.1 전체 진척률 (8개 중 1번 영구 금지 제외)

```text
전체 진척률 = (50 + 50 + 75 + 50 + 0 + 0 + 0) / (7 × 100) = 225 / 700 = 32.1%
```

### 2.2 단계별 분포

| 단계 | 항목 수 | 항목 # |
| --- | ---: | --- |
| S0 (0%) | 3 | #5, #6, #7 |
| S1 (25%) | 0 | — |
| S2 (50%) | 3 | #1, #2, #4 |
| S3 (75%) | 1 | #3 |
| S4 (100%) | 0 | — |
| 영구 금지 보존 | 1 | #8 |

---

## 3. 진척률 갱신 절차

### 3.1 갱신 trigger

다음 시점에 진척률을 재측정한다.

- 새 phase plan commit 시 (S0 → S1 전이 가능성)
- 새 safe-staged 코드 commit 시 (S1 → S2 전이 가능성)
- 새 smoke/audit 통과 시 (S2 → S3 전이 가능성)
- live write/runtime commit + 사용자 명시 승인 시 (S3 → S4 전이 가능성)
- mid-checkpoint 문서 갱신 시

### 3.2 갱신 방법

mid-checkpoint 문서를 amend하지 않는다(snapshot freeze). 대신 다음을 따른다.

1. 신규 측정값을 새 mid-checkpoint 문서로 신설 (`<날짜>_v3k_midpoint_checkpoint_<base>_to_<head>.md` 명명 규칙)
2. 본 산식 방법론 문서(`2026-05-12_v3k_progress_metric_methodology.md`)는 산식이 변하지 않는 한 freeze
3. 산식 자체가 변경되면 새 methodology 문서 신설

### 3.3 갱신 자동화 후보 (Phase H 이후)

본 방법론을 audit script(`scripts/audit_v3k_progress_metric.py`)로 자동화하는 것을 follow-up으로 둔다. 현 phase에서는 수동 측정.

---

## 4. 가중치 선택 사유

### 4.1 4단계 vs 다른 분해

- **2단계(미진행/완료)**: 너무 거칠어 부분 진척을 표현 못함
- **3단계(미진행/부분/완료)**: "부분"이 모호 (50% 추정 임의)
- **4단계(S0–S4)**: V3K의 safe-staged → read-only → operational 흐름과 1:1 매핑되어 자기설명적 ← **채택**
- **백분율 연속값**: 산식 없이 추정 시 임의성 누적 (mid-checkpoint W2 발현)

### 4.2 S2(safe-staged) = 50% 의미

V3K 미션의 핵심 구분은 **safe-staged vs operational activation**이다(audit §6.1/6.2). S2 = 50%는 "safe-staged 완료"가 미션의 정확한 절반이라는 의미다. S3/S4는 operational activation의 단계적 진척이다.

### 4.3 S3(read-only/dry-run) = 75%

read-only/dry-run은 operational의 첫 단계로 reversible하고 위험이 낮다. S2(50%)에서 한 칸 진척으로 25% 가산은 합리적이다. S4(100%) live activation까지 남은 거리는 동등하다.

---

## 5. 영구 금지 항목 보존도 (L7 LS)

L7(LS 직접 의존 금지)는 진척률에 포함하지 않는다. 대신 **보존도(preservation rate)**를 측정한다.

```text
보존도 = (변경된 파일 중 LS marker 미포함 비율)
산식: (총 변경 파일 - LS marker 매치 파일) / 총 변경 파일 × 100%
```

cd6f5bd2..HEAD 검증 결과:
- 총 변경 파일: 약 40+ (27 commit 합산)
- LS marker 매치 파일: **0건**
- 보존도: **100%**

---

## 6. 본 방법론의 freeze 정책

- **freeze 시점**: 본 commit
- **변경 트리거**: 산식 자체가 바뀌어야 할 때만 신규 methodology 문서 신설 (예: S0–S4 → S0–S6 확장)
- **갱신 금지**: 본 문서를 amend하여 단계 추가/제거 금지

---

## 7. 관련 문서

- `docs/update_log/2026-05-12_v3k_midpoint_checkpoint_cd6f5bd_to_e1c4619c.md` (§5 진척률, 본 산식 적용 baseline)
- `docs/update_log/2026-05-10_2uc_v3k_full_feature_audit.md` (§6.2 8 항목, 산식의 입력)
- `docs/plans/2026-05-10_v3k_phase_a_shadow_db_plan.md` (§K.6 미션 완료 판정 = S4 × 7 + 보존도 100%)
