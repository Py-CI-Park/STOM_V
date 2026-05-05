
import bisect
import datetime
from numba import njit


def set_builtin_print(q):
    """내장 print 함수를 설정합니다.
    UI 큐를 통해 로그를 출력합니다.
    Args:
        q: UI 큐
    """
    import inspect
    import builtins
    from utility.settings.setting_base import ui_num

    # noinspection PyUnusedLocal,PyUnresolvedReferences
    def ui_print(*args, sep=' ', end='\n', file=None):
        try:
            is_direct_print = False
            frame = inspect.currentframe()
            caller_frame = frame.f_back.f_back
            if caller_frame:
                caller_filename = caller_frame.f_code.co_filename
                caller_function = caller_frame.f_code.co_name
                excluded_paths  = ['site-packages', 'numba', 'numpy', 'pandas', 'talib']
                is_excluded     = any(path in caller_filename for path in excluded_paths)
                if not is_excluded and caller_function != '<module>':
                    is_direct_print = True
                elif '__main__' in caller_filename:
                    is_direct_print = True

            if not is_direct_print:
                return

            processed_args = []
            for arg in args:
                if callable(arg):
                    processed_args.append(str(arg()))
                else:
                    processed_args.append(str(arg))

            message = sep.join(processed_args)
            message = message.lstrip()
            message = message.rstrip()

            q.put((ui_num['시스템로그'], message))
        except Exception:
            pass

    builtins.print = ui_print


def get_ema_list(is_tick):
    """EMA 윈도우 리스트를 반환합니다.
    Args:
        is_tick: 틱 데이터 여부
    Returns:
        EMA 윈도우 리스트
    """
    return (60, 150, 300, 600, 1200) if is_tick else (5, 10, 20, 60, 120)


def add_rolling_data(df, round_unit, angle_cf_list, is_tick, avg_list, cf1=None, cf2=None):
    """롤링 데이터를 추가합니다.
    Args:
        df: 데이터프레임
        round_unit: 반올림 단위
        angle_cf_list: 각도 계수 리스트
        is_tick: 틱 데이터 여부
        avg_list: 평균 리스트
        cf1: 계수1
        cf2: 계수2
    Returns:
        배열
    """
    import numpy as np

    for window in get_ema_list(is_tick):
        df[f'이동평균{window}'] = df['현재가'].rolling(window=window).mean().round(round_unit)

    for avg in avg_list:
        rolling_data = df['현재가'].rolling(window=avg)
        df[f'최고현재가{avg}'] = rolling_data.max()
        df[f'최저현재가{avg}'] = rolling_data.min()

        if not is_tick:
            df[f'최고분봉고가{avg}'] = df['분봉고가'].rolling(window=avg).max()
            df[f'최저분봉저가{avg}'] = df['분봉저가'].rolling(window=avg).min()

        rolling_data = df['체결강도'].rolling(window=avg)
        df[f'체결강도평균{avg}'] = rolling_data.mean().round(3)
        df[f'최고체결강도{avg}'] = rolling_data.max()
        df[f'최저체결강도{avg}'] = rolling_data.min()

        if is_tick:
            rolling_data1 = df['초당매수수량'].rolling(window=avg)
            rolling_data2 = df['초당매도수량'].rolling(window=avg)
            df[f'최고초당매수수량{avg}'] = rolling_data1.max()
            df[f'최고초당매도수량{avg}'] = rolling_data2.max()
            df[f'누적초당매수수량{avg}'] = rolling_data1.sum()
            df[f'누적초당매도수량{avg}'] = rolling_data2.sum()
            df[f'초당거래대금평균{avg}'] = df['초당거래대금'].rolling(window=avg).mean().round(0)
        else:
            rolling_data1 = df['분당매수수량'].rolling(window=avg)
            rolling_data2 = df['분당매도수량'].rolling(window=avg)
            df[f'최고분당매수수량{avg}'] = rolling_data1.max()
            df[f'최고분당매도수량{avg}'] = rolling_data2.max()
            df[f'누적분당매수수량{avg}'] = rolling_data1.sum()
            df[f'누적분당매도수량{avg}'] = rolling_data2.sum()
            df[f'분당거래대금평균{avg}'] = df['분당거래대금'].rolling(window=avg).mean().round(0)

        if cf1 is None:
            cf1, cf2 = angle_cf_list

        df2 = df[['등락율', '당일거래대금']].copy()
        df2[f'등락율N{avg}'] = df2['등락율'].shift(avg - 1)
        df2['등락율차이'] = df2['등락율'] - df2[f'등락율N{avg}']
        df2[f'당일거래대금N{avg}'] = df2['당일거래대금'].shift(avg - 1)
        df2['당일거래대금차이'] = df2['당일거래대금'] - df2[f'당일거래대금N{avg}']
        df['등락율각도'] = round(np.arctan2(df2['등락율차이'] * cf1, avg) / (2 * np.pi) * 360, 2)
        df['당일거래대금각도'] = round(np.arctan2(df2['당일거래대금차이'] * cf2, avg) / (2 * np.pi) * 360, 2)

    arry = np.array(df)
    return np.nan_to_num(arry)


