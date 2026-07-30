"""라벨 데이터셋 빌더 (QSP1 P1) — 거래 CSV → 수익률(라벨) + 설명변수 행렬.

사용자 방법론(2026-07-29): "백테스트 결과를 매수시점 변수로 잘 생성해 내고, 조건식으로
만들 수 있는 매수 시점 파생 변수도 만들어서 … 수익률이 라벨링된 결과를 시간대·시총대로
상세 분석"의 데이터 계층이다.

세 가지 책임(순수 함수·무예외 지향):
  1) enrich()       : 원시 B_* 스냅샷에서 **조건식으로 재현 가능한** 파생변수를 만든다.
                      파생 수식은 조건식 문법과 1:1 이라 분석 결과가 곧 조건식 수정안이 된다.
  2) leaf coords    : QSP 계층 좌표(시간밴드 × 시총단계)를 라벨링한다 — 잔차표의 축.
  3) leaf_matrix()  : 리프별 잔차 요약. min CSS 복권형 분포(승률 12%·payoff 1.77)가
                      평균을 왜곡하던 R0 발견에 따라 **중앙값·승률을 평균과 병기**한다.
  4) feature 자동 편입: 컬럼을 하드코딩하지 않고 CSV 헤더의 B_*/D_* 수치 컬럼을 전부
                      설명변수로 취급한다(엔진 v2 확장 컬럼·미래 컬럼 자동 반영).
                      zero-variance(예: min CSV 의 B_초당* = 전부 0) 컬럼은 자동 제외.

파생 규칙(전부 SSOT 어휘로 재현 가능 — 근거를 각 항목에 명시):
  D_전일종가        = B_현재가/(1+B_등락율/100)            ← 조건식 관례(전 시드 공통)
  D_총호가매수비율   = B_매수총잔량/(B_매수총잔량+B_매도총잔량)
  D_잔량비          = B_매도총잔량/B_매수총잔량
  D_거래대금시총비   = B_당일거래대금/B_시가총액
  D_분봉위치율      = (B_현재가-B_분봉저가)/(B_분봉고가-B_분봉저가)
  -- 아래는 엔진 v2 확장 컬럼(B_시가/고가/저가/체결강도평균/초당·분당 계열)이 있을 때만 --
  D_시가등락율      = (B_시가-D_전일종가)/D_전일종가*100
  D_시가대비등락율   = (B_현재가-B_시가)/B_시가*100
  D_현재가위치      = (B_현재가-B_저가)/(B_고가-B_저가)*100
  D_고가근접율      = (B_현재가-(B_고가-(B_고가-B_저가)*0.3)) 부호
  D_체결강도비율     = B_체결강도/B_체결강도평균
  D_거래대금폭발배수 = B_초당거래대금/B_초당거래대금평균 (min 은 분당)
  D_누적수급비      = B_누적초당매수수량/B_누적초당매도수량 (tick)
  D_수급비          = B_분당매수수량/B_분당매도수량 (min)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd

# ---------------------------------------------------------------------------
# QSP 리프 좌표 정의 — 시드 골격(hierarchy_preservation.md)과 동일해야 한다.
# ---------------------------------------------------------------------------
TICK_TIME_BANDS: Sequence[Tuple[int, str]] = (
    (90200, "B1_900_902"), (90500, "B2_902_905"), (91000, "B3_905_910"),
    (92000, "B4_910_920"), (93000, "B5_920_930"),
)
MIN_TIME_BANDS: Sequence[Tuple[int, str]] = (
    (93000, "B1_장초반"), (103000, "B2_오전"), (130000, "B3_한산"), (150000, "B4_오후"),
    (152000, "B5_마감"),
)
CAP_BANDS: Sequence[Tuple[float, str]] = (
    (3000, "S_3000미만"), (5000, "M1_3000_5000"), (10000, "M2_5000_10000"),
    (float("inf"), "L_10000이상"),
)

# 리프 통계 신뢰 최소 표본(R0 리뷰 반영 — 5는 과소, t검정 관례 하한 사용).
DEFAULT_LEAF_MIN_N = 30


def _hms_from_buy_time(value: Any) -> Optional[int]:
    """매수시간(YYYYMMDDHHMMSS=tick(14) | YYYYMMDDHHMM=min(12)) → HHMMSS."""
    text = str(value or "").strip()
    if len(text) == 14 and text.isdigit():
        return int(text[8:14])
    if len(text) == 12 and text.isdigit():
        return int(text[8:12] + "00")
    return None


def detect_timeframe(df: pd.DataFrame) -> str:
    """매수시간 자릿수로 tick/min 판별(backtest_analysis 와 동일 규약)."""
    for value in df.get("매수시간", pd.Series(dtype=object)):
        text = str(value).strip()
        if len(text) == 14 and text.isdigit():
            return "tick"
        if len(text) == 12 and text.isdigit():
            return "min"
    return "unknown"


def time_band(hms: Optional[int], timeframe: str) -> str:
    bands = TICK_TIME_BANDS if timeframe == "tick" else MIN_TIME_BANDS
    if hms is None:
        return "unknown"
    for edge, label in bands:
        if hms < edge:
            return label
    return "out_of_window"


def cap_band(value: Any) -> str:
    try:
        cap = float(value)
    except (TypeError, ValueError):
        return "unknown"
    for edge, label in CAP_BANDS:
        if cap < edge:
            return label
    return "unknown"


def _num(df: pd.DataFrame, col: str) -> pd.Series:
    """컬럼 → 수치 Series. 컬럼 부재 시 전체 NaN Series(스칼라 nan 반환 방지 —
    부재 컬럼이 파생 수식에 들어가면 .where 호출에서 죽던 실측 결함, 2026-07-30)."""
    if col not in df.columns:
        return pd.Series([float("nan")] * len(df), index=df.index, dtype=float)
    return pd.to_numeric(df[col], errors="coerce")


def _safe_div(a: pd.Series, b: pd.Series) -> pd.Series:
    return a / b.where(b != 0)


@dataclass
class LabelDataset:
    """enrich() 출력 — 라벨 행렬 + 변수 카탈로그."""

    df: pd.DataFrame
    timeframe: str
    features: List[str] = field(default_factory=list)        # 사용 가능(분산>0) 설명변수
    excluded: Dict[str, str] = field(default_factory=dict)   # 제외 컬럼 → 사유
    derived: List[str] = field(default_factory=list)         # 이번에 만든 D_* 목록


def enrich(df: pd.DataFrame) -> LabelDataset:
    """거래 DF 에 리프 좌표 + 파생변수(D_*)를 더하고 설명변수 목록을 만든다(무예외).

    입력 df 는 변형하지 않는다(사본에 추가 — 불변성 규약).
    """
    out = df.copy()
    timeframe = detect_timeframe(out)

    # ---- 리프 좌표 ----
    hms = out.get("매수시간", pd.Series(dtype=object)).map(_hms_from_buy_time)
    out["leaf_time"] = [time_band(h, timeframe) for h in hms]
    out["leaf_cap"] = out.get("시가총액", pd.Series(dtype=object)).map(cap_band)
    out["leaf"] = out["leaf_time"] + "×" + out["leaf_cap"]

    derived: List[str] = []

    def put(name: str, series: pd.Series) -> None:
        out[name] = series
        derived.append(name)

    # ---- 파생(구 14컬럼만으로 가능한 것) ----
    현재가, 등락율 = _num(out, "B_현재가"), _num(out, "B_등락율")
    매수잔, 매도잔 = _num(out, "B_매수총잔량"), _num(out, "B_매도총잔량")
    전일종가 = _safe_div(현재가, 1 + 등락율 / 100.0)
    put("D_전일종가", 전일종가)
    put("D_총호가매수비율", _safe_div(매수잔, 매수잔 + 매도잔))
    put("D_잔량비", _safe_div(매도잔, 매수잔))
    put("D_거래대금시총비", _safe_div(_num(out, "B_당일거래대금"), _num(out, "B_시가총액")))
    분고, 분저 = _num(out, "B_분봉고가"), _num(out, "B_분봉저가")
    put("D_분봉위치율", _safe_div(현재가 - 분저, 분고 - 분저))

    # ---- 파생(엔진 v2 확장 컬럼 필요 — 있을 때만) ----
    if "B_시가" in out.columns:
        시가 = _num(out, "B_시가")
        put("D_시가등락율", _safe_div(시가 - 전일종가, 전일종가) * 100.0)
        put("D_시가대비등락율", _safe_div(현재가 - 시가, 시가) * 100.0)
    if "B_고가" in out.columns and "B_저가" in out.columns:
        고가, 저가 = _num(out, "B_고가"), _num(out, "B_저가")
        put("D_현재가위치", _safe_div(현재가 - 저가, 고가 - 저가) * 100.0)
        put("D_고가근접율", 현재가 - (고가 - (고가 - 저가) * 0.3))
    if "B_체결강도평균" in out.columns:
        put("D_체결강도비율", _safe_div(_num(out, "B_체결강도"), _num(out, "B_체결강도평균")))
    if timeframe == "tick" and "B_초당거래대금평균" in out.columns:
        put("D_거래대금폭발배수", _safe_div(_num(out, "B_초당거래대금"), _num(out, "B_초당거래대금평균")))
        put("D_누적수급비", _safe_div(_num(out, "B_누적초당매수수량"), _num(out, "B_누적초당매도수량")))
    if timeframe == "min" and "B_분당거래대금평균" in out.columns:
        put("D_거래대금폭발배수", _safe_div(_num(out, "B_분당거래대금"), _num(out, "B_분당거래대금평균")))
        put("D_수급비", _safe_div(_num(out, "B_분당매수수량"), _num(out, "B_분당매도수량")))

    # ---- 설명변수 자동 편입(하드코딩 금지 — 헤더 주도) ----
    features: List[str] = []
    excluded: Dict[str, str] = {}
    for col in out.columns:
        if not (col.startswith("B_") or col.startswith("D_")):
            continue
        vals = pd.to_numeric(out[col], errors="coerce")
        n_valid = int(vals.notna().sum())
        if n_valid == 0:
            excluded[col] = "non_numeric"
            continue
        if n_valid < max(1, int(len(out) * 0.5)):
            excluded[col] = f"missing>{50}%"
            continue
        if float(vals.std(skipna=True) or 0.0) == 0.0:
            # min CSV 의 B_초당*(전부 0) 같은 타임프레임 외 필드 자동 제외.
            excluded[col] = "zero_variance"
            continue
        features.append(col)

    return LabelDataset(df=out, timeframe=timeframe, features=features,
                        excluded=excluded, derived=derived)


def leaf_matrix(ds: LabelDataset, min_n: int = DEFAULT_LEAF_MIN_N) -> List[Dict[str, Any]]:
    """리프(시간밴드×시총단계)별 잔차 요약 — 평균과 **중앙값·승률 병기**(R0 반영).

    반환 행: {leaf_time, leaf_cap, n, mean_pct, median_pct, win_rate, total_krw,
              reliable(n>=min_n)} — mean 정렬은 소비자 몫(정렬하지 않고 좌표순).
    """
    rows: List[Dict[str, Any]] = []
    if ds.df.empty:
        return rows
    pct = pd.to_numeric(ds.df.get("수익률"), errors="coerce")
    krw = pd.to_numeric(ds.df.get("수익금"), errors="coerce")
    for (lt, lc), idx in ds.df.groupby(["leaf_time", "leaf_cap"]).groups.items():
        p = pct.loc[idx].dropna()
        if p.empty:
            continue
        rows.append({
            "leaf_time": lt,
            "leaf_cap": lc,
            "n": int(len(p)),
            "mean_pct": float(p.mean()),
            "median_pct": float(p.median()),
            "win_rate": float((p > 0).mean() * 100.0),
            "total_krw": float(krw.loc[idx].sum() or 0.0),
            "reliable": bool(len(p) >= min_n),
        })
    return rows


def feature_discrimination(ds: LabelDataset) -> List[Dict[str, Any]]:
    """설명변수별 변별력 — 승/패 그룹 Cohen's d (R1 게이트 측정용).

    반환: [{feature, n, d, win_mean, loss_mean}] |d| 내림차순.
    검정(FDR)은 autopsy.analyze 가 담당 — 여기는 효과크기 순위만(게이트 판단용).
    """
    out: List[Dict[str, Any]] = []
    pct = pd.to_numeric(ds.df.get("수익률"), errors="coerce")
    is_win = pct > 0
    for col in ds.features:
        vals = pd.to_numeric(ds.df[col], errors="coerce")
        w, l = vals[is_win].dropna(), vals[~is_win].dropna()
        if len(w) < 10 or len(l) < 10:
            continue
        import math
        pooled = math.sqrt(((len(w) - 1) * float(w.std()) ** 2
                            + (len(l) - 1) * float(l.std()) ** 2)
                           / max(1, len(w) + len(l) - 2))
        d = (float(w.mean()) - float(l.mean())) / pooled if pooled > 0 else 0.0
        out.append({"feature": col, "n": int(len(w) + len(l)), "d": float(d),
                    "win_mean": float(w.mean()), "loss_mean": float(l.mean())})
    out.sort(key=lambda r: abs(r["d"]), reverse=True)
    return out


def load_csv(csv_path: str) -> pd.DataFrame:
    """거래 CSV 로드(utf-8-sig). 실패는 빈 DF(무예외)."""
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig")
    except Exception:  # noqa: BLE001
        return pd.DataFrame()


def build(csv_path: str) -> LabelDataset:
    """CSV 경로 → enrich 한 라벨 데이터셋(원스톱)."""
    return enrich(load_csv(csv_path))
