
def load_settings():
    """설정을 로드합니다.
    데이터베이스에서 설정을 읽어와 딕셔너리로 반환합니다.
    Returns:
        설정 딕셔너리
    """
    import sqlite3
    import pandas as pd
    from cryptography import fernet
    from traceback import format_exc
    from utility.settings.setting_base import DB_SETTING
    from utility.static_method.static import read_key, de_text

    EN_KEY = read_key()

    con   = sqlite3.connect(DB_SETTING)
    df_m  = pd.read_sql('SELECT * FROM main', con).set_index('index')
    df_a  = pd.read_sql('SELECT * FROM account', con).set_index('index')
    df_t  = pd.read_sql('SELECT * FROM telegram', con).set_index('index')
    df_s  = pd.read_sql('SELECT * FROM strategy', con).set_index('index')
    df_b  = pd.read_sql('SELECT * FROM back', con).set_index('index')
    df_e  = pd.read_sql('SELECT * FROM etc', con).set_index('index')
    df_bo = pd.read_sql('SELECT * FROM buyorder', con).set_index('index')
    df_so = pd.read_sql('SELECT * FROM sellorder', con).set_index('index')
    con.close()

    binance_leverage_ = []
    for text_ in df_m['바이낸스선물변동레버리지값'][0].split('^'):
        lvrg_list_ = text_.split(';')
        lvrg_list_ = [float(x) for x in lvrg_list_]
        binance_leverage_.append(lvrg_list_)

    df_a_not_empty = True if len(df_a) > 0 else False
    df_t_not_empty  = True if len(df_t) > 0 else False

    try:
        DICT_SET = {
            '키':            EN_KEY,
            '거래소':         df_m['거래소'][0],
            '모의투자':       df_m['모의투자'][0],
            '데이터저장':      df_m['데이터저장'][0],
            '알림소리':       df_m['알림소리'][0],
            '타임프레임':      df_m['타임프레임'][0],
            '프로그램비밀번호': de_text(EN_KEY, df_m['프로그램비밀번호'][0]) if df_m['프로그램비밀번호'][0] else '',

            '바이낸스선물고정레버리지':   df_m['바이낸스선물고정레버리지'][0],
            '바이낸스선물고정레버리지값': df_m['바이낸스선물고정레버리지값'][0],
            '바이낸스선물변동레버리지값': binance_leverage_,
            '바이낸스선물마진타입':     df_m['바이낸스선물마진타입'][0],
            '바이낸스선물포지션':       df_m['바이낸스선물포지션'][0],

            'access_key01': de_text(EN_KEY, df_a['access_key'][1])  if df_a_not_empty and df_a['access_key'][1] else None,
            'secret_key01': de_text(EN_KEY, df_a['secret_key'][1])  if df_a_not_empty and df_a['secret_key'][1] else None,
            'access_key02': de_text(EN_KEY, df_a['access_key'][2])  if df_a_not_empty and df_a['access_key'][2] else None,
            'secret_key02': de_text(EN_KEY, df_a['secret_key'][2])  if df_a_not_empty and df_a['secret_key'][2] else None,
            'access_key03': de_text(EN_KEY, df_a['access_key'][3])  if df_a_not_empty and df_a['access_key'][3] else None,
            'secret_key03': de_text(EN_KEY, df_a['secret_key'][3])  if df_a_not_empty and df_a['secret_key'][3] else None,
            'access_key04': de_text(EN_KEY, df_a['access_key'][4])  if df_a_not_empty and df_a['access_key'][4] else None,
            'secret_key04': de_text(EN_KEY, df_a['secret_key'][4])  if df_a_not_empty and df_a['secret_key'][4] else None,
            'access_key05': de_text(EN_KEY, df_a['access_key'][5])  if df_a_not_empty and df_a['access_key'][5] else None,
            'secret_key05': de_text(EN_KEY, df_a['secret_key'][5])  if df_a_not_empty and df_a['secret_key'][5] else None,
            'access_key06': de_text(EN_KEY, df_a['access_key'][6])  if df_a_not_empty and df_a['access_key'][6] else None,
            'secret_key06': de_text(EN_KEY, df_a['secret_key'][6])  if df_a_not_empty and df_a['secret_key'][6] else None,
            'access_key07': de_text(EN_KEY, df_a['access_key'][7])  if df_a_not_empty and df_a['access_key'][7] else None,
            'secret_key07': de_text(EN_KEY, df_a['secret_key'][7])  if df_a_not_empty and df_a['secret_key'][7] else None,
            'access_key08': de_text(EN_KEY, df_a['access_key'][8])  if df_a_not_empty and df_a['access_key'][8] else None,
            'secret_key08': de_text(EN_KEY, df_a['secret_key'][8])  if df_a_not_empty and df_a['secret_key'][8] else None,
            'access_key09': de_text(EN_KEY, df_a['access_key'][9])  if df_a_not_empty and df_a['access_key'][9] else None,
            'secret_key09': de_text(EN_KEY, df_a['secret_key'][9])  if df_a_not_empty and df_a['secret_key'][9] else None,
            'access_key10': de_text(EN_KEY, df_a['access_key'][10]) if df_a_not_empty and df_a['access_key'][10] else None,
            'secret_key10': de_text(EN_KEY, df_a['secret_key'][10]) if df_a_not_empty and df_a['secret_key'][10] else None,
            'access_key11': de_text(EN_KEY, df_a['access_key'][11]) if df_a_not_empty and df_a['access_key'][11] else None,
            'secret_key11': de_text(EN_KEY, df_a['secret_key'][11]) if df_a_not_empty and df_a['secret_key'][11] else None,
            'access_key12': de_text(EN_KEY, df_a['access_key'][12]) if df_a_not_empty and df_a['access_key'][12] else None,
            'secret_key12': de_text(EN_KEY, df_a['secret_key'][12]) if df_a_not_empty and df_a['secret_key'][12] else None,
            'access_key13': de_text(EN_KEY, df_a['access_key'][13]) if df_a_not_empty and df_a['access_key'][13] else None,
            'secret_key13': de_text(EN_KEY, df_a['secret_key'][13]) if df_a_not_empty and df_a['secret_key'][13] else None,
            'access_key14': de_text(EN_KEY, df_a['access_key'][14]) if df_a_not_empty and df_a['access_key'][14] else None,
            'secret_key14': de_text(EN_KEY, df_a['secret_key'][14]) if df_a_not_empty and df_a['secret_key'][14] else None,
            'access_key15': de_text(EN_KEY, df_a['access_key'][15]) if df_a_not_empty and df_a['access_key'][15] else None,
            'secret_key15': de_text(EN_KEY, df_a['secret_key'][15]) if df_a_not_empty and df_a['secret_key'][15] else None,
            'access_key16': de_text(EN_KEY, df_a['access_key'][16]) if df_a_not_empty and df_a['access_key'][16] else None,
            'secret_key16': de_text(EN_KEY, df_a['secret_key'][16]) if df_a_not_empty and df_a['secret_key'][16] else None,
            'access_key17': de_text(EN_KEY, df_a['access_key'][17]) if df_a_not_empty and df_a['access_key'][17] else None,
            'secret_key17': de_text(EN_KEY, df_a['secret_key'][17]) if df_a_not_empty and df_a['secret_key'][17] else None,
            'access_key18': de_text(EN_KEY, df_a['access_key'][18]) if df_a_not_empty and df_a['access_key'][18] else None,
            'secret_key18': de_text(EN_KEY, df_a['secret_key'][18]) if df_a_not_empty and df_a['secret_key'][18] else None,

            '텔레그램봇토큰01':     de_text(EN_KEY, df_t['bot_token'][1])   if df_t_not_empty and df_t['bot_token'][1] else None,
            '텔레그램아이디01': int(de_text(EN_KEY, df_t['chatingid'][1]))  if df_t_not_empty and df_t['chatingid'][1] else None,
            '텔레그램봇토큰02':     de_text(EN_KEY, df_t['bot_token'][2])   if df_t_not_empty and df_t['bot_token'][2] else None,
            '텔레그램아이디02': int(de_text(EN_KEY, df_t['chatingid'][2]))  if df_t_not_empty and df_t['chatingid'][2] else None,
            '텔레그램봇토큰03':     de_text(EN_KEY, df_t['bot_token'][3])   if df_t_not_empty and df_t['bot_token'][3] else None,
            '텔레그램아이디03': int(de_text(EN_KEY, df_t['chatingid'][3]))  if df_t_not_empty and df_t['chatingid'][3] else None,
            '텔레그램봇토큰04':     de_text(EN_KEY, df_t['bot_token'][4])   if df_t_not_empty and df_t['bot_token'][4] else None,
            '텔레그램아이디04': int(de_text(EN_KEY, df_t['chatingid'][4]))  if df_t_not_empty and df_t['chatingid'][4] else None,
            '텔레그램봇토큰05':     de_text(EN_KEY, df_t['bot_token'][5])   if df_t_not_empty and df_t['bot_token'][5] else None,
            '텔레그램아이디05': int(de_text(EN_KEY, df_t['chatingid'][5]))  if df_t_not_empty and df_t['chatingid'][5] else None,
            '텔레그램봇토큰06':     de_text(EN_KEY, df_t['bot_token'][6])   if df_t_not_empty and df_t['bot_token'][6] else None,
            '텔레그램아이디06': int(de_text(EN_KEY, df_t['chatingid'][6]))  if df_t_not_empty and df_t['chatingid'][6] else None,
            '텔레그램봇토큰07':     de_text(EN_KEY, df_t['bot_token'][7])   if df_t_not_empty and df_t['bot_token'][7] else None,
            '텔레그램아이디07': int(de_text(EN_KEY, df_t['chatingid'][7]))  if df_t_not_empty and df_t['chatingid'][7] else None,
            '텔레그램봇토큰08':     de_text(EN_KEY, df_t['bot_token'][8])   if df_t_not_empty and df_t['bot_token'][8] else None,
            '텔레그램아이디08': int(de_text(EN_KEY, df_t['chatingid'][8]))  if df_t_not_empty and df_t['chatingid'][8] else None,
            '텔레그램봇토큰09':     de_text(EN_KEY, df_t['bot_token'][9])   if df_t_not_empty and df_t['bot_token'][9] else None,
            '텔레그램아이디09': int(de_text(EN_KEY, df_t['chatingid'][9]))  if df_t_not_empty and df_t['chatingid'][9] else None,
            '텔레그램봇토큰10':     de_text(EN_KEY, df_t['bot_token'][10])  if df_t_not_empty and df_t['bot_token'][10] else None,
            '텔레그램아이디10': int(de_text(EN_KEY, df_t['chatingid'][10])) if df_t_not_empty and df_t['chatingid'][10] else None,
            '텔레그램봇토큰11':     de_text(EN_KEY, df_t['bot_token'][11])  if df_t_not_empty and df_t['bot_token'][11] else None,
            '텔레그램아이디11': int(de_text(EN_KEY, df_t['chatingid'][11])) if df_t_not_empty and df_t['chatingid'][11] else None,
            '텔레그램봇토큰12':     de_text(EN_KEY, df_t['bot_token'][12])  if df_t_not_empty and df_t['bot_token'][12] else None,
            '텔레그램아이디12': int(de_text(EN_KEY, df_t['chatingid'][12])) if df_t_not_empty and df_t['chatingid'][12] else None,
            '텔레그램봇토큰13':     de_text(EN_KEY, df_t['bot_token'][13])  if df_t_not_empty and df_t['bot_token'][13] else None,
            '텔레그램아이디13': int(de_text(EN_KEY, df_t['chatingid'][13])) if df_t_not_empty and df_t['chatingid'][13] else None,
            '텔레그램봇토큰14':     de_text(EN_KEY, df_t['bot_token'][14])  if df_t_not_empty and df_t['bot_token'][14] else None,
            '텔레그램아이디14': int(de_text(EN_KEY, df_t['chatingid'][14])) if df_t_not_empty and df_t['chatingid'][14] else None,
            '텔레그램봇토큰15':     de_text(EN_KEY, df_t['bot_token'][15])  if df_t_not_empty and df_t['bot_token'][15] else None,
            '텔레그램아이디15': int(de_text(EN_KEY, df_t['chatingid'][15])) if df_t_not_empty and df_t['chatingid'][15] else None,
            '텔레그램봇토큰16':     de_text(EN_KEY, df_t['bot_token'][16])  if df_t_not_empty and df_t['bot_token'][16] else None,
            '텔레그램아이디16': int(de_text(EN_KEY, df_t['chatingid'][16])) if df_t_not_empty and df_t['chatingid'][16] else None,
            '텔레그램봇토큰17':     de_text(EN_KEY, df_t['bot_token'][17])  if df_t_not_empty and df_t['bot_token'][17] else None,
            '텔레그램아이디17': int(de_text(EN_KEY, df_t['chatingid'][17])) if df_t_not_empty and df_t['chatingid'][17] else None,
            '텔레그램봇토큰18':     de_text(EN_KEY, df_t['bot_token'][18])  if df_t_not_empty and df_t['bot_token'][18] else None,
            '텔레그램아이디18': int(de_text(EN_KEY, df_t['chatingid'][18])) if df_t_not_empty and df_t['chatingid'][18] else None,

            '매수전략':     df_s['매수전략'][0],
            '매도전략':     df_s['매도전략'][0],
            '평균값계산틱수': df_s['평균값계산틱수'][0],
            '최대매수종목수': df_s['최대매수종목수'][0],
            '전략종료시간':  df_s['전략종료시간'][0],
            '잔고청산':     df_s['잔고청산'][0],
            '프로세스종료':  df_s['프로세스종료'][0],
            '컴퓨터종료':   df_s['컴퓨터종료'][0],
            '투자금고정':   df_s['투자금고정'][0],
            '투자금':      df_s['투자금'][0],
            '손실중지':     df_s['손실중지'][0],
            '손실중지수익률': df_s['손실중지수익률'][0],
            '수익중지':     df_s['수익중지'][0],
            '수익중지수익률': df_s['수익중지수익률'][0],

            '블랙리스트추가':     df_b['블랙리스트추가'][0],
            '백테주문관리적용':   df_b['백테주문관리적용'][0],
            '백테매수시간기준':   df_b['백테매수시간기준'][0],
            '백테일괄로딩':      df_b['백테일괄로딩'][0],
            '그래프저장하지않기': df_b['그래프저장하지않기'][0],
            '그래프띄우지않기':   df_b['그래프띄우지않기'][0],
            '디비자동관리':      df_b['디비자동관리'][0],
            '교차검증가중치':    df_b['교차검증가중치'][0],
            '기준값최소상승률':  df_b['기준값최소상승률'][0],
            '백테스케쥴실행':    df_b['백테스케쥴실행'][0],
            '백테스케쥴요일':    df_b['백테스케쥴요일'][0],
            '백테스케쥴시간':    df_b['백테스케쥴시간'][0],
            '백테스케쥴구분':    df_b['백테스케쥴구분'][0],
            '백테스케쥴명':      df_b['백테스케쥴명'][0],
            '백테날짜고정':      df_b['백테날짜고정'][0],
            '백테날짜':         df_b['백테날짜'][0],
            '범위자동관리':      df_b['범위자동관리'][0],
            '보조지표설정':      [int(x) if '.' not in x else float(x) for x in df_b['보조지표설정'][0].split(';')],
            '최적화기준값제한':   df_b['최적화기준값제한'][0],
            '백테엔진분류방법':   df_b['백테엔진분류방법'][0],
            '옵튜나샘플러':      df_b['옵튜나샘플러'][0],
            '옵튜나고정변수':     df_b['옵튜나고정변수'][0],
            '옵튜나실행횟수':     df_b['옵튜나실행횟수'][0],
            '옵튜나자동스탭':     df_b['옵튜나자동스탭'][0],
            '백테스트로그기록안함': df_b['백테스트로그기록안함'][0],
            '시장미시구조분석':    df_b['시장미시구조분석'][0],
            '시장리스크분석':     df_b['시장리스크분석'][0],

            '저해상도':         df_e['저해상도'][0],
            '휴무프로세스종료':   df_e['휴무프로세스종료'][0],
            '휴무컴퓨터종료':    df_e['휴무컴퓨터종료'][0],
            '창위치기억':       df_e['창위치기억'][0],
            '창위치':          [int(x) for x in df_e['창위치'][0].split(';')] if df_e['창위치'][0] else None,
            '스톰라이브':       df_e['스톰라이브'][0],
            '프로그램종료':      df_e['프로그램종료'][0],
            '테마':            df_e['테마'][0],
            '팩터선택':         df_e['팩터선택'][0],
            '웹대시보드':       df_e['웹대시보드'][0],
            '웹대시보드포트번호': df_e['웹대시보드포트번호'][0],
            '시리얼키':         de_text(EN_KEY, df_e['시리얼키'][0]) if len(df_e) > 0 and df_e['시리얼키'][0] else None,

            '매수주문유형':      df_bo['매수주문유형'][0],
            '매수분할횟수':      df_bo['매수분할횟수'][0],
            '매수분할방법':      df_bo['매수분할방법'][0],
            '매수분할시그널':    df_bo['매수분할시그널'][0],
            '매수분할하방':      df_bo['매수분할하방'][0],
            '매수분할상방':      df_bo['매수분할상방'][0],
            '매수분할하방수익률': df_bo['매수분할하방수익률'][0],
            '매수분할상방수익률': df_bo['매수분할상방수익률'][0],
            '매수분할고정수익률': df_bo['매수분할고정수익률'][0],
            '매수지정가기준가격': df_bo['매수지정가기준가격'][0],
            '매수지정가호가번호': df_bo['매수지정가호가번호'][0],
            '매수시장가잔량범위': df_bo['매수시장가잔량범위'][0],
            '매수취소관심이탈':   df_bo['매수취소관심이탈'][0],
            '매수취소매도시그널': df_bo['매수취소매도시그널'][0],
            '매수취소시간':      df_bo['매수취소시간'][0],
            '매수취소시간초':    df_bo['매수취소시간초'][0],
            '매수금지블랙리스트': df_bo['매수금지블랙리스트'][0],
            '매수금지손절횟수':   df_bo['매수금지손절횟수'][0],
            '매수금지손절횟수값': df_bo['매수금지손절횟수값'][0],
            '매수금지거래횟수':   df_bo['매수금지거래횟수'][0],
            '매수금지거래횟수값': df_bo['매수금지거래횟수값'][0],
            '매수금지시간':      df_bo['매수금지시간'][0],
            '매수금지시작시간':   df_bo['매수금지시작시간'][0],
            '매수금지종료시간':   df_bo['매수금지종료시간'][0],
            '매수금지간격':      df_bo['매수금지간격'][0],
            '매수금지간격초':     df_bo['매수금지간격초'][0],
            '매수금지손절간격':   df_bo['매수금지손절간격'][0],
            '매수금지손절간격초': df_bo['매수금지손절간격초'][0],
            '매수정정횟수':      df_bo['매수정정횟수'][0],
            '매수정정호가차이':   df_bo['매수정정호가차이'][0],
            '매수정정호가':      df_bo['매수정정호가'][0],
            '비중조절':         [float(x) for x in df_bo['비중조절'][0].split(';')],

            '매도주문유형':      df_so['매도주문유형'][0],
            '매도분할횟수':      df_so['매도분할횟수'][0],
            '매도분할방법':      df_so['매도분할방법'][0],
            '매도분할시그널':    df_so['매도분할시그널'][0],
            '매도분할하방':      df_so['매도분할하방'][0],
            '매도분할상방':      df_so['매도분할상방'][0],
            '매도분할하방수익률': df_so['매도분할하방수익률'][0],
            '매도분할상방수익률': df_so['매도분할상방수익률'][0],
            '매도지정가기준가격': df_so['매도지정가기준가격'][0],
            '매도지정가호가번호': df_so['매도지정가호가번호'][0],
            '매도시장가잔량범위': df_so['매도시장가잔량범위'][0],
            '매도취소관심진입':   df_so['매도취소관심진입'][0],
            '매도취소매수시그널': df_so['매도취소매수시그널'][0],
            '매도취소시간':      df_so['매도취소시간'][0],
            '매도취소시간초':    df_so['매도취소시간초'][0],
            '매도금지매수횟수':   df_so['매도금지매수횟수'][0],
            '매도금지매수횟수값': df_so['매도금지매수횟수값'][0],
            '매도금지시간':      df_so['매도금지시간'][0],
            '매도금지시작시간':   df_so['매도금지시작시간'][0],
            '매도금지종료시간':   df_so['매도금지종료시간'][0],
            '매도금지간격':      df_so['매도금지간격'][0],
            '매도금지간격초':    df_so['매도금지간격초'][0],
            '매도정정횟수':      df_so['매도정정횟수'][0],
            '매도정정호가차이':   df_so['매도정정호가차이'][0],
            '매도정정호가':      df_so['매도정정호가'][0],
            '매도익절수익률청산': df_so['매도익절수익률청산'][0],
            '매도익절수익률':    df_so['매도익절수익률'][0],
            '매도익절수익금청산': df_so['매도익절수익금청산'][0],
            '매도익절수익금':    df_so['매도익절수익금'][0],
            '매도손절수익률청산': df_so['매도손절수익률청산'][0],
            '매도손절수익률':    df_so['매도손절수익률'][0],
            '매도손절수익금청산': df_so['매도손절수익금청산'][0],
            '매도손절수익금':    df_so['매도손절수익금'][0],

            '백테엔진프로파일링': False
        }
    except fernet.InvalidToken:
        return 'fernet.InvalidToken'
    except Exception:
        return format_exc()
    else:
        return DICT_SET
