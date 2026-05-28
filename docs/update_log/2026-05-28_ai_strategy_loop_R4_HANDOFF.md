# AI 조건식 루프 — R4(tick·유니버스) 인계 (2026-05-28, compact용 자급자족)

> 이 문서 하나로 무중단 재개. 브랜치 `STOM_Version_2U_C-ai-strategy-loop` / 워크트리 `C:/System_Trading/STOM/STOM_V.wt-dev`.
> 선행: `2026-05-27_universe_realignment_design.md`, `.omc/plans/ai-loop-master-roadmap.md`(통합 로드맵), `2026-05-27_ai_strategy_loop_research_improvement.md`.

---

## §0. 현재 위치 (한눈에)

목표: 사람이 GUI로 수동하던 조건식 개발을 AI가 자율(생성→백테→분석→개선) 대체해 **보고서 우수전략급**(연130~262%·매매성능지수1.25+·MDD2~7%·일평균10~23·다중보유6~12) 조건식 생산 + 실시간 대시보드 관찰.

**이번 세션 커밋 4건**(전부 baseline 7 failed/1718 passed 유지, 엔진 무수정):
- `9251b614` R0/R1 — 다중포지션 창발 실증(mhct>1) + cold/JSON daily_avg 수정 + tpi 게이트 토글
- `9c71fd5a` R-Viz1 — 대시보드 전 전략 누적 수익곡선 오버랩(GET /equity_curves + EquityOverlayChart)
- `9e4b538b` 보고서 변수패턴/철학 프롬프트 주입(brain/prompt.py `_report_pattern_lines`)
- `481d2578` R4 tick 인프라 — build_subset_db `--timeframe tick` + small_universe tick 경로

**현재 블로커(R4)**: tick small_universe 백테가 **0거래**(Tick_902 시드). 정의적 원인 규명됨 → §4.

**미커밋 없음**(전부 커밋). 작업트리 깨끗(임시 _*.txt 무해).

---

## §1. 핵심 발견 (왜 여기 왔나 — 잊지 말 것)

1. **단일종목 1/40 축소체제였음**: 루프가 `bt_scope='single_stock'`(개발속도용)이라 일평균0.4·연+5%·MDD33 — 보고서 목표의 1/40. 그동안의 gen2 winner·게이트 sweep은 **축소체제 산물(목표 무관)**.
2. **다중포지션은 seed 인자 아님 — 유니버스 창발**: `divid_mode='종목코드별 분류'`로 여러 코드 넣으면 거래 시간겹침으로 mhct 자동 창발(back_subtotal.py:106-123). R0서 mhct=2(N=8), N=30서 mhct=3 실증. seed=정규화 분모일 뿐(back_static_numba.py:59-63). **보유상한 6~12는 강제 아님·측정만**(엔진 Buy게이트 없음). → 자연창발 수용(사용자 결정).
3. **N 비례 스케일**: N=8→일평균0.8, N=30→2.6. 보고서 일10~23은 풀유니버스/대N 필요.
4. **MIN·약한시드는 음의엣지**: R3(min·N=30·Min_Study) 2회 모두 우승0. 보고서 패턴 프롬프트 주입 후 R3b는 best가 gen7(MDD6.26·일평균2)로 진화했으나 수익 −69K(엣지 부족). → **보고서 도메인=TICK·풀유니버스로 가야 엣지** = R4.

---

## §2. R4 블로커 — 정의적 진단 + 해결 옵션 (재개 핵심)

**증상**: `run_backtest_for(small_universe, tick, tick_subset N=8, Tick_902 시드)` → 5일·20일 창 모두 **0거래** ("backtest completed without metrics, csv=no").

**원인(확정)**: `관심종목`은 per-tick **데이터 플래그**(arry_code 컬럼, `dict_findex['관심종목']`). 엔진이 `if not 관심종목: continue`로 비관심 틱 스킵(backengine_future_min.py:98 등). Tick_902 첫 줄 `if not (관심종목==1): 매수=False`. **8개 liquid subset 종목이 tick 데이터에서 09:00~05에 관심종목==1 플래그가 안 돼 진입 전부 차단 → 0거래.**

