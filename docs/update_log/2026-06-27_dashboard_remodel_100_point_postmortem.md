# 대시보드 리모델 100점 미달 원인 분석 및 재도전 기준

## 목적

사용자가 요청한 실제 리모델링 대시보드 대비 현재 구현이 왜 100점이 아니었는지, 어떤 판단 실수와 시행착오가 있었는지 기록한다. 이 기록은 다음 구현 라운드에서 100점 기준을 명확히 고정하기 위한 회고 자료다.

## 현재 정정 점수

최종 100점 주장은 취소한다. 2026-06-27 캡처 비교 재채점 기준 현재 상태는 다음과 같다.

| 기준 | 점수 |
|---|---:|
| 캡처 시각 유사도 평균 | 71.5 / 100 |
| DOM/정보구조 반영 평균 | 89.9 / 100 |
| 기능 반영 평균 | 79.8 / 100 |
| 보정 총점 평균 | 79.6 / 100 |

근거:

- 비교 contact sheet: `artifacts/runtime/zip-parity-compare/side-by-side-contact-sheet.png`
- 상세 점수 JSON: `artifacts/runtime/zip-parity-compare/detailed-scorecard.json`
- 캡처 재채점 문서: `docs/update_log/2026-06-27_dashboard_remodel_capture_parity_recheck.md`

## 왜 이렇게 개발되었는가

### 1. “기능 보존”을 “기존 production React graph 유지”로 과하게 해석했다

초기 요구는 다음 두 가지를 동시에 포함했다.

1. 현재 웹 대시보드 기능을 모두 보존한다.
2. 제공 압축파일 기준으로 리모델링 대시보드를 구현한다.

여기서 첫 번째 조건을 너무 강하게 잡아 `/ui/remodel/*`도 기존 production React bundle을 로드하도록 만들었다. 이 방식은 기존 API, 백테스트, 차트 리플레이 기능 보존에는 유리했지만, 사용자가 제공한 압축파일의 실제 시각 구조와는 달라졌다. 결과적으로 사용자가 “프론트엔드가 바뀐 게 없어 보인다”고 지적한 상태가 발생했다.

### 2. 압축파일의 역할을 “디자인 참고”와 “실행 대상” 사이에서 명확히 고정하지 못했다

압축파일 내부 `CODEX_AGENT_BRIEF.md`는 “이 정적 프로토타입을 production frontend로 전환하라”고 말한다. 그런데 초기 구현에서는 압축파일을 완전한 실행 대상이 아니라 production UI에 덧씌울 디자인 참고로 취급했다. 그래서 `src/app.js`, `src/data.js`, `styles/theme.css`를 보존하면서도 실제 활성 엔트리포인트는 production bundle이었다.

이것이 첫 번째 큰 시행착오다.

### 3. 100점 검증 기준을 파일/라우트/기능 존재 중심으로 먼저 잡았다

초기 검증은 다음을 확인했다.

- 라우트가 열린다.
- 탭이 존재한다.
- 안전 금지 문구가 있다.
- forbidden control이 없다.
- API가 200을 반환한다.
- 콘솔 오류가 없다.

이 기준은 “동작한다”는 증거는 되지만, “사용자가 제공한 캡처와 실제 화면이 같은가”를 증명하지 못한다. 픽셀/구조 캡처 비교가 뒤늦게 들어갔기 때문에 100점 판단이 과장되었다.

### 4. 실제 8776 백엔드 상태가 참조 캡처의 더미 상태를 덮어썼다

압축파일 참조 캡처는 `Gen 137`, `running`, `68.5%`, `backend 9200` 같은 기준 상태를 가진다. 현재 8776 실행 화면은 실제 backend bridge가 `/status`, `/runs`, `/ws`를 호출하면서 `idle`, `Gen -1`, `0.0%`, `backend 8776` 같은 값으로 바뀌었다.

