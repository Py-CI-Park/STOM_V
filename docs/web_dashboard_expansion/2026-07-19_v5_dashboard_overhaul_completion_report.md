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

## 9. 실행 성과 요약

### 9.1 정량 성과

| 항목 | 결과 |
|---|---:|
| 승인 계획 범위 | V5.P0~V5.7 전체 |
| Durable Ultragoal 필수 목표 | 8/8 완료 |
| 실행 중 추가된 차단 해결 목표 | 모두 완료 또는 검증된 successor로 supersede |
| 최종 실패·차단·review-blocked 목표 | 0 |
| 최종 커밋 | `0d790306cf721625264ddd72a5c2ec2926af56f3` |
| 최종 프런트엔드 번들 | `app.js?v=42883881` |
| 전체 dashboard 회귀 | 814 passed |
| Track Z 회귀 | 15 passed |
| 브라우저 검증 조합 | 7개 화면 × 3개 해상도 = 21 |
| 수평 overflow | 21/21 모두 0 |
| AI slop cleanup blocking | 0 |
| 최종 architecture/product/code 상태 | CLEAR / CLEAR / CLEAR |
| 최종 검토 권고 | APPROVE |
| Ultragoal 실행 경과시간 | 약 19시간 50분 |
| Goal 모드 누적 사용량 | 6,005,535 tokens |

경과시간은 최초 durable goal 생성 시각인 2026-07-18 14:17경부터 final aggregate receipt가 생성된 2026-07-19 10:07경까지의 벽시계 기준이다. 이 시간에는 구현, blocker 발견과 수정, 번들 재생성, 전체 회귀, 브라우저 자동화, 다중 해상도 화면 캡처, cleanup, architecture 및 executor red-team 검토가 모두 포함된다.

### 9.2 종합 평가

| 평가 영역 | 배점 | 획득 | 근거 |
|---|---:|---:|---|
| 계획 구현 완성도 | 25 | 25 | V5.P0~V5.7과 successor blocker story 완료 |
| 사용자 목적 충족 | 20 | 20 | 연구 진행·데이터·결과를 한 화면에서 관찰하고 탐색하는 흐름 구축 |
| 울트라와이드 UX/UI | 15 | 15 | 1920/2560/3440 전 화면 overflow 0, Live 그래프 병렬 배치 |
| 기능·데이터 계약 | 15 | 15 | Backtest, History, Reports/Wiki, sealed P4 계약 충족 |
| 안정성·회귀 검증 | 15 | 15 | dashboard 814, Track Z 15, 브라우저 21행 통과 |
| 보안·운영 경계 | 5 | 5 | sandbox/CSP, path guard, env-only mode=ro, protected path 보존 |
| 유지보수 정돈 | 5 | 3 | 정상 동작과 무관한 미사용 `audit` 아이콘 분기 1건 advisory |
| **합계** | **100** | **98** | **운영 통합 승인 수준** |

98점은 기능 결함 때문에 감점한 점수가 아니다. 최종 cleaner가 정상 레일에서 도달할 수 없는 레거시 `audit` 아이콘 switch 분기 하나를 낮은 우선순위 advisory로 식별했기 때문이다. 해당 분기는 사용자 동작, 6목적지 IA, 라우팅, 접근성 또는 보안 결과에 영향을 주지 않는다.

## 10. 공통 대시보드 Shell UX/UI

### 10.1 상단 헤더

| UI 요소 | 기능 | UX 계약 |
|---|---|---|
| 제품명 `조건식 AI 연구 터미널` | 현재 애플리케이션 식별 | 모든 목적지에서 동일하게 유지 |
| 버전·contract 표시 | 현재 V4 shell과 contract 세대 표시 | 작은 보조 텍스트지만 제품명과 분리해 판독 가능 |
| Build badge | 실제 로드된 프런트엔드 bundle 식별 | 최종 `42883881`과 브라우저 transcript를 일치시킴 |
| 실거래·브로커 상태 | 거래/브로커 비활성 경계 표시 | 연구 화면을 실거래 화면으로 오인하지 않도록 유지 |
| HUMAN GATE | 사람 승인 필요 경계 표시 | 자동 승격·주문으로 오인하지 않도록 지속 노출 |
| APPEND-ONLY 감사 | 감사 기록의 변경 불가 성격 표시 | 연구 결과가 임의 교체된다는 인상을 방지 |
| BASE 입력·적용 | API 기준 주소 전환 | 전환 세대와 owner guard를 적용해 이전 BASE 응답을 폐기 |
| 연결 상태 | 백엔드 연결, 재연결, 대기 상태 표시 | 오래된 응답을 최신 데이터로 위장하지 않음 |
| AI Context | 우측 개발자 drawer 열기 | 일반 사용자 목적지가 아닌 진단·개발자 기능으로 격리 |
| Dark/Light | 테마 변경 | 두 테마에서 주요 텍스트·테이블·입력 경계를 유지 |

### 10.2 연구 RUN 선택기

| 기능 | 상세 동작 |
|---|---|
| 현재 RUN 표시 | 화면이 참조하는 연구 실행 ID를 상단에서 고정적으로 확인 |
| RUN 변경 | 선택한 run identity를 각 패널에 전달 |
| 선택 세대 | 새 run 선택 시 이전 요청 결과를 폐기 |
| owner 검증 | 응답의 run/selection owner가 현재 화면과 일치할 때만 반영 |
| unavailable 처리 | 해당 run에 자료가 없으면 다른 run 결과로 대체하지 않고 unavailable 표시 |
| LIVE 상태 | 현재 실행과 과거 실행을 시각적으로 구분 |

### 10.3 좌측 6목적지 레일

