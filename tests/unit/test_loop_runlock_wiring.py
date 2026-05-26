"""P6 — run_loop의 cross-process 락 배선 단위 테스트 (실루프 미기동).

검증:
  (a) acquire_run_lock이 busy(error)면 run_loop은 LoopState 생성/백테 없이
      즉시 stop_reason='lock_busy'로 반환한다(동시 실행 차단).
  (b) 정상 경로(state 주입=격리)에서는 락을 건너뛴다 — 운영 lockfile 미접촉
      (acquire/release가 호출되지 않음).

run_loop은 락 거부 시 LoopState()를 만들기 전에 반환하므로, acquire mock만으로
실루프(provider/백테) 없이 분기를 검증할 수 있다.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import loop as loopmod  # noqa: E402


def test_run_loop_aborts_when_lock_busy(monkeypatch):
    """(a) 락이 busy면 run_loop은 즉시 lock_busy로 반환(실루프 미기동)."""
    # acquire가 busy(error)를 돌리도록 강제.
    monkeypatch.setattr(loopmod, "acquire_run_lock", lambda *a, **k: {
        "status": "error", "message": "다른 루프가 실행 중입니다", "holder_pid": 12345,
    })

    # LoopState가 만들어지면 안 됨(락 거부가 그 전에 일어난다).
    def _boom(*a, **k):
        raise AssertionError("락 거부 시 LoopState를 만들면 안 됨")

    monkeypatch.setattr(loopmod, "LoopState", _boom)
    # release도 호출되면 안 됨(획득 못 했으므로).
    released = {"n": 0}
    monkeypatch.setattr(loopmod, "release_run_lock",
                        lambda *a, **k: released.__setitem__("n", released["n"] + 1))

    summary = run = loopmod.run_loop(LoopConfig(max_generations=1))
    assert summary["stop_reason"] == "lock_busy"
    assert summary["holder_pid"] == 12345
    assert summary["best_gen"] == -1
    assert released["n"] == 0
    _ = run


def test_run_loop_skips_lock_when_state_injected(monkeypatch):
    """(b) state 주입(격리 테스트 경로)이면 락 acquire/release를 건너뛴다.

    should_terminate를 즉시 stop으로 mock해 실제 세대 생성/백테 없이 분기만
    확인한다. acquire/release가 한 번이라도 호출되면 실패한다(운영 lockfile 미접촉).
    """
    def _no_acquire(*a, **k):
        raise AssertionError("state 주입 경로에서 acquire_run_lock이 호출되면 안 됨")

    def _no_release(*a, **k):
        raise AssertionError("state 주입 경로에서 release_run_lock이 호출되면 안 됨")

    monkeypatch.setattr(loopmod, "acquire_run_lock", _no_acquire)
    monkeypatch.setattr(loopmod, "release_run_lock", _no_release)
    # 첫 세대 시작 전에 종료시켜 실루프(생성/백테) 미기동.
    monkeypatch.setattr(loopmod, "should_terminate", lambda metrics, config: (True, "max_generations"))
    # provider/proxy 기동을 막는다(네트워크 없음).
    monkeypatch.setattr(loopmod, "_make_provider_with_proxy", lambda config: (object(), False))
    monkeypatch.setattr(loopmod, "_refresh_meta_insights", lambda st: None)

    class _FakeState:
        def resume_or_start(self, *a, **k):
            return "run_iso"

        def get_last_completed_gen(self, rid):
            return -1

        def get_run(self, rid):
            return None

        def get_cumulative_generation_count(self, rid):
            return 0

        def get_generations(self, rid):
            return []

        def finish_run(self, *a, **k):
            pass

        def close(self):
            pass

    cfg = LoopConfig(max_generations=0, bt_engine_mode="cold")
    summary = loopmod.run_loop(cfg, state=_FakeState())
    # 주입 경로에선 락을 건드리지 않는다(acquire/release 미호출 = 위 mock이 raise 안 함).
    assert summary["run_id"] == "run_iso"
    assert summary["stop_reason"] == "max_generations"
