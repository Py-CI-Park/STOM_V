# Phase 7 계획 — 시뮬 탭 대개선(지표·속도·엔진·호가·멀티차트) + 전체 탭 결함 정비

> 2026-06-13 · 브랜치 `feature/webbt-phase7` (base `65a646b7` = PR #43 머지 이후 origin tip)
> 프로세스: ralplan 합의(Planner→Architect→Critic 3라운드, **Critic APPROVE**) → 사용자 승인(팀 병렬) → wt-webbt 분리 개발 → 게이트 → PR → 머지 → wt-dev 8770.
> 전체 합의 계획 원본: `.omc/plans/webbt-phase7-sim-improvements.md`(로컬). 본 문서는 추적용 요약+결정 기록.

## §0. 사용자 피드백 SSOT
1. 엔진/지표 라벨 글자가 잘 안 보임 → 가독성 수정.
2. 보조지표 더 추가.
3. 시뮬레이션 엔진(리플레이) 속도 개선.
4. 라이브/LWC/SVG 3개 엔진이 왜 필요한지 설명 + 시각화 개선.
5. 호가창 생성/강화.
6. 멀티차트 2열 + 행 선택/입력.
7. 오더플로우를 차트에서도 보기.
8. 체결강도 그래프.
9. 호가 그래프.
10. 모든 탭 부족 부분 연구·검토·개선.

## §1. 합의 핵심 결정 (ADR 요지)
- **비대칭 엔진 패리티**: LWC v4.2엔 `addPane` API가 없어(서브시리즈 = 단일 캔들 패인의 오버레이 price scale) 3밴드 적층 시 캔들 가독성이 55% 바닥 아래로 떨어진다(7.3 스파이크 실측 ≈ 50~55%). 따라서 **라이브+SVG = 풀 오더플로우(체결강도+호가불균형+net-delta), LWC = 체결강도 오버레이만**. 엔진 차별화 자체가 설계(라이브=최경량·SVG=무의존·LWC=전문 줌/크로스헤어).
- **지표 계산 = 입력 위치 기준 분리**: 판별 기준은 "OHLCV인가"가 아니라 "입력이 이미 wire에 동일하게 실려 있는가". EMA/RSI/MACD/거래량MA/**체결강도MA**는 입력(OHLCV+strength)이 모두 wire에 있어 **클라이언트 계산**(엔진 간 발산 0). VWAP밴드만 `trade_amt`(emission에서 빠짐)가 필요해 **서버 계산**(유일 신규 필드 `vwap_up/low`, k=1.0). `fields` 와이어 필터는 제거(불필요).
- **속도 600x**: 분할(divisor)만 키워 1x=실시간 불변 유지. 라이브 rAF 보간은 `min(150ms, 배치 실시간)`으로 바운드·라이브 전용(LWC 네이티브 애니메이션 이중처리 회피). 실측 elapsed 타이밍 테스트로 검증.
- **검증 오라클은 비브라우저**: 저장소에 pytest Playwright 인프라 없음 → WCAG 대비비(토큰 hex 계산)·소스/구조 grep·실측 타이밍으로 pytest 검증. 시각 증거는 기존 패턴(8771 라이브 서버 대상 C:/Temp 스크린샷)으로 수동 QA.
- **캐시 계약 per-asset 락스텝**: 소스 핀이 이질적(simulation.jsx=613b·evolution=612a·나머지 613a) → 전역 sed 금지, 자산별 소스→타깃 매칭. styles.css는 인라인 스타일로 미변경이라 범프 제외.

## §2. 트랙 (파일 소유 분리)
| 트랙 | 소유 | 요구 |
|------|------|------|
| **S 차트** | simulation-charts.jsx · sim-live-chart.jsx | 4(차트측)·5·7·8·9 + 클라 지표 헬퍼 |
| **B 셸/백엔드** | simulation.jsx · replay_engine.py · simulation_api.py | 1·2·3·4(UI)·6 + 서버 vwap밴드 |
| **L 타 탭** | backtest.jsx · evolution-analysis.jsx · research-lab.jsx | 10 |
| **Shared(메인)** | index/lab/pro.html · tests · 커밋·게이트·PR | 캐시 락스텝·WCAG·계약 동기 |

## §3. 게이트
전체 pytest 신규 실패 0(pre-existing 7 제외) + 캐시 계약 per-asset 락스텝 + vendor-babel 6개 변환 + verify_nonrelease_sync + 8771 시각 증거. 완료 후 코드리뷰 → PR #44 → 머지 → wt-dev 8770.
