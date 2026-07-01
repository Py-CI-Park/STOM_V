# STOM 조건식 연구 프로세스 v2 Sell-only Repair 검증 핸드오프

## 1. 한 장 요약

| 항목 | 결과 |
|---|---|
| run_id | `process_research_sellonly_20260701_night` |
| 목적 | parent buy는 고정하고 parent sell만 한 축씩 바꿔 give-back/MDD/보유시간 개선 가능성 검증 |
| seed | `rr8_12_turnover_min_902=1.5` |
| fixed buy | `GATE_rr8_12_turnover_min_902_1_5_B` |
| parent sell | `GATE_rr8_12_turnover_min_902_1_5_S` |
| 실행 범위 | 2025 full-period, tick, 09:00~09:28, engine 64 |
| fallback | 32 fallback 미사용 (`fallbackUsed=false`) |
| 후보 | 기본 4개 + 6시 전 추가 ladder 2개 = 총 6개 |
| safety | research-only, no export, no live, no final promotion |
| 핵심 결론 | `hard_stop` 축만 소폭 개선. trailing/hold/orderflow-ma 조기청산은 대부분 수익과 MDD를 악화 |

## 2. 왜 이 실험을 했는가

직전 buy-side reject filter 연구에서는 `거래대금증감 < -5_000_000_000` 축이 MDD를 크게 낮췄지만 거래수와 수익도 크게 줄었다. 그래서 이번 실험은 같은 진입을 유지한 채 **매도 조건식만 변경**해 다음 질문을 검증했다.

| 질문 | 검증 방식 |
|---|---|
| 좋은 진입은 유지하면서 손실 확대만 줄일 수 있는가? | parent buy 고정, sell만 hard stop/trailing/hold/orderflow 축으로 변경 |
| MDD를 줄이는 매도축이 존재하는가? | baseline 대비 MDD, profit, trade count, avg hold time 비교 |
| buy-side reject와 결합할 가치가 있는 sell 축이 있는가? | 단독 효과가 있는 축만 다음 paired repair 후보로 보류 |

## 3. 프로세스 산출물

| 산출물 | 경로 |
|---|---|
| 실행 스크립트 | `artifacts/process-research-sellonly-20260701/run_sellonly_research.py` |
| Context Pack JSON | `artifacts/process-research-sellonly-20260701/research_context_pack.json` |
| Context Pack prompt | `artifacts/process-research-sellonly-20260701/research_context_pack_prompt.md` |
| Analysis Card v2 | `artifacts/process-research-sellonly-20260701/analysis_cards.jsonl` |
| Candidate Cards | `artifacts/process-research-sellonly-20260701/candidate_cards.jsonl` |
| Prompt receipts | `artifacts/process-research-sellonly-20260701/prompt_mutation_receipts.jsonl` |
| Official backtest receipts | `artifacts/process-research-sellonly-20260701/full_period_backtest_receipts.json` |
| Safety receipt | `artifacts/process-research-sellonly-20260701/safety_receipt.json` |
| Strategy DB cleanup receipt | `artifacts/process-research-sellonly-20260701/strategy_db_cleanup_receipt.json` |
| HTML report | `artifacts/process-research-sellonly-20260701/sell_only_validation_report.html` |
| 연구 계획서 | `docs/research/condition_research/research_runs/process_research_sellonly_20260701_night_plan.md` |
| 연구 관리 보고서 | `docs/research/condition_research/research_runs/process_research_sellonly_20260701_night_management.md` |
| 연구 결과 보고서 | `docs/research/condition_research/research_runs/process_research_sellonly_20260701_night_result.md` |
| Local verification summary | `artifacts/process-research-sellonly-20260701/local_verification_summary.json` |
| HTML screenshot | `artifacts/process-research-sellonly-20260701/sell_only_validation_report.png` |
| Strategy DB post-cleanup query | `artifacts/process-research-sellonly-20260701/strategy_db_post_cleanup_query.json` |
| Final review summary | `artifacts/process-research-sellonly-20260701/final_review_summary.json` |

