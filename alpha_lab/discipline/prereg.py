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

import ast
import hashlib
import json
import re
import os
import stat
from pathlib import Path, PurePosixPath

from alpha_lab.discipline import windows
from alpha_lab.discipline.evidence import (
    EvidenceSchemaError,
    canonical_json_bytes,
    validate_prereg_seal,
)

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


def _dynamic_local_dependencies(tree: ast.AST, path: Path, root: Path) -> set[Path]:
    """Resolve only direct, literal dynamic imports; reject executable indirection."""
    calls, aliases = _dynamic_call_kinds(tree)
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
    local_callables = {
        node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }
    safe_aliases = local_callables | {
        name for name, canonical in aliases.items()
        if canonical in allowed_direct
        or _module_file(root, canonical.rsplit(".", 1)[0]) is not None
    }
    unsafe_aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
            if isinstance(node.value, ast.Lambda) or (
                isinstance(node.value, ast.Name) and node.value.id in local_callables
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
        if isinstance(node.func, ast.Name) and node.func.id not in safe_aliases and node.func.id not in {
            "abs", "all", "any", "bool", "dict", "enumerate", "float", "int", "isinstance",
            "len", "list", "map", "max", "min", "next", "print", "range", "repr", "set",
            "sorted", "str", "sum", "tuple", "type", "zip",
        }:
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
        target = node.args[0] if kind in {"module", "file_first"} and node.args else (
            node.args[1] if kind == "file" and len(node.args) > 1 else next(
                (keyword.value for keyword in node.keywords if keyword.arg in {"location", "path"}), None
            )
        )
        if not isinstance(target, ast.Constant) or not isinstance(target.value, str):
            raise EvidenceSchemaError(f"dynamic import/load target must be an exact string literal: {path}")
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
    if canonical_output.exists():
        raise FileExistsError(f"existing prereg seal sidecar cannot be overwritten: {canonical_output}")
    canonical_output.parent.mkdir(parents=True, exist_ok=True)
    revalidate_authority_paths(root, contract["authority_paths"])
    _contract_ledger_path(contract["ledger_path"], root)
    with open(canonical_output, "x", encoding="utf-8", newline="\n") as handle:
        handle.write(canonical_json_bytes(validated).decode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    return dict(validated)
