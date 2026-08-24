# AGENT HANDOFF — STOM AI 조건식 자율진화 (에이전트 무관·자기완결)

> **[최신 정본 우선]** 이 문서는 역사 기록으로 보존된다. 현재 통합 지점과 재개 절차는
> `docs/research/quant_scoring_pipeline/2026-08-25_BOOT-01_PIPE-01_환경사전점검과_LT3000_실패원장.md`,
> `docs/research/quant_scoring_pipeline/HANDOFF_2026-08-24_process_research_pipeline_재출발.md`,
> 전체 UX/UI·파이프라인·백테스트 후 분석·연구 계획은
> `docs/research/quant_scoring_pipeline/2026-08-24_process_research_pipeline_재출발_대시보드_연구_성숙화_마스터플랜.md`
> 를 먼저 읽어라. 기준 통합은
> `loop/process-research-pipeline @ f75b80ebcb7fd72cd41c8933c4f6e63df8c2ae52`,
> 재출발 브랜치는 `codex/process-research-pipeline-restart`다.
> BOOT-01·PIPE-01은 완료되었으며, `<3000` 정정 집계는 지표 생성 2 / 정상 무거래 0 / 실행 오류 6 / timeout 2다. 다음 한 단위는 `SYS-01A Research Truth Contract`다.
> 아래 본문의 날짜·HEAD·브랜치는 2026-06-03 기준 역사값이다.

> **이 문서는 어떤 AI 에이전트(Claude·Codex·Gemini 등)든 이 작업을 콜드로 이어받기 위한 자기완결적 핸드오프다.** Claude 전용 메모리(`~/.claude/...`)에 의존하지 않는다. 상세는 `docs/update_log/`를 가리키되, 이 문서만으로 방향·제약·현황·다음 단계를 파악할 수 있다.
>
> **갱신**: 2026-06-03 · **브랜치**: `STOM_Version_2U_C-ai-strategy-loop` · **워크트리**: `STOM_V.wt-dev` · **HEAD 근처**: `f63241c3`(핸드오프 docs) 위 — `447febd3`(T2)·`d22efe89`(T3)·`8f1ea7fa`(T4)·`a4b8de59`(보유종목수)·`b097aa7c`(T1)·`a45a7502`(T0).

---

## 0. 프로젝트 정체성 (왜 이 작업이 있나)
`ai_strategy_loop/`는 **주식 단타 조건식(매수/매도 전략 코드)을 LLM으로 자율 생성 → STOM 공식 백테 엔진으로 평가 → 채점 → 부검 → 반복**하는 자율진화 연구 시스템이다. **북극성 = 인간 고수가 만든 좋은 조건식(`docs/reference/STOM_Good_Results/` 17개 스크린샷, 전부 tick·09:00~09:30·일평균10~23·동시보유6~12·MDD1.9~6.75%) 수준 또는 그 이상을 자율로 만들고, 앞으로도 자율 개선하는 시스템.**

핵심 도메인 사실:
- **시드 전략 `Tick_B_902_905_Update_2`**(매수)+`Tick_S_902_905_Update_2`(매도) = 09:02~09:05(3분) tick 스캘퍼. 운영 DB `_database/strategy.db`에 byte-동일 존재(실배포 가능 자산). **다년(2022~2025) 연속 흑자·누적 우상향 r²0.90 = 견고한 골드.**
- **902=09:02(시분초 90200)·905=09:05.** tick 데이터는 09:00~09:30만 존재(`_database/stock_tick_*.db`). 1분봉(min) 데이터는 09:00~15:19(`_database/stock_min_back.db`).

---

## 1. 🔴 어떻게 이어받나 (자기완결 재개)
1. 이 문서 + `docs/update_log/2026-06-03_tick_program_complete_handoff.md`(직전 세션 상세) + `docs/update_log/2026-06-02_comprehensive_review_and_redirection.md`(방향성 종합검토) 읽기.
2. 현재 상태(§3) + 불변식(§2) 확인.
3. **다음 작업(§6)**: 토글 ON 다년 연구 run 실가동 + 2022/2026 OOS 분리검증 = 실제 인간 reference 능가 여부 정직 판정.
4. 변경마다 불변식(§2) 준수.

---

