"""
Settings Adapter for CLI
========================

PyQt5 없이 DICT_SET 및 데이터베이스 경로를 로드하는 어댑터.
"""

import sqlite3
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from traceback import print_exc
from utility.static import read_key, de_text, get_logger

logger_ = get_logger('SettingsAdapter')

# Database paths
DB_PATH = './_database'
DB_SETTING = './_database/setting.db'
DB_BACKTEST = './_database/backtest.db'
DB_TRADELIST = './_database/tradelist.db'
DB_STRATEGY = './_database/strategy.db'
DB_STOCK_TICK = './_database/stock_tick.db'
DB_STOCK_MIN = './_database/stock_min.db'
DB_STOCK_BACK_TICK = './_database/stock_tick_back.db'
DB_STOCK_BACK_MIN = './_database/stock_min_back.db'
DB_COIN_TICK = './_database/coin_tick.db'
DB_COIN_MIN = './_database/coin_min.db'
DB_COIN_BACK_TICK = './_database/coin_tick_back.db'
DB_COIN_BACK_MIN = './_database/coin_min_back.db'
DB_FUTURE_TICK = './_database/future_tick.db'
DB_FUTURE_MIN = './_database/future_min.db'
DB_FUTURE_BACK_TICK = './_database/future_tick_back.db'
DB_FUTURE_BACK_MIN = './_database/future_min_back.db'
DB_CODE_INFO = './_database/code_info.db'


def get_database_paths() -> Dict[str, str]:
    """모든 데이터베이스 경로 반환"""
    return {
        'setting': DB_SETTING,
        'backtest': DB_BACKTEST,
        'tradelist': DB_TRADELIST,
        'strategy': DB_STRATEGY,
        'stock_tick': DB_STOCK_TICK,
        'stock_min': DB_STOCK_MIN,
        'stock_back_tick': DB_STOCK_BACK_TICK,
        'stock_back_min': DB_STOCK_BACK_MIN,
        'coin_tick': DB_COIN_TICK,
        'coin_min': DB_COIN_MIN,
        'coin_back_tick': DB_COIN_BACK_TICK,
        'coin_back_min': DB_COIN_BACK_MIN,
        'future_tick': DB_FUTURE_TICK,
        'future_min': DB_FUTURE_MIN,
        'future_back_tick': DB_FUTURE_BACK_TICK,
        'future_back_min': DB_FUTURE_BACK_MIN,
        'code_info': DB_CODE_INFO,
    }


def _load_blacklists() -> Tuple[List[str], List[str], List[str]]:
    """블랙리스트 파일 로드"""
    blacklist_stock = []
    blacklist_future = []
    blacklist_coin = []

    try:
        with open('./utility/blacklist_stock.txt') as f:
            for line in f:
                blacklist_stock.append(line.strip())
    except FileNotFoundError:
        logger_.warning("blacklist_stock.txt not found")

    try:
        with open('./utility/blacklist_future.txt') as f:
            for line in f:
                blacklist_future.append(line.strip())
    except FileNotFoundError:
        logger_.warning("blacklist_future.txt not found")

    try:
        with open('./utility/blacklist_coin.txt') as f:
            for line in f:
                blacklist_coin.append(line.strip())
    except FileNotFoundError:
        logger_.warning("blacklist_coin.txt not found")

    return blacklist_stock, blacklist_future, blacklist_coin


def get_blacklists() -> Dict[str, List[str]]:
    """블랙리스트 딕셔너리 반환"""
    stock_bl, future_bl, coin_bl = _load_blacklists()
    return {
        'stock': stock_bl,
        'future': future_bl,
        'coin': coin_bl,
    }


