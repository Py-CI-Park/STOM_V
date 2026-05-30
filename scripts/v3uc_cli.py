"""V3U / 3U_C 통합 CLI (V3U_C E2, 사이클 4 산출).

V3U lane(wt-3u) 운영과 3U_C custom 도구 호출을 단일 진입점에 묶는다. 각
subcommand는 자체 진실 도구를 subprocess로 호출하고 표준화된 exit code만 전파한다.
도구 자체는 기존 스크립트가 보유 — 본 CLI는 1-key UX 레이어다.

## subcommand 정의

| subcommand | 동작 | 호출 대상 |
|---|---|---|
| status | 양 lane HEAD + worktree + 조건식·DB·pytest 보존 표 | git + scripts/v3uc_strategy_migration scan + v3uc_db_compatibility_check scan |
| verify | V3U 통합 verifier 8 stage 실행 | scripts/verify_v3u_pyd_gui_contract.py |
| db scan | strategy + DB 호환성 동시 scan | scripts/v3uc_strategy_migration.py + scripts/v3uc_db_compatibility_check.py |
| db migrate | 조건식 + PK 마이그레이션 (--target, --confirm 필요) | scripts/v3uc_strategy_migration.py migrate + scripts/v3uc_db_compatibility_check.py --add-pk |
| test | tests/v3u + tests/v3uc 양 lane pytest 일괄 | python -m pytest |
| ingest | V3.X 흡수 파이프라인 호출 (dry-run/live) | scripts/v3uc_ingest_pipeline.py |
| gui | python stom.py 실행 (헤드리스 offscreen / live) | stom.py with optional QT_QPA_PLATFORM=offscreen |

## 사용 예

```powershell
# 상태 한눈에
python scripts/v3uc_cli.py status

# V3U 안전망 정기 점검
python scripts/v3uc_cli.py verify

# DB·조건식 보존 상태 검증
python scripts/v3uc_cli.py db scan

# V3.19 흡수 dry-run
python scripts/v3uc_cli.py ingest --version V3.19 --dry-run
```

## 설계 원칙

- V3 official source 0줄 수정 (V3U invariant 상속)
- 모든 실 작업은 기존 도구에 위임 — CLI는 디스패처 only
- exit code 전파 (0=성공, !=0=실패)
- 한글 출력 + 한글 에러 메시지
- --workspace 옵션으로 wt-3u 경로 override 가능 (기본: 호출 디렉터리)
"""
from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Sequence


# Windows cp949 콘솔에서 em-dash 등 비-cp949 문자 인코딩 실패 방지 — utf-8 재설정
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:
        pass  # reconfigure 실패는 무시 (테스트 환경 등)


THIS_FILE = Path(__file__).resolve()
SCRIPTS_DIR = THIS_FILE.parent
REPO_ROOT_3UC = SCRIPTS_DIR.parent


def _resolve_workspace(workspace: str | None) -> Path:
    """V3U 작업 워크트리(wt-3u) 절대경로 확정."""
    if workspace:
        return Path(workspace).resolve()
    # 기본: 호출 cwd가 wt-3u라고 가정
    return Path.cwd().resolve()


def _resolve_script(name: str) -> Path:
    """3U_C 스크립트 절대경로 (CLI는 wt-3uc에 묶여 있음)."""
    return SCRIPTS_DIR / name


def _run(cmd: Sequence[str], *, cwd: Path, dry: bool = False, env_extra: dict[str, str] | None = None) -> int:
    """subprocess 실행 + exit code 반환. dry-run 시 echo only."""
    pretty = " ".join(shlex.quote(c) for c in cmd)
    if dry:
        print(f"  [DRY-RUN] $ {pretty}")
        return 0
    print(f"  $ {pretty}")
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(cmd, cwd=str(cwd), env=env, check=False)
    return proc.returncode


# ------------------------- subcommand handlers -------------------------


def _cmd_status(args: argparse.Namespace) -> int:
    """양 lane HEAD + 보존 상태 표."""
    ws = _resolve_workspace(args.workspace)
    print(f"[STATUS] V3U workspace: {ws}")
    print(f"[STATUS] 3U_C tools at: {REPO_ROOT_3UC}")

    # V3U HEAD
    rc1 = _run(["git", "-C", str(ws), "log", "--oneline", "-3"], cwd=ws, dry=args.dry_run)
    print("--- 3U_C HEAD ---")
    rc2 = _run(["git", "-C", str(REPO_ROOT_3UC), "log", "--oneline", "-3"], cwd=ws, dry=args.dry_run)

    # 조건식 보존 확인 (strategy.db scan)
    strategy_db = ws / "_database" / "strategy.db"
    if strategy_db.exists():
        print("--- 조건식 보존 확인 ---")
        _run([
            sys.executable,
            str(_resolve_script("v3uc_strategy_migration.py")),
            "--db", str(strategy_db),
            "scan",
        ], cwd=ws, dry=args.dry_run)
    else:
        print(f"[STATUS] strategy.db 없음 ({strategy_db}) — scan 생략")

    return 0 if (rc1 == 0 and rc2 == 0) else 1


