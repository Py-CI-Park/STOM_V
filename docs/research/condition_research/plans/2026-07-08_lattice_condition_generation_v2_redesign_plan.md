# 2026-07-08 Lattice / Condition-Generation V2 Redesign Plan

작성시각: 2026-07-07 22:55 KST

## 1. 목적

이 계획의 목적은 기존 576 lattice와 Plan D seed 연구 결과를 바탕으로, 다음 조건식 생성 체계를 재설계하는 것이다.

중요한 범위 제한:

- 이번 계획은 backtest 실행 계획이 아니라 redesign plan이다.
- 새 조건식 생성, DB 등록, full tick/min 288 실행, OOS, portfolio, export/live/final promotion은 실행하지 않는다.
- Plan D R3를 자동으로 열지 않는다.
- 다음 실행이 필요하면 blind split 또는 walk-forward 경계를 먼저 확정한 뒤 별도 승인으로 연다.

## 2. 왜 재설계가 필요한가

기존 lattice는 전수 검증 자체에는 성공했다. 하지만 전략 후보로는 실패했다.

| evidence | result |
|---|---:|
| tick official warm64 | 288/288 status ok, gate_passed 0 |
| min official warm64 | 288/288 coverage, gate_passed 0 |
| P6 decision | go 0, hold 0, no_go 576 |
| 576 deep positive + MDD + daily intersection | 0 |
| repair composite selected OOS-style | survivor 15 / 16 |
| seed_pool after Plan D rank03 R2 closeout | 24 records |

따라서 문제는 backtest engine이 아니라 조건식 생성 구조다. 같은 lattice 축을 다시 반복하면 같은 실패 지도를 더 비싸게 만드는 일이 된다.

## 3. 유지할 접근과 버릴 접근

### 유지

| 유지할 것 | 이유 |
|---|---|
| DB 전체기간/warm64/profile receipt | wrong-profile과 성과 문제를 분리할 수 있음 |
| INSERT-only 원칙 | 연구 DB 원장 추적 가능 |
| source_read_receipt, SHA, line_count | 다음 세션 복원 가능 |
| min lane 중심 repair | tick보다 sparse positive fragment가 있음 |
| composite coverage | 단일 lattice보다 survivor 생성 성과가 있음 |
| selected-only preregistration | 과최적화와 scope creep 방지 |
| no_go 원인 분해 | MDD, 손익, daily, time/size/strength/family별 원인 추적 가능 |

### 버릴 것

| 버릴 것 | 이유 |
|---|---|
| 같은 576 lattice 반복 | P6 go 0/hold 0/no_go 576으로 이미 결론 |
| tick lane 단독 채굴 | tick 288 전부 negative profit |
| full-period replay에서 고른 후보를 blind OOS로 해석 | selection contamination 위험 |
| Plan D R3/R4 자동 반복 | window overfit 위험 |
| portfolio 산출 선행 | portfolio-ready evidence가 없음 |

## 4. V2 설계 원칙

V2는 "격자 채굴"이 아니라 "failure map 기반 constrained generation"으로 바꾼다.

1. candidate를 많이 만드는 것이 목표가 아니다.
2. 먼저 blind split 또는 walk-forward evaluation boundary를 고정한다.
3. tick lane은 stress/diagnostic으로만 사용하고, seed discovery는 min lane 중심으로 한다.
4. 단일 cell/time/size/strength/family 후보보다 composite coverage 후보를 우선한다.
5. daily trade coverage와 MDD cap을 동시에 설계 목표로 둔다.
6. sell/risk profile은 매수 신호 edge 부족을 가리는 보정 수단으로 쓰지 않는다.
7. 모든 candidate는 research lane, hypothesis_seed label, sanitized name만 허용한다.

## 5. V2 축 재설계

### 기존 축 문제

| 기존 축 | 문제 |
|---|---|
| tick 09:00~09:25 bucket | 손실과 MDD가 구조적으로 큼 |
| min 09h/10h/11h/13h/14h/1430p | 일부 positive fragment는 있으나 daily/MDD/profit 교집합 부족 |
| size small/midsmall/midlarge/large | 안전한 단일 size 축 없음 |
| strength low/mid/high | threshold만 조정해도 survivor 교집합 생성 안 됨 |
| family momentum/volume/strength/prevday | family 단독 edge 부족 |

