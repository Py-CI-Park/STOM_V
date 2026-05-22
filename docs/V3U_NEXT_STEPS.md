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

## 2. 현재 사이클 상태 (사이클 5, 2026-05-20)

| 지표 | 값 |
|---|---|
| 결함 누적 (LESSONS.md §7) | 10 |
| 자동 회귀 테스트 | 42 |
| 신규 자동 도구 | 1 (`scripts/v3u_attr_inventory_diff.py`) |
| 수정 커밋 누적 | 5 |
| 재발 방지 액션 | 5/5 적용 완료 |
| CRITICAL drift baseline | 68 (max 100) |
| 사용자 시각 검증 사이클 | 5회 |
| Remote sync | 14 commits push 완료 (`Py-CI-Park/STOM_V`) |
| stom.py 활성 상태 | 백그라운드 (사용자 시각 검증 대기) |

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
| 🟢 1 | A1 (사전 정찰) | 사용자 추가 시각 사이클 사전 차단, ROI 가장 높음 |
| 🟡 2 | A2 (CRITICAL 정리) | A1 진행 중 자연스럽게 일부 처리됨 + 안전망 강화 |
| 🟠 3 | B1 (시각 결과 reactive) | stom.py 떠있는 동안 병렬 가능 |
| 🔵 4 | C1 (DB 검증) | production 사용 전 |
| 🔵 5 | C2 (실거래) | release 전 |
| ⚪ 6 | D1·D2·D3 (정책 결정) | 정량 측정 불가, 사용자 판단 |

**Default 권장 흐름**: A1 → A2 → (B1 reactive) → C1 → C2 → D1

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
