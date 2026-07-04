# Plan D — 생존 조건식 시드 연구 프로그램 (2026-07-02)

> 목적: Plan C 생존자·격자 시드·기존 검증 시드를 입력으로, 시드별 정제 라운드를 돌려
> OOS 생존 조건식을 축적하고 포트폴리오 프레임에서 명예의 전당 상대 지표에 접근한다.
> 실행 주체: 발굴/검증/기록 3역할 에이전트(§7). 이 문서 하나로 라운드 운영이 가능해야 한다.

## 0. 불변 조건 (Plan C §0과 동일 — 위반 시 즉시 중단)

1. 연구 레인 전용 — `hypothesis_seed` 라벨 필수, 승격/export/live 접근 금지, `backtest/graph/` 불가침.
2. 전략 DB는 INSERT만(UPDATE/DELETE 금지), 실저장 전 백업, 이름 충돌 시 저장 금지·보고, dry-run 기본 + `--apply` 명시.
3. provenance 필수(JSONL + md 이중 기록), 기존 커밋 파일 수정 금지(신규 파일 + `_database` 데이터만), 파일당 800줄 이하, print 금지, 전체 테스트 스위트 금지.
4. n_trials 정직 합산·부활 레지스트리·**OOS-blind 동결 규율**: 라운드 진행 중 고정 OOS 접촉 금지. OOS는 시드/후보 동결 후에만, 사용 횟수 공시와 함께.
5. 파생 조건식 네이밍: 기반 네임 + `_VAR{n}` 접미사(카탈로그 §2 규칙). 저장 시 provenance(부모 id, 부모 sha, 변이축, 코드 sha)를 원장에 남긴다.

## 1. 프로세스 기반 — B3 config 재사용

정제 라운드의 실행 config는 **Plan B의 B3 config**를 재사용한다
(`docs/research/condition_research/plans/2026-07-02_plan_B_*.md`의 B3 절 참조).
Plan B 문서가 없거나 B3이 미정의인 경우 아래 fallback을 B3으로 간주한다(동일 계약):

| 필드 (`cli/research_loop.py` `ResearchLoopConfig`) | 값 | 근거 |
|---|---|---|
| preset | `research` (research-only authority) | process-research v2 검증 run 계승 |
| engine | 64 first + 32 fallback receipt(미사용 시 false 기록) | 2026-07-01 검증 run 정책 |
| `candidate_slots_override` | `8` (다후보 8슬롯 — 기본 4의 연구 레인 opt-in 확장, fail-closed) | Phase 3 T3.2 |
| `candidate_lane_quota` | `{"repair": 5, "discovery": 3}` (합=8 필수) | repair 중심 정제 + 커버리지 유지 |
| `axis_ledger_path` | `docs/research/condition_research/generated_conditions/axis_ledger.jsonl` | Phase 3 T3.3 |
| `record_replay_profile` | `true` (CANONICAL 대비 diff 영수증) | Phase 0 T0.1 |
| `slippage_profiles_enabled` | `true` (advisory 병기 — 랭킹 불변) | Phase 0 T0.2 |
| 공식 replay 파라미터 | betting "5" / avg_time 30 고정 (`CANONICAL_REPLAY_PROFILE_V1`) | replay 포렌식 동결 |

실행 스켈레톤: 직전 검증 run 스크립트
`artifacts/process-research-validation-20260701/run_process_research_validation.py`를 복제해
run별 신규 스크립트를 만든다(기존 파일 수정 금지). 후보 팩 생산은
`ai_strategy_loop/brain/pack_producer.py`(`produce_candidate_pack`, partial/shortfall 정직 기록,
결정론 폴백 = prompt credit 0), strict validation은
`cli/condition_generator.py`의 `validate_multi_hypothesis_candidate_pack`을 그대로 쓴다.

## 2. 입력 시드 풀

