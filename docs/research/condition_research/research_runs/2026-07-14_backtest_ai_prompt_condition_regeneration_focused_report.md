# 백테스트 분석 기반 AI 조건식 재생성 경로 집중 연구보고서

| 항목 | 내용 |
|---|---|
| 기준 커밋 | `bb41ae4ee4e15f4a0f2f98d63df1e6cb43aa738c` |
| 연구 브랜치 | `research/v4-condition-process-audit-20260714` |
| 상위 심층 보고서 | `2026-07-14_v4_condition_process_audit_improved_report.md` — 본 집중 경로 감사의 companion·상위 프로세스 결론 |
| 보고서 불변 기준 | 초기 보고서의 불변 비교 기준은 최초 보고서 커밋 `3f7cb1d634f4a53e08122baad5784a73ebec02f2`이며, 코드 감사 기준 `bb41ae4…`에는 해당 보고서가 아직 존재하지 않았다. 초기 보고서 현재 blob `68822a1a4e9e4eb20eb50920bc84ac7eb3a83648`을 본 작업에서 변경하지 않는다. |
| 연구 범위 | 공식 백테스트 결과 → 분석·채점 → AI 입력 → system/user prompt → 응답 검증 → 조건식 재생성 → 다음 평가 |
| 분석 경계 | 정본 `ai_strategy_loop`와 CLI `research_loop`를 별도 경로로 감사 |
| 실행 경계 | 정적 소스·기존 산출물만 분석. provider·공식 백테스트·보호 DB/state 미접근 |
| 성과 상태 | `performance_proved=false`, `human_comparison_proved=false`, `live_authorized=false` |
| 종합 판정 | **BLOCK — AI 재생성은 작동하지만 독립 검증된 학습 폐루프는 아님** |

## 1. 핵심 결론

| 질문 | 확인 결과 | 판정 |
|---|---|---|
| 백테스트 결과가 AI에 들어가는가 | Python 분석이 자연어 autopsy·history·hint로 변환되어 다음 세대 prompt에 주입됨 | 예 |
| AI가 백테스트 원자료를 직접 분석하는가 | AI는 원 CSV를 직접 읽지 않고 조립된 요약·부검·Context Pack을 소비 | 아니오 |
| AI가 실패 원인을 인과적으로 구분하는가 | BUY/SELL 결합 결과를 규칙으로 귀속하며 공식 2×2 인과 분리가 없음 | 아니오 |
| 정본 loop와 CLI 연구가 같은가 | 출력 형식·선택·승격·fallback 의미가 다른 별도 경로 | 아니오 |
| 통계 피드백이 실제 prompt에 들어가는가 | 기본 autopsy는 들어가지만 AnalysisCardV3 directive는 정본 호출에서 비어 있음 | 부분 |
| holdout은 생성에서 격리되는가 | 동일 전체 CSV가 fitness·autopsy에 쓰인 뒤 holdout slice로 판정될 수 있음 | 아니오 |
| AI 개선 성과를 주장할 수 있는가 | fresh validation·sealed OOS·후보 identity·소비 계보가 완결되지 않음 | 불가 |

## 2. 정본 AI loop 프로세스

| 단계 | 입력 | 함수·소유자 | 출력 | 다음 소비자 | 위험 |
|---:|---|---|---|---|---|
| 1 | seed 또는 best buy/sell | `controller/loop.py::_generate_pair` | 생성 요청 | `generate_strategy` | resume 시 부모·carry 복원 불완전 |
| 2 | 규칙·부모·feedback·history | `brain/prompt.py::build_messages` | system/user messages | provider | 상충 지시·과도한 prior |
| 3 | messages | `brain/generator.py::generate_strategy` → `provider.chat` | LLM 응답 | 코드 추출 | provider 실패는 즉시 종료 |
| 4 | 응답 | `extract_code`·compile·token·scope·선택 gate | 저장 가능한 전체 전략 | state/전략 저장 | 다수 gate 기본 OFF |
| 5 | buy/sell 전략 | `controller/loop.py::run_backtest_for` 또는 warm session | `BacktestOutcome`·CSV·metrics | score/autopsy | cold/warm 성공 계약 차이 |
| 6 | metrics·CSV | `_score_outcome`, `fitness/score.py` | hard/graded fitness | best/winner | missing·NaN metric fail-open 위험 |
| 7 | 전체 CSV | `_build_feedback`, buy/sell autopsy | 자연어 feedback | 다음 세대 prompt | holdout·side 귀속 오염 |
| 8 | segment/feature/card/hypothesis | 선택 feedback builders | avoid/prefer/directive | 다음 BUY prompt | 대부분 기본 OFF·card dead |
| 9 | evidence ON 시 | evidence store consumption | prompt↔feedback FK | 감사·resume | side별 실제 소비 증명 불완전 |

