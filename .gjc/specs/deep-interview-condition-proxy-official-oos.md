# Deep Interview Spec: STOM Proxy Condition Official OOS Research

## Metadata
- Interview ID: 2b1ab709-7950-4aa8-9a88-14ba85f2c0c3
- Rounds: 12 + topology + restate gate
- Final Ambiguity Score: 3.20%
- Type: brownfield
- Generated: 2026-06-19
- Threshold: 0.05
- Threshold Source: default
- Initial Context Summarized: no
- Status: PASSED
- Auto-Researched Rounds: []
- Auto-Answered Rounds: []
- Architect Failures: 0
- Lateral Reviews: 1
- Lateral Panel Failures: 0
- Refined Rounds: []
- Closure Overrides: none
- Restated Goal: STOM에서 실매매/export 없이 연구 범위로만, 기존 combined CSV 조합을 그대로 쓰지 않고 `r8_exclude_cap_lt_1500` 기반 단일 proxy 조건식 후보를 최대 3개 설계해 공식 OOS로 검증하며, 기준 통과 여부를 기존 combined 결과와 비교한 pass/defer/reject 판단 카드로 남기고, 3개 모두 실패하면 fallback 조건식 세트/운영 규칙 연구는 별도 후속으로 분리한다.

## Clarity Breakdown
| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Goal Clarity | 0.98 | 0.35 | 0.3430 |
| Constraint Clarity | 0.96 | 0.25 | 0.2400 |
| Success Criteria | 0.97 | 0.25 | 0.2425 |
| Context Clarity | 0.95 | 0.15 | 0.1425 |
| **Total Clarity** | | | **0.9680** |
| **Ambiguity** | | | **0.0320** |

## Topology
| Component | Status | Description | Coverage / Deferral Note |
|-----------|--------|-------------|--------------------------|
| 실매매 가능한 조건식 형태 | active | CSV 조합이 아니라 STOM에서 백테스트/실매매 후보가 될 수 있는 단일 조건식 또는 실행 가능한 조건식 세트를 정의한다. | 단일 조건식 v1은 `r8_exclude_cap_lt_1500` 기반이며, combined 성과를 맞추기 위한 exit2/r2full proxy 조건도 허용한다. |
| 조합 로직의 구현 가능성 | active | exit2 prior-month 같은 월별/상황별 선택 규칙을 STOM 조건식이나 전략 운영 구조로 표현 가능한지 판단한다. | 단일 조건식 v1은 proxy 후보 최대 3개까지 평가한다. 3개 모두 실패하면 fallback 조건식 세트/운영 규칙 연구는 별도 후속으로 분리한다. |
| 검증 방법 | active | 새 조건식 또는 조건식 세트를 공식 OOS/백테스트로 검증해 기존 CSV 조합 결과와 유사한 성과가 나는지 확인한다. | 공식 OOS 총수익 7,292,861원 초과, MDD 19.09% 이하, 전 구간 gate pass, 거래수 132건 이상, 최소 4개 구간 양수, Q4 양수, 상위 거래 의존 과도 시 보류. |
| 실매매 승격 경계 | active | 연구 결과를 운영 DB/export/live로 넘기기 전 필요한 승인, 비목표, 중단 조건을 분리한다. | 이번 범위는 조건식 코드, 공식 OOS 결과표, combined 비교표, pass/defer/reject 판단 카드까지다. 실매매/export/운영 DB 반영은 별도 승인 전 금지한다. |