| 소스 | 내용 | 진입 조건 |
|---|---|---|
| Plan C 생존자 | `css_v7_validation_ledger.jsonl`의 `final_status=survivor` 쌍 | Plan C 단계 3 통과 |
| 기존 검증 시드 | `rr8_12_turnover_min_902=1.5` 계열 (`GATE_rr8_12_turnover_min_902_1_5_B/S`, passport `condition_passports/rr8_12_turnover_min_902_1.5.md`) — 안정 기준선 | 이미 4/4 OOS-style 통과 |
| 격자(lattice) 시드 | `python -m cli.seed_lattice build --out-dir docs/research/condition_research/generated_conditions/lattice` (144셀×패밀리 4=576시드, passport 자동 생성) → 셀 단위 스모크(`evaluate_smoke_budget`, 창 비례 예산)와 coverage(`python -m cli.seed_lattice coverage --seeds ... --results ... --out coverage_map.json --gaps-out coverage_gaps.json --min-trades 300`)로 `go` 셀만 | 스모크 `go` + coverage gap 우선 |

시드 풀 관리 규칙:

- **passport 필수**: passport 없는 시드는 풀에 넣지 않는다(격자는 자동 생성, Plan C 생존자는 chart_sulsa passport 재사용, 신규는 `ai_strategy_loop/seeds/passport.py` 형식).
- **sha 추적**: 풀 등재 시 buy/sell 코드 sha256을 재계산해 passport 값과 대조 — 불일치 시 등재 금지·충돌 보고.
- 풀 원장(신규 파일): `docs/research/condition_research/generated_conditions/seed_pool.jsonl` — append-only.
  `{"seed_id","source":"plan_c|verified|lattice","passport_path","buy","sell","buy_sha256","sell_sha256","status":"active|frozen|exhausted","rounds_done":n,"best":{...},"ts"}`
  상태 변경도 새 행 append(수정 금지). 우선순위: Plan C 생존자 → rr8_12 계열 → 격자(coverage gap 순).
- 동시 active 시드는 1개(직렬) — 멀티스타트는 §4의 전환 규칙으로 구현한다.

## 3. 라운드 구조 (active 시드당 1라운드 = 아래 4스텝)

run_id 규칙: `seedref_<seed_id축약>_r<라운드번호>_<YYYYMMDD>`. 매 라운드 시작 전 positive control(§6) 확인.

### R-a. Ablation — 무효 절 제거 실험

1. `ai_strategy_loop/autopsy/ablation.py`의 `parse_top_level_clauses`로 시드 buy/sell 절 분해 → 직전 공식 run의 per-trade 풀에서 절별 통과율/제거 효과/자카드 산출(CSV 후처리 — 백테스트 없음).
2. `VERDICT_INEFFECTIVE`(단독으로 아무 행도 거르지 않음) 절이 있으면 해당 절 제거 변형(`<시드>_VAR{n}`)을 만들어 **공식 replay 1회**로 등가 확인. 성과 동등(사전선언: profit ±2% 이내, MDD 비악화)이면 단순화 구조를 라운드의 새 부모로 채택.
3. ablation의 변이축 제안 목록을 R-b 입력으로 넘긴다.

### R-b. 축 원장 사전확률 반영 변이

1. `ai_strategy_loop/controller/axis_ledger.py`: `AxisLedger` 로드 → `aggregate_axis_priors` → `to_prompt_lines`를 Context Pack에 주입(연구 루프 배선은 `axis_ledger_path`로 자동).
2. **`banned_axes` 자동 준수**(기본: 시도 n≥3 & 개선확률 ≤0.2 → 금지): 금지 축 변이는 생성 단계에서 제외한다. 수동 예외는 금지(데이터로만 해제 — 신규 증거가 사전확률을 바꿀 때).
3. 변이는 단일축 원칙: buy-only 또는 sell-only 레인 분리, paired repair는 각 축 단독 효과 확인 후에만(2026-07-01 핸드오프 규칙).

### R-c. 다후보 8슬롯 생성·평가

