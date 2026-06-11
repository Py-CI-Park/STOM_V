# V3U pyd 추론 lessons learned (지속 관리 문서)

- 최초 작성: 2026-05-12
- 대상 lane: `STOM_Version_3U`
- 본 문서 정책: **새 결함 발견 시 §6에 기록 추가 + 재발 방지 액션 §5에 반영**
- 갱신 주기: 결함 발견 즉시. lane 종료 시까지 영구 유지.
- 참조 문서: `docs/V3U_PYD_REMOVAL_PLAN.md` §11, `docs/V3U_TEST_AUTOMATION_GUIDE.md`, `CLAUDE.md`

---

## 1. 본 문서의 목적

V3U pyd-free 전환 과정에서 발견된 추론 결함의 **근본 원인을 기록하고 재발을 방지**한다. 자동 검증 31~37 케이스가 PASS한 상태에서도 사용자 시각 검증으로만 발견되는 결함이 누적적으로 발견됐다는 사실 자체가 중요한 lesson이다.

본 문서는 **단발 보고서가 아니라 지속 관리 문서**다. V3U lane이 살아있는 동안 새 결함이 발견될 때마다 §6에 기록을 추가하고, 패턴이 반복되면 §5의 재발 방지 액션을 갱신한다.

---

## 2. 사이클별 결함 요약

### 사이클 1 (2026-05-05~12, 본 문서 초기 작성 시점)

총 9개 결함 — 모두 사용자 첫 시각 검증(2026-05-12 09:46~11:14) 3회 사이클에서 발견됨.

| # | 결함 | 카테고리 | 발견 단계 | 수정 커밋 |
|---|---|---|---|---|
| 1 | `backengine_starting` 누락 | runtime state | 1차 시각 (백테 클릭) | `72308bca` |
| 2 | `back_tick_cunsum` 누락 | runtime state | 1차 시각 | `72308bca` |
| 3 | `qtimer1` 자동 시작 누락 | timer wiring | 1차 시각 (창 제목 정적) | `72308bca` |
| 4 | 콘솔 로깅 부재 | infrastructure | 1차 진단 시도 | `72308bca` |
| 5 | qlist V3 컨벤션 mismatch | queue convention | 2차 분석 (홈 데이터) | `b72f0162` |
| 6 | WebCrawling worker 미시작 | worker startup | 2차 분석 | `b72f0162` |
| 7 | `draw_homechart` vs `draw_home_chart` | naming | 3차 분석 (placeholder 영구) | `25f61980` |
| 8 | `webc.signal.connect` 누락 | signal/slot wiring | 3차 분석 | `25f61980` |
| 9 | `UpdateCrawlingData`/`TelegramMsg` 인스턴스 누락 | helper inventory | 3차 분석 | `25f61980` |

---

## 3. 근본 원인 5가지

### 근본 원인 1: pyd 내부를 직접 못 봄

`ui/main_window.pyd`는 컴파일된 binary다. 내부 attr·메서드 목록을 직접 조사할 수 없다. 추론은 외부 사용처(`ui.X.Y` 패턴)를 grep으로 역추적해 reverse-engineer 한다.

**한계**: 외부 호출 빈도가 낮은 attr은 grep에 약하게 잡혀 누락된다 (예: `backengine_starting`은 5곳뿐).

### 근본 원인 2: 2U 추론 경험을 체계적으로 옮기지 않음

`docs/V3U_PYD_REMOVAL_PLAN.md` §5는 2U를 "참고 자료로만 사용"한다고 명시했다. 의도는 V3 구조와 V2/Kiwoom 구조 혼재를 막는 것이었으나, 결과적으로 **2U가 이미 풀어둔 명백한 메타 패턴(worker startup, queue convention, signal connect, helper inventory)까지 처음부터 다시 추론하게 됐다**.

| 비교 | init attr 수 |
|---|---|
| 2U `ui_mainwindow.py` (V2 pyd 추론본) | 156 |
| V3U `ui/main_window.py` (사이클 1 시작 시점) | 98 |
| 차이 | 약 30개 단순 누락 + 약 30개 V3-specific 차이 |

→ **2U를 init 출발점으로 사용했다면 사이클 1의 결함 9개 중 7개는 첫 시도에 잡혔을 것.**

### 근본 원인 3: 외부 호출 일치 검증 미적용

pytest 31 케이스 PASS 상태에서도 `ui.draw_homechart` (밑줄 없음) vs 우리 부착 `ui.draw_home_chart` (밑줄) mismatch는 검증되지 않았다. 헤드리스 모드라 worker 실제 동작 확인도 못함.

→ **검증 시스템이 "외부 호출 site와 우리 init의 일치"를 자동 검증하지 않음.**

### 근본 원인 4: V3 worker qlist 컨벤션 미문서화

V3 worker(`trade/base_receiver.py`, `base_trader.py`, `base_strategy.py`, `utility/sub_process_and_thread/*`)가 `qlist[N]`을 hardcoded 인덱스로 직접 access한다. 우리는 컨벤션을 명시 안 한 채 임의 큐 순서로 init했고, 결과적으로 worker가 잘못된 큐로 메시지를 push하는 silent 결함이 됐다.

| qlist 인덱스 | V3 컨벤션 | 사이클 1 시작 시점 V3U |
|---|---|---|
| 8 | receivQ | totalQ ❌ |
| 9 | traderQ | testQ ❌ |
| 10 | stgQs (list) | kimpQ ❌ |
| 11 | liveQ | wdzservQ ❌ |
| 12 | testQ | (없음) ❌ |

→ **컨벤션을 docs로 사전 고정하지 않은 채 추론.**

### 근본 원인 5: signal/slot wiring inventory 빈약

`pyqtSignal` 기반 worker(WebCrawling)는 `start()`만으로 데이터가 흐르지 않는다. `signal.connect(handler)` 호출이 필수다. V3U 사이클 1 시작 시점에는 worker startup 메서드 자체가 없었고(`_init_workers`), 이후 추가 시에도 `start()`만 했다.

