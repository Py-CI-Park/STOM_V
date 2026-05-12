# V3K Ralph 명령어 Playbook — 미션 완료까지의 실행 명령 모음

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-12 KST |
| 작성 trigger | v2 mid-checkpoint(`48a2cb05`) + Phase H plan(`6e5cdf43`) 완료 후 plan coverage 100% 달성. 미션 완료까지의 실행 명령을 단일 문서로 정본화 |
| 적용 범위 | F5 / F1 / Phase H / F3 / F4 / closure 실행 + mid-checkpoint v3 거버넌스 |
| 위치 | `docs/update_log/2026-05-12_v3k_ralph_command_playbook.md` |
| freeze 정책 | 명령 자체는 freeze. 명령이 인용하는 plan이 갱신되면 별도 playbook 신설 |
| 인용 원본 | Phase A plan §K, F1–F7 plans, Phase H plan, mid-checkpoint v1·v2 |

---

## 0. 요지

```text
plan coverage 100% 달성 시점의 ralph 명령어 모음. 각 명령은 plan을 인용하고 사용자 명시 승인을 요구한다.
A(즉시 진입) → B(중간 위험) → C(고위험/대형) → D(closure) → E(거버넌스) 순서로 정리.
모든 명령은 한국어 commit과 보존 원칙(Kiwoom 유지 / LS 제외 / default-OFF / 운영 _database/ 무변경) 강제.
force: prefix는 plan이 이미 정본화되어 ralplan gate를 우회한다는 표시.
```

---

## A. 즉시 진입 가능 명령 (낮은 위험)

### A1. Phase E6 — sidecar tempfile writer prototype (page 025)

대상 plan: `docs/plans/2026-05-12_v3k_page_025_phase_e6_sidecar_tempfile_writer_plan.md`

```powershell
omx ralph "force: V3K Page 025 Phase E6 sidecar tempfile writer prototype을 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_page_025_phase_e6_sidecar_tempfile_writer_plan.md를 기준으로, sidecar persistence를 tempfile write 단계로 끌어올린다. 운영 _database/setting.db는 절대 건드리지 않고 tempfile만 사용하며 schema validator/read-only loader/write guard 산출물을 그대로 활용한다. Kiwoom 주문/청산/live runtime, formula runtime hook, analyzer trading decision, 운영 _database/setting.db, LS Securities 직접 의존은 변경하지 않는다. default-OFF 보존, V3K_PHASE_C/E feature flag 무회귀. 완료 시 py_compile, V3K smoke 전체, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB artifact status를 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록 후 한국어 commit한다."
```

### A2. Phase H H-1 — Kiwoom dry-run hook 모듈 설계 (KHOPENAPI 불필요)

대상 plan: `docs/plans/2026-05-12_v3k_phase_h_live_kiwoom_dryrun_plan.md` §C T01–T03

```powershell
omx ralph "force: V3K Phase H H-1 sub-phase (Kiwoom dry-run hook 모듈 설계)을 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_phase_h_live_kiwoom_dryrun_plan.md §C T01–T03을 기준으로, strategy/v3k_kiwoom_dryrun_hook.py 신설, scripts/smoke_v3k_phase_h_hook_unit.py 신설, scripts/audit_v3k_phase_h_env_check.py 신설을 수행한다. LH1(주문/청산 경로 무변경) + LH2(idempotent) + LH4(KHOPENAPI sentinel)를 코드로 enforce하고 unit smoke가 LH1/LH2 시나리오 PASS 함을 검증한다. KHOPENAPI 호환 환경은 없어도 본 sub-phase는 진행 가능하다. Kiwoom 주문/청산/live runtime, LS Securities 직접 의존은 변경하지 않는다. default-OFF 보존. 완료 시 py_compile, smoke unit, V3K smoke 전체, audit_v3k_verify_1a --base 57496d24, verify_release_sync, git diff --check를 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 H-1 결과를 기록 후 한국어 commit한다."
```

### A3. F5 — Production learning DB read 실행

