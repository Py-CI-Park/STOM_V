"""시장 설정 모듈입니다.
백테스트 및 트레이딩 관련 클래스와 데이터베이스 경로를 포함합니다.
"""
from utility.settings.setting_base import DB_PATH
from trade.stock_korea.stock_trader import StockTrader
from trade.stock_korea.stock_receiver import StockReceiver
from trade.stock_korea.stock_strategy import StockStrategy
from trade.stock_usa.stock_usa_trader import StockUsaTrader
from trade.stock_usa.stock_usa_receiver import StockUsaReceiver
from trade.stock_usa.stock_usa_strategy import StockUsaStrategy
from trade.upbit.upbit_trader import UpbitTrader
from trade.upbit.upbit_receiver import UpbitReceiver
from trade.upbit.upbit_strategy import UpbitStrategy
from trade.future.future_trader import FutureTrader
from trade.future.future_receiver import FutureReceiver
from trade.future.future_strategy import FutureStrategy
from trade.future_oversea.future_os_trader import FutureOsTrader
from trade.future_oversea.future_os_receiver import FutureOsReceiver
from trade.future_oversea.future_os_strategy import FutureOsStrategy
from trade.binance.binance_trader import BinanceTrader
from trade.binance.binance_receiver import BinanceReceiver
from trade.binance.binance_strategy import BinanceStrategy

from backtest.stock_korea.backengine_stock import BackEngineStock
from backtest.stock_korea.backengine_stock_oms import BackEngineStockOms
from backtest.stock_usa.backengine_stock_usa import BackEngineStockUsa
from backtest.stock_usa.backengine_stock_usa_oms import BackEngineStockUsaOms
from backtest.upbit.backengine_upbit import BackEngineUpbit
from backtest.upbit.backengine_upbit_oms import BackEngineUpbitOms
from backtest.future.backengine_future import BackEngineFuture
from backtest.future.backengine_future_oms import BackEngineFutureOms
from backtest.future_oversea.backengine_future_oversea import BackEngineFutureOversea
from backtest.future_oversea.backengine_future_oversea_oms import BackEngineFutureOverseaOms
from backtest.binance.backengine_binance import BackEngineBinance
from backtest.binance.backengine_binance_oms import BackEngineBinanceOms

