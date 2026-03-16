
OPENAPI_PATH        = 'C:/OpenAPI'
ICON_PATH           = './ui/icon'
STOCK_LOGIN_PATH    = './trade/stock_korea/login_kiwoom'
FUTURE_LOGIN_PATH   = './trade/future_oversea/login_future'
GRAPH_PATH          = './backtest/graph'
BACK_TEMP           = './backtest/temp'
DB_PATH             = './_database'
DB_SETTING          = './_database/setting.db'
DB_BACKTEST         = './_database/backtest.db'
DB_TRADELIST        = './_database/tradelist.db'
DB_STRATEGY         = './_database/strategy.db'
DB_OPTUNA           = 'sqlite:///./_database/optuna.db'
DB_STOCK_TICK       = './_database/stock_tick.db'
DB_STOCK_MIN        = './_database/stock_min.db'
DB_STOCK_BACK_TICK  = './_database/stock_tick_back.db'
DB_STOCK_BACK_MIN   = './_database/stock_min_back.db'
DB_COIN_TICK        = './_database/coin_tick.db'
DB_COIN_MIN         = './_database/coin_min.db'
DB_COIN_BACK_TICK   = './_database/coin_tick_back.db'
DB_COIN_BACK_MIN    = './_database/coin_min_back.db'
DB_FUTURE_TICK      = './_database/future_tick.db'
DB_FUTURE_MIN       = './_database/future_min.db'
DB_FUTURE_BACK_TICK = './_database/future_tick_back.db'
DB_FUTURE_BACK_MIN  = './_database/future_min_back.db'
DB_CODE_INFO        = './_database/code_info.db'

ui_num = {'설정로그': 1, '종목명데이터': 2, '백테엔진': 3, '기본로그': 4, '타임로그': 5, '시스템로그': 6, 'S백테스트': 7, 'SF백테스트': 8,
          'C백테스트': 9, 'CF백테스트': 10, '사용자수식': 10.5, 'DB관리': 11, 'S실현손익': 12, 'S거래목록': 13, 'S잔고평가': 14, 'S잔고목록': 15,
          'S체결목록': 16, 'S당일합계': 17, 'S당일상세': 18, 'S누적합계': 19, 'S누적상세': 20, 'S관심종목': 21, 'C실현손익': 22,
          'C거래목록': 23, 'C잔고평가': 24, 'C잔고목록': 25, 'C체결목록': 26, 'C당일합계': 27, 'C당일상세': 28, 'C누적합계': 29,
          'C누적상세': 30, 'C관심종목': 31, 'S호가종목': 32, 'S호가체결': 33, 'S호가잔량': 34, 'C호가종목': 35, 'C호가체결': 36,
          'C호가잔량': 37, 'S호가체결2': 38, 'C호가체결2': 39, '스톰라이브1': 40, '스톰라이브2': 41, '스톰라이브3': 42,
          '스톰라이브4': 43, '스톰라이브5': 44, '스톰라이브6': 45, '스톰라이브7': 50, '스톰라이브8': 51, '스톰라이브9': 52,
          '스톰라이브10': 53, '스톰라이브11': 54, '김프': 55, '기업개요': 56, '기업공시': 57, '기업뉴스': 58, '재무년도': 59,
          '재무분기': 60, 'S상세기록': 61, 'C상세기록': 62, '차트': 63, '실시간차트': 64, '코스피': 65, '코스닥': 66, '트리맵': 67,
          '트리맵1': 68, '트리맵2': 69, '풍경사진': 70, '홈차트': 71}

columns_tt   = ['거래횟수', '총매수금액', '총매도금액', '총수익금액', '총손실금액', '수익률', '수익금합계']
columns_td   = ['종목명', '매수금액', '매도금액', '주문수량', '수익률', '수익금', '체결시간']
columns_tdf  = ['종목명', '포지션', '매수금액', '매도금액', '주문수량', '수익률', '수익금', '체결시간']
columns_tj   = ['추정예탁자산', '추정예수금', '보유종목수', '수익률', '총평가손익', '총매입금액', '총평가금액']
columns_jg   = ['종목명', '매수가', '현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량', '분할매수횟수', '분할매도횟수', '매수시간']
columns_cj   = ['종목명', '주문구분', '주문수량', '체결수량', '미체결수량', '체결가', '체결시간', '주문가격', '주문번호']
columns_gj   = ['종목명', 'per', 'hlp', 'lhp', 'ch', 'tm', 'dm', 'bm', 'sm']
columns_jgf  = ['종목명', '포지션', '매수가', '현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량', '분할매수횟수', '분할매도횟수', '매수시간']
columns_jgcf = ['종목명', '포지션', '매수가', '현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량', '레버리지', '분할매수횟수', '분할매도횟수', '매수시간']

