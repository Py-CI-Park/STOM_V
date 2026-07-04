# 조건식 생성 범위/AND-OR 다양성 재평가 (2026-06-17)

## 1. 최종 점수

| 항목 | 점수 | 부족분 | 판단 |
|---|---:|---:|---|
| 전체 자기개선 프로세스 기존 점수 | 68점 | 32% | 2026-06-17 전체 프로세스 기준 |
| 이번 집중 평가: 조건식 생성 범위/AND-OR/사람식 사례 | **66점** | **34%** | 구조는 넓지만 OOS 성과 연결이 부족 |
| 구조적 생성 폭 | 79점 | 21% | 템플릿, 시간/시총, AND/분기 구조는 많이 확보 |
| 성과 증명 | 52점 | 48% | cold/stateful broad generation은 아직 OOS 후보 0 |
| 좋은 조건식 주변 개선 능력 | 82점 | 18% | anchor mutation은 train-gate 기준 강함 |
| OOS/최종 검증 | **35점** | **65%** | 가장 큰 병목 |

**결론:** AI가 넓은 범위의 조건식을 만들 장치는 상당히 생겼다. 하지만 "넓게 만든 조건식이 스스로 좋은 조건식으로 진화해 OOS까지 통과한다"는 증거는 아직 부족하다. 현재 가장 강한 경로는 **cold LLM 생성**이 아니라 **검증된 seed/anchor 주변을 변이하고 백테스트 gate로 채택하는 방식**이다.

## 2. 사용자가 질문한 핵심 항목별 답변

| 질문 | 현재 답변 | 근거 수치 | 평가 |
|---|---|---:|---|
| AI가 넓은 범위 조건식을 생성하나요? | 예, 구조적으로는 넓다 | 템플릿 149개, tick 111/min 38, 기본 렌더 검증 149/149 | 좋음 |
| 여러 범위/time/cap/수급을 섞나요? | 예 | time_window 100%, market_cap 100%, liquidity 75.2%, volume_surge 68.5% | 좋음 |
| AND 조건을 충분히 섞나요? | 예 | 149/149 템플릿이 AND 포함, 평균 AND 17.07개 | 강함 |
| OR 조건도 섞나요? | 부분적으로 예 | literal OR 38/149, `if/elif` branch 121/149 | 중간 |
| 사람이 시도했던 여러 사례처럼 만드나요? | 일부 반영됨 | 5분 bucket, 시총 band, few-shot, human reference 계획 존재 | 보완 필요 |
| 백테스트 결과를 보고 다음 조건식을 개선하나요? | 일부 가능 | stateful feedback, autopsy, feature hint, mutation loop 존재 | 중간 이상 |
| 나쁜 조건식에서 좋은 조건식으로 스스로 개선되나요? | anchor 주변은 가능, cold 생성은 약함 | ovn_anchor +13.93M, full_stateful_n40 PROMISING 0/40 | 반반 |
| 전체 시간을 모두 고려하나요? | min은 가능성이 있고 tick은 제한적 | min full-session toggle 존재, tick은 09:00~09:30 중심 | 부족 |
| 최종 성공이라고 볼 수 있나요? | 아직 아님 | 신규 OOS PROMISING 0 | 보류 |

## 3. 조건식 생성 폭 정량 수치

| 지표 | 수치 | 의미 |
|---|---:|---|
| 전체 template 수 | 149개 | 생성 구조의 후보 풀이 커졌다 |
| tick template | 111개 | tick 중심 연구가 강함 |
| min template | 38개 | min도 있으나 tick보다 적음 |
| 기본 렌더/검증 통과 | 149/149, 100% | 템플릿 자체는 실행 가능한 형태 |
| 평균 파라미터 수 | 33.98개 | 조정 가능한 범위가 넓음 |
| 중앙 파라미터 수 | 37개 | 대부분 단순 seed보다 넓은 탐색 공간 |
| 최대 파라미터 수 | 53개 | 일부는 매우 복잡 |
| AND 포함 | 149/149, 100% | 필터 결합은 충분 |
| literal OR 포함 | 38/149, 25.5% | 직접 OR는 많지 않음 |
| `if/elif` branch 포함 | 121/149, 81.2% | 실제 대체 경로 OR는 분기 구조가 담당 |
| 평균 `elif` 수 | 6.65개 | 다중 구간/분기 구조가 흔함 |
| 5개 이상 필터 범주 | 133/149, 89.3% | 사람식 복합 게이트에 가까움 |
| 시간창 no-op | 0/149 | 의미 없는 전체시간 조건은 없음 |

