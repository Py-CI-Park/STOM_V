"""US-002 M1/A1: env-before-import 격리 검증.

`ai_strategy_loop.bootstrap` 를 cli.* / utility.* import 보다 먼저 import 하면,
cli.paths.DB_STRATEGY 와 utility.setting_base.DB_STRATEGY 가 production
strategy.db 가 아니라 루프 전용 격리 DB 경로를 가리켜야 한다.

이 테스트는 격리를 깨지 않기 위해 별도 파이썬 서브프로세스에서 실행한다
(같은 프로세스에서 다른 테스트가 이미 cli.paths 를 import 했을 수 있으므로).
"""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 서브프로세스에서 실행할 스크립트: bootstrap 먼저 import → 그 뒤 cli/utility import.
_CHILD_SCRIPT = r"""
import os, sys, json

# 1) bootstrap 먼저 import (env-before-import 계약)
import ai_strategy_loop.bootstrap as bootstrap

# 2) 그 다음에 cli.paths / utility.setting_base import
from cli.paths import DB_STRATEGY as CLI_DB
from utility.setting_base import DB_STRATEGY as UTIL_DB

out = {
    "expected": os.path.normcase(os.path.abspath(str(bootstrap.LOOP_DB_STRATEGY))),
    "cli_db": os.path.normcase(os.path.abspath(CLI_DB)),
    "util_db": os.path.normcase(os.path.abspath(UTIL_DB)),
    "env_db": os.environ.get("STOM_CLI_DB_STRATEGY", ""),
    "minimal": os.environ.get("STOM_ALLOW_MINIMAL_SETTING", ""),
}
print(json.dumps(out))
"""


def _run_child() -> dict:
    import json

    env = dict(os.environ)
    # 격리 검증을 위해 호출자가 미리 설정한 override는 제거한다.
    env.pop("STOM_CLI_DB_STRATEGY", None)
    env.pop("STOM_ALLOW_MINIMAL_SETTING", None)
    env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(
        [sys.executable, "-c", _CHILD_SCRIPT],
        cwd=str(PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"child failed (rc={result.returncode})\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    # 마지막 JSON 라인만 파싱 (경고 등 잡음 무시).
    last_line = [ln for ln in result.stdout.strip().splitlines() if ln.strip()][-1]
    return json.loads(last_line)


def test_bootstrap_sets_loop_db_for_cli_paths():
    """cli.paths.DB_STRATEGY 가 루프 격리 DB 를 가리킨다."""
    data = _run_child()
    assert data["cli_db"] == data["expected"]


def test_bootstrap_sets_loop_db_for_setting_base():
    """utility.setting_base.DB_STRATEGY 가 루프 격리 DB 를 가리킨다."""
    data = _run_child()
    assert data["util_db"] == data["expected"]


def test_loop_db_is_not_production_strategy_db():
    """격리 DB 는 production strategy.db 가 아니다."""
    data = _run_child()
    # 경로에 loop_strategies.db 가 포함되고 _database/strategy.db 는 아니어야 한다.
    assert "loop_strategies.db" in data["cli_db"]
    assert "loop_strategies.db" in data["util_db"]
    prod = os.path.normcase(str(PROJECT_ROOT / "_database" / "strategy.db"))
    assert data["cli_db"] != prod
    assert data["util_db"] != prod


def test_bootstrap_sets_minimal_setting_flag():
    """STOM_ALLOW_MINIMAL_SETTING 이 '1' 로 설정된다."""
    data = _run_child()
    assert data["minimal"] == "1"


def test_env_db_matches_loop_path():
    """STOM_CLI_DB_STRATEGY env 값이 루프 DB 경로다."""
    data = _run_child()
    assert os.path.normcase(os.path.abspath(data["env_db"])) == data["expected"]
