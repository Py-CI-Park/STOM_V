"""HOF4 — 챔피언이 놓친 승자를 전수 추출하고 배제 사유를 판정한다.

사전 등록: `docs/research/quant_scoring_pipeline/2026-08-12_HOF4_사전등록.md`
(커밋 `33882bcb` — 실행 전)

## 무엇을 세나

학습 구간(달력 411일)의 09:00~09:05 에서, 트레일링(5/2)로 들어갔으면 +5% 이상
났을 지점(승자) 중 챔피언이 사지 않은 onset 을 전수 추출하고, 각 onset 이
**챔피언의 어느 절에 걸려 배제됐는지**를 우주 동명 컬럼으로 판정한다.

## 이 산출은 시드 전용이다

`trail_5_2` 는 전방 라벨(lookahead)이고 챔피언 매도가 아니다(근사).
여기서 나온 어떤 문턱도 채택되지 않는다 — 판정은 HOF5 엔진 A/B 다.
"남긴 수익금" 합계는 실현 가능 금액이 아니라 규모 감각용 근사다.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from typing import Callable, Final

import numpy as np
import pandas as pd

from ai_strategy_loop.labeling.run_trade_autopsy import (
    _BT_DB, _LABEL_ROOT, calendar_days, load_trades, split_days)

#: 사전 등록 §4 — 실행 전 고정.
WINDOW: Final = (90000, 90500)
WINNER_LABEL: Final = "trail_5_2"
WINNER_MIN_PCT: Final = 5.0
ONSET_GAP_SEC: Final = 60
TAKEN_GAP_SEC: Final = 60
MIN_PRICE: Final = 1000

#: 추출에 필요한 우주 컬럼.
COLUMNS: Final = [
    "일자", "종목코드", "시분초", "현재가", "시가", "고가", "저가", "등락율",
    "시가총액", "체결강도", "회전율", "전일비", "전일동시간비", "당일거래대금",
    "시가등락율", "시가대비등락율", "고저평균대비등락율", "초당순매수금액",
    "초당거래대금배율_30", "초당매수수량", "매도총잔량", "매수총잔량",
    "라운드피겨위5호가이내", "VI가격", "VI호가단위", "관심종목",
    "flag_no_trade", "flag_limit_up", "flag_vi_near",
    WINNER_LABEL, "trailt_5_2",
]


def _sec(hhmmss: pd.Series | np.ndarray) -> np.ndarray:
    h = np.asarray(hhmmss, dtype=np.int64)
    return (h // 10000) * 3600 + ((h // 100) % 100) * 60 + h % 100


#: 챔피언 절 판정 — 밴드별. True = 통과, False = 이 절에 걸림.
#:   챔피언 DSL(scratchpad/champion_buy.py 27~114행)을 그대로 옮겼다.
#:   우주에 없는 재료(당일거래대금각도(30)·누적초당수량(30)비율)는 UNEVALUATED 로 둔다.
Clause = tuple[str, Callable[[pd.DataFrame], pd.Series]]

_COMMON: Final[list[Clause]] = [
    ("관심종목", lambda d: d["관심종목"] == 1),
    ("VI아래5호가", lambda d: d["현재가"] < d["VI가격"] - 5 * d["VI호가단위"]),
    ("라운드피겨", lambda d: d["라운드피겨위5호가이내"] == 0),
    ("고저평균대비등락율>0", lambda d: d["고저평균대비등락율"] > 0),
    ("시가총액<3000", lambda d: d["시가총액"] < 3000),
    ("초당순매수금액1~1000", lambda d: (d["초당순매수금액"] > 1) & (d["초당순매수금액"] < 1000)),
    ("고가권20%이내", lambda d: d["현재가"] > d["고가"] - (d["고가"] - d["저가"]) * 0.20),
]

BAND1_CLAUSES: Final[list[Clause]] = _COMMON + [
    ("현재가1000~50000", lambda d: (d["현재가"] > 1000) & (d["현재가"] <= 50000)),
    ("등락율1~8", lambda d: (d["등락율"] > 1.0) & (d["등락율"] <= 8.0)),
    ("시가등락율1~4", lambda d: (d["시가등락율"] >= 1.0) & (d["시가등락율"] < 4.0)),
    ("시가대비등락율0.5~6", lambda d: (d["시가대비등락율"] >= 0.5) & (d["시가대비등락율"] < 6.0)),
    ("전일비>0", lambda d: (d["전일비"] > 0) & (d["전일동시간비"] > 0)),
    ("회전율>2", lambda d: d["회전율"] > 2),
    ("당일거래대금>500", lambda d: d["당일거래대금"] > 5 * 100),
    ("초당거래대금배율>3", lambda d: d["초당거래대금배율_30"] > 3.0),
    ("초당매수>매도잔량20%", lambda d: d["초당매수수량"] > d["매도총잔량"] * 0.20),
    ("잔량비0.1~2", lambda d: (d["매도총잔량"] > d["매수총잔량"] * 0.10)
                            & (d["매도총잔량"] < d["매수총잔량"] * 2.0)),
    ("체결강도100~300", lambda d: (d["체결강도"] >= 100) & (d["체결강도"] <= 300)),
]

BAND2_CLAUSES: Final[list[Clause]] = _COMMON + [
    ("현재가1000~30000", lambda d: (d["현재가"] > 1000) & (d["현재가"] <= 30000)),
    ("등락율2~15", lambda d: (d["등락율"] > 2.0) & (d["등락율"] <= 15.0)),
    ("시가등락율0~8", lambda d: (d["시가등락율"] >= 0.0) & (d["시가등락율"] < 8.0)),
    ("시가대비등락율3~8", lambda d: (d["시가대비등락율"] >= 3.0) & (d["시가대비등락율"] < 8.0)),
    ("전일비>5", lambda d: (d["전일비"] > 5) & (d["전일동시간비"] > 0)),
    ("회전율>1.5", lambda d: d["회전율"] > 1.5),
    ("당일거래대금>5000", lambda d: d["당일거래대금"] > 50 * 100),
    ("초당거래대금배율>2", lambda d: d["초당거래대금배율_30"] > 2.0),
    ("초당매수>매도잔량30%", lambda d: d["초당매수수량"] > d["매도총잔량"] * 0.30),
    ("매수잔량>매도잔량10%", lambda d: d["매도총잔량"] * 0.10 < d["매수총잔량"] * 1.0),
    ("체결강도50~300", lambda d: (d["체결강도"] >= 50) & (d["체결강도"] <= 300)),
]

#: 우주 컬럼으로 판정 불가 — 아는 척하지 않는다(사전 등록 §4).
UNEVALUATED: Final = ("당일거래대금각도(30)", "누적초당수량(30)비율(밴드2)",
                      "초당거래대금N(1)배(밴드2)")


def find_onsets(frame: pd.DataFrame) -> pd.DataFrame:
    """승자 초 → (일자·종목코드)별 60초 dedupe 한 onset 만 남긴다."""
    winners = frame[
        (frame["시분초"] >= WINDOW[0]) & (frame["시분초"] < WINDOW[1])
        & (frame["flag_no_trade"] == 0) & (frame["flag_limit_up"] == 0)
        & (frame["flag_vi_near"] == 0) & (frame["현재가"] > MIN_PRICE)
        & (frame[WINNER_LABEL] >= WINNER_MIN_PCT)
    ].copy()
    if winners.empty:
        return winners
    winners = winners.sort_values(["종목코드", "시분초"])
    sec = _sec(winners["시분초"])
    new_code = winners["종목코드"].ne(winners["종목코드"].shift())
    gap = pd.Series(sec, index=winners.index).diff() > ONSET_GAP_SEC
    return winners[new_code | gap]


def match_trade_codes(day_frame: pd.DataFrame, trades: pd.DataFrame) -> tuple[dict, int]:
    """챔피언 거래 → 종목코드. (일자·매수시간±2초·현재가=매수가) 유일 일치.

    반환: ({(코드, 초): True}, 미매칭 수). 미매칭은 로그 대상(사전 등록 §6-3).
    """
    taken: dict = {}
    unmatched = 0
    sec_all = _sec(day_frame["시분초"])
    for _, trade in trades.iterrows():
        t_sec = int(_sec(np.array([trade["B_시분초"]]))[0])
        near = day_frame[(np.abs(sec_all - t_sec) <= 2)
                         & (day_frame["현재가"] == trade["매수가"])]
        codes = near["종목코드"].unique()
        if len(codes) == 1:
            taken[(codes[0], t_sec)] = True
        else:
            unmatched += 1
    return taken, unmatched


def drop_taken(onsets: pd.DataFrame, taken: dict) -> pd.DataFrame:
    """챔피언이 산 지점 ±60초 이내의 onset 은 '놓친 것'이 아니다."""
    if onsets.empty or not taken:
        return onsets
    sec = _sec(onsets["시분초"])
    keep = np.ones(len(onsets), dtype=bool)
    for i, (code, s) in enumerate(zip(onsets["종목코드"].to_numpy(), sec)):
        for (t_code, t_sec) in taken:
            if code == t_code and abs(int(s) - t_sec) <= TAKEN_GAP_SEC:
                keep[i] = False
                break
    return onsets[keep]


def evaluate_clauses(onsets: pd.DataFrame) -> pd.DataFrame:
    """onset 별로 해당 밴드 절을 판정해 실패 절 목록·수를 붙인다."""
    out = onsets.copy()
    out["밴드"] = np.where(out["시분초"] < 90200, 1, 2)
    fails: list[list[str]] = [[] for _ in range(len(out))]
    for band, clauses in ((1, BAND1_CLAUSES), (2, BAND2_CLAUSES)):
        part = out[out["밴드"] == band]
        if part.empty:
            continue
        position = {idx: i for i, idx in enumerate(out.index)}
        for name, fn in clauses:
            passed = fn(part)
            for idx in part.index[~passed.fillna(False)]:
                fails[position[idx]].append(name)
    out["실패절"] = fails
    out["실패수"] = [len(f) for f in fails]
    return out


def summarize(onsets: pd.DataFrame) -> dict:
    """배제 사유 분포 + 단일 절 실패의 절별 '남긴 수익(근사)' 집계."""
    total = len(onsets)
    reason_counts: dict[str, int] = {}
    for failed in onsets["실패절"]:
        for name in failed:
            reason_counts[name] = reason_counts.get(name, 0) + 1
    single = onsets[onsets["실패수"] == 1]
    single_by: dict[str, dict] = {}
    for name in sorted({f[0] for f in single["실패절"]}):
        part = single[[f == [name] for f in single["실패절"]]]
        single_by[name] = {
            "onsets": int(len(part)),
            "trail_sum_pct": float(part[WINNER_LABEL].sum()),
            "trail_mean_pct": float(part[WINNER_LABEL].mean()),
        }
    return {
        "onsets_total": total,
        "pass_all": int((onsets["실패수"] == 0).sum()),
        "single_fail": int(len(single)),
        "fail_count_hist": {str(k): int(v) for k, v in
                            onsets["실패수"].value_counts().sort_index().items()},
        "reason_counts": dict(sorted(reason_counts.items(),
                                     key=lambda kv: -kv[1])),
        "single_fail_by_clause": dict(sorted(single_by.items(),
                                             key=lambda kv: -kv[1]["onsets"])),
        "unevaluated_clauses": list(UNEVALUATED),
    }


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-name", default="design_v5")
    parser.add_argument("--champion-table",
                        default="stock_bt_Tick_B_902_905_20260810232454")
    args = parser.parse_args()

    split = split_days(calendar_days(args.out_name))
    train = split["train"]
    trades = load_trades(args.champion_table)
    trades = trades[trades["일자"].isin(set(train))]
    print(f"[구간] 학습 {len(train)}일 · 챔피언 거래 {len(trades)}건 "
          f"— 검증·확인은 읽지 않는다", flush=True)

    root = os.path.join(_LABEL_ROOT, args.out_name)
    all_onsets: list[pd.DataFrame] = []
    unmatched_total = 0
    t0 = time.time()
    for i, day in enumerate(train, 1):
        path = os.path.join(root, f"day={day}.parquet")
        frame = pd.read_parquet(path, columns=COLUMNS)
        frame = frame[frame["시분초"] < WINDOW[1]]
        onsets = find_onsets(frame)
        if onsets.empty:
            continue
        day_trades = trades[trades["일자"] == day]
        if not day_trades.empty:
            taken, unmatched = match_trade_codes(frame, day_trades)
            unmatched_total += unmatched
            onsets = drop_taken(onsets, taken)
        all_onsets.append(onsets)
        if i % 100 == 0:
            print(f"  … {i}/{len(train)}일 · onset 누계 "
                  f"{sum(len(o) for o in all_onsets):,} ({time.time()-t0:.0f}초)",
                  flush=True)

    merged = pd.concat(all_onsets, ignore_index=True) if all_onsets else pd.DataFrame()
    if merged.empty:
        print("onset 0건 — 사전 등록 중단 조건. '챔피언 포화'로 기록한다.")
        return
    merged = evaluate_clauses(merged)
    summary = summarize(merged)
    summary["train_days"] = len(train)
    summary["champion_trades_train"] = int(len(trades))
    summary["unmatched_champion_trades"] = int(unmatched_total)
    summary["note"] = ("시드 전용 — trail_5_2 는 lookahead 근사이며 챔피언 매도가 "
                       "아니다. trail_sum_pct 는 실현 가능 금액이 아니다.")

    out_path = os.path.join(root, "_hof4_missed.json")
    keep_cols = [c for c in merged.columns if c not in ("flag_no_trade",
                 "flag_limit_up", "flag_vi_near")]
    payload = {"summary": summary,
               "onsets": merged[keep_cols].to_dict(orient="records")}
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, default=float)

    print(f"\n=== 놓친 승자 (학습 {len(train)}일 · {time.time()-t0:.0f}초) ===")
    print(f" onset 총 {summary['onsets_total']:,} · 전절 통과 {summary['pass_all']} "
          f"· 단일 절 실패 {summary['single_fail']:,} "
          f"· 챔피언 거래 미매칭 {unmatched_total}")
    print("\n 배제 사유 상위 (중복 집계):")
    for name, count in list(summary["reason_counts"].items())[:12]:
        print(f"   {name:<24}{count:>8,}")
    print("\n 단일 절 실패 — 이 절 하나만 풀면 잡히는 onset:")
    for name, row in summary["single_fail_by_clause"].items():
        print(f"   {name:<24}{row['onsets']:>7,}건  trail합 {row['trail_sum_pct']:>10,.0f}%p"
              f"  평균 {row['trail_mean_pct']:.2f}%")
    print(f"\n기록: {out_path}", flush=True)


if __name__ == "__main__":
    main()