## 3. CLI research loop 프로세스

| 단계 | 입력 | 함수·소유자 | 출력 | AI 여부 | 위험 |
|---:|---|---|---|---|---|
| 1 | baseline 전략·기간 | `run_research_iteration` | baseline CSV | 아니오 | candidate 기간 기본값이 동일 기간 |
| 2 | B_*·수익률 결과 | `cli/analyzer.py::analyze_result_frame` | 나쁜 구간·임계값 | 아니오 | 동일 결과로 fit·평가 |
| 3 | 분석 결과 | 결정론 condition generator | exclusion 후보 | 아니오 | fallback을 AI와 혼동 가능 |
| 4 | analysis card·gap·부모 | Context Pack builder | repair/discovery prompt | 준비 | 전문 중복·명령형 자산 혼재 |
| 5 | opt-in provider | candidate pack producer | LLM 후보팩 | **예** | `run_research_once`에는 AI 호출 없음 |
| 6 | AI 응답 | strict response validator | code+metadata | AI 출력 검증 | prompt와 assembler schema drift |
| 7 | 후보팩 실패 | deterministic fallback | 진단 후보 | 아니오 | iteration은 계속 성공 가능 |
| 8 | candidate expression | `strategy_generator.py::generate_buy_filter_strategy` | 기존 전략+제외식 | 아니오 | 전체 전략 code와 소비 계약 충돌 |
| 9 | 임시 전략 | 공식 candidate backtest | 비교·promotion | 아니오 | 동일 기간·비용/MDD gate 부족 |
| 10 | 후보 결과 | research ranking | `best_candidate` | 아니오 | promotion 실패 후보도 best 가능 |

## 4. AI 투입 지점

| 경로 | 실제 AI 호출 조건 | AI 입력 | AI 출력 | fallback |
|---|---|---|---|---|
| 정본 loop | 매 세대 `_generate_pair`가 provider를 호출 | 전체 전략 규칙, 부모 code, autopsy, history, 선택 hint | 완성된 buy 또는 sell STOM 전략 | 생성 error·재시도 |
| CLI research | `run_research_iteration` + `llm_candidate_pack_enabled=True` + provider | Context Pack, repair card 또는 discovery gap | Python code+JSON metadata 후보 | 결정론 exclusion 후보 |
| CLI single | `run_research_once` | 없음 | 없음 | 항상 결정론 |
| non-research process | LLM flag 조합에 따라 호출 가능 | 생산되지만 소비되지 않을 수 있음 | 후보팩 | 비용 낭비 가능 |

## 5. 정본 프롬프트 조립 순서

