# 알파 랩 AI 코드 에이전트 핸드오프 — 초기 5아이디어 재검토 문서 패키지 (2026-07-09)

> 대상 독자: Codex, Claude, GJC, 기타 AI code agent.
> 목적: 새 세션이 이전 대화 맥락 없이도 알파 랩 초기 5개 아이디어의 목적, 실패 원인, 현재 산출물, 다음 작업, 추천 작업, 금지 작업을 빠르게 복원하도록 한다.
> 범위: 본 핸드오프는 documentation/research handoff다. 엔진 실행, 백테스트 실행, DB 쓰기, 전략 등록, 런타임 변경을 승인하지 않는다.

---

## 0. 가장 먼저 읽을 결론

현재 알파 랩의 핵심 결론은 다음이다.

1. 초기 5개 아이디어의 공통 목적은 기존 `조건식 생성 → 백테스트 채점` 루프의 병목을 깨고, **데이터가 먼저 말하게 하는 역방향 발굴**로 STOM 수익 조건식 또는 시드 공급원을 만들려는 것이었다.
2. 실제 실행 결과, **데이터에서 새 단독 매수 조건식을 직접 캐내는 축(Idea1/2/3)은 deployable alpha를 만들지 못했다.**
3. **Idea5의 전역 청산 교체도 실패했다.** `hard_stop -5 + time_stop 300`은 리플레이에서는 좋아 보였으나 엔진 확인에서 CI 0 포함, 2024/2025 역전, MDD 5창 중 4창 악화로 기각됐다.
4. **Idea4의 adaptive timing/regime rotation도 실패했다.** v4에서 살아남은 것은 레짐 타이밍이 아니라 검증 챔피언 4종의 **정적 1/4 등가중 다각화**다.
5. 현재 증거상 “수익형 STOM 조건식”에 가장 가까운 자산은 새 단독 조건식이 아니라, `RR8_12`, `RR8_0`, `RR8_21`, `GPTAUTH_G8` 원문 조건식을 각 1/4 고정 비중으로 운용하는 **v4 정적 등가중 챔피언 앙상블**이다.
6. 2025-01~2026-02 성과는 이제 알려진 감사 증거다. 향후 연구에서 이를 `fresh blind OOS`로 다시 주장하면 안 된다.
7. 이 문서 패키지와 핸드오프는 **미래 연구의 안전장치**다. 새 수익 조건식을 이미 증명한 문서가 아니다.

---

## 1. 현재 브랜치와 작업 상태

| 항목 | 현재 값 / 해석 |
|---|---|
| 작업 브랜치 | `research/alpha-lab-idea5-foundation-20260707` |
| 직전 HEAD | `5ec0a780` — `아이디어5 재연구 토대를 추가한다` |
| 이번 핸드오프의 목적 | 이전 Ultragoal/Ralplan 실행으로 만든 6개 문서 패키지를 후속 AI agent가 다시 이해하고 이어갈 수 있게 고정 |
| 이번 커밋 포함 대상 | 새 synthesis 문서 1개, idea별 상세 문서 5개, 이 AI agent handoff 문서 1개 |
| 명시적 제외 | `.gjc/`, `.omo/evidence/tmap-walkforward/_discovery_feedback.txt`, protected/runtime/data 경로 |
| 작업 성격 | docs-only, research handoff |
| 완료 상태 | Ultragoal `G001`은 이전 실행에서 durable checkpoint `complete` 처리됨. 단 `.gjc` 런타임 상태는 repo source가 아니므로 후속 agent는 문서와 git commit을 기준으로 판단해야 함 |

---

## 2. 이번 문서 패키지의 파일 목록

이번 작업의 핵심 산출물은 아래 7개 파일이다. 첫 6개는 초기 5아이디어 재검토 패키지이고, 마지막 1개가 현재 핸드오프다.