| 목적지 | 정상 레일 | 소유 책임 |
|---|---:|---|
| Live | 예 | 현재 연구 실행, 단계, 조건식·엔진·분석 근거 |
| Backtest | 예 | 독립 전략 실행과 결과 분석 |
| Replay | 예 | 시장·차트 재생 |
| History | 예 | 과거 연구, 비교, 정본 상세, 거버넌스 |
| 성과 | 예 | 장기 성과 기준과 Hall-of-Fame |
| Reports | 예 | HTML 보고서, Wiki, Reports 소유 prototype |
| Audit | 아니오 | History 거버넌스로 흡수 |
| Lab | 아니오 | Live 단계 분석과 History 상세로 흡수 |
| Context | 아니오 | AI Context developer drawer로 이동 |
| Alpha | 아니오 | 정상 목적지가 아닌 명시적 prototype/rollback 경계 |
| Catalog | 아니오 | Reports 소유 `?prototype=catalog` deep link |

### 10.4 공통 상태와 실패 UX

| 상태 | 화면 표현 | 금지되는 동작 |
|---|---|---|
| loading | 현재 목적지의 loading 문구 또는 skeleton | 이전 목적지 데이터를 현재 결과로 표시하지 않음 |
| connected | `백엔드 연결됨 · v2` | 연결 상태만으로 데이터 freshness를 추정하지 않음 |
| reconnecting | 재연결·대기 상태 | 반복 점멸로 최신 응답처럼 보이게 하지 않음 |
| unavailable | 해당 자료가 없다는 명시적 상태 | 임의 샘플이나 다른 run 결과로 채우지 않음 |
| stale | 최신 선택과 일치하지 않는 응답 폐기 | 화면 state 갱신 금지 |
| malformed | envelope·owner·identity 오류 표시 | 부분 payload를 정상 결과로 병합하지 않음 |
| empty | 정상적으로 데이터가 없는 상태 | 실패와 동일한 빨간 오류로 과장하지 않음 |
| partial | 일부 근거만 존재 | complete로 승격하지 않음 |
| conflict | 서로 다른 정본 근거 충돌 | 임의 우선순위로 한쪽을 숨기지 않음 |

## 11. Live 탭 상세 완료 결과

### 11.1 사용자 목적

Live는 “지금 연구가 어떤 조건식으로 어느 단계까지 진행됐으며 어떤 데이터와 결과를 근거로 판단 중인가”를 한 화면에서 파악하고, 자동 진행을 방해하지 않으면서 특정 세대와 단계를 고정해 분석하는 화면이다.

### 11.2 화면 구조

| 영역 | 배치 | 표시 내용 | UX 의도 |
|---|---|---|---|
| 상단 연구 상태 | 콘텐츠 최상단 | run, 세대, 단계, 전체 진행률 | 화면 진입 즉시 현재 위치 파악 |
| 단계 stepper | 상단 우측/전체 폭 | 생성, 백테스트, 채점, 부검 | 연구 파이프라인을 순서대로 이해 |
| workflow evidence | stepper 인접 | 단계별 시간, 차단 사유, 최신 로그 | 긴 텍스트 나열을 compact evidence로 전환 |
| Fitness 그래프 | 3열 그래프 영역 | 세대별 graded score, gate, best | 연구 개선 방향과 gate 거리 확인 |
| Profit trajectory | 그래프 영역 | 세대별 수익률·수익금 | fitness와 실제 경제적 결과를 분리 비교 |
| Quality metrics | 그래프 영역 | Calmar, 우상향 R², MDD 등 | 하나의 점수로 숨겨진 품질 위험 확인 |
| 전체 궤적 | 하단 분석 영역 | 후보별 전체 곡선·선택 세대 | 선택 결과가 전체 분포에서 어디에 있는지 확인 |
| 세대 상세 | 우측 패널 또는 drawer | 현재 세대, phase, checkpoint, 근거 | 차트와 현재 실행 정체성 연결 |
| 반복 세대 사이클 | 우측 시각화 | generation loop 단계 | 연구 반복 구조를 직관적으로 확인 |
| 정본 필드 | 단계별 panel | 조건식 코드, 엔진 설정, 분석 source | 표시 근거의 출처·신선도 확인 |

### 11.3 그래프와 울트라와이드 UX

| 요청 사항 | 구현 결과 |
|---|---|
| 한 그래프가 화면 대부분을 차지하는 문제 | hero 높이를 제한하고 핵심 그래프를 병렬 카드로 분해 |
| 3440×1440에서 여러 그래프 동시 확인 | 3열 그래프-first grid 적용 |
| 그래프 아래 정보가 너무 멀리 배치 | 주요 KPI와 보조 분석을 첫 화면 밀도에 맞게 재배치 |
| 글자와 버튼이 너무 작음 | 핵심 제목, 단계, KPI, 조작 target의 판독성과 최소 크기 보강 |
| 우측 패널 확대 | 상세 panel/drawer를 펼쳐 긴 조건식과 근거 확인 가능 |
| 세로 스크롤 과다 | 현재 의사결정에 필요한 차트·KPI를 먼저 배치하고 상세 근거는 disclosure로 분리 |
| 상태 텍스트만 나열 | badge, progress, stepper, KPI, compact evidence로 변환 |

### 11.4 단계 stepper와 관찰 상태

| 기능 | 동작 |
|---|---|
| Follow Live | 최신 세대와 현재 단계가 변경되면 활성 탭이 진행 흐름을 따라감 |
| User Pin | 사용자가 특정 단계 또는 세대를 선택하면 자동 이동을 정지 |
| Reset/Follow 복귀 | 사용자가 명시적으로 최신 진행 관찰로 복귀 |
| 단계 자동 전환 | follow 상태에서 실제 phase가 바뀔 때 해당 단계 패널 활성화 |
| terminal precedence | run 완료·실패·취소가 관측되면 오래된 running 표시보다 우선 |
| keyboard 이동 | 탭/화살표/Enter 계열의 접근 가능한 단계 탐색 |
| focus 보존 | 자동 갱신이 사용자의 현재 키보드 포커스를 임의로 빼앗지 않음 |
| drawer focus | 상세 drawer가 열리면 내부로 포커스 이동, 닫으면 호출 지점으로 복원 |

