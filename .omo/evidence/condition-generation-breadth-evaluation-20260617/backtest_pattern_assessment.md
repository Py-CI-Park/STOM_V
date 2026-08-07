# 백테스트 결과와 생성 패턴 연결 평가 (2026-06-17)

## 핵심 결론

| 질문 | 수치 근거 | 판단 |
|---|---:|---|
| AI가 넓은 범위 조건식을 생성하는가? | 템플릿 149개, tick 111 / min 38, 기본 렌더 검증 149/149 | 예, 구조적 범위는 넓다 |
| AND/OR를 섞는가? | AND 149/149, literal OR 38/149, `if/elif` branch 121/149 | 예, 다만 literal OR보다 branch OR 중심 |
| 사람처럼 여러 시도를 하는가? | time bucket, cap band, multiband, theta anchor, orderflow, min full-session 계열 존재 | 일부 예, 하지만 human reference corpus화는 부족 |
| 넓게 생성한 조건식이 좋은 조건식으로 이어졌는가? | full stateful n=40 PROMISING 0/40 | 아직 약하다 |
| 좋은 조건식 주변을 변이하면 개선되는가? | ovn_anchor best +13,928,386 / MDD 9.62, adopted 399 | train-gate 기준 강하다 |
| 최종 성공인가? | 신규 OOS PROMISING 0 | 아니다. OOS 전까지 보류 |

## 실험/근거별 판정

| 근거 | 생성 방식 | 결과 | 해석 |
|---|---|---:|---|
| `ab_random_n8` | 무상태 random broad generation | PROMISING 0/8, no-go 8/8 | 넓게만 뿌리면 성과가 없다 |
| `ab_stateful_n8` | 이전 결과를 피드백으로 주는 broad generation | smoke-pass 3/8, PROMISING 0/8 | stateful feedback은 개선 신호가 있으나 OOS까지 못 감 |
| `full_stateful_n40` | stateful broad generation 40개 | PROMISING 0/40, no-go 40/40 | cold/stateful LLM 생성은 아직 주력 우승 경로가 아님 |
| `multiband_escalation` | multiband broad generation 40개 | smoke-pass 1/40, no-go 38/40, PROMISING 0 | branch/multiband가 있어도 검증 관문에서 대부분 탈락 |
| champion positive control | 검증 champion 4개를 discovery gate 재투입 | 4/4 gate=True, +9.55M~+10.97M | 데이터와 gate는 정상, 생성기가 좋은 구조를 못 찾는 병목 |
| `ovn_anchor` | seed_902905 anchor mutation, LLM 0회 | 19 rounds, adopted 399, best +13.93M / MDD 9.62 | 검증 앵커 주변의 parametric search가 현재 최강 경로 |
| `ovn_t2late.jsonl` | t2late anchor mutation | jsonl 기준 9 rounds, adopted 30, best +10.58M / MDD 11.5 | 다른 basin도 가능하나 summary drift 있음 |
| 신규 OOS | frozen OOS promotion evidence | 0 | 최종 claim 불가 |

## 조건식 생성 패턴별 평가

| 패턴 | 현재 구현/증거 | 점수 | 부족분 | 개선 방법 |
|---|---|---:|---:|---|
| 시간창 조건 | 149/149 time bounds, no-op 0%, span 72~21600초 | 78 | 22 | 시간창별 activation/trade/profit/OOS를 branch별로 기록 |
| 시총 밴드 | market_cap 149/149, cap motif 57% | 80 | 20 | cap band별 lift와 OOS collapse 여부를 별도 리포트화 |
| 수급/거래대금 | liquidity 75.2%, volume_surge 68.5%, turnover 59.1% | 72 | 28 | 거래대금/회전율/체결강도 조합을 과거 good seed와 비교 |
| 호가/잔량 | orderbook 22.1% | 45 | 55 | 사람식 호가벽/매수잔량/매도잔량 setup을 별도 template family로 증설 |
| AND 필터 | 149/149, 평균 17.07개 | 84 | 16 | 과협착 시 자동 완화 action 필요 |
| OR/분기 | `elif` 81.2%, literal OR 25.5% | 66 | 34 | branch별 독립 성과와 branch가 손실을 추가하는지 측정 |
| 사람식 여러 사례 | seed, theta, t2late, orderflow, multiband, min family 존재 | 62 | 38 | human reference 17개를 taxonomy/few-shot/benchmark로 구조화 |
| 매수 조건 다양성 | time/cap/change/liquidity 중심 폭넓음 | 72 | 28 | low-category template 16개는 5+ filter category로 보강 |
| 매도 조건 다양성 | stop/take/trail/hold-time 계열과 exit forensics 존재 | 68 | 32 | branch별 exit rule과 MFE/MAE/giveback을 연결 |
| OOS 생존성 | 신규 OOS PROMISING 0 | 35 | 65 | train champion frozen OOS queue 우선 실행 |