## 4. 검증된 Context Pack 조건

이번 run은 다음 사용자 요구를 반영했다.

| 요구 | 반영 여부 |
|---|---|
| 조건식 id만 전달 금지 | 반영. full parent buy/sell code와 sha256 포함 |
| STOM 변수/규칙 원천 포함 | 반영. `strategy.txt`, `rules.txt`, system prompt, variables, forbidden, examples 포함 |
| Analysis Card v2 | 반영 |
| 후보 3~4개 이상 | 반영. 기본 4개 + 추가 ladder 2개 |
| 한 번에 한 sell 축만 변경 | 반영 |
| 64 engine 우선 | 반영 |
| 32 fallback 조건부 | 반영. fallback trigger 없음 |
| export/live/final promotion 금지 | 반영 |
| 결과 보고/관리 보고/HTML | 반영 |

주의: 기존 공용 `multi_hypothesis_candidate_pack_v1` validator는 repair와 discovery가 모두 있어야 통과한다. 이번 실험은 의도적으로 sell-only repair만 허용하므로, 공용 validator의 유일한 이탈 사유가 `missing_discovery_candidate`일 때 `strict_sell_only_repair_validation_v1` profile로 승인했다. 이는 우회가 아니라 이번 실험의 핵심 제약인 “discovery 없음, parent buy 고정, sell-only 단축 검증”을 명시한 것이다.

후속 검토에서 지적된 누락도 재검증했다. 추가 ladder 후보 `trail05`, `stop06`까지 포함해 candidate card 6개, prompt receipt 6개, backtest receipt 6개가 모두 맞물리며 `missingPromptReceipts=[]` 상태다. 또한 transient strategy row cleanup은 기존 row가 있던 경우 원본 code sha로 복원하고, 새로 만든 후보 row는 삭제하도록 수정했다. 재조회 결과 sell-only transient row는 `stockbuy`/`stocksell`에 남아 있지 않다.

최종 재검토도 완료했다. Architect lane은 blocker 없음/승인, QA lane은 candidate-count/prompt-receipt/backtest/safety 불일치 없음, slop-cleanup lane은 blocking finding 0으로 판정했다.

## 5. Baseline

| Profit | MDD | Trades | Win | Avg hold | TPI |
|---:|---:|---:|---:|---:|---:|
| 518,822 | 20.54 | 175 | 52.57 | 280.04 | 1.13 |

## 6. Candidate 결과

| 후보 | sell axis | 조건 | Profit | ΔProfit | MDD | ΔMDD | Trades | Win | Avg hold | 판정 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `prv2sell_20260701_trail01` | trailing_giveback | `최고수익률 > 2.5 and 최고수익률 * 0.72 >= 수익률` | 356,100 | -162,722 | 24.61 | +4.07 | 177 | 54.24 | 231.02 | 악화 |
| `prv2sell_20260701_stop02` | hard_stop | `수익률 <= -3.5 and 현재가 < 현재가N(1)` | 558,947 | +40,125 | 19.09 | -1.45 | 175 | 52.57 | 260.74 | **소폭 개선** |
| `prv2sell_20260701_hold03` | hold_time_stop | `보유시간 > 45 and 수익률 < 1.0 and 현재가 < 최저현재가(int(30), int(보유시간))` | 202,095 | -316,727 | 28.45 | +7.91 | 176 | 45.45 | 180.43 | 악화 |
| `prv2sell_20260701_flowma04` | orderflow_ma_breakdown | `시가총액 < 10000 and (초당매도수량 - 초당매수수량) >= 매수총잔량 * 0.45 and 이동평균(60) > 현재가 and (현재가 / 현재가N(1) - 1) * 100 < -0.35` | 96,566 | -422,256 | 28.10 | +7.56 | 182 | 44.51 | 168.90 | 악화 |
| `prv2sell_20260701_trail05` | additional_trailing_ladder | `최고수익률 > 3.5 and 최고수익률 * 0.68 >= 수익률` | 530,905 | +12,083 | 20.60 | +0.06 | 175 | 52.57 | 275.60 | 중립/미세 수익 개선, MDD 악화 |
| `prv2sell_20260701_stop06` | additional_hard_stop_ladder | `수익률 <= -4.2 and 현재가 < 현재가N(1) and 등락율각도(30) < 5` | 554,107 | +35,285 | 20.04 | -0.50 | 175 | 52.57 | 278.89 | 소폭 개선 |

