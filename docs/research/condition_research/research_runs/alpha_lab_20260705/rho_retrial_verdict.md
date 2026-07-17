# P1 ρ게이트 재판정(봉인 마지막 1회) — 최종 판정
날짜: 2026-07-06T09:44:26.163282+09:00 · 스테이지: P1_rho_retrial_engine_confirmation_ALP_RM2_top10

## 결론

**ρ = 0.668696 → 본빌드 진행 권고** (이분법: ρ>=0.5 본빌드 진행 / ρ<0.5 포기 — 추가 재시도 없음)

- 판정 기준: 봉인 재판정 조항 그대로 — "번역 계층 결함 진단·수정에 한해 1회, 동일 10규칙 재백테 <=10회. 규칙 재선별·임계값 하향·표본창 교체 금지. 재판정도 rho<0.5면 포기와 동일 처리."
- ρ 산정: scipy.stats.spearmanr(mined_lift[n=10], engine_pf_with_sentinel[n=10]) — 1차와 동일한 채굴 lift 값(rho_retrial_registration_receipt.json meta.lift), PF는 거래 CSV '수익금' 기반 cli.research_metrics.calculate_profit_factor(1차와 동일 정의).
- 검열 처리(사전선언, 실행 전 2026-07-06T08:08:50.659492+09:00 선언·스냅샷 sha256 10039b5d05f779b9bb93954f47a1cbf8ddb03ec49f272b990e30f6b5278e515c): 타임아웃/무거래 = PF=-inf 센티널 최하위 동률(average ties)
- 이번 실측 검열: 2건(timeout) + 0건(no_trades) — ['ALP_RM2_08', 'ALP_RM2_09']

## 규칙별 실측 (n=10, 엔진 시도 총 10회 — 규칙당 정확히 1회)

| 규칙 | 1차 규칙 | 채굴 lift | lift 순위 | 엔진 상태 | 엔진 PF | PF 순위(n10) | 총수익 | 거래수 | MDD | 1차 거래수 | Δ거래수 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ALP_RM2_01 | ALP_RM_01 | 3.8740 | 1 | ok | 0.5702 | 5.0 | -35,682,794 | 929 | 352.36 | 981 | -5.30% |
| ALP_RM2_02 | ALP_RM_02 | 3.5734 | 2 | ok | 0.5870 | 4.0 | -201,272,927 | 6,771 | 394.42 | 6,845 | -1.08% |
| ALP_RM2_03 | ALP_RM_03 | 3.1212 | 3 | ok | 0.7247 | 2.0 | -11,826,414 | 598 | 118.83 | 598 | +0.00% |
| ALP_RM2_04 | ALP_RM_04 | 2.9866 | 4 | ok | 0.7281 | 1.0 | -12,645,529 | 669 | 126.10 | 672 | -0.45% |
| ALP_RM2_05 | ALP_RM_05 | 2.6532 | 5 | ok | 0.6062 | 3.0 | -125,022,574 | 4,139 | 502.70 | 4,166 | -0.65% |
| ALP_RM2_06 | ALP_RM_06 | 2.5809 | 6 | ok | 0.5330 | 7.0 | -107,642,719 | 3,997 | 689.64 | 4,651 | -14.06% |
| ALP_RM2_07 | ALP_RM_07 | 2.5786 | 7 | ok | 0.5255 | 8.0 | -1,351,416,284 | 46,963 | 1077.77 | 49,273 | -4.69% |
| ALP_RM2_08 | ALP_RM_08 | 2.3759 | 8 | censored_timeout | -inf(검열) | 9.5 | — | — | — | — | — |
| ALP_RM2_09 | ALP_RM_09 | 2.2834 | 9 | censored_timeout | -inf(검열) | 9.5 | — | — | — | — | — |
| ALP_RM2_10 | ALP_RM_10 | 2.1082 | 10 | ok | 0.5466 | 6.0 | -637,359,398 | 19,569 | 579.00 | 19,730 | -0.82% |

- PF 정의: 거래 CSV '수익금' 기반 cli.research_metrics.calculate_profit_factor(1차와 동일 정의).
- 부가 지표(총수익·거래수·MDD·Δ거래수)는 기록 전용 — 판정에 미사용(봉인은 ρ만)
- Δ거래수 중앙값(측정 가능 규칙): -0.95%
- 1차 검열 규칙의 재판 결과: ALP_RM2_08 → censored_timeout, ALP_RM2_09 → censored_timeout

## 엔진 규율 준수 증거

