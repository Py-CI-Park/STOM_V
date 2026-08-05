"""라벨 QA 3종 (실행계획 v2 §3) — 전부 통과 전에는 M-1(지형도) 진행 금지.

QA-1 정합: 실거래(와이드 그물 CSV)의 매수/매도 시각 가격을 tick DB 에서 독립 재계산해
        엔진 실현 수익률과 대조한다. 라벨 계산 경로 전체(가격 조회·비용 모델)를 검증.
QA-2 자기 검증: 902/905 창(09:02~05)+거친 905 필터가 지도에서 실제로 밝은지.
QA-3 음성 대조군: 다른 날의 라벨(민 라벨)에는 변수 정보력이 ≈0 이어야 한다.
"""

from __future__ import annotations

import glob
import json
import os
import sqlite3

import numpy as np
import pandas as pd

from ai_strategy_loop.labeling import label_spec as spec

_DB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "_database")
_LABEL_DIR = os.path.join(os.path.dirname(__file__), "..", "state", "labels", "design")


def _name_to_code() -> dict[str, str]:
    con = sqlite3.connect(f"file:{os.path.join(_DB_DIR, 'code_info.db')}?mode=ro", uri=True)
    try:
        rows = con.execute('SELECT "index", 종목명 FROM stockinfo').fetchall()
    finally:
        con.close()
    return {name: code for code, name in rows}


def _price_at(con: sqlite3.Connection, code: str, hhmmss: int, day: int,
              column: str = "현재가") -> float | None:
    """해당 초 이하 마지막 관측 가격(스테일 허용 내). 없으면 None.

    QA-1 실측(2026-08-05): 엔진 체결 = 매수는 `매도호가1`(83%), 매도는 `매수호가1`(92~93%)
    — 즉 라벨 가격 기준 **A(호가)** 가 엔진 정합 기준이다. 기준 B(현재가)는 참조용.
    """
    stamp = day * 1_000_000 + hhmmss
    row = con.execute(
        f'SELECT "index", {column} FROM "{code}" WHERE "index" <= ? ORDER BY "index" DESC LIMIT 1',
        (stamp,),
    ).fetchone()
    if row is None:
        return None
    obs_sod = spec.hhmmss_to_sod(int(row[0]) % 1_000_000)
    if spec.hhmmss_to_sod(hhmmss) - obs_sod > spec.STALE_TOLERANCE_SEC:
        return None
    return float(row[1])


