# V3K Phase G — Microstructure Engine Replacement 실행 계획 (F4, 대형)

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-12 KST |
| audit §6.2 항목 | #7 V3 microstructure engine replacement |
| 현재 단계 (F6 산식) | S0 (0%) — plan 미작성 |
| 목표 단계 | S4 (100%) operational — V3 microstructure가 2U_C에서 작동 |
| Phase letter | **G** (audit §8 정본 letter G와 의미 일치) |
| 위험도 | **대형** + 고위험 — engine 이식 대형 작업, Kiwoom data shape 적응 |
| 의존 입력 | Phase A–D 완료, F1/F3/F5 완료 권장 |
| **sub-phase 의무 분해** | **G-1/G-2/G-3** (Phase A plan §0.2 명시) |
| **`--deliberate` ralplan 의무** | **YES** — pre-mortem + expanded test plan |

---

## 0. V3K 미션 재인용

```text
V3K = V3 신기능을 2U_C에 모두 반영. LS 제외, Kiwoom 유지, CLI 보존.
audit §6.2 #7: V3 microstructure engine replacement — adapter가 아닌 engine 자체 이식.
```

본 plan은 V3K 미션 7개 달성 항목 중 가장 큰 작업이다. V3 branch의 microstructure 분석 엔진(LS 데이터 의존)을 Kiwoom OPT* 데이터 shape에 맞춰 이식 또는 동등 기능을 재구현한다.

---

## A. Drivers + Scope

### A.1 Drivers

1. V3K 미션 statement의 "V3 신기능을 모두 반영"의 마지막 큰 항목
2. analyzer adapter(Phase D)는 boundary 수준의 read-only contract였고 실제 engine은 없음
3. Phase F(analyzer 전략 반영)와 결합 시 V3K 미션 핵심 가치 완성

### A.2 Scope

| In scope | Out of scope |
| --- | --- |
| V3 microstructure 모듈 이식 또는 동등 재구현 | LS Securities REST/TR/REAL 직접 의존 (L7 영구 금지) |
| Kiwoom OPT* 데이터 shape 적응 mapping | V3 branch와 binary identical 이식 (현실적 불가) |
| 성능/메모리 benchmark vs V3 baseline | Phase F analyzer 전략 반영 (F3 별도) |
| backtest parity (V3 baseline vs 2U_C engine) | Phase H live Kiwoom dry-run (별도 phase) |
| default-OFF + rollback flag (Phase F 패턴 재사용) | feature flag ON 전환 (사용자 명시 승인 후) |

---

## B. Phase-specific invariants

### B.1 보존 (L1–L9)

모두 보존. 특히:
- **L7**: V3 코드의 LS 의존 부분은 이식 시 제거 또는 Kiwoom mapping으로 대체
- **L9**: STOM CLI surface 보존 — engine은 strategy formula 또는 별도 module로 노출되지 외부 CLI 시그니처 변경 없음

### B.2 신규 Phase G 전용 invariants (LG1–LG5)

| # | invariant | 사유 |
| --- | --- | --- |
| LG1 | V3 microstructure engine 이식 시 LS 직접 의존 자동 제거 (audit guard) | L7 보존 자동화 |
| LG2 | Kiwoom OPT* data shape mapping 표는 별도 문서로 정본화 | data shape drift 차단 |
| LG3 | backtest parity (V3 baseline vs 2U_C engine) 한계 정의 사전 명시 | Phase F LF3 패턴 재사용 |
| LG4 | 성능/메모리 benchmark는 V3 대비 ±20% 범위 내 (P5 운영 가용성) | 성능 회귀 차단 |
| LG5 | engine ON 전환 commit은 단일 commit + 사용자 명시 승인 (Phase F LF2 패턴) | 가시성 보장 |

---

## C. 상세 실행 계획 — sub-phase 분해 (G-1/G-2/G-3)

Phase A plan §0.2는 Phase G의 G-1/G-2/G-3 분해 권장을 명시했다. 각 sub-phase는 별도 ralplan을 요구하지 않지만 commit 단위는 분리한다.

