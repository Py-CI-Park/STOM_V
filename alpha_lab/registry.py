"""사전등록 봉인 레지스트리 + LEGACY_NON_AUTHORITATIVE 탐색 n_trials 원장.

봉인(seal): 결정적 canonical JSON을 파일로 고정하고 sha256으로 무결성을
지킨다. 봉인 이후 내용이 다른 payload로 다시 봉인하려 하면 SealViolation
으로 거부한다 — 임계값·피처 목록·사건 정의 변경은 새 사전등록 파일
(새 n_trials)로만 가능하다.

append_trials와 LEGACY_NON_AUTHORITATIVE_SCHEMA는 별도 탐색 실행의 역사적
카운터(JSONL)만 위한 레거시 형식이다. 이는 v2 엄격 스키마·manifest issuer를
갖지 않으므로 승격 권한 원장이 될 수 없고, canonical 권한 원장에는 기록할 수
없다. canonical 권한 원장의 유일한 기입 API는
alpha_lab.discipline.ledger.append_trial_v2이다. 레거시 호출자의 ledger_path는
논리 namespace 키일 뿐이며, 출력은 고정 비권한 archive 안의 sha256 매핑 파일이다.

규율: 현재시각은 호출자가 now 인자로 주입한다(내부 datetime.now() 금지).
파일 입출력은 바이트 단위로 처리해 OS 개행 변환 없이 sha 결정성을 보장한다.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path

from alpha_lab.discipline import ledger as authority_ledger

# v1 프로그램 4태그 + 알파 랩 v2 additive 태그(V2M=채굴 리프, V2F=필터 A/B)
# + 알파 랩 v3 additive 태그(V3M=EV 채굴 리프, V3H=힐클라임 엔진 시행)
# + 알파 랩 v4 additive 태그(V4E=레짐-적응 챔피언 앙상블 엔진 시행)
# + 알파 랩 v5 additive 태그(V5C=비상관 후보 특성화 엔진 시행).
# 기존 태그 의미는 불변 — v2/v3/v4/v5 확장은 각 preregistration_v{2,3,4,5}.json
# ledger.tags 봉인값(v3: 50d3d38a — {"path":..., "tags":["V3M","V3H"]};
# v4: 87821aaa... — {"path":..., "tags":["V4E"]};
# v5: 15144e12... — {"path":..., "tags":["V5C"]}).
ALLOWED_PROGRAMS: frozenset[str] = frozenset(
    {"P1", "P2", "P3", "P5", "V2M", "V2F", "V3M", "V3H", "V4E", "V5C"}
)
# 레거시 탐색 카운터 JSONL의 비권한 스키마. v2 권한 원장 스키마와 호환되지 않는다.
LEGACY_NON_AUTHORITATIVE_SCHEMA: tuple[str, ...] = (
    "ts",
    "program",
    "batch",
    "n",
    "meta",
)
# Historical v1 counter records are confined to this non-authoritative archive.
# New preregistration contracts must use alpha_lab.discipline.ledger instead.
LEGACY_NON_AUTHORITATIVE_ARCHIVE_DIRECTORY = (
    "stom_alpha_legacy_non_authoritative_archive"
)
LEGACY_NON_AUTHORITATIVE_LEDGER_ROOT = (
    Path(tempfile.gettempdir()) / LEGACY_NON_AUTHORITATIVE_ARCHIVE_DIRECTORY
)


def _legacy_archive_ledger_path(ledger_path) -> Path:
    """Map a canonical logical path to one fixed, isolated archive file."""
    try:
        root_lexical = Path(LEGACY_NON_AUTHORITATIVE_LEDGER_ROOT).absolute()
        root_resolved = root_lexical.resolve(strict=False)
        logical_path = Path(ledger_path).absolute().resolve(strict=False)
    except OSError:
        raise ValueError(
            "LEGACY_NON_AUTHORITATIVE ledger path cannot be canonicalized"
        ) from None
    if root_lexical != root_resolved:
        raise ValueError(
            "LEGACY_NON_AUTHORITATIVE archive root must not use a symlink"
        )
    if root_lexical.exists() and not root_lexical.is_dir():
        raise ValueError(
            "LEGACY_NON_AUTHORITATIVE archive root must be a directory"
        )
    digest = hashlib.sha256(str(logical_path).encode("utf-8")).hexdigest()
    target = root_lexical / f"{digest}.jsonl"
    try:
        resolved_target = target.resolve(strict=False)
        resolved_target.relative_to(root_resolved)
    except (OSError, ValueError):
        raise ValueError(
            "LEGACY_NON_AUTHORITATIVE archive destination escapes its fixed root"
        ) from None
    if target != resolved_target:
        raise ValueError(
            "LEGACY_NON_AUTHORITATIVE archive destination must not use a symlink"
        )
    return target


def _lstat_final_component(target: Path) -> os.stat_result | None:
    """Inspect a final component without following links or reparse points."""
    try:
        named = os.lstat(target)
    except FileNotFoundError:
        return None
    except OSError as error:
        raise ValueError(
            "LEGACY_NON_AUTHORITATIVE archive destination cannot be inspected"
        ) from error
    if _is_symlink_or_reparse_point(named):
        raise ValueError(
            "LEGACY_NON_AUTHORITATIVE archive destination must not use a symlink or reparse point"
        )
    return named


def _is_symlink_or_reparse_point(st: os.stat_result) -> bool:
    """Return whether an lstat result names a link or Windows reparse point."""
    reparse_point = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    attributes = getattr(st, "st_file_attributes", 0)
    return stat.S_ISLNK(st.st_mode) or bool(attributes & reparse_point)


def _open_no_follow(target: Path, flags: int, mode: int = 0o600) -> int:
    """Open an archive file without following its final path component.

    POSIX uses O_NOFOLLOW. Windows lacks that flag, so it rejects a final
    symlink/reparse point before opening; callers must still validate the
    opened descriptor against a fresh lstat while holding the archive lock.
    """
    no_follow = getattr(os, "O_NOFOLLOW", None)
    if no_follow is not None:
        return os.open(target, flags | no_follow, mode)
    _lstat_final_component(target)
    return os.open(target, flags, mode)


def _file_identity(st: os.stat_result) -> tuple[int, int]:
    return (st.st_dev, st.st_ino)


def _authority_identity() -> tuple[int, int] | None:
    """Return the physical authority-ledger identity without following aliases."""
    canonical = Path(authority_ledger.DEFAULT_LEDGER_PATH)
    try:
        fd = _open_no_follow(canonical, os.O_RDONLY)
    except FileNotFoundError:
        return None
    except OSError as error:
        raise ValueError(
            "canonical authority ledger cannot be safely inspected"
        ) from error
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            raise ValueError("canonical authority ledger must be a regular file")
        return _file_identity(opened)
    finally:
        os.close(fd)


def _validate_open_legacy_archive_handle(fd: int, target: Path) -> None:
    """Bind an opened descriptor to the mapped path and reject physical aliases."""
    opened = os.fstat(fd)
    if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
        raise ValueError(
            "LEGACY_NON_AUTHORITATIVE archive destination must be one regular unlinked file"
        )
    try:
        named = os.lstat(target)
    except OSError as error:
        raise ValueError(
            "LEGACY_NON_AUTHORITATIVE archive destination cannot be inspected"
        ) from error
    if _is_symlink_or_reparse_point(named) or _file_identity(named) != _file_identity(opened):
        raise ValueError(
            "LEGACY_NON_AUTHORITATIVE archive destination changed or uses a symlink or reparse point"
        )
    authority_identity = _authority_identity()
    if authority_identity is not None and _file_identity(opened) == authority_identity:
        raise ValueError(
            "LEGACY_NON_AUTHORITATIVE ledger must not alias the canonical authority ledger"
        )
def _validate_expected_open_identity(
    fd: int, expected: os.stat_result | None
) -> None:
    """Reject a normal-file replacement between pre-open lstat and open."""
    if expected is not None and _file_identity(os.fstat(fd)) != _file_identity(expected):
        raise ValueError(
            "LEGACY_NON_AUTHORITATIVE archive destination changed before open"
        )




@contextmanager
def _locked_legacy_archive_handle(target: Path, flags: int):
    """Open, exclusively lock, and physically revalidate one archive descriptor."""
    expected = _lstat_final_component(target)
    try:
        fd = _open_no_follow(target, flags | os.O_CREAT | os.O_EXCL)
    except FileExistsError:
        expected = _lstat_final_component(target)
        try:
            fd = _open_no_follow(target, flags)
        except OSError as error:
            raise ValueError(
                "LEGACY_NON_AUTHORITATIVE archive destination cannot be safely opened"
            ) from error
    except OSError as error:
        raise ValueError(
            "LEGACY_NON_AUTHORITATIVE archive destination cannot be safely opened"
        ) from error
    try:
        _lock_handle(fd, exclusive=True)
        _validate_open_legacy_archive_handle(fd, target)
        _validate_expected_open_identity(fd, expected)
        yield fd
    finally:
        try:
            _unlock_handle(fd)
        finally:
            os.close(fd)


@contextmanager
def _locked_legacy_archive_reader(target: Path):
    """Open, shared-lock, and physically revalidate an existing archive descriptor."""
    expected = _lstat_final_component(target)
    try:
        fd = _open_no_follow(target, os.O_RDONLY)
    except FileNotFoundError:
        yield None
        return
    except OSError as error:
        raise ValueError(
            "LEGACY_NON_AUTHORITATIVE archive destination cannot be safely opened"
        ) from error
    try:
        _lock_handle(fd, exclusive=False)
        _validate_open_legacy_archive_handle(fd, target)
        _validate_expected_open_identity(fd, expected)
        yield fd
    finally:
        try:
            _unlock_handle(fd)
        finally:
            os.close(fd)


def _lock_handle(fd: int, *, exclusive: bool) -> None:
    """Use the archive file itself as the cross-process check-and-append lock."""
    try:
        import fcntl
    except ImportError:
        import msvcrt

        mode = msvcrt.LK_LOCK if exclusive else msvcrt.LK_RLCK
        os.lseek(fd, 0, os.SEEK_SET)
        try:
            msvcrt.locking(fd, mode, 1)
        except OSError:
            # A newly-created empty file has no byte to lock.
            os.write(fd, b"")
            msvcrt.locking(fd, mode, 1)
    else:
        fcntl.flock(fd, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)


def _unlock_handle(fd: int) -> None:
    try:
        import fcntl
    except ImportError:
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(fd, fcntl.LOCK_UN)


def _validate_legacy_archive_destination(target: Path) -> None:
    """Reject aliases before opening; descriptor validation closes this TOCTOU window."""
    if _targets_canonical_authority_ledger(target):
        raise ValueError(
            "LEGACY_NON_AUTHORITATIVE ledger must not alias the canonical authority ledger"
        )
    try:
        named = os.lstat(target)
    except FileNotFoundError:
        return
    except OSError:
        raise ValueError(
            "LEGACY_NON_AUTHORITATIVE archive destination cannot be inspected"
        ) from None
    if _is_symlink_or_reparse_point(named):
        raise ValueError(
            "LEGACY_NON_AUTHORITATIVE archive destination must not use a symlink or reparse point"
        )
    if named.st_nlink != 1:
        raise ValueError(
            "LEGACY_NON_AUTHORITATIVE archive destination must not use a hardlink"
        )


def _targets_canonical_authority_ledger(target: Path) -> bool:
    """target이 canonical 권한 원장과 같은 파일이면 True (symlink/hardlink 포함)."""
    canonical = authority_ledger.DEFAULT_LEDGER_PATH
    try:
        if target.exists() and canonical.exists() and target.samefile(canonical):
            return True
    except OSError:
        # samefile 불가 경로도 resolve 비교로 fail-closed 판정한다.
        pass
    try:
        return target.resolve(strict=False) == canonical.resolve(strict=False)
    except OSError:
        return target == canonical

class SealViolation(Exception):
    """봉인 파일 변경 시도 또는 봉인 sha 불일치."""


def canonical_json(payload: dict) -> str:
    """결정적 직렬화: 키 정렬, ensure_ascii=False, separators=(",", ": "), 끝 개행 1개."""
    body = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ": ")
    )
    return body + "\n"


def seal(payload: dict, path) -> str:
    """payload를 canonical JSON으로 path에 봉인하고 sha256 hex를 반환한다.

    파일이 이미 존재하면: 내용이 동일할 때만 sha를 반환하고(멱등),
    다르면 SealViolation을 던진다(봉인 후 변경 거부 — 기존 파일 보존).
    """
    target = Path(path)
    data = canonical_json(payload).encode("utf-8")
    if target.exists():
        existing = target.read_bytes()
        if existing != data:
            raise SealViolation(
                f"봉인 후 변경 거부: 기존 봉인과 내용이 다릅니다 — {target}"
            )
        return hashlib.sha256(existing).hexdigest()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def sha256_of(path) -> str:
    """파일 바이트 전체의 sha256 hex."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_seal(path, expected_sha: str) -> None:
    """파일 sha256이 기대값과 일치하지 않으면 SealViolation."""
    actual = sha256_of(path)
    if actual != expected_sha:
        raise SealViolation(
            f"봉인 불일치: {path} 실제 sha {actual} != 기대 sha {expected_sha}"
        )


