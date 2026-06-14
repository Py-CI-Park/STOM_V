# V3U Next Steps Decision Tree (지속 관리 문서)

- 최초 작성: 2026-05-20 (사이클 5 시점)
- 본 문서 정책: **사이클 마무리 시 §3 옵션 + §5 선택 이력 갱신 의무**
- 갱신 주기: 매 사이클 종료 시 또는 옵션 추가/제거 발생 시
- 관련 진실 원천: `docs/V3U_INFERENCE_LESSONS.md` (결함 기록), `CLAUDE.md` (운영 규칙)

---

## 1. 본 문서의 목적

V3U lane 진행 중 매 사이클 종료 시점에 **다음 사이클의 옵션을 정렬하고 우선순위를 평가**한다. 사용자/Claude가 결정 시점에 동일한 옵션 집합을 일관되게 마주하도록 영구 기록한다.

`docs/V3U_INFERENCE_LESSONS.md`가 **과거(결함 기록·근본 원인·재발 방지)**라면, 본 문서는 **미래(다음 사이클의 가능한 액션·우선순위·선택 이력)**를 다룬다.

---

## 2. 현재 사이클 상태 (사이클 15, 2026-06-11)

| 지표 | 값 |
|---|---|
| 결함 누적 (LESSONS.md §7) | 20 + #12 잔여 완결(A5) + 게이트 사전 차단 1건(homepg) |
| 자동 회귀 테스트 (pytest tests/v3u) | 49 |
| 신규 자동 도구 | 1 (`scripts/v3u_attr_inventory_diff.py`) + A3 verifier 8 stage UX |
| 수정 커밋 누적 | 17 (V3.30~32 흡수 3 + 기록 포함) |
| 재발 방지 액션 | 5/5 적용 + §5-2 read-before-write 한계 기록 (보강 옵션 A7) |
| CRITICAL drift baseline | 0 (strict 모드) — V3.32 흡수에서 첫 실전 차단 입증 |
| 사용자 시각 검증 사이클 | 7회 (사이클 15 B1: V3.32 + #16 + A5 + TTS 동시 검증, 결함 0건) |
| V3 lane 버전 | V3.32 (`3dea3b94`, tail `fcc626a5` 1건 차기 흡수 예정) |
| stom.py 활성 상태 | 사이클 15 B1 정상 종료 (2026-06-11, traceback 0건·exit 0) |

### 미해결 사용자 잔여 작업 (선행 핸드오프 §3 기준)

| 영역 | 항목 | 사이클 5 시점 상태 |
|---|---|---|
| 1순위 | 메인창 + 9개 탭 + strategy 아이콘 | 사용자 시각 검증 진행 중 |
| 2순위 | 백테 1회 + 차트 zoom/pan + 변손익분석 | 사이클 5에서 진행 가능 |
| 3순위 | DB 마이그레이션 (D1) | 사용자 백업 DB 필요 |
| 4순위 | 실거래 (C1~C4·B3) | release 전 사용자 필수 |
| 결정 | `STOM_Version_3U_C` 생성 (F1), V3 upstream V3.0 reconcile (E1·E2) | 1·2순위 PASS 후 사용자 결정 |

---

## 3. 옵션 카탈로그 (우선순위 그룹별)

### 그룹 A — Claude 자율 진행 가능 (사용자 시각 검증 부담 사전 감소)

#### A1: 카테고리 B/C/D 사전 정찰 (30~60분)
LESSONS.md §4 예측 결함 후보를 사용자가 클릭하기 전 사전 점검·fix.

| 카테고리 | 후보 worker/attr |
|---|---|
| B (worker 누락) | `proc_chqs` (ChartHogaQuery 프로세스), `proc_tele` (TelegramBot QThread), `KimpWebSocketManager`, `PyttsxSound` |
| C (signal connect 누락) | TelegramBot.signal, KimpWebSocketManager.signal 등 |
| D (helper 이름 mismatch) | `update_widget`, 기타 미부착 helper |

**ROI**: 사용자 추가 시각 사이클 1~2회 사전 차단.

#### A2: CRITICAL drift 68 → 0 정리 (1~2시간)
`scripts/v3u_attr_inventory_diff.py`의 68개 CRITICAL을 분류·해결.
- 실 결함 → `_init_runtime_state`/`_init_workers`에 추가
- noise(위젯 등) → filter 패턴 보강
- baseline 점진 감소 → 회귀 안전망 강화

**ROI**: 차후 외부 코드 변경 시 더 정확한 자동 fail.

#### A3: contract verifier 단계 분리 (30분)
현재 pytest gate가 attr inventory를 포함하지만 명시적으로 분리해 verifier 출력에 "attr inventory: PASS/FAIL" 라인 추가.

**ROI**: V3 흡수 시 verifier 출력만 봐도 단계별 PASS 여부 즉시 파악.

#### A4: stom.py 종료 cleanup 추가 보강 (30분)
`process_kill`이 현재 timer + webc만 정리. proc_chqs/proc_tele 추가 시 동일 cleanup 추가 필요.

**ROI**: A1 진행 시 자연스럽게 함께 처리됨.

#### A5: proc_chqs(ChartHogaQuery) 실 spawn ✅ **완료 (사이클 14, 2026-06-11)**
2U 선례(`wt-2u/ui/ui_mainwindow.py:344`)는 부팅 시 `Process(target=..., args=(qlist, dict_set), daemon=True)` 직접 spawn. V3에 동일 계약 `ChartHogaQuery(qlist, dict_set)` 존재(`utility/sub_process_and_thread/chart_hoga_query.py:25`), pyd import 목록(`import_hook.py:25`)에도 등재. 현재 `_NullProcess` 영구 placeholder → queryQ 소비자 부재 → **DB관리 탭 버튼 10개 전면 무반응 + 차트/호가 조회 + 설정 저장 반영 + 전략에디터/GA/옵튜나 등 가드 47곳 비활성**.

**ROI**: pyd 기능 최대 미달점 해소. 결함 #12 잔여 의무 완결.
**적용 결과 (사이클 14)**: `_init_workers` spawn + `process_kill` terminate cleanup(proc_chqs 분 A6 선반영) + conftest `STOM_V3U_DISABLE_CHQS=1` + spawn 계약 회귀 테스트. 실 child 동작은 B1 시각 검증 필요.

#### A6: process_kill 종료 범위 보강 (2U 선례)
2U `ui/ui_process_kill.py` 선례: 다이얼로그 23종 close + 백테 프로세스 26종 terminate/join + 트레이드 프로세스 정리. V3 공식 소스의 트레이드 프로세스는 non-daemon(`button_clicked_shortcut.py:203-214`) → 거래/백테 중 종료 시 zombie/hang 위험.

**ROI**: 종료 안정성. A5 진행 시 proc_chqs cleanup도 함께 (A4 통합).

#### A7: attr inventory read-before-write 감지 보강
결함 #16의 자동망 회피 경로 차단. `ui.X =` 외부 할당을 '커버됨'으로 분류하는 현 로직에, 같은 파일에서 할당보다 앞서 읽는 site 또는 runtime 디렉토리 전용 할당을 분리 분류하는 휴리스틱 추가. WARN 신설 시 strict 게이트 영향 검토 필요.

**ROI**: 카테고리 A 회귀의 V3.X 흡수 시 자동 차단.

#### A8: allowlist 정합성 (거버넌스)
직접 tree diff에서 allowlist 외 경로 2건(`ui/create_widget/set_style.py` +1줄 color_hv_bt, `utility/db_control/database_check.py` 상수 노출)이 금지 경로에 존재하나 update_log 사유만 있고 ① CARRY_FORWARD_REGISTRY allowlist 미등재 ② PLAN §5.2 조건부 허용 양식 미작성 ③ 통합 게이트가 allowlist diff를 실제 검사하지 않음(위반 상태 8/8 PASS).

**ROI**: CLAUDE.md "위반 시 게이트 자동 fail" 문구와 실제 게이트 동작 일치화.

### 그룹 B — 사용자 시각 검증 reactive (Claude 4단계 워크플로우 자동 적용)

#### B1: 사이클 5 결과 보고 + 결함 fix
stom.py 떠있는 상태에서 사용자 보고:
- ✅ 정상 → 사이클 5 종료 (LESSONS.md §6에 "추가 결함 없음" 기록)
- ⚠️ 결함 발견 → 즉시 4단계 워크플로우 (발견→수정→회귀→문서)

**ROI**: 사용자 능동 검증으로만 잡히는 실 결함 해소.

### 그룹 C — 사용자 환경 의존 (Claude 보조 가능)

#### C1: 3순위 DB 마이그레이션 (D1)
사용자가 백업 DB 경로 제공 시 Claude가 dry-run 보조.

**필요 정보**: 백업 DB 파일 경로 또는 사본.

#### C2: 4순위 실거래 (C1~C4·B3)
사용자 자격증명·실 자금·라이브 시장 필수. Claude는 mock 단위 테스트만 가능.

**필요 환경**: LS 모의투자 / 바이낸스 테스트넷 / 업비트 실 최소금액.

### 그룹 E — V3U_C custom 작업 (3U_C 생성 후, 사용자 선택)

3U_C 생성 후 사용 가능한 custom 기능 도입 후보. V3U_TRANSITION_AUDIT_2026-05-22.md §6.3 참조.

#### E1: V3.X 흡수 자동화 파이프라인
2U_C T-step 패턴으로 V3.19 흡수 단계 분해 (T01 branch merge → T02 verifier → T03 audit 정본화 → T04 한글 commit → T05 push). mock execution + live dry-run.

**ROI**: 매 V3.X 흡수가 명시적 게이트 시퀀스로 자동 진행. 사용자 개입 최소화.

#### E2: STOM_CLI 자동화 + V3U 통합
2U_C `STOM_CLI_AI_AUTOMATION_PLAN.md` 패턴 참고. V3U_C에 CLI 단축키 + 자동화 시나리오 추가.

**ROI**: 자주 쓰는 V3U 동작 (테스트 실행·verifier·debug)을 단축키로 즉시 호출.

#### E3: 실시간 모니터링 dashboard
`ui.web_dashboard` 인스턴스 적극 활용. 별도 worker로 자체 web dashboard server. 2U_C 사이드카 승인 패턴.

**ROI**: 운영 중 lane 상태 (큐 길이·worker 상태·결함 카운트)를 브라우저로 모니터.

#### E4: 고급 백테 자동화
2U_C V3K mapping 지도 참고. V3U_C에 백테 결과 자동 분석 + GA + Optuna 자동 ranking.

**ROI**: 백테 결과 분석·전략 최적화 워크플로우 자동화.

### 그룹 D — 정책 판단 (사용자만)

#### D1: `STOM_Version_3U_C` 생성 시점 결정
선행 Directive(`4aef1cce`)로 보류 중. 1·2순위 시각 검증 PASS 후 사용자 결정.

#### D2: V3 upstream V3.0 reconcile (E1·E2)
V3 wave 시작 시 별도 결정. 현재 V2.79 웨이브 정책상 동기화 의무 없음.

#### D3: V3.19 흡수 시점
V3 upstream 새 버전 발표 시 통합 게이트 자동 실행 후 사용자 승인.

---

## 4. 우선순위 추천 매트릭스

| 우선순위 | 옵션 | 사유 |
|---|---|---|
| 🟢 1 | B1 (사용자 직접 테스트) | V3.29 흡수 + #16 fix + A5 proc_chqs spawn 이후 시각 검증 0회 — DB관리 탭·차트/호가·MEM/NET 게이지 활성 확인 |
| 🟡 2 | A6 (process_kill 잔여 보강) | 트레이드/백테 프로세스 종료 (proc_chqs 분은 A5에서 선반영) |
| 🟡 3 | A7 (도구 read-before-write) | 결함 #16 패턴 자동 차단 |
| ⚪ 4 | A8 (allowlist 정합성) | 기능 영향 없음, 거버넌스 일치화 |
| 🔵 5 | C1 (DB 검증) → C2 (실거래) | release 전 사용자 |
| ⚪ 6 | D1·D2·D3 (정책 결정) | 정량 측정 불가, 사용자 판단 |

**Default 권장 흐름**: B1 → A6 → A7 → A8 → C1 → C2 → D1
(완료 이력: A1·A2 사이클 5·6, A3·A4 사이클 7, A5 사이클 14)

---

## 5. 선택 이력 (지속 갱신 — 사이클 종료 시 추가)

각 사이클 종료 시 다음 형식으로 기록.

```
### 사이클 N (YYYY-MM-DD): 선택 옵션 / 결과 요약

- 사용자 선택: <옵션 ID>
- 실행 결과: <commit hash, pytest 케이스 변화, 결함 N건 fix>
- 발견 신규 결함: <카테고리·#번호 또는 "없음">
- LESSONS.md 갱신: <§6·§7 변경 요약>
- 다음 사이클 후보: <다음 우선순위 옵션>
```

### 사이클 1~4 (2026-05-12): V3U pyd 추론 발견·수정 사이클

- 사용자 선택: (사이클 1·2·3 시각 검증으로 결함 9건 발견, 사이클 4 종료 후 OSError로 결함 #10 발견)
- 실행 결과: 13 한글 커밋(`e01a96bf..03293c29`) + 39 pytest 케이스 + LESSONS.md §1~9 신규 작성
- 발견 신규 결함: A(2), B(1), C(1), D(2), 기타(4) = 총 10건
- 다음 사이클 후보: A1·A2 사전 정찰 + 시각 검증 사이클 5

### 사이클 5 (2026-05-20): §5-1·§5-2 시스템화 + A1 사전 정찰 + 시각 검증 진행 중

- 사용자 선택: "권장 흐름 진행" → 1순위 시각 검증 + 2순위 자율 §5 적용 → "A1 진행"
- 실행 결과:
  - 14번째 커밋(`1116540a`) §5-1·§5-2 시스템화
  - 15번째 커밋(`0d6eb498`) NEXT_STEPS 신규
  - 16번째 커밋(본 사이클) A1 사전 정찰 결함 #11·#12 fix
  - 44 pytest 케이스 (사이클 시작 39 → §5 추가 3 → A1 추가 2)
- 발견 신규 결함: A1 사전 정찰 2건 + 시각 검증 종료 reactive 1건
  - #11 ui.telegram 미부착 (B+D 카테고리)
  - #12 ui.proc_chqs None placeholder (B 카테고리)
  - #13 WebCrawling.run() OSError("handle is closed") main exit 누출 — 결함 #10 잔여
- LESSONS.md 갱신: §6 결함 #11·#12·#13 + §7 통계 (45/19/7/baseline 68, 결함 13건)
- 다음 사이클 후보: A2 (CRITICAL 정리) 또는 C1 (DB 검증)

### 사이클 6 (2026-05-21): A2 CRITICAL drift 0 달성

- 사용자 선택: "A2 진행"
- 실행 결과:
  - 18번째 커밋(`0eba2a71`) CRITICAL 67 → 0
  - 도구 보강 4건: filter 패턴 강화 (_lineEdittt/_Button_/_groupBox), Qt internal 추가,
    모듈 namespace 카테고리, setattr/메서드 def 추출 추가
  - 실 결함 5건 fix: dbreader, window_closing, move_dialog_list, location_list,
    stub method 3개(setting_serial_save/web_dashboard_log/dialog_stg_input)
- 발견 신규 결함: A2에서 5건 (#14a~e 통합)
- LESSONS.md 갱신: §6 결함 #14 통합 항목 + §7 통계 (45/19/8/baseline **0**, 결함 18건)
- 회귀 테스트 strict 모드: `_CRITICAL_BASELINE_MAX = 0` → 새 외부 ui.X 참조 즉시 fail
- 다음 사이클 후보: 사용자 시각 검증 reactive (fix #13/#14 효과 확인) 또는 C1 (DB 검증)

### 사이클 17 (2026-06-13): V3.33 흡수 (V3.32 tail fcc626a5 포함)

- 사용자 선택: "흡수 진행해" (V3.33 신규 발표 흡수)
- 실행 결과:
  - wt-3 formal `32991b24` (V3.33, V3.32 tail fcc626a5 포함) — parity 일치
  - wt-3u pyd-free `3a1c1a93`, 통합 게이트 8/8 PASS (pytest 49, attr critical=0)
  - V3U 보정 0건 (순수 overlay) — 신규 파일 2개(bstart.py/famous_saying.py)는
    기존 attr만 참조, 게이트가 market_infos false alarm 확정
- 발견 신규 결함: 0건
- lane 버전: V3.32 → **V3.33**, tail 잔여 0
- 상세: docs/update_log/2026-06-13_v3u_v333_pyd_free_update.md
- 다음: 3U_C `git merge STOM_Version_3U`로 따라잡기 (사이클 18 cross-link)

### 사이클 16 (2026-06-13): 3U_C lane V3.19~V3.32 흡수 (cross-link)

- 사용자 선택: "A 진행" (3U_C를 V3U lane으로 따라잡기)
- 실행 위치: wt-3uc (STOM_Version_3U_C) — 3U_C lane 사이클 5
- 방식: `git merge --no-ff STOM_Version_3U` (merge `32900141`), lane V3.18 → V3.32
- 결과: 통합 게이트 8/8 PASS (pytest 49) + tests/v3uc 32, 충돌 0, invariant 만족
- V3U lane 영향: 0건 (3U_C 단방향 흡수, V3U 안전망 그대로 상속)
- 상세 진실 원천: 3U_C `docs/V3U_C_NEXT_STEPS.md` §5 사이클 5 +
  `docs/update_log/2026-06-13_v3uc_v319_v332_absorption.md`
- 명문화: V3공식→V3U는 overlay/E1, V3U→3U_C는 git merge (hop별 메커니즘 구분)

### 사이클 15 (2026-06-11): 업스트림 신선도 점검 + V3.30~V3.32 흡수 + 2U_C 백포트 검토

- 사용자 선택: "공식 업데이트 업스트림 확인 + version별 업데이트 + 3U 추가 흡수 분석 + 2U_C 반영 상세 검토 커밋 (검토 문서 stom_v/wt-3u 동시 커밋)"
- 실행 결과:
  - V2 lane: upstream tag V2.0 == 로컬 V2.79 → 반영 없음
  - V3 freshness 권원 정정: `refs/tags/V3.0` stale → `refs/heads/V3.00` (tip fcc626a5, V3.32)
  - wt-3 formal: `a488af5d`(V3.30) `b9cdcd99`(V3.31) `3dea3b94`(V3.32), parity 검증 통과
  - V3U 흡수: `9459a422`/`83be2de0`/`1da630da`, 버전별 게이트 8/8 PASS
  - **게이트 첫 실전 차단**: V3.32 신규 계약 `ui.homepg` CRITICAL drift 자동 검출 → 보정
  - TTS 실 worker 전환 (supertonic 삭제로 placeholder 사유 소멸) + 회귀 테스트 → pytest 49
  - 2U_C 백포트 검토: 후보 10항목 판정 (1순위: 업비트 첫틱 당일매수/매도금액 수정),
    공용 검토 문서 STOM_V/wt-3u 동시 커밋
- 발견 신규 결함: 0건 (게이트 사전 차단 1건은 커밋 전 해소)
- LESSONS.md 갱신: 사이클 15 절 + §7 통계 (23/49/17)
- **B1 시각 검증 종결 (2026-06-11)**: 사용자 "모두 정상 확인" — 부팅/종료 로그 클린
  + MEM/NET 게이지·DB관리 탭·홈탭 마우스오버·읽기속도 음성 전 항목 정상, 결함 0건.
  UPSTREAM_SYNC_STRATEGY.md V3 권원도 refs/heads/V3.00으로 갱신 (후속 권고 §4-4 이행)
- 다음 사이클 후보: V3.33 발표 시 tail `fcc626a5` 포함 흡수 (E1 ingest CLI 첫 실 사용 후보),
  2U_C 백포트 사이클 (기능 브랜치 정리 후, 1순위 업비트 첫틱), A6/A7/A8 자율 작업

### 사이클 14 (2026-06-11): A5 proc_chqs ChartHogaQuery 실 spawn — 결함 #12 잔여 완결

- 사용자 선택: "push 하고 A5 진행"
- 실행 결과:
  - 사이클 13 commit `828f8a02` origin push 완료
  - `_init_workers`에 `Process(target=ChartHogaQuery, args=(qlist, dict_set), daemon=True)`
    spawn (2U 선례 `wt-2u/ui/ui_mainwindow.py:344` 동일 패턴)
  - `process_kill`에 proc_chqs terminate/join cleanup (A6의 proc_chqs 분 선반영)
  - conftest `STOM_V3U_DISABLE_CHQS=1` (pytest 실 child spawn 방지)
  - 회귀 테스트 +1: `test_chart_hoga_query_spawn_contract` → pytest 48 케이스
- 발견 신규 결함: 0건 (기존 공백 해소 작업)
- LESSONS.md 갱신: §6 "A5 적용" 절 + §7 통계 (회귀 22 / pytest 48 / 커밋 13)
- 다음 사이클 후보: **B1 사용자 직접 테스트 최우선** (V3.29 + #16 + A5 효과 통합 확인:
  DB관리 탭 버튼 반응, 차트/호가 조회, MEM/NET 게이지, 종료 로그 proc_chqs 종료 OK)

### 사이클 13 (2026-06-11): pyd→py 추론 전면 재검증 + 결함 #16 4단계 수정

- 사용자 선택: "pyd→py 추론 반영 재검증 검토" → "결함 #16 4단계 워크플로우로 수정 진행"
- 실행 결과:
  - 재검증: 통합 게이트 8/8 PASS 재확인 + 병렬 심층 감사 3종
    (이벤트 핸들러 278개 배선 PASS / upstream V3.19~V3.29 계약 커버리지 PASS /
    main_window.py stub·lifecycle 감사에서 신규 결함 1건 + 기능 공백 2건 확인)
  - 결함 #16 fix: `_init_runtime_state`에 last_recv/memory_per/net_recv 초기화 추가
  - 회귀 테스트 +1: `test_cpuper_network_stat_attrs_initialized` → pytest 47 케이스
- 발견 신규 결함: #16 (A 카테고리 3번째 반복, V3.24 흡수 회귀) — 통합 게이트 PASS
  상태에서 자동망 회피 (attr inventory read-before-write 맹점 + `__getattr__` 가림)
- 미해결 공백 옵션화: A5 (proc_chqs 미spawn — 가드 47곳 비활성), A6 (process_kill
  축소), A7 (도구 맹점 보강), A8 (allowlist 외 2파일 거버넌스 정합성)
- LESSONS.md 갱신: §6 결함 #16 + §5-2 한계 + §7 통계 (결함 20 / 회귀 21 / pytest 47 / 커밋 12)
- 다음 사이클 후보: A5(+A6) 최우선, 사용자 stom.py 직접 테스트 (V3.29 + #16 fix 효과 확인)

### 사이클 12 (2026-05-30): 3U_C lane E2 V3U/3U_C 통합 CLI 도입 + 백테 PK 분석

- 사용자 선택: "c 진행 ultracode" (E2/E3/E4 중 자율 선택 → E2 최우선 매트릭스 🟡2 선정)
- 실행 흐름 (Claude 자율):
  - 사전 분석: `back_static.py:108` `SELECT * FROM moneytop` 등 backtest는 순수 SELECT → moneytop·기타 DB PK 누락은 백테 차단 안 함 (`INSERT OR REPLACE`/`PRIMARY KEY` 0건 확인)
  - `scripts/v3uc_cli.py` 7 subcommand 작성 (status/verify/db scan|migrate/test/ingest/gui)
  - `tests/v3uc/test_cli.py` 16 케이스 작성 → 32 회귀 PASS
  - `docs/V3U_C_CLI_GUIDE.md` 운영 매뉴얼
  - V3U_C LESSONS 사이클 4 + 결함 #1·#2(3U_C-specific 도구 자체 결함) 기록
- 발견 신규 결함: 2건 (3U_C lane 자체 도구 — V3 official source 영향 없음)
  - #1 argparse `parents=` gotcha — subparser default가 부모 namespace를 None으로 덮어쓰는 known issue (해결: `default=argparse.SUPPRESS` + main()에서 getattr 정규화)
  - #2 Windows cp949 콘솔 utf-8 미설정 — em-dash(U+2014) 출력 시 UnicodeEncodeError (해결: 스크립트 헤드에서 `sys.stdout.reconfigure(encoding="utf-8")`)
- 백테 PK 분석 결과 (옵션 카탈로그 갱신 반영):
  - 기타 DB(backtest/code_info/setting/strategy/tradelist) PK 추가 작업은 **백테 사용 시점에는 불필요** — 실시간 수집(라이브 거래) 사용 시에만 의미
  - 우선순위 매트릭스에서 "기타 DB PK 도구" 우선순위 하향 (선제 작업 아님)
- LESSONS.md 갱신: 본 V3U LESSONS는 사이클 12 절만 추가, V3U_C LESSONS에 결함 상세
- NEXT_STEPS.md 갱신: 본 항목
- 다음 사이클 후보:
  - **사용자 stom.py 백테 시각 확인** (사이클 10·11 Step 6 누적, PK 차단 가능성 사전 검증으로 신뢰도 ↑)
  - E3 web_dashboard 활성화 또는 E4 백테 결과 자동 분석
  - V3.30+ 발표 시 `cli ingest --version V3.30 --dry-run`로 E1 첫 실 사용

### 사이클 11 (2026-05-23): 3U_C lane E7 strategy.db 조건식 V2→V3 마이그레이션

- 사용자 통찰: "조건식이 저장안되있어서 아직 못하지 않나요? 조건식을 v2 공식에서 복사해서 적절하게 v3 v3U에 맞게 들고와야 진행가능 하지 않나요?"
- 발견: V3U strategy.db에 V2 시절 stockbuy/stocksell 데이터 보존(51/35 rows)되어 있으나 V3 컨벤션(stock_buy 밑줄)으로 안 옮겨짐 → 백테 못 함
- 실행 흐름 (Claude 자율 도구 + 실 변환):
  - 3U_C E7 도구 작성 (87b6645b origin/STOM_Version_3U_C push)
  - V3U 실 strategy.db scan: 95 rows 마이그레이션 후보 발견
  - dry-run + 실 migrate: 95 rows 복사, 에러 0
  - post-verification: V2 == V3 == 95 ✅
- 발견 신규 결함: 0건 (사용자 통찰로 발견됐지만 도구 자체 결함은 아님 — 사용자 환경 마이그레이션 누락)
- LESSONS.md 갱신: 사이클 11 + V3 거래소별 prefix 패턴 정본화
- NEXT_STEPS.md 갱신: 본 항목
- 다음 사이클 후보:
  - **사용자 stom.py 백테 시각 확인** (사이클 10 Step 6과 통합)
  - 사용자가 V2에서 다른 거래소(coin/future/stock_etf) 조건식 만들었다면 --target 별도 호출
  - 기타 DB(backtest/code_info/setting) 마이그레이션 (E5 v2 또는 E8)

### 사이클 10 (2026-05-22~23): 3U_C lane E5 + A++ DB 마이그레이션 끝까지 자동 실행

- 사용자 선택: "위의 업무 내용 지금까지 조사 내용 먼저 문서로 아주 자세하게 남기고 한글로 아주 자세하개 commit 하고 A++ 진행"
- 실행 흐름 (Claude 자율 Step 1~5 + 사용자 Step 6 시각 1분):
  - Step 1: 3U_C에 진단 도구 + 종합 조사 문서 + 7 회귀 (c0c43958 push)
  - Step 2: 백업 1175 파일
  - Step 3: V2→V3 컬럼 변환 (1166 stock DB)
  - Step 4: PK 진단 (89,699 stock 테이블 미호환 발견)
  - Step 5: 88,534 PK 추가 (에러 0)
- 발견 신규 결함: 0건 (백업 안전망 + 단위 테스트 + dry-run 검증)
- LESSONS.md 갱신: 본 V3U LESSONS 사이클 10 + V3U_C LESSONS 사이클 2
- NEXT_STEPS.md 갱신: 본 항목
- 잔여:
  - **Step 6 사용자 시각 확인 1분** (python stom.py → 백테 라이브 → 시작 → 결과 화면)
  - 기타 DB(backtest/code_info/setting) PK 별도 사이클
- 다음 사이클 후보:
  - Step 6 결과 reactive (정상 PASS면 사이클 10 종료, 결함 발견 시 4단계 워크플로우)
  - 기타 DB PK 자동 추가 도구 확장 (E5 v2)
  - V3.19 발표 시 E1 실 dry-run

### 사이클 9 (2026-05-22): 3U_C lane E1 V3.X 흡수 자동화 파이프라인 도입

- 사용자 선택: "E1 진행" (V3U_C custom 작업 첫 사이클, 3U_C lane)
- 실행 위치: wt-3uc (STOM_Version_3U_C)
- 실행 결과:
  - origin/STOM_Version_3U_C에 2 commit 추가 (ebd9a8f3·9f565c3d)
  - scripts/v3uc_ingest_pipeline.py (5 T-step 흡수 자동화)
  - tests/v3uc/test_ingest_pipeline.py (4 unit 케이스 PASS)
  - docs/V3U_C_INGEST_PIPELINE.md (운영 매뉴얼)
  - docs/V3U_C_INFERENCE_LESSONS.md (3U_C 결함 진실 원천 신규)
  - docs/V3U_C_NEXT_STEPS.md (3U_C decision tree 신규)
  - CARRY_FORWARD_REGISTRY 사이클 1 항목 등록
- 발견 신규 결함 (V3U lane): 0건 (3U_C 신규 산출만)
- LESSONS.md 갱신: 본 V3U LESSONS에 사이클 9 절 + §7 통계 (3U_C lane 통계 분리 표기)
- NEXT_STEPS.md 갱신: 본 항목
- 본 commit은 V3U lane에 머무름 (3U_C 사이클 진행 기록만, 3U_C 산출은 origin/STOM_Version_3U_C에 별도)
- 다음 사이클 후보:
  - V3.19 발표 시 E1 실 dry-run + live 검증
  - 3U_C 그룹 E의 E2/E3/E4 중 선택
  - V3U lane 사용자 2순위 시각 검증 (백테 1회·차트·변손익분석)
  - C1 DB 마이그레이션 (사용자 백업 DB)

### 사이클 8 (2026-05-22): 3U_C 생성 Phase A·B 완료

- 사용자 선택: "A 진행" (V3U_TRANSITION_AUDIT §7 우선순위 4번, 3U_C 생성)
- 실행 결과:
  - 23번째 커밋(`2ba974f8`) Phase A 거버넌스 사전 작업 (docs 3개 갱신)
  - Phase B: STOM_Version_3U_C branch 생성 + wt-3uc 워크트리 + origin push
  - 24번째 커밋(본 사이클) LESSONS/NEXT_STEPS 사이클 8 기록
- 발견 신규 결함: 0건 (거버넌스 작업)
- 3U_C lane 사전 검증:
  - 3U vs 3U_C diff 비어있음 (invariant 유지)
  - 3U_C 워크트리 pytest collect 46 케이스 정상 (V3U 안전망 자동 상속)
  - origin/STOM_Version_3U_C remote push 완료
- LESSONS.md 갱신: §6 사이클 8 거버넌스 작업 절 + §7 통계 (46/20/11/baseline 0, 활성 워크트리 6)
- NEXT_STEPS.md 갱신: 본 항목
- 다음 사이클 후보: 그룹 E (V3U_C custom 작업 X1~X4 중 선택) — 사용자 결정 필요

### 사이클 7 (2026-05-22): A3 verifier UX 분리 + A4 web_dashboard placeholder

- 사용자 선택: "A 진행" (A3·A4 자율 묶음, 중간 점검 보고서 §7 우선순위 1번)
- 실행 결과:
  - 22번째 커밋(본 사이클) A3·A4 통합
  - A3: verify_v3u_pyd_gui_contract.py에 attr_inventory_diff 별도 단계 + 8 stage
    [PASS]/[FAIL]/[SKIP] 라인 출력 UX
  - A4: web_dashboard placeholder 부착 (결함 #15 사전 차단)
- 발견 신규 결함: A4에서 1건 (#15 web_dashboard)
- LESSONS.md 갱신: §6 결함 #15 + A3 보강 절 + §7 통계 (46/20/10/baseline 0, 결함 19건)
- NEXT_STEPS.md 갱신: 본 항목
- 다음 사이클 후보: 3U_C 생성 Phase A·B 또는 2순위 사용자 시각 검증 또는 다른 자율 작업

### 사이클 6-2 (2026-05-21): 시각 검증 — 결함 0건, A1·A2 가치 입증

- 사용자 선택: "시각 검증 사이클 6 진행"
- 실행 결과:
  - stom.py 부팅·시각 확인·종료 1 사이클 정상 완주
  - 부팅 로그 4 INFO (boot/telegram/signal connected/webc start) 모두 정상
  - 사용자 시각 검증 약 3분, 결함 보고 0건
  - 종료 로그 3 INFO (timers/telegram/webc graceful) + **OSError traceback 0건**
- 발견 신규 결함: 0건 (A1 +2 + A2 +5 + 직전 #13 fix가 모두 효과적이었음)
- LESSONS.md 갱신: 사이클 6 시각 검증 결과 절 추가 + §7 통계 (45/19/9/baseline 0, 결함 18건, 사이클 6회)
- 다음 사이클 후보:
  - C1 (사용자 백업 DB로 D1 검증)
  - 자율 작업: A4 추가 worker 사전 정찰 또는 contract verifier UX 개선
  - D1 (STOM_Version_3U_C 생성 시점 결정 — 1·2순위 시각 PASS 완료)
- NEXT_STEPS.md 갱신: 본 항목
- 다음 사이클 후보: A2 (CRITICAL 정리) 또는 C1 (DB 검증) 또는 사용자 다음 시각 사이클

---

## 6. 운영 규칙

### 6.1 사이클 종료 시점의 정의

다음 중 하나가 발생하면 사이클 종료로 간주하고 §5에 기록.
- 사용자가 명시적으로 "사이클 N 종료" 또는 "다음 단계 안내" 요청
- 한 사용자 시각 검증 + reactive fix 사이클이 자연스럽게 완료
- 자율 작업(그룹 A) 한 묶음이 commit·push까지 완료

### 6.2 본 문서 갱신 의무

각 사이클 종료 시 다음을 수행:
1. §2 현재 사이클 상태 표 숫자 갱신
2. §5 선택 이력에 본 사이클 항목 추가
3. §3 옵션 카탈로그에 신규 옵션 추가 또는 제거된 옵션 정리
4. §4 우선순위 매트릭스 재평가

### 6.3 cross-link 유지

다음 문서와 일관성 유지:
- `docs/V3U_INFERENCE_LESSONS.md` §7 통계와 본 문서 §2 통계 동기화
- `CLAUDE.md` "V3U Test Automation Gate" 4단계 워크플로우 참조

---

## 7. 관련 문서

- `docs/V3U_INFERENCE_LESSONS.md` 결함 기록 진실 원천
- `docs/V3U_TRANSITION_AUDIT_2026-05-22.md` 3U_C 생성 전 중간 점검 v1 (lane 상태 종합 + 다른 워크트리 영향 + 2U_C 컨셉 흡수 가능성)
- `docs/V3U_PYD_REMOVAL_PLAN.md` §11 자동 검증 시스템 extension
- `docs/V3U_TEST_AUTOMATION_GUIDE.md` 운영 매뉴얼
- `docs/WORKTREE_STRATEGY.md` V3 Lane Branch Parity Invariants
- `docs/UPSTREAM_SYNC_STRATEGY.md` V3 Ingress Policy
- `docs/CARRY_FORWARD_REGISTRY.md` V3U custom allowlist rule
- `CLAUDE.md` V3U Test Automation Gate + 결함 발견·수정 4단계 워크플로우
- `.omc/plans/2026-05-12_v3u_test_automation_and_governance.md` 컨센서스 플랜
- `tests/v3u/README.md` 테스트 운영자 빠른 참조
