"""사전등록 스켈레톤 생성기 (백로그 A1 — D1 봉인본 2026-07-12 구조 준용).

생성되는 문서는 **봉인 전 초안 골격**이다: 가설/모집단/창/표본 하한/kill/
효과크기 하한/보정(BH-FDR·일자블록 부트스트랩)/엔진 예산/§13 미결 결정의
자리를 강제해, "측정 먼저·문서 나중"이라는 위반 형태를 구조적으로 막는다.

창 검증: 스켈레톤 생성 시점에 windows.assert_measurement_window 가드를
통과해야 한다 — known 창을 측정창으로 삼은 사전등록은 초안 단계에서 거부.
2024 조건부 창은 conditional_2024=True 명시 시에만 허용된다(그 사전등록
자체가 원장 §1이 요구하는 근거 문서가 된다).

기존 문서 보호: write_skeleton은 이미 존재하는 파일을 덮어쓰지 않는다
(봉인 문화 — 사후 변경은 새 사전등록으로만).
"""

from __future__ import annotations

import contextlib
import ast
import hashlib
import json
import re
import os
import stat
from pathlib import Path, PurePosixPath
from typing import Iterator

from alpha_lab.discipline import windows
from alpha_lab.discipline.evidence import (
    EvidenceSchemaError,
    canonical_json_bytes,
    validate_prereg_seal,
)
class UnsupportedAuthorityPlatform(EvidenceSchemaError):
    """Strict authority mutation is not yet descriptor-safe on this platform."""



_FILL = "(기입)"

DEFAULT_KILL_CRITERIA: tuple[str, ...] = (
    "kill-1(주 결론): (기입 — 어떤 결과가 나오면 가설을 소거로 확정하는가)",
    "kill-2(표본 하한 미달): 자격 표본이 §5 하한 미달 → inconclusive 종결(분모 제외, kill-1 아님)",
    "kill-3(재현 게이트): 스칼라/벡터 등가 대조 미달 → 해당 경로 금지, 전 경로 미달 시 중단",
)
_CONTRACT_FENCE = re.compile(r"```json prereg-contract-v2\s*\n(?P<contract>.*?)\n```", re.DOTALL)
_CONTRACT_KEYS = {"schema_version", "hypothesis_id", "discovery_window", "primary_estimand", "sample_floors", "multiplicity_family", "kill_rule", "ledger_path", "authority_paths", "dependency_roots", "dynamic_python_dependencies", "non_python_dependencies"}


def _front_sections(params: dict) -> list[str]:
    """머리말·결론·쉬운 설명·창 지위·가설 섹션(§0~§2)."""
    window_line = f"{params['window_start']} ~ {params['window_end']}"
    return [
        f"# {params['title']} 사전등록 — 스켈레톤 (봉인 전 초안)",
        "",
        "> 지위: **측정 전 봉인 대상 초안.** 메인 세션이 §13 미결을 해소·봉인 커밋한 뒤에만 측정 착수. 사후 변경은 새 사전등록으로만.",
        f"> 정본 대조: 창-지위 원장 `{windows.LEDGER_DOC_PATH}` §1·§2 — 본 문서와 불일치하면 원장이 정본.",
        "> 구조 준용: D1 절-단위 A/B 분해 봉인본(2026-07-12) — 결론 먼저·표 중심·쉬운 설명 병기.",
        f"> 계열(series_kind): {params['series_kind']}",
        f"> 생성기: alpha_lab.discipline.prereg / 생성 시각: {params['generated_ts'] or '(미주입 — 봉인 시 기록)'}",
        "",
        "---",
        "",
        "## 0. 결론 먼저",
        "",
        f"{_FILL}: 무엇을(측정량), 어떤 표본 위에서, 어떤 판정 기준으로 검정하며, 통과/전멸 각각이 무엇을 확정하는지 1문단.",
        "",
        "## 0.5 쉬운 설명 (비유 의무)",
        "",
        f"{_FILL}: 일상 비유 1-2문장 먼저, 기술 설명은 그 뒤에(보고 규율).",
        "",
        "## 1. 창 지위 (원장 §1·§2 상속)",
        "",
        f"- 측정창: **{window_line}** — 가드 판정: **{params['window_status']}**",
        f"- known 창({windows.KNOWN_START}~{windows.KNOWN_END})은 측정 금지 — \"{windows.LEDGER_QUOTE_KNOWN}\"",
        f"- 2024 조건부 창: \"{windows.LEDGER_QUOTE_CONDITIONAL}\"",
        f"- {_FILL}: 이 계열의 창별 개봉 이력(원장 §2 행 인용)과 그 함의.",
        "",
        "## 2. 가설",
        "",
        f"- H0: {params['hypothesis_h0']}",
        f"- H1: {params['hypothesis_h1']}",
        f"- 측정량 정의: {_FILL}",
    ]


def _design_sections(params: dict) -> list[str]:
    """모집단·게이트·표본 하한·방법 섹션(§3~§6)."""
    return [
        "",
        "## 3. 모집단·대상 봉인 (효과 관측 전 봉인)",
        "",
        f"- 모집단: {params['population']}",
        f"- 대상 원문/자산 sha 봉인: {_FILL}",
        f"- 후보 수 상한(FDR 분모 상한) 봉인: {_FILL}",
        "",
        "## 4. 측정 가능성 게이트 (자기채점 차단)",
        "",
        f"- {_FILL}: 화이트리스트/패리티 게이트 — 어떤 효과도 관측하기 전에 1회 실행해 자격을 확정하고 원장에 기록, 이후 분모 변경 금지(사후 분모 확대 = 위반).",
        "",
        "## 5. 표본·라벨 — 표본 하한",
        "",
        f"- 표본 하한: {params['sample_floor']}",
        "- 하한 미달 시: inconclusive(판정 불가 지역 기록 — kill 아님, 분모 제외)",
        f"- 라벨 정의·조건부 딱지: {_FILL}",
        "",
        "## 6. 방법",
        "",
        f"- {_FILL}: read-only 접근 경로·재현 게이트(스칼라 등가 대조 등)·체크포인트 규약.",
    ]


def _control_sections(params: dict) -> list[str]:
    """판정·다중성·딱지·kill·예산·금지·미결 섹션(§7~§13)."""
    kills = [f"{i}. {text}" for i, text in enumerate(params["kill_criteria"], start=1)]
    opens = [f"{i}. {text}" for i, text in enumerate(params["open_decisions"], start=1)]
    return [
        "",
        "## 7. 판정 기준 (전 조건 동시 충족)",
        "",
        "| 기준 | 봉인 문턱 |",
        "|---|---|",
        f"| 효과크기 하한 | Δ ≥ {params['effect_floor']} |",
        f"| 다중검정 보정(BH-FDR) | q = {params['fdr_q']}, 분모 = 검정족 시행 수({_FILL}) |",
        f"| 일자블록 부트스트랩 CI | n_boot {params['n_boot']}, CI 하한 > 0 |",
        f"| 일관성 축(연도 동부호 등) | {_FILL} |",
        "",
        "## 8. 다중성·족 통제",
        "",
        f"- FDR 분모 = n_trials 원장 type-b 계상과 동일 수 — 기입은 단일 API(alpha_lab.discipline.ledger.append_trial)로만.",
        f"- 족(family) 정의·근접 중복 처리: {_FILL}",
        "",
        "## 9. 딱지 (강제 인쇄)",
        "",
        f"- {_FILL}: 시드-조건부/라벨-조건부/audit-grade 등 모든 산출물에 인쇄할 한정 문구.",
        "",
        "## 10. Kill 기준",
        "",
        *kills,
        "",
        "## 11. 엔진 예산 · n_trials",
        "",
        f"- 엔진 예산: {params['engine_budget']}",
        "- n_trials 기록: 게이트 확정 시점에 단일 기입 API로 일괄 기록, 구 프로그램 누계(1,100+) 병기(원장 §3).",
        "- 판정 문서에는 trials_report의 '시행 병기 블록'을 포함한다(A6).",
        "",
        "## 12. 이 라운드에서 하지 않는 것 (즉시 금지)",
        "",
        f"- {_FILL}: 범위 밖 측정·known 창 접촉·사후 문턱 조정 등 명시적 금지 목록.",
        "",
        "## 13. 미결 결정 (봉인 시 메인 세션이 해소·기록)",
        "",
        *opens,
        "",
        "---",
        "",
        "*본 문서는 스켈레톤이다 — §13 해소·봉인 커밋 전에는 어떤 측정도 착수하지 않는다.*",
        "",
    ]


def build_skeleton(
    *,
    title: str,
    series_kind: str,
    window_start=windows.DISCOVERY_START,
    window_end=windows.DISCOVERY_END,
    hypothesis_h0: str = _FILL,
    hypothesis_h1: str = _FILL,
    population: str = _FILL,
    sample_floor: str = "(기입 — 예: 양쪽 각 n ≥ 2,000 ∧ 연도별 각 ≥ 400)",
    effect_floor: str = "+0.10%p",
    fdr_q: str = "0.10",
    n_boot: int = 400,
    engine_budget: str = "0회",
    kill_criteria=None,
    open_decisions=None,
    conditional_2024: bool = False,
    generated_ts: str | None = None,
) -> str:
    """사전등록 스켈레톤 md 문자열을 생성한다(창-지위 가드 통과 필수).

    known 창을 측정창으로 지정하면 WindowViolation. 2024 조건부 창은
    conditional_2024=True일 때만 허용(본 초안이 근거 사전등록이 된다).
    """
    if not title.strip() or not series_kind.strip():
        raise ValueError("title과 series_kind는 비어 있을 수 없습니다")
    prereg_ref = f"본 사전등록 초안({title})" if conditional_2024 else None
    status = windows.assert_measurement_window(
        window_start, window_end, series_kind, conditional_2024_prereg=prereg_ref
    )
    params = {
        "title": title.strip(),
        "series_kind": series_kind.strip(),
        "window_start": windows.parse_date(window_start).isoformat(),
        "window_end": windows.parse_date(window_end).isoformat(),
        "window_status": status,
        "hypothesis_h0": hypothesis_h0,
        "hypothesis_h1": hypothesis_h1,
        "population": population,
        "sample_floor": sample_floor,
        "effect_floor": effect_floor,
        "fdr_q": fdr_q,
        "n_boot": n_boot,
        "engine_budget": engine_budget,
        "kill_criteria": list(kill_criteria or DEFAULT_KILL_CRITERIA),
        "open_decisions": list(open_decisions or [f"{_FILL}: 봉인 전 결정 필요 항목"]),
        "generated_ts": generated_ts,
    }
    lines = _front_sections(params) + _design_sections(params) + _control_sections(params)
    return "\n".join(lines)


