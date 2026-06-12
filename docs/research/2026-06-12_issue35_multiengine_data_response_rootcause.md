# 이슈 #35 근본 조사 — cold 멀티엔진(engines≥2, 종목코드별 분류) 데이터 응답 교착

> 조사일: 2026-06-12 · 환경: `STOM_V.wt-webbt`(feature/webbt-phase3)
> 입력: GitHub 이슈 #35, `docs/research/2026-06-12_orderflow_v5_workbench_validation_results.md` §3
> 도구: 직접 CLI 재현(`stom_backtest.py`), `py-spy 0.4.2` 스택 덤프, `psutil` 프로세스 트리

## 0. 결론 (먼저)

**멀티엔진 데이터-응답 경로는 정상이다. engines=1·2·4 모두 '종목코드별 분류'로
정상 완주했다(success).** 이슈가 관측한 "응답 0건 교착"은 멀티엔진 데이터 전송
메커니즘의 결함이 아니라 **v5 고비용 전략의 BackTest 연산 단계가 타임아웃을
초과한 것**이며(연구 §3에서 이미 확정: `backtest_process_started` 이후 >600초),
이슈 본문에서 두 개의 서로 다른 실패 지점(데이터 응답 단계 vs. 연산 단계)이
하나로 혼동돼 기술됐다.

따라서 **engines=1 강제 가드는 적절하지 않다 — 작동하는 기능을 비활성화하는 것**이다.
대신 '응답 0/N' 증상을 블록 지점으로 환원할 수 있도록 **runner.py 데이터-응답
타임아웃 진단을 보강**했다(엔진별 생존/종료코드 스냅샷).

## 1. 재현 매트릭스 (단순 전략 `WEBBT_SMOKE_ALWAYS_B/S`)

env: `STOM_ALLOW_MINIMAL_SETTING=1`,
`STOM_CLI_DB_STOCK_BACK_TICK=ai_strategy_loop/state/tick_subset.db`

| engines | 기간 | 코드수 | divid_mode | 결과 | 데이터 응답 | elapsed |
|---------|------|--------|-----------|------|------------|---------|
| 2 | 20260223–27 | 4 | 종목코드별 분류 | ✅ success | 2/2 (chunk [2,2]) | 42.4s |
| 1 | 20260223–27 | 4 | 종목코드별 분류 | ✅ success | 1/1 (chunk [4]) | 40.8s |
| 4 | 20260101–0227 | 5 | 종목코드별 분류 | ✅ success | 4/4 (chunk [1,1,1,2]) | 46.6s |

세 케이스 모두 `engine_data_response_received` 가 정상 도착하고
`engine_data_load_completed` → `backtest_process_finished` → `csv_detected` 로
완주했다. **데이터 응답 단계 교착은 단순 전략에서 재현되지 않는다.**

## 2. "23개 자식·~242MB" 관측의 정체

`py-spy`/`psutil` 트리 분석 결과 자식 구성은 다음과 같다(정상 아키텍처):

- 20 × `BackSubTotal` (중간집계 워커, 각 ~150–248MB) — `back_subtotal.py:39` MainLoop 에서
  큐 `get` 블록(유휴 대기). **이것이 이슈의 "~242MB 유휴 자식"의 정체.**
- N × 엔진 프로세스 (engines 값)
- 1 × `BackTest` + 1 × 내부 `Total`

engines=1 → 20+1+1+1 = **23개**가 정확히 재현된다. 누수가 아니라 설계상
프로세스 풀이다. 데이터 로딩 중에는 엔진이 CPU 46–109%로 활발히 계산하며(`add_rolling_data`),
완료 후 다음 메시지를 기다리며 0% CPU 유휴로 전환된다 — 이슈가 본 "0% CPU 유휴"는
이 정상 대기 상태이거나, 타임아웃 후 엔진이 멈춘 상태다.

## 3. 진짜 교착 잠재 경로 (정직한 기술)

