# 2026-07-04 퀀트 중간검토: gate_passed=0 원인 분해와 루프 진행성 판정 핸드오프

> 검토 시점: 2026-07-04, Plan B P5 wrong-profile 중단 직후.
> 검토 범위: `2026-07-03_ai_loop_full_implementation_session_handoff.md` 이후 커밋 4건
> (`02eb0419` 이후 `a4681b15`, `1586e751`, `c7892f1d`, `611473b5`)과 update_log,
> `.omo` 계획/증거, seed_lattice 실측 산출물 전수 대조.
> 목적: "조건식 게이트를 통과하지 못한다"는 현상이 (1) 프로세스 고장인지,
> (2) 시드 생성 오류인지, (3) 차트술사 조건식 무효인지 층위를 분리해 판정하고,
> 시드(기존/생성) → 탐색 → 개선 루프가 계속 진행 가능한지 결론을 고정한다.

## 1. 총평 (결론 먼저)

**프로세스는 정상 궤도이고, gate_passed=0 은 루프 고장이 아니라 대부분 예측
가능한 결과다.** 세 층위가 "게이트 통과 실패" 하나로 뭉뚱그려져 있어서
진단이 흐려졌다. 층위별 판정은 다음과 같다.

| 층위 | 대상 | 판정 | 성격 |
|---|---|---|---|
| 1 | 차트술사 CSS_V7 (fixcall 후) | 현재 번역 형태로는 **무효** | 조건식 품질 문제 (증거 확정) |
| 2 | 격자(lattice) 시드 576 | 생성 오류 **아님** — 승격 게이트 통과용 설계가 아닌 지도용 시드 | 기대치/게이트 설정 문제 |
| 3 | 실행/운영 | pause 판단 옳음 + 신규 결함 2건 발견 | 운영 결함 (수정 필요) |

## 2. 검토 입력 (증거 목록)

- 커밋: `a4681b15`(provider 폴백), `1586e751`(provider 진입점), `c7892f1d`(승격 보류),
  `611473b5`(격자 안전명 전환 + P5R 수리), `ae2eb028`(중단 상태 기록)
- 문서: `2026-07-03_css_v7_plan_c_t4_t5_execution.md`,
  `2026-07-03_css_v7_plan_b_precheck_timeout_diagnosis.md`,
  `2026-07-03_css_v7_root_cause_before_plan_b.md`,
  `2026-07-04_plan_b_lattice_wrong_profile_pause_handoff.md`
- 계획: `.omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md` (P1~P5R 완료, P5 paused)
- 실측:
  - `artifacts/chart_sulsa_validation_20260702/plan_c_fixcall_final_summary.json` (rejected 19 / hold 2)
  - `docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_results_tick_acceptance20_sanitized.json` (20/20 손실)
  - `docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_results_tick_full_sanitized_20260704_partial_aborted.json` (254/288, ok=238, error=16, gate_passed=0)
  - `docs/research/condition_research/research_runs/seed_lattice_20260702/lattice_sample14_feasibility_audit.json`
- 코드: `ai_strategy_loop/seeds/lattice.py` (셀/패밀리/청산 규약),
  `ai_strategy_loop/fitness/score.py` (게이트 규칙),
  `ai_strategy_loop/fitness/lift.py` (거래당 EV/lift/payoff — 미사용 상태),
  `ai_strategy_loop/config.py` (`min_daily_trades` 기본 0.5)

## 3. 층위 1 — 차트술사 CSS_V7: 현재 형태로는 타당하지 않음 (증거 확정)

fixcall 수리 후 실제 완주한 결과가 판결문이다.

| 페어 | profit | MDD | trades | 판정 |
|---|---:|---:|---:|---|
| CSS_V7 tick MASTER (fixcall) | -22,584,035 | 64.91% | 1,232 | rejected |
| CSS_V7 min RETEST_PULLBACK 콤보 (fixcall) | -7,563,121 | 51.03% | 232 | rejected |
| OPT tick/min 2쌍 | 미실행 | - | - | hold (별도 한정 검증 대기) |

판정 근거 (증거와 추론 구분):

- [증거] 저장/미러링/엔진 문제가 아니다 — 07-03 원인분석에서 catalog sha 일치,
  comparator 동일 창 15초 완주, arity 수정본 정상 완주를 이미 확증했다.
