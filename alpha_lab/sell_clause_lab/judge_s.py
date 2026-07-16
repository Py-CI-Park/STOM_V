"""매도식 D1 판정 — 절별 Δ·등급·FDR·재발화 분포·리포트 (봉인 bd5bb3c4 §14).

측정량: 절 k 영향 집합(old_clause==k)에서 델타 = (abl_net − old_net)×100 %p.
판정(§14-F4): 양방향 floor ±0.10%p ∧ CI 부호 확정 ∧ 연도 동부호 ∧
BH-FDR(q=0.10, 분모=정식 8) — 제거-개선(Δ≥+0.10) = B2 후보 /
load-bearing(Δ≤−0.10) = 보존 확정. 전체 기대효과 = Δ_k×(영향n/862,932) 병기.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from alpha_lab.clause_lab.judge import _mde_from_ci
from alpha_lab.o4lab.judge_o4 import day_block_mean_bootstrap
from alpha_lab.sell_clause_lab.harness import FIRE_CLAUSES, MIRROR_OF_SELL_SHA
from alpha_lab.stats_common import bh_fdr

N_BOOT = 400
SEED = 20260717              # §14-F5.
FDR_Q = 0.10
EFFECT_FLOOR_PP = 0.10       # §14-F4 양방향.
WEAK_LOW_PP = 0.05
FLOOR_N = 2000               # §14-F3 정식.
FLOOR_YEAR = 400
OBS_LOW = 100
SANITY_FLAT_PP = 0.02
TOTAL_LABELED = 862_932
YEARS = (2022, 2023)

CLAUSE_DESC = {
    1: "등락율>29.5 (상한가 직전)", 2: "시가하회 −2% 최저이탈 손절",
    3: "보유>60 최저가 이탈 손절 (지배 절)", 4: "수익률 +9/−5 하드컷",
    5: "트레일링 60% (최고>3)", 6: "각도급락1 (≥10)", 7: "각도급락2 (5–10)",
    8: "각도급락3 (0–5)", 9: "MA60 이탈 익절 (최고>4.5)",
}

TAGS = [
    "① known-오염: 매도식 임계는 2024 선정창을 본 챔피언 계보의 산물 — "
    "측정창(2022-2023) clean 이나 계보 조건부 진단.",
    "② 출구/진입 조건부: Δ는 서지 온셋(관심종목 유니버스) × 챔피언 매수 계보 "
    "위의 값 — 다른 진입이면 다른 지도.",
    "③ 가문 공유 출구: sha 8ef01e0e 는 stocksell 약 50종이 바이트 공유 — "
    "제거-개선 절 발견 시 파급 범위가 챔피언 1종이 아니다.",
    "④ 온셋≠실전 거래: 은행 온셋 리플레이는 엔진 진입 프레임(1일1회·순위)을 "
    "담지 않는다 — B2 승격은 엔진 A/B(type-a ≤8 별도 봉인)와 U-4 실전이 심판.",
    "⑤ 성능 주장 아님: 본 판정은 절 기여 진단이지 전략 성능·실전 수익 주장이 "
    "아니다.",
]


def _grade(n_used: int, year_counts: Dict[int, int]) -> str:
    if n_used >= FLOOR_N and all(year_counts.get(y, 0) >= FLOOR_YEAR
                                 for y in YEARS):
        return "formal"
    if n_used >= OBS_LOW:
        return "observational"
    return "insufficient"


def _classify(point: float, ci_low: float, ci_high: float,
              both_pos: bool, both_neg: bool, mde: float,
              fdr_survive: bool) -> str:
    if (point >= EFFECT_FLOOR_PP and ci_low > 0 and both_pos and fdr_survive):
        return "removal_candidate"          # 제거 시 개선 — B2 후보.
    if (point <= -EFFECT_FLOOR_PP and ci_high < 0 and both_neg and fdr_survive):
        return "load_bearing"               # 제거 시 악화 — 보존 확정.
    if WEAK_LOW_PP <= abs(point) < EFFECT_FLOOR_PP and (
            (point > 0 and ci_low > 0) or (point < 0 and ci_high < 0)):
        return "weak_signal"
    if np.isfinite(mde) and mde > EFFECT_FLOOR_PP:
        return "no_detect_power"            # 검정력 부족 — 효과 없음 주장 금지.
    return "no_detect_local_opt"            # 이 절은 ±0.10%p 내 — 국소 최적 방향.


def judge_all(deltas: pd.DataFrame, *, n_boot: int = N_BOOT, seed: int = SEED,
              fdr_q: float = FDR_Q) -> Dict[str, object]:
    """절 1~9 판정 — 정식 등급만 FDR 족(분모=정식 수), 관찰은 보고 전용."""
    per: Dict[str, Dict[str, object]] = {}
    for k in FIRE_CLAUSES:
        aff = deltas[deltas["old_clause"] == k]
        used = aff[aff["abl_labeled"]]
        n_aff, n_used = int(len(aff)), int(len(used))
        yc = {int(y): int((used["year"] == y).sum()) for y in YEARS}
        row: Dict[str, object] = {
            "clause": int(k), "desc": CLAUSE_DESC[k],
            "n_affected": n_aff, "n_used": n_used,
            "n_label_dropped": n_aff - n_used, "year_counts": yc,
            "grade": _grade(n_used, yc),
        }
        if n_used > 0:
            d_pp = (used["abl_net"].to_numpy(np.float64)
                    - used["old_net"].to_numpy(np.float64)) * 100.0
            boot = day_block_mean_bootstrap(
                used["day"].to_numpy(np.int64), d_pp, n_boot=n_boot, seed=seed)
            ym = {int(y): {
                "mean_pp": float(np.mean(d_pp[(used["year"] == y).to_numpy()]))
                if yc[int(y)] else float("nan"),
                "n": yc[int(y)],
            } for y in YEARS}
            vals = [ym[y]["mean_pp"] for y in YEARS if yc[y] > 0]
            refire = {str(int(c)): int(n) for c, n in
                      used["abl_clause"].value_counts().sort_index().items()}
            row.update({
                "delta_pp": float(boot["point"]),
                "ci_low_pp": float(boot["ci_low"]),
                "ci_high_pp": float(boot["ci_high"]),
                "p_two_sided": float(boot["p_two"]),
                "mde_pp": float(_mde_from_ci(boot["ci_low"], boot["ci_high"])),
                "year_mean": ym,
                "both_year_positive": bool(vals and all(v > 0 for v in vals)
                                           and len(vals) == 2),
                "both_year_negative": bool(vals and all(v < 0 for v in vals)
                                           and len(vals) == 2),
                "expected_total_pp": float(boot["point"]) * n_used / TOTAL_LABELED,
                "refire_dist": refire,
                "n_boot": n_boot, "seed": seed,
            })
        per[str(k)] = row

    formal = [k for k in FIRE_CLAUSES if per[str(k)]["grade"] == "formal"
              and "p_two_sided" in per[str(k)]]
    pvals = [float(per[str(k)]["p_two_sided"]) for k in formal]
    survive = bh_fdr(pvals, q=fdr_q) if pvals else np.zeros(0, dtype=bool)
    for k, sv in zip(formal, survive):
        r = per[str(k)]
        r["fdr_survive"] = bool(sv)
        r["classification"] = _classify(
            float(r["delta_pp"]), float(r["ci_low_pp"]), float(r["ci_high_pp"]),
            bool(r["both_year_positive"]), bool(r["both_year_negative"]),
            float(r["mde_pp"]), bool(sv))
    for k in FIRE_CLAUSES:
        r = per[str(k)]
        if r["grade"] != "formal" and "delta_pp" in r:
            r["fdr_survive"] = False
            r["classification"] = "observational_report_only"

    removal = [int(k) for k in formal
               if per[str(k)].get("classification") == "removal_candidate"]
    loadb = [int(k) for k in formal
             if per[str(k)].get("classification") == "load_bearing"]
    flat = [k for k in formal
            if abs(float(per[str(k)]["delta_pp"])) < SANITY_FLAT_PP]
    return {
        "per_clause": per,
        "formal_clauses": [int(k) for k in formal],
        "fdr_denominator": len(formal), "fdr_q": fdr_q,
        "removal_candidates": removal, "load_bearing": loadb,
        "kill1_local_optimum": not removal and not loadb,
        "sanity_flat_tripped": len(flat) == len(formal) and len(formal) > 0,
        "mirror_of_sell_sha": MIRROR_OF_SELL_SHA[:8],
    }


def write_outputs(out_dir, judgment: Dict[str, object],
                  run_summary: Dict[str, object],
                  spot: Dict[str, object] | None, *, commit: str = "미기록",
                  ) -> None:
    """summary json + report md — 딱지 5종 강제 인쇄(§14-F11)."""
    out = Path(out_dir)
    payload = {
        "kind": "sell_d1_judgment",
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "preregistration":
            "2026-07-16_sell_d1_exit_ablation_preregistration.md (bd5bb3c4)",
        "window": "2022-03-23~2023-12-31(발견 — 청산 레버: 2024도 known)",
        "run": run_summary, "fullmask_spot": spot, "judgment": judgment,
        "contamination_tags": TAGS, "commit": commit,
    }
    (out / "sell_d1_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    per = judgment["per_clause"]
    lines: List[str] = [
        "# 매도식 D1 판정 — 절-단위 ablation (봉인 bd5bb3c4)", "",
        f"생성 {payload['generated']} · commit {commit}", "",
        "## 결론 먼저",
        f"- 정식 8절 판정 — 제거-개선(B2 후보): {judgment['removal_candidates'] or '없음'}"
        f" / load-bearing(보존 확정): {judgment['load_bearing'] or '없음'}",
        f"- kill-1(절 단위 국소 최적) = {judgment['kill1_local_optimum']}",
        "",
        "| 절 | 설명 | 영향 n | Δ(%p) | CI | 연도(22/23) | MDE | 전체기대(%p) | 등급 | 판정 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for k in FIRE_CLAUSES:
        r = per[str(k)]
        if "delta_pp" in r:
            ym = r["year_mean"]
            lines.append(
                f"| {k} | {r['desc']} | {r['n_used']:,} | {r['delta_pp']:+.3f} "
                f"| [{r['ci_low_pp']:+.3f},{r['ci_high_pp']:+.3f}] "
                f"| {ym[2022]['mean_pp']:+.3f}/{ym[2023]['mean_pp']:+.3f} "
                f"| {r['mde_pp']:.3f} | {r['expected_total_pp']:+.4f} "
                f"| {r['grade']} | {r.get('classification', '-')} |")
        else:
            lines.append(f"| {k} | {r['desc']} | {r['n_used']:,} | — | — | — "
                         f"| — | — | {r['grade']} | 판정 불가 |")
    lines += ["", "## 재발화 분포(절 제거 시 다음 청산 — §14-F7)", ""]
    for k in FIRE_CLAUSES:
        r = per[str(k)]
        if "refire_dist" in r:
            lines.append(f"- 절 {k} 제거 → {r['refire_dist']}")
    lines += ["", "## 딱지(강제 인쇄 — §14-F11)", ""]
    lines += [f"- {t}" for t in TAGS]
    (out / "sell_d1_report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")
