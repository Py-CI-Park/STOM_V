# P1 ρ게이트 판정 — warm64 훈련창 재현 (alpha_lab_20260705)

작성: 2026-07-06 05:18 KST · 브랜치 `research/alpha-lab-20260704` · 데이터: `rho_gate_verdict.json`

## 결론

**판정 = `blocked_indeterminate_engine_censoring`** — 봉인 ρ(n=10)를 정직하게 산출할 수 없다.

- 10규칙 중 **8규칙 실측 완료**, 2규칙(ALP_RM_08·09)은 동결 프로파일의 per-run 예산 `bt_warm_run_timeout=300s`를 **재현 가능하게 초과**(각 2회 시도, gen0-fresh 단독 세션 포함)해 CSV/metrics가 생성되지 않았다(검열, censored — 거래 0건이 아님).
- 실측 8규칙 진단 ρ = **0.5000** (참고값 — 봉인 통계 아님).
- 검열 2규칙의 가능한 모든 순위 배치에 대한 **attainable ρ(n=10) 구간 = [-0.0729, +0.6565]** — 봉인 3분지(go/hold/abandon)를 전부 가로지르므로, 어떤 배치 가정 없이는 분지가 결정되지 않는다. 사전등록·과제 규율(추정 금지, 불확실하면 blocked)에 따라 imputation을 거부하고 blocked로 보고한다.

## 봉인 검증 (실행 전·판정 시 각 1회, `alpha_lab.registry.verify_seal`)

| seal | sha256 | 결과 |
|---|---|---|
| v1 `preregistration_v1.json` | `6750a567…c39e5b` | 통과 (rho_gate `{go:0.5, hold:0.2, n_rules:10}` assert) |
| p3 `p3_preregistration_v1.json` | `6a75e831…9ad54` | 통과 |
| p5 `p5_preregistration_v1.json` | `84eeb95a…3aeb` | 통과 (engine_confirmation 원문 "~25회, min 스윕 종료 후 PENDING") |

판정 임계는 봉인값만 사용: `preregistration_v1.json → mining_spec.rho_gate == {go: 0.5, hold: 0.2, n_rules: 10}`.

## 3분지 규정 (봉인)

- ρ ≥ 0.5 → **go** (본빌드 진행 권고)
- 0.2 ≤ ρ < 0.5 → **hold** (보류 — **번역 계층 결함 진단에 한해 1회 재판정 가능, 재선별·임계 하향 금지**)
- ρ < 0.2 → **abandon** (포기 — CSS_V7 재판)

## 방법 (전부 저장소 실측 근거)

- **엔진 경로**: `ai_strategy_loop/scripts/claude_candidate_batch_eval.py` + 동결 공식 프로파일 `docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_tick_official_full_warm64_20260704.json` (tick, bt_full 20220323~20260227, betting "5", avg_time 30, warm64, 유니버스 90000~92800, bt_warm_run_timeout 300). `--fail-fast-timeout` 필수, 청크당 warm64 prepare/close — p5 프로토콜(`p5_tick_full_run_protocol_after_preflight_20260704.md`), 본 워크플로 규율로 2~3쌍 청크.
- **전략 해석 배선**: `STOM_CLI_DB_STRATEGY=C:/System_Trading/STOM/STOM_V.wt-alpha/_database/strategy.db` 선지정(bootstrap setdefault 존중 — `ai_strategy_loop/bootstrap.py:39`, `cli/paths.py:27` env-override 실측). 매 쌍 buy=sell=`ALP_RM_XX`(stockbuy/stocksell 동명 등재 — 등재 영수증 post_verify byte-exact).
- **PF 정의(1차 지표)**: `cli/research_metrics.py:34 calculate_profit_factor(df, '수익금')` = 거래 CSV의 수익금 양합 / |음합| (무손실+이익시 inf, 무이익시 0.0). 상위 근거: 연구 프로그램 문서 "채굴 lift 순위 vs 엔진 PF 순위 Spearman ρ"(`2026-07-04_new_alpha_research_program.md` 검증 설계 절). CSV는 utf-8-sig로 로드(대시보드 선례 `ai_strategy_loop/dashboard/backtest_analysis.py:98`). CSV 행수·수익금 합이 loop_runs.db의 trade_count·profit과 전 규칙 정확 일치함을 교차 확인.
- **거래 0건 처리(선언)**: no_trades는 PF=-inf 센티널로 최하위 동률(실측 PF는 항상 ≥0.0), 동률 순위는 `scipy.stats.spearmanr` 기본 average ties. **이번 실측에서는 해당 규칙 0개.**
- **ρ**: `scipy.stats.spearmanr`(scipy 1.17.1), 채굴 lift(내림) vs 엔진 PF(내림), n_rules=10 봉인.
- **검열 처리(핵심)**: 타임아웃 검열은 거래 0건이 아니므로 **어떤 순위도 부여하지 않는다**(추정 금지). 대신 검열 2규칙의 의사 PF를 실측 8값의 모든 구간 중점·양끝 밖·정확 동률 후보 17개로 전수 대입(17×17)해 **모든 순위 위상에서의 attainable ρ 구간**을 계산했다.

