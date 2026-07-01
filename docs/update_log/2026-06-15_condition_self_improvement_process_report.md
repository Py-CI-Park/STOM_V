# 조건식 자기개선 프로세스 상세 검토 보고서 (2026-06-15)

> 범위: 현재 개발된 tick/min 조건식 생성, 백테스트 검증, 연구 기록, 테스트 결과를 바탕으로 "나쁜 조건식에서 좋은 조건식으로 AI가 스스로 개선하는 프로세스"가 어느 정도 완성됐는지 평가하고, 어떻게 업데이트하면 좋은지 정리한다. 이 문서는 구현 기록이 아니라 연구/개발 준비 보고서다.

## 1. 한 줄 결론

| 항목 | 판단 |
|---|---|
| 전체 목적 이해 | DB와 백테스트 결과를 이용해 매수/매도 규칙을 데이터 기반으로 찾고, 실패 원인을 다음 생성에 반영하는 폐루프를 만들려는 것이다. |
| 현재 완성도 | **56%** |
| 현재 부족분 | **44%** |
| 가장 강한 부분 | 백테스트 격상 게이트, P0b 재백테스트 게이트, OOS 기준 명확화 |
| 가장 부족한 부분 | seed coverage ledger, typed feedback action ledger, buy/sell 원인 분리 후 mutation, 전체 lineage |
| 현재 실증 | stateful pilot은 smoke-pass rate를 0.0 -> 0.375로 올렸지만 OOS PROMISING은 여전히 0이다. |
| 핵심 결론 | "조금 학습하는 생성기"는 됐지만, "좋은 조건식을 스스로 찾는 완전한 AI 연구 루프"는 아직 아니다. |

## 2. 목적과 프로세스 이해

| 구성 | 의미 | 좋은 프로세스가 되려면 |
|---|---|---|
| DB | 과거 tick/min 데이터, 전략 결과, 거래별 B_*/S_*/R_* 기록의 원천 | 후보마다 어떤 조건에서 사고팔았는지 재현 가능해야 함 |
| 생성기 | 매수/매도 조건식 또는 TMAP template을 만드는 계층 | 랜덤이 아니라 coverage debt와 실패 교훈에 따라 다음 후보를 만들어야 함 |
| 백테스트 | 후보가 실제 과거 데이터에서 작동하는지 검증 | q1/q2/full/OOS/WF 단계가 분리되어야 함 |
| 매수 진단 | B_* snapshot, 시간대, 시총, 등락률, 체결강도 등 진입 원인 분석 | 어느 진입 구간이 홍수/저승률/과적합인지 action으로 바꿔야 함 |
| 매도 진단 | MFE/MAE, giveback, hold time, sell rule 분석 | 진입 edge가 있는데 청산이 망치는지 분리해야 함 |
| feedback | 실패/성공 원인을 다음 생성에 반영 | 자연어 힌트가 아니라 typed action ledger로 관리해야 함 |
| OOS/WF | 진짜 일반화 검증 | smoke-pass, score, dashboard metric이 아니라 OOS 통과만 성공으로 인정 |

## 3. 현재 개발/연구/테스트 근거

| 영역 | 근거 | 확인된 내용 |
|---|---|---|
| stateful feedback | `ai_strategy_loop/scripts/tmap_multiband_discovery.py:87` | 이전 record에서 avoid/prefer feedback을 만드는 구조가 있다. |
| feedback 주입 | `ai_strategy_loop/scripts/gen_template_hypothesis.py:73` | `feedback_text`를 generation prompt에 넣을 수 있다. |
| 검증 funnel | `ai_strategy_loop/scripts/tmap_multiband_discovery.py:212` | q1 -> q2 -> full train -> OOS 격상 구조가 있다. |
| segment avoid | `ai_strategy_loop/brain/segment_feedback.py:84` | 손실 시간/시총/등락률 cell을 매수 avoid 라인으로 만들 수 있다. |
| 매수 분석 | `ai_strategy_loop/autopsy/analyze.py:25` | B_* 진입 변수 목록이 있다. |
| 매도 분석 | `ai_strategy_loop/autopsy/analyze.py:295` | MFE/MAE/보유시간/매도조건 분석 함수가 있다. |
| 백테 결과 데이터 | `backtest/backengine_base.py:557` | R_MFE, R_MAE, 매수후최고/최저수익률이 결과에 들어간다. |
| prompt lineage gap | `ai_strategy_loop/config.py:514` | prompt logging은 필요성이 문서화됐지만 default-OFF다. |
| dashboard 분석 | `ai_strategy_loop/dashboard/analysis_snapshot.py:244` | edge ratio, feature importance, generation metrics, daily P/L 분석이 가능하다. |
| OOS 기준 | `.omo/evidence/tmap-walkforward/p1_ab_preregistration.md:14` | OOS PROMISING 수가 유일한 합격 지표로 동결됐다. |
| pilot 결과 | `.omo/evidence/tmap-walkforward/ab_result_n8.json` | random 0/8 smoke-pass, stateful 3/8 smoke-pass, OOS는 둘 다 0. |
| 40회 결과 | `docs/update_log/2026-06-15_multiband_overnight_results.md:8` | 40회 중 PROMISING 0, 전체기간 도달 1건도 과적합 기각. |

