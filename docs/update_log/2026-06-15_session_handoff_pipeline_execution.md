# 세션 핸드오프 — 데이터마이닝 파이프라인 구현 (2026-06-16 갱신: 10:38)

> compact/세션 교체돼도 이 한 장 + 디스크 상태로 이어간다. **현재: P0~P5 전 단계 구현완료(7/7).**
> ★P3(§7)·P4·P5 완료(§8). 각 단계 code-reviewer APPROVE(CRIT/HIGH 0)·byte-identical 유지·엔진 무수정.
> **A(P3 효과 검증 런) 종료**: 15세대, best 0.36, gate-pass 0(흑자 gen 있으나 MDD>20/빈도 미달). 학습 신호는 작동.
> 다음 후보 실험 = P5 폐루프(exit_forensics+autopsy_loop+mutator)를 켠 연구 런 — 사장님 지시 대기. 미커밋.
> 정본 계획: `.omc/plans/condition-discovery-process-redesign-20260615.md`(ralplan APPROVE).
> 연구보고서: `docs/update_log/2026-06-15_condition_discovery_process_research_report.md`.

## 0. 마인드셋(불변 — 메모리 keep-developing-not-exhausted)
"아직 못 찾았고 프로세스 미완성" — **"데이터 천장/소진"으로 결론짓지 말 것.** 인간은 찾는다=가능.
엔진/CLI 무수정. 출력=실매매용 per-stock 조건식. **횡단면(엔진수정)=하지 않음**(사장님 폐기).

## 1. 7단계 진행
| 단계 | 상태 |
|---|---|
| P0a 오프라인 게이트 | ✅ `tmap/refine_gate.py decide()` + 픽스처 + test |
| P0b 진짜 재백테 게이트 | ✅ `refine_gate.gate_candidate` + claude_candidate_batch_eval. 실백테 검증(결정론·known-good +2.17M PASS·새후보 −3M REFUSE). **P2~P5 단일 해금게이트** |
| P2 유상태 코어 | ✅ `tmap_multiband_discovery.py --stateful` + `build_feedback`(★과적합-인지: smoke-pass→회피, 전체기간생존→선호) + `gen_template_hypothesis --feedback-file` |
| **P1 A/B** | 🔶 pilot 완료, **full n=40 실행 중**(아래 §2) |
| P3 환류토글ON+feature_importance+FDR | ✅ **구현완료**(2026-06-16 07:25, 아래 §7). 124테스트 green·code-reviewer APPROVE(CRIT 0·HIGH 0) |
| P4 grid / P5 lift·mutator | ⬜ P1·P3 후 |

## 2. P1 결과 + full 현황
- **pilot(n=8)**: RANDOM smoke-pass率 0.0 vs STATEFUL 0.375(3/8, 전부 THETA앵커). OOS 둘 다 0.
- **발견1**: 폐루프가 무작위엔 없던 양분기 흑자 코너 생성 = 프로세스 효과(사장님 가설) 입증.
- **발견2(결함→수정)**: smoke-pass 3건 전부 전체기간 과적합(−10~−21M). 원인=build_feedback가 smoke-pass를 *선호*에 넣어 과적합 증폭 → **수정: smoke-pass→회피-과적합, 전체기간생존만 선호**(test 통과).
- **full n=40(수정 피드백, stateful arm만)**: 실행 중, 23:20 기준 ~25/40 **전부 no-go**(과적합 회피하니 smoke-pass 0). random baseline=기존 야간40+pilot8(OOS 0). 완료 ~01:30 예상.
- **full 완료 시**: 생존(train-pass+) 나오면 강조 / 0이면 → **P3가 다음 레버**(승인 후). D 운영규모화는 병행 수익 옵션.

## 3. 핵심 파일(이번 세션 신규/변경, 미커밋)
- `ai_strategy_loop/tmap/refine_gate.py`(decide·gate_candidate·materialize)
- `ai_strategy_loop/scripts/tmap_multiband_discovery.py`(build_feedback 과적합인지·--stateful·evaluate 격상)
- `ai_strategy_loop/scripts/gen_template_hypothesis.py`(--feedback-file·다밴드 프롬프트)
- `ai_strategy_loop/scripts/ab_discovery_eval.py`(A/B metrics·verdict)
- `ai_strategy_loop/scripts/build_process_flow_html.py`(프로세스 시각화 HTML 생성기)
- 대시보드 탭: `dashboard/app.py`(@app.get /process_flow) + `dashboard/frontend/app.jsx`(STOM_TABS process 탭+iframe) + `frontend/bundle/app.js`(재빌드 v=d0f56818). ★프론트는 번들이라 jsx 수정시 `cd dashboard/webui-build && node build-app.mjs` 필요.
- 테스트: `tests/unit/test_refine_gate*.py`·`test_discovery_stateful.py`·`test_template_hypothesis.py`(전부 통과)
- 산출: `.omo/evidence/tmap-walkforward/full_stateful_n40.*`·`ab_result_n8.json`·`p1_ab_preregistration.md`·`docs/process_flow.html`

