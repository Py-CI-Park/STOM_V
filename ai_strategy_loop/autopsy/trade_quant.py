"""per-trade 결과 테이블 심층 퀀트 분석 (G003).

`ai_strategy_loop/autopsy/analyze.py`(entry/exit 부검)와 별개로, 백테스트
per-trade CSV 하나에서 확장 퀀트 지표(기대값/PF/승률/페이오프, 수익률 분포,
연속승패, 보유시간×수익 관계, 시간대별 성과, MFE/MAE 효율, 낙폭 기여,
진입 피처 승패 분리 요약)를 뽑아 프롬프트 환류용 자연어 라인까지 만든다.

공개 API는 `analyze_trade_table` 하나뿐이며 **무예외 계약**을 따른다 — 파일이
없거나, CSV가 비었거나, 필수 컬럼이 없어도 raise 하지 않고 `status`로 보고한다.

실제 per-trade CSV 컬럼명(backtest/back_static.py, fitness/score.py,
fitness/edge_ratio.py, autopsy/analyze.py 확인)은 한글이며 다음과 같다:
    수익률, 수익금, 수익금합계, 매수시간, 매도시간, 보유시간, 종목명/종목코드,
    R_매수후최고수익률(R_MFE 폴백), R_매수후최저수익률(R_MAE 폴백),
    B_현재가 등 14개 B_* 진입 피처.
컬럼명은 스키마마다 약간씩 다를 수 있어(관용 별칭) `_ColumnResolver`로 흡수한다.
"""

from __future__ import annotations

import math
import os
from typing import Any, Dict, List, Mapping, Optional, Sequence


import pandas as pd

STATUS_OK = "ok"
STATUS_NO_DATA = "no_data"
STATUS_ERROR = "error"

# 컬럼 별칭(관용 이름) — 실제 STOM per-trade CSV(backtest/back_static.py) 기준 +
#   구/대안 스키마에서 보이는 이름들을 폴백으로 허용한다.
_RETURN_ALIASES = ["수익률", "수익률(%)"]
_PROFIT_AMOUNT_ALIASES = ["수익금"]
_CUM_PROFIT_ALIASES = ["수익금합계"]
_BUY_TIME_ALIASES = ["매수시간", "체결시간"]
_SELL_TIME_ALIASES = ["매도시간"]
_HOLD_TIME_ALIASES = ["보유시간"]
_MFE_ALIASES = ["R_매수후최고수익률", "R_MFE"]
_MAE_ALIASES = ["R_매수후최저수익률", "R_MAE"]
_TRADE_ID_ALIASES = ["종목명", "종목코드"]

_B_PREFIX = "B_"


def _resolve(df: pd.DataFrame, aliases: Sequence[str]) -> Optional[str]:
    """df.columns에서 aliases 중 처음 매치되는 실제 컬럼명을 돌려준다(없으면 None)."""
    for name in aliases:
        if name in df.columns:
            return name
    return None


def _numeric(df: pd.DataFrame, col: Optional[str]) -> Optional[pd.Series]:
    """col이 없으면 None, 있으면 숫자로 강제한 Series(NaN 포함)를 돌려준다."""
    if col is None:
        return None
    return pd.to_numeric(df[col], errors="coerce")


