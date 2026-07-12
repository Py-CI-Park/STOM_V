from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable

from ai_strategy_loop.scripts.run_canonical_mini_loop import (
    DEFAULT_PROFILE,
    METHODOLOGY,
    MiniLoopConfig,
    TIMEFRAME,
    run_mini_loop,
)

BUY_NAME = "CLR07_official_buy"
SELL_NAME = "CLR07_official_sell"
CONTROL_POSITIVE_BUY = "CLR07_control_positive_buy"
CONTROL_POSITIVE_SELL = "CLR07_control_positive_sell"
CONTROL_NEGATIVE_BUY = "CLR07_control_negative_buy"
CONTROL_NEGATIVE_SELL = "CLR07_control_negative_sell"
ABLATION_BUY = "CLR07_ablation_buy"
ABLATION_SELL = "CLR07_ablation_sell"


class OfficialProvider:
    def __init__(
        self,
        *,
        generate: Callable[[str, str, str], dict[str, Any]] | None = None,
        strategy_db: str | Path,
        timeframe: str = TIMEFRAME,
    ) -> None:
        self.strategy_db = Path(strategy_db)
        self.timeframe = timeframe
        self._generate = generate or self._make_default_generate()

    def _make_default_generate(self) -> Callable[[str, str, str], dict[str, Any]]:
        from ai_strategy_loop.brain import DedupTracker, generate_strategy
        from ai_strategy_loop.config import LoopConfig
        from ai_strategy_loop.provider.factory import make_provider

        loop_config = LoopConfig()
        provider = make_provider(loop_config)
        dedup = DedupTracker(k=5)

        def generate(gubun: str, name: str, autopsy_feedback: str) -> dict[str, Any]:
            return generate_strategy(
                provider,
                gubun,
                name,
                str(self.strategy_db),
                timeframe=self.timeframe,
                retry_max=3,
                dedup=dedup,
                autopsy_feedback=autopsy_feedback,
            )

        return generate

    def propose_pack(self, *, round_no: int, feedback: list[dict]) -> list[dict]:
        proposals: list[dict[str, Any]] = []
        specs = (
            ("repair", "momentum", 0.40),
            ("repair", "mean_reversion", 0.45),
            ("discovery", "momentum", 0.90),
            ("discovery", "mean_reversion", 0.85),
        )

        seen_expressions: set[str] = set()
        for index, (lane, family, novelty) in enumerate(specs, start=1):
            stem = f"CLR07_R{round_no:02d}_{index:02d}_{lane}_{family}"
            buy: dict[str, Any] = {}
            sell: dict[str, Any] = {}
            buy_code = ""
            sell_code = ""
            expression = ""
            sell_expression = "보유시간 >= 1"
            candidate_feedback = ""
            for attempt in range(1, 4):
                candidate_feedback = _feedback_text(
                    round_no,
                    feedback,
                    lane=lane,
                    family=family,
                    avoid=sorted(seen_expressions),
                    attempt=attempt,
                )
                buy = self._generate("buy", f"{stem}_buy", candidate_feedback)
                sell = self._generate("sell", f"{stem}_sell", candidate_feedback)
                if buy.get("status") != "ok" or sell.get("status") != "ok":
                    raise RuntimeError(f"generation_failed:{stem}")
                buy_code = str(buy.get("code") or "")
                sell_code = str(sell.get("code") or "")
                expression = _extract_condition_expression(buy_code)
                sell_expression = _extract_condition_expression(sell_code, default="보유시간 >= 1")
                if expression and expression not in seen_expressions:
                    break
            if expression and expression not in seen_expressions:
                seen_expressions.add(expression)
            proposals.append(
                _official_proposal(
                    candidate_id=f"r{round_no}-{index}-{lane}-{family}",
                    lane=lane,
                    family=family,
                    expression=expression,
                    sell_expression=sell_expression,
                    novelty=novelty,
                    round_no=round_no,
                    index=index,
                    feedback_text=candidate_feedback,
                    buy_code=buy_code,
                    sell_code=sell_code,
                )
            )
        return proposals