def write_skeleton(path, **kwargs) -> Path:
    """스켈레톤을 파일로 저장한다 — 기존 파일 덮어쓰기 거부(봉인 문화)."""
    target = Path(path)
    if target.exists():
        raise FileExistsError(
            f"기존 문서 덮어쓰기 거부: {target} — 사후 변경은 새 사전등록으로만"
        )
    content = build_skeleton(**kwargs)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target
_AUTHORITY_PATH_KEYS = {
    "seal_dir", "promotions_dir", "catalog_dir", "target_db", "journal_dir", "backup_dir",
}
_PROTECTED_ROOT_NAMES = frozenset({"_database", "_database_v3k_shadow", "backup", "_log"})


def _has_reparse_point(root: Path, relative: PurePosixPath) -> bool:
    """Reject link/junction authority aliases even when they resolve inside root."""
    current = root
    for part in relative.parts:
        current /= part
        if not current.exists() and not current.is_symlink():
            break
        metadata = os.lstat(current)
        if current.is_symlink() or getattr(
            metadata, "st_file_attributes", 0
        ) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
            return True
    return False


def _physical_path(path: Path) -> str:
    """Return an existing path's Windows physical spelling when the OS provides one."""
    value = os.path.realpath(path)
    if os.name == "nt":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        size = kernel32.GetLongPathNameW(value, None, 0)
        if size:
            buffer = ctypes.create_unicode_buffer(size)
            if kernel32.GetLongPathNameW(value, buffer, size):
                value = buffer.value
        kernel32.CreateFileW.restype = ctypes.c_void_p
        handle = kernel32.CreateFileW(
            value, 0x80, 0x7, None, 3, 0x02000000, None
        )
        if handle not in (None, ctypes.c_void_p(-1).value):
            try:
                size = kernel32.GetFinalPathNameByHandleW(handle, None, 0, 0)
                if size:
                    buffer = ctypes.create_unicode_buffer(size + 1)
                    if kernel32.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0):
                        value = buffer.value.removeprefix("\\\\?\\")
            finally:
                kernel32.CloseHandle(handle)
    return os.path.normcase(os.path.normpath(value))


def _same_physical_file(left: Path, right: Path) -> bool:
    try:
        return left.exists() and right.exists() and os.path.samefile(left, right)
    except OSError as exc:
        raise EvidenceSchemaError("authority path physical identity cannot be verified") from exc


def _validate_physical_ancestry(
    root: Path, relative: PurePosixPath, resolved: Path, field: str
) -> None:
    """Reject existing reparse, protected, and hardlink identities before mutation."""
    protected = [
        candidate for candidate in (root / name for name in _PROTECTED_ROOT_NAMES)
        if candidate.exists()
    ]
    protected_identities = {_physical_path(candidate) for candidate in protected}
    current = root
    for part in relative.parts:
        current /= part
        if not current.exists() and not current.is_symlink():
            break
        metadata = os.lstat(current)
        if current.is_symlink() or getattr(
            metadata, "st_file_attributes", 0
        ) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
            raise EvidenceSchemaError(f"{field} must not traverse a symlink or reparse point")
        if _physical_path(current) in protected_identities or any(
            _same_physical_file(current, candidate) for candidate in protected
        ):
            raise EvidenceSchemaError(f"{field} aliases a protected physical identity")
    if resolved.exists() and resolved.is_file() and resolved.stat().st_nlink > 1:
        raise EvidenceSchemaError(f"{field} must not be a hardlink")


def revalidate_authority_paths(
    repo_root: Path | str, authority_paths: object
) -> dict[str, str]:
    """Recheck all v2 authority identities immediately before a mutation."""
    root = Path(repo_root).resolve()
    if not isinstance(authority_paths, dict) or set(authority_paths) != _AUTHORITY_PATH_KEYS:
        raise EvidenceSchemaError("authority_paths must contain exactly the six v2 authority paths")

    paths: dict[str, str] = {}
    resolved_paths: dict[str, Path] = {}
    for field in sorted(_AUTHORITY_PATH_KEYS):
        path, resolved = _repo_path(
            authority_paths[field], f"authority_paths.{field}", root
        )
        if _PROTECTED_ROOT_NAMES.intersection(
            part.casefold() for part in PurePosixPath(path).parts
        ):
            raise EvidenceSchemaError(
                f"authority_paths.{field} must not name a protected DB path"
            )
        if field == "target_db":
            if not resolved.is_file():
                raise EvidenceSchemaError(
                    "authority_paths.target_db must name an existing non-protected file"
                )
        elif resolved.exists() and not resolved.is_dir():
            raise EvidenceSchemaError(
                f"authority_paths.{field} must name a directory when it exists"
            )
        _validate_physical_ancestry(
            root, PurePosixPath(path), resolved, f"authority_paths.{field}"
        )
        paths[field], resolved_paths[field] = path, resolved

    fields = sorted(paths)
    for index, left in enumerate(fields):
        left_identity = _physical_path(resolved_paths[left])
        left_parts = tuple(part.casefold() for part in PurePosixPath(paths[left]).parts)
        for right in fields[index + 1:]:
            right_identity = _physical_path(resolved_paths[right])
            right_parts = tuple(part.casefold() for part in PurePosixPath(paths[right]).parts)
            if (
                left_parts == right_parts
                or left_parts[:len(right_parts)] == right_parts
                or right_parts[:len(left_parts)] == left_parts
                or left_identity == right_identity
                or _same_physical_file(resolved_paths[left], resolved_paths[right])
            ):
                raise EvidenceSchemaError(
                    "authority_paths destinations must be case-normalized, semantically distinct, and physically distinct"
                )
    return paths
