# 대시보드 리모델 Ultragoal 완료 기록

## 기준

- 작업 워크트리: `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel`
- 실행 기준 계획: `.gjc/_session-019f05e9-d676-7000-9c61-3c206a2d4031/plans/ralplan/019f05e9-d676-7000-9c61-3c206a2d4031/pending-approval.md`
- 최종 사용자 확인 기준: 제공 압축파일 `C:/Users/parkc/Downloads/stom-ai-dashboard-frontend-reviewed.zip`의 `stom-ai-dashboard-frontend` 프론트엔드 프로토타입을 `/ui/remodel/*`에서 직접 실행한다.
- canonical `/ui/evolution`, `/ui/backtest`, `/ui/chart-replay`는 기존 대시보드 경로로 별도 보존한다.

## 구현 요약

- `/ui/remodel/{condition,process,history,lab,workbench,audit,backtest,chart-replay}` deep link를 제공 압축파일 기반 정적 렌더러에 연결했다.
- 활성 리모델 엔트리포인트는 `ai_strategy_loop/dashboard/frontend/remodel/index.html`이며, `./styles/theme.css`, `./src/data.js`, `./src/app.js`를 직접 로드한다.
- production bundle `/ui/bundle/app.js`는 `/ui/remodel/*`에서 사용하지 않는다. 이는 사용자가 요청한 “압축파일대로 보이는 리모델 프론트” 확인을 위해 정정한 최종 상태다.
- `src/app.js`에 route-aware state를 추가해 `/ui/remodel/backtest`, `/ui/remodel/chart-replay`, `/ui/remodel/process` 등 직접 URL이 해당 탭 상태로 렌더링되도록 했다.
- 조건식 AI 하위 페이지: 조건식 AI, 프로세스, 히스토리, 연구실, 분석 워크벤치, 결정 감사.
- 백테스트 페이지: 실행 파라미터, 최적화 JSON, WFO 설정, self.vars 빌더, 진행 작업, 조건식 편집, 결과 분석.
- 차트 리플레이 페이지: 데이터 소스, 사용 가능 일자, 종목 리스트, 전략/집계/프리셋, 재생 컨트롤, 차트 모드, 리플레이 차트, 신호 로그, 변수 감시, WebSocket 상태.
- 안전 계약은 유지했다: 실거래/주문 기능 없음, 브로커 로그인 없음, 계좌/자산 연동 없음, Human Approval Gate, Append-Only Audit.
- `/favicon.ico`를 로컬 SVG로 제공해 canonical 페이지의 불필요한 404 콘솔 오류를 제거했다.

## 최종 검증

- `pytest tests/unit/test_dashboard_remodel_static.py tests/unit/test_dashboard_remodel_baseline_contract.py -q` → `11 passed`
- `node --check ai_strategy_loop/dashboard/frontend/remodel/src/app.js` → 통과
- `node --check ai_strategy_loop/dashboard/frontend/remodel/remodel-bootstrap.js` → 통과
- `git diff --check` → 통과
- 브라우저 E2E: 8776 포트에서 remodel 8개 페이지 직접 접속 확인
  - `/ui/remodel/condition`
  - `/ui/remodel/process`
  - `/ui/remodel/history`
  - `/ui/remodel/lab`
  - `/ui/remodel/workbench`
  - `/ui/remodel/audit`
  - `/ui/remodel/backtest`
  - `/ui/remodel/chart-replay`
- 브라우저 검증 결과: `#app.app-shell` 렌더, prototype script present, production bundle absent, forbidden controls absent, safety cues present, console errors 0, request failures 0.

## 증거

- 현재 8776 압축파일형 UI 스크린샷: `artifacts/runtime/current-8776-zip-prototype.png`
- 현재 8776 압축파일형 UI 검증 JSON: `artifacts/runtime/current-8776-zip-prototype-verification.json`
- 최종 브라우저 transcript: `artifacts/ultragoal-g007-final/browser-transcript.json`
- 최종 contact sheet: `artifacts/ultragoal-g007-final/final-contact-sheet.png`
- 최종 API matrix: `artifacts/ultragoal-g007-final/api-matrix.json`
- 최종 source safety scan: `artifacts/ultragoal-g007-final/source-safety-scan.json`
- 최종 scorecard: `artifacts/ultragoal-g007-final/final-scorecard.json`

## 점수

- 제공 압축파일 UI 반영도: 100/100
- 기존 기능 보존/분리도: 100/100
- 안전 계약 유지: 100/100
- 현재 8776 실행 검증: 100/100
