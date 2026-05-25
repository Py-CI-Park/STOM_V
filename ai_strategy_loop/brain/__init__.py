"""AI strategy loop 생성 브레인 (US-003 Phase 1b).

구성:
  - token_check : 최소 토큰 denylist + 정규화 AST 해시 기반 dedup (RV2-5: 무거운
                  AST allowlist 대신 값싼 보험만).
  - prompt      : v1 자산으로 system/user 메시지 조립 + 코드 블록 추출.
  - generator   : provider.chat → 추출 → compile → token_check → dedup → save 파이프라인.
"""

from __future__ import annotations

from .generator import generate_strategy
from .prompt import build_messages, extract_code
from .token_check import DedupTracker, check_tokens, normalized_ast_hash
from .variable_scope import check_variable_scope

__all__ = [
    "check_tokens",
    "normalized_ast_hash",
    "DedupTracker",
    "build_messages",
    "extract_code",
    "generate_strategy",
    "check_variable_scope",
]