columns_btf  = ['종목명', '포지션', '매수시간', '매도시간', '보유시간', '매수가', '매도가', '매수금액', '매도금액', '수익률', '수익금', '수익금합계', '매도조건', '추가매수시간']
columns_bt   = ['종목명', '시가총액', '매수시간', '매도시간', '보유시간', '매수가', '매도가', '매수금액', '매도금액', '수익률', '수익금', '수익금합계', '매도조건', '추가매수시간']
columns_dt   = ['거래일자', '누적매수금액', '누적매도금액', '누적수익금액', '누적손실금액', '수익률', '누적수익금']
columns_dd   = ['체결시간', '종목명', '매수금액', '매도금액', '주문수량', '수익률', '수익금']
columns_nt   = ['기간', '누적매수금액', '누적매도금액', '누적수익금액', '누적손실금액', '누적수익률', '누적수익금']
columns_nd   = ['일자', '총매수금액', '총매도금액', '총수익금액', '총손실금액', '수익률', '수익금합계']
columns_sb   = ['구분', '백테스트', '백파인더', '최적화', '최적화V', '최적화VC', '최적화T', '최적화VT', '최적화VCT',
                '최적화OG', '최적화OGV', '최적화OGVC', '최적화OC', '최적화OCV', '최적화OCVC', '전진분석', '전진분석V', '전진분석VC', '합계']
columns_sd   = ['period', 'time', 'dc', 'at', 'bet', 'seed', 'ttc', 'atc', 'mhc', 'aht', 'pc', 'mc', 'wr', 'app', 'tpp', 'mdd', 'tsg', 'cagr']

columns_vj   = ['배팅금액', '필요자금', '거래횟수', '일평균거래횟수', '최대보유종목수', '평균보유기간', '익절', '손절',
                '승률', '평균수익률', '수익률합계', '최대낙폭률', '수익금합계', '매매성능지수', '연간예상수익률', '매수전략', '매도전략']
columns_vc   = ['변수', '배팅금액', '필요자금', '거래횟수', '일평균거래횟수', '최대보유종목수', '평균보유기간', '익절', '손절', '승률',
                '평균수익률', '수익률합계', '최대낙폭률', '수익금합계', '매매성능지수', '연간예상수익률', '매수전략', '매도전략', '범위설정']

columns_hj   = ['종목명', '현재가', '등락율', '시가총액', 'UVI', '시가', '고가', '저가']
columns_hc   = ['체결수량', '체결강도']
columns_hc2  = ['팩터구분', '팩터값']
columns_hg   = ['잔량', '호가']

columns_ns   = ['일자', '언론사', '제목', '링크']
columns_gc   = ['일자', '정보제공', '공시', '링크']
columns_jm1  = ['', '', '', '', '']
columns_jm2  = ['', '', '', '', '', '']
columns_stg1 = ['매수전략', '매도전략', '최적화매수전략', '최적화매도전략']
columns_stg2 = ['최적화범위', 'GA범위', '매수조건', '매도조건']
columns_kp   = ['종목명', '바이낸스(달러)', '업비트(원)', '대비(원)', '대비율(%)']

list_stock_tick = [
    'index', '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '체결강도', '초당매수수량', '초당매도수량',
    '거래대금증감', '전일비', '회전율', '전일동시간비', '시가총액', '라운드피겨위5호가이내', 'VI해제시간', 'VI가격', 'VI호가단위',
    '초당거래대금', '고저평균대비등락율', '저가대비고가등락율', '초당매수금액', '초당매도금액',
    '당일매수금액', '최고매수금액', '최고매수가격', '당일매도금액', '최고매도금액', '최고매도가격',
    '매도호가5', '매도호가4', '매도호가3', '매도호가2', '매도호가1', '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5',
    '매도잔량5', '매도잔량4', '매도잔량3', '매도잔량2', '매도잔량1', '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5',
    '매도총잔량', '매수총잔량', '매도수5호가잔량합', '관심종목',
    '이동평균60', '이동평균150', '이동평균300', '이동평균600', '이동평균1200', '최고현재가', '최저현재가',
    '체결강도평균', '최고체결강도', '최저체결강도', '최고초당매수수량', '최고초당매도수량', '누적초당매수수량',
    '누적초당매도수량', '초당거래대금평균', '등락율각도', '당일거래대금각도', '전일비각도'
]