def error_decorator(func):
    """에러 처리 데코레이터입니다.
    Args:
        func: 데코레이터를 적용할 함수
    Returns:
        래퍼 함수
    """
    from traceback import format_exc

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            print(format_exc())
            return None
    return wrapper


def thread_decorator(func):
    """스레드 데코레이터입니다.
    Args:
        func: 데코레이터를 적용할 함수
    Returns:
        래퍼 함수
    """
    from threading import Thread

    def wrapper(*args):
        Thread(target=func, args=args, daemon=True).start()
    return wrapper


def get_profile_text(pr):
    """프로파일 텍스트를 가져옵니다.
    Args:
        pr: 프로파일 객체
    Returns:
        프로파일 텍스트
    """
    import io
    import pstats
    output = io.StringIO()
    stats = pstats.Stats(pr, stream=output)
    stats.sort_stats('cumulative')
    stats.print_stats(30)
    result = output.getvalue()
    output.close()
    return result


def get_logger(name):
    """로거를 생성합니다.
    Args:
        name: 로거 이름
    Returns:
        설정된 로거 인스턴스
    """
    import sys
    from loguru import logger
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
               "<level>{level: <5}</level> | "
               f"<cyan>{name}</cyan> : "
               "<level>{message}</level>",
        level="DEBUG",
        colorize=True
    )
    return logger


def summer_time():
    """서머타임을 계산합니다.
    Returns:
        서머타임 초
    """
    import pytz
    now_utc_ = datetime.datetime.now(pytz.utc)
    now_cme_ = now_utc_.astimezone(pytz.timezone('America/Chicago'))
    # noinspection PyUnresolvedReferences
    summer_t = int(now_cme_.dst().total_seconds())
    return summer_t


def get_time_gap():
    """시간 차이를 계산합니다.
    Returns:
        시간 차이 초
    """
    time_gap = int(summer_time() - 50400)
    return time_gap


def now():
    """현재 시간을 반환합니다.
    Returns:
        현재 시간
    """
    return datetime.datetime.now()


def now_utc():
    """UTC 현재 시간을 반환합니다.
    Returns:
        UTC 현재 시간
    """
    return timedelta_sec(-32400)


def now_cme():
    """CME 현재 시간을 반환합니다.
    Returns:
        CME 현재 시간
    """
    return timedelta_sec(get_time_gap())


def str_ymdhmsf(std_time=None):
    """연월일시분초밀리초 문자열을 반환합니다.
    Args:
        std_time: 표준 시간
    Returns:
        연월일시분초밀리초 문자열
    """
    if std_time is not None:
        return strf_time('%Y%m%d%H%M%S%f', std_time)
    else:
        return strf_time('%Y%m%d%H%M%S%f')


def str_ymdhms(std_time=None):
    """연월일시분초 문자열을 반환합니다.
    Args:
        std_time: 표준 시간
    Returns:
        연월일시분초 문자열
    """
    if std_time is not None:
        return strf_time('%Y%m%d%H%M%S', std_time)
    else:
        return strf_time('%Y%m%d%H%M%S')


def str_ymdhm(std_time=None):
    """연월일시분 문자열을 반환합니다.
    Args:
        std_time: 표준 시간
    Returns:
        연월일시분 문자열
    """
    if std_time is not None:
        return strf_time('%Y%m%d%H%M', std_time)
    else:
        return strf_time('%Y%m%d%H%M')


def str_ymdhms_ios(std_time=None):
    """iOS 형식 연월일시분초 문자열을 반환합니다.
    Args:
        std_time: 표준 시간
    Returns:
        iOS 형식 연월일시분초 문자열
    """
    if std_time is not None:
        return strf_time('%Y-%m-%d %H:%M:%S', std_time)
    else:
        return strf_time('%Y-%m-%d %H:%M:%S')