**해결 옵션 (재개 시 택1, 추천=1)**:
1. **[추천·단순] fresh 보고서패턴 tick 생성** — seed 없이(seed_buy/sell 비움) `_report_pattern_lines`로 LLM이 관심종목 게이트 없는 tick 전략 생성. 관심종목 의존 제거. R4 run을 seed 없이 돌린다.
2. **관심종목 플래그 종목 subset** — build_subset_db가 관심종목==1 비중 높은 종목 선별(select_liquid_codes에 관심종목 점수 추가). 데이터 조사 필요.
3. **Tick_902 변형** — `관심종목==1` 줄 제거한 시드 복사 후 사용.

> 재개 전 빠른 확인(선택): 관심종목 게이트 없는 단순 tick 시드(예: `등락율>1`만)로 PoC 돌려 진입>0 뜨면 옵션1·3 유효 확정.

---

## §3. 아키텍처/코드맵 (변경분 중심)

- **백테 스코프**(`ai_strategy_loop/config.py`): `bt_scope` = single_stock | small_universe | universe. `bt_timeframe` = min|tick. `bt_subset_db`(None→state/min_subset.db). `bt_engine_mode` = warm|cold (small_universe는 cold). 게이트: `min_daily_trades`·`mdd_cap`·`tpi_gate`·**`tpi_gate_enabled`(신규 토글, 기본 OFF)**. `exit_quality_enabled`·`freeze_buy_on_mdd_only`.
- **small_universe 실행**(`controller/loop.py:201 run_backtest_for`, 214~251 분기): subset back-DB + `--divid-mode 종목코드별 분류`. **timeframe-aware(481d2578)**: tick이면 `STOM_CLI_DB_STOCK_BACK_TICK` env + `--timeframe tick`, min이면 MIN env. `_select_universe_window`로 날짜창. cold subprocess(stom_backtest.py).
- **subset 빌더**(`scripts/build_subset_db.py`): `--timeframe {min,tick} --size N`. min=stock_min_back.db→state/min_subset.db(div10000), tick=stock_tick_back.db(2427종목)→state/tick_subset.db(div1000000). 유동성순 N종목.
- **메트릭**(`cli/output.py` cold/JSON + `cli/runner.py:_extract_metrics` warm): trade_count·daily_avg_trades·max_hold_count(mhct)·total_profit_pct·mdd_pct·tpi 등. (cold daily_avg 누락은 R1서 수정.)
- **적합도**(`fitness/score.py`): compute_fitness 하드게이트(빈도·MDD·흑자[·tpi 옵션]) + compute_graded_fitness(선택 그래디언트, 청산레버 exit_quality_term). load_exit_quality_from_csv(payoff/give_back), load_equity_series_from_csv.
- **프롬프트**(`brain/prompt.py`): build_messages — `_timeframe_lines`(min=분당*/tick=초당* 가드) + `_report_pattern_lines`(보고서 변수범주·철학) + seed-refine(base_code)·crossover·autopsy·history.
- **루프 라이브 발행**(`controller/loop.py` run_loop): 매 세대 `_publish_live`→`state/current_state.json`→대시보드 WS.
- **대시보드**(`dashboard/app.py`): GET /status·/health·/runs·/strategy_code·**/equity_curves(R-Viz1)**, WS /ws. frontend(in-browser React/Babel, 빌드없음): chart.jsx(FitnessChart·ProfitChart·**EquityOverlayChart**)·table.jsx·panels.jsx.
- **PoC 스크립트**: `scripts/r0_multiposition_poc.py`(min, mhct 관측), `scripts/r4_tick_smalluniverse_poc.py`(tick).

---

## §4. 실행법 (명령어·환경)

전부 `STOM_ALLOW_MINIMAL_SETTING=1` + `python`(=C:/Python/64/Python31313). 워크트리에서 실행.

