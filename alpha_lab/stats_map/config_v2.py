"""V2-A 기반 교정 상수 단일 출처 — 감사(2026-07-11) 반영, 봉인.

이 모듈은 S-트랙 사전등록 V2-A(§1 기반 교정)의 두 오류 수정을 담는 유일
원천이다. 어떤 값도 측정 결과로 사후 변경하지 않는다(사전등록 규율) — 변경은
새 사전등록으로만 가능하다. v1 `config.py`(오염 경계·고정 세율)는 그대로 두고,
여기서 교정판을 별도 봉인해 v1과 물리적으로 분리한다(빌드ID `v2a_pilot_*`).

교정 2건(실험 변수 아님 — 오류 수정이므로 전 라벨에 공통 적용):
  1) 등락율 축 경계: (1.71,3.47,6.70) → (1.59,3.56,6.88).
     근거 W3-R(발견창 전량 437일·L0 3,262만 linear 분위). 오염 경계는 pooled
     20일 표본에 2024/2025 미래창이 섞여 발생 — 발견창 전용 재산정으로 교정.
  2) 매도세율 연도 키: 2022=0.23%, 2023=0.20%(발견창). 기존 고정 0.18%(2024
     실세율)는 발견창 비용을 과소평가 → 순EV 과대(낙관). 시장 무관(KOSPI=KOSDAQ
     동률). 근거 W3-R 작업2(law.go.kr lsiSeq=282431 포함).

수수료(0.015%×2)·불리체결(±2틱)·시간대 5분·시총 3구간·L1 서지 온셋·창은
v1 봉인을 그대로 재사용한다(라벨-only 원칙 — 갭 축·돌파 온셋 편입 금지).
"""
from __future__ import annotations

import hashlib
import json
from typing import Dict, Mapping

from alpha_lab.stats_map import config as _v1

__all__ = [
    "BUILD_ID_PREFIX",
    "H300_HORIZON",
    "UPDOWN_EDGES_V2",
    "YEAR_TAX_RATE",
    "param_sha_v2",
    "year_tax_rate",
]

# ── 교정 1: 등락율 축 경계(W3-R 재봉인, 유리한 쪽 선택 없음). ─────────────────
UPDOWN_EDGES_V2 = (1.59, 3.56, 6.88)

# ── 교정 2: 매도세율 연도 키(발견창=2022/2023, 미래창은 해당 연도 키). ────────
# 거래세(탄력세율)+농어촌특별세 실효 매도세율. KOSDAQ은 농특세 없이 거래세만으로
# KOSPI 합계와 동률(정책) — 시장 구분 불요. 2026-01-01 시행령 재인상 반영.
YEAR_TAX_RATE: Dict[int, float] = {
    2022: 0.0023,
    2023: 0.0020,
    2024: 0.0018,
    2025: 0.0015,
    2026: 0.0020,
}

# ── 파일럿 라벨 지평(고정 300초 청산 — 대조군 h300 교정판). ──────────────────
H300_HORIZON = 300

# ── v2 빌드ID 접두(stats_map v2 파티션 — v1과 분리). ─────────────────────────
BUILD_ID_PREFIX = "v2a_pilot"


def year_tax_rate(year: int) -> float:
    """연도 → 실효 매도세율(단일 출처 조회). 미봉인 연도는 KeyError.

    day→year 확정 빌드라 결정론이며, 세율 전파의 유일 지점이다 — h300 라벨
    경로와 L3 라벨 경로가 모두 이 함수를 거쳐야 지점 간 패리티가 성립한다.
    """
    key = int(year)
    if key not in YEAR_TAX_RATE:
        raise KeyError(
            f"봉인되지 않은 연도 세율: {key} (봉인 연도 {sorted(YEAR_TAX_RATE)})"
        )
    return YEAR_TAX_RATE[key]


def _param_payload() -> Mapping[str, object]:
    """param_sha_v2 원천 — v2 교정값 + 재사용 v1 상수 지문 결합."""
    return {
        "updown_edges_v2": list(UPDOWN_EDGES_V2),
        "year_tax_rate": {str(k): YEAR_TAX_RATE[k] for k in sorted(YEAR_TAX_RATE)},
        "h300_horizon": H300_HORIZON,
        # 재사용 v1 봉인(교정 대상 아님 — 지문에 포함해 드리프트 감지).
        "time_buckets": list(_v1.TIME_BUCKETS),
        "time_bucket_seconds": _v1.TIME_BUCKET_SECONDS,
        "mktcap_edges": list(_v1.MKTCAP_EDGES),
        "window": [_v1.WINDOW_START_HMS, _v1.WINDOW_END_HMS, _v1.WINDOW_SECONDS,
                   _v1.GRID_START_OFFSET],
        "surge": [_v1.SURGE_WINDOW_SEC, _v1.SURGE_MIN_OBS, _v1.SURGE_THRESHOLD,
                  _v1.ONSET_COOLDOWN_SEC],
        "bootstrap": [_v1.N_BOOT, _v1.BUILD_SEED],
        "fee_rate": 0.00015,
        "adverse_ticks": 2,
    }


def param_sha_v2() -> str:
    """봉인 v2 파라미터 묶음의 sha256(16자리 축약) — 빌드 영수증 지문."""
    blob = json.dumps(_param_payload(), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]