대상 plan: `docs/plans/2026-05-12_v3k_production_learning_db_read_plan.md` §C T01–T05

```powershell
omx ralph "force: V3K F5 production learning DB read 실행을 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_production_learning_db_read_plan.md §C T01–T05를 기준으로, strategy/v3k_analyzer_adapter.py에 read_production_learning_db method 추가, scripts/smoke_v3k_learning_db_production_read.py / smoke_v3k_learning_db_leakage_guard.py / smoke_v3k_learning_db_fallback.py 3건 신설, CARRY_FORWARD_REGISTRY에 V3K-PROD-READ 섹션 추가한다. ?mode=ro SQLite URI 강제로 운영 _database/는 절대 변경하지 않으며 last_update < backtest_date L6 invariant를 자동검증한다. Kiwoom 주문/청산/live runtime, LS Securities 직접 의존은 변경하지 않는다. default-OFF 보존. 완료 시 py_compile, 3건 smoke 전체, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_release_sync, git diff --check, git status _database/ 빈 출력을 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록 후 한국어 commit한다."
```

---

## B. 중간 위험 명령 (사전 조건 + --deliberate ralplan 권장)

### B1. F1 — DB cutover 사전 ralplan 재합의

대상 plan: `docs/plans/2026-05-12_v3k_db_cutover_plan.md`

```powershell
omx ralplan --deliberate "V3K F1 DB cutover (docs/plans/2026-05-12_v3k_db_cutover_plan.md §C T01–T08)를 실행하기 전에 Planner/Architect/Critic 합의를 재실행한다. LC1(backup-first) / LC2(단일 commit + 사용자 명시 승인) / LC3(7일 모니터링) invariant가 충분한지 pre-mortem 3 시나리오(cutover 도중 power fail / backup 손상 / schema drift)와 expanded test plan(backup checksum unit / cutover dry-run integration / post-cutover health e2e / 7일 monitoring observability)을 추가 검증한다. F5 production read 완료가 precondition임을 명시한다."
```

### B2. F1 — DB cutover script 신설 (T01–T04, cutover 실제 실행 전)

대상 plan: `docs/plans/2026-05-12_v3k_db_cutover_plan.md` §C T01–T04

```powershell
omx ralph "force: V3K F1 DB cutover script 신설을 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_db_cutover_plan.md §C T01–T04를 기준으로, scripts/backup_operational_database.py / cutover_v3k_shadow_to_database.py / smoke_v3k_cutover_dryrun.py / rollback_v3k_cutover.py 4건을 신설하고 .gitignore에 backup 디렉터리 정책을 추가한다. 본 단계는 cutover 실제 실행이 아니라 script 신설과 dry-run 검증만 수행한다. T02 cutover script는 V3K_CUTOVER_USER_ACK 환경 변수 미설정 시 SystemExit하도록 enforce한다. Kiwoom 주문/청산/live runtime, 운영 _database/, LS Securities 직접 의존은 변경하지 않는다. default-OFF 보존. 완료 시 py_compile 4건, smoke_v3k_cutover_dryrun, audit_v3k_verify_1a, verify_release_sync, git diff --check, git status _database/ 빈 출력을 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록 후 한국어 commit한다. **실제 cutover 실행(T05)은 별도 commit cycle에서 사용자 명시 승인 후 진행한다.**"
```

### B3. Phase H H-2 / H-3 — KHOPENAPI 환경에서 dry-run 실행

대상 plan: `docs/plans/2026-05-12_v3k_phase_h_live_kiwoom_dryrun_plan.md` §C T04–T10

