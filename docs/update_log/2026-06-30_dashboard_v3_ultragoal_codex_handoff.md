# 2026-06-30 V3 대시보드 Ultragoal 완료 및 Codex 핸드오프

## 1. 한 줄 결론

`C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel` 워크트리에서 V3 대시보드 UX/UI maturity 작업은 Ultragoal G001~G007 전체가 완료됐고, 최종 evidence gate까지 통과했다. Codex에서 이어서 작업할 때는 이 워크트리를 기준으로 열고, V2 기본 라우트는 그대로 보존한 채 `/ui/remodel/*` 명시 V3 경로를 확인하면 된다.

## 2. 현재 작업 위치와 브랜치

| 항목 | 값 |
|---|---|
| 실제 작업 워크트리 | `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel` |
| 작업 브랜치 | `feature/dashboard-remodel-20260626` |
| 현재 HEAD | `5a68e2ad` |
| 원본/비교 워크트리 | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| 최초 리모델 기준 zip | `C:/Users/parkc/Downloads/stom-ai-dashboard-frontend-reviewed.zip` |
| 작업 시작 기록 | `docs/update_log/2026-06-26_dashboard_remodel_worktree_intake.md` |
| Ralplan 계획 | `.gjc/_session-019f05e9-d676-7000-9c61-3c206a2d4031/plans/ralplan/019f05e9-d676-7000-9c61-3c206a2d4031/pending-approval.md` |
| Ultragoal state | `.gjc/_session-019f05e9-d676-7000-9c61-3c206a2d4031/ultragoal/goals.json` |
| Ultragoal audit ledger | `.gjc/_session-019f05e9-d676-7000-9c61-3c206a2d4031/ultragoal/ledger.jsonl` |

Codex에서 열 위치:

```text
C:\System_Trading\STOM\STOM_V.wt-dashboard-remodel
```

## 3. 왜 8776에서 새 화면이 안 보일 수 있는가

| URL | 정상 동작 | 설명 |
|---|---|---|
| `http://127.0.0.1:8776/ui/evolution` | V2 화면 | V2는 default로 보존하는 것이 원래 제약이다. |
| `http://127.0.0.1:8776/ui/remodel/condition?demo=reference` | V3 화면 | V3는 explicit opt-in 경로다. |
| `http://127.0.0.1:8776/ui/remodel/backtest?demo=reference` | V3 Backtest | 새 Backtest UX 확인 경로다. |
| `http://127.0.0.1:8776/ui/remodel/chart-replay?demo=reference` | V3 Chart Replay | 새 Replay UX 확인 경로다. |

`stom_dashboard.bat` 기본 URL은 `/ui/evolution`이고 기본 포트도 8770이다. 8776에서 V3를 보려면 포트를 지정하고 V3 명시 URL로 들어가야 한다.

PowerShell 예시:

```powershell
cd C:\System_Trading\STOM\STOM_V.wt-dashboard-remodel
$env:STOM_DASHBOARD_PORT='8776'
$env:STOM_DASHBOARD_NO_BROWSER='1'
$env:STOM_DASHBOARD_NO_PAUSE='1'
.\stom_dashboard.bat
```

CMD 예시:

```bat
cd /d C:\System_Trading\STOM\STOM_V.wt-dashboard-remodel
set STOM_DASHBOARD_PORT=8776
set STOM_DASHBOARD_NO_BROWSER=1
set STOM_DASHBOARD_NO_PAUSE=1
stom_dashboard.bat
```

직접 확인 URL:

```text
http://127.0.0.1:8776/ui/remodel/condition?demo=reference
```

## 4. 작업 흐름 요약

