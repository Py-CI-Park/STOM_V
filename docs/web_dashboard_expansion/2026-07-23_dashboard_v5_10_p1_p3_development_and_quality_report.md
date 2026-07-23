# 대시보드 v5.10 P1~P3 개발·품질 보고서

## 1. 결론

`feature/dashboard-v5.10-p1-p3-ux-quality`에서 P1 데이터 진실성, P2 UX·구조 고도화, P3 다중 해상도·접근성 품질 게이트를 구현하고 검증했다. 연결된 Backtest의 암묵적 데모 결과를 제거했고, 실제 run/gen 결과를 1열 전폭으로 통일했으며, Live·History·Reports·Hall·Replay·Settings를 동일한 증거·가독성 원칙으로 정비했다.

최종 품질 점수는 아래 명시적 루브릭 기준 **95.6/100**이다. 이는 정적 코드 인상평이 아니라 1,268개 대시보드 테스트, 252개 접근성 조합, 63개 페이지·해상도 브라우저 조합, 실제 run/gen·History 코드·Replay·Hall 카탈로그 증거를 근거로 산정했다.

## 2. 개발 범위와 브랜치 전략

| 구분 | 결과 |
|---|---|
| 부모 브랜치 | `loop/process-research-pipeline` |
| 계획 기준 커밋 | `06cd902` (`대시보드 v5.10 개선 계획 수립`) |
| 개발 브랜치 | `feature/dashboard-v5.10-p1-p3-ux-quality` |
| 대시보드 버전 | `v5.10.0` |
| 앱 번들 | `app.js?v=ecfc1971` |
| CSS 번들 | `v4.css?v=edbe0f54` |
| 개발 시작 | 2026-07-23 11:19:05 KST |
| 최종 검증 종료 | 2026-07-23 14:27:40 KST |
| 실측 경과 시간 | 3시간 8분 35초 |
| Goal 완료 시 누적 토큰 | 948,109 tokens (`goal complete` 실측) |

부모 브랜치에는 계획만 먼저 봉인하고, 구현은 별도 기능 브랜치에서 진행했다. 통합 시에는 이 기능 브랜치의 개발 커밋을 부모 브랜치에 PR로 병합하는 구조를 유지한다.

## 3. P1 구현 결과

| 순서 | 요구 | Before | After | 직접 증거 |
|---:|---|---|---|---|
| 1 | `__demo__` 자동 결과 제거 | 실제 선택이 없어도 합성 결과가 표시될 수 있었음 | 실제 job 또는 run/gen 선택 전에는 정직한 빈 상태만 표시 | `bt-tab-root.jsx`, `bt-result-area.jsx`, `test_backtest_result_identity.py` |
| 2 | Backtest 전폭 1열 | 초광폭에서 구형 다열 규칙이 차트를 절반 폭으로 압축 | 1920/2560/3440 모두 결과 섹션과 차트가 전폭 1열 | `artifacts/v510_real_run_fullwidth.json` |
| 3 | Live/History capability 계약 | 미지원 기능이 비활성 또는 무반응으로 보임 | Monte Carlo·range·compare 지원 여부와 이유를 데이터 원천별로 명시 | `bt-result-area.jsx`, `v4-research.jsx` |
| 4 | History 코드 확대 | 실제 선택 코드의 표시 높이·결합 근거가 불충분 | 정확한 run/gen의 매수·매도 코드를 좌우 배치, 440~560px, 복사 제공 | `artifacts/v510_history_code_height.json` |
| 5 | Reports 폭 | 데스크톱 목록 폭이 좁고 모바일 오버플로 가능 | 데스크톱 360~460px, 모바일 1열, 긴 JSON 줄바꿈 | `artifacts/v510_browser_matrix_final.json` |
| 6 | Hall 전체 AI 카탈로그 | 우수 사례 중심의 제한된 목록 | 성공·실패·손실·no-trade 포함, 서버 필터·정렬·페이지네이션 | `artifacts/v510_hall_catalog_evidence.json` |
| 7 | Replay N+1·실규모 프로파일 | 반복 조회와 성능 근거 부족 | 배치 신호 API, 캐시된 스키마, 단일 replay query, p50/p95 증거 | `artifacts/v510_replay_profile.json` |

