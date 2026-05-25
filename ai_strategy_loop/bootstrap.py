"""AI strategy loop bootstrap (M1/A1: env-before-import 격리).

이 모듈은 IMPORT 시점에 다음 환경변수를 설정한다 (cli.* / utility.* 가
import 되기 전이어야 함):

  - STOM_CLI_DB_STRATEGY : 루프 전용 격리 DB 경로
        (ai_strategy_loop/state/loop_strategies.db, 절대경로)
  - STOM_ALLOW_MINIMAL_SETTING = "1"
        (CLI에서 암호화 키 불일치 우회)

계약(contract): 모든 루프 엔트리포인트는 cli.* / utility.* import 보다
**먼저** `import ai_strategy_loop.bootstrap` 을 수행해야 한다. 그래야
cli.paths / utility.setting_base 의 DB_STRATEGY 가 import 시점에 격리
경로로 해석된다.

기존 환경변수가 이미 설정되어 있으면 덮어쓰지 않는다 (호출자 오버라이드 존중).
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

# 패키지 루트 (.../ai_strategy_loop)
_PACKAGE_DIR = Path(__file__).resolve().parent

# 루프 전용 격리 DB 경로 (절대경로)
LOOP_STATE_DIR = _PACKAGE_DIR / "state"
LOOP_DB_STRATEGY = LOOP_STATE_DIR / "loop_strategies.db"


def _apply_isolation_env() -> None:
    """격리 환경변수를 import 시점에 적용한다 (idempotent)."""
    # state 디렉토리는 미리 만들어 둔다 (DB는 실제 사용 시 생성).
    LOOP_STATE_DIR.mkdir(parents=True, exist_ok=True)

    # 이미 설정된 값이 있으면 존중한다 (테스트/호출자 오버라이드).
    os.environ.setdefault("STOM_CLI_DB_STRATEGY", str(LOOP_DB_STRATEGY))
    os.environ.setdefault("STOM_ALLOW_MINIMAL_SETTING", "1")


# IMPORT 시점에 즉시 적용 — 이것이 핵심.
_apply_isolation_env()


def resolve_strategy_db() -> str:
    """env가 설정된 뒤 cli.paths 를 import 하여 DB_STRATEGY 를 반환한다.

    env-before-import 계약이 지켜졌는지 확인하는 용도로도 쓰인다.
    """
    # _apply_isolation_env 는 import 시점에 이미 실행됐지만, 방어적으로 재확인.
    _apply_isolation_env()
    from cli.paths import DB_STRATEGY  # noqa: PLC0415 - env 설정 후 지연 import

    return DB_STRATEGY


# 백테 엔진이 DB_STRATEGY에서 추가로 읽는 테이블 (수식/지표 정의).
#   backtest/backengine_base.py:UpdateFormulaData → trade/formula_manager.py:
#   get_formula_data 가 `SELECT * FROM formula` 를 수행한다. 격리 루프 DB에는
#   generator가 stockbuy/stocksell만 만들기 때문에 formula 테이블이 없어
#   sqlite3.OperationalError(no such table: formula) → 엔진이 '백테완료'를
#   못 보내 BackTest child가 데드락(타임아웃)한다.
#
#   운영 strategy.db의 formula 스키마(9컬럼, 0행)를 그대로 빈 테이블로 만든다.
#   행이 비어 있으면 get_formula_data는 ([], {}, 0)을 깔끔히 반환하므로
#   백테 결과(수식 미사용)에 영향이 없다.
_FORMULA_COLUMNS = (
    "수식명", "차트표시", "전략연산", "팩터명",
    "표시형태", "색상", "굵기", "종류", "수식코드",
)


def ensure_loop_db_engine_compat(db_path: str | None = None) -> None:
    """루프 DB가 백테 엔진과 호환되도록 필요한 빈 테이블을 보장한다 (idempotent).

    현재는 `formula` 빈 테이블만 보장한다. stockbuy/stocksell은 generator의
    save 경로(cli.strategy_generator)가 생성하므로 여기서 다루지 않는다.

    백테스트를 실행하는 모든 루프 엔트리포인트는 백테 직전에 한 번 호출해야 한다.
    """
    target = db_path or os.environ.get("STOM_CLI_DB_STRATEGY") or str(LOOP_DB_STRATEGY)
    con = sqlite3.connect(target)
    try:
        cols_sql = ", ".join(f'"{c}" TEXT' for c in _FORMULA_COLUMNS)
        con.execute(f"CREATE TABLE IF NOT EXISTS formula ({cols_sql})")
        con.commit()
    finally:
        con.close()
