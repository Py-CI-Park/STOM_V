# Plan C — chart_sulsa v7 조건식 타당성 평가 프로토콜 (2026-07-02)

> 대상: `CSS_V7_*` 조건식 25개(단독) + 문서 명시 권장 조합 2세트.
> 실행 주체: 후속 검증 에이전트. 이 문서 하나로 단계 0~4 전체를 실행 가능해야 한다.
> 산출: 생존/기각/보류 판정 + 기계가독 검증 원장 + Plan D 입력 시드 목록.

## 0. 불변 조건 (위반 시 즉시 중단)

1. 연구 레인 전용. 모든 조건식은 `hypothesis_seed` 라벨 유지. 승격/export/live 코드·데이터 접근 금지. `backtest/graph/` 불가침.
2. 전략 DB(`_database/strategy.db`, `ai_strategy_loop/state/loop_strategies.db` 등)는 **INSERT만 허용**(UPDATE/DELETE 절대 금지). 실저장 전 DB 파일 백업 필수. 이름 충돌 시 저장하지 말고 충돌 보고. dry-run 기본, `--apply` 명시 시에만 저장.
3. 출처 기록(provenance) 필수: 모든 검증 이벤트를 기계가독 원장(JSONL)과 md 문서 양쪽에 남긴다.
4. 기존 커밋된 파일 수정 금지(신규 파일 + `_database` 데이터만). 파일당 800줄 이하. CLI 출력은 `sys.stdout.write`(print 금지). 전체 테스트 스위트 실행 금지(자기 테스트만).
5. n_trials 정직 합산: 스모크 포함 모든 시도(run)는 시도로 등재하며, 동결 심사 시 `--trial-runs` 합산에서 누락 금지.
6. 기각은 삭제가 아니다: 기각 조건식은 부활 레지스트리(`ai_strategy_loop/seeds/revival_registry.py`, `REVALIDATION_POLICY=all_no_selection`)에 등재한다.

## 1. 입력 자산 (정찰 완료 상태)

| 자산 | 경로 | 상태 |
|---|---|---|
| 원문 HTML | `C:/System_Trading/chart_sulsa_stom_quant_insight_report_v7_0.html` | sha256 `454715a9faad0f6efcb0f24c12ad7dad0087a3d51afc5f9935c6d49c4b78f5d4` |
| 마스터 카탈로그 | `docs/research/condition_research/chart_sulsa/2026-07-02_chart_sulsa_v7_condition_catalog.md` | 25개 목록 + code sha256 + 조합 2세트 |
| 코드 전문 | 같은 디렉터리 `..._code_tick.md` / `..._code_min.md` | tick 9 / min 16 |
| Condition Passport | `docs/research/condition_research/condition_passports/chart_sulsa/*.md` (25개) | 페어링 규칙 포함 |
| provenance 원장 | `docs/research/condition_research/chart_sulsa/provenance_registry.jsonl` (27행) | 조건 25 + 조합 2 |
| DB 저장 영수증 | `docs/research/condition_research/chart_sulsa/db_insert_receipt_20260702.json` | `_database/strategy.db` stockbuy 14 / stocksell 11, 백업 `strategy.db.bak.chart_sulsa_20260702T142627Z` |
| conditions JSON | `ai_strategy_loop/brain/data/chart_sulsa_v7_conditions.json` | 12필드 스키마, opt_vars tick 27 / min 31 |

권장 조합(원문 §12.1 명시 — §4.4/§5.8에는 조합 산문 없음):

| 우선순위 | combo_id | buy | sell |
|---|---|---|---|
| 1 | `CSS_V7_COMBO_MIN_01_RETEST_PULLBACK_MASTER_SELL` | `CSS_V7_MIN_B_RETEST_PULLBACK_SWITCH_0900_1518` | `CSS_V7_MIN_S_MASTER_0900_1518` |
| 2 (장초반) | `CSS_V7_COMBO_TICK_01_MASTER_EARLY_SESSION` | `CSS_V7_TICK_B_MASTER_0900_0930` | `CSS_V7_TICK_S_MASTER_0900_0930` |