### 11.5 단계별 기능

| 단계 | 핵심 정보 | 시각화·조작 |
|---|---|---|
| 생성 | 생성 조건식, LLM/code generation 상태, 후보 identity | 생성 성공·실패, 시간, source 근거 |
| 백테스트 | 실제 매수·매도 조건식, 엔진 모드, timeframe, cost | 조건식 코드 disclosure, engine panel, 결과 연결 |
| 채점 | fitness, gate, quality metrics, promotion blockers | 점수 곡선, gate line, KPI badge |
| 부검 | 실패 원인, MDD, holdout, advisory 원인 | autopsy 결과, 차단 badge, 분석 상세 |
| 반복 | 다음 세대 생성 여부, max generation, terminal reason | 현재/전체 세대, 완료 또는 다음 반복 표시 |

### 11.6 Live 정본 데이터 계약

| 필드 | 정본 기준 | 잘못된 데이터 처리 |
|---|---|---|
| run ID | 현재 선택된 run | 불일치 응답 폐기 |
| generation | 현재 selected/follow generation | 이전 세대 응답으로 덮어쓰기 금지 |
| phase | 서버 상태와 terminal precedence | 화면이 추정한 phase를 정본으로 사용하지 않음 |
| 조건식 코드 | 해당 세대의 authoritative strategy fields | 다른 run 또는 fallback 코드 표시 금지 |
| 엔진 설정 | 실제 backtest engine payload | label만 보고 엔진 종류 추정 금지 |
| 분석 결과 | source/freshness/identity가 있는 payload | source 누락 시 unavailable/partial |
| 차단 사유 | hard gate와 advisory를 구분 | advisory를 승인 또는 완료로 표현하지 않음 |

## 12. Backtest 탭 상세 완료 결과

### 12.1 사용자 작업 흐름

1. 실행 모드를 선택한다.
2. 매수·매도 조건식을 라이브러리에서 선택하거나 편집한다.
3. 기간, 장중 시간, 봉 단위, 엔진 수, 투자금과 데이터 분류를 설정한다.
4. 수동으로 실행한다.
5. 결과 라이브러리에서 실행 결과를 선택한다.
6. 핵심 지표와 누적수익·분포·거래 상세를 검토한다.
7. 필요하면 Monte Carlo, A/B, portfolio 근거로 확장 분석한다.

### 12.2 입력·실행 영역

| 기능 | 세부 기능 | UX/UI 결과 |
|---|---|---|
| 모드 선택 | 백테스트, 최적화, WFO, 스텝 | 선택 상태를 명확한 active style로 표시 |
| 매수 조건식 | 이름 선택, 코드 편집, 저장 | 좌측 editor와 라이브러리 연결 |
| 매도 조건식 | 이름 선택, 코드 편집, 저장 | 우측 editor와 라이브러리 연결 |
| 기간 | 시작일·종료일 | 형식과 기본 경계를 label로 명시 |
| 거래 시간 | 시작·종료 HHMMSS | 날짜와 시간을 별도 입력으로 분리 |
| timeframe | tick/minute 구분 | 분봉·틱 단위 혼동 방지 |
| engine count | 병렬 실행 수 | 기존 `/bt` contract 범위에서 전달 |
| 투자금 | 백만원 단위 | 단위를 입력 label에 명시 |
| 평균 계산 tick | 계산 주기 | 실제 engine field와 연결 |
| 데이터 분류 | 종목코드별 등 | 실행 데이터 owner를 명시 |
| 실행 | 명시적 사용자 action | 자동 실행하지 않음 |
| 취소 | 실행 중 취소 | 기존 runner 취소 경계 유지 |

### 12.3 결과 라이브러리

| 기능 | 동작 |
|---|---|
| 결과 목록 | 실행별 stable identity와 상태 표시 |
| 검색 | run/memo/tag/전략을 기준으로 필터 |
| 즐겨찾기 | 자주 비교할 결과를 고정 |
| 결과 선택 | 선택된 결과만 상세 패널의 owner가 됨 |
| primary/detail guard | 목록 선택이 바뀐 뒤 도착한 이전 상세 응답 폐기 |
| refresh | 서버 결과 목록을 다시 조회하되 현재 선택 identity 검증 |
| empty state | 실행 결과가 없을 때 빈 차트를 성공 결과로 위장하지 않음 |
| result status | 성공·실패·취소·증거 준비 여부를 구분 |

### 12.4 결과 분석 화면

| 분석 영역 | 표시 지표·기능 |
|---|---|
| 핵심 메트릭 | 거래 수, 승률, 누적수익률, 수익금, MDD, CAGR |
| 운영 지표 | 일평균 거래, 필요 자금, 최대 동시보유, 평균 보유, 수익/손실 건수 |
| 거래 품질 | 평균 수익률, MDD 금액, TPI, 거래일 |
| 누적수익·월별 손익 | 수익/손실 bar와 누적수익 line, 기간 선택·구간 분석 |
| 손익 분포 | 이익·손실 bin histogram |
| 거래 상세 | 개별 진입·청산, 보유시간, 수익률과 비용 |
| Monte Carlo | 결과 안정성·분산 근거 |
| A/B | 동일 정체성 기준의 두 실행 비교 |
| Portfolio | 복수 전략 조합의 자본·위험 근거 |
| 결과 disclosure | 큰 차트와 상세 표를 필요할 때 확장·축소 |

### 12.5 Backtest 경계

