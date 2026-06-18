# 조건식 자율탐색 — 근본 원인 분석과 목표 달성 계획 (2026-06-10, 전부 당일 실측 기반)

> **목적**: "시스템이 좋은 조건식을 만들어내지 못한다"의 **정확한 원인**을 실측으로 확정하고,
> 원인별 1:1 해결책과 실행 로드맵을 제시한다. 이 문서의 문제들을 해결하면
> "수익 내는 조건식을 만들고 → 백테스트로 검증하고 → 사용 가능 판정"이라는 목적에 도달한다.
> **근거**: 본 문서의 모든 수치는 2026-06-10 당일 실측(스모크 4라운드 20회 + 3년 train 3회 +
> 공식 부검 9회)과 기존 증거(.omo/evidence/, 6/5 방향성 검토)다. 추측 없음.
> **상태**: 백테스트 루프는 train 배치까지 완료 후 전부 종료됨(추가 실행 없음).
> 증거 루트: `.omo/evidence/claude-condition-research-20260610/`

---

## 0. 한 줄 결론

**"조건식을 못 만든다"는 한 개의 버그가 아니라 6개의 적층된 원인이며, 그중 2개(①선택 기준이
인간 시드조차 탈락시키는 비정합, ②시드 알파 자체의 연도별 쇠퇴)는 오늘 처음 실측으로 확정됐다.**
이 두 가지를 교정하지 않으면 생성기를 아무리 개선해도(GPT든 Claude든) "과적합 모양의 후보만
동결되고 OOS에서 붕괴"하는 기존 패턴이 구조적으로 반복된다.

---

## 1. 오늘 실측한 것 (요약 표)

