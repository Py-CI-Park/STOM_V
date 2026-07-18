"""F3 — Backtest 데이터 분류(divid_mode) GUI 패리티 결손 보강.

검증:
  - 웹 bt-tab-run 이 divid_mode 3옵션을 노출하고, 그 집합이 cli/subcommands.DIVID_MODE_CHOICES
    (백엔드 정본)와 정확히 일치한다(프론트 하드코딩 드리프트 방지).
  - 단일 backtest 모드 payload 에 divid_mode 를 실어보내고, '한종목 로딩' 시 one_code 를 요구한다.
  - 백엔드 /bt/run 은 이미 divid_mode·one_code 를 파싱한다(backtest_api allowed set) — 프론트 결손만 보강.
"""

from __future__ import annotations

from pathlib import Path

from cli.subcommands import DIVID_MODE_CHOICES

ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _front(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_web_divid_mode_options_match_backend_canon() -> None:
    src = _front("bt-tab-run.jsx")
    # 3 정본 옵션이 모두 <option> 으로 노출된다.
    for choice in DIVID_MODE_CHOICES:
        assert f'value="{choice}"' in src, f"divid_mode 옵션 누락: {choice}"
    # 프론트가 정본에 없는 임의 분류 옵션을 추가하지 않았는지(드리프트) — select 블록 한정 검사.
    start = src.find('<label>데이터 분류</label>')
    assert start != -1, "데이터 분류 셀렉터 없음"
    block = src[start:start + 400]
    option_count = block.count("<option ")
    assert option_count == len(DIVID_MODE_CHOICES), f"옵션 개수 불일치: {option_count} != {len(DIVID_MODE_CHOICES)}"


def test_web_sends_divid_mode_and_requires_one_code() -> None:
    src = _front("bt-tab-run.jsx")
    # 단일 backtest 모드에서 payload 에 divid_mode 를 싣는다.
    assert 'payload.divid_mode = dividMode' in src
    assert 'mode === "backtest"' in src
    # '한종목 로딩' 은 one_code 를 요구·전송한다.
    assert 'payload.one_code = oc' in src
    assert "'한종목 로딩'은 종목코드가 필요합니다" in src


def test_backend_bt_run_accepts_divid_mode() -> None:
    # 백엔드가 divid_mode·one_code 를 이미 수용(프론트 결손만 보강했음을 고정).
    api = (ROOT / "ai_strategy_loop" / "dashboard" / "backtest_api.py").read_text(encoding="utf-8")
    assert '"divid_mode"' in api and '"one_code"' in api