## 규칙별 결과 (lift 내림차순)

| # | 규칙 | rule_id | mined lift | 엔진 PF | 거래수 | 수익금(원) | MDD% | 상태 |
|---|---|---|---|---|---|---|---|---|
| 1 | ALP_RM_01 | P1-s02-l019 | 3.8740 | 0.5569 | 981 | -38,095,762 | 376.9 | ok |
| 2 | ALP_RM_02 | P1-s04-l011 | 3.5734 | 0.5857 | 6,845 | -202,998,002 | 397.6 | ok |
| 3 | ALP_RM_03 | P1-s03-l026 | 3.1212 | 0.7247 | 598 | -11,826,414 | 118.8 | ok |
| 4 | ALP_RM_04 | P1-s00-l026 | 2.9866 | 0.7297 | 672 | -12,572,414 | 125.4 | ok |
| 5 | ALP_RM_05 | P1-s02-l020 | 2.6532 | 0.6063 | 4,166 | -125,361,096 | 504.0 | ok |
| 6 | ALP_RM_06 | P1-s03-l007 | 2.5809 | 0.5063 | 4,651 | -125,984,689 | 807.0 | ok |
| 7 | ALP_RM_07 | P1-s01-l029 | 2.5786 | 0.5189 | 49,273 | -1,403,257,691 | 1119.0 | ok |
| 8 | ALP_RM_08 | P1-s04-l027 | 2.3759 | **측정불가** | — | — | — | censored_timeout (356s/344s) |
| 9 | ALP_RM_09 | P1-s00-l012 | 2.2834 | **측정불가** | — | — | — | censored_timeout (361s/359s) |
| 10 | ALP_RM_10 | P1-s03-l011 | 2.1082 | 0.5456 | 19,730 | -641,121,223 | 581.9 | ok |

전 실측 규칙 PF < 1 (전부 순손실). fitness 게이트(gate_passed)는 전 규칙 False(mdd_cap 35 초과)지만, ρ게이트는 게이트 통과 여부가 아니라 **순위 상관**을 본다.

## ρ 수치

- 실측 8규칙 진단 ρ = **0.500000** (n=8 — 봉인 n=10이 아님, 판정에 직접 사용 불가)
- attainable ρ(n=10) 구간 = **[-0.072949, +0.656538]** → 도달 가능 분지 {abandon, hold, go} 전부
- 참고 시나리오(봉인 규정 밖 가정): 검열 2규칙을 최하위 동률로 두면 ρ = 0.6565 (=구간 상한; go 상당) — **imputation이므로 판정에 사용하지 않음**

## 검열 증거와 완결 시도 (p5 blocker 전례 준수: retry/supplement with new run_id only, 동일 동결 프로파일)

| 청크 | run_id | 내용 | 결과 |
|---|---|---|---|
| 1 | alp_rho_gate_warm64_chunk01_20260706 | RM_01~03 | 3 ok (prepare ok back_count=2424, 299s) |
| 2 | alp_rho_gate_warm64_chunk02_20260706 | RM_04~06 | 3 ok (prepare 290s) |
| 3 | alp_rho_gate_warm64_chunk03_20260706 | RM_07~08 | 07 ok(308s) / 08 timeout 356s → fail-fast abort |
| 4 | alp_rho_gate_warm64_chunk04_20260706 | RM_09~10 | 09 gen0-fresh timeout 361s → abort, 10 미시도 |
| 5 | alp_rho_gate_warm64_chunk05_supplement08_20260706 | RM_08 단독 gen0-fresh | timeout 344s (재현) |
| 6 | alp_rho_gate_warm64_chunk06_supplement09_20260706 | RM_09 단독 gen0-fresh | timeout 359s (재현) |
| 7 | alp_rho_gate_warm64_chunk07_supplement10_20260706 | RM_10 단독 | ok (148s) |

