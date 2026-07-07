# 알파 랩 v5 최종 판정 — R1+R2 복합 선택/앙상블 게이트 미실행, KILL (v4 그대로 유지) (2026-07-07)

> **봉인 판정**: R0 discovery 백테 자격 후보 **0/8**(9개 완전쌍 중 1건은 데이터 갭으로 시도 자체 불가) →
> `selection_rule_sealed.kill`("자격자 0 → 비상관 복합 없음, v4 그대로 머지 권고")에 따라 **선택·OOS 백테·5-way
> 조립·개선판정(R1+R2 2~4단계)을 실행하지 않고 종결**한다. OOS 봉인창(2025-01~2026-02)은 이번 태스크에서
> 소비하지 않았다(선택 후보가 없어 소비 대상 자체가 없음).
> **v5 개선 판정: 불가(no-go). v4 `ensemble_a_static_equal`을 배포자산으로 그대로 유지.**
> 영수증: `research_runs/alpha_lab_v5_20260707/`(사전등록 sha `15144e12…` — verify_seal green).

## 0. 실행 전 확인 (본 R1+R2 임무 범위)

1. `alpha_lab.registry.verify_seal(path, expected_sha)`을 `preregistration_v5.json`(`15144e1286be14cb9afb403d3fa55bd3f87543d215991ac25558f5a85601b731`)에 직접 실행 — **OK**(`SealViolation` 없음).
2. R0 산출물(`v5_candidate_pool.json`, `v5_candidate_characterization.json`) 원문을 전 필드 대조 — 완전쌍 9건 식별, 8건 discovery 창 백테 시도, **8/8 error**(0 ok), 1건(`CSS_V7_MIN_MASTER`)은 min DB 데이터 갭으로 시도 자체 불가.
3. `alpha_lab.registry.total_trials(ledger, 'V5C')`로 `n_trials_ledger.jsonl` 독립 재합산 — **8**(R0 보고값과 완전 일치).
4. `python -m pytest tests/unit/test_alpha_registry.py -q` — **22 passed**(R0가 additive로 추가한 `V5C` 태그가 기존 9태그와 함께 회귀 없이 동작함을 확인).
5. 판정 결과: **discovery 자격 후보 0건** → 사전등록 봉인 `selection_rule_sealed.kill` 규칙에 따라 선택·OOS·5-way 조립·개선판정 없이 본 문서로 정직 기록 후 종료. 이번 R1+R2 임무의 엔진 실행은 **0회**(예산 미추가 소진, `n_trials_ledger.jsonl` 신규 append 없음 — 실행 없는 항목은 이중장부 방지 원칙상 기록하지 않음).

## 1. 수치 요약

| 항목 | 값 |
|---|---|
| R0 식별 완전쌍(B+S) | 9건(sealed 4 type: CSS_V7_MIN·CSS_V7_TICK·C_T_900_920·Study) |
| discovery 창 백테 시도 | 8건(1건은 데이터 갭으로 시도 불가) |
| discovery 백테 성공(ok) | **0/8** |
| discovery 백테 실패(error) | **8/8**(런타임 arity 결함 — 아래 §2) |
| qualify 통과(`profit>0 AND corr<0.6`) | **0건**(유효 profit/corr 측정치 자체가 없음) |
| select 결과 | 해당 없음(N/A) — 자격자 0 |
| R1 OOS 백테(선택 후보) | **미실행**(선택 후보 없음) |
| R2 5-way 등가중 조립 | **미실행**(5번째 후보 없음) |
| R2 개선판정(improvement_rule) | **미실행**(입력 데이터 없음 → 평가 대상 없음) |
| v4 4-way 배포자산(baseline, 불변) | `ensemble_a_static_equal`: OOS profit 2,608,362 / MDD 493,591 / **calmar 5.2845** |
| 엔진 예산 | 봉인 상한 40 중 R0 8 사용, 이번 R1+R2 **0 사용**, 잔여 **32** |
| n_trials 원장 | `V5C`=8(이번 태스크 추가 append 0건, 독립 재합산 일치) |

## 2. 판정 근거 — 사전등록 봉인 규칙 기계 적용

`preregistration_v5.json.selection_rule_sealed`(원문):

