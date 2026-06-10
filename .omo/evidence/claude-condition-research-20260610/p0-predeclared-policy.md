# Claude 조건식 연구 사이클 — 사전선언 정책 (2026-06-10)

## 배경
- gpt_auth는 HTTP 429(usage_limit)로 2026-06-11 10:00까지 사용 불가(boulder 차단 사유와 동일).
- 본 사이클은 LLM 생성 단계를 **Claude(세션 내 직접 생성)**로 대체한다. 평가는 기존
  zero-LLM 경로(seed_buy/seed_sell + max_generations=1, warm 엔진)를 그대로 사용한다.
- 조건식 시드 출처: 사용자 제공 v5.0 오더플로우 리포트
  (`STOM_0900_0930_orderflow_auto_discovery_v5_0_full_report.md`)의 F01~F20 원리 +
  인간 시드(Tick_B/S_902_905_Update_2) 구조 + gen4 통과 구조.

## 불변식 (기존과 동일)
1. 엔진 무수정(`backtest/backengine_*.py`, `back_static.py`), 하드게이트 무수정(`fitness/score.py`).
2. `backtest/graph/` 보호. 신규 도구는 추가 전용(기존 동작 byte-동일).
3. OOS 사후 재선택 금지. 후보 동결(freeze) 이전에 2022/2026 OOS 결과를 보지 않는다.
4. final_approval / export_winner / USER_ACK / KHOPENAPI / 블랭킷 taskkill 금지.

## 후보 (Claude 생성, 주입 전 공식 가드 통과 필수)
- 주입 전 검증: compile + brain.token_check.check_tokens + brain.variable_scope.check_variable_scope(tick, kind).
- 매수 8종: C1_V5C(리포트 복합 적응판), C2_F0520(거래대금 고가돌파+오더플로우 지속),
  C3_OPEN(시초 90030~90200 소형), C4_MIDCAP(gen4 개선), C5_PULLBACK(이평20 눌림 재돌파),
  C6_LARGE(대형주 추세), C7_SEEDPLUS(시드+위험필터 3종), C8_ABSORB(매도흡수 재돌파).
- 매도 3종: S_DYN(시총별 동적+이탈점수), S_FAST(시초 스캘프), S_TREND(추세 트레일링).
- 모든 시각 단위/변수는 엔진 실측(시가총액=억, 금액류=백만원, self.Buy()/self.Sell() 무인자) 기준.

## 평가 단계 (사전선언)
1. **스모크** `cldgen_smoke_2025q1_20260610`: tick 2025-01-01~2025-03-31, 09:00:00~09:30:00,
   warm 8엔진, betting 5. 후보 10쌍(베이스라인 시드/gen4 포함).
   - 탈락 규칙(사전선언): 백테 오류/타임아웃, 거래 0건, 3개월 거래수 > 600(과발화),
     profit < -1,000,000(3개월 총손실 100만원 초과).
   - 시간 제약(사전선언 보충): 3년 train의 per-run 시간은 스모크의 ~12배이므로
     스모크 run 시간 > 150초인 후보는 train 전에 지연계산(선게이트 후계산) 구조로
     재작성한다(시그널 동일 유지). 재작성판은 스모크 재실행으로 동등성·시간을 확인한다.
2. **train** `cldgen_train_2023_2025_20260610`: tick 2023-01-01~2025-12-31, 동일 윈도우,
   스모크 생존 후보만.
3. **선택기 동결**: 기존 `sparse_positive_v1`(무수정)을 train 행에만 적용해
   — 단, 베이스라인 행(strategy_gist가 `BASE_` 접두사: 인간 시드/과거 동결 gen4)은
   발굴 후보가 아니므로 **출처 기준**으로 선택기 입력에서 제외한다(성과 기반 아님).
   `p5-selected-candidate.json` 작성(oos_excluded=true). 후보가 없으면 OOS 스킵 + 차단 문서.
   - 다양성 슬롯(사전선언): 선택기 적격(eligible) 후보 중 상위 2개까지 OOS 허용.
     모든 결과 보고, 승격 판정은 후보별 독립 적용, 다중비교 사실은 결정 카드에 명시.
4. **고정 OOS**: 6/4 p6와 동일 설정(2022-01-01~2022-12-31, 2026-01-01~2026-02-28,
   16엔진, 90000~93000). 동결 후보만. 시드 베이스라인은 6/4 실측치 재사용
   (seed_2022 +2,223,554/58거래, seed_2026 -191,109/10거래).
5. **판정(6/4 P6 합격 규칙 동일)**: 두 OOS 연도 모두 AI profit>0, 합산 AI>=합산 시드,
   AI maxMDD<=시드 maxMDD, 연도별 >=20거래, 합산 >=50거래. 미달 시
   REJECT_CANDIDATE 또는 NEEDS_MORE_EVIDENCE. PBO/DSR 미구현은 advisory blocker로 명시.

## 도구
- `ai_strategy_loop/scripts/claude_candidate_batch_eval.py` (신규, 연구 전용):
  WarmBacktestSession prepare 1회 + run N회. 공식 `_score_outcome`/`record_generation` 재사용으로
  loop_runs.db에 기록(대시보드/선택기 호환). LLM 호출 0회.
- 공식 OOS run은 기존 loop CLI(max_generations=1) 그대로 사용.

## train 환류 (인샘플 한정)
- 부검/세그먼트 분석은 train CSV에만 적용해 2차 후보(v2) 설계에 사용한다.
- OOS 결과는 어떤 생성/선택 입력으로도 사용하지 않는다(읽기 전 동결 강제).
