import sys
import sqlite3
import pyqtgraph as pg
from collections import deque
from PyQt5.QtGui import QFont
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from utility.lazy_imports import get_np, get_pd


class SupplyDemandCalculator:
    def __init__(self, lookback_period=30, min_touches=2, zone_strength_threshold=0.5):
        self.lookback_period = lookback_period
        self.min_touches = min_touches
        self.zone_strength_threshold = zone_strength_threshold
        
        # 데이터 저장
        self.price_data  = deque(maxlen=lookback_period * 2)
        self.volume_data = deque(maxlen=lookback_period * 2)
        
        # Supply/Demand 존 데이터
        self.supply_zones = []
        self.demand_zones = []
        self.price_levels = {}  # 가격 레벨별 터치 횟수 및 볼륨 기록
        
    def add_price_data(self, price, volume):
        """가격 데이터 추가"""
        self.price_data.append(price)
        self.volume_data.append(volume)

        price_level = price
        if price_level not in self.price_levels:
            self.price_levels[price_level] = {
                'touches': 0,
                'total_volume': 0,
                'rejections': 0,
                'breakouts': 0,
                'type': None  # 'supply' or 'demand'
            }
        
        self.price_levels[price_level]['touches'] += 1
        self.price_levels[price_level]['total_volume'] += volume
        
        # Supply/Demand 존 업데이트
        self.identify_supply_demand_zones()
        
    def identify_supply_demand_zones(self):
        """Supply/Demand 존 식별"""
        if len(self.price_data) < self.lookback_period:
            return
        
        recent_prices = list(self.price_data)[-self.lookback_period:]
        recent_volumes = list(self.volume_data)[-self.lookback_period:]
        
        # 가격 레벨 분석
        zones_found = 0
        for price_level, data in self.price_levels.items():
            if data['touches'] < self.min_touches:
                continue
            
            # 가격 레벨 주변 데이터 분석
            level_volumes = []
            current_price = recent_prices[-1] if len(recent_prices) > 0 else price_level
            price_range = current_price * 0.002  # 현재가 대비 0.2% 범위
            
            for i, price in enumerate(recent_prices):
                if abs(price - price_level) < price_range:
                    level_volumes.append(recent_volumes[i])
            
            if len(level_volumes) == 0:
                continue

            avg_volume_at_level = get_np().mean(level_volumes)
            avg_volume_overall = get_np().mean(recent_volumes)

            # Supply 존 조건 (저항선) - 조건 완화
            # noinspection PyTypeChecker
            is_supply = (
                price_level > current_price and  # 현재 가격보다 높음
                data['touches'] >= self.min_touches and  # 최소 터치 횟수 (2회)
                avg_volume_at_level > avg_volume_overall * 1.1 and  # 거래량 조건 완화 (10%만 높아도)
                self.check_rejection_pattern(price_level, recent_prices)  # 반등 패턴
            )

            # Demand 존 조건 (지지선) - 조건 완화
            # noinspection PyTypeChecker
            is_demand = (
                price_level < current_price and  # 현재 가격보다 낮음
                data['touches'] >= self.min_touches and  # 최소 터치 횟수 (2회)
                avg_volume_at_level > avg_volume_overall * 1.1 and  # 거래량 조건 완화 (10%만 높아도)
                self.check_support_pattern(price_level, recent_prices)  # 지지 패턴
            )

            # 존 타입 업데이트
            if is_supply:
                data['type'] = 'supply'
                self.update_supply_zone(price_level, data)
                zones_found += 1

            if is_demand:
                data['type'] = 'demand'
                self.update_demand_zone(price_level, data)
                zones_found += 1
    
    def check_rejection_pattern(self, price_level, prices):
        """가격 반등 패턴 확인 (Supply 존) - 비율 기반"""
        current_price = prices[-1] if len(prices) > 0 else price_level
        price_range = current_price * 0.002  # 현재가 대비 0.2% 범위
        level_prices = [p for p in prices if abs(p - price_level) < price_range]
        if len(level_prices) < 2:
            return False
        
        # 가격이 해당 레벨에서 반등되는 패턴 확인
        rejections = 0
        rejection_threshold = current_price * 0.0005  # 현재가 대비 0.05% 반등 기준
        for i in range(1, len(level_prices)):
            if level_prices[i-1] >= price_level and level_prices[i] < price_level - rejection_threshold:
                rejections += 1
        
        return rejections >= 1
    
    def check_support_pattern(self, price_level, prices):
        """가격 지지 패턴 확인 (Demand 존) - 비율 기반"""
        current_price = prices[-1] if len(prices) > 0 else price_level
        price_range = current_price * 0.002  # 현재가 대비 0.2% 범위
        level_prices = [p for p in prices if abs(p - price_level) < price_range]
        if len(level_prices) < 2:
            return False
        
        # 가격이 해당 레벨에서 지지받는 패턴 확인
        supports = 0
        support_threshold = current_price * 0.0005  # 현재가 대비 0.05% 지지 기준
        for i in range(1, len(level_prices)):
            if level_prices[i-1] <= price_level and level_prices[i] > price_level + support_threshold:
                supports += 1
        
        return supports >= 1
    
    def update_supply_zone(self, price_level, data):
        """Supply 존 업데이트"""
        # 기존 존 확인
        update = False
        for zone in self.supply_zones:
            current_price = self.price_data[-1] if len(self.price_data) > 0 else price_level
            zone_merge_threshold = current_price * 0.002  # 현재가 대비 0.2% 병합 기준
            if abs(zone['price'] - price_level) < zone_merge_threshold:
                # 강도 업데이트
                zone['strength'] = min(zone['strength'] + 0.001, 1.0)
                zone['touches'] = data['touches']
                zone['volume'] = data['total_volume']
                update = True
                break

        # 새로운 Supply 존 추가
        if not update:
            self.supply_zones.append({
                'price': price_level,
                'strength': 0.1,
                'touches': data['touches'],
                'volume': data['total_volume'],
                'created': len(self.price_data)
            })

    def update_demand_zone(self, price_level, data):
        """Demand 존 업데이트"""
        # 기존 존 확인
        update = False
        for zone in self.demand_zones:
            current_price = self.price_data[-1] if len(self.price_data) > 0 else price_level
            zone_merge_threshold = current_price * 0.002  # 현재가 대비 0.3% 병합 기준
            if abs(zone['price'] - price_level) < zone_merge_threshold:
                # 강도 업데이트
                zone['strength'] = min(zone['strength'] + 0.001, 1.0)
                zone['touches'] = data['touches']
                zone['volume'] = data['total_volume']
                update = True
                break

        # 새로운 Demand 존 추가
        if not update:
            self.demand_zones.append({
                'price': price_level,
                'strength': 0.1,
                'touches': data['touches'],
                'volume': data['total_volume'],
                'created': len(self.price_data)
            })
    
    def get_zone_signals(self, current_price):
        """현재 가격 기준 존 신호 분석"""
        signals = []

        # 저항 존 근접 신호
        for zone in self.supply_zones[:2]:
            zone_price = zone['price']
            distance = abs(current_price - zone_price)
            if distance < zone_price * 0.002:
                signals.append({
                    'type': 'supply_resistance',
                    'price': zone_price,
                    'strength': zone['strength'],
                    'distance': distance,
                    'signal': 'SELL' if current_price >= zone_price - zone_price * 0.002 else 'WATCH'
                })

        # 지지 존 근접 신호
        for zone in self.demand_zones[:2]:
            zone_price = zone['price']
            distance = abs(current_price - zone_price)
            if distance < zone_price * 0.002:
                signals.append({
                    'type': 'demand_support',
                    'price': zone_price,
                    'strength': zone['strength'],
                    'distance': distance,
                    'signal': 'BUY' if current_price <= zone_price + zone_price * 0.002 else 'WATCH'
                })
        
        return signals