DB_STOCK_TICK            = f'{DB_PATH}/stock_tick.db'
DB_STOCK_MIN             = f'{DB_PATH}/stock_min.db'
DB_STOCK_TICK_BACK       = f'{DB_PATH}/stock_tick_back.db'
DB_STOCK_MIN_BACK        = f'{DB_PATH}/stock_min_back.db'
DB_STOCK_ETF_TICK        = f'{DB_PATH}/stock_etf_tick.db'
DB_STOCK_ETF_MIN         = f'{DB_PATH}/stock_etf_min.db'
DB_STOCK_ETF_TICK_BACK   = f'{DB_PATH}/stock_etf_tick_back.db'
DB_STOCK_ETF_MIN_BACK    = f'{DB_PATH}/stock_etf_min_back.db'
DB_STOCK_ETN_TICK        = f'{DB_PATH}/stock_etn_tick.db'
DB_STOCK_ETN_MIN         = f'{DB_PATH}/stock_etn_min.db'
DB_STOCK_ETN_TICK_BACK   = f'{DB_PATH}/stock_etn_tick_back.db'
DB_STOCK_ETN_MIN_BACK    = f'{DB_PATH}/stock_etn_min_back.db'
DB_STOCK_USA_TICK        = f'{DB_PATH}/stock_usa_tick.db'
DB_STOCK_USA_MIN         = f'{DB_PATH}/stock_usa_min.db'
DB_STOCK_USA_TICK_BACK   = f'{DB_PATH}/stock_usa_tick_back.db'
DB_STOCK_USA_MIN_BACK    = f'{DB_PATH}/stock_usa_min_back.db'
DB_COIN_TICK             = f'{DB_PATH}/coin_tick.db'
DB_COIN_MIN              = f'{DB_PATH}/coin_min.db'
DB_COIN_TICK_BACK        = f'{DB_PATH}/coin_tick_back.db'
DB_COIN_MIN_BACK         = f'{DB_PATH}/coin_min_back.db'
DB_FUTURE_TICK           = f'{DB_PATH}/future_tick.db'
DB_FUTURE_MIN            = f'{DB_PATH}/future_min.db'
DB_FUTURE_TICK_BACK      = f'{DB_PATH}/future_tick_back.db'
DB_FUTURE_MIN_BACK       = f'{DB_PATH}/future_min_back.db'
DB_FUTURE_NT_TICK        = f'{DB_PATH}/future_nt_tick.db'
DB_FUTURE_NT_MIN         = f'{DB_PATH}/future_nt_min.db'
DB_FUTURE_NT_TICK_BACK   = f'{DB_PATH}/future_nt_tick_back.db'
DB_FUTURE_NT_MIN_BACK    = f'{DB_PATH}/future_nt_min_back.db'
DB_FUTURE_OS_TICK        = f'{DB_PATH}/future_os_tick.db'
DB_FUTURE_OS_MIN         = f'{DB_PATH}/future_os_min.db'
DB_FUTURE_OS_TICK_BACK   = f'{DB_PATH}/future_os_tick_back.db'
DB_FUTURE_OS_MIN_BACK    = f'{DB_PATH}/future_os_min_back.db'
DB_COIN_FUTURE_TICK      = f'{DB_PATH}/coin_future_tick.db'
DB_COIN_FUTURE_MIN       = f'{DB_PATH}/coin_future_min.db'
DB_COIN_FUTURE_TICK_BACK = f'{DB_PATH}/coin_future_tick_back.db'
DB_COIN_FUTURE_MIN_BACK  = f'{DB_PATH}/coin_future_min_back.db'

LIST_BASIC_TICK = [
    'index', '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '체결강도', '초당매수수량', '초당매도수량',
    '초당거래대금', '고저평균대비등락율', '저가대비고가등락율', '초당매수금액', '초당매도금액',
    '당일매수금액', '최고매수금액', '최고매수가격', '당일매도금액', '최고매도금액', '최고매도가격',
    '매도호가1', '매도호가2', '매도호가3', '매도호가4', '매도호가5', '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5',
    '매도잔량1', '매도잔량2', '매도잔량3', '매도잔량4', '매도잔량5', '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5',
    '매도총잔량', '매수총잔량', '매도수5호가잔량합', '관심종목',
    '이동평균60', '이동평균150', '이동평균300', '이동평균600', '이동평균1200', '최고현재가', '최저현재가',
    '체결강도평균', '최고체결강도', '최저체결강도', '최고초당매수수량', '최고초당매도수량', '누적초당매수수량',
    '누적초당매도수량', '초당거래대금평균', '등락율각도', '당일거래대금각도'
]

LIST_BASIC_MIN = [
    'index', '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '체결강도', '분당매수수량', '분당매도수량',
    '분봉시가', '분봉고가', '분봉저가',
    '분당거래대금', '고저평균대비등락율', '저가대비고가등락율', '분당매수금액', '분당매도금액',
    '당일매수금액', '최고매수금액', '최고매수가격', '당일매도금액', '최고매도금액', '최고매도가격',
    '매도호가1', '매도호가2', '매도호가3', '매도호가4', '매도호가5', '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5',
    '매도잔량1', '매도잔량2', '매도잔량3', '매도잔량4', '매도잔량5', '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5',
    '매도총잔량', '매수총잔량', '매도수5호가잔량합', '관심종목',
    '이동평균5', '이동평균10', '이동평균20', '이동평균60', '이동평균120', '최고현재가', '최저현재가',
    '최고분봉고가', '최저분봉저가',
    '체결강도평균', '최고체결강도', '최저체결강도', '최고분당매수수량', '최고분당매도수량', '누적분당매수수량',
    '누적분당매도수량', '분당거래대금평균', '등락율각도', '당일거래대금각도',
    'AD', 'ADOSC', 'ADXR', 'APO', 'AROOND', 'AROONU', 'ATR', 'BBU', 'BBM', 'BBL', 'CCI', 'DIM', 'DIP', 'MACD', 'MACDS',
    'MACDH', 'MFI', 'MOM', 'OBV', 'PPO', 'ROC', 'RSI', 'SAR', 'STOCHSK', 'STOCHSD', 'STOCHFK', 'STOCHFD', 'WILLR'
]

