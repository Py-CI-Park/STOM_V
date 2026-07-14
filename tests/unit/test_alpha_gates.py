# -*- coding: utf-8 -*-
"""A5 prereg-diff · A7 measure_gate 단위 테스트 (WBS v3 P1-2 / P1-3).

검증 대상:
- prereg_diff: 봉인 md 선언 추출 → 결과 json 대조. 픽스처 일치/변조 5종 검출/
  수동확인(MANUAL) 격리/선언 충돌 격리 + 실제 D1 봉인↔요약 스모크(read-only).
- measure_gate: tmp_path 에 subprocess 로 만든 **임시 git repo** 를 대상으로
  clean-pass / dirty / untracked / sha 불일치 / 봉인 문서 미커밋 분기 검증.

규율:
- gate 테스트의 git 은 전부 tmp repo 에만 실행한다 — ROOT 저장소 git 접근 0.
  (tmp repo 구성용 init/add/commit 은 테스트 픽스처 한정. 게이트 모듈 자체는
  읽기 전용 git 화이트리스트를 코드로 강제하며, 그 강제도 여기서 검증한다.)
- 모듈은 full path importlib 로 로드한다 — alpha_lab/discipline/__init__.py 는
  다른 작업(A1) 소유라 존재 여부에 의존하지 않는다.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_GIT = shutil.which("git")


def _load(name: str, rel: str):
    """alpha_lab/discipline 모듈을 파일 경로로 로드(패키지 초기화 비의존)."""
    spec = importlib.util.spec_from_file_location(name, str(ROOT / rel))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


prereg_diff = _load("t_alpha_discipline_prereg_diff",
                    "alpha_lab/discipline/prereg_diff.py")
measure_gate = _load("t_alpha_discipline_measure_gate",
                     "alpha_lab/discipline/measure_gate.py")

# ── prereg_diff 픽스처 ───────────────────────────────────────────────────────
_BUY_SHA = "0123456789abcdef" * 4          # 64 hex
_SELL_SHA = "deadbeef" + "0" * 56          # 64 hex (md 에는 축약 8자만 봉인)

_FIXTURE_MD = f"""# 테스트 봉인 사전등록 (픽스처)

