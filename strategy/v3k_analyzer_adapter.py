from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Mapping

import numpy as np


FLAG_BACKTEST_LEARNING = "V3K_BACKTEST_LEARNING_ENABLED"
FLAG_REALTIME_LEARNING = "V3K_REALTIME_LEARNING_ENABLED"
FLAG_ANALYSIS_UI = "V3K_ANALYSIS_UI_ENABLED"
FLAG_FORMULA_MANAGER_ADAPTER = "V3K_FORMULA_MANAGER_ADAPTER"
FLAG_STG_GLOBALS_FACADE = "V3K_STG_GLOBALS_FACADE"
FLAG_FORMULA_GLOBAL_FACADE = FLAG_FORMULA_MANAGER_ADAPTER
FLAG_RISK_ANALYZER_V3 = "V3K_RISK_ANALYZER_V3_ENGINE"
FLAG_ANALYZER_MODULE_STAGING = "V3K_ANALYZER_MODULE_STAGING"
FLAG_CANDLE_ANALYSIS = "캔들분석"
FLAG_VOLUME_SPIKE_ANALYSIS = "거래량분석"
FLAG_VOLUME_PROFILE_ANALYSIS = "가격대분석"
FLAG_VOLATILITY_PATTERN_ANALYSIS = "변동성분석"
FLAG_VOLATILITY_STOP_TAKE_ANALYSIS = "변손익분석"
FLAG_RISK_ANALYSIS = "리스크분석"
FLAG_PHASE_F_ANALYZER_STRATEGY = "V3K_PHASE_F_ANALYZER_STRATEGY"
ENV_PHASE_F_ENABLE = "V3K_PHASE_F_ENABLE"
ENV_PHASE_F_DISABLE = "V3K_PHASE_F_DISABLE"
DB_FLAG_PHASE_F_ANALYZER_STRATEGY = "phase_f_analyzer_strategy.enabled"

FIELD_INDEX = "index"
FIELD_CURRENT_PRICE = "현재가"
FIELD_DAY_TRADE_VALUE = "당일거래대금"
FIELD_OPEN_PRICE = "시가"
FIELD_HIGH_PRICE = "고가"
FIELD_LOW_PRICE = "저가"
FIELD_MIN_OPEN_PRICE = "분봉시가"
FIELD_MIN_HIGH_PRICE = "분봉고가"
FIELD_MIN_LOW_PRICE = "분봉저가"
FIELD_TICK_TRADE_VALUE = "초당거래대금"
FIELD_MIN_TRADE_VALUE = "분당거래대금"
FIELD_CHEGYEOL_STRENGTH = "체결강도"
FIELD_TICK_BUY_VOLUME = "초당매수수량"
FIELD_TICK_SELL_VOLUME = "초당매도수량"
FIELD_MIN_BUY_VOLUME = "분당매수수량"
FIELD_MIN_SELL_VOLUME = "분당매도수량"
FIELD_HIGH_LOW_RATIO = "고저평균대비등락율"
FIELD_MAX_CURRENT_PRICE = "최고현재가"
FIELD_MIN_CURRENT_PRICE = "최저현재가"
FIELD_CHEGYEOL_STRENGTH_AVG = "체결강도평균"
FIELD_CHANGE_RATE_ANGLE = "등락율각도"

MARKET_GUBUN_TO_TYPE = {
    1: "stock",
    2: "future",
}

DEFAULT_FLAGS = {
    FLAG_BACKTEST_LEARNING: False,
    FLAG_REALTIME_LEARNING: False,
    FLAG_ANALYSIS_UI: False,
    FLAG_FORMULA_GLOBAL_FACADE: False,
    FLAG_STG_GLOBALS_FACADE: False,
    FLAG_RISK_ANALYZER_V3: False,
    FLAG_ANALYZER_MODULE_STAGING: False,
    FLAG_CANDLE_ANALYSIS: False,
    FLAG_VOLUME_SPIKE_ANALYSIS: False,
    FLAG_VOLUME_PROFILE_ANALYSIS: False,
    FLAG_VOLATILITY_PATTERN_ANALYSIS: False,
    FLAG_VOLATILITY_STOP_TAKE_ANALYSIS: False,
    FLAG_RISK_ANALYSIS: False,
    FLAG_PHASE_F_ANALYZER_STRATEGY: False,
}

