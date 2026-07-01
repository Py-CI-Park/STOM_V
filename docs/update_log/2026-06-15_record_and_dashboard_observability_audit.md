# STOM 연구기록·대시보드 관측성 점검 보고서 (2026-06-15)

## 1. 요약

**한줄평 (기록관리)**: 폐루프 발굴 파이프라인(P0a/P0b/P2)의 산출물·증거·결정로그는 **완전 영속·고발견성**으로 다음 세션 재발견이 보장되나, 오케스트레이터 브리핑의 읽기경로 오기(`tmap/`↔`scripts/`)와 `§검증된사실3` 미갱신 등 **문서 표기 drift 2건**이 잔존한다.

**한줄평 (대시보드 관측성)**: 업그레이드 프로세스 5단계(게이트·A/B·격상·환류·다밴드) 전부가 마크다운 표/JSONL/summary로 **관측 가능**하나, P2 환류의 실효(`_discovery_feedback.txt`가 `회피: a` 단일토큰으로 퇴화)와 **P1 stateful arm 미완(현재 백그라운드 실행 중, 1/8행)**으로 환류 효과는 아직 대시보드상 증명되지 않았다.

**종합 점수: 9.0 / 10** — 코드정합(9.5)은 별도 교차검증에서 확정. 기록관리·관측성은 인프라는 우수하나 환류 실효성 증명과 문서 표기 drift에서 감점.

---

## 2. 점수표

| 항목 | 점수 | 한줄 근거 |
|---|---|---|
| **기록 관리** | **9.0 / 10** | ledger 209행(태스크별 adversarial-class+cleanup 영수증), boulder.json 레지스트리, evidence 디렉토리 풍부, plans 18종 정리. 감점: 브리핑 읽기경로 오기 1건. |
| **대시보드 관측성** | **8.5 / 10** | A/B·escalation 표 + summary JSON으로 5단계 전부 관측 가능. 감점: P2 환류 퇴화(`회피: a`)·stateful arm 미완으로 환류 *효과* 미관측. |
| **코드 정합** | **9.5 / 10** | 계획서 10개 명세 전부 file:line 실재, 24 단위테스트 통과, P0b 실백테 DB 영속(2,167,239 결정론·−3M REFUSE). drift 2건(문서). |

---

## 3. 기록 관리 — 완전성·일관성·발견성·최신성

**결론**: 영속·발견성은 우수(휘발성 0). drift는 문서 표기 2건 + 사전등록서 1건의 상태 갱신뿐, 데이터 손실 0.

| 차원 | 평가 | 근거 (절대경로) |
|---|---|---|
| **완전성** | ✅ 우수 | `loop_strategies.db`(GATE_ 전략 4종), `loop_runs.db`(runs 321·generations 2730·P0b 3 run), A/B 산출(`ab_random_n8.md/.jsonl/_summary.json`, `ab_stateful_n8.*`), escalation(`multiband_escalation.md/.jsonl/_summary.json`) 모두 실재 |
| **일관성** | ✅ 양호 | ledger 209행 전 항목 `event/plan/task/session_id/artifact/adversarial_classes/cleanup` 스키마 일관. boulder.json `schema_version:2` 레지스트리로 work별 status 추적 |
| **발견성** | ✅ 우수 | plans/(18 md), evidence/tmap-walkforward/(manifest·log·pairs·config 일관 명명), gate/(p0b_verify.py+pairs 3종) — 명명규칙으로 재발견 용이 |
| **최신성** | ⚠️ drift | 브리핑 읽기경로 `ai_strategy_loop/tmap/(tmap_multiband_discovery·gen_template_hypothesis)`는 오기, 실제 `ai_strategy_loop/scripts/`. `§검증된사실3 "피드백=last_errors뿐"`이 P2 추가 후 미갱신 |

### 갭·보강안 (기록)

| ID | 갭 | 심각도 | 보강안 |
|---|---|---|---|
| **R-D1** | 브리핑 읽기경로 오기(`tmap/`→실제`scripts/`). 계획서 line313-315는 `scripts/`로 일관, 브리핑만 오기 | 낮음 | 핵심파일인덱스 경로 1줄 정정(문서 정합, 코드 무영향) |
| **R-D2** | `§검증된사실3 "피드백=last_errors뿐"`이 P2 환류(`feedback_text`) 추가 후 미갱신 | 낮음 | `build_prompt`에 `feedback_text`+`last_errors` 공존 명기(기능 정합, 문구만 갱신) |
| **R-G1** | `_discovery_feedback.txt` 내용이 `회피: a` 단일토큰으로 **퇴화** — 환류 ledger가 의미있는 회피/선호/앵커를 축적 못함 | 중간 | P2 `build_feedback` 출력 점검: ledger 비어 degrade 중인지, 파싱 손실인지 확인(코드 읽기로 진단, 엔진무수정) |