## 4. 전체 점수표

| 평가축 | 점수 | 부족분 | 판단 |
|---|---:|---:|---|
| 목적 정렬 | 85% | 15% | OOS 기준과 연구 목적은 명확하다. |
| 데이터 캡처 | 78% | 22% | B_*/MFE/MAE는 있다. lineage 결합이 부족하다. |
| 백테스트 게이트 | 82% | 18% | 현재 가장 강한 부분이다. |
| Seed breadth | 45% | 55% | 넓은 탐색 의도는 있으나 coverage ledger가 없다. |
| 생성 다양성 | 48% | 52% | 다밴드 생성은 하지만 family 중복/편중 제어가 약하다. |
| Buy-side 진단 | 58% | 42% | B_*와 segment 분석은 있으나 action화가 부족하다. |
| Sell-side 진단 | 52% | 48% | MFE/MAE 분석은 있으나 매도 mutation 연결이 약하다. |
| Feedback policy | 42% | 58% | 자연어 prompt feedback 중심이다. typed ledger가 필요하다. |
| DB/evidence lineage | 55% | 45% | 분석 snapshot은 있으나 prompt/feedback/run lineage가 불완전하다. |
| Dashboard/runbook | 60% | 40% | 분석은 보이지만 다음 action 이유가 충분히 보이지 않는다. |
| OOS proof | 25% | 75% | 현재 신규 후보 OOS PROMISING은 0이다. |
| End-to-end autonomy | 38% | 62% | 자동 반복은 시작됐지만 완전 폐루프는 아니다. |
| **평균** | **56%** | **44%** | 현 단계는 "정직한 검증기 + 부분 feedback 생성기" 수준이다. |

## 5. 지금 부족한 것

| 우선 | 부족한 것 | 왜 문제인가 | 현재 증거 |
|---|---|---|---|
| 1 | OOS 통과 후보 0 | 좋은 조건식을 찾았다고 말할 수 없다. | n=8 A/B와 40회 다밴드 모두 OOS/PROMISING 0 |
| 2 | Seed coverage ledger 없음 | 초반 seed가 넓지 않으면 같은 구간만 반복 탐색한다. | broad guidance는 있으나 coverage debt 기록이 없음 |
| 3 | Feedback이 typed action이 아님 | "피하라/선호하라" 문장은 재현, 측정, expiry 관리가 어렵다. | `feedback_text` 기반 prompt 주입 |
| 4 | Buy/Sell 원인 분리 미흡 | 매수 실패인지 청산 실패인지 모르면 잘못된 부분을 고친다. | autopsy 함수는 있으나 mutation 연결 부족 |
| 5 | Prompt/feedback lineage 부족 | 어떤 prompt와 feedback이 어떤 결과를 냈는지 완전 추적이 어렵다. | prompt logging default-OFF |
| 6 | Proxy score 과신 위험 | smoke-pass rate가 올라가도 OOS 0이면 성공이 아니다. | stateful pilot smoke-pass 0.375, OOS 0 |
| 7 | Mutation/grid policy 부족 | 실패 원인을 구조적으로 바꿔 재시도하는 체계가 약하다. | P4/P5 미완료 |
| 8 | Dashboard action 설명 부족 | 왜 다음 세대가 그렇게 바뀌는지 관리하기 어렵다. | analysis snapshot은 있으나 action ledger UI 없음 |

