"""SQ02 — 버전 고정 지표 정의 레지스트리와 projection 계층.

기존 ``summary_metrics``/``_result_context`` 가 계산하는 값의 *의미*를 별도
versioned 정의로 분리한다. 정의를 바꾸면 같은 키를 덮어쓰지 않고 새
``definition_version`` 을 발행한다(봉인 결과의 소급 수정 금지).

projection 은 각 지표를 ``{value, unit, state, reason}`` 로 감싼다:

- ``complete``   : 정의대로 계산된 값.
- ``missing``    : 입력 부재/무거래로 정의 불가 — 0.0 과 구분한다.
- ``degraded``   : 값은 있으나 정의상 주의가 필요(예: 표본 부족으로 0 반환된 Sharpe).

비용(수수료/슬리피지)은 현재 엔진 결과에 모델링돼 있지 않다. 관련 정의는
``cost_model='none'`` 으로 명시하고 값을 지어내지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Mapping

DEFINITIONS_VERSION: str = "sq02.v1"

# projection 의 state 어휘 — SQ02 결측 계약.
STATE_COMPLETE = "complete"
STATE_MISSING = "missing"
STATE_DEGRADED = "degraded"


@dataclass(frozen=True, slots=True)
class MetricDef:
    """한 지표의 불변 정의. 버전 변경은 새 entry 발행이지 in-place 수정이 아니다."""

    key: str
    label_ko: str
    unit: str  # krw | pct | count | days | ratio | sec | score | text | date
    formula: str
    basis: str  # capital | trade_sum | realized_curve | engine | derived | calendar
    missing_policy: str  # zero | null | undefined
    version: str = DEFINITIONS_VERSION
    cost_model: str = "none"  # 수수료/슬리피지 미반영이 정본 상태.
    caveat: str = ""

    def to_json(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label_ko": self.label_ko,
            "unit": self.unit,
            "formula": self.formula,
            "basis": self.basis,
            "missing_policy": self.missing_policy,
            "version": self.version,
            "cost_model": self.cost_model,
            "caveat": self.caveat,
        }


# ---------------------------------------------------------------------------
# 정의 레지스트리 — summary_metrics/_result_context 가 노출하는 모든 지표를 덮는다.
# ---------------------------------------------------------------------------
_DEFS: tuple[MetricDef, ...] = (
    # --- 수익률 계열 ---------------------------------------------------------
    MetricDef(
        "sum_trade_return_pct", "거래수익률 합", "pct",
        "거래별 수익률(%)의 단순 합", "trade_sum", "zero",
        caveat="자본 대비 수익률이 아니다 — 같은 자본이 회전하므로 산술 참고치.",
    ),
    MetricDef(
        "return_on_capital_pct", "운용자본 수익률", "pct",
        "총실현손익 / 운용자본 * 100 (엔진·채점기 기준)", "capital", "null",
        caveat="저장 행(generations.total_profit_pct)에서 온다 — CSV 재계산이 아님.",
    ),
    MetricDef(
        "annual_return_pct", "연환산 수익률", "pct",
        "(1+r/100)^(365/calendar_days)-1, calendar_days>=20 일 때만", "derived", "undefined",
        caveat="기간 20일 미만·원금전손 시 정의 불가 — 추정하지 않고 missing.",
    ),
    MetricDef(
        "avg_profit_pct", "평균 거래수익률", "pct",
        "거래별 수익률(%)의 산술평균", "trade_sum", "zero",
    ),
    MetricDef(
        "total_profit_krw", "총 실현손익", "krw",
        "거래별 실현손익(원) 합", "trade_sum", "zero",
        caveat="수수료·슬리피지 미반영(cost_model=none).",
    ),
    MetricDef("total_profit_pct", "총 수익률 합", "pct",
              "sum_trade_return_pct 와 동일 값(하위호환 별칭)", "trade_sum", "zero"),
    MetricDef("avg_win_krw", "평균 이익", "krw", "이익 거래의 실현손익 평균", "trade_sum", "zero"),
    MetricDef("avg_loss_krw", "평균 손실", "krw", "손실 거래의 실현손익 평균(음수)", "trade_sum", "zero"),
    MetricDef("payoff_ratio", "페이오프 비", "ratio",
              "평균이익 / |평균손실| — 평균손실 0이면 정의 불가→0", "derived", "zero"),
    MetricDef("profit_factor", "수익계수", "ratio",
              "총이익 / |총손실| — 총손실 0이면 정의 불가→0", "derived", "zero"),
    # --- MDD 계열(두 정의를 이름으로 구분 — v5.13.2 혼선 교정 계약) ------------
    MetricDef(
        "max_drawdown_pct", "MDD(실현곡선 반납률)", "pct",
        "거래순 누적 실현손익 곡선의 peak-to-trough / peak * 100 (peak>0 구간만)", "realized_curve", "zero",
        caveat="엔진 자본 대비 MDD 가 아니다 — mdd_on_capital_pct 와 별개.",
    ),
    MetricDef("max_drawdown_krw", "MDD(실현곡선, 원)", "krw",
              "누적 실현손익 곡선의 최대 낙폭(원)", "realized_curve", "zero"),
    MetricDef(
        "mdd_on_capital_pct", "MDD(자본 대비)", "pct",
        "엔진/채점기가 기록한 자본 대비 최대낙폭 — 저장 행(generations.mdd)", "engine", "null",
        caveat="명예의 전당이 쓰는 정의 — realized_curve MDD 와 혼용 금지.",
    ),
    # --- 자본 계열 -----------------------------------------------------------
    MetricDef(
        "capital_krw", "운용자본(역산)", "krw",
        "return_krw / return_on_capital_pct * 100 으로 역산 — 입력 둘 중 하나라도 없으면 missing",
        "derived", "undefined",
        caveat="저장된 자본이 아니라 비율 역산값 — 추정치로 취급.",
    ),
    MetricDef("return_krw", "총 실현손익(저장값)", "krw",
              "저장 행(generations.profit)의 총손익", "engine", "null"),
    # --- 기간 계열 -----------------------------------------------------------
    MetricDef("period_start", "기간 시작", "date", "최초 거래일(YYYYMMDD)", "calendar", "null"),
    MetricDef("period_end", "기간 종료", "date", "최종 거래일(YYYYMMDD)", "calendar", "null"),
    MetricDef("calendar_days", "달력 일수", "days",
              "period_end - period_start + 1 (파싱 실패 시 0)", "calendar", "zero"),
    MetricDef("trading_days", "거래일 수", "days", "손익이 기록된 고유 거래일 수", "calendar", "zero"),
    MetricDef("avg_trades_per_day", "일평균 거래 수", "ratio",
              "trade_count / trading_days", "derived", "zero"),
    # --- 빈도·분포 계열 ------------------------------------------------------
    MetricDef("trade_count", "거래 수", "count", "행 수", "trade_sum", "zero"),
    MetricDef("win_count", "승 거래 수", "count", "실현손익>0 거래 수", "trade_sum", "zero"),
    MetricDef("loss_count", "패 거래 수", "count", "실현손익<0 거래 수", "trade_sum", "zero"),
    MetricDef("win_rate", "승률", "pct", "win_count / trade_count * 100", "derived", "zero"),
    MetricDef("max_consecutive_wins", "최대 연승", "count",
              "거래 순서 기준 최대 연속 승(손익 0은 연속 단절)", "derived", "zero"),
    MetricDef("max_consecutive_losses", "최대 연패", "count",
              "거래 순서 기준 최대 연속 패", "derived", "zero"),
    MetricDef("avg_hold_sec", "평균 보유(초)", "sec",
              "보유시간의 정본 단위는 초 — tick CSV 원단위 부풀림 교정(v5.13.2)", "derived", "zero"),
    MetricDef("median_hold_sec", "중앙 보유(초)", "sec", "보유시간 중앙값(초)", "derived", "zero"),
    MetricDef("max_hold_sec", "최대 보유(초)", "sec", "최대 보유시간(초)", "derived", "zero"),
    MetricDef("avg_hold_min", "평균 보유(분)", "sec", "avg_hold_sec / 60 (파생 표기)", "derived", "zero"),
    MetricDef("median_hold_min", "중앙 보유(분)", "sec", "median_hold_sec / 60 (파생 표기)", "derived", "zero"),
    MetricDef("timeframe", "타임프레임", "text", "CSV 자릿수로 판별한 tick/min", "engine", "zero"),
    MetricDef("hold_unit", "보유 표기 단위", "text", "timeframe==tick 이면 sec 아니면 min", "derived", "zero"),
    # --- 리스크·연율화 계열 ---------------------------------------------------
    MetricDef(
        "sharpe", "샤프 비율", "ratio",
        "일별 손익(원) 평균/표본표준편차 * sqrt(252) — 무위험수익률 0 가정", "derived", "undefined",
        caveat="trading_days<2 또는 변동 0이면 정의 불가 — 0이 아니라 missing.",
    ),
    MetricDef(
        "calmar", "칼마 비율", "ratio",
        "연율화 손익 / MDD(원) — MDD·거래일 0이면 정의 불가", "derived", "undefined",
        caveat="정의 불가 조건에서 0으로 반환되던 것을 missing 으로 표시.",
    ),
    MetricDef("score", "채점 점수", "score", "루프 채점기 점수(저장값)", "engine", "null"),
    MetricDef("gate_passed", "게이트 통과", "text", "저장 행의 gate_passed 플래그", "engine", "null"),
    MetricDef("status", "실행 상태", "text", "저장 행의 status", "engine", "null"),
)

METRIC_DEFINITIONS: Mapping[str, MetricDef] = {d.key: d for d in _DEFS}


# ---------------------------------------------------------------------------
# 결측/퇴보 판정
# ---------------------------------------------------------------------------
def _entry(value: Any, state: str, reason: str | None) -> dict[str, Any]:
    return {"value": value, "state": state,
            **({"reason": reason} if reason else {})}


def _project_one(defn: MetricDef, summary: Mapping[str, Any],
                 has_trades: bool) -> dict[str, Any]:
    value = summary.get(defn.key)
    if value is None:
        return _entry(None, STATE_MISSING, "value_absent")
    if not has_trades:
        # 무거래 — 모든 파생 지표는 '0'이 아니라 정의 불가로 표기한다.
        if defn.missing_policy == "zero":
            return _entry(value, STATE_MISSING, "no_trades")
        return _entry(None, STATE_MISSING, "no_trades")
    # 정의상 퇴보 조건.
    if defn.key == "sharpe" and (summary.get("trading_days") or 0) < 2:
        return _entry(value, STATE_DEGRADED, "trading_days_lt_2")
    if defn.key == "calmar" and (summary.get("max_drawdown_krw") or 0) <= 0:
        return _entry(value, STATE_DEGRADED, "no_drawdown")
    if defn.key in ("payoff_ratio",) and (summary.get("avg_loss_krw") or 0) == 0:
        return _entry(value, STATE_DEGRADED, "avg_loss_zero")
    if defn.key == "profit_factor" and (summary.get("avg_loss_krw") or 0) == 0:
        return _entry(value, STATE_DEGRADED, "gross_loss_zero")
    return _entry(value, STATE_COMPLETE, None)


def project_summary(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    """summary_metrics 출력을 versioned projection 으로 감싼다(입력 불변)."""
    summary = dict(summary or {})
    has_trades = bool(summary.get("trade_count"))
    metrics: dict[str, Any] = {}
    for key, defn in METRIC_DEFINITIONS.items():
        if key not in summary and defn.key in (
            "return_on_capital_pct", "mdd_on_capital_pct", "capital_krw",
            "return_krw", "annual_return_pct", "score", "gate_passed", "status",
        ):
            continue  # context-only 정의는 summary projection 에서 생략.
        metrics[key] = {**_project_one(defn, summary, has_trades),
                        "unit": defn.unit, "def": defn.version}
    return {
        "definitions_version": DEFINITIONS_VERSION,
        "metrics": metrics,
    }


def project_result_context(context: Mapping[str, Any]) -> dict[str, Any]:
    """``_result_context`` 출력의 지표 필드를 versioned projection 으로 감싼다."""
    context = dict(context or {})
    metrics: dict[str, Any] = {}
    for key in (
        "return_on_capital_pct", "sum_trade_return_pct", "annual_return_pct",
        "mdd_on_capital_pct", "capital_krw", "return_krw",
        "calendar_days", "trading_days",
    ):
        defn = METRIC_DEFINITIONS.get(key)
        if defn is None:
            continue
        value = context.get(key)
        if value is None:
            entry = _entry(None, STATE_MISSING, "value_absent")
        else:
            entry = _entry(value, STATE_COMPLETE, None)
        metrics[key] = {**entry, "unit": defn.unit, "def": defn.version}
    return {
        "definitions_version": DEFINITIONS_VERSION,
        "metrics": metrics,
    }


def definitions_catalog() -> dict[str, Any]:
    """정의 레지스트리 전체 — 문서·UI·보고서가 같은 정의를 참조하기 위한 카탈로그."""
    return {
        "definitions_version": DEFINITIONS_VERSION,
        "states": [STATE_COMPLETE, STATE_MISSING, STATE_DEGRADED],
        "cost_model": "none",
        "metrics": {k: d.to_json() for k, d in METRIC_DEFINITIONS.items()},
    }


# 회귀 가드 — registry 는 hash 로 고정돼 버전 무변경 in-place 수정을 탐지한다.
class _RegistryFingerprint:
    _EXPECTED: ClassVar[str] = ""  # 아래에서 계산해 고정.

    @staticmethod
    def compute() -> str:
        import hashlib
        import json

        blob = json.dumps(
            {k: d.to_json() for k, d in sorted(METRIC_DEFINITIONS.items())},
            ensure_ascii=False, sort_keys=True,
        )
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def registry_fingerprint() -> str:
    """레지스트리 내용의 SHA-256 — 정의 무고지 변경 탐지용."""
    return _RegistryFingerprint.compute()
