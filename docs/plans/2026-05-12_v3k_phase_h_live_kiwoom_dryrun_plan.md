# V3K Phase H — Live Kiwoom Dry-run Hook 실행 계획 (잔여 plan, audit §6.2 #5)

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-12 KST |
| audit §6.2 항목 | #5 live Kiwoom runtime dry-run hook |
| audit §8 원안 letter | E (live Kiwoom dry-run hook) |
| F2 후 letter | **H** (재배치 — F2 `cba6fc7e` §2.2 정본) |
| 현재 단계 (F6 산식) | S0 (0%) — plan 미작성이 v2 mid-checkpoint 시점의 잔여 항목 |
| 목표 단계 | S4 (100%) operational — KHOPENAPI 호환 환경에서 dry-run hook 작동 |
| 위험도 | 중간–높음 (live Kiwoom runtime 인접, 단 dry-run만 수행) |
| sub-phase 의무 분해 | **H-1 / H-2 / H-3** |
| **`--deliberate` ralplan 의무** | **YES** (live Kiwoom runtime 인접성) |
| 의존 입력 | Phase A·D 완료 권장. F1 cutover는 무관. F3·F4와 독립적 진행 가능 |
| Phase A plan §K.5 의무 인용 | audit / Phase A plan / mid-checkpoint v1·v2 / F2 / F6 / F7 |

---

## 0. V3K 미션 재인용

```text
V3K = V3 신기능을 STOM_Version_2U_C에 모두 반영한다.
LS Securities REST/TR/REAL 직접 의존은 제외하고 Kiwoom증권 API/runtime을 유지한다.
STOM CLI surface의 외부 동작도 유지한다.
DB는 운영 _database/와 격리된 _database_v3k_shadow/로 separate 후 단계적 cutover한다.
feature flag는 모든 phase에서 default-OFF로 유지한다.
```

audit §8 원안 Phase E(=letter H)의 정본 정의:

```text
Kiwoom live runtime에서 주문/청산 경로를 바꾸지 않고 V3K preload diagnostic만 남긴다.
완료 조건:
- KHOPENAPI 호환 환경에서 실행한다.
- 주문, 청산, 계좌, 체결 처리 경로를 변경하지 않는다.
- dry-run log만 남긴다.
```

본 plan은 위 정의를 letter H로 정본화한다. dry-run hook은 audit §6.2 #5 종착 조건이지만 **dry-run 본연의 비-침습성** 때문에 live order/exit 직접 변경(별도 phase 필요)과 분리된다.

---

## A. Drivers + Scope

### A.1 Drivers

1. audit §6.2 #5 종착 조건 (live Kiwoom runtime dry-run hook 작동)
2. v2 mid-checkpoint(`48a2cb05`) §9.1의 유일한 미작성 plan 항목 해소
3. Plan coverage 85.7% → 100% 완성
4. Phase A·B·D 산출물(adapter, contract, learning DB read)이 live runtime에서 정상 동작하는지 dry-run 검증 (코드/DB는 무영향)

### A.2 Scope

| In scope | Out of scope |
| --- | --- |
| Kiwoom OCX connect/login 후 V3K preload diagnostic 1회 실행 | 주문/청산/계좌/체결 처리 경로 변경 (영구 금지, P1) |
| Kiwoom 시세/잔고 read-only fetch로 V3K adapter 정상 동작 확인 | analyzer output을 매매 판단에 사용 (F3 Phase F 별도) |
| dry-run log archive (`.omx/reports/v3k-phase-h-*.json`) | live order signal 생성 또는 발행 |
| feature flag 이중 gate + rollback flag (Phase F LF1–LF2 패턴 재사용) | KHOPENAPI 환경 자체 설치/구성 (운영자 책임) |
| KHOPENAPI 호환 환경 사전 검증 smoke | LS Securities 직접 의존 (L7 영구 금지) |

---

## B. Phase-specific invariants

### B.1 보존 (L1–L9)

모두 보존. 특히:
- **L7**: LS 의존 도입 절대 금지 (Phase H는 Kiwoom 전용)
- **L9**: STOM CLI surface 보존 — dry-run hook은 hook으로만 동작, CLI 시그니처 변경 0건

