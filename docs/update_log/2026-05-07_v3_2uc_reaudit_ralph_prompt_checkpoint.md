# V3 -> 2U_C 재탐색 Ralph 프롬프트 체크포인트

작성일: 2026-05-07 KST
목적: 반복적인 V3 -> 2U_C Kiwoom 유지 backport 재탐색 루프를 다시 실행하기 전에, 실제로 사용할 프롬프트와 운영 기준을 문서로 고정한다.

## 1. 판단

이 문서를 먼저 commit하고 이어서 `omx ralph --no-deslop` 재탐색 루프를 실행하는 방식이 가장 안전하다.

이유는 다음과 같다.

- 이전 작업은 여러 commit과 update log를 통해 page 단위로 진행되었고, 재탐색 기준이 문서에 남아 있을수록 중단 후 복구가 쉽다.
- 직전 Ralph run에서 no-more-safe-candidates 결론은 도달했지만, commit hook과 PowerShell 한글 인코딩 문제로 문서/커밋 정리가 흔들렸다.
- 따라서 이번에는 실행 전 프롬프트 자체를 먼저 문서화해, 다른 세션이나 후속 agent도 같은 기준으로 이어갈 수 있게 한다.
- 실제 실행 프롬프트는 한글 깨짐을 피하기 위해 영어/ASCII 중심으로 유지하고, 해설과 commit message는 한글로 남긴다.

## 2. 현재 기준 상태

```text
전체 진행률        [####################] 100.0%  62 / 62 page
no-more closure    [####################] 100.0%   1 /  1 page
남은 safe 후보     [--------------------]   0.0%   0 /  0 page
```

현재 완료 기준:

- `STOM_Version_2`: root orchestration lane
- `STOM_Version_2U_C`: active Kiwoom custom/backport lane
- 최신 no-more 문서: `docs/update_log/2026-05-07_v3_2uc_no_more_safe_candidates_handoff.md`
- allowlist 기준 문서: `docs/update_log/2026-05-06_2uc_v3_backport_allowlist_plan.md`
- 완료된 실제 code 반영:
  - BP-005A: progressbar 표시 보정
  - BP-006A: `strategy/analyzer_risk.py` dormant module 보존
- 현재 판단: 추가 safe candidate 없음. 단, 사용자가 원하면 같은 기준으로 재탐색 루프를 다시 실행할 수 있다.

## 3. 왜 `ralph --no-deslop`인가

| 선택지 | 판단 | 이유 |
|---|---|---|
| `omx ralph --no-deslop` | 추천 | 단일 owner가 read-only inventory, 후보 gate, patch/hold, docs, commit, final guard를 순차 관리하기 좋다. |
| `omx autopilot` | 비추천 | `ralplan -> ralph -> code-review` 전체 pipeline이라 현재처럼 이미 문서화된 반복 backport 점검에는 과하다. |
| `omx team` | 비추천 | 이전 Phase 6 문서에서 worker pane startup 불안정 기록이 있다. |
| `omx explore` | 보조/비추천 | Windows POSIX wrapper 문제로 실패 기록이 있어 main loop로 쓰지 않는다. |
| `omx sparkshell` | 검증 보조 | release sync, status, grep, diff inventory 같은 read-only 검증에 사용한다. |

## 4. 최종 실행 프롬프트

아래 프롬프트를 그대로 `omx ralph --no-deslop`에 전달한다.

```text
Goal: Re-run the STOM V3-to-2U_C selective backport exhaustion loop from the current no-more-safe-candidates baseline.

Start from:
- docs/update_log/2026-05-07_v3_2uc_no_more_safe_candidates_handoff.md
- docs/update_log/2026-05-06_2uc_v3_backport_allowlist_plan.md

Current baseline:
- Root worktree: C:/System_Trading/STOM/STOM_V on STOM_Version_2
- Active 2U_C worktree: C:/System_Trading/STOM/STOM_V.wt-dev on STOM_Version_2U_C
- V3 source worktree: C:/System_Trading/STOM/STOM_V.wt-3 on STOM_Version_3
- V3U worktree: C:/System_Trading/STOM/STOM_V.wt-3u on STOM_Version_3U
- Current documented baseline: 62 / 62 pages, no-more-safe-candidates closure complete

Hard rules:
- Preserve Kiwoom Securities support in STOM_Version_2U_C.
- Do NOT create STOM_Version_3U_C.
- Do NOT use git add -A.
- Do NOT use git rebase or git reset --hard.
- Do NOT commit runtime artifacts: _database, _log, *.db, backtest/graph/*.
- Do NOT broad-merge V3.
- Do NOT introduce LS API assumptions into 2U_C.
- Do NOT perform DB migration without a separate migration spec.
- Do NOT wire AnalyzerRisk or any dormant module into runtime without a new BP-ID, target call-site evidence, dict_findex/array-shape evidence, and tests.
- Use exact git add paths only.
- Use Korean commit titles and Korean markdown commit bodies with Lore-style trailers.

Required loop:
1. Verify root and 2U_C are clean.
2. Run read-only inventory of STOM_Version_3 vs STOM_Version_2U_C.
3. Exclude already completed or held items:
   - BP-005A completed
   - BP-006A completed
   - BP-001 hold
   - BP-003 hold
   - BP-002/BP-004 no-op or hold
   - documented no-more-safe-candidates result
4. Search for any remaining candidate that is all of:
   - broker-neutral
   - DB-neutral
   - pyd-neutral
   - Kiwoom-compatible
   - small enough for a micro-candidate
   - mock-testable
5. If a safe candidate exists, assign the next BP-ID and process exactly one candidate through:
   - Page 1 read-only inventory
   - Page 2 decision
   - Page 3 minimal patch or hold
   - Page 4 docs sync
   - Page 5 final guard
6. Commit root and 2U_C documentation at each page.
7. Commit 2U_C code only if Page 3 applies a safe patch.
8. If no safe candidate exists, update the no-more handoff, verify clean state, run release sync for both root and 2U_C, verify forbidden runtime artifacts are not tracked, verify STOM_Version_3U_C does not exist, and stop.

Every report and document must include:
- total progress
- current page progress
- remaining pages
- progress bars
- next OMX command

```

