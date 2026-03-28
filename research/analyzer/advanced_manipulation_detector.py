"""
고급 시장 조작 감지 및 예측 시스템
머신러닝 기반 비정상 거래 패턴 식별
"""

import warnings
from typing import Dict, List
from datetime import datetime
from utility.lazy_imports import get_np
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest, RandomForestClassifier
warnings.filterwarnings('ignore')


class AdvancedManipulationDetector:
    """
    고급 시장 조작 감지 시스템
    
    기능:
    - 머신러닝 기반 비정상 패턴 감지
    - 스푸핑/레이어링 탐지
    - 펌프앤덤프 패턴 식별
    - 실시간 위험도 평가
    """
    
    def __init__(self, contamination_rate: float = 0.1):
        """
        초기화
        
        Args:
            contamination_rate: 이상치 비율
        """
        self.contamination_rate = contamination_rate
        self.isolation_forest = IsolationForest(
            contamination=contamination_rate, random_state=42
        )
        self.random_forest = RandomForestClassifier(
            n_estimators=100, random_state=42
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_history = []
        self.manipulation_score = 0.0
        self.alerts = []
        
    def extract_orderbook_features(self, orderbook_data: Dict) -> get_np().ndarray:
        """
        호가창 데이터에서 특성 추출
        
        Args:
            orderbook_data: 호가창 데이터
            
        Returns:
            특성 배열
        """
        features = []
        
        # 매수/매도 호가 스프레드
        best_bid = orderbook_data.get('best_bid', 0)
        best_ask = orderbook_data.get('best_ask', 0)
        spread = best_ask - best_bid
        spread_ratio = spread / best_bid if best_bid > 0 else 0
        
        # 호가 깊이 불균형
        bid_volume = sum(orderbook_data.get('bid_volumes', []))
        ask_volume = sum(orderbook_data.get('ask_volumes', []))
        volume_imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume + 1e-8)
        
        # 대규모 주문 비율
        large_orders = orderbook_data.get('large_orders', 0)
        total_volume = bid_volume + ask_volume
        large_order_ratio = large_orders / total_volume if total_volume > 0 else 0
        
        # 호가 변화율
        price_change = orderbook_data.get('price_change', 0)
        price_volatility = orderbook_data.get('price_volatility', 0)
        
        features.extend([
            spread, spread_ratio, volume_imbalance,
            large_order_ratio, price_change, price_volatility
        ])
        
        return get_np().array(features)
    
    def extract_trade_features(self, trade_data: Dict) -> get_np().ndarray:
        """
        체결 데이터에서 특성 추출
        
        Args:
            trade_data: 체결 데이터
            
        Returns:
            특성 배열
        """
        features = []
        
        # 거래량 이상치
        volume = trade_data.get('volume', 0)
        avg_volume = trade_data.get('avg_volume', 1)
        volume_ratio = volume / avg_volume
        
        # 거래 빈도
        trade_frequency = trade_data.get('trade_frequency', 0)
        
        # 가격 변화율
        price_change = trade_data.get('price_change', 0)
        price_impact = trade_data.get('price_impact', 0)
        
        # 시간 패턴
        time_pattern = trade_data.get('time_pattern', 0)
        
        # 거래 방향 비율
        buy_ratio = trade_data.get('buy_ratio', 0.5)
        
        features.extend([
            volume, volume_ratio, trade_frequency,
            price_change, price_impact, time_pattern, buy_ratio
        ])
        
        return get_np().array(features)
    
    def detect_spoofing(self, orderbook_data: Dict) -> Dict:
        """
        스푸핑 감지
        
        Args:
            orderbook_data: 호가창 데이터
            
        Returns:
            스푸핑 감지 결과
        """
        features = self.extract_orderbook_features(orderbook_data)
        
        if not self.is_trained:
            return {'spoofing_detected': False, 'confidence': 0.0}
        
        # 이상치 점수 계산
        anomaly_score = self.isolation_forest.decision_function([features])[0]
        
        # 스푸핑 특징 확인
        # noinspection PyTypeChecker
        large_spread = features[0] > get_np().mean([f[0] for f in self.feature_history]) * 2
        volume_imbalance = abs(features[2]) > 0.7
        
        spoofing_confidence = 0.0
        if large_spread and volume_imbalance:
            spoofing_confidence = 0.8
        elif large_spread or volume_imbalance:
            spoofing_confidence = 0.5
        
        return {
            'spoofing_detected': spoofing_confidence > 0.6,
            'confidence': spoofing_confidence,
            'anomaly_score': anomaly_score
        }
    
    def detect_layering(self, trade_sequence: List[Dict]) -> Dict:
        """
        레이어링 감지
        
        Args:
            trade_sequence: 거래 시퀀스
            
        Returns:
            레이어링 감지 결과
        """
        if len(trade_sequence) < 10:
            return {'layering_detected': False, 'confidence': 0.0}
        
        # 작은 주문 패턴 분석
        small_trades = [t for t in trade_sequence if t.get('volume', 0) < 1000]
        
        # 작은 주문 비율
        small_trade_ratio = len(small_trades) / len(trade_sequence)
        
        # 가격 영향력 분석
        price_impacts = [t.get('price_impact', 0) for t in small_trades]
        avg_small_impact = get_np().mean(price_impacts) if price_impacts else 0
        
        # 시간 집중도
        time_intervals = []
        for i in range(1, len(trade_sequence)):
            t1 = trade_sequence[i-1].get('timestamp')
            t2 = trade_sequence[i].get('timestamp')
            if t1 and t2:
                time_intervals.append((t2 - t1).total_seconds())
        
        time_concentration = get_np().std(time_intervals) if time_intervals else 0
        
        # 레이어링 점수 계산
        layering_score = 0.0
        if small_trade_ratio > 0.7 and avg_small_impact > 0.001:
            layering_score += 0.4
        if time_concentration < 10:  # 짧은 시간 간격
            layering_score += 0.3
        
        return {
            'layering_detected': layering_score > 0.5,
            'confidence': min(layering_score, 1.0),
            'small_trade_ratio': small_trade_ratio,
            'time_concentration': time_concentration
        }
    
    def detect_pump_dump(self, price_data: get_np().ndarray, volume_data: get_np().ndarray) -> Dict:
        """
        펌프앤덤프 패턴 감지
        
        Args:
            price_data: 가격 데이터
            volume_data: 거래량 데이터
            
        Returns:
            펌프앤덤프 감지 결과
        """
        if len(price_data) < 50:
            return {'pump_dump_detected': False, 'confidence': 0.0}
        
        # 가격 변화율 계산
        returns = get_np().diff(get_np().log(price_data))
        
        # 거래량 이상치 감지
        volume_ma = get_np().convolve(volume_data, get_np().ones(10)/10, mode='valid')
        volume_spike = volume_data > volume_ma * 3
        
        # 급격한 가격 상승 후 하락 패턴
        price_spike = returns > get_np().percentile(returns, 95)
        subsequent_decline = returns < -get_np().percentile(returns, 80)
        
        # 패턴 매칭
        pump_detected = False
        dump_detected = False
        confidence = 0.0
        
        for i in range(1, len(price_spike)):
            if price_spike[i] and volume_spike[i]:
                pump_detected = True
                # 이후 하락 확인
                if i + 5 < len(subsequent_decline) and get_np().any(subsequent_decline[i:i+5]):
                    dump_detected = True
                    confidence = 0.8
                    break
        
        return {
            'pump_dump_detected': pump_detected and dump_detected,
            'confidence': confidence,
            'pump_detected': pump_detected,
            'dump_detected': dump_detected
        }
    
    def calculate_manipulation_score(self, features: get_np().ndarray) -> float:
        """
        종합 조작 점수 계산
        
        Args:
            features: 특성 배열
            
        Returns:
            조작 점수 (0-1)
        """
        if not self.is_trained:
            return 0.0
        
        # 이상치 점수
        anomaly_score = self.isolation_forest.decision_function([features])[0]
        normalized_score = (anomaly_score + 1) / 2  # 0-1로 정규화
        
        return max(0, min(1, normalized_score))
    
    def train_model(self, training_data: List[Dict]):
        """
        조작 감지 모델 학습
        
        Args:
            training_data: 학습 데이터
        """
        if len(training_data) < 100:
            print("경고: 학습 데이터가 부족합니다.")
            return
        
        # 특성 추출
        all_features = []
        labels = []
        
        for data in training_data:
            if 'orderbook' in data:
                features = self.extract_orderbook_features(data['orderbook'])
            elif 'trade' in data:
                features = self.extract_trade_features(data['trade'])
            else:
                continue
            
            all_features.append(features)
            labels.append(data.get('label', 0))  # 0: 정상, 1: 조작
        
        if len(all_features) == 0:
            return
        
        # 데이터 정규화
        X = self.scaler.fit_transform(all_features)
        y = get_np().array(labels)
        
        # 모델 학습
        self.isolation_forest.fit(X)
        self.random_forest.fit(X, y)
        self.is_trained = True
        
        print(f"조작 감지 모델 학습 완료. 학습 데이터: {len(all_features)}개")
    
    def analyze_realtime_data(self, market_data: Dict) -> Dict:
        """
        실시간 시장 데이터 분석
        
        Args:
            market_data: 시장 데이터
            
        Returns:
            분석 결과
        """
        results = {
            'timestamp': datetime.now(),
            'manipulation_score': 0.0,
            'alerts': [],
            'detailed_analysis': {}
        }
        
        # 특성 추출
        features = self.extract_orderbook_features(market_data['orderbook'])
        results['manipulation_score'] = self.calculate_manipulation_score(features)

        spoofing_result = self.detect_spoofing(market_data['orderbook'])
        results['detailed_analysis']['spoofing'] = spoofing_result

        if 'trade_sequence' in market_data:
            layering_result = self.detect_layering(market_data['trade_sequence'])
            results['detailed_analysis']['layering'] = layering_result

        if 'price_volume' in market_data:
            price_data = market_data['price_volume']['price']
            volume_data = market_data['price_volume']['volume']
            pump_dump_result = self.detect_pump_dump(price_data, volume_data)
            results['detailed_analysis']['pump_dump'] = pump_dump_result

        # 경고 생성
        alerts = []
        for analysis_type, analysis_result in results['detailed_analysis'].items():
            if analysis_result.get(f'{analysis_type}_detected', False):
                alerts.append({
                    'type': analysis_type,
                    'confidence': analysis_result.get('confidence', 0.0),
                    'message': f"{analysis_type.upper()} 감지됨 (신뢰도: {analysis_result.get('confidence', 0.0):.2f})"
                })
        
        results['alerts'] = alerts
        
        # 이력 저장
        self.feature_history.append(features if 'orderbook' in market_data else get_np().zeros(6))
        if len(self.feature_history) > 1000:
            self.feature_history = self.feature_history[-1000:]
        
        self.manipulation_score = results['manipulation_score']
        self.alerts.extend(alerts)
        
        return results


