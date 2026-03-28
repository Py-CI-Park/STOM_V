"""
실시간 HHLL 차트 (RealtimeHHLLChart)

이 모듈은 실시간 가격 데이터와 여러 이동평균선을 시각화합니다:
- PyQt5 기반의 고성능 실시간 차트
- 현재가, 60이동평균, 60최고가/최저가 표시
- 직전 60최고가/최저가 비교 표시
- 대용량 데이터 처리를 위한 deque 사용
- 일자별 데이터 자동 초기화

표시되는 선:
- 현재가 (녹색)
- 60이동평균 (파란색)
- 60최고가 (빨간색)
- 직전 60최고가 (스카이블루)
- 60최저가 (블루)
- 직전 60최저가 (스카이블루)
"""

import sys
import sqlite3
import pyqtgraph as pg
from collections import deque
from PyQt5.QtGui import QFont
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from utility.lazy_imports import get_np, get_pd


class RealtimeHHLLCalculator:
    """실시간 이동평균 계산기 클래스"""

    def __init__(self, window_size=60):
        """
        실시간 이동평균 계산기 초기화

        Args:
            window_size: 이동평균 윈도우 크기 (기본 30)
        """
        self.window_size = window_size

        # 데이터 저장
        self.price_data = deque(maxlen=window_size)

    def calculate_sma(self, data=None):
        """
        단순 이동평균 계산

        Args:
            data: 데이터 배열 (None이면 내부 데이터 사용)

        Returns:
            float: SMA 값 또는 None
        """
        if data is None:
            data = list(self.price_data)
        if len(data) < self.window_size:
            return None
        data = list(self.price_data)[-self.window_size:]
        return sum(data) / len(data)

    def calculate_rolling_high(self, data=None):
        """
        롤링 최고가 계산

        Args:
            data: 데이터 배열 (None이면 내부 데이터 사용)

        Returns:
            float: 롤링 최고가 또는 None
        """
        if data is None:
            data = list(self.price_data)
        if len(data) < self.window_size:
            return None
        data = list(self.price_data)[-self.window_size:]
        return max(data)

    def calculate_rolling_low(self, data=None):
        """
        롤링 최저가 계산

        Args:
            data: 데이터 배열 (None이면 내부 데이터 사용)

        Returns:
            float: 롤링 최저가 또는 None
        """
        if data is None:
            data = list(self.price_data)
        if len(data) < self.window_size:
            return None
        data = list(self.price_data)[-self.window_size:]
        return min(data)

    def add_price(self, price):
        """새로운 가격 데이터 추가"""
        self.price_data.append(price)