→ **"worker 시작 = 단순히 start() 호출"이라는 잘못된 mental model.**

---

## 4. 패턴 분류 — 향후 결함 예측

근본 원인 분석을 토대로 향후 발견될 가능성이 높은 결함 카테고리:

### 카테고리 A: 추가 누락 runtime state attr
- 외부 핸들러가 `if ui.X:` 로 참조하는 boolean state
- 외부 핸들러가 `ui.X = True/False` 로 단순 할당하는 state
- 예측 위험도: **medium** (이미 사이클 1에서 2개 발견, 더 있을 수 있음)

### 카테고리 B: 추가 누락 worker
- V2/Kiwoom에는 있던 worker가 V3에서도 동일하게 필요할 가능성
- 후보: `proc_chqs` (ChartHogaQuery 프로세스), `proc_tele` (TelegramBot QThread), `KimpWebSocketManager`, `PyttsxSound`
- 예측 위험도: **high** (사용자가 거래/실시간차트/김프 기능 클릭 시 발견 예상)

### 카테고리 C: 추가 signal/slot connect 누락
- 다른 QThread worker(TelegramBot, KimpWebSocketManager)도 signal 가질 수 있음
- 예측 위험도: **medium**

### 카테고리 D: helper attr 이름 mismatch
- V3 외부 코드가 사용하는 attr 이름과 우리가 부착한 이름의 불일치
- 후보: `update_widget`, 기타 미부착 helper
- 예측 위험도: **medium**

### 카테고리 E: 큐 producer/consumer 불일치
- V3 worker가 특정 큐를 consumer로 사용하는데 우리가 producer 못 만든 경우
- 예측 위험도: **low** (qlist 컨벤션 fix 후)

---

## 5. 재발 방지 액션 (지속 갱신)

### 액션 1: 2U attr 명세를 V3U init 출발점으로 시스템화 ✅ **적용 완료 (사이클 5)**

**목표**: 2U `ui_mainwindow.py`의 374개 self.X attr을 자동 추출하고, V3 외부 참조와 cross-check해 V3U init 누락을 자동 감지한다.

**구현**:
- `scripts/v3u_attr_inventory_diff.py` (3-way diff 도구)
- `tests/v3u/test_attr_inventory_drift.py` (회귀 차단 3 케이스)

**baseline (사이클 5 시작)**: CRITICAL drift 68 → max 100 (여유 32)
**baseline 정책**: 사이클 진행 중 CRITICAL이 줄어들면 함께 감소.

### 액션 2: 외부 ui.X.Y 호출 자동 inventory + cross-check ✅ **적용 완료 (사이클 5)**

**목표**: AST·정규식 grep으로 외부 모든 `ui.*` 참조 추출 → 우리 init한 attr + widget builder setattr 결과와 자동 3-way diff.

**구현**: 액션 1과 통합 (`scripts/v3u_attr_inventory_diff.py`가 외부 ref + widget builder setattr + V3U init 동시 추출).

**boundary**:
- CRITICAL: V3 external 참조 + V3U init/widget builder 모두에 없음 → 실 결함
- WARN: 2U has + V3 external uses + V3U init 누락 → V3에도 확실히 필요한 패턴
- INFO: 2U-only (V2/Kiwoom 전용), V3U-extra (자체 추가)