- **tick subset 빌드**(이미 N=8 있음): `python -m ai_strategy_loop.scripts.build_subset_db --timeframe tick --size 30`
- **tick PoC**: `python -m ai_strategy_loop.scripts.r4_tick_smalluniverse_poc` (또는 run_backtest_for 직접 호출)
- **진화 run**: `python -m ai_strategy_loop.controller.loop --config-json <cfg.json>` (cfg는 ai_strategy_loop/state/run_*.json; R3은 run_r3_config.json — bt_scope=small_universe). tick R4용 새 cfg 필요: bt_timeframe=tick, bt_subset_db=state/tick_subset.db, bt_engine_mode=cold, seed 비움(옵션1) 또는 Tick_902.
- **대시보드**: `python -m ai_strategy_loop --port 8770` (백그라운드). 관찰 `http://127.0.0.1:8770/ui/`. 코드 변경 후 재시작 필요(in-browser React라 새로고침). PID는 `ai_strategy_loop --port 8770` 매칭으로 찾아 Stop-Process.
- **baseline**: `python -m pytest tests/unit/ -q` → **기대: 7 failed / 1718+ passed**(7 failed가 baseline, 신규 0이어야 함). 브랜치게이트: `python scripts/verify_nonrelease_sync.py`.
- **시드 복사**(_database/strategy.db→loop DB): r0_multiposition_poc.py의 `_copy_seed_to_loop_db` 재사용. 시드명: Min_B/S_Study_251227(min), Tick_B/S_902_905_Update_2(tick).

---

## §5. 제약·게이트·함정 (반드시 준수)