## 왜 "시드가 중요하다"는 판단이 강해졌는가

| 비교 | broad cold generation | 검증 anchor mutation |
|---|---:|---:|
| 후보 생성 폭 | 넓음 | seed 주변으로 제한 |
| 백테스트 생존 | full n=40 PROMISING 0 | train-gate adopted 399 |
| best 성과 | 없음 | +13,928,386 / MDD 9.62 |
| 장점 | 새로운 형태를 찾을 가능성 | 검증된 구조를 보존하며 개선 |
| 단점 | 대부분 no-go | 국소 최적/과적합 위험 |
| 현재 우선순위 | 탐색 보조 | 주력 개선 경로 |

판단: 초기 seed는 중요하다. 다만 "시드 하나만 중요"가 아니라, **좋은 seed 여러 개를 basin으로 삼아 넓지만 통제된 multi-start 변이를 돌리는 것**이 가장 현실적이다.

## 전체 시간을 모두 고려한 조건식에 부족한 점

| 구분 | 현재 상태 | 부족한 점 | 개선 방법 |
|---|---|---|---|
| tick | 주로 09:00~09:30 연구, time bounds는 정교함 | 장중 전체 tick 데이터/검증 범위가 제한적 | tick은 09:00~09:30으로 명시하고, OOS를 먼저 강화 |
| min | 09:00~15:19 full-session toggle/템플릿 존재 | 오전/점심/오후/장마감 family별 성과 관리 부족 | min full-day bucket registry: 09~10, 10~11:30, 11:30~13, 13~14:30, 14:30~15:19 |
| 매수 | 시간/시총/등락/수급 조합은 많음 | 전체 시간대별 최적 변수 조합이 자동으로 재학습되지 않음 | time bucket별 feature importance와 template quota 연결 |
| 매도 | hold-time/stop/take/trail 있음 | 진입 시간/시총별 매도식 차별화 부족 | branch_id별 exit profile 저장, 동일 매도식 일괄 적용 축소 |
| 검증 | smoke/full/OOS cascade 구조 존재 | OOS 통과 후보가 아직 없음 | best train 후보부터 frozen OOS 검증 |

## 앞으로 개발 준비 우선순위

| 우선순위 | 작업 | 목적 | 완료 기준 |
|---:|---|---|---|
| 1 | best anchor OOS 검증 | +13.93M 후보가 진짜인지 확인 | 2022/2026 또는 정의된 frozen OOS pass/fail 카드 |
| 2 | summary drift 복구 | 연구 관리 신뢰도 회복 | `ovn_t2late_summary.json`과 jsonl best 일치 |
| 3 | branch attribution | OR/분기 구조가 도움이 되는지 확인 | branch별 trade/profit/MDD/OOS lift 표 |
| 4 | human reference corpus | 사람식 사례를 재사용 가능한 seed/few-shot으로 전환 | 17개 reference taxonomy + numeric benchmark |
| 5 | feedback action ledger | 나쁜 조건식이 왜 어떻게 개선되는지 추적 | action_id별 before/after 성과 |
| 6 | time-bucket quota | 전체 시간대가 균형 있게 연구되도록 제어 | bucket별 후보 수, 생존율, OOS 결과 대시보드 |
