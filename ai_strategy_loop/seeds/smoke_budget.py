"""셀 단위 스모크 예산 판정 (T1.5) — 자원 배분용 advisory go/no-go 라벨.

스모크 선별 규약(docs/research/condition_research/
2026-06-12_smoke_screening_protocol.md)의 사전선언 임계 —
**tick 기준 스모크 손익 <= -2,000,000 이면 no-go** (기준 창 2025Q1 = 90일) —
를 셀 단위 결과에 적용한다. 판정 창이 기준 창(90일)보다 짧으면 예산을 창
길이에 **비례 축소**한다 (예: 45일 창 → -1,000,000). 기준보다 긴 창이라고
예산을 확대하지는 않는다 (축소 전용 — 보수적 방향 고정).

**advisory 원칙 (규약 4항 — 위반 금지)**: 판정('go'|'no_go')은 '본 스윕을
할지'를 정하는 **자원 배분용 advisory 라벨일 뿐**이며, 어떤 후보 선택·동결
(freeze)·승격 판단에도 사용해서는 안 된다. no_go 는 영구 폐기가 아니라
대기열 후순위 강등이다 (응답곡선 가치가 필요해지면 실행).

**n_trials 정직성 (규약 4항)**: 스모크도 시도(trial)다. 판정 payload 의
``attempt`` 필드(counted_as_trial/run_id/trades)를 동결 시 ``--trial-runs``
n_trials 합산에 포함해야 한다 (누락 금지).

순수 모듈: I/O·전역 상태 없음. 같은 입력 → 같은 출력. 연구 레인 전용
(승격/export/live 권한 로직과 무관).
"""

from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Optional, Sequence

SMOKE_VERDICT_SCHEMA = "seed_lattice_smoke_verdict_v1"

SMOKE_GO = "go"
SMOKE_NO_GO = "no_go"

# 사전선언 임계 (스모크 규약 3항): 스모크 손익 <= -2,000,000 → no-go.
SMOKE_BASE_BUDGET_KRW = -2_000_000.0
# 기준 창: 2025Q1 스모크 창 (20250101~20250331 = 90일 — smoke-config.json).
SMOKE_BASE_WINDOW_DAYS = 90

VALID_SMOKE_LANES = ("tick", "min")

# advisory 라벨 사용 금지 영역 (규약 4항의 기계 판독 표식).
SMOKE_FORBIDDEN_USES = ("selection", "freeze")

# 셀 결과 dict 의 동의 키 (coverage.py 유연 스키마 규약과 동일 — 앞선 키 우선).
_PROFIT_KEYS = ("profit", "prior_profit", "total_profit", "smoke_profit")
_TRADE_KEYS = ("trades", "prior_trades", "trade_count", "n_trades")
_CELL_KEYS = ("cell_id", "cell")
_RUN_ID_KEYS = ("run_id", "smoke_run_id")


def _first_key(entry: Mapping[str, Any], keys: Sequence[str]) -> Optional[Any]:
    """동의 키 목록에서 처음으로 존재하는(None 아님) 값을 돌려준다."""
    for key in keys:
        value = entry.get(key)
        if value is not None:
            return value
    return None


def smoke_budget_threshold(
    window_days: int,
    *,
    base_budget: float = SMOKE_BASE_BUDGET_KRW,
    base_window_days: int = SMOKE_BASE_WINDOW_DAYS,
) -> float:
    """창 길이에 비례 축소된 스모크 예산 임계를 돌려준다.

    scale = min(1.0, window_days / base_window_days) — 축소 전용. 기준 창(90일)
    이상이면 기준 예산(-2,000,000) 그대로다 (확대 없음 — 보수적 방향 고정).

    Args:
        window_days: 스모크 판정 창 길이 (일, 양수).
        base_budget: 기준 예산 (음수 — 기본 -2,000,000, tick 기준).
        base_window_days: 기준 창 길이 (기본 90일 = 2025Q1).

    Returns:
        음수 float 임계 (profit <= 임계 → no_go).

    Raises:
        ValueError: window_days/base_window_days 가 양수가 아니거나
            base_budget 이 음수가 아닐 때 (시스템 경계 검증).
    """
    days = int(window_days)
    base_days = int(base_window_days)
    if days <= 0:
        raise ValueError(f"window_days 는 양수여야 합니다: {window_days}")
    if base_days <= 0:
        raise ValueError(f"base_window_days 는 양수여야 합니다: {base_window_days}")
    budget = float(base_budget)
    if not math.isfinite(budget) or budget >= 0:
        raise ValueError(f"base_budget 은 유한한 음수여야 합니다: {base_budget}")
    scale = min(1.0, days / base_days)
    return budget * scale


