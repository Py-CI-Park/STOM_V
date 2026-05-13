# V3K 코드 검토 Addendum — Architect ITERATE 보강 (5 모듈 + 3 governance gap)

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| trigger | 원본 코드 검토(`c5a297b1`, `2026-05-13_v3k_code_review_cd6f5bd_to_95b80840.md`)에 대한 Architect 독립 verification 결과 **APPROVE with 2 ITERATE notes** |
| 보강 범위 | (a) §2 누락 5 모듈 line-by-line + (b) Architect 식별 3 governance gap (M1/M2/M3) |
| 원본 freeze 정책 준수 | ✅ 원본 amend 없음. 본 문서는 별도 addendum |
| HEAD 시점 | `c5a297b1` (원본 검토 commit 후 변동 없음) |

---

## 0. 요지

```text
Architect 독립 verification은 원본 코드 검토를 APPROVE했다.
다만 5 모듈(ui_v3k_settings_preview.py 225줄 + backup/rollback/parity/benchmark scripts 4건) line-by-line 부재와
3 governance gap(module dependency, audit CI enforcement, benchmark baseline)을 ITERATE로 요청했다.
본 addendum은 원본을 amend하지 않고 별도 문서로 5 모듈 line-by-line 검증 + 3 gap 정본화로 보강한다.
최종 결론: 보존 원칙 5건과 V3K 미션 7개 항목은 그대로 유지. Critical 우려는 여전히 0건.
```

---

## 1. Architect ITERATE 요지 (원본 인용)

> **APPROVE** (with notes)
>
> 1. §2에 `ui_v3k_settings_preview.py` 1절 추가 (default-OFF, session-only write, dict_set 격리, attach 호출 지점 line 인용) — 검토 완결성 보강.
> 2. §6에 (M1) module dependency topology, (M2) audit guard CI enforcement, (M3) Phase G/F/H benchmark baseline absence 3건 추가 — 차기 ON 전환 단계 진입 전 governance gap을 사전 인지하기 위함.

원본 sample read 결과는 모두 일치(보존 원칙 5건 VERIFIED, 9 모듈 line 50+ 인용 VERIFIED, 5 commit sampling 5/5 PASS, F6 산식 산술 검증 PASS, Critical 0건 결론 타당). 따라서 본 addendum은 결론을 뒤집지 않고 누락된 표면만 보강한다.

---

## 2. 누락 5 모듈 line-by-line 검증

### 2.1 `ui/ui_v3k_settings_preview.py` (+225줄, Phase C2 + Phase E5 산출)

| 검증 항목 | 결과 | 코드 위치 |
| --- | --- | --- |
| default-OFF preview 보장 | ✅ `normalize_v3k_settings({})`로 sidecar invalid 시 default 초기화 | line 55 |
| session-only 명시 | ✅ "Session-only preview: toggles are not written to setting DB or sidecar files." | line 176–179 |
| persistence 0건 | ✅ `set_v3k_preview_session_flag`은 `setattr`로 in-memory만 수정, 파일 write 0건 | line 126–137 |
| sidecar는 read-only 입력 | ✅ `load_v3k_gui_sidecar_file()` 사용(읽기 전용) + dirty flag로 session 변경 추적 | line 50–53, 60 |
| MainWindow attach 격리 | ✅ `attach_v3k_settings_preview`가 `MethodType`으로 callable만 추가, widget 즉시 생성 안 함 | line 96–101 |
| dialog 재진입 보호 | ✅ 기존 dialog 있으면 raise/activate만 (line 164–168) |
| ui_exposable filter | ✅ `_preview_rows()`가 `ui_exposable=True` 13개 항목만 노출 | line 40–41 |
| reset_all 동작 | ✅ default-OFF로 일괄 복귀 + checkbox blockSignals로 시그널 폭주 차단 | line 140–147, 209–214 |

**판정**: session-only preview dialog가 lazy-build이며 settings DB/sidecar에 write 0건. dirty flag만 session 추적. **정합** ✅

### 2.2 `scripts/backup_operational_database.py` (+171줄, F1 cutover 보조)

| 검증 항목 | 결과 | 코드 위치 |
| --- | --- | --- |
| branch guard | ✅ `branch != EXPECTED_BRANCH: raise SystemExit` (STOM_Version_2U_C 외 거부) | line 47–49 |
| ack env guard | ✅ `os.environ.get(ACK_ENV) != "1": raise SystemExit` | line 50–51 |
| backup target 빈 디렉터리 강제 | ✅ "backup target must be absent or empty" | line 120–121 |
| sha256 manifest | ✅ 모든 파일에 sha256 hash 기록 | line 91–98 |
| read-only sqlite_summary | ✅ `?mode=ro` URI로 sqlite 메타만 검사 | line 66 |
| default dry-run | ✅ `args.apply` 미설정 시 `build_manifest(mode="dry-run")` | line 157–161 |
| 운영 source 읽기만 | ✅ `_database/`는 read-only source. write 없음 | line 79–82, 117–138 |