class ManipulationRiskManager:
    """
    조작 감지 기반 리스크 관리 시스템
    """
    
    def __init__(self, risk_threshold: float = 0.7):
        """
        초기화
        
        Args:
            risk_threshold: 리스크 임계값
        """
        self.risk_threshold = risk_threshold
        self.position_adjustments = {}
        
    def calculate_position_adjustment(self, manipulation_score: float, current_position: float) -> float:
        """
        조작 점수에 따른 포지션 조정
        
        Args:
            manipulation_score: 조작 점수
            current_position: 현재 포지션
            
        Returns:
            조정된 포지션 크기
        """
        if manipulation_score < 0.3:
            return current_position  # 정상
        elif manipulation_score < 0.5:
            return current_position * 0.8  # 20% 감소
        elif manipulation_score < 0.7:
            return current_position * 0.5  # 50% 감소
        else:
            return current_position * 0.2  # 80% 감소
    
    def should_halt_trading(self, manipulation_score: float, consecutive_alerts: int) -> bool:
        """
        거래 중단 여부 결정
        
        Args:
            manipulation_score: 조작 점수
            consecutive_alerts: 연속 경고 수
            
        Returns:
            거래 중단 여부
        """
        return (manipulation_score > self.risk_threshold or 
                consecutive_alerts > 3)