## 2. 🔒 하드 불변식 (절대 — 위반 금지)
| # | 불변식 | 이유 |
|---|---|---|
| 1 | **엔진 무수정**: `backtest/backengine_*.py`·`backtest/back_static.py`(`GetBuyStg`/`GetSellStg`) | 공식 백테 엔진. 전략코드는 정규형(`매수=True`→`if not(cond): 매수=False` 체인)으로 as-is exec |
| 2 | **하드게이트 무수정**: `ai_strategy_loop/fitness/score.py` `compute_fitness`(졸업/우승 PASS/FAIL) | 평가 기준선. 신규 지표는 `compute_graded_fitness`(gate-실패 분기) 가산만 |
| 3 | **`backtest/graph/` 무수정** | 보호된 결과 데이터(소스 아님) |
| 4 | **신규 기능 = config 토글 기본 OFF, OFF일 때 byte-identical** | 운영 동작 무변경 보장 |
| 5 | **각 변경 = 독립 code-reviewer APPROVE** (저자/검토 분리) | 자기승인 금지 |
| 6 | **결정론 baseline**: `PYTHONUTF8=1 python -m pytest tests/unit/ -p no:randomly -q` → 기존 **7 failed**(백테 spawn/UI 계약, 무관) 외 **신규 0** | 회귀 차단 |
| 7 | **`python scripts/verify_nonrelease_sync.py` 통과** | 비정식 워크트리 동기화 가드 |
| 8 | **블랭킷 `taskkill /F /IM python.exe` 금지** | 무관 python 프로세스 상주(`.omc/research` 워커·MCP·web.main·대시보드·타 프로젝트). 외과적(loop PID만) 정리. 클린 exit은 엔진 자동정리 |
| 9 | **V3 마이그레이션 금지·research/init 전파 금지** (`CLAUDE.md`) | 이 레인은 2U_C 최종 기준선 |

검증 사이즈: `python` 사용(이 머신은 `python`에 pandas 등 의존성, `python3` 아님). `PYTHONUTF8=1` 필수(cp949 회피). git index.lock stale 시 `rm -f C:/System_Trading/STOM/STOM_V/.git/worktrees/STOM_V.wt-dev/index.lock`.

---

## 3. ✅ 현재 상태 — TICK 우선 프로그램 T0~T4 완료
인간 reference가 전부 tick이라 **tick 09:00~09:30 전체 창**으로 자율진화 인프라를 구축(루프 시드 902는 3분만 써 고착돼 있었음). 6커밋, 각 단계 실DB 스모크로 실증, 전부 불변식 준수.

| 단계 | 커밋 | 무엇 | 실증 |
|---|---|---|---|
| T0 창/시드 확장 | `a45a7502` | classification 프롬프트 시간창 09:28→09:30·902 고착해제 | 생성 gen1 91거래 09:00~09:19 gate PASS·+685k·MDD6.59 |
| T1 퀀트분석+시각화 | `b097aa7c` | 등락률 분석 축 + 대시보드 히트맵/막대(`analysis.jsx`) | 등락률 급등+490k/초급등+674k vs 상승(3~6%)−459k적자·시간대 0905-0910 골든(승률57%) |
| 보유종목수 버그수정 | `a4b8de59` | 무거래 세대 동시보유 0→"거래없음" 구분 | 대시보드 풀렌더 |
| T4 반복 정제 폐루프 | `8f1ea7fa` | 패배 세그먼트 → 생성 매수 프롬프트 avoid 환류(`segment_feedback.py`·토글 `segment_feedback_enabled`) | 실데이터 avoid 6라인(3~6% 적자 등) |
| T3 넓은생성 강화 | `d22efe89` | 시간창 값범위 측정(`filter_gate.time_window_bounds/span_sec/is_noop`·합집합 envelope·토글 `require_meaningful_time_window`) | g1=09:00~09:20·시드902=09:02~09:05(좁아도 no-op 아님). **스모크가 교집합 반전버그 잡아 합집합 수정** |
| T2 백파인더 원리 | `447febd3` | headless lookahead 채굴(`backfinder_principle.py`)→승리셋업 분포→BandSpec 시드 | 실DB 24,229행·129승자·**최고셀 lift 8.99**·승리셋업 등락율 q25~q75=−1.5~5.4·체결강도 116~180 |

추가: **S0 min 풀세션 토글**(`8148467b`, `full_session_enabled`+`bt_min_universe_end_time=151900`, warm스모크 ON=40거래 09:29~15:18/OFF=0거래)도 보존.

