
"""
머니트래킹 실시간 차트 (MoneyTrackingChart)

이 모듈은 가격별 누적 매수/매도 금액을 실시간으로 시각화합니다:
- PyQt5 기반의 고성능 실시간 차트
- 가격별 매수/매도 금액 누적 추적
- 실시간 가격 그래프 및 호가 시각화
- 대용량 데이터 처리를 위한 deque 사용
- 일자별 데이터 자동 초기화

사용법:
python test_tracking_money_chart.py
"""

import sys
import sqlite3
import numpy as np
import pandas as pd
import pyqtgraph as pg
from collections import deque
from PyQt5.QtGui import QFont
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel


class MoneyTrackingChart(QMainWindow):
    def __init__(self, max_points=1800):
        super().__init__()
        self.max_points = max_points
        
        # 데이터 저장용 deque (속도 우선)
        self.prices = deque(maxlen=max_points)
        self.realtime_prices = deque(maxlen=max_points)
        self.realtime_timestamps = deque(maxlen=max_points)
        
        # 당일 누적 금액 데이터
        self.daily_buy_amounts = deque(maxlen=max_points)  # 당일매수금액
        self.daily_sell_amounts = deque(maxlen=max_points)  # 당일매도금액
        
        # 실시간 데이터 생성용 변수
        self.all_data = None
        self.current_index = 0
        
        # 가격 레벨별 누적 수량 딕셔너리
        self.price_level_buy = {}   # {가격: 누적매수금액}
        self.price_level_sell = {}  # {가격: 누적매도금액}
        
        # 종목 정보
        self.code = None
        self.current_price = None
        self.timestamp = None
        self.current_date = None
        self.change_rate = None
        self.money_buy = 0
        self.money_sell = 0

        self.sell_plot = None
        self.price_plot = None
        self.realtime_plot = None
        self.daily_amount_plot = None  # 당일매수매도금액 그래프
        self.info_label = None
        self.buy_plot = None
        
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
        self.setWindowTitle('가격별 누적매수매도금액 추적 실시간 그래프 (PyQt5)')
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
        
        # 그래프 레이아웃
        upper_layout = QHBoxLayout()  # 상단 그래프 레이아웃
        lower_layout = QHBoxLayout()  # 하단 그래프 레이아웃
        
        # 상단 그래프: 실시간 가격 그래프 (좌측 50%)
        self.realtime_plot = pg.PlotWidget(title="현재가")
        self.realtime_plot.setLabel('left', '가격')
        self.realtime_plot.setLabel('bottom', '시간')
        self.realtime_plot.showGrid(x=True, y=True, alpha=0.3)
        self.realtime_plot.setBackground('k')  # 검은색 배경
        
        # 상단 그래프: 당일매수매도금액 그래프 (우측 50%)
        self.daily_amount_plot = pg.PlotWidget(title="당일매수매도금액")
        self.daily_amount_plot.setLabel('left', '금액')
        self.daily_amount_plot.setLabel('bottom', '시간')
        self.daily_amount_plot.showGrid(x=True, y=True, alpha=0.3)
        self.daily_amount_plot.setBackground('k')  # 검은색 배경
        self.daily_amount_plot.addLegend()  # 범례 추가
        
        # 매도/매수 막대그래프 (하단)
        self.buy_plot = pg.PlotWidget(title="누적매도금액")
        self.buy_plot.setLabel('left', '가격')
        self.buy_plot.setLabel('bottom', '금액')
        self.buy_plot.showGrid(x=True, y=True, alpha=0.3)
        self.buy_plot.setBackground('k')  # 검은색 배경
        
        self.price_plot = pg.PlotWidget(title="현재가")
        self.price_plot.setLabel('left', '가격')
        self.price_plot.setLabel('bottom', '호가')
        self.price_plot.showGrid(x=True, y=True, alpha=0.3)
        self.price_plot.setBackground('k')  # 검은색 배경
        
        self.sell_plot = pg.PlotWidget(title="누적매수금액")
        self.sell_plot.setLabel('left', '가격')
        self.sell_plot.setLabel('bottom', '금액')
        self.sell_plot.showGrid(x=True, y=True, alpha=0.3)
        self.sell_plot.setBackground('k')  # 검은색 배경
        
        # 상단 그래프 추가 (가격: 50%, 매수매도금액: 50%)
        upper_layout.addWidget(self.realtime_plot, stretch=1)
        upper_layout.addWidget(self.daily_amount_plot, stretch=1)
        
        # 하단 그래프 추가 (현재가 영역 너비 줄임)
        lower_layout.addWidget(self.buy_plot, stretch=2)
        lower_layout.addWidget(self.price_plot, stretch=1)
        lower_layout.addWidget(self.sell_plot, stretch=2)
        
        main_layout.addLayout(upper_layout)
        main_layout.addLayout(lower_layout)
        
        # 그래프 스타일 설정
        self.setup_plot_styles()
    
    def setup_plot_styles(self):
        """그래프 스타일 설정"""
        # 한글 폰트 설정
        font = QFont("Malgun Gothic", 9)
        
        # 실시간 그래프
        self.realtime_plot.getAxis('left').setStyle(tickFont=font)
        self.realtime_plot.getAxis('bottom').setStyle(tickFont=font)
        
        # 막대그래프들
        for plot in [self.buy_plot, self.price_plot, self.sell_plot, self.daily_amount_plot]:
            plot.getAxis('left').setStyle(tickFont=font)
            plot.getAxis('bottom').setStyle(tickFont=font)
    
    def add_data(self, price, buy_volume, sell_volume, timestamp):
        """새로운 데이터 추가"""
        if price not in list(self.prices):
            self.prices.append(price)

        new_date = timestamp[:10]
        if self.current_date is None:
            self.current_date = new_date
        elif self.current_date != new_date:
            print(f"일자 변경: {self.current_date} -> {new_date}, 누적 수량 초기화")
            self.price_level_buy.clear()
            self.price_level_sell.clear()
            self.current_date = new_date
            self.money_buy = 0
            self.money_sell = 0
            # 실시간 그래프도 초기화
            self.realtime_prices.clear()
            self.realtime_timestamps.clear()

        money_buy = price * buy_volume
        money_sell = price * sell_volume

        if price in self.price_level_buy:
            self.price_level_buy[price] += money_buy
        else:
            self.price_level_buy[price] = money_buy

        if price in self.price_level_sell:
            self.price_level_sell[price] += money_sell
        else:
            self.price_level_sell[price] = money_sell

        self.money_buy += price * buy_volume
        self.money_sell += price * sell_volume
        
        # 실시간 가격 데이터 추가
        self.realtime_prices.append(price)
        self.realtime_timestamps.append(timestamp)
        
        # 당일 누적 금액 데이터 추가
        self.daily_buy_amounts.append(self.money_buy)
        self.daily_sell_amounts.append(self.money_sell)
    
    def update_data(self):
        """데이터 업데이트 및 그래프 갱신"""
        if self.all_data is not None and self.current_index < len(self.all_data):
            # 다음 데이터 추가
            row = self.all_data.iloc[self.current_index]
            price = row.get('현재가', 80000)
            buy_volume = row.get('초당매수수량', np.random.randint(100, 1000))
            sell_volume = row.get('초당매도수량', np.random.randint(100, 1000))
            t = str(row.get('index', ''))[:-2]
            timestamp = f'{t[:4]}-{t[4:6]}-{t[6:8]} {t[8:10]}:{t[10:12]}:{t[12:]}'
            change_rate = row.get('등락율', 0)

            # 일자 변경 감지
            new_date = timestamp[:10]
            if self.current_date is None:
                self.current_date = new_date
            elif self.current_date != new_date:
                print(f"일자 변경: {self.current_date} -> {new_date}, 누적 수량 초기화")
                self.price_level_buy.clear()
                self.price_level_sell.clear()
                self.current_date = new_date
                self.money_buy = 0
                self.money_sell = 0
                # 실시간 그래프도 초기화
                self.realtime_prices.clear()
                self.realtime_timestamps.clear()
                self.daily_buy_amounts.clear()
                self.daily_sell_amounts.clear()

            self.current_price = price
            self.timestamp = timestamp
            self.change_rate = change_rate
            self.add_data(price, buy_volume, sell_volume, timestamp)
            self.current_index += 1
            
            # 그래프 업데이트
            self.update_plots()
    
    def update_plots(self):
        """모든 그래프 업데이트"""
        price_values = list(self.prices)
        
        if price_values:
            # 매도/매수 데이터 준비
            sell_values = [self.price_level_sell.get(price, 0) for price in price_values]
            buy_values = [self.price_level_buy.get(price, 0) for price in price_values]
            
            # 가격 범위 계산
            price_range = max(price_values) - min(price_values)
            margin = price_range * 0.05
            max_price_range = max(price_values) + margin
            min_price_range = min(price_values) - margin
            
            # 막대 높이 계산 (겹치지 않게 조정)
            bar_height = price_range / len(price_values) * 0.4
            
            # 매도 막대그래프 업데이트 (수평 막대 - 음수 방향)
            self.buy_plot.clear()
            
            # 가장 큰 매도 막대 두 개 찾기
            sell_bars = [(price, sell_val) for price, sell_val in zip(price_values, sell_values) if sell_val > 0]
            sell_bars.sort(key=lambda x: x[1], reverse=True)
            top_sell_bars = sell_bars[:2]
            top_sell_prices = {price for price, _ in top_sell_bars}
            
            for price, sell_val in zip(price_values, sell_values):
                if sell_val > 0:
                    # BarGraphItem을 올바르게 사용하여 수평 막대 그리기
                    bar_item = pg.BarGraphItem(
                        x=[-sell_val/2],  # 막대 중심 위치
                        y=[price],  # Y축 위치 명시적 지정
                        height=bar_height,  # 막대 두께
                        width=sell_val,  # 막대 너비
                        brush='b',  # 파란색
                        pen='b'
                    )
                    self.buy_plot.addItem(bar_item)
                    
                    # 가장 큰 막대 두 개에만 가격 표시
                    if price in top_sell_prices:
                        price_text = pg.TextItem(f'{price:,.0f}', color='white', anchor=(1, 0.5))
                        price_text.setPos(-sell_val, price)
                        price_text.setFont(QFont("Malgun Gothic", 8))
                        self.buy_plot.addItem(price_text)
            
            # X축 스케일 통일을 위해 최대값 저장
            max_sell = max(sell_values) if sell_values else 1
            self.buy_plot.setYRange(min_price_range, max_price_range)
            
            # 현재가 그래프 업데이트
            self.price_plot.clear()
            
            # 표시할 가격 개수 제한 (최대 15개)
            max_display = min(len(price_values), 15)
            step = max(1, len(price_values) // max_display)
            display_prices = price_values[::step]
            
            for i, price in enumerate(price_values):
                if price == self.current_price:
                    # 현재가 강조
                    self.price_plot.plot([0, 1], [price, price], pen=pg.mkPen('r', width=3))
                    text_item = pg.TextItem(f'{price:,.0f}', color='white', anchor=(0.5, 0.5))
                    text_item.setPos(0.5, price)
                    text_item.setFont(QFont("Malgun Gothic", 10, QFont.Bold))
                    self.price_plot.addItem(text_item)
                elif price in display_prices:
                    # 일정 간격으로만 표시
                    self.price_plot.plot([0, 1], [price, price], pen=pg.mkPen('gray', width=1))
                    text_item = pg.TextItem(f'{price:,.0f}', color='white', anchor=(0.5, 0.5))
                    text_item.setPos(0.5, price)
                    text_item.setFont(QFont("Malgun Gothic", 9))
                    self.price_plot.addItem(text_item)
            
            self.price_plot.setYRange(min_price_range, max_price_range)
            self.price_plot.setXRange(0, 1)
            
            # 매수 막대그래프 업데이트 (수평 막대 - 양수 방향)
            self.sell_plot.clear()
            
            # 가장 큰 매수 막대 두 개 찾기
            buy_bars = [(price, buy_val) for price, buy_val in zip(price_values, buy_values) if buy_val > 0]
            buy_bars.sort(key=lambda x: x[1], reverse=True)
            top_buy_bars = buy_bars[:2]
            top_buy_prices = {price for price, _ in top_buy_bars}
            
            for price, buy_val in zip(price_values, buy_values):
                if buy_val > 0:
                    # BarGraphItem을 올바르게 사용하여 수평 막대 그리기
                    bar_item = pg.BarGraphItem(
                        x=[buy_val/2],  # 막대 중심 위치
                        y=[price],  # Y축 위치 명시적 지정
                        height=bar_height,  # 막대 두께
                        width=buy_val,  # 막대 너비
                        brush='r',  # 빨간색
                        pen='r'
                    )
                    self.sell_plot.addItem(bar_item)
                    
                    # 가장 큰 막대 두 개에만 가격 표시
                    if price in top_buy_prices:
                        price_text = pg.TextItem(f'{price:,.0f}', color='white', anchor=(0, 0.5))
                        price_text.setPos(buy_val, price)
                        price_text.setFont(QFont("Malgun Gothic", 8))
                        self.sell_plot.addItem(price_text)
            
            # X축 스케일 통일
            max_buy = max(buy_values) if buy_values else 1
            max_scale = max(max_sell, max_buy) * 1.1
            
            # 최고 매수/매도 금액 찾기 및 표시
            max_sell_items = sorted([(price, val) for price, val in zip(price_values, sell_values) if val > 0],
                                    key=lambda x: x[1], reverse=True)[:2]
            max_buy_items = sorted([(price, val) for price, val in zip(price_values, buy_values) if val > 0], 
                                   key=lambda x: x[1], reverse=True)[:2]
            
            # 매도 최고 금액 표시 (막대 안쪽 아래)
            for price, sell_val in max_sell_items:
                # 막대 중심을 기준으로 끝부분에 위치 조정
                x_pos = -sell_val * 0.4  # 막대 중심(-sell_val/2)에서 약간 왼쪽
                y_pos = price - bar_height * 0.8  # 막대 아래쪽
                text_item = pg.TextItem(f'{sell_val:,.0f}', color='cyan', anchor=(1, 1))
                text_item.setPos(x_pos, y_pos)
                text_item.setFont(QFont("Malgun Gothic", 8, QFont.Bold))
                self.buy_plot.addItem(text_item)
            
            # 매수 최고 금액 표시 (막대 안쪽 아래)
            for price, buy_val in max_buy_items:
                # 막대 중심을 기준으로 끝부분에 위치 조정
                x_pos = buy_val * 0.4  # 막대 중심(buy_val/2)에서 약간 오른쪽
                y_pos = price - bar_height * 0.8  # 막대 아래쪽
                text_item = pg.TextItem(f'{buy_val:,.0f}', color='yellow', anchor=(0, 1))
                text_item.setPos(x_pos, y_pos)
                text_item.setFont(QFont("Malgun Gothic", 8, QFont.Bold))
                self.sell_plot.addItem(text_item)
            
            # 양쪽 그래프의 X축 스케일 통일
            self.buy_plot.setXRange(-max_scale, 0)
            self.sell_plot.setXRange(0, max_scale)
            self.sell_plot.setYRange(min_price_range, max_price_range)
            
            # 실시간 가격 그래프 업데이트
            if len(self.realtime_prices) > 1:
                self.realtime_plot.clear()
                x_indices = list(range(len(self.realtime_prices)))
                self.realtime_plot.plot(x_indices, list(self.realtime_prices), 
                                        pen=pg.mkPen('lime', width=2), name='가격')  # 밝은 녹색
                
                # 현재가 강조
                self.realtime_plot.plot([len(self.realtime_prices)-1], [self.current_price], 
                                        pen=None, symbol='o', symbolBrush='r', symbolSize=10)
                
                # X축 시간 표시
                step = max(1, len(self.realtime_timestamps) // 10)
                x_ticks = list(range(0, len(self.realtime_timestamps), step))
                x_labels = [self.realtime_timestamps[i][11:19] for i in x_ticks]
                ax = self.realtime_plot.getAxis('bottom')
                ax.setTicks([list(zip(x_ticks, x_labels))])
                
                # Y축 범위 동적 조절
                price_min = min(self.realtime_prices)
                price_max = max(self.realtime_prices)
                margin = (price_max - price_min) * 0.1
                self.realtime_plot.setYRange(price_min - margin, price_max + margin)
            
            # 당일매수매도금액 그래프 업데이트
            if len(self.daily_buy_amounts) > 1:
                self.daily_amount_plot.clear()
                x_indices = list(range(len(self.daily_buy_amounts)))
                
                # 당일매수금액 선 (빨간색)
                self.daily_amount_plot.plot(x_indices, list(self.daily_buy_amounts), 
                                            pen=pg.mkPen('red', width=2), name='당일매수금액')
                
                # 당일매도금액 선 (파란색)
                self.daily_amount_plot.plot(x_indices, list(self.daily_sell_amounts), 
                                            pen=pg.mkPen('blue', width=2), name='당일매도금액')
                
                # X축 시간 표시
                step = max(1, len(self.realtime_timestamps) // 10)
                x_ticks = list(range(0, len(self.realtime_timestamps), step))
                x_labels = [self.realtime_timestamps[i][11:19] for i in x_ticks]
                ax = self.daily_amount_plot.getAxis('bottom')
                ax.setTicks([list(zip(x_ticks, x_labels))])
                
                # Y축 범위 동적 조절 (두 선의 최대/최소값 기준)
                if len(self.daily_buy_amounts) > 0 and len(self.daily_sell_amounts) > 0:
                    all_values = list(self.daily_buy_amounts) + list(self.daily_sell_amounts)
                    min_val = min(all_values)
                    max_val = max(all_values)
                    margin = (max_val - min_val) * 0.02 if max_val > min_val else max_val * 0.1
                    self.daily_amount_plot.setYRange(min_val - margin, max_val + margin)
            
            # 정보 라벨 업데이트
            info_text = (f'종목코드: {self.code} | '
                         f'현재가: {self.current_price:,.0f} | '
                         f'등락율: {self.change_rate:.2f}% | '
                         f'누적매수금액: {self.money_buy:,.0f} | '
                         f'누적매도금액: {self.money_sell:,.0f} | '
                         f'체결시간: {self.timestamp}')
            self.info_label.setText(info_text)
    
    def load_sample_data(self):
        """데이터베이스에서 샘플 데이터 로드"""
        try:
            conn = sqlite3.connect('../_database/stock_tick_back.db')
            df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", conn)
            stock_codes = df['name'].to_list()
            stock_codes.remove('moneytop')
            stock_codes.remove('stockinfo')

            while True:
                self.code = np.random.choice(stock_codes)
                df = pd.read_sql(f"SELECT * FROM '{self.code}'", conn)
                lastday = int(str(df['index'].iloc[-1])[:8]) * 1000000
                df = df[df['index'] >= lastday]
                if len(df[df['관심종목'] == 1]) >= len(df) * 0.7:
                    break

            conn.close()
            print(f"선택된 종목: {self.code}")
            print(f"데이터 로드 완료: {len(df)}개")

            self.all_data = df
            self.current_index = 0

            for i in range(min(10, len(df))):
                row = df.iloc[i]
                price = row.get('현재가', 80000)
                buy_volume = row.get('초당매수수량', np.random.randint(100, 1000))
                sell_volume = row.get('초당매도수량', np.random.randint(100, 1000))
                t = str(row.get('index', ''))[:-2]
                timestamp = f'{t[:4]}-{t[4:6]}-{t[6:8]} {t[8:10]}:{t[10:12]}:{t[12:]}'
                change_rate = row.get('등락율', 0)
                
                self.current_price = price
                self.timestamp = timestamp
                self.change_rate = change_rate
                self.add_data(price, buy_volume, sell_volume, timestamp)
                
        except Exception as e:
            print(f"데이터 로드 오류: {e}")


def main():
    """메인 실행 함수"""
    print("실시간 주식 그래프 시작 (PyQt5 + PyQtGraph)...")
    
    app = QApplication(sys.argv)
    chart = MoneyTrackingChart(max_points=1800)
    chart.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
