"""연구 증거 lineage 자동 검사기 (advisory 전용, 읽기 전용).

.omo/evidence 계열 캠페인 산출물 디렉터리를 검사한다.

검사 항목:
  (a) ``*_summary.json`` 과 짝 ``*.jsonl`` 의 일관성
      - iter/eval 형식: promising 목록 재계산 일치, ``_n{N}`` 이름 규약 행수,
        iter 중복, out 경로 존재/표기.
      - round/event 형식: rounds/adopted_total 재계산 일치,
        best_overall.profit 이 jsonl cand 레코드에 존재하는지(허용오차).
  (b) research_runs/ 3종 문서 세트(plan/management/result) 완결성.
  (c) 캠페인 registry 성격 인벤토리 — summary 의 artifacts 등록부 파일
      존재/비어있지 않음, 디렉터리 내 0바이트 파일.

결과는 JSON 보고(issue 목록 {path, check, severity, detail})로 stdout 에 쓰고,
severity 'error' 가 하나라도 있으면 종료코드 1 을 반환한다.
알 수 없는 summary 형식은 'unknown_format' advisory 로 스킵한다.
파일 쓰기는 ``--report`` 출력 1건뿐이다.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SEV_ERROR = "error"
SEV_WARNING = "warning"
SEV_ADVISORY = "advisory"

_SUMMARY_SUFFIX = "_summary.json"
_ROWCOUNT_NAME_RE = re.compile(r"_n(\d+)$")
_RUN_DOC_SUFFIXES = ("_plan.md", "_management.md", "_result.md")
_SKIP_DIR_NAMES = {"__pycache__"}
_DEFAULT_RESEARCH_RUNS = Path("docs/research/condition_research/research_runs")


def make_issue(path, check, severity, detail):
    """issue 레코드를 새 dict 로 생성한다."""
    return {
        "path": str(path),
        "check": str(check),
        "severity": str(severity),
        "detail": str(detail),
    }


def load_json_file(path):
    """JSON 파일을 읽는다. (data, error_message) 튜플 반환."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"read failed: {exc}"
    try:
        return json.loads(text), None
    except ValueError as exc:
        return None, f"json parse failed: {exc}"


def load_jsonl_rows(path):
    """JSONL 파일을 읽는다. (rows, bad_line_numbers) 튜플 반환."""
    rows = []
    bad_lines = []
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return [], [-1]
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            rows.append(json.loads(stripped))
        except ValueError:
            bad_lines.append(line_no)
    return rows, bad_lines


def classify_summary(data):
    """summary dict 의 형식을 판별한다."""
    if not isinstance(data, dict):
        return "unknown"
    if "promising" in data and "out" in data:
        return "iter_eval"
    if "rounds" in data and "adopted_total" in data:
        return "round_event"
    return "unknown"


def _is_close(a, b, rel_tol=1e-6, abs_tol=1e-3):
    """허용오차 내 수치 비교."""
    try:
        fa, fb = float(a), float(b)
    except (TypeError, ValueError):
        return False
    return abs(fa - fb) <= max(abs_tol, rel_tol * max(abs(fa), abs(fb)))


def recompute_promising(rows):
    """jsonl iter/eval 레코드에서 promising 템플릿 목록을 재계산한다.

    규칙: eval.both_positive 가 True 인 레코드의 template.
    """
    found = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        eval_block = row.get("eval")
        if isinstance(eval_block, dict) and eval_block.get("both_positive") is True:
            template = row.get("template")
            if template is not None and template not in found:
                found.append(template)
    return sorted(str(t) for t in found)


def recompute_round_stats(rows):
    """jsonl event 레코드에서 rounds/adopted_total/cand profit 목록을 재계산한다."""
    round_markers = 0
    max_round = 0
    adopted = 0
    cand_profits = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        event = row.get("event")
        round_no = row.get("round")
        if isinstance(round_no, (int, float)):
            max_round = max(max_round, int(round_no))
        if event in ("round_done", "round_dry"):
            round_markers += 1
        elif event == "cand":
            if row.get("gate") is True:
                adopted += 1
            profit = row.get("profit")
            if isinstance(profit, (int, float)):
                cand_profits.append(float(profit))
    rounds = round_markers if round_markers > 0 else max_round
    return {"rounds": rounds, "adopted_total": adopted, "cand_profits": cand_profits}


