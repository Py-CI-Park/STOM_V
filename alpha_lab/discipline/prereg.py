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
_CONTRACT_KEYS = {"schema_version", "hypothesis_id", "discovery_window", "primary_estimand", "sample_floors", "multiplicity_family", "kill_rule", "dependency_roots", "dynamic_python_dependencies", "non_python_dependencies"}


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


def _dynamic_local_dependencies(tree: ast.AST, path: Path, root: Path) -> set[Path]:
    """Resolve literal local dynamic imports; reject non-literal local loader targets."""
    found: set[Path] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        name = function.id if isinstance(function, ast.Name) else function.attr if isinstance(function, ast.Attribute) else ""
        is_module_import = name in {"__import__", "import_module"}
        is_file_loader = name in {"spec_from_file_location", "SourceFileLoader", "SourcelessFileLoader"}
        if not (is_module_import or is_file_loader):
            continue
        target = node.args[0] if is_module_import and node.args else (
            node.args[1] if is_file_loader and len(node.args) > 1 else next(
                (keyword.value for keyword in node.keywords if keyword.arg in {"location", "path"}), None
            )
        )
        if not isinstance(target, ast.Constant) or not isinstance(target.value, str):
            raise EvidenceSchemaError(f"dynamic import/load target must be an exact string literal: {path}")
        if is_module_import:
            candidate = _module_file(root, target.value)
        else:
            location = Path(target.value)
            candidate = (path.parent / location).resolve() if not location.is_absolute() else location.resolve()
            if not candidate.is_file() or candidate.suffix != ".py":
                candidate = None
        if candidate is not None:
            try:
                candidate.relative_to(root)
            except ValueError:
                continue
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
    pending = [(root / Path(*PurePosixPath(item).parts)).resolve() for item in dependency_roots]
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


def finalize_prereg(doc_path: Path | str, *, repo_root: Path | str, code_files: tuple[Path | str, ...], manifest_path: Path | str, sealed_at: str) -> dict:
    """Create a v2 prereg seal after contract and dependency-closure validation."""
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
    python_closure, dynamic_dependencies = _derived_python_closure(root, contract["dependency_roots"])
    if dynamic_dependencies != set(contract["dynamic_python_dependencies"]):
        raise EvidenceSchemaError("dynamic_python_dependencies must exactly declare every local dynamic import/load target")
    expected = python_closure | set(contract["non_python_dependencies"])
    if set(declared) != expected:
        raise EvidenceSchemaError("code_files must equal derived Python dependency closure plus non_python_dependencies")
    manifest = [{"path": item, "sha256": hashlib.sha256((root / Path(*PurePosixPath(item).parts)).read_bytes()).hexdigest()} for item in sorted(expected)]
    seal = {"schema_version": 2, "kind": "prereg_seal", "status": "SEALED", "sealed_at": sealed_at, "sealed_doc": {"path": doc_relative, "sha256": hashlib.sha256(document.read_bytes()).hexdigest()}, "code_manifest": manifest}
    validated = validate_prereg_seal(seal, repo_root=root, verify_files=True)
    output = Path(manifest_path)
    if output.exists():
        raise FileExistsError(f"existing prereg seal sidecar cannot be overwritten: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "x", encoding="utf-8", newline="\n") as handle:
        handle.write(canonical_json_bytes(validated).decode("utf-8"))
    return dict(validated)
