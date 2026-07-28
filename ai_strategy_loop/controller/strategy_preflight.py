"""조건식 사전 검증기(preflight) — 평가 전 fail-fast 게이트.

배경(2026-07-28 tick 연구 전수검사 실측):
  - 결함 A: 구문 오류 조건식이 엔진에서 fail-fast 되지 않고 per-run 타임아웃(기본 600초)까지
    정지한다(elelif 결함 쌍 2회 재현 → 수정 후 동일 쌍 46초 정상, 인과 확정).
  - 결함 B: SSOT 어휘 밖이면서 로컬 할당도 없는 미정의 변수(예: CSS_V7 매도식 9종의
    `강제청산`)는 실행 시 NameError 로 같은 무한 정지를 만든다. 매도식은 체결이 있어야
    평가되므로 "거래 0건 쌍만 완주"라는 교착 서명으로 나타났다.

이 모듈은 엔진을 수정하지 않는다. 배치/루프가 조건식을 엔진에 넣기 **전에**
① ast 구문 검증 ② 미정의 변수 검증(로드 식별자 − 로컬 할당 − SSOT − 파이썬 내장 − self)
을 수행해 1초 안에 불량을 걸러낸다.

SSOT 어휘는 대시보드와 동일 원천(ai_strategy_loop.dashboard.backtest_api._load_ssot_vocabulary)
을 재사용한다 — 두 개의 어휘 사본을 만들지 않는다(단일 진실 공급원).
"""

from __future__ import annotations

import ast
import builtins
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set

_LOOP_STRATEGY_DB = Path(__file__).resolve().parents[1] / "state" / "loop_strategies.db"
_TABLE_BY_KIND = {"buy": "stockbuy", "sell": "stocksell"}

# 엔진이 조건식 네임스페이스에 항상 주입하는 비-SSOT 이름들.
_ALWAYS_ALLOWED = {"self", "int", "float", "abs", "max", "min", "len", "round", "True", "False", "None"}


@dataclass
class PreflightIssue:
    kind: str          # "syntax" | "undefined"
    detail: str


@dataclass
class PreflightResult:
    ok: bool
    issues: List[PreflightIssue] = field(default_factory=list)

    @property
    def reason(self) -> str:
        return " · ".join(f"{i.kind}: {i.detail}" for i in self.issues) or "ok"


def _ssot_vocabulary() -> Set[str]:
    """대시보드 SSOT 로더 재사용(프로세스 생애 1회 캐시는 로더가 소유). 실패 시 빈 집합."""
    try:
        from ai_strategy_loop.dashboard.backtest_api import _load_ssot_vocabulary  # noqa: PLC0415

        return set(_load_ssot_vocabulary())
    except Exception:  # noqa: BLE001 - 어휘 로드 실패가 평가를 막으면 안 된다(구문 검증은 유지).
        return set()


def validate_strategy_code(code: str, *, ssot: Optional[Set[str]] = None) -> PreflightResult:
    """조건식 코드 1개를 검증한다. 엔진 실행 없음, 밀리초 단위.

    - 구문: ast.parse (self.Buy()/Sell() 은 유효 구문이므로 치환 불필요)
    - 미정의: Load 식별자 − Store 식별자 − SSOT − 내장 − 상시 허용 이름
      (함수형 화이트리스트 토큰도 SSOT 에 포함돼 있어 Call.func 이름까지 커버된다)
    """
    text = str(code or "")
    if not text.strip():
        return PreflightResult(False, [PreflightIssue("syntax", "빈 코드")])
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return PreflightResult(False, [PreflightIssue(
            "syntax", f"line {exc.lineno}: {exc.msg}")])

    vocab = _ssot_vocabulary() if ssot is None else ssot
    stores: Set[str] = set()
    loads: Set[str] = set()
    gui_calls: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            (stores if isinstance(node.ctx, ast.Store) else loads).add(node.id)
        # v5.13.2(결함 F) — GUI식 다인자 self.Buy/Sell 호출 검출. 백테 엔진 시그니처는
        #   Buy(buy_long=False)/Sell(sell_long=False)(위치 인자 최대 1개)라서, GUI식
        #   7-인자 호출은 체결 성립 틱마다 TypeError 를 던져 무한 정지로 나타난다
        #   (2026-07-28 실측: C_T_900_920_U2 매수식 — 조건 성립 순간부터 600초 정지).
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "self"
                and node.func.attr in ("Buy", "Sell")):
            n_args = len(node.args) + len(node.keywords)
            if n_args > 1:
                gui_calls.append(f"self.{node.func.attr}({n_args}개 인자)")
    if gui_calls:
        return PreflightResult(False, [PreflightIssue(
            "gui_signature",
            "백테 엔진 시그니처 위반(최대 1인자) — GUI식 호출: " + ", ".join(sorted(set(gui_calls)))
            + " → self.Buy()/self.Sell() 로 바꿔야 합니다")])
    undefined = sorted(
        name for name in loads
        if name not in stores
        and name not in vocab
        and name not in _ALWAYS_ALLOWED
        and not hasattr(builtins, name)
    )
    if vocab and undefined:  # 어휘 로드 실패(빈 집합) 시에는 오탐을 내지 않는다.
        return PreflightResult(False, [PreflightIssue(
            "undefined", "미정의 변수 " + ", ".join(undefined[:8])
            + (f" 외 {len(undefined) - 8}개" if len(undefined) > 8 else ""))])
    return PreflightResult(True)


def load_loop_strategy_code(kind: str, name: str, db_path: Optional[Path] = None) -> Optional[str]:
    """loop_strategies.db 에서 전략 코드를 읽는다(읽기 전용). 없으면 None."""
    table = _TABLE_BY_KIND.get(kind)
    if table is None:
        return None
    path = Path(db_path) if db_path else _LOOP_STRATEGY_DB
    if not path.exists():
        return None
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            row = con.execute(
                f'SELECT "전략코드" FROM {table} WHERE "index"=?', (name,)
            ).fetchone()
            return row[0] if row else None
        finally:
            con.close()
    except Exception:  # noqa: BLE001 - 조회 실패는 '검증 불가'로 취급(None).
        return None


def preflight_pair(buy_name: str, sell_name: str,
                   db_path: Optional[Path] = None) -> PreflightResult:
    """(매수, 매도) 쌍 사전 검증 — 배치/루프가 엔진 실행 전에 호출한다."""
    issues: List[PreflightIssue] = []
    ssot = _ssot_vocabulary()
    for kind, name in (("buy", buy_name), ("sell", sell_name)):
        code = load_loop_strategy_code(kind, name, db_path=db_path)
        if code is None:
            issues.append(PreflightIssue("undefined", f"{kind} 전략 '{name}' 없음(loop_strategies.db)"))
            continue
        result = validate_strategy_code(code, ssot=ssot)
        if not result.ok:
            for issue in result.issues:
                issues.append(PreflightIssue(issue.kind, f"[{kind}:{name}] {issue.detail}"))
    return PreflightResult(not issues, issues)