def _load_database_records() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame,
                                      pd.DataFrame, pd.DataFrame, pd.DataFrame,
                                      pd.DataFrame, pd.DataFrame, pd.DataFrame,
                                      pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """설정 데이터베이스에서 모든 테이블 로드"""
    try:
        con = sqlite3.connect(DB_SETTING)
        df1 = pd.read_sql('SELECT * FROM main', con).set_index('index')
        df2 = pd.read_sql('SELECT * FROM stock', con).set_index('index')
        df3 = pd.read_sql('SELECT * FROM coin', con).set_index('index')
        df4 = pd.read_sql('SELECT * FROM sacc', con).set_index('index')
        df5 = pd.read_sql('SELECT * FROM cacc', con).set_index('index')
        df6 = pd.read_sql('SELECT * FROM telegram', con).set_index('index')
        df7 = pd.read_sql('SELECT * FROM stockbuyorder', con).set_index('index')
        df8 = pd.read_sql('SELECT * FROM stocksellorder', con).set_index('index')
        df9 = pd.read_sql('SELECT * FROM coinbuyorder', con).set_index('index')
        df10 = pd.read_sql('SELECT * FROM coinsellorder', con).set_index('index')
        df11 = pd.read_sql('SELECT * FROM etc', con).set_index('index')
        df12 = pd.read_sql('SELECT * FROM back', con).set_index('index')
        con.close()
        return df1, df2, df3, df4, df5, df6, df7, df8, df9, df10, df11, df12
    except Exception as e:
        logger_.error(f"Failed to load database records: {e}")
        print_exc()
        raise


def _safe_get(df: pd.DataFrame, col: str, idx: int, en_key: bytes, decrypt: bool = False) -> Any:
    """데이터프레임에서 안전하게 값 추출 (암호화된 경우 복호화)"""
    try:
        if df is None or len(df) == 0 or col not in df.columns:
            return None

        val = df[col][idx] if idx in df.index else None

        if val is None or val == '':
            return None

        if decrypt:
            return de_text(en_key, val)
        return val
    except Exception as e:
        logger_.debug(f"Error getting value from {col}[{idx}]: {e}")
        return None


