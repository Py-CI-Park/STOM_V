# 2025 Q4 방어, 선행 월규칙, half_exit2, 대시보드 기록 확인

작성일: 2026-06-18  
작업 ID: `q4-defense-prerule-halfexit-dashboard-20260618`  
범위: 연구/OOS/대시보드 기록 확인. `backtest.py`, V3K 게이트, 실거래 경로는 수정하지 않았다.

## 목적

이 작업의 목적은 이전 실험에서 발견된 2025년 4분기 손실 구간을 실제 공식 OOS로 다시 확인하고, 손실을 줄일 수 있는 방어 규칙이 사후 해석이 아니라 실전에 가까운 선행 규칙으로도 의미가 있는지 확인하는 것이다.

핵심 질문은 네 가지였다.

| 번호 | 질문 | 확인 방법 | 결과 |
|---:|---|---|---|
| 1 | 2025년 4분기 `r8_4 + r2full_mdd` 손실이 공식 OOS에서도 재현되는가 | Q4 전용 공식 OOS 3개 실행 | 재현됨. 조합 손익 `-833,963원` |
| 2 | `exit2_balance`를 절반 자본으로 추가하면 손실 완충이 되는가 | 공식 `exit2_balance` Q4 OOS를 0.5배 포트폴리오로 합산 | 손실을 `+320,050원` 완충하지만 단독 해결은 아님 |
| 3 | 월간 방어를 사후 제외가 아니라 전월 기준 선행 규칙으로 바꾸면 쓸 만한가 | 2022~2026 완료 OOS CSV 15개로 prior-only 규칙 시뮬레이션 | MDD는 일부 감소하지만 수익 희생이 커서 바로 적용은 부적절 |
| 4 | 이번 연구 기록을 진화 대시보드 연구 기록 카드에서 볼 수 있는가 | `/research_records`와 detail API를 TestClient로 호출 | 새 캠페인 1순위 노출, detail `available=true` |

## 공식 Q4 OOS 결과

Q4 설정 파일: `.omo/evidence/tmap-walkforward/oos-2025-q4-e32-config.json`  
기간: `2025-10-01`부터 `2025-12-31`까지  
엔진: 기존 2025 OOS와 같은 e32 warm-engine 설정

| 전략 | run_id | 손익 | DB MDD | 거래수 | Gate |
|---|---|---:|---:|---:|---|
| `r8_4` | `ovn_r8_oos_2025q4_20260618` | `-835,479원` | `35.60%` | 35 | 실패 |
| `r2full_mdd` | `ovn_r2full_mdd_oos_2025q4_20260618` | `+1,516원` | `17.17%` | 25 | 통과 |
| `exit2_balance` | `ovn_exit2_balance_oos_2025q4_20260618` | `+640,100원` | `16.43%` | 23 | 통과 |

판단: 2025년 4분기 손실의 대부분은 `r8_4`에서 발생했다. `r2full_mdd`는 거의 보합이고, `exit2_balance`는 같은 구간에서 양수라서 완충 역할은 가능하다.

## Q4 조합 성과

아래 수익률은 각 조합의 최대 배정 자본 기준이다. 예를 들어 2개 전략은 1,000만원, 3개 전략은 1,500만원, `half_exit2`는 1,250만원 기준이다.

| 조합 | 손익 | 수익률 | 연평균 환산 | 일별 실현 MDD | 거래수 | 해석 |
|---|---:|---:|---:|---:|---:|---|
| `r8_4` 단독 | `-835,479원` | `-16.71%` | `-57.50%` | `35.69%` | 35 | Q4 손실 원인 |
| `r2full_mdd` 단독 | `+1,516원` | `+0.03%` | `+0.14%` | `17.19%` | 25 | 보합 |
| `exit2_balance` 단독 | `+640,100원` | `+12.80%` | `+75.72%` | `9.60%` | 23 | Q4 방어 후보 |
| `r8_4 + r2full_mdd` | `-833,963원` | `-8.34%` | `-33.47%` | `26.48%` | 60 | 기존 스트레스 조합 |
| `r8_4 + exit2_balance` | `-195,379원` | `-1.95%` | `-8.82%` | `21.75%` | 58 | 손실 크게 축소 |
| `r2full_mdd + exit2_balance` | `+641,616원` | `+6.42%` | `+33.78%` | `12.52%` | 48 | Q4만 보면 가장 안정적 |
| `r8_4 + r2full_mdd + exit2_balance` | `-193,863원` | `-1.29%` | `-5.91%` | `20.24%` | 83 | full exit2는 손실 완충 |
| `r8_4 + r2full_mdd + half_exit2` | `-513,913원` | `-4.11%` | `-17.84%` | `22.73%` | 83 | 절반 추가는 완충이 약함 |

