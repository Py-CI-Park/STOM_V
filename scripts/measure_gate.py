# -*- coding: utf-8 -*-
"""measure_gate CLI 래퍼 (백로그 A7 / WBS v3 P1-3).

alpha_lab.discipline.measure_gate를 호출해 실행한다.

측정 배치 기동 직전에 호출해 exit code 로 기동 여부를 정한다:
  0 = pass(기동 허용) / 1 = fail(기동 거부) / 2 = 인자·기록 오류

사용 예:
  python scripts/measure_gate.py ^
    --sealed-doc docs/research/condition_research/plans/<봉인문서>.md ^
    --code alpha_lab/clause_lab/judge.py --code scripts/<측정스크립트>.py ^
    --expect scripts/<측정스크립트>.py=<sha256> --json-out <결과>.json
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_root = str(_ROOT)
if _root not in sys.path:
    sys.path.insert(0, _root)

from alpha_lab.discipline.measure_gate import main


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):  # 파이프/구형 스트림이면 무시
        pass
    sys.exit(main(sys.argv[1:]))
