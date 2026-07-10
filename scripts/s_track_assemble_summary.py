"""w4_full_build.json + w4_champion_overlay.json → w4_full_summary.json 병합.

본 적재 빌드/게이트/분석/corr(빌드 산출)과 챔피언 게이트/오버레이/tick 동치
스팟체크(게이트 러너 산출)를 하나의 기계판독 요약으로 합친다. 결정론·재실행 가능.
리포트(w4_full_report.md)는 이 요약에서 저자가 작성한다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_RUN = (_REPO / "docs/research/condition_research/research_runs"
        / "alpha_restart_20260710")


def main(argv=None) -> int:
    build = json.loads((_RUN / "w4_full_build.json").read_text(encoding="utf-8"))
    champ = json.loads(
        (_RUN / "w4_champion_overlay.json").read_text(encoding="utf-8"))
    summary = {
        "meta": {
            "stage": "W4-3 본 적재 + W4-2b 챔피언 게이트 + W4-4 지도",
            "preregistration":
                "docs/research/condition_research/plans/"
                "2026-07-10_s_track_preregistration.md",
            "engine_backtests": 0, "source_access": "read-only (URI mode=ro)",
        },
        "build": build["build"],
        "gates_w4_2a": build["gates"],
        "champion_gate_w4_2b": champ["champion_gate"],
        "tick_equivalence_spotcheck": champ["tick_equivalence_spotcheck"],
        "counts": build["counts"],
        "analysis": build["analysis"],
        "overlay_advisory": champ["overlay_advisory"],
        "corr_matrix": build["corr_matrix"],
        "csv_files": champ["csv_files"],
    }
    out = _RUN / "w4_full_summary.json"
    out.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8")
    print(f"assembled -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