## Established Facts
- 현재 combined portfolio 결과는 순수 공식 buy/sell OOS가 아니라 포트폴리오 시뮬레이션/CSV 재분석이다.
- 사용자는 실매매에 쓸 수 있는 조건식 또는 실행 가능한 전략 형태를 목표로 한다.
- 최종 목표는 먼저 단일 조건식으로 유사 성과를 검증하고, 실패하면 조건식 세트 또는 운영 규칙을 검토하는 순서다.
- 단일 조건식 v1은 r8 저시총 제외 같은 entry filter 범위로 시작하지만, combined 성과를 맞추기 위해 exit2/r2full 특성을 흉내 내는 proxy 조건도 적극 허용한다.
- 단일 조건식 v1의 최소 통과 기준은 공식 OOS 단독 기준선보다 개선되는 것이다: 총수익 7,292,861원 초과, MDD 19.09% 이하, 전 구간 gate pass.
- proxy 후보가 좋아 보여도 거래수가 공식 OOS 기준 263건의 50% 미만이면 탈락한다.
- 수익 집중 검토는 최소 4개 구간 양수, Q4 양수, 상위 거래 의존 과도 시 보류로 판단한다.
- 단일 proxy 설계 3개까지 공식 OOS 평가하고, 모두 기준 미달이면 이번 범위에서는 실패 판단 카드까지만 쓰고 fallback 연구는 별도 후속으로 분리한다.
- 통과해도 이번 범위는 연구 종료 및 보고까지이며, 실매매/export/운영 DB 반영은 별도 승인 전 금지한다.

## Trigger Metadata
| Round | Trigger | Status | Effect |
|---:|---|---|---|
| 5 | D scope expansion | resolved by Round 7-12 | proxy 조건 적극 허용으로 ambiguity가 상승했고, 이후 과최적화/거래수/fallback 기준으로 해소했다. |
| 6 | C low-quality/evasive + D scope expansion | resolved by Round 7-12 | “나중에 과최적화 검토”로 안전 기준이 약해졌다가 사후 탈락 기준과 fallback 기준으로 해소했다. |

## Lateral Review Panel
- Round 2 전 initial→progress 전환에서 researcher, contrarian, simplifier 렌즈를 convene했다.
- folded finding: prior-month 손익 기반 규칙은 단일 STOM 조건식 내부 상태로 보기 어렵고, r8 entry filter 및 접근 가능한 proxy 조건으로 단일 조건식 v1을 제한해야 한다.

## Goal
STOM에서 실매매/export 없이 연구 범위로만, 기존 combined CSV 조합을 그대로 쓰지 않고 `r8_exclude_cap_lt_1500` 기반 단일 proxy 조건식 후보를 최대 3개 설계해 공식 OOS로 검증하며, 기준 통과 여부를 기존 combined 결과와 비교한 pass/defer/reject 판단 카드로 남기고, 3개 모두 실패하면 fallback 조건식 세트/운영 규칙 연구는 별도 후속으로 분리한다.

## Constraints
- 제품/운영 mutation 금지: 실매매, export, 운영 DB, strategy DB 반영, V3K/live 경로는 별도 승인 전 금지.
- combined CSV 결과를 공식 buy/sell OOS라고 부르지 않는다.
- 단일 조건식 v1은 최대 3개의 서로 다른 proxy 설계까지만 공식 OOS 평가한다.
- proxy 조건은 성과 우선으로 넓게 허용하되, 결과/손익/미래 정보 또는 실매매에서 재현 불가능한 입력을 쓰면 판단 카드에서 보류/탈락 사유로 기록한다.
- 3개 모두 실패하면 fallback 조건식 세트/운영 규칙 연구는 별도 후속으로 분리한다.

## Non-Goals
- CSV 파일을 상황별로 고르는 수동 운용 방식 구현.
- 실매매 연결, export, 운영 strategy DB 반영.
- V3K gate/live 승인 경로 변경.
- UI/frontend/bundle 개선.
- fallback 조건식 세트/운영 규칙 연구를 이번 범위에서 바로 실행.

