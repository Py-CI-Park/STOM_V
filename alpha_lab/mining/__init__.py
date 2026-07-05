"""alpha_lab.mining — P1 규칙 채굴 (결정트리 리프 전수 → 통계 게이트 → 채택).

mine_rules(trees)로 리프 전수를 뽑고(전체 리프 수 = n_trials 후보 수),
evaluate_leaves(stats)로 일 블록 부트스트랩 CI·p와 BH-FDR 생존을 부착한 뒤
adopt(stats)의 봉인 게이트(lift/support/FDR/전 연도 lift 동시 충족)로
채택 리프를 고른다. 통계 원식은 alpha_lab.stats_common 단일 원본을 재사용한다.
"""
from alpha_lab.mining.stats import adopt, evaluate_leaves, rule_mask
from alpha_lab.mining.trees import mine_rules

__all__ = ["adopt", "evaluate_leaves", "mine_rules", "rule_mask"]
