
import numpy as np
from typing import Dict, List
from collections import deque
from datetime import datetime, timedelta


class ManipulationDetector:

    def __init__(self):
        self.data_cnt = 10
        self.dict_orderbook_history = {}
        self.dict_price_history     = {}
        self.dict_volume_history    = {}
        self.pump_threshold = 0.05
        self.volume_spike_threshold = 3.0

    def get_all_manipulations(self, code: str, orderbook_data: np.ndarray, volume_data: np.ndarray = None) -> Dict[str, List]:
        timestamp = datetime.now()

        if code not in self.dict_orderbook_history:
            self.dict_orderbook_history[code] = deque(maxlen=self.data_cnt)
            self.dict_price_history[code]     = deque(maxlen=self.data_cnt)
            self.dict_volume_history[code]    = deque(maxlen=self.data_cnt)

        self.dict_orderbook_history[code].append({
            'timestamp': timestamp,
            'data': orderbook_data.copy()
        })

        ask_prices = orderbook_data[0:5]
        bid_prices = orderbook_data[5:10]
        mid_price = (ask_prices[0] + bid_prices[0]) / 2
        self.dict_price_history[code].append(mid_price)

        buy_volume = volume_data[0]
        sell_volume = volume_data[1]
        self.dict_volume_history[code].append({
            'timestamp': timestamp,
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'total_volume': buy_volume + sell_volume
        })

        layering = self.detect_layering(code)
        pump_dump = self.detect_pump_dump(code)
        overall_risk = self.calculate_overall_risk(layering, pump_dump)

        return {
            'layering': layering,
            'pump_dump': pump_dump,
            'overall_risk': overall_risk
        }
    
    def detect_layering(self, code: str) -> List[Dict]:
        layering_signals = []
        
        if len(self.dict_orderbook_history[code]) < self.data_cnt:
            return layering_signals

        recent_orderbooks = list(self.dict_orderbook_history[code])

        for side in ['ask', 'bid']:
            suspicious_levels = self._analyze_price_levels(recent_orderbooks, side)

            large_order_changes = self._detect_large_order_changes(recent_orderbooks, side)
            
            if suspicious_levels or large_order_changes:

                layering_confidence = self._calculate_layering_confidence(suspicious_levels)
                spoofing_confidence = self._calculate_spoofing_confidence_from_changes(large_order_changes)

                combined_confidence = max(layering_confidence, spoofing_confidence)
                if suspicious_levels and large_order_changes:
                    combined_confidence = min((layering_confidence + spoofing_confidence) / 2 * 1.2, 1.0)
                
                layering_signals.append({
                    'type': 'layering',
                    'side': side,
                    'levels': suspicious_levels,
                    'large_changes': large_order_changes,
                    'confidence': combined_confidence,
                    'timestamp': recent_orderbooks[-1]['timestamp']
                })
        
        return layering_signals
    
    def _analyze_price_levels(self, orderbooks: List, side: str) -> List[Dict]:
        level_analysis = {}
        
        for ob in orderbooks:
            data = ob['data']
            
            if side == 'ask':
                prices = data[0:5]
                quantities = data[10:15]
            else:
                prices = data[5:10]
                quantities = data[15:20]

            for price, qty in zip(prices, quantities):
                if qty > 0:
                    if price not in level_analysis:
                        level_analysis[price] = {
                            'total_quantity': 0,
                            'occurrences': 0,
                            'quantities': []
                        }
                    level_analysis[price]['total_quantity'] += qty
                    level_analysis[price]['occurrences'] += 1
                    level_analysis[price]['quantities'].append(qty)

        suspicious_levels = []
        for price, analysis in level_analysis.items():
            avg_qty = analysis['total_quantity'] / analysis['occurrences']
            max_qty = max(analysis['quantities'])

            if max_qty > avg_qty * 3 and analysis['occurrences'] >= 3:
                suspicious_levels.append({
                    'price': price,
                    'avg_quantity': avg_qty,
                    'max_quantity': max_qty,
                    'occurrences': analysis['occurrences'],
                    'suspicion_score': min(max_qty / (avg_qty + 1e-8) / 3, 10.0)
                })
        
        return suspicious_levels

    def _detect_large_order_changes(self, orderbooks: List, side: str) -> List[Dict]:
        changes = []

        if len(orderbooks) < 3:
            return changes

        for i in range(1, len(orderbooks)):
            prev_data = orderbooks[i-1]['data']
            curr_data = orderbooks[i]['data']

            if side == 'ask':
                prev_quantities = prev_data[10:15]
                curr_quantities = curr_data[10:15]
                prices = curr_data[0:5]
            else:
                prev_quantities = prev_data[15:20]
                curr_quantities = curr_data[15:20]
                prices = curr_data[5:10]

            for level, (prev_qty, curr_qty, price) in enumerate(zip(prev_quantities, curr_quantities, prices)):
                qty_change = abs(curr_qty - prev_qty)

                if max(prev_qty, curr_qty) > 0 and qty_change / max(prev_qty, curr_qty) > 0.5:
                    changes.append({
                        'level': level,
                        'price': price,
                        'prev_quantity': prev_qty,
                        'curr_quantity': curr_qty,
                        'change_amount': qty_change,
                        'change_ratio': qty_change / max(prev_qty, curr_qty),
                        'timestamp': orderbooks[i]['timestamp']
                    })

        return changes
    
    def _calculate_layering_confidence(self, levels: List[Dict]) -> float:
        """레이어링 신뢰도 계산"""
        if not levels:
            return 0.0

        max_suspicion_score = max(level['suspicion_score'] for level in levels)
        avg_suspicion_score = sum(level['suspicion_score'] for level in levels) / len(levels)

        max_occurrences = max(level['occurrences'] for level in levels)
        occurrence_weight = min(max_occurrences / 10.0, 1.0)

        confidence = (max_suspicion_score * 0.6 + avg_suspicion_score * 0.4) * occurrence_weight
        return min(confidence, 1.0)

    def _calculate_spoofing_confidence_from_changes(self, changes: List[Dict]) -> float:
        """변동 기반 스푸핑 신뢰도 계산"""
        if not changes:
            return 0.0

        max_change_ratio = max(change['change_ratio'] for change in changes)
        avg_change_ratio = sum(change['change_ratio'] for change in changes) / len(changes)

        change_count_weight = min(len(changes) / 5.0, 1.0)

        confidence = (max_change_ratio * 0.6 + avg_change_ratio * 0.4) * change_count_weight
        return min(confidence, 1.0)
    
    def detect_pump_dump(self, code: str) -> List[Dict]:
        """펌프 앤 덤프 탐지"""
        pump_dump_signals = []

        if len(self.dict_price_history[code]) < self.data_cnt:
            return pump_dump_signals

        prices = np.array(list(self.dict_price_history[code]))
        price_changes = np.where(prices[:-1] > 0, np.diff(prices) / prices[:-1] * 100, 0)

        volume_spikes = self._detect_volume_spikes(code)

        for i in range(len(price_changes)):
            if (abs(price_changes[i]) > self.pump_threshold and
                    i < len(volume_spikes) and volume_spikes[i] > self.volume_spike_threshold):
                
                if self._is_pump_dump_pattern(prices, i):
                    pump_dump_signals.append({
                        'type': 'pump_dump',
                        'timestamp': datetime.now() - timedelta(seconds=len(price_changes)-i),
                        'price_change': price_changes[i],
                        'volume_spike': volume_spikes[i],
                        'confidence': self._calculate_pump_confidence(price_changes[i], volume_spikes[i])
                    })
        
        return pump_dump_signals
    
    def _detect_volume_spikes(self, code: str) -> List[float]:
        volumes = [v['total_volume'] for v in self.dict_volume_history[code]]
        spikes = []

        avg_volume = np.mean(volumes)
        for i, volume in enumerate(volumes):
            # noinspection PyTypeChecker
            spike_ratio = volume / (avg_volume + 1e-8)
            spikes.append(spike_ratio)

        return spikes
    
    def _is_pump_dump_pattern(self, prices: np.ndarray, index: int) -> bool:
        if index < 10:
            return False

        window = 10
        if index + window < len(prices):
            before = prices[index-window:index]
            after = prices[index:index+window]

            # noinspection PyTypeChecker
            if np.mean(after) < np.mean(before) * 0.95 and prices[index] > np.mean(before) * 1.05:
                return True
        
        return False
    
    def _calculate_pump_confidence(self, price_change: float, volume_spike: float) -> float:
        price_score = min(abs(price_change) / 0.1, 1.0)
        volume_score = min(volume_spike / 5.0, 1.0)
        return (price_score + volume_score) / 2.0
    
    def calculate_overall_risk(self, layering_signals, pump_dump_signals) -> Dict:
        all_signals = {
            'layering': layering_signals,
            'pump_dump': pump_dump_signals
        }

        total_signals = sum(len(signals) for signals in all_signals.values() if isinstance(signals, list))

        max_confidence = 0
        for signals in all_signals.values():
            if isinstance(signals, list):
                for signal in signals:
                    if 'confidence' in signal:
                        max_confidence = max(max_confidence, signal['confidence'])

        if total_signals == 0:
            risk_level = 'LOW'
        elif total_signals <= 2 and max_confidence < 0.8:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'HIGH'
        
        return {
            'risk_level': risk_level,
            'total_signals': total_signals,
            'max_confidence': max_confidence,
            'timestamp': datetime.now()
        }
