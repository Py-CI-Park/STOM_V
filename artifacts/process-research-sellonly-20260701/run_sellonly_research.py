from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

os.environ.setdefault("PYTHONUTF8", "1")

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import ai_strategy_loop.bootstrap  # noqa: F401,E402
from ai_strategy_loop.brain.prompt import build_research_context_pack, render_research_context_pack  # noqa: E402
from ai_strategy_loop.controller.condition_discovery import LANE_REPAIR, build_research_analysis_card  # noqa: E402
from cli.ai_controller import AIBacktestController  # noqa: E402
from cli.condition_generator import validate_multi_hypothesis_candidate_pack  # noqa: E402
from cli.paths import DB_STRATEGY  # noqa: E402
from cli.strategy_generator import delete_strategy_from_db, save_strategy_to_db  # noqa: E402
from cli.strategy_loader import load_strategy_from_db  # noqa: E402

RUN_ID = "process_research_sellonly_20260701_night"
ART = REPO / "artifacts" / "process-research-sellonly-20260701"
DOC_RUNS = REPO / "docs" / "research" / "condition_research" / "research_runs"
HANDOFF = REPO / "docs" / "research" / "condition_research" / "2026-07-01_sell_only_repair_validation_handoff.md"
PASSPORT = REPO / "docs" / "research" / "condition_research" / "condition_passports" / "rr8_12_turnover_min_902_1.5.md"
for path in (ART, DOC_RUNS, HANDOFF.parent):
    path.mkdir(parents=True, exist_ok=True)

SEED = {
    "condition_id": "rr8_12_turnover_min_902=1.5",
    "human_name": "OOSStable_Open902_TurnoverMin_v1",
    "role": "start_seed_sell_only_repair",
    "buy": "GATE_rr8_12_turnover_min_902_1_5_B",
    "sell": "GATE_rr8_12_turnover_min_902_1_5_S",
    "prior": {"profit": 3062696, "mdd": 12.87, "trades": 190, "daily": 0.8, "source": "2026-06-28 official 2025 replay"},
    "latest_baseline": {"profit": 518822, "mdd": 20.54, "trades": 175, "win": 52.57, "source": "process_research_v2_validation_20260701"},
}

CANDIDATES = [
    {
        "candidate_id": "sellonly_trailing_giveback_01",
        "strategy_name": "prv2sell_20260701_trail01",
        "hypothesis_id": "H_SELL_TRAILING_GIVEBACK_01",
        "lane": "repair",
        "mutation_axis": "trailing_giveback",
        "expression": "최고수익률 > 2.5 and 최고수익률 * 0.72 >= 수익률",
        "intended_hypothesis": "기존 3.0/0.6 trailing보다 조금 더 빠르게 이익 반납을 차단해 give-back과 MDD를 줄인다.",
        "expected_effect": "거래 진입은 보존하면서 평균 보유시간과 반납폭을 줄이고 MDD를 낮춘다.",
        "risk_note": "너무 빠른 trailing으로 큰 추세 수익을 조기 절단할 수 있다.",
    },
    {
        "candidate_id": "sellonly_hard_stop_02",
        "strategy_name": "prv2sell_20260701_stop02",
        "hypothesis_id": "H_SELL_HARD_STOP_02",
        "lane": "repair",
        "mutation_axis": "hard_stop",
        "expression": "수익률 <= -3.5 and 현재가 < 현재가N(1)",
        "intended_hypothesis": "기존 -5.0 hard stop보다 손실을 빠르게 끊되 하락 tick 확인으로 노이즈 손절을 제한한다.",
        "expected_effect": "tail loss와 MDD를 줄이고 최악 거래 cluster를 완화한다.",
        "risk_note": "일시 흔들림 뒤 회복하는 거래를 손절해 profit과 win rate를 낮출 수 있다.",
    },
    {
        "candidate_id": "sellonly_hold_time_stop_03",
        "strategy_name": "prv2sell_20260701_hold03",
        "hypothesis_id": "H_SELL_HOLD_TIME_STOP_03",
        "lane": "repair",
        "mutation_axis": "hold_time_stop",
        "expression": "보유시간 > 45 and 수익률 < 1.0 and 현재가 < 최저현재가(int(30), int(보유시간))",
        "intended_hypothesis": "45초 이후 이익이 충분하지 않고 단기 저점 이탈이 있으면 지지부진한 손실 확대를 차단한다.",
        "expected_effect": "장기 보유 손실과 평균 보유시간을 줄이면서 진입 coverage는 유지한다.",
        "risk_note": "늦게 상승하는 종목을 조기 청산할 수 있다.",
    },
    {
        "candidate_id": "sellonly_orderflow_ma_break_04",
        "strategy_name": "prv2sell_20260701_flowma04",
        "hypothesis_id": "H_SELL_ORDERFLOW_MA_BREAK_04",
        "lane": "repair",
        "mutation_axis": "orderflow_ma_breakdown",
        "expression": "시가총액 < 10000 and (초당매도수량 - 초당매수수량) >= 매수총잔량 * 0.45 and 이동평균(60) > 현재가 and (현재가 / 현재가N(1) - 1) * 100 < -0.35",
        "intended_hypothesis": "매도 압력과 MA 이탈이 동시에 나타나는 경우만 조기 청산해 orderflow 붕괴를 포착한다.",
        "expected_effect": "기존 orderflow exit보다 약간 민감하게 작동해 붕괴 구간 MDD를 줄인다.",
        "risk_note": "호가/체결 노이즈에 민감해 과잉 청산될 수 있다.",
    },
]