def _optional_int(entry: Mapping[str, Any], keys: Sequence[str],
                  label: str) -> Optional[int]:
    """동의 키에서 선택적 정수 필드를 꺼낸다 (없으면 None, 비수치는 거부)."""
    raw = _first_key(entry, keys)
    if raw is None:
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} 숫자 변환 실패: {raw!r}") from exc
    if value < 0:
        raise ValueError(f"{label} 는 음수일 수 없습니다: {value}")
    return value


def evaluate_smoke_budget(
    cell_result: Mapping[str, Any],
    *,
    lane: str,
    window_days: int,
    base_budget: float = SMOKE_BASE_BUDGET_KRW,
    base_window_days: int = SMOKE_BASE_WINDOW_DAYS,
) -> Dict[str, Any]:
    """셀 스모크 결과 하나를 예산 임계로 판정한다 — **advisory 전용**.

    판정 규칙 (스모크 규약 3항의 셀 단위 적용):
      - profit <= 창 비례 축소 임계 → ``no_go`` (경계 포함 — -2,000,000 정확히면
        no_go). 그 외 → ``go``.
      - profit 이 비유한수(NaN/inf)면 ``no_go`` (fail-closed).

    **advisory 원칙 (위반 금지)**: 반환 verdict 는 '본 스윕을 할지'의 자원 배분
    결정에만 쓴다. 후보 **선택·동결(freeze)·승격 판단에 사용 금지** — payload 의
    ``advisory_only``/``forbidden_uses`` 가 이 원칙의 기계 판독 표식이다.
    no_go 는 영구 폐기가 아니라 대기열 후순위 강등이다.

    **n_trials 정직성**: 스모크도 trial 이다. 반환 ``attempt`` 필드를 동결 시
    ``--trial-runs`` n_trials 합산에 포함해야 한다 (누락 금지).

    Args:
        cell_result: 유연 스키마 결과 dict — ``profit`` 필수 (동의 키:
            profit|prior_profit|total_profit|smoke_profit). ``cell_id``/
            ``trades``/``run_id`` 는 선택 (attempt 기록에 실림).
        lane: 'tick' | 'min' (임계 기준은 tick 규약 — min 도 같은 예산을
            advisory 로 준용하되 payload 에 basis 를 남긴다).
        window_days: 스모크 창 길이 (일, 양수 — 창 비례 축소 입력).
        base_budget: 기준 예산 (기본 -2,000,000).
        base_window_days: 기준 창 길이 (기본 90일 = 2025Q1).

    Returns:
        JSON 직렬화 가능한 판정 dict (schema ``seed_lattice_smoke_verdict_v1``).

    Raises:
        ValueError: lane 미지, profit 누락/비수치, window_days 비양수 등
            (시스템 경계 검증).
    """
    if lane not in VALID_SMOKE_LANES:
        raise ValueError(f"lane 은 {VALID_SMOKE_LANES} 중 하나여야 합니다: {lane!r}")
    if not isinstance(cell_result, Mapping):
        raise ValueError(f"cell_result 는 Mapping 이어야 합니다: {type(cell_result)!r}")

    threshold = smoke_budget_threshold(
        window_days, base_budget=base_budget, base_window_days=base_window_days)

    profit_raw = _first_key(cell_result, _PROFIT_KEYS)
    if profit_raw is None:
        raise ValueError(f"cell_result 에 profit 필드가 없습니다 (허용 키: {_PROFIT_KEYS})")
    try:
        profit = float(profit_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"profit 숫자 변환 실패: {profit_raw!r}") from exc

    if not math.isfinite(profit):
        verdict, reason = SMOKE_NO_GO, "non_finite_profit"  # fail-closed
    elif profit <= threshold:
        verdict, reason = SMOKE_NO_GO, "smoke_profit_at_or_below_budget"
    else:
        verdict, reason = SMOKE_GO, "smoke_profit_within_budget"

    cell_id = _first_key(cell_result, _CELL_KEYS)
    run_id = _first_key(cell_result, _RUN_ID_KEYS)
    trades = _optional_int(cell_result, _TRADE_KEYS, "trades")

    return {
        "schema": SMOKE_VERDICT_SCHEMA,
        "cell_id": None if cell_id is None else str(cell_id),
        "lane": lane,
        "window_days": int(window_days),
        "base_window_days": int(base_window_days),
        "base_budget": float(base_budget),
        "budget_threshold": threshold,
        "budget_basis": "tick_smoke_protocol_2026-06-12",
        "profit": profit,
        "verdict": verdict,
        "reason": reason,
        "advisory_only": True,
        "forbidden_uses": list(SMOKE_FORBIDDEN_USES),
        "policy_note": (
            "자원 배분용 advisory 라벨 — 후보 선택·동결(freeze) 사용 금지. "
            "no_go 는 영구 폐기가 아니라 대기열 후순위 강등이다."
        ),
        "attempt": {
            "counted_as_trial": True,
            "run_id": None if run_id is None else str(run_id),
            "trades": trades,
            "note": "스모크도 trial — 동결 시 --trial-runs n_trials 에 합산(누락 금지)",
        },
    }