## 2. 평가 단위 정의 — 유니크 replay 쌍

- 페어링 규칙: **각 조건식의 passport에 기록된 `buy_strategy_id`/`sell_strategy_id` 쌍을 그대로 쓴다.** (buy 단독 조건은 같은 레인 `*_S_MASTER_*`와, sell 단독 조건은 같은 레인 `*_B_MASTER_*`와 페어링돼 있다. OPT는 OPT끼리.)
- 25개 passport 쌍에서 **중복 쌍을 제거**해 유니크 쌍 목록을 만든다. 조합 2세트는 각각 passport 쌍과 동일 쌍이므로 별도 실행이 아니라 **우선순위 태그만** 부여된다. 추정 유니크 쌍 ≈ 21개(tick ≈ 7, min ≈ 14) — 단계 0에서 기계적으로 산출·확정한다.
- 산출물: `artifacts/chart_sulsa_validation_20260702/pairs_unique.json` — 형식은 batch 러너 계약(`[{"label","buy","sell"}]`, §4 참조)에 `combo_priority`(1/2/null), `lane`, `passport` 필드를 추가한 확장형(러너에는 3필드만 투영).

## 3. 단계 0 — 정적 게이트 (완료 상태 기록 + 재확인)

**상태: 이미 통과 완료(2026-07-02 추출 시).** compile 25/25, 금지토큰/변수스코프 통과, 원리 게이트(`ai_strategy_loop/brain/principle_gate.py`, CSC-06/07/10) 통과, HTML↔JSON 양방향 sha 25/25 일치.

재확인 명령(읽기 전용 — 실행 세션마다 1회):

```powershell
# (1) DB 저장명·코드 sha256 대조 (provenance ↔ _database/strategy.db)
$env:PYTHONUTF8=1
python -X utf8 -c "
import json, sqlite3, hashlib, sys
w = sys.stdout.write
reg = [json.loads(l) for l in open('docs/research/condition_research/chart_sulsa/provenance_registry.jsonl', encoding='utf-8') if l.strip()]
con = sqlite3.connect('file:_database/strategy.db?mode=ro', uri=True)
bad = 0
for e in [r for r in reg if r.get('entry_type') == 'condition']:
    row = con.execute('SELECT 전략코드 FROM %s WHERE \"index\"=?' % e['db_table'], (e['db_name'],)).fetchone()
    if row is None:
        w('MISSING %s\n' % e['db_name']); bad += 1; continue
    sha = hashlib.sha256(row[0].encode('utf-8')).hexdigest()
    if sha != e['code_sha256']:
        w('SHA_MISMATCH %s\n' % e['db_name']); bad += 1
w('checked=%d bad=%d\n' % (len([r for r in reg if r.get('entry_type')=='condition']), bad))
"
# (2) tick 조건식의 09:00~09:30 시간창 가드 정적 확인 (시분초 < 93000)
python -X utf8 -c "
import sys, re
txt = open('docs/research/condition_research/chart_sulsa/2026-07-02_chart_sulsa_v7_condition_catalog_code_tick.md', encoding='utf-8').read()
sys.stdout.write('window_guards=%d\n' % len(re.findall(r'9(?:0000|0500)?\s*<=\s*시분초\s*<\s*93000|시분초\s*<\s*93000', txt)))
"
```

- 판정: (1)에서 `bad=0`이 아니면 **전체 중단 + 충돌 보고**(어떤 쓰기도 하지 않는다). (2)는 tick 9건 전부 가드 존재 확인(개별 코드 md에서 육안 대조 병행).
- 원리 게이트 재확인이 필요하면 `principle_gate` 자기 테스트만 실행: `python -m pytest tests/unit -q -k principle_gate`.

### 3.5 단계 0.5 — 준비: loop_strategies.db 미러 INSERT

배치 러너(§4)는 `ai_strategy_loop/state/loop_strategies.db`의 stockbuy/stocksell `index`를 참조한다(`_database/strategy.db` 아님). 따라서 25개 조건식을 미러 INSERT한다.