def _feedback_text(
    round_no: int,
    feedback: list[dict],
    *,
    lane: str,
    family: str,
    avoid: list[str] | None = None,
    attempt: int = 1,
) -> str:
    rendered = json.dumps(feedback, ensure_ascii=False, sort_keys=True) if feedback else "[]"
    avoid = list(avoid or [])
    avoid_text = ""
    if avoid:
        avoid_text = (
            " Avoid these exact already-used expressions in this round and produce a different "
            f"condition: {json.dumps(avoid, ensure_ascii=False)}."
        )
    return (
        f"CL-R07 round {round_no} attempt {attempt} {lane}/{family}: output one SINGLE distinctive MINIMAL min-scope "
        "ENTRY condition for this candidate. Use one loose indicator condition likely to trade in a "
        "5-day single-stock min window, from 체결강도/등락율/초당거래대금 계열. Do not make the "
        "selected clause a boilerplate universe/time/market-cap filter. Make this candidate differ by "
        "lane/family and, when feedback is present, change materially versus the prior-round feedback."
        f"{avoid_text} feedback={rendered}"
    )


def _extract_condition_expression(code: str, *, default: str = "") -> str:
    text = " ".join(line.strip() for line in code.splitlines() if line.strip() and not line.strip().startswith("#"))
    if not text:
        return default
    if "\n" not in code and not any(token in text for token in ("매수", "매도", "self.", ":")):
        return text
    candidates: list[str] = []
    for raw_line in code.splitlines():
        line = raw_line.strip()
        if not line.startswith(("if ", "elif ")) or not line.endswith(":"):
            continue
        condition = line.split(" ", 1)[1][:-1].strip()
        if condition in {"매수", "매도"} or "self." in condition:
            continue
        if _is_boilerplate_condition(condition):
            continue
        candidates.append(condition)
    if candidates:
        return candidates[0]
    return default or text


def _is_boilerplate_condition(condition: str) -> bool:
    compact = condition.replace(" ", "")
    return (
        "관심종목" in condition
        or "시분초" in condition
        or "시가총액" in condition
        or compact in {"True", "1==1"}
    )


def _official_proposal(
    *,
    candidate_id: str,
    lane: str,
    family: str,
    expression: str,
    sell_expression: str,
    novelty: float,
    round_no: int,
    index: int,
    feedback_text: str,
    buy_code: str,
    sell_code: str,
) -> dict[str, Any]:
    dataset_sha = hashlib.sha256(f"{candidate_id}:{expression}:{sell_expression}".encode("utf-8")).hexdigest()
    feedback_sha = hashlib.sha256(feedback_text.encode("utf-8")).hexdigest()
    return {
        "candidate_id": candidate_id,
        "lane": lane,
        "family": family,
        "expression": expression,
        "buy": expression,
        "sell": sell_expression,
        "buy_code": buy_code,
        "sell_code": sell_code,
        "timeframe": TIMEFRAME,
        "novelty": float(novelty),
        "threshold_provenance": {
            "estimator": "official_llm_feedback_conditioned",
            "parameters": {"round_no": round_no, "proposal_index": index, "feedback_sha": feedback_sha},
            "fit_role": "unit",
            "period": "bounded_single_stock_window",
            "row_count": 5,
            "row_signature": f"{METHODOLOGY}:{candidate_id}",
            "dataset_sha": dataset_sha,
            "fold_id": f"round-{round_no}",
            "source_receipt": feedback_sha,
        },
    }


