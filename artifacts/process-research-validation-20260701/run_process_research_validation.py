from __future__ import annotations

import hashlib
import json
import os
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
from ai_strategy_loop.controller.condition_discovery import (  # noqa: E402
    LANE_DISCOVERY,
    LANE_REPAIR,
    build_research_analysis_card,
)
from cli.ai_controller import AIBacktestController  # noqa: E402
from cli.condition_generator import validate_multi_hypothesis_candidate_pack  # noqa: E402
from cli.paths import DB_STRATEGY  # noqa: E402
from cli.strategy_loader import load_strategy_from_db  # noqa: E402

RUN_ID = "process_research_v2_validation_20260701"
ART = REPO / "artifacts" / "process-research-validation-20260701"
DOC_RUNS = REPO / "docs" / "research" / "condition_research" / "research_runs"
PASSPORTS = REPO / "docs" / "research" / "condition_research" / "condition_passports"
for path in (ART, DOC_RUNS, PASSPORTS):
    path.mkdir(parents=True, exist_ok=True)

SEEDS = [
    {
        "condition_id": "rr8_12_turnover_min_902=1.5",
        "human_name": "OOSStable_Open902_TurnoverMin_v1",
        "role": "start_seed",
        "buy": "GATE_rr8_12_turnover_min_902_1_5_B",
        "sell": "GATE_rr8_12_turnover_min_902_1_5_S",
        "prior": {"profit": 3062696, "mdd": 12.87, "trades": 190, "daily": 0.8, "source": "2026-06-28 official 2025 replay"},
    },
    {
        "condition_id": "rr8_21_trail_keep=0.7",
        "human_name": "ProfitLead_TrailKeep070_2025Comparator",
        "role": "profit_comparator",
        "buy": "GATE_rr8_21_trail_keep_0_7_B",
        "sell": "GATE_rr8_21_trail_keep_0_7_S",
        "prior": {"profit": 3089180, "mdd": 18.84, "trades": 165, "daily": 0.7, "source": "2026-06-28 official 2025 replay"},
    },
    {
        "condition_id": "rr8_0_cap_max=2500",
        "human_name": "CapLimited_2500_Comparator",
        "role": "segment_comparator",
        "buy": "GATE_rr8_0_cap_max_2500_B",
        "sell": "GATE_rr8_0_cap_max_2500_S",
        "prior": {"profit": 3047522, "mdd": 17.34, "trades": 145, "daily": 0.6, "source": "2026-06-28 official 2025 replay"},
    },
    {
        "condition_id": "human_seed_gptauth_B_gen8",
        "human_name": "GPTGen8_HighCoverage_FailedProfitContext",
        "role": "failure_coverage_context",
        "buy": "AILOOP_follow12_gptauth_B_seeded64_20260628_g8_buy",
        "sell": "AILOOP_follow12_gptauth_B_seeded64_20260628_g8_sell",
        "prior": {"profit": 1772126, "mdd": 15.14, "trades": 550, "daily": 2.3, "source": "2026-06-28 official 2025 replay"},
    },
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fp:
        for row in rows:
            fp.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(REPO.resolve()).as_posix()
    except Exception:
        return str(path).replace("\\", "/")


def load_strategy(name: str, kind: str) -> dict[str, Any]:
    loaded = load_strategy_from_db(DB_STRATEGY, name, kind)
    if loaded.get("status") != "ok":
        raise RuntimeError(f"strategy_load_failed {kind} {name}: {loaded}")
    code = str(loaded.get("code") or "")
    return {"id": name, "code": code, "sha256": sha256_text(code), "var_refs": loaded.get("var_refs") or [], "warnings": loaded.get("warnings") or []}


def load_seed_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for seed in SEEDS:
        buy = load_strategy(seed["buy"], "buy")
        sell = load_strategy(seed["sell"], "sell")
        item = {**seed, "buy_record": buy, "sell_record": sell}
        records.append(item)
    return records


def write_passports(records: list[dict[str, Any]]) -> None:
    for item in records:
        passport_path = PASSPORTS / f"{item['condition_id'].replace('=', '_').replace('/', '_')}.md"
        buy = item["buy_record"]
        sell = item["sell_record"]
        text = f"""# Condition Passport — {item['human_name']}

| Field | Value |
|---|---|
| condition_id | `{item['condition_id']}` |
| human_name | `{item['human_name']}` |
| role | `{item['role']}` |
| buy_strategy_id | `{buy['id']}` |
| sell_strategy_id | `{sell['id']}` |
| buy_code_sha256 | `{buy['sha256']}` |
| sell_code_sha256 | `{sell['sha256']}` |
| prior_profit | `{item['prior'].get('profit')}` |
| prior_mdd | `{item['prior'].get('mdd')}` |
| prior_trades | `{item['prior'].get('trades')}` |
| promotion_status | `research_only / not_promoted` |

## Core hypothesis

이 passport는 개선된 process-research v2 검증의 입력이다. LLM에는 id만 전달하지 않고 buy/sell 조건식 전문과 sha256을 함께 전달한다.

## Buy condition full code

```python
{buy['code']}
```

## Sell condition full code

```python
{sell['code']}
```
"""
        write_text(passport_path, text)
        item["passport_path"] = rel(passport_path)


def seed_summary(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "condition_id": r["condition_id"],
            "human_name": r["human_name"],
            "role": r["role"],
            "buy_id": r["buy_record"]["id"],
            "sell_id": r["sell_record"]["id"],
            "buy_sha256": r["buy_record"]["sha256"],
            "sell_sha256": r["sell_record"]["sha256"],
            "prior": r["prior"],
            "passport_path": r.get("passport_path"),
        }
        for r in records
    ]