class _WindowsAuthorityGuard:
    """Keep authority identities stable while Windows authority work is in flight."""

    def __init__(self, root: Path, authority_paths: dict[str, str], fields: tuple[str, ...]):
        self.root = root
        self.authority_paths = authority_paths
        self.fields = fields
        self._dir_fds: dict[str, int] = {}
        self._target_dir_fds: dict[str, int] = {}
        self._target_identities: dict[str, tuple[int, int]] = {}
        self._windows_handles: list[object] = []

    def _open_windows(
        self, path: Path, *, directory: bool = True, deny_writes: bool = False,
    ) -> None:
        import ctypes

        class _FileInfo(ctypes.Structure):
            _fields_ = [
                ("attributes", ctypes.c_uint32),
                ("created_low", ctypes.c_uint32),
                ("created_high", ctypes.c_uint32),
                ("accessed_low", ctypes.c_uint32),
                ("accessed_high", ctypes.c_uint32),
                ("written_low", ctypes.c_uint32),
                ("written_high", ctypes.c_uint32),
                ("volume_serial", ctypes.c_uint32),
                ("size_high", ctypes.c_uint32),
                ("size_low", ctypes.c_uint32),
                ("links", ctypes.c_uint32),
                ("index_high", ctypes.c_uint32),
                ("index_low", ctypes.c_uint32),
            ]

        kernel32 = ctypes.windll.kernel32
        kernel32.CreateFileW.restype = ctypes.c_void_p
        handle = kernel32.CreateFileW(
            str(path), 0x80000000, 0x1 if deny_writes else 0x3, None, 3, 0x02200000, None
        )
        invalid = ctypes.c_void_p(-1).value
        if handle in (None, invalid):
            raise EvidenceSchemaError(f"cannot lock authority identity: {path}")
        info = _FileInfo()
        if not kernel32.GetFileInformationByHandle(handle, ctypes.byref(info)):
            kernel32.CloseHandle(handle)
            raise EvidenceSchemaError(f"cannot inspect locked authority identity: {path}")
        if info.attributes & 0x400 or directory and not info.attributes & 0x10:
            kernel32.CloseHandle(handle)
            raise EvidenceSchemaError(f"authority path must not traverse a reparse point: {path}")
        size = kernel32.GetFinalPathNameByHandleW(handle, None, 0, 0)
        if not size:
            kernel32.CloseHandle(handle)
            raise EvidenceSchemaError(f"cannot resolve locked authority identity: {path}")
        buffer = ctypes.create_unicode_buffer(size + 1)
        if not kernel32.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0):
            kernel32.CloseHandle(handle)
            raise EvidenceSchemaError(f"cannot resolve locked authority identity: {path}")
        self._windows_handles.append(handle)
    def hold_write_denied_file(self, path: Path | str) -> None:
        """Retain a file handle that denies writes and deletes until guard release."""
        if os.name != "nt":
            raise UnsupportedAuthorityPlatform(
                "write-denying retained authority files are unsupported on POSIX"
            )
        self._open_windows(Path(path), directory=False, deny_writes=True)

    @staticmethod
    def _path_key(path: Path) -> str:
        return os.path.normcase(os.path.normpath(os.path.abspath(path)))

    def _hold_posix_parent_chain(self, parent: Path) -> int:
        try:
            relative = parent.relative_to(self.root)
        except ValueError as exc:
            raise EvidenceSchemaError(f"mutation parent must be inside repo_root: {parent}") from exc
        flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
        root_fd = os.open(self.root, flags)
        self._dir_fds[f"target:{len(self._dir_fds)}"] = root_fd
        current_fd, current_path = root_fd, self.root
        for part in relative.parts:
            try:
                metadata = os.stat(part, dir_fd=current_fd, follow_symlinks=False)
            except FileNotFoundError:
                try:
                    os.mkdir(part, dir_fd=current_fd)
                except FileExistsError:
                    pass
                try:
                    metadata = os.stat(part, dir_fd=current_fd, follow_symlinks=False)
                except FileNotFoundError as exc:
                    raise EvidenceSchemaError(
                        f"authority parent component disappeared during creation: {current_path / part}"
                    ) from exc
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
                raise EvidenceSchemaError(
                    f"authority parent component must be a non-symlink directory: {current_path / part}"
                )
            try:
                child_fd = os.open(part, flags, dir_fd=current_fd)
            except OSError as exc:
                raise EvidenceSchemaError(
                    f"cannot securely hold authority parent component: {current_path / part}"
                ) from exc
            opened = os.fstat(child_fd)
            if (opened.st_dev, opened.st_ino) != (metadata.st_dev, metadata.st_ino):
                os.close(child_fd)
                raise EvidenceSchemaError(
                    f"authority parent component identity changed: {current_path / part}"
                )
            self._dir_fds[f"target:{len(self._dir_fds)}"] = child_fd
            current_fd, current_path = child_fd, current_path / part
        return current_fd

    def _hold_windows_parent_chain(self, parent: Path) -> None:
        try:
            relative = parent.relative_to(self.root)
        except ValueError as exc:
            raise EvidenceSchemaError(f"mutation parent must be inside repo_root: {parent}") from exc
        current = self.root
        self._open_windows(current)
        for part in relative.parts:
            current /= part
            try:
                os.mkdir(current)
            except FileExistsError:
                pass
            self._open_windows(current)

    def _hold_directory(self, field: str, path: Path) -> None:
        if not path.exists():
            return
        if not path.is_dir():
            raise EvidenceSchemaError(f"authority_paths.{field} must name a directory")
        if os.name == "nt":
            self._open_windows(path)
        else:
            flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
            self._dir_fds[field] = os.open(path, flags)

    def hold_path(self, path: Path | str) -> None:
        """Hold or securely establish a target's parent without creating the target."""
        target = Path(path)
        parent = target.parent
        if os.name == "nt":
            self._hold_windows_parent_chain(parent)
            if target.exists():
                self._open_windows(target, directory=False)
            return

        parent_fd = self._hold_posix_parent_chain(parent)
        self._target_dir_fds[self._path_key(parent)] = parent_fd
        if target.exists():
            try:
                fd = os.open(
                    target.name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=parent_fd
                )
            except OSError as exc:
                raise EvidenceSchemaError(f"cannot securely hold mutation target: {target}") from exc
            try:
                metadata = os.fstat(fd)
                self._target_identities[self._path_key(target)] = (
                    metadata.st_dev, metadata.st_ino
                )
            finally:
                os.close(fd)

    def dir_fd(self, field: str) -> int:
        """Return a POSIX authority directory descriptor for open-relative mutation."""
        if os.name == "nt" or field not in self._dir_fds:
            raise EvidenceSchemaError(f"no POSIX directory handle for {field}")
        return self._dir_fds[field]

    def open_relative(self, field: str, name: str, flags: int, mode: int = 0o666) -> int:
        """Open one basename beneath a held POSIX authority directory."""
        if Path(name).name != name:
            raise EvidenceSchemaError("authority-relative mutation must use a basename")
        return os.open(name, flags | getattr(os, "O_NOFOLLOW", 0), mode,
                       dir_fd=self.dir_fd(field))
    def _open_windows_path(self, target: Path, flags: int, mode: int) -> int:
        """Open a final authority file by handle and validate it before exposing a CRT fd."""
        import ctypes
        import msvcrt

        class _FileInfo(ctypes.Structure):
            _fields_ = [
                ("attributes", ctypes.c_uint32),
                ("created_low", ctypes.c_uint32),
                ("created_high", ctypes.c_uint32),
                ("accessed_low", ctypes.c_uint32),
                ("accessed_high", ctypes.c_uint32),
                ("written_low", ctypes.c_uint32),
                ("written_high", ctypes.c_uint32),
                ("volume_serial", ctypes.c_uint32),
                ("size_high", ctypes.c_uint32),
                ("size_low", ctypes.c_uint32),
                ("links", ctypes.c_uint32),
                ("index_high", ctypes.c_uint32),
                ("index_low", ctypes.c_uint32),
            ]

        kernel32 = ctypes.windll.kernel32
        kernel32.CreateFileW.restype = ctypes.c_void_p
        access = 0x80000000
        if flags & (os.O_WRONLY | os.O_RDWR):
            access |= 0x40000000
        if flags & os.O_CREAT and flags & os.O_EXCL:
            disposition = 1  # CREATE_NEW
        elif flags & os.O_CREAT:
            disposition = 4  # OPEN_ALWAYS
        else:
            disposition = 3  # OPEN_EXISTING
        handle = kernel32.CreateFileW(
            str(target), access, 0x3, None, disposition, 0x00200080, None
        )
        invalid = ctypes.c_void_p(-1).value
        if handle in (None, invalid):
            error = kernel32.GetLastError()
            if error in (2, 3):
                raise FileNotFoundError(target)
            if error in (80, 183) and flags & os.O_CREAT and flags & os.O_EXCL:
                raise FileExistsError(target)
            raise EvidenceSchemaError(f"cannot securely open authority mutation target: {target}")
        try:
            info = _FileInfo()
            if not kernel32.GetFileInformationByHandle(handle, ctypes.byref(info)):
                raise EvidenceSchemaError(f"cannot inspect authority mutation target: {target}")
            if kernel32.GetFileType(handle) != 1 or info.attributes & 0x410 or info.links != 1:
                raise EvidenceSchemaError(
                    f"authority mutation target must be a regular non-reparse non-hardlinked file: {target}"
                )
            size = kernel32.GetFinalPathNameByHandleW(handle, None, 0, 0)
            if not size:
                raise EvidenceSchemaError(f"cannot resolve authority mutation target: {target}")
            buffer = ctypes.create_unicode_buffer(size + 1)
            if not kernel32.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0):
                raise EvidenceSchemaError(f"cannot resolve authority mutation target: {target}")
            final_path = os.path.normcase(os.path.normpath(buffer.value.removeprefix("\\\\?\\")))
            root_path = _physical_path(self.root)
            try:
                if os.path.commonpath((final_path, root_path)) != root_path:
                    raise EvidenceSchemaError("authority mutation target resolves outside repo_root")
            except ValueError as exc:
                raise EvidenceSchemaError("authority mutation target identity cannot be compared") from exc
            _validate_physical_ancestry(
                self.root,
                PurePosixPath(target.relative_to(self.root).as_posix()),
                target,
                "mutation target",
            )
            crt_flags = flags & (os.O_APPEND | os.O_WRONLY | os.O_RDWR)
            crt_flags |= getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0)
            try:
                return msvcrt.open_osfhandle(handle, crt_flags)
            except OSError as exc:
                raise EvidenceSchemaError(
                    f"cannot convert authority mutation handle to CRT fd: {target}"
                ) from exc
        except Exception:
            kernel32.CloseHandle(handle)
            raise

    def open_path(self, path: Path | str, flags: int, mode: int = 0o666) -> int:
        """Open one target beneath a held parent, with no pathname reopen after validation."""
        target = Path(path)
        if os.name == "nt":
            return self._open_windows_path(target, flags, mode)
        key = self._path_key(target.parent)
        if key not in self._target_dir_fds:
            raise EvidenceSchemaError(f"no held POSIX parent for {target}")
        fd = os.open(target.name, flags | getattr(os, "O_NOFOLLOW", 0), mode,
                     dir_fd=self._target_dir_fds[key])
        expected = self._target_identities.get(self._path_key(target))
        if expected is not None:
            metadata = os.fstat(fd)
            if (metadata.st_dev, metadata.st_ino) != expected:
                os.close(fd)
                raise EvidenceSchemaError(f"opened mutation target identity changed: {target}")
        return fd


    def validate_file(self, path: Path | str) -> None:
        """Reject a target that no longer has the identity held by this guard."""
        target = Path(path)
        if target.exists():
            _validate_physical_ancestry(
                self.root, PurePosixPath(target.relative_to(self.root).as_posix()),
                target.resolve(), "mutation target",
            )
        revalidate_authority_paths(self.root, self.authority_paths)

    def close(self) -> None:
        for fd in self._dir_fds.values():
            os.close(fd)
        self._dir_fds.clear()
        self._target_dir_fds.clear()
        self._target_identities.clear()
        if os.name == "nt":
            import ctypes
            for handle in self._windows_handles:
                ctypes.windll.kernel32.CloseHandle(handle)
        self._windows_handles.clear()


@contextlib.contextmanager
def authority_mutation_guard(
    repo_root: Path | str, authority_paths: object, fields: tuple[str, ...] | None = None,
) -> Iterator[_WindowsAuthorityGuard]:
    """Lock and revalidate canonical authority identities across a mutation window."""
    root = Path(repo_root).resolve()
    if os.name != "nt":
        raise UnsupportedAuthorityPlatform(
            "strict authority mutation is unsupported on POSIX until every operation is descriptor-relative"
        )
    paths = revalidate_authority_paths(root, authority_paths)
    selected = tuple(sorted(paths) if fields is None else fields)
    if not selected or any(field not in paths for field in selected):
        raise EvidenceSchemaError("authority mutation fields must be non-empty authority path keys")
    guard = _WindowsAuthorityGuard(root, paths, selected)
    try:
        for field in selected:
            target = root / Path(*PurePosixPath(paths[field]).parts)
            guard._hold_directory(field, target.parent if field == "target_db" else target)
            if field == "target_db":
                guard.hold_path(target)
        revalidate_authority_paths(root, paths)
        yield guard
        revalidate_authority_paths(root, paths)
    finally:
        guard.close()


def recheck_authority_paths(value: object, root: Path | str) -> dict[str, str]:
    """Compatibility alias for callers not yet migrated to the v2 helper."""
    return revalidate_authority_paths(root, value)


def _contract_authority_paths(value: object, root: Path) -> dict[str, str]:
    """Validate the contract's six authority paths."""
    return revalidate_authority_paths(root, value)


def _repo_path(value: object, field: str, root: Path) -> tuple[str, Path]:
    if not isinstance(value, str) or not value or "\\" in value or any(
        part in ("", ".", "..") for part in value.split("/")
    ):
        raise EvidenceSchemaError(f"{field} must be a non-empty repository-relative POSIX path")
    path = PurePosixPath(value)
    if path.is_absolute():
        raise EvidenceSchemaError(f"{field} must be a safe repository-relative POSIX path")
    try:
        resolved = (root / Path(*path.parts)).resolve()
    except (OSError, RuntimeError) as exc:
        raise EvidenceSchemaError(f"{field} cannot safely resolve") from exc
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise EvidenceSchemaError(f"{field} resolves outside repo_root") from exc
    return path.as_posix(), resolved
