import os
import sqlite3
import pandas as pd
from static import read_key, write_key

os.makedirs('./_database', exist_ok=True)
os.makedirs('./_log', exist_ok=True)

DB_SETTING   = './_database/setting.db'
DB_TRADELIST = './_database/tradelist.db'
DB_STRATEGY  = './_database/strategy.db'
DB_BACKTEST  = './_database/backtest.db'

try:
    read_key()
    print('시스템 명령 실행 알림 - 암호화키 확인 완료')
except:
    write_key()
    print('시스템 명령 실행 알림 - 암호화키 생성 완료')

con = sqlite3.connect(DB_SETTING)
df  = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
table_list = df['name'].to_list()

if 'main' not in table_list:
    columns = [
        'index', '증권사', '주식리시버', '주식트레이더', '주식데이터저장', '거래소', '코인리시버', '코인트레이더', '코인데이터저장',
        '바이낸스선물고정레버리지', '바이낸스선물고정레버리지값', '바이낸스선물변동레버리지값', '바이낸스선물마진타입', '바이낸스선물포지션',
        '버전업', '리시버공유'
    ]
    data = [0, '키움증권1', 0, 0, 0, '바이낸스선물', 0, 0, 0, 1, 1, '0;5;1^5;10;2^10;20;3^20;30;4^30;100;5', 'ISOLATED', 'false', 1, 0]
    df = pd.DataFrame([data], columns=columns).set_index('index')
    df.to_sql('main', con)

if 'sacc' not in table_list:
    columns = [
        "index", "아이디", "비밀번호", "인증서비밀번호", "계좌비밀번호"
    ]
    data = [
        [1, '', '', '', ''],
        [2, '', '', '', ''],
        [3, '', '', '', ''],
        [4, '', '', '', ''],
        [5, '', '', '', ''],
        [6, '', '', '', ''],
        [7, '', '', '', ''],
        [8, '', '', '', '']
    ]
    df = pd.DataFrame(data, columns=columns).set_index('index')
    df.to_sql('sacc', con)

if 'cacc' not in table_list:
    columns = ["index", "Access_key", "Secret_key"]
    data = [[1, '', ''], [2, '', '']]
    df = pd.DataFrame(data, columns=columns).set_index('index')
    df.to_sql('cacc', con)

if 'telegram' not in table_list:
    columns = ["index", "str_bot", "int_id"]
    data = [[1, '', ''], [2, '', ''], [3, '', ''], [4, '', '']]
    df = pd.DataFrame(data, columns=columns).set_index('index')
    df.to_sql('telegram', con)

if 'stock' not in table_list:
    columns = [
        "index", "주식모의투자", "주식알림소리", "주식매수전략", "주식매도전략", "주식타임프레임", "주식평균값계산틱수", "주식최대매수종목수",
        "주식전략종료시간", "주식잔고청산", "주식프로세스종료", "주식컴퓨터종료", "주식투자금고정", "주식투자금", "주식손실중지",
        "주식손실중지수익률", "주식수익중지", "주식수익중지수익률", "주식경과틱수설정"
    ]
    data = [0, 1, 1, '', '', 1, 30, 10, 93000, 1, 1, 0, 1, 20.0, 0, 2.0, 0, 2.0, '']
    df = pd.DataFrame([data], columns=columns).set_index('index')
    df.to_sql('stock', con)

if 'coin' not in table_list:
    columns = [
        "index", "코인모의투자", "코인알림소리", "코인매수전략", "코인매도전략", "코인타임프레임", "코인평균값계산틱수", "코인최대매수종목수",
        "코인전략종료시간", "코인잔고청산", "코인프로세스종료", "코인컴퓨터종료", "코인투자금고정", "코인투자금", "코인손실중지",
        "코인손실중지수익률", "코인수익중지", "코인수익중지수익률", "코인경과틱수설정"
    ]
    data = [0, 1, 1, '', '', 0, 30, 10, 235000, 1, 0, 0, 1, 1000.0, 0, 2.0, 0, 2.0, '']
    df = pd.DataFrame([data], columns=columns).set_index('index')
    df.to_sql('coin', con)

