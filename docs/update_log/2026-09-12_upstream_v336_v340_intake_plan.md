# 2026-09-12 업스트림 신선도 점검 및 V3.36~V3.40 흡수 계획 (코드 미반영)

- 기준일: 2026-09-12
- 성격: 계획/재개 정본. 공식 overlay, merge, push는 아직 하지 않는다.
- 직전 닫힌 사이클: 2026-07-12 V3.35 (wt-3 c6ac10b2 / V3U 2fb212e2 / 3U_C merge ff704397)
- 공식 freshness: https://github.com/devstom/STOM.git
  - V2: refs/tags/V2.0 = 873d51eed3f581daa1925bcd9e3672254f525f0a (여전히 2026-04-08 V2.79)
  - V3: refs/heads/V3.00 = 09a11f832445aa0141e1c9eb0a6db3f5c2880cc3 (V3.40 + tail)
  - refs/tags/V3.0 는 2026-04-23 V3.08 stale tag. freshness 권원 금지.

이 문서는 다음 세션이 어디서, 어떤 순서로, 어떤 pyd 추론으로 흡수할지 바로 복구하기 위한 기록이다.

---

## 0. 한줄 판정

~~~
V2 신규 없음.
지금 할 일 = V3.36 -> V3.40(+tail) 을
wt-3(공식) -> wt-3u(pyd-free) -> wt-3uc(merge) 한 버전씩.
wt-dev / 2U_C 는 HOLD. 2U는 버전 전파 완료(ahead 1은 push 판단만).
~~~

---

## 1. Status Dashboard (2026-09-12 실측)

| Lane | Worktree | Branch / HEAD | 로컬 흡수 | Upstream | 이번 계획 |
|---|---|---|---|---|---|
| V2 공식 | STOM_V | STOM_Version_2 2867dbec | V2.79 b88ed672 | tag V2.0 = V2.79 | 코드 없음. 본 계획만 기록 |
| 2U | STOM_V.wt-2u | STOM_Version_2U 3b7a3aeb | V2.79 + 3.13 pyd-free 정렬 | 동일 | HOLD. origin ahead 1 |
| 2U_C 브랜치 | (체크아웃 없음) | STOM_Version_2U_C 8006cd93 | V2.79 custom 경로 | V2 신규 없음 | HOLD. origin ahead 26 |
| 2U_C 개발 | STOM_V.wt-dev | research/v516-d3-mcap-dev 97a59ad3 | 공식 lane 아님 | 해당 없음 | HOLD. dirty 보존 |
| V3 공식 | STOM_V.wt-3 | STOM_Version_3 c6ac10b2 | V3.35 경계 9d24b635 | V3.00 tip 09a11f83 | hop 시작점 |
| V3U | STOM_V.wt-3u | STOM_Version_3U 24cd79c1 | V3.35 pyd-free | 동일 잔여 | 공식 다음 overlay |
| 3U_C | STOM_V.wt-3uc | STOM_Version_3U_C 66220795 | 사이클 8 = V3.35 | 동일 잔여 | git merge --no-ff STOM_Version_3U |

