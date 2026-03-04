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
"""

import sys
import sqlite3
import numpy as np
import pandas as pd
import pyqtgraph as pg
from PyQt5.QtGui import QFont
from PyQt5.QtCore import QTimer
from collections import defaultdict, deque
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel

# 주식 틱 데이터 칼럼
list_stock_tick = [
    'index', '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '체결강도', '초당매수수량', '초당매도수량',
    '거래대금증감', '전일비', '회전율', '전일동시간비', '시가총액', '라운드피겨위5호가이내', 'VI해제시간', 'VI가격', 'VI호가단위',
    '초당거래대금', '고저평균대비등락율', '저가대비고가등락율', '초당매수금액', '초당매도금액',
    '당일매수금액', '최고매수금액', '최고매수가격', '당일매도금액', '최고매도금액', '최고매도가격',
    '매도호가5', '매도호가4', '매도호가3', '매도호가2', '매도호가1', '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5',
    '매도잔량5', '매도잔량4', '매도잔량3', '매도잔량2', '매도잔량1', '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5',
    '매도총잔량', '매수총잔량', '매도수5호가잔량합', '관심종목'
]


class SmartVWAPCalculator:
    """Smart VWAP 계산기 클래스"""
    
    def __init__(self, market_type: str = 'stock', decay_factor=0.95, liquidity_weight=0.3, pressure_weight=0.2):
        """
        Smart VWAP 계산기 초기화
        
        Args:
            market_type: 'stock', 'coin', 'future' (시장 종류)
            decay_factor: 시간 가중치 감쇠 계수 (0.95 = 과거 데이터에 5% 더 높은 가중치)
            liquidity_weight: 유동성 가중치 (0.0-1.0)
            pressure_weight: 시장 압력 가중치 (0.0-1.0)
        """
        self.market_type      = market_type
        self.decay_factor     = decay_factor
        self.liquidity_weight = liquidity_weight
        self.pressure_weight  = pressure_weight

        # 종목별 데이터 저장용 딕셔너리
        self.price_volume_data  = defaultdict(lambda: deque(maxlen=1800))
        self.smart_vwap_history = defaultdict(lambda: deque(maxlen=30))

    def calculate_smart_vwap(self, code, price, volume, ask_prices, bid_prices, ask_qtys, bid_qtys,
                             total_bid_qtys, total_ask_qtys, period=30, std_multiplier=2.0):
        """
        Smart VWAP, 밴드 계산

        Args:
            code: 종목코드
            price: 현재가
            volume: 거래량
            ask_prices: 매도호가 배열
            bid_prices: 매수호가 배열
            ask_qtys: 매도잔량 배열
            bid_qtys: 매수잔량 배열
            total_bid_qtys: 매수총잔량
            total_ask_qtys: 매도총잔량
            period: 기간 (기본 30)
            std_multiplier: 표준편차 배수 (기본 2.0)

        Returns:
            Smart VWAP, 상단밴드, 하단밴드
        """
        # 디큐에 데이터 추가
        code_data_deque = self.price_volume_data[code]
        code_data_deque.append((price, volume))

        if len(code_data_deque) < 2:
            return price, price, price

        # 시간 가중치 적용 VWAP
        weighted_price_sum = 0
        weighted_volume_sum = 0

        for i, (p, v) in enumerate(code_data_deque):
            # 시간 가중치 (최근일수록 낮은 가중치)
            time_weight = self.decay_factor ** (len(code_data_deque) - i - 1)
            weighted_price_sum += p * v * time_weight
            weighted_volume_sum += v * time_weight

        time_weighted_vwap = weighted_price_sum / weighted_volume_sum if weighted_volume_sum > 0 else price

        # 유동성 압력 계산
        total_liquidity = total_bid_qtys + total_ask_qtys
        if total_liquidity == 0:
            liquidity_adjustment = 0.0
        else:
            liquidity_imbalance = (total_bid_qtys - total_ask_qtys) / total_liquidity
            liquidity_adjustment = liquidity_imbalance * 0.001

        # 시장 압력 계산
        buy_pressure = sum(q * (1 - (price - p) / price) for p, q in zip(bid_prices, bid_qtys) if p < price and q > 0)
        sell_pressure = sum(q * (1 - (p - price) / price) for p, q in zip(ask_prices, ask_qtys) if p > price and q > 0)
        total_pressure = buy_pressure + sell_pressure
        if total_pressure == 0:
            pressure_adjustment = 0.0
        else:
            net_pressure = (buy_pressure - sell_pressure) / total_pressure
            pressure_adjustment = net_pressure * 0.002  # 최대 ±0.2% 조정

        # Smart VWAP = 시간가중VWAP + 유동성조정 + 압력조정
        smart_vwap = time_weighted_vwap
        smart_vwap += liquidity_adjustment * self.liquidity_weight * price
        smart_vwap += pressure_adjustment * self.pressure_weight * price

        # Smart VWAP 히스토리 저장 (밴드 계산용)
        code_vwap_deque = self.smart_vwap_history[code]
        code_vwap_deque.append(smart_vwap)

        if len(code_vwap_deque) < period:
            return smart_vwap, smart_vwap, smart_vwap

        # 최근 period개 Smart VWAP 데이터
        recent_vwaps = list(code_vwap_deque)
        # 중간선 (이동평균)
        middle = np.mean(recent_vwaps)
        # 표준편차
        std = np.std(recent_vwaps)
        # 상단/하단 밴드
        # noinspection PyTypeChecker
        upper = middle + (std * std_multiplier)
        # noinspection PyTypeChecker
        lower = middle - (std * std_multiplier)

        return smart_vwap, upper, lower


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
            pressure_weight=0.15    # 시장 압력 가중치
        )
        
        # 데이터 저장용 deque (속도 우선)
        self.prices      = deque(maxlen=max_points)
        self.volumes     = deque(maxlen=max_points)
        self.timestamps  = deque(maxlen=max_points)
        
        # Smart VWAP 데이터
        self.smart_vwaps = deque(maxlen=max_points)     # Smart VWAP
        self.upper_bands = deque(maxlen=max_points)     # 상단 밴드
        self.lower_bands = deque(maxlen=max_points)     # 하단 밴드
        self.trade_data  = deque(maxlen=max_points)     # 신호 저장

        self.first_draw  = True
        self.draw_items  = {}
        self.chuse_item  = []
        
        # 실시간 데이터 생성용 변수
        self.current_index = 0
        self.arry_data     = None
        
        # 종목 정보
        self.code          = None
        self.current_price = None
        self.timestamp     = None
        self.current_date  = None
        self.change_rate   = None
        self.trade_state   = None
        
        # UI 컴포넌트
        self.price_plot    = None
        self.info_label    = None

        # 칼럼 설정
        self._setup_columns()
        
        # UI 초기화
        self.init_ui()
        
        # 데이터 로드
        self.load_sample_data()
        
        # 타이머 설정
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(100)

    def _setup_columns(self):
        """
        시장 및 데이터 타입에 따른 칼럼 설정
        """
        # 칼럼 인덱스 매핑 (빠른 접근용)
        self.col_index = {col: idx for idx, col in enumerate(list_stock_tick)}
    
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

    def add_data(self, code, data):
        """새로운 데이터 추가"""
        price  = data[self.col_index['현재가']]
        volume = data[self.col_index['초당매수수량']] + data[self.col_index['초당매도수량']]

        ask_prices = [
            data[self.col_index['매도호가1']],
            data[self.col_index['매도호가2']],
            data[self.col_index['매도호가3']],
            data[self.col_index['매도호가4']],
            data[self.col_index['매도호가5']]
        ]

        bid_prices = [
            data[self.col_index['매수호가1']],
            data[self.col_index['매수호가2']],
            data[self.col_index['매수호가3']],
            data[self.col_index['매수호가4']],
            data[self.col_index['매수호가5']]
        ]

        ask_qtys = [
            data[self.col_index['매도잔량1']],
            data[self.col_index['매도잔량2']],
            data[self.col_index['매도잔량3']],
            data[self.col_index['매도잔량4']],
            data[self.col_index['매도잔량5']]
        ]

        bid_qtys = [
            data[self.col_index['매수잔량1']],
            data[self.col_index['매수잔량2']],
            data[self.col_index['매수잔량3']],
            data[self.col_index['매수잔량4']],
            data[self.col_index['매수잔량5']]
        ]

        total_bid_qtys = data[self.col_index['매수총잔량']]
        total_ask_qtys = data[self.col_index['매도총잔량']]

        self.prices.append(price)
        self.volumes.append(volume)
        self.timestamps.append(self.timestamp)

        # Smart VWAP 계산
        smart_vwap, upper_band, lower_band = self.vwap_calculator.calculate_smart_vwap(
            code, price, volume, ask_prices, bid_prices, ask_qtys, bid_qtys, total_bid_qtys, total_ask_qtys
        )

        # 돌파 상태 감지
        trade_state = None
        if upper_band != lower_band:
            # 상단 밴드 돌파 감지
            if self.trade_state is None and smart_vwap > upper_band:
                band_width_ratio = (upper_band - lower_band) / price * 100                  # 현재가 대비 밴드폭 비율
                strength = (smart_vwap - upper_band) / (upper_band - lower_band) * 100      # 밴드폭 대비 돌파 강도(%)
                if band_width_ratio >= self.width_limit and strength >= self.strength_limit:
                    trade_state = 'BUY'
                    self.trade_state = 'BUY'
            # 현재가가 Smart VWAP 아래인 경우 매도신호
            elif self.trade_state == 'BUY' and price < upper_band:
                pct = (price / upper_band - 1) * 100
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
            elif self.twoway and self.trade_state == 'SELL' and price > lower_band:
                pct = (price / lower_band - 1) * 100
                if pct >= self.sell_limit:
                    trade_state = 'BUY'
                    self.trade_state = None

        self.smart_vwaps.append(smart_vwap)
        self.upper_bands.append(upper_band)
        self.lower_bands.append(lower_band)
        self.trade_data.append(trade_state)

        if len(self.smart_vwaps) >= 2:
            fill_item = None
            list_smart_vwaps = list(self.smart_vwaps)
            list_upper_bands = list(self.upper_bands)
            list_lower_bands = list(self.lower_bands)
            if smart_vwap > upper_band or list_smart_vwaps[-2] > list_upper_bands[-2]:
                brush_color = (255, 100, 100, 80)
                curve_upper = pg.PlotDataItem(x=[self.current_index - 1, self.current_index], y=[list_smart_vwaps[self.current_index - 1], list_smart_vwaps[self.current_index]])
                curve_lower = pg.PlotDataItem(x=[self.current_index - 1, self.current_index], y=[list_upper_bands[self.current_index - 1], list_upper_bands[self.current_index]])
                fill_item = pg.FillBetweenItem(curve_upper, curve_lower, brush=brush_color)
            elif smart_vwap < lower_band or list_smart_vwaps[-2] < list_lower_bands[-2]:
                brush_color = (100, 100, 255, 80)
                curve_upper = pg.PlotDataItem(x=[self.current_index - 1, self.current_index], y=[list_lower_bands[self.current_index - 1], list_lower_bands[self.current_index]])
                curve_lower = pg.PlotDataItem(x=[self.current_index - 1, self.current_index], y=[list_smart_vwaps[self.current_index - 1], list_smart_vwaps[self.current_index]])
                fill_item = pg.FillBetweenItem(curve_upper, curve_lower, brush=brush_color)

            if fill_item is not None:
                self.chuse_item.append(fill_item)

    def update_data(self):
        """데이터 업데이트 및 그래프 갱신"""
        if self.arry_data is not None and self.current_index < len(self.arry_data):
            # 다음 데이터 추가
            data = self.arry_data[self.current_index]

            t = str(int(data[self.col_index['index']]))[:-2]
            self.timestamp = f'{t[:4]}-{t[4:6]}-{t[6:8]} {t[8:10]}:{t[10:12]}:{t[12:]}'
            self.current_price = data[self.col_index['현재가']]
            self.change_rate = data[self.col_index['등락율']]

            # 일자 변경 감지
            new_date = self.timestamp[:10]
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

            self.add_data('000000', data)
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
                self.draw_items[1] = self.price_plot.plot(x_indices, list(self.upper_bands), pen=pg.mkPen('skyblue', width=1, style=2), name='상단밴드')
                self.draw_items[2] = self.price_plot.plot(x_indices, list(self.lower_bands), pen=pg.mkPen('skyblue', width=1, style=2), name='하단밴드')
                self.draw_items[3] = self.price_plot.plot(x_indices, list(self.smart_vwaps), pen=pg.mkPen('orange', width=1), name='Smart VWAP')
                self.draw_items[4] = self.price_plot.plot(x_indices, list(self.prices), pen=pg.mkPen('lime', width=2), name='현재가')
                self.draw_items[5] = self.price_plot.plot([len(self.prices)-1], [self.current_price], pen=None, symbol='o', symbolBrush='yellow', symbolSize=10)
            else:
                self.draw_items[1].setData(x_indices, list(self.upper_bands), pen=pg.mkPen('skyblue', width=1, style=2), name='상단밴드')
                self.draw_items[2].setData(x_indices, list(self.lower_bands), pen=pg.mkPen('skyblue', width=1, style=2), name='하단밴드')
                self.draw_items[3].setData(x_indices, list(self.smart_vwaps), pen=pg.mkPen('orange', width=1), name='Smart VWAP')
                self.draw_items[4].setData(x_indices, list(self.prices), pen=pg.mkPen('lime', width=2), name='현재가')
                self.draw_items[5].setData([len(self.prices)-1], [self.current_price], pen=None, symbol='o', symbolBrush='yellow', symbolSize=10)
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
            conn = sqlite3.connect('../../_database/stock_tick_back.db')
            df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", conn)
            codes = df['name'].to_list()
            codes.remove('moneytop')
            if 'stockinfo' in codes: codes.remove('stockinfo')
            if 'futureinfo' in codes: codes.remove('futureinfo')

            while True:
                self.code = np.random.choice(codes)
                df = pd.read_sql(f"SELECT * FROM '{self.code}'", conn)
                lastday = int(str(df['index'].iloc[-1])[:8]) * 1000000
                df = df[df['index'] >= lastday]
                if df['고저평균대비등락율'].max() >= 7:
                    break

            conn.close()
            print(f"선택된 종목: {self.code}")
            print(f"데이터 로드 완료: {len(df)}개")

            self.arry_data = np.array(df)
            self.current_index = 0

            # 초기 데이터 10개 추가
            for data in self.arry_data[:10]:
                t = str(int(data[self.col_index['index']]))[:-2]
                self.timestamp = f'{t[:4]}-{t[4:6]}-{t[6:8]} {t[8:10]}:{t[10:12]}:{t[12:]}'
                self.current_price = data[self.col_index['현재가']]
                self.change_rate = data[self.col_index['등락율']]
                self.add_data(self.code, data)
                self.current_index += 1
        except Exception as e:
            print(f"데이터 로드 오류: {e}")


def main():
    """메인 실행 함수"""
    print("Smart VWAP 실시간 차트 시작 (PyQt5 + PyQtGraph)...")
    print("Smart VWAP 특징:")
    print("- 시간 가중치: 최근 거래에 더 낮은 가중치 부여")
    print("- 호가 유동성: 매수/매도 호가 잔량 고려")
    print("- 호가 압력: 총잔량 수급 불균형 감지")
    print()
    
    app = QApplication(sys.argv)
    chart = SmartVWAPChart(False, 0.7, 5, 0.7)
    chart.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