class OfficialEvaluator:
    def __init__(
        self,
        *,
        backtest: Callable[[str, str, str, int, int], dict[str, Any]] | None = None,
        select_window: Callable[..., tuple[str, int, int, int] | tuple[str, int, int]] | None = None,
        strategy_db: str | Path,
    ) -> None:
        self.strategy_db = Path(strategy_db)
        self._uses_default_backtest = backtest is None
        self._backtest = backtest or self._default_backtest
        self._select_window = select_window or self._default_select_window
        self._winner: dict[str, str] = {"buy": _buy_code("체결강도 > 100"), "sell": _sell_code("보유시간 >= 1"), "clause": "체결강도 > 100"}

    def evaluate(self, candidate: dict, *, kind: str, arm: str | None, context: dict) -> dict[str, Any]:
        try:
            if kind == "primary":
                clause = str(candidate.get("expression") or candidate.get("buy") or "")
                buy_code = str(candidate.get("buy_code") or _buy_code(clause))
                sell_code = str(candidate.get("sell_code") or _sell_code(str(candidate.get("sell") or "보유시간 >= 1")))
                self._winner = {"buy": buy_code, "sell": sell_code, "clause": clause}
                return self._evaluate_codes(BUY_NAME, SELL_NAME, buy_code, sell_code, clause)
            if kind == "control_positive":
                return self._evaluate_codes(
                    CONTROL_POSITIVE_BUY,
                    CONTROL_POSITIVE_SELL,
                    _buy_code("체결강도 >= 0"),
                    _sell_code("보유시간 >= 1"),
                    "control_positive",
                )
            if kind == "control_negative":
                return self._evaluate_codes(
                    CONTROL_NEGATIVE_BUY,
                    CONTROL_NEGATIVE_SELL,
                    _buy_code("체결강도 < -999999"),
                    _sell_code("보유시간 >= 1"),
                    "control_negative",
                )
            if kind == "ablation":
                if arm not in {"A", "B", "C", "D"}:
                    return _error_result(f"invalid_ablation_arm:{arm}", str(candidate.get("expression") or "ablation"))
                buy_on = arm in {"A", "B"}
                sell_on = arm in {"A", "C"}
                buy_code = self._winner["buy"] if buy_on else _buy_code("체결강도 < -999999")
                sell_code = self._winner["sell"] if sell_on else _sell_code("보유시간 >= 999999")
                return self._evaluate_codes(f"{ABLATION_BUY}_{arm}", f"{ABLATION_SELL}_{arm}", buy_code, sell_code, f"ablation {arm}")
            if kind == "extra":
                return self._evaluate_codes(BUY_NAME, SELL_NAME, self._winner["buy"], self._winner["sell"], "extra")
            return _error_result(f"unsupported_kind:{kind}", str(candidate.get("expression") or kind))
        except Exception as exc:  # official harness must fail closed without raising into the driver
            return _error_result(str(exc), str(candidate.get("expression") or kind))

    def _evaluate_codes(self, buy_name: str, sell_name: str, buy_code: str, sell_code: str, clause: str) -> dict[str, Any]:
        save = _save_strategy_pair(self.strategy_db, buy_name, buy_code, sell_name, sell_code)
        if save.get("status") != "ok":
            return _error_result(str(save), clause)
        one_code, start, end = self._window()
        raw = self._backtest(
            buy_name if self._uses_default_backtest else buy_code,
            sell_name if self._uses_default_backtest else sell_code,
            one_code,
            int(start),
            int(end),
        )
        if raw.get("status") == "error":
            return _error_result(str(raw.get("message") or raw), clause)
        return {
            "status": "ok",
            "profit": float(raw.get("profit", 0.0)),
            "mdd": float(raw.get("mdd", 0.0)),
            "trade_count": int(raw.get("trade_count", 0)),
            "daily_freq": float(raw.get("daily_freq", 0.0)),
            "clause": clause,
        }

    def _window(self) -> tuple[str, int, int]:
        try:
            selected = self._select_window(TIMEFRAME, 5)
        except TypeError:
            selected = self._select_window()
        return str(selected[0]), int(selected[1]), int(selected[2])

    @staticmethod
    def _default_select_window(timeframe: str = TIMEFRAME, window_days: int = 5) -> tuple[str, int, int, int]:
        from ai_strategy_loop.scripts.e2e_smoke import _select_single_stock

        return _select_single_stock(timeframe, window_days=window_days)

    def _default_backtest(self, buy_name: str, sell_name: str, one_code: str, start: int, end: int) -> dict[str, Any]:
        import ai_strategy_loop.bootstrap as bootstrap
        import ai_strategy_loop.scripts.e2e_smoke as e2e_smoke
        from ai_strategy_loop.config import LoopConfig
        from ai_strategy_loop.scripts.e2e_smoke import _parse_cli_json, _run_backtest_subprocess

        loop = LoopConfig()
        original_buy_name = e2e_smoke.BUY_NAME
        original_sell_name = e2e_smoke.SELL_NAME
        original_loop_db = bootstrap.LOOP_DB_STRATEGY
        original_e2e_loop_db = e2e_smoke.bootstrap.LOOP_DB_STRATEGY
        try:
            e2e_smoke.BUY_NAME = buy_name
            e2e_smoke.SELL_NAME = sell_name
            bootstrap.LOOP_DB_STRATEGY = self.strategy_db
            e2e_smoke.bootstrap.LOOP_DB_STRATEGY = self.strategy_db
            os.environ["STOM_CLI_DB_STRATEGY"] = str(self.strategy_db)
            os.environ["STOM_ALLOW_MINIMAL_SETTING"] = "1"
            proc = _run_backtest_subprocess(loop, one_code, start, end)
        finally:
            e2e_smoke.BUY_NAME = original_buy_name
            e2e_smoke.SELL_NAME = original_sell_name
            bootstrap.LOOP_DB_STRATEGY = original_loop_db
            e2e_smoke.bootstrap.LOOP_DB_STRATEGY = original_e2e_loop_db
        payload = _parse_cli_json(proc.stdout)
        if payload and str(payload.get("message") or "") == "backtest completed without metrics":
            # Clean zero-trade backtest (engine finished exitcode 0, no CSV produced):
            # a valid zero-activity measurement, not an infra error. Required so degenerate
            # ablation off-arms (buy-off/sell-off) yield the 4 metrics for compute_attribution.
            return {"status": "ok", "profit": 0.0, "mdd": 0.0, "trade_count": 0, "daily_freq": 0.0}
        if proc.returncode != 0 or not payload:
            return {"status": "error", "message": proc.stderr.strip() or proc.stdout.strip() or f"exit:{proc.returncode}"}
        metrics = payload.get("metrics") or {}
        if payload.get("status") not in {"ok", "success", "completed"} and not metrics:
            return {"status": "error", "message": payload.get("message") or payload}
        return {
            "status": "ok",
            "profit": float(metrics.get("total_profit_pct") or metrics.get("profit") or 0.0),
            "mdd": float(metrics.get("mdd_pct") or metrics.get("mdd") or 0.0),
            "trade_count": int(metrics.get("trade_count") or 0),
            "daily_freq": float(metrics.get("daily_freq") or metrics.get("trades_per_day") or 0.0),
        }