LIST_STOCK_TICK = [
    'index', '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '체결강도', '초당매수수량', '초당매도수량', '시가총액',
    'VI해제시간', 'VI가격', 'VI호가단위',
    '초당거래대금', '고저평균대비등락율', '저가대비고가등락율', '초당매수금액', '초당매도금액',
    '당일매수금액', '최고매수금액', '최고매수가격', '당일매도금액', '최고매도금액', '최고매도가격',
    '매도호가1', '매도호가2', '매도호가3', '매도호가4', '매도호가5', '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5',
    '매도잔량1', '매도잔량2', '매도잔량3', '매도잔량4', '매도잔량5', '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5',
    '매도총잔량', '매수총잔량', '매도수5호가잔량합', '관심종목',
    '이동평균60', '이동평균150', '이동평균300', '이동평균600', '이동평균1200', '최고현재가', '최저현재가',
    '체결강도평균', '최고체결강도', '최저체결강도', '최고초당매수수량', '최고초당매도수량', '누적초당매수수량',
    '누적초당매도수량', '초당거래대금평균', '등락율각도', '당일거래대금각도'
]

LIST_STOCK_MIN = [
    'index', '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '체결강도', '분당매수수량', '분당매도수량', '시가총액',
    'VI해제시간', 'VI가격', 'VI호가단위', '분봉시가', '분봉고가', '분봉저가',
    '분당거래대금', '고저평균대비등락율', '저가대비고가등락율', '분당매수금액', '분당매도금액',
    '당일매수금액', '최고매수금액', '최고매수가격', '당일매도금액', '최고매도금액', '최고매도가격',
    '매도호가1', '매도호가2', '매도호가3', '매도호가4', '매도호가5', '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5',
    '매도잔량1', '매도잔량2', '매도잔량3', '매도잔량4', '매도잔량5', '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5',
    '매도총잔량', '매수총잔량', '매도수5호가잔량합', '관심종목',
    '이동평균5', '이동평균10', '이동평균20', '이동평균60', '이동평균120', '최고현재가', '최저현재가',
    '최고분봉고가', '최저분봉저가',
    '체결강도평균', '최고체결강도', '최저체결강도', '최고분당매수수량', '최고분당매도수량', '누적분당매수수량',
    '누적분당매도수량', '분당거래대금평균', '등락율각도', '당일거래대금각도',
    'AD', 'ADOSC', 'ADXR', 'APO', 'AROOND', 'AROONU', 'ATR', 'BBU', 'BBM', 'BBL', 'CCI', 'DIM', 'DIP', 'MACD', 'MACDS',
    'MACDH', 'MFI', 'MOM', 'OBV', 'PPO', 'ROC', 'RSI', 'SAR', 'STOCHSK', 'STOCHSD', 'STOCHFK', 'STOCHFD', 'WILLR'
]

LIST_STOCK_USA_TICK = [
    'index', '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '체결강도', '초당매수수량', '초당매도수량', '시가총액',
    '초당거래대금', '고저평균대비등락율', '저가대비고가등락율', '초당매수금액', '초당매도금액',
    '당일매수금액', '최고매수금액', '최고매수가격', '당일매도금액', '최고매도금액', '최고매도가격',
    '매도호가1', '매도호가2', '매도호가3', '매도호가4', '매도호가5', '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5',
    '매도잔량1', '매도잔량2', '매도잔량3', '매도잔량4', '매도잔량5', '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5',
    '매도총잔량', '매수총잔량', '매도수5호가잔량합', '관심종목',
    '이동평균60', '이동평균150', '이동평균300', '이동평균600', '이동평균1200', '최고현재가', '최저현재가',
    '체결강도평균', '최고체결강도', '최저체결강도', '최고초당매수수량', '최고초당매도수량', '누적초당매수수량',
    '누적초당매도수량', '초당거래대금평균', '등락율각도', '당일거래대금각도'
]

