# Sell-only Repair Ultragoal 연구 커밋 기록

## 요약

2026-07-02 기준 `process-research` v2의 sell-only repair 실전 검증을 완료했다. 이번 run은 `rr8_12_turnover_min_902=1.5` seed에서 parent buy를 고정하고 parent sell만 한 축씩 바꾸는 연구-only 검증이다.

| 항목 | 결과 |
|---|---|
| run_id | `process_research_sellonly_20260701_night` |
| Ultragoal | G001/G002/G003 complete |
| engine | 64 |
| fallback | false |
| candidates | 기본 4개 + 추가 ladder 2개 = 6개 |
| safety | research-only, no export, no live, no final promotion |
| 최종 결론 | hard stop 축만 다음 연구 가치 있음 |

## 완료한 목표

| Goal | 내용 | 상태 |
|---|---|---|
| G001 | sell-only 연구 계획, full Context Pack, safety boundary 확정 | complete |
| G002 | sell-only 후보 6개 생성, prompt/candidate/backtest receipt 정합성 검증 | complete |
| G003 | 추가 ladder 연구, HTML/보고서/핸드오프/quality gate 재생성 | complete |

## 공식 백테스트 결과

Baseline은 2025 full-period tick 09:00~09:28 replay에서 Profit 518,822 / MDD 20.54 / Trades 175 / Win 52.57 / Avg hold 280.04다.

| 후보 | 축 | Profit | MDD | Trades | 판정 |
|---|---|---:|---:|---:|---|
| `prv2sell_20260701_trail01` | trailing_giveback | 356,100 | 24.61 | 177 | 악화 |
| `prv2sell_20260701_stop02` | hard_stop | 558,947 | 19.09 | 175 | 최선 |
| `prv2sell_20260701_hold03` | hold_time_stop | 202,095 | 28.45 | 176 | 악화 |
| `prv2sell_20260701_flowma04` | orderflow_ma_breakdown | 96,566 | 28.10 | 182 | 악화 |
| `prv2sell_20260701_trail05` | additional_trailing_ladder | 530,905 | 20.60 | 175 | 중립 |
| `prv2sell_20260701_stop06` | additional_hard_stop_ladder | 554,107 | 20.04 | 175 | 소폭 개선 |

핵심 후보는 `prv2sell_20260701_stop02`다.

```text
수익률 <= -3.5 and 현재가 < 현재가N(1)
```

이 후보는 baseline 대비 Profit +40,125, MDD -1.45%p, Trades 동일, Avg hold -19.30초를 기록했다.

## 보존 산출물

| 산출물 | 경로 |
|---|---|
| 최종 핸드오프 | `docs/research/condition_research/2026-07-02_sell_only_repair_validation_handoff.md` |
| 실행/검증 artifacts | `artifacts/process-research-sellonly-20260701/` |
| 연구 계획서 | `docs/research/condition_research/research_runs/process_research_sellonly_20260701_night_plan.md` |
| 연구 관리 보고서 | `docs/research/condition_research/research_runs/process_research_sellonly_20260701_night_management.md` |
| 연구 결과 보고서 | `docs/research/condition_research/research_runs/process_research_sellonly_20260701_night_result.md` |
| 최신 문서 index | `docs/research/condition_research/README.md` |

## 검증

| 검증 | 결과 |
|---|---|
| `python -m py_compile artifacts/process-research-sellonly-20260701/run_sellonly_research.py` | passed |
| `python artifacts/process-research-sellonly-20260701/run_sellonly_research.py` | passed, baseline + 6 candidates official backtest 성공 |
| `pytest tests/unit/test_research_prompt_contracts.py tests/unit/test_condition_generator.py tests/unit/test_condition_discovery_policy.py -q` | 35 passed |
| `git diff --check` | passed |
| protected path status check | clean |
| browser HTML screenshot | `sell_only_validation_report.png` 생성 |
| final architect review | approve, blockers 없음 |
| final QA review | pass, blockers 없음 |
| final slop cleanup | blocking finding 0 |

## 다음 단계

다음 연구는 hard-stop ladder가 맞다.

1. `수익률 <= -3.2 / -3.5 / -3.8 / -4.0` 비교.
2. `현재가 < 현재가N(1)` 유지/제거 비교.
3. `등락율각도(30) < x` 추가 여부 비교.
4. MA 확인 조건 추가 여부 비교.
5. hard-stop 최적 후보가 나온 뒤에만 buy-side reject와 paired repair를 검토한다.

아직 promotion-ready가 아니다. frozen/fresh holdout, OOS/WF, slippage advisory, evidence health 검토는 별도 zero-generation promotion-review 단계에서만 수행한다.
