# V3K Phase H H-2 runner P-lane 작성 plan

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-20 KST |
| baseline HEAD | `054cb9b9` (`STOM_Version_2U_C`) |
| Phase | H sub-phase H-2 (runner 코드 작성) |
| lane | **P-lane (preparation)** — actual execution 아님 |
| 본체 plan 인용 | `docs/plans/2026-05-12_v3k_phase_h_live_kiwoom_dryrun_plan.md` §C.0 T04~T07 |
| 지도 plan 인용 | `docs/plans/2026-05-20_v3k_feature_to_page_mapping_overview_plan.md` §4.1 |
| preparation-first 정책 인용 | `docs/plans/2026-05-15_v3k_preparation_first_execution_sequence_plan.md` §3 |
| 코드 변경 | scripts 2~3건 신규, default-OFF, `--ack` 없이는 즉시 abort |
| runtime 활성화 | 0건 |
| operating DB write | 0건 |

---

## §0. 문서 목적

본체 `phase_h_live_kiwoom_dryrun_plan.md` §C에 정의된 T05/T06(+옵션 T07) task를 **오늘 P-lane에서 실제 코드로 작성**하는 실행 plan을 정본화한다.

본 plan 정체성:

- 본체 plan §C task의 *실행 instance*
- preparation-first §4.1 P-lane 작업
- actual execution(A1)은 본 plan 종료 후 별도 사용자 승인 단계에서 진행
- supersede 아님, 본체 plan 본문 무변경

---

## §1. 사전 상태 확인

| 항목 | 상태 |
| --- | --- |
| H-1 hook 모듈 (`strategy/v3k_kiwoom_dryrun_hook.py`) | ✅ 존재 |
| T03 sentinel guard (`scripts/audit_v3k_phase_h_env_check.py`) | ✅ 존재 |
| Gate4 environment status audit (`scripts/audit_v3k_phase_h_gate4_environment_status.py`) | ✅ 존재 (2026-05-15 신설) |
| **T05 runner (`scripts/run_v3k_phase_h_dryrun.py`)** | ❌ **부재 — 본 plan으로 작성** |
| **T06 health smoke (`scripts/smoke_v3k_phase_h_post_health.py`)** | ❌ **부재 — 본 plan으로 작성** |
| T07 audit (`scripts/audit_v3k_phase_h_h2_execution.py`) | 옵션 — page 080/081 패턴 따라 작성 |

---

## §2. 산출물 분해

### §2.1 T05 — `scripts/run_v3k_phase_h_dryrun.py`

**목적**: KHOPENAPI 호환 환경에서 키움 OCX 1회 connect/login 후 V3K preload diagnostic 1회 실행, 즉시 disconnect.

**가드 체인 (모든 가드 통과 후에만 실제 connect 시도)**:

| 가드 | 조건 | 실패 시 |
| --- | --- | --- |
| G1 `--ack` 인자 | required | `sys.exit("Refused: --ack required")` |
| G2 `--account-mode` 인자 | must equal `read-only` | `sys.exit("Refused: account-mode must be read-only")` |
| G3 `V3K_PHASE_H_USER_ACK` env | `== "1"` | `sys.exit("Refused: V3K_PHASE_H_USER_ACK env var not set")` |
| G4 T03 sentinel | `khopenapi_compatible == True` | `sys.exit("Refused: KHOPENAPI sentinel incompatible")` |
| G5 host_identifier | host hash와 evidence 정합 | `sys.exit("Refused: host_identifier mismatch")` |

**실행 흐름 (G1~G5 통과 후)**:

```text
1. PyQt5 QApplication 생성
2. QAxWidget("KHOPENAPI.KHOpenAPICtrl.1") 인스턴스
3. V3KKiwoomDryrunHook(feature_flags={FLAG_PHASE_H_KIWOOM_DRYRUN: True}) 생성
4. hook.register(ocx) — OnEventConnect 이벤트에만 등록
5. ocx.dynamicCall("CommConnect()") — Open API login 창 띄움
6. QTimer.singleShot(30_000, app.quit) — 30초 timeout
7. app.exec_() — 이벤트 루프 진입
8. 이벤트 루프 종료 후:
   - hook.collect_result() 호출
   - .omx/reports/v3k-phase-h-dryrun-<utc>.json archive
9. ocx.dynamicCall("CommTerminate()")
10. sys.exit(0)
```

**절대 호출 금지 API** (LH1 invariant):

- `SendOrder`, `SendOrderCredit`, `SendOrderFO`
- `GetAccountList`, `GetLoginInfo("ACCNO")`
- `OPW00018` (잔고조회), `OPW00001` (예수금)
- `KOA_Functions("ShowAccountWindow", ...)` 등 모든 계좌 관련

