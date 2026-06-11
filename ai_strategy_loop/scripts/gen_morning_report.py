"""P-C (2026-06-12) — 아침 보고 자동 생성: 검증 결산·니치 비교·결정 이력 → md.

매 사이클 사람이 손으로 모으던 보고 재료(검증 결산 lines/alerts·PROMOTE
체크리스트·니치 비교 표·최근 run·결정 이력)를 대시보드 페이로드 함수에서
직접 모아 마크다운 한 장으로 만든다(HTTP 불요 — 대시보드가 꺼져 있어도 동작).

사용:
  PYTHONUTF8=1 python -m ai_strategy_loop.scripts.gen_morning_report \
      [--out docs/research/condition_research/auto_reports/morning_YYYYMMDD.md]
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]

_ICON = {"pass": "✅", "warn": "⚠️", "fail": "❌", "pending": "⏳"}


def compose_report(
    verdict: Optional[Dict[str, Any]],
    niche: Optional[Dict[str, Any]],
    ops: Optional[Dict[str, Any]],
    decisions: Optional[Dict[str, Any]],
    now_label: str = "",
) -> str:
    """보고 본문 합성 — 순수 함수(테스트 대상). 빈 입력은 절 단위로 생략."""
    lines: List[str] = [f"# 아침 자동 보고 — {now_label}", ""]

    if verdict:
        checklist = verdict.get("promote_checklist") or []
        if checklist:
            lines += ["## 1. PROMOTE 체크리스트", "",
                      "| 조건 | 상태 | 근거 |", "|---|---|---|"]
            lines += [f"| {c.get('item')} | {_ICON.get(c.get('status'), '?')} |"
                      f" {c.get('detail') or '—'} |" for c in checklist]
            lines.append("")
        for alert in verdict.get("alerts") or []:
            lines.append(f"> ⚠️ {alert}")
        if verdict.get("alerts"):
            lines.append("")
        if verdict.get("lines"):
            lines += ["## 2. 검증 결산", ""]
            lines += [f"- {l}" for l in verdict["lines"]]
            lines.append("")

    runs = (niche or {}).get("runs") or []
    if runs:
        lines += ["## 3. 니치 지도 비교", "",
                  "| run | 상태 | 베이스라인 | 최강 고원/격자 | 동결상관 |",
                  "|---|---|---|---|---|"]
        for r in runs:
            base = r.get("baseline") or {}
            top = r.get("top_slot") or {}
            grid = r.get("grid") or {}
            summary = (
                f"{top.get('param')}: 중심 {top.get('center')}" if top
                else (f"격자 {grid.get('cells')}셀 mesa {grid.get('mesa')}" if grid else "—")
            )
            lines.append(
                f"| {r.get('run_id')} | {r.get('status')} |"
                f" {base.get('profit', 0):,.0f} (MDD {base.get('mdd')}) |"
                f" {summary} | {r.get('corr_vs_frozen', '—')} |"
            )
        lines.append("")

    recent = (ops or {}).get("recent") or []
    if recent:
        lines += ["## 4. 최근 완료 run", ""]
        lines += [f"- {r.get('run_id')} ({r.get('gens')}세대"
                  + (f", 최고 {r.get('best_profit'):,.0f}" if r.get("best_profit") is not None else "")
                  + ")" for r in recent[:8]]
        lines.append("")

    decided = (decisions or {}).get("decisions") or []
    lines += ["## 5. 운용 결정 이력", ""]
    if decided:
        lines += [f"- {d.get('verdict')} — {d.get('note') or '메모 없음'}" for d in decided]
    else:
        lines.append("- 기록 없음 — **V6 결정 대기** (`/ui/verdict.html`)")
    lines.append("")
    lines.append("> 자동 생성(P-C) — 수치는 전부 advisory, 판정 규율은 OOS/사전선언 기준.")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    import ai_strategy_loop.bootstrap  # noqa: F401,PLC0415
    from ai_strategy_loop.dashboard.app import (  # noqa: PLC0415
        _decisions_payload,
        _freeze_verdict_payload,
        _niche_compare_payload,
        _ops_status_payload,
    )

    stamp = time.strftime("%Y-%m-%d %H:%M")
    text = compose_report(
        _freeze_verdict_payload(),
        _niche_compare_payload(""),
        _ops_status_payload(48),
        _decisions_payload(),
        now_label=stamp,
    )
    out = Path(args.out) if args.out else (
        REPO_ROOT / "docs/research/condition_research/auto_reports"
        / f"morning_{time.strftime('%Y%m%d')}.md"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"[REPORT] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
