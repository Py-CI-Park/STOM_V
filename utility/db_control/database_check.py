
import os
import sqlite3
import pandas as pd
from traceback import format_exc
from utility.settings.setting_base import code_info_tables
from utility.static_method.static import read_key, write_key

MAIN_CLOUMNS = [
    'index', '거래소', '타임프레임', '데이터저장', '모의투자', '알림소리', '프로그램비밀번호', '바이낸스선물고정레버리지',
    '바이낸스선물고정레버리지값', '바이낸스선물변동레버리지값', '바이낸스선물마진타입', '바이낸스선물포지션'
]
MAIN_DATA = [
    [0, '국내주식01', 1, 1, 1, 1, '', 1, 1, '0;5;1^5;10;2^10;20;3^20;30;4^30;100;5', 'ISOLATED', 'false']
]

ACCOUNT_CLOUMNS = ["index", "access_key", "secret_key"]
ACCOUNT_DATA = [
    [1, '', ''], [2, '', ''], [3, '', ''], [4, '', ''], [5, '', ''], [6, '', ''],
    [7, '', ''], [8, '', ''], [9, '', ''], [10, '', ''], [11, '', ''], [12, '', ''],
    [13, '', ''], [14, '', ''], [15, '', ''], [16, '', ''], [17, '', ''], [18, '', '']
]

TELE_CLOUMNS = ["index", "bot_token", "chatingid"]
TELE_DATA = [
    [1, '', ''], [2, '', ''], [3, '', ''], [4, '', ''], [5, '', ''], [6, '', ''],
    [7, '', ''], [8, '', ''], [9, '', ''], [10, '', ''], [11, '', ''], [12, '', ''],
    [13, '', ''], [14, '', ''], [15, '', ''], [16, '', ''], [17, '', ''], [18, '', '']
]

STG_CLOUMNS = [
    "index", "매수전략", "매도전략", "평균값계산틱수", "최대매수종목수",
    "전략종료시간", "잔고청산", "프로세스종료", "컴퓨터종료", "투자금고정", "투자금", "손실중지",
    "손실중지수익률", "수익중지", "수익중지수익률", "블랙리스트"
]
STG_DATA = [
    [1, '', '', 30, 10, 93000, 1, 1, 0, 1, 20.0, 0, 2.0, 0, 2.0, ''],
    [2, '', '', 30, 10, 152000, 1, 1, 0, 1, 20.0, 0, 2.0, 0, 2.0, ''],
    [3, '', '', 30, 10, 93000, 1, 1, 0, 1, 20.0, 0, 2.0, 0, 2.0, ''],
    [4, '', '', 30, 10, 152000, 1, 1, 0, 1, 20.0, 0, 2.0, 0, 2.0, ''],
    [5, '', '', 30, 10, 93000, 1, 1, 0, 1, 20.0, 0, 2.0, 0, 2.0, ''],
    [6, '', '', 30, 10, 152000, 1, 1, 0, 1, 20.0, 0, 2.0, 0, 2.0, ''],
    [7, '', '', 30, 10, 103000, 1, 1, 0, 1, 20.0, 0, 2.0, 0, 2.0, ''],
    [8, '', '', 30, 10, 160000, 1, 1, 0, 1, 20.0, 0, 2.0, 0, 2.0, ''],
    [9, '', '', 30, 10, 10000, 1, 1, 0, 1, 1000.0, 0, 2.0, 0, 2.0, ''],
    [10, '', '', 30, 10, 235000, 1, 1, 0, 1, 1000.0, 0, 2.0, 0, 2.0, ''],
    [11, '', '', 30, 10, 100000, 1, 1, 0, 1, 1.0, 0, 2.0, 0, 2.0, ''],
    [12, '', '', 30, 10, 143500, 1, 1, 0, 1, 1.0, 0, 2.0, 0, 2.0, ''],
    [13, '', '', 30, 10, 190000, 1, 1, 0, 1, 1.0, 0, 2.0, 0, 2.0, ''],
    [14, '', '', 30, 10, 60000, 1, 1, 0, 1, 1.0, 0, 2.0, 0, 2.0, ''],
    [15, '', '', 30, 10, 103000, 1, 1, 0, 1, 1.0, 0, 2.0, 0, 2.0, ''],
    [16, '', '', 30, 10, 160000, 1, 1, 0, 1, 1.0, 0, 2.0, 0, 2.0, ''],
    [17, '', '', 30, 10, 10000, 1, 1, 0, 1, 1000.0, 0, 2.0, 0, 2.0, ''],
    [18, '', '', 30, 10, 235000, 1, 1, 0, 1, 1000.0, 0, 2.0, 0, 2.0, ''],
]