| 순서 | 섹션 | 출처 | 의도 | 신뢰 등급 | 문제 |
|---:|---|---|---|---|---|
| 1 | system prompt·variables·forbidden | `utility/ai_agent/system_prompt/v1` | 문법·보안·변수 제한 | A | research JSON 출력과 충돌 가능 |
| 2 | kind/timeframe 기본 계약 | `prompt.py` | buy/sell 정규형 | A | 전체 전략 전용 계약 |
| 3 | 계산예산·원리 가이드 | 선택 flags | 구조 유도 | C/D | 대부분 기본 OFF |
| 4 | crossover/base code | 이전 후보 | 변이 출발점 | B | untrusted code 경계 없음 |
| 5 | 거래·청산 고정 경험칙 | 코드 내 hardcoded prior | 탐색 방향 | D | 현재 run provenance 없음 |
| 6 | segment avoid | train CSV | 손실 구간 배제 | C | feature prefer와 충돌 가능 |
| 7 | feature prefer | train CSV | 우위 변수 선호 | C | 기본 OFF |
| 8 | AnalysisCardV3 | train 통계 | 안전한 directive | B/C | 현재 정본 호출에서 빈 directive |
| 9 | band seed | 채굴 artifact | threshold 힌트 | D | lookahead 가능성 고지에 의존 |
| 10 | history | 최근 세대 | 반복 실패 방지 | B/C | config window와 구현 K 불일치 |
| 11 | meta seed | 여러 run 요약 | cross-run prior | D | 오류 유형 오분류 가능 |
| 12 | hypothesis | 이전 가정 판정 | 기각 방향 회피 | C | 결과가 G+2에 반영 가능 |
| 13 | autopsy | 직전 결과 | 직접 개선 지시 | C | BUY/SELL 인과 미분리 |
| 14 | few-shot | 우수 전략 | 구조 학습 | C/D | recency·복제 편향 |
| 15 | prior error | 직전 생성 거부 | 형식 교정 | A | 실제 provider 전송 token cap 없음 |

## 6. CLI research 프롬프트 계약

| Lane | 주요 입력 | 요구 출력 | 현재 소비 | 계약 공백 |
|---|---|---|---|---|
| Repair | 부모 전문·AnalysisCard·단일 변이축 | Python 1블록+JSON metadata | candidate `expression` | prompt에 없는 `mutation_axis`를 assembler가 요구 가능 |
| Discovery | coverage gap·novelty context | Python 1블록+JSON metadata | candidate `expression` | structured novelty 축 요구 불일치 |
| 공통 | 전체 규칙 자산·권한 제한 | research-only 후보 | exclusion wrapper | “전체 전략 후보”와 “Boolean 제외식” 의미 충돌 |

## 7. 확정 결함

| ID | 우선순위 | 결함 | 근거 symbol | 영향 |
|---|---|---|---|---|
| P-AI-01 | P0 | graduation holdout 결과가 fitness·autopsy·다음 prompt에 노출 | `loop.py::_score_outcome`, `_build_feedback`, `_compute_holdout_verdict` | OOS 독립성 상실 |
| P-AI-02 | P0 | 전체 전략과 제외식 소비 계약 충돌 | `prompt.py::build_*_research_messages`, `strategy_generator.py::generate_buy_filter_strategy` | compile 실패 또는 의미 반전 |
| P-AI-03 | P1 | system은 코드만, research user는 code+JSON 요구 | `_build_system_message`, research lane builders | 정상 응답 거부 가능 |
| P-AI-04 | P1 | zero-trade 완화와 filter hard gate가 상충 | `prompt.py::build_messages`, `generator.py::generate_strategy` | 어느 지시를 따라도 실패 가능 |
| P-AI-05 | P1 | hardcoded 경험칙이 현재 증거와 provenance 없이 경쟁 | `_report_pattern_lines`, sell 기본 지침 | 잘못된 방향 고착 |
| P-AI-06 | P1 | AnalysisCardV3 directive가 정본 호출에서 비어 있음 | `loop.py::_build_analysis_card_v3`, `analysis_card.py` | 통계 안전 feedback 미소비 |
| P-AI-07 | P1 | approved-B hard enforcement가 CLI 호출에서 OFF | `condition_generator.py::expression_result_from_candidate_pack` | 미등록 변수 이동 |
| P-AI-08 | P1 | 동일 baseline에서 threshold fit·candidate 평가 | `research_loop.py` candidate 기간 fallback | 결과 누수·과적합 |
| P-AI-09 | P1 | 모든 promotion 실패여도 CLI advisory `best_candidate` 생성 가능 | `research_ranking.py`, `research_loop.py` | 실패 후보를 개선 seed로 오인할 수 있으나 정본 `run_loop` official parent 자동 소비는 미증명 |
| P-AI-10 | P1 | feedback consumption이 side별 rendered prompt를 정확히 증명하지 못함 | evidence append/consumption wiring | 학습 계보 미증명 |
| P-AI-11 | P1 | resume이 부모·history·budget·dedup·pending feedback을 완전 복원하지 않음 | `loop.py::run_loop` resume 초기화 | 재개 후 다른 후보 생성 |
| P-AI-12 | P2 | fitness 파싱 실패 시 이전 feedback이 남을 수 있음 | `loop.py` fit-is-None branch | stale 원인 재사용 |
| P-AI-13 | P2 | timeout/runtime/0거래를 양쪽 전략 문제로 복제 | backtest error feedback | 잘못된 side 교정 |
| P-AI-14 | P2 | 최종 전송 prompt가 model-aware cap으로 차단되지 않음 | context pack budget, `provider.chat(messages)` | context 초과·receipt 부정확 |

