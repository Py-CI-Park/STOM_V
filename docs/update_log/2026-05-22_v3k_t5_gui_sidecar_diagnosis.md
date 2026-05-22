# T5 — 분야 ③ 화면 설정 사이드카 진단 보고서

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-22 KST |
| baseline HEAD | `774807e4` (T4 수식 진단 직후) |
| 마스터 plan | `docs/plans/2026-05-22_v3k_backtest_track_5fields_sequential_execution_plan.md` §3.5 T5 |
| 본 commit 정체성 | 5개 분야 순차 plan **T5 (분야 ③ GUI 사이드카) 마지막 단계** 진단 결과 정본화 |
| 코드 변경 | 0건 |
| 매매 영향 | 0건 |

---

## §0. TL;DR

```text
분야 ③ 화면 설정 사이드카는 master plan 추정 75%보다 풍부한 진척 상태.

핵심 자산:
  - strategy/v3k_gui_sidecar.py (147줄, 1 클래스, 5 함수)
  - Phase E0/E1/E2/E3/E4/E5/E6 7 sub-phase 모두 closure
  - V3K-PHASE-E0 ~ V3K-PHASE-E6 registry 7 섹션 등록
  - Sidecar 관련 plan 15건 + audit scripts 10건 + smoke 4건
  - _v3k_sidecar/v3k_gui_settings.json 실제 파일 존재 (2026-05-14)
  - Phase F/G 토글 ON 상태 (live wiring/operating DB write는 false)
  - smoke 4건 모두 PASS

진척률 실측: 75% → 90% (+15%p)
잔여: Phase F/G의 live order/exit wiring + operating DB write (매매 트랙 D에서 다룸)
```

---

## §1. v3k_gui_sidecar.py 모듈 구조

`strategy/v3k_gui_sidecar.py` (147줄):

```python
V3K_GUI_SIDECAR_DIR             = "_v3k_sidecar"
V3K_GUI_SIDECAR_FILE            = "_v3k_sidecar/v3k_gui_settings.json"
V3K_GUI_SIDECAR_BACKUP_DIR      = "_v3k_sidecar/backups"
V3K_GUI_SIDECAR_SCHEMA_VERSION  = 1
V3K_GUI_SIDECAR_SOURCE          = "v3k_gui_settings_preview"
V3K_GUI_SIDECAR_REQUIRED_FIELDS = (...)  # 필수 필드 튜플

class V3KGuiSidecarValidationResult       # line 31
def _default_off_result(...)               # line 53
def _payload_from_json_text(...)           # line 62
def validate_v3k_gui_sidecar_payload(...)  # line 74
def load_v3k_gui_sidecar_file(...)         # line 118
def apply_v3k_sidecar_session_override(...) # line 136
```

**핵심 invariant**: schema_version 1 + required fields 검증 + session override 우선순위 + default-OFF fallback.

---

## §2. _v3k_sidecar/v3k_gui_settings.json 본문

현재 (2026-05-14T09:21 갱신) 사이드카 토글 상태:

```json
{
  "approval_gate": "phase-g-g3-on-await-user-approval",
  "approval_record": "2026-05-14T06:42:48+09:00",
  "approval_state": "approved-gate3-phase-g-enabled",
  "phase_f_approval_record": "2026-05-14T08:51:52+09:00",
  "phase_g_approval_record": "2026-05-14T09:21:23+09:00",
  "phase_f_live_order_exit_wiring":   false,   ← 매매 wiring 없음
  "phase_f_operating_database_written": false,   ← 운영 DB write 없음
  "phase_g_live_order_exit_wiring":   false,
  "phase_g_operating_database_written": false,
  "phase_g_rollback_env": "V3K_PHASE_G_DISABLE",
  "schema_version": 1,
  "settings": {
    "V3K_ANALYSIS_UI_ENABLED":        false,
    "V3K_ANALYZER_MODULE_STAGING":    false,
    "V3K_BACKTEST_LEARNING_ENABLED":  false,
    "V3K_FORMULA_MANAGER_ADAPTER":    false,
    "V3K_PHASE_F_ANALYZER_STRATEGY":  true,   ← Phase F 토글 ON
    "V3K_PHASE_G_MICROSTRUCTURE_ENGINE": true, ← Phase G 토글 ON
    "V3K_REALTIME_LEARNING_ENABLED":  false,
    "V3K_RISK_ANALYZER_V3_ENGINE":    false,
    "V3K_STG_GLOBALS_FACADE":         false,
    "가격대분석": false, "거래량분석": false, "리스크분석": false,
    "변동성분석": false, "변손익분석": false, "캔들분석": false
  }
}
```

