# UXR-P6 — Backtest gap: 웹 구현 인벤토리 + parity matrix (§10-2)

- 작성: 2026-07-18 · 브랜치: `uxr-p6-backtest`
- 원칙: **이식 아님 — 현 웹 구현 inventory → python GUI parity → 결손만 보강.**
  검토 §3(P5 "port" 오진단 High) 반영: 현 웹 백테스트는 이미 광범위하다.

## 1. 현 웹 백테스트 표면 (실측 인벤토리)

### 컴포넌트 (12 bt-*.jsx)
| 파일 | 역할 |
|---|---|
| bt-tab-root.jsx | 탭 루트·health·전략명 목록 오케스트레이션 |
| bt-tab-run.jsx | 실행 스펙(전략/기간)·`/bt/run`·job 진행·취소·메타 |
| bt-tab-library.jsx | 전략 CRUD(저장/삭제/검증)·변수 추출 |
| bt-tab-analysis.jsx | overlay·A/B·portfolio 분석 |
| bt-tab-mode-results.jsx | 모드별 결과 |
| bt-result-area.jsx | 결과 영역(메트릭·차트 호스트) |
| bt-equity-charts.jsx | 누적수익/낙폭 곡선 |
| bt-distribution-charts.jsx | 분포(손익 히스토그램 등) |
| bt-stat-panels.jsx | 지표 패널 |
| bt-gui-parity.jsx | **GUI parity 뷰(이미 존재)** |
| bt-chart-utils / bt-tab-utils | 공용 유틸 |

### 엔드포인트 (13 `/bt/*`)
- 읽기: `/bt/health` · `/bt/data_range` · `/bt/jobs` · `/bt/job` · `/bt/strategies`.
- Mutation(capability 게이트): `POST /bt/run`·`/bt/job/cancel`·`/bt/job/meta`·`/bt/portfolio`(SAFE_BACKTEST); `POST /bt/strategy`·`/bt/strategy/delete`·`/bt/strategy/validate`·`/bt/extract_vars`(STRATEGY_WRITE).
- Monte Carlo·portfolio 결합·A/B overlay 이미 구현.

## 2. Mutation 경계 (§10-4 — 이미 준수 확인)

- 모든 실행/전략 mutation은 `security_capabilities.py: HTTP_CAPABILITIES`로 capability 분류 + 세션 + origin 게이트.
- 취소는 `_confirmBacktestDanger`(v4-backtest.jsx)로 명시 확인 다이얼로그.
- demo 모드에서 mutation 전면 inert(`if (isDemo) return`).
- **결론: mutation 경계는 신규 설계 불필요 — 기존 계약 유지.**

## 3. 확정 field-level parity matrix (PyQt ↔ 웹)

대조 기준은 PyQt 일반 백테스트(`ui/set_stg_unified_tap.py`, `ui/ui_button_clicked_editer_unified.py`), 공식 CLI(`cli/config.py`), 기존 웹 `/bt/*` 소유자다. 최적화·GA·BackFinder·WFO·sweep 확장은 V5.3 범위가 아니다.