**실증된 폐루프**(사용자 비전): ①넓은생성(T0) → ①퀀트/시각화 정제(T1) → ③백파인더 시드(T2) → 반복 avoid 환류(T4), 시간창 측정(T3)로 가시화.

**⚠️ 정직한 한계**: 인프라는 완성·작동하나, **이 토글들을 ON으로 켠 다년·풀유니버스 연구 run + OOS 검증은 아직 안 함** = "실제로 인간 reference를 능가하는지" 미판정. 신규 토글 전부 기본 OFF라 **현 운영 동작은 무변경**.

---

## 4. 🧭 핵심 연구 GROUND-TRUTH (반드시 알고 시작 — 헛수고 방지)
과거 세션들이 실증·반증한 비가역 사실들. 이걸 모르면 같은 실패를 반복한다.

1. **정적 코드로 "좋은 전략"을 판별 불가** (R7.4·§3.14·§3.15, 매수+매도 양쪽 반증). 흑/적을 가르는 건 코드가 아니라 **시장 레짐**. → 정적 품질 게이트/reject로 "수익 보장" 시도 금지. 구조 게이트(과발화 차단·범주 수·no-op 탐지)는 OK, 품질 판정은 불가.
2. **시드 Tick_902는 다년강건 골드** (2024 Q1 +1.55M·2025 Q1 +1.94M 2년연속). AI refine은 **정직한 1년/OOS 평가서 시드를 못 이김**(연 +318K·MDD36·calmar0.18). 1개월 "보고서급"은 우호창 과적합.
3. **가장 배포가능한 검증 결과 = 적응형 레짐타이밍**(시드 자기 자본곡선 추종: 직전 lookback개월<0이면 OFF). 다년 2022~2026 진짜 OOS서 **위험조정 3.5배**(MDD −71%). 인과적·AI불필요. 토글 `adaptive_timing_enabled`(분석전용).
4. **도메인주입이 fresh 생성을 구제**: classification(시간×시총×등락률) + filter_gate(범주 AND) + few_shot(seed_db 인간전략)이 백지붕괴(§3.17)를 막아 viable·다양·강건 전략 자율생산. 단 AI도 윈도우/레짐 과적합(교차연도 실패)=인간 공통 시장구조 난제.
5. **앙상블/보완**: AI는 시드 *대체*가 아니라 *보완*(시드 약세월 메우기). 2025 H1 앙상블 +79%/MDD−58%이나 **2024 OOS 고정전이 실패** → 전방은 적응형만 유효.
6. **"인간 초월"은 탐색이지 보장 아님**. 레짐강건은 **holdout/다년 OOS로만** 확보. 게이트통과 ≠ 수익(불변).
7. **백파인더(T2) 시드는 lookahead/survivorship 편향** → 생성 시드 전용, OOS 검증 필수.
8. **OOM**: 3년 풀유니버스 단일 warm ~5세대 한계(과발화 per-run 메모리 폭증). 1개월 백테 ~20s 안전. tick 30분창은 가벼움. 크래시 후 고아 엔진 외과적 정리 필수.

---

## 5. 🗺️ 아키텍처 빠른 지도
- **CLI 진입**: `python -m ai_strategy_loop.controller.loop --config-json <cfg.json> --run-id <id> --max-gen <N>`
- **생성**: `brain/prompt.py`(프롬프트·classification/avoid/dispersion 블록)·`brain/generator.py`(PRE-SAVE 게이트 사슬)·`brain/filter_gate.py`(범주·시간창 측정)·`brain/variable_scope.py`(timeframe 허용변수)·`brain/segment_feedback.py`(T4)·`brain/band_compiler.py`+`seed_902_band.py`(밴드 P0)
- **채점**: `fitness/score.py`(`compute_fitness` 하드게이트·`compute_graded_fitness`)·`fitness/edge_ratio.py`·`feature_importance.py`·`adaptive_timing.py`·`backfinder_principle.py`(T2)·`multiyear.py`·`holdout.py`(전부 분석/가산·게이트 무영향)
- **루프**: `controller/loop.py`(`run_loop`·`_build_warm_btconfig`·warm 엔진)·`controller/state.py`(loop_runs.db·loop_strategies.db)·`config.py`(LoopConfig 토글)·`launch_config.py`(대시보드 폼)
- **백테**: warm 모드(엔진 1회 prepare→세대마다 run). tick=`stock_tick_back.db`·min=`stock_min_back.db`(env `STOM_CLI_DB_STOCK_BACK_TICK/MIN`로 subset 오버라이드 — warm은 launch 시 명시 필요).
- **대시보드**: `python -m ai_strategy_loop` → `http://127.0.0.1:8770/ui/`. 프론트(`dashboard/frontend/*.jsx`)는 StaticFiles 디스크 즉시서빙(재시작 불요). **새 백엔드 모듈/엔드포인트는 재시작 필요**(uvicorn 무reload). run 셀렉터로 임의 run 분석 열람.
- **검증 run 프로파일**(gitignored, `ai_strategy_loop/state/run_*config.json`): `run_tickwide_config.json`(T0 넓은생성 토글 ON 예시)·`run_minfullsession_config.json`(S0).

