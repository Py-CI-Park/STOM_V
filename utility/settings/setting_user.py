
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
        no = int(df_m['거래소'][0][-2:])

        DICT_SET = {
            '키':            EN_KEY,
            '거래소':         df_m['거래소'][0],
            '타임프레임':      df_m['타임프레임'][0],
            '데이터저장':      df_m['데이터저장'][0],
            '모의투자':       df_m['모의투자'][0],
            '알림소리':       df_m['알림소리'][0],
            '프로그램비밀번호': de_text(EN_KEY, df_m['프로그램비밀번호'][0]) if df_m['프로그램비밀번호'][0] else '',

            '바이낸스선물고정레버리지':   df_m['바이낸스선물고정레버리지'][0],
            '바이낸스선물고정레버리지값': df_m['바이낸스선물고정레버리지값'][0],
            '바이낸스선물변동레버리지값': binance_leverage_,
            '바이낸스선물마진타입':     df_m['바이낸스선물마진타입'][0],
            '바이낸스선물포지션':       df_m['바이낸스선물포지션'][0],

            'access_key': de_text(EN_KEY, df_a['access_key'][no])  if df_a_not_empty and df_a['access_key'][no] else None,
            'secret_key': de_text(EN_KEY, df_a['secret_key'][no]) if df_a_not_empty and df_a['secret_key'][no] else None,

            '텔레그램봇토큰':     de_text(EN_KEY, df_t['bot_token'][no])   if df_t_not_empty and df_t['bot_token'][no] else None,
            '텔레그램아이디': int(de_text(EN_KEY, df_t['chatingid'][no]))  if df_t_not_empty and df_t['chatingid'][no] else None,

            '매수전략':     df_s['매수전략'][no],
            '매도전략':     df_s['매도전략'][no],
            '평균값계산틱수': df_s['평균값계산틱수'][no],
            '최대매수종목수': df_s['최대매수종목수'][no],
            '전략종료시간':  df_s['전략종료시간'][no],
            '잔고청산':     df_s['잔고청산'][no],
            '프로세스종료':  df_s['프로세스종료'][no],
            '컴퓨터종료':   df_s['컴퓨터종료'][no],
            '투자금고정':   df_s['투자금고정'][no],
            '투자금':      df_s['투자금'][no],
            '손실중지':     df_s['손실중지'][no],
            '손실중지수익률': df_s['손실중지수익률'][no],
            '수익중지':     df_s['수익중지'][no],
            '수익중지수익률': df_s['수익중지수익률'][no],

            '블랙리스트추가':     df_b['블랙리스트추가'][no],
            '백테주문관리적용':   df_b['백테주문관리적용'][no],
            '백테매수시간기준':   df_b['백테매수시간기준'][no],
            '백테일괄로딩':      df_b['백테일괄로딩'][no],
            '그래프저장하지않기': df_b['그래프저장하지않기'][no],
            '그래프띄우지않기':   df_b['그래프띄우지않기'][no],
            '디비자동관리':      df_b['디비자동관리'][no],
            '교차검증가중치':    df_b['교차검증가중치'][no],
            '기준값최소상승률':  df_b['기준값최소상승률'][no],
            '백테스케쥴실행':    df_b['백테스케쥴실행'][no],
            '백테스케쥴요일':    df_b['백테스케쥴요일'][no],
            '백테스케쥴시간':    df_b['백테스케쥴시간'][no],
            '백테스케쥴명':      df_b['백테스케쥴명'][no],
            '백테날짜고정':      df_b['백테날짜고정'][no],
            '백테날짜':         df_b['백테날짜'][no],
            '범위자동관리':      df_b['범위자동관리'][no],
            '보조지표설정':      [int(x) if '.' not in x else float(x) for x in df_b['보조지표설정'][no].split(';')],
            '최적화기준값제한':   df_b['최적화기준값제한'][no],
            '백테엔진분류방법':   df_b['백테엔진분류방법'][no],
            '옵튜나샘플러':      df_b['옵튜나샘플러'][no],
            '옵튜나고정변수':     df_b['옵튜나고정변수'][no],
            '옵튜나실행횟수':     df_b['옵튜나실행횟수'][no],
            '옵튜나자동스탭':     df_b['옵튜나자동스탭'][no],
            '백테스트로그기록안함': df_b['백테스트로그기록안함'][no],
            '시장미시구조분석':    df_b['시장미시구조분석'][no],
            '리스크분석':        df_b['리스크분석'][no],
            '패턴분석':         df_b['패턴분석'][no],
            '가격대분석':        df_b['가격대분석'][no],
            '자동학습':         df_b['자동학습'][no],

            '저해상도':         df_e['저해상도'][no],
            '휴무프로세스종료':   df_e['휴무프로세스종료'][no],
            '휴무컴퓨터종료':    df_e['휴무컴퓨터종료'][no],
            '창위치기억':       df_e['창위치기억'][no],
            '창위치':          [int(x) for x in df_e['창위치'][no].split(';')] if df_e['창위치'][no] else None,
            '스톰라이브':       df_e['스톰라이브'][no],
            '프로그램종료':      df_e['프로그램종료'][no],
            '테마':            df_e['테마'][no],
            '팩터선택':         df_e['팩터선택'][no],
            '웹대시보드':       df_e['웹대시보드'][no],
            '웹대시보드포트번호': df_e['웹대시보드포트번호'][no],
            '시리얼키':         de_text(EN_KEY, df_e['시리얼키'][no]) if len(df_e) > 0 and df_e['시리얼키'][no] else None,

            '매수주문유형':      df_bo['매수주문유형'][no],
            '매수분할횟수':      df_bo['매수분할횟수'][no],
            '매수분할방법':      df_bo['매수분할방법'][no],
            '매수분할시그널':    df_bo['매수분할시그널'][no],
            '매수분할하방':      df_bo['매수분할하방'][no],
            '매수분할상방':      df_bo['매수분할상방'][no],
            '매수분할하방수익률': df_bo['매수분할하방수익률'][no],
            '매수분할상방수익률': df_bo['매수분할상방수익률'][no],
            '매수분할고정수익률': df_bo['매수분할고정수익률'][no],
            '매수지정가기준가격': df_bo['매수지정가기준가격'][no],
            '매수지정가호가번호': df_bo['매수지정가호가번호'][no],
            '매수시장가잔량범위': df_bo['매수시장가잔량범위'][no],
            '매수취소관심이탈':   df_bo['매수취소관심이탈'][no],
            '매수취소매도시그널': df_bo['매수취소매도시그널'][no],
            '매수취소시간':      df_bo['매수취소시간'][no],
            '매수취소시간초':    df_bo['매수취소시간초'][no],
            '매수금지블랙리스트': df_bo['매수금지블랙리스트'][no],
            '매수금지손절횟수':   df_bo['매수금지손절횟수'][no],
            '매수금지손절횟수값': df_bo['매수금지손절횟수값'][no],
            '매수금지거래횟수':   df_bo['매수금지거래횟수'][no],
            '매수금지거래횟수값': df_bo['매수금지거래횟수값'][no],
            '매수금지시간':      df_bo['매수금지시간'][no],
            '매수금지시작시간':   df_bo['매수금지시작시간'][no],
            '매수금지종료시간':   df_bo['매수금지종료시간'][no],
            '매수금지간격':      df_bo['매수금지간격'][no],
            '매수금지간격초':     df_bo['매수금지간격초'][no],
            '매수금지손절간격':   df_bo['매수금지손절간격'][no],
            '매수금지손절간격초': df_bo['매수금지손절간격초'][no],
            '매수정정횟수':      df_bo['매수정정횟수'][no],
            '매수정정호가차이':   df_bo['매수정정호가차이'][no],
            '매수정정호가':      df_bo['매수정정호가'][no],
            '비중조절':         [float(x) for x in df_bo['비중조절'][no].split(';')],

            '매도주문유형':      df_so['매도주문유형'][no],
            '매도분할횟수':      df_so['매도분할횟수'][no],
            '매도분할방법':      df_so['매도분할방법'][no],
            '매도분할시그널':    df_so['매도분할시그널'][no],
            '매도분할하방':      df_so['매도분할하방'][no],
            '매도분할상방':      df_so['매도분할상방'][no],
            '매도분할하방수익률': df_so['매도분할하방수익률'][no],
            '매도분할상방수익률': df_so['매도분할상방수익률'][no],
            '매도지정가기준가격': df_so['매도지정가기준가격'][no],
            '매도지정가호가번호': df_so['매도지정가호가번호'][no],
            '매도시장가잔량범위': df_so['매도시장가잔량범위'][no],
            '매도취소관심진입':   df_so['매도취소관심진입'][no],
            '매도취소매수시그널': df_so['매도취소매수시그널'][no],
            '매도취소시간':      df_so['매도취소시간'][no],
            '매도취소시간초':    df_so['매도취소시간초'][no],
            '매도금지매수횟수':   df_so['매도금지매수횟수'][no],
            '매도금지매수횟수값': df_so['매도금지매수횟수값'][no],
            '매도금지시간':      df_so['매도금지시간'][no],
            '매도금지시작시간':   df_so['매도금지시작시간'][no],
            '매도금지종료시간':   df_so['매도금지종료시간'][no],
            '매도금지간격':      df_so['매도금지간격'][no],
            '매도금지간격초':    df_so['매도금지간격초'][no],
            '매도정정횟수':      df_so['매도정정횟수'][no],
            '매도정정호가차이':   df_so['매도정정호가차이'][no],
            '매도정정호가':      df_so['매도정정호가'][no],
            '매도익절수익률청산': df_so['매도익절수익률청산'][no],
            '매도익절수익률':    df_so['매도익절수익률'][no],
            '매도익절수익금청산': df_so['매도익절수익금청산'][no],
            '매도익절수익금':    df_so['매도익절수익금'][no],
            '매도손절수익률청산': df_so['매도손절수익률청산'][no],
            '매도손절수익률':    df_so['매도손절수익률'][no],
            '매도손절수익금청산': df_so['매도손절수익금청산'][no],
            '매도손절수익금':    df_so['매도손절수익금'][no],

            '백테엔진프로파일링': False
        }
    except fernet.InvalidToken:
        return 'fernet.InvalidToken'
    except Exception:
        return format_exc()
    else:
        return DICT_SET
