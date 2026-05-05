# V3 Phase 6 team runtime 실행 시도 기록

- 작성일: 2026-05-05
- 작성 시각: 2026-05-05 17:13:19 +09:00
- 작업 위치: `C:\System_Trading\STOM\STOM_V`
- 대상 워크트리: `C:\System_Trading\STOM\STOM_V.wt-3`
- 관련 preflight: `docs/update_log/2026-05-05_v3_phase6_preflight_dry_run.md`
- 실행 전 `STOM_Version_2` HEAD: `0737e59c`
- 실행 전 `STOM_Version_3` HEAD: `0737e59c`

## 1. 목적

이 문서는 Phase 6 본작업 진입을 위해 추천했던 `omx team` 실행 시도와 실패 결과를 기록한다.

Phase 6은 V3 official source intake로 변경량이 크기 때문에 원래는 team runtime으로 lane을 나누는 것이 가장 안전한 추천 경로였다. 하지만 현재 tmux/worker pane startup 단계에서 worker pane이 유지되지 않아 team mode가 시작되지 않았다.

## 2. 실행 전 상태

실행 전 확인:

```text
STOM_Version_2: clean, ahead origin
STOM_Version_3: clean
STOM_V.wt-3 ignored runtime: !! _database/
TMUX: /tmp/psmux-117576/default,62734,0
tmux: 3.3.4
omx: C:\Users\parkc\AppData\Roaming\npm\omx.ps1
```

team runtime 전제인 tmux와 `omx` command 자체는 존재했다.

## 3. 1차 실행: 4-worker team

실행 명령:

```powershell
omx team 4:executor "Phase 6 STOM V3 official source intake: use docs/update_log/2026-05-05_v3_phase6_preflight_dry_run.md as guard; apply V3.0..V3.17 one formal commit at a time; do not use git add -A; preserve protected governance/runtime files; work in C:/System_Trading/STOM/STOM_V.wt-3 on STOM_Version_3; record evidence and stop if marker/ref changes."
```

결과:

```text
[omx:team] worker startup resolution: model=gpt-5.5 thinking_level=xhigh source=explicit
[omx:team] worker startup resolution: model=gpt-5.5 thinking_level=xhigh source=explicit
[omx:team] worker startup resolution: model=gpt-5.5 thinking_level=xhigh source=explicit
[omx:team] worker startup resolution: model=gpt-5.5 thinking_level=xhigh source=explicit
Error: worker pane 3 did not remain present after tmux split-window returned %25
```

판정: team startup 실패. source 변경 없음.

## 4. 2차 실행: 2-worker 축소 team

4-worker 실패 후 headcount를 줄이고 범위를 `STOM V3.0` formal commit gate로 좁혀 재시도했다.

실행 명령:

```powershell
omx team 2:executor "Phase 6 STOM V3 official source intake controlled start: use docs/update_log/2026-05-05_v3_phase6_preflight_dry_run.md as guard. Work in C:/System_Trading/STOM/STOM_V.wt-3 on STOM_Version_3. Prepare exact guarded source-intake steps and start only the STOM V3.0 formal commit gate if safe. Do not use git add -A. Preserve AGENTS.md, docs, .gitignore, _database, _log. Stop and report before applying V3.01+ or if upstream marker/ref changes."
```

결과:

```text
[omx:team] worker startup resolution: model=gpt-5.5 thinking_level=xhigh source=explicit
[omx:team] worker startup resolution: model=gpt-5.5 thinking_level=xhigh source=explicit
Error: worker pane 2 did not remain present after tmux split-window returned %27
```

판정: team startup 실패. source 변경 없음.

## 5. 실패 후 검증

실패 후 확인:

```text
tmux panes:
- %1: leader pane, cwd=C:\System_Trading\STOM\STOM_V
- %4: existing conhost/HUD-like pane, cwd=C:\WINDOWS

team state:
- `.omx/state/team` 아래 활성 team state 없음

git status:
- STOM_Version_2: clean except branch ahead count
- STOM_Version_3: clean
- STOM_V.wt-3 ignored runtime: !! _database/
```

즉, team worker가 실제 작업을 시작하지 못했고 repository/source에는 변화가 없었다.

## 6. 판정

현재 세션에서는 `omx team` runtime이 worker pane startup 단계에서 안정적으로 동작하지 않는다.

따라서 Phase 6 본작업은 다음 둘 중 하나로 진행하는 것이 안전하다.

1. **권장 fallback:** `$ralph ... --no-deslop` 단일-owner 보수 루프에서 `STOM V3.0`부터 한 commit씩 진행
2. **team runtime 복구 후 재시도:** `omx doctor` 또는 team runtime 환경 점검 후 `omx team 1~2:executor` 재시도

## 7. 다음 명령 권고

현재 V3 source 적용을 계속 진행하려면 다음 명령을 추천한다.

```text
$ralph .omx/plans/prd-v3-kickoff-phase-0-11.md .omx/plans/test-spec-v3-kickoff-phase-0-11.md --no-deslop
```

이 fallback은 team pane 장애를 우회하고, 현재 leader session에서 Phase 6을 한 commit씩 진행하는 보수 경로다.

진행 시 첫 작업은 `STOM V3.0` formal commit gate만 수행하고, 그 다음 `V3.01+`로 넘어가기 전에 다시 상태를 보고해야 한다.

## 8. 주의사항

- `git add -A` 금지
- source 적용 전 upstream ref/marker 재확인 유지
- `AGENTS.md`, `.gitignore`, `docs/` 보호
- `_database`, `_log`, `*.db` stage 금지
- official V3 pyd `ui/main_window.pyd` 보존
- pyd 제거는 Phase 10에서만 수행