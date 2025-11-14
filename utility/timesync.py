import time
import ntplib
import win32api
from dateutil import tz
from datetime import datetime
from utility.static import thread_decorator, get_logger


@thread_decorator
def timesync():
    logger_ = get_logger('TimeSync')
    while True:
        try:
            ntp_client = ntplib.NTPClient()
            response = ntp_client.request('time.windows.com', version=3)
            offset   = response.offset
            if abs(offset) >= 0.05:
                dt = datetime.fromtimestamp(response.tx_time + response.delay - 32400).astimezone(tz.tzlocal())
                win32api.SetSystemTime(
                    dt.year,
                    dt.month,
                    dt.weekday(),
                    dt.day,
                    dt.hour,
                    dt.minute,
                    dt.second,
                    dt.microsecond // 1000
                )
                logger_.info(f'표준시간 동기화 중 ... 현재 표준시간과의 차이는 [{offset:.6f}]초입니다.')
            else:
                logger_.info(f'표준시간 동기화 완 ... 현재 표준시간과의 차이는 [{offset:.6f}]초입니다.')
                break
        except:
            pass
        time.sleep(1)
