# V3K 중간점검: V3 기능 대비 2U_C 반영률 및 커스텀 기능 전수 검사

- 작성일: 2026-05-14 KST
- 대상 worktree: `STOM_V.wt-dev/` (`STOM_Version_2U_C`)
- 기준 커밋: `b86de6bc` + 본 점검 중 발견한 감사/스모크 최신화 수정
- 목적: V3 기능 전체 대비 2U_C 반영률, 남은 기능 수, 즉시 사용 가능 범위, 남은 반영 방법, 2U_C 커스텀 기능의 현재 검증 상태를 한 번에 확인한다.

## 1. 요약 결론

| 항목 | 현재 판정 | 수치 | 해석 |
|---|---:|---:|---|
| V3 전략 파일 직접 반영 | 부분 반영 | 6/9 = 66.7% | V3의 6개 analyzer 파일은 2U_C에 staging 형태로 존재한다. `analyzer_microstructure.py`, `manager_formula.py`, `stg_globals_func.py`는 직접 파일 반영이 아니라 V3K 전용 대체/파사드로 분리했다. |
| V3K 구조/대체 반영 | 대부분 반영 | 13/17 = 76.5% | LS증권 직접 의존성을 제외한 V3K 주요 단위 17개 중 13개가 안전 staging/검증 가능 상태다. |
| 실제 승인 게이트 진행률 | 중간 진행 | 3/6 = 50.0% | Gate1 GUI sidecar, Gate2 Phase F, Gate3 Phase G만 승인 실행 완료. Gate4는 KHOPENAPI 환경 증거가 없어 차단. |
| 즉시 사용 가능 범위 | 개발/검증용 가능, 실거래 불가 | 안전 기능 13개 / 실거래 기능 0개 | 지금 바로 쓸 수 있는 것은 read-only, dry-run, preview, synthetic proof, default-OFF adapter다. 실계좌/실주문/운영 DB 전환은 아직 금지. |
| 2U_C 커스텀 기능 검증 | 자동 검증 범위 통과 | V3K smoke 24/24, gate/audit 19/19 | 점검 중 기존 감사 2개와 GUI preview smoke 1개가 Gate3 이후 상태를 반영하지 못해 수정했고, 수정 후 전체 통과했다. |
| pytest 전체 테스트 | 미실행 | 0개 | 현재 환경에 `pytest` 모듈이 없어 실행 불가. 의존성 설치는 명시 승인 전에는 하지 않았다. |

**중간점검 결론:** 2U_C는 V3 기능을 “실거래 ON”으로 가져온 상태가 아니라, `Kiwoom 유지 + LS 의존성 제외 + default-OFF/approval-gated` 방식으로 상당 부분 이식한 상태다. 지금부터 사용할 수 있는 것은 안전한 검증/미리보기/드라이런 기능이며, 실제 운영 DB 전환·KHOPENAPI 접속·live order/exit 소비는 아직 사용할 수 없다.

## 2. V3 원본 기능 목록 대비 2U_C 반영 현황

V3 공식 전략 파일 기준(`STOM_V.wt-3/strategy`)으로 확인한 기능 파일은 다음 9개다.

| V3 원본 기능 파일 | 2U_C 상태 | 반영 방식 | 즉시 사용 가능성 |
|---|---|---|---|
| `analyzer_candle_pattern.py` | 반영 | 2U_C staging 파일 존재, import/field contract smoke 통과 | 개발/검증 가능, runtime ON 아님 |
| `analyzer_volume_spike.py` | 반영 | 2U_C staging 파일 존재, import/field contract smoke 통과 | 개발/검증 가능, runtime ON 아님 |
| `analyzer_volume_profile.py` | 반영 | 2U_C staging 파일 존재, import/field contract smoke 통과 | 개발/검증 가능, runtime ON 아님 |
| `analyzer_volatility_pattern.py` | 반영 | 2U_C staging 파일 존재, import/field contract smoke 통과 | 개발/검증 가능, runtime ON 아님 |
| `analyzer_volatility_stop_take.py` | 반영 | 2U_C staging 파일 존재, import/field contract smoke 통과 | 개발/검증 가능, runtime ON 아님 |
| `analyzer_risk.py` | 반영 | 2U_C staging 파일 존재, AnalyzerRisk adapter smoke 통과 | 개발/검증 가능, runtime ON 아님 |
| `analyzer_microstructure.py` | 대체 반영 | 직접 파일 대신 `strategy/v3k_microstructure_engine.py`로 Kiwoom-neutral/default-OFF 구현 | synthetic parity/benchmark 가능, live ON 아님 |
| `manager_formula.py` | 대체 반영 | 직접 파일 대신 `strategy/v3k_formula_facade.py`로 `V3K_` prefix facade 구현 | dry-run 가능, live globals hook 아님 |
| `stg_globals_func.py` | 대체 반영 | 직접 `globals().update` 대신 formula facade와 boundary contract로 분리 | dry-run 가능, live strategy 주입 아님 |

