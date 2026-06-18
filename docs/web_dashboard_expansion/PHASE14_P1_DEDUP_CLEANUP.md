# P1 — 중복 정리(데드 RunComparePanel·CodeBlock 충돌) + 전역 중복 가드레일

> 2026-06-14. ralplan 계획 P1. 대시보드 감사 우선순위 1(저위험 빠른 정리).

## 한 줄 요약
데드 코드 `RunComparePanel`(panels.jsx, ORDER상 run-compare.jsx에 덮여 실행 안 됨) 제거 + `CodeBlock` 이름 충돌 해소(code-viewer→`CvCodeBlock`)로 **코드뷰어 Python 하이라이팅 복구** + 재발 방지 `test_no_duplicate_globals` 신설. 동작 변화 = 하이라이팅 복구뿐.

## 변경
- **panels.jsx**: `function RunComparePanel`(880줄, ~80줄) 삭제 + `Object.assign(window,…)`에서 제거. 정본은 `run-compare.jsx:50`(ORDER idx2, 유일 소비처 app.jsx). panels 버전은 ORDER상 항상 덮여 실행되지 않던 데드코드.
- **code-viewer.jsx**: `function CodeBlock({code})`(하이라이터) → `CvCodeBlock` 리네임(정의·호출부·window export 3곳). strategy-inspector.jsx의 `function CodeBlock`(plain, ORDER 뒤)이 충돌서 이겨 code-viewer가 평이 `<pre>`로 렌더하던 버그(Phase14.4 리뷰 발견) 수정 → CvCodeBlock(highlightPython→`{ln,parts:[{cls:"tok-kw"}]}`→`<span className={cls}>`)로 하이라이팅 복구. strategy-inspector의 CodeBlock은 이제 유일(내부 전용).
- **test_no_duplicate_globals.py**(신규): 순수 Python(node 비의존), 26 .jsx 최상위 function/const/let/class 선언 이름 중복 검출. 단일 번들 전역 스코프에서 동명 선언이 조용히 덮어쓰는 충돌 클래스를 영구 차단(P1 수정의 회귀 가드). `const {…}=React`(구조분해)·`const x=window.x`(별칭)는 한 파일 1선언이라 무해.

## 검증
- **하이라이터 복구**: code-viewer가 CvCodeBlock 렌더(소스 확인) — highlightPython 토큰→className span. code-viewer에 잔여 `<CodeBlock` 0.
- **데드 제거**: panels RunComparePanel 참조 0, run-compare 정본 1, 번들 app.js RunComparePanel=1.
- **가드**: test_no_duplicate_globals 통과(P1 후 중복 0). 빌드 하네스+가드 10/10.
- **실화면**: 8771 6탭 0 pageerror. CvCodeBlock·RunComparePanel·CodeBlock(strategy) 전역 정상.
- **게이트**: 전체 pytest 신규 실패 0(P0.5 후 베이스라인 7 + 11 skip) + verify_nonrelease exit0 + 코드리뷰.

## 다음
P4-functional(백테 CSV·드릴다운·엔진게이지/LWC 라벨) → P2(라이브차트 통합·결정 동선) → P3(통합·공유유틸) → Design.