## 7. 해석

### 7.1 가장 좋은 후보

`prv2sell_20260701_stop02`가 가장 좋다.

| 기준 | 해석 |
|---|---|
| Profit | +40,125 개선 |
| MDD | -1.45%p 개선 |
| Trades | 175로 baseline 보존 |
| Win | 52.57로 baseline 보존 |
| Avg hold | 280.04 → 260.74로 단축 |

즉, 이 hard stop 축은 “좋은 진입을 줄이지 않고 손실 확대를 조금 빠르게 차단”하는 방향으로 보인다.

### 7.2 추가 ladder 후보

`prv2sell_20260701_stop06`도 소폭 개선이지만 `stop02`보다 개선폭이 작다. 따라서 다음 연구에서는 `-3.5` 주변을 더 촘촘하게 탐색하는 것이 맞다.

### 7.3 실패한 축

| 축 | 실패 이유 |
|---|---|
| trailing_giveback | 너무 빠른 이익 반납 차단이 큰 수익을 잘라 MDD까지 악화 |
| hold_time_stop | 보유시간 단축은 되었지만 win/profit/MDD 모두 악화. 지연 상승 종목을 잘랐을 가능성 |
| orderflow_ma_breakdown | 과잉 조기청산. 거래수는 늘었지만 profit, win, MDD 모두 악화 |

## 8. 다음 연구 방향

| 우선순위 | 연구 | 구체 조건 |
|---:|---|---|
| 1 | hard stop ladder 확장 | `수익률 <= -3.2/-3.5/-3.8/-4.0` + 하락 tick 확인 |
| 2 | hard stop + MA/각도 조건 분리 | `현재가 < 현재가N(1)`만 쓸지, `등락율각도(30) < x`를 붙일지 분리 |
| 3 | stop02와 buy-side 거래대금증감 reject의 paired repair 후보 | 단독 효과가 확인된 후에만 조합. 지금 바로 promotion 금지 |
| 4 | trailing은 더 느린 조건으로만 재검토 | `최고수익률 > 4.0` 이상에서만 작동하는 완만한 trailing |
| 5 | hold/orderflow 축은 보류 | 현재 조건은 손익비를 악화하므로 root-cause 재분석 전 중단 |

## 9. 안전/제한 사항

- 모든 후보는 research-only다.
- export 금지.
- live 금지.
- final promotion 금지.
- 이번 결과는 2025 full-period 공식 백테스트 한 세트다.
- promotion-review를 하려면 별도 zero-generation 단계에서 frozen/fresh holdout, OOS/WF, slippage advisory, evidence health만 검토해야 한다.
- 이번 run은 transient strategy DB row를 사용했고 cleanup receipt를 남겼다. 기존 row는 이전 code/sha로 복원하고 새 후보 row는 삭제했다. DB row는 source artifact가 아니며 커밋 대상이 아니다.

## 10. 바로 이어서 할 작업

다음 실행은 아래 방향이 가장 타당하다.

```text
/skill:ultragoal "execute hard-stop ladder research-only validation for STOM condition research process v2. Use seed rr8_12_turnover_min_902=1.5. Keep parent buy fixed and mutate only parent sell. Start from best sell-only candidate prv2sell_20260701_stop02: 수익률 <= -3.5 and 현재가 < 현재가N(1). Generate 4-6 audited hard-stop ladder hypotheses around -3.2, -3.5, -3.8, -4.0 with and without 등락율각도/MA confirmation. Include full parent buy/sell code, sha256, STOM sources, Analysis Card v2, candidate cards, strict sell-only validation, official backtests, HTML/dashboard report, safety receipt, research plan, management report, result report, final handoff. Research-only: no export, no live, no final promotion."
```

