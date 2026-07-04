"""시드 격자 커버리지 지도 (T1.4) — 셀별 (시드 수, 거래수, 손익 분포) 집계와 gap 산출.

입력 계약:
  - 시드: :class:`~ai_strategy_loop.seeds.lattice.SeedRecord` 또는 동형 dict
    (``cell_id`` 필수, ``buy_sha256`` 있으면 결과 매칭 인덱스에 등록).
  - 백테스트 결과 요약: 유연 스키마 dict — **``trades`` 와 ``profit`` 만 필수**
    (동의 키 허용: trades|prior_trades|trade_count|n_trades,
    profit|prior_profit|total_profit). 셀 귀속은 ``cell_id`` 가 있으면 그것으로,
    없으면 ``buy_sha256``(동의 키: buy_code_sha256|sha256) 을 시드 인덱스에서
    조회한다. 둘 다 없거나 미지 sha 면 unmatched 로 남긴다 (지도에 집계).
    백테스트 실행 자체는 이 모듈 범위 밖이다 — 기존 러너가 시드를 소비한다.

출력 계약:
  - :func:`build_coverage_map` → JSON 직렬화 가능한 dict
    (schema ``seed_lattice_coverage_map_v1``, 셀 순서 = 격자 열거 순서).
  - :func:`coverage_gaps` → discovery 프롬프트의 ``coverage_gap`` 입력 형식
    (:func:`ai_strategy_loop.brain.prompt.build_discovery_research_messages`
    가 읽는 ``coverage_gap_id`` + ``coverage_bucket_keys`` 를 반드시 포함 —
    prompt.py 는 읽기 전용 계약 소비, 수정 금지 대상).
  - :func:`save_coverage_map` / :func:`load_coverage_map` — JSON 왕복.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from ai_strategy_loop.seeds.lattice import Cell, SeedRecord, enumerate_cells

COVERAGE_MAP_SCHEMA = "seed_lattice_coverage_map_v1"
COVERAGE_GAPS_SCHEMA = "seed_lattice_coverage_gaps_v1"

# 셀당 train 거래 목표 (격자 설계 기본값 — 완화 임계·거래수 우선 규약과 짝).
DEFAULT_MIN_TRADES = 300

# 결과 요약 dict 의 동의 키 (앞선 키 우선).
_TRADE_KEYS = ("trades", "prior_trades", "trade_count", "n_trades")
_PROFIT_KEYS = ("profit", "prior_profit", "total_profit")
_CELL_KEYS = ("cell_id", "cell")
_SHA_KEYS = ("buy_sha256", "buy_code_sha256", "sha256")


# ---------------------------------------------------------------------------
# 셀 커버리지 레코드
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CellCoverage:
    """셀 하나의 커버리지 집계 (불변 스냅샷).

    Attributes:
        cell_id: 셀 식별자 (``{lane}_{band}_{cap}_{regime}``).
        lane: 'tick' | 'min'.
        time_band: 시간밴드 라벨.
        cap_tier: 시가총액 단계 이름.
        regime: 등락율 국면 이름.
        seed_count: 이 셀에 귀속된 시드 수.
        result_count: 이 셀에 귀속된 결과 요약 수.
        trades: 결과 요약의 거래수 합.
        profit_summary: 손익 분포 요약
            (n/total/mean/min/max/wins — 결과 0건이면 min/max 는 None).
    """

    cell_id: str
    lane: str
    time_band: str
    cap_tier: str
    regime: str
    seed_count: int
    result_count: int
    trades: int
    profit_summary: Mapping[str, Optional[float]]

    def to_dict(self) -> Dict[str, Any]:
        """JSON 직렬화용 dict 를 새로 만들어 돌려준다."""
        return {
            "cell_id": self.cell_id,
            "lane": self.lane,
            "time_band": self.time_band,
            "cap_tier": self.cap_tier,
            "regime": self.regime,
            "seed_count": self.seed_count,
            "result_count": self.result_count,
            "trades": self.trades,
            "profit_summary": dict(self.profit_summary),
        }


def _parse_cell_axes(cell_id: str) -> Tuple[str, str, str, str]:
    """cell_id ``{lane}_{band}_{cap}_{regime}`` 를 4축으로 분해한다.

    격자 축 이름에는 밑줄이 없으므로 (lattice.py 축 상수 규약) split 이 안전하다.
    형식이 어긋나면 축을 'unknown' 으로 둔다 (동적 셀 허용 — 유연 스키마).
    """
    parts = str(cell_id).split("_")
    if len(parts) == 4 and all(parts):
        return parts[0], parts[1], parts[2], parts[3]
    return "unknown", "unknown", "unknown", "unknown"


def _first_key(entry: Mapping[str, Any], keys: Sequence[str]) -> Optional[Any]:
    """동의 키 목록에서 처음으로 존재하는(None 아님) 값을 돌려준다."""
    for key in keys:
        value = entry.get(key)
        if value is not None:
            return value
    return None


def _extract_result_fields(entry: Mapping[str, Any], index: int) -> Tuple[int, float]:
    """결과 요약에서 (trades, profit) 필수 필드를 꺼내 검증한다.

    Raises:
        ValueError: trades/profit 누락 또는 숫자 변환 불가 (시스템 경계 검증).
    """
    trades_raw = _first_key(entry, _TRADE_KEYS)
    profit_raw = _first_key(entry, _PROFIT_KEYS)
    if trades_raw is None:
        raise ValueError(f"results[{index}] 에 trades 필드가 없습니다 (허용 키: {_TRADE_KEYS})")
    if profit_raw is None:
        raise ValueError(f"results[{index}] 에 profit 필드가 없습니다 (허용 키: {_PROFIT_KEYS})")
    try:
        trades = int(trades_raw)
        profit = float(profit_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"results[{index}] trades/profit 숫자 변환 실패: {exc}") from exc
    if trades < 0:
        raise ValueError(f"results[{index}] trades 는 음수일 수 없습니다: {trades}")
    return trades, profit


def _seed_fields(seed: Union[SeedRecord, Mapping[str, Any]], index: int) -> Tuple[str, str]:
    """시드에서 (cell_id, buy_sha256) 를 꺼낸다 (SeedRecord 또는 동형 dict)."""
    if isinstance(seed, SeedRecord):
        return seed.cell_id, seed.buy_sha256
    cell_id = seed.get("cell_id")
    if not cell_id:
        raise ValueError(f"seeds[{index}] 에 cell_id 가 없습니다")
    return str(cell_id), str(seed.get("buy_sha256") or "")


def _profit_summary(profits: Sequence[float]) -> Dict[str, Optional[float]]:
    """손익 리스트의 분포 요약 (n/total/mean/min/max/wins) 을 만든다."""
    if not profits:
        return {"n": 0, "total": 0.0, "mean": 0.0, "min": None, "max": None, "wins": 0}
    total = float(sum(profits))
    return {
        "n": len(profits),
        "total": total,
        "mean": total / len(profits),
        "min": float(min(profits)),
        "max": float(max(profits)),
        "wins": sum(1 for p in profits if p > 0),
    }


# ---------------------------------------------------------------------------
# 커버리지 지도 빌드
# ---------------------------------------------------------------------------
def build_coverage_map(
    seeds: Iterable[Union[SeedRecord, Mapping[str, Any]]],
    results: Iterable[Mapping[str, Any]] = (),
    cells: Optional[Sequence[Cell]] = None,
) -> Dict[str, Any]:
    """시드 목록 + 결과 요약 목록을 셀별 커버리지 지도로 집계한다.

    시드가 0개인 격자 셀도 지도에 남는다 (열거 축 전체가 gap 판정 대상이므로).
    격자 밖 cell_id 의 시드는 동적 셀로 뒤에 추가한다 (외부 패밀리 확장 대응).

    Args:
        seeds: :class:`SeedRecord` 또는 동형 dict 목록 (``cell_id`` 필수).
        results: 유연 스키마 결과 요약 dict 목록 (trades/profit 필수).
        cells: 기준 격자 셀 (None 이면 :func:`enumerate_cells` 기본 144셀).

    Returns:
        JSON 직렬화 가능한 커버리지 지도 dict (schema/cells/totals/unmatched).

    Raises:
        ValueError: 시드 cell_id 누락, 결과 trades/profit 누락·비수치.
    """
    base_cells = list(cells) if cells is not None else enumerate_cells()

    # 집계 버퍼 (로컬 누적 후 불변 스냅샷으로 변환).
    seed_counts: Dict[str, int] = {}
    trades_acc: Dict[str, int] = {}
    profits_acc: Dict[str, List[float]] = {}
    result_counts: Dict[str, int] = {}
    cell_order: List[str] = []
    axes: Dict[str, Tuple[str, str, str, str]] = {}

    def _register_cell(cell_id: str, ax: Tuple[str, str, str, str]) -> None:
        if cell_id not in axes:
            cell_order.append(cell_id)
            axes[cell_id] = ax
            seed_counts[cell_id] = 0
            trades_acc[cell_id] = 0
            profits_acc[cell_id] = []
            result_counts[cell_id] = 0

    for cell in base_cells:
        _register_cell(cell.cell_id, (cell.lane, cell.band.label, cell.cap.name, cell.regime.name))

    sha_to_cell: Dict[str, str] = {}
    n_seeds = 0
    for i, seed in enumerate(seeds):
        cell_id, buy_sha = _seed_fields(seed, i)
        _register_cell(cell_id, _parse_cell_axes(cell_id))
        seed_counts[cell_id] += 1
        n_seeds += 1
        if buy_sha:
            sha_to_cell[buy_sha] = cell_id

    unmatched: List[Dict[str, Any]] = []
    n_results = 0
    for i, entry in enumerate(results):
        n_results += 1
        trades, profit = _extract_result_fields(entry, i)
        cell_id = _first_key(entry, _CELL_KEYS)
        if cell_id is None:
            sha = _first_key(entry, _SHA_KEYS)
            cell_id = sha_to_cell.get(str(sha)) if sha is not None else None
        if cell_id is None or str(cell_id) not in axes:
            unmatched.append({
                "index": i,
                "reason": "cell_id/buy_sha256 로 셀 귀속 실패",
                "cell_id": None if cell_id is None else str(cell_id),
            })
            continue
        key = str(cell_id)
        trades_acc[key] += trades
        profits_acc[key].append(profit)
        result_counts[key] += 1

    cells_out: Dict[str, Dict[str, Any]] = {}
    for cell_id in cell_order:
        lane, band, cap, regime = axes[cell_id]
        cov = CellCoverage(
            cell_id=cell_id,
            lane=lane,
            time_band=band,
            cap_tier=cap,
            regime=regime,
            seed_count=seed_counts[cell_id],
            result_count=result_counts[cell_id],
            trades=trades_acc[cell_id],
            profit_summary=_profit_summary(profits_acc[cell_id]),
        )
        cells_out[cell_id] = cov.to_dict()

    return {
        "schema": COVERAGE_MAP_SCHEMA,
        "cells": cells_out,
        "totals": {
            "cells": len(cells_out),
            "seeds": n_seeds,
            "results": n_results,
            "matched_results": n_results - len(unmatched),
            "unmatched_results": len(unmatched),
            "trades": sum(trades_acc.values()),
        },
        "unmatched": unmatched,
    }


# ---------------------------------------------------------------------------
# coverage gap — discovery 프롬프트 입력 형식
# ---------------------------------------------------------------------------
def coverage_gaps(coverage_map: Mapping[str, Any],
                  min_trades: int = DEFAULT_MIN_TRADES) -> List[Dict[str, Any]]:
    """거래수 미충족 셀을 discovery 프롬프트 ``coverage_gap`` 형식으로 돌려준다.

    판정: 셀 trades < ``min_trades`` (경계: 299 → gap, 300 → 충족). 순서는 지도의
    셀 순서(= 격자 열거 순서) 그대로 — 결정론.

    각 gap dict 는 :func:`build_discovery_research_messages` 계약 필드를 포함한다:
      - ``coverage_gap_id``: 문자열 식별자.
      - ``coverage_bucket_keys``: 문자열 리스트 (cell/lane/time_band/cap_tier/
        regime 버킷 키).
    나머지 필드(seed_count/trades/min_trades/trade_deficit/reason)는 프롬프트에
    JSON 블록으로 그대로 실리는 보조 컨텍스트다.

    Args:
        coverage_map: :func:`build_coverage_map` 산출 dict.
        min_trades: 셀당 최소 거래수 목표 (기본 300 — 격자 설계 규약).

    Returns:
        gap dict 리스트 (JSON 직렬화 가능).

    Raises:
        ValueError: 지도 스키마 불일치 또는 min_trades 가 양수가 아닐 때.
    """
    if coverage_map.get("schema") != COVERAGE_MAP_SCHEMA:
        raise ValueError(f"coverage map 스키마 불일치: {coverage_map.get('schema')!r}")
    if int(min_trades) <= 0:
        raise ValueError(f"min_trades 는 양수여야 합니다: {min_trades}")

    gaps: List[Dict[str, Any]] = []
    for cell_id, cov in coverage_map.get("cells", {}).items():
        trades = int(cov.get("trades", 0))
        if trades >= min_trades:
            continue
        seed_count = int(cov.get("seed_count", 0))
        gaps.append({
            "coverage_gap_id": f"lattice_gap:{cell_id}:min_trades_{int(min_trades)}",
            "coverage_bucket_keys": [
                f"cell:{cell_id}",
                f"lane:{cov.get('lane')}",
                f"time_band:{cov.get('time_band')}",
                f"cap_tier:{cov.get('cap_tier')}",
                f"regime:{cov.get('regime')}",
            ],
            "cell_id": cell_id,
            "lane": cov.get("lane"),
            "time_band": cov.get("time_band"),
            "cap_tier": cov.get("cap_tier"),
            "regime": cov.get("regime"),
            "seed_count": seed_count,
            "trades": trades,
            "min_trades": int(min_trades),
            "trade_deficit": int(min_trades) - trades,
            "reason": "no_seeds" if seed_count == 0 else "insufficient_train_trades",
        })
    return gaps


# ---------------------------------------------------------------------------
# JSON 직렬화 저장/로드
# ---------------------------------------------------------------------------
def save_coverage_map(coverage_map: Mapping[str, Any], path: Union[str, Path]) -> Path:
    """커버리지 지도를 JSON 으로 저장한다 (utf-8, 한글 보존).

    Args:
        coverage_map: :func:`build_coverage_map` 산출 dict.
        path: 저장 경로 (부모 디렉토리는 자동 생성).

    Returns:
        저장된 :class:`Path`.
    """
    if coverage_map.get("schema") != COVERAGE_MAP_SCHEMA:
        raise ValueError(f"coverage map 스키마 불일치: {coverage_map.get('schema')!r}")
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(dict(coverage_map), ensure_ascii=False, indent=2),
                 encoding="utf-8")
    return p


def load_coverage_map(path: Union[str, Path]) -> Dict[str, Any]:
    """JSON 커버리지 지도를 읽어 dict 로 돌려준다 (스키마 검증 포함).

    Raises:
        ValueError: schema 필드가 ``seed_lattice_coverage_map_v1`` 이 아닐 때.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != COVERAGE_MAP_SCHEMA:
        raise ValueError(f"coverage map 스키마 불일치: {path}")
    return data
