"""기본 설정 모듈입니다.
경로, UI 번호, 컬럼 정의 등 기본 설정을 포함합니다.
"""
DB_PATH      = './_database'
LOG_PATH     = './_log'
BACK_PATH    = './backtest'
ICON_PATH    = './ui/_icon'
GRAPH_PATH   = f'{BACK_PATH}/_graph'
BACK_TEMP    = f'{BACK_PATH}/_temp'
DB_SETTING   = f'{DB_PATH}/setting.db'
DB_BACKTEST  = f'{DB_PATH}/backtest.db'
DB_TRADELIST = f'{DB_PATH}/tradelist.db'
DB_STRATEGY  = f'{DB_PATH}/strategy.db'
DB_CODE_INFO = f'{DB_PATH}/code_info.db'
DB_OPTUNA    = f'sqlite:///{DB_PATH}/optuna.db'

UI_NUM = {'설정로그': 1, '종목명데이터': 2, '백테엔진': 3, '기본로그': 4, '타임로그': 5,
          '시스템로그': 6, '백테스트': 7, '사용자수식': 8, 'DB관리': 9,  '학습로그': 10,
          '실현손익': 11, '거래목록': 12, '잔고평가': 13, '잔고목록': 14, '체결목록': 15,
          '당일합계': 16, '당일상세': 17, '누적합계': 18, '누적상세': 19, '관심종목': 20,
          '호가종목': 21, '호가체결': 22, '호가잔량': 23, '호가체결2': 24, '스톰라이브1': 25,
          '스톰라이브2': 26, '스톰라이브3': 27, '스톰라이브4': 28, '스톰라이브5': 29, '스톰라이브6': 30,
          '스톰라이브7': 31, '스톰라이브8': 32, '스톰라이브9': 33, '스톰라이브10': 34, '스톰라이브11': 35,
          '김프': 36, '기업개요': 37, '기업공시': 38, '기업뉴스': 39, '재무년도': 40,
          '재무분기': 41, '상세기록': 42, '차트': 43, '실시간차트': 44, '코스피': 45,
          '코스닥': 46, '트리맵': 47, '트리맵1': 48, '트리맵2': 49, '풍경사진': 50,
          '홈차트': 51}

COLUMNS_TT   = ['거래횟수', '총매수금액', '총매도금액', '총수익금액', '총손실금액', '수익률', '수익금합계']
COLUMNS_TD   = ['종목명', '매수금액', '매도금액', '주문수량', '수익률', '수익금', '체결시간']
COLUMNS_TDF  = ['종목명', '포지션', '매수금액', '매도금액', '주문수량', '수익률', '수익금', '체결시간']
COLUMNS_TJ   = ['추정예탁자산', '추정예수금', '보유종목수', '수익률', '총평가손익', '총매입금액', '총평가금액']
COLUMNS_JG   = ['종목명', '매수가', '현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량', '분할매수횟수', '분할매도횟수',
                '매수시간']
COLUMNS_JGF  = ['종목명', '포지션', '매수가', '현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량', '분할매수횟수',
                '분할매도횟수', '매수시간']
COLUMNS_JGCF = COLUMNS_JGF + ['레버리지']
COLUMNS_CG   = ['종목명', '주문구분', '주문수량', '체결수량', '미체결수량', '체결가', '체결시간', '주문가격', '주문번호']
COLUMNS_GJ   = ['종목명', 'per', 'hlp', 'lhp', 'ch', 'tm', 'dm', 'bm', 'sm']

COLUMNS_BRT  = ['종목명', '시가총액', '매수시간', '매도시간', '보유시간', '매수가', '매도가', '매수금액', '매도금액', '수익률',
                '수익금', '수익금합계', '매도조건', '추가매수시간']
COLUMNS_BRTF = ['종목명', '포지션', '매수시간', '매도시간', '보유시간', '매수가', '매도가', '매수금액', '매도금액', '수익률',
                '수익금', '수익금합계', '매도조건', '추가매수시간']
COLUMNS_DTT  = ['거래일자', '누적매수금액', '누적매도금액', '누적수익금액', '누적손실금액', '수익률', '누적수익금']
COLUMNS_DTD  = ['체결시간', '종목명', '매수금액', '매도금액', '주문수량', '수익률', '수익금']
COLUMNS_NTT  = ['기간', '누적매수금액', '누적매도금액', '누적수익금액', '누적손실금액', '누적수익률', '누적수익금']
COLUMNS_NTD  = ['일자', '총매수금액', '총매도금액', '총수익금액', '총손실금액', '수익률', '수익금합계']
COLUMNS_SLBT = ['구분', '백테스트', '백파인더', '최적화', '최적화V', '최적화VC', '최적화T', '최적화VT', '최적화VCT',
                '최적화OG', '최적화OGV', '최적화OGVC', '최적화OC', '최적화OCV', '최적화OCVC', '전진분석', '전진분석V',
                '전진분석VC', '합계']
