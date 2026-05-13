# V3K Page075 worktree entrypoint alignment 계획

## 목적

Page074에서 `AGENTS.md`에 V3K 목표 entrypoint를 추가했지만, 같은 파일의 worktree map은 이전 `wt-2uc` archive layout을 가리키고 있었다. 현재 실제 worktree는 5개이며, V3K 목표를 이어갈 때 2U_C와 V3/V3U lane을 혼동하지 않도록 branch-local entrypoint와 `git worktree list` 결과를 맞춘다.

## 현재 실제 worktree map

```text
STOM_V/          -> STOM_Version_2
STOM_V.wt-2u/    -> STOM_Version_2U
STOM_V.wt-3/     -> STOM_Version_3
STOM_V.wt-3u/    -> STOM_Version_3U
STOM_V.wt-dev/   -> STOM_Version_2U_C
```

`STOM_V.wt-2uc/`는 현재 active worktree가 아니며 archive lane을 다시 만들려면 사용자 명시 지시가 필요하다.

## 변경 계획

- `AGENTS.md`의 stale `wt-2uc` active map을 5-worktree layout으로 교체한다.
- V3 work excluded 문장은 formal V2 wave에만 적용된다는 점을 명확히 한다.
- `scripts/audit_v3k_worktree_entrypoint_alignment.py`로 `git worktree list`와 `AGENTS.md`의 map이 일치하는지 검증한다.
- `scripts/run_v3k_audit_suite.py`에 worktree entrypoint alignment audit을 추가한다.

## 검증

```powershell
python scripts/audit_v3k_worktree_entrypoint_alignment.py
python scripts/run_v3k_audit_suite.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _v3k_sidecar _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
```

## 실행하지 않는 범위

이 페이지는 문서와 검증 entrypoint만 정렬한다. 실제 worktree 생성/삭제, branch checkout 변경, approval gate execution, USER_ACK, DB write, sidecar write, KHOPENAPI connect/login, live runtime 변경은 수행하지 않는다.