### sub-phase G-1: V3 engine 이식 + Kiwoom data shape mapping

| 목표 | engine 코드를 2U_C로 이식, LS 의존 제거, Kiwoom mapping |
| --- | --- |
| 위험 수준 | 중간 (read-only 단계, 매매 영향 없음) |
| commit 예상 | 4–6건 |

### sub-phase G-2: backtest parity + 성능 benchmark

| 목표 | V3 baseline vs 2U_C engine의 parity 한계 검증, 성능/메모리 benchmark |
| --- | --- |
| 위험 수준 | 중간 |
| commit 예상 | 3–4건 |

### sub-phase G-3: engine ON 전환 + 사용자 명시 승인

| 목표 | feature flag ON + Phase F LF2 패턴 rollback flag + registry 등록 |
| --- | --- |
| 위험 수준 | **치명** |
| commit 예상 | 2–3건 |

### C.0 task별 실행/commit lane (G-1)

| Task | sub-phase | 변경 대상 |
| --- | --- | --- |
| T01 (V3 engine inventory) | G-1 | docs/plans/v3k_phase_g_inventory.md (신규) |
| T02 (Kiwoom data shape mapping 표) | G-1 | docs/update_log/v3k_kiwoom_opt_data_shape_mapping.md (신규) |
| T03 (engine 이식 — LS 의존 제거) | G-1 | strategy/v3k_microstructure_engine.py (신규) |
| T04 (이식 audit guard) | G-1 | scripts/audit_v3k_phase_g_ls_excise.py (신규) |
| T05 (이식 후 unit smoke) | G-1 | scripts/smoke_v3k_phase_g_engine_unit.py (신규) |

### C.0 task별 실행/commit lane (G-2)

| Task | sub-phase | 변경 대상 |
| --- | --- | --- |
| T06 (parity baseline script) | G-2 | scripts/backtest_v3k_phase_g_parity.py (신규) |
| T07 (성능 benchmark script) | G-2 | scripts/benchmark_v3k_phase_g_engine.py (신규) |
| T08 (parity + benchmark report archive) | G-2 | .omx/reports/v3k-phase-g-parity-<utc>.json + benchmark report |

### C.0 task별 실행/commit lane (G-3)

| Task | sub-phase | 변경 대상 |
| --- | --- | --- |
| T09 (feature flag 이중 gate + rollback flag) | G-3 | strategy/v3k_microstructure_engine.py (수정) |
| T10 (사용자 명시 승인 dance) | G-3 | n/a |
| T11 (ON commit + V3K-PHASE-G-ENABLE registry) | G-3 | docs/CARRY_FORWARD_REGISTRY.md + .omx/reports/ |
| T12 (24h monitoring) | G-3 | .omx/reports/v3k-phase-g-monitor-<utc>.json |

---

### T01 — V3 engine inventory

- 목표: V3 branch에서 microstructure 관련 모듈 목록 작성 (파일 경로 + LOC + LS 의존 표시)
- 변경 파일: `docs/plans/v3k_phase_g_inventory.md` (신규)
- 변경 의도:
  - V3 branch (`STOM_Version_3`) 또는 `STOM_V.wt-3`에서 microstructure 모듈 식별
  - 각 모듈의 LS 의존도(import 그래프)·LOC·테스트 커버리지 표
- 완료 조건: inventory 표가 V3 microstructure 모듈 최소 5개 이상 식별
- 선행: 없음

### T02 — Kiwoom data shape mapping 표 정본화 (LG2)

- 목표: V3 데이터 shape ↔ Kiwoom OPT* shape mapping 표 정본화
- 변경 파일: `docs/update_log/2026-05-12_v3k_kiwoom_opt_data_shape_mapping.md` (신규)
- 변경 의도:
  - 가격/체결가/거래량/시가/고가/저가/현재가 등 field-level mapping
  - tick vs minute 분해의 차이
  - mapping이 모호한 case에 대한 fallback 결정 (예: V3에는 있지만 Kiwoom 미제공 field)
  - mapping은 LG2 lifetime invariant로 freeze
