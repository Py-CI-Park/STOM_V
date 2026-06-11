"""TMAP G2 — 지형 스윕 러너 (대량 백테스트, LLM 호출 0회).

템플릿의 좌표 스윕 포인트(기본값 1점 + 슬롯별 후보값)를 렌더→가드 검증→주입한 뒤
WarmBacktestSession **prepare 1회 + run N회**로 평가하고 loop_runs.db에 기록한다
(strategy_gist='TMAP {param}={value}' — tendency 분석기·대시보드 /tmap_map 호환).

사용:
  PYTHONUTF8=1 python -m ai_strategy_loop.scripts.tmap_sweep \
      --template seed_902905 --config-json <loopconfig.json> --run-id <run_id> \
      [--params cap_max,window_end] [--max-points 60] [--manifest-out <path.json>]

완료 후 경향성 요약(고원/절벽)을 stdout에 출력한다. 분석/연구 전용 —
엔진·하드게이트·선택 규율 무수정(기존 공식 헬퍼만 재사용).
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import ai_strategy_loop.bootstrap as bootstrap
from ai_strategy_loop.launch_config import config_from_dict
from ai_strategy_loop.controller.loop import (
    _build_warm_btconfig,
    _warm_to_outcome,
    _score_outcome,
)
from ai_strategy_loop.controller.state import LoopState
from ai_strategy_loop.tmap.template import (
    coordinate_points,
    load_template,
    render,
    strategy_names,
    validate_rendered,
)
from cli.strategy_generator import save_strategy_to_db
from cli.warm_session import WarmBacktestSession


def _load_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--config-json", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--params", default="", help="스윕할 슬롯 부분집합(쉼표). 비우면 전체")
    ap.add_argument("--max-points", type=int, default=200)
    ap.add_argument("--manifest-out", default="")
    args = ap.parse_args()

    template = load_template(args.template)
    params = [p.strip() for p in args.params.split(",") if p.strip()] or None
    points = coordinate_points(template, params=params)[: args.max_points]

    config = config_from_dict(_load_json(args.config_json))
    bootstrap.ensure_loop_db_engine_compat()
    db = str(bootstrap.LOOP_DB_STRATEGY)

    # 1) 렌더→가드→주입 (실패 포인트는 스윕에서 제외하고 기록만 남긴다).
    prepared = []
    for i, point in enumerate(points):
        buy_code, sell_code = render(template, point["theta"])
        errors = validate_rendered(buy_code, sell_code, template.timeframe)
        if errors:
            print(f"[SWEEP] skip {point['label']}: {errors}", flush=True)
            continue
        buy_name, sell_name = strategy_names(template, i)
        r1 = save_strategy_to_db(db, buy_name, buy_code, "buy")
        r2 = save_strategy_to_db(db, sell_name, sell_code, "sell")
        if r1.get("status") != "ok" or r2.get("status") != "ok":
            print(f"[SWEEP] save 실패 {point['label']}: {r1} {r2}", flush=True)
            continue
        prepared.append((point, buy_name, sell_name))
    print(f"[SWEEP] template={template.name} points={len(prepared)}/{len(points)}", flush=True)

    st = LoopState()
    rid = st.start_run(config, run_id=args.run_id)
    sess = WarmBacktestSession(_build_warm_btconfig(config))
    t0 = time.time()
    prep = sess.prepare()
    print(f"[SWEEP] prepare status={prep.get('status')} "
          f"back_count={prep.get('back_count')} elapsed={time.time()-t0:.0f}s", flush=True)
    if prep.get("status") != "ok":
        st.finish_run(rid, status="error")
        return 2

    manifest = {"template": template.name, "run_id": rid, "points": []}
    try:
        for gen_no, (point, buy_name, sell_name) in enumerate(prepared):
            t1 = time.time()
            try:
                outcome = _warm_to_outcome(
                    sess.run(buy_name, sell_name, timeout=config.bt_warm_run_timeout)
                )
            except Exception as exc:  # noqa: BLE001 - 한 점 실패가 스윕을 못 막게.
                from ai_strategy_loop.controller.loop import BacktestOutcome
                outcome = BacktestOutcome(False, "error", None, None, f"run raised: {exc}")
            elapsed = time.time() - t1
            entry = {"gen_no": gen_no, **{k: point[k] for k in ("label", "param", "value")},
                     "buy_name": buy_name}

            if not outcome.ok:
                st.record_generation(
                    rid, gen_no, buy_name=buy_name, sell_name=sell_name,
                    status="error", score=0.0, gate_passed=False,
                    reason=f"backtest failed: {outcome.reason}",
                    csv_path=outcome.csv_path, strategy_gist=point["label"],
                )
                print(f"[SWEEP] gen{gen_no} {point['label']} ERROR ({elapsed:.0f}s)", flush=True)
                entry["status"] = "error"
                manifest["points"].append(entry)
                continue

            fit, graded, fit_err = _score_outcome(outcome, config)
            if fit is None:
                st.record_generation(
                    rid, gen_no, buy_name=buy_name, sell_name=sell_name,
                    status="error", score=0.0, gate_passed=False,
                    reason=f"fitness failed: {fit_err}",
                    csv_path=outcome.csv_path, strategy_gist=point["label"],
                )
                entry["status"] = "fitness_error"
                manifest["points"].append(entry)
                continue

            total_profit_pct = float((outcome.metrics or {}).get("total_profit_pct", 0.0) or 0.0)
            # reason은 fit.reason 원문(기록 계약 — test_record_reason_contract).
            st.record_generation(
                rid, gen_no, buy_name=buy_name, sell_name=sell_name,
                status="ok", score=graded.graded, calmar=fit.calmar,
                uptrend_r2=fit.uptrend_r2, gate_passed=fit.gate_passed,
                reason=fit.reason, csv_path=outcome.csv_path,
                trade_count=fit.trade_count, daily_avg_trades=fit.daily_avg_trades,
                mdd=graded.mdd, profit=graded.total_profit,
                total_profit_pct=total_profit_pct, strategy_gist=point["label"],
                payoff_ratio=graded.payoff_ratio, give_back_rate=graded.give_back_rate,
            )
            print(f"[SWEEP] gen{gen_no} {point['label']} profit={graded.total_profit:,.0f} "
                  f"mdd={graded.mdd:.2f} trades={fit.trade_count} ({elapsed:.0f}s)", flush=True)
            entry.update({"status": "ok", "profit": graded.total_profit,
                          "mdd": graded.mdd, "trades": fit.trade_count})
            manifest["points"].append(entry)
    finally:
        sess.close()

    st.finish_run(rid, status="complete")
    if args.manifest_out:
        Path(args.manifest_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.manifest_out).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # 경향성 요약 즉시 출력(advisory).
    from ai_strategy_loop.tmap.tendency import summarize_tendency
    summary = summarize_tendency(rid)
    base = summary.get("baseline") or {}
    print(f"[SWEEP] baseline profit={base.get('profit', 0):,.0f} mdd={base.get('mdd')}", flush=True)
    ranked = sorted(summary.get("params", {}).items(),
                    key=lambda kv: -(kv[1].get("plateau_score") or 0))
    for name, m in ranked:
        plateau = m.get("plateau") or {}
        print(f"[SWEEP] {name}: plateau_score={m.get('plateau_score')} "
              f"center={plateau.get('center_value')} width={plateau.get('width')} "
              f"positive={m.get('positive_ratio')}", flush=True)
    print("[SWEEP] done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
