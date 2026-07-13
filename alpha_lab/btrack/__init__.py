"""B-트랙 가지(branch) 분해 — 챔피언 자기 깊은 조건식의 프레임 검증 (봉인본 `plans/2026-07-13_b_track_branch_decomposition_preregistration.md` §14).

챔피언 RR8_12 는 시간-분리 DNF(902 24절 AND ∨ 905 26절 AND). O-4 flat-39-AND 프록시가
구조적 공집합(bit_6∧bit_21=0)이었음을 규명하고, 가지 AND 합집합(정본 발동 프록시)의 은행
mean L3 로 프레임을 검증한다: (a) 양(+) → 깊은 좌표 존재 / (b) 명확한 음 → 프레임 갭 확정
(엔진 진입 프레임 피벗) / (c) CI 0 걸침 → 검정력 부족·판정 유보.

- branches : §3 매핑 상수(902/905 비트 튜플·공통 등뼈).
- judge_b  : 무결성 → 가지/anchor mean L3·CI·등급·FDR·3분법·엔진 갭.

기존 파일 무수정 — clause_lab(무결성·MDE)·o4lab(단일군 부트스트랩)·stats_common(FDR) 재사용만.
신규 비트 0·신규 스캔 0·엔진 0.
"""