LIST_STOCK_USA_MIN = [
    'index', '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '체결강도', '분당매수수량', '분당매도수량', '시가총액',
    '분봉시가', '분봉고가', '분봉저가',
    '분당거래대금', '고저평균대비등락율', '저가대비고가등락율', '분당매수금액', '분당매도금액',
    '당일매수금액', '최고매수금액', '최고매수가격', '당일매도금액', '최고매도금액', '최고매도가격',
    '매도호가1', '매도호가2', '매도호가3', '매도호가4', '매도호가5', '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5',
    '매도잔량1', '매도잔량2', '매도잔량3', '매도잔량4', '매도잔량5', '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5',
    '매도총잔량', '매수총잔량', '매도수5호가잔량합', '관심종목',
    '이동평균5', '이동평균10', '이동평균20', '이동평균60', '이동평균120', '최고현재가', '최저현재가',
    '최고분봉고가', '최저분봉저가',
    '체결강도평균', '최고체결강도', '최저체결강도', '최고분당매수수량', '최고분당매도수량', '누적분당매수수량',
    '누적분당매도수량', '분당거래대금평균', '등락율각도', '당일거래대금각도',
    'AD', 'ADOSC', 'ADXR', 'APO', 'AROOND', 'AROONU', 'ATR', 'BBU', 'BBM', 'BBL', 'CCI', 'DIM', 'DIP', 'MACD', 'MACDS',
    'MACDH', 'MFI', 'MOM', 'OBV', 'PPO', 'ROC', 'RSI', 'SAR', 'STOCHSK', 'STOCHSD', 'STOCHFK', 'STOCHFD', 'WILLR'
]

LEN_LIST_STOCK_TICK     = len(LIST_STOCK_TICK)
LEN_LIST_STOCK_MIN      = len(LIST_STOCK_MIN)
LEN_LIST_BASIC_TICK     = len(LIST_BASIC_TICK)
LEN_LIST_BASIC_MIN      = len(LIST_BASIC_MIN)
LEN_LIST_STOCK_USA_TICK = len(LIST_STOCK_USA_TICK)
LEN_LIST_STOCK_USA_MIN  = len(LIST_STOCK_USA_MIN)

DICT_MARKET_GUBUN = {
    '국내주식01': 1,
    '국내주식02': 1,
    '국내주식ETF03': 2,
    '국내주식ETF04': 2,
    '국내주식ETN05': 3,
    '국내주식ETN06': 3,
    '해외주식07': 4,
    '해외주식08': 4,
    '업비트09': 5,
    '업비트10': 5,
    '지수선물11': 6,
    '지수선물12': 6,
    '야간선물13': 7,
    '야간선물14': 7,
    '해외선물15': 8,
    '해외선물16': 8,
    '바이낸스선물17': 9,
    '바이낸스선물18': 9,
}

