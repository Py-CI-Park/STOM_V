# Ultragoal G001 — 100점 재도전 기준/인벤토리

- 생성 시각: 2026-06-28T00:36:29.792964+00:00
- 승인 계획: `.gjc/_session-019f05e9-d676-7000-9c61-3c206a2d4031/plans/ralplan/019f05e9-d676-7000-9c61-3c206a2d4031/pending-approval.md`
- 현재 보정 총점: 79.6/100
- 현재 캡처 평균: 71.5/100

## 현재 최저 페이지

|페이지|보정 총점|캡처 점수|
|---|---:|---:|
|차트 리플레이|76.0|70.2|
|백테스트|77.4|71.5|
|히스토리|79.4|70.0|

## 실행 매트릭스

|Story|Gap|Required change|Evidence|
|---|---|---|---|
|G002|live side effects contaminate reference captures|fail-closed ?demo=reference mode, no REST/WS/timers/random/localStorage writes/mutations|reference no-network proof and mode unit tests|
|G003|six condition-suite pages partly static/live-mixed|mode-aware selectors/adapters and page model fixtures/live mappings|page markers, reference captures, live smoke for core endpoints|
|G004|Backtest static depth below production|implement /bt/* endpoint/action/WS matrix in zip shell|live /bt API/WS manifest, inert reference proof|
|G005|Chart Replay static depth below production|implement /sim/* endpoint/action/WS matrix in zip shell|live /sim API/WS transcript, inert reference proof|
|G006|no hard visual/evidence gate|capture all 8 pages, score, contact sheet, manifest, forbidden scan|manifest thresholds all passed|
|G007|no final 100-point proof package|run full command/browser/API/WS/architect/QA gate|clean quality gate and final checkpoint|

## 현재 app.js 위험 신호

- hasRouteToState: `True`
- callsReconnectBackend: `True`
- usesFetchJson: `True`
- constructsWebSocket: `True`
- usesLocalStorage: `True`
- usesMathRandom: `True`
- needsFailClosedReferenceMode: `True`

## API 계약 수

- backtest: 34 routes
- simulation: 6 routes
- coreDashboard: 58 routes

## 안전 스캔 기준

- 금지어 현재 출현: []
- 필수 cue 현재 출현: ['실거래/주문 기능 없음', '브로커 로그인 없음', '계좌/자산 연동 없음', 'Human Approval Gate', 'Append-Only Audit', '연구 전용']

## 증거

- JSON inventory: `artifacts/ultragoal-g001-100point/baseline-inventory.json`
- Focused baseline tests: `pytest tests/unit/test_dashboard_remodel_static.py tests/unit/test_dashboard_remodel_baseline_contract.py -q` -> `11 passed`

## QA 보강 — 승인/리플레이/안전 스캔

- 승인 출처: 사용자가 현재 대화에서 `울트라골 명령어 승인 계획 진행 승인`으로 pending plan 실행을 승인했다. 계획 파일 자체는 `pending approval` 상태였으나 Ultragoal 실행은 이 승인 메시지 이후 시작됐다.
- Replay matrix 보강: `/sim/health`, `/sim/days`, `/sim/demo`, `/sim/stocks`, `/sim/signals`, `/bt/strategies`, `/sim/ws`와 WS client actions `start/pause/resume/speed/seek/stop`, server messages `meta/bars/history/done/error`를 G005 필수 증거로 고정했다.
- Safety terms 보강: hidden export, automatic production export, mutable audit edit/delete, broker runtime/login, account balance/trading/connect, live order, final_approval 계열을 명시적 scan term으로 고정했다.
- JSON inventory updated: `approvalProvenance`, `replayWsMatrix`, expanded `safetyTerms.forbidden`.

## G001 결론

현재 실행 기준은 고정됐다. 다음 G002는 `?demo=reference` fail-closed 모드부터 구현해야 하며, 현재 `app.js`의 live fetch, WebSocket, localStorage, Math.random 경로가 reference 캡처를 흔드는 직접 차단 대상이다.

## QA 보강 — safety scan 결과 정합성

- `baseline-inventory.json`의 `safetyTerms.presentForbiddenTerms`는 실행 가능한 금지 control/handler 발견 여부만 의미하도록 `[]`로 정정했다.
- 금지/안전 문구 자체가 설명 텍스트에 출현하는 경우는 `safetyTerms.lexicalSafetyTermHits`로 분리했으며, 이는 blocker가 아니다.
- 최종 G006/G007에서는 DOM/action handler 기반 forbidden control scan으로 다시 검증한다.
