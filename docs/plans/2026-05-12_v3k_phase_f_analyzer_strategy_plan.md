# V3K Phase F — Analyzer Output 전략 반영 실행 계획 (F3, 고위험)

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-12 KST |
| audit §6.2 항목 | #6 analyzer output을 전략식/주문/청산 판단에 사용 |
| 현재 단계 (F6 산식) | S0 (0%) — plan 미작성 |
| 목표 단계 | S4 (100%) operational — analyzer output이 매매 판단에 통합 |
| Phase letter | **F** (audit §8 정본 letter F와 의미 일치) |
| 위험도 | **고위험** — 실제 매매 판단 변경, backtest 회귀 + rollback flag 필수 |
| 의존 입력 | Phase A·B·D 완료, F5 production read 완료, F1 cutover 권장 |
| **`--deliberate` ralplan 의무** | **YES** (CLAUDE.md `## High-risk Phase` 정합) |

---

## 0. V3K 미션 재인용

```text
V3K = V3 신기능을 2U_C에 모두 반영. LS 제외, Kiwoom 유지, CLI 보존.
feature flag는 모든 phase에서 default-OFF로 유지하고, 명시적 사용자 승인 후에만 ON 전환을 허용한다.
```

Phase F는 가장 위험한 phase다. analyzer output이 실제 매매 판단에 통합되면 수익률·손실·MDD가 직접 변동한다. default-OFF + rollback flag + backtest parity 3중 안전망이 필수다.

---

## A. Drivers + Scope

### A.1 Drivers

1. audit §6.2 #6 종착 조건은 analyzer output이 strategy/order/exit 판단에 영향
2. Phase D(formula dry-run)와 Phase A·B 산출물이 입력 baseline
3. Phase F 통과 시 V3K 미션의 핵심 가치(V3 분석 능력을 Kiwoom runtime에서 활용)가 실현

### A.2 Scope

| In scope | Out of scope |
| --- | --- |
| analyzer output을 strategy formula에 노출 (`V3K_` prefix) | Kiwoom runtime/order/receiver 코드 변경 (P1·L9 보존) |
| backtest 회귀 (parity baseline vs analyzer-enabled) | LS Securities 직접 의존 (L7 영구 금지) |
| feature flag 이중 gate (env + DB row) | live order/exit 직접 변경 (별도 phase 필요 시 분리) |
| rollback flag (`V3K_PHASE_F_DISABLE=1` 우회) | microstructure engine 이식 (F4 별도) |
| 손실/거래횟수/MDD 기준 검증 | DB cutover (F1 별도) |
| 충분한 sample period backtest | production learning DB read (F5에서 완료) |

---

## B. Phase-specific invariants

### B.1 보존 (L1–L9)

모두 보존. 특히:
- **L2**: `init_v3k_shadow_db.py` 외부 동작 보존
- **L5**: default-OFF (analyzer output 활용은 명시적 ON 후에만)
- **L7**: LS 직접 의존 금지
- **L9**: STOM CLI surface 보존

### B.2 신규 Phase F 전용 invariants (LF1–LF4)

| # | invariant | 사유 |
| --- | --- | --- |
| LF1 | analyzer output 사용은 ON 시점에 backtest parity (1주일 sample) 통과 후에만 허용 | 회귀 차단 |
| LF2 | rollback flag(`V3K_PHASE_F_DISABLE=1`)는 환경 변수 한 줄로 즉시 disable | 운영 즉시 차단 가능성 |
| LF3 | analyzer-enabled vs analyzer-disabled backtest 결과의 손실·MDD·거래횟수 변동 한계 사전 정의 | 수치 임계 자동 검증 |
| LF4 | Phase F ON 시점에 V3K-PHASE-F-ENABLE registry 행 추가 (commit sha + 사용자 ack timestamp) | 가시성 보장 |

---

## C. 상세 실행 계획 (T01–T10, sub-phase 분해)

### C.0 sub-phase 분해

Phase F는 다음 4 sub-phase로 분해한다.

