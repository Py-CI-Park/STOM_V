"""O-3 돌파 온셋 × L3 출구 접목 — 측정 패키지 (추출 + 게이트 + 판정).

봉인본: docs/research/condition_research/plans/2026-07-12_o3_breakout_onset_preregistration.md (§14 확정).

레인 규율(§14 봉인):
- 온셋 = 가격이 벽을 뚫는 순간(돌파). 5변형 P20/P300/DH/OP/VI(detect.VARIANTS).
  상태 교차(t_prev=직전 present 행)+30초 쿨다운(VI 제외)+워밍업 30초(F7).
- L3 라벨 = 봉인 pilot_v2._l3_labels 이중 세율 규약(§14-8·F6): 발화 = 엔진 0.18%
  의미론(labels_v2.build_l3_labels), 실현 = 연도 세율 재계상(costs_v2). 래퍼만.
- 판정 = 변형×모집단(전체/서지-비중첩 ±30) 단독 절대 EV(mean≥+0.10%p·CI하한>0·
  BH-FDR q=0.10·연도 동부호). 서지 기준선 onset_l3_bank.parquet read-only 소비.
- extract.py 무수정(F6) — 돌파 컬럼은 detect.load_dense_o3(gap_o1g 선례) 자체 로더.
  onset_bank_v2.py 무수정 — 은행 스키마는 o3lab.bank 자체 정의(v2+variant, F5).
- 원본 tick DB read-only(URI mode=ro). 엔진 백테 0회. git 커밋은 메인 세션 몫.
"""
from __future__ import annotations

__all__ = ["detect", "breakouts", "bank", "judge", "run"]
