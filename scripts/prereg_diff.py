# -*- coding: utf-8 -*-
"""prereg-diff CLI 래퍼 (백로그 A5 / WBS v3 P1-2).

alpha_lab/discipline/prereg_diff.py 를 파일 경로로 로드해 실행한다.
(discipline 패키지 __init__.py 는 별도 소유(A1) — 존재 여부에 의존하지 않는다.)

사용 예 (D1 첫 실전 적용):
  python scripts/prereg_diff.py ^
    --prereg docs/research/condition_research/plans/2026-07-12_d1_clause_ablation_preregistration.md ^
    --result docs/research/condition_research/research_runs/alpha_restart_20260710/d1_clause_ablation_summary.json
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = _ROOT / "alpha_lab" / "discipline" / "prereg_diff.py"


def _load_module():
    """discipline 모듈을 패키지 초기화 없이 파일 경로로 로드한다."""
    spec = importlib.util.spec_from_file_location(
        "alpha_discipline_prereg_diff", str(_MODULE_PATH))
    if spec is None or spec.loader is None:
        raise ImportError(f"모듈 로드 실패: {_MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):  # 파이프/구형 스트림이면 무시
        pass
    sys.exit(_load_module().main(sys.argv[1:]))
