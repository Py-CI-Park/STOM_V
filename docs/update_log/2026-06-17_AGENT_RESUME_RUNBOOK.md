# AGENT RESUME RUNBOOK — 조건식 발굴 연구 (2026-06-17 10:25)

> **어떤 AI 에이전트(새 Claude 세션·Codex 등)든 이 한 장으로 작업·테스트를 이어간다.** 컨텍스트 0에서 시작 가정.
> 상위 핸드오프: `docs/update_log/2026-06-17_session_handoff_anchor_mutation_research.md`,
> `2026-06-15_session_handoff_pipeline_execution.md`(P0~P5 §7/§8).

## 0. 프로젝트 한눈에
- **목표**: 기존 STOM 데이터를 마이닝해 **실매매용 per-stock 조건식**(if 조건: self.Buy())을 자동 발굴.
- **정직지표**: **OOS(미지 기간) 통과 후보 수**(baseline 0). train 통과는 진행지표일 뿐 합격 아님.
- **규율(불가침)**: 엔진/CLI/`backtest/`/`backtest/graph/` **무수정**(연구계층 `ai_strategy_loop/`만). 사후슬라이스≠엣지
  (재백테 게이트 필수). **커밋은 사용자 요청 시에만**(지금 전부 미커밋). 모든 보고에 체크시각.
- **확정된 진단**: "데이터 천장 아님 — 알파 실재(검증 챔피언이 발굴게이트로 +9.5~11M 재현), **병목=콜드 LLM 생성**".
  → 레버 = **앵커 변이**(검증 시드를 parametric 변이 + P0b 게이트, LLM 0회).

## 1. 환경 (Codex/새 에이전트 필독)
- OS Windows. 셸: git bash(이 runbook 명령) + PowerShell(프로세스/detached). **모든 python 앞에 `PYTHONUTF8=1`**(한글).
- 워크트리(작업 루트): `C:\System_Trading\STOM\STOM_V.wt-dev` (브랜치 `STOM_Version_2U_C`). 명령은 여기서 실행.
- 백테는 **warm 엔진**(대용량 시장DB 로드, prepare ~250s, 32 워커). ★**무거운 워밍 백테는 한 번에 하나만**
  — 동시 2개면 prepare 경합 타임아웃(bt_timeout=900). 발굴 게이트 = `claude_candidate_batch_eval`(LLM 0회).

## 2. 지금까지의 성과 (전부 미커밋)
- **P0~P5 구현·검증·code-reviewer APPROVE**(P0a/b 게이트, P1 A/B, P2 유상태, P3 환류토글+FDR+feature_importance,
  P4 grid coarse-to-fine, P5 lift/mutator/Exit-Regret/오케스트레이터). 단위테스트 다수(아래 §6).
- **양성대조 진단**: 챔피언 4종(FROZEN_THETA·T2C1·T2C2·T2C3)을 발굴게이트로 재백테 → 4/4 통과(천장 아님 입증).
- **밤샘 앵커변이(seed_902905)**: 19라운드·통과 399·**챔피언 +13,928,386 / MDD 9.62**(`r8_4_strength_max=250`),
  r8 수렴(증분→0, 구조해석 반복수렴과 동일). summary: `.omo/evidence/tmap-walkforward/ovn_anchor_summary.json`.
- **멀티스타트(다른 봉우리)**: t2late(`seed_902905_t2late`) → best **+10,582,342 / MDD 11.5**(`r4_4_cap_hi_late=99999`).
  = seed보다 profit 낮음(payoff↑·MDD↑). **결론: t2late 봉우리는 seed보다 낮다.** (exit2/r2full 미탐색.)
- **대시보드(8770)**: 프로세스 흐름 페이지 시각화(/process_flow), `/time_profit`·`/run_log` 엔드포인트,
  `_csv_by_buy_name` 폴백(진화탭 BacktestDetailChart가 warm-batch/발굴 런의 동시보유·일별손익·누적수익·낙폭을
  실시간 표시), `fitness/backtest_timeseries.py`(동시보유·시간대수익, test 5).

