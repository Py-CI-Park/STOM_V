"""탭형 연구 리포트 HTML + manifest 생성 CLI — 수동 오프라인 writer 전용.

사용: STOM_ALLOW_MINIMAL_SETTING=1 python scripts/build_research_report.py [--commit <hash>]
산출: docs/research/condition_research/reports/research_lab_report.html
      docs/research/condition_research/reports/research_report_manifest.json
원본 read-only(판정 json·원장·strategy.db) · 엔진 0회 · git 커밋은 메인 세션 몫.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from alpha_lab.reporting import loaders, registry  # noqa: E402
from alpha_lab.reporting.build_html import build_all, extract_report_links  # noqa: E402

_DEFAULT_OUT = _REPO / "docs/research/condition_research/reports"
_SCHEMA = "stom-research-report-manifest-v1"
_WRITER = "manual-offline"
_MANIFEST_NAME = "research_report_manifest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> Optional[str]:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _dedupe(items: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _source_paths_for_study(study: registry.Study) -> List[str]:
    paths = [registry.PLANS + "/" + study.seal_doc]
    paths.extend(loaders.rel_path(*part.split("/")) for part in study.evidence)
    return _dedupe(paths)


def _source_paths_for_hub() -> List[str]:
    paths = [
        "alpha_lab/reporting/build_html.py",
        "alpha_lab/reporting/detail.py",
        "alpha_lab/reporting/loaders.py",
        "alpha_lab/reporting/registry.py",
        "alpha_lab/reporting/tabs.py",
        "alpha_lab/reporting/util.py",
        loaders.rel_path("n_trials_ledger.jsonl"),
    ]
    for study in registry.STUDIES:
        paths.extend(_source_paths_for_study(study))
    return _dedupe(paths)


def _source_hashes(source_paths: Iterable[str]) -> Dict[str, str]:
    hashes: Dict[str, str] = {}
    for rel in source_paths:
        digest = _sha256_file(_REPO / rel)
        if digest is not None:
            hashes[rel] = digest
    return hashes


def _report_row(
    *,
    path: str,
    title: str,
    kind: str,
    research_id: str,
    html: str,
    source_paths: List[str],
    links: List[str],
    step_id: Optional[str] = None,
) -> Dict[str, object]:
    encoded = html.encode("utf-8")
    source_sha256 = _source_hashes(source_paths)
    missing = [p for p in source_paths if p not in source_sha256]
    row: Dict[str, object] = {
        "path": path,
        "title": title,
        "kind": kind,
        "research_id": research_id,
        "html_sha256": hashlib.sha256(encoded).hexdigest(),
        "bytes": len(encoded),
        "source_paths": source_paths,
        "source_sha256": source_sha256,
        "trust": _WRITER,
        "missing": missing,
        "stale": bool(missing),
        "links": links,
    }
    if step_id:
        row["step_id"] = step_id
    return row


def build_manifest(
    files: Mapping[str, str],
    *,
    commit: Optional[str],
    generated_at: Optional[str] = None,
) -> Dict[str, object]:
    """Build the deterministic report manifest; does not write files."""
    rows = [
        _report_row(
            path="research_lab_report.html",
            title="알파 재시작 연구소 — 연구 리포트 허브",
            kind="hub",
            research_id="alpha_restart_20260710",
            html=files["research_lab_report.html"],
            source_paths=_source_paths_for_hub(),
            links=extract_report_links(files["research_lab_report.html"]),
        )
    ]
    for study in registry.STUDIES:
        rel = f"research/{study.id}.html"
        rows.append(
            _report_row(
                path=rel,
                title=f"{study.name} — 연구 상세",
                kind="study-detail",
                research_id=study.id,
                step_id=study.extractor,
                html=files[rel],
                source_paths=_source_paths_for_study(study),
                links=extract_report_links(files[rel]),
            )
        )

    return {
        "schema": _SCHEMA,
        "writer": _WRITER,
        "generated_at": generated_at or _utc_now(),
        "commit": commit or "미기록",
        "reports": rows,
    }


def _resolve_out_dir(value: str) -> Path:
    out_dir = Path(value)
    if out_dir.resolve() != _DEFAULT_OUT.resolve():
        raise ValueError(f"output is restricted to {_DEFAULT_OUT.as_posix()}")
    return out_dir


def _validate_report_paths(files: Mapping[str, str]) -> None:
    for rel in files:
        path = Path(rel)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != rel or not rel.lower().endswith(".html"):
            raise ValueError(f"unsafe report path: {rel!r}")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_reports_atomic(out_dir: Path, files: Mapping[str, str], manifest: Mapping[str, object]) -> None:
    _validate_report_paths(files)
    out_dir = out_dir.resolve()
    parent = out_dir.parent
    parent.mkdir(parents=True, exist_ok=True)
    staging: Optional[Path] = Path(tempfile.mkdtemp(prefix=f".{out_dir.name}.", dir=str(parent)))
    backup: Optional[Path] = None
    try:
        assert staging is not None
        for rel, html_text in files.items():
            _write_text(staging / rel, html_text)
        manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        _write_text(staging / _MANIFEST_NAME, manifest_text)

        if out_dir.exists():
            backup = Path(tempfile.mkdtemp(prefix=f".{out_dir.name}.backup.", dir=str(parent)))
            shutil.rmtree(backup)
            out_dir.replace(backup)
        staging.replace(out_dir)
        staging = None
        if backup is not None:
            shutil.rmtree(backup, ignore_errors=True)
    except Exception:
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)
        if backup is not None and backup.exists() and not out_dir.exists():
            backup.replace(out_dir)
        raise


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="계층형 연구 리포트 HTML 생성(허브 + 상세)")
    ap.add_argument("--out-dir", default=str(_DEFAULT_OUT),
                    help="고정 reports/ 디렉토리(허브 + research/<id>.html + manifest 생성)")
    ap.add_argument("--commit", default=None, help="생성 커밋 해시(미지정=미기록 — git 호출 금지)")
    ap.add_argument("--writer", default=_WRITER, choices=(_WRITER,), help="수동 오프라인 writer 전용")
    args = ap.parse_args(argv)

    try:
        out_dir = _resolve_out_dir(args.out_dir)
        files = build_all(commit=args.commit)
        manifest = build_manifest(files, commit=args.commit)
        write_reports_atomic(out_dir, files, manifest)
    except Exception as exc:  # noqa: BLE001 - CLI reports contract failures without partial writes.
        print(f"[REPORT][ERROR] {exc}", file=sys.stderr)
        return 2

    total = sum(len(text.encode("utf-8")) for text in files.values())
    print(f"[REPORT] {out_dir} · 파일 {len(files)}개(허브 1 + 상세 {len(files)-1}) + manifest · "
          f"총 {total:,} bytes · writer={args.writer} · commit={args.commit or '미기록'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