| 번호 | 파일 | 역할 | 후속 agent가 읽을 때의 관점 |
|---:|---|---|---|
| 1 | `docs/research/condition_research/plans/2026-07-07_alpha_lab_initial_five_synthesis_to_profitable_stom_conditions.md` | 전체 종합 문서 | 가장 먼저 읽는다. 전체 결론, evidence timeline, claim ledger `C-001`~`C-015`, roadmap, invalid claims가 있다. |
| 2 | `docs/research/condition_research/plans/2026-07-07_alpha_lab_idea1_rule_mining_failure_improvement_reuse.md` | Idea1 규칙 채굴 상세 | lift/ranking과 EV 혼동, fixed-horizon label mismatch, standalone buy-expression 실패를 이해한다. |
| 3 | `docs/research/condition_research/plans/2026-07-07_alpha_lab_idea2_event_study_failure_improvement_reuse.md` | Idea2 이벤트 스터디 상세 | 42,363 events / 138 cells / FDR survivor 0의 clean negative를 이해한다. |
| 4 | `docs/research/condition_research/plans/2026-07-07_alpha_lab_idea3_microstructure_layer_failure_improvement_reuse.md` | Idea3 미시구조 레이어 상세 | 346 samples < 2,000 minimum으로 success/fail 모두 과잉 판정 금지라는 상태를 이해한다. |
| 5 | `docs/research/condition_research/plans/2026-07-07_alpha_lab_idea4_regime_gate_failure_improvement_reuse.md` | Idea4 레짐 게이트 상세 | adaptive timing/regime rotation 실패와 static equal-weight만 생존했다는 결론을 이해한다. |
| 6 | `docs/research/condition_research/plans/2026-07-07_alpha_lab_idea5_champion_exit_failure_improvement_reuse.md` | Idea5 챔피언 청산 상세 | replay는 triage, engine은 final judge라는 원칙과 P5 global exit rejection을 이해한다. |
| 7 | `docs/research/condition_research/plans/2026-07-09_alpha_lab_ai_agent_handoff_initial_five_docs.md` | 현재 핸드오프 | Codex/Claude/GJC가 다음 세션에서 현재 상태와 추천 작업을 복원하는 색인이다. |

관련 선행/근거 문서는 다음 순서로 읽으면 된다.

| 우선순위 | 문서 | 이유 |
|---:|---|---|
| 1 | `docs/research/condition_research/plans/2026-07-07_alpha_lab_master_handoff_ideas_to_deployment.md` | 초기 5아이디어부터 v4/v5까지 전체 역사와 배포 자산을 이미 압축한 마스터 핸드오프 |
| 2 | `docs/research/condition_research/plans/2026-07-07_alpha_lab_initial_five_synthesis_to_profitable_stom_conditions.md` | 이번 6문서 패키지의 중심 문서 |
| 3 | `docs/research/condition_research/plans/2026-07-07_alpha_lab_idea5_research_foundation.md` | 현재 브랜치의 출발점. Idea5를 앞으로 어떻게 살릴지 별도 연구 토대 제공 |
| 4 | `docs/research/condition_research/research_runs/alpha_lab_20260705/p5_engine_confirmation.md` | P5 전역 청산 교체 기각의 직접 근거 |
| 5 | `docs/research/condition_research/research_runs/alpha_lab_v4_20260707/v4_final_verdict.md` | v4 정적 등가중 성공과 adaptive/regime 실패의 직접 근거 |
| 6 | `docs/update_log/2026-07-07_alpha_lab_v4_supervised_deployment_protocol.md` | v4 감독형 운용 조건, kill-switch, no optimization 제약 |

---

## 3. 초기 5개 아이디어의 원래 목적과 실제 판정

초기 5개 아이디어는 모두 같은 병목에서 나왔다. 기존 자율 루프는 `조건식 생성 → 백테스트 채점` 구조였고, 콜드 LLM 생성은 통과율이 낮았으며, 인간 시드 공급이 병목이었다. 그래서 백테스트를 탐색기의 반복 평가자가 아니라 **최종 심판**으로 낮추고, 발견을 tick DB·거래 원장·사건 통계 같은 오프라인 계산으로 옮기려 했다.