### B.2 신규 Phase H 전용 invariants (LH1–LH4)

| # | invariant | 사유 |
| --- | --- | --- |
| LH1 | Kiwoom 주문/청산/계좌/체결 처리 경로 코드 무변경 (P1 강화) | audit §8 정의의 핵심 |
| LH2 | dry-run hook은 Kiwoom connect/login 직후 한 번만 실행 (idempotent) | side effect 차단 |
| LH3 | dry-run log는 `.omx/reports/v3k-phase-h-*.json`에만 archive. live trade log 별도 보존 | 격리 |
| LH4 | KHOPENAPI 호환 환경 외 실행 거부 (sentinel guard) | 환경 외 실수 차단 |

---

## C. 상세 실행 계획 — sub-phase 분해 (H-1 / H-2 / H-3)

본 plan은 다음 3 sub-phase로 분해한다.

| sub-phase | 목표 | 위험 수준 |
| --- | --- | --- |
| H-1 | dry-run hook 설계 + no-GUI smoke (KHOPENAPI 없이 시뮬레이션) | 낮음 |
| H-2 | KHOPENAPI 호환 환경에서 connect/login 후 dry-run 1회 실행 + log archive | 중간 |
| H-3 | feature flag 이중 gate + rollback flag + 사용자 명시 승인 ON + 7일 모니터링 | 중간 |

### C.0 task별 실행/commit lane

| Task | sub-phase | lane | commit lane |
| --- | --- | --- | --- |
| T01 (dry-run hook 모듈 설계) | H-1 | 양쪽 | 2U_C |
| T02 (no-GUI smoke) | H-1 | 양쪽 | 2U_C |
| T03 (KHOPENAPI sentinel guard) | H-1 | 양쪽 | 2U_C |
| T04 (KHOPENAPI 호환 환경 검증 script) | H-2 | **KHOPENAPI 환경** | 2U_C |
| T05 (live dry-run 1회 실행 + log archive) | H-2 | **KHOPENAPI 환경**, ack 후 | 2U_C |
| T06 (post-dry-run health smoke) | H-2 | **KHOPENAPI 환경** | 2U_C |
| T07 (feature flag 이중 gate + rollback flag) | H-3 | 2U_C | 2U_C |
| T08 (사용자 명시 승인 dance) | H-3 | n/a | n/a |
| T09 (ON commit + V3K-PHASE-H-ENABLE registry) | H-3 | 2U_C, ack 후 | 2U_C |
| T10 (7일 모니터링 audit) | H-3 | 양쪽 | 2U_C |

### T01 — dry-run hook 모듈 설계

- 목표: Kiwoom connect/login 직후 hook을 받아 V3K preload diagnostic을 호출하는 모듈 신설. read-only 강제
- 변경 파일:
  - `strategy/v3k_kiwoom_dryrun_hook.py` (신규)
- 변경 의도:
  - class `V3KKiwoomDryrunHook` — `register(receiver)` method가 connect/login event listener에 self를 등록 (event-driven, polling 아님)
  - `on_login(account_info)` callback — V3K adapter의 read-only smoke 1회 호출 후 log emit
  - **주문/청산/계좌수정 경로에 절대 hook 등록 금지** — audit guard로 차단
  - default-OFF: feature flag OFF 시 register는 no-op
- 완료 조건:
  ```powershell
  python -m py_compile strategy/v3k_kiwoom_dryrun_hook.py
  python -c "from strategy.v3k_kiwoom_dryrun_hook import V3KKiwoomDryrunHook; h=V3KKiwoomDryrunHook(); assert callable(h.register)"
  ```
  PASS: 둘 다 exit 0
- 선행: 없음

### T02 — no-GUI smoke (KHOPENAPI 없이 시뮬레이션)

- 목표: T01 hook의 unit-level 동작을 KHOPENAPI 없이 검증
- 변경 파일:
  - `scripts/smoke_v3k_phase_h_hook_unit.py` (신규)
- 변경 의도:
  - mock receiver를 만들어 connect/login event를 simulate
  - hook이 register됐을 때 diagnostic 1회 호출, 두 번째 event는 ignore (LH2 idempotent)
  - 주문/청산 event 발생 시 hook이 trigger되지 않음을 검증 (LH1)