엔진 `DataLoad`(`backengine_base.py:351`)는 성공 시 정확히 1회 `self.bq.put(shared_info)`
한다(line 434). 그런데 `MainLoop`(line 339-346)은 `DataLoad`를 try/except로 감싸고
예외를 **gubun==0 일 때만 로깅하고 삼킨다**. 즉 `DataLoad`가 line 434 이전에 예외를
던지면 엔진은 backQ에 아무것도 넣지 않고 다음 메시지를 기다린다 → runner는 그 엔진의
응답을 받지 못한다.

**그러나 이것은 무한 교착이 아니다.** runner의 `_collect_engine_shared_info`는
`backQ.get(timeout=remaining)`로 데드라인을 강제하므로(runner.py:236), 최악의 경우에도
`timeout`초 후 `engine_data_response_timeout`으로 **깨끗이 종결**된다. 단, 기존 진단은
"몇 개 받았는지"만 기록하고 **어느 엔진이 왜 응답하지 않았는지**(살아서 계산 중인지,
조용히 죽었는지)를 구분하지 못해 블록 지점 확정이 불가능했다.

엔진 core(`backengine_base.py`) 수정은 warm 세션(GUI/loop)과 cold CLI가 **공유하는
경로**라 blast radius가 크고(put-on-error 변경이 warm 소비자 계약을 깰 위험), 무한 교착도
아니므로 **core를 건드리지 않는다**. 대신 runner 진단만 보강한다.

## 4. 적용한 수정 (runner.py — cold CLI 전용, 무행동변경)

`cli/runner.py`:
- `_snapshot_engine_liveness(engine_procs)` 추가: 각 엔진의 `pid/is_alive/exitcode` 수집.
- `_record_engine_data_loading_timeout(...)`에 `engine_procs` 인자 추가 → 타임아웃
  detail·result에 `engine_liveness` 배열 첨부.
- `_collect_engine_shared_info(...)`에 `engine_procs` 인자 추가(타임아웃 두 분기에 전달).
- `run_backtest`에서 엔진 spawn 시 `engine_procs` 리스트 수집 후 위 함수에 전달.

진단 신호 해석:
- 한 엔진이라도 `alive=False` + `exitcode!=0` → `DataLoad` 단계 침묵 예외(블록 지점 확정).
- 전원 `alive=True` → 계산 지연(전략 비용/대용량 데이터). 이 경우 timeout 상향이 답.

**타임아웃 발동 조건·정상 완주 경로는 일절 바뀌지 않는다.** 실패 시 결과 페이로드에
진단 필드 하나가 더 붙을 뿐이다.

## 5. 회귀 테스트

`tests/unit/test_runner_helpers.py`:
- `test_collect_engine_shared_info_records_structured_timeout`: 기존 테스트에
  `engine_liveness: []`(엔진 procs 미전달 시) 기대값 추가.
- `test_collect_engine_shared_info_timeout_captures_engine_liveness`(신규): 엔진 더블
  2개(살아있음/죽음)를 주입해 `engine_liveness`가 alive/exitcode/pid를 정확히
  포착하고 checkpoint detail에도 동일하게 기록됨을 검증.

## 6. 권고 (워크벤치 운영)

1. v5 류 고비용 전략은 데이터 단계가 아니라 **BackTest 연산 단계**에서 타임아웃한다 →
   연구 §3의 OPTI 경량화(시간 게이트 안으로 파생변수 이동, ~96% 절감)가 선결 과제다.
2. 멀티엔진(engines≥2)은 단순/중간 비용 전략에서 정상 작동하므로 워크벤치가
   engines≥2를 일괄 차단할 이유는 없다. 고비용 전략에 한해 `timeout`을 충분히 주거나
   OPTI판으로 먼저 검증하라.
3. 향후 '응답 0/N' 재발 시 결과 JSON의 `engine_data_loading.engine_liveness`를 먼저 확인 —
   `alive=False`/`exitcode` 패턴이 곧 블록 지점이다.
