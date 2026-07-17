"""테이블 적재기 4종(clauses·strategies·cells·ledger_mirror) — 방어적 파싱.

각 원천의 실측 스키마(2026-07-12 확인)를 기준으로 하되, 필드 누락은 영수증에
기록하고 계속 진행한다. sqlite 원천은 URI mode=ro로만 연다(원본 무변형).
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from alpha_lab.catalog.sources import add_note, record_source
from alpha_lab.discipline import ledger as authority_ledger

# ---------------------------------------------------------------------------
# ledger_mirror — n_trials_ledger.jsonl 미러(row_num = 물리 행 번호 1-기반).
# ---------------------------------------------------------------------------

def load_ledger_mirror(
    con: sqlite3.Connection, run_dir: Path, receipt: Dict[str, Any], *, strict: bool = False,
) -> List[Tuple[int, dict]]:
    """장부 jsonl을 미러 적재하고 (행번호, 원본객체) 목록을 돌려준다."""
    rel = "n_trials_ledger.jsonl"
    path = Path(run_dir) / rel
    rows: List[Tuple[int, dict]] = []
    if not path.is_file():
        receipt["missing"].append(rel)
        receipt["sources"].append({"path": rel, "status": "missing"})
        return rows
    if strict:
        try:
            authority_ledger.read_all(path)
        except authority_ledger.LedgerSchemaError as exc:
            raise ValueError(f"strict ledger validation failed: {exc}") from exc
    for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1):
        text = line.strip()
        if not text:
            continue
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as exc:
            receipt["skipped"].append(
                {"path": rel, "reason": f"{lineno}행 json 파싱 실패: {exc}"})
            continue
        rows.append((lineno, obj))
        con.execute(
            "INSERT OR REPLACE INTO ledger_mirror "
            "(row_num, ts, series, window, trial_type, target, result, session,"
            " raw_json) VALUES (?,?,?,?,?,?,?,?,?)",
            (lineno, obj.get("ts"), obj.get("series"), obj.get("window"),
             obj.get("trial_type"), obj.get("target"), obj.get("result"),
             obj.get("session"), json.dumps(obj, ensure_ascii=False)),
        )
    record_source(receipt, run_dir, path)
    return rows


# ---------------------------------------------------------------------------
# clauses — d1_clause_ablation_summary.json judgment.per_clause 미러.
# ---------------------------------------------------------------------------

_CLAUSE_MAPPED = frozenset({
    "num", "text", "family", "cat", "tier", "n_sat", "n_unsat", "delta_pp",
    "ci_low_pp", "ci_high_pp", "mde_pp", "p_one_sided", "p_two_sided",
    "both_year_positive", "both_year_negative", "floor_pass", "fdr_survive",
    "classification", "year_delta",
})


def _classification_fallback(judgment: dict) -> Dict[int, str]:
    """per_clause에 분류 필드가 없을 때 쓸 판정부 num 목록 기반 분류 사전."""
    fallback: Dict[int, str] = {}
    lists = (("load_bearing_nums", "load_bearing"),
             ("counter_productive_nums", "counter_productive"),
             ("weak_signal_nums", "weak_signal"),
             ("inconclusive_nums", "inconclusive"))
    for key, label in lists:
        for num in judgment.get(key) or []:
            try:
                fallback[int(num)] = label
            except (TypeError, ValueError):
                continue
    return fallback


def load_clauses(
    con: sqlite3.Connection, d1: Optional[dict], receipt: Dict[str, Any],
) -> None:
    """D1 절별 전 수치 적재 — 분류 누락 시 판정부 목록→'unclassified(누락)' 순."""
    if d1 is None:
        return
    judgment = d1.get("judgment") or {}
    per = judgment.get("per_clause") or {}
    if not per:
        receipt["skipped"].append({
            "path": "d1_clause_ablation_summary.json",
            "reason": "judgment.per_clause 없음 — clauses 적재 생략",
        })
        return
    fallback = _classification_fallback(judgment)
    n_no_class = 0
    n_fallback = 0
    for key in sorted(per, key=lambda k: int(k)):
        c = per[key] or {}
        num = int(c.get("num", key))
        classification = c.get("classification")
        if not classification:
            classification = fallback.get(num)
            if classification:
                n_fallback += 1
            else:
                classification = "unclassified(누락)"
                n_no_class += 1
        extra = {k: v for k, v in c.items() if k not in _CLAUSE_MAPPED}
        con.execute(
            "INSERT OR REPLACE INTO clauses (clause_num, text, family,"
            " w5_category, tier, n_sat, n_unsat, delta_pp, ci_low_pp,"
            " ci_high_pp, mde_pp, p_one_sided, p_two_sided,"
            " both_year_positive, both_year_negative, floor_pass,"
            " fdr_survive, classification, year_delta_json, extra_json)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (num, str(c.get("text", "")), c.get("family"),
             c.get("cat"), c.get("tier"), c.get("n_sat"), c.get("n_unsat"),
             c.get("delta_pp"), c.get("ci_low_pp"), c.get("ci_high_pp"),
             c.get("mde_pp"), c.get("p_one_sided"), c.get("p_two_sided"),
             _b(c.get("both_year_positive")), _b(c.get("both_year_negative")),
             _b(c.get("floor_pass")), _b(c.get("fdr_survive")),
             classification,
             json.dumps(c.get("year_delta"), ensure_ascii=False),
             json.dumps(extra, ensure_ascii=False)),
        )
    _note_missing_clause_nums(per, n_no_class, n_fallback, receipt)


def _note_missing_clause_nums(
    per: dict, n_no_class: int, n_fallback: int, receipt: Dict[str, Any],
) -> None:
    """절 스펙 39종 대비 per_clause 미포함 절 번호를 영수증에 기록."""
    try:
        nums = {int(k) for k in per}
    except (TypeError, ValueError):
        return
    if nums and max(nums) <= 39:
        absent = sorted(set(range(1, 40)) - nums)
        if absent:
            add_note(receipt, (
                f"clauses: per_clause 실측 {len(nums)}건 — 절 스펙 39종 중 "
                f"미포함 절 번호 {absent}(원천 그대로 적재, 문서 표기 39절과 차이)"))
    if n_fallback:
        add_note(receipt, (
            f"clauses: per_clause classification 필드 부재 {n_fallback}건 — "
            "판정부 num 목록(inconclusive_nums 등)으로 분류 보강"))
    if n_no_class:
        add_note(receipt, f"clauses: classification 판별 불가 {n_no_class}건 — 'unclassified(누락)' 표기")


def _b(v: Any) -> Optional[int]:
    """bool류를 0/1 정수로(None은 그대로)."""
    if v is None:
        return None
    return 1 if v else 0


# ---------------------------------------------------------------------------
# strategies — w2 랭킹 4개 섹션 union + B1 역사적 영수증 1행 + sha 보강.
# ---------------------------------------------------------------------------

_W2_SECTIONS: Tuple[Tuple[str, str], ...] = (
    ("alp_v4_champions", "strategy"),
    ("engine_top40_by_total_return", "strategy"),
    ("engine_top20_by_annualized", "strategy"),
    ("human_hall_of_fame", "id"),
)
_HUMAN_TAG = "외부 벤치마크·원문 없음 확정·절 파싱 금지(전당 목표선)"


def load_strategies(
    con: sqlite3.Connection, w2: Optional[dict], d1: Optional[dict],
    b1: Optional[dict], receipt: Dict[str, Any],
) -> None:
    """W2 랭킹 union 적재 후 B1 역사적·비권위 행 추가·RR8_12 원문 sha 보강."""
    if w2 is not None:
        merged = _merge_w2_sections(w2, receipt)
        legacy = set(
            ((w2.get("api_compat") or {}).get("stockbuy") or {}).get("legacy_names") or [])
        for name, ent in merged.items():
            con.execute(
                "INSERT OR REPLACE INTO strategies (name, source_section,"
                " family, rank_by_total, total_return_pct, annual_return_pct,"
                " monthly_return_pct, mdd_pct, win_rate, payoff, trades,"
                " api_compat, source_sha256, lineage, rank_metrics_json,"
                " status_tag) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                _strategy_row(name, ent, legacy),
            )
        add_note(receipt, (
            "strategies.api_compat: 'legacy(실측)'는 w2 legacy_names 일치,"
            " 나머지 엔진 전략은 'current(잔여 추정)' — w2 json에 전략별 명시 필드 없음"))
        add_note(receipt, "strategies.source_sha256: w2 json에 원문 sha 부재 — B1 영수증·D1 요약에서만 보강")
    _insert_b1_strategy(con, b1, receipt)
    _enrich_rr8_12_sha(con, d1, receipt)


def _merge_w2_sections(w2: dict, receipt: Dict[str, Any]) -> Dict[str, dict]:
    """섹션 4종을 이름 기준 union — 첫 등장 섹션이 대표 지표를 제공한다."""
    merged: Dict[str, dict] = {}
    for section, key in _W2_SECTIONS:
        rows = w2.get(section)
        if not isinstance(rows, list):
            receipt["skipped"].append(
                {"path": "w2_strategy_inventory.json", "reason": f"{section} 섹션 없음"})
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = str(row.get(key) or "").strip()
            if not name:
                receipt["skipped"].append(
                    {"path": "w2_strategy_inventory.json",
                     "reason": f"{section} 내 이름({key}) 없는 행 1건 생략"})
                continue
            ent = merged.setdefault(
                name, {"primary": row, "primary_section": section, "rows": {}})
            ent["rows"][section] = row
    return merged


def _strategy_row(name: str, ent: dict, legacy: set) -> tuple:
    """strategies INSERT 값 튜플 — 인간 전당/엔진 필드명 차이를 흡수."""
    r = ent["primary"]
    section = ent["primary_section"]
    is_human = section == "human_hall_of_fame"
    if is_human:
        api = "원문없음(외부 벤치마크)"
    elif name in legacy:
        api = "legacy(실측 — 현행 엔진 실행 불가)"
    else:
        api = "current(잔여 추정)"
    return (
        name, ",".join(ent["rows"].keys()), r.get("family"),
        r.get("rank_by_total"), r.get("total_return_pct"),
        r.get("annual_return_pct"), r.get("monthly_return_pct"),
        r.get("mdd_pct"), r.get("win_rate", r.get("win_rate_pct")),
        r.get("payoff_tpi", r.get("payoff")), r.get("trades"), api, None,
        r.get("lineage"), json.dumps(ent["rows"], ensure_ascii=False),
        _HUMAN_TAG if is_human else None,
    )


def _insert_b1_strategy(
    con: sqlite3.Connection, b1: Optional[dict], receipt: Dict[str, Any],
) -> None:
    """B1 역사적 영수증에서 비권위 행을 추가한다(랭킹·승격 근거 아님)."""
    if b1 is None:
        return
    inserted = ((b1.get("register") or {}).get("inserted") or [{}])[0]
    name = str(b1.get("name") or inserted.get("name") or "ALP_D5R_B1_S")
    sha = {k: inserted.get(k) for k in ("buy_sha256", "sell_sha256") if inserted.get(k)}
    if not sha:
        pre = b1.get("pre") or {}
        sha = {"pre_incumbent_buy_sha": pre.get("incumbent_buy_sha"),
               "pre_patch_sell_sha": pre.get("patch_sell_sha")}
        add_note(receipt, "strategies(B1): register.inserted sha 누락 — pre 단축 sha로 대체 기록")
    meta = inserted.get("meta") or {}
    con.execute(
        "INSERT OR REPLACE INTO strategies (name, source_section, family,"
        " api_compat, source_sha256, lineage, rank_metrics_json, status_tag)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (name, "b1_registration_receipt", "alpha_lab_d5r",
         "historical/non-authoritative(등록 영수증)", json.dumps(sha, ensure_ascii=False),
         meta.get("sell_note"),
         json.dumps({"register": b1.get("register"), "post": b1.get("post")},
                    ensure_ascii=False),
         "역사적 B1 등록 영수증 — 비권위이며 v2 승격 근거가 아님"),
    )


def _enrich_rr8_12_sha(
    con: sqlite3.Connection, d1: Optional[dict], receipt: Dict[str, Any],
) -> None:
    """D1 요약의 RR8_12 원문 sha(매수/매도)를 해당 전략 행에 보강."""
    if d1 is None:
        return
    sha = {k: d1.get(k) for k in ("buy_sha256", "sell_sha256") if d1.get(k)}
    if not sha:
        add_note(receipt, "strategies(RR8_12): d1 요약에 buy/sell sha 부재 — 보강 생략")
        return
    cur = con.execute(
        "UPDATE strategies SET source_sha256=? WHERE name=?",
        (json.dumps(sha, ensure_ascii=False), "ALP_V4_RR8_12"))
    if cur.rowcount == 0:
        add_note(receipt, "strategies(RR8_12): W2 랭킹에 ALP_V4_RR8_12 행 없음 — sha 보강 미적용")


# ---------------------------------------------------------------------------
# cells — S-v1/V2-A sqlite + O-1G json 통합 union(label_tag 딱지 필수).
# ---------------------------------------------------------------------------

_CELL_COLSET = frozenset({
    "axis_set", "map_type", "time_label", "time_b", "updown_q", "mktcap_b",
    "gap_b", "gap_label", "win", "win_label", "h", "n", "n_candidates",
    "censor_rate", "exclusion_rate", "insufficient", "mean_net", "median_net",
    "q25_net", "q75_net", "p_net_ge0", "p_net_ge1", "ci_low", "ci_high",
    "winrate", "payoff", "mfe_mean", "mae_mean", "year2022_mean",
    "year2022_sign", "year2023_mean", "year2023_sign",
})
_REQUIRED_CELL_COLS = frozenset({"n", "mean_net", "ci_low", "ci_high"})
_TAG_SV1 = "함정 설명 전용(S-v1 칸-조준 kill-2)·자동 veto 금지"
_TAG_V2F = "함정 설명 전용(V2-C KILL 0/2)·자동 veto 금지"
_TAG_V2P = "함정 설명 전용·V2-B 파일럿 참고"
_TAG_O1G = "시초 함정 지도·O-3 null 기준선·자동 veto 금지"
_REGEN_SV1 = "STOM_ALLOW_MINIMAL_SETTING=1 python scripts/s_track_build_main.py"
_REGEN_V2 = "alpha_lab/stats_map(pilot_v2·config_v2) 경로 — V2-A 봉인(bb0778ef) 절차 재실행"

# (상대경로, ((원천 테이블, source 명),...), 고정 label_kind(None=행 컬럼 사용), 딱지, 재생성 명령)
_CELL_DB_SPECS = (
    ("stats_map/stats_map.db",
     (("cells_l0", "sv1_l0"), ("cells_l1", "sv1_l1")), "h300", _TAG_SV1, _REGEN_SV1),
    ("stats_map/stats_map_v2a_full.db",
     (("cells_pilot_v2", "v2a_full"),), None, _TAG_V2F, _REGEN_V2),
    ("stats_map/stats_map_v2a_pilot.db",
     (("cells_pilot_v2", "v2a_pilot"),), None, _TAG_V2P, _REGEN_V2),
)


def load_cells(
    con: sqlite3.Connection, run_dir: Path, o1g: Optional[dict],
    receipt: Dict[str, Any],
) -> None:
    """stats_map db 3종 + O-1G json 셀을 union 적재."""
    for spec in _CELL_DB_SPECS:
        _load_cells_db(con, Path(run_dir), spec, receipt)
    _load_cells_o1g(con, o1g, receipt)


def _load_cells_db(
    con: sqlite3.Connection, run_dir: Path, spec: tuple, receipt: Dict[str, Any],
) -> None:
    """sqlite 원천 1개 적재 — 파일 없음/스키마 상이면 '재생성 필요' 기록 후 스킵."""
    rel, tables, fixed_kind, tag, regen = spec
    path = run_dir / rel
    if not path.is_file():
        receipt["missing"].append(rel)
        receipt["skipped"].append(
            {"path": rel, "reason": "파일 없음 — 재생성 필요", "regen_cmd": regen})
        return
    src = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    try:
        for table, source_name in tables:
            cols = {r[1] for r in src.execute(f"PRAGMA table_info({table})")}
            if not cols or not _REQUIRED_CELL_COLS <= cols:
                receipt["skipped"].append({
                    "path": rel, "reason": f"스키마 상이(테이블 {table}) — 재생성 필요",
                    "regen_cmd": regen})
                continue
            for row in src.execute(f"SELECT * FROM {table}"):  # noqa: S608 — 고정 스펙 테이블명
                _insert_cell(con, dict(row), source_name, rel, fixed_kind, tag)
    except sqlite3.DatabaseError as exc:
        receipt["skipped"].append(
            {"path": rel, "reason": f"sqlite 읽기 실패: {exc} — 재생성 필요", "regen_cmd": regen})
    finally:
        src.close()
    record_source(receipt, run_dir, path)


def _load_cells_o1g(
    con: sqlite3.Connection, o1g: Optional[dict], receipt: Dict[str, Any],
) -> None:
    """O-1G 144셀 적재 — exit→exit_kind/label_kind 매핑."""
    if o1g is None:
        return
    cells = o1g.get("cells")
    if not isinstance(cells, list) or not cells:
        receipt["skipped"].append(
            {"path": "o1g/o1g_grid_summary.json", "reason": "cells 배열 없음 — cells 적재 생략"})
        return
    # o1g 원천의 연도 필드명은 스키마 컬럼명과 달라 그대로 두면 extra_json으로
    # 밀려난다(대시보드 V2가 연도 컬럼으로 질의 시 o1g 누락 — 검증 지적) →
    # 전용 연도 컬럼으로 매핑한다. p_one_sided 등 잔여는 extra 보존.
    year_map = {"mean_net_2022": "year2022_mean", "mean_net_2023": "year2023_mean",
                "year_sign_2022": "year2022_sign", "year_sign_2023": "year2023_sign"}
    for cell in cells:
        data = dict(cell)
        exit_kind = data.pop("exit", None)
        data["exit_kind"] = exit_kind
        for src_key, col in year_map.items():
            if src_key in data:
                data[col] = data.pop(src_key)
        _insert_cell(con, data, "o1g", "o1g/o1g_grid_summary.json",
                     str(exit_kind), _TAG_O1G)


def _insert_cell(
    con: sqlite3.Connection, data: Dict[str, Any], source: str,
    source_path: str, fixed_kind: Optional[str], label_tag: str,
) -> None:
    """셀 1행 삽입 — 알려진 컬럼만 매핑하고 잔여는 extra_json 보존."""
    label_kind = fixed_kind
    known: Dict[str, Any] = {}
    extra: Dict[str, Any] = {}
    for key, value in data.items():
        if key == "label_kind" and fixed_kind is None:
            label_kind = value
        elif key == "exit_kind":
            known[key] = value
        elif key in _CELL_COLSET:
            known[key] = value
        else:
            extra[key] = value
    cols = ["source", "source_path", "label_kind", "label_tag", "extra_json"]
    vals: List[Any] = [source, source_path, label_kind, label_tag,
                       json.dumps(extra, ensure_ascii=False) if extra else None]
    for key, value in known.items():
        cols.append(key)
        vals.append(value)
    placeholders = ",".join("?" for _ in cols)
    con.execute(
        f"INSERT INTO cells ({','.join(cols)}) VALUES ({placeholders})", vals)