- 총 엔진 실행 시도 12회 = ok 8 + timeout 4. 전 청크 warm prepare status=ok, 청크 간 프로세스 표면 기저 복귀(python.exe 4~6) 확인. 실행 중 최대 ~92 프로세스는 당사 warm64 세션 자체.
- 검열은 위치/부하 무관 재현: RM_08은 2번째 슬롯(356s)과 단독 gen0(344s), RM_09는 gen0 2회(361s/359s). 고빈도 규칙일수록 런타임 증가(RM_07 49k거래 ~308s는 통과, RM_10 19.7k거래 148s) — 검열 2규칙은 채굴 support 21,878/56,376의 초고빈도 규칙으로 300s 예산을 구조적으로 초과.
- n_trials 원장: `P1-rho-gate-engine-confirmation-20260706` n=12 append (전 프로그램 총합 713 → **725**).

## 판정 불가 논증

1. 봉인 통계는 ρ(n_rules=10). 검열 2규칙의 PF 순위는 관측되지 않았다.
2. 전수 배치 분석 결과 attainable ρ가 3분지를 모두 가로지른다 — 즉 **검열 규칙의 배치 가정이 분지를 결정**한다.
3. 과제 규율 "추정 금지, 불확실하면 blocked" + 봉인 문서에 검열 처리 규정 부재 → imputation(최하위 동률 포함)은 무근거. 거래 0건 규정은 no_trades에만 적용되며 검열은 no_trades가 아니다(엔진이 계산 중 시간 초과로 절단됨).

## 해소 경로 (오케스트레이터 결정 필요 — 본 서브에이전트 권한 밖)

- **(a) 계측 예산 상향**: `bt_warm_run_timeout`을 검열 2규칙에 한해 상향(예: 900s)한 supplement 2회. 동결 프로파일 필드의 명시적 개정이므로 상위 결정 필요. 비용 ~2×12분. 시장 의미론(기간·betting·avg_time·유니버스)은 불변이라 순위 비교의 왜곡 없음이 논증 가능.
- **(b) 봉인 해석 재정(ruling)**: "계측 불능 규칙은 최하위 동률" 등의 규정을 상위가 재정하면 ρ=0.6565(go 상당)로 계산됨 — 단 이는 사후 규정 추가이므로 재정 기록 필수.
- **(c) 검열 그대로 보류(hold 상당) 처리**: 실측 8 진단 ρ=0.500과 구간 하한 -0.073을 함께 두고, 번역 계층이 아닌 **계측 계층** 결함으로 분류해 재판정 1회 규정과 별도 트랙으로 처리.

어느 경로든 **재선별·임계 하향은 금지**(봉인) — 10규칙 구성과 임계는 그대로다.

## 원자료 경로 (git add 금지 자산 — 경로만)

- `ai_strategy_loop/state/loop_runs.db` (runs/generations — run_id 7건)
- 거래 CSV 8건: `backtest/csv/stock_bt_ALP_RM_01_20260706035925.csv`, `..._02_20260706040044.csv`, `..._03_20260706040204.csv`, `..._04_20260706040928.csv`, `..._05_20260706041042.csv`, `..._06_20260706041207.csv`, `..._07_20260706042317.csv`, `..._10_20260706050253.csv`
- `_database/backtest.db` (stock_bt — 엔진 자체 기록)
- 커밋 대상 산출물: `rho_gate_verdict.json`, `rho_gate_engine_runs.json`, `rho_gate_engine_preflight_receipt.json`, `pairs_alp_rho_gate_warm64_chunk0{1..7}*.json`, `n_trials_ledger.jsonl`(1줄 append) — 커밋은 오케스트레이터 몫.