## 3. ★중단/실행 상태 (2026-06-17 10:25 기준)
| 항목 | 상태 | 조치 |
|---|---|---|
| t2late 발굴 런 | **중단됨**(PID 100176 kill, 고아 0) | 필요시 §4-B로 재기동 |
| seed 발굴 런 | 완료(자율 종료) | — |
| 대시보드 8770 | **실행 중**(detached) | 보존. 죽었으면 §4-D로 재시작 |
| 모니터/크론 | 세션 전용 → **새 세션엔 없음** | 필요시 다시 설정 |
| OOS 검증 | **미실행**(사용자 지시 보류) | §4-C로 실행(결정적) |

## 4. 재시작/실행 방법 (복붙 가능, 모두 워크트리에서)
**A. 상태 확인**
```
PYTHONUTF8=1 python -c "import json;d=json.load(open('.omo/evidence/tmap-walkforward/ovn_anchor_summary.json'));print(d['best_overall'])"
# 실행 중 워밍 런 확인(겹침 방지):
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { \$_.CommandLine -match 'overnight_anchor|candidate_batch_eval' } | Select-Object ProcessId"
```
**B. 멀티스타트(다른 시드 봉우리) — ★다른 워밍 런 없을 때만**
```
# dry-run으로 변이·재료화 먼저 확인:
PYTHONUTF8=1 python -m ai_strategy_loop.scripts.overnight_anchor_mutation --template seed_902905_r2full \
  --config-json ai_strategy_loop/state/run_p5_validation_tick_late.json --out .omo/evidence/tmap-walkforward/ovn_r2full.jsonl \
  --run-prefix ovn_r2full --dry-run --max-rounds 1 --max-per-param 3
# 실주행(detached, PowerShell):
powershell -NoProfile -Command "$env:PYTHONUTF8='1'; Start-Process -WindowStyle Hidden -WorkingDirectory 'C:\System_Trading\STOM\STOM_V.wt-dev' -FilePath 'python' -ArgumentList '-m','ai_strategy_loop.scripts.overnight_anchor_mutation','--template','seed_902905_r2full','--config-json','ai_strategy_loop/state/run_p5_validation_tick_late.json','--run-prefix','ovn_r2full','--out','.omo/evidence/tmap-walkforward/ovn_r2full.jsonl','--max-rounds','12','--deadline-hhmm','18:00','--max-per-param','3' -RedirectStandardOutput 'C:\System_Trading\STOM\STOM_V.wt-dev\.omo\evidence\tmap-walkforward\ovn_r2full_run.log' -RedirectStandardError 'C:\System_Trading\STOM\STOM_V.wt-dev\.omo\evidence\tmap-walkforward\ovn_r2full_run.err'"
# 후보 시드: seed_902905_r2full(11θ)·seed_902905_exit2(7θ). 진행: ovn_<name>_run.log tail.
```
**C. ★OOS 검증(결정적·다음 핵심) — 최고 봉우리 챔피언(현재 seed의 r8_4, +13.93M)을 OOS로**
- 챔피언 θ는 ovn_anchor_summary.json의 best_overall.theta. seed_902905 템플릿에 render → materialize →
  **OOS config**로 `claude_candidate_batch_eval` 재백테 → gate/profit이 OOS서 재현되면 진짜 알파, 아니면 과적합.
- OOS config: 발굴 config(`run_p5_validation_tick_late.json`)에서 `bt_full_start/bt_full_end`를 학습 외 기간으로
  바꾼 사본을 만들어 사용(예: 2022 또는 2026 단독). 엔진 무수정·재백테만. ★넓게 탐색했으니 다중검정 주의.

**D. 대시보드 재시작 / 재생성**
```
# 죽었으면:  PYTHONUTF8=1 python -m ai_strategy_loop --port 8770   (detached 권장: powershell Start-Process)
# 프로세스 흐름 페이지는 매 요청 재생성(import 캐시) → build_process_flow_html.py 수정 시 서버 재시작 필요.
# 프론트 jsx 수정 시에만:  cd ai_strategy_loop/dashboard/webui-build && node build-app.mjs
# 보기: http://127.0.0.1:8770/ui/ (Ctrl+Shift+R 하드새로고침; iframe 캐시 끈질김)
```
**E. 테스트 / 브랜치 게이트**
```
# 이번 세션 신규 테스트:
PYTHONUTF8=1 python -m pytest tests/unit/test_backtest_timeseries.py tests/unit/test_feedback_toggles_on.py \
  tests/unit/test_grid_refine.py tests/unit/test_lift.py tests/unit/test_mutator.py tests/unit/test_p5_exit_forensics.py \
  tests/unit/test_research_presets.py -q
# 브랜치 게이트(CLAUDE.md):  python scripts/verify_nonrelease_sync.py ;  python -m pytest tests/unit/ -q
# ※전체 유닛 중 8건은 pre-existing 실패(backtest/·ui/·dashboard-pages.jsx = 무수정/타작업 영역, P0~P5 무관).
```

