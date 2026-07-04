"""T4.2 차트술사 v7.0 조건식 구조화 데이터 검증.

검증 대상:
  - ai_strategy_loop/brain/data/chart_sulsa_v7_conditions.json
      스키마, 21개 이상, compile 통과(needs_repair 제외), sha256 일치,
      금지 토큰 부재(forbidden.md (b) — brain.token_check 재사용),
      매수식의 매도 전용 변수 부재(forbidden.md (a)).
  - ai_strategy_loop/brain/data/chart_sulsa_pattern_families.json
      12개 패턴군, 자기서술 스키마 키.
  - docs/research/condition_research/condition_passports/chart_sulsa/*.md
      조건별 passport 존재 + 자기 측 sha256 포함 + '무근거 가설' 라벨 + oos none.

주의: 이 데이터는 전부 '무근거 가설 시드'다. 본 테스트는 데이터 무결성만 다루며
백테스트 성능을 검증하지 않는다.
"""

import ast
import hashlib
import json
import os
import re
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_strategy_loop.brain.token_check import check_tokens  # noqa: E402

DATA_DIR = os.path.join(PROJECT_ROOT, "ai_strategy_loop", "brain", "data")
CONDITIONS_PATH = os.path.join(DATA_DIR, "chart_sulsa_v7_conditions.json")
FAMILIES_PATH = os.path.join(DATA_DIR, "chart_sulsa_pattern_families.json")
PASSPORT_DIR = os.path.join(
    PROJECT_ROOT, "docs", "research", "condition_research", "condition_passports", "chart_sulsa"
)

REQUIRED_KEYS = {
    "id", "name_ko", "lane", "side", "principle_ids", "code", "code_sha256",
    "vars_ranges", "time_window", "status", "source",
}

# forbidden.md (a): 매수전략에서 금지되는 매도 전용 변수/복합조건 이름
SELL_ONLY_NAMES = {
    "수익금", "수익률", "최고수익률", "최저수익률", "매수가", "보유수량", "보유시간",
    "분할매수횟수", "분할매도횟수",
    "횡보상태장기보유", "변동성급증_역추세매도", "장기보유종목_동적익절청산",
    "거래대금비율기반_동적청산", "호가압력기반_동적청산", "이평기반_동적청산",
    "변동성기반_동적청산", "변동성급증기반_동적청산",
}