- **qualify**: `discovery profit > 0 AND (후보 월별P&L vs v4앙상블 상관) < 0.6`
- **select**: `자격자 중 상관 최저(동률 → discovery calmar 최고) 1종`
- **kill**: `자격자 0 → 비상관 복합 없음, v4 그대로 머지 권고`

R0에서 8개 discovery 대상 후보가 전부(8/8) error로 종료됐다(6건 300초 타임아웃, 2건 56~62초 "backtest completed without metrics"). 원인은 개별 전략의 수익성이 아니라 **9개 완전쌍 전원이 공유하는 구조적 결함**이다: buy/sell 코드가 `self.Buy(종목코드, 종목명, 매수수량, 현재가, 매도호가1, 매수호가1, 데이터길이)` / `self.Sell(...동일 7인자)`라는 레거시 호출을 쓰는데, 현재 `backtest/backengine_base.py`의 실제 시그니처는 `Buy(self, buy_long=False)`/`Sell(self, sell_long=False)`(0~1인자)다. `self.Strategy()` 호출이 bare `except`로 감싸여 있어(725-730행) `TypeError`가 나면 `BackStop(3)`으로 조용히 죽고 "백테중지완료" 신호를 보내지 않아(566-574행 분기), 오케스트레이터가 무한 대기하다 300초 타임아웃으로 표면화된다. 이 결함은 `docs/update_log/2026-07-03_css_v7_root_cause_before_plan_b.md` / `2026-07-03_css_v7_plan_b_precheck_timeout_diagnosis.md`에 CSS_V7 비-OPT 21개 조건식에서 이미 확정 진단된 **사전 존재 결함**이며, 이번 R0가 그 범위가 `C_T_900_920`/`Study` 계열까지 포함함을 추가 확인했다. `compile()`은 Python 구문만 검사해(런타임 API 계약 무관) 이 결함을 걸러내지 못한다.

따라서 유효한 `discovery_profit`/`corr_with_v4` 측정치가 존재하는 후보가 **0건**이며, `qualify` 조건(`profit>0`)을 평가할 원자료 자체가 없다 → **자격자 0** → 봉인 `kill` 규칙이 기계적으로 확정된다. 이는 v4 등가중 앙상블(상관 0.816)의 실측 성과 미달이 아니라, **후보 풀 자체가 실행 불가능했다는 실행 게이트 실패**다.

## 3. R1+R2 단계별 미실행 사유 (사전등록 조건부 규칙의 직접 적용)

사전등록 임무 지시는 "자격자 있으면" 2~4단계(OOS 백테 → 5-way 조립 → 개선판정)를 수행하도록 조건부로 명시한다. 자격자가 0이므로 각 단계를 강제로 수행하지 않았다 — 이는 누락이 아니라 봉인 규율의 정확한 준수다.

| 단계 | 실행 여부 | 사유 |
|---|---|---|
| 1. 선택 | 실행(결과: N/A) | 자격자 0 → 선택 대상 없음, kill 분기 즉시 확정 |
| 2. OOS 백테(선택 후보, 2025-01~2026-02) | **미실행** | 선택 후보가 없어 `oos_rule`("선택 후보만 OOS 백테")의 실행 대상 자체가 없음. 재사용 자원인 OOS 봉인창을 임의 소비하지 않음(재시도 금지 규율과 동일한 절제 원칙) |
| 3. 5-way 등가중 조립(v4 4종 + 선택 1종) | **미실행** | 5번째 후보가 없어 조립 입력 자체가 없음. 임의 대체 편입은 봉인 select 규칙 우회이므로 수행하지 않음(`alpha_lab.ensemble.portfolio.static_equal`/`robustness.py` 미호출, 재구현 없음) |
| 4. 개선판정(`improvement_rule`: OOS 5-way calmar > 5.284 AND 4창 중 ≥3창 MDD 이하) | **미실행** | 5-way 성과 데이터 자체가 없어 규칙을 적용할 입력이 없음 → 평가 없이 "미개선"으로 귀결 |

## 4. 정직한 한계 및 후속 경로