결론: Q4에만 한정하면 `exit2_balance`를 full로 붙였을 때 손실 감소 효과가 더 크다. 다만 전체 기간 자본 효율에서는 `half_exit2`가 과도한 자본 확대를 피하는 후보였으므로, 바로 폐기하지 말고 다음 검증에서 "언제 half, 언제 full, 언제 제외"를 판단해야 한다.

## 월간 선행 방어 규칙

이전 월간 방어 분석은 손실이 난 달을 사후에 줄이는 방식이라 실전에 바로 쓸 수 없었다. 이번에는 전월 또는 전전월까지의 결과만 보고 다음 달 비중을 조절하는 규칙으로 다시 계산했다.

| 규칙 | 뜻 |
|---|---|
| `baseline_no_prior_defense` | 방어 없음 |
| `strategy_half_after_prior_month_loss` | 전략별 전월 손실이면 다음 달 그 전략 0.5배 |
| `strategy_skip_after_prior_month_loss` | 전략별 전월 손실이면 다음 달 그 전략 제외 |
| `strategy_skip_after_prior_month_loss_500k` | 전략별 전월 손실이 `-500,000원` 이하이면 다음 달 제외 |
| `strategy_half_after_two_month_cum_loss` | 전략별 최근 2개월 합산 손실이면 다음 달 0.5배 |
| `combo_half_after_prior_month_loss` | 조합 전체 전월 손실이면 다음 달 조합 전체 0.5배 |

| 조합 | 기준 수익 | 기준 MDD | 최고 수익 규칙 | 최고 수익 | 최고 수익 MDD | 최저 MDD 규칙 | 최저 MDD | 판단 |
|---|---:|---:|---|---:|---:|---|---:|---|
| `r8_4 + r2full_mdd` | `30,605,706원` | `12.84%` | 기준 유지 | `30,605,706원` | `12.84%` | 전월 손실 전략 제외 | `11.84%` | MDD 1.0%p 개선 대신 수익 816만원 감소 |
| `r8_4 + exit2_balance` | `31,505,991원` | `9.39%` | 전월 `-50만원` 이하 전략 제외 | `31,702,635원` | `9.27%` | 동일 | `9.27%` | 가장 실용적인 후보 |
| `r8_4 + r2full_mdd + exit2_balance` | `45,217,645원` | `10.94%` | 전월 `-50만원` 이하 전략 제외 | `45,414,289원` | `10.94%` | 전월 손실 전략 제외 | `10.22%` | 수익 개선 규칙과 MDD 개선 규칙이 다름 |
| `r8_4 + r2full_mdd + half_exit2` | `37,911,676원` | `11.70%` | 기준 유지 | `37,911,676원` | `11.70%` | 전월 손실 전략 제외 | `10.86%` | 방어하면 수익 손실이 큼 |

판단: 지금 단계에서 월간 방어 규칙을 바로 채택하면 안 된다. `r8_4 + exit2_balance`의 `전월 -50만원 이하 전략 제외`만 수익과 MDD를 동시에 조금 개선했다. 나머지는 MDD 개선 폭보다 수익 희생이 크다.

## 대시보드 기록 확인

이번 연구를 대시보드 연구 기록 카드에서 보이도록 다음 캠페인 파일을 추가했다.

