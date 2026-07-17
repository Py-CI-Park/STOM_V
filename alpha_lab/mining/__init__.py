"""alpha_lab.mining — P1 규칙 채굴 (결정트리 리프 전수 → 통계 게이트 → 채택).

mine_rules(trees)로 리프 전수를 뽑고(전체 리프 수 = n_trials 후보 수),
evaluate_leaves(stats)로 일 블록 부트스트랩 CI·p와 BH-FDR 생존을 부착한 뒤
adopt(stats)의 봉인 게이트(lift/support/FDR/전 연도 lift 동시 충족)로
채택 리프를 고른다. 통계 원식은 alpha_lab.stats_common 단일 원본을 재사용한다.

v3 additive — EV 채택 경로(preregistration_v3 봉인 50d3d38a):
adopt_by_ev(ev_adopt)는 lift 대신 EV(mean L3_net)의 일블록 부트스트랩
CI_low>0·연도별 EV>0·support·FDR 동시 게이트, transition(전이 샘플러)은
규칙의 FALSE→TRUE onset만 추출해 EV·일평균 전이율([5,60] 예산)을 재측정한다.
"""
from alpha_lab.mining.ev_adopt import adopt_by_ev
from alpha_lab.mining.stats import adopt, evaluate_leaves, rule_mask
from alpha_lab.mining.transition import (
    TRANSITION_RATE_BUDGET,
    extract_transitions,
    measure_transition_ev,
    series_ids_from,
    state_mask,
    transition_mask,
)
from alpha_lab.mining.trees import mine_rules

__all__ = [
    "TRANSITION_RATE_BUDGET",
    "adopt",
    "adopt_by_ev",
    "evaluate_leaves",
    "extract_transitions",
    "measure_transition_ev",
    "mine_rules",
    "rule_mask",
    "series_ids_from",
    "state_mask",
    "transition_mask",
]
