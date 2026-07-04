# 2026-07-01 AI Strategy Loop 연구/개발 커밋 핸드오프 기록

## 목적

`STOM_Version_2U_C`에서 파생된 `STOM_Version_2U_C-ai-strategy-loop` 흐름 이후 진행된 process-research 조건식 연구/개발/문서화/검증 산출물을 커밋 가능한 단위로 정리한다. 실제 작업 브랜치는 `loop/process-research-pipeline`이며, 이번 정리에서 코드/테스트, 연구 문서, evidence artifacts를 분리 커밋했다. 이 문서 자체의 freshness 보강 커밋이 추가될 수 있으므로 최종 HEAD는 `git log -1 --oneline` 결과를 권위값으로 둔다.

## 브랜치 관계

| 기준 | 값 |
|---|---|
| 현재 브랜치 | `loop/process-research-pipeline` |
| 최종 HEAD 확인 | `git log -1 --oneline` |
| 로컬 `STOM_Version_2U_C-ai-strategy-loop` merge-base | `45c7e8d46916af03dd3e739ff54962b54b8492c9` |
| 로컬 ai-strategy-loop 대비 ahead/behind | `git rev-list --left-right --count STOM_Version_2U_C-ai-strategy-loop...HEAD`로 최종 확인 |
| `origin/STOM_Version_2U_C-ai-strategy-loop` merge-base | `17cae9046fbb1bca1c08983d0ddbfe92858c9ecc` |
| origin ai-strategy-loop 대비 ahead/behind | `git rev-list --left-right --count origin/STOM_Version_2U_C-ai-strategy-loop...HEAD`로 최종 확인 |
| `STOM_Version_2U_C` merge-base | `8006cd937611e917b08dd28f8add2e2c5aed7dba` |

## 최근 커밋 맥락

| Commit | 제목 | 의미 |
|---|---|---|
| `942e8b28` | 조건식 연구 검증 산출물 보존 | process-research v2 실전 검증 artifacts, receipts, HTML/screenshot, quality gates 보존 |
| `833bc650` | 조건식 연구 기록과 핸드오프 문서 정리 | condition research docs, passports, research run reports, branch handoff docs 보존 |
| `332106f2` | 조건식 연구 컨텍스트팩과 다중 후보 루프 개선 | Research Prompt Context Pack, Analysis Card v2, multi-hypothesis loop, dashboard/tests 개선 |
| `a57a61a93` | 울트라골 최종 스냅샷 갱신 | 이전 Ultragoal/연구 상태 snapshot 정리 |
| `47798adce` | 프로세스 연구 벤치마크 우선 실행 | process-research 실행/검증 기반 |

## 최종 worktree 상태 요약

| 분류 | 상태 | 처리 방침 |
|---|---|---|
| committed code/tests/docs/artifacts | `332106f2`, `833bc650`, `942e8b28` | 이번 연구/개발/검증 산출물로 보존 |
| remaining `.gjc` | untracked runtime state | GJC session/Ultragoal runtime audit trail, 일반 커밋 제외 |
| remaining `.omo` | untracked drafts/evidence/plans 대량 | WAL/로그/스크린샷/과거 evidence가 섞여 별도 inventory 전까지 커밋 제외 |
| protected runtime paths | 0 변경 | 커밋 금지 경로 변경 없음 |

상세 인벤토리는 `docs/research/condition_research/2026-07-01_uncommitted_inventory_and_commit_plan.md`가 기준이다.

## 개발된 코드/프로세스 핵심

| 영역 | 파일 | 핵심 내용 |
|---|---|---|
| Prompt Context Pack | `ai_strategy_loop/brain/prompt.py` | STOM 변수/규칙 원천, full parent buy/sell code, sha256, 분석 카드, prompt budget을 하나의 연구 컨텍스트로 구성 |
| Research policy | `ai_strategy_loop/controller/condition_discovery.py` | process-research/promotion-review authority, Analysis Card v2, prompt maturity, validation provenance, evidence health |
| Candidate generation | `cli/condition_generator.py` | multi-hypothesis candidate pack, strict validation, parent code propagation, diagnostic fallback demotion |
| Research loop | `cli/research_loop.py` | context_pack_id/candidate_pack_id/hypothesis_id/mutation_axis/fallback metadata와 공식 백테스트 결과 연결 |
| Ranking | `cli/research_ranking.py` | advisory ranking, prompt/fallback/result provenance 보존 |
| Dashboard | `ai_strategy_loop/dashboard/frontend/panels-analysis.jsx`, `docs/process_flow.html` | 연구 흐름, context pack, branch tree, prompt receipts, fallback/promotion blocker 관측 |
| Tests | `tests/unit/test_research_prompt_contracts.py`, `tests/unit/test_condition_*`, `tests/unit/test_research_loop.py` | full-code prompt contract, authority, candidate pack, research loop 검증 |

