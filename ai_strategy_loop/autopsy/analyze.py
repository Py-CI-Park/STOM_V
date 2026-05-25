"""부검 분석 — working-window 거래 CSV에서 수익/손실을 가른 진입 조건을 찾는다.

핵심 신호: 14개 진입시점 컬럼(B_*) 각각에 대해 수익 그룹 평균과 손실 그룹 평균을
구하고, 표준화 평균차(Cohen's-d 류)로 변별력을 매긴다.

    std_mean_diff = (win_mean - loss_mean) / pooled_std

부호(>0)는 "수익 거래에서 그 값이 더 컸다", 음수는 "손실 거래에서 더 컸다"를 뜻한다.
|std_mean_diff| 가 클수록 그 진입 조건이 승패를 더 잘 갈랐다는 의미다.

데이터 모양으로는 절대 예외를 던지지 않는다(상태 코드로 깔끔히 반환). 단, 부검은
working/train 거래에서만 돌아야 하므로 is_holdout=True 면 ValueError 를 던진다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd

# 수익률 컬럼: >0 이면 수익(win), <=0 이면 손실(loss).
RETURN_COLUMN = "수익률"

# 진입시점(B_*) 컬럼 — backtest/back_static.py TRADE_RESULT_B_COLUMNS 와 동일.
B_COLUMNS = [
    "B_현재가", "B_등락율", "B_당일거래대금", "B_거래대금증감", "B_체결강도",
    "B_시가총액", "B_회전율", "B_전일동시간비", "B_매수총잔량", "B_매도총잔량",
    "B_시분초", "B_분봉시가", "B_분봉고가", "B_분봉저가",
]

# 변별 변수가 매핑되는 실제 STOM 진입 변수(요약 가이드에서 튜닝 힌트로 사용).
B_TO_STOM_VAR = {
    "B_현재가": "현재가",
    "B_등락율": "등락율",
    "B_당일거래대금": "당일거래대금",
    "B_거래대금증감": "거래대금증감",
    "B_체결강도": "체결강도",
    "B_시가총액": "시가총액",
    "B_회전율": "회전율",
    "B_전일동시간비": "전일동시간비",
    "B_매수총잔량": "매수총잔량",
    "B_매도총잔량": "매도총잔량",
    "B_시분초": "시분초",
    "B_분봉시가": "분봉시가",
    "B_분봉고가": "분봉고가",
    "B_분봉저가": "분봉저가",
}

# 최소 거래 수. 이 미만이면 통계가 의미 없어 insufficient_trades 로 처리한다.
DEFAULT_MIN_TRADES = 10

STATUS_OK = "ok"
STATUS_INSUFFICIENT = "insufficient_trades"
STATUS_SINGLE_CLASS = "single_class"


@dataclass
class Discriminator:
    """한 진입(B_*) 컬럼의 수익/손실 변별 통계."""

    column: str
    win_mean: float
    loss_mean: float
    std_mean_diff: float  # (win_mean - loss_mean) / pooled_std (Cohen's-d 류)


@dataclass
class AutopsyResult:
    """부검 1회 결과.

    status:
      - 'ok'                  : 변별 통계 산출됨 (discriminators 채워짐).
      - 'insufficient_trades' : 거래 0건 또는 min_trades 미만 (통계 무의미).
      - 'single_class'        : 전부 수익 또는 전부 손실 (변별 불가).
    """

    trade_count: int
    win_count: int
    loss_count: int
    discriminators: List[Discriminator] = field(default_factory=list)
    status: str = STATUS_OK
    note: str = ""
    min_trades: int = DEFAULT_MIN_TRADES


def _pooled_std(win_vals: pd.Series, loss_vals: pd.Series) -> float:
    """두 그룹의 합동 표준편차(pooled std). 표본<2인 그룹은 std=0으로 본다."""
    win_std = float(win_vals.std(ddof=1)) if len(win_vals) >= 2 else 0.0
    loss_std = float(loss_vals.std(ddof=1)) if len(loss_vals) >= 2 else 0.0
    n_w, n_l = len(win_vals), len(loss_vals)
    if n_w + n_l <= 2:
        return 0.0
    # pooled variance (각 그룹 자유도 가중).
    num = (max(n_w - 1, 0)) * (win_std ** 2) + (max(n_l - 1, 0)) * (loss_std ** 2)
    den = n_w + n_l - 2
    if den <= 0:
        return 0.0
    var = num / den
    return float(var ** 0.5)


def analyze_trades(
    csv_path: str,
    *,
    min_trades: int = DEFAULT_MIN_TRADES,
    is_holdout: bool = False,
) -> AutopsyResult:
    """거래 CSV를 읽어 진입 조건의 수익/손실 변별력을 분석한다.

    Args:
        csv_path: 백테스트 결과 CSV(utf-8-sig, 거래당 1행, '수익률' 컬럼 보유).
        min_trades: 통계 산출 최소 거래 수 (미만이면 insufficient_trades).
        is_holdout: True면 ValueError (부검은 working/train 거래에서만, RV2-4/A5).

    Returns:
        AutopsyResult. 데이터 모양 문제(0건/단일클래스/B_컬럼없음)는 예외가 아니라
        status 로 표현한다.

    Raises:
        ValueError: is_holdout=True 일 때.
    """
    if is_holdout:
        raise ValueError(
            "autopsy must run on working/train trades only — holdout 거래로는 부검 금지 (RV2-4/A5)"
        )

    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
    except pd.errors.EmptyDataError:
        # 완전히 빈 파일(헤더조차 없음) — 거래 0건과 동일하게 처리.
        return AutopsyResult(
            trade_count=0, win_count=0, loss_count=0,
            status=STATUS_INSUFFICIENT, min_trades=min_trades,
            note="CSV가 비어 있다 — 거래 0건.",
        )

    if RETURN_COLUMN not in df.columns:
        return AutopsyResult(
            trade_count=int(len(df)), win_count=0, loss_count=0,
            status=STATUS_INSUFFICIENT, min_trades=min_trades,
            note=f"수익률 컬럼('{RETURN_COLUMN}')이 없어 승패를 가를 수 없다.",
        )

    # 수익률을 숫자로 강제 변환, 결측 행 제거.
    returns = pd.to_numeric(df[RETURN_COLUMN], errors="coerce")
    valid_mask = returns.notna()
    df = df.loc[valid_mask].reset_index(drop=True)
    returns = returns.loc[valid_mask].reset_index(drop=True)

    trade_count = int(len(df))
    is_win = returns > 0
    win_count = int(is_win.sum())
    loss_count = trade_count - win_count

    # 0건 또는 min_trades 미만 → insufficient.
    if trade_count == 0:
        return AutopsyResult(
            trade_count=0, win_count=0, loss_count=0,
            status=STATUS_INSUFFICIENT, min_trades=min_trades,
            note="거래 0건 — 진입이 한 번도 발생하지 않았다.",
        )
    if trade_count < min_trades:
        return AutopsyResult(
            trade_count=trade_count, win_count=win_count, loss_count=loss_count,
            status=STATUS_INSUFFICIENT, min_trades=min_trades,
            note=f"거래 {trade_count}건 < 최소 {min_trades}건 — 통계가 무의미하다.",
        )

    # 전부 수익 또는 전부 손실 → 변별 불가.
    if win_count == 0 or loss_count == 0:
        only = "수익" if loss_count == 0 else "손실"
        return AutopsyResult(
            trade_count=trade_count, win_count=win_count, loss_count=loss_count,
            status=STATUS_SINGLE_CLASS, min_trades=min_trades,
            note=f"모든 거래가 {only} — 수익/손실 변별이 불가능하다.",
        )

    # --- 변별 통계: 존재하는 B_* 컬럼별 표준화 평균차 ---
    present = [c for c in B_COLUMNS if c in df.columns]
    discriminators: List[Discriminator] = []
    for col in present:
        vals = pd.to_numeric(df[col], errors="coerce")
        win_vals = vals[is_win].dropna()
        loss_vals = vals[~is_win].dropna()
        if len(win_vals) == 0 or len(loss_vals) == 0:
            continue
        win_mean = float(win_vals.mean())
        loss_mean = float(loss_vals.mean())
        pooled = _pooled_std(win_vals, loss_vals)
        if pooled <= 1e-12:
            # 분산이 ~0 (모든 값 동일): 변별력 0으로 둔다(0 나눗셈 가드).
            smd = 0.0
        else:
            smd = (win_mean - loss_mean) / pooled
        discriminators.append(
            Discriminator(
                column=col, win_mean=win_mean, loss_mean=loss_mean,
                std_mean_diff=float(smd),
            )
        )

    # |std_mean_diff| 내림차순 정렬 (가장 잘 가른 조건 먼저).
    discriminators.sort(key=lambda d: abs(d.std_mean_diff), reverse=True)

    note = (
        f"거래 {trade_count}건 (수익 {win_count} / 손실 {loss_count}), "
        f"분석 B_컬럼 {len(discriminators)}개."
    )
    return AutopsyResult(
        trade_count=trade_count, win_count=win_count, loss_count=loss_count,
        discriminators=discriminators, status=STATUS_OK, min_trades=min_trades,
        note=note,
    )