def _contract_repo_path(value: object, field: str, root: Path) -> str:
    if not isinstance(value, str) or not value or "\\" in value or any(part in ("", ".", "..") for part in value.split("/")):
        raise EvidenceSchemaError(f"{field} must be a non-empty repository-relative POSIX path")
    path = PurePosixPath(value)
    resolved = (root / Path(*path.parts)).resolve()
    if path.is_absolute() or not resolved.is_file():
        raise EvidenceSchemaError(f"{field} must name an existing repository file")
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise EvidenceSchemaError(f"{field} resolves outside repo_root") from exc
    return path.as_posix()


def _parse_contract(text: str, root: Path) -> dict:
    matches = _CONTRACT_FENCE.findall(text)
    if len(matches) != 1:
        raise EvidenceSchemaError("preregistration requires exactly one prereg-contract-v2 JSON fence")
    try:
        contract = json.loads(matches[0])
    except json.JSONDecodeError as exc:
        raise EvidenceSchemaError("prereg-contract-v2 must contain valid JSON") from exc
    if not isinstance(contract, dict) or set(contract) != _CONTRACT_KEYS or contract["schema_version"] != 2:
        raise EvidenceSchemaError("prereg-contract-v2 has invalid keys or schema_version")
    for field in ("hypothesis_id", "primary_estimand", "multiplicity_family", "kill_rule"):
        if not isinstance(contract[field], str) or not contract[field].strip():
            raise EvidenceSchemaError(f"{field} must be a non-empty string")
    window = contract["discovery_window"]
    if not isinstance(window, dict) or set(window) != {"start", "end"}:
        raise EvidenceSchemaError("discovery_window must contain exactly start and end")
    try:
        windows.assert_measurement_window(window["start"], window["end"], "prereg contract")
    except (TypeError, ValueError, windows.WindowViolation) as exc:
        raise EvidenceSchemaError(f"invalid discovery_window: {exc}") from exc
    ledger_path = _contract_ledger_path(contract["ledger_path"], root)
    contract["ledger_path"] = ledger_path
    contract["authority_paths"] = _contract_authority_paths(contract["authority_paths"], root)
    floors = contract["sample_floors"]
    if not isinstance(floors, dict) or not floors or any(not isinstance(name, str) or not name.strip() or not isinstance(floor, int) or isinstance(floor, bool) or floor <= 0 for name, floor in floors.items()):
        raise EvidenceSchemaError("sample_floors must be a non-empty object of positive integer floors")
    roots, dynamic_dependencies, dependencies = (
        contract["dependency_roots"],
        contract["dynamic_python_dependencies"],
        contract["non_python_dependencies"],
    )
    if not isinstance(roots, list) or not roots or not isinstance(dynamic_dependencies, list) or not isinstance(dependencies, list):
        raise EvidenceSchemaError("dependency_roots must be non-empty and dynamic_python_dependencies/non_python_dependencies must be lists")
    root_paths = [_contract_repo_path(item, f"dependency_roots[{index}]", root) for index, item in enumerate(roots)]
    dynamic_paths = [_contract_repo_path(item, f"dynamic_python_dependencies[{index}]", root) for index, item in enumerate(dynamic_dependencies)]
    dependency_paths = [_contract_repo_path(item, f"non_python_dependencies[{index}]", root) for index, item in enumerate(dependencies)]
    if (
        any(not item.endswith(".py") for item in root_paths)
        or any(not item.endswith(".py") for item in dynamic_paths)
        or any(item.endswith(".py") for item in dependency_paths)
    ):
        raise EvidenceSchemaError("dependency_roots and dynamic_python_dependencies must be Python; non_python_dependencies must not be Python")
    for paths in (root_paths, dynamic_paths, dependency_paths):
        if paths != sorted(paths) or len(set(paths)) != len(paths):
            raise EvidenceSchemaError("declared dependency paths must be sorted and unique")
    return contract
def _contract_ledger_path(value: object, root: Path) -> str:
    if not isinstance(value, str) or not value or "\\" in value or any(
        part in ("", ".", "..") for part in value.split("/")
    ):
        raise EvidenceSchemaError("ledger_path must be a non-empty repository-relative POSIX path")
    path = PurePosixPath(value)
    if path.is_absolute() or not path.as_posix().endswith(".jsonl"):
        raise EvidenceSchemaError("ledger_path must be a repository-relative .jsonl path")
    if _PROTECTED_ROOT_NAMES.intersection(part.casefold() for part in path.parts):
        raise EvidenceSchemaError("ledger_path must not name a protected path")
    resolved = (root / Path(*path.parts)).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise EvidenceSchemaError("ledger_path resolves outside repo_root") from exc
    if resolved.exists() and not resolved.is_file():
        raise EvidenceSchemaError("ledger_path must not name a directory")
    _validate_physical_ancestry(root, path, resolved, "ledger_path")
    return path.as_posix()




def _module_file(root: Path, module: str) -> Path | None:
    if not module:
        return None
    base = root.joinpath(*module.split("."))
    for candidate in (base.with_suffix(".py"), base / "__init__.py"):
        if candidate.is_file():
            return candidate.resolve()
    return None


def _package_initializers(path: Path, root: Path) -> set[Path]:
    """Return every local package initializer executed before *path* is imported."""
    initializers: set[Path] = set()
    parent = path.parent
    while parent != root:
        initializer = parent / "__init__.py"
        if initializer.is_file():
            initializers.add(initializer.resolve())
        parent = parent.parent
    return initializers


def _reject_wildcard_imports(tree: ast.AST, path: Path) -> None:
    """Reject wildcard imports before they can overwrite trusted bindings."""
    if any(
        isinstance(node, ast.ImportFrom)
        and any(alias.name == "*" for alias in node.names)
        for node in ast.walk(tree)
    ):
        raise EvidenceSchemaError(f"wildcard import is unsupported: {path}")
_SAFE_STATIC_CALL_EFFECTS = {
    # Pure numerical reductions explicitly needed by sealed measurement code.
    "numpy.mean": "pure",
    # Dynamic imports are safe only because _dynamic_local_dependencies below
    # requires a literal local target and adds that target to the manifest.
    "__import__": "tracked_dynamic",
    "builtins.__import__": "tracked_dynamic",
    "importlib.import_module": "tracked_dynamic",
    "importlib.util.spec_from_file_location": "tracked_dynamic",
    "importlib.machinery.SourceFileLoader": "tracked_dynamic",
    "importlib.machinery.SourcelessFileLoader": "tracked_dynamic",
}


def _reviewed_static_call(receiver: str | None) -> bool:
    """Return whether a static-module callable has a reviewed safe effect."""
    return receiver in _SAFE_STATIC_CALL_EFFECTS


def _direct_function_api_names(tree: ast.Module) -> set[str]:
    """Return only top-level functions with one unambiguous final binding."""

    class _Bindings(ast.NodeVisitor):
        def __init__(self) -> None:
            self.events: dict[str, list[str]] = {}

        def _record(self, names: set[str], kind: str) -> None:
            for name in names:
                self.events.setdefault(name, []).append(kind)

        def visit_Import(self, node: ast.Import) -> None:
            self._record({alias.asname or alias.name.split(".", 1)[0] for alias in node.names}, "other")

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            self._record({alias.asname or alias.name for alias in node.names}, "other")

        def visit_Assign(self, node: ast.Assign) -> None:
            self._record(set().union(*(_bound_names(target) for target in node.targets)), "other")
            self.generic_visit(node.value)

        def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
            self._record(_bound_names(node.target), "other")
            if node.value is not None:
                self.visit(node.value)

        def visit_AugAssign(self, node: ast.AugAssign) -> None:
            self._record(_bound_names(node.target), "other")

        def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
            self._record(_bound_names(node.target), "other")
            self.visit(node.value)
        def visit_Delete(self, node: ast.Delete) -> None:
            for target in node.targets:
                self._record(_bound_names(target), "other")

        def visit_For(self, node: ast.For) -> None:
            self._record(_bound_names(node.target), "other")
            self.generic_visit(node)

        visit_AsyncFor = visit_For

        def visit_With(self, node: ast.With) -> None:
            for item in node.items:
                if item.optional_vars is not None:
                    self._record(_bound_names(item.optional_vars), "other")
            self.generic_visit(node)

        visit_AsyncWith = visit_With

        def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
            if node.name:
                self._record({node.name}, "other")
            self.generic_visit(node)
        def visit_Match(self, node: ast.Match) -> None:
            for case in node.cases:
                self._record(_pattern_bound_names(case.pattern), "other")
            self.generic_visit(node)


        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._record({node.name}, "other")

        visit_AsyncFunctionDef = visit_FunctionDef
        visit_ClassDef = visit_FunctionDef

        def visit_Lambda(self, node: ast.Lambda) -> None:
            return

    bindings = _Bindings()
    for statement in tree.body:
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)) and not statement.decorator_list:
            bindings._record({statement.name}, "function")
        else:
            bindings.visit(statement)
    return {
        name for name, events in bindings.events.items()
        if events == ["function"]
    }


def _declared_local_module_apis(module_path: Path) -> set[str]:
    """Return direct function APIs declared by a local module, never re-exports."""
    try:
        tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        raise EvidenceSchemaError(
            f"cannot inspect local module API: {module_path}"
        ) from exc
    _reject_sealed_store_mutation(tree, module_path)
    _, aliases = _dynamic_call_kinds(tree)
    _reject_sealed_global_mutation(tree, aliases, module_path)
    _reject_namespace_export_mutation(tree, aliases, module_path)
    return _direct_function_api_names(tree)


