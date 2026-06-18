# Dirty Worktree Split Inventory - STOM Reorganization Page 3

Captured: 2026-06-18T22:06:15+09:00
Worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
Source command: `git status --short --untracked-files=all`

## Completeness

| Metric | Count |
|---|---:|
| Dirty lines before Page 1~3 evidence files | 443 |
| Tracked modified lines | 24 |
| Untracked lines | 419 |
| Cleanup performed | 0 |
| Staged files | 0 |
| Deleted files | 0 |

Every dirty line from the 443-line baseline is represented below either as an explicit path or a glob group with an explicit count.

## Bucketed Inventory

| Count | Git kind | Bucket | Path or glob | Proposed action |
|---:|---|---|---|---|
| 191 | untracked | evidence artifact | `.omo/evidence/tmap-walkforward/*` | keep; review in research evidence commit group |
| 103 | untracked | research template | `ai_strategy_loop/tmap/templates/*` | stage later only with matching tests/evidence |
| 51 | untracked | evidence artifact | `.omo/evidence/*` | keep; group by originating plan before commit |
| 22 | untracked | docs/update_log | `docs/update_log/*` | stage later in research journal/doc groups |
| 12 | untracked | test | `tests/unit/*` | stage later with corresponding source changes |
| 11 | untracked | plan | `.omo/plans/*` | stage later as plan/history docs if still relevant |
| 10 | untracked | workflow state | `.gjc/*` | investigate; likely workflow state, do not stage by default |
| 3 | untracked | test | `tests/unit/dashboard/*` | stage later with dashboard API/UI changes |
| 2 | tracked | generated bundle | `ai_strategy_loop/dashboard/frontend/bundle/*` | stage only with dashboard frontend source that generated it |
| 1 | untracked | research source change | `ai_strategy_loop/fitness/lift.py` | investigate/stage later with tests |
| 1 | untracked | research source change | `ai_strategy_loop/fitness/backtest_timeseries.py` | investigate/stage later with tests |
| 1 | untracked | research source change | `ai_strategy_loop/scripts/overnight_anchor_mutation.py` | investigate/stage later with evidence |
| 1 | untracked | research source change | `ai_strategy_loop/scripts/ab_discovery_eval.py` | investigate/stage later with evidence |
| 1 | untracked | dashboard API/UI change | `ai_strategy_loop/dashboard/research_records.py` | stage later with API tests |
| 1 | untracked | dashboard API/UI change | `ai_strategy_loop/dashboard/frontend/evolution-gui-parity-panel.jsx` | stage later with dashboard tests and rebuilt bundle |
| 1 | untracked | dashboard API/UI change | `ai_strategy_loop/dashboard/evolution_gui_parity.py` | stage later with API tests |
| 1 | untracked | research source change | `ai_strategy_loop/brain/feature_importance_feedback.py` | investigate/stage later with tests |
| 1 | untracked | dashboard API/UI change | `ai_strategy_loop/dashboard/frontend/research-records-panel.jsx` | stage later with dashboard tests and rebuilt bundle |
| 1 | tracked | workflow state | `.omo/start-work/ledger.jsonl` | keep; commit only if execution record is needed |
| 1 | tracked | research source change | `ai_strategy_loop/autopsy/analyze.py` | stage later with research/autopsy tests |
| 1 | tracked | workflow state | `.omo/boulder.json` | keep; do not include in product/source PR unless needed |
| 1 | untracked | test | `tests/fixtures/refine_gate/hcase_post_hoc.json` | stage later with refine gate tests |
| 1 | untracked | research source change | `ai_strategy_loop/tmap/refine_gate.py` | stage later with refine gate tests |
| 1 | untracked | research source change | `ai_strategy_loop/scripts/tmap_autopsy_loop.py` | stage later with tests/evidence |
| 1 | untracked | research source change | `ai_strategy_loop/scripts/research_presets.py` | stage later with tests/evidence |
| 1 | untracked | research source change | `ai_strategy_loop/tmap/mutator.py` | stage later with mutator tests |
| 1 | untracked | research source change | `ai_strategy_loop/scripts/tmap_multiband_discovery.py` | stage later with evidence |
| 1 | tracked | research source change | `ai_strategy_loop/autopsy/summarize.py` | stage later with autopsy tests |
| 1 | tracked | dashboard API/UI change | `ai_strategy_loop/dashboard/frontend/lab.html` | stage later with dashboard frontend group |
| 1 | tracked | dashboard API/UI change | `ai_strategy_loop/dashboard/frontend/index.html` | stage later with dashboard frontend group |
| 1 | tracked | dashboard API/UI change | `ai_strategy_loop/dashboard/frontend/verdict.html` | stage later with dashboard frontend group |
| 1 | tracked | dashboard API/UI change | `ai_strategy_loop/dashboard/frontend/pro.html` | stage later with dashboard frontend group |
| 1 | tracked | dashboard API/UI change | `ai_strategy_loop/dashboard/frontend/app.jsx` | stage later with dashboard frontend group and rebuilt bundle |
| 1 | tracked | research source change | `ai_strategy_loop/controller/loop.py` | stage later with controller tests |
| 1 | tracked | research source change | `ai_strategy_loop/config.py` | stage later with config tests |
| 1 | tracked | dashboard API/UI change | `ai_strategy_loop/dashboard/frontend/STOM AI Dashboard.html` | stage later with dashboard frontend group |
| 1 | tracked | dashboard API/UI change | `ai_strategy_loop/dashboard/app.py` | stage later with dashboard API tests |
| 1 | tracked | dashboard API/UI change | `ai_strategy_loop/dashboard/research_api.py` | stage later with research records/API tests |
| 1 | untracked | draft | `.omo/drafts/*` | keep; commit only if plan trace is wanted |
| 1 | tracked | research source change | `ai_strategy_loop/brain/prompts/p5_template_hypothesis.md` | stage later with generation tests |
| 1 | tracked | research source change | `ai_strategy_loop/brain/generator.py` | stage later with generation tests |
| 1 | tracked | research source change | `ai_strategy_loop/brain/prompt.py` | stage later with generation tests |
| 1 | tracked | test | `tests/unit/*` | stage later with source group |
| 1 | tracked | research source change | `ai_strategy_loop/scripts/gen_template_hypothesis.py` | stage later with template tests |
| 1 | tracked | research source change | `ai_strategy_loop/scripts/build_process_flow_html.py` | stage later with generated docs/process_flow.html |
| 1 | tracked | docs | `docs/process_flow.html` | generated doc; stage only with build_process_flow_html.py |
| 1 | tracked | research source change | `ai_strategy_loop/tmap/tendency.py` | stage later with tendency tests |

