"""
Smart VWAP 실시간 차트 (SmartVWAPChart)

이 모듈은 Smart Volume Weighted Average Price를 실시간으로 계산하고 시각화합니다:
- PyQt5 기반의 고성능 실시간 차트
- 시장 마이크로스트럭처를 고려한 Smart VWAP 계산
- 일반 VWAP과 Smart VWAP 비교 표시
- 실시간 가격 그래프 및 VWAP 선 시각화
- 대용량 데이터 처리를 위한 deque 사용
- 일자별 데이터 자동 초기화

Smart VWAP 특징:
- 시간 가중치: 최근 거래에 더 높은 가중치
- 호가 유동성: 매수/매도 호가 잔량 고려
- 거래 강도: 체결 강도와 초당 거래량 반영
- 시장 압력: 수급 불균형 감지

사용법:
python test_smart_vwap_chart.py
"""

import sys
import sqlite3
import numpy as np
import pandas as pd
import pyqtgraph as pg
from collections import deque
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QFont


class SmartVWAPCalculator:
    """Smart VWAP 계산기 클래스"""
    
    def __init__(self, decay_factor=0.95, liquidity_weight=0.3, pressure_weight=0.2):
        """
        Smart VWAP 계산기 초기화
        
        Args:
            decay_factor: 시간 가중치 감쇠 계수 (0.95 = 최근 데이터에 5% 더 높은 가중치)
            liquidity_weight: 유동성 가중치 (0.0-1.0)
            pressure_weight: 시장 압력 가중치 (0.0-1.0)
        """
        self.decay_factor = decay_factor
        self.liquidity_weight = liquidity_weight
        self.pressure_weight = pressure_weight

        # 데이터 저장
        self.price_volume_data = deque(maxlen=1000)     # 가격-거래량 데이터
        self.orderbook_data = deque(maxlen=100)         # 호가 데이터
        self.pressure_data = deque(maxlen=50)           # 시장 압력 데이터
        self.smart_vwap_history = deque(maxlen=100)     # Smart VWAP 히스토리 (밴드용)
        
    def calculate_smart_vwap(self, price, volume, ask_prices, bid_prices, ask_qtys, bid_qtys):
        """
        Smart VWAP 계산
        
        Args:
            price: 현재가
            volume: 거래량
            ask_prices: 매도호가 배열
            bid_prices: 매수호가 배열
            ask_qtys: 매도잔량 배열
            bid_qtys: 매수잔량 배열
            
        Returns:
            float: Smart VWAP 값
        """
        # 기본 VWAP 계산
        self.price_volume_data.append((price, volume))
        
        if len(self.price_volume_data) < 2:
            return price
        
        # 시간 가중치 적용 VWAP
        weighted_price_sum = 0
        weighted_volume_sum = 0
        
        for i, (p, v) in enumerate(self.price_volume_data):
            # 시간 가중치 (최근일수록 높은 가중치)
            time_weight = self.decay_factor ** (len(self.price_volume_data) - i - 1)
            
            weighted_price_sum += p * v * time_weight
            weighted_volume_sum += v * time_weight
        
        time_weighted_vwap = weighted_price_sum / weighted_volume_sum if weighted_volume_sum > 0 else price
        
        # 유동성 조정 계수 계산
        liquidity_adjustment = self._calculate_liquidity_adjustment(ask_prices, bid_prices, ask_qtys, bid_qtys)
        
        # 시장 압력 조정 계수 계산
        pressure_adjustment = self._calculate_pressure_adjustment(price, ask_prices, bid_prices, ask_qtys, bid_qtys)
        
        # Smart VWAP = 시간가중VWAP + 유동성조정 + 압력조정
        smart_vwap = time_weighted_vwap
        smart_vwap += liquidity_adjustment * self.liquidity_weight * price
        smart_vwap += pressure_adjustment * self.pressure_weight * price
        
        # Smart VWAP 히스토리 저장 (밴드 계산용)
        self.smart_vwap_history.append(smart_vwap)
        
        return smart_vwap

    def calculate_ema60(self):
        if len(self.price_volume_data) < 60:
            return None
        return sum(p for p, v in list(self.price_volume_data)[-60:]) / 60
    
    def calculate_bollinger_bands(self, period=30, std_multiplier=2.0):
        """
        Smart VWAP 기준 볼린저 밴드 계산
        
        Args:
            period: 기간 (기본 30)
            std_multiplier: 표준편차 배수 (기본 2.0)
            
        Returns:
            tuple: (상단밴드, 중간선, 하단밴드)
        """
        if len(self.smart_vwap_history) < period:
            return None, None
        
        # 최근 period개 Smart VWAP 데이터
        recent_vwaps = list(self.smart_vwap_history)[-period:]
        
        # 중간선 (이동평균)
        middle = np.mean(recent_vwaps)
        
        # 표준편차
        std = np.std(recent_vwaps)
        
        # 상단/하단 밴드
        # noinspection PyTypeChecker
        upper = middle + (std * std_multiplier)
        # noinspection PyTypeChecker
        lower = middle - (std * std_multiplier)
        
        return upper, lower
    
    def _calculate_liquidity_adjustment(self, ask_prices, bid_prices, ask_qtys, bid_qtys):
        """유동성 조정 계수 계산"""
        try:
            # 호가 스프레드 계산
            best_ask = ask_prices[0] if ask_prices[0] > 0 else float('inf')
            best_bid = bid_prices[0] if bid_prices[0] > 0 else 0
            
            if best_ask == float('inf') or best_bid == 0:
                return 0
            
            spread = best_ask - best_bid
            spread_pct = spread / best_bid
            
            # 총 유동성 계산
            total_ask_liquidity = sum(ask_qtys)
            total_bid_liquidity = sum(bid_qtys)
            total_liquidity = total_ask_liquidity + total_bid_liquidity
            
            if total_liquidity == 0:
                return 0
            
            # 유동성 불균형 계산
            liquidity_imbalance = (total_bid_liquidity - total_ask_liquidity) / total_liquidity
            
            # 스프레드가 좁을수록, 유동성이 높을수록 긍정적 조정
            spread_factor = max(0, 1 - spread_pct * 100)  # 스프레드 1%당 1점 감소
            liquidity_factor = min(1, total_liquidity / 10000)  # 유동성 10000당 1점
            
            adjustment = (liquidity_imbalance * 0.7 + spread_factor * 0.2 + liquidity_factor * 0.1) * 0.001
            
            return adjustment
            
        except (IndexError, ZeroDivisionError):
            return 0
    
    def _calculate_pressure_adjustment(self, current_price, ask_prices, bid_prices, ask_qtys, bid_qtys):
        """시장 압력 조정 계수 계산"""
        try:
            # 가격 레벨별 압력 계산
            buy_pressure = 0
            sell_pressure = 0
            
            for i in range(min(5, len(ask_prices), len(bid_prices))):
                # 매수 압력: 현재가보다 낮은 매수호가에 대한 수요
                if bid_prices[i] < current_price and bid_qtys[i] > 0:
                    distance_ratio = (current_price - bid_prices[i]) / current_price
                    buy_pressure += bid_qtys[i] * (1 - distance_ratio)
                
                # 매도 압력: 현재가보다 높은 매도호가에 대한 공급
                if ask_prices[i] > current_price and ask_qtys[i] > 0:
                    distance_ratio = (ask_prices[i] - current_price) / current_price
                    sell_pressure += ask_qtys[i] * (1 - distance_ratio)
            
            total_pressure = buy_pressure + sell_pressure
            if total_pressure == 0:
                return 0
            
            # 순압력 계산 (-1 ~ 1)
            net_pressure = (buy_pressure - sell_pressure) / total_pressure
            
            # 압력 조정 계수 (매수 압력이 높으면 양수, 매도 압력이 높으면 음수)
            pressure_adjustment = net_pressure * 0.002  # 최대 ±0.2% 조정
            
            return pressure_adjustment
            
        except (IndexError, ZeroDivisionError):
            return 0