RISK_COMMON_FIELDS = (
    FIELD_CURRENT_PRICE,
    FIELD_DAY_TRADE_VALUE,
    FIELD_CHEGYEOL_STRENGTH,
    FIELD_HIGH_LOW_RATIO,
    FIELD_MAX_CURRENT_PRICE,
    FIELD_MIN_CURRENT_PRICE,
    FIELD_CHEGYEOL_STRENGTH_AVG,
    FIELD_CHANGE_RATE_ANGLE,
)

RISK_TICK_FIELDS = (
    FIELD_TICK_BUY_VOLUME,
    FIELD_TICK_SELL_VOLUME,
)

RISK_MIN_FIELDS = (
    FIELD_MIN_BUY_VOLUME,
    FIELD_MIN_SELL_VOLUME,
)

AnalyzerKind = Literal[
    "candle_pattern",
    "volume_spike",
    "volume_profile",
    "volatility_pattern",
    "volatility_stop_take",
    "risk",
]


@dataclass(frozen=True)
class AnalyzerModuleContract:
    kind: AnalyzerKind
    module_name: str
    class_name: str
    feature_flag: str
    tick_fields: tuple[str, ...]
    min_fields: tuple[str, ...]
    output_names: tuple[str, ...]
    db_name: str | None = None
    runtime_wired: bool = False

    def required_fields(self, is_tick: bool) -> tuple[str, ...]:
        return self.tick_fields if is_tick else self.min_fields


@dataclass(frozen=True)
class LearningDbContract:
    kind: AnalyzerKind
    db_name: str
    table_template: str
    order_columns: tuple[str, ...]

    def table_name(self, strategy_gubun: str, is_tick: bool) -> str:
        safe_strategy = safe_identifier(strategy_gubun)
        timeframe = "tick" if is_tick else "min"
        return self.table_template.format(
            strategy_gubun=safe_strategy,
            timeframe=timeframe,
        )


ANALYZER_MODULE_CONTRACTS: dict[AnalyzerKind, AnalyzerModuleContract] = {
    "candle_pattern": AnalyzerModuleContract(
        kind="candle_pattern",
        module_name="strategy.analyzer_candle_pattern",
        class_name="AnalyzerCandlePattern",
        feature_flag=FLAG_CANDLE_ANALYSIS,
        tick_fields=(),
        min_fields=(
            FIELD_CURRENT_PRICE,
            FIELD_MIN_OPEN_PRICE,
            FIELD_MIN_HIGH_PRICE,
            FIELD_MIN_LOW_PRICE,
        ),
        output_names=("패턴점수", "패턴신뢰도"),
        db_name="pattern_analysis.db",
    ),
    "volume_spike": AnalyzerModuleContract(
        kind="volume_spike",
        module_name="strategy.analyzer_volume_spike",
        class_name="AnalyzerVolumeSpike",
        feature_flag=FLAG_VOLUME_SPIKE_ANALYSIS,
        tick_fields=(FIELD_CURRENT_PRICE, FIELD_TICK_TRADE_VALUE),
        min_fields=(FIELD_CURRENT_PRICE, FIELD_MIN_TRADE_VALUE),
        output_names=("거래량점수", "거래량신뢰도"),
        db_name="volume_spike.db",
    ),
    "volume_profile": AnalyzerModuleContract(
        kind="volume_profile",
        module_name="strategy.analyzer_volume_profile",
        class_name="AnalyzerVolumeProfile",
        feature_flag=FLAG_VOLUME_PROFILE_ANALYSIS,
        tick_fields=(FIELD_CURRENT_PRICE, FIELD_TICK_TRADE_VALUE),
        min_fields=(FIELD_CURRENT_PRICE, FIELD_MIN_TRADE_VALUE),
        output_names=("가격대점수", "가격대신뢰도"),
        db_name="volume_profile.db",
    ),
    "volatility_pattern": AnalyzerModuleContract(
        kind="volatility_pattern",
        module_name="strategy.analyzer_volatility_pattern",
        class_name="AnalyzerVolatilityPattern",
        feature_flag=FLAG_VOLATILITY_PATTERN_ANALYSIS,
        tick_fields=(FIELD_CURRENT_PRICE,),
        min_fields=(FIELD_CURRENT_PRICE,),
        output_names=("변동성점수", "변동성신뢰도"),
        db_name="volatility_pattern.db",
    ),
    "volatility_stop_take": AnalyzerModuleContract(
        kind="volatility_stop_take",
        module_name="strategy.analyzer_volatility_stop_take",
        class_name="AnalyzerVolatilityStopTake",
        feature_flag=FLAG_VOLATILITY_STOP_TAKE_ANALYSIS,
        tick_fields=(FIELD_CURRENT_PRICE,),
        min_fields=(FIELD_CURRENT_PRICE,),
        output_names=("예상수익률", "익절수익률", "손절수익률", "변손익신뢰도"),
        db_name="volatility_stop_take.db",
    ),
    "risk": AnalyzerModuleContract(
        kind="risk",
        module_name="strategy.analyzer_risk",
        class_name="AnalyzerRisk",
        feature_flag=FLAG_RISK_ANALYSIS,
        tick_fields=RISK_COMMON_FIELDS + RISK_TICK_FIELDS,
        min_fields=RISK_COMMON_FIELDS + RISK_MIN_FIELDS,
        output_names=("리스크점수",),
        db_name=None,
    ),
}


