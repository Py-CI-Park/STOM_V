"""타임프레임 인지 변수 스코프 가드 (US-003 E2E 강건성 핵심 픽스).

배경 (데드락 근본원인 #2):
  MIN 엔진에서 백테스트하는데 TICK 전용 변수(예: `초당거래대금`)를 쓴 전략은
  엔진 내부 `exec(self.buystg)`에서 `NameError: name '초당거래대금' is not defined`로
  죽는다. 엔진이 '백테완료'를 못 보내 BackTest child가 데드락(타임아웃)한다.
  → 백테스트 **이전**에 결정론적으로 차단해야 한다.

설계 (단순함 우선):
  전략 코드는 한글/영문 NAME 식별자만 참조한다. 어떤 NAME이 주어진 타임프레임에서
  유효한지는 다음 합집합으로 정의한다:

    allowed = 타임프레임 스칼라 변수
            ∪ 타임프레임에서 허용되는 SetGlobalsFunc 함수형 이름
            ∪ 코드가 스스로 대입한 로컬 이름 (매수/매도 포함)
            ∪ python builtins/keywords (True/False/None/and/or/not/min/max 등)

  타임프레임 게이팅의 핵심:
    - tick: 초당매수수량/초당매도수량/초당거래대금/초당매수금액/초당매도금액 (+ N 함수형)
    - min : 분당매수수량/분당매도수량/분당거래대금/분당매수금액/분당매도금액
            + 분봉시가/분봉고가/분봉저가 (+ N 함수형), 보조지표(RSI/MACD 등)
    - 공통: 현재가/등락율/체결강도/시가총액/관심종목/시분초 + 이동평균()/호가상승압력()/
            거래대금급증및연속상승() 같은 합성 함수.

  SetGlobalsFunc 181개 이름은 trade/base_strategy.py의 dict_add_func 리터럴 키에서
  AST로 추출한다 (test_ai_dictionary.py와 동일한 단일 진실 공급원). 그 중 초당*/분당*/
  분봉* 접두 이름만 타임프레임으로 나누고, 나머지는 양쪽 공통으로 둔다.
"""

from __future__ import annotations

import ast
import builtins
import keyword
from pathlib import Path
from typing import FrozenSet, List, Set, Tuple

# trade/base_strategy.py 위치 (저장소 고정).
_REPO_ROOT = Path(__file__).resolve().parents[2]
_BASE_STRATEGY = _REPO_ROOT / "trade" / "base_strategy.py"

_VALID_TIMEFRAMES = ("min", "tick")

# --- 타임프레임 전용 스칼라 변수 (strategy.txt의 두 섹션 차이) ---
# tick: 초당* 계열. min: 분당* + 분봉* 계열.
_TICK_ONLY_SCALARS = frozenset({
    "초당매수수량", "초당매도수량", "초당거래대금", "초당매수금액", "초당매도금액",
})
_MIN_ONLY_SCALARS = frozenset({
    "분당매수수량", "분당매도수량", "분당거래대금", "분당매수금액", "분당매도금액",
    "분봉시가", "분봉고가", "분봉저가",
})

# 1분봉 전용 보조지표 (strategy.txt 1분봉 섹션). tick에는 없다.
_MIN_ONLY_INDICATORS = frozenset({
    "AD", "ADOSC", "ADXR", "APO", "AROOND", "AROONU", "ATR",
    "BBU", "BBM", "BBL", "CCI", "DIM", "DIP",
    "MACD", "MACDS", "MACDH", "MFI", "MOM", "OBV", "PPO",
    "ROC", "RSI", "SAR", "STOCHSK", "STOCHSD", "STOCHFK", "STOCHFD", "WILLR",
})

# --- 양쪽 공통 스칼라 변수 (strategy.txt 양 섹션에 동일하게 등장) ---
_COMMON_SCALARS = frozenset({
    # 가격
    "현재가", "시가", "고가", "저가", "등락율",
    "고저평균대비등락율", "저가대비고가등락율",
    # 거래량/거래대금/체결
    "당일거래대금", "체결강도",
    "당일매수금액", "당일매도금액",
    "최고매수금액", "최고매도금액", "최고매수가격", "최고매도가격",
    # 호가
    "매도호가1", "매도호가2", "매도호가3", "매도호가4", "매도호가5",
    "매도잔량1", "매도잔량2", "매도잔량3", "매도잔량4", "매도잔량5",
    "매수호가1", "매수호가2", "매수호가3", "매수호가4", "매수호가5",
    "매수잔량1", "매수잔량2", "매수잔량3", "매수잔량4", "매수잔량5",
    "매도총잔량", "매수총잔량", "매도수5호가잔량합",
    # 그외
    "호가단위", "데이터길이", "시분초", "종목명", "종목코드", "관심종목",
    # 국내주식 전용 스칼라
    "거래대금증감", "전일비", "회전율", "전일동시간비", "시가총액",
    "라운드피겨위5호가이내", "VI해제시간", "VI가격", "VI호가단위",
})

