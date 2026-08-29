# ANA-04 G0→G1 Failure Autopsy 구현 결과

> 완료일: 2026-08-29
>
> 구현 브랜치: `codex/process-research-ana-04-failure-autopsy`
>
> 구현 커밋: `f47999aa` — `기능(분석): G0-G1 공통 실패 부검을 읽기 전용으로 연결`
>
> 권위: `DEVELOPMENT_DIAGNOSTIC_NO_OOS_NO_ADOPTION`
>
> 결론: **7개 G1 후보의 공통 실패를 Family·Fold·거래수·MDD·Exit로 요약했다. 상대 개선 신호가 있어도 Development 0/7을 뒤집지 않으며, 새 기준·재실행·채택 기능은 없다.**

---

## 1. Status Dashboard

```text
┌─────────────────────────────────────────────────────────────────┐
│ ANA-04 FAILURE AUTOPSY                                         │
├─────────────────────────┬───────────────────────────────────────┤
│ Candidates              │ 7                                    │
│ Families                │ 5                                    │
│ Folds                   │ 28 · observed 23 · unobserved 5      │
│ Paired Signal           │ 3/7                                  │
│ Development Pass        │ 0/7 · STOP                           │
│ Positive Profit Folds   │ 4/28                                 │
│ Trades                  │ 1,415 → 819 · -596 · -42.12%        │
│ Holdout                 │ SEALED_NOT_TOUCHED                   │
└─────────────────────────┴───────────────────────────────────────┘
```

---

## 2. 공통 실패 Tree

```text
Development STOP 7/7
│
├── 양수 Fold 부족 .............. 7/7
├── 결합 평균 손익 실패 ......... 6/7
├── 결합 총손익 실패 ............ 6/7
├── Fold 최소 거래수 실패 ....... 4/7
└── MDD 상한 실패 ............... 3/7

Fold 28
├── 지표 관측 ................... 23
├── 미관측 ...................... 5
├── 양수 손익 Fold .............. 4
├── 평균 손익 개선 Fold ......... 15
└── MDD 15% 초과 Fold ........... 4
```

평균 손익 개선 Fold 15개는 상대 변화다. 절대 양수 손익 Fold는 4개뿐이며 Development 통과 후보는 0개다.

---

## 3. Family 결과

| Family | 후보 | 거래 G0→G1 | 양수 Fold | G1 결합손익 | 최대 MDD | Paired | DEV |
|---|---:|---:|---:|---:|---:|---:|---:|
| ABSORPTION_REVERSAL | 2 | 140→117 | 1 | -58.13% | 28.20% | 1/2 | 0/2 |
| COMPRESSION_CONFIRMED_BREAKOUT | 1 | 470→412 | 0 | -35.23% | 13.72% | 1/1 | 0/1 |
| FAILED_BREAKOUT_RETURN | 1 | 372→15 | 2 | +0.46% | 5.84% | 0/1 | 0/1 |
| FLOW_PRICE_DIVERGENCE | 1 | 93→0 | 0 | **미관측** | **미관측** | 0/1 | 0/1 |
| OPENING_OVERREACTION_MEAN_REVERT | 2 | 340→275 | 1 | -71.66% | 22.64% | 1/2 | 0/2 |

FAILED_BREAKOUT_RETURN의 결합손익 +0.46%도 Fold 최소 거래수와 양수 Fold 기준을 충족하지 못해 DEV STOP이다. FLOW_PRICE_DIVERGENCE는 NO_TRADES이므로 손익/MDD를 0으로 합성하지 않는다.

---

## 4. Exit attribution

| Exit | G0→G1 | 거래 Δ | 손익 Δ 원 | 해석 경계 |
|---|---:|---:|---:|---|
| STOP_LOSS | 637→341 | -296 | +6,804,361 | 손실 감소 관측, 경제 성공 주장 아님 |
| TAKE_PROFIT | 299→180 | -119 | -3,467,769 | 익절 거래와 익절 손익 동반 감소 |
| TIME | 405→260 | -145 | +584,371 | 거래 감소 관측 |
| SESSION | 72→36 | -36 | +216,244 | 거래 감소 관측 |
| OTHER | 2→2 | 0 | -1,960 | 변화 미미 |

```text
손절 감소 + 익절 감소
          │
          └── 거래수가 줄었다는 사실
                    ≠
              전략이 개선됐다는 증거
```

---

## 5. 구현 구조

```text
GET /research-result/current
          │
          ▼
v4-research-failure-autopsy-model.mjs
  ├── failure count
  ├── Fold aggregate
  ├── Family aggregate
  ├── Exit aggregate
  └── candidate summary
          │
          ▼
v4-research-failure-autopsy.jsx
  ├── 공통 실패 카드
  ├── 실패 빈도 bar
  ├── Family table
  ├── Exit table
  └── 후보별 근거 버튼
          │
          ▼
UX-03 selected candidate + evidence details open
```

| 파일 | 역할 |
|---|---|
| `v4-research-failure-autopsy-model.mjs` | 순수 집계, 96 pure LOC |
| `v4-research-failure-autopsy.jsx` | 읽기 전용 Autopsy UI, 46 pure LOC |
| `v4-research-result.jsx` | 선택 후보와 상세 open 상태 연결 |
| `v4.css` | 산업형 밀도·반응형·내부 table scroll |
| `test_research_failure_autopsy.py` | 실제 봉인 수치·wiring·미관측·mobile overflow 계약 |

---

## 6. 검증 결과

| Gate | 결과 |
|---|---|
| 최초 model red | `ERR_MODULE_NOT_FOUND` 확인 |
| ANA-04 테스트 | **5 passed / 6.04s** |
| 기존 UX-04/UX-03/ANA-03 | **15 passed / 13.61s** |
| Ruff | PASS |
| basedpyright | 0 errors · 0 warnings |
| no-excuse | 0 violations |
| frontend typecheck | PASS |
| runtime JSX | 139 JSX / 592 graph files PASS |
| build | `app.js v=f155970e`, `v4.css v=b7249f41` |

전체 20개 결합 pytest는 이 환경에서 출력 없이 프로세스가 종료된 회차가 있어 성공으로 기록하지 않는다. 동일 테스트를 ANA-04 5개와 기존 15개로 독립 실행해 각각 종료 코드 0을 확인했다.

---

## 7. 인하우스 브라우저 QA

| 시나리오 | 관측 |
|---|---|
| 1280×720 | Mission→Autopsy→Raw Evidence 순서, 가로 넘침 없음 |
| 공통 실패 | bar 5개, 7/7·6/7·6/7·4/7·3/7 표시 |
| 상세 | Family 5행, Exit 5행, 후보 버튼 7개 |
| 미관측 | FLOW_PRICE_DIVERGENCE 손익/MDD `미관측` |
| 후보 deep link | Compression 버튼 → UX-03 Compression 근거 선택·상세 open |
| 620×900 초기 | KPI 1열, 페이지 가로 넘침 없음 |
| 620 상세 수정 전 | Family scroll container 660px로 clipping 위험 발견 |
| 620 상세 수정 후 | Family 556→660, Exit 536→660 내부 스크롤; 페이지 overflow 없음 |
| console | warn/error 0 |

---

## 8. 다음 단계

```text
[ANA-04 COMPLETE]
        │
        ▼
[UX-05 CURRENT STOP vs HISTORICAL HOF]
  ├── 현재 판정 최상위
  ├── 과거 HOF Historical watermark
  ├── 권위·검증일 표시
  └── 과거 양수를 현재 승격 근거로 사용 금지
```

새 연구 프로그램은 별도 사전등록 전까지 시작하지 않는다.