def str_ymdhm_ios(std_time=None):
    """iOS 형식 연월일시분 문자열을 반환합니다.
    Args:
        std_time: 표준 시간
    Returns:
        iOS 형식 연월일시분 문자열
    """
    if std_time is not None:
        return strf_time('%Y-%m-%d %H:%M', std_time)
    else:
        return strf_time('%Y-%m-%d %H:%M')


def str_ymd_ios(std_time=None):
    """iOS 형식 연월일 문자열을 반환합니다.
    Args:
        std_time: 표준 시간
    Returns:
        iOS 형식 연월일 문자열
    """
    if std_time is not None:
        return strf_time('%Y-%m-%d', std_time)
    else:
        return strf_time('%Y-%m-%d')


def str_hms_ios(std_time=None):
    """iOS 형식 시분초 문자열을 반환합니다.
    Args:
        std_time: 표준 시간
    Returns:
        iOS 형식 시분초 문자열
    """
    if std_time is not None:
        return strf_time('%H:%M:%S', std_time)
    else:
        return strf_time('%H:%M:%S')


def str_hm_ios(std_time=None):
    """iOS 형식 시분 문자열을 반환합니다.
    Args:
        std_time: 표준 시간
    Returns:
        iOS 형식 시분 문자열
    """
    if std_time is not None:
        return strf_time('%H:%M', std_time)
    else:
        return strf_time('%H:%M')


def str_ymdhms_utc(time_):
    """UTC 연월일시분초 문자열을 반환합니다.
    Args:
        time_: 시간
    Returns:
        UTC 연월일시분초 문자열
    """
    return str_ymdhms(from_timestamp(int(time_ / 1000 - 32400)))


def str_ymd(std_time=None):
    """연월일 문자열을 반환합니다.
    Args:
        std_time: 표준 시간
    Returns:
        연월일 문자열
    """
    if std_time is not None:
        return strf_time('%Y%m%d', std_time)
    else:
        return strf_time('%Y%m%d')


def str_hmsf(std_time=None):
    """시분초밀리초 문자열을 반환합니다.
    Args:
        std_time: 표준 시간
    Returns:
        시분초밀리초 문자열
    """
    if std_time is not None:
        return strf_time('%H%M%S%f', std_time)
    else:
        return strf_time('%H%M%S%f')


def float_hmsf(std_time=None):
    """시분초밀리초 실수를 반환합니다.
    Args:
        std_time: 표준 시간
    Returns:
        시분초밀리초 실수
    """
    if std_time is not None:
        return float(strf_time('%H%M%S.%f', std_time))
    else:
        return float(strf_time('%H%M%S.%f'))


def str_hms(std_time=None):
    """시분초 문자열을 반환합니다.
    Args:
        std_time: 표준 시간
    Returns:
        시분초 문자열
    """
    if std_time is not None:
        return strf_time('%H%M%S', std_time)
    else:
        return strf_time('%H%M%S')


def str_hms_cme_from_str(std_hms=None):
    """CME 시분초 문자열을 반환합니다.
    Args:
        std_hms: 표준 시분초
    Returns:
        CME 시분초 문자열
    """
    if std_hms is not None:
        std_time = timedelta_sec(get_time_gap(), dt_hms(std_hms))
    else:
        std_time = now_cme()
    return str_hms(std_time)


def str_hm(std_time):
    """시분 문자열을 반환합니다.
    Args:
        std_time: 표준 시간
    Returns:
        시분 문자열
    """
    return strf_time('%H%M', std_time)


def dt_ymdhms_ios(str_time):
    """iOS 형식 연월일시분초를 datetime으로 변환합니다.
    Args:
        str_time: 시간 문자열
    Returns:
        datetime 객체
    """
    return datetime.datetime.fromisoformat(str_time)


def dt_ymdhms(str_time):
    """연월일시분초를 datetime으로 변환합니다.
    Args:
        str_time: 시간 문자열
    Returns:
        datetime 객체
    """
    str_time = f'{str_time[:4]}-{str_time[4:6]}-{str_time[6:8]} {str_time[8:10]}:{str_time[10:12]}:{str_time[12:14]}'
    return datetime.datetime.fromisoformat(str_time)