## 4. 라이브 프로세스(세션 무관 — OS 독립 프로세스)
- full 런: 백그라운드 detached(완료 시 통지). 모니터 `bang86zzl`, 다이제스트 cron `ac3822a2`(매시 :47).
- 대시보드: 독립 프로세스 8770(재시작 시 `python -m ai_strategy_loop --port 8770`). /process_flow 라우트 + 🗺️탭(하드새로고침으로 노출).

## 5. 재개 절차
1. 이 문서 → 계획서 §B(P0~P5) 읽기.
2. full 런 상태: `.omo/evidence/tmap-walkforward/full_stateful_n40.jsonl`(iter수·판정), `_summary.json` 있으면 완료.
3. full 결과 보고 → **P3는 사장님 승인 후** 착수(조건별 기여도 분석·불필요 제거).
4. 규율: 엔진무수정·정직지표(OOS)·사후슬라이스 재백테게이트·소진단정 금지.

## 6. 안전 노트 (중단·복구 대비)
- **compact는 안전**: 세션을 *유지*한 채 컨텍스트만 요약 → full 런·대시보드·cron 모두 계속 진행.
- **full 런(b91e1f4mb) = 세션-백그라운드 작업**: 세션을 *완전히 닫으면* 멈출 수 있음. 단 **완료 iter는
  `full_stateful_n40.jsonl`에 계속 append되어 데이터 손실 0**. 23:20 기준 ~25/40, 완료 ~01:30 예상.
  - 재가동(중단 시): `PYTHONUTF8=1 python -m ai_strategy_loop.scripts.tmap_multiband_discovery --max-iters 40 --stateful --out .omo/evidence/tmap-walkforward/full_stateful_n40.md`
    (주의: iter 카운터 0부터 재시작·기존 jsonl에 append되니, 완료분 분석 후 새 --out 권장).
- **대시보드(8770) = 진정 detached**(powershell Start-Process): 세션 무관하게 생존. 재시작:
  `python -m ai_strategy_loop --port 8770`. 프론트 jsx 변경 시 `cd dashboard/webui-build && node build-app.mjs`.
- **cron(ac3822a2 :47 다이제스트)·monitor(bang86zzl)는 세션 전용** — 세션 종료 시 소멸. 재개 시 다시 걸면 됨.
- **다음 결정점**: P3 완료(§7). 다음은 P4(grid 자율루프)·P5(lift/mutator) — **사장님 승인 후**. 미커밋(요청 시 커밋).

## 7. P3 완료 기록 (2026-06-16 07:25, code-reviewer APPROVE)
**대상 루프 = `controller/loop.py`**(THETA 세대 학습 루프 — P2의 야간 하네스와 다른 루프, R5 분리).
신규 3종(전부 가법적·토글 OFF면 byte-identical):
1. **연구프리셋 환류 토글 ON** — `scripts/research_presets.py` `_COMMON_DISCOVERY`에 segment/quantile/
   counterfactual/hypothesis/feature_importance 5종 True 추가. **전역 LoopConfig 기본값은 OFF 유지.**
2. **FDR(Benjamini-Hochberg)** — `autopsy/analyze.py`: Discriminator에 p_value/q_value/fdr_pass 가법
   필드 + `_two_sample_p`(정규근사 erfc) + `_benjamini_hochberg`(α=0.10 동결, family=present B_* 전수).
   `summarize.py`: quantile 임계 후보를 **FDR 통과분(`fdr_pass is not False`)에만** 병기 → 잡음 피처
   선택편향(R1) 차단. ★주의: **quantile-ON 출력은 FDR 게이팅으로 *의도적*으로 pre-P3와 달라진다**
   (OFF 경로는 byte-동일 유지). 이는 계획 승인된 R1 보정.