1. **9개 완전쌍 전원이 R0 특성화에 사용 불가능한 "불완전 쌍"이다** — compile 게이트로는 포착 불가능한 런타임 API arity 결함이며, 성능/선택도 문제가 아니다.
2. **코드 수리는 이번 임무 범위 밖이다.** `self.Buy()`/`self.Sell()` 정규형으로 수정하는 것은 사전등록의 "완전 B+S 쌍 그대로 사용(신규 조건식 생성 아님)" 및 "기존파일 수정 additive만" 제약과 상충하므로 R0/R1/R2 어디에서도 수행하지 않았다 — 별도 의사결정/사전등록이 필요하다.
3. **향후 재시도 경로 2가지**: (a) strategy.db의 9개 완전쌍을 `self.Buy()`/`self.Sell()` 정규형으로 수리(재승인 필요), 또는 (b) `CSS_V7_OPT_*` 4개처럼 이미 정규형인 완전쌍을 새로 물색(단, 봉인 `candidate_pool.types` 목록 밖이므로 사전등록 확장 필요).
4. **CSS_V7_MIN_MASTER 1건은 애초에 시도되지 못했다** — 로컬 `_database/stock_min_back.db` 실측 범위(202504070900~202602271519)가 discovery 창(2022-03~2024-12)을 전혀 커버하지 않는 데이터 갭이며, 전략 결함과는 무관하다.
5. **OOS 봉인창(2025-01~2026-02)은 미개봉 보존**이다 — 향후 자격 후보가 발생할 경우에만(코드 수리 또는 신규 정규형 완전쌍 확보 후) 1회 소비 가능하다.

## 5. 예산·무결성 준수

- 엔진 사용: 이번 R1+R2 태스크 **0회**(R0의 8회만 프로그램 누적치에 포함, 봉인 상한 40 중 잔여 32). 신규 엔진 프로세스 기동 없음.
- 봉인 검증: 실행 전 `preregistration_v5.json`(sha `15144e12…`) `verify_seal` 통과. 파라미터(qualify/select/kill 규칙) 재해석 없음 — 봉인 원문 그대로 기계 적용.
- 원장: `n_trials_ledger.jsonl` 신규 append **없음**(이번 태스크 실행분 0건 — 실행 없는 항목은 이중장부 방지 원칙상 기록하지 않음, v3 선례 승계). `V5C` 독립 재합산 결과 8(R0 보고값과 일치).
- 레지스트리 회귀 확인: `test_alpha_registry.py` 22/22 green(R0가 추가한 `V5C` 태그가 기존 9태그와 공존하며 회귀 없음).
- git 커밋 없음(오케스트레이터 소관). `backtest/graph/` 미접근. 기존 파일(등록·원장·사전등록) 수정 없음(본 문서 2건은 신규 파일). `_database`는 git-ignored 로컬 사본, wt-dev 무접촉.
- v4 배포자산(`ensemble_a_static_equal`, OOS calmar 5.2845, MDD 493,591)은 이번 판정으로 **변경되지 않는다** — `v4_final_verdict.md` 결론이 그대로 유지된다.

### 산출물

| 파일 | 내용 |
|---|---|
| `v5_final_verdict.json` | 본 판정의 기계 판독용 구조화 기록(봉인 검증 결과·root cause·예산 대사 포함) |
| `v5_final_verdict.md` | 본 문서(서술형 판정 보고) |

### 참조(선행 산출물, 이번 태스크에서 재실행 없이 인용만)

- `v5_candidate_pool.json` — R0 후보풀 원본(완전쌍 9건 식별, `runtime_arity_audit` 근거)
- `v5_candidate_characterization.json` — R0 특성화 원본(8/8 error, `root_cause`, `selection_rule_applied.verdict=kill` 근거)
- `preregistration_v5.json`(sha `15144e12…`) — 봉인 원문(qualify/select/kill, ensemble_test_sealed, improvement_rule)
- `n_trials_ledger.jsonl` — `V5C` 원장(1줄, 합계 8)
- `docs/research/condition_research/research_runs/alpha_lab_v4_20260707/v4_final_verdict.md`, `v4_oos_verdict.json` — v4 배포자산 baseline(OOS calmar 5.2845, MDD 493,591) 인용 출처
- `docs/update_log/2026-07-03_css_v7_root_cause_before_plan_b.md`, `2026-07-03_css_v7_plan_b_precheck_timeout_diagnosis.md` — self.Buy/Sell 7-arg 레거시 결함 사전 확정 진단(선례)