def make_metrics_from_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    # Analysis CSV output shape varies by analyzer path; keep JSON-safe key evidence and prior official metrics.
    return {
        "status": analysis.get("status"),
        "recommended_candidate_count": len(analysis.get("recommended_candidates") or []),
        "time_analysis": analysis.get("time_analysis") or [],
        "market_cap_candidates": analysis.get("market_cap_candidates") or [],
        "quantile_candidate_count": len(analysis.get("quantile_candidates") or []),
        "ttest_candidate_count": len(analysis.get("ttest_candidates") or []),
        "baseline_prior_profit": 3062696,
        "baseline_prior_mdd": 12.87,
        "baseline_prior_trades": 190,
    }


def make_context_and_candidates(records: list[dict[str, Any]], analysis: dict[str, Any], baseline_csv: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    parent = records[0]
    context_pack_id = f"rcp_{RUN_ID}"
    metrics = make_metrics_from_analysis(analysis)
    root_cause = {
        "primary": "직전 연구에서 turnover_min_902 1.5 -> 3.0 강화는 profit/MDD를 모두 악화시켰으므로 같은 축 반복 대신 고등락 과열, 약한 체결강도, 거래대금 붕괴, 초소형 약점 구간을 분리 검증한다.",
        "evidence": [
            "docs/research/condition_research/auto_reports/morning_20260628_human_process_research.md",
            baseline_csv,
        ],
    }
    segment_contribution = {
        "time": "09:00~09:10 open regime 중심. 기존 분석에서 09:05~09:10이 상대적으로 약한 후보군으로 반복 확인됨.",
        "market_cap": "초소형은 거래수 대비 효율이 낮아 방어 repair 후보에 포함한다.",
        "regime": "등락율 과열, 체결강도 약화, 거래대금증감 붕괴를 각각 별도 가설로 분리한다.",
    }
    candidate_hypotheses = [
        {
            "hypothesis_id": "H_REPAIR_OVERHEAT_01",
            "lane": "repair",
            "mutation_axis": "overextension_reject_filter",
            "expected_effect": "과열 추격 진입을 줄여 MDD와 MAE를 낮춘다.",
            "risk_note": "강한 추세 지속 구간을 일부 버려 profit이 줄 수 있다.",
        },
        {
            "hypothesis_id": "H_REPAIR_MICROCAP_WEAK_02",
            "lane": "repair",
            "mutation_axis": "microcap_weak_open_filter",
            "expected_effect": "초소형 약한 초반 진입을 줄여 손실 cluster를 낮춘다.",
            "risk_note": "초소형 승자 일부를 같이 제거할 수 있다.",
        },
        {
            "hypothesis_id": "H_DISCOVERY_STRENGTH_03",
            "lane": "discovery",
            "mutation_axis": "high_strength_regime_filter",
            "expected_effect": "체결강도 약한 진입을 제거해 quality를 높인다.",
            "risk_note": "거래수 감소와 late-entry bias 가능성이 있다.",
        },
        {
            "hypothesis_id": "H_DISCOVERY_TURNOVER_DECAY_04",
            "lane": "discovery",
            "mutation_axis": "turnover_decay_regime_filter",
            "expected_effect": "거래대금증감 붕괴 국면을 제거해 give-back을 줄인다.",
            "risk_note": "거래대금증감의 단위/분포 민감도가 커서 과필터 위험이 있다.",
        },
    ]
    context = build_research_context_pack(
        context_pack_id=context_pack_id,
        mode="process-research",
        timeframe="tick",
        parent_buy_id=parent["buy_record"]["id"],
        parent_buy_code=parent["buy_record"]["code"],
        parent_sell_id=parent["sell_record"]["id"],
        parent_sell_code=parent["sell_record"]["code"],
        official_metrics=metrics,
        daily_rows_summary={"source": "baseline official replay", "baseline_csv": baseline_csv},
        regime_summaries={"open_regime": "09:00~09:10", "slippage": "3 tick advisory only"},
        segment_heatmap={"time_x_cap_x_regime": "required in result report; current run starts from prior 2026-06-28 segment notes and analyzer output"},
        feature_importance={"source": "analysis_result", "recommended_candidates": analysis.get("recommended_candidates") or []},
        edge_ratio={"prior_edge_ratio": 1.3895514417942327},
        mfe_mae={"prior_mean_mfe": 2.4652105263157895, "prior_mean_mae": 1.7741052631578949},
        correlation_redundancy={"policy": "do not repeat turnover_min_902 strengthening; separate hypotheses by feature family"},
        avoid_zones=["repeat turnover_min_902 1.5 -> 3.0", "R_/S_ diagnostic leakage", "promotion/live/export authority"],
        prefer_zones=["single-axis repair", "distinct discovery coverage", "official backtest ranking"],
        root_cause_summary=root_cause,
        candidate_hypotheses=candidate_hypotheses,
        validation_provenance={"process": "process-research", "preset": "research", "research_only": True, "baseline_csv": baseline_csv},
        extra_context={"seeds": seed_summary(records), "run_id": RUN_ID},
    )
    context_sha = sha256_text(json.dumps(context, ensure_ascii=False, sort_keys=True))
    card = build_research_analysis_card(
        analysis_id=f"A_{RUN_ID}_baseline",
        candidate_id=parent["condition_id"],
        lane=LANE_REPAIR,
        metrics=metrics,
        parent_id=parent["condition_id"],
        round_id=RUN_ID,
        slot_id="baseline",
        context_pack_id=context["context_pack_id"],
        parent_comparison={"comparators": seed_summary(records[1:])},
        root_cause=root_cause,
        segment_contribution=segment_contribution,
        next_recommendation="Generate 4 audited candidates: 2 repair + 2 discovery; rank by official result only.",
        evidence_health={"status": "research_only", "baseline_csv": baseline_csv},
        validation_provenance={"engine_policy": "64 first, 32 fallback on trigger"},
        safety_flags={"can_export": False, "can_live": False, "can_final_promote": False, "slippage": "advisory_only"},
        parent_buy_id=parent["buy_record"]["id"],
        parent_buy_code=parent["buy_record"]["code"],
        parent_buy_sha256=parent["buy_record"]["sha256"],
        parent_sell_id=parent["sell_record"]["id"],
        parent_sell_code=parent["sell_record"]["code"],
        parent_sell_sha256=parent["sell_record"]["sha256"],
        daily_rows_summary={"baseline_csv": baseline_csv},
        regime_summaries={"open": "09:00~09:10"},
        segment_heatmap={"time_cap_regime": "see result report"},
        feature_importance={"recommended_candidates": analysis.get("recommended_candidates") or []},
        edge_ratio={"prior": 1.3895514417942327},
        mfe_mae={"mfe": 2.4652105263157895, "mae": 1.7741052631578949},
        correlation_redundancy={"blocked_repeat_axis": "turnover_min_902_1.5_to_3.0"},
        avoid_zones=["turnover_min_902 repeat", "authority smuggling"],
        prefer_zones=["single root-cause axis", "different feature families"],
        mutation_axis="multi_hypothesis_branching",
        expected_effect="Find whether high-overextension, weak microcap, weak strength, or turnover-decay filters improve official result.",
        risk_note="Every filter can reduce trades and may worsen profit; official result decides.",
    )
    parent_buy = parent["buy_record"]
    parent_sell = parent["sell_record"]
    base_candidate = {
        "analysis_card_id": card["analysis_id"],
        "parent_buy_id": parent_buy["id"],
        "parent_buy_code": parent_buy["code"],
        "parent_buy_sha256": parent_buy["sha256"],
        "parent_sell_id": parent_sell["id"],
        "parent_sell_code": parent_sell["code"],
        "parent_sell_sha256": parent_sell["sha256"],
        "preserves_parent_structure": True,
        "mode_authority": "research_only",
        "generation_allowed": True,
        "full_stom_sources_included": True,
        "prompt_budget_estimated_tokens": context["budget"]["estimated_tokens"],
        "context_pack_id": context["context_pack_id"],
        "context_pack_sha256": context_sha,
    }
    candidates = [
        {
            **base_candidate,
            "lane": "repair",
            "hypothesis_id": "H_REPAIR_OVERHEAT_01",
            "expression": "등락율 >= 7.2",
            "intended_hypothesis": "Reject overextended opening spikes rather than repeating turnover strengthening.",
            "mutation_axis": "overextension_reject_filter",
            "expected_effect": "Reduce high-chase MAE/MDD while preserving most baseline structure.",
            "risk_note": "Can remove true momentum winners and reduce profit.",
        },
        {
            **base_candidate,
            "lane": "repair",
            "hypothesis_id": "H_REPAIR_MICROCAP_WEAK_02",
            "expression": "시가총액 < 700 and 등락율 < 3.0",
            "intended_hypothesis": "Reject weak low-cap open entries that contribute poor efficiency.",
            "mutation_axis": "microcap_weak_open_filter",
            "expected_effect": "Improve payoff/MDD by removing thin weak opens.",
            "risk_note": "May remove some early microcap breakouts.",
        },
        {
            **base_candidate,
            "lane": "discovery",
            "hypothesis_id": "H_DISCOVERY_STRENGTH_03",
            "expression": "체결강도 < 120",
            "intended_hypothesis": "Explore a high-strength regime distinct from turnover_min repair.",
            "mutation_axis": "high_strength_regime_filter",
            "expected_effect": "Improve entry quality by excluding low-strength names.",
            "risk_note": "Could overfit to strength and cut trade count heavily.",
            "discovery_target_coverage": {"coverage_bucket_keys": ["strength_high", "open_0900_0910"]},
            "novelty_rationale": "Uses 체결강도 feature family rather than turnover_min_902 axis.",
            "novelty": {"feature_family": "체결강도", "coverage_regime": "open high-strength", "market_segment": "all-cap"},
        },
        {
            **base_candidate,
            "lane": "discovery",
            "hypothesis_id": "H_DISCOVERY_TURNOVER_DECAY_04",
            "expression": "거래대금증감 < -5_000_000_000",
            "intended_hypothesis": "Explore turnover-decay avoidance without tightening turnover_min_902.",
            "mutation_axis": "turnover_decay_regime_filter",
            "expected_effect": "Reduce post-spike give-back by excluding collapsing turnover regimes.",
            "risk_note": "Unit sensitivity can make the filter too narrow or too broad.",
            "discovery_target_coverage": {"coverage_bucket_keys": ["turnover_decay", "open_reversal"]},
            "novelty_rationale": "Targets 거래대금증감 decay regime rather than absolute turnover_min threshold.",
            "novelty": {"feature_family": "거래대금증감", "coverage_regime": "turnover decay", "market_segment": "reversal-risk"},
        },
    ]
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
            "buy": {"id": parent_buy["id"], "code": parent_buy["code"], "sha256": parent_buy["sha256"]},
            "sell": {"id": parent_sell["id"], "code": parent_sell["code"], "sha256": parent_sell["sha256"]},
        },
        "analysis_card_id": card["analysis_id"],
        "candidates": candidates,
    }
    validation = validate_multi_hypothesis_candidate_pack(pack, min_candidates=2)
    if not validation.get("valid"):
        raise RuntimeError("candidate_pack_validation_failed: " + json.dumps(validation, ensure_ascii=False))
    return context, card, pack


