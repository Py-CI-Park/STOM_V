# 2026-07-01 커밋 전 파일 인벤토리와 정리 계획

## 상태 요약

이 문서는 현재 worktree에 남아 있는 커밋되지 않은 파일을 연구/개발/증거/세션 상태로 분류한다. 목적은 `git add -A` 없이 안전하게 선별 커밋하거나 별도 보관 판단을 할 수 있게 하는 것이다.

| 항목 | 개수 | 판단 |
|---|---:|---|
| current branch | `loop/process-research-pipeline` | 로컬 `STOM_Version_2U_C-ai-strategy-loop` 기준 4 commits ahead |
| current HEAD | `a57a61a93` | 커밋 전 기준 HEAD |
| modified tracked files | 12 | 이번 process-research v2 프로세스 개선 코드/테스트/문서 인덱스 후보 |
| untracked files/groups | 442 | 연구 문서, artifacts, `.omo` 과거 evidence, `.gjc` 세션 상태가 혼재 |
| top-level untracked groups | 5 | `.gjc`, `.omo`, `artifacts`, `docs`, `tests` |
| protected runtime path 변경 | 0 | 별도 protected path check에서 변경 없음 |

## Modified tracked files — 커밋 후보 A

아래 12개는 현재 git이 추적 중이며 수정된 파일이다. 하나의 코드 커밋으로 묶을 수 있지만, 문서와 대시보드 변경까지 포함되므로 최종 리뷰 후 분리 커밋도 가능하다.

| 파일 | 역할 | 권장 처리 |
|---|---|---|
| `ai_strategy_loop/brain/prompt.py` | Research Prompt Context Pack, full parent condition code, STOM source inclusion | 코드 커밋 후보 |
| `ai_strategy_loop/controller/condition_discovery.py` | process mode authority, Analysis Card v2, prompt maturity, promotion-review boundary | 코드 커밋 후보 |
| `ai_strategy_loop/dashboard/frontend/panels-analysis.jsx` | dashboard observability | 코드/대시보드 커밋 후보 |
| `cli/condition_generator.py` | multi-hypothesis candidate pack, strict validation, full parent code propagation | 코드 커밋 후보 |
| `cli/research_loop.py` | orchestration, candidate/backtest receipts, research metadata wiring | 코드 커밋 후보 |
| `cli/research_ranking.py` | ranking metadata, prompt/fallback/advisory reason | 코드 커밋 후보 |
| `docs/process_flow.html` | process visualization | 문서/대시보드 커밋 후보 |
| `docs/research/condition_research/README.md` | research docs index | 문서 커밋 후보 |
| `tests/unit/dashboard/test_dashboard_ui_remodel.py` | dashboard behavior coverage | 테스트 커밋 후보 |
| `tests/unit/test_condition_discovery_policy.py` | policy/authority/analysis card tests | 테스트 커밋 후보 |
| `tests/unit/test_condition_generator.py` | candidate pack / strict validation tests | 테스트 커밋 후보 |
| `tests/unit/test_research_loop.py` | orchestration/receipt tests | 테스트 커밋 후보 |

## Untracked groups — 커밋 전 분류

| 그룹 | 개수 | 예시 | 권장 처리 |
|---|---:|---|---|
| `.gjc` | 1 | `.gjc/` | GJC workflow/session state. 일반 코드 커밋 제외 |
| `.omo` | 252 | `.omo/evidence/tmap-walkforward/...`, `.omo/plans/...` | 이번 run과 직접 무관한 과거/별도 evidence가 대량 섞임. 별도 inventory 전까지 커밋 제외 |
| `artifacts` | 147 | `artifacts/process-research-validation-20260701/`, `artifacts/g001-*` 등 | evidence 커밋 여부를 선별 판단. `__pycache__` 제외 |
| `docs` | 40 | condition research docs, update logs | durable 연구 문서는 문서 커밋 후보. update_log는 별도 검토 |
| `tests` | 1 | `tests/unit/test_research_prompt_contracts.py` | 코드 커밋 후보 |

## 이번 연구와 직접 관련 있는 신규 문서

| 경로 | 역할 | 권장 처리 |
|---|---|---|
| `docs/research/condition_research/2026-06-30_condition_research_knowledge_system.md` | Condition Passport/문서 관리 체계 | 커밋 후보 |
| `docs/research/condition_research/2026-06-30_next_improved_process_research_plan.md` | 다음 개선 연구 계획 | 커밋 후보 |
| `docs/research/condition_research/2026-07-01_process_research_v2_handoff_and_sell_axis.md` | 전체 핸드오프, sell-axis 방향, 파일 정리 | 커밋 후보 |
| `docs/research/condition_research/2026-07-01_uncommitted_inventory_and_commit_plan.md` | 현재 파일 인벤토리 | 커밋 후보 |
| `docs/update_log/2026-07-01_ai_strategy_loop_branch_handoff_commit_record.md` | 브랜치/커밋/제한사항/다음 연구 핸드오프 | 커밋 후보 |
| `docs/research/condition_research/condition_passports/` | seed/comparator Condition Passport | 커밋 후보 |
| `docs/research/condition_research/research_runs/` | plan/management/result report | 커밋 후보 |
| `docs/research/condition_research/auto_reports/` | 이전 process research 자동 보고서 | 커밋 후보이나 범위가 넓어 별도 검토 가능 |