- 절차(선례: `.omo/evidence/claude-condition-research-20260610/insert_candidates.py` — 공식 PRE-SAVE 가드 재사용):
  1. 백업: `Copy-Item ai_strategy_loop/state/loop_strategies.db ai_strategy_loop/state/loop_strategies.db.bak.css_v7_<UTC타임스탬프>`
  2. 신규 스크립트 `artifacts/chart_sulsa_validation_20260702/mirror_insert_css_v7.py` 작성: `_database/strategy.db`에서 `CSS_V7_%` 행을 읽어 `check_tokens`/`check_variable_scope` 통과 후 `save_strategy_to_db`로 loop DB에 저장. **dry-run 기본, `--apply` 시에만 저장.**
  3. 이름 충돌(동명 행 존재) 시 저장하지 않고 충돌 보고서 출력 후 중단.
  4. 저장 후 sha256 재대조(§3 (1)의 loop DB 버전) → 영수증 `mirror_insert_receipt.json` 기록.

## 4. 공통 실행 도구와 공식 프로파일

- 배치 러너(LLM 호출 0회, warm 엔진):
  `PYTHONUTF8=1 python -m ai_strategy_loop.scripts.claude_candidate_batch_eval --pairs-json <pairs.json> --config-json <config.json> --run-id <run_id>`
- 공식 replay 프로파일: `ai_strategy_loop/controller/replay_profile.py`의 `CANONICAL_REPLAY_PROFILE_V1`(`official_replay_v1_20260702`) — **betting "5"(500만), avg_time 30 고정**, tick 시간창 090000~092800, `divid_mode="종목코드별 분류"`. 모든 공식 run은 config로 `ReplayProfile`을 구성해 `canonical_execution_diff()` 결과를 영수증에 남긴다. **betting/avg_time/시간창/divid_mode/DB 차이는 불허**, 기간(start/end_date) 차이만 레인별 사전선언 창으로 허용하고 diff에 명시한다.
- 엔진 정책: 스모크는 config의 warm 8 유지, 전기간/OOS는 64 engine first + 32 fallback receipt(미사용 시 `fallback:false` 기록).
- 창 config(기존 자산 재사용 — 새로 만들지 않는다):

| 용도 | 레인 | config 경로 | 창 |
|---|---|---|---|
| 스모크 | tick | `.omo/evidence/claude-condition-research-20260610/smoke-config.json` | 2025Q1 (20250101~20250331, 90일) |
| 스모크 | min | `.omo/evidence/tmap-walkforward/min-smoke-config.json` (실행 전 `bt_full_start/end`로 창 확인) | 2025-05 (31일) |
| train | tick | `.omo/evidence/claude-condition-research-20260610/train-config.json` | 20230101~20251231 |
| train | min | `.omo/evidence/tmap-walkforward/min-fullsession-e64-config.json` 중 `bt_full_end`를 20251231로 바꾼 **신규 사본** `min-train-e64-css.json` (원본 수정 금지) | 20250408~20251231 |
| 고정 OOS | tick | `oos-2022-config.json` / `oos-2026-config.json` (같은 디렉터리) | 2022년 / 20260101~20260228 |
| 고정 OOS | min | `.omo/evidence/tmap-walkforward/min-oos-config.json` | 20260101~20260227 |

- 모든 run 전에 사용하는 config 파일의 sha256을 원장에 기록한다.

## 5. 단계 1 — 스모크 (자원 배분 advisory)

규약: `docs/research/condition_research/2026-06-12_smoke_screening_protocol.md` + `ai_strategy_loop/seeds/smoke_budget.py`.

1. 유니크 쌍 전건(§2)을 레인별 스모크 config로 배치 실행. run_id 규칙: `smoke_css_v7_<lane>_20260702`.
2. 판정: 쌍별 profit을 `evaluate_smoke_budget(cell_result, lane=<tick|min>, window_days=<90|31>)`로 판정.
   - 임계는 **창 비례 축소**: tick 90일 = −2,000,000 / min 31일 ≈ −688,888 (모듈이 계산 — 수기 산정 금지). 경계 포함(정확히 임계면 no_go), NaN/inf는 fail-closed no_go.
   - `no_go`는 **영구 폐기가 아니라 대기열 후순위 강등**이다. 어떤 선택·동결·승격 판단에도 사용 금지(advisory 전용).
