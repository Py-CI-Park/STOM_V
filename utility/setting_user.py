
with open('./utility/blacklist_stock.txt') as f:
    stockreadlines = f.readlines()
with open('./utility/blacklist_future.txt') as f:
    futurereadlines = f.readlines()
with open('./utility/blacklist_coin.txt') as f:
    coinreadlines = f.readlines()

blacklist_stock = []
blacklist_future = []
blacklist_coin = []
for readline in stockreadlines:
    blacklist_stock.append(readline.strip())
for readline in futurereadlines:
    blacklist_future.append(readline.strip())
for readline in coinreadlines:
    blacklist_coin.append(readline.strip())


def load_settings():
    import sqlite3
    import pandas as pd
    from cryptography import fernet
    from traceback import format_exc
    from utility.setting_base import DB_SETTING
    from utility.static import read_key, de_text

    EN_KEY = read_key()

    con   = sqlite3.connect(DB_SETTING)
    df_m  = pd.read_sql('SELECT * FROM main', con).set_index('index')
    df_s  = pd.read_sql('SELECT * FROM stock', con).set_index('index')
    df_c  = pd.read_sql('SELECT * FROM coin', con).set_index('index')
    df_sa = pd.read_sql('SELECT * FROM sacc', con).set_index('index')
    df_ca = pd.read_sql('SELECT * FROM cacc', con).set_index('index')
    df_t  = pd.read_sql('SELECT * FROM telegram', con).set_index('index')
    df_sb = pd.read_sql('SELECT * FROM stockbuyorder', con).set_index('index')
    df_ss = pd.read_sql('SELECT * FROM stocksellorder', con).set_index('index')
    df_cb = pd.read_sql('SELECT * FROM coinbuyorder', con).set_index('index')
    df_cs = pd.read_sql('SELECT * FROM coinsellorder', con).set_index('index')
    df_e  = pd.read_sql('SELECT * FROM etc', con).set_index('index')
    df_b  = pd.read_sql('SELECT * FROM back', con).set_index('index')
    con.close()

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
            '주식에이전트':    df_m['주식에이전트'][0],
            '주식트레이더':    df_m['주식트레이더'][0],
            '주식데이터저장':   df_m['주식데이터저장'][0],
            '거래소':         df_m['거래소'][0],
            '코인리시버':      df_m['코인리시버'][0],
            '코인트레이더':    df_m['코인트레이더'][0],
            '코인데이터저장':   df_m['코인데이터저장'][0],
    
            '바이낸스선물고정레버리지':   df_m['바이낸스선물고정레버리지'][0],
            '바이낸스선물고정레버리지값': df_m['바이낸스선물고정레버리지값'][0],
            '바이낸스선물변동레버리지값': binance_leverage_,
            '바이낸스선물마진타입':     df_m['바이낸스선물마진타입'][0],
            '바이낸스선물포지션':       df_m['바이낸스선물포지션'][0],
    
            '아이디1':        de_text(EN_KEY, df_sa['아이디'][1])         if df_sa_not_empty and df_sa['아이디'][1] else None,
            '비밀번호1':      de_text(EN_KEY, df_sa['비밀번호'][1])       if df_sa_not_empty and df_sa['비밀번호'][1] else None,
            '인증서비밀번호1': de_text(EN_KEY, df_sa['인증서비밀번호'][1])   if df_sa_not_empty and df_sa['인증서비밀번호'][1] else None,
            '계좌비밀번호1':   de_text(EN_KEY, df_sa['계좌비밀번호'][1])    if df_sa_not_empty and df_sa['계좌비밀번호'][1] else None,
            '아이디2':        de_text(EN_KEY, df_sa['아이디'][2])         if df_sa_not_empty and df_sa['아이디'][2] else None,
            '비밀번호2':      de_text(EN_KEY, df_sa['비밀번호'][2])        if df_sa_not_empty and df_sa['비밀번호'][2] else None,
            '인증서비밀번호2': de_text(EN_KEY, df_sa['인증서비밀번호'][2])   if df_sa_not_empty and df_sa['인증서비밀번호'][2] else None,
            '계좌비밀번호2':   de_text(EN_KEY, df_sa['계좌비밀번호'][2])    if df_sa_not_empty and df_sa['계좌비밀번호'][2] else None,
            '아이디3':        de_text(EN_KEY, df_sa['아이디'][3])         if df_sa_not_empty and df_sa['아이디'][3] else None,
            '비밀번호3':      de_text(EN_KEY, df_sa['비밀번호'][3])        if df_sa_not_empty and df_sa['비밀번호'][3] else None,
            '인증서비밀번호3': de_text(EN_KEY, df_sa['인증서비밀번호'][3])   if df_sa_not_empty and df_sa['인증서비밀번호'][3] else None,
            '계좌비밀번호3':   de_text(EN_KEY, df_sa['계좌비밀번호'][3])    if df_sa_not_empty and df_sa['계좌비밀번호'][3] else None,
            '아이디4':        de_text(EN_KEY, df_sa['아이디'][4])         if df_sa_not_empty and df_sa['아이디'][4] else None,
            '비밀번호4':      de_text(EN_KEY, df_sa['비밀번호'][4])        if df_sa_not_empty and df_sa['비밀번호'][4] else None,
            '인증서비밀번호4': de_text(EN_KEY, df_sa['인증서비밀번호'][4])   if df_sa_not_empty and df_sa['인증서비밀번호'][4] else None,
            '계좌비밀번호4':   de_text(EN_KEY, df_sa['계좌비밀번호'][4])    if df_sa_not_empty and df_sa['계좌비밀번호'][4] else None,
            '아이디5':        de_text(EN_KEY, df_sa['아이디'][5])         if df_sa_not_empty and df_sa['아이디'][5] else None,
            '비밀번호5':      de_text(EN_KEY, df_sa['비밀번호'][5])       if df_sa_not_empty and df_sa['비밀번호'][5] else None,
            '인증서비밀번호5': de_text(EN_KEY, df_sa['인증서비밀번호'][5])   if df_sa_not_empty and df_sa['인증서비밀번호'][5] else None,
            '계좌비밀번호5':   de_text(EN_KEY, df_sa['계좌비밀번호'][5])    if df_sa_not_empty and df_sa['계좌비밀번호'][5] else None,
            '아이디6':        de_text(EN_KEY, df_sa['아이디'][6])         if df_sa_not_empty and df_sa['아이디'][6] else None,
            '비밀번호6':      de_text(EN_KEY, df_sa['비밀번호'][6])        if df_sa_not_empty and df_sa['비밀번호'][6] else None,
            '인증서비밀번호6': de_text(EN_KEY, df_sa['인증서비밀번호'][6])   if df_sa_not_empty and df_sa['인증서비밀번호'][6] else None,
            '계좌비밀번호6':   de_text(EN_KEY, df_sa['계좌비밀번호'][6])    if df_sa_not_empty and df_sa['계좌비밀번호'][6] else None,
            '아이디7':        de_text(EN_KEY, df_sa['아이디'][7])         if df_sa_not_empty and df_sa['아이디'][7] else None,
            '비밀번호7':      de_text(EN_KEY, df_sa['비밀번호'][7])        if df_sa_not_empty and df_sa['비밀번호'][7] else None,
            '인증서비밀번호7': de_text(EN_KEY, df_sa['인증서비밀번호'][7])   if df_sa_not_empty and df_sa['인증서비밀번호'][7] else None,
            '계좌비밀번호7':   de_text(EN_KEY, df_sa['계좌비밀번호'][7])    if df_sa_not_empty and df_sa['계좌비밀번호'][7] else None,
            '아이디8':        de_text(EN_KEY, df_sa['아이디'][8])         if df_sa_not_empty and df_sa['아이디'][8] else None,
            '비밀번호8':      de_text(EN_KEY, df_sa['비밀번호'][8])        if df_sa_not_empty and df_sa['비밀번호'][8] else None,
            '인증서비밀번호8': de_text(EN_KEY, df_sa['인증서비밀번호'][8])   if df_sa_not_empty and df_sa['인증서비밀번호'][8] else None,
            '계좌비밀번호8':   de_text(EN_KEY, df_sa['계좌비밀번호'][8])    if df_sa_not_empty and df_sa['계좌비밀번호'][8] else None,
    
            'Access_key1':   de_text(EN_KEY, df_ca['Access_key'][1])    if df_ca_not_empty and df_ca['Access_key'][1] else None,
            'Secret_key1':   de_text(EN_KEY, df_ca['Secret_key'][1])    if df_ca_not_empty and df_ca['Secret_key'][1] else None,
            'Access_key2':   de_text(EN_KEY, df_ca['Access_key'][2])    if df_ca_not_empty and df_ca['Access_key'][2] else None,
            'Secret_key2':   de_text(EN_KEY, df_ca['Secret_key'][2])    if df_ca_not_empty and df_ca['Secret_key'][2] else None,
    
            '텔레그램봇토큰1':      de_text(EN_KEY, df_t['str_bot'][1])      if df_t_not_empty and df_t['str_bot'][1] else None,
            '텔레그램사용자아이디1': int(de_text(EN_KEY, df_t['int_id'][1]))  if df_t_not_empty and df_t['int_id'][1]  else None,
            '텔레그램봇토큰2':      de_text(EN_KEY, df_t['str_bot'][2])      if df_t_not_empty and df_t['str_bot'][2] else None,
            '텔레그램사용자아이디2': int(de_text(EN_KEY, df_t['int_id'][2]))  if df_t_not_empty and df_t['int_id'][2]  else None,
            '텔레그램봇토큰3':      de_text(EN_KEY, df_t['str_bot'][3])      if df_t_not_empty and df_t['str_bot'][3] else None,
            '텔레그램사용자아이디3': int(de_text(EN_KEY, df_t['int_id'][3]))  if df_t_not_empty and df_t['int_id'][3]  else None,
            '텔레그램봇토큰4':      de_text(EN_KEY, df_t['str_bot'][4])      if df_t_not_empty and df_t['str_bot'][4] else None,
            '텔레그램사용자아이디4': int(de_text(EN_KEY, df_t['int_id'][4]))  if df_t_not_empty and df_t['int_id'][4]  else None,
            '텔레그램봇토큰5':      de_text(EN_KEY, df_t['str_bot'][5])      if df_t_not_empty and df_t['str_bot'][5] else None,
            '텔레그램사용자아이디5': int(de_text(EN_KEY, df_t['int_id'][5]))  if df_t_not_empty and df_t['int_id'][5]  else None,
            '텔레그램봇토큰6':      de_text(EN_KEY, df_t['str_bot'][6])      if df_t_not_empty and df_t['str_bot'][6] else None,
            '텔레그램사용자아이디6': int(de_text(EN_KEY, df_t['int_id'][6]))  if df_t_not_empty and df_t['int_id'][6]  else None,
            '텔레그램봇토큰7':      de_text(EN_KEY, df_t['str_bot'][7])      if df_t_not_empty and df_t['str_bot'][7] else None,
            '텔레그램사용자아이디7': int(de_text(EN_KEY, df_t['int_id'][7]))  if df_t_not_empty and df_t['int_id'][7]  else None,
            '텔레그램봇토큰8':      de_text(EN_KEY, df_t['str_bot'][8])      if df_t_not_empty and df_t['str_bot'][8] else None,
            '텔레그램사용자아이디8': int(de_text(EN_KEY, df_t['int_id'][8]))  if df_t_not_empty and df_t['int_id'][8]  else None,
    
            '주식블랙리스트': blacklist_stock,
            '해선블랙리스트': blacklist_future,
            '코인블랙리스트': blacklist_coin,
    
            '주식모의투자':         df_s['주식모의투자'][0],
            '주식알림소리':         df_s['주식알림소리'][0],
            '주식매수전략':         df_s['주식매수전략'][0],
            '주식매도전략':         df_s['주식매도전략'][0],
            '주식타임프레임':       df_s['주식타임프레임'][0],
            '주식평균값계산틱수':    df_s['주식평균값계산틱수'][0],
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
            '코인평균값계산틱수':    df_c['코인평균값계산틱수'][0],
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
            '기준값최소상승률':      df_b['기준값최소상승률'][0],
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
            '백테스트로그기록안함':    df_b['백테스트로그기록안함'][0],
            '시장미시구조분석':       df_b['시장미시구조분석'][0],
            '시장리스크분석':        df_b['시장리스크분석'][0],
    
            '저해상도':            df_e['저해상도'][0],
            '휴무프로세스종료':      df_e['휴무프로세스종료'][0],
            '휴무컴퓨터종료':       df_e['휴무컴퓨터종료'][0],
            '창위치기억':          df_e['창위치기억'][0],
            '창위치':             [int(x) for x in df_e['창위치'][0].split(';')] if df_e['창위치'][0] else None,
            '스톰라이브':          df_e['스톰라이브'][0],
            '프로그램종료':         df_e['프로그램종료'][0],
            '테마':               df_e['테마'][0],
            '팩터선택':            df_e['팩터선택'][0],
            '시리얼키':            de_text(EN_KEY, df_e['시리얼키'][0]) if len(df_e) > 0 and df_e['시리얼키'][0] else None,
    
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
            '주식매도익절수익률청산': df_ss['주식매도익절수익률청산'][0],
            '주식매도익절수익률':    df_ss['주식매도익절수익률'][0],
            '주식매도익절수익금청산': df_ss['주식매도익절수익금청산'][0],
            '주식매도익절수익금':    df_ss['주식매도익절수익금'][0],
            '주식매도손절수익률청산': df_ss['주식매도손절수익률청산'][0],
            '주식매도손절수익률':    df_ss['주식매도손절수익률'][0],
            '주식매도손절수익금청산': df_ss['주식매도손절수익금청산'][0],
            '주식매도손절수익금':    df_ss['주식매도손절수익금'][0],
    
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
            '코인매도익절수익률청산': df_cs['코인매도익절수익률청산'][0],
            '코인매도익절수익률':    df_cs['코인매도익절수익률'][0],
            '코인매도익절수익금청산': df_cs['코인매도익절수익금청산'][0],
            '코인매도익절수익금':    df_cs['코인매도익절수익금'][0],
            '코인매도손절수익률청산': df_cs['코인매도손절수익률청산'][0],
            '코인매도손절수익률':    df_cs['코인매도손절수익률'][0],
            '코인매도손절수익금청산': df_cs['코인매도손절수익금청산'][0],
            '코인매도손절수익금':    df_cs['코인매도손절수익금'][0],

            '에이전트프로파일링': False,
            '트레이더프로파일링': False,
            '전략연산프로파일링': False,
            '백테엔진프로파일링': False
        }
    except fernet.InvalidToken:
        return 'fernet.InvalidToken'
    except:
        return format_exc()
    else:
        return DICT_SET
