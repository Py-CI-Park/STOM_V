"""alpha_lab.mcl — P3 호가 미시구조 조건부 레이어(MCL) 서브패키지 (research-only).

보수 설계 확정안(2026-07-05_p3_mcl_remediation_preregistration_draft.md)의
오프라인 스크리닝 코어: (a) 절단 비의존 재라벨(alpha_lab.dataset.labels
재사용 — A안), (b) identity 4-튜플 거래 dedup(alpha_lab.distill.ledger_wiring
재사용), (c) 분위수 lift 스크리닝(alpha_lab.stats_common 재사용, ML-free).
실 CSV 스캔·tick 재조인 실행·봉인 파일 생성은 이 패키지 밖(다음 라운드)이다.
"""

from alpha_lab.mcl.screening import (
    C1_RETURN_TOL,
    DISCOVERY_END_DAY,
    ENTRY_HMS_MAX,
    ENTRY_HMS_MIN,
    FDR_Q,
    L1_HORIZONS,
    LABEL_TARGETS,
    MAE_TAIL_PCT,
    MAE_TARGET,
    MFE_TARGET,
    MIN_CELL_N,
    MIN_POOL_N,
    N_QUANTILES,
    PATH_WINDOW_SEC,
    TRIAL_INSUFFICIENT,
    TRIAL_NO_POSITIVES,
    TRIAL_OK,
    VALID_TRIAL_MIN_FRACTION,
    YEAR_AGREE_MIN_FRACTION,
    apply_fdr,
    build_targets,
    dedup_trades,
    filter_discovery,
    quantile_cells,
    relabel_trade,
    relabel_trades,
    screen_trials,
    screen_verdict,
)

__all__ = [
    "C1_RETURN_TOL",
    "DISCOVERY_END_DAY",
    "ENTRY_HMS_MAX",
    "ENTRY_HMS_MIN",
    "FDR_Q",
    "L1_HORIZONS",
    "LABEL_TARGETS",
    "MAE_TAIL_PCT",
    "MAE_TARGET",
    "MFE_TARGET",
    "MIN_CELL_N",
    "MIN_POOL_N",
    "N_QUANTILES",
    "PATH_WINDOW_SEC",
    "TRIAL_INSUFFICIENT",
    "TRIAL_NO_POSITIVES",
    "TRIAL_OK",
    "VALID_TRIAL_MIN_FRACTION",
    "YEAR_AGREE_MIN_FRACTION",
    "apply_fdr",
    "build_targets",
    "dedup_trades",
    "filter_discovery",
    "quantile_cells",
    "relabel_trade",
    "relabel_trades",
    "screen_trials",
    "screen_verdict",
]
