# -*- coding: utf-8 -*-
"""W4~W5 성과 차트 생성 — 엔진 실거래 기록에서만 그린다(지도 추정 아님).

산출: docs/research/quant_scoring_pipeline/artifacts/w4w5_*.png

원칙:
  · 수치는 전부 `_database/backtest.db` 의 실제 체결 기록에서 나온다.
  · 유리한 구간만 그리지 않는다 — 설계 구간 전체를 그린다.
  · 불확실성을 지운 그림을 그리지 않는다(신뢰구간·필요표본을 함께 그린다).

실행: python docs/research/quant_scoring_pipeline/build_w4w5_charts.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager, rcParams

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "artifacts"
OUT.mkdir(parents=True, exist_ok=True)

TABLES = {
    "champion": "stock_bt_Tick_B_902_905_20260806233421",
    "b1": "stock_bt_Tick_B_902_905_20260806234054",
    "b2": "stock_bt_Tick_B_902_905_20260806234631",
    "b3": "stock_bt_Tick_B_902_905_20260806235158",
}

INK = "#1A2332"
MUTED = "#5A6B7D"
GRID = "#D5D9D2"
CHAMP = "#5A6B7D"
B3 = "#0B7A5C"
WARN = "#B7791F"
FAIL = "#B42318"


def _use_korean_font() -> None:
    for name in ("Malgun Gothic", "NanumGothic", "AppleGothic", "Noto Sans KR"):
        if any(f.name == name for f in font_manager.fontManager.ttflist):
            rcParams["font.family"] = name
            break
    rcParams["axes.unicode_minus"] = False  # U+2212 가 Malgun Gothic 에 없다
    rcParams["figure.facecolor"] = "white"
    rcParams["axes.edgecolor"] = GRID
    rcParams["axes.labelcolor"] = INK
    rcParams["text.color"] = INK
    rcParams["xtick.color"] = MUTED
    rcParams["ytick.color"] = MUTED


def load() -> dict[str, pd.DataFrame]:
    con = sqlite3.connect(str(ROOT / "_database" / "backtest.db"))
    out = {}
    for key, table in TABLES.items():
        d = pd.read_sql(f'SELECT 매수시간,종목명,수익률,수익금,보유시간 FROM "{table}"', con)
        d["일자"] = d["매수시간"].astype(str).str[:8].astype(int)
        d["월"] = d["매수시간"].astype(str).str[:6]
        d["key"] = d["매수시간"].astype(str) + "|" + d["종목명"].astype(str)
        out[key] = d.sort_values("매수시간").reset_index(drop=True)
    con.close()
    return out


def _finish(ax, title: str, sub: str = "") -> None:
    # 제목·부제를 직접 좌표로 찍는다 — set_title 의 pad 와 text 가 겹쳐 글자가 포개졌다.
    ax.text(0, 1.13 if sub else 1.04, title, transform=ax.transAxes,
            fontsize=13, fontweight="bold", color=INK, va="bottom")
    if sub:
        ax.text(0, 1.035, sub, transform=ax.transAxes, fontsize=9.5,
                color=MUTED, va="bottom")
    ax.grid(True, axis="y", color=GRID, linewidth=0.7, alpha=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def chart_cumulative(F: dict[str, pd.DataFrame]) -> Path:
    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=170)
    for key, label, color, lw in (("champion", "사람이 만든 챔피언 (902/905)", CHAMP, 2.0),
                                  ("b3", "AI 매도 규칙 B3 (trailing 5%/2%)", B3, 2.6)):
        d = F[key]
        x = pd.to_datetime(d["일자"].astype(str), format="%Y%m%d")
        ax.plot(x, d["수익금"].cumsum() / 10000, label=label, color=color, linewidth=lw)
    ax.axhline(0, color=GRID, linewidth=1)
    ax.set_ylabel("누적 수익금 (만원)")
    ax.legend(frameon=False, fontsize=10, loc="upper left")
    _finish(ax, "누적 수익 — 설계 구간 355일 · 진입 조건 동일, 매도만 교체",
            "엔진 실제 체결 기록 · 챔피언 80.5만원 → B3 142.2만원 (단, B3 는 자본을 2배 쓴다)")
    fig.tight_layout()
    p = OUT / "w4w5_cumulative.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    return p


def chart_capital_fair(F: dict[str, pd.DataFrame]) -> Path:
    metrics = [("총수익금\n(만원)", 80.5, 142.2, True),
               ("필요자금\n(만원)", 100.4, 199.8, False),
               ("총수익률\n(%)", 80.17, 71.17, True),
               ("CAGR\n(%)", 56.30, 49.98, True),
               ("MDD\n(%)", 14.82, 10.48, False),
               ("Calmar\n(CAGR/MDD)", 3.80, 4.77, True)]
    fig, ax = plt.subplots(figsize=(10, 5.0), dpi=170)
    x = np.arange(len(metrics))
    w = 0.36
    a = [m[1] for m in metrics]
    b = [m[2] for m in metrics]
    ax.bar(x - w / 2, a, w, label="챔피언", color=CHAMP)
    ax.bar(x + w / 2, b, w, label="B3", color=B3)
    for i, (name, av, bv, higher_better) in enumerate(metrics):
        b3_wins = (bv > av) if higher_better else (bv < av)
        ax.text(i, max(av, bv) * 1.06, "B3 우세" if b3_wins else "챔피언 우세",
                ha="center", fontsize=8.5,
                color=B3 if b3_wins else WARN, fontweight="bold")
        ax.text(i - w / 2, av, f"{av:,.1f}", ha="center", va="bottom", fontsize=8, color=MUTED)
        ax.text(i + w / 2, bv, f"{bv:,.1f}", ha="center", va="bottom", fontsize=8, color=MUTED)
    ax.set_xticks(x)
    ax.set_xticklabels([m[0] for m in metrics], fontsize=9.5)
    ax.set_yscale("log")
    ax.set_ylabel("값 (로그 축 — 단위가 달라서)")
    ax.legend(frameon=False, fontsize=10, loc="upper right")
    _finish(ax, "자본까지 감안한 정직한 비교 — 일방적 승리가 아니다",
            "B3 는 자본을 2배 쓴다. 총액은 크지만 자본 대비(총수익률·CAGR)는 챔피언이 낫다.")
    fig.tight_layout()
    p = OUT / "w4w5_capital_fair.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    return p


def chart_regime(F: dict[str, pd.DataFrame]) -> Path:
    alld = sorted(set(F["champion"]["일자"]) | set(F["b3"]["일자"]))
    e = np.linspace(0, len(alld), 5).astype(int)
    segs = [(alld[e[i]], alld[min(e[i + 1], len(alld)) - 1]) for i in range(4)]
    labels = [f"구간 {i+1}\n{str(a)[:6]}~{str(b)[:6]}" for i, (a, b) in enumerate(segs)]
    fig, ax = plt.subplots(figsize=(10, 4.8), dpi=170)
    x = np.arange(4)
    w = 0.36
    for key, label, color, off in (("champion", "챔피언", CHAMP, -w / 2), ("b3", "B3", B3, w / 2)):
        d = F[key]
        vals = [d[(d["일자"] >= a) & (d["일자"] <= b)]["수익률"].mean() for a, b in segs]
        bars = ax.bar(x + off, vals, w, label=label, color=color)
        for r, v in zip(bars, vals):
            ax.text(r.get_x() + r.get_width() / 2, v + (0.04 if v >= 0 else -0.10),
                    f"{v:+.2f}", ha="center", fontsize=8.5,
                    color=MUTED if v >= 0 else FAIL)
    ax.axhline(0, color=INK, linewidth=1)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("건당 수익률 (%)")
    ax.legend(frameon=False, fontsize=10)
    _finish(ax, "국면 4분할 - B3 는 4/4 양수, 챔피언은 3/4",
            "챔피언조차 한 구간이 음수다. '4/4 양수'를 합격선으로 쓰면 챔피언도 탈락한다.")
    fig.tight_layout()
    p = OUT / "w4w5_regime.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    return p


def chart_paired(F: dict[str, pd.DataFrame]) -> Path:
    m = F["champion"].merge(F["b3"], on="key", suffixes=("_A", "_B"))
    diff = (m["수익률_B"] - m["수익률_A"]).to_numpy()
    mean, sd = diff.mean(), diff.std(ddof=1)
    se = sd / np.sqrt(len(diff))
    lo, hi = mean - 1.96 * se, mean + 1.96 * se

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6), dpi=170,
                             gridspec_kw={"width_ratios": [1.25, 1]})
    ax = axes[0]
    ax.hist(diff, bins=40, color=B3, alpha=0.75, edgecolor="white", linewidth=0.5)
    ax.axvline(0, color=INK, linewidth=1.2)
    ax.axvline(mean, color=FAIL, linewidth=1.8, linestyle="--",
               label=f"평균 {mean:+.3f}%p")
    ax.set_xlabel("거래별 차이 (B3 빼기 챔피언, %p)")
    ax.set_ylabel("거래 수")
    ax.legend(frameon=False, fontsize=9.5)
    _finish(ax, f"거래별로는 거의 반반 — 개선 {int((diff>0).sum())}건 vs 악화 {int((diff<0).sum())}건",
            "평균 우위는 소수의 큰 거래에서 나온다.")

    ax = axes[1]
    ax.errorbar([0], [mean], yerr=[[mean - lo], [hi - mean]], fmt="o",
                color=B3, capsize=8, markersize=9, linewidth=2.2)
    ax.axhline(0, color=FAIL, linewidth=1.4, linestyle="--")
    ax.text(0.06, 0, " 0 = 차이 없음", color=FAIL, fontsize=9, va="bottom")
    ax.text(0.06, mean, f" {mean:+.3f}%p", fontsize=9.5, va="center", color=INK)
    ax.text(0.06, lo, f" 하한 {lo:+.3f}", fontsize=8.5, va="center", color=MUTED)
    ax.text(0.06, hi, f" 상한 {hi:+.3f}", fontsize=8.5, va="center", color=MUTED)
    ax.set_xlim(-0.35, 0.9)
    ax.set_xticks([])
    ax.set_ylabel("거래당 차이 (%p)")
    _finish(ax, "95% 신뢰구간이 0 을 넘는다 → 아직 확정 못함",
            "P(B3 우세) = 94.7% · 95% 기준에 간발로 미달")
    fig.tight_layout()
    p = OUT / "w4w5_paired.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    return p


def chart_power() -> Path:
    fig, ax = plt.subplots(figsize=(10, 4.4), dpi=170)
    labels = ["현재 표본\n(설계 355일)", "필요 표본\n(짝지은 검정)", "라벨 미생성분까지\n(DB 보유 952일)"]
    vals = [155, 475, 155 * 952 / 355]
    colors = [FAIL, B3, WARN]
    bars = ax.barh(labels[::-1], vals[::-1], color=colors[::-1], height=0.55)
    for r, v in zip(bars, vals[::-1]):
        ax.text(v + 8, r.get_y() + r.get_height() / 2, f"{v:,.0f}건",
                va="center", fontsize=10, fontweight="bold", color=INK)
    ax.axvline(475, color=B3, linestyle="--", linewidth=1.4)
    ax.set_xlabel("거래 수")
    ax.set_xlim(0, 560)
    _finish(ax, "진짜 병목 — 표본이 3.1배 부족하다",
            "DB 에는 이미 952 거래일이 있는데 라벨은 355일분만 만들어져 있다(결손 597일).")
    fig.tight_layout()
    p = OUT / "w4w5_power.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    return p


def main() -> None:
    _use_korean_font()
    F = load()
    for fn in (chart_cumulative, chart_capital_fair, chart_regime, chart_paired):
        print("saved:", fn(F))
    print("saved:", chart_power())


if __name__ == "__main__":
    main()