```powershell
omx ralph "force: V3K Phase H H-2 + H-3 sub-phase (KHOPENAPI 호환 환경에서 live dry-run + ON 전환)을 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. 사전 조건: H-1 commit 완료 + KHOPENAPI 호환 환경 확보 + V3K_PHASE_H_USER_ACK=1 환경 변수 설정. docs/plans/2026-05-12_v3k_phase_h_live_kiwoom_dryrun_plan.md §C T04–T10을 기준으로, KHOPENAPI 환경 검증 smoke 실행 → live dry-run 1회 실행 → log archive → post-health smoke → 이중 gate + rollback flag 도입 → 사용자 명시 승인 후 ON commit → V3K-PHASE-H-ENABLE registry → 7일 모니터링 audit 신설을 수행한다. LH1(주문/청산 경로 무변경) 자동검증을 강제하고 주문 API 호출이 0건임을 V07로 확인한다. Kiwoom 주문/청산/live runtime 경로 코드는 절대 변경하지 않는다. LS Securities 직접 의존은 변경하지 않는다. 완료 시 py_compile, smoke 전체, audit, verify_release_sync, git diff --check, git diff -- trade/ utility/ Kiwoom* 빈 출력을 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록 후 한국어 commit한다."
```

---

## C. 고위험 / 대형 명령 (--deliberate ralplan 의무)

### C1. F3 — Phase F (analyzer 전략 반영) 사전 --deliberate ralplan

대상 plan: `docs/plans/2026-05-12_v3k_phase_f_analyzer_strategy_plan.md`

```powershell
omx ralplan --deliberate "V3K F3 Phase F analyzer output 전략 반영 (docs/plans/2026-05-12_v3k_phase_f_analyzer_strategy_plan.md)을 실행하기 전에 Planner/Architect/Critic 합의를 재실행한다. LF1(parity 통과 후 ON) / LF2(rollback flag 즉시 OFF) / LF3(손실·MDD·거래횟수 변동 한계) / LF4(V3K-PHASE-F-ENABLE registry) invariant가 충분한지 pre-mortem 3 시나리오(parity 한계 이탈 / rollback flag 미작동 / 24h monitoring 한계 이탈)와 expanded test plan(parity unit / 이중 gate integration / ON 전환 e2e / monitoring observability)을 추가 검증한다. F5 production read 완료가 precondition이며 F1 cutover 완료는 권장. sub-phase F-1/F-2/F-3는 코드/검증 작업이며 F-4는 ON 전환 commit임을 명확히 분리한다."
```

### C2. F3 — Phase F sub-phase F-1/F-2/F-3 (ON 전 사전 작업)

대상 plan: `docs/plans/2026-05-12_v3k_phase_f_analyzer_strategy_plan.md` §C T01–T06

```powershell
omx ralph "force: V3K F3 Phase F sub-phase F-1+F-2+F-3 (analyzer formula adapter + backtest parity baseline + 이중 gate + rollback flag)을 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_phase_f_analyzer_strategy_plan.md §C T01–T06을 기준으로, strategy/v3k_formula_facade.py와 v3k_analyzer_adapter.py에 V3K_ prefix callable 노출 (default-OFF), scripts/smoke_v3k_phase_f_default_off.py 신설, scripts/backtest_v3k_phase_f_parity.py 신설로 1주일 sample period 회귀, .omx/reports/v3k-phase-f-parity-<utc>.json archive, scripts/audit_v3k_phase_f_rollback.py 신설로 V3K_PHASE_F_DISABLE rollback flag 시나리오 검증. 본 단계는 ON 전환(F-4) 전이며 default-OFF가 유지된다. Kiwoom 주문/청산/live runtime, 운영 _database/, LS Securities 직접 의존은 변경하지 않는다. parity 결과 한계 이탈 시 ON 차단. 완료 시 py_compile, smoke 전체, parity report 한계 내 PASS, audit, verify_release_sync, git diff --check를 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록 후 한국어 commit한다. **F-4 ON 전환은 별도 commit cycle에서 사용자 명시 승인 후 진행한다.**"
```

### C3. F4 — Phase G G-1 사전 --deliberate ralplan

대상 plan: `docs/plans/2026-05-12_v3k_phase_g_microstructure_engine_plan.md`

