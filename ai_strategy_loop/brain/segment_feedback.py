"""T4 반복 정제 폐루프 — 패배 세그먼트 'avoid 가이드' 환류 (순수·무예외).

목표: 백테 결과 per-trade CSV를 시간대×시총×등락률 셀로 쪼개(edge_by_segment),
'패배·불필요 구간'(만성 적자/저승률 셀)을 다음 세대 **매수(BUY)** 프롬프트에
'avoid 라인'으로 환류한다. 루프가 스스로 불필요 구간을 줄이며 재생성하게 하는
"실행→분석→불필요 구간 제거→재생성" 폐루프의 환류 헬퍼다.

설계 제약(분석/프롬프트 보조 전용):
  - **하드게이트(compute_fitness)·엔진·backtest_graph에 무영향**이다. 이 모듈은 결과
    CSV를 읽어 NL avoid 라인 리스트만 만든다(생성 프롬프트 넛지).
  - 순수·무예외: 파일 없음/빈 파일/읽기 실패/데이터 부족은 **빈 리스트**로 흡수한다
    (graceful). 어떤 입력에도 예외를 던지지 않는다.
  - 결정론: edge_by_segment의 라벨링/정렬(avg_return 오름차순)을 그대로 따르고,
    패배 셀 추출·avoid 라인 생성도 결정론적이다(동일 입력→동일 출력).

라벨링은 fitness/edge_ratio.edge_by_segment(=cli/research_segments 재사용)를 그대로
쓴다 — 시총 자동 단위추론·시간 버킷(coarse 또는 fine)·등락률 버킷.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from ai_strategy_loop.fitness.edge_ratio import edge_by_segment
from cli._utils import ensure_dataframe as _ensure_dataframe

# 패배 셀 판정 임계: 승률이 이 값 미만이면 '저승률'(적자가 아니어도 비효율 구간).
#   total_profit<0(적자)이거나 win_rate<이 값이면 패배 셀로 본다(AND가 아니라 OR).
DEFAULT_LOSS_WIN_RATE = 0.45

# avoid 라인 토큰 폭증 방지: 축별 상위 패배 셀 개수 상한(가장 적자/저승률부터).
#   edge_by_segment가 avg_return 오름차순 정렬이라 앞쪽이 가장 나쁜 셀이다.
MAX_LINES_PER_AXIS = 2
# cross(시간대×시총) 축은 상호작용 신호라 가장 나쁜 한 조합만 환류한다.
MAX_CROSS_LINES = 1

# 환류 대상 축과 사람이 읽는 축 이름(avoid 문구 framing용).
_AXIS_LABELS = {
    "time": "시간대",
    "market_cap": "시총",
    "change": "등락률",
    "cross": "시간대×시총",
}


def _is_losing_cell(cell: Dict[str, Any], min_count: int, loss_win_rate: float) -> bool:
    """한 세그먼트 셀이 '패배·불필요 구간'인지 판정한다(결정론).

    조건: count >= min_count (표본 충분) AND (total_profit < 0 OR win_rate < loss_win_rate).
    total_profit이 None(수익금 컬럼 부재)이면 적자 판정은 건너뛰고 승률만 본다.
    """
    count = int(cell.get("count", 0) or 0)
    if count < min_count:
        return False
    total_profit = cell.get("total_profit")
    is_loss = total_profit is not None and float(total_profit) < 0.0
    win_rate = cell.get("win_rate")
    is_low_win = win_rate is not None and float(win_rate) < loss_win_rate
    return bool(is_loss or is_low_win)


def _avoid_line(axis: str, cell: Dict[str, Any]) -> str:
    """패배 셀 하나를 매수 프롬프트용 한국어 avoid 라인으로 만든다.

    예) "- 시간대 '0915-0920' 구간은 최근 백테서 적자(승률 38%·평균 -1.2%·표본 12건)
         — 이 구간 진입을 피하거나 더 엄격히 게이트하라."
    """
    axis_ko = _AXIS_LABELS.get(axis, axis)
    label = str(cell.get("label", "?"))
    count = int(cell.get("count", 0) or 0)
    win_rate = cell.get("win_rate")
    win_pct = f"{float(win_rate) * 100:.0f}%" if win_rate is not None else "?"
    avg_return = cell.get("avg_return")
    avg_s = f"{float(avg_return):.2g}%" if avg_return is not None else "?"
    total_profit = cell.get("total_profit")
    verdict = "적자" if (total_profit is not None and float(total_profit) < 0.0) else "저승률"
    return (
        f"- {axis_ko} '{label}' 구간은 최근 백테서 {verdict}"
        f"(승률 {win_pct}·평균 {avg_s}·표본 {count}건) "
        f"— 이 구간 진입을 피하거나 더 엄격히 게이트하라."
    )


def build_segment_avoid_lines(
    df_or_path: Any,
    *,
    min_count: int = 8,
    fine_time: bool = False,
    loss_win_rate: float = DEFAULT_LOSS_WIN_RATE,
) -> List[str]:
    """per-trade 결과(DataFrame 또는 CSV 경로)에서 '패배 셀' avoid 라인 리스트를 만든다.

    "실행→분석→불필요 구간 제거→재생성" 폐루프의 환류 헬퍼(순수·무예외). 결과를
    시간대×시총×등락률×교차 셀로 쪼개(edge_by_segment) 패배 셀(표본 충분 + 적자/저승률)을
    추출하고, 각 셀을 매수 프롬프트용 한국어 avoid 라인으로 만든다. 데이터 없음/부족/
    읽기 실패는 **빈 리스트**로 흡수한다(graceful).

    Args:
        df_or_path: 거래 DataFrame, 또는 per-trade CSV 경로(str). 경로면 BOM 자동 제거
            로더(ensure_dataframe)로 읽는다(없거나 실패하면 빈 리스트).
        min_count: 패배 셀로 지목되려면 필요한 셀 최소 표본 수(잡음 배제).
        fine_time: True면 세그먼트 시간축을 5분 시초 셀로 세분(segment_fine_time 미러).
        loss_win_rate: 이 승률 미만이면 '저승률' 패배 셀로 본다(기본 0.45).

    Returns:
        매수 프롬프트에 append할 한국어 avoid 라인 리스트(없으면 빈 리스트).
        축 순서: time → market_cap → change → cross. 각 축 내부는 가장 나쁜 셀부터
        (edge_by_segment의 avg_return 오름차순 정렬을 그대로 따름).
    """
    # --- DataFrame 확보(경로면 무예외 로드) ---
    df: Optional[pd.DataFrame]
    if isinstance(df_or_path, pd.DataFrame):
        df = df_or_path
    elif df_or_path:
        try:
            df = _ensure_dataframe(df_or_path)
        except Exception:  # noqa: BLE001 - 파일 없음/빈 파일/읽기 실패는 빈 가이드로 흡수.
            return []
    else:
        return []

    if df is None or len(df) == 0:
        return []

    # min_count는 곧 세그먼트 셀 최소표본(edge_by_segment의 min_samples)으로도 쓴다 —
    #   표본 미달 셀은 애초에 반환되지 않아 _is_losing_cell의 count 검사와 일치한다.
    try:
        segments = edge_by_segment(df, fine_time=fine_time, min_samples=max(int(min_count), 1))
    except Exception:  # noqa: BLE001 - 세그먼트 산출 실패도 빈 가이드로 흡수(graceful).
        return []

    lines: List[str] = []
    for axis, cap in (
        ("time", MAX_LINES_PER_AXIS),
        ("market_cap", MAX_LINES_PER_AXIS),
        ("change", MAX_LINES_PER_AXIS),
        ("cross", MAX_CROSS_LINES),
    ):
        cells = segments.get(axis) or []
        taken = 0
        for cell in cells:  # 이미 avg_return 오름차순 — 가장 나쁜 셀부터.
            if taken >= cap:
                break
            if _is_losing_cell(cell, int(min_count), loss_win_rate):
                lines.append(_avoid_line(axis, cell))
                taken += 1
    return lines


# ---------------------------------------------------------------------------
# DR-05 — AnalysisCardV3 영속 지시 렌더러. 카드가 이미 게이트(표본/CI/q값-또는
#   -사전등록축/train-only)를 통과시킨 actionable_directives 만 그대로 렌더한다
#   — 여기서 새로 판정하거나 카드 content_hash 를 재계산하지 않는다(동일-해시
#   렌더 경로 계약: analysis_card.render_card_v3_md 와 항상 같은 해시를 참조).
# ---------------------------------------------------------------------------


def render_directives_from_card_v3(card: Any) -> List[str]:
    """AnalysisCardV3.actionable_directives 를 매수 프롬프트용 라인으로 렌더한다.

    카드가 이미 train-only + 표본/CI/FDR 게이트를 통과시킨 것만 실었으므로,
    여기서는 재판정하지 않고 그대로 옮긴다. 각 라인은 카드 content_hash 를
    참조 태그로 달아, 다른 렌더 경로와 동일 정체성임을 검증 가능하게 한다.
    빈 카드/지시 0개는 빈 리스트를 돌려준다(무예외).
    """
    directives = getattr(card, "actionable_directives", None) or ()
    content_hash = getattr(card, "content_hash", "")
    lines: List[str] = []
    for directive in directives:
        statement = directive.get("statement") if isinstance(directive, dict) else None
        if statement:
            lines.append(f"[card:{content_hash}] {statement}")
    return lines