## 2026-07-01 실전 검증 연구 요약

| 항목 | 값 |
|---|---|
| run id | `process_research_v2_validation_20260701` |
| 시작 seed | `rr8_12_turnover_min_902=1.5` |
| engine | 64 성공 |
| fallback | 미발생, receipt 기록 |
| 후보 수 | 4개 |
| 산출물 | `artifacts/process-research-validation-20260701/` |
| 결과 보고서 | `docs/research/condition_research/research_runs/process_research_v2_validation_20260701_result.md` |
| HTML 보고서 | `artifacts/process-research-validation-20260701/process_research_validation_report.html` |

### 공식 결과

| 후보 | Reject filter | Profit | MDD | Trades | 판단 |
|---|---|---:|---:|---:|---|
| baseline | parent | 518,822 | 20.54 | 175 | 기준 |
| cand001 | `시가총액 < 700 and 등락율 < 3.0` | 518,822 | 20.54 | 175 | no-op에 가까움 |
| cand002 | `체결강도 < 120` | 419,904 | 14.68 | 121 | MDD 개선, strength ladder 후보 |
| cand003 | `등락율 >= 7.2` | -25,668 | 12.56 | 55 | 과도한 차단, 후순위 |
| cand004 | `거래대금증감 < -5_000_000_000` | 439,000 | 5.0 | 36 | 가장 강한 risk-control branch |

## 현재 제한 사항과 어려움

| 제한/어려움 | 영향 | 대응 |
|---|---|---|
| 후보가 아직 buy-side reject filter 중심 | MDD는 줄지만 거래수/수익이 같이 줄 수 있음 | sell-only repair lane 추가 |
| cand004는 MDD는 우수하나 거래수 36으로 작음 | 즉시 승격 불가 | threshold ladder로 균형점 탐색 |
| deterministic/non-LLM 후보 fallback 흔적 | prompt maturity를 과대평가할 위험 | diagnostic fallback으로만 기록, prompt credit 분리 |
| 대량 `.omo` evidence가 untracked 상태 | 커밋 범위 혼탁 | 이번 커밋에서는 보류하고 별도 inventory 필요 |
| `.gjc` runtime state가 untracked | workflow state가 소스와 섞일 위험 | 일반 커밋 제외 |
| protected runtime path 제약 | DB/log/graph 등은 소스 커밋 대상 아님 | protected path status check 유지 |

## 계속 진행해야 할 연구

1. `거래대금증감` threshold ladder: `-2B`, `-3B`, `-4B`, `-5B`, `-6B` 계열.
2. `체결강도 < 120` 완화 ladder: `<100`, `<110`, `<120`, `<130`, `<140`.
3. sell-only repair lane: parent buy는 고정하고 sell 조건식만 변경.
4. sell mutation axis: trailing give-back, hard stop, hold-time stop, orderflow exit, MA breakdown.
5. 단독 효과 확인 전 buy/sell paired repair 금지.
6. promotion-review는 생성 없이 frozen/fresh holdout, OOS/WF, slippage advisory, evidence health만 검토.

## 커밋 결과

1. 코드/테스트 커밋 완료: `332106f2 조건식 연구 컨텍스트팩과 다중 후보 루프 개선`.
2. 연구 문서 커밋 완료: `833bc650 조건식 연구 기록과 핸드오프 문서 정리`.
3. evidence artifacts 커밋 완료: `942e8b28 조건식 연구 검증 산출물 보존`.
4. 제외 유지: `.gjc/`, `.omo/` 대량 evidence, `__pycache__/`, protected runtime paths.

## 최종 검증 결과

| 검증 | 결과 |
|---|---|
| `pytest tests/unit/test_research_prompt_contracts.py tests/unit/test_condition_discovery_policy.py tests/unit/test_condition_generator.py tests/unit/test_research_loop.py tests/unit/dashboard/test_dashboard_ui_remodel.py -q` | 149 passed in 11.46s |
| `python -m py_compile ai_strategy_loop/brain/prompt.py ai_strategy_loop/controller/condition_discovery.py cli/condition_generator.py cli/research_loop.py cli/research_ranking.py tests/unit/test_research_prompt_contracts.py tests/unit/test_condition_discovery_policy.py tests/unit/test_condition_generator.py tests/unit/test_research_loop.py tests/unit/dashboard/test_dashboard_ui_remodel.py` | 통과 |
| `git diff --check` | 통과 |
| protected path status | 출력 없음, 변경 없음 |