def _dynamic_call_kinds(tree: ast.AST) -> tuple[dict[str, str], dict[str, str]]:
    """Resolve supported literal dynamic execution APIs and reject unknown variants."""
    kinds = {
        "__import__": "module",
        "builtins.__import__": "module",
        "importlib.import_module": "module",
        "importlib.util.spec_from_file_location": "file",
        "importlib.machinery.SourceFileLoader": "file",
        "importlib.machinery.SourcelessFileLoader": "file",
        "runpy.run_module": "module",
        "runpy.run_path": "file_first",
    }
    aliases: dict[str, str] = {}
    calls = {"__import__": "module"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound = alias.asname or alias.name.split(".", 1)[0]
                aliases[bound] = alias.name if alias.asname else bound
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                canonical = f"{node.module}.{alias.name}"
                aliases[alias.asname or alias.name] = canonical
                if canonical in kinds:
                    calls[alias.asname or alias.name] = kinds[canonical]
        elif isinstance(node, ast.Assign):
            canonical = _dotted_name(node.value, aliases)
            if canonical:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        aliases[target.id] = canonical
                        if canonical in kinds:
                            calls[target.id] = kinds[canonical]
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "getattr" and node.args:
            base = _dotted_name(node.args[0], aliases)
            if base and (base.startswith("importlib") or base in {"builtins", "runpy"}):
                raise EvidenceSchemaError("dynamic import/load through getattr is unsupported")
    for name, canonical in aliases.items():
        if canonical in kinds:
            calls[name] = kinds[canonical]
        for canonical_name, kind in kinds.items():
            if canonical_name.startswith(f"{canonical}."):
                calls[f"{name}{canonical_name[len(canonical):]}"] = kind
    return calls, aliases


def _dotted_name(node: ast.AST, aliases: dict[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value, aliases)
        return f"{parent}.{node.attr}" if parent else None
    return None
def _bound_names(target: ast.AST) -> set[str]:
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        return set().union(*(_bound_names(item) for item in target.elts))
    if isinstance(target, ast.Starred):
        return _bound_names(target.value)
    return set()
def _pattern_bound_names(pattern: ast.pattern) -> set[str]:
    if isinstance(pattern, ast.MatchAs):
        return _pattern_bound_names(pattern.pattern) | ({pattern.name} if pattern.name else set())
    if isinstance(pattern, ast.MatchStar):
        return {pattern.name} if pattern.name else set()
    if isinstance(pattern, ast.MatchMapping):
        return set().union(*(_pattern_bound_names(item) for item in pattern.patterns)) | (
            {pattern.rest} if pattern.rest else set()
        )
    if isinstance(pattern, ast.MatchClass):
        return set().union(
            *(_pattern_bound_names(item) for item in (*pattern.patterns, *pattern.kwd_patterns))
        )
    if isinstance(pattern, ast.MatchSequence):
        return set().union(*(_pattern_bound_names(item) for item in pattern.patterns))
    if isinstance(pattern, ast.MatchOr):
        return set().union(*(_pattern_bound_names(item) for item in pattern.patterns))
    return set()



def _assignment_receiver(node: ast.AST, aliases: dict[str, str]) -> str | None:
    """Return the affected receiver path for an attribute or container mutation."""
    if isinstance(node, ast.Attribute):
        return _dotted_name(node, aliases)
    if isinstance(node, ast.Subscript):
        return _assignment_receiver(node.value, aliases)
    return None
def _reject_namespace_export_mutation(
    tree: ast.AST, aliases: dict[str, str], path: Path
) -> None:
    """Reject writes through runtime module namespace carriers."""
    namespace_functions = {
        "globals", "locals", "vars",
        "builtins.globals", "builtins.locals", "builtins.vars",
    }
    namespace_names: set[str] = set()

    def _is_imported_module(node: ast.AST) -> bool:
        while isinstance(node, ast.Attribute):
            node = node.value
        return isinstance(node, ast.Name) and node.id in aliases

    def _is_namespace(node: ast.AST) -> bool:
        if isinstance(node, ast.Name):
            return node.id in namespace_names
        if isinstance(node, ast.Attribute) and node.attr == "__dict__":
            return _is_namespace(node.value) or _is_imported_module(node.value)
        if isinstance(node, ast.Subscript):
            base = _dotted_name(node.value, aliases)
            return base == "sys.modules" or _is_namespace(node.value)
        if isinstance(node, ast.Call):
            return (
                _dotted_name(node.func, aliases) in namespace_functions
                or isinstance(node.func, ast.Name) and node.func.id in namespace_helpers
            )
        return False

    namespace_helpers = {
        statement.name
        for statement in tree.body
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not statement.decorator_list
        and len(statement.body) == 1
        and isinstance(statement.body[0], ast.Return)
        and statement.body[0].value is not None
        and _is_namespace(statement.body[0].value)
    }
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
                targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
                if _is_namespace(node.value):
                    names = set().union(*(_bound_names(target) for target in targets))
                    if not names.issubset(namespace_names):
                        namespace_names.update(names)
                        changed = True

    def _is_namespace_store(target: ast.AST) -> bool:
        return (
            _is_namespace(target)
            or isinstance(target, ast.Subscript) and _is_namespace(target.value)
            or isinstance(target, ast.Attribute) and _is_namespace(target.value)
        )

    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Delete)):
            targets = (
                node.targets if isinstance(node, (ast.Assign, ast.Delete)) else (node.target,)
            )
            if any(_is_namespace_store(target) for target in targets):
                raise EvidenceSchemaError(
                    f"module namespace export mutation is unsupported: {path}"
                )
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"__setitem__", "update", "setdefault"}
            and _is_namespace(node.func.value)
        ):
            raise EvidenceSchemaError(
                f"module namespace export mutation is unsupported: {path}"
            )
def _reject_sealed_store_mutation(tree: ast.AST, path: Path) -> None:
    """Reject every SEALED AST mutation target before provenance analysis."""
    for node in ast.walk(tree):
        if isinstance(node, ast.AugAssign) or (
            isinstance(node, (ast.Attribute, ast.Subscript))
            and isinstance(node.ctx, (ast.Store, ast.Del))
        ):
            raise EvidenceSchemaError(
                f"sealed mutation (function-body object mutation or module-level object mutation) is unsupported: {path}"
            )


def _reject_sealed_global_mutation(
    tree: ast.AST, aliases: dict[str, str], path: Path
) -> None:
    """Keep SEALED code pure: no export, namespace, or object/container mutation.

    Later checks cover mutation carriers and method sinks.
    """
    _reject_sealed_store_mutation(tree, path)

    mutating_method_names = frozenset({
        "__delattr__", "__delitem__", "__iadd__", "__ior__", "__isub__",
        "__setattr__", "__setitem__", "add", "append", "clear",
        "difference_update", "discard", "extend", "insert",
        "intersection_update", "pop", "popitem", "remove", "reverse",
        "setdefault", "sort", "symmetric_difference_update", "update",
    })

    for node in ast.walk(tree):
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            raise EvidenceSchemaError(
                f"global or nonlocal declaration is unsupported in sealed code: {path}"
            )

    def _is_builtins_namespace(node: ast.AST) -> bool:
        if isinstance(node, ast.Name):
            return _dotted_name(node, aliases) in {"builtins", "__builtins__"}
        if isinstance(node, (ast.Attribute, ast.Subscript)):
            return _is_builtins_namespace(node.value)
        return False

    def _is_store(target: ast.AST) -> bool:
        return isinstance(target, (ast.Attribute, ast.Subscript))

    class _FunctionBodyMutation(ast.NodeVisitor):
        """Reject every unproven object or container mutation in a function."""

        def _reject_targets(self, targets: tuple[ast.AST, ...]) -> None:
            if any(_is_store(target) for target in targets):
                raise EvidenceSchemaError(
                    f"function-body object mutation is unsupported in sealed code: {path}"
                )

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.generic_visit(node)

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Lambda(self, node: ast.Lambda) -> None:
            self.generic_visit(node)

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self.generic_visit(node)

        def visit_Assign(self, node: ast.Assign) -> None:
            self._reject_targets(tuple(node.targets))
            self.generic_visit(node)

        def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
            self._reject_targets((node.target,))
            self.generic_visit(node)

        def visit_AugAssign(self, node: ast.AugAssign) -> None:
            self._reject_targets((node.target,))
            self.generic_visit(node)

        def visit_Delete(self, node: ast.Delete) -> None:
            self._reject_targets(tuple(node.targets))
            self.generic_visit(node)

        def visit_Call(self, node: ast.Call) -> None:
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr in mutating_method_names
            ):
                raise EvidenceSchemaError(
                    f"function-body mutating method is unsupported in sealed code: {path}"
                )
            self.generic_visit(node)

    class _ModuleScopeStores(ast.NodeVisitor):
        """Reject import-time object writes without receiver provenance inference."""

        def _reject_targets(self, targets: tuple[ast.AST, ...]) -> None:
            if any(_is_store(target) for target in targets):
                raise EvidenceSchemaError(
                    f"module-level object mutation is unsupported: {path}"
                )

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            _FunctionBodyMutation().visit(node)

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Lambda(self, node: ast.Lambda) -> None:
            self.generic_visit(node)

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self.generic_visit(node)

        def visit_Assign(self, node: ast.Assign) -> None:
            self._reject_targets(tuple(node.targets))
            self.generic_visit(node)

        def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
            self._reject_targets((node.target,))
            self.generic_visit(node)

        def visit_AugAssign(self, node: ast.AugAssign) -> None:
            self._reject_targets((node.target,))
            self.generic_visit(node)

        def visit_Delete(self, node: ast.Delete) -> None:
            self._reject_targets(tuple(node.targets))
            self.generic_visit(node)

    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Delete)):
            targets = (
                node.targets if isinstance(node, (ast.Assign, ast.Delete)) else (node.target,)
            )
            if any(_is_builtins_namespace(target) for target in targets):
                raise EvidenceSchemaError(
                    f"builtins namespace mutation is unsupported: {path}"
                )
        elif isinstance(node, ast.Call):
            raw = _dotted_name(node.func, {})
            canonical = _dotted_name(node.func, aliases)
            if raw in {"setattr", "delattr"} or canonical in {
                "setattr", "delattr", "builtins.setattr", "builtins.delattr",
            }:
                raise EvidenceSchemaError(
                    f"dynamic attribute mutation is unsupported: {path}"
                )
    _ModuleScopeStores().visit(tree)






def _local_importfrom_receivers(
    tree: ast.AST, path: Path, root: Path
) -> tuple[set[str], set[str]]:
    """Return module and direct-symbol bindings from repository-local imports."""
    package = list(path.relative_to(root).parent.parts)
    module_receivers: set[str] = set()
    symbol_receivers: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.level and node.level > len(package) + 1:
            raise EvidenceSchemaError(f"relative import escapes repo package: {path}")
        prefix = package[:len(package) - node.level + 1] if node.level else []
        base = prefix + (node.module.split(".") if node.module else [])
        module = ".".join(base)
        if _module_file(root, module) is None:
            continue
        for alias in node.names:
            imported = ".".join((*base, alias.name))
            bound = alias.asname or alias.name
            if _module_file(root, imported) is not None:
                module_receivers.add(bound)
            else:
                symbol_receivers.add(bound)
    return module_receivers, symbol_receivers


