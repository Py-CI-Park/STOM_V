# 2026-06-18 조건식 연구 전체 재검토

## 1. 한 줄 결론

2026-06-18 작업으로 **백테스트/OOS/포트폴리오/대시보드 연구 관리**는 크게 좋아졌다. 다만 **AI가 넓은 조건식을 cold 상태에서 직접 생성해 좋은 조건식으로 만드는 능력**은 아직 약하다. 현재는 좋은 seed 또는 검증 후보 주변을 좁혀가며 공식 OOS로 확인하는 방식이 가장 현실적인 경로다.

## 2. 최종 점수

| 평가 범위 | 현재 점수 | 부족분 | 전날 대비 | 판단 |
|---|---:|---:|---:|---|
| 전체 연구 프로세스 | **72점** | **28%** | +6점 | OOS와 대시보드 기록이 추가되어 70점대 진입 |
| 조건식 생성 AI 자체 | **67점** | **33%** | +1점 | 생성 폭은 넓지만 cold 생성 성공률은 여전히 낮음 |
| 검증/OOS/포트폴리오 연구 | **76점** | **24%** | +20점 이상 | 2022~2026 OOS와 Q4 stress 검증으로 크게 개선 |
| 최종 승격 준비도 | **56점** | **44%** | +21점 | 다음 robust 후보 공식 OOS 전이라 아직 보류 |

해석: 6월 17일의 66점 평가는 주로 "넓은 생성이 실제 OOS 성과로 연결되는가"에 대한 평가였다. 6월 18일에는 OOS와 포트폴리오 검증이 늘었으므로 전체 프로세스는 72점으로 올릴 수 있다. 하지만 생성기 자체는 아직 60점대다.

## 3. 좋아진 부분

| 항목 | 이전 상태 | 현재 상태 | 개선 판단 |
|---|---|---|---|
| OOS 증거 | 신규 OOS PROMISING 0, train-gate 중심 | 2022/2026 OOS 4개 통과, 2023~2025 OOS 9개 통과 | 크게 개선 |
| Q4 손실 원인 | 2025 Q4 약화만 추정 | 공식 Q4 OOS에서 `r8_4` 손실 확정 | 크게 개선 |
| 방어 후보 | seed/anchor train 성과 중심 | `exit2_balance`, `r2full_mdd`, 저시총 제외 필터 후보로 좁힘 | 개선 |
| 포트폴리오 판단 | 단일 후보 중심 | `r8_4 + exit2`, `r8_4 + r2full`, 3전략 조합 비교 | 개선 |
| 연구 관리 | evidence는 많지만 찾기 어려움 | Research Records API/패널, GUI parity 패널, 캠페인 노출 확인 | 크게 개선 |

## 4. 핵심 수치

| 구분 | 수치 | 의미 |
|---|---:|---|
| 조건식 템플릿 | 149개 | tick 111개, min 38개 |
| 기본 렌더/검증 통과 | 149/149 | STOM 문법 생성 기반은 안정적 |
| AND 포함 | 149/149 | 다중 필터 조건식은 충분히 생성 |
| literal OR | 38/149 | OR는 아직 약함 |
| if/elif 분기 | 121/149 | OR보다는 분기형 대체 경로가 많음 |
| full_stateful_n40 PROMISING | 0/40 | cold/stateful AI 생성은 아직 약함 |
| anchor mutation 채택 | 399개 | seed 주변 개선은 강함 |
| anchor best | +13,928,386원 / MDD 9.62% | train-gate 기준 강한 후보 |
| 2023~2025 OOS | 9/9 통과 | 고정 후보 검증력 개선 |
| 2022/2026 OOS | 4/4 통과 | 기간 확장 검증 개선 |
| Q4 공식 OOS | 2/3 통과 | `r8_4`만 실패 |
| 대시보드 캠페인 노출 | rank 1, detail 200 | 연구 기록 가시성 개선 |

## 5. OOS와 포트폴리오 판단

| 후보/조합 | 전체 수익 | 주요 MDD | 판단 |
|---|---:|---:|---|
| `r8_4` 단독 | 16,894,052원 | 최대 연도 MDD 25.78% | 자본효율은 좋지만 Q4 손실 원인 |
| `r8_4 + exit2` | 31,505,991원 | 최대 연도 MDD 24.43% | 전체 총수익 2전략 우위 |
| `r8_4 + r2full` | 30,605,706원 | 최대 연도 MDD 21.64% | 최근 2025~2026 방어 우위 |
| 3전략 조합 | 45,217,645원 | 최대 연도 MDD 21.93% | 총액은 최대, 자본효율은 2전략보다 약함 |

| 2025 Q4 공식 OOS | 손익 | MDD | Gate | 해석 |
|---|---:|---:|---|---|
| `r8_4` | -835,479원 | 35.60% | 실패 | Q4 손실의 핵심 원인 |
| `r2full_mdd` | +1,516원 | 17.17% | 통과 | 거의 보합 방어 |
| `exit2_balance` | +640,100원 | 16.43% | 통과 | Q4 방어 후보 |

## 6. 다음 공식 OOS 후보