| 단계 | 내용 | 결과 |
|---|---|---|
| 워크트리 생성/인수 | `feature/dashboard-remodel-20260626` 브랜치로 `STOM_V.wt-dashboard-remodel` 작업 시작 | 완료 |
| 외부 reviewed zip intake | `ai_strategy_loop/dashboard/frontend/remodel/`에 격리형 V3 프리뷰 번들 추가 | 완료 |
| FastAPI 라우팅 | `/ui/remodel/{page}` 및 remodel static asset route 추가 | 완료 |
| 기존 V2 보존 | `/ui/evolution`, `/ui/backtest`, `/ui/chart-replay`는 V2 기본 유지 | 완료 |
| 최초 100점 후 UX 재평가 | 안전/증거 중심 점수가 human UX를 놓친 문제 확인 | 완료 |
| Ralplan | V3 UX/UI maturity pending plan 작성 | 완료 |
| Ultragoal Tranche 0 | human UX rubric, storyboards, baseline capture 구축 | 완료 |
| Backtest-first | 조건식 편집/검증/수동 실행/분석 흐름 개선 | 완료 |
| Chart Replay | 빠른 시작, 날짜/종목/전략, playback/timeline, signal log 개선 | 완료 |
| Lab + Condition | 히트맵/후보/성과 판단 구조 개선 | 완료 |
| Workbench + History | 후보 비교와 run inspect/compare/lineage 구조 개선 | 완료 |
| Process + Audit | cockpit 유지, decision funnel, append-only evidence 정리 | 완료 |
| Final evidence gate | 전체 8페이지 검증 및 최종 aggregate receipt 생성 | 완료 |

## 5. Ultragoal 완료 상태

`gjc ultragoal status --json` 기준:

| 항목 | 상태 |
|---|---|
| Ultragoal status | `complete` |
| complete goals | 7 |
| pending | 0 |
| active | 0 |
| failed | 0 |
| blocked | 0 |
| review_blocked | 0 |
| 최종 receipt | G007 `final-aggregate` |
| GJC goal | `complete` |

Goal별 완료 내용:

| Goal | 제목 | 핵심 성과 |
|---|---|---|
| G001 | Tranche 0 human UX rubric baseline | human UX verifier, V2/V3 baseline, Condition/Backtest/Replay storyboards 생성 |
| G002 | Shared IA and Backtest redesign | task frame, compact safety strip, evidence drawer, Backtest select/edit/validate/gated-run/analyze 구현 |
| G003 | Chart Replay redesign | V2식 quick-start/date/symbol/strategy/playback/timeline 직관성 복원, signal log 연동 |
| G004 | Lab and Condition redesign | 큰 히트맵, 값/범례/선택 셀 설명, 후보/성과 primary canvas 구성 |
| G005 | Workbench and History redesign | 후보 선택 funnel, comparison, review handoff, history find/inspect/compare/lineage 구성 |
| G006 | Process and Audit polish | Process cockpit 유지, Audit OOS evidence → Human Decision → Append-Only Ledger funnel 구성 |
| G007 | Final full evidence gate | 전체 8페이지 최종 human UX / visual / compare / safety / browser / review gate 통과 |

## 6. 최종 검증 결과

최종 evidence report:

```text
artifacts/dashboard-human-ux-v3/final-full-verification-report.json
```

요약 수치:

| 검증 | 결과 |
|---|---:|
| Dashboard tests | `939 passed` |
| Human UX rubric | PASS |
| Mean V3 score | `96.89` |
| Mean named V3-V2 delta | `+21.72` |
| Category floor | PASS |
| Visual gate | PASS `100.0` |
| V2/V3 compare | PASS `100.0` |
| Safety audit | PASS `100.0` |
| Browser evidence | passed, 8 actions/routes |
| Forbidden network count | 0 |
| Architect review | `CLEAR / CLEAR / CLEAR`, `APPROVE` |
| Executor QA/red-team | `passed` |
| `git diff --check` | pass |
| protected runtime paths | clean |

최종 명령 기록:

```text
node --check ai_strategy_loop/dashboard/frontend/remodel/src/app.js
python -m pytest tests/unit/test_dashboard*.py tests/unit/dashboard -q
python scripts/verify_dashboard_human_ux_rubric.py --v2-base-url http://127.0.0.1:8776 --v3-base-url http://127.0.0.1:8776 --out artifacts/dashboard-human-ux-v3/final-full-evidence --storyboard artifacts/dashboard-human-ux-v3/storyboards/storyboards.json --viewports 1440x900,1920x1080,1280x720 --tranche final --min-v3-score 90 --min-delta 15
python scripts/verify_dashboard_remodel_visual_gate.py --base-url http://127.0.0.1:8776 --out artifacts/dashboard-human-ux-v3/final-full-visual-gate --min-page-score 95 --min-average-score 97 --timeout-ms 60000
python scripts/verify_dashboard_v2_v3_compare.py --v2-base-url http://127.0.0.1:8776 --v3-base-url http://127.0.0.1:8776 --out artifacts/dashboard-human-ux-v3/final-full-v2-v3-compare --timeout-ms 60000
python scripts/verify_dashboard_safety_audit.py --v2-base-url http://127.0.0.1:8776 --v3-base-url http://127.0.0.1:8776 --out artifacts/dashboard-human-ux-v3/final-full-safety-audit --timeout-ms 60000
git diff --check
git status --short -- _database _database_v3k_shadow _log backup "*.db" backtest/graph .omx/reports "v3k_settings*.json"
```

## 7. 주요 산출물

| 경로 | 역할 |
|---|---|
| `artifacts/dashboard-human-ux-v3/final-full-verification-report.json` | G007 최종 검증 요약 |
| `artifacts/dashboard-human-ux-v3/final-full-quality-gate.json` | Ultragoal checkpoint용 strict quality gate |
| `artifacts/dashboard-human-ux-v3/final-full-browser-evidence.json` | 8개 V3 route selector browser transcript |
| `artifacts/dashboard-human-ux-v3/final-full-evidence/scorecard.json` | human UX rubric 전체 scorecard |
| `artifacts/dashboard-human-ux-v3/final-full-evidence/category-floor-check.json` | category floor invariant check |
| `artifacts/dashboard-human-ux-v3/final-full-visual-gate/scorecard.json` | visual gate scorecard |
| `artifacts/dashboard-human-ux-v3/final-full-v2-v3-compare/compare-scorecard.json` | V2/V3 route/asset/default preservation gate |
| `artifacts/dashboard-human-ux-v3/final-full-safety-audit/safety-scorecard.json` | safety audit scorecard |
| `artifacts/dashboard-human-ux-v3/final-full-ai-slop-cleaner-report.txt` | AI slop cleanup report |
| `ai_strategy_loop/dashboard/frontend/remodel/docs/captures/*.png` | 최종 accepted visual baseline captures |

## 8. 주요 변경 영역

| 영역 | 파일/디렉터리 | 내용 |
|---|---|---|
| Dashboard server | `ai_strategy_loop/dashboard/app.py` | `/ui/remodel/*` 명시 V3 route/static serving, V2 route 보존 |
| V3 frontend | `ai_strategy_loop/dashboard/frontend/remodel/src/app.js` | 8페이지 task-first V3 UI, safety/provenance/evidence drawer, Backtest/Replay/Lab 등 구현 |
| V3 styles | `ai_strategy_loop/dashboard/frontend/remodel/styles/theme.css` | task frame, primary canvas, drawer, chart/heatmap/readability/responsive 스타일 |
| V3 data | `ai_strategy_loop/dashboard/frontend/remodel/src/data.js`, `data/stom-dummy-data.json` | reference/demo data 기반 렌더링 |
| V3 captures | `ai_strategy_loop/dashboard/frontend/remodel/docs/captures/*.png` | final visual gate baseline |
| Verifiers | `scripts/verify_dashboard_human_ux_rubric.py`, `verify_dashboard_remodel_visual_gate.py`, `verify_dashboard_v2_v3_compare.py`, `verify_dashboard_safety_audit.py`, `verify_dashboard_runtime_depth.py`, `verify_dashboard_inventory_gate.py` | human UX / visual / compare / safety / runtime evidence gates |
| Tests | `tests/unit/test_dashboard_human_ux_rubric.py`, `test_dashboard_remodel_static.py`, `test_dashboard_remodel_baseline_contract.py`, route/ws tests | static contract 및 dashboard test coverage |
| Evidence | `artifacts/dashboard-human-ux-v3/**` | tranche별 및 final evidence |
| Update logs | `docs/update_log/2026-06-26...`, `2026-06-27...`, `2026-06-29...`, 이 문서 | 작업 기록 |

## 9. 현재 git status 요약