def _reject_unresolved_module_receivers(
    tree: ast.AST, aliases: dict[str, str], path: Path, root: Path
) -> None:
    """Reject receiver calls that cross a local sealed module's declared API."""

    class _Bindings(ast.NodeVisitor):
        """Collect bindings without treating nested executable scopes as local."""

        def __init__(self) -> None:
            self.events: dict[str, list[tuple[str, ast.AST | None]]] = {}

        def _record(self, names: set[str], kind: str, value: ast.AST | None = None) -> None:
            for name in names:
                self.events.setdefault(name, []).append((kind, value))

        def visit_Import(self, node: ast.Import) -> None:
            for alias in node.names:
                self._record({alias.asname or alias.name.split(".", 1)[0]}, "import")

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            for alias in node.names:
                self._record({alias.asname or alias.name}, "import")

        def visit_Assign(self, node: ast.Assign) -> None:
            names = set().union(*(_bound_names(target) for target in node.targets))
            self._record(names, "alias", node.value)
            self.visit(node.value)

        def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
            self._record(
                _bound_names(node.target), "alias" if node.value is not None else "unsafe", node.value
            )
            if node.value is not None:
                self.visit(node.value)

        def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
            self._record(_bound_names(node.target), "alias", node.value)
            self.visit(node.value)

        def visit_AugAssign(self, node: ast.AugAssign) -> None:
            self._record(_bound_names(node.target), "unsafe")

        def visit_Delete(self, node: ast.Delete) -> None:
            for target in node.targets:
                self._record(_bound_names(target), "unsafe")

        def visit_For(self, node: ast.For) -> None:
            self._record(_bound_names(node.target), "unsafe")
            self.generic_visit(node)

        visit_AsyncFor = visit_For

        def visit_With(self, node: ast.With) -> None:
            for item in node.items:
                if item.optional_vars is not None:
                    self._record(_bound_names(item.optional_vars), "unsafe")
            self.generic_visit(node)

        visit_AsyncWith = visit_With

        def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
            if node.name:
                self._record({node.name}, "unsafe")
            self.generic_visit(node)
        def visit_Match(self, node: ast.Match) -> None:
            for case in node.cases:
                self._record(_pattern_bound_names(case.pattern), "unsafe")
            self.generic_visit(node)


        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._record({node.name}, "sealed")

        visit_AsyncFunctionDef = visit_FunctionDef
        visit_ClassDef = visit_FunctionDef

        def visit_Lambda(self, node: ast.Lambda) -> None:
            return

        def visit_ListComp(self, node: ast.ListComp) -> None:
            for child in ast.walk(node):
                if isinstance(child, ast.NamedExpr):
                    self.visit_NamedExpr(child)

        visit_SetComp = visit_ListComp
        visit_DictComp = visit_ListComp
        visit_GeneratorExp = visit_ListComp


    def _receiver_root(node: ast.AST) -> str | None:
        while isinstance(node, ast.Attribute):
            node = node.value
        return node.id if isinstance(node, ast.Name) else None
    def _attribute_depth(node: ast.Attribute) -> int:
        depth = 0
        current: ast.AST = node
        while isinstance(current, ast.Attribute):
            depth += 1
            current = current.value
        return depth

    local_module_receivers = {
        name for name, canonical in aliases.items()
        if _module_file(root, canonical) is not None
    }
    imported_modules, local_symbol_receivers = _local_importfrom_receivers(tree, path, root)
    local_module_receivers.update(imported_modules)
    local_module_apis: dict[str, set[str]] = {}
    for receiver in local_module_receivers:
        module_path = _module_file(root, aliases.get(receiver, receiver))
        if module_path is not None:
            local_module_apis[receiver] = _declared_local_module_apis(module_path)



    invalidated_receivers: set[str] = set()
    for node in ast.walk(tree):
        targets: tuple[ast.AST, ...]
        if isinstance(node, ast.Assign):
            targets = tuple(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets = (node.target,)
        elif isinstance(node, ast.AugAssign):
            targets = (node.target,)
        elif isinstance(node, ast.Delete):
            targets = tuple(node.targets)
        else:
            continue
        for target in targets:
            receiver = _assignment_receiver(target, aliases)
            if receiver:
                invalidated_receivers.add(receiver)

    def _is_invalidated(receiver: str) -> bool:
        return any(
            receiver == invalidated
            or receiver.startswith(f"{invalidated}.")
            or invalidated.startswith(f"{receiver}.")
            for invalidated in invalidated_receivers
        )

    def _reviewed_static_receiver(receiver: str | None) -> bool:
        return _reviewed_static_call(receiver)


    def _scope_bindings(
        statements: list[ast.stmt], parameters: set[str], inherited: set[str]
    ) -> set[str]:
        collector = _Bindings()
        for statement in statements:
            collector.visit(statement)
        safe = set(inherited)
        safe.difference_update(parameters)
        safe_events = {"import", "sealed"}
        for name, events in collector.events.items():
            if all(kind in safe_events for kind, _ in events):
                safe.add(name)
            else:
                safe.discard(name)
        changed = True
        while changed:
            changed = False
            for name, events in collector.events.items():
                if name in safe or any(kind not in {"alias"} for kind, _ in events):
                    continue
                if all(_receiver_root(value) in safe for _, value in events):
                    safe.add(name)
                    changed = True
        return safe

    def _parameters(args: ast.arguments) -> set[str]:
        return {
            argument.arg
            for argument in (*args.posonlyargs, *args.args, *args.kwonlyargs)
        } | ({args.vararg.arg} if args.vararg else set()) | ({args.kwarg.arg} if args.kwarg else set())

    class _ModuleScopeCalls(ast.NodeVisitor):
        def __init__(self) -> None:
            self.safe_scopes: list[set[str]] = []

        @property
        def safe(self) -> set[str]:
            return self.safe_scopes[-1]

        def _visit_scope(
            self, statements: list[ast.stmt], parameters: set[str] | None = None
        ) -> None:
            inherited = self.safe if self.safe_scopes else set()
            self.safe_scopes.append(_scope_bindings(statements, parameters or set(), inherited))
            for statement in statements:
                self.visit(statement)
            self.safe_scopes.pop()

        def visit_Module(self, node: ast.Module) -> None:
            self._visit_scope(node.body)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            for decorator in node.decorator_list:
                self.visit(decorator)
            for default in (*node.args.defaults, *node.args.kw_defaults):
                if default is not None:
                    self.visit(default)
            self._visit_scope(node.body, _parameters(node.args))

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            for decorator in node.decorator_list:
                self.visit(decorator)
            for base in node.bases:
                self.visit(base)
            for keyword in node.keywords:
                self.visit(keyword.value)
            self._visit_scope(node.body)

        def _visit_comprehension(self, node: ast.AST, generators: list[ast.comprehension]) -> None:
            self.safe_scopes.append(set(self.safe))
            for generator in generators:
                self.visit(generator.iter)
                self.safe_scopes[-1].difference_update(_bound_names(generator.target))
                for condition in generator.ifs:
                    self.visit(condition)
            if isinstance(node, ast.DictComp):
                self.visit(node.key)
                self.visit(node.value)
            else:
                self.visit(node.elt)
            self.safe_scopes.pop()

        def visit_ListComp(self, node: ast.ListComp) -> None:
            self._visit_comprehension(node, node.generators)

        visit_SetComp = visit_ListComp
        visit_GeneratorExp = visit_ListComp

        def visit_DictComp(self, node: ast.DictComp) -> None:
            self._visit_comprehension(node, node.generators)

        def visit_Call(self, node: ast.Call) -> None:
            if isinstance(node.func, ast.Attribute):
                receiver = _dotted_name(node.func, aliases)
                root = _receiver_root(node.func)
                if root in local_symbol_receivers or (
                    root in local_module_receivers and (
                        _attribute_depth(node.func) != 1
                        or node.func.attr not in local_module_apis.get(root, set())
                    )
                ):
                    raise EvidenceSchemaError(
                        f"unresolved executable receiver is unsupported: {path}"
                    )
                if (
                    receiver is None
                    or root is None
                    or root not in self.safe
                    or _is_invalidated(receiver)
                    or (
                        root not in local_module_receivers
                        and not _reviewed_static_receiver(receiver)
                    )
                ):
                    raise EvidenceSchemaError(
                        f"unresolved executable receiver is unsupported: {path}"
                    )
            self.generic_visit(node)

    _ModuleScopeCalls().visit(tree)




def _dynamic_module_file(root: Path, target: str, path: Path) -> Path | None:
    if not target.startswith("."):
        return _module_file(root, target)
    package = list(path.relative_to(root).parent.parts)
    dots = len(target) - len(target.lstrip("."))
    if dots > len(package):
        raise EvidenceSchemaError(f"relative dynamic import escapes repo package: {path}")
    suffix = target[dots:]
    module = package[:len(package) - dots + 1] + (suffix.split(".") if suffix else [])
    return _module_file(root, ".".join(module))
def _reject_untrusted_bare_calls(
    tree: ast.Module, path: Path, allowed_direct: set[str],
    safe_local_callables: set[str],
) -> set[int]:
    """Require each bare call to resolve to one exact lexical capability."""

    class _Bindings(ast.NodeVisitor):
        def __init__(self) -> None:
            self.events: dict[str, list[tuple[str, str | None]]] = {}

        def _record(self, names: set[str], kind: str, value: str | None = None) -> None:
            for name in names:
                self.events.setdefault(name, []).append((kind, value))

        def visit_Import(self, node: ast.Import) -> None:
            for alias in node.names:
                self._record({alias.asname or alias.name.split(".", 1)[0]}, "import", alias.name)

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            for alias in node.names:
                canonical = f"{node.module}.{alias.name}" if node.module else None
                self._record({alias.asname or alias.name}, "import", canonical)

        def visit_Assign(self, node: ast.Assign) -> None:
            self._record(set().union(*(_bound_names(target) for target in node.targets)), "other")
            self.visit(node.value)

        def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
            self._record(_bound_names(node.target), "other")
            if node.value is not None:
                self.visit(node.value)

        def visit_AugAssign(self, node: ast.AugAssign) -> None:
            self._record(_bound_names(node.target), "other")

        def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
            self._record(_bound_names(node.target), "other")
            self.visit(node.value)

        def visit_Delete(self, node: ast.Delete) -> None:
            for target in node.targets:
                self._record(_bound_names(target), "other")

        def visit_For(self, node: ast.For) -> None:
            self._record(_bound_names(node.target), "other")
            self.generic_visit(node)

        visit_AsyncFor = visit_For

        def visit_With(self, node: ast.With) -> None:
            for item in node.items:
                if item.optional_vars is not None:
                    self._record(_bound_names(item.optional_vars), "other")
            self.generic_visit(node)

        visit_AsyncWith = visit_With

        def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
            if node.name:
                self._record({node.name}, "other")
            self.generic_visit(node)
        def visit_Match(self, node: ast.Match) -> None:
            for case in node.cases:
                self._record(_pattern_bound_names(case.pattern), "other")
            self.generic_visit(node)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._record({node.name}, "other")

        visit_AsyncFunctionDef = visit_FunctionDef
        visit_ClassDef = visit_FunctionDef

        def visit_Lambda(self, node: ast.Lambda) -> None:
            return

    def _scope(
        statements: list[ast.stmt], parameters: set[str]
    ) -> dict[str, list[tuple[str, str | None]]]:
        bindings = _Bindings()
        bindings._record(parameters, "other")
        for statement in statements:
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)) and not statement.decorator_list:
                bindings._record({statement.name}, "function")
            else:
                bindings.visit(statement)
        return bindings.events

    def _parameters(args: ast.arguments) -> set[str]:
        return {
            argument.arg
            for argument in (*args.posonlyargs, *args.args, *args.kwonlyargs)
        } | ({args.vararg.arg} if args.vararg else set()) | ({args.kwarg.arg} if args.kwarg else set())

    builtins = {
        "abs", "all", "any", "bool", "dict", "enumerate", "float", "int", "isinstance",
        "len", "list", "map", "max", "min", "next", "print", "range", "repr", "set",
        "sorted", "str", "sum", "tuple", "type", "zip",
    }

    class _Calls(ast.NodeVisitor):
        def __init__(self) -> None:
            self.scopes: list[dict[str, list[tuple[str, str | None]]]] = []
            self.trusted_calls: set[int] = set()

        def _resolve(self, name: str) -> list[tuple[str, str | None]] | None:
            for scope in reversed(self.scopes):
                if name in scope:
                    return scope[name]
            return None

        def _visit_scope(self, statements: list[ast.stmt], parameters: set[str]) -> None:
            self.scopes.append(_scope(statements, parameters))
            for statement in statements:
                self.visit(statement)
            self.scopes.pop()

        def visit_Module(self, node: ast.Module) -> None:
            self._visit_scope(node.body, set())

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            for decorator in node.decorator_list:
                self.visit(decorator)
            for default in (*node.args.defaults, *node.args.kw_defaults):
                if default is not None:
                    self.visit(default)
            self._visit_scope(node.body, _parameters(node.args))

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            for decorator in node.decorator_list:
                self.visit(decorator)
            for base in node.bases:
                self.visit(base)
            self._visit_scope(node.body, set())
        def _visit_comprehension(
            self, node: ast.AST, generators: list[ast.comprehension]
        ) -> None:
            self.scopes.append({})
            for generator in generators:
                self.visit(generator.iter)
                self.scopes[-1].update(
                    {name: [("other", None)] for name in _bound_names(generator.target)}
                )
                for condition in generator.ifs:
                    self.visit(condition)
            if isinstance(node, ast.DictComp):
                self.visit(node.key)
                self.visit(node.value)
            else:
                self.visit(node.elt)
            self.scopes.pop()

        def visit_ListComp(self, node: ast.ListComp) -> None:
            self._visit_comprehension(node, node.generators)

        visit_SetComp = visit_ListComp
        visit_GeneratorExp = visit_ListComp

        def visit_DictComp(self, node: ast.DictComp) -> None:
            self._visit_comprehension(node, node.generators)


        def visit_Call(self, node: ast.Call) -> None:
            if isinstance(node.func, ast.Name):
                events = self._resolve(node.func.id)
                trusted = (
                    events is None and node.func.id in (builtins | {"__import__"})
                ) or events == [("function", None)] or (
                    events is not None
                    and len(events) == 1
                    and events[0][0] == "import"
                    and events[0][1] in allowed_direct
                )
                if not trusted:
                    raise EvidenceSchemaError(
                        f"unresolved callable alias is unsupported: {path}"
                    )
                self.trusted_calls.add(id(node))
                callback: ast.AST | None = None
                if node.func.id in {"map", "filter"} and node.args:
                    callback = node.args[0]
                elif node.func.id in {"sorted", "min", "max"}:
                    callback = next(
                        (keyword.value for keyword in node.keywords if keyword.arg == "key"),
                        None,
                    )
                elif node.func.id == "iter" and len(node.args) == 2:
                    callback = node.args[0]
                if callback is not None and (
                    not isinstance(callback, ast.Name)
                    or not (
                        self._resolve(callback.id) is None
                        and callback.id in {"abs", "bool", "float", "int", "repr", "str", "tuple"}
                        or self._resolve(callback.id) == [("function", None)]
                        and callback.id in safe_local_callables
                    )
                ):
                    raise EvidenceSchemaError(
                        f"unproven callback capability is unsupported: {path}"
                    )
            self.generic_visit(node)

    calls = _Calls()
    calls.visit(tree)
    return calls.trusted_calls