def _cmd_verify(args: argparse.Namespace) -> int:
    """V3U 통합 verifier 호출."""
    ws = _resolve_workspace(args.workspace)
    verifier = ws / "scripts" / "verify_v3u_pyd_gui_contract.py"
    if not verifier.exists():
        # 3U_C scripts에도 사본 존재 (carry-forward) — 보조 경로
        verifier = _resolve_script("verify_v3u_pyd_gui_contract.py")
    if not verifier.exists():
        print(f"[ERROR] verifier 스크립트 미발견: {verifier}")
        return 2
    cmd = [sys.executable, str(verifier)]
    if args.branch:
        cmd += ["--branch", args.branch]
    if args.version:
        cmd += ["--version", args.version]
    return _run(cmd, cwd=ws, dry=args.dry_run)


def _cmd_db_scan(args: argparse.Namespace) -> int:
    """strategy + DB 호환성 동시 scan."""
    ws = _resolve_workspace(args.workspace)
    db_dir = ws / "_database"
    strategy_db = db_dir / "strategy.db"
    rc_total = 0
    if strategy_db.exists():
        print("=== strategy.db scan ===")
        rc = _run([
            sys.executable, str(_resolve_script("v3uc_strategy_migration.py")),
            "--db", str(strategy_db), "scan",
        ], cwd=ws, dry=args.dry_run)
        rc_total = rc_total or rc
    else:
        print(f"[SCAN] strategy.db 없음: {strategy_db}")
    if db_dir.exists():
        print("=== DB 호환성 scan ===")
        rc = _run([
            sys.executable, str(_resolve_script("v3uc_db_compatibility_check.py")),
            "--db-dir", str(db_dir), "scan",
        ], cwd=ws, dry=args.dry_run)
        rc_total = rc_total or rc
    else:
        print(f"[SCAN] _database 디렉토리 없음: {db_dir}")
    return rc_total


def _cmd_db_migrate(args: argparse.Namespace) -> int:
    """조건식 또는 PK 마이그레이션 (--confirm 필수, 백업 검증은 각 도구가 수행)."""
    if not args.confirm and not args.dry_run:
        print("[ERROR] db migrate는 --confirm 또는 --dry-run 필요 (실수 차단)")
        return 1
    ws = _resolve_workspace(args.workspace)
    db_dir = ws / "_database"
    strategy_db = db_dir / "strategy.db"
    rc_total = 0
    if args.what in ("strategy", "all"):
        if not strategy_db.exists():
            print(f"[MIGRATE] strategy.db 없음 — skip ({strategy_db})")
        else:
            cmd = [
                sys.executable, str(_resolve_script("v3uc_strategy_migration.py")),
                "--db", str(strategy_db),
            ]
            if args.target:
                cmd += ["--target", args.target]
            cmd += ["migrate"]
            if args.dry_run:
                cmd += ["--dry-run"]
            if args.force:
                cmd += ["--force"]
            rc_total = rc_total or _run(cmd, cwd=ws, dry=False)
    if args.what in ("pk", "all"):
        if not db_dir.exists():
            print(f"[MIGRATE] _database 디렉토리 없음 — skip ({db_dir})")
        else:
            cmd = [
                sys.executable, str(_resolve_script("v3uc_db_compatibility_check.py")),
                "--db-dir", str(db_dir),
            ]
            cmd += ["--add-pk"] if not args.dry_run else ["scan"]
            rc_total = rc_total or _run(cmd, cwd=ws, dry=False)
    return rc_total


def _cmd_test(args: argparse.Namespace) -> int:
    """양 lane pytest 일괄 실행."""
    ws = _resolve_workspace(args.workspace)
    rc_total = 0
    v3u_tests = ws / "tests" / "v3u"
    v3uc_tests = REPO_ROOT_3UC / "tests" / "v3uc"
    if v3u_tests.exists():
        print("=== V3U 안전망 pytest ===")
        rc_total = rc_total or _run(
            [sys.executable, "-m", "pytest", str(v3u_tests), "-q"],
            cwd=ws, dry=args.dry_run,
        )
    else:
        print(f"[TEST] V3U tests 없음: {v3u_tests}")
    if v3uc_tests.exists():
        print("=== 3U_C 도구 pytest ===")
        rc_total = rc_total or _run(
            [sys.executable, "-m", "pytest", str(v3uc_tests), "-q"],
            cwd=REPO_ROOT_3UC, dry=args.dry_run,
        )
    else:
        print(f"[TEST] 3U_C tests 없음: {v3uc_tests}")
    return rc_total


