"""D9 moneytop 전이 온셋 × L3 출구 접목 — 측정 패키지 (R1 추출 + R3 대조).

봉인본: docs/research/condition_research/plans/2026-07-12_d5_d9_transition_onset_preregistration.md (§14 확정).

레인 규율:
- 온셋 = 저장 관심종목 플래그 행-시퀀스의 0→1 전이(프로브 probe_min_d9 정의 그대로).
- L3 라벨 = 봉인 pilot_v2._l3_labels 이중 세율 규약(§14-8): 발화는 엔진 0.18% 의미론
  (labels_v2.build_l3_labels), 실현은 연도 세율 재계상(costs_v2, 2022=0.23%/2023=0.20%).
- 서지 기준선은 기존 onset_l3_bank.parquet(863,446행/유효 862,932)을 read-only 로만 소비.
- Δ CI = 전이·서지 동시 일자블록 차 부트스트랩(judge.day_block_diff_bootstrap, n_boot 400).
- 원본 tick DB read-only(URI mode=ro). 엔진 백테 0회. git 커밋은 메인 세션 몫.
"""
from __future__ import annotations

__all__ = ["transitions", "overlap", "judge_d9", "run"]
