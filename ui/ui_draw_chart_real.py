
from ui.ui_etc import chart_clear
from utility.static import error_decorator
from ui.ui_draw_chart_base import DrawChartBase
from utility.static import from_timestamp, dt_ymdhms
from ui.ui_process_alive import coin_strategy_process_alive, coin_receiver_process_alive


class DrawRealChart(DrawChartBase):
    @error_decorator
    def draw_real_chart(self, data):
        self.real = True
        self.code, self.ui.ctpg_arry = data[1:]

        if 'KRW' in self.code or 'USDT' in self.code:
            self.gubun = 'C'
        elif '키움증권' in self.ui.dict_set['증권사']:
            self.gubun = 'S'
        else:
            self.gubun = 'F'

        if not self.ui.dialog_chart.isVisible():
            chart_clear(self.ui)
            if self.gubun == 'C':
                if coin_strategy_process_alive(self.ui): self.ui.cstgQ.put(('차트종목코드', None))
                if not self.ui.dict_set['코인타임프레임'] and coin_receiver_process_alive(self.ui): self.ui.creceivQ.put(
                    ('차트종목코드', None))
            else:
                self.ui.wdzservQ.put(('strategy', ('차트종목코드', None)))
                if not self.ui.dict_set['주식타임프레임']: self.ui.wdzservQ.put(('agent', ('차트종목코드', None)))
            return

        self.chart_cnt = len(self.ui.ctpg)
        self.is_min = self.chart_cnt in (6, 8) or (self.chart_cnt == 10 and self.ui.ct_pushButtonnn_05.text() == 'CHART III')

        curr_last_index = self.ui.ctpg_arry[-1, 0]
        self.same_code = self.ui.ctpg_code == self.code
        self.same_time = self.last_index == curr_last_index

        if not (self.same_code and self.same_time):
            if self.is_min:
                self.ui.ctpg_xticks = [dt_ymdhms(f'{str(int(x))}00').timestamp() for x in self.ui.ctpg_arry[:, 0]]
            else:
                self.ui.ctpg_xticks = [dt_ymdhms(str(int(x))).timestamp() for x in self.ui.ctpg_arry[:, 0]]
        else:
            if self.is_min:
                self.ui.ctpg_xticks.append(dt_ymdhms(f'{str(int(curr_last_index))}00').timestamp())
            else:
                self.ui.ctpg_xticks.append(dt_ymdhms(str(int(curr_last_index))).timestamp())

        self.last_index = curr_last_index
        self.gsjm_arry = self.ui.ctpg_arry[:, self.fi('관심종목')]
        self.xmin, self.xmax = self.ui.ctpg_xticks[0], self.ui.ctpg_xticks[-1]
        self.hms = from_timestamp(self.xmax).strftime('%H:%M' if self.is_min else '%H:%M:%S')

        self.draw_all_chart()