| sub-phase | 목표 | 위험 수준 |
| --- | --- | --- |
| F-1 | analyzer output을 `V3K_` prefix formula로 노출 (read-only adapter, default-OFF) | 중간 |
| F-2 | backtest parity baseline 산출 (analyzer-disabled vs enabled, sample 1주일+) | 중간 |
| F-3 | feature flag 이중 gate + rollback flag 도입 | 중간 |
| F-4 | 사용자 명시 승인 후 단일 commit으로 ON 전환 + V3K-PHASE-F-ENABLE registry | 치명 |

### C.1 task별 실행/commit lane

| Task | sub-phase | lane | commit lane |
| --- | --- | --- | --- |
| T01 (analyzer output formula 노출 adapter) | F-1 | 2U_C | 2U_C |
| T02 (default-OFF smoke + invariant 보존 회귀) | F-1 | 양쪽 | 2U_C |
| T03 (backtest parity baseline script) | F-2 | 양쪽 | 2U_C |
| T04 (parity 회귀 결과 archive) | F-2 | 2U_C | 2U_C |
| T05 (feature flag 이중 gate 도입) | F-3 | 2U_C | 2U_C |
| T06 (rollback flag 도입 + audit guard) | F-3 | 양쪽 | 2U_C |
| T07 (사용자 명시 승인 dance) | F-4 | n/a | n/a |
| T08 (Phase F ON commit) | F-4 | 2U_C, ack 후 | 2U_C |
| T09 (V3K-PHASE-F-ENABLE registry) | F-4 | 2U_C | 2U_C |
| T10 (24시간 backtest 모니터링 + 결과 commit) | F-4 | 2U_C | 2U_C |

### T01 — analyzer output formula adapter

- 목표: V3KAnalyzerAdapter의 output을 `V3K_` prefix callable로 strategy formula namespace에 노출 (default-OFF)
- 변경 파일:
  - `strategy/v3k_formula_facade.py` (수정 — analyzer output 노출 hook)
  - `strategy/v3k_analyzer_adapter.py` (수정 — formula-facing accessor)
- 변경 의도:
  - `V3K_pattern_score(code, market)`, `V3K_volume_spike_level(code, is_tick, market)` 등 `V3K_` prefix callable 노출
  - default-OFF 시 모든 callable이 0 또는 None 반환 (no-op)
  - ON 시 production learning DB(F5)에서 read-only로 조회
- 완료 조건:
  ```powershell
  python -m py_compile strategy/v3k_formula_facade.py strategy/v3k_analyzer_adapter.py
  python -c "from strategy.v3k_formula_facade import V3KFormulaFacade; f=V3KFormulaFacade(); assert f.V3K_pattern_score('TEST', 'KOSPI') == 0  # default-OFF"
  ```
  PASS: 둘 다 exit 0
- 선행: F5 완료

### T02 — default-OFF smoke + 회귀

- 변경 파일: `scripts/smoke_v3k_phase_f_default_off.py` (신규)
- 변경 의도: ON 전환 없이 T01 facade 호출 시 모든 callable이 0/None 반환 + 기존 strategy 결과 무회귀 확인
- 완료 조건:
  ```powershell
  python scripts/smoke_v3k_phase_f_default_off.py
  ```
  PASS: exit 0 + 모든 callable 0/None
- 선행: T01

### T03 — backtest parity baseline script

- 변경 파일: `scripts/backtest_v3k_phase_f_parity.py` (신규)
- 변경 의도:
  - 동일 sample period(1주일 권장, 최소 5 거래일)에 대해 (a) analyzer-disabled (b) analyzer-enabled 두 모드로 backtest 실행
  - 결과 비교: 수익률, 손실, MDD, 거래횟수, 체결률
  - parity report: `.omx/reports/v3k-phase-f-parity-<utc>.json`
  - 한계 정의 (LF3): 손실 변동 < ±5%, MDD 변동 < ±3%, 거래횟수 변동 < ±10%
- 완료 조건:
  ```powershell
  python scripts/backtest_v3k_phase_f_parity.py --sample-period 7d
  ```
  PASS: exit 0 + 한계 내 변동
- 선행: T02

