from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from strategy.v3k_analyzer_adapter import (
    DB_FLAG_PHASE_F_ANALYZER_STRATEGY,
    ENV_PHASE_F_DISABLE,
    ENV_PHASE_F_ENABLE,
    FLAG_FORMULA_GLOBAL_FACADE,
    FLAG_STG_GLOBALS_FACADE,
    V3KPhaseFAnalyzerGateResult,
    V3KAnalyzerOutput,
    evaluate_phase_f_analyzer_gate,
    normalize_v3k_flags,
)


V3K_FORMULA_GLOBAL_PREFIX = "V3K_"

V3K_ANALYZER_FORMULA_FIELDS = (
    "패턴점수",
    "패턴신뢰도",
    "리스크점수",
    "거래량점수",
    "거래량신뢰도",
    "가격대점수",
    "가격대신뢰도",
    "변동성점수",
    "변동성신뢰도",
    "예상수익률",
    "익절수익률",
    "손절수익률",
    "변손익신뢰도",
)

V3K_ANALYZER_KIND_FIELDS = {
    "candle_pattern": ("패턴점수", "패턴신뢰도"),
    "risk": ("리스크점수",),
    "volume_spike": ("거래량점수", "거래량신뢰도"),
    "volume_profile": ("가격대점수", "가격대신뢰도"),
    "volatility_pattern": ("변동성점수", "변동성신뢰도"),
    "volatility_stop_take": (
        "예상수익률",
        "익절수익률",
        "손절수익률",
        "변손익신뢰도",
    ),
}


@dataclass(frozen=True)
class V3KFormulaGlobalRequest:
    """Input for a side-effect-free V3K formula/global facade build."""

    analyzer_values: dict[str, Any] = field(default_factory=dict)
    feature_flags: dict[str, Any] = field(default_factory=dict)
    include_zero_defaults: bool = True


@dataclass(frozen=True)
class V3KFormulaGlobalResult:
    request: V3KFormulaGlobalRequest
    values: dict[str, float] = field(default_factory=dict)
    globals_dict: dict[str, Any] = field(default_factory=dict)
    diagnostics: tuple[str, ...] = ()

    @property
    def has_globals(self) -> bool:
        return bool(self.globals_dict)


@dataclass(frozen=True)
class V3KFormulaGlobalDryRunResult:
    """Collision-aware preview for future formula/global runtime injection."""

    formula_result: V3KFormulaGlobalResult
    existing_keys: tuple[str, ...] = ()
    candidate_keys: tuple[str, ...] = ()
    collisions: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()

    @property
    def enabled(self) -> bool:
        return self.formula_result.has_globals

    @property
    def ready(self) -> bool:
        return self.enabled and not self.collisions

    @property
    def globals_dict(self) -> dict[str, Any]:
        return self.formula_result.globals_dict


@dataclass(frozen=True)
class V3KPhaseFFormulaResult:
    """Phase F pre-ON formula result with explicit dual-gate evidence."""

    gate: V3KPhaseFAnalyzerGateResult
    formula_result: V3KFormulaGlobalResult

    @property
    def enabled(self) -> bool:
        return self.gate.enabled and self.formula_result.has_globals

    @property
    def globals_dict(self) -> dict[str, Any]:
        return self.formula_result.globals_dict