- 완료 조건:
  ```powershell
  python scripts/smoke_v3k_phase_h_hook_unit.py
  ```
  PASS: exit 0 + 모든 LH1/LH2 시나리오 PASS
- 선행: T01

### T03 — KHOPENAPI sentinel guard (LH4)

- 목표: KHOPENAPI 호환 환경 외에서 dry-run 실행 시 자동 거부
- 변경 파일:
  - `strategy/v3k_kiwoom_dryrun_hook.py` (수정 — guard 추가)
  - `scripts/audit_v3k_phase_h_env_check.py` (신규)
- 변경 의도:
  - guard: `register()` 호출 시 `khopenapi.dll` 존재 여부 확인 (Path.is_file)
  - 미존재 시 SystemExit("KHOPENAPI environment required for Phase H")
  - audit script: 환경 확인 결과를 `.omx/reports/v3k-phase-h-env-<utc>.json`에 emit
- 완료 조건:
  ```powershell
  python scripts/audit_v3k_phase_h_env_check.py --stdout
  ```
  PASS: KHOPENAPI 환경 검증 결과 출력 (호환/비호환 명시)
- 선행: T01

### T04 — KHOPENAPI 호환 환경 검증 (H-2 사전)

- 목표: 본격 dry-run 실행 전 환경 사전 점검
- 변경 파일: `scripts/smoke_v3k_phase_h_kiwoom_env.py` (신규)
- 변경 의도:
  - KHOPENAPI 호환 인터프리터(예: Python 32-bit)에서 실행
  - OCX 등록 여부 확인 (registry read-only)
  - 실제 connect 시도 없음 (환경 검증만)
- 완료 조건:
  ```powershell
  python scripts/smoke_v3k_phase_h_kiwoom_env.py
  ```
  PASS: 환경 호환 시 exit 0 + 호환 정보 출력
- 선행: T03

### T05 — live dry-run 1회 실행 + log archive

- 목표: KHOPENAPI 호환 환경에서 Kiwoom connect/login 후 V3K dry-run 1회 실행
- 변경 파일:
  - `scripts/run_v3k_phase_h_dryrun.py` (신규)
  - `.omx/reports/v3k-phase-h-dryrun-<utc>.json` (산출 commit)
- 변경 의도:
  - argparse: `--ack` required (사용자 명시 승인 marker), `--account-mode read-only` required
  - 실행 절차: (1) T03 sentinel guard 통과 → (2) Kiwoom OCX connect/login → (3) T01 hook이 등록되어 diagnostic 1회 실행 → (4) log를 JSON으로 archive → (5) disconnect
  - **주문/청산 API 절대 호출 금지** (audit guard로 차단)
- 완료 조건:
  ```powershell
  python scripts/run_v3k_phase_h_dryrun.py --ack --account-mode read-only
  ```
  PASS: exit 0 + log archive 파일 생성 + 주문 API 0건 호출
- 선행: T04 + 사용자 명시 승인

### T06 — post-dry-run health smoke

- 목표: dry-run 후 Kiwoom runtime 상태가 무변경인지 검증
- 변경 파일: `scripts/smoke_v3k_phase_h_post_health.py` (신규)
- 변경 의도:
  - dry-run 전후 process/handler state 비교
  - 주문/청산 history가 0건 추가됨을 확인
- 완료 조건: 호환 환경에서 PASS
- 선행: T05

### T07 — feature flag 이중 gate + rollback flag (Phase F LF1–LF2 패턴)

- 목표: ON 시점 차단 안전망
- 변경 파일: `strategy/v3k_kiwoom_dryrun_hook.py` (수정)
- 변경 의도:
  - gate1: 환경 변수 `V3K_PHASE_H_ENABLE=1`
  - gate2: `v3k_meta.db.v3k_feature_flags`의 row `phase_h_kiwoom_dryrun.enabled=1`
  - rollback flag: `V3K_PHASE_H_DISABLE=1` → 즉시 OFF (LF2 패턴)
- 완료 조건: gate 시뮬 + rollback flag 시뮬 PASS
- 선행: T06

### T08 — 사용자 명시 승인 dance

- form: F7 §2 Gate 2 유사
- 완료 조건: 사용자 명시 "승인" 응답
- 선행: T07

