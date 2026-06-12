"""결정 카드 자동 초안 생성기 (2026-06-12)

N10 양식 의무 필드(비교군 ≥3 · 약세 연도 단독 성과 · 기각된 경로 ·
거래 중복도 · 남은 검증)를 아티팩트 JSON + loop_runs.db에서 자동 조립.
판정·권고는 사람이 작성 — 이 스크립트는 재료 조립만 담당.

사용:
  PYTHONUTF8=1 python -m ai_strategy_loop.scripts.gen_decision_card [--out PATH] [--force]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# 수집 함수 (주입형)
# ---------------------------------------------------------------------------

def load_json(path: Path) -> Optional[Dict[str, Any]]:
    """JSON 파일 로더. 파일 없거나 파싱 실패 시 None 반환."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def collect_oos_rows(
    con: sqlite3.Connection,
    run_id_pattern: str = "%oos%",
) -> Dict[str, List[Dict[str, Any]]]:
    """generations 테이블에서 OOS run의 FROZEN/BASE_SEED(gen_no=0) 행 수집.

    반환: {"<run_id>": [{"gen_no": int, "buy_name": str, "profit": float,
                         "mdd": float, "trade_count": int}, ...]}
    """
    cur = con.cursor()
    cur.execute(
        """
        SELECT run_id, gen_no, buy_name, profit, mdd, trade_count
        FROM generations
        WHERE run_id LIKE ?
        ORDER BY run_id, gen_no
        """,
        (run_id_pattern,),
    )
    rows: Dict[str, List[Dict[str, Any]]] = {}
    for run_id, gen_no, buy_name, profit, mdd, trade_count in cur.fetchall():
        rows.setdefault(run_id, []).append(
            {
                "gen_no": gen_no,
                "buy_name": buy_name or "",
                "profit": profit or 0.0,
                "mdd": mdd or 0.0,
                "trade_count": trade_count or 0,
            }
        )
    return rows


# ---------------------------------------------------------------------------
# 순수 compose 함수
# ---------------------------------------------------------------------------

def _fmt_profit(v: Any) -> str:
    try:
        return f"{int(v):,}"
    except Exception:
        return str(v)


def _na(v: Any, fmt: str = "") -> str:
    """값이 None/빈 시 '자료 없음' 반환."""
    if v is None:
        return "자료 없음"
    if isinstance(v, str) and not v.strip():
        return "자료 없음"
    if fmt == "profit":
        return _fmt_profit(v)
    if fmt == "pct":
        try:
            return f"{float(v):.3f}"
        except Exception:
            return str(v)
    return str(v)


