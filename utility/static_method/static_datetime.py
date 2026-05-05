
import datetime


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


def summer_time():
    """서머타임을 계산합니다.
    Returns:
        서머타임 초
    """
    from zoneinfo import ZoneInfo
    now_utc_ = datetime.datetime.now(datetime.timezone.utc)
    now_cme_ = now_utc_.astimezone(ZoneInfo('America/Chicago'))
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