def qa1_engine_reconciliation(csv_path: str, *, sample_days: int = 10, seed: int = 7) -> dict:
    """실거래 수익률 vs 라벨식 재계산 — 중앙값 오차 ≈ 0 이어야 통과."""
    trades = pd.read_csv(csv_path, encoding="utf-8-sig",
                         usecols=["종목명", "매수시간", "매도시간", "매수가", "매도가", "수익률"])
    trades["일자"] = trades["매수시간"] // 1_000_000
    rng = np.random.default_rng(seed)
    days = rng.choice(trades["일자"].unique(), size=min(sample_days, trades["일자"].nunique()),
                      replace=False)
    picked = trades[trades["일자"].isin(days)]
    codes = _name_to_code()

    diffs: list[float] = []
    buy_price_match = 0
    checked = 0
    unmatched_name = 0
    missing_price = 0
    for day, group in picked.groupby("일자"):
        db = os.path.join(_DB_DIR, f"stock_tick_{day}.db")
        if not os.path.exists(db):
            continue
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            tables = {name for (name,) in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            for trade in group.itertuples():
                code = codes.get(trade.종목명)
                if code is None or code not in tables:
                    unmatched_name += 1
                    continue
                buy = _price_at(con, code, int(trade.매수시간) % 1_000_000, int(day), "매도호가1")
                sell = _price_at(con, code, int(trade.매도시간) % 1_000_000, int(day), "매수호가1")
                if buy is None or sell is None:
                    missing_price += 1
                    continue
                label_ret = ((sell * (1 - spec.COST_OUT)) / (buy * (1 + spec.COST_IN)) - 1) * 100
                diffs.append(label_ret - float(trade.수익률))
                buy_price_match += int(abs(buy - float(trade.매수가)) < 1e-6)
                checked += 1
        finally:
            con.close()

    arr = np.array(diffs)
    result = {
        "checked": checked, "unmatched_name": unmatched_name, "missing_price": missing_price,
        "median_diff_pp": round(float(np.median(arr)), 4) if checked else None,
        "iqr_pp": round(float(np.percentile(arr, 75) - np.percentile(arr, 25)), 4) if checked else None,
        "within_0p1pp": round(float(np.mean(np.abs(arr) <= 0.1)), 4) if checked else None,
        "buy_price_exact_match": round(buy_price_match / checked, 4) if checked else None,
        "pass": bool(checked >= 200 and abs(float(np.median(arr))) <= 0.05),
    }
    return result


def _load_labels(columns: list[str], limit_days: int | None = None) -> pd.DataFrame:
    files = sorted(glob.glob(os.path.join(_LABEL_DIR, "day=*.parquet")))
    if limit_days:
        files = files[:limit_days]
    frames = [pd.read_parquet(f, columns=columns) for f in files]
    return pd.concat(frames, ignore_index=True)


_USABLE = ["flag_no_trade", "flag_limit_up", "flag_vi_near"]


def qa2_self_check() -> dict:
    """902/905 창 자기 검증 — 거친 905 필터 영역이 무조건 평균보다 밝아야 통과."""
    cols = ["분", "시분초", "frB_300", "시가총액", "등락율", "시가대비등락율", "체결강도", *_USABLE]
    df = _load_labels(cols)
    usable = df[(df[_USABLE].sum(axis=1) == 0) & df["frB_300"].notna()]
    window = usable[(usable["시분초"] >= 90200) & (usable["시분초"] < 90500)]
    coarse = window[
        (window["시가총액"] < 3000) & (window["등락율"] > 2.0) & (window["등락율"] <= 15.0)
        & (window["시가대비등락율"] >= 3.0) & (window["시가대비등락율"] < 8.0)
        & (window["체결강도"] >= 50) & (window["체결강도"] <= 300)
    ]
    base_mean = float(window["frB_300"].mean())
    coarse_mean = float(coarse["frB_300"].mean()) if len(coarse) else float("nan")
    return {
        "window_rows": int(len(window)), "coarse_rows": int(len(coarse)),
        "window_mean_pp": round(base_mean, 4),
        "coarse_mean_pp": round(coarse_mean, 4),
        "pass": bool(len(coarse) >= 300 and coarse_mean > base_mean and coarse_mean > 0),
    }


def _decile_spread(frame: pd.DataFrame, variable: str, label: str) -> float:
    """상위 10분위 평균 − 하위 10분위 평균 (간이 정보력)."""
    deciles = pd.qcut(frame[variable], 10, labels=False, duplicates="drop")
    means = frame.groupby(deciles)[label].mean()
    return float(means.iloc[-1] - means.iloc[0])


def qa3_negative_control(variables: tuple[str, ...] = ("체결강도", "등락율", "초당거래대금")) -> dict:
    """민 라벨(같은 종목, 다음 라벨일) 정보력 ≈ 0 검증 — 누출 탐지."""
    cols = ["일자", "종목코드", "시분초", "frB_300", *set(variables), *_USABLE]
    df = _load_labels(list(dict.fromkeys(cols)))
    df = df[(df[_USABLE].sum(axis=1) == 0) & df["frB_300"].notna()]

    # 민 라벨: (종목, 시분초) 를 고정하고 라벨만 그 종목의 "다음 관측일" 것으로 치환.
    df = df.sort_values(["종목코드", "시분초", "일자"])
    df["shifted_label"] = df.groupby(["종목코드", "시분초"])["frB_300"].shift(-1)
    paired = df[df["shifted_label"].notna()]

    out: dict[str, dict[str, float]] = {}
    ok = True
    for var in variables:
        sub = paired[paired[var].notna()]
        true_spread = _decile_spread(sub, var, "frB_300")
        shifted_spread = _decile_spread(sub, var, "shifted_label")
        ratio = abs(shifted_spread) / max(abs(true_spread), 1e-9)
        out[var] = {"true_spread_pp": round(true_spread, 4),
                    "shifted_spread_pp": round(shifted_spread, 4),
                    "shifted_over_true": round(ratio, 3)}
        # 민 라벨 정보력이 진짜의 1/3 을 넘으면 누출 의심.
        ok = ok and (abs(shifted_spread) <= max(abs(true_spread) / 3, 0.02))
    return {"pairs": int(len(paired)), "variables": out, "pass": bool(ok)}


def main() -> None:
    csv = os.path.join(_DB_DIR, "..", "backtest", "csv",
                       "stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260803234054.csv")
    report = {
        "qa1": qa1_engine_reconciliation(os.path.abspath(csv)),
        "qa2": qa2_self_check(),
        "qa3": qa3_negative_control(),
    }
    report["all_pass"] = all(report[k]["pass"] for k in ("qa1", "qa2", "qa3"))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
