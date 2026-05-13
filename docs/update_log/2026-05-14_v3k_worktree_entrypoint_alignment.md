# V3K worktree entrypoint alignment

`V3K_WORKTREE_ENTRYPOINT_ALIGNMENT`

## 결론

`AGENTS.md`의 worktree map을 현재 실제 5-worktree layout과 맞췄다. 이제 `STOM_Version_2U_C` entrypoint는 공식 V2/2U/3/3U lane과 V3K custom lane을 정확히 구분한다.

## 현재 layout

| Path | Branch | Role |
| --- | --- | --- |
| `STOM_V/` | `STOM_Version_2` | V2 공식 유지 / root orchestration |
| `STOM_V.wt-2u/` | `STOM_Version_2U` | V2 pyd-free 유지 |
| `STOM_V.wt-3/` | `STOM_Version_3` | V3 공식 ingress |
| `STOM_V.wt-3u/` | `STOM_Version_3U` | V3 pyd-free |
| `STOM_V.wt-dev/` | `STOM_Version_2U_C` | Kiwoom 유지 V3K custom/backport |

`STOM_V.wt-2uc/`는 현재 active worktree가 아니다.

## 의미

- V2 formal wave와 V3K custom lane을 혼동하지 않는다.
- `STOM_Version_2U_C`는 V3 branch가 아니라 Kiwoom 유지 custom lane이다.
- V3K 목표는 `V3 features + Kiwoom retained`이며 LS Securities REST/TR/REAL 직접 의존은 제외한다.
- 실제 approval gate execution은 여전히 `0/6`이다.

## 검증

추가된 audit:

```powershell
python scripts/audit_v3k_worktree_entrypoint_alignment.py
```

통합 검증:

```powershell
python scripts/run_v3k_audit_suite.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _v3k_sidecar _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
```

## 다음 단계

worktree map은 정렬되었지만 V3K final goal은 아직 완료가 아니다. 다음 실제 진행은 첫 gate의 정확 승인 문구가 필요하다.

```text
I approve gui-sidecar-write-await-user-approval only
```

