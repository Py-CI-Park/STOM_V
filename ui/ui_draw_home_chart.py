
from utility.static import error_decorator


class DrawHomeChart:
    def __init__(self, ui):
        self.ui = ui
        self.pg_index = {
            '코스피': 0,
            '코스닥': 1,
            '코스피100': 2,
            '코스피200': 3,
            '코스피200선물': 4,
            '환율': 5,
            '휘발유': 6,
            '국제금': 7,
            'BTC/USDT': 8,
            'ETH/USDT': 9,
            'BNB/USDT': 10,
            'XRP/USDT': 11,
            'SOL/USDT': 12,
            'DOGE/USDT': 13,
            'ADA/USDT': 14,
            'LINK/USDT': 15,
        }

    @error_decorator
    def draw_home_chart(self, data):
        for name, df in data[1].items():
            if df is None:
                continue

            pgindex    = self.pg_index[name]
            values     = df.values
            last_price = f'{values[-1, 1]:,}'
            if name in ('코스피', '코스닥', '코스피100', '코스피200', '코스피200선물'):
                last_pct = values[-1, 3]
                pct_text = f"{last_pct:+.2f}%"
                prev_price = values[0, 1] - values[0, 2]
            else:
                last_pct = values[-1, 2]
                pct_text = f"{last_pct:+.2f}%"
                prev_price = values[0, 1]
            pct_color  = 'color: rgb(250, 100, 100);' if last_pct >= 0 else 'color: rgb(100, 100, 250);'

            if name == '코스피':
                self.ui.home_label_001.setText(last_price)
                self.ui.home_label_017.setText(pct_text)
                self.ui.home_label_017.setStyleSheet(pct_color)
            elif name == '코스닥':
                self.ui.home_label_002.setText(last_price)
                self.ui.home_label_018.setText(pct_text)
                self.ui.home_label_018.setStyleSheet(pct_color)
            elif name == '코스피100':
                self.ui.home_label_003.setText(last_price)
                self.ui.home_label_019.setText(pct_text)
                self.ui.home_label_019.setStyleSheet(pct_color)
            elif name == '코스피200':
                self.ui.home_label_004.setText(last_price)
                self.ui.home_label_020.setText(pct_text)
                self.ui.home_label_020.setStyleSheet(pct_color)
            elif name == '코스피200선물':
                self.ui.home_label_005.setText(last_price)
                self.ui.home_label_021.setText(pct_text)
                self.ui.home_label_021.setStyleSheet(pct_color)
            elif name == '환율':
                self.ui.home_label_006.setText(last_price)
                self.ui.home_label_022.setText(pct_text)
                self.ui.home_label_022.setStyleSheet(pct_color)
            elif name == '휘발유':
                self.ui.home_label_007.setText(last_price)
                self.ui.home_label_023.setText(pct_text)
                self.ui.home_label_023.setStyleSheet(pct_color)
            elif name == '국제금':
                self.ui.home_label_008.setText(last_price)
                self.ui.home_label_024.setText(pct_text)
                self.ui.home_label_024.setStyleSheet(pct_color)
            elif name == 'BTC/USDT':
                self.ui.home_label_009.setText(last_price)
                self.ui.home_label_025.setText(pct_text)
                self.ui.home_label_025.setStyleSheet(pct_color)
            elif name == 'ETH/USDT':
                self.ui.home_label_010.setText(last_price)
                self.ui.home_label_026.setText(pct_text)
                self.ui.home_label_026.setStyleSheet(pct_color)
            elif name == 'BNB/USDT':
                self.ui.home_label_011.setText(last_price)
                self.ui.home_label_027.setText(pct_text)
                self.ui.home_label_027.setStyleSheet(pct_color)
            elif name == 'XRP/USDT':
                self.ui.home_label_012.setText(last_price)
                self.ui.home_label_028.setText(pct_text)
                self.ui.home_label_028.setStyleSheet(pct_color)
            elif name == 'SOL/USDT':
                self.ui.home_label_013.setText(last_price)
                self.ui.home_label_029.setText(pct_text)
                self.ui.home_label_029.setStyleSheet(pct_color)
            elif name == 'DOGE/USDT':
                self.ui.home_label_014.setText(last_price)
                self.ui.home_label_030.setText(pct_text)
                self.ui.home_label_030.setStyleSheet(pct_color)
            elif name == 'ADA/USDT':
                self.ui.home_label_015.setText(last_price)
                self.ui.home_label_031.setText(pct_text)
                self.ui.home_label_031.setStyleSheet(pct_color)
            elif name == 'LINK/USDT':
                self.ui.home_label_016.setText(last_price)
                self.ui.home_label_032.setText(pct_text)
                self.ui.home_label_032.setStyleSheet(pct_color)

            self.ui.homepg[pgindex].clear()
            self.ui.homepg[pgindex].showAxis('right', True)
            self.ui.homepg[pgindex].showAxis('bottom', True)

            x_data = values[:, 0]
            y_data = values[:, 1]
            above_mask = y_data >= prev_price

            above_segments = []
            start = None
            for i, is_above in enumerate(above_mask):
                if is_above and start is None:
                    start = i
                elif not is_above and start is not None:
                    above_segments.append((start, i-1))
                    start = None
            if start is not None:
                above_segments.append((start, len(above_mask)-1))

            below_segments = []
            start = None
            below_mask = ~above_mask
            # noinspection PyTypeChecker
            for i, is_below in enumerate(below_mask):
                if is_below and start is None:
                    start = i
                elif not is_below and start is not None:
                    below_segments.append((start, i-1))
                    start = None
            if start is not None:
                # noinspection PyTypeChecker
                below_segments.append((start, len(below_mask)-1))

            for start_idx, end_idx in above_segments:
                segment_x = x_data[start_idx:end_idx+2]
                segment_y = y_data[start_idx:end_idx+2]
                self.ui.homepg[pgindex].plot(x=segment_x, y=segment_y, pen=(250, 100, 100),
                                             fillLevel=prev_price, brush=(250, 100, 100, 80))

            for start_idx, end_idx in below_segments:
                segment_x = x_data[start_idx:end_idx+2]
                segment_y = y_data[start_idx:end_idx+2]
                self.ui.homepg[pgindex].plot(x=segment_x, y=segment_y, pen=(100, 100, 250),
                                             fillLevel=prev_price, brush=(100, 100, 250, 80))
