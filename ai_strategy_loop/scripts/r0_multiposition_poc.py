"""R0 PoC — 다중포지션 창발 실증 (마스터 로드맵 R0).

목적: bt_scope='small_universe'(N=8 subset, divid_mode='종목코드별 분류')에서
백테 1회를 돌려 **최대보유종목수(mhct)>1**이 거래 시간겹침으로 창발함을 관측한다.
seed 인자 주입 없음·엔진/CLI 무수정. (합의 결과: 다중포지션은 입력이 아니라 창발.)

실행: STOM_ALLOW_MINIMAL_SETTING=1 python -m ai_strategy_loop.scripts.r0_multiposition_poc
"""
from __future__ import annotations

import sqlite3
import sys

from ai_strategy_loop import bootstrap  # noqa: F401  (env/DB 경로 셋업)
from ai_strategy_loop.config import LoopConfig
from ai_strategy_loop.controller.loop import run_backtest_for

SRC_DB = r"C:\System_Trading\STOM\STOM_V.wt-dev\_database\strategy.db"
SEED_BUY = "Min_B_Study_251227"
SEED_SELL = "Min_S_Study_251227"


def _copy_seed_to_loop_db(name: str, table: str) -> bool:
    """_database/strategy.db의 시드 1개를 loop_strategies.db로 복사(있으면 갱신)."""
    loop_db = str(bootstrap.LOOP_DB_STRATEGY)
    src = sqlite3.connect(f"file:{SRC_DB}?mode=ro", uri=True)
    try:
        scur = src.cursor()
        cols = [r[1] for r in scur.execute(f"PRAGMA table_info({table})")]
        row = scur.execute(
            f'SELECT * FROM {table} WHERE "{cols[0]}"=?', (name,)
        ).fetchone()
    finally:
        src.close()
    if row is None:
        print(f"[R0] 소스에 시드 없음: {table}.{name}", flush=True)
        return False
    dst = sqlite3.connect(loop_db)
    try:
        dcur = dst.cursor()
        dcols = [r[1] for r in dcur.execute(f"PRAGMA table_info({table})")]
        dcur.execute(f'DELETE FROM {table} WHERE "{dcols[0]}"=?', (name,))
        # 소스/타겟 컬럼 교집합만 안전 복사(스키마 차이 방어).
        common = [c for c in cols if c in dcols]
        vals = [row[cols.index(c)] for c in common]
        ph = ",".join("?" * len(common))
        collist = ",".join(f'"{c}"' for c in common)
        dcur.execute(f"INSERT INTO {table} ({collist}) VALUES ({ph})", vals)
        dst.commit()
    finally:
        dst.close()
    print(f"[R0] 시드 복사 완료: {table}.{name} → {loop_db}", flush=True)
    return True


def main() -> int:
    print("[R0] === 다중포지션 창발 PoC (N=8 small_universe) ===", flush=True)
    ok_b = _copy_seed_to_loop_db(SEED_BUY, "stockbuy")
    ok_s = _copy_seed_to_loop_db(SEED_SELL, "stocksell")
    if not (ok_b and ok_s):
        print("[R0] 시드 준비 실패 → 중단", flush=True)
        return 1

    config = LoopConfig(
        bt_scope="small_universe",
        bt_subset_db=None,          # None → state/min_subset.db (방금 빌드한 N=8)
        bt_timeframe="min",
        bt_engine_count=4,
        bt_window_days_universe=20,
        bt_timeout=300,
        bt_betting="5",
    )
    print(f"[R0] scope={config.bt_scope} engines={config.bt_engine_count} "
          f"window_days={config.bt_window_days_universe} timeout={config.bt_timeout}", flush=True)

    outcome = run_backtest_for(config, SEED_BUY, SEED_SELL)
    print(f"[R0] backtest ok={outcome.ok} status={outcome.status} "
          f"reason={outcome.reason}", flush=True)
    m = outcome.metrics or {}
    mhct = m.get("max_hold_count", 0)
    print("[R0] --- 메트릭 ---", flush=True)
    for k in ("trade_count", "daily_avg_trades", "max_hold_count",
              "total_profit_pct", "mdd_pct", "tpi", "day_count"):
        print(f"[R0]   {k} = {m.get(k)}", flush=True)
    print("", flush=True)
    if mhct and mhct > 1:
        print(f"[R0] ✅ PASS — 최대보유종목수(mhct)={mhct} > 1 : "
              f"다중포지션이 엔진 무수정으로 창발함 (합의 가설 입증).", flush=True)
        return 0
    print(f"[R0] ⚠️ mhct={mhct} (>1 아님) — 시간겹침 부족 가능. "
          f"거래 빈번 종목/윈도우 조정 검토.", flush=True)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