COLUMNS_SLBD = ['period', 'time', 'dc', 'at', 'bet', 'seed', 'ttc', 'atc', 'mhc', 'aht', 'pc', 'mc', 'wr', 'app',
                'tpp', 'mdd', 'tsg', 'cagr']

COLUMNS_BBS  = ['배팅금액', '필요자금', '거래횟수', '일평균거래횟수', '최대보유종목수', '평균보유기간', '익절', '손절',
                '승률', '평균수익률', '수익률합계', '최대낙폭률', '수익금합계', '매매성능지수', '연간예상수익률', '매수전략', '매도전략']
COLUMNS_BOS  = ['변수', '배팅금액', '필요자금', '거래횟수', '일평균거래횟수', '최대보유종목수', '평균보유기간', '익절', '손절', '승률',
                '평균수익률', '수익률합계', '최대낙폭률', '수익금합계', '매매성능지수', '연간예상수익률', '매수전략', '매도전략', '범위설정']

COLUMNS_HJ   = ['종목명', '현재가', '등락율', '시가총액', 'UVI', '시가', '고가', '저가']
COLUMNS_HC   = ['체결수량', '체결강도']
COLUMNS_HC2  = ['팩터구분', '팩터값']
COLUMNS_HG   = ['잔량', '호가']

COLUMNS_GNS  = ['일자', '언론사', '제목', '링크']
COLUMNS_GGS  = ['일자', '정보제공', '공시', '링크']
COLUMNS_JM1  = ['', '', '', '', '']
COLUMNS_JM2  = ['', '', '', '', '', '']
COLUMNS_DSG  = ['매수전략', '매도전략', '최적화매수전략', '최적화매도전략']
COLUMNS_DSV  = ['최적화범위', 'GA범위', '매수조건', '매도조건']
COLUMNS_KIMP = ['종목명', '바이낸스(달러)', '업비트(원)', '대비(원)', '대비율(%)']

CODE_INFO_TABLES = [
    'stock_info', 'stock_etf_info', 'stock_etn_info', 'stock_usa_info', 'coin_info', 'future_info',
    'future_nt_info', 'future_os_info', 'coin_future_info'
]

DICT_ORDER_RATIO = {
    1: {
        10: {
            0: 10.00, 1: 10.00, 2: 10.00, 3: 10.00, 4: 10.00, 5: 10.00, 6: 10.00, 7: 10.00, 8: 10.00, 9: 10.00
        },
        9: {
            0: 11.11, 1: 11.11, 2: 11.11, 3: 11.11, 4: 11.11, 5: 11.11, 6: 11.11, 7: 11.11, 8: 11.11
        },
        8: {
            0: 12.50, 1: 12.50, 2: 12.50, 3: 12.50, 4: 12.50, 5: 12.50, 6: 12.50, 7: 12.50
        },
        7: {
            0: 14.29, 1: 14.29, 2: 14.29, 3: 14.29, 4: 14.29, 5: 14.29, 6: 14.29
        },
        6: {
            0: 16.67, 1: 16.67, 2: 16.67, 3: 16.67, 4: 16.67, 5: 16.67
        },
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
        10: {
            0: 51.61, 1: 25.81, 2: 12.90, 3: 6.45, 4: 3.23, 5: 1.61, 6: 0.81, 7: 0.40, 8: 0.20, 9: 0.10
        },
        9: {
            0: 53.33, 1: 26.67, 2: 13.33, 3: 6.67, 4: 3.33, 5: 1.67, 6: 0.83, 7: 0.42, 8: 0.21
        },
        8: {
            0: 55.56, 1: 27.78, 2: 13.89, 3: 6.94, 4: 3.47, 5: 1.74, 6: 0.87, 7: 0.43
        },
        7: {
            0: 57.14, 1: 28.57, 2: 14.29, 3: 7.14, 4: 3.57, 5: 1.79, 6: 0.89
        },
        6: {
            0: 60.00, 1: 30.00, 2: 15.00, 3: 7.50, 4: 3.75, 5: 1.88
        },
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
        10: {
            0: 0.10, 1: 0.20, 2: 0.40, 3: 0.81, 4: 1.61, 5: 3.23, 6: 6.45, 7: 12.90, 8: 25.81, 9: 51.61
        },
        9: {
            0: 0.21, 1: 0.42, 2: 0.83, 3: 1.67, 4: 3.33, 5: 6.67, 6: 13.33, 7: 26.67, 8: 53.33
        },
        8: {
            0: 0.43, 1: 0.87, 2: 1.74, 3: 3.47, 4: 6.94, 5: 13.89, 6: 27.78, 7: 55.56
        },
        7: {
            0: 0.89, 1: 1.79, 2: 3.57, 3: 7.14, 4: 14.29, 5: 28.57, 6: 57.14
        },
        6: {
            0: 1.88, 1: 3.75, 2: 7.50, 3: 15.00, 4: 30.00, 5: 60.00
        },
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

DICT_INDICATOR_BASE = {
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

DICT_INDICATOR = {
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
