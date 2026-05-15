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

### 액션 1: 2U attr 명세를 V3U init 출발점으로 시스템화 ⏳ **미적용**

**목표**: 2U `ui_mainwindow.py`의 156개 init attr을 자동 추출하고, V3 컨벤션 mapping 후 V3U-specific 차이만 명시한다. 우리 init이 빠뜨린 게 있으면 회귀 테스트로 자동 fail.

**구현 후보**:
- `scripts/v3u_attr_inventory_diff.py` 신규
- `tests/v3u/test_attr_inventory_drift.py` 신규
- 2U attr → V3 expected attr mapping JSON

**진행 상태**: 미시작. 별도 ralplan(옵션 G)으로 분리 가능.

### 액션 2: 외부 ui.X.Y 호출 자동 inventory + cross-check ⏳ **미적용**

**목표**: AST grep으로 외부 모든 `ui.*` 참조 추출 → 우리 init한 attr과 자동 diff → 회귀 테스트.

**구현 후보**:
- `scripts/v3u_external_ref_inventory.py` 신규
- `tests/v3u/test_external_ref_match.py` 신규

**진행 상태**: 미시작.

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

---

## 7. 통계 (지속 갱신)

| 측정 | 값 (2026-05-12 11:30 시점) |
|---|---|
| 총 발견 결함 | 9 |
| 자동 회귀 테스트 추가 | 11 (사이클 1 추가분 4 + 갱신 2 + 신규 5) |
| pytest 케이스 총수 | 37 |
| 수정 커밋 누적 | 3 (72308bca, b72f0162, 25f61980) |
| 사용자 시각 검증 사이클 | 3회 |
| 평균 결함 발견·수정 사이클 시간 | 약 25분 |
| 근본 원인 카테고리 | 5 (§3) |
| 재발 방지 액션 | 5 (§5) — 적용 3, 미적용 2 |

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

- `docs/V3U_PYD_REMOVAL_PLAN.md` §11 자동 검증 시스템 extension
- `docs/V3U_TEST_AUTOMATION_GUIDE.md` 운영 매뉴얼
- `docs/WORKTREE_STRATEGY.md` V3 Lane Branch Parity Invariants
- `docs/UPSTREAM_SYNC_STRATEGY.md` V3 Ingress Policy
- `docs/CARRY_FORWARD_REGISTRY.md` V3U custom allowlist rule
- `CLAUDE.md` V3U Test Automation Gate
- `.omc/plans/2026-05-12_v3u_test_automation_and_governance.md` 컨센서스 플랜
- `tests/v3u/README.md` 테스트 운영자 빠른 참조
- `docs/update_log/2026-05-12_v3u_test_automation_setup.md` 자동 검증 시스템 도입 감사
