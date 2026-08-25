from __future__ import annotations

import os
from uuid import uuid4


def create_backtest_shared_memory_name(engine_index: int) -> str:
    """Return a process-local, collision-resistant backtest memory name."""
    return f"stom_backdata_{os.getpid()}_{engine_index}_{uuid4().hex}"