### T09 — ON commit + V3K-PHASE-H-ENABLE registry

- 사전 조건: T08 사용자 명시 승인 + `V3K_PHASE_H_USER_ACK=1`
- 변경 파일:
  - `docs/CARRY_FORWARD_REGISTRY.md` (수정)
  - `.omx/reports/v3k-phase-h-enable-<utc>.json` (신규, audit trail)
- 완료 조건: registry 매치 + ON commit 후 dry-run hook 작동 확인
- 선행: T08

### T10 — 7일 모니터링 audit (LC3와 동일 패턴)

- 변경 파일: `scripts/audit_v3k_phase_h_post_enable_monitor.py` (신규)
- 변경 의도: ON commit 후 7일 동안 dry-run log 정상 archive 확인
- 완료 조건: 7일 경과 + dry-run log 일관성 PASS
- 선행: T09

---

## D. 검증 단계 V01–V12

| # | 명령 | lane | PASS |
| --- | --- | --- | --- |
| V01 | py_compile 4 scripts | 양쪽 | exit 0 |
| V02 | `python scripts/smoke_v3k_phase_h_hook_unit.py` | 양쪽 | exit 0 |
| V03 | `python scripts/audit_v3k_phase_h_env_check.py --stdout` | 양쪽 | 환경 정보 출력 |
| V04 | `python scripts/smoke_v3k_phase_h_kiwoom_env.py` | **KHOPENAPI 환경** | exit 0 |
| V05 | KHOPENAPI 비호환 환경에서 `register()` 시도 | 비호환 환경 | SystemExit + "KHOPENAPI required" |
| V06 | `python scripts/run_v3k_phase_h_dryrun.py --ack --account-mode read-only` | **KHOPENAPI 환경, ack 후** | exit 0 + log archive |
| V07 | `python scripts/smoke_v3k_phase_h_post_health.py` | **KHOPENAPI 환경** | 주문 history 변화 0건 |
| V08 | feature flag 이중 gate 시뮬 | 2U_C | env+DB 동시 충족 시에만 ON |
| V09 | `V3K_PHASE_H_DISABLE=1` 설정 시 즉시 OFF | 2U_C | OFF 작동 |
| V10 | `Select-String docs/CARRY_FORWARD_REGISTRY.md -Pattern "^## V3K-PHASE-H-ENABLE"` | 양쪽 | 매치 1건 |
| V11 | `git diff cd6f5bd2..HEAD --name-only -- trade/ utility/ Kiwoom_OpenAPI/` | 양쪽 | **0건** (LH1 보존) |
| V12 | `python scripts/verify_release_sync.py` | 양쪽 | preflight passed |

---

## E. 위험 매트릭스

| ID | 위험 | 영향도 | 발생가능성 | (Trigger, 자동탐지, 차단액션) |
| --- | --- | --- | --- | --- |
| R1 | 주문/청산/계좌 처리 경로 변경 (LH1·P1 위반) | **치명** | 매우 낮음 | (trade/utility/ 변경, V11 audit, commit reject) |
| R2 | dry-run hook이 idempotent하지 않음 (LH2 위반) | 높음 | 낮음 | (T02 smoke의 두 번째 event 호출 시 hook 재실행, exit 1) |
| R3 | KHOPENAPI 비호환 환경에서 dry-run 시도 (LH4 위반) | 높음 | 중간 | (T03 sentinel guard, SystemExit) |
| R4 | live trade log와 dry-run log 혼재 (LH3 위반) | 중간 | 낮음 | (log path 불일치, T05 출력 path 검증) |
| R5 | rollback flag 미작동 | 치명 | 낮음 | (T07 후 V09 시뮬 FAIL, T09 commit 차단) |
| R6 | feature flag 단일 gate | 높음 | 낮음 | (T07 단일 gate 적용, V08 FAIL) |
| R7 | LS 직접 의존 신규 (L7 위반) | 치명 | 매우 낮음 | (LS marker grep, audit reject) |
| R8 | Kiwoom OCX state 손상 | 치명 | 낮음 | (V07 health smoke FAIL, F.1 rollback) |
| R9 | dry-run 중 unexpected disconnect | 중간 | 중간 | (T05 disconnect handler, idempotent 보존) |
| R10 | 사용자 승인 없이 ON | 치명 | 낮음 | (V3K_PHASE_H_USER_ACK 미설정, T09 reject) |
| R11 | DB 파일 commit (L8) | 높음 | 낮음 | (`*.db` git status, `.gitignore` guard) |
| R12 | CLI surface 변경 (L9) | 높음 | 낮음 | (init/backtest CLI 시그니처 변경, audit reject) |

