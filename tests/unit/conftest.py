"""unit 공통 픽스처 (2026-06-12 신설).

라이브 상태 파일 격리: run_loop·publish 계열을 부르는 테스트들이 실제
`ai_strategy_loop/state/current_state.json`을 덮어써 대시보드 상단에
'segrun gen 2/2' 같은 합성 run이 표시되던 오염(실사고 — 사용자가 두 차례
목격)을 차단한다. 각 테스트는 자신만의 tmp 경로를 본다.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_live_state(monkeypatch, tmp_path):
    from ai_strategy_loop.controller import state as S

    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