if 'back' not in table_list:
    columns = [
        "index", "블랙리스트추가", "백테주문관리적용", "백테매수시간기준", "백테일괄로딩", "그래프저장하지않기", "그래프띄우지않기",
        "디비자동관리", "교차검증가중치", "백테스케쥴실행", "백테스케쥴요일", "백테스케쥴시간", "백테스케쥴구분", "백테스케쥴명",
        "백테날짜고정", "백테날짜", "최적화기준값제한", "백테엔진분류방법", "옵튜나샘플러", "옵튜나고정변수", "옵튜나실행횟수",
        "옵튜나자동스탭", "범위자동관리", "보조지표설정", "최적화로그기록안함"
    ]
    data = [0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 4, 160000, '', '', 1, '20220323',
            '0.0;1000.0;0;100.0;0.0;100.0;-10.0;10.0;0.0;100.0;-10000.0;10000.0;0.0;10.0',
            '종목코드별 분류', 'TPESampler', '', 0, 0, 0,
            '3;10;14;12;26;0;14;14;5;2;2;0;14;14;12;26;9;14;10;12;26;0;10;14;0.02;0.2;5;3;0;3;0;5;3;0;14', 1]
    df = pd.DataFrame([data], columns=columns).set_index('index')
    df.to_sql('back', con)

if 'etc' not in table_list:
    columns = ["index", "테마", "저해상도", "휴무프로세스종료", "휴무컴퓨터종료", "창위치기억", "창위치", "스톰라이브", "프로그램종료", "팩터선택"]
    data = [0, '다크블루', 0, 1, 0, 1, '', 1, 0, '1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1']
    df = pd.DataFrame([data], columns=columns).set_index('index')
    df.to_sql('etc', con)

if 'stockbuyorder' not in table_list:
    columns = [
        'index', '주식매수주문구분', '주식매수분할횟수', '주식매수분할방법', '주식매수분할시그널', '주식매수분할하방', '주식매수분할상방',
        '주식매수분할하방수익률', '주식매수분할상방수익률', '주식매수분할고정수익률', '주식매수지정가기준가격', '주식매수지정가호가번호',
        '주식매수시장가잔량범위', '주식매수취소관심이탈', '주식매수취소매도시그널', '주식매수취소시간', '주식매수취소시간초', '주식매수금지블랙리스트',
        '주식매수금지라운드피겨', '주식매수금지라운드호가', '주식매수금지손절횟수', '주식매수금지손절횟수값', '주식매수금지거래횟수',
        '주식매수금지거래횟수값', '주식매수금지시간', '주식매수금지시작시간', '주식매수금지종료시간', '주식매수금지간격', '주식매수금지간격초',
        '주식매수금지손절간격', '주식매수금지손절간격초', '주식매수정정횟수', '주식매수정정호가차이', '주식매수정정호가', '주식비중조절'
    ]
    data = [0, '시장가', 1, 2, 1, 0, 1, 0.5, 0.5, 1, '매수1호가', 0, 3, 0, 0, 0, 30, 0, 0, 5, 0, 2, 0, 2, 0, 120000,
            130000, 0, 5, 0, 300, 0, 5, 2, '0;0;0;0;0;1;1;1;1;1']
    df = pd.DataFrame([data], columns=columns).set_index('index')
    df.to_sql('stockbuyorder', con)

if 'stocksellorder' not in table_list:
    columns = [
        'index', '주식매도주문구분', '주식매도분할횟수', '주식매도분할방법', '주식매도분할시그널', '주식매도분할하방', '주식매도분할상방',
        '주식매도분할하방수익률', '주식매도분할상방수익률', '주식매도지정가기준가격', '주식매도지정가호가번호', '주식매도시장가잔량범위',
        '주식매도취소관심진입', '주식매도취소매수시그널', '주식매도취소시간', '주식매도취소시간초', '주식매도손절수익률청산', '주식매도손절수익률',
        '주식매도손절수익금청산', '주식매도손절수익금', '주식매도금지매수횟수', '주식매도금지매수횟수값', '주식매도금지라운드피겨',
        '주식매도금지라운드호가', '주식매도금지시간', '주식매도금지시작시간', '주식매도금지종료시간', '주식매도금지간격', '주식매도금지간격초',
        '주식매도정정횟수', '주식매도정정호가차이', '주식매도정정호가'
    ]
    data = [0, '시장가', 1, 1, 1, 0, 1, 0.5, 2.0, '매도1호가', 0, 5, 0, 0, 0, 30, 0, 5, 0, 100, 0, 2, 0, 5, 0, 120000, 130000, 0, 300, 0, 5, 2]
    df = pd.DataFrame([data], columns=columns).set_index('index')
    df.to_sql('stocksellorder', con)

