# 2026-06-18 조건식 연구 현황 재검토 요약

## 목적

이 문서는 `docs/update_log/2026-06-18_condition_research_current_state_rereview.md`의 장기 연구 참조용 요약이다. 실행 일지는 `docs/update_log/`에 두고, 이후 조건식 연구 기준표로 반복 참조할 내용은 이 `docs/research/condition_research/` 문서에 둔다.

## 최종 점수

| 평가 범위 | 현재 점수 | 부족분 | 판단 |
|---|---:|---:|---|
| 전체 연구 프로세스 | 72점 | 28% | OOS, 포트폴리오, 대시보드 연구 기록이 보강되어 70점대 진입 |
| 조건식 생성 AI 자체 | 67점 | 33% | 넓은 생성은 가능하지만 cold AI 생성 성공률은 아직 낮음 |
| 검증/OOS/포트폴리오 연구 | 76점 | 24% | 2022~2026 OOS와 Q4 stress 검증으로 크게 개선 |
| 최종 승격 준비도 | 56점 | 44% | robust 후보 공식 OOS 전이라 아직 보류 |

## 핵심 판단

| 질문 | 답 |
|---|---|
| AI가 넓은 조건식을 만드는가 | 예. 149개 템플릿, tick 111개, min 38개, AND 149/149 구조가 있다. |
| AI가 cold 상태에서 좋은 조건식을 직접 찾는가 | 아직 약하다. full_stateful_n40 기준 PROMISING 0/40이다. |
| 지금 가장 강한 개선 루프는 무엇인가 | 검증된 seed/anchor 주변 mutation과 공식 OOS 검증이다. |
| OOS 증거는 좋아졌는가 | 좋아졌다. 2022/2026 OOS 4/4 통과, 2023~2025 OOS 9/9 통과가 추가됐다. |
| 최종 후보로 승격 가능한가 | 아직 아니다. 저시총 제외 robust 후보의 공식 OOS가 남아 있다. |

## 현재 기준 수치

| 항목 | 값 |
|---|---:|
| 템플릿 수 | 149 |
| 기본 렌더/검증 통과 | 149/149 |
| AND 포함 | 149/149 |
| literal OR | 38/149 |
| if/elif branch | 121/149 |
| anchor mutation 채택 | 399 |
| anchor best | +13,928,386원 / MDD 9.62% |
| 2025 Q4 `r8_4` | -835,479원 / MDD 35.60% / Gate 실패 |
| 2025 Q4 `exit2_balance` | +640,100원 / MDD 16.43% / Gate 통과 |
| 2025 Q4 `r2full_mdd` | +1,516원 / MDD 17.17% / Gate 통과 |

## 다음 공식 OOS 우선순위

| 우선 | 쉬운 이름 | 내부 후보 | 목적 |
|---:|---|---|---|
| 1 | 저시총 제외 방어 조합 | `r8_exclude_cap_lt_1500__exit2_skip_after_prior_exit2_loss_500k_else_full` | 과최적화 위험이 낮은 robust 후보 공식 OOS |
| 2 | 11월 제외 비교용 | `r8_exclude_month_11__exit2_skip_after_prior_exit2_loss_500k_else_full` | raw score 1위지만 달력 과최적화 위험이 있어 shadow 비교 |
| 3 | exit2 월별 ON/OFF | `exit2_full_after_prior_r8r2_loss_else_off` | 조건식 변경 없는 포트폴리오 규칙 검증 |
| 4 | r8 저시총 제외 단독 | `r8_exclude_cap_lt_1500` | r8 손실 원인 필터 단독 검증 |

## 남은 부족분

| 우선 | 부족한 부분 | 부족분 | 개선 방향 |
|---:|---|---:|---|
| 1 | cold AI 생성 성능 | 62% | AI는 seed/template 제안기로 두고 seed-bank mutation 우선 |
| 2 | 최종 승격 준비 | 44% | robust 후보 공식 OOS 실행 |
| 3 | 전체 시간대 일반화 | 42% | open/midday/afternoon/close bucket quota |
| 4 | AND/OR branch 기여도 | 32% | branch_id별 거래수, 수익, MDD, OOS lift 기록 |
| 5 | human-case corpus | 32% | 사람식 setup taxonomy와 seed bank 연결 |
| 6 | evidence lineage | 30% | summary/jsonl consistency test와 campaign registry |

## 참조 위치

| 구분 | 위치 |
|---|---|
| 상세 실행 일지 | `docs/update_log/2026-06-18_condition_research_current_state_rereview.md` |
| 점수 JSON | `.omo/evidence/condition-research-current-state-rereview-20260618/current_state_score_matrix.json` |
| source inventory | `.omo/evidence/condition-research-current-state-rereview-20260618/source_inventory.md` |
| 검증 기록 | `.omo/evidence/condition-research-current-state-rereview-20260618/verification.md` |
| 다음 실행 계획 | `.omo/plans/post-20260618-official-oos-dashboard-cleanup.md` |

## 결론

조건식을 찾는 전체 연구 시스템은 70점대에 들어왔다. 하지만 AI 생성기가 스스로 좋은 조건식을 만드는 단계는 아직 60점대다. 다음 개발은 대량 생성보다 `seed bank + 공식 OOS + branch attribution + evidence lineage`에 집중해야 한다.