### 반영률 산정 기준

| 기준 | 분자/분모 | 반영률 | 비고 |
|---|---:|---:|---|
| 직접 파일 존재 기준 | 6/9 | 66.7% | V3 원본 파일명이 그대로 2U_C에 있는 경우만 계산. |
| 기능 대체/파사드 포함 기준 | 9/9 | 100.0% | 모든 V3 전략 기능에 대응 후보는 있으나, 일부는 안전 파사드/default-OFF라서 runtime 사용률과 다르다. |
| V3K 주요 단위 기준 | 13/17 | 76.5% | 아래 17개 주요 기능 단위 중 안전 staging/검증 완료 수. |
| 실운영/live 사용 기준 | 0/4 critical live units | 0.0% | KHOPENAPI, DB cutover, live order/exit, production monitoring은 아직 차단. |

## 3. V3K 주요 단위 17개 현황

| # | 기능 단위 | 상태 | 증거/파일 | 즉시 사용 가능 여부 |
|---:|---|---|---|---|
| 1 | V3/V3U 기준 레인 확보 | 완료 | `STOM_V.wt-3`, `STOM_V.wt-3u` | 분석 기준으로 사용 가능 |
| 2 | 6개 analyzer module staging | 완료 | `strategy/analyzer_*.py`, `smoke_v3k_analyzer_modules.py` | 개발/검증 가능 |
| 3 | AnalyzerRisk adapter | 완료 | `strategy/v3k_analyzer_adapter.py`, `smoke_v3k_analyzer_adapter.py` | OFF/no-signal 검증 가능 |
| 4 | 학습 DB 계약/스키마/manifest | 완료 | design/update logs, `diff_v3_vs_2uc_db_schema.py` 계열 | read-only 설계 확인 가능 |
| 5 | shadow DB/init/apply/read-only tooling | 완료 | `init_v3k_shadow_db.py`, `apply_v3k_shadow_db.py`, DB health | dry-run/read-only 가능 |
| 6 | backtest learning loader/hook | 완료 | `backtest/backengine_base.py`, `smoke_v3k_backtest_learning_hook.py` | flag 기반 no-op/dry-run 가능 |
| 7 | realtime learning preload boundary | 완료 | `smoke_v3k_realtime_learning_boundary.py` | boundary 검증 가능, live ON 아님 |
| 8 | formula/global facade | 완료 | `strategy/v3k_formula_facade.py` | dry-run 가능, live globals hook 아님 |
| 9 | settings surface/GUI bridge/preview | 완료 | `ui/ui_v3k_settings_bridge.py`, `ui/ui_v3k_settings_preview.py` | session-only preview 가능 |
| 10 | GUI sidecar schema/read-only/writer guard | 완료 | `strategy/v3k_gui_sidecar.py`, sidecar smokes | ignored sidecar 검증 가능 |
| 11 | Phase F analyzer strategy candidate | 승인 실행 완료 | sidecar `V3K_PHASE_F_ANALYZER_STRATEGY=true`, Gate2 audit | 승인된 candidate build 가능, live wiring 아님 |
| 12 | Phase G microstructure engine candidate | 승인 실행 완료 | sidecar `V3K_PHASE_G_MICROSTRUCTURE_ENGINE=true`, Gate3 audit | synthetic engine 가능, live wiring 아님 |
| 13 | Phase H Kiwoom dry-run hook H1 | 계약 완료 | `strategy/v3k_kiwoom_dryrun_hook.py`, env audit | unit/sentinel 검증 가능, KHOPENAPI 없음 |
| 14 | Phase H H2/H3 live dry-run | 차단 | `audit_v3k_phase_h_env_check.py` 결과 `khopenapi_compatible=false` | 즉시 사용 불가 |
| 15 | F1 actual DB cutover | 차단 | Gate5 review-only, `smoke_v3k_cutover_dryrun.py` | 운영 DB 적용 불가, tempfile dry-run만 가능 |
| 16 | live order/exit rule consumption | 차단 | Gate6 review-only | 즉시 사용 불가 |
| 17 | production runtime/monitoring integration | 잔여 | MainWindow/pyd full runtime, live monitoring | 즉시 사용 불가 |

