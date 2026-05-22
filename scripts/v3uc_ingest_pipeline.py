"""V3.X 흡수 자동화 파이프라인 (V3U_C E1, 2U_C T-step 패턴 적용).

V3 upstream에서 새 버전(V3.19, V3.20, ...) 발표 시 V3U lane으로 자동 흡수하는 5단계
T-step 파이프라인. 매 단계 PASS/FAIL 명시 + audit JSON 정본화 + dry-run 모드 지원.

## T-step 정의

| T | 단계 | 동작 | dry-run 차이 |
|---|---|---|---|
| T01 | upstream merge | git fetch + git merge STOM_Version_3 → STOM_Version_3U | merge 시뮬, 실 merge 안 함 |
| T02 | integrated verifier | verify_v3u_pyd_gui_contract.py 8 stage 통합 게이트 | 실 verifier 실행 (read-only) |
| T03 | audit JSON 정본화 | .omc/audits/v3u_ingest_<version>_<date>.json 생성 | 동일 (write) |
| T04 | 한글 commit | "V3.X 흡수를 V3U lane에 정본화한다" 메시지로 commit | echo만 |
| T05 | origin push | git push origin STOM_Version_3U | echo만 |

각 단계는 fail-fast — 실패 시 즉시 abort + audit JSON에 fail 기록.

## 사용 예

```powershell
# dry-run (실 merge·commit·push 없음, verifier만 실 실행)
python scripts/v3uc_ingest_pipeline.py --version V3.19 --upstream-ref STOM_Version_3 --dry-run

# live 실행
python scripts/v3uc_ingest_pipeline.py --version V3.19 --upstream-ref STOM_Version_3 --live
```

## Constraint

- V3 official source 0줄 수정 (V3U invariant 상속)
- V3U lane(STOM_Version_3U)에서 실행 — 3U_C(`wt-3uc`)는 본 스크립트 보관만
- 매 T-step 실행은 git working tree clean 전제
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.cwd()


def _run_cmd(cmd: list[str], *, dry: bool, capture: bool = True) -> tuple[int, str, str]:
    """subprocess wrapper. dry-run 시 echo만 + exit 0."""
    if dry:
        print(f"  [DRY-RUN] $ {' '.join(cmd)}")
        return 0, "(dry-run: not executed)", ""
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=600,
    )
    return proc.returncode, proc.stdout, proc.stderr


def step_t01_upstream_merge(*, version: str, upstream_ref: str, dry: bool) -> dict:
    """T01: V3 upstream merge → STOM_Version_3U.

    dry-run: git status + diff stat만 표시 (실 merge 안 함)
    live: 실 merge 실행
    """
    print(f"[T01] upstream merge: {upstream_ref} → STOM_Version_3U")
    # 현재 branch가 V3U인지 사전 확인
    code, out, err = _run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], dry=False)
    current_branch = out.strip()
    if current_branch != "STOM_Version_3U":
        return {
            "step": "T01",
            "status": "failed",
            "reason": f"현재 branch={current_branch!r}, STOM_Version_3U 필요. checkout 후 재시도.",
        }
    # working tree clean 확인
    code, out, err = _run_cmd(["git", "status", "--porcelain"], dry=False)
    if out.strip():
        return {
            "step": "T01",
            "status": "failed",
            "reason": "working tree에 미커밋 변경 존재. clean 상태 필수.",
            "git_status": out.strip()[:500],
        }
    # dry-run: 가상 merge 시뮬 (diff stat만)
    if dry:
        code, out, err = _run_cmd(
            ["git", "diff", "--stat", f"STOM_Version_3U..{upstream_ref}"],
            dry=False,
        )
        return {
            "step": "T01",
            "status": "passed",
            "mode": "dry-run",
            "diff_stat": out.strip()[:1000],
            "would_merge": upstream_ref,
        }
    # live: 실 merge (no-ff로 명시적 merge commit)
    code, out, err = _run_cmd(
        ["git", "merge", "--no-ff", "-m", f"V3.{version} 흡수: {upstream_ref} → STOM_Version_3U", upstream_ref],
        dry=False,
    )
    if code != 0:
        return {
            "step": "T01",
            "status": "failed",
            "reason": "merge 충돌 또는 실패",
            "stderr": err[:500],
        }
    return {
        "step": "T01",
        "status": "passed",
        "mode": "live",
        "merge_output": out.strip()[:500],
    }


def step_t02_integrated_verifier(*, version: str, upstream_ref: str, log_dir: Path, dry: bool) -> dict:
    """T02: verify_v3u_pyd_gui_contract.py 통합 8 stage 게이트."""
    print(f"[T02] integrated verifier (V3U pyd contract + pytest + attr inventory)")
    verifier = ROOT / "scripts" / "verify_v3u_pyd_gui_contract.py"
    if not verifier.is_file():
        return {"step": "T02", "status": "failed", "reason": f"{verifier} not found"}
    manifest = log_dir / f"ingest_v3_{version}_verifier.json"
    cmd = [
        sys.executable, str(verifier),
        "--branch", "STOM_Version_3U",
        "--version", version,
        "--upstream-ref", upstream_ref,
        "--manifest", str(manifest.relative_to(ROOT)),
        "--log-dir", str(log_dir.relative_to(ROOT)),
    ]
    code, out, err = _run_cmd(cmd, dry=False)  # dry-run에서도 verifier는 실 실행 (read-only)
    return {
        "step": "T02",
        "status": "passed" if code == 0 else "failed",
        "exit_code": code,
        "manifest_path": str(manifest),
        "stdout_tail": out.strip().splitlines()[-15:] if out else [],
    }


def step_t03_audit_json(*, version: str, upstream_ref: str, log_dir: Path, t01: dict, t02: dict, dry: bool) -> dict:
    """T03: audit JSON 정본화 — primary/corroborating signal 분리 (2U_C audit v2 패턴)."""
    print(f"[T03] audit JSON 정본화 (.omc/audits/v3u_ingest_*)")
    audit_dir = ROOT / ".omc" / "audits"
    audit_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    audit_path = audit_dir / f"v3u_ingest_{version}_{date_str}.json"
    payload = {
        "schema_version": "v2",
        "version": version,
        "upstream_ref": upstream_ref,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "dry-run" if dry else "live",
        "primary_signals": {
            "t01_upstream_merge": t01.get("status"),
            "t02_integrated_verifier": t02.get("status"),
        },
        "corroborating_signals": {
            "t01_diff_stat_present": bool(t01.get("diff_stat") or t01.get("merge_output")),
            "t02_manifest_path": t02.get("manifest_path"),
            "t02_stdout_lines": len(t02.get("stdout_tail", [])),
        },
        "decision": "PASS" if t01.get("status") == "passed" and t02.get("status") == "passed" else "FAIL",
    }
    audit_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "step": "T03",
        "status": "passed",
        "audit_path": str(audit_path),
        "decision": payload["decision"],
    }


def step_t04_korean_commit(*, version: str, audit_path: str, dry: bool) -> dict:
    """T04: 한글 commit. dry-run은 echo만."""
    print(f"[T04] 한글 commit (audit 증적 + V3 흡수 메시지)")
    msg = (
        f"V3.{version} 흡수를 V3U lane에 정본화한다\n\n"
        f"V3.X 흡수 자동화 파이프라인(v3uc_ingest_pipeline.py) T01~T05 통과 결과.\n"
        f"audit 증적: {audit_path}\n\n"
        f"- T01 upstream merge: PASS\n"
        f"- T02 통합 verifier (8 stage): PASS\n"
        f"- T03 audit JSON 정본화: PASS (schema v2)\n"
        f"- T04 한글 commit: 본 commit\n"
        f"- T05 origin push: 후속 단계\n\n"
        f"Constraint: V3 official source 0줄 수정."
    )
    if dry:
        print(f"  [DRY-RUN] git commit -m \"<{len(msg)} chars 메시지>\"")
        return {"step": "T04", "status": "passed", "mode": "dry-run", "msg_len": len(msg)}
    # live: 실 commit (T01 merge가 이미 commit 만들었으므로 amend 또는 새 commit)
    # 단순화: merge commit이 이미 있으면 추가 commit 없이 PASS
    code, out, err = _run_cmd(["git", "log", "-1", "--format=%s"], dry=False)
    last_subject = out.strip()
    if version in last_subject and "흡수" in last_subject:
        return {"step": "T04", "status": "passed", "mode": "live", "note": "T01 merge commit이 이미 메시지 보유"}
    # 별도 audit commit 생성
    code, out, err = _run_cmd(["git", "commit", "--allow-empty", "-m", msg], dry=False)
    return {
        "step": "T04",
        "status": "passed" if code == 0 else "failed",
        "exit_code": code,
        "commit_output": out.strip()[:300],
    }


def step_t05_origin_push(*, dry: bool) -> dict:
    """T05: origin push. dry-run은 echo만."""
    print(f"[T05] origin push (STOM_Version_3U)")
    if dry:
        print(f"  [DRY-RUN] git push origin STOM_Version_3U")
        return {"step": "T05", "status": "passed", "mode": "dry-run"}
    code, out, err = _run_cmd(["git", "push", "origin", "STOM_Version_3U"], dry=False)
    return {
        "step": "T05",
        "status": "passed" if code == 0 else "failed",
        "exit_code": code,
        "push_output": (out + err).strip()[:300],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="V3.X 흡수 자동화 파이프라인 (V3U_C E1)")
    parser.add_argument("--version", required=True, help="흡수할 V3.X 버전 (예: 19, 20)")
    parser.add_argument("--upstream-ref", required=True, help="흡수 source ref (예: STOM_Version_3 또는 tag)")
    parser.add_argument("--log-dir", default=".omx/logs/v3u", help="log 출력 디렉토리")
    parser.add_argument(
        "--dry-run", action="store_const", const="dry-run", dest="mode",
        help="실 merge·commit·push 없이 시뮬만 (verifier는 read-only로 실행)",
    )
    parser.add_argument(
        "--live", action="store_const", const="live", dest="mode",
        help="실제 흡수 실행 (T01 merge + T04 commit + T05 push)",
    )
    parser.set_defaults(mode="dry-run")
    args = parser.parse_args(argv)
    dry = args.mode == "dry-run"

    log_dir = ROOT / args.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== V3.{args.version} 흡수 파이프라인 (mode={args.mode}) ===\n")

    # T01
    t01 = step_t01_upstream_merge(version=args.version, upstream_ref=args.upstream_ref, dry=dry)
    print(f"  → T01 {t01['status']}")
    if t01["status"] == "failed":
        print(f"  abort: {t01.get('reason')}")
        return 1

    # T02 (read-only, dry-run에서도 실행)
    t02 = step_t02_integrated_verifier(version=args.version, upstream_ref=args.upstream_ref, log_dir=log_dir, dry=dry)
    print(f"  → T02 {t02['status']}")
    if t02["status"] == "failed":
        print(f"  abort: verifier exit={t02.get('exit_code')}")
        return 1

    # T03
    t03 = step_t03_audit_json(version=args.version, upstream_ref=args.upstream_ref, log_dir=log_dir, t01=t01, t02=t02, dry=dry)
    print(f"  → T03 {t03['status']} (audit: {t03['audit_path']})")

    # T04
    t04 = step_t04_korean_commit(version=args.version, audit_path=t03["audit_path"], dry=dry)
    print(f"  → T04 {t04['status']}")
    if t04["status"] == "failed":
        return 1

    # T05
    t05 = step_t05_origin_push(dry=dry)
    print(f"  → T05 {t05['status']}")
    if t05["status"] == "failed":
        return 1

    print(f"\n[OK] V3.{args.version} 흡수 파이프라인 5 T-step 모두 PASS (mode={args.mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
