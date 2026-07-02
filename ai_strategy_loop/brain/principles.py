"""차트술사 구조론 원리 문서 로더 (T4.1, Phase 1).

`utility/ai_agent/system_prompt/v1/`의 원리 계층 3문서를 읽어 문자열로 반환한다.

  - principles.md            : 원리 계층 (원문 마스터 프롬프트 0~28장 재구성)
  - constraints_checklist.md : AI 금지사항 7개조 + 검증 주의점 기계 판정 체크리스트
  - idiom_dictionary.md      : 원리 개념 → STOM 변수 관용구 사전 (tick/min 구분)

주의:
  - 이 모듈은 **어디에도 자동 연결되지 않는다**. build_messages는 이 로더를 부르지
    않으며, Phase 2의 Context Pack이 소비할 예정이다(현 시점 기본 동작 불변).
  - 문서 내용은 백테스트로 검증되지 않은 가설 체계다. 소비자는 임계값을 검증된
    사실로 취급하면 안 된다(각 문서 서두에 동일 경고 명시).
  - 토글: ai_strategy_loop.config.LoopConfig.principle_docs_enabled (기본 False).
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PRINCIPLE_DOC_DIR = _REPO_ROOT / "utility" / "ai_agent" / "system_prompt" / "v1"

PRINCIPLES_PATH = _PRINCIPLE_DOC_DIR / "principles.md"
CONSTRAINTS_PATH = _PRINCIPLE_DOC_DIR / "constraints_checklist.md"
IDIOMS_PATH = _PRINCIPLE_DOC_DIR / "idiom_dictionary.md"


def _read_doc(path: Path) -> str:
    """원리 문서 하나를 읽어 반환한다. 없거나 비어 있으면 명시적으로 실패한다."""
    if not path.is_file():
        raise FileNotFoundError(f"원리 문서가 없습니다: {path}")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"원리 문서가 비어 있습니다: {path}")
    return text


def load_principles() -> str:
    """원리 계층 문서(principles.md) 전문을 반환한다."""
    return _read_doc(PRINCIPLES_PATH)


def load_constraints() -> str:
    """제약 체크리스트 문서(constraints_checklist.md) 전문을 반환한다."""
    return _read_doc(CONSTRAINTS_PATH)


def load_idioms() -> str:
    """관용구 사전 문서(idiom_dictionary.md) 전문을 반환한다."""
    return _read_doc(IDIOMS_PATH)


__all__ = [
    "PRINCIPLES_PATH",
    "CONSTRAINTS_PATH",
    "IDIOMS_PATH",
    "load_principles",
    "load_constraints",
    "load_idioms",
]
