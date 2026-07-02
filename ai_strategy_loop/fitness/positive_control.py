"""양성대조(positive control) 자동 판정 — 발굴 게이트 건전성 감시 (T5.1).

2026-06-16 챔피언 양성대조 진단(docs/update_log/
2026-06-16_champion_positive_control_diagnostic.md)의 자동화다. 그 진단은
검증된 챔피언 4종을 발굴 게이트(mdd_cap=20 · min_daily_trades=0.05)로
재판정해 **4/4 전원 통과**를 확인했고, 이로써 "게이트/데이터는 정상이고
생성기가 병목"임을 규명했다. 이 모듈은 같은 판정을 함수로 고정해, 이후
게이트/데이터 파이프라인이 회귀하면 챔피언 탈락으로 즉시 드러나게 한다.

핵심 해석 (docstring 계약):
  - `all_passed=True`  → 게이트·데이터 건전(gate_healthy). 인간 검증 전략이
    발굴 게이트를 통과한다 = 측정기 교정 유지.
  - `all_passed=False` → **게이트 또는 데이터 건전성 이상 신호**
    (gate_regression_suspected). 검증된 챔피언(인간이 이미 수익성을 확인한
    전략)이 발굴 게이트에서 탈락한다는 것은 전략의 문제가 아니라 게이트
    설정·지표 추출·데이터 파이프라인 중 어딘가가 회귀했다는 뜻이다.
    (2026-06-16 진단의 대우명제를 자동화한 것.)

권한: **advisory_only** — 연구 레인 전용 참고 신호다. 이 판정이 자동으로
게이트 설정을 바꾸거나 루프를 멈추지 않는다.

게이트 재사용: 판정은 기존 하드 게이트 `fitness.score.compute_fitness`를
읽기 전용으로 재사용한다(재구현 금지 — 발굴 루프와 byte-동일 기준 보장).
gate_passed는 metrics+config 만으로 결정되며 equity_series는 score(표시용)
에만 영향을 준다.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from ai_strategy_loop.fitness.score import compute_fitness

# 판정 결과의 고정 권한 표기 — 연구 레인 전용 참고 신호.
AUTHORITY = "advisory_only"

# verdict 문자열 (계약 고정).
VERDICT_HEALTHY = "gate_healthy"
VERDICT_REGRESSION = "gate_regression_suspected"

# 기본 챔피언 기준선 경로 — dashboard/reference_strategies.json (읽기 전용).
DEFAULT_BASELINE_PATH = (
    Path(__file__).resolve().parent.parent / "dashboard" / "reference_strategies.json"
)


@dataclass(frozen=True)
class PositiveControlGateConfig:
    """양성대조 판정용 발굴 게이트 설정 (compute_fitness의 getattr 계약 충족).

    기본값은 2026-06-16 진단이 쓴 발굴 게이트 config
    (state/run_p5_validation_tick_late.json)와 동일하다:
      mdd_cap=20.0 · min_trades=20 · min_daily_trades=0.05.

    ai_strategy_loop.config.LoopConfig 등 어떤 객체든 같은 속성을 노출하면
    evaluate_positive_control(gate_config=...)에 그대로 넘길 수 있다
    (compute_fitness가 getattr로만 읽는다). 여기서 별도 dataclass를 두는
    이유는 config.py(동시 작업 중인 모듈)에 대한 import 의존을 만들지 않기
    위해서다.
    """

    mdd_cap: float = 20.0
    min_trades: int = 20
    min_daily_trades: float = 0.05
    tpi_gate: float = 0.0
    tpi_gate_enabled: bool = False


def _coerce_gate_config(gate_config: Any) -> Any:
    """gate_config 인자를 compute_fitness가 읽을 수 있는 객체로 정규화한다.

    - None            → 기본 발굴 게이트(PositiveControlGateConfig()).
    - Mapping(dict)   → 알려진 필드만 골라 PositiveControlGateConfig 생성.
    - 그 외 객체      → 그대로 통과(getattr 계약 — LoopConfig 등).
    """
    if gate_config is None:
        return PositiveControlGateConfig()
    if isinstance(gate_config, Mapping):
        known = {
            key: gate_config[key]
            for key in (
                "mdd_cap",
                "min_trades",
                "min_daily_trades",
                "tpi_gate",
                "tpi_gate_enabled",
            )
            if key in gate_config
        }
        return PositiveControlGateConfig(**known)
    return gate_config


def _gate_config_snapshot(config: Any) -> dict:
    """receipt/리포트에 실을 게이트 설정 스냅샷(dict)을 만든다."""
    if isinstance(config, PositiveControlGateConfig):
        return asdict(config)
    return {
        "mdd_cap": getattr(config, "mdd_cap", None),
        "min_trades": getattr(config, "min_trades", None),
        "min_daily_trades": getattr(config, "min_daily_trades", None),
        "tpi_gate": getattr(config, "tpi_gate", None),
        "tpi_gate_enabled": getattr(config, "tpi_gate_enabled", None),
    }


def _champion_name(entry: Mapping, index: int) -> str:
    """챔피언 엔트리에서 표시 이름을 꺼낸다 (name > id > 순번)."""
    for key in ("name", "id"):
        raw = entry.get(key)
        if raw is not None and str(raw).strip():
            return str(raw)
    return f"champion_{index}"


def _champion_metrics(entry: Mapping, name: str) -> dict:
    """챔피언 엔트리에서 metrics dict를 꺼낸다 (부재 시 정직 에러).

    허용 형태:
      - {"name": ..., "metrics": {...}}          (정규형)
      - 평평한 dict에 metric 키가 직접 있는 형태  (러너 산출물 호환) —
        cagr/mdd_pct/trade_count/total_profit_krw 중 하나라도 있으면
        엔트리 자체를 metrics로 간주한다.
    """
    metrics = entry.get("metrics")
    if isinstance(metrics, Mapping):
        return dict(metrics)
    flat_keys = ("total_profit_krw", "cagr", "mdd_pct", "trade_count")
    if any(key in entry for key in flat_keys):
        return {k: v for k, v in entry.items() if k not in ("equity_series",)}
    raise ValueError(
        f"챔피언 '{name}'에 metrics가 없습니다 — 양성대조는 기존 백테스트 "
        "결과 지표(cagr/mdd_pct/trade_count/total_profit_krw 등)를 요구합니다. "
        "'metrics' 키 또는 평평한 metric 키를 제공하세요."
    )


def evaluate_positive_control(
    champion_results: Sequence[Mapping],
    gate_config: Any = None,
) -> dict:
    """챔피언(인간 검증 전략) 결과들을 발굴 게이트로 재판정한다 — 양성대조.

    2026-06-16 진단의 자동화: 검증된 챔피언은 정상 게이트·정상 데이터에서
    반드시 통과해야 한다. 따라서 **all_passed=False는 전략의 문제가 아니라
    게이트 설정/지표 추출/데이터 파이프라인의 건전성 이상 신호**로 해석한다
    (verdict='gate_regression_suspected'). all_passed=True면 측정기(게이트)
    교정이 유지되고 있다는 뜻이다(verdict='gate_healthy').

    판정은 기존 하드 게이트 `compute_fitness`를 읽기 전용 재사용한다.
    gate_passed는 metrics+config만으로 결정된다(equity_series는 score에만
    영향 — 양성대조 판정과 무관하므로 엔트리에 없어도 된다).

    Args:
        champion_results: 챔피언 결과 dict 목록. 각 엔트리는
            {"name": str, "metrics": {...}, "equity_series": [...](선택)}
            정규형 또는 metric 키가 평평하게 있는 러너 산출물 형태.
            빈 목록이면 양성대조가 성립하지 않으므로 ValueError(정직 에러).
        gate_config: None(기본 발굴 게이트: mdd_cap=20 · min_trades=20 ·
            min_daily_trades=0.05) | dict | getattr 호환 config 객체.

    Returns:
        {
          "passed_count": int, "total": int, "all_passed": bool,
          "per_champion": [{"name", "passed", "reasons",
                            "gate_metrics": {...}}, ...],
          "verdict": "gate_healthy" | "gate_regression_suspected",
          "authority": "advisory_only",
          "gate_config": {...스냅샷...},
        }

        reasons는 게이트 실패 시 compute_fitness의 첫 위반 사유
        (first-violation 의미론 — 발굴 루프와 동일 문자열) 목록이며,
        통과 시 빈 목록이다.

    Raises:
        ValueError: champion_results가 비었거나 어떤 엔트리에 metrics가 없을 때.
    """
    if not champion_results:
        raise ValueError(
            "champion_results가 비어 있습니다 — 챔피언 증거 없이 양성대조를 "
            "수행할 수 없습니다(빈 입력을 '통과'로 취급하지 않는 정직 에러)."
        )

    config = _coerce_gate_config(gate_config)

    per_champion = []
    passed_count = 0
    for index, entry in enumerate(champion_results):
        if not isinstance(entry, Mapping):
            raise ValueError(
                f"champion_results[{index}]가 dict가 아닙니다: {type(entry).__name__}"
            )
        name = _champion_name(entry, index)
        metrics = _champion_metrics(entry, name)
        equity = entry.get("equity_series") or []
        fit = compute_fitness(metrics, equity, config)
        if fit.gate_passed:
            passed_count += 1
        per_champion.append(
            {
                "name": name,
                "passed": bool(fit.gate_passed),
                "reasons": [] if fit.gate_passed else [fit.reason],
                # 판정에 실제 쓰인 원시 구성요소(감사/리포트용).
                "gate_metrics": {
                    "cagr": fit.cagr,
                    "mdd_pct": fit.mdd,
                    "trade_count": fit.trade_count,
                    "total_profit_krw": fit.total_profit,
                    "daily_avg_trades": fit.daily_avg_trades,
                },
            }
        )

    total = len(per_champion)
    all_passed = passed_count == total
    return {
        "passed_count": passed_count,
        "total": total,
        "all_passed": all_passed,
        "per_champion": per_champion,
        "verdict": VERDICT_HEALTHY if all_passed else VERDICT_REGRESSION,
        "authority": AUTHORITY,
        "gate_config": _gate_config_snapshot(config),
    }


def load_champion_baselines(path: Optional[str] = None) -> list:
    """dashboard/reference_strategies.json에서 양성대조 대상 서브셋을 로드한다.

    인간 검증 우수전략(19종) 중 **수익 지표가 있는 전략만** 골라
    evaluate_positive_control이 받는 정규형으로 변환한다. reference 필드 →
    엔진 metrics 키 매핑:
      annual_return_pct → cagr · mdd_pct → mdd_pct · trades → trade_count ·
      profit_krw → total_profit_krw · daily_avg_trades → daily_avg_trades ·
      payoff(매매성능지수) → tpi.

    NOTE: 이 기준선은 보고서 지표의 재판정(정적 양성대조)이다. 발굴 게이트
    config로 재백테한 동적 양성대조(2026-06-16 진단의 champ_diag 경로)는
    scripts/run_positive_control.py에 기존 러너 산출물 JSON을 넘겨 수행한다.

    Args:
        path: reference_strategies.json 경로. None이면 기본 경로
            (ai_strategy_loop/dashboard/reference_strategies.json).

    Returns:
        [{"name": str, "metrics": {...}}, ...] — 수익 지표 보유 전략만.

    Raises:
        FileNotFoundError: 기준선 파일이 없을 때(정직 에러 — 조용한 빈 목록 금지).
        ValueError: 파일은 있으나 수익 지표(profit_krw)를 가진 전략이 하나도
            없거나 'strategies' 목록 자체가 없을 때.
    """
    baseline_path = Path(path) if path is not None else DEFAULT_BASELINE_PATH
    if not baseline_path.exists():
        raise FileNotFoundError(
            f"챔피언 기준선 파일이 없습니다: {baseline_path} — "
            "reference_strategies.json 없이 양성대조 기준선을 만들 수 없습니다."
        )
    with open(baseline_path, encoding="utf-8-sig") as fh:
        payload = json.load(fh)

    strategies = payload.get("strategies")
    if not isinstance(strategies, list) or not strategies:
        raise ValueError(
            f"기준선 파일에 'strategies' 목록이 없습니다: {baseline_path}"
        )

    champions = []
    for entry in strategies:
        if not isinstance(entry, Mapping):
            continue
        profit = entry.get("profit_krw")
        if profit is None:
            continue  # 수익 지표 없는 전략은 양성대조 대상에서 제외.
        metrics = {
            "cagr": entry.get("annual_return_pct", 0.0),
            "mdd_pct": entry.get("mdd_pct", 0.0),
            "trade_count": entry.get("trades", 0),
            "total_profit_krw": profit,
        }
        if entry.get("daily_avg_trades") is not None:
            metrics["daily_avg_trades"] = entry.get("daily_avg_trades")
        if entry.get("payoff") is not None:
            metrics["tpi"] = entry.get("payoff")
        champions.append(
            {"name": _champion_name(entry, len(champions)), "metrics": metrics}
        )

    if not champions:
        raise ValueError(
            f"수익 지표(profit_krw)를 가진 전략이 하나도 없습니다: {baseline_path} — "
            "양성대조 기준선이 성립하지 않습니다."
        )
    return champions