LEARNING_DB_CONTRACTS: dict[AnalyzerKind, LearningDbContract] = {
    "candle_pattern": LearningDbContract(
        kind="candle_pattern",
        db_name="pattern_analysis.db",
        table_template="{strategy_gubun}_pattern_score",
        order_columns=("last_update", "confidence_score"),
    ),
    "volume_spike": LearningDbContract(
        kind="volume_spike",
        db_name="volume_spike.db",
        table_template="{strategy_gubun}_volume_spike_{timeframe}",
        order_columns=("last_update", "confidence_score"),
    ),
    "volume_profile": LearningDbContract(
        kind="volume_profile",
        db_name="volume_profile.db",
        table_template="{strategy_gubun}_volume_score_{timeframe}",
        order_columns=("last_update", "confidence_score"),
    ),
    "volatility_pattern": LearningDbContract(
        kind="volatility_pattern",
        db_name="volatility_pattern.db",
        table_template="{strategy_gubun}_volatility_pattern_{timeframe}",
        order_columns=("last_update", "confidence_score"),
    ),
    "volatility_stop_take": LearningDbContract(
        kind="volatility_stop_take",
        db_name="volatility_stop_take.db",
        table_template="{strategy_gubun}_volatility_{timeframe}",
        order_columns=("last_update", "confidence_score"),
    ),
}


@dataclass(frozen=True)
class V3KAnalyzerContext:
    """Adapter input that keeps V3 analyzer wiring explicit and side-effect free."""

    market_gubun: int
    market_type: str
    is_tick: bool
    dict_findex: dict[str, int]
    code_data: np.ndarray
    code: str = ""
    backtest_date: int | str | None = None
    current_price: float | int | None = None
    feature_flags: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LearningLoadRequest:
    kind: AnalyzerKind
    code: str
    backtest_date: int | str
    strategy_gubun: str
    is_tick: bool
    feature_flags: dict[str, Any] = field(default_factory=dict)
    limit: int | None = None


@dataclass(frozen=True)
class LearningLoadResult:
    request: LearningLoadRequest
    db_path: Path
    table_name: str
    query: str | None
    params: tuple[Any, ...]
    rows: tuple[dict[str, Any], ...] = ()
    diagnostics: tuple[str, ...] = ()

    @property
    def has_rows(self) -> bool:
        return bool(self.rows)


@dataclass(frozen=True)
class ProductionLearningDbReadResult:
    db_path: Path
    table_name: str
    uri: str | None
    exists: bool
    table_exists: bool = False
    columns: tuple[dict[str, Any], ...] = ()
    rows: tuple[dict[str, Any], ...] = ()
    diagnostics: tuple[str, ...] = ()

    @property
    def has_rows(self) -> bool:
        return bool(self.rows)


@dataclass(frozen=True)
class RealtimeLearningPreloadRequest:
    codes: tuple[str, ...]
    as_of_date: int | str
    strategy_gubun: str
    is_tick: bool
    feature_flags: dict[str, Any] = field(default_factory=dict)
    limit: int | None = None


@dataclass(frozen=True)
class RealtimeLearningPreloadResult:
    request: RealtimeLearningPreloadRequest
    load_results: tuple[LearningLoadResult, ...] = ()
    diagnostics: tuple[str, ...] = ()

    @property
    def has_rows(self) -> bool:
        return any(result.has_rows for result in self.load_results)