---

## F. Rollback 절차

### F.1 dry-run 도중 Kiwoom state 이상 발견 (R8)

```powershell
# 1) rollback flag 즉시 설정
$env:V3K_PHASE_H_DISABLE = "1"
# 2) Kiwoom OCX 종료
# 3) 운영 환경 점검 (별도 KOA Studio 등)
# 4) audit
python scripts/audit_v3k_phase_h_env_check.py
```

### F.2 ON commit 후 7일 모니터링 중 문제

```powershell
# 1) rollback flag 적용
$env:V3K_PHASE_H_DISABLE = "1"
# 2) DB row UPDATE (phase_h_kiwoom_dryrun.enabled=0)
# 3) ON commit revert (최후 수단)
git -C C:/System_Trading/STOM/STOM_V.wt-dev revert <on-commit-sha> --no-edit
```

### F.3 hook이 idempotent하지 않음 (R2)

```powershell
# 1) T02 smoke 재실행으로 재현
python scripts/smoke_v3k_phase_h_hook_unit.py
# 2) T01 hook 모듈에서 idempotent guard 추가
# 3) T02 통과 후 재진행
```

---

## G. 산출물

### G.1 Commit 포함 (~10건, sub-phase별 분리)

| sub-phase | commit 예상 |
| --- | --- |
| H-1 | hook 모듈 + unit smoke + sentinel guard + env check audit = 4건 |
| H-2 | env smoke + dry-run runner + post-health smoke + log archive report = 4건 |
| H-3 | gate + rollback + ON commit + registry + 7일 monitor = 5건 |

세부:
1. `strategy/v3k_kiwoom_dryrun_hook.py` (신규)
2. `scripts/smoke_v3k_phase_h_hook_unit.py` (신규)
3. `scripts/audit_v3k_phase_h_env_check.py` (신규)
4. `scripts/smoke_v3k_phase_h_kiwoom_env.py` (신규)
5. `scripts/run_v3k_phase_h_dryrun.py` (신규)
6. `scripts/smoke_v3k_phase_h_post_health.py` (신규)
7. `scripts/audit_v3k_phase_h_post_enable_monitor.py` (신규)
8. `.omx/reports/v3k-phase-h-env-<utc>.json` (audit trail)
9. `.omx/reports/v3k-phase-h-dryrun-<utc>.json` (audit trail)
10. `.omx/reports/v3k-phase-h-enable-<utc>.json` (ON commit 시점)
11. `docs/CARRY_FORWARD_REGISTRY.md` (수정 — V3K-PHASE-H-ENABLE)

### G.2 Ephemeral 또는 commit 금지

- `_database/` DB row 변경 (L8 — feature flag DB row는 운영 DB로 갈 시 commit 금지)
- Kiwoom OCX 상태 (런타임만 존재)

---

## H. Commit message 한국어 sample

### H.1 H-1 — hook 모듈

```text
V3K Phase H Kiwoom dry-run hook 모듈을 도입한다 (H-1)

- `strategy/v3k_kiwoom_dryrun_hook.py`를 신규 작성한다.
- connect/login event 직후 V3K preload diagnostic을 1회만 실행한다 (LH2 idempotent).
- 주문/청산/계좌수정 경로에는 절대 hook을 등록하지 않는다 (LH1 보존).
- KHOPENAPI 미호환 환경에서는 sentinel guard로 실행을 거부한다 (LH4).
```

### H.2 H-2 — KHOPENAPI 환경 dry-run

```text
V3K Phase H live Kiwoom dry-run을 1회 실행한다 (H-2)

- KHOPENAPI 호환 환경에서 connect/login 후 V3K preload diagnostic을 1회 실행한다.
- dry-run log를 `.omx/reports/v3k-phase-h-dryrun-<utc>.json`에 archive한다.
- 주문/청산 API는 단 1건도 호출되지 않는다 (LH1 보존).
```

