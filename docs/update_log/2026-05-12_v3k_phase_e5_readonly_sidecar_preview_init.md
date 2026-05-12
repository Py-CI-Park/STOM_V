# V3K-PHASE-E5: read-only sidecar preview initialization bridge

작성일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`

---

## 1. 작업 목적

2U_C의 V3K 목표는 Kiwoom을 유지하면서 V3 기능을 안전하게 이행하는 것이다. Page 024는 actual sidecar write 없이, 사용자가 수동으로 준비한 valid sidecar 후보 파일을 session-only GUI preview 초기값으로 읽어올 수 있는 최소 경계를 구현했다.

이 변경은 persistence가 아니다. read-only loader의 결과를 preview의 in-memory 초기 상태로만 반영하며, 이후 사용자의 toggle은 기존 session-only override 경로로 처리된다.

---

## 2. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `ui/ui_v3k_settings_preview.py` | `initialize_v3k_preview_from_sidecar()` 추가, preview attach 시 read-only sidecar 초기값 반영 경계 추가 |
| `scripts/smoke_v3k_gui_sidecar_preview_init.py` | missing/corrupt/valid sidecar, session override, no artifact smoke 추가 |
| `scripts/smoke_v3k_gui_settings_preview.py` | preview attach 결과에 read-only sidecar 상태 검증 추가 |
| `scripts/audit_v3k_gui_sidecar_persistence_design.py` | Page 024 문서 요구사항 반영 |
| `scripts/audit_v3k_gui_sidecar_write_guard.py` | Page 024/025 문서 요구사항 반영 |
| `scripts/audit_v3k_verify_1b_closure.py` | closure checklist에 read-only preview init smoke 반영 |
| `docs/update_log/2026-05-12_v3k_cd6f5bd_to_page024_flow_review.md` | `cd6f5bd` 이후 전체 흐름 리뷰 기록 |

---

## 3. 검증 기준

- missing sidecar: default-OFF preview 유지
- corrupt sidecar: default-OFF preview 유지
- valid sidecar: preview model 초기 checked 값에 반영
- session override: sidecar 초기값보다 우선
- no-write: repo `_v3k_sidecar`, `_database`, `_log`, `*.db`, `backtest/graph` artifact 미생성
- no-live-runtime: Kiwoom 주문/청산/live runtime, formula/global runtime hook, analyzer trading decision 미연결

---

## 4. 현재 결론

Page 024는 목표에 맞게 진행되었다. V3 기능 활성화의 GUI persistence 경로를 준비하되, 실제 write는 보류했고, read-only sidecar 값을 session-only preview 초기값으로만 제한했다.

다음 단계는 Page 025에서 tempfile-only writer prototype을 검토하는 것이다. 이는 repo sidecar write가 아니며, Page 023 guard 조건을 만족할 수 있는지 확인하는 안전한 중간 단계다.
