# UXR-P1 — 관측·계약 동결 (Observation & Contract Freeze)

- 작성: 2026-07-18
- 브랜치: `uxr-p1-observe` (from `feature/dashboard-hodo-20260717`)
- 목적: UX 구현(P2~) 전에 현 대시보드의 구조·route·field·연결 상태를 계측·동결한다.
  화면 변경 없음. 순수 관측 + 계측 instrumentation.

---

## 0. 헤드라인 발견 (Critical) — WS 세션 게이트가 정본 경로에서 라이브 연결을 거부

계측 결과, V4 정본 경로로 진입하면 WebSocket이 **열릴 때마다 즉시 `code 4401 session_required`로 닫히고 무한 재시도**한다(15초간 22회 비정상 종료 관측).

### 증거
- `window.getWsDiag()` (신규 계측): `{ unexpectedCloses: 22, codes: { "4401": 22 }, reason: "session_required" }`
- Set-Cookie 헤더 직접 비교:
  | 경로 | Set-Cookie(session) |
  |---|---|
  | `/ui/v4/` (부트스트랩 경로) | ✅ 발급 |
  | `/ui/evolution` (정본 승격) | ❌ 없음 |
  | `/ui/` (루트) | ❌ 없음 |

### 근본원인
- `security.py: BOOTSTRAP_PATHS = {"/ui/v4", "/ui/v4/"}` — 세션 쿠키는 이 경로에서만 발급.
- 하지만 V4 graph-first 셸 승격(2026-07-17)으로 **정본 진입은 `/ui/`·`/ui/evolution`·`/ui/backtest`·`/ui/chart-replay`** 로 이동.
- `issue_bootstrap_cookie`(app.py 미들웨어)는 위 정본 경로를 쿠키 발급 대상에서 제외 → 세션 미발급.
- `/ws`(`authorize_websocket`, Capability.LOOP_CONTROL)는 세션 쿠키를 요구 → 4401 거부 → 클라이언트 무한 재연결(`conn-backend.jsx` 지수 backoff).

### 영향
- 정본 경로 사용자는 **라이브 WS 데이터를 전혀 받지 못하고**, 연결 배지가 계속 "재연결" 깜빡임.
- "연결 깜빡임"(R09·R32)은 **cosmetic backoff가 아니라 실제 연결 실패**다. → **P2에서 debounce로 은폐 금지**(검토 §4). 진짜 수정은 **정본 경로 세션 부트스트랩**.

### 수정 위치(P2에서 실행)
- `security.py`: `issue_bootstrap_cookie`가 셸 서빙 GET(`/ui/`, `/ui/evolution[/*]`, `/ui/backtest`, `/ui/chart-replay`, 기존 `/ui/v4[/]`)에서도 세션을 발급하도록 확장. httponly·samesite=strict·loopback 경계 불변.

---

## 1. 셸 토폴로지 (동결)

3개 HTML 셸이 **단일 번들**(`bundle/app.js`)을 공유. 라우팅으로 진입 셸 결정.

| 셸 | 진입 | 헤더 버전 | 상태 |
|---|---|---|---|
| **V4 graph-first (정본)** | `/ui/`·`/ui/evolution[/*]`·`/ui/backtest`·`/ui/chart-replay`·`/ui/v4[/]` | `v4-ops` | 기본 |
| Legacy(app.jsx) | `?dashboard_version=legacy`(v2/production/ops 별칭) 1회 | v2 계열 | 폴백 |
| Remodel(v3) | `/ui/remodel[/*]`·`?dashboard_version=v3` | v3 | 실험 |

- 신규 패널은 **반드시 V4 셸(`v4-*.jsx`)** 에 배선(가드: `test_shell_wiring_parity.py`).
- 셸 컴포넌트: `dashboard-v4-shell.jsx`(`DashboardV4Shell`) — 좌측 레일 + graph-first stage.

## 2. 탭 인벤토리 (현 9탭 → 목표 6탭)