### T04 — parity 결과 archive

- 변경 파일: `.omx/reports/v3k-phase-f-parity-<utc>.json` (신규, commit)
- 변경 의도: T03 결과를 git에 archive. closure gate에서 인용
- 완료 조건: `Test-Path .omx/reports/v3k-phase-f-parity-*.json` True
- 선행: T03

### T05 — feature flag 이중 gate

- 변경 파일:
  - `strategy/v3k_formula_facade.py` (수정)
- 변경 의도:
  - gate1: 환경 변수 `V3K_PHASE_F_ENABLE=1` (commit이 아닌 runtime 활성화)
  - gate2: `v3k_meta.db.v3k_feature_flags`의 row `phase_f_analyzer_strategy.enabled=1` (DB 활성화)
  - **gate1 AND gate2** 모두 충족 시에만 ON. 둘 중 하나가 빠지면 default-OFF
- 완료 조건:
  ```powershell
  python -c "from strategy.v3k_formula_facade import V3KFormulaFacade; ... # env + DB 두 조건 검증"
  ```
  PASS: 두 조건 모두 만족 시에만 ON
- 선행: T04

### T06 — rollback flag + audit guard

- 변경 파일:
  - `strategy/v3k_formula_facade.py` (수정)
  - `scripts/audit_v3k_phase_f_rollback.py` (신규)
- 변경 의도:
  - rollback flag: `V3K_PHASE_F_DISABLE=1` 환경 변수 → 즉시 OFF (gate1·gate2와 무관하게 우선)
  - audit guard: T08 commit에 rollback flag 시나리오 검증 결과 포함
- 완료 조건:
  ```powershell
  python scripts/audit_v3k_phase_f_rollback.py
  ```
  PASS: rollback flag 시나리오 모두 OFF 확인
- 선행: T05

### T07 — 사용자 명시 승인 dance

- 작업자가 사용자에게 form으로 승인 요청 (F7 §2 Gate 2 유사):
  ```text
  V3K Phase F (analyzer output 전략 반영) ON 전환 승인을 요청합니다.
  
  - T01–T06 모두 commit + PASS
  - parity 결과: 손실 변동 X%, MDD 변동 Y%, 거래횟수 변동 Z% (모두 한계 내)
  - rollback flag 시나리오 검증: PASS
  - 환경: STOM_V.wt-dev (STOM_Version_2U_C)
  
  ON 시점부터 analyzer output이 전략 판단에 영향을 줍니다.
  Rollback flag (V3K_PHASE_F_DISABLE=1)로 즉시 OFF 가능합니다.
  승인하시겠습니까?
  ```
- 완료 조건: 사용자 명시 "승인" 응답
- 선행: T01–T06

### T08 — Phase F ON commit

- 변경 파일:
  - `_database/v3k_meta.db` (cutover 후 DB) 또는 sidecar — `phase_f_analyzer_strategy.enabled=1` row INSERT
  - **commit 대상**: registry, 산출 report만 (DB는 L8로 commit 금지)
- 사전 조건: T07 사용자 명시 승인 + F1 cutover 완료 또는 sidecar 경로 결정
- 실행 절차:
  1. 환경 변수 `V3K_PHASE_F_USER_ACK=1` 설정
  2. feature flag DB row INSERT (production DB 또는 sidecar)
  3. ON 시점 audit report 생성 (`.omx/reports/v3k-phase-f-enable-<utc>.json`)
- 완료 조건: ON 시점 audit report 통과
- 선행: T07

### T09 — V3K-PHASE-F-ENABLE registry

- 변경 파일: `docs/CARRY_FORWARD_REGISTRY.md` (수정)
- 변경 의도: `## V3K-PHASE-F-ENABLE` 섹션 추가 (LF4 enforce) — commit sha + 사용자 ack timestamp + 한계 수치
- 완료 조건: `Select-String -Pattern "^## V3K-PHASE-F-ENABLE"` 매치 1건
- 선행: T08

### T10 — 24시간 backtest 모니터링