## Acceptance Criteria
- [ ] 최대 3개 단일 proxy 조건식 후보를 설계하고 각각 조건식 코드를 저장한다.
- [ ] 각 후보를 공식 OOS로 검증한다.
- [ ] 후보별 공식 OOS 결과표에는 총수익, MDD, gate, 거래수, 기간별 수익, Q4 수익을 포함한다.
- [ ] pass 기준: 총수익 7,292,861원 초과, MDD 19.09% 이하, 전 구간 gate pass.
- [ ] 거래수 기준: 공식 OOS 기준 263건의 50% 이상, 즉 최소 132건 이상.
- [ ] 수익 집중 검토: 최소 4개 구간 양수, Q4 양수, 상위 거래 의존 과도 시 보류.
- [ ] 기존 combined 결과와 비교표를 작성한다: combined 전체 수익 39,402,438원, MDD 7.6823%, Q4 수익 952,502원.
- [ ] 최종 판단 카드는 `pass`, `defer`, `reject` 중 하나로 기록한다.
- [ ] 3개 모두 기준 미달이면 실패 판단 카드만 남기고 fallback 연구는 별도 후속으로 분리한다.
- [ ] protected runtime path status가 깨끗해야 한다.

## Deferrals
- fallback 조건식 세트/운영 규칙 연구는 단일 proxy 후보 3개가 모두 실패할 때 별도 후속으로 분리한다.
- production/export/live 승격 계획은 별도 승인 전 보류한다.
- Convergence pacing deferral: 별도 min-round floor, score-drop cap, confidence dampening은 두지 않았다. Bidirectional scoring이 pacing mechanism이다.

## Assumptions Exposed & Resolved
| Assumption | Challenge | Resolution |
|------------|-----------|------------|
| CSV 조합 결과를 그대로 전략으로 쓰면 된다 | 사용자가 실매매 가능한 조건식이 목적이라고 정정했다 | 단일 proxy 조건식 공식 OOS 검증으로 목표를 재정의했다 |
| exit2 prior-month 규칙을 단일 조건식 안에 넣을 수 있다 | STOM 조건식 런타임에서 전월 전략 손익 상태를 바로 쓸 근거가 약하다 | 단일 조건식 v1은 proxy 조건을 허용하고, 실제 prior-month 운영 규칙은 fallback/별도 후속으로 분리한다 |
| 성과만 맞으면 된다 | 과최적화와 수익 집중 위험이 있다 | 거래수 하한, 구간 양수, Q4 양수, 상위 거래 의존 보류 기준을 추가했다 |

## Technical Context
- Brownfield: STOM/ai_strategy_loop 연구 환경.
- 공식 OOS는 이름 있는 buy/sell 조건식 pair를 평가한다.
- 기존 combined 결과는 `.omo/evidence/tmap-walkforward/post-20260618-combined-portfolio-simulation-readout-20260619.json`에 정리된 포트폴리오 시뮬레이션/CSV 재분석이다.
- 비교 기준선: 공식 OOS 단독 `r8_exclude_cap_lt_1500` 총수익 7,292,861원, MDD 19.09%, 총 거래수 263건.
- 비교 대상 combined 기준: 총수익 39,402,438원, MDD 7.6823%, Q4 수익 952,502원.

## Ontology (Key Entities)
| Entity | Type | Fields | Relationships |
|--------|------|--------|---------------|
| proxy 기반 단일 조건식 v1 | core domain | 조건식 코드, proxy 설계, 공식 OOS 결과 | 공식 OOS로 검증되고 판단 카드로 평가된다 |
| 공식 OOS | validation surface | 총수익, MDD, gate, 거래수, 기간별 수익 | proxy 조건식 후보를 검증한다 |
| combined portfolio simulation | reference evidence | 총수익, MDD, Q4 수익 | 비교표의 기준이지만 공식 buy/sell OOS는 아니다 |
| fallback 연구 | deferred follow-up | 조건식 세트, 운영 규칙 | 3개 proxy 후보 실패 시 별도 후속으로 분리된다 |
| 판단 카드 | decision artifact | pass, defer, reject, 사유 | 연구 완료 산출물이다 |

## Ontology Convergence
| Round | Entity Count | New | Changed | Stable | Stability Ratio |
|-------|-------------|-----|---------|--------|----------------|
| 1 | 6 | 6 | - | - | N/A |
| 2 | 8 | 2 | 1 | 5 | 75% |
| 3 | 9 | 1 | 0 | 8 | 88% |
| 4 | 11 | 2 | 1 | 7 | 82% |
| 5 | 13 | 2 | 1 | 10 | 85% |
| 6 | 14 | 2 | 1 | 11 | 93% |
| 12 | 20 | 0 | 0 | 20 | 100% |