def write_run_docs(records: list[dict[str, Any]], stage: str, result: dict[str, Any] | None = None) -> None:
    plan_path = DOC_RUNS / f"{RUN_ID}_plan.md"
    management_path = DOC_RUNS / f"{RUN_ID}_management.md"
    result_path = DOC_RUNS / f"{RUN_ID}_result.md"
    seed_table = "\n".join(
        f"| {r['role']} | `{r['condition_id']}` | `{r['human_name']}` | `{r['buy_record']['id']}` | `{r['sell_record']['id']}` |"
        for r in records
    )
    if not plan_path.exists():
        write_text(plan_path, f"""# Research Plan — {RUN_ID}

## Scope

- canonical process: `process-research`
- preset: `research`
- boundary: research-only, no export, no live, no final promotion
- slippage: 3-tick advisory only
- engine policy: 64 first; 32 fallback receipt on warm prepare failure, engine_data_response_timeout, no-metrics, or replay failure
- prompt policy: `full_condition_code_required_not_id_only`

## Seeds

| Role | condition_id | human_name | buy | sell |
|---|---|---|---|---|
{seed_table}

## Required artifacts

- `research_context_pack.json`
- `candidate_cards.jsonl`
- `analysis_cards.jsonl`
- `prompt_mutation_receipts.jsonl`
- `full_period_backtest_receipts.json`
- `dashboard_verification.json`
- `safety_receipt.json`

## Candidate policy

Generate at least 2 and target 4 candidates from one baseline Analysis Card v2: repair >= 1 and discovery >= 1. Each candidate must have hypothesis, mutation axis, expected effect, risk note, parent buy/sell full code, and official backtest result or failure receipt.
""")
    write_text(management_path, f"""# Research Management Report — {RUN_ID}

| Time | Stage | Status | Evidence |
|---|---|---|---|
| {now()} | current | {stage} | `{rel(ART)}` |

## Notes

- The run keeps research-only boundaries.
- Candidate generation uses full parent buy/sell code and source hashes, not id-only context.
- Any 64-engine replay failure triggers a 32-engine fallback receipt.
""")
    if result is not None:
        result_status = result.get("status")
        candidates = result.get("candidates") or []
        rows = []
        for cand in candidates:
            cr = cand.get("candidate_result") or {}
            metrics = cr.get("metrics") or {}
            rows.append(
                f"| `{cand.get('strategy_name')}` | `{cand.get('expression')}` | {metrics.get('total_profit_krw')} | {metrics.get('mdd_pct')} | {metrics.get('trade_count')} | {cr.get('status')} |"
            )
        if not rows:
            rows.append("| none | none |  |  |  | no candidate result |")
        write_text(result_path, f"""# Research Result Report — {RUN_ID}

## Executive summary

This is a research-only validation run for the improved process. It checks whether full-context prompt packaging, Analysis Card v2, multi-hypothesis candidate branching, strict validation, and official backtest receipts are produced end-to-end. It does not export, trade live, or final-promote any condition.

## Run status

- status: `{result_status}`
- phase: `{result.get('phase')}`
- baseline_csv: `{result.get('baseline_csv')}`
- fallback_used: `{result.get('fallback_used', False)}`

## Candidate official results

| Candidate | Expression | Profit KRW | MDD % | Trades | Status |
|---|---|---:|---:|---:|---|
{chr(10).join(rows)}

## Required next interpretation

- Rank candidates only by official backtest evidence, not prompt score.
- A worse result is still useful if it sharpens root-cause and next queue.
- Any improved candidate remains research-only and can only enter later zero-generation promotion-review.
""")


