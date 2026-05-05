
import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal
from utility.settings.setting_base import UI_NUM


class MonitorWindowQ(QThread):
    """윈도우 큐 모니터 스레드 클래스입니다.
    윈도우 큐의 데이터를 분류하여 전송합니다.
    """
    signal1 = pyqtSignal(tuple)
    signal2 = pyqtSignal(tuple)
    signal3 = pyqtSignal(tuple)
    signal4 = pyqtSignal(tuple)
    signal5 = pyqtSignal(str)

    def __init__(self, windowQ):
        super().__init__()
        self.windowQ = windowQ
        self.df_list = [None, None, None, None, None, None, None, None]

    def run(self):
        """윈도우 큐 모니터 스레드를 실행합니다."""
        gsjm_count = 0
        while True:
            try:
                data = self.windowQ.get()
                if data[0].__class__ != str:
                    if data[0] <= UI_NUM['학습로그']:
                        self.signal1.emit(data)
                    elif UI_NUM['실현손익'] <= data[0] <= UI_NUM['상세기록']:
                        if data[0] == UI_NUM['관심종목']:
                            if len(data) == 3:
                                index = data[1]
                                self.df_list[index] = data[2]
                                gsjm_count += 1
                                if gsjm_count == 8:
                                    gsjm_count = 0
                                    df_list = [x for x in self.df_list if x is not None]
                                    df = pd.concat(df_list)
                                    df.sort_values(by=['dm'], ascending=False, inplace=True)
                                    self.signal2.emit((UI_NUM['관심종목'], df))
                            else:
                                df = data[1]
                                df.sort_values(by=['dm'], ascending=False, inplace=True)
                                self.signal2.emit((UI_NUM['관심종목'], df))
                        else:
                            self.signal2.emit(data)
                    elif data[0] == UI_NUM['차트']:
                        self.signal3.emit(data)
                    elif data[0] == UI_NUM['실시간차트']:
                        self.signal4.emit(data)
                else:
                    self.signal5.emit(data)
            except Exception:
                pass
