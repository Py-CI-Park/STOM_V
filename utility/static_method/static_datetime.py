
import datetime
from zoneinfo import ZoneInfo

_now_utc = datetime.datetime.now(datetime.timezone.utc)
_now_cme = _now_utc.astimezone(ZoneInfo('America/Chicago'))
# noinspection PyUnresolvedReferences
CME_GAP = int(_now_cme.dst().total_seconds() - 3600 * 14)
UTC_GAP = 3600 * 9


def now():
    """현재 시간을 반환합니다."""
    return datetime.datetime.now()


def now_utc():
    """UTC 현재 시간을 반환합니다."""
    return timedelta_sec(-UTC_GAP)


def now_cme():
    """CME 현재 시간을 반환합니다."""
    return timedelta_sec(CME_GAP)


def str_ymdhmsf(std_time=None):
    """연월일시분초밀리초 문자열을 반환합니다."""
    return strf_time('%Y%m%d%H%M%S%f', std_time)


def str_ymdhms(std_time=None):
    """연월일시분초 문자열을 반환합니다."""
    return strf_time('%Y%m%d%H%M%S', std_time)


def str_ymdhm(std_time=None):
    """연월일시분 문자열을 반환합니다."""
    return strf_time('%Y%m%d%H%M', std_time)


def str_ymdhms_ios(std_time=None):
    """iOS 형식 연월일시분초 문자열을 반환합니다."""
    return strf_time('%Y-%m-%d %H:%M:%S', std_time)


def str_ymd_ios(std_time=None):
    """iOS 형식 연월일 문자열을 반환합니다."""
    return strf_time('%Y-%m-%d', std_time)


def str_ymdhms_from_timestamp(time_):
    """UTC 연월일시분초 문자열을 반환합니다."""
    return str_ymdhms(from_timestamp(int(time_ / 1000 - UTC_GAP)))


def str_ymd(std_time=None):
    """연월일 문자열을 반환합니다."""
    return strf_time('%Y%m%d', std_time)


def str_hms(std_time=None):
    """시분초 문자열을 반환합니다."""
    return strf_time('%H%M%S', std_time)


def dt_ymdhms_ios(str_time):
    """iOS 형식 연월일시분초를 datetime으로 변환합니다."""
    return datetime.datetime.fromisoformat(str_time)


def dt_ymdhms(str_time):
    """연월일시분초를 datetime으로 변환합니다."""
    str_time = f'{str_time[:4]}-{str_time[4:6]}-{str_time[6:8]} {str_time[8:10]}:{str_time[10:12]}:{str_time[12:14]}'
    return datetime.datetime.fromisoformat(str_time)


def dt_ymdhm(str_time):
    """연월일시분을 datetime으로 변환합니다."""
    str_time = f'{str_time[:4]}-{str_time[4:6]}-{str_time[6:8]} {str_time[8:10]}:{str_time[10:12]}'
    return datetime.datetime.fromisoformat(str_time)


def dt_ymd(str_time):
    """연월일을 datetime으로 변환합니다."""
    str_time = f'{str_time[:4]}-{str_time[4:6]}-{str_time[6:8]}'
    return datetime.datetime.fromisoformat(str_time)


def dt_hms(str_time):
    """시분초를 datetime으로 변환합니다."""
    if len(str_time) < 6: str_time = str_time.zfill(6)
    str_time = f'2000-01-01 {str_time[:2]}:{str_time[2:4]}:{str_time[4:6]}'
    return datetime.datetime.fromisoformat(str_time)


def dt_hm(str_time):
    """시분을 datetime으로 변환합니다."""
    if len(str_time) < 4: str_time = str_time.zfill(4)
    str_time = f'2000-01-01 {str_time[:2]}:{str_time[2:4]}'
    return datetime.datetime.fromisoformat(str_time)


def strf_time(timetype, std_time=None):
    """시간 포맷 문자열을 반환합니다."""
    if std_time is None: std_time = now()
    return std_time.strftime(timetype)


def from_timestamp(time_):
    """타임스탬프를 datetime으로 변환합니다."""
    return datetime.datetime.fromtimestamp(time_)


def timedelta_sec(second, std_time=None):
    """초 단위 timedelta를 반환합니다."""
    if std_time is None: std_time = now()
    return std_time + datetime.timedelta(seconds=float(second))


def timedelta_day(day, std_time=None):
    """일 단위 timedelta를 반환합니다."""
    if std_time is None: std_time = now()
    return std_time + datetime.timedelta(days=float(day))


def get_inthms(market_gubun):
    """시장 구분에 따른 시분초 정수를 반환합니다."""
    if market_gubun < 4 or market_gubun in (6, 7):
        return int(str_hms())
    elif market_gubun in (4, 8):
        return int(str_hms(now_cme()))
    else:
        return int(str_hms(now_utc()))


def get_str_ymdhms(market_gubun):
    """시장 구분에 따른 연월일시분초 문자열을 반환합니다."""
    if market_gubun < 4 or market_gubun in (6, 7):
        return str_ymdhms()
    elif market_gubun in (4, 8):
        return str_ymdhms(now_cme())
    else:
        return str_ymdhms(now_utc())


def get_str_ymdhmsf(market_gubun):
    """시장 구분에 따른 연월일시분초밀리초 문자열을 반환합니다."""
    if market_gubun < 4 or market_gubun in (6, 7):
        return str_ymdhmsf()
    elif market_gubun in (4, 8):
        return str_ymdhmsf(now_cme())
    else:
        return str_ymdhmsf(now_utc())


def cme_normal_open():
    """CME 정규장 오픈 여부를 확인합니다."""
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