def dt_ymdhm(str_time):
    """연월일시분을 datetime으로 변환합니다.
    Args:
        str_time: 시간 문자열
    Returns:
        datetime 객체
    """
    str_time = f'{str_time[:4]}-{str_time[4:6]}-{str_time[6:8]} {str_time[8:10]}:{str_time[10:12]}'
    return datetime.datetime.fromisoformat(str_time)


def dt_ymd(str_time):
    """연월일을 datetime으로 변환합니다.
    Args:
        str_time: 시간 문자열
    Returns:
        datetime 객체
    """
    str_time = f'{str_time[:4]}-{str_time[4:6]}-{str_time[6:8]}'
    return datetime.datetime.fromisoformat(str_time)


def dt_hms(str_time):
    """시분초를 datetime으로 변환합니다.
    Args:
        str_time: 시간 문자열
    Returns:
        datetime 객체
    """
    if len(str_time) < 6: str_time = str_time.zfill(6)
    str_time = f'2000-01-01 {str_time[:2]}:{str_time[2:4]}:{str_time[4:6]}'
    return datetime.datetime.fromisoformat(str_time)


def dt_hm(str_time):
    """시분을 datetime으로 변환합니다.
    Args:
        str_time: 시간 문자열
    Returns:
        datetime 객체
    """
    if len(str_time) < 4: str_time = str_time.zfill(4)
    str_time = f'2000-01-01 {str_time[:2]}:{str_time[2:4]}'
    return datetime.datetime.fromisoformat(str_time)


def strf_time(timetype, std_time=None):
    """시간 포맷 문자열을 반환합니다.
    Args:
        timetype: 시간 형식
        std_time: 표준 시간
    Returns:
        포맷된 시간 문자열
    """
    return now().strftime(timetype) if std_time is None else std_time.strftime(timetype)


def from_timestamp(time_):
    """타임스탬프를 datetime으로 변환합니다.
    Args:
        time_: 타임스탬프
    Returns:
        datetime 객체
    """
    return datetime.datetime.fromtimestamp(time_)


def timedelta_sec(second, std_time=None):
    """초 단위 timedelta를 반환합니다.
    Args:
        second: 초
        std_time: 표준 시간
    Returns:
        datetime 객체
    """
    return now() + datetime.timedelta(seconds=float(second)) if std_time is None else std_time + datetime.timedelta(seconds=float(second))


def timedelta_day(day, std_time=None):
    """일 단위 timedelta를 반환합니다.
    Args:
        day: 일
        std_time: 표준 시간
    Returns:
        datetime 객체
    """
    return now() + datetime.timedelta(days=float(day)) if std_time is None else std_time + datetime.timedelta(days=float(day))


def get_inthms(market_gubun):
    """시장 구분에 따른 시분초 정수를 반환합니다.
    Args:
        market_gubun: 시장 구분
    Returns:
        시분초 정수
    """
    if market_gubun < 4 or market_gubun in (6, 7):
        return int(str_hms())
    elif market_gubun in (4, 8):
        return int(str_hms(now_cme()))
    else:
        return int(str_hms(now_utc()))


def get_str_ymdhms(market_gubun):
    """시장 구분에 따른 연월일시분초 문자열을 반환합니다.
    Args:
        market_gubun: 시장 구분
    Returns:
        연월일시분초 문자열
    """
    if market_gubun < 4 or market_gubun in (6, 7):
        return str_ymdhms()
    elif market_gubun in (4, 8):
        return str_ymdhms(now_cme())
    else:
        return str_ymdhms(now_utc())


def get_str_ymdhmsf(market_gubun):
    """시장 구분에 따른 연월일시분초밀리초 문자열을 반환합니다.
    Args:
        market_gubun: 시장 구분
    Returns:
        연월일시분초밀리초 문자열
    """
    if market_gubun < 4 or market_gubun in (6, 7):
        return str_ymdhmsf()
    elif market_gubun in (4, 8):
        return str_ymdhmsf(now_cme())
    else:
        return str_ymdhmsf(now_utc())


def threading_timer(sec, func, args=None):
    """스레드 타이머를 설정합니다.
    Args:
        sec: 초
        func: 실행할 함수
        args: 함수 인자
    """
    from threading import Timer
    if args is None:
        Timer(float(sec), func).start()
    else:
        Timer(float(sec), func, args=[args]).start()


def win_proc_alive(name):
    """윈도우 프로세스가 살아있는지 확인합니다.
    Args:
        name: 프로세스 이름
    Returns:
        프로세스 생존 여부
    """
    import psutil
    alive = False
    for proc in psutil.process_iter():
        if name in proc.name():
            alive = True
    return alive


