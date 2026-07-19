# UXR-P2 — 안정화·타이포 (Connection Stabilization & Typography)

- 작성: 2026-07-18
- 브랜치: `uxr-p2-connection` (from `feature/dashboard-hodo-20260717`)
- 선행: UXR-P1 관측(WS 4401 세션 게이트 근본원인 확정)

## 1. 세션 부트스트랩 정본화 (헤드라인 수정 — P1 발견의 근본 해결)

- 문제(P1): 정본 경로(`/ui/`·`/ui/evolution`)는 세션 쿠키 미발급 → `/ws`가 `4401 session_required`로 무한 거부 → 라이브 데이터 없음, 연결 깜빡임.
- 수정: `security.py`
  - `BOOTSTRAP_PATHS`를 V4 셸 서빙 GET 진입점으로 확장: `/ui/`·`/ui/v4[/]`·`/ui/evolution`·`/ui/backtest`·`/ui/chart-replay`·`/ui/remodel[/]`.
  - `BOOTSTRAP_PATH_PREFIXES=("/ui/evolution/","/ui/remodel/")` + `_is_bootstrap_path()`로 동적 하위탭 딥링크 포함.
  - httponly·samesite=strict·loopback·origin 경계 불변. 4xx 응답엔 쿠키 미발급(미지 하위탭 404 검증).
- 검증:
  - Set-Cookie: `/ui/`·`/ui/evolution`·`/ui/evolution/records`·`/ui/backtest`·`/ui/chart-replay` 모두 발급 ✅
  - 실브라우저 깨끗한 로드: WS diag `total:1, kinds:["open"], unexpectedCloses:0` — LIVE 유지, 4401·demo 없음(이전 15초 22회 4401 → 0회).
  - `test_security_boundary.py`: 신규 6 파라미터 + 미지-하위탭 음성 1건 추가, 25 통과.

## 2. 정직한 재연결 grace (은폐 없는 debounce — 검토 §4)

- `conn-backend.jsx`: 안정 연결(≥2s 유지)의 단발 종료만 1.2s 유예 → 그 안에 재연결 성공 시 깜빡임 없음.
- **플래핑**(열리자마자 <2s 닫힘 = 세션/권한 지속 실패 신호)은 즉시 "reconnecting" 노출 → 장애 은폐 금지.
- `lastOpenAt`/`graceTimer` ref, 언마운트 정리. 근본(세션) 수정으로 현재 끊김 0이지만, 실제 네트워크 blip에 한해 UX 완충.

## 3. 관측 계측 (P1 계승)

- `getWsDiag()`/`window.__stomWsDiag` 유지 — 재연결 grace가 실패를 가리지 않는지 상시 검증 가능.

## 4. 버전 배지 (R08 관측성)

- 상단 안전 스트립에 `build <app.js 지문>` 칩 추가(`v4-sfx build`, 파란색). 런타임에 `app.js?v=` 파싱 → 사용자가 최신 빌드 여부 확인. 빌드 스크립트 변경 불필요.

## 5. 탭 강조 + 울트라와이드 타이포 (R02·R06·R07·R08)

- `v4.css`: 활성 레일 탭에 좌측 액센트 바(inset 3px teal) + 라벨 teal·600 강조.
- `@media (min-width:2400px)`: brand/rail-label/safety chip/view-title/runsel/stat 값 폰트 확대(밀도 유지).
- `v4.css?v=` 수동 핀 갱신(`20260718p2`).

## 6. 빌드·검증

- 번들 재빌드: app.js `v=4ea4112c`.
- 집중 회귀: security_boundary·shell_wiring_parity·static_cache 34 통과.
- 실브라우저 3해상도 스크린샷: `artifacts/uxr_p2_{3440,2560,1920}.png`. build 배지·Live 탭 강조 렌더 확인.

## 7. 다음(P3 IA migration)

- Audit 거버넌스 이전(삭제 아님)·Context 격하·Lab field 이전·Bench→성과(전당) 개명 + redirect/rollback/파리티 가드.
