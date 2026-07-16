"""stage1_cell_decomposition -- Stage-1 per-trade CSV의 결정론적 12-cell 분해 (G005).

이 모듈은 순수 분해/발행 헬퍼 집합이다. 백테스트를 재실행하지 않고, DB에
쓰지 않으며, ``cli.wide_seed_trial_planner.TrialSpecV1``/``cli.wide_seed_v1.LEAF_CELLS``
가 정의한 12개 리프 셀(시간창 3 x 시가총액 밴드 4) 경계를 이미 실행된
per-trade 백테스트 CSV에 적용해 셀별 집계를 만들고, 그 결과를
``cli.condition_history_schema`` 의 ``condition_history_v1`` 트리로 투영해
``cli.research_history_projection.publish_condition_history`` 로 발행한다.

절대 하지 않는 것:
  - 백테스트 재실행 또는 서브프로세스 호출 (입력은 이미 생성된 CSV).
  - 운영/루프 DB에 쓰기.
  - 셀 경계(윈도우/캡) 값을 CSV 데이터로부터 추측/재계산 -- 항상
    ``TrialSpecV1.cell_metadata`` (즉 ``LEAF_CELLS``) 의 동결된 값만 사용한다.

CSV 컬럼 관용(tolerance):
  - 필수로 취급하는 컬럼은 ``매수시간`` / ``시가총액`` 뿐이다. 나머지
    (``종목명``, ``종목코드``, ``매도시간``, ``수익률``, ``수익금``) 는 있으면
    쓰고 없으면 해당 지표만 ``None`` 으로 비워둔다 -- 열이 없다고 CSV 전체를
    거부하지 않는다.
  - ``매수시간`` 형식: 14자리 정수/문자열(``YYYYMMDDHHMMSS``, 뒤 6자리를
    HHMMSS로 사용) 또는 ``YYYY-MM-DD HH:MM:SS`` 문자열을 허용한다. 그 외
    형식/결측은 unassigned 로 보내고 사유를 남긴다.
  - ``시가총액``: 억원 단위 스칼라(정수/실수). 결측/비수치/음수는 unassigned.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from cli.condition_history_schema import (
    ConditionNode,
    EvaluationNode,
    ResearchNode,
    StageNode,
    validate_research_node,
)
from cli.research_history_projection import publish_condition_history
from cli.wide_seed_trial_planner import TrialSpecV1

#: 12-cell 분해에 필요한 필수 per-trade CSV 컬럼 -- 없으면 모든 행이 unassigned.
REQUIRED_TRADE_COLUMNS: tuple[str, ...] = ("매수시간", "시가총액")

#: 종목 식별 컬럼 -- 선호 순서(``종목코드`` 우선, 없으면 ``종목명``).
_SYMBOL_ID_COLUMNS: tuple[str, ...] = ("종목코드", "종목명")

#: 발행 캠페인 이름 -- ``publish_condition_history`` 파일명에 그대로 쓰인다.
CAMPAIGN_NAME = "wide_seed_v1_stage1"

#: 이 모듈이 만드는 ``ResearchNode.research_id`` 고정값.
RESEARCH_ID = "campaign:wide_seed_v1_stage1"

#: 이 모듈이 만드는 단일 ``StageNode.stage_id`` 고정값.
STAGE_ID = "stage1_exploratory_full_history"

#: unassigned 사유 라벨 -- 순서는 우선순위(먼저 매칭되는 사유가 채택됨)를 뜻한다.
REASON_MISSING_BUY_TIME = "missing_buy_time"
REASON_UNPARSEABLE_BUY_TIME = "unparseable_buy_time"
REASON_BUY_TIME_OUT_OF_WINDOW = "buy_time_out_of_window"
REASON_MISSING_CAP = "missing_cap"
REASON_INVALID_CAP = "invalid_cap"
REASON_CAP_OUT_OF_BAND = "cap_out_of_band"

_ISO_DATETIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[ T](\d{2}):(\d{2}):(\d{2})"
)


# ---------------------------------------------------------------------------
# 파싱 헬퍼 -- 순수 함수.
# ---------------------------------------------------------------------------


def _parse_buy_hhmmss(raw: Any) -> Optional[int]:
    """``매수시간`` 원시값에서 HHMMSS 정수를 뽑아낸다. 실패하면 ``None``.

    허용 형식:
      - 14자리 ``YYYYMMDDHHMMSS`` (tick 레인, 뒤 6자리를 HHMMSS로 사용)
      - 12자리 ``YYYYMMDDHHMM`` (min 레인, 분 해상도 -- 뒤 4자리를 HHMM으로
        읽어 초 00을 붙인다; 실측 min per-trade CSV가 이 형식이다)
      - ``YYYY-MM-DD HH:MM[:SS]`` 문자열
    정수/부동소수/문자열 모두 허용하며, 그 외 형식/결측은 ``None``.
    """

    if raw is None:
        return None
    if isinstance(raw, float) and pd.isna(raw):
        return None

    text = str(raw).strip()
    if not text or text.lower() == "nan":
        return None

    match = _ISO_DATETIME_RE.match(text)
    if match:
        hh, mm, ss = match.groups()
        try:
            hhmmss = int(hh) * 10000 + int(mm) * 100 + int(ss)
        except ValueError:
            return None
        if 0 <= hhmmss <= 235959:
            return hhmmss
        return None

    digits = text
    if digits.endswith(".0"):
        digits = digits[:-2]
    if not digits.isdigit():
        return None
    if len(digits) == 12:
        # min 레인: YYYYMMDDHHMM -- 뒤 4자리(HHMM)에 초 00을 붙인다.
        hhmm_str = digits[-4:]
        try:
            hhmm = int(hhmm_str)
        except ValueError:
            return None
        hh, mm = divmod(hhmm, 100)
        if hh > 23 or mm > 59:
            return None
        return hhmm * 100
    if len(digits) < 6:
        return None
    hhmmss_str = digits[-6:]
    try:
        hhmmss = int(hhmmss_str)
    except ValueError:
        return None
    hh, rem = divmod(hhmmss, 10000)
    mm, ss = divmod(rem, 100)
    if hh > 23 or mm > 59 or ss > 59:
        return None
    return hhmmss


def _parse_cap(raw: Any) -> Optional[float]:
    """``시가총액`` 원시값을 억원 단위 실수로 강제 변환한다. 실패하면 ``None``."""

    if raw is None:
        return None
    if isinstance(raw, float) and pd.isna(raw):
        return None
    text = str(raw).strip()
    if not text or text.lower() == "nan":
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    return value


def _match_cell(hhmmss: int, cap: float, cells: tuple[dict[str, Any], ...]) -> Optional[dict[str, Any]]:
    """(hhmmss, cap) 쌍이 속하는 셀 메타데이터를 반환한다. 없으면 ``None``."""

    for cell in cells:
        if not (cell["window_lo"] <= hhmmss < cell["window_hi"]):
            continue
        cap_lo = cell["cap_lo"]
        cap_hi = cell["cap_hi"]
        if cap < cap_lo:
            continue
        if cap_hi is not None and cap >= cap_hi:
            continue
        return cell
    return None


def _symbol_id(row: pd.Series, columns: list[str]) -> Optional[str]:
    """``종목코드`` 우선, 없으면 ``종목명`` 값을 문자열로 반환한다 (둘 다 결측이면 ``None``)."""

    for column in _SYMBOL_ID_COLUMNS:
        if column not in columns:
            continue
        value = row.get(column)
        if value is None:
            continue
        if isinstance(value, float) and pd.isna(value):
            continue
        text = str(value).strip()
        if text and text.lower() != "nan":
            return text
    return None


def _classify_pnl(row: pd.Series, columns: list[str]) -> Optional[str]:
    """행 하나를 ``수익률`` 우선(없으면 ``수익금``)으로 승/패/보합 분류한다.

    두 컬럼 모두 결측/비수치이면 분류 불가(``None``)로 남긴다 -- 이 경우
    trade_count에는 포함되지만 winning/losing/breakeven 어느 쪽에도 더해지지
    않는다(허구 데이터 생성 금지).
    """

    for column in ("수익률", "수익금"):
        if column not in columns:
            continue
        raw = row.get(column)
        if raw is None:
            continue
        if isinstance(raw, float) and pd.isna(raw):
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if value > 0:
            return "winning"
        if value < 0:
            return "losing"
        return "breakeven"
    return None


def _numeric_or_none(row: pd.Series, column: str, columns: list[str]) -> Optional[float]:
    if column not in columns:
        return None
    raw = row.get(column)
    if raw is None:
        return None
    if isinstance(raw, float) and pd.isna(raw):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# decompose_cells -- CSV -> 12-cell 집계 (+ unassigned).
# ---------------------------------------------------------------------------


def _empty_cell_accumulator(cell_meta: dict[str, Any]) -> dict[str, Any]:
    return {
        **{k: cell_meta[k] for k in ("lane", "window_label", "window_lo", "window_hi", "cap_lo", "cap_hi", "ordinal")},
        "trade_count": 0,
        "symbol_ids": set(),
        "symbol_column_seen": False,
        "winning_count": 0,
        "losing_count": 0,
        "breakeven_count": 0,
        "gross_profit": 0.0,
        "gross_loss": 0.0,
        "profit_seen": False,
    }


def _finalize_cell(acc: dict[str, Any]) -> dict[str, Any]:
    trade_count = acc["trade_count"]
    traded_symbol_count = len(acc["symbol_ids"]) if acc["symbol_column_seen"] else None
    if acc["profit_seen"]:
        gross_profit = acc["gross_profit"]
        gross_loss = acc["gross_loss"]
        net_profit = gross_profit + gross_loss
    else:
        gross_profit = None
        gross_loss = None
        net_profit = None
    win_rate = (acc["winning_count"] / trade_count) if trade_count > 0 else None
    return {
        "lane": acc["lane"],
        "window_label": acc["window_label"],
        "window_lo": acc["window_lo"],
        "window_hi": acc["window_hi"],
        "cap_lo": acc["cap_lo"],
        "cap_hi": acc["cap_hi"],
        "ordinal": acc["ordinal"],
        "trade_count": trade_count,
        "traded_symbol_count": traded_symbol_count,
        "winning_count": acc["winning_count"],
        "losing_count": acc["losing_count"],
        "breakeven_count": acc["breakeven_count"],
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "net_profit": net_profit,
        "win_rate": win_rate,
    }


def decompose_cells(csv_path: str | Path, spec: TrialSpecV1) -> dict:
    """per-trade CSV 1건을 ``spec`` 의 12개 리프 셀로 결정론적으로 분해한다.

    각 행은 ``window_lo <= HHMMSS < window_hi`` 와 ``cap_lo <= 시가총액 < cap_hi``
    (``cap_hi is None`` 이면 상한 없음) 를 모두 만족하는 셀 정확히 1개에
    배정되거나, 배정 불가 사유와 함께 ``unassigned`` 버킷에 명시적으로
    쌓인다 -- 절대 조용히 버려지지 않고, 절대 0-cap(``cap_lo==0``) 셀로
    잘못 집계되지 않는다.

    Returns:
        ``cells``(ordinal 순 12개 dict), ``unassigned``(count/reasons),
        ``totals``(12개 셀 합산), ``total_rows``, ``parity_ok`` 키를 갖는 dict.
    """

    csv_path = Path(csv_path)
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    columns = list(df.columns)

    cells = list(spec.cell_metadata)
    accumulators = {cell["ordinal"]: _empty_cell_accumulator(cell) for cell in cells}

    unassigned_count = 0
    unassigned_reasons: dict[str, int] = {}

    has_buy_time_col = "매수시간" in columns
    has_cap_col = "시가총액" in columns

    for _, row in df.iterrows():
        reason: Optional[str] = None
        hhmmss: Optional[int] = None
        cap: Optional[float] = None

        if not has_buy_time_col:
            reason = REASON_MISSING_BUY_TIME
        else:
            raw_time = row.get("매수시간")
            hhmmss = _parse_buy_hhmmss(raw_time)
            if hhmmss is None:
                text = "" if raw_time is None else str(raw_time).strip()
                if not text or text.lower() == "nan":
                    reason = REASON_MISSING_BUY_TIME
                else:
                    reason = REASON_UNPARSEABLE_BUY_TIME

        if reason is None:
            if not has_cap_col:
                reason = REASON_MISSING_CAP
            else:
                raw_cap = row.get("시가총액")
                cap = _parse_cap(raw_cap)
                if cap is None:
                    text = "" if raw_cap is None else str(raw_cap).strip()
                    if not text or text.lower() == "nan":
                        reason = REASON_MISSING_CAP
                    else:
                        reason = REASON_INVALID_CAP

        matched_cell: Optional[dict[str, Any]] = None
        if reason is None:
            assert hhmmss is not None and cap is not None
            in_any_window = any(cell["window_lo"] <= hhmmss < cell["window_hi"] for cell in cells)
            if not in_any_window:
                reason = REASON_BUY_TIME_OUT_OF_WINDOW
            elif cap < 0:
                reason = REASON_CAP_OUT_OF_BAND
            else:
                matched_cell = _match_cell(hhmmss, cap, tuple(cells))
                if matched_cell is None:
                    reason = REASON_CAP_OUT_OF_BAND

        if reason is not None:
            unassigned_count += 1
            unassigned_reasons[reason] = unassigned_reasons.get(reason, 0) + 1
            continue

        acc = accumulators[matched_cell["ordinal"]]
        acc["trade_count"] += 1

        symbol_column_present = any(col in columns for col in _SYMBOL_ID_COLUMNS)
        if symbol_column_present:
            acc["symbol_column_seen"] = True
            symbol_id = _symbol_id(row, columns)
            if symbol_id is not None:
                acc["symbol_ids"].add(symbol_id)

        pnl_class = _classify_pnl(row, columns)
        if pnl_class == "winning":
            acc["winning_count"] += 1
        elif pnl_class == "losing":
            acc["losing_count"] += 1
        elif pnl_class == "breakeven":
            acc["breakeven_count"] += 1

        profit_amount = _numeric_or_none(row, "수익금", columns)
        if profit_amount is not None:
            acc["profit_seen"] = True
            if profit_amount >= 0:
                acc["gross_profit"] += profit_amount
            else:
                acc["gross_loss"] += profit_amount

    finalized_cells = [_finalize_cell(accumulators[cell["ordinal"]]) for cell in sorted(cells, key=lambda c: c["ordinal"])]

    total_trade_count = sum(c["trade_count"] for c in finalized_cells)
    total_winning = sum(c["winning_count"] for c in finalized_cells)
    total_losing = sum(c["losing_count"] for c in finalized_cells)
    total_breakeven = sum(c["breakeven_count"] for c in finalized_cells)

    profit_cells = [c for c in finalized_cells if c["gross_profit"] is not None]
    if profit_cells:
        total_gross_profit = sum(c["gross_profit"] for c in profit_cells)
        total_gross_loss = sum(c["gross_loss"] for c in profit_cells)
        total_net_profit = total_gross_profit + total_gross_loss
    else:
        total_gross_profit = None
        total_gross_loss = None
        total_net_profit = None

    symbol_cells = [c for c in finalized_cells if c["traded_symbol_count"] is not None]
    if symbol_cells:
        # 셀 경계는 서로소이므로 셀 간 종목 중복 가능성이 있어 단순 합산 대신
        # CSV 전체에서 다시 유일값을 센다 (심볼 컬럼이 하나라도 있었던 경우만).
        symbol_column_present = any(col in columns for col in _SYMBOL_ID_COLUMNS)
        if symbol_column_present:
            preferred_column = next((c for c in _SYMBOL_ID_COLUMNS if c in columns), None)
            total_traded_symbol_count = int(df[preferred_column].dropna().astype(str).str.strip().replace({"": None, "nan": None}).dropna().nunique())
        else:
            total_traded_symbol_count = None
    else:
        total_traded_symbol_count = None

    total_win_rate = (total_winning / total_trade_count) if total_trade_count > 0 else None

    totals = {
        "trade_count": total_trade_count,
        "traded_symbol_count": total_traded_symbol_count,
        "winning_count": total_winning,
        "losing_count": total_losing,
        "breakeven_count": total_breakeven,
        "gross_profit": total_gross_profit,
        "gross_loss": total_gross_loss,
        "net_profit": total_net_profit,
        "win_rate": total_win_rate,
    }

    total_rows = int(len(df))
    parity_ok = (total_trade_count + unassigned_count) == total_rows

    return {
        "lane": spec.lane,
        "csv_path": str(csv_path),
        "total_rows": total_rows,
        "cells": finalized_cells,
        "unassigned": {
            "count": unassigned_count,
            "reasons": unassigned_reasons,
        },
        "totals": totals,
        "parity_ok": parity_ok,
    }


# ---------------------------------------------------------------------------
# cells_to_history_evaluations -- 분해 결과 -> condition_history_v1 ResearchNode.
# ---------------------------------------------------------------------------


def _metrics_from_cell(cell: dict[str, Any]) -> dict[str, Optional[float]]:
    metric_keys = (
        "trade_count",
        "traded_symbol_count",
        "winning_count",
        "losing_count",
        "breakeven_count",
        "gross_profit",
        "gross_loss",
        "net_profit",
        "win_rate",
    )
    metrics: dict[str, Optional[float]] = {}
    for key in metric_keys:
        value = cell.get(key)
        metrics[key] = None if value is None else float(value)
    return metrics


def _evaluation_status(trade_count: int) -> str:
    return "success" if trade_count > 0 else "no_trades"


def _condition_id(spec: TrialSpecV1, suffix: str) -> str:
    return f"{spec.trial_id}:{suffix}"


def _stage_coverage_status(condition_statuses: list[str]) -> str:
    """조건 상태 목록으로부터 스테이지/연구 레벨 coverage_status를 결정한다.

    하나라도 ``success`` 면 ``success``, 전부 ``no_trades`` 면 ``no_trades``,
    그 외(알 수 없는 상태 혼재)는 첫 상태를 그대로 승격한다.
    """

    if "success" in condition_statuses:
        return "success"
    if condition_statuses and all(status == "no_trades" for status in condition_statuses):
        return "no_trades"
    return condition_statuses[0] if condition_statuses else "no_trades"


def cells_to_history_evaluations(
    cells: dict,
    spec: TrialSpecV1,
    csv_path: str | Path,
    csv_sha256: str,
) -> ResearchNode:
    """``decompose_cells`` 결과를 ``condition_history_v1`` ``ResearchNode`` 로 투영한다.

    조건(condition) 노드는 리프 셀 12개 + 통합 페어 전체(overall) 1개로 총
    13개이며, 각 조건은 평가(evaluation) 노드 정확히 1개를 갖는다. 결과
    역할은 항상 탐색적(exploratory)이며 -- 어떤 승격/의사결정 신호로도
    쓰이지 않는다.
    """

    evaluations_by_condition: list[ConditionNode] = []

    for cell in cells["cells"]:
        ordinal = cell["ordinal"]
        condition_id = _condition_id(spec, f"cell:{ordinal:02d}")
        status = _evaluation_status(cell["trade_count"])
        evaluation: EvaluationNode = {
            "evaluation_id": f"{condition_id}:eval",
            "condition_id": condition_id,
            "status": status,
            "metrics": _metrics_from_cell(cell),
        }
        condition: ConditionNode = {
            "condition_id": condition_id,
            "stage_id": STAGE_ID,
            "label": f"{spec.lane}:{cell['window_label']}:cap[{cell['cap_lo']},{cell['cap_hi']})",
            "coverage_status": status,
            "evaluations": [evaluation],
        }
        evaluations_by_condition.append(condition)

    overall_condition_id = _condition_id(spec, "overall")
    overall_status = _evaluation_status(cells["totals"]["trade_count"])
    overall_metrics = _metrics_from_cell(cells["totals"])
    overall_metrics["unassigned_count"] = float(cells["unassigned"]["count"])
    overall_metrics["total_rows"] = float(cells["total_rows"])
    overall_metrics["parity_ok"] = 1.0 if cells["parity_ok"] else 0.0
    for reason, count in sorted(cells["unassigned"]["reasons"].items()):
        overall_metrics[f"unassigned_reason_{reason}"] = float(count)

    overall_evaluation: EvaluationNode = {
        "evaluation_id": f"{overall_condition_id}:eval",
        "condition_id": overall_condition_id,
        "status": overall_status,
        "metrics": overall_metrics,
    }
    overall_condition: ConditionNode = {
        "condition_id": overall_condition_id,
        "stage_id": STAGE_ID,
        "label": f"{spec.lane}:unified_wide_pair:overall",
        "coverage_status": overall_status,
        "evaluations": [overall_evaluation],
    }
    evaluations_by_condition.append(overall_condition)

    condition_statuses = [c["coverage_status"] for c in evaluations_by_condition]
    stage_status = _stage_coverage_status(condition_statuses)

    stage: StageNode = {
        "stage_id": STAGE_ID,
        "research_id": RESEARCH_ID,
        "label": "Stage-1 탐색적 전체 히스토리 12-cell 분해",
        "coverage_status": stage_status,
        "conditions": evaluations_by_condition,
    }

    research: ResearchNode = {
        "research_id": RESEARCH_ID,
        "label": f"Stage-1 12-cell 분해 -- {spec.lane} lane ({spec.trial_id})",
        "coverage_status": stage_status,
        "stages": [stage],
    }

    errors = validate_research_node(research)
    if errors:
        raise ValueError(f"assembled ResearchNode failed validation: {errors}")

    return research


def compute_csv_sha256(csv_path: str | Path) -> str:
    """CSV 파일 바이트의 sha256 16진 다이제스트를 계산한다 (provenance용)."""

    digest = hashlib.sha256()
    with open(csv_path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# publish_stage1 -- ResearchNode -> 증거 디렉터리 발행.
# ---------------------------------------------------------------------------


def publish_stage1(cells_node: ResearchNode, evidence_dir: str | Path) -> Path:
    """``cells_node`` (``ResearchNode``) 를 ``evidence_dir`` 에 원자적으로 발행한다.

    캠페인 이름은 항상 ``wide_seed_v1_stage1`` 로 고정되며, 실제 파일 쓰기는
    ``cli.research_history_projection.publish_condition_history`` 에 위임한다
    (이 모듈은 별도 쓰기 경로를 만들지 않는다).
    """

    errors = validate_research_node(cells_node)
    if errors:
        raise ValueError(f"refusing to publish invalid ResearchNode: {errors}")

    return publish_condition_history(CAMPAIGN_NAME, dict(cells_node), Path(evidence_dir))


__all__ = [
    "CAMPAIGN_NAME",
    "RESEARCH_ID",
    "STAGE_ID",
    "REQUIRED_TRADE_COLUMNS",
    "REASON_MISSING_BUY_TIME",
    "REASON_UNPARSEABLE_BUY_TIME",
    "REASON_BUY_TIME_OUT_OF_WINDOW",
    "REASON_MISSING_CAP",
    "REASON_INVALID_CAP",
    "REASON_CAP_OUT_OF_BAND",
    "decompose_cells",
    "cells_to_history_evaluations",
    "publish_stage1",
    "compute_csv_sha256",
]