## 8. 고정 경험칙 감사

| 고정 prior | 현재 표현 | 필요한 교정 |
|---|---|---|
| give-back 70~88% | 모든 sell prompt에 사실형으로 주입 | `EmpiricalPrior`로 분리, dataset/timeframe/sample/as-of 필수 |
| 최고익 2~3% 후 손실 | 현재 run과 무관 | 적용 조건과 confidence 추가 |
| payoff 1.1 목표 | 전략군 공통 목표 | 목적함수·비용 계약별로 버전화 |
| 손실 MAE 약 2.6배 | 선택 toggle에서 사실형 | current train evidence와 충돌 시 suppress |
| 최고평가익 약 20% 실현 | 출처 hash 없음 | evidence receipt와 함께만 렌더 |
| 청산이 승패를 결정 | 인과 검증 없는 일반화 | BUY/SELL 2×2 전에는 hypothesis로만 표기 |

## 9. 실패 유형별 현재 처방과 공백

| 실패 | 현재 처방 | 잘못될 수 있는 이유 | 목표 처방 |
|---|---|---|---|
| 0거래 | BUY/SELL 조건 완화 | filter gate와 충돌, SELL 무관 | BUY 임계 완화 또는 typed BLOCKED |
| timeout | 양쪽 단순화 | engine 또는 sell 계산비용일 수 있음 | 원인 role 분리 후 해당 side만 수정 |
| runtime error | 변수·연산 회피 | 인프라 오류까지 전략 오류로 오인 | strategy/engine/provider error enum |
| 거래 부족 | 양쪽 완화 | 진입 문제를 SELL에 전달 | BUY-only directive |
| MDD 초과 | SELL 강화 | 진입 과다도 원인 가능 | 2×2 attribution 후 side 결정 |
| 음수익 | BUY+SELL 동시 변경 | 다음 결과의 인과 소실 | 한 번에 한 레버 또는 2×2 |
| fitness error | 이전 carry 유지 가능 | stale feedback | 모든 파생 carry clear·INDETERMINATE |
| holdout 실패 | 이미 full CSV가 prompt에 노출 | 누수 | train-only result identity 강제 |

## 10. 개선된 prompt·evidence 계약

| 계약 | 필수 내용 | Fail-closed 조건 |
|---|---|---|
| `PromptSpecV2` | lane, expected output kind, side, schema version, budget | system/user/parser drift |
| `CandidatePayloadV2` | `FULL_STRATEGY` 또는 `BUY_EXCLUSION_EXPR`, body hash, parent identity | consumer와 kind 불일치 |
| `EvidenceEnvelopeV2` | source/hash/dataset/split/as-of/sample/trust/side | split이 train 아님 |
| `FeedbackResolutionV2` | READY/EMPTY/BLOCKED/STALE, side, priority, incompatibility | stale·cross-side·cross-manifest |
| `CandidateIdentityV2` | run/gen/candidate/code/profile/config/data/cost/fill hashes | review/winner/export mismatch |
| `ConsumptionReceiptV2` | feedback ID, 실제 rendered prompt ID, target passport | synthetic/orphan prompt ID |
| `ResumeDecisionV2` | best/winner/parent/history/budget/dedup/pending feedback | 필드 하나라도 모호하거나 누락 |

## 11. 권장 prompt 우선순위

