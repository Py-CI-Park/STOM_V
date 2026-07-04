# 계획서 B — 조건식 연구 실행 로드맵 B1~B5 (2026-07-02)

> 권위: advisory_only (연구 레인 실행 계획). 근거:
> `docs/update_log/2026-07-02_ai_loop_phase_implementation_record.md` "다음 실행 순서",
> `docs/research/condition_research/2026-07-02_ai_loop_execution_checklist.md`.
> 이 문서만 읽고 다른 에이전트가 실행 가능하도록 정확한 명령·경로·완료 기준·중단
> 조건을 명시한다. 실행 순서는 B1 → B2 → B3 → B4 → B5 (B2는 B1 스모크 산출을 소비).

## 0. 공통 불변 조건 (전 단계, 위반 = 즉시 중단)

1. **연구 레인 전용**: 생성·저장하는 모든 조건식은 '무근거 가설 시드(hypothesis_seed)'
   라벨 필수. 승격/export/live 코드·데이터 접근 금지. `backtest/graph/` 불가침.
2. **전략 DB 조작**: INSERT만 허용(기존 행 UPDATE/DELETE 절대 금지). 실저장 전 DB 파일
   백업 필수. 이름 충돌 시 저장하지 말고 충돌 보고. dry-run 기본, `--apply` 명시 시에만
   저장. 주의: 기존 `cli/strategy_generator.py:144 save_strategy_to_db`는 이름 존재 시
   **UPDATE**하므로 연구 레인에서 그대로 쓰면 규칙 위반 — 반드시 사전 충돌 검사 후
   INSERT 경로만 태운다.
3. **출처 기록(provenance)**: 모든 조건식은 원천 문서 경로+문서 sha256+섹션+코드
   sha256+DB 저장명을 기계가독 원장(JSONL)과 md 문서 양쪽에 남긴다. (격자 시드는
   passport md + `lattice_seeds.json`의 `buy_sha256/sell_sha256`이 이 요건의 절반을
   충족 — DB 저장명 매핑 원장은 B1.3에서 추가로 만든다.)
4. 기존 커밋 파일 수정 금지(신규 파일 + `_database`/`ai_strategy_loop/state` 데이터만).
   파일당 800줄 이하, 신규 CLI는 print 금지(`sys.stdout.write`).
5. 전체 테스트 스위트 실행 금지 — 자기 테스트만.
6. Python 실행은 항상 UTF-8 강제: `PYTHONUTF8=1` (PowerShell:
   `$env:PYTHONUTF8='1'`) 또는 `python -X utf8`.
7. **공식 replay 프로파일 준수**(본 검증 실행): `betting "5"`(500만원)/`avg_time 30`/
   엔진 64(실패 시 fallback 32) — 정본은
   `ai_strategy_loop/controller/replay_profile.py:119` `official_replay_v1_20260702`
   (tick, 20250101~20251231, 90000~92800, `_database/stock_tick_back.db`, 2025 기준선
   +3,062,696/190거래/MDD 12.87). 스모크는 2025Q1 서브셋 예외를 명시 허용.
8. n_trials 정직 합산·부활 레지스트리·OOS-blind 동결 규율 유지. 스모크도 trial이다.
9. 각 단계 종료 시 `docs/update_log/`에 신규 실행 기록 md를 남긴다(§7).

---

## B1 — 격자 채굴 (576 시드 생성 → 야간 배치 백테스트)

### B1.1 격자 생성 (실측 CLI)

```
PYTHONUTF8=1 python -m cli.seed_lattice build --out-dir docs/research/condition_research/generated_conditions/lattice
```

- 선택 인자: `--lane tick|min`(반복 지정), `--family <이름>`(반복 지정, 기본 전체 4
  패밀리: momentum_breakout/volume_surge/strength_surge/prevday_active),
  `--families-json <외부 JSON>`(불변 병합), `--skip-passports`.
- 산출:
  - `docs/research/condition_research/generated_conditions/lattice/lattice_seeds.json`
    (schema `seed_lattice_seeds_v1`, 144셀×4패밀리=576시드; 시드 필드:
    `condition_id/cell_id/family/buy_code/sell_code/buy_sha256/sell_sha256/params/
    created_reason/passport_md`)
  - 같은 디렉토리 아래 passport md 576장(시드당 1장, hypothesis_seed 라벨 포함).
