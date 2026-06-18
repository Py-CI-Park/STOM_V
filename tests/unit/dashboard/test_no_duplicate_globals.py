"""P1 — 전역 스코프 단일 번들 최상위 선언 이름 중복 금지 가드(근본 원인 가드레일).

webui-build/build-app.mjs 가 26개 .jsx 를 esbuild transform(번들 아님) 후 ORDER 순서로
연결해 단일 app.js(하나의 최상위 스코프)로 만든다. 두 파일이 같은 최상위
function/const/let/class 이름을 선언하면, 자바스크립트 호이스팅/실행 순서상 **나중(ORDER 뒤)
파일이 조용히 덮어쓴다**(에러 없이) — Phase14.4 리뷰가 잡은 CodeBlock/RunComparePanel 충돌의
원인 클래스. 이 테스트가 그 충돌을 자동 차단한다(P1 수정의 영구 회귀 가드).

순수 Python(node/esbuild 비의존) — P0.5 의 esbuild-skip 클러스터에 들어가지 않는다.
window **자기-재노출 별칭**(`const fmtScore = window.fmtScore`)은 정본이 번들이고 같은 값을
가리키는 무해한 passthrough 이므로 여러 파일에 있어도 충돌이 아니다 → 카운트에서 제외한다
(14.x 공유유틸 패턴에서 여러 .jsx 가 동일 window.* 를 별칭하는 정상 케이스의 오탐 방지).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest  # noqa: F401  (수집 일관성)

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

FRONTEND = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"

# 컬럼0(최상위) 선언만: function/const/let/class NAME. `const {`/`const [`(구조분해)는 식별자가
#   아니므로 미매치 → 파일별 React 훅 별칭(const { useState: ... } = React)은 제외된다.
_DECL = re.compile(r"^(?:export\s+)?(?:async\s+)?(?:function|const|let|class)\s+([A-Za-z_$][\w$]*)")

# P7(2026-06-15) 가드 강화 — 과거: window 자기-별칭(`const NAME = window.NAME`)을 "무해한 passthrough"
#   로 보고 카운트에서 제외했다. 그러나 단일 번들(transform-not-bundle) 한 스코프에서는 같은 최상위
#   이름이 두 번 선언되면(함수+const, const+const, 별칭+정의 무엇이든) "Identifier already declared"
#   SyntaxError 로 **앱 전체가 크래시**한다. 즉 자기-별칭도 엄연한 최상위 선언이라 충돌 대상이다.
#   (실제 사례: P7 에서 research-lab 의 `function VdtPromoteChecklist` 와 dashboard-pages 의
#   `const VdtPromoteChecklist = window.VdtPromoteChecklist` 가 충돌해 전 탭이 깨졌다.)
#   → 자기-별칭 제외를 폐기하고 모든 최상위 선언(별칭 포함)을 카운트한다. format.ts(.ts) 전역을
#   .jsx 한 곳에서 별칭하는 정상 패턴은 이름이 그 파일에만 1회 등장하므로 여전히 통과한다.
def _top_level_decls(src: str) -> list[str]:
    out = []
    for line in src.splitlines():
        m = _DECL.match(line)
        if m:
            out.append(m.group(1))
    return out


def test_no_duplicate_top_level_declarations() -> None:
    """26 .jsx 중 어느 두 파일도 같은 최상위 선언 이름을 갖지 않는다."""
    jsx = sorted(FRONTEND.glob("*.jsx"))
    assert len(jsx) >= 20, f".jsx 수집 비정상({len(jsx)}) — frontend 경로 확인"
    seen: dict[str, list[str]] = {}
    for f in jsx:
        for name in _top_level_decls(f.read_text(encoding="utf-8")):
            seen.setdefault(name, []).append(f.name)
    dups = {n: fs for n, fs in seen.items() if len(fs) > 1}
    assert not dups, (
        "전역 스코프 최상위 이름 중복(단일 번들에서 ORDER 뒤 정의가 조용히 덮어씀 — 이름 고유화 필요):\n"
        + "\n".join(f"  {n}: {fs}" for n, fs in sorted(dups.items()))
    )
