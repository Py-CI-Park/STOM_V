# AI 자율 조건식 루프 — 세션 인계(HANDOFF) 문서 (2026-05-25)

> **새 대화는 이 문서를 먼저 끝까지 읽으세요.** 그다음 `.omc/progress.txt`(디스크에 있음, gitignore)와 §13의 참고 파일들을 보면 됩니다.
> 브랜치: **`STOM_Version_2U_C-ai-strategy-loop`** (off `STOM_Version_2U_C`). 모든 커밋 **로컬·미푸시**.

---

## 0. 한 줄 요약 / 현재 상태
LLM(GPT-5.5, gpt auth)이 매수/매도 전략 코드를 **생성→백테→채점→부검피드백→재생성**하는 자율 루프 + 실시간 웹 대시보드를 STOM에 구축.

### ✅ UPDATE 2026-05-25 (오후 세션) — BLOCKER 해결 + warm-pool + seed-and-refine 완료
**§6 BLOCKER 완전 해결.** 근본 원인은 CLI 경로 비효율이 아니라 **콜드스타트**였다: CLI는 매 백테마다 엔진 32개를 **순차** spawn(130초) + 데이터 재로딩(80초)하고 끝나면 죽인다(총 ~273초). 실제 연산은 GUI와 동일한 28초. **CLI=GUI 메트릭 완전 일치(betting=5에서 105거래·6.34%·MDD36.38·TPI1.03 정확히 동일)** — CLI 엔진은 정상, 앞선 불일치는 betting 인자(1M vs 5M) 때문이었다. GUI가 빠른 이유: ① `ThreadPoolExecutor` **병렬** spawn ② 엔진을 **살려둔 채 전략만 바꿔 반복**(warm-pool).

**구현·검증 완료(이번 세션):**
- `cli/warm_session.py` — `WarmBacktestSession`(prepare 1회 178초 → run 세대당 ~50초 → close). 단독 스모크: run1/run2 각 ~60초·105거래 정확 일치·엔진 누수 0.
- 루프 배선(`controller/loop.py` + `config.py`): `bt_engine_mode='warm'`(기본), `_build_warm_btconfig`, `_warm_to_outcome`, run_loop가 warm 세션을 1회 prepare→세대마다 run→finally close.
- **견고성**: run 타임아웃이 엔진을 오염시켜 다음 run을 망치던 결함 → `_reset_engines`(`'백테중지'` 핸드셰이크) + `_reload_data`로 복구. 진단+실제 루프 둘 다 검증(gen1 타임아웃 후 gen2 정상).
- **seed-and-refine**: `build_messages`/`generate_strategy`에 `base_code` + run_loop가 best 전략 코드를 출발점으로 hill-climb. `config.seed_buy/seed_sell/bt_refine_from_best`.
- 코드리뷰(opus) CRITICAL 1건(`cumulative_tokens` 사용전할당) 수정. 회귀 baseline 유지(7 failed/1480 passed, 신규 0).

**seed-and-refine 첫 실험(Tick_902 시드, warm, tick, 3세대, 792초):**
- gen0 시드 = 52초·105거래·graded 0.618·MDD36.38(하드게이트 실패)=best.
- gen1 = 타임아웃(과진입)→리셋복구. gen2 = 40초·248거래·MDD50.72·**수익 음수**(개악).
- → **인프라(빠름·견고·시드기반) 완성·증명. 남은 과제: 개선이 실제로 climb하도록 튜닝**(프롬프트가 선별성↑·MDD↓·과매매 페널티 유도; graded 가 over-firing 벌점). 시드가 best로 유지됨.