- 완료 기준: stdout JSON에 `"seed_count": 576` (lane 필터 시 비례 감소), seeds JSON
  schema 일치.
- 중단 조건: `미등록 패밀리`/schema 오류 SystemExit, seed_count 0.

### B1.2 시드의 DB 등재 (신규 스크립트 — dry-run 기본)

배치 러너(`claude_candidate_batch_eval`)는 전략명을
`ai_strategy_loop/state/loop_strategies.db`의 `stockbuy/stocksell.index`에서 읽는다
(스크립트 docstring 실측; `ai_strategy_loop/bootstrap.py:30`이 이 경로를
`STOM_CLI_DB_STRATEGY`로 주입). **live `_database/strategy.db`가 아니라 이 연구 전용
DB에만 등재한다.**

신규 스크립트 `ai_strategy_loop/scripts/register_lattice_seeds.py`(신규 파일)를 작성해
실행한다. 필수 사양:

- 입력: `--seeds <lattice_seeds.json>` `--db <기본 ai_strategy_loop/state/loop_strategies.db>`
  `--pairs-out <pairs.json>` `--ledger-out <provenance JSONL>` `--apply`(생략 시 dry-run).
- 이름 규약: buy=`LAT_<condition_id>_B`, sell=`LAT_<condition_id>_S` (condition_id는
  시드 JSON의 결정론 식별자).
- 동작: (1) `--apply` 시 DB 파일을 `<db>.bak_<YYYYMMDD_HHMMSS>`로 먼저 복사(백업 필수),
  (2) 대상 테이블에서 이름 존재 여부 사전 조회 — **충돌 시 해당 시드 저장 없이 충돌
  목록 보고**(UPDATE 금지), (3) 신규만 `INSERT INTO stockbuy/stocksell ("index",
  "전략코드") VALUES (?, ?)` 파라미터 쿼리, (4) provenance 원장 JSONL 1줄/시드:
  `{"condition_id","cell_id","family","buy_sha256","sell_sha256","db_buy_name",
  "db_sell_name","source_doc":"generated_conditions/lattice/lattice_seeds.json",
  "source_schema":"seed_lattice_seeds_v1","passport_md",...,"label":"hypothesis_seed"}`,
  (5) pairs.json: `[{"label": "<condition_id>", "buy": "LAT_..._B", "sell":
  "LAT_..._S"}, ...]` (label에 condition_id를 넣어야 결과→셀 역매핑이 가능하다).
- 완료 기준: dry-run 보고(등재 예정/충돌 0) 확인 → `--apply` 후 등재 수=시드 수,
  원장 JSONL 줄 수 일치, 백업 파일 존재.
- 중단 조건: 충돌 1건 이상(보고 후 사용자 판단 대기), 백업 실패, DB 잠금.

### B1.3 스모크 배치 실행 (2025Q1 서브셋 — 야간 1차)

러너(실측):

```
PYTHONUTF8=1 python -m ai_strategy_loop.scripts.claude_candidate_batch_eval `
  --pairs-json docs/research/condition_research/generated_conditions/lattice/pairs_tick.json `
  --config-json docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_tick.json `
  --run-id lat_smoke_tick_20260702