- 변경 파일: `.omx/reports/v3k-phase-f-monitor-<utc>.json` (신규, 24시간 후 commit)
- 변경 의도: ON 후 24시간 동안 backtest를 주기적으로 재실행. parity 한계 이탈 발견 시 즉시 rollback flag 적용
- 완료 조건: 24시간 monitoring 완료 + 한계 내 유지
- 선행: T08

---

## D. 검증 단계 V01–V12

| # | 명령 | lane | PASS |
| --- | --- | --- | --- |
| V01 | py_compile 3 scripts | 양쪽 | exit 0 |
| V02 | `python scripts/smoke_v3k_phase_f_default_off.py` | 양쪽 | exit 0 |
| V03 | `python scripts/backtest_v3k_phase_f_parity.py --sample-period 7d` | 2U_C | exit 0 + 한계 내 변동 |
| V04 | parity report `.omx/reports/v3k-phase-f-parity-*.json` 검증 | 양쪽 | report 파일 존재 + 한계 수치 명시 |
| V05 | `python scripts/audit_v3k_phase_f_rollback.py` | 양쪽 | rollback 시나리오 PASS |
| V06 | feature flag 이중 gate 시뮬레이션 (env+DB 두 조합) | 2U_C | gate1+gate2 모두 충족 시에만 ON |
| V07 | T07 사용자 명시 승인 응답 기록 | n/a | "승인" 응답 |
| V08 | T08 ON commit 후 V3K_PHASE_F_DISABLE=1 적용 시 즉시 OFF 확인 | 2U_C | OFF 작동 |
| V09 | `Select-String docs/CARRY_FORWARD_REGISTRY.md -Pattern "^## V3K-PHASE-F-ENABLE"` | 양쪽 | 매치 1건 |
| V10 | 24시간 monitoring report 검증 | 2U_C | 한계 내 유지 |
| V11 | LS marker grep + Kiwoom runtime diff | 양쪽 | 모두 0건 |
| V12 | `python scripts/verify_release_sync.py` | 양쪽 | preflight passed |

---

## E. 위험 매트릭스

| ID | 위험 | 영향도 | 발생가능성 | (Trigger, 자동탐지, 차단액션) |
| --- | --- | --- | --- | --- |
| R1 | analyzer output이 손실 증가시킴 (LF3 위반) | **치명** | 중간 | (T03 parity 한계 이탈, exit 1 + ON 차단, rollback flag 활성화) |
| R2 | rollback flag 미작동 | **치명** | 낮음 | (T06 audit smoke FAIL, T08 commit 차단) |
| R3 | feature flag 단일 gate (env only or DB only) | 높음 | 낮음 | (T05 이중 gate 미적용, V06 시뮬 FAIL, T08 차단) |
| R4 | 24시간 모니터링 중 한계 이탈 | 치명 | 중간 | (T10 monitor FAIL, rollback flag 즉시 적용) |
| R5 | parity sample period 부족 | 높음 | 낮음 | (T03 --sample-period < 5 거래일, exit 1) |
| R6 | LS 직접 의존 신규 (L7 위반) | 치명 | 매우 낮음 | (LS marker grep, audit reject) |
| R7 | Kiwoom runtime 영향 (P1 위반) | 치명 | 매우 낮음 | (trade/ utility/ 변경, V11 audit reject) |
| R8 | CLI surface 변경 (L9 위반) | 높음 | 낮음 | (init/backtest/realtime CLI 시그니처 변경, audit reject) |
| R9 | DB 파일 commit (L8 위반) | 높음 | 낮음 | (`*.db` git status, .gitignore guard) |
| R10 | 사용자 승인 없이 ON commit | 치명 | 낮음 | (V3K_PHASE_F_USER_ACK 미설정, T08 reject) |

---

## F. Rollback 절차

### F.1 즉시 rollback (운영 중 한계 이탈 발견)

```powershell
# 1) rollback flag 즉시 설정
$env:V3K_PHASE_F_DISABLE = "1"
# 2) 운영 환경에서 strategy 재시작 (analyzer output 무시)
# 3) audit
python scripts/audit_v3k_phase_f_rollback.py
# 4) 원인 분석 후 별도 phase plan
```