@pytest.fixture(scope="module")
def conditions_doc():
    with open(CONDITIONS_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def conditions(conditions_doc):
    return conditions_doc["conditions"]


@pytest.fixture(scope="module")
def families_doc():
    with open(FAMILIES_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_conditions_file_exists():
    assert os.path.isfile(CONDITIONS_PATH), f"조건식 JSON 없음: {CONDITIONS_PATH}"


def test_at_least_21_conditions(conditions):
    assert len(conditions) >= 21, f"조건식 21개 미만: {len(conditions)}"


def test_condition_ids_unique(conditions):
    ids = [c["id"] for c in conditions]
    assert len(ids) == len(set(ids)), "중복 id 존재"


def test_condition_schema(conditions):
    for c in conditions:
        missing = REQUIRED_KEYS - set(c)
        assert not missing, f"{c.get('id')}: 필수 키 누락 {missing}"
        assert c["lane"] in ("tick", "min"), f"{c['id']}: lane 이상 {c['lane']}"
        assert c["side"] in ("buy", "sell"), f"{c['id']}: side 이상 {c['side']}"
        assert c["status"] == "hypothesis_seed", f"{c['id']}: status 이상"
        assert c["source"] == "chart_sulsa_v7_0", f"{c['id']}: source 이상"
        assert isinstance(c["principle_ids"], list) and c["principle_ids"], (
            f"{c['id']}: principle_ids 비어 있음"
        )
        assert all(re.fullmatch(r"P\d{1,2}", p) for p in c["principle_ids"]), (
            f"{c['id']}: principle_ids 형식 이상 {c['principle_ids']}"
        )
        assert isinstance(c["code"], str) and c["code"].strip(), f"{c['id']}: code 비어 있음"


def test_expected_composition(conditions):
    """4장 tick(매수3+매도2+통합2) + 5장 min(매수7+매도5+통합2) + 6장 최적화 2벌."""
    def n(lane, side, opt):
        return sum(
            1 for c in conditions
            if c["lane"] == lane and c["side"] == side
            and c["id"].startswith("CSS_V7_OPT_") == opt
        )

    assert n("tick", "buy", False) == 4   # 매수 3 + 통합 매수 1
    assert n("tick", "sell", False) == 3  # 매도 2 + 통합 매도 1
    assert n("min", "buy", False) == 8    # 매수 7 + 통합 매수 1
    assert n("min", "sell", False) == 6   # 매도 5 + 통합 매도 1
    assert n("tick", "buy", True) == 1 and n("tick", "sell", True) == 1
    assert n("min", "buy", True) == 1 and n("min", "sell", True) == 1


def test_codes_compile(conditions):
    for c in conditions:
        if c.get("needs_repair"):
            continue
        try:
            compile(c["code"], f"<{c['id']}>", "exec")
        except SyntaxError as exc:
            pytest.fail(f"{c['id']}: compile 실패 — {exc}")


def test_code_sha256_matches(conditions):
    for c in conditions:
        actual = hashlib.sha256(c["code"].encode("utf-8")).hexdigest()
        assert actual == c["code_sha256"], f"{c['id']}: sha256 불일치"


def test_no_forbidden_tokens(conditions):
    """forbidden.md (b): import/exec/eval/open/compile/dunder — token_check 재사용."""
    for c in conditions:
        if c.get("needs_repair"):
            continue
        ok, reason = check_tokens(c["code"])
        assert ok, f"{c['id']}: 금지 토큰 — {reason}"


def test_buy_conditions_have_no_sell_only_names(conditions):
    """forbidden.md (a): 매수식은 잔고종목 전용 변수를 쓰면 안 된다."""
    for c in conditions:
        if c["side"] != "buy" or c.get("needs_repair"):
            continue
        tree = ast.parse(c["code"])
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        bad = names & SELL_ONLY_NAMES
        assert not bad, f"{c['id']}: 매수식에 매도 전용 변수 {bad}"


def test_opt_conditions_have_vars_ranges(conditions):
    for c in conditions:
        is_opt = c["id"].startswith("CSS_V7_OPT_")
        if is_opt:
            vr = c["vars_ranges"]
            assert isinstance(vr, dict) and vr.get("vars"), f"{c['id']}: vars_ranges 누락"
            for v in vr["vars"]:
                assert set(v) >= {"index", "range", "default"}, f"{c['id']}: vars 항목 이상 {v}"
                assert len(v["range"]) == 3, f"{c['id']}: range는 [min,max,step] — {v}"
        else:
            assert c["vars_ranges"] is None, f"{c['id']}: 비최적화형인데 vars_ranges 존재"


def test_passports_exist_and_consistent(conditions):
    assert os.path.isdir(PASSPORT_DIR), f"passport 디렉토리 없음: {PASSPORT_DIR}"
    for c in conditions:
        path = os.path.join(PASSPORT_DIR, c["id"].lower() + ".md")
        assert os.path.isfile(path), f"passport 없음: {path}"
        text = open(path, encoding="utf-8").read()
        assert c["code_sha256"] in text, f"{c['id']}: passport에 자기 sha256 없음"
        assert "무근거 가설" in text, f"{c['id']}: passport에 '무근거 가설' 라벨 없음"
        assert re.search(r"oos_status \| `none`", text), f"{c['id']}: oos_status none 누락"
        assert "## Buy condition full code" in text, f"{c['id']}: buy 전문 섹션 없음"
        assert "## Sell condition full code" in text, f"{c['id']}: sell 전문 섹션 없음"


def test_pattern_families_schema(families_doc):
    fams = families_doc["families"]
    assert len(fams) == 12, f"패턴군 12개 아님: {len(fams)}"
    ids = [f["family_id"] for f in fams]
    assert len(ids) == len(set(ids)), "패턴군 family_id 중복"
    for f in fams:
        missing = {
            "family_id", "name_ko", "lane", "buy_template_hint",
            "default_params", "param_ranges",
        } - set(f)
        assert not missing, f"{f.get('family_id')}: 키 누락 {missing}"
        assert f["lane"] in ("tick", "min"), f"{f['family_id']}: lane 이상"
        assert isinstance(f["default_params"], dict) and f["default_params"]
        assert isinstance(f["param_ranges"], dict) and f["param_ranges"]
        for name, rng in f["param_ranges"].items():
            assert len(rng) == 3, f"{f['family_id']}.{name}: [min,max,step] 아님 — {rng}"
            assert rng[0] <= rng[1], f"{f['family_id']}.{name}: min>max"


def test_pattern_family_hints_reference_known_conditions(families_doc, conditions):
    known = {c["id"] for c in conditions}
    for f in families_doc["families"]:
        referenced = re.findall(r"CSS_V7_[A-Z0-9_]+", f["buy_template_hint"])
        assert referenced, f"{f['family_id']}: buy_template_hint에 조건 id 없음"
        for rid in referenced:
            assert rid in known, f"{f['family_id']}: 알 수 없는 조건 id {rid}"
