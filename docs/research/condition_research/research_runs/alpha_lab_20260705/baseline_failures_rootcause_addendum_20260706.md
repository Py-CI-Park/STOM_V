# 기준선 실패 10건 — 파일·라인 단위 근본원인 확정 부록 (2026-07-06)

> **결론**: 실패 10건 전부의 근본원인이 **알파 랩이 손대지 않은 코어 소스/런타임 상태**에 있음을 파일·라인 단위로 확정했다. 원인 파일 전체가 알파 착수 커밋(70775539) 시점과 **바이트 동일**(커밋 + 워킹트리 포함)이므로, 10건은 알파 작업 이전부터 존재한 실패임이 구성적으로 증명된다. 알파 스코프 내 수리는 불가능하며(§4), 수리 소관은 wt-dev 레인이다.
>
> 본 부록은 `baseline_test_failures_20260705.md`(stash 재현·단독 실행 격리·알파 전수 green)의 3종 증거를 4번째 증거(원인 파일 불변성)로 보강한다. 검증 라운드 지적("전체 통과 기준 미충족")에 대한 수복 임무(wf 재검증, 2026-07-06)의 산출물이다. 2차 수복 라운드의 전 항목 독립 재실측과 최종 판정은 §7 참조.

## 1. 재현 스냅샷 (2026-07-06, STAGE 1 미커밋 변경 포함 트리)

- 지목된 10개 노드 ID만 단독 실행: **10 failed in 12.69s** — 검증 라운드와 동일 집합, 신규/소멸 0.
- 알파 스코프 전수: `-k "test_alpha"` → **290 passed, 4019 deselected in 31.55s** (문서화된 247에서 STAGE 1 신규 테스트 43건 증가분 포함, 실패 0).
- `python scripts/verify_nonrelease_sync.py` → **exit 0**.
- 전체 스위트 신규 스냅샷: §5 참조.

## 2. 실패별 근본원인 (파일·라인 실측)

| # | 테스트 | 감사 대상 | 근본원인 (실측 증거) |
|---|---|---|---|
| 1 | `test_backtest_button_contract::test_backtest_constructor_contract_is_small_and_queue_driven` | `backtest/backtest.py` | 실제 `BackTest.__init__` 시그니처가 **레거시 롱폼 26파라미터(self 포함)**(`sc, wq, sq, tq, lq, teleQ, beq_list, bstq_list, backname, ui_gubun, dict_set, betting, avgtime, startday, endday, starttime, endtime, buystg_name, sellstg_name, dict_cn, back_count, blacklist, schedul, back_club, diagnostic_queue`) — `bq` 부재. 테스트는 2U_C CLI 시대의 12파라미터 큐 구동 계약을 기대 |
| 2 | `test_backtest_process_protocol_diagnostics::test_backtest_start_emits_key_protocol_checkpoints` | `backtest/backtest.py` | `backtest_child_*` 체크포인트 토큰 문자열 부재 (표본 4종 전부 `False` 실측). `_emit_cli_protocol_checkpoint` 함수 자체는 존재(동일 파일 내 다른 2개 테스트는 통과) — 호출부 계측만 이 레인 코어에 미반영 |
| 3 | `test_backtest_process_protocol_diagnostics::test_total_emits_key_protocol_checkpoints` | `backtest/backtest.py` | 동일 — `total_*` 체크포인트 토큰 부재 |
| 4 | `test_backtest_spawn_contract_audit::test_stock_backtest_spawn_does_not_pass_legacy_long_signature` | `ui/ui_button_clicked_editer_stock.py` | spawn 블록이 레거시 롱폼 인자(`betting, avgtime, startday, endday, starttime, endtime, buystg, sellstg, …`)를 그대로 전달 → `"betting" not in block` 단언 실패 |
| 5 | `test_backtest_spawn_contract_audit::test_coin_backtest_spawn_does_not_pass_legacy_long_signature` | `ui/ui_button_clicked_editer_coin.py` | 동일 — 코인 에디터 spawn 블록도 레거시 롱폼 |
| 6 | `test_runner_helpers::TestCliDictSetProcessArgs::test_backtest_process_passes_dict_set_to_constructor` | `cli/runner.py` | 실측 spawn: `args=(BackTest,dict(dict_set),shared_cnt,windowQ,soundQ,totalQ,liveQ,teleQ,back_eques,back_sques,'백테스트','S',dict(dict_set),config.betting,…` — `backQ` 부재 + 롱폼 연장. 테스트는 `backQ` 포함 14인자 숏폼을 기대 |
| 7 | `test_tick_seed_timeout_probe::test_run_cold_command_uses_warm_window_and_forbidden_tokens_are_absent` | `ai_strategy_loop/scripts/tick_seed_timeout_probe.py` → `controller/loop.py:386 _build_warm_btconfig` → `controller/condition_discovery.py:511` | `effective_condition_discovery_runtime_config`가 `bt_universe_end_time`을 레인 고정 tick 연구창 **92800**으로 재기입. 테스트 config의 `90100`이 통과되지 않아 실측 커맨드가 `--end-time 92800` 생성(재현 완료) — 테스트는 `--end-time 90100` passthrough 기대. min 스윕/조건탐색 시대(알파 이전) 변경 |
| 8 | `test_filter_gate::test_real_seed_buy_has_many_categories` | `ai_strategy_loop/state/loop_strategies.db` (gitignore: `state/.gitignore:2`) | 런타임 시드 전략 DB 부재(라이브 루프 산출물, fresh 워크트리에 없음). §3의 0바이트 아티팩트 참고 |
| 9 | `test_time_window::test_noop_real_seed_buy_is_NOT_noop` | 동일 | 동일 — `sqlite3.OperationalError: no such table: stockbuy` |
| 10 | `test_ui_jisu_cleanup::test_v270_removed_jisu_chart_references_are_fully_cleaned` | `ui/ui_process_kill.py` | V2.70 지수차트 제거 기준 창위치 인덱스 재정렬 토큰 `ui.dict_set['창위치'][7]` 부재 — 재정렬이 이 레인 ui 코어에 미반영 |