buy_code_sha256 `{_BUY_SHA}`
표본: L1 서지 온셋 **12,345건**, sell_sha256 `deadbeef…`
| 2022-03-23 ~ 2023-12-31 | **발견 사용(DISCOVERY)** |
| 2024-01-01 ~ 2024-12-31 | 선정 창 포함(known) |
판정: BH-FDR q=0.10, 일자블록 부트스트랩(n_boot 400)
FDR 분모의 상한은 **7**로 봉인한다
효과크기 하한 ≥ +0.10%p
표본 하한: 양쪽 각 n ≥ 2,000 ∧ 연도별 각 ≥ 400
연도 세율 2022=0.23%/2023=0.20%
param_sha `cafe0123beef4567`
"""


def _fixture_json() -> dict:
    """픽스처 md 의 선언과 전부 일치하는 결과 json(변조 테스트의 기준본)."""
    return {
        "buy_sha256": _BUY_SHA,
        "sell_sha256": _SELL_SHA,
        "window": "2022-03-23~2023-12-31 (발견창)",
        "bank_meta": {"n_onsets_total": 12345},
        "consolidate": {"n_onsets": 12345},
        "gate": {"qualified": {"sealed_cap": 7, "fdr_denominator": 7}},
        "judgment": {
            "fdr_q": 0.1,
            "fdr_denominator": 6,
            "per_clause": {"1": {"n_boot": 400}, "2": {"n_boot": 400}},
        },
    }


def _entries_by_key(entries):
    return {e.key: e for e in entries}


def test_extract_declarations_fixture():
    decls = prereg_diff.extract_declarations(_FIXTURE_MD)
    by_key = {d.key: d.value for d in decls}
    assert by_key["buy_sha256"] == _BUY_SHA          # 축약 없이 전체값
    assert by_key["sell_sha256"] == "deadbeef"       # 축약 8자
    assert by_key["window_discovery"] == "2022-03-23~2023-12-31"
    assert by_key["window_other[2024-01-01~2024-12-31]"] == "2024-01-01~2024-12-31"
    assert by_key["n_onsets"] == "12345"
    assert by_key["n_boot"] == "400"
    assert by_key["fdr_q"] == "0.10"
    assert by_key["sealed_cap"] == "7"
    assert by_key["effect_floor_pp"] == "0.10"
    assert by_key["sample_floor_each"] == "2000"
    assert by_key["sample_floor_year"] == "400"
    assert by_key["tax_rate_2022"] == "0.23"
    assert by_key["tax_rate_2023"] == "0.20"
    assert by_key["param_sha"] == "cafe0123beef4567"


def test_compare_all_match_and_manual_isolated():
    decls = prereg_diff.extract_declarations(_FIXTURE_MD)
    entries = prereg_diff.compare(decls, _fixture_json())
    counts = prereg_diff.summarize(entries)
    assert counts["MISMATCH"] == 0
    by_key = _entries_by_key(entries)
    for key in ("buy_sha256", "sell_sha256", "window_discovery", "n_onsets",
                "n_boot", "fdr_q", "sealed_cap", "fdr_denominator≤sealed_cap"):
        assert by_key[key].status == "MATCH", key
    # 자동 매핑이 불확실한 선언은 MISMATCH 가 아니라 MANUAL 로 격리(오탐 최소화).
    for key in ("effect_floor_pp", "sample_floor_each", "sample_floor_year",
                "tax_rate_2022", "tax_rate_2023", "param_sha",
                "window_other[2024-01-01~2024-12-31]"):
        assert by_key[key].status == "MANUAL", key


def test_tamper_detection_five_kinds():
    """적대 변조 5종 — 각각 해당 키 MISMATCH 로 검출돼야 한다(A5 판정 조건 정신)."""
    decls = prereg_diff.extract_declarations(_FIXTURE_MD)
    tampers = {
        "buy_sha256": lambda d: d.__setitem__("buy_sha256", "f" * 64),
        "sell_sha256": lambda d: d.__setitem__("sell_sha256", "beefdead" + "0" * 56),
        "window_discovery": lambda d: d.__setitem__(
            "window", "2022-03-24~2023-12-31 (발견창)"),
        "n_boot": lambda d: d["judgment"]["per_clause"]["2"].__setitem__(
            "n_boot", 500),
        "fdr_q": lambda d: d["judgment"].__setitem__("fdr_q", 0.2),
    }
    for key, mutate in tampers.items():
        data = _fixture_json()
        mutate(data)
        entries = prereg_diff.compare(decls, data)
        assert _entries_by_key(entries)[key].status == "MISMATCH", key


def test_fdr_denominator_bound_violation_detected():
    data = _fixture_json()
    data["gate"]["qualified"]["fdr_denominator"] = 9  # 봉인 상한 7 초과
    entries = prereg_diff.compare(
        prereg_diff.extract_declarations(_FIXTURE_MD), data)
    assert _entries_by_key(entries)["fdr_denominator≤sealed_cap"].status == "MISMATCH"


def test_conflicting_declaration_goes_manual():
    md = _FIXTURE_MD + "\n재기재: n_boot 800\n"
    entries = prereg_diff.compare(
        prereg_diff.extract_declarations(md), _fixture_json())
    entry = _entries_by_key(entries)["n_boot"]
    assert entry.status == "MANUAL"
    assert "충돌" in entry.note


def test_missing_json_key_goes_manual_not_mismatch():
    data = _fixture_json()
    del data["judgment"]["per_clause"]  # n_boot 대응 키 제거
    entries = prereg_diff.compare(
        prereg_diff.extract_declarations(_FIXTURE_MD), data)
    entry = _entries_by_key(entries)["n_boot"]
    assert entry.status == "MANUAL"
    assert "대응 키 없음" in entry.note


def test_render_table_korean_summary():
    decls = prereg_diff.extract_declarations(_FIXTURE_MD)
    entries = prereg_diff.compare(decls, _fixture_json())
    text = prereg_diff.render_table(entries, "prereg.md", "result.json")
    assert "요약: MATCH" in text
    assert "MANUAL(수동 확인 필요)" in text


def test_run_diff_report_shape(tmp_path):
    md = tmp_path / "prereg.md"
    md.write_text(_FIXTURE_MD, encoding="utf-8")
    js = tmp_path / "summary.json"
    js.write_text(json.dumps(_fixture_json(), ensure_ascii=False),
                  encoding="utf-8")
    report = prereg_diff.run_diff(md, js)
    assert report["kind"] == "prereg_diff_report"
    assert report["counts"]["MISMATCH"] == 0
    assert report["counts"]["MATCH"] >= 8
    assert report["counts"]["MANUAL"] >= 7


# ── prereg_diff — 실제 D1 정본 스모크(read-only) ─────────────────────────────
_D1_MD = (ROOT / "docs" / "research" / "condition_research" / "plans"
          / "2026-07-12_d1_clause_ablation_preregistration.md")
_D1_JSON = (ROOT / "docs" / "research" / "condition_research" / "research_runs"
            / "alpha_restart_20260710" / "d1_clause_ablation_summary.json")


@pytest.mark.skipif(not (_D1_MD.exists() and _D1_JSON.exists()),
                    reason="D1 정본 파일 부재")
def test_prereg_diff_real_d1_no_mismatch():
    """첫 실전 적용 대상 D1: 봉인↔요약 자동 대조 전항 불일치 0 이어야 한다."""
    report = prereg_diff.run_diff(_D1_MD, _D1_JSON)
    counts = report["counts"]
    assert counts["MISMATCH"] == 0
    assert counts["MATCH"] >= 6
    match_keys = {e["key"] for e in report["entries"] if e["status"] == "MATCH"}
    assert {"buy_sha256", "sell_sha256", "window_discovery", "n_onsets",
            "n_boot", "fdr_q", "sealed_cap"} <= match_keys


# ── measure_gate — tmp git repo 픽스처 ───────────────────────────────────────
def _git_env(tmp_path: Path) -> dict:
    """글로벌/시스템 git 설정을 차단한 격리 환경(서명·autocrlf 간섭 배제)."""
    empty_cfg = tmp_path / "empty_gitconfig"
    if not empty_cfg.exists():
        empty_cfg.write_text("", encoding="utf-8")
    env = dict(os.environ)
    env.update({
        "GIT_CONFIG_GLOBAL": str(empty_cfg),
        "GIT_CONFIG_SYSTEM": str(empty_cfg),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CEILING_DIRECTORIES": str(tmp_path),
        "PYTHONIOENCODING": "utf-8",
    })
    return env


def _git(repo: Path, env: dict, *args: str) -> str:
    """테스트 픽스처 전용 git — tmp repo 에만 실행한다(ROOT 접근 금지)."""
    cp = subprocess.run(("git", "-C", str(repo)) + args, capture_output=True,
                        encoding="utf-8", errors="replace", env=env, timeout=60)
    assert cp.returncode == 0, f"git {args}: {cp.stderr}"
    return cp.stdout


@pytest.fixture
def sealed_repo(tmp_path):
    """봉인 문서+측정 코드가 커밋된 임시 repo (clean 기준 상태)."""
    if _GIT is None:
        pytest.skip("git 실행 파일 없음")
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "code").mkdir()
    sealed = repo / "docs" / "prereg_sealed.md"
    sealed.write_text("# 봉인 픽스처\n", encoding="utf-8")
    code = repo / "code" / "measure.py"
    code.write_text("VALUE = 1\n", encoding="utf-8")
    env = _git_env(tmp_path)
    _git(repo, env, "init", "-q")
    _git(repo, env, "add", "-A")
    _git(repo, env, "-c", "user.name=tester", "-c", "user.email=t@example.com",
         "commit", "-q", "-m", "init")
    return repo, sealed, code, env


def test_gate_pass_clean_committed(sealed_repo):
    repo, sealed, code, _ = sealed_repo
    result = measure_gate.run_gate(repo, sealed, (str(code),))
    assert result["gate_pass"] is True
    assert result["reasons"] == []
    doc = result["checks"]["sealed_doc"]
    assert len(doc["last_commit"]) == 40  # "측정 시점 코드"를 커밋 해시로 답변
    assert result["checks"]["sha_seal"]["checked"] is False


def test_gate_pass_with_sha_seal_full_and_prefix(sealed_repo):
    repo, sealed, code, _ = sealed_repo
    sha = measure_gate.file_sha256(code)
    for want in (sha, sha[:12]):  # 전체값·축약 접두 모두 허용
        result = measure_gate.run_gate(repo, sealed, (str(code),),
                                       {str(code): want})
        assert result["gate_pass"] is True
        assert result["checks"]["sha_seal"]["checked"] is True


def test_gate_fail_sha_mismatch(sealed_repo):
    repo, sealed, code, _ = sealed_repo
    result = measure_gate.run_gate(repo, sealed, (str(code),),
                                   {str(code): "0" * 64})
    assert result["gate_pass"] is False
    assert any("sha256 불일치" in r for r in result["reasons"])


def test_gate_fail_dirty_code(sealed_repo):
    repo, sealed, code, _ = sealed_repo
    code.write_text("VALUE = 2\n", encoding="utf-8")  # 미커밋 수정
    result = measure_gate.run_gate(repo, sealed, (str(code),))
    assert result["gate_pass"] is False
    assert any("미커밋 변경" in r for r in result["reasons"])


def test_gate_fail_untracked_code(sealed_repo):
    """O-1G 실사고 유형: 측정 코드가 untracked 인 채 배치 기동 → 거부."""
    repo, sealed, code, _ = sealed_repo
    extra = repo / "code" / "measure_extra.py"
    extra.write_text("VALUE = 3\n", encoding="utf-8")
    result = measure_gate.run_gate(repo, sealed, (str(code), str(extra)))
    assert result["gate_pass"] is False
    assert any("untracked" in r for r in result["reasons"])


def test_gate_fail_sealed_doc_not_committed(sealed_repo):
    repo, _, code, _ = sealed_repo
    draft = repo / "docs" / "prereg_draft.md"
    draft.write_text("# 미봉인 초안\n", encoding="utf-8")
    result = measure_gate.run_gate(repo, draft, (str(code),))
    assert result["gate_pass"] is False
    assert any("커밋 이력에 없음" in r for r in result["reasons"])


def test_gate_fail_sealed_doc_dirty(sealed_repo):
    """검증 실증 우회 조합 차단: 커밋된 봉인 문서를 로컬 변조(dirty)하면
    게이트가 거부한다 — '변조 봉인 기준 MATCH' 경로 봉쇄(하드닝)."""
    repo, sealed, code, _ = sealed_repo
    sealed.write_text("# 봉인 픽스처 (변조)\n", encoding="utf-8")  # 미커밋 수정
    result = measure_gate.run_gate(repo, sealed, (str(code),))
    assert result["gate_pass"] is False
    assert any("변조 의심" in r for r in result["reasons"])


def test_gate_fail_require_sha_without_record(sealed_repo):
    repo, sealed, code, _ = sealed_repo
    result = measure_gate.run_gate(repo, sealed, (str(code),), None,
                                   require_sha=True)
    assert result["gate_pass"] is False
    assert any("fail-closed" in r for r in result["reasons"])


def test_gate_fail_outside_repo(tmp_path, monkeypatch):
    if _GIT is None:
        pytest.skip("git 실행 파일 없음")
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "doc.md").write_text("x\n", encoding="utf-8")
    # 상위 디렉토리로의 repo 탐색을 차단해 환경 비의존적으로 non-repo 를 보장.
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    result = measure_gate.run_gate(plain, plain / "doc.md",
                                   (str(plain / "doc.md"),))
    assert result["gate_pass"] is False


def test_run_git_rejects_write_commands(sealed_repo):
    """읽기 전용 화이트리스트 강제 — 쓰기 git 은 모듈 차원에서 실행 불가."""
    repo, _, _, _ = sealed_repo
    for bad in (("commit", "-m", "x"), ("add", "-A"), ("push",),
                ("checkout", "."), ("reset", "--hard")):
        with pytest.raises(ValueError):
            measure_gate._run_git(repo, *bad)
    with pytest.raises(ValueError):  # status 는 --porcelain 강제
        measure_gate._run_git(repo, "status")

def _v2_seal_manifest(repo: Path, sealed: Path, code: Path, env: dict) -> Path:
    from alpha_lab.discipline.evidence import sha256_canonical

    manifest = {
        "schema_version": 2,
        "kind": "prereg_seal",
        "status": "SEALED",
        "sealed_at": "2026-07-14T00:00:00+00:00",
        "sealed_doc": {
            "path": sealed.relative_to(repo).as_posix(),
            "sha256": measure_gate.file_sha256(sealed),
        },
        "code_manifest": [{
            "path": code.relative_to(repo).as_posix(),
            "sha256": measure_gate.file_sha256(code),
        }],
    }
    path = repo / "seal.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":")), encoding="utf-8")
    _git(repo, env, "add", "seal.json")
    _git(repo, env, "-c", "user.name=tester", "-c", "user.email=t@example.com",
         "commit", "-q", "-m", "seal")
    assert sha256_canonical(json.loads(path.read_text(encoding="utf-8")))
    return path


def test_issue_and_claim_gate_receipt_v2_once(sealed_repo):
    repo, sealed, code, env = sealed_repo
    seal = _v2_seal_manifest(repo, sealed, code, env)
    receipt_path = repo / "receipt.json"
    receipt = measure_gate.issue_gate_receipt_v2(
        repo, seal, receipt_path=receipt_path,
        issued_at="2026-07-14T00:00:00+00:00", nonce="run-1")
    assert receipt["code_manifest"] == json.loads(
        seal.read_text(encoding="utf-8"))["code_manifest"]
    assert len(receipt["receipt_id"]) == 64
    usage_path = repo / "usage.json"
    usage = measure_gate.claim_gate_receipt_v2(
        receipt_path, repo_root=repo, usage_path=usage_path,
        consumer="measure-run-1", consumed_at="2026-07-14T00:01:00+00:00")
    assert usage["receipt_id"] == receipt["receipt_id"]
    original_usage = usage_path.read_bytes()
    with pytest.raises(ValueError):
        measure_gate.claim_gate_receipt_v2(
            receipt_path, repo_root=repo, usage_path=usage_path,
            consumer="measure-run-2", consumed_at="2026-07-14T00:02:00+00:00")
    assert usage_path.read_bytes() == original_usage


def test_claim_gate_receipt_v2_rejects_tampered_receipt_and_code(sealed_repo):
    repo, sealed, code, env = sealed_repo
    seal = _v2_seal_manifest(repo, sealed, code, env)
    receipt_path = repo / "receipt.json"
    measure_gate.issue_gate_receipt_v2(
        repo, seal, receipt_path=receipt_path,
        issued_at="2026-07-14T00:00:00+00:00", nonce="run-1")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["receipt_id"] = "0" * 64
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    usage_path = repo / "usage.json"
    with pytest.raises(ValueError):
        measure_gate.claim_gate_receipt_v2(
            receipt_path, repo_root=repo, usage_path=usage_path,
            consumer="measure-run-1", consumed_at="2026-07-14T00:01:00+00:00")
    assert not usage_path.exists()
    receipt_path.unlink()
    measure_gate.issue_gate_receipt_v2(
        repo, seal, receipt_path=receipt_path,
        issued_at="2026-07-14T00:00:00+00:00", nonce="run-2")
    code.write_text("VALUE = 99\n", encoding="utf-8")
    with pytest.raises(ValueError):
        measure_gate.claim_gate_receipt_v2(
            receipt_path, repo_root=repo, usage_path=usage_path,
            consumer="measure-run-1", consumed_at="2026-07-14T00:01:00+00:00")
    assert not usage_path.exists()


def test_issue_gate_receipt_v2_rejects_noncanonical_inputs_without_output(sealed_repo):
    repo, sealed, code, env = sealed_repo
    seal = _v2_seal_manifest(repo, sealed, code, env)
    raw = json.loads(seal.read_text(encoding="utf-8"))
    raw["code_manifest"][0]["sha256"] = raw["code_manifest"][0]["sha256"][:12]
    seal.write_text(json.dumps(raw), encoding="utf-8")
    receipt_path = repo / "receipt.json"
    with pytest.raises(ValueError):
        measure_gate.issue_gate_receipt_v2(
            repo, seal, receipt_path=receipt_path,
            issued_at="2026-07-14T00:00:00+00:00", nonce="run-1")
    assert not receipt_path.exists()


# ── CLI 래퍼(subprocess) 스모크 — 실행 대상은 전부 tmp ───────────────────────
def test_measure_gate_cli_pass_and_fail(sealed_repo, tmp_path):
    repo, sealed, code, env = sealed_repo
    script = ROOT / "scripts" / "measure_gate.py"
    out_json = tmp_path / "gate_result.json"
    base = [sys.executable, str(script), "--repo-root", str(repo),
            "--sealed-doc", str(sealed), "--code", str(code)]
    ok = subprocess.run(base + ["--json-out", str(out_json)],
                        capture_output=True, encoding="utf-8",
                        errors="replace", env=env, timeout=120)
    assert ok.returncode == 0, ok.stderr
    assert json.loads(ok.stdout)["gate_pass"] is True
    assert json.loads(out_json.read_text(encoding="utf-8"))["gate_pass"] is True

    fail = subprocess.run(base + ["--expect", f"{code}={'0' * 64}"],
                          capture_output=True, encoding="utf-8",
                          errors="replace", env=env, timeout=120)
    assert fail.returncode == 1
    assert json.loads(fail.stdout)["gate_pass"] is False


def test_prereg_diff_cli_smoke(tmp_path):
    md = tmp_path / "prereg.md"
    md.write_text(_FIXTURE_MD, encoding="utf-8")
    js = tmp_path / "summary.json"
    js.write_text(json.dumps(_fixture_json(), ensure_ascii=False),
                  encoding="utf-8")
    out_json = tmp_path / "diff_report.json"
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "prereg_diff.py"),
         "--prereg", str(md), "--result", str(js), "--json-out", str(out_json)],
        capture_output=True, encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"}, timeout=120)
    assert cp.returncode == 0, cp.stderr
    assert "요약: MATCH" in cp.stdout
    report = json.loads(out_json.read_text(encoding="utf-8"))
    assert report["counts"]["MISMATCH"] == 0