이 때문에 DOM 구조가 비슷해도 텍스트 edge와 배치 폭이 달라져 캡처 유사도가 70점대에 머물렀다.

### 5. 백테스트와 차트 리플레이는 두 목표 사이에서 중간 상태가 되었다

백테스트/차트 리플레이는 특히 요구가 강했다.

- 기존 대시보드 대비 기능이 떨어지면 안 된다.
- 압축파일 디자인도 반영되어야 한다.

초기 production bundle 방식은 기능은 강하지만 압축파일과 시각적으로 달랐다. 이후 압축파일 `src/app.js`를 직접 활성화하자 시각 구조는 가까워졌지만, production 백테스트/리플레이의 실제 job 실행, result 분석, websocket job 상태, simulation API 깊이는 정적 프로토타입 수준으로 낮아졌다.

따라서 현재 백테스트 77.4점, 차트 리플레이 76.0점으로 가장 낮다.

### 6. “100점”이라는 표현을 서로 다른 기준에 혼용했다

서로 다른 세 점수가 있었다.

| 점수 종류 | 의미 | 현재 문제 |
|---|---|---|
| 라우트/파일 반영 점수 | 압축파일 파일이 존재하고 로드되는가 | 높음 |
| 정보구조 점수 | 페이지/탭/패널/문구가 있는가 | 89.9점 |
| 캡처/기능 대체 점수 | 실제 화면과 기존 기능을 완전 대체하는가 | 79.6점 |

초기에는 첫 번째와 두 번째 기준을 근거로 100점을 말했다. 사용자의 실제 기대는 세 번째였다. 이것이 가장 중요한 커뮤니케이션/검증 실수다.

## 페이지별 100점 미달 핵심 원인

| 페이지 | 보정 점수 | 100점 미달 원인 |
|---|---:|---|
| 조건식 AI | 81.5 | 참조 더미 run 상태와 실제 8776 run 상태 차이, 텍스트/진행률 불일치 |
| 프로세스 | 80.1 | 프로세스 로그/메타값 fixture 고정 없음, 캡처 edge 차이 |
| 히스토리 | 79.4 | run 목록과 일부 데이터가 live/fallback 상태에 영향받음 |
| 연구실 | 81.2 | 가장 가까우나 사이드 진행률/경고/텍스트 fixture 차이 존재 |
| 분석 워크벤치 | 80.2 | 후보 데이터와 요약값 fixture freeze 없음 |
| 결정 감사 | 80.7 | append-only 구조는 있으나 ledger/checklist 값이 참조와 다름 |
| 백테스트 | 77.4 | 압축파일 정적 UI와 production 실제 백테스트 기능 사이 통합 부족 |
| 차트 리플레이 | 76.0 | 압축파일 정적 UI와 production simulation/replay API 통합 부족 |

## 재발 방지 규칙

1. 100점이라고 말하기 전에 항상 `reference capture ↔ current capture` 비교를 먼저 수행한다.
2. “기능 존재”와 “시각/사용자 경험 대체” 점수를 분리해서 보고한다.
3. 리모델 기준 파일이 있으면 활성 엔트리포인트가 그 파일인지 브라우저에서 확인한다.
4. 동적 백엔드 값이 캡처 기준을 흔들면 `reference fixture mode`를 먼저 구현한다.
5. 백테스트/차트 리플레이처럼 기능 깊이가 큰 페이지는 정적 프로토타입을 그대로 쓰지 않고 production API를 zip 스타일 컴포넌트에 연결한다.
6. 최종 완료 전 8개 페이지 모두에 대해 스크린샷, DOM marker, API/WS 동작, forbidden control scan을 한 번에 검증한다.

## 이번 100점 도전의 정의

완전한 100점은 단순 픽셀 동일성이 아니라 다음 모든 조건을 만족하는 상태로 정의한다.

### A. 캡처/시각 기준