| # | key | 현 라벨 | 컴포넌트 | P3 IA 계획 |
|---|---|---|---|---|
| 1 | research | Live | `V4ResearchLive` | 유지(Live) |
| 2 | backtest | Backtest | `V4Backtest` | 유지·강화(독립) |
| 3 | replay | Replay | `V4Replay` (keep-alive) | 유지 |
| 4 | history | History | `V4History` | 유지 + 거버넌스 이전지 |
| 5 | lab | Lab | `V4Lab` | field-level 이전 후 해체 |
| 6 | workbench | Bench | `V4Workbench` | 성과(전당)로 개명 |
| 7 | audit | Audit | `V4Audit` | **거버넌스 이전**(삭제 아님) |
| 8 | alpha | Alpha | `V4Alpha` | 추후(P8, 비-P4) |
| 9 | context | Context | `window.AIContextPanel` | 격하(drawer) |
| — | (legacy) | LEGACY | 링크 | 유지 |

## 3. Route → 셸/탭 매핑 (동결)

- 셸 매핑: `dashboard-v4-shell.jsx: V4_PATH_TAB_MAP` + `v4TabFromPathname()`.
- 딥링크: `/ui/evolution/{records|lab|workbench|verdict|process|backtest|chart-replay}` → 각 탭.
- 별칭 리다이렉트(app.py): `/ui/records|history|lab|pro|verdict|process|simulation` → `/ui/evolution/*`.
- 탭 전환은 `?tab=` 쿼리 동기화(`replaceState`), 키보드 Home/End/Arrow 지원.

## 4. 백엔드 엔드포인트 인벤토리 (read-only vs mutation 경계)

### 읽기 전용 GET(무예외 규약) — 발췌
`/status`·`/config/spec`·`/runs`·`/run_state`·`/runs/compare`·`/equity_curve[s]`·`/hall_of_fame`·`/decisions`·`/freeze_verdict`·`/regime_report`·`/portfolio_*`·`/tmap_*`·`/edge_ratio`·`/feature_importance`·`/variable_correlation`·`/ai_context_pack`·`/backtest_detail`·`/strategy_code`·`/strategy_diff`·`/prompts`·`/autopsy`·`/trade_quant`·`/counterfactual`·`/freeze_mc`·`/research_maturity`·`/gpt_auth/status` 등 (+ alpha `/api/alpha/*`).

### Mutation(capability 게이트 + 세션 + origin) — P6/거버넌스에서 계약화
- WS `/ws`(Capability.LOOP_CONTROL): start/stop/final_approval.
- Backtest: `POST /bt/run`·`/bt/job/cancel`·`/bt/job/meta`·`/bt/strategy`·`/bt/strategy/delete`.
- 거버넌스: `final_approval→export_winner`, `/record_decision`.
- 게이트: `security.py` — 세션 쿠키 + origin 정확일치 + loopback + capability. body 상한 256KB, WS 메시지 상한 128K chars.

## 5. 연결 계측 (신규 — P1 산출물)

- `conn-backend.jsx`: `_recordWsDiag()` 링버퍼(200) — open/close/error/demo 이벤트에 `{t, kind, code, reason, byUs, attempt}` 기록.
- `window.getWsDiag()` / `window.__stomWsDiag` 노출(수동 점검). 순수 관측, 연결 동작 불변.
- **debounce(P2) 전 근거 확보 완료**: 현 끊김은 4401 세션 게이트 → 근본 수정 후 재계측으로 debounce 필요성 판정.

## 6. baseline 스크린샷 (3해상도)

- `artifacts/uxr_p1_baseline_3440.png` (3440×1440 ultrawide, 주 타깃)
- `artifacts/uxr_p1_baseline_2560.png` (2560×1440)
- `artifacts/uxr_p1_baseline_1920.png` (1920×1080)
- 각 단계(P2~) 전후 비교 기준선. (스크린샷은 세션 정본화 전 상태 — WS 미연결/데모 폴백 UI 포함.)

## 7. 동결 계약(P2~ 착수 전 불변)

- 단일 발행기(backend WS 단일 소스), read-only 조회 무예외, `performance_proved=false`.
- V4 셸 배선 가드·안전 문구(실거래/브로커 없음·HUMAN GATE·APPEND-ONLY) 유지.
- 신규 패널 → `v4-*.jsx`. 번들 변경 시 `npm run build` + 커밋.

## 8. 다음 단계(P2)

1. **세션 부트스트랩 정본화**(헤드라인 수정) — `security.py` BOOTSTRAP 경로 확장 + 회귀·라이브 재계측(4401 소멸 확인).
2. 재계측 후 잔여 끊김 있으면 reconnect debounce(짧은 grace) 적용, 없으면 불필요 판정 기록.
3. 타이포·버전 배지·탭 강조.