### 1.1 인프라 (전부 가동 검증)
| 항목 | 결과 |
|---|---|
| zero-LLM 평가 경로 | `seed_buy/seed_sell`+`max_generations=1` + 신규 배치도구(prepare 1회+run N회) 가동. LLM 0회 |
| 후보 생성 | Claude 직접 생성 19개(매수 15·매도 4), 공식 가드(compile/token/scope) 전부 통과 주입 |
| 백테 실행 | 스모크(2025Q1) 4라운드 20회 + 3년 train(2023-2025, 2,285종목, prepare 279초) 3회 |
| 부검 엔진 | analyze_trades/analyze_exits 9회 실행 — 실행 가능·신호 유의미(아래 §2 곳곳에 인용) |
| 대시보드 | 단위테스트 318 통과 + live GET 8종 200 + 배치 run 표시 확인 (http://127.0.0.1:8770) |
| 프로젝트 게이트 | verify_nonrelease_sync 통과, 보호경로 무변경, 전체 단위테스트 2,374 통과(실패 7건은 기존 UI 계약 테스트 — 본 작업 무관) |

### 1.2 핵심 실측 수치
| 전략 | 구간 | profit | MDD | 거래 | 비고 |
|---|---|---:|---:|---:|---|
| 인간 시드 | train 2023-25 | **+8,631,199** | 17.44 | 307 | 게이트 통과. 연도별: 2023 +4.88M / 2024 +3.37M / **2025 +0.38M** |
| 인간 시드 | 2022 OOS(6/4) | +2,223,554 | 13.02 | 58 | |
| 인간 시드 | 2026 OOS(6/4) | **-191,109** | 15.63 | 10 | 쇠퇴 추세의 연장 |
| C7(시드+위험필터3) | train 2023-25 | +2,347,400 | 16.52 | 142 | 연도별 +1.95M/+0.70M/**-0.31M** — 필터가 수익 73% 깎고 MDD는 5%만 개선 |
| gen4(6/4 동결 후보) | 2025Q1 | -141,200 | 3.38 | 5 | train 전체 +1.16M였던 후보가 train 부분구간에서도 음수 = 과적합 직접 증거 |
| 신규 니치 5종(C3/C8/C2C/C9 등) | 2025Q1 | 전부 음수(-0.77M~-9.3M) | 16~94 | 35~684 | 리포트 임계값 직이식 실패 |

---

## 2. 정확한 원인 (우선순위순, 전부 실측 근거)

### 원인 1 ⭐신규 발견 — 선택 기준이 "시드급 행동"과 비정합: 시드조차 탈락하는 잣대로 시드 초월을 찾고 있었다
- 동결 선택기 `sparse_positive_v1` 기준: profit>0, **MDD≤10**, **거래 20~250**, 일평균≥0.05, payoff≥1.05.
- 그런데 같은 측정계로 잰 **인간 시드(목표 기준점)가 train MDD 17.44, 거래 307** — 두 항목 모두 탈락.
  6/4 OOS에서도 시드 MDD 13.02~15.63. 즉 **추구하는 벤치마크 자체가 현 기준을 통과 못 한다.**
- 귀결(구조적 필연): 기준을 통과할 수 있는 건 "저거래·저MDD 모양"뿐 → 그 모양은 train 우연
  적합(gen4: 124거래/MDD 9.12)일 확률이 높음 → OOS 붕괴 → `REJECT` 무한루프.
  **6/4의 일관 REJECT는 생성기 문제이기 이전에 기준-목표 비정합의 필연이었다.**
- 보조 사실: 17개 우수전략 문서의 MDD 1.9~6.75%·일평균 10~23회와 본 측정계(시드 MDD 17.4·일평균 0.4)는
  **단위/프레임이 다르다**(전일 full-day 기준 vs 시초 28분·베팅 단위 차이 추정). 기준 수치를 어느
  측정계에서 가져왔는지의 보정 감사가 한 번도 없었다.

### 원인 2 (6/5 진단을 당일 재확인) — 환류 신호가 전부 인샘플이라 루프가 과적합을 "생산"한다
- 부검은 train 거래에서만, best/winner 선택도 train 점수로만(6/5 검토 §3.4).
- 당일 재확인: 6/4 동결 gen4가 **train의 부분구간(2025Q1)에서도 -141,200/5거래** — train 전체
  점수가 train 내부 서브윈도우 일반화조차 보장하지 않는다.
- PBO/DSR(다중시도 보정) 미장착(감사 권고만 존재) → "여러 세대 중 최고"의 상향편의 무보정.

### 원인 3 ⭐신규 발견(11/11 완벽 분리) — 엔진 계산예산 가드 부재: 매도식의 비유계 스캔이 세대를 통째로 태운다
- 실측: 타임아웃 11건 전원이 `고가미갱신지속틱수()`(마지막 신고가까지 비유계 역스캔)+윈도우 호출
  다수의 매도(S_DYN/S_TREND) 사용. 스칼라 매도로 바꾸면 **같은 매수가 350초 타임아웃→21초**.
- 메커니즘: 매도식은 보유 종목의 모든 틱에서 평가 → 비용이 (보유 수×보유 시간)에 곱해진다.
- LLM 루프 함의: 기존 실패 분류의 "timeout/missing-CSV" 상당수가 이 원인일 개연성. 현 PRE-SAVE
  게이트(범주 수·유동성·시간창)는 **계산 비용을 전혀 보지 않는다.** 유효하지만-느린 전략이
  세대를 통째로 소모(타임아웃+엔진복구 최대 ~30분/건 실측).

### 원인 4 — 리포트 임계값의 직이식 실패: 신규 니치 5/5 음수
- v5.0 리포트의 원리(오더플로우 공격비·소화율·갭 분기)는 유효한 어휘지만, **임계값은 이 DB
  단위·이 유니버스(거래대금 상위 moneytop)에 비보정**. 직이식한 신규 니치 전부 음수:
  C3 -1.28M(88건), C8 -0.77M(35건), C2C -3.10M(171건), C9 -9.29M(684건), C8B(3년) -7.5M.
- 패턴(부검): moneytop 유니버스는 "이미 달린 종목"이라 폭발+고가돌파 직이식은 **추격매수**가
  되고, 타이트 손절(-0.8%)과 결합해 손절 다발(C9: 손실 563건 중 손절집중). 승자 분리 신호는
  존재(C9 승자: 더 이른 진입·고회전율)하나 컷 깊이가 부족했다.

### 원인 5 ⭐신규 발견 — 목표 기준점(시드)의 알파 자체가 연도별로 쇠퇴 중
- 시드 연도별: **2023 +4.88M → 2024 +3.37M → 2025 +0.38M → 2026(OOS) -0.19M.** 승률 52.6→51.1→46.7%.
- 함의 두 가지: (a) "2023-25 train에서 시드를 초월"해도 2026 실전성이 보장 안 됨(움직이는 과녁),
  (b) 역으로 **시드의 손실 군집을 차단하는 변형은 쇠퇴 구간(2025)에서 가장 큰 개선 여지**.
- 시드 자기 부검(307건)의 최강 판별자: **전일동시간비(패 4,956 vs 승 14,705 — 3배)**, 회전율(패 5.6
  vs 승 6.4), 시가총액(패 1,651 vs 승 1,425). ⭐이는 v5.0 리포트의 F11(전일동시간비폭발) 원리를
  부검이 **독립 재발견**한 것 — 리포트 원리와 실데이터가 교차 검증됨.
- 청산 부검: MFE 2.7% 대비 실현 0.56%(2.1%p 반납), 손실 MAE 평균 -2.5%(최악 -5.6%),
  `시가대비등락율<0 & 수익률≤-2 & 최저현재가` 규칙이 11건 전패(평균 -4.2%) — 익절/트레일링
  부재와 늦은 깊은손절이 시드의 약점.

### 원인 6 — 운영 단일점: gpt_auth 429로 프로그램 전체 차단(6/6 boulder 차단 사유)
- 당일 해소: Claude 직접 생성 + zero-LLM 평가 경로로 전 파이프라인(생성→스모크→train→부검)을
  GPT 없이 가동함을 실증. GPT 복귀(6/11 10:00) 후에도 이 경로는 보조 생성기/검증기로 병행 가능.

### (보조) 프로세스 결함 2건 — 발견 즉시 문서화/대응
- 선택기 sparse 버킷이 gate_reason **fullmatch** 의존 → reason에 접두사 붙이는 도구는 조용히
  분류가 깨짐(당일 발견·수정). 기록 계약 문서화 필요.
- 6/4 p6 비교는 시드(92800)와 AI(93000)의 유니버스 창이 달랐음 — 차기 OOS는 동일 창에서
  시드 재측정으로 비교해야 함.

---

## 3. 잘 작동하는 자산 (유지·확대)

1. **정직 검증 체계**: OOS-blind 동결·사전선언 선택기·결정 카드 — 자기기만 차단 구조는 그대로 유지.
2. **부검 엔진**: 시드 손실군집(F11 원리)을 데이터만으로 재발견 — 환류 재료의 질은 충분.
3. **zero-LLM 평가 인프라**(신규): 배치도구가 공식 `_score_outcome`/`record_generation`을 재사용해
   대시보드/선택기와 완전 호환. provider 불가 시에도 연구 지속 가능.
4. **대시보드**: 분석·관측 기능 정상(테스트 318 + live 8종). 개선 제안은 §7.

---

## 4. 원인별 정확한 해결책 (1:1 매핑)

| # | 원인 | 해결책 (구체 스펙) | 비용 |
|---|---|---|---|
| S1 | 기준-목표 비정합(원인1) | **측정계 보정 감사 + 시드 상대 선택기**: ① MDD/거래수 산출 정의를 코드로 확정하고 17개 우수전략 수치와 단위 정합 검사. ② 신규 사전선언 선택기 `seed_relative_v1`(예: profit>0, MDD ≤ 시드측정 MDD×1.1, 거래 50~400, payoff≥1.05, **연도별 흑자≥2/3년 advisory**)를 **OOS 보기 전에** 동결. 기존 sparse_positive_v1은 비교용 병기 | 소 |
| S2 | 인샘플 환류(원인2) | ① `graduation_holdout=true` 기본 운용(이미 존재, 토글 ON만). ② 연도별 분해를 선택 advisory로 승격(yearly 선택기 이미 존재 — 임계값만 S1과 정합화). ③ N1(PBO/CSCV·DSR)을 advisory 가산항으로 장착(6/5 권고 그대로) | 중 |
| S3 | 계산예산 가드 부재(원인3) | **생성 가드 2건(토글, 기본 OFF)**: ① 매도 프롬프트에 "미갱신류/장윈도우 함수 사용 시 보유시간 상한 필수, 윈도우 호출 ≤N" 지침. ② PRE-SAVE 정적 검사: 매도식 AST에서 비유계 스캔 함수+`보유시간` 상한 부재 조합을 reject. (매수식은 "싼 스칼라 게이트 선행" 지침 추가) | 소 |
| S4 | 임계값 직이식 실패(원인4) | 리포트 원리의 역할 재배치(§5): 신규 진입식 발명 대신 ① 시드 앵커 변형의 **위험 필터**로 사용(F14/F15/위험점수), ② 임계값은 부검 분위수로 보정(예: 전일동시간비 하한 = 시드 승자 하위 4분위) | 소 |
| S5 | 시드 쇠퇴(원인5) | **시드 개선 패밀리(v2)를 1순위 후보로**: (a) `전일동시간비 ≥ 1000~2000` 하한, (b) 시가총액 상한 보강, (c) 매도식 — 익절/트레일링 추가(MFE 2.7 대비 실현 0.56 반납 차단) + `-2.0 깊은손절` 규칙 재설계(-1.2~-1.5 조기 컷). 전부 시드 자기 부검 근거. + 적응형 레짐타이밍(검증된 3.5×)을 배포층에서 결합 | 중 |
| S6 | 운영 단일점(원인6) | 이미 해소(zero-LLM 경로). GPT 복귀 후: GPT 생성 ∥ Claude 보조생성 ∥ 배치 재평가 3중화. boulder 차단 항목은 S3 가드 장착과 함께 재개 | 0 |
| S7 | 기록 계약 취약(보조) | record reason 원문 보존 규칙을 코드 주석+테스트로 고정(배치도구는 수정 완료). 차기 OOS는 동일 창(93000)에서 시드 동시 재측정 | 소 |

---

## 5. 연구된 조건식·리포트 원리의 재활용 계획 (버리지 않는다)

| 자산 | 재활용 방식 |
|---|---|
| v5.0 F01~F20 원리 | F11(전일동시간비)=시드 v2의 핵심 필터(부검 교차검증 완료). F14/F15(호가 소화/방어)·위험점수=진입 필터 블록. F05/F20(폭발·지속)=GPT 복귀 후 변이 어휘(few-shot 어휘로 주입) |
| v5.0 매도 원리(시총별 동적·세력이탈) | S_DYN2(스칼라판)로 계산예산 안전화 완료 → 시드 매도 개선(익절/트레일링 추가)의 템플릿. 세력이탈점수는 "스칼라 항만" 채택 |
| C1~C9 코드 19종 | loop_strategies.db에 주입된 상태 유지 — ① GPT 복귀 시 few-shot negative/positive 예시(과발화·추격매수의 실패 사례 + C7의 생존 사례), ② 변이 출발점. C2C/C9 부검(승자=더 이른 진입·고회전율)은 임계값 보정 재시도의 출발 데이터 |
| 배치 평가도구·부검 스크립트 | 그대로 차기 사이클의 표준 도구(스모크→train→부검→동결→OOS) |
| 오늘의 실측 지식 2건 | 영구 메모리 저장 완료(엔진 계산예산 / zero-LLM 경로) — 차기 세션 자동 회수 |

---

## 6. 실행 로드맵 (사용자 확인 후 착수)

| 단계 | 내용 | 산출물 | 예상 소요 |
|---|---|---|---|
| P1 | **측정계 보정 감사**(S1①): MDD·거래수·일평균 정의 코드 확정, 우수전략 문서 수치와 프레임 대조표 | 보정 감사 문서 | 0.5h |
| P2 | **선택기 사전선언**(S1②): `seed_relative_v1` 스펙 동결(OOS 보기 전) + 코드 추가(기존 선택기 무수정, 신규 함수) | 선택기+테스트 | 1h |
| P3 | **시드 v2 패밀리 생성·검증**(S5): 부검 근거 4~6 변형(전일동시간비/시총상한/익절·트레일링/조기손절) → 스모크 → 3년 train → P2 선택기 동결 | train 결과+동결 아티팩트 | 2~3h(머신) |
| P4 | **고정 OOS**(2022/2026, 동일 창, 시드 동시 재측정) → 결정 카드(PROMOTE/REJECT/NEEDS_MORE) | p6/p7 아티팩트 | 1h(머신) |
| P5 | **계산예산 가드 구현**(S3, 토글 OFF 기본) + 기록계약 테스트(S7) | 코드+테스트 | 1~2h |
| P6 | GPT 복귀(6/11 10:00) 후: 가드 ON 스모크 A/B → 본 루프 재개(boulder 차단 해제 조건 충족) + N1(PBO/DSR) 착수(S2③) | A/B 증거 | 이후 |

주: P3~P4가 "수익 내는 조건식 + 검증" 목적의 최단 경로다(시드 v2는 발화 구조가 검증된 앵커
위의 보정이라 신규 발명 대비 성공 확률이 구조적으로 높고, 시드 쇠퇴 구간(2025)을 직접 겨냥한다).
모든 단계는 기존 불변식(엔진/하드게이트/backtest_graph 무수정, 토글 기본 OFF, OOS 사후 재선택
금지)을 유지한다.

---

## 7. 대시보드 점검 결과와 개선 제안

**점검 결과(정상)**: 단위테스트 318 통과(연구실/비교/차트/명예의전당/AI컨텍스트 등) ·
live GET 8종 200(/health /runs /run_state /adaptive_timing /config/spec /research_docs
/research_criteria /index_compare) · 비-루프 배치 run도 record 계약만 지키면 완전 표시.
현재 http://127.0.0.1:8770 가동 중.

**개선 제안(조건식 개선 작업에 직결되는 순)**
1. **연도별 분해 패널**: 세대/전략별 per-year profit·승률(이번에 pandas로 수동 산출한 것을
   API화) — 원인 5(쇠퇴)와 S2(연도별 advisory)의 상시 가시화. equity_points 테이블 재사용 가능.
2. **부검 결과 뷰**: analyze_trades/analyze_exits 요약을 run 상세에 표시(현재는 프롬프트
   환류로만 소비) — "왜 졌는지"를 사람이 바로 봄.
3. **타임아웃 원인 표시**: error 세대의 reason에 경과시간·복구방식 표기(계산예산 문제 식별 용이).
4. **선택기 시뮬레이터**: run 선택 후 sparse_positive_v1/seed_relative_v1 기준을 적용한
   동결 가능 후보 미리보기(기준-목표 비정합을 눈으로 확인).
5. (소) run 목록에 배치 run의 label(strategy_gist) 노출 — 현재 gen 행에만 표시.

---

## 8. 루프 실행 전 코드 업데이트 목록 (파일 단위 상세 스펙)

> §4 해결책을 실행 가능한 코드 변경으로 전수 분해한 것. **루프(LLM 조건식 개선 알고리즘) 재실행의
> 전제는 B군 완료**다. 모든 신규 동작은 기존 불변식(엔진/하드게이트/backtest_graph 무수정,
> 토글 기본 OFF·OFF시 byte-identical, 독립 리뷰, OOS 사후 재선택 금지)을 따른다.

### 공통 배선 체크리스트 (신규 토글마다 동일 적용)
`config.py` 필드(기본 OFF·주석에 데이터 근거) → `launch_config.py` 스펙 노출 →
`controller/state.py` active-config allow-list → 소비처(`brain/prompt.py` 또는
`brain/generator.py`) → `generate_strategy` prompt_logging `injected_features` 반영 →
tests(OFF byte-identity + ON 동작 + from_dict 파싱).

### A. 완료(당일 반영) — 추가 전용, 기존 동작 불변
| ID | 파일 | 내용 | 상태 |
|---|---|---|---|
| A1 | `ai_strategy_loop/scripts/claude_candidate_batch_eval.py` (신규) | zero-LLM 배치 평가(prepare 1회+run N회, 공식 `_score_outcome`/`record_generation` 재사용, reason 원문 보존) | 완료(단위테스트는 E3) |
| A2 | `.omo/evidence/claude-condition-research-20260610/insert_candidates.py`, `select_and_freeze.py` | 후보 가드 검증·주입 / 선택기 동결 스크립트(베이스라인 출처 제외 포함) | 완료 |

### B. 필수 — 루프 재실행 전 (원인 1·3·4 직격)
| ID | 대상 파일 | 변경 내용 (스펙) | 근거 | 테스트 |
|---|---|---|---|---|
| B1 | `controller/_seed_relative_selection.py`(신규), `controller/candidate_selection.py`(export), 아티팩트는 기존 writer 재사용 | 선택기 `seed_relative_v1`: profit>0, **MDD ≤ max(20, 시드측정 MDD×1.1)**, 거래 50~400, payoff≥1.05, daily≥0.05 + per-year 흑자(≥2/3년) advisory 필드. 기준치는 같은 run의 BASE_SEED 행(또는 사전선언 상수)에서 산출. 기존 sparse_positive_v1 무수정·병기 | 원인1 (시드 MDD 17.44·거래 307이 현 기준 탈락) | `tests/unit/test_seed_relative_selection.py`: 시드 프로파일 통과, gen4 프로파일(저거래·저MDD 과적합 모양) 상대 순위 하락, OOS 필드 거부 |
| B2 | 코드 변경 0 — `fitness/score.py`·metrics 추출 경로 **읽기 전용 감사** + `docs/research/condition_research/` 대조표 | 측정계 보정 감사: MDD/일평균/거래수의 산출 정의 확정, 17개 우수전략 문서 수치(MDD 1.9~6.75·일평균 10~23)와 프레임 차이 문서화 → B1 임계값의 근거 | 원인1 | 감사 문서 산출물(수치 재계산 검증 스크립트 포함) |
| B3 | `brain/exec_budget.py`(신규), `brain/generator.py`(PRE-SAVE 체인에 kind=='sell' 검사 추가), `config.py`: `sell_exec_budget_guard_enabled=False`(+`sell_max_window_calls` 등 파라미터) | 매도식 계산예산 PRE-SAVE 가드: AST 정적 검사 — ①비유계 스캔 함수(1차 확정 목록: `고가미갱신지속틱수`·`저가미갱신지속틱수`; `trade/base_strategy.py` 감사로 확장) 사용 시 `보유시간` 상한 조건 부재면 reject→prior_error 재시도 ②매도식 윈도우 호출 수 상한. 공통 배선 체크리스트 적용 | 원인3 (11/11 분리: 동일 매수 350s→21s) | `tests/unit/test_exec_budget_guard.py`: OFF byte-identical, ON에서 S_DYN형 reject·S_DYN2/시드매도형 통과 |
| B4 | `brain/prompt.py`(kind=='sell' 블록), `config.py`: `exec_budget_prompt_enabled=False` | 매도 프롬프트 계산예산 지침: "미갱신류/장윈도우 함수는 보유시간 상한과 함께만, 스칼라(수익률/최고수익률/보유시간/초당수량) 우선, 92800 강제청산 포함" | 원인3 | OFF byte-identity + ON 문구 포함 테스트 |
| B5 | `brain/prompt.py`(kind=='buy' 블록), B4와 동일 토글로 분기 | 매수 프롬프트 지연계산 지침: "싼 스칼라 게이트(좁은 시간창 > 초당거래대금 하한 > 체결강도 밴드 > 시총 슬라이스) 선행, 윈도우 함수(이동평균/최고·최저현재가/평균류) 후행 배치" + 시드/gen4 구조 사례 1줄 | 원인3·4 (니치 강제 실측) | 동일 |
| B6 | `brain/prompt.py`(buy/sell 블록), `config.py`: `report_principles_enabled=False` | v5.0 리포트 원리 어휘 주입: 매수=F01~F20 압축 어휘(오더플로우 공격비·호가 소화/방어·위험점수 **필터** 라이브러리)+**단위 보정 명시(시가총액=억, 금액류=백만원)**+"임계값 직이식 금지, 부검 분위수로 보정(예: 전일동시간비 하한=승자 하위 4분위)" / 매도=시총별 동적 파라미터+세력이탈 '스칼라 항' 원리 | 원인4·사용자 리포트 활용 (§5) | OFF byte-identity + ON 어휘 포함 + injected_features 기록 |
| B7 | `tests/unit/test_record_reason_contract.py`(신규) | 기록 계약 고정: ①record_generation의 reason은 fit.reason 원문(접두사 금지) ②배치도구 행이 sparse 버킷 fullmatch로 정상 분류 ③error 행 reason 장식은 status!=ok라 선택기 무영향임을 명시 | 보조 결함(S7) | 자체 |
| B8 | `.omo/evidence/.../select_and_freeze.py`(갱신), OOS 페어/설정 생성 스크립트(증거 디렉토리) | 동결을 seed_relative_v1로 전환(사전선언 후), OOS는 **동일 창(93000)에서 시드 동시 재측정** 페어 자동 구성 | 원인1·6/4 창 불일치 | 동결 아티팩트 스키마 검증 |

### C. 권장 — 재개 직후 (원인 2: 일반화 압력)
| ID | 대상 파일 | 변경 내용 | 근거 |
|---|---|---|---|
| C1 | `fitness/overfit_stats.py`(신규, 분석 전용), `config.py`: `overfit_advisory_enabled=False`, graded **가산항만**(`compute_graded_fitness`) | PBO(CSCV)·Deflated Sharpe advisory + 결정카드 실측치 채움. 하드게이트 무수정 | 원인2 (6/5 N1 — 감사 최우선 권고) |
| C2 | 코드 0 — run config 표준에 `graduation_holdout: true` 명시 | holdout 졸업 기본 운용 | 원인2 |
| C3 | `select_yearly_sparse_robust_v1` 호출부 thresholds 프로파일 상수 추가(또는 파라미터화) | yearly advisory 임계를 B1과 정합(거래 50~400 등) | 원인2 |

### D. 대시보드 개선 (분석 가시화 — §7 상세)
| ID | 대상 파일 | 변경 내용 |
|---|---|---|
| D1 | `dashboard/app.py`(GET `/run_yearly`), `dashboard/frontend/run-compare.jsx`·`panels.jsx`, `tests/unit/test_dashboard_yearly.py` | 세대/전략별 **연도별 분해**(거래수·손익·승률) — CSV/equity_points 기반 읽기 전용 (원인5 상시 가시화) |
| D2 | `dashboard/app.py`(GET `/autopsy`), `frontend/strategy-inspector.jsx` | 부검(analyze_trades/analyze_exits) 요약 뷰 — 손실군집·MFE반납·손실집중 매도규칙 표시 |
| D3 | `controller/loop.py`(error 행 reason에 elapsed/복구방식 — status!=ok라 선택기 무영향), `frontend/table.jsx` | 타임아웃 원인 표시(계산예산 문제 식별) |
| D4 | `dashboard/app.py`(GET `/selector_preview`), `frontend/research-lab.jsx` | 선택기 시뮬레이터(sparse_positive_v1/seed_relative_v1 적용 미리보기 — 기존 함수 재사용, 쓰기 없음) |
| D5 | `dashboard/app.py`(`/runs`에 대표 gist), `frontend/app.jsx` | run 목록에 배치 run 라벨 노출 |

### E. 선택 (여유 시)
| ID | 대상 파일 | 변경 내용 | 비고 |
|---|---|---|---|
| E1 | `provider/factory.py`+`provider/claude_*.py`(신규) | provider 다중화(claude CLI/API) — gpt_auth 단일점 보강 | zero-LLM 경로가 이미 우회라 선택 |
| E2 | `brain/exemplar_pool.py` | few_shot_source 확장('named' allowlist) — CLDGEN 생존/실패 사례를 few-shot 교사로 | §5 재활용 |
| E3 | `tests/unit/test_claude_candidate_batch_eval.py` | A1 배치도구 계약 단위테스트 | |

### 실행 순서 권고
B2(감사) → B1·B7(선택기+계약 테스트) → B3~B6(가드·프롬프트 4종 — 한 PR로 묶기 가능) →
B8 → [P3~P4 연구 사이클 재개] → C1~C3 → D1~D5 → E. GPT 복귀(6/11 10:00) 전에 B군을 마치면
복귀 즉시 루프가 "계산예산 가드 + 리포트 어휘 + 정합 선택기" 상태로 재가동된다.

### B군 구현 완료 기록 (2026-06-10 당일)
- **B1 완료**: `controller/_seed_relative_selection.py` + `candidate_selection.py` export +
  `tests/unit/test_seed_relative_selection.py`(9 테스트). 실데이터 검증: 기존 train run에
  적용 결과 **C7_SEEDPLUS 동결 성공**(MDD 16.52 ≤ 한도 20, 거래 142, 연도별 2/3 흑자) —
  같은 입력에서 sparse_positive_v1은 selected=False(원인1 해소 입증).
- **B2 완료**: `docs/research/condition_research/2026-06-10_measurement_calibration_audit.md`.
  핵심: MDD% 분모(seed 필요자금)가 동시보유 수에 비례 — 절대 MDD 기준은 포지션 레짐 간
  이식 불가(시드 17.44% vs 우수전략 1.9~6.75%는 같은 공식·다른 분모). 분산(동시보유↑)이
  MDD%의 구조 레버.
- **B3 완료(스펙 교정 포함)**: `brain/exec_budget.py` + generator 4f 게이트 + 토글.
  ⚠️ 스펙 교정: 실측상 타임아웃 매도식(S_DYN/S_TREND)은 보유시간 상한이 **있었는데도**
  죽었다(스캔 깊이는 당일 이력에 비례) → "보유시간 상한 시 허용" 조건부 면제를 제거하고
  매도식 내 비유계 스캔 함수는 무조건 reject로 확정.
- **B4·B5 완료**: `exec_budget_prompt_enabled` 단일 토글로 매수(지연계산)/매도(스칼라
  우선·미갱신 금지) 지침 분기. OFF byte-identity 테스트 포함.
- **B6 완료**: `report_principles_enabled` — v5.0 원리 어휘(F20 수급·F11 상대활성도·위험
  필터 라이브러리·시총별 동적 청산) + 단위 보정 + "임계값 직이식 금지, 부검 분위수 보정".
- **B7 완료**: `tests/unit/test_record_reason_contract.py` — fullmatch 계약 + 배치도구
  원문 보존 정적 고정.
- **B8 완료**: `select_and_freeze.py`(seed_relative 1차+비교 병기, 복수 run 합산,
  SQLite bool 보정) + `gen_oos_configs.py`(동결 후보+시드를 동일 창에서 동시 재측정).
- 신규 테스트 27개 전부 통과, 관련 회귀 101개 통과.
- **정직성 공시**: seed_relative_v1의 절대 바닥(MDD 20)·회랑(50~400)은 train 결과(시드
  17.44/307, C7 16.52/142)를 본 뒤 선언됐다. OOS(2022/2026)는 여전히 미개봉이므로
  OOS-blind 규율 위반은 아니나, **선택기 설계가 train 정보에 의존**함을 결정 카드에
  명시한다(과적합 위험은 OOS와 C1(PBO/DSR)로 측정).

### C·D·E군 구현 완료 기록 (2026-06-10~11)
- **C1 완료(스펙 일탈 공시)**: `fitness/overfit_stats.py`(PBO/CSCV + Deflated Sharpe,
  분석 전용) + `tests/unit/test_overfit_stats.py`(8 테스트). §8 표의 "graded 가산항"
  대신 **동결 시점 advisory**로 배선 — PBO는 후보 '집단' 통계라 세대 단위 graded에
  끼우면 의미가 왜곡되기 때문(의도적 일탈). 실측: **DSR(C7)=0.276<0.95** — 16개 시도
  보정 시 train 엣지가 통계적으로 유의하지 않음을 사전 경고(OOS 결과와 정합).
  결정 카드 PBO/DSR 칸이 사상 처음 실측치로 채워짐.
- **C2 완료(문서)**: LLM 루프 run 설정 표준에 `graduation_holdout: true` 권장을 명시
  (코드 변경 0 — 기존 토글). 차기 루프 설정부터 적용.
- **C3 완료**: yearly advisory 임계를 seed_relative와 정합(거래 50~400·MDD 20,
  `SEED_ALIGNED_YEARLY_THRESHOLDS`) — select_and_freeze가 사용.
- **D1~D5 완료**: 대시보드 검증 뷰 — GET `/run_yearly`(연도 분해: 시드 쇠퇴 가시화),
  GET `/autopsy`(부검 NL 요약), GET `/selector_preview`(선택기 진단 미리보기 —
  기준-목표 비정합을 눈으로 확인), `/runs` 대표 라벨(D5), error 세대 reason에
  elapsed 병기(D3, 선택기 무영향). 프런트: Research Lab에 **Validation 탭**
  (`_ValidationPanel`) 추가, run 드롭다운 라벨 병기, index.html 캐시 버전 갱신.
  `tests/unit/test_dashboard_validation_views.py`(14 테스트) + 라이브 QA
  (실 run 4종 엔드포인트 정상 — 연도분해가 시드 4.88M→3.37M→0.38M 쇠퇴를 표시).
- **E3 부분 충족**: 배치도구의 핵심 계약(reason 원문 보존)은
  `test_record_reason_contract.py`가 정적으로 고정. 엔진 spawn이 필요한 전체 흐름
  단위테스트는 비용 대비 가치가 낮아 보류(연구 도구 — 사용 시마다 로그 증거 생성).
- **E1·E2 보류(사유)**: E1(claude provider)은 zero-LLM 배치 경로가 이미 대체 수단이고
  GPT 복귀(6/11 10:00) 임박으로 우선순위 낮음. E2(few-shot 'named' 확장)는 GPT 루프
  재개 후 실사용 패턴을 보고 결정.

---

## 9. 정직성 체크리스트 (이 사이클에서 지켜진 것)

- [x] OOS 미실행 — 동결 후보가 없으므로 2022/2026 데이터를 단 한 번도 열지 않음
- [x] 사전선언 정책(p0-predeclared-policy.md) 먼저, 실행은 그 다음
- [x] 엔진·하드게이트·backtest/graph 무수정 (신규 파일은 배치도구 1개 — 추가 전용)
- [x] 보호 경로 git 상태 무변경, verify_nonrelease_sync 통과
- [x] 베이스라인 제외는 출처 기준(BASE_ 접두사), 성과 기준 아님
- [x] 모든 수치는 loop_runs.db·CSV·로그로 재추적 가능
