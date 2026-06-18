"""Claude 생성 후보를 공식 가드(compile/token/scope) 통과 후 loop_strategies.db에 주입.

- 생성기와 동일한 PRE-SAVE 가드를 그대로 재사용한다(맹목 주입 금지).
- C7_SEEDPLUS는 시드(Tick_B_902_905_Update_2) 코드를 DB에서 읽어
  말미에 위험필터 3종 오버레이를 끼워 프로그래밍 방식으로 구성한다.
실행: PYTHONUTF8=1 python .omo/evidence/claude-condition-research-20260610/insert_candidates.py
"""
import sys
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

import ai_strategy_loop.bootstrap as bootstrap  # noqa: E402 (env 격리)
from ai_strategy_loop.brain.token_check import check_tokens  # noqa: E402
from ai_strategy_loop.brain.variable_scope import check_variable_scope  # noqa: E402
from cli.strategy_generator import save_strategy_to_db  # noqa: E402

CAND_DIR = Path(__file__).resolve().parent / "candidates"
DB = str(bootstrap.LOOP_DB_STRATEGY)

SEED_BUY_NAME = "Tick_B_902_905_Update_2"

SEEDPLUS_OVERLAY = """
# ── CLDGEN 위험필터 오버레이 (시드 구조 보존, 진입 직전 3종 차단) ──
if 매수:
    스프레드틱_CLD = (매도호가1 - 매수호가1) / 호가단위 if 호가단위 != 0 else 99
    매도공격비5_CLD = 누적초당매도수량(5) / 누적초당매수수량(5) if 누적초당매수수량(5) > 0 else 0
    if 스프레드틱_CLD > 2.0:
        매수 = False
    elif 매도공격비5_CLD >= 1.8:
        매수 = False
    elif 매수잔량1 < 매수잔량1N(1) * 0.5:
        매수 = False

if 매수:
    self.Buy()
"""


def validate(name: str, code: str, kind: str) -> list:
    errors = []
    try:
        compile(code, "<string>", "exec")
    except SyntaxError as e:
        errors.append(f"compile: {e}")
    ok, msg = check_tokens(code)
    if not ok:
        errors.append(f"token: {msg}")
    ok, missing = check_variable_scope(code, "tick", kind)
    if not ok:
        errors.append(f"scope({kind}/tick): {missing}")
    return errors


def build_seedplus() -> str:
    con = sqlite3.connect(DB)
    try:
        row = con.execute(
            'SELECT "전략코드" FROM stockbuy WHERE "index"=?', (SEED_BUY_NAME,)
        ).fetchone()
    finally:
        con.close()
    if not row:
        raise SystemExit(f"seed not found: {SEED_BUY_NAME}")
    code = row[0]
    tail = "if 매수:\n    self.Buy()"
    if code.count(tail) != 1:
        raise SystemExit(f"seed tail mismatch (count={code.count(tail)})")
    return code.replace(tail, SEEDPLUS_OVERLAY.strip())


def main() -> int:
    items = []
    for p in sorted(CAND_DIR.glob("*.txt")):
        stem = p.name
        if stem.endswith(".buy.txt"):
            items.append((stem[: -len(".buy.txt")], p.read_text(encoding="utf-8"), "buy"))
        elif stem.endswith(".sell.txt"):
            items.append((stem[: -len(".sell.txt")], p.read_text(encoding="utf-8"), "sell"))
    items.append(("CLDGEN_0610_C7_SEEDPLUS_B", build_seedplus(), "buy"))

    failed = False
    for name, code, kind in items:
        errs = validate(name, code, kind)
        if errs:
            failed = True
            print(f"[FAIL] {name} ({kind})")
            for e in errs:
                print(f"   - {e}")
            continue
        res = save_strategy_to_db(DB, name, code, kind)
        print(f"[{res.get('status','?').upper()}] {name} ({kind}) {res.get('action','')}{res.get('message','')}")
        if res.get("status") != "ok":
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
