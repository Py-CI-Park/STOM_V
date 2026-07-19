# V5 대시보드 전면 개편 완료 보고서

- 기준 계획: `docs/web_dashboard_expansion/2026-07-18_v5_series_dashboard_overhaul_master_plan.md`
- 승인 기준 커밋: `2268b709751e109e862192653d91e7e409e1d0f2`
- 실행 브랜치: `feature/dashboard-v5-overhaul-20260718`
- 최종 프런트엔드 번들: `app.js?v=42883881`
- 적용 범위: V5.P0 ~ V5.7 및 실행 중 검토에서 추가된 차단 해결 목표
- 데이터 안전: 사용자 미추적 파일과 보호된 런타임·거래 데이터는 수정·삭제·스테이징하지 않음

## 1. 최종 판정

V5 계획의 정본 계약, Live 연구 흐름, 독립 Backtest, History 연구 정체성, 6개 목적지 IA, Reports/Wiki, sealed P4 Catalog를 구현했다. 각 단계는 단순 화면 존재가 아니라 집중 테스트, 전체 dashboard 회귀, Track Z 회귀, 브라우저 자동화, 다중 해상도 화면 근거, cleanup/architecture/red-team 검토를 통과한 뒤 durable Ultragoal ledger에 체크포인트했다.

| 영역 | 최종 상태 | 핵심 결과 |
|---|---:|---|
| V5.P0 계약·소유권 | 완료 | 6개 정본 목적지와 owner matrix 단일화, 레거시 경로 fail-closed 및 rollback-only 보존 |
| V5.0~V5.2 Live | 완료 | 울트라와이드 3열 밀도, 단계 stepper, follow-live/pin, 현재 조건식·엔진·분석 근거 표시 |
| V5.3 Backtest | 완료 | 기존 `/bt` 실행 경계를 재사용한 gap-only 패리티, 결과·거래·Monte Carlo·A/B 시각화 |
| V5.4 History | 완료 | 안정 연구 ID, 취소/세대 guard, 조건·평가·부검·holdout·문서·커밋·거버넌스 통합 |
| V5.5 IA | 완료 | Live/Backtest/Replay/History/성과/Reports 6개 목적지, Audit/Lab/Context/Alpha/Catalog 정상 레일 제거 |
| V5.6 Reports/Wiki | 완료 | manual-offline 원자적 writer, manifest/hash/trust/stale, sandbox/CSP, byte-preserving 읽기 전용 Wiki |
| V5.7 P4 Catalog | 완료 | env-only mode=ro rdc-1 API 4개, 동적 cells 파티션, V1~V5 정본 뷰, 정직한 B1 빈 골격 |

## 2. 사용자 피드백 반영표

| 원래 문제 | 반영 내용 | 검증 결과 |
|---|---|---|
| Live 그래프가 지나치게 커서 3440×1440에서 여러 정보를 볼 수 없음 | hero 높이 제한, 3열 그래프 배치, 카드 밀도·타이포·사이드 패널 재조정 | 1920/2560/3440에서 가로 overflow 0; 3440 화면에서 주요 그래프 동시 표시 |
| 세대·프로세스가 흩어지고 현재 단계가 불명확 | 생성→백테스트→채점→부검 stepper, follow-live와 사용자 pin/reset, terminal precedence 추가 | 키보드·pin/reset·terminal·drawer focus 자동화 통과 |
| 단계별 시간·차단 사유·최신 로그가 단순 텍스트 | compact workflow evidence와 단계 상태에 통합 | running/complete fixture와 DOM 계약 검증 |
| 백테스트 조건식과 분석 결과가 약함 | 독립 Backtest의 조건 편집, 결과 라이브러리, 핵심 지표, 거래 상세, 차트·분포·A/B/portfolio 보강 | Backtest 집중 241개 테스트 및 브라우저 근거 통과 |
| History가 연구 전체를 체계적으로 관리하지 못함 | governed research identity, legacy archive 분리, 선택·요약·Compare·세부 근거 통합 | race/malformed/cursor/keyboard/path-leak 적대 검증 통과 |
| Audit/Lab/Context/Alpha/Catalog가 중복 탭 | 거버넌스는 History, 분석은 Live/History, 성과는 Hall-of-Fame, Context는 개발자 drawer, Catalog는 Reports prototype으로 이동 | 정상 레일은 정확히 6개; back/forward/localStorage/rollback 계약 통과 |
| 연구 HTML 보고서와 Wiki가 부족 | 구조화 manifest, 연구/단계별 report, sandbox iframe, 읽기 전용 Wiki 검색·태그·연혁·연관 문서 | scriptless/CSP/path/symlink/hash/byte/source mutation 검증 통과 |
| 연결 끊김·재연결 표시가 반복 | BASE 소유권과 stale response guard, 실제 서버 연결 상태 표시 경계 정리 | 최종 21개 페이지×viewport 브라우저 행에서 모두 `백엔드 연결됨 · v2` 확인 |