- 완료 조건: 표가 V3 microstructure field 100% 커버
- 선행: T01

### T03 — engine 이식 (LS 의존 제거)

- 목표: V3 microstructure engine을 2U_C로 이식, 모든 LS 직접 의존 제거 또는 Kiwoom mapping으로 대체
- 변경 파일: `strategy/v3k_microstructure_engine.py` (신규)
- 변경 의도:
  - V3 코드를 시작점으로 LS 의존 import를 모두 제거
  - T02 mapping에 따라 Kiwoom OPT* 데이터로 input port 재구성
  - default-OFF: 이식 단계에서는 engine 인스턴스화만 가능, 실제 호출 없음
- 완료 조건:
  ```powershell
  python -m py_compile strategy/v3k_microstructure_engine.py
  Select-String -Path strategy/v3k_microstructure_engine.py -Pattern "ls_securities|LS_REST|xingapi|restapi_ls"
  ```
  PASS: 첫 명령 exit 0, 두 번째 매치 0건
- 선행: T01, T02

### T04 — 이식 audit guard (LG1)

- 목표: LS 의존 자동 제거 검증
- 변경 파일: `scripts/audit_v3k_phase_g_ls_excise.py` (신규)
- 변경 의도: `strategy/v3k_microstructure_engine.py` + 의존 모듈에서 LS marker 0건 자동 검증. CI/pre-commit hook 등록 가능
- 완료 조건:
  ```powershell
  python scripts/audit_v3k_phase_g_ls_excise.py
  ```
  PASS: exit 0 + "LS excise audit passed"
- 선행: T03

### T05 — 이식 후 unit smoke

- 목표: 이식된 engine의 unit-level 동작 검증 (default-OFF 시 인스턴스화 + smoke read 가능)
- 변경 파일: `scripts/smoke_v3k_phase_g_engine_unit.py` (신규)
- 완료 조건: engine 인스턴스화 + sample read 가능
- 선행: T03, T04

### T06 — parity baseline script (LG3)

- 목표: V3 baseline vs 2U_C engine의 backtest parity 검증
- 변경 파일: `scripts/backtest_v3k_phase_g_parity.py` (신규)
- 변경 의도:
  - 동일 종목·기간(1주일+)에 대해 (a) V3 branch에서 microstructure 결과 (b) 2U_C engine에서 microstructure 결과 산출
  - 결과 비교: 핵심 indicator (pattern_score, volume_spike_level, volatility_level)
  - parity 한계: ±15% 범위 (LG3 default, 운영 baseline에 따라 보정 가능)
- 완료 조건: 한계 내 PASS
- 선행: T05

### T07 — 성능 benchmark (LG4)

- 목표: 메모리 사용량·실행 시간 V3 baseline 대비 ±20% 검증
- 변경 파일: `scripts/benchmark_v3k_phase_g_engine.py` (신규)
- 변경 의도: `time.perf_counter` + `tracemalloc`으로 동일 input에 대한 실행 시간/메모리 비교
- 완료 조건: 한계 내 PASS
- 선행: T05

### T08 — parity + benchmark report archive

- 목표: 결과를 audit trail로 commit
- 변경 파일: `.omx/reports/v3k-phase-g-parity-<utc>.json`, `.omx/reports/v3k-phase-g-benchmark-<utc>.json` (신규, commit)
- 완료 조건: report 파일 생성
- 선행: T06, T07

### T09 — feature flag 이중 gate + rollback flag (Phase F 패턴 재사용)

- 목표: ON 시점 차단 안전망
- 변경 파일: `strategy/v3k_microstructure_engine.py` (수정)
- 변경 의도: `V3K_PHASE_G_ENABLE` 환경 변수 + `phase_g_microstructure.enabled` DB row 이중 gate, `V3K_PHASE_G_DISABLE=1` rollback flag
- 완료 조건: gate 시뮬레이션 PASS, rollback flag 시뮬레이션 PASS
- 선행: T08