### H.3 H-3 — ON 전환

```text
V3K Phase H Kiwoom dry-run hook을 ON으로 전환한다 (H-3)

- 사용자 명시 승인(V3K_PHASE_H_USER_ACK=1) 후 feature flag 이중 gate를 ON한다.
- registry V3K-PHASE-H-ENABLE 섹션을 추가한다.
- 7일 모니터링을 시작하며 한계 이탈 시 rollback flag 즉시 적용한다.
```

---

## I. ADR 요지

- **Decision**: Phase H는 H-1(설계+unit smoke)/H-2(KHOPENAPI dry-run)/H-3(ON 전환) 3 sub-phase로 분해. LH1–LH4 신규 invariant + Phase F LF1–LF2 패턴 재사용
- **Drivers**: audit §6.2 #5 종착, v2 mid-checkpoint 잔여 plan 해소, Phase A–D 산출물의 live runtime 정상 작동 검증
- **Alternatives considered**:
  - Phase letter E로 letter 충돌 유지 → F2로 명시 차단됨, letter H 재배치 결정
  - single phase (분해 없음) → live runtime 인접성으로 H-1/H-2/H-3 분해로 위험 격리
  - polling 방식 (event 아닌) → idempotent 보장 어려움, 기각
- **Why chosen**: event-driven hook + idempotent guard + KHOPENAPI sentinel + 이중 gate + rollback flag 5중 안전망
- **Consequences**:
  - 긍정: F6 #5 항목 S4 도달, plan coverage 100%, V3K 미션 closure gate(F7) 진입 가능
  - 부정: KHOPENAPI 호환 환경 의존성. CI 자동화 어려움 (수동 검증 필요)
- **Follow-ups**:
  - F1 cutover 후 Phase H 재실행으로 cutover된 운영 DB의 read-only smoke 검증 가능
  - Phase F + H 결합 효과 (analyzer output이 live Kiwoom data로 dry-run) 통합 smoke

---

## J. 핵심 설계 질문

### Q1. KHOPENAPI 호환 환경이 없으면?
A. T03 sentinel guard가 SystemExit. T04/T05/T06은 진행 불가. H-1까지만 commit하고 H-2/H-3는 환경 확보 후 진행.

### Q2. dry-run 중 unexpected disconnect 발생 시?
A. T01 hook의 disconnect handler가 LH2 idempotent을 보존. 다음 connect 시 hook이 재실행되지 않음.

### Q3. live order/exit를 변경하지 않는다고 어떻게 보장하나?
A. (a) T01 hook 등록 path가 connect/login만 (b) audit guard가 `trade/`/`utility/` diff 0건 강제 (c) V11 검증.

### Q4. Phase F·G와의 순서?
A. 본 plan은 Phase F·G와 독립적. Phase A·B·D 산출물 기반이므로 Phase F·G 미진행이어도 실행 가능. 단, Phase F 또는 G의 ON 후 결합 효과 smoke는 별도 follow-up.

### Q5. 7일 모니터링은 왜?
A. Phase F LF3·F1 LC3 패턴 재사용. live runtime 인접성 때문에 안정성 확인 시간 필요. 7일 미만에 새 변경 금지.

---

## K. 다음 단계 전환 지침

### K.1 완료 조건

- T01–T10 모두 commit (T08은 사용자 명시 승인, T05/T06는 KHOPENAPI 환경)
- V01–V12 모두 PASS
- F6 산식 #5 항목 S0 → S4 전이 확인
- 7일 monitoring 통과

### K.2 본 phase 완료 후 진행 가능한 phase

- **closure gate (F7)**: §1.1 #5 종착 조건 PASS — Phase F·G 미완료여도 #5는 S4 달성
- **Phase F + H 결합 smoke**: follow-up
- **Phase G + H 결합 smoke**: follow-up

### K.3 본 plan freeze 정책

Phase H H-3 ON commit 후 본 plan freeze.

### K.4 `--deliberate` ralplan 의무