핵심 판단은 명확하다. **매도 조건식 개선은 효과가 있을 수 있지만 넓게 바꾸면 위험하고, 현재는 hard stop 단일 축만 다음 연구 가치가 있다.**

## 11. Ultragoal 최종 성과 상세 보고

| 항목 | 결과 |
|---|---|
| Ultragoal 상태 | 완료 |
| `goal` 상태 | 완료 |
| 완료 goal | G001, G002, G003 전부 complete |
| 실패/blocked/review_blocked | 없음 |
| 최종 aggregate receipt | G003에서 생성 완료 |
| 연구 경계 | research-only 유지 |
| export/live/final promotion | 전부 금지 유지 |
| 실제 실행 여부 | 64-engine official backtest로 baseline + 후보 6개 실행 |
| 검증 | py_compile, focused pytest 35 passed, git diff --check, protected path check, browser screenshot, architect/QA/slop review |

이번 작업은 단순 문서 정리가 아니라, 개선된 process-research v2 흐름으로 실제 sell-only 조건식 연구를 수행하고 공식 백테스트, 보고서, HTML, 검증, 리뷰까지 끝낸 run이다.

## 12. 연구 성과 판단

이번 run에서 확인한 성과는 다음과 같다.

1. 개선된 프로세스가 실제 연구에 사용 가능함을 증명했다.
2. 조건식 id가 아니라 full code + sha + STOM source 기반 Context Pack이 유지되었다.
3. 후보 1개가 아니라 6개 multi-hypothesis sell-only 후보를 공식 백테스트했다.
4. 매도 조건식 개선이 의미 있을 수 있다는 실증 결과를 얻었다.
5. 다음 연구축이 hard stop ladder로 좁혀졌다.

가장 중요한 실증 결과는 `prv2sell_20260701_stop02`다.

| 항목 | Baseline | `stop02` | 변화 |
|---|---:|---:|---:|
| Profit | 518,822 | 558,947 | +40,125 |
| MDD | 20.54 | 19.09 | -1.45%p |
| Trades | 175 | 175 | 0 |
| Win | 52.57 | 52.57 | 0 |
| Avg hold | 280.04 | 260.74 | -19.30 |

이 결과는 “좋은 진입을 줄이지 않고 손실 확대를 조금 빠르게 차단”한 가능성을 보여준다. 단일 full-period 연구이므로 promotion-ready는 아니며, 다음 단계는 hard-stop ladder와 OOS/frozen/fresh 검토다.

## 13. 커밋/보존 방침

이번 연구에서 커밋 대상으로 남길 것은 다음이다.

| 묶음 | 경로 | 이유 |
|---|---|---|
| 최종 핸드오프 | `docs/research/condition_research/2026-07-02_sell_only_repair_validation_handoff.md` | 사람이 전체 연구 맥락을 복원하는 핵심 문서 |
| 연구 run 문서 | `docs/research/condition_research/research_runs/process_research_sellonly_20260701_night_*.md` | 계획/관리/결과 보고서 3종 |
| 연구 evidence | `artifacts/process-research-sellonly-20260701/` | Context Pack, 후보 카드, prompt receipt, backtest receipt, HTML/screenshot, gate receipt |
| 연구 index | `docs/research/condition_research/README.md` | 최신 기준 문서 목록 갱신 |
| update log | `docs/update_log/2026-07-02_sell_only_repair_ultragoal_commit_record.md` | 커밋과 검증 사실 기록 |

커밋 대상이 아닌 것은 `.gjc/`와 `.omo/`다. `.gjc/`는 GJC/Ultragoal runtime state이고, `.omo/`는 과거 evidence/log/WAL/screenshot/계획 초안이 섞여 있어 이번 sell-only 연구 산출물로 함께 커밋하지 않는다.