class SmartVWAPChart(QMainWindow):
    def __init__(self, twoway=False, width_limit=0.75, strength_limit=5, sell_limit=0.75, max_points=1800):
        super().__init__()
        self.twoway = twoway
        self.width_limit = width_limit
        self.sell_limit = sell_limit
        self.strength_limit = strength_limit
        self.max_points = max_points
        
        # Smart VWAP 계산기
        self.vwap_calculator = SmartVWAPCalculator(
            decay_factor=0.97,      # 시간 가중치 감쇠 계수
            liquidity_weight=0.25,  # 유동성 가중치
            pressure_weight=0.15   # 시장 압력 가중치
        )
        
        # 데이터 저장용 deque (속도 우선)
        self.prices = deque(maxlen=max_points)
        self.volumes = deque(maxlen=max_points)
        self.timestamps = deque(maxlen=max_points)
        
        # Smart VWAP 데이터
        self.smart_vwaps = deque(maxlen=max_points)     # Smart VWAP
        self.sma60 = deque(maxlen=max_points)           # SMA60
        self.upper_bands = deque(maxlen=max_points)     # 상단 밴드
        self.lower_bands = deque(maxlen=max_points)     # 하단 밴드
        self.trade_data = deque(maxlen=max_points)      # 신호 저장

        self.first_draw = True
        self.draw_items = {}
        
        # 실시간 데이터 생성용 변수
        self.all_data = None
        self.current_index = 0
        
        # 종목 정보
        self.code = None
        self.current_price = None
        self.timestamp = None
        self.current_date = None
        self.change_rate = None
        self.trade_state = None
        
        # UI 컴포넌트
        self.price_plot = None
        self.info_label = None
        
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
        self.setWindowTitle('Smart VWAP 실시간 차트 (PyQt5)')
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
        
        # 그래프: 가격과 Smart VWAP
        self.price_plot = pg.PlotWidget(title="가격 vs Smart VWAP")
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
    
    def add_data(self, price, volume, ask_prices, bid_prices, ask_qtys, bid_qtys, timestamp):
        """새로운 데이터 추가"""
        self.prices.append(price)
        self.volumes.append(volume)
        self.timestamps.append(timestamp)
        
        # Smart VWAP 계산
        smart_vwap = self.vwap_calculator.calculate_smart_vwap(
            price, volume, ask_prices, bid_prices, ask_qtys, bid_qtys
        )

        # SMA60 계산
        sma60 = self.vwap_calculator.calculate_ema60()
        
        # 볼린저 밴드 계산
        upper_band, lower_band = self.vwap_calculator.calculate_bollinger_bands()
        
        # 돌파 상태 감지
        trade_state = None

        if sma60 and upper_band and lower_band:
            # 상단 밴드 돌파 감지
            if self.trade_state is None and smart_vwap > upper_band:
                band_width_ratio = (upper_band - lower_band) / price * 100                  # 현재가 대비 밴드폭 비율
                strength = (smart_vwap - upper_band) / (upper_band - lower_band) * 100      # 밴드폭 대비 돌파 강도(%)
                if band_width_ratio >= self.width_limit and strength >= self.strength_limit:
                    trade_state = 'BUY'
                    self.trade_state = 'BUY'
            # 현재가가 Smart VWAP 아래인 경우 매도신호
            elif self.trade_state == 'BUY' and price < sma60:
                pct = (price / sma60 - 1) * 100
                if pct <= -self.sell_limit:
                    trade_state = 'SELL'
                    self.trade_state = None
            # 하단 밴드 이탈 감지
            elif self.twoway and self.trade_state is None and smart_vwap < lower_band:
                band_width_ratio = (upper_band - lower_band) / price * 100                  # 현재가 대비 밴드폭 비율
                strength = (lower_band - smart_vwap) / (upper_band - lower_band) * 100      # 밴드폭 대비 하락 강도(%)
                if band_width_ratio >= self.width_limit and strength >= self.strength_limit:
                    trade_state = 'SELL'
                    self.trade_state = 'SELL'
            # 현재가가 Smart VWAP 위인 경우 매도신호
            elif self.twoway and self.trade_state == 'SELL' and price > sma60:
                pct = (price / sma60 - 1) * 100
                if pct >= self.sell_limit:
                    trade_state = 'BUY'
                    self.trade_state = None
            else:
                trade_state = None
        else:
            trade_state = None
        
        self.smart_vwaps.append(smart_vwap)
        self.sma60.append(sma60 if sma60 else smart_vwap)
        self.upper_bands.append(upper_band if upper_band else smart_vwap)
        self.lower_bands.append(lower_band if lower_band else smart_vwap)
        self.trade_data.append(trade_state)
    
    def update_data(self):
        """데이터 업데이트 및 그래프 갱신"""
        if self.all_data is not None and self.current_index < len(self.all_data):
            # 다음 데이터 추가
            row = self.all_data.iloc[self.current_index]
            price = row.get('현재가', 80000)
            volume = row.get('초당매수수량', 0) + row.get('초당매도수량', 1)
            
            # 호가 데이터 추출
            ask_prices = [
                row.get('매도호가1', price + 10),
                row.get('매도호가2', price + 20),
                row.get('매도호가3', price + 30),
                row.get('매도호가4', price + 40),
                row.get('매도호가5', price + 50)
            ]
            
            bid_prices = [
                row.get('매수호가1', price - 10),
                row.get('매수호가2', price - 20),
                row.get('매수호가3', price - 30),
                row.get('매수호가4', price - 40),
                row.get('매수호가5', price - 50)
            ]
            
            ask_qtys = [
                row.get('매도잔량1', np.random.randint(100, 1000)),
                row.get('매도잔량2', np.random.randint(100, 1000)),
                row.get('매도잔량3', np.random.randint(100, 1000)),
                row.get('매도잔량4', np.random.randint(100, 1000)),
                row.get('매도잔량5', np.random.randint(100, 1000))
            ]
            
            bid_qtys = [
                row.get('매수잔량1', np.random.randint(100, 1000)),
                row.get('매수잔량2', np.random.randint(100, 1000)),
                row.get('매수잔량3', np.random.randint(100, 1000)),
                row.get('매수잔량4', np.random.randint(100, 1000)),
                row.get('매수잔량5', np.random.randint(100, 1000))
            ]
            
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
                self.volumes.clear()
                self.timestamps.clear()
                self.smart_vwaps.clear()
                self.sma60.clear()
                self.upper_bands.clear()
                self.middle_bands.clear()
                self.lower_bands.clear()
                self.trade_data.clear()
                self.current_date = new_date

            self.current_price = price
            self.timestamp = timestamp
            self.change_rate = change_rate
            self.add_data(price, volume, ask_prices, bid_prices, ask_qtys, bid_qtys, timestamp)
            self.current_index += 1
            
            # 그래프 업데이트
            self.update_plots()
    
    def update_plots(self):
        """모든 그래프 업데이트"""
        if len(self.prices) > 1:
            x_indices = list(range(len(self.prices)))

            if self.first_draw:
                self.price_plot.clear()
                self.draw_items[1] = self.price_plot.plot(x_indices, list(self.sma60), pen=pg.mkPen('blue', width=1), name='SMA60')
                self.draw_items[2] = self.price_plot.plot(x_indices, list(self.upper_bands), pen=pg.mkPen('skyblue', width=1, style=2), name='상단밴드')
                self.draw_items[3] = self.price_plot.plot(x_indices, list(self.lower_bands), pen=pg.mkPen('skyblue', width=1, style=2), name='하단밴드')
                self.draw_items[4] = self.price_plot.plot(x_indices, list(self.smart_vwaps), pen=pg.mkPen('red', width=1), name='Smart VWAP')
                self.draw_items[5] = self.price_plot.plot(x_indices, list(self.prices), pen=pg.mkPen('lime', width=2), name='현재가')
                self.draw_items[6] = self.price_plot.plot([len(self.prices)-1], [self.current_price], pen=None, symbol='o', symbolBrush='yellow', symbolSize=10)
            else:
                self.draw_items[1].setData(x_indices, list(self.sma60), pen=pg.mkPen('blue', width=1), name='SMA60')
                self.draw_items[2].setData(x_indices, list(self.upper_bands), pen=pg.mkPen('skyblue', width=1, style=2), name='상단밴드')
                self.draw_items[3].setData(x_indices, list(self.lower_bands), pen=pg.mkPen('skyblue', width=1, style=2), name='하단밴드')
                self.draw_items[4].setData(x_indices, list(self.smart_vwaps), pen=pg.mkPen('red', width=1), name='Smart VWAP')
                self.draw_items[5].setData(x_indices, list(self.prices), pen=pg.mkPen('lime', width=2), name='현재가')
                self.draw_items[6].setData([len(self.prices)-1], [self.current_price], pen=None, symbol='o', symbolBrush='yellow', symbolSize=10)
                self.first_draw = False

            if len(self.trade_data) > 0:
                for i, data in enumerate(self.trade_data):
                    if data == 'BUY':
                        y_end = self.prices[i]
                        self.price_plot.plot([i], [y_end], pen=pg.mkPen('red', width=1), symbol='t1',
                                             symbolBrush=pg.mkBrush(255, 0, 0), symbolSize=12)
                    elif data == 'SELL':
                        y_end = self.prices[i]
                        self.price_plot.plot([i], [y_end], pen=pg.mkPen('blue', width=1), symbol='t',
                                             symbolBrush=pg.mkBrush(0, 0, 255), symbolSize=12)
            
            # X축 시간 표시
            step = max(1, len(self.timestamps) // 10)
            x_ticks = list(range(0, len(self.timestamps), step))
            x_labels = [self.timestamps[i][11:19] for i in x_ticks]
            ax = self.price_plot.getAxis('bottom')
            ax.setTicks([list(zip(x_ticks, x_labels))])
            
            # Y축 범위 동적 조절
            all_values = list(self.prices) + list(self.smart_vwaps)
            if len(self.upper_bands) > 0:
                all_values.extend(list(self.upper_bands))
            if len(self.lower_bands) > 0:
                all_values.extend(list(self.lower_bands))
            
            min_val = min(all_values)
            max_val = max(all_values)
            margin = (max_val - min_val) * 0.05
            self.price_plot.setYRange(min_val - margin, max_val + margin)
            
            # 정보 라벨 업데이트
            current_smart_vwap = self.smart_vwaps[-1] if self.smart_vwaps else self.current_price
            vwap_difference = current_smart_vwap - self.current_price
            
            # 밴드 정보 추가
            band_info = ""
            
            if len(self.upper_bands) > 0 and len(self.lower_bands) > 0:
                current_upper = self.upper_bands[-1]
                current_lower = self.lower_bands[-1]
                band_width = current_upper - current_lower
                
                # 밴드 위치 판단
                if self.current_price > current_upper:
                    band_position = "상단 돌파"
                elif self.current_price < current_lower:
                    band_position = "하단 돌파"
                else:
                    band_position = "밴드 내부"
                
                band_info = f' | 밴드폭: {band_width:.0f} | 위치: {band_position}'
            
            info_text = (f'종목코드: {self.code} | '
                         f'현재가: {self.current_price:,.0f} | '
                         f'등락율: {self.change_rate:.2f}% | '
                         f'Smart VWAP: {current_smart_vwap:,.0f} ({vwap_difference:+.0f})'
                         f'{band_info}'
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

            # 초기 데이터 10개 추가
            for i in range(min(10, len(df))):
                row = df.iloc[i]
                price = row.get('현재가', 80000)
                volume = row.get('초당매수수량', 0) + row.get('초당매도수량', 1)
                
                ask_prices = [
                    row.get('매도호가1', price + 10),
                    row.get('매도호가2', price + 20),
                    row.get('매도호가3', price + 30),
                    row.get('매도호가4', price + 40),
                    row.get('매도호가5', price + 50)
                ]
                
                bid_prices = [
                    row.get('매수호가1', price - 10),
                    row.get('매수호가2', price - 20),
                    row.get('매수호가3', price - 30),
                    row.get('매수호가4', price - 40),
                    row.get('매수호가5', price - 50)
                ]
                
                ask_qtys = [
                    row.get('매도잔량1', np.random.randint(100, 1000)),
                    row.get('매도잔량2', np.random.randint(100, 1000)),
                    row.get('매도잔량3', np.random.randint(100, 1000)),
                    row.get('매도잔량4', np.random.randint(100, 1000)),
                    row.get('매도잔량5', np.random.randint(100, 1000))
                ]
                
                bid_qtys = [
                    row.get('매수잔량1', np.random.randint(100, 1000)),
                    row.get('매수잔량2', np.random.randint(100, 1000)),
                    row.get('매수잔량3', np.random.randint(100, 1000)),
                    row.get('매수잔량4', np.random.randint(100, 1000)),
                    row.get('매수잔량5', np.random.randint(100, 1000))
                ]
                
                t = str(row.get('index', ''))[:-2]
                timestamp = f'{t[:4]}-{t[4:6]}-{t[6:8]} {t[8:10]}:{t[10:12]}:{t[12:]}'
                change_rate = row.get('등락율', 0)
                
                self.current_price = price
                self.timestamp = timestamp
                self.change_rate = change_rate
                self.add_data(price, volume, ask_prices, bid_prices, ask_qtys, bid_qtys, timestamp)
                self.current_index += 1
                
        except Exception as e:
            print(f"데이터 로드 오류: {e}")


def main():
    """메인 실행 함수"""
    print("Smart VWAP 실시간 차트 시작 (PyQt5 + PyQtGraph)...")
    print("Smart VWAP 특징:")
    print("- 시간 가중치: 최근 거래에 더 높은 가중치 부여")
    print("- 호가 유동성: 매수/매도 호가 잔량 고려")
    print("- 거래 강도: 초당 거래량 반영")
    print("- 시장 압력: 수급 불균형 감지")
    print()
    
    app = QApplication(sys.argv)
    chart = SmartVWAPChart(False, 0.75, 5, 0.75)
    chart.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
