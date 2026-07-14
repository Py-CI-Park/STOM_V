# 2026-07-12 조건식 AI 루프 고도화 최종 결과 및 잔여 작업 인계 보고서

> 브랜치: `feature/loop-visual-and-quant-deepening-20260712`
>
> 기준 HEAD: `f0ba153d`
>
> 계보: `loop/process-research-pipeline`의 `8ded51f8`을 병합한 `1b7215f0` → P0 배선 개선 브랜치 → 본 G1~G5 고도화 브랜치
>
> 데이터 정책: **현존 데이터만 사용**. 신규 데이터 수집·추가·기간 확장은 오너의 별도 결정 전까지 보류한다.
>
> 승인 경계: CL-R08~R10은 정확한 승인 문구 없이는 실행하지 않는다. 생성·게이트·연구 실행 의미를 바꾸는 신규 선택 기능은 전역 기본 OFF를 유지한다. 읽기 전용 분석 API와 시각화는 관찰성 기능이라 실행 토글 대상이 아니다.

---

## 1. 최종 결론

이번 작업은 “수익 전략을 이미 만들었다”는 완료가 아니다. 다음 두 상태를 명확히 분리해야 한다.

1. **조건식 AI 연구 시스템 개발·검증:** G1~G5 전부 완료.
2. **실제 수익성 증명:** 아직 0점. CL-R08~R10이 잠겨 있어 실행하지 않았다.

완료된 핵심은 다음과 같다.

- LLM이 단순한 `not` 필터 나열을 벗어나 AND/OR, 시간대·국면 분기, 박스·돌파·눌림, 오더플로우, 다단 청산을 참고할 수 있는 복합 조건식 예제 자산을 구축했다.
- 운영 `strategy.db` 인간 전략을 대상으로 기계 게이트를 전수 감사했고, **확정 오탐은 0건**임을 입증했다. 높은 거부율의 주원인은 인간 GUI 전략과 루프 백테스트 실행 환경의 차이다.
- 매수·매도 시점 데이터와 거래 결과 테이블에서 기대값, PF, streak, 분포, 보유시간, 시간대, MFE/MAE, 낙폭 기여 등을 추출하는 per-trade 퀀트 분석기를 구축했다.
- 대시보드에 시드→프롬프트→AI 생성→게이트→공식 백테스트→채점→부검→환류의 8단계 세대 사이클과 애니메이션을 구축했다.
- 연구 프로그램을 9단계로 채점하는 결정론 스코어카드를 구축했고, 현재 성숙도는 **77/100**이다.
- 브랜치 전체 단위 테스트는 **7 known failed / 4,559 passed / 1 skipped / 신규 실패 0**이다.

현재 병목은 더 이상 “조건식을 작성할 수 있는가”가 아니다. **정본 연구 실행, 프롬프트·시드 A/B 귀속, 자동 환류 소비, blind OOS, 수익 증명**이 남은 병목이다.

---

## 2. 연구 목표와 판단 기준

최종 목표는 다음 폐루프를 재현 가능하게 만드는 것이다.

```text
현존 tick/min DB
  → 시드·도메인 지식·실패 기록 준비
  → AI 조건식 생성/개선
  → 기계 게이트
  → 공식 STOM 백테스트
  → 채점·강건성 판정
  → per-trade 부검·퀀트 분석
  → 근거가 있는 프롬프트 환류
  → 다음 세대 생성
  → 봉인 OOS와 인간 기준선 비교
```

이번 개발의 완료 기준은 다음이었다.

- 생성 다양성: AND/OR와 국면별 복합 구조를 충분히 참조할 수 있는가.
- 문법·실행 안전성: 기계 게이트가 잘못 막거나 실행 불가능한 전략을 허용하지 않는가.
- 분석 깊이: 단순 총수익/MDD를 넘어 개별 거래의 진입·청산 특성을 설명할 수 있는가.
- 관찰성: 현재 세대가 어느 단계에 있고 AI가 어디서 개입하는지 대시보드에서 이해할 수 있는가.
- 연구 관리: 진행도를 감이 아니라 측정 신호로 관리할 수 있는가.
- 정직성: 개발 완료와 수익 증명을 혼동하지 않는가.

