from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from strategy.v3k_analyzer_adapter import (
    DEFAULT_FLAGS,
    FLAG_ANALYSIS_UI,
    FLAG_ANALYZER_MODULE_STAGING,
    FLAG_BACKTEST_LEARNING,
    FLAG_CANDLE_ANALYSIS,
    FLAG_FORMULA_GLOBAL_FACADE,
    FLAG_REALTIME_LEARNING,
    FLAG_RISK_ANALYSIS,
    FLAG_RISK_ANALYZER_V3,
    FLAG_STG_GLOBALS_FACADE,
    FLAG_VOLATILITY_PATTERN_ANALYSIS,
    FLAG_VOLATILITY_STOP_TAKE_ANALYSIS,
    FLAG_VOLUME_PROFILE_ANALYSIS,
    FLAG_VOLUME_SPIKE_ANALYSIS,
    normalize_v3k_flags,
)


V3K_SETTINGS_SURFACE_VERSION = "V3K_SETTINGS_SURFACE_V1"


@dataclass(frozen=True)
class V3KSettingContract:
    key: str
    default: bool
    group: str
    label: str
    description: str
    ui_exposable: bool = False


@dataclass(frozen=True)
class V3KSettingsSurfaceResult:
    version: str
    settings: dict[str, bool]
    feature_flags: dict[str, bool]
    diagnostics: tuple[str, ...] = ()

    @property
    def all_off(self) -> bool:
        return not any(self.settings.values())


@dataclass(frozen=True)
class V3KSettingsBridgeResult:
    version: str
    dict_set: dict[str, Any]
    settings: dict[str, bool]
    feature_flags: dict[str, bool]
    diagnostics: tuple[str, ...] = ()

    @property
    def all_off(self) -> bool:
        return not any(self.settings.values())


V3K_SETTING_CONTRACTS: tuple[V3KSettingContract, ...] = (
    V3KSettingContract(
        key=FLAG_ANALYSIS_UI,
        default=False,
        group="ui",
        label="V3K analysis UI",
        description="Expose V3K analysis controls in a future UI surface.",
        ui_exposable=True,
    ),
    V3KSettingContract(
        key=FLAG_BACKTEST_LEARNING,
        default=False,
        group="learning",
        label="V3K backtest learning",
        description="Allow read-only V3K learning-data loads during backtest dry-run hooks.",
        ui_exposable=True,
    ),
    V3KSettingContract(
        key=FLAG_REALTIME_LEARNING,
        default=False,
        group="learning",
        label="V3K realtime learning",
        description="Allow realtime learning-data preload dry-runs.",
        ui_exposable=True,
    ),
    V3KSettingContract(
        key=FLAG_ANALYZER_MODULE_STAGING,
        default=False,
        group="analyzer",
        label="V3K analyzer module staging",
        description="Allow staged analyzer module import/contract checks.",
    ),
    V3KSettingContract(
        key=FLAG_RISK_ANALYZER_V3,
        default=False,
        group="analyzer",
        label="V3K risk analyzer engine",
        description="Allow the V3 AnalyzerRisk smoke path.",
        ui_exposable=True,
    ),
    V3KSettingContract(
        key=FLAG_CANDLE_ANALYSIS,
        default=False,
        group="analyzer",
        label="Candle pattern analysis",
        description="Allow candle-pattern analyzer outputs when a later runtime hook is approved.",
        ui_exposable=True,
    ),
    V3KSettingContract(
        key=FLAG_VOLUME_SPIKE_ANALYSIS,
        default=False,
        group="analyzer",
        label="Volume spike analysis",
        description="Allow volume-spike analyzer outputs when a later runtime hook is approved.",
        ui_exposable=True,
    ),
    V3KSettingContract(
        key=FLAG_VOLUME_PROFILE_ANALYSIS,
        default=False,
        group="analyzer",
        label="Volume profile analysis",
        description="Allow volume-profile analyzer outputs when a later runtime hook is approved.",
        ui_exposable=True,
    ),
    V3KSettingContract(
        key=FLAG_VOLATILITY_PATTERN_ANALYSIS,
        default=False,
        group="analyzer",
        label="Volatility pattern analysis",
        description=(
            "Allow volatility-pattern analyzer outputs when a later runtime hook is approved."
        ),
        ui_exposable=True,
    ),
    V3KSettingContract(
        key=FLAG_VOLATILITY_STOP_TAKE_ANALYSIS,
        default=False,
        group="analyzer",
        label="Volatility stop/take analysis",
        description=(
            "Allow volatility stop/take analyzer outputs when a later runtime hook is approved."
        ),
        ui_exposable=True,
    ),
    V3KSettingContract(
        key=FLAG_RISK_ANALYSIS,
        default=False,
        group="analyzer",
        label="Risk analysis",
        description="Allow risk analyzer outputs when a later runtime hook is approved.",
        ui_exposable=True,
    ),
    V3KSettingContract(
        key=FLAG_FORMULA_GLOBAL_FACADE,
        default=False,
        group="formula",
        label="V3K formula manager adapter",
        description="Allow V3K analyzer outputs to be converted into prefixed formula globals.",
        ui_exposable=True,
    ),
    V3KSettingContract(
        key=FLAG_STG_GLOBALS_FACADE,
        default=False,
        group="formula",
        label="V3K strategy globals facade",
        description="Allow V3K prefixed globals to be built for a future strategy-global hook.",
        ui_exposable=True,
    ),
)


