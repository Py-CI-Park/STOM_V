# v5.3.4 Backtest 전수검사표 (U5) — 백엔드 21 엔드포인트 × 프론트 13모듈

- 검사 일시: 2026-07-19 · 대상 서버: wt-v5 8771(현행 코드) · 방법: 안전(GET·무인자) 실호출 프로브 + 소스 인벤토리.

## 1. 백엔드 엔드포인트 검사 결과

### 1.1 무인자 GET — 실호출 전부 정상 (7/7 · 200 · 정상 JSON envelope)
| 엔드포인트 | 상태 | 응답 스키마(키) | 판정 |
|---|---|---|---|
| /bt/health | 200 | status·module·api_version | ✅ |
| /bt/strategies | 200 | status·reason·message·items·count·kind | ✅ (envelope 우수) |
| /bt/jobs | 200 | jobs·count | ✅ |
| /bt/data_range | 200 | tick·min | ✅ |
| /bt/evo_gens | 200 | items·count·run_id | ✅ |
| /bt/legacy/self_vars | 200 | available·adapter·rows·refs·message·reversible | ✅ |
| /bt/backfinder/preflight | 200 | available·kind·name·precondition_ok·has_tickcols… | ✅ |

### 1.2 인자 필요 GET — job/전략 데이터 필요(운영 검사 대기)
| 엔드포인트 | 필요 인자 | 검사 방법(운영 run 시) |
|---|---|---|
| /bt/result·/bt/job·/bt/job/meta | job_id | run 1회 후 응답 스키마·에러 envelope 확인 |
| /bt/report·/bt/compare·/bt/overlay·/bt/portfolio·/bt/analysis/montecarlo | job/전략 | 동일 |
| /bt/strategy·/bt/extract_vars | 전략명 | 저장 전략으로 확인 |

### 1.3 실행 계열(POST) — 수동 검사·가드 확인 대상
| 엔드포인트 | 성격 | 가드 |
|---|---|---|
| /bt/run | 백테 실행 | job 큐·cancel 가능(기실증: V5.3 divid_mode 계약 테스트) |
| /bt/job/cancel | 작업 취소 | job_id 스코프 |
| /bt/strategy/validate | 구문 검증 | 읽기성 |
| /bt/strategy/delete | **파괴적** | 수동 확인 필수 — UI 확인 다이얼로그 존재 여부 v5.3.4b에서 확인 |

## 2. 프론트 모듈 인벤토리(5,700줄) — 역할·검사 항목
| 모듈 | 줄 | 역할 | 검사 항목 |
|---|---|---|---|
| bt-tab-run(840) | 실행 폼 | divid_mode·기간·전략 선택 | 폼 검증·실행 가드 |
| bt-equity-charts(792) | Equity·MAE/MFE·Underwater·Rolling·Cumulative | 차트 5종 렌더·빈 데이터 |
| bt-tab-analysis(657) | 분석 탭 오케스트레이션 | 탭 전환·구간 브러시 |
| bt-gui-parity(568) | PyQt 파리티 필드 | 필드 대사표 |
| bt-distribution-charts(533) | 분포·히트맵·MC·월별 캘린더 | 차트 4종 |
| bt-result-area(494) | 결과 본체(+판정 배너 v5.2.5) | 밀도(§3) |
| bt-stat-panels(411)·bt-tab-library(380)·bt-tab-mode-results(354)·bt-tab-root(267)·utils(347)·v4-backtest(40) | 보조 | — |

## 3. 결과 밀도 재배치(v5.3.4b, 운영 result 필요)
- 현 구조: 판정 배너→조건식 밴드→메트릭 카드→차트 세로 나열(9종) — "너무 크게 보임" 원인.
- 계획: 3440에서 차트 2~3열 그리드 + 차트당 max-height 320 + 통계 fold + 클릭 확대. **실측정은 result 데이터가 필요(운영 run 또는 저장 job)** — 합성 격리 렌더로 1차, 운영 검사에서 확정.
- 인사이트 gap 후보(payload 파생): 요일×시간 히트맵 · 보유시간-수익 산점 · 연승/연패 런.

## 4. 종합 판정
- 백엔드: 무인자 GET 7/7 정상, envelope 일관(available/status·reason) — **구조 건전**.
- 잔여: 인자 GET·실행계열은 운영 run 검사 대기(§1.2·1.3), 밀도 재배치 v5.3.4b.