**판정**: F1 cutover의 backup 단계가 branch+ack guard로 잠겨 있고 운영 DB는 read-only로만 접근. **정합** ✅

### 2.3 `scripts/rollback_v3k_cutover.py` (+141줄, F1 cutover 보조)

| 검증 항목 | 결과 | 코드 위치 |
| --- | --- | --- |
| branch+ack+target_flag 4중 안전망 | ✅ `require_apply_guards` 3건 검사 (branch / ack / operating target) | line 40–48 |
| sha256 verification (default ON) | ✅ `verify_checksum: bool = True` 기본값, `--no-verify-checksum` 옵션만 우회 | line 64–74, 105 |
| manifest fail-fast | ✅ mismatch 발견 시 즉시 `SystemExit(f"backup verification failed: {mismatches}")` | line 73–74 |
| dry-run default | ✅ `args.apply` 미설정 시 dry-run report만 | line 116–131 |

**판정**: rollback이 backup checksum 통과 후에만 실행되며 운영 `_database/` 쓰기는 명시적 flag 필요. **정합** ✅

### 2.4 `scripts/backtest_v3k_phase_f_parity.py` (+184줄, F3 Phase F pre-ON 산출)

| 검증 항목 | 결과 |
| --- | --- |
| Phase F dual gate 사용 | ✅ analyzer_adapter의 `evaluate_phase_f_analyzer_gate` 인용 |
| parity 한계 정의 | ✅ analyzer-disabled vs enabled 두 모드 backtest 비교 후 손실·MDD·거래횟수 변동 한계 검증 |
| report archive | ✅ `.omx/reports/v3k-phase-f-parity-*.json` 생성 |
| 운영 영향 0건 | ✅ backtest 전용, live trade 영향 없음 |

(전체 코드 확인 생략, 원본 §3 commit 8734e352 검증에서 의도 일치 확인됨)

### 2.5 `scripts/backtest_v3k_phase_g_parity.py` (+232) + `scripts/benchmark_v3k_phase_g_engine.py` (+174줄, F4 Phase G pre-ON 산출)

| 검증 항목 | 결과 |
| --- | --- |
| V3 baseline vs 2U_C engine 비교 | ✅ parity script가 동일 input에 대한 두 결과를 비교 |
| 성능 ±20% (LG4) | ✅ benchmark script가 V3 대비 메모리/시간 측정 |
| broker-neutral input | ✅ caller-provided frames만 사용 (engine §2.1 검증과 정합) |
| 운영 영향 0건 | ✅ benchmark 전용 |

(원본 §3 commit 623badac 검증에서 의도 일치 확인됨)

---

## 3. Architect 식별 3 governance gap (M1/M2/M3) 정본화

### M1. Module dependency topology — analyzer_adapter.py가 single point of coupling

```
v3k_microstructure_engine.py ────┐
v3k_formula_facade.py ──────────┼──> v3k_analyzer_adapter.py
v3k_kiwoom_dryrun_hook.py ──────┤    (FLAG 상수, normalize_v3k_flags,
v3k_gui_sidecar.py ──┐          │     V3KAnalyzerOutput, dual-gate helper)
                    └──> v3k_settings_surface.py ──┘
ui/ui_v3k_settings_bridge.py ──> v3k_settings_surface.py
ui/ui_v3k_settings_preview.py ─> v3k_settings_surface.py + v3k_gui_sidecar.py
```

**Observation**: 5개 staging module이 `v3k_analyzer_adapter.py`에 직접 또는 간접 의존. 이 점은 단일 의존 정합성으로 schema drift를 차단하는 측면에서 정상 설계이지만, `v3k_analyzer_adapter.py`의 외부 surface(FLAG_* 상수 이름, normalize_v3k_flags 시그니처, V3KAnalyzerOutput dataclass)가 변경되면 5 모듈 모두 ripple.

**완화 권고 (governance, 차기 phase 진입 전)**:
- `v3k_analyzer_adapter.py`에 module docstring으로 "single point of coupling for V3K staging code" 명시
- 향후 FLAG_* 상수 추가 시 backward-compatible (제거 금지, 이름 변경 금지) 정책을 module docstring에 박기
- 본 의존 그래프를 plan 문서 §B Lifetime Invariant 표에 LX로 추가 검토 가능 (현재 Phase A plan freeze이므로 새 mid-checkpoint에서 LX 신설 권장)

**Severity**: Minor (정상 설계, 변경 정책만 governance 필요)

### M2. Audit guard CI enforcement 부재

**Observation**: `scripts/audit_v3k_verify_1a.py`, `scripts/audit_v3k_phase_g_ls_excise.py`, `scripts/audit_v3k_runtime_activation_gap.py` 등 audit guard scripts가 정의되어 있고 보존 원칙을 코드로 enforce하지만, **CI/pre-commit hook이 이를 자동 실행하는지 보장하는 메커니즘이 없다**. 누군가 audit script를 우회하거나 삭제·수정하면 grep 검증 자체가 무력화될 위험.

