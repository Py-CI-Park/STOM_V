# 조건식 자기개선 프로세스 재점수화 및 개선책 업데이트 (2026-06-17)

> 기준: 2026-06-15 보고서 이후 추가된 코드, 연구 문서, tmap evidence, 테스트를 다시 검토했다. 점수는 연구 프로세스 완성도 진단용이며, 실제 성공 지표는 여전히 **OOS/WF 통과 후보 수**다.

## 1. 한 줄 결론

| 항목 | 2026-06-15 | 2026-06-17 | 변화 |
|---|---:|---:|---:|
| 전체 완성도 | 56% | **68%** | **+12%p** |
| 전체 부족분 | 44% | **32%** | **-12%p** |
| 신규 후보 OOS 통과 수 | 0 | **0** | 0 |
| best train-gate 후보 | 없음 | **+13,928,386 / MDD 9.62** | 신규 |
| 프로세스 상태 | 부분 feedback 생성기 | **앵커 변이 hill-climb 폐루프 진입** | 크게 개선 |
| 최종 판단 | 검증기는 강하나 학습 루프 부족 | **학습/변이 루프는 크게 강화, OOS 증명은 아직 미완** | 다음은 OOS |

## 2. 가장 중요한 새 사실

| 새 사실 | 수치 | 의미 |
|---|---:|---|
| 챔피언 양성대조 | **4/4 gate=True** | 데이터 천장이나 게이트 문제가 아니라, 콜드 LLM 생성이 병목임이 확인됐다. |
| 챔피언 profit 범위 | **+9.55M ~ +10.97M** | 발굴 게이트로도 기존 우수 전략이 재현된다. |
| 앵커 변이 seed 런 | **19라운드 / 399 adopted** | LLM 없이도 검증 앵커 주변에서 통과 후보를 대량 생성했다. |
| 앵커 변이 best | **+13,928,386 / MDD 9.62** | train-gate 기준 최고 후보가 크게 개선됐다. |
| t2late 멀티스타트 best | **+10,582,342 / MDD 11.5** | 다른 봉우리도 존재하지만 seed 봉우리보다 낮다. |
| full stateful n=40 | **PROMISING 0** | 콜드/stateful LLM 생성은 아직 진짜 통과 후보를 못 냈다. |
| 신규 OOS proof | **0** | 앵커 변이 best도 OOS 전에는 최종 성공으로 볼 수 없다. |

## 3. 점수 재산정

| 평가축 | 6/15 | 6/17 | 변화 | 현재 부족분 | 판단 |
|---|---:|---:|---:|---:|---|
| 목적 정렬 | 85% | **90%** | +5 | 10% | OOS 기준과 병목 진단이 더 명확해졌다. |
| 데이터 캡처 | 78% | **84%** | +6 | 16% | CSV fallback, time-series 분석이 보강됐다. |
| 백테스트 게이트 | 82% | **88%** | +6 | 12% | 챔피언 4/4 양성대조로 게이트 신뢰가 올랐다. |
| Seed breadth | 45% | **58%** | +13 | 42% | 멀티스타트/앵커 변이가 생겼지만 coverage ledger는 아직 부족하다. |
| 생성 다양성 | 48% | **63%** | +15 | 37% | 콜드 LLM에서 앵커 변이로 방향 전환했다. |
| Buy-side 진단 | 58% | **70%** | +12 | 30% | feature_importance prefer feedback이 추가됐다. |
| Sell-side 진단 | 52% | **68%** | +16 | 32% | exit regret/false-break 포렌식이 추가됐다. |
| Feedback policy | 42% | **58%** | +16 | 42% | 토글/FDR/힌트는 강화됐지만 typed ledger는 아직 없다. |
| DB/evidence lineage | 55% | **63%** | +8 | 37% | jsonl 증거는 풍부해졌지만 summary drift가 있다. |
| Dashboard/runbook | 60% | **75%** | +15 | 25% | runbook, process flow, `/time_profit`, `/run_log`가 보강됐다. |
| OOS proof | 25% | **35%** | +10 | 65% | 양성대조는 좋지만 신규 후보 OOS 통과는 아직 0이다. |
| End-to-end autonomy | 38% | **68%** | +30 | 32% | P5/앵커 변이로 자율 반복성이 크게 개선됐다. |
| **평균** | **56%** | **68%** | **+12** | **32%** | 프로세스는 성숙했지만 OOS가 남은 핵심 병목이다. |

## 4. 무엇이 좋아졌나