class V3KFormulaGlobalFacade:
    """Build a safe formula/global facade for staged V3K analyzer outputs.

    The facade returns prefixed callable names that are suitable for a future
    `globals().update(...)` boundary. It intentionally does not import or call
    Kiwoom strategy, receiver, trader, order, or formula-manager runtime code.
    """

    def __init__(
        self,
        feature_flags: dict[str, Any] | None = None,
        prefix: str = V3K_FORMULA_GLOBAL_PREFIX,
    ):
        self.feature_flags = normalize_v3k_flags(feature_flags)
        self.prefix = prefix

    def _flags_for_request(self, request: V3KFormulaGlobalRequest) -> dict[str, bool]:
        flags = dict(self.feature_flags)
        if request.feature_flags:
            flags.update(normalize_v3k_flags(request.feature_flags))
        return flags

    @staticmethod
    def _numeric(value: Any) -> float:
        if value is None:
            return 0.0
        if isinstance(value, bool):
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
        return 0.0

    @staticmethod
    def _value_from_output(value: Any) -> float:
        if isinstance(value, V3KAnalyzerOutput):
            return V3KFormulaGlobalFacade._numeric(value.risk_score)
        return V3KFormulaGlobalFacade._numeric(value)

    def _empty_values(self) -> dict[str, float]:
        return {name: 0.0 for name in V3K_ANALYZER_FORMULA_FIELDS}

    def _apply_kind_value(
        self,
        values: dict[str, float],
        kind: str,
        raw_value: Any,
    ) -> tuple[str, ...]:
        fields = V3K_ANALYZER_KIND_FIELDS.get(kind)
        if not fields:
            return (f"unknown V3K analyzer kind skipped: {kind}",)

        if isinstance(raw_value, V3KAnalyzerOutput):
            values[fields[0]] = self._value_from_output(raw_value)
            return tuple(raw_value.diagnostics)

        if isinstance(raw_value, dict):
            for field_name in fields:
                values[field_name] = self._numeric(raw_value.get(field_name, 0.0))
            return ()

        if isinstance(raw_value, (list, tuple)):
            for field_name, item in zip(fields, raw_value):
                values[field_name] = self._numeric(item)
            return ()

        values[fields[0]] = self._numeric(raw_value)
        return ()

    def build_values(
        self,
        request: V3KFormulaGlobalRequest,
    ) -> tuple[dict[str, float], tuple[str, ...]]:
        values = self._empty_values() if request.include_zero_defaults else {}
        diagnostics: list[str] = []

        for key, raw_value in request.analyzer_values.items():
            if key in V3K_ANALYZER_FORMULA_FIELDS:
                values[key] = self._value_from_output(raw_value)
                if isinstance(raw_value, V3KAnalyzerOutput):
                    diagnostics.extend(raw_value.diagnostics)
                continue

            diagnostics.extend(self._apply_kind_value(values, key, raw_value))

        return values, tuple(diagnostic for diagnostic in diagnostics if diagnostic)

    def build_globals(self, values: dict[str, float]) -> dict[str, Any]:
        globals_dict: dict[str, Any] = {}
        for field_name, field_value in values.items():
            global_name = f"{self.prefix}{field_name}"

            def getter(value: float = field_value) -> float:
                return value

            globals_dict[global_name] = getter
        return globals_dict

    def build(self, request: V3KFormulaGlobalRequest) -> V3KFormulaGlobalResult:
        flags = self._flags_for_request(request)
        if not (
            flags.get(FLAG_FORMULA_GLOBAL_FACADE, False)
            and flags.get(FLAG_STG_GLOBALS_FACADE, False)
        ):
            return V3KFormulaGlobalResult(
                request=request,
                diagnostics=("formula/global facade disabled by V3K feature flags",),
            )

        values, diagnostics = self.build_values(request)
        globals_dict = self.build_globals(values)
        return V3KFormulaGlobalResult(
            request=request,
            values=values,
            globals_dict=globals_dict,
            diagnostics=("formula/global facade dry-run built",) + diagnostics,
        )

    def build_phase_f(
        self,
        request: V3KFormulaGlobalRequest,
        *,
        env: Mapping[str, Any] | None = None,
        db_flags: Mapping[str, Any] | None = None,
    ) -> V3KPhaseFFormulaResult:
        """Build Phase F analyzer formula candidates behind dual gate only.

        Page034 remains a pre-ON boundary. This method does not mutate runtime
        globals and does not read/write operating DB files. The caller must pass
        explicit env/DB-flag mappings so tests can prove env-only, DB-only, and
        rollback cases without touching live state.
        """

        gate = evaluate_phase_f_analyzer_gate(env=env, db_flags=db_flags)
        if not gate.enabled:
            return V3KPhaseFFormulaResult(
                gate=gate,
                formula_result=V3KFormulaGlobalResult(
                    request=request,
                    diagnostics=(
                        "phase f analyzer formula facade disabled by dual gate",
                    )
                    + gate.diagnostics,
                ),
            )

        phase_flags = dict(request.feature_flags)
        phase_flags[FLAG_FORMULA_GLOBAL_FACADE] = True
        phase_flags[FLAG_STG_GLOBALS_FACADE] = True
        phase_request = V3KFormulaGlobalRequest(
            analyzer_values=dict(request.analyzer_values),
            feature_flags=phase_flags,
            include_zero_defaults=request.include_zero_defaults,
        )
        formula_result = self.build(phase_request)
        return V3KPhaseFFormulaResult(
            gate=gate,
            formula_result=V3KFormulaGlobalResult(
                request=formula_result.request,
                values=formula_result.values,
                globals_dict=formula_result.globals_dict,
                diagnostics=gate.diagnostics + formula_result.diagnostics,
            ),
        )

    @staticmethod
    def normalize_existing_keys(
        existing: Iterable[str] | Mapping[str, Any] | None = None,
    ) -> tuple[str, ...]:
        if existing is None:
            return ()
        if isinstance(existing, Mapping):
            keys = existing.keys()
        else:
            keys = existing
        return tuple(sorted({key for key in keys if isinstance(key, str)}))

    def dry_run(
        self,
        request: V3KFormulaGlobalRequest,
        existing: Iterable[str] | Mapping[str, Any] | None = None,
    ) -> V3KFormulaGlobalDryRunResult:
        formula_result = self.build(request)
        existing_keys = self.normalize_existing_keys(existing)
        candidate_keys = tuple(sorted(formula_result.globals_dict))
        collisions = tuple(sorted(set(existing_keys) & set(candidate_keys)))

        diagnostics = list(formula_result.diagnostics)
        if collisions:
            diagnostics.append(
                "formula/global dry-run collision: " + ", ".join(collisions),
            )
        elif formula_result.has_globals:
            diagnostics.append("formula/global dry-run ready")

        return V3KFormulaGlobalDryRunResult(
            formula_result=formula_result,
            existing_keys=existing_keys,
            candidate_keys=candidate_keys,
            collisions=collisions,
            diagnostics=tuple(diagnostics),
        )