```

스모크 config(기존 검증 실적 있는
`.omo/evidence/claude-condition-research-20260610/smoke-config.json`을 신규 경로로
복사·수정해 사용 — LLM 0회, provider 미호출):

```json
{
  "provider": "gpt_auth",
  "bt_engine_mode": "warm",
  "bt_warm_engine_count": 8,
  "bt_betting": "5",
  "bt_avg_time": 30,
  "bt_timeframe": "tick",
  "bt_full_start": 20250101,
  "bt_full_end": 20250331,
  "bt_universe_start_time": 90000,
  "bt_universe_end_time": 92800,
  "min_daily_trades": 0.3,
  "mdd_cap": 35,
  "winner_objective": "uptrend",
  "autopsy_enabled": false,
  "max_generations": 1,
  "bt_timeout": 900,
  "bt_warm_run_timeout": 300,
  "equity_points_enabled": true
}
```

- 스모크는 2025Q1(90일 창) 서브셋 — 공식 프로파일의 betting/avg_time/시간창은 준수,
  기간·엔진 수만 축소(창 비례 예산 판정은 B2).
- min 레인 스모크는 2025-05-01~2025-05-31 창(`bt_timeframe: "min"`,
  `bt_full_start: 20250501, bt_full_end: 20250531` — min 검증 프로토콜
  `2026-06-12_min_timeframe_validation_protocol.md` §3의 사전선언 창).
- **야간 배치 순서: tick 먼저 → min.** 근거: tick DB는 09:00~09:30만 존재(952일)라
  셀 시간밴드가 시초 30분 집중이고 공식 기준선·OOS 자산이 tick에 몰려 있다 — tick
  결과가 이후 단계(B2 예산)의 주 입력이다. min은 tick 배치 완주 확인 후 이어서 건다.
- 결과 저장: 러너가 `loop_runs.db`(대시보드 호환)에 세대 기록. run 완료 후 결과 요약
  JSON(셀 역매핑용 — `cell_id`(=label에서 파싱)+`profit`+`trades`+`run_id` 필드)을
  신규 소형 스크립트 `ai_strategy_loop/scripts/export_lattice_results.py`(신규,
  loop_runs.db에서 run_id의 세대 행을 읽어 `{"results": [...]}` JSON으로 내보냄)로
  추출해 `docs/research/condition_research/research_runs/seed_lattice_20260702/
  smoke_results_tick.json`에 저장한다.

### B1.4 본 스윕 (B2 go 셀만 — 공식 프로파일)

본 스윕 config는 스모크 config에서 다음만 변경: `bt_full_start: 20250101`,
`bt_full_end: 20251231`, `bt_warm_engine_count: 64`. 엔진 64로 prepare 실패/불안정
시 **fallback 32**로 1회 재시도(공식 프로파일의 fallback_engine_count=32 — 이 사실을
run 기록에 남긴다). pairs는 B2의 go 셀 소속 시드만 필터한 `pairs_tick_go.json`.

### B1.5 타임아웃·고아 프로세스 대응 (필수 위생)

- config의 `bt_timeout: 900` / `bt_warm_run_timeout: 300`은 유지(쌍 단위 타임아웃 —
  러너가 개별 실패를 흡수하고 다음 쌍 진행).
- 배치 비정상 종료(콘솔 강제 종료, 세션 타임아웃 등) 후에는 반드시:

```
PYTHONUTF8=1 python scripts/cleanup_orphan_backtest_procs.py --older-than-minutes 30
```

  (dry-run 기본 — 후보 목록만 출력). 목록을 **눈으로 확인**해 현재 실행 중인 정상
  배치의 pid가 없음을 확인한 뒤에만:

```
PYTHONUTF8=1 python scripts/cleanup_orphan_backtest_procs.py --older-than-minutes 30 --kill --report docs/research/condition_research/research_runs/seed_lattice_20260702/orphan_cleanup_receipt.json
```

  진행 중 배치가 있으면 `--exclude-pid <pid>`로 보호한다.

### B1.6 완료 기준 / 중단 조건 / 예상 소요 / 산출물

- 완료 기준: tick 스모크 576쌍(레인 필터 시 해당 수) 전 쌍이 ok 또는 정직 error로
  기록되고 `smoke_results_tick.json` 추출 완료. min 동일.
- 중단 조건: (a) prepare `status != ok` 2회 연속(64→32 fallback 포함), (b) 동일
  오류로 연속 20쌍 error(러너 정상이 아님 — 원인 조사로 전환), (c) 디스크 여유 <10GB.
- 예상 소요(정직 추정 — 실측 전): warm prepare 수 분 + 쌍당 12초(min E2E 실측)~
  수십 초(tick 2025Q1). 576쌍 스모크 = 대략 2~8시간/레인 → **야간 1교대**. 첫 10쌍
  경과로 총 소요를 재추정해 기록하고, 야간 완주 불가 판단 시 family 단위로 분할한다.
- 산출물: `docs/research/condition_research/research_runs/seed_lattice_20260702/`
  아래 config 2종, pairs 2종, smoke_results 2종, provenance 원장 JSONL, (본 스윕 후)
  full_results JSON.

---

## B2 — 예산 판정 (coverage / smoke-plan, go/no-go)

### B2.1 명령 (실측 CLI)

```
PYTHONUTF8=1 python -m cli.seed_lattice coverage `
  --seeds docs/research/condition_research/generated_conditions/lattice/lattice_seeds.json `
  --results docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_results_tick.json `
  --out docs/research/condition_research/research_runs/seed_lattice_20260702/coverage_tick.json `
  --gaps-out docs/research/condition_research/research_runs/seed_lattice_20260702/coverage_gaps_tick.json `
  --min-trades 300

PYTHONUTF8=1 python -m cli.seed_lattice smoke-plan `
  --coverage docs/research/condition_research/research_runs/seed_lattice_20260702/coverage_tick.json `
  --smoke docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_results_tick.json `
  --out docs/research/condition_research/research_runs/seed_lattice_20260702/batch_plan_tick.json `
  --min-trades 300 --window-days 90
```