## 4. P2 페이지별 UX·구조 고도화

| 페이지/섹션 | 개선 내용 | 사용자 효과 |
|---|---|---|
| Backtest | sticky 섹션 목차, 핵심 차트 다음 MDD/Monte Carlo, 진단 lazy mount, 동일 높이 토큰, 전폭 차트 | 긴 페이지 탐색이 빨라지고 차트가 더 이상 작게 뭉치지 않음 |
| Live | 공유 `BtResultArea` 사용, 중복 Detail·GUI parity 제거, capability·빈 상태 계약 | Backtest 결과 분석과 동일한 시각 언어를 사용하고 중복 정보 감소 |
| 채점·부검 | 임의 개수 대응 균일 그리드, 권위 데이터만 표시, 마지막 카드 의도적 span | 카드 크기와 정보 밀도가 일관되고 가짜 fallback 제거 |
| History | 연구일·목적·사용처·참조 관계 read model, 선택 identity/stale guard, 코드 확대, bounded scroll | 과거 연구를 정확한 run/gen 단위로 재열람 가능 |
| Reports | 카탈로그 분류, provenance/integrity, 시스템·라이트·다크 템플릿, 목록 폭 확대 | 레거시와 재생성 가능 리포트를 구분하고 읽기·탐색 개선 |
| Hall | AI 전체 결과 카탈로그와 human benchmark 분리, 상태·gate·outcome 필터 | 성공 사례 편향 없이 전체 연구 성과를 탐색 가능 |
| Replay | batch API, 쿼리 계측, 오류의 종목별 격리 | 대규모 재생에서 요청 수와 실패 전파 감소 |
| Settings | redacted 200행 로그 링, 필터·복사·내보내기·retention 안내 | 비밀정보를 저장하지 않고 운영 상태를 확인 가능 |
| 공통 차트 | `ChartFrame` loading/ready/empty/stale/malformed/error 계약, raw table 지연 mount | 시각화 상태가 명확하고 키보드·보조기술 접근성 향상 |

## 5. P3 검증 결과

| 게이트 | 실행 결과 | 판정 |
|---|---:|---|
| canonical frontend build | runtime JSX 91개 / 그래프 파일 541개, Vite·앱 번들 성공 | PASS |
| 집중 회귀 | 38 passed | PASS |
| 전체 대시보드 단위·계약 테스트 | 1,268 passed / 0 failed | PASS |
| 비릴리스 동기화 | `verify_nonrelease_sync.py` 전체 OK | PASS |
| diff 무결성 | `git diff --check` 오류 없음 | PASS |
| 접근성 | 9탭 × 7폭 × 2테마 × 2모션 = 252/252, serious/critical 0 | PASS |
| 반응형 브라우저 | 9탭 × 7폭 = 63/63, 가로 오버플로·page error·error boundary 0 | PASS |
| 실제 Backtest | 1920/2560/3440 전폭 1열, 초기 진단 DOM 미마운트 | PASS |
| 실제 History 코드 | buy/sell computed height 560px, 최소 440px, 실제 코드 결합 | PASS |
| Replay 실자료 | 51종목, 376 bars, query_count=1, load p50 24.006ms / p95 33.472ms | PASS |
| Hall 실자료 | 5,364건, 54페이지 완주, 중복 0, 누락 0 | PASS |

검사 해상도는 `375, 768, 1199, 1200, 1920, 2560, 3440px`이다. 접근성 결과는 dark/light와 normal/reduced-motion을 모두 포함한다.

## 6. 섹션별 점수

점수는 기능 정확성 35%, UX·정보 구조 25%, 반응형 15%, 접근성 15%, 성능·운영 증거 10%를 기본으로 하되, 페이지별 적용 불가 항목은 나머지 항목에 비례 배분했다. 증거 없는 주관적 가산점은 부여하지 않았다.

