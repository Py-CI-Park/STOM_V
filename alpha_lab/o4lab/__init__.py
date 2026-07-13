"""O-4 생성 문법 후보 — 오프라인 선별 (봉인본 `plans/2026-07-13_o4_generation_grammar_preregistration.md` §14).

검증 부품(D1 압력 4족 + 2절 결합 규칙 + 함정 회피)으로 조립한 매수 후보 158종을 서지 온셋 풀
(mean L3 −1.008%p) 위에서 재며, 양의 조건부 EV(mean L3_net ≥ +0.10%p)를 갖고 챔피언 발동과
구별되는(겹침 ≤0.50) 후보를 오프라인(엔진 0회)으로 선별한다.

- grammar   : 닫힌 문법 후보 열거(N=158)·족 태깅.
- bits      : 재도출 임계 신규 5비트 산출(발견창 온셋 위, D1 P1 경로 미러).
- gate      : 무결성 지문 + 신규 비트 패리티(엔진 exec 100%) + 포함관계 sanity.
- judge_o4  : 자격(L3 미접촉) → 발화 mean L3·일자블록 CI·FDR·겹침·분류.

기존 파일 무수정 — clause_lab(비트·패리티)·stats_map(온셋)·stats_common(FDR) import 재사용만.
"""