## 5. 미커밋 상태 (git status: 276개)
- 변경(M): `analyze.py`·`summarize.py`·`dashboard/app.py`·`build_process_flow_html.py`·`config.py`·`controller/loop.py`·
  `brain/{prompt,generator}.py`·`scripts/gen_template_hypothesis.py`·여러 테스트.
- 신규(??): `scripts/overnight_anchor_mutation.py`·`scripts/research_presets.py`·`fitness/backtest_timeseries.py`·
  `tmap/refine_gate.py`·`brain/feature_importance_feedback.py`·`scripts/tmap_autopsy_loop.py`·`tests/unit/test_*`·
  `tests/fixtures/refine_gate/`·다수 `tmap/templates/llmgen_*`·`.omo/evidence/tmap-walkforward/*`.
- **커밋은 사용자 요청 시에만**. 요청 시: 논리 단위로 분리(엔진 무수정 확인 후) + 브랜치게이트 통과 후.

## 6. 핵심 신규 파일 (목적)
- `scripts/overnight_anchor_mutation.py` — 앵커 변이 hill-climb 발굴 드라이버(LLM 0회). mutator+materialize+batch_eval 조립.
- `tmap/mutator.py`(propose_mutations)·`tmap/tendency.py`(refine_candidates,INTERACTION_PAIRS)·`fitness/lift.py`·
  `fitness/backtest_timeseries.py`·`tmap/refine_gate.py`(P0b gate_candidate·materialize_candidate).
- `autopsy/analyze.py`(FDR `_benjamini_hochberg`·`_two_sample_p`·Exit Regret/False-Break)·`summarize.py`(토글 게이트 라인).
- `dashboard/app.py`(`_csv_by_buy_name`·`/time_profit`·`/run_log`)·`scripts/build_process_flow_html.py`(시각화).
- `scripts/research_presets.py`(발굴 프리셋, 환류 6토글 ON). config는 `ai_strategy_loop/state/run_p5_validation_tick_late.json`.

## 7. 함정/교훈 (꼭 지킬 것)
1. **워밍 백테 동시 실행 금지** — 겹치면 prepare 타임아웃(982s 사례). 한 번에 하나.
2. **좀비 워커 정리(고아만)**: `multiprocessing.spawn` 워커 중 ParentProcessId가 죽은 것만 Stop-Process
   (활성 런·대시보드·타 워크트리 워커 보존 — 경로로 구분 불가하므로 부모생존으로만 판단).
3. **대시보드 캐시**: 생성기 수정→서버 재시작, 브라우저 Ctrl+Shift+R. /backtest_detail은 csv_path None이면 `_csv_by_buy_name` 폴백.
4. **train 수렴 ≠ 정답**: hill-climb 수렴은 국소최적·train. OOS 검증 전엔 "발굴"이라 단정 금지.

## 8. 다음 단계 (우선순위)
1. ★**OOS 검증**(§4-C): seed 챔피언 r8_4(+13.93M)를 OOS로 → 진짜 알파/과적합 판별. **이게 정직지표를 0→양수로 옮기는 결정적 단계.**
2. 추가 멀티스타트(§4-B): r2full(11θ)·exit2(7θ) — 한 번에 하나. 각 best 수집 → 최고 봉우리 선정 → 그것을 OOS.
3. 미완: 태스크 #25(레짐 분석 리포트 HTML), #27(v2 레짐인식 루프 — 현 드라이버=v1 단일축 hill-climb; 레짐별 분석+탐색/활용+
   레짐-robust 게이트는 설계만, 미구현 — 프로세스 페이지 §1.6 참조).
4. 메모리: `champion-passes-discovery-gate`·`anchor-mutation-convergence-fea-analogy`·`keep-developing-not-exhausted`.