# --- 매도전략 전용 잔고종목 스칼라 (forbidden.md (a): 매수에서는 금지) ---
#   G2(2026-07-12) 진실 공급원 확정: 이 가드의 계약은 **백테 엔진 exec env**
#   (backengine_* Strategy 스코프)다 — 저장 시점 검증기(back_code_test.py)는
#   GUI 라이브 이름까지 포함한 superset env라 진실 공급원이 아니다(아키텍트
#   리뷰 5-G2ArchitectReview 판정). '매도수량'/'강제청산'/'매수수량'은 GUI
#   라이브 전용 이름으로 어떤 backengine sell exec env에도 없어 **미추가**
#   (추가하면 NameError→BackStop 무신호→타임아웃 홀 재개방). 인간 운영
#   전략의 self.Sell(종목코드, 종목명, 매도수량, 강제청산) 시그니처는 루프
#   정규형(bare self.Sell())과 호스트 환경이 다른 것이지 가드 오탐이 아니다.
#   근거: docs/update_log/2026-07-12_g2_gate_false_reject_audit_report.md.
_SELL_ONLY_SCALARS = frozenset({
    "수익금", "수익률", "매수가", "보유수량", "보유시간",
    "분할매수횟수", "분할매도횟수", "최고수익률", "최저수익률",
})

# --- 정규 상태/실행 이름 (항상 허용) ---
_STATE_NAMES = frozenset({"매수", "매도", "self"})

# 위험한 builtins — 변수 스코프 가드가 "유효 이름"으로 인정하면 안 된다
#   (token_check와 동일 위협모델: 샌드박스 우회 경로). dir(builtins)에서 제거한다.
_DANGEROUS_BUILTINS = frozenset({
    "getattr", "setattr", "delattr",
    "globals", "locals", "vars",
    "breakpoint", "memoryview",
    "eval", "exec", "open", "compile", "__import__",
})

# python builtins + keywords (True/False/None/and/or/not/min/max/abs/len 등).
#   위험 builtins는 빼서 전략이 참조하면 offending으로 잡히게 한다.
_PY_NAMES = (
    (frozenset(dir(builtins)) - _DANGEROUS_BUILTINS)
    | frozenset(keyword.kwlist)
    | frozenset(keyword.softkwlist)
)


def _derive_setglobals_names() -> Set[str]:
    """trade/base_strategy.py의 SetGlobalsFunc.dict_add_func 리터럴 키를 AST로 추출한다.

    test_ai_dictionary.py와 동일한 단일 진실 공급원. 181개 함수형 이름을 돌려준다.
    """
    tree = ast.parse(_BASE_STRATEGY.read_text(encoding="utf-8"))
    func = next(
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "SetGlobalsFunc"
    )
    names: Set[str] = set()
    for node in ast.walk(func):
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(t, ast.Name) and t.id == "dict_add_func" for t in node.targets
        ):
            continue
        if isinstance(node.value, ast.Dict):
            for key in node.value.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    names.add(key.value)
    return names


def _is_tick_specific(name: str) -> bool:
    """SetGlobalsFunc 이름이 TICK 전용인지 (초당* 접두, 또는 누적/최고 등 접두 뒤의 '초당').

    '누적초당매수수량', '최고초당매도수량'처럼 파생 접두(누적/최고)가 '초당' 앞에
    붙는 이름도 tick 파생이므로 부분일치로 판정한다 (base_strategy.py dict_add_func
    실측: '초당'을 포함하는 리터럴 키는 전부 tick 전용).
    """
    return "초당" in name