공통 구조: 1~7·10은 **2U_C(wt-dev) 레인에서 동기화된 계약 감사 테스트**가 이 연구 레인의 **구세대 코어**(백테스트 숏폼 전환·CLI 프로토콜 계측·V2.70 UI 재정렬 미반영)를 감사해서 생기는 레인 괴리, 8·9는 런타임 산출물 의존이다.

## 3. 실패 모드 표기 변화 1건 (원인 불변)

`loop_strategies.db`가 **0바이트 빈 파일**(테이블 0개)로 존재함을 실측 — mtime `2026-07-05 23:16:41`, 전체 스위트 검증 실행 중 쓰기모드 `sqlite3.connect` 부작용으로 자동 생성된 아티팩트다(시딩 아님, gitignore 경로). 이로써 #8·#9의 실패 메시지가 `assert os.path.exists`(seed DB 없음)에서 `sqlite3.OperationalError: no such table: stockbuy`로 바뀌었으나, **근본원인(시드 전략 부재)과 실패 집합은 불변**이다. 아티팩트는 재실행 시 재생성될 수 있어 삭제하지 않고 기록만 남긴다(원본 문서 §3 시딩 금지 결정 유지).

## 4. 구성적 증명 — 원인 파일 불변성 (증거 4)

알파 착수 커밋 `70775539`(알파 랩 워크트리 착수 핸드오프) 대비, **커밋 이력 + 현재 워킹트리(STAGE 1 미커밋 변경 포함)** 전체에서:

```
git diff --stat 70775539 -- backtest/ ui/ cli/runner.py stom_backtest.py \
    ai_strategy_loop/scripts/ ai_strategy_loop/generation/ ai_strategy_loop/state/ \
    ai_strategy_loop/controller/ ai_strategy_loop/config.py
→ (출력 없음 = 바이트 동일)

git diff --name-only 70775539 -- tests/unit/ | grep -v test_alpha_
→ (출력 없음 = 비알파 테스트 무변경)
```

알파 작업 전체 footprint(추적+미추적, run-dir 산출물 제외): `alpha_lab/**`(신규 `mcl/` 포함), `cli/alpha_*.py`(신규 `alpha_crosscheck.py` 포함), `tests/unit/test_alpha_*.py`(신규 `test_alpha_mcl.py` 포함), `ai_strategy_loop/dashboard/alpha_api.py`(+`app.py` 라우터 2줄), 연구 문서. **§2 원인 파일과 교집합 0**. 또한 실패 10건이 속한 8개 테스트 파일에서 `alpha` 토큰 검색 결과 **0건** — import·로직 어느 경로로도 알파 코드와 접점이 없다.

∴ 10건은 `70775539` 시점에도 동일하게 실패했음이 구성적으로 따라온다(감사 대상과 테스트가 모두 바이트 동일이므로). 원본 문서 §2의 stash 재현·단독 실행 격리와 독립적으로 성립하는 세 번째 축이다.

## 5. 전체 스위트 스냅샷 근거 (실측만 기재)

- 검증 라운드 공식 실측(2026-07-05): `python -m pytest tests/unit -q` → **10 failed, 4279 passed, 20 skipped in 402.55s** — 실패 10건이 본 문서 §2 목록과 정확히 일치.
- 본 수복 라운드 표적 재실행(2026-07-06): 지목 10개 노드 ID 단독 → **10 failed in 12.69s** (집합 동일, 신규/소멸 0) + 알파 스코프 **290 passed**.
- 재검증 라운드 전체 스위트 실측(2차 수복 임무 브리핑 인용): `python -m pytest tests/unit -q` → **10 failed, 4279 passed, 20 skipped in 407.15s** — 실패 집합이 §2 목록과 집합 단위 동일(신규 0, 소멸 0). 산술 정합: 알파 290 + 비알파 4019 = 4309 수집 = 10 failed + 4279 passed + 20 skipped.

