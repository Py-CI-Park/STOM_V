"""백테 결과 per-trade CSV → 차트용 시계열/분포 (순수·무예외, 추가 백테 0회).

- concurrent_holdings: 매수시간~매도시간 구간 겹침으로 '그 순간 동시 보유 종목수'의 시계열·
  최대·분포를 낸다(자본 효율·집중 위험 가시화).
- time_of_day_profit: 매수시간의 HHMMSS를 시간대 버킷으로 묶어 평균수익률·합수익금·승률을 낸다
  (어느 시간에 진입한 게 돈이 됐나).

대시보드 /concurrent_holdings·/time_profit 엔드포인트가 소비한다. 엔진/하드게이트 무수정·읽기 전용.
잘못된 입력(컬럼 부재·빈 파일·파싱 실패)은 빈 결과로 흡수한다(무예외).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from cli._utils import ensure_dataframe as _ensure_dataframe

_RETURN = "수익률"
_PROFIT = "수익금"
_BUY_TS = "매수시간"
_SELL_TS = "매도시간"
_SERIES_CAP = 3000  # 차트 점 상한(초과 시 균등 다운샘플).


def _load(df_or_path: Any) -> Optional[pd.DataFrame]:
    if isinstance(df_or_path, pd.DataFrame):
        return df_or_path
    if not df_or_path:
        return None
    try:
        return _ensure_dataframe(df_or_path)
    except Exception:  # noqa: BLE001
        return None


def _as_ts(v: Any) -> Optional[int]:
    """YYYYMMDDHHMMSS(문자/실수) → 정수. 14자리 미만/비수치는 None."""
    s = str(v).strip()
    if s.endswith(".0"):
        s = s[:-2]
    if not s.isdigit() or len(s) < 12:
        return None
    return int(s)


def _fmt_ts(ts: int) -> str:
    """정수 YYYYMMDDHHMMSS → 'YY-MM-DD HH:MM' (차트 라벨)."""
    s = f"{ts:014d}"
    return f"{s[2:4]}-{s[4:6]}-{s[6:8]} {s[8:10]}:{s[10:12]}"


def concurrent_holdings(df_or_path: Any) -> Dict[str, Any]:
    """매수~매도 구간 겹침으로 동시 보유 종목수 시계열·최대·분포를 낸다(순수·무예외).

    각 거래의 (매수시간 +1, 매도시간 -1) 이벤트를 시각순 누적해 '그 순간 보유 수'를 만든다.
    매수<매도 동시각이면 매도(-1)를 먼저 적용해 경계에서 과대계상을 막는다.

    Returns:
        {"n_trades", "max_concurrent", "avg_concurrent_at_event",
         "series": [{"t": "YY-MM-DD HH:MM", "n": int}, ...],   # 이벤트별(상한 다운샘플)
         "histogram": [{"n": k, "events": cnt}, ...]}          # 보유수 k였던 구간 진입 횟수
        컬럼 부재/빈 입력 → 모두 0/빈 리스트.
    """
    empty = {"n_trades": 0, "max_concurrent": 0, "avg_concurrent_at_event": 0.0,
             "series": [], "histogram": []}
    df = _load(df_or_path)
    if df is None or len(df) == 0 or _BUY_TS not in df.columns or _SELL_TS not in df.columns:
        return empty
    events: List[tuple] = []
    n_trades = 0
    for b, s in zip(df[_BUY_TS], df[_SELL_TS]):
        bt, st = _as_ts(b), _as_ts(s)
        if bt is None or st is None or st < bt:
            continue
        n_trades += 1
        events.append((bt, 1))    # 진입 +1
        events.append((st, -1))   # 청산 -1
    if not events:
        return empty
    # 동일 시각은 청산(-1) 먼저 → 경계 과대계상 방지(delta 오름차순=-1먼저).
    events.sort(key=lambda e: (e[0], e[1]))
    series: List[Dict[str, Any]] = []
    cur = 0
    max_c = 0
    sum_at_entry = 0
    hist: Dict[int, int] = {}
    for ts, delta in events:
        cur += delta
        if delta == 1:  # 진입 순간의 동시보유 수 기록(분포·평균).
            hist[cur] = hist.get(cur, 0) + 1
            sum_at_entry += cur
            max_c = max(max_c, cur)
        series.append({"t": _fmt_ts(ts), "n": cur})
    # 차트 점 상한 — 초과 시 균등 다운샘플.
    if len(series) > _SERIES_CAP:
        step = len(series) / _SERIES_CAP
        series = [series[int(i * step)] for i in range(_SERIES_CAP)]
    return {
        "n_trades": n_trades,
        "max_concurrent": max_c,
        "avg_concurrent_at_event": round(sum_at_entry / max(n_trades, 1), 3),
        "series": series,
        "histogram": [{"n": k, "events": hist[k]} for k in sorted(hist)],
    }


def time_of_day_profit(df_or_path: Any, bucket_sec: int = 300) -> Dict[str, Any]:
    """매수시간의 HHMMSS를 시간대 버킷으로 묶어 평균수익률·합수익금·승률을 낸다(순수·무예외).

    Args:
        df_or_path: per-trade DataFrame 또는 결과 CSV 경로.
        bucket_sec: 버킷 크기(초). 기본 300=5분.

    Returns:
        {"bucket_sec", "n_trades",
         "buckets": [{"time": "HH:MM", "n", "avg_return", "sum_profit", "win_rate"}, ...]}
        시각 오름차순. 컬럼 부재/빈 입력 → 빈 buckets.
    """
    out = {"bucket_sec": int(bucket_sec), "n_trades": 0, "buckets": []}
    df = _load(df_or_path)
    if df is None or len(df) == 0 or _BUY_TS not in df.columns or _RETURN not in df.columns:
        return out
    bsec = max(int(bucket_sec), 1)
    rets = pd.to_numeric(df[_RETURN], errors="coerce")
    profits = pd.to_numeric(df[_PROFIT], errors="coerce") if _PROFIT in df.columns else None
    agg: Dict[int, Dict[str, float]] = {}
    n_total = 0
    for i, raw in enumerate(df[_BUY_TS]):
        ts = _as_ts(raw)
        r = rets.iloc[i]
        if ts is None or pd.isna(r):
            continue
        s = f"{ts:014d}"
        hh, mm, ss = int(s[8:10]), int(s[10:12]), int(s[12:14])
        sod = hh * 3600 + mm * 60 + ss
        key = (sod // bsec) * bsec
        a = agg.setdefault(key, {"n": 0, "sum_r": 0.0, "win": 0, "sum_p": 0.0})
        a["n"] += 1
        a["sum_r"] += float(r)
        a["win"] += 1 if float(r) > 0 else 0
        if profits is not None and not pd.isna(profits.iloc[i]):
            a["sum_p"] += float(profits.iloc[i])
        n_total += 1
    buckets = []
    for key in sorted(agg):
        a = agg[key]
        hh, mm = key // 3600, (key % 3600) // 60
        buckets.append({
            "time": f"{hh:02d}:{mm:02d}",
            "n": int(a["n"]),
            "avg_return": round(a["sum_r"] / a["n"], 4) if a["n"] else 0.0,
            "sum_profit": round(a["sum_p"], 0),
            "win_rate": round(a["win"] / a["n"], 4) if a["n"] else 0.0,
        })
    out["n_trades"] = n_total
    out["buckets"] = buckets
    return out
