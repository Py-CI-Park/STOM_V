# UX-04 Research Mission Control 구현 결과

> 완료일: 2026-08-28
>
> 구현 브랜치: `codex/process-research-ux-04-mission-control`
>
> 구현 커밋: `9f27ed24` — `기능(UX): 연구 중단 Mission Control을 첫 화면에 배치`
>
> 연구 권위: `DEVELOPMENT_DIAGNOSTIC_NO_OOS_NO_ADOPTION`
>
> 결론: **사용자가 첫 화면에서 실행 성공, 경제 실패, 정상 중단, 지금 허용된 행동을 분리해 읽을 수 있다. 연구 수치·판정·Holdout 상태는 바꾸지 않았다.**

---

## 1. Current Status Dashboard

```text
┌───────────────────────────────────────────────────────────────┐
│ UX-04 RESEARCH MISSION CONTROL                               │
├────────────────────────┬──────────────────────────────────────┤
│ Platform              │ G1 28/28 VALID                      │
│ Paired Signal         │ 3/7 · 승격 증거 아님               │
│ Development Rule      │ 0/7 · STOP                          │
│ Current State         │ 정상 중단                           │
│ Allowed Action        │ 읽기 전용 실패 부검                │
│ Blocked               │ G2 · Holdout · 자동채택             │
│ Holdout               │ SEALED_NOT_TOUCHED                  │
└────────────────────────┴──────────────────────────────────────┘
```

```text
G0 실행      G1 실행      짝비교        경제 Gate       다음 연구
  [완료]  ─→   [완료]  ─→  [3/7]   ─→    [0/7]    ─→   [차단]
                                                           ▲
                                                     CURRENT POINT
```

---

## 2. 구현 목적과 변화

| 이전 문제 | UX-04 변화 | 사용자 효과 |
|---|---|---|
| 프로그램·Family·차트가 현재 판정보다 먼저 보임 | Mission Control을 연구 화면 첫 결정 Surface로 이동 | 첫 화면에서 현재 상태를 바로 이해 |
| 28/28이 전략 성공처럼 보일 수 있음 | 실행 상태와 Development Rule을 별도 카드로 표시 | 플랫폼 성공과 경제 실패 분리 |
| 다음 행동과 금지 행동이 여러 위치에 흩어짐 | `읽기 전용 실패 부검`과 `G2·Holdout·자동채택 차단`을 한 줄에 고정 | 허용 범위가 명확해짐 |
| UX-03 후보/Fold/Exit 표가 처음부터 길게 노출 | 판정 근거를 기본 접힘으로 전환 | 요약 우선, 필요할 때만 상세 확인 |
| 화면의 연구 순서가 암묵적 | G0→G1→Paired→Economic→Locked 5단 Roadmap 표시 | 현재 위치를 한눈에 파악 |

읽기 순서는 다음으로 고정했다.

```text
[정상 중단]
     ↓
[실행 상태] [왜 멈췄나] [지금 허용된 행동]
     ↓
[G0 → G1 → Paired → Economic → Locked]
     ↓
[차단 정책]
     ↓
[필요할 때만 UX-03 상세 근거 펼침]
```

---

## 3. 구현 파일

| 파일 | 역할 |
|---|---|
| `frontend/v4-research-result.jsx` | Mission Control, 상태 카드, Roadmap, 정책, 상세 토글 |
| `frontend/v4-research.jsx` | Mission Control을 프로그램 Cockpit보다 먼저 렌더 |
| `frontend/v4.css` | 산업형 상태 계층, 1280/620 반응형, focus-visible |
| `tests/unit/dashboard/test_research_mission_control.py` | 순서·문구·접힘·읽기 전용·반응형 계약 |
| `frontend/bundle/app.js`, `manifest.json`, HTML 6종 | 프로덕션 번들 `app.js v=2f299da4` |

API·봉인 evidence·연구 판정·DB·전략 조건식은 변경하지 않았다.

---

## 4. TDD와 자동 검증

| Gate | 결과 |
|---|---|
| UX-04 최초 계약 | **RED: 3 failed, 1 passed** |
| UX-04 + UX-03 + ANA-03 집중 회귀 | **15 passed / 56.31s** |
| Ruff | All checks passed |
| basedpyright | 0 errors · 0 warnings · 0 notes |
| Python no-excuse | violations 0 |
| Frontend typecheck | exit 0 |
| Runtime JSX graph | 138 JSX / 590 graph files PASS |
| Production build | exit 0 · `app.js v=2f299da4` |

---

## 5. 실제 브라우저 사용 결과

정상 진입 주소: `http://127.0.0.1:18833/?tab=research`

| 시나리오 | 관측 결과 |
|---|---|
| 최종 bundle | 화면에서 `build 2f299da4` 확인 |
| 첫 Surface | Mission Control 1개, 기존 프로그램보다 DOM상 먼저 위치 |
| 초기 상세 | `detailsOpen=false` |
| 1280×720 | client 1270 = scroll 1270, 가로 넘침 없음 |
| 620×900 | client 610 = scroll 610, 상태·Roadmap 각각 574px 1열 |
| 상세 펼침 | 후보 버튼 7개, Fold 표 1개, `aria-expanded=true` |
| console | warn/error 0 |

키보드 계약은 native `button`, `aria-expanded`, `aria-controls`, `summary`, `focus-visible`로 구현·정적 검증했다. 인앱 브라우저의 합성 Enter/Space는 포커스만 이동하고 기본 click을 발생시키지 않아 실제 키 활성화 E2E는 증명하지 못했다. 이는 UX-04의 데이터·클릭 동작 실패가 아니지만, S9 접근성 Gate에서는 사람 키보드 확인 또는 별도 브라우저 자동화로 닫아야 한다.

---

## 6. 성공·실패 경계

| 질문 | 판정 |
|---|---|
| UX-04 구현은 성공했는가 | **예.** 실제 봉인 데이터로 첫 화면 판단과 progressive disclosure가 동작한다. |
| 연구가 경제적으로 성공했는가 | **아니다.** Development Rule 0/7은 그대로다. |
| G2를 실행할 수 있는가 | **아니다.** UI와 문서 모두 차단 상태다. |
| Holdout을 열 수 있는가 | **아니다.** `SEALED_NOT_TOUCHED`다. |
| 자동채택할 수 있는가 | **아니다.** 권위와 API 모두 읽기 전용이다. |
| 다음 제품 작업은 무엇인가 | **ANA-04 읽기 전용 실패 부검**이다. |

---

## 7. 다음 단계

```text
[UX-04 COMPLETE]
       │
       ▼
[ANA-04 Failure Autopsy]
  ├─ Family 공통 실패
  ├─ 양수 Fold 부족
  ├─ 거래수 감소
  ├─ MDD/최악 Fold
  └─ Exit attribution
       │
       ▼
[UX-05 Current STOP vs Historical HOF]
```

ANA-04에서도 threshold 변경, 새 후보 생성, 재실행, G2, Holdout, 채택은 하지 않는다.