## 4. 현재 바로 사용 가능한 기능

아래는 “운영/실거래 사용”이 아니라 **개발·검증·드라이런 목적의 즉시 사용 가능 기능**이다.

| # | 바로 가능한 기능 | 실행/확인 방법 | 제한 |
|---:|---|---|---|
| 1 | V3 analyzer import/field contract 확인 | `python scripts/smoke_v3k_analyzer_modules.py` | runtime 전략 엔진에 자동 연결되지 않음 |
| 2 | analyzer adapter OFF/no-signal 확인 | `python scripts/smoke_v3k_analyzer_adapter.py` | ON path는 의도적으로 차단/제어됨 |
| 3 | 학습 DB read-only/fallback/leakage guard | `smoke_v3k_learning_db_*.py` | 운영 DB 쓰기 없음 |
| 4 | backtest learning hook no-op/dry-run | `python scripts/smoke_v3k_backtest_learning_hook.py` | flag/DB 조건 없으면 no-op |
| 5 | realtime learning preload boundary | `python scripts/smoke_v3k_realtime_learning_boundary.py` | 실시간 매매 연결 아님 |
| 6 | formula/global facade dry-run | `python scripts/smoke_v3k_formula_facade.py` | `globals().update` live hook 아님 |
| 7 | GUI settings preview | GUI `Alt+V`/preview helper smoke | session-only, DB 저장 아님 |
| 8 | sidecar schema/read-only/tempfile writer | `smoke_v3k_gui_sidecar_*.py` | sidecar는 ignored runtime artifact |
| 9 | Phase F candidate build/rollback proof | `smoke_v3k_phase_f_default_off.py`, Gate2 audit | live order/exit wiring 아님 |
| 10 | Phase G microstructure synthetic proof | `smoke_v3k_phase_g_engine_unit.py`, parity/benchmark | live market/order data 미연결 |
| 11 | Phase H hook unit/sentinel | `smoke_v3k_phase_h_hook_unit.py` | KHOPENAPI 미탐지로 live dry-run 불가 |
| 12 | F1 cutover tempfile dry-run/rollback | `python scripts/smoke_v3k_cutover_dryrun.py` | 운영 `_database` 적용 금지 |
| 13 | V3K DB health read-only report | `python scripts/v3k_db_health.py --read-only ...` | report는 `.omx/reports` ignored artifact |

## 5. 승인 게이트 현황

| Gate | 승인 문구/대상 | 현재 상태 | 개발완성률 관점 | 다음 조치 |
|---|---|---|---:|---|
| Gate1 | GUI sidecar actual write | 완료 | 1/6 | 현 상태 유지. Gate2/3 이후 sidecar subset audit으로 갱신됨. |
| Gate2 | `phase-f-f4-on-await-user-approval` | 완료 | 2/6 | Phase F는 sidecar ON이나 rollback/env guard 유지. |
| Gate3 | `phase-g-g3-on-await-user-approval` | 완료 | 3/6 | Phase G는 sidecar ON이나 synthetic proof 범위. |
| Gate4 | `phase-h-h2-h3-live-dryrun-await-user-approval` | 차단 | 3/6 유지 | `khopenapi.dll` sentinel/환경 증거 없이는 보류. |
| Gate5 | `f1-actual-db-cutover-await-user-approval` | 보류/차단 | 3/6 유지 | Gate4가 막히면 사전점검만 가능. 운영 DB 적용은 별도 승인 필요. |
| Gate6 | `live-order-exit-rule-consumption-await-user-approval` | 보류/차단 | 3/6 유지 | 가장 위험한 최종 live wiring. DB/live dry-run 이후만 검토. |