3. tick 쌍은 결과 receipt의 `bt_universe_start_time=90000/end_time=93000`과 조건 코드 내부 `시분초 < 93000` 가드가 함께 있는지 확인해 09:00~09:30 창 준수를 기록한다.
4. 기록 의무:
   - 스모크 1줄 로그: `artifacts/chart_sulsa_validation_20260702/css_v7_smoke_log.txt`
   - `no_go` 쌍은 즉시 `register_rejected`(`ai_strategy_loop/seeds/revival_registry.py`)로 신규 JSONL(`docs/research/condition_research/chart_sulsa/css_v7_revival_registry.jsonl`)에 등재.
   - 스모크 run_id는 시도(trial)다 — 이후 동결 심사 시 `--trial-runs`에 **전건 합산**(n_trials 누락 금지).
5. 0거래(trades=0) 쌍은 `no_trades` 특수 라벨로 보류 — 원인(창/유니버스/가드) 1회 조사 후 재시도, 재현되면 no_go 준용 처리하고 사유를 원장에 남긴다.

## 6. 단계 2 — 전기간 train (측정 단계 — 판정 없음)

1. 단계 1 `go` 쌍(+ 보류 해소분)을 레인별 train config로 공식 replay. run_id: `train_css_v7_<lane>_20260702`. betting "5"/avg_time 30 고정 확인(§4 영수증).
2. 비교 앵커: tick 배치에 comparator 쌍 `{"label":"comparator_rr8_12","buy":"GATE_rr8_12_turnover_min_902_1_5_B","sell":"GATE_rr8_12_turnover_min_902_1_5_S"}`를 **동일 배치에 포함**해 같은 창 동시 재측정한다(단계 3 비열등 판정의 기준). min 레인은 공식 시드 부재를 공시한다(§7).
3. 결과 영속 — 거래 원장: 쌍별 per-trade CSV를 `ai_strategy_loop/autopsy/trade_ledger.py`의 `append_trades`(48컬럼, parquet/sqlite 자동)로 `artifacts/chart_sulsa_validation_20260702/trade_ledger/`에 적재한다.
4. Analysis Card 생성: 쌍별로 `ai_strategy_loop/autopsy/analysis_card.py`의 `build_analysis_card`(10섹션, `insufficient_data` 정직 라벨) + `render_card_md` → `analysis_cards/<label>.md` + `analysis_cards.jsonl`.
5. 이 단계는 스크리닝 판정을 하지 않는다(기각 없음). 단, `trades < 30`인 쌍은 `low_sample` advisory 라벨을 붙인다(단독 기각 금지 — OOS 판정력 경고용).
6. 단계 3 진입 우선순위 정렬에만 train 성과를 사용한다(§9의 순서 규칙이 우선).

## 7. 단계 3 — OOS / Walk-Forward (판정 단계)

기존 프로토콜 준수: 고정 OOS 사용 횟수 공시 + V4 walk-forward(`2026-06-12_process_v2_and_seed_reresearch_plan.md`, `2026-06-12_min_timeframe_validation_protocol.md`, `2026-06-12_oos_false_negative_and_gap_research.md`).

1. 고정 OOS 실행: 단계 2 완료 쌍을 tick은 2022·2026 두 창, min은 2026-01~02 한 창으로 replay(comparator 쌍 동시 포함). **각 실행은 원장에 `oos_usage` 이벤트로 등재**(창, run_id, 대상 쌍 수 — 사용 횟수 공시 의무).
2. OOS 판정 v2 (사전선언 — 신규 판정 전부 적용):
   - ① **비열등**: 같은 OOS 창에서 comparator(tick=`GATE_rr8_12_*` 쌍) 대비 profit 비열등(시장 운 상쇄). min 레인은 comparator 부재를 공시하고 absolute-niche 기준(`min_positive_years=1` + 흑자 월 ≥5 advisory 병기)으로 ①을 대체한다.
   - ② **MDD 한도**: tick = comparator MDD×1.5 이내. min = config `mdd_cap`(35) 이내.
   - ③ **무붕괴**: OOS 손실이 −(comparator 손실×1.5) 이내(min은 창 비례 스모크 예산 절대치 준용). 횡보·소폭 손실은 **HOLD-OK**(기각 아님).
   - 절대 수익(전 창 흑자)은 가점일 뿐 필수 아님. `trades < 20` 창은 단독 기각 금지(advisory 강등) — 표본 판정력은 walk-forward가 1차.
