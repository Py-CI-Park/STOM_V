# 조건식 연구 지식관리 시스템 설계

## 목적

조건식 연구는 단발 백테스트 결과보다 **조건식 계보, 이름, 코드 전문, 분석 카드, 공식 백테스트 결과, 실패 원인, 다음 가설**이 함께 보존될 때 재현 가능해진다. 현재 `rr8_12_turnover_min_902=1.5` 같은 이름은 연구자에게는 힌트를 주지만, 새로 보는 사람이나 AI에게는 다음 한계가 있다.

| 문제 | 영향 | 개선 원칙 |
|---|---|---|
| 이름이 파라미터 조각 중심 | 조건식의 구조/시장 가설/부모 계보를 즉시 알기 어렵다 | 사람이 읽는 별칭과 기계 id를 분리한다 |
| id만 프롬프트에 전달 | LLM이 실제 매수/매도 구조를 모른 채 후보를 만든다 | 프롬프트에는 buy/sell 조건식 전문과 sha256을 넣는다 |
| 결과 파일과 조건식 연결 약함 | 어떤 조건식이 어떤 백테스트/분석 카드/후보를 만들었는지 추적이 어렵다 | Condition Passport를 기준 레코드로 둔다 |
| 연구 기록이 산발적 | 같은 실패를 반복하고 다음 가설이 약해진다 | 계획서, 관리 보고서, 결과 보고서를 한 세트로 남긴다 |

## 퀀트 관점 검토

사용자 의견인 “wiki/Obsidian 같은 연구 문서 관리 시스템이 도움이 되는가?”에 대한 판단은 **매우 타당하다**. 조건식 연구는 일반 소프트웨어 개발보다 실험 계보와 실패 기록의 가치가 크다. 좋은 조건식은 한 번에 생성되지 않고, 여러 시드/국면/손실 원인/수정축을 누적 비교하면서 발견된다. 따라서 문서가 단순 보고서가 아니라 다음 연구 입력이 되어야 한다.

| 관점 | 판단 |
|---|---|
| AI 프롬프트 품질 | 문서화된 Condition Passport와 분석 카드가 있으면 LLM 입력 품질이 올라간다 |
| 사람 검토 | 어려운 id 대신 별칭/가설/성과/위험을 한 화면에서 볼 수 있다 |
| 재현성 | 조건식 전문, sha256, backtest csv, run id가 연결되면 재실행 가능하다 |
| 과최적화 방지 | 실패 원인과 OOS/frozen/fresh 상태를 보존하면 같은 과최적화를 반복하지 않는다 |
| 연구 속도 | 다음 후보 생성 전에 자료를 찾는 시간이 줄어든다 |

결론: **도입해야 한다.** 다만 처음부터 거대한 시스템보다 Markdown 기반 wiki + JSONL registry + dashboard 링크의 혼합형이 맞다.

## 권장 구조

```text
docs/research/condition_research/
  README.md
  condition_registry.md                  # 사람이 보는 조건식 인덱스
  condition_passports/
    <condition-id>.md                     # 조건식별 passport
  research_runs/
    <run-id>_plan.md                      # 연구 계획서
    <run-id>_management.md                # 진행 관리 보고서
    <run-id>_result.md                    # 최종 결과 보고서
  auto_reports/
    ...                                   # 기존 자동 보고서
artifacts/<run-id>/
  research_context_pack.json
  candidate_cards.jsonl
  analysis_cards.jsonl
  prompt_mutation_receipts.jsonl
  full_period_backtest_receipts.json
  dashboard_verification.json
```

## Condition Passport 표준

각 조건식은 사람이 읽는 한 장짜리 passport를 가져야 한다.

