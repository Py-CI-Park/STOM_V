"""G005 — 연구 프로그램 단계별 성숙도 자동 스코어카드.

`build_scorecard(repo_root=None)`는 저장소를 9개 연구 파이프라인 단계로 나누고, 각
단계를 파일 존재·설정값·상태 DB 행수 같은 **실측 가능한 결정론 신호**로 채점한다.
테스트를 실행하거나 코드를 import/실행하지 않는다 — 소스 텍스트/AST 파싱, 파일
존재 확인, 읽기전용(mode=ro) SQLite 쿼리만 사용한다. 같은 저장소 상태에서는
`generated_at`을 제외한 모든 필드가 항상 동일하게 나온다(결정론 계약).

무예외 계약: 신호 하나가 수집 실패해도(파일 없음/파싱 실패/DB 없음) 그 신호는
0점 + note로 흡수될 뿐, `build_scorecard` 자체가 예외를 던지는 일은 없다.

한계(정직 고지 — 아키텍트 리뷰 반영): 신호 다수가 **존재 기반**(파일/라우트/행수)이라
빈 파일·형식만 갖춘 아티팩트·가짜 행 삽입으로 개별 단계 점수를 부풀릴 수 있다. 이
도구는 자기 저장소용 advisory 지표이지 감사 증명이 아니다 — 행 품질/계보 검증은
증거 원장(EvidenceStore)과 CL-R 게이트가 담당한다. 단 예외 하나: `수익증명` 단계는
어떤 파일/문서 조작으로도 오르지 않는 하드코드 0점이며(레드팀 E2 실증), CL-R08~R10
완료가 별도 승인·증거로 확정된 뒤 코드 개정으로만 열린다.

CLI:
    python scripts/research_maturity_scorecard.py [--out PATH]

    JSON을 --out(기본 ai_strategy_loop/state/research_maturity.json)에 쓰고,
    마크다운 단계별 표를 stdout에 출력한다. 항상 exit 0.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

SCHEMA = "research_maturity_v1"

# 이 파일 위치 기준 저장소 루트(scripts/의 부모).
_DEFAULT_REPO_ROOT = Path(__file__).resolve().parent.parent


def _signal(name: str, value: Any, points: int, max_points: int, note: str) -> Dict[str, Any]:
    points = max(0, min(int(points), int(max_points)))
    return {
        "name": name,
        "value": value,
        "points": points,
        "max_points": int(max_points),
        "note": note,
    }


def _stage(stage_id: str, label: str, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
    max_score = sum(s["max_points"] for s in signals) or 100
    score = round(sum(s["points"] for s in signals) / max_score * 100)
    return {
        "id": stage_id,
        "label": label,
        "score": max(0, min(score, 100)),
        "signals": signals,
        "max_score": 100,
    }


def _file_signal(name: str, path: Path, max_points: int, ok_note: str, missing_note: str) -> Dict[str, Any]:
    try:
        ok = path.is_file()
    except OSError:
        ok = False
    return _signal(name, ok, max_points if ok else 0, max_points, ok_note if ok else missing_note)


def _safe_stage(builder, repo_root: Path, stage_id: str, label: str, max_signal_points: int) -> Dict[str, Any]:
    """스테이지 빌더를 무예외로 실행한다 — 예외 시 전 신호 0점 + note로 흡수."""
    try:
        return builder(repo_root)
    except Exception as exc:  # noqa: BLE001 - 신호 수집 실패는 0점+note로 흡수(무예외 계약).
        return _stage(
            stage_id,
            label,
            [_signal("collection_error", str(exc), 0, max_signal_points, f"signal collection raised: {exc}")],
        )


def _read_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _literal_assign(path: Path, target_name: str) -> Any:
    """path의 모듈 레벨 `target_name = <literal>` 대입값을 실행 없이 파싱한다."""
    text = _read_text(path)
    if text is None:
        return None
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
        else:
            continue
        for tgt in targets:
            if isinstance(tgt, ast.Name) and tgt.id == target_name:
                try:
                    return ast.literal_eval(node.value)
                except (ValueError, TypeError, SyntaxError):
                    return None
    return None


def _defined_functions(path: Path) -> set:
    text = _read_text(path)
    if text is None:
        return set()
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return set()
    return {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


# ---------------------------------------------------------------------------
# Stage 1 — 엔진계약
# ---------------------------------------------------------------------------


def _stage_engine_contract(repo_root: Path) -> Dict[str, Any]:
    signals = [
        _file_signal(
            "backengine_kiwoom_tick_present",
            repo_root / "backtest" / "backengine_kiwoom_tick.py",
            34,
            "backtest/backengine_kiwoom_tick.py exists",
            "backtest/backengine_kiwoom_tick.py missing",
        ),
        _file_signal(
            "back_static_present",
            repo_root / "backtest" / "back_static.py",
            33,
            "backtest/back_static.py exists",
            "backtest/back_static.py missing",
        ),
        _file_signal(
            "verify_nonrelease_sync_present",
            repo_root / "scripts" / "verify_nonrelease_sync.py",
            33,
            "scripts/verify_nonrelease_sync.py exists",
            "scripts/verify_nonrelease_sync.py missing",
        ),
    ]
    return _stage("engine_contract", "엔진계약", signals)


# ---------------------------------------------------------------------------
# Stage 2 — 생성 (brain/prompt.py 자산 + build_messages 파라미터)
# ---------------------------------------------------------------------------

_CORE_DOMAIN_ASSETS = ("principles", "constraints_checklist", "idiom_dictionary", "composite_examples")
_ASSET_NAME_RE = re.compile(r'\(\s*"(\w+)"\s*,')


def _asset_path_for(repo_root: Path, name: str) -> Path:
    if name in ("strategy", "rules"):
        return repo_root / "utility" / "ai_agent" / f"{name}.txt"
    return repo_root / "utility" / "ai_agent" / "system_prompt" / "v1" / f"{name}.md"


def _stage_generation(repo_root: Path) -> Dict[str, Any]:
    prompt_path = repo_root / "ai_strategy_loop" / "brain" / "prompt.py"
    text = _read_text(prompt_path)
    if text is None:
        signals = [
            _signal("full_stom_source_assets_present", None, 0, 40, "ai_strategy_loop/brain/prompt.py missing"),
            _signal("core_domain_assets_present", None, 0, 40, "ai_strategy_loop/brain/prompt.py missing"),
            _signal(
                "build_messages_structure_principles_param", None, 0, 20,
                "ai_strategy_loop/brain/prompt.py missing",
            ),
        ]
        return _stage("generation", "생성", signals)

    m = re.search(r"_FULL_STOM_SOURCE_ASSETS\s*=\s*\((.*?)\n\)\n", text, re.S)
    names = _ASSET_NAME_RE.findall(m.group(1)) if m else []

    existing = [n for n in names if _asset_path_for(repo_root, n).is_file()]
    full_frac = (len(existing) / len(names)) if names else 0.0
    points_full = round(full_frac * 40)
    note_full = (
        f"{len(existing)}/{len(names)} _FULL_STOM_SOURCE_ASSETS resolved on disk"
        if names else "_FULL_STOM_SOURCE_ASSETS tuple not found/parsed in prompt.py"
    )

    core_present = [n for n in _CORE_DOMAIN_ASSETS if n in names and _asset_path_for(repo_root, n).is_file()]
    core_frac = len(core_present) / len(_CORE_DOMAIN_ASSETS)
    points_core = round(core_frac * 40)
    missing_core = sorted(set(_CORE_DOMAIN_ASSETS) - set(core_present))
    note_core = (
        "principles/constraints_checklist/idiom_dictionary/composite_examples all present"
        if not missing_core else f"missing core assets: {missing_core}"
    )

    has_def = bool(re.search(r"def\s+build_messages\s*\(", text))
    has_param = has_def and bool(re.search(r"structure_principles_prompt_enabled\s*:\s*bool", text))
    note_param = (
        "build_messages() declares structure_principles_prompt_enabled"
        if has_param else "structure_principles_prompt_enabled parameter not found in build_messages()"
    )

    signals = [
        _signal("full_stom_source_assets_present", f"{len(existing)}/{len(names)}", points_full, 40, note_full),
        _signal("core_domain_assets_present", f"{len(core_present)}/{len(_CORE_DOMAIN_ASSETS)}",
                 points_core, 40, note_core),
        _signal("build_messages_structure_principles_param", has_param, 20 if has_param else 0, 20, note_param),
    ]
    return _stage("generation", "생성", signals)


# ---------------------------------------------------------------------------
# Stage 3 — 게이트
# ---------------------------------------------------------------------------

_GATE_MODULES = ("variable_scope", "token_check", "filter_gate", "exec_budget", "principle_gate")


def _stage_gates(repo_root: Path) -> Dict[str, Any]:
    signals = [
        _file_signal(
            f"gate_module_{mod}_present",
            repo_root / "ai_strategy_loop" / "brain" / f"{mod}.py",
            15,
            f"ai_strategy_loop/brain/{mod}.py exists",
            f"ai_strategy_loop/brain/{mod}.py missing",
        )
        for mod in _GATE_MODULES
    ]
    signals.append(
        _file_signal(
            "g2_gate_false_reject_audit_present",
            repo_root / "artifacts" / "g2_gate_false_reject_audit.json",
            25,
            "artifacts/g2_gate_false_reject_audit.json exists (audit performed)",
            "artifacts/g2_gate_false_reject_audit.json missing — false-reject audit not performed",
        )
    )
    return _stage("gates", "게이트", signals)


# ---------------------------------------------------------------------------
# Stage 4 — 채점
# ---------------------------------------------------------------------------


def _stage_scoring(repo_root: Path) -> Dict[str, Any]:
    score_path = repo_root / "ai_strategy_loop" / "fitness" / "score.py"
    funcs = _defined_functions(score_path)
    text = _read_text(score_path) or ""
    has_compute_fitness = "compute_fitness" in funcs
    has_graded = "compute_graded_fitness" in funcs
    # 아키텍트 리뷰 MEDIUM 반영: regex 단어경계는 언더스코어 식별자에서 위음성
    #   (compute_pbo 등 미매치) — 이미 수집한 함수명 집합의 substring 판정으로 통일.
    deflated_implemented = any("deflated_sharpe" in f.lower() for f in funcs)
    pbo_implemented = any("pbo" in f.lower() for f in funcs)
    dsr_pbo_implemented = deflated_implemented and pbo_implemented

    signals = [
        _signal(
            "compute_fitness_present", has_compute_fitness, 30 if has_compute_fitness else 0, 30,
            "compute_fitness symbol present" if has_compute_fitness else "compute_fitness symbol missing",
        ),
        _signal(
            "compute_graded_fitness_present", has_graded, 30 if has_graded else 0, 30,
            "compute_graded_fitness symbol present" if has_graded else "compute_graded_fitness symbol missing",
        ),
        _signal(
            "deflated_sharpe_pbo_implemented", dsr_pbo_implemented, 40 if dsr_pbo_implemented else 0, 40,
            "Deflated Sharpe/PBO graded terms implemented" if dsr_pbo_implemented else
            "Deflated Sharpe/PBO not implemented in fitness/score.py — "
            "docs/update_log 2026-07-12 P1 plan (CL-R08 companion work), still pending",
        ),
    ]
    return _stage("scoring", "채점", signals)


# ---------------------------------------------------------------------------
# Stage 5 — 부검/환류
# ---------------------------------------------------------------------------


def _stage_autopsy_feedback(repo_root: Path) -> Dict[str, Any]:
    targets = [
        ("autopsy_analyze_present", repo_root / "ai_strategy_loop" / "autopsy" / "analyze.py",
         "ai_strategy_loop/autopsy/analyze.py"),
        ("autopsy_trade_quant_present", repo_root / "ai_strategy_loop" / "autopsy" / "trade_quant.py",
         "ai_strategy_loop/autopsy/trade_quant.py"),
        ("brain_segment_feedback_present", repo_root / "ai_strategy_loop" / "brain" / "segment_feedback.py",
         "ai_strategy_loop/brain/segment_feedback.py"),
        ("fitness_edge_ratio_present", repo_root / "ai_strategy_loop" / "fitness" / "edge_ratio.py",
         "ai_strategy_loop/fitness/edge_ratio.py"),
    ]
    signals = [
        _file_signal(name, path, 25, f"{label} exists", f"{label} missing")
        for name, path, label in targets
    ]
    return _stage("autopsy_feedback", "부검/환류", signals)


# ---------------------------------------------------------------------------
# Stage 6 — 증거원장
# ---------------------------------------------------------------------------


def _ro_table_count(db_path: Path, table: str) -> Optional[int]:
    """읽기전용(mode=ro) URI로 table의 행수를 센다. 실패/부재면 None."""
    if not db_path.is_file():
        return None
    uri = f"file:{db_path.as_posix()}?mode=ro"
    try:
        con = sqlite3.connect(uri, uri=True)
        try:
            row = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # noqa: S608 - fixed table names.
            return int(row[0]) if row else None
        finally:
            con.close()
    except sqlite3.Error:
        return None


def _stage_evidence_ledger(repo_root: Path) -> Dict[str, Any]:
    signals = [
        _file_signal(
            "evidence_store_present",
            repo_root / "ai_strategy_loop" / "controller" / "evidence_store.py",
            30,
            "ai_strategy_loop/controller/evidence_store.py exists",
            "ai_strategy_loop/controller/evidence_store.py missing",
        ),
    ]
    db_path = repo_root / "ai_strategy_loop" / "state" / "loop_runs.db"
    for name, table, max_points in (
        ("candidate_passports_row_count", "candidate_passports", 35),
        ("feedback_envelopes_row_count", "feedback_envelopes", 35),
    ):
        count = _ro_table_count(db_path, table)
        if count is None:
            signals.append(_signal(name, None, 0, max_points, f"{table}: state DB/table unreadable or absent"))
        elif count == 0:
            signals.append(
                _signal(name, 0, 5, max_points, f"{table}: 0 rows — ledger not yet populated (CL-R08 locked)")
            )
        else:
            signals.append(_signal(name, count, max_points, max_points, f"{table}: {count} rows recorded"))
    return _stage("evidence_ledger", "증거원장", signals)


# ---------------------------------------------------------------------------
# Stage 7 — 프로필/토글
# ---------------------------------------------------------------------------

# tests/unit/test_research_profile_wiring.py를 파싱할 수 없을 때의 정본 ON 키 폴백
# (2026-07-12 기준 _CANONICAL_ON_KEYS와 동일 — 테스트 파일이 정본이며, 이건 안전망일 뿐).
_FALLBACK_CANONICAL_ON_KEYS = (
    "sparse_positive_prompt_enabled", "exec_budget_prompt_enabled", "report_principles_enabled",
    "structure_principles_prompt_enabled", "require_filter_gates", "few_shot_enabled",
    "sell_exec_budget_guard_enabled", "mdd_control_enabled", "exit_edge_feedback_enabled",
    "principle_gate_enabled", "evidence_ledger_enabled", "segment_feedback_enabled",
    "quantile_feedback_enabled", "counterfactual_feedback_enabled", "hypothesis_tracking_enabled",
    "feature_importance_feedback_enabled", "exit_forensics_feedback_enabled", "meta_seed_enabled",
    "dispersion_prompt_enabled", "dispersion_enabled",
)


def _stage_profiles_toggles(repo_root: Path) -> Dict[str, Any]:
    test_path = repo_root / "tests" / "unit" / "test_research_profile_wiring.py"
    canonical = _literal_assign(test_path, "_CANONICAL_ON_KEYS")
    source_note = "reused _CANONICAL_ON_KEYS from tests/unit/test_research_profile_wiring.py"
    source_resolved = bool(canonical)
    if not canonical:
        canonical = _FALLBACK_CANONICAL_ON_KEYS
        source_note = "test file unavailable/unparsable — used embedded fallback canonical ON key set"

    presets_path = repo_root / "ai_strategy_loop" / "scripts" / "research_presets.py"
    common = _literal_assign(presets_path, "_COMMON_DISCOVERY") or {}

    matched = [k for k in canonical if common.get(k) is True]
    frac = (len(matched) / len(canonical)) if canonical else 0.0
    points = round(frac * 90)

    signals = [
        _signal(
            "canonical_on_keys_source_resolved", source_note, 10 if source_resolved else 0, 10, source_note
        ),
        _signal(
            "common_discovery_on_key_coverage", f"{len(matched)}/{len(canonical)}", points, 90,
            "all canonical ON keys are True in _COMMON_DISCOVERY" if len(matched) == len(canonical) and canonical
            else f"missing/false canonical keys: {sorted(set(canonical) - set(matched))}",
        ),
    ]
    return _stage("profiles_toggles", "프로필/토글", signals)


# ---------------------------------------------------------------------------
# Stage 8 — 대시보드
# ---------------------------------------------------------------------------


def _stage_dashboard(repo_root: Path) -> Dict[str, Any]:
    app_path = repo_root / "ai_strategy_loop" / "dashboard" / "app.py"
    text = _read_text(app_path) or ""
    routes = ("/trade_quant", "/research_maturity", "/edge_ratio")
    signals = []
    for route in routes:
        needle = f'@app.get("{route}")'
        present = needle in text
        signals.append(
            _signal(
                f"route_{route.strip('/')}_present", present, 20 if present else 0, 20,
                f'{needle} present in dashboard/app.py' if present else f'{needle} not found in dashboard/app.py',
            )
        )
    signals.append(
        _file_signal(
            "frontend_v4_loop_cycle_present",
            repo_root / "ai_strategy_loop" / "dashboard" / "frontend" / "v4-loop-cycle.jsx",
            40,
            "ai_strategy_loop/dashboard/frontend/v4-loop-cycle.jsx exists",
            "ai_strategy_loop/dashboard/frontend/v4-loop-cycle.jsx missing",
        )
    )
    return _stage("dashboard", "대시보드", signals)


# ---------------------------------------------------------------------------
# Stage 9 — 수익증명 (0점 고정 — 정직 신호)
# ---------------------------------------------------------------------------


def _stage_profit_proof(repo_root: Path) -> Dict[str, Any]:
    update_log_dir = repo_root / "docs" / "update_log"
    mentions = 0
    try:
        if update_log_dir.is_dir():
            for path in update_log_dir.glob("*.md"):
                text = _read_text(path) or ""
                if re.search(r"CL-R0[89]|CL-R10", text):
                    mentions += 1
    except OSError:
        mentions = 0
    signals = [
        _signal(
            "cl_r08_r09_r10_completion_recorded",
            False,
            0,
            100,
            "CL-R08/R09/R10(수익 검증 게이트)의 완료를 이 도구가 검증한 기록은 없다"
            f"(docs/update_log에서 관련 언급 문서 {mentions}건 발견 — 내용의 완료/보류 여부는 "
            "이 스캔이 판정하지 않으며 점수에도 무관). "
            "이 단계 점수는 승인 게이트 설계에 따른 하드코드 0점(정직 신호)이다.",
        )
    ]
    return _stage("profit_proof", "수익증명", signals)


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

_STAGE_BUILDERS = (
    (_stage_engine_contract, "engine_contract", "엔진계약", 100),
    (_stage_generation, "generation", "생성", 100),
    (_stage_gates, "gates", "게이트", 100),
    (_stage_scoring, "scoring", "채점", 100),
    (_stage_autopsy_feedback, "autopsy_feedback", "부검/환류", 100),
    (_stage_evidence_ledger, "evidence_ledger", "증거원장", 100),
    (_stage_profiles_toggles, "profiles_toggles", "프로필/토글", 100),
    (_stage_dashboard, "dashboard", "대시보드", 100),
    (_stage_profit_proof, "profit_proof", "수익증명", 100),
)


def _render_markdown(overall_score: int, stages: List[Dict[str, Any]]) -> str:
    lines = [
        "# 연구 프로그램 성숙도 스코어카드",
        "",
        f"**전체 점수: {overall_score}/100**",
        "",
        "| 단계 | 점수 | 신호 |",
        "|---|---:|---|",
    ]
    for st in stages:
        signal_summary = ", ".join(f"{s['name']}={s['points']}/{s['max_points']}" for s in st["signals"])
        lines.append(f"| {st['label']} | {st['score']}/100 | {signal_summary} |")
    lines.append("")
    return "\n".join(lines)


def build_scorecard(repo_root: Optional[str] = None) -> Dict[str, Any]:
    """저장소를 스캔해 9단계 연구 성숙도 스코어카드를 계산한다. 무예외."""
    try:
        root = Path(repo_root).resolve() if repo_root is not None else _DEFAULT_REPO_ROOT
    except (OSError, TypeError, ValueError):
        root = _DEFAULT_REPO_ROOT

    stages = [
        _safe_stage(builder, root, stage_id, label, max_points)
        for builder, stage_id, label, max_points in _STAGE_BUILDERS
    ]
    overall = round(sum(s["score"] for s in stages) / len(stages)) if stages else 0

    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_score": max(0, min(overall, 100)),
        "stages": stages,
        "markdown": _render_markdown(overall, stages),
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=str(_DEFAULT_REPO_ROOT / "ai_strategy_loop" / "state" / "research_maturity.json"),
        help="Output JSON path (default: ai_strategy_loop/state/research_maturity.json)",
    )
    parser.add_argument("--repo-root", default=None, help="Repository root override (default: auto-detected)")
    args = parser.parse_args(argv)

    scorecard = build_scorecard(args.repo_root)

    out_path = Path(args.out)
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(scorecard, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        print(f"warning: could not write {out_path}: {exc}", file=sys.stderr)

    print(scorecard["markdown"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