**튜닝 + 10세대 실험(2026-05-25 밤) — 첫 우승전략 확보:**
- 튜닝: `mdd_cap 25→35`, graded에 `overtrade_term`(거래수>`overtrade_softcap`(150) 감점), 프롬프트 refine 지침에 "선별성↑·거래수 유지/감소·MDD 우선" 명시.
- Tick_902 시드 warm 10세대(34분): **gen3 = 우승전략(gate 통과)** — 거래63·MDD18.58·수익+180K·Calmar0.201(시드 0.181보다 위험조정 우수)·graded1.016=best. gen4도 통과(MDD11.38). 과매매 페널티가 gen2(176건)를 정확히 강등.
- ⚠️ gen5~9는 MDD는 낮게 유지하나 **수익 음수**로 드리프트 → 프롬프트가 MDD를 과강조해 수익 희생. **다음: "MDD 낮게 유지 + 수익 양수" 동시 유도**(§7' 튜닝).
- 메커니즘 완전 증명: cold-start 50세대 0건 → seed-and-refine+튜닝+warm으로 **3세대 만에** 우승전략.

**수익+MDD 튜닝(2026-05-26) + 20세대 진화 — 시드 능가 전략 확보:**
- 튜닝: gate-failed graded를 `profit_term × mean(거래·MDD·R²·과매매)`로 → 손실 전략이 수익 전략을 못 이기게 교정(시드 0.458 > 손실 gen5 0.363). 프롬프트에 "수익 양수 유지·손절만 조이고 익절 유지" 추가.
- 20세대(61분): **우승전략 3개**(gen8·12·13). **gen8 = 시드 완전 능가**(MDD 14.16<36.38, 수익 +536,758>+318,045, 거래 61<105, gate 통과). winner=gen13(graded 1.037; MDD12.14·+230K). 
- ⚠️ **탐색 불안정(비수렴)**: 타임아웃 4회 + 극단 과매매(gen7: 343거래/−6.4M) + 과선별(gen9/14/16/18: 거래 4~23 < min 30) 오감. greedy hill-climb + 다양성 제어 부재의 증거.
- ⚠️ **선택 이슈**: gate-passed graded=`1+Calmar×R²`라 절대수익 직접 최대화 안 함 → 수익 최고 gen8(+537K)이 아닌 위험조정 gen13(+230K)이 winner로 뽑힘. 절대수익 중시하려면 통과 graded에 수익 가중 필요.

**다음 세션 최우선**(우선순위순): ① 탐색 안정화 = **GA(population/crossover)** — 불안정성이 현 최대 병목, warm-pool로 K개 병렬백테 가능 ② **부검 강화** = 세그먼트 cross-tab + 기존 `cli/analyzer.py`(분위수+t검정)·`cli/ml_factor_model.py`(RF중요도) 재사용 → 거래밴드·손실원인 구체 피드백 ③ **전략 기록·버전비교·누적·메타분석**(사용자 장기 비전; loop_runs.db 확장 + autoresearch/wiki 스킬 활용) ④ holdout/WFO 과적합 방어 ⑤ 운영 대시보드. 인프라(warm/견고/seed-refine)는 완성.
**실행법(warm seed-and-refine)**: 시드를 루프 DB에 복사(`_database/strategy.db`→`ai_strategy_loop/state/loop_strategies.db`) 후 `python -m ai_strategy_loop.controller.loop --config-json <warm+seed cfg>`. 예시 cfg: `C:/Temp/warm_seed_cfg.json` 패턴(bt_engine_mode=warm, bt_timeframe=tick, seed_buy/seed_sell, bt_refine_from_best=true, bt_betting="5", bt_warm_engine_count=32).

### (이하 원래 기록 — 역사적)
**~~현재 막힌 핵심(BLOCKER): CLI 백테가 전체 유니버스에서 23~33분으로 느림~~** → ✅ 위에서 해결(warm-pool).
**수익성(가치증명)**: cold-start 누적 ~50세대 수익 0. → seed-and-refine 인프라 완성, 개선 튜닝이 다음 레버(§7').

---

## 1. 원래 목적 / 비전 (사용자 요청)
사람이 수동으로 하던 **조건식(매수/매도 전략) 연구→생성→백테→분석→개선** 반복을, **AI(가장 선호: gpt auth)** 를 두뇌로 **목표 도달까지 자율 수행**하게 하고, 전 과정을 **웹 대시보드(Claude Design 제작)에서 실시간 관찰·제어**. 새 브랜치에서, **실제 백테를 직접 돌려가며** 단계별 검증하며 개발. 최근 2U_C 커밋/커스텀 이해.

## 2. 확정된 설계 결정 (deep-interview + 사용자 정정)
- 생성 단위 = **매수/매도 전략 코드**(strategy.db stockbuy/stocksell, 한글 변수 파이썬), 차트 수식 아님.
- 생성 = **LLM 자유 작문** + 가드레일(compile + token + variable-scope) + 사전(ai_agent) 컨텍스트.
- 적합도 = **복합 점수**: `graded = Calmar(CAGR/MDD) × 우상향도(equity R²) × gate(거래수≥N·MDD≤상한·수익>0)`. 게이트 통과시 graded=1+composite. 하드 게이트는 "졸업/우승" 기준, graded는 최적화 gradient.
- 자율성 = **완전 자율 + 최종 우승전략만 사람 승인**(=실전 투입 게이트). 백테까지만 자율, live trading은 비목표.
- provider = **GPT-5.5, gpt auth**(OpenAI표준 추상화, OpenRouter 폴백).
- 대시보드 = 모니터+제어, **시작설정 CLI=GUI 공유 스키마**.
- 과적합 가드 = holdout 졸업검사 **기본 OFF 토글**(구현됐으나 루프 미배선 — §10).
- exec 안전 = **가볍게**(과한 AST 화이트리스트 거부, 사용자 단순성 선호). token denylist + variable-scope만.
- MVP timeframe = **min**(분봉). (사용자 단순성 선호: `feedback_design_simplicity` 메모 참조)
- **백테 평가 스코프(사용자 정정 2026-05-25)**: 전체 DB **2025년 이후 전 종목** 사용, 코어(엔진) **32(또는 64)**, 시간대 **tick 090000~092800 / min 0900(00)~1518(00)** 전부. (개발용 축소: 2024 데이터 제거 + 코어 128→32/64.) ← 내가 "8종목 subset"으로 줄인 건 **잘못된 가정**이었음(전체 유니버스가 1시간이라 오판). 단, CLI 전체 유니버스가 실제로 느린 게 §6 블로커.

## 3. 아키텍처 / 코드 위치 (전부 `ai_strategy_loop/` 패키지)
- `bootstrap.py` — **import 시점에** STOM_CLI_DB_STRATEGY(루프 DB)+STOM_ALLOW_MINIMAL_SETTING=1 설정(cli.*/utility.* import 전 필수). `ensure_loop_db_engine_compat()` = 루프 DB에 빈 `formula` 테이블 보장(없으면 엔진 데드락).
- `config.py` — `LoopConfig`(provider/model/mdd_cap/min_trades/graduation_holdout/bt_scope/bt_*/target_score/max_generations/cost_cap_*/autopsy_enabled). 공유 스키마.
- `launch_config.py` — `config_from_dict`(CLI=GUI) + `config_field_specs`(GUI 폼).
- `provider/` — `factory.make_provider`, `base.chat(messages,model)->(text,usage)`, `gpt_auth.py`(로컬 프록시 127.0.0.1:18761), `openrouter.py`, `codex_proxy.py`, `chatgpt_oauth/`(Newsletter_AI 이식: token_manager/proxy_server/api_translator/oauth_login/constants).
- `brain/` — `prompt.py`(timeframe-aware + 사전 + 히스토리 + 거래빈도 지시), `generator.py`(생성→validate_strategy→token_check→variable_scope→dry_run→save), `token_check.py`(import/exec/eval/open/getattr/setattr/globals 등 거부 + 정규화AST dedup), `variable_scope.py`(timeframe별 유효변수만).
- `fitness/` — `score.py`(compute_fitness 하드 + compute_graded_fitness gradient), `holdout.py`(split_window, 기본 OFF).
- `autopsy/` — `analyze.py`(win/loss B_*14컬럼 표준화평균차 + `analyze_exits` MFE/MAE/give-back/매도조건), `summarize.py`(NL 피드백 + gate_failure_directive + exit 가이드 + error 분류).
- `controller/` — `loop.py`(run_loop: 생성→백테→채점→부검→재생성, 견고성 백스톱), `state.py`(SQLite loop_runs.db WAL + JSON 스냅샷 + 마이그레이션), `termination.py`(target/max-gen/cost-cap), `export.py`(우승→production strategy.db 명시경로, no order/account), `contract.py`(LoopState pydantic, CONTRACT_VERSION=1), `STATE_CONTRACT.md`, `history.py`(누적 히스토리).
- `dashboard/` — `app.py`(FastAPI: /health //status //config/spec, WS /ws, /ui StaticFiles, / 리다이렉트, 제어 start/stop/final_approval), `frontend/`(Claude Design React 앱), `FRONTEND_PROMPT.md`.
- `__main__.py` — `python -m ai_strategy_loop` → uvicorn 대시보드(:8770).
- `scripts/` — `e2e_smoke.py`, `build_subset_db.py`(소규모 유니버스 DB; 현재 불필요·전체 유니버스로 가야 함).
- 런타임 산출물 `state/`(loop_runs.db·min_subset.db 100MB·snapshots) = **gitignore**(추적 안 함).

## 4. 실행 방법
```powershell
# 대시보드(백엔드+프론트): http://127.0.0.1:8770/ 접속
python -m ai_strategy_loop --port 8770
# 헤드리스 루프
python -m ai_strategy_loop.controller.loop --config-json '{"bt_scope":"small_universe","max_generations":15,"provider":"gpt_auth","bt_timeframe":"min"}'
# 직접 백테(CLI) — 현재 느림(§6)
STOM_ALLOW_MINIMAL_SETTING=1 python stom_backtest.py ai-controller run --buy <전략> --sell <전략> --start 20250407 --end 20260227 --timeframe min --engines 32 --format json
```
- `python` = **Python 3.13 (Python31313)**. STOM_ALLOW_MINIMAL_SETTING=1 필수.
- gpt auth: 토큰 `~/.config/newsletter-ai/chatgpt_auth.json` 재사용(재로그인 불필요). 소스 원본 `D:\Chanil_Park\Project\Programming\Newsletter_AI\processors\chatgpt_oauth\`.
- deps 설치됨: fastapi/uvicorn/pydantic/websockets/aiohttp/requests/sklearn.
- 머신: **64 논리코어 / 32 물리코어**.

## 5. 완성된 것 (검증 증거) — US-001~007 + 수렴엔진
- Phase 0 AI 사전 / Phase 1 provider(gpt auth 라이브 OK)+생성 브레인 / Phase 2 복합적합도+자율루프(상태·종료·export·견고성) / Phase 3 부검 / Phase 4 대시보드 백엔드+프론트(Claude Design 통합, /ui 서빙 HTTP검증). 
- 수렴 메커니즘: graded gradient + 누적 히스토리 + 에러원인 피드백 + exit(매도) 부검.
- **검증**: 신규 단위테스트 ~150+, 회귀 **baseline 7**(기존 backtest 계약 스냅샷 5 + dict_set 1 + jisu 1; 내 작업 신규실패 0). 실제 gpt auth 호출·실제 백테(204 trades)·6/15/20세대 자율실행·대시보드 /health 검증.
- **부수 버그픽스**: `cli/runner.py:543` `x['len']`→`x['shape'][0]` (9384bc98 V2.79전파 회귀; 정본 GUI ui_backtest_engine.py:274와 동일). CLI 백테 데이터로딩 복구.
- 코드리뷰(opus) HIGH3/MEDIUM5 반영(exec우회 차단·대시보드 서브프로세스 hard-stop·final_approval dest 고정·CORS localhost·mdd/profit/gist 영속 등).

## 6. ⛔ BLOCKER — CLI 백테 성능
- `ai-controller run`(전체 유니버스, 32엔진): **1개월=23분, 11개월=33분.** 날짜 11배 차이에도 시간 거의 동일 → 병목은 데이터량이 아니라 **1,379종목 로딩/순회의 고정비용**.
- 좀비 아님(3.13 STOM 프로세스 0개 확인), 64코어, env 정상인데도 느림.
- **사용자는 동일 백테를 1~2분이라 함.** → 가설: **사용자의 빠른 백테는 GUI 경로**(정본 `ui_backtest_engine`)인데, AI 루프가 쓰는 **CLI 경로(`cli/runner.py`, V2.79 커스텀 적응본)가 비효율**. (그 러너에서 `'len'` 버그도 나왔음.)
- **PENDING(사용자 답변 대기)**: "1~2분 백테를 정확히 어떻게 돌리는가?"(GUI? CLI 명령? 엔진수? 전체종목?). 직접 `! <명령>`으로 시간+명령 보여주면 그 경로에 맞춤.
- **새 세션 첫 과제**: 위 답을 받아 (a) GUI가 빠르면 cli/runner.py 데이터로딩을 GUI 수준으로 최적화하거나 루프를 빠른 경로로 라우팅, (b) 그 후 루프를 **전체 유니버스**(8종목 subset 폐기)로 평가하도록 교정.

## 7. 수익성(가치증명) 현황 — US-008 (열린 문제)
- cold-start(백지 생성) 누적 ~50세대: **수익 전략 0개.** 메커니즘(탐색·위험제어·피드백·수렴)은 작동, graded는 상승추세(0.53→0.85) 보였으나 게이트 통과 0.
- best 근접: gen7 = MDD19(≤25✓)·거래91(≥30✓)·**수익만 음수**(✗). 다수 세대 과매매(MDD 200%+)·전부 손실.
- **미시도 유망 레버 = seed-and-refine**: 사용자의 검증된 production 전략(예: WideV1Final, AutoResearchBaselineCompare 등)을 **시드로 출발 → AI가 부검 루프로 개선**. 무에서 alpha 발굴보다 현실적, 사용자 원래 비전("조건식 초기선택→개선")과 일치. (사람 시드 모드는 구현됨, 실험은 전부 cold-start였음.)
- 기타 레버: 평가 스코프 현실화(전체 유니버스, §6 해결 후), 과매매-수수료 분석, 시장 윈도우 다양화, 부검 세그먼트 강화(시총/시간대별).

## 8. 부검(autopsy) — 현재 vs 사용자 기대
- **현재**: 거래를 수익/손실군으로 나눠 14개 B_* 매수시점 컬럼의 표준화평균차(Cohen's d) 랭킹 + 매도쪽(MFE/MAE/give-back/손실집중 매도규칙) → NL 피드백.
- **사용자 기대(미구현, 후속)**: 시가총액 밴드별·시간대별·특징별 **세그먼트 cross-tab 분석**("손실이 시총<X / 10:30-11:00 집중" 등). "더 연구 필요"로 합의.

## 9. 실험 로그 요약
- 6세대(단일종목5일): 진동, 수익 0, best 0.852.
- 6세대(graded+히스토리): gradient 작동 확인, exit=2(0거래) 67%.
- exit=2 진단: **0거래(진입 과엄격)→메트릭없음→status error**. 런타임 크래시 아님.
- 15세대(소규모 유니버스 N=8): graded 0.53→0.85 상승, 수익 0, gen7 근접.
- 20세대(exit 피드백): best 0.724, 수익 0, MDD 폭발 다수 — exit 피드백도 cold-start 수익성 미해결.

## 10. 알려진 함정 / 주의사항
- **bash가 PowerShell `$_`/`$var`를 깨뜨림** → `$_` 없는 명령 쓰거나 임시 `.ps1` 파일 경유. 또는 git-bash `ps`/`wmic` 사용.
- **`tail -f | grep` / `| tail` 버퍼링** → 완료 전 출력 안 보임. 진행확인은 프로세스/별도 로그로.
- **Python 3.13(Python31313) = 오직 STOM**(사용자 다른 프로젝트는 3.11/3.12 venv). 따라서 STOM 백테 프로세스만 안전 정리하려면 3.13만 종료.
- **루프 DB는 stockbuy/stocksell만** → 엔진이 읽는 `formula` 테이블 없으면 데드락 → 백테 전 `ensure_loop_db_engine_compat()` 필수.
- **env-before-import**: 루프 엔트리포인트는 `import ai_strategy_loop.bootstrap` 먼저.
- **NameError in exec → 엔진 '백테완료' 미전송 → 자식 데드락(타임아웃)**. variable_scope 가드가 사전 차단(결정적) + 백테 timeout=전략탈락 백스톱.
- **`.omc/` gitignore**(progress/specs/plans는 디스크에만). **`ai_strategy_loop/state/` gitignore**(min_subset.db 100MB 등).
- `ai-controller run` 플래그 = `--buy --sell --start --end --timeframe{tick,min} --engines --format` 뿐(시간대/divid_mode/betting은 BacktestConfig 기본값: divid_mode='종목코드별 분류'=전체 유니버스, start_time 90000/end_time 152800).
- LF→CRLF git 경고는 무해.
- **서브프로세스 reap**: 루프/백테가 크래시·강제중단 시 엔진 자식이 좀비로 남을 수 있음(코드리뷰 HIGH-2, 대시보드는 hard-stop 추가됨; 루프 백테 경로도 reap 강화 여지). TaskStop 시 3.13 프로세스가 정리됨은 확인.
- 회귀 baseline 7건은 V2.79 백테 계약 미완 마이그레이션 잔여(본 작업 범위 외).

## 11. 커밋 이력 (브랜치 STOM_Version_2U_C-ai-strategy-loop, 미푸시)
```
5ae10078 feat: 대시보드 프론트엔드(Claude Design React 앱) FastAPI 통합
a2ff734a chore: ai_strategy_loop/state 런타임 산출물 git 추적 제외
64eedc50 feat: 매도(exit) 부검 피드백 + 거래빈도 프롬프트 (수익성 공략)
fb34ad28 feat: 소규모 다종목 평가 스코프 + generations 스키마 마이그레이션
043a735b docs: AI 자율 조건식 루프 중간 점검 자료
82f89621 feat: AI 자율 조건식 생성·백테·진화 루프 + 대시보드 (ai_strategy_loop)
fd68ef7f fix: CLI 백테 shared_info 정렬 키를 V2.79 엔진 계약(shape)에 맞춘다
```
미커밋(작업트리): 이 HANDOFF 문서. (state.py 마이그레이션은 fb34ad28에 포함됨.)

## 12. 담당별 잔여
**🤖 Claude (다음 세션)**
1. **(최우선) §6 CLI 백테 성능** — 사용자의 빠른 백테 방법 확인 → cli/runner.py 최적화 또는 빠른 경로 라우팅.
2. 루프 평가를 **전체 유니버스**(2025+ 전종목, 32/64엔진, 정확한 시간대)로 교정(8종목 subset 폐기).
3. **seed-and-refine** 구현·실행(사람 시드 → 개선)으로 수익성 공략.
4. C2 holdout 졸업검사 배선(토글 재노출), LOW 5 리뷰항목, 부검 세그먼트 강화.
5. 푸시/PR(사용자 지시 시).
**🙋 사용자**
1. **(BLOCKING) 1~2분 백테 방법 알려주기**(GUI/CLI, 명령, 엔진수, 종목범위) — §6.
2. seed로 쓸 검증된 production 전략 지정.
3. 평가 게이트값(MDD·거래수·목표) / 시드 / 최종 전략 승인.
4. CPU 점유 중인 본인 서비스(webui PID 48480 등 — STOM 아님) 관리.

## 13. 참고 파일 (읽기 순서)
1. 이 문서 (`docs/update_log/2026-05-25_ai_strategy_loop_HANDOFF.md`).
2. `.omc/progress.txt` (상세 시간순 로그, 디스크에만).
3. `.omc/specs/deep-interview-ai-strategy-loop.md` (사양, Revision 2026-05-24 포함).
4. `.omc/plans/2026-05-23_ai_strategy_loop_consensus_plan.md` (합의 계획, Revision 2).
5. `ai_strategy_loop/controller/STATE_CONTRACT.md` (대시보드 계약 v1).
6. `ai_strategy_loop/dashboard/FRONTEND_PROMPT.md` (Claude Design 프롬프트).
7. `docs/update_log/2026-05-25_ai_strategy_loop_midpoint_review.md` (중간 점검, 역사적).
8. CLAUDE.md (레인 규칙: 2U_C 기준선, backtest/graph 보호, live/V3/.pyd 금지).