list_stock_min_base = [
    'index', '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '체결강도', '분당매수수량', '분당매도수량',
    '거래대금증감', '전일비', '회전율', '전일동시간비', '시가총액', '라운드피겨위5호가이내', 'VI해제시간', 'VI가격', 'VI호가단위',
    '분봉시가', '분봉고가', '분봉저가',
    '분당거래대금', '고저평균대비등락율', '저가대비고가등락율', '분당매수금액', '분당매도금액',
    '당일매수금액', '최고매수금액', '최고매수가격', '당일매도금액', '최고매도금액', '최고매도가격',
    '매도호가5', '매도호가4', '매도호가3', '매도호가2', '매도호가1', '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5',
    '매도잔량5', '매도잔량4', '매도잔량3', '매도잔량2', '매도잔량1', '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5',
    '매도총잔량', '매수총잔량', '매도수5호가잔량합', '관심종목',
    '이동평균5', '이동평균10', '이동평균20', '이동평균60', '이동평균120', '최고현재가', '최저현재가',
    '최고분봉고가', '최저분봉저가',
    '체결강도평균', '최고체결강도', '최저체결강도', '최고분당매수수량', '최고분당매도수량', '누적분당매수수량',
    '누적분당매도수량', '분당거래대금평균', '등락율각도', '당일거래대금각도', '전일비각도'
]

list_coin_tick = [
    'index', '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '체결강도', '초당매수수량', '초당매도수량',
    '초당거래대금', '고저평균대비등락율', '저가대비고가등락율', '초당매수금액', '초당매도금액',
    '당일매수금액', '최고매수금액', '최고매수가격', '당일매도금액', '최고매도금액', '최고매도가격',
    '매도호가5', '매도호가4', '매도호가3', '매도호가2', '매도호가1', '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5',
    '매도잔량5', '매도잔량4', '매도잔량3', '매도잔량2', '매도잔량1', '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5',
    '매도총잔량', '매수총잔량', '매도수5호가잔량합', '관심종목',
    '이동평균60', '이동평균150', '이동평균300', '이동평균600', '이동평균1200', '최고현재가', '최저현재가',
    '체결강도평균', '최고체결강도', '최저체결강도', '최고초당매수수량', '최고초당매도수량', '누적초당매수수량',
    '누적초당매도수량', '초당거래대금평균', '등락율각도', '당일거래대금각도'
]

list_coin_min_base = [
    'index', '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '체결강도', '분당매수수량', '분당매도수량',
    '분봉시가', '분봉고가', '분봉저가',
    '분당거래대금', '고저평균대비등락율', '저가대비고가등락율', '분당매수금액', '분당매도금액',
    '당일매수금액', '최고매수금액', '최고매수가격', '당일매도금액', '최고매도금액', '최고매도가격',
    '매도호가5', '매도호가4', '매도호가3', '매도호가2', '매도호가1', '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5',
    '매도잔량5', '매도잔량4', '매도잔량3', '매도잔량2', '매도잔량1', '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5',
    '매도총잔량', '매수총잔량', '매도수5호가잔량합', '관심종목',
    '이동평균5', '이동평균10', '이동평균20', '이동평균60', '이동평균120', '최고현재가', '최저현재가',
    '최고분봉고가', '최저분봉저가',
    '체결강도평균', '최고체결강도', '최저체결강도', '최고분당매수수량', '최고분당매도수량', '누적분당매수수량',
    '누적분당매도수량', '분당거래대금평균', '등락율각도', '당일거래대금각도'
]

list_chegyeol_colum1 = ['매수가', '매도가']
list_chegyeol_colum2 = ['매수가', '매도가', '매수가2', '매도가2']
list_indicator       = [
    'AD', 'ADOSC', 'ADXR', 'APO', 'AROOND', 'AROONU', 'ATR', 'BBU', 'BBM', 'BBL', 'CCI', 'DIM', 'DIP', 'MACD', 'MACDS',
    'MACDH', 'MFI', 'MOM', 'OBV', 'PPO', 'ROC', 'RSI', 'SAR', 'STOCHSK', 'STOCHSD', 'STOCHFK', 'STOCHFD', 'WILLR'
]

list_stock_min    = list_stock_min_base + list_indicator
list_coin_min     = list_coin_min_base + list_indicator
list_stock_tick2  = list_stock_tick + list_chegyeol_colum1
list_stock_min2   = list_stock_min_base + list_chegyeol_colum1 + list_indicator
list_coin_tick2   = list_coin_tick + list_chegyeol_colum1
list_coin_min2    = list_coin_min_base + list_chegyeol_colum1 + list_indicator
list_future_tick2 = list_coin_tick + list_chegyeol_colum2
list_future_min2  = list_coin_min_base + list_chegyeol_colum2 + list_indicator