| 파일 | 역할 |
|---|---|
| `.omo/evidence/tmap-walkforward/q4-defense-prerule-halfexit-dashboard-20260618_summary.json` | Research Records 카드 요약 |
| `.omo/evidence/tmap-walkforward/q4-defense-prerule-halfexit-dashboard-20260618.jsonl` | Q4 조합 후보 행 |
| `.omo/evidence/tmap-walkforward/q4-defense-prerule-halfexit-dashboard-20260618_log.txt` | 실행 로그 |
| `.omo/evidence/tmap-walkforward/dashboard-research-records-check-20260618.json` | API 검증 증거 |

검증 결과:

| 항목 | 결과 |
|---|---|
| `/research_records` 상태 | 200 |
| 새 캠페인 노출 | true |
| 새 캠페인 순위 | 1 |
| detail API | `available=true` |
| 캠페인 수 | 15 |

주의: `ResearchRecordsPanel`은 캠페인형 evidence를 보여주는 표면이다. 마크다운 연구 일지 전체를 보여주는 표면은 별도 `research_docs` 계열인데, 현재는 allowlist 구조라 모든 최신 update_log가 자동 노출되지는 않는다.

## 결론

| 결론 | 채택 여부 | 이유 |
|---|---|---|
| 2025 Q4 손실은 실제 공식 OOS에서도 재현됨 | 확정 | Q4 공식 OOS 3개 완료 |
| Q4 손실의 핵심 원인은 `r8_4` | 확정 | `r8_4` 단독 `-835,479원`, `r2full_mdd` 보합 |
| `exit2_balance`는 Q4 방어 후보 | 후보 유지 | Q4 단독 `+640,100원`, 조합 손실 완충 |
| `half_exit2`는 전체기간 확장 후보이나 Q4 단독 방어로는 약함 | 후보 유지, 추가 검증 필요 | Q4 손실을 줄이지만 `full exit2`보다 완충 약함 |
| 월간 선행 방어 전체 도입 | 보류 | 다수 규칙에서 수익 희생이 큼 |
| `r8_4 + exit2_balance`에 대한 `전월 -50만원 이하 전략 제외` | 다음 실험 후보 | 수익 `+196,644원`, MDD `-0.12%p` 동시 개선 |

## 다음 작업

| 우선순위 | 다음 실험 | 목적 | 예상 소요 |
|---:|---|---|---:|
| 1 | `r8_4 + exit2_balance` 전월 `-50만원` 제외 규칙을 연도별/반기별로 분해 검증 | 개선이 특정 기간 착시인지 확인 | 30~45분 |
| 2 | `exit2_balance` full/half 동적 배정 규칙 실험 | Q4 방어력과 전체 자본 효율 균형 확인 | 45~60분 |
| 3 | `r8_4` Q4 손실일의 요일/시간/종목군 원인 분해 | `r8_4` 자체 필터를 만들 수 있는지 확인 | 45~75분 |
| 4 | 마크다운 연구 일지 자동 노출 개선 설계 | Research Records와 Research Docs의 역할 혼선을 줄임 | 30~45분 |

## 산출물

- `.omo/evidence/tmap-walkforward/oos-2025-q4-e32-config.json`
- `.omo/evidence/tmap-walkforward/q4-oos-baseline-coverage-20260618.json`
- `.omo/evidence/tmap-walkforward/q4-official-oos-run-records-20260618.json`
- `.omo/evidence/tmap-walkforward/q4-defense-official-oos-20260618.json`
- `.omo/evidence/tmap-walkforward/half-exit2-official-oos-20260618.json`
- `.omo/evidence/tmap-walkforward/monthly-prerule-sim-r8-exit2-r2full-20260618.json`
- `.omo/evidence/tmap-walkforward/q4-defense-prerule-halfexit-dashboard-20260618_summary.json`
- `.omo/evidence/tmap-walkforward/q4-defense-prerule-halfexit-dashboard-20260618.jsonl`
- `.omo/evidence/tmap-walkforward/q4-defense-prerule-halfexit-dashboard-20260618_log.txt`
- `.omo/evidence/tmap-walkforward/dashboard-research-records-check-20260618.json`