DICT_MARKET_INFO = {
    1: {
        '마켓이름': '국내주식',
        '거래대금순위': 100,
        '반올림단위': 3,
        '시작시간': 90000,
        '종료시간': {0: 152000, 1: 100000},
        '프로세스종료시간': 153030,
        '각도계수': {0: [5, 0.01], 1: [5, 0.01]},
        '마켓구분': 'stock',
        '전략구분': 'stock',
        '종목디비': 'stock_info',
        '체결디비': 'stock_chegeollist',
        '잔고디비': 'stock_jangolist',
        '손익디비': 'stock_totaltradelist',
        '거래디비': 'stock_tradelist',
        '일자디비경로': {0: f'{DB_PATH}/stock_min', 1: f'{DB_PATH}/stock_tick'},
        '팩터목록': {0: LIST_STOCK_MIN,     1: LIST_STOCK_TICK},
        '팩터개수': {0: LEN_LIST_STOCK_MIN, 1: LEN_LIST_STOCK_TICK},
        '당일디비': {0: DB_STOCK_MIN,       1: DB_STOCK_TICK},
        '백테디비': {0: DB_STOCK_MIN_BACK,  1: DB_STOCK_TICK_BACK},
        '백테엔진': {0: BackEngineStock,    1: BackEngineStockOms},
        '프로세스': {0: StockReceiver,      1: StockTrader, 2: StockStrategy}
    },
    2: {
        '마켓이름': '국내주식',
        '거래대금순위': 10,
        '반올림단위': 3,
        '시작시간': 90000,
        '종료시간': {0: 152000, 1: 100000},
        '프로세스종료시간': 153030,
        '각도계수': {0: [5, 0.01], 1: [5, 0.01]},
        '마켓구분': 'stock',
        '전략구분': 'stock_etf',
        '종목디비': 'stock_etf_info',
        '체결디비': 'stock_etf_chegeollist',
        '잔고디비': 'stock_etf_jangolist',
        '손익디비': 'stock_etf_totaltradelist',
        '거래디비': 'stock_etf_tradelist',
        '일자디비경로': {0: f'{DB_PATH}/stock_etf_min', 1: f'{DB_PATH}/stock_etf_tick'},
        '팩터목록': {0: LIST_STOCK_MIN,        1: LIST_STOCK_TICK},
        '팩터개수': {0: LEN_LIST_STOCK_MIN,    1: LEN_LIST_STOCK_TICK},
        '당일디비': {0: DB_STOCK_ETF_MIN,      1: DB_STOCK_ETF_TICK},
        '백테디비': {0: DB_STOCK_ETF_MIN_BACK, 1: DB_STOCK_ETF_TICK_BACK},
        '백테엔진': {0: BackEngineStock,       1: BackEngineStockOms},
        '프로세스': {0: StockReceiver,         1: StockTrader, 2: StockStrategy}
    },
    3: {
        '마켓이름': '국내주식',
        '거래대금순위': 10,
        '반올림단위': 3,
        '시작시간': 90000,
        '종료시간': {0: 152000, 1: 100000},
        '프로세스종료시간': 153030,
        '각도계수': {0: [5, 0.01], 1: [5, 0.01]},
        '마켓구분': 'stock',
        '전략구분': 'stock_etn',
        '종목디비': 'stock_etn_info',
        '체결디비': 'stock_etn_chegeollist',
        '잔고디비': 'stock_etn_jangolist',
        '손익디비': 'stock_etn_totaltradelist',
        '거래디비': 'stock_etn_tradelist',
        '일자디비경로': {0: f'{DB_PATH}/stock_etn_min', 1: f'{DB_PATH}/stock_etn_tick'},
        '팩터목록': {0: LIST_STOCK_MIN,        1: LIST_STOCK_TICK},
        '팩터개수': {0: LEN_LIST_STOCK_MIN,    1: LEN_LIST_STOCK_TICK},
        '당일디비': {0: DB_STOCK_ETN_MIN,      1: DB_STOCK_ETN_TICK},
        '백테디비': {0: DB_STOCK_ETN_MIN_BACK, 1: DB_STOCK_ETN_TICK_BACK},
        '백테엔진': {0: BackEngineStock,       1: BackEngineStockOms},
        '프로세스': {0: StockReceiver,         1: StockTrader, 2: StockStrategy},
    },
    4: {
        '마켓이름': '해외주식',
        '거래대금순위': 100,
        '반올림단위': 5,
        '시작시간': 93000,
        '종료시간': {0: 160000, 1: 103000},
        '프로세스종료시간': 160030,
        '각도계수': {0: [5, 0.01], 1: [5, 0.01]},
        '마켓구분': 'stock',
        '전략구분': 'stock_usa',
        '종목디비': 'stock_usa_info',
        '체결디비': 'stock_usa_chegeollist',
        '잔고디비': 'stock_usa_jangolist',
        '손익디비': 'stock_usa_totaltradelist',
        '거래디비': 'stock_usa_tradelist',
        '일자디비경로': {0: f'{DB_PATH}/stock_usa_min', 1: f'{DB_PATH}/stock_usa_tick'},
        '팩터목록': {0: LIST_STOCK_USA_MIN,     1: LIST_STOCK_USA_TICK},
        '팩터개수': {0: LEN_LIST_STOCK_USA_MIN, 1: LEN_LIST_STOCK_USA_TICK},
        '당일디비': {0: DB_STOCK_USA_MIN,       1: DB_STOCK_USA_TICK},
        '백테디비': {0: DB_STOCK_USA_MIN_BACK,  1: DB_STOCK_USA_TICK_BACK},
        '백테엔진': {0: BackEngineStockUsa,     1: BackEngineStockUsaOms},
        '프로세스': {0: StockUsaReceiver,       1: StockUsaTrader, 2: StockUsaStrategy}
    },
    5: {
        '마켓이름': '업비트',
        '거래대금순위': 10,
        '반올림단위': 8,
        '시작시간': 0,
        '종료시간': {0: 235000, 1: 10000},
        '프로세스종료시간': 235030,
        '각도계수': {0: [10, 0.000_000_01], 1: [10, 0.000_000_01]},
        '마켓구분': 'coin',
        '전략구분': 'coin',
        '종목디비': 'coin_info',
        '체결디비': 'coin_chegeollist',
        '잔고디비': 'coin_jangolist',
        '손익디비': 'coin_totaltradelist',
        '거래디비': 'coin_tradelist',
        '일자디비경로': {0: f'{DB_PATH}/coin_min', 1: f'{DB_PATH}/coin_tick'},
        '팩터목록': {0: LIST_BASIC_MIN,     1: LIST_BASIC_TICK},
        '팩터개수': {0: LEN_LIST_BASIC_MIN, 1: LEN_LIST_BASIC_TICK},
        '당일디비': {0: DB_COIN_MIN,        1: DB_COIN_TICK},
        '백테디비': {0: DB_COIN_MIN_BACK,   1: DB_COIN_TICK_BACK},
        '백테엔진': {0: BackEngineUpbit,    1: BackEngineUpbitOms},
        '프로세스': {0: UpbitReceiver,      1: UpbitTrader, 2: UpbitStrategy}
    },
    6: {
        '마켓이름': '지수선물',
        '거래대금순위': 10,
        '반올림단위': 3,
        '시작시간': 84500,
        '종료시간': {0: 143500, 1: 100000},
        '프로세스종료시간': 154530,
        '각도계수': {0: [100, 0.000_000_05], 1: [100, 0.000_000_05]},
        '마켓구분': 'future',
        '전략구분': 'future',
        '종목디비': 'future_info',
        '체결디비': 'future_chegeollist',
        '잔고디비': 'future_jangolist',
        '손익디비': 'future_totaltradelist',
        '거래디비': 'future_tradelist',
        '일자디비경로': {0: f'{DB_PATH}/future_min', 1: f'{DB_PATH}/future_tick'},
        '팩터목록': {0: LIST_BASIC_MIN,     1: LIST_BASIC_TICK},
        '팩터개수': {0: LEN_LIST_BASIC_MIN, 1: LEN_LIST_BASIC_TICK},
        '당일디비': {0: DB_FUTURE_MIN,      1: DB_FUTURE_TICK},
        '백테디비': {0: DB_FUTURE_MIN_BACK, 1: DB_FUTURE_TICK_BACK},
        '백테엔진': {0: BackEngineFuture,   1: BackEngineFutureOms},
        '프로세스': {0: FutureReceiver,     1: FutureTrader, 2: FutureStrategy},
    },
    7: {
        '마켓이름': '야간선물',
        '거래대금순위': 10,
        '반올림단위': 3,
        '시작시간': 180000,
        '종료시간': {0: 60000, 1: 190000},
        '프로세스종료시간': 60030,
        '각도계수': {0: [100, 0.000_000_05], 1: [100, 0.000_000_05]},
        '마켓구분': 'future',
        '전략구분': 'future_nt',
        '종목디비': 'future_nt_info',
        '체결디비': 'future_nt_chegeollist',
        '잔고디비': 'future_nt_jangolist',
        '손익디비': 'future_nt_totaltradelist',
        '거래디비': 'future_nt_tradelist',
        '일자디비경로': {0: f'{DB_PATH}/future_nt_min', 1: f'{DB_PATH}/future_nt_tick'},
        '팩터목록': {0: LIST_BASIC_MIN,        1: LIST_BASIC_TICK},
        '팩터개수': {0: LEN_LIST_BASIC_MIN,    1: LEN_LIST_BASIC_TICK},
        '당일디비': {0: DB_FUTURE_NT_MIN,      1: DB_FUTURE_NT_TICK},
        '백테디비': {0: DB_FUTURE_NT_MIN_BACK, 1: DB_FUTURE_NT_TICK_BACK},
        '백테엔진': {0: BackEngineFuture,      1: BackEngineFutureOms},
        '프로세스': {0: FutureReceiver,        1: FutureTrader, 2: FutureStrategy}
    },
    8: {
        '마켓이름': '해외선물',
        '거래대금순위': 10,
        '반올림단위': 3,
        '시작시간': 93000,
        '종료시간': {0: 160000, 1: 103000},
        '프로세스종료시간': 160030,
        '각도계수': {0: [100, 0.000_000_05], 1: [100, 0.000_000_05]},
        '마켓구분': 'future',
        '전략구분': 'future_os',
        '종목디비': 'future_os_info',
        '체결디비': 'future_os_chegeollist',
        '잔고디비': 'future_os_jangolist',
        '손익디비': 'future_os_totaltradelist',
        '거래디비': 'future_os_tradelist',
        '일자디비경로': {0: f'{DB_PATH}/future_os_min', 1: f'{DB_PATH}/future_os_tick'},
        '팩터목록': {0: LIST_BASIC_MIN,          1: LIST_BASIC_TICK},
        '팩터개수': {0: LEN_LIST_BASIC_MIN,      1: LEN_LIST_BASIC_TICK},
        '당일디비': {0: DB_FUTURE_OS_MIN,        1: DB_FUTURE_OS_TICK},
        '백테디비': {0: DB_FUTURE_OS_MIN_BACK,   1: DB_FUTURE_OS_TICK_BACK},
        '백테엔진': {0: BackEngineFutureOversea, 1: BackEngineFutureOverseaOms},
        '프로세스': {0: FutureOsReceiver,        1: FutureOsTrader, 2: FutureOsStrategy},
    },
    9: {
        '마켓이름': '바이낸스선물',
        '거래대금순위': 10,
        '반올림단위': 8,
        '시작시간': 0,
        '종료시간': {0: 235000, 1: 10000},
        '프로세스종료시간': 235030,
        '각도계수': {0: [10, 0.000_000_01], 1: [10, 0.000_000_01]},
        '마켓구분': 'coin',
        '전략구분': 'coin_future',
        '종목디비': 'coin_future_info',
        '체결디비': 'coin_future_chegeollist',
        '잔고디비': 'coin_future_jangolist',
        '손익디비': 'coin_future_totaltradelist',
        '거래디비': 'coin_future_tradelist',
        '일자디비경로': {0: f'{DB_PATH}/coin_future_min', 1: f'{DB_PATH}/coin_future_tick'},
        '팩터목록': {0: LIST_BASIC_MIN,          1: LIST_BASIC_TICK},
        '팩터개수': {0: LEN_LIST_BASIC_MIN,      1: LEN_LIST_BASIC_TICK},
        '당일디비': {0: DB_COIN_FUTURE_MIN,      1: DB_COIN_FUTURE_TICK},
        '백테디비': {0: DB_COIN_FUTURE_MIN_BACK, 1: DB_COIN_FUTURE_TICK_BACK},
        '백테엔진': {0: BackEngineBinance,       1: BackEngineBinanceOms},
        '프로세스': {0: BinanceReceiver,         1: BinanceTrader, 2: BinanceStrategy}
    },
}
