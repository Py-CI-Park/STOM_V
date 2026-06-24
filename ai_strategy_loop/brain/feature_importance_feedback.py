"""P3 — 세그먼트별 feature_importance 'prefer 힌트' 환류 (순수·무예외).

목표: 백테 결과 per-trade CSV를 시총/시간대 세그먼트로 쪼개(feature_importance_by_segment),
각 셀에서 승/패를 가장 강하게 가른 진입 피처(B_*)와 그 분위 승률 격차를 다음 세대
**매수(BUY)** 프롬프트에 'prefer 힌트'로 환류한다. segment_feedback(패배 구간 avoid)과
짝을 이루는 양(prefer)의 신호다 — "어느 시총×시간대에서 어느 변수의 상단/하단을 노려라".

설계 제약(분석/프롬프트 보조 전용):
  - **하드게이트(compute_fitness)·엔진·backtest_graph에 무영향**이다. NL 힌트 라인 리스트만
    만든다(생성 프롬프트 넛지).
  - 순수·무예외: 파일 없음/빈 파일/읽기 실패/데이터 부족은 **빈 리스트**로 흡수한다(graceful).
  - 결정론: feature_importance_by_segment의 라벨링/그룹핑을 그대로 따르고, 셀·피처 선택도
    결정론적이다(동일 입력→동일 출력).
  - holdout 가드: train CSV에서만 호출한다(호출부 책임 — loop의 outcome.csv_path는 train).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from ai_strategy_loop.autopsy.analyze import B_TO_STOM_VAR
from ai_strategy_loop.fitness.feature_importance import feature_importance_by_segment
from cli._utils import ensure_dataframe as _ensure_dataframe

# 분위 승률 격차(상위25% 승률 - 하위25% 승률)가 이 값 이상이어야 '결정적 피처'로 환류한다.
#   작은 격차는 잡음일 수 있어 환류하지 않는다(prefer 힌트 보수화).
DEFAULT_MIN_WINRATE_GAP = 0.15

# 토큰 폭증 방지: 축별 환류 셀 수 상한(가장 격차 큰 셀부터).
MAX_CELLS_PER_AXIS = 2

# 환류 대상 축과 사람이 읽는 축 이름.
_AXES: Tuple[Tuple[str, str], ...] = (("market_cap", "시총"), ("time", "시간대"))


def _best_feature(
    feats: List[Dict[str, Any]], min_gap: float
) -> Optional[Tuple[Dict[str, Any], float]]:
    """한 세그먼트 셀의 피처 목록에서 분위 승률 격차가 가장 큰 피처를 고른다(없으면 None).

    두 분위 승률(win_rate_top_q/win_rate_bot_q)이 모두 산출됐고 |격차| >= min_gap인 피처만
    후보로 본다. 후보 중 |격차| 최대를 (피처, 격차)로 돌려준다. 후보가 없으면 None.
    """
    best: Optional[Tuple[Dict[str, Any], float]] = None
    best_abs = -1.0  # 지금까지 본 최대 |격차|(동률 시 먼저 온 상위 피처 유지용 추적값).
    for feat in feats or []:
        top = feat.get("win_rate_top_q")
        bot = feat.get("win_rate_bot_q")
        if top is None or bot is None:
            continue
        gap = float(top) - float(bot)
        if abs(gap) < min_gap:
            continue  # 최소 격차 미달(min_gap '이상'이면 통과 — 경계 포함).
        # 동률(|gap| 동일)이면 먼저 온(랭킹 상위) 피처를 유지한다 — feats는 compute_
        #   feature_importance가 |Cohen's d| 내림차순으로 정렬한 리스트라 앞쪽이 더 강하다.
        if abs(gap) > best_abs:
            best = (feat, gap)
            best_abs = abs(gap)
    return best


def _hint_line(axis_ko: str, seg_label: str, feat: Dict[str, Any], gap: float) -> str:
    """결정적 피처 하나를 매수 프롬프트용 한국어 'prefer 힌트' 라인으로 만든다.

    예) "- 시총 '소형' 구간에서는 체결강도 상단(높은 값)이 승패를 가른다
         (상위25% 승률 62% vs 하위25% 38%·표본 120건) — 이 구간 진입에 체결강도 상단을 우선하라."
    """
    col = str(feat.get("feature", "?"))
    stom = B_TO_STOM_VAR.get(col, col)
    top = feat.get("win_rate_top_q")
    bot = feat.get("win_rate_bot_q")
    n = int(feat.get("n", 0) or 0)
    top_s = f"{float(top) * 100:.0f}%" if top is not None else "?"
    bot_s = f"{float(bot) * 100:.0f}%" if bot is not None else "?"
    side_ko = "상단(높은 값)" if gap > 0 else "하단(낮은 값)"
    side_short = "상단" if gap > 0 else "하단"
    return (
        f"- {axis_ko} '{seg_label}' 구간에서는 {stom} {side_ko}이 승패를 가른다"
        f"(상위25% 승률 {top_s} vs 하위25% {bot_s}·표본 {n}건) "
        f"— 이 구간 진입에 {stom} {side_short}을 우선하라."
    )


def build_feature_importance_lines(
    df_or_path: Any,
    *,
    min_cell: int = 20,
    fine_time: bool = False,
    min_winrate_gap: float = DEFAULT_MIN_WINRATE_GAP,
) -> List[str]:
    """per-trade 결과(DataFrame 또는 CSV 경로)에서 세그먼트별 'prefer 힌트' 라인을 만든다.

    feature_importance_by_segment로 시총·시간대 셀별 피처 중요도를 산출하고, 각 셀에서
    분위 승률 격차가 가장 큰 결정적 피처를 골라 매수 프롬프트용 한국어 힌트로 만든다.
    데이터 없음/부족/읽기 실패는 **빈 리스트**로 흡수한다(graceful·무예외).

    Args:
        df_or_path: 거래 DataFrame 또는 per-trade CSV 경로(str). 경로면 BOM 자동 제거
            로더(ensure_dataframe)로 읽는다(없거나 실패하면 빈 리스트).
        min_cell: 한 세그먼트 셀이 분석되려면 필요한 최소 거래 수(잡음 셀 배제).
        fine_time: True면 시간축을 5분 시초 셀로 세분(segment_fine_time 미러).
        min_winrate_gap: 결정적 피처로 환류되려면 필요한 최소 분위 승률 격차(기본 0.15).

    Returns:
        매수 프롬프트에 append할 한국어 prefer 힌트 라인 리스트(없으면 빈 리스트).
        축 순서: market_cap → time. 각 축 내부는 격차가 큰 셀부터 최대 MAX_CELLS_PER_AXIS개.
    """
    df: Optional[pd.DataFrame]
    if isinstance(df_or_path, pd.DataFrame):
        df = df_or_path
    elif df_or_path:
        try:
            df = _ensure_dataframe(df_or_path)
        except Exception:  # noqa: BLE001 - 파일 없음/빈 파일/읽기 실패는 빈 힌트로 흡수.
            return []
    else:
        return []

    if df is None or len(df) == 0:
        return []

    lines: List[str] = []
    for axis, axis_ko in _AXES:
        try:
            by_seg = feature_importance_by_segment(
                df, axis=axis, fine_time=fine_time, min_cell=int(min_cell),
            )
        except Exception:  # noqa: BLE001 - 세그먼트 산출 실패도 빈 힌트로 흡수(graceful).
            continue
        # 셀별 최강 격차 피처를 모아 |격차| 내림차순으로 상위 셀만 환류(결정론).
        scored: List[Tuple[float, str, Dict[str, Any], float]] = []
        for seg_label, feats in by_seg.items():
            best = _best_feature(feats, min_winrate_gap)
            if best is not None:
                feat, gap = best
                scored.append((abs(gap), str(seg_label), feat, gap))
        scored.sort(key=lambda x: x[0], reverse=True)
        for _, seg_label, feat, gap in scored[:MAX_CELLS_PER_AXIS]:
            lines.append(_hint_line(axis_ko, seg_label, feat, gap))
    return lines
