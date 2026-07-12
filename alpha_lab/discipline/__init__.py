"""alpha_lab.discipline — 연구 규율 가드 라이브러리 (WBS v3 P1 규율 핵심 패키지).

백로그 A1(W1b 가드)·A21(원장 기입 헬퍼)·A6(시행 병기 리포터)·A4(ledger-lint)를
코드로 실장한다 — "규율을 양심에서 코드로"(V-1형 위반 구조적 재발 방지).

구성 모듈:
- windows: 창-지위 상수 + assert_measurement_window 가드
  (정본은 창-지위 원장 문서 — 불일치 시 원장이 우선).
- ledger: 전역 n_trials 원장의 **단일 기입 API**(append_trial)와
  read_all/aggregate. 기입 경로는 프로그램 전체에서 이 1개뿐이다
  (기록자 2개면 장부가 갈라진다 — 백로그 중복 제거 기록 #2).
- prereg: 사전등록 스켈레톤 생성기(D1 봉인본 2026-07-12 구조 준용).
- trials_report: 판정 문서용 '시행 병기 블록' 생성 — ledger 소비 전용,
  자체 기입 경로 없음(A6 채택 조건).
- lint: known 창 날짜의 측정 문맥 접촉을 문서에서 검출 — **보고 전용**,
  차단 모드 없음(A4 채택 조건).
- measure_gate: 배치 기동 전 봉인 커밋·코드 clean·sha 일치 게이트
  (백로그 A7 — 병행 트랙 산출, 자립형).
- prereg_diff: 봉인 문서 ↔ 결과 JSON 자동 대조기
  (백로그 A5 — 병행 트랙 산출, 자립형).

3계층 방어선에서의 위치(백로그 중복 제거 기록 #8): 커밋 전(lint) ·
기동 전(measure_gate) · 기록 시점(ledger) · 설계 시점(windows/prereg)
층을 본 패키지가 담당하고, 런타임 가드(B1 runner)는 별도 트랙이다.

규율: 원본 데이터 read-only, 측정 없음(도구·그릇만), 한국어 문서화.
"""