def load_settings_without_qt() -> Dict[str, Any]:
    """
    PyQt5 없이 DICT_SET 로드

    Returns:
        Dict[str, Any]: 설정 딕셔너리
    """
    try:
        # 키 로드
        en_key = read_key()

        # 데이터베이스 로드
        df_m, df_s, df_c, df_sa, df_ca, df_t, df_sb, df_ss, df_cb, df_cs, df_e, df_b = _load_database_records()

        # 플래그
        df_sa_not_empty = len(df_sa) > 0
        df_ca_not_empty = len(df_ca) > 0
        df_t_not_empty = len(df_t) > 0

        # 바이낸스 레버리지 파싱
        binance_leverage_ = []
        try:
            lvrg_str = df_m['바이낸스선물변동레버리지값'][0]
            for text_ in lvrg_str.split('^'):
                lvrg_list_ = [float(x) for x in text_.split(';')]
                binance_leverage_.append(lvrg_list_)
        except Exception as e:
            logger_.warning(f"Failed to parse binance leverage: {e}")

        # 보조지표 파싱
        try:
            indicator_str = df_b['보조지표설정'][0]
            indicators = [int(x) if '.' not in x else float(x) for x in indicator_str.split(';')]
        except Exception as e:
            logger_.warning(f"Failed to parse indicators: {e}")
            indicators = []

        # 창위치 파싱
        try:
            window_pos_str = df_e['창위치'][0]
            window_pos = [int(x) for x in window_pos_str.split(';')] if window_pos_str else None
        except Exception as e:
            logger_.warning(f"Failed to parse window position: {e}")
            window_pos = None

        # 블랙리스트 로드
        blacklist_stock, blacklist_future, blacklist_coin = _load_blacklists()

        # DICT_SET 구성
        dict_set = {
            # 기본 설정
            '키': en_key,
            '증권사': _safe_get(df_m, '증권사', 0, en_key),
            '주식에이전트': _safe_get(df_m, '주식에이전트', 0, en_key),
            '주식트레이더': _safe_get(df_m, '주식트레이더', 0, en_key),
            '주식데이터저장': _safe_get(df_m, '주식데이터저장', 0, en_key),
            '거래소': _safe_get(df_m, '거래소', 0, en_key),
            '코인리시버': _safe_get(df_m, '코인리시버', 0, en_key),
            '코인트레이더': _safe_get(df_m, '코인트레이더', 0, en_key),
            '코인데이터저장': _safe_get(df_m, '코인데이터저장', 0, en_key),

            # 바이낸스 설정
            '바이낸스선물고정레버리지': _safe_get(df_m, '바이낸스선물고정레버리지', 0, en_key),
            '바이낸스선물고정레버리지값': _safe_get(df_m, '바이낸스선물고정레버리지값', 0, en_key),
            '바이낸스선물변동레버리지값': binance_leverage_,
            '바이낸스선물마진타입': _safe_get(df_m, '바이낸스선물마진타입', 0, en_key),
            '바이낸스선물포지션': _safe_get(df_m, '바이낸스선물포지션', 0, en_key),

            # 증권사 계정 (8개)
            **{f'아이디{i}': _safe_get(df_sa, '아이디', i, en_key, decrypt=True) for i in range(1, 9) if df_sa_not_empty},
            **{f'비밀번호{i}': _safe_get(df_sa, '비밀번호', i, en_key, decrypt=True) for i in range(1, 9) if df_sa_not_empty},
            **{f'인증서비밀번호{i}': _safe_get(df_sa, '인증서비밀번호', i, en_key, decrypt=True) for i in range(1, 9) if df_sa_not_empty},
            **{f'계좌비밀번호{i}': _safe_get(df_sa, '계좌비밀번호', i, en_key, decrypt=True) for i in range(1, 9) if df_sa_not_empty},

            # 코인 API 키 (2개)
            **{f'Access_key{i}': _safe_get(df_ca, 'Access_key', i, en_key, decrypt=True) for i in range(1, 3) if df_ca_not_empty},
            **{f'Secret_key{i}': _safe_get(df_ca, 'Secret_key', i, en_key, decrypt=True) for i in range(1, 3) if df_ca_not_empty},

            # 텔레그램 봇 (8개)
            **{f'텔레그램봇토큰{i}': _safe_get(df_t, 'str_bot', i, en_key, decrypt=True) for i in range(1, 9) if df_t_not_empty},
            **{f'텔레그램사용자아이디{i}': int(_safe_get(df_t, 'int_id', i, en_key, decrypt=True)) if _safe_get(df_t, 'int_id', i, en_key, decrypt=True) else None for i in range(1, 9) if df_t_not_empty},

            # 블랙리스트
            '주식블랙리스트': blacklist_stock,
            '해선블랙리스트': blacklist_future,
            '코인블랙리스트': blacklist_coin,

            # 주식 설정
            '주식모의투자': _safe_get(df_s, '주식모의투자', 0, en_key),
            '주식알림소리': _safe_get(df_s, '주식알림소리', 0, en_key),
            '주식매수전략': _safe_get(df_s, '주식매수전략', 0, en_key),
            '주식매도전략': _safe_get(df_s, '주식매도전략', 0, en_key),
            '주식타임프레임': _safe_get(df_s, '주식타임프레임', 0, en_key),
            '주식평균값계산틱수': _safe_get(df_s, '주식평균값계산틱수', 0, en_key),
            '주식최대매수종목수': _safe_get(df_s, '주식최대매수종목수', 0, en_key),
            '주식전략종료시간': _safe_get(df_s, '주식전략종료시간', 0, en_key),
            '주식잔고청산': _safe_get(df_s, '주식잔고청산', 0, en_key),
            '주식프로세스종료': _safe_get(df_s, '주식프로세스종료', 0, en_key),
            '주식컴퓨터종료': _safe_get(df_s, '주식컴퓨터종료', 0, en_key),
            '주식투자금고정': _safe_get(df_s, '주식투자금고정', 0, en_key),
            '주식투자금': _safe_get(df_s, '주식투자금', 0, en_key),
            '주식손실중지': _safe_get(df_s, '주식손실중지', 0, en_key),
            '주식손실중지수익률': _safe_get(df_s, '주식손실중지수익률', 0, en_key),
            '주식수익중지': _safe_get(df_s, '주식수익중지', 0, en_key),
            '주식수익중지수익률': _safe_get(df_s, '주식수익중지수익률', 0, en_key),
            '주식경과틱수설정': _safe_get(df_s, '주식경과틱수설정', 0, en_key),

            # 코인 설정
            '코인모의투자': _safe_get(df_c, '코인모의투자', 0, en_key),
            '코인알림소리': _safe_get(df_c, '코인알림소리', 0, en_key),
            '코인매수전략': _safe_get(df_c, '코인매수전략', 0, en_key),
            '코인매도전략': _safe_get(df_c, '코인매도전략', 0, en_key),
            '코인타임프레임': _safe_get(df_c, '코인타임프레임', 0, en_key),
            '코인평균값계산틱수': _safe_get(df_c, '코인평균값계산틱수', 0, en_key),
            '코인최대매수종목수': _safe_get(df_c, '코인최대매수종목수', 0, en_key),
            '코인전략종료시간': _safe_get(df_c, '코인전략종료시간', 0, en_key),
            '코인잔고청산': _safe_get(df_c, '코인잔고청산', 0, en_key),
            '코인프로세스종료': _safe_get(df_c, '코인프로세스종료', 0, en_key),
            '코인컴퓨터종료': _safe_get(df_c, '코인컴퓨터종료', 0, en_key),
            '코인투자금고정': _safe_get(df_c, '코인투자금고정', 0, en_key),
            '코인투자금': _safe_get(df_c, '코인투자금', 0, en_key),
            '코인손실중지': _safe_get(df_c, '코인손실중지', 0, en_key),
            '코인손실중지수익률': _safe_get(df_c, '코인손실중지수익률', 0, en_key),
            '코인수익중지': _safe_get(df_c, '코인수익중지', 0, en_key),
            '코인수익중지수익률': _safe_get(df_c, '코인수익중지수익률', 0, en_key),
            '코인경과틱수설정': _safe_get(df_c, '코인경과틱수설정', 0, en_key),

            # 백테스트 설정
            '블랙리스트추가': _safe_get(df_b, '블랙리스트추가', 0, en_key),
            '백테주문관리적용': _safe_get(df_b, '백테주문관리적용', 0, en_key),
            '백테매수시간기준': _safe_get(df_b, '백테매수시간기준', 0, en_key),
            '백테일괄로딩': _safe_get(df_b, '백테일괄로딩', 0, en_key),
            '그래프저장하지않기': _safe_get(df_b, '그래프저장하지않기', 0, en_key),
            '그래프띄우지않기': _safe_get(df_b, '그래프띄우지않기', 0, en_key),
            '디비자동관리': _safe_get(df_b, '디비자동관리', 0, en_key),
            '교차검증가중치': _safe_get(df_b, '교차검증가중치', 0, en_key),
            '백테스케쥴실행': _safe_get(df_b, '백테스케쥴실행', 0, en_key),
            '백테스케쥴요일': _safe_get(df_b, '백테스케쥴요일', 0, en_key),
            '백테스케쥴시간': _safe_get(df_b, '백테스케쥴시간', 0, en_key),
            '백테스케쥴구분': _safe_get(df_b, '백테스케쥴구분', 0, en_key),
            '백테스케쥴명': _safe_get(df_b, '백테스케쥴명', 0, en_key),
            '백테날짜고정': _safe_get(df_b, '백테날짜고정', 0, en_key),
            '백테날짜': _safe_get(df_b, '백테날짜', 0, en_key),
            '범위자동관리': _safe_get(df_b, '범위자동관리', 0, en_key),
            '보조지표설정': indicators,
            '최적화기준값제한': _safe_get(df_b, '최적화기준값제한', 0, en_key),
            '백테엔진분류방법': _safe_get(df_b, '백테엔진분류방법', 0, en_key),
            '옵튜나샘플러': _safe_get(df_b, '옵튜나샘플러', 0, en_key),
            '옵튜나고정변수': _safe_get(df_b, '옵튜나고정변수', 0, en_key),
            '옵튜나실행횟수': _safe_get(df_b, '옵튜나실행횟수', 0, en_key),
            '옵튜나자동스탭': _safe_get(df_b, '옵튜나자동스탭', 0, en_key),
            '최적화로그기록안함': _safe_get(df_b, '최적화로그기록안함', 0, en_key),

            # 기타 설정
            '저해상도': _safe_get(df_e, '저해상도', 0, en_key),
            '휴무프로세스종료': _safe_get(df_e, '휴무프로세스종료', 0, en_key),
            '휴무컴퓨터종료': _safe_get(df_e, '휴무컴퓨터종료', 0, en_key),
            '창위치기억': _safe_get(df_e, '창위치기억', 0, en_key),
            '창위치': window_pos,
            '스톰라이브': _safe_get(df_e, '스톰라이브', 0, en_key),
            '프로그램종료': _safe_get(df_e, '프로그램종료', 0, en_key),
            '테마': _safe_get(df_e, '테마', 0, en_key),
            '팩터선택': _safe_get(df_e, '팩터선택', 0, en_key),

            # 주식 매수 주문 설정
            '주식매수주문구분': _safe_get(df_sb, '주식매수주문구분', 0, en_key),
            '주식매수분할횟수': _safe_get(df_sb, '주식매수분할횟수', 0, en_key),
            '주식매수분할방법': _safe_get(df_sb, '주식매수분할방법', 0, en_key),
            '주식매수분할시그널': _safe_get(df_sb, '주식매수분할시그널', 0, en_key),
            '주식매수분할하방': _safe_get(df_sb, '주식매수분할하방', 0, en_key),
            '주식매수분할상방': _safe_get(df_sb, '주식매수분할상방', 0, en_key),
            '주식매수분할하방수익률': _safe_get(df_sb, '주식매수분할하방수익률', 0, en_key),
            '주식매수분할상방수익률': _safe_get(df_sb, '주식매수분할상방수익률', 0, en_key),
            '주식매수분할고정수익률': _safe_get(df_sb, '주식매수분할고정수익률', 0, en_key),
            '주식매수지정가기준가격': _safe_get(df_sb, '주식매수지정가기준가격', 0, en_key),
            '주식매수지정가호가번호': _safe_get(df_sb, '주식매수지정가호가번호', 0, en_key),
            '주식매수시장가잔량범위': _safe_get(df_sb, '주식매수시장가잔량범위', 0, en_key),
            '주식매수취소관심이탈': _safe_get(df_sb, '주식매수취소관심이탈', 0, en_key),
            '주식매수취소매도시그널': _safe_get(df_sb, '주식매수취소매도시그널', 0, en_key),
            '주식매수취소시간': _safe_get(df_sb, '주식매수취소시간', 0, en_key),
            '주식매수취소시간초': _safe_get(df_sb, '주식매수취소시간초', 0, en_key),
            '주식매수금지블랙리스트': _safe_get(df_sb, '주식매수금지블랙리스트', 0, en_key),
            '주식매수금지라운드피겨': _safe_get(df_sb, '주식매수금지라운드피겨', 0, en_key),
            '주식매수금지라운드호가': _safe_get(df_sb, '주식매수금지라운드호가', 0, en_key),
            '주식매수금지손절횟수': _safe_get(df_sb, '주식매수금지손절횟수', 0, en_key),
            '주식매수금지손절횟수값': _safe_get(df_sb, '주식매수금지손절횟수값', 0, en_key),
            '주식매수금지거래횟수': _safe_get(df_sb, '주식매수금지거래횟수', 0, en_key),
            '주식매수금지거래횟수값': _safe_get(df_sb, '주식매수금지거래횟수값', 0, en_key),
            '주식매수금지시간': _safe_get(df_sb, '주식매수금지시간', 0, en_key),
            '주식매수금지시작시간': _safe_get(df_sb, '주식매수금지시작시간', 0, en_key),
            '주식매수금지종료시간': _safe_get(df_sb, '주식매수금지종료시간', 0, en_key),
            '주식매수금지간격': _safe_get(df_sb, '주식매수금지간격', 0, en_key),
            '주식매수금지간격초': _safe_get(df_sb, '주식매수금지간격초', 0, en_key),
            '주식매수금지손절간격': _safe_get(df_sb, '주식매수금지손절간격', 0, en_key),
            '주식매수금지손절간격초': _safe_get(df_sb, '주식매수금지손절간격초', 0, en_key),
            '주식매수정정횟수': _safe_get(df_sb, '주식매수정정횟수', 0, en_key),
            '주식매수정정호가차이': _safe_get(df_sb, '주식매수정정호가차이', 0, en_key),
            '주식매수정정호가': _safe_get(df_sb, '주식매수정정호가', 0, en_key),
            '주식비중조절': _parse_ratios(df_sb, '주식비중조절', 0),

            # 주식 매도 주문 설정
            '주식매도주문구분': _safe_get(df_ss, '주식매도주문구분', 0, en_key),
            '주식매도분할횟수': _safe_get(df_ss, '주식매도분할횟수', 0, en_key),
            '주식매도분할방법': _safe_get(df_ss, '주식매도분할방법', 0, en_key),
            '주식매도분할시그널': _safe_get(df_ss, '주식매도분할시그널', 0, en_key),
            '주식매도분할하방': _safe_get(df_ss, '주식매도분할하방', 0, en_key),
            '주식매도분할상방': _safe_get(df_ss, '주식매도분할상방', 0, en_key),
            '주식매도분할하방수익률': _safe_get(df_ss, '주식매도분할하방수익률', 0, en_key),
            '주식매도분할상방수익률': _safe_get(df_ss, '주식매도분할상방수익률', 0, en_key),
            '주식매도지정가기준가격': _safe_get(df_ss, '주식매도지정가기준가격', 0, en_key),
            '주식매도지정가호가번호': _safe_get(df_ss, '주식매도지정가호가번호', 0, en_key),
            '주식매도시장가잔량범위': _safe_get(df_ss, '주식매도시장가잔량범위', 0, en_key),
            '주식매도취소관심진입': _safe_get(df_ss, '주식매도취소관심진입', 0, en_key),
            '주식매도취소매수시그널': _safe_get(df_ss, '주식매도취소매수시그널', 0, en_key),
            '주식매도취소시간': _safe_get(df_ss, '주식매도취소시간', 0, en_key),
            '주식매도취소시간초': _safe_get(df_ss, '주식매도취소시간초', 0, en_key),
            '주식매도손절수익률청산': _safe_get(df_ss, '주식매도손절수익률청산', 0, en_key),
            '주식매도손절수익률': _safe_get(df_ss, '주식매도손절수익률', 0, en_key),
            '주식매도손절수익금청산': _safe_get(df_ss, '주식매도손절수익금청산', 0, en_key),
            '주식매도손절수익금': _safe_get(df_ss, '주식매도손절수익금', 0, en_key),
            '주식매도금지매수횟수': _safe_get(df_ss, '주식매도금지매수횟수', 0, en_key),
            '주식매도금지매수횟수값': _safe_get(df_ss, '주식매도금지매수횟수값', 0, en_key),
            '주식매도금지라운드피겨': _safe_get(df_ss, '주식매도금지라운드피겨', 0, en_key),
            '주식매도금지라운드호가': _safe_get(df_ss, '주식매도금지라운드호가', 0, en_key),
            '주식매도금지시간': _safe_get(df_ss, '주식매도금지시간', 0, en_key),
            '주식매도금지시작시간': _safe_get(df_ss, '주식매도금지시작시간', 0, en_key),
            '주식매도금지종료시간': _safe_get(df_ss, '주식매도금지종료시간', 0, en_key),
            '주식매도금지간격': _safe_get(df_ss, '주식매도금지간격', 0, en_key),
            '주식매도금지간격초': _safe_get(df_ss, '주식매도금지간격초', 0, en_key),
            '주식매도정정횟수': _safe_get(df_ss, '주식매도정정횟수', 0, en_key),
            '주식매도정정호가차이': _safe_get(df_ss, '주식매도정정호가차이', 0, en_key),
            '주식매도정정호가': _safe_get(df_ss, '주식매도정정호가', 0, en_key),

            # 코인 매수 주문 설정
            '코인매수주문구분': _safe_get(df_cb, '코인매수주문구분', 0, en_key),
            '코인매수분할횟수': _safe_get(df_cb, '코인매수분할횟수', 0, en_key),
            '코인매수분할방법': _safe_get(df_cb, '코인매수분할방법', 0, en_key),
            '코인매수분할시그널': _safe_get(df_cb, '코인매수분할시그널', 0, en_key),
            '코인매수분할하방': _safe_get(df_cb, '코인매수분할하방', 0, en_key),
            '코인매수분할상방': _safe_get(df_cb, '코인매수분할상방', 0, en_key),
            '코인매수분할하방수익률': _safe_get(df_cb, '코인매수분할하방수익률', 0, en_key),
            '코인매수분할상방수익률': _safe_get(df_cb, '코인매수분할상방수익률', 0, en_key),
            '코인매수분할고정수익률': _safe_get(df_cb, '코인매수분할고정수익률', 0, en_key),
            '코인매수지정가기준가격': _safe_get(df_cb, '코인매수지정가기준가격', 0, en_key),
            '코인매수지정가호가번호': _safe_get(df_cb, '코인매수지정가호가번호', 0, en_key),
            '코인매수시장가잔량범위': _safe_get(df_cb, '코인매수시장가잔량범위', 0, en_key),
            '코인매수취소관심이탈': _safe_get(df_cb, '코인매수취소관심이탈', 0, en_key),
            '코인매수취소매도시그널': _safe_get(df_cb, '코인매수취소매도시그널', 0, en_key),
            '코인매수취소시간': _safe_get(df_cb, '코인매수취소시간', 0, en_key),
            '코인매수취소시간초': _safe_get(df_cb, '코인매수취소시간초', 0, en_key),
            '코인매수금지블랙리스트': _safe_get(df_cb, '코인매수금지블랙리스트', 0, en_key),
            '코인매수금지200원이하': _safe_get(df_cb, '코인매수금지200원이하', 0, en_key),
            '코인매수금지손절횟수': _safe_get(df_cb, '코인매수금지손절횟수', 0, en_key),
            '코인매수금지손절횟수값': _safe_get(df_cb, '코인매수금지손절횟수값', 0, en_key),
            '코인매수금지거래횟수': _safe_get(df_cb, '코인매수금지거래횟수', 0, en_key),
            '코인매수금지거래횟수값': _safe_get(df_cb, '코인매수금지거래횟수값', 0, en_key),
            '코인매수금지시간': _safe_get(df_cb, '코인매수금지시간', 0, en_key),
            '코인매수금지시작시간': _safe_get(df_cb, '코인매수금지시작시간', 0, en_key),
            '코인매수금지종료시간': _safe_get(df_cb, '코인매수금지종료시간', 0, en_key),
            '코인매수금지간격': _safe_get(df_cb, '코인매수금지간격', 0, en_key),
            '코인매수금지간격초': _safe_get(df_cb, '코인매수금지간격초', 0, en_key),
            '코인매수금지손절간격': _safe_get(df_cb, '코인매수금지손절간격', 0, en_key),
            '코인매수금지손절간격초': _safe_get(df_cb, '코인매수금지손절간격초', 0, en_key),
            '코인매수정정횟수': _safe_get(df_cb, '코인매수정정횟수', 0, en_key),
            '코인매수정정호가차이': _safe_get(df_cb, '코인매수정정호가차이', 0, en_key),
            '코인매수정정호가': _safe_get(df_cb, '코인매수정정호가', 0, en_key),
            '코인비중조절': _parse_ratios(df_cb, '코인비중조절', 0),

            # 코인 매도 주문 설정
            '코인매도주문구분': _safe_get(df_cs, '코인매도주문구분', 0, en_key),
            '코인매도분할횟수': _safe_get(df_cs, '코인매도분할횟수', 0, en_key),
            '코인매도분할방법': _safe_get(df_cs, '코인매도분할방법', 0, en_key),
            '코인매도분할시그널': _safe_get(df_cs, '코인매도분할시그널', 0, en_key),
            '코인매도분할하방': _safe_get(df_cs, '코인매도분할하방', 0, en_key),
            '코인매도분할상방': _safe_get(df_cs, '코인매도분할상방', 0, en_key),
            '코인매도분할하방수익률': _safe_get(df_cs, '코인매도분할하방수익률', 0, en_key),
            '코인매도분할상방수익률': _safe_get(df_cs, '코인매도분할상방수익률', 0, en_key),
            '코인매도지정가기준가격': _safe_get(df_cs, '코인매도지정가기준가격', 0, en_key),
            '코인매도지정가호가번호': _safe_get(df_cs, '코인매도지정가호가번호', 0, en_key),
            '코인매도시장가잔량범위': _safe_get(df_cs, '코인매도시장가잔량범위', 0, en_key),
            '코인매도취소관심진입': _safe_get(df_cs, '코인매도취소관심진입', 0, en_key),
            '코인매도취소매수시그널': _safe_get(df_cs, '코인매도취소매수시그널', 0, en_key),
            '코인매도취소시간': _safe_get(df_cs, '코인매도취소시간', 0, en_key),
            '코인매도취소시간초': _safe_get(df_cs, '코인매도취소시간초', 0, en_key),
            '코인매도손절수익률청산': _safe_get(df_cs, '코인매도손절수익률청산', 0, en_key),
            '코인매도손절수익률': _safe_get(df_cs, '코인매도손절수익률', 0, en_key),
            '코인매도손절수익금청산': _safe_get(df_cs, '코인매도손절수익금청산', 0, en_key),
            '코인매도손절수익금': _safe_get(df_cs, '코인매도손절수익금', 0, en_key),
            '코인매도금지매수횟수': _safe_get(df_cs, '코인매도금지매수횟수', 0, en_key),
            '코인매도금지매수횟수값': _safe_get(df_cs, '코인매도금지매수횟수값', 0, en_key),
            '코인매도금지시간': _safe_get(df_cs, '코인매도금지시간', 0, en_key),
            '코인매도금지시작시간': _safe_get(df_cs, '코인매도금지시작시간', 0, en_key),
            '코인매도금지종료시간': _safe_get(df_cs, '코인매도금지종료시간', 0, en_key),
            '코인매도금지간격': _safe_get(df_cs, '코인매도금지간격', 0, en_key),
            '코인매도금지간격초': _safe_get(df_cs, '코인매도금지간격초', 0, en_key),
            '코인매도정정횟수': _safe_get(df_cs, '코인매도정정횟수', 0, en_key),
            '코인매도정정호가차이': _safe_get(df_cs, '코인매도정정호가차이', 0, en_key),
            '코인매도정정호가': _safe_get(df_cs, '코인매도정정호가', 0, en_key),

            # 프로파일링 설정 (CLI에서는 비활성화)
            '에이전트프로파일링': False,
            '트레이더프로파일링': False,
            '전략연산프로파일링': False,
            '백테엔진프로파일링': False,
        }

        logger_.info("Settings loaded successfully without Qt")
        return dict_set

    except Exception as e:
        logger_.error(f"Failed to load settings: {e}")
        print_exc()
        raise




def _parse_ratios(df: pd.DataFrame, col: str, idx: int) -> List[float]:
    """비중조절 문자열을 float 리스트로 파싱"""
    try:
        if df is None or len(df) == 0 or col not in df.columns:
            return []
        val = df[col][idx] if idx in df.index else None
        if not val:
            return []
        return [float(x) for x in val.split(';')]
    except Exception as e:
        logger_.warning(f"Failed to parse ratios from {col}: {e}")
        return []
