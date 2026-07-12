# 전체 워크트리 pyd→py 상태 지도 및 wt-dev 반영 기능 연결 (2026-07-12)

## 목적

"전체 워크트리의 pyd 기능이 py로 잘 구현되어 있는가"에 대한 정확한 답을 기록으로 고정한다.
결론은 **"pyd-free lane 4곳은 자동 검증 기준 누락 없음, 단 lane마다 검증 깊이가 다르고
공식 lane 2곳은 설계상 pyd를 보존한다"**이다. 함께, wt-dev(2U_C 계열)에 반영 가능한
기능 목록이 담긴 계획서를 본 문서에서 연결한다.

## 1. 워크트리 전체 pyd→py 상태 지도 (2026-07-12 검증 기준)

### 1.1 pyd-free 변환 lane — 4곳 모두 정상

| worktree | branch | pyd 원본 | py 대체 | 검증 수준 | 판정 |
|---|---|---|---|---|---|
| `STOM_V.wt-3u` | `STOM_Version_3U` | `ui/main_window.pyd` (V3) | `ui/main_window.py` | **최고**: 통합 게이트 8/8 + 4축 심층 감사(호출 해석 0건 미해결, orphan 핸들러 0, MainWindow 메서드 계약 미해결 0, attr 1,607 strict critical=0) | 누락 없음 |
| `STOM_V.wt-3uc` | `STOM_Version_3U_C` | V3U 상속 | V3U 상속 | 통합 게이트 8/8 + tests/v3uc 32 + invariant diff allowlist only | 누락 없음 |
| `STOM_V.wt-2u` | `STOM_Version_2U` | `ui/ui_mainwindow.pyd` (V2) | pyd-free 런타임 | 표준 게이트: smoke `[OK]` + pyd GUI contract `[OK]`, tracked pyd 0 | 누락 없음 (표준 게이트 수준) |
| `STOM_V.wt-dev` | 2U_C 계열 feature | 2U 상속 | 2U 상속 | 표준 게이트: smoke `[OK]` + contract `[OK]`, `STOM_Version_2U_C`가 정상 ancestor | 누락 없음 (표준 게이트 수준), 개발 계속 가능 |

### 1.2 pyd를 보존하는 공식 lane — 변환 대상 아님 (설계 원칙)

| worktree | branch | pyd | 근거 |
|---|---|---|---|
| `STOM_V.wt-3` | `STOM_Version_3` | `ui/main_window.pyd` 보존 (upstream sha256 일치 확인) | 공식 lane invariant — upstream 원본 보존 |
| `STOM_V` | `STOM_Version_2` | upstream pyd 보존 | 동일 원칙 |

### 1.3 이번 검증 범위 밖 워크트리

| worktree | 성격 | 비고 |
|---|---|---|
| `wt-alpha`, `wt-dashboard-next`, `wt-dashboard-remodel`, `wt-evo-governance`, `wt-webbt` | pyd-free lane에서 분기한 개발 브랜치 | base lane 검증을 상속하나 개별 게이트 미실행 |

## 2. "잘 구현되어 있다"의 보장 범위와 한계

| 보장하는 것 (자동 검증 완료) | 보장하지 않는 것 |
|---|---|
| 외부 코드가 요구하는 `ui.X` attr 1,607개 전부 존재 (strict critical=0 warn=0) | 바이너리 pyd 내부 로직과의 수학적 동작 동일성 (pyd는 역컴파일이 아닌 계약 기반 추론) |
| 버튼/콤보/시그널 핸들러 배선 orphan 0, ui/ 84개 모듈 미해결 호출 0 | 실행 시 시각적/기능적 동일성의 최종 확인 |
| MainWindow 메서드 계약 미해결 0 (메서드 46 + self attr 148 + 외부 할당 98) | — |
| offline GUI 기동 smoke + pytest 49 회귀 | — |

**사용자 시각 검증 현황**: V3.32(V3U 사이클 15 B1)까지 완료. V3.33~V3.35 구간은 자동
게이트 통과 상태로 사용자 직접 실행 확인 대기 (`docs/V3U_NEXT_STEPS.md` §2).

## 3. wt-dev(2U_C)에 반영 가능한 기능 — 계획서 연결

상세 실행 계획(파일 매핑·명령·검증·기록 규칙 포함)은 다음 문서가 정본이다.

> **`docs/update_log/2026-07-12_2series_pyd_review_and_backport_plan.md`** §2~§3

요약 (V3.33~V3.35 유래, Kiwoom 유지 원칙으로 LS 전용 제외):

| ID | 기능 | 우선순위 | wt-dev 대상 파일 | 특이사항 |
|---|---|---|---|---|
| BP-1 | 바이낸스선물 정정주문 (native modify) | P1 | `trade/binance/binance_trader.py` | 현행 취소+재주문 → native modify, `futures_modify_order` 지원 확인 선행 |
| BP-2 | 주문 응답/예외 처리 강화 (upbit/binance) | P1 | `trade/upbit/upbit_restapi.py`, `trade/upbit/upbit_trader.py`, `trade/binance/binance_trader.py` | 실거래 안정성 직접 영향, 최우선 권장 |
| BP-3 | 바이낸스선물 감시종목제한 설정 | P2 | binance receiver(min/tick) + 설정 UI + `main` 테이블 컬럼 2개 | **DB migration spec 필수**, 백업 선행 |
| BP-7 | V3.33 명언 텍스트 | P3(보류) | 명언 정의 위치 | 텍스트만 선택 반영, 구조 변경 금지 |
| 제외 | BP-4/5/6 (LS 시장가·해외주식 체결·ordxctptncode) | — | — | LS API 전용, Kiwoom 유지판 무관 |

실행 규칙 핵심: 2U_C 직접 커밋 금지(백포트 전용 feature 브랜치), 순서 BP-2→BP-1→BP-3,
V3K 프로그램 phase 대상 파일과 겹치면 V3K 우선, 각 BP마다 smoke+contract+pytest 게이트.

## 4. 남은 사용자/후속 항목

| 항목 | 내용 |
|---|---|
| 사용자 실행 확인 | `stom.py` 기동 후 V3.33~V3.35 항목: 백테 시작, 명언, 타이틀바 색상, 바이낸스 정정주문/감시종목제한, 주문 예외 경로 |
| 2U push | `STOM_Version_2U` ahead 1 (`3b7a3aeb`, 검증 통과) — push 승인 대기 |
| 2U_C push | `STOM_Version_2U_C` ahead 26 — 개발 주체 시점 결정 |
| V3U A8 | `set_style.py` +1줄 allowlist 정식 등재 (다음 V3U 사이클 후보) |
| V3.36+ | 발표 시 `V3 공식 → V3U → 3U_C` 동일 패턴 |

## 5. 관련 문서

| 문서 | 내용 |
|---|---|
| `docs/update_log/2026-07-12_v3u_pyd_wiring_final_audit.md` | V3U 4축 심층 감사 상세 (본 문서 §1.1 근거) |
| `docs/update_log/2026-07-12_2series_pyd_review_and_backport_plan.md` | 2U/2U_C 재검토 + BP 백포트 실행 계획 정본 |
| `docs/update_log/2026-07-12_v3u_v335_pyd_free_update.md` | V3.35 V3U 흡수 감사 |
| `docs/V3U_NEXT_STEPS.md` | V3U 사이클 상태 (사이클 21, 시각 검증 대기 항목) |