### T10 — 사용자 명시 승인 dance

- form: F7 §2 Gate 2 유사
- 완료 조건: 사용자 명시 "승인" 응답
- 선행: T09

### T11 — ON commit + V3K-PHASE-G-ENABLE registry

- 사전 조건: T10 사용자 명시 승인 + `V3K_PHASE_G_USER_ACK=1`
- 변경 파일: `docs/CARRY_FORWARD_REGISTRY.md` (수정), `.omx/reports/v3k-phase-g-enable-<utc>.json` (신규)
- 완료 조건: registry 매치 + audit report 통과
- 선행: T10

### T12 — 24h monitoring

- 변경 파일: `.omx/reports/v3k-phase-g-monitor-<utc>.json` (24h 후 commit)
- 변경 의도: ON 후 24h 동안 backtest parity 재검증 + 성능 모니터링
- 완료 조건: 한계 내 유지
- 선행: T11

---

## D. 검증 단계 V01–V15

| # | 명령 | lane | PASS |
| --- | --- | --- | --- |
| V01 | T01 inventory 표 작성 | 양쪽 | 최소 5개 모듈 식별 |
| V02 | T02 mapping 표 검증 | 양쪽 | V3 field 100% 커버 |
| V03 | `python -m py_compile strategy/v3k_microstructure_engine.py` | 양쪽 | exit 0 |
| V04 | `python scripts/audit_v3k_phase_g_ls_excise.py` | 양쪽 | LS marker 0건 |
| V05 | `python scripts/smoke_v3k_phase_g_engine_unit.py` | 2U_C | engine 인스턴스화 PASS |
| V06 | `python scripts/backtest_v3k_phase_g_parity.py --sample-period 7d` | 2U_C | 한계 내 |
| V07 | `python scripts/benchmark_v3k_phase_g_engine.py` | 2U_C | ±20% 한계 내 |
| V08 | parity/benchmark report 생성 확인 | 양쪽 | 두 파일 존재 |
| V09 | feature flag 이중 gate 시뮬레이션 | 2U_C | env+DB 동시 충족 시에만 ON |
| V10 | rollback flag 시뮬레이션 | 2U_C | DISABLE 시 즉시 OFF |
| V11 | T10 사용자 명시 승인 응답 기록 | n/a | "승인" 응답 |
| V12 | T11 ON commit 후 registry | 양쪽 | V3K-PHASE-G-ENABLE 매치 |
| V13 | T12 24h monitoring | 2U_C | 한계 내 유지 |
| V14 | Kiwoom runtime diff + CLI surface 검증 | 양쪽 | 모두 0건 |
| V15 | `python scripts/verify_release_sync.py` | 양쪽 | preflight passed |

---

## E. 위험 매트릭스

| ID | 위험 | 영향도 | 발생가능성 | (Trigger, 자동탐지, 차단액션) |
| --- | --- | --- | --- | --- |
| R1 | LS 의존 잔존 (L7·LG1 위반) | 치명 | 중간 | (T04 audit grep 매치, exit 1, T03 재이식) |
| R2 | Kiwoom data shape mismatch | 높음 | 중간 | (T02 mapping 누락, T06 parity FAIL, T02 보정) |
| R3 | parity 한계 이탈 (LG3) | 치명 | 중간 | (T06 한계 초과, exit 1 + ON 차단) |
| R4 | 성능 회귀 (LG4) | 높음 | 중간 | (T07 benchmark ±20% 초과, exit 1) |
| R5 | engine 메모리 누수 | 높음 | 낮음 | (tracemalloc 결과 비정상, T07 FAIL) |
| R6 | 24h monitoring 한계 이탈 | 치명 | 중간 | (T12 monitor FAIL, rollback flag 즉시 적용) |
| R7 | feature flag 단일 gate | 높음 | 낮음 | (T09 단일 gate 적용, V09 FAIL) |
| R8 | Kiwoom runtime 영향 (P1) | 치명 | 매우 낮음 | (trade/ 변경, V14 reject) |
| R9 | CLI surface 변경 (L9) | 높음 | 낮음 | (init/backtest CLI 시그니처 변경, audit reject) |
| R10 | DB 파일 commit (L8) | 높음 | 낮음 | (`*.db` git status, .gitignore guard) |
| R11 | 사용자 승인 없이 ON | 치명 | 낮음 | (V3K_PHASE_G_USER_ACK 미설정, T11 reject) |

