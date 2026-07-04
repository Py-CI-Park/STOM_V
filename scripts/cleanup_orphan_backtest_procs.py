"""고아 multiprocessing-fork 백테스트 자식 프로세스 정리 (T6.3).

배경(2026-06-19 진단): warm-run 부모 프로세스가 사라진 뒤에도 repo cwd 에서
``--multiprocessing-fork`` 자식 python 프로세스 104개가 잔존해 다음 warm-engine
data loading 이 멈췄다(.omo/evidence/tmap-walkforward/proxy-oos-20260619).
이 스크립트는 그 수동 정리를 자동화한다.

안전 규약(파괴적 동작 금지 — 이 파일의 계약):
  - **기본은 dry-run**: 후보 목록(pid / 명령행 요약 / 생성 시각)만 출력하고
    어떤 프로세스도 종료하지 않는다.
  - ``--kill`` 을 명시했을 때만 종료를 시도한다.
  - 대상은 '명령행에 multiprocessing 포크 마커(``--multiprocessing-fork`` 등)가
    있는 python 프로세스'로 한정한다. 다른 프로세스는 후보조차 되지 않는다.
  - 자기 자신(pid)·부모(ppid)·``--exclude-pid`` 화이트리스트는 항상 제외한다.
  - 열거는 PowerShell ``Get-CimInstance Win32_Process`` 경유(wmic 미사용).
  - 열거/종료 subprocess 호출은 주입 가능한 콜러블로 분리되어 있어 단위
    테스트는 mock 으로만 검증한다(실 프로세스 조작 없음).

연구 레인 전용 · advisory. print 미사용(sys.stdout.write / sys.stderr.write).

사용 예:
    python scripts/cleanup_orphan_backtest_procs.py                    # dry-run 목록
    python scripts/cleanup_orphan_backtest_procs.py --older-than-minutes 30
    python scripts/cleanup_orphan_backtest_procs.py --kill --report out.json

종료코드: 0=정상(dry-run 또는 전원 종료 성공), 1=일부 종료 실패, 2=입력/열거 오류.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

RECEIPT_SCHEMA = "orphan_cleanup_receipt_v1"
AUTHORITY = "advisory_only"

# 정찰 확인 마커(.omo/evidence/tmap-walkforward/proxy-oos-20260619 실측 패턴):
#   python.exe -c "from multiprocessing.spawn import spawn_main; ..." --multiprocessing-fork
# resource_tracker 는 fork 헬퍼 잔존물로 함께 남는 경우가 있어 포함한다.
FORK_MARKERS: Tuple[str, ...] = (
    "--multiprocessing-fork",
    "from multiprocessing.spawn import spawn_main",
    "from multiprocessing.resource_tracker import main",
)

_PYTHON_NAME_RE = re.compile(r"^python[\w.]*\.exe$", re.IGNORECASE)
_PS_DATE_RE = re.compile(r"/Date\((\d+)\)/")
_CMDLINE_SUMMARY_CHARS = 160

# PowerShell 열거 쿼리 — wmic 미사용. 단일 결과도 배열로 강제(@()) 직렬화.
_PS_QUERY = (
    "$ErrorActionPreference = 'Stop'; "
    "$procs = Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%'\" | "
    "Select-Object ProcessId, ParentProcessId, Name, CommandLine, "
    "@{Name='CreationDateIso';Expression={ if ($_.CreationDate) "
    "{ $_.CreationDate.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ') } else { $null } }}; "
    "if ($null -eq $procs) { '[]' } "
    "else { ConvertTo-Json -InputObject @($procs) -Compress -Depth 3 }"
)


class EnumerationError(RuntimeError):
    """프로세스 열거 실패(정직 에러 — 조용한 빈 목록 금지)."""


def default_process_query(timeout_sec: float = 30.0) -> str:
    """PowerShell Get-CimInstance 로 python 프로세스 목록 JSON 을 얻는다.

    subprocess 경계 함수 — 테스트에서는 이 콜러블 자체를 mock 으로 대체한다.
    """
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", _PS_QUERY],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EnumerationError(f"PowerShell 프로세스 열거 실패: {exc}") from exc
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()[:500]
        raise EnumerationError(f"PowerShell 종료코드 {proc.returncode}: {detail}")
    return proc.stdout or "[]"


def default_kill(pid: int, timeout_sec: float = 15.0) -> Dict[str, Any]:
    """taskkill /PID <pid> /F 로 단일 프로세스를 종료한다(/T 트리킬 미사용).

    subprocess 경계 함수 — 테스트에서는 이 콜러블 자체를 mock 으로 대체한다.
    """
    try:
        proc = subprocess.run(
            ["taskkill", "/PID", str(int(pid)), "/F"],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"pid": int(pid), "status": "error", "detail": str(exc)}
    if proc.returncode == 0:
        return {"pid": int(pid), "status": "killed", "detail": (proc.stdout or "").strip()[:200]}
    detail = (proc.stderr or proc.stdout or "").strip()[:200]
    return {"pid": int(pid), "status": "error", "detail": detail}


def parse_process_records(raw_json: str) -> List[Dict[str, Any]]:
    """PowerShell ConvertTo-Json 출력을 정규화된 레코드 리스트로 변환한다.

    단일 객체(dict)·배열·빈 문자열 모두 허용. 키는 PS 5.1/7 변형을 흡수한다.
    """
    text = (raw_json or "").strip()
    if not text:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise EnumerationError(f"프로세스 목록 JSON 파싱 실패: {exc}") from exc
    if data is None:
        return []
    items = data if isinstance(data, list) else [data]
    records = []
    for item in items:
        if not isinstance(item, dict):
            continue
        records.append({
            "pid": _to_int(item.get("ProcessId", item.get("pid"))),
            "parent_pid": _to_int(item.get("ParentProcessId", item.get("parent_pid"))),
            "name": str(item.get("Name", item.get("name")) or ""),
            "command_line": str(item.get("CommandLine", item.get("command_line")) or ""),
            "creation_date": item.get(
                "CreationDateIso", item.get("CreationDate", item.get("creation_date"))
            ),
        })
    return records


def _to_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def is_python_fork_process(
    record: Dict[str, Any], markers: Sequence[str] = FORK_MARKERS
) -> bool:
    """'python 실행파일 + 명령행에 포크 마커' 를 모두 만족할 때만 True."""
    name = (record.get("name") or "").strip()
    if not _PYTHON_NAME_RE.match(name):
        return False
    cmdline = record.get("command_line") or ""
    return any(marker in cmdline for marker in markers)


def parse_creation_date(value: Any) -> Optional[datetime]:
    """ISO('...Z'/'+09:00') 및 PS 5.1 '/Date(ms)/' 형식을 UTC datetime 으로."""
    if not value or not isinstance(value, str):
        return None
    ms_match = _PS_DATE_RE.search(value)
    if ms_match:
        return datetime.fromtimestamp(int(ms_match.group(1)) / 1000.0, tz=timezone.utc)
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def compute_age_minutes(record: Dict[str, Any], now: datetime) -> Optional[float]:
    created = parse_creation_date(record.get("creation_date"))
    if created is None:
        return None
    return max(0.0, (now - created).total_seconds() / 60.0)


def select_candidates(
    records: Sequence[Dict[str, Any]],
    *,
    now: datetime,
    markers: Sequence[str] = FORK_MARKERS,
    older_than_minutes: Optional[float] = None,
    excluded_pids: frozenset = frozenset(),
) -> List[Dict[str, Any]]:
    """정리 후보를 고른다(순수 함수 — 입력 레코드는 변형하지 않는다).

    규칙:
      - python + 포크 마커 프로세스만.
      - excluded_pids(자기/부모/화이트리스트)는 무조건 제외.
      - older_than_minutes 지정 시 그보다 오래된 프로세스만. 생성 시각을 알 수
        없는 프로세스는 **제외**한다(나이 미상 프로세스를 죽이지 않는 보수 선택).
    """
    candidates = []
    for record in records:
        pid = record.get("pid")
        if pid is None or pid in excluded_pids:
            continue
        if not is_python_fork_process(record, markers):
            continue
        age = compute_age_minutes(record, now)
        if older_than_minutes is not None and (age is None or age < older_than_minutes):
            continue
        cmdline = record.get("command_line") or ""
        candidates.append({
            "pid": pid,
            "parent_pid": record.get("parent_pid"),
            "name": record.get("name"),
            "command_line_summary": cmdline[:_CMDLINE_SUMMARY_CHARS],
            "creation_date": record.get("creation_date"),
            "age_minutes": round(age, 2) if age is not None else None,
        })
    return sorted(candidates, key=lambda c: c["pid"])


def build_receipt(
    *,
    mode: str,
    now: datetime,
    scanned_count: int,
    candidates: List[Dict[str, Any]],
    killed: List[Dict[str, Any]],
    kill_errors: List[Dict[str, Any]],
    older_than_minutes: Optional[float],
    self_pid: int,
    parent_pid: Optional[int],
    extra_excluded_pids: List[int],
    markers: Sequence[str] = FORK_MARKERS,
) -> Dict[str, Any]:
    """orphan_cleanup_receipt_v1 스키마 receipt 를 만든다(순수 함수)."""
    return {
        "schema": RECEIPT_SCHEMA,
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "authority": AUTHORITY,
        "mode": mode,
        "target_scope": "python processes whose command line contains a multiprocessing fork marker",
        "fork_markers": list(markers),
        "older_than_minutes": older_than_minutes,
        "self_pid": self_pid,
        "parent_pid": parent_pid,
        "extra_excluded_pids": sorted(extra_excluded_pids),
        "scanned_python_processes": scanned_count,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "killed": killed,
        "kill_errors": kill_errors,
    }


def format_summary_lines(receipt: Dict[str, Any]) -> List[str]:
    """사람이 읽을 stdout 요약 라인(순수 함수)."""
    lines = [
        f"[orphan-cleanup] mode={receipt['mode']} "
        f"scanned_python={receipt['scanned_python_processes']} "
        f"candidates={receipt['candidate_count']}",
    ]
    for cand in receipt["candidates"]:
        age = cand.get("age_minutes")
        age_text = f"{age:.1f}min" if isinstance(age, (int, float)) else "unknown"
        lines.append(
            f"  pid={cand['pid']} ppid={cand.get('parent_pid')} age={age_text} "
            f"created={cand.get('creation_date')} cmd={cand['command_line_summary']}"
        )
    if receipt["mode"] == "dry_run" and receipt["candidate_count"]:
        lines.append("  (dry-run — 아무것도 종료하지 않음. 종료하려면 --kill 을 명시)")
    for entry in receipt["killed"]:
        lines.append(f"  killed pid={entry['pid']}")
    for entry in receipt["kill_errors"]:
        lines.append(f"  kill-error pid={entry['pid']}: {entry.get('detail')}")
    return lines


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cleanup_orphan_backtest_procs",
        description=(
            "고아 multiprocessing-fork python 프로세스 목록(기본 dry-run)과 "
            "명시적 --kill 정리. 연구 레인 advisory 도구."
        ),
    )
    parser.add_argument("--kill", action="store_true",
                        help="후보 프로세스를 실제로 종료한다(기본은 dry-run 목록만).")
    parser.add_argument("--older-than-minutes", type=float, default=None,
                        help="이 분(minute)보다 오래된 프로세스만 대상으로 한다.")
    parser.add_argument("--exclude-pid", type=int, action="append", default=[],
                        help="추가로 보호할 pid(반복 지정 가능). 자기/부모는 항상 제외.")
    parser.add_argument("--report", type=str, default=None,
                        help="JSON receipt 를 쓸 경로(미지정 시 stdout 요약만 — 파일 쓰기 없음).")
    return parser


def main(
    argv: Optional[Sequence[str]] = None,
    *,
    process_query: Optional[Callable[[], str]] = None,
    kill_func: Optional[Callable[[int], Dict[str, Any]]] = None,
    now: Optional[datetime] = None,
    self_pid: Optional[int] = None,
    parent_pid: Optional[int] = None,
    stdout=None,
    stderr=None,
) -> int:
    """CLI 엔트리포인트. subprocess 경계(process_query/kill_func)는 주입 가능."""
    out = stdout if stdout is not None else sys.stdout
    err = stderr if stderr is not None else sys.stderr
    try:
        args = _build_parser().parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:  # argparse 오류를 종료코드 2로 정규화.
        return 2 if exc.code not in (0, None) else 0

    if args.older_than_minutes is not None and args.older_than_minutes < 0:
        err.write("[orphan-cleanup] --older-than-minutes 는 0 이상이어야 함\n")
        return 2

    query = process_query if process_query is not None else default_process_query
    kill = kill_func if kill_func is not None else default_kill
    now_utc = now if now is not None else datetime.now(timezone.utc)
    me = self_pid if self_pid is not None else os.getpid()
    parent = parent_pid if parent_pid is not None else os.getppid()

    try:
        records = parse_process_records(query())
    except EnumerationError as exc:
        err.write(f"[orphan-cleanup] 열거 실패: {exc}\n")
        return 2

    excluded = frozenset({me, parent, *args.exclude_pid} - {None})
    candidates = select_candidates(
        records,
        now=now_utc,
        older_than_minutes=args.older_than_minutes,
        excluded_pids=excluded,
    )

    killed: List[Dict[str, Any]] = []
    kill_errors: List[Dict[str, Any]] = []
    if args.kill:
        for cand in candidates:
            if cand["pid"] in excluded:  # 방어적 재확인(선별과 이중 안전장치).
                continue
            result = kill(cand["pid"])
            if result.get("status") == "killed":
                killed.append(result)
            else:
                kill_errors.append(result)

    receipt = build_receipt(
        mode="kill" if args.kill else "dry_run",
        now=now_utc,
        scanned_count=len(records),
        candidates=candidates,
        killed=killed,
        kill_errors=kill_errors,
        older_than_minutes=args.older_than_minutes,
        self_pid=me,
        parent_pid=parent,
        extra_excluded_pids=list(args.exclude_pid),
    )

    for line in format_summary_lines(receipt):
        out.write(line + "\n")

    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            json.dump(receipt, fh, ensure_ascii=False, indent=2)
        out.write(f"[orphan-cleanup] receipt: {args.report}\n")

    return 1 if kill_errors else 0


if __name__ == "__main__":
    sys.exit(main())