## 6. 남은 반영 방법

| 남은 기능 | 권장 순서 | 반영 방법 | 필수 검증/중단 조건 |
|---|---:|---|---|
| Phase H H2/H3 Kiwoom live dry-run | 1 | `V3K_KHOPENAPI_DLL` 또는 기본 경로에서 `khopenapi.dll` sentinel 확인 후, login/connect 없는 dry-run부터 실행 | `audit_v3k_phase_h_env_check.py --stdout`에서 `khopenapi_compatible=true`; 실주문/잔고 mutation 없음 |
| F1 actual DB cutover | 2 | 운영 DB backup → checksum → shadow→operational cutover → rollback rehearsal 순서 | `--backup-first`, USER_ACK, corruption rejection, rollback success. 실패 시 즉시 rollback |
| live order/exit rule consumption | 3 | analyzer output을 live decision path에 직접 연결하지 말고 dry-run decision log → shadow compare → limited rule consumption 순서 | 실주문 전 반드시 no-order dry-run log 비교; Kiwoom order/exit mutation 차단 |
| production runtime/monitoring | 4 | health report, runtime diagnostics, rollback toggle, alert/로그 정책을 먼저 고정 | `_database`, `_log`, `.db`, `.omx/reports` 커밋 금지; 성능/latency 기준 초과 시 중단 |
| MainWindow/pyd full integration | Gate별 | preview/session-only에서 persistence bridge로 확장하되 pyd-free wrapper boundary 유지 | `verify_pyd_gui_contract.py`, `smoke_offline_gui.py`, `verify_nonrelease_sync.py` 통과 전 ON 금지 |

## 7. 2U_C 커스텀 기능 전수 검사 결과

이번 점검에서 2U_C 전체 커스텀 차이는 `STOM_Version_2U...HEAD` 기준 약 1035개 파일이다. 이 전체 차이는 V3K뿐 아니라 기존 CLI/연구/문서/테스트/런타임 커스텀을 포함한다. 따라서 “모든 줄 수동 검토”가 아니라, 현재 안전하게 자동 검증 가능한 커스텀 표면을 전수 검사했다.

| 검사 묶음 | 결과 | 비고 |
|---|---:|---|
| 모든 `smoke_v3k*.py` | PASS 24/24 | 최초 1개 실패 후, Gate3 이후 valid sidecar 상태를 반영하도록 smoke 수정 후 재통과 |
| 현재 게이트/런타임 감사 | PASS 19/19 | Gate1/Gate2 감사가 Gate3 이후 sidecar 상태를 오판하던 문제 수정 후 재통과 |
| V3K script py_compile | PASS 72/72 | `scripts/*v3k*.py` 전체 compile 통과 |
| V3K core strategy/UI py_compile | PASS | adapter/facade/sidecar/hook/engine/settings/GUI preview compile 통과 |
| Phase F parity | PASS | 손실/MDD/trades delta 0.00% |
| Phase G parity/benchmark | PASS | worst_delta 0.00%, benchmark threshold 내 통과 |
| LS dependency excise | PASS | Phase G 대상에서 LS broker marker 없음 |
| KHOPENAPI 환경 검사 | BLOCKED_EXPECTED | `khopenapi_compatible=false`, live connect 시도 없음 |
| DB health read-only | PASS | `.omx/reports/v3k-db-health.midpoint-20260514.json` 생성, ignored artifact |
| `verify_nonrelease_sync.py` | PASS | 2U_C 비정식 워크트리 guardrail 통과 |
| `git diff --check` | PASS | whitespace error 없음 |
| runtime artifact status guard | PASS | `_database`, `_log`, `*.db`, sidecar/report tracked 변경 없음 |
| `python -m pytest -q` | NOT RUN | 현재 Python 환경에 `pytest` 모듈 없음 |

### 점검 중 수정한 문제

