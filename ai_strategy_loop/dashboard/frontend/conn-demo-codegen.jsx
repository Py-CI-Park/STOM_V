/* Connection demo code generators (split from connection.jsx for the thin-barrel pattern).
   Demo strategy code generators — Korean-flavored stock pseudo-Python. Pure string builders
   (no React, no window deps). useBackend 의 demo 시뮬레이터(buildPlan)가 import 해서 매수/매도
   조건식 스니펫을 날조한다(DEMO 전용 — backend 가 없을 때만 동작). conn-backend.jsx 가 소비.
*/

// ---------- Demo strategy code generators (Korean-flavored stock pseudo-Python) ----------
function genBuyCode(tag, gen) {
  const seed = (gen * 7) % 9 + 1;
  const map = {
    VWAP: `# BUY_VWAP_g${gen} — VWAP × 거래량가속 + RSI 필터
def signal_buy(bar, ind, book):
    # 1) 가격이 VWAP 위로 ${(0.2 + seed * 0.05).toFixed(2)}% 이상 이격
    if not (bar.close > ind.vwap * 1.00${seed}):
        return False
    # 2) 5분 거래량이 20봉 평균의 ${(150 + seed * 10)}% 이상
    if ind.vol_5m < ind.vol_20m_avg * ${(1.5 + seed * 0.1).toFixed(1)}:
        return False
    # 3) RSI(14) 50~70 구간 (과매수 회피)
    if not (50 <= ind.rsi_14 <= 70):
        return False
    # 4) 호가창 매수총잔량 / 매도총잔량 비율
    if book.bid_total / max(1, book.ask_total) < ${(1.4 + seed * 0.1).toFixed(2)}:
        return False
    return True`,
    MOM: `# BUY_MOM_g${gen} — 5/20 골든크로스 + 거래량 급증
def signal_buy(bar, ind, book):
    if ind.ema_5 <= ind.ema_20:                # 정배열 필요
        return False
    if ind.ema_5_prev > ind.ema_20_prev:       # 직전봉이 이미 정배열이면 신선도↓
        return False
    if ind.vol_now < ind.vol_20m_avg * ${(2.0 + seed * 0.1).toFixed(1)}:
        return False
    if bar.close <= bar.open * 1.00${seed}:    # 양봉 + 0.${seed}% 이상
        return False
    return True`,
    ORB: `# BUY_ORB_g${gen} — Opening Range Breakout 30m
def signal_buy(bar, ind, book):
    if bar.minute_of_day > 30 + 60:            # 장초반 90분 이내만
        return False
    if bar.high <= ind.or_30m_high:            # 30분 박스 상단 돌파
        return False
    if abs(bar.gap_pct) > 0.6:                 # 시초가 갭 0.6% 이내
        return False
    if ind.atr_14 < bar.close * 0.005:         # 변동성 너무 낮으면 패스
        return False
    return True`,
    FLOW: `# BUY_FLOW_g${gen} — 수급 추종 (프로그램·외인)
def signal_buy(bar, ind, book):
    if ind.program_netbuy_5m < ${(8e8 + seed * 1e8).toExponential(1)}:
        return False
    if ind.foreign_netbuy_today <= 0:
        return False
    if ind.short_ratio_today > ${(0.10 + seed * 0.01).toFixed(2)}:  # 공매도 비율 상한
        return False
    return True`,
    RSI: `# BUY_RSI_g${gen} — RSI 다이버전스 + BB 하단 반등
def signal_buy(bar, ind, book):
    if ind.rsi_14 < 30 or ind.rsi_14 > 45:
        return False
    if bar.close > ind.bb_lower * 1.01:
        return False
    if ind.obv_slope <= 0:                     # OBV는 우상향
        return False
    return True`,
    OBV: `# BUY_OBV_g${gen} — OBV 발산 + 거래대금 필터
def signal_buy(bar, ind, book):
    if ind.obv_5m < ind.obv_5m_prev:
        return False
    if ind.trading_value_today < ${5_000_000_000 + seed * 1e9}:
        return False
    if bar.close < ind.ema_20:
        return False
    return True`,
  };
  return map[tag] || map.VWAP;
}

function genSellCode(tag, gen) {
  const seed = (gen * 11) % 9 + 1;
  const map = {
    ATR: `# SELL_ATR_g${gen} — ATR 트레일링 스탑
def signal_sell(pos, bar, ind):
    trail = pos.high_since_entry - ind.atr_14 * ${(1.4 + seed * 0.1).toFixed(2)}
    if bar.close < trail:
        return ("trail_stop", bar.close)
    if pos.bars_held >= ${30 + seed * 5}:
        return ("time_exit", bar.close)
    if bar.close >= pos.entry_price * (1 + ${(0.024 + seed * 0.003).toFixed(3)}):
        return ("take_profit", bar.close)
    return None`,
    TRAIL: `# SELL_TRAIL_g${gen} — 동적 트레일 + 손익비 강제
def signal_sell(pos, bar, ind):
    pnl = (bar.close / pos.entry_price) - 1
    if pnl < -${(0.012 + seed * 0.002).toFixed(3)}:
        return ("stop_loss", bar.close)
    if pnl > ${(0.03 + seed * 0.004).toFixed(3)} and ind.rsi_14 > 72:
        return ("overbought_exit", bar.close)
    if pos.high_since_entry / pos.entry_price > 1.025:
        # 1.025배 이상 갔다면 본전 + 0.3% 스탑
        if bar.close < pos.entry_price * 1.003:
            return ("breakeven_stop", bar.close)
    return None`,
    FIXED: `# SELL_FIXED_g${gen} — 고정 익절/손절
def signal_sell(pos, bar, ind):
    pnl = (bar.close / pos.entry_price) - 1
    if pnl >= ${(0.025 + seed * 0.005).toFixed(3)}:
        return ("take_profit", bar.close)
    if pnl <= -${(0.015 + seed * 0.002).toFixed(3)}:
        return ("stop_loss", bar.close)
    return None`,
    PIVOT: `# SELL_PIVOT_g${gen} — 일중 피봇 이탈
def signal_sell(pos, bar, ind):
    if bar.close < ind.pivot_s1:
        return ("pivot_break", bar.close)
    if bar.minute_of_day >= 360:                # 14시 이후 트레일 강화
        if bar.close < pos.high_since_entry * 0.99${seed}:
            return ("late_trail", bar.close)
    return None`,
    TIME: `# SELL_TIME_g${gen} — 시간 기반 청산
def signal_sell(pos, bar, ind):
    if bar.minute_of_day >= 359:                # 종가 30분 전 강제청산
        return ("close_force", bar.close)
    if pos.bars_held >= ${20 + seed * 4}:
        return ("time_exit", bar.close)
    return None`,
  };
  return map[tag] || map.ATR;
}

// Track Z — dual-safe ESM export. KEEP on ONE physical line.
export { genBuyCode, genSellCode };