@dataclass(frozen=True)
class V3KAnalyzerOutput:
    """Neutral result bundle for future V3K analyzer outputs.

    IMPL-2A only wires the dormant AnalyzerRisk smoke path. Other fields remain
    reserved for later stages and must not affect order/exit logic yet.
    """

    risk_score: float | None = None
    diagnostics: tuple[str, ...] = ()

    @property
    def has_signal(self) -> bool:
        return self.risk_score is not None


@dataclass(frozen=True)
class V3KPhaseFAnalyzerGateResult:
    """Phase F pre-ON dual-gate decision without touching runtime state."""

    env_enabled: bool
    db_enabled: bool
    rollback_disabled: bool
    enabled: bool
    diagnostics: tuple[str, ...] = ()


def normalize_v3k_flags(raw_flags: dict[str, Any] | None) -> dict[str, bool]:
    flags = dict(DEFAULT_FLAGS)
    if not raw_flags:
        return flags

    for key, value in raw_flags.items():
        if isinstance(value, str):
            flags[key] = value.strip().lower() in {"1", "true", "on", "yes", "y"}
        else:
            flags[key] = bool(value)
    return flags


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "on", "yes", "y"}
    return bool(value)


def evaluate_phase_f_analyzer_gate(
    env: Mapping[str, Any] | None = None,
    db_flags: Mapping[str, Any] | None = None,
) -> V3KPhaseFAnalyzerGateResult:
    """Evaluate the Phase F env+DB dual gate with rollback priority.

    This is a pre-ON helper. It reads caller-provided mappings only; it does not
    inspect or mutate ``os.environ`` or any SQLite DB. Runtime/live trading code
    can only consume this later through a separately approved F-4 cycle.
    """

    env = env or {}
    db_flags = db_flags or {}
    env_enabled = _truthy(env.get(ENV_PHASE_F_ENABLE, False))
    db_enabled = _truthy(db_flags.get(DB_FLAG_PHASE_F_ANALYZER_STRATEGY, False))
    rollback_disabled = _truthy(env.get(ENV_PHASE_F_DISABLE, False))
    enabled = env_enabled and db_enabled and not rollback_disabled

    diagnostics: list[str] = []
    if rollback_disabled:
        diagnostics.append("phase f rollback flag disabled analyzer strategy")
    elif enabled:
        diagnostics.append("phase f analyzer strategy dual gate enabled")
    else:
        missing: list[str] = []
        if not env_enabled:
            missing.append(ENV_PHASE_F_ENABLE)
        if not db_enabled:
            missing.append(DB_FLAG_PHASE_F_ANALYZER_STRATEGY)
        diagnostics.append("phase f analyzer strategy disabled: missing " + ", ".join(missing))

    return V3KPhaseFAnalyzerGateResult(
        env_enabled=env_enabled,
        db_enabled=db_enabled,
        rollback_disabled=rollback_disabled,
        enabled=enabled,
        diagnostics=tuple(diagnostics),
    )


def phase_f_formula_output_contract() -> dict[AnalyzerKind, tuple[str, ...]]:
    """Return analyzer kind -> formula output fields for Phase F smoke/audit."""

    return {
        kind: contract.output_names
        for kind, contract in ANALYZER_MODULE_CONTRACTS.items()
    }


def market_type_from_gubun(market_gubun: int) -> str:
    return MARKET_GUBUN_TO_TYPE.get(market_gubun, "coin")


def safe_identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_]+", value):
        raise ValueError(f"unsafe SQL identifier: {value!r}")
    return value


def safe_db_filename(value: str) -> str:
    if Path(value).name != value or not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        raise ValueError(f"unsafe DB filename: {value!r}")
    if not value.endswith(".db"):
        raise ValueError(f"production learning DB filename must end with .db: {value!r}")
    return value


def quoted_identifier(value: str) -> str:
    safe = safe_identifier(value)
    return f'"{safe}"'


def resolve_field(
    dict_findex: dict[str, int],
    *candidate_names: str,
    required: bool = False,
) -> int | None:
    for name in candidate_names:
        if name in dict_findex:
            return dict_findex[name]
    if required:
        raise KeyError(f"missing required V3K field: {candidate_names!r}")
    return None


def slice_window(arry_code: np.ndarray, index: int, tick_count: int) -> np.ndarray:
    if tick_count <= 0:
        raise ValueError("tick_count must be positive")
    start = max(0, index + 1 - tick_count)
    return arry_code[start : index + 1, :]