### §2.1 매우 중요한 발견 — sidecar 토글은 이미 ON, 단 매매 wiring은 분리

- **Phase F 토글 ON** (`V3K_PHASE_F_ANALYZER_STRATEGY: true`)
- **Phase G 토글 ON** (`V3K_PHASE_G_MICROSTRUCTURE_ENGINE: true`)
- 다만:
  - `phase_f_live_order_exit_wiring: false` (매매 결정 경로 wiring 안 됨)
  - `phase_g_live_order_exit_wiring: false`
  - `phase_f_operating_database_written: false`
  - `phase_g_operating_database_written: false`

즉 **사이드카 토글 자체는 승인된 상태**이지만 **매매 결정 경로 wiring 0건 + 운영 DB write 0건**. 이게 *분야 ⑥ + ⑦ 진척률 50%*의 근거 (master plan §4.2 표).

매매 트랙 D 활성화 시 sidecar 토글을 보고 wiring 활성화 → live order/exit 경로 변경 → operating DB write 발생. 그 시점 전까지는 본 sidecar 토글 자체로 매매 영향 0건.

---

## §3. Phase E 7 sub-phase closure 상태 (registry 인용)

| Sub-phase | Registry 섹션 | 위치 | 상태 |
| --- | --- | ---: | --- |
| E0 | V3K-PHASE-E0: runtime activation gap review | line 877 | ✅ closure |
| E1 | V3K-PHASE-E1: GUI sidecar persistence design | line 895 | ✅ closure |
| E2 | V3K-PHASE-E2: GUI sidecar schema validator | line 915 | ✅ closure |
| E3 | V3K-PHASE-E3: GUI sidecar read-only loader | line 937 | ✅ closure |
| E4 | V3K-PHASE-E4: GUI sidecar write guard/rollback decision | line 959 | ✅ closure |
| E5 | V3K-PHASE-E5: read-only sidecar preview init bridge | line 980 | ✅ closure |
| E6 | V3K-PHASE-E6: sidecar tempfile-only writer prototype | line 1005 | ✅ closure |

→ Phase E0~E6 7개 sub-phase 모두 종결 상태.

---

## §4. 관련 plan 인벤토리 (15건+)

| Plan | 단계 |
| --- | --- |
| `2026-05-12_v3k_page_019_phase_e0_runtime_activation_gap_review_plan.md` | E0 |
| `2026-05-12_v3k_page_020_phase_e1_gui_sidecar_persistence_design_plan.md` | E1 |
| `2026-05-12_v3k_page_021_phase_e2_gui_sidecar_schema_validator_plan.md` | E2 |
| `2026-05-12_v3k_page_022_phase_e3_gui_sidecar_readonly_loader_plan.md` | E3 |
| `2026-05-12_v3k_page_023_phase_e4_gui_sidecar_write_guard_plan.md` | E4 |
| `2026-05-12_v3k_page_024_phase_e5_readonly_sidecar_preview_init_plan.md` | E5 |
| `2026-05-12_v3k_page_025_phase_e6_sidecar_tempfile_writer_plan.md` | E6 |
| `2026-05-13_v3k_page_049_gui_sidecar_write_approval_prep_plan.md` | write approval prep |
| `2026-05-13_v3k_page_057_gui_actual_sidecar_write_preflight_plan.md` | actual write preflight |
| `2026-05-13_v3k_page_059_gui_sidecar_write_approval_execution_packet_plan.md` | approval execution |
| `2026-05-13_v3k_page_060_gui_sidecar_write_readiness_audit_plan.md` | readiness audit |
| `2026-05-13_v3k_page_062_gui_sidecar_default_payload_preview_plan.md` | default payload |
| `2026-05-13_v3k_page_063_gui_sidecar_write_approval_template_plan.md` | approval template |
| `2026-05-14_v3k_page_064_gui_sidecar_preapproval_completion_audit_plan.md` | preapproval completion |
| `2026-05-14_v3k_page_071_gui_sidecar_first_gate_preflight_plan.md` | first gate preflight |