min 레인은 `--window-days 31`(2025-05 창)로 바꿔 동일 실행.

### B2.2 go/no-go 기준 (창 비례 — 실측 `ai_strategy_loop/seeds/smoke_budget.py`)

- 임계 = `-2,000,000 × min(1.0, window_days / 90)` (축소 전용, 확대 없음).
  90일(2025Q1)=-2,000,000 그대로, 31일(min 5월)≈-688,889 (프로토콜 문서의 -500,000
  선언과 다르면 **더 보수적인 쪽(-500,000)을 채택**하고 기록에 사유를 남긴다).
- `profit <= 임계` → no_go (경계 포함). NaN/inf → no_go (fail-closed).
- **advisory 원칙(위반 금지)**: verdict는 '본 스윕 자원 배분'에만 사용. 후보 선택·
  동결(freeze)·승격 판단 사용 금지(payload의 `advisory_only/forbidden_uses`가 기계
  표식). no_go는 영구 폐기가 아니라 대기열 후순위 강등이다.

### B2.3 부활 레지스트리 등재 규칙 + n_trials 정직 합산

- no_go 셀의 시드는 `ai_strategy_loop/seeds/revival_registry.py`의
  `register_rejected(...)`(schema `seed_revival_registry_v1`, JSONL append)로 등재한다.
  레지스트리 경로(고정): `docs/research/condition_research/research_runs/
  seed_lattice_20260702/revival_registry.jsonl`. 등재 없이 버리는 것 금지.
- 재검증 추출은 `pending_revalidation(...)`/`load_registry(...)` 사용(등재 행 삭제 금지
  — append 전용).
- **n_trials 정직 합산**: 스모크도 trial이다. `evaluate_smoke_budget` 반환의
  `attempt` 필드를 이후 동결 시 `--trial-runs` n_trials 합산에 포함해야 한다(누락
  금지). 셀별 attempt 누계를 batch_plan JSON과 update_log 양쪽에 기록한다.

### B2.4 완료 기준 / 중단 조건 / 예상 소요 / 산출물

- 완료 기준: 레인별 coverage/gaps/batch_plan JSON 3종 산출 + go/no_go 셀 수 집계 +
  no_go 시드 전량 부활 레지스트리 등재.
- 중단 조건: coverage가 seeds schema 불일치 SystemExit, 결과 JSON에 cell 역매핑
  불가(라벨 파싱 실패) 시드가 10% 초과(B1.2 라벨 규약 위반 — B1로 회귀).
- 예상 소요: 계산 자체는 분 단위. 검토 포함 1~2시간.
- 산출물: 위 JSON 3종×2레인 + revival_registry.jsonl.

---

## B3 — 정제 라운드 (연구 루프 반복 — 분석·환류 full 배선)

### B3.1 조건식 연구 루프 config (ResearchLoopConfig — 실측 필드명 전문)

go 셀 상위 시드(본 스윕 성적순)를 부모로 `cli/ai_controller.py`
`research_strategy_once(config_dict)` 경로(= `run_research_iteration`)를 돌린다.
config_dict 예시 (필드명 전부 `cli/research_loop.py:142-246` 실측):