| 아이디어 | 원래 목적 | 원래 원리 | 실제 판정 | 지금 남길 것 | 버릴 것 / 금지 |
|---|---|---|---|---|---|
| Idea1 규칙 채굴 | 조건식을 사람이/LLM이 지어내는 대신 데이터에서 직접 캐내기 | 전수 `(종목,초)` 격자에 미래 라벨 부착 → 얕은 트리 → STOM 문법 번역 | 실패. lift/ranking 신호는 있었지만 단독 매수식 경제성 없음. v3 EV 채택 0 | ranking compass, negative map, 번역/피처 패리티 인프라 | lift 높은 규칙을 곧바로 profitable buy condition으로 주장 |
| Idea2 이벤트 스터디 | 시장 사건 뒤 조건부 수익 분포 측정 후 생존 사건만 조건식화 | VI해제·신고가·거래대금서지 등 사건을 사전등록하고 FDR/placebo로 검정 | clean negative. 42,363 events, 138 cells, FDR survivors 0 | event-as-context, champion trade tag, FDR gate template | raw non-FDR EV cell을 시드로 되살리기 |
| Idea3 미시구조 레이어 | 호가/잔량/체결 흐름을 챔피언 위 손실꼬리 필터로 사용 | 챔피언 거래 원장 재조인 → MFE/MAE/loss-tail 조건부 lift | 판정보류. 346 samples < sealed minimum 2,000 | 표본 하한 규율, champion-only overlay 원칙, residual-path label 요구 | 346표본으로 성공/실패 확정 주장, 독립 트리거화 |
| Idea4 레짐 게이트 | 어느 날 어떤 전략을 켜고 끌지 결정하는 상위 운영 규칙 | 일 단위 breadth/churn/VI 등 시장 상태 → full/half/off/rotation | 자동 selector/rotation 실패. static equal-weight만 성공 | 위험 경보, 운영 체크리스트, sizing cap 검토 | adaptive timing, regime rotation, 비중 최적화 성공 주장 |
| Idea5 챔피언 청산/증류 | OOS 통과 챔피언 원장에서 진입 필터와 청산 개선 찾기 | tick 경로 반사실 replay로 hard-stop/time-stop/trailing 등 평가 | 전역 청산 교체 기각. replay gate는 유용하지만 최종 심판 아님 | replay triage, incumbent sell baseline, 조건부 패치 연구 | `hard_stop -5 + time_stop 300` 채택, replay만으로 성공 확정 |

---

## 4. Canonical claim ledger 요약

세부 claim은 synthesis 문서 Appendix A의 `C-001`~`C-015`를 기준으로 삼는다. 후속 agent는 아래 claim을 바꾸면 안 된다.