---

## 6. 🔴 다음 작업 (권장 순서)
1. **(최우선) 토글 ON 다년 연구 run + OOS**: `run_tickwide_config.json` 패턴으로 `classification_generation_enabled`+`require_filter_gates`+`encourage_time_dispersion`+`few_shot_enabled`(`few_shot_source=seed_db`)+`segment_feedback_enabled` ON, `bt_timeframe=tick`, 09:00~09:30, 다월(또는 2023~25 multiyear), `max_gen`↑. 진행 중 T1 대시보드 히트맵으로 패배구간 보고→T4 환류→재생성. **2022/2026 OOS 분리검증으로 인간 reference 능가 여부 정직 판정.** (OOM 주의: 풀유니버스 다세대는 거래수 캡·메모리 관찰; 1개월 탐색→OOS 분리 권장.)
2. 백파인더 `backfinder_principle.to_band_seeds` 출력 → 밴드 생성경로(P1: `band_generation_enabled`) 배선 = 데이터구동 밴드 생성.
3. T3 시간창 span 분포를 대시보드 패널로 가시화(생성이 09:00~09:30 분산하는지).
4. (감사 잔여) Sharpe/CVaR/PBO/CSCV/Deflated Sharpe를 graded 가산항으로(하드게이트 불변) = "인간초월"의 통계적 척도. 문서 `docs/update_log/2026-06-02_analysis_capability_audit.md`.

---

## 7. ✅ 어떻게 검증하나
- **단위/회귀**: `PYTHONUTF8=1 python -m pytest tests/unit/ -p no:randomly --tb=no -q` → 7 known/신규0.
- **동기화**: `python scripts/verify_nonrelease_sync.py`.
- **실DB 스모크(중요)**: 단위테스트가 못 잡는 의미버그를 실DB 스모크가 잡는다(T3 교집합반전·T2 채굴 검증이 실증). 새 분석/생성은 1개월·소형(`tick_subset.db`/`min_subset.db`) 스모크로 검증(3년 풀유니버스 회피).
- **AI auth**: provider=`gpt_auth`(=ChatGPT OAuth, `ai_strategy_loop/provider/chatgpt_oauth/` token_manager 자동갱신). 생성 성공·인증오류0이면 정상.

---

## 8. 📚 상세 문서 색인 (`docs/update_log/`)
- `2026-06-03_tick_program_complete_handoff.md` — TICK T0~T4 상세 핸드오프(최신)
- `2026-06-02_comprehensive_review_and_redirection.md` — 전 도메인 종합검토 + 방향성 재설정(8도메인 정독)
- `2026-06-02_overnight_generation_research_campaign.md` — 생성연구 19에피소드 + 앙상블/적응형
- `2026-06-02_analysis_capability_audit.md` — 분석역량 감사(퀀트 갭 top-8)
- `2026-06-02_band_generator_design.md` — 밴드 파라미터화 생성기 설계(P0~P5)
- `2026-05-30_seed_tick902_supervised_deployment_plan.md` — 시드 감독형 실배포 계획
- 프로젝트 가이드(에이전트 무관): 루트 `AGENTS.md`(구조/개요)·`CLAUDE.md`(레인 규칙)

> **정리 권장(미적용)**: 세션 중 에이전트 deepinit이 만든 `AGENTS.md`(서브디렉토리)·`.claude/` 잡파일이 untracked로 남음 — 필요시 정리/`.gitignore`.
