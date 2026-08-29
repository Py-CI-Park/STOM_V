"""unit 공통 픽스처 (2026-06-12 신설).

라이브 상태 파일 격리: run_loop·publish 계열을 부르는 테스트들이 실제
`ai_strategy_loop/state/current_state.json`을 덮어써 대시보드 상단에
'segrun gen 2/2' 같은 합성 run이 표시되던 오염(실사고 — 사용자가 두 차례
목격)을 차단한다. 각 테스트는 자신만의 tmp 경로를 본다.
"""

from __future__ import annotations

import pytest

from tests.unit.slow_suite_manifest import is_slow_suite


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Apply the measured slow marker without editing large contract files."""
    slow_marker = pytest.mark.slow_suite
    for item in items:
        if is_slow_suite(item.nodeid):
            item.add_marker(slow_marker)


@pytest.fixture(autouse=True)
def _isolate_live_state(monkeypatch, tmp_path):
    from ai_strategy_loop.controller import state as S

    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")

    # 2026-06-12 추가: 발굴 이력 DB 오염 차단 — phase4/discovery 테스트들이
    # 실제 _database/backtest_history.db에 TestBuy/A·B 행을 쓰던 실사고
    # (discovery_runs 619~623 실측, gen_02와 동일 패턴)의 근본 수정.
    import cli.history as H

    monkeypatch.setattr(H, "DEFAULT_DB_PATH", str(tmp_path / "backtest_history.db"))
