import os
import sys
import sqlite3
import pandas as pd
from traceback import print_exc
from cryptography import fernet
from utility.static import read_key, de_text as _strict_de_text, get_logger
from utility.worktree_policy import apply_serial_key_to_dict_set, uses_serial_key

logger_             = get_logger('Setting')
EN_KEY              = read_key()
ALLOW_MINIMAL_SETTING = os.environ.get('STOM_ALLOW_MINIMAL_SETTING', '1' if sys.platform != 'win32' else '0') == '1'
OPENAPI_PATH        = 'C:/OpenAPI'
ICON_PATH           = './ui/icon'
LOGIN_PATH          = './trade/stock_korea/login_kiwoom'
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


_decrypt_warning_emitted = False


def safe_de_text(text):
    global _decrypt_warning_emitted
    if not text:
        return None
    try:
        return _strict_de_text(EN_KEY, text)
    except fernet.InvalidToken:
        if not ALLOW_MINIMAL_SETTING:
            raise
        if not _decrypt_warning_emitted:
            logger_.warning('암호화 필드 복호화에 실패하여 최소 설정 모드로 계속 진행합니다.')
            _decrypt_warning_emitted = True
        return None


def safe_de_int(text):
    value = safe_de_text(text)
    if value in (None, ''):
        return None
    try:
        return int(value)
    except ValueError:
        return None


with open('./utility/blacklist_stock.txt') as f:
    stockreadlines = f.readlines()
with open('./utility/blacklist_future.txt') as f:
    futurereadlines = f.readlines()
with open('./utility/blacklist_coin.txt') as f:
    coinreadlines = f.readlines()

blacklist_stock  = []
blacklist_future = []
blacklist_coin   = []
for readline in stockreadlines:
    blacklist_stock.append(readline.strip())
for readline in futurereadlines:
    blacklist_future.append(readline.strip())
for readline in coinreadlines:
    blacklist_coin.append(readline.strip())


def database_load():
    con  = sqlite3.connect(DB_SETTING)
    df1  = pd.read_sql('SELECT * FROM main', con).set_index('index')
    df2  = pd.read_sql('SELECT * FROM stock', con).set_index('index')
    df3  = pd.read_sql('SELECT * FROM coin', con).set_index('index')
    df4  = pd.read_sql('SELECT * FROM sacc', con).set_index('index')
    df5  = pd.read_sql('SELECT * FROM cacc', con).set_index('index')
    df6  = pd.read_sql('SELECT * FROM telegram', con).set_index('index')
    df7  = pd.read_sql('SELECT * FROM stockbuyorder', con).set_index('index')
    df8  = pd.read_sql('SELECT * FROM stocksellorder', con).set_index('index')
    df9  = pd.read_sql('SELECT * FROM coinbuyorder', con).set_index('index')
    df10 = pd.read_sql('SELECT * FROM coinsellorder', con).set_index('index')
    df11 = pd.read_sql('SELECT * FROM etc', con).set_index('index')
    df12 = pd.read_sql('SELECT * FROM back', con).set_index('index')
    con.close()
    return df1, df2, df3, df4, df5, df6, df7, df8, df9, df10, df11, df12


df_m, df_s, df_c, df_sa, df_ca, df_t, df_sb, df_ss, df_cb, df_cs, df_e, df_b = database_load()

binance_leverage_ = []
for text_ in df_m['바이낸스선물변동레버리지값'][0].split('^'):
    lvrg_list_ = text_.split(';')
    lvrg_list_ = [float(x) for x in lvrg_list_]
    binance_leverage_.append(lvrg_list_)

df_sa_not_empty = True if len(df_sa) > 0 else False
df_ca_not_empty = True if len(df_ca) > 0 else False
df_t_not_empty  = True if len(df_t) > 0 else False

