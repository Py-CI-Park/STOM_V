
from ui.etcetera.etc import chart_clear
from utility.static_method.static import dt_ymdhms
from ui.draw_chart.draw_chart_base import DrawChartBase
from ui.etcetera.process_alive import strategy_process_alive, receiver_process_alive


class DrawRealChart(DrawChartBase):
    """실시간 차트 그리기 클래스입니다.
    실시간 데이터를 사용하여 차트를 그립니다.
    """
    def draw_real_chart(self, data):
        """실시간 차트를 그립니다.
        Args:
            data: 차트 데이터 튜플
        """
        self.real = True
        self.code, self.ui.ctpg_arry = data[1:]

        if not self.ui.dialog_chart.isVisible():
            chart_clear(self.ui)
            if receiver_process_alive(self.ui):
                self.ui.receivQ.put(('차트종목코드', None))
            if strategy_process_alive(self.ui):
                if self.ui.market_gubun < 5:
                    for q in self.ui.stgQs:
                        q.put(('차트종목코드', None))
                else:
                    self.ui.stgQs[0].put(('차트종목코드', None))
            return

        curr_last_index = self.ui.ctpg_arry[-1, 0]
        self.same_code  = self.ui.ctpg_code == self.code
        self.same_time  = self.last_index == curr_last_index
        self.last_index = curr_last_index

        if self.same_code and self.same_time:
            if self.is_min:
                self.ui.ctpg_xticks.append(dt_ymdhms(f'{str(int(curr_last_index))}00').timestamp())
            else:
                self.ui.ctpg_xticks.append(dt_ymdhms(str(int(curr_last_index))).timestamp())
        else:
            if self.is_min:
                self.ui.ctpg_xticks = [dt_ymdhms(f'{str(int(x))}00').timestamp() for x in self.ui.ctpg_arry[:, 0]]
            else:
                self.ui.ctpg_xticks = [dt_ymdhms(str(int(x))).timestamp() for x in self.ui.ctpg_arry[:, 0]]

        self.draw_all_chart()