if 'coinbuyorder' not in table_list:
    columns = [
        'index', '코인매수주문구분', '코인매수분할횟수', '코인매수분할방법', '코인매수분할시그널', '코인매수분할하방', '코인매수분할상방',
        '코인매수분할하방수익률', '코인매수분할상방수익률', '코인매수분할고정수익률', '코인매수지정가기준가격', '코인매수지정가호가번호',
        '코인매수시장가잔량범위', '코인매수취소관심이탈', '코인매수취소매도시그널', '코인매수취소시간', '코인매수취소시간초', '코인매수금지블랙리스트',
        '코인매수금지200원이하', '코인매수금지손절횟수', '코인매수금지손절횟수값', '코인매수금지거래횟수', '코인매수금지거래횟수값', '코인매수금지시간',
        '코인매수금지시작시간', '코인매수금지종료시간', '코인매수금지간격', '코인매수금지간격초', '코인매수금지손절간격', '코인매수금지손절간격초',
        '코인매수정정횟수', '코인매수정정호가차이', '코인매수정정호가', '코인비중조절'
    ]
    data = [0, '시장가', 1, 1, 1, 0, 1, 0.5, 0.5, 1, '매수1호가', 0, 3, 0, 0, 0, 30, 0, 0, 0, 2, 0, 2, 0, 150000, 210000,
            0, 5, 0, 300, 0, 5, 2, '0;0;0;0;0;1;1;1;1;1']
    df = pd.DataFrame([data], columns=columns).set_index('index')
    df.to_sql('coinbuyorder', con)

if 'coinsellorder' not in table_list:
    columns = [
        'index', '코인매도주문구분', '코인매도분할횟수', '코인매도분할방법', '코인매도분할시그널', '코인매도분할하방', '코인매도분할상방',
        '코인매도분할하방수익률', '코인매도분할상방수익률', '코인매도지정가기준가격', '코인매도지정가호가번호', '코인매도시장가잔량범위',
        '코인매도취소관심진입', '코인매도취소매수시그널', '코인매도취소시간', '코인매도취소시간초', '코인매도손절수익률청산', '코인매도손절수익률',
        '코인매도손절수익금청산', '코인매도손절수익금', '코인매도금지매수횟수', '코인매도금지매수횟수값', '코인매도금지시간', '코인매도금지시작시간',
        '코인매도금지종료시간', '코인매도금지간격', '코인매도금지간격초', '코인매도정정횟수', '코인매도정정호가차이', '코인매도정정호가'
    ]
    data = [0, '시장가', 1, 1, 1, 0, 1, 0.5, 2.0, '매도1호가', 0, 5, 0, 0, 0, 30, 0, 5, 0, 100, 0, 2, 0, 150000, 210000, 0, 300, 0, 5, 2]
    df = pd.DataFrame([data], columns=columns).set_index('index')
    df.to_sql('coinsellorder', con)

if 'codename' not in table_list:
    columns = ["index", "종목명"]
    data = ['005930', '삼성전자']
    df = pd.DataFrame([data], columns=columns).set_index('index')
    df.to_sql('codename', con)

con.commit()
con.close()

con = sqlite3.connect(DB_STRATEGY)
cur = con.cursor()
df  = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
table_list = df['name'].to_list()

if 'coinbuy' not in table_list:
    cur.execute('CREATE TABLE "coinbuy" ( "index" TEXT, "전략코드" TEXT )')
    cur.execute('CREATE INDEX "ix_coinbuy_index" ON "coinbuy"("index")')

if 'coinsell' not in table_list:
    cur.execute('CREATE TABLE "coinsell" ( "index" TEXT, "전략코드" TEXT )')
    cur.execute('CREATE INDEX "ix_coinsell_index"ON "coinsell" ("index")')

if 'coinoptibuy' not in table_list:
    query = 'CREATE TABLE "coinoptibuy" ( "index" TEXT, "전략코드" TEXT, "변수값" TEXT )'
    cur.execute(query)
    cur.execute('CREATE INDEX "ix_coinoptibuy_index"ON "coinoptibuy" ("index")')

if 'coinoptisell' not in table_list:
    cur.execute('CREATE TABLE "coinoptisell" ( "index" TEXT, "전략코드" TEXT )')
    cur.execute('CREATE INDEX "ix_coinoptisell_index"ON "coinoptisell" ("index")')

if 'coinoptivars' not in table_list:
    cur.execute('CREATE TABLE "coinoptivars" ( "index" TEXT, "전략코드" TEXT )')
    cur.execute('CREATE INDEX "ix_coinoptivars_index"ON "coinoptivars" ("index")')

if 'coinvars' not in table_list:
    cur.execute('CREATE TABLE "coinvars" ( "index" TEXT, "전략코드" TEXT )')
    cur.execute('CREATE INDEX "ix_coinvars_index"ON "coinvars" ("index")')

