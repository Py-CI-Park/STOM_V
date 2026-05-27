# AI 자율 조건식 루프 — P1~P10 + 거래빈도 게이트 세션 인계 (2026-05-27)

> **이 문서만으로 무중단 이어갈 수 있게 작성.** 먼저 이 문서 → 그다음 필요시 `docs/update_log/2026-05-25_ai_strategy_loop_HANDOFF.md`(초기 인프라/warm-pool 상세)·`2026-05-26_ai_strategy_loop_midcheck_roadmap.md`.
> 브랜치: **`STOM_Version_2U_C-ai-strategy-loop`** (off `STOM_Version_2U_C`, wt-dev). 모든 커밋 **로컬·미푸시**.
> python = **`C:/Python/64/Python31313/python.exe`** (3.13). 모든 실행에 `STOM_ALLOW_MINIMAL_SETTING=1` 필수.

---

## 0. 한 줄 요약 / 현재 위치
사람이 GUI에서 수동으로 만들던 조건식(매수/매도 tick 전략)을, **LLM(GPT-5.5, gpt auth)이 생성→백테(warm-pool)→채점→부검분석→재생성**하는 자율 루프 + 실시간 대시보드로 자동화. 이번 세션에 **로드맵 P0~P10 전부 구현 + 적합도 4단계 튜닝** 완료. **현재 핵심 목표 = "일평균거래횟수 ≥ 0.5(2~3일 1회 이상) + 흑자 + MDD≤35"** 인 일일 시스템 트레이딩 전략을 루프가 찾게 하는 것.

**최신 상태**: P7.3로 게이트를 **절대 거래수 → 일평균거래횟수**로 전환. `Run A2`(Tick_902 시드, 일평균≥0.5 게이트, 8세대) **완료** — **통과전략 못 찾음**(best=시드 gen0). 빈도↑면 손실/고MDD, 흑자면 너무 희소(gen2 +84,249·MDD8.65·20거래=0.08/일). → **빈도(≥0.5/일) vs 수익·저MDD 트레이드오프가 핵심 난제 확인**. 28분 단일포지션 셋업의 구조적 한계로 추정. 대시보드 서버 가동 중(`http://127.0.0.1:8770/ui`).

## 1. 목적 / 사용자 기준 (방향성 고정)
- 최종 목적: AI가 사람보다 더 많은 반복·더 좋은 분석으로 **수익 내는 조건식** 생산. + 결과분석·전략기록·버전경과비교·데이터누적·메타분석을 **지속 관리되는 연구 파이프라인**으로.
- **거래빈도 기준(중요, 2026-05-27 사용자 정정)**: 일일 시스템 트레이딩은 **일평균거래횟수(거래수/거래일수) ≥ 0.5**(못해도 2~3일에 1회, 거의 매일 거래). 절대 거래수 30(1년 기준)은 너무 희소 → 잘못된 목표였음.
- 최적화 목표: **절대수익 우선**(winner_objective='profit'). 위험조정(Calmar)도 옵션.
- 단순성 우선, 가산·토글(기본 안전값), 하위호환, 회귀 baseline 유지.

