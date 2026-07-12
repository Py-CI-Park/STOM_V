# STOM AI · 조건식 AI 연구 대시보드 Frontend Prototype

Korean quant-trading research/control-plane dashboard frontend prototype. 이 패키지는 생성된 대시보드 이미지 콘셉트와 제공된 STOM 전략 문서를 바탕으로, 통일된 다크 퀀트 터미널 테마와 전체 탭 정보구조를 정적 프론트엔드로 구현한 산출물입니다.

> 중요한 범위: 연구/백테스트/감사/리플레이 제어면 전용입니다. 실거래 주문, 브로커 로그인, 계좌/자산 연동, 자동 프로덕션 Export UI는 포함하지 않습니다.

## 빠른 실행

### 방법 1: 파일 직접 열기

```text
index.html
```

브라우저에서 `index.html`을 직접 열면 더미 데이터 기반 대시보드가 동작합니다. `sample.html`은 `index.html`로 이동하는 테스트용 진입 파일입니다.

### 방법 2: 로컬 정적 서버

```bash
python -m http.server 8080
# 브라우저에서 http://localhost:8080 접속
```

또는 Node.js가 있으면:

```bash
npm run serve
```

## 기술 스택

- HTML5 단일 페이지 애플리케이션
- Vanilla JavaScript, 외부 런타임 의존성 없음
- CSS Custom Properties 기반 테마 토큰
- SVG 기반 내장 차트/캔들/히트맵 렌더링
- 오프라인 더미 데이터: `src/data.js`, `data/stom-dummy-data.json`
- 빌드 도구 없음: Codex AI Agent가 React/Vite/Next.js 등으로 쉽게 이식 가능

## 파일 구조

```text
stom-ai-dashboard-frontend/
├── index.html                       # 실제 실행 진입점
├── sample.html                      # 샘플 실행 HTML, index.html로 이동
├── package.json                     # 정적 서버/검증 스크립트
├── README.md                        # 현재 문서
├── CODEX_AGENT_BRIEF.md             # Codex AI Agent 적용 지시서
├── styles/
│   └── theme.css                    # 통일 테마, 레이아웃, 컴포넌트 스타일
├── src/
│   ├── data.js                      # 브라우저용 더미 데이터
│   └── app.js                       # 전체 탭/컴포넌트 렌더링 로직
├── data/
│   └── stom-dummy-data.json         # API 대체용 JSON 더미 데이터
├── docs/
│   ├── ARCHITECTURE.md              # 구조/컴포넌트 설계
│   ├── DATA_CONTRACT.md             # FastAPI/WebSocket 연동 계약 초안
│   ├── UI_IMPLEMENTATION_SPEC.md    # 탭별 구현 사양
│   ├── TAB_CHECKLIST.md             # 보존 기능 체크리스트
│   ├── design-references/           # 생성 이미지 레퍼런스 PNG
│   └── source-context/              # 제공된 STOM 전략/분석 원문 문서
├── samples/
│   └── sample-runbook.md            # 더미 데이터로 점검하는 샘플 시나리오
└── tests/
    ├── smoke-test.html              # 브라우저 수동 스모크 테스트
    └── CHECKLIST.md                 # QA 체크리스트
```

## 구현된 탭

### Top-level

1. `조건식 AI`
2. `백테스트`
3. `차트 리플레이`

### 조건식 AI Nested Tabs

1. `조건식 AI`
2. `프로세스`
3. `히스토리`
4. `연구실`
5. `분석 워크벤치`
6. `결정 감사`

각 탭은 독립적인 대시보드 화면으로 구현되어 있으며, 공통 Global Shell, 상태 배지, REST/WebSocket 표시, Run Status, LIVE/ARCHIVE, 세대 진행률, Provider, Timeframe, run_id, Start/Stop, 설정 모달, Human Approval Gate, Append-Only Audit 컨셉을 공유합니다.

## 더미 데이터

`data/stom-dummy-data.json`은 API 응답 대체 데이터입니다. 실제 백엔드 연동 시 아래 순서로 교체하세요.

1. `src/data.js`의 `window.STOM_DATA` 초기값을 REST fetch 결과로 대체합니다.
2. WebSocket state stream을 연결해 run status, progress, generation table, logs를 갱신합니다.
3. Export/Decision/Audit 같은 변경성 액션은 실제 API 연결 전까지 disabled 상태로 유지합니다.

## 안전/계약 원칙

- No Live Order
- No Broker Login
- No Account Trading
- Research Only
- Human Approval Gate Required
- Decision Audit is Append-Only
- Backtest/research analysis is read-only unless explicitly saving strategy or recording decision
- Final strategy export approval is separate from Decision Audit

## 권장 다음 단계

1. `src/app.js`를 탭별 컴포넌트 파일로 분리합니다.
2. `data/stom-dummy-data.json`을 FastAPI 응답 스키마와 1:1로 맞춥니다.
3. WebSocket 이벤트 타입을 정의해 live run 상태, process edge, logs, replay cursor를 갱신합니다.
4. 코드 에디터는 Monaco/CodeMirror로 교체할 수 있습니다.
5. 차트는 필요 시 Lightweight Charts, ECharts, Plotly, D3 중 하나로 교체할 수 있습니다.

## 브라우저 호환성

- Chrome/Edge 최신 버전 권장
- Safari/Firefox에서도 정적 렌더링 가능
- 외부 CDN 미사용