| Claim | 핵심 내용 | 후속 작업에서의 사용법 |
|---|---|---|
| C-001 | 초기 점수: rule mining 83, event study 82, microstructure 77, regime gate 71, champion exit 75 | 점수는 착수 우선순위일 뿐 성능 증거가 아니다. |
| C-002 | 공통 원칙: offline discovery, backtest/engine as final judge | 오프라인 결과를 최종 성능으로 포장하지 않는다. |
| C-003 | cycle 1은 인프라와 durable negative assets를 남겼지만 deployable alpha는 없었다 | 실패 산출물은 재사용 가능하지만 배포 후보가 아니다. |
| C-004 | Idea1/P1은 ranking/lift signal은 있었지만 standalone buy rules는 unprofitable | lift/ranking을 EV로 오해하지 않는다. |
| C-005 | v3 EV mining positive-EV adopted rules/leaves 0; data-first mining v1/v2/v3 실패 | 데이터-우선 단독 매수식 채굴은 현재 증거에서 종결. |
| C-006 | Idea2/P2 42,363 events, 138 cells, FDR survivors 0 | 이벤트 raw cell 재활용 금지. |
| C-007 | Idea3/P3 346 samples < sealed minimum 2,000, inconclusive | 성공/실패 과잉 판정 금지. |
| C-008 | P5 replay gate는 강했지만 global exit candidate는 engine confirmation에서 rejected | replay를 최종 증거로 쓰지 않는다. |
| C-009 | P5 기각 사유: CI crosses zero, 2024/2025 reversal, MDD worsened 4/5; incumbent sell baseline | 현직 매도식 전역 교체 금지. |
| C-010 | v4 equal-weight 4-champion ensemble: profit ~2,608,362, MDD ~493,590/493,591, calmar ~5.28 | 현재 수익형 후보의 기준 숫자. |
| C-011 | v4 success는 static equal-weight diversification; adaptive timing/single adaptive/regime rotation 실패 | v4 성공 원인을 타이밍/레짐으로 오해하지 않는다. |
| C-012 | v4 감독형 프로토콜: fixed 1/4, no optimization, small supervised, kill-switch ~740k, future revalidation | 배포/GUI 검증/운용 논의의 제약. |
| C-013 | 2025-01~2026-02는 known/audit evidence이지 future fresh blind OOS가 아니다 | 새 연구 OOS 오염 방지. |
| C-014 | Future Idea5는 replay를 triage로 취급하고 engine confirmation을 final judge로 둬야 한다 | 청산 연구 재개 시 핵심 gate. |
| C-015 | 이번 documentation package는 source/DB/engine/strategy registration을 승인하지 않는다 | docs-only 범위 유지. |

---

## 5. 지금까지 진행된 작업과 성과

이번 브랜치에서 이어진 작업은 두 층으로 나뉜다.

### 5.1 먼저 완료된 Idea5 foundation

`5ec0a780`에서 `2026-07-07_alpha_lab_idea5_research_foundation.md`가 추가됐다. 이 문서는 초기 5아이디어를 다시 보고, 특히 Idea5를 앞으로 효과 있게 만들려면 전역 청산 교체가 아니라 **조건부 청산 패치·병렬 변종·포트폴리오 MDD 감소**로 연구 문제를 축소해야 한다고 고정했다.

핵심 성과는 다음이다.

| 항목 | 내용 |
|---|---|
| P5 기존 결론 보존 | `hard -5 + time 300` 전역 교체는 기각 상태로 유지 |
| 새 연구 질문 | incumbent sell의 load-bearing 절, time_stop 300의 도움/해로움 조건, 포트폴리오 MDD 개선, replay triage 재사용 |
| 연구 프로그램 | Idea5-R R0~R5: 실패 포렌식, preregistration, 후보군 4종 제한, 엔진 판정 기준, 채택 형태 우선순위 |
| 즉시 규율 | 새 후보는 새 봉인+n_trials, 2025-01~2026-02 fresh OOS 재사용 금지, replay 최종 증거 금지 |

### 5.2 이어서 완료된 초기 5아이디어 문서 패키지

사용자가 Ralplan/Ultragoal로 승인한 docs-only 계획에 따라 6개 문서가 작성됐다. 목적은 각 아이디어를 하나씩 자세히 실패 원인 분석하고, 개선 방향과 다시 사용할 방법을 고정하는 것이었다.

| 산출물 | 달성한 것 |
|---|---|
| 종합 문서 | 전체 결론, evidence timeline, final verdict table, common root causes, reuse asset map, future approval gates, invalid claims, cross-link index, canonical claim ledger 작성 |
| Idea1 문서 | rule mining 실패를 lift/ranking vs EV, fixed-horizon label mismatch, engine firing mismatch 관점으로 정리 |
| Idea2 문서 | event study clean negative와 raw cell revival 금지, event-as-context만 허용하는 재사용 경계 정리 |
| Idea3 문서 | sample-limited inconclusive 상태와 residual-path labels, dedup cohort, portfolio-MDD objective 필요성 정리 |
| Idea4 문서 | adaptive timing/regime rotation 실패와 fixed 1/4 static equal-weight baseline 유지 원칙 정리 |
| Idea5 문서 | replay vs engine 차이, incumbent sell baseline, 조건부/병렬 청산 연구로의 축소 방향 정리 |

---