## 3. 페이지별 최종 상태

| 목적지 | 소유 기능 | 1920×1080 | 2560×1440 | 3440×1440 | 가로 overflow |
|---|---|---:|---:|---:|---:|
| Live | 실시간 연구, 단계, 조건식·엔진·분석 근거 | 통과 | 통과 | 통과 | 0 |
| Backtest | 전략 실행·결과·상세 분석 | 통과 | 통과 | 통과 | 0 |
| Replay | 시뮬레이션·차트 replay | 통과 | 통과 | 통과 | 0 |
| History | 아카이브·정본 연구 상세·비교·Wiki/거버넌스 | 통과 | 통과 | 통과 | 0 |
| 성과 | 장기 기준과 Hall-of-Fame 전용 | 통과 | 통과 | 통과 | 0 |
| Reports | 구조화 HTML report와 Research Wiki | 통과 | 통과 | 통과 | 0 |
| Catalog prototype | Reports 소유 sealed P4 조회 | 통과 | 통과 | 통과 | 0 |

최종 브라우저 행은 각 페이지에서 동일한 6개 레일, 올바른 canonical URL, 현재 페이지 heading, `백엔드 연결됨 · v2`, 가로 overflow 0을 확인했다. History는 근거 전체를 제공하므로 세로 길이가 길지만 가로 잘림은 없고, 정본/legacy 영역을 명시적으로 구분한다.

## 4. 구현 상세

### 4.1 Live 연구 UX

- 대형 단일 그래프 중심 구성을 해체하고 울트라와이드에서 핵심 그래프를 병렬 배치했다.
- 단계 stepper가 생성, 백테스트, 채점, 부검 상태를 표시한다.
- 자동 단계 추적과 사용자의 고정 관찰을 분리해 연구 중 자동 이동과 수동 검토가 충돌하지 않는다.
- 현재 조건식, 엔진 설정, 분석 payload의 source/freshness/identity를 fail-closed로 표시한다.
- terminal 상태가 running 표시보다 우선하도록 계약을 봉인했다.

### 4.2 Backtest gap-only 패리티

- 새로운 병렬 엔진을 만들지 않고 기존 `/bt` runner와 보안·수동 실행 경계를 재사용했다.
- 전략 선택/편집, 기간·시간·자본·tick, 실행/취소, 결과 library와 세부 결과를 연결했다.
- 거래 상세, 누적 손익, 손익 분포, Monte Carlo, A/B, portfolio 근거를 실제 결과 정체성으로 묶었다.
- primary/detail 응답 경쟁과 tick/minute 단위 혼동을 차단했다.

### 4.3 History 연구 정체성

- campaign과 loop run의 안정 ID를 분리하고 선택 세대·취소·owner guard를 적용했다.
- 조건식, 평가, autopsy, holdout, A/B, 문서, 커밋, governance 상태를 complete/partial/missing/conflict로 표시한다.
- legacy archive Compare와 governed research selection은 같은 것으로 위장하지 않는다.
- 절대 경로, 잘못된 owner 메타데이터, malformed envelope, stale response가 UI를 오염시키지 않도록 fail-closed 처리했다.

### 4.4 6개 목적지 IA

- 정상 레일은 Live, Backtest, Replay, History, 성과, Reports만 유지한다.
- Audit은 History 거버넌스로 흡수했고 Lab 분석은 Live/History로 이동했다.
- 성과는 장기 기준과 Hall-of-Fame만 소유한다.
- Context는 우측 개발자 drawer로 이동했다.
- Alpha와 Catalog는 정상 레일이 아니라 명시적 prototype/rollback 경로로만 남긴다.
- `/ui/evolution/catalog`은 Reports 소유 `?prototype=catalog`로 canonicalize된다.

### 4.5 Reports와 Wiki

- writer는 명시적 manual/offline 실행만 허용하고 staging 후 원자적으로 교체한다.
- report manifest는 stable research/step ID, HTML/source SHA-256, byte 수, trust, missing, stale, allowlisted links를 포함한다.
- report HTML은 scriptless이며 `/reports/view`의 CSP `default-src 'none'`과 빈 sandbox iframe으로 이중 격리한다.
- 기존 unmanaged report는 보존하고 관리 대상 report만 교체한다.
- Wiki는 원문 Markdown을 변경하지 않고 index/sidecar 메타데이터로 검색, 태그, category, chronology, related links를 제공한다.