## 2. 아키텍처 / 코드 맵 (`ai_strategy_loop/` 패키지 + `cli/`)
- `cli/warm_session.py` — **WarmBacktestSession**: prepare(엔진32+데이터 1회 로딩 ~178s, 병렬 spawn) → run(전략만 바꿔 백테, 좋은전략 ~50s) → close. **타임아웃 시 `_reset_engines`('백테중지')+`_reload_data` 복구**. 전체유니버스 tick, GUI와 메트릭 1:1 동일.
- `cli/runner.py` — `run_backtest`(cold 경로), `_extract_metrics`(stock_bt 읽기 — **일평균거래횟수→`daily_avg_trades`, 거래일수→`day_count` 역산** P7.3에서 추가). 헬퍼들.
- `ai_strategy_loop/controller/loop.py` — `run_loop`(seed-and-refine hillclimb; warm prepare→세대루프→finally close; `if evolution_mode=='ga': return run_ga_loop`; runlock acquire/release). `_build_warm_btconfig`(BacktestConfig.timeout=max(bt_timeout,600), per-run은 bt_warm_run_timeout). `_warm_to_outcome`, `_read_strategy_code`, best/winner 갱신(winner_objective 키), page_data 발행.
- `ai_strategy_loop/controller/ga.py` — `run_ga_loop`(population K·crossover 2부모·mutation·elitism, 가드실패 시 elite복제로 K 유지). 비용 K×warm/세대.
- `ai_strategy_loop/controller/lineage.py` — 계보 트리·버전 diff(코드 namespaced 재조회)·run 비교(loop_runs.db 직접). page_data['lineage'].
- `ai_strategy_loop/meta/analyze.py`, `seed.py` — 누적 generations 집계(통과전략 공통조건·개선변경·실패패턴)→`state/meta_insights.json`. meta_seed 주입(config.meta_seed_enabled, 기본 OFF). **⚠️ 인사이트 생성이 빈 출력(버그 의심, P12 디버그).**
- `ai_strategy_loop/controller/runlock.py` — cross-process PID/lockfile(`state/loop.lock`)+stale 복구. CLI/GUI 동시 루프 차단.
- `ai_strategy_loop/autopsy/analyze.py`(진입 B_* Cohen's d + 청산 give-back/MAE), `segment.py`(시총×시간대 cross-tab + 분위수/t검정/BH 임계값, `cli/research_segments.py`·`analyzer.py` wrap), `summarize.py`(NL 피드백 + 토큰 1400자 상한). page_data['autopsy'].
- `ai_strategy_loop/fitness/score.py` — **적합도 핵심(아래 §3)**. `holdout.py`(졸업검사, graduation_holdout 토글; 일평균 게이트 미적용 — trade_count 폴백).
- `ai_strategy_loop/controller/contract.py` — LoopState(CONTRACT_VERSION=2, page_data passthrough), GenerationInfo(graded_score/gate_passed/trade_count/mdd/profit/total_profit_pct/daily_avg_trades/strategy_gist).
- `ai_strategy_loop/controller/state.py` — loop_runs.db(SCHEMA_VERSION=4, 멱등 ALTER), record_generation, current_state.json 발행.
- `ai_strategy_loop/dashboard/app.py` — FastAPI /health //status //config/spec, WS /ws, /ui, 제어 start/stop/final_approval(→export_winner), **GET /runs·/runs/compare·/strategy_code?run=&gen=**.
- `ai_strategy_loop/dashboard/frontend/` — React+Babel(빌드없음). chart.jsx(graded 추이+ProfitChart 수익률/수익금), table.jsx(이력+수익률+일평균 컬럼), code-viewer.jsx(/strategy_code fetch), panels.jsx(Autopsy/Population/Lineage/Meta/Holdout/RunCompare). connection.jsx(live/demo 분리, demo 시뮬레이터는 wsStatus=='demo'만).

## 3. 적합도 설계 (현재 최종 — fitness/score.py)
- **하드게이트(compute_fitness, 졸업/winner 자격)**: `일평균거래횟수 ≥ min_daily_trades(0.5)` AND `MDD ≤ mdd_cap(35)` AND `total_profit > 0`. (daily_avg_trades 없으면 trade_count≥min_trades 폴백=하위호환.)
- **graded(compute_graded_fitness, 선택 그래디언트)**:
  - gate 통과: `1.0 + _gate_passed_term(objective)` — objective='profit'면 `profit_term`, 'risk_adjusted'면 `composite`(Calmar×R²), 'balanced'면 블렌드. 항상 ≥1.0.
  - gate 실패: `profit_term × mean(trades_term, mdd_term, uptrend_term, overtrade_term) × undertrade_factor`. 항상 <1.0.
  - `_profit_term`: **부호보존 로그압축** `z=sign(p)·log1p(|p|/scale)` → 로지스틱. 큰 적자도 단조 구별(P7.1). breakeven=0.5.
  - `trades_term`/`_undertrade_factor`: **일평균 기준**(daily_avg/min_daily; 미달 시 (비율)^2 페널티) — P7.2/P7.3.
  - `overtrade_term`: 절대 softcap(150) 기준(과진입 방지).
- **winner 선택(loop.py/ga.py)**: objective='profit'면 gate통과 중 **total_profit 최대**(동률 MDD tie-break); 'risk_adjusted'면 fit.score.

## 4. config 노브 (LoopConfig, 중요)
provider/model(gpt_auth/gpt-5.5), bt_engine_mode('warm'), bt_timeframe('tick'|'min'), bt_warm_engine_count(32), bt_full_start/end(20250101/20251231), bt_universe_start_time/end_time(90000/92800), bt_betting('5'), bt_avg_time(30), **bt_warm_run_timeout(120; wide baseline 등 느린 전략은 600 필요)**, mdd_cap(35), **min_daily_trades(0.5)**, min_trades(30 폴백), overtrade_softcap(150), seed_buy/seed_sell, bt_refine_from_best(true), **evolution_mode('hillclimb'|'ga')**, **winner_objective('profit'|'risk_adjusted'|'balanced')**, profit_weight, meta_seed_enabled(false), graduation_holdout(false), max_generations, autopsy_enabled(true).

## 5. 실행 방법
```powershell
# 대시보드(가동 중일 수 있음): http://127.0.0.1:8770/ui
STOM_ALLOW_MINIMAL_SETTING=1 C:/Python/64/Python31313/python.exe -m ai_strategy_loop --port 8770
# 헤드리스 진화 루프 (config-json 파일 경로)
STOM_ALLOW_MINIMAL_SETTING=1 C:/Python/64/Python31313/python.exe -m ai_strategy_loop.controller.loop --config-json <cfg.json> [--run-id <기존run>(resume)]
```
- **시드 복사**: production `_database/strategy.db` → 루프 DB(`ai_strategy_loop/state/loop_strategies.db`). bootstrap import 후 `save_strategy_to_db(LOOP_DB, name, code, kind)`. (Tick_902·ResearchTest_Wide는 이미 복사돼 있음.)
- 예시 config: `C:/Temp/runA2_cfg.json`(Tick_902, 일평균 게이트), `C:/Temp/runB_wide_meta_cfg.json`(wide+meta). 노브는 §4 참조해 재생성 가능.
- **단위테스트/게이트**: `python -m pytest tests/unit -q` (baseline **7 failed / ~1672 passed**, 신규 0 유지가 기준). `python scripts/verify_nonrelease_sync.py`.

## 6. 실험 결과 (검증된 발견 — 중요)
- **warm-pool**: 콜드 273s → prepare 178s + 세대당 ~50s(좋은전략). GUI와 메트릭 동일.
- **Tick_902 시드(사람 전략, +6.34%/105거래/MDD36.38/일평균0.4)** 정제 → **흑자 게이트통과 전략 도달**(구 절대게이트 기준): gen8(+537K, 20세대런), Run A gen6(+303,240·MDD24.7·65거래). **gen7(+1,180,813·MDD2.01·20거래)** = 고수익·저MDD인데 희소.
- **wide baseline(ResearchTest_Wide, −603%/42,691거래)**: 부검 기반 필터링으로 −12.4억→손익분기(−2~4만)까지 **단조 climb**(P7.1 후), 단 **흑자 plateau**(못 넘음). 데이터 풍부하나 흑자엔 좋은 시드가 유리.
- **★ 거래빈도 정정(P7.3)**: 절대게이트 winner들(gen6 0.27/일, gen7 0.08/일)은 **일평균<0.5라 너무 희소** → 새 게이트 미통과. 시드 Tick_902(0.4/일)도 근소 미달. **루프가 이제 ≥0.5/일 흑자전략을 찾아야 함**(진짜 목표). Run A2가 첫 검증.
- **타임아웃**: over-firing 변이가 fail-fast(per-run timeout)에 걸림. wide baseline(435s)은 timeout 600 필요. GA는 K배라 느림(plateau시 비현실적).
- **Run A2(일평균≥0.5 게이트 첫 실험, 8세대)**: 통과전략 0. best=시드 Tick_902(gen0, 일평균0.4·미달). gen2=흑자(+84,249)·저MDD(8.65)지만 20거래(0.08/일)로 너무 희소. 고빈도 세대(185/485거래)는 손실·고MDD. **→ ≥0.5/일 + 흑자 + MDD≤35 동시 달성이 28분 단일포지션서 매우 어려움.** 대응 후보(P-freq): 다중포지션(적정최대보유>1)·배팅 조정으로 빈도↑, 또는 임계값 현실화(시드도 0.4라 0.4로?), 또는 더 긴 진화/다른 시드.

## 7. 다음 단계 (페이지)
| 페이지 | 내용 | 우선 |
|---|---|---|
| **즉시** | Run A2(일평균 게이트, `C:/Temp/runA2.out`) 결과 분석 — ≥0.5/일 흑자 도달? | 🔄 |
| **P-freq** | 일평균≥0.5 충족하며 흑자 — **다중포지션 허용/배팅·진입조건 조정**(28분 단일포지션은 일평균 한계 가능. 리포트 우수전략은 적정최대보유 6~8개로 일평균10~23) | 1 |
| P9 | 분석 고도화(다변량/상호작용, RF 중요도 환류) | 2 |
| P11 | 과적합 검증(holdout/WFO + holdout에 일평균 게이트 적용) | 3 |
| P12 | GA 값비교 + 메타 A/B + **메타 생성 버그 수정** | 4 |
| P-seed | 좋은 시드 다양화(WideV2Final 등) 정제 | 5 |
| P-tf | tick + min 양쪽 | 6 |

## 8. 열린 이슈 / 함정
- **메타 인사이트 생성 빈 출력**(P12 디버그 필요) — meta_seed가 B run에 기여 못 함.
- **28분 단일포지션 일평균 한계**: ≥0.5/일 흑자가 현 셋업서 어려울 수 있음 → 다중포지션(적정최대보유종목수)·배팅 검토(P-freq).
- holdout은 일평균 게이트 미적용(trade_count 폴백) — 필요시 holdout_metrics에 daily_avg 합성.
- bt_warm_run_timeout: 좋은전략 120 OK, **wide/넓은 전략은 600**. over-firing은 fail-fast가 처리하되 GA서 비용 증폭.
- `_temp_*.txt`, `testsunit_exit_test_out.txt`: 세션 이전부터 있던 stray, 커밋 제외.
- baseline 7 failed는 V2.79 backtest 계약/spawn/UI cleanup 잔여(본 작업 무관, 신규 0 유지가 기준).
- bash가 PowerShell `$_` 깨뜨림 — `$_`-free 명령 또는 powershell -Command. 대시보드/루프 종료는 STOM Python31313 + spawn_main/stom_backtest.py/controller.loop 프로세스만 kill(GUI stom.py·타 프로젝트 보존).
- `.omc/`·`ai_strategy_loop/state/` gitignore.

## 9. 커밋 이력 (이번 세션, 미푸시)
```
f027c1a6 feat(P7.3): 거래빈도 게이트 — 일평균거래횟수≥0.5
bd2d58c0 fix(P7.2): sub-min-trades 페널티 — plateau 붕괴 방지
e38e208c fix(P7.1): 적자 영역 그래디언트 — _profit_term 로그 압축
fbd10934 feat(P7): 절대수익 최적화 — winner_objective
7e1987e4 feat(P10): 대시보드 강화 — 코드 LIVE + 수익률/수익금 차트
32a31b70 docs: P1~P6 실행 완료 기록
28fdce4d feat(P6): 운영·관찰 완성 — lock + run비교 + export
462744f9 feat(P5): holdout 졸업검사
34794d35 perf: warm-run fail-fast 타임아웃 분리
17af7bc1 feat(P3+P4): 연구 데이터 파이프라인(계보) + 메타분석
1c6afc79 feat(P2): GA(LLM population)
5312748d feat(P1): 부검 강화 — 세그먼트
447efc5b feat(P0): 관찰 seam contract v2 page_data
(앞선 warm-pool/seed-and-refine/튜닝: e2ca9ba8, c247a4ef, 5c4ea0f2, f0c8af32)
```

## 10. 재개 첫 행동 (compact 후)
1. 이 문서 읽기 → `git log --oneline -15`로 커밋 확인.
2. `C:/Temp/runA2.out`에서 Run A2(일평균 게이트) 결과 확인 — 세대별 일평균·수익·gate, winner 도달 여부.
3. 머신 클린 확인(`python.exe` Python31313 중 spawn_main/controller.loop 잔여) + 대시보드(:8770) 생존 확인.
4. `python -m pytest tests/unit -q`로 baseline(7 failed) 재확인.
5. 다음 단계: Run A2 분석 → **P-freq(일평균≥0.5 흑자 달성: 다중포지션/배팅/진입조건)** 우선 진행.