3. Walk-forward:
   - **고정(비-OPT) 조건식**: 재적합이 없으므로 롤링 창 성과 분해로 무붕괴 확인 — train 창을 연/분기 서브창으로 나눠 batch 재실행(tick: 2023/2024/2025 연 3창, min: 분기 3창), 특정 창 집중·후반 붕괴 여부를 Analysis Card에 병기.
   - **OPT 계열(`CSS_V7_OPT_*`, opt_vars tick 27/min 31)**: OOS 생존 시에만 V4 정책 드라이버 적용 — `PYTHONUTF8=1 python -m ai_strategy_loop.scripts.tmap_walkforward --template <신규 스윕 템플릿> --config-json <base> --run-prefix wf_css_v7 --windows "20230101-20231231:20240101-20240630,20240101-20241231:20250101-20250630" --params <상위 기여 축 2~3개>`. 전축 스윕 금지(예산) — 축 선정 근거는 ablation/Analysis Card에서 인용.
4. 판정 결과 처리: 통과 → `생존`(Plan D 입력). 기각 → `css_v7_revival_registry.jsonl` 등재(사유 필수). HOLD-OK → V4/롤링 분해 추가 증거 확보 후 재판정 1회(그래도 불충분하면 보류 상태로 원장에 남기고 종료).

## 8. 단계 4 — 슬리피지 (advisory 전용)

1. 생존·보류 쌍의 per-trade CSV로 `ai_strategy_loop/fitness/slippage_profiles.py`의 `compute_slippage_profiles` 실행 → tick0~3 프로파일 산출(비용 수 초/쌍).
2. `evaluate_slippage_gate`(`ai_strategy_loop/controller/condition_discovery.py`, fail-closed, promotion 프리셋 `tick2`)로 receipt만 생성 — **배선 금지, 판정은 advisory**.
3. tick2 프로파일 total_profit이 음수인 쌍은 연구는 계속하되 **`not_promotion_candidate` 라벨**을 passport와 원장에 남긴다(승격 후보 목록에서 제외 — 승격 자체는 어차피 금지).

## 9. 평가 순서와 백테스트 예산

순서(문서 §12.1 권장 순위 — 조합 우선):

1. `CSS_V7_COMBO_MIN_01` 쌍 (= MIN_B_RETEST_PULLBACK_SWITCH + MIN_S_MASTER)
2. `CSS_V7_COMBO_TICK_01` 쌍 (= TICK_B_MASTER + TICK_S_MASTER, 장초반)
3. 나머지 MASTER/OPT 쌍 (MIN_B_MASTER+MIN_S_MASTER, OPT tick 쌍, OPT min 쌍)
4. 단독 패턴 조건식 쌍 전건 (passport 페어링 순 — buy 패턴, sell 패턴)

예산 추정(전부 **추정 라벨** — 각 레인 첫 쌍 실측 후 반드시 재산정하고 원장에 기록):

