# UX-05 Current STOP vs Historical HOF 구현 결과

> 완료일: 2026-08-29
>
> 구현 브랜치: `codex/process-research-ux-05-current-vs-history`
>
> 구현 커밋: `b6b06bc8` — `기능(UX): 현재 STOP과 과거 HOF 권위를 분리`
>
> 현재 권위: `DEVELOPMENT_DIAGNOSTIC_NO_OOS_NO_ADOPTION`
>
> 결론: **기록과 성과 화면에서 현재 0/7 STOP을 과거 run·winner·HOF보다 먼저 표시한다. 과거 좋은 결과에는 Historical-only watermark를 적용했고, 현재 승격 근거·OOS·실전 증거로 자동 해석하지 않는다.**

---

## 1. Status Dashboard

```text
┌───────────────────────────────────────────────────────────────┐
│ UX-05 AUTHORITY BOUNDARY                                     │
├────────────────────────┬──────────────────────────────────────┤
│ Current Canonical      │ Development 0/7 · STOP              │
│ Authority              │ DEVELOPMENT_DIAGNOSTIC_NO_OOS...    │
│ Verified-at            │ 2026-08-25                           │
│ Holdout                │ SEALED_NOT_TOUCHED                   │
├────────────────────────┼──────────────────────────────────────┤
│ History / HOF          │ HISTORICAL ONLY                      │
│ Current Promotion      │ BLOCKED                              │
│ OOS / Live Conversion  │ BLOCKED                              │
│ Automatic Adoption     │ BLOCKED                              │
└────────────────────────┴──────────────────────────────────────┘
```

---

## 2. 정보 순서

```text
CURRENT CANONICAL
├── Development 0/7 STOP
├── authority
├── verified-at
└── holdout
        │
        ▼
HISTORICAL ONLY
├── 과거 run·세대
├── 과거 winner
├── 과거 HOF·수익·점수
└── 현재 STOP을 덮지 않음
        │
        ▼
기존 History / Workbench 원문
```

이 순서를 기록과 성과 양쪽에 동일하게 적용했다.

---

## 3. 구현 구조

```text
dashboard-v4-shell.jsx
        │
        ├── V4HistoryWithAuthority
        │     ├── CurrentHistoryAuthority
        │     └── 기존 V4History
        │
        └── V4WorkbenchWithAuthority
              ├── CurrentHistoryAuthority
              └── 기존 V4Workbench
```

| 파일 | 역할 |
|---|---|
| `v4-current-history-authority.jsx` | 현재/역사 권위·verified-at·Mission Control 이동 |
| `v4-authority-pages.jsx` | 기존 페이지 소유권을 유지하는 얇은 wrapper |
| `dashboard-v4-shell.jsx` | 기존 History/Workbench 렌더를 wrapper로 교체 |
| `v4.css` | Current/Historical 시각 경계와 620 반응형 |
| `test_current_history_authority.py` | 현재 권위·순서·fail-closed·읽기 전용 계약 |

기존 440 pure LOC `v4-history.jsx`와 기존 HOF 구현은 수정하지 않았다.

---

## 4. TDD·정적 검증

| Gate | 결과 |
|---|---|
| 최초 UX-05 계약 | **3 failed · 1 passed** |
| UX-05 테스트 | **4 passed / 7.62s**, plugin autoload disabled |
| 테스트 함수 직접 실행 | 4/4 PASS |
| ANA-04 회귀 | **5 passed / 6.08s** |
| Ruff | PASS |
| basedpyright | 0 errors · 0 warnings |
| no-excuse | 0 violations |
| frontend typecheck | PASS |
| runtime JSX | 141 JSX / 594 graph files PASS |
| build | `app.js v=9175e0f9`, `v4.css v=0e9ac4af` |

정상 pytest plugin autoload 환경에서는 이 새 파일 실행 시 프로세스가 출력 없이 `-1`로 종료됐다. collect-only와 직접 함수는 통과했고, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`에서 4개 모두 종료 코드 0을 확인했다. 특정 외부 plugin 충돌은 UX-05 제품 수정 범위에 포함하지 않았다.

---

## 5. 인하우스 브라우저 QA

### 기록 1280×720

| 항목 | 관측 |
|---|---|
| Current boundary | History보다 먼저 |
| Current | Development 0/7 STOP |
| verified-at | 2026-08-25 |
| Historical copy | 과거 run·세대는 과거 실행 기록 |
| Mission Control 버튼 | `?tab=research`, Mission Control visible |
| overflow | 없음 · 1270=1270 |

### 성과 1280×720

| 항목 | 관측 |
|---|---|
| Current boundary | Workbench/HOF보다 먼저 |
| watermark | `HISTORICAL ONLY` |
| HOF copy | 아래 명예의 전당은 과거 비교 기록 |
| overflow | 없음 |

### 기록·성과 620×900

| 항목 | 관측 |
|---|---|
| 권위 grid | 1열 |
| authority dl | 1열 |
| watermark | static |
| 기록 URL | `?tab=history` |
| 성과 URL | `?tab=workbench` |
| page overflow | 없음 · 610=610 |
| console | warn/error 0 |

---

## 6. 성공·실패 경계

| 질문 | 판정 |
|---|---|
| UX-05는 성공했는가 | **예.** 현재 권위가 과거 성과보다 먼저 보이고 실제 탭 이동이 동작한다. |
| 과거 HOF가 삭제됐는가 | 아니다. 역사 비교 자료로 보존한다. |
| 과거 HOF를 승격할 수 있는가 | 아니다. Historical-only다. |
| 현재 경제 후보가 있는가 | 아니다. 0/7 STOP이다. |
| Holdout을 열 수 있는가 | 아니다. `SEALED_NOT_TOUCHED`다. |

---

## 7. 다음 단계

```text
[UX-05 COMPLETE]
        │
        ▼
[S9 KEYBOARD ACCESSIBILITY]
  ├── 실제 Tab 순서
  ├── Enter/Space 활성화
  ├── focus-visible
  ├── History → Mission Control
  └── Chrome 또는 Computer Use 교차검증
```