| 순위 | 쉬운 이름 | 내부 이름 | 현재 근거 | 주의 |
|---:|---|---|---|---|
| 1 | 저시총 제외 방어 조합 | `r8_exclude_cap_lt_1500__exit2_skip_after_prior_exit2_loss_500k_else_full` | 점수 90.5884, 전체 +39,402,438원, MDD 7.68%, Q4 +952,502원 | 아직 공식 OOS 전 |
| 2 | 11월 제외 비교용 | `r8_exclude_month_11__exit2_skip_after_prior_exit2_loss_500k_else_full` | 점수 93.5087, 전체 +46,745,487원 | 달력 월 제외라 과최적화 위험 큼 |
| 3 | exit2 월별 ON/OFF | `exit2_full_after_prior_r8r2_loss_else_off` | Q4 방어 성과 명확 | 조건식이 아니라 포트폴리오 규칙 |
| 4 | r8 저시총 제외 단독 | `r8_exclude_cap_lt_1500` | r8 Q4 손실 원인과 연결 | 단독 공식 OOS 필요 |

결론: 다음 작업은 조건식 대량 생성을 다시 하는 것이 아니라, 1순위 robust 후보를 공식 OOS로 실행하는 것이 맞다. 11월 제외 후보는 점수는 높지만 채택 후보가 아니라 shadow 비교용이다.

## 7. 아직 부족한 부분

| 우선 | 부족한 부분 | 부족분 | 왜 중요한가 | 개선책 |
|---:|---|---:|---|---|
| 1 | cold AI 생성 성능 | 62% | 넓게 만들지만 좋은 후보를 직접 못 찾음 | AI는 seed/template 제안기로 두고 seed-bank mutation 우선 |
| 2 | 최종 승격 준비 | 44% | robust 후보 공식 OOS가 아직 없음 | deferred official OOS plan 실행 |
| 3 | 전체 시간대 일반화 | 42% | tick이 장초반 중심 | open/midday/afternoon/close bucket별 quota |
| 4 | AND/OR branch 기여도 | 32% | OR/분기가 실제 수익에 도움인지 불명확 | branch_id별 거래수/수익/MDD/OOS lift 기록 |
| 5 | human-case corpus | 32% | 사람식 조건식 사례가 구조화되지 않음 | setup taxonomy, seed, backtest verdict 연결 |
| 6 | evidence lineage | 30% | artifact가 많고 summary drift 위험 있음 | summary/jsonl consistency test와 campaign registry |
| 7 | 대시보드 연구 문서 노출 | 18% | Research Records는 보이나 최신 update_log 자동 노출 미완 | recent update_log indexing 구현 |
| 8 | 전체 unit green | 잔여 7개 실패 | 연구 변경 외 기존 계약 실패가 남음 | `backtest.py` 계약 안정화 별도 plan |

## 8. 지금 프로세스의 의미

| 질문 | 현재 답 |
|---|---|
| AI가 넓은 조건식을 생성하나? | 예. 149개 템플릿과 다양한 시간/시총/거래량/체결강도 조건이 있다. |
| AI가 사람처럼 AND/OR를 섞나? | 부분적으로 예. AND는 강하지만 OR는 아직 분기 중심이고 기여도 측정이 부족하다. |
| 나쁜 조건식이 좋은 조건식으로 스스로 개선되나? | seed 주변에서는 가능하다. cold 생성에서 바로 좋은 후보를 찾는 것은 아직 약하다. |
| 백테스트 결과를 다음 연구에 반영하나? | 예. Q4 손실 원인, 저시총 제외, exit2 방어, 월별 선행 규칙까지 반영됐다. |
| 최종 실전 후보인가? | 아직 아니다. 공식 OOS와 승격 라벨이 더 필요하다. |
| 연구 관리는 잘되고 있나? | 전보다 좋아졌다. 대시보드 Research Records까지 연결됐지만 최신 문서 자동 노출과 lineage 정리가 남았다. |

## 9. 다음 작업

| 우선 | 명령/계획 | 목적 |
|---:|---|---|
| 1 | `$start-work .omo/plans/post-20260618-official-oos-dashboard-cleanup.md` | robust 후보 공식 OOS와 shadow 비교 실행 |
| 2 | `condition-research-evidence-lineage-cleanup-20260618` | summary/jsonl drift 방지, campaign registry 정리 |
| 3 | `condition-generation-branch-attribution-20260618` | AND/OR/분기별 실제 수익 기여도 측정 |
| 4 | `condition-generation-human-case-corpus-20260618` | 사람식 조건식 사례를 구조화하고 seed bank로 연결 |
| 5 | `backtest-contract-stabilization-20260618` | 연구와 별도로 전체 unit 잔여 7개 실패 정리 |

## 10. 최종 판단

| 항목 | 판단 |
|---|---|
| 현재 완성도 | **72/100** |
| 가장 강한 부분 | 공식 OOS 확대, Q4 손실 원인 분해, 포트폴리오 비교, 대시보드 연구 기록 |
| 가장 약한 부분 | cold AI 생성, 최종 robust 후보 공식 OOS, branch attribution |
| 개발 방향 | 대량 생성보다 seed bank + 공식 OOS + branch 기여도 추적 |
| 한 줄 결론 | **좋은 조건식을 찾는 연구 시스템은 70점대에 들어왔지만, AI 생성기가 스스로 좋은 조건식을 만드는 단계는 아직 60점대다.** |
