"""시드 격자 열거기 (T1.1+T1.2) — lane × time_band × cap_tier × regime 격자 위 패턴 패밀리 시드 생성.

격자 축 (DB 커버리지 실측 기반, 2026-06 재확인):
  - lane: 'tick' | 'min'.
      tick: ``_database/stock_tick_YYYYMMDD.db`` 952일(2022-03-23~2026-02-27),
            각 일 09:00:00~09:30:00 만 존재 → 시간밴드 = 09:00~09:30 내 5분 버킷 6개.
      min : ``_database/stock_min_back.db`` moneytop 2025-04-07~2026-02-27 풀세션
            → 시간밴드 = 36셀 지도(M1) 밴드 정의 재사용: 09·10·11·13·14시·14:30+
            (12시 점심 밴드 없음 — docs/research/condition_research/
            2026-06-13_entry_extension_and_min_roadmap.md §M1).
            청산 규약: force_exit 145900 + entry_end <= 144500.
  - cap_tier: 4단계 (소형/중소/중대/대형). 시가총액(억원)은 tick/min 공통 스칼라이므로
      **조건식 안에서 직접 표현한다** (후처리 필터 축이 아님). 참고: r8 계열은
      baseline buy 뒤 후위 필터(``if 매수: if not (시가총액 >= N): 매수 = False``)
      관용구도 쓰지만(prepare_proxy_oos_20260619.py), 격자에서는 in-code 밴드가 정본.
  - regime: 등락율(-30~30) 3구간 (저/중/고).

패턴 패밀리 (첫 돌파 순수 모멘텀 계열만 — 완화 임계 기본값):
  셀당 train 거래 >= 300건 목표. 임계 기본값은 의도적으로 느슨하게(거래수 우선) 잡고,
  스윕/지도 단계에서 조인다.

  기각 확정 계열은 격자에서 **전면 제외**한다 (breadth 평가 §D: 생존 = 첫 돌파 순수
  모멘텀뿐 — .omo/evidence/condition-generation-breadth-evaluation-20260617/):
    - F04 매도흡수, F18 재진입, F03 눌림회복: 흡수/되돌림/재진입 '두 번째 기회' 계열
      전멸 기각 → 눌림 리테스트류 패밀리를 등록하지 않는다.
    - F10 대형주추세: 패밀리로서 전멸 기각. (대형 cap_tier 셀 자체는 지도 커버리지
      측정용 축으로 유지 — 패밀리 기각과 축 유지는 별개.)

코드 생성:
  - buy: :mod:`ai_strategy_loop.brain.band_compiler` (읽기 전용 소비) 의
    :func:`compile_to_code` 로 엔진 정규형(``매수=True`` → 가드 체인 → ``if 매수:
    self.Buy()``) 결정론 컴파일. time_band 는 ``시분초`` HHMMSS 게이트.
  - sell: band_compiler 는 buy 전용 표현이므로 자체 템플릿 문자열 조립
    (``매도=False`` → ``if 매도: self.Sell()`` 관용구, tmap 템플릿과 동일 형).
  - 모든 생성 코드는 ``compile(code, '<seed>', 'exec')`` 구문 검증 +
    :func:`ai_strategy_loop.brain.token_check.check_tokens` 통과가 필수다
    (:func:`build_seed` 내부에서 강제).

외부 패밀리 등록: :func:`load_pattern_families` 가 JSON 파일에서 패밀리를 읽어
dict 로 돌려준다 (Phase 4 가 chart_sulsa 21개를 이 형식으로 공급 예정). 병합은
``{**default_pattern_families(), **load_pattern_families(path)}`` 처럼 불변으로.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple, Union

from ai_strategy_loop.brain.band_compiler import (
    BandSpec,
    BandStrategy,
    Clause,
    FixedFragment,
    TimeBranch,
    compile_to_code,
)
from ai_strategy_loop.brain.token_check import check_tokens

_VALID_LANES = ("tick", "min")


# ---------------------------------------------------------------------------
# 숫자 포맷 — band_compiler._fmt 과 동일 규칙 (정수는 정수, 실수는 소수점 보존)
# ---------------------------------------------------------------------------
def _fmt_num(x: Union[int, float]) -> str:
    """파라미터 값을 시드 리터럴 스타일 문자열로 포맷한다.

    band_compiler 의 규칙을 따른다: int → ``str(int)``, 정수값 float → ``8.0``,
    그 외 float → ``:g``. (private ``_fmt`` 를 import 하지 않고 규칙만 복제 —
    band_compiler 는 읽기 전용.)

    Args:
        x: 포맷할 정수 또는 실수.

    Returns:
        시드 리터럴 표기 문자열.
    """
    if isinstance(x, bool):
        raise TypeError("파라미터 값은 bool 일 수 없습니다")
    if isinstance(x, int):
        return str(x)
    if x == int(x):
        return f"{int(x)}.0"
    return f"{x:g}"


# ---------------------------------------------------------------------------
# 격자 축 dataclass
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TimeBand:
    """시간밴드 축 원소 (``시분초`` HHMMSS 정수 반열림 구간 [start, end)).

    Attributes:
        label: 밴드 라벨 (cell_id 구성 요소, ASCII).
        start: 시작 시분초 (포함).
        end: 종료 시분초 (미포함).
    """

    label: str
    start: int
    end: int


@dataclass(frozen=True)
class CapTier:
    """시가총액(억원) 단계 축 원소. lo/hi 반열림 [lo, hi); None 은 무경계.

    Attributes:
        name: 단계 이름 (small/midsmall/midlarge/large).
        lo: 하한 (포함, None=하한 없음).
        hi: 상한 (미포함, None=상한 없음).
    """

    name: str
    lo: Optional[float]
    hi: Optional[float]


@dataclass(frozen=True)
class Regime:
    """등락율 국면 축 원소 (반열림 [lo, hi), 도메인 -30~30).

    Attributes:
        name: 국면 이름 (low/mid/high).
        lo: 하한 (포함).
        hi: 상한 (미포함).
    """

    name: str
    lo: float
    hi: float


@dataclass(frozen=True)
class Cell:
    """격자 셀 = lane × time_band × cap_tier × regime 조합 하나.

    Attributes:
        cell_id: 결정론 식별자 ``{lane}_{band.label}_{cap.name}_{regime.name}``.
        lane: 'tick' | 'min'.
        band: 시간밴드.
        cap: 시가총액 단계.
        regime: 등락율 국면.
    """

    cell_id: str
    lane: str
    band: TimeBand
    cap: CapTier
    regime: Regime


# --- 기본 축 정의 ---
# tick: 09:00~09:30 내 5분 버킷 6개 (DB 가 그 창만 존재).
TICK_BANDS: Tuple[TimeBand, ...] = (
    TimeBand("0900", 90000, 90500),
    TimeBand("0905", 90500, 91000),
    TimeBand("0910", 91000, 91500),
    TimeBand("0915", 91500, 92000),
    TimeBand("0920", 92000, 92500),
    TimeBand("0925", 92500, 93000),
)

# min: 36셀 지도(M1) 밴드 재사용 — 09·10·11·13·14시·14:30+ (12시 없음),
#   entry_end <= 144500 (마지막 밴드 상한), force_exit 145900 은 sell 쪽 규약.
MIN_BANDS: Tuple[TimeBand, ...] = (
    TimeBand("09h", 90000, 100000),
    TimeBand("10h", 100000, 110000),
    TimeBand("11h", 110000, 120000),
    TimeBand("13h", 130000, 140000),
    TimeBand("14h", 140000, 143000),
    TimeBand("1430p", 143000, 144500),
)

# 시가총액 4단계 (억원). 1500/3000 은 기존 관용 경계(r8_exclude_cap_lt_1500,
#   seed McapBlock cap_lt=3000), 10000 은 중대/대형 분리 경계.
CAP_TIERS: Tuple[CapTier, ...] = (
    CapTier("small", None, 1500.0),
    CapTier("midsmall", 1500.0, 3000.0),
    CapTier("midlarge", 3000.0, 10000.0),
    CapTier("large", 10000.0, None),
)

# 등락율 3구간 (완화 임계 — 거래수 우선). 상한 29.0 은 상한가(30) 직전 컷.
REGIMES: Tuple[Regime, ...] = (
    Regime("low", 0.0, 3.0),
    Regime("mid", 3.0, 8.0),
    Regime("high", 8.0, 29.0),
)


@dataclass(frozen=True)
class LatticeConfig:
    """격자 열거 설정. 기본값 = 모듈 상수 축 (2×6×4×3 = 144셀).

    Attributes:
        lanes: 열거할 레인들.
        tick_bands: tick 시간밴드 축.
        min_bands: min 시간밴드 축.
        cap_tiers: 시가총액 단계 축.
        regimes: 등락율 국면 축.
    """

    lanes: Tuple[str, ...] = _VALID_LANES
    tick_bands: Tuple[TimeBand, ...] = TICK_BANDS
    min_bands: Tuple[TimeBand, ...] = MIN_BANDS
    cap_tiers: Tuple[CapTier, ...] = CAP_TIERS
    regimes: Tuple[Regime, ...] = REGIMES


def enumerate_cells(config: Optional[LatticeConfig] = None) -> List[Cell]:
    """격자 축의 곱으로 셀을 결정론 열거한다.

    순서 고정: lane → time_band → cap_tier → regime (선언 순서). 같은 config 는
    항상 같은 리스트를 돌려준다.

    Args:
        config: 격자 설정 (None 이면 기본 :class:`LatticeConfig`).

    Returns:
        :class:`Cell` 리스트 (기본 설정에서 2×6×4×3 = 144개).

    Raises:
        ValueError: 알 수 없는 lane 이 설정에 있을 때.
    """
    cfg = config if config is not None else LatticeConfig()
    cells: List[Cell] = []
    for lane in cfg.lanes:
        if lane not in _VALID_LANES:
            raise ValueError(f"알 수 없는 lane: {lane!r} (허용: {_VALID_LANES})")
        bands = cfg.tick_bands if lane == "tick" else cfg.min_bands
        for band in bands:
            for cap in cfg.cap_tiers:
                for regime in cfg.regimes:
                    cell_id = f"{lane}_{band.label}_{cap.name}_{regime.name}"
                    cells.append(Cell(cell_id, lane, band, cap, regime))
    return cells


# ---------------------------------------------------------------------------
# 패턴 패밀리
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ParamSpec:
    """패밀리 파라미터 정의 (기본값 + 허용 범위).

    Attributes:
        name: 파라미터 이름 (buy 조각 템플릿의 ``{name}`` placeholder).
        default: 기본값 (완화 임계 — 거래수 우선).
        lo: 허용 하한 (포함).
        hi: 허용 상한 (포함).
        integer: True 면 정수만 허용 (윈도우 인자 등).
    """

    name: str
    default: float
    lo: float
    hi: float
    integer: bool = False


@dataclass(frozen=True)
class PatternFamily:
    """패턴 패밀리 = 이름 → (buy 조각 템플릿, sell 파라미터 오버라이드, 파라미터 스펙).

    buy 조각 템플릿은 lane 키('tick'/'min'/'common') → 조건 표현식 문자열 튜플.
    각 조각은 ``{param}`` placeholder 를 가질 수 있고, 셀 빌드 시
    :class:`FixedFragment` 로 밴드 가드 체인에 이어진다. sell 은 공통 청산 템플릿
    (:data:`SELL_DEFAULTS` 참조) 에 ``sell_overrides`` 를 겹쳐 만든다.

    Attributes:
        name: 패밀리 이름 (레지스트리 키).
        description: 한 줄 설명 (프리미티브 매핑 포함).
        lanes: 지원 레인 튜플.
        buy_fragments: lane → 조건 조각 템플릿 튜플. 'common' 키는 양 레인 공용.
        params: buy 파라미터 스펙 튜플.
        sell_overrides: lane 기본 sell 파라미터 위에 겹칠 값들.
        source: 출처 ('builtin' 또는 JSON 경로).
    """

    name: str
    description: str
    lanes: Tuple[str, ...]
    buy_fragments: Mapping[str, Tuple[str, ...]]
    params: Tuple[ParamSpec, ...]
    sell_overrides: Mapping[str, float] = field(default_factory=dict)
    source: str = "builtin"

    def buy_template(self, cell: Cell, params: Mapping[str, Union[int, float]]) -> str:
        """이 패밀리의 buy 템플릿 함수 — 셀+파라미터로 buy 코드를 생성한다."""
        return build_buy_code(cell, self, params)

    def sell_template(self, cell: Cell, params: Mapping[str, Union[int, float]]) -> str:
        """이 패밀리의 sell 템플릿 함수 — 셀+파라미터로 sell 코드를 생성한다."""
        return build_sell_code(cell, self, params)


def default_pattern_families() -> Dict[str, PatternFamily]:
    """내장 패밀리 레지스트리를 새로 만들어 돌려준다 (불변 병합용).

    셀당 train 거래 >= 300건 목표에 맞춰 임계 기본값은 전부 완화(느슨)하게 둔다.
    구성 4계열은 M1 지도 프리미티브 중 첫 돌파/활성 계열만이다:
      - momentum_breakout ← 신고가 돌파
      - volume_surge      ← 거래대금 급증
      - strength_surge    ← 체결강도 급등
      - prevday_active    ← 전일동시간비 고활성

    제외(등록 금지) 계열과 사유 링크:
      - F04 매도흡수 / F18 재진입 / F03 눌림회복(눌림 리테스트): '두 번째 기회'
        계열 전멸 기각 — .omo/evidence/condition-generation-breadth-evaluation-
        20260617/ §D (생존 = 첫 돌파 순수 모멘텀뿐).
      - F10 대형주추세: 패밀리 전멸 기각 (대형 cap 축은 지도 측정용으로만 유지).
      - 보류(F09 VI·F17 유계 근사·F08/F13/F15)와 F19(스모크 선별 의무)는 이후
        JSON 공급 단계에서 판단 — 여기서는 싣지 않는다.

    Returns:
        이름 → :class:`PatternFamily` dict (호출마다 새 dict).
    """
    families = (
        PatternFamily(
            name="momentum_breakout",
            description="신고가 돌파 — 당일 고가 재돌파 첫 진입 (첫 돌파 순수 모멘텀)",
            lanes=("tick", "min"),
            buy_fragments={"common": ("현재가 >= 고가 * {high_mult}",)},
            # 고가는 당일 고가(현재 tick 포함)라 현재가 > 고가 가 불가 → 상한 1.0
            # (1.0 초과는 충족 불가 사구간). 기본값은 완화 규약(거래수 우선)에 따라
            # 최엄격점 1.0 이 아닌 0.995(고가 근접 재돌파)로 둔다.
            params=(ParamSpec("high_mult", 0.995, 0.98, 1.0),),
        ),
        PatternFamily(
            name="volume_surge",
            description="거래대금 급증 — 레인별 초당/분당 거래대금의 창평균 대비 배수",
            lanes=("tick", "min"),
            buy_fragments={
                "tick": ("초당거래대금 >= 초당거래대금평균({avg_win}) * {surge_mult}",),
                "min": ("분당거래대금 >= 분당거래대금평균({avg_win}) * {surge_mult}",),
            },
            params=(
                ParamSpec("avg_win", 30, 5, 120, integer=True),
                ParamSpec("surge_mult", 2.0, 1.2, 6.0),
            ),
        ),
        PatternFamily(
            name="strength_surge",
            description="체결강도 급등 — 매수 우위 체결강도 하한 (완화 기본 110)",
            lanes=("tick", "min"),
            buy_fragments={"common": ("체결강도 >= {strength_min}",)},
            params=(ParamSpec("strength_min", 110.0, 100.0, 300.0),),
        ),
        PatternFamily(
            name="prevday_active",
            description="전일동시간비 고활성 — 전일 동시간 대비 거래 활성 하한",
            lanes=("tick", "min"),
            buy_fragments={"common": ("전일동시간비 >= {prev_ratio_min}",)},
            params=(ParamSpec("prev_ratio_min", 50.0, 0.0, 1000.0),),
        ),
    )
    return {f.name: f for f in families}


# ---------------------------------------------------------------------------
# 외부 패밀리 JSON 로더 (Phase 4: chart_sulsa 21개 공급 형식)
# ---------------------------------------------------------------------------
def load_pattern_families(path: Union[str, Path]) -> Dict[str, PatternFamily]:
    """JSON 파일에서 패턴 패밀리를 읽어 dict 로 돌려준다 (레지스트리 병합은 호출자 몫).

    스키마 (v1)::

        {
          "schema": "seed_lattice_pattern_families_v1",
          "families": [
            {
              "name": "...",                      # 필수
              "description": "...",               # 선택
              "lanes": ["tick", "min"],           # 필수(부분집합)
              "buy_fragments": {"common": [...], "tick": [...], "min": [...]},
              "params": [{"name": "x", "default": 1.0, "min": 0.5,
                          "max": 3.0, "integer": false}],
              "sell_overrides": {"take_profit": 3.0}   # 선택
            }, ...
          ]
        }

    params 이름은 sell 예약 키(:data:`_SELL_KEYS` — take_profit/stop_loss/
    max_hold/force_exit)와 충돌할 수 없다 (충돌 시 :func:`build_seed` 의
    오버라이드 분배가 buy 쪽으로 가로채져 sell 조정이 막히므로 로드 시점 거부).
    조각 코드의 안전성(금지 토큰·구문)은 :func:`build_seed` 가 빌드 시점에 강제하므로
    로더는 그 외 형식 검증만 한다.

    Args:
        path: JSON 파일 경로.

    Returns:
        이름 → :class:`PatternFamily` dict.

    Raises:
        ValueError: 스키마/필드 형식이 어긋날 때.
    """
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    entries = data.get("families")
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"families 리스트가 비었거나 없습니다: {p}")

    out: Dict[str, PatternFamily] = {}
    for i, e in enumerate(entries):
        name = e.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"families[{i}].name 은 비어있지 않은 문자열이어야 합니다")
        lanes = tuple(e.get("lanes", ()))
        if not lanes or any(ln not in _VALID_LANES for ln in lanes):
            raise ValueError(f"families[{i}].lanes 는 {_VALID_LANES} 의 비지 않은 부분집합: {lanes!r}")
        frags_raw = e.get("buy_fragments")
        if not isinstance(frags_raw, dict) or not frags_raw:
            raise ValueError(f"families[{i}].buy_fragments 는 비지 않은 객체여야 합니다")
        frags: Dict[str, Tuple[str, ...]] = {}
        for key, vals in frags_raw.items():
            if key not in ("common",) + _VALID_LANES:
                raise ValueError(f"families[{i}].buy_fragments 키 오류: {key!r}")
            if not isinstance(vals, list) or not all(isinstance(v, str) and v.strip() for v in vals):
                raise ValueError(f"families[{i}].buy_fragments[{key!r}] 는 문자열 리스트여야 합니다")
            frags[key] = tuple(vals)
        specs: List[ParamSpec] = []
        for j, ps in enumerate(e.get("params", [])):
            try:
                spec = ParamSpec(
                    name=str(ps["name"]),
                    default=float(ps["default"]),
                    lo=float(ps["min"]),
                    hi=float(ps["max"]),
                    integer=bool(ps.get("integer", False)),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"families[{i}].params[{j}] 형식 오류: {exc}") from exc
            if not (spec.lo <= spec.default <= spec.hi):
                raise ValueError(
                    f"families[{i}].params[{j}] default 가 범위 밖: {spec.default} not in [{spec.lo}, {spec.hi}]"
                )
            if spec.name in _SELL_KEYS:
                # buy 파라미터가 sell 키를 가로채면 sell 오버라이드가 조용히 막힌다.
                raise ValueError(
                    f"families[{i}].params[{j}] 이름 {spec.name!r} 이 sell 예약 키와 "
                    f"충돌합니다 (예약: {sorted(_SELL_KEYS)})"
                )
            specs.append(spec)
        sell_overrides = e.get("sell_overrides", {})
        if not isinstance(sell_overrides, dict):
            raise ValueError(f"families[{i}].sell_overrides 는 객체여야 합니다")
        fam = PatternFamily(
            name=name,
            description=str(e.get("description", "")),
            lanes=lanes,
            buy_fragments=frags,
            params=tuple(specs),
            sell_overrides=dict(sell_overrides),
            source=str(p),
        )
        out[fam.name] = fam
    return out


# ---------------------------------------------------------------------------
# 코드 생성 — buy(band_compiler 소비) / sell(자체 템플릿)
# ---------------------------------------------------------------------------
def _render_fragment(template: str, params: Mapping[str, Union[int, float]], family: str) -> str:
    """조각 템플릿의 ``{param}`` placeholder 를 포맷된 값으로 치환한다."""
    try:
        return template.format(**{k: _fmt_num(v) for k, v in params.items()})
    except (KeyError, IndexError) as exc:
        raise ValueError(f"패밀리 {family!r} 조각 템플릿의 미정의 placeholder: {exc}") from exc


def _cap_clause(cap: CapTier) -> Clause:
    """cap_tier 를 조건 clause 로 변환한다 (시가총액 in-code 밴드)."""
    if cap.lo is None and cap.hi is None:
        raise ValueError(f"cap_tier {cap.name!r} 는 lo/hi 중 하나는 있어야 합니다")
    if cap.hi is None:
        # BandSpec op enum 에 'ge' 단독이 없어 FixedFragment 로 표현.
        return FixedFragment(f"시가총액 >= {_fmt_num(cap.lo)}")
    if cap.lo is None:
        return BandSpec("시가총액", "lt", hi=cap.hi)
    return BandSpec("시가총액", "between_le", lo=cap.lo, hi=cap.hi)


def build_buy_code(cell: Cell, family: PatternFamily, params: Mapping[str, Union[int, float]]) -> str:
    """셀 × 패밀리 × 파라미터로 buy 코드를 결정론 생성한다 (band_compiler 소비).

    구조: ``매수 = True`` → ``if not (관심종목 == 1)`` → ``elif {band.start} <=
    시분초 < {band.end}:`` 안에 [cap 밴드, regime 밴드, 패밀리 조각들] 가드 체인 →
    ``else: 매수 = False`` → ``if 매수: self.Buy()``.

    Args:
        cell: 격자 셀.
        family: 패턴 패밀리.
        params: 완전 해석된 buy 파라미터 (이름 → 값).

    Returns:
        엔진 정규형 buy 코드 문자열.

    Raises:
        ValueError: 패밀리가 셀 lane 을 지원하지 않거나 조각 템플릿이 없을 때.
    """
    if cell.lane not in family.lanes:
        raise ValueError(f"패밀리 {family.name!r} 는 lane {cell.lane!r} 미지원 (지원: {family.lanes})")
    templates = family.buy_fragments.get(cell.lane) or family.buy_fragments.get("common")
    if not templates:
        raise ValueError(f"패밀리 {family.name!r} 에 lane {cell.lane!r} 용 buy 조각이 없습니다")

    fragments = tuple(
        FixedFragment(_render_fragment(t, params, family.name)) for t in templates
    )
    branch = TimeBranch(
        cond=f"{cell.band.start} <= 시분초 < {cell.band.end}",
        flat_clauses=(_cap_clause(cell.cap),
                      BandSpec("등락율", "between_le", lo=cell.regime.lo, hi=cell.regime.hi))
        + fragments,
        branch_kind="elif",
    )
    strat = BandStrategy(
        kind="buy",
        timeframe=cell.lane,
        preamble=(),
        state_init="매수 = True",
        preconditions=(FixedFragment("관심종목 == 1"),),
        time_branches=(branch,),
        else_false=True,
        call="if 매수:\n    self.Buy()",
    )
    return compile_to_code(strat)


# sell 청산 기본값 (lane 별). 보유시간 단위: tick=초, min=분 (tmap 템플릿 관용).
#   tick: DB 가 09:30:00 에 끝나므로 force_exit 92900 (마지막 밴드 0925 진입분은
#         체류가 짧다 — 지도 측정용 완화 규약).
#   min : 로드맵 청산 규약 force_exit 145900 (entry_end <= 144500 은 밴드 축이 보장).
SELL_DEFAULTS: Mapping[str, Mapping[str, Union[int, float]]] = {
    "tick": {"take_profit": 2.0, "stop_loss": 2.0, "max_hold": 180, "force_exit": 92900},
    "min": {"take_profit": 3.0, "stop_loss": 3.0, "max_hold": 60, "force_exit": 145900},
}
_SELL_KEYS = frozenset({"take_profit", "stop_loss", "max_hold", "force_exit"})

_SELL_TEMPLATE = (
    "매도 = False\n"
    "if 수익률 >= {take_profit}:\n"
    "    매도 = True\n"
    "elif 수익률 <= -{stop_loss}:\n"
    "    매도 = True\n"
    "elif 보유시간 >= {max_hold}:\n"
    "    매도 = True\n"
    "elif 시분초 >= {force_exit}:\n"
    "    매도 = True\n"
    "if 매도:\n"
    "    self.Sell()"
)


def _resolve_sell_params(cell: Cell, family: PatternFamily,
                         overrides: Mapping[str, Union[int, float]]) -> Dict[str, Union[int, float]]:
    """lane 기본값 ← 패밀리 오버라이드 ← 호출자 오버라이드 순으로 sell 파라미터를 겹친다."""
    merged = {**SELL_DEFAULTS[cell.lane], **dict(family.sell_overrides), **dict(overrides)}
    unknown = set(merged) - _SELL_KEYS
    if unknown:
        raise ValueError(f"알 수 없는 sell 파라미터: {sorted(unknown)} (허용: {sorted(_SELL_KEYS)})")
    if merged["take_profit"] <= 0 or merged["stop_loss"] <= 0 or merged["max_hold"] <= 0:
        raise ValueError(f"sell 파라미터는 양수여야 합니다: {merged}")
    merged["max_hold"] = int(merged["max_hold"])
    merged["force_exit"] = int(merged["force_exit"])
    return merged


def build_sell_code(cell: Cell, family: PatternFamily,
                    sell_params: Optional[Mapping[str, Union[int, float]]] = None) -> str:
    """셀 × 패밀리로 sell 코드를 결정론 생성한다 (자체 템플릿 — band_compiler 는 buy 전용).

    구조: ``매도 = False`` → 익절/손절/보유시간/강제청산 체인 → ``if 매도:
    self.Sell()``. 수익률/보유시간은 매도전략 전용 잔고 스칼라다.

    Args:
        cell: 격자 셀 (lane 이 청산 기본값을 결정).
        family: 패턴 패밀리 (``sell_overrides`` 반영).
        sell_params: 호출자 sell 오버라이드 (허용 키: take_profit/stop_loss/
            max_hold/force_exit).

    Returns:
        엔진 정규형 sell 코드 문자열.
    """
    merged = _resolve_sell_params(cell, family, sell_params or {})
    return _SELL_TEMPLATE.format(
        take_profit=_fmt_num(float(merged["take_profit"])),
        stop_loss=_fmt_num(float(merged["stop_loss"])),
        max_hold=_fmt_num(int(merged["max_hold"])),
        force_exit=_fmt_num(int(merged["force_exit"])),
    )


# ---------------------------------------------------------------------------
# 시드 빌드
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SeedRecord:
    """격자 시드 산출물 (셀 × 패밀리 × 파라미터의 결정론 스냅샷).

    Attributes:
        cell_id: 셀 식별자.
        family: 패밀리 이름.
        buy_code: 생성된 buy 코드.
        sell_code: 생성된 sell 코드.
        buy_sha256: buy 코드 sha256 hex.
        sell_sha256: sell 코드 sha256 hex.
        params: 완전 해석된 파라미터 (buy + sell 병합).
        created_reason: 생성 사유 태그.
    """

    cell_id: str
    family: str
    buy_code: str
    sell_code: str
    buy_sha256: str
    sell_sha256: str
    params: Mapping[str, Union[int, float]]
    created_reason: str


def _sha256(code: str) -> str:
    """코드 문자열의 sha256 hex 를 돌려준다 (Passport 필드 규약)."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def seed_condition_id(cell_id: str, family: str) -> str:
    """격자 시드의 정본 condition_id 를 돌려준다 (``lattice_v1:{cell_id}:{family}``).

    passport 의 condition_id 와 :func:`build_seed` 의 기본 created_reason 이 모두
    이 함수를 쓴다 (포맷 단일 출처 — 중복 하드코딩 금지). created_reason 에 custom
    태그를 넣어도 condition_id 는 셀·패밀리 기반 정본 포맷을 유지한다.

    Args:
        cell_id: 격자 셀 식별자.
        family: 패밀리 이름.

    Returns:
        정본 condition_id 문자열.
    """
    return f"lattice_v1:{cell_id}:{family}"


