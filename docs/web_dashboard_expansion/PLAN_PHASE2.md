# Phase 2 계획 — OPTI 실증 + 승자 리포트 + 시뮬레이션 2차 + 이슈 수정

> 2026-06-12 · 브랜치 `feature/webbt-phase2` (base 63680f11 = PR #33 머지 커밋) · 워크트리 wt-webbt 재활용
> 원칙: 부모(활발 개발 재개)와의 접점 최소화 — 우리 소유 파일(backtest*·simulation*·docs)만.
> index.html·캐시 계약 테스트는 메인 세션 통합 관리. styles.css 추가만.

| 트랙 | 내용 | 파일 소유 |
|------|------|----------|
| A1 (#34) | v5 조건식 OPTI 변환(파생변수 블록을 시간 게이트 안으로) → 워크벤치 등록·검증 → 1종목 1일 → 확장 백테 → 실거래 분석 문서 | 코드 0 — strategy.db(워크트리 사본)+docs/research |
| B1+A2 (#36·#37) | `GET /bt/report`(job_id 또는 run_id+gen_no) 자급자족 HTML 리포트(전 분석+몬테카를로+인사이트, 인라인 SVG) + 리포트 버튼 / back_db_override allowlist / feature_importance gen_no 수정 | backtest_report.py(신규)·backtest_api.py·backtest_jobs.py·backtest.jsx·app.py(2줄)·tests |
| C | 시장 미니맵(등락 타일 클릭→차트 추가)·호가 잔량 흐름 차트(프레임에 raw 잔량 추가)·변수 워치 패널(현재 프레임 값+사용자 임계 비교) | replay_engine.py·simulation_api.py·simulation*.jsx·tests |

게이트(전 트랙 공통): dashboard 테스트 + 전체 스위트 신규 실패 0(pre-existing 7 제외) + verify_nonrelease_sync + 실데이터 스모크. 완료 후 동일 플로우로 PR → 리뷰 → 머지 → wt-dev 통합.