## 이번 연구와 직접 관련 있는 신규 artifacts

| 경로 | 역할 | 권장 처리 |
|---|---|---|
| `artifacts/process-research-validation-20260701/research_context_pack.json` | full Context Pack | evidence 커밋 후보 |
| `artifacts/process-research-validation-20260701/research_context_pack_prompt.md` | prompt용 Context Pack | evidence 커밋 후보 |
| `artifacts/process-research-validation-20260701/analysis_cards.jsonl` | Analysis Card v2 | evidence 커밋 후보 |
| `artifacts/process-research-validation-20260701/candidate_cards.jsonl` | multi-hypothesis 후보 카드 | evidence 커밋 후보 |
| `artifacts/process-research-validation-20260701/prompt_mutation_receipts.jsonl` | prompt/authority receipt | evidence 커밋 후보 |
| `artifacts/process-research-validation-20260701/full_period_backtest_receipts.json` | 공식 백테스트 결과 receipt | evidence 커밋 후보 |
| `artifacts/process-research-validation-20260701/engine_fallback_receipt.json` | 64/32 fallback 정책 receipt | evidence 커밋 후보 |
| `artifacts/process-research-validation-20260701/safety_receipt.json` | research-only safety receipt | evidence 커밋 후보 |
| `artifacts/process-research-validation-20260701/process_research_validation_report.html` | HTML 보고서 | evidence 커밋 후보 |
| `artifacts/process-research-validation-20260701/process_research_validation_report.png` | 브라우저 검증 screenshot | evidence 커밋 후보 |
| `artifacts/process-research-validation-20260701/quality_gate_G001.json` 등 | Ultragoal quality gate | evidence 커밋 후보 |
| `artifacts/process-research-validation-20260701/__pycache__/` | Python bytecode | 커밋 제외 |

## 커밋 분리 추천

### Commit 1 — 코드와 테스트

목적: process-research v2 기능 개선 자체를 기록한다.

포함 후보:

```text
ai_strategy_loop/brain/prompt.py
ai_strategy_loop/controller/condition_discovery.py
ai_strategy_loop/dashboard/frontend/panels-analysis.jsx
cli/condition_generator.py
cli/research_loop.py
cli/research_ranking.py
tests/unit/test_research_prompt_contracts.py
tests/unit/test_condition_discovery_policy.py
tests/unit/test_condition_generator.py
tests/unit/test_research_loop.py
tests/unit/dashboard/test_dashboard_ui_remodel.py
docs/process_flow.html
```

### Commit 2 — 연구 문서 체계

목적: 사람과 AI가 연구 맥락을 재구성할 수 있는 durable docs를 남긴다.

포함 후보:

```text
docs/research/condition_research/README.md
docs/research/condition_research/2026-06-30_condition_research_knowledge_system.md
docs/research/condition_research/2026-06-30_next_improved_process_research_plan.md
docs/research/condition_research/2026-07-01_process_research_v2_handoff_and_sell_axis.md
docs/research/condition_research/2026-07-01_uncommitted_inventory_and_commit_plan.md
docs/research/condition_research/condition_passports/
docs/research/condition_research/research_runs/
```

### Commit 3 — 연구 evidence artifacts

목적: 실전 검증 run을 재검토할 수 있는 증거를 보존한다.

포함 후보:

```text
artifacts/process-research-validation-20260701/*.json
artifacts/process-research-validation-20260701/*.jsonl
artifacts/process-research-validation-20260701/*.md
artifacts/process-research-validation-20260701/*.html
artifacts/process-research-validation-20260701/*.png
artifacts/process-research-validation-20260701/*.txt
```

제외:

```text
artifacts/process-research-validation-20260701/__pycache__/
```

## 현재 정리 상태

| 항목 | 상태 |
|---|---|
| 연구 프로세스/실행 결과 문서화 | 완료 |
| 매도 조건식 연구 방향 문서화 | 완료 |
| 커밋되지 않은 파일 그룹 분류 | 완료 |
| 실제 git staging/commit | 미수행 |
| 대량 `.omo` evidence 선별 | 미수행, 별도 inventory 필요 |
| artifacts 중 `__pycache__` 제거/무시 처리 | 미수행 |

## 권장 다음 조치

1. 위 Commit 1/2/3 순서로 선별 staging한다.
2. `.gjc/`, `.omo/`, `__pycache__/`는 바로 커밋하지 않는다.
3. 커밋 전 검증을 다시 실행한다.

```powershell
pytest tests/unit/test_research_prompt_contracts.py tests/unit/test_condition_discovery_policy.py tests/unit/test_condition_generator.py tests/unit/test_research_loop.py tests/unit/dashboard/test_dashboard_ui_remodel.py -q
python -m py_compile ai_strategy_loop/brain/prompt.py ai_strategy_loop/controller/condition_discovery.py cli/condition_generator.py cli/research_loop.py cli/research_ranking.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup "*.db" backtest/graph .omx/reports "v3k_settings*.json" _v3k_sidecar/v3k_gui_settings.json
```