## 6. 어떻게 업데이트하면 좋은가

| 업데이트 | 구체 방법 | 기대 개선 |
|---|---|---|
| P0 metric freeze | OOS/WF PROMISING count만 성공으로 인정하고 proxy metric은 진행 지표로만 표기 | 자기채점/과적합 방지 |
| P1 lineage | prompt id, seed id, feedback action id, run id, artifact path, verdict를 연결 | 재현성과 연구 관리 개선 |
| P2 Seed coverage ledger | tick/min, 시간 bucket, 시총 bucket, 등락률 bucket, entry family, exit family별 시도/실패/성공 기록 | 넓은 탐색과 반복 편중 방지 |
| P3 typed feedback ledger | `reject`, `avoid_segment`, `tighten_threshold`, `relax_threshold`, `revise_exit`, `mutate_seed`, `promote_candidate`로 action화 | 나쁜 조건식의 원인을 다음 생성에 정확히 반영 |
| P4 mutation/grid | 실패 원인을 바탕으로 threshold, seed branch, exit rule을 의도적으로 변형 | 랜덤 생성에서 데이터 주도 탐색으로 전환 |
| P5 dashboard/runbook | coverage debt, action history, OOS status, 다음 추천 작업을 표시 | 연구 관리와 의사결정 속도 개선 |

## 7. Seed가 가장 중요한가?

| 질문 | 답 |
|---|---|
| Seed가 중요한가 | **중요하다.** 초기 seed가 좁으면 AI는 좁은 공간에서만 실패를 반복한다. |
| Seed가 가장 중요한가 | **단독 1순위는 아니다.** seed breadth, feedback policy, OOS gate, mutation ledger가 같이 있어야 한다. |
| 현재 seed 문제 | 다밴드 생성은 가능해졌지만 coverage debt가 없어 어떤 시간/시총/등락률/family를 얼마나 탐색했는지 관리가 약하다. |
| 좋은 seed 조건 | 처음부터 tick/min, 5분 시간 bucket, 시총 tier, 등락률 regime, entry family, exit family를 넓게 분산해야 한다. |
| 나쁜 seed 조건 | 검증된 anchor 근처만 반복하거나, 09:00~09:05 같은 좁은 시간대에 고착되는 구조다. |

| Seed Coverage 축 | 필요한 기록 | 개선 방향 |
|---|---|---|
| timeframe | tick/min 분리, OOS 정책 | tick은 honest OOS 중심, min은 오염 여부를 별도 표기 |
| time bucket | 09:00~09:30 5분 bucket | unexplored bucket 우선 배정 |
| market-cap bucket | small/mid/upper/large | 한 cap tier 반복 방지 |
| change bucket | flat/low/mid/high momentum | 홍수형 등락률 구간 회피 |
| entry family | normalized structure hash | 같은 아이디어 이름만 바꿔 반복 금지 |
| exit family | stop/trail/time/MFE/MAE family | 청산 실패를 별도 mutation 대상으로 관리 |

## 8. Buy-Side 진단 폐루프

| Buy 실패 유형 | 진단 근거 | 다음 action |
|---|---|---|
| 홍수형 진입 | 거래수 과다, q1/q2 큰 음수 | `reject` 또는 liquidity/change threshold 강화 |
| 특정 시간대 손실 | time segment total_profit < 0 | `avoid_segment(time_bucket)` |
| 특정 시총 손실 | cap bucket win-rate 저하 | cap 범위 변경 또는 해당 cell 회피 |
| 임계값이 낮음 | 승자 B_* 분위수가 더 높은 곳에 몰림 | `tighten_threshold` |
| 임계값이 높음 | 거래수 부족, near-miss 존재 | 제한적 `relax_threshold` |
| 중복 idea | 구조 hash가 최근 실패 family와 동일 | duplicate reject 또는 family 변경 |

## 9. Sell-Side 진단 폐루프

