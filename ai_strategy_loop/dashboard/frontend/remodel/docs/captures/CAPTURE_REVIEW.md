# STOM AI 대시보드 실행 캡처 및 점검 리포트

## 실행/캡처 조건

- 대상: `stom-ai-dashboard-frontend` 정적 프론트엔드
- 렌더링 엔진: Chromium Headless
- 캡처 뷰포트: `1920 × 1080`
- 캡처 방식: 실제 DOM 렌더링 후 탭 버튼 클릭 순회
- 캡처 파일: 일반 뷰포트 캡처 8장 + Full-page 캡처 8장 + 전체 탭 contact sheet 1장
- JS 문법 검사: `npm run check:js` 통과
- 콘솔 오류: 0건
- 페이지 오류: 0건

## 캡처 목록 및 점검 결과

| # | 탭 | 화면 캡처 | Full-page 캡처 | 상태 | 점검 요약 |
|---:|---|---|---|---|---|
| 1 | 조건식 AI / 조건식 AI | `01_condition_ai_overview.png` | `01_condition_ai_overview_full.png` | PASS | 라이브 세대, 세대 테이블, Winner/Approval, 전략 인스펙터, 분석 패널 확인 |
| 2 | 조건식 AI / 프로세스 | `02_process.png` | `02_process_full.png` | PASS | Generation → Backtest → Scoring → Autopsy → Repeat 맵, 로그, 카탈로그 확인 |
| 3 | 조건식 AI / 히스토리 | `03_history.png` | `03_history_full.png` | PASS | Run/gen archive, Research Records, ResultDetail, Compare, Lineage Search 확인 |
| 4 | 조건식 AI / 연구실 | `04_lab.png` | `04_lab_full.png` | PASS | Edge Ratio, 변수 중요도, 상관관계, 변수 조합, Holdout 검증 확인 |
| 5 | 조건식 AI / 분석 워크벤치 | `05_workbench.png` | `05_workbench_full.png` | PASS | Hall of Fame, 후보 심층 분석, Evidence Notes, 리뷰 큐, Handoff 확인 |
| 6 | 조건식 AI / 결정 감사 | `06_decision_audit.png` | `06_decision_audit_full.png` | PASS | Append-Only Ledger, PROMOTE 체크리스트, OOS CI, Human Decision, 결정 히스토리 확인 |
| 7 | 백테스트 | `07_backtest.png` | `07_backtest_full.png` | PASS | Demo Mode, 실행 파라미터, 최적화/WFO/스윕, 코드 편집, 결과 분석 확인 |
| 8 | 차트 리플레이 | `08_chart_replay.png` | `08_chart_replay_full.png` | PASS | Tick/Min 소스, 재생 컨트롤, 리플레이 차트, 신호 로그, WS 상태 확인 |

## 자동 점검 결과

| 항목 | 결과 |
|---|---|
| 주요 탭 렌더링 | PASS |
| 필수 텍스트/섹션 존재 검사 | PASS |
| 콘솔 이벤트 | 0건 |
| Page error | 0건 |
| Global shell 일관성 | PASS |
| REST/WebSocket local contract 표기 | PASS |
| Human Approval Gate 표기 | PASS |
| Append-Only Audit 표기 | PASS |
| 실거래/주문/브로커/계좌 제어 미노출 | PASS |

## 발견 및 조치 사항

1. 히스토리 화면의 계보 검색 패널이 한국어 `라인리지 검색`으로만 표기되어 자동 필수 텍스트 검사에서 `Lineage` 키워드가 한 차례 누락되었습니다.  
   → `라인리지 검색 (Lineage Search)`로 수정 후 재캡처했고, 최종 결과는 PASS입니다.

2. 데이터 밀도가 높은 화면들은 1920×1080 기준으로 세로 스크롤이 발생합니다.  
   → 일반 캡처와 Full-page 캡처를 모두 제공했습니다.

3. 대시보드가 연구/백테스트/리플레이/감사 목적임을 나타내는 안전 고지와 Human Approval Gate는 전역 푸터와 관련 패널에서 확인됩니다.

## 권장 후속 개선

- 긴 화면에서 상단 탭/Run 상태 바를 sticky 처리하면 스크롤 중 문맥 유지가 더 좋아집니다.
- 캡처 자동화 스크립트를 CI에 연결해 탭별 스냅샷 회귀 테스트로 사용할 수 있습니다.
- 실제 FastAPI/WebSocket 연결 시 더미 데이터와 실제 payload schema를 비교하는 contract test를 추가하는 것이 좋습니다.
