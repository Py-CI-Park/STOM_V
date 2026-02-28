
import numpy as np
from typing import Dict
from strategy.orderbook_analyzer import OrderBookAnalyzer
from strategy.manipulation_detector import ManipulationDetector


class MicrostructureAnalyzer:
    def __init__(self):
        self.orderbook_analyzer = OrderBookAnalyzer()
        self.manipulation_detector = ManipulationDetector()

    def analyze_microstructure_signal(self, code: str, orderbook_data: np.ndarray, volume_data: np.ndarray = None):
        market_state = self.orderbook_analyzer.get_market_state(code, orderbook_data)
        manipulation_signals = self.manipulation_detector.get_all_manipulations(code, orderbook_data, volume_data)
        risk_assessment = self.assess_risk(market_state, manipulation_signals)
        trading_signal = self.generate_scalping_signal(
            market_state, manipulation_signals, risk_assessment
        )

        return trading_signal['action'], trading_signal['confidence']
        # return {
        #     'market_state': market_state,
        #     'manipulation_signals': manipulation_signals,
        #     'trading_signal': trading_signal,
        #     'risk_assessment': risk_assessment,
        #     'timestamp': datetime.now()
        # }
    
    def generate_scalping_signal(self, market_state: Dict, manipulation_signals: Dict, risk_assessment: Dict) -> Dict:
        if manipulation_signals['overall_risk']['risk_level'] == 'HIGH':
            return {
                'action': 'HOLD',
                'reason': 'HIGH_MANIPULATION_RISK',
                'confidence': 0.0
            }

        liquidity_signal = market_state['pressure']['liquidity_signal']
        pressure_level = market_state['pressure']['pressure_level']
        flow_signal = self.analyze_order_flow(market_state)
        final_signal = self.fuse_signals(liquidity_signal, flow_signal)
        confidence = self.calculate_signal_confidence(
            final_signal, market_state, risk_assessment
        )

        return {
            'action': final_signal,
            'confidence': confidence,
            'strength': pressure_level
        }
    
    def analyze_order_flow(self, market_state: Dict) -> str:
        metrics = market_state['metrics']
        imbalance = metrics['imbalance']
        depth_ratio = metrics['depth_ratio']
        spread_pct = metrics['spread_pct']
        bid_concentration = metrics['bid_concentration']
        ask_concentration = metrics['ask_concentration']

        buy_flow_strength = (
            (imbalance > 0) * 0.4 +
            (depth_ratio > 1.5) * 0.3 +
            (spread_pct < 0.1) * 0.2 +
            (bid_concentration > 0.5) * 0.1
        )

        sell_flow_strength = (
            (imbalance < 0) * 0.4 +
            (depth_ratio < 0.5) * 0.3 +
            (spread_pct < 0.1) * 0.2 +
            (ask_concentration > 0.5) * 0.1
        )

        if buy_flow_strength > sell_flow_strength + 0.2:
            return 'STRONG_BUY'
        elif sell_flow_strength > buy_flow_strength + 0.2:
            return 'STRONG_SELL'
        elif buy_flow_strength > sell_flow_strength:
            return 'WEAK_BUY'
        elif sell_flow_strength > buy_flow_strength:
            return 'WEAK_SELL'
        else:
            return 'NEUTRAL'
    
    def fuse_signals(self, liquidity_signal: str, flow_signal: str) -> str:
        liquidity_weight = 0.6
        flow_weight = 0.4

        signal_scores = {
            'STRONG_BUY': 2, 'BUY': 1, 'WEAK_BUY': 0.5,
            'STRONG_SELL': -2, 'SELL': -1, 'WEAK_SELL': -0.5,
            'NEUTRAL': 0, 'HOLD': 0
        }

        liquidity_score = signal_scores.get(liquidity_signal, 0)
        flow_score = signal_scores.get(flow_signal, 0)
        fused_score = liquidity_score * liquidity_weight + flow_score * flow_weight
        if fused_score >= 0.4:
            return 'BUY'
        elif fused_score <= -0.4:
            return 'SELL'
        else:
            return 'HOLD'
    
    def calculate_signal_confidence(self, signal: str, market_state: Dict, risk_assessment: Dict) -> float:
        pressure_level    = market_state['pressure']['pressure_level']
        imbalance         = abs(market_state['metrics']['imbalance'])
        imbalance_trend   = market_state['pressure']['imbalance_trend']
        depth_ratio       = market_state['metrics']['depth_ratio']
        risk_level        = risk_assessment['total_risk']

        signal_adjustments = {
            'BUY': 1.0, 'SELL': 1.0, 'HOLD': 0.1
        }
        base_confidence = signal_adjustments.get(signal, 0) * 0.2
        pressure_confidence = min(max(0.01, pressure_level * 3), 1.0) * 0.2
        imbalance_confidence = min(max(0.01, imbalance), 1.0) * 0.2
        if signal == 'BUY':
            trend_confidence = min(max(0.01, imbalance_trend * 20), 1.0) * 0.1
            depth_confidence = min(max(0.01, depth_ratio * 0.3), 1.0) * 0.1
        else:
            trend_confidence = min(max(0.01, 1 - imbalance_trend * 20), 1.0) * 0.1
            depth_confidence = min(max(0.01, 1 - depth_ratio * 0.3), 1.0) * 0.1
        risk_confidence = min(max(0.01, 1 - risk_level), 1.0) * 0.2

        final_confidence = base_confidence + pressure_confidence + imbalance_confidence + trend_confidence + depth_confidence + risk_confidence
        final_confidence = np.round(final_confidence, 2)
        final_confidence = min(max(final_confidence, 0.1), 1.0)

        return final_confidence
    
    def assess_risk(self, market_state: Dict, manipulation_signals: Dict) -> Dict:
        market_risk = self.calculate_market_risk(market_state)
        manipulation_risk = self.calculate_manipulation_risk(manipulation_signals)
        liquidity_risk = self.calculate_liquidity_risk(market_state)
        total_risk = (market_risk + manipulation_risk + liquidity_risk) / 3

        return {
            'market_risk': market_risk,
            'manipulation_risk': manipulation_risk,
            'liquidity_risk': liquidity_risk,
            'total_risk': total_risk,
            'risk_level': self.determine_risk_level(total_risk)
        }
    
    def calculate_market_risk(self, market_state: Dict) -> float:
        metrics = market_state['metrics']
        spread_risk = min(metrics['spread_pct'] / 1.0, 1.0)
        imbalance_risk = abs(metrics['imbalance'])
        depth_risk = min(abs(1 - metrics['depth_ratio']) / 2.0, 1.0)
        return (spread_risk + imbalance_risk + depth_risk) / 3
    
    def calculate_manipulation_risk(self, manipulation_signals: Dict) -> float:
        risk_level = manipulation_signals['overall_risk']['risk_level']
        total_signals = manipulation_signals['overall_risk']['total_signals']
        
        base_risk = {
            'LOW': 0.1,
            'MEDIUM': 0.5,
            'HIGH': 0.9
        }.get(risk_level, 0.5)
        signal_risk = min(total_signals / 10.0, 1.0)
        return (base_risk + signal_risk) / 2
    
    def calculate_liquidity_risk(self, market_state: Dict) -> float:
        metrics = market_state['metrics']
        total_depth = metrics['total_bid_depth'] + metrics['total_ask_depth']
        depth_risk = max(0, 1 - total_depth / 100000)
        avg_concentration = (metrics['bid_concentration'] + metrics['ask_concentration']) / 2
        concentration_risk = avg_concentration
        return (depth_risk + concentration_risk) / 2
    
    def determine_risk_level(self, total_risk: float) -> str:
        if total_risk < 0.3:
            return 'LOW'
        elif total_risk < 0.7:
            return 'MEDIUM'
        else:
            return 'HIGH'