## 6. 스코프 내 수리 가능성 판정과 게이트 권고

- **#1~7·10**: 수리는 `backtest/`·`ui/`·`cli/runner.py`·`ai_strategy_loop/controller/` 코어 수정 또는 비알파 테스트 수정을 요구 — 둘 다 알파 랩 소관 외(원본 §3 "기존 파일 불수정" 규율). 코어의 숏폼/계측/재정렬 이식은 wt-dev 레인 사안.
- **#8·9**: gitignore 런타임 DB 시딩으로만 녹색화 가능 — wf1 fix r2에서 시도 후 부정직으로 판정·원복된 방식(원본 §3). 재시도하지 않는다.
- **권고**: 알파 게이트는 "전체 통과" 대신 "**알파 스코프 전수 green + 기준선 10건 문서화 면제**"로 판정한다. 근거: 증거 4종(순수 기준선 stash 재현 · 단독 실행 격리 · 알파 전수 green · 원인 파일 불변성) + 파일·라인 단위 근본원인 확정(§2).

## 7. 2차 수복 라운드 독립 재검증 (2026-07-06)

1차 수복 산출(§1~6)을 신뢰 전제 없이 전 항목 독립 재실측했다. 전부 재확인됨(실측만 기재):

- 표적 10개 노드 ID 단독 재실행 → **10 failed in 12.07s** — 집합 §2와 동일, 신규/소멸 0.
- 알파 스코프 `pytest tests/unit -k "test_alpha"` → **290 passed, 4019 deselected in 30.68s** — 실패 0.
- `python scripts/verify_nonrelease_sync.py` → **exit 0**.
- 사전등록 봉인: `preregistration_v1.json` sha256 실측 `6750a567…4ac39e5b` = `.sha256` 기재값과 일치(봉인 무결, 재봉인 없음).
- 원인 파일 불변성(§4 커맨드 재실행): `git diff --stat 70775539 -- backtest/ ui/ cli/runner.py stom_backtest.py ai_strategy_loop/{scripts,generation,state,controller}/ ai_strategy_loop/config.py` → 출력 없음(커밋+워킹트리 바이트 동일). `git diff --name-only 70775539 -- tests/unit/ | grep -v test_alpha_` → 출력 없음(비알파 테스트 무변경). 원인 경로 `git status --porcelain` → 출력 없음(미커밋 변경도 없음).
- 실패 10건이 속한 8개 테스트 파일에서 `alpha` 토큰(대소문자 무시) → **0건**.
- 안전 확인: 위 8개 파일의 `subprocess.Popen` 사용처는 전부 monkeypatch 가짜(fail_popen/fake_popen), `multiprocessing`은 Queue/Process 시그니처 계약용 import — 표적 실행이 실제 백테스트/엔진 프로세스를 기동하지 않음을 소스 수준 확인 후 실행(min 스윕 비간섭 유지).

**최종 판정**: "전체 통과" 리터럴 기준은 알파 소관(`alpha_lab/**`, `cli/alpha_*.py`, `tests/unit/test_alpha_*.py`, run-dir 문서) 내 어떤 정직한 수단으로도 충족 불가함이 2개 수복 라운드에 걸쳐 독립적으로 확정됐다. 잔여 경로는 (a) 게이트를 §6 권고("알파 스코프 전수 green + 기준선 10건 문서화 면제")로 판정하거나, (b) 10건 수리를 wt-dev 레인 별도 사안으로 발주하는 것 두 가지뿐이다. 추가 스코프 내 수복 라운드는 동일 결론만 재생산한다.

## 8. 추록 — 11번째(신규 관측) 플레이키 실패 (2026-07-07, 알파 랩 v4 검증 라운드)

알파 랩 v4 검증 라운드에서 전체 스위트 재실측(`11 failed, 4493 passed, 20 skipped in 469s`) 중 본 문서 §2 목록 10건 외에 `tests/unit/dashboard/test_backtest_jobs.py::test_cancel_kills_child_tree_and_releases_queue`가 추가로 관측됐다(격리 재실행 시 3 fail/2 pass로 비결정적). 이 문서의 "고정 10건" 목록은 **불변**이다 — 신규 항목은 결정적 실패가 아니라 확률적(flaky) 실패이므로 별도 문서로 근본원인·알파 무관성을 구성적으로 증명했다. 상세: `../alpha_lab_v4_20260707/pytest_baseline_11th_failure_repair_20260707.md`(원인 파일·테스트 파일 모두 알파 착수 커밋 `70775539`과 바이트 동일, `alpha` 토큰 0건, 알파 스코프 505 passed/0 failed 재확인). 본 부록 §1~7의 10건 목록·근본원인·판정은 이 추록으로 변경되지 않는다.
