
import time
import ntplib
import win32api
from dateutil import tz
from datetime import datetime
from utility.static import thread_decorator


@thread_decorator
def timesync(ui_num, windowQ):
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
                windowQ.put((ui_num['시스템로그'], f'Time synchronizing ... diff [{offset:.6f}]seconds'))
            else:
                windowQ.put((ui_num['시스템로그'], f'Time synchronized ... diff [{offset:.6f}]seconds'))
                break
        except:
            pass
        time.sleep(1)