1. B3 config(§1)로 process-research 1 iteration 실행: 부모 buy/sell 전문+sha, Analysis Card, 축 원장 라인, R-a/R-b 산출을 Context Pack에 포함(250k budget).
2. 후보 8개(repair 5 / discovery 3) → strict validation(전문 누락·R_/S_ 누수·authority 밀반입 차단) → DB 저장은 INSERT-only·백업·dry-run 규칙(§0) → 공식 replay 전건.
3. 결과는 trade_ledger 적재 + 후보별 Analysis Card + 슬리피지 advisory 병기. 실패/부분 생산은 partial/shortfall로 정직 기록(슬롯 수 조작 금지).

### R-d. 교차비교 매트릭스 → 라운드 판정

1. 라운드 교차비교 매트릭스(Phase 3 T3.4 — 후보×지표+변이 귀속 아티팩트, opt-in 저장)를 생성해 8후보+부모를 한 표로 비교한다.
2. 라운드 판정(사전선언 — train 프레임, OOS 접촉 없음):
   - **개선**: 부모 대비 (profit 비열등 & MDD 개선) 또는 (profit 개선 & MDD 비악화)이고 trades가 부모의 50% 이상인 후보 존재 → 최량 후보를 다음 라운드 부모로 승계(`_VAR{n}` 네이밍, passport 신규 발급).
   - **무개선**: 위 후보 없음 → `rounds_no_improve += 1`.
3. 모든 후보의 변이축 결과를 `AxisLedger.append`로 축 원장에 기록(개선/악화 verdict — mdd_pct 키 규약 준수). 기각 후보는 revival 등재.

### 시드 동결(라운드 체인 종료) 시

- 최종 부모를 동결하고 **그때 1회** 고정 OOS + V4/롤링 분해(Plan C §7 기준 그대로: OOS 판정 v2 — 비열등·MDD캡·무붕괴, `trades<20` advisory, HOLD-OK 경로) 실행. `--trial-runs`에 라운드 전 시도(스모크·ablation 변형 포함) 합산.
- OOS 통과 → `OOS 생존자` 명부(`generated_conditions/oos_survivors.jsonl`) 등재 → §5 통합 대상. 기각 → revival 등재 + 시드 상태 `frozen`.

## 4. 경향 학습·전환 규칙 (국소최적 대응 — 멀티스타트)

| 규칙 | 내용 |
|---|---|
| 축 원장 학습 | 매 라운드 축별 verdict 축적 → 사전확률이 다음 라운드 프롬프트에 자동 주입, `banned_axes` 자동 갱신 |
| 3라운드 무개선 동결 | `rounds_no_improve == 3` → 시드 상태 `frozen`(동결 OOS 절차 실행 후) + seed_pool 다음 우선순위 시드로 전환 |
| 재방문 | frozen 시드는 삭제 아님 — 새 증거(신규 데이터 도착, 축 원장 사전확률 변화)가 생기면 revival 규율(`all_no_selection` — 전수 재검증, 선별 금지)로만 복귀 |
| 다양성 보존 | discovery 3슬롯은 coverage gap(`coverage_gaps.json`)·feature family·market segment 강제 — repair 수렴으로 인한 탐색 소멸 방지 |

## 5. 통합 — 포트폴리오 결합과 명예의 전당 상대 지표

발동 조건: `oos_survivors.jsonl`에 **OOS 생존자 2개 이상**.

1. `ai_strategy_loop/portfolio/assembler.py`로 결합 평가:
   - 일별 손익 상관 **< 0.5 캡**(초과 제외 시 제외 사유 기록 필수), 최소 중첩 20거래일.
   - **시간대 상보성**: tick(09:00~09:30)×min(풀세션) 조합 우선.
   - 결합 MDD·결합 지표는 **포트폴리오 측정 프레임 라벨**(`fitness/measurement_frame.py`)을 반드시 부착 — 단일 전략 프레임 수치와 직접 비교 금지.
2. 명예의 전당 상대 지표(**portfolio 프레임 전용**): `ai_strategy_loop/dashboard/reference_strategies.json`의 인간 검증 19전략 대비 TPI·payoff·MDD비를 세션마다 기록.
   - **목표 정의(도달 선언이 아니라 격차 추적)**: 포트폴리오 프레임에서 **TPI 1.25+ / MDD 2~7%** 접근(명예의 전당 연 130~262% / MDD 2~7% / TPI 1.25+ 범위 대비 격차 시계열 유지).
