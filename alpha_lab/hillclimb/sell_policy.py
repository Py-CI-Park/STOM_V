"""챔피언 매도식(hard-stop 계열) 고정 상수 — 힐클라임 전 시드 공통 sell_expr.

원문 출처: docs/research/condition_research/condition_passports/
rr8_12_turnover_min_902_1.5.md "Sell condition full code" 펜스 블록
(끝 개행 제거) — sell_code_sha256 필드와 바이트 동일성을 이 모듈
임포트 시점에 자가 검증한다(전사 오류 즉시 실패).

preregistration_v3.json hillclimb.mutator: "매도식 고정(hard-stop 계열
sha 8ef01e0e)" — 힐클라임은 매수식만 변이하고 이 매도식은 절대 바꾸지
않는다(생성 금지 원칙, alpha_lab.translate.codegen.SELL_POLICY와 동일
취지).
"""
from __future__ import annotations

import hashlib

__all__ = ["CHAMPION_SELL_EXPR", "CHAMPION_SELL_EXPR_SHA256"]

CHAMPION_SELL_EXPR_SHA256 = "8ef01e0ef2087ec95ac6b358b6f5c710414f3eb4dd401b01cc8162877f911c07"

CHAMPION_SELL_EXPR = '# ================================\n#  공통 계산 지표\n# ================================\n시가대비등락율    = ((현재가 - 시가) / 시가) * 100                      # 단위: 퍼센트\n# ------------------------------------------------\n#  New 지표 (미사용 시 주석 처리)\n#   · 매도잔량압력 · 체결강도변동성 · RSI변화율 등\n# ------------------------------------------------\n\n\n\n# ================================\n#  매도 조건 (902 ↔ 905 통합)\n# ================================\n매도 = False\n\n\n# 등락율 상한가 직전\nif 등락율 > 29.5:\n    매도 = True\nelif 시가대비등락율 < 0 and 수익률 <= -2.0 and 현재가 < 최저현재가(int(60), int(보유시간)):\n    매도 = True\n\n\nelif 보유시간 > 60 and 현재가 < 최저현재가(int(60), int(보유시간)):\n    매도 = True\nelif 시분초 < 93000:\n    if 수익률 >= 9 or 수익률 <= -5.0:\n        매도 = True\n    elif 최고수익률 > 3 and 최고수익률 * 0.6 >= 수익률:\n        매도 = True\n    elif 시가총액 < 10000:\n        if 등락율각도(30) >= 10 and (초당매도수량 - 초당매수수량) >= 매수총잔량 * 0.5 and (현재가 / 현재가N(1) - 1) * 100 < -0.5:\n            매도 = True\n        elif 등락율각도(30) < 10 and 등락율각도(30) >= 5 and (초당매도수량 - 초당매수수량) >= 매수총잔량 * 0.7 and (현재가 / 현재가N(1) - 1) * 100 < -0.7:\n            매도 = True\n        elif 등락율각도(30) < 5 and 등락율각도(30) >= 0 and (초당매도수량 - 초당매수수량) >= 매수총잔량 * 0.8 and (현재가 / 현재가N(1) - 1) * 100 < -0.5:\n            매도 = True\n        elif 4.5 < 최고수익률 and 현재가N(1) >= 이동평균(60, 1) and 이동평균(60) > 현재가:\n            매도 = True\n\n\n# ================================\n#  매도 호출\n# ================================\nif 매도:\n    self.Sell()'

_actual = hashlib.sha256(CHAMPION_SELL_EXPR.encode("utf-8")).hexdigest()
if _actual != CHAMPION_SELL_EXPR_SHA256:
    raise AssertionError(
        f"CHAMPION_SELL_EXPR sha256 불일치(전사 오류 의심): "
        f"{_actual} != {CHAMPION_SELL_EXPR_SHA256}"
    )