| 우선순위 | 자료 | 충돌 정책 |
|---:|---|---|
| 1 | 보안·문법·변수 scope | 항상 우선 |
| 2 | lane·output schema | consumer와 동일해야 함 |
| 3 | 현재 train 공식 evidence | split·hash 검증 필수 |
| 4 | 현재 parent·card·gap | candidate identity 일치 |
| 5 | 판정 hypothesis·history | stale 여부 확인 |
| 6 | provenance가 있는 empirical prior | 현재 evidence와 충돌 시 제거 |
| 7 | few-shot·일반 원리 | 구조 참고만 허용 |

## 12. 우선 연구·교정 순서

| 순서 | 연구·교정 | 성공 기준 |
|---:|---|---|
| 1 | holdout을 train 분석·prompt에서 완전 격리 | holdout 변경 시 prompt hash 불변 |
| 2 | full strategy와 exclusion expression 타입 분리 | 교차 consumer 100% side-effect 전 reject |
| 3 | system/user/parser/assembler schema 통일 | 정상 fixture가 단일 계약으로 통과 |
| 4 | failed-best·diagnostic fallback authority 분리 | promotion 실패 advisory seed의 official parent authority 0 |
| 5 | typed feedback conflict resolver | 상충 directive 동시 렌더 0 |
| 6 | hardcoded prior provenance화 | current evidence 충돌 시 자동 suppress |
| 7 | AnalysisCardV3 실제 finding·hash 배선 | card/prompt/receipt 동일 hash |
| 8 | BUY/SELL 2×2 attribution | main effect·interaction receipt 존재 |
| 9 | exact consumption·resume | 중단 전후 다음 prompt/candidate hash 동일 |
| 10 | fresh validation·sealed OOS | 별도 승인 단계에서만 성능 판정 |

## 13. 검증 실험

| 실험 | 조작 | 기대 결과 |
|---|---|---|
| Holdout taint | holdout 행 수익률/B_*만 변경 | train score·autopsy·prompt hash 불변 |
| Output-kind matrix | 2 kind × 2 consumer | 올바른 2조합만 통과 |
| Prompt conflict | zero-trade+filter gate | resolver가 단일 일관 처방 생성 |
| Prior conflict | current autopsy가 고정 prior와 반대 | 낮은 신뢰 prior가 제거됨 |
| Side attribution | BUY/Sell 2×2 arm | main effect와 interaction 분리 |
| Failed-best | 전 후보 promotion fail | official parent None, advisory seed는 별도 상태 |
| Fallback accounting | provider 없음·예외·malformed | generation mode와 exact reason 분리 |
| Resume | 각 boundary에서 crash | uninterrupted와 next prompt/candidate 동일 |
| Evidence FK | prompt logging 실패 | consumption·GO receipt 미발급 |
| Token boundary | cap-1/cap/cap+1 | provider 전송 전 결정론 차단 |

## 14. 정직한 상태

| 상태 | 값 | 이유 |
|---|---|---|
| `system_built` | 부분적으로 true | 생성·백테스트·기본 autopsy 연결 존재 |
| `learning_proved` | false | side 인과·소비·resume·fresh validation 미완결 |
| `performance_proved` | false | CL-R08 미실행 |
| `human_comparison_proved` | false | CL-R10 미실행 |
| `live_authorized` | false | export/live 승인 없음 |
| `R08_ready` | false | `R08_CONTRACT_AMENDMENT_REQUIRED` |

## 15. 재현 가능한 증거 원장