BACT_CLOUMNS = [
    "index", "블랙리스트추가", "백테주문관리적용", "백테매수시간기준", "백테일괄로딩", "그래프저장하지않기", "그래프띄우지않기",
    "디비자동관리", "교차검증가중치", "기준값최소상승률", "백테스케쥴실행", "백테스케쥴요일", "백테스케쥴시간",
    "백테스케쥴명", "백테날짜고정", "백테날짜", "최적화기준값제한", "백테엔진분류방법", "옵튜나샘플러", "옵튜나고정변수",
    "옵튜나실행횟수", "옵튜나자동스탭", "범위자동관리", "보조지표설정", "백테스트로그기록안함", "시장미시구조분석", '리스크분석',
    "자동학습", "패턴분석", "가격대분석"
]

BACT_DATA_BASE = [
    0, 0, 0, 1, 0, 0, 1, 1, 2, 0, 4, 160000, '', 0, '365',
    '0.0;1000.0;0;100.0;0.0;100.0;-10.0;10.0;0.0;1000.0;-10000.0;10000.0;0.0;100.0',
    '종목코드별 분류', 'TPESampler', '', 0, 0, 0,
    '3;10;14;12;26;0;14;14;5;2;2;0;14;14;12;26;9;14;10;12;26;0;10;14;0.02;0.2;5;3;0;3;0;5;3;0;14',
    0, 0, 0, 0, 0, 0
]
BACT_DATA = [[i+1] + BACT_DATA_BASE for i in range(18)]

ETC_CLOUMNS = [
    "index", "테마", "저해상도", "휴무프로세스종료", "휴무컴퓨터종료", "창위치기억", "창위치", "스톰라이브",
    "프로그램종료", "웹대시보드", "웹대시보드포트번호", "팩터선택", "시가총액상위제외목록", "시리얼키"
]
EXCLUSION_LIST = [
    '000150', '000270', '000660', '000720', '000810', '003230', '003550', '003670', '005380', '005490',
    '005830', '005930', '005940', '006260', '006400', '006800', '007660', '009150', '009540', '010120',
    '010130', '010140', '010950', '011070', '011200', '012330', '012450', '0126Z0', '015760', '017670',
    '018260', '024110', '028260', '030200', '032830', '033780', '034020', '034730', '035420', '035720',
    '039490', '042660', '042700', '047040', '047050', '047810', '051910', '055550', '064350', '066570',
    '068270', '071050', '079550', '086280', '086520', '086790', '096770', '105560', '138040', '196170',
    '207940', '247540', '259960', '267250', '267260', '272210', '277810', '278470', '298040', '307950',
    '316140', '323410', '329180', '352820', '373220', '402340', '443060'
]
ETC_DATA_BASE = [
    '다크블루', 0, 1, 1, 1, '', 1, 1, 0, 3000, ';'.join(['1'] * 38), ';'.join(EXCLUSION_LIST), ''
]
ETC_DATA = [[i+1] + ETC_DATA_BASE for i in range(18)]