def test_manipulation_detector():
    """
    조작 감지 시스템 테스트
    """
    # 조작 감지기 초기화
    detector = AdvancedManipulationDetector(contamination_rate=0.1)
    risk_manager = ManipulationRiskManager()
    
    # 샘플 데이터 생성
    get_np().random.seed(42)
    
    # 학습 데이터 생성
    training_data = []
    for i in range(200):
        # 정상 데이터
        normal_data = {
            'orderbook': {
                'best_bid': get_np().random.normal(100, 1),
                'best_ask': get_np().random.normal(101, 1),
                'bid_volumes': get_np().random.exponential(1000, 5).tolist(),
                'ask_volumes': get_np().random.exponential(1000, 5).tolist(),
                'large_orders': get_np().random.exponential(100),
                'price_change': get_np().random.normal(0, 0.5),
                'price_volatility': get_np().random.exponential(0.5)
            },
            'label': 0
        }
        training_data.append(normal_data)
        
        # 조작 데이터 (스푸핑)
        if i % 10 == 0:
            spoofing_data = {
                'orderbook': {
                    'best_bid': 100,
                    'best_ask': 105,  # 큰 스프레드
                    'bid_volumes': [10000, 5000, 1000, 500, 100],
                    'ask_volumes': [100, 200, 300, 400, 500],
                    'large_orders': 50000,
                    'price_change': 2.0,
                    'price_volatility': 2.0
                },
                'label': 1
            }
            training_data.append(spoofing_data)
    
    # 모델 학습
    detector.train_model(training_data)
    
    print("실시간 조작 감지 테스트")
    print("=" * 50)
    
    # 실시간 데이터 분석 시뮬레이션
    for i in range(20):
        # 테스트 데이터 생성
        if i < 10:
            # 정상 시장
            test_data = {
                'orderbook': {
                    'best_bid': get_np().random.normal(100, 0.5),
                    'best_ask': get_np().random.normal(101, 0.5),
                    'bid_volumes': get_np().random.exponential(1000, 5).tolist(),
                    'ask_volumes': get_np().random.exponential(1000, 5).tolist(),
                    'large_orders': get_np().random.exponential(100),
                    'price_change': get_np().random.normal(0, 0.2),
                    'price_volatility': get_np().random.exponential(0.3)
                }
            }
        else:
            # 조작 시장
            test_data = {
                'orderbook': {
                    'best_bid': 100,
                    'best_ask': 104,  # 스푸핑 의심
                    'bid_volumes': [10000, 100, 100, 100, 100],
                    'ask_volumes': [100, 100, 100, 100, 100],
                    'large_orders': 30000,
                    'price_change': 1.5,
                    'price_volatility': 1.8
                }
            }
        
        # 실시간 분석
        results = detector.analyze_realtime_data(test_data)
        
        # 리스크 관리
        position_adj = risk_manager.calculate_position_adjustment(
            results['manipulation_score'], 1000000
        )
        
        should_halt = risk_manager.should_halt_trading(
            results['manipulation_score'], len(results['alerts'])
        )
        
        print(f"\n시간 {i+1}:")
        print(f"조작 점수: {results['manipulation_score']:.3f}")
        print(f"경고 수: {len(results['alerts'])}")
        
        if results['alerts']:
            for alert in results['alerts']:
                print(f"  - {alert['message']}")
        
        print(f"권장 포지션: {position_adj:,.0f}")
        print(f"거래 중단: {'예' if should_halt else '아니오'}")
    
    print("\n" + "=" * 50)
    print("조작 감지 시스템 테스트 완료")


if __name__ == "__main__":
    test_manipulation_detector()