---

## 3. 지금까지의 연구 계보

### 3.1 전수 검사에서 확인한 초기 문제

기존 전수 보고서 `2026-07-12_ai_condition_system_full_audit_and_improvement_report.md`에서 다음을 확인했다.

- 전체 세대 5,124건 중 프롬프트 기록은 460건 수준으로, 과거 실행의 대부분은 AI가 아닌 결정론 격자였다.
- `principles.md`, `constraints_checklist.md`, `idiom_dictionary.md`가 존재하지만 프롬프트에 제대로 배선되지 않았다.
- 연구 품질 토글 대부분이 기본 OFF였고, 정본 연구 프로파일로 완주한 run이 없었다.
- 증거 원장 스키마는 있으나 정본 DB의 passport/envelope 행은 0이었다.
- tick 데이터는 길지만 09:00~09:30으로 좁고, min 데이터는 풀 세션이나 약 11개월로 짧다.
- 기존 조건식 생성 실물은 시간대 분기와 다단 청산을 생성할 수 있었으므로, 핵심 문제는 생성 능력 자체보다 배선·실험 설계·검증 단계였다.

### 3.2 P0 선행 개선

| 범위 | 주요 커밋 | 완료 내용 |
|---|---|---|
| 정본 병합 | `1b7215f0` | `8ded51f8` V4 대시보드와 `loop/process-research-pipeline` 기능 통합 |
| 연구 계약 복원 | `10b3ef82` | 문장형 STOM 조건 지문, BinOp 정준화, 깨진 연구 계약 테스트 10건 복구 |
| 구조론 프롬프트 배선 | `967d0124` | 구조론·제약·관용구 자산을 Context Pack 및 선택 프롬프트에 연결 |
| 정본 연구 프로파일 | `904b660e` | 원리 게이트·증거 원장·부검/분산 관련 정본 ON 묶음 확립, 전역 기본 OFF 유지 |
| 골드 시드 우선 | `08f9caa4` | 운영 `strategy.db` few-shot에서 골드 시드 우선, 임시 전략 제외 |
| 런타임 위생 | `c4c901dd` | `.gjc` 세션 상태 gitignore, 낡은 frontend stash 정리 |
| 밴드 시드 | `61499e33` | tick 실DB 채굴 밴드를 매수 프롬프트 힌트로 연결, 기본 OFF |
| 정책·대시보드 마감 | `4fa5eac5` | 현존 데이터만 사용 정책 확정, V4 실기동·실렌더 검증, 원리 게이트 설정 노출 |

실DB 밴드 시드 스모크는 tick subset 22,545행에서 승자 3,570행, 프롬프트용 시드 5개를 산출했다. 이는 임계값을 LLM의 감만으로 정하지 않고 실제 데이터 분포에서 가져오는 첫 경로다. 단, 생성 시드용 힌트이며 수익성 증거가 아니다.

---

## 4. G1~G5 완료 결과

| 목표 | 구현·교정 커밋 | 증거 |
|---|---|---|
| G1 복합 예제 | `4c20fcba`, `b9b0716f` | `artifacts/g1_quality_gate.json` |
| G2 게이트 감사 | `284e792b`, `22c9671f`, `f5f7deba` | `artifacts/g2_quality_gate.json` |
| G3 퀀트 분석 | `2fcaf6c0`, `68be3b5c` | `artifacts/g3_quality_gate.json` |
| G4 세대 시각화 | `210749b6`, `7c047fbf`, `28615559` + 증거 스키마 정합 커밋 | `artifacts/g4_quality_gate.json` |
| G5 성숙도 | `293f797e`, `8c34a439`, `ade5930b` | `artifacts/g5_quality_gate.json` |
| 최종 증거 보존 | `f0ba153d` | G1~G5 품질 게이트 정본 |


### 4.1 G1 — 복합 조건식 예제 자산과 프롬프트 배선

**산출물**