if 'coinbuyconds' not in table_list:
    cur.execute('CREATE TABLE "coinbuyconds" ( "index" TEXT, "전략코드" TEXT )')
    cur.execute('CREATE INDEX "ix_coinbuyconds_index" ON "coinbuyconds"("index")')

if 'coinsellconds' not in table_list:
    cur.execute('CREATE TABLE "coinsellconds" ( "index" TEXT, "전략코드" TEXT )')
    cur.execute('CREATE INDEX "ix_coinsellconds_index"ON "coinsellconds" ("index")')

if 'stockbuy' not in table_list:
    cur.execute('CREATE TABLE "stockbuy" ( "index" TEXT, "전략코드" TEXT )')
    cur.execute('CREATE INDEX "ix_stockbuy_index"ON "stockbuy" ("index")')

if 'stocksell' not in table_list:
    cur.execute('CREATE TABLE "stocksell" ( "index" TEXT, "전략코드" TEXT )')
    cur.execute('CREATE INDEX "ix_stocksell_index"ON "stocksell" ("index")')

if 'stockoptibuy' not in table_list:
    query = 'CREATE TABLE "stockoptibuy" ( "index" TEXT, "전략코드" TEXT, "변수값" TEXT )'
    cur.execute(query)
    cur.execute('CREATE INDEX "ix_stockoptibuy_index"ON "stockoptibuy" ("index")')

if 'stockoptisell' not in table_list:
    cur.execute('CREATE TABLE "stockoptisell" ( "index" TEXT, "전략코드" TEXT )')
    cur.execute('CREATE INDEX "ix_stockoptisell_index"ON "stockoptisell" ("index")')

if 'stockoptivars' not in table_list:
    cur.execute('CREATE TABLE "stockoptivars" ( "index" TEXT, "전략코드" TEXT )')
    cur.execute('CREATE INDEX "ix_stockoptivars_index"ON "stockoptivars" ("index")')

if 'stockvars' not in table_list:
    cur.execute('CREATE TABLE "stockvars" ( "index" TEXT, "전략코드" TEXT )')
    cur.execute('CREATE INDEX "ix_stockvars_index"ON "stockvars" ("index")')

if 'stockbuyconds' not in table_list:
    cur.execute('CREATE TABLE "stockbuyconds" ( "index" TEXT, "전략코드" TEXT )')
    cur.execute('CREATE INDEX "ix_stockbuyconds_index" ON "stockbuyconds"("index")')

if 'stocksellconds' not in table_list:
    cur.execute('CREATE TABLE "stocksellconds" ( "index" TEXT, "전략코드" TEXT )')
    cur.execute('CREATE INDEX "ix_stocksellconds_index"ON "stocksellconds" ("index")')

if 'schedule' not in table_list:
    cur.execute('CREATE TABLE "schedule" ( "index" TEXT, "스케쥴" TEXT )')
    cur.execute('CREATE INDEX "ix_schedule_index"ON "schedule" ("index")')

con.commit()
con.close()

con = sqlite3.connect(DB_TRADELIST)
cur = con.cursor()
df  = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
table_list = df['name'].to_list()

if 'c_chegeollist' not in table_list:
    query = 'CREATE TABLE "c_chegeollist" ( "index"	TEXT, "종목명" TEXT, "주문구분" TEXT, "주문수량" REAL, ' \
            '"체결수량" REAL, "미체결수량" REAL, "체결가" REAL, "체결시간" TEXT, "주문가격" REAL, "주문번호" TEXT )'
    cur.execute(query)
    cur.execute('CREATE INDEX "ix_c_chegeollist_index" ON "c_chegeollist" ( "index" )')

if 'c_jangolist' not in table_list:
    query = 'CREATE TABLE "c_jangolist" ( "index" TEXT, "종목명" TEXT, "매입가" REAL, "현재가" REAL, "수익률" REAL, ' \
            '"평가손익" INTEGER, "매입금액" INTEGER, "평가금액" INTEGER, "보유수량" REAL, "분할매수횟수" INTEGER, "분할매도횟수" INTEGER, "매수시간" TEXT )'
    cur.execute(query)
    cur.execute('CREATE INDEX "ix_c_jangolist_index"ON "c_jangolist" ("index")')

if 'c_jangolist_future' not in table_list:
    query = 'CREATE TABLE "c_jangolist_future" ( "index" TEXT, "종목명" TEXT, "포지션" TEXT, "매입가" REAL, "현재가" REAL, "수익률" REAL, ' \
            '"평가손익" INTEGER, "매입금액" INTEGER, "평가금액" INTEGER, "보유수량" REAL, "레버리지" INTEGER, "분할매수횟수" INTEGER, "분할매도횟수" INTEGER, "매수시간" TEXT )'
    cur.execute(query)
    cur.execute('CREATE INDEX "ix_c_jangolist_future_index"ON "c_jangolist_future" ("index")')