def append_trials(
    ledger_path,
    *,
    program: str,
    batch: str,
    n: int,
    now,
    meta: dict | None = None,
) -> None:
    """LEGACY_NON_AUTHORITATIVE 탐색 카운터(JSONL)에 1줄 append한다.

    이 API와 LEGACY_NON_AUTHORITATIVE_SCHEMA는 분리된 과거 탐색 실행의
    append-only 기록 전용이며 v2 엄격 스키마·manifest issuer가 없다.
    ledger_path는 canonicalized logical namespace key이며, 실제 출력은 고정된
    비권한 archive root의 sha256 매핑 파일뿐이다. archive root·매핑 대상의
    symlink/hardlink 및 canonical 승격 권한 원장 별칭은 쓰기 전에 ValueError로
    거부한다. 열린 descriptor가 현재 매핑 path 및 canonical authority ledger와
    물리적으로 다르고 링크 수가 하나임을 재검증한 뒤, 그 descriptor만
    cross-process 잠금·flush·fsync로 append한다. program은 ALLOWED_PROGRAMS만
    허용하며 now는 호출자가 주입하는 datetime(ts = now.isoformat())다.
    """
    if program not in ALLOWED_PROGRAMS:
        raise ValueError(
            f"허용되지 않은 program: {program!r} (허용: {sorted(ALLOWED_PROGRAMS)})"
        )
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        raise ValueError(f"n은 0 이상의 int여야 합니다: {n!r}")
    target = _legacy_archive_ledger_path(ledger_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target = _legacy_archive_ledger_path(ledger_path)
    _validate_legacy_archive_destination(target)
    record = {
        "ts": now.isoformat(),
        "program": program,
        "batch": batch,
        "n": n,
        "meta": meta,
    }
    data = (
        json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ": "))
        + "\n"
    ).encode("utf-8")
    with _locked_legacy_archive_handle(target, os.O_WRONLY | os.O_APPEND) as fd:
        written = 0
        while written < len(data):
            count = os.write(fd, data[written:])
            if count <= 0:
                raise OSError("LEGACY_NON_AUTHORITATIVE archive append failed")
            written += count
        os.fsync(fd)


