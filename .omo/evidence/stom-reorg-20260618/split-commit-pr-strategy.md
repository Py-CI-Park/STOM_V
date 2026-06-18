# Split Commit, PR, And Handoff Strategy

Generated: 2026-06-18T23:19:07+09:00  
Plan page: 16  
Status: strategy only. No staging, commit, push, PR, merge, reset, stash, or cleanup was performed.

## Operating Model

| Worktree | Role | Rule |
|---|---|---|
| `wt-dev` | Canonical current research worktree and restart source for this plan | Keep research evidence, `.omo`, update logs, tmap/brain/script changes here until explicitly selected for commit. |
| `wt-webbt` | Clean auxiliary dashboard worktree for future file-disjoint dashboard PR work | Use for dashboard-only implementation slices, then PR-merge and reflect into `wt-dev`. It is not the canonical restart branch. |
| `STOM_Version_2U_C-ai-strategy-loop` | Protected AI evolution dashboard anchor | Update only through reviewed PR merge, not force move, reset, rebase, or direct overwrite. |

## Anchor Catch-Up Sequence

After dirty-state classification and selected commits:

1. Commit selected `wt-dev` changes in explicit groups.
2. Push local `STOM_Version_2U_C-ai-strategy-loop` so GitHub can use it as PR base.
3. Push `lazycodex/tick-sparse-positive-generation-improvement-20260604`.
4. Open PR with `base: STOM_Version_2U_C-ai-strategy-loop` and `compare: lazycodex/tick-sparse-positive-generation-improvement-20260604`.
5. Merge by reviewed PR merge commit.
6. Create the next development branch from the updated `STOM_Version_2U_C-ai-strategy-loop`.
7. Keep `wt-webbt` available as the dashboard-only auxiliary worktree.

## Commit / PR Groups

| Group | Target | Files/globs | Korean commit title | Verification |
|---:|---|---|---|---|
| 1 | `wt-dev` research docs | `.omo/evidence/stom-reorg-20260618/safety-snapshot.txt`, `protected-path-status.txt`, `branch-map.md`, `pr-restart-strategy.md`, `dirty-worktree-inventory.md` | `docs(운영): AI 연구 브랜치 파생 관계 지도화` | `git status --short --branch`; protected path status command. |
| 2 | `wt-dev` research governance | `research-source-inventory.md`, `research-registry.json`, `research-registry.md`, `naming-taxonomy.md` | `docs(연구): 조건식 연구 정본 레지스트리와 네이밍 규칙 추가` | `python -m json.tool .omo/evidence/stom-reorg-20260618/research-registry.json` |
| 3 | `wt-dev` research process | `evidence-lineage-rules.md`, `research-management-process.md`, `official-oos-queue.md`, `branch-attribution-plan.md` | `docs(연구): 증거 계보와 공식 OOS 절차 정리` | Search for `official`, `candidate`, `literal OR`, `if/elif`, `seed bank`. |
| 4 | `wt-dev` dashboard audit docs | `dashboard-inventory.md`, `dashboard-duplicate-audit.md`, `dashboard-visual-error-audit.md`, `dashboard-static-gates.txt`, `dashboard-curl-smoke.txt` | `docs(대시보드): 정보구조와 중복 기능 전수 감사` | `node build-app.mjs`; `node track-z-harness.mjs`; `node check-missing-imports.mjs`. |
| 5 | `wt-dev` QA/PR strategy docs | `dashboard-improvement-backlog.md`, `dashboard-qa-matrix.md`, `split-commit-pr-strategy.md`, final verification artifacts | `docs(대시보드): QA 매트릭스와 PR 분리 전략 정리` | Final verification wave F1~F4. |
| 6 | `wt-webbt` future dashboard implementation PR | `ai_strategy_loop/dashboard/**`, `tests/unit/dashboard/**`, related rebuilt `frontend/bundle/**` only when source changes require it | `feat(대시보드): 연구 기록 라벨과 최신 일지 노출 개선` | Dashboard gates, focused tests, browser QA, `verify_nonrelease_sync.py`. |
| 7 | `wt-dev` future official OOS execution | `.omo/evidence/tmap-walkforward/*official-oos*`, `docs/update_log/YYYY-MM-DD_*`, registry updates | `docs(연구): 저시총 제외 방어 조합 공식 OOS 기록` | Official OOS raw/summary evidence, protected path status, registry JSON validation. |
| 8 | Separate stabilization branch | Backtest contract stabilization files only if later approved | `fix(백테스트): 계약 테스트 안정화` | Full targeted backtest/unit suite; not part of this reorg commit set. |

## Explicit Staging Examples

Use explicit file paths per group. Examples:

```powershell
git add .omo/evidence/stom-reorg-20260618/branch-map.md .omo/evidence/stom-reorg-20260618/pr-restart-strategy.md
git add .omo/evidence/stom-reorg-20260618/research-registry.json .omo/evidence/stom-reorg-20260618/research-registry.md
git add .omo/evidence/stom-reorg-20260618/dashboard-inventory.md .omo/evidence/stom-reorg-20260618/dashboard-duplicate-audit.md
```

Do not stage unrelated dirty files. Do not stage protected runtime paths.

## PR Descriptions

### Research governance PR

Title: `docs(연구): 조건식 연구 정리와 공식 OOS 재시작 기준 확립`

Body outline:

```markdown
## 목적
- STOM 조건식 연구를 registry, naming, evidence lineage, official OOS queue로 재정리합니다.

## 검증
- research-registry JSON parse
- protected path status
- dashboard static gates where applicable

## 제외
- 실제 official OOS 실행 없음
- live/strategy DB 승격 없음
- V3K gate 변경 없음
```

### Dashboard implementation PR in `wt-webbt`

Title: `feat(대시보드): 연구 기록 라벨과 최신 일지 가시성 개선`

Body outline:

```markdown
## 목적
- Research Records, evidence labels, latest update_log visibility, GUI parity visibility를 개선합니다.

## 검증
- node build-app.mjs
- node track-z-harness.mjs
- node check-missing-imports.mjs
- focused pytest
- browser/manual QA artifacts

## worktree
- 개발: wt-webbt
- 반영: reviewed PR merge 후 wt-dev에 merge/fetch로 반영
```

## Handoff Rule

- If the user wants research continuation, resume from `wt-dev` and run the official OOS plan.
- If the user wants dashboard implementation, create a file-disjoint `wt-webbt` feature branch and PR it back.
- If the catch-up PR is too large, split by wave into integration branches while preserving final base `STOM_Version_2U_C-ai-strategy-loop`.
- Never rewrite the protected anchor branch history.