## 6. 후속 agent가 대화형으로 설명할 때 쓸 쉬운 체계

사용자가 “문서에 뭐가 담겼나”라고 물으면 다음 순서로 설명하면 된다.

1. **전체 방향 전환**: 새 단독 조건식 발명에서 검증 챔피언의 단순·견고한 조립으로 방향이 바뀌었다.
2. **실패의 가치**: Idea1/2/3/P5의 실패는 버릴 쓰레기가 아니라, 다시 밟지 말아야 할 탐색 공간을 표시한 negative map이다.
3. **v4의 성공 원인**: 레짐 타이밍이나 최적화가 아니라, 4개 챔피언의 손익 비동조를 이용한 정적 1/4 등가중이다.
4. **Idea5의 재활성화 조건**: 현직 매도식 전역 교체가 아니라, 조건부 time-stop, 국소 threshold, 병렬 변종, cross-champion loss-tail veto로만 재개한다.
5. **OOS 규율**: 2025-01~2026-02는 이제 known/audit evidence다. 향후 fresh OOS는 2026-03 이후 같은 새 데이터여야 한다.
6. **실행 금지**: 이 문서들만으로 engine/backtest/DB/source/strategy registration을 하면 안 된다. 별도 승인과 사전등록이 필요하다.

---

## 7. 다음 작업 후보

아래는 추천 작업 목록이다. 우선순위는 “증거를 더럽히지 않고 다음 연구를 열 수 있는가” 기준이다.

| 우선순위 | 작업 | 목적 | 산출물 | 실행 전 조건 | 주의점 |
|---:|---|---|---|---|---|
| 1 | 이번 문서 패키지 커밋 확인 | 후속 agent가 untracked docs를 놓치지 않도록 git history에 고정 | 한국어 커밋 1개 | 현재 작업트리에서 docs 파일만 명시 stage | `.gjc/`, `.omo/...`는 stage 금지 |
| 2 | 문서 기반 브리핑 생성 | 사용자/agent에게 현재 결론을 쉽게 설명 | 1~2페이지 요약 또는 대화형 답변 | 새 파일 생성은 사용자 요청 시만 | 새 성능 claim 금지 |
| 3 | Idea5-R R1 실패 포렌식 설계 | 기존 산출물만 읽어 P5 실패를 구조화 | `idea5_failure_forensics` 계획 또는 read-only report | 별도 승인 권장. 엔진 0회/read-only로 제한 | 2025-01~2026-02 fresh OOS 금지 |
| 4 | incumbent sell attribution 설계 | 현직 매도식의 load-bearing 절 식별 | clause attribution report 계획 | 기존 CSV/문서 read-only 범위 확정 | 절 순서/의미론을 바꾸지 말 것 |
| 5 | v4 GUI 감독형 검증 준비 | 사용자가 STOM GUI에서 4챔피언 등가중 재현 | 체크리스트/운영 노트 | 사용자 GUI/데이터 환경 필요 | DB/전략 등록은 별도 승인 필요 |
| 6 | v6 비상관 전략 후보 선별 | rr8/GPTAUTH 이외 실행 가능한 신규 후보 찾기 | 후보 API 호환성 필터 | 현행 엔진 API compatibility 먼저 확인 | v5처럼 구식 API 후보를 반복하지 말 것 |

---

## 8. 권장 재개 루틴

새 AI code agent가 이 브랜치에서 이어받으면 다음 순서로 진행한다.

### 8.1 문맥 복원

1. `AGENTS.md`와 `docs/AGENTS.md`를 읽는다.
2. 현재 브랜치가 `research/alpha-lab-idea5-foundation-20260707`인지 확인한다.
3. 이 문서와 synthesis 문서를 읽는다.
4. 작업 성격이 docs-only인지, research-only인지, engine execution인지 구분한다.
5. `.gjc/` 런타임 상태에 의존하지 말고 git-tracked docs를 기준으로 판단한다.

### 8.2 설명 요청 대응

사용자가 설명을 요청하면 다음 형태로 답한다.