| 필드 | 필수 | 설명 |
|---|---:|---|
| `condition_id` | 예 | 기계 추적 id. 예: `rr8_12_turnover_min_902=1.5` |
| `human_name` | 예 | 사람이 이해하는 이름. 예: `OOS 안정형 09:02 거래대금 완화 시드` |
| `family` | 예 | rr8, gptauth, cldgen, human_mutation 등 |
| `lane` | 예 | seed, repair, discovery, comparator, promotion-review-source |
| `buy_strategy_id` | 예 | STOM buy 전략 id |
| `sell_strategy_id` | 예 | STOM sell 전략 id |
| `buy_code_sha256` | 예 | 매수 조건식 전문 hash |
| `sell_code_sha256` | 예 | 매도 조건식 전문 hash |
| `buy_code` | 예 | 매수 조건식 전문. 프롬프트 전달용 |
| `sell_code` | 예 | 매도 조건식 전문. 프롬프트 전달용 |
| `core_hypothesis` | 예 | 이 조건식이 노리는 시장 현상 |
| `known_strengths` | 예 | 강한 시간대/시총/국면 |
| `known_weaknesses` | 예 | 약한 구간, 손실 cluster, give-back 등 |
| `official_metrics` | 예 | profit, MDD, trades, daily, win, payoff |
| `oos_status` | 예 | untested / partial / passed_windows / failed |
| `slippage_status` | 예 | advisory 상태. 3틱은 즉시 hard gate 아님 |
| `promotion_status` | 예 | research_only / review_only / not_promoted |
| `source_artifacts` | 예 | backtest csv, analysis card, receipt 경로 |
| `next_allowed_actions` | 예 | repair/discovery/review 가능 여부 |

## 이름 규칙

기계 id는 유지하되, 사람이 보는 이름을 별도로 만든다.

| 구성 요소 | 예 | 설명 |
|---|---|---|
| 안정성/역할 | `OOSStable`, `ProfitLead`, `Comparator`, `DiscoverySeed` | 연구 역할 |
| 시간/국면 | `Open902`, `Midday`, `CloseRisk` | 주요 구간 |
| 핵심 축 | `TurnoverMin`, `TrailKeep`, `CapMax`, `ExitEdge` | 주요 파라미터/가설 |
| 버전 | `v1`, `v2`, `r01` | 사람이 보는 연구 버전 |

권장 human name 예시:

| 기존 id | human_name | 역할 |
|---|---|---|
| `rr8_12_turnover_min_902=1.5` | `OOSStable_Open902_TurnoverMin_v1` | 1차 repair seed |
| `rr8_21_trail_keep=0.7` | `ProfitLead_TrailKeep070_2025Comparator` | profit comparator |
| `rr8_0_cap_max=2500` | `CapLimited_2500_Comparator` | 시총 축 comparator |
| `human_seed_gptauth_B_gen8` | `GPTGen8_HighCoverage_FailedProfitContext` | 실패/coverage 참고 |
- 구현 계약명: `full_condition_code_required_not_id_only`

## 연구 문서 3종 세트

| 문서 | 작성 시점 | 목적 | 포함 내용 |
|---|---|---|---|
| 연구 계획서 | 실행 전 | 무엇을 왜 돌리는지 고정 | seed, comparator, Context Pack, 후보 구성, 엔진, 안전 경계 |
| 연구 관리 보고서 | 실행 중 | 진행 상황과 의사결정 기록 | 실행 로그, 실패/timeout, fallback, 후보별 상태, 변경 금지 사항 |
| 연구 결과 보고서 | 실행 후 | 다음 연구 입력으로 재사용 | 공식 결과, 분석 카드, 실패 원인, 다음 후보 queue, 안전 receipt |

## AI와 사람이 함께 쓰는 운영 방식

| 단계 | 사람 역할 | AI 역할 | 산출물 |
|---|---|---|---|
| 시작 전 | seed/목표/금지 경계 확인 | registry/passport/과거 보고서 수집 | 연구 계획서 |
| 실행 중 | 중간 판단 필요 시 방향 확인 | 관리 보고서 갱신, 실패 기록, 후보 실행 | 관리 보고서 |
| 실행 후 | 결과 해석 검토 | 분석 카드/다음 queue 생성 | 결과 보고서 |
| 다음 루프 | 우선순위 승인 | Context Pack에 이전 결과 반영 | 다음 연구 계획서 |

## 필수 원칙

1. 조건식 id만으로 LLM에게 생성 요청하지 않는다.
2. 이전 매수/매도 조건식 전문과 sha256을 prompt/context/receipt에 남긴다.
3. seed 이름은 사람이 이해할 수 있는 별칭을 붙인다.
4. 모든 후보는 부모, 가설, 수정축, 위험, 공식 백테스트 결과를 가진다.
5. promotion-review는 생성 없이 evidence health만 본다.
6. export/live/final promotion은 연구 문서에서도 금지로 명시한다.
7. 실패한 후보도 다음 연구 입력이므로 삭제하지 않고 reject reason을 남긴다.