class SupplyDemandChart(QMainWindow):
    def __init__(self, max_points=1800):
        super().__init__()
        self.max_points = max_points
        
        # Supply/Demand 계산기
        self.sd_calculator = SupplyDemandCalculator()
        
        # 데이터 저장용 deque (속도 우선)
        self.prices     = deque(maxlen=max_points)
        self.volumes    = deque(maxlen=max_points)
        self.timestamps = deque(maxlen=max_points)
        
        # Supply/Demand 데이터
        self.supply_zones = deque(maxlen=10)
        self.demand_zones = deque(maxlen=10)
        self.zone_signals = deque(maxlen=max_points)

        self.signal_plot = None
        self.zone_plot   = None
        self.price_plot  = None
        self.info_label  = None
        
        # 실시간 데이터 생성용 변수
        self.current_price = 0
        self.current_volume = 0
        self.timestamp = ""
        self.code = "005930"  # 삼성전자
        self.data_index = 0
        self.sample_data = []
        
        # UI 초기화
        self.init_ui()
        
        # 데이터 로드
        self.load_sample_data()
        
        # 실시간 업데이트 타이머
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(200)
        
        # 초기 데이터 표시
        self.update_plots()
    
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("지지/저항 Zones 실시간 차트")
        self.setGeometry(100, 100, 1500, 1000)
        
        # 메인 위젯 및 레이아웃
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_widget.setStyleSheet("background-color: black;")  # 메인 배경 검은색
        main_layout = QVBoxLayout(main_widget)
        
        # 정보 라벨
        self.info_label = QLabel()
        self.info_label.setFont(QFont("Malgun Gothic", 10))
        self.info_label.setStyleSheet("background-color: #333333; color: white; padding: 10px; border-radius: 5px; border: 1px solid #555555;")
        main_layout.addWidget(self.info_label)
        
        # 가격 차트 (지지/저항 존 오버레이)
        self.price_plot = pg.PlotWidget(title="가격 & 지지/저항 Zones")
        self.price_plot.setLabel('left', '가격', units='원')
        self.price_plot.setLabel('bottom', '시간')
        self.price_plot.showGrid(x=True, y=True, alpha=0.3)
        self.price_plot.setBackground('k')
        self.price_plot.addLegend()
        main_layout.addWidget(self.price_plot)
        
        # 신호 차트
        self.signal_plot = pg.PlotWidget(title="존 근접 신호")
        self.signal_plot.setLabel('left', '신호 강도')
        self.signal_plot.setLabel('bottom', '시간')
        self.signal_plot.showGrid(x=True, y=True, alpha=0.3)
        self.signal_plot.setBackground('k')
        self.signal_plot.addLegend()
        self.signal_plot.setMaximumHeight(250)
        main_layout.addWidget(self.signal_plot)
    
    def load_sample_data(self):
        """샘플 데이터 로드"""
        try:
            conn = sqlite3.connect('../_database/stock_tick_back.db')
            df = get_pd().read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", conn)
            stock_codes = df['name'].to_list()
            stock_codes.remove('moneytop')
            stock_codes.remove('stockinfo')

            while True:
                self.code = get_np().random.choice(stock_codes)
                df = get_pd().read_sql(f"SELECT `index`, 현재가, 초당매수수량, 초당매도수량, 관심종목 FROM '{self.code}'", conn)
                lastday = int(str(df['index'].iloc[-1])[:8]) * 1000000
                df = df[df['index'] >= lastday]
                if len(df[df['관심종목'] == 1]) >= len(df) * 0.7:
                    break

            conn.close()
            df['체결수량'] = df['초당매수수량'] + df['초당매도수량']
            df = df[['index', '현재가', '체결수량']]
            self.sample_data = df.to_dict('records')
            print(f"샘플 데이터 {len(self.sample_data)}개 로드 완료")
            
        except Exception as e:
            print(f"데이터 로드 오류: {e}")
            # 더미 데이터 생성
            import random
            base_price = 80000
            for i in range(1000):
                price = base_price + random.uniform(-2000, 2000)
                volume = random.uniform(100, 10000)
                self.sample_data.append({
                    'index': f'2024-01-01 09:{i//60:02d}:{i%60:02d}',
                    '현재가': price,
                    '체결수량': volume
                })
    
    def update_data(self):
        """실시간 데이터 업데이트"""
        if self.data_index >= len(self.sample_data):
            self.data_index = 0  # 데이터 순환
        
        data = self.sample_data[self.data_index]
        price = data['현재가']
        volume = data['체결수량']
        t = str(data['index'])
        timestamp = f'{t[:4]}-{t[4:6]}-{t[6:8]} {t[8:10]}:{t[10:12]}:{t[12:]}'
        
        self.current_price = price
        self.current_volume = volume
        self.timestamp = timestamp
        
        # 데이터 추가
        self.prices.append(price)
        self.volumes.append(volume)
        self.timestamps.append(timestamp)
        
        # Supply/Demand 계산기에 데이터 추가
        self.sd_calculator.add_price_data(price, volume)
        
        # 존 신호 분석
        signals = self.sd_calculator.get_zone_signals(price)
        self.zone_signals.append(signals)
        
        # Supply/Demand 존 데이터 업데이트
        self.supply_zones.clear()
        self.demand_zones.clear()
        
        for zone in self.sd_calculator.supply_zones:
            self.supply_zones.append(zone)
        
        for zone in self.sd_calculator.demand_zones:
            self.demand_zones.append(zone)
        
        # 차트 업데이트
        self.update_plots()
        
        self.data_index += 1
    
    def update_plots(self):
        """모든 그래프 업데이트"""
        if len(self.prices) > 1:
            x_indices = list(range(len(self.prices)))
            
            # 가격 차트 업데이트
            self.price_plot.clear()
            self.price_plot.plot(x_indices, list(self.prices),
                                 pen=pg.mkPen('lime', width=2), name='현재가')

            # 지지 존 표시 (빨간색 영역) - 마지막 업데이트된 2개 표시
            if len(self.demand_zones) > 0:
                last_demand_zones = sorted(self.demand_zones, key=lambda x: x['strength'], reverse=True)[:2]
                for zone in last_demand_zones:
                    zone_price = zone['price']
                    zone_strength = zone['strength']

                    # 수평선으로 지지 존 표시
                    self.price_plot.plot([0, len(self.prices)-1], [zone_price, zone_price],
                                         pen=pg.mkPen('red', width=1 + int(zone_strength * 4), style=2),
                                         name=f'지지선 {zone_price:.0f}')

                    # 지지 존 영역 채우기
                    zone_width = zone_price * zone_strength * 2 / 1000
                    fill_upper = pg.PlotDataItem(x=[0, len(self.prices)-1],
                                                 y=[zone_price + zone_width, zone_price + zone_width])
                    fill_lower = pg.PlotDataItem(x=[0, len(self.prices)-1],
                                                 y=[zone_price - zone_width, zone_price - zone_width])
                    fill_item = pg.FillBetweenItem(fill_upper, fill_lower,
                                                   brush=pg.mkBrush(255, 0, 0, int(70 * zone_strength)))
                    self.price_plot.addItem(fill_item)
                    
                    # 지지선 정보 텍스트 표시
                    info_text = f'지지선: {zone_price:.0f} 강도: {zone_strength*100:.1f}%'
                    text_item = pg.TextItem(info_text, color='w', anchor=(0, 0.5))
                    text_item.setPos(len(self.prices) * 0.3, zone_price - zone_price * 0.001)
                    text_item.setFont(QFont("Arial", 9))
                    self.price_plot.addItem(text_item)

            # 저항 존 표시 (파란색 영역) - 마지막 업데이트된 2개 표시
            if len(self.supply_zones) > 0:
                last_supply_zones = sorted(self.supply_zones, key=lambda x: x['strength'], reverse=True)[:2]
                for zone in last_supply_zones:
                    zone_price = zone['price']
                    zone_strength = zone['strength']

                    # 수평선으로 저항 존 표시
                    self.price_plot.plot([0, len(self.prices)-1], [zone_price, zone_price],
                                         pen=pg.mkPen('blue', width=1 + int(zone_strength * 4), style=2),
                                         name=f'저항선 {zone_price:.0f}')

                    # 저항 존 영역 채우기
                    zone_width = zone_price * zone_strength * 2 / 1000
                    fill_upper = pg.PlotDataItem(x=[0, len(self.prices)-1],
                                                 y=[zone_price + zone_width, zone_price + zone_width])
                    fill_lower = pg.PlotDataItem(x=[0, len(self.prices)-1],
                                                 y=[zone_price - zone_width, zone_price - zone_width])
                    fill_item = pg.FillBetweenItem(fill_upper, fill_lower,
                                                   brush=pg.mkBrush(0, 0, 255, int(70 * zone_strength)))
                    self.price_plot.addItem(fill_item)
                    
                    # 저항선 정보 텍스트 표시
                    info_text = f'저항선: {zone_price:.0f} 강도: {zone_strength*100:.1f}%'
                    text_item = pg.TextItem(info_text, color='w', anchor=(0, 0.5))
                    text_item.setPos(len(self.prices) * 0.6, zone_price - zone_price * 0.001)
                    text_item.setFont(QFont("Arial", 9))
                    self.price_plot.addItem(text_item)
            
            # 현재가 강조
            self.price_plot.plot([len(self.prices)-1], [self.current_price],
                                 pen=None, symbol='o', symbolBrush='yellow', symbolSize=10)
            
            # 신호 차트 업데이트
            self.signal_plot.clear()
            
            # 신호 강도 계산 (최근 데이터만 처리로 속도 최적화)
            signal_strengths = []
            recent_signals = list(self.zone_signals)[-100:]  # 최근 100개만 처리
            
            for i, signals in enumerate(recent_signals):
                max_strength = 0
                signal_type = 'NEUTRAL'
                
                for signal in signals:
                    if signal['strength'] > max_strength:
                        max_strength = signal['strength']
                        signal_type = signal['signal']
                
                signal_strengths.append(max_strength * 100 if signal_type != 'NEUTRAL' else 0)
                
                # 신호 마커 표시
                if max_strength > 0:
                    color = 'blue' if signal_type == 'SELL' else 'red' if signal_type == 'BUY' else 'yellow'
                    actual_index = len(self.zone_signals) - len(recent_signals) + i
                    self.signal_plot.plot([actual_index], [max_strength * 100], pen=None,
                                          symbol='t' if signal_type == 'SELL' else 't1' if signal_type == 'BUY' else 'o',
                                          symbolBrush=pg.mkBrush(color), symbolSize=12)
            
            if len(signal_strengths) > 0:
                # X축 인덱스도 최근 데이터에 맞춰서 생성
                recent_x_indices = list(range(len(self.zone_signals)))[-len(signal_strengths):]
                self.signal_plot.plot(recent_x_indices, signal_strengths,
                                      pen=pg.mkPen('cyan', width=2), name='신호 강도')
            
            # X축 시간 표시
            step = max(1, len(self.timestamps) // 10)
            x_ticks = list(range(0, len(self.timestamps), step))
            x_labels = [self.timestamps[i][11:19] for i in x_ticks]
            ax = self.price_plot.getAxis('bottom')
            ax.setTicks([list(zip(x_ticks, x_labels))])
            ax2 = self.signal_plot.getAxis('bottom')
            ax2.setTicks([list(zip(x_ticks, x_labels))])

            # 정보 업데이트
            self.update_info()
    
    def update_info(self):
        """정보 라벨 업데이트"""
        current_price = self.current_price
        
        # 현재 가장 가까운 존 정보
        nearest_supply = None
        nearest_demand = None
        min_supply_distance = float('inf')
        min_demand_distance = float('inf')
        
        for zone in self.supply_zones:
            distance = abs(current_price - zone['price'])
            if distance < min_supply_distance:
                min_supply_distance = distance
                nearest_supply = zone
        
        for zone in self.demand_zones:
            distance = abs(current_price - zone['price'])
            if distance < min_demand_distance:
                min_demand_distance = distance
                nearest_demand = zone
        
        # 체결시간 포맷팅 (int 형식을 HH:MM으로 변환)
        time_str = str(self.timestamp)
        if len(time_str) == 12 and time_str.isdigit():  # 20260218093000 형식
            hour = int(time_str[8:10])
            minute = int(time_str[10:12])
            formatted_time = f"{hour:02d}:{minute:02d}"
        else:
            formatted_time = time_str
        
        # 정보 텍스트 생성
        info_text = (f'종목코드: {self.code} | '
                     f'현재가: {current_price:,.0f} | '
                     f'저항 존: {len(self.supply_zones)}개 | '
                     f'지지 존: {len(self.demand_zones)}개')
        
        if nearest_supply:
            info_text += f' | 가까운 저항: {nearest_supply["price"]:,.0f} ({min_supply_distance:.0f}원)'
        
        if nearest_demand:
            info_text += f' | 가까운 지지: {nearest_demand["price"]:,.0f} ({min_demand_distance:.0f}원)'
        
        info_text += f' | 체결시간: {formatted_time}'
        
        self.info_label.setText(info_text)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    chart = SupplyDemandChart()
    chart.show()
    sys.exit(app.exec_())
