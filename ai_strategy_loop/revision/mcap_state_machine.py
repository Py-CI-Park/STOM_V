"""Market-cap-stratified D3 temporal state-machine candidate representation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Any, Mapping

from ai_strategy_loop.revision.mcap_bands import MCAP_BANDS
from ai_strategy_loop.revision.window_contract import ResearchWindowContract
from ai_strategy_loop.revision.execution_contract import evaluate_execution_contract

AUTHORITY = "existing_db_development_no_oos_no_adoption"
STEPS = ("STATE_ENTER", "STATE_PERSIST", "EVENT", "CONFIRM", "ENTER")
D3_ALLOWED_FUNCTIONS = (
    "self.Buy", "구간호가총잔량비율", "구간저가대비현재가등락율",
    "체결강도평균대비비율", "구간고가대비현재가등락율",
    "고가미갱신지속틱수", "거래대금평균대비비율", "변동성",
    "최고현재가", "최저현재가", "현재가N", "등락율N", "저가미갱신지속틱수",
    "변동성급증",
)


@dataclass(frozen=True, slots=True)
class ParameterSpec:
    name: str
    kind: str
    low: float
    high: float
    default: float

    def validate(self, value: Any) -> int | float:
        number = float(value)
        if not math.isfinite(number) or not self.low <= number <= self.high:
            raise ValueError(f"{self.name} outside [{self.low}, {self.high}]")
        return int(number) if self.kind == "integer" else number


@dataclass(frozen=True, slots=True)
class StateFamily:
    family_id: str
    hypothesis: str
    parameters: tuple[ParameterSpec, ...]
    steps: tuple[str, ...] = STEPS


@dataclass(frozen=True, slots=True)
class McapStateCandidate:
    candidate_id: str
    band_id: str
    family_id: str
    parameters: dict[str, int | float]
    source: str
    source_sha256: str
    canonical_sha256: str
    window_contract_sha256: str
    steps: tuple[str, ...] = STEPS
    authority: str = AUTHORITY
    lane: str = "stock_tick"
    schema: str = "stom.d3_mcap_state_candidate.v1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


FAMILIES = (
    StateFamily("ABSORPTION_REVERSAL", "매도호가 압력이 지속돼도 저점 진행이 제한된 뒤 체결 Flow가 반전한다.", (
        ParameterSpec("book_window", "integer", 10, 60, 30),
        ParameterSpec("prior_book_max", "continuous", 0.15, 0.48, 0.35),
        ParameterSpec("price_window", "integer", 5, 45, 15),
        ParameterSpec("recovery_rate", "continuous", 0.05, 1.5, 0.35),
        ParameterSpec("flow_window", "integer", 10, 60, 30),
        ParameterSpec("flow_ratio", "continuous", 1.02, 2.5, 1.15),
    )),
    StateFamily("FAILED_BREAKOUT_RETURN", "고점 돌파가 지속되지 못한 뒤 Range 복귀와 매수 Flow 재확인이 발생한다.", (
        ParameterSpec("breakout_window", "integer", 10, 60, 45),
        ParameterSpec("return_rate", "continuous", 0.05, 1.5, 0.35),
        ParameterSpec("persistence", "integer", 2, 30, 6),
        ParameterSpec("flow_window", "integer", 10, 60, 30),
        ParameterSpec("confirmation", "continuous", 1.0, 2.2, 1.12),
        ParameterSpec("turnover_ratio", "continuous", 0.8, 4.0, 1.2),
    )),
    StateFamily("COMPRESSION_CONFIRMED_BREAKOUT", "직전 변동성 압축 뒤 확장·신고가·Flow 확인이 순차 발생한다.", (
        ParameterSpec("vol_window", "integer", 10, 60, 30),
        ParameterSpec("compression", "continuous", 0.05, 1.2, 0.4),
        ParameterSpec("expansion", "continuous", 1.1, 5.0, 1.8),
        ParameterSpec("price_window", "integer", 5, 60, 20),
        ParameterSpec("flow_window", "integer", 10, 60, 30),
        ParameterSpec("strength_ratio", "continuous", 1.0, 2.5, 1.15),
    )),
    StateFamily("FLOW_PRICE_DIVERGENCE", "직전 강한 체결 Flow 대비 가격 반응이 제한된 후 가격·Flow가 같은 방향으로 확인된다.", (
        ParameterSpec("flow_window", "integer", 10, 60, 30),
        ParameterSpec("prior_flow", "continuous", 1.05, 3.0, 1.4),
        ParameterSpec("price_window", "integer", 5, 60, 20),
        ParameterSpec("reaction_ceiling", "continuous", 0.05, 1.5, 0.4),
        ParameterSpec("current_flow", "continuous", 1.0, 2.5, 1.12),
        ParameterSpec("recovery_rate", "continuous", 0.05, 1.2, 0.25),
    )),
    StateFamily("OPENING_OVERREACTION_MEAN_REVERT", "시초 급락 뒤 저점 미갱신 지속·거래대금 둔화·가격 회귀가 확인된다.", (
        ParameterSpec("price_window", "integer", 5, 60, 30),
        ParameterSpec("overreaction", "continuous", -4.0, -0.3, -1.2),
        ParameterSpec("persistence", "integer", 2, 30, 6),
        ParameterSpec("rebound", "continuous", 0.05, 2.0, 0.4),
        ParameterSpec("flow_window", "integer", 10, 60, 30),
        ParameterSpec("cooldown", "continuous", 0.1, 1.2, 0.7),
    )),
)
_FAMILY_BY_ID = {family.family_id: family for family in FAMILIES}
_BAND_EXPRESSION = {
    "MCAP_A_LT3000": "시가총액 < 3000",
    "MCAP_B_3000_5000": "3000 <= 시가총액 < 5000",
    "MCAP_C_5000_10000": "5000 <= 시가총액 < 10000",
    "MCAP_D_GE10000": "10000 <= 시가총액",
}


def normalize_parameters(family_id: str, values: Mapping[str, Any]) -> dict[str, int | float]:
    family = _FAMILY_BY_ID.get(family_id)
    if family is None:
        raise ValueError(f"unknown D3 family: {family_id}")
    expected = {spec.name for spec in family.parameters}
    if set(values) != expected:
        raise ValueError(f"parameter keys mismatch: expected={sorted(expected)}, observed={sorted(values)}")
    return {spec.name: spec.validate(values[spec.name]) for spec in family.parameters}


def _signal(family_id: str, p: Mapping[str, int | float]) -> str:
    if family_id == "ABSORPTION_REVERSAL":
        return (f"구간호가총잔량비율({p['book_window']}, {p['book_window']}) <= {p['prior_book_max']:.4f} and "
                f"구간저가대비현재가등락율({p['price_window']}) >= {p['recovery_rate']:.4f} and "
                f"체결강도평균대비비율({p['flow_window']}) >= {p['flow_ratio']:.4f}")
    if family_id == "FAILED_BREAKOUT_RETURN":
        return (f"구간고가대비현재가등락율({p['breakout_window']}) <= -{p['return_rate']:.4f} and "
                f"{p['persistence']} <= 고가미갱신지속틱수() <= {p['breakout_window']} and "
                f"체결강도평균대비비율({p['flow_window']}) >= {p['confirmation']:.4f} and "
                f"거래대금평균대비비율({p['flow_window']}) >= {p['turnover_ratio']:.4f}")
    if family_id == "COMPRESSION_CONFIRMED_BREAKOUT":
        return (f"변동성({p['vol_window']}, {p['vol_window']}) > 0 and "
                f"변동성({p['vol_window']}, {p['vol_window']}) <= {p['compression']:.4f} and "
                f"변동성급증({p['vol_window']}, {p['expansion']:.4f}) and "
                f"현재가 > 최고현재가({p['price_window']}, 1) and "
                f"체결강도평균대비비율({p['flow_window']}) >= {p['strength_ratio']:.4f}")
    if family_id == "FLOW_PRICE_DIVERGENCE":
        reaction_factor = 1.0 + float(p["reaction_ceiling"]) / 100.0
        return (f"체결강도평균대비비율({p['flow_window']}, {p['flow_window']}) >= {p['prior_flow']:.4f} and "
                f"현재가N({p['price_window']}) <= 최저현재가({p['price_window']}, {p['price_window']}) * {reaction_factor:.6f} and "
                f"체결강도평균대비비율({p['flow_window']}) >= {p['current_flow']:.4f} and "
                f"구간저가대비현재가등락율({p['price_window']}) >= {p['recovery_rate']:.4f}")
    if family_id == "OPENING_OVERREACTION_MEAN_REVERT":
        return (f"등락율N({p['price_window']}) <= {p['overreaction']:.4f} and "
                f"저가미갱신지속틱수() >= {p['persistence']} and "
                f"구간저가대비현재가등락율({p['price_window']}) >= {p['rebound']:.4f} and "
                f"거래대금평균대비비율({p['flow_window']}) <= {p['cooldown']:.4f}")
    raise ValueError(f"unknown D3 family: {family_id}")


def render_state_machine_source(*, family_id: str, band_id: str, parameters: Mapping[str, Any],
                                window: ResearchWindowContract) -> str:
    if band_id not in _BAND_EXPRESSION or band_id not in {band.band_id for band in MCAP_BANDS}:
        raise ValueError(f"unknown market-cap band: {band_id}")
    p = normalize_parameters(family_id, parameters)
    signal = _signal(family_id, p)
    return "\n".join((
        f"# D3 Opening State Machine · {family_id} · {band_id}",
        f"# window_contract_sha256={window.contract_sha256}",
        "# existing DB development only · OOS/자동채택/실전 권한 없음",
        "VI아래5호가 = VI가격 - VI호가단위 * 5",
        "매수 = True", "",
        "if not (관심종목 == 1):", "    매수 = False",
        "elif not (1000 < 현재가 < 50000):", "    매수 = False",
        "elif not (현재가 < VI아래5호가):", "    매수 = False",
        "elif 라운드피겨위5호가이내:", "    매수 = False",
        f"elif not ({_BAND_EXPRESSION[band_id]}):", "    매수 = False",
        f"elif not ({window.start} <= 시분초 < {window.end_exclusive}):", "    매수 = False",
        f"elif not ({signal}):", "    매수 = False", "",
        "if 매수:", "    self.Buy()", "",
    ))


def build_candidate(*, family_id: str, band_id: str, parameters: Mapping[str, Any],
                    window: ResearchWindowContract) -> McapStateCandidate:
    normalized = normalize_parameters(family_id, parameters)
    source = render_state_machine_source(
        family_id=family_id, band_id=band_id, parameters=normalized, window=window,
    )
    source_sha256 = hashlib.sha256(source.encode("utf-8")).hexdigest()
    contract = evaluate_execution_contract(
        source, allowed_functions=D3_ALLOWED_FUNCTIONS,
        max_clauses=32, max_lookback=240, max_estimated_work=256,
    )
    if not contract.ok:
        raise ValueError(f"D3 source execution contract failed: {contract.reasons}")
    canonical = json.dumps({"family_id": family_id, "band_id": band_id, "parameters": normalized,
                            "window": window.contract_sha256, "steps": STEPS},
                           ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    canonical_sha256 = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return McapStateCandidate(
        candidate_id=f"D3_{family_id}_{band_id}_{canonical_sha256[:10]}",
        band_id=band_id, family_id=family_id, parameters=normalized,
        source=source, source_sha256=source_sha256, canonical_sha256=canonical_sha256,
        window_contract_sha256=window.contract_sha256,
    )