→ Phase E의 design → persistence → schema validator → readonly loader → write guard → preview init → tempfile writer → approval prep → preflight → execution packet → readiness audit → default payload → approval template → preapproval completion → first gate preflight까지 매우 깊은 trail.

---

## §5. Sidecar 관련 scripts (10건+)

```
audit_v3k_gui_sidecar_approval_template.py
audit_v3k_gui_sidecar_first_gate_blocker_snapshot.py
audit_v3k_gui_sidecar_first_gate_preflight.py
audit_v3k_gui_sidecar_gate1_execution.py
audit_v3k_gui_sidecar_persistence_design.py
audit_v3k_gui_sidecar_preapproval_completion.py
audit_v3k_gui_sidecar_write_guard.py
audit_v3k_gui_sidecar_write_readiness.py
preflight_v3k_gui_sidecar_write_gate.py
preview_v3k_gui_sidecar_default_payload.py
```

추가로 sidecar 토글 writer scripts:

```
write_v3k_phase_f_sidecar_enable.py     ← Phase F 토글 writer
write_v3k_phase_g_sidecar_enable.py     ← Phase G 토글 writer
```

→ 사이드카 토글 메커니즘 모든 단계 (design / validate / load / write guard / preview / tempfile writer / approval template / preflight / readiness)에 audit/preflight scripts 작성됨.

---

## §6. Smoke 4건 실행 결과 (직접 검증)

본 PC `STOM_Version_2U_C` worktree에서 read-only 실행:

| # | smoke | 결과 | 검증 항목 |
| ---: | --- | --- | --- |
| 1 | `smoke_v3k_gui_sidecar_schema_validator.py` | ✅ PASS | session override priority 검증 |
| 2 | `smoke_v3k_gui_sidecar_readonly_loader.py` | ✅ PASS | missing/corrupt/valid/session-override 경로 모두 검증 |
| 3 | `smoke_v3k_gui_sidecar_preview_init.py` | ✅ PASS | read-only sidecar values initialize session-only preview |
| 4 | `smoke_v3k_gui_settings_bridge.py` | ✅ PASS | GUI/settings extraction filter |

**총 4건 모두 PASS** — sidecar schema 검증 + read-only loader + preview init + GUI settings bridge 모두 동작 확인.

---

## §7. 진척률 영향

### §7.1 분야 ③ 갱신

```
변경 전 (master plan 추정): 75%
변경 후 (T5 실측):          90% (+15%p)
```

산정 근거:

| 항목 | 점수 |
| --- | ---: |
| 본체 module v3k_gui_sidecar.py 완비 | 15점 |
| Phase E0~E6 7 sub-phase 모두 closure | 25점 |
| V3K-PHASE-E0 ~ E6 registry 7 섹션 등록 | 15점 |
| 관련 plan 15건 + audit scripts 10건 | 20점 |
| smoke 4건 모두 PASS | 10점 |
| _v3k_sidecar/v3k_gui_settings.json 실제 파일 + Phase F/G 토글 ON | 5점 |
| **소계** | **90점** |
| Phase F/G live order/exit wiring (운영 매매 측면) | 0점 (이연) |
| operating DB write 활성화 | 0점 (이연) |

분야 ③의 *백테스트/사이드카 정책 영역*은 사실상 closure 상태. 잔여 10%는 모두 매매 트랙 D에서 다룸.

### §7.2 F6 산식 단독 영향

```
이전: (50+90+75+75+100+50+50)/700 = 490/700 = 70.0%  (T4 commit 후)
이후: (50+90+90+75+100+50+50)/700 = 505/700 = 72.1%  (T5 진단 후)

⊕ +2.1%p
```

---

## §8. 잔여 작업 정리

### §8.1 분야 ③에서 미진행

