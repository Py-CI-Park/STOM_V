"""T4.1 원리 문서 3종 + 로더 + 토글 기본값 검증.

검증 대상:
  - utility/ai_agent/system_prompt/v1/{principles.md, constraints_checklist.md,
    idiom_dictionary.md} 존재·비어있지 않음·핵심 헤더/경고 문구.
  - ai_strategy_loop/brain/principles.py 로더 3종이 str을 반환.
  - LoopConfig.principle_docs_enabled 기본 False (기본 동작 불변 보장).
"""

import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_strategy_loop.brain.principles import (  # noqa: E402
    CONSTRAINTS_PATH,
    IDIOMS_PATH,
    PRINCIPLES_PATH,
    load_constraints,
    load_idioms,
    load_principles,
)
from ai_strategy_loop.config import LoopConfig  # noqa: E402


@pytest.mark.parametrize(
    "path",
    [PRINCIPLES_PATH, CONSTRAINTS_PATH, IDIOMS_PATH],
    ids=["principles", "constraints", "idioms"],
)
def test_principle_doc_exists_and_nonempty(path):
    assert path.is_file(), f"원리 문서 파일이 없음: {path}"
    text = path.read_text(encoding="utf-8")
    assert text.strip(), f"원리 문서가 비어 있음: {path}"


@pytest.mark.parametrize(
    ("loader", "header"),
    [
        (load_principles, "# 차트술사 구조론 원리 계층"),
        (load_constraints, "# 차트술사 구조론 제약 체크리스트"),
        (load_idioms, "# 원리 개념 → STOM 변수 관용구 사전"),
    ],
    ids=["principles", "constraints", "idioms"],
)
def test_loader_returns_str_with_header(loader, header):
    text = loader()
    assert isinstance(text, str)
    first_line = text.lstrip().splitlines()[0]
    assert first_line.startswith(header), f"헤더 불일치: {first_line!r}"


def test_principles_doc_declares_unverified_hypothesis():
    """원리 문서는 서두에 '백테스트 미검증 가설 체계' 경고를 명시해야 한다."""
    text = load_principles()
    assert "백테스트로 검증되지 않은 가설 체계" in text
    assert "무근거 가설" in text


def test_constraints_doc_has_machine_checkable_ids():
    """금지사항 7개조(CSC-01~07) + 검증 주의점(CSC-10~) id가 존재해야 한다."""
    text = load_constraints()
    for i in range(1, 8):
        assert f"CSC-0{i}" in text, f"금지사항 id 누락: CSC-0{i}"
    assert "CSC-10" in text  # tick 시간창 09:00~09:30
    assert "매수식에 대응 손절 매도조건 부재" in text
    assert "거래량/거래대금 조건 없는 돌파 매수" in text


def test_idioms_doc_distinguishes_tick_and_min():
    """관용구 사전은 tick/min 변수 구분과 핵심 관용구를 포함해야 한다."""
    text = load_idioms()
    assert "[tick]" in text and "[min]" in text
    assert "최고현재가(" in text  # 박스 상단 관용구
    assert "초당거래대금평균" in text  # 사건거래대금 tick
    assert "분당거래대금평균" in text  # 사건거래대금 min


def test_principle_docs_toggle_default_off():
    """토글 기본 OFF — 기본 설정에서 원리 문서 소비 의사가 표시되지 않아야 한다."""
    cfg = LoopConfig()
    assert cfg.principle_docs_enabled is False
    # 직렬화 왕복에도 기본값 유지
    assert LoopConfig.from_dict(cfg.to_dict()).principle_docs_enabled is False


def test_loader_raises_on_missing_file(tmp_path, monkeypatch):
    """존재 검증: 파일이 없으면 FileNotFoundError로 명시적으로 실패해야 한다."""
    import ai_strategy_loop.brain.principles as P

    monkeypatch.setattr(P, "PRINCIPLES_PATH", tmp_path / "no_such_doc.md")
    with pytest.raises(FileNotFoundError):
        P.load_principles()