## Proposed Future Staging Groups

| Group | Include | Exclude for now | Korean commit title suggestion |
|---|---|---|---|
| workflow trace | selected `.omo/plans/*`, `.omo/evidence/stom-reorg-20260618/*`, maybe `.omo/start-work/ledger.jsonl` | `.gjc/*` unless explicitly needed | `작업 재시작 안전 스냅샷 정리` |
| research engine changes | `ai_strategy_loop/brain/*`, `ai_strategy_loop/controller/loop.py`, `ai_strategy_loop/config.py`, `ai_strategy_loop/tmap/*.py`, `ai_strategy_loop/scripts/*.py`, matching `tests/unit/*` | generated dashboard bundle | `조건식 연구 엔진 변경 정리` |
| dashboard API/UI | `ai_strategy_loop/dashboard/*.py`, `ai_strategy_loop/dashboard/frontend/*.jsx`, `*.html`, matching dashboard tests | research templates unless required | `조건식 연구 대시보드 기록 화면 정리` |
| generated dashboard bundle | `ai_strategy_loop/dashboard/frontend/bundle/app.js`, `manifest.json` | standalone bundle-only commit | `대시보드 번들 재생성 반영` |
| research evidence | `.omo/evidence/tmap-walkforward/*`, `.omo/evidence/condition-*/*` | protected/runtime paths | `조건식 연구 증거 산출물 정리` |
| update logs | `docs/update_log/*.md`, `docs/research/**` if applicable | `_database/`, `_log/`, `*.db` | `조건식 연구 진행 기록 정리` |
| tests | `tests/unit/*`, `tests/unit/dashboard/*`, `tests/fixtures/*` | tests without source/evidence link | `조건식 연구 검증 테스트 정리` |

## Generated Bundle Tie-Back

| Generated file group | Source tie-back | Required verification before staging |
|---|---|---|
| `ai_strategy_loop/dashboard/frontend/bundle/app.js` | `ai_strategy_loop/dashboard/frontend/app.jsx`, `research-records-panel.jsx`, `evolution-gui-parity-panel.jsx`, dashboard API changes | `node build-app.mjs`, `node track-z-harness.mjs`, `node check-missing-imports.mjs`, focused dashboard tests |
| `ai_strategy_loop/dashboard/frontend/bundle/manifest.json` | same frontend build inputs | same as above |
| `docs/process_flow.html` | `ai_strategy_loop/scripts/build_process_flow_html.py` | script-specific regeneration/check command to be defined before commit |

## Protected Runtime Classification

| Pattern | Baseline count | Action |
|---|---:|---|
| `_database/` | 0 | protected-do-not-touch |
| `_database_v3k_shadow/` | 0 | protected-do-not-touch |
| runtime `_log/` | 0 by explicit pathspec | protected-do-not-touch |
| `backup/` | 0 | protected-do-not-touch |
| `*.db` | 0 | protected-do-not-touch |
| `backtest/graph/` | 0 | protected-do-not-touch |
| `.omx/reports/` | 0 | protected-do-not-touch |
| `v3k_settings*.json` | 0 | protected-do-not-touch |
| `_v3k_sidecar/v3k_gui_settings.json` | 0 | protected-do-not-touch |

`docs/update_log/*` appears in dirty status, but it is documentation and not the protected runtime `_log/` directory.

## QA Results

| Scenario | Result |
|---|---|
| inventory completeness | 443 baseline dirty lines represented by grouped rows above. |
| protected runtime classification | protected patterns listed and all explicit protected pathspec counts are 0. |
| no mutation | no staging, deletion, stash, checkout, branch creation, reset, rebase, push, or merge performed. |

Cleanup receipt:
- No owned process/server/browser/tmux/temp directory remains.
- No files outside `.omo/boulder.json`, `.omo/start-work/ledger.jsonl`, the selected plan, and `.omo/evidence/stom-reorg-20260618/*` were modified by this Page 1~3 execution.
