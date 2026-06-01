# AI 조건식 루프 — 방향 재조준 + 인프라 플랜 (2026-06-01)

> **트리거**: 사용자가 `docs/reference/STOM_Good_Results/`(19개 인간 고수 시초 전략 스크린샷+분석 리포트)를 추가하고, 이를 개발 프로세스에 반영 + 대시보드 단계별 그래프 점검 + "가정(hypothesis) 루프" 도입 + 데이터/프롬프트 DB 누적 + 조건식 대시보드 열람을 요청.
> **사용자 선택 진행순서**: 인프라(Phase 1) → 가정 루프(Phase 2) → 생성 재조준(Phase 3).
> **상세 감사 근거**: 5영역 병렬 워크플로 감사(대시보드/가정/데이터누적/프롬프트DB/참고자료 정합), 2026-06-01.

---

## 0. 핵심 재프레이밍 (방향성의 근거)

그동안 "**고빈도(10~23/day)+다종목(6~12)+저MDD는 본질적으로 불가능**"이라 결론냈으나(메모리 §3.6·3.16), **참고자료의 19명 인간 고수는 실제로 달성**했다. 진짜 원인은 본질 장벽이 아니라 **잘못된 시드 템플릿 + 빠진 매도 레버**였다.

| 지표 | 인간 고수 19명 | 시드 Tick_902 |
|---|---|---|
| 시간창 | **09:00~09:30 (30분)** | 09:00~09:05 (5분) ❌ |
| 평균간격 | 30틱 | (동일) |
| 일평균거래 | 10~23 (평균17) | 0.4 ❌ |
| 동시보유 | 6~12 | 1~3 ❌ |
| 평균보유 | 200~300초 | (유사) |
| MDD | 1.9~6.75% (평균4.05%) | 1년 36% ❌ |
| payoff(매매성능지수) | 1.15~1.47 (평균1.27) | 1.44 ✅ |
| 연간수익 | 134~262% | — |
| **매도 규율** | **체결강도 30% + 이명60 20% + 수익률/최고수익률 트레일 + 매수시간 보유캡** | 체결강도 **0회** ❌ |

**결론**: ① 시드가 5분 스캘퍼라 refine가 5분 구조를 상속 → 루프 전체 고착. ② 인간 매도의 정의적 특성인 **"체결강도 페이드 청산"이 시드·프롬프트 양쪽에 없음** = 인간이 MDD 4%대를 만든 핵심 레버가 빠짐. "본질 불가"가 아니라 **레버 누락**이었다.

참고자료 검증: 스크린샷 원본은 상단 일별손익 막대(녹색 우세) + 하단 **1년 매끄러운 누적 우상향 자산곡선 + 낮은 MDD**. 이것이 `uptrend_r2` 골드 스탠더드이자 대시보드가 생성전략에 대해 보여줘야 할 곡선.

---

## 1. 불변식 (모든 Phase 공통)

- 엔진(`backengine_*`)·하드게이트(`compute_fitness`)·`backtest/graph/` **무수정**.
- 모든 신규 기능 = **config 토글, 기본 OFF, 미설정 시 byte-identical**.
- 신규 DB 스키마 = `_migrate_schema` 멱등 `ADD COLUMN`/신규 테이블, 기존 행 NULL 백필(하위호환).
- 각 변경 = code-reviewer(opus) APPROVE 후 커밋. baseline `PYTHONUTF8=1 python -m pytest tests/unit/ -q` 기존 7 failed 외 **신규 0**.
- `python scripts/verify_nonrelease_sync.py` 통과.
- gate-passed graded ≥ 1.0 불변식 유지.

---

## 2. Phase 1 — 측정 인프라 (사용자 요구 ①③) — ✅ 완료 (2026-06-01)

> 3커밋 전부 code-reviewer(opus) APPROVE · baseline 신규0 · 엔진/하드게이트 무수정.
> P1a `4b06f087` (대시보드 QualityTrendChart) · P1c `8cbe191d` (프롬프트 DB v7) · P1b `f60e04af` (숫자 델타 v8).
> phase-map "버그"는 의도된 4단계/5단계 별개 인덱스(loop.py:630)라 무변경. 거래구조(win_rate/avg_hold/distinct_symbols)·equity_points 테이블은 Phase 3(재조준 측정)와 묶어 연기.

