# AI Loop Worktree Inventory and Cleanup Note

- Date: 2026-06-24
- Primary worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
- AI loop base branch: `STOM_Version_2U_C-ai-strategy-loop`
- Documentation commit: this note is contained in the current local AI loop HEAD
- Functional dashboard fix base: `17cae9046fbb1bca1c08983d0ddbfe92858c9ecc` (`루프 연구실 히트맵 가시성 보정`)
- Follow-up development branch: `loop/dashboard-followup-20260624` is to be fast-forwarded from the local AI loop HEAD for resumed work.

## Purpose

대시보드 연구/개발 중 병렬 작업을 위해 열어 둔 보조 worktree를 즉시 삭제하지 않고 보존한다. 이 기록은 `wt-dev`의 AI loop 브랜치에서 남기는 정리 메모이며, 보조 worktree의 현재 역할, 왜 보존하는지, 그리고 추후 정리 전에 확인해야 할 조건을 명확히 한다.

## What changed in this session

| Item | Result | Reason |
|---|---|---|
| `wt-dev` branch reset | `STOM_Version_2U_C-ai-strategy-loop`로 복귀 | 사용자가 새 개발 브랜치는 나중에 다시 요청하고, 지금은 AI loop 브랜치에서 이어가겠다고 지시했다. |
| temporary development branch | `loop/dashboard-followup-20260624 @ 17cae904` 보존 | 삭제하지 않고 나중에 사용자가 다시 요청할 수 있도록 남겼다. |
| follow-up development branch restart | `loop/dashboard-followup-20260624`를 local AI loop HEAD로 fast-forward한 뒤 `wt-dev`에서 checkout | 사용자가 보존 개발 브랜치를 AI loop에서 다시 시작하도록 요청했다. |
| `wt-2u` branch alignment | `STOM_Version_2U @ 3b7a3aeb`로 복귀 | `wt-2u`는 2U 기준선 보존 worktree이므로 AI loop 브랜치와 분리했다. |
| auxiliary worktrees | `dashboard-next`, `webbt`, `evo-governance` 모두 보존 | 사용자가 병렬 연구/개발 worktree로 기억하고 있어 즉시 삭제하지 않는다. |
| cleanup documentation | 이 문서 추가 | 후속 정리 시 어떤 worktree를 왜 남겼는지 다시 확인할 수 있게 한다. |

## Branch / worktree clarification

| Worktree | Current branch after follow-up | Current local state | Current role | Note |
|---|---|---:|---|---|
| `STOM_V.wt-dev` | `loop/dashboard-followup-20260624` | fast-forwarded from local `STOM_Version_2U_C-ai-strategy-loop`; origin AI loop 대비 문서 커밋 포함 | AI loop에서 재시작한 후속 개발 worktree | 기준점은 `STOM_Version_2U_C-ai-strategy-loop`이고, 새 변경은 follow-up branch에서 진행한다. |
| `STOM_V.wt-2u` | `STOM_Version_2U` | `3b7a3aeb` | 보존해야 하는 2U 기준 worktree | 2U 기준선이다. AI loop 브랜치와 같은 브랜치가 아니다. origin 대비 `ahead 1` 상태는 기존 2U 로컬 커밋 때문이다. |

Git worktree는 한 worktree가 다른 worktree의 하위 폴더처럼 파일시스템상 파생되는 구조가 아니라 같은 저장소의 별도 checkout이다. 다만 아래 보조 worktree들은 운영상 `wt-dev`/AI loop 연구를 병렬로 진행하기 위해 만든 sibling worktree로 취급한다. 즉 "wt-dev에서 파생"이라는 표현은 Git 내부 구조가 아니라 작업 운용상 출발점과 목적을 설명하는 말이다.

## 2U / 2U_C / AI loop relationship

| Branch | Meaning | Worktree currently using it |
|---|---|---|
| `STOM_Version_2U` | 2U 기준선. 2U worktree에서 보존해야 하는 원 기준 브랜치 | `STOM_V.wt-2u` |
| `STOM_Version_2U_C` | 2U_C 기준선. 이 lane의 비릴리즈/커스텀 기준 | no active worktree in this note |
| `STOM_Version_2U_C-ai-strategy-loop` | 2U_C 기준 위에 AI strategy loop, dashboard research, loop telemetry 계열 작업을 얹은 진행 브랜치 | base branch for `STOM_V.wt-dev` follow-up work |

따라서 현재 확인 결론은 다음과 같다. `wt-2u`는 2U 브랜치에서 개발/보존 중이고, `wt-dev`는 2U_C 계열의 AI loop HEAD에서 fast-forward한 `loop/dashboard-followup-20260624` 브랜치로 후속 개발을 다시 시작한다.

## Preserved auxiliary worktrees

| Worktree | Branch | HEAD | Evidence vs `STOM_Version_2U_C-ai-strategy-loop` | Current decision |
|---|---|---:|---|---|
| `STOM_V.wt-dashboard-next` | `lazycodex/dashboard-ui-phase3-feedback-20260619` | `1958a8ac` | committed branch delta is already contained in AI loop (`base ahead 7 / branch ahead 0` after this doc commit); tracked clean; untracked `.gjc/` remains | Preserve for historical dashboard Phase 3/4 evidence until reviewed. |
| `STOM_V.wt-webbt` | `feature/webbt-followup-gates-20260618` | `19d82beb` | committed branch delta is already contained in AI loop (`base ahead 59 / branch ahead 0` after this doc commit); tracked clean | Preserve for WebBT follow-up history until explicit cleanup. |
| `STOM_V.wt-evo-governance` | `feature/evo-dashboard-condition-discovery-governance` | `210bba85` | committed branch delta is already contained in AI loop (`base ahead 6 / branch ahead 0` after this doc commit), but worktree has 21 tracked dirty files and 9 untracked entries | Preserve. Do not delete until dirty changes are reviewed, migrated, committed, or explicitly discarded. |

## Why the auxiliary worktrees are not deleted now

| Worktree | Why keep it now | Cleanup risk |
|---|---|---|
| `wt-dashboard-next` | Dashboard Phase 3/4 evidence and `.gjc` workflow state may still be useful for audit/review. | Removing it without inspecting `.gjc/` may lose local workflow context. |
| `wt-webbt` | It is clean, but it may still be useful as a WebBT follow-up reference checkout. | Low technical risk, but removal should still be an explicit cleanup decision. |
| `wt-evo-governance` | It contains uncommitted tracked and untracked work around config, loop/controller state, dashboard frontend, launch config, and tests. | High risk. Removing it now would discard or hide live unreviewed work. |

## Cleanup backlog

| Item | Action required before cleanup |
|---|---|
| `wt-dashboard-next` | Decide whether untracked `.gjc/` evidence must be copied, archived, or discarded. |
| `wt-webbt` | Confirm no historical quick-access need remains, then remove worktree and branch separately if desired. |
| `wt-evo-governance` | Inspect dirty files and untracked advisory/condition-discovery work before any removal. |

## Guardrails

- Preserve `wt-2u` as the 2U baseline worktree.
- Continue new follow-up development from `wt-dev` on `loop/dashboard-followup-20260624`, which is based on the local `STOM_Version_2U_C-ai-strategy-loop` HEAD.
- Keep `STOM_Version_2U_C-ai-strategy-loop` as the AI loop base branch unless a later explicit branch request changes that.
- Do not remove `dashboard-next`, `webbt`, or `evo-governance` worktrees without an explicit cleanup decision.
- Treat `wt-evo-governance` as protected until its dirty changes are reviewed.