def total_trials(ledger_path, program: str | None = None) -> int:
    """고정 LEGACY_NON_AUTHORITATIVE archive의 n 총합을 반환한다.

    program 지정 시 해당 프로그램만 합산한다. 원장 파일이 없으면 0. 알 수 없는
    program 필터는 ValueError(오타 필터가 조용히 0을 반환해 합산을 오도하는 것을 방지).
    ledger_path는 논리 namespace key이며, 매핑 archive 대상의 alias는 읽기에도
    허용하지 않는다. 읽기도 열린 descriptor가 현재 mapping path 및 canonical
    authority ledger와 물리적으로 다르고 링크 수 하나임을 검증한 뒤 수행한다.
    """
    if program is not None and program not in ALLOWED_PROGRAMS:
        raise ValueError(
            f"허용되지 않은 program 필터: {program!r} (허용: {sorted(ALLOWED_PROGRAMS)})"
        )
    target = _legacy_archive_ledger_path(ledger_path)
    _validate_legacy_archive_destination(target)
    total = 0
    with _locked_legacy_archive_reader(target) as fd:
        if fd is None:
            return 0
        with os.fdopen(os.dup(fd), "r", encoding="utf-8") as handle:
            for raw in handle:
                line = raw.strip()
                if not line:
                    continue
                record = json.loads(line)
                if program is None or record.get("program") == program:
                    total += int(record.get("n", 0))
    return total
