"""G1 — 복합 조건식 예제집(composite_examples.md) 계약 테스트.

모든 샘플은 `# [BUY|SELL][tick|min] <ID>` 헤더를 가진 python 코드펜스이며,
1) 선언된 timeframe/kind에서 변수 스코프 위반이 없어야 하고,
2) 문법상 유효(ast.parse)해야 하며,
3) 매수 12개 이상 / 매도 8개 이상이어야 하고,
4) Context Pack 자산으로 등재되어 있어야 한다.
"""
import ast
import re
from pathlib import Path

from ai_strategy_loop.brain.prompt import _FULL_STOM_SOURCE_ASSETS
from ai_strategy_loop.brain.variable_scope import check_variable_scope

_DOC = Path(__file__).resolve().parents[2] / "utility" / "ai_agent" / "system_prompt" / "v1" / "composite_examples.md"
_FENCE_RE = re.compile(r"```python\n(# \[(BUY|SELL)\]\[(tick|min)\][^\n]*\n)(.*?)```", re.DOTALL)


def _samples():
    text = _DOC.read_text(encoding="utf-8")
    out = []
    for m in _FENCE_RE.finditer(text):
        header, kind, timeframe, body = m.group(1), m.group(2), m.group(3), m.group(4)
        out.append((header.strip(), kind.lower(), timeframe, header + body))
    return out


def test_sample_counts_meet_contract():
    samples = _samples()
    buys = [s for s in samples if s[1] == "buy"]
    sells = [s for s in samples if s[1] == "sell"]
    assert len(buys) >= 12, f"매수 샘플 {len(buys)}개 (<12)"
    assert len(sells) >= 8, f"매도 샘플 {len(sells)}개 (<8)"
    # P2(아키텍트 리뷰): 헤더 규약을 벗어난 python 펜스가 조용히 누락되지 않게
    #   전체 python 펜스 수 == 파싱된 샘플 수 완전성 단언.
    text = _DOC.read_text(encoding="utf-8")
    assert text.count("```python") == len(samples), "헤더 없는/깨진 python 펜스 존재"
    # 샘플 ID 유일성(파서가 같은 샘플을 두 번 세지 않음을 보장).
    headers = [s[0] for s in samples]
    assert len(set(headers)) == len(headers)


def test_every_sample_parses_and_passes_variable_scope():
    failures = []
    for header, kind, timeframe, code in _samples():
        try:
            ast.parse(code)
        except SyntaxError as exc:
            failures.append(f"{header}: SyntaxError {exc}")
            continue
        ok, offending = check_variable_scope(code, timeframe, kind)
        if not ok:
            failures.append(f"{header}: scope 위반 {offending}")
    assert not failures, "\n".join(failures)


def _referenced_names(code: str) -> set:
    return {n.id for n in ast.walk(ast.parse(code)) if isinstance(n, ast.Name)}


_SELL_ONLY_NAMES = {
    "수익금", "수익률", "최고수익률", "최저수익률", "매수가",
    "보유수량", "보유시간", "분할매수횟수", "분할매도횟수",
}

_FORCE_CLOSE_RE = re.compile(r"시분초\s*>=\s*\d+")
_STOP_LOSS_RE = re.compile(
    r"수익률\s*<=\s*-|최저수익률\s*<=\s*-|현재가\s*<\s*매수가|현재가\s*<\s*최저현재가|"
    r"현재가\s*<\s*분봉저가N|현재가\s*<\s*이동평균"
)


def test_buy_samples_end_with_action_and_avoid_sell_vars():
    for header, kind, timeframe, code in _samples():
        if kind == "buy":
            assert "self.Buy()" in code, header
            # P3(아키텍트 리뷰): 부분문자열 대신 AST Name 정확 일치로 매도전용 변수 검사.
            leaked = _referenced_names(code) & _SELL_ONLY_NAMES
            assert not leaked, f"{header}: 매수식에 매도전용 변수 {sorted(leaked)}"
        else:
            assert "self.Sell()" in code, header


def test_sell_samples_carry_force_close_and_stop_loss():
    """P3(아키텍트 리뷰): CSC-07/CSC-10/CSC-11 안전망을 회귀 가드로 강제."""
    for header, kind, timeframe, code in _samples():
        if kind != "sell":
            continue
        assert _FORCE_CLOSE_RE.search(code), f"{header}: 시분초 강제청산 분기 부재"
        assert _STOP_LOSS_RE.search(code), f"{header}: 손절/구조이탈 분기 부재"
        stripped = code.replace(" ", "")
        if timeframe == "tick":
            assert "시분초>=927" in stripped, f"{header}: tick 강제청산이 09:30 이내가 아님"
        else:
            assert "시분초>=151800" in stripped, f"{header}: min 강제청산이 15:18이 아님"


def test_tick_buy_samples_reference_session_window():
    for header, kind, timeframe, code in _samples():
        if kind == "buy" and timeframe == "tick":
            assert "시분초" in code, f"{header}: tick 매수식에 시간창 참조 없음"


def test_registered_in_full_stom_source_assets():
    by_name = dict(_FULL_STOM_SOURCE_ASSETS)
    assert "composite_examples" in by_name
    assert by_name["composite_examples"].exists()


def test_hypothesis_and_disclaimer_present():
    text = _DOC.read_text(encoding="utf-8")
    assert "무근거 가설" in text
    assert text.count("가설:") >= 20  # 샘플마다 엣지 가설 주석
