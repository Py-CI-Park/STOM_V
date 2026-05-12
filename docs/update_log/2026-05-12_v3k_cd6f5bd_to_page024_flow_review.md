# V3K cd6f5bd 이후 Page 024까지 전체 흐름 리뷰

작성일: 2026-05-12 KST
기준 commit: `cd6f5bd24bd41a190feb59a8cc65b921df84ca0d`
현재 목표: `STOM_Version_2U_C`에 Kiwoom을 유지한 채 V3 기능을 안전하게 이행

---

## 1. 전체 목표 재확인

이 작업 흐름의 목표는 `STOM_Version_2U_C`를 V3 branch로 바꾸는 것이 아니다. 목표는 V2/2U_C의 Kiwoom 기반 런타임을 유지하면서, V3에서 새로 도입된 DB/학습/분석/backtest/realtime/GUI 설정/공식 계산 관련 기능을 LS증권 직접 의존성 없이 단계적으로 이행하는 것이다.

따라서 다음 원칙이 계속 유지되어야 한다.

- Kiwoom 주문/청산/live runtime은 직접 건드리지 않는다.
- LS Securities 직접 API 의존성은 들여오지 않는다.
- operating `_database/setting.db`와 실제 DB cutover는 별도 migration/backup/rollback 전에는 금지한다.
- V3K feature flag는 default-OFF로 둔다.
- read-only/dry-run/smoke/audit를 통과한 경계만 다음 단계로 넘긴다.

---

## 2. cd6f5bd 이후 흐름 요약

| 구간 | 대표 commit/문서 | 내용 | 목표 정합성 |
| --- | --- | --- | --- |
| 감사 기준 정렬 | `cd6f5bd`, `b5e91a91`, `76f2bfe7` | Python 3.13 기준 감사 보고서와 의도적 미완료 항목 활성화 순서 정리 | 양호 |
| Phase A | `1196946a` | shadow DB rehearsal을 실행 가능하게 구성 | 양호: 운영 DB cutover 아님 |
| Phase B | `53515434`, `3eac14ec` | 학습 DB read-only 경계 증명 | 양호: read-only 유지 |
| Page 011 / Phase C | `eac38f12`, `88335424` | 다음 활성화 경계와 settings bridge default-OFF 고정 | 양호 |
| Phase C2 | `31f870c9` ~ `5ed8cd2b` | GUI wrapper, MainWindow inert state, session-only preview, Alt+V launcher, C2 closeout | 양호: persistence 없음 |
| Phase D | `0b13abc1` ~ `0d8ac586` | formula/global boundary, dry-run, runtime hook 보류 | 양호: `globals().update` 미연결 |
| Phase E0-E2 | `87d7e696` ~ `d478c2c8` | GUI sidecar persistence design, schema validator | 양호: file write 없음 |
| Phase E3-E4 | `eb7d5631`, `d763e71a` | read-only loader, write guard/rollback decision, actual write 보류 | 양호 |
| Phase E5 | 현재 Page 024 | read-only sidecar를 session-only preview 초기값으로 연결 | 양호: read-only + session-only 유지 |

---

## 3. 문서화된 Page 흐름

| Page | 문서 | 상태 | 한 줄 의미 |
| ---: | --- | --- | --- |
| 013 | `2026-05-12_v3k_page_013_session_only_ui_preview_plan.md` | 완료 | GUI preview를 session-only로 분리 |
| 014 | `2026-05-12_v3k_page_014_preview_launcher_exposure_plan.md` | 완료 | Alt+V launcher 노출 |
| 015 | `2026-05-12_v3k_page_015_gui_preview_closeout_plan.md` | 완료 | C2 GUI preview closeout |
| 016 | `2026-05-12_v3k_page_016_phase_d_formula_global_boundary_plan.md` | 완료 | formula/global runtime boundary 고정 |
| 017 | `2026-05-12_v3k_page_017_phase_d1_formula_global_dryrun_plan.md` | 완료 | dry-run adapter 추가 |
| 018 | `2026-05-12_v3k_page_018_phase_d2_formula_runtime_hook_decision_plan.md` | 완료 | runtime hook 보류 결정 |
| 019 | `2026-05-12_v3k_page_019_phase_e0_runtime_activation_gap_review_plan.md` | 완료 | 다음 후보를 GUI sidecar로 선택 |
| 020 | `2026-05-12_v3k_page_020_phase_e1_gui_sidecar_persistence_design_plan.md` | 완료 | sidecar path/schema design |
| 021 | `2026-05-12_v3k_page_021_phase_e2_gui_sidecar_schema_validator_plan.md` | 완료 | schema validator |
| 022 | `2026-05-12_v3k_page_022_phase_e3_gui_sidecar_readonly_loader_plan.md` | 완료 | read-only loader |
| 023 | `2026-05-12_v3k_page_023_phase_e4_gui_sidecar_write_guard_plan.md` | 완료 | write guard/rollback decision |
| 024 | `2026-05-12_v3k_page_024_phase_e5_readonly_sidecar_preview_init_plan.md` | 완료 | read-only sidecar preview init |
| 025 | `2026-05-12_v3k_page_025_phase_e6_sidecar_tempfile_writer_plan.md` | 예정 | tempfile-only writer prototype 검토 |

---

## 4. 전체 리뷰 결론

현재 흐름은 초기 목표와 정합적이다.

- V3 기능을 한 번에 broad merge하지 않고 작은 guard 단계로 나누고 있다.
- Kiwoom runtime은 유지되고 있다.
- LS증권 직접 의존성은 들어오지 않았다.
- DB/sidecar/live runtime write는 금지 상태를 유지하고 있다.
- Page 024는 write 없이 read-only sidecar 값을 session-only preview 초기값으로만 제한했으므로 목표에 부합한다.

다만 아직 완료가 아닌 항목은 남아 있다.

- actual GUI sidecar writer
- production DB read/cutover
- live Kiwoom runtime dry-run hook
- analyzer output trading decision 연동
- formula/global runtime hook

이 항목들은 “누락”이 아니라 의도적으로 보류한 고위험 runtime 활성화 항목이며, 각 항목은 별도 guard/rollback/smoke를 통과한 뒤에만 진행해야 한다.
