# 2026-07-01 파일 인벤토리와 커밋 정리 기록

## 상태 요약

이 문서는 커밋 전 인벤토리와 커밋 후 남은 파일 처분을 함께 기록한다. 목적은 `git add -A` 없이 안전하게 선별 커밋한 근거와, 최종 worktree에 남긴 세션/OMO evidence의 이유를 한 곳에서 확인하게 하는 것이다.

| 항목 | 상태 | 판단 |
|---|---|---|
| current branch | `loop/process-research-pipeline` | `STOM_Version_2U_C-ai-strategy-loop` 흐름의 연구/개발 정리 브랜치 |
| 완료 커밋 | `332106f2`, `833bc650`, `942e8b28` | 코드/테스트, 연구 문서, evidence artifacts를 분리 커밋 |
| 최종 HEAD 확인 | `git log -1 --oneline` 사용 | 이 문서 자체의 freshness 보강 커밋이 추가될 수 있어 명령 결과를 권위값으로 둔다 |
| committed tracked changes | 코드/테스트/문서/artifacts | 이번 process-research v2 프로세스 개선과 연구 검증 evidence |
| remaining untracked groups | `.gjc`, `.omo` | GJC session state와 OMO 과거/별도 evidence라 일반 커밋 제외 |
| protected runtime path 변경 | 0 | protected path check에서 변경 없음 |

## Historical pre-commit snapshot — 당시 modified tracked files

아래 12개는 커밋 전 인벤토리 시점에 git이 추적 중이며 수정되어 있던 파일이다. 현재는 `332106f2` 코드/테스트 커밋과 `833bc650` 문서 커밋으로 정리 완료되었다.

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

## Post-commit remaining groups — 최종 보류 분류

| 그룹 | 현재 상태 | 판단 |
|---|---|---|
| `.gjc` | untracked session/workflow state | GJC runtime state이므로 일반 소스 커밋 제외. Ultragoal ledger/checkpoint는 runtime audit trail로 유지 |
| `.omo` | untracked drafts/evidence/plans 대량 | 일부 연구 맥락은 유용하지만 sqlite WAL/로그/스크린샷/과거 evidence가 섞여 있어 별도 OMO inventory 없이는 커밋하지 않음 |
| `artifacts` | committed | `942e8b28`에서 연구/검증 산출물 보존 커밋 완료 |
| `docs` | committed + 이 freshness patch | `833bc650`에서 문서 정리 커밋 완료, 이후 stale wording만 보강 |
| `tests` | committed | `332106f2`에서 테스트 커밋 완료 |

## 이번 연구와 직접 관련해 커밋된 문서

| 경로 | 역할 | 처리 결과 |
|---|---|---|
| `docs/research/condition_research/2026-06-30_condition_research_knowledge_system.md` | Condition Passport/문서 관리 체계 | `833bc650`에 포함 |
| `docs/research/condition_research/2026-06-30_next_improved_process_research_plan.md` | 다음 개선 연구 계획 | `833bc650`에 포함 |
| `docs/research/condition_research/2026-07-01_process_research_v2_handoff_and_sell_axis.md` | 전체 핸드오프, sell-axis 방향, 파일 정리 | `833bc650`, `0d9591d5`, `d640f98d`에 포함 |
| `docs/research/condition_research/2026-07-01_uncommitted_inventory_and_commit_plan.md` | 파일 인벤토리와 커밋 후 보류 상태 | `833bc650`, `0d9591d5`, `d640f98d`에 포함 |
| `docs/update_log/2026-07-01_ai_strategy_loop_branch_handoff_commit_record.md` | 브랜치/커밋/제한사항/다음 연구 핸드오프 | `833bc650`, `0d9591d5`에 포함 |
| `docs/research/condition_research/condition_passports/` | seed/comparator Condition Passport | `833bc650`에 포함 |
| `docs/research/condition_research/research_runs/` | plan/management/result report | `833bc650`에 포함 |
| `docs/research/condition_research/auto_reports/` | 이전 process research 자동 보고서 | `833bc650`에 포함 |