```json
{
  "name": "LAT_REFINE_R1_tick_0900_mid_low",
  "base_buy_strategy": "LAT_<condition_id>_B",
  "sell_strategy": "LAT_<condition_id>_S",
  "is_tick": true,
  "betting": "5",
  "avg_time": 30,
  "start_date": 20250101,
  "end_date": 20251231,
  "start_time": 90000,
  "end_time": 92800,
  "run_candidates": true,
  "candidate_count": 8,
  "candidate_name_prefix": "LATR1",
  "condition_discovery_process": "process-research",
  "record_replay_profile": true,
  "slippage_profiles_enabled": true,
  "context_pack_enabled": true,
  "axis_ledger_path": "docs/research/condition_research/research_runs/seed_lattice_20260702/axis_ledger.jsonl",
  "round_matrix_enabled": true,
  "round_matrix_output_dir": "docs/research/condition_research/research_runs/seed_lattice_20260702/round_matrix",
  "candidate_slots_override": 8,
  "candidate_lane_quota": {"repair": 4, "discovery": 4},
  "llm_candidate_pack_enabled": false,
  "runtime_output_path": "docs/research/condition_research/research_runs/seed_lattice_20260702/refine_r1_runtime.json"
}
```

주의 사항 (실측 계약):

- `condition_discovery_process`는 `"process-research"`(=프리셋 `research`) —
  `"promotion-review"` 사용 금지(B4 전용).
- `candidate_slots_override`는 2~12 정수만, `candidate_lane_quota`는 두 레인 합계가
  override와 정확히 일치해야 하며 위반은 fail-closed로 반복 시작이 거부된다.
- **`llm_candidate_pack_enabled`는 provider 준비 조건부**: 계획서 A의 A2(상위 진입점
  배선)가 커밋되기 전에는 `research_strategy_once`가 provider를 전달할 수 없으므로
  `false`로 둔다(true여도 provider 미주입이면 결정론 폴백(credit 0)으로 자연 낙하 —
  거짓 크레딧은 없지만 의도를 명시하라). A2 커밋 후에는 `true` +
  `"llm_pack_provider": "gpt_auth"`(또는 `"openrouter"`) 키를 추가한다.
- 이 필드들은 CLI 미노출 — Python API로 전달한다(신규 실행 스크립트에서
  `from cli.ai_controller import AIController` 후 `controller.research_strategy_once(
  config_dict)` 호출, 또는 기존 검증 하네스 패턴 재사용).

### B3.2 발굴 루프(ai_strategy_loop) 병행 시 — 환류 4종 병합

발굴 루프(`python -m ai_strategy_loop.controller.loop --config-json <json>`)를 병행할
경우, config dict에 `ai_strategy_loop/config.py:656`
`research_feedback_config_overrides()`의 정본 4종을 병합한다:

```json
{
  "segment_feedback_enabled": true,
  "quantile_feedback_enabled": true,
  "hypothesis_tracking_enabled": true,
  "feature_importance_feedback_enabled": true
}
```

병합 방법(코드에서): `LoopConfig.from_dict({**base_dict,
**research_feedback_config_overrides()})`. JSON 파일로 줄 때는 위 4키를 직접 추가.
전역 기본은 전부 OFF — 이 병합은 연구 레인 명시 opt-in이다.

### B3.3 라운드당 산출물 확인 목록 (전부 존재해야 라운드 인정)

| 산출물 | 확인 위치 |
|---|---|
| runtime JSON (체크포인트·결과) | config의 `runtime_output_path` |
| replay 영수증 | 결과 dict additive 키(`record_replay_profile` — 공식 프로파일 대비 diff 확인) |
| 슬리피지 프로파일 tick0/1/2/3 | 후보 결과 `slippage_profiles` (advisory) |
| Analysis Card | 부검 산출(`ai_strategy_loop/autopsy/analysis_card.py` 소비 경로) — insufficient_data 정직 라벨 허용 |
| ablation (절 분해) | `ai_strategy_loop/autopsy/ablation.py` 산출 — 변이축 제안 확인 |
| 라운드 교차비교 매트릭스 | `round_matrix_output_dir` JSON+md, 결과 dict `round_matrix` 요약 키 |
| 축 원장 | `axis_ledger_path` JSONL 행 증가 + 후보별 delta 기록/스킵 사유 |
| Context Pack 영수증 | analysis_result의 `context_pack_id/context_pack_sha256/research_context_pack_receipt` (전문은 영속 안 함 — 정상) |