3. **feature_importance 배선** — `brain/feature_importance_feedback.py`(신규, 순수·무예외):
   시총/시간대 셀별 분위 승률 격차 큰 결정 피처를 매수 'prefer 힌트'로. `_build_feature_importance_lines`
   (loop, train CSV 전용=holdout 가드) → gen_kwargs → `_generate_pair`(매수만) → `generate_strategy`
   → `build_messages`(매수 전용 블록). 전부 `segment_avoid` 채널 패턴 미러링.
- **신규 토글**: `config.py` `feature_importance_feedback_enabled`(F)·`feature_importance_feedback_min_cell`(20).
- **테스트**: `tests/unit/test_feedback_toggles_on.py`(13). + 탭 테스트 수정(process 탭으로 7개).
- **검증**: 전체 유닛 3278 pass. byte-identical 회귀(quantile/autopsy/segment/hypothesis/prompt) 전부 green.
  나머지 8 실패는 backtest/·ui/·runner·dashboard-pages.jsx(내 diff 외)만 건드림 → **pre-existing**(무수정 영역).
  code-reviewer 별도 패스 **APPROVE**(CRIT 0·HIGH 0·MED 2·LOW 2 — 전부 튜닝/문서 권고, 블로커 아님).
- **사용법**: 연구 런은 `python -m ai_strategy_loop.scripts.research_presets <preset> --out <config.json>`로
  프리셋 config 생성 후 `loop --config-json`으로 기동하면 환류 6종이 켜진 폐루프가 돈다.

## 8. P4·P5·A 완료 기록 (2026-06-16 10:38)
**P4 — grid coarse-to-fine** (대상 `tmap/tendency.py`, code-reviewer APPROVE):
- 신규 `refine_candidates(summary,*,template,interaction_pairs,min_plateau_score)` — 1-D plateau_score 랭크 →
  사전선언 `INTERACTION_PAIRS`(cap×take,cap×trail,take×trail) 우선, 없으면 top-2 → 2차 grid 추천(순수·advisory).
- grid_points/grid_summary/parse_grid_label/tmap_sweep --grid는 **이미 존재**(C6/P1) — P4는 추천 엔진만 추가.
- 테스트 `test_grid_refine.py`(12). 동률 결정론·template 교차검증 가드 포함.

**P5 — 포렌식 폐루프 완성** (R_* 컬럼 존재 확인=proceed-full, code-reviewer APPROVE):
- `fitness/lift.py`(신규) — compute_lift_ev/lift_ev_by_segment(in-sample Lift·EV 순수). test 14.
- `tmap/mutator.py`(신규) — propose_mutations(앵커 이웃 변이, 기존 param 좌표만, 게이트 미호출). test 23.
- `autopsy/analyze.py` analyze_exits — **Exit Regret**(익절기회 수익거래 중 고점 절반도 못 지킨 비율)·
  **False-Break**(손실거래 중 진입 후 못 오른 비율) 가법 산출 + `exit_regret_keep` 파라미터. test 4.
- `autopsy/summarize.py` — 포렌식 라인(토글 `exit_forensics_feedback_enabled` ON일 때만, OFF=byte-동일).
- `scripts/tmap_autopsy_loop.py`(신규) — plan_candidates(순수)+run_autopsy_loop(주입 gate_fn으로 **P0b 통과분만
  채택·게이트 우회 0**)+CLI. test 5. = 사람 개입 0 폐루프 [A]→[F].
- config 토글 `exit_forensics_feedback_enabled`(F) + 프리셋 ON.

**A — P3 효과 검증 런**(p3val_20260616, controller.loop 15세대, 38분):
- best_gen=2 best_score=0.36, **winner/gate-pass 0**. graded 0→0.36 상승(학습 작동), gen9 +58,669 흑자(8건=빈도미달).
- 흑자 구성은 MDD>20 또는 거래빈도 미달로 게이트 탈락 → **P5 포렌식(MDD=Exit Regret, 진입=False-Break)이
  정확히 이 실패모드를 겨냥**. ※A config는 P5 토글 추가 전 생성이라 P3만 적용 — P5 켠 재런이 다음 자연 실험.

**검증 종합**: P4·P5 신규/회귀 테스트 전부 green. 전체 유닛은 8 pre-existing(backtest/·ui/·dashboard-pages,
무수정 영역) + (A 가동 중엔 루프락 보유로 loop/dashboard_ws 3건 일시 실패→A 종료 후 통과 확인). **P3/P4/P5 회귀 0.**