- [증거] 임계값 아깝게 미달이 아니라 구조적 대량 손실이다 (MDD 51~65%).
- [추론] 본질은 번역 손실이다. 차트술사 원전은 위치·구조·맥락을 보는 재량적
  차트 판독인데, V7 번역은 단일 시점 boolean 조건으로 평탄화했다. 맥락 필터가
  빠진 돌파/눌림 진입은 고빈도 노이즈 매매가 되고, 1,232회 거래 × 왕복비용이
  손실 규모를 만든다.

**권고**: CSS_V7 비-OPT 21건을 "완결 전략"으로 재도전시키지 않는다.
절(clause) 단위로 해체해 격자의 family_trigger / ablation 원장 입력으로
강등한다. P4의 `load_pattern_families()`(외부 패밀리 JSON 21개 공급 형식)가
이미 이 배선을 지원한다. OPT 2쌍만 한정 검증으로 hold 를 해소하면 Plan C 는
정직하게 종결된다.

## 4. 층위 2 — 격자 시드: 잘못 생성된 것이 아니라, 승격 게이트 통과용 물건이 아님

### 4.1 설계 사실

`ai_strategy_loop/seeds/lattice.py` 청산 규약:

- **TP 2% / SL 2% 대칭**, max_hold 180초(tick), force_exit 09:29
- tick DB 는 09:00~09:30 만 존재 → 전 시드가 개장 30분 스캘핑으로 강제됨

### 4.2 수학적 기대값 (추론)

대칭 배리어 + 초단기 보유 → 승률 ~50% 동전던지기 구조이며, 기대 순손익은
정확히 **-(왕복비용)** 이다. 진입 신호에 실제 엣지가 없으면 총손익은 반드시
음수로 수렴한다.

### 4.3 실측이 수학을 확인 (증거)

- acceptance20: 20/20 전부 손실, payoff_ratio 0.55~1.46 (1.0 주변 분포),
  실패 사유는 `total_profit <= 0` / `mdd > 35` / `daily_avg_trades < 0.5` 혼합.
- partial 254행: ok 238건 **전부 음수 profit**. 최고 성적 -383원(사실상 0),
  거래당 손실 -2.3만~-3.9만원 = 비용 스케일. 전형적 "엣지 없음 + 비용 잠식"
  시그니처.
- sample14 feasibility audit: 병목은 entry gate 축(market_cap_tier,
  regime_filter, family_trigger)이며 구조 결함 아님.

### 4.4 기저율 (증거)

07-02 전수 감사가 명시한 사실: **콜드 LLM 생성 88회+ 전부 OOS PROMISING 0,
유일 생존 경로였던 인간시드+힐클라임도 3틱 슬리피지에 전멸.** 이 기저율에서
조잡한 격자 시드 576개가 스모크에서 승격 게이트(profit>0 ∧ MDD≤35 ∧
일평균≥0.5)를 통과하리라는 기대 자체가 보정되지 않은 기대다.

### 4.5 구조적으로 통과 불가능한 셀 (증거)

0915 이후 밴드 × 소형주 셀은 일평균 0.2~0.3회로 `min_daily_trades 0.5` 를
**구조상 절대 통과할 수 없다**. 이 셀들의 게이트 탈락은 시드 생성 실패가
아니라 지도의 정상 측정값이다. 정제 후보 배분에서만 제외하면 된다.

### 4.6 게이트 이원화 권고

| 게이트 | 용도 | 기준 |
|---|---|---|
| 지도 게이트 (스모크) | 격자 커버리지 측정 | 셀별 거래 발생, 거래당 EV(bps, gross/net 분리), MDD 형상 |
| 승격 게이트 (정제 후) | 생존자 선발 | 기존 compute_fitness 게이트 그대로 |

`fitness/lift.py`(거래당 EV·lift·payoff)가 정확히 지도 게이트 용도로 이미
구현되어 있으나 P5/P6 경로에 배선되지 않았다. P6 coverage 산출에 반드시
사용한다. "엣지가 없다"와 "엣지 < 비용"은 gross/net EV 분리 없이는 구분이
불가능하다.

### 4.7 B3 정제 1순위 축