## 4. 필터 범주별 커버리지

| 필터 범주 | 포함률 | 평가 |
|---|---:|---|
| 시간창 | 100.0% | 강함 |
| 시총 | 100.0% | 강함 |
| 등락/변화율 | 96.6% | 강함 |
| 가격 밴드 | 94.6% | 강함 |
| 유동성/거래대금 | 75.2% | 양호 |
| 거래대금 급증/각도 | 68.5% | 양호 |
| 체결강도 | 67.8% | 양호 |
| 회전율/전일비 | 59.1% | 보통 |
| 호가/잔량 | **22.1%** | 약함 |

**해석:** 현재 조건식은 시간, 시총, 등락률, 가격, 거래대금에는 강하다. 사람이 자주 보는 호가벽, 매수잔량, 매도잔량, 매도벽 소멸 같은 orderbook 계열은 아직 약하다.

## 5. 백테스트 결과와 연결

| 실험 | 결과 | 의미 |
|---|---:|---|
| random broad generation n=8 | PROMISING 0/8 | 넓게만 뿌리면 성과 없음 |
| stateful broad generation n=8 | smoke-pass 3/8, PROMISING 0/8 | 피드백은 도움되지만 OOS 후보까지 못 감 |
| full stateful n=40 | PROMISING 0/40 | cold/stateful LLM 생성은 아직 주력 우승 경로 아님 |
| multiband escalation n=40 | smoke-pass 1/40, PROMISING 0 | branch/multiband도 검증에서 대부분 탈락 |
| champion positive control | 4/4 gate=True | 데이터/gate 문제보다 생성기가 병목 |
| anchor mutation | adopted 399, best +13,928,386 / MDD 9.62 | 검증 seed 주변 변이는 강함 |
| t2late mutation | jsonl 기준 best +10,582,342 / MDD 11.5 | 다른 seed basin도 가능 |
| 신규 OOS 통과 | 0 | 최종 성공은 아직 아님 |

## 6. 점수표

| 평가축 | 점수 | 부족분 | 이유 | 개선책 |
|---|---:|---:|---|---|
| 템플릿 풀 넓이 | 82 | 18 | 149개, tick/min, 100% 렌더 검증 | family registry로 중복/쏠림 관리 |
| 시간/시총 범위 | 78 | 22 | time/cap 100%, no-op 0 | bucket별 train/OOS 카드 |
| AND 필터 | 84 | 16 | 평균 AND 17.07, 5+ 범주 89.3% | 0거래 시 자동 완화 |
| OR/분기 다양성 | 66 | 34 | `if/elif` 81.2%, literal OR 25.5% | branch별 P/L/OOS lift 측정 |
| 사람식 사례 반영 | 62 | 38 | 5분 bucket, 시총 band, few-shot 계획 | human reference 17개 corpus화 |
| 백테스트 피드백 반영 | 70 | 30 | autopsy/feature hint/mutation 존재 | action ledger 구축 |
| cold LLM 생성 효과 | 38 | 62 | full n=40 PROMISING 0 | cold 생성은 seed 제안기로 격하 |
| anchor 변이 개선 | 82 | 18 | train-gate +13.93M | OOS queue 연결 |
| OOS 증명 | 35 | 65 | 신규 OOS 후보 0 | frozen OOS 검증 실행 |
| evidence 관리 | 61 | 39 | jsonl 풍부하나 summary drift | canonical summary 재생성 |
| 전체 시간 일반화 | 52 | 48 | min full-session은 있으나 tick은 09:00~09:30 중심 | min 장중 bucket registry |
| 안전한 연구 거버넌스 | 78 | 22 | research/claim 분리 | 결과 카드 상태 라벨 강화 |
| **평균** | **66** | **34** | 구조는 강하고 성과 검증은 약함 | OOS와 lineage가 다음 핵심 |

## 7. 왜 seed가 중요한가

| 비교 | 넓은 cold generation | 검증 seed/anchor mutation |
|---|---:|---:|
| 탐색 폭 | 넓음 | seed 주변으로 제한 |
| 좋은 후보 발견률 | 낮음 | 높음 |
| 현재 PROMISING | 0 | OOS 전 train-gate 후보 존재 |
| best 수익 | 없음 | +13,928,386 |
| 장점 | 새로운 구조 발견 가능 | 검증된 구조 보존 |
| 약점 | 대부분 no-go | 국소 최적/과적합 위험 |
| 현재 역할 | 보조 탐색/아이디어 생성 | 주력 개선 경로 |