### V2 축

| V2 axis | 설계 방식 |
|---|---|
| lane | min primary, tick diagnostic only |
| time regime | morning, midday, late buckets를 단일 후보가 아니라 composite slots로 조합 |
| coverage class | daily >= 0.5를 생성 전 목표로 둠 |
| risk class | MDD proxy를 후보 설계 단계에서 제약으로 둠 |
| signal family | price-position, volume/amount, strength, prevday-active를 독립 축이 아니라 component pool로 관리 |
| exit profile | default TP3/SL3/H90을 baseline으로 두고, sell mutation은 별도 실험으로 분리 |
| seed lineage | repair composite survivor와 Plan D survivor를 lineage passport로만 사용 |

## 6. V2 후보군 설계

### Candidate classes

| class | quota | 설명 |
|---|---:|---|
| coverage composite | 8 | daily 부족을 해결하기 위한 multi-slot 후보 |
| risk-balanced composite | 8 | low-MDD fragment와 coverage fragment 결합 |
| survivor-seed derivative | 8 | seed_pool 상위 후보를 직접 재사용하지 않고 component만 차용 |
| negative-control | 4 | 기존 실패 lattice와 유사한 구조를 의도적으로 포함해 gate sanity 확인 |
| holdout-control | 4 | repair composite survivor 중 하나를 control로 고정 |

초기 설계 총량은 32개를 넘기지 않는다. 이것도 바로 backtest하지 않는다. 먼저 static/token/compile/dry-run registration 검증만 수행한다.

## 7. 검증 경계

V2에서 가장 먼저 고정할 것은 평가 경계다.

### 권장 split

| segment | 기간 | 용도 |
|---|---|---|
| train/design | 2025-04-07~2025-09-30 | 후보 설계와 parameter sanity |
| validation | 2025-10-01~2025-12-31 | preflight 선택 |
| blind OOS | 2026-01-01~2026-02-27 | 선택 후 1회만 열기 |

이 split은 min DB 기준이다. tick은 stress lane으로 별도 사용한다.

### Walk-forward 대안

| fold | design | validation |
|---|---|---|
| WF1 | 2025-04~2025-06 | 2025-07 |
| WF2 | 2025-05~2025-08 | 2025-09 |
| WF3 | 2025-07~2025-10 | 2025-11 |
| WF4 | 2025-09~2025-12 | 2026-01 |

선택은 다음 계획에서 한다. 이번 계획은 두 안을 모두 남기되, 실행은 하지 않는다.

## 8. Gate 재정의

### Research gate

promotion gate와 research gate를 분리한다.

| gate | 기준 |
|---|---|
| execution | status ok, metrics present |
| profit | validation profit > 0 |
| MDD | MDD <= 35, 단 train-only 과최적화 후보는 hold |
| daily | daily_avg_trades >= 0.5 |
| stability | validation과 blind OOS 방향성 불일치 시 no_go |
| lineage | same lineage 반복 후보는 diversity cap 적용 |

### Promotion gate

이번 계획에서는 정의만 하고 실행하지 않는다.

- fully blind OOS 통과
- walk-forward 3/4 fold 이상 positive
- seed lineage diversity 확보
- portfolio stress 통과
- 사용자 승인 후에만 export/live/final 검토

## 9. 밤샘 작업 페이지

내일 2026-07-08 06:50 KST까지 실행한다면 다음 범위가 적절하다. 이 범위는 heavy backtest가 아니라 plan/evidence generation이다.

| page | 목표 | 산출물 | 예상 시간 |
|---|---|---|---:|
| T0 | source receipt 재확인 | source receipt, SHA/line count | 10~20m |
| T1 | 576 failure map 재분해 | axis discard/keep ledger | 40~60m |
| T2 | seed_pool lineage audit | seed lineage diversity table | 30~60m |
| T3 | V2 axis spec 작성 | axis spec JSON/MD | 60~90m |
| T4 | split/WF boundary 설계 | evaluation protocol MD/JSON | 60~90m |
| T5 | candidate class quota 설계 | candidate quota ledger | 40~60m |
| T6 | static/dry-run-only command 설계 | next execution command draft | 30~45m |
| T7 | adversarial review | boundary receipt, no-execution proof | 30~45m |
| T8 | handoff/commit | update_log, ULW evidence, Korean commit | 30~60m |