| 좋아진 부분 | 개선 전 | 개선 후 | 효과 |
|---|---|---|---|
| 병목 진단 | 데이터 천장인지 생성기 문제인지 불명확 | 챔피언 4/4 통과로 생성기 병목 확정 | 연구 방향이 명확해짐 |
| 생성 방식 | 콜드 LLM 생성 중심 | 앵커 변이 hill-climb 추가 | train-gate 통과 후보 대량 생성 |
| 매수 feedback | segment avoid 중심 | feature_importance prefer 추가 | 어떤 B_*를 선호할지 더 구체화 |
| 매도 feedback | MFE/MAE 기초 분석 | exit regret/false-break 추가 | 청산 실패 원인 분리 강화 |
| mutation | 계획 수준 | `mutator.py`, `tmap_autopsy_loop.py`, `overnight_anchor_mutation.py` | 자동 변이 루프 가능 |
| dashboard/runbook | 분석은 있으나 실행 관리 약함 | time_profit/run_log/process_flow/runbook 보강 | 연구 재개와 상태 관리 개선 |

## 5. 아직 부족한 부분

| 순위 | 부족한 부분 | 현재 수치 | 왜 중요한가 | 개선책 |
|---:|---|---:|---|---|
| 1 | 신규 후보 OOS 통과 | **0개** | 진짜 일반화 증거가 없다. | +13.93M 앵커 champion을 frozen OOS로 검증 |
| 2 | summary drift | t2late summary best=null vs jsonl best +10.58M | 연구 관리 신뢰를 떨어뜨린다. | jsonl 기준 canonical summary 재생성 |
| 3 | typed feedback ledger | 미완 | 힌트가 action으로 추적되지 않는다. | action_id/source_metric/scope/outcome 스키마 추가 |
| 4 | multi-start 완료 | seed/t2late 일부 | 전역 최고봉 보장이 없다. | r2full, exit2를 한 번에 하나씩 추가 탐색 |
| 5 | OOS promotion workflow | 미완 | train-gate best가 승격/기각되지 않았다. | train-gate -> OOS -> promote/reject 문서화 |

## 6. 핵심 해석

| 질문 | 답 |
|---|---|
| 이제 데이터에 알파가 없다는 결론인가? | **아니다.** 챔피언 4/4가 발굴 게이트를 통과해 알파 실재가 확인됐다. |
| 그럼 왜 자동 생성은 실패했나? | **콜드 LLM 생성이 병목**이다. full stateful n=40도 PROMISING 0이다. |
| 앵커 변이는 성공인가? | **train-gate 기준으로는 강한 성공**이다. +13.93M/MDD 9.62까지 갔다. |
| 최종 성공인가? | **아직 아니다.** OOS 검증 전에는 과적합 가능성이 남는다. |
| 6/15 대비 가장 큰 진전은? | P4/P5와 앵커 변이로 end-to-end autonomy가 38% -> 68%로 상승했다. |
| 다음 핵심은? | OOS 검증이다. 이걸 통과해야 OOS proof가 35%에서 크게 오른다. |

## 7. 업데이트된 개발 우선순위

| Phase | 우선순위 | 작업 | 완료 기준 |
|---|---:|---|---|
| P0 | 1 | 앵커 champion OOS 검증 | `r8_4_strength_max=250` OOS pass/fail 기록 |
| P1 | 2 | evidence summary repair | `ovn_*_summary.json`이 jsonl best와 일치 |
| P2 | 3 | multi-start queue 완성 | seed, t2late, r2full, exit2 best 비교표 작성 |
| P3 | 4 | typed feedback/action ledger | buy/sell/mutation 힌트가 action record로 저장 |
| P4 | 5 | OOS promotion workflow | mutation -> train gate -> OOS -> promote/reject 자동 관리 |
| P5 | 6 | dashboard/runbook 패널 | champion/OOS/summary drift/next action 표시 |

## 8. 다음 `$start-work` 권장

| 추천 | 이유 |
|---|---|
| `$start-work condition-self-improvement-oos-validation-20260617` | 지금 가장 중요한 단계다. +13.93M train champion이 진짜인지 과적합인지 판별한다. |
| `$start-work condition-self-improvement-evidence-summary-repair-20260617` | OOS 전이라도 먼저 해야 할 관리 작업이다. t2late summary drift를 고쳐야 연구 기록 신뢰가 올라간다. |

## 9. 최종 판단

| 항목 | 판단 |
|---|---|
| 연구 관리 | 6/15보다 좋아졌다. runbook과 evidence가 크게 늘었다. 다만 summary drift가 생겨 관리 점수는 아직 63%다. |
| 자동 개선 프로세스 | 크게 발전했다. 단순 prompt feedback에서 앵커 변이 hill-climb까지 왔다. |
| 조건식 발굴 가능성 | 높아졌다. 데이터 천장이 아니라는 양성대조가 나왔다. |
| 최종 검증 상태 | 아직 미완. 신규 후보 OOS 통과 0개다. |
| 전체 결론 | **프로세스 완성도는 56% -> 68%로 상승. 이제 핵심은 더 개발하는 것이 아니라, 최고 train 후보를 OOS로 검증해 진짜 알파인지 판별하는 것이다.** |