- **엔진(backtest/*.py, numba) 무수정**이 기본. 게이트/적합도 변경은 토글·하위호환(기본 OFF=기존 동작 보존). baseline 7 failed 유지(신규 0).
- **timeframe 가드**: min에 초당*, tick에 분당*/RSI 등 쓰면 백테 NameError 죽음. 프롬프트가 동적 안내하나 검증 필수.
- **다중포지션은 자연창발**(seed 인자/엔진게이트 없음). 보유상한 강제 원하면 엔진 수정=별도스코프+사용자확인.
- **커밋은 사용자 승인 시**. 커밋 메시지 끝: `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`.
- **프로세스 안전**: STOM-dev는 Python31313. 좀비 정리는 31313의 spawn_main/controller.loop만. Python3119(타 프로젝트)·GUI stom.py·대시보드(31313, controller.loop 아님)는 보존.
- `backtest/graph/` 보호 결과데이터. CLAUDE.md 금지: CLI child lane/.pyd/live/V3.
- **runlock**: 동시 루프 차단(cross-process). 락 든 채 dashboard start-control 테스트는 transient 실패(아티팩트). state/loop.lock stale면 삭제 가능.
- **tick 백테는 무겁다**(stock_tick_back 29GB): subset N·window 작게 시작. 풀유니버스는 ~1시간/세대.

---

## §6. 재개 첫 행동 (권장 순서)

1. 이 문서 + `.omc/plans/ai-loop-master-roadmap.md` 읽기. `git log --oneline -6`로 커밋(481d2578까지) 확인.
2. **R4 옵션1(fresh 보고서패턴 tick)**: (a) 빠른 확인 — 관심종목 게이트 없는 단순 tick 시드로 PoC 진입>0 확인. (b) tick subset N=30 빌드. (c) R4 cfg(tick·small_universe·cold·seed 비움·tpi_gate_enabled·다중포지션·report패턴 프롬프트) 작성. (d) 대시보드 기동. (e) run_loop 실행→라이브 관찰. (f) 우승/SUMMARY 보고.
3. 진전 시: N 확대·풀유니버스(universe scope, ~1hr/gen)로 R4 검증. CPCV/holdout 과적합 검증(로드맵 R3.5).
4. baseline 7 유지·커밋은 승인 시.

---

## §7. 커밋 이력 (이번 체인)
`319baf01`(P1-P10 핸드오프) → `a5fd7176`(청산레버+freeze_buy) → `e870169f`(대시보드 청산품질) → `88932e29`(연구문서) → `4f218dcf`(재정렬설계+게이트sweep) → `9251b614`(R0/R1) → `9c71fd5a`(R-Viz1) → `9e4b538b`(보고서패턴 프롬프트) → **`481d2578`(R4 tick 인프라)**.

목표 임계값(조정가능): 일평균≥8~10·MDD≤7%·매매성능지수≥1.25·연수익≥130%. (N=30 dev 스케일에선 일평균~2.6라 게이트 하향 조정해 진화; 풀스케일은 풀유니버스.)

---

## §8. R4 실행 결과 + 진단 정정 + R5 (2026-05-28 이어서)

> §2의 "관심종목 게이트가 블로커" 진단은 **틀렸다**. 아래가 정정·최신 상태다.

### 8.1 진단 정정 (관심종목 → 시가총액)
- **관심종목은 블로커가 아니다**: tick subset 데이터에 관심종목=1이 **50~67%** 존재(09:00~05에도 종목당 6.2만~9.2만 틱). 엔진 `tick.py:88 if not 관심종목:continue`는 통과한다.
- **진짜 블로커 = 시가총액 미스매치**: `Tick_902`는 `if 시가총액<3000`(소형주)에서만 매수하는데, `build_subset_db`(유동성=거래대금순 선별)는 전부 **대형주**(평균 3~6.6조)라 시총<3000 틱이 ≈0 → 매수=False 고정 → 0거래.
- **실증**: 시총 제약 없는 느슨 전략 PoC → trade_count 12>0.

### 8.2 R4 진화 결과 (run=r4tick1, N=8 대형주 tick, 8세대, 18분)
- 파이프라인 **전부 정상**(fresh 생성→tick 백테~103s→채점→대시보드 라이브).
- **winner 0**: 전 세대 음의 엣지. plateau graded~0.489(gen4: MDD3.84·trades18·수익−36K). 빈도는 보고서급(gen0 93거래=일평균18.6, 목표10~23 안)·MDD제어OK(1~3.8%)지만 흑자 미달(R3 min과 동일).

### 8.3 R5 — 소형주 도메인 + 윈도우 개선 (사용자 선택)
- **소형주 선별 스캔**: 소스 tick DB 전체 2425종목 중 **1878종목**이 소형주 아침(시총<3000&관심&09:00-30) 활동. top-12로 `state/tick_subset_small.db`(524MB) 빌드.
- **Tick_902 isolation = 0거래(N=12)**: richest 윈도우(시총<3000 아침틱 41,747 충족)에서도 0거래. **병목은 시총/윈도우가 아니라 Tick_902의 ~10조건 AND 체인** — 12종목 규모에선 진입 confluence가 안 생김.
- **🔑 구조적 결론**: **선택적 보고서 전략은 풀유니버스(~1379종목)·1년 규모가 본질**. dev-scale(N=8~30) small_universe로는 재현 불가. (느슨 전략은 dev-scale서도 발화하나 음의 엣지.)
- **윈도우 선택 개선(커밋됨)**: `_select_universe_window`가 '가장 이른 N일'만 골라 데이터 빈약 → `config.bt_window_select` 토글 추가(`earliest`기본=하위호환 / `richest`=moneytop coverage 최대 연속구간). 테스트 4/4, 회귀 0.

### 8.4 baseline 진실 (중요)
- 문서상 "7 failed"는 **stale**. 현재 환경 진짜 baseline = **34 failed / 1691 passed**. 추가 33개는 전부 `tune/sweep/wfo/setting/report/optimizer/db/formula/exit_codes/backtest_contract` 등 **cli·ui 도구 테스트**(ai_strategy_loop 무관, 이번 세션 이전부터 존재 — 환경/의존성 드리프트로 추정). 윈도우 개선은 +1 pass·신규 실패 0으로 검증.

### 8.5 다음 단계 = 풀유니버스 (사용자 결정)
- `bt_engine_mode="warm"`(WarmBacktestSession, 엔진 32개) + `bt_timeframe="tick"`로 풀유니버스 Tick_902 검증 → fresh 진화. 세대당 ~1시간. prepare 비용 큼(tick 29GB) — 먼저 1회 warm 백테로 Tick_902가 풀유니버스서 흑자/보고서급인지 확인 후 진화.
- 보조 자산(gitignored, 로컬): `state/run_r4_config.json`(N=8 대형주 fresh), `state/run_r5_config.json`(N=12 소형주 fresh+richest), `state/tick_subset_small.db`(소형주 N=12). 진단 스크립트는 워크트리 `_temp_*.py`(커밋 제외).