현재 워크트리는 커밋되지 않은 변경이 많다. Codex에서 이어받을 때 먼저 `git status --short --branch`로 확인한다.

주요 modified:

```text
ai_strategy_loop/dashboard/app.py
ai_strategy_loop/dashboard/frontend/STOM AI Dashboard.html
ai_strategy_loop/dashboard/frontend/app.jsx
ai_strategy_loop/dashboard/frontend/bundle/app.js
ai_strategy_loop/dashboard/frontend/bundle/manifest.json
ai_strategy_loop/dashboard/frontend/cards.jsx
ai_strategy_loop/dashboard/frontend/conn-backend.jsx
ai_strategy_loop/dashboard/frontend/index.html
ai_strategy_loop/dashboard/frontend/lab.html
ai_strategy_loop/dashboard/frontend/pro.html
ai_strategy_loop/dashboard/frontend/sim-tab-root.jsx
ai_strategy_loop/dashboard/frontend/verdict.html
tests/unit/test_dashboard_route_parity.py
tests/unit/test_dashboard_ws.py
```

주요 untracked:

```text
.gjc/
ai_strategy_loop/dashboard/frontend/remodel/
artifacts/
docs/update_log/2026-06-26_dashboard_remodel_worktree_intake.md
docs/update_log/2026-06-27_dashboard_remodel_*.md
docs/update_log/2026-06-27_ultragoal_*.md
docs/update_log/2026-06-28_ultragoal_g001_100point_inventory.md
docs/update_log/2026-06-29_ultragoal_*.md
docs/update_log/2026-06-30_dashboard_v3_ultragoal_codex_handoff.md
scripts/verify_dashboard_*.py
tests/unit/test_dashboard_human_ux_rubric.py
tests/unit/test_dashboard_remodel_baseline_contract.py
tests/unit/test_dashboard_remodel_static.py
```

주의: `.gjc/`와 `artifacts/`는 durable workflow/evidence state다. 커밋 여부는 maintainer 결정 전까지 임의로 stage하지 않는다.

## 10. Codex에서 바로 확인할 체크리스트

서버:

```text
http://127.0.0.1:8776/health
```

V2 default:

```text
http://127.0.0.1:8776/ui/evolution
```

V3 pages:

| 페이지 | URL |
|---|---|
| Condition | `http://127.0.0.1:8776/ui/remodel/condition?demo=reference` |
| Process | `http://127.0.0.1:8776/ui/remodel/process?demo=reference` |
| History | `http://127.0.0.1:8776/ui/remodel/history?demo=reference` |
| Lab | `http://127.0.0.1:8776/ui/remodel/lab?demo=reference` |
| Workbench | `http://127.0.0.1:8776/ui/remodel/workbench?demo=reference` |
| Audit | `http://127.0.0.1:8776/ui/remodel/audit?demo=reference` |
| Backtest | `http://127.0.0.1:8776/ui/remodel/backtest?demo=reference` |
| Chart Replay | `http://127.0.0.1:8776/ui/remodel/chart-replay?demo=reference` |

중점 확인:

| 페이지 | 확인 포인트 |
|---|---|
| Backtest | 큰 buy/sell condition editor, Select → Edit → Validate → Gated Run → Analyze 흐름 |
| Chart Replay | quick start, date/symbol/strategy, sticky playback/timeline, selected bar, synchronized signal log |
| Lab | heatmap 값/범례/선택 셀 narrative, holdout 해석, 변수 중요도 |
| Condition | current generation, BEST candidate, primary charts, export/audit separation |
| Workbench | candidate selection funnel, comparison, review handoff |
| History | find → inspect → compare → lineage |
| Process | payload-driven cockpit, state/map/log/queue/worker/contract hierarchy |
| Audit | OOS evidence → Human Decision → Append-Only Ledger |

## 11. 안전/비범위 조건

반드시 유지:

| 조건 | 설명 |
|---|---|
| V2 default | `/ui/evolution`, `/ui/backtest`, `/ui/chart-replay`는 V2 기본 동작 유지 |
| V3 explicit | V3는 `/ui/remodel/*`에서만 명시 진입 |
| No live order | 실거래 주문 기능 추가 금지 |
| No broker login | 브로커 로그인/계좌 연결 금지 |
| No account trading | 계좌 거래/자산 연동 금지 |
| No hidden export | 숨은 production export 금지 |
| No protected writes | `_database/`, `_log/`, `*.db`, `.omx/reports` 등 보호 경로 쓰기 금지 |
| Reference/demo honesty | `REFERENCE mode`, `REST INERT`, `WebSocket 정적 fixture`, `Human Gate Required`, `Append-Only` 표시 유지 |
| No page-load mutation | `/bt/run`, `/bt/ws_job`, `/sim/ws`, order/broker/account 계열 자동 호출 금지 |

## 12. 다음 Codex 권장 시작 절차

1. 워크트리 열기:

```text
C:\System_Trading\STOM\STOM_V.wt-dashboard-remodel
```

2. 상태 확인:

```powershell
git status --short --branch
gjc ultragoal status --json
```

3. 서버 실행 또는 확인:

```powershell
$env:STOM_DASHBOARD_PORT='8776'
$env:STOM_DASHBOARD_NO_BROWSER='1'
$env:STOM_DASHBOARD_NO_PAUSE='1'
.\stom_dashboard.bat
```

4. V3 직접 확인:

```text
http://127.0.0.1:8776/ui/remodel/condition?demo=reference
```

5. 회귀 검증:

```powershell
node --check ai_strategy_loop/dashboard/frontend/remodel/src/app.js
python -m pytest tests/unit/test_dashboard*.py tests/unit/dashboard -q
python scripts/verify_dashboard_human_ux_rubric.py --v2-base-url http://127.0.0.1:8776 --v3-base-url http://127.0.0.1:8776 --out artifacts/dashboard-human-ux-v3/final-full-evidence --storyboard artifacts/dashboard-human-ux-v3/storyboards/storyboards.json --viewports 1440x900,1920x1080,1280x720 --tranche final --min-v3-score 90 --min-delta 15
python scripts/verify_dashboard_v2_v3_compare.py --v2-base-url http://127.0.0.1:8776 --v3-base-url http://127.0.0.1:8776 --out artifacts/dashboard-human-ux-v3/final-full-v2-v3-compare --timeout-ms 60000
python scripts/verify_dashboard_safety_audit.py --v2-base-url http://127.0.0.1:8776 --v3-base-url http://127.0.0.1:8776 --out artifacts/dashboard-human-ux-v3/final-full-safety-audit --timeout-ms 60000
git diff --check
git status --short -- _database _database_v3k_shadow _log backup "*.db" backtest/graph .omx/reports "v3k_settings*.json"
```

## 13. Codex용 시작 프롬프트 예시

```text
Open C:\System_Trading\STOM\STOM_V.wt-dashboard-remodel. Read docs/update_log/2026-06-30_dashboard_v3_ultragoal_codex_handoff.md first. The V3 dashboard UX/UI maturity Ultragoal is complete: G001-G007 complete, final aggregate receipt exists, final evidence under artifacts/dashboard-human-ux-v3/final-full-*. Preserve V2 as default and V3 as explicit /ui/remodel/* routes. Do not enable V3 as default unless explicitly requested. Verify current state with gjc ultragoal status --json, /health on port 8776, and the final human UX / compare / safety gates before making changes.
```

## 14. 현재 남은 작업

기능 구현 관점에서는 남은 필수 tranche는 없다. 남은 것은 maintainer/Codex 판단 작업이다.

| 후보 작업 | 성격 |
|---|---|
| 사람이 실제 Chrome에서 UX 재검토 후 미세 조정 | 선택 |
| commit/PR 정리 | maintainer 결정 필요 |
| batch 기본 URL을 V3로 바꾸기 | 현재 제약상 비추천; V2 default 보존 때문에 별도 승인 필요 |
| artifacts/.gjc 포함 여부 결정 | commit 정책 결정 필요 |
| 운영 배포 여부 | 별도 승인 필요 |

## 15. 최종 주의

이번 작업은 V3K gate 작업이 아니다. V3K gate 상태는 기존 지침대로 `3/6`이며, live broker/KHOPENAPI/DB cutover/USER_ACK 관련 작업을 건드리면 안 된다.