- 별도 실행 엔진을 새로 만들지 않고 기존 `/bt` runner를 사용한다.
- 화면은 수동 실행을 보조하며 자동 주문이나 실거래 승격을 수행하지 않는다.
- primary result와 detail result의 identity가 다르면 병합하지 않는다.
- tick/minute와 시각 단위를 label 및 데이터 계약에서 분리한다.
- 데이터가 없을 때 임의의 수익 곡선이나 예제 지표를 실제 결과처럼 표시하지 않는다.

## 13. Replay 탭 상세 완료 결과

| 영역 | 기능 | UX/UI 결과 |
|---|---|---|
| 데이터 선택 | replay source와 날짜 선택 | 사용 중인 source를 상단에 명시 |
| 재생 제어 | 시작, 일시정지, 이동 | 명시적 control과 상태 표시 |
| 속도 | replay 속도 변경 | 현재 속도를 즉시 확인 |
| 차트 | 가격·거래·조건 이벤트 | 시간축과 이벤트를 동일 맥락에서 표시 |
| 조건식 근거 | 해당 시점의 조건 충족 여부 | 미래 데이터와 혼합하지 않음 |
| 상태 복원 | direct URL, back/forward | 정상 6목적지 shell 상태와 일치 |
| unavailable | sim backend 또는 데이터 없음 | 빈 성공 화면 대신 원인 표시 |
| 반응형 | 1920/2560/3440 | 전 해상도 overflow 0 |

Replay는 연구 결과의 원인을 시간 순서로 재검토하는 목적지이며, Backtest 실행·History 아카이브·Live 진행 상태의 소유권을 중복하지 않는다.

## 14. History 탭 상세 완료 결과

### 14.1 정보 구조

| 계층 | 내용 |
|---|---|
| Archive selection | 과거 campaign/run 목록과 기본 지표 |
| Summary | 선택 연구의 기간·성과·근거 상태 |
| Compare | 복수 run/세대를 동일 기준으로 비교 |
| Governed research index | 정본 research identity 목록 |
| Research detail | 조건식·평가·부검·holdout·문서·커밋·거버넌스 |
| Analysis | 시간대·시가총액·correlation 등 검증된 분석 |
| Wiki relation | 관련 연구 문서와 변경 이력 |

### 14.2 Archive/Compare

| 기능 | 상세 |
|---|---|
| campaign 목록 | 후보 수, best PnL, MDD, artifact 수, 갱신 시각 |
| 선택 요약 | 선택 campaign/run의 root와 핵심 결과 |
| top candidates | 동일 campaign 내 우수 후보 비교 |
| Run Compare | 최대 허용 범위 안에서 복수 run/gen 비교 |
| 과거 연구 재열람 | 선택 run의 세대·조건식·결과로 이동 |
| legacy 표시 | 정본 governed 연구와 legacy archive를 같은 근거로 위장하지 않음 |
| demo/unavailable | 백엔드 미연결 시 실제 기록처럼 보이지 않도록 표시 |

### 14.3 Governed Research History

| 기능 | 상세 |
|---|---|
| 안정 ID | `campaign:*`, `loop_run:*`처럼 source kind를 포함 |
| 검색 | label과 research ID 검색 |
| source filter | campaign/loop run 등 owner별 필터 |
| 상태 요약 | stages, conditions, evaluations, tree, updated |
| selected row | 현재 선택을 시각적으로 강조 |
| source owner | adapter·section owner·artifact reference 표시 |
| provenance | 데이터 출처와 신뢰 상태 표시 |
| stage load | 사용자가 필요한 stage/section을 명시적으로 로드 |
| pagination | signed cursor와 server ceiling 유지 |
| selection generation | 선택마다 세대를 증가시키고 이전 응답 폐기 |

### 14.4 조건식과 평가 상세

| 영역 | 표시 내용 |
|---|---|
| Condition tree | 조건식 계층, 부모·자식, code/name 상태 |
| Condition disclosure | 긴 조건식 코드를 행별로 확장 |
| Evaluation rows | 실제 `evaluation_status`, 거래 수, 수익률, MDD 등 |
| Autopsy | 실패 원인과 단계별 판정 |
| Holdout | OOS/holdout 존재·부분·누락 상태 |
| A/B | 정본 또는 legacy 비교의 성격 명시 |
| Docs | 정확히 연결된 연구 문서 |
| Commits | 연구와 연관된 커밋 |
| Governance | 승인·차단·근거 건강 상태 |

### 14.5 History UX 안전장치

| 위험 | 방어 |
|---|---|
| 늦게 도착한 선택 응답 | abort + selection generation 확인 |
| 잘못된 owner metadata | 타입과 허용 owner를 fail-closed 검증 |
| 절대 evidence path 노출 | UI payload와 summary에서 경로 redaction |
| 문서 내부 경로 노출 | `/research_doc` 응답의 공개 필드만 렌더 |
| malformed envelope | 정상 행으로 병합하지 않고 unavailable/error |
| cursor 과다 조회 | server ceiling과 continuation 규칙 유지 |
| legacy/governed 혼합 | 별도 영역과 명시적 label 사용 |
| 잘못된 ARIA | 선택 행과 disclosure 역할을 실제 동작에 맞게 분리 |
| keyboard 탐색 | 조건식 disclosure와 목록 선택을 키보드로 수행 |
| 없는 holdout 추정 | missing/partial 상태를 그대로 표시 |

## 15. 성과 탭 상세 완료 결과

### 15.1 역할

성과 탭은 분석 워크벤치가 아니라 장기 성과 기준과 Hall-of-Fame 전용 화면이다. Live의 진행 분석, History의 연구 비교, Backtest의 실행 상세를 다시 복제하지 않는다.

### 15.2 Hall-of-Fame 기능

