
import numpy as np
from typing import Dict
from collections import deque


class OrderBookAnalyzer:
    def __init__(self):
        self.data_cnt = 10
        self.dict_orderbook_history = {}
        self.dict_spread_history = {}

    def get_market_state(self, code: str, orderbook_data: np.ndarray) -> Dict:
        metrics = self.calculate_depth_metrics(code, orderbook_data)
        pressure = self.detect_liquidity_pressure(code, metrics)

        return {
            'metrics': metrics,
            'pressure': pressure,
            'timestamp': np.datetime64('now')
        }

    def calculate_depth_metrics(self, code: str, orderbook_data: np.ndarray) -> Dict:
        ask_prices = orderbook_data[0:5]
        bid_prices = orderbook_data[5:10]
        ask_quantities = orderbook_data[10:15]
        bid_quantities = orderbook_data[15:20]
        best_bid = bid_prices[0]
        best_ask = ask_prices[0]

        if best_bid == 0 or best_ask == 0:
            return {
                'spread': 0,
                'spread_pct': 0,
                'imbalance': 0,
                'vwap_bid': 0,
                'vwap_ask': 0,
                'bid_concentration': 0,
                'ask_concentration': 0,
                'depth_ratio': 0,
                'total_bid_depth': 0,
                'total_ask_depth': 0,
                'data_valid': False
            }

        spread = best_ask - best_bid
        spread_pct = (spread / best_bid) * 100

        total_bid_qty = sum(bid_quantities)
        total_ask_qty = sum(ask_quantities)
        imbalance = (total_bid_qty - total_ask_qty) / (total_bid_qty + total_ask_qty)

        vwap_bid = self._calculate_vwap(bid_prices, bid_quantities)
        vwap_ask = self._calculate_vwap(ask_prices, ask_quantities)

        bid_concentration = self._calculate_concentration(bid_quantities)
        ask_concentration = self._calculate_concentration(ask_quantities)

        depth_ratio = total_bid_qty / total_ask_qty if total_ask_qty > 0 else 0

        metrics = {
            'spread': spread,
            'spread_pct': spread_pct,
            'imbalance': imbalance,
            'vwap_bid': vwap_bid,
            'vwap_ask': vwap_ask,
            'bid_concentration': bid_concentration,
            'ask_concentration': ask_concentration,
            'depth_ratio': depth_ratio,
            'total_bid_depth': total_bid_qty,
            'total_ask_depth': total_ask_qty,
            'data_valid': True
        }

        if code not in self.dict_orderbook_history:
            self.dict_orderbook_history[code] = deque(maxlen=self.data_cnt)
            self.dict_spread_history[code] = deque(maxlen=self.data_cnt)

        self.dict_orderbook_history[code].append(metrics)
        self.dict_spread_history[code].append(spread_pct)

        return metrics
    
    def _calculate_vwap(self, prices: np.ndarray, quantities: np.ndarray) -> float:
        total_value = sum(prices * quantities)
        total_qty = sum(quantities)
        return total_value / (total_qty + 1e-8)
    
    def _calculate_concentration(self, quantities: np.ndarray) -> float:
        total_qty = sum(quantities)
        if total_qty == 0:
            return 0
        
        proportions = quantities / total_qty
        hhi = sum(p**2 for p in proportions)
        return hhi

    def detect_liquidity_pressure(self, code: str, current_metrics: Dict) -> Dict:
        if len(self.dict_spread_history[code]) == self.data_cnt:
            recent_spreads = list(self.dict_spread_history[code])
            spread_trend = np.polyfit(range(self.data_cnt), recent_spreads, 1)[0]
        else:
            spread_trend = 0

        if len(self.dict_orderbook_history[code]) == self.data_cnt:
            recent_imbalances = [h['imbalance'] for h in list(self.dict_orderbook_history[code])]
            imbalance_trend = np.polyfit(range(self.data_cnt), recent_imbalances, 1)[0]
        else:
            imbalance_trend = 0

        liquidity_signal = self._generate_liquidity_signal(
            current_metrics, spread_trend, imbalance_trend
        )

        return {
            'spread_trend': spread_trend,
            'imbalance_trend': imbalance_trend,
            'liquidity_signal': liquidity_signal,
            'pressure_level': self._calculate_pressure_level(current_metrics)
        }
    
    def _generate_liquidity_signal(self, metrics: Dict, spread_trend: float, imbalance_trend: float) -> str:
        if metrics['imbalance'] > 0.3 and spread_trend < -0.1 and imbalance_trend > 0.05:
            return 'STRONG_BUY'

        elif metrics['imbalance'] < -0.3 and spread_trend < -0.1 and imbalance_trend < -0.05:
            return 'STRONG_SELL'

        elif metrics['imbalance'] > 0.1:
            return 'WEAK_BUY'

        elif metrics['imbalance'] < -0.1:
            return 'WEAK_SELL'
        
        return 'NEUTRAL'

    def _calculate_pressure_level(self, metrics: Dict) -> float:
        imbalance_score = abs(metrics['imbalance'])
        spread_score = min(metrics['spread_pct'] / 1.0, 1.0)
        concentration_score = (metrics['bid_concentration'] + metrics['ask_concentration']) / 2
        
        return (imbalance_score + spread_score + concentration_score) / 3
