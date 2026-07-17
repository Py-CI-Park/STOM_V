"""X1 엔진 A/B 오케스트레이션 — scratch DB·등록·인자 대조·배치 구성·metrics 추출.

봉인본 §6·§8·§14-F8·F9. **엔진 백테는 이 모듈이 직접 기동하지 않는다** —
run phase(메인 세션, measure_gate 후 분리 러너)가 assemble_* 헬퍼로 구성한 뒤
`claude_candidate_batch_eval` 을 subprocess 로 돌리고 loop_runs.db 를 읽는다
(hillclimb.engine_eval 분리 원칙 동일). 여기 함수는 순수 조립 + 파일 I/O 만.

경계(불변 규율): 실 `_database/strategy.db` 미접촉 — 변형 등록은 **scratch 복사본**에만
INSERT(§14-F9, B1 register 전례). 매도는 원본 `ALP_V4_RR8_12`(8ef01e0e) 고정.
기준 A = B1 A_2022/A_2023 재사용(추가 엔진 0) — 기동 전 엔진 인자 완전 대조(§14-F8).
"""
from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple

from alpha_lab.x1lab import variants as V

__all__ = [
    "YEAR_WINDOWS", "PARITY_FIELDS", "SELL_NAME",
    "arg_parity_check", "build_pairs_json", "build_year_config",
    "extract_metrics_from_generations", "prepare_scratch_db", "register_variants",
]

SELL_NAME = "ALP_V4_RR8_12"          # 매도 원본(8ef01e0e) 고정 대조.
CHAMPION_SELL_SHA_PREFIX = "8ef01e0e"

# 발견창 연도별 창(§1) — B1 A 런과 동일해야(§14-F8).
YEAR_WINDOWS: Dict[int, Tuple[int, int]] = {
    2022: (20220323, 20221231),
    2023: (20230101, 20231231),
}

# §14-F8 인자 완전 대조 대상(A 런 config vs X1 B config).
PARITY_FIELDS: Tuple[str, ...] = (
    "bt_betting", "bt_avg_time", "bt_timeframe",
    "bt_universe_start_time", "bt_universe_end_time",
    "bt_full_start", "bt_full_end",
)


def prepare_scratch_db(real_db_path, scratch_db_path) -> Dict[str, object]:
    """실 strategy.db → scratch 복사(실 DB 미접촉 — 복사만). run phase 에서 호출."""
    real, scratch = Path(real_db_path), Path(scratch_db_path)
    if not real.exists():
        raise FileNotFoundError(f"실 strategy.db 부재: {real}")
    scratch.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(real, scratch)
    # scratch 에 원본 매도(8ef01e0e)·매수(348c5181)가 존재하는지 확인(등록 대상 조회).
    con = sqlite3.connect(f"file:{scratch.as_posix()}?mode=ro", uri=True)
    try:
        sell = con.execute('SELECT "전략코드" FROM stocksell WHERE "index"=?',
                           (SELL_NAME,)).fetchone()
    finally:
        con.close()
    import hashlib
    sell_sha = hashlib.sha256(str(sell[0]).encode()).hexdigest() if sell else None
    return {
        "scratch_db": str(scratch), "copied_from": str(real),
        "sell_name": SELL_NAME,
        "sell_sha_prefix": (sell_sha[:8] if sell_sha else None),
        "sell_sha_ok": bool(sell_sha and sell_sha.startswith(CHAMPION_SELL_SHA_PREFIX)),
    }


def register_variants(scratch_db_path, variant_results: Mapping[str, V.VariantResult],
                      *, champion_sell_text: str,
                      now: Optional[datetime] = None) -> Dict[str, object]:
    """변형 4종을 scratch DB 에 INSERT(쌍: buy=변형·sell=원본 매도 미러) — registrar 재사용.

    scratch 만 대상(실 DB 미접촉). 매도는 원본 8ef01e0e 미러라 배치에서 sell=원본 이름을
    써도 동일. now 는 백업 파일명 스탬프(registrar 계약).
    """
    from alpha_lab.bridge.registrar import register_conditions
    scratch = Path(scratch_db_path)
    items = []
    for cand in V.CANDIDATES:
        r = variant_results[cand]
        meta = dict(V.CANDIDATE_META[cand])
        items.append({
            "name": V.strategy_name(cand),
            "buy_expr": r.text,
            "sell_expr": champion_sell_text,   # 원본 매도(8ef01e0e) 미러 — sell 고정.
            "meta": {
                "series": "X1 매수 절 삭제 엔진 A/B (봉인 cb8a9d6a)",
                "drop_clause": meta["clause"], "branch": meta["branch"],
                "buy_variant_sha256": r.sha256,
                "note": f"ALP_V4_RR8_12 매수 원문(348c5181)에서 절 #{meta['clause']} 삭제 — {meta['desc']}",
                "prereg": "2026-07-17_x1_buy_clause_drop_ab_preregistration.md (cb8a9d6a)",
            },
        })
    result = register_conditions(scratch, items, backup_dir=scratch.parent,
                                 now=now or datetime.now())
    return {"scratch_db": str(scratch), "n_items": len(items),
            "inserted": result.get("inserted"), "conflicts": result.get("conflicts"),
            "variant_names": [V.strategy_name(c) for c in V.CANDIDATES]}