def _parse_hhmm(raw: Any) -> Optional[str]:
    """매수시간류 값에서 'HHMM' 4자리를 뽑는다. 실패하면 None.

    지원 형태: YYYYMMDDHHMM(12자리), YYYYMMDDHHMMSS(14자리), HHMMSS(6자리 —
    int 파싱으로 선행 0이 소실된 5자리도 zfill 복원), HHMM(4자리).
    그 외 자릿수(13자리 epoch ms 등)는 오버매치 방지를 위해 None.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if s == "" or s.lower() == "nan":
        return None
    digits = "".join(ch for ch in s if ch.isdigit())
    if len(digits) in (12, 14):
        return digits[8:12]
    if len(digits) == 5:
        # HHMMSS가 int로 읽혀 선행 0이 소실된 형태(예: 090512 → 90512).
        digits = digits.zfill(6)
    if len(digits) == 6:
        return digits[0:4]
    if len(digits) == 4:
        return digits
    return None


def _bucket_label(hhmm: str, bucket_minutes: int) -> Optional[str]:
    """'HHMM' 문자열을 bucket_minutes 단위로 내림한 'HHMM' 라벨로 변환한다."""
    try:
        hh = int(hhmm[0:2])
        mm = int(hhmm[2:4])
    except (ValueError, IndexError):
        return None
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        return None
    total = hh * 60 + mm
    bucket_start = (total // bucket_minutes) * bucket_minutes
    return f"{bucket_start // 60:02d}{bucket_start % 60:02d}"


def _safe_round(x: Optional[float], nd: int = 6) -> Optional[float]:
    if x is None:
        return None
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(xf) or math.isinf(xf):
        return None
    return round(xf, nd)


def _expectancy_pf_winrate_payoff(returns: pd.Series) -> Dict[str, Any]:
    """기대값(%)/profit_factor/win_rate/payoff_ratio(수익률 기준). 계산불가는 None+사유."""
    n = int(len(returns))
    out: Dict[str, Any] = {}
    out["expectancy_pct"] = _safe_round(float(returns.mean())) if n else None
    if n == 0:
        out["expectancy_pct_reason"] = "거래 0건"

    wins = returns[returns > 0]
    # 무손익(수익률==0) 거래는 승/패 어느 쪽도 아니다 — payoff_ratio 분모/분자에서 제외.
    losses = returns[returns < 0]
    out["win_rate"] = _safe_round(float(len(wins)) / n) if n else None

    gross_profit = float(wins.sum())
    gross_loss = float(-losses.sum())  # 양수화.
    # 의도적 분기: fitness/score.py(load_exit_quality...)는 스코어 수식용이라
    #   분모 0을 999.0 cap으로 처리하지만, 이 모듈은 서술/프롬프트 환류용이라
    #   정직한 결측(None+사유)이 옳다 — 두 관례를 '정합화'하지 말 것.
    if gross_loss > 0:
        out["profit_factor"] = _safe_round(gross_profit / gross_loss)
    else:
        out["profit_factor"] = None
        out["profit_factor_reason"] = (
            "손실 거래 없음(총손실=0) — profit_factor 계산 불가"
        )

    if len(wins) > 0 and len(losses) > 0:
        mean_win = float(wins.mean())
        mean_loss = float(losses.mean())
        denom = abs(mean_loss)
        out["payoff_ratio"] = _safe_round(mean_win / denom) if denom > 0 else None
        if denom == 0:
            out["payoff_ratio_reason"] = "평균손실=0 — payoff_ratio 계산 불가"
    else:
        out["payoff_ratio"] = None
        reason_bits = []
        if len(wins) == 0:
            reason_bits.append("승리거래 없음")
        if len(losses) == 0:
            reason_bits.append("손실거래 없음")
        out["payoff_ratio_reason"] = " · ".join(reason_bits) + " — payoff_ratio 계산 불가"
    return out


def _distribution(returns: pd.Series) -> Dict[str, Optional[float]]:
    """수익률 분포 통계(pandas 기본만 사용, scipy 불요)."""
    n = int(len(returns))
    if n == 0:
        keys = ["mean", "std", "skew", "kurtosis", "q05", "q25", "q50", "q75", "q95"]
        return {k: None for k in keys}
    dist = {
        "mean": _safe_round(float(returns.mean())),
        "std": _safe_round(float(returns.std())) if n > 1 else None,
        "skew": _safe_round(float(returns.skew())) if n > 2 else None,
        "kurtosis": _safe_round(float(returns.kurt())) if n > 3 else None,
        "q05": _safe_round(float(returns.quantile(0.05))),
        "q25": _safe_round(float(returns.quantile(0.25))),
        "q50": _safe_round(float(returns.quantile(0.50))),
        "q75": _safe_round(float(returns.quantile(0.75))),
        "q95": _safe_round(float(returns.quantile(0.95))),
    }
    return dist


def _streaks(is_win: pd.Series, top_k: int = 3) -> Dict[str, Any]:
    """거래 순서(입력 순서)의 연속승/연속패 streak. 최대값 + 상위 top_k(길이순)."""
    runs: List[Dict[str, Any]] = []
    cur_type: Optional[bool] = None
    cur_len = 0
    cur_start = 0
    values = list(is_win)
    for i, v in enumerate(values):
        if cur_type is None or v != cur_type:
            if cur_type is not None:
                runs.append(
                    {
                        "type": "win" if cur_type else "loss",
                        "length": cur_len,
                        "start_index": cur_start,
                        "end_index": i - 1,
                    }
                )
            cur_type = v
            cur_len = 1
            cur_start = i
        else:
            cur_len += 1
    if cur_type is not None:
        runs.append(
            {
                "type": "win" if cur_type else "loss",
                "length": cur_len,
                "start_index": cur_start,
                "end_index": len(values) - 1,
            }
        )

    win_lens = [r["length"] for r in runs if r["type"] == "win"]
    loss_lens = [r["length"] for r in runs if r["type"] == "loss"]
    top_streaks = sorted(runs, key=lambda r: r["length"], reverse=True)[:top_k]
    return {
        "max_win_streak": max(win_lens) if win_lens else 0,
        "max_loss_streak": max(loss_lens) if loss_lens else 0,
        "top_streaks": top_streaks,
    }


def _hold_time_analysis(hold: Optional[pd.Series], returns: pd.Series) -> Optional[Dict[str, Any]]:
    """보유시간×수익 pearson 상관 + 보유시간 4분위별 평균수익."""
    if hold is None:
        return None
    mask = hold.notna() & returns.notna()
    h = hold[mask]
    r = returns[mask]
    if len(h) < 2:
        return {"pearson_corr": None, "reason": "유효 보유시간 표본 < 2", "quartile_returns": None}

    corr = h.corr(r)
    corr_val = _safe_round(float(corr)) if corr is not None and not pd.isna(corr) else None

    if len(h) < 4 or h.nunique() < 2:
        quartiles = None
        q_reason = "보유시간 표본/고유값 부족 — 4분위 산출 불가"
    else:
        try:
            bins = pd.qcut(h, 4, labels=False, duplicates="drop")
        except ValueError:
            bins = None
        if bins is None or pd.Series(bins).nunique() < 2:
            quartiles = None
            q_reason = "보유시간 분포가 단조로워 4분위 분리 불가"
        else:
            quartiles = []
            q_reason = None
            for qi in sorted(pd.unique(bins)):
                if qi is None or (isinstance(qi, float) and math.isnan(qi)):
                    continue
                sel = bins == qi
                quartiles.append(
                    {
                        "quartile": int(qi) + 1,
                        "count": int(sel.sum()),
                        "mean_hold": _safe_round(float(h[sel].mean())),
                        "mean_return": _safe_round(float(r[sel].mean())),
                    }
                )

    out: Dict[str, Any] = {"pearson_corr": corr_val, "quartile_returns": quartiles}
    if quartiles is None:
        out["reason"] = q_reason
    return out


def _time_of_day_analysis(
    buy_raw: Optional[pd.Series],
    returns: pd.Series,
    pnl: pd.Series,
    fine_time: bool,
    pnl_unit: str = "pct",
) -> Optional[Dict[str, Any]]:
    """매수시각 HHMM 버킷(fine_time: 5분, else 30분)별 {count, win_rate, total_pnl}."""
    if buy_raw is None:
        return None
    bucket_minutes = 5 if fine_time else 30
    buckets: Dict[str, Dict[str, Any]] = {}
    for raw, ret, p in zip(buy_raw, returns, pnl):
        hhmm = _parse_hhmm(raw)
        if hhmm is None or pd.isna(ret):
            continue
        label = _bucket_label(hhmm, bucket_minutes)
        if label is None:
            continue
        b = buckets.setdefault(label, {"count": 0, "win_count": 0, "total_pnl": 0.0})
        b["count"] += 1
        if ret > 0:
            b["win_count"] += 1
        if p is not None and not pd.isna(p):
            b["total_pnl"] += float(p)

    if not buckets:
        return {
            "bucket_minutes": bucket_minutes, "pnl_unit": pnl_unit,
            "buckets": {}, "reason": "매수시각 파싱 가능한 행 없음",
        }

    out_buckets: Dict[str, Any] = {}
    for label, b in sorted(buckets.items()):
        out_buckets[label] = {
            "count": b["count"],
            "win_rate": _safe_round(b["win_count"] / b["count"]) if b["count"] else None,
            "total_pnl": _safe_round(b["total_pnl"]),
        }
    return {"bucket_minutes": bucket_minutes, "pnl_unit": pnl_unit, "buckets": out_buckets}


def _mfe_mae_analysis(
    mfe: Optional[pd.Series], mae: Optional[pd.Series], returns: pd.Series
) -> Optional[Dict[str, Any]]:
    """MFE/MAE 효율: realized/mfe 캡처율(승리거래), 손실거래 MAE vs 승리거래 MAE 비율."""
    if mfe is None and mae is None:
        return None

    out: Dict[str, Any] = {}

    if mfe is not None:
        mask = mfe.notna() & returns.notna() & (returns > 0) & (mfe > 0)
        if mask.sum() > 0:
            eff = (returns[mask] / mfe[mask]).mean()
            out["realized_over_mfe_efficiency"] = _safe_round(float(eff))
        else:
            out["realized_over_mfe_efficiency"] = None
            out["realized_over_mfe_efficiency_reason"] = "MFE>0 인 승리거래 없음"
    else:
        out["realized_over_mfe_efficiency"] = None
        out["realized_over_mfe_efficiency_reason"] = "MFE 컬럼 없음"

    if mae is not None:
        win_mask = returns.notna() & mae.notna() & (returns > 0)
        loss_mask = returns.notna() & mae.notna() & (returns <= 0)
        win_mae = mae[win_mask].abs()
        loss_mae = mae[loss_mask].abs()
        if len(win_mae) > 0 and len(loss_mae) > 0 and float(win_mae.mean()) > 0:
            out["loss_vs_win_mae_ratio"] = _safe_round(float(loss_mae.mean()) / float(win_mae.mean()))
        else:
            out["loss_vs_win_mae_ratio"] = None
            out["loss_vs_win_mae_ratio_reason"] = "승/손 MAE 표본 부족 또는 승리MAE=0"
    else:
        out["loss_vs_win_mae_ratio"] = None
        out["loss_vs_win_mae_ratio_reason"] = "MAE 컬럼 없음"

    return out


def _drawdown_contributors(
    pnl: pd.Series, trade_ids: Optional[pd.Series], top_n: int
) -> Optional[Dict[str, Any]]:
    """누적손익 경로에서 최대 낙폭 구간의 개별 거래 기여 top_n."""
    valid_mask = pnl.notna()
    p = pnl[valid_mask].reset_index(drop=True)
    ids = trade_ids[valid_mask].reset_index(drop=True) if trade_ids is not None else None
    n = len(p)
    if n == 0:
        return None

    equity = p.cumsum()
    # 낙폭의 기준(peak)은 0에서 시작한다(자금 곡선의 시작점) — 첫 거래가 곧바로
    #   손실이어도 그 손실 전체가 낙폭으로 잡혀야 한다(peak를 첫 누적값으로 잡으면
    #   단일 손실 거래의 낙폭이 0으로 사라지는 버그였다).
    running_peak = equity.cummax().clip(lower=0.0)
    drawdown = equity - running_peak

    trough_idx = int(drawdown.idxmin())
    max_dd = float(drawdown.iloc[trough_idx])
    if max_dd >= 0:
        return {
            "total_decline": 0.0,
            "top": [],
            "reason": "낙폭 없음(누적손익이 단조 비감소)",
        }

    peak_value = float(running_peak.iloc[trough_idx])
    # peak_idx = -1 은 '시리즈 시작 이전의 가상 0 지점'(zero-origin peak)을 뜻한다 —
    #   낙폭 구간이 첫 거래부터 시작하는 경우(peak_value==0 이 시리즈 내에 없음)를 표현.
    peak_idx = -1
    for i in range(trough_idx, -1, -1):
        if math.isclose(float(equity.iloc[i]), peak_value, rel_tol=1e-9, abs_tol=1e-9):
            peak_idx = i
            break

    window = range(peak_idx + 1, trough_idx + 1)
    total_decline = abs(float(equity.iloc[trough_idx]) - peak_value)

    # 기여자 = 최대낙폭 구간 내 **손실 거래만**(아키텍트 리뷰 MEDIUM 반영).
    #   share 분모는 구간 내 총손실(gross loss) — 구간 내 이익 거래가 상쇄해도
    #   share 합이 100%를 넘지 않게 의미를 고정한다.
    loss_contributors = []
    for i in window:
        pnl_i = float(p.iloc[i])
        if pnl_i >= 0:
            continue
        loss_contributors.append(
            {
                "index": i,
                "id": (str(ids.iloc[i]) if ids is not None else None),
                "pnl": _safe_round(pnl_i),
            }
        )
    loss_contributors.sort(key=lambda c: c["pnl"] if c["pnl"] is not None else 0.0)
    window_gross_loss = -sum(c["pnl"] for c in loss_contributors if c["pnl"] is not None)

    top = []
    for c in loss_contributors[:max(0, top_n)]:
        share = (
            (-c["pnl"] / window_gross_loss)
            if window_gross_loss > 0 and c["pnl"] is not None
            else None
        )
        top.append(
            {
                "index": c["index"],
                "id": c["id"],
                "pnl": c["pnl"],
                "share_of_decline": _safe_round(share) if share is not None else None,
            }
        )

    return {
        "total_decline": _safe_round(total_decline),
        "window_gross_loss": _safe_round(window_gross_loss),
        "peak_index": peak_idx,
        "trough_index": trough_idx,
        "top": top,
    }


def _entry_feature_split(df: pd.DataFrame, is_win: pd.Series, top_k: int = 3) -> Optional[Dict[str, Any]]:
    """B_* 진입 피처 중 승/패 평균 차이(정규화) 큰 상위 top_k 요약(부검 discriminator와 중복 없이 간략만)."""
    b_cols = [c for c in df.columns if c.startswith(_B_PREFIX)]
    if not b_cols:
        return None

    rows = []
    for c in b_cols:
        vals = pd.to_numeric(df[c], errors="coerce")
        win_vals = vals[is_win].dropna()
        loss_vals = vals[~is_win].dropna()
        if len(win_vals) < 2 or len(loss_vals) < 2:
            continue
        mean_win = float(win_vals.mean())
        mean_loss = float(loss_vals.mean())
        pooled_std = math.sqrt(
            (float(win_vals.std(ddof=1) or 0.0) ** 2 + float(loss_vals.std(ddof=1) or 0.0) ** 2) / 2.0
        )
        diff_norm = (mean_win - mean_loss) / pooled_std if pooled_std > 0 else 0.0
        rows.append(
            {
                "column": c,
                "win_mean": _safe_round(mean_win),
                "loss_mean": _safe_round(mean_loss),
                "diff_norm": _safe_round(diff_norm),
            }
        )

    if not rows:
        return {"top": [], "reason": "B_* 컬럼은 있으나 승/패 표본 부족"}

    rows.sort(key=lambda r: abs(r["diff_norm"]) if r["diff_norm"] is not None else 0.0, reverse=True)
    return {"top": rows[:top_k]}


def _build_nl_lines(metrics: Dict[str, Any], trade_count: int, top_n: int) -> List[str]:
    lines: List[str] = []

    exp = metrics.get("expectancy_pct")
    pf = metrics.get("profit_factor")
    if exp is not None:
        pf_txt = f"{pf:.2f}" if pf is not None else "N/A"
        lines.append(f"기대값 {exp:+.2f}%/거래, PF {pf_txt} (거래 {trade_count}건).")

    win_rate = metrics.get("win_rate")
    payoff = metrics.get("payoff_ratio")
    if win_rate is not None:
        payoff_txt = f"{payoff:.2f}" if payoff is not None else "N/A"
        lines.append(f"승률 {win_rate:.1%}, 페이오프비율 {payoff_txt}.")

    streaks = metrics.get("streaks") or {}
    if streaks:
        lines.append(
            f"최대 연속승 {streaks.get('max_win_streak', 0)}회, "
            f"최대 연속패 {streaks.get('max_loss_streak', 0)}회."
        )

    hold = metrics.get("hold_time")
    if hold and hold.get("pearson_corr") is not None:
        corr = hold["pearson_corr"]
        qr = hold.get("quartile_returns")
        extra = ""
        if qr:
            worst = min(qr, key=lambda q: q["mean_return"] if q["mean_return"] is not None else 0.0)
            extra = f" 보유 {worst['quartile']}분위(평균 {worst['mean_hold']:.0f})가 수익률 최저({worst['mean_return']:+.2f}%)."
        lines.append(f"보유시간-수익 상관 {corr:+.2f}.{extra}")

    tod = metrics.get("time_of_day")
    if tod and tod.get("buckets"):
        best_label, best = max(tod["buckets"].items(), key=lambda kv: kv[1]["total_pnl"] if kv[1]["total_pnl"] is not None else 0.0)
        unit_txt = "원" if tod.get("pnl_unit") == "amount" else "%p합(비가산 근사)"
        lines.append(
            f"시간대 {best_label} 버킷이 누적손익 최고({best['total_pnl']}{unit_txt}, 승률 {best['win_rate']:.1%})."
        )

    mm = metrics.get("mfe_mae")
    if mm:
        eff = mm.get("realized_over_mfe_efficiency")
        ratio = mm.get("loss_vs_win_mae_ratio")
        if eff is not None or ratio is not None:
            eff_txt = f"{eff:.0%}" if eff is not None else "N/A"
            ratio_txt = f"{ratio:.2f}배" if ratio is not None else "N/A"
            lines.append(f"MFE 대비 실현효율 {eff_txt}, 손실거래 MAE가 승리거래 MAE의 {ratio_txt}.")

    dd = metrics.get("drawdown_contributors")
    if dd and dd.get("total_decline"):
        top = dd.get("top") or []
        share_sum = sum(t["share_of_decline"] for t in top if t.get("share_of_decline") is not None)
        if top:
            lines.append(
                f"최대낙폭 구간({dd['total_decline']}) 손실의 {share_sum:.0%}가 "
                f"구간 내 손실 상위 {len(top)}거래에서 발생."
            )

    ef = metrics.get("entry_feature_split")
    if ef and ef.get("top"):
        best = ef["top"][0]
        lines.append(f"진입 피처 중 {best['column']}가 승패 평균차 최대(정규화 {best['diff_norm']:+.2f}).")

    # 최대 8줄(가용 지표에 비례) — 희소 스키마면 더 적을 수 있다.
    return lines[:8] if lines else []


def analyze_trade_table(csv_path: str, *, fine_time: bool = False, top_n: int = 5) -> Dict[str, Any]:
    """백테스트 per-trade 결과 CSV에서 확장 퀀트 지표를 뽑는다(순수·무예외).

    Args:
        csv_path: per-trade 결과 CSV 경로(utf-8-sig, 거래당 1행).
        fine_time: True면 시간대 버킷을 5분 단위, False면 30분 단위로 잡는다.
        top_n: 낙폭 기여 상위 N 거래 수.

    Returns:
        dict: {"status": "ok"|"no_data"|"error", "trade_count": int,
               "metrics": dict, "nl_lines": [str, ...], "error": str|None}
        어떤 입력(없는 파일/빈 CSV/컬럼 누락)에도 raise 하지 않는다.
    """
    empty = {"status": STATUS_NO_DATA, "trade_count": 0, "metrics": {}, "nl_lines": [], "error": None}

    if not isinstance(csv_path, str) or not csv_path:
        return {**empty, "status": STATUS_ERROR, "error": "csv_path가 비어 있음"}

    if not os.path.exists(csv_path):
        return {**empty, "status": STATUS_ERROR, "error": f"파일이 존재하지 않음: {csv_path}"}

    try:
        try:
            df = pd.read_csv(csv_path, encoding="utf-8-sig")
        except pd.errors.EmptyDataError:
            return {**empty, "note": "CSV가 비어 있음(헤더 없음)"}

        if df is None or len(df) == 0:
            return {**empty, "note": "거래 0건"}

        return_col = _resolve(df, _RETURN_ALIASES)
        if return_col is None:
            return {
                **empty,
                "trade_count": int(len(df)),
                "status": STATUS_ERROR,
                "error": f"필수 컬럼(수익률) 없음 — 확인한 별칭: {_RETURN_ALIASES}",
            }

        returns_all = pd.to_numeric(df[return_col], errors="coerce")
        valid_mask = returns_all.notna()
        df = df.loc[valid_mask].reset_index(drop=True)
        returns = returns_all.loc[valid_mask].reset_index(drop=True)
        trade_count = int(len(df))

        if trade_count == 0:
            return {**empty, "note": "유효한 수익률 값을 가진 거래 0건"}

        profit_col = _resolve(df, _PROFIT_AMOUNT_ALIASES)
        cum_col = _resolve(df, _CUM_PROFIT_ALIASES)
        buy_col = _resolve(df, _BUY_TIME_ALIASES)
        sell_col = _resolve(df, _SELL_TIME_ALIASES)
        hold_col = _resolve(df, _HOLD_TIME_ALIASES)
        mfe_col = _resolve(df, _MFE_ALIASES)
        mae_col = _resolve(df, _MAE_ALIASES)
        id_col = _resolve(df, _TRADE_ID_ALIASES)

        # streak/낙폭처럼 경로(순서)에 의존하는 지표는 입력 행 순서가 아니라
        #   매수/매도 시간 기준의 정본 순서를 써야 한다 — 같은 거래 집합을 시간순이
        #   아닌 다른 행 순서로 넣어도 결과(연속승패 길이, MDD)가 바뀌면 안 된다.
        #   (거래id/종목명은 시간 순서를 보장하지 않으므로 정렬 키로 쓰지 않는다.)
        sort_col = buy_col or sell_col
        if sort_col is not None:
            order = df[sort_col].astype(str).sort_values(kind="stable").index
            df = df.loc[order].reset_index(drop=True)
            returns = returns.loc[order].reset_index(drop=True)

        is_win = returns > 0

        profit_amount = _numeric(df, profit_col)
        hold_time = _numeric(df, hold_col)
        mfe = _numeric(df, mfe_col)
        mae = _numeric(df, mae_col)
        trade_ids = df[id_col] if id_col is not None else None

        metrics: Dict[str, Any] = {}
        metrics.update(_expectancy_pf_winrate_payoff(returns))

        if profit_amount is not None and profit_amount.notna().sum() > 0:
            metrics["expectancy_amount"] = _safe_round(float(profit_amount.dropna().mean()))
        else:
            metrics["expectancy_amount"] = None
            metrics["expectancy_amount_reason"] = "수익금 컬럼 없음/전부 결측"

        metrics["distribution"] = _distribution(returns)
        metrics["streaks"] = _streaks(is_win)
        metrics["hold_time"] = _hold_time_analysis(hold_time, returns)
        metrics["time_of_day"] = _time_of_day_analysis(
            df[buy_col] if buy_col is not None else None,
            returns,
            profit_amount if profit_amount is not None else returns,
            fine_time,
            pnl_unit=("amount" if profit_amount is not None else "pct"),
        )
        metrics["mfe_mae"] = _mfe_mae_analysis(mfe, mae, returns)

        # 낙폭 기여는 거래단위 pnl 경로가 필요 — 수익금 있으면 금액, 없으면 수익률(%)을 사용.
        if profit_amount is not None and profit_amount.notna().sum() == trade_count:
            dd_pnl = profit_amount
            dd_unit = "amount"
        else:
            dd_pnl = returns
            dd_unit = "pct"
        dd = _drawdown_contributors(dd_pnl, trade_ids, top_n)
        if dd is not None:
            dd["unit"] = dd_unit
        metrics["drawdown_contributors"] = dd

        metrics["entry_feature_split"] = _entry_feature_split(df, is_win)

        # cum_col(수익금합계)이 존재하면 참고 메타로만 노출(별도 재계산 없이 마지막 값).
        if cum_col is not None:
            cum_series = _numeric(df, cum_col)
            if cum_series is not None and cum_series.notna().sum() > 0:
                metrics["final_cum_profit_reported"] = _safe_round(float(cum_series.dropna().iloc[-1]))

        nl_lines = _build_nl_lines(metrics, trade_count, top_n)

        return {
            "status": STATUS_OK,
            "trade_count": trade_count,
            "metrics": metrics,
            "nl_lines": nl_lines,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001 — 무예외 계약: 어떤 예외도 status로 흡수.
        return {**empty, "status": STATUS_ERROR, "error": f"{type(exc).__name__}: {exc}"}


# ---------------------------------------------------------------------------
# AnalysisCardV3 정본 섹션 (DR-05) — 표본/결측/집중도/tail/downside/CVaR/
#   capacity·participation/비용 스트레스를 하나의 typed dict 섹션으로 묶는다.
#   기존 analyze_trade_table 은 전혀 건드리지 않는다(가법 전용, 별도 공개 API).
# ---------------------------------------------------------------------------

TRADE_QUANT_SECTION_SCHEMA_V3 = "trade_quant_section_v3"

# CVaR/tail 근사에 쓰는 하위 분위(worst 5%) — advisory 정밀도면 충분.
_CVAR_TAIL_FRACTION = 0.05
_TAIL_TOP_N = (1, 5, 10)


def build_trade_quant_section(
    rows: Sequence[Mapping[str, Any]], contract: Optional[Any] = None,
) -> Dict[str, Any]:
    """거래행(dict 시퀀스)에서 AnalysisCardV3 정본 섹션을 만든다(순수·무예외).

    Args:
        rows: 거래행 dict 시퀀스(백테스트 per-trade CSV를 dict로 읽은 것).
        contract: `ai_strategy_loop.fitness.edge_ratio.TradeColumnContract`
            (None이면 기본 계약). 순환 import 회피를 위해 함수 내부에서 지연 import.

    Returns:
        dict(schema=TRADE_QUANT_SECTION_SCHEMA_V3, n_trades/n_days/n_symbols,
        missing_count, excluded_duplicate_count, concentration, tail,
        downside, capacity, cost_stress). status(SECTION_OK/insufficient)
        메타 없이도 안전한 기본값(0/None)만 돌려준다 — 무예외 계약.
    """
    from ai_strategy_loop.fitness import edge_ratio as _edge_ratio  # noqa: PLC0415
    from ai_strategy_loop.fitness import promotion_diagnostics as _promo  # noqa: PLC0415

    active_contract = contract or _edge_ratio.DEFAULT_TRADE_COLUMN_CONTRACT
    resolved = [_edge_ratio.resolve_trade_columns(row, active_contract) for row in rows]
    n_trades = len(resolved)

    dates = {r.date_key for r in resolved if r.date_key}
    symbols = {r.symbol_key for r in resolved if r.symbol_key}
    missing_count = sum(1 for r in resolved if r.return_value is None)

    seen_keys = set()
    excluded_duplicate_count = 0
    for row in rows:
        key = _edge_ratio.canonical_trade_key(row, active_contract)
        if key in seen_keys:
            excluded_duplicate_count += 1
        else:
            seen_keys.add(key)

    profits = [r.profit_value for r in resolved if r.profit_value is not None]
    returns = [r.return_value for r in resolved if r.return_value is not None]

    concentration = None
    if profits and sum(abs(p) for p in profits) > 0:
        total_abs = sum(abs(p) for p in profits)
        concentration = round(max(abs(p) for p in profits) / total_abs, 6)

    tail: Dict[str, Any] = {}
    if profits:
        total_profit = sum(profits)
        ordered = sorted(profits, reverse=True)
        for top_n in _TAIL_TOP_N:
            removed = sum(ordered[:top_n])
            tail[f"top{top_n}_removed_total"] = round(total_profit - removed, 6)
    else:
        for top_n in _TAIL_TOP_N:
            tail[f"top{top_n}_removed_total"] = None

    downside: Dict[str, Any] = {"downside_deviation": None, "cvar_95": None}
    if returns:
        negatives = [r for r in returns if r < 0]
        if negatives:
            mean_neg = sum(negatives) / len(negatives)
            variance = sum((r - mean_neg) ** 2 for r in negatives) / len(negatives)
            downside["downside_deviation"] = round(variance ** 0.5, 6)
        ordered_returns = sorted(returns)
        tail_n = max(1, int(round(len(ordered_returns) * _CVAR_TAIL_FRACTION)))
        worst = ordered_returns[:tail_n]
        downside["cvar_95"] = round(sum(worst) / len(worst), 6) if worst else None

    n_days = len(dates)
    capacity = {
        "trades_per_day": round(n_trades / n_days, 6) if n_days else None,
        "note": "participation/capacity 는 실제 유동성 데이터가 없어 거래빈도 proxy 만 제공한다.",
    }

    cost_stress: Dict[str, Any] = {"status": "insufficient_data", "rows": ()}
    if profits:
        total_profit = sum(profits)
        summary = _promo.OosTradeSummary(
            name="trade_quant_section_v3", final_profit=float(total_profit), trade_count=n_trades,
        )
        stress = _promo.compute_slippage_stress(summary)
        cost_stress = {
            "status": stress.status,
            "promotion_passed": stress.promotion_passed,
            "rows": tuple({"haircut": row.haircut, "stressed_profit": row.stressed_profit} for row in stress.rows),
        }

    return {
        "schema": TRADE_QUANT_SECTION_SCHEMA_V3,
        "n_trades": n_trades,
        "n_days": n_days,
        "n_symbols": len(symbols),
        "missing_count": missing_count,
        "excluded_duplicate_count": excluded_duplicate_count,
        "concentration": concentration,
        "tail": tail,
        "downside": downside,
        "capacity": capacity,
        "cost_stress": cost_stress,
    }