- `utility/ai_agent/system_prompt/v1/composite_examples.md`
- `ai_strategy_loop/brain/prompt.py`의 `_FULL_STOM_SOURCE_ASSETS` 등록
- `tests/unit/test_composite_examples_asset.py`
- `artifacts/g1_quality_gate.json`

**구축 내용**

- 총 25개 예제: 매수 16개, 매도 9개.
- 매수 tick 12 + min 4, 매도 tick 6 + min 3.
- 포함 구조:
  - AND/OR/괄호 결합
  - 시간대·시가총액 국면 분기
  - 박스 하단 지지와 상단 돌파
  - 눌림·리테스트
  - 사건 거래대금과 거래량 급증
  - 호가·체결 오더플로우
  - 갭과 기준선 결합
  - 다단 트레일링·시간 청산·구조 무효화
- 각 샘플에 엣지 가설과 “임계값은 검증 전 무근거 가설” 고지를 포함했다.
- 매도 샘플의 강제청산·손절 경로와 매수/매도 변수 스코프를 AST 기반 테스트로 고정했다.

**정직한 판정**

예제 자산은 LLM의 탐색 어휘를 넓혔지만, 예제 추가가 수익률을 높였는지는 아직 A/B로 측정하지 않았다. 현재 증명된 것은 **프롬프트에 다양한 구조를 안전하게 제공한다**는 계약이다.

### 4.2 G2 — 기계 검사 게이트 오탐 전수 감사

**산출물**

- `scripts/audit_gate_false_rejects.py`
- `docs/update_log/2026-07-12_g2_gate_false_reject_audit_report.md`
- `artifacts/g2_gate_false_reject_audit.json`
- 관련 회귀 테스트

**실측 대상**

- 운영 `_database/strategy.db` 읽기 전용 사용.
- 인간 전략 stockbuy 102 / stocksell 47에서 `__AUTO_TMP__` 3건을 제외한 146개 전략.

**최종 결과**

| 검사 | 거부율 | 최종 판정 |
|---|---:|---|
| variable scope | 72/197 평가, 36.5% | 확정 오탐 0 |
| token check | 1/146, 0.7% | 실제 구문 오류 |
| filter gate | 10/99, 10.1% | 연구 lane의 의도적 타이트함 |
| sell exec budget | 20/47, 42.6% | warm timeout 실측에 근거한 의도적 상한 |
| principle gate | 24/41 평가 | 데이터 창·실행 문맥 차이 포함 |
| 하나 이상 거부 | 103/146, 70.5% | 인간 GUI 전략을 루프 정규형으로 변환해야 함 |

초기에는 `강제청산`, `매도수량`을 오탐 후보로 보았으나 아키텍트 검토에서 틀린 판정임이 드러났다. 저장 시점 GUI 검증기가 아니라 **공식 백테스트 엔진의 exec 환경**이 진실 공급원이다. 해당 화이트리스트 확대는 철회했고, 잘못 허용하지 않도록 회귀 테스트로 고정했다.

**실제 교정**

- `누적초당*`, `누적분당*`, `최고초당*`, `최고분당*`, `분봉*` 파생 이름의 tick/min 계열 판정을 정확히 분리했다.
- SetGlobals 이름 181개를 대조해 신규 오분류가 없음을 확인했다.

### 4.3 G3 — per-trade 퀀트 심층 분석

**산출물**

- `ai_strategy_loop/autopsy/trade_quant.py`
- 대시보드 `GET /trade_quant`
- `tests/unit/test_trade_quant.py`
- `tests/unit/dashboard/test_trade_quant_endpoint.py`
- `artifacts/g3_trade_quant_real_csv_smoke.json`

**분석 지표**

- 기대수익률·기대금액, 승률, profit factor, payoff.
- 수익률 평균·표준편차·왜도·첨도·q05~q95 분위.
- 최대 연승·연패와 streak 분포.
- 보유시간과 수익의 상관, 보유시간 분위별 성과.
- 5분/30분 매수 시간대별 성과.
- MFE 포착률, 손실 MAE, 승패별 MFE/MAE 효율.
- 최대낙폭 구간 내 손실 거래 기여 top-N.
- B_* 진입 피처의 승패 차이.
- 다음 프롬프트에서 사용할 수 있는 한국어 `nl_lines` 최대 8줄.

