"""US-005 Phase 2b — 루프 컨트롤러.

헤드리스 진화 루프의 4가지 책임을 모듈로 분리한다:

  - state.py       : SQLite(WAL) run/generation 영속 + JSON 스냅샷 + resume
  - termination.py : 종료 판정(target / max-gen / cost-cap)
  - export.py      : 우승 전략을 PRODUCTION strategy.db로 export (human gate)
  - loop.py        : 오케스트레이터(generate→backtest→fitness→record→terminate)

모든 엔트리포인트는 cli.* import 전에 ai_strategy_loop.bootstrap을 먼저
import 해야 한다 (env-before-import 격리 계약).
"""

from .export import export_winner
from .state import LoopState
from .termination import should_terminate

__all__ = ["LoopState", "should_terminate", "export_winner"]
