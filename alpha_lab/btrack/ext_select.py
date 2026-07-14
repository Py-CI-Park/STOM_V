"""B-ext 기계 선정 — 손 선정 배제(봉인본 §14-F1·확인③).

봉인 규약(§14-F1):
  - 코어 7 고정 명단 + 가문 확장 = 나머지 Tick_B_* 를 '신규 절 수 오름차순' ≤6종(신규 비트 ≤40 상한 내)
  - 비가문 = 정정 풀에서 W2 연율 순 ≤5종(RR8_0/21 제외 확정).
  - 재사용률 ≥50% = '가문' 기계 태깅.
  - 선정 게이트: 원문 실재(stockbuy 전략코드 non-null) ∧ 엔진 문법(가지 파스 성공·측정가능 분기 ≥1).
  - 신규 비트 ≤40 상한. 초과 시 저(신규)중복 전략부터 편입 중단.

선정·sha·가지·매핑·신규 비트 정의를 전부 게이트 리포트로 영속화(**L3 관측 전** — 확인③ 정본).
strategy.db read-only. 엔진 0회.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from alpha_lab.btrack.ext_parse import (
    Branch, compile_clause, enumerate_branches, map_atom_to_bit, normalize_atom,
)
from alpha_lab.dataset.reader import connect_ro

__all__ = [
    "CORE_7", "MAX_FAMILY_EXPAND", "MAX_NONFAMILY", "NEW_BIT_CAP", "NONFAMILY_POOL",
    "REUSE_FAMILY_THRESHOLD", "BranchInfo", "SelectionResult", "StrategyInfo",
    "analyze_strategy", "load_strategy_texts", "select",
]

# §14-F1 봉인 명단.
CORE_7: Tuple[str, ...] = (
    "Tick_B_902_905", "Tick_B_902_905_Study", "Tick_B_902_905_Study_2",
    "Tick_B_902_905_Update", "Tick_B_902_905_Update_2", "Tick_B_902_905_Update_2_Study",
    "Tick_B_930_Dev")
# 비가문 정정 풀(W2 연율 순 — engine_top20 순서, RR8_0/21 제외).
NONFAMILY_POOL: Tuple[str, ...] = (
    "GATE_r2_14_atk_a_0_35_B", "TMAP_seed_902905_r2full_004_B",
    "TMAP_seed_902905_r2full_007_B", "R2R3_C_B",
    "GATE_r1_6_ogap_lo_b_2_0_B", "GATE_r4_8_burst_a_3_0_B")
NEW_BIT_CAP = 40
MAX_FAMILY_EXPAND = 6
MAX_NONFAMILY = 5
REUSE_FAMILY_THRESHOLD = 0.50


def _sha(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


@dataclass
class BranchInfo:
    """전략 분기 하나 — 기존 비트 절# + 신규 절 키((canonical, negated)) + 측정가능 여부."""

    strategy: str
    index: int
    n_atoms: int
    bit_nums: List[int] = field(default_factory=list)          # 기존 39비트 재사용.
    new_keys: List[Tuple[str, bool]] = field(default_factory=list)  # 신규 절((canon, negated)).
    measurable: bool = True
    exclude_reason: str = ""


@dataclass
class StrategyInfo:
    name: str
    sha256: str
    n_branches: int
    branches: List[BranchInfo]
    n_reuse_atoms: int
    n_total_atoms: int
    new_keys: List[Tuple[str, bool]]        # 측정가능 분기의 신규 절(중복제거).
    is_family: bool                          # 재사용률 ≥50%.
    source_present: bool
    parse_ok: bool

    @property
    def reuse_ratio(self) -> float:
        return (self.n_reuse_atoms / self.n_total_atoms) if self.n_total_atoms else 0.0

    @property
    def n_measurable(self) -> int:
        return sum(1 for b in self.branches if b.measurable)


def analyze_strategy(name: str, text: Optional[str]) -> StrategyInfo:
    """전략 1개 — 가지 파스·비트 매핑·신규 절 컴파일·재사용률·가문 태깅."""
    if text is None or not str(text).strip():
        return StrategyInfo(name, "", 0, [], 0, 0, [], False, source_present=False, parse_ok=False)
    sha = _sha(text)
    try:
        branches = enumerate_branches(text)
    except SyntaxError:
        return StrategyInfo(name, sha, 0, [], 0, 0, [], False, source_present=True, parse_ok=False)

    binfos: List[BranchInfo] = []
    reuse_atoms = total_atoms = 0
    strat_new: Dict[Tuple[str, bool], None] = {}
    for i, br in enumerate(branches):
        bit_nums: List[int] = []
        new_keys: List[Tuple[str, bool]] = []
        measurable = br.conjunctive
        reason = "" if br.conjunctive else "비-conjunctive(가드 OR/NOT-AND)"
        for atom, negated in br.atoms:
            total_atoms += 1
            num = map_atom_to_bit(atom)
            if num is not None:
                bit_nums.append(num)
                reuse_atoms += 1
            else:
                ci = compile_clause(atom, negated=negated)
                if not ci.evaluable:
                    measurable = False
                    reason = reason or ci.reason
                key = (normalize_atom(atom) or atom, negated)
                new_keys.append(key)
        bi = BranchInfo(strategy=name, index=i, n_atoms=len(br.atoms),
                        bit_nums=sorted(set(bit_nums)), new_keys=new_keys,
                        measurable=measurable, exclude_reason=reason)
        binfos.append(bi)
        if measurable:
            for k in new_keys:
                strat_new.setdefault(k, None)
    is_family = (reuse_atoms / total_atoms) >= REUSE_FAMILY_THRESHOLD if total_atoms else False
    return StrategyInfo(name, sha, len(branches), binfos, reuse_atoms, total_atoms,
                        list(strat_new.keys()), is_family, source_present=True, parse_ok=True)