### P1a. 대시보드 단계별 그래프 + phase 버그
- **품질지표 추이 차트(QualityTrendChart)** 신설(`dashboard/frontend/chart.jsx`): calmar·uptrend_r2·mdd·daily_avg_trades·max_hold_count·payoff_ratio를 세대축 멀티라인(지표 토글). 데이터는 이미 `state.generations[]`에 LIVE 존재 → **백엔드 무변, 프론트만**. `app.jsx` EquityOverlayChart 아래 배치.
- **phase-map 버그 수정**: backend `_PHASE_STEP`(loop.py:643, backtest_end→1) vs frontend `LIVE_PHASE_INDEX`(phase-detail.jsx:64, backtest_end→2) 불일치 → 한쪽으로 정합 + 단위테스트로 키/값 동등성 assert.
- (선택) 장기 run X축 동적화, ProcessFlowPanel 활성박스에 last_checkpoint 캡션.

### P1b. 데이터 누적 (loop_runs.db, SCHEMA_VERSION 7)
- **generation_deltas 정규화**: `_build_parent_diff`가 이미 계산하는 d_graded/d_mdd/d_trades/d_profit + d_calmar/d_uptrend_r2/d_daily_trades를 **숫자 컬럼**으로도 저장(현재 자유텍스트 1컬럼 → SQL 집계 가능). meta/analyze가 NL 빈도 대신 AVG/ORDER BY 사용.
- **거래구조 컬럼**: `win_rate`, `avg_hold_sec`, `distinct_symbols`(동시보유 추적) — outcome CSV에서 산출(엔진 무변, 읽기 전용). dispersion_term/max_hold_count 실측 채움 또는 미사용 명시.
- **equity_points 테이블(선택)**: run_id,gen_no,t_index,cum_profit,cum_pct,drawdown — CSV에서 다운샘플 적재(풀틱 금지). CSV 삭제 후에도 세대간 곡선 비교.

### P1c. 프롬프트 DB (loop_runs.db, 동일 v7)
- **prompts 테이블**: prompt_id, run_id, gen_no, kind(buy/sell), attempt, role, content, system_sha256, user_sha256, injected_features(JSON: timeframe·토글6종·base_code_sha·meta_seed유무), autopsy_feedback, prior_error, model, prompt_tokens, completion_tokens, total_tokens, created_at. FK(run_id,gen_no)→generations.
- **record_prompt** 메서드(`controller/state.py`) + `generator.py` retry 루프에서 build_messages 직후 기록.
- 토글 `config.prompt_logging_enabled=False`(기본 OFF, 미설정 시 휘발=기존 동작). 용량 가드: winner 계보만 full content, 나머지 sha.

---

## 3. Phase 2 — 가정(Hypothesis) 루프 (사용자 요구 ②) — ✅ 완료 (2026-06-01)

> 3커밋 전부 code-reviewer(opus) APPROVE · baseline 신규0 · 엔진/하드게이트 무수정 · 토글 `hypothesis_tracking_enabled` 기본 OFF.
> P2a `0a7beaa5` (코어: Hypothesis 객체+build+adjudicate+영속 v9, 31테스트) · P2b-1 `2ef5fec8` (환류 프롬프트 슬롯=루프 닫기, 17테스트) · P2b-2 `c7048b6f` (대시보드 HypothesisPanel, 13테스트).
> 부검 방향성 예측→1급 Hypothesis→P1b 델타로 자동 채택/기각(추가백테0)→환류로 refine가 빗나간 방향 반복 회피→대시보드 verdict 뱃지 노출.
> 잔여(소규모 후속): meta hypothesis_accept_rate 집계(source/metric별 채택률 → meta_seed 환류) — 연기.

**근거**: 부검(`autopsy/summarize`)은 이미 방향성 예측("체결강도 낮은 손실거래 → 기준 ↑")을 만들지만 NL 문자열로 즉시 소모 → refine가 **빗나간 가정을 반복**(§3.16-D 천장 의심 원인). 예측 vs 관측 채택/기각이 없음.

- **Hypothesis dataclass**(`autopsy/hypothesis.py`): id, gen_no, side, text, target_metric(mdd/profit/daily_avg_trades/payoff/give_back/graded), expected_direction(±1), source(discriminator/gate/exit/segment), basis(근거수치), verdict(accepted/rejected/inconclusive), observed_delta.
- **가정 수립**: `_build_feedback` 확장 — 요약기들이 NL + `List[Hypothesis]` 반환(부호=expected_direction).
- **가정 판정**: `_score_outcome` 직후·record_generation 직전 `_adjudicate_hypotheses(prev, parent_metrics, current)` — sign(observed_delta)==expected면 accepted (추가 백테 0회).
- **지속화**: generations에 `hypotheses_json` 컬럼 + 토글 `hypothesis_tracking_enabled=False`. (P1b의 hypotheses 테이블/FK와 결합 검토.)
- **환류**: prompt.py에 "직전 가정 판정" 슬롯("체결강도↑→손실↓ 예상 [기각: MDD+3.2] → 다른 변별변수 시도").
- **메타**: meta/analyze에 hypothesis_accept_rate(source·metric별 채택률) → 신뢰 높은 가정 우선.
- **대시보드**: page_data['hypothesis'] 섹션(이번 세대 가정 + 직전 판정). phase 인덱스는 불변(가드 테스트 유지).