본 plan 실행 전 `--deliberate` ralplan 재합의 필수. live Kiwoom runtime 인접성으로 pre-mortem 3 시나리오(disconnect / OCX state 손상 / dry-run log 누설) + expanded test plan 보강 권장.

### K.5 audit script identity policy + 분기 logic + LH5 schema invariant (amend, 분기 plan `2026-05-15_v3k_phase_h_lh4_clarification_plan.md` 합의 결과)

본 절은 v2-compat sentinel plan(`4d132139`)에서 별도 분기 plan으로 위임된 §K.7 freeze 예외 사안의 통합 정정이며, 분기 plan(`docs/plans/2026-05-15_v3k_phase_h_lh4_clarification_plan.md`, ralplan iteration 2 APPROVE 합의)의 §K.5 amend 결정을 본 plan에 반영한다. K.1–K.4 본문은 무변경(추가만 허용).

**audit script identity policy (Option B 채택)**: `scripts/audit_v3k_phase_h_gate4_blocked_environment.py`는 commit `b6327b30`의 historical audit trail로 frozen 보존한다. 신규 `scripts/audit_v3k_phase_h_gate4_environment_status.py`(`V3K_PHASE_H_GATE4_ENV_STATUS_AUDIT_V1`)를 병렬 추가하여 active polling을 담당한다. rename(Option A)은 audit immutability + docs freeze 충돌 우려로 명시 거부.

**`primary_signal.exists` 분기 logic (LH4 ↔ V07 invariant)**:

| `primary_signal.exists` | 활성 audit | 동작 |
| --- | --- | --- |
| `True` | `audit_v3k_phase_h_gate4_environment_status.py` (unblocked branch) | `khopenapi_compatible=True` 검증 + H-2 dry-run은 별도 사용자 명시 승인 + `V3K_PHASE_H_USER_ACK=1` 필수 |
| `False` | `audit_v3k_phase_h_gate4_environment_status.py` (blocked_or_pending branch) + historical script | 기존 blocked 동작 검증 보존 |

V05 결정 룰(분기 plan §D.1)과 정합. 어느 branch도 live connect/login 시도 + 주문/청산 경로 변경 0건을 자동 검증.

**LH5 forward-only schema invariant (신규 lifetime invariant)**: audit JSON `schema_version >= 2` artifact에만 적용한다. `schema_version == 1` historical audit(예: `b6327b30` 시점 결과)은 적용 범위 외이며 retroactive 재평가하지 않는다. 신규 LH 추가 또는 audit JSON 구조 변경은 schema_version 정수 bump를 동반한다.

**K.6/K.7 위임**: 미래 추가 freeze 예외/lifetime invariant 사안은 본 plan §K에 K.6/K.7로 amend하지 않고 별도 분기 plan으로 위임한다. 본 §K.5 단일 절 신설로 분기 plan §I.6 합의를 충족한다.

---

## L. 관련 문서 (Phase A plan §K.5 + F2 §3.3 의무 인용)

- `docs/update_log/2026-05-10_2uc_v3k_full_feature_audit.md` (§6.2 #5, §8 원안 Phase E 정의)
- `docs/plans/2026-05-10_v3k_phase_a_shadow_db_plan.md` (Phase A plan §0/§K)
- `docs/update_log/2026-05-12_v3k_midpoint_checkpoint_cd6f5bd_to_e1c4619c.md` (v1 mid-checkpoint)
- `docs/update_log/2026-05-12_v3k_midpoint_checkpoint_cd6f5bd_to_067886d3.md` (v2 mid-checkpoint, 본 plan은 v2 §9.1 잔여 항목)
- `docs/update_log/2026-05-12_v3k_phase_letter_remapping_decision.md` (F2, letter H 정본)
- `docs/update_log/2026-05-12_v3k_progress_metric_methodology.md` (F6 산식)
- `docs/update_log/2026-05-12_v3k_mission_closeout_procedure.md` (F7 closure)
- `docs/plans/2026-05-12_v3k_phase_f_analyzer_strategy_plan.md` (F3, LF 패턴)
- `docs/plans/2026-05-12_v3k_phase_g_microstructure_engine_plan.md` (F4, sub-phase 분해 패턴)
- `docs/CARRY_FORWARD_REGISTRY.md` (V3K-PHASE-H-ENABLE 등록 위치)
