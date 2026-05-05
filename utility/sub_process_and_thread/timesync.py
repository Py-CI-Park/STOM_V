
import time
import ntplib
import win32api
from dateutil import tz
from datetime import datetime
from utility.static_method.static import thread_decorator


@thread_decorator
def timesync(ui_num, windowQ):
    """시간 동기화를 수행합니다.
    NTP 서버와 시간을 동기화합니다.
    Args:
        ui_num: UI 번호
        windowQ: 윈도우 큐
    """
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
                windowQ.put((ui_num['시스템로그'], f'표준시간 동기화 중 ... 차이 [{offset:.6f}]초'))
            else:
                windowQ.put((ui_num['시스템로그'], f'표준시간 동기화 완료 [{offset:.6f}]초'))
                break
        except Exception:
            pass
        time.sleep(1)