> ✅ **긍정 정정**: 교차검증 보고서 G2 보강안이 "P1 사전등록서 미작성"을 우려했으나, `p1_ab_preregistration.md`(3.7KB, 2026-06-15 실행 전 동결)가 **실재 확인**. arm 정의·OOS 단일 합격지표·rate 대리지표·C3 K=3 평탄 정지규칙·n(8/40) 전부 동결됨. 사전등록 규율 충족.

---

## 4. 대시보드 관측성 — 업그레이드 프로세스 확인 가능성

**결론**: 5단계(게이트→A/B→격상→환류→다밴드) 전부 산출물로 관측 가능. 단, **환류(P2)의 실효**와 **A/B B-arm(stateful)**은 미완으로 *효과*가 아직 관측 불가.

| 프로세스 | 관측 가능성 | 관측 경로 / 현재 신호 |
|---|---|---|
| **① 게이트 (P0a/P0b)** | ✅ 완전 | `loop_runs.db` P0b 3 run 영속: known-good 2,167,239 동일(결정론 PASS), no-go −3,048,898(mdd 65.93>cap35 REFUSE). `gate/p0b_verify.py` 재실행 가능 |
| **② A/B (P1)** | ⚠️ 진행중 | A-arm `ab_random_n8.md` **8행 완료**(전 no-go, promising 0). B-arm `ab_stateful_n8.md` **1행만**(iter0 no-go) — ★백그라운드 실행 중, 미완 |
| **③ 격상 (스모크→전체→OOS)** | ✅ 완전 | escalation 표 컬럼(robust코너/smoke q1·q2/전체train/OOS/판정)으로 단계별 가시화. iter7만 `smoke-pass`(205,715/1,533,675→전체 −2,030,044) 단계강등 관측 |
| **④ 환류 (feedback)** | ❌ 효과 미관측 | `_discovery_feedback.txt` = `회피: a`(퇴화). 환류 *배선*은 코드 실재하나 ledger 축적 빈약으로 회피/선호 신호가 대시보드에 의미있게 안 뜸 |
| **⑤ 다밴드 (track rotation)** | ✅ 완전 | escalation 40 iter에 tick_new·tick_anchor·min_new 로테이션 가시화. iter2 `gen-fail`(min_new None)도 분모제외 신호로 관측 |

### 갭·보강안 (관측성)

| ID | 갭 | 심각도 | 보강안 |
|---|---|---|---|
| **O-G1** | B-arm(stateful) **8행 중 1행만** — 환류 우위 판정 불가 상태가 대시보드에 명시 안 됨(완료처럼 보일 위험) | 중간 | A/B md 상단에 `진행 N/8 (실행중)` 진행률 헤더 추가([승인필요]: `ab_discovery_eval` 출력 1줄, 엔진무수정) |
| **O-G2** | 환류 ledger 퇴화(`회피: a`)로 ④단계가 "ON인데 무내용". rate 대리지표(smoke-pass率/near-miss率)가 md에 미표시 — `p1_ab_preregistration §3` 정의분 미가시화 | 중간 | escalation/A/B md에 valid-attempt 분모·rate 3종 1행 추가(사전등록 §3 정합) |
| **O-G3** | escalation 40 iter 전부 no-go인데 **C3 평탄(K=3) 카운터가 대시보드 미표시** — 천장선언 트리거 진척이 안 보임 | 낮음 | summary JSON에 `flat_streak/K` 필드 1개 추가(천장선언 가시화) |

---

## 5. 코드↔기록↔대시보드 정합 (drift 목록)

> 별도 교차검증 완료: **정합 9.5/10**, 기능적 불일치 0, P0b 실백테 증거 DB 영속. 아래는 그 drift 목록 + 본 점검에서 추가 확인분.

| ID | drift | 심각도 | 상태 |
|---|---|---|---|
| **D1** | 브리핑 읽기경로 오기(`tmap/`→실제`scripts/`). 코드 무영향 | 낮음 | 문서 정정 필요 |
| **D2** | `§검증된사실3 "피드백=last_errors뿐"`이 P2 후 미갱신(`feedback_text` 공존) | 낮음 | 문구 갱신 필요(기능 정합) |
| **G1(코드)** | `ab_discovery_eval.metrics()`/`verdict` **단위테스트 부재** (계획서 line230 요구분). P1 task#20 in_progress와 정합 | 중간 | P1 합격판정 전 필수 — rand/stateful 픽스처 jsonl 2개로 5분기 커버 |
| **G2(코드)** | P0b 거짓기각 가드 **(b)비결정론 분기 라이브 미발동** — known-good 2회=결정론(a분기)로 종료. noise_margin은 단위모킹만 | 낮음 | 계획 허용 분기(갭 아님). noise_margin 라이브 임계 동결 권고 |
| **G3(보강 정정)** | 교차검증이 우려한 "P1 사전등록서 미작성"은 **해소됨** — `p1_ab_preregistration.md` 실재 | — | ✅ 해결 확인 |
| **G4(신규)** | `_discovery_feedback.txt` 퇴화(`회피: a`) — 코드 환류배선↔실제 ledger 축적 사이 **실효 drift** | 중간 | P2 `build_feedback` ledger 입력 진단(R-G1과 동일 항목) |