| Sell 실패 유형 | 진단 근거 | 다음 action |
|---|---|---|
| giveback 과다 | MFE 대비 realized return 낮음 | MFE lock 또는 trailing 개선 |
| 손실 방치 | loser MAE가 깊음 | MAE cut 또는 빠른 손절 |
| 손실 보유시간 과다 | losers hold longer than winners | time-stop 강화 |
| 특정 매도조건 손실 집중 | sell-rule avg_return 최저 | 해당 sell family mutate/demote |
| 진입 edge는 있으나 실현 낮음 | edge ratio 양호, payoff 낮음 | exit capture 중심 mutation |
| 너무 빠른 익절 | winners MFE 발전 전 매도 | 최소 보유/완화 조건 검토 |

## 10. Typed Feedback Ledger 설계

| action | 언제 생성 | 다음 생성 반영 |
|---|---|---|
| `reject` | 구조 자체가 홍수/과적합/중복 | 같은 family 반복 금지 |
| `avoid_segment` | 특정 시간/시총/등락률 cell 손실 | 해당 cell 회피 또는 더 강한 filter 요구 |
| `tighten_threshold` | 승자 분위수가 더 엄격한 조건에 집중 | threshold 상향 후보 제공 |
| `relax_threshold` | 거래수 부족이나 adjacent near-miss | 제한적 완화 후보 제공 |
| `revise_exit` | giveback, MAE, hold, sell-rule 손실 | 매도식 family 변경 |
| `mutate_seed` | seed coverage debt 또는 실패 family | 다른 bucket/family로 분기 |
| `preserve_anchor` | 전체기간/OOS 생존 또는 검증 anchor | anchor quota로 유지 |
| `promote_candidate` | OOS/WF 통과 | 후보 pool/운영 검토로 승격 |

## 11. P0-P5 업데이트 로드맵

| Phase | 목표 | 먼저 해야 하는 이유 | 완료 기준 |
|---|---|---|---|
| P0 | metric/gate freeze | 성공 기준이 흔들리면 이후 모든 학습이 자기기만이 된다. | OOS/WF count만 success로 표시 |
| P1 | lineage/report reliability | 좋은/나쁜 후보의 원인을 재현해야 학습된다. | prompt/seed/feedback/run/artifact/verdict 연결 |
| P2 | Seed coverage ledger | 초반 탐색 공간이 넓어야 좋은 후보가 나올 가능성이 생긴다. | coverage debt 기반 batch 생성 |
| P3 | Buy/Sell typed feedback | 실패 원인을 다음 생성에 구조적으로 반영해야 한다. | buy/sell action record 생성 |
| P4 | mutation/grid/coarse-to-fine | 랜덤 생성이 아니라 실패 원인 기반 변형이 필요하다. | action별 mutation 후 재검증 |
| P5 | dashboard/runbook | 연구가 커질수록 관리와 판단 근거가 필요하다. | coverage/action/OOS 패널과 보고서 자동화 |

## 12. 다음 `$start-work` 권장 범위

| 추천 scope | 목적 | 포함할 작업 |
|---|---|---|
| `$start-work condition-self-improvement-p0-p2-implementation-20260615` | metric, lineage, seed coverage부터 구현 | OOS metric freeze, prompt/action lineage 설계, seed coverage ledger |
| `$start-work condition-self-improvement-p3-feedback-ledger-20260615` | P0-P2 이후 typed feedback 구현 | Buy/Sell diagnosis action, feedback ledger, mutation input |

## 13. 최종 판단

| 판단 | 내용 |
|---|---|
| 연구 관리는 잘되고 있나 | 최근 evidence, preregistration, gate 문서가 생겨 관리 수준은 좋아졌다. 다만 prompt/action lineage가 완전하지 않아 "왜 개선됐는지" 추적은 아직 부족하다. |
| AI가 스스로 개선 중인가 | 부분적으로 그렇다. stateful feedback이 proxy smoke-pass를 개선했다. 하지만 OOS가 0이라 "좋은 조건식으로 개선됐다"는 증거는 아직 없다. |
| 가장 먼저 고칠 것 | seed coverage ledger와 typed feedback ledger다. 이 둘이 없으면 나쁜 조건식의 교훈이 다음 좋은 조건식으로 안정적으로 전달되지 않는다. |
| 개발 방향 | 더 많은 프롬프트보다, "어떤 실패를 어떤 action으로 바꾸고 어떻게 재검증했는가"를 기록하는 연구 시스템을 먼저 강화해야 한다. |