**한계 (2026-06-11 결함 #16에서 확인)**: 도구가 `ui.X =` 외부 할당을 widget-builder
setattr와 동일하게 '커버됨'으로 분류하므로, 외부 코드가 같은 attr을 **할당보다 먼저
읽는** read-before-write 패턴(예: `process_starter.py:95`가 읽고 `:96`이 할당)은
CRITICAL로 잡지 못한다. 보강 옵션은 `docs/V3U_NEXT_STEPS.md` §3 A7. 임시 안전망:
`tests/v3u/test_smoke.py::test_cpuper_network_stat_attrs_initialized`.

### 액션 3: V3 worker qlist 컨벤션 자동 검증 ✅ **적용**

**적용 커밋**: `b72f0162`
**적용 위치**: `tests/v3u/test_smoke.py::test_qlist_v3_convention_order`

### 액션 4: signal/slot connect inventory ✅ **부분 적용**

**적용 커밋**: `25f61980`
**적용 위치**: `tests/v3u/test_smoke.py::test_webcrawling_signal_connected`

**잔여 작업**: 다른 worker(ChartHogaQuery, TelegramBot, KimpWebSocketManager) 추가 시 동일 패턴 적용.

### 액션 5: 사용자 시각 검증 즉시 회귀 테스트화 ✅ **패턴 정착**

사이클 1 9개 결함 모두 발견 즉시 회귀 테스트로 변환 완료. 향후 같은 결함은 `pytest tests/v3u/`에서 자동 차단.

---

## 6. 결함 기록 (지속 갱신 — 새 결함 발견 시 추가)

각 결함은 다음 형식으로 기록한다.

```
### 결함 #N (YYYY-MM-DD): 한 줄 제목

- 카테고리: A/B/C/D/E (§4 분류)
- 발견 경로: 사용자 시각 / 자동 회귀 / V3 흡수 게이트
- 외부 호출 site: 파일:줄 (참조 위치)
- 우리 누락 위치: 파일:줄
- 수정 커밋: <hash>
- 회귀 테스트: 파일::함수
- 근본 원인 매핑: §3-N
- 재발 방지 액션 매핑: §5-N
```

---

### 결함 #1 (2026-05-12): backengine_starting 누락

- 카테고리: A (runtime state)
- 발견 경로: 사용자 백테 시작 버튼 클릭
- 외부 호출 site: `ui/event_click/button_clicked_backtest_start.py:11,114`, `button_clicked_backtest_engine.py:64,214`, `button_clicked_stg_editer.py:1339`
- 우리 누락 위치: `ui/main_window.py::_init_runtime_state`
- 수정 커밋: `72308bca`
- 회귀 테스트: `tests/v3u/test_smoke.py::test_runtime_state_attrs_initialized`
- 근본 원인 매핑: §3-1, §3-2
- 재발 방지 액션 매핑: §5-1, §5-2

### 결함 #2 (2026-05-12): back_tick_cunsum 누락

- 카테고리: A (runtime state)
- 외부 호출 site: 백테 진행 카운터
- 수정 커밋: `72308bca`
- 회귀 테스트: `tests/v3u/test_smoke.py::test_runtime_state_attrs_initialized`
- 근본 원인 매핑: §3-1, §3-2

### 결함 #3 (2026-05-12): qtimer1 자동 시작 누락

- 카테고리: timer wiring (sub-category of B)
- 발견 경로: 사용자 메인창 제목이 정적 표시 (시계 갱신 안 됨)
- 우리 누락 위치: `ui/main_window.py::_init_timers`에서 qtimer2/3은 start, qtimer1만 빠짐
- 수정 커밋: `72308bca`
- 회귀 테스트: `tests/v3u/test_smoke.py::test_qtimer1_auto_started_for_process_starter`
- 근본 원인 매핑: §3-1 (단순 추론 누락)

### 결함 #4 (2026-05-12): 콘솔 로깅 부재

- 카테고리: infrastructure
- 발견 경로: 1차 진단 시 cmd 창에 아무 로그도 없음
- 수정 커밋: `72308bca` (StreamHandler 부착 + boot INFO 메시지)
- 근본 원인 매핑: 별도 (V3U init 자체에 logger 인프라 없었음)

### 결함 #5 (2026-05-12): qlist V3 컨벤션 mismatch

- 카테고리: queue convention
- 발견 경로: 홈 대시보드 데이터 source 추적 중 worker 코드의 `qlist[8]=receivQ` 발견
- 외부 호출 site: `trade/base_receiver.py:47-48`, `base_trader.py:56-60`, `base_strategy.py:39-40`, `utility/sub_process_and_thread/telegram_bot.py:26`
- 우리 누락 위치: `_init_queues`에서 V3 컨벤션 무시하고 임의 순서
- 수정 커밋: `b72f0162`
- 회귀 테스트: `tests/v3u/test_smoke.py::test_qlist_v3_convention_order`
- 근본 원인 매핑: §3-4
- 재발 방지 액션 매핑: §5-3 (적용 완료)

### 결함 #6 (2026-05-12): WebCrawling worker 미시작

- 카테고리: B (worker startup)
- 외부 호출 site: 외부 코드가 `ui.webc.is_alive()` 등 호출 가능
- 우리 누락 위치: `_init_workers` 메서드 자체가 없었음
- 수정 커밋: `b72f0162`
- 회귀 테스트: `tests/v3u/test_smoke.py::test_webcrawling_worker_started`
- 근본 원인 매핑: §3-2, §3-5

### 결함 #7 (2026-05-12): draw_homechart vs draw_home_chart 이름 mismatch

- 카테고리: D (helper attr 이름 mismatch)
- 외부 호출 site: `ui/update_widget/update_crawling_data.py:13`
- 우리 누락 위치: `_init_update_and_chart_helpers`에서 `self.draw_home_chart`(밑줄)로만 부착
- 수정 커밋: `25f61980` (alias 추가)
- 회귀 테스트: `tests/v3u/test_smoke.py::test_v3_helper_attr_names`
- 근본 원인 매핑: §3-3

### 결함 #8 (2026-05-12): webc.signal.connect 누락

- 카테고리: C (signal/slot wiring)
- 외부 호출 site: WebCrawling이 `pyqtSignal`로 emit하는데 receiver 없음
- 수정 커밋: `25f61980`
- 회귀 테스트: `tests/v3u/test_smoke.py::test_webcrawling_signal_connected`
- 근본 원인 매핑: §3-5

### 결함 #9 (2026-05-12): UpdateCrawlingData/TelegramMsg 인스턴스 누락

- 카테고리: D (helper inventory)
- 외부 호출 site: 위 결함 #7과 같은 흐름. ui.update_crawling_data 인스턴스 자체 없음
- 수정 커밋: `25f61980`
- 회귀 테스트: `tests/v3u/test_smoke.py::test_v3_helper_attr_names`
- 근본 원인 매핑: §3-2, §3-3

### 결함 #16 (2026-06-11): last_recv/memory_per/net_recv 미초기화 — V3.24 흡수 회귀 (read-before-write)

- 카테고리: A (runtime state) — **카테고리 A 3번째 반복** (#1·#2 이후)
- 발견 경로: pyd→py 추론 재검증 심층 감사 (통합 게이트 8/8 PASS 상태에서 수동 교차 감사로 발견 — §5 자동망 회피 사례)
- 외부 호출 site: `ui/etcetera/process_starter.py:95` (last_recv 읽기),
  `ui/update_widget/update_progressbar.py:42/45` (memory_per), `:43/46` (net_recv)
- 우리 누락 위치: `ui/main_window.py::_init_runtime_state` (cpu_per만 init, 나머지 3개 부재)
- 유입 시점: upstream V3.24(`22782984`)가 `_update_cpuper()`를 process_starter.py에 추가 →
  V3U 흡수 커밋 `be593744`가 외부 소스는 반영했으나 pyd 내부 초기화 대응분을 누락
- 증상 연쇄: qtimer1 매초 → `net_io.bytes_recv - ui.last_recv` → `__getattr__` no-op 함수 반환
  → `int - function` TypeError (thread_decorator 데몬 스레드) → 자기치유 할당(96행) 미도달
  → memory_per/net_recv 영구 미설정 → `update_progressbar.py:42` `setValue(함수)` TypeError
  → `MainWindow.UpdateProgressBar` try/except가 매 500ms 침묵 삼킴
  → MEM/NET 게이지·다이얼로그 버튼 스타일·백테 프로세스 26종 깜빡임 표시·로그 오류
  알림소리·풍경사진 요청(webcQ) 전부 비활성
- 수정: `_init_runtime_state`에 `last_recv = 0`, `memory_per = 0`, `net_recv = 0.0` 추가
- 수정 커밋: (본 사이클)
- 회귀 테스트: `tests/v3u/test_smoke.py::test_cpuper_network_stat_attrs_initialized`
- 자동 검증망이 못 잡은 이유 2가지:
  1. attr inventory가 `ui.X =` 외부 할당(`process_starter.py:96-98`)을 '커버됨'으로 분류 —
     **read-before-write 맹점** (`scripts/v3u_attr_inventory_diff.py:137` 할당 패턴 추출)
  2. `__getattr__` no-op fallback이 AttributeError fail-fast를 차단 + 사이클 5·6 시각 검증은
     V3.24 흡수(2026-05-27) **이전**이라 본 회귀를 관찰할 수 없었음
- 근본 원인 매핑: §3-1 (pyd 내부 init 미관찰), §3-3 (외부 호출 일치 검증 한계)
- 재발 방지 액션 매핑: §5-2 한계 갱신 (read-before-write) + NEXT_STEPS §3 신규 옵션 A7 (도구 보강)

### 사이클 15 (2026-06-11): V3.30~V3.32 흡수 — 게이트가 신규 pyd 계약(homepg)을 첫 실전 차단

V3 upstream(`refs/heads/V3.00`, stale tag 아님) V3.30~V3.32를 버전별로 흡수했다.
상세는 `docs/update_log/2026-06-11_v3u_v330_v332_pyd_free_update.md`.

**게이트 가치 첫 실전 입증**: V3.32 홈탭 마우스오버가 pyd 내부에서 초기화하던
`ui.homepg` dict를 신규 요구 → 1차 게이트에서 attr inventory CRITICAL drift 1 +
pytest drift 테스트 FAIL로 **커밋 전 자동 차단**. `_init_runtime_state`에 빈 dict
추가로 해소. 첨자 할당(`ui.homepg[0] = x`)은 도구의 setattr 추출에 잡히지 않는
것이 올바른 동작임을 확인 (attr 미생성이므로 실제로 init 필요).

**의도적 변경**: V3.32 supertonic 삭제로 tts_sound placeholder 사유 소멸 →
실 TextToSpeak(win32com SAPI) 부착 (soundQ 소비자 복원, 알림소리 parity).
회귀 테스트 `test_text_to_speak_attach_contract` 추가 (pytest 49).

**잔여**: V3.32 tail `fcc626a5`(윈도우 핸들 ctypes 수정) 미포함 — 다음 V3 흡수
시 formal 포함. `change_title_bar_color` 오류 관찰 시 원인 후보 1순위.

**사이클 15 시각 검증 결과 (2026-06-11, B1) — 결함 0건으로 종결**:
- 부팅 5 worker INFO 정상 (MainWindow/TelegramBot/ChartHogaQuery pid=137952/
  TextToSpeak/WebCrawling), 10분 세션 traceback 0건
- 종료 5단계 클린 (timers → proc_chqs 종료 OK → tts_sound → telegram → webc
  graceful timeout 위임), exit code 0
- 사용자 시각 확인 전 항목 정상: MEM/NET 게이지(결함 #16 fix), DB관리 탭
  응답(A5 chqs), 홈탭 마우스오버(V3.32 homepg), 읽기속도 윈도우 음성(V3.32 TTS)
- 누적 검증 의미: 결함 #16 + A5 + TTS 실 worker + V3.30~32 흡수가 한 세션에서
  동시 검증됨. proc_chqs 실 프로세스의 spawn→종료 lifecycle 첫 실가동 확인.

### A5 적용 (2026-06-11): proc_chqs ChartHogaQuery 실 spawn — 결함 #12 잔여 의무 완결

- 배경: 결함 #12(2026-05-20)는 AttributeError 방지 placeholder까지만 적용하고
  "V3 pyd가 실제로 어떻게 ChartHogaQuery를 spawn하는지 reactive 학습 후 진짜
  Process로 교체"를 잔여 의무로 남겼다. 사이클 13 재검증 감사에서 2U 선례
  (`wt-2u/ui/ui_mainwindow.py:344` `Process(target=ChartHogaQuerySound,
  args=(qlist, dict_set), daemon=True)`)와 V3 동일 계약 클래스
  (`utility/sub_process_and_thread/chart_hoga_query.py:25`, `__init__` →
  `_main_loop()` 진입), pyd import 증거(`ui/etcetera/import_hook.py:25`)를 확보해
  추론 불확실성이 해소됐다.
- 영향 해소: queryQ/chartQ/hogaQ 소비자 부재로 비활성이던
  `if ui.proc_chqs.is_alive():` 가드 47곳 (DB관리 탭 버튼 10개, 차트/호가 조회,
  설정 저장 반영, 전략에디터/GA/옵튜나 등) 활성화.
- 적용: `_init_workers`에 `Process(target=ChartHogaQuery, args=(self.qlist,
  self.dict_set), daemon=True)` spawn + `process_kill`에 terminate/join cleanup
  (A4/A6의 proc_chqs 분 함께 처리).
- pytest 안전 가드: conftest가 `STOM_V3U_DISABLE_CHQS=1` 설정 (매 테스트 실
  child process spawn 방지). webc의 `STOM_V3U_DISABLE_WEBC` 패턴 재사용.
- 회귀 테스트: `tests/v3u/test_smoke.py::test_chart_hoga_query_spawn_contract`
  (Process spy monkeypatch로 target/args/daemon/start/terminate 계약 검증)
- 잔여: 실 spawn 후 child process의 DB 연결·hoga 갱신 동작은 사용자 시각 검증
  (B1)으로 확인 필요. terminate의 mid-write 중단 가능성은 daemon=True OS cleanup과
  동일 수준 (2U 선례와 같은 트레이드오프).
- 근본 원인 매핑: §3-1 (pyd 내부 spawn 미관찰) — 2U 선례 교차 검증으로 해소
- 재발 방지 액션 매핑: §5-1 (2U attr/패턴 명세를 출발점으로 사용)

### 사이클 11 (2026-05-23): 3U_C lane E7 strategy.db 조건식 V2→V3 마이그레이션

사이클 10 끝 사용자 통찰 — "조건식(strategy.db)이 V2 시절 데이터인데 V3는 stock_buy(밑줄) 컨벤션이라 백테 못 함". 즉시 사이클 11 발동 + 4단계 워크플로우.

**3U_C lane 사이클 3 산출** (origin/STOM_Version_3U_C `87b6645b`):
- `scripts/v3uc_strategy_migration.py` (220 lines, scan/migrate + --target 9종 + dry-run/force)
- `tests/v3uc/test_strategy_migration.py` (5 회귀 PASS)
- carry-forward registry 사이클 3 등록

**V3U lane 실 데이터 변환**:
- V2 컨벤션 `stockbuy/stocksell/...` → V3 컨벤션 `stock_buy/stock_sell/...` (밑줄 추가)
- 51 매수 + 35 매도 + 2/2/5 옵티 = **총 95 rows V2→V3 복사, 에러 0**
- post-verification: V2 rows == V3 rows == 95 ✅

**V3U lane / V3 official 영향**: 0건 (도구는 3U_C, 실 변환은 사용자 _database/strategy.db).

**V3 거래소별 prefix 패턴 정본화**:
- `stock` (국내주식01·02), `stock_etf` (ETF03·04), `stock_etn` (ETN05·06)
- `stock_usa` (해외주식07·08)
- `coin`, `future`, `future_nt` (야간), `future_os` (해외), `coin_future`

**잔여**:
- 사용자 백테 시각 확인 (사이클 10 Step 6과 통합 가능)
- 사용자가 V2에서 다른 거래소(coin/future/stock_etf) 조건식 만들었다면 --target 별도 호출

### 사이클 10 (2026-05-22~23): 3U_C lane E5 + A++ DB 마이그레이션 끝까지 자동 실행

V3 LS API 백테 가능하게 하는 DB 마이그레이션을 A++ 7단계로 진행. Step 1~5는 Claude 자율 완료, Step 6(시각 확인 1분)만 사용자 잔여.

**3U_C lane 사이클 2 산출** (origin/STOM_Version_3U_C `c0c43958`):
- `scripts/v3uc_db_compatibility_check.py` (300 lines, --scan/--add-pk/--analyze-extra)
- `tests/v3uc/test_db_compatibility.py` (7 케이스 PASS)
- `docs/V3U_C_DB_MIGRATION_PLAN.md` (종합 조사 + A++ 절차)

**V3U lane 실행 결과** (Step 2~5 wt-3u에서):
- Step 2: `_database_backup_2026-05-22` 백업 (1175 파일)
- Step 3: `update_db_20260418.py` 19 worker 완료, V2→V3 컬럼 변환 (1166 stock DB)
- Step 4: 사전 진단 — 89,699 stock 테이블 모두 PK 없음 → V3.08 호환 X
- Step 5: 88,534 테이블 PK 추가 (에러 0), 잔여 1,165는 moneytop (update_db.py 동일 정책 skip)
- Post-verification: stock data 테이블 PK 100% 적용

**V3U lane 영향**: 0건 (도구·테스트·문서는 3U_C, 실 실행은 사용자 데이터 _database/ 변환).
**V3 official 영향**: 0건.
**카탈로그**:
- 3U_C E5 옵션 ✅ 완료
- 기타 DB(backtest/code_info/setting/strategy/tradelist) PK 누락 분 — 별도 사이클 후보

### 사이클 9 (2026-05-22): 3U_C lane E1 V3.X 흡수 자동화 파이프라인 도입

3U_C lane(`wt-3uc`)에서 첫 custom 작업 사이클. V3U_TRANSITION_AUDIT §6.3 옵션 E1 적용.
V3U lane 결함이 아닌 3U_C 신규 산출이므로 `docs/V3U_C_INFERENCE_LESSONS.md`가 상세 기록 진실 원천.

**3U_C 사이클 1 산출** (2 커밋 — origin/STOM_Version_3U_C):
- `ebd9a8f3` 3U_C E1 V3.X 흡수 자동화 파이프라인을 도입한다
- `9f565c3d` 3U_C CARRY_FORWARD_REGISTRY에 사이클 1 E1 항목을 등록한다

**핵심 산출물**:
- `scripts/v3uc_ingest_pipeline.py` (5 T-step 흡수 자동화)
- `tests/v3uc/test_ingest_pipeline.py` (4 unit 케이스)
- `docs/V3U_C_INGEST_PIPELINE.md` 운영 매뉴얼
- `docs/V3U_C_INFERENCE_LESSONS.md` 3U_C 결함 진실 원천 (V3U와 별도)
- `docs/V3U_C_NEXT_STEPS.md` 3U_C decision tree (V3U와 별도)

**V3U lane 영향**: 0건. 3U_C 신규 파일만 추가. V3U 안전망(`tests/v3u/`, `scripts/v3u_*`, `ui/main_window.py`) 0줄 수정.

**V3 official 영향**: 0건 (invariant 유지).

**향후 운영 흐름** (V3.19 발표 시):
```
cd wt-3u
python wt-3uc/scripts/v3uc_ingest_pipeline.py --version 19 --upstream-ref STOM_Version_3 --dry-run
# PASS 확인 후
python wt-3uc/scripts/v3uc_ingest_pipeline.py --version 19 --upstream-ref STOM_Version_3 --live
# T01 merge → T02 verifier → T03 audit → T04 commit → T05 push 자동
```

### 사이클 8 거버넌스 작업 (2026-05-22): 3U_C 생성 Phase A·B 완료 — 결함 0건

V3U_TRANSITION_AUDIT §5 Phase A·B 적용. 신규 결함 없이 거버넌스 + branch + worktree
구축 완료. 3U_C lane이 V3U 안전망(45 pytest + baseline 0)을 자동 상속.

**Phase A (commit 2ba974f8) 갱신 docs**:
- CARRY_FORWARD_REGISTRY.md: V3U_C custom allowlist rule + V3U_C lane carry-forward 절
- WORKTREE_STRATEGY.md: 3단계 Verification Order (3U vs 3 / 3U_C vs 3U / 3U_C vs 3)
- V3U_NEXT_STEPS.md: 그룹 E (V3U_C 작업) 4 옵션 (E1~E4)

**Phase B 워크트리 인벤토리** (2026-05-22 시점):
| 경로 | branch | HEAD |
|---|---|---|
| STOM_V | STOM_Version_2 | adfe80c7 |
| wt-2u | STOM_Version_2U | 3b7a3aeb |
| wt-3 | STOM_Version_3 | 7faec937 |
| wt-3u | STOM_Version_3U | 2ba974f8 |
| **wt-3uc (신규)** | **STOM_Version_3U_C** | 2ba974f8 |
| wt-dev | STOM_Version_2U_C | 6e8e23d0 |

**3단계 verification 사전 검증**:
- `3U vs 3U_C`: diff 비어있음 (Phase B 직후 invariant 유지)
- 3U_C pytest collect: 46 케이스 정상 (V3U 안전망 자동 상속)

**Remote sync**: origin/STOM_Version_3U_C 신규 push 완료.

### 결함 #15 (2026-05-22): ui.web_dashboard placeholder 사전 차단 (A4)

- 카테고리: D (helper inventory, placeholder)
- 발견 경로: 사이클 7 A4 사전 정찰 (외부 ref grep)
- 외부 호출 site: `ui/event_click/button_clicked_shortcut.py:252-254/279-280`
  - 252: `ui.web_dashboard = DashboardStarter(...)` (부착)
  - 253: `ui.web_dashboard.log_received.connect(ui.web_dashboard_log)` (signal connect)
  - 254: `ui.web_dashboard.start()` (시작)
  - 279: `if ui.dict_set['웹대시보드'] and ui.web_dashboard:` (None 체크 후 사용)
  - 280: `ui.web_dashboard.stop()`
- 위험: 사용자 단축키로 활성화 전 다른 site에서 `ui.web_dashboard` 참조 시 AttributeError
- 우리 누락: `_init_runtime_state`에 placeholder 부재
- 수정: `self.web_dashboard = None` 추가 (사용자가 단축키로 DashboardStarter 부착)
- 회귀 테스트: `tests/v3u/test_smoke.py::test_web_dashboard_attr_present_for_safe_attribute_access`
- 근본 원인 매핑: §3-1 (pyd 내부 spawn 메커니즘 미관찰), §3-2 (2U는 web_dashboard 컨셉 없음)

### A3 보강 (2026-05-22): verifier UX 단계 분리

`verify_v3u_pyd_gui_contract.py`가 8 stage 결과를 [PASS]/[FAIL]/[SKIP] 라인으로
명시 출력. V3 흡수 시 어느 단계가 fail인지 즉시 파악 가능.

신규 8 stage:
1. upstream_pyd_evidence (V3 lane pyd 보존 검증)
2. tracked_pyd_guard (V3U tracked .pyd 0건)
3. mainwindow_ast (V3U main_window.py AST 정합성)
4. imports (V3U import 누락 없음)
5. contract_manifest (GUI contract inventory)
6. offline_smoke (구조 smoke)
7. pytest_gate (45 케이스 PASS)
8. **attr_inventory_diff** (CRITICAL=0 strict, A3 신규 단계)

`run_attr_inventory_diff(log_dir)` 신규 함수 — strict 모드 호출 + summary 파싱.

### 사이클 6 시각 검증 결과 (2026-05-21): 신규 결함 0건 — fix #10·#11·#13 검증 PASS

A1·A2 사전 정찰로 차단된 결함 7건이 모두 효과적이었음을 사용자 시각 검증으로 확인.
fix #13 (WebCrawling OSError swallow)도 정상 동작 — 종료 stderr이 traceback 0건.

**부팅 로그 (4 INFO)**:
- MainWindow boot OK
- TelegramBot 시작 OK (결함 #11 fix 효과 가시화)
- WebCrawling.signal connected (결함 #8 효과)
- WebCrawling 시작 OK (결함 #6 효과)

**종료 로그 (3 INFO)**:
- process_kill: timers stopped (결함 #10)
- process_kill: telegram 종료 OK (결함 #11 cleanup, 사이클 6 신규)
- process_kill: webc graceful 종료 timeout (결함 #13 안전 fallback)

**OSError / Traceback**: 0건 — fix #13 의 효과 100% 검증

이 사이클은 **A1·A2 사전 정찰 패턴의 가치를 정량 입증**한 사례다 — 사용자가 시각 검증을
별도로 보고할 필요 없이 자율 사이클(A1·A2)로 7건 결함을 사전 차단했고, 시각 검증 사이클
자체에서 0건 발견은 사전 정찰이 충분히 catch-up 했음을 의미.

### 결함 #14 (2026-05-21): A2 CRITICAL 정리 — 5건 일괄 발견·fix

A2(CRITICAL drift 정리) 사이클에서 추가로 발견된 init/method 누락 5건.

| # | attr | 카테고리 | 외부 호출 site | fix |
|---|---|---|---|---|
| 14a | `self.dbreader` | B (DB helper) | `etcetera/etc.py:145`, `etcetera/load_database.py:23`, `event_activate/activated_back.py:23` | DatabaseReadOnly() 인스턴스 부착 |
| 14b | `self.window_closing` | A (boolean state) | `set_widget.py:1066` | _init_runtime_state에 False 추가 |
| 14c | `self.move_dialog_list` | A (list state) | `etcetera/etc.py:4` | _init_runtime_state에 [] 추가 |
| 14d | `self.location_list` | A (list state) | `set_widget.py:1110-1112` | _init_runtime_state에 [] 추가 |
| 14e | `self.setting_serial_save`, `self.web_dashboard_log`, `self.dialog_stg_input` | D (method/widget) | `set_setup_tap.py:201`, `button_clicked_shortcut.py:253`, `button_clicked_stg_module.py:136` | stub method + self placeholder |

**도구 보강** (재발 방지 강화):
- `_WIDGET_SUFFIX_RE`에 `_lineEdittt`/`_lineEditttt`/`_Button_`/`_groupBox` 추가 (45개 위젯 noise 정리)
- `_QT_INTERNAL`에 setFixedSize/winId/main_window 추가
- `_MODULE_NAMESPACES` 신규 (etcetera/event_*/set_style 등 6개 namespace)
- `extract_self_attrs`에 setattr() + 클래스 메서드 def 패턴 추출 추가

**baseline**: 68 → **0** (CRITICAL drift)
**회귀 테스트 strict 모드**: `_CRITICAL_BASELINE_MAX = 0`으로 강화 → 향후 외부 코드 변경 시 즉시 fail

### 결함 #13 (2026-05-20): WebCrawling.run() main exit 시 OSError("handle is closed") 누출

- 카테고리: B 보조 (worker lifecycle cleanup) — 결함 #10의 잔여 부분
- 발견 경로: 사이클 5 시각 검증 후 stom.py 종료 시 stderr Traceback
- 증상: process_kill의 webc.quit() + wait(500ms)이 webc.run()의 `webcQ.empty()` block에서
  타임아웃. main exit 시 multiprocessing.Queue 핸들 closed → `OSError("handle is closed")`
  webc thread에서 raise → stderr traceback. main process는 정상 종료되지만 cosmetic noise.
- 외부 호출 site: `utility/sub_process_and_thread/webcrawling.py:56` `if not self.webcQ.empty():`
- V3 source 수정 금지 invariant 유지하면서 fix:
  V3U `_init_workers`에서 WebCrawling.run을 monkey-patch — `_safe_webc_run_wrapper`로
  감싸 `OSError("handle is closed")`와 `OSError("WinError 6")`만 swallow, 다른 OSError는 raise
- 회귀 테스트: `tests/v3u/test_smoke.py::test_safe_webc_run_wrapper_swallows_handle_closed`
- 근본 원인 매핑: §3-2 (2U는 webc.stop() 패턴이 있지만 V3 WebCrawling은 stop 메서드 없음)
- 재발 방지 액션 매핑: 추가 액션 §5-6 후보 — worker subclass wrapping 패턴 (필요 시 §5에 정식 추가)

### 결함 #11 (2026-05-20): `ui.telegram` attr 미부착 → isRunning() AttributeError 위험

- 카테고리: D (helper inventory) + B (worker 시작)
- 발견 경로: 사이클 5 A1 사전 정찰 (외부 ref grep)
- 외부 호출 site: `ui/etcetera/etc.py:79` `if ui.telegram.isRunning():`
- 우리 누락 위치: `_init_workers`에서 telegram attr 자체가 없음
- 수정: TelegramBot(qlist, dict_set) 인스턴스화 + start. 자격증명 없으면 봇 run_forever만 (telegram_bot.py:65 자체 가드)
- 회귀 테스트: `tests/v3u/test_smoke.py::test_telegram_worker_attached_for_isRunning_call`
- 근본 원인 매핑: §3-2, §3-5
- 재발 방지 액션 매핑: §5-1·§5-2(이미 적용, 사이클 5 사전 정찰이 이걸 추가로 잡음)

### 결함 #12 (2026-05-20): `ui.proc_chqs` None placeholder → is_alive() AttributeError

- 카테고리: B (worker placeholder 부재)
- 발견 경로: 사이클 5 A1 사전 정찰 (외부 ref grep)
- 외부 호출 site: `ui/etcetera/etc.py:77`, `ui/event_click/button_clicked_database.py:14/32/50/68/86/105/124/138/152/171`,
  `button_clicked_backtest_start.py:582`, `button_clicked_chart.py:129`, `button_clicked_etc.py:190/281`,
  `button_clicked_formula.py:105/115`, `button_clicked_passticks.py:49`, `button_clicked_settings.py:273/315`
  → 총 20+ site에서 None 체크 없이 `ui.proc_chqs.is_alive()` 호출
- 우리 누락 위치: `_init_workers`에서 proc_chqs를 None placeholder로 둠 → `None.is_alive()` AttributeError
- 수정: `_NullProcess()` 클래스 신규 (`is_alive() → False`, terminate/join/start/pid/poll 인터페이스),
  proc_chqs와 proc_tele 둘 다 _NullProcess() 인스턴스 부착
- 회귀 테스트: `tests/v3u/test_smoke.py::test_proc_chqs_safe_for_is_alive_call`
- 잔여 의무: V3 pyd가 실제로 어떻게 ChartHogaQuery를 spawn하는지 V3.X 흡수 시 reactive 학습 후 진짜 Process로 교체
- 근본 원인 매핑: §3-1 (pyd 내부 spawn 메커니즘 미관찰), §3-2 (2U 패턴은 ChartHogaQuerySound callable이라 V3 직접 적용 불가)
- 재발 방지 액션 매핑: §5-1·§5-2

### 결함 #10 (2026-05-16): closeEvent + process_kill 누락 → 종료 시 OSError

- 카테고리: B (worker startup의 짝, lifecycle cleanup)
- 발견 경로: 사용자 stom.py 종료 후 stderr Traceback
- 외부 호출 site: `ui/event_keypress/overwrite_event_filter.py:266` `ui.process_kill()`,
  `ui/event_click/button_clicked_backtest_start.py:514` `QTimer.singleShot(180*1000, ui.process_kill)`
- 우리 누락 위치: `ui/main_window.py`에 `closeEvent`/`process_kill` 메서드 자체가 없음
- 증상: WebCrawling.run()의 while 루프가 main 프로세스 종료 시점에도 계속 동작 →
  multiprocessing.Queue.empty() 호출 중 핸들 invalid → `OSError [WinError 6]
  핸들이 잘못되었습니다`. pytest fixture teardown에서도 동일 access violation.
- 수정 커밋: (본 사이클)
- 회귀 테스트: `tests/v3u/test_smoke.py::test_process_kill_method_present`,
  `test_process_kill_stops_timers_only`
- 부수 결함: pytest 환경에서 V3 close_event가 QMessageBox.question modal을 띄우며
  access violation 유발. conftest의 main_window fixture가 `mw.close()` 대신
  `process_kill() + hide() + deleteLater()`로 우회. `STOM_V3U_DISABLE_WEBC=1`
  env var 추가로 pytest에서 webc start 자체를 건너뜀.
- 근본 원인 매핑: §3-2 (2U process_kill 패턴 미반영), §3-5 (worker lifecycle wiring 누락)
- 재발 방지 액션 매핑: §5-1 (2U lifecycle pattern import 필요)

---

## 7. 통계 (지속 갱신)

| 측정 | 값 (2026-06-11 사이클 15 V3.30~32 흡수 시점; 3U_C lane 항목은 사이클 9 시점 수치) |
|---|---|
| 총 발견 결함 (V3U lane) | 20 + #12 잔여 완결(A5) + 게이트 사전 차단 1건(homepg, 사이클 15) |
| 자동 회귀 테스트 추가 (V3U lane) | 23 |
| pytest 케이스 (V3U lane) | 49 |
| 수정 커밋 누적 (V3U lane) | 17 (V3.30~32 흡수 3 + 기록 1 포함) |
| 신규 자동 도구 (V3U lane) | 1 (attr_inventory_diff) + A3 verifier UX 분리 |
| **3U_C lane 추가 자동 도구** | **1** (v3uc_ingest_pipeline 5 T-step) |
| **3U_C lane 추가 회귀 테스트** | **4** |
| **3U_C lane commit** | **2** (ebd9a8f3, 9f565c3d) |
| **3U_C lane 신규 docs** | **3** (V3U_C_INGEST_PIPELINE/INFERENCE_LESSONS/NEXT_STEPS) |
| 사용자 시각 검증 사이클 | 6회 |
| **활성 워크트리** | 6 |
| **활성 lane branch** | 6 |
| 평균 결함 발견·수정 사이클 시간 | 약 25분 |
| 근본 원인 카테고리 | 5 (§3) |
| 재발 방지 액션 | 5 (§5) — **적용 5, 미적용 0** |
| CRITICAL drift baseline | **0** (strict 모드 유지) |
| A1 사전 정찰 효과 | 사용자 거래/DB 클릭 시 발견될 결함 2건 사전 차단 |
| A2 CRITICAL 정리 효과 | 추가 5건 사전 차단 + filter 보강으로 노이즈 67→0 |
| **사이클 6 효과 검증** | **OSError traceback 0건, 사용자 결함 보고 0건 — A1·A2 가치 정량 입증** |

---

## 8. 운영 규칙 (CLAUDE.md와 동기화)

### 8.1 새 결함 발견 시 4단계 워크플로우

1. **발견·진단**: 사용자 보고 또는 자동 검증 fail
2. **수정**: V3U 전용 파일에서만 (V3 official source 0줄 수정)
3. **회귀 테스트 추가**: 동일 결함이 다시 발생하지 않도록 `tests/v3u/`에 케이스 추가
4. **본 문서 갱신**: §6에 결함 기록 추가, §7 통계 갱신, 패턴 반복되면 §5 재발 방지 액션 갱신

이 4단계는 **모든 V3U 결함 수정 사이클의 표준 절차**다. 빠뜨리면 lessons learned가 휘발된다.

### 8.2 V3 정규 업데이트 흡수 시

- `git merge STOM_Version_3` → `STOM_Version_3U` 후 통합 게이트 실행
- `verify_v3u_pyd_gui_contract.py` PASS여도 사용자 1순위 시각 검증 필수
- 새 결함 발견 시 §8.1 4단계 워크플로우 적용

### 8.3 본 문서가 진실의 원천

V3U lane의 결함 이력·근본 원인·재발 방지 액션의 **유일한 진실 원천**이다. 다른 update_log 문서는 단발 사건 기록이지만 본 문서는 **lane이 끝날 때까지 갱신되는 누적 학습 기록**이다.

---

## 9. 관련 문서

- `docs/V3U_NEXT_STEPS.md` 미래 결정 진실 원천 (옵션 카탈로그 + 선택 이력)
- `docs/V3U_TRANSITION_AUDIT_2026-05-22.md` 3U_C 생성 전 중간 점검 v1 (lane 상태 종합 + 다른 워크트리 영향 + 2U_C 컨셉 흡수 가능성)
- `docs/V3U_PYD_REMOVAL_PLAN.md` §11 자동 검증 시스템 extension
- `docs/V3U_TEST_AUTOMATION_GUIDE.md` 운영 매뉴얼
- `docs/WORKTREE_STRATEGY.md` V3 Lane Branch Parity Invariants
- `docs/UPSTREAM_SYNC_STRATEGY.md` V3 Ingress Policy
- `docs/CARRY_FORWARD_REGISTRY.md` V3U custom allowlist rule
- `CLAUDE.md` V3U Test Automation Gate
- `.omc/plans/2026-05-12_v3u_test_automation_and_governance.md` 컨센서스 플랜
- `tests/v3u/README.md` 테스트 운영자 빠른 참조
- `docs/update_log/2026-05-12_v3u_test_automation_setup.md` 자동 검증 시스템 도입 감사