try:
    DICT_SET = {
        '키':            EN_KEY,
        '증권사':         df_m['증권사'][0],
        '주식에이전트':      df_m['주식에이전트'][0],
        '주식트레이더':    df_m['주식트레이더'][0],
        '주식데이터저장':  df_m['주식데이터저장'][0],
        '거래소':         df_m['거래소'][0],
        '코인리시버':      df_m['코인리시버'][0],
        '코인트레이더':    df_m['코인트레이더'][0],
        '코인데이터저장':  df_m['코인데이터저장'][0],

        '바이낸스선물고정레버리지':   df_m['바이낸스선물고정레버리지'][0],
        '바이낸스선물고정레버리지값': df_m['바이낸스선물고정레버리지값'][0],
        '바이낸스선물변동레버리지값': binance_leverage_,
        '바이낸스선물마진타입':     df_m['바이낸스선물마진타입'][0],
        '바이낸스선물포지션':       df_m['바이낸스선물포지션'][0],

        '아이디1':        safe_de_text(df_sa['아이디'][1])         if df_sa_not_empty and df_sa['아이디'][1] else None,
        '비밀번호1':      safe_de_text(df_sa['비밀번호'][1])       if df_sa_not_empty and df_sa['비밀번호'][1] else None,
        '인증서비밀번호1': safe_de_text(df_sa['인증서비밀번호'][1])   if df_sa_not_empty and df_sa['인증서비밀번호'][1] else None,
        '계좌비밀번호1':   safe_de_text(df_sa['계좌비밀번호'][1])    if df_sa_not_empty and df_sa['계좌비밀번호'][1] else None,
        '아이디2':        safe_de_text(df_sa['아이디'][2])         if df_sa_not_empty and df_sa['아이디'][2] else None,
        '비밀번호2':      safe_de_text(df_sa['비밀번호'][2])        if df_sa_not_empty and df_sa['비밀번호'][2] else None,
        '인증서비밀번호2': safe_de_text(df_sa['인증서비밀번호'][2])   if df_sa_not_empty and df_sa['인증서비밀번호'][2] else None,
        '계좌비밀번호2':   safe_de_text(df_sa['계좌비밀번호'][2])    if df_sa_not_empty and df_sa['계좌비밀번호'][2] else None,
        '아이디3':        safe_de_text(df_sa['아이디'][3])         if df_sa_not_empty and df_sa['아이디'][3] else None,
        '비밀번호3':      safe_de_text(df_sa['비밀번호'][3])        if df_sa_not_empty and df_sa['비밀번호'][3] else None,
        '인증서비밀번호3': safe_de_text(df_sa['인증서비밀번호'][3])   if df_sa_not_empty and df_sa['인증서비밀번호'][3] else None,
        '계좌비밀번호3':   safe_de_text(df_sa['계좌비밀번호'][3])    if df_sa_not_empty and df_sa['계좌비밀번호'][3] else None,
        '아이디4':        safe_de_text(df_sa['아이디'][4])         if df_sa_not_empty and df_sa['아이디'][4] else None,
        '비밀번호4':      safe_de_text(df_sa['비밀번호'][4])        if df_sa_not_empty and df_sa['비밀번호'][4] else None,
        '인증서비밀번호4': safe_de_text(df_sa['인증서비밀번호'][4])   if df_sa_not_empty and df_sa['인증서비밀번호'][4] else None,
        '계좌비밀번호4':   safe_de_text(df_sa['계좌비밀번호'][4])    if df_sa_not_empty and df_sa['계좌비밀번호'][4] else None,
        '아이디5':        safe_de_text(df_sa['아이디'][5])         if df_sa_not_empty and df_sa['아이디'][5] else None,
        '비밀번호5':      safe_de_text(df_sa['비밀번호'][5])       if df_sa_not_empty and df_sa['비밀번호'][5] else None,
        '인증서비밀번호5': safe_de_text(df_sa['인증서비밀번호'][5])   if df_sa_not_empty and df_sa['인증서비밀번호'][5] else None,
        '계좌비밀번호5':   safe_de_text(df_sa['계좌비밀번호'][5])    if df_sa_not_empty and df_sa['계좌비밀번호'][5] else None,
        '아이디6':        safe_de_text(df_sa['아이디'][6])         if df_sa_not_empty and df_sa['아이디'][6] else None,
        '비밀번호6':      safe_de_text(df_sa['비밀번호'][6])        if df_sa_not_empty and df_sa['비밀번호'][6] else None,
        '인증서비밀번호6': safe_de_text(df_sa['인증서비밀번호'][6])   if df_sa_not_empty and df_sa['인증서비밀번호'][6] else None,
        '계좌비밀번호6':   safe_de_text(df_sa['계좌비밀번호'][6])    if df_sa_not_empty and df_sa['계좌비밀번호'][6] else None,
        '아이디7':        safe_de_text(df_sa['아이디'][7])         if df_sa_not_empty and df_sa['아이디'][7] else None,
        '비밀번호7':      safe_de_text(df_sa['비밀번호'][7])        if df_sa_not_empty and df_sa['비밀번호'][7] else None,
        '인증서비밀번호7': safe_de_text(df_sa['인증서비밀번호'][7])   if df_sa_not_empty and df_sa['인증서비밀번호'][7] else None,
        '계좌비밀번호7':   safe_de_text(df_sa['계좌비밀번호'][7])    if df_sa_not_empty and df_sa['계좌비밀번호'][7] else None,
        '아이디8':        safe_de_text(df_sa['아이디'][8])         if df_sa_not_empty and df_sa['아이디'][8] else None,
        '비밀번호8':      safe_de_text(df_sa['비밀번호'][8])        if df_sa_not_empty and df_sa['비밀번호'][8] else None,
        '인증서비밀번호8': safe_de_text(df_sa['인증서비밀번호'][8])   if df_sa_not_empty and df_sa['인증서비밀번호'][8] else None,
        '계좌비밀번호8':   safe_de_text(df_sa['계좌비밀번호'][8])    if df_sa_not_empty and df_sa['계좌비밀번호'][8] else None,

        'Access_key1':   safe_de_text(df_ca['Access_key'][1])    if df_ca_not_empty and df_ca['Access_key'][1] else None,
        'Secret_key1':   safe_de_text(df_ca['Secret_key'][1])    if df_ca_not_empty and df_ca['Secret_key'][1] else None,
        'Access_key2':   safe_de_text(df_ca['Access_key'][2])    if df_ca_not_empty and df_ca['Access_key'][2] else None,
        'Secret_key2':   safe_de_text(df_ca['Secret_key'][2])    if df_ca_not_empty and df_ca['Secret_key'][2] else None,

        '텔레그램봇토큰1':      safe_de_text(df_t['str_bot'][1])  if df_t_not_empty and df_t['str_bot'][1] else None,
        '텔레그램사용자아이디1': safe_de_int(df_t['int_id'][1])   if df_t_not_empty and df_t['int_id'][1]  else None,
        '텔레그램봇토큰2':      safe_de_text(df_t['str_bot'][2])  if df_t_not_empty and df_t['str_bot'][2] else None,
        '텔레그램사용자아이디2': safe_de_int(df_t['int_id'][2])   if df_t_not_empty and df_t['int_id'][2]  else None,
        '텔레그램봇토큰3':      safe_de_text(df_t['str_bot'][3])  if df_t_not_empty and df_t['str_bot'][3] else None,
        '텔레그램사용자아이디3': safe_de_int(df_t['int_id'][3])   if df_t_not_empty and df_t['int_id'][3]  else None,
        '텔레그램봇토큰4':      safe_de_text(df_t['str_bot'][4])  if df_t_not_empty and df_t['str_bot'][4] else None,
        '텔레그램사용자아이디4': safe_de_int(df_t['int_id'][4])   if df_t_not_empty and df_t['int_id'][4]  else None,
        '텔레그램봇토큰5':      safe_de_text(df_t['str_bot'][5])  if df_t_not_empty and df_t['str_bot'][5] else None,
        '텔레그램사용자아이디5': safe_de_int(df_t['int_id'][5])   if df_t_not_empty and df_t['int_id'][5]  else None,
        '텔레그램봇토큰6':      safe_de_text(df_t['str_bot'][6])  if df_t_not_empty and df_t['str_bot'][6] else None,
        '텔레그램사용자아이디6': safe_de_int(df_t['int_id'][6])   if df_t_not_empty and df_t['int_id'][6]  else None,
        '텔레그램봇토큰7':      safe_de_text(df_t['str_bot'][7])  if df_t_not_empty and df_t['str_bot'][7] else None,
        '텔레그램사용자아이디7': safe_de_int(df_t['int_id'][7])   if df_t_not_empty and df_t['int_id'][7]  else None,
        '텔레그램봇토큰8':      safe_de_text(df_t['str_bot'][8])  if df_t_not_empty and df_t['str_bot'][8] else None,
        '텔레그램사용자아이디8': safe_de_int(df_t['int_id'][8])   if df_t_not_empty and df_t['int_id'][8]  else None,

        '주식블랙리스트': blacklist_stock,
        '해선블랙리스트': blacklist_future,
        '코인블랙리스트': blacklist_coin,

        '주식모의투자':         df_s['주식모의투자'][0],
        '주식알림소리':         df_s['주식알림소리'][0],
        '주식매수전략':         df_s['주식매수전략'][0],
        '주식매도전략':         df_s['주식매도전략'][0],
        '주식타임프레임':       df_s['주식타임프레임'][0],
        '주식평균값계산틱수':  df_s['주식평균값계산틱수'][0],
        '주식최대매수종목수':    df_s['주식최대매수종목수'][0],
        '주식전략종료시간':      df_s['주식전략종료시간'][0],
        '주식잔고청산':         df_s['주식잔고청산'][0],
        '주식프로세스종료':      df_s['주식프로세스종료'][0],
        '주식컴퓨터종료':       df_s['주식컴퓨터종료'][0],
        '주식투자금고정':       df_s['주식투자금고정'][0],
        '주식투자금':          df_s['주식투자금'][0],
        '주식손실중지':         df_s['주식손실중지'][0],
        '주식손실중지수익률':    df_s['주식손실중지수익률'][0],
        '주식수익중지':         df_s['주식수익중지'][0],
        '주식수익중지수익률':    df_s['주식수익중지수익률'][0],
        '주식경과틱수설정':      df_s['주식경과틱수설정'][0],

        '코인모의투자':         df_c['코인모의투자'][0],
        '코인알림소리':         df_c['코인알림소리'][0],
        '코인매수전략':         df_c['코인매수전략'][0],
        '코인매도전략':         df_c['코인매도전략'][0],
        '코인타임프레임':       df_c['코인타임프레임'][0],
        '코인평균값계산틱수':   df_c['코인평균값계산틱수'][0],
        '코인최대매수종목수':    df_c['코인최대매수종목수'][0],
        '코인전략종료시간':      df_c['코인전략종료시간'][0],
        '코인잔고청산':         df_c['코인잔고청산'][0],
        '코인프로세스종료':      df_c['코인프로세스종료'][0],
        '코인컴퓨터종료':       df_c['코인컴퓨터종료'][0],
        '코인투자금고정':       df_c['코인투자금고정'][0],
        '코인투자금':           df_c['코인투자금'][0],
        '코인손실중지':         df_c['코인손실중지'][0],
        '코인손실중지수익률':    df_c['코인손실중지수익률'][0],
        '코인수익중지':         df_c['코인수익중지'][0],
        '코인수익중지수익률':    df_c['코인수익중지수익률'][0],
        '코인경과틱수설정':      df_c['코인경과틱수설정'][0],

        '블랙리스트추가':        df_b['블랙리스트추가'][0],
        '백테주문관리적용':      df_b['백테주문관리적용'][0],
        '백테매수시간기준':      df_b['백테매수시간기준'][0],
        '백테일괄로딩':         df_b['백테일괄로딩'][0],
        '그래프저장하지않기':    df_b['그래프저장하지않기'][0],
        '그래프띄우지않기':      df_b['그래프띄우지않기'][0],
        '디비자동관리':         df_b['디비자동관리'][0],
        '교차검증가중치':       df_b['교차검증가중치'][0],
        '백테스케쥴실행':       df_b['백테스케쥴실행'][0],
        '백테스케쥴요일':       df_b['백테스케쥴요일'][0],
        '백테스케쥴시간':       df_b['백테스케쥴시간'][0],
        '백테스케쥴구분':       df_b['백테스케쥴구분'][0],
        '백테스케쥴명':         df_b['백테스케쥴명'][0],
        '백테날짜고정':         df_b['백테날짜고정'][0],
        '백테날짜':            df_b['백테날짜'][0],
        '범위자동관리':         df_b['범위자동관리'][0],
        '보조지표설정':         [int(x) if '.' not in x else float(x) for x in df_b['보조지표설정'][0].split(';')],
        '최적화기준값제한':      df_b['최적화기준값제한'][0],
        '백테엔진분류방법':      df_b['백테엔진분류방법'][0],
        '옵튜나샘플러':         df_b['옵튜나샘플러'][0],
        '옵튜나고정변수':        df_b['옵튜나고정변수'][0],
        '옵튜나실행횟수':        df_b['옵튜나실행횟수'][0],
        '옵튜나자동스탭':        df_b['옵튜나자동스탭'][0],
        '최적화로그기록안함':    df_b['최적화로그기록안함'][0],

        '저해상도':            df_e['저해상도'][0],
        '휴무프로세스종료':      df_e['휴무프로세스종료'][0],
        '휴무컴퓨터종료':       df_e['휴무컴퓨터종료'][0],
        '창위치기억':          df_e['창위치기억'][0],
        '창위치':             [int(x) for x in df_e['창위치'][0].split(';')] if df_e['창위치'][0] else None,
        '스톰라이브':          df_e['스톰라이브'][0],
        '프로그램종료':        df_e['프로그램종료'][0],
        '테마':               df_e['테마'][0],
        '팩터선택':            df_e['팩터선택'][0],

        '주식매수주문구분':      df_sb['주식매수주문구분'][0],
        '주식매수분할횟수':      df_sb['주식매수분할횟수'][0],
        '주식매수분할방법':      df_sb['주식매수분할방법'][0],
        '주식매수분할시그널':    df_sb['주식매수분할시그널'][0],
        '주식매수분할하방':      df_sb['주식매수분할하방'][0],
        '주식매수분할상방':      df_sb['주식매수분할상방'][0],
        '주식매수분할하방수익률': df_sb['주식매수분할하방수익률'][0],
        '주식매수분할상방수익률': df_sb['주식매수분할상방수익률'][0],
        '주식매수분할고정수익률': df_sb['주식매수분할고정수익률'][0],
        '주식매수지정가기준가격': df_sb['주식매수지정가기준가격'][0],
        '주식매수지정가호가번호': df_sb['주식매수지정가호가번호'][0],
        '주식매수시장가잔량범위': df_sb['주식매수시장가잔량범위'][0],
        '주식매수취소관심이탈':   df_sb['주식매수취소관심이탈'][0],
        '주식매수취소매도시그널': df_sb['주식매수취소매도시그널'][0],
        '주식매수취소시간':      df_sb['주식매수취소시간'][0],
        '주식매수취소시간초':    df_sb['주식매수취소시간초'][0],
        '주식매수금지블랙리스트': df_sb['주식매수금지블랙리스트'][0],
        '주식매수금지라운드피겨': df_sb['주식매수금지라운드피겨'][0],
        '주식매수금지라운드호가': df_sb['주식매수금지라운드호가'][0],
        '주식매수금지손절횟수':   df_sb['주식매수금지손절횟수'][0],
        '주식매수금지손절횟수값': df_sb['주식매수금지손절횟수값'][0],
        '주식매수금지거래횟수':   df_sb['주식매수금지거래횟수'][0],
        '주식매수금지거래횟수값': df_sb['주식매수금지거래횟수값'][0],
        '주식매수금지시간':      df_sb['주식매수금지시간'][0],
        '주식매수금지시작시간':   df_sb['주식매수금지시작시간'][0],
        '주식매수금지종료시간':   df_sb['주식매수금지종료시간'][0],
        '주식매수금지간격':      df_sb['주식매수금지간격'][0],
        '주식매수금지간격초':     df_sb['주식매수금지간격초'][0],
        '주식매수금지손절간격':   df_sb['주식매수금지손절간격'][0],
        '주식매수금지손절간격초': df_sb['주식매수금지손절간격초'][0],
        '주식매수정정횟수':      df_sb['주식매수정정횟수'][0],
        '주식매수정정호가차이':   df_sb['주식매수정정호가차이'][0],
        '주식매수정정호가':      df_sb['주식매수정정호가'][0],
        '주식비중조절':         [float(x) for x in df_sb['주식비중조절'][0].split(';')],

        '주식매도주문구분':      df_ss['주식매도주문구분'][0],
        '주식매도분할횟수':      df_ss['주식매도분할횟수'][0],
        '주식매도분할방법':      df_ss['주식매도분할방법'][0],
        '주식매도분할시그널':    df_ss['주식매도분할시그널'][0],
        '주식매도분할하방':      df_ss['주식매도분할하방'][0],
        '주식매도분할상방':      df_ss['주식매도분할상방'][0],
        '주식매도분할하방수익률': df_ss['주식매도분할하방수익률'][0],
        '주식매도분할상방수익률': df_ss['주식매도분할상방수익률'][0],
        '주식매도지정가기준가격': df_ss['주식매도지정가기준가격'][0],
        '주식매도지정가호가번호': df_ss['주식매도지정가호가번호'][0],
        '주식매도시장가잔량범위': df_ss['주식매도시장가잔량범위'][0],
        '주식매도취소관심진입':   df_ss['주식매도취소관심진입'][0],
        '주식매도취소매수시그널': df_ss['주식매도취소매수시그널'][0],
        '주식매도취소시간':      df_ss['주식매도취소시간'][0],
        '주식매도취소시간초':    df_ss['주식매도취소시간초'][0],
        '주식매도손절수익률청산': df_ss['주식매도손절수익률청산'][0],
        '주식매도손절수익률':    df_ss['주식매도손절수익률'][0],
        '주식매도손절수익금청산': df_ss['주식매도손절수익금청산'][0],
        '주식매도손절수익금':    df_ss['주식매도손절수익금'][0],
        '주식매도금지매수횟수':   df_ss['주식매도금지매수횟수'][0],
        '주식매도금지매수횟수값': df_ss['주식매도금지매수횟수값'][0],
        '주식매도금지라운드피겨': df_ss['주식매도금지라운드피겨'][0],
        '주식매도금지라운드호가': df_ss['주식매도금지라운드호가'][0],
        '주식매도금지시간':      df_ss['주식매도금지시간'][0],
        '주식매도금지시작시간':   df_ss['주식매도금지시작시간'][0],
        '주식매도금지종료시간':   df_ss['주식매도금지종료시간'][0],
        '주식매도금지간격':      df_ss['주식매도금지간격'][0],
        '주식매도금지간격초':    df_ss['주식매도금지간격초'][0],
        '주식매도정정횟수':      df_ss['주식매도정정횟수'][0],
        '주식매도정정호가차이':   df_ss['주식매도정정호가차이'][0],
        '주식매도정정호가':      df_ss['주식매도정정호가'][0],

        '코인매수주문구분':      df_cb['코인매수주문구분'][0],
        '코인매수분할횟수':      df_cb['코인매수분할횟수'][0],
        '코인매수분할방법':      df_cb['코인매수분할방법'][0],
        '코인매수분할시그널':    df_cb['코인매수분할시그널'][0],
        '코인매수분할하방':      df_cb['코인매수분할하방'][0],
        '코인매수분할상방':      df_cb['코인매수분할상방'][0],
        '코인매수분할하방수익률': df_cb['코인매수분할하방수익률'][0],
        '코인매수분할상방수익률': df_cb['코인매수분할상방수익률'][0],
        '코인매수분할고정수익률': df_cb['코인매수분할고정수익률'][0],
        '코인매수지정가기준가격': df_cb['코인매수지정가기준가격'][0],
        '코인매수지정가호가번호': df_cb['코인매수지정가호가번호'][0],
        '코인매수시장가잔량범위': df_cb['코인매수시장가잔량범위'][0],
        '코인매수취소관심이탈':   df_cb['코인매수취소관심이탈'][0],
        '코인매수취소매도시그널': df_cb['코인매수취소매도시그널'][0],
        '코인매수취소시간':      df_cb['코인매수취소시간'][0],
        '코인매수취소시간초':    df_cb['코인매수취소시간초'][0],
        '코인매수금지블랙리스트': df_cb['코인매수금지블랙리스트'][0],
        '코인매수금지200원이하': df_cb['코인매수금지200원이하'][0],
        '코인매수금지손절횟수':   df_cb['코인매수금지손절횟수'][0],
        '코인매수금지손절횟수값': df_cb['코인매수금지손절횟수값'][0],
        '코인매수금지거래횟수':   df_cb['코인매수금지거래횟수'][0],
        '코인매수금지거래횟수값': df_cb['코인매수금지거래횟수값'][0],
        '코인매수금지시간':      df_cb['코인매수금지시간'][0],
        '코인매수금지시작시간':   df_cb['코인매수금지시작시간'][0],
        '코인매수금지종료시간':   df_cb['코인매수금지종료시간'][0],
        '코인매수금지간격':      df_cb['코인매수금지간격'][0],
        '코인매수금지간격초':    df_cb['코인매수금지간격초'][0],
        '코인매수금지손절간격':   df_cb['코인매수금지손절간격'][0],
        '코인매수금지손절간격초': df_cb['코인매수금지손절간격초'][0],
        '코인매수정정횟수':      df_cb['코인매수정정횟수'][0],
        '코인매수정정호가차이':   df_cb['코인매수정정호가차이'][0],
        '코인매수정정호가':      df_cb['코인매수정정호가'][0],
        '코인비중조절':         [float(x) for x in df_cb['코인비중조절'][0].split(';')],

        '코인매도주문구분':      df_cs['코인매도주문구분'][0],
        '코인매도분할횟수':      df_cs['코인매도분할횟수'][0],
        '코인매도분할방법':      df_cs['코인매도분할방법'][0],
        '코인매도분할시그널':    df_cs['코인매도분할시그널'][0],
        '코인매도분할하방':      df_cs['코인매도분할하방'][0],
        '코인매도분할상방':      df_cs['코인매도분할상방'][0],
        '코인매도분할하방수익률': df_cs['코인매도분할하방수익률'][0],
        '코인매도분할상방수익률': df_cs['코인매도분할상방수익률'][0],
        '코인매도지정가기준가격': df_cs['코인매도지정가기준가격'][0],
        '코인매도지정가호가번호': df_cs['코인매도지정가호가번호'][0],
        '코인매도시장가잔량범위': df_cs['코인매도시장가잔량범위'][0],
        '코인매도취소관심진입':   df_cs['코인매도취소관심진입'][0],
        '코인매도취소매수시그널': df_cs['코인매도취소매수시그널'][0],
        '코인매도취소시간':      df_cs['코인매도취소시간'][0],
        '코인매도취소시간초':    df_cs['코인매도취소시간초'][0],
        '코인매도손절수익률청산': df_cs['코인매도손절수익률청산'][0],
        '코인매도손절수익률':    df_cs['코인매도손절수익률'][0],
        '코인매도손절수익금청산': df_cs['코인매도손절수익금청산'][0],
        '코인매도손절수익금':    df_cs['코인매도손절수익금'][0],
        '코인매도금지매수횟수':   df_cs['코인매도금지매수횟수'][0],
        '코인매도금지매수횟수값': df_cs['코인매도금지매수횟수값'][0],
        '코인매도금지시간':      df_cs['코인매도금지시간'][0],
        '코인매도금지시작시간':   df_cs['코인매도금지시작시간'][0],
        '코인매도금지종료시간':   df_cs['코인매도금지종료시간'][0],
        '코인매도금지간격':      df_cs['코인매도금지간격'][0],
        '코인매도금지간격초':    df_cs['코인매도금지간격초'][0],
        '코인매도정정횟수':      df_cs['코인매도정정횟수'][0],
        '코인매도정정호가차이':   df_cs['코인매도정정호가차이'][0],
        '코인매도정정호가':      df_cs['코인매도정정호가'][0],

        '스마트브이왑': False,
        '마이크로스트럭처분석': False,
        '에이전트프로파일링': False,
        '트레이더프로파일링': False,
        '전략연산프로파일링': False,
        '백테엔진프로파일링': False
    }
    # CLI headless 모드: 환경 변수로 전달된 DICT_SET 오버라이드 적용
    # Windows spawn 방식에서 손자 프로세스(Total 등)까지 설정을 전파하기 위함
    _cli_ovr = os.environ.get('_STOM_CLI_DICT_SET')
    if _cli_ovr:
        import json as _json
        DICT_SET.update(_json.loads(_cli_ovr))
    apply_serial_key_to_dict_set(
        DICT_SET,
        df_e,
        safe_de_text,
        uses_serial_key()
    )