def _reject_executable_annotations(tree: ast.AST, path: Path) -> None:
    """Allow only annotation syntax whose evaluation has no user protocol hooks."""

    def _reject(annotation: ast.AST | None) -> None:
        if annotation is None:
            return
        if isinstance(annotation, (ast.Name, ast.Constant)):
            return
        if isinstance(annotation, ast.Tuple):
            for element in annotation.elts:
                _reject(element)
            return
        raise EvidenceSchemaError(f"executable annotation is unsupported: {path}")

    class _Annotations(ast.NodeVisitor):
        def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
            _reject(node.annotation)
            self.generic_visit(node)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            args = node.args
            for argument in (
                *args.posonlyargs,
                *args.args,
                *((args.vararg,) if args.vararg else ()),
                *args.kwonlyargs,
                *((args.kwarg,) if args.kwarg else ()),
            ):
                _reject(argument.annotation)
            _reject(node.returns)
            self._visit_type_parameters(node)
            self.generic_visit(node)

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self._visit_type_parameters(node)
            self.generic_visit(node)

        def visit_TypeAlias(self, node: ast.AST) -> None:
            _reject(getattr(node, "value", None))
            self._visit_type_parameters(node)
            self.generic_visit(node)

        @staticmethod
        def _visit_type_parameters(node: ast.AST) -> None:
            for parameter in getattr(node, "type_params", ()):
                _reject(getattr(parameter, "bound", None))
                _reject(getattr(parameter, "default_value", None))

    _Annotations().visit(tree)