### B3.4 판정·다음 라운드 결정 규칙

1. 라운드 종료 후 `round_matrix`의 "baseline 대비 개선 후보 수"와 best_candidate의
   comparison(항상 공식 프로파일 성적 기준)을 확인한다.
2. 개선 후보 ≥1 → best를 다음 라운드 부모로 승계(이름은 `candidate_name_prefix`
   증가). 개선 0 → 축 원장(`axis_ledger.jsonl`)의 축별 사전확률을 검토해 악화 축을
   피하는 방향으로 레인 쿼터/부모를 조정해 1회 재시도.
3. **2라운드 연속 개선 0** → 해당 셀 정제 종료, 다음 go 셀로 이동(셀은 부활
   레지스트리에 attempt 누계와 함께 기록).
4. 모든 라운드 attempt는 n_trials 합산에 포함. 후보의 OOS 데이터(2022, 2026,
   min 2026-01~02)는 **이 단계에서 절대 조회 금지**(OOS-blind — B4 전용).
5. 라운드당 예상 소요: baseline+후보 8개 백테스트 — 공식 프로파일(2025 전체,
   엔진 64)로 쌍당 수 분 → 라운드당 30분~2시간(첫 라운드 실측으로 재추정).
- 중단 조건: validate 단계 fail-closed 거부(config 오류 — 수정 후 재시도 1회),
  `max_consecutive_candidate_failures`(기본 3) 초과 반복, 디스크/DB 잠금 오류.

---

## B4 — 검증 승격 (고정 OOS · walk-forward — 기존 프로토콜)

### B4.1 프로토콜 문서 (정본 — 실행 전 필독)

- tick 고정 OOS: `docs/research/condition_research/
  2026-06-12_oos_false_negative_and_gap_research.md` — 고정 OOS 2022(1년) +
  2026(2개월), 9건 표본 거짓 기각 17~27% 논의와 완화 규칙.
- 프로세스 v2 판정 규칙: `2026-06-12_process_v2_and_seed_reresearch_plan.md`.
- min 레인: `2026-06-12_min_timeframe_validation_protocol.md` — train
  2025-04-08~2025-12-31, 고정 OOS 2026-01-01~2026-02-27(동결 후에만, 사용 횟수 공시),
  V4 walk-forward(분기 fit→월 eval 롤링)가 1차 일반화 증거.
- 스모크 규약: `2026-06-12_smoke_screening_protocol.md`.

### B4.2 실행 (동결 후에만 OOS 개봉)

1. B3 생존 후보를 **동결 선언**(update_log에 후보명·코드 sha256·n_trials 누계 기록)
   한 뒤에만 OOS 창을 실행한다.
2. OOS 백테스트는 B1.4와 동일 러너/OOS config(기간만 교체: tick 2022 =
   `bt_full_start 20220101, bt_full_end 20221231`(tick DB 커버리지 확인 선행),
   2026 = `20260101~20260227`; min = `20260101~20260227`). betting/avg_time/시간창은
   공식 프로파일 유지.
3. walk-forward (기존 도구, 실측 CLI):

```
PYTHONUTF8=1 python -m ai_strategy_loop.scripts.tmap_walkforward `
  --template <템플릿명> --config-json <config> --run-prefix wf_<후보명> `
  --windows <창 정의> --washout-days 2 --out <결과 경로>
```

   `--washout-days 2` 권장(N7 전일참조 누수 완화 — help 실측).
4. 승격 검토는 **promotion-review 레인(zero-generation) 유지**:
   `condition_discovery_process: "promotion-review"`는 생성 0·판정만이며,
   `ai_strategy_loop/portfolio/promotion_preconditions.py`의
   `evaluate_promotion_preconditions`가 전부 통과해도 `can_promote=False` 고정이다.
   실제 승격/export는 이 로드맵 범위 밖(계획서 A의 A3 — 사용자 승인 사항).