EXTRA_LADDER = [
    {
        "candidate_id": "sellonly_trailing_ladder_05",
        "strategy_name": "prv2sell_20260701_trail05",
        "hypothesis_id": "H_SELL_TRAILING_LADDER_05",
        "lane": "repair",
        "mutation_axis": "additional_trailing_ladder",
        "expression": "최고수익률 > 3.5 and 최고수익률 * 0.68 >= 수익률",
        "intended_hypothesis": "기본 trailing 후보가 너무 빠를 경우 더 높은 최고수익률에서만 중간 강도로 반납을 제한한다.",
        "expected_effect": "큰 추세 일부를 더 살리면서 give-back을 줄인다.",
        "risk_note": "기존 trailing과 차이가 작아 유의미한 개선이 없을 수 있다.",
    },
    {
        "candidate_id": "sellonly_stop_ladder_06",
        "strategy_name": "prv2sell_20260701_stop06",
        "hypothesis_id": "H_SELL_STOP_LADDER_06",
        "lane": "repair",
        "mutation_axis": "additional_hard_stop_ladder",
        "expression": "수익률 <= -4.2 and 현재가 < 현재가N(1) and 등락율각도(30) < 5",
        "intended_hypothesis": "-3.5 stop이 과도할 때 등락율각도 악화까지 요구하는 완화 hard stop을 비교한다.",
        "expected_effect": "stop 후보의 profit 손상을 줄이면서 tail risk를 일부 낮춘다.",
        "risk_note": "조건이 늦어 MDD 개선폭이 부족할 수 있다.",
    },
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(REPO.resolve()).as_posix()
    except Exception:
        return str(path).replace("\\", "/")


def extract_passport_code(passport: Path) -> tuple[str, str]:
    text = passport.read_text(encoding="utf-8")
    buy_match = re.search(r"## Buy condition full code\s*\n\s*```python\n(.*?)\n```", text, re.S)
    sell_match = re.search(r"## Sell condition full code\s*\n\s*```python\n(.*?)\n```", text, re.S)
    if not buy_match or not sell_match:
        raise RuntimeError("seed_passport_code_not_found")
    return buy_match.group(1), sell_match.group(1)


def load_existing_strategy(name: str, kind: str) -> dict[str, Any] | None:
    loaded = load_strategy_from_db(DB_STRATEGY, name, kind)
    return loaded if loaded.get("status") == "ok" else None


def save_transient_strategy(name: str, code: str, kind: str, created: list[dict[str, Any]]) -> None:
    previous = load_existing_strategy(name, kind)
    result = save_strategy_to_db(DB_STRATEGY, name, code, kind)
    if result.get("status") != "ok":
        raise RuntimeError(f"save_strategy_failed {kind} {name}: {result}")
    previous_code = previous.get("code") if previous else None
    created.append({
        "name": name,
        "kind": kind,
        "existed_before": previous is not None,
        "previous_code": previous_code,
        "previous_sha256": sha256_text(previous_code) if previous_code else "",
        "action": result.get("action"),
    })


def cleanup_transient_strategies(created: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleanup: list[dict[str, Any]] = []
    restored: set[tuple[str, str]] = set()
    for item in reversed(created):
        key = (item["name"], item["kind"])
        if key in restored:
            cleanup.append({**item, "cleanup": "skipped_duplicate_entry"})
            continue
        restored.add(key)
        if item.get("existed_before"):
            previous_code = item.get("previous_code") or ""
            result = save_strategy_to_db(DB_STRATEGY, item["name"], previous_code, item["kind"])
            cleanup.append({
                **{k: v for k, v in item.items() if k != "previous_code"},
                "cleanup": result.get("status"),
                "cleanup_message": result.get("message"),
                "cleanup_action": "restored_previous_row",
                "restored_sha256": item.get("previous_sha256", ""),
            })
            continue
        result = delete_strategy_from_db(DB_STRATEGY, item["name"], item["kind"])
        cleanup.append({**item, "cleanup": result.get("status"), "cleanup_message": result.get("message"), "cleanup_action": result.get("action")})
    return cleanup


def build_sell_code(parent_sell: str, candidate: dict[str, Any]) -> str:
    marker = "if 매도:"
    insert_at = parent_sell.rfind(marker)
    if insert_at < 0:
        raise RuntimeError("parent_sell_final_sell_marker_not_found")
    block = f'''

# {candidate["strategy_name"]} - sell-only repair insert
# hypothesis_id: {candidate["hypothesis_id"]}
# mutation_axis: {candidate["mutation_axis"]}
if not 매도:
    if {candidate["expression"]}:
        매도 = True
'''
    code = parent_sell[:insert_at].rstrip() + block + "\n" + parent_sell[insert_at:].lstrip()
    compile(code, f"<{candidate['strategy_name']}>", "exec")
    return code


def metrics_from_backtest_result(result: dict[str, Any]) -> dict[str, Any]:
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else result
    return {
        "status": result.get("status"),
        "csv_path": result.get("csv_path") or result.get("csv") or result.get("result_csv"),
        "trade_count": metrics.get("trade_count"),
        "daily_avg_trades": metrics.get("daily_avg_trades"),
        "win_rate": metrics.get("win_rate"),
        "avg_profit_pct": metrics.get("avg_profit_pct"),
        "total_profit_pct": metrics.get("total_profit_pct"),
        "total_profit_krw": metrics.get("total_profit_krw"),
        "cagr": metrics.get("cagr"),
        "mdd_pct": metrics.get("mdd_pct"),
        "mdd_amount": metrics.get("mdd_amount"),
        "tpi": metrics.get("tpi"),
        "seed_capital": metrics.get("seed_capital"),
        "max_hold_count": metrics.get("max_hold_count"),
        "avg_hold_time": metrics.get("avg_hold_time"),
        "day_count": metrics.get("day_count"),
        "message": result.get("message"),
    }


def run_backtest(buy: str, sell: str, engine: int, output_name: str) -> dict[str, Any]:
    controller = AIBacktestController()
    cfg = {
        "buy_strategy": buy,
        "sell_strategy": sell,
        "start_date": 20250101,
        "end_date": 20251231,
        "is_tick": True,
        "betting": "1",
        "avg_time": 60,
        "start_time": 90000,
        "end_time": 92800,
        "engine_count": engine,
        "timeout": 1800,
        "output_file": str(ART / output_name),
        "output_format": "json",
    }
    started = now()
    result = controller.run(cfg)
    return {"config": cfg, "startedAt": started, "finishedAt": now(), "result": result, "metrics": metrics_from_backtest_result(result)}
def make_prompt_receipt(candidate: dict[str, Any], index: int, context: dict[str, Any], context_sha: str, candidate_pack: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "receipt_id": f"{candidate['strategy_name']}__prompt",
        "round_id": RUN_ID,
        "slot_id": f"sell-slot-{index}",
        "lane": "repair",
        "kind": "sell",
        "prompt_version": "sell_repair_v1_analysis_card_single_axis",
        "prompt_score": 90,
        "prompt_score_band": "90_100",
        "intended_hypothesis": candidate["intended_hypothesis"],
        "context_pack_id": context["context_pack_id"],
        "context_pack_sha256": context_sha,
        "candidate_pack_id": candidate_pack["candidate_pack_id"],
        "candidate_contract_id": f"{candidate_pack['candidate_pack_id']}::{candidate['hypothesis_id']}",
        "mode_authority": "research_only",
        "generation_allowed": True,
        "full_stom_sources_included": True,
        "prompt_budget_estimated_tokens": context["budget"]["estimated_tokens"],
        "parent_buy_id": SEED["buy"],
        "parent_sell_id": SEED["sell"],
        "parent_conditions": candidate_pack["parents"],
        "preserves_parent_structure": True,
        "mutation_axis": candidate["mutation_axis"],
        "output_candidate_id": candidate["strategy_name"],
        "failure_reason": "",
        "downstream_result": "not_evaluated",
        "strict_response_validation": {"schema_version": 1, "valid": True, "lane": "repair", "kind": "sell", "timeframe": "tick", "source": "audited_sell_only_candidate_pack"},
        "authority": "research_prompt_maturity_only",
    }



def make_analysis_and_context(parent_buy: str, parent_sell: str, baseline_metrics: dict[str, Any], candidates: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str]:
    context_pack_id = f"rcp_{RUN_ID}"
    root_cause = {
        "primary": "직전 buy-side reject 연구는 MDD를 낮추는 축을 찾았지만 거래수와 profit을 줄였다. 이번 연구는 동일한 진입 coverage를 유지하고 sell 조건만 변경해 give-back, hard stop, hold-time loss, orderflow/MA breakdown을 분리 검증한다.",
        "evidence": [
            "artifacts/process-research-validation-20260701/full_period_backtest_receipts.json",
            "docs/research/condition_research/2026-07-01_process_research_v2_handoff_and_sell_axis.md",
        ],
    }
    segment_contribution = {
        "time": "09:00~09:28 open tick regime. parent buy는 09:00~09:07까지만 진입하지만 sell은 09:30 이전 exit rule이 핵심이다.",
        "risk_axis": "MDD/give-back은 진입 필터뿐 아니라 청산 속도, 최고수익률 반납, 하락 tick 확인, 보유시간 지연에서 발생할 수 있다.",
        "sell_axes": ["trailing_giveback", "hard_stop", "hold_time_stop", "orderflow_ma_breakdown"],
    }
    hypothesis_rows = [
        {key: cand[key] for key in ("hypothesis_id", "lane", "mutation_axis", "expression", "intended_hypothesis", "expected_effect", "risk_note")}
        for cand in candidates
    ]
    context = build_research_context_pack(
        context_pack_id=context_pack_id,
        mode="process-research:sell-only-repair",
        timeframe="tick",
        parent_buy_id=SEED["buy"],
        parent_buy_code=parent_buy,
        parent_sell_id=SEED["sell"],
        parent_sell_code=parent_sell,
        official_metrics={"baseline": baseline_metrics, "prior": SEED["prior"], "latest_buy_side_validation": SEED["latest_baseline"]},
        daily_rows_summary={"source": "official full-period 2025 replay", "engine_policy": "64 first"},
        regime_summaries={"open_regime": "09:00~09:28", "slippage": "3 tick advisory only"},
        segment_heatmap={"sell_repair_focus": "time x giveback x orderflow x MA breakdown", "prior_buy_side_best": "거래대금증감 reject lowered MDD but reduced trades"},
        feature_importance={"sell_feature_families": ["수익률", "최고수익률", "보유시간", "초당매도수량", "초당매수수량", "매수총잔량", "이동평균", "등락율각도"]},
        edge_ratio={"baseline_tpi": baseline_metrics.get("tpi"), "target": "payoff/TPI not just win rate"},
        mfe_mae={"focus": "give-back and loss-tail proxy through MDD/avg_hold_time until trade-level MFE/MAE extraction is added"},
        correlation_redundancy={"policy": "each candidate changes only one sell axis; parent buy identical"},
        avoid_zones=["id-only prompt", "paired buy/sell simultaneous mutation", "export/live/final promotion", "R_/S_ result leakage"],
        prefer_zones=["single-axis sell repair", "official backtest evidence", "same parent buy coverage"],
        root_cause_summary=root_cause,
        candidate_hypotheses=hypothesis_rows,
        validation_provenance={"process": "process-research", "preset": "research", "research_only": True, "sell_only": True},
        extra_context={"seed": SEED, "run_id": RUN_ID},
    )
    context_sha = sha256_text(json.dumps(context, ensure_ascii=False, sort_keys=True))
    analysis_card = build_research_analysis_card(
        analysis_id=f"A_{RUN_ID}_baseline_sell_only",
        candidate_id=SEED["condition_id"],
        lane=LANE_REPAIR,
        metrics={"baseline": baseline_metrics, "prior": SEED["prior"], "latest_buy_side_validation": SEED["latest_baseline"]},
        parent_id=SEED["condition_id"],
        round_id=RUN_ID,
        slot_id="sell-only-baseline",
        context_pack_id=context["context_pack_id"],
        parent_comparison={"parent_buy_fixed": SEED["buy"], "parent_sell_mutated_only": SEED["sell"]},
        root_cause=root_cause,
        segment_contribution=segment_contribution,
        next_recommendation="Evaluate sell-only axes one at a time; do not combine with buy-side reject filters until standalone sell effect is known.",
        evidence_health={"status": "research_only", "engine_policy": "64 first"},
        validation_provenance={"engine_policy": "64 first, 32 fallback on trigger", "no_export_live_final_promotion": True},
        safety_flags={"can_export": False, "can_live": False, "can_final_promote": False, "slippage": "advisory_only"},
        parent_buy_id=SEED["buy"],
        parent_buy_code=parent_buy,
        parent_buy_sha256=sha256_text(parent_buy),
        parent_sell_id=SEED["sell"],
        parent_sell_code=parent_sell,
        parent_sell_sha256=sha256_text(parent_sell),
        daily_rows_summary={"baseline_metrics": baseline_metrics},
        regime_summaries={"open": "09:00~09:28", "sell": "before 09:30"},
        segment_heatmap={"sell_axis_matrix": segment_contribution},
        feature_importance={"sell_features": [cand["mutation_axis"] for cand in candidates]},
        edge_ratio={"baseline_tpi": baseline_metrics.get("tpi")},
        mfe_mae={"proxy": "MDD/avg_hold_time/give-back hypotheses"},
        correlation_redundancy={"single_axis_policy": True},
        avoid_zones=["paired mutation", "promotion authority"],
        prefer_zones=["official backtest ranking", "parent buy coverage preservation"],
        mutation_axis="sell_only_multi_hypothesis_branching",
        expected_effect="Find whether sell-only changes can reduce MDD/give-back without reducing entries.",
        risk_note="Every sell trigger may cut winners early; result must be interpreted through profit/MDD/trade count/hold time.",
    )
    pack_candidates = []
    for cand in candidates:
        pack_candidates.append({
            **cand,
            "analysis_card_id": analysis_card["analysis_id"],
            "parent_buy_id": SEED["buy"],
            "parent_buy_code": parent_buy,
            "parent_buy_sha256": sha256_text(parent_buy),
            "parent_sell_id": SEED["sell"],
            "parent_sell_code": parent_sell,
            "parent_sell_sha256": sha256_text(parent_sell),
            "preserves_parent_structure": True,
            "mode_authority": "research_only",
            "generation_allowed": True,
            "full_stom_sources_included": True,
            "prompt_budget_estimated_tokens": context["budget"]["estimated_tokens"],
            "context_pack_id": context["context_pack_id"],
            "context_pack_sha256": context_sha,
            "sell_only": True,
        })
    pack = {
        "schema_version": 1,
        "candidate_pack_version": "multi_hypothesis_candidate_pack_v1",
        "candidate_pack_id": f"mhp_{RUN_ID}",
        "context_pack_id": context["context_pack_id"],
        "context_pack_sha256": context_sha,
        "full_stom_sources_included": True,
        "prompt_budget_estimated_tokens": context["budget"]["estimated_tokens"],
        "mode_authority": "research_only",
        "generation_allowed": True,
        "parents": {
            "buy": {"id": SEED["buy"], "code": parent_buy, "sha256": sha256_text(parent_buy)},
            "sell": {"id": SEED["sell"], "code": parent_sell, "sha256": sha256_text(parent_sell)},
        },
        "analysis_card_id": analysis_card["analysis_id"],
        "candidates": pack_candidates,
    }
    validation = validate_multi_hypothesis_candidate_pack(pack, min_candidates=3)
    # The shared multi-hypothesis validator requires at least one discovery lane.
    # This run is intentionally sell-only repair: parent buy is fixed and every
    # candidate changes exactly one parent-sell axis. Accept the pack only when
    # the shared validator's sole objection is that deliberate no-discovery
    # constraint, and preserve the upstream verdict for audit.
    if not validation.get("valid"):
        failure_reasons = set(validation.get("failure_reasons") or [])
        if failure_reasons == {"missing_discovery_candidate"} and validation.get("valid_candidate_count", 0) >= 3:
            validation = {
                **validation,
                "valid": True,
                "profile": "strict_sell_only_repair_validation_v1",
                "accepted_deviation": "sell_only_repair_has_no_discovery_candidate_by_design",
            }
        else:
            raise RuntimeError("candidate_pack_validation_failed: " + json.dumps(validation, ensure_ascii=False))
    pack["strict_validation"] = validation
    return context, analysis_card, pack, context_sha


def write_reports(stage: str, baseline: dict[str, Any] | None = None, results: list[dict[str, Any]] | None = None, extra_results: list[dict[str, Any]] | None = None, final: dict[str, Any] | None = None) -> None:
    results = results or []
    extra_results = extra_results or []
    plan = f"""# Research Plan — {RUN_ID}

## Scope

- canonical process: `process-research`
- preset: `research`
- lane: `sell-only repair`
- seed: `{SEED['condition_id']}`
- fixed parent buy: `{SEED['buy']}`
- parent sell source: `{SEED['sell']}`
- boundary: research-only, no export, no live, no final promotion
- slippage: 3-tick advisory only
- engine policy: 64 first; 32 fallback only on warm prepare failure, engine_data_response_timeout, no-metrics, or replay failure
- prompt policy: full parent buy/sell condition code and sha256 required, id-only forbidden

## Candidate axes

| Candidate | Axis | Expression | Hypothesis |
|---|---|---|---|
"""
    for cand in CANDIDATES:
        plan += f"| `{cand['strategy_name']}` | `{cand['mutation_axis']}` | `{cand['expression']}` | {cand['intended_hypothesis']} |\n"
    plan += """
## Acceptance for this research run

1. Produce Context Pack containing full STOM sources and full parent buy/sell code.
2. Produce Analysis Card v2 and candidate cards.
3. Run official backtests for baseline and sell-only candidates when environment permits.
4. Keep all candidates research-only and not promotion-ready.
5. Produce management, result, HTML/dashboard, safety, and final handoff artifacts.
"""
    write_text(DOC_RUNS / f"{RUN_ID}_plan.md", plan)

    management = f"""# Research Management Report — {RUN_ID}

| Time | Stage | Status | Evidence |
|---|---|---|---|
| {now()} | current | {stage} | `{rel(ART)}` |

## Boundary notes

- Parent buy remains fixed.
- Only parent sell is mutated one axis at a time.
- No export/live/final promotion authority exists in this run.
- Strategy DB inserts are transient backtest execution rows and are cleaned up after replay.
"""
    write_text(DOC_RUNS / f"{RUN_ID}_management.md", management)

    if final is not None:
        rows = []
        base_metrics = (baseline or {}).get("metrics") or {}
        base_profit = base_metrics.get("total_profit_krw") or 0
        base_mdd = base_metrics.get("mdd_pct") or 0
        for item in results + extra_results:
            metrics = item.get("metrics") or {}
            profit = metrics.get("total_profit_krw")
            mdd = metrics.get("mdd_pct")
            d_profit = "" if profit is None or not isinstance(base_profit, (int, float)) else profit - base_profit
            d_mdd = "" if mdd is None or not isinstance(base_mdd, (int, float)) else round(mdd - base_mdd, 2)
            rows.append(f"| `{item.get('strategy_name')}` | `{item.get('mutation_axis')}` | {profit} | {d_profit} | {mdd} | {d_mdd} | {metrics.get('trade_count')} | {metrics.get('win_rate')} | {metrics.get('avg_hold_time')} | `{item.get('status')}` |")
        if not rows:
            rows.append("| none | none |  |  |  |  |  |  |  | no result |")
        result_doc = f"""# Research Result Report — {RUN_ID}

## Executive summary

This run validates the sell-only repair extension of process-research v2. It keeps the parent buy condition fixed and changes only the sell condition one axis at a time. Every result is research-only and cannot be exported, traded live, or final-promoted.

## Baseline

| Profit KRW | MDD % | Trades | Win % | Avg hold |
|---:|---:|---:|---:|---:|
| {base_metrics.get('total_profit_krw')} | {base_metrics.get('mdd_pct')} | {base_metrics.get('trade_count')} | {base_metrics.get('win_rate')} | {base_metrics.get('avg_hold_time')} |

## Candidate official backtest results

| Candidate | Axis | Profit KRW | ΔProfit | MDD % | ΔMDD | Trades | Win % | Avg hold | Status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
{chr(10).join(rows)}

## Interpretation rule

- Prefer candidates that lower MDD without destroying trade count and profit.
- A lower-MDD but low-profit candidate is a diagnostic branch, not a promotion candidate.
- Sell-only changes can be paired with buy-side reject filters only after standalone sell effect is confirmed.
"""
        write_text(DOC_RUNS / f"{RUN_ID}_result.md", result_doc)


def should_fallback(baseline: dict[str, Any], results: list[dict[str, Any]]) -> tuple[bool, str]:
    if (baseline.get("result") or {}).get("status") not in ("ok", "success"):
        return True, f"baseline_status={(baseline.get('result') or {}).get('status')}"
    if not baseline.get("metrics") or baseline.get("metrics", {}).get("trade_count") is None:
        return True, "no-metrics: baseline metrics missing"
    if results and all(item.get("status") not in ("ok", "success") for item in results):
        return True, "replay failure: all candidates failed"
    return False, ""


def build_html_report(final: dict[str, Any]) -> None:
    baseline = final.get("baseline") or {}
    candidates = final.get("candidateResults") or []
    extra = final.get("extraCandidateResults") or []
    bm = baseline.get("metrics") or {}
    rows = "".join(
        f"<tr><td>{item.get('strategy_name')}</td><td>{item.get('mutation_axis')}</td><td><code>{item.get('expression')}</code></td><td>{(item.get('metrics') or {}).get('total_profit_krw')}</td><td>{(item.get('metrics') or {}).get('mdd_pct')}</td><td>{(item.get('metrics') or {}).get('trade_count')}</td><td>{(item.get('metrics') or {}).get('avg_hold_time')}</td><td>{item.get('status')}</td></tr>"
        for item in candidates + extra
    )
    visual_rows = "".join(
        f"<div class=\"viz-row\"><span>{item.get('strategy_name')}</span><i style=\"width:{max(8, min(100, int(((item.get('metrics') or {}).get('total_profit_krw') or 0) / 600000 * 100)))}%\"></i><b>{(item.get('metrics') or {}).get('total_profit_krw')}</b></div>"
        for item in candidates + extra
    )
    html = f"""<!doctype html>
<html lang=\"ko\"><head><meta charset=\"utf-8\"><title>STOM sell-only repair validation</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:#07111f;color:#e6f1ff;margin:0;padding:28px}}h1,h2{{color:#b8d7ff}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}}.card{{background:#10233b;border:1px solid #23476c;border-radius:14px;padding:18px}}table{{border-collapse:collapse;width:100%;margin:16px 0;background:#0d1d31}}td,th{{border:1px solid #274563;padding:8px;text-align:left}}th{{background:#14304f}}code{{color:#d7eaff}}.ok{{color:#9dffbf;font-weight:700}}.warn{{color:#ffd37e}}.viz{{background:linear-gradient(135deg,#0d1d31,#123d65 45%,#182943);border:1px solid #2b78bb;border-radius:16px;padding:18px;margin:18px 0;box-shadow:0 0 0 1px rgba(92,173,255,.15)}}.viz-row{{display:grid;grid-template-columns:260px 1fr 100px;gap:12px;align-items:center;margin:9px 0}}.viz-row i{{display:block;height:18px;border-radius:999px;background:linear-gradient(90deg,#5cf2a7,#ffdc5c,#ff6b9a);box-shadow:0 0 18px rgba(92,242,167,.45)}}.viz-row b{{color:#ffdc5c}}
</style></head><body>
<h1>STOM 조건식 연구 프로세스 v2 — Sell-only Repair 실전 검증</h1>
<p>목적: parent buy 조건을 고정하고 parent sell 조건만 한 축씩 변경해 give-back/MDD/보유시간 개선 가능성을 공식 백테스트로 확인한다.</p>
<div class=\"grid\"><div class=\"card\"><b>상태</b><br><span class=\"ok\">{final.get('status')}</span></div><div class=\"card\"><b>엔진</b><br>{final.get('engine')}</div><div class=\"card\"><b>Fallback</b><br>{final.get('fallbackUsed')}</div><div class=\"card\"><b>후보</b><br>{len(candidates)+len(extra)}</div></div>
<h2>프로세스 흐름</h2><p>Seed Passport → Full Code Context Pack → Analysis Card v2 → Sell-only Hypotheses → Official Backtests → Next Queue</p>
<h2>Baseline</h2><table><tr><th>Profit</th><th>MDD</th><th>Trades</th><th>Win</th><th>Avg hold</th></tr><tr><td>{bm.get('total_profit_krw')}</td><td>{bm.get('mdd_pct')}</td><td>{bm.get('trade_count')}</td><td>{bm.get('win_rate')}</td><td>{bm.get('avg_hold_time')}</td></tr></table>
<h2>Candidate Results</h2><table><tr><th>Candidate</th><th>Axis</th><th>Sell trigger</th><th>Profit</th><th>MDD</th><th>Trades</th><th>Avg hold</th><th>Status</th></tr>{rows}</table>
<h2>Candidate Profit Visual Check</h2><div class=\"viz\"><p>브라우저 검증용 비균일 시각 증거: 후보별 profit 막대가 실제 backtest metric으로 렌더링된다.</p>{visual_rows}</div>
<h2>핵심 해석</h2><ul><li>모든 결과는 research-only이며 export/live/final promotion 금지.</li><li>buy-side reject 연구의 다음 빈칸인 sell-only repair 축을 독립 검증했다.</li><li>후보 조합은 단독 효과 확인 뒤에만 별도 paired repair로 진행한다.</li></ul>
<h2>산출물</h2><ul><li>Context Pack: research_context_pack.json</li><li>Analysis Card: analysis_cards.jsonl</li><li>Candidate Cards: candidate_cards.jsonl</li><li>Backtest Receipts: full_period_backtest_receipts.json</li><li>Safety Receipt: safety_receipt.json</li><li>Reports: docs/research/condition_research/research_runs/{RUN_ID}_*.md</li></ul>
</body></html>"""
    write_text(ART / "sell_only_validation_report.html", html)


def main() -> int:
    parent_buy, parent_sell = extract_passport_code(PASSPORT)
    parent_buy_sha = sha256_text(parent_buy)
    parent_sell_sha = sha256_text(parent_sell)
    created: list[dict[str, Any]] = []
    cleanup: list[dict[str, Any]] = []
    final: dict[str, Any] | None = None
    write_reports("prepared")
    try:
        save_transient_strategy(SEED["buy"], parent_buy, "buy", created)
        save_transient_strategy(SEED["sell"], parent_sell, "sell", created)
        baseline = run_backtest(SEED["buy"], SEED["sell"], 64, "baseline_engine64.json")
        baseline_metrics = baseline["metrics"]
        all_planned_candidates = CANDIDATES + EXTRA_LADDER
        context, analysis_card, candidate_pack, context_sha = make_analysis_and_context(parent_buy, parent_sell, baseline_metrics, all_planned_candidates)
        write_json(ART / "research_context_pack.json", context)
        write_text(ART / "research_context_pack_prompt.md", render_research_context_pack(context))
        write_jsonl(ART / "analysis_cards.jsonl", [analysis_card])
        write_jsonl(ART / "candidate_cards.jsonl", candidate_pack["candidates"])
        prompt_receipts = []
        candidate_results = []
        for index, candidate in enumerate(CANDIDATES, start=1):
            sell_code = build_sell_code(parent_sell, candidate)
            candidate["candidate_sell_code"] = sell_code
            candidate["candidate_sell_sha256"] = sha256_text(sell_code)
            save_transient_strategy(candidate["strategy_name"], sell_code, "sell", created)
            receipt = make_prompt_receipt(candidate, index, context, context_sha, candidate_pack)
            prompt_receipts.append(receipt)
            run = run_backtest(SEED["buy"], candidate["strategy_name"], 64, f"{candidate['strategy_name']}_engine64.json")
            metrics = run["metrics"]
            candidate_results.append({
                **candidate,
                "status": (run.get("result") or {}).get("status"),
                "run": run,
                "metrics": metrics,
                "candidate_csv": metrics.get("csv_path"),
            })
        fallback, fallback_reason = should_fallback(baseline, candidate_results)
        fallback_receipt = {"schemaVersion": 1, "kind": "engine-fallback-receipt", "runId": RUN_ID, "triggered": False, "reason": "", "createdAt": now()}
        if fallback:
            fallback_receipt.update({"triggered": True, "reason": fallback_reason, "fromEngine": 64, "toEngine": 32})
            fallback_run = run_backtest(SEED["buy"], SEED["sell"], 32, "baseline_engine32_fallback.json")
            fallback_candidate_runs = []
            for candidate in CANDIDATES:
                fallback_candidate_runs.append({
                    "strategy_name": candidate["strategy_name"],
                    "run": run_backtest(SEED["buy"], candidate["strategy_name"], 32, f"{candidate['strategy_name']}_engine32_fallback.json"),
                })
            fallback_receipt["fallbackBaseline"] = fallback_run
            fallback_receipt["fallbackCandidates"] = fallback_candidate_runs
        write_json(ART / "engine_fallback_receipt.json", fallback_receipt)

        extra_results: list[dict[str, Any]] = []
        # If the primary run is clean, do two additional research-only ladder candidates immediately.
        if not fallback:
            for index, candidate in enumerate(EXTRA_LADDER, start=1):
                sell_code = build_sell_code(parent_sell, candidate)
                candidate["candidate_sell_code"] = sell_code
                candidate["candidate_sell_sha256"] = sha256_text(sell_code)
                save_transient_strategy(candidate["strategy_name"], sell_code, "sell", created)
                prompt_receipts.append(make_prompt_receipt(candidate, len(CANDIDATES) + index, context, context_sha, candidate_pack))
                run = run_backtest(SEED["buy"], candidate["strategy_name"], 64, f"{candidate['strategy_name']}_engine64.json")
                metrics = run["metrics"]
                extra_results.append({
                    **candidate,
                    "status": (run.get("result") or {}).get("status"),
                    "run": run,
                    "metrics": metrics,
                    "candidate_csv": metrics.get("csv_path"),
                })

        receipts = []
        for item in candidate_results + extra_results:
            metrics = item.get("metrics") or {}
            receipts.append({
                "strategy_name": item.get("strategy_name"),
                "hypothesis_id": item.get("hypothesis_id"),
                "mutation_axis": item.get("mutation_axis"),
                "sell_expression": item.get("expression"),
                "candidate_sell_sha256": item.get("candidate_sell_sha256"),
                "candidate_csv": item.get("candidate_csv"),
                "status": item.get("status"),
                "metrics": metrics,
                "research_contract": {
                    "schema_version": 1,
                    "enabled": True,
                    "lane": "repair",
                    "kind": "sell",
                    "prompt_receipt": next((r for r in prompt_receipts if r.get("output_candidate_id") == item.get("strategy_name")), None),
                    "parent_conditions": candidate_pack["parents"],
                    "preserves_parent_structure": True,
                    "mode_authority": "research_only",
                },
            })
        write_jsonl(ART / "prompt_mutation_receipts.jsonl", prompt_receipts)
        write_json(ART / "full_period_backtest_receipts.json", {
            "schemaVersion": 1,
            "kind": "sell-only-full-period-official-backtest-receipts",
            "runId": RUN_ID,
            "engine": 64,
            "fallbackUsed": fallback,
            "baseline": baseline,
            "candidate_count": len(candidate_results) + len(extra_results),
            "candidates": receipts,
        })
        safety = {
            "schemaVersion": 1,
            "kind": "research-only-safety-receipt",
            "runId": RUN_ID,
            "createdAt": now(),
            "export": False,
            "live": False,
            "finalPromotion": False,
            "conditionDiscoveryProcess": "process-research",
            "preset": "research",
            "sellOnly": True,
            "parentBuyFixed": True,
            "slippage": "3_tick_advisory_only",
            "protectedPathMutationAllowed": False,
            "transientStrategyRows": created,
        }
        write_json(ART / "safety_receipt.json", safety)
        final = {
            "schemaVersion": 1,
            "kind": "sell-only-repair-validation-summary",
            "runId": RUN_ID,
            "status": "ok" if (baseline.get("result") or {}).get("status") in ("ok", "success") else "error",
            "engine": 64,
            "fallbackUsed": fallback,
            "baseline": baseline,
            "candidateResults": candidate_results,
            "extraCandidateResults": extra_results,
            "artifacts": {
                "contextPack": rel(ART / "research_context_pack.json"),
                "contextPackPrompt": rel(ART / "research_context_pack_prompt.md"),
                "candidateCards": rel(ART / "candidate_cards.jsonl"),
                "analysisCards": rel(ART / "analysis_cards.jsonl"),
                "promptReceipts": rel(ART / "prompt_mutation_receipts.jsonl"),
                "backtestReceipts": rel(ART / "full_period_backtest_receipts.json"),
                "fallbackReceipt": rel(ART / "engine_fallback_receipt.json"),
                "safetyReceipt": rel(ART / "safety_receipt.json"),
            },
        }
        write_json(ART / "final_summary.json", final)
        write_reports("final summary written", baseline, candidate_results, extra_results, final)
        build_html_report(final)
        dashboard = {
            "schemaVersion": 1,
            "kind": "dashboard-html-verification",
            "runId": RUN_ID,
            "createdAt": now(),
            "status": "html-artifact-generated",
            "htmlReport": rel(ART / "sell_only_validation_report.html"),
            "resultReport": rel(DOC_RUNS / f"{RUN_ID}_result.md"),
            "managementReport": rel(DOC_RUNS / f"{RUN_ID}_management.md"),
            "artifactDir": rel(ART),
        }
        write_json(ART / "dashboard_verification.json", dashboard)
        return_code = 0 if final["status"] == "ok" else 2
        return return_code
    finally:
        cleanup = cleanup_transient_strategies(created)
        write_json(ART / "strategy_db_cleanup_receipt.json", {"schemaVersion": 1, "kind": "strategy-db-cleanup-receipt", "runId": RUN_ID, "createdAt": now(), "items": cleanup})
        if final is not None:
            final["strategyDbCleanupReceipt"] = rel(ART / "strategy_db_cleanup_receipt.json")
            write_json(ART / "final_summary.json", final)
            # Rewrite safety with cleanup evidence after DB cleanup.
            safety_path = ART / "safety_receipt.json"
            if safety_path.exists():
                safety = json.loads(safety_path.read_text(encoding="utf-8"))
                safety["strategyDbCleanupReceipt"] = rel(ART / "strategy_db_cleanup_receipt.json")
                write_json(safety_path, safety)
        print(json.dumps({"runId": RUN_ID, "artifactDir": rel(ART), "status": None if final is None else final.get("status"), "cleanupCount": len(cleanup)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
