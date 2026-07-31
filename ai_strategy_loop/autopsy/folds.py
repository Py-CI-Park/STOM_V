"""다중 폴드 워크포워드 검증(QSP5) — '유의성' 대신 '반복 재현'을 증거로 삼는다.

왜 필요한가(실측 근거): 이 분포는 복권형(승률 46%·건당 수익률 표준편차 4%대)이라
평균 t검정은 검출력이 없다 — 건당 +0.17% 엣지를 95% 신뢰로 확인하려면 약 2,127건이
필요한데 리프별 표본은 63~151건뿐이다(limitation_ledger 2026-07-31). 표본을 4배로
늘려도 부족하다. 그래서 판정 기준을 바꾼다:

    "이 주머니가 통계적으로 유의한가?"  →  "여러 해에 걸쳐 반복해서 흑자인가?"

폴드는 시간 순 분할이다(랜덤 분할 금지 — 시장은 시계열이라 미래 정보가 샌다).
한 폴드라도 크게 무너지면 그 주머니는 특정 국면 산물로 본다.
순수 함수 — CSV/DataFrame 만 받는다.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import pandas as pd

# 폴드 판정 기본값 — 과반 흑자 + 최악 폴드의 손실이 전체 이익을 삼키지 않을 것.
DEFAULT_MIN_FOLD_N = 25          # 폴드가 이보다 작으면 판정에서 제외(표본 부족).
DEFAULT_MIN_POS_RATIO = 0.60     # 유효 폴드 중 흑자 비율 하한.
DEFAULT_MAX_WORST_SHARE = 1.00   # 최악 폴드 손실 / 전체 이익 상한(1.0 = 이익을 못 넘김).


def year_key(df: pd.DataFrame) -> pd.Series:
    """매수시간(YYYYMMDD…) → 'YYYY' 연 폴드 라벨."""
    return df["매수시간"].astype(str).str.slice(0, 4)


def half_key(df: pd.DataFrame) -> pd.Series:
    """반기 폴드 — 연 폴드가 2개 미만일 때 대체."""
    s = df["매수시간"].astype(str)
    year = s.str.slice(0, 4)
    month = pd.to_numeric(s.str.slice(4, 6), errors="coerce").fillna(1)
    return year + "H" + (((month - 1) // 6) + 1).astype(int).astype(str)


def quarter_key(df: pd.DataFrame) -> pd.Series:
    s = df["매수시간"].astype(str)
    year = s.str.slice(0, 4)
    month = pd.to_numeric(s.str.slice(4, 6), errors="coerce").fillna(1)
    return year + "Q" + (((month - 1) // 3) + 1).astype(int).astype(str)


def _auto_key(df: pd.DataFrame, min_folds: int = 3) -> pd.Series:
    """연 → 반기 → 분기 순으로 내려가며 최소 폴드 수를 확보한다."""
    for fn in (year_key, half_key, quarter_key):
        k = fn(df)
        if k.nunique() >= min_folds:
            return k
    return quarter_key(df)


def fold_report(df: pd.DataFrame, *,
                min_fold_n: int = DEFAULT_MIN_FOLD_N,
                min_pos_ratio: float = DEFAULT_MIN_POS_RATIO,
                max_worst_share: float = DEFAULT_MAX_WORST_SHARE,
                key: Optional[pd.Series] = None) -> Dict[str, Any]:
    """거래 부분집합 → 폴드별 성적과 통과 여부.

    반환: {folds:[{label,n,pnl,per_trade}], n_eff, pos, pos_ratio, worst,
           total_pnl, passed, reason}
    """
    if df is None or df.empty or "수익금" not in df.columns:
        return {"folds": [], "n_eff": 0, "pos": 0, "pos_ratio": 0.0, "worst": 0.0,
                "total_pnl": 0.0, "passed": False, "reason": "표본 없음"}
    k = key if key is not None else _auto_key(df)
    pnl = pd.to_numeric(df["수익금"], errors="coerce").fillna(0.0)
    rows: List[Dict[str, Any]] = []
    for label, idx in df.groupby(k).groups.items():
        p = float(pnl.loc[idx].sum())
        n = int(len(idx))
        rows.append({"label": str(label), "n": n, "pnl": p,
                     "per_trade": p / n if n else 0.0})
    rows.sort(key=lambda r: r["label"])
    eff = [r for r in rows if r["n"] >= min_fold_n]
    total = float(pnl.sum())
    if len(eff) < 2:
        return {"folds": rows, "n_eff": len(eff), "pos": 0, "pos_ratio": 0.0,
                "worst": min((r["pnl"] for r in rows), default=0.0),
                "total_pnl": total, "passed": False,
                "reason": f"유효 폴드 부족({len(eff)}) — 표본 {min_fold_n}건 이상 폴드 2개 필요"}
    pos = sum(1 for r in eff if r["pnl"] > 0)
    ratio = pos / len(eff)
    worst = min(r["pnl"] for r in eff)
    gains = sum(r["pnl"] for r in eff if r["pnl"] > 0) or 1.0
    worst_share = abs(min(0.0, worst)) / gains
    passed = ratio >= min_pos_ratio and worst_share <= max_worst_share and total > 0
    reason = "통과"
    if total <= 0:
        reason = "전체 손익 음수"
    elif ratio < min_pos_ratio:
        reason = f"흑자 폴드 비율 {ratio:.0%} < {min_pos_ratio:.0%}"
    elif worst_share > max_worst_share:
        reason = f"최악 폴드 손실이 이익의 {worst_share:.0%}"
    return {"folds": rows, "n_eff": len(eff), "pos": pos, "pos_ratio": ratio,
            "worst": worst, "worst_share": worst_share, "total_pnl": total,
            "passed": passed, "reason": reason}


def summarize(report: Dict[str, Any]) -> str:
    """사람이 읽는 한 줄 요약."""
    if not report.get("folds"):
        return "폴드 없음"
    parts = [f"{r['label']}:{r['pnl']/1e6:+.1f}M" for r in report["folds"]]
    return (f"{report['pos']}/{report['n_eff']} 흑자 · " + " ".join(parts)
            + (" · " + report["reason"] if not report["passed"] else ""))