def opstarter_kill():
    """opstarter, nfstarter 프로세스를 종료합니다."""
    import subprocess
    if win_proc_alive('opstarter'):
        subprocess.run('C:/Windows/System32/taskkill /f /im opstarter.exe',
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL,
                       shell=True)
    if win_proc_alive('nfstarter'):
        subprocess.run('C:/Windows/System32/taskkill /f /im nfstarter.exe',
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL,
                       shell=True)


def pickle_write(file, data):
    """데이터를 피클 파일로 저장합니다.
    Args:
        file: 파일 이름
        data: 저장할 데이터
    """
    import _pickle
    with open(f'{file}.pkl', "wb") as f:
        _pickle.dump(data, f, protocol=-1)


def pickle_read(file):
    """피클 파일에서 데이터를 읽습니다.
    Args:
        file: 파일 이름
    Returns:
        읽은 데이터
    """
    import os
    import _pickle
    data = None
    if os.path.isfile(f'{file}.pkl'):
        with open(f'{file}.pkl', "rb") as f:
            data = _pickle.load(f)
    return data


def qtest_qwait(sec):
    """Qt 테스트 대기 시간을 설정합니다.
    Args:
        sec: 초
    """
    from PyQt5.QtTest import QTest
    # noinspection PyArgumentList
    QTest.qWait(int(sec * 1000))


def change_format(text, float_point=2):
    """텍스트 포맷을 변경합니다.
    Args:
        text: 텍스트
        float_point: 소수점 자리수
    Returns:
        포맷된 텍스트
    """
    text = str(text)
    try:
        format_data = f'{int(text):,}'
    except Exception:
        format_data = f'{float(text):,.{float_point}f}'
    return format_data


def floor_down(float_, decimal_point):
    """소수점 아래로 내림합니다.
    Args:
        float_: 실수
        decimal_point: 소수점
    Returns:
        내림된 실수
    """
    float_ = int(float_ * (1 / decimal_point))
    float_ = float_ * decimal_point
    return float_


def comma2int(t):
    """콤마가 포함된 문자열을 정수로 변환합니다.
    Args:
        t: 문자열
    Returns:
        정수
    """
    if '.' in t: t = t.split('.')[0]
    if ':' in t: t = t.replace(':', '')
    if ' ' in t: t = t.replace(' ', '')
    if ',' in t: t = t.replace(',', '')
    return int(t)


def comma2float(t):
    """콤마가 포함된 문자열을 실수로 변환합니다.
    Args:
        t: 문자열
    Returns:
        실수
    """
    if ' ' in t: t = t.replace(' ', '')
    if ',' in t: t = t.replace(',', '')
    return float(t)


