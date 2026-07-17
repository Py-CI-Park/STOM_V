# -*- coding: utf-8 -*-
"""D5R B1 매도식 패치 생성 + 기계적 bit-diff 검증 (읽기 전용, DB 미접촉).

- rr8_12 검증 매도식 원문(sha 8ef01e0e)에 Family B B1 조건절 1개를 삽입.
- 삽입 위치: 사전등록 §4 — `elif 시가총액 < 10000:` 블록 최하단 sub-elif.
- 절 값(봉인): 보유시간 >= 120 and 최고수익률 < 1.0 and 수익률 < 0.0 -> 매도 = True
- 매도조건명 주석(STOM 규약, 매도=True 직전 줄): # D5R_B1_저활력절단
- 검증: 원문과의 diff가 정확히 이 1절 추가뿐(그 외 1바이트도 다르면 실패).
"""
import sys, io, hashlib, difflib, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

REPO = r"C:\System_Trading\STOM\STOM_V.wt-alpha"
SELL_POLICY = os.path.join(REPO, "alpha_lab", "hillclimb", "sell_policy.py")

# --- 1. 원문 로드 (sell_policy.py를 격리 exec — 패키지 heavy import 회피) ---
ns = {}
with open(SELL_POLICY, "r", encoding="utf-8") as f:
    src = f.read()
exec(compile(src, SELL_POLICY, "exec"), ns)   # 모듈 자체가 import 시 sha 자가검증
CHAMPION = ns["CHAMPION_SELL_EXPR"]
CHAMPION_SHA = ns["CHAMPION_SELL_EXPR_SHA256"]

EXPECTED_CHAMPION_SHA = "8ef01e0ef2087ec95ac6b358b6f5c710414f3eb4dd401b01cc8162877f911c07"
assert CHAMPION_SHA == EXPECTED_CHAMPION_SHA, "sell_policy 선언 sha 불일치"
assert hashlib.sha256(CHAMPION.encode("utf-8")).hexdigest() == EXPECTED_CHAMPION_SHA, \
    "원문 실측 sha != 8ef01e0e (전사 오류)"
print("[1] 원문 sha 확인:", hashlib.sha256(CHAMPION.encode("utf-8")).hexdigest())

# --- 2. 삽입 앵커 (시가총액<10000 블록 최하단 sub-elif의 body) ---
# `이동평균(60) > 현재가` 는 원문에 정확히 1회 등장 → 앵커 유일성 보장.
ANCHOR = "이동평균(60) > 현재가:\n            매도 = True"
assert CHAMPION.count(ANCHOR) == 1, f"앵커 유일성 실패: count={CHAMPION.count(ANCHOR)}"

# --- 3. 신규 절 (봉인 B1 값 + 매도조건명 주석 직전 매도=True) ---
# 들여쓰기: elif 8칸, 주석/매도 12칸 (형제 sub-elif 와 동일 레벨)
NEW_CLAUSE = (
    "\n        elif 보유시간 >= 120 and 최고수익률 < 1.0 and 수익률 < 0.0:"
    "\n            # D5R_B1_저활력절단"
    "\n            매도 = True"
)

# --- 4. B1 패치 생성 (앵커 body 직후 삽입) ---
B1 = CHAMPION.replace(ANCHOR, ANCHOR + NEW_CLAUSE, 1)
assert B1 != CHAMPION, "패치가 원문과 동일 (삽입 실패)"

# --- 5. 기계적 bit-diff 검증 (3중 교차확인) ---
# 5a. 문자 단위 복원: B1에서 추가분(NEW_CLAUSE)만 제거하면 원문과 바이트 동일해야.
idx = CHAMPION.index(ANCHOR) + len(ANCHOR)
reconstructed = B1[:idx] + B1[idx + len(NEW_CLAUSE):]
assert reconstructed == CHAMPION, "복원 실패: 추가분 외 바이트가 변경됨"
# 5b. 길이 증가분 == 추가 바이트 수 정확히.
assert len(B1) - len(CHAMPION) == len(NEW_CLAUSE), "길이 델타 불일치"
# 5c. 삽입된 바이트가 정확히 NEW_CLAUSE 인지.
assert B1[idx:idx + len(NEW_CLAUSE)] == NEW_CLAUSE, "삽입 바이트 불일치"

# 5d. difflib 라인 단위: 추가 라인만 있고 삭제 라인 0.
diff = list(difflib.unified_diff(
    CHAMPION.splitlines(keepends=False), B1.splitlines(keepends=False),
    lineterm="", n=0))
added = [d for d in diff if d.startswith("+") and not d.startswith("+++")]
removed = [d for d in diff if d.startswith("-") and not d.startswith("---")]
assert removed == [], f"삭제된 라인 존재(원문 변형): {removed}"
expected_added = [
    "+        elif 보유시간 >= 120 and 최고수익률 < 1.0 and 수익률 < 0.0:",
    "+            # D5R_B1_저활력절단",
    "+            매도 = True",
]
assert added == expected_added, f"추가 라인 불일치: {added}"
print("[5] bit-diff 검증 통과: 삭제 0줄, 추가 3줄(=조건절 1개), 그 외 0바이트 변경")

# --- 6. 엔진 변환 안전성 (GetSellStg/SetSellCond 재현) — 컴파일 + attribution ---
def SetSellCond(selllist):
    count = 1; sellstg = ""
    dict_cond = {0: "전략종료청산", 1000: "분할매도", 1001: "익절청산", 1002: "손절청산"}
    for i, text in enumerate(selllist):
        if text and text[0] != "#" and ("매도 = True" in text or "매도= True" in text
                                        or "매도 =True" in text or "매도=True" in text):
            dict_cond[count] = selllist[i - 1]
            sellstg = f"{sellstg}{text.split('매도')[0]}self.sell_cond = {count}\n"
            count += 1
        if text:
            sellstg = f"{sellstg}{text}\n"
    return sellstg, dict_cond

wrapped = "self.sell_cond = 0\n" + B1
transformed, dict_cond = SetSellCond(wrapped.split("\n"))
compile(transformed, "<b1_sell>", "exec")   # SyntaxError면 여기서 실패
b1_attr = [v for v in dict_cond.values() if "D5R_B1_저활력절단" in str(v)]
assert b1_attr, f"신규 절 attribution 누락: {dict_cond}"
# 원문도 동일 변환 가능한지(회귀) 확인
compile(SetSellCond(("self.sell_cond = 0\n" + CHAMPION).split("\n"))[0], "<champ>", "exec")
print("[6] 엔진 변환/컴파일 통과. 신규 절 attribution =", repr(b1_attr[0].strip()))
print("    dict_cond 절 개수: 원문", len(SetSellCond(("self.sell_cond = 0\n"+CHAMPION).split("\n"))[1]),
      "-> B1", len(dict_cond))

# --- 7. B1 sha + 산출물 저장 ---
B1_SHA = hashlib.sha256(B1.encode("utf-8")).hexdigest()
print("[7] B1 매도식 sha256:", B1_SHA)

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ALP_D5R_B1_S.sell.txt")
with open(out_path, "w", encoding="utf-8", newline="") as f:
    f.write(B1)
print("    저장:", out_path, "(", len(B1), "bytes )")

print("\n===== 통합 diff (원문 -> B1) =====")
for line in difflib.unified_diff(
        CHAMPION.splitlines(), B1.splitlines(),
        fromfile="rr8_12_sell(8ef01e0e)", tofile="ALP_D5R_B1_S", lineterm="", n=3):
    print(line)
