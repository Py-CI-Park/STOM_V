"""M1 (2026-06-11) — 두 전략의 거래 중복도 분석 (advisory).

V6 운용 결정("시드 대체 vs 보완")의 직접 입력이다: 후보가 시드와 거의 같은
거래를 하면(중복도 높음) '보완'은 같은 베팅을 두 배로 거는 것에 불과하고,
중복도가 낮으면 포트폴리오 결합 가치가 있다. per-trade CSV 두 개만 읽으므로
백테스트 0회. 어떤 실패도 None으로 흡수한다(advisory 계약).

키 정의: (종목명, 매수시간 분 단위 절사 YYYYMMDDHHMM) — 같은 분에 같은
종목을 산 거래는 동일 기회로 본다(초 단위 차이는 체결 우연).
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Set, Tuple


def _trade_keys(csv_path: str) -> Optional[Tuple[Set[Tuple[str, str]], float]]:
    """CSV에서 (거래 키 집합, 총수익금)을 읽는다. 실패는 None."""
    try:
        import pandas as pd  # noqa: PLC0415 - 무거운 import는 호출 시점에만.

        path = Path(csv_path)
        if not path.is_file():
            return None
        df = pd.read_csv(path, encoding="utf-8-sig")
        if "종목명" not in df.columns or "매수시간" not in df.columns:
            return None
        keys = set(zip(
            df["종목명"].astype(str),
            df["매수시간"].astype(str).str[:12],  # YYYYMMDDHHMM (분 절사).
        ))
        total = float(df["수익금"].sum()) if "수익금" in df.columns else 0.0
        return keys, total
    except Exception:  # noqa: BLE001 - advisory.
        return None


def trade_overlap(csv_a: str, csv_b: str) -> Optional[Dict[str, object]]:
    """두 전략 CSV의 거래 중복도(Jaccard)와 해석 라벨을 반환한다.

    - jaccard: |교집합| / |합집합| (0=완전 분리, 1=동일 거래).
    - interpretation: 운용 결정 참고 라벨(사전선언 구간 —
      >=0.8 사실상 동일 / 0.4~0.8 부분 중복 / <0.4 낮은 중복).
    """
    a = _trade_keys(csv_a)
    b = _trade_keys(csv_b)
    if a is None or b is None:
        return None
    keys_a, _total_a = a
    keys_b, _total_b = b
    if not keys_a and not keys_b:
        return None
    common = keys_a & keys_b
    union = keys_a | keys_b
    jaccard = len(common) / max(len(union), 1)
    if jaccard >= 0.8:
        label = "사실상 동일 거래 — '보완'은 동일 베팅 2배와 같음(대체 검토)"
    elif jaccard >= 0.4:
        label = "부분 중복 — 보완 시 중복 구간 리스크 합산 주의"
    else:
        label = "낮은 중복 — 포트폴리오 결합 가치 후보"
    return {
        "n_trades_a": len(keys_a),
        "n_trades_b": len(keys_b),
        "n_common": len(common),
        "jaccard": round(jaccard, 4),
        "interpretation": label,
        "note": "advisory — V6 운용 결정(대체 vs 보완) 참고용, 판정 미사용",
    }