| 파일 | 문제 | 수정 |
|---|---|---|
| `scripts/smoke_v3k_gui_settings_preview.py` | Gate1~3 승인 후 기본 sidecar가 valid가 되면서, “missing sidecar default-OFF” smoke가 현재 sidecar를 읽고 실패 | missing sidecar 전용 tempfile 경로를 명시해 default-OFF 경로를 독립 검증 |
| `scripts/audit_v3k_gui_sidecar_gate1_execution.py` | Gate2/3 이후 같은 sidecar에 Phase F/G가 ON인데 Gate1 감사가 영구 all-OFF만 기대 | Gate1 subset invariant로 변경: Gate1은 기록/안전 경계, 현재 sidecar는 이후 승인된 F/G만 허용 |
| `scripts/audit_v3k_phase_f_gate2_execution.py` | Gate3 이후 Phase G ON을 Phase F 감사가 unapproved로 오판 | Phase F 필수 ON + 이후 승인된 Phase G만 추가 허용하도록 변경 |

## 8. 사용 가능성 판정

| 사용 시나리오 | 지금 사용 가능? | 판정 이유 |
|---|---:|---|
| V3K 기능 구조/코드 검토 | 가능 | 파일/계약/문서가 존재하고 smokes 통과 |
| analyzer/learning/formula 개발 검증 | 가능 | default-OFF, read-only, dry-run 경계 통과 |
| GUI V3K 설정 preview | 가능 | session-only 또는 ignored sidecar 기반. DB 저장 아님 |
| Phase F/G 후보 성능·동작 검증 | 가능 | synthetic/parity/benchmark 범위 가능 |
| Kiwoom live dry-run | 아직 불가 | KHOPENAPI sentinel 없음 |
| 운영 DB cutover | 아직 불가 | 실제 `_database` 적용 승인/백업/rollback gate 필요 |
| 실거래 order/exit 소비 | 아직 불가 | live wiring gate 미승인, 실주문 경로 미연결 |

## 9. 다음 단계 안내

1. **Gate4는 현재 보류**: `khopenapi.dll` 환경 증거가 없으므로 바로 진행하지 않는다.
2. **가능한 대체 진행**: Gate4가 계속 막히면 Gate5/F1도 실제 적용은 보류하고, DB cutover 사전점검·rollback rehearsal 문서/스크립트 검토만 진행한다.
3. **실제 사용 시작 전 필수**: `audit_v3k_phase_h_env_check.py --stdout`에서 KHOPENAPI compatible이 확인되어야 한다.
4. **실거래 전 필수**: DB cutover, live order/exit consumption은 별도 one-gate approval과 no-order dry-run evidence 이후에만 진행한다.
5. **현재 권장 사용 범위**: 개발자 검증, smoke/audit 실행, GUI preview 확인, synthetic benchmark까지만 사용한다.

## 10. 검증 명령 기록

이번 문서의 근거로 다음을 실행했다.

```powershell
# V3K smoke 전체
Get-ChildItem scripts -Filter 'smoke_v3k*.py' | Sort-Object Name | ForEach-Object { python $_.FullName }

# V3K scripts compile 전체
python -m py_compile (Get-ChildItem scripts -Filter '*v3k*.py')

# 주요 게이트/런타임 감사
python scripts/audit_v3k_gui_sidecar_gate1_execution.py
python scripts/audit_v3k_phase_f_gate2_execution.py
python scripts/audit_v3k_phase_g_gate3_execution.py
python scripts/audit_v3k_phase_h_gate4_blocked_environment.py
python scripts/audit_v3k_gate5_gate6_review_only_blocked.py
python scripts/audit_v3k_runtime_activation_gap.py
python scripts/backtest_v3k_phase_f_parity.py --sample-period 7d
python scripts/audit_v3k_phase_f_rollback.py
python scripts/backtest_v3k_phase_g_parity.py
python scripts/benchmark_v3k_phase_g_engine.py
python scripts/audit_v3k_phase_g_ls_excise.py
python scripts/audit_v3k_phase_h_env_check.py --stdout
python scripts/v3k_db_health.py --read-only --output .omx/reports/v3k-db-health.midpoint-20260514.json
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _v3k_sidecar _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
```