BORDER_CLOUMNS = [
    'index', '매수주문유형', '매수분할횟수', '매수분할방법', '매수분할시그널', '매수분할하방', '매수분할상방',
    '매수분할하방수익률', '매수분할상방수익률', '매수분할고정수익률', '매수지정가기준가격', '매수지정가호가번호',
    '매수시장가잔량범위', '매수취소관심이탈', '매수취소매도시그널', '매수취소시간', '매수취소시간초', '매수금지블랙리스트',
    '매수금지손절횟수', '매수금지손절횟수값', '매수금지거래횟수',
    '매수금지거래횟수값', '매수금지시간', '매수금지시작시간', '매수금지종료시간', '매수금지간격', '매수금지간격초',
    '매수금지손절간격', '매수금지손절간격초', '매수정정횟수', '매수정정호가차이', '매수정정호가', '비중조절'
]
BORDER_DATA_BASE = [
    '시장가', 1, 2, 1, 0, 1, 0.5, 0.5, 1, '매수1호가', 0, 3, 0, 0, 0, 30, 0, 0, 2, 0, 2, 0,
    120000, 130000, 0, 5, 0, 300, 0, 5, 2, '0;0;0;0;0;1;1;1;1;1'
]
BORDER_DATA = [[i+1] + BORDER_DATA_BASE for i in range(18)]

SORDER_CLOUMNS = [
    'index', '매도주문유형', '매도분할횟수', '매도분할방법', '매도분할시그널', '매도분할하방', '매도분할상방',
    '매도분할하방수익률', '매도분할상방수익률', '매도지정가기준가격', '매도지정가호가번호', '매도시장가잔량범위',
    '매도취소관심진입', '매도취소매수시그널', '매도취소시간', '매도취소시간초', '매도금지매수횟수',
    '매도금지매수횟수값', '매도금지시간', '매도금지시작시간',
    '매도금지종료시간', '매도금지간격', '매도금지간격초', '매도정정횟수', '매도정정호가차이', '매도정정호가',
    '매도익절수익률청산', '매도익절수익률', '매도익절수익금청산', '매도익절수익금',
    '매도손절수익률청산', '매도손절수익률', '매도손절수익금청산', '매도손절수익금'
]
SORDER_DATA_BASE = [
    '시장가', 1, 1, 1, 0, 1, 0.5, 2.0, '매도1호가', 0, 5, 0, 0, 0, 30, 0, 2, 0,
    120000, 130000, 0, 300, 0, 5, 2, 0, 5, 0, 1_000_000, 0, 5, 0, 1_000_000
]
SORDER_DATA = [[i+1] + SORDER_DATA_BASE for i in range(18)]