→ 정적 grep audit으로 강제 (T07 audit 또는 verify_1a 확장).

**산출 schema**:

```json
{
  "schema_version": 1,
  "plan_ref": "2026-05-20_v3k_phase_h_h2_runner_prep_lane_plan.md",
  "captured_at_utc": "2026-05-...",
  "host_identifier": "9024e3b9",
  "sentinel": {
    "khopenapi_compatible": true,
    "primary_signal": {"source": "ActiveX ProgID", "path": "...", "exists": true},
    "schema_version": 2
  },
  "user_ack": "V3K_PHASE_H_USER_ACK=1",
  "connect_result_code": 0,
  "login_succeeded": true,
  "diagnostic_steps": [
    {"step": "preload_analyzer_modules", "result": "ok", "elapsed_ms": 12},
    {"step": "verify_v3k_shadow_db_readable", "result": "ok", "elapsed_ms": 4},
    {"step": "smoke_v3k_kiwoom_adapter", "result": "ok", "elapsed_ms": 8}
  ],
  "order_api_calls": 0,
  "account_api_calls": 0,
  "elapsed_sec": 12.4,
  "disconnect_clean": true
}
```

### §2.2 T06 — `scripts/smoke_v3k_phase_h_post_health.py`

**목적**: dry-run 후 Kiwoom runtime / operating DB / 코드 경로 무변경 검증.

**검증 항목**:

| # | 항목 | 통과 조건 |
| ---: | --- | --- |
| 1 | 최신 archive 로드 | `glob(".omx/reports/v3k-phase-h-dryrun-*.json")` 가장 최근 |
| 2 | scope_guard order_api_calls | `== 0` |
| 3 | scope_guard account_api_calls | `== 0` |
| 4 | operating `_database/` mtime | dry-run 전후 동일 |
| 5 | `trade/`, `utility/`, `Kiwoom_OpenAPI/` 코드 diff | git diff 결과 0건 |
| 6 | `_v3k_sidecar/v3k_gui_settings.json` toggle | Phase F/G 토글 false 유지 |
| 7 | host_identifier 매치 | archive와 본 PC host hash 동일 |

실패 시 `sys.exit(2)` + 어느 항목 실패인지 stdout/stderr 출력.

### §2.3 (옵션) T07 — `scripts/audit_v3k_phase_h_h2_execution.py`

page 080/081 (Phase F/G gate2/3) 패턴 그대로 Phase H gate4 execution audit 작성:

- canonical approval phrase: `I approve phase-h-h2-await-user-approval only`
- required USER_ACK: `V3K_PHASE_H_USER_ACK=1`
- enable registry: `V3K-PHASE-H-ENABLE`
- sidecar source-of-truth (없음 — Phase H는 sidecar 토글이 아니라 archive 기반)

T07은 plan에 명시만 하고 본 plan에서는 T05/T06까지만 작성한다. T07은 다음 P-lane plan에서 처리.

---

## §3. Task 분해

| Task | 산출 | 검증 |
| --- | --- | --- |
| P-T05-01 | `scripts/run_v3k_phase_h_dryrun.py` (G1~G5 가드 + 실행 흐름 + archive 생성) | `python -m py_compile` |
| P-T05-02 | G1~G5 abort 시나리오 5건 mock 실행 | 각 시나리오 적절한 exit code + stderr 메시지 |
| P-T06-01 | `scripts/smoke_v3k_phase_h_post_health.py` (검증 7건) | `python -m py_compile` |
| P-T06-02 | T06 mock 실행 (archive 없는 상태) | 우아한 abort |
| P-VERIFY | 기존 audit suite 회귀 0건 | gate4_environment_status + verify_1a + verify_nonrelease_sync 모두 PASS |
| P-EVIDENCE | `.omx/reports/v3k-phase-h-h2-runner-prep-<host>.json` mock evidence 1건 | scope_guard 7항목 모두 false |
| P-REGISTRY | `docs/CARRY_FORWARD_REGISTRY.md` `V3K-PHASE-H-H2-RUNNER-PREP` 섹션 추가 | grep 매치 |
| P-COMMIT | 한글 commit 메시지 | git log 정합 |

---

## §4. 검증 명령 (작성 후)