**실데이터 스모크**

- 4,365거래를 분석했다.
- PF 0.55, 승률 33.7%, 최대 연패 21, 손실 MAE 약 2.42배.
- 이 결과는 분석기가 실제 CSV를 읽고 의미 있는 약점을 추출한다는 증거다.
- 동시에 해당 표본 전략이 수익 전략이 아님을 보여 준다. 이를 수익 성과로 해석하면 안 된다.

**현재 연결 수준**

- `/trade_quant` API는 읽기 전용으로 실시간 조회 가능하다.
- `nl_lines`는 생성되지만 아직 `FeedbackEnvelope`나 다음 세대 `build_messages`의 자동 소비 경로로 연결되지 않았다.
- V4 전용 시각 카드도 아직 없다. 현재는 백엔드 API 노출 단계다.

### 4.4 G4 — 반복 세대 루프 시각화와 애니메이션

**산출물**

- `ai_strategy_loop/dashboard/frontend/v4-loop-cycle.jsx`
- `v4-research.jsx`, `v4.css`, 재빌드 번들
- `tests/unit/dashboard/test_v4_loop_cycle.py`
- `artifacts/g4_loop_cycle_render_20260712.png`
- `artifacts/g4_qa_render.png`
- `artifacts/g4_browser_transcript.json`

**화면 구성**

```text
시드
 → 프롬프트 조립
 → AI 조건식 생성
 → 기계 게이트
 → 공식 STOM 백테스트
 → 채점
 → 부검
 → AI 환류
 ↺ 다음 세대
```

- 8개 노드를 원형으로 배치했다.
- AI가 직접 개입하는 생성·환류 위치와 코드가 수행하는 위치를 배지로 구분했다.
- 백엔드 `current_step`을 실제 단계 하이라이트에 연결했다.
- 실행 중 단계는 pulse 애니메이션, 완료 단계는 dim·완료 상태로 표시한다.
- `prefers-reduced-motion`을 지원한다.
- Playwright 검증 5/5, 8탭 왕복, JS 오류 0, 헤드리스 스크린샷으로 실렌더를 검증했다.

**판정**

세대 진행 과정은 V4 Research Live에서 시각적으로 이해할 수 있다. 다만 G3/G5의 상세 지표는 아직 같은 화면의 카드로 통합되지 않았다.

### 4.5 G5 — 연구 관리 성숙도 스코어카드

**산출물**

- `scripts/research_maturity_scorecard.py`
- 대시보드 `GET /research_maturity`
- `ai_strategy_loop/state/research_maturity.json` 런타임 산출(비커밋)
- `docs/update_log/2026-07-12_g5_research_maturity_scorecard.md`

**현재 결정론 점수**

| 단계 | 점수 | 의미 |
|---|---:|---|
| 엔진 계약 | 100 | 공식 엔진·비릴리스 검증 표면 존재 |
| 생성 | 100 | 프롬프트 자산 10/10, 핵심 도메인 자산 4/4 |
| 게이트 | 100 | 5종 게이트와 G2 전수 감사 존재 |
| 채점 | 60 | 기본/graded fitness 존재, Deflated Sharpe·PBO 없음 |
| 부검·환류 분석 | 100 | 기존 부검 + trade_quant + segment/edge 분석 존재 |
| 증거 원장 | 40 | 스키마·저장기는 있으나 passport/envelope 0행 |
| 프로필·토글 | 91 | 정본 프로파일 20개 키 중 18개 활성 |
| 대시보드 | 100 | 관련 API와 V4 loop cycle 존재 |
| 수익 증명 | 0 | CL-R08~R10 미실행, 하드코드 0 |
| **전체** | **77/100** | 개발 성숙도이며 수익 가능성 점수가 아님 |

스코어카드는 파일 존재나 행 수로 일부 단계가 부풀 수 있는 advisory 지표다. 허위 CL-R 문서를 넣어도 수익 증명 점수는 0에서 변하지 않도록 레드팀으로 확인했다.