## Interview Transcript
<details>
<summary>Full Q&A</summary>

### Round 0
**Q:** Topology confirmation.
**A:** 맞습니다. 이 4개로 진행하세요.

### Round 1
**Q:** 최종 목표는 어느 형태에 가장 가깝습니까?
**A:** 먼저 단일 조건식으로 유사 성과가 나오는지 검증하고, 안 되면 세트/운영 규칙을 검토한다.
**Ambiguity:** 56.25%

### Round 2
**Q:** 단일 조건식 시도에서 허용할 로직 범위는 어디까지입니까?
**A:** 단일 조건식 v1은 r8 저시총 제외 같은 entry filter만 만들고, exit2 전월 손익 규칙은 조건식 세트/운영 규칙으로 분리한다.
**Ambiguity:** 37.00%

### Round 3
**Q:** 단일 조건식 v1이 통과했다고 볼 최소 기준은 무엇입니까?
**A:** 공식 OOS 단독보다 개선되면 충분: 총수익 7,292,861원 초과, MDD 19.09% 이하, 전 구간 gate pass.
**Ambiguity:** 21.80%

### Round 4
**Q:** 단일 조건식 v1이 통과 기준을 만족하면 다음 단계는 무엇이어야 합니까?
**A:** 연구 종료 및 보고까지만 한다. 실매매/export/운영 DB 반영은 별도 승인 전 금지한다.
**Ambiguity:** 14.90%

### Round 5
**Q:** 단일 조건식 v1은 어떤 방식으로 만들어야 합니까?
**A:** combined 성과를 맞추기 위해 exit2/r2full 특성을 흉내 내는 proxy 조건도 적극 허용한다.
**Ambiguity:** 19.90%

### Round 6
**Q:** proxy 조건을 만들 때 어떤 제한을 반드시 걸어야 합니까?
**A:** 성과가 가장 중요하므로 proxy 탐색은 넓게 허용하고, 나중에 과최적화만 검토한다.
**Ambiguity:** 26.25%

### Round 7
**Q:** proxy 조건식 후보가 좋은 성과를 냈더라도 어떤 경우에는 탈락시켜야 합니까?
**A:** 성과 기준은 통과해도 거래수가 너무 적거나 특정 구간에 수익이 몰리면 탈락시킨다.
**Ambiguity:** 20.70%

### Round 8
**Q:** 단일 proxy 조건식 v1의 사후 탈락 기준은 어느 정도가 적절합니까?
**A:** 거래수는 공식 OOS 기준 263건의 50% 이상이면 되고, 수익 집중은 정성 검토로 둔다.
**Ambiguity:** 17.70%

### Round 9
**Q:** 수익 집중 정성 검토에서 어떤 패턴이면 탈락 또는 보류로 보겠습니까?
**A:** 최소 4개 구간 양수 + Q4 양수 + 상위 거래 의존 과도 시 보류로 본다.
**Ambiguity:** 11.90%

### Round 10
**Q:** 이번 후속 연구의 완료 산출물은 무엇이어야 합니까?
**A:** 조건식 코드 + 공식 OOS 결과표 + 기존 combined 결과와의 비교표 + pass/defer/reject 판단 카드까지.
**Ambiguity:** 9.40%

### Round 11
**Q:** 단일 조건식 v1에서 조건식 세트/운영 규칙 연구로 넘어가는 기준은 무엇입니까?
**A:** 서로 다른 proxy 설계 3개까지 공식 OOS 평가하고, 모두 기준 미달이면 fallback으로 전환한다.
**Ambiguity:** 5.60%

### Round 12
**Q:** 3개 proxy 설계가 모두 기준 미달이면 어떻게 처리해야 합니까?
**A:** 이번 범위에서는 실패 판단 카드까지만 쓰고, fallback 연구는 별도 후속으로 분리한다.
**Ambiguity:** 3.20%

### Restate Gate
**Goal line confirmed:** 예, 이대로 spec을 작성하세요.

</details>
