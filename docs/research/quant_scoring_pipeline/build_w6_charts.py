# -*- coding: utf-8 -*-
"""W6 결과 차트 — 원장(엔진 실측)과 지도 산출에서만 그린다.

산출: docs/research/quant_scoring_pipeline/artifacts/w6_*.png

원칙(build_w4w5_charts.py 와 동일):
  · 수치는 전부 실측에서 나온다 — 손으로 적은 숫자를 그리지 않는다.
  · 불확실성을 지운 그림을 그리지 않는다(신뢰구간을 함께 그린다).
  · 자본 축을 감춘 그림을 그리지 않는다(총수익금 옆에 필요자금).

실행: python docs/research/quant_scoring_pipeline/build_w6_charts.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager, rcParams

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "artifacts"
OUT.mkdir(parents=True, exist_ok=True)
LABELS = ROOT / "ai_strategy_loop" / "state" / "labels"

# 문서 폴더에서 직접 실행해도 되게 저장소 루트를 경로에 넣는다.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

INK, MUTED, GRID = "#1A2332", "#5A6B7D", "#D5D9D2"
PASS, WARN, FAIL, CHAMP = "#0B7A5C", "#B7791F", "#B42318", "#5A6B7D"


def _font() -> None:
    for name in ("Malgun Gothic", "NanumGothic", "AppleGothic", "Noto Sans KR"):
        if any(f.name == name for f in font_manager.fontManager.ttflist):
            rcParams["font.family"] = name
            break
    rcParams["axes.unicode_minus"] = False      # U+2212 가 Malgun Gothic 에 없다
    rcParams["figure.facecolor"] = "white"
    rcParams["axes.edgecolor"] = GRID
    rcParams["axes.labelcolor"] = INK
    rcParams["text.color"] = INK
    rcParams["xtick.color"] = MUTED
    rcParams["ytick.color"] = MUTED


def _finish(ax, title: str, sub: str = "") -> None:
    # 제목을 좌표로 직접 찍는다 — set_title 의 pad 와 text 가 겹쳐 글자가 포개진 전례.
    ax.text(0, 1.13 if sub else 1.04, title, transform=ax.transAxes,
            fontsize=13, fontweight="bold", color=INK, va="bottom")
    if sub:
        ax.text(0, 1.03, sub, transform=ax.transAxes, fontsize=10.5,
                color=MUTED, va="bottom")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y", color=GRID, lw=.7, alpha=.8)
    ax.set_axisbelow(True)


def _save(fig, name: str) -> None:
    path = OUT / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  {path.relative_to(ROOT)}")


def _ledger():
    from ai_strategy_loop.controller import strategy_ledger as sl
    rows = sl.latest_per_candidate()
    return {str(r["sell_name"] or r["candidate_id"]): r for r in rows}


# ---------------------------------------------------------------------------
# 1. 자본 축 — 총수익금만 보면 자본을 더 쓴 쪽이 이긴다
# ---------------------------------------------------------------------------

def chart_capital(led) -> None:
    order = ["Tick_S_902_905", "W6_S_TURN_TIME_STOP", "W4_S_TRAIL_5_2",
             "W6_S_TURN_TREND_BREAK", "W6_S_TURN_HARD_STOP",
             "W4_S_TRAIL_3_1p5", "W4_S_TRAIL_3_1"]
    rows = [(k, led[k]) for k in order if k in led]
    names = [k.replace("Tick_S_902_905", "챔피언").replace("W6_S_TURN_", "B3+")
              .replace("W4_S_", "") for k, _ in rows]
    money = np.array([float(r["total_profit_krw"] or 0) / 1e6 for _, r in rows])
    seed = np.array([float(r["seed_capital"] or 0) / 1e6 for _, r in rows])
    rate = np.array([float(r["total_profit_pct"] or 0) for _, r in rows])
    base_rate = rate[0]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.6, 4.6))
    y = np.arange(len(names))[::-1]
    ax1.barh(y + .18, money, .34, color=[PASS if i else CHAMP for i in range(len(names))],
             label="총수익금")
    ax1.barh(y - .18, seed, .34, color=MUTED, alpha=.55, label="필요자금")
    ax1.set_yticks(y); ax1.set_yticklabels(names, fontsize=9.5)
    ax1.set_xlabel("백만원")
    ax1.legend(frameon=False, fontsize=9, loc="lower right")
    _finish(ax1, "총수익금 vs 필요자금",
            "자본을 두 배 쓰면 수익도 커 보인다 — 나란히 놓아야 속지 않는다")

    colors = [CHAMP] + [PASS if v >= base_rate else FAIL for v in rate[1:]]
    ax2.barh(y, rate, .55, color=colors)
    ax2.axvline(base_rate, color=CHAMP, ls="--", lw=1.2)
    ax2.text(base_rate, y.max() + .55, f" 합격선 {base_rate:.0f}%",
             color=CHAMP, fontsize=9, va="bottom")
    for yy, v in zip(y, rate):
        ax2.text(v + 4, yy, f"{v:.1f}%", va="center", fontsize=9, color=INK)
    ax2.set_yticks(y); ax2.set_yticklabels([])
    ax2.set_xlabel("총수익률 (%) = 총수익금 / 필요자금")
    ax2.set_xlim(0, max(rate) * 1.18)
    _finish(ax2, "자본 대비 수익률", "이 축에서 챔피언을 넘은 것은 시간손절 하나뿐")
    fig.tight_layout()
    _save(fig, "w6_capital_axis.png")


# ---------------------------------------------------------------------------
# 2. 짝지은 신뢰구간 — 확정과 미확정을 한 눈에
# ---------------------------------------------------------------------------

def chart_forest(led) -> None:
    order = ["W4_S_TRAIL_5_2", "W6_S_TURN_TREND_BREAK", "W6_S_TURN_HARD_STOP",
             "W6_S_TURN_TIME_STOP", "W4_S_TRAIL_3_1p5", "W4_S_TRAIL_3_1"]
    rows = [(k, led[k]) for k in order
            if k in led and led[k].get("paired_ci_low") is not None]
    names = [k.replace("W6_S_TURN_", "B3+").replace("W4_S_", "") for k, _ in rows]
    mid = np.array([float(r["paired_mean_diff_pct"]) for _, r in rows])
    lo = np.array([float(r["paired_ci_low"]) for _, r in rows])
    hi = np.array([float(r["paired_ci_high"]) for _, r in rows])
    sig = [bool(r["paired_significant"]) for _, r in rows]

    fig, ax = plt.subplots(figsize=(9.4, 4.2))
    y = np.arange(len(names))[::-1]
    for yy, m, l, h, s in zip(y, mid, lo, hi, sig):
        color = PASS if s else WARN
        ax.plot([l, h], [yy, yy], color=color, lw=2.4, solid_capstyle="round")
        ax.plot([l, h], [yy, yy], "|", color=color, ms=9)
        ax.plot(m, yy, "o", color=color, ms=7)
        ax.text(h + .03, yy, "확정" if s else "미확정", va="center",
                fontsize=9, color=color, fontweight="bold")
    ax.axvline(0, color=INK, lw=1.1)
    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=9.5)
    ax.set_xlabel("챔피언 대비 건당 차이 (%p) · 짝지은 95% 신뢰구간")
    ax.set_xlim(min(lo) - .08, max(hi) + .22)
    _finish(ax, "짝지은 검정 — 구간이 0을 넘어야 확정이다",
            "같은 진입을 1:1 로 맞춰 진입 분산을 제거했다 (표본 352~358짝)")
    fig.tight_layout()
    _save(fig, "w6_paired_ci.png")


# ---------------------------------------------------------------------------
# 3. 매도축 응답면 — 고원인가 절벽인가
# ---------------------------------------------------------------------------

def chart_surface() -> None:
    # 태그를 고정하지 않는다 — 라벨이 넓어지면 새 태그로 산출된다(_wide → _wide832).
    #   가장 최근 산출을 그린다.
    found = sorted((LABELS / "design_v5").glob("_exit_response_surface*.json"),
                   key=lambda q: q.stat().st_mtime)
    if not found:
        print("  (응답면 산출 없음 — 건너뜀)")
        return
    path = found[-1]
    rep = json.loads(path.read_text(encoding="utf-8"))
    arms, gives = rep["arms"], rep["gives"]
    grid = np.array([[np.nan if v is None else v for v in row] for row in rep["matrix"]])
    verdict = {(c["arm"], c["give"]): c["verdict"] for c in rep["cells"]}

    fig, ax = plt.subplots(figsize=(8.6, 5.2))
    im = ax.imshow(grid, cmap="YlGn", aspect="auto", origin="upper")
    for i, a in enumerate(arms):
        for j, g in enumerate(gives):
            v = grid[i, j]
            if np.isnan(v):
                continue
            mark = {"고원": "O", "경사": "/", "절벽": "!", "음수": "-"}.get(
                verdict.get((a, g), ""), "")
            # 진한 칸에 어두운 글자를 얹으면 안 읽힌다 — 명도에 따라 뒤집는다.
            share = (v - np.nanmin(grid)) / max(np.nanmax(grid) - np.nanmin(grid), 1e-9)
            ax.text(j, i, f"{v:.2f}\n{mark}", ha="center", va="center",
                    fontsize=9, color="white" if share > 0.55 else INK)
    ax.set_xticks(range(len(gives))); ax.set_xticklabels([f"{g:g}" for g in gives])
    ax.set_yticks(range(len(arms))); ax.set_yticklabels([f"+{a:g}%" for a in arms])
    ax.set_xlabel("되돌림 허용 (%p)"); ax.set_ylabel("무장 임계")
    ax.grid(False)
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(False)
    counts = rep["verdict_counts"]
    ax.text(0, 1.13, f"매도축 응답면 — {rep['entry_positions']:,}건 진입 · {len(rep['cells'])}셀",
            transform=ax.transAxes,
            fontsize=13, fontweight="bold", color=INK, va="bottom")
    ax.text(0, 1.03,
            f"고원 {counts.get('고원', 0)} · 경사 {counts.get('경사', 0)} · "
            f"절벽 {counts.get('절벽', 0)} · 음수 {counts.get('음수', 0)}"
            "   (O 고원 · / 경사 · ! 절벽)",
            transform=ax.transAxes, fontsize=10.5, color=MUTED, va="bottom")
    fig.colorbar(im, ax=ax, label="지도 건당 기대값 (%)")
    fig.tight_layout()
    _save(fig, "w6_response_surface.png")


# ---------------------------------------------------------------------------
# 4. 진입 절 제거 — 지도 예측과 엔진 실측이 어긋난다
# ---------------------------------------------------------------------------

def chart_entry_gap() -> None:
    abl = LABELS / "design_v5" / "_entry_ablation.json"
    rel = LABELS / "design_v4" / "_entry_relax_ext.json"
    if not (abl.exists() and rel.exists()):
        print("  (진입 산출 없음 — 건너뜀)")
        return
    ablation = {c["clause"]: c for c in json.loads(abl.read_text(encoding="utf-8"))["clauses"]}
    relax = json.loads(rel.read_text(encoding="utf-8"))
    base = float(relax["baseline_metrics"]["avg_profit_pct"])

    names, mapd, engd, gates = [], [], [], []
    for o in relax["outcomes"]:
        key = o["clause"]
        names.append(key.replace("905_", ""))
        mapd.append(float(ablation[key]["expectancy_delta_pct"]))
        engd.append(float(o["engine"]["avg_profit_pct"]) - base)
        gates.append(bool((o.get("gate") or {}).get("pass")))

    fig, ax = plt.subplots(figsize=(9.4, 4.4))
    x = np.arange(len(names))
    ax.bar(x - .19, mapd, .36, color=MUTED, alpha=.65, label="지도 예측")
    ax.bar(x + .19, engd, .36,
           color=[PASS if g else FAIL for g in gates], label="엔진 실측")
    ax.axhline(0, color=INK, lw=1.1)
    # 값 라벨은 막대 **바깥쪽**에 붙이되, 아래로 내려가는 막대의 라벨이 x 축
    #   눈금 글자와 겹치지 않도록 아래쪽 여백을 먼저 확보한다(실측: -0.270 이
    #   '시가대비' 위에 포개졌다).
    span = max(max(mapd + engd) - min(mapd + engd), 1e-6)
    pad = span * .10
    ax.set_ylim(min(mapd + engd + [0.0]) - pad * 1.8, max(mapd + engd + [0.0]) + pad)
    for xx, m, e, g in zip(x, mapd, engd, gates):
        ax.text(xx - .19, m + (pad * .12 if m >= 0 else -pad * .55), f"{m:+.3f}",
                ha="center", va="bottom" if m >= 0 else "top",
                fontsize=8.5, color=MUTED)
        ax.text(xx + .19, e + (pad * .12 if e >= 0 else -pad * .55), f"{e:+.3f}",
                ha="center", va="bottom" if e >= 0 else "top",
                fontsize=8.5, color=PASS if g else FAIL)
    ax.set_xticks(x); ax.set_xticklabels(names, fontsize=10)
    ax.set_ylabel("챔피언 대비 건당 차이 (%p)")
    ax.legend(frameon=False, fontsize=9)
    _finish(ax, "진입 절 제거 — 지도는 셋 다 개선이라 했다",
            "엔진에서는 셋 중 둘이 악화. 지도 순위(1·2·3위)가 정확히 뒤집혔다")
    fig.tight_layout()
    _save(fig, "w6_entry_map_vs_engine.png")


def main() -> None:
    _font()
    led = _ledger()
    print("W6 차트 생성:")
    chart_capital(led)
    chart_forest(led)
    chart_surface()
    chart_entry_gap()


if __name__ == "__main__":
    main()
