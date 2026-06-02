"""밴드 패러다임 P0 — 결정론 밴드→코드 컴파일러 (순수, 엔진 0수정).

P0 of the band-generator paradigm. A deterministic band->code compiler.
The band representation captures *box conditions* (single-variable range gates,
e.g. ``1000 < 현재가 <= 50000``) as tunable :class:`BandSpec` vectors, and *non-box*
conditions (variable ratios, function-form args, derived position, 누적 etc.) as
verbatim :class:`FixedFragment` strings. Emission is byte-deterministic so the same
:class:`BandStrategy` always compiles to identical code (dedup·baseline 정합).

설계 근거 (design `docs/update_log/2026-06-02_band_generator_design.md` §1·§2·§8 P0):
  - 전략 = 고정 조건집합 위 밴드 벡터. 각 box 조건 = (변수, op, [lo,hi], active).
  - op enum 은 유한집합(결정론 핵심). off 조건(active=False 또는 자연도메인 전범위)은
    미emit. P0 시드는 전부 active·narrow 라 미omit 되지 않지만 ``is_off`` 는 구현한다.
  - 컴파일러는 엔진 기대 정규형(``매수=True`` → ``if not(밴드): 매수=False`` 체인 →
    ``if 매수: self.Buy()``)으로 변환한다. 엔진/스코어/게이트/생성 어디도 건드리지 않는
    순수 추가 모듈이다 (P0 에서는 아무도 이 모듈을 읽지 않는다).

This is purely additive: it imports nothing from the engine and changes no
existing behavior. Determinism is guaranteed by (1) a fixed op enum, (2) a fixed
number format (``f"{x:g}"`` with int-preservation), and (3) emission order = the
declared order of branches/clauses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

# ---------------------------------------------------------------------------
# op enum — 유한집합 (결정론 핵심). 각 op 은 (lo, hi) 로 하나의 부등식을 만든다.
# ---------------------------------------------------------------------------
#   lt_le      : lo <  var <= hi      (예: 1000 < 현재가 <= 50000)
#   ge_le      : var >= lo and var <= hi  (예: 체결강도 >= 50 and 체결강도 <= 300)
#   gt         : var >  lo            (예: 회전율 > 1.5)
#   lt         : var <  hi            (예: 시가총액 < 3000)
#   gt_lt      : lo <  var <  hi      (예: 1 < 초당순매수금액 < 1000)
#   between_le : lo <= var <  hi      (예: 2.0 <= 시가등락율 < 4.0)
_OP_ENUM = frozenset({"lt_le", "ge_le", "gt", "lt", "gt_lt", "between_le"})


def _fmt(x: Union[int, float]) -> str:
    """숫자를 시드 리터럴 스타일로 포맷한다 (정수는 정수, 실수는 ``:g``).

    시드는 ``1000`` (정수)·``1.0`` (실수)·``8.0`` (실수) 를 섞어 쓴다. ``f"{x:g}"`` 는
    ``1000.0`` 를 ``1000`` 으로, ``1.0`` 을 ``1`` 로 줄여버려 시드 스타일과 어긋난다.
    그래서 int 는 ``str(int)``, float 는 명시적으로 소수점을 보존한다.

    Args:
        x: 포맷할 정수 또는 실수.

    Returns:
        시드 리터럴과 동일한 표기의 문자열.
    """
    if isinstance(x, bool):  # bool 은 int 의 서브클래스 — 방어
        raise TypeError("밴드 경계는 bool 일 수 없습니다")
    if isinstance(x, int):
        return str(x)
    # float: 정수값(8.0)도 소수점 유지(시드 스타일 1.0/8.0), 그 외는 일반 표기.
    if x == int(x):
        return f"{int(x)}.0"
    return f"{x:g}"


# ---------------------------------------------------------------------------
# 밴드 표현 dataclass
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class BandSpec:
    """단일 변수 box 조건 (튜닝 가능한 밴드).

    Attributes:
        var: 변수 이름 (예: ``현재가``).
        op: op enum 중 하나 (``lt_le``/``ge_le``/``gt``/``lt``/``gt_lt``/``between_le``).
        lo: 하한 (op 에 따라 사용; ``lt`` 는 None 가능).
        hi: 상한 (op 에 따라 사용; ``gt`` 는 None 가능).
        active: False 이면 미게이트(미emit).
        window: 함수형 윈도우 인자 (box 조건에서는 보통 None).
    """

    var: str
    op: str
    lo: Optional[float] = None
    hi: Optional[float] = None
    active: bool = True
    window: Optional[int] = None

    def __post_init__(self) -> None:
        if self.op not in _OP_ENUM:
            raise ValueError(f"알 수 없는 op: {self.op!r} (허용: {sorted(_OP_ENUM)})")


@dataclass(frozen=True)
class FixedFragment:
    """box 로 표현 불가한 NON-box 조건의 verbatim 표현식.

    비율(``초당매수수량 > 매도총잔량 * 0.20``)·함수형 인자(``당일거래대금각도(30) > 5``)·
    파생 위치(``현재가 > (고가 - (고가 - 저가) * 0.20)``)·누적 조건 등 밴드 [lo,hi] 로
    담을 수 없는 조건은 코드 조각 그대로 보존한다.

    ``reject_if`` 가 가드 극성을 결정한다 (시드의 두 관용구를 모두 정확히 재현):
      - ``"not_satisfied"`` (기본): ``elif not (<code>): 매수 = False`` —
        조건이 *충족 안 되면* 거부 (시드의 대다수 필터 관용구).
      - ``"satisfied"``: ``elif <code>: 매수 = False`` — 조건이 *충족되면* 거부
        (시드의 ``elif 라운드피겨위5호가이내: 매수=False`` 처럼 양성 거부 게이트).

    Attributes:
        code: 조건 표현식 (예: ``"당일거래대금각도(30) > 5 and 당일거래대금각도(30) < 30"``).
        reject_if: ``"not_satisfied"`` (not 래핑) 또는 ``"satisfied"`` (그대로).
    """

    code: str
    reject_if: str = "not_satisfied"

    def __post_init__(self) -> None:
        if self.reject_if not in ("not_satisfied", "satisfied"):
            raise ValueError(
                f"reject_if 은 'not_satisfied'|'satisfied': {self.reject_if!r}"
            )


# 조건 한 줄 = box 밴드이거나 고정 조각.
Clause = Union[BandSpec, FixedFragment]


@dataclass(frozen=True)
class McapBlock:
    """``if 시가총액 < cap_lt:`` 중첩 블록.

    컴파일러는 ``if 시가총액 < {cap_lt}:`` 헤더 → 내부 clause if/elif 체인 →
    ``else: 매수 = False`` 를 emit 한다.

    Attributes:
        cap_lt: 시가총액 상한 (예: 3000).
        clauses: 블록 내부 조건들 (순서 보존).
    """

    cap_lt: float
    clauses: Tuple[Clause, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class TimeBranch:
    """시간창 분기 (예: 902 / 905).

    Attributes:
        cond: 분기 조건 (예: ``"시분초 < 90200"`` 또는 ``"90200 <= 시분초 < 90500"``).
        flat_clauses: 중첩 mcap 블록 이전의 평면 조건들 (순서 보존).
        mcap_block: 중첩 ``if 시가총액 < X`` 블록 (없으면 None).
        branch_kind: ``"if"`` 또는 ``"elif"`` (시드는 모든 분기가 ``elif``).
        inner_time_guard: 902 분기처럼 mcap 앞에 한 번 더 ``elif 시분초 < X:`` 가
            감싸는 경우 그 조건 (없으면 None). 905 분기는 평면 조건 뒤 바로 ``else:``
            안에서 mcap 을 여므로 None + ``mcap_in_else=True``.
        mcap_in_else: True 면 mcap 블록을 평면 조건 체인의 ``else:`` 안에 emit (905 형).
            False 면 ``inner_time_guard`` 의 ``elif`` 안에 emit (902 형).
    """

    cond: str
    flat_clauses: Tuple[Clause, ...] = field(default_factory=tuple)
    mcap_block: Optional[McapBlock] = None
    branch_kind: str = "elif"
    inner_time_guard: Optional[str] = None
    mcap_in_else: bool = False

    def __post_init__(self) -> None:
        if self.branch_kind not in ("if", "elif"):
            raise ValueError(f"branch_kind 은 'if'|'elif': {self.branch_kind!r}")


@dataclass(frozen=True)
class BandStrategy:
    """밴드 전략 표현 (한 전략 = 고정 조건집합 위 밴드 벡터).

    Attributes:
        kind: ``"buy"`` 또는 ``"sell"``.
        timeframe: ``"tick"`` 또는 ``"min"``.
        preamble: 공통 계산 지표 + VI아래5호가 등 verbatim 파생지표 라인들.
        state_init: 상태 초기화 (매수면 ``"매수 = True"``).
        preconditions: 분기 이전 공통 필터들 (첫 ``if not(...): 매수=False``).
        time_branches: 시간창 분기들 (902/905 등).
        else_false: True 면 마지막에 ``else: 매수 = False`` emit.
        call: 호출 (매수면 ``"if 매수:\\n    self.Buy()"``).
    """

    kind: str
    timeframe: str
    preamble: Tuple[str, ...] = field(default_factory=tuple)
    state_init: str = "매수 = True"
    preconditions: Tuple[Clause, ...] = field(default_factory=tuple)
    time_branches: Tuple[TimeBranch, ...] = field(default_factory=tuple)
    else_false: bool = True
    call: str = "if 매수:\n    self.Buy()"


# ---------------------------------------------------------------------------
# is_off — 미게이트(미emit) 판정
# ---------------------------------------------------------------------------
# 시드 box 변수들의 자연 도메인(전범위). [lo,hi] 가 이 전범위면 그 줄은 미게이트로 본다.
#   (P0 시드 밴드는 전부 narrow active 라 실제로는 미omit 되지 않지만, 테스트가 검증한다.)
DOMAIN: Dict[str, Tuple[float, float]] = {
    "현재가": (0.0, 1_000_000.0),
    "등락율": (-30.0, 30.0),
    "시가등락율": (-30.0, 30.0),
    "시가대비등락율": (-30.0, 30.0),
    "회전율": (0.0, 1_000.0),
    "당일거래대금": (0.0, 1e15),
    "시가총액": (0.0, 1e9),
    "체결강도": (0.0, 1_000.0),
    "초당순매수금액": (-1e9, 1e9),
}


def is_off(spec: BandSpec, domain: Optional[Dict[str, Tuple[float, float]]] = None) -> bool:
    """밴드가 미게이트(미emit) 인지 판정한다.

    off 조건: active=False, 또는 그 [lo,hi] 가 변수의 자연 도메인 전범위와 같음
    (즉 아무 것도 걸러내지 않음).

    Args:
        spec: 판정할 밴드.
        domain: 변수→(전범위 lo, 전범위 hi). None 이면 모듈의 :data:`DOMAIN` 사용.

    Returns:
        미게이트면 True (컴파일러가 그 줄을 emit 하지 않음).
    """
    if not spec.active:
        return True
    dom = DOMAIN if domain is None else domain
    bounds = dom.get(spec.var)
    if bounds is None:
        return False
    dlo, dhi = bounds
    # op 별로 "전범위 = 아무 것도 안 거름" 판정.
    if spec.op == "gt":
        return spec.lo is not None and spec.lo <= dlo
    if spec.op == "lt":
        return spec.hi is not None and spec.hi >= dhi
    if spec.op in ("lt_le", "ge_le", "gt_lt", "between_le"):
        lo_full = spec.lo is None or spec.lo <= dlo
        hi_full = spec.hi is None or spec.hi >= dhi
        return lo_full and hi_full
    return False


# ---------------------------------------------------------------------------
# clause → 조건 표현식
# ---------------------------------------------------------------------------
def emit_clause(spec: Clause) -> str:
    """clause 를 조건 표현식 문자열로 변환한다 (``not(...)`` 래핑 없음).

    BandSpec → op enum 에 따른 부등식. FixedFragment → 그 ``.code`` verbatim.

    Args:
        spec: BandSpec 또는 FixedFragment.

    Returns:
        조건 표현식 (예: ``"1000 < 현재가 <= 50000"`` 또는 verbatim 조각).
    """
    if isinstance(spec, FixedFragment):
        return spec.code
    if not isinstance(spec, BandSpec):  # 방어
        raise TypeError(f"Clause 는 BandSpec|FixedFragment: {type(spec)!r}")

    var = spec.var
    lo = _fmt(spec.lo) if spec.lo is not None else None
    hi = _fmt(spec.hi) if spec.hi is not None else None
    op = spec.op
    if op == "lt_le":
        return f"{lo} < {var} <= {hi}"
    if op == "ge_le":
        return f"{var} >= {lo} and {var} <= {hi}"
    if op == "gt":
        return f"{var} > {lo}"
    if op == "lt":
        return f"{var} < {hi}"
    if op == "gt_lt":
        return f"{lo} < {var} < {hi}"
    if op == "between_le":
        return f"{lo} <= {var} < {hi}"
    raise ValueError(f"알 수 없는 op: {op!r}")  # pragma: no cover (BandSpec 가 먼저 막음)


# ---------------------------------------------------------------------------
# 컴파일러
# ---------------------------------------------------------------------------
_IND = "    "  # 4-space 들여쓰기 (고정).


def _emit_guard_chain(
    clauses: Tuple[Clause, ...],
    indent: int,
    lead_kind: str,
    domain: Optional[Dict[str, Tuple[float, float]]],
) -> List[str]:
    """조건 clause 들을 ``if/elif not(...): 매수 = False`` 체인으로 emit 한다.

    첫 줄은 ``lead_kind`` (``"if"`` 또는 ``"elif"``), 이후는 ``elif``. 미게이트
    (is_off) clause 는 건너뛴다. 빈 결과면 빈 리스트.

    Args:
        clauses: 조건들 (순서 보존).
        indent: 들여쓰기 단계 수.
        lead_kind: 첫 조건의 키워드 (``"if"``/``"elif"``).
        domain: is_off 판정용 도메인.

    Returns:
        코드 라인들의 리스트.
    """
    lines: List[str] = []
    pad = _IND * indent
    first = True
    for cl in clauses:
        if isinstance(cl, BandSpec) and is_off(cl, domain):
            continue
        kw = lead_kind if first else "elif"
        expr = emit_clause(cl)
        # 가드 극성: satisfied FixedFragment 는 'elif <expr>:' (양성 거부),
        #   그 외(BandSpec·not_satisfied)는 'elif not (<expr>):'.
        if isinstance(cl, FixedFragment) and cl.reject_if == "satisfied":
            lines.append(f"{pad}{kw} {expr}:")
        else:
            lines.append(f"{pad}{kw} not ({expr}):")
        lines.append(f"{pad}{_IND}매수 = False")
        first = False
    return lines


def _emit_mcap_block(block: McapBlock, indent: int,
                     domain: Optional[Dict[str, Tuple[float, float]]]) -> List[str]:
    """``if 시가총액 < cap_lt:`` 중첩 블록을 emit 한다 (내부 체인 + ``else: 매수=False``).

    Args:
        block: McapBlock.
        indent: ``if 시가총액`` 헤더의 들여쓰기 단계.
        domain: is_off 판정용 도메인.

    Returns:
        코드 라인들.
    """
    pad = _IND * indent
    lines: List[str] = [f"{pad}if 시가총액 < {_fmt(block.cap_lt)}:"]
    lines.extend(_emit_guard_chain(block.clauses, indent + 1, "if", domain))
    lines.append(f"{pad}else:")
    lines.append(f"{pad}{_IND}매수 = False")
    return lines


def _emit_time_branch(branch: TimeBranch, indent: int,
                      domain: Optional[Dict[str, Tuple[float, float]]]) -> List[str]:
    """시간창 분기를 emit 한다 (902/905 두 구조 모두 지원).

    902 형(``inner_time_guard`` 사용): 평면 조건 체인 → ``elif <inner_time_guard>:`` →
      그 안에 mcap 블록 → 분기 ``else: 매수=False``.
    905 형(``mcap_in_else=True``): 평면 조건 체인 → ``else:`` → 그 안에 mcap 블록.

    Args:
        branch: TimeBranch.
        indent: 분기 헤더(``elif <cond>:``)의 들여쓰기 단계.
        domain: is_off 판정용 도메인.

    Returns:
        코드 라인들.
    """
    pad = _IND * indent
    lines: List[str] = [f"{pad}{branch.branch_kind} {branch.cond}:"]
    body = indent + 1

    # 평면 조건 체인 (mcap 블록 이전).
    lines.extend(_emit_guard_chain(branch.flat_clauses, body, "if", domain))

    if branch.mcap_block is None:
        return lines

    if branch.mcap_in_else:
        # 905 형: 평면 체인의 else 안에 mcap.
        bpad = _IND * body
        lines.append(f"{bpad}else:")
        lines.extend(_emit_mcap_block(branch.mcap_block, body + 1, domain))
    else:
        # 902 형: elif <inner_time_guard>: 안에 mcap, 그 뒤 분기 else.
        bpad = _IND * body
        guard = branch.inner_time_guard if branch.inner_time_guard else branch.cond
        lines.append(f"{bpad}elif {guard}:")
        lines.extend(_emit_mcap_block(branch.mcap_block, body + 1, domain))
        lines.append(f"{bpad}else:")
        lines.append(f"{bpad}{_IND}매수 = False")
    return lines


def compile_to_code(strat: BandStrategy,
                    domain: Optional[Dict[str, Tuple[float, float]]] = None) -> str:
    """밴드 전략을 엔진 정규형 코드로 결정론 컴파일한다.

    emit 순서: preamble → state_init → 첫 precondition(``if not(...): 매수=False``) →
    각 time_branch(``elif``) → ``else: 매수=False`` → call. 동일 :class:`BandStrategy`
    는 항상 byte-identical 코드를 낸다 (dedup·baseline 정합).

    Args:
        strat: 컴파일할 밴드 전략.
        domain: is_off 판정용 도메인 (None 이면 :data:`DOMAIN`).

    Returns:
        엔진 정규형 전략 코드 문자열 (끝에 개행 없음).
    """
    lines: List[str] = []

    # 1) preamble (공통 계산 지표 + VI아래5호가).
    for p in strat.preamble:
        lines.append(p)

    # 2) state_init.
    lines.append(strat.state_init)
    lines.append("")

    # 3) preconditions: 첫 조건은 'if not(...)', 이후 'elif not(...)'.
    #    (시드는 precondition 1개 = 관심종목. time_branch 들이 그 뒤 elif 로 이어진다.)
    pre_lines = _emit_guard_chain(strat.preconditions, 0, "if", domain)
    lines.extend(pre_lines)

    # 4) time_branches: precondition 이 있으면 elif 로 이어지는 게 자연스럽다.
    #    각 branch 는 자체 branch_kind 를 갖는다(시드는 전부 'elif').
    for branch in strat.time_branches:
        lines.extend(_emit_time_branch(branch, 0, domain))

    # 5) else: 매수 = False.
    if strat.else_false:
        lines.append("else:")
        lines.append(f"{_IND}매수 = False")

    # 6) call.
    lines.append("")
    lines.append(strat.call)

    return "\n".join(lines)