```powershell
omx ralplan --deliberate "V3K F4 Phase G G-1 (V3 microstructure engine 2U_C 이식, docs/plans/2026-05-12_v3k_phase_g_microstructure_engine_plan.md §C T01–T05)을 실행하기 전에 Planner/Architect/Critic 합의를 재실행한다. LG1(LS 의존 자동 제거) / LG2(Kiwoom OPT* data shape mapping 정본화) / LG3(parity ±15%) / LG4(성능 ±20%) / LG5(ON 단일 commit + 사용자 승인) invariant가 충분한지 pre-mortem 3 시나리오(LS 의존 잔존 / Kiwoom data shape mismatch / parity 한계 이탈)와 expanded test plan을 추가 검증한다. V3 engine inventory (T01)와 Kiwoom OPT* mapping 표 (T02)는 G-1의 핵심 산출물임을 명시한다."
```

### C4. F4 — Phase G G-1 (V3 microstructure engine 이식)

```powershell
omx ralph "force: V3K F4 Phase G G-1 sub-phase (V3 microstructure engine 이식 + LS 제거 + Kiwoom mapping)을 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_phase_g_microstructure_engine_plan.md §C T01–T05를 기준으로, V3 branch(STOM_V.wt-3)에서 microstructure 모듈 inventory 작성, Kiwoom OPT* data shape mapping 표 정본화, strategy/v3k_microstructure_engine.py 신설(LS 의존 0건 자동검증), scripts/audit_v3k_phase_g_ls_excise.py 신설, scripts/smoke_v3k_phase_g_engine_unit.py 신설을 수행한다. default-OFF 시 engine 인스턴스화만 가능. Kiwoom 주문/청산/live runtime, 운영 _database/, LS Securities 직접 의존(LG1으로 자동검증)은 변경하지 않는다. 완료 시 py_compile, audit_v3k_phase_g_ls_excise, smoke engine unit, audit_v3k_verify_1a, verify_release_sync, git diff --check, LS marker 0건을 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록 후 한국어 commit한다."
```

### C5. F4 — Phase G G-2 + G-3 (parity benchmark + ON 전환)

대상 plan: `docs/plans/2026-05-12_v3k_phase_g_microstructure_engine_plan.md` §C T06–T12

```powershell
omx ralph "force: V3K F4 Phase G G-2 + G-3 sub-phase (backtest parity baseline + 성능 benchmark + 이중 gate + ON 전환)을 진행한다. 사전 조건: G-1 commit 완료 + V3K_PHASE_G_USER_ACK=1 (G-3 시점). docs/plans/2026-05-12_v3k_phase_g_microstructure_engine_plan.md §C T06–T12를 기준으로, scripts/backtest_v3k_phase_g_parity.py와 benchmark_v3k_phase_g_engine.py 신설로 V3 baseline 대비 parity ±15% / 성능 ±20% 한계 내 통과 검증, parity/benchmark report archive, strategy/v3k_microstructure_engine.py에 이중 gate + V3K_PHASE_G_DISABLE rollback flag 추가, 사용자 명시 승인 후 ON commit, V3K-PHASE-G-ENABLE registry, 24h monitoring report. LG3/LG4 한계 이탈 시 ON 차단. Kiwoom 주문/청산/live runtime, 운영 _database/, LS Securities 직접 의존은 변경하지 않는다. 완료 시 py_compile, parity + benchmark 한계 내 PASS, smoke 전체, audit, verify_release_sync, git diff --check, V3K-PHASE-G-ENABLE 매치 1건을 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록 후 한국어 commit한다."
```

---

## D. Closure 명령 (모든 단계 완료 후)

### D1. closure gate audit script 신설 + 미션 완료 선언

대상 plan: `docs/update_log/2026-05-12_v3k_mission_closeout_procedure.md` §1.1–§3