---

## F. Rollback

### F.1 즉시 rollback

```powershell
$env:V3K_PHASE_G_DISABLE = "1"
# strategy/runtime 재시작 → engine OFF
python scripts/audit_v3k_phase_g_ls_excise.py  # LS 의존 0건 재확인
```

### F.2 DB row OFF

```powershell
# phase_g_microstructure.enabled = 0 UPDATE (사용자 명시 승인 + V3K_PHASE_G_USER_ACK=1)
```

### F.3 ON commit revert + 이식 revert (최후 수단)

```powershell
git -C C:/System_Trading/STOM/STOM_V.wt-dev revert <on-commit> --no-edit
# G-1 이식 commit도 revert 가능. parity/benchmark는 archive로 보존
```

---

## G. 산출물

### G.1 Commit 포함 (~14건, sub-phase별 분리)

| sub-phase | commit 예상 |
| --- | --- |
| G-1 | inventory + mapping + engine + audit guard + unit smoke = 5건 |
| G-2 | parity + benchmark + 2 report archive = 4건 |
| G-3 | gate + rollback audit + ON commit + registry + 24h monitor = 5건 |

### G.2 Ephemeral 또는 commit 금지

- live runtime log
- `_database/` DB row 변경 (L8)

---

## H. Commit message 한국어 sample

### H.1 G-1 — engine 이식 + LS 제거

```text
V3K Phase G microstructure engine을 2U_C로 이식한다 (G-1)

- V3 microstructure engine을 strategy/v3k_microstructure_engine.py로 이식한다.
- LS 직접 의존 import를 모두 제거하고 Kiwoom OPT* 데이터 shape에 적응한다.
- LS excise audit guard가 LS marker 0건을 자동검증한다.
```

### H.2 G-2 — parity + benchmark

```text
V3K Phase G engine의 parity와 성능 benchmark를 검증한다 (G-2)

- V3 baseline vs 2U_C engine의 backtest parity를 한계 ±15% 내에서 확인한다.
- 메모리/실행시간 성능이 V3 대비 ±20% 한계 내임을 검증한다.
- parity와 benchmark report를 audit trail로 commit한다.
```

### H.3 G-3 — ON 전환

```text
V3K Phase G microstructure engine을 ON으로 전환한다 (G-3)

- 사용자 명시 승인(V3K_PHASE_G_USER_ACK=1)과 parity/benchmark 통과를 commit 시점에 기록한다.
- registry V3K-PHASE-G-ENABLE 섹션을 추가한다.
- 24시간 monitoring을 시작하며 한계 이탈 시 rollback flag 즉시 적용한다.
```

---

## I. ADR 요지

- **Decision**: Phase G는 G-1(이식)/G-2(parity+benchmark)/G-3(ON 전환) 3 sub-phase로 분해. Phase F LF1–LF4 패턴 재사용 + LG1–LG5 신규 invariant
- **Drivers**: audit §6.2 #7 종착, V3K 미션의 마지막 큰 항목, Kiwoom 유지 조건 하의 V3 분석 능력 실현
- **Alternatives considered**:
  - 단일 phase (분해 없음) → 대형 작업이라 위험 분산 부족, 기각
  - adapter 수준 유지 (engine 이식 없음) → audit §6.2 #7이 종착 못함, 기각
  - 완전 재구현 (V3 코드 미참조) → V3 검증 baseline 없음, 기각