| 기능 | 상세 |
|---|---|
| 성과 source 구분 | 인간 벤치마크, Seed, AI 생성 전략 |
| 정렬 | 총수익률, 총수익금, 연평균, MDD, payoff |
| 필터 | 전체/인간/Seed/AI |
| 표시 지표 | 총수익금, 총수익률, 연평균, MDD, payoff, 일평균 거래, 동시보유, 운영금, 기간 |
| 장기 기준 | 단기 최고점만으로 승격하지 않고 기간·표본·비용·MDD를 함께 표시 |
| human reference | 사람 개발 성과를 AI 생성 결과와 구분 |
| gate 설명 | 승격 전에 필요한 비교 기준과 증거를 안내 |
| freshness | 새로운 BASE/run 선택 후 이전 Hall-of-Fame 응답 폐기 |
| 결과 screenshot | 인간 결과 근거를 별도 검토 자료로 확인 |
| refresh | 현재 owner와 selection generation을 유지하며 갱신 |

### 15.3 승격 안전 경계

- Hall-of-Fame 행은 실거래 승인이나 미래 성과 보장을 뜻하지 않는다.
- 서버 검증, hard gate, 코드 검토, 비용·표본·MDD 근거와 사람 승인이 없으면 자동 승격하지 않는다.
- AI 결과와 인간 reference를 동일 source인 것처럼 혼합하지 않는다.
- 연결이 끊기면 마지막 응답을 최신 Hall-of-Fame으로 간주하지 않는다.

## 16. Reports 탭 상세 완료 결과

### 16.1 HTML Reports

| 기능 | 상세 |
|---|---|
| 보고서 목록 | 관리 manifest와 기존 unmanaged HTML을 구분해 나열 |
| 보고서 선택 | 선택한 manifest/report identity만 뷰어에 표시 |
| 보고서 메타데이터 | report ID, research ID, status, SHA, byte 수, 생성 시각 |
| provenance | source 파일과 생성 loader/registry/build 경로 |
| trust | trusted/untrusted, hash match/mismatch 표시 |
| stale | source 변경 후 재생성 필요 상태 |
| missing | HTML 또는 source 누락 상태 |
| allowlisted links | 보고서가 이동할 수 있는 내부 탭·문서 링크 제한 |
| scriptless report | 보고서 내부 JavaScript 실행 금지 |
| sandbox viewer | 빈 sandbox iframe으로 외부 권한 차단 |
| CSP | `/reports/view`에서 `default-src 'none'` 적용 |
| manual writer | 명시적 offline/manual 명령에서만 보고서 생성 |
| atomic replace | staging에 완성 후 관리 대상 corpus 교체 |
| unmanaged preservation | 관리 대상이 아닌 기존 HTML 삭제 금지 |
| failure isolation | 하나의 보고서 실패가 전체 registry를 손상시키지 않음 |

### 16.2 권장 연구 보고서 구성

| 탭/절 | 필수 내용 |
|---|---|
| 요약 | 연구 목적, 결론, 최종 상태, 핵심 KPI |
| 연구 상세 | run/research ID, 기간, 시장, 데이터, 비용, 엔진 |
| 결과·조건식 근거 | 매수·매도 조건식, 세대, fitness, holdout, OOS |
| 조건식 | 실제 조건식 코드와 parent/source |
| 활동·유물 | 생성·백테스트·채점·부검 단계와 artifact |
| 원인 분석 | 성공·실패 원인, MDD, 표본, regime, leakage 위험 |
| 결론 | 채택·보류·폐기 판정과 다음 연구 |
| 히스토리 | 관련 문서, 커밋, 이전·후속 보고서 |
| 거버넌스 | 승인, gate, blocker, evidence health |

### 16.3 Research Wiki

| 기능 | 상세 |
|---|---|
| 검색 | title, document ID, tag, SHA |
| category | Methods, Good Results, Metrics 등 |
| 태그 | 연구 유형·단계·대상별 필터 |
| chronology | 문서 생성·변경 순서 |
| related links | 관련 연구·보고서·커밋 연결 |
| 문서 상세 | 제목, 경로 대신 공개 문서 ID, trust, byte 수, SHA |
| 원문 보존 | Markdown bytes를 수정하거나 HTML로 덮어쓰지 않음 |
| sidecar/index | 검색 메타데이터를 원문과 별도로 관리 |
| pagination | bounded limit/cursor로 대규모 문서 집합 처리 |
| failure state | 누락·읽기 실패·잘못된 metadata를 정상 문서로 위장하지 않음 |
| read-only | 대시보드에서 원문 편집·삭제 기능을 제공하지 않음 |

## 17. Reports 소유 P4 Catalog prototype

### 17.1 접근과 소유권

- Catalog는 일곱 번째 정상 탭이 아니다.
- `/ui/evolution/catalog` direct route는 Reports의 `?prototype=catalog`로 canonicalize된다.
- 화면 제목은 prototype임을 명시하고 정상 운영 데이터와 혼동하지 않도록 한다.
- rollback 경로는 비정본임을 표시하며 정본 6목적지 IA를 변경하지 않는다.

### 17.2 API 계약

| API | 반환 내용 | 서버가 하지 않는 일 |
|---|---|---|
| `/research/assets` | 연구 자산, kind, 상태, window, summary | 임의 집계·수정 |
| `/research/judgments` | 판단 카드와 판정 근거 | 재판정·승격 |
| `/research/cells` | source별 cell 행과 allowed partitions | 존재하지 않는 source 추정 |
| `/research/clauses` | 조건식 clause와 상태 | 서버 COUNT/AVG/SUM |
| `/research/summary` | 폐기, 404 | 구형 집계 유지 |

### 17.3 데이터 안전