- 완료 기준: 후보별 OOS 2창 + walk-forward 결과와 판정(프로토콜 문서 기준) 기록.
- 중단 조건: 동결 선언 없이 OOS 데이터에 접근하려는 어떤 경로든 발견 즉시 중단·보고
  (OOS-blind 위반). OOS 사용 횟수 공시 누락도 동일.
- 예상 소요: 후보당 OOS 2회 + walk-forward 1회 = 1~3시간.

---

## B5 — 포트폴리오 (assembler 결합 + 상시 위생 검사)

### B5.1 assembler 사용 (실측 API — `ai_strategy_loop/portfolio/assembler.py`)

OOS 생존자 2개 이상 확보 시:

- `combine_candidates(candidates, ...)`(`:549`) — **상관 캡 0.5**(초과 시 제외 사유
  필수 기록), 시간밴드 상보성, 결합 MDD 산출. 입력 후보에는 per-trade 데이터와
  시간밴드 메타를 포함시킨다.
- `load_reference_strategies()`(`:636`) + `compare_to_benchmark(...)`(`:703`) —
  명예의 전당 19전략 상대 지표.
- **측정 프레임 라벨 필수**: 포트폴리오 수치에는 `fitness/measurement_frame.py`의
  포트폴리오 전용 프레임 라벨을 병기한다(단일 전략 프레임과 비교 금지 — 프레임
  불일치 수치를 한 표에 섞지 않는다).
- 실행은 신규 소형 스크립트(신규 파일, 예:
  `ai_strategy_loop/scripts/assemble_lattice_portfolio.py`)로 결과 JSON을
  `docs/research/condition_research/research_runs/seed_lattice_20260702/portfolio/`
  에 저장.

### B5.2 상시 위생 검사 (주기: 각 단계 종료 시 + 최소 주 1회)

```
PYTHONUTF8=1 python scripts/run_positive_control.py --use-reference-baselines `
  --report docs/research/condition_research/research_runs/seed_lattice_20260702/positive_control_receipt.json

PYTHONUTF8=1 python scripts/check_research_evidence_lineage.py `
  --report docs/research/condition_research/research_runs/seed_lattice_20260702/lineage_report.json
```

- positive control 기대: 19/19 통과·gate_healthy(6/30 실측 기준). **불건전 판정 시
  연구 결과 해석을 전면 보류**하고 게이트 원인 조사로 전환(중단 조건).
- lineage 검사: summary·jsonl 일관성/문서 완결성 — 불일치 발견 시 해당 증거를
  사용하는 판정을 보류.
- 완료 기준: receipt 2종이 산출·보존되고 판정이 healthy/consistent.
- 예상 소요: 회당 수 분.

---

## 6. 단계별 요약표

| 단계 | 핵심 명령/도구 | 완료 기준 | 대표 중단 조건 | 예상 소요 |
|---|---|---|---|---|
| B1 | `cli.seed_lattice build` + 등재 스크립트 + `claude_candidate_batch_eval` | 576시드 생성·등재·스모크 전 쌍 기록 | 이름 충돌, prepare 실패 2연속, 연속 20쌍 error | 야간 1~2교대 |
| B2 | `cli.seed_lattice coverage/smoke-plan` | 판정 JSON 3종 + no_go 전량 레지스트리 등재 | 셀 역매핑 실패 >10% | 1~2시간 |
| B3 | `research_strategy_once`(Python API) | 라운드 산출물 8종 전부 + 판정 기록 | fail-closed config 거부, 2라운드 무개선 | 라운드당 0.5~2시간 |
| B4 | OOS config + `tmap_walkforward` | 동결→OOS 2창+WF 판정 기록 | OOS-blind 위반 | 후보당 1~3시간 |
| B5 | `portfolio.assembler` + 위생 스크립트 2종 | 포트폴리오 JSON + receipt healthy | positive control 불건전 | 1~2시간 |

## 7. 기록(update_log) 의무

각 단계 종료 시 `docs/update_log/2026-MM-DD_seed_lattice_<단계>_execution_log.md`
(신규 파일)를 작성한다. 필수 항목: 실행 명령 전문, config sha256, 산출물 경로,
go/no_go·개선/무개선 판정 수치, n_trials 누계, 부활 레지스트리 증분, 이상 징후와
대응(고아 프로세스 정리 receipt 포함), 다음 단계 착수 조건 충족 여부.
