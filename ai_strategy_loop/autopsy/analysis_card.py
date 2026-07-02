"""Analysis Card v2 생산자 — 거래행 + ablation 근거를 하나의 연구 분석 카드로 만든다.

build_analysis_card(result_meta, trades_df, ablation_result=None) 가 카드(dict,
schema='analysis_card_v2')를 만든다. 섹션: metrics(공식 지표), segment_heatmap
(시간대×시가총액 — segment.analyze_segments 재사용), mfe_mae, edge_ratio(평균
MFE/평균|MAE|), feature_importance(승/패 Cohen's d — analyze.analyze_trades
재사용, FDR 포함), avoid_zones/prefer_zones(손실/이익 집중 세그먼트),
correlation_redundancy(B_* 상관 쌍 + ablation 절 자카드 중복), root_cause
(ablation harmful/ineffective 절 + 세그먼트 손실 집중 결합, 1~3개),
mutation_axis(root-cause 파생 변이축), risk_note.

[정직 라벨 계약] 모든 분석 섹션은 "status" 필드를 가진 dict 다:
'ok' | 'insufficient_data'. 입력 데이터가 없으면 빈 값을 조작하지 않고
'insufficient_data' + 사유(note)로 정직하게 표시한다.

[권한 계약] 카드는 연구 분석 전용(authority='research_analysis_card_only')이다.
result_meta 에 승격/실전 권한 키(can_promote 등)가 truthy 면 ValueError
(권한 밀반입 가드 — condition_discovery 카드 계약과 동일).

기존 autopsy 모듈(analyze/segment)은 읽기 전용 import 소비만 한다(수정 금지).
데이터 모양 문제로는 예외를 던지지 않는다(autopsy 관례 — 섹션 status 로 반환).
"""

from __future__ import annotations

import io
import json
import math
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import pandas as pd

# 읽기 전용 import 소비 — 기존 autopsy 분석기 재사용(수정 금지 계약).
from ai_strategy_loop.autopsy import analyze as _analyze
from ai_strategy_loop.autopsy import segment as _segment
from ai_strategy_loop.autopsy.ablation import (
    ABLATION_STATUS_OK, EVAL_STATUS_OK, REDUNDANCY_SUGGEST_THRESHOLD,
    VERDICT_HARMFUL, AblationResult, ClauseAblation, to_mutation_axis_suggestions,
)

# 카드 스키마/권한 — condition_discovery 의 RESEARCH_ANALYSIS_CARD_VERSION 과 동일 문자열.
ANALYSIS_CARD_SCHEMA = "analysis_card_v2"
CARD_AUTHORITY = "research_analysis_card_only"

# 섹션 status — 정직 라벨 계약.
SECTION_OK = "ok"
SECTION_INSUFFICIENT = "insufficient_data"

# 권한 밀반입 가드 — result_meta 에 truthy 로 들어오면 ValueError.
FORBIDDEN_AUTHORITY_KEYS = ("can_promote", "can_export", "can_live", "promotion_eligible")

# MFE/MAE 컬럼 후보(정본 R_매수후최고/최저수익률 우선, R_MFE/R_MAE 폴백).
MFE_COLUMN_CANDIDATES = (_analyze.MFE_COLUMN, "R_MFE")
MAE_COLUMN_CANDIDATES = (_analyze.MAE_COLUMN, "R_MAE")

# 섹션별 상위 노출 개수(토큰 폭증 방지)와 근사/판정 상수.
TOP_FEATURES = 8
TOP_ZONES = 3
MAX_ROOT_CAUSES = 3
_CORR_THRESHOLD = 0.9   # B_* 변수 상관 중복 판정 임계.
_CORR_MIN_ROWS = 5      # 상관 계산 최소 공동 표본.
_ROUND = 6

# result_meta 지표 별칭 — 카드에 실리는 키는 이 화이트리스트뿐이다(임의 키 복사 금지).
_METRIC_ALIASES: Mapping[str, Tuple[str, ...]] = {
    "profit": ("profit", "total_profit", "수익금합계", "총수익금", "수익금"),
    "mdd": ("mdd", "MDD", "max_drawdown", "최대낙폭"),
    "trades": ("trades", "trade_count", "total_trades", "거래횟수", "매매횟수"),
    "win_rate": ("win_rate", "winrate", "승률"),
    "payoff": ("payoff", "payoff_ratio", "손익비"),
}

# 카드 작업 사본에서 숫자로 강제할 컬럼 후보.
_NUMERIC_CANDIDATES = (
    _analyze.RETURN_COLUMN, "수익금", _analyze.HOLD_COLUMN,
) + MFE_COLUMN_CANDIDATES + MAE_COLUMN_CANDIDATES


# ---------------------------------------------------------------------------
# 공통 헬퍼
# ---------------------------------------------------------------------------

def _safe_number(value: Any, digits: int = _ROUND) -> Optional[float]:
    """JSON-안전 숫자 변환. 비유한/변환불가 값은 None(조작 금지)."""
    if value is None or isinstance(value, bool):
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(num):
        return None
    return round(num, digits)


