# -*- coding: utf-8 -*-
"""prereg-diff CLI 래퍼 (백로그 A5 / WBS v3 P1-2).

alpha_lab.discipline.prereg_diff 를 호출해 실행한다.

사용 예 (D1 첫 실전 적용):
  python scripts/prereg_diff.py ^
    --prereg docs/research/condition_research/plans/2026-07-12_d1_clause_ablation_preregistration.md ^
    --result docs/research/condition_research/research_runs/alpha_restart_20260710/d1_clause_ablation_summary.json
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_root = str(_ROOT)
if _root not in sys.path:
    sys.path.insert(0, _root)

from alpha_lab.discipline.prereg_diff import main


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):  # 파이프/구형 스트림이면 무시
        pass
    sys.exit(main(sys.argv[1:]))