| 주장 | 근거 경로 | SHA-256 | 원본 field·구간 | 결정론적 확인 절차 | 판정 한계 |
|---|---|---|---|---|---|
| CLI promotion 실패 후보가 advisory best로 노출 | `artifacts/process-research-validation-20260701/result_engine64.json` | `288fe384a78aa2af70bf297344e2ebf7eed9d968c08972eb7c1f0baeae3f3699` | candidate result의 `selected_as_best=true`, `promotion.passed=false`, `downstream_result=rejected` 조합 | JSON에서 세 조건을 동시에 만족하는 후보를 필터링 | 정본 `run_loop` official parent 소비는 증명하지 않음 |
| 연구 성숙도 77/100, profit proof 0 | `docs/update_log/2026-07-12_g5_research_maturity_scorecard.md` | `4c0d5a19b6ec1063700c26c9357f77fd5a74de4331ca162c1819a2b375d2a15d` | `현재 점수` 표·서술의 overall 77, 수익증명 0 | 문서의 현재 점수 섹션을 고정 SHA에서 확인 | capability advisory이며 성과 증거가 아님 |
| G5 quality gate가 77점과 profit-proof 잠금을 검증 | `artifacts/g5_quality_gate.json` | `f3e46ce66883ac8d567a0728350619d6b8787e409a68cc1b756227a3a31ab1e3` | `executorQa.evidence`, `adversarialCases` | 고정 SHA JSON의 QA·red-team receipt 확인 | 당시 quality gate 증거이며 현재 수익을 재검증하지 않음 |
| lattice 후보군 0 survivor와 음수익·MDD 열위 | `docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/lattice_v3_failure_lesson_matrix_20260709.md` | `4c0a6578a34a442e3daf7c3edb2a23b9b58d4e5e7e165ef5e6c668695b45b755` | tick/min/V2 failure matrix 표 | 고정 SHA 문서의 cohort별 count·profit·MDD 열 확인 | source summary 상속값이며 본 연구에서 백테스트 재실행 안 함 |
| CSS 후속 종결 결과 reject 19·hold 2 | `artifacts/chart_sulsa_validation_20260702/plan_c_fixcall_final_summary.json` | `82abe8883a29c9d7a2cf536f3eb94d63cd41fd72e7d4f12cebac80cade6d62f5` | 최상위 count와 candidate terminal verdict | 고정 SHA JSON count를 후보 terminal verdict 합계와 대조 | 초기 중간보고를 supersede하는 후속 artifact로만 사용 |

## 16. 승인 계획과 G0 정합성

| 항목 | 값 |
|---|---|
| 승인 계획 | `.gjc/_session-019f609b-254a-7000-a30c-cdac0689122b/plans/ralplan/019f609b-254a-7000-a30c-cdac0689122b/pending-approval.md` |
| 계획 SHA-256 | `0e9cce37288eb9d05236338861d9bfeb5f72ee2fe559209e61839f0085b70be3` |
| 합의 | Architect `CLEAR/APPROVE`, Critic `OKAY`, deadline intent reconciled |
| 구조화 승인 | Ralplan approval gate에서 `Approve execution via ultragoal` 선택 |
| durable 실행 영수증 | Ultragoal ledger `plan_created` event `ea464078-0028-4dfd-bfb4-606f09b2f891`, G001~G004 |
| 권한 한계 | CL-R08~R10·provider·공식 backtest·보호 DB/state·export/live는 승인되지 않음 |

| G0 완료 기준 | 상태 | 증거 | 편차 |
|---|---|---|---|
| 분석→AI 입력→prompt→parse→재생성 symbol map | 충족 | 본 보고서 §§2~6 | 없음 |
| evidence/inference와 정본/CLI 분리 | 충족 | §§1~4, §15 | 없음 |
| initial report byte 불변 | 충족 | 기준 commit `3f7cb1d6`, blob `68822a1a…` | 코드 감사 기준 `bb41ae4…`에는 보고서가 없었음을 명시 |
| improved report companion pointer만 additive | 충족 | improved report 메타데이터 한 행 | final commit 전 SHA는 post-commit receipt에서 기록 |
| `performance_proved=false` 유지 | 충족 | §14 | 없음 |
| 제품 파일 0·docs-only commit | commit 전 검증 대기 | Git staged allowlist로 검증 예정 | commit SHA는 자기참조 방지를 위해 post-commit receipt에만 기록 |


## 17. 제한 및 금지된 해석

| 항목 | 제한 |
|---|---|
| 실행 | provider·공식 백테스트·브라우저·보호 DB/state를 실행하지 않음 |
| 인과 | 구조 결함별 수익 영향 크기는 동일예산 A/B 전 미확정 |
| 후보 성과 | 과거 후보 실패를 미래 후보의 불가능성으로 일반화하지 않음 |
| 성숙도 | 구현 성숙도 점수를 수익 증거로 사용하지 않음 |
| 승인 | 본 보고서는 CL-R08~R10, OOS, export/live 실행 권한을 부여하지 않음 |
