# -*- coding: utf-8 -*-
"""B1 감독형 이관 — ALP_D5R_B1_S 쌍 등록 (INSERT-only) + 3중 sha 검증.

절차(승인 조건 3건 이행):
 (1) 등록 전: 현직 stockbuy/ALP_V4_RR8_12 원문 sha == 348c5181 확인(미러 원천 무결).
 (2) 등록: buy_expr = 그 원문의 byte-exact 미러(파일 348c5181), sell_expr = 패치(48018620).
 (3) 등록 후: DB에서 재조회하여 두 sha 재검증 + 현직 RR8_12 불변 재확인.
사용: python register_b1.py [--write]  (--write 없으면 드라이런)
"""
import sys, io, json, hashlib, sqlite3
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"C:\System_Trading\STOM\STOM_V.wt-alpha")
from alpha_lab.bridge.registrar import register_conditions

WRITE = "--write" in sys.argv[1:]
SCRATCH = Path(r"C:\Temp\claude\C--System-Trading-STOM-STOM-V-wt-alpha\f12d90e9-de14-41e1-89a7-5a5a21c801fb\scratchpad")
DB = Path(r"C:\System_Trading\STOM\STOM_V.wt-alpha\_database\strategy.db")
BACKUP_DIR = DB.parent
NAME = "ALP_D5R_B1_S"
EXP_BUY_SHA = "348c5181"
EXP_SELL_SHA = "48018620"

def sha(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()

buy_expr = (SCRATCH / "ALP_V4_RR8_12.buy.txt").read_text(encoding="utf-8")
sell_expr = (SCRATCH / "ALP_D5R_B1_S.sell.txt").read_text(encoding="utf-8")

# (1) 등록 전 — 현직 원문 대조 (파일 미러가 DB 현직과 byte-exact인지)
con = sqlite3.connect("file:" + str(DB).replace("\\", "/") + "?mode=ro", uri=True)
incumbent_buy = con.execute(
    'SELECT "전략코드" FROM stockbuy WHERE "index"=?', ("ALP_V4_RR8_12",)
).fetchone()[0]
incumbent_sell = con.execute(
    'SELECT "전략코드" FROM stocksell WHERE "index"=?', ("ALP_V4_RR8_12",)
).fetchone()[0]
con.close()

chk = {
    "incumbent_buy_sha": sha(incumbent_buy)[:8],
    "mirror_file_sha": sha(buy_expr)[:8],
    "mirror_is_byte_exact": incumbent_buy == buy_expr,
    "incumbent_sell_sha": sha(incumbent_sell)[:8],
    "patch_sell_sha": sha(sell_expr)[:8],
}
print("[사전 검증]", json.dumps(chk, ensure_ascii=False, indent=2))
assert chk["mirror_file_sha"] == EXP_BUY_SHA and chk["mirror_is_byte_exact"], "매수 미러가 현직과 불일치"
assert chk["patch_sell_sha"] == EXP_SELL_SHA, "매도 패치 sha 불일치"
assert chk["incumbent_sell_sha"] == "8ef01e0e", "현직 매도 원문 sha 불일치"

if not WRITE:
    print("\n[DRY-RUN] --write 없음. DB 미변경.")
    sys.exit(0)

# (2) 등록 (INSERT-only, 백업 강제, 멱등)
result = register_conditions(
    DB,
    [{
        "name": NAME,
        "buy_expr": buy_expr,
        "sell_expr": sell_expr,
        "meta": {
            "series": "D5-R B1 감독형 소액 실전 이관 (U-4)",
            "buy_note": "ALP_V4_RR8_12 매수 원문(348c5181)의 byte-exact 미러 — 신규 매수 전략 아님(registrar 쌍 계약의 기계적 산물)",
            "sell_note": "rr8_12 매도(8ef01e0e) + 절 1개(보유시간>=120 ∧ 최고수익률<1.0 ∧ 수익률<0.0 → 매도, # D5R_B1_저활력절단)",
            "canonical_pairing": "매수 ALP_V4_RR8_12 + 매도 ALP_D5R_B1_S",
            "prereg": "2026-07-12_d5r_conditional_exit_preregistration.md (ac5ca448)",
            "engine_ab": "2022 Δ+947,387 / 2023 Δ+591,485 / ΣΔ+1,538,872 — 4런 전체 PASS",
        },
    }],
    backup_dir=BACKUP_DIR,
    now=datetime.now(),
)
print("\n[등록 결과]", json.dumps(result, ensure_ascii=False, indent=2))

# (3) 등록 후 재검증 — 신규 쌍 sha + 현직 불변
con = sqlite3.connect("file:" + str(DB).replace("\\", "/") + "?mode=ro", uri=True)
new_buy = con.execute('SELECT "전략코드" FROM stockbuy WHERE "index"=?', (NAME,)).fetchone()[0]
new_sell = con.execute('SELECT "전략코드" FROM stocksell WHERE "index"=?', (NAME,)).fetchone()[0]
inc_buy2 = con.execute('SELECT "전략코드" FROM stockbuy WHERE "index"=?', ("ALP_V4_RR8_12",)).fetchone()[0]
inc_sell2 = con.execute('SELECT "전략코드" FROM stocksell WHERE "index"=?', ("ALP_V4_RR8_12",)).fetchone()[0]
n_buy = con.execute("SELECT COUNT(*) FROM stockbuy").fetchone()[0]
n_sell = con.execute("SELECT COUNT(*) FROM stocksell").fetchone()[0]
con.close()

post = {
    "db_buy_sha": sha(new_buy)[:8],
    "db_sell_sha": sha(new_sell)[:8],
    "buy_mirror_ok": sha(new_buy)[:8] == EXP_BUY_SHA and new_buy == incumbent_buy,
    "sell_patch_ok": sha(new_sell)[:8] == EXP_SELL_SHA,
    "incumbent_unchanged": inc_buy2 == incumbent_buy and inc_sell2 == incumbent_sell,
    "row_counts": {"stockbuy": n_buy, "stocksell": n_sell},
}
print("\n[등록 후 재검증]", json.dumps(post, ensure_ascii=False, indent=2))
assert post["buy_mirror_ok"] and post["sell_patch_ok"] and post["incumbent_unchanged"], "등록 후 검증 실패"

receipt = {"pre": chk, "register": result, "post": post, "name": NAME, "ts": datetime.now().isoformat()}
out = SCRATCH / "b1_registration_receipt.json"
out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
print("\n[영수증]", out)
print("\n등록 완료 + 3중 검증 전부 통과")