def _as_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "on", "yes", "y"}
    return bool(value)


def v3k_setting_contract_keys() -> tuple[str, ...]:
    return tuple(contract.key for contract in V3K_SETTING_CONTRACTS)


def v3k_settings_defaults() -> dict[str, bool]:
    return {contract.key: contract.default for contract in V3K_SETTING_CONTRACTS}


def v3k_settings_contract_rows() -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "key": contract.key,
            "default": contract.default,
            "group": contract.group,
            "label": contract.label,
            "description": contract.description,
            "ui_exposable": contract.ui_exposable,
        }
        for contract in V3K_SETTING_CONTRACTS
    )


def normalize_v3k_settings(
    raw_settings: Mapping[str, Any] | None = None,
) -> V3KSettingsSurfaceResult:
    settings = v3k_settings_defaults()
    diagnostics: list[str] = []
    known_keys = set(settings)

    for key, value in (raw_settings or {}).items():
        if key not in known_keys:
            diagnostics.append(f"unknown V3K setting ignored: {key}")
            continue
        settings[key] = _as_bool(value)

    feature_flags = normalize_v3k_flags(settings)
    return V3KSettingsSurfaceResult(
        version=V3K_SETTINGS_SURFACE_VERSION,
        settings=settings,
        feature_flags=feature_flags,
        diagnostics=tuple(diagnostics),
    )


def assert_v3k_settings_contract_aligned() -> None:
    keys = v3k_setting_contract_keys()
    if len(keys) != len(set(keys)):
        raise AssertionError("duplicate V3K setting contract keys")

    missing_from_defaults = [key for key in keys if key not in DEFAULT_FLAGS]
    if missing_from_defaults:
        raise AssertionError(
            f"V3K settings missing from DEFAULT_FLAGS: {missing_from_defaults}",
        )

    not_off = [
        contract.key
        for contract in V3K_SETTING_CONTRACTS
        if contract.default is not False or DEFAULT_FLAGS.get(contract.key) is not False
    ]
    if not_off:
        raise AssertionError(f"V3K setting defaults must stay OFF: {not_off}")

def extract_v3k_settings_from_dict_set(
    dict_set: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not dict_set:
        return {}
    known_keys = set(v3k_setting_contract_keys())
    return {key: dict_set[key] for key in known_keys if key in dict_set}


def bridge_v3k_settings_into_dict_set(
    dict_set: Mapping[str, Any] | None = None,
    raw_settings: Mapping[str, Any] | None = None,
) -> V3KSettingsBridgeResult:
    base = dict(dict_set or {})
    merged_settings = extract_v3k_settings_from_dict_set(base)
    if raw_settings:
        merged_settings.update(raw_settings)

    normalized = normalize_v3k_settings(merged_settings)
    bridged = dict(base)
    bridged.update(normalized.settings)
    return V3KSettingsBridgeResult(
        version=normalized.version,
        dict_set=bridged,
        settings=normalized.settings,
        feature_flags=normalized.feature_flags,
        diagnostics=normalized.diagnostics,
    )