except fernet.InvalidToken:
    logger_.critical('이 컴퓨터의 암호키로 생성된 계정이 아닙니다. setting.db를 삭제 후 재실행 하십시오.')
    sys.exit()
except KeyError:
    print_exc()
    logger_.error('setting.db가 구버전 상태입니다. 삭제 후 재실행 하십시오.')
    sys.exit()

ui_num = {'설정로그': 1, '종목명데이터': 1.2, '백테엔진': 1.4,
          'S단순텍스트': 2, 'S로그텍스트': 3, 'C단순텍스트': 4, 'C로그텍스트': 5,
          'S백테스트': 6, 'SF백테스트': 7, 'C백테스트': 8, 'CF백테스트': 9, 'DB관리': 10,
          'S실현손익': 11, 'S거래목록': 12, 'S잔고평가': 13, 'S잔고목록': 14, 'S체결목록': 15,
          'S당일합계': 16, 'S당일상세': 17, 'S누적합계': 18, 'S누적상세': 19, 'S관심종목': 20,
          'C실현손익': 21, 'C거래목록': 22, 'C잔고평가': 23, 'C잔고목록': 24, 'C체결목록': 25,
          'C당일합계': 26, 'C당일상세': 27, 'C누적합계': 28, 'C누적상세': 29, 'C관심종목': 30,
          'S호가종목': 31, 'S호가체결': 32, 'S호가잔량': 33, 'C호가종목': 34, 'C호가체결': 35, 'C호가잔량': 36,
          'S호가체결2': 36.1, 'C호가체결2': 36.2,
          '스톰라이브1': 37.1, '스톰라이브2': 37.2, '스톰라이브3': 37.3, '스톰라이브4': 37.4, '스톰라이브5': 37.5, '스톰라이브6': 37.6,
          '스톰라이브7': 37.7, '스톰라이브8': 37.8, '스톰라이브9': 37.9, '스톰라이브10': 37.91, '스톰라이브11': 37.92,
          '김프': 40, '기업개요': 41, '기업공시': 42, '기업뉴스': 43, '재무년도': 44, '재무분기': 45, 'S상세기록': 46, 'C상세기록': 47,
          '차트': 51, '실시간차트': 52, '코스피': 53, '코스닥': 54, '트리맵': 61, '트리맵1': 62, '트리맵2': 63, '풍경사진': 70}

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