dict_order_ratio = {
    1: {
        5: {
            0: 20.00, 1: 20.00, 2: 20.00, 3: 20.00, 4: 20.00
        },
        4: {
            0: 25.00, 1: 25.00, 2: 25.00, 3: 25.00
        },
        3: {
            0: 33.33, 1: 33.33, 2: 33.33
        },
        2: {
            0: 50.00, 1: 50.00
        },
        1: {
            0: 100.00
        }
    },
    2: {
        5: {
            0: 51.61, 1: 25.81, 2: 12.90, 3: 6.45, 4: 3.23
        },
        4: {
            0: 53.33, 1: 26.67, 2: 13.33, 3: 6.67
        },
        3: {
            0: 57.14, 1: 28.57, 2: 14.29
        },
        2: {
            0: 66.67, 1: 33.33
        },
        1: {
            0: 100.00
        }
    },
    3: {
        5: {
            0: 3.23, 1: 6.45, 2: 12.90, 3: 25.81, 4: 51.61
        },
        4: {
            0: 6.67, 1: 13.33, 2: 26.67, 3: 53.33
        },
        3: {
            0: 14.29, 1: 28.57, 2: 57.14
        },
        2: {
            0: 33.33, 1: 66.67
        },
        1: {
            0: 100.00
        }
    }
}

indi_base = {
    'ADOSC_fastperiod': 3,
    'ADOSC_slowperiod': 10,
    'ADXR_timeperiod': 14,
    'APO_fastperiod': 12,
    'APO_slowperiod': 26,
    'APO_matype': 0,
    'AROON_timeperiod': 14,
    'ATR_timeperiod': 14,
    'BBANDS_timeperiod': 5,
    'BBANDS_nbdevup': 2,
    'BBANDS_nbdevdn': 2,
    'BBANDS_matype': 0,
    'CCI_timeperiod': 14,
    'DI_timeperiod': 14,
    'MACD_fastperiod': 12,
    'MACD_slowperiod': 26,
    'MACD_signalperiod': 9,
    'MFI_timeperiod': 14,
    'MOM_timeperiod': 10,
    'PPO_fastperiod': 12,
    'PPO_slowperiod': 26,
    'PPO_matype': 0,
    'ROC_timeperiod': 10,
    'RSI_timeperiod': 14,
    'SAR_acceleration': 0.02,
    'SAR_maximum': 0.2,
    'STOCHS_fastk_period': 5,
    'STOCHS_slowk_period': 3,
    'STOCHS_slowk_matype': 0,
    'STOCHS_slowd_period': 3,
    'STOCHS_slowd_matype': 0,
    'STOCHF_fastk_period': 5,
    'STOCHF_fastd_period': 3,
    'STOCHF_fastd_matype': 0,
    'WILLR_timeperiod': 14
}

indicator = {
    'ADOSC_fastperiod': 0,
    'ADOSC_slowperiod': 0,
    'ADXR_timeperiod': 0,
    'APO_fastperiod': 0,
    'APO_slowperiod': 0,
    'APO_matype': 0,
    'AROON_timeperiod': 0,
    'ATR_timeperiod': 0,
    'BBANDS_timeperiod': 0,
    'BBANDS_nbdevup': 0,
    'BBANDS_nbdevdn': 0,
    'BBANDS_matype': 0,
    'CCI_timeperiod': 0,
    'DI_timeperiod': 0,
    'MACD_fastperiod': 0,
    'MACD_slowperiod': 0,
    'MACD_signalperiod': 0,
    'MFI_timeperiod': 0,
    'MOM_timeperiod': 0,
    'PPO_fastperiod': 0,
    'PPO_slowperiod': 0,
    'PPO_matype': 0,
    'ROC_timeperiod': 0,
    'RSI_timeperiod': 0,
    'SAR_acceleration': 0,
    'SAR_maximum': 0,
    'STOCHS_fastk_period': 0,
    'STOCHS_slowk_period': 0,
    'STOCHS_slowk_matype': 0,
    'STOCHS_slowd_period': 0,
    'STOCHS_slowd_matype': 0,
    'STOCHF_fastk_period': 0,
    'STOCHF_fastd_period': 0,
    'STOCHF_fastd_matype': 0,
    'WILLR_timeperiod': 0
}