def database_check():
    """데이터베이스를 초기화하고 검사합니다.
    필요한 디렉토리와 데이터베이스 파일을 생성하고,
    설정 테이블을 초기화합니다.
    """
    try:
        os.makedirs('./_log', exist_ok=True)
        os.makedirs('./_database', exist_ok=True)
        os.makedirs('./backtest/_temp', exist_ok=True)
        os.makedirs('./backtest/_graph', exist_ok=True)

        DB_PATH       = './_database'
        DB_SETTING    = f'{DB_PATH}/setting.db'
        DB_TRADELIST  = f'{DB_PATH}/tradelist.db'
        DB_STRATEGY   = f'{DB_PATH}/strategy.db'
        DB_CODE_INFO  = f'{DB_PATH}/code_info.db'

        try:
            read_key()
        except Exception:
            write_key()

        # --------------------------------------------------------------------------------------------------------------

        con = sqlite3.connect(DB_SETTING)
        df  = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
        table_list = df['name'].to_list()

        if 'main' not in table_list:
            df = pd.DataFrame(MAIN_DATA, columns=MAIN_CLOUMNS).set_index('index')
            df.to_sql('main', con)

        if 'account' not in table_list:
            df = pd.DataFrame(ACCOUNT_DATA, columns=ACCOUNT_CLOUMNS).set_index('index')
            df.to_sql('account', con)

        if 'telegram' not in table_list:
            df = pd.DataFrame(TELE_DATA, columns=TELE_CLOUMNS).set_index('index')
            df.to_sql('telegram', con)

        if 'strategy' not in table_list:
            df = pd.DataFrame(STG_DATA, columns=STG_CLOUMNS).set_index('index')
            df.to_sql('strategy', con)

        if 'back' not in table_list:
            df = pd.DataFrame(BACT_DATA, columns=BACT_CLOUMNS).set_index('index')
            df.to_sql('back', con)

        if 'etc' not in table_list:
            df = pd.DataFrame(ETC_DATA, columns=ETC_CLOUMNS).set_index('index')
            df.to_sql('etc', con)

        if 'buyorder' not in table_list:
            df = pd.DataFrame(BORDER_DATA, columns=BORDER_CLOUMNS).set_index('index')
            df.to_sql('buyorder', con)

        if 'sellorder' not in table_list:
            df = pd.DataFrame(SORDER_DATA, columns=SORDER_CLOUMNS).set_index('index')
            df.to_sql('sellorder', con)

        con.close()

        # --------------------------------------------------------------------------------------------------------------

        con = sqlite3.connect(DB_CODE_INFO)
        df  = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
        table_list = df['name'].to_list()

        if 'stock_info' not in table_list:
            columns = ['index', '종목명']
            data = ['005930', '삼성전자']
            df = pd.DataFrame([data], columns=columns).set_index('index')
            df.to_sql('stock_info', con)

        if 'stock_etf_info' not in table_list:
            columns = ['index', '종목명']
            data = ['005930', '삼성전자']
            df = pd.DataFrame([data], columns=columns).set_index('index')
            df.to_sql('stock_etf_info', con)

        if 'stock_etn_info' not in table_list:
            columns = ['index', '종목명']
            data = ['005930', '삼성전자']
            df = pd.DataFrame([data], columns=columns).set_index('index')
            df.to_sql('stock_etn_info', con)

        if 'stock_usa_info' not in table_list:
            columns = ['index', '종목명', '거래소코드', '상장주식수']
            data = ['AAPL', '애플', '82', 14681100000]
            df = pd.DataFrame([data], columns=columns).set_index('index')
            df.to_sql('stock_usa_info', con)

        if 'future_info' not in table_list:
            columns = ['index', '종목명', '위탁증거금', '호가단위', '틱가치', '소숫점자리수']
            data = ['A0166000', '코스피200', 5000, 0.25, 20.0, 2]
            df = pd.DataFrame([data], columns=columns).set_index('index')
            df.to_sql('future_info', con)

        if 'future_nt_info' not in table_list:
            columns = ['index', '종목명', '위탁증거금', '호가단위', '틱가치', '소숫점자리수']
            data = ['A0166000', '코스피200', 5000, 0.25, 20.0, 2]
            df = pd.DataFrame([data], columns=columns).set_index('index')
            df.to_sql('future_nt_info', con)

        if 'future_os_info' not in table_list:
            columns = ['index', '종목명', '위탁증거금', '호가단위', '틱가치', '소숫점자리수']
            data = ['LSCH27', 'Steel Scrap(2027.03)', 330, 0.5, 5.0, 2]
            df = pd.DataFrame([data], columns=columns).set_index('index')
            df.to_sql('future_os_info', con)

        if 'coin_info' not in table_list:
            columns = ['index', '종목명', '거래대금']
            data = ['KRW-BTC', 'KRW-BTC', 5000]
            df = pd.DataFrame([data], columns=columns).set_index('index')
            df.to_sql('coin_info', con)

        if 'coin_future_info' not in table_list:
            columns = ['index', '종목명', '호가단위', '가격소숫점자리수', '수량소숫점자리수']
            data = ['BTSUSDT', 'BTSUSDT', 1, 1, 1]
            df = pd.DataFrame([data], columns=columns).set_index('index')
            df.to_sql('coin_future_info', con)

        con.close()

        # --------------------------------------------------------------------------------------------------------------

        con = sqlite3.connect(DB_STRATEGY)
        cur = con.cursor()
        df  = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
        table_list = df['name'].to_list()

        market_list = [
            'stock', 'stock_etf', 'stock_etn', 'stock_usa', 'future', 'future_nt', 'future_os', 'coin', 'coin_future'
        ]
        endname_list = [
            '_buy', '_sell', '_optibuy', '_optisell', '_optivars', '_optigavars', '_buyconds', '_sellconds', '_passticks'
        ]

        for market in market_list:
            for endname in endname_list:
                table_name = f'{market}{endname}'
                if table_name not in table_list:
                    if endname != '_optibuy':
                        cur.execute(f'''
                            CREATE TABLE {table_name} (
                                'index' TEXT,
                                '전략코드' TEXT,
                                PRIMARY KEY ('index')
                            )
                        ''')
                    else:
                        cur.execute(f'''
                            CREATE TABLE {table_name} (
                                'index' TEXT,
                                '전략코드' TEXT,
                                '변수값' TEXT,
                                PRIMARY KEY ('index')
                            )
                        ''')

        # --------------------------------------------------------------------------------------------------------------

        if 'schedule' not in table_list:
            cur.execute('''
                CREATE TABLE schedule (
                    'index' TEXT,
                    '스케쥴' TEXT,
                    PRIMARY KEY ('index')
                )
            ''')

        if 'custombutton' not in table_list:
            cur.execute('''
                CREATE TABLE custombutton (
                    'index' INTEGER,
                    '버튼명' TEXT,
                    '전략코드' TEXT,
                    PRIMARY KEY ('index')
                    )
            ''')

        if 'formula' not in table_list:
            cur.execute('''
                CREATE TABLE formula (
                    '수식명' TEXT,
                    '차트표시' INTEGER,
                    '전략연산' INTEGER,
                    '팩터명' TEXT,
                    '표시형태' TEXT,
                    '색상' TEXT,
                    '크기' REAL,
                    '라인타입' INTEGER,
                    '수식코드' TEXT,
                    PRIMARY KEY ('수식명')
                )
            ''')

        con.commit()
        con.close()

        # --------------------------------------------------------------------------------------------------------------

        con = sqlite3.connect(DB_TRADELIST)
        cur = con.cursor()
        df  = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
        table_list = df['name'].to_list()

        market_list = [
            'stock', 'stock_etf', 'stock_etn', 'stock_usa', 'future', 'future_nt', 'future_os', 'coin', 'coin_future'
        ]
        endname_list = [
            '_chegeollist', '_totaltradelist', '_tradelist', '_jangolist'
        ]

        for market in market_list:
            for endname in endname_list:
                table_name = f'{market}{endname}'
                if table_name not in table_list:
                    if table_name == '_chegeollist':
                        cur.execute(f'''
                            CREATE TABLE {table_name} (
                                'index'	TEXT,
                                '종목명' TEXT,
                                '주문구분' TEXT,
                                '주문수량' REAL,
                                '체결수량' REAL,
                                '미체결수량' REAL,
                                '체결가' REAL,
                                '체결시간' TEXT,
                                '주문가격' REAL,
                                '주문번호' TEXT,
                                PRIMARY KEY ('index')
                            )
                        ''')
                    elif table_name == '_totaltradelist':
                        cur.execute(f'''
                            CREATE TABLE {table_name} (
                                "index" TEXT,
                                "거래횟수" INTEGER,
                                "총매수금액" INTEGER,
                                "총매도금액" INTEGER,
                                "총수익금액" INTEGER,
                                "총손실금액" INTEGER,
                                "수익률" REAL,
                                "수익금합계" INTEGER,
                                PRIMARY KEY ('index')
                            )
                        ''')
                    elif table_name == '_jangolist':
                        if market == 'coin_future':
                            cur.execute(f'''
                                CREATE TABLE {table_name} (
                                    "index" TEXT,
                                    "종목명" TEXT,
                                    "포지션" TEXT,
                                    "매수가" REAL,
                                    "현재가" REAL,
                                    "수익률" REAL,
                                    "평가손익" INTEGER,
                                    "매입금액" INTEGER,
                                    "평가금액" INTEGER,
                                    "보유수량" REAL,
                                    "분할매수횟수" INTEGER,
                                    "분할매도횟수" INTEGER,
                                    "매수시간" TEXT,
                                    "레버리지" INTEGER,
                                    PRIMARY KEY ('index')
                                )
                            ''')
                        elif 'future' in market:
                            cur.execute(f'''
                                CREATE TABLE {table_name} (
                                    "index" TEXT,
                                    "종목명" TEXT,
                                    "포지션" TEXT,
                                    "매수가" REAL,
                                    "현재가" REAL,
                                    "수익률" REAL,
                                    "평가손익" INTEGER,
                                    "매입금액" INTEGER,
                                    "평가금액" INTEGER,
                                    "보유수량" REAL,
                                    "분할매수횟수" INTEGER,
                                    "분할매도횟수" INTEGER,
                                    "매수시간" TEXT,
                                    PRIMARY KEY ('index')
                                )
                            ''')
                        else:
                            cur.execute(f'''
                                CREATE TABLE {table_name} (
                                    "index" TEXT,
                                    "종목명" TEXT,
                                    "매수가" REAL,
                                    "현재가" REAL,
                                    "수익률" REAL,
                                    "평가손익" INTEGER,
                                    "매입금액" INTEGER,
                                    "평가금액" INTEGER,
                                    "보유수량" REAL,
                                    "분할매수횟수" INTEGER,
                                    "분할매도횟수" INTEGER,
                                    "매수시간" TEXT,
                                    PRIMARY KEY ('index')
                                )
                            ''')
                    else:
                        if 'future' not in market:
                            cur.execute(f'''
                                CREATE TABLE {table_name} (
                                    "index" TEXT,
                                    "종목명" TEXT,
                                    "포지션" TEXT,
                                    "매수금액" INTEGER,
                                    "매도금액" INTEGER,
                                    "주문수량" REAL,
                                    "수익률" REAL,
                                    "수익금" INTEGER,
                                    "체결시간" TEXT,
                                    PRIMARY KEY ('index')
                                )
                            ''')
                        else:
                            cur.execute(f'''
                                CREATE TABLE {table_name} (
                                    "index" TEXT,
                                    "종목명" TEXT,
                                    "매수금액" INTEGER,
                                    "매도금액" INTEGER,
                                    "주문수량" REAL,
                                    "수익률" REAL,
                                    "수익금" INTEGER,
                                    "체결시간" TEXT,
                                    PRIMARY KEY ('index')
                                )
                            ''')

        con.commit()
        con.close()

        # --------------------------------------------------------------------------------------------------------------

        file_list  = os.listdir(DB_PATH)
        file_names = ['stock_tick_', 'future_tick_', 'coin_tick_']
        for file_name in file_names:
            file_list_ = [x for x in file_list if file_name in x and '.db' in x and 'back' not in x]
            if file_list_:
                con = sqlite3.connect(f'{DB_PATH}/{file_list_[0]}')
                df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
                table_list = df['name'].to_list()
                if 'moneytop' in table_list:
                    table_list.remove('moneytop')
                if table_list:
                    df = pd.read_sql(f'SELECT * FROM "{table_list[0]}"', con)
                    idx_ask1 = list(df.columns).index('매도호가1')
                    idx_ask2 = list(df.columns).index('매도호가2')
                    if '전일비' in df.columns or '당일매수금액' not in df.columns or idx_ask2 != idx_ask1 + 1:
                        con.close()
                        return False, '일자DB의 칼럼이 일치하지 않습니다.\nupdate_db_20260418.bat 파일을 실행하여 DB를 업데이트하십시오.\n'
                con.close()

            file_list_ = [x for x in file_list if file_name in x and '.db' in x and 'back' in x]
            if file_list_:
                con = sqlite3.connect(f'{DB_PATH}/{file_list_[0]}')
                df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
                table_list = df['name'].to_list()
                if 'moneytop' in table_list:
                    table_list.remove('moneytop')
                for table in code_info_tables:
                    if table in table_list:
                        table_list.remove(table)
                if table_list:
                    df = pd.read_sql(f'SELECT * FROM "{table_list[0]}"', con)
                    if '당일매수금액' not in df.columns:
                        con.close()
                        return False, f'백테DB의 칼럼이 일치하지 않습니다.\n업데이트 된 일자DB로 백테DB를 새로 생성하십시오.'
                con.close()

        return True, None

    except Exception:
        return False, format_exc()