def _dynamic_local_dependencies(tree: ast.AST, path: Path, root: Path) -> set[Path]:
    """Resolve only direct, literal dynamic imports; reject executable indirection."""
    _reject_executable_annotations(tree, path)
    _reject_sealed_store_mutation(tree, path)
    if any(isinstance(node, ast.Lambda) for node in ast.walk(tree)):
        raise EvidenceSchemaError(f"lambda executable dependencies are unsupported: {path}")
    parameter_names = {
        argument.arg
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))
        for argument in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
    }
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in parameter_names
        ):
            raise EvidenceSchemaError(
                f"unresolved executable receiver parameter is unsupported: {path}"
            )
    _reject_wildcard_imports(tree, path)
    calls, aliases = _dynamic_call_kinds(tree)
    _reject_sealed_global_mutation(tree, aliases, path)
    _reject_namespace_export_mutation(tree, aliases, path)
    _reject_unresolved_module_receivers(tree, aliases, path, root)
    found: set[Path] = set()
    executable = {
        "__import__", "builtins.__import__", "importlib.import_module",
        "importlib.util.spec_from_file_location", "importlib.machinery.SourceFileLoader",
        "importlib.machinery.SourcelessFileLoader", "runpy.run_module", "runpy.run_path",
        "exec", "eval", "compile", "open", "builtins.exec", "builtins.eval",
        "builtins.compile", "builtins.open",
    }
    allowed_direct = {
        "__import__", "builtins.__import__", "importlib.import_module",
        "importlib.util.spec_from_file_location", "importlib.machinery.SourceFileLoader",
        "importlib.machinery.SourcelessFileLoader",
    }
    forbidden = executable - allowed_direct
    forbidden_callables = {
        "getattr", "builtins.getattr", "operator.attrgetter", "operator.itemgetter",
        "pickle.load", "pickle.loads", "dill.load", "dill.loads",
        "cloudpickle.load", "cloudpickle.loads", "marshal.load", "marshal.loads",
        "shelve.open", "joblib.load", "numpy.load", "pandas.read_pickle",
        "torch.load", "yaml.load", "yaml.full_load", "yaml.unsafe_load",
    }
    dangerous_prefixes = (
        "subprocess.", "multiprocessing.", "ctypes.", "cffi.", "ffi.", "win32api.",
        "asyncio.create_subprocess", "concurrent.futures.ProcessPoolExecutor",
        "os.system", "os.popen", "os.exec", "os.spawn", "os.posix_spawn", "os.startfile",
    )
    loader_methods = {"exec_module", "load_module", "get_code", "create_module"}
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    local_callables = _direct_function_api_names(tree)
    _, local_symbol_receivers = _local_importfrom_receivers(tree, path, root)
    # A direct symbol imported from a repository-local module has no runtime
    # provenance here: it may be a function, class, or dynamically supplied
    # capability.  Local calls must retain the module carrier syntax so the
    # receiver scanner can validate the declared API path.  The import also
    # wins over a same-named earlier declaration.
    safe_local_callables = local_callables - local_symbol_receivers
    trusted_bare_calls = _reject_untrusted_bare_calls(
        tree, path, allowed_direct, safe_local_callables
    )
    safe_aliases = safe_local_callables | {
        name for name, canonical in aliases.items()
        if name not in local_symbol_receivers
        and (
            canonical in allowed_direct
            or _module_file(root, canonical.rsplit(".", 1)[0]) is not None
        )
    }
    unsafe_aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
            if isinstance(node.value, ast.Lambda) or (
                isinstance(node.value, ast.Name) and node.value.id in safe_local_callables
            ):
                safe_aliases.update(targets)
            else:
                unsafe_aliases.update(targets)

    # Dangerous capabilities may only be invoked directly through a sealed API.
    # Passing one to map/filter/partial or storing it as a value is executable
    # indirection, even when the eventual target would be a literal local module.
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Name, ast.Attribute)):
            continue
        canonical = _dotted_name(node, aliases)
        parent = parents.get(node)
        if isinstance(parent, ast.Attribute) and parent.value is node:
            continue
        is_loader_method = isinstance(node, ast.Attribute) and node.attr in loader_methods
        is_dangerous = (
            canonical in executable
            or canonical in forbidden_callables
            or bool(canonical and canonical.startswith(dangerous_prefixes))
            or bool(canonical and canonical.startswith(
                ("pickle.", "dill.", "cloudpickle.", "marshal.", "shelve.", "joblib.")
            ))
            or bool(canonical and (
                canonical.startswith("importlib.machinery.") or "Loader" in canonical
            ))
            or is_loader_method
        )
        if not is_dangerous:
            continue
        if (
            canonical in allowed_direct
            and isinstance(parent, ast.Call)
            and parent.func is node
        ):
            continue
        raise EvidenceSchemaError(
            f"higher-order or unsafe executable callable is unsupported: {path}"
        )

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Call):
            raise EvidenceSchemaError(f"call-of-call execution is unsupported: {path}")
        if not isinstance(node.func, (ast.Name, ast.Attribute)):
            raise EvidenceSchemaError(f"callable-producing expression is unsupported: {path}")
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Call)
            and isinstance(node.func.value.func, ast.Name)
            and node.func.value.func.id == "type"
            and node.func.attr == "__getattribute__"
        ):
            raise EvidenceSchemaError(f"reflective attribute factory is unsupported: {path}")
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Call):
            raise EvidenceSchemaError(f"callable-producing attribute factory is unsupported: {path}")
        raw_name = _dotted_name(node.func, {})
        canonical = _dotted_name(node.func, aliases)
        if isinstance(node.func, ast.Subscript):
            raise EvidenceSchemaError(f"indirect subscript execution is unsupported: {path}")
        if isinstance(node.func, ast.Attribute) and node.func.attr in {"exec_module", "load_module", "get_code"}:
            raise EvidenceSchemaError(f"loader execution through an unresolved callable is unsupported: {path}")
        if isinstance(node.func, ast.Name) and node.func.id in unsafe_aliases:
            raise EvidenceSchemaError(f"unresolved callable alias is unsupported: {path}")
        if (
            isinstance(node.func, ast.Name)
            and node.func.id not in safe_aliases
            and id(node) not in trusted_bare_calls
        ):
            raise EvidenceSchemaError(f"unresolved callable alias is unsupported: {path}")
        if raw_name in forbidden or canonical in forbidden:
            raise EvidenceSchemaError(f"indirect local Python execution is unsupported: {path}")
        loader_name = canonical or raw_name or ""
        if (
            loader_name.startswith(("pickle", "dill", "cloudpickle", "marshal", "shelve", "joblib"))
            or loader_name.endswith((".load", ".loads", ".Unpickler", ".find_class", ".load_module", ".unsafe_load"))
            or loader_name in {"numpy.load", "pandas.read_pickle", "torch.load", "yaml.full_load"}
        ):
            raise EvidenceSchemaError(f"unsafe deserializer/loader is unsupported: {path}")
        kind = calls.get(raw_name) if raw_name else None
        kind = kind or (calls.get(canonical) if canonical else None)
        if kind is None:
            if canonical and (
                canonical.startswith("importlib")
                or canonical.startswith("runpy")
                or "FileLoader" in canonical
            ):
                raise EvidenceSchemaError(f"unsupported dynamic import/load API or alias: {path}")
            continue
        exact_module_import = (canonical or raw_name) in {
            "__import__", "builtins.__import__", "importlib.import_module",
        }
        if exact_module_import and (len(node.args) != 1 or node.keywords):
            raise EvidenceSchemaError(
                f"dynamic module import must use one exact literal argument: {path}"
            )
        target = node.args[0] if kind in {"module", "file_first"} and node.args else (
            node.args[1] if kind == "file" and len(node.args) > 1 else next(
                (keyword.value for keyword in node.keywords if keyword.arg in {"location", "path"}), None
            )
        )
        if not isinstance(target, ast.Constant) or not isinstance(target.value, str):
            raise EvidenceSchemaError(f"dynamic import/load target must be an exact string literal: {path}")
        if exact_module_import and target.value.startswith("."):
            raise EvidenceSchemaError(
                f"dynamic module import target must be an absolute module name: {path}"
            )
        if kind == "module":
            candidate = _dynamic_module_file(root, target.value, path)
        else:
            location = Path(target.value)
            candidate = (path.parent / location).resolve() if not location.is_absolute() else location.resolve()
            if not candidate.is_file() or candidate.suffix != ".py":
                raise EvidenceSchemaError(f"dynamic import/load target must resolve to a local .py file: {path}")
        if candidate is None:
            raise EvidenceSchemaError(f"dynamic import/load target cannot be resolved locally: {path}")
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise EvidenceSchemaError(f"dynamic import/load target resolves outside repo_root: {path}") from exc
        found.add(candidate)
    return found


def _local_imports(path: Path, root: Path) -> tuple[set[Path], set[Path]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        raise EvidenceSchemaError(f"cannot parse dependency Python file {path}: {exc}") from exc
    package = list(path.relative_to(root).parent.parts)
    found: set[Path] = set()
    for node in ast.walk(tree):
        modules: list[str] = []
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            prefix = package[:len(package) - node.level + 1] if node.level else []
            if node.level and node.level > len(package) + 1:
                raise EvidenceSchemaError(f"relative import escapes repo package: {path}")
            base = prefix + (node.module.split(".") if node.module else [])
            if base:
                modules.append(".".join(base))
            modules.extend(".".join(base + [alias.name]) for alias in node.names)
        for module in modules:
            candidate = _module_file(root, module)
            if candidate is not None:
                found.add(candidate)
                found.update(_package_initializers(candidate, root))
    return found, _dynamic_local_dependencies(tree, path, root)


def _derived_python_closure(root: Path, dependency_roots: list[str]) -> tuple[set[str], set[str]]:
    roots = [(root / Path(*PurePosixPath(item).parts)).resolve() for item in dependency_roots]
    pending = roots + [initializer for item in roots for initializer in _package_initializers(item, root)]
    closure: set[Path] = set()
    dynamic: set[Path] = set()
    while pending:
        current = pending.pop()
        if current not in closure:
            closure.add(current)
            imports, dynamic_imports = _local_imports(current, root)
            dynamic.update(dynamic_imports)
            pending.extend((imports | dynamic_imports | set().union(*(_package_initializers(item, root) for item in dynamic_imports))) - closure)
    return (
        {path.relative_to(root).as_posix() for path in closure},
        {path.relative_to(root).as_posix() for path in dynamic},
    )


def derive_prereg_code_manifest(text: str, repo_root: Path | str) -> set[str]:
    """Derive the only valid code manifest from a sealed document contract."""
    root = Path(repo_root).resolve()
    contract = _parse_contract(text, root)
    python_closure, dynamic_dependencies = _derived_python_closure(root, contract["dependency_roots"])
    if dynamic_dependencies != set(contract["dynamic_python_dependencies"]):
        raise EvidenceSchemaError("dynamic_python_dependencies must exactly declare every local dynamic import/load target")
    return python_closure | set(contract["non_python_dependencies"])


def finalize_prereg(doc_path: Path | str, *, repo_root: Path | str, code_files: tuple[Path | str, ...], manifest_path: Path | str, sealed_at: str) -> dict:
    """Create a v2 prereg seal only at its contract-owned canonical destination."""
    root, document = Path(repo_root).resolve(), Path(doc_path).resolve()
    try:
        doc_relative = document.relative_to(root).as_posix()
    except ValueError as exc:
        raise EvidenceSchemaError("doc_path must resolve inside repo_root") from exc
    if not document.is_file():
        raise EvidenceSchemaError("doc_path must name an existing preregistration document")
    text = document.read_text(encoding="utf-8")
    if "> 지위: **SEALED**" not in text:
        raise EvidenceSchemaError("preregistration document is not explicitly SEALED")
    if any(marker in text for marker in ("봉인 전 초안", "(기입)", "(미주입")):
        raise EvidenceSchemaError("preregistration document retains draft marker")
    contract = _parse_contract(text, root)
    declared = []
    for index, code_file in enumerate(code_files):
        candidate = Path(code_file).resolve()
        if not candidate.is_file():
            raise EvidenceSchemaError(f"code_files[{index}] must name a file")
        try:
            declared.append(candidate.relative_to(root).as_posix())
        except ValueError as exc:
            raise EvidenceSchemaError(f"code_files[{index}] must resolve inside repo_root") from exc
    if len(declared) != len(set(declared)):
        raise EvidenceSchemaError("code_files must resolve to unique paths")
    expected = derive_prereg_code_manifest(text, root)
    if set(declared) != expected:
        raise EvidenceSchemaError("code_files must equal derived Python dependency closure plus non_python_dependencies")
    manifest = [{"path": item, "sha256": hashlib.sha256((root / Path(*PurePosixPath(item).parts)).read_bytes()).hexdigest()} for item in sorted(expected)]
    sealed_doc = {"path": doc_relative, "sha256": hashlib.sha256(document.read_bytes()).hexdigest()}
    canonical_output = root / Path(*PurePosixPath(contract["authority_paths"]["seal_dir"]).parts) / f"{sealed_doc['sha256']}.seal.json"
    if Path(manifest_path).resolve() != canonical_output:
        raise EvidenceSchemaError("manifest_path must equal the canonical contract seal path")
    seal = {
        "schema_version": 2, "kind": "prereg_seal", "status": "SEALED", "sealed_at": sealed_at,
        "sealed_doc": sealed_doc, "ledger_path": contract["ledger_path"],
        "authority_paths": contract["authority_paths"], "code_manifest": manifest,
    }
    validated = validate_prereg_seal(seal, repo_root=root, verify_files=True)
    with authority_mutation_guard(root, contract["authority_paths"], fields=("seal_dir",)) as guard:
        guard.hold_path(canonical_output)
        guard.validate_file(canonical_output)
        if canonical_output.exists():
            raise FileExistsError(f"existing prereg seal sidecar cannot be overwritten: {canonical_output}")
        fd = guard.open_path(canonical_output, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(canonical_json_bytes(validated).decode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
    return dict(validated)