### 4.6 sealed P4 Catalog

- `STOM_RESEARCH_ASSETS_DB`의 절대 경로만 사용하며 기본 DB 경로가 없다.
- SQLite는 요청마다 `mode=ro`로 열고 schema/mtime을 검증한다.
- 정본 API는 `/research/assets`, `/research/judgments`, `/research/cells`, `/research/clauses` 네 개뿐이다.
- `/research/summary`와 서버 `COUNT/AVG/SUM/GROUP BY` 집계를 제거했다.
- cells 파티션은 DB가 반환한 `allowed[]`에서 동적으로 발견하며 UI가 존재하지 않는 source를 추정하지 않는다.
- V1 연구 연혁, V2 함정 지도, V3 절 실험실, V4 표본/출구 은행, V5 B1 빈 골격을 제공한다.
- B1은 운용 개시/U-4/data-vessel 근거 전에는 성공 수치나 색상을 만들지 않는다.

## 5. 검증 근거

| 검증 | 최종 결과 |
|---|---:|
| dashboard 전체 단위/계약 테스트 | 814 passed |
| Track Z 통합 harness | 15 passed |
| G007 카탈로그/API/UI 집중 테스트 | 50 passed, repair 후 31 passed |
| G006 Reports/manifest 집중 테스트 | 22 passed |
| Web TypeScript + runtime JSX | PASS, 89 JSX / 537 graph files |
| 최종 번들 build | PASS, `app.js?v=42883881` |
| 브라우저 페이지×viewport 행 | 7페이지 × 3 viewport = 21행 통과 |
| 가로 overflow | 전 행 0 |
| 정상 레일 | 전 행 6개 고정 |
| Catalog legacy summary | 404 확인 |
| Catalog DB 쓰기 | `mode=ro` 차단 테스트 통과 |
| protected runtime/trading paths | tracked 변경 없음 |

단계별 검증 영수증과 blocker 해결 이력은 현재 세션의 Ultragoal `goals.json` 및 `ledger.jsonl`에 보존한다. 브라우저 transcript, test report, screenshot matrix는 `artifacts/`의 실행 근거이며 제품 소스 커밋에는 포함하지 않는다.

## 6. 주요 커밋 계보

| 커밋 | 내용 |
|---|---|
| `258387d1`, `00623850` | V5.P0 owner/legacy 경로 정리 |
| `17b0aff8` | Live V5.0~V5.2 검증 차단 해결 |
| `366f6de9` | Backtest V5.3 gap-only 패리티 |
| `42366d74` | V5.5 IA·BASE·Reports/History 경계 봉인 |
| `02e2718`, `62a13ffd` | History V5.4 최종 정체성/QA 차단 해결 |
| `7a40bc38` | Reports/Wiki V5.6 manifest·보고서 corpus 봉인 |
| `c8268070` | P4 rdc-1 API와 5개 Catalog 뷰 |
| `561297a3` | Catalog canonical deep link |
| `5082e6fe` | Catalog cells 파티션 동적 탐색 |

## 7. 운영 경계와 잔여 사항

- Catalog와 Alpha는 정본 정상 레일로 승격되지 않았다. Catalog는 Reports 소유 prototype이며 승인된 V5.7 읽기 전용 범위만 제공한다.
- B1은 운용 근거가 없으므로 의도적으로 빈 골격이다. 이것은 미완성이 아니라 거짓 준비 상태를 막는 계약이다.
- V3K live gate, broker 연결, 주문/승인, protected DB cutover는 이번 V5 dashboard 작업 범위 밖이며 기존 default-OFF 및 승인 경계를 유지한다.
- 생성된 브라우저·테스트 artifact와 합성 Catalog fixture는 제품 커밋 대상이 아니다.

## 8. 완료 기준 체크리스트

- [x] 승인 기준 커밋에서 별도 브랜치 생성
- [x] V5.P0~V5.7 구현
- [x] 실행 중 발견한 모든 blocking review story 해결 또는 명시적 successor로 supersede
- [x] 6개 정상 목적지와 소유권 단일화
- [x] 1920×1080, 2560×1440, 3440×1440 브라우저 검증
- [x] 번들·manifest 재생성
- [x] 집중/전체/Track Z 회귀 통과
- [x] cleanup, architecture, executor red-team 검토
- [x] 사용자·미추적·protected runtime/trading 데이터 보존
- [x] 한국어 커밋과 명시적 staging