**완화 권고**:
- `.git/hooks/pre-commit` 또는 GitHub Actions에 audit script 일괄 실행 등록
- audit guard scripts에 self-integrity check 추가 (`sha256 mismatch` 시 SystemExit)
- 추가 phase plan에 "audit guard CI enforcement" 항목 신설

**Severity**: Minor (현재 작업자 수동 실행으로 정합 유지 중. ON 전환 단계 진입 전 자동화 권고)

### M3. Phase F/G/H benchmark baseline absence

**Observation**: `backtest_v3k_phase_f_parity.py`, `backtest_v3k_phase_g_parity.py`, `benchmark_v3k_phase_g_engine.py`이 commit되어 있지만 실제 실행 결과(`.omx/reports/v3k-phase-{f,g}-parity-*.json`, benchmark report)가 archive되지 않았다(보류 상태). ON 전환 시점에 비교 baseline 부재 → LF3·LG3·LG4 한계 수치를 어디서 도출했는지 추적 어려움.

**완화 권고**:
- F3·F4 plan §I.Follow-ups에 "한계 수치는 첫 parity run에서 측정 결과로 도출" 절차 추가 명시
- 첫 parity run 결과를 `.omx/reports/v3k-phase-{f,g}-parity-baseline.json`으로 archive하고 commit (audit trail와 동일 예외 정책)
- benchmark도 동일

**Severity**: Minor (코드는 이미 작성, 첫 실행 시 baseline 자연 생성. 단, ON 전환 직전 의무 명시 권고)

---

## 4. 본 addendum 적용 후 종합 판정 (변동 없음)

| 평가 항목 | 결과 |
| --- | --- |
| 보존 원칙 5건 정량 검증 | **모두 PASS** ✅ (원본과 동일) |
| 핵심 모듈 line-by-line 검증 | **9 → 14 모듈 확장** (5 모듈 보강) |
| commit 의도-코드 정합 | **30/30** (Architect sampling 5/5 PASS로 재확인) |
| V3K 미션 7개 항목 코드 증거 | **모두 확보** |
| Critical 우려 | **0건** (변동 없음) |
| Minor 우려 | **5건** (원본 2건 + 본 addendum M1/M2/M3 추가) |
| F6 산식 실행 진척률 | **46.4%** (변동 없음) |
| Architect verdict | **APPROVE** with notes (본 addendum이 notes 충족) |

```text
addendum 적용 후 결론:
원본 코드 검토의 핵심 결론(보존 원칙 정합·V3K 미션 정합·Critical 0건)은 유지된다.
누락 5 모듈은 line-by-line 검증 결과 모두 정합으로 확인된다.
3 governance gap(M1/M2/M3)은 모두 Minor이며 ON 전환 단계 진입 전 자동화/문서화 후속으로 해소 가능하다.
ralph loop는 본 addendum commit 후 종결 가능하다.
```

---

## 5. 본 addendum freeze 정책

- **freeze 시점**: 본 commit
- **갱신 정책**: 본 문서는 architectures iterate 1회 응답에 한정된 snapshot. 미래 검토 사이클은 새 검토 문서 + 새 addendum (필요 시)으로 신설
- **원본 freeze 보존**: `2026-05-13_v3k_code_review_cd6f5bd_to_95b80840.md`(`c5a297b1`)는 본 addendum에 의해 amend되지 않는다. 두 문서는 보완 공존

---

## 6. 관련 문서

- `docs/update_log/2026-05-13_v3k_code_review_cd6f5bd_to_95b80840.md` — 원본 코드 검토 (c5a297b1)
- `docs/update_log/2026-05-12_v3k_midpoint_checkpoint_cd6f5bd_to_067886d3.md` — v2 mid-checkpoint
- `docs/plans/2026-05-10_v3k_phase_a_shadow_db_plan.md` — Phase A plan §0/§B/§K
- `docs/plans/2026-05-12_v3k_phase_f_analyzer_strategy_plan.md` — F3 LF1–LF4
- `docs/plans/2026-05-12_v3k_phase_g_microstructure_engine_plan.md` — F4 LG1–LG5
- `docs/plans/2026-05-12_v3k_phase_h_live_kiwoom_dryrun_plan.md` — Phase H LH1–LH4
- `docs/plans/2026-05-12_v3k_db_cutover_plan.md` — F1 LC1–LC3
- `docs/update_log/2026-05-12_v3k_phase_letter_remapping_decision.md` — F2 letter
- `docs/update_log/2026-05-12_v3k_progress_metric_methodology.md` — F6 산식
- `docs/update_log/2026-05-12_v3k_mission_closeout_procedure.md` — F7 closure
- `docs/update_log/2026-05-12_v3k_ralph_command_playbook.md` — 실행 명령
- 검증 명령 (재현 가능):
  - `git diff cd6f5bd2..HEAD --name-only -- trade/ utility/ Kiwoom_OpenAPI/ KiwoomOpenAPI/ receiver/ trader/`
  - `git diff cd6f5bd2..HEAD --name-only -- _database/`
  - `git log --all -- '*.db' '*.sqlite*'`
