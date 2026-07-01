# 2026-06-30 조건식 연구 프로세스 v2 개발·연구 기록

## 상태
- 모드: research-only advisory
- 금지 유지: export=false, live=false, finalPromotion=false
- 목적: 좋은 조건식 하나를 즉시 승격하는 것이 아니라, 좋은 조건식을 만들 확률을 높이는 연구 프로세스 개선
- 핵심 보강: 조건식 전달은 id 추적에 그치지 않고, 이전 매수/매도 조건식 전문을 Research Prompt Context Pack과 prompt receipt/contract에 포함

## 개발 반영 기록
| 영역 | 반영 내용 | 근거 파일 |
|---|---|---|
| Research Prompt Context Pack | `parents.delivery_policy=full_condition_code_required_not_id_only`를 명시하고, 부모 매수/매도 조건식 전문과 sha256을 포함 | `ai_strategy_loop/brain/prompt.py` |
| 프롬프트 렌더링 | JSON Context Pack 외에 `Parent condition full-code payload` 코드블록을 렌더링하여 LLM이 id가 아니라 조건식 전문을 읽도록 함 | `ai_strategy_loop/brain/prompt.py` |
| repair/discovery 메시지 | 선택적으로 Research Prompt Context Pack 전체를 repair/discovery 프롬프트에 삽입할 수 있게 함 | `ai_strategy_loop/brain/prompt.py` |
| prompt receipt | `parent_conditions.buy/sell.code/sha256`를 기록하여 어떤 전체 조건식이 LLM 입력/평가 기록에 연결됐는지 추적 | `ai_strategy_loop/brain/prompt.py`, `cli/research_loop.py` |
| candidate pack 검증 | repair 후보는 parent id만으로는 부족하며, 부모 buy/sell 조건식 전문이 pack 또는 candidate에 있어야 유효 | `cli/condition_generator.py` |
| authority 안전 | pack-level top-level/nested `can_live`, `can_export` 등 권한 smuggling을 pack blocker로 유지 | `cli/condition_generator.py`, `tests/unit/test_condition_generator.py` |
| 결과/진단 누수 차단 | LLM 후보식의 `R_`, `S_` 결과/진단 변수 사용 차단 | `cli/condition_generator.py`, `ai_strategy_loop/brain/prompt.py` |

## 왜 id만으로는 부족한가
| 방식 | 문제 | v2 기준 |
|---|---|---|
| `parent_buy_id`, `parent_sell_id`만 전달 | LLM은 실제 논리 구조, 필터 위치, exit와 entry의 상호작용을 볼 수 없음 | id는 추적용으로만 사용 |
| 조건식 전문 전달 없음 | repair 후보가 부모 구조 보존을 주장해도 실제로 무엇을 보존했는지 확인 불가 | buy/sell 전문과 sha256을 Context Pack에 포함 |
| 분석 결과만 전달 | 어떤 조건식에서 발생한 실패인지 구조적 원인 연결이 약함 | 분석 카드 + 부모 조건식 전문 + official metrics를 동시에 전달 |
| 후보 결과만 전달 | 다음 후보가 과거 실패를 반복할 수 있음 | root-cause, avoid/prefer zone, segment contribution, parent code를 함께 전달 |

## 다음 실제 연구 실행 권장 시작점
| 역할 | 후보 | 이유 | 사용 방식 |
|---|---|---|---|
| 1차 repair seed | `rr8_12_turnover_min_902=1.5` | 4/4 OOS-style window 통과, MDD 12.87로 안정성 기준선 | 첫 repair 부모로 사용. buy/sell 전문을 반드시 추출해 Context Pack에 포함 |
| profit comparator | `rr8_21_trail_keep=0.7` | 2025 full-period profit 3,089,180로 profit leader | 직접 승격이 아니라 비교 기준과 대체 repair 부모로 보관 |
| third comparator | `rr8_0_cap_max=2500` | 상위 fallback 후보이며 다른 시총 축을 가짐 | discovery/segment 비교용 |
| GPT prior context | `human_seed_gptauth_B_gen8` | profit은 낮지만 trades/daily가 높아 coverage 정보가 있음 | 좋은 seed가 아니라 실패/coverage 분석 자료로 사용 |

