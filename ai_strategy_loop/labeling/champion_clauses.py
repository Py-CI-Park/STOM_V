"""챔피언 진입 조건의 **절 단위 분해** — 빈도를 올릴 곳을 찾기 위한 해부도.

## 왜 필요한가

챔피언은 하루 **0.433건**만 산다(361건 / DB 833거래일). 열흘 중 엿새는 아예
거래가 없다. 표본이 늘 모자란 근본 원인이 여기 있다 — 절 34개를 전부 통과해야
하기 때문이다.

그런데 어느 절이 수익을 만들고 어느 절이 거래만 막는지는 아무도 모른다.
`verify_human_strategy._mask_902/_mask_905` 는 조건을 하나의 긴 `&` 사슬로
붙여 놓아서 절을 하나씩 뺄 수가 없다. 이 모듈이 그 사슬을 **이름 붙은 절**로
푼다.

## 계약 — 등가성

절을 전부 AND 한 결과는 원본 마스크와 **완전히 같아야** 한다. 다르면 해부도가
다른 전략을 재고 있는 것이므로, 그 사실을 테스트가 먼저 잡는다
(`test_w7_champion_clauses.py::test_clause_decomposition_equals_the_original_mask`).

## 구조 절은 뺄 수 없다

시간 창(`창_902`, `창_905`)은 두 분기를 가르는 뼈대다. 이것을 빼면 분기가 서로
겹쳐 "챔피언이 아닌 무언가"를 재게 된다. `droppable=False` 로 잠근다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Final, Sequence

import pandas as pd


@dataclass(frozen=True)
class Clause:
    """이름 붙은 진입 절 하나."""

    key: str
    label: str
    predicate: Callable[[pd.DataFrame], pd.Series]
    #: 구조 절(시간 창)은 빼면 분기가 겹친다 — 제거 실험 대상이 아니다.
    droppable: bool = True


def _c(key: str, label: str, predicate, droppable: bool = True) -> Clause:
    return Clause(key=key, label=label, predicate=predicate, droppable=droppable)


# --- 09:00:00 ~ 09:02:00 분기 -------------------------------------------------
CLAUSES_902: Final[tuple[Clause, ...]] = (
    _c("902_창", "시간 창 09:00~09:02", lambda f: f["시분초"] < 90200, droppable=False),
    _c("902_가격대", "현재가 1,000~50,000",
       lambda f: (f["현재가"] > 1000) & (f["현재가"] <= 50000)),
    _c("902_등락율", "등락율 1~8%",
       lambda f: (f["등락율"] > 1.0) & (f["등락율"] <= 8.0)),
    _c("902_고저평균", "고저평균대비등락율 > 0", lambda f: f["고저평균대비등락율"] > 0),
    _c("902_라운드피겨", "라운드피겨 위 5호가 회피",
       lambda f: f["라운드피겨위5호가이내"] == 0),
    _c("902_시총", "시가총액 < 3,000억", lambda f: f["시가총액"] < 3000),
    _c("902_시가등락율", "시가등락율 2~4%",
       lambda f: (f["시가등락율"] >= 2.0) & (f["시가등락율"] < 4.0)),
    _c("902_시가대비", "시가대비등락율 0.5~6%",
       lambda f: (f["시가대비등락율"] >= 0.5) & (f["시가대비등락율"] < 6.0)),
    _c("902_순매수금액", "초당순매수금액 1~1,000백만",
       lambda f: (f["초당순매수금액"] > 1) & (f["초당순매수금액"] < 1000)),
    _c("902_일중위치", "일중위치 > 0.8 (고가 근처)", lambda f: f["일중위치"] > 0.8),
    _c("902_전일비", "전일비 > 0 · 전일동시간비 > 0",
       lambda f: (f["전일비"] > 0) & (f["전일동시간비"] > 0)),
    _c("902_회전율", "회전율 > 2", lambda f: f["회전율"] > 2),
    _c("902_거래대금", "당일거래대금 > 500백만", lambda f: f["당일거래대금"] > 500),
    _c("902_거래대금급증", "초당거래대금 30초평균 대비 > 3.0배",
       lambda f: f["초당거래대금배율_30"] > 3.0),
    _c("902_매수흐름", "초당매수수량 > 매도총잔량 x 0.20",
       lambda f: f["매수흐름_매도잔량비"] > 0.20),
    _c("902_잔량비", "매도총잔량 / 매수총잔량 0.10~2.0",
       lambda f: (f["잔량비"] > 0.10) & (f["잔량비"] < 2.0)),
    _c("902_체결강도", "체결강도 50~300",
       lambda f: (f["체결강도"] >= 50) & (f["체결강도"] <= 300)),
)

# --- 09:02:00 ~ 09:05:00 분기 (같은 골격, 다른 임계) --------------------------
CLAUSES_905: Final[tuple[Clause, ...]] = (
    _c("905_창", "시간 창 09:02~09:05",
       lambda f: (f["시분초"] >= 90200) & (f["시분초"] < 90500), droppable=False),
    _c("905_가격대", "현재가 1,000~30,000",
       lambda f: (f["현재가"] > 1000) & (f["현재가"] <= 30000)),
    _c("905_등락율", "등락율 2~15%",
       lambda f: (f["등락율"] > 2.0) & (f["등락율"] <= 15.0)),
    _c("905_고저평균", "고저평균대비등락율 > 0", lambda f: f["고저평균대비등락율"] > 0),
    _c("905_라운드피겨", "라운드피겨 위 5호가 회피",
       lambda f: f["라운드피겨위5호가이내"] == 0),
    _c("905_거래대금직전비", "초당거래대금 직전초 대비 > 1.0",
       lambda f: f["초당거래대금직전비"] > 1.0),
    _c("905_시총", "시가총액 < 3,000억", lambda f: f["시가총액"] < 3000),
    _c("905_시가등락율", "시가등락율 0~8%",
       lambda f: (f["시가등락율"] >= 0.0) & (f["시가등락율"] < 8.0)),
    _c("905_시가대비", "시가대비등락율 3~8%",
       lambda f: (f["시가대비등락율"] >= 3.0) & (f["시가대비등락율"] < 8.0)),
    _c("905_순매수금액", "초당순매수금액 1~1,000백만",
       lambda f: (f["초당순매수금액"] > 1) & (f["초당순매수금액"] < 1000)),
    _c("905_일중위치", "일중위치 > 0.8 (고가 근처)", lambda f: f["일중위치"] > 0.8),
    _c("905_전일비", "전일비 > 5 · 전일동시간비 > 0",
       lambda f: (f["전일비"] > 5) & (f["전일동시간비"] > 0)),
    _c("905_회전율", "회전율 > 1.5", lambda f: f["회전율"] > 1.5),
    _c("905_거래대금", "당일거래대금 > 5,000백만", lambda f: f["당일거래대금"] > 5000),
    _c("905_거래대금급증", "초당거래대금 30초평균 대비 > 2.0배",
       lambda f: f["초당거래대금배율_30"] > 2.0),
    _c("905_매수흐름", "초당매수수량 > 매도총잔량 x 0.30",
       lambda f: f["매수흐름_매도잔량비"] > 0.30),
    _c("905_체결강도", "체결강도 50~300",
       lambda f: (f["체결강도"] >= 50) & (f["체결강도"] <= 300)),
)

BRANCHES: Final = {"902": CLAUSES_902, "905": CLAUSES_905}

#: 뺄 수 있는 절 전부 — 제거 실험의 격자다. 실행 전에 고정된다(헌법 5항).
DROPPABLE: Final[tuple[str, ...]] = tuple(
    c.key for clauses in BRANCHES.values() for c in clauses if c.droppable)


def _validate_drop(drop: str) -> None:
    """제거 대상을 **전체 등록부** 기준으로 검사한다.

    분기별로 검사하면 "다른 분기의 구조 절"을 미등록으로 오인한다(실측: 902 분기를
    먼저 평가하다가 `905_창` 을 '알 수 없는 절'로 보고했다 — 실제로는 뺄 수 없는
    절이라고 말해야 한다).
    """
    for clauses in BRANCHES.values():
        for clause in clauses:
            if clause.key == drop:
                if not clause.droppable:
                    raise ValueError(f"구조 절은 뺄 수 없다: {drop} — 빼면 분기가 겹친다")
                return
    raise KeyError(f"알 수 없는 절: {drop}")


def branch_mask(frame: pd.DataFrame, branch: str, *, drop: str | None = None) -> pd.Series:
    """분기 하나의 마스크. `drop` 을 주면 그 절만 빼고 AND 한다.

    다른 분기의 절을 넘기면 이 분기는 그대로다 — 무시가 아니라 정상이다
    (절 이름에 분기 접두가 있으므로 소속이 명확하다).
    """
    clauses = BRANCHES[branch]
    if drop is not None:
        _validate_drop(drop)
    result: pd.Series | None = None
    for clause in clauses:
        if clause.key == drop:
            continue
        part = clause.predicate(frame)
        result = part if result is None else (result & part)
    assert result is not None
    return result


def champion_mask(frame: pd.DataFrame, *, drop: str | None = None) -> pd.Series:
    """챔피언 진입 마스크 = 902 분기 OR 905 분기.

    `drop` 은 그 절을 가진 분기에서만 빠진다 — 절 이름에 분기 접두가 있으므로
    다른 분기는 영향받지 않는다.
    """
    return branch_mask(frame, "902", drop=drop) | branch_mask(frame, "905", drop=drop)


#: 절 → 챔피언 매수 DSL 안에서 그 절을 **유일하게** 가리키는 문자열.
#:
#: 지도에서 "완화 후보"로 나온 절을 엔진에 올리려면 실제 조건식에서 빼야 한다.
#: 자동 매칭 대신 문자열을 손으로 등록하는 이유: 902/905 분기가 같은 변수를 다른
#: 임계로 쓰기 때문에(예: 전일비 > 0 / > 5) 변수 이름만으로는 어느 분기인지
#: 구분되지 않는다. 유일성은 테스트가 확인한다.
DSL_ANCHOR: Final[dict[str, str]] = {
    "905_시가대비": "3.0 <= 시가대비등락율 < 8.0",
    "905_거래대금급증": "초당거래대금 / 초당거래대금평균(30) > 2.0",
    "905_전일비": "전일비 > 5 and 전일동시간비 > 0",
    "902_거래대금급증": "초당거래대금 / 초당거래대금평균(30) > 3.0",
    "902_회전율": "회전율 > 2",
    "905_거래대금": "당일거래대금 > 50 * 100",
}


def drop_clause_from_dsl(code: str, clause_key: str) -> str:
    """챔피언 매수 DSL 에서 절 하나를 **주석 처리**한다.

    지우지 않고 주석으로 남기는 이유: 엔진에 올라간 조건식만 보고도 "챔피언에서
    무엇을 뺐는지" 알 수 있어야 한다. 삭제하면 그 사실이 사라진다.

    `elif not (...):` 와 바로 뒤의 `매수 = False` 두 줄이 한 절이다.
    """
    anchor = DSL_ANCHOR.get(clause_key)
    if anchor is None:
        raise KeyError(f"DSL 앵커가 등록되지 않은 절: {clause_key} "
                       f"(등록됨: {sorted(DSL_ANCHOR)})")
    if code.count(anchor) != 1:
        raise ValueError(f"앵커가 {code.count(anchor)}회 나타난다 — 유일해야 한다: {anchor}")

    lines = code.splitlines()
    index = next(i for i, line in enumerate(lines) if anchor in line)
    # 사슬의 **첫** 분기(`if`)를 주석 처리하면 뒤의 `elif` 가 고아가 되어
    #   SyntaxError 다. `elif` 만 뺀다.
    if not lines[index].lstrip().startswith("elif "):
        raise ValueError(
            f"사슬의 첫 분기는 뺄 수 없다(뒤의 elif 가 고아가 된다): {lines[index].strip()!r}")
    if "매수 = False" not in lines[index + 1]:
        raise ValueError(f"절 구조가 예상과 다르다: {lines[index + 1]!r}")

    marker = f"  # [완화] {clause_key} 제거"
    lines[index] = "# " + lines[index].lstrip() + marker
    lines[index + 1] = "# " + lines[index + 1].lstrip()
    return "\n".join(lines)


def clause_by_key(key: str) -> Clause:
    for clauses in BRANCHES.values():
        for clause in clauses:
            if clause.key == key:
                return clause
    raise KeyError(f"알 수 없는 절: {key}")


def required_columns() -> set[str]:
    """절이 참조하는 열 이름 — 로더가 이 목록만 읽으면 된다."""
    import inspect
    import re

    names: set[str] = set()
    for clauses in BRANCHES.values():
        for clause in clauses:
            source = inspect.getsource(clause.predicate)
            names.update(re.findall(r'f\[\s*"([^"]+)"\s*\]', source))
    return names


def summary() -> list[dict]:
    """해부도 한 장 — 절 목록과 제거 가능 여부."""
    return [{"branch": branch, "key": c.key, "label": c.label, "droppable": c.droppable}
            for branch, clauses in BRANCHES.items() for c in clauses]


def clause_count(clauses: Sequence[Clause] | None = None) -> int:
    if clauses is not None:
        return len(clauses)
    return sum(len(c) for c in BRANCHES.values())
