# 대시보드 v5.11.0 회귀 복구 개발·릴리스 보고서

## 1. 결론

v5.10 전수감사에서 확인한 주소/버전 불일치, Backtest 결과 레이아웃 퇴행, 성과 표 의미 색상 소실, Replay 0-frame 정지, Reports 렌더러 분리 문제를 v5.11.0의 7개 단계로 복구했다. 정식 운영 주소는 `http://127.0.0.1:8770/ui/`이며 V4 shell이 계속 유일한 정식 UI다.

이 릴리스는 대시보드 신뢰성·사용성 회복 릴리스다. 연구 성능 증명이 아니므로 `performance_proved=false`를 유지한다. V3K 상태도 승인 근거 없이 변경하지 않았고 `3/6`이다.

## 2. 단계별 변경

| 단계 | PR | 핵심 결과 |
|---|---:|---|
| Foundation | #115 | frontend/backend release·build·PID 메타데이터, stale capability 경고, path 우선 canonical routing |
| Backtest/Live | #116 | 공유 `auto / wide / balanced / dense` 결과 레이아웃, 실제 열 수 표시, 진단 발견성, Live 완료 후 결과 진입점 |
| 성과 | #117 | signed return, MDD 위험, gate/status/outcome 배지, sticky header/identity, zebra·hover·numeric alignment |
| Replay | #118 | LWC 기본 엔진, Canvas 실험적 분리, 0-frame timeout, WebSocket lifecycle·OHLC·sparse geometry 복구 |
| Reports | #119 | typed script-free renderer, `executive / quant_research / research_journal`, 4개 theme, 공통 run-report adapter와 manifest metadata |
| History/Settings | #120 | History 공유 레이아웃·출처 기반 trend/scatter/regression, release/capability probes, redacted log filter/export, scoped preference reset |
| Final gates | PR-7 branch | 전체 회귀·브라우저·접근성 검증, Hall 중복 부호와 Windows jsdom gate 안정화 |

## 3. 사용자 지적 사항별 복구 상태

| 지적 | 복구 결과 | 근거 |
|---|---|---|
| 8770/8784 및 path/query 혼선 | 8770을 정식 주소로 고정하고 path가 충돌 query보다 우선하도록 정규화 | `/ui/evolution/workbench?tab=research` → `/ui/evolution/workbench`, 성과 탭 선택 |
| Backtest 강제 1열 | 사용자가 `auto / wide / balanced / dense`를 선택하고 실제 적용 열 수를 확인 | `stom_v511_result_layout`, responsive clamp |
| 결과 분석 그래프가 사라져 보임 | 진단 shell과 섹션 탐색을 항상 발견 가능하게 유지하고 데이터는 lazy load | 실제 source identity/capability가 없는 경우 명시적 unavailable |
| 성과 표 색상·가독성 | 이익/손실/보합, MDD 위험, gate/status/outcome을 색+텍스트+아이콘으로 표현 | 69개 실데이터 row, 이익 computed color `rgb(76, 214, 179)` |
| Replay가 평평한 선처럼 보임 | LWC candlestick을 신규 기본값으로 변경하고 lifecycle/slider/OHLC를 복구 | quick start 후 376봉 계약, slider 0/375 활성, 실제 candle screenshot |
| Reports 템플릿 부족 | 문서 목적이 다른 3개 template과 system/light/dark/print theme 구현 | typed blocks, inert SVG, CSP/sandbox, manifest metadata |
| History/Settings 누락 | 출처 기반 반복 분석과 운영 가시성·안전한 로그 도구 추가 | 누락값은 `—`; `/debug/logs` 인증·redaction 경계 유지 |

## 4. 최종 검증 증거

### 자동화

- `python -m pytest tests/unit/dashboard/ -q`: **886 passed** (`583.78s`).
- 최종 focused Hall/Replay/UI: **56 passed**.
- Reports focused suite: **100 passed**.
- History/Settings focused suite: **9 passed**.
- Frontend runtime JSX: **91 JSX / 541 graph files PASS**.
- 최종 app bundle: **`812714fc`**.
- 최종 CSS bundle: **`ea1ca2fb`**.
- `python scripts/verify_nonrelease_sync.py`: **PASS**.
- `git diff --check`: **PASS**.

### 브라우저·상호작용

- 7 viewport × 7 canonical routes = **49/49**, horizontal overflow 0, empty root 0, render error boundary 0.
- 접근성 matrix: **252/252 passed**, serious/critical 0, runtime/axe errors 0.
- Hall: 실제 69 rows, 양수 의미색 확인, `++` 중복 부호 0.
- Replay: `최대 상승일` quick start, LWC/min, bounded wait 안에 5/376봉 수신, slider enabled `5/375`, OHLC `79,300–82,200`, screenshot build `812714fc`.
- 증거: `artifacts/v511_final_interaction_gate.json`, `artifacts/v511_accessibility_gate.json`, `artifacts/v511_replay_lwc_lifecycle.png`.

## 5. 보존한 안전 경계

- Reports CSP/sandbox와 script-free publication을 유지한다.
- `/debug/logs`는 인증된 same-origin GET과 redaction을 유지하며 export도 이미 가려진 현재 행만 사용한다.
- 누락 데이터는 `—` 또는 unavailable로 표시하며 demo/0/inference로 채우지 않는다.
- protected DB/export, broker, human approval, V3K gate를 변경하지 않는다.
- 기존 legacy 보고서는 근거 없이 덮어쓰지 않는다.

## 6. 잔여 제한

- 현재 데이터셋의 Backtest 최근 목록에는 openable 완료 artifact가 없어, 최종 브라우저 gate에서 새 실전 Backtest를 생성하지 않았다. renderer·layout·identity 계약은 unit/integration gate로 검증했고 누락 artifact는 fail-closed로 표시된다.
- UI scale, 접근성, Replay 상호작용 증거는 투자 수익성 또는 운영 성과 증거가 아니다.
- 새로운 대시보드 점수는 별도 점수 부풀리기 없이 릴리스 gate 결과로만 평가한다.
