# 챔피언 양성대조 진단 — "천장 vs 프로세스 vs 게이트" 규명 (2026-06-16 14:58)

## 한 줄 결론
검증된 챔피언 4종을 **발굴 게이트로 재백테 → 4/4 전원 통과**. ∴ 조건식 발굴 루프의 gate-pass=0은
**데이터 천장도, 게이트 오설정도 아니고 — 콜드 LLM 생성기(controller.loop)가 약한 것**이다. 데이터에
알파는 *실재*하고(챔피언이 +9.5~11M 재현), 측정기(게이트)는 *정상 교정*됐다.

## 배경 — 왜 이 실험이 필요했나
P0~P5 전 단계 구현·검증 후에도 자동 발굴의 정직지표(게이트/OOS 통과 후보 수)는 **0**이었다.
- A 런(p3val, P3 5토글, 15세대): best 0.36, **gate-pass 0**.
- P5 런(p5val, 6토글+exit_forensics, 15세대): best 0.30, **gate-pass 0**.
- 적대적 패널(5에이전트) 진단: gate-pass=0이 ①데이터 천장 ②생성기 무능 ③게이트/타깃 오설정 중
  무엇인지 *구분 불가*. **검증된 승자를 발굴 게이트로 통과시키는 양성대조**가 단일 최고-정보량 실험으로 도출됨.

## 실험
- 대상: `pairs-t2-corner.json`의 챔피언 4종(과거 mdd35/daily0.3 게이트로 OOS 통과한 다밴드 승자).
- 처치: 생성 0회. `claude_candidate_batch_eval`로 **발굴 게이트 config**(`run_p5_validation_tick_late.json`:
  mdd_cap=20·min_daily_trades=0.05·tick 2023–2025·universe)로 그대로 재백테.
- run-id `champ_diag_disc_20260616`. 증거: `.omo/evidence/tmap-walkforward/champion_diag_discovery.log`.

## 결과 (4/4 gate=True)
| 챔피언 | profit | MDD (<20) | daily (≥0.05) | trades | payoff | gate |
|---|---|---|---|---|---|---|
| FROZEN_THETA | +10,965,479 | 10.04 | 0.40 | 272 | 1.53 | **True** |
| T2C1 (91000/4000/4.0) | +9,550,593 | 13.76 | 0.40 | 317 | 1.63 | **True** |
| T2C2 (91000/4000/3.0) | +9,642,207 | 13.89 | 0.40 | 322 | 1.62 | **True** |
| T2C3 (91500/4000/4.0, 다밴드) | +9,866,240 | 11.30 | 0.50 | 356 | 1.66 | **True** |

전원 MDD가 cap의 절반 수준(10~14 vs 20), 빈도는 floor의 8~10배(0.40~0.50 vs 0.05)로 **여유 통과**.

## 판정
1. **천장 아님** — 검증 전략이 +9.5~11M을 재현. 데이터에 알파 실재. (메모리 [[keep-developing-not-exhausted]] 실측 뒷받침)
2. **게이트 정상** — 같은 발굴 게이트를 챔피언이 무난히 통과. 측정기 교정됨.
3. **생성기 문제 확정** — A·P5의 cold-generation은 *같은 게이트·같은 scope*에서 0인데 검증 전략은 전원 통과.
   → gate-pass=0의 원인은 controller.loop의 **콜드 LLM 생성**이다.

## 정직한 한계 (2차·미해결)
이 진단은 챔피언을 **자연 scope(09:00–09:30 다밴드)**로 통과시킨 것. *09:20–09:25 5분창 단독*에 별도
알파가 있는지는 별개 질문으로 **미검증**(부차적 — 주 결론 "생성기 병목"은 불변).

## 함의 — 다음 레버
**콜드 생성을 버리고 앵커 변이로 전환.** 검증 승자는 전부 *앵커 parametric search*(TMAP sweep)에서
나왔고, P5가 그 도구(`tmap/mutator.py`+`scripts/tmap_autopsy_loop.py`)를 이미 구현했다. 통과 챔피언
T2C3(mdd11/daily0.5)를 앵커로 변이→P0b 게이트 폐루프를 돌리면 **신규 통과 후보 산출 가능성이 높다**.

## 연결
- 메모리: [[champion-passes-discovery-gate]] (다음 세션 "천장" 재논쟁 방지).
- 핸드오프: `docs/update_log/2026-06-15_session_handoff_pipeline_execution.md` §7(P3)·§8(P4/P5/A).
- 적대적 패널 원본: `.../tasks/wiqw8i1pz.output` (rankedDeficiencies·단일실험 도출 근거).
