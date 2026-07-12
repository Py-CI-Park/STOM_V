# -*- coding: utf-8 -*-
"""measure_gate CLI 래퍼 (백로그 A7 / WBS v3 P1-3).

alpha_lab/discipline/measure_gate.py 를 파일 경로로 로드해 실행한다.
(discipline 패키지 __init__.py 는 별도 소유(A1) — 존재 여부에 의존하지 않는다.)

측정 배치 기동 직전에 호출해 exit code 로 기동 여부를 정한다:
  0 = pass(기동 허용) / 1 = fail(기동 거부) / 2 = 인자·기록 오류

사용 예:
  python scripts/measure_gate.py ^
    --sealed-doc docs/research/condition_research/plans/<봉인문서>.md ^
    --code alpha_lab/clause_lab/judge.py --code scripts/<측정스크립트>.py ^
    --expect scripts/<측정스크립트>.py=<sha256> --json-out <결과>.json
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = _ROOT / "alpha_lab" / "discipline" / "measure_gate.py"


def _load_module():
    """discipline 모듈을 패키지 초기화 없이 파일 경로로 로드한다."""
    spec = importlib.util.spec_from_file_location(
        "alpha_discipline_measure_gate", str(_MODULE_PATH))
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
