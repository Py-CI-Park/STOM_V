"""exitlab_r — D5-R 조건부 청산 사전등록 실행 인프라(포렌식·리플레이 triage).

봉인 근거: docs/research/condition_research/plans/
2026-07-12_d5r_conditional_exit_preregistration.md (커밋 ac5ca448).

현직 rr8_12 매도식(sha 8ef01e0e)을 1바이트도 바꾸지 않고, 매도 exec
네임스페이스 실측 스칼라 3종(보유시간·최고수익률[누적최대]·수익률)만으로
정의한 청산 변형(Family A 트레일링 완화, Family B 저활력 조기 절단)의
반사실 청산을 계산한다. 엔진 백테 0회 — 전부 tick DB(read-only) 리플레이.

두 경로(순수 스칼라 / 벡터)를 제공하며 L3 재현 게이트가 둘의 등가를
검증한 뒤에만 벡터 경로를 신뢰한다(labels_v2 등가성 게이트 상속).
"""
from alpha_lab.exitlab_r.patch_exit import (
    B_CLAUSE_TAG,
    ExitResult,
    Patch,
    PathAnalysis,
    analyze_path,
    replay_patched_pure,
    replay_patched_vector,
    time_stop_cut,
)

__all__ = [
    "B_CLAUSE_TAG",
    "ExitResult",
    "Patch",
    "PathAnalysis",
    "analyze_path",
    "replay_patched_pure",
    "replay_patched_vector",
    "time_stop_cut",
]