def write_key():
    """암호화 키를 레지스트리에 저장합니다."""
    import winreg as reg
    from cryptography.fernet import Fernet
    key = str(Fernet.generate_key(), 'utf-8')
    reg.CreateKey(reg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\STOM')
    reg.CreateKey(reg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\STOM\EN_KEY')
    openkey = reg.OpenKey(reg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\STOM\EN_KEY', 0, reg.KEY_ALL_ACCESS)
    reg.SetValueEx(openkey, 'EN_KEY', 0, reg.REG_SZ, key)
    reg.CloseKey(openkey)


def read_key():
    """레지스트리에서 암호화 키를 읽습니다.
    Returns:
        암호화 키
    """
    import winreg as reg
    openkey = reg.OpenKey(reg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\STOM\EN_KEY', 0, reg.KEY_ALL_ACCESS)
    key, _ = reg.QueryValueEx(openkey, 'EN_KEY')
    reg.CloseKey(openkey)
    return key


def en_text(key, text):
    """텍스트를 암호화합니다.
    Args:
        key: 암호화 키
        text: 암호화할 텍스트
    Returns:
        암호화된 텍스트
    """
    from cryptography.fernet import Fernet
    fernet = Fernet(bytes(key, 'utf-8'))
    return str(fernet.encrypt(bytes(text, 'utf-8')), 'utf-8')


def de_text(key, text):
    """텍스트를 복호화합니다.
    Args:
        key: 암호화 키
        text: 복호화할 텍스트
    Returns:
        복호화된 텍스트
    """
    from cryptography.fernet import Fernet
    fernet = Fernet(bytes(key, 'utf-8'))
    return str(fernet.decrypt(bytes(text, 'utf-8')), 'utf-8')


def factorial(x):
    """팩토리얼을 계산합니다.
    Args:
        x: 숫자
    Returns:
        팩토리얼 값
    """
    if x <= 1: return 1
    result  = 1
    current = 2
    while current <= x:
        result *= current
        current += 1
    return result


def text_not_in_special_characters(t):
    """특수 문자가 포함되지 않았는지 확인합니다.
    Args:
        t: 텍스트
    Returns:
        특수 문자 포함 여부
    """
    import re
    t = t.replace(' ', '')
    if t == re.findall(r'\w+', t)[0]:
        return True
    return False


def cme_normal_open():
    """CME 정규장 오픈 여부를 확인합니다.
    Returns:
        정규장 오픈 여부
    """
    import exchange_calendars as ec
    str_day  = str_ymd(now_cme())
    today    = dt_ymdhms_ios(f'{str_day} 17:00:00')
    ec_cme   = ec.get_calendar('CMES')
    day_list = ec_cme.sessions_in_range(start=str_day, end=str_day)
    if len(day_list) > 0:
        close_time = ec_cme.session_close(day_list[0]).tz_convert('America/Chicago').time()
        if today.time() != close_time:
            return False
    else:
        return False
    return True


_UPBIT_HOGA_KEYS = (0.01, 1, 10, 100, 1000, 10000, 100000, 500000, 1000000, 2000000, float('inf'))
_UPBIT_HOGA_VALS = (0.0001, 0.001, 0.01, 0.1, 1, 5, 10, 50, 100, 500, 1000)


def get_hogaunit_coin(price):
    """코인 호가 단위를 반환합니다.
    Args:
        price: 가격
    Returns:
        호가 단위
    """
    idx = bisect.bisect_right(_UPBIT_HOGA_KEYS, price)
    return _UPBIT_HOGA_VALS[idx]


_HOGA_NEW_KEYS = (2000, 5000, 20000, 50000, 200000, 500000, float('inf'))
_HOGA_NEW_VALS = (1, 5, 10, 50, 100, 500, 1000)


def get_hogaunit_stock(price):
    """주식 호가 단위를 반환합니다.
    Args:
        price: 가격
    Returns:
        호가 단위
    """
    idx = bisect.bisect_right(_HOGA_NEW_KEYS, price)
    return _HOGA_NEW_VALS[idx]


@njit(cache=True)
def get_profit_stock(bg, cg, etfn=False):
    """주식 수익을 계산합니다.
    Args:
        bg: 매수 금액
        cg: 매도 금액
        etfn: etf, etn
    Returns:
        (수익금, 수익금액, 수익률)
    """
    fee = 0.00015 if not etfn else 0.00005
    texs = int(cg * 0.0018)
    bfee = int(bg * fee / 10) * 10
    sfee = int(cg * fee / 10) * 10
    pg = int(cg - texs - bfee - sfee + 0.5)
    sg = int(pg - bg + 0.5)
    sp = round(sg / bg * 100, 2)
    return pg, sg, sp


@njit(cache=True)
def get_profit_stock_os(bg, cg):
    """해외 주식 수익을 계산합니다.
    Args:
        bg: 매수 금액
        cg: 매도 금액
    Returns:
        (수익금, 수익금액, 수익률)
    """
    texs = int(cg * 0.000008)
    bfee = int(bg * 0.00065 / 10) * 10
    sfee = int(cg * 0.00065 / 10) * 10
    pg = int(cg - texs - bfee - sfee + 0.5)
    sg = int(pg - bg + 0.5)
    sp = round(sg / bg * 100, 2)
    return pg, sg, sp


@njit(cache=True)
def get_profit_future_long(bg, cg):
    """선물 롱 수익을 계산합니다.
    Args:
        bg: 매수 금액
        cg: 매도 금액
    Returns:
        (수익금, 수익금액, 수익률)
    """
    fee = 0.00002
    pg = round(cg - fee * 2, 1)
    sg = round(pg - bg, 1)
    sp = round(sg / bg * 100, 2)
    return pg, sg, sp


@njit(cache=True)
def get_profit_future_short(bg, cg):
    """선물 숏 수익을 계산합니다.
    Args:
        bg: 매수 금액
        cg: 매도 금액
    Returns:
        (수익금, 수익금액, 수익률)
    """
    fee = 0.00002
    pg = round(bg + bg - cg - fee * 2, 1)
    sg = round(pg - bg, 1)
    sp = round(sg / bg * 100, 2)
    return pg, sg, sp


@njit(cache=True)
def get_profit_future_os_long(mini, bg, cg):
    """해외 선물 롱 수익을 계산합니다.
    Args:
        mini: 미니선물
        bg: 매수 금액
        cg: 매도 금액
    Returns:
        (수익금, 수익금액, 수익률)
    """
    fee = 2 if mini else 7.5
    pg = round(cg - fee * 2, 1)
    sg = round(pg - bg, 1)
    sp = round(sg / bg * 100, 2)
    return pg, sg, sp


@njit(cache=True)
def get_profit_future_os_short(mini, bg, cg):
    """해외 선물 숏 수익을 계산합니다.
    Args:
        mini: 미니선물
        bg: 매수 금액
        cg: 매도 금액
    Returns:
        (수익금, 수익금액, 수익률)
    """
    fee = 2 if mini else 7.5
    pg = round(bg + bg - cg - fee * 2, 1)
    sg = round(pg - bg, 1)
    sp = round(sg / bg * 100, 2)
    return pg, sg, sp


@njit(cache=True)
def get_profit_coin(bg, cg):
    """코인 수익을 계산합니다.
    Args:
        bg: 매수 금액
        cg: 매도 금액
    Returns:
        (수익금, 수익금액, 수익률)
    """
    bfee = bg * 0.0005
    sfee = cg * 0.0005
    pg = round(cg - bfee - sfee, 4)
    sg = round(pg - bg, 4)
    sp = round(sg / bg * 100, 2)
    return pg, sg, sp


@njit(cache=True)
def get_profit_coin_future_long(bg, cg, market1, market2):
    """코인 선물 롱 수익을 계산합니다.
    Args:
        bg: 매수 금액
        cg: 매도 금액
        market1: 시장1
        market2: 시장2
    Returns:
        (수익금, 수익금액, 수익률)
    """
    bfee = bg * (0.0004 if market1 else 0.0002)
    sfee = (cg - bfee) * (0.0004 if market2 else 0.0002)
    pg = round(cg - bfee - sfee, 4)
    sg = round(pg - bg, 4)
    sp = round(sg / bg * 100, 2)
    return pg, sg, sp


@njit(cache=True)
def get_profit_coin_future_short(bg, cg, market1, market2):
    """코인 선물 숏 수익을 계산합니다.
    Args:
        bg: 매수 금액
        cg: 매도 금액
        market1: 시장1
        market2: 시장2
    Returns:
        (수익금, 수익금액, 수익률)
    """
    bfee = bg * (0.0004 if market1 else 0.0002)
    sfee = (cg - bfee) * (0.0004 if market2 else 0.0002)
    pg = round(bg + bg - cg - bfee - sfee, 4)
    sg = round(pg - bg, 4)
    sp = round(sg / bg * 100, 2)
    return pg, sg, sp


def get_vi_price(std_price):
    """VI 가격을 계산합니다.
    Args:
        std_price: 기준 가격
    Returns:
        (상단 VI, 하단 VI, 호가 단위)
    """
    uvi = int(std_price * 1.1)
    x = get_hogaunit_stock(uvi)
    if uvi % x != 0:
        uvi += x - uvi % x
    dvi = int(std_price * 0.9)
    y = get_hogaunit_stock(dvi)
    if dvi % y != 0:
        dvi -= dvi % y
    return int(uvi), int(dvi), int(x)


def get_limit_price(predayclose):
    """상한가 하한가를 계산합니다.
    Args:
        predayclose: 전일 종가
    Returns:
        (상한가, 하한가)
    """
    uplimitprice = int(predayclose * 1.30)
    x = get_hogaunit_stock(uplimitprice)
    if uplimitprice % x != 0:
        uplimitprice -= uplimitprice % x
    downlimitprice = int(predayclose * 0.70)
    x = get_hogaunit_stock(downlimitprice)
    if downlimitprice % x != 0:
        downlimitprice += x - downlimitprice % x
    return int(uplimitprice), int(downlimitprice)


def get_indicator(mc, mh, ml, mv, k):
    """지표를 계산합니다.
    Args:
        mc: 현재가
        mh: 고가
        ml: 저가
        mv: 거래량
        k: 파라미터 리스트
    Returns:
        지표 리스트
    """
    from talib import stream
    AD, ADOSC, ADXR, APO, AROOND, AROONU, ATR, BBU, BBM, BBL, CCI, DIM, DIP, MACD, MACDS, MACDH, MFI, MOM, OBV, PPO, \
        ROC, RSI, SAR, STOCHSK, STOCHSD, STOCHFK, STOCHFD, WILLR = \
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    try:    AD                     = stream.AD(      mh, ml, mc, mv)
    except Exception: AD                     = 0
    if k[0] != 0:
        try:    ADOSC              = stream.ADOSC(   mh, ml, mc, mv, fastperiod=k[0], slowperiod=k[1])
        except Exception: ADOSC              = 0
    if k[2] != 0:
        try:    ADXR               = stream.ADXR(    mh, ml, mc,     timeperiod=k[2])
        except Exception: ADXR               = 0
    if k[3] != 0:
        try:    APO                = stream.APO(     mc,             fastperiod=k[3], slowperiod=k[4], matype=k[5])
        except Exception: APO                = 0
    if k[6] != 0:
        try:    AROOND, AROONU     = stream.AROON(   mh, ml,         timeperiod=k[6])
        except Exception: AROOND, AROONU     = 0, 0
    if k[7] != 0:
        try:    ATR                = stream.ATR(     mh, ml, mc,     timeperiod=k[7])
        except Exception: ATR                = 0
    if k[8] != 0:
        try:    BBU, BBM, BBL      = stream.BBANDS(  mc,             timeperiod=k[8], nbdevup=k[9], nbdevdn=k[10], matype=k[11])
        except Exception: BBU, BBM, BBL      = 0, 0, 0
    if k[12] != 0:
        try:    CCI                = stream.CCI(     mh, ml, mc,     timeperiod=k[12])
        except Exception: CCI                = 0
    if k[13] != 0:
        try:    DIM, DIP           = stream.MINUS_DI(mh, ml, mc,     timeperiod=k[13]), stream.PLUS_DI( mh, ml, mc, timeperiod=k[13])
        except Exception: DIM, DIP           = 0, 0
    if k[14] != 0:
        try:    MACD, MACDS, MACDH = stream.MACD(    mc,             fastperiod=k[14], slowperiod=k[15], signalperiod=k[16])
        except Exception: MACD, MACDS, MACDH = 0, 0, 0
    if k[17] != 0:
        try:    MFI                = stream.MFI(     mh, ml, mc, mv, timeperiod=k[17])
        except Exception: MFI                = 0
    if k[18] != 0:
        try:    MOM                = stream.MOM(     mc,             timeperiod=k[18])
        except Exception: MOM                = 0
    try:    OBV                    = stream.OBV(     mc, mv)
    except Exception: OBV                    = 0
    if k[19] != 0:
        try:    PPO                = stream.PPO(     mc,             fastperiod=k[19], slowperiod=k[20], matype=k[21])
        except Exception: PPO                = 0
    if k[22] != 0:
        try:    ROC                = stream.ROC(     mc,             timeperiod=k[22])
        except Exception: ROC                = 0
    if k[23] != 0:
        try:    RSI                = stream.RSI(     mc,             timeperiod=k[23])
        except Exception: RSI                = 0
    if k[24] != 0:
        try:    SAR                = stream.SAR(     mh, ml,         acceleration=k[24], maximum=k[25])
        except Exception: SAR                = 0
    if k[26] != 0:
        try:    STOCHSK, STOCHSD   = stream.STOCH(   mh, ml, mc,     fastk_period=k[26], slowk_period=k[27], slowk_matype=k[28], slowd_period=k[29], slowd_matype=k[30])
        except Exception: STOCHSK, STOCHSD   = 0, 0
    if k[31] != 0:
        try:    STOCHFK, STOCHFD   = stream.STOCHF(  mh, ml, mc,     fastk_period=k[31], fastd_period=k[32], fastd_matype=k[33])
        except Exception: STOCHFK, STOCHFD   = 0, 0
    if k[34] != 0:
        try:    WILLR              = stream.WILLR(   mh, ml, mc,     timeperiod=k[34])
        except Exception: WILLR              = 0
    return [AD, ADOSC, ADXR, APO, AROOND, AROONU, ATR, BBU, BBM, BBL, CCI, DIM, DIP, MACD, MACDS, MACDH, MFI, MOM, OBV, PPO, ROC, RSI, SAR, STOCHSK, STOCHSD, STOCHFK, STOCHFD, WILLR]
