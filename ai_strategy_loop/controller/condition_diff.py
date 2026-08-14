"""조건식 비교 — 두 조건식이 **어디가 다른가**를 절 단위로 본다.

## 왜 필요한가

원장(페이지 30)은 "어느 후보가 나은가"를 답한다. 그런데 그 다음 질문에 답할
화면이 없었다: **"그래서 정확히 뭐가 다른가?"**

지금까지는 그 답을 커밋 메시지와 문서에 손으로 적어 왔다. 손으로 적으면
어긋난다 — 실제로 W6 에서 "조기 청산 한 줄만 얹었다"는 서술이 맞는지
매번 렌더 결과를 눈으로 확인해야 했다.

이 모듈은 그 대조를 코드로 만든다.

## 두 층으로 본다

| 층 | 무엇을 보나 | 쓸모 |
|---|---|---|
| **절** | 이름 붙은 절이 살아 있나 / 주석 처리됐나 / 없나 | "무엇을 뺐나"가 한 줄로 |
| **줄** | 표준 라인 diff | 절 이름이 없는 변화도 놓치지 않는다 |

절 층만 보면 임계 변경(`> 2` → `> 1.5`)을 놓치고, 줄 층만 보면 공백·주석
잡음에 묻힌다. 둘 다 낸다.

## 규율

이 모듈은 **조건식을 실행하지 않는다.** 텍스트만 읽는다.
`exec`/`eval`/`compile` 을 쓰지 않는 것이 계약이다.
"""

from __future__ import annotations

import difflib
import re
from typing import Any, Final, Sequence

from ai_strategy_loop.labeling.champion_clauses import BRANCHES, DSL_ANCHOR

#: 주석 판정 — 앞 공백 뒤 `#`.
_COMMENT: Final = re.compile(r"^\s*#")


def _is_comment(line: str) -> bool:
    return bool(_COMMENT.match(line))


def _strip_comment_marker(line: str) -> str:
    """주석 기호를 떼어 낸 알맹이 — 주석 처리만 다른 줄을 알아보기 위해."""
    return re.sub(r"^\s*#\s?", "", line).strip()


def clause_state(code: str) -> dict[str, str]:
    """이름 붙은 절이 이 조건식에서 어떤 상태인가.

    | 상태 | 뜻 |
    |---|---|
    | `active` | 살아 있다 |
    | `commented` | 주석 처리됐다(제거 실험의 흔적) |
    | `absent` | 이 조건식에 아예 없다 |

    앵커가 등록된 절만 판정한다 — 앵커 없이 변수 이름으로 찾으면 902/905 가
    같은 변수를 다른 임계로 쓰기 때문에 어느 분기인지 구분되지 않는다.
    """
    lines = code.splitlines()
    out: dict[str, str] = {}
    for key, anchor in DSL_ANCHOR.items():
        hit = next((l for l in lines if anchor in l), None)
        if hit is None:
            out[key] = "absent"
        else:
            out[key] = "commented" if _is_comment(hit) else "active"
    return out


def clause_delta(left: str, right: str) -> list[dict[str, str]]:
    """절 상태가 **달라진** 것만. 같은 것은 소음이다."""
    a, b = clause_state(left), clause_state(right)
    rows = []
    for key in DSL_ANCHOR:
        if a[key] == b[key]:
            continue
        label = next((c.label for clauses in BRANCHES.values()
                      for c in clauses if c.key == key), key)
        rows.append({"clause": key, "label": label, "left": a[key], "right": b[key]})
    return rows