## 5. PowerShell/tmux 실행 예시

PowerShell 한글 인코딩 문제를 줄이기 위해 prompt는 ASCII로 유지하고, tmux 새 창에서 실행한다.

```powershell
$script = 'C:\Temp\stom_omx_ralph_reaudit_ascii.ps1'

@'
Set-Location 'C:\System_Trading\STOM\STOM_V'

omx ralph --no-deslop @'
Goal: Re-run the STOM V3-to-2U_C selective backport exhaustion loop from the current no-more-safe-candidates baseline.

Start from:
- docs/update_log/2026-05-07_v3_2uc_no_more_safe_candidates_handoff.md
- docs/update_log/2026-05-06_2uc_v3_backport_allowlist_plan.md

Current baseline:
- Root worktree: C:/System_Trading/STOM/STOM_V on STOM_Version_2
- Active 2U_C worktree: C:/System_Trading/STOM/STOM_V.wt-dev on STOM_Version_2U_C
- V3 source worktree: C:/System_Trading/STOM/STOM_V.wt-3 on STOM_Version_3
- V3U worktree: C:/System_Trading/STOM/STOM_V.wt-3u on STOM_Version_3U
- Current documented baseline: 62 / 62 pages, no-more-safe-candidates closure complete

Hard rules:
- Preserve Kiwoom Securities support in STOM_Version_2U_C.
- Do NOT create STOM_Version_3U_C.
- Do NOT use git add -A.
- Do NOT use git rebase or git reset --hard.
- Do NOT commit runtime artifacts: _database, _log, *.db, backtest/graph/*.
- Do NOT broad-merge V3.
- Do NOT introduce LS API assumptions into 2U_C.
- Do NOT perform DB migration without a separate migration spec.
- Do NOT wire AnalyzerRisk or any dormant module into runtime without a new BP-ID, target call-site evidence, dict_findex/array-shape evidence, and tests.
- Use exact git add paths only.
- Use Korean commit titles and Korean markdown commit bodies with Lore-style trailers.

Required loop:
1. Verify root and 2U_C are clean.
2. Run read-only inventory of STOM_Version_3 vs STOM_Version_2U_C.
3. Exclude already completed or held items:
   - BP-005A completed
   - BP-006A completed
   - BP-001 hold
   - BP-003 hold
   - BP-002/BP-004 no-op or hold
   - documented no-more-safe-candidates result
4. Search for any remaining candidate that is all of:
   - broker-neutral
   - DB-neutral
   - pyd-neutral
   - Kiwoom-compatible
   - small enough for a micro-candidate
   - mock-testable
5. If a safe candidate exists, assign the next BP-ID and process exactly one candidate through:
   - Page 1 read-only inventory
   - Page 2 decision
   - Page 3 minimal patch or hold
   - Page 4 docs sync
   - Page 5 final guard
6. Commit root and 2U_C documentation at each page.
7. Commit 2U_C code only if Page 3 applies a safe patch.
8. If no safe candidate exists, update the no-more handoff, verify clean state, run release sync for both root and 2U_C, verify forbidden runtime artifacts are not tracked, verify STOM_Version_3U_C does not exist, and stop.

Every report and document must include:
- total progress
- current page progress
- remaining pages
- progress bars
- next OMX command

'@

Write-Host 'OMX Ralph re-audit command exited. Review output above.'
'@ | Set-Content -LiteralPath $script -Encoding UTF8

tmux new-window -d -n stom-ralph-redo "powershell -NoProfile -NoExit -ExecutionPolicy Bypass -File '$script'"
```

## 6. 모니터링 명령

```powershell
tmux list-windows
tmux capture-pane -t 31:stom-ralph-redo.0 -p -S -300
```

window 이름으로 잡히지 않으면 아래처럼 index를 확인한다.

```powershell
tmux list-windows -t 31
tmux capture-pane -t 31:1.0 -p -S -300
```

## 7. 실행 전후 검증 명령

```powershell
omx sparkshell powershell -NoProfile -Command "python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py; python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V.wt-dev; git -C C:/System_Trading/STOM/STOM_V status --short; git -C C:/System_Trading/STOM/STOM_V.wt-dev status --short"
```

추가 guard:

```powershell
git -C C:/System_Trading/STOM/STOM_V.wt-dev ls-files -- _database _log '*.db' 'backtest/graph/*'
git -C C:/System_Trading/STOM/STOM_V branch --list STOM_Version_3U_C
```

## 8. 이어서 진행할 때의 stop condition

Ralph가 아래 중 하나에 도달하면 멈춘다.

1. 새 safe candidate를 찾지 못해 no-more handoff만 갱신하고 검증을 통과한다.
2. 새 candidate가 발견되어 하나의 BP-ID만 Page 1~5로 완료한다.
3. broker-neutral, DB-neutral, pyd-neutral, Kiwoom-compatible, mock-testable 조건 중 하나라도 충족하지 못해 hold 문서만 남긴다.
4. root 또는 2U_C가 clean하지 않거나 release sync가 실패해 사용자 확인이 필요한 상태가 된다.

## 9. 다음 단계

이 문서가 root와 2U_C에 commit되면 다음 단계는 위 PowerShell/tmux 실행 예시를 사용해 `omx ralph --no-deslop` 재탐색 루프를 시작하는 것이다.
