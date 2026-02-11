"""
STOM CLI Test Fixtures - Sample Strategies
===========================================

테스트용 샘플 전략 코드 및 데이터
"""

# ============================================================
# 전략 코드 샘플
# ============================================================

# 전략 1: 이동평균선 교차 (Golden Cross)
STRATEGY_MA_CROSSOVER = """
def signal(price, ma_short, ma_long):
    '''
    이동평균선 교차 전략
    - 단기 이평선이 장기 이평선을 상향 돌파하면 매수
    - 단기 이평선이 장기 이평선을 하향 돌파하면 매도
    '''
    if ma_short > ma_long:
        return 'BUY'
    elif ma_short < ma_long:
        return 'SELL'
    return 'HOLD'

def risk_management(position_size, stop_loss=0.02):
    '''리스크 관리: 2% 손절'''
    return position_size * (1 - stop_loss)
"""

# 전략 2: RSI 과매도/과매수
STRATEGY_RSI = """
def signal(rsi, oversold=30, overbought=70):
    '''
    RSI 기반 전략
    - RSI < 30: 과매도 구간, 매수 신호
    - RSI > 70: 과매수 구간, 매도 신호
    '''
    if rsi < oversold:
        return 'BUY'
    elif rsi > overbought:
        return 'SELL'
    return 'HOLD'
"""

# 전략 3: 볼린저 밴드
STRATEGY_BOLLINGER = """
def signal(price, upper_band, lower_band, middle_band):
    '''
    볼린저 밴드 전략
    - 가격이 하단 밴드 터치: 매수
    - 가격이 상단 밴드 터치: 매도
    '''
    if price <= lower_band:
        return 'BUY'
    elif price >= upper_band:
        return 'SELL'
    return 'HOLD'
"""

# 전략 4: 단순 전략 (테스트용)
STRATEGY_SIMPLE = """
def signal():
    '''항상 매수 신호를 반환하는 단순 전략'''
    return 'BUY'
"""

# 전략 5: 복합 전략
STRATEGY_COMBINED = """
def signal(price, ma20, ma50, rsi, volume, avg_volume):
    '''
    복합 전략: 이평선 + RSI + 거래량

    매수 조건:
    - 20일 이평선 > 50일 이평선
    - RSI < 40
    - 거래량 > 평균 거래량의 1.5배
    '''
    ma_condition = ma20 > ma50
    rsi_condition = rsi < 40
    volume_condition = volume > avg_volume * 1.5

    if ma_condition and rsi_condition and volume_condition:
        return 'BUY'
    elif rsi > 70 or ma20 < ma50:
        return 'SELL'
    return 'HOLD'
"""

# ============================================================
# 문법 오류가 있는 전략 (테스트용)
# ============================================================

STRATEGY_INVALID_SYNTAX = """
def signal(price moving_avg):  # 쉼표 누락
    if price > moving_avg
        return 'BUY'  # 콜론 누락
"""

STRATEGY_INVALID_INDENT = """
def signal():
return 'BUY'  # 잘못된 들여쓰기
"""

STRATEGY_INVALID_IMPORT = """
import nonexistent_module  # 존재하지 않는 모듈

def signal():
    return nonexistent_module.calculate()
"""

# ============================================================
# 전략 메타데이터
# ============================================================