| 경계 | 구현 |
|---|---|
| DB 위치 | 절대 `STOM_RESEARCH_ASSETS_DB` 환경변수만 허용 |
| 기본 DB | 없음 |
| 상대 경로 | 거부 |
| 연결 모드 | SQLite URI `mode=ro` |
| 연결 수명 | 요청 단위 |
| schema | rdc-1 기대 schema 검증 |
| freshness | DB mtime 검증 |
| provenance | 응답 envelope에 정본 metadata 제공 |
| 오류 | not_configured, invalid_path, schema_mismatch 등 fail-closed |
| 집계 | 서버 SQL 집계 금지 |
| 쓰기 | API와 connection 모두 쓰기 금지 |

### 17.4 Catalog 화면

| 뷰 | 기능 | 상태 |
|---|---|---|
| V1 | 연구 파이프라인·연혁 | 완료 |
| V2 | 함정 지도 | 완료 |
| V3 | 절·조건 실험실 | 완료 |
| V4 | 표본·출구 은행 | 완료 |
| V5/B1 | 운용 준비 골격 | 근거 전까지 의도적 empty shell |
| Provenance cards | asset/judgment 출처와 commit | 완료 |
| Source partition | cells API `allowed[]` 기반 동적 선택 | 완료 |
| BAD/KILL 표시 | 실패 판단을 성공 색상으로 위장하지 않음 | 완료 |

## 18. 해상도별 UX/UI 검증

| 해상도 | 검증 목적 | 결과 |
|---|---|---|
| 1920×1080 | 일반 데스크톱에서 핵심 기능과 조작이 잘리지 않는지 확인 | 7개 화면 통과, overflow 0 |
| 2560×1440 | QHD에서 밀도와 여백이 균형을 유지하는지 확인 | 7개 화면 통과, overflow 0 |
| 3440×1440 | 사용자 울트라와이드 환경에서 복수 그래프·패널 동시 확인 | 7개 화면 통과, overflow 0 |

브라우저 자동화는 각 해상도에서 Live, Backtest, Replay, History, 성과, Reports, Catalog prototype을 순회했다. 각 행에서 현재 heading, 최종 bundle `42883881`, 연결 상태, 6개 정상 목적지와 수평 overflow를 확인했고 화면 screenshot을 별도 artifact로 남겼다.

## 19. 검토 중 발견하고 해결한 주요 결함

| 발견 결함 | 위험 | 최종 조치 |
|---|---|---|
| 성과에 ResearchPro/RunCompare 중복 | Hall-of-Fame 전용 계약 위반 | 비교·분석을 History로 이동 |
| Context가 일반 rail로 복원될 가능성 | 6목적지 IA 붕괴 | developer drawer로 제한 |
| popstate 후 비활성 탭에 focus 잔류 | 키보드 접근성 저하 | route와 focus state 동기화 |
| History root 절대 경로 표시 | 로컬 파일 구조 노출 | 공개 필드만 렌더하고 경로 redaction |
| 평가 상태 필드 불일치 | 실제 성공/실패 상태가 `—`로 표시 | `evaluation_status` 정본 필드 연결 |
| 잘못된 `aria-selected` 역할 | 보조기술 의미 오류 | 선택 행·disclosure 역할 수정 |
| History 목적지 owner metadata 누락/오류 | 다른 source 결과 혼입 | owner 타입과 selection generation fail-closed |
| Reports 선택 응답 경합 | 이전 보고서가 현재 선택을 덮음 | 선택 세대와 owner guard |
| Hall-of-Fame BASE 응답 경합 | 이전 BASE 성과를 최신으로 오인 | BASE generation guard |
| Catalog source 하드코딩 | DB와 UI 불일치 | `/research/cells`의 `allowed[]` 동적 탐색 |
| Catalog 기본 DB 가능성 | stale DB 또는 의도치 않은 데이터 사용 | env-only 절대 경로, 기본값 없음 |
| Catalog 쓰기·집계 위험 | sealed P4 읽기 전용 계약 위반 | `mode=ro`, 네 API, 서버 집계 제거 |
| 큰 Live 단일 그래프 | 3440 화면 활용 실패 | 3열 graph-first grid와 hero 제한 |
| 연결 끊김 반복 표시 | stale 응답을 최신으로 오인 | connection과 data freshness 분리 |

## 20. 최종 검증 및 증거 위치

| 증거 | 위치 | 내용 |
|---|---|---|
| 최종 테스트 보고 | `artifacts/g008-final-test-report.json` | 최종 commit/bundle, 814+15 tests, build/sync/protected checks |
| 최종 브라우저 transcript | `artifacts/g008-final-browser-transcript.json` | 7페이지×3해상도 자동화 |
| 1920 contact sheet | `artifacts/g008-final-matrix-42883881-1920x1080.jpg` | 전체 화면 시각 근거 |
| 2560 contact sheet | `artifacts/g008-final-matrix-42883881-2560x1440.jpg` | QHD 전체 화면 시각 근거 |
| 3440 contact sheet | `artifacts/g008-final-matrix-42883881-3440x1440.jpg` | 울트라와이드 전체 화면 시각 근거 |
| 최종 품질 gate | `artifacts/g008-quality-gate-0d790306.json` | cleaner, architect, executor QA 종합 |
| Durable 목표 상태 | 현재 세션 Ultragoal `goals.json` | required goal 8/8 complete |
| Durable 감사 기록 | 현재 세션 Ultragoal `ledger.jsonl` | per-goal 및 final aggregate receipt |

`artifacts/`는 검증 근거이며 제품 소스 커밋 대상이 아니다. 사용자가 기존에 보유한 미추적 artifact, 연구 데이터, DB와 문서는 삭제하거나 일괄 스테이징하지 않았다.

## 21. 최종 운영 판정