```powershell
# 1) 정적 검증
python -m py_compile scripts/run_v3k_phase_h_dryrun.py
python -m py_compile scripts/smoke_v3k_phase_h_post_health.py

# 2) G1 abort (--ack 없이)
python scripts/run_v3k_phase_h_dryrun.py
# expected: exit 1, "Refused: --ack required"

# 3) G2 abort (--account-mode 잘못된 값)
python scripts/run_v3k_phase_h_dryrun.py --ack --account-mode full
# expected: exit 1, "Refused: account-mode must be read-only"

# 4) G3 abort (USER_ACK env 미설정)
python scripts/run_v3k_phase_h_dryrun.py --ack --account-mode read-only
# expected: exit 1, "Refused: V3K_PHASE_H_USER_ACK env var not set"

# 5) T06 mock 실행 (archive 없는 상태)
python scripts/smoke_v3k_phase_h_post_health.py
# expected: exit 2 또는 graceful "no archive found"

# 6) 기존 audit suite 회귀
python scripts/audit_v3k_phase_h_gate4_environment_status.py
python scripts/audit_v3k_verify_1a.py --base 9423735e
python scripts/verify_nonrelease_sync.py
git diff --check
```

→ **이 시점까지 절대 G1~G5를 모두 통과시키지 않는다.** 모두 통과시키는 순간 Kiwoom OCX 실제 connect가 시도되므로, 이는 A-lane(actual execution) 진입을 의미한다.

---

## §5. scope_guard (P-lane 종료 시점)

| # | 항목 | 통과 조건 |
| ---: | --- | --- |
| 1 | kiwoom_runtime_mutated | False |
| 2 | ls_direct_dependency_added | False |
| 3 | operating_database_write_attempted | False |
| 4 | live_connect_attempted | False (G3 가드에서 abort) |
| 5 | user_ack_emitted | False |
| 6 | monitoring_24h_or_more_collected | False (P-lane이라 N/A) |
| 7 | sidecar_toggle_changed | False |

본 P-lane plan commit은 위 7항목 모두 False로 archive에 기록한다.

---

## §6. preparation-first §3 정합

| §3 허용 | 본 plan |
| --- | --- |
| default-OFF adapter | ✅ G1~G5 가드로 default-OFF |
| read-only dry-run | ✅ `--account-mode read-only` 강제 |
| audit/evidence schema | ✅ archive JSON |
| approval phrase guard / USER_ACK guard | ✅ G3 가드 |

| §3 금지 | 본 plan |
| --- | --- |
| 운영 `_database/` write | ❌ 0건 |
| live connect/login | ❌ runner 작성으로 0건 |
| feature flag default-ON 전환 | ❌ default-OFF 유지 |
| Kiwoom 주문/청산/exit runtime wiring 변경 | ❌ LH1 invariant 강제 |
| LS Securities direct dependency 추가 | ❌ |

→ P-lane 적격.

---

## §7. 종료 조건

```text
- T05 runner + T06 smoke 파일 신설
- G1~G5 abort 시나리오 5건 모두 PASS
- 기존 audit suite 회귀 0건
- mock evidence JSON 1건 archive
- CARRY_FORWARD_REGISTRY V3K-PHASE-H-H2-RUNNER-PREP 섹션 추가
- runtime activation 0건
- A-lane(actual execution) 미진입
```

---

## §8. 다음 인계 (A-lane 진입 조건)

본 P-lane plan이 종료된 후, 사용자 명시 phrase + USER_ACK env var 발급 시점에 A-lane 진입.

A-lane 진입 시 실행 절차:

```powershell
# A1 — Phase H H-2 actual
$env:V3K_PHASE_H_USER_ACK='1'
python scripts/run_v3k_phase_h_dryrun.py --ack --account-mode read-only
# → Open API login 창 GUI 띄움 → 사용자가 로그인 → diagnostic 1회 → disconnect

# 검증
python scripts/smoke_v3k_phase_h_post_health.py
# → scope_guard 7항목 모두 False 확인

# 24h monitoring 시작
```

이후 Step 3(F1 DB cutover)로 진입할 수 있다. 본 P-lane plan은 A-lane 진입 trigger를 *준비*만 하고 *발사*하지 않는다.

---

## §9. 관련 문서

- `docs/plans/2026-05-12_v3k_phase_h_live_kiwoom_dryrun_plan.md` (본체 plan, §C T05/T06 task 정의)
- `docs/plans/2026-05-20_v3k_feature_to_page_mapping_overview_plan.md` (지도 plan §4.1)
- `docs/plans/2026-05-15_v3k_preparation_first_execution_sequence_plan.md` (P-lane 기준)
- `docs/plans/2026-05-15_v3k_phase_h_lh4_clarification_plan.md` (Gate4 audit 분기)
- `docs/update_log/2026-05-15_v3k_midpoint_checkpoint_cd6f5bd_to_4dbac74f.md` (50% 마일스톤)
- `docs/CARRY_FORWARD_REGISTRY.md`