def _cmd_ingest(args: argparse.Namespace) -> int:
    """V3.X 흡수 파이프라인 호출."""
    if not args.version:
        print("[ERROR] ingest는 --version V3.X 필요")
        return 1
    ws = _resolve_workspace(args.workspace)
    cmd = [
        sys.executable, str(_resolve_script("v3uc_ingest_pipeline.py")),
        "--version", args.version,
    ]
    if args.upstream_ref:
        cmd += ["--upstream-ref", args.upstream_ref]
    cmd += ["--dry-run"] if args.dry_run else ["--live"]
    return _run(cmd, cwd=ws, dry=False)


def _cmd_gui(args: argparse.Namespace) -> int:
    """stom.py 실행. --offscreen 시 QT_QPA_PLATFORM=offscreen 적용 (headless 점검)."""
    ws = _resolve_workspace(args.workspace)
    stom = ws / "stom.py"
    if not stom.exists():
        print(f"[ERROR] stom.py 미발견: {stom}")
        return 2
    env_extra: dict[str, str] = {}
    if args.offscreen:
        env_extra["QT_QPA_PLATFORM"] = "offscreen"
    return _run([sys.executable, str(stom)], cwd=ws, dry=args.dry_run, env_extra=env_extra)


# ------------------------- argparse -------------------------


def build_parser() -> argparse.ArgumentParser:
    """argparse 트리 구성 (테스트에서 import 가능하도록 분리).

    --workspace / --dry-run 은 parent parser로 전 subcommand 공유 — `cli --dry-run X`
    와 `cli X --dry-run` 모두 허용.
    """
    # default=SUPPRESS 로 subparser 재선언 시 부모 값을 None으로 덮어쓰지 않도록 방어
    # (parents= 사용 시 argparse 기본 default가 namespace를 reset하는 known gotcha)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--workspace", default=argparse.SUPPRESS,
        help="V3U 워크트리 경로 (기본: 현재 cwd)",
    )
    common.add_argument(
        "--dry-run", action="store_true", default=argparse.SUPPRESS,
        help="실 실행 없이 명령만 echo",
    )

    p = argparse.ArgumentParser(
        prog="v3uc_cli",
        description="V3U / 3U_C 통합 CLI — 양 lane 운영 1-key 진입점",
        parents=[common],
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", parents=[common], help="양 lane HEAD + 보존 상태 표")

    p_verify = sub.add_parser("verify", parents=[common], help="V3U 통합 verifier 호출")
    p_verify.add_argument("--branch", help="git branch (verifier 인자)")
    p_verify.add_argument("--version", help="V3 버전 라벨")

    p_db = sub.add_parser("db", parents=[common], help="DB·조건식 작업")
    p_db_sub = p_db.add_subparsers(dest="db_action", required=True)
    p_db_sub.add_parser("scan", parents=[common], help="strategy + 호환성 동시 scan")
    p_db_migrate = p_db_sub.add_parser("migrate", parents=[common], help="조건식 또는 PK 마이그레이션")
    p_db_migrate.add_argument(
        "what", choices=["strategy", "pk", "all"], help="대상 종류",
    )
    p_db_migrate.add_argument("--target", help="strategy 거래소 prefix (예: stock, coin)")
    p_db_migrate.add_argument("--confirm", action="store_true", help="실 변경 확인 (실수 차단)")
    p_db_migrate.add_argument("--force", action="store_true", help="기존 V3 데이터 덮어쓰기 허용")

    sub.add_parser("test", parents=[common], help="tests/v3u + tests/v3uc 양 lane pytest 일괄")

    p_ingest = sub.add_parser("ingest", parents=[common], help="V3.X 흡수 파이프라인 호출")
    p_ingest.add_argument("--version", required=True, help="V3 버전 (예: V3.30)")
    p_ingest.add_argument("--upstream-ref", help="upstream git ref")

    p_gui = sub.add_parser("gui", parents=[common], help="python stom.py 실행")
    p_gui.add_argument("--offscreen", action="store_true", help="QT_QPA_PLATFORM=offscreen 적용")

    return p


# ------------------------- entry -------------------------


HANDLERS = {
    ("status", None): _cmd_status,
    ("verify", None): _cmd_verify,
    ("db", "scan"): _cmd_db_scan,
    ("db", "migrate"): _cmd_db_migrate,
    ("test", None): _cmd_test,
    ("ingest", None): _cmd_ingest,
    ("gui", None): _cmd_gui,
}


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    # SUPPRESS 사용 → 미지정 시 attribute 자체가 없으므로 getattr 정규화
    if not hasattr(args, "workspace"):
        args.workspace = None
    if not hasattr(args, "dry_run"):
        args.dry_run = False
    key = (args.cmd, getattr(args, "db_action", None))
    handler = HANDLERS.get(key)
    if handler is None:
        parser.error(f"unknown subcommand routing: {key}")
        return 2  # pragma: no cover (argparse.error는 SystemExit)
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