현재 대칭 2/2 청산은 차트술사 원전의 "손절은 짧게, 수익은 길게" 원칙과
정면 모순이다. 정제는 TP/SL 비대칭(예: TP 3~4% / SL 1~1.5%), 트레일링,
조건 기반 청산부터 스윕하는 것이 거래당 EV 를 가장 싸게 올리는 경로다.

## 5. 층위 3 — 운영: pause 판단 옳음 + 신규 발견 결함 2건

wrong-profile pause(2025Q1/warm8 결과 공식판단 금지)는 옳았다. 추가로 이번
검토에서 발견한 결함:

### 5.1 게이트 파라미터 미전파 버그 (증거)

`smoke_config_tick.json` 은 `min_daily_trades: 0.3` 인데, 실측 게이트 사유
문자열은 전부 `< min_daily_trades 0.5` (= `LoopConfig` 기본값)이다.
config JSON → LoopConfig 전파가 끊겨 있다. **공식 run 전에 수정하고,
receipt 에 실효 게이트 값을 명기해야 한다.**

### 5.2 엔진 풀 열화 스트릭 (증거)

partial run 의 error 16건은 gen 154~169 **연속 타임아웃(300초) 스트릭**이다.
개별 페어 문제가 아니라 ~150페어 이후 warm 풀 열화다(이후 resume 12쌍
청크들은 전부 ok=12). **공식 288 run 은 청크당 40~60페어 + 청크 간 엔진
재기동을 프로토콜로 고정한다.** warm64 로 늘리면 사라진다는 보장이 없다.

### 5.3 기대치 관리 (추론 — 다음 세션 오진 방지용 고정)

DB 전체기간 + warm64 재실행은 통계 신뢰도와 국면 커버리지를 올릴 뿐,
비용 잠식이 지배하는 한 부호를 뒤집지 못한다. **공식 run 에서도
gate_passed ≈ 0 이 나올 가능성이 높고, 그것은 실패가 아니라 지도 완성이다.**
P5 성공 판정문을 "게이트 통과 수"가 아니라 "144셀 커버리지 지도 + 셀별
net EV 분포 산출"로 지금 바꿔 두지 않으면, 다음 세션이 또
"게이트 0 = 고장" 오진 루프로 돌아온다.

### 5.4 min 레인 구조 노트

min DB 는 2025-04-07 시작(11개월 미만)이라 OOS 분할 여력이 얇다.
min OOS preregistration 전에 기간 산술부터 검증한다.

## 6. 사용자 질문 직답

| 질문 | 판정 |
|---|---|
| 전체 프로세스가 잘 진행되고 있는가 | 예. arity → 파일명 안전성 → no_trades 분류 → 프로파일 순서로 실결함을 잡아왔고, positive control gate_healthy 가 게이트/데이터/엔진 건전성을 증명 |
| 조건식 시드가 잘못 생성됐는가 | 아니요. 기계적으로 정상(238/254 완주, 거래 생성). 대칭 2/2 청산 설계상 스모크 승격 게이트 통과가 수학적으로 거의 불가능한 "지도용" 시드일 뿐 |
| 차트술사 조건식이 타당하지 않은가 | 현재 번역 형태로는 타당하지 않음(MDD 51~65%, 대량 손실). 완결 전략이 아니라 절/트리거 조각으로 강등해 격자 패밀리로 재활용 |
| 시드→탐색→개선 루프가 진행 가능한가 | 가능. 단 스모크=지도 게이트, 정제 후=승격 게이트로 성공 정의를 이원화하고, 5.1/5.2 결함을 공식 run 전에 수정 |

## 7. 다음 작업 — P5-profile-audit 확장 범위 (이 검토로 추가)

기존 pause 핸드오프의 P5-profile-audit 7단계에 다음 4항목을 추가한다.

1. **게이트 전파 감사**: smoke config JSON 의 `min_daily_trades`/`mdd_cap` 이
   실효 LoopConfig 게이트에 도달하는지 코드 대조 + 수정 + 실효값 receipt 명기.
2. **청크/재기동 프로토콜**: 공식 288 run 을 40~60페어 청크로 분할하고
   청크 간 warm 엔진 재기동을 config/절차에 고정. gen154~169 스트릭 재발 방지.