def compose_card(
    selected: Dict[str, Any],
    overfit: Dict[str, Any],
    overlap: Optional[Dict[str, Any]],
    yearly: Optional[Dict[str, Any]],
    oos_rows: Dict[str, List[Dict[str, Any]]],
    regime: Optional[Dict[str, Any]],
    rejected: Optional[Dict[str, Any]],
    now_label: str = "",
) -> str:
    """결정 카드 마크다운 초안 합성 — 순수 함수(테스트 대상).

    입력 결측은 "자료 없음"으로 표기. 예외 발생 금지.
    """
    lines: List[str] = []

    # --- 제목 ---
    cand = selected.get("selected_candidate") or {}
    buy_name = cand.get("buy_name") or selected.get("run_id") or "후보명 불명"
    lines += [
        f"# 결정 카드 — {buy_name} [DRAFT]",
        f"> 생성: {now_label}",
        "",
        "> **N10 양식 의무 필드**: 비교군 ≥3 · 약세 연도 단독 성과 · 기각된 경로 ·",
        "> 거래 중복도 · 남은 검증.",
        "",
    ]

    # --- 섹션 0: 판정 보류 문구 ---
    lines += [
        "## 0. 자동 조립 공시",
        "",
        "> **이 초안은 자동 조립 — 판정·권고는 사람이 작성.**",
        "> 수치는 전부 advisory. 최종 결정 전 사람이 각 섹션을 검토·보완해야 한다.",
        "",
    ]

    # --- 섹션 1: 후보 ---
    lines += ["## 1. 후보", ""]
    seed = selected.get("seed_profile") or {}
    sel_yearly = selected.get("selected_yearly") or {}
    years = sel_yearly.get("years") or []

    lines += [
        f"- **buy_name**: {_na(cand.get('buy_name'))}",
        f"- **sell_name**: {_na(cand.get('sell_name'))}",
        f"- **run_id**: {_na(selected.get('run_id'))}",
        f"- **gen_no**: {_na(cand.get('gen_no'))}",
        f"- **graded_score**: {_na(cand.get('graded_score'), 'pct')}",
        "",
    ]

    lines += [
        "### 1-1. 훈련 성과 (train)",
        "",
        "| 구간 | 후보 | 시드 | 비교 |",
        "|---|---|---|---|",
    ]
    cand_profit = cand.get("profit")
    cand_mdd = cand.get("mdd")
    cand_trades = cand.get("trade_count")
    seed_profit = seed.get("profit")
    seed_mdd = seed.get("mdd")
    seed_trades = seed.get("trade_count")

    def _diff_profit(a: Any, b: Any) -> str:
        try:
            pct = (float(a) - float(b)) / abs(float(b)) * 100
            return f"{pct:+.1f}%"
        except Exception:
            return "자료 없음"

    lines.append(
        f"| train | {_na(cand_profit, 'profit')} / MDD {_na(cand_mdd)} / {_na(cand_trades)}건"
        f" | {_na(seed_profit, 'profit')} / MDD {_na(seed_mdd)} / {_na(seed_trades)}건"
        f" | 수익 {_diff_profit(cand_profit, seed_profit)} · MDD 차 |"
    )

    # 약세 연도 (N10 의무)
    bear_year_row = ""
    if years:
        # 약세 연도 = 수익 최소 연도
        try:
            bear = min(years, key=lambda y: y[1])
            bear_year = bear[0]
            bear_profit = bear[1]
            # seed yearly from selected_yearly — seed별 연도 별도 없으면 표기만
            bear_year_row = (
                f"| **{bear_year} (약세 연도 단독)** | **{_fmt_profit(bear_profit)}** | 자료 없음 | — |"
            )
        except Exception:
            bear_year_row = "| 약세 연도 | 자료 없음 | 자료 없음 | — |"
    else:
        bear_year_row = "| 약세 연도 | 자료 없음 | 자료 없음 | — |"
    lines.append(bear_year_row)
    lines.append("")

    # 연도별
    lines += ["### 1-2. 연도별 (train)", "", "| 연도 | 수익 |", "|---|---|"]
    if years:
        for yr, pf in years:
            lines.append(f"| {yr} | {_fmt_profit(pf)} |")
    else:
        lines.append("| — | 자료 없음 |")
    pos = sel_yearly.get("positive_years")
    obs = sel_yearly.get("observed_years")
    lines += [
        "",
        f"- 흑자 연도: {_na(pos)} / {_na(obs)}",
        "",
    ]

    # --- 섹션 2: 과적합 통계 (V1) ---
    lines += ["## 2. 과적합 통계 (V1)", ""]
    dsr_d = overfit.get("dsr") or {}
    pbo_d = overfit.get("pbo") or {}
    mc = overfit.get("mc_block_bootstrap") or {}
    pool_ind = overfit.get("pool_independence") or {}
    twin_warn = pool_ind.get("pbo_reliability_warning") or ""

    lines += [
        f"- **DSR**: {_na(dsr_d.get('dsr'), 'pct')}",
        f"- **n_trials**: {_na(overfit.get('n_trials'))}",
        f"- **PBO**: {_na(pbo_d.get('pbo'), 'pct')}",
        f"- **쌍둥이 경고**: {twin_warn if twin_warn else '자료 없음'}",
        "",
        "### 2-1. MC 블록 부트스트랩",
        "",
        f"- P(흑자): {_na(mc.get('p_positive'))}",
        f"- 중앙값 수익: {_na(mc.get('profit_p50'), 'profit')}",
        f"- n_days: {_na(mc.get('n_days'))}",
        "",
    ]

    # --- 섹션 3: OOS 연도별 표 (후보 vs 시드) ---
    lines += ["## 3. OOS 연도별 (후보 vs 시드)", ""]
    if oos_rows:
        lines += [
            "| run_id | gen_no | buy_name | profit | mdd | trade_count |",
            "|---|---|---|---|---|---|",
        ]
        for run_id in sorted(oos_rows.keys()):
            for row in oos_rows[run_id]:
                lines.append(
                    f"| {run_id} | {row['gen_no']} | {row['buy_name']}"
                    f" | {_fmt_profit(row['profit'])} | {row['mdd']} | {row['trade_count']} |"
                )
        lines.append("")
    else:
        lines += ["자료 없음", ""]

    # --- 섹션 4: 거래 중복도 (N10 의무) ---
    lines += ["## 4. 거래 중복도 (N10 의무)", ""]
    if overlap:
        jaccard = overlap.get("jaccard")
        n_a = overlap.get("n_trades_a")
        n_b = overlap.get("n_trades_b")
        n_common = overlap.get("n_common")
        interp = overlap.get("interpretation") or ""
        lines += [
            f"- **Jaccard**: {_na(jaccard, 'pct')}",
            f"- 후보 거래 수: {_na(n_b)} / 시드 거래 수: {_na(n_a)} / 공통: {_na(n_common)}",
            f"- 해석: {interp if interp else '자료 없음'}",
            "",
        ]
    else:
        lines += ["자료 없음", ""]

    # --- 섹션 5: 레짐 분해 ---
    lines += ["## 5. 레짐 분해", ""]
    if regime:
        breakdowns = regime.get("breakdowns") or {}
        metric = regime.get("metric") or "자료 없음"
        lines += [f"- 지표: {metric}", ""]
        if breakdowns:
            lines += [
                "| 전략 | 레짐 | 수익 | 기간(일) |",
                "|---|---|---|---|",
            ]
            for strat, bd in breakdowns.items():
                for regime_label in ("active", "contracted", "unlabeled"):
                    seg = bd.get(regime_label) or {}
                    seg_profit = seg.get("profit")
                    seg_days = seg.get("days")
                    if seg_profit is not None:
                        lines.append(
                            f"| {strat} | {regime_label} | {_fmt_profit(seg_profit)} | {_na(seg_days)} |"
                        )
            lines.append("")
            # concentration warning
            for strat, bd in breakdowns.items():
                conc = bd.get("concentration")
                warn = bd.get("warning")
                if conc is not None:
                    lines.append(f"- {strat} concentration: {conc}"
                                 + (f" — {warn}" if warn else ""))
            lines.append("")
        else:
            lines += ["자료 없음", ""]
    else:
        lines += ["자료 없음", ""]

    # --- 섹션 6: 기각된 경로 (N10 의무) ---
    lines += ["## 6. 기각된 경로 (N10 의무)", ""]
    if rejected:
        entries = rejected.get("rejected") or []
        if entries:
            lines += [
                "| 레이블 | 기각일 | 기각 근거 | train 수익 |",
                "|---|---|---|---|",
            ]
            for e in entries:
                label = e.get("label") or "—"
                rej_at = e.get("rejected_at") or "—"
                basis = e.get("reject_basis") or "—"
                train = e.get("train") or {}
                t_profit = _fmt_profit(train.get("profit")) if train.get("profit") is not None else "—"
                lines.append(f"| {label} | {rej_at} | {basis} | {t_profit} |")
            lines.append("")
        else:
            lines += ["자료 없음", ""]
    else:
        lines += ["자료 없음", ""]

    # --- 섹션 7: 비교군 (N10 의무 — ≥3) ---
    lines += ["## 7. 비교군 (N10 의무 — 차점 후보, ≥3 등재)", ""]
    eligible = selected.get("eligible_candidates") or []
    if len(eligible) >= 1:
        lines += [
            "| gen_no | positive_years | 연도별 수익 요약 |",
            "|---|---|---|",
        ]
        for ec in eligible[:8]:
            gn = ec.get("gen_no")
            ey = ec.get("yearly") or {}
            ey_years = ey.get("years") or []
            pos_yrs = ey.get("positive_years")
            yr_summary = " / ".join(
                f"{y[0]}:{_fmt_profit(y[1])}" for y in ey_years
            ) if ey_years else "자료 없음"
            lines.append(f"| {gn} | {_na(pos_yrs)} | {yr_summary} |")
        lines.append("")
        if len(eligible) < 3:
            lines.append("> ⚠️ 비교군 후보 3개 미만 — N10 요건 미충족")
            lines.append("")
    else:
        lines += ["자료 없음", "", "> ⚠️ 비교군 없음 — N10 요건 미충족", ""]

    # --- 섹션 8: 남은 검증·결정 칸 (N10 의무) ---
    lines += [
        "## 8. 남은 검증 · 결정 (N10 의무 — 사람이 작성)",
        "",
        "| # | 항목 | 결과 |",
        "|---|---|---|",
        "| 1 | V2 플라시보 | ___ |",
        "| 2 | V4 walk-forward | ___ |",
        "| 3 | V5 슬리피지 | ___ |",
        "| 4 | 기타 | ___ |",
        "",
        "## 9. 최종 결정 (사람이 작성)",
        "",
        "- **판정**: ___ (PROMOTE / NEEDS_MORE_EVIDENCE / REJECT)",
        "- **근거**: ___",
        "- **결정자**: ___",
        "- **결정일**: ___",
        "",
        "> [DRAFT] 자동 조립 초안 — 판정·권고는 사람이 작성. 수치 전부 advisory.",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="결정 카드 자동 초안 생성기 (N10 양식)"
    )
    ap.add_argument("--out", default="", help="출력 경로 (기본: .omo/evidence/tmap-walkforward/decision_card_draft_YYYYMMDD.md)")
    ap.add_argument("--force", action="store_true", help="기존 파일 덮어쓰기 허용")
    args = ap.parse_args()

    today = datetime.now().strftime("%Y%m%d")

    # 아티팩트 경로
    evidence_dir = REPO_ROOT / ".omo" / "evidence" / "claude-condition-research-20260610"
    wf_dir = REPO_ROOT / ".omo" / "evidence" / "tmap-walkforward"

    selected = load_json(evidence_dir / "p5-selected-candidate.json") or {}
    overfit = load_json(evidence_dir / "p5-overfit-advisory.json") or {}
    overlap = load_json(evidence_dir / "p5-trade-overlap.json")
    yearly = load_json(evidence_dir / "p5-yearly-advisory.json")
    regime = load_json(wf_dir / "regime_report_20260612.json")
    rejected = load_json(wf_dir / "rejected_registry.json")

    # OOS rows from DB
    db_path = REPO_ROOT / "ai_strategy_loop" / "state" / "loop_runs.db"
    oos_rows: Dict[str, Any] = {}
    if db_path.exists():
        con = sqlite3.connect(str(db_path))
        try:
            oos_rows = collect_oos_rows(con)
        finally:
            con.close()

    now_label = datetime.now().strftime("%Y-%m-%d %H:%M")
    text = compose_card(
        selected=selected,
        overfit=overfit,
        overlap=overlap,
        yearly=yearly,
        oos_rows=oos_rows,
        regime=regime,
        rejected=rejected,
        now_label=now_label,
    )

    out_path = (
        Path(args.out)
        if args.out
        else wf_dir / f"decision_card_draft_{today}.md"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if out_path.exists() and not args.force:
        print(f"[ERROR] 파일 이미 존재: {out_path}")
        print("       덮어쓰려면 --force 옵션을 사용하라.")
        return 1

    out_path.write_text(text, encoding="utf-8")
    print(f"[CARD] {out_path}")

    # 섹션 요약 출력
    section_headers = [l for l in text.splitlines() if l.startswith("## ")]
    print("섹션 목록:")
    for h in section_headers:
        print(f"  {h}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