| 판정 항목 | 결과 |
|---|---|
| 사용자 요청 누락 | 확인된 blocking 누락 없음 |
| 기능 구현 | 완료 |
| UX/UI 개편 | 완료 |
| 울트라와이드 대응 | 완료 |
| 데이터 정체성·경합 방어 | 완료 |
| Reports/Wiki 보안 경계 | 완료 |
| sealed P4 읽기 전용 경계 | 완료 |
| 전체 회귀 | 완료 |
| 브라우저 다중 해상도 | 완료 |
| Cleaner | PASS, blocking 0 |
| Architecture | CLEAR |
| Product | CLEAR |
| Code | CLEAR |
| Executor E2E/Red-team | PASS |
| Durable final aggregate receipt | 생성 완료 |
| 최종 권고 | APPROVE |

V5 대시보드 개편은 승인된 계획과 실행 중 추가된 검토 차단을 모두 반영해 완료됐다. 정상 사용 경로는 6개 목적지로 정리됐고, Live는 실시간 연구 관찰, Backtest는 독립 실행과 결과 분석, Replay는 시간 순서 재검토, History는 연구 정체성과 비교·거버넌스, 성과는 Hall-of-Fame, Reports는 HTML 보고서·Wiki·P4 prototype을 각각 소유한다. 화면 존재만 확인한 것이 아니라 실제 데이터 소유권, stale response, malformed payload, 경로 노출, 읽기 전용 DB, sandbox, 접근성, 3440 화면 밀도와 전체 회귀까지 검증했다.

## 22. 브랜치 계보와 부모 브랜치 통합 안내

### 22.1 확인된 브랜치 관계

| 항목 | 값 |
|---|---|
| 현재 작업 브랜치 | `feature/dashboard-v5-overhaul-20260718` |
| 직접 부모 브랜치 | `feature/dashboard-hodo-20260717` |
| 부모 브랜치 HEAD | `2268b709751e109e862192653d91e7e409e1d0f2` |
| 두 브랜치 merge-base | `2268b709751e109e862192653d91e7e409e1d0f2` |
| 부모에만 있는 커밋 | 0 |
| 현재 V5 브랜치에만 있는 커밋 | 41 |
| V5 구현 최종 커밋 | `0d790306cf721625264ddd72a5c2ec2926af56f3` |
| 장기 기준 브랜치 | `STOM_Version_2U_C-ai-strategy-loop` |
| 기준 브랜치 대비 부모 관계 | 기준 브랜치 고유 커밋 0, 부모가 545커밋 전진 |

현재 상태에서는 `feature/dashboard-hodo-20260717`이 V5 브랜치의 정확한 조상이고 부모 측 고유 커밋이 없다. 따라서 부모 브랜치로 되돌릴 때 일반 merge commit을 만들 필요가 없으며, **fast-forward only**가 가장 안전하고 이력을 가장 명확하게 유지한다.

이 보고서의 상세 확장은 V5 구현 최종 커밋 이후 작업 트리에 추가된 문서 변경이다. 부모 브랜치에 반영하기 전에 이 보고서만 명시적으로 stage하고 별도 한국어 문서 커밋으로 봉인해야 한다. 사용자 미추적 파일, `.gjc`, `.omo`, `artifacts/`, DB와 runtime state는 stage하지 않는다.

### 22.2 권장 통합 순서

| 순서 | 작업 | 목적 |
|---:|---|---|
| 1 | 현재 브랜치와 변경 파일 재확인 | 다른 사용자 작업과 보고서 변경을 구분 |
| 2 | 상세 완료 보고서만 명시적으로 stage | 미추적 연구 자료와 artifact 유입 방지 |
| 3 | 한국어 문서 커밋 생성 | 최종 보고서 변경을 독립 이력으로 보존 |
| 4 | 보고서 커밋에서 최소 검증 재실행 | 문서 형식과 보호 경계 확인 |
| 5 | 부모 브랜치로 전환 | 통합 대상 확인 |
| 6 | `--ff-only`로 V5 브랜치 통합 | 불필요한 merge commit 및 잘못된 overlay 방지 |
| 7 | 부모 브랜치에서 전체 검증 | 통합 후 현재 상태를 다시 증명 |
| 8 | 원격 반영은 명시적 지시 후 수행 | push/PR은 별도 운영 결정으로 유지 |
| 9 | 장기 기준 브랜치 전파는 별도 검토 | 545+41 커밋 전체를 무검토로 합치지 않음 |

### 22.3 보고서 커밋 절차

현재 V5 브랜치에서 다음 순서가 권장된다.

```powershell
git branch --show-current
git status --short

git add docs/web_dashboard_expansion/2026-07-19_v5_dashboard_overhaul_completion_report.md
git diff --cached --check
git diff --cached --stat

git commit -m "문서: V5 대시보드 상세 완료 보고 보강" `
  -m "탭별 기능과 UX/UI 계약, 검증 근거, 브랜치 통합 절차를 상세히 기록합니다."
```

금지 사항:

- `git add -A` 사용 금지
- `artifacts/`, `.gjc/`, `.omo/`, `ai_strategy_loop/state/` 일괄 stage 금지
- 사용자 미추적 파일 삭제·이동·stash 금지
- `_database/`, `_database_v3k_shadow/`, `_log/`, `backup/`, `*.db` stage 금지
- 완료 근거를 이유로 synthetic fixture 또는 screenshot을 제품 커밋에 포함하지 않음

### 22.4 부모 브랜치 fast-forward 절차

보고서 커밋과 검증이 완료된 후 다음처럼 진행한다.

```powershell
git status --short
git switch feature/dashboard-hodo-20260717