```powershell
omx ralph "force: V3K closure gate 진입을 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/update_log/2026-05-12_v3k_mission_closeout_procedure.md §1.1–§3을 기준으로, scripts/audit_v3k_closeout_gate.py를 신설하고 audit §6.2 #1~#7 모두 S4 + #8 보존도 100% + L1~L9 모두 무회귀 종합 3-tuple 자동검증을 구현한다. closeout audit이 PASS하면 docs/update_log/<날짜>_v3k_closure_declaration.md를 §3 표준 양식으로 작성하고 CARRY_FORWARD_REGISTRY에 V3K-CLOSURE 섹션을 추가한다. audit 보고서 §11에 'V3K closure 선언일: <날짜>' 한 줄을 예외적으로 추가한다(audit freeze의 명시적 1줄 예외). 사용자 명시 승인 후에만 본 closure declaration commit을 수행한다. 완료 시 audit_v3k_closeout_gate PASS, verify_release_sync, git diff --check, registry 매치 1건을 통과시키고 한국어 closure commit한다."
```

---

## E. 주기적 거버넌스 명령

### E1. mid-checkpoint v3 신설 (F5 또는 F1 완료 시점)

```powershell
omx ralph "force: V3K mid-checkpoint v3 신설을 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. F6 §3.2 명명 규칙(<날짜>_v3k_midpoint_checkpoint_<base>_to_<head>.md)에 따라 docs/update_log/<날짜>_v3k_midpoint_checkpoint_cd6f5bd_to_<현재-head>.md를 신설한다. v1(3da98175) 및 v2(48a2cb05) mid-checkpoint와 보완 관계로 공존시키고, F6 산식 실행 진척률 + plan coverage 메트릭을 재측정한다. audit §6.2 8 항목 vs 현재 단계 매트릭스, Phase letter 매핑(F2 후), 35+ commit 분류 (Phase α/β/γ/δ), 보존 원칙 정량 검증 (검증 시점 HEAD 명시), 남은 작업 우선순위 갱신, 종합 판정 7건을 포함한다. Phase A plan §K.7 freeze, audit freeze, prior mid-checkpoint freeze 모두 보존한다. 완료 시 git diff --check, heading tree, 산식 검산을 통과시키고 한국어 commit한다."
```

---

## F. 추천 진행 순서

| # | 단계 | 명령 | 소요 commit cycle |
| ---: | --- | --- | --- |
| 1 | Phase E6 (sidecar tempfile writer) | A1 | 1 |
| 2 | Phase H H-1 (KHOPENAPI 없이 hook 설계) | A2 | 1 |
| 3 | F5 production read | A3 | 1 |
| 4 | mid-checkpoint v3 (진척률 재측정) | E1 | 1 |
| 5 | F1 cutover script 신설 (사전 ralplan + script) | B1 + B2 | 2 |
| 6 | F1 cutover 실제 실행 | (별도 cycle, 사용자 ack + 7일 모니터링) | 1 |
| 7 | Phase H H-2/H-3 (KHOPENAPI 환경 확보 시) | B3 | 2 |
| 8 | F3 Phase F sub-phase F-1/F-2/F-3 | C1 + C2 | 2 |
| 9 | F3 F-4 ON 전환 (사용자 ack + 24h 모니터링) | (별도 cycle) | 1 |
| 10 | F4 Phase G G-1 (engine 이식) | C3 + C4 | 2 |
| 11 | F4 Phase G G-2 + G-3 (parity + ON) | C5 | 2 |
| 12 | mid-checkpoint v4 (closure 직전) | E1 (재실행) | 1 |
| 13 | closure gate + V3K-CLOSURE 선언 | D1 | 1 |

**총 commit cycle 예상**: 약 18건 (sub-phase 단위)

---

## G. 사용 시 주의 사항

### G.1 명령 prefix 의미

| prefix | 의미 |
| --- | --- |
| `omx ralph "force: ..."` | plan이 이미 정본화되어 있어 ralplan gate 우회. 본 playbook의 모든 ralph 명령에 적용 |
| `omx ralplan --deliberate "..."` | 고위험 phase 사전 합의 재실행. pre-mortem + expanded test plan 추가 |

### G.2 보존 원칙 (모든 명령에 강제)

모든 명령 본문에 다음 6대 원칙이 명시적으로 포함되어야 한다.