### F.2 feature flag DB row 비활성화

```powershell
# 1) production DB row UPDATE (사용자 명시 승인 + V3K_PHASE_F_USER_ACK=1)
# - phase_f_analyzer_strategy.enabled=0 UPDATE
# 2) audit re-run
python scripts/audit_v3k_phase_f_rollback.py
```

### F.3 ON commit revert (최후 수단)

```powershell
# 1) ON commit revert
git -C C:/System_Trading/STOM/STOM_V.wt-dev revert <on-commit-sha> --no-edit
# 2) DB row 수동 OFF
# 3) 7일 모니터링 재시작 (LF3 한계 재정의 필요 시)
```

---

## G. 산출물

### G.1 Commit 포함 (~12건, sub-phase별 분리 권장)

| sub-phase | commit 예상 |
| --- | --- |
| F-1 | adapter + smoke 2건 |
| F-2 | parity script + report 2건 |
| F-3 | feature flag gate + rollback audit + smoke 3건 |
| F-4 | ON commit + registry + 24h monitor report 3건 |

세부:
1. `strategy/v3k_formula_facade.py` (수정)
2. `strategy/v3k_analyzer_adapter.py` (수정)
3. `scripts/smoke_v3k_phase_f_default_off.py` (신규)
4. `scripts/backtest_v3k_phase_f_parity.py` (신규)
5. `.omx/reports/v3k-phase-f-parity-<utc>.json` (audit trail)
6. `scripts/audit_v3k_phase_f_rollback.py` (신규)
7. `.omx/reports/v3k-phase-f-rollback-audit.json` (audit trail)
8. `docs/CARRY_FORWARD_REGISTRY.md` (수정 — V3K-PHASE-F-ENABLE 섹션)
9. `.omx/reports/v3k-phase-f-enable-<utc>.json` (ON commit 시점 audit trail)
10. `.omx/reports/v3k-phase-f-monitor-<utc>.json` (24h monitor 결과)

### G.2 Ephemeral 또는 commit 금지

- `_database/*.db` (L8)
- live runtime log

---

## H. Commit message 한국어 sample

### H.1 F-1 — adapter + smoke

```text
V3K Phase F analyzer output formula adapter를 도입한다 (default-OFF)

- `strategy/v3k_formula_facade.py`에 `V3K_` prefix callable을 노출한다.
- default-OFF 시 모든 callable이 0/None을 반환한다.
- 기존 strategy formula는 무회귀로 보호된다.
```

### H.2 F-2 — backtest parity baseline

```text
V3K Phase F backtest parity baseline을 산출한다

- 1주일 sample period에서 analyzer-disabled vs enabled 두 모드를 비교한다.
- 손실 변동 X%, MDD 변동 Y%, 거래횟수 변동 Z%가 한계 내임을 검증한다.
- parity report를 audit trail로 commit한다.
```

### H.3 F-3 — feature flag 이중 gate + rollback

```text
V3K Phase F feature flag 이중 gate와 rollback flag를 도입한다

- 환경 변수와 DB row 두 조건을 모두 만족할 때만 ON된다.
- `V3K_PHASE_F_DISABLE=1`로 즉시 OFF로 전환 가능하다.
- rollback 시나리오를 audit script로 자동검증한다.
```

### H.4 F-4 — ON 전환 (사용자 명시 승인 후)

```text
V3K Phase F analyzer output 전략 반영을 ON으로 전환한다

- 사용자 명시 승인(V3K_PHASE_F_USER_ACK=1)과 parity 한계 내 통과를 commit 시점에 기록한다.
- registry V3K-PHASE-F-ENABLE 섹션을 추가한다.
- 24시간 backtest monitoring을 시작한다. 한계 이탈 발견 시 rollback flag 즉시 적용한다.
```

---

## I. ADR 요지