---

## 5. 시드는 고정되어 있는가, AI는 언제 투입되는가

### 5.1 시드 동작

시드는 하나로 영구 고정된 구조가 아니다. run 설정에 따라 다음 방식이 가능하다.

1. `seed_buy`/`seed_sell`이 지정된 gen-0:
   - AI 생성 없이 기존 시드를 그대로 평가한다.
2. seed-refine:
   - 기존 매수/매도 코드를 출발점으로 주고 AI가 1~2개 조건을 점진 개선한다.
3. fresh generation:
   - base code 없이 프롬프트 자산과 환류 근거로 새 조건식을 생성한다.
4. `freeze_buy`:
   - 매수식은 byte 그대로 복제하고 AI는 매도식만 개선한다.
5. few-shot seed:
   - 운영 `strategy.db`의 인간 전략을 예제로 주입한다. 골드 시드 우선·임시 전략 제외가 적용된다.
6. band seed hint:
   - 현존 tick DB에서 채굴한 분위 밴드를 매수 프롬프트의 가설 힌트로 제공한다.
7. meta seed:
   - 과거 run의 공통 성공·실패 요약을 프롬프트 가이드로 제공한다.

모든 선택 기능은 전역 기본 OFF다. 정본 연구 프리셋에서 검증 대상 기능만 켠다.

### 5.2 AI 개입 시점

| 시점 | AI 개입 | 설명 |
|---|---|---|
| gen-0 시드 지정 | 없음 | 기존 시드 원형을 먼저 평가 |
| fresh/seed-refine 생성 | 있음 | `generate_strategy`가 매수·매도 프롬프트를 조립하고 provider를 호출 |
| 기계 게이트 실패 재시도 | 있음 | 오류·거부 사유를 다음 생성 시도에 전달 |
| 백테스트 | 없음 | 공식 STOM 엔진이 결정론 실행 |
| 채점 | 없음 | 코드가 fitness·hard gate를 계산 |
| 부검 | 주로 없음 | 코드가 거래 테이블을 분석해 구조화 결과와 NL 근거 생성 |
| 다음 세대 환류 | 있음 | 부검·세그먼트·가정·메타 근거가 다음 AI 프롬프트에 주입 |
| `freeze_buy` | 매도만 | 매수 원형 보존, 청산만 AI 개선 |

즉 AI가 수익을 임의로 “판정”하지 않는다. AI는 조건식 후보 생성과 개선에 개입하고, 채택·졸업은 공식 백테스트 결과와 하드 게이트가 결정한다.

---

## 6. 검증 기록

### 6.1 Ultragoal 완료

- G001~G005 모두 `complete`.
- 각 목표에 architect 3-lane 검토, executor QA/레드팀, cleanup 재검증, 품질 게이트 영수증이 존재한다.
- 최종 aggregate receipt 생성 후 Ultragoal을 완료했다.
- 품질 게이트: `artifacts/g1_quality_gate.json` ~ `artifacts/g5_quality_gate.json`.

### 6.2 테스트

| 검증 | 결과 |
|---|---|
| 전체 `tests/unit/` 최종 실행 | **7 failed / 4,559 passed / 1 skipped / 44 warnings** |
| 신규 실패 | **0** |
| known 실패 | backtest spawn/UI 계약 7건 |
| G4 브라우저 QA | 8노드·AI/코드 배지·탭 왕복·reduced-motion·오류 0 통과 |
| G2 실DB 안전성 | `strategy.db` 읽기 전용, SHA 불변 |
| G3 실 CSV | 4,365거래 분석, 독립 19지표 재계산 정합 |
| G5 게임화 공격 | 허위 CL 문서/가짜 행으로도 수익 증명 0점 유지 |

known 7건은 이번 브랜치가 만든 회귀가 아니다. 그러나 저장소 전체가 완전 green이라는 뜻도 아니므로 PR 설명에 반드시 구분해 적는다.

---

## 7. 아직 완료되지 않은 것