1. Kiwoom 주문/청산/live runtime 미변경 (P1, L4)
2. LS Securities 직접 의존 금지 (L7)
3. 운영 `_database/` 미변경 (P1, L4, L8)
4. STOM CLI surface 보존 (L9)
5. feature flag default-OFF (P3, L5)
6. DB 파일 commit 금지 (L8)

### G.3 명령 실행 전 체크리스트

- [ ] 사용자 명시 승인 받았는가? (모든 단계 필수)
- [ ] precondition phase commit 완료됐는가?
- [ ] `--deliberate` ralplan 필요 단계인가? (F1, F3, F4, Phase H H-2 이상)
- [ ] verify_release_sync.py 통과 상태인가?
- [ ] git working tree clean인가?

### G.4 commit 본문 한국어 의무

CLAUDE.md `## Commit Language Rules` 정합. 모든 commit 제목과 본문은 한국어 markdown.

### G.5 검증 명령 표준 set

각 ralph 명령 완료 시 다음을 통과시킨다.

```powershell
python -m py_compile <신규/수정 scripts>
python <신규 smoke scripts>
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/verify_release_sync.py
git diff --check
git status --porcelain -- _database/ _database_v3k_shadow/ *.db
```

---

## H. 본 playbook freeze 정책

- **freeze 시점**: 본 commit
- **변경 trigger**: 다음 중 하나일 때 새 playbook 신설
  - 인용된 plan이 갱신되어 명령 본문 변경 필요
  - 새 phase letter가 도입됨 (F2 letter remapping decision의 후속)
  - 새 거버넌스 명령이 도입됨
- **갱신 금지**: 본 문서 amend로 명령 추가 금지

---

## I. 관련 문서

### plan 문서 (실행 대상)

- `docs/plans/2026-05-10_v3k_phase_a_shadow_db_plan.md` — Phase A plan (실행 완료)
- `docs/plans/2026-05-11_v3k_phase_b_readonly_learning_db_plan.md` — Phase B plan (실행 완료)
- `docs/plans/2026-05-11_v3k_phase_c_activation_boundary_plan.md` — Phase C1 plan
- `docs/plans/2026-05-11_v3k_phase_c2_gui_wrapper_inventory_plan.md` — Phase C2 plan
- `docs/plans/2026-05-12_v3k_page_025_phase_e6_sidecar_tempfile_writer_plan.md` — A1 대상
- `docs/plans/2026-05-12_v3k_production_learning_db_read_plan.md` — A3 (F5) 대상
- `docs/plans/2026-05-12_v3k_db_cutover_plan.md` — B2 (F1) 대상
- `docs/plans/2026-05-12_v3k_phase_f_analyzer_strategy_plan.md` — C2 (F3) 대상
- `docs/plans/2026-05-12_v3k_phase_g_microstructure_engine_plan.md` — C4/C5 (F4) 대상
- `docs/plans/2026-05-12_v3k_phase_h_live_kiwoom_dryrun_plan.md` — A2/B3 (Phase H) 대상

### 거버넌스 문서

- `docs/update_log/2026-05-10_2uc_v3k_full_feature_audit.md` — audit 정본
- `docs/update_log/2026-05-12_v3k_phase_letter_remapping_decision.md` — F2 letter
- `docs/update_log/2026-05-12_v3k_progress_metric_methodology.md` — F6 산식
- `docs/update_log/2026-05-12_v3k_mission_closeout_procedure.md` — F7 closure → D1 명령

### 점검 문서

- `docs/update_log/2026-05-12_v3k_cd6f5bd_to_page024_flow_review.md` — prior flow review
- `docs/update_log/2026-05-12_v3k_midpoint_checkpoint_cd6f5bd_to_e1c4619c.md` — v1 mid-checkpoint
- `docs/update_log/2026-05-12_v3k_midpoint_checkpoint_cd6f5bd_to_067886d3.md` — v2 mid-checkpoint (plan coverage 메트릭 도입)