3. 이 단계 산출은 전부 advisory — `promotion_preconditions`의 `can_promote`는 항상 False(fail-closed) 계약 그대로다. export/live/final promotion 금지 불변.

## 6. 운영 규칙

### 세션당 기록 의무

| 산출물 | 경로/형식 |
|---|---|
| 연구 3종 문서 | `docs/research/condition_research/research_runs/<run_id>_plan.md` / `_management.md` / `_result.md` |
| update_log | `docs/update_log/<날짜>_<주제>.md` 1건(라운드 요약 + 커밋 해시) |
| 기계가독 원장 | `seed_pool.jsonl`, `axis_ledger.jsonl`, `oos_survivors.jsonl`, revival JSONL — 전부 append-only |
| 영수증 | replay profile diff, engine fallback, safety, positive control, 교차비교 매트릭스 — run별 `artifacts/<run_id>/` |

### positive control 주기

- **매 세션 시작 시 1회** + 공식 replay 누적 20회마다 1회:
  `python scripts/run_positive_control.py <직전 공식 결과 JSON> --use-reference-baselines --gate-config ai_strategy_loop/state/run_p5_validation_tick_late.json --report artifacts/<run_id>/positive_control_receipt.json`
- 기준: 직전 실측 19/19 `gate_healthy`. 실패 시 모든 판정 중단 → 게이트 조사 우선(측정계 오염 상태의 라운드 결과는 무효 처리하고 원장에 사유 기록).

### KPI (성공/중단)

| 구분 | 지표 | 기준 |
|---|---|---|
| 성공(프로세스) | 시드당 평균 라운드 수, 라운드당 개선 후보 비율, 축 원장 사전확률의 예측 적중률 | 추이 개선 |
| 성공(결과) | OOS 생존자 수(목표: 프로그램 1기당 2+), 포트폴리오 프레임 TPI/MDD 격차 축소 | §5 목표 접근 |
| 중단 | positive control 실패 / 시드 풀 소진 / **3시드 연속 전-라운드 무개선** | 즉시 중단 → 프로세스 재검토 보고서 작성 후 재개 판단 |

## 7. 역할 분담 (3역할 — 같은 세션에서 겸임 금지, 작성/검증 레인 분리)

| 역할 | 입력 | 출력 | 금지사항 |
|---|---|---|---|
| **발굴 에이전트** | seed_pool, 부모 전문+sha, Analysis Card, 축 원장 프롬프트 라인, coverage gaps | 후보 팩(가설 id·변이축·기대효과·risk note 포함), R-a/R-b 산출 | 공식 판정·DB `--apply` 저장·OOS 접촉·banned_axes 변이 생성·자기 후보 자체 승인 |
| **검증 에이전트** | 후보 팩, B3 config, 창 config | strict validation 결과, 공식 replay receipt, 교차비교 매트릭스, 라운드/OOS 판정, 축 원장 append | 후보 수정·신규 생성, 판정 기준 임의 변경, 승격/export, n_trials 누락 |
| **기록 에이전트** | 전 receipt·판정 | 3종 문서, passport 발급/갱신, seed_pool·provenance·revival 원장 append, update_log | 수치 재계산·판정 번복, 원장 기존 행 수정, 커밋 파일 수정 |

핸드오프는 파일(원장·receipt)로만 한다 — 구두 전달 수치 사용 금지. 각 역할은 자기 산출물의 경로 목록을 세션 종료 시 management 문서에 남긴다.

## 8. 프로그램 종료 조건

- 1기(program cycle) 종료: 시드 풀 우선순위 상위 3개 시드가 각각 동결(OOS 판정 완료)되고, §5 통합 평가가 1회 이상 수행되며, KPI 표가 result 문서에 채워지면 종료. 차기 프로그램은 이 문서의 개정판(신규 파일)으로 계획한다.