---

## 6. ★우선 보강 Top 5 (엔진무수정·최소공수 순)

| 순위 | 항목 | 영역 | 공수 | 승인 | 효과 |
|---|---|---|---|---|---|
| **1** | D1/D2 문서 표기 1~2줄 정정(`scripts/` 경로 + `§검증된사실3` feedback 공존) | 기록 | 5분 | 불요(문서) | 정합 drift 즉시 0화 |
| **2** | `_discovery_feedback.txt` 퇴화(`회피: a`) 원인 진단 — `build_feedback` ledger 입력 점검(읽기) | 기록+관측 | 30분 | 불요(읽기) | ④환류 실효성 회복 전제 |
| **3** | A/B md에 `진행 N/8 (실행중)` 진행률 헤더 — 미완을 완료로 오독 차단 | 관측 | 15분 | [승인필요] `ab_discovery_eval` 출력 1줄 | O-G1 해소, stateful arm 미완 가시화 |
| **4** | escalation/A/B md에 valid-attempt 분모 + rate 3종 1행(사전등록 §3 정합) | 관측 | 30분 | [승인필요] 표 출력 행 추가 | O-G2 해소, 대리지표 가시화 |
| **5** | `ab_discovery_eval.metrics()`/`verdict` 5분기 단위테스트(픽스처 jsonl 2개) | 코드+기록 | 1h | 불요(테스트추가) | G1(코드) 해소, P1 합격판정 전 필수 회귀방지 |

> 모두 엔진/CLI/backtest-graph 무수정. 1·2·5는 승인 불요(문서·읽기·테스트), 3·4만 산출물 출력행 추가로 [승인필요].

---

## 7. 다음 액션 (P3~P5와 병행 가능한 관측성/기록 보강)

| 액션 | 병행 P단계 | 비고 |
|---|---|---|
| **C3 평탄 카운터(`flat_streak/K`) summary JSON 노출** | P1 종료 직전 | 천장선언 트리거 가시화. 현 escalation 40 no-go가 K=3 평탄에 얼마나 근접했는지 관측(O-G3) |
| **P2 환류 ledger 실효 진단 → feedback 품질 회귀테스트** | P3(환류토글ON+feature_importance) 착수 전 | `회피: a` 퇴화 해소가 P3 전제. feature_importance 환류도 같은 ledger 경로 재사용 가능성 점검 |
| **P4 grid 산출물 명명규칙을 escalation/A/B와 통일** | P4(grid) 착수 시 | `mbdisc_NNN`·`llmgNN` 기존 규칙 답습 → 발견성 유지 |
| **P5 lift·mutator 결과를 rate 대리지표 표에 합류** | P5 | 사전등록 §3 rate 정의에 mutator 효과를 동일 분모로 비교(raw count 금지 철칙 준수) |
| **noise_margin 라이브 임계 동결** | P1 실행 중 | `p1_ab_preregistration.md`에 1줄 추가(G2 코드 보강). 비결정론 라이브 미발동분 사전 동결 |
| **boulder.json work 상태 갱신** | 상시 | P1 완료 시 `tick-min-condition-generation-review` work 종료 기록 일관성 유지 |

> ★주의 준수: 본 점검은 전 과정 **읽기 전용**으로 수행. 백테/엔진/LLM 실행 0건. P1 A/B 백그라운드 백테는 미접촉(B-arm `ab_stateful_n8` 1/8행은 진행 중 상태 그대로 관측만).

---

**핵심 파일 (절대경로)**:
- 기록: `C:\System_Trading\STOM\STOM_V.wt-dev\.omo\start-work\ledger.jsonl`(209행), `...\.omo\boulder.json`, `...\.omo\plans\tick-min-condition-generation-review-20260613.md`
- 관측성: `...\.omo\evidence\tmap-walkforward\ab_random_n8.md`(8행 완료), `...\ab_stateful_n8.md`(1/8 실행중), `...\multiband_escalation.md`(40 no-go), `...\p1_ab_preregistration.md`, `...\_discovery_feedback.txt`(퇴화)
- 정합·게이트: `...\.omo\evidence\tmap-walkforward\gate\p0b_verify.py`, `...\ai_strategy_loop\tmap\refine_gate.py`, `...\ai_strategy_loop\scripts\ab_discovery_eval.py`(rate/verdict 단위테스트 부재), `...\tmap_multiband_discovery.py`, `...\gen_template_hypothesis.py`