| 섹션 | 점수 | 핵심 근거 | 남은 감점 요인 |
|---|---:|---|---|
| 데이터 진실성·권위 계약 | 98 | 암묵적 데모 제거, read-only LoopState, null/zero 구분 | capability 메타의 장기 API 스키마화 필요 |
| Backtest | 97 | 전폭 1열, sticky 목차, MDD 우선, lazy diagnostics | 초대형 실자료 장시간 브라우저 프로파일 추가 여지 |
| Live | 95 | 공유 결과 분석, 중복 제거, 상태·지원 이유 표시 | 라이브 스트림 장시간 soak 증거는 별도 운영 게이트 |
| 채점·부검·반복 성과 | 95 | 균일 그리드, 권위 데이터만 사용, 의미 기반 높이 | 복잡한 메트릭 조합의 사용자 연구 여지 |
| History | 96 | 정확한 run/gen 코드, 560px, 메타데이터·stale guard | referenced-by 데이터 충실도는 원천 데이터 품질 의존 |
| Reports | 95 | 폭·모바일·테마·목차·provenance 개선 | 일부 legacy static은 원천 부재로 재생성 불가 |
| Hall | 95 | 5,364건 완주, 중복 0, 전체 outcome | 전체 카탈로그 p95 약 695ms로 추가 캐시 최적화 여지 |
| Replay | 95 | batch·query_count 1·p50/p95 계측 | 실시간 장시간 seek/full-day soak 추가 여지 |
| Settings | 94 | redaction·필터·내보내기·retention | 서버 로그는 보안상 수동 조회이며 고급 검색은 미제공 |
| 공통 UX·접근성·반응형 | 96 | 252 접근성 + 63 브라우저 조합 전부 통과 | axe moderate/minor 권고는 후속 개선 가능 |
| **가중 총점** | **95.6** | 1차 목표 90 및 최종 목표 95 충족 | 운영 장시간 검증은 배포 후 관찰 항목 |

## 7. 핵심 비포/애프터

| 관점 | Before | After |
|---|---|---|
| 결과 신뢰 | 선택 없는 합성 결과가 실제처럼 보일 위험 | 명시적 선택·출처·capability가 없는 결과는 표시하지 않음 |
| 차트 크기 | 초광폭에서도 반폭·다열로 뭉침 | 모든 핵심 결과 차트 전폭 1열 |
| 페이지 길이 | 진단까지 한 번에 mount되어 약 14.2 viewport | 핵심 우선 + lazy 진단으로 약 5.2 viewport 초기 흐름 |
| Live/Backtest 일관성 | 결과 분석 구현이 분리·중복 | 공유 결과 컴포넌트와 동일한 상태 계약 |
| 과거 연구 | 선택·코드·메타데이터 결합이 약함 | exact run/gen + 440~560px 코드 + stale guard |
| Hall | 성공 사례 중심 | 전체 AI 결과 5,364건, 실패·손실·no-trade 포함 |
| Replay | 종목별 반복 요청 | batch 요청, query_count 1, 성능 수치 공개 |
| 접근성 | 일부 무명 컨트롤·대비 문제 | 252조합 serious/critical 0 |
| 반응형 | Reports 모바일 오버플로 포함 | 63조합 오버플로 0 |

## 8. 증거 파일

- `artifacts/v510_accessibility_quality_gate_final.json`
- `artifacts/v510_browser_matrix_final.json`
- `artifacts/v510_real_run_fullwidth.json`
- `artifacts/v510_history_code_height.json`
- `artifacts/v510_replay_profile.json`
- `artifacts/v510_hall_catalog_evidence.json`

## 9. 통합·배포 다음 단계

1. 이 기능 브랜치의 개발 커밋을 원격에 push한다.
2. `loop/process-research-pipeline`을 대상으로 PR을 생성한다.
3. PR CI에서 전체 대시보드 테스트와 비릴리스 검증을 재실행한다.
4. PR 병합 후 부모 브랜치에서 번들 hash와 63/252 게이트를 재확인한다.
5. 부모 브랜치에 v5.10 배포 태그를 생성하고 대시보드를 배포한다.
6. 배포 후 Live WebSocket 장시간 soak, Hall p95, Replay full-day seek를 운영 관찰한다.

현재 구현은 연구 재개를 막지 않는다. 오히려 실제 결과·실패·no-trade를 숨기지 않고 History/Hall/Reports에 연결하므로 다음 연구 단계의 의사결정 기반이 강화되었다. 다만 부모 통합과 배포 태깅은 PR/원격 권한이 필요한 별도 배포 행위다.