def _split_overrides(family: PatternFamily,
                     overrides: Mapping[str, Union[int, float]]) -> Tuple[
                         Dict[str, Union[int, float]], Dict[str, Union[int, float]]]:
    """호출자 오버라이드를 (buy 파라미터, sell 파라미터) 로 나누고 범위 검증한다.

    buy 키는 패밀리 :class:`ParamSpec` 범위 [lo, hi] 안이어야 하고, integer 스펙은
    정수값만 허용한다. sell 키는 :data:`_SELL_KEYS` 만 허용한다.
    """
    specs = {s.name: s for s in family.params}
    buy: Dict[str, Union[int, float]] = {s.name: (int(s.default) if s.integer else s.default)
                                         for s in family.params}
    sell: Dict[str, Union[int, float]] = {}
    for key, value in overrides.items():
        if key in specs:
            spec = specs[key]
            v = float(value)
            if not (spec.lo <= v <= spec.hi):
                raise ValueError(
                    f"패밀리 {family.name!r} 파라미터 {key}={value} 가 범위 밖 [{spec.lo}, {spec.hi}]"
                )
            if spec.integer:
                if not v.is_integer():
                    raise ValueError(f"패밀리 {family.name!r} 파라미터 {key} 는 정수여야 합니다: {value}")
                buy[key] = int(v)
            else:
                buy[key] = v
        elif key in _SELL_KEYS:
            sell[key] = value
        else:
            raise ValueError(
                f"패밀리 {family.name!r} 에 없는 파라미터: {key!r} "
                f"(buy: {sorted(specs)}, sell: {sorted(_SELL_KEYS)})"
            )
    return buy, sell


