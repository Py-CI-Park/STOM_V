# AI STRATEGY LOOP KNOWLEDGE BASE

## OVERVIEW
`ai_strategy_loop/` owns autonomous STOM condition-expression generation, backtesting, scoring, runtime state, and the browser dashboard. It is research/control-plane code, not production broker runtime.

## STRUCTURE
```text
ai_strategy_loop/
??? __main__.py              # `python -m ai_strategy_loop` dashboard/service entry
??? bootstrap.py             # env isolation before imports
??? config.py                # loop settings, gates, objectives, feature flags
??? brain/                   # LLM prompt/generator/validation path
??? controller/              # loop orchestration, state DB, export contracts
??? dashboard/               # FastAPI backend + static frontend
??? fitness/                 # score and graded fitness
??? provider/                # model providers/auth wrappers
??? autopsy/, meta/          # failure analysis and meta-insight helpers
??? scripts/                 # run_loop/run_dashboard and helper scripts
??? state/                   # runtime DB/snapshots; treat as generated state
```

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Start service | `__main__.py`, `scripts/run_dashboard.py` | Starts FastAPI/uvicorn dashboard. |
| Loop execution | `controller/loop.py` | Backtest cycle, candidate generation, stop handling. |
| State schema | `controller/state.py` | `loop_runs.db`, generations, prompts, equity points. |
| Prompt design | `brain/prompt.py`, `brain/generator.py` | Seed-refine, crossover, filter gates, hypothesis feedback. |
| Scoring | `fitness/score.py` | MDD/profit/frequency/TPI and objective shaping. |
| Dashboard API | `dashboard/app.py` | REST/WebSocket, final approval, reference screenshots. |
| Frontend (셸 3종·단일 번들) | `dashboard/frontend/*.jsx`, `styles.css` | 아래 DASHBOARD SHELL TOPOLOGY 먼저 읽을 것. No new frontend framework unless explicitly requested. |

## DASHBOARD SHELL TOPOLOGY (2026-07-17 전수검사 이후 필독)
프런트엔드는 **셸 3종이 단일 컴파일 번들(`frontend/bundle/app.js`)을 공유**한다:
- **V4 graph-first (정본·기본)**: `v4.html` → `dashboard-v4-shell.jsx` + `v4-*.jsx`. `/ui`·`/ui/evolution/*` 기본 서빙. 헤더 `X-STOM-Dashboard-Version: v4-ops`.
- **legacy (동결·보수만)**: `index.html` → `app.jsx`. `?dashboard_version=legacy` 로만 1회 열림.
- **V3 remodel (프리뷰)**: `remodel/` → `?dashboard_version=v3`.

규칙:
- **신규 연구/분석 패널은 V4 셸(`v4-*.jsx`)에 배선한다.** `app.jsx`(legacy)에만 넣으면 번들엔 컴파일돼도 `/ui`(V4)에서 안 보인다 — 2026-07-17 History 트리·A/B 시각화 누락 사고의 원인.
- 가드: `tests/unit/dashboard/test_shell_wiring_parity.py` 가 "legacy 렌더 컴포넌트 ⊆ V4 렌더 ∪ 화이트리스트"를 강제한다. legacy 전용 신규 패널은 테스트 실패.
- `.jsx` 수정 후 반드시 `dashboard/webui-build`에서 `npm run build` 로 번들 재생성(산출물 커밋).
- 근거: `docs/update_log/2026-07-17_dashboard_v4_forensic_audit_and_perf.md`.

## CONVENTIONS
- Keep generation tied to STOM syntax and official backtest evidence; do not treat LLM output as truth before validation.
- Research/profile runs should preserve prompt, hypothesis, equity, and rejection evidence when possible.
- `controller/export.py` and dashboard final approval are the export boundary; do not bypass human approval into production strategy DBs.
- Runtime files in `state/` are generated; avoid committing snapshots/DB changes unless the task explicitly requires a fixture.
- V3K features remain default-OFF unless the root approval gate allows a specific enablement.

## ANTI-PATTERNS
- Do not write operating `_database/` or live strategy wiring from this loop without the approved gate.
- Do not promote one-month or smoke-test winners as final strategies without longer validation.
- Do not introduce dependencies for the dashboard/frontend without explicit request.
- Do not use S_* or result/diagnostic leakage variables as generated buy-condition inputs.

## COMMANDS
```powershell
python -m ai_strategy_loop
pytest tests/unit/test_dashboard* -q
pytest tests/unit/test_graded_fitness.py tests/unit/test_hypothesis_loop.py -q
```
