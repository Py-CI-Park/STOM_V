"""탭형 연구 리포팅 — 단일 자가완결 HTML 생성기(디자인 정본 = 결산 v1).

연구 전체·각 스텝·결과·조건식을 탭 이동 HTML 하나로 생성해 커밋 기록으로 남기고, 추후 wt-dev
대시보드(P4) 이식이 가능하게 한다. 외부 의존 0·라이트/다크 이중 토큰·JS 미작동 폴백.

- registry: 11개 연구 정체(판정 라벨·봉인 커밋은 프로그램 사실, 수치는 loaders 가 json 에서).
- loaders : 판정 json·원장·strategy.db 원문 로더(파일 부재 graceful).
- util    : 이스케이프·조건식 하이라이터·컴포넌트.
- tabs    : 5개 탭 렌더러.
- build_html: CSS(결산 v1 계승)+탭 셸+JS 조립.

엔진 0회 · 원본 read-only · 집계 재계산 없음(원장 count 만 aggregate 재사용).
"""