def build_seed(cell: Cell,
               family: Union[str, PatternFamily],
               params: Optional[Mapping[str, Union[int, float]]] = None,
               families: Optional[Mapping[str, PatternFamily]] = None,
               created_reason: Optional[str] = None) -> SeedRecord:
    """셀 × 패밀리로 :class:`SeedRecord` 를 빌드한다 (구문+금지토큰 가드 통과 필수).

    같은 입력은 항상 같은 코드/sha 를 낸다 (band_compiler 결정론 + 고정 템플릿).
    생성 코드가 ``compile(code, '<seed>', 'exec')`` 또는
    :func:`~ai_strategy_loop.brain.token_check.check_tokens` 를 통과하지 못하면
    시드를 내지 않고 raise 한다.

    Args:
        cell: 격자 셀.
        family: 패밀리 이름(레지스트리 조회) 또는 :class:`PatternFamily` 인스턴스.
        params: buy/sell 파라미터 오버라이드 (미지정 키는 기본값).
        families: 이름 조회용 레지스트리 (None 이면 :func:`default_pattern_families`).
        created_reason: 생성 사유 태그 (None 이면 :func:`seed_condition_id` 값
            ``lattice_v1:{cell_id}:{family}``).

    Returns:
        :class:`SeedRecord`.

    Raises:
        ValueError: 미등록 패밀리 / lane 미지원 / 파라미터 범위 밖 / 가드 실패.
    """
    if isinstance(family, str):
        registry = families if families is not None else default_pattern_families()
        if family not in registry:
            raise ValueError(f"미등록 패밀리: {family!r} (등록: {sorted(registry)})")
        fam = registry[family]
    else:
        fam = family

    buy_params, sell_overrides = _split_overrides(fam, params or {})
    buy_code = build_buy_code(cell, fam, buy_params)
    sell_code = build_sell_code(cell, fam, sell_overrides)

    # 가드: 구문 검증 + 금지 토큰 검사 (둘 다 필수 — 실패 시 시드 미발행).
    for label, code in (("buy", buy_code), ("sell", sell_code)):
        try:
            compile(code, "<seed>", "exec")
        except SyntaxError as exc:
            raise ValueError(f"{cell.cell_id}/{fam.name} {label} 코드 구문 오류: {exc}") from exc
        ok, reason = check_tokens(code)
        if not ok:
            raise ValueError(f"{cell.cell_id}/{fam.name} {label} 코드 금지 토큰: {reason}")

    merged_params = {**buy_params, **_resolve_sell_params(cell, fam, sell_overrides)}
    return SeedRecord(
        cell_id=cell.cell_id,
        family=fam.name,
        buy_code=buy_code,
        sell_code=sell_code,
        buy_sha256=_sha256(buy_code),
        sell_sha256=_sha256(sell_code),
        params=merged_params,
        created_reason=created_reason or seed_condition_id(cell.cell_id, fam.name),
    )