## 이번 연구와 직접 관련해 커밋된 artifacts

| 경로 | 역할 | 처리 결과 |
|---|---|---|
| `artifacts/process-research-validation-20260701/research_context_pack.json` | full Context Pack | `942e8b28`에 포함 |
| `artifacts/process-research-validation-20260701/research_context_pack_prompt.md` | prompt용 Context Pack | `942e8b28`에 포함 |
| `artifacts/process-research-validation-20260701/analysis_cards.jsonl` | Analysis Card v2 | `942e8b28`에 포함 |
| `artifacts/process-research-validation-20260701/candidate_cards.jsonl` | multi-hypothesis 후보 카드 | `942e8b28`에 포함 |
| `artifacts/process-research-validation-20260701/prompt_mutation_receipts.jsonl` | prompt/authority receipt | `942e8b28`에 포함 |
| `artifacts/process-research-validation-20260701/full_period_backtest_receipts.json` | 공식 백테스트 결과 receipt | `942e8b28`에 포함 |
| `artifacts/process-research-validation-20260701/engine_fallback_receipt.json` | 64/32 fallback 정책 receipt | `942e8b28`에 포함 |
| `artifacts/process-research-validation-20260701/safety_receipt.json` | research-only safety receipt | `942e8b28`에 포함 |
| `artifacts/process-research-validation-20260701/process_research_validation_report.html` | HTML 보고서 | `942e8b28`에 포함 |
| `artifacts/process-research-validation-20260701/process_research_validation_report.png` | 브라우저 검증 screenshot | `942e8b28`에 포함 |
| `artifacts/process-research-validation-20260701/quality_gate_G001.json` 등 | Ultragoal quality gate | `942e8b28`에 포함 |
| `artifacts/process-research-validation-20260701/__pycache__/` | Python bytecode | 정리 완료, 커밋 제외 |

## Historical commit split plan — 실행 완료된 분리 기준

### Commit 1 — 코드와 테스트, 완료됨

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

### Commit 2 — 연구 문서 체계, 완료됨

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

### Commit 3 — 연구 evidence artifacts, 완료됨

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
| 코드/테스트 커밋 | 완료: `332106f2 조건식 연구 컨텍스트팩과 다중 후보 루프 개선` |
| 연구 문서 커밋 | 완료: `833bc650 조건식 연구 기록과 핸드오프 문서 정리` |
| 연구 evidence artifacts 커밋 | 완료: `942e8b28 조건식 연구 검증 산출물 보존` |
| 대량 `.omo` evidence 선별 | 보류, 별도 inventory 필요 |
| artifacts 중 `__pycache__` 제거/무시 처리 | 완료 |
| `.gjc` runtime state | 커밋 제외, Ultragoal runtime audit trail로 유지 |

## 최종 검증 명령

```powershell
pytest tests/unit/test_research_prompt_contracts.py tests/unit/test_condition_discovery_policy.py tests/unit/test_condition_generator.py tests/unit/test_research_loop.py tests/unit/dashboard/test_dashboard_ui_remodel.py -q
python -m py_compile ai_strategy_loop/brain/prompt.py ai_strategy_loop/controller/condition_discovery.py cli/condition_generator.py cli/research_loop.py cli/research_ranking.py tests/unit/test_research_prompt_contracts.py tests/unit/test_condition_discovery_policy.py tests/unit/test_condition_generator.py tests/unit/test_research_loop.py tests/unit/dashboard/test_dashboard_ui_remodel.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup "*.db" backtest/graph .omx/reports "v3k_settings*.json" _v3k_sidecar/v3k_gui_settings.json
```

## 남은 untracked 처리 방침

- `.gjc/`: 현재 세션 Ultragoal 상태와 ledger이므로 커밋하지 않는다.
- `.omo/`: 대량 과거 evidence와 WAL/로그/스크린샷이 섞여 있다. 별도 OMO evidence inventory를 만든 뒤 필요한 일부만 선별 커밋한다.
- protected runtime paths: 변경 없음. 계속 커밋 금지.