- 먼저 한 문장 결론: “새 단독 조건식 채굴은 실패했고, 검증 챔피언 정적 등가중이 현재 증거상 최선이다.”
- 그 다음 5개 아이디어별로 `목적 → 실패 원인 → 살릴 것 → 금지할 것 → 다음 연구` 순서로 설명한다.
- 숫자는 claim ledger에 있는 값만 사용한다.
- `fresh OOS`, `P5 success`, `regime timing success`, `v4 weight optimization` 같은 표현은 반드시 부정 맥락으로만 사용한다.

### 8.3 새 연구 요청 대응

새 연구 실행 요청이 오면 다음 gate를 적용한다.

| Gate | 확인 질문 | 통과 기준 |
|---|---|---|
| 범위 | docs-only인가, read-only 분석인가, engine/backtest/DB 실행인가 | engine/backtest/DB/source는 별도 승인 필요 |
| 데이터 | 2025-01~2026-02를 fresh OOS로 쓰려는가 | 쓰려면 실패. known/audit evidence로만 표기 |
| 가설 | 기존 실패 공간과 무엇이 다른가 | C-001~C-015와 대조한 차별점 필요 |
| 봉인 | success/fail, n_trials, 표본 하한이 측정 전 고정됐는가 | 사전등록 전 측정 금지 |
| 판정 | 오프라인 결과를 최종 증거로 주장하는가 | 최종은 engine confirmation 또는 future data verification |

---

## 9. 절대 하면 안 되는 일

아래 행동은 이 핸드오프와 문서 패키지의 결론을 깨뜨린다.

1. `hard_stop -5 + time_stop 300`을 다시 채택 후보로 권고한다.
2. replay 통과를 engine success로 표현한다.
3. v4 성공을 adaptive timing 또는 regime rotation 성공이라고 말한다.
4. v4 4챔피언 비중을 최적화하거나 파라미터 조정해도 된다고 말한다.
5. 2025-01~2026-02를 향후 fresh blind OOS라고 부른다.
6. Idea1/2/3의 실패 산출물을 deployable alpha라고 부른다.
7. 346개 MCL 표본으로 성공/실패를 확정한다.
8. FDR survivor 0인 이벤트 셀을 raw EV 기준으로 되살린다.
9. 이 문서만으로 DB 쓰기, strategy registration, engine/backtest run, runtime/source edit을 진행한다.
10. `.gjc/` runtime state를 repo-visible source of truth로 취급한다.

---

## 10. 검증 체크리스트

이번 문서 패키지를 검증할 때는 다음을 확인한다.

| 검증 항목 | 기대 결과 |
|---|---|
| 파일 존재 | synthesis 1개 + per-idea 5개 + handoff 1개 존재 |
| per-idea 구조 | 각 idea 문서에 `Verdict`, `Evidence claims`, `Failure/root cause`, `Reusable assets`, `Disallowed claims`, `Future hypotheses requiring approval` 존재 |
| synthesis ledger | `C-001`~`C-015` 전부 존재 |
| cross-link | synthesis가 5개 per-idea docs를 가리키고, 각 per-idea doc이 synthesis를 가리킴 |
| invalid claim | fresh OOS 2025, P5 success, regime timing succeeded, optimize v4 weights 등은 긍정 claim으로 등장하지 않음 |
| scope | diff가 docs 파일만 포함하고 protected/runtime/data 경로가 비어 있음 |
| whitespace | `git diff --check` 통과 |
| commit discipline | `git add -A` 금지, 대상 파일만 명시 stage, commit message는 한국어 title/body |

검증 예시 명령은 다음과 같다. 실제 실행 시에는 shell 검색 대신 전용 `search`/`find`/`read` 도구를 우선 사용하고, bash는 git/python 검증에만 사용한다.