def find_repo_root(start):
    """start 에서 상위로 올라가며 .git 이 있는 디렉터리를 찾는다."""
    current = Path(start).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _resolve_out_path(out_value, summary_path, repo_root):
    """summary 의 out 경로를 해석해 존재하는 Path 또는 None 을 반환한다."""
    normalized = str(out_value).replace("\\", "/")
    raw = Path(normalized)
    candidates = [raw] if raw.is_absolute() else []
    if not raw.is_absolute():
        if repo_root is not None:
            candidates.append(repo_root / raw)
        candidates.append(Path(summary_path).parent / raw)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def check_out_path(summary_path, data, repo_root):
    """iter_eval summary 의 out 경로 표기/존재를 검사한다."""
    issues = []
    out_value = data.get("out")
    if not isinstance(out_value, str) or not out_value.strip():
        issues.append(make_issue(
            summary_path, "out_path_missing_field", SEV_WARNING,
            "summary has no usable 'out' path field",
        ))
        return issues
    normalized = out_value.replace("\\", "/")
    if Path(normalized).is_absolute():
        issues.append(make_issue(
            summary_path, "out_path_absolute", SEV_ADVISORY,
            f"non-portable absolute out path notation: {out_value}",
        ))
    if _resolve_out_path(out_value, summary_path, repo_root) is None:
        issues.append(make_issue(
            summary_path, "out_path_missing", SEV_WARNING,
            f"out path does not exist: {out_value}",
        ))
    return issues


def check_iter_eval(summary_path, data, rows):
    """iter/eval 형식 summary 와 jsonl 의 일관성을 검사한다."""
    issues = []
    iters = [row.get("iter") for row in rows
             if isinstance(row, dict) and row.get("iter") is not None]
    duplicates = sorted({i for i in iters if iters.count(i) > 1})
    if duplicates:
        issues.append(make_issue(
            summary_path, "duplicate_iter", SEV_WARNING,
            f"duplicate iter values in paired jsonl: {duplicates}",
        ))

    stem = Path(summary_path).name[: -len(_SUMMARY_SUFFIX)]
    match = _ROWCOUNT_NAME_RE.search(stem)
    if match:
        expected = int(match.group(1))
        if expected != len(rows):
            issues.append(make_issue(
                summary_path, "row_count_mismatch", SEV_ERROR,
                f"name declares n={expected} but paired jsonl has {len(rows)} rows",
            ))

    declared = data.get("promising")
    if isinstance(declared, list):
        declared_sorted = sorted(str(t) for t in declared)
        recomputed = recompute_promising(rows)
        if declared_sorted != recomputed:
            issues.append(make_issue(
                summary_path, "promising_mismatch", SEV_ERROR,
                f"summary promising={declared_sorted} but jsonl recompute"
                f" (both_positive=true)={recomputed}",
            ))
    else:
        issues.append(make_issue(
            summary_path, "promising_not_list", SEV_ERROR,
            "summary 'promising' field is not a list",
        ))
    return issues


def check_round_event(summary_path, data, rows):
    """round/event 형식 summary 와 jsonl 의 일관성을 검사한다."""
    issues = []
    stats = recompute_round_stats(rows)

    declared_rounds = data.get("rounds")
    if isinstance(declared_rounds, (int, float)):
        if int(declared_rounds) != stats["rounds"]:
            issues.append(make_issue(
                summary_path, "rounds_mismatch", SEV_ERROR,
                f"summary rounds={int(declared_rounds)} but jsonl recompute"
                f"={stats['rounds']}",
            ))

    declared_adopted = data.get("adopted_total")
    if isinstance(declared_adopted, (int, float)):
        if int(declared_adopted) != stats["adopted_total"]:
            issues.append(make_issue(
                summary_path, "adopted_total_mismatch", SEV_ERROR,
                f"summary adopted_total={int(declared_adopted)} but jsonl"
                f" gate=true cand count={stats['adopted_total']}",
            ))

    best = data.get("best_overall")
    if isinstance(best, dict) and stats["cand_profits"]:
        profit = best.get("profit")
        if isinstance(profit, (int, float)):
            hit = any(_is_close(profit, p) for p in stats["cand_profits"])
            if not hit:
                issues.append(make_issue(
                    summary_path, "best_overall_not_in_jsonl", SEV_WARNING,
                    f"best_overall.profit={profit} not found among"
                    f" {len(stats['cand_profits'])} cand profits (tolerance)",
                ))
    return issues