~~~
V2 official   [####################] 100%  terminal V2.79
2U version    [####################] 100%  버전 완료 / ahead 1은 별건
2U_C / wt-dev [==== HOLD ==========]   0%  이번 사이클 제외
V3 official   [##############------]  87%  V3.35 / V3.40  (남은 hop 5)
V3U / 3U_C    [##############------]  87%  V3.35 동기, V3.36부터 대기
~~~

---

## 2. ASCII Flowchart

~~~
 GitHub devstom/STOM
        |
        +-- refs/tags/V2.0 (V2.79) ---- 신규 0 ----X  STOM_V / wt-2u 유지
        |                                              X wt-dev 투입 금지
        |
        +-- refs/heads/V3.00 (V3.40 + tail)
                  |
                  v
         [1] STOM_V.wt-3     STOM_Version_3
             restore --source=<version-boundary>
             커밋 제목: STOM V3.xx
             본문: _update.txt 해당 섹션 전문
             pyd 보존: ui/main_window.pyd
                  |
                  v
         [2] STOM_V.wt-3u    STOM_Version_3U
             같은 py 파일 overlay
             pyd 금지, ui/main_window.py 유지
             pyd 변경 hop(V3.38/39)만 추론 보정
             게이트: smoke + verify 8/8 + attr critical=0
                  |
                  v
         [3] STOM_V.wt-3uc   STOM_Version_3U_C
             git merge --no-ff STOM_Version_3U
             ingest pipeline 사용 금지
             게이트: 8/8 + tests/v3uc + allowlist diff
                  |
                  v
             기록 커밋 후 다음 버전으로 돌아간다
~~~

금지:

~~~
X git add -A
X rebase / reset --hard
X 여러 공식 버전을 한 커밋에 합치기
X V3U에서 official runtime 소스 수정 (backtest/strategy/trade/utility/stom.py/ui/create_widget 등)
X 3U_C hop에 v3uc_ingest_pipeline.py 사용
X wt-dev dirty 정리, 공식 overlay, 2U merge
X _database / _log / .gjc / backtest/graph / _database_backup_2026-05-22 커밋 또는 삭제
X refs/tags/V3.0 를 freshness 권원으로 사용
~~~

---

## 3. Text Tree - 워크트리 역할과 분석 렌즈

~~~
C:\System_Trading\STOM\
+-- STOM_V\              V2 ingress     렌즈: 공식 파일 + upstream pyd 보존
|                          이번: 문서만. V2.80 생기면 여기가 첫 입구
+-- STOM_V.wt-2u\        2U pyd-free    렌즈: V2 비-pyd 파일 = V2, 차이는 추론본만
|                          이번: HOLD. 3.13 정렬 3b7a3aeb 은 검증 통과, 미push
+-- STOM_V.wt-3\         V3 ingress     렌즈: 바이트 overlay + pyd 보존 + 한 버전=한 커밋
|                          이번: V3.36부터 공식 restore
+-- STOM_V.wt-3u\        V3U 추론       렌즈: official 0줄 + main_window.py 계약
|                          이번: overlay 후 attr inventory로 누락 탐지
+-- STOM_V.wt-3uc\       3U_C custom    렌즈: 3U merge + allowlist only
|                          이번: merge --no-ff, ingest 금지
+-- STOM_V.wt-dev\       2U_C 개발본    렌즈: Kiwoom 유지 선별 백포트 (나중)
                           이번: HOLD. 2026-09-12_2series_deferred_after_v340.md
~~~

모든 V3 hop 공통 분석 순서:

~~~
1. _update.txt 마커로 버전을 자른다
2. 직전 흡수 경계(현재 9d24b635) 이후 커밋만 본다
3. 파일을 4통으로 분류한다
     A. official runtime py  -> V3 공식 restore, V3U overlay
     B. ui/main_window.pyd   -> V3만 교체, V3U는 py 추론
     C. UI helper py         -> overlay 후 ui.X 신규 참조를 추론 입력으로 쓴다
     D. docs/scripts/tests   -> release overlay 제외. lane 기록만
4. V3U는 grep(ui.X) + attr inventory + 8/8 게이트로 계약을 잠근다
5. 3U_C는 merge만. custom 파일 충돌 시 custom 보존
~~~

---

## 4. Roadmap - 남은 hop 5개

로컬 V3.35는 c3db5f9c..9d24b635 까지 이미 넣었다. V3.36 changelog 앞 4줄은 그 tail이라 다시 넣지 않는다.

~~~
NOW --> V3.36 --> V3.37 --> V3.38(pyd) --> V3.39(pyd) --> V3.40+tail --> STOP
        hop1      hop2      hop3           hop4           hop5
        낮음      중        높음           높음           중
~~~

| 순서 | 버전 | 날짜 | upstream 범위 | 핵심 | pyd | V3U 추론 |
|---:|---|---|---|---|---|---|
| 1 | V3.36 | 07-23 | 9d24b635..2f83673c | 바이낸스 체결 처리, 중복 코드 제거 | 없음 | 순수 overlay 예상 |
| 2 | V3.37 | 07-27 | 2f83673c..3b7ef0d8 (tail 972aeca7 포함) | 위탁증거금율/선물 수익률, requirements | 없음 | overlay + test_data_layer 점검 |
| 3 | V3.38 | 08-02 | 3b7ef0d8..01f716e5 | 무료 실매매 제한, 차트/백테 UI | 있음 283648->311296 | stom_public 계약 추가 예상 |
| 4 | V3.39 | 08-14 | 01f716e5..182d09da | 라이선스 확인, 거래량분석 기준, Alt+L | 있음 311296->312832 | check_stom_public / subprocess_start 예상 |
| 5 | V3.40 | 08-22 | 182d09da..09a11f83 (marker 2b31a0f2 + tail) | 텔레그램 잔고청산, 매도 스크린샷, 코스닥150 틱가치 | 없음 | 순수 overlay 예상. telegram worker 확인 |

V3.40 tail (마커 이후, V3.41 없음, V3.35 선례로 이번 hop에 포함):

| commit | 날짜 | 내용 | 포함 이유 |
|---|---|---|---|
| 31f54d64 | 08-26 | 매도 텔레그램: dict_set[잔고청산] -> dict_bool[잔고청산] | 버그픽스. 지금 흡수 시점에 존재 |
| 09a11f83 | 08-26 | 코스닥150 틱가치 100000->10000, 주석 t8467 | 작은 LS 수정. 동일 |

한 hop이 공식 + V3U + 3U_C + 기록까지 끝나기 전에는 다음 버전으로 가지 않는다.

---

## 5. 버전별 파일 분류와 워크트리 동작

### 5.1 V3.36 - 순수 trade overlay

파일: _update.txt, trade/base_trader.py, trade/binance/binance_trader.py, trade/stock_usa/stock_usa_trader.py

| 워크트리 | 동작 |
|---|---|
| wt-3 | 4파일 restore. pyd 불변 확인. py_compile 3파일 |
| wt-3u | 동일 py overlay. MainWindow 계약 무관 예상 |
| wt-3uc | merge --no-ff |

changelog 재기술 항목(이미 V3.35 tail): 지정가 간소화, ordxctptncode, LS 체결 강화, 수신 간소화. 재적용 금지.

### 5.2 V3.37 - 백테/선물 광범위, pyd 없음

27파일. 선물 위탁증거금 -> 위탁증거금율, 수익률=위탁증거금 기준, 수수료=계약금 기준.
database_check.py seed 컬럼명 변경. requirements.txt pandas/numba/scipy 등 bump.

| 워크트리 | 동작 |
|---|---|
| wt-3 | 전체 official 파일 restore. pyd 불변 |
| wt-3u | overlay. tests/v3u/test_data_layer.py 가 future_info 컬럼을 가정하면 V3.34 때처럼 테스트만 보정 |
| wt-3uc | merge. custom DB 도구가 컬럼명을 하드코딩하면 tests/v3uc만 수정 |

### 5.3 V3.38 - 첫 pyd hop (높음)

24파일. 핵심 계약 변화:

~~~
BaseTrader.__init__(qlist, dict_set, market_infos)
        |
        v
BaseTrader.__init__(qlist, dict_set, market_infos, stom_public)

trade_process_start:
  ui.proc_trader = Process(..., ui.stom_public)   # V3.38

무료 라이선스면 실주문 대신 paper_trade
~~~

| 파일 | 변화 | 추론 입력 |
|---|---|---|
| ui/event_click/button_clicked_shortcut.py | trader args에 ui.stom_public | MainWindow attr stom_public 필요 |
| ui/event_click/button_clicked_backtest_engine.py | ui.back_sques 에 종목명 put | 이미 V3U에 back_sques 존재 |
| ui/event_click/table_cell_clicked.py | 선물(6,7,8)은 code=name | market_gubun 이미 존재 |
| ui/event_click/button_clicked_chart.py | DICT_INDICATOR 삭제, DICT_INDICATOR_BASE만 | MainWindow 무관 |
| ui/draw_chart/draw_chart_base.py | arrow zValue=30 | MainWindow 무관 |
| utility/settings/setting_base.py | 제로 딕셔너리 DICT_INDICATOR 삭제 | overlay만 |
| ui/update_widget/update_tablewidget.py | 분봉 상세 시간 표시 | overlay만 |

wt-3: pyd 포함 restore.
wt-3u: pyd 제외. overlay 후 게이트가 ui.stom_public CRITICAL을 띄울 가능성 높음 -> ui/main_window.py 에만 추가.

### 5.4 V3.39 - 둘째 pyd hop (높음)

V3.38의 ui.stom_public 전달이 바로 ui.check_stom_public() 호출로 바뀐다.

~~~
V3.38: Process(..., ui.stom_public)
V3.39: stom_public = ui.check_stom_public()
       Process(..., stom_public)

process_starter:
  if not ui.subprocess_start: return
~~~

| 파일 | 변화 | 추론 입력 |
|---|---|---|
| button_clicked_shortcut.py | check_stom_public() | MainWindow 메서드 필요 |
| ui/etcetera/process_starter.py | ui.subprocess_start 가드 | MainWindow bool attr 필요 |
| ui/create_widget/set_main_menu.py | 계정삭제 버튼 라벨 A->L | 위젯명 ad_pushButton 유지 |
| event_keypress 2파일 | Ctrl+A -> Ctrl+L | overlay |
| strategy/analyzer_volume_spike.py | 초당거래대금 -> 초당매수금액 | overlay. 전략 학습 의미 변경 |
| utility/db_control/database_check.py | 라이선스 확인 경로 가능 | 테스트 점검 |

check_stom_public 구현은 pyd 내부라 직접 못 본다. 추론 절차:

~~~
1. 사용처 grep: check_stom_public / stom_public / 무료 라이선스
2. 트레이더가 stom_public True면 paper_trade 하는 의미로 반환값(bool) 확정
3. V3U에 동명 메서드를 최소 구현 (시리얼/라이선스 필드 읽기)
4. 불확실하면 보수적으로 True(실매매 차단) 또는 기존 시리얼 판정 재사용
5. 추측 남발 금지. 게이트 PASS + 사용자 GUI 확인 항목으로 남긴다
~~~

현재 V3U main_window.py (V3.35)에는 stom_public / check_stom_public / subprocess_start 가 없다. V3.38/39 overlay 후 계약 게이트가 이 세 항목을 잡을 가능성이 높다.

### 5.5 V3.40 + tail

| 파일 | 변화 |
|---|---|
| utility/sub_process_and_thread/telegram_bot.py | 명령 잔고청산을 traderQ 로 전달 |
| trade/base_strategy.py | info_for_signal -> info_for_buy / info_for_sell (분봉 언팩 오류) |
| trade/base_trader.py | 매도 스크린샷: 전략청산 전 매도마다, 이후 잔고 없을 때 한 번 |
| tail base_trader.py | dict_bool[잔고청산] 로 수정 |
| tail trade/restapi_ls.py | 코스닥150 틱가치 10_000 |

V3U: telegram은 이미 ui.telegram worker가 있다. 이번 변경은 worker 내부라 overlay면 충분할 가능성이 높다. 그래도 8/8을 돌린다.

---

## 6. pyd 추론 - 워크트리별 렌즈

~~~
          V2                         V3
ui/ui_mainwindow.pyd           ui/main_window.pyd
        |                              |
        v                              v
wt-2u ui/ui_mainwindow.py      wt-3u ui/main_window.py
  참고만. 덮어쓰지 말 것         유일한 보정 허용 파일
~~~

| 보장 (자동) | 보장하지 않음 |
|---|---|
| 외부 ui.X attr 존재 (strict critical=0) | pyd 내부 로직의 수학적 동일 |
| orphan 핸들러 0, import/AST/smoke | 시각적 동일. 사용자 GUI 확인 |
| official 디렉터리 0줄 수정 | 라이선스 서버 실판정 |

이번 웨이브 예측:

~~~
V3.36  카테고리 없음 (trade 내부)
V3.37  테스트 전제 drift 가능 (database_check seed)
V3.38  A: ui.stom_public 누락 가능성 HIGH
V3.39  D: ui.check_stom_public 메서드 누락 HIGH
       A: ui.subprocess_start 누락 HIGH
V3.40  C: telegram 잔고청산은 worker 내부. 낮음
~~~

FAIL 시 수정 위치: ui/main_window.py 또는 tests/v3u/ 만.

---

## 7. hop 실행 명령 (V3.36 예시, 이후 동일)

### 7.1 사전

~~~powershell
git fetch https://github.com/devstom/STOM.git refs/heads/V3.00:refs/remotes/devstom_tmp/V3.00_latest --force
git show refs/remotes/devstom_tmp/V3.00_latest:_update.txt | Select-Object -First 20
~~~

V2 head가 여전히 2026-04-08 V2.79 이면 V2 체인은 건너뛴다.

### 7.2 wt-3 공식

~~~powershell
cd C:\System_Trading\STOM\STOM_V.wt-3
git status -sb
# 기대: STOM_Version_3, c6ac10b2, ?? .gjc 만

$from = '9d24b635'
$to   = '2f83673c'
git log --oneline "$from..$to"
git diff --name-only "$from..$to"
git restore --source=$to --worktree --staged -- _update.txt trade/base_trader.py trade/binance/binance_trader.py trade/stock_usa/stock_usa_trader.py
git ls-files "*.pyd"   # ui/main_window.pyd
python -m py_compile trade/base_trader.py trade/binance/binance_trader.py trade/stock_usa/stock_usa_trader.py
# 제목: STOM V3.36
# 본문: _update.txt 의 2026-07-23 V3.36 섹션 전문
# git add -A 금지. 경로 명시

git diff --name-only HEAD 2f83673c -- . ":!docs" ":!AGENTS.md" ":!CLAUDE.md" ":!.gitignore" ":!scripts" ":!tests"
~~~

### 7.3 wt-3u overlay

~~~powershell
cd C:\System_Trading\STOM\STOM_V.wt-3u
# _database_backup_2026-05-22, .gjc, .codegraph 보존

git restore --source=STOM_Version_3 --worktree --staged -- _update.txt trade/base_trader.py trade/binance/binance_trader.py trade/stock_usa/stock_usa_trader.py
# .pyd 는 restore 하지 않는다

python scripts/v3u_smoke_offline_gui.py --branch STOM_Version_3U --version V3.36 --offline --log-dir .omx/logs/v3u
python scripts/verify_v3u_pyd_gui_contract.py --branch STOM_Version_3U --version V3.36 --upstream-ref STOM_Version_3 --manifest .omx/logs/v3u/verify_YYYY-MM-DD_v336.json --log-dir .omx/logs/v3u
~~~

기록 커밋은 overlay와 분리해도 된다 (V3.35 선례: overlay 2fb212e2 + 기록 f4b8fb42).
v3uc_ingest_pipeline.py --dry-run 은 V3->V3U 미리보기로만 쓰고, live는 충돌/커밋 형식을 본 뒤에만.

### 7.4 wt-3uc merge

~~~powershell
cd C:\System_Trading\STOM\STOM_V.wt-3uc
git merge --no-ff STOM_Version_3U
python scripts/v3u_smoke_offline_gui.py --branch STOM_Version_3U_C --version V3.36 --offline --log-dir .omx/logs/v3u
python scripts/verify_v3u_pyd_gui_contract.py --branch STOM_Version_3U_C --version V3.36 --upstream-ref STOM_Version_3 --manifest .omx/logs/v3u/verify_3uc_YYYY-MM-DD_v336.json --log-dir .omx/logs/v3u
python -m pytest tests/v3uc -q
git diff --name-only STOM_Version_3U..HEAD
~~~

### 7.5 V3.38/39 추가 점검

~~~powershell
rg -n "stom_public|check_stom_public|subprocess_start" ui trade
rg -n "self\.stom_public|def check_stom_public|self\.subprocess_start" ui/main_window.py
~~~

없으면 main_window.py 의 _init_runtime_state / 메서드에만 추가하고 게이트를 다시 돌린다.

---

## 8. 게이트 분리

| 게이트 | 지금 | 닫히는 조건 |
|---|---|---|
| 계획 기록 | 본 문서 | 본 커밋 |
| 구현 overlay | 미착수 | hop별 STOM V3.xx + parity |
| pyd 추론 | V3.35 과거 PASS | V3.38/39에서 재검증 |
| tests | 과거 8/8 + v3uc 32 | 매 hop 재실행. 과거 green 재사용 금지 |
| 사용자 GUI | V3.33~35 대기 중 | 흡수 후 별도. 자동 PASS != 시각 확인 |
| push | 미실시 | 사용자 명시 |
| 2U_C 백포트 | HOLD | 2026-09-12_2series_deferred_after_v340.md |
| 릴리스/실거래 | 미실시 | 별 게이트 |

---

## 9. 문서 배치

| 문서 | 위치 | 역할 |
|---|---|---|
| 본 파일 | wt-3u, wt-3uc, STOM_V | V3 hop 정본 |
| 2026-09-12_2series_deferred_after_v340.md | 동일 | 2U/2U_C/wt-dev 추후 |
| docs/V3U_NEXT_STEPS.md | wt-3u만 | 사이클 22 계획 이력 |
| docs/V3U_C_NEXT_STEPS.md | wt-3uc만 | 사이클 9 계획 이력 |

V3 공식 lane(wt-3)에는 계획 문서를 넣지 않는다. 실행 세션은 디스크의 wt-3u 경로를 읽는다.

---

## 10. 다음 세션 첫 명령

~~~powershell
cd C:\System_Trading\STOM\STOM_V.wt-3
git status -sb
git log -1 --oneline
# 기대: c6ac10b2 STOM V3.35
# 시작: V3.36 restore from 2f83673c (범위 9d24b635..2f83673c)
~~~