def extract_research_result(raw: dict[str, Any], engine: int, fallback_used: bool) -> dict[str, Any]:
    result = raw.get("result") if isinstance(raw.get("result"), dict) else raw
    result = dict(result)
    result["engine_count"] = engine
    result["fallback_used"] = fallback_used
    return result


def run_once(records: list[dict[str, Any]], engine: int, fallback_used: bool = False) -> dict[str, Any]:
    import cli.research_loop as rl

    orig_analyze = rl.analyze_result_csv
    context_state: dict[str, Any] = {}

    def analyze_with_pack(csv_path: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        analysis = orig_analyze(csv_path, *args, **kwargs)
        if analysis.get("status") == "ok":
            context, card, pack = make_context_and_candidates(records, analysis, csv_path)
            context_state["context"] = context
            context_state["card"] = card
            context_state["pack"] = pack
            write_json(ART / "research_context_pack.json", context)
            write_text(ART / "research_context_pack_prompt.md", render_research_context_pack(context))
            append_jsonl(ART / "analysis_cards.jsonl", [card])
            append_jsonl(ART / "candidate_cards.jsonl", pack["candidates"])
            analysis = {**analysis, "research_candidate_pack": pack}
        return analysis

    rl.analyze_result_csv = analyze_with_pack
    try:
        controller = AIBacktestController()
        cfg = {
            "name": f"{RUN_ID}_engine{engine}",
            "score_reference_csv": "backtest/csv/stock_bt_GATE_rr8_12_turnover_min_902_1_5_B_20260628234642.csv",
            "base_buy_strategy": records[0]["buy_record"]["id"],
            "sell_strategy": records[0]["sell_record"]["id"],
            "start_date": 20250101,
            "end_date": 20251231,
            "is_tick": True,
            "betting": "1",
            "avg_time": 60,
            "start_time": 90000,
            "end_time": 92800,
            "engine_count": engine,
            "top_n": 4,
            "run_candidate": False,
            "run_candidates": True,
            "candidate_count": 4,
            "candidate_name_prefix": f"prv2_20260701_e{engine}",
            "cleanup_best_candidate": True,
            "keep_loser_candidates": False,
            "keep_failed_candidate": False,
            "min_estimated_retention": 0.0,
            "candidate_pool_multiplier": 1,
            "candidate_timeout": 900,
            "runtime_output_path": str(ART / f"runtime_result_engine{engine}.json"),
            "max_consecutive_candidate_failures": 4,
            "condition_discovery_process": "process-research",
            "condition_discovery_preset": "research",
            "hybrid_research_enabled": True,
        }
        write_json(ART / f"config_engine{engine}.json", cfg)
        raw = controller.research_strategy_once(cfg)
        write_json(ART / f"result_engine{engine}.json", raw)
        result = extract_research_result(raw, engine, fallback_used)
        # prompt receipts are available in candidate specs when the run reaches that phase.
        receipts = []
        for spec in result.get("candidate_specs") or []:
            receipt = spec.get("prompt_receipt") or ((spec.get("research_contract") or {}).get("prompt_receipt"))
            if receipt:
                receipts.append(receipt)
        if receipts:
            append_jsonl(ART / "prompt_mutation_receipts.jsonl", receipts)
        write_json(ART / "full_period_backtest_receipts.json", {
            "schemaVersion": 1,
            "kind": "full-period-official-backtest-receipts",
            "runId": RUN_ID,
            "engine": engine,
            "fallbackUsed": fallback_used,
            "baseline_csv": result.get("baseline_csv"),
            "candidate_count": len(result.get("candidates") or []),
            "candidates": [
                {
                    "strategy_name": c.get("strategy_name"),
                    "expression": c.get("expression"),
                    "candidate_csv": c.get("candidate_csv"),
                    "status": (c.get("candidate_result") or {}).get("status"),
                    "metrics": (c.get("candidate_result") or {}).get("metrics") or {},
                    "research_contract": c.get("research_contract") or {},
                }
                for c in (result.get("candidates") or [])
            ],
        })
        write_run_docs(records, f"engine {engine} run complete", result)
        return result
    finally:
        rl.analyze_result_csv = orig_analyze


def needs_fallback(result: dict[str, Any]) -> tuple[bool, str]:
    if result.get("status") not in ("ok", "success"):
        return True, f"status={result.get('status')} phase={result.get('phase')} message={result.get('message')}"
    if not result.get("baseline_csv"):
        return True, "no-metrics: missing baseline_csv"
    candidates = result.get("candidates") or []
    if not candidates:
        return True, "no-metrics: no candidate results"
    failed = [c for c in candidates if (c.get("candidate_result") or {}).get("status") not in ("ok", "success")]
    if len(failed) == len(candidates):
        return True, "replay failure: all candidates failed"
    return False, ""


def main() -> int:
    records = load_seed_records()
    write_passports(records)
    write_json(ART / "seed_condition_records.json", seed_summary(records))
    write_run_docs(records, "prepared")

    result64 = run_once(records, 64, fallback_used=False)
    fallback, reason = needs_fallback(result64)
    final = result64
    fallback_receipt = {"schemaVersion": 1, "kind": "engine-fallback-receipt", "runId": RUN_ID, "triggered": False, "reason": "", "createdAt": now()}
    if fallback:
        fallback_receipt.update({"triggered": True, "reason": reason, "fromEngine": 64, "toEngine": 32})
        write_json(ART / "engine_fallback_receipt.json", fallback_receipt)
        final = run_once(records, 32, fallback_used=True)
    else:
        write_json(ART / "engine_fallback_receipt.json", fallback_receipt)

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
        "slippage": "3_tick_advisory_only",
        "protectedPathMutationAllowed": False,
        "artifacts": [rel(p) for p in sorted(ART.glob("*"))],
    }
    write_json(ART / "safety_receipt.json", safety)
    dashboard = {
        "schemaVersion": 1,
        "kind": "dashboard-html-verification",
        "runId": RUN_ID,
        "createdAt": now(),
        "status": "artifact-only",
        "note": "Dashboard live browser verification should load the generated result docs/artifacts; this receipt records artifact availability for the research-only run.",
        "resultReport": rel(DOC_RUNS / f"{RUN_ID}_result.md"),
        "managementReport": rel(DOC_RUNS / f"{RUN_ID}_management.md"),
        "artifactDir": rel(ART),
    }
    write_json(ART / "dashboard_verification.json", dashboard)
    summary = {
        "schemaVersion": 1,
        "kind": "improved-process-validation-summary",
        "runId": RUN_ID,
        "status": final.get("status"),
        "phase": final.get("phase"),
        "engine": final.get("engine_count"),
        "fallbackUsed": final.get("fallback_used"),
        "baselineCsv": final.get("baseline_csv"),
        "candidateCount": len(final.get("candidates") or []),
        "artifacts": {
            "contextPack": rel(ART / "research_context_pack.json"),
            "candidateCards": rel(ART / "candidate_cards.jsonl"),
            "analysisCards": rel(ART / "analysis_cards.jsonl"),
            "promptReceipts": rel(ART / "prompt_mutation_receipts.jsonl"),
            "backtestReceipts": rel(ART / "full_period_backtest_receipts.json"),
            "fallbackReceipt": rel(ART / "engine_fallback_receipt.json"),
            "safetyReceipt": rel(ART / "safety_receipt.json"),
            "dashboardVerification": rel(ART / "dashboard_verification.json"),
        },
    }
    write_json(ART / "final_summary.json", summary)
    write_run_docs(records, "final summary written", final)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if final.get("status") in ("ok", "success") else 2


if __name__ == "__main__":
    raise SystemExit(main())