def check_artifacts(summary_path, data):
    """summary 의 artifacts 등록부에 있는 파일 존재/비어있지 않음을 검사한다."""
    issues = []
    artifacts = data.get("artifacts")
    if not isinstance(artifacts, list):
        return issues
    base_dir = Path(summary_path).parent
    for name in artifacts:
        artifact_path = base_dir / str(name).replace("\\", "/")
        if not artifact_path.exists():
            issues.append(make_issue(
                summary_path, "artifact_missing", SEV_ERROR,
                f"registered artifact not found: {name}",
            ))
        elif artifact_path.is_file() and artifact_path.stat().st_size == 0:
            issues.append(make_issue(
                summary_path, "artifact_empty", SEV_ERROR,
                f"registered artifact is empty: {name}",
            ))
    return issues


def check_summary_file(summary_path, repo_root):
    """단일 *_summary.json 을 형식 판별 후 검사한다."""
    issues = []
    data, error = load_json_file(summary_path)
    if error is not None:
        issues.append(make_issue(
            summary_path, "summary_parse_error", SEV_ERROR, error))
        return issues

    fmt = classify_summary(data)
    if fmt == "unknown":
        issues.append(make_issue(
            summary_path, "unknown_format", SEV_ADVISORY,
            "summary format not recognized; consistency checks skipped",
        ))
        if isinstance(data, dict):
            issues.extend(check_artifacts(summary_path, data))
        return issues

    stem = Path(summary_path).name[: -len(_SUMMARY_SUFFIX)]
    jsonl_path = Path(summary_path).parent / f"{stem}.jsonl"
    if not jsonl_path.exists():
        issues.append(make_issue(
            summary_path, "missing_jsonl_pair", SEV_ERROR,
            f"paired jsonl not found: {jsonl_path.name}",
        ))
        issues.extend(check_artifacts(summary_path, data))
        if fmt == "iter_eval":
            issues.extend(check_out_path(summary_path, data, repo_root))
        return issues

    rows, bad_lines = load_jsonl_rows(jsonl_path)
    if bad_lines:
        issues.append(make_issue(
            jsonl_path, "jsonl_parse_error", SEV_ERROR,
            f"unparseable jsonl lines: {bad_lines[:10]}",
        ))
    if not rows:
        issues.append(make_issue(
            jsonl_path, "empty_jsonl", SEV_ERROR,
            "paired jsonl has no parseable rows",
        ))
        issues.extend(check_artifacts(summary_path, data))
        return issues

    if fmt == "iter_eval":
        issues.extend(check_iter_eval(summary_path, data, rows))
        issues.extend(check_out_path(summary_path, data, repo_root))
    elif fmt == "round_event":
        issues.extend(check_round_event(summary_path, data, rows))
    issues.extend(check_artifacts(summary_path, data))
    return issues


def _iter_files(root):
    """스킵 디렉터리를 제외하고 root 하위 파일을 순회한다."""
    root_path = Path(root)
    for path in sorted(root_path.rglob("*")):
        rel_parts = path.relative_to(root_path).parts
        if set(rel_parts) & _SKIP_DIR_NAMES:
            continue
        if any(part.startswith(".") for part in rel_parts[:-1]):
            continue
        if path.is_file():
            yield path


def check_orphan_jsonl(root, summary_stems):
    """summary 짝이 없는 jsonl 을 경고로 보고한다."""
    issues = []
    for path in _iter_files(root):
        if path.suffix != ".jsonl":
            continue
        if path.stem not in summary_stems:
            issues.append(make_issue(
                path, "jsonl_without_summary", SEV_WARNING,
                f"no paired {path.stem}{_SUMMARY_SUFFIX} found",
            ))
    return issues


def check_inventory(root):
    """디렉터리 인벤토리 — 0바이트 파일을 보고한다."""
    issues = []
    for path in _iter_files(root):
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size == 0:
            issues.append(make_issue(
                path, "empty_file", SEV_WARNING, "file exists but is empty"))
    return issues


