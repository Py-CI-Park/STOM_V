# V3K-PHASE-E6: sidecar tempfile-only writer prototype

작성일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`

---

## 1. 작업 목적

f51 playbook 기준 다음 1단계는 A1/Page025다. 목적은 GUI sidecar actual write를 허용하는 것이 아니라, Page 023에서 고정한 guard 조건을 tempfile directory 안에서만 prototype smoke로 검증하는 것이다.

따라서 이 단계는 persistence 기능이 아니다. 실제 repo `_v3k_sidecar/` 파일, 운영 `_database/setting.db`, Kiwoom 주문/청산/live runtime, formula/global runtime hook, analyzer trading decision은 변경하지 않았다.

---

## 2. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `scripts/smoke_v3k_gui_sidecar_tempfile_writer.py` | tempfile-only writer prototype smoke 추가 |
| `scripts/audit_v3k_gui_sidecar_write_guard.py` | E6 문서와 prototype smoke 존재/계약 검증 추가 |
| `scripts/audit_v3k_verify_1b_closure.py` | closure checklist에 tempfile writer prototype smoke 반영 |
| `docs/plans/2026-05-12_v3k_page_025_phase_e6_sidecar_tempfile_writer_plan.md` | Page 025 완료 기록으로 갱신 |
| `docs/plans/2026-05-12_v3k_page_026_phase_h_h1_kiwoom_dryrun_hook_plan.md` | 다음 A2/H-1 계획 추가 |
| `docs/CARRY_FORWARD_REGISTRY.md` | `V3K-PHASE-E6` 기록 추가 |

---

## 3. Prototype contract

`scripts/smoke_v3k_gui_sidecar_tempfile_writer.py`는 다음 contract를 검증한다.

1. writer target은 repo 내부일 수 없다.
2. invalid payload는 파일 생성 전에 reject한다.
3. valid payload만 tempfile directory 안에서 atomic replace 대상이 된다.
4. 기존 valid file이 있으면 backup-before-replace가 수행된다.
5. replace 실패 시 target 내용은 이전 상태로 보존된다.
6. temp file은 실패 후 누출되지 않는다.
7. corrupt existing sidecar는 자동 overwrite하지 않고 reject한다.
8. 모든 검증 전후 repo artifact status는 동일해야 한다.

---

## 4. 검증 결과

필수 smoke:

```powershell
python scripts/smoke_v3k_gui_sidecar_tempfile_writer.py
```

검증 메시지:

```text
v3k GUI sidecar tempfile-only writer prototype smoke passed
atomic write, backup-before-replace, rollback, corruption rejection verified
```

---

## 5. Actual write go/no-go

결론: **repo sidecar actual write는 계속 보류**한다.

이유:

- Page 025는 tempfile-only prototype이다.
- 운영 파일에 대한 실제 write는 사용자 명시 승인, backup/rollback 정책, artifact 관리 정책, post-write monitoring 기준을 별도 단계로 요구한다.
- `audit_v3k_verify_1b_closure.py`의 `Actual GUI sidecar write implementation`은 계속 `USER_APPROVAL_REQUIRED`에 남긴다.

---

## 6. 다음 단계

다음은 f51 playbook의 A2다.

```text
Phase H H-1 — Kiwoom dry-run hook 모듈 설계
```

H-1은 KHOPENAPI 호환 환경 없이도 hook 단위 설계와 no-GUI smoke를 진행할 수 있다. H-2/H-3부터는 KHOPENAPI 환경과 사용자 승인 gate가 필요하므로 자동 진행하지 않는다.