3. **성공 판정문 교체**: P5 공식 run 의 성공 = 커버리지 지도 완성
   (셀별 거래수·gross/net EV·MDD 분포). gate_passed 수는 참고 지표로 강등.
4. **지도 게이트 배선**: `fitness/lift.py` 의 EV/lift/payoff 를 P6 coverage
   산출 입력으로 배선 (스모크 CSV → 거래당 bps 분해).

## 8. 남은 단계 지도

| 단계 | 내용 | 상태 |
|---|---|---|
| P5-profile-audit | 프로파일 감사 + 공식 config 생성 + preflight 계획 (§7 확장 포함) | **다음 작업** |
| P5 공식 run | tick 288 (전체기간+warm64+새 run_id) → 완료 후 min 288 | 대기 |
| P6 | coverage/go_no_go/refinement(비대칭 청산 우선)/OOS(사전등록)/portfolio | 대기 |
| P7 (Plan D) | 생존 시드 풀 연구 프로그램 | 대기, 실행 금지 유지 |
| CSS_V7 후속 | OPT 2쌍 한정 검증 + 비-OPT 21건 절 단위 해체 → 격자 패밀리 공급 | P6 정제와 병행 가능 |
| F1~F3 | 증거/코드/계보 최종 감사 | 마지막 |

## 9. 금지 사항 (유지)

- `lat_smoke_tick_full_sanitized_20260704*` 결과로 생존/기각/P6 판단 금지.
- chunk08~chunk10 이어 실행 금지. min smoke 선행 실행 금지.
- OOS preregistration 없이 OOS 실행 금지. Plan D 실행 금지.
- DB UPDATE/DELETE 금지. A3/promotion/export/live/final 경로 수정 금지.
- `git add -A` 금지. dashboard 7파일, `.gjc`, unrelated `.omo` 잔재 스테이징 금지.
- CSS_V7 비-OPT 21건을 완결 전략으로 재실행 금지 (절 해체 경로만 허용).

## 10. 추천 다음 명령어

```text
$start-work .omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md

범위는 P5-profile-audit만 진행한다.
목표는 기존 2025Q1/warm8 tick smoke 산출물을 공식 판단에서 제외하고,
tick/min lattice 공식 재실행 기준(DB 전체기간 + warm64)을 검증한 뒤
새 config와 preflight 계획만 만드는 것이다.

진행:
1. docs/update_log/2026-07-04_plan_b_lattice_wrong_profile_pause_handoff.md 와
   docs/update_log/2026-07-04_quant_midreview_gate_zero_diagnosis_handoff.md 를 먼저 읽는다.
2. lat_smoke_tick_full_sanitized_20260704* run들은 smoke 참고자료로만 표시한다.
3. tick/min 원천 DB 기간을 read-only로 재확인한다.
4. [추가] smoke config의 min_daily_trades/mdd_cap이 실효 게이트에 전파되는지
   코드 대조로 감사하고, 끊겨 있으면 수정 후 실효값을 receipt에 명기한다.
5. 공식 tick config를 새 파일로 생성한다: 전체기간 + warm64 + 09:00~09:28/09:30 정책 명시.
6. 공식 min config를 새 파일로 생성한다: 전체기간 + warm64 + 09:00~15:19.
7. [추가] 공식 run을 40~60페어 청크로 분할하고 청크 간 warm 엔진 재기동을
   프로토콜로 고정한다 (gen154~169 연속 타임아웃 재발 방지).
8. pair count tick=288/min=288, sanitized name safety, DB row 존재 여부를 static gate로 확인한다.
9. [추가] P5 성공 판정문을 "커버리지 지도 완성(셀별 거래수·gross/net EV·MDD 분포)"로
   config/receipt에 명시한다. gate_passed 수는 참고 지표로 강등한다.
10. 공식 full run 전 preflight 2~4쌍 계획과 예상 시간을 산출한다.

금지:
- tick chunk08~chunk10 실행 금지
- tick 288 / min 288 full 실행 금지
- P6/P7/Plan D 실행 금지
- 기존 Q1/warm8 결과로 생존/기각 판단 금지
- CSS_V7 비-OPT 21건 완결 전략 재실행 금지
- DB UPDATE/DELETE 금지
- git add -A 금지
```