def _save_strategy_pair(strategy_db: Path, buy_name: str, buy_code: str, sell_name: str, sell_code: str) -> dict[str, Any]:
    from ai_strategy_loop.bootstrap import ensure_loop_db_engine_compat
    from cli.strategy_generator import save_strategy_to_db

    ensure_loop_db_engine_compat(str(strategy_db))
    buy = save_strategy_to_db(str(strategy_db), buy_name, buy_code, "buy")
    if buy.get("status") != "ok":
        return buy
    sell = save_strategy_to_db(str(strategy_db), sell_name, sell_code, "sell")
    if sell.get("status") != "ok":
        return sell
    return {"status": "ok"}


def _buy_code(expression: str) -> str:
    return f"매수 = False\nif {expression}:\n    매수 = True\nif 매수:\n    self.Buy()\n"


def _sell_code(expression: str) -> str:
    return f"매도 = False\nif {expression}:\n    매도 = True\nif 매도:\n    self.Sell()\n"


def _error_result(message: str, clause: str) -> dict[str, Any]:
    return {"status": "error", "profit": 0.0, "mdd": 0.0, "trade_count": 0, "daily_freq": 0.0, "clause": clause, "message": message}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the CL-R07 bounded canonical mini-loop with official adapters.")
    parser.add_argument("--strategy-db", required=True, type=Path, help="Isolated generated-strategy/state DB path.")
    parser.add_argument("--evidence-dir", required=True, type=Path, help="Isolated evidence directory path.")
    parser.add_argument("--profile", default=DEFAULT_PROFILE)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    strategy_db = Path(args.strategy_db)
    code_db = strategy_db.parent / "strategy_code.sqlite"
    os.environ["STOM_CLI_DB_STRATEGY"] = str(code_db)
    os.environ["STOM_ALLOW_MINIMAL_SETTING"] = "1"
    from ai_strategy_loop.bootstrap import ensure_loop_db_engine_compat
    from ai_strategy_loop.provider.chatgpt_oauth import (
        clear_env,
        inject_env,
        start_proxy_sync,
        stop_proxy_sync,
    )

    ensure_loop_db_engine_compat(str(code_db))
    config = MiniLoopConfig(strategy_db=strategy_db, evidence_dir=args.evidence_dir, profile=args.profile)
    # gpt_auth generation requires the local OAuth proxy running for the whole loop.
    inject_env()
    if not start_proxy_sync():
        clear_env()
        print(json.dumps({"status": "NO_GO_PROXY_START_FAILED", "stop_reason": "proxy_start_failed"}, ensure_ascii=False, sort_keys=True))
        return 3
    try:
        provider = OfficialProvider(strategy_db=code_db, timeframe=TIMEFRAME)
        evaluator = OfficialEvaluator(strategy_db=code_db)
        summary = run_mini_loop(config, provider=provider, evaluator=evaluator)
    finally:
        stop_proxy_sync()
        clear_env()
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if summary["status"] == "GO_PROCESS_PROOF" else 2


if __name__ == "__main__":
    raise SystemExit(main())