def _fmt(value: Any) -> str:
    """사람용 숫자/값 표기. None 은 'N/A' 로 정직 표기."""
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return format(value, "g")
    return str(value)


def _mean_or_none(series: pd.Series) -> Optional[float]:
    values = series.dropna()
    return _safe_number(float(values.mean())) if len(values) else None


def _pick_column(frame: pd.DataFrame, candidates: Sequence[str]) -> Optional[str]:
    for column in candidates:
        if column in frame.columns:
            return column
    return None


def _working_frame(trades_df: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
    """원본 불변 작업 사본. 0행/None 은 None(섹션들이 insufficient 로 라벨)."""
    if trades_df is None or not isinstance(trades_df, pd.DataFrame) or len(trades_df) == 0:
        return None
    frame = trades_df.copy()
    for column in _NUMERIC_CANDIDATES:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def _guard_authority(result_meta: Optional[Mapping[str, Any]]) -> None:
    """권한 밀반입 가드 — 승격/실전 권한 키가 truthy 면 계약 위반(ValueError)."""
    if not isinstance(result_meta, Mapping):
        return
    for key in FORBIDDEN_AUTHORITY_KEYS:
        if result_meta.get(key):
            raise ValueError("analysis_card_forbidden_authority_key:%s" % key)


def _insufficient(note: str, **extra: Any) -> Dict[str, Any]:
    """insufficient_data 섹션 dict — 사유(note)를 항상 싣는다."""
    return {"status": SECTION_INSUFFICIENT, "note": note, **extra}


# ---------------------------------------------------------------------------
# 섹션 빌더 — 전부 {"status": ...} 를 가진 dict 를 돌려준다(무예외).
# ---------------------------------------------------------------------------

def _build_metrics_section(result_meta: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """공식 결과 지표(profit/MDD/trades/win/payoff)를 별칭 화이트리스트로 추출."""
    if not isinstance(result_meta, Mapping) or not result_meta:
        return _insufficient("result_meta 없음 — 공식 지표를 실을 수 없다.",
                             values={}, missing=list(_METRIC_ALIASES))
    values: Dict[str, Optional[float]] = {}
    missing: List[str] = []
    for metric, aliases in _METRIC_ALIASES.items():
        resolved: Optional[float] = None
        for alias in aliases:
            if alias in result_meta:
                resolved = _safe_number(result_meta[alias])
                if resolved is not None:
                    break
        if resolved is None:
            missing.append(metric)
        else:
            values[metric] = int(resolved) if metric == "trades" else resolved
    if not values:
        return _insufficient("result_meta 에서 인식 가능한 지표가 없다.",
                             values={}, missing=missing)
    note = "공식 지표 %d/%d개 추출." % (len(values), len(_METRIC_ALIASES))
    if missing:
        note += " 미제공: %s." % ", ".join(missing)
    return {"status": SECTION_OK, "values": values, "missing": missing, "note": note}


def _run_segment_analysis(
    frame: Optional[pd.DataFrame], *, min_trades: int,
    segment_min_samples: int, fine_time: bool,
) -> Tuple[Optional[_segment.SegmentAutopsyResult], Optional[str]]:
    """segment.analyze_segments 재사용 호출(무예외 — 실패는 사유 문자열로)."""
    if frame is None:
        return None, "거래행 없음(0건)."
    try:
        result = _segment.analyze_segments(
            frame, min_trades=min_trades,
            segment_min_samples=segment_min_samples, fine_time=fine_time,
        )
    except Exception as exc:  # noqa: BLE001 - 데이터 모양 문제는 라벨로 흡수.
        return None, "세그먼트 분석 실패: %s" % exc
    return result, None


def _segment_row(seg: "_segment.SegmentStat") -> Dict[str, Any]:
    return {
        "label": seg.label, "axis": seg.axis, "count": int(seg.count),
        "avg_return": _safe_number(seg.avg_return), "win_rate": _safe_number(seg.win_rate),
        "avg_mae": _safe_number(seg.avg_mae), "total_profit": _safe_number(seg.total_profit),
        "return_diff": _safe_number(seg.return_diff),
    }


def _threshold_row(thr: "_segment.ThresholdStat") -> Dict[str, Any]:
    return {
        "feature": thr.feature, "stom_var": thr.stom_var, "operator": thr.operator,
        "threshold": _safe_number(thr.threshold),
        "lower_bound": _safe_number(thr.lower_bound),
        "upper_bound": _safe_number(thr.upper_bound),
        "count": int(thr.count), "mean_return": _safe_number(thr.mean_return),
        "win_rate": _safe_number(thr.win_rate), "source": thr.source,
    }


def _build_heatmap_section(
    seg_result: Optional[_segment.SegmentAutopsyResult], seg_error: Optional[str],
) -> Dict[str, Any]:
    """시간대×시가총액 히트맵 — 교차 셀 전체 + 단축 세그먼트 + 데이터구동 임계값."""
    if seg_result is None:
        return _insufficient(seg_error or "거래행 없음(0건).", cells=[])
    if seg_result.status != _analyze.STATUS_OK:
        return _insufficient(seg_result.note or seg_result.status, cells=[])
    return {
        "status": SECTION_OK,
        "trade_count": int(seg_result.trade_count),
        "overall_avg_return": _safe_number(seg_result.overall_avg_return),
        "overall_win_rate": _safe_number(seg_result.overall_win_rate),
        "time_segments": [_segment_row(s) for s in seg_result.time_segments],
        "market_cap_segments": [_segment_row(s) for s in seg_result.market_cap_segments],
        "cells": [_segment_row(s) for s in seg_result.cross_segments],
        "thresholds": [_threshold_row(t) for t in seg_result.thresholds],
        "note": seg_result.note,
    }


def _build_zone_sections(
    seg_result: Optional[_segment.SegmentAutopsyResult], seg_error: Optional[str],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """손실 집중(avoid) / 이익 집중(prefer) 세그먼트 상위 — 교차 셀 우선."""
    if seg_result is None or seg_result.status != _analyze.STATUS_OK:
        note = seg_error or (seg_result.note if seg_result is not None else "거래행 없음(0건).")
        return (_insufficient(note, zone_axis=None, zones=[]),
                _insufficient(note, zone_axis=None, zones=[]))
    if seg_result.cross_segments:
        pool, zone_axis = list(seg_result.cross_segments), "cross"
    else:
        pool = list(seg_result.time_segments) + list(seg_result.market_cap_segments)
        zone_axis = "single"
    avoid = sorted((s for s in pool if s.return_diff < 0), key=lambda s: s.return_diff)[:TOP_ZONES]
    prefer = sorted((s for s in pool if s.return_diff > 0), key=lambda s: -s.return_diff)[:TOP_ZONES]
    avoid_section = {
        "status": SECTION_OK, "zone_axis": zone_axis,
        "zones": [_segment_row(s) for s in avoid],
        "note": ("손실 집중 세그먼트 %d개(전체 대비 return_diff<0)." % len(avoid))
        if avoid else "손실 집중 세그먼트 없음(전 셀 return_diff>=0).",
    }
    prefer_section = {
        "status": SECTION_OK, "zone_axis": zone_axis,
        "zones": [_segment_row(s) for s in prefer],
        "note": ("이익 집중 세그먼트 %d개(전체 대비 return_diff>0)." % len(prefer))
        if prefer else "이익 집중 세그먼트 없음(전 셀 return_diff<=0).",
    }
    return avoid_section, prefer_section


def _build_feature_importance_section(
    frame: Optional[pd.DataFrame], min_trades: int,
) -> Dict[str, Any]:
    """승/패 Cohen's d — analyze.analyze_trades 재사용(FDR 보정 포함).

    analyze_trades 는 CSV 경로/버퍼를 받으므로 utf-8-sig 바이트 버퍼로 왕복해
    로직(정렬·분위수·BH-FDR)을 그대로 재사용한다(재발명 금지).
    """
    if frame is None:
        return _insufficient("거래행 없음(0건).", features=[])
    try:
        buffer = io.BytesIO(frame.to_csv(index=False).encode("utf-8-sig"))
        result = _analyze.analyze_trades(buffer, min_trades=min_trades)
    except Exception as exc:  # noqa: BLE001 - 데이터 모양 문제는 라벨로 흡수.
        return _insufficient("피처 중요도 산출 실패: %s" % exc, features=[])
    if result.status != _analyze.STATUS_OK:
        return _insufficient(result.note or result.status, features=[])
    features = [
        {
            "feature": d.column,
            "stom_var": _analyze.B_TO_STOM_VAR.get(d.column, d.column),
            "win_mean": _safe_number(d.win_mean), "loss_mean": _safe_number(d.loss_mean),
            "cohens_d": _safe_number(d.std_mean_diff), "win_q50": _safe_number(d.win_q50),
            "p_value": _safe_number(d.p_value), "q_value": _safe_number(d.q_value),
            "fdr_pass": None if d.fdr_pass is None else bool(d.fdr_pass),
        }
        for d in result.discriminators[:TOP_FEATURES]
    ]
    if not features:
        return _insufficient("분석 가능한 B_* 컬럼이 없다.", features=[])
    return {
        "status": SECTION_OK, "features": features,
        "win_count": int(result.win_count), "loss_count": int(result.loss_count),
        "note": result.note,
    }


def _build_mfe_mae_section(frame: Optional[pd.DataFrame]) -> Dict[str, Any]:
    """MFE/MAE 요약 — give-back(수익거래 고점 반납)과 adverse excursion(손실 깊이)."""
    if frame is None:
        return _insufficient("거래행 없음(0건).")
    mfe_col = _pick_column(frame, MFE_COLUMN_CANDIDATES)
    mae_col = _pick_column(frame, MAE_COLUMN_CANDIDATES)
    if mfe_col is None and mae_col is None:
        return _insufficient("MFE/MAE 컬럼 없음(%s / %s)." % (
            "|".join(MFE_COLUMN_CANDIDATES), "|".join(MAE_COLUMN_CANDIDATES)))
    if _analyze.RETURN_COLUMN not in frame.columns:
        return _insufficient("수익률 컬럼 없음 — 승/패 분리 불가.")
    returns = pd.to_numeric(frame[_analyze.RETURN_COLUMN], errors="coerce")
    valid = returns.notna()
    if int(valid.sum()) == 0:
        return _insufficient("유효 수익률 행 0건.")
    is_win = valid & (returns > 0)
    is_loss = valid & (returns <= 0)

    section: Dict[str, Any] = {
        "status": SECTION_OK, "mfe_column": mfe_col, "mae_column": mae_col,
        "avg_mfe_all": None, "avg_mfe_winners": None, "avg_realized_winners": None,
        "giveback_gap_winners": None, "avg_mae_all": None, "avg_mae_losers": None,
        "worst_mae_losers": None,
    }
    if mfe_col is not None:
        mfe = pd.to_numeric(frame[mfe_col], errors="coerce")
        section["avg_mfe_all"] = _mean_or_none(mfe[valid])
        section["avg_mfe_winners"] = _mean_or_none(mfe[is_win])
        section["avg_realized_winners"] = _mean_or_none(returns[is_win])
        if section["avg_mfe_winners"] is not None and section["avg_realized_winners"] is not None:
            section["giveback_gap_winners"] = round(
                section["avg_mfe_winners"] - section["avg_realized_winners"], _ROUND)
    if mae_col is not None:
        mae = pd.to_numeric(frame[mae_col], errors="coerce")
        section["avg_mae_all"] = _mean_or_none(mae[valid])
        loss_mae = mae[is_loss].dropna()
        section["avg_mae_losers"] = _mean_or_none(loss_mae)
        section["worst_mae_losers"] = _safe_number(float(loss_mae.min())) if len(loss_mae) else None
    section["note"] = (
        "MFE=%s, MAE=%s 기준. give-back gap(수익거래) %s%%p, 손실 평균 MAE %s%%." % (
            mfe_col or "(없음)", mae_col or "(없음)",
            _fmt(section["giveback_gap_winners"]), _fmt(section["avg_mae_losers"])))
    return section


def _build_edge_ratio_section(frame: Optional[pd.DataFrame]) -> Dict[str, Any]:
    """edge_ratio = 평균 MFE / 평균 |MAE| — 진입 후 유리/불리 이동폭 비율(>1 이면 유리)."""
    if frame is None:
        return _insufficient("거래행 없음(0건).", edge_ratio=None)
    mfe_col = _pick_column(frame, MFE_COLUMN_CANDIDATES)
    mae_col = _pick_column(frame, MAE_COLUMN_CANDIDATES)
    if mfe_col is None or mae_col is None:
        return _insufficient("MFE/MAE 컬럼 없음 — edge ratio 정의 불가.", edge_ratio=None)
    mfe = pd.to_numeric(frame[mfe_col], errors="coerce")
    mae = pd.to_numeric(frame[mae_col], errors="coerce")
    joint = mfe.notna() & mae.notna()
    rows = int(joint.sum())
    if rows == 0:
        return _insufficient("유효 MFE/MAE 행 0건.", edge_ratio=None)
    avg_mfe = float(mfe[joint].mean())
    avg_abs_mae = float(mae[joint].abs().mean())
    if avg_abs_mae <= 1e-12:
        return _insufficient("평균 |MAE| 가 0 — edge ratio 나눗셈 불가.", edge_ratio=None)
    return {
        "status": SECTION_OK,
        "edge_ratio": round(avg_mfe / avg_abs_mae, _ROUND),
        "avg_mfe": _safe_number(avg_mfe), "avg_abs_mae": _safe_number(avg_abs_mae),
        "rows": rows,
        "note": "edge_ratio = 평균 MFE / 평균 |MAE| (공동 유효 %d행)." % rows,
    }


def _coerce_ablation(ablation_result: Any) -> Optional[AblationResult]:
    """AblationResult 또는 to_dict() 형태 Mapping 을 수용. 모양이 다르면 None(정직)."""
    if ablation_result is None:
        return None
    if isinstance(ablation_result, AblationResult):
        return ablation_result
    if isinstance(ablation_result, Mapping):
        try:
            items = tuple(
                ClauseAblation(
                    clause_index=int(item["clause_index"]),
                    clause_text=str(item["clause_text"]),
                    combinator=str(item.get("combinator", "and")),
                    status=str(item.get("status", "")),
                    pass_rate=item.get("pass_rate"),
                    delta_trades_if_removed=item.get("delta_trades_if_removed"),
                    blocked_avg_return=item.get("blocked_avg_return"),
                    redundancy=item.get("redundancy"),
                    redundancy_partner=item.get("redundancy_partner"),
                    verdict=str(item.get("verdict", "")),
                    note=str(item.get("note", "")),
                )
                for item in ablation_result.get("items", ())
            )
            return AblationResult(
                status=str(ablation_result.get("status", "")),
                trade_count=int(ablation_result.get("trade_count", 0)),
                clause_count=int(ablation_result.get("clause_count", len(items))),
                evaluable_clause_count=int(ablation_result.get("evaluable_clause_count", 0)),
                items=items,
                note=str(ablation_result.get("note", "")),
            )
        except (KeyError, TypeError, ValueError):
            return None
    return None


def _build_correlation_section(
    frame: Optional[pd.DataFrame], ablation: Optional[AblationResult],
) -> Dict[str, Any]:
    """중복 신호 — B_* 변수 상관 쌍(|pearson|>=임계) + ablation 절 자카드 중복 쌍."""
    have_frame = frame is not None
    have_ablation = ablation is not None and ablation.status == ABLATION_STATUS_OK
    if not have_frame and not have_ablation:
        return _insufficient("거래행/ablation 입력 없음 — 중복 분석 불가.",
                             variable_pairs=[], clause_pairs=[])

    variable_pairs: List[Dict[str, Any]] = []
    if have_frame:
        b_cols = [c for c in _analyze.B_COLUMNS if c in frame.columns]
        numeric = {c: pd.to_numeric(frame[c], errors="coerce") for c in b_cols}
        for i, col_a in enumerate(b_cols):
            for col_b in b_cols[i + 1:]:
                joint = numeric[col_a].notna() & numeric[col_b].notna()
                if int(joint.sum()) < _CORR_MIN_ROWS:
                    continue
                corr = float(numeric[col_a][joint].corr(numeric[col_b][joint]))
                if math.isfinite(corr) and abs(corr) >= _CORR_THRESHOLD:
                    variable_pairs.append({
                        "feature_a": col_a, "feature_b": col_b,
                        "correlation": round(corr, _ROUND),
                    })
        variable_pairs.sort(
            key=lambda p: (-abs(p["correlation"]), p["feature_a"], p["feature_b"]))

    clause_pairs: List[Dict[str, Any]] = []
    if have_ablation:
        seen: set = set()
        for item in ablation.items:
            if item.status != EVAL_STATUS_OK or item.redundancy is None:
                continue
            if item.redundancy < REDUNDANCY_SUGGEST_THRESHOLD or item.redundancy_partner is None:
                continue
            pair_key = frozenset((item.clause_text, item.redundancy_partner))
            if pair_key in seen:
                continue
            seen.add(pair_key)
            clause_pairs.append({
                "clause_text": item.clause_text, "partner": item.redundancy_partner,
                "jaccard": _safe_number(item.redundancy),
            })

    return {
        "status": SECTION_OK,
        "variable_pairs": variable_pairs, "clause_pairs": clause_pairs,
        "note": "변수 상관 쌍(|r|>=%s) %d개, 절 중복 쌍(자카드>=%s) %d개." % (
            _fmt(_CORR_THRESHOLD), len(variable_pairs),
            _fmt(REDUNDANCY_SUGGEST_THRESHOLD), len(clause_pairs)),
    }


def _ablation_candidates(ablation: Optional[AblationResult]) -> List[Dict[str, Any]]:
    """ablation 제안(to_mutation_axis_suggestions 재사용)을 root-cause 후보로 변환."""
    if ablation is None or ablation.status != ABLATION_STATUS_OK:
        return []
    candidates: List[Dict[str, Any]] = []
    for suggestion in to_mutation_axis_suggestions(ablation):
        verdict = str(suggestion.get("verdict", ""))
        prefix = "유해 절" if verdict == VERDICT_HARMFUL else "무효/중복 절"
        candidates.append({
            "source": "ablation", "verdict": verdict,
            "cause": "%s: %s" % (prefix, suggestion.get("clause_text")),
            "evidence": str(suggestion.get("evidence", "")),
            "mutation_axis": str(suggestion.get("mutation_axis", "")),
            "expected_effect": str(suggestion.get("expected_effect", "")),
            "risk_note": str(suggestion.get("risk_note", "")),
        })
    return candidates


def _segment_candidate(zone: Mapping[str, Any]) -> Dict[str, Any]:
    """손실 집중 세그먼트 한 셀을 root-cause 후보로 변환."""
    count = int(zone.get("count", 0))
    return {
        "source": "segment", "verdict": "loss_concentration",
        "cause": "손실 집중 세그먼트: %s" % zone.get("label"),
        "evidence": "%d건, 평균 수익률 %s%%, 전체 대비 %s%%p, 승률 %s." % (
            count, _fmt(zone.get("avg_return")),
            _fmt(zone.get("return_diff")), _fmt(zone.get("win_rate"))),
        "mutation_axis": "세그먼트 회피 필터: %s 구간 진입 제한" % zone.get("label"),
        "expected_effect": "손실 집중 구간 제거 — 평균 수익률/MDD 개선 기대",
        "risk_note": "세그먼트 표본 %d건 — 소표본 과적합 주의, 재백테스트 검증 필요" % count,
    }


def _build_root_cause_section(
    ablation: Optional[AblationResult], avoid_section: Mapping[str, Any],
) -> Dict[str, Any]:
    """최대 실패 원인 후보 1~3개 — ablation harmful/ineffective + 세그먼트 손실 집중."""
    ablation_cands = _ablation_candidates(ablation)
    harmful = [c for c in ablation_cands if c.get("verdict") == VERDICT_HARMFUL]
    others = [c for c in ablation_cands if c.get("verdict") != VERDICT_HARMFUL]
    segment_cands: List[Dict[str, Any]] = []
    if avoid_section.get("status") == SECTION_OK:
        segment_cands = [_segment_candidate(zone) for zone in avoid_section.get("zones", [])]

    # 우선순위: harmful 절 → 최악 손실 세그먼트 1개 → 나머지 절 제안 → 나머지 세그먼트.
    ordered = harmful + segment_cands[:1] + others + segment_cands[1:]
    if not ordered:
        return _insufficient(
            "root-cause 근거 부족 — ablation harmful/ineffective 절도, "
            "손실 집중 세그먼트도 없다.", candidates=[])
    candidates = [
        {"rank": rank, **cand}
        for rank, cand in enumerate(ordered[:MAX_ROOT_CAUSES], start=1)
    ]
    return {
        "status": SECTION_OK, "candidates": candidates,
        "note": "후보 %d개(ablation %d + segment %d 결합, 상한 %d)." % (
            len(candidates), len(ablation_cands), len(segment_cands), MAX_ROOT_CAUSES),
    }


def _build_mutation_axis_section(root_section: Mapping[str, Any]) -> Dict[str, Any]:
    """root-cause 후보에서 변이축 제안을 파생(우선순위 보존, 중복 제거)."""
    if root_section.get("status") != SECTION_OK:
        return _insufficient("root-cause 후보 없음 — 변이축 제안 불가.", axes=[])
    axes: List[Dict[str, Any]] = []
    seen: set = set()
    for cand in root_section.get("candidates", []):
        axis = cand.get("mutation_axis")
        if not axis or axis in seen:
            continue
        seen.add(axis)
        axes.append({
            "mutation_axis": axis,
            "expected_effect": cand.get("expected_effect"),
            "risk_note": cand.get("risk_note"),
            "source": cand.get("source"),
        })
    if not axes:
        return _insufficient("root-cause 후보에 변이축이 없다.", axes=[])
    return {
        "status": SECTION_OK, "axes": axes,
        "note": "root-cause 후보에서 파생한 변이축 %d개(우선순위 순)." % len(axes),
    }


def _build_risk_note(
    sections: Mapping[str, Mapping[str, Any]], ablation: Optional[AblationResult],
) -> str:
    """카드 전체 리스크 노트 — 근사/표본 한계와 데이터 부족 섹션을 항상 명시."""
    parts = [
        "연구 전용 분석 카드(authority=%s)다 — 승격/내보내기/실전 판단 권한 없음." % CARD_AUTHORITY,
    ]
    if ablation is not None and ablation.status == ABLATION_STATUS_OK:
        parts.append("ablation 수치는 행 기반 근사다 — 절 제거 재백테스트 검증 전 확정 금지.")
    if sections.get("segment_heatmap", {}).get("status") == SECTION_OK:
        parts.append("세그먼트/임계 통계는 주어진 거래행 표본 기반이다 — 홀드아웃 재검증 전 일반화 금지.")
    missing = [name for name, sec in sections.items() if sec.get("status") == SECTION_INSUFFICIENT]
    if missing:
        parts.append("데이터 부족 섹션: %s — 해당 축으로는 결론을 내리지 말 것." % ", ".join(missing))
    return " ".join(parts)


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------

def build_analysis_card(
    result_meta: Optional[Mapping[str, Any]],
    trades_df: Optional[pd.DataFrame],
    ablation_result: Any = None,
    *,
    min_trades: int = _analyze.DEFAULT_MIN_TRADES,
    segment_min_samples: int = _segment.DEFAULT_SEGMENT_MIN_SAMPLES,
    fine_time: bool = False,
) -> Dict[str, Any]:
    """거래행 + (선택) ablation 결과에서 Analysis Card v2(dict)를 만든다.

    Args:
        result_meta: 공식 결과 지표 Mapping(profit/mdd/trades/win_rate/payoff 별칭
            화이트리스트만 추출 — 임의 키는 카드에 복사하지 않는다).
        trades_df: 백테스트 거래행 DataFrame(back_static.py df_tsg 스키마).
            원본은 수정하지 않는다(작업 사본 사용).
        ablation_result: ablation.ablate() 의 AblationResult 또는 그 to_dict() Mapping.
        min_trades: 통계 산출 최소 거래 수(analyze/segment 계약과 동일 의미).
        segment_min_samples: 세그먼트 셀 보고 최소 표본.
        fine_time: True 면 시간축을 5분 시초 셀로 세분(segment 계약 그대로 전달).

    Returns:
        카드 dict. 모든 분석 섹션은 status('ok'|'insufficient_data')를 가진다 —
        입력이 없으면 빈 값을 조작하지 않고 insufficient_data 로 정직 라벨링한다.

    Raises:
        ValueError: result_meta 에 승격/실전 권한 키(can_promote/can_export/
            can_live/promotion_eligible)가 truthy 로 들어온 경우(권한 밀반입 가드).
    """
    _guard_authority(result_meta)
    frame = _working_frame(trades_df)
    trade_count = 0 if frame is None else int(len(frame))

    metrics = _build_metrics_section(result_meta)
    seg_result, seg_error = _run_segment_analysis(
        frame, min_trades=min_trades,
        segment_min_samples=segment_min_samples, fine_time=fine_time,
    )
    segment_heatmap = _build_heatmap_section(seg_result, seg_error)
    avoid_zones, prefer_zones = _build_zone_sections(seg_result, seg_error)
    ablation = _coerce_ablation(ablation_result)
    root_cause = _build_root_cause_section(ablation, avoid_zones)

    sections = {
        "metrics": metrics,
        "segment_heatmap": segment_heatmap,
        "mfe_mae": _build_mfe_mae_section(frame),
        "edge_ratio": _build_edge_ratio_section(frame),
        "feature_importance": _build_feature_importance_section(frame, min_trades),
        "avoid_zones": avoid_zones,
        "prefer_zones": prefer_zones,
        "correlation_redundancy": _build_correlation_section(frame, ablation),
        "root_cause": root_cause,
        "mutation_axis": _build_mutation_axis_section(root_cause),
    }
    return {
        "schema": ANALYSIS_CARD_SCHEMA,
        "authority": CARD_AUTHORITY,
        "trade_count": trade_count,
        **sections,
        "risk_note": _build_risk_note(sections, ablation),
    }


def card_to_json(card: Mapping[str, Any]) -> str:
    """카드를 결정론 JSON 문자열로 직렬화(sort_keys, NaN 금지 — allow_nan=False)."""
    return json.dumps(
        card, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    )


def card_from_json(text: str) -> Dict[str, Any]:
    """JSON 문자열에서 카드를 역직렬화. 스키마 불일치는 계약 위반(ValueError).

    Raises:
        ValueError: JSON 파싱 실패(json.JSONDecodeError 는 ValueError 하위 클래스),
            객체가 아니거나 schema != 'analysis_card_v2' 인 경우.
    """
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("analysis_card_json_not_object")
    if data.get("schema") != ANALYSIS_CARD_SCHEMA:
        raise ValueError("analysis_card_schema_mismatch")
    return data


# ---------------------------------------------------------------------------
# 사람이 읽는 markdown 렌더
# ---------------------------------------------------------------------------

def _md_start(lines: List[str], title: str, section: Mapping[str, Any]) -> bool:
    """섹션 헤더를 쓰고, ok 가 아니면 insufficient 라벨을 쓰고 False 를 돌려준다."""
    lines.extend(["", "## " + title])
    if section.get("status") != SECTION_OK:
        lines.append("- **insufficient_data** — %s" % (section.get("note") or "입력 데이터 없음."))
        return False
    return True


def _md_metrics(lines: List[str], section: Mapping[str, Any]) -> None:
    if not _md_start(lines, "공식 지표", section):
        return
    values = section.get("values") or {}
    for key in _METRIC_ALIASES:
        lines.append("- %s: %s" % (key, _fmt(values.get(key))))


def _md_heatmap(lines: List[str], section: Mapping[str, Any]) -> None:
    if not _md_start(lines, "세그먼트 히트맵 (시간대×시가총액)", section):
        return
    lines.append("- 전체 평균 수익률 %s%% / 승률 %s" % (
        _fmt(section.get("overall_avg_return")), _fmt(section.get("overall_win_rate"))))
    cells = section.get("cells") or []
    if cells:
        lines.extend(["", "| 셀 | 건수 | 평균수익률(%) | 승률 | return_diff(%p) |",
                      "| --- | --- | --- | --- | --- |"])
        for cell in cells:
            lines.append("| %s | %s | %s | %s | %s |" % (
                cell.get("label"), _fmt(cell.get("count")), _fmt(cell.get("avg_return")),
                _fmt(cell.get("win_rate")), _fmt(cell.get("return_diff"))))
    else:
        lines.append("- 교차 셀 없음(표본 미달) — 단축 세그먼트 참조.")
    for thr in section.get("thresholds") or []:
        lines.append("- 임계 후보: %s %s %s (n=%s, 평균 %s%%, %s)" % (
            thr.get("stom_var"), thr.get("operator"), _fmt(thr.get("threshold")),
            _fmt(thr.get("count")), _fmt(thr.get("mean_return")), thr.get("source")))


def _md_mfe_mae(lines: List[str], section: Mapping[str, Any]) -> None:
    if not _md_start(lines, "MFE/MAE 요약", section):
        return
    lines.append("- 수익거래 평균 MFE %s%% / 실현 %s%% → give-back %s%%p" % (
        _fmt(section.get("avg_mfe_winners")), _fmt(section.get("avg_realized_winners")),
        _fmt(section.get("giveback_gap_winners"))))
    lines.append("- 손실거래 평균 MAE %s%% (최악 %s%%)" % (
        _fmt(section.get("avg_mae_losers")), _fmt(section.get("worst_mae_losers"))))


def _md_edge_ratio(lines: List[str], section: Mapping[str, Any]) -> None:
    if not _md_start(lines, "Edge Ratio", section):
        return
    lines.append("- edge_ratio %s = 평균 MFE %s%% / 평균 |MAE| %s%% (n=%s)" % (
        _fmt(section.get("edge_ratio")), _fmt(section.get("avg_mfe")),
        _fmt(section.get("avg_abs_mae")), _fmt(section.get("rows"))))


def _md_features(lines: List[str], section: Mapping[str, Any]) -> None:
    if not _md_start(lines, "피처 중요도 (승/패 Cohen's d)", section):
        return
    lines.extend(["| 피처 | Cohen's d | 승자평균 | 패자평균 | FDR |",
                  "| --- | --- | --- | --- | --- |"])
    for feat in section.get("features") or []:
        lines.append("| %s | %s | %s | %s | %s |" % (
            feat.get("feature"), _fmt(feat.get("cohens_d")), _fmt(feat.get("win_mean")),
            _fmt(feat.get("loss_mean")), _fmt(feat.get("fdr_pass"))))


def _md_zones(lines: List[str], title: str, section: Mapping[str, Any]) -> None:
    if not _md_start(lines, title, section):
        return
    zones = section.get("zones") or []
    if not zones:
        lines.append("- (해당 구간 없음) %s" % (section.get("note") or ""))
        return
    for zone in zones:
        lines.append("- %s: %s건, 평균 %s%%, return_diff %s%%p" % (
            zone.get("label"), _fmt(zone.get("count")),
            _fmt(zone.get("avg_return")), _fmt(zone.get("return_diff"))))


def _md_correlation(lines: List[str], section: Mapping[str, Any]) -> None:
    if not _md_start(lines, "중복/상관 (correlation & redundancy)", section):
        return
    for pair in section.get("variable_pairs") or []:
        lines.append("- 변수 상관: %s ↔ %s (r=%s)" % (
            pair.get("feature_a"), pair.get("feature_b"), _fmt(pair.get("correlation"))))
    for pair in section.get("clause_pairs") or []:
        lines.append("- 절 중복: %s ↔ %s (자카드 %s)" % (
            pair.get("clause_text"), pair.get("partner"), _fmt(pair.get("jaccard"))))
    if not (section.get("variable_pairs") or section.get("clause_pairs")):
        lines.append("- 중복 신호 없음.")


def _md_root_cause(lines: List[str], section: Mapping[str, Any]) -> None:
    if not _md_start(lines, "Root Cause 후보", section):
        return
    for cand in section.get("candidates") or []:
        lines.append("%s. [%s] %s" % (cand.get("rank"), cand.get("source"), cand.get("cause")))
        lines.append("   - 근거: %s" % cand.get("evidence"))
        lines.append("   - 변이축: %s" % cand.get("mutation_axis"))


def _md_mutation(lines: List[str], section: Mapping[str, Any]) -> None:
    if not _md_start(lines, "변이축(mutation axis) 제안", section):
        return
    for idx, axis in enumerate(section.get("axes") or [], start=1):
        lines.append("%d. %s" % (idx, axis.get("mutation_axis")))
        lines.append("   - 기대효과: %s / 리스크: %s" % (
            axis.get("expected_effect"), axis.get("risk_note")))


def render_card_md(card: Mapping[str, Any]) -> str:
    """카드를 사람이 읽는 한국어 markdown 문자열로 렌더링한다(무예외).

    insufficient_data 섹션은 사유(note)와 함께 그대로 노출한다 — 빈 표를
    그럴듯하게 채우지 않는다(정직 라벨 계약).
    """
    lines: List[str] = ["# Analysis Card v2", ""]
    lines.append("- schema: %s" % card.get("schema", "(없음)"))
    lines.append("- authority: %s" % card.get("authority", "(없음)"))
    lines.append("- 거래행 수: %s" % _fmt(card.get("trade_count")))

    _md_metrics(lines, card.get("metrics") or {})
    _md_heatmap(lines, card.get("segment_heatmap") or {})
    _md_mfe_mae(lines, card.get("mfe_mae") or {})
    _md_edge_ratio(lines, card.get("edge_ratio") or {})
    _md_features(lines, card.get("feature_importance") or {})
    _md_zones(lines, "회피 구간 (avoid zones)", card.get("avoid_zones") or {})
    _md_zones(lines, "선호 구간 (prefer zones)", card.get("prefer_zones") or {})
    _md_correlation(lines, card.get("correlation_redundancy") or {})
    _md_root_cause(lines, card.get("root_cause") or {})
    _md_mutation(lines, card.get("mutation_axis") or {})

    lines.extend(["", "## 리스크 노트", str(card.get("risk_note") or "(없음)")])
    return "\n".join(lines) + "\n"