def risk_required_fields(is_tick: bool) -> tuple[str, ...]:
    volume_fields = RISK_TICK_FIELDS if is_tick else RISK_MIN_FIELDS
    return RISK_COMMON_FIELDS + volume_fields


def missing_risk_fields(dict_findex: dict[str, int], is_tick: bool) -> tuple[str, ...]:
    return tuple(name for name in risk_required_fields(is_tick) if name not in dict_findex)


def staged_analyzer_modules() -> tuple[AnalyzerModuleContract, ...]:
    return tuple(ANALYZER_MODULE_CONTRACTS.values())


def learning_db_manifest() -> tuple[LearningDbContract, ...]:
    return tuple(LEARNING_DB_CONTRACTS.values())


def missing_analyzer_fields(
    kind: AnalyzerKind,
    dict_findex: dict[str, int],
    is_tick: bool,
) -> tuple[str, ...]:
    contract = ANALYZER_MODULE_CONTRACTS[kind]
    return tuple(name for name in contract.required_fields(is_tick) if name not in dict_findex)


def learning_db_contract(kind: AnalyzerKind) -> LearningDbContract:
    if kind not in LEARNING_DB_CONTRACTS:
        raise KeyError(f"{kind} does not have a V3K learning DB contract")
    return LEARNING_DB_CONTRACTS[kind]


def learning_query_for_request(request: LearningLoadRequest) -> tuple[str, tuple[Any, ...], str]:
    contract = learning_db_contract(request.kind)
    table_name = contract.table_name(request.strategy_gubun, request.is_tick)
    order_by = ", ".join(f"{safe_identifier(column)} DESC" for column in contract.order_columns)
    limit_sql = "" if request.limit is None else " LIMIT ?"
    query = (
        f"SELECT * FROM {table_name} "
        "WHERE code = ? AND last_update < ? "
        f"ORDER BY {order_by}{limit_sql}"
    )
    params: tuple[Any, ...]
    if request.limit is None:
        params = (request.code, int(request.backtest_date))
    else:
        params = (request.code, int(request.backtest_date), int(request.limit))
    return query, params, table_name


def build_market_info(
    market_gubun: int,
    is_tick: bool,
    dict_findex: dict[str, int],
) -> dict[str, Any]:
    return {
        "마켓구분": market_type_from_gubun(market_gubun),
        "팩터목록": {is_tick: list(dict_findex.keys())},
        "dict_findex": dict(dict_findex),
    }


def no_signal(*reasons: str) -> V3KAnalyzerOutput:
    return V3KAnalyzerOutput(risk_score=None, diagnostics=tuple(reasons))


class V3KLearningDataAdapter:
    """Read-only V3K learning-data load path for later backtest wiring.

    IMPL-3 only prepares the policy and read path. It does not create DB files,
    initialize analyzer DB classes, or connect to runtime backtest loops.
    """

    def __init__(
        self,
        base_dir: str | Path = "_database_v3k_shadow",
        feature_flags: dict[str, Any] | None = None,
        master_flag: str = FLAG_BACKTEST_LEARNING,
    ):
        self.base_dir = Path(base_dir)
        self.feature_flags = normalize_v3k_flags(feature_flags)
        self.master_flag = master_flag

    def _flags_for_request(self, request: LearningLoadRequest) -> dict[str, bool]:
        flags = dict(self.feature_flags)
        if request.feature_flags:
            flags.update(normalize_v3k_flags(request.feature_flags))
        return flags

    def learning_is_enabled(self, kind: AnalyzerKind, flags: dict[str, bool]) -> bool:
        contract = ANALYZER_MODULE_CONTRACTS[kind]
        return flags.get(self.master_flag, False) and flags.get(
            contract.feature_flag,
            False,
        )

    def db_path_for_kind(self, kind: AnalyzerKind) -> Path:
        contract = learning_db_contract(kind)
        return self.base_dir / contract.db_name

    def load_before_backtest(self, request: LearningLoadRequest) -> LearningLoadResult:
        flags = self._flags_for_request(request)
        db_path = self.db_path_for_kind(request.kind)
        query, params, table_name = learning_query_for_request(request)

        if not self.learning_is_enabled(request.kind, flags):
            return LearningLoadResult(
                request=request,
                db_path=db_path,
                table_name=table_name,
                query=query,
                params=params,
                diagnostics=("learning load disabled by V3K feature flags",),
            )

        if not db_path.exists():
            return LearningLoadResult(
                request=request,
                db_path=db_path,
                table_name=table_name,
                query=query,
                params=params,
                diagnostics=("learning DB missing; read-only load skipped",),
            )

        uri = db_path.resolve().as_uri() + "?mode=ro"
        try:
            with closing(sqlite3.connect(uri, uri=True)) as conn:
                conn.row_factory = sqlite3.Row
                rows = tuple(dict(row) for row in conn.execute(query, params).fetchall())
        except sqlite3.Error as exc:
            return LearningLoadResult(
                request=request,
                db_path=db_path,
                table_name=table_name,
                query=query,
                params=params,
                diagnostics=(f"read-only learning load failed: {type(exc).__name__}: {exc}",),
            )

        return LearningLoadResult(
            request=request,
            db_path=db_path,
            table_name=table_name,
            query=query,
            params=params,
            rows=rows,
            diagnostics=("read-only learning load executed",),
        )


