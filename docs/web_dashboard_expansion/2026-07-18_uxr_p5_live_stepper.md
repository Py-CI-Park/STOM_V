# UXR-P5 — Live 스테퍼 상태기계 확장 (gap-only)

- 작성: 2026-07-18 · 브랜치: `uxr-p5-live-stepper`

## 원칙 (§10-2 gap-only)

Live 스테퍼는 이미 성숙(`PhaseTimeline`·`LIVE_PHASE_INDEX`·`phaseIndex`·`ProcessFlowDiagram` dagre 시각화·`flowStepStatus`). **재구축 아님 — 결손(실패 상태 은폐)만 보강.**

## 변경 (phase-detail.jsx `PhaseTimeline`)

기존 상태 어휘 = active/done/pending 3종뿐 → 실패·중단·차단 시 스테퍼가 "pending 동결"로 오표시(§10-9 위반).

- 상태 확장: `error`/`blocked`/`stopping`/`complete` 를 명시적으로 판별.
- **실패 단계 표시**: error/blocked 시 마지막 알려진 단계를 `failed`(X 아이콘·red)로 표시(`failedIdx`).
- **사유 배너**(`phase-status-banner`): error→"오류 · {latest.error}", blocked→"차단 · {block_reason|message}". 은폐 금지.
- **상태 라벨**(gen-tag): 정지 중… / 실패 · 중단됨 / 차단됨 / N세대 완료 — 각 상태색(amber/red/teal).
- CSS는 **v4.css**에 배치(styles.css 핀 테스트 얽힘 회피 — legacy는 폴백).

## follow-live vs user-pinned (§10-9 잔여)

- 현 스테퍼는 상태 표시(navigation 아님) — live phase 자동 반영. 사용자가 과거 단계를 pin해 자동 진행에 밀리지 않게 하는 phase 네비게이션은 별도 후속(P5b)으로 문서화. 현재는 backend 단일 발행기·표시 전용 규약 유지.

## 검증

- 격리 렌더(실브라우저, `window.PhaseTimeline` 합성 상태):
  | 상태 | gen-tag | 실패단계 | 배너 |
  |---|---|---|---|
  | error | 실패 · 중단됨(red) | 1(백테 X) | 오류 · 백테 엔진 예외… |
  | blocked | 차단됨(amber) | 1(생성 X) | 차단 · frozen snapshot 미충족 |
  | stopping | 정지 중…(amber) | 0 | 없음 |
  | complete | 14세대 완료(teal) | 0 | 없음 |
  `artifacts/uxr_p5_states.png`.
- 구조 가드: `test_dashboard_phase_mapping.py::test_phase_timeline_surfaces_failure_stop_and_block_states`. 18 통과.
- 번들 v=1a690122, v4.css?v=20260718p5. phaseIndex·LIVE_PHASE_INDEX 불변(회귀 없음).

## 다음(P6 Backtest gap)

- 현 웹 구현(`/bt/run`·bt-tab-run·bt-result-area·Monte Carlo) inventory → python GUI parity matrix → 결손만 보강(§10-2·§10-4 mutation 경계).