def build_year_config(base_config_path, year: int) -> Dict[str, object]:
    """base 엔진 config(원본) → 해당 연도 창만 덮어쓴 config(engine_eval.build_train_config 관례).

    변형 금지 원본을 읽어 bt_full_start/end 만 교체 — 그 외 인자(betting/avg/timeframe/
    universe)는 base 를 그대로 승계(A 런과 동일 보장의 토대, §14-F8).
    """
    if year not in YEAR_WINDOWS:
        raise ValueError(f"발견창 연도 아님(2022/2023): {year}")
    start, end = YEAR_WINDOWS[year]
    base = json.loads(Path(base_config_path).read_text(encoding="utf-8"))
    config = dict(base)
    config["bt_full_start"] = int(start)
    config["bt_full_end"] = int(end)
    config["_x1_derived"] = {
        "schema": "x1_buy_drop_ab_year_config_v1", "year": year,
        "base_config": str(base_config_path),
        "changed_fields_only": ["bt_full_start", "bt_full_end"],
        "window_basis": "발견창(2022-2023)만 — 2024/2025 known 금지(봉인 §1)",
    }
    return config


def arg_parity_check(a_run_config: Mapping[str, object],
                     x1_config: Mapping[str, object], *,
                     ignore_window: bool = True) -> Dict[str, object]:
    """§14-F8 — B1 A 런 config 와 X1 B config 의 엔진 인자 완전 대조.

    ignore_window=True 면 bt_full_start/end 는 비교 제외(연도창은 다를 수 있음 —
    betting/avg/timeframe/universe 만 동일 요구). 불일치 항목이 있으면 parity_ok=False
    → 호출측(run phase)은 기동 중단하고 A 재실행(예비 예산) 판단.
    """
    fields = [f for f in PARITY_FIELDS
              if not (ignore_window and f in ("bt_full_start", "bt_full_end"))]
    diffs = {}
    for f in fields:
        a, b = a_run_config.get(f), x1_config.get(f)
        if a != b:
            diffs[f] = {"A_run": a, "X1_B": b}
    return {"parity_fields": fields, "diffs": diffs, "parity_ok": len(diffs) == 0}


def build_pairs_json(candidates: Tuple[str, ...] = V.CANDIDATES) -> List[Dict[str, str]]:
    """배치 pairs.json — buy=변형명·sell=원본 매도(ALP_V4_RR8_12). 후보 1명당 1행."""
    return [{"label": f"X1_{c}", "buy": V.strategy_name(c), "sell": SELL_NAME}
            for c in candidates]


def extract_metrics_from_generations(loop_runs_db, run_id: str,
                                     pairs: List[Mapping[str, str]]) -> Dict[str, Dict]:
    """run phase 산출 loop_runs.db generations → 후보별 A-json 호환 metrics.

    hillclimb.engine_eval.read_generation_metrics 와 같은 원천(generations 행)에서
    total_profit_krw(profit)·trade_count·mdd_pct(mdd)·status 를 뽑는다. 행 부재는
    status='missing'(정직 부재). gen_no = pairs 순서 인덱스(배치 기록 규약).
    """
    uri = Path(loop_runs_db).resolve().as_uri() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    con.row_factory = sqlite3.Row
    out: Dict[str, Dict] = {}
    try:
        for gen_no, pair in enumerate(pairs):
            row = con.execute(
                "SELECT * FROM generations WHERE run_id=? AND gen_no=?",
                (run_id, gen_no)).fetchone()
            label = pair.get("label", f"pair{gen_no}")
            cand = label.replace("X1_", "")
            if row is None:
                out[cand] = {"status": "missing", "label": label}
                continue
            d = dict(row)
            out[cand] = {
                "status": str(d.get("status") or "error"),
                "metrics": {
                    "total_profit_krw": float(d.get("profit") or 0.0),
                    "trade_count": int(d.get("trade_count") or 0),
                    "mdd_pct": float(d.get("mdd") or 0.0),
                    "total_profit_pct": float(d.get("total_profit_pct") or 0.0),
                    "daily_avg_trades": float(d.get("daily_avg_trades") or 0.0),
                },
                "label": label, "buy": pair.get("buy"), "sell": pair.get("sell"),
            }
    finally:
        con.close()
    return out


def batch_command(pairs_json: str, config_json: str, run_id: str) -> List[str]:
    """run phase 가 subprocess 로 돌릴 배치 명령(문서화 — 여기서 실행하지 않음)."""
    return [
        "python", "-m", "ai_strategy_loop.scripts.claude_candidate_batch_eval",
        "--pairs-json", pairs_json, "--config-json", config_json,
        "--run-id", run_id,
    ]