- **Decision**: Phase F는 default-OFF + 이중 gate + rollback flag + parity 한계 검증 + 24h 모니터링 5중 안전망으로 운영. sub-phase F-1/F-2/F-3/F-4로 분해
- **Drivers**: audit §6.2 #6 종착, V3K 미션의 핵심 가치 실현, 매매 판단 영향 차단
- **Alternatives considered**:
  - 단일 gate (env only or DB only) → R3로 기각
  - rollback flag 없음 → R2로 기각
  - parity 검증 생략 → R1로 기각
  - 24h 모니터링 생략 → R4로 기각
- **Why chosen**: 5중 안전망이 reversible하게 매매 판단 영향을 차단한다
- **Consequences**:
  - 긍정: F6 #6 항목 S4 도달, V3K 미션 핵심 가치 실현
  - 부정: ON 전 sub-phase 4개 분리로 일정 정체. 단, 안전성 우선
- **Follow-ups**:
  - F4 (Phase G microstructure)에서 본 phase의 LF1–LF4 패턴 재사용
  - parity 한계 수치(LF3)는 운영 모니터링 결과에 따라 보정 가능 (별도 phase)

---

## J. 핵심 설계 질문

### Q1. parity 한계 수치(LF3)는 어떻게 결정되는가?
A. T03 작업 시점에 결정. 본 plan은 권장 한계(손실 ±5%, MDD ±3%, 거래횟수 ±10%)를 명시하지만 운영 backtest baseline에서 도출된 statistical noise 범위로 보정 가능.

### Q2. rollback flag와 DB row OFF 중 어느 것이 우선?
A. **rollback flag 우선**. `V3K_PHASE_F_DISABLE=1`이 설정되면 DB row와 무관하게 즉시 OFF.

### Q3. sub-phase F-1/F-2/F-3는 각각 별도 ralplan 필요?
A. F-1, F-2, F-3는 본 plan의 single ralplan에서 합의된 sub-phase이므로 추가 ralplan 불필요. F-4(ON 전환)는 사용자 명시 승인 자체가 합의 수준의 gate.

### Q4. analyzer output이 기존 strategy의 결과를 *악화*시키면?
A. T03 parity에서 발견되어 LF3 한계 이탈로 ON 차단. ON 후 발견되면 T10 monitoring에서 발견되어 rollback flag 적용.

### Q5. Phase F가 V3K 미션의 가장 위험한 phase인 이유는?
A. 매매 판단 직접 영향. 다른 phase는 read/dry-run/sidecar 등 reversible 범위에 머무르지만 Phase F는 실제 P&L 변동. 따라서 5중 안전망 필수.

---

## K. 다음 단계 전환 지침

### K.1 완료 조건

- T01–T10 모두 commit (T07은 사용자 명시 승인 응답)
- V01–V12 모두 PASS
- F6 산식 #6 항목 S0 → S4 전이 확인
- 24h monitoring 한계 내 유지

### K.2 본 phase 완료 후 진행 가능한 phase

- **F4 (Phase G microstructure)**: Phase F의 LF1–LF4 패턴 재사용
- **closure gate (F7)**: §1.1 #6 종착 조건 PASS

### K.3 본 plan freeze 정책

Phase F ON commit 후 본 plan freeze. parity 한계 수치 조정이 필요하면 별도 phase plan.

### K.4 `--deliberate` ralplan 의무

본 plan 실행 전 `/oh-my-claudecode:ralplan --deliberate` 재합의 필수. pre-mortem + expanded test plan (unit/integration/e2e/observability) 보강 권장.

---

## L. 관련 문서

- `docs/plans/2026-05-10_v3k_phase_a_shadow_db_plan.md` (Phase A plan)
- `docs/plans/2026-05-12_v3k_production_learning_db_read_plan.md` (F5, precondition)
- `docs/plans/2026-05-12_v3k_db_cutover_plan.md` (F1, precondition 권장)
- `docs/update_log/2026-05-12_v3k_phase_letter_remapping_decision.md` (F2)
- `docs/update_log/2026-05-12_v3k_progress_metric_methodology.md` (F6)
- `docs/update_log/2026-05-12_v3k_mission_closeout_procedure.md` (F7)
- `docs/update_log/2026-05-10_2uc_v3k_full_feature_audit.md` (§6.2 #6)