def diff_lines(left: str, right: str, *, context: int = 2) -> list[dict[str, Any]]:
    """줄 단위 diff — 바뀐 곳과 그 주변만.

    전체를 다 뿌리면(챔피언 매수식은 131줄) 화면에서 차이를 못 찾는다.
    바뀐 덩어리와 앞뒤 `context` 줄만 낸다.
    """
    a, b = left.splitlines(), right.splitlines()
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
    rows: list[dict[str, Any]] = []
    last_end = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        start = max(i1 - context, last_end)
        if start > last_end and rows:
            rows.append({"op": "gap", "left_no": None, "right_no": None,
                         "text": f"… {start - last_end}줄 생략 …"})
        for k in range(start, i1):                       # 앞 문맥
            rows.append({"op": "same", "left_no": k + 1,
                         "right_no": j1 - (i1 - k) + 1, "text": a[k]})
        for k in range(i1, i2):
            rows.append({"op": "del", "left_no": k + 1, "right_no": None, "text": a[k]})
        for k in range(j1, j2):
            rows.append({"op": "add", "left_no": None, "right_no": k + 1, "text": b[k]})
        tail = min(i2 + context, len(a))
        for k in range(i2, tail):                        # 뒤 문맥
            rows.append({"op": "same", "left_no": k + 1,
                         "right_no": j2 + (k - i2) + 1, "text": a[k]})
        last_end = tail

    if not rows:
        rows.append({"op": "identical", "left_no": None, "right_no": None,
                     "text": "두 조건식이 완전히 같다"})
    return rows


def _code_lines(code: str) -> list[str]:
    return [l.strip() for l in code.splitlines() if l.strip() and not _is_comment(l)]


def _missing(a: Sequence[str], b: Sequence[str]) -> list[str]:
    """a 에는 있고 b 에는 없는 줄(중복 개수까지 센다)."""
    rest = list(b)
    out = []
    for line in a:
        if line in rest:
            rest.remove(line)
        else:
            out.append(line)
    return out


def comment_only(left: str, right: str) -> bool:
    """차이가 **코드를 주석으로 옮긴 것뿐**인가 — 절 제거 실험이 그렇게 생긴다.

    단순히 줄을 나란히 비교하지 않는다: 제거 렌더는 주석에 설명 마커를 붙이므로
    (`# elif not (...):  # [완화] 905_시가대비 제거`) 글자 대조로는 안 맞는다.
    코드 줄이 **빠지기만** 했고, 빠진 줄이 오른쪽에 주석으로 남아 있으면 참이다.
    """
    a, b = _code_lines(left), _code_lines(right)
    if a == b:
        return False                       # 코드가 같으면 '제거'가 아니다
    removed = _missing(a, b)
    if not removed or _missing(b, a):
        return False                       # 오른쪽에만 있는 코드가 있다 = 단순 주석화가 아니다
    commented = [_strip_comment_marker(l) for l in right.splitlines() if _is_comment(l)]
    # 설명 마커가 뒤에 붙을 수 있으므로 앞부분 일치로 본다.
    return all(any(c.startswith(line) for c in commented) for line in removed)


def compare(left_name: str, left_code: str,
            right_name: str, right_code: str, *,
            context: int = 2) -> dict[str, Any]:
    """비교 한 장 — 절 층 + 줄 층 + 요약."""
    rows = diff_lines(left_code, right_code, context=context)
    changed = [r for r in rows if r["op"] in ("del", "add")]
    code_lines = lambda t: len([l for l in t.splitlines()
                                if l.strip() and not _is_comment(l)])
    return {
        "available": True,
        "left": {"name": left_name, "lines": len(left_code.splitlines()),
                 "code_lines": code_lines(left_code)},
        "right": {"name": right_name, "lines": len(right_code.splitlines()),
                  "code_lines": code_lines(right_code)},
        "identical": not changed,
        "comment_only": comment_only(left_code, right_code),
        "clause_delta": clause_delta(left_code, right_code),
        "diff": rows,
        "changed_lines": len(changed),
        "note": ("절 층은 앵커가 등록된 절만 본다. 임계만 바꾼 변화는 줄 층에서 "
                 "확인한다 — 두 층을 함께 읽어야 놓치지 않는다."),
    }


def known_clauses() -> list[dict[str, str]]:
    """앵커가 등록된 절 목록 — 화면 범례용."""
    return [{"clause": key,
             "label": next((c.label for clauses in BRANCHES.values()
                            for c in clauses if c.key == key), key)}
            for key in sorted(DSL_ANCHOR)]


def pick_pairs(names: Sequence[str], *, prefix: str) -> list[str]:
    """우리 이름공간의 후보만 — 남의 자산을 화면 기본값으로 올리지 않는다."""
    return sorted(n for n in names if str(n).startswith(prefix))