class RealtimeHHLLChart(QMainWindow):
    def __init__(self, twoway=False, window_size=60, lowhighpct=2, max_points=1800):
        super().__init__()
        self.twoway     = twoway
        self.lowhighpct = lowhighpct
        self.max_points = max_points

        # 계산기
        self.ma_calculator = RealtimeHHLLCalculator(window_size=window_size)

        # 데이터 저장용 deque (속도 우선)
        self.prices     = deque(maxlen=max_points)
        self.timestamps = deque(maxlen=max_points)

        # 데이터
        self.sma               = deque(maxlen=max_points)   # 이동평균
        self.rolling_high      = deque(maxlen=max_points)   # 최고가
        self.rolling_low       = deque(maxlen=max_points)   # 최저가
        self.prev_rolling_high = deque(maxlen=max_points)   # 직전 최고가
        self.prev_rolling_low  = deque(maxlen=max_points)   # 직전 최저가
        self.trade_data        = deque(maxlen=max_points)   # 신호 저장

        self.first        = True
        self.first_draw   = True
        self.chuse_item   = []
        self.draw_items   = {}
        self.upper_bounds = []
        self.lower_bounds = []

        # 실시간 데이터 생성용 변수
        self.all_data      = None
        self.current_index = 0

        # 종목 정보
        self.code          = None
        self.current_price = None
        self.timestamp     = None
        self.current_date  = None
        self.change_rate   = None

        # UI 컴포넌트
        self.price_plot    = None
        self.info_label    = None
        self.trade_state   = None

        # UI 초기화
        self.init_ui()

        # 데이터 로드
        self.load_sample_data()

        # 타이머 설정 (200ms 간격)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(200)

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle('실시간 이동평균 차트 (PyQt5)')
        self.setGeometry(100, 100, 1500, 1000)

        # 메인 위젯 및 레이아웃
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setStyleSheet("background-color: black;")  # 메인 배경 검은색
        main_layout = QVBoxLayout(central_widget)

        # 정보 라벨
        self.info_label = QLabel()
        self.info_label.setFont(QFont("Malgun Gothic", 10))
        self.info_label.setStyleSheet("background-color: #333333; color: white; padding: 10px; border-radius: 5px; border: 1px solid #555555;")
        main_layout.addWidget(self.info_label)

        # 그래프: 가격과 이동평균선
        self.price_plot = pg.PlotWidget(title="HH, PHH, LL, PLL 실시간 차트")
        self.price_plot.setLabel('left', '가격')
        self.price_plot.setLabel('bottom', '시간')
        self.price_plot.showGrid(x=True, y=True, alpha=0.3)
        self.price_plot.setBackground('k')  # 검은색 배경
        self.price_plot.addLegend()  # 범례 추가

        # 그래프 추가
        main_layout.addWidget(self.price_plot)

        # 그래프 스타일 설정
        self.setup_plot_styles()

    def setup_plot_styles(self):
        """그래프 스타일 설정"""
        # 한글 폰트 설정
        font = QFont("Malgun Gothic", 9)

        # 그래프 폰트 설정
        self.price_plot.getAxis('left').setStyle(tickFont=font)
        self.price_plot.getAxis('bottom').setStyle(tickFont=font)

    def add_data(self, price, timestamp):
        """새로운 데이터 추가"""
        self.prices.append(price)
        self.timestamps.append(timestamp)

        # 이동평균 계산기에 가격 추가
        self.ma_calculator.add_price(price)

        # 각종 이동평균 계산
        sma = self.ma_calculator.calculate_sma()
        rolling_high = self.ma_calculator.calculate_rolling_high()
        rolling_low = self.ma_calculator.calculate_rolling_low()

        # 데이터 저장 (None이면 현재가로 대체)
        self.sma.append(sma if sma is not None else price)
        self.rolling_high.append(rolling_high if rolling_high is not None else price)
        self.rolling_low.append(rolling_low if rolling_low is not None else price)
        if rolling_high is not None:
            list_rolling_high = list(self.rolling_high)
            list_rolling_low  = list(self.rolling_low)
            prev_rolling_high = list_rolling_high[-2] if not self.first else list_rolling_high[-1]
            prev_rolling_low  = list_rolling_low[-2] if not self.first else list_rolling_low[-1]
            if not self.first and prev_rolling_high == rolling_high:
                prev_rolling_high = list(self.prev_rolling_high)[-1]
            if not self.first and prev_rolling_low == rolling_low:
                prev_rolling_low = list(self.prev_rolling_low)[-1]
            if self.first: self.first = False
        else:
            prev_rolling_high = price
            prev_rolling_low = price

        trade_state = None
        if rolling_high is not None:
            상승추세 = rolling_high > prev_rolling_high and rolling_low > prev_rolling_low
            하락추세 = rolling_high < prev_rolling_high and rolling_low < prev_rolling_low
            if self.trade_state is None and 상승추세 and price == rolling_high and \
                    (rolling_high / rolling_low - 1) * 100 >= self.lowhighpct:
                trade_state = 'BUY'
                self.trade_state = 'BUY'
            elif self.trade_state == 'BUY' and price == rolling_low:
                trade_state = 'SELL'
                self.trade_state = None
            elif self.twoway and self.trade_state is None and 하락추세 and price == rolling_low and \
                    (rolling_high / rolling_low - 1) * 100 >= self.lowhighpct:
                trade_state = 'SELL'
                self.trade_state = 'SELL'
            elif self.twoway and self.trade_state == 'SELL' and price == rolling_high:
                trade_state = 'BUY'
                self.trade_state = None

        # 상단: 최고가와 직전최고가 중 높은 값
        self.upper_bounds.append(max(self.rolling_high[-1], prev_rolling_high))
        # 하단: 최저가와 직전최저가 중 낮은 값
        self.lower_bounds.append(min(self.rolling_low[-1], prev_rolling_low))
        if len(self.upper_bounds) > 1 and len(self.lower_bounds) > 1:
            # 구간별 색상 결정 및 영역 채우기
            if self.rolling_high[-1] > prev_rolling_high and self.rolling_low[-1] > prev_rolling_low:
                # 옅은 빨간색 (상승 채널)
                brush_color = (255, 100, 100, 50)  # RGBA
            elif self.rolling_high[-1] < prev_rolling_high and self.rolling_low[-1] < prev_rolling_low:
                # 옅은 파란색 (하락 채널)
                brush_color = (100, 100, 255, 50)  # RGBA
            else:
                # 옅은 회색 (횡보)
                brush_color = (150, 150, 150, 50)  # RGBA

            # FillBetweenItem으로 영역 채우기
            curve_upper = pg.PlotDataItem(x=[self.current_index - 1, self.current_index],
                                          y=[self.upper_bounds[self.current_index - 1], self.upper_bounds[self.current_index]])
            curve_lower = pg.PlotDataItem(x=[self.current_index - 1, self.current_index],
                                          y=[self.lower_bounds[self.current_index - 1], self.lower_bounds[self.current_index]])
            fill_item = pg.FillBetweenItem(curve_upper, curve_lower, brush=brush_color)
            self.chuse_item.append(fill_item)

        self.prev_rolling_high.append(prev_rolling_high)
        self.prev_rolling_low.append(prev_rolling_low)
        self.trade_data.append(trade_state)

    def update_data(self):
        """데이터 업데이트 및 그래프 갱신"""
        if self.all_data is not None and self.current_index < len(self.all_data):
            # 다음 데이터 추가
            row = self.all_data.iloc[self.current_index]
            price = row.get('현재가', 80000)

            t = str(row.get('index', ''))[:-2]
            timestamp = f'{t[:4]}-{t[4:6]}-{t[6:8]} {t[8:10]}:{t[10:12]}:{t[12:]}'
            change_rate = row.get('등락율', 0)

            # 일자 변경 감지
            new_date = timestamp[:10]
            if self.current_date is None:
                self.current_date = new_date
            elif self.current_date != new_date:
                print(f"일자 변경: {self.current_date} -> {new_date}, 데이터 초기화")
                self.prices.clear()
                self.timestamps.clear()
                self.sma.clear()
                self.rolling_high.clear()
                self.rolling_low.clear()
                self.prev_rolling_high.clear()
                self.prev_rolling_low.clear()
                self.ma_calculator.price_data.clear()
                self.current_date = new_date
                self.first = True
                self.upper_bounds = []
                self.lower_bounds = []

            self.current_price = price
            self.timestamp = timestamp
            self.change_rate = change_rate
            self.add_data(price, timestamp)
            self.current_index += 1

            # 그래프 업데이트
            self.update_plots()

    def update_plots(self):
        """모든 그래프 업데이트"""
        if len(self.prices) > 1:
            x_indices = list(range(len(self.prices)))

            if self.first_draw:
                self.price_plot.clear()

            for chuse_item in self.chuse_item:
                self.price_plot.addItem(chuse_item)

            if self.first_draw:
                self.draw_items[1] = self.price_plot.plot(x_indices, list(self.prev_rolling_high), pen=pg.mkPen('skyblue', width=1, style=2), name='직전최고가')
                self.draw_items[2] = self.price_plot.plot(x_indices, list(self.rolling_high), pen=pg.mkPen('red', width=1, style=2), name='최고가')
                self.draw_items[3] = self.price_plot.plot(x_indices, list(self.prev_rolling_low), pen=pg.mkPen('skyblue', width=1, style=2), name='직전최저가')
                self.draw_items[4] = self.price_plot.plot(x_indices, list(self.rolling_low), pen=pg.mkPen('blue', width=1, style=2), name='최저가')
                self.draw_items[5] = self.price_plot.plot(x_indices, list(self.sma), pen=pg.mkPen('orange', width=1), name='이동평균')
                self.draw_items[6] = self.price_plot.plot(x_indices, list(self.prices), pen=pg.mkPen('lime', width=2), name='현재가')
                self.draw_items[7] = self.price_plot.plot([len(self.prices)-1], [self.current_price], pen=None, symbol='o', symbolBrush='yellow', symbolSize=10)
            else:
                self.draw_items[1].setData(x_indices, list(self.prev_rolling_high), pen=pg.mkPen('skyblue', width=1, style=2), name='직전최고가')
                self.draw_items[2].setData(x_indices, list(self.rolling_high), pen=pg.mkPen('red', width=1, style=2), name='최고가')
                self.draw_items[3].setData(x_indices, list(self.prev_rolling_low), pen=pg.mkPen('skyblue', width=1, style=2), name='직전최저가')
                self.draw_items[4].setData(x_indices, list(self.rolling_low), pen=pg.mkPen('blue', width=1, style=2), name='최저가')
                self.draw_items[5].setData(x_indices, list(self.sma), pen=pg.mkPen('orange', width=1), name='이동평균')
                self.draw_items[6].setData(x_indices, list(self.prices), pen=pg.mkPen('lime', width=2), name='현재가')
                self.draw_items[7].setData([len(self.prices)-1], [self.current_price], pen=None, symbol='o', symbolBrush='yellow', symbolSize=10)
                self.first_draw = False

            if len(self.trade_data) > 0:
                for i, data in enumerate(self.trade_data):
                    y_end = self.prices[i]
                    if data == 'BUY':
                        self.price_plot.plot([i], [y_end], pen=pg.mkPen('red', width=1), symbol='t1',
                                             symbolBrush=pg.mkBrush(255, 0, 0), symbolSize=12)
                    elif data == 'SELL':
                        self.price_plot.plot([i], [y_end], pen=pg.mkPen('blue', width=1), symbol='t',
                                             symbolBrush=pg.mkBrush(0, 0, 255), symbolSize=12)

            # X축 시간 표시
            step = max(1, len(self.timestamps) // 10)
            x_ticks = list(range(0, len(self.timestamps), step))
            x_labels = [self.timestamps[i][11:19] for i in x_ticks]
            ax = self.price_plot.getAxis('bottom')
            ax.setTicks([list(zip(x_ticks, x_labels))])

            # Y축 범위 동적 조절
            all_values = list(self.prices)
            all_values.extend(list(self.sma))
            all_values.extend(list(self.rolling_high))
            all_values.extend(list(self.rolling_low))

            min_val = min(all_values)
            max_val = max(all_values)
            margin = (max_val - min_val) * 0.05
            self.price_plot.setYRange(min_val - margin, max_val + margin)

            # 정보 라벨 업데이트
            current_sma = self.sma[-1] if self.sma else self.current_price
            current_high = self.rolling_high[-1] if self.rolling_high else self.current_price
            current_low = self.rolling_low[-1] if self.rolling_low else self.current_price
            sma_diff = self.current_price - current_sma

            # 위치 정보 계산
            if self.current_price >= current_high:
                position_info = "최고가 돌파"
            elif self.current_price <= current_low:
                position_info = "최저가 이탈"
            elif self.current_price >= current_sma:
                position_info = "이평 상단"
            else:
                position_info = "이평 하단"

            info_text = (f'종목코드: {self.code} | '
                         f'현재가: {self.current_price:,.0f} | '
                         f'등락율: {self.change_rate:.2f}% | '
                         f'이평: {current_sma:,.0f} ({sma_diff:+,.0f}) | '
                         f'고저: {current_high:,.0f}/{current_low:,.0f} | '
                         f'위치: {position_info} | '
                         f'체결시간: {self.timestamp}')
            self.info_label.setText(info_text)

    def load_sample_data(self):
        """데이터베이스에서 샘플 데이터 로드"""
        try:
            conn = sqlite3.connect('../_database/stock_tick_back.db')
            df = get_pd().read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", conn)
            stock_codes = df['name'].to_list()
            stock_codes.remove('moneytop')
            stock_codes.remove('stockinfo')

            while True:
                self.code = get_np().random.choice(stock_codes)
                df = get_pd().read_sql(f"SELECT * FROM '{self.code}'", conn)
                lastday = int(str(df['index'].iloc[-1])[:8]) * 1000000
                df = df[df['index'] >= lastday]
                if len(df[df['관심종목'] == 1]) >= len(df) * 0.7:
                    break

            conn.close()
            print(f"선택된 종목: {self.code}")
            print(f"데이터 로드 완료: {len(df)}개")

            self.all_data = df
            self.current_index = 0

            # 초기 데이터 10개 추가
            for i in range(min(10, len(df))):
                row = df.iloc[i]
                price = row.get('현재가', 80000)

                t = str(row.get('index', ''))[:-2]
                timestamp = f'{t[:4]}-{t[4:6]}-{t[6:8]} {t[8:10]}:{t[10:12]}:{t[12:]}'
                change_rate = row.get('등락율', 0)

                self.current_price = price
                self.timestamp = timestamp
                self.change_rate = change_rate
                self.add_data(price, timestamp)
                self.current_index += 1

        except Exception as e:
            print(f"데이터 로드 오류: {e}")


def main():
    """메인 실행 함수"""
    print("실시간 HHLL 차트 시작 (PyQt5 + PyQtGraph)...")

    app = QApplication(sys.argv)
    chart = RealtimeHHLLChart(False, 60, 2)
    chart.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