### 7.1 우선순위 P0 — 승인 없이 가능한 후속 개발

1. **G3/G5 V4 카드 통합**
   - `/trade_quant`, `/research_maturity`는 API만 존재한다.
   - V4 Research/Autopsy 화면에 지표 카드, 시간대 표, MFE/MAE, 낙폭 기여, 9단계 성숙도 막대를 연결해야 한다.
2. **trade_quant 자동 환류 배선**
   - 현재 `nl_lines` 생성까지만 완료했다.
   - `FeedbackEnvelope` 생산→증거 원장 기록→다음 세대 프롬프트 소비를 단일 계약으로 연결해야 한다.
3. **A-4 매도/리스크 ablation**
   - 매수 Tick_902 고정, 체결강도 페이드·트레일링·시간 손절을 분리 비교한다.
   - 기존 데이터와 공식 엔진만 사용하며, 결과를 수익 증명이 아닌 사전 청산 구조 선택 근거로 취급한다.
4. **Deflated Sharpe/PBO 구현**
   - 현재 채점 60점의 직접 원인이다.
   - 다중 시도·선택 편향을 보정한 뒤 CL-R08 결과를 해석해야 한다.
5. **프롬프트·시드 A/B 귀속**
   - composite examples ON/OFF, few-shot ON/OFF, band hint ON/OFF를 동일 분할·예산에서 비교한다.
   - “프롬프트를 개선했기 때문에 좋아졌다”를 세대 성과와 조인해 증명한다.
6. **정본 프로파일 18/20 검토**
   - 현재 `few_shot_enabled`, `require_filter_gates`가 공통 정본 ON 묶음에서 빠져 있다.
   - 무조건 켜지 말고 A/B와 거래 과소화 영향을 확인한 뒤 결정한다.
7. **조건식 통합 카탈로그**
   - 운영 DB, loop DB, lattice, Plan D, repair composite를 AST fingerprint 기준으로 묶어 중복·계보·성과를 조회한다.
8. **밴드 직접 컴파일 전 변수 검증**
   - `seed_902_band.py`의 `VI아래5호가`, `초당순매수금액`은 엔진 정의가 확인되지 않았다.
   - NL 힌트 경로는 안전하지만 직접 조건식 컴파일 경로를 열기 전에 반드시 교정한다.
9. **sell scope 진실 공급원 자동화**
   - 현재 계약을 문서·테스트로 고정했다.
   - 장기적으로 backengine의 실제 exec unpack AST에서 허용 이름을 도출해 수기 목록 드리프트를 없앤다.

### 7.2 승인·시간 잠금 단계

| 단계 | 실행 조건 | 목적 |
|---|---|---|
| CL-R08 | 정확히 `I approve CL-R08 bounded min performance only` | 제한된 min train/validation 성능 검증 |
| CL-R09 | 2026-07-11 이후 20거래일 데이터 조건 + 정확히 `I approve CL-R09 sealed OOS/WF only` | 봉인 OOS/walk-forward 검증 |
| CL-R10 | 정확히 `I approve CL-R10 benchmark promotion review only` | 인간 기준선 비교와 승격 검토 |

이 세 단계가 끝나기 전에는 “수익 전략을 만들었다”, “자동 연구가 효과가 있다”, “프로덕션 승격 가능”이라고 결론 내리지 않는다.

### 7.3 오너 결정으로 보류된 것

- 신규 데이터 수집.
- min 기간 연장.
- 외부 데이터 소스 추가.
- 데이터베이스 쓰기·이관.

현재 연구는 기존 tick/min DB만 사용한다.

### 7.4 금지 유지

- broad grid 재실행 또는 축만 늘린 조합 폭발.
- full-period 선별 후보를 OOS 승자로 해석.
- 하드 게이트 완화로 통과율을 인위적으로 높이기.
- 승인 없는 CL-R08~R10, export, live 주문.
- V3K 후속 게이트 우회.
- 보호 DB와 결과 경로를 소스 작업처럼 수정·삭제.

---

## 8. 권장 후속 실행 순서

