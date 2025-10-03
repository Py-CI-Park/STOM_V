import datetime
import exchange_calendars as ec


def strf_time(timetype, std_time=None):
    return datetime.datetime.now().strftime(timetype) if std_time is None else std_time.strftime(timetype)


def timedelta_day(day_, std_time=None):
    return datetime.datetime.now() + datetime.timedelta(days=float(day_)) if std_time is None else std_time + datetime.timedelta(days=float(day_))


def dt_ymdhms_ios(str_time):
    return datetime.datetime.fromisoformat(str_time)


start = dt_ymdhms_ios('2025-01-01 17:00:00')
end   = dt_ymdhms_ios('2025-12-31 17:00:00')
today = start
dict_count = {'정상개장': 0, '빠른마감': 0, '휴장': 0}
while True:
    str_day = strf_time('%Y-%m-%d', today)
    ec_cme  = ec.get_calendar('CMES')
    day_list  = ec_cme.sessions_in_range(start=str_day, end=str_day)
    if len(day_list) > 0:
        close_time = ec_cme.session_close(day_list[0]).tz_convert('America/Chicago').time()
        if today.time() == close_time:
            print(f'{str_day} : 정상개장')
            dict_count['정상개장'] += 1
        else:
            print(f'{str_day} : 빠른마감')
            dict_count['빠른마감'] += 1
    else:
        print(f'{str_day} : 휴장')
        dict_count['휴장'] += 1
    today = timedelta_day(1, today)
    if today > end: break

print(dict_count)