SAMPLE_STRATEGIES_METADATA = [
    {
        "name": "ma_crossover",
        "type": "stock",
        "buy_sell": "buy",
        "code": STRATEGY_MA_CROSSOVER,
        "description": "이동평균선 교차 전략",
        "parameters": {
            "ma_short": 20,
            "ma_long": 50
        }
    },
    {
        "name": "rsi_oversold",
        "type": "stock",
        "buy_sell": "buy",
        "code": STRATEGY_RSI,
        "description": "RSI 과매도 전략",
        "parameters": {
            "oversold": 30,
            "overbought": 70
        }
    },
    {
        "name": "bollinger_bounce",
        "type": "coin",
        "buy_sell": "buy",
        "code": STRATEGY_BOLLINGER,
        "description": "볼린저 밴드 반등 전략",
        "parameters": {
            "period": 20,
            "std_dev": 2
        }
    },
    {
        "name": "profit_taking",
        "type": "stock",
        "buy_sell": "sell",
        "code": """
def signal(profit, threshold=0.1):
    '''10% 수익 실현 전략'''
    return 'SELL' if profit > threshold else 'HOLD'
""",
        "description": "수익 실현 전략",
        "parameters": {
            "threshold": 0.1
        }
    },
    {
        "name": "stop_loss",
        "type": "stock",
        "buy_sell": "sell",
        "code": """
def signal(loss, threshold=-0.02):
    '''2% 손절 전략'''
    return 'SELL' if loss < threshold else 'HOLD'
""",
        "description": "손절 전략",
        "parameters": {
            "threshold": -0.02
        }
    }
]

# ============================================================
# JSON 형식 테스트 데이터
# ============================================================

SAMPLE_STRATEGIES_JSON = [
    {
        "name": "test_ma_cross",
        "type": "stock",
        "buy_sell": "buy",
        "code": "def signal(): return 'BUY' if ma20 > ma50 else 'HOLD'"
    },
    {
        "name": "test_rsi_strategy",
        "type": "coin",
        "buy_sell": "buy",
        "code": "def signal(rsi): return 'BUY' if rsi < 30 else 'HOLD'"
    },
    {
        "name": "test_sell_strategy",
        "type": "stock",
        "buy_sell": "sell",
        "code": "def signal(profit): return 'SELL' if profit > 0.05 else 'HOLD'"
    }
]

# ============================================================
# CSV 형식 테스트 데이터
# ============================================================

SAMPLE_STRATEGIES_CSV = """name,type,buy_sell,code
test_csv_ma,stock,buy,"def signal(): return 'BUY'"
test_csv_rsi,coin,buy,"def signal(rsi): return 'BUY' if rsi < 30 else 'HOLD'"
test_csv_sell,stock,sell,"def signal(): return 'SELL'"
"""

# ============================================================
# 백테스트 결과 샘플
# ============================================================

SAMPLE_BACKTEST_RESULTS = [
    {
        "strategy_name": "ma_crossover",
        "start_date": "20260101",
        "end_date": "20260131",
        "total_return": 0.15,
        "sharpe_ratio": 1.5,
        "max_drawdown": -0.08,
        "win_rate": 0.62,
        "total_trades": 25
    },
    {
        "strategy_name": "rsi_oversold",
        "start_date": "20260101",
        "end_date": "20260131",
        "total_return": 0.08,
        "sharpe_ratio": 0.9,
        "max_drawdown": -0.12,
        "win_rate": 0.55,
        "total_trades": 18
    },
    {
        "strategy_name": "bollinger_bounce",
        "start_date": "20260115",
        "end_date": "20260131",
        "total_return": 0.22,
        "sharpe_ratio": 2.1,
        "max_drawdown": -0.05,
        "win_rate": 0.71,
        "total_trades": 14
    }
]

# ============================================================
# 거래 내역 샘플
# ============================================================

SAMPLE_TRADES = [
    {
        "symbol": "005930",  # 삼성전자
        "trade_date": "20260101",
        "trade_time": "093000",
        "side": "BUY",
        "quantity": 10,
        "price": 70000
    },
    {
        "symbol": "005930",
        "trade_date": "20260101",
        "trade_time": "143000",
        "side": "SELL",
        "quantity": 10,
        "price": 71500
    },
    {
        "symbol": "000660",  # SK하이닉스
        "trade_date": "20260102",
        "trade_time": "100000",
        "side": "BUY",
        "quantity": 5,
        "price": 120000
    },
    {
        "symbol": "BTCUSDT",
        "trade_date": "20260101",
        "trade_time": "120000",
        "side": "BUY",
        "quantity": 0.1,
        "price": 50000
    }
]
