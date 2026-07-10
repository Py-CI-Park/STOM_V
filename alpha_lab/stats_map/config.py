"""봉인 상수 단일 출처 — 사전등록(2026-07-10_s_track_preregistration.md) 정합.

여기의 어떤 값도 측정 결과로 사후 변경하지 않는다(사전등록 규율). 변경은
새 사전등록으로만 가능하다. param_sha()가 이 상수 묶음의 지문을 만들어
build_receipts에 남긴다 — 같은 지문이면 같은 파라미터로 빌드된 것이다.
"""
from __future__ import annotations

import hashlib
import json
from typing import Dict, Tuple

# ── 창(09:00:00~09:30:00, 초 단위) — tick DB 실측 커버리지와 동일. ──────────
WINDOW_START_HMS = "090000"       # 창 시작(초 오프셋 0).
WINDOW_END_HMS = "093000"         # 창 끝(초 오프셋 1800) = 절단 기준 "장 마감".
WINDOW_SECONDS = 1800             # 09:00:00→09:30:00 오프셋 최댓값.
GRID_START_OFFSET = 1             # t0 그리드 첫 오프셋 = 09:00:01(entry=t0+1s).

# ── 셀 축(사전등록 §3 — 프로파일링 Q1/Q2 채택, 봉인). ────────────────────────
TIME_BUCKET_SECONDS = 300         # 5분 = 300초 버킷.
TIME_BUCKETS = (900, 905, 910, 915, 920, 925)  # 버킷 라벨(HHMM 축약).
UPDOWN_EDGES = (1.71, 3.47, 6.70)     # 등락율 4분위 경계(발견창 2022-2023 봉인).
MKTCAP_EDGES = (1000.0, 3000.0)       # 시가총액 3구간 경계(억원): <1000/1000-3000/3000+.
MIN_CELL_N = 2000                     # 3축 셀 판정 바닥(P3 교훈 — 미달은 insufficient).

# ── 라벨 지평(사전등록 §4 — tick {60,180,300}, 600 제외). ───────────────────
HORIZONS: Tuple[int, ...] = (60, 180, 300)
PROB_THRESHOLDS = (0.0, 0.01)         # P(net≥0), P(net≥+1%).

# ── 서지 온셋(사전등록 §2 / 프로파일링 §7 — L1 게이트 전용). ────────────────
SURGE_WINDOW_SEC = 30             # "직전 30초 평균" 창.
SURGE_MIN_OBS = 10               # 그 창 안 관측 최소 10.
SURGE_THRESHOLD = 2.0            # 초당거래대금 > 평균 × 2.0.
ONSET_COOLDOWN_SEC = 30          # 동일 종목 연속 온셋 30초 쿨다운.

# ── 부트스트랩(사전등록 §4 항목6 — 일블록, n_boot 400). ─────────────────────
N_BOOT = 400
BUILD_SEED = 20260710            # 결정론 시드(재현성 게이트 근거).

# ── 축 집합·지도 종류 식별자. ──────────────────────────────────────────────
AXIS_TIME_UD = "time_ud"          # 1차 지도 = 2축(시간대×등락율).
AXIS_TIME_MC_UD = "time_mc_ud"    # 2차 지도 = 3축(+시총).
AXIS_SETS = (AXIS_TIME_UD, AXIS_TIME_MC_UD)
MAP_L0 = "l0"                     # 지형 지도(전 그리드).
MAP_L1 = "l1"                     # 온셋 지도(서지 온셋 표본).

# ── corr_matrix 후보 변수(프로파일링 corr_matrix 정합). ─────────────────────
CORR_VARS = ("minute", "mktcap", "updown", "surge", "strength", "rest_ratio")


def param_sha() -> str:
    """봉인 파라미터 묶음의 sha256(16자리 축약) — 빌드 영수증용 지문."""
    payload = _param_payload()
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _param_payload() -> Dict[str, object]:
    """param_sha의 원천 dict — 상수 변경이 지문에 반영되도록 전부 포함."""
    return {
        "window": [WINDOW_START_HMS, WINDOW_END_HMS, WINDOW_SECONDS,
                   GRID_START_OFFSET],
        "time_buckets": list(TIME_BUCKETS),
        "time_bucket_seconds": TIME_BUCKET_SECONDS,
        "updown_edges": list(UPDOWN_EDGES),
        "mktcap_edges": list(MKTCAP_EDGES),
        "min_cell_n": MIN_CELL_N,
        "horizons": list(HORIZONS),
        "prob_thresholds": list(PROB_THRESHOLDS),
        "surge": [SURGE_WINDOW_SEC, SURGE_MIN_OBS, SURGE_THRESHOLD,
                  ONSET_COOLDOWN_SEC],
        "bootstrap": [N_BOOT, BUILD_SEED],
        "corr_vars": list(CORR_VARS),
    }
