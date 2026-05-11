# V3K-PHASE-E3: GUI sidecar read-only loader

작성일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`

---

## 1. 작업 목적

2U_C의 V3K 목표는 Kiwoom 증권 API를 유지하면서 V3의 신기능을 안전하게 이행하는 것이다. Page 022에서는 GUI 설정 persistence로 가기 위한 중간 단계로, sidecar 후보 파일을 **읽을 수만 있는 loader**를 추가했다.

이 단계는 기능 활성화의 편의성을 높이기 위한 준비 작업이지만, 아직 실제 저장 기능은 아니다. 운영 DB나 sidecar 파일을 쓰지 않는 상태에서 다음을 검증하는 것이 핵심이다.

- sidecar 후보 파일이 없을 때 default-OFF로 안전하게 닫히는가
- sidecar 후보 파일이 깨졌을 때 overwrite 없이 default-OFF로 닫히는가
- valid payload가 Page 021 schema validator와 동일한 계약으로 해석되는가
- 알 수 없는 key는 무시되고 diagnostic으로 남는가
- session-only preview override가 sidecar보다 우선하는가
- repo `_v3k_sidecar/`, `_database`, `*.db`, `_log`, `backtest/graph` artifact가 생성되지 않는가

---

## 2. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `strategy/v3k_gui_sidecar.py` | `load_v3k_gui_sidecar_file()` 추가. 후보 경로를 read-only로 읽고 missing/read 실패는 default-OFF fallback 처리. |
| `scripts/smoke_v3k_gui_sidecar_readonly_loader.py` | tempfile 기반 missing/corrupt/valid/session override/no-artifact smoke 추가. |
| `scripts/audit_v3k_gui_sidecar_persistence_design.py` | Page 022 문서와 read-only loader missing-file contract 검증 추가. |
| `scripts/audit_v3k_verify_1b_closure.py` | closure checklist에 read-only loader smoke 반영. |
| `docs/plans/2026-05-12_v3k_page_022_phase_e3_gui_sidecar_readonly_loader_plan.md` | Page 022 계획을 완료 기록으로 갱신. |
| `docs/plans/2026-05-12_v3k_page_023_phase_e4_gui_sidecar_write_guard_plan.md` | 다음 Page 023 guard/rollback 계획 추가. |
| `docs/CARRY_FORWARD_REGISTRY.md` | V3K-PHASE-E3 carry-forward 기록 추가. |

---

## 3. 구현 세부

### 3.1 Loader contract

`load_v3k_gui_sidecar_file(path=V3K_GUI_SIDECAR_FILE)`는 다음 원칙을 따른다.

1. 파일을 만들지 않는다.
2. 디렉터리를 만들지 않는다.
3. `Path.is_file()`로 존재 여부만 확인한다.
4. 파일이 있으면 UTF-8 text로 읽고 기존 payload validator에 위임한다.
5. 파일이 없거나 읽을 수 없으면 default-OFF fallback을 반환한다.
6. fallback 과정에서 기존 파일을 덮어쓰지 않는다.

### 3.2 Smoke contract

`smoke_v3k_gui_sidecar_readonly_loader.py`는 repo 내부가 아니라 OS tempfile 내부에서만 test file을 만든다.

검증 항목:

- missing path → invalid/default-OFF + `sidecar file missing; default-OFF fallback`
- corrupt JSON → invalid/default-OFF + `sidecar payload invalid JSON; default-OFF fallback`
- valid JSON → schema v1 payload valid
- unknown setting → normalized settings에 누출되지 않고 diagnostic에 남음
- session-only override → sidecar 값보다 우선
- smoke 전후 git artifact status 동일

---

## 4. 의도적으로 제외한 항목

| 제외 항목 | 제외 이유 | 향후 조건 |
| --- | --- | --- |
| 실제 sidecar write | atomic write/backup/rollback/corruption recovery 정책이 아직 확정되지 않았음 | Page 023에서 guard/rollback 조건 확정 필요 |
| operating `setting.db` write | V2/2U_C 운영 설정 DB를 건드리면 rollback 범위가 커짐 | 별도 DB migration spec과 backup rehearsal 필요 |
| live Kiwoom runtime hook | read-only loader는 설정 후보 해석 단계일 뿐 live 주문/청산에 연결할 단계가 아님 | dry-run runtime hook과 rollback smoke 필요 |
| formula/global runtime hook | Page D-2에서 직접 hook을 보류했음 | guard 완화 승인과 collision-free 증거 필요 |
| analyzer output trading decision | analyzer는 아직 staged/dry-run 계약임 | live decision audit과 default-OFF rollback 필요 |

---

## 5. 검증 계획

필수 검증:

```powershell
python -m py_compile strategy/v3k_gui_sidecar.py scripts/smoke_v3k_gui_sidecar_readonly_loader.py scripts/audit_v3k_gui_sidecar_persistence_design.py scripts/audit_v3k_verify_1b_closure.py
python scripts/smoke_v3k_gui_sidecar_readonly_loader.py
python scripts/audit_v3k_gui_sidecar_persistence_design.py
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/verify_nonrelease_sync.py
python -m compileall -q strategy scripts ui backtest
python scripts/smoke_v3k_analyzer_adapter.py
python scripts/smoke_v3k_analyzer_modules.py
python scripts/smoke_v3k_learning_loader.py
python scripts/smoke_v3k_backtest_learning_hook.py
python scripts/smoke_v3k_realtime_learning_boundary.py
python scripts/smoke_v3k_formula_facade.py
python scripts/smoke_v3k_formula_boundary_contract.py
python scripts/smoke_v3k_formula_runtime_hook_decision.py
python scripts/smoke_v3k_settings_surface.py
python scripts/smoke_v3k_gui_settings_preview.py
python scripts/smoke_v3k_gui_sidecar_schema_validator.py
python scripts/smoke_v3k_gui_sidecar_readonly_loader.py
python scripts/audit_v3k_runtime_activation_gap.py
git diff --check
git status --short -- _v3k_sidecar _database _database_v3k_shadow _log backup *.db backtest/graph
```

---

## 6. 다음 단계

다음 Page 023은 `V3K-PHASE-E4: GUI sidecar write guard/rollback decision`이다.

Page 023의 stop condition은 “actual write를 해도 되는지”를 막연히 결정하는 것이 아니라, 실제 write를 허용하기 위한 **불변 조건**을 문서와 smoke 기준으로 확정하는 것이다.

조건이 부족하면 Page 023 결론은 “write 보류”가 맞다. V3K 전체 목표는 빠른 write가 아니라, Kiwoom 유지 + V3 기능 이행을 rollback 가능한 방식으로 완료하는 것이다.