---

## 4. Phase 3 — 생성 재조준 (참고자료 반영, 최고 연구 레버) — 🔶 코드 완료, 검증 대기 (2026-06-01)

> **핵심 발견(재검토)**: 참고자료의 상당 부분이 **이미 prompt.py에 반영돼 있었음**(_report_pattern_lines: 다종목분산 6~12·VI·호가잔량·체결강도/이동평균/수익률 청산·payoff≥1.25·MDD 3~7%; encourage_time_dispersion: 09:00~20분; dispersion/multi/min_hold 토글·config). 진짜 빠진 **유일 핵심 레버 = 체결강도 "페이드" 청산을 명시 규율로**.
> **P3-1 `cc32bb12`** (코드): 매도 체결강도 페이드 + 이동평균 추세이탈 청산 규율을 mdd_control_enabled 블록에 추가(OFF byte-identical, code-reviewer APPROVE, baseline 신규0). 인간 매도 18/19의 체결강도 사용 = 낮은 MDD의 핵심 레버.
> **P3-2 연기**: filter_gate VI/호전량 범주 = 게이트 약화 + 변수명 불확실(과한 설계 경계).
> **재조준 번들 = 기존 토글/설정을 켜는 run config** (`ai_strategy_loop/state/run_reframe_smoke_config.json`, gitignored): winner_objective=multi·dispersion ON·target_daily_trades=15·mdd_control ON(P3-1)·encourage_time_dispersion ON·require_filter_gates(min7)·require_liquidity_gate·mdd_cap 12·payoff_target 1.25 + hypothesis_tracking/prompt_logging ON(Phase1/2 인프라 관측). 1개월(2025-01)·max_gen 3·OOM 회피. **로드·토글 적용 검증 완료.**
> **🔴 잔여 = 짧은 백테 검증 실행**: 빈도(→10~23)·동시보유(→6~12)·MDD(→<7%)가 인간 템플릿으로 이동하는지 측정. 자원/시간/OOM 고려로 사용자 결정 대기.

A·B 인프라로 효과 측정. 모두 토글/프롬프트/config, 엔진 무변.
- **시간창 30분**: 시드 매수 `시분초<90500`(5분) → 09:00~09:28(엔진창 90000~92800 정합) 확장 fresh 변형 + prompt 하드 가이드(단일 분 고정 금지). encourage_time_dispersion 기본 ON 후보.
- **매도 체결강도 페이드 규율(핵심)**: prompt.py 매도 지침 + mdd_control 블록에 "체결강도/N1/평균이 꺾이거나 임계 이하 페이드 시 청산" 명시. 시드 매도에 체결강도 페이드 분기 추가 변형.
- **이명60 추세이탈 청산** 명문화.
- **다종목 분산 ON**: dispersion_enabled+dispersion_prompt_enabled+target_daily_trades=15, winner_objective='multi'(multi_daily_target=10), min_hold_symbols=6 유지.
- **게이트 인간 기준 조임**: mdd_cap 35→~10~15(단계), payoff_target 1.1→1.25, tpi_gate 검토.
- **filter_gate 범주 보강**: `vi`(VI가격·VI호가단위·라운드피겨)·`order_flow`(매수호전량·매도호전량) 추가, min_filter_categories 5→7.
- **검증**: warm 풀유니버스 09:00~09:28, require_filter_gates+과발화 PRE-SAVE 차단으로 OOM 회피, 짧은 run. 측정: daily_avg_trades 10~23·distinct_symbols 6~12·MDD<7%로 이동하는가(대시보드).

---

## 5. 인프라 주의 (재확인)
- 3년 풀유니버스 단일 warm run은 ~5세대 OOM(과발화 per-run 메모리 폭증). 크래시 후 고아 엔진 누적 → `taskkill /F /IM python.exe`(python3.exe 보존). 검증은 짧은/소형 우선.

## 6. 재개 명령어
```
ai_strategy_loop 방향 재조준 진행. docs/update_log/2026-06-01_direction_reframe_and_infra_plan.md 읽고
Phase 1(측정 인프라: 대시보드 품질추이차트+phase버그·데이터누적 델타/거래구조/에쿼티·프롬프트DB)부터.
토글 기본 OFF·엔진 무수정·code-reviewer APPROVE·baseline 신규0.
```