def _is_min_specific(name: str) -> bool:
    """SetGlobalsFunc 이름이 MIN 전용인지 (분당*/분봉* 접두, 또는 보조지표 _N).

    보조지표 함수형 이름은 'RSI_N', 'MACD_N' 처럼 끝나며 _MIN_ONLY_INDICATORS의
    '_N' 변형이다. 단순화를 위해 베이스 이름이 보조지표면 MIN 전용으로 본다.
    '누적분당매수수량', '최고분당매도수량'처럼 파생 접두(누적/최고)가 '분당'/'분봉'
    앞에 붙는 이름도 min 파생이므로 부분일치로 판정한다 (base_strategy.py
    dict_add_func 실측: '분당'/'분봉'을 포함하는 리터럴 키는 전부 min 전용).
    """
    if "분당" in name or "분봉" in name:
        return True
    # 'RSI_N' → base 'RSI'
    base = name[:-2] if name.endswith("_N") else name
    return base in _MIN_ONLY_INDICATORS


# SetGlobalsFunc 이름을 모듈 import 시 한 번만 추출 (181개).
_SETGLOBALS_NAMES: FrozenSet[str] = frozenset(_derive_setglobals_names())


def _allowed_names(timeframe: str, kind: str) -> FrozenSet[str]:
    """주어진 타임프레임/kind에서 허용되는 전역 이름 집합을 만든다.

    Args:
        timeframe: 'min' | 'tick'.
        kind: 'buy' | 'sell'. sell이면 잔고종목 스칼라를 추가 허용.
    """
    is_min = timeframe == "min"

    # SetGlobalsFunc: 타임프레임 전용 접두만 게이팅, 나머지는 공통.
    setglobals = {
        n for n in _SETGLOBALS_NAMES
        if not (
            (is_min and _is_tick_specific(n))
            or (not is_min and _is_min_specific(n))
        )
    }

    scalars = set(_COMMON_SCALARS)
    if is_min:
        scalars |= _MIN_ONLY_SCALARS | _MIN_ONLY_INDICATORS
    else:
        scalars |= _TICK_ONLY_SCALARS

    allowed = scalars | setglobals | set(_STATE_NAMES) | set(_PY_NAMES)
    if kind == "sell":
        allowed |= _SELL_ONLY_SCALARS
    return frozenset(allowed)


def _collect_assigned_locals(tree: ast.AST) -> Set[str]:
    """코드가 스스로 대입하는 로컬 이름을 수집한다 (좌변 Name 타깃)."""
    locals_: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                for sub in ast.walk(tgt):
                    if isinstance(sub, ast.Name):
                        locals_.add(sub.id)
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            tgt = node.target
            if isinstance(tgt, ast.Name):
                locals_.add(tgt.id)
        elif isinstance(node, (ast.For, ast.comprehension)):
            tgt = node.target
            for sub in ast.walk(tgt):
                if isinstance(sub, ast.Name):
                    locals_.add(sub.id)
        elif isinstance(node, ast.FunctionDef):
            locals_.add(node.name)
            for arg in node.args.args:
                locals_.add(arg.arg)
    return locals_


def check_variable_scope(code: str, timeframe: str, kind: str = "buy") -> Tuple[bool, List[str]]:
    """전략 코드가 참조하는 NAME이 타임프레임 스코프에 모두 들어오는지 검사한다.

    AST로 모든 참조 NAME(ast.Name with Load ctx)을 모으고, 허용 집합
    (타임프레임 변수 ∪ SetGlobalsFunc ∪ 대입 로컬 ∪ python builtins/keywords)에
    없는 이름이 하나라도 있으면 거부한다. 위반 이름을 정렬해 반환한다.

    이것이 NameError-데드락을 백테스트 이전에 결정론적으로 차단하는 핵심 가드다.

    Args:
        code: 전략 코드 문자열.
        timeframe: 'min' | 'tick'.
        kind: 'buy' | 'sell' (sell이면 잔고종목 스칼라 허용).

    Returns:
        (ok, offending_names). ok=True면 통과(offending_names=[]),
        ok=False면 허용 집합에 없는 이름들(정렬·중복제거).

    Raises:
        ValueError: timeframe이 'min'/'tick'가 아닐 때.
    """
    if timeframe not in _VALID_TIMEFRAMES:
        raise ValueError(f"timeframe은 {_VALID_TIMEFRAMES} 중 하나여야 합니다: {timeframe!r}")

    if not code or not code.strip():
        return False, ["<빈 코드>"]

    try:
        tree = ast.parse(code)
    except SyntaxError:
        # 구문 오류는 상위 compile 게이트가 먼저 거른다. 여기선 스코프 판정 불가.
        return False, ["<구문 오류>"]

    allowed = _allowed_names(timeframe, kind) | _collect_assigned_locals(tree)

    offending: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id not in allowed:
                offending.add(node.id)

    if offending:
        return False, sorted(offending)
    return True, []