- 8개 페이지 각각 참조 캡처 대비 보정 시각 점수 95점 이상.
- 평균 보정 시각 점수 97점 이상.
- viewport 1920x1080 기준 상단 shell, primary tabs, nested tabs, 핵심 card grid, side panel 위치가 참조와 일치.
- `?demo=reference` 또는 동등한 fixture lock 모드로 참조 캡처 상태를 재현.

### B. 기능 기준

- 조건식 AI: live/run 상태, active strategy, generation table, inspector, approval dialog 유지.
- 프로세스: phase map, logs, route boundary contract, process metadata 유지.
- 히스토리: runs archive, research records, compare launcher, result detail 유지.
- 연구실: heatmap, importance, correlation, validation/holdout, context pack 유지.
- 워크벤치: candidate strip, hall of fame, monthly heatmap, review handoff 유지.
- 결정 감사: append-only ledger, human decision form, export approval 분리 유지.
- 백테스트: `/bt/*` 실제 API와 연결된 전략 선택, 실행, job progress, result, montecarlo/analysis, report path 표시.
- 차트 리플레이: `/sim/*` 실제 API와 연결된 날짜/종목/전략/재생 컨트롤, candle chart, signal log, websocket status 표시.

### C. 안전 기준

- live order, broker login, account trading, hidden production export 금지.
- Human Approval Gate와 Append-Only Audit 문구 모든 페이지에서 유지.
- Decision Audit과 final export approval 분리 유지.

### D. 검증 기준

- 8개 페이지 browser capture 재생성.
- side-by-side contact sheet 생성.
- visual score JSON 생성.
- forbidden control scan 통과.
- `pytest tests/unit/test_dashboard_remodel_static.py tests/unit/test_dashboard_remodel_baseline_contract.py -q` 통과.
- dashboard 관련 unit/API smoke 통과.
- 백테스트와 차트 리플레이는 실제 `/bt/*`, `/sim/*` endpoint 호출 evidence 포함.

## 100점 달성을 위한 구현 방향

1. **Reference Fixture Mode 추가**
   - URL: `/ui/remodel/condition?demo=reference`
   - localStorage 또는 query flag로 backend bridge가 참조 캡처용 더미 상태를 덮어쓰지 않게 한다.
   - 참조 캡처와 동일한 run/progress/backend/status 값을 고정한다.

2. **Zip UI를 유지한 채 production API adapter 연결**
   - `src/app.js`의 static `DATA`를 유지하되 `/status`, `/runs`, `/bt/*`, `/sim/*` 결과를 page별 selector로 병합한다.
   - demo/reference 모드에서는 고정 fixture, live 모드에서는 실제 API를 사용한다.

3. **백테스트 페이지 재구현**
   - 압축파일 레이아웃을 유지한다.
   - 기존 `BacktestTab` 기능 목록을 API 단위로 이식한다.
   - job run/result/analysis/report/strategy library를 모두 UI에 노출한다.

4. **차트 리플레이 페이지 재구현**
   - 압축파일 레이아웃을 유지한다.
   - `/sim/health`, `/sim/days`, `/sim/demo`, `/sim/signals`, websocket replay 상태를 결합한다.
   - candle chart와 signal log가 실제 response에서 갱신되도록 한다.

5. **자동 캡처 점수 게이트 추가**
   - reference/current 8페이지 캡처를 자동 비교한다.
   - 어떤 페이지든 보정 총점 95 미만이면 완료 금지.

## 결론

현재 상태가 100점이 아니었던 이유는 기준 혼선과 검증 순서 문제다. 기능 보존을 이유로 production bundle을 우선 유지했고, 이후 압축파일형 UI로 바꾸면서 기능 깊이가 일부 낮아졌다. 다음 라운드는 두 방향을 분리하지 않고, **압축파일 시각 구조 + production API 기능 깊이 + reference fixture 캡처 게이트**를 동시에 만족해야 100점으로 인정한다.
