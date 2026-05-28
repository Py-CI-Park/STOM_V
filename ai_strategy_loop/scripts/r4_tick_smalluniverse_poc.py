"""R4 PoC — tick small_universe 백테 실증 (TICK 스코프 활성화 검증).

목적: bt_scope='small_universe' + bt_timeframe='tick' (N=8 tick_subset,
divid_mode='종목코드별 분류')에서 백테 1회를 돌려 tick 다종목 백테가
status=success로 끝나고 다중포지션이 창발(mhct>1)함을 관측한다.
seed 인자 주입 없음·엔진/CLI 무수정. r0_multiposition_poc(min)의 tick 대응판.

전제: state/tick_subset.db 가 먼저 빌드돼 있어야 한다
    (python -m ai_strategy_loop.scripts.build_subset_db --timeframe tick --size 8).

실행: STOM_ALLOW_MINIMAL_SETTING=1 python -m ai_strategy_loop.scripts.r4_tick_smalluniverse_poc
"""
from __future__ import annotations

import os
import sys

from ai_strategy_loop import bootstrap  # noqa: F401  (env/DB 경로 셋업)
from ai_strategy_loop.config import LoopConfig
from ai_strategy_loop.controller.loop import REPO_ROOT, run_backtest_for
from ai_strategy_loop.scripts.r0_multiposition_poc import _copy_seed_to_loop_db

SEED_BUY = "Tick_B_902_905_Update_2"
SEED_SELL = "Tick_S_902_905_Update_2"
TICK_SUBSET = os.path.join(REPO_ROOT, "ai_strategy_loop", "state", "tick_subset.db")


def main() -> int:
    print("[R4] === tick small_universe PoC (N=8 tick_subset) ===", flush=True)
    if not os.path.isfile(TICK_SUBSET):
        print(f"[R4] tick subset 없음: {TICK_SUBSET}", flush=True)
        print("[R4] 먼저 빌드: python -m ai_strategy_loop.scripts.build_subset_db "
              "--timeframe tick --size 8", flush=True)
        return 1

    ok_b = _copy_seed_to_loop_db(SEED_BUY, "stockbuy")
    ok_s = _copy_seed_to_loop_db(SEED_SELL, "stocksell")
    if not (ok_b and ok_s):
        print("[R4] 시드 준비 실패 → 중단", flush=True)
        return 1

    config = LoopConfig(
        bt_scope="small_universe",
        bt_timeframe="tick",
        bt_subset_db=TICK_SUBSET,
        bt_engine_mode="cold",      # small_universe → run_backtest_for(cold) 경로.
        bt_engine_count=4,
        bt_window_days_universe=5,  # tick은 무거우니 짧게.
        bt_timeout=300,
        bt_betting="5",
    )
    print(f"[R4] scope={config.bt_scope} timeframe={config.bt_timeframe} "
          f"engines={config.bt_engine_count} "
          f"window_days={config.bt_window_days_universe} "
          f"timeout={config.bt_timeout}", flush=True)
    print(f"[R4] subset={TICK_SUBSET}", flush=True)

    outcome = run_backtest_for(config, SEED_BUY, SEED_SELL)
    print(f"[R4] backtest ok={outcome.ok} status={outcome.status} "
          f"reason={outcome.reason}", flush=True)
    m = outcome.metrics or {}
    mhct = m.get("max_hold_count", 0)
    print("[R4] --- 메트릭 ---", flush=True)
    for k in ("trade_count", "daily_avg_trades", "max_hold_count",
              "total_profit_pct", "mdd_pct", "tpi", "day_count"):
        print(f"[R4]   {k} = {m.get(k)}", flush=True)
    print("", flush=True)

    if not outcome.ok:
        print(f"[R4] FAIL — tick 백테 비성공: {outcome.reason}", flush=True)
        return 2
    if mhct and mhct > 1:
        print(f"[R4] PASS — status=success + max_hold_count(mhct)={mhct} > 1 : "
              f"tick 다종목 다중포지션 창발 (TICK 스코프 활성화 입증).", flush=True)
        return 0
    print(f"[R4] PARTIAL — status=success 이나 mhct={mhct} (>1 아님). "
          f"tick 백테 경로는 동작; 시간겹침 부족 가능(윈도우/종목 조정 검토).", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
