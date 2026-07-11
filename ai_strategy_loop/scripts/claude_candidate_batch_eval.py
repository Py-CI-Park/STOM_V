"""Claude 생성 후보 일괄 평가 (연구 전용 헤드리스 도구, LLM 호출 0회).

WarmBacktestSession을 1회 prepare한 뒤 (buy, sell) 쌍 N개를 순차 run하고,
공식 루프와 동일한 `_score_outcome`/`record_generation`으로 loop_runs.db에
기록한다(대시보드·선택기 호환). 엔진·하드게이트·backtest/graph는 무수정이며
기존 모듈(공식 헬퍼)만 재사용한다.

사용:
  PYTHONUTF8=1 python -m ai_strategy_loop.scripts.claude_candidate_batch_eval \
      --pairs-json <pairs.json> --config-json <loopconfig.json> --run-id <run_id>

pairs.json 형식: [{"label": "...", "buy": "<전략명>", "sell": "<전략명>"}, ...]
(전략명은 loop_strategies.db stockbuy/stocksell의 index)
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import ai_strategy_loop.bootstrap as bootstrap
from ai_strategy_loop.launch_config import config_from_dict
from ai_strategy_loop.controller.loop import (
    _build_warm_btconfig,
    _warm_to_outcome,
    _score_outcome,
)
from ai_strategy_loop.controller.phase_contract import (
    EXECUTION_KIND_FIXED_BATCH,
    canonical_phase_owner_ok,
)
from ai_strategy_loop.controller.state import LoopState, publish_batch_state
from cli.warm_session import WarmBacktestSession


def _load_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _failed_generation_payload(label: str, outcome) -> dict[str, Any]:
    if outcome.status == "no_trades":
        return {
            "status": "no_trades",
            "score": 0.0,
            "gate_passed": False,
            "reason": f"[{label}] {outcome.reason}",
            "csv_path": outcome.csv_path,
            "trade_count": 0,
            "daily_avg_trades": 0.0,
            "mdd": 0.0,
            "profit": 0.0,
            "strategy_gist": label,
        }
    return {
        "status": "error",
        "score": 0.0,
        "gate_passed": False,
        "reason": f"[{label}] backtest failed: {outcome.reason}",
        "csv_path": outcome.csv_path,
        "strategy_gist": label,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs-json", required=True)
    ap.add_argument("--config-json", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument(
        "--fail-fast-timeout",
        action="store_true",
        help="timeout 발생 시 warm 엔진 복구/재로딩을 생략하고 error row 기록 후 배치를 중단",
    )
    args = ap.parse_args()

    pairs = _load_json(args.pairs_json)
    config = config_from_dict(_load_json(args.config_json))

    bootstrap.ensure_loop_db_engine_compat()
    st = LoopState()
    rid = st.start_run(config, run_id=args.run_id)
    print(f"[BATCH] run_id={rid} pairs={len(pairs)}", flush=True)
    # CL-R04 todo10 — fixed_batch는 canonical passport lineage를 절대 진전시키지
    #   않는다(EvidenceStore.append_passport/append_manifest를 이 스크립트가
    #   호출하지 않는다). canonical_phase_owner_ok(fixed_batch)==False로 그
    #   보장을 명시적으로 고정한다(회귀 시 즉시 AssertionError).
    assert not canonical_phase_owner_ok(EXECUTION_KIND_FIXED_BATCH), (
        "claude_candidate_batch_eval is execution_kind=fixed_batch and must "
        "never be treated as a canonical phase owner"
    )

    sess = WarmBacktestSession(_build_warm_btconfig(config))
    t0 = time.time()
    prep = sess.prepare()
    print(f"[BATCH] prepare status={prep.get('status')} "
          f"back_count={prep.get('back_count')} elapsed={time.time()-t0:.0f}s", flush=True)
    if prep.get("status") != "ok":
        st.finish_run(rid, status="error")
        print(f"[BATCH] prepare failed: {prep.get('message')}", flush=True)
        return 2

    try:
        for i, pair in enumerate(pairs):
            label = pair.get("label", f"pair{i}")
            buy, sell = pair["buy"], pair["sell"]
            # E3(2026-06-11) — 배치도 라이브 상태 발행(대시보드 상단 표시, 실패 흡수).
            publish_batch_state(rid, i, len(pairs), label=label,
                                message=f"배치 {i + 1}/{len(pairs)} 평가 중: {label}",
                                engine={"back_count": prep.get("back_count")})
            t1 = time.time()
            try:
                outcome = _warm_to_outcome(
                    sess.run(
                        buy,
                        sell,
                        timeout=config.bt_warm_run_timeout,
                        recover_on_timeout=not args.fail_fast_timeout,
                    )
                )
            except Exception as exc:  # noqa: BLE001 - 한 후보 실패가 배치를 못 막게.
                from ai_strategy_loop.controller.loop import BacktestOutcome
                outcome = BacktestOutcome(False, "error", None, None, f"run raised: {exc}")
            elapsed = time.time() - t1

            if not outcome.ok:
                st.record_generation(
                    rid, i, buy_name=buy, sell_name=sell,
                    **_failed_generation_payload(label, outcome),
                )
                level = "NO_TRADES" if outcome.status == "no_trades" else "ERROR"
                print(f"[BATCH] gen{i} {label} {level} ({elapsed:.0f}s) {outcome.reason}",
                      flush=True)
                if args.fail_fast_timeout and outcome.status == "error" and "시간 초과" in outcome.reason:
                    print(f"[BATCH] abort after timeout: {label}", flush=True)
                    break
                continue

            fit, graded, fit_err = _score_outcome(outcome, config)
            if fit is None:
                st.record_generation(
                    rid, i, buy_name=buy, sell_name=sell,
                    status="error", score=0.0, gate_passed=False,
                    reason=f"[{label}] fitness failed: {fit_err}",
                    csv_path=outcome.csv_path,
                )
                print(f"[BATCH] gen{i} {label} FITNESS-ERROR {fit_err}", flush=True)
                continue

            total_profit_pct = float(
                (outcome.metrics or {}).get("total_profit_pct", 0.0) or 0.0
            )
            # reason은 fit.reason 원문 그대로 저장한다 — sparse_positive_v1 선택기의
            #   버킷 판정이 gate_reason fullmatch 정규식이라 접두사를 붙이면 깨진다.
            #   후보 라벨은 strategy_gist에만 둔다.
            st.record_generation(
                rid, i, buy_name=buy, sell_name=sell,
                status="ok", score=graded.graded, calmar=fit.calmar,
                uptrend_r2=fit.uptrend_r2, gate_passed=fit.gate_passed,
                reason=fit.reason, csv_path=outcome.csv_path,
                trade_count=fit.trade_count,
                daily_avg_trades=fit.daily_avg_trades,
                mdd=graded.mdd, profit=graded.total_profit,
                total_profit_pct=total_profit_pct,
                strategy_gist=label,
                payoff_ratio=graded.payoff_ratio,
                give_back_rate=graded.give_back_rate,
            )
            print(
                f"[BATCH] gen{i} {label} ok profit={graded.total_profit:,.0f} "
                f"mdd={graded.mdd:.2f} trades={fit.trade_count} "
                f"daily={fit.daily_avg_trades:.2f} payoff={graded.payoff_ratio} "
                f"gate={fit.gate_passed} reason={fit.reason} ({elapsed:.0f}s)",
                flush=True,
            )
    finally:
        sess.close()

    st.finish_run(rid, status="complete")
    # G-1 보완(2026-06-11) — 종료 발행 누락이 라이브 영역 'gen N 박제'를 만들었다
    #   (스윕에는 있던 idle 발행이 배치에 없었음 — 23:28 실사고).
    publish_batch_state(rid, len(pairs), len(pairs), status="idle",
                        message=f"배치 완료: {rid}")
    print("[BATCH] done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