if 'c_totaltradelist' not in table_list:
    query = 'CREATE TABLE "c_totaltradelist" ( "index" TEXT, "총매수금액" INTEGER, "총매도금액" INTEGER, "총수익금액" INTEGER, ' \
            '"총손실금액" INTEGER, "수익률" REAL, "수익금합계" INTEGER )'
    cur.execute(query)
    cur.execute('CREATE INDEX "ix_c_totaltradelist_index" ON "c_totaltradelist" ( "index" )')

if 'c_tradelist' not in table_list:
    query = 'CREATE TABLE "c_tradelist" ( "index" TEXT, "종목명" TEXT, "매수금액" INTEGER, "매도금액" INTEGER, ' \
            '"주문수량" REAL, "수익률" REAL, "수익금" INTEGER, "체결시간" TEXT )'
    cur.execute(query)
    cur.execute('CREATE INDEX "ix_c_tradelist_index" ON "c_tradelist" ( "index" )')

if 'c_tradelist_future' not in table_list:
    query = 'CREATE TABLE "c_tradelist_future" ( "index" TEXT, "종목명" TEXT, "포지션" TEXT, "매수금액" INTEGER, "매도금액" INTEGER, ' \
            '"주문수량" REAL, "수익률" REAL, "수익금" INTEGER, "체결시간" TEXT )'
    cur.execute(query)
    cur.execute('CREATE INDEX "ix_c_tradelist_future_index" ON "c_tradelist_future" ( "index" )')

if 's_chegeollist' not in table_list:
    query = 'CREATE TABLE "s_chegeollist" ( "index" TEXT, "종목명" TEXT, "주문구분" TEXT, "주문수량" INTEGER, ' \
            '"체결수량" INTEGER, "미체결수량" INTEGER, "체결가" INTEGER, "체결시간" TEXT, "주문가격" INTEGER, "주문번호" TEXT )'
    cur.execute(query)
    cur.execute('CREATE INDEX "ix_s_chegeollist_index" ON "s_chegeollist" ( "index" )')

if 's_jangolist' not in table_list:
    query = 'CREATE TABLE "s_jangolist" ( "index" TEXT, "종목명" TEXT, "매입가" INTEGER, "현재가" INTEGER, "수익률" REAL, ' \
            '"평가손익" INTEGER, "매입금액" INTEGER, "평가금액" INTEGER, "보유수량" INTEGER, "분할매수횟수" INTEGER, "분할매도횟수" INTEGER, "매수시간" TEXT )'
    cur.execute(query)
    cur.execute('CREATE INDEX "ix_s_jangolist_index"ON "s_jangolist" ("index")')

"""
if 's_jangolist_future' not in table_list:
    query = 'CREATE TABLE "s_jangolist_future" ( "index" TEXT, "종목명" TEXT, "포지션" TEXT, "매입가" INTEGER, "현재가" INTEGER, "수익률" REAL, ' \
            '"평가손익" INTEGER, "매입금액" INTEGER, "평가금액" INTEGER, "보유수량" INTEGER, "레버리지" INTEGER, "분할매수횟수" INTEGER, "분할매도횟수" INTEGER, "매수시간" TEXT )'
    cur.execute(query)
    cur.execute('CREATE INDEX "ix_s_jangolist_future_index"ON "c_jangolist_future" ("index")')
"""

if 's_totaltradelist' not in table_list:
    query = 'CREATE TABLE "s_totaltradelist" ( "index" TEXT, "총매수금액" INTEGER, "총매도금액" INTEGER, ' \
            '"총수익금액" INTEGER, "총손실금액" INTEGER, "수익률" REAL, "수익금합계" INTEGER)'
    cur.execute(query)
    cur.execute('CREATE INDEX "ix_s_totaltradelist_index" ON "s_totaltradelist" ( "index" )')

if 's_tradelist' not in table_list:
    query = 'CREATE TABLE "s_tradelist" ( "index" TEXT, "종목명" TEXT, "매수금액" INTEGER, "매도금액" INTEGER, ' \
            '"주문수량" INTEGER, "수익률" REAL, "수익금" INTEGER, "체결시간" TEXT )'
    cur.execute(query)
    cur.execute('CREATE INDEX "ix_s_tradelist_index" ON "s_tradelist" ( "index" )')

con.commit()
con.close()

print('시스템 명령 실행 알림 - 데이터베이스 확인 완료')
