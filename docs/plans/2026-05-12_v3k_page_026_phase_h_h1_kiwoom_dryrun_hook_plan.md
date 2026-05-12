# V3K Page 026 — Phase H H-1 Kiwoom dry-run hook 모듈 설계 계획

작성일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`

기준 문서:
- `docs/update_log/2026-05-12_v3k_ralph_command_playbook.md`
- `docs/plans/2026-05-12_v3k_phase_h_live_kiwoom_dryrun_plan.md`
- `docs/update_log/2026-05-12_v3k_phase_e6_sidecar_tempfile_writer.md`

---

## 0. 목적

Page 026의 목적은 f51 playbook A2에 해당하는 `Phase H H-1`을 수행하는 것이다.

H-1은 KHOPENAPI 호환 환경 없이 진행 가능한 낮은 위험 단계다. 목표는 Kiwoom live runtime에 직접 연결하지 않고, dry-run hook 모듈과 unit smoke, KHOPENAPI sentinel audit를 설계하는 것이다.

---

## 1. In-scope

| Step | 작업 | 완료 조건 |
| ---: | --- | --- |
| 026-1 | hook 모듈 설계 | `strategy/v3k_kiwoom_dryrun_hook.py` 신설 |
| 026-2 | no-GUI unit smoke | `scripts/smoke_v3k_phase_h_hook_unit.py` 신설 |
| 026-3 | KHOPENAPI sentinel audit | `scripts/audit_v3k_phase_h_env_check.py` 신설 |
| 026-4 | 보존 원칙 검증 | Kiwoom 주문/청산/live runtime diff 0건 |
| 026-5 | 다음 gate 결정 | H-2/H-3은 KHOPENAPI 환경 + 사용자 승인 전까지 보류 |

현재 진행률:

```text
Page 026: [░░░░░░░░░░░░░░░░░░░░] 0 / 5 = 0%
```

---

## 2. Out-of-scope

- KHOPENAPI 실제 connect/login
- live dry-run 1회 실행
- feature flag ON 전환
- Kiwoom 주문/청산/live runtime 코드 변경
- operating `_database/` write
- LS Securities 직접 의존

---

## 3. 반복 OMX 명령

```powershell
omx ralph "force: V3K 단계별 지속 진행을 1단계만 수행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. 반드시 docs/update_log/2026-05-12_v3k_ralph_command_playbook.md, docs/update_log/2026-05-12_v3k_cd6f5bd_to_page024_flow_review.md, docs/CARRY_FORWARD_REGISTRY.md, docs/update_log/2026-05-12_v3k_progress_metric_methodology.md, docs/update_log/2026-05-12_v3k_mission_closeout_procedure.md, 최신 docs/update_log/*checkpoint* 문서를 먼저 읽고 현재 HEAD 기준 아직 완료되지 않은 다음 단계 1개만 선택한다. f51de818 playbook의 추천 순서를 따르되, 2U_C에서는 verify_release_sync.py 대신 scripts/verify_nonrelease_sync.py를 사용한다. 사용자 승인, KHOPENAPI 환경, DB cutover, ON 전환, live runtime, 운영 _database write가 필요한 단계에서는 실행하지 말고 gate 사유와 다음 승인 조건만 문서화한다. 실행 가능한 낮은 위험 단계라면 구현/문서/update_log/CARRY_FORWARD_REGISTRY 갱신/한국어 Lore commit까지 완료한다. 모든 단계에서 Kiwoom 주문/청산/live runtime 미변경, LS Securities 직접 의존 금지, feature flag default-OFF, 운영 _database/ 미변경, DB 파일 commit 금지, STOM CLI surface 보존을 강제한다. 완료 시 py_compile, 신규 smoke, V3K smoke 전체, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB/sidecar artifact status를 통과시키고 전체 페이지/현재 페이지/남은 페이지/진행률/다음 omx 명령을 보고한다."
```