class V3KRealtimeLearningAdapter:
    """Realtime preload boundary for V3K learning data.

    This adapter deliberately does not import Kiwoom receivers, traders, or
    strategy classes. It only prepares a read-only/missing-DB load boundary that
    later realtime code can call behind explicit feature flags.
    """

    def __init__(
        self,
        base_dir: str | Path = "_database_v3k_shadow",
        feature_flags: dict[str, Any] | None = None,
    ):
        self.feature_flags = normalize_v3k_flags(feature_flags)
        self.loader = V3KLearningDataAdapter(
            base_dir=base_dir,
            feature_flags=self.feature_flags,
            master_flag=FLAG_REALTIME_LEARNING,
        )

    def _flags_for_request(self, request: RealtimeLearningPreloadRequest) -> dict[str, bool]:
        flags = dict(self.feature_flags)
        if request.feature_flags:
            flags.update(normalize_v3k_flags(request.feature_flags))
        return flags

    @staticmethod
    def _learning_kinds_for_timeframe(is_tick: bool) -> tuple[AnalyzerKind, ...]:
        kinds: list[AnalyzerKind] = []
        for kind in LEARNING_DB_CONTRACTS:
            if kind == "candle_pattern" and is_tick:
                continue
            kinds.append(kind)
        return tuple(kinds)

    def preload(self, request: RealtimeLearningPreloadRequest) -> RealtimeLearningPreloadResult:
        flags = self._flags_for_request(request)
        if not flags.get(FLAG_REALTIME_LEARNING, False):
            return RealtimeLearningPreloadResult(
                request=request,
                diagnostics=("realtime learning preload disabled by V3K feature flags",),
            )

        if not request.codes:
            return RealtimeLearningPreloadResult(
                request=request,
                diagnostics=("realtime learning preload skipped: no codes",),
            )

        results: list[LearningLoadResult] = []
        for code in request.codes:
            for kind in self._learning_kinds_for_timeframe(request.is_tick):
                load_request = LearningLoadRequest(
                    kind=kind,
                    code=code,
                    backtest_date=request.as_of_date,
                    strategy_gubun=request.strategy_gubun,
                    is_tick=request.is_tick,
                    feature_flags=flags,
                    limit=request.limit,
                )
                results.append(self.loader.load_before_backtest(load_request))

        return RealtimeLearningPreloadResult(
            request=request,
            load_results=tuple(results),
            diagnostics=("realtime learning preload dry-run executed",),
        )