| 단계 | 물량 | 단가 추정 | 소계 추정 |
|---|---|---|---|
| 1 스모크 | tick ~7쌍 ×5분 + min ~14쌍 ×2분 | 규약 실측(tick 2025Q1 ~5분) / min 미실측 | ~1.1h |
| 2 train | 생존쌍(50~100%) — tick ~7×8분(3년) + min ~14×15분(9개월) | tick 150초/2025년 실측의 3년 환산 / min 미실측 | ~2~4.5h |
| 3 OOS | tick 생존쌍 ×2창 ×3분 + min 생존쌍 ×1창 ×4분 | OOS 창이 짧아 저비용 | ~1~2h |
| 3 WF 롤링 분해 | 생존쌍 ×3창 | train 단가의 창 비례 | ~1~3h |
| 3 V4(OPT만) | OOS 생존 OPT 계열 ×창 2 (스윕 포함) | 고비용(수십 분~수 시간/계열) | 생존 시 별도 승인 |
| 4 슬리피지 | CSV 후처리 | 수 초/쌍 | 무시 가능 |

## 10. 판정 매트릭스 (요약)

| 단계 | 통과 | 기각 | 보류 | 기록 의무 |
|---|---|---|---|---|
| 0 정적 | sha/게이트 전건 일치 | (불일치 = 전체 중단·충돌 보고) | — | 재확인 로그 |
| 1 스모크 | `go` (profit > 창비례 임계) | `no_go` → 후순위 강등 + revival 등재 | `no_trades` 1회 조사 | smoke log 1줄 + 원장 + n_trials 합산 |
| 2 train | (판정 없음 — 측정) | — | `low_sample` advisory | trade_ledger 영속 + Analysis Card |
| 3 OOS/WF | v2 ①②③ 충족 | 시드 열위·MDD 위배·붕괴 → revival 등재 | HOLD-OK → 추가 증거 후 재판정 1회 | oos_usage 공시 + 원장 + passport 갱신 |
| 4 슬리피지 | (advisory) | — | tick2 음수 → `not_promotion_candidate` 라벨 | receipt + passport 라벨 |

## 11. 추적 시트 — 원장 갱신 필드

- 기계가독 원장(신규 파일): `docs/research/condition_research/chart_sulsa/css_v7_validation_ledger.jsonl` — **append-only**. 이벤트 스키마:
  `{"entry_type":"validation_event","id":<condition_id 또는 combo_id>,"pair_label":...,"stage":"smoke|train|oos|wf|slippage|oos_usage","run_id":...,"config_path":...,"config_sha256":...,"window":"YYYYMMDD-YYYYMMDD","profit":...,"mdd_pct":...,"trades":...,"verdict":"go|no_go|pass|reject|hold_ok|advisory","labels":[...],"receipt_path":...,"counted_as_trial":true,"ts":"<UTC ISO>"}`
- `provenance_registry.jsonl` 갱신: 조건별 최종 상태를 append-only 이벤트 행(`entry_type:"validation_summary"` — id, final_status(`survivor|rejected|hold|not_promotion_candidate`), ledger 참조 경로, ts)으로 추가한다. **기존 행 수정 금지.** 실행 시점에 이 파일이 이미 커밋돼 있으면 원본은 불변으로 두고 자매 신규 파일 `provenance_registry_updates_20260702.jsonl`에 기록한다(`git ls-files`로 확인).
- 사람용 문서: 연구 3종 문서(`docs/research/condition_research/research_runs/css_v7_validation_20260702_plan|management|result.md`) + `docs/update_log/` 기록 1건. passport의 `oos_status/prior_*` 필드는 passport가 커밋 전이면 직접 갱신, 커밋 후면 조건별 추가 노트 파일로 병기.

## 12. 위생·건전성

- 세션 시작 시 positive control 1회: `python scripts/run_positive_control.py <직전 공식 결과 JSON> --use-reference-baselines --gate-config ai_strategy_loop/state/run_p5_validation_tick_late.json --report artifacts/chart_sulsa_validation_20260702/positive_control_receipt.json` — `gate_healthy` 아니면 **모든 판정 중단**하고 게이트 조사부터.
- 증거 정합 검사(읽기 전용): `python scripts/check_research_evidence_lineage.py` 실행 결과를 세션 종료 receipt에 첨부.
- 종료 조건: 유니크 쌍 전건이 `생존|기각|보류` 중 하나로 원장에 남고, 생존 목록이 Plan D(`2026-07-02_plan_D_seed_research_program.md`) 입력 형식(§Plan D 2절)으로 export되면 완료.