- **Why chosen**: G-1/G-2/G-3 분해가 각 단계의 위험을 isolation하면서도 V3 baseline parity로 정량 검증 가능
- **Consequences**:
  - 긍정: F6 #7 항목 S4 도달, V3K 미션 마지막 큰 항목 완료
  - 부정: 작업량 대형. parity/benchmark가 한계 이탈 시 mapping/이식 반복 필요
- **Follow-ups**:
  - Phase F + G 모두 ON 후 결합 효과(microstructure → analyzer → strategy) 통합 smoke
  - V3 branch 향후 update에 따른 mapping 표 갱신 의무

---

## J. 핵심 설계 질문

### Q1. V3 branch의 microstructure 모듈이 어디에 있나?
A. T01 inventory 단계에서 파악. `STOM_Version_3` 또는 `STOM_V.wt-3`의 strategy/analyzer 디렉터리.

### Q2. Kiwoom data shape mismatch가 너무 크면?
A. T02 mapping이 fallback 결정을 명시. V3에는 있지만 Kiwoom 미제공 field는 (a) 동등 indicator로 대체 또는 (b) Phase G에서 제외하고 별도 phase로 분리.

### Q3. parity ±15%, 성능 ±20% 한계는 왜?
A. LG3·LG4 default. 운영 baseline 측정 결과에 따라 보정. 단, ON 전환 전 한계 명시는 필수.

### Q4. G-1/G-2/G-3가 각각 별도 ralplan 필요?
A. 본 plan이 single ralplan(--deliberate)으로 합의되므로 sub-phase 추가 ralplan 불필요. G-3(ON 전환)는 사용자 명시 승인 자체가 합의 수준의 gate.

### Q5. Phase F와 Phase G의 순서?
A. 의존 입력 면에서 Phase F가 먼저 권장(Phase F는 read-only adapter 결과로 형성된 contract를 사용하고 Phase G는 engine 자체를 이식). 단, 본 plan은 Phase F 완료를 강제하지 않는다. Phase F·G 둘 다 ON 시 결합 효과는 별도 통합 smoke 필요(follow-up).

---

## K. 다음 단계 전환 지침

### K.1 완료 조건

- T01–T12 모두 commit (T10은 사용자 명시 승인 응답)
- V01–V15 모두 PASS
- F6 산식 #7 항목 S0 → S4 전이 확인
- 24h monitoring 한계 내 유지

### K.2 본 phase 완료 후 진행 가능한 작업

- **closure gate (F7)**: §1.1 #7 종착 조건 PASS
- **Phase H (live Kiwoom dry-run)**: 별도 plan
- **Phase F + G 결합 효과 통합 smoke**: follow-up

### K.3 본 plan freeze 정책

Phase G G-3 ON commit 후 본 plan freeze.

### K.4 `--deliberate` ralplan 의무

본 plan 실행 전 `--deliberate` ralplan 재합의 필수. pre-mortem 3 시나리오 + expanded test plan(unit/integration/e2e/observability) 보강 권장.

---

## L. 관련 문서

- `docs/plans/2026-05-10_v3k_phase_a_shadow_db_plan.md` (Phase A plan, §0.2에 G-1/G-2/G-3 분해 권고)
- `docs/plans/2026-05-12_v3k_phase_f_analyzer_strategy_plan.md` (F3, LF 패턴 재사용)
- `docs/plans/2026-05-12_v3k_db_cutover_plan.md` (F1, 권장 precondition)
- `docs/plans/2026-05-12_v3k_production_learning_db_read_plan.md` (F5, precondition)
- `docs/update_log/2026-05-12_v3k_phase_letter_remapping_decision.md` (F2)
- `docs/update_log/2026-05-12_v3k_progress_metric_methodology.md` (F6)
- `docs/update_log/2026-05-12_v3k_mission_closeout_procedure.md` (F7)
- `docs/update_log/2026-05-10_2uc_v3k_full_feature_audit.md` (§6.2 #7)
