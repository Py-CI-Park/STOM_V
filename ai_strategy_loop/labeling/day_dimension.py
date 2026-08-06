"""QSP10 후속 단서 — '날(day)' 차원 분석.

P3 진단에서 나온 관측: 거래수 상위 20% 일은 기대값 +0.244%, 하위 80% 일은 −0.380%.
지금 지도는 (종목, 초) 차원만 보고 **날 차원을 보지 않는다**. 이 모듈은 날을 관측 단위로
바꿔서 "그날 아침 정보만으로 유리한 날을 고를 수 있는가"를 검증한다.

**누출 금지 규율**: 날 특징은 반드시 **관측 시각 이전**의 정보만 쓴다. 예를 들어
09:00~09:05 의 시장 상태로 09:05 이후 진입의 성적을 예측하는 식이며, 그날 종일의
집계(당일 총거래대금 등)를 특징으로 쓰면 미래를 훔치는 것이다.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from ai_strategy_loop.labeling.frontier import row_values

MIN_DAYS = 60


def day_table(frame: pd.DataFrame, *, feature_end: int, entry_start: int,
              **rule) -> pd.DataFrame:
    """날 단위 표 — 이른 창(feature_end 이전)의 시장 상태 + 이후 진입의 성적.

    feature_end 이전 행에서만 특징을 만들고, entry_start 이후 행에서만 성적을 잰다.
    두 창이 겹치지 않으므로 구조적으로 누출이 없다.
    """
    if entry_start < feature_end:
        raise ValueError("특징 창과 진입 창이 겹치면 미래 정보가 샌다")
    values = row_values(frame, **rule)
    early = frame["시분초"] < feature_end
    late = frame["시분초"] >= entry_start

    early_frame = frame.loc[early]
    late_frame = frame.loc[late]
    late_values = values[late.to_numpy()]

    features = early_frame.groupby("일자").agg(
        아침_종목수=("종목코드", "nunique"),
        아침_신호수=("종목코드", "size"),
        아침_체결강도=("체결강도", "mean"),
        아침_등락율=("등락율", "mean"),
        아침_스프레드=("spread_pct", "mean"),
        아침_회전율=("회전율", "mean"),
    )
    outcome = pd.DataFrame({"일자": late_frame["일자"].to_numpy(), "value": late_values})
    performance = outcome.groupby("일자")["value"].agg(거래수="size", 기대값="mean")
    return features.join(performance, how="inner").dropna()


def rank_day_features(table: pd.DataFrame, *, buckets: int = 5) -> pd.DataFrame:
    """날 특징별 상·하위 분위 성적 — 관측 단위가 '날'이라 겹침 표본 문제가 없다."""
    records = []
    for column in table.columns:
        if column in ("거래수", "기대값"):
            continue
        codes = pd.qcut(table[column], buckets, labels=False, duplicates="drop")
        valid = codes.notna()
        # 값이 거의 상수인 특징은 분위가 만들어지지 않는다 — 조용히 건너뛴다.
        if valid.sum() < MIN_DAYS or codes[valid].nunique() < 2:
            continue
        low = table.loc[valid & (codes == codes[valid].min()), "기대값"]
        high = table.loc[valid & (codes == codes[valid].max()), "기대값"]
        if len(low) < 5 or len(high) < 5:
            continue
        t_stat, p_two = stats.ttest_ind(high, low, equal_var=False)
        records.append({
            "특징": column, "하위분위": float(low.mean()), "상위분위": float(high.mean()),
            "차이": float(high.mean() - low.mean()),
            "상위_양수일비율": float((high > 0).mean()),
            "p": float(p_two), "n_days": int(len(table)),
        })
    return pd.DataFrame(records).sort_values("차이", ascending=False).reset_index(drop=True)