총 예상: 5~7시간. 내일 아침까지 충분히 완료 가능한 planning scope다.

## 10. 금지 사항

- full tick 288 실행 금지
- full min 288 실행 금지
- OOS 실행 금지
- portfolio 산출 금지
- export/live/final promotion 금지
- Plan D R3 자동 진행 금지
- DB UPDATE/DELETE 금지
- DB INSERT apply 금지
- 새 STOM 전략 코드 생성 금지
- 기존 dashboard 7파일, `.gjc`, unrelated `.omo` 잔재 stage 금지
- `git add -A` 금지

## 11. 다음 실행 명령어

아침까지 실제로 이어갈 때는 아래 명령을 추천한다.

```text
$ulw-loop .omo/plans/lattice-condition-generation-v2-redesign-overnight-20260708.md

범위는 redesign-plan-only-until-20260708-0650-KST까지만 진행한다.
목표는 기존 576 lattice 실패와 repair composite/Plan D survivor seed를 바탕으로
lattice/condition-generation v2 재설계 계획과 다음 실행 명령어를 완성하는 것이다.

반드시 먼저 읽을 문서:
- docs/update_log/2026-07-08_condition_research_full_result_and_analysis.md
- docs/update_log/2026-07-08_plan_d_rank03_r2_selected_oos_closeout_handoff.md
- docs/research/condition_research/plans/lattice_condition_generation_v2_redesign_source_receipt_20260708.json
- docs/research/condition_research/research_runs/seed_lattice_20260702/repair_overnight_20260705/overnight_no_d_576_deep_analysis_20260705.json
- docs/research/condition_research/generated_conditions/seed_pool.jsonl
- utility/ai_agent/strategy.txt
- utility/ai_agent/rules.txt

진행:
1. 576 lattice failure map에서 버릴 축과 유지할 축을 확정한다.
2. seed_pool lineage를 중복/과최적화 위험 기준으로 audit한다.
3. min/composite/coverage 중심 V2 axis spec을 작성한다.
4. blind split 또는 walk-forward 평가 경계를 설계한다.
5. 후보 class별 quota와 negative/holdout control을 설계한다.
6. 다음 단계에서 실행할 static/dry-run-only 명령어만 작성한다.
7. backtest, DB INSERT apply, OOS, portfolio, Plan D R3는 실행하지 않는다.
8. handoff, ULW evidence, 한글 커밋까지 남긴다.

금지:
- full tick 288 실행 금지
- full min 288 실행 금지
- OOS 실행 금지
- portfolio 산출 금지
- export/live/final promotion 금지
- Plan D R3 자동 진행 금지
- DB UPDATE/DELETE 금지
- DB INSERT apply 금지
- 새 조건식 코드 생성 금지
- git add -A 금지
- dashboard 7파일, .gjc, unrelated .omo 잔재 stage 금지

완료 후 보고:
- 버릴 축 / 유지할 축
- V2 axis spec
- evaluation boundary
- candidate class quota
- 다음 static/dry-run-only 실행 명령어
- remaining risks
- 커밋 해시
```

## 12. 다음 단계 판단

이 계획이 완료되면 바로 실행할 수 있는 다음 단계는 `candidate generation dry-run only`다.

다음 단계에서 허용 가능한 작업:

- V2 axis spec 기반 후보 이름 설계
- strategy/rules 기준 static syntax 검토
- DB registration dry-run
- no apply, no backtest

다음 단계에서도 아직 금지할 작업:

- DB INSERT apply
- limited replay
- OOS
- portfolio

## 13. 최종 추천

내일 아침까지는 실제 backtest가 아니라 redesign plan을 끝내는 것이 효율적이다. 이유는 명확하다.

1. 이미 576/576 공식 coverage는 완료됐고 survivor는 0이었다.
2. 지금 필요한 것은 더 많은 계산이 아니라 생성 구조의 재정의다.
3. fully blind boundary 없이 계속 Plan D를 돌리면 연구 성과가 아니라 window overfit이 될 위험이 크다.
4. repair composite와 Plan D survivor는 버릴 것이 아니라 V2 설계 입력으로 보존해야 한다.

따라서 다음 연구의 첫 목표는 "새 조건식을 더 만들기"가 아니라 "새 조건식을 어떻게 만들고 어떻게 검증할지"를 확정하는 것이다.