| 항목 | 보류 사유 |
| --- | --- |
| `phase_f_live_order_exit_wiring` true 전환 | 매매 결정 경로 변경, 트랙 D 활성화 시점 |
| `phase_g_live_order_exit_wiring` true 전환 | 동일 |
| `phase_f_operating_database_written` true 전환 | 운영 DB write 시작, 트랙 D + F1 cutover 시점 |
| `phase_g_operating_database_written` true 전환 | 동일 |

### §8.2 분야 ③ 진행 plan 작성 필요 여부

**불필요**. 이유:

1. Phase E0~E6 plan 7건 + Page 049~071 plan 8건 = 총 15건 이미 정본화
2. 본 T5 진단 결과 분야 ③의 사이드카 정책 영역은 사실상 완료
3. 잔여 live wiring + operating DB write는 매매 트랙 D 활성화 시점에 기존 plan 인용

본 T5 commit은 진척률 실측 + Phase E 종결 확인 baseline.

---

## §9. preparation-first §3 정합

| 허용 | 본 commit |
| --- | --- |
| docs 추가 | ✅ update_log 1건 |
| read-only smoke 실행 | ✅ 4건 모두 default-OFF / read-only |
| sidecar 토글 read | ✅ JSON read만 |

| 금지 | 본 commit |
| --- | --- |
| 코드 변경 | ❌ 0건 |
| `_v3k_sidecar/v3k_gui_settings.json` write | ❌ 0건 |
| `phase_f/g_live_order_exit_wiring` 변경 | ❌ 0건 |
| operating `_database/` write | ❌ 0건 |
| LS direct dependency | ❌ 0건 |

→ P-lane 적격.

---

## §10. 검증

```powershell
python scripts/audit_v3k_phase_h_gate4_environment_status.py
python scripts/audit_v3k_verify_1a.py --base 9423735e
python scripts/verify_nonrelease_sync.py
git diff --check
```

---

## §11. 5개 분야 순차 plan 완료 선언

```
T1 ⑥ 분석기 parity            ✅ 완료 (26a10919)
T2 ⑦ 엔진 parity + benchmark  ✅ 완료 (26a10919)
T3 ② F5 마무리                ✅ 완료 (397390f1)
T4 ④ 수식 전역값 진단         ✅ 완료 (774807e4)
T5 ③ 사이드카 진단            ✅ 완료 (본 commit)
```

**5/5 (100%) 완료**. 트랙 A 백테스트 강화 cycle 종결.

---

## §12. 다음 인계 (트랙 A 종결 후)

5개 분야 순차 plan 완료 후 다음 가능한 작업:

| 옵션 | 작업 | 트랙 |
| --- | --- | --- |
| 트랙 B 진입 | CLI 확장 plan Phase 1 확장 (ai_controller / strategy_generator 노출) | 트랙 B |
| 트랙 B Phase 2 | 출력 표준화 일관성 검증 | 트랙 B |
| 트랙 B Phase 3 | config / history CLI 신규 | 트랙 B |
| 트랙 D 재개 | F1 cutover ralplan iteration 2 (Architect review) | 트랙 D (사용자 결정) |
| v5 mid-checkpoint | F6 산식 통일 + 트랙 A closure summary | 메타 |

권장 다음 작업: **트랙 B (CLI 확장)** 또는 **v5 mid-checkpoint 정본화** (트랙 A closure 결과 통합).

---

## §13. 관련 문서

- `docs/plans/2026-05-22_v3k_backtest_track_5fields_sequential_execution_plan.md` §3.5 T5
- `strategy/v3k_gui_sidecar.py` (본 진단 대상, 147줄)
- `_v3k_sidecar/v3k_gui_settings.json` (실제 사이드카 토글 파일)
- Phase E 7 sub-phase plan 7건 (`page_019` ~ `page_025`)
- Phase E + page 049-064-071 plan 15건 (§4 인용)
- audit scripts 10건 (§5 인용)
- smoke 4건 (`schema_validator`, `readonly_loader`, `preview_init`, `gui_settings_bridge`)
- `docs/CARRY_FORWARD_REGISTRY.md` (V3K-PHASE-E0~E6 7 섹션 line 877-1010 + 본 commit `V3K-T5-GUI-SIDECAR-DIAGNOSIS` 섹션)