**판단:** 사용자의 생각처럼 seed는 매우 중요하다. 다만 seed 하나만 중요한 것이 아니라, **좋은 seed 여러 개를 준비하고 각 seed 주변을 넓게 변이하는 multi-start 구조**가 필요하다.

## 8. 지금 부족한 것

| 우선순위 | 부족한 부분 | 부족분 | 왜 문제인가 | 개선 방향 |
|---:|---|---:|---|---|
| 1 | OOS 증명 | 65% | train-gate 수익이 과적합일 수 있음 | +13.93M 후보 frozen OOS 검증 |
| 2 | cold LLM 생성 성과 | 62% | 넓게 생성해도 좋은 후보가 안 나옴 | LLM은 template/seed 제안, mutation은 검증 anchor 중심 |
| 3 | 전체 장중 시간 일반화 | 48% | tick은 09:00~09:30 중심 | min full-day bucket별 family 분리 |
| 4 | human reference corpus | 38% | 사람식 사례가 아직 숫자/구조로 고정되지 않음 | 17개 reference taxonomy + benchmark |
| 5 | summary drift | 39% | 연구 관리 신뢰도 저하 | jsonl 기준 summary 재생성 |
| 6 | branch 기여도 | 34% | OR/분기가 손실을 늘리는지 알 수 없음 | branch_id별 P/L/OOS lift |
| 7 | feedback action 추적 | 30% | 어떤 개선이 효과 있었는지 모호 | action_id 기반 before/after ledger |

## 9. 개발 준비 로드맵

| 단계 | 작업 | 목적 | 완료 기준 |
|---:|---|---|---|
| P0 | anchor best OOS 검증 | train-gate 후보가 진짜인지 확인 | OOS pass/fail 카드 |
| P1 | evidence summary repair | 연구 관리 신뢰도 회복 | `ovn_t2late_summary.json`과 jsonl 일치 |
| P2 | human reference corpus | 사람식 사례를 AI 입력 자산화 | reference 17개 taxonomy/metrics |
| P3 | branch attribution | AND/OR/분기 기여도 측정 | branch별 trade/profit/MDD/OOS |
| P4 | feedback action ledger | 나쁜 조건식 개선 과정을 추적 | action별 before/after 성과 |
| P5 | multi-start seed queue | seed 하나 의존 탈피 | seed/t2late/r2full/exit2 비교 |
| P6 | time-bucket quota | 전체 시간대 균형 연구 | bucket별 후보수/생존율/OOS |

## 10. 다음 권장 `$start-work`

| 명령 | 이유 |
|---|---|
| `$start-work condition-generation-oos-validation-20260617` | 가장 중요한 부족분인 OOS 65%를 줄인다. +13.93M train 후보부터 검증한다. |
| `$start-work condition-generation-evidence-summary-repair-20260617` | t2late summary drift를 먼저 고쳐 연구 기록 신뢰도를 복구한다. |
| `$start-work condition-generation-human-reference-corpus-20260617` | 사람이 시도했던 사례를 AI가 반복 활용할 수 있는 구조화 자료로 만든다. |

## 11. 최종 판단

| 항목 | 판단 |
|---|---|
| 넓은 범위 생성 | 가능해졌다. 149개 템플릿과 time/cap/AND 구조가 있다. |
| AND/OR 혼합 | AND는 강하고, OR는 literal OR보다 `if/elif` branch 중심이다. |
| 사람식 사례 | 방향은 반영됐지만 corpus/benchmark가 부족하다. |
| 백테스트 분석 반영 | stateful feedback과 anchor mutation으로 일부 반영된다. |
| 나쁜 조건식 개선 | 검증 seed 주변에서는 가능성이 높다. cold LLM 단독은 아직 약하다. |
| 전체 시간 고려 | min full-session 방향은 있으나 tick 전체시간 일반화는 부족하다. |
| 최종 완성도 | **66/100**. 구조는 70점대, OOS 증명은 35점이다. |
| 한 줄 결론 | **이제 넓게 만들 수는 있지만, 좋은 조건식으로 증명하는 단계는 seed/anchor OOS 검증이 핵심 병목이다.** |