def check_research_runs(runs_dir):
    """research_runs/ 3종 문서 세트(plan/management/result) 완결성 검사."""
    issues = []
    runs_path = Path(runs_dir)
    if not runs_path.is_dir():
        issues.append(make_issue(
            runs_path, "research_runs_missing", SEV_ADVISORY,
            "research_runs directory not found; doc-set check skipped",
        ))
        return issues

    groups = {}
    for path in sorted(runs_path.glob("*.md")):
        matched = None
        for suffix in _RUN_DOC_SUFFIXES:
            if path.name.endswith(suffix):
                matched = suffix
                break
        if matched is None:
            issues.append(make_issue(
                path, "research_run_unrecognized", SEV_ADVISORY,
                "file does not follow *_plan/_management/_result.md convention",
            ))
            continue
        base = path.name[: -len(matched)]
        groups.setdefault(base, {})[matched] = path

    for base in sorted(groups):
        members = groups[base]
        for suffix in _RUN_DOC_SUFFIXES:
            member = members.get(suffix)
            if member is None:
                issues.append(make_issue(
                    runs_path / f"{base}{suffix}", "research_run_doc_missing",
                    SEV_ERROR,
                    f"run '{base}' is missing its '{suffix}' document",
                ))
            elif member.stat().st_size == 0:
                issues.append(make_issue(
                    member, "research_run_doc_empty", SEV_ERROR,
                    f"run '{base}' document is empty",
                ))
    return issues


def run_checks(root, research_runs_dir=None):
    """전체 검사를 수행하고 보고 dict 를 반환한다 (읽기 전용)."""
    root_path = Path(root)
    issues = []
    summaries_checked = 0

    if not root_path.is_dir():
        issues.append(make_issue(
            root_path, "root_missing", SEV_ERROR,
            "evidence root directory not found",
        ))
    else:
        repo_root = find_repo_root(root_path)
        summary_paths = [p for p in _iter_files(root_path)
                         if p.name.endswith(_SUMMARY_SUFFIX)]
        summary_stems = {p.name[: -len(_SUMMARY_SUFFIX)] for p in summary_paths}
        for summary_path in summary_paths:
            summaries_checked += 1
            issues.extend(check_summary_file(summary_path, repo_root))
        issues.extend(check_orphan_jsonl(root_path, summary_stems))
        issues.extend(check_inventory(root_path))

    if research_runs_dir is None:
        repo_root = find_repo_root(root_path if root_path.exists() else Path.cwd())
        base = repo_root if repo_root is not None else Path.cwd()
        research_runs_dir = base / _DEFAULT_RESEARCH_RUNS
    issues.extend(check_research_runs(research_runs_dir))

    counts = {SEV_ERROR: 0, SEV_WARNING: 0, SEV_ADVISORY: 0}
    for issue in issues:
        severity = issue["severity"]
        counts[severity] = counts.get(severity, 0) + 1
    exit_code = 1 if counts.get(SEV_ERROR, 0) > 0 else 0

    return {
        "root": str(root_path),
        "research_runs": str(research_runs_dir),
        "summaries_checked": summaries_checked,
        "counts": counts,
        "issues": issues,
        "exit_code": exit_code,
    }


def build_parser():
    """CLI 파서를 생성한다."""
    parser = argparse.ArgumentParser(
        prog="check_research_evidence_lineage",
        description="research evidence lineage checker (advisory, read-only)",
    )
    parser.add_argument(
        "--root", default=".omo/evidence/tmap-walkforward",
        help="evidence root directory to inspect",
    )
    parser.add_argument(
        "--research-runs", default=None,
        help="research_runs directory (default: repo docs/research/"
             "condition_research/research_runs)",
    )
    parser.add_argument(
        "--report", default=None,
        help="optional path to write the JSON report",
    )
    return parser


def main(argv=None):
    """CLI 진입점. severity 'error' 존재 시 1 을 반환한다."""
    args = build_parser().parse_args(argv)
    report = run_checks(args.root, research_runs_dir=args.research_runs)
    rendered = json.dumps(report, ensure_ascii=True, indent=2, sort_keys=False)
    sys.stdout.write(rendered + "\n")
    if args.report:
        report_path = Path(args.report)
        if report_path.parent and not report_path.parent.exists():
            report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(rendered + "\n", encoding="utf-8")
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