class V3KAnalyzerAdapter:
    """Feature-flagged adapter boundary for V3K analyzer rollout.

    The adapter is intentionally not imported by existing runtime paths. It is
    a staging surface for IMPL-2A smoke checks and later explicit backtest /
    realtime wiring.
    """

    def __init__(
        self,
        feature_flags: dict[str, Any] | None = None,
        production_db_dir: str | Path = "_database",
    ):
        self.feature_flags = normalize_v3k_flags(feature_flags)
        self.production_db_dir = Path(production_db_dir)

    def _flags_for_context(self, context: V3KAnalyzerContext) -> dict[str, bool]:
        flags = dict(self.feature_flags)
        if context.feature_flags:
            flags.update(normalize_v3k_flags(context.feature_flags))
        return flags

    def production_learning_db_path(self, db_name: str) -> Path:
        return self.production_db_dir / safe_db_filename(db_name)

    def read_production_learning_db(
        self,
        db_name: str,
        table_name: str,
        *,
        sample_limit: int = 1,
        retry_once: bool = True,
    ) -> ProductionLearningDbReadResult:
        """Read a production learning DB through SQLite ``mode=ro`` only.

        This method is a F5 boundary helper. It never creates DB files, never
        writes to ``_database/``, and intentionally returns diagnostics instead
        of raising on missing DB/table/lock cases.
        """

        db_path = self.production_learning_db_path(db_name)
        safe_table = quoted_identifier(table_name)
        if sample_limit < 0:
            raise ValueError("sample_limit must be non-negative")

        if not db_path.exists():
            return ProductionLearningDbReadResult(
                db_path=db_path,
                table_name=table_name,
                uri=None,
                exists=False,
                diagnostics=("production learning DB missing; read-only production read skipped",),
            )

        uri = db_path.resolve().as_uri() + "?mode=ro"
        attempts = 2 if retry_once else 1
        last_error: sqlite3.Error | None = None
        for attempt in range(attempts):
            try:
                with closing(sqlite3.connect(uri, uri=True, timeout=0.1)) as conn:
                    conn.row_factory = sqlite3.Row
                    conn.execute("PRAGMA query_only = ON")
                    table_exists = (
                        conn.execute(
                            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                            (table_name,),
                        ).fetchone()
                        is not None
                    )
                    if not table_exists:
                        return ProductionLearningDbReadResult(
                            db_path=db_path,
                            table_name=table_name,
                            uri=uri,
                            exists=True,
                            table_exists=False,
                            diagnostics=("production learning table missing; read-only production read skipped",),
                        )

                    columns = tuple(
                        dict(row) for row in conn.execute(f"PRAGMA table_info({safe_table})").fetchall()
                    )
                    if sample_limit == 0:
                        rows: tuple[dict[str, Any], ...] = ()
                    else:
                        rows = tuple(
                            dict(row)
                            for row in conn.execute(
                                f"SELECT * FROM {safe_table} LIMIT ?",
                                (int(sample_limit),),
                            ).fetchall()
                        )

                return ProductionLearningDbReadResult(
                    db_path=db_path,
                    table_name=table_name,
                    uri=uri,
                    exists=True,
                    table_exists=True,
                    columns=columns,
                    rows=rows,
                    diagnostics=("read-only production learning DB read executed",),
                )
            except sqlite3.OperationalError as exc:
                last_error = exc
                if "locked" in str(exc).lower() and attempt + 1 < attempts:
                    continue
                break
            except sqlite3.Error as exc:
                last_error = exc
                break

        return ProductionLearningDbReadResult(
            db_path=db_path,
            table_name=table_name,
            uri=uri,
            exists=True,
            diagnostics=(
                "read-only production learning DB read failed; no-op fallback",
                f"{type(last_error).__name__}: {last_error}",
            ),
        )

    @staticmethod
    def risk_is_enabled(flags: dict[str, bool]) -> bool:
        return (
            flags.get(FLAG_BACKTEST_LEARNING, False)
            and flags.get(FLAG_RISK_ANALYZER_V3, False)
            and flags.get(FLAG_RISK_ANALYSIS, False)
        )

    def analyze_risk(self, context: V3KAnalyzerContext) -> V3KAnalyzerOutput:
        flags = self._flags_for_context(context)
        if not self.risk_is_enabled(flags):
            return no_signal("risk analyzer disabled by V3K feature flags")

        missing = missing_risk_fields(context.dict_findex, context.is_tick)
        if missing:
            return no_signal(f"risk analyzer missing fields: {', '.join(missing)}")

        if context.code_data.ndim != 2:
            return no_signal("risk analyzer requires a 2D code_data window")

        if len(context.code_data) < 30:
            return no_signal("risk analyzer requires at least 30 rows")

        try:
            from strategy.analyzer_risk import AnalyzerRisk

            analyzer = AnalyzerRisk(
                context.market_type or market_type_from_gubun(context.market_gubun),
                context.dict_findex,
            )
            return V3KAnalyzerOutput(
                risk_score=float(analyzer.get_risk_score(context.code_data)),
                diagnostics=("risk analyzer executed",),
            )
        except Exception as exc:
            return no_signal(f"risk analyzer execution failed: {type(exc).__name__}: {exc}")