```text
[현재 브랜치 PR/통합]
  ↓
[P0-1 V4 trade_quant·maturity 카드]
  ↓
[P0-2 trade_quant → FeedbackEnvelope → 다음 프롬프트 자동 환류]
  ↓
[P0-3 매도 ablation + Deflated Sharpe/PBO]
  ↓
[P0-4 composite/few-shot/band hint A/B]
  ↓
[정본 프로파일 확정 + 증거 원장 실제 행 생성]
  ↓
[정확한 승인 후 CL-R08]
  ↓
[봉인 조건 충족 후 CL-R09]
  ↓
[정확한 승인 후 CL-R10 인간 기준선 비교]
  ↓
[그때만 수익성·승격 최종 판정]
```

가장 먼저 할 일은 더 많은 조건식을 무작정 생성하는 것이 아니다. **어떤 시드·프롬프트·환류가 성과 변화의 원인이었는지 귀속 가능한 실험 구조를 완성하는 것**이다.

---

## 9. 현재 성숙도 해석

- **개발 성숙도 77%:** 루프 구성요소와 관찰 도구는 상당 부분 완성됐다.
- **조건식 생성 기반 100%:** 자산·도메인 지식·복합 예제의 존재와 배선 기준이다. 수익성 100%가 아니다.
- **게이트 100%:** 필요한 검사 모듈과 실DB 감사가 있다는 의미다. 통과율이 높다는 뜻이 아니다.
- **부검·환류 분석 100%:** 분석기가 존재한다는 의미다. G3의 자동 프롬프트 소비까지 끝났다는 뜻이 아니다.
- **대시보드 100%:** 관련 API와 V4 사이클이 존재한다는 스코어카드 정의다. G3/G5 전용 카드가 모두 있다는 뜻은 아니다.
- **수익 증명 0%:** 현재 가장 중요한 정직 신호다.

따라서 시스템은 “연구 도구 완성에 가까움, 성과 증명은 시작 전” 상태다.

---

## 10. 파일·증거 색인

### 핵심 코드

- `ai_strategy_loop/controller/loop.py`
- `ai_strategy_loop/brain/prompt.py`
- `ai_strategy_loop/brain/variable_scope.py`
- `ai_strategy_loop/autopsy/trade_quant.py`
- `ai_strategy_loop/dashboard/app.py`
- `ai_strategy_loop/dashboard/frontend/v4-loop-cycle.jsx`
- `scripts/audit_gate_false_rejects.py`
- `scripts/research_maturity_scorecard.py`
- `utility/ai_agent/system_prompt/v1/composite_examples.md`

### 세부 보고서

- `docs/update_log/2026-07-12_ai_condition_system_full_audit_and_improvement_report.md`
- `docs/update_log/2026-07-12_g2_gate_false_reject_audit_report.md`
- `docs/update_log/2026-07-12_g3_trade_quant_module.md`
- `docs/update_log/2026-07-12_g5_research_maturity_scorecard.md`
- `docs/update_log/2026-07-11_ai_condition_loop_canonical_rebuild_handoff.md`

### 검증 아티팩트

- `artifacts/g1_quality_gate.json`
- `artifacts/g2_gate_false_reject_audit.json`
- `artifacts/g3_trade_quant_real_csv_smoke.json`
- `artifacts/g4_browser_transcript.json`
- `artifacts/g4_loop_cycle_render_20260712.png`
- `artifacts/g4_qa_render.png`
- `artifacts/g1_quality_gate.json` ~ `artifacts/g5_quality_gate.json`

---

## 11. 인계 시 한 문장 상태

**브랜치의 G1~G5 개발·코드 리뷰·QA·단위 테스트는 완료됐고, AI 조건식 루프는 다양한 조건식 생성·기계 검증·개별 거래 부검·세대 시각화·연구 성숙도 측정 기반을 갖췄다. 그러나 trade_quant의 자동 환류와 전용 V4 카드, Deflated Sharpe/PBO, 프롬프트/시드 A/B, 실제 증거 원장 축적, CL-R08~R10 수익 검증은 남아 있으며 현재 수익 증명은 0%다.**