```powershell
git diff --check -- docs/research/condition_research/plans/2026-07-07_alpha_lab_initial_five_synthesis_to_profitable_stom_conditions.md docs/research/condition_research/plans/2026-07-07_alpha_lab_idea1_rule_mining_failure_improvement_reuse.md docs/research/condition_research/plans/2026-07-07_alpha_lab_idea2_event_study_failure_improvement_reuse.md docs/research/condition_research/plans/2026-07-07_alpha_lab_idea3_microstructure_layer_failure_improvement_reuse.md docs/research/condition_research/plans/2026-07-07_alpha_lab_idea4_regime_gate_failure_improvement_reuse.md docs/research/condition_research/plans/2026-07-07_alpha_lab_idea5_champion_exit_failure_improvement_reuse.md docs/research/condition_research/plans/2026-07-09_alpha_lab_ai_agent_handoff_initial_five_docs.md

git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json _v3k_sidecar/v3k_gui_settings.json
```

---

## 11. 후속 작업별 권장 의사결정

| 사용자 요청 | 권장 반응 | 이유 |
|---|---|---|
| “문서 내용 설명해줘” | synthesis → idea별 docs 순서로 설명 | 이미 충분한 docs가 있으므로 추가 실행 불필요 |
| “Idea5 다시 살려봐” | 먼저 Idea5-R R1 read-only 실패 포렌식 계획/문서부터 제안 | 전역 청산 교체는 기각됐고 새 측정은 사전등록 필요 |
| “백테 바로 돌려” | 별도 승인/사전등록/범위 정의 전에는 거절 또는 Ralplan | 현재 패키지는 engine/backtest 실행 승인 아님 |
| “v4 배포해” | supervised deployment protocol과 GUI 검증 게이트를 안내 | v4는 자동 배포가 아니라 감독형 후보 |
| “2025 OOS 다시 쓰자” | known/audit evidence로만 가능하다고 정정 | OOS 오염 방지 |
| “레짐으로 켜고 끄자” | 자동 selector 금지, 위험 경보/체크리스트로 축소 | adaptive/regime rotation 실패 기록 존재 |
| “새 조건식 만들어” | `utility/ai_agent/strategy.txt`/`rules.txt` read-first 및 별도 승인 필요 | 전략 생성 규칙과 branch policy 준수 필요 |

---

## 12. 커밋/작업트리 주의사항

이번 요청은 “핸드오프 문서 작성 후 커밋”이다. 따라서 커밋에는 아래 문서 파일만 들어가야 한다.

```text
docs/research/condition_research/plans/2026-07-07_alpha_lab_initial_five_synthesis_to_profitable_stom_conditions.md
docs/research/condition_research/plans/2026-07-07_alpha_lab_idea1_rule_mining_failure_improvement_reuse.md
docs/research/condition_research/plans/2026-07-07_alpha_lab_idea2_event_study_failure_improvement_reuse.md
docs/research/condition_research/plans/2026-07-07_alpha_lab_idea3_microstructure_layer_failure_improvement_reuse.md
docs/research/condition_research/plans/2026-07-07_alpha_lab_idea4_regime_gate_failure_improvement_reuse.md
docs/research/condition_research/plans/2026-07-07_alpha_lab_idea5_champion_exit_failure_improvement_reuse.md
docs/research/condition_research/plans/2026-07-09_alpha_lab_ai_agent_handoff_initial_five_docs.md
```

기존 미추적 항목인 `.gjc/`와 `.omo/evidence/tmap-walkforward/_discovery_feedback.txt`는 사용자/런타임 산출물로 보존하고 stage하지 않는다.

커밋 메시지는 프로젝트 규칙에 따라 한국어 제목과 한국어 markdown 본문을 사용한다.

---

## 13. 최종 한 줄 핸드오프

이 브랜치의 현재 작업은 **초기 5개 알파 아이디어를 실패 포함 연구 자산으로 재정리하고, 후속 AI agent가 같은 실패를 반복하지 않도록 synthesis/per-idea/handoff 문서 패키지를 고정하는 것**이다. 다음 실험은 곧바로 엔진을 돌리는 것이 아니라, claim ledger와 approval gates를 기준으로 별도 사전등록된 read-only/triage 연구부터 시작해야 한다.
