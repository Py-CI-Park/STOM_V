# V3K Page 013 — session-only V3K UI preview 계획

작성일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`
기준 commit: `a05c26ee V3K 체크박스 노출 전에 layout 저장 경계를 먼저 닫는다`
연결 문서:
- `docs/plans/2026-05-11_v3k_phase_c2_gui_wrapper_inventory_plan.md`
- `docs/update_log/2026-05-12_v3k_phase_c2_3_gui_checkbox_layout_feasibility.md`
- `docs/update_log/2026-05-12_v3k_phase_c2_4_persistent_storage_decision.md`

---

## 0. 목적

Page 013의 목적은 C2-4 결정에 따라 **persistent 저장 없이 session-only V3K UI preview**를 구현할 수 있는 가장 좁은 경계를 고정하는 것이다.

전체 V3K 목적은 계속 동일하다.

```text
STOM_Version_2U_C에서 Kiwoom 증권 API를 유지한다.
LS증권 직접 의존성은 제외한다.
V3의 분석·학습·DB·백테스트·실시간 사전학습 기능은 안전한 단계로 반영한다.
```

---

## 1. C2-4 결정 요약

| 선택지 | 판단 |
| --- | --- |
| session-only | **다음 구현 경계로 선택**. 운영 DB를 바꾸지 않고 UI 표시/토글 smoke를 먼저 만들 수 있다. |
| sidecar 설정 저장소 | 운영 DB보다 안전하지만 파일 write/위치/백업/동기화 정책이 필요하므로 session-only UI preview 이후 별도 phase로 보류한다. |
| 운영 `_database/setting.db` migration | 기존 설정 DB schema와 설정 파일 복사/적용 흐름을 바꾸므로 현재 단계에서 제외한다. |

---

## 2. Page 013 in-scope

| 항목 | 내용 |
| --- | --- |
| UI 형태 | 기존 groupBox에 끼워 넣지 않고, 별도 V3K 탭 또는 별도 dialog 중 더 작은 변경을 선택한다. |
| 데이터 원천 | `v3k_settings_contract_rows()` metadata와 MainWindow의 `v3k_settings`/`v3k_feature_flags` inert state. |
| 저장 정책 | session-only. 재시작/설정파일 전환 후 persistence를 보장하지 않는다. |
| default | 모든 V3K flag는 default-OFF. |
| smoke | no-GUI smoke에 source-level layout/slot 경계 확인을 추가하고, 가능하면 `verify_pyd_gui_contract.py`와 `smoke_offline_gui.py`를 실행한다. |

---

## 3. Out-of-scope

| 항목 | 이유 |
| --- | --- |
| 운영 `_database/setting.db` schema/write | C2-4에서 보류한 고위험 경계다. |
| sidecar 설정 파일/DB write | 별도 저장소 정책 phase 전까지 보류한다. |
| Kiwoom 주문/청산/live runtime | UI preview와 무관하며 Phase E/F/G 전까지 금지한다. |
| formula globals runtime hook | Phase D 전까지 금지한다. |
| analyzer output trading decision | Phase F/G 전까지 금지한다. |
| LS Securities 직접 의존성 | V3K 정의상 영구 제외한다. |

---

## 4. 권장 구현 순서

| Step | 작업 | 완료 조건 |
| ---: | --- | --- |
| 013-1 | V3K UI preview 위치 결정 | 별도 탭/dialog 중 하나를 선택하고 이유를 update_log에 기록 |
| 013-2 | session-only UI skeleton 구현 | `setting.db` write 없이 `v3k_settings` in-memory state만 표시/토글 |
| 013-3 | no-GUI source-level smoke 보강 | widget 추가 위치, persistent write 부재, default-OFF 유지 검증 |
| 013-4 | GUI/pyd-free smoke | `verify_pyd_gui_contract.py`, `smoke_offline_gui.py` 가능 시 통과 또는 환경 사유 기록 |
| 013-5 | C2 저장소 후속 판단 | sidecar/persistent 저장 phase가 필요한지 재판단 |

현재 진행률:

```text
Page 013: [░░░░░░░░░░] 0 / 5 = 0%
```

---

## 5. 다음 추천 OMX 명령

```powershell
omx ralph "force: V3K Page 013 Phase C2-5 session-only V3K UI preview skeleton을 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_page_013_session_only_ui_preview_plan.md와 docs/update_log/2026-05-12_v3k_phase_c2_4_persistent_storage_decision.md를 기준으로, 운영 _database/setting.db schema/write와 sidecar 파일 write 없이 MainWindow의 v3k_settings/v3k_feature_flags inert state를 표시하거나 session-only로 토글할 수 있는 가장 작은 별도 V3K 탭 또는 dialog skeleton을 검토하고 가능하면 구현한다. Kiwoom 주문/청산/live runtime, formula globals runtime hook, analyzer output trading decision, LS Securities 직접 의존성은 변경하지 않는다. 완료 시 py_compile, smoke_v3k_gui_wrapper_bridge, smoke_v3k_gui_settings_bridge, smoke_v3k_settings_surface, verify_pyd_gui_contract.py, 가능한 경우 smoke_offline_gui.py, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB artifact status를 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록 후 한국어 Lore commit한다."
```

현재 Codex 환경에서 `omx ralph`가 `stdin is not a terminal`로 실패하면, 같은 프롬프트를 현재 세션에서 직접 이어서 수행한다.