## 다음 연구 실행 단계
| 단계 | 목적 | 입력 | 산출물 | 통과 기준 |
|---|---|---|---|---|
| 0. seed code resolve | id를 조건식 전문으로 변환 | 시작 seed id, sell id | parent buy/sell full code, sha256 | code 누락 시 중단 |
| 1. Context Pack 생성 | LLM 입력을 최대한 풍부하게 구성 | STOM sources, parent code, metrics, segments, root-cause | `research_context_pack` | 250k budget 이내, source/hash 존재 |
| 2. seed official replay | 부모 성능 재확인 | parent buy/sell code | full-period official backtest receipt | no-metrics/timeout/replay failure 없거나 fallback receipt |
| 3. Analysis Card v2 | 실패 원인을 생성 가능한 가설로 구조화 | official result, time/cap/regime/edge/MFE/MAE/correlation | `analysis_card_v2` | root-cause, avoid/prefer, mutation axis 명시 |
| 4. Multi-hypothesis generation | 후보 1개가 아니라 서로 다른 가설 2~3개 생성 | Context Pack + Analysis Card | candidate pack | repair 1개 이상, discovery 1개 이상, parent code 포함 |
| 5. Official candidate backtest | 후보별 실제 검증 | candidate pack | candidate receipts, official result | 모든 후보 공식 backtest 또는 실패 receipt |
| 6. Ranking/branch 선택 | 다음 연구 줄기 선택 | official metrics, rank_score, analysis cards | next branch decision | prompt score가 아니라 official result 기준 |
| 7. 다음 iteration | 한 번에 좋아질 수 없음을 전제로 반복 | best branch + reject reasons | updated analysis/prompt receipts | 단일 실패원인/단일 mutation axis 유지 |
| 8. Promotion-review | 생성 없이 evidence health만 점검 | frozen candidates | promotion-review report | C_new_candidates=0, export/live/finalPromotion=false |

## 다음 batch의 1차 후보 구성 권장
| 후보 | lane | 부모 | 가설 | 바꿀 축 | 기대 효과 | 위험 |
|---|---|---|---|---|---|---|
| A | repair | `rr8_12_turnover_min_902=1.5` | 안정 baseline에서 손실 군집 하나만 줄임 | exit/trailing 또는 특정 open-loss filter 1개 | MDD 유지/개선, profit 보존 | 거래수 감소 |
| B | repair | `rr8_12_turnover_min_902=1.5` | turnover 추가 강화는 직전 악화가 있어 피하고 다른 축을 수정 | time/cap loss segment 1개 | 손실 구간 제거 | 과도한 구간 축소 |
| C | discovery | fallback top3와 다른 coverage | 기존 rr8과 다른 feature family/market segment | coverage regime 또는 feature family | 새로운 강점 구간 발견 | overfit/저빈도 |

## 실행 원칙
1. 조건식은 id만 넘기지 않는다. id는 추적용이고, 프롬프트에는 buy/sell 전문을 넣는다.
2. 250k prompt budget 안에서는 STOM 규칙/변수/금지/예제/부모 조건식/분석 카드를 최대한 넣는다.
3. 후보는 2~3개 이상 생성하되, 서로 다른 가설이어야 한다.
4. repair는 부모 구조 보존 + 단일 실패 원인 + 단일 수정축만 허용한다.
5. discovery는 novelty gate를 반드시 통과해야 한다.
6. deterministic fallback은 진단용이며 prompt maturity credit은 0이다.
7. promotion-review는 절대 생성하지 않는다.
8. export/live/final promotion은 금지 상태를 유지한다.
