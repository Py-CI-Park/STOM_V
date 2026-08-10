"""HOF2 — 넓은 창 실거래 부검. 손실 거래를 골라내는 절 후보를 **발굴**한다.

## 이것은 판정이 아니라 발굴이다

여기서 나온 어떤 문턱도 채택되지 않는다. 후보 목록과 근거 분포를 만들 뿐이다.
판정은 HOF3 이 **발굴이 보지 못한 구간**(검증/확인)에서 한다.

## 왜 백파인더 원본도, 알파 채굴 재실행도 아닌가

엔진 결과 테이블이 이미 **매수 시점 지표 스냅샷**(`B_*` 22종)을 담고 있다 —
백파인더가 하는 일이 결과에 내장돼 있다. 그리고 라벨이 가상 수익(고정 지평)이
아니라 **챔피언 매도로 실현된 손익**이고, 표본이 임의 시점이 아니라 **챔피언 절을
전부 통과한 진입**이다. 이 조합은 이전 어떤 프로그램도 묻지 않았다.

## ★ 발굴은 TRAIN 구간에서만 한다

전 구간에서 문턱을 고르면 HOF3 의 검증·확인 구간이 이미 오염된다(발굴이 그
날들을 봤다). 그래서 이 러너는 **TRAIN 구간의 거래만** 읽는다. 검증·확인
구간은 파일에서 날짜만 기록하고 **성적을 계산하지 않는다**.

## 부트스트랩이 보정하는 것과 못 하는 것

일 블록 부트스트랩 + BH-FDR 은 **표집 변동**과 **다중 비교**를 다룬다.
문턱을 성적을 보고 골랐다는 **선택 편의는 보정하지 못한다** — 그것은
표본 밖(HOF3 검증·확인)에서만 드러난다.

사용:
    python -m ai_strategy_loop.labeling.run_trade_autopsy \\
        --table stock_bt_HOF1_B_WINDOW_920_20260810233137 --budget 10
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sqlite3
import sys
from typing import Final

import numpy as np
import pandas as pd

_BT_DB: Final = os.path.join(os.path.dirname(__file__), "..", "..",
                             "_database", "backtest.db")
_LABEL_ROOT: Final = os.path.join(os.path.dirname(__file__), "..", "state", "labels")

#: 시각 코호트 — 챔피언의 창(A·B)과 새로 열린 창(C)을 가른다.
#:   하한 90000 을 명시한다: 장 시작 전 시각은 어느 코호트도 아니다.
COHORTS: Final = (("A", 90000, 90200), ("B", 90200, 90500), ("C", 90500, 92000))

#: 결과가 아니라 원인만 쓴다. `R_*`(매수 후 최고/최저)는 미래 정보다.
FEATURE_PREFIX: Final = "B_"

#: 시각 자체는 코호트로 이미 다루므로 피처에서 뺀다.
FEATURE_EXCLUDE: Final = frozenset({"B_시분초"})

#: 문턱 후보 — 분위. 전셀 보고(헌법 5항) 대상이다.
QUANTILES: Final = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)

#: 같은 거래를 남기는 규칙은 같은 가설이다(가격 수준 피처들이 대표적).
JACCARD_DUP: Final = 0.9

#: 가설 예산 기본값 — 헌법 15항.
DEFAULT_BUDGET: Final = 10


def cohort_of(hhmmss: int) -> str:
    """진입 시각을 코호트 이름으로. 창 밖이면 빈 문자열."""
    for name, lo, hi in COHORTS:
        if lo <= int(hhmmss) < hi:
            return name
    return ""


def calendar_days(out_name: str = "design_v5") -> list[int]:
    """설계 구간의 **거래일 달력** — 팔과 무관한 분할 기준.

    ## 왜 팔의 거래일을 쓰면 안 되는가

    분할을 각 팔의 체결 기록에서 뽑으면 팔마다 거래일 수가 달라 **경계가
    움직인다**(챔피언 268일 vs 시간창 후보 550일). 그러면 같은 "검증 구간"이
    후보마다 다른 날짜가 되어 비교가 성립하지 않는다(헌법 10항).

    우주 파케이 파일명(`day=YYYYMMDD.parquet`)이 설계 구간의 거래일 달력이다.
    """
    root = os.path.join(_LABEL_ROOT, out_name)
    days = sorted(int(name[4:12]) for name in os.listdir(root)
                  if name.startswith("day=") and name.endswith(".parquet")
                  and name[4:12].isdigit())
    if not days:
        raise SystemExit(f"거래일 달력을 찾을 수 없다: {root}")
    return days


def split_days(days, *, train: float = 0.5, valid: float = 0.25,
               purge: int = 5) -> dict:
    """거래일 달력을 시간 순서대로 학습/검증/확인으로 가른다.

    구간 사이에 `purge` 거래일을 버려 경계 오염을 막는다(`cli/wfo.py` 개념).
    **발굴은 학습 구간만 본다.**

    입력은 `calendar_days()` 의 달력이어야 한다 — 팔의 체결 기록이 아니다.
    """
    ordered = sorted({int(d) for d in days})
    if train <= 0 or valid <= 0 or train + valid >= 1:
        raise ValueError("train·valid 는 양수이고 합이 1 미만이어야 한다")
    if purge < 0:
        raise ValueError("purge 는 0 이상이어야 한다")
    total = len(ordered)
    cut1, cut2 = int(total * train), int(total * (train + valid))
    if cut1 <= purge or cut2 - cut1 <= purge or total - cut2 <= purge:
        raise ValueError(f"거래일 {total}일로는 purge {purge}일 분할이 불가능하다")
    return {
        "train": ordered[:cut1 - purge],
        "valid": ordered[cut1:cut2 - purge],
        "test": ordered[cut2:],
        "purged": ordered[cut1 - purge:cut1] + ordered[cut2 - purge:cut2],
    }


def usable_features(frame: pd.DataFrame, *, min_unique: int = 5) -> list[str]:
    """상수·저분산 열을 뺀 매수 시점 피처."""
    return [c for c in frame.columns
            if c.startswith(FEATURE_PREFIX) and c not in FEATURE_EXCLUDE
            and frame[c].nunique(dropna=True) >= min_unique]


def scan_thresholds(frame: pd.DataFrame, features: list[str], *,
                    quantiles=QUANTILES, min_keep: int = 100) -> list[dict]:
    """전셀 주사 — 피처 × 분위 × 방향. **전부** 돌려준다(헌법 5항).

    `min_keep` 미만만 남기는 규칙은 버린다 — 표본이 얇으면 무엇이든 좋아 보인다.
    """
    out: list[dict] = []
    for feature in features:
        values = frame[feature].astype(float)
        for q in quantiles:
            threshold = float(values.quantile(q))
            for op in (">=", "<"):
                keep = values >= threshold if op == ">=" else values < threshold
                kept = int(keep.sum())
                if kept < min_keep:
                    continue
                out.append({
                    "feature": feature, "op": op, "threshold": threshold,
                    "quantile": q, "kept": kept,
                    "kept_profit_krw": float(frame.loc[keep, "수익금"].sum()),
                    "kept_avg_pct": float(frame.loc[keep, "수익률"].mean()),
                    "dropped": int(len(frame) - kept),
                    "dropped_profit_krw": float(frame.loc[~keep, "수익금"].sum()),
                })
    return out


def _mask(frame: pd.DataFrame, row: dict) -> pd.Series:
    values = frame[row["feature"]].astype(float)
    return values >= row["threshold"] if row["op"] == ">=" else values < row["threshold"]


def select_candidates(frame: pd.DataFrame, rows: list[dict], *,
                      budget: int = DEFAULT_BUDGET,
                      jaccard_dup: float = JACCARD_DUP) -> list[dict]:
    """효과 순으로 고르되 **같은 거래를 남기는 규칙은 하나로 본다**.

    가격 수준 피처(현재가·시가·고가·저가)처럼 사실상 같은 규칙이 예산을
    나눠 갖는 것을 막는다 — 겹침(Jaccard)이 기준을 넘으면 같은 가설이다.
    """
    picked: list[dict] = []
    masks: list[np.ndarray] = []
    for row in sorted(rows, key=lambda r: r["kept_profit_krw"], reverse=True):
        if len(picked) >= budget:
            break
        current = _mask(frame, row).to_numpy()
        duplicate = False
        for other in masks:
            union = int((current | other).sum())
            if union and (current & other).sum() / union >= jaccard_dup:
                duplicate = True
                break
        if duplicate:
            continue
        picked.append(dict(row))
        masks.append(current)
    return picked


def day_block_bootstrap(frame: pd.DataFrame, keep: pd.Series, *,
                        draws: int = 2000, seed: int = 20260810) -> dict:
    """거래일 단위 재표집 — 같은 날 거래는 서로 독립이 아니다.

    통계량은 **남긴 거래의 총수익금**(일 평균 × 일수). 단측 p 값은
    재표집에서 총수익금이 0 이하로 나온 비율이다.
    """
    daily = (frame.assign(_keep=keep.to_numpy())
             .groupby("일자")
             .apply(lambda g: float(g.loc[g["_keep"], "수익금"].sum()),
                    include_groups=False))
    values = daily.to_numpy(dtype=float)
    n = len(values)
    if n == 0:
        return {"draws": 0, "ci_low": None, "ci_high": None, "p_value": 1.0}
    rng = np.random.default_rng(seed)
    totals = rng.choice(values, size=(draws, n), replace=True).sum(axis=1)
    return {
        "draws": int(draws),
        "observed_krw": float(values.sum()),
        "ci_low": float(np.percentile(totals, 2.5)),
        "ci_high": float(np.percentile(totals, 97.5)),
        "p_value": float((totals <= 0).mean()),
    }


def bh_fdr(pvalues: list[float], *, alpha: float = 0.1) -> list[bool]:
    """Benjamini-Hochberg — 다중 비교에서 살아남는 것만 참."""
    n = len(pvalues)
    if n == 0:
        return []
    order = sorted(range(n), key=lambda i: pvalues[i])
    survive = [False] * n
    cutoff = -1
    for rank, index in enumerate(order, start=1):
        if pvalues[index] <= alpha * rank / n:
            cutoff = rank
    for rank, index in enumerate(order, start=1):
        if rank <= cutoff:
            survive[index] = True
    return survive


def to_dsl(row: dict) -> str:
    """`B_매도총잔량 < 19563` → `매도총잔량 < 19563` (DSL 어휘와 1:1)."""
    name = row["feature"][len(FEATURE_PREFIX):]
    return f"{name} {row['op']} {row['threshold']:.6g}"


def load_trades(table: str, db_path: str | None = None) -> pd.DataFrame:
    path = os.path.abspath(db_path or _BT_DB)
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        frame = pd.read_sql(f'SELECT * FROM "{table}"', con)
    finally:
        con.close()
    frame["일자"] = (frame["매수시간"].astype("int64") // 1_000_000).astype(int)
    frame["코호트"] = frame["B_시분초"].map(cohort_of)
    return frame


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", required=True, help="엔진 결과 테이블(후보 팔)")
    parser.add_argument("--out-name", default="design_v5")
    parser.add_argument("--cohort", default="C", help="부검할 코호트")
    parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET,
                        help="가설 예산 — 절 후보 상한(헌법 15항)")
    parser.add_argument("--min-keep", type=int, default=100)
    parser.add_argument("--alpha", type=float, default=0.1, help="BH-FDR 수준")
    parser.add_argument("--draws", type=int, default=2000)
    args = parser.parse_args()

    frame = load_trades(args.table)
    # 분할은 팔이 아니라 **거래일 달력**이 정한다 — 경계가 팔마다 움직이면
    #   같은 이름의 구간이 후보마다 다른 날짜가 된다(헌법 10항).
    split = split_days(calendar_days(args.out_name))
    train_days = set(split["train"])

    everything = frame[frame["코호트"] != ""]
    cohort_all = everything[everything["코호트"] == args.cohort]
    target = cohort_all[cohort_all["일자"].isin(train_days)].copy()
    if target.empty:
        raise SystemExit(f"학습 구간에 코호트 {args.cohort} 거래가 없다")

    print(f"[표] 전체 {len(frame)}건 · 코호트 {args.cohort} {len(cohort_all)}건 "
          f"· 그중 학습 구간 {len(target)}건", flush=True)
    print(f"[구간] 학습 {len(split['train'])}일 "
          f"({split['train'][0]}~{split['train'][-1]}) · "
          f"검증 {len(split['valid'])}일 · 확인 {len(split['test'])}일 "
          f"· 버림 {len(split['purged'])}일 — **검증·확인은 읽지 않는다**", flush=True)

    cohort_table = [{
        "cohort": name,
        "trades": int((everything["코호트"] == name).sum()),
        "profit_krw": float(everything.loc[everything["코호트"] == name, "수익금"].sum()),
        "avg_pct": float(everything.loc[everything["코호트"] == name, "수익률"].mean()),
        "win_rate": float((everything.loc[everything["코호트"] == name, "수익률"] > 0).mean() * 100),
    } for name, _, _ in COHORTS]

    features = usable_features(target)
    scanned = scan_thresholds(target, features, min_keep=args.min_keep)
    print(f"[주사] 피처 {len(features)}종 × 분위 {len(QUANTILES)} × 방향 2 "
          f"→ 유효 규칙 {len(scanned)}개 (최소 잔존 {args.min_keep}건)", flush=True)

    picked = select_candidates(target, scanned, budget=args.budget)
    for row in picked:
        keep = _mask(target, row)
        row["bootstrap"] = day_block_bootstrap(target, keep, draws=args.draws)
        row["dsl"] = to_dsl(row)
    survive = bh_fdr([r["bootstrap"]["p_value"] for r in picked], alpha=args.alpha)
    for row, ok in zip(picked, survive):
        row["bh_survive"] = bool(ok)

    baseline_profit = float(target["수익금"].sum())
    report = {
        "table": args.table, "cohort": args.cohort,
        "budget": args.budget, "alpha": args.alpha,
        "split": {k: (v if k == "purged" else [v[0], v[-1]] if v else [])
                  for k, v in split.items()},
        "split_sizes": {k: len(v) for k, v in split.items()},
        "cohorts": cohort_table,
        "train_cohort_trades": int(len(target)),
        "train_cohort_profit_krw": baseline_profit,
        "scanned_rules": len(scanned),
        "features": features,
        "candidates": picked,
        "note": ("발굴이지 판정이 아니다. 문턱은 학습 구간에서만 골랐고, "
                 "검증·확인 구간은 읽지 않았다. 부트스트랩·BH-FDR 은 표집 변동과 "
                 "다중 비교를 다룰 뿐 **선택 편의는 보정하지 못한다** — "
                 "그것은 HOF3 의 표본 밖에서만 드러난다."),
    }
    out_dir = os.path.join(_LABEL_ROOT, args.out_name)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "_hof2_autopsy.json")
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=1, default=float)

    print(f"\n=== 절 후보 {len(picked)}종 (학습 구간 코호트 {args.cohort} "
          f"{len(target)}건 · 원본 {baseline_profit:,.0f}원) ===")
    print(f" {'DSL 절':<34}{'잔존':>6}{'남긴수익금':>13}{'CI 하한':>13}{'p':>8}  BH")
    for row in picked:
        boot = row["bootstrap"]
        print(f" {row['dsl']:<34}{row['kept']:>6}{row['kept_profit_krw']:>13,.0f}"
              f"{boot['ci_low']:>13,.0f}{boot['p_value']:>8.3f}"
              f"  {'생존' if row['bh_survive'] else '탈락'}")
    print(f"\n기록: {out_path}", flush=True)


if __name__ == "__main__":
    main()