- 동결 프로파일: `docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_tick_official_full_warm64_20260704.json` (sha256 `00ebb88b34383d3b0270360c236f15b31195b5bd4433bae954387c5e37f84e21`) — 어떤 필드도 무수정(timeout 300s 포함)
- 전략 DB: `STOM_CLI_DB_STRATEGY=C:/System_Trading/STOM/STOM_V.wt-alpha/_database/strategy.db` (launcher가 명시 설정 — run_chunk.sh:7)
- 직렬 실행, run_id: alp_rho_retrial_warm64_chunk01_20260706, alp_rho_retrial_warm64_chunk02_20260706, alp_rho_retrial_warm64_chunk03_20260706, alp_rho_retrial_warm64_chunk04_20260706
- 청크별 실행 전 프로세스 재스캔 수행(대형 엔진 배치 부재 확인) — 사전선언 preflight.will_rescan_before_each_chunk 이행. chunk04는 wt-dev 레인 min 배치(lat_repair_composite_expanded_48, 09:11:23~09:29:31 실측)의 종료를 대기한 뒤 09:29:51 청정 상태에서 기동
- 검열 wall 실측: ALP_RM2_08 357s(1차 356s/344s와 동급), ALP_RM2_09 353s(1차 361s/359s와 동급, 청정 환경). RM2_08 실행창 마지막 ~55초와 wt-dev 배치 기동이 겹친 사실은 `rho_retrial_engine_runs.json` chunk03.environment_note에 기록 — 1차 청정 재현 2회와 이번 wall 동급성에 근거해 사전선언 규칙(엔진 타임아웃 판정, 재시도 없음)대로 검열 확정
- 원시 증거: `rho_retrial_engine_runs.json`(행·배치 로그 전문), loop_runs.db(generations), trade CSV 8건

## 인프라 사건 기록 (판정 무영향 — 엔진 시도 0회 소모)

chunk01 1차 기동(08:13, 이전 세션)이 Windows multiprocessing spawn 데드락으로 영구 정지 — py-spy 실측:
`Process.start() → popen_spawn_win32.__init__:97 reduction.dump` 파이프 쓰기 블록(BackTest spawn 자식 조기 사망, 부모가 read handle 보유로 broken-pipe 미발생).
gen 행 0건·CSV 0건·엔진 타임아웃 판정 미발생을 실측 확인 후 트리 종료, 동일 run_id로 재기동(INSERT OR REPLACE — controller/state.py:275).
상세: `rho_retrial_chunk01_launch_incident.json`(사건 기록 2026-07-06T08:35:07.375711+09:00) — 사전선언 검열 규칙(엔진 타임아웃 판정)과 무관한 launcher-infra 결함이므로 어떤 규칙에도 검열을 부여하지 않음(추정 금지).

## n_trials 원장

- P1 batch=rho_retrial n=10 append (원장 총계 745)

## 변경 파일 전수 선언 (tracked) — 검증 지적 수복 (2026-07-06T10:07:38+09:00, 선언 정정만)

검증 지적: 이 사이클의 tracked 수정 전수(5건)가 기존 선언 문언("codegen.py+test, n_trials_ledger")보다 2건 넓었다. 본 절은 전수를 판정 문서에 명시 선언해 문언 불일치를 해소한다. 본 수복은 문서 선언 정정뿐이다 — ρ·per_rule·검열 규칙 등 판정 본문 무변경, tracked 코드/원장 내용에도 추가 수정 없음(수복 시점 git diff --numstat 실측 2026-07-06T10:06:09+09:00, 아래 기계 대조 포함).

| 파일 | numstat | 성격 | 근거 |
|---|---|---|---|
| `alpha_lab/translate/codegen.py` | +29/−2 | 번역 계층 결함 수정 본체(허용 수정) — `SAMPLE_TIME_GUARD`(:67)·`UNIVERSE_GUARD_MONEYTOP_PROXY`(:74) 신규 상수, `universe_guard` 옵션(기본 None=기존 산출 byte-identical) | `rho_retrial_diagnosis.md` §4 |
| `tests/unit/test_alpha_translate.py` | +97/−0 | 수정 검증 테스트 7케이스 추가(허용) — 수복 시점 재실행 78 passed(1.27s, 2026-07-06 10:05 KST) | 동 §4 |
| `alpha_lab/translate/__init__.py` | +4/−0 | codegen 변경의 재수출 부속 — 신규 상수 2종의 import 2행 + `__all__` 2행 추가뿐(순수 additive, 로직 무변경). 기존 선언 문언에서 누락 → 본 절에서 선언 | git diff 전문 실측 |
| `n_trials_ledger.jsonl` | +1/−0 | 원장 append(허용) — batch=rho_retrial n=10. 원장 전 행 재합산 총계 745 == 본 판정 n_trials_ledger_total_after | 원장 재합산 기계 검증 |
| `rho_gate_registration_provenance.jsonl` | +10/−0 | 등재기 계약상의 provenance append-only — ALP_RM2_01..10 10행(stage=rho_retrial_registration). 기존 1차 10행은 HEAD 대비 byte-identical(기계 대조), 추가 10행의 buy/leaf/first_buy/sell sha256·retrial_of·rule_id는 재등재 영수증(verification[]·registration.inserted[])과 전건 일치(불일치 0). 기존 선언 문언에서 누락 → 본 절에서 선언 | 기계 교차 대조(불일치 0) |

- 영수증 무결성: `rho_retrial_registration_receipt.json` 수복 시점 sha256 == 본 판정 registration_receipt.sha256(`5e2d1c20e0b5…`) — 영수증·사전선언 스냅샷은 수복 과정에서 바이트 무변경.
- 상세 기계 대조 결과는 `rho_retrial_verdict.json` tracked_change_manifest에 동일 내용으로 기록.

## 후속

본빌드 단계로 진행을 권고한다. 다음 단계 범위·설계는 본 판정 문서의 소관 밖이다.