def load_strategy_texts(strategy_db_path, names: Tuple[str, ...]) -> Dict[str, Optional[str]]:
    """stockbuy 원문 read-only 로드(부재 = None)."""
    conn = connect_ro(strategy_db_path)
    try:
        out: Dict[str, Optional[str]] = {}
        for n in names:
            row = conn.execute('SELECT "전략코드" FROM stockbuy WHERE "index" = ?', (n,)).fetchone()
            out[n] = (str(row[0]) if row and row[0] is not None else None)
        return out
    finally:
        conn.close()


@dataclass
class SelectionResult:
    selected: List[str]
    family_expand: List[str]
    nonfamily: List[str]
    excluded: List[Dict[str, object]]
    strategies: Dict[str, StrategyInfo]
    new_bit_ids: Dict[Tuple[str, bool], str]     # (canon, negated) → ext_<NNN>.
    n_new_bits: int
    n_branches_measurable: int
    caps: Dict[str, int]


def _assign_new_bit_ids(keys: List[Tuple[str, bool]]) -> Dict[Tuple[str, bool], str]:
    """신규 절 키(중복제거) → 결정론 ext_id(정렬 순)."""
    uniq = sorted(set(keys), key=lambda k: (k[0], k[1]))
    return {k: f"ext_{i:03d}" for i, k in enumerate(uniq)}


def select(strategy_db_path) -> SelectionResult:
    """§14-F1 기계 선정 — 코어 7 + 가문 확장(오름차순≤6·cap) + 비가문(연율순≤5·cap)."""
    all_names = tuple(dict.fromkeys(CORE_7 + _family_candidates(strategy_db_path) + NONFAMILY_POOL))
    texts = load_strategy_texts(strategy_db_path, all_names)
    infos = {n: analyze_strategy(n, texts.get(n)) for n in all_names}

    selected: List[str] = []
    excluded: List[Dict[str, object]] = []
    new_keys: Dict[Tuple[str, bool], None] = {}

    def _try_add(name: str, group: str) -> bool:
        info = infos[name]
        if not info.source_present:
            excluded.append({"strategy": name, "group": group, "reason": "원문 부재(stockbuy)"})
            return False
        if not info.parse_ok or info.n_measurable == 0:
            excluded.append({"strategy": name, "group": group,
                             "reason": "파스 실패 또는 측정가능 분기 0"})
            return False
        prospective = dict(new_keys)
        for k in info.new_keys:
            prospective.setdefault(k, None)
        if len(prospective) > NEW_BIT_CAP:
            excluded.append({"strategy": name, "group": group,
                             "reason": f"신규 비트 상한 초과(누적 {len(prospective)}>{NEW_BIT_CAP})"})
            return False
        for k in info.new_keys:
            new_keys.setdefault(k, None)
        selected.append(name)
        return True

    # 코어 7(고정 — 상한 검사만).
    for n in CORE_7:
        _try_add(n, "core")
    # 가문 확장: 나머지 Tick_B, 신규 절 수 오름차순 ≤6.
    fam_cands = [n for n in _family_candidates(strategy_db_path)
                 if n not in CORE_7 and infos[n].source_present and infos[n].n_measurable]
    fam_cands.sort(key=lambda n: (len(infos[n].new_keys), n))
    fam_added = 0
    fam_selected: List[str] = []
    for n in fam_cands:
        if fam_added >= MAX_FAMILY_EXPAND:
            excluded.append({"strategy": n, "group": "family_expand", "reason": "가문 확장 상한(6) 소진"})
            continue
        if _try_add(n, "family_expand"):
            fam_added += 1
            fam_selected.append(n)
    # 비가문: 풀 연율순 ≤5.
    nf_added = 0
    nf_selected: List[str] = []
    for n in NONFAMILY_POOL:
        if nf_added >= MAX_NONFAMILY:
            excluded.append({"strategy": n, "group": "nonfamily", "reason": "비가문 상한(5) 소진"})
            continue
        if _try_add(n, "nonfamily"):
            nf_added += 1
            nf_selected.append(n)

    ids = _assign_new_bit_ids(list(new_keys.keys()))
    n_meas = sum(infos[n].n_measurable for n in selected)
    return SelectionResult(
        selected=selected, family_expand=fam_selected, nonfamily=nf_selected,
        excluded=excluded, strategies={n: infos[n] for n in all_names},
        new_bit_ids=ids, n_new_bits=len(ids), n_branches_measurable=n_meas,
        caps={"new_bit_cap": NEW_BIT_CAP, "max_family_expand": MAX_FAMILY_EXPAND,
              "max_nonfamily": MAX_NONFAMILY})


def _family_candidates(strategy_db_path) -> Tuple[str, ...]:
    """stockbuy 의 Tick_B_* 전 전략(가문 확장 후보 원천)."""
    conn = connect_ro(strategy_db_path)
    try:
        names = [n for (n,) in conn.execute('SELECT "index" FROM stockbuy')
                 if str(n).startswith("Tick_B")]
    finally:
        conn.close()
    return tuple(sorted(names))