git merge --ff-only feature/dashboard-v5-overhaul-20260718
git log --oneline --decorate -5
```

`--ff-only`가 실패하면 강제로 일반 merge를 만들지 않는다. 실패는 부모 브랜치가 별도로 전진했거나 worktree 상태가 달라졌다는 뜻이므로 아래를 다시 확인해야 한다.

```powershell
git merge-base feature/dashboard-hodo-20260717 feature/dashboard-v5-overhaul-20260718
git rev-list --left-right --count feature/dashboard-hodo-20260717...feature/dashboard-v5-overhaul-20260718
git status --short
```

부모 고유 커밋 수가 0이 아니면 먼저 차이를 검토하고, V5 브랜치를 새 부모 위로 재검증하거나 필요한 커밋만 명시적으로 cherry-pick한다. 사용자 작업을 덮는 reset, 강제 checkout, overlay 복사는 사용하지 않는다.

### 22.5 부모 브랜치 통합 후 검증

| 검증 | 명령 | 합격 조건 |
|---|---|---|
| 브랜치 | `git branch --show-current` | `feature/dashboard-hodo-20260717` |
| 이력 | `git rev-parse HEAD` | 상세 보고서 커밋과 일치 |
| 문서·공백 | `git diff --check` | 출력 없음 |
| Dashboard 전체 | `python -m pytest tests/unit/dashboard -q --maxfail=1` | 현재 기준 814 passed |
| Track Z | `python -m pytest tests/unit/dashboard/test_track_z_pr1_harness.py -q` | 15 passed |
| TypeScript/JSX | `npm run typecheck` in `ai_strategy_loop/dashboard/webui-build` | runtime JSX PASS |
| Bundle | `npm run build` in `ai_strategy_loop/dashboard/webui-build` | `app.js?v=42883881`, 예상 외 tracked diff 없음 |
| Nonrelease | `python scripts/verify_nonrelease_sync.py` | 전체 OK |
| 보호 경로 | 보호 경로 대상 `git status --short` | 출력 없음 |
| 최종 상태 | `git status --short` | 사용자 미추적 파일만 보존, 예상하지 않은 tracked 변경 없음 |

빌드가 생성 파일을 변경하지 않는 것이 현재 기대 상태다. bundle hash가 바뀌면 변경 원인을 검토하고, 브라우저 transcript와 보고서의 bundle identity를 갱신한 뒤 다시 검증해야 한다.

### 22.6 장기 기준 브랜치로의 후속 전파

`STOM_Version_2U_C-ai-strategy-loop`는 `feature/dashboard-hodo-20260717`의 조상이지만, 부모 브랜치는 장기 기준보다 이미 545개 커밋 앞서 있다. V5 통합 후에는 차이가 더 커지므로 장기 기준 브랜치에 곧바로 전체 feature history를 overlay merge하는 것은 권장하지 않는다.

| 선택지 | 적용 조건 | 권고 |
|---|---|---|
| 부모 feature에서 계속 검증 | 대시보드 연구·QA가 계속될 때 | 가장 안전한 기본 경로 |
| 기준 브랜치에 전체 fast-forward | 545개 선행 변경 전체가 이미 승인됐을 때만 | 별도 통합 승인과 전체 회귀 필요 |
| 기준 브랜치에 선택적 cherry-pick | V5 관련 커밋만 분리 전파해야 할 때 | 프로젝트의 upstream 동기화 정책과 가장 잘 맞음 |
| overlay copy 또는 일반 대형 merge | 변경 출처·소유권을 추적하기 어려울 때 | 금지·비권장 |

선택적 cherry-pick을 사용할 경우 계획, 구현, blocker 수정, 보고서 커밋을 임의로 누락하면 안 된다. 먼저 다음 명령으로 V5 범위 커밋을 확정한다.

```powershell
git log --reverse --oneline 2268b709751e109e862192653d91e7e409e1d0f2..feature/dashboard-v5-overhaul-20260718
```

그 후 별도 integration branch를 장기 기준에서 만들고 커밋을 순서대로 cherry-pick한다. 중간 충돌에서 V3K live gate, serial/PYD 정책, Kiwoom 유지 경계를 훼손하지 않아야 하며, 최종적으로 dashboard 전체 테스트와 `verify_nonrelease_sync.py`를 다시 실행한다.

### 22.7 원격 push 또는 PR

이 보고서 작성 시점에는 push나 PR 생성이 요청되지 않았다. 따라서 로컬 커밋과 부모 브랜치 통합 이후에도 원격 작업은 자동 수행하지 않는다. 원격 반영 시에는 다음 정보를 PR 본문에 포함해야 한다.

- 승인 기준 커밋 `2268b709`
- 최종 V5 구현 커밋 `0d790306`
- 상세 완료 보고서 경로
- 최종 bundle `42883881`
- dashboard 814 passed
- Track Z 15 passed
- 7페이지 × 3해상도, overflow 0
- Reports/Wiki sandbox와 P4 `mode=ro` 경계
- 보호된 runtime/trading data 변경 없음
- Catalog는 Reports 소유 prototype이고 B1은 의도적 empty shell임

### 22.8 권장 최종 브랜치 상태

| 브랜치 | 권장 상태 |
|---|---|
| `feature/dashboard-v5-overhaul-20260718` | V5 구현과 상세 보고서를 보존하는 실행 증거 브랜치 |
| `feature/dashboard-hodo-20260717` | 검증 후 V5 브랜치로 fast-forward된 직접 부모 |
| `STOM_Version_2U_C-ai-strategy-loop` | 별도 승인 전에는 유지; 선택적 cherry-pick 또는 승인된 전체 전파만 수행 |
| 원격 브랜치/PR | 사용자 또는 운영자의 명시적 지시 후 생성 |

즉시 권장되는 다음 상태는 **상세 보고서를 현재 V5 브랜치에 독립 커밋한 뒤, 직접 부모 `feature/dashboard-hodo-20260717`을 `--ff-only`로 전진시키고 부모에서 전체 검증을 재실행하는 것**이다. 장기 기준 브랜치 전파와 원격 push는 이 로컬 통합이 확인된 뒤 별도 승인 단위로 수행한다.