| 필드·표면 | PyQt/공식 계약 | 기존 웹 소유자 | 판정 | V5.3 처리 |
|---|---|---|---|---|
| 시장군 선택 | PyQt는 주식·코인·선물 화면을 가짐 | 공식 웹 CLI runner는 국내주식 경로 | 해당 없음 | 시장 선택기·브로커 경로를 추가하지 않음 |
| 일반 백테스트 모드 | 백테스트 버튼 | `POST /bt/run`, `mode=backtest` | 완료 | 기존 경로 유지 |
| 매수·매도 전략 선택/코드 | PyQt 편집기·DB | `/bt/strategies`, `/bt/strategy*` | 완료 | STRATEGY_WRITE와 수동 저장 유지 |
| 시작·종료일 | YYYYMMDD | `/bt/run.start/end`, `/bt/data_range` | 완료 | 기존 검증 유지 |
| 장중 시작·종료시간 | PyQt 매 실행 입력, CLI `--start-time/--end-time` | 기존 run adapter에서 누락 | **결손** | 기존 `/bt/run`→job spec→CLI argv에만 추가 |
| 종목당 투입금 | PyQt 매 실행 입력, CLI `--betting`(백만원) | 기존 run adapter에서 누락 | **결손** | 양수 검증 후 기존 argv에 추가 |
| 평균 계산 틱 | PyQt 매 실행 입력, CLI `--avg-time` | 기존 run adapter에서 누락 | **결손** | 양의 정수/쉼표 목록 검증 후 기존 argv에 추가 |
| tick/min 시간단위 | PyQt 설정에서 유도 | `/bt/run.timeframe` | 완료 | 두 정본 값 유지 |
| 데이터 분류·한 종목 | 공식 CLI `--divid-mode/--one-code` | `bt-tab-run.jsx`, `/bt/run` | 완료 | `05d8cf0f`에서 보강됨; 재구현하지 않음 |
| 엔진 수 | PyQt `back_count` | `/bt/run.engines`→CLI `--engines` | 완료 | 1–16 경계 유지 |
| 상시 엔진 준비/재시작 | PyQt 전용 상주 엔진 | 웹은 실행마다 CLI 엔진 생성 | 해당 없음 | 상주 엔진·준비 endpoint를 만들지 않음 |
| 실행·취소 | 명시적 사용자 동작 | `/bt/run`, `/bt/job/cancel` | 완료 | demo inert, SAFE_BACKTEST, 취소 확인 유지 |
| 진행·이력·로그 | PyQt backlog | `/bt/jobs`, `/bt/job`, `/bt/ws_job` | 완료/제한 | 단일 publisher 유지; 연결 상태를 엔진 준비로 과장하지 않음 |
| 결과 상태·재시도 | 결과/상세 화면 | `/bt/result` | 완료 | loading/error/no-trades를 정상 상태로 유지 |
| 핵심 6지표 | PyQt 결과 요약 | `BtResultArea` | 완료 | 기존 카드 유지 |
| 추가 결과 지표 | PyQt 일평균·필요자금·보유·승패·MDD금액·TPI 등 | 서버가 이미 반환하지만 화면 누락 | **결손** | 서버값 우선 compact strip, 결측 `—`, 클라이언트 재계산 금지 |
| 거래별 상세 | PyQt `columns_bt` 14필드 | CSV는 존재하나 웹 표 없음 | **결손** | 기존 `/bt/result`에만 최대 100행 페이지 envelope와 지연 로드 표 추가 |
| HTML 보고서 | PyQt 그래프/상세 | `/bt/report` | 완료 | 별도 writer/route 금지 |
| equity·분포·히트맵·MDD·MAE/MFE·청산 | PyQt PlotShow | 기존 분석 컴포넌트 | 완료 | 기존 서버 분석 재사용 |
| GUI parity 6그래프 | PyQt 결과 이미지 | `bt-gui-parity.jsx` | 완료 | 기존 결과 재사용 |
| 지수 비교 | PyQt 외부 지수 선택 가능 | 공식 결과 CSV에 지수 계열 없음 | 해당 없음 | 네트워크/yfinance/합성 데이터 금지 |
| Monte Carlo·A/B·portfolio | 웹 확장 기능 | 기존 `/bt/analysis/*`, `/bt/compare`, `/bt/portfolio` | 완료 | 범위 확장 없음 |

## 4. 구현 계약과 예산

- 실행 입력 기본값은 공식 CLI와 동일한 `090000`, `152800`, `1`(백만원), `60`이다.
- 네 입력은 일반 백테스트에서만 기존 `/bt/run`에 포함하며, 같은 조건 재실행에도 보존한다.
- 결과의 `run_context`는 `start/end/start_time/end_time/timeframe/betting/avg_time/engines/divid_mode/one_code`만 허용한다. DB override나 파일 경로는 노출하지 않는다.
- 거래 상세는 기존 `/bt/result` 소유자에서만 제공한다. 기본 `detail_limit=0`, 최대 100행, 원본 CSV 순서, 명시적 empty/missing/error 상태를 사용한다.
- 상세 UI는 접힘 기본·지연 로드·이전/다음·재시도·요청 취소/세대 guard를 갖고, 페이지 이동으로 차트 분석을 다시 계산하지 않는다.
- 모든 mutation은 명시적 사용자 동작으로만 실행한다. demo inert, capability, exact-Origin/session, body bound, 취소 확인을 약화하지 않는다.
- `/bt/run-v2`, `/bt/trades`, 별도 report/result store, 상주 엔진, 두 번째 progress publisher를 만들지 않는다.

## 5. 판정

- **기존 구조:** 유지. 실행·결과·보고·분석 소유권은 이미 올바르다.
- **확인된 결손:** 실행 입력 4개, 추가 서버 지표 표시, 제한된 거래 상세, 연결/엔진 문구 정직성.
- **완료 조건:** 위 결손의 focused test, 현재 번들, 실제 브라우저의 수동 실행 경계·결과 상세·반응형 표시 근거가 모두 같은 커밋을 가리켜야 한다.
- **금지:** 추측성 대규모 이식, 새 실행/결과 경로, 클라이언트 금융 계산, 라이브 브로커·엔진 수명주기 확장.

## 6. 다음(P7 History·Reports)

- History stable identity·join·pagination(§10-10) + Reports 보안 계약(iframe sandbox/CSP/traversal·inline JS 금지, §10-5). P7은 보안 설계가 선행.
